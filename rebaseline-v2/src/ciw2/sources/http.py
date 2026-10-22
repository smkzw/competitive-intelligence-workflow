"""统一抓取：所有外部内容先进 CAS、再登记 sources 表，之后才允许抽取。
- 原始字节与纯文本分别存 CAS（原文核验用纯文本）。
- 网络失败抛 FetchError；调用方必须把它记为「失败路线」，不能当作「无结果」。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, ClassVar

import httpx

from ciw2.harness.tools import ToolContext

UA = "ciw2/0.1 (clinical competitive-intelligence; single-user research tool)"


class FetchError(RuntimeError):
    pass


@dataclass
class Fetched:
    source_id: str | None
    url: str
    status: int
    content: bytes
    text: str
    content_type: str

    def json(self) -> Any:
        return json.loads(self.content)


class _TextExtractor(HTMLParser):
    SKIP: ClassVar[frozenset[str]] = frozenset({'script', 'style', 'noscript', 'svg'})

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self.SKIP:
            self._skip += 1
        elif tag in {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "td", "th"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    text = "".join(p.parts)
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def to_text(content: bytes, content_type: str) -> str:
    raw = content.decode("utf-8", errors="replace")
    if "html" in content_type or raw.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        return html_to_text(raw)
    return raw


def fetch(ctx: ToolContext | None, url: str, *, kind: str, params: dict[str, Any] | None = None,
          title: str = "", retries: int = 2, register: bool = True,
          client: httpx.Client | None = None) -> Fetched:
    timeout = getattr(getattr(ctx, "settings", None), "http_timeout_s", 30.0)
    last: Exception | None = None
    own = client is None
    client = client or httpx.Client(timeout=timeout, headers={"User-Agent": UA}, follow_redirects=True)
    try:
        for attempt in range(retries + 1):
            try:
                resp = client.get(url, params=params)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if resp.status_code >= 400:
                    raise FetchError(f"HTTP {resp.status_code} {resp.url}")
                ctype = resp.headers.get("content-type", "")
                text = to_text(resp.content, ctype)
                sid = None
                if register and ctx is not None and ctx.db is not None and ctx.cas is not None:
                    digest = ctx.cas.put(resp.content)
                    tdigest = ctx.cas.put(text.encode("utf-8"))
                    sid = ctx.db.add_source(ctx.project_id, kind, str(resp.url), digest, title=title,
                                            text_digest=tdigest, meta={"content_type": ctype})
                return Fetched(sid, str(resp.url), resp.status_code, resp.content, text, ctype)
            except httpx.HTTPError as exc:
                last = exc
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
        raise FetchError(f"{type(last).__name__}: {last} ({url})")
    finally:
        if own:
            client.close()


def register_text(ctx: ToolContext, *, kind: str, url: str, text: str, title: str = "",
                  raw: bytes | None = None, meta: dict[str, Any] | None = None) -> str | None:
    """把已获取的文本（如外部命令输出）登记为来源。"""
    if ctx.db is None or ctx.cas is None:
        return None
    digest = ctx.cas.put(raw if raw is not None else text.encode("utf-8"))
    tdigest = ctx.cas.put(text.encode("utf-8"))
    return ctx.db.add_source(ctx.project_id, kind, url, digest, title=title, text_digest=tdigest,
                             meta=meta or {})


def source_text(ctx: ToolContext, source_id: str) -> str | None:
    row = ctx.db.one("SELECT text_digest FROM sources WHERE id=?", (source_id,))
    if not row or not row["text_digest"]:
        return None
    return ctx.cas.get_text(row["text_digest"])


def source_by_url(ctx: ToolContext, url: str) -> dict[str, Any] | None:
    return ctx.db.one("SELECT * FROM sources WHERE project_id=? AND url=? ORDER BY fetched_at DESC",
                      (ctx.project_id, url))
