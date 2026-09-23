"""Strict, on-demand loopback editor for :mod:`user_fact_edit`.

The server has no wildcard CORS, file URL, shell, filesystem-path, or multipart upload
surface. Every write requires an exact loopback Host/Origin pair, a SameSite session,
and a per-session CSRF token.
"""

from __future__ import annotations

import argparse
import html
import json
import secrets
import threading
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ci_workflow.application.user_fact_edit import (
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveConflictError,
    UserFactSaveError,
)

_MAX_BODY = 64 * 1024


def _editor_page(*, facts: dict[str, dict[str, Any]], revision: int, project_id: str) -> bytes:
    encoded = json.dumps(facts, ensure_ascii=False).replace("</", "<\\/")
    rate = facts.get("fact-crude-rate", {})
    threshold = facts.get("fact-c-threshold", {})
    numerator = html.escape(str(rate.get("numerator", "")))
    denominator = html.escape(str(rate.get("denominator", "")))
    threshold_operator = html.escape(str(threshold.get("threshold_operator", "<")))
    threshold_value = html.escape(str(threshold.get("threshold_value", "")))
    threshold_unit = html.escape(str(threshold.get("threshold_unit", "g/dL")))
    encoded_project_id = json.dumps(project_id)
    template = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>事实修订</title><style>
body{{font:16px system-ui,sans-serif;margin:2rem;max-width:860px;color:#17212b}}
section{{border:1px solid #ccd6df;border-radius:12px;padding:1rem;margin:1rem 0}}
label{{display:inline-grid;gap:.35rem;margin:.5rem}} input{{font:inherit;padding:.45rem;width:9rem}}
button{{font:inherit;padding:.6rem 1rem;background:#8b1e2d;color:white;border:0;border-radius:8px}}
#status{{padding:.75rem;background:#f3f6f8}} code{{overflow-wrap:anywhere}}
</style></head><body>
<h1>当前事实修订</h1>
<p id="status" role="status">
当前 revision {revision}；用户保存后不继承独立科学接受。
</p>
<section data-fact-id="fact-crude-rate"><h2>人数粗率</h2>
<label>事件人数 n<input id="numerator" inputmode="numeric" value="{numerator}"></label>
<label>分母 N<input id="denominator" inputmode="numeric" value="{denominator}"></label>
<label>用户依据<input id="rate-basis" value="根据核对后的病例汇总表修订"></label>
<button id="save-rate">保存人数粗率</button></section>
<section data-fact-id="fact-c-threshold"><h2>C 阈值</h2>
<label>运算符<input id="threshold-operator" value="{threshold_operator}"></label>
<label>阈值<input id="threshold-value" inputmode="decimal" value="{threshold_value}"></label>
<label>单位<input id="threshold-unit" value="{threshold_unit}"></label>
<label>用户依据<input id="threshold-basis" value="根据方案修订版修订阈值"></label>
<button id="save-threshold">保存 C 阈值</button></section>
<pre id="result"></pre><script id="facts" type="application/json">{encoded}</script>
<script>
const facts=JSON.parse(document.getElementById('facts').textContent);let revision={revision};
const post=async(target,edits,basis)=>{{
 const payload={{schema_version:'1.0',request_id:'browser-'+crypto.randomUUID(),
 project_id:{encoded_project_id},
 expected_revision:revision,operation:'save',target:{{fact_id:target.fact_id,fact_version_id:target.fact_version_id,
 entity_id:target.entity_id,field_id:target.field_id}},edits,user_basis:basis,saved_by:'browser-user',
 saved_at:new Date().toISOString()}};
 const response=await fetch('/api/save',{{method:'POST',headers:{{'Content-Type':'application/json',
 'X-CSRF-Token':document.querySelector('meta[name=csrf]').content}},body:JSON.stringify(payload)}});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'保存失败');
 revision=data.revision;target.fact_version_id=data.fact_version_id;
 document.getElementById('status').textContent=
  `当前 revision ${{revision}}；用户修订，未独立复核。`;
 document.getElementById('result').textContent=JSON.stringify(data,null,2);return data;
}};
document.getElementById('save-rate').onclick=()=>post(facts['fact-crude-rate'],{{numerator:Number(numerator.value),denominator:Number(denominator.value)}},document.getElementById('rate-basis').value).catch(e=>status.textContent=e.message);
document.getElementById('save-threshold').onclick=()=>post(facts['fact-c-threshold'],{{threshold_operator:document.getElementById('threshold-operator').value,threshold_value:Number(document.getElementById('threshold-value').value),threshold_unit:document.getElementById('threshold-unit').value}},document.getElementById('threshold-basis').value).catch(e=>status.textContent=e.message);
</script></body></html>"""
    return template.encode("utf-8")


class LoopbackEditServer:
    def __init__(self, service: UserFactEditService, *, port: int = 0) -> None:
        self.service = service
        self._sessions: dict[str, str] = {}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "CIWorkflowLoopback/1.0"

            def log_message(self, _format: str, *args: object) -> None:
                return

            def _host(self) -> str | None:
                expected = f"127.0.0.1:{owner.port}"
                return expected if self.headers.get("Host") == expected else None

            def _send(
                self,
                status: int,
                body: bytes,
                *,
                content_type: str,
                headers: dict[str, str] | None = None,
            ) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                content_security_policy = (
                    "default-src 'self'; script-src 'unsafe-inline'; "
                    "style-src 'unsafe-inline'; object-src 'none'; "
                    "base-uri 'none'; frame-ancestors 'none'"
                )
                self.send_header("Content-Security-Policy", content_security_policy)
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                self._send(
                    status,
                    (json.dumps(payload, ensure_ascii=False) + "\n").encode(),
                    content_type="application/json; charset=utf-8",
                )

            def _session(self) -> tuple[str, str] | None:
                cookie = SimpleCookie()
                try:
                    cookie.load(self.headers.get("Cookie", ""))
                except Exception:
                    return None
                morsel = cookie.get("session")
                if morsel is None:
                    return None
                token = owner._sessions.get(morsel.value)
                return (morsel.value, token) if token is not None else None

            def _authorize_write(self) -> bool:
                host = self._host()
                if host is None:
                    self._json(HTTPStatus.FORBIDDEN, {"error": "Host不受信任"})
                    return False
                if self.headers.get("Origin") != f"http://{host}":
                    self._json(HTTPStatus.FORBIDDEN, {"error": "Origin不受信任"})
                    return False
                session = self._session()
                csrf = self.headers.get("X-CSRF-Token", "")
                if session is None or not secrets.compare_digest(session[1], csrf):
                    self._json(HTTPStatus.FORBIDDEN, {"error": "会话或CSRF校验失败"})
                    return False
                return True

            def do_GET(self) -> None:  # noqa: N802
                if self._host() is None:
                    self._json(HTTPStatus.FORBIDDEN, {"error": "Host不受信任"})
                    return
                path = urlsplit(self.path).path
                if path == "/favicon.ico":
                    self._send(HTTPStatus.NO_CONTENT, b"", content_type="image/x-icon")
                    return
                if path != "/":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
                    return
                session_id = secrets.token_urlsafe(32)
                csrf = secrets.token_urlsafe(32)
                owner._sessions[session_id] = csrf
                current = owner.service.read_current_delivery()
                page = _editor_page(
                    facts=owner.service.current_facts(),
                    revision=current.revision,
                    project_id=current.project_id,
                )
                marker = b"<head>"
                page = page.replace(
                    marker,
                    marker + f'<meta name="csrf" content="{html.escape(csrf)}">'.encode(),
                    1,
                )
                self._send(
                    HTTPStatus.OK,
                    page,
                    content_type="text/html; charset=utf-8",
                    headers={
                        "Set-Cookie": f"session={session_id}; HttpOnly; SameSite=Strict; Path=/",
                        "X-CSRF-Token": csrf,
                    },
                )

            def do_POST(self) -> None:  # noqa: N802
                path = urlsplit(self.path).path
                if path != "/api/save":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "资源不存在"})
                    return
                if not self._authorize_write():
                    return
                if self.headers.get_content_type() != "application/json":
                    self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "仅接受JSON"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    length = -1
                if length < 0 or length > _MAX_BODY:
                    self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "请求过大"})
                    return
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw)
                    if not isinstance(payload, dict):
                        raise ValueError("top level")
                    command = UserFactSaveCommand.model_validate(payload)
                    result = owner.service.save(command)
                except UserFactSaveConflictError as error:
                    self._json(HTTPStatus.CONFLICT, {"error": str(error)})
                    return
                except (json.JSONDecodeError, ValueError, UserFactSaveError) as error:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                    return
                self._json(HTTPStatus.OK, result.model_dump(mode="json"))

        self._httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.port = int(self._httpd.server_address[1])
        self._thread: threading.Thread | None = None

    def start(self) -> LoopbackEditServer:
        if self._thread is None:
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
        return self

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> LoopbackEditServer:
        return self.start()

    def __exit__(self, *_args: object) -> None:
        self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="启动严格loopback事实编辑界面")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    server = LoopbackEditServer(UserFactEditService(args.project), port=args.port)
    print(f"http://127.0.0.1:{server.port}", flush=True)
    try:
        server._httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server._httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
