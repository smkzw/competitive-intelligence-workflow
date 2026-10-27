"""Private DNS fallback without changing system DNS, TLS identity, or model routes."""

import http.client
import ipaddress
import json
import shutil
import socket
import subprocess
import urllib.request
from urllib.parse import urlsplit


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
