"""Bounded PubMed E-utilities acquisition; pagination is not universe closure.

This route returns current records, not historical as-of reconstructions.
Official interface: https://www.ncbi.nlm.nih.gov/books/NBK25501/
No cookies, authentication, alternate hosts, implicit retries or web environments are used.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.pubmed import (
    PubMedRecord,
    build_pubmed_nct_search_url,
    parse_pubmed_efetch_xml,
)
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import source_json_decoder

_EFETCH_AVAILABLE_STATES = frozenset({"pubmed", "aheadofprint"})

FetchStatus = Literal[
    "complete", "complete_with_attrition", "no_records", "incomplete",
    "network_error", "rate_limited", "access_denied", "invalid_response",
]
_JSON_MEDIA = "application/json"
_XML_MEDIA_TYPES = {"application/xml", "text/xml"}


class PubMedFetchError(RuntimeError):
    """PubMed 获取失败的共同基类：每类失败都有独立类型和独立状态。"""

    status: ClassVar[FetchStatus] = "invalid_response"

    def __init__(self, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.diagnostic = diagnostic


class PubMedTimeoutError(PubMedFetchError):
    """请求超时。"""

    status: ClassVar[FetchStatus] = "network_error"


class PubMedNetworkError(PubMedFetchError):
    """连接或传输失败。"""

    status: ClassVar[FetchStatus] = "network_error"


class PubMedHttpError(PubMedFetchError):
    """非预期 HTTP 状态。"""

    status: ClassVar[FetchStatus] = "invalid_response"

    def __init__(self, code: int, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.code = code


class PubMedRateLimitedError(PubMedHttpError):
    """429 限流。"""

    status: ClassVar[FetchStatus] = "rate_limited"


class PubMedAccessDeniedError(PubMedHttpError):
    """401/403 拒绝访问。"""

    status: ClassVar[FetchStatus] = "access_denied"


class PubMedServerError(PubMedHttpError):
    """5xx 来源服务不可用。"""

    status: ClassVar[FetchStatus] = "network_error"


class PubMedMalformedResponseError(PubMedFetchError):
    """JSON、XML、媒体类型或重定向不符合限定来源合同。"""

    status: ClassVar[FetchStatus] = "invalid_response"


class PubMedEmptyResultError(PubMedFetchError):
    """来源确认当前检索式零记录：这是结果状态，不是失败。"""

    status: ClassVar[FetchStatus] = "no_records"


@dataclass(frozen=True)
class HttpPage:
    status: int
    content_type: str
    body: bytes
    final_url: str


class Transport(Protocol):
    def __call__(self, url: str, timeout: float, max_bytes: int) -> HttpPage: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str,
    ) -> None:
        return None


def _download(url: str, timeout: float, max_bytes: int) -> HttpPage:
    """Bounded single request; a server error page is classified but never retained."""
    request = Request(url, headers={
        "Accept": "application/json, application/xml, text/xml",
        "User-Agent": "CI-Workflow/1.4 public-research",
    })
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            return HttpPage(
                response.status, response.headers.get_content_type(),
                response.read(max_bytes + 1), response.geturl(),
            )
    except HTTPError as error:
        # Do not log or persist a server's error or authentication page.
        code = error.code
        error.close()
        return HttpPage(code, "", b"", url)
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise PubMedTimeoutError("公开接口请求超时；不是无数据") from error
        raise PubMedNetworkError("公开接口网络获取失败；不是无数据") from error
    except TimeoutError as error:
        raise PubMedTimeoutError("公开接口请求超时；不是无数据") from error
    except OSError as error:
        raise PubMedNetworkError("公开接口网络获取失败；不是无数据") from error


def _classify_status(status: int, *, context: str) -> None:
    """Turn every non-200 status into its own typed failure; 200 is the only success."""
    if status == 200:
        return
    if status == 429:
        raise PubMedRateLimitedError(status, f"{context}被来源限流；需按来源恢复策略重试")
    if status in {401, 403}:
        raise PubMedAccessDeniedError(status, f"{context}被公开接口拒绝；不能当作无记录")
    if status >= 500:
        raise PubMedServerError(status, f"{context}时来源服务暂不可用；不能当作无记录")
    raise PubMedHttpError(status, f"{context}返回非预期状态；不能当作无记录")


# pubmed.py owns the canonical E-utilities route (endpoint, db, retmode); deriving the root
# from it keeps this module from re-declaring the same source address.
_ESEARCH = urlsplit(build_pubmed_nct_search_url("NCT00000001"))
_EUTILS_ROOT = urlunsplit(
    (_ESEARCH.scheme, _ESEARCH.netloc, _ESEARCH.path.rsplit("/", 1)[0], "", "")
)
_SEARCH_DEFAULTS = {
    key: values[0] for key, values in parse_qs(_ESEARCH.query).items() if key != "term"
}


def build_pubmed_term_search_url(term: str, *, retstart: int, retmax: int) -> str:
    """Search URL: only the term and the retstart/retmax cursor are supplied here."""
    params = {**_SEARCH_DEFAULTS, "term": term, "retstart": str(retstart), "retmax": str(retmax)}
    return f"{_EUTILS_ROOT}/esearch.fcgi?{urlencode(params)}"


def build_pubmed_summary_url(pmids: tuple[str, ...]) -> str:
    from urllib.parse import urlencode

    params = urlencode({"db": "pubmed", "id": ",".join(pmids), "retmode": "json"})
    return f"{_EUTILS_ROOT}/esummary.fcgi?{params}"


def build_pubmed_records_url(pmids: tuple[str, ...]) -> str:
    """Record URL for one exact identifier batch; no history or web environment is used."""
    if not pmids:
        raise ValueError("记录获取需要至少一个 PubMed 标识")
    params = {
        "db": _SEARCH_DEFAULTS["db"],
        "retmode": "xml",
        "rettype": "abstract",
        "id": ",".join(pmids),
    }
    return f"{_EUTILS_ROOT}/efetch.fcgi?{urlencode(params)}"


@dataclass(frozen=True)
class _SearchPage:
    total: int
    pmids: tuple[str, ...]


def _as_nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise PubMedMalformedResponseError(f"检索响应字段 {field} 不是非负整数")
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise PubMedMalformedResponseError(f"检索响应字段 {field} 不是非负整数")


def _parse_search_page(body: bytes, *, offset: int) -> _SearchPage:
    """Parse one search page; a rejected query or a repeated cursor is never an empty set."""
    try:
        payload = source_json_decoder().decode(body.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise PubMedMalformedResponseError("检索响应不是有效 JSON；不能当作无记录") from error
    if not isinstance(payload, dict):
        raise PubMedMalformedResponseError("检索响应缺少结果对象；不能当作无记录")
    result = payload.get("esearchresult")
    if not isinstance(result, dict):
        raise PubMedMalformedResponseError("检索响应缺少 esearchresult；不能当作无记录")
    if "ERROR" in result or "error" in result:
        raise PubMedMalformedResponseError("来源拒绝该检索式；不是无记录")
    total = _as_nonnegative_int(result.get("count"), "count")
    if _as_nonnegative_int(result.get("retstart"), "retstart") != offset:
        raise PubMedMalformedResponseError("来源回执的检索游标与请求不一致；防止循环及虚假完成")
    raw_ids = result.get("idlist")
    if not isinstance(raw_ids, list):
        raise PubMedMalformedResponseError("检索响应缺少标识列表；不能当作无记录")
    pmids: list[str] = []
    for item in raw_ids:
        if not isinstance(item, str) or not item.strip().isdigit():
            raise PubMedMalformedResponseError("检索响应包含无效标识；不能当作无记录")
        pmids.append(item.strip())
    if len(set(pmids)) != len(pmids):
        raise PubMedMalformedResponseError("检索响应包含重复标识；需重新核查集合")
    if total == 0:
        raise PubMedEmptyResultError("来源确认该检索式当前无记录；原始空响应已留存")
    return _SearchPage(total=total, pmids=tuple(pmids))


def _parse_record_page(body: bytes) -> tuple[PubMedRecord, ...]:
    """Parse one record document; malformed XML and error documents are never empty sets."""
    try:
        text = body.decode("utf-8")
    except UnicodeError as error:
        raise PubMedMalformedResponseError("记录响应不是 UTF-8 XML；不能当作无记录") from error
    if "<ERROR>" in text:
        raise PubMedMalformedResponseError("来源返回错误文档；不是无记录")
    try:
        return parse_pubmed_efetch_xml(text)
    except ValueError as error:
        raise PubMedMalformedResponseError("PubMed 记录 XML 无法解析；不能当作无记录") from error


class CapturedPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    page_number: int
    request_url: str
    acquired_at: datetime
    raw_asset: ContentBlob
    pmids: tuple[str, ...]


class AttritionRecord(BaseModel):
    """efetch 未返回但经 esummary 分类解释的标识；不是已获取记录。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pmid: str
    state: str
    detail_zh: str = ""


class PubMedFetchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    query: str
    status: FetchStatus
    pagination_complete: bool
    universe_closed: Literal[False] = False
    temporal_scope: Literal["current_records"] = "current_records"
    acquired_at: datetime
    total_count: int | None
    records: tuple[PubMedRecord, ...]
    search_pages: tuple[CapturedPage, ...]
    record_pages: tuple[CapturedPage, ...]
    summary_pages: tuple[CapturedPage, ...] = ()
    attrition: tuple[AttritionRecord, ...] = ()
    diagnostic: str


def _require_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("获取时钟必须有明确时区")
    return moment


def fetch_pubmed_results(
    project_root: Path,
    query: str,
    *,
    page_size: int = 200,
    max_pages: int = 1000,
    timeout: float = 30,
    max_page_bytes: int = 20 * 1024 * 1024,
    max_total_bytes: int = 128 * 1024 * 1024,
    efetch_batch_size: int = 200,
    transport: Transport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> PubMedFetchResult:
    """Fetch the search cursor and every record page, retaining partial evidence on failure.

    Resource limits are failures, never Top-N success. Caller owns recovery, publication-role
    judgement, universe closure and independent review.
    """
    query = query.strip()
    if not query or len(query) > 4000 or any(ord(char) < 32 for char in query):
        raise ValueError("检索式必须是非空、有界的公开检索条件")
    if not 1 <= page_size <= 10000 or max_pages < 1 or not 0 < timeout <= 60:
        raise ValueError("分页大小、页数或超时配置无效")
    if not 1 <= efetch_batch_size <= 1000:
        raise ValueError("记录批大小配置无效")
    if max_page_bytes < 1 or max_total_bytes < 1:
        raise ValueError("获取字节预算必须为正")
    download = transport or _download
    store = ContentAddressedStore(project_root)
    acquired_at = _require_aware(clock())
    search_pages: list[CapturedPage] = []
    record_pages: list[CapturedPage] = []
    records: dict[str, PubMedRecord] = {}
    pmids: list[str] = []
    seen: set[str] = set()
    total: int | None = None
    byte_count = 0

    def finish(status: FetchStatus, diagnostic: str) -> PubMedFetchResult:
        return PubMedFetchResult(
            query=query, status=status,
            pagination_complete=status in {
                "complete", "complete_with_attrition", "no_records",
            },
            acquired_at=acquired_at, total_count=total, records=tuple(records.values()),
            search_pages=tuple(search_pages), record_pages=tuple(record_pages),
            diagnostic=diagnostic,
        )

    offset = 0
    for page_number in range(1, max_pages + 1):
        remaining = min(max_page_bytes, max_total_bytes - byte_count)
        if remaining <= 0:
            return finish("incomplete", "获取字节预算已耗尽；必须恢复，不能认定检索完成")
        url = build_pubmed_term_search_url(query, retstart=offset, retmax=page_size)
        try:
            response = download(url, timeout, remaining)
        except PubMedFetchError as error:
            return finish(error.status, error.diagnostic)
        except OSError:
            return finish("network_error", "公开接口网络获取失败；不是无数据")
        try:
            _classify_status(response.status, context="PubMed 检索")
            if response.final_url != url:
                raise PubMedMalformedResponseError("接口状态或重定向不符合限定来源合同")
            if len(response.body) > remaining:
                return finish("incomplete", "响应超出获取预算；未保存截断正文")
            if response.content_type.split(";", 1)[0].strip().lower() != _JSON_MEDIA:
                raise PubMedMalformedResponseError("来源未返回JSON；不接纳错误页作为检索结果")
            acquired = _require_aware(clock())
            page = _parse_search_page(response.body, offset=offset)
        except PubMedEmptyResultError as error:
            raw = store.put_bytes(response.body, media_type=_JSON_MEDIA)
            search_pages.append(CapturedPage(
                page_number=page_number, request_url=url, acquired_at=acquired,
                raw_asset=raw, pmids=(),
            ))
            total = 0
            return finish("no_records", error.diagnostic)
        except PubMedFetchError as error:
            return finish(error.status, error.diagnostic)
        raw = store.put_bytes(response.body, media_type=_JSON_MEDIA)
        search_pages.append(CapturedPage(
            page_number=page_number, request_url=url, acquired_at=acquired,
            raw_asset=raw, pmids=page.pmids,
        ))
        byte_count += len(response.body)
        if total is not None and total != page.total:
            return finish("incomplete", "检索期间来源总量变化，需重新核查集合")
        total = page.total
        fresh = tuple(pmid for pmid in page.pmids if pmid not in seen)
        if page.pmids and not fresh:
            return finish("incomplete", "来源重复返回同一分页游标；防止循环及虚假完成")
        seen.update(fresh)
        pmids.extend(fresh)
        if not page.pmids:
            return finish("incomplete", "来源声明总数与返回标识不一致；不能认定检索完成")
        offset += len(page.pmids)
        if len(pmids) >= total:
            break
    else:
        return finish("incomplete", "页数预算已耗尽；保留部分证据并等待恢复")
    if len(pmids) != total:
        return finish("incomplete", "来源声明总数与返回标识不一致；不能认定检索完成")

    for batch_number, start in enumerate(range(0, len(pmids), efetch_batch_size), start=1):
        batch = tuple(pmids[start:start + efetch_batch_size])
        remaining = min(max_page_bytes, max_total_bytes - byte_count)
        if remaining <= 0:
            return finish("incomplete", "获取字节预算已耗尽；必须恢复，不能认定检索完成")
        url = build_pubmed_records_url(batch)
        try:
            response = download(url, timeout, remaining)
        except PubMedFetchError as error:
            return finish(error.status, error.diagnostic)
        except OSError:
            return finish("network_error", "公开接口网络获取失败；不是无数据")
        try:
            _classify_status(response.status, context="PubMed 记录")
            if response.final_url != url:
                raise PubMedMalformedResponseError("接口状态或重定向不符合限定来源合同")
            if len(response.body) > remaining:
                return finish("incomplete", "响应超出获取预算；未保存截断正文")
            if response.content_type.split(";", 1)[0].strip().lower() not in _XML_MEDIA_TYPES:
                raise PubMedMalformedResponseError("来源未返回XML；不接纳错误页作为论文记录")
            acquired = _require_aware(clock())
            batch_records = _parse_record_page(response.body)
        except PubMedFetchError as error:
            return finish(error.status, error.diagnostic)
        raw = store.put_bytes(response.body, media_type="application/xml")
        record_pages.append(CapturedPage(
            page_number=batch_number, request_url=url, acquired_at=acquired,
            raw_asset=raw, pmids=batch,
        ))
        byte_count += len(response.body)
        returned = tuple(record.pmid for record in batch_records)
        if len(set(returned)) != len(returned):
            return finish("invalid_response", "记录响应包含重复标识；需重新获取一致集合")
        for record in batch_records:
            previous = records.get(record.pmid)
            if previous is not None and previous != record:
                return finish("incomplete", "同一标识的记录内容冲突；需重新获取一致集合")
            records[record.pmid] = record
    # G8-1：efetch 属性差（非 PubMed 中央库/在处理/已删除标识永不返回）经
    # esummary 逐批分类解释；已解释的属性=完成（complete_with_attrition），
    # 不可解释的缺失仍是截断。不冒充完整记录集，attrition 单列。
    attrition: list[AttritionRecord] = []
    summary_pages_local: list[CapturedPage] = []
    missing = [pmid for pmid in pmids if pmid not in records]
    unclassified: list[str] = []
    for batch_number, start in enumerate(
        range(0, len(missing), efetch_batch_size), start=1,
    ):
        batch = tuple(missing[start:start + efetch_batch_size])
        if not batch:
            break
        remaining = min(max_page_bytes, max_total_bytes - byte_count)
        if remaining <= 0:
            return finish("incomplete", "获取字节预算已耗尽；必须恢复，不能认定检索完成")
        url = build_pubmed_summary_url(batch)
        try:
            response = download(url, timeout, remaining)
        except PubMedFetchError as error:
            return finish(error.status, error.diagnostic)
        except OSError:
            return finish("network_error", "公开接口网络获取失败；不是无数据")
        try:
            _classify_status(response.status, context="PubMed 摘要回落")
            if response.final_url != url:
                raise PubMedMalformedResponseError("接口状态或重定向不符合限定来源合同")
            if len(response.body) > remaining:
                return finish("incomplete", "响应超出获取预算；未保存截断正文")
            if response.content_type.split(";", 1)[0].strip().lower() != _JSON_MEDIA:
                raise PubMedMalformedResponseError("来源未返回JSON；不接纳错误页作为摘要回落")
            acquired = _require_aware(clock())
            payload = json.loads(response.body.decode("utf-8"))
            results = payload.get("result")
            if not isinstance(results, dict):
                raise PubMedMalformedResponseError("摘要回落缺少 result 结构")
        except PubMedFetchError as error:
            return finish(error.status, error.diagnostic)
        except (UnicodeDecodeError, ValueError):
            return finish("invalid_response", "摘要回落响应不是合法JSON")
        raw = store.put_bytes(response.body, media_type=_JSON_MEDIA)
        summary_pages_local.append(CapturedPage(
            page_number=batch_number, request_url=url, acquired_at=acquired,
            raw_asset=raw, pmids=batch,
        ))
        byte_count += len(response.body)
        for pmid in batch:
            entry = results.get(pmid)
            if isinstance(entry, dict) and entry.get("uid") == pmid:
                state = str(entry.get("pubstatus") or "unknown")
                if state in _EFETCH_AVAILABLE_STATES:
                    # esummary 显示可获取却未被 efetch 返回：真截断，不是属性。
                    unclassified.append(pmid)
                else:
                    attrition.append(AttritionRecord(
                        pmid=pmid, state=state,
                        detail_zh="efetch 未返回该标识；esummary 状态已分类",
                    ))
            else:
                unclassified.append(pmid)
    if unclassified:
        return finish(
            "incomplete",
            f"有标识既不在 efetch 也不在 esummary 结果中，无法解释：{unclassified[:5]}",
        )
    if attrition:
        states: dict[str, int] = {}
        for item in attrition:
            states[item.state] = states.get(item.state, 0) + 1
        state_text = "、".join(f"{key}×{value}" for key, value in sorted(states.items()))
        result = finish(
            "complete_with_attrition",
            f"检索分页完整；efetch 返回 {len(records)} 条，另有 {len(attrition)} 个标识"
            f"经 esummary 分类为非可获取记录（{state_text}）。属性差异已解释，"
            "不代表论文—试验关系判定或竞品闭包",
        )
        return result.model_copy(update={
            "attrition": tuple(attrition),
            "summary_pages": tuple(summary_pages_local),
        })
    if len(records) != len(pmids):
        return finish("incomplete", "获取记录数与检索标识数不一致；不能认定检索完成")
    return finish("complete", "当前检索式分页与记录已核对；不代替论文—试验关系判定或竞品闭包")
