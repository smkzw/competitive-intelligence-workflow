"""统一抓取：所有外部内容先进 CAS、再登记 sources 表，之后才允许抽取。
- 原始字节与纯文本分别存 CAS（原文核验用纯文本）。
- 网络失败抛 FetchError；调用方必须把它记为「失败路线」，不能当作「无结果」。
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, ClassVar
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from ciw2.harness.tools import ToolContext

UA = "ciw2/0.1 (clinical competitive-intelligence; single-user research tool)"


class FetchError(RuntimeError):
    pass


def public_url(url: str) -> str:
    """Keep source identity parameters, never authentication material."""
    parsed = urlsplit(url)
    host = parsed.hostname or ''
    if ':' in host:
        host = f'[{host}]'
    if parsed.port is not None:
        host += f':{parsed.port}'
    public_cursor = parsed.hostname == 'clinicaltrials.gov' and parsed.path.rstrip('/') == '/api/v2/studies'
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
             if (public_cursor and key == 'pageToken') or (
                 key.lower() not in {'key', 'auth', 'authorization'} and not any(
                     marker in key.lower() for marker in ('token', 'password', 'signature', 'credential', 'api_key', 'apikey')))]
    return urlunsplit((parsed.scheme, host, parsed.path, urlencode(query), ''))


@dataclass
class Fetched:
    source_id: str | None
    url: str
    status: int | None
    content: bytes
    text: str
    content_type: str
    mode: str = 'unspecified'
    network_checked_at: str | None = None

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


def _observe(ctx: ToolContext | None, source_id: str | None) -> None:
    if ctx is not None and source_id:
        if ctx.extra is None:
            ctx.extra = {}
        ctx.extra.setdefault('source_ids_read', set()).add(source_id)


def _receipt(ctx: ToolContext, source_id: str, mode: str, url: str, status: int | None = None) -> str | None:
    """Content reuse is distinct from a new check of public availability."""
    checked_at = datetime.now(UTC).isoformat() if mode == 'network_checked' else None
    ctx.db.log_step(ctx.run_id, ctx.stage, 'source', 0, 'source_observation', {
        'project_id': ctx.project_id, 'source_id': source_id, 'mode': mode, 'url': public_url(url),
        'http_status': status,
        'network_checked_at': checked_at})
    return checked_at


def fetch(ctx: ToolContext | None, url: str, *, kind: str, params: dict[str, Any] | None = None,
          title: str = "", retries: int = 2, register: bool = True,
          client: httpx.Client | None = None) -> Fetched:
    cache = (ctx.extra or {}).get('fetch_cache') if ctx and register and ctx.db and ctx.cas else None
    request_url = httpx.URL(url) if params is None else httpx.URL(url, params=params)
    key = (getattr(ctx, 'project_id', None), kind, hashlib.sha256(str(request_url).encode()).hexdigest())
    if cache is not None and key in cache:
        source = ctx.db.one('SELECT * FROM sources WHERE id=?', (cache[key],))
        if source:
            _observe(ctx, source['id'])
            _receipt(ctx, source['id'], 'cache_reused', source['url'])
            return Fetched(source['id'], source['url'], None, ctx.cas.get(source['digest']),
                           ctx.cas.get_text(source['text_digest']), json.loads(source['meta']).get('content_type', ''),
                           mode='cache_reused')
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
                    raise FetchError(f"HTTP {resp.status_code} {public_url(str(resp.url))}")
                ctype = resp.headers.get("content-type", "")
                text = to_text(resp.content, ctype)
                sid = None
                checked_at = datetime.now(UTC).isoformat()
                if register and ctx is not None and ctx.db is not None and ctx.cas is not None:
                    digest = ctx.cas.put(resp.content)
                    tdigest = ctx.cas.put(text.encode("utf-8"))
                    sid = ctx.db.add_source(ctx.project_id, kind, public_url(str(resp.url)), digest, title=title,
                                            text_digest=tdigest, meta={"content_type": ctype})
                    if cache is not None:
                        cache[key] = sid
                    checked_at = _receipt(ctx, sid, 'network_checked', str(resp.url), resp.status_code)
                _observe(ctx, sid)
                return Fetched(sid, public_url(str(resp.url)), resp.status_code, resp.content, text, ctype,
                               mode='network_checked', network_checked_at=checked_at)
            except httpx.HTTPError as exc:
                last = exc
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
        raise FetchError(f"{type(last).__name__}: network request failed ({public_url(url)})")
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
    sid = ctx.db.add_source(ctx.project_id, kind, public_url(url), digest, title=title, text_digest=tdigest,
                            meta=meta or {})
    _observe(ctx, sid)
    _receipt(ctx, sid, 'imported', url)
    return sid


def source_text(ctx: ToolContext, source_id: str) -> str | None:
    row = ctx.db.one("SELECT text_digest FROM sources WHERE id=? AND project_id=?", (source_id, ctx.project_id))
    if not row or not row["text_digest"]:
        return None
    _observe(ctx, source_id)
    return ctx.cas.get_text(row["text_digest"])


def source_by_url(ctx: ToolContext, url: str) -> dict[str, Any] | None:
    url = public_url(url)
    row = ctx.db.one("SELECT s.* FROM agent_steps a JOIN sources s "
                     "ON s.id=json_extract(a.content,'$.source_id') "
                     "WHERE a.role='source_observation' AND s.project_id=? AND s.url=? "
                     "AND json_extract(a.content,'$.mode') IN ('network_checked','imported') "
                     "ORDER BY a.id DESC LIMIT 1", (ctx.project_id, url))
    if row is None:  # Read-only compatibility for evidence captured before observation receipts.
        row = ctx.db.one("SELECT * FROM sources WHERE project_id=? AND url=? ORDER BY fetched_at DESC, rowid DESC",
                         (ctx.project_id, url))
    if row:
        _observe(ctx, row['id'])
    return row
