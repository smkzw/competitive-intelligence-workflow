"""最小 HTTP 客户端：重试、超时、可选代理（环境变量 CIW_PROXY）。不引入 requests。"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "ciw/2 (competitive-intelligence research; contact via workbench owner)"


def _opener() -> urllib.request.OpenerDirector:
    proxy = os.environ.get("CIW_PROXY")
    handlers: list[urllib.request.BaseHandler] = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


def get_bytes(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 60,
    retries: int = 4,
    headers: dict[str, str] | None = None,
) -> bytes:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    opener = _opener()
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with opener.open(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            last = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
        time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"GET 失败（{retries} 次）：{url}") from last


def get_json(url: str, params: dict[str, Any] | None = None, **kw: Any) -> Any:
    return json.loads(get_bytes(url, params, **kw))
