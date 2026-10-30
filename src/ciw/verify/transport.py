"""Private DNS fallback without changing system DNS, TLS identity, or model routes."""

import codecs
import http.client
import ipaddress
import json
import math
import re
import shutil
import socket
import subprocess
import urllib.request
from email.utils import parsedate_to_datetime
from time import monotonic, sleep, time
from urllib.error import HTTPError
from urllib.parse import urlsplit

from ciw.verify.stream import assemble_sse, completion_from_json


def _tailscale_address(host: str) -> str:
    cli = shutil.which("tailscale")
    if not cli:
        raise OSError("Tailscale DNS工具不可用")
    try:
        result = subprocess.run(
            [cli, "dns", "query", "--json", host, "A"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except subprocess.SubprocessError as exc:
        raise OSError("Tailscale DNS查询失败") from exc
    doc = json.loads(result.stdout)
    addresses = {
        str(ipaddress.ip_address(a["Body"]))
        for a in doc.get("Answers", [])
        if a.get("Type") == "TypeA" and a.get("Name", "").rstrip(".").casefold() == host.casefold()
    }
    if doc.get("ResponseCode") != "RCodeSuccess" or len(addresses) != 1:
        raise OSError("Tailscale DNS没有唯一地址")
    address = addresses.pop()
    if ipaddress.ip_address(address) not in ipaddress.ip_network("100.64.0.0/10"):
        raise OSError("解析结果不是Tailscale私网地址")
    return address


class _PrivateHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, *, expected_host, transport, **kwargs):
        super().__init__(host, **kwargs)

        def connect(address, timeout, source_address):
            try:
                return socket.create_connection(address, timeout, source_address)
            except socket.gaierror:
                if address[0] != expected_host:
                    raise
                ip = _tailscale_address(expected_host)
                transport["dns_resolution"] = "tailscale-cli"
                return socket.create_connection((ip, address[1]), timeout, source_address)

        # HTTPSConnection still wraps this socket using the original host as SNI,
        # and the standard certificate/hostname checks stay enabled.
        self._create_connection = connect


class _PrivateHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, host, transport):
        super().__init__()
        self.host, self.transport = host, transport

    def https_open(self, req):
        def connection(host, **kwargs):
            return _PrivateHTTPSConnection(host, expected_host=self.host, transport=self.transport, **kwargs)

        return self.do_open(connection, req, context=self._context)


def model_opener(base_url: str, no_proxy: bool, transport: dict):
    handlers = [urllib.request.ProxyHandler({})] if no_proxy else []
    url = urlsplit(base_url)
    if no_proxy and url.scheme == "https" and url.hostname and url.hostname.endswith(".ts.net"):
        handlers.append(_PrivateHTTPSHandler(url.hostname, transport))
    return urllib.request.build_opener(*handlers)


def _retry_delay(header, attempt):
    floor = min(60, 5 * 2**attempt)
    try:
        value = float(header)
        if math.isfinite(value):
            return max(floor, value)
    except (ValueError, TypeError):
        pass
    try:
        return max(floor, parsedate_to_datetime(header).timestamp() - time())
    except (ValueError, TypeError, AttributeError, OverflowError):
        return floor


def rejection_kind(error):
    """Keep an operational category only; upstream text may contain private data."""
    if not isinstance(error, (dict, str)):
        return "unclassified"
    text = (json.dumps(error, ensure_ascii=False) if isinstance(error, dict) else error)[:4096].lower()
    for category, pattern in (
        ("quota", r"quota|\bbalance\b|\bcredits?\b|insufficient.{0,24}funds"),
        ("concurrency", r"concurren|in[-_ ]?flight|simultaneous|active requests|parallel"),
        ("context_capacity", r"context|kv.{0,12}(?:cache|pool)|token.{0,12}(?:budget|capacity)"),
        ("request_rate", r"rate[-_ ]?limit|requests per|too many requests"),
        ("model_transition", r"switch|loading|warming"),
        ("service_busy", r"overload|busy|capacity"),
    ):
        if re.search(pattern, text):
            return category
    return "unclassified"


def _error_receipt(exc, transport):
    """Consume an error once and retain only operational enums, never its private body."""
    transport["rejection_kind"] = "unclassified"
    try:
        failure = json.loads(exc.read(8192))
        error = failure.get("error", failure.get("detail", failure)) if isinstance(failure, dict) else failure
        transport["rejection_kind"] = rejection_kind(error)
        message = str(error.get("message", "")) if isinstance(error, dict) else ""
        for parameter in ("response_format", "temperature", "max_tokens", "reasoning_effort"):
            if parameter in message:
                transport["provider_parameter"] = parameter
                break
    except (ValueError, OSError, AttributeError):
        pass
    finally:
        exc.close()
    return transport["rejection_kind"]


def model_json(opener, request, timeout, transport, stream=False):
    """Retry only completed 429 rejections, never an in-flight/ambiguous model request."""
    started = monotonic()
    attempt = 0
    while True:
        remaining = timeout - (monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("模型请求总等待时间已用尽")
        try:
            with opener.open(request, timeout=remaining) as response:
                if stream:
                    return _stream_completion(response, started, timeout, transport)
                return json.load(response)
        except HTTPError as exc:
            kind = _error_receipt(exc, transport)
            temporary = kind in {"concurrency", "context_capacity", "model_transition", "service_busy"}
            budget = timeout if temporary else min(timeout, 180)
            wait = _retry_delay((exc.headers or {}).get("Retry-After"), attempt)
            if (exc.code != 429 or kind == "quota" or (not temporary and attempt >= 5)
                    or monotonic() - started + wait >= budget):
                raise
            transport.setdefault("admission_retries", []).append(dict(http_status=429, wait_seconds=wait))
            exc.close()
            sleep(wait)
            attempt += 1


def _media_type(response):
    headers = getattr(response, "headers", None)
    if headers is None:
        return ""
    if hasattr(headers, "get_content_type"):
        return (headers.get_content_type() or "").lower()
    raw = headers.get("Content-Type", "") if hasattr(headers, "get") else ""
    return str(raw).split(";", 1)[0].strip().lower()


def _arm_timeout(response, remaining):
    if hasattr(response, "settimeout"):
        response.settimeout(remaining)
    fp = getattr(response, "fp", None)
    raw = getattr(fp, "raw", None)
    sock = getattr(raw, "_sock", None) or getattr(response, "_sock", None)
    if sock is not None and sock is not response and hasattr(sock, "settimeout"):
        sock.settimeout(remaining)


def _bounded_read(response, started, timeout):
    """Read one response until EOF without extending the original deadline."""
    while True:
        remaining = timeout - (monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("模型请求总等待时间已用尽")
        _arm_timeout(response, remaining)
        try:
            read = getattr(response, "read1", None) or response.read
            chunk = read(8192)
        except TimeoutError:
            raise TimeoutError("模型请求总等待时间已用尽") from None
        except http.client.HTTPException:
            raise OSError("模型流式响应失败") from None
        if not chunk:
            return
        if not isinstance(chunk, (bytes, bytearray)):
            raise OSError("模型流式响应失败")
        yield bytes(chunk)


def _event_text(response, started, timeout):
    decoder = codecs.getincrementaldecoder("utf-8")()
    parts = []
    for chunk in _bounded_read(response, started, timeout):
        try:
            parts.append(decoder.decode(chunk, False))
        except UnicodeDecodeError:
            raise OSError("模型流式响应失败") from None
    try:
        tail = decoder.decode(b"", True)
    except UnicodeDecodeError:
        raise OSError("模型流式响应失败") from None
    if tail:
        parts.append(tail)
    return "".join(parts)


def _json_document(response, started, timeout):
    raw = b"".join(_bounded_read(response, started, timeout))
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise OSError("模型流式响应失败") from None


def _stream_completion(response, started, timeout, transport):
    """Consume SSE, or one explicit JSON completion. Do not open another request."""
    media = _media_type(response)
    try:
        if media == "application/json":
            result = completion_from_json(_json_document(response, started, timeout))
        elif media == "text/event-stream":
            result = assemble_sse(_event_text(response, started, timeout))
        else:
            raise OSError("模型流式响应失败")
    except OSError as exc:
        kind = getattr(exc, "rejection_kind", None)
        if kind:
            transport["rejection_kind"] = kind
        raise
    return result
