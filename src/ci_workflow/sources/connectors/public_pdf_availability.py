"""Bounded official CT.gov large-document availability witness over the existing CAS.

One full public GET proves only that the pinned exact bytes were publicly
retrievable at the observation instant; it is never evidence of first
publication, posting, effective or historical availability, and it never
rewrites a source-version identity. Hosts are restricted to the official
clinicaltrials.gov document hosts; this adapter limit is not a global product
policy and other channels remain open. No credentials, cookies, query URLs,
implicit retries or unofficial redirects are used; failures stay scoped.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError

OFFICIAL_PDF_HOSTS = frozenset({"cdn.clinicaltrials.gov", "clinicaltrials.gov"})
PdfAvailabilityStatus = Literal[
    "available", "unavailable", "access_denied", "network_error", "mismatch",
    "invalid_response",
]


class PublicPdfAvailabilityError(ValueError):
    """官方 PDF 可用性见证或复核不能成立；失败必须封闭，不得伪造成功。"""


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("文本不能为空")
    return value.strip()


def _utc_instant(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含明确时区偏移")
    return value.astimezone(UTC)


def _require_official_pdf_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in OFFICIAL_PDF_HOSTS:
        raise PublicPdfAvailabilityError("仅支持 clinicaltrials.gov 官方域名的公开 HTTPS 附件")
    if parts.username is not None or parts.password is not None:
        raise PublicPdfAvailabilityError("官方附件 URL 不得包含用户凭据")
    try:
        explicit_port = parts.port
    except ValueError as error:
        raise PublicPdfAvailabilityError("官方附件 URL 端口无效") from error
    if explicit_port is not None:
        raise PublicPdfAvailabilityError("官方附件 URL 不得包含显式端口")
    if parts.query or parts.fragment:
        raise PublicPdfAvailabilityError("官方附件 URL 必须是精确路径，不含查询或片段")
    if not parts.path.lower().endswith(".pdf"):
        raise PublicPdfAvailabilityError("官方附件 URL 必须指向 PDF 附件路径")


def _require_cas_binding(blob: ContentBlob) -> None:
    digest = blob.sha256
    if blob.relative_path != f"evidence/raw/sha256/{digest[:2]}/{digest}.bin":
        raise PublicPdfAvailabilityError("原始资产路径必须与内容摘要绑定")
    if blob.byte_size < 1:
        raise PublicPdfAvailabilityError("原始资产不得为空")


def _require_pdf_media(blob: ContentBlob) -> None:
    if blob.media_type != "application/pdf":
        raise PublicPdfAvailabilityError("原始资产媒体类型必须是 application/pdf")


@dataclass(frozen=True)
class PdfHttpPage:
    status: int
    content_type: str
    content_length: int | None
    body: bytes
    final_url: str


class PdfTransport(Protocol):
    def __call__(self, url: str, timeout: float, max_bytes: int) -> PdfHttpPage: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: object, code: int, msg: str,
        headers: object, newurl: str,
    ) -> None:
        return None


def _download(url: str, timeout: float, max_bytes: int) -> PdfHttpPage:
    request = Request(url, headers={
        "Accept": "application/pdf", "User-Agent": "CI-Workflow/1.4 public-research",
    })
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            raw_length = response.headers.get("Content-Length")
            try:
                content_length = int(raw_length) if raw_length is not None else None
            except ValueError:
                content_length = None
            return PdfHttpPage(
                response.status, response.headers.get_content_type(), content_length,
                response.read(max_bytes + 1), response.geturl(),
            )
    except HTTPError as error:
        # Do not log or persist a server's error/authentication page.
        status = error.code
        error.close()
        return PdfHttpPage(status, "", None, b"", url)


class PublicPdfAvailabilityWitness(BaseModel):
    """一次官方附件当前可公开获取的实际观察；不是任何首次/发布/生效日期角色。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_url: str
    final_url: str
    request_started_at: datetime
    observed_available_at: datetime
    http_status: Literal[200] = 200
    content_type: str
    content_length: int | None = Field(default=None, ge=0)
    expected_raw_asset: ContentBlob
    raw_asset: ContentBlob
    receipt_asset: ContentBlob | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("request_url", "final_url", "content_type")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("request_started_at", "observed_available_at")
    @classmethod
    def _observation_is_aware(cls, value: datetime) -> datetime:
        return _utc_instant(value)

    @model_validator(mode="after")
    def _receipt_is_internally_consistent(self) -> PublicPdfAvailabilityWitness:
        if self.request_url != self.final_url:
            raise ValueError("请求地址与最终地址必须一致；不接受重定向")
        _require_official_pdf_url(self.request_url)
        if self.request_started_at > self.observed_available_at:
            raise ValueError("获取开始时刻不得晚于完成观察时刻")
        if self.content_type.split(";", 1)[0].strip().lower() != "application/pdf":
            raise ValueError("见证的响应媒体类型必须是 application/pdf")
        if self.content_length is not None and self.content_length != self.raw_asset.byte_size:
            raise ValueError("见证的响应长度与实际字节不一致")
        _require_cas_binding(self.raw_asset)
        _require_pdf_media(self.expected_raw_asset)
        if self.raw_asset != self.expected_raw_asset:
            raise PublicPdfAvailabilityError("见证原始资产必须与既有固定资产同址同字节")
        if self.receipt_asset is not None:
            _require_cas_binding(self.receipt_asset)
            if self.receipt_asset.media_type != "application/json":
                raise ValueError("获取回执必须是JSON原始资产")
        return self


class PublicPdfAvailabilityCapture(BaseModel):
    """一次有界获取尝试的范围化结果；失败只保留原因，绝不伪造成功。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_url: str
    status: PdfAvailabilityStatus
    witness: PublicPdfAvailabilityWitness | None = None
    diagnostic: str

    @field_validator("request_url", "diagnostic")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def _status_matches_witness(self) -> PublicPdfAvailabilityCapture:
        if (self.witness is None) == (self.status == "available"):
            raise ValueError("结果状态与见证存在性不一致")
        if self.witness is not None and self.witness.request_url != self.request_url:
            raise ValueError("结果与见证的请求地址不一致")
        return self


def capture_public_pdf_availability(
    project_root: Path,
    url: str,
    expected_raw_asset: ContentBlob,
    timeout: float = 30,
    *,
    transport: PdfTransport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> PublicPdfAvailabilityCapture:
    """Perform one bounded public GET against the pinned original and witness success.

    The pinned raw asset is reopened from CAS first; the response must then match
    its exact SHA-256, size, PDF media type and magic on the final official URL.
    Received bytes are stored once into the existing CAS, so a repeat same-byte
    retrieval reuses the same address and never mints a new source identity.
    """
    if not 0 < timeout <= 60:
        raise ValueError("获取超时必须在 0-60 秒内")
    _require_official_pdf_url(url)
    store = ContentAddressedStore(project_root)
    try:
        pinned = store.read_bytes(expected_raw_asset)
    except (OSError, ContentIntegrityError) as error:
        raise PublicPdfAvailabilityError("既有原始资产缺失或摘要漂移") from error
    _require_pdf_media(expected_raw_asset)
    _require_cas_binding(expected_raw_asset)
    if not pinned.startswith(b"%PDF-"):
        raise PublicPdfAvailabilityError("既有原始资产不是已固定的官方 PDF")
    expected_sha = hashlib.sha256(pinned).hexdigest()
    expected_size = len(pinned)

    def finish(status: PdfAvailabilityStatus, diagnostic: str) -> PublicPdfAvailabilityCapture:
        return PublicPdfAvailabilityCapture(request_url=url, status=status, diagnostic=diagnostic)

    download = transport or _download
    request_started_at = _utc_instant(clock())
    try:
        response = download(url, timeout, expected_size)
    except (OSError, URLError, TimeoutError):
        return finish("network_error", "公开网络获取失败；这既不是可用也不是不可用证据")
    if response.status in {401, 403, 429}:
        return finish("access_denied", "官方来源拒绝访问或限流；不是不可用证据")
    if response.status in {404, 410}:
        return finish("unavailable", "官方附件当前不可公开获取；这不是历史或首次公开证据")
    if response.status >= 500:
        return finish("network_error", "官方服务暂不可用；不是不可用证据")
    if 300 <= response.status < 400:
        return finish("invalid_response", "官方地址发生重定向；不凭猜测接纳跳转目标")
    if response.status != 200:
        return finish("invalid_response", "官方来源返回非预期状态")
    if response.final_url != url:
        return finish("invalid_response", "最终地址与请求地址不一致；出现非官方跳转")
    if response.content_type.split(";", 1)[0].strip().lower() != "application/pdf":
        return finish("invalid_response", "来源未按 application/pdf 返回官方附件")
    if not response.body.startswith(b"%PDF-"):
        return finish("invalid_response", "响应缺少 PDF 魔数；不接纳错误页或其他内容")
    if response.content_length is not None and response.content_length != len(response.body):
        return finish("invalid_response", "传输长度与实际字节不一致；疑似截断")
    if len(response.body) > expected_size:
        return finish("mismatch", "响应超出既有原始资产大小；未保存截断正文")
    if len(response.body) != expected_size:
        return finish("mismatch", "响应字节数与既有原始资产不一致")
    if hashlib.sha256(response.body).hexdigest() != expected_sha:
        return finish("mismatch", "响应内容与既有官方原始资产摘要不一致；疑似版本变化")
    observed_available_at = _utc_instant(clock())
    if request_started_at > observed_available_at:
        raise PublicPdfAvailabilityError("获取开始时刻晚于完成观察时刻")
    raw = store.put_bytes(response.body, media_type="application/pdf")
    witness = PublicPdfAvailabilityWitness(
        request_url=url, final_url=response.final_url, request_started_at=request_started_at,
        observed_available_at=observed_available_at,
        content_type=response.content_type, content_length=response.content_length,
        expected_raw_asset=expected_raw_asset, raw_asset=raw,
    )
    receipt = store.put_bytes(witness.model_dump_json().encode(), media_type="application/json")
    witness = witness.model_copy(update={"receipt_asset": receipt})
    return PublicPdfAvailabilityCapture(
        request_url=url, status="available",
        diagnostic="官方附件当前完整可公开获取；仅为当前可用性观察",
        witness=witness,
    )


def verify_public_pdf_availability(
    project_root: Path,
    witness: PublicPdfAvailabilityWitness,
    source_url: str,
    expected_raw_asset: ContentBlob,
    cutoff: datetime,
) -> bytes:
    """Reopen the receipt and exact raw bytes from CAS; any inconsistency fails closed.

    Every field is re-derived from the current instance because frozen models can
    be forged via ``model_copy``. A cutoff before the observed instant fails: a
    current-availability observation must never be backdated, and any earlier
    first-disclosure proof must come separately from the parent workflow.
    """
    _require_official_pdf_url(source_url)
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise PublicPdfAvailabilityError("复核截止时刻缺少时区偏移")
    cutoff_at = _utc_instant(cutoff)
    if witness.expected_raw_asset != expected_raw_asset:
        raise PublicPdfAvailabilityError("见证与本次复核所固定的原始资产不一致")
    if witness.request_url != source_url or witness.final_url != source_url:
        raise PublicPdfAvailabilityError("见证的请求或最终地址与来源地址不一致")
    if witness.http_status != 200:
        raise PublicPdfAvailabilityError("见证不是一次成功的完整获取")
    observation = witness.observed_available_at
    if observation.tzinfo is None or observation.utcoffset() is None:
        raise PublicPdfAvailabilityError("见证的观察时刻缺少时区偏移")
    observed_available_at = _utc_instant(observation)
    started = witness.request_started_at
    if started.tzinfo is None or started.utcoffset() is None:
        raise PublicPdfAvailabilityError("见证的获取开始时刻缺少时区偏移")
    if _utc_instant(started) > observed_available_at or observed_available_at > datetime.now(UTC):
        raise PublicPdfAvailabilityError("见证时序无效或声称未来已完成获取")
    if cutoff_at < observed_available_at:
        raise PublicPdfAvailabilityError(
            "复核截止早于实际观察时刻；当前可用性不得回溯为更早可得，"
            "首次公开日期须由上层流程另行举证"
        )
    if witness.content_type.split(";", 1)[0].strip().lower() != "application/pdf":
        raise PublicPdfAvailabilityError("见证的响应媒体类型不是 application/pdf")
    if witness.content_length is not None and witness.content_length != witness.raw_asset.byte_size:
        raise PublicPdfAvailabilityError("见证的响应长度与实际字节不一致")
    _require_pdf_media(expected_raw_asset)
    _require_cas_binding(expected_raw_asset)
    _require_pdf_media(witness.raw_asset)
    _require_cas_binding(witness.raw_asset)
    if witness.raw_asset != witness.expected_raw_asset:
        raise PublicPdfAvailabilityError("见证原始资产与既有固定资产不同址")
    store = ContentAddressedStore(project_root)
    try:
        receipt_asset = witness.receipt_asset
        if receipt_asset is None:
            raise PublicPdfAvailabilityError("见证缺少可重开的内容寻址获取回执")
        _require_cas_binding(receipt_asset)
        if receipt_asset.media_type != "application/json":
            raise PublicPdfAvailabilityError("获取回执媒体类型无效")
        receipt_bytes = store.read_bytes(receipt_asset)
        reopened = PublicPdfAvailabilityWitness.model_validate_json(receipt_bytes)
        if reopened.receipt_asset is not None or reopened.model_dump(
            mode="json", exclude={"receipt_asset"},
        ) != witness.model_dump(mode="json", exclude={"receipt_asset"}):
            raise PublicPdfAvailabilityError("获取回执与当前见证字段不一致")
        pinned = store.read_bytes(expected_raw_asset)
        raw = store.read_bytes(witness.raw_asset)
    except (OSError, ContentIntegrityError) as error:
        raise PublicPdfAvailabilityError("见证或既有原始资产缺失、篡改或摘要漂移") from error
    except ValueError as error:
        raise PublicPdfAvailabilityError("获取回执不可解析或与当前见证不一致") from error
    if raw != pinned:
        raise PublicPdfAvailabilityError("重开原始字节与既有官方原始资产不一致；疑似版本变化")
    if not raw.startswith(b"%PDF-"):
        raise PublicPdfAvailabilityError("重开资产缺少 PDF 魔数")
    return raw
