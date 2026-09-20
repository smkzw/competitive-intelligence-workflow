"""Bounded CT.gov v2 acquisition; pagination completion is not universe closure.

This endpoint returns current records, not historical as-of reconstructions.
Official interface: https://clinicaltrials.gov/data-api/api
No cookies, authentication, alternate hosts or implicit retries are used.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict

from ci_workflow.domain.evidence import ContentBlob, CtgovRecordSelector, SourceTextDerivation
from ci_workflow.sources.connectors.clinicaltrials_gov import (
    ClinicalTrialsGovCapture,
    ClinicalTrialsGovStudyVersion,
    build_next_page_url,
)
from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    capture_source_text,
    source_json_decoder,
)

API = "https://clinicaltrials.gov/api/v2/studies"
FetchStatus = Literal[
    "complete", "no_records", "incomplete", "network_error", "rate_limited",
    "access_denied", "invalid_response",
]


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
        self, req: Request, fp: Any, code: int, msg: str,
        headers: Any, newurl: str,
    ) -> None:
        return None


def _download(url: str, timeout: float, max_bytes: int) -> HttpPage:
    request = Request(url, headers={
        "Accept": "application/json", "User-Agent": "CI-Workflow/1.4 public-research",
    })
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            return HttpPage(
                response.status, response.headers.get_content_type(),
                response.read(max_bytes + 1), response.geturl(),
            )
    except HTTPError as error:
        # Do not log or persist a server's error/authentication page.
        status = error.code
        error.close()
        return HttpPage(status, "", b"", url)


class CapturedPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    page_number: int
    request_url: str
    acquired_at: datetime
    raw_asset: ContentBlob
    study_ids: tuple[str, ...]


class CtgovFetchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    condition: str
    status: FetchStatus
    pagination_complete: bool
    universe_closed: Literal[False] = False
    temporal_scope: Literal["current_records"] = "current_records"
    total_count: int | None
    studies: tuple[ClinicalTrialsGovStudyVersion, ...]
    pages: tuple[CapturedPage, ...]
    diagnostic: str


def fetch_ctgov_condition(
    project_root: Path,
    condition: str,
    *,
    page_size: int = 100,
    max_pages: int = 1000,
    timeout: float = 30,
    max_page_bytes: int = 20 * 1024 * 1024,
    max_total_bytes: int = 128 * 1024 * 1024,
    transport: Transport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> CtgovFetchResult:
    """Fetch every cursor page, retaining partial evidence on any failure.

    Resource limits are failures, never Top-N success. Caller owns recovery,
    alias expansion, historical reconstruction and independent review.
    """
    condition = condition.strip()
    if not condition or len(condition) > 4000 or any(ord(char) < 32 for char in condition):
        raise ValueError("检索条件必须是非空、有界的公开研究条件")
    if not 1 <= page_size <= 1000 or max_pages < 1 or not 0 < timeout <= 60:
        raise ValueError("分页大小、页数或超时配置无效")
    if max_page_bytes < 1 or max_total_bytes < 1:
        raise ValueError("获取字节预算必须为正")
    url = API + "?" + urlencode({
        "query.cond": condition, "format": "json", "pageSize": page_size, "countTotal": "true",
    })
    download = transport or _download
    store = ContentAddressedStore(project_root)
    studies: dict[str, ClinicalTrialsGovStudyVersion] = {}
    pages: list[CapturedPage] = []
    tokens: set[str] = set()
    total: int | None = None
    platform_holder: str | None = None
    byte_count = 0

    def finish(status: FetchStatus, diagnostic: str) -> CtgovFetchResult:
        return CtgovFetchResult(
            condition=condition, status=status,
            pagination_complete=status in {"complete", "no_records"},
            total_count=total, studies=tuple(studies.values()), pages=tuple(pages),
            diagnostic=diagnostic,
        )

    for page_number in range(1, max_pages + 1):
        remaining = min(max_page_bytes, max_total_bytes - byte_count)
        if remaining <= 0:
            return finish("incomplete", "获取字节预算已耗尽；必须恢复，不能认定检索完成")
        try:
            response = download(url, timeout, remaining)
        except (OSError, URLError, TimeoutError):
            return finish("network_error", "公开接口网络获取失败；不是无数据")
        if response.status == 429:
            return finish("rate_limited", "接口限流；需按来源恢复策略重试")
        if response.status in {401, 403}:
            return finish("access_denied", "公开接口拒绝访问；不能当作无记录")
        if response.status >= 500:
            return finish("network_error", "来源服务暂不可用；不能当作无记录")
        if response.status != 200 or response.final_url != url:
            return finish("invalid_response", "接口状态或重定向不符合限定来源合同")
        if len(response.body) > remaining:
            return finish("incomplete", "响应超出获取预算；未保存截断正文")
        if response.content_type.split(";", 1)[0].strip().lower() != "application/json":
            return finish("invalid_response", "来源未返回JSON；不接纳错误页作为临床数据")
        acquired_at = clock()
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise ValueError("获取时钟必须有明确时区")
        try:
            payload = source_json_decoder().decode(response.body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("response must be an object")
            capture = ClinicalTrialsGovCapture.from_api_payload(
                payload, acquired_at=acquired_at.isoformat(),
            )
            # CT.gov returns countTotal on page one, omitting it on cursor pages.
            count = payload.get("totalCount", total)
            if type(count) is not int or count < 0:
                raise ValueError("countTotal response must contain a nonnegative totalCount")
            token = payload.get("nextPageToken")
            if token is not None and (not isinstance(token, str) or not token.strip()):
                raise ValueError("cursor must be a nonempty string")
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return finish("invalid_response", "来源JSON缺少有效记录、计数或分页字段")
        raw = store.put_bytes(response.body, media_type="application/json")
        pages.append(CapturedPage(
            page_number=page_number, request_url=url, acquired_at=acquired_at,
            raw_asset=raw, study_ids=tuple(study.nct_id for study in capture.studies),
        ))
        byte_count += len(response.body)
        if total is not None and total != count:
            return finish("incomplete", "分页期间来源总量变化，需重新核查集合")
        total = count
        for study in capture.studies:
            if platform_holder is not None and platform_holder != study.platform_version_holder:
                return finish("incomplete", "分页期间登记平台版本变化；需重新获取一致集合")
            platform_holder = study.platform_version_holder
            previous = studies.get(study.nct_id)
            if previous is not None and previous.source_version_id != study.source_version_id:
                return finish("incomplete", "分页期间同一登记记录发生版本冲突")
            studies[study.nct_id] = study
        if capture.next_page_token is None:
            if len(studies) != total:
                return finish("incomplete", "终页唯一登记数与来源声明总数不一致")
            return finish(
                "complete" if studies else "no_records", "当前查询分页已核对；非竞品宇宙闭包",
            )
        if capture.next_page_token in tokens:
            return finish("incomplete", "重复分页游标；防止循环及虚假完成")
        tokens.add(capture.next_page_token)
        url = build_next_page_url(url, capture.next_page_token)
    return finish("incomplete", "页数预算已耗尽；保留部分证据并等待恢复")


class DerivedCtgovStudy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    nct_id: str
    title: str
    record_url: str
    registry_posted_version_date: str
    registry_posted_date_precision: Literal["calendar_day"] = "calendar_day"
    temporal_scope: Literal["current_record"] = "current_record"
    acquired_at: datetime
    content_text: str
    text_derivation: SourceTextDerivation


def derive_ctgov_records(
    project_root: Path, result: CtgovFetchResult,
) -> tuple[DerivedCtgovStudy, ...]:
    """Reopen the whole cursor chain, then extract exact per-record JSON slices.

    Publication-date precision is retained; no midnight instant is invented.
    This does not assign scientific claims, approve a report, or close a universe.
    """
    if not result.pagination_complete or result.status not in {"complete", "no_records"}:
        raise SourceDerivationError("分页尚未完成；原始部分证据保留但不能晋级完整记录集")
    if not result.pages:
        raise SourceDerivationError("获取结果没有可重开的原始响应")
    store = ContentAddressedStore(project_root)
    page_index = 0

    def replay(url: str, timeout: float, max_bytes: int) -> HttpPage:
        nonlocal page_index
        if page_index >= len(result.pages):
            raise SourceDerivationError("原始分页链尚未到终页")
        page = result.pages[page_index]
        page_index += 1
        if page.request_url != url or page.page_number != page_index:
            raise SourceDerivationError("分页请求条件或顺序与回执不一致")
        return HttpPage(200, page.raw_asset.media_type, store.read_bytes(page.raw_asset), url)

    try:
        query = parse_qs(urlsplit(result.pages[0].request_url).query)
        size = query.get("pageSize", [])
        if len(size) != 1:
            raise SourceDerivationError("获取回执缺少唯一分页大小")
        verified = fetch_ctgov_condition(
            project_root, result.condition, page_size=int(size[0]),
            max_pages=len(result.pages), transport=replay,
            clock=lambda: result.pages[page_index - 1].acquired_at,
        )
        if (
            page_index != len(result.pages) or not verified.pagination_complete
            or verified.status != result.status or verified.total_count != result.total_count
            or verified.studies != result.studies or verified.pages != result.pages
        ):
            raise SourceDerivationError("获取回执与实际原始响应、版本或总量不一致")
        records: dict[str, DerivedCtgovStudy] = {}
        for page in verified.pages:
            raw = store.read_bytes(page.raw_asset)
            capture = ClinicalTrialsGovCapture.from_api_payload(
                json.loads(raw), acquired_at=page.acquired_at.isoformat(),
            )
            for index, study in enumerate(capture.studies):
                date.fromisoformat(study.registry_posted_version_date)
                text, receipt = capture_source_text(
                    project_root, raw, media_type="application/json",
                    record_selector=CtgovRecordSelector(study_index=index, nct_id=study.nct_id),
                )
                records[study.nct_id] = DerivedCtgovStudy(
                    nct_id=study.nct_id, title=study.title, record_url=study.record_url,
                    registry_posted_version_date=study.registry_posted_version_date,
                    acquired_at=study.acquired_at, content_text=text, text_derivation=receipt,
                )
        return tuple(records.values())
    except (OSError, ContentIntegrityError, ValueError) as error:
        raise SourceDerivationError("原始分页证据无法支持当前记录集投影") from error
