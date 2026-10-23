"""统一抓取：所有外部内容先进 CAS、再登记 sources 表，之后才允许抽取。
- 原始字节与纯文本分别存 CAS（原文核验用纯文本）。
- 网络失败抛 FetchError；调用方必须把它记为「失败路线」，不能当作「无结果」。
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
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
    meta: dict[str,Any] = field(default_factory=dict)

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
    if is_pdf(content,content_type):
        from ciw2.sources.pdf_text import parse_pdf
        return parse_pdf(content).text
    raw = content.decode("utf-8", errors="replace")
    if "html" in content_type or raw.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        return html_to_text(raw)
    return raw


def is_pdf(content: bytes,content_type: str) -> bool:
    return 'pdf' in content_type.casefold() or b'%PDF-' in content[:1024]


def _document_text(ctx: ToolContext | None,body: bytes,ctype: str,url: str,kind: str) -> tuple[str,dict[str,Any],str]:
    if not is_pdf(body,ctype):return to_text(body,ctype),{'content_type':ctype},'decoded'
    from ciw2.sources.pdf_text import parse_pdf, parser_identity
    parser_id=parser_identity()
    if ctx is not None and ctx.db is not None and ctx.cas is not None:
        rows=ctx.db.query('SELECT text_digest,meta FROM sources WHERE project_id=? AND kind=? AND url=? '
            "AND digest=? AND text_digest IS NOT NULL AND json_extract(meta,'$.text_parser_id')=? ORDER BY rowid DESC",
            (ctx.project_id,kind,public_url(url),hashlib.sha256(body).hexdigest(),parser_id))
        for source in rows:
            try:text=ctx.cas.get(source['text_digest'])
            except OSError:continue
            if hashlib.sha256(text).hexdigest()==source['text_digest']:
                return text.decode('utf-8'),json.loads(source['meta']),'reused'
    result=parse_pdf(body)
    return result.text,{'content_type':ctype,'text_state':'parsed','text_parser_id':result.parser_id,
        'text_parser_version':result.parser_version,'pages':result.pages},'parsed'


def _cached(ctx: ToolContext,key: tuple[Any,...],cache: dict[Any,Any]) -> Fetched | None:
    source=ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                      (cache[key],ctx.project_id,key[1]))
    if not source or not source['text_digest']:return None
    try:
        raw=ctx.cas.get(source['digest']);text=ctx.cas.get(source['text_digest'])
    except OSError:return None
    if hashlib.sha256(raw).hexdigest()!=source['digest'] or hashlib.sha256(text).hexdigest()!=source['text_digest']:
        return None
    meta=json.loads(source['meta'])
    if is_pdf(raw,meta.get('content_type','')):
        from ciw2.sources.pdf_text import PDFTextError, parser_identity
        try:current=parser_identity()
        except PDFTextError:return None
        if meta.get('text_parser_id')!=current:return None
    _observe(ctx,source['id']);_receipt(ctx,source['id'],'cache_reused',source['url'])
    return Fetched(source['id'],source['url'],None,raw,text.decode('utf-8'),meta.get('content_type',''),
                   mode='cache_reused',meta=meta)


def _received(ctx: ToolContext | None,resp: httpx.Response,kind: str,title: str,register: bool) -> Fetched:
    ctype=resp.headers.get('content-type','');url=public_url(str(resp.url))
    persistent=register and ctx is not None and ctx.db is not None and ctx.cas is not None
    digest=ctx.cas.put(resp.content) if persistent else None
    from ciw2.sources.pdf_text import PDFTextError
    try:text,meta,parse_mode=_document_text(ctx if persistent else None,resp.content,ctype,url,kind)
    except PDFTextError as exc:
        reason=getattr(exc,'reason','parser_failed')
        reason=reason if isinstance(reason,str) and re.fullmatch(r'[a-z_]{1,40}',reason) else 'parser_failed'
        if persistent:
            sid=ctx.db.add_source(ctx.project_id,kind,url,digest,title=title,
                meta={'content_type':ctype,'text_state':'failed','text_error':reason})
            _receipt(ctx,sid,'network_checked',url,resp.status_code)
            ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_parse',
                {'source_id':sid,'state':'failed','reason':reason})
        raise FetchError(f'PDF文本解析失败（{reason}），原始来源未作临床事实采用') from None
    sid=None;checked_at=datetime.now(UTC).isoformat()
    if persistent:
        sid=ctx.db.add_source(ctx.project_id,kind,url,digest,title=title,
            text_digest=ctx.cas.put(text.encode('utf-8')),meta=meta)
        checked_at=_receipt(ctx,sid,'network_checked',url,resp.status_code)
        if is_pdf(resp.content,ctype):
            ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_parse',
                {'source_id':sid,'state':'parsed','mode':parse_mode,'text_parser_id':meta['text_parser_id']})
    _observe(ctx,sid)
    return Fetched(sid,url,resp.status_code,resp.content,text,ctype,mode='network_checked',
                   network_checked_at=checked_at,meta=meta)


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
        cached=_cached(ctx,key,cache)
        if cached:return cached
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
                result=_received(ctx,resp,kind,title,register)
                if cache is not None:cache[key]=result.source_id
                return result
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


def source_by_url(ctx: ToolContext, url: str, *, request_context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    url = public_url(url)
    candidates = ctx.db.query("SELECT s.* FROM agent_steps a JOIN sources s "
                     "ON s.id=json_extract(a.content,'$.source_id') "
                     "WHERE a.role='source_observation' AND s.project_id=? AND s.url=? "
                     "AND json_extract(a.content,'$.mode') IN ('network_checked','imported') "
                     "ORDER BY a.id DESC", (ctx.project_id, url))
    def matches(source: dict[str, Any]) -> bool:
        return request_context is None or json.loads(source['meta']).get('request_context') == request_context
    row = next((source for source in candidates if matches(source)),None)
    if row is None:  # Read-only compatibility for evidence captured before observation receipts.
        candidates = ctx.db.query("SELECT * FROM sources WHERE project_id=? AND url=? ORDER BY fetched_at DESC, rowid DESC",
                                  (ctx.project_id, url))
        row = next((source for source in candidates if matches(source)),None)
    if row:
        _observe(ctx, row['id'])
    return row
