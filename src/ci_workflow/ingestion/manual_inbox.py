"""Task 3.3 用户辅助下载与自动摄取。

自动路线穷尽后，只有确为关键阻断的 publication/supplement 才请求用户下载。
用户保留发布者原文件名放入项目唯一 `evidence/manual-inbox/<request_id>/` 目录；
本模块按内容摘要、媒体类型、嵌入文本中的 NCT/DOI/PMID/标题完成唯一高置信匹配，
规范命名、隔离、内容寻址归档，并生成绑定来源版本与缺口的重抽取任务。

六态迁移（DownloadRequestState）全部显式声明并失败关闭：
- awaiting_user -> file_detected -> matched -> accepted（主链）
- file_detected/matched -> needs_re_download（登录/错误页、残缺/不可读、错附件、歧义）
- needs_re_download -> awaiting_user（去重后重新请求，attempt_number 递增）
- 任一未接受态 -> not_required（其他已接受证据关闭缺口；不得掩盖仍失败的关键单元）

每次已声明迁移都写入规范事件（前后状态、触发者、守卫证据、时间、幂等键与
attempt_number）；事件库按幂等键去重，重放同一业务事件不重复移动、归档、事件
或重抽取任务。下载请求绑定真实 GateSpec（从批准 YAML 加载并校验身份与指纹），
只有仍在阻断且目标文档预期关闭至少一个关键单元时才创建请求。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import DownloadRequestState
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import GateBlockingLevel, GateSpec
from ci_workflow.ingestion.classifier import DocumentRole
from ci_workflow.storage.content_store import (
    ContentAddressedStore,
    EvidenceRepository,
)
from ci_workflow.storage.event_store import EventStore, WorkflowEvent
from ci_workflow.storage.migrations import apply_migrations

# 已声明迁移：from_state -> to_state
_DECLARED_TRANSITIONS: frozenset[tuple[DownloadRequestState, DownloadRequestState]] = (
    frozenset(
        {
            (DownloadRequestState.AWAITING_USER, DownloadRequestState.FILE_DETECTED),
            (DownloadRequestState.FILE_DETECTED, DownloadRequestState.MATCHED),
            (DownloadRequestState.FILE_DETECTED, DownloadRequestState.NEEDS_RE_DOWNLOAD),
            (DownloadRequestState.MATCHED, DownloadRequestState.NEEDS_RE_DOWNLOAD),
            (DownloadRequestState.MATCHED, DownloadRequestState.ACCEPTED),
            (DownloadRequestState.NEEDS_RE_DOWNLOAD, DownloadRequestState.AWAITING_USER),
            # 扫描收件目录后未发现任何合法目标（全部无效/歧义）→ 直接需要重新下载
            (DownloadRequestState.AWAITING_USER, DownloadRequestState.NEEDS_RE_DOWNLOAD),
        }
    )
) | frozenset(
    {
        (state, DownloadRequestState.NOT_REQUIRED)
        for state in (
            DownloadRequestState.AWAITING_USER,
            DownloadRequestState.FILE_DETECTED,
            DownloadRequestState.MATCHED,
            DownloadRequestState.NEEDS_RE_DOWNLOAD,
        )
    }
)

_NCT_PATTERN = re.compile(r"NCT\d{8}", re.IGNORECASE)
_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s<>\"']+")
_PMID_PATTERN = re.compile(r"PMID[:\s]*(\d{1,9})", re.IGNORECASE)
_DOI_TRAILING = re.compile(r"[.,;:)\]}]+$")
_LOGIN_OR_ERROR_MARKERS = (
    "sign in to view",
    "sign in to continue",
    "log in to view",
    "log in to continue",
    "please sign in",
    "please log in",
    "access denied",
    "accessdenied",
    "登录后查看",
    "请登录后",
    "无法访问该内容",
    "访问受限",
    "captcha",
    "验证码",
    "页面不存在",
)

# 需要用户动作的活跃状态：列表只展示这些请求，已接受/不再需要不出现。
_ACTIVE_REQUEST_STATES = frozenset(
    {
        DownloadRequestState.AWAITING_USER,
        DownloadRequestState.FILE_DETECTED,
        DownloadRequestState.MATCHED,
        DownloadRequestState.NEEDS_RE_DOWNLOAD,
    }
)


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("下载请求字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("下载请求时间必须包含明确时区偏移")
    return value


class DownloadRequestError(ValueError):
    """下载请求状态机或守卫失败。"""


class UndeclaredTransitionError(DownloadRequestError):
    """未声明的状态迁移一律拒绝。"""


class RequestNotRequiredError(DownloadRequestError):
    """关键缺口已被接受证据关闭，或请求不满足阻断前提，不创建/取消请求。"""


class DownloadRequest(BaseModel):
    """一个用户辅助下载请求；保存稳定身份、阻断优先级、缺口与唯一相对收件目录。

    只保存项目相对路径与中文用户说明；绝不保存机器绝对路径或后端状态词。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    report_kind: Literal["A", "B", "C"]
    blocking_priority: Literal["blocking", "non_blocking"]
    product_id: str | None = None
    trial_id: str | None = None
    registry_identifiers: tuple[str, ...] = ()
    doi: str | None = None
    pmid: str | None = None
    document_role: DocumentRole
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    landing_page_url: str = Field(min_length=1)
    attachment_url: str = Field(min_length=1)
    missing_fields: tuple[str, ...] = Field(min_length=1)
    expected_to_close_units: tuple[str, ...] = Field(min_length=1)
    reason_zh: str = Field(min_length=1)
    inbox_directory: str = Field(min_length=1)
    state: DownloadRequestState = DownloadRequestState.AWAITING_USER
    # GateSpec 绑定（真实身份）
    spec_id: str = Field(min_length=1)
    spec_fingerprint: str = Field(min_length=1)
    # 匹配/接受元数据
    original_filename: str | None = None
    content_sha256: str | None = None
    media_type: str | None = None
    canonical_filename: str | None = None
    canonical_relative_path: str | None = None
    source_version_id: str | None = None
    re_extraction_job_ids: tuple[str, ...] = ()
    matched_identifiers: tuple[str, ...] = ()
    quarantine_reason_zh: str | None = None
    quarantine_rejected_paths: tuple[str, ...] = ()
    attempt_number: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "request_id",
        "project_id",
        "run_id",
        "title",
        "publisher",
        "landing_page_url",
        "attachment_url",
        "spec_id",
        "spec_fingerprint",
    )
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("product_id", "trial_id", "doi", "pmid")
    @classmethod
    def _optional_text_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @field_validator(
        "registry_identifiers",
        "missing_fields",
        "expected_to_close_units",
        "matched_identifiers",
        "re_extraction_job_ids",
        "quarantine_rejected_paths",
    )
    @classmethod
    def _items_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)

    @field_validator("reason_zh", "quarantine_reason_zh")
    @classmethod
    def _optional_zh_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @field_validator("created_at", "updated_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("content_sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("内容摘要必须是小写 SHA-256")
        return value

    @field_validator("source_version_id", "canonical_relative_path")
    @classmethod
    def _optional_id_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @model_validator(mode="after")
    def _inbox_directory_is_project_relative(self) -> DownloadRequest:
        pure = PurePosixPath(self.inbox_directory)
        if pure.is_absolute() or ".." in pure.parts or "\\" in self.inbox_directory:
            raise ValueError("收件目录必须是项目相对路径")
        if self.inbox_directory != f"evidence/manual-inbox/{self.request_id}":
            raise ValueError("收件目录必须与请求身份一一对应")
        return self

    @model_validator(mode="after")
    def _project_relative_paths(self) -> DownloadRequest:
        for field in ("canonical_relative_path",):
            value = getattr(self, field)
            if value is None:
                continue
            pure = PurePosixPath(value)
            if pure.is_absolute() or ".." in pure.parts or "\\" in value:
                raise ValueError(f"{field} 必须是项目相对路径")
        for value in self.quarantine_rejected_paths:
            pure = PurePosixPath(value)
            if pure.is_absolute() or ".." in pure.parts or "\\" in value:
                raise ValueError("隔离路径必须是项目相对路径")
        return self

    @model_validator(mode="after")
    def _zh_fields_contain_chinese(self) -> DownloadRequest:
        for value in (self.reason_zh,):
            if not any("\u4e00" <= char <= "\u9fff" for char in value):
                raise ValueError("用户说明必须为中文")
        if self.quarantine_reason_zh is not None and not any(
            "\u4e00" <= char <= "\u9fff" for char in self.quarantine_reason_zh
        ):
            raise ValueError("隔离说明必须为中文")
        return self

    @model_validator(mode="after")
    def _matched_requires_identity(self) -> DownloadRequest:
        if self.state is DownloadRequestState.MATCHED:
            if not self.content_sha256:
                raise ValueError("已匹配记录必须保存内容摘要")
            if not self.matched_identifiers:
                raise ValueError("已匹配记录必须保存匹配标识符")
        return self

    @model_validator(mode="after")
    def _accepted_requires_archive_metadata(self) -> DownloadRequest:
        if self.state is DownloadRequestState.ACCEPTED:
            if not self.original_filename:
                raise ValueError("已接受记录必须保存用户提供的原文件名")
            if not self.content_sha256:
                raise ValueError("已接受记录必须保存内容摘要")
            if not self.canonical_filename:
                raise ValueError("已接受记录必须保存规范文件名")
            if not self.canonical_relative_path:
                raise ValueError("已接受记录必须保存规范归档相对路径")
            if not self.source_version_id:
                raise ValueError("已接受记录必须保存来源版本标识")
            if not self.re_extraction_job_ids:
                raise ValueError("已接受记录必须保存重抽取任务标识")
            if not self.matched_identifiers:
                raise ValueError("已接受记录必须保存匹配标识符")
        return self


# ── GateSpec 真源校验 ───────────────────────────────────────────────────────


def _canonical_gate_spec_path(report_kind: str) -> Path:
    return Path(__file__).resolve().parents[3] / "policies" / "gates" / f"{report_kind}-v1.yaml"


def _canonical_gate_spec(report_kind: str) -> GateSpec:
    return GateSpec.from_yaml(_canonical_gate_spec_path(report_kind))


def _critical_unit_ids(spec: GateSpec) -> frozenset[str]:
    return frozenset(
        unit.unit_id for unit in spec.units if unit.blocking_level is GateBlockingLevel.CRITICAL
    )


# ── 规范命名 ────────────────────────────────────────────────────────────────


def _canonical_slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return normalized[:48] or "doc"


def _canonical_filename(
    *,
    basis: str,
    document_role: str,
    version_or_date: str | None,
    digest: str,
    original_extension: str,
) -> str:
    version = _canonical_slug(version_or_date or "v1")
    extension = original_extension.lstrip(".").lower() or "bin"
    return (
        f"{_canonical_slug(basis)}-{_canonical_slug(document_role)}"
        f"-{version}-{digest[:8]}.{extension}"
    )


def _canonical_basis(request: DownloadRequest) -> str:
    return request.trial_id or request.product_id or request.title


# ── 标识符规范化 ────────────────────────────────────────────────────────────


def _normalize_doi(value: str) -> str:
    return _DOI_TRAILING.sub("", value).casefold()


def _normalize_nct(value: str) -> str:
    return value.upper()


def _normalize_pmid(value: str) -> str:
    match = re.search(r"\d{1,9}", value)
    return match.group(0) if match else value


def _normalize_identifier(value: str) -> str:
    if re.fullmatch(r"NCT\d{8}", value, re.IGNORECASE):
        return _normalize_nct(value)
    if _DOI_PATTERN.fullmatch(value):
        return _normalize_doi(value)
    return _normalize_pmid(value)


def _identifiers_in_text(text: str) -> tuple[str, ...]:
    found: list[str] = []
    found.extend(_normalize_nct(item) for item in _NCT_PATTERN.findall(text))
    found.extend(_normalize_doi(item) for item in _DOI_PATTERN.findall(text))
    found.extend(item for item in _PMID_PATTERN.findall(text))
    return tuple(dict.fromkeys(found))


def _request_identifier_set(request: DownloadRequest) -> set[str]:
    identifiers: set[str] = set()
    for item in request.registry_identifiers:
        identifiers.add(_normalize_identifier(item))
    if request.doi:
        identifiers.add(_normalize_doi(request.doi))
    if request.pmid:
        identifiers.add(_normalize_pmid(request.pmid))
    return identifiers


# ── 内容识别 ────────────────────────────────────────────────────────────────


def _pdf_text_and_metadata(content: bytes) -> tuple[str, bool, bool]:
    """Return searchable text, parseability, and whether a page text layer exists."""
    try:
        import io as _io

        from pypdf import PdfReader

        reader = PdfReader(_io.BytesIO(content))
        metadata: dict[str, Any] = dict(reader.metadata or {})
        title = str(metadata.get("/Title") or metadata.get("title") or "")
        subject = str(metadata.get("/Subject") or metadata.get("subject") or "")
        keywords = str(metadata.get("/Keywords") or metadata.get("keywords") or "")
        pages = "\n".join(str(page.extract_text() or "") for page in reader.pages)
        return (
            "\n".join(part for part in (title, subject, keywords, pages) if part),
            True,
            bool(pages.strip()),
        )
    except Exception:  # noqa: BLE001
        return "", False, False


def _extract_embedded_text(content: bytes, media_type: str) -> tuple[str, bool, bool]:
    """Return embedded text, readability, and whether OCR is required."""
    if media_type == "application/pdf":
        text, readable, has_page_text = _pdf_text_and_metadata(content)
        return text, readable, readable and not has_page_text
    if media_type in ("text/html", "text/plain", "application/json", "text/json"):
        try:
            return content.decode("utf-8"), True, False
        except UnicodeDecodeError:
            return "", False, False
    return "", False, False


class ContentIdentification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sha256: str
    media_type: str
    embedded_text: str
    identifiers: tuple[str, ...] = ()
    is_login_or_error_page: bool = False
    is_readable: bool = True
    requires_ocr: bool = False

    @model_validator(mode="after")
    def _readability_consistent(self) -> ContentIdentification:
        if not self.embedded_text.strip() and self.is_readable:
            raise ValueError("不可读内容必须标记不可读")
        return self


def identify_content(content: bytes, media_type: str) -> ContentIdentification:
    if not content:
        raise DownloadRequestError("文件内容为空")
    digest = hashlib.sha256(content).hexdigest()
    text, readable, requires_ocr = _extract_embedded_text(content, media_type)
    is_error = _is_login_or_error_page(content, media_type, text)
    return ContentIdentification(
        sha256=digest,
        media_type=media_type.strip(),
        embedded_text=text,
        identifiers=_identifiers_in_text(text),
        is_login_or_error_page=is_error and readable,
        is_readable=readable,
        requires_ocr=requires_ocr,
    )


def _is_login_or_error_page(content: bytes, media_type: str, text: str) -> bool:
    if media_type == "text/html":
        lowered = text.casefold()
        return any(marker in lowered for marker in _LOGIN_OR_ERROR_MARKERS)
    return False


_GENERIC_TITLE_WORDS = frozenset(
    {
        "analysis",
        "clinical",
        "results",
        "study",
        "trial",
    }
)


def _title_matches(title: str, text: str) -> bool:
    """中文标题按连续语义片段核对；英文标题至少命中两个有区分度的词。"""
    comparable_text = text.casefold()
    cjk_parts = tuple(part for part in re.split(r"[^\u4e00-\u9fff]+", title) if len(part) >= 4)
    if any(part in comparable_text for part in cjk_parts):
        return True
    latin_parts = tuple(
        dict.fromkeys(
            part
            for part in re.findall(
                r"[A-Za-z0-9][A-Za-z0-9-]{3,}",
                title.casefold(),
            )
            if part not in _GENERIC_TITLE_WORDS
        )
    )
    if not latin_parts:
        return False
    matched_count = sum(part in comparable_text for part in latin_parts)
    return matched_count >= min(2, len(latin_parts))


def _media_type_for(ext: str) -> str:
    _map = {
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".htm": "text/html",
        ".txt": "text/plain",
        ".json": "application/json",
    }
    return _map.get(ext.lower(), "application/octet-stream")


# ── 类型与角色一致性 ────────────────────────────────────────────────────────


def _validate_file_type(content: bytes, filename: str, media_type: str) -> None:
    """文件名扩展名、媒体类型与内容三者一致；不一致即拒绝。"""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        if media_type != "application/pdf":
            raise DownloadRequestError(
                "这个 PDF 附件的实际格式与文件名不一致，请重新下载原始附件后放入。"
            )
        if not content[:4] == b"%PDF":
            raise DownloadRequestError("文件内容不是有效的 PDF 格式")
    elif ext in (".html", ".htm"):
        if media_type != "text/html":
            raise DownloadRequestError(
                "这个网页附件的实际格式与文件名不一致，请重新下载原始附件后放入。"
            )
    elif ext in (".txt",):
        if media_type != "text/plain":
            raise DownloadRequestError(
                "这个文本附件的实际格式与文件名不一致，请重新下载原始附件后放入。"
            )
    else:
        if media_type == "application/pdf" and not content[:4] == b"%PDF":
            raise DownloadRequestError("文件内容不是有效的 PDF 格式")


def _assert_role_type_coherent(document_role: DocumentRole, media_type: str) -> None:
    """publication_pdf 必须由真实 PDF 满足；HTML 不能冒充论文全文。"""
    if document_role == "publication_pdf" and media_type != "application/pdf":
        raise DownloadRequestError("论文全文必须提供真实 PDF 附件，HTML 文件不能替代。")


# ── 持久化辅助 ──────────────────────────────────────────────────────────────


def _load_requests(path: Path) -> tuple[DownloadRequest, ...]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return ()
    return tuple(
        DownloadRequest.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with open(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _request_identity_fields(request: DownloadRequest) -> dict[str, object]:
    """不可变身份字段：同 request_id 下这些字段发生漂移即拒绝覆盖。"""
    return {
        "project_id": request.project_id,
        "run_id": request.run_id,
        "report_kind": request.report_kind,
        "blocking_priority": request.blocking_priority,
        "product_id": request.product_id,
        "trial_id": request.trial_id,
        "registry_identifiers": request.registry_identifiers,
        "doi": request.doi,
        "pmid": request.pmid,
        "document_role": request.document_role,
        "title": request.title,
        "publisher": request.publisher,
        "landing_page_url": request.landing_page_url,
        "attachment_url": request.attachment_url,
        "missing_fields": request.missing_fields,
        "expected_to_close_units": request.expected_to_close_units,
        "spec_id": request.spec_id,
        "spec_fingerprint": request.spec_fingerprint,
    }


def _save_request(path: Path, request: DownloadRequest) -> None:
    """追加式/替换式持久化：同 request_id 身份漂移失败关闭，否则替换。"""
    records = list(_load_requests(path))
    kept: list[DownloadRequest] = []
    for record in records:
        if record.request_id == request.request_id:
            if _request_identity_fields(record) != _request_identity_fields(request):
                raise DownloadRequestError("同一下载请求标识对应了不同身份内容，拒绝覆盖")
            continue
        kept.append(record)
    kept.append(request)
    content = "\n".join(json.dumps(r.model_dump(mode="json"), ensure_ascii=False) for r in kept)
    if content:
        content += "\n"
    _atomic_write(path, content)


def _append_jsonl(path: Path, line: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    content = existing
    if content and not content.endswith("\n"):
        content += "\n"
    content += json.dumps(line, ensure_ascii=False) + "\n"
    _atomic_write(path, content)


def _record_quarantine_note(note_path: Path, filename: str, reason_zh: str) -> None:
    """保留每个隔离文件的处理说明；同一说明重放时不重复。"""
    line = f"- {Path(filename).name}：{reason_zh}"
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else "# 文件处理说明\n"
    if line not in existing.splitlines():
        _atomic_write(note_path, existing.rstrip() + "\n\n" + line + "\n")


# ── 下载列表（原子重生成，不显示内部状态） ─────────────────────────────────


def _request_list_line(request: DownloadRequest) -> str:
    return (
        f"- 「{request.title}」（{request.reason_zh}）\n"
        f"  {request.landing_page_url}\n"
        f"  附件：{request.attachment_url}\n"
        f"  放入：{request.inbox_directory}\n"
        f"  无需重命名"
    )


def _regenerate_download_list(
    log_path: Path,
    requests_path: Path,
) -> None:
    """从物化请求原子重生成当前下载列表：只列活跃待办请求，每个一次；
    已接受/不再需要消失；无待办时显示“当前无需补充资料”。"""
    active = [
        request
        for request in _load_requests(requests_path)
        if request.state in _ACTIVE_REQUEST_STATES
    ]
    if not active:
        _atomic_write(log_path, "# 待补充资料\n\n当前无需补充资料。\n")
        return
    lines = ["# 待补充资料", ""]
    for request in active:
        lines.append(_request_list_line(request))
        lines.append("")
    _atomic_write(log_path, "\n".join(lines).rstrip() + "\n")


# ── main 服务 ──────────────────────────────────────────────────────────────


class ManualInboxService:
    """用户辅助下载服务：六态迁移、守卫事件、内容识别、隔离、归档与重抽取。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.event_store = EventStore(self.project_root)
        self.content_store = ContentAddressedStore(self.project_root)
        self.database_path = self.project_root / "state/project.sqlite"
        apply_migrations(self.database_path)
        self.evidence_repo = EvidenceRepository(self.database_path, self.content_store)
        self.requests_path = self.project_root / "receipts" / "download_requests.jsonl"
        self.re_extraction_path = self.project_root / "receipts" / "re-extraction-jobs.jsonl"
        self.download_log_path = self.project_root / "logs" / "download_requests.md"
        self.manual_mapping_path = self.project_root / "receipts" / "manual-source-mappings.jsonl"

    # ── 请求读取/保存 ──────────────────────────────────────────────────────────

    def load_request(self, request_id: str) -> DownloadRequest:
        for request in _load_requests(self.requests_path):
            if request.request_id == request_id:
                return request
        raise KeyError(f"下载请求不存在：{request_id}")

    def _persist(self, request: DownloadRequest) -> DownloadRequest:
        _save_request(self.requests_path, request)
        return request

    def _active_others(self, request_id: str) -> tuple[DownloadRequest, ...]:
        current = self.load_request(request_id)
        return tuple(
            request
            for request in _load_requests(self.requests_path)
            if request.request_id != request_id
            and request.project_id == current.project_id
            and request.run_id == current.run_id
            and request.state in _ACTIVE_REQUEST_STATES
        )

    # ── 事件写入（含 attempt_number 身份） ─────────────────────────────────────

    def _write_transition_event(
        self,
        *,
        request: DownloadRequest,
        prior: DownloadRequestState,
        current: DownloadRequestState,
        trigger: str,
        guard_evidence: dict[str, Any],
        content_digest: str,
        occurred_at: datetime,
    ) -> None:
        effective_digest = content_digest or request.request_id
        attempt = request.attempt_number
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(
                "download-event",
                request.request_id,
                prior.value,
                current.value,
                str(attempt),
                effective_digest,
            ),
            project_id=request.project_id,
            run_id=request.run_id,
            event_type="download_request_state_changed",
            occurred_at=occurred_at,
            actor_id="manual-inbox",
            idempotency_key=(
                f"download:{request.request_id}:{prior.value}->{current.value}"
                f":{trigger}:{attempt}:{effective_digest}"
            ),
            payload={
                "request_id": request.request_id,
                "prior_state": prior.value,
                "current_state": current.value,
                "trigger": trigger,
                "attempt_number": attempt,
                "guard_evidence": guard_evidence,
                "content_digest": effective_digest,
            },
        )
        self.event_store.append(event)

    # ── 创建与取消（真实 GateSpec + 类型化守卫） ──────────────────────────────

    def create_request(
        self,
        *,
        project_id: str,
        run_id: str,
        report_kind: Literal["A", "B", "C"],
        spec: GateSpec,
        blocking_priority: Literal["blocking", "non_blocking"],
        product_id: str | None,
        trial_id: str | None,
        registry_identifiers: tuple[str, ...],
        doi: str | None,
        pmid: str | None = None,
        document_role: DocumentRole,
        title: str,
        publisher: str,
        landing_page_url: str,
        attachment_url: str,
        missing_fields: tuple[str, ...],
        reason_zh: str,
        gap_still_open: bool,
        expected_to_close_units: tuple[str, ...],
    ) -> DownloadRequest:
        """只有关键缺口仍在阻断且目标文档预期关闭至少一个关键单元时才创建。"""
        try:
            doi = _not_blank(doi) if doi is not None else None
            pmid = _not_blank(pmid) if pmid is not None else None
            registry_identifiers = tuple(
                _not_blank(identifier) for identifier in registry_identifiers
            )
        except ValueError as exc:
            raise RequestNotRequiredError(
                "目标资料缺少可核对的论文或试验标识，暂不向用户发起下载请求。"
            ) from exc
        if blocking_priority != "blocking":
            raise RequestNotRequiredError(
                "非阻断字段（统计细节或试验完成情况）缺失不得触发用户补件。"
            )
        if not gap_still_open:
            raise RequestNotRequiredError(
                "已接受的登记/主文/监管证据已关闭关键缺口，不再请求补充材料。"
            )
        if not expected_to_close_units:
            raise RequestNotRequiredError("目标文档必须声明预期关闭至少一个关键单元。")
        # 真实 GateSpec 校验：身份/指纹/关键单元都取自批准 YAML，伪造不可能。
        canonical = _canonical_gate_spec(report_kind)
        if spec.report_kind.value != report_kind:
            raise RequestNotRequiredError("所选报告与证据规则不一致")
        if spec.spec_id != canonical.spec_id:
            raise RequestNotRequiredError("GateSpec 标识与批准规则不符")
        if spec.spec_fingerprint != canonical.spec_fingerprint:
            raise RequestNotRequiredError("GateSpec 指纹与批准规则不符")
        if spec.report_kind is not canonical.report_kind:
            raise RequestNotRequiredError("GateSpec 报告类型与批准规则不符")
        critical = _critical_unit_ids(canonical)
        for field in missing_fields:
            if field not in critical:
                raise RequestNotRequiredError(f"非阻断字段（{field}）缺失不得触发用户补件")
        for unit in expected_to_close_units:
            if unit not in critical:
                raise RequestNotRequiredError(f"目标文档声明的关闭单元（{unit}）不是关键单元")
        if not set(expected_to_close_units) & set(missing_fields):
            raise RequestNotRequiredError("目标文档未覆盖任何所缺关键单元，不创建请求")
        if not doi and not pmid and not registry_identifiers:
            raise RequestNotRequiredError(
                "目标资料缺少可核对的论文或试验标识，暂不向用户发起下载请求。"
            )

        now_value = datetime.now(UTC)
        request_id = self._request_id(
            project_id=project_id,
            run_id=run_id,
            report_kind=report_kind,
            product_id=product_id,
            trial_id=trial_id,
            document_role=document_role,
            doi=doi,
            pmid=pmid,
            registry_identifiers=registry_identifiers,
            title=title,
            attachment_url=attachment_url,
            missing_fields=missing_fields,
            spec_fingerprint=canonical.spec_fingerprint,
        )
        existing = self._find_request(request_id)
        candidate = DownloadRequest(
            request_id=request_id,
            project_id=project_id,
            run_id=run_id,
            report_kind=report_kind,
            blocking_priority=blocking_priority,
            product_id=product_id,
            trial_id=trial_id,
            registry_identifiers=tuple(registry_identifiers),
            doi=doi,
            pmid=pmid,
            document_role=document_role,
            title=title,
            publisher=publisher,
            landing_page_url=landing_page_url,
            attachment_url=attachment_url,
            missing_fields=tuple(missing_fields),
            expected_to_close_units=tuple(expected_to_close_units),
            reason_zh=reason_zh,
            inbox_directory=f"evidence/manual-inbox/{request_id}",
            spec_id=canonical.spec_id,
            spec_fingerprint=canonical.spec_fingerprint,
            created_at=now_value,
            updated_at=now_value,
        )
        if existing is not None:
            if _request_identity_fields(existing) != _request_identity_fields(candidate):
                raise DownloadRequestError("同一下载请求标识对应了不同身份内容，拒绝覆盖")
            return existing
        self._persist(candidate)
        inbox_dir = self.project_root / candidate.inbox_directory
        inbox_dir.mkdir(parents=True, exist_ok=True)
        _regenerate_download_list(self.download_log_path, self.requests_path)
        return candidate

    def _find_request(self, request_id: str) -> DownloadRequest | None:
        for request in _load_requests(self.requests_path):
            if request.request_id == request_id:
                return request
        return None

    def _request_id(
        self,
        *,
        project_id: str,
        run_id: str,
        report_kind: str,
        product_id: str | None,
        trial_id: str | None,
        document_role: DocumentRole,
        doi: str | None,
        pmid: str | None,
        registry_identifiers: tuple[str, ...],
        title: str,
        attachment_url: str,
        missing_fields: tuple[str, ...],
        spec_fingerprint: str,
    ) -> str:
        if doi:
            source_identity = _normalize_doi(doi)
        elif pmid:
            source_identity = _normalize_pmid(pmid)
        else:
            source_identity = "|".join(
                sorted(_normalize_identifier(item) for item in registry_identifiers)
            )
        return stable_id(
            "download-request",
            project_id,
            run_id,
            report_kind,
            trial_id or product_id or "",
            document_role,
            source_identity,
            title,
            attachment_url,
            "|".join(sorted(missing_fields)),
            spec_fingerprint,
        )

    def mark_not_required(
        self,
        request_id: str,
        *,
        reason_zh: str,
        gap_still_open: bool,
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        request = self.load_request(request_id)
        if request.state is DownloadRequestState.NOT_REQUIRED:
            return request
        if gap_still_open:
            raise DownloadRequestError("关键缺口仍阻断时不得取消下载请求")
        updated = self._transition(
            request_id,
            to_state=DownloadRequestState.NOT_REQUIRED,
            trigger="accepted_evidence_closed_gap",
            guard_evidence={"gap_still_open": False, "reason_zh": reason_zh},
            content_digest=reason_zh,
            updates={"quarantine_reason_zh": reason_zh},
            occurred_at=occurred_at,
        )
        _regenerate_download_list(self.download_log_path, self.requests_path)
        return updated

    # ── 状态机辅助 ─────────────────────────────────────────────────────────────

    def _already_detected(self, request: DownloadRequest, content: bytes) -> bool:
        if request.state not in (
            DownloadRequestState.FILE_DETECTED,
            DownloadRequestState.MATCHED,
            DownloadRequestState.ACCEPTED,
            DownloadRequestState.NEEDS_RE_DOWNLOAD,
        ):
            return False
        return request.content_sha256 == hashlib.sha256(content).hexdigest()

    def _already_matched(self, request: DownloadRequest, content: bytes) -> bool:
        if request.state not in (
            DownloadRequestState.MATCHED,
            DownloadRequestState.ACCEPTED,
        ):
            return False
        return request.content_sha256 == hashlib.sha256(content).hexdigest()

    def _transition(
        self,
        request_id: str,
        *,
        to_state: DownloadRequestState,
        trigger: str,
        guard_evidence: dict[str, Any],
        updates: dict[str, Any],
        content_digest: str = "",
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        request = self.load_request(request_id)
        prior = request.state
        if (prior, to_state) not in _DECLARED_TRANSITIONS:
            raise UndeclaredTransitionError(
                f"未声明的下载请求迁移：{prior.value} -> {to_state.value}"
            )
        timestamp = occurred_at or datetime.now(UTC)
        updated = request.model_copy(update={**updates, "state": to_state, "updated_at": timestamp})
        self._write_transition_event(
            request=updated,
            prior=prior,
            current=to_state,
            trigger=trigger,
            guard_evidence=guard_evidence,
            content_digest=content_digest,
            occurred_at=timestamp,
        )
        return self._persist(updated)

    # ── 文件检测（直接 API 也强制类型一致性） ────────────────────────────────

    def detect_file(
        self,
        request_id: str,
        *,
        filename: str,
        content: bytes,
        media_type: str,
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        _validate_file_type(content, filename, media_type)
        request = self.load_request(request_id)
        _assert_role_type_coherent(request.document_role, media_type)
        if self._already_detected(request, content):
            return request
        digest = hashlib.sha256(content).hexdigest()
        return self._transition(
            request_id,
            to_state=DownloadRequestState.FILE_DETECTED,
            trigger="file_found_in_inbox",
            guard_evidence={
                "inbox_directory": request.inbox_directory,
                "original_filename": filename,
                "content_sha256": digest,
                "media_type": media_type,
                "size_bytes": len(content),
            },
            content_digest=digest,
            updates={
                "original_filename": filename,
                "content_sha256": digest,
                "media_type": media_type,
            },
            occurred_at=occurred_at,
        )

    # ── 文件系统扫描（真实文件系统行为） ────────────────────────────────────

    def scan_and_process_inbox(
        self,
        request_id: str,
        *,
        occurred_at: datetime | None = None,
    ) -> DownloadRequest | None:
        """扫描收件目录：逐文件校验/识别，无效或错附件按摘要隔离；
        恰好一个合法高置信目标则接受；多个合法目标全部按歧义隔离。"""
        request = self.load_request(request_id)
        if request.state is DownloadRequestState.ACCEPTED:
            # 已接受状态重放必须是 no-op：不扫描、删除、移动或改写用户文件。
            return request
        inbox = self.project_root / request.inbox_directory
        if not inbox.is_dir():
            return None
        files = [
            f
            for f in sorted(inbox.iterdir())
            if f.is_file()
            and not f.name.startswith(".")
            and not f.name.endswith("~")
            and f.name != "下载说明.md"
        ]
        if not files:
            return None

        valid_targets: list[tuple[Path, bytes, str, str]] = []
        quarantine_reasons: list[str] = []
        for filepath in files:
            content = filepath.read_bytes()
            filename = filepath.name
            media_type = _media_type_for(filepath.suffix)
            try:
                _validate_file_type(content, filename, media_type)
                _assert_role_type_coherent(request.document_role, media_type)
                identification = identify_content(content, media_type)
            except DownloadRequestError as exc:
                self._quarantine_file(request_id, filepath, str(exc))
                quarantine_reasons.append(str(exc))
                continue
            if identification.is_login_or_error_page:
                self._quarantine_file(
                    request_id,
                    filepath,
                    "收到的是登录提示页或错误页，请下载附件原文后重新放入。",
                )
                quarantine_reasons.append("登录提示页或错误页")
                continue
            if not identification.is_readable:
                self._quarantine_file(
                    request_id,
                    filepath,
                    "文件残缺或不可读，请重新下载完整附件后放入。",
                )
                quarantine_reasons.append("文件残缺或不可读")
                continue
            matched, _matched_ids, reason = self._match_guard(
                request,
                identification,
                self._active_others(request_id),
            )
            if matched:
                valid_targets.append((filepath, content, filename, media_type))
            else:
                self._quarantine_file(request_id, filepath, cast(str, reason))
                quarantine_reasons.append(cast(str, reason))

        if len(valid_targets) == 1:
            filepath, content, filename, media_type = valid_targets[0]
            try:
                self.detect_file(
                    request_id,
                    filename=filename,
                    content=content,
                    media_type=media_type,
                    occurred_at=occurred_at,
                )
            except UndeclaredTransitionError:
                return self.load_request(request_id)
            return self.match_and_accept(
                request_id,
                filename=filename,
                content=content,
                media_type=media_type,
                occurred_at=occurred_at,
            )
        # 无合法目标，或存在多个合法目标 → 全部已隔离，请求进入需要重新下载
        if len(valid_targets) > 1:
            for _filepath, _content, _filename, _media_type in valid_targets:
                self._quarantine_file(
                    request_id,
                    _filepath,
                    "收件目录中存在多个匹配附件，无法唯一确定目标文档，请删除多余文件后重新放入。",
                )
            reason_zh = (
                "收件目录中存在多个匹配附件，无法唯一确定目标文档，请删除多余文件后重新放入。"
            )
        else:
            reason_zh = (
                quarantine_reasons[0]
                if quarantine_reasons
                else ("未发现与目标资料匹配的合法附件，请重新下载后放入。")
            )
        request = self.load_request(request_id)
        if request.state is DownloadRequestState.AWAITING_USER:
            return self._quarantine(
                request_id,
                reason_zh=reason_zh,
                trigger="scan_no_valid_target",
                guard_evidence={
                    "quarantined_count": len(quarantine_reasons)
                    + (len(valid_targets) if len(valid_targets) > 1 else 0),
                    "reason_zh": reason_zh,
                },
                occurred_at=occurred_at,
            )
        return self.load_request(request_id)

    def _quarantine_file(
        self,
        request_id: str,
        filepath: Path,
        reason_zh: str,
    ) -> DownloadRequest:
        """把单个文件按摘要消歧移到隔离区，并记录路径/原因（不改变状态）。"""
        request = self.load_request(request_id)
        quarantine_dir = self.project_root / "evidence/quarantine" / request_id
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(filepath.read_bytes()).hexdigest()
        digest_dir = quarantine_dir / digest[:16]
        digest_dir.mkdir(parents=True, exist_ok=True)
        target = digest_dir / filepath.name
        if not target.exists():
            os.replace(filepath, target)
        else:
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise DownloadRequestError("隔离区同名文件内容不一致，拒绝覆盖")
            filepath.unlink(missing_ok=True)
        rejected_path = f"evidence/quarantine/{request_id}/{digest_dir.name}/{filepath.name}"
        note = quarantine_dir / "处理说明.md"
        _record_quarantine_note(note, filepath.name, reason_zh)
        updated = request.model_copy(
            update={
                "quarantine_reason_zh": reason_zh,
                "quarantine_rejected_paths": (
                    (*request.quarantine_rejected_paths, rejected_path)
                    if rejected_path not in request.quarantine_rejected_paths
                    else request.quarantine_rejected_paths
                ),
            }
        )
        return self._persist(updated)

    def match_and_accept(
        self,
        request_id: str,
        *,
        filename: str,
        content: bytes,
        media_type: str,
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        """匹配并接受：内容匹配 + 类型验证 → 规范归档。"""
        _validate_file_type(content, filename, media_type)
        request = self.load_request(request_id)
        _assert_role_type_coherent(request.document_role, media_type)
        identification = identify_content(content, media_type)
        if request.state is DownloadRequestState.ACCEPTED:
            if request.content_sha256 != identification.sha256:
                raise DownloadRequestError("已归档资料与收件目录中的文件内容不一致")
            # 已接受状态重放必须保留用户收件文件。
            return request
        if request.state is DownloadRequestState.MATCHED:
            if request.content_sha256 != identification.sha256:
                raise DownloadRequestError("已识别资料与本次文件内容不一致")
            return self.accept(
                request_id,
                filename=filename,
                content=content,
                media_type=media_type,
                occurred_at=occurred_at,
            )
        if request.state is not DownloadRequestState.FILE_DETECTED:
            raise UndeclaredTransitionError(f"匹配只能在文件检测后执行（{request.state.value}）")
        matched, matched_ids, reason = self._match_guard(
            request,
            identification,
            self._active_others(request_id),
        )
        if not matched:
            return self._quarantine(
                request_id,
                reason_zh=cast(str, reason),
                trigger="content_mismatch",
                guard_evidence={
                    "content_sha256": identification.sha256,
                    "identifiers": list(identification.identifiers),
                    "login_or_error_page": identification.is_login_or_error_page,
                    "readable": identification.is_readable,
                },
                occurred_at=occurred_at,
            )
        self._transition(
            request_id,
            to_state=DownloadRequestState.MATCHED,
            trigger="unique_high_confidence_content_match",
            guard_evidence={
                "content_sha256": identification.sha256,
                "identifiers": list(matched_ids),
            },
            content_digest=identification.sha256,
            updates={
                "matched_identifiers": tuple(matched_ids),
                "content_sha256": identification.sha256,
                "media_type": identification.media_type,
            },
            occurred_at=occurred_at,
        )
        return self.accept(
            request_id,
            filename=filename,
            content=content,
            media_type=media_type,
            occurred_at=occurred_at,
        )

    # ── 匹配（规范化 + 自动比对其他活跃请求） ────────────────────────────────

    def _match_guard(
        self,
        request: DownloadRequest,
        identification: ContentIdentification,
        other_active_requests: tuple[DownloadRequest, ...],
    ) -> tuple[bool, tuple[str, ...], str | None]:
        if identification.is_login_or_error_page:
            return False, (), "收到的是登录提示页或错误页，请下载附件原文后重新放入。"
        if not identification.is_readable:
            return False, (), "文件残缺或不可读，请重新下载完整附件后放入。"
        request_identifiers = _request_identifier_set(request)
        content_ids = set(identification.identifiers)
        matched = tuple(sorted(request_identifiers & content_ids))
        if not matched:
            return False, (), "文件内容与本请求的目标资料不一致（错附件），请核对后重新下载。"
        text = identification.embedded_text
        matched_title = _title_matches(request.title, text)
        has_doi = any(item.startswith("10.") for item in matched)
        if not has_doi and not matched_title:
            return False, (), "标识符匹配但标题无法核对，存在歧义，请确认后重新放入。"
        # 自动比对其他活跃请求：一份文件不能被两个目标文档静默接受
        for other in other_active_requests:
            other_ids = _request_identifier_set(other)
            if content_ids & other_ids:
                return False, (), "文件同时匹配多个下载请求，存在歧义，请按提示重新放入。"
        return True, matched, None

    def match_file(
        self,
        request_id: str,
        *,
        filename: str,
        content: bytes,
        media_type: str,
        other_candidate_requests: tuple[DownloadRequest, ...] = (),
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        _validate_file_type(content, filename, media_type)
        request = self.load_request(request_id)
        _assert_role_type_coherent(request.document_role, media_type)
        if self._already_matched(request, content):
            return request
        if request.state is not DownloadRequestState.FILE_DETECTED:
            raise UndeclaredTransitionError(
                f"未声明的迁移：文件未发现前不能匹配（{request.state.value}）"
            )
        identification = identify_content(content, media_type)
        others = tuple(other_candidate_requests) + self._active_others(request_id)
        matched, matched_ids, reason = self._match_guard(
            request,
            identification,
            others,
        )
        if matched:
            return self._transition(
                request_id,
                to_state=DownloadRequestState.MATCHED,
                trigger="unique_high_confidence_content_match",
                guard_evidence={
                    "content_sha256": identification.sha256,
                    "identifiers": list(matched_ids),
                },
                content_digest=identification.sha256,
                updates={
                    "matched_identifiers": tuple(matched_ids),
                    "content_sha256": identification.sha256,
                    "media_type": identification.media_type,
                },
                occurred_at=occurred_at,
            )
        return self._quarantine(
            request_id,
            reason_zh=cast(str, reason),
            trigger="content_mismatch",
            guard_evidence={
                "content_sha256": identification.sha256,
                "identifiers": list(identification.identifiers),
                "login_or_error_page": identification.is_login_or_error_page,
                "readable": identification.is_readable,
            },
            occurred_at=occurred_at,
        )

    # ── 隔离 ──────────────────────────────────────────────────────────────────

    def _quarantine(
        self,
        request_id: str,
        *,
        reason_zh: str,
        trigger: str,
        guard_evidence: dict[str, Any],
        occurred_at: datetime | None,
    ) -> DownloadRequest:
        request = self.load_request(request_id)
        quarantine_dir = self.project_root / "evidence/quarantine" / request_id
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        rejected_path = None
        source = (
            (self.project_root / request.inbox_directory / request.original_filename)
            if request.original_filename
            else None
        )
        if source is not None and source.exists():
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            digest_dir = quarantine_dir / digest[:16]
            digest_dir.mkdir(parents=True, exist_ok=True)
            target = digest_dir / source.name
            if not target.exists():
                os.replace(source, target)
            rejected_path = f"evidence/quarantine/{request_id}/{digest_dir.name}/{source.name}"
        note = quarantine_dir / "处理说明.md"
        if rejected_path is not None:
            _record_quarantine_note(
                note,
                request.original_filename or "附件",
                reason_zh,
            )
        elif not request.quarantine_rejected_paths:
            _record_quarantine_note(note, "未能识别文件名的附件", reason_zh)
        updated = self._transition(
            request_id,
            to_state=DownloadRequestState.NEEDS_RE_DOWNLOAD,
            trigger=trigger,
            guard_evidence={
                **guard_evidence,
                "quarantine_directory": f"evidence/quarantine/{request_id}",
                "rejected_path": rejected_path,
                "reason_zh": reason_zh,
            },
            content_digest=guard_evidence.get("content_sha256", ""),
            updates={
                "quarantine_reason_zh": reason_zh,
                "quarantine_rejected_paths": (
                    (*request.quarantine_rejected_paths, rejected_path)
                    if rejected_path and rejected_path not in request.quarantine_rejected_paths
                    else request.quarantine_rejected_paths
                ),
            },
            occurred_at=occurred_at,
        )
        _regenerate_download_list(self.download_log_path, self.requests_path)
        return updated

    def quarantine(
        self,
        request_id: str,
        *,
        reason_zh: str,
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        request = self.load_request(request_id)
        if request.state is DownloadRequestState.NEEDS_RE_DOWNLOAD:
            return request
        if request.state not in (DownloadRequestState.FILE_DETECTED, DownloadRequestState.MATCHED):
            raise UndeclaredTransitionError(
                f"未声明的迁移：隔离只能在发现/匹配后执行（{request.state.value}）"
            )
        return self._quarantine(
            request_id,
            reason_zh=reason_zh,
            trigger="explicit_quarantine",
            guard_evidence={
                "reason_zh": reason_zh,
                "content_sha256": request.content_sha256 or request.request_id,
            },
            occurred_at=occurred_at,
        )

    def re_request(
        self,
        request_id: str,
        *,
        reason_zh: str,
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        request = self.load_request(request_id)
        if request.state is DownloadRequestState.AWAITING_USER:
            return request
        if request.state is not DownloadRequestState.NEEDS_RE_DOWNLOAD:
            raise UndeclaredTransitionError(
                f"重新请求只能在需要重新下载后执行：{request.state.value}"
            )
        inbox_dir = self.project_root / request.inbox_directory
        inbox_dir.mkdir(parents=True, exist_ok=True)
        updated = self._transition(
            request_id,
            to_state=DownloadRequestState.AWAITING_USER,
            trigger="deduplicated_re_request",
            guard_evidence={"reason_zh": reason_zh},
            content_digest=request.request_id,
            updates={
                "quarantine_reason_zh": None,
                "attempt_number": request.attempt_number + 1,
            },
            occurred_at=occurred_at,
        )
        _regenerate_download_list(self.download_log_path, self.requests_path)
        return updated

    # ── 接受：收件目录内原地规范命名 + 重抽取任务（全部幂等） ────────────────

    def _append_manual_mapping(self, mapping: dict[str, Any]) -> str:
        """在原地改名之前写入可恢复、冲突感知的映射回执。"""
        mapping_id = stable_id(
            "manual-source-mapping",
            str(mapping["request_id"]),
            str(mapping["content_sha256"]),
            str(mapping["target_relative_path"]),
        )
        stable_mapping = {
            key: value for key, value in mapping.items() if key not in {"mapping_id", "recorded_at"}
        }
        existing: list[dict[str, Any]] = []
        if self.manual_mapping_path.exists():
            existing = [
                json.loads(line)
                for line in self.manual_mapping_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        for record in existing:
            if record.get("mapping_id") != mapping_id:
                continue
            existing_stable = {
                key: value
                for key, value in record.items()
                if key not in {"mapping_id", "recorded_at"}
            }
            if existing_stable != stable_mapping:
                raise DownloadRequestError("同一补件映射标识对应了不同内容，拒绝覆盖")
            return mapping_id
        _append_jsonl(
            self.manual_mapping_path,
            {
                "mapping_id": mapping_id,
                **stable_mapping,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )
        return mapping_id

    def accept(
        self,
        request_id: str,
        *,
        filename: str,
        content: bytes,
        media_type: str,
        version_or_date: str | None = None,
        occurred_at: datetime | None = None,
    ) -> DownloadRequest:
        """匹配后在唯一收件目录中原子改名；不复制、移动或改写用户文件。"""
        _validate_file_type(content, filename, media_type)
        request = self.load_request(request_id)
        _assert_role_type_coherent(request.document_role, media_type)
        digest = hashlib.sha256(content).hexdigest()
        if request.state is DownloadRequestState.ACCEPTED:
            if request.content_sha256 != digest:
                raise DownloadRequestError("已接受资料与本次文件内容不一致")
            # 接受后的重放是 no-op：保留收件目录中的规范文件，不删除用户文件。
            return request
        if request.state is not DownloadRequestState.MATCHED:
            raise UndeclaredTransitionError(f"接受只能在匹配后执行（{request.state.value}）")
        timestamp = occurred_at or datetime.now(UTC)
        identification = identify_content(content, media_type)
        if not identification.is_readable or identification.is_login_or_error_page:
            raise DownloadRequestError("不可读或登录/错误页内容不得接受")
        if request.content_sha256 not in (None, digest):
            raise DownloadRequestError("已发现文件与接受内容摘要不一致")

        original_name = request.original_filename or Path(filename).name
        safe_name = Path(filename).name
        if not safe_name or safe_name != filename:
            raise DownloadRequestError("补件文件名必须是收件目录中的单一文件名")
        inbox_dir = self.project_root / request.inbox_directory
        inbox_dir.mkdir(parents=True, exist_ok=True)
        inbox_source = inbox_dir / safe_name
        if not inbox_source.is_file():
            raise DownloadRequestError("接受必须引用收件目录中实际存在的原文件")
        actual_bytes = inbox_source.read_bytes()
        if actual_bytes != content or hashlib.sha256(actual_bytes).hexdigest() != digest:
            raise DownloadRequestError("收件目录原文件内容与接受内容摘要不一致")

        basis = _canonical_basis(request)
        canonical = _canonical_filename(
            basis=basis,
            document_role=request.document_role,
            version_or_date=version_or_date,
            digest=digest,
            original_extension=Path(original_name).suffix or ".bin",
        )
        canonical_path = inbox_dir / canonical
        if canonical_path == inbox_source:
            collision_check = "same_path"
        elif canonical_path.exists():
            existing_digest = hashlib.sha256(canonical_path.read_bytes()).hexdigest()
            collision_check = "conflict"
            self._append_manual_mapping(
                {
                    "request_id": request_id,
                    "original_filename": original_name,
                    "content_sha256": digest,
                    "doi": request.doi,
                    "pmid": request.pmid,
                    "registry_identifiers": request.registry_identifiers,
                    "target_filename": canonical,
                    "target_relative_path": f"{request.inbox_directory}/{canonical}",
                    "collision_check": collision_check,
                    "existing_target_sha256": existing_digest,
                }
            )
            raise DownloadRequestError("收件目录规范文件名已存在，拒绝覆盖")
        else:
            collision_check = "clear"

        # Compatibility guard for stale copied archives: it never receives a
        # new byte, but a pre-existing drift is still a hard conflict.
        legacy_path = self.project_root / "evidence/library" / request_id / canonical
        if legacy_path.is_file():
            legacy_digest = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
            if legacy_digest != digest:
                self._append_manual_mapping(
                    {
                        "request_id": request_id,
                        "original_filename": original_name,
                        "content_sha256": digest,
                        "doi": request.doi,
                        "pmid": request.pmid,
                        "registry_identifiers": request.registry_identifiers,
                        "target_filename": canonical,
                        "target_relative_path": f"{request.inbox_directory}/{canonical}",
                        "collision_check": "legacy-library-conflict",
                        "existing_target_sha256": legacy_digest,
                    }
                )
                raise DownloadRequestError("历史归档同名文件摘要不一致，拒绝接受")

        canonical_relative = f"{request.inbox_directory}/{canonical}"
        mapping_id = self._append_manual_mapping(
            {
                "request_id": request_id,
                "original_filename": original_name,
                "content_sha256": digest,
                "doi": request.doi,
                "pmid": request.pmid,
                "registry_identifiers": request.registry_identifiers,
                "target_filename": canonical,
                "target_relative_path": canonical_relative,
                "collision_check": collision_check,
                "existing_target_sha256": None,
            }
        )
        if canonical_path != inbox_source:
            try:
                os.replace(inbox_source, canonical_path)
            except OSError as error:
                raise DownloadRequestError("收件目录原地规范命名失败，未接受补件") from error

        source_version_id = stable_id(
            "source-version",
            stable_id("source", request.project_id, request.trial_id or request.title),
            digest,
        )

        job_ids: list[str] = []
        for gap_id in request.missing_fields:
            job_id = stable_id(
                "re-extraction",
                request_id,
                source_version_id,
                gap_id,
            )
            job = {
                "job_id": job_id,
                "request_id": request_id,
                "source_version_id": source_version_id,
                "gap_id": gap_id,
                "original_filename": original_name,
                "canonical_relative_path": canonical_relative,
                "state": "queued",
                "extraction_mode": (
                    "ocr_required" if identification.requires_ocr else "embedded_text"
                ),
                "created_at": timestamp.isoformat(),
            }
            self._append_re_extraction_job(job)
            job_ids.append(job_id)

        accepted_request = self._transition(
            request_id,
            to_state=DownloadRequestState.ACCEPTED,
            trigger="content_accept_in_place_rename",
            guard_evidence={
                "original_filename": original_name,
                "original_filename_sha256": digest,
                "doi": request.doi,
                "pmid": request.pmid,
                "registry_identifiers": list(request.registry_identifiers),
                "canonical_filename": canonical,
                "canonical_relative_path": canonical_relative,
                "collision_check": collision_check,
                "manual_mapping_id": mapping_id,
                "source_version_id": source_version_id,
                "re_extraction_job_ids": job_ids,
            },
            content_digest=digest,
            updates={
                "canonical_filename": canonical,
                "canonical_relative_path": canonical_relative,
                "source_version_id": source_version_id,
                "re_extraction_job_ids": tuple(job_ids),
                "content_sha256": digest,
                "media_type": media_type,
            },
            occurred_at=timestamp,
        )
        _regenerate_download_list(self.download_log_path, self.requests_path)
        return accepted_request

    def _append_re_extraction_job(self, job: dict[str, Any]) -> None:
        """按稳定 job_id 幂等且冲突感知地追加：同 ID 同内容为 no-op，
        同 ID 不同内容失败关闭；崩溃后重放不重复。"""
        self.re_extraction_path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if self.re_extraction_path.exists():
            existing = [
                json.loads(line)
                for line in self.re_extraction_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        for record in existing:
            if record.get("job_id") == job["job_id"]:
                stable_record = {key: value for key, value in record.items() if key != "created_at"}
                stable_job = {key: value for key, value in job.items() if key != "created_at"}
                if stable_record == stable_job:
                    return  # 相同重试：no-op
                raise DownloadRequestError("同一重抽取任务标识对应了不同内容，拒绝覆盖")
        _append_jsonl(self.re_extraction_path, job)
