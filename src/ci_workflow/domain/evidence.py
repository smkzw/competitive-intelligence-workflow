from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.ids import stable_id

_SHA256 = re.compile(r"[0-9a-f]{64}")
DateEvidenceState = Literal["reported", "not_publicly_disclosed", "not_applicable"]
DatePrecision = Literal["instant", "calendar_day"]


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("日期时间必须包含明确时区偏移")
    return value


class EvidenceLocator(BaseModel):
    """可回到来源字段、页、表或段落的精确位置。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_role: str
    field_path: str | None = None
    heading: str | None = None
    page: int | None = Field(default=None, ge=1)
    table: str | None = None
    row: str | None = None
    column: str | None = None
    paragraph: str | None = None
    url: str | None = None

    @field_validator("document_role")
    @classmethod
    def _role_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("field_path", "heading", "table", "row", "column", "paragraph", "url")
    @classmethod
    def _optional_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @model_validator(mode="after")
    def _has_precise_anchor(self) -> EvidenceLocator:
        if not any(
            (
                self.field_path,
                self.heading,
                self.page,
                self.table,
                self.row,
                self.column,
                self.paragraph,
                self.url,
            )
        ):
            raise ValueError("证据位置必须包含字段、页、表、段落或链接")
        return self


class DateEvidence(BaseModel):
    """一个来源日期及其披露状态和定位。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: DateEvidenceState
    value: datetime | None
    precision: DatePrecision = "instant"
    locator: EvidenceLocator

    def is_known_by(self, cutoff: datetime) -> bool:
        _offset_datetime(cutoff)
        if self.state != "reported" or self.value is None:
            return False
        if self.precision == "calendar_day":
            return cutoff >= self.value + timedelta(days=1) - timedelta(microseconds=1)
        return self.value <= cutoff

    @field_validator("value")
    @classmethod
    def _value_has_offset(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _offset_datetime(value)

    @model_validator(mode="after")
    def _state_matches_value(self) -> DateEvidence:
        if self.state == "reported" and self.value is None:
            raise ValueError("已披露日期必须有日期时间")
        if self.state != "reported" and self.value is not None:
            raise ValueError("未公开或不适用日期不得伪造日期时间")
        if self.state != "reported" and self.precision != "instant":
            raise ValueError("未公开或不适用日期不能声明日期精度")
        if (
            self.state == "reported"
            and self.precision == "calendar_day"
            and self.value is not None
            and any(
                (
                    self.value.hour,
                    self.value.minute,
                    self.value.second,
                    self.value.microsecond,
                )
            )
        ):
            raise ValueError("仅公开自然日的日期必须按来源时区零点保存")
        return self


def source_version_identity(
    source_id: str, content_sha256: str, *,
    published_at: DateEvidence, effective_at: DateEvidence, first_disclosed_at: DateEvidence,
    text_derivation: SourceTextDerivation | None = None,
) -> str:
    """V2 identity binds immutable date evidence; repeated downloads deduplicate.

    Old content-only IDs remain stored history. Re-ingestion uses this versioned
    identity and therefore requires fresh dependent review, never record edits.
    """
    dates = {}
    for role, evidence in (
        ("published_at", published_at), ("effective_at", effective_at),
        ("first_disclosed_at", first_disclosed_at),
    ):
        material = evidence.model_dump(mode="json")
        if evidence.value is not None and evidence.precision == "instant":
            material["value"] = evidence.value.astimezone(UTC).isoformat()
        dates[role] = material
    if text_derivation is not None:
        dates["text_derivation"] = text_derivation.model_dump(mode="json")
    encoded = json.dumps(dates, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return stable_id(
        "source-version", "date-identity-v2", source_id, content_sha256,
        hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    )


class ContentBlob(BaseModel):
    """内容寻址原文的相对路径记录。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sha256: str
    relative_path: str
    byte_size: int = Field(ge=0)
    media_type: str

    @field_validator("sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("内容摘要必须是小写 SHA-256")
        return value

    @field_validator("relative_path", "media_type")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CtgovRecordSelector(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    study_index: int = Field(ge=0, strict=True)
    nct_id: str = Field(pattern=r"^NCT[0-9]{8}$")


class SourceTextDerivation(BaseModel):
    """Explicit raw-asset to text derivation, never a PDF hash relabelled as text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    raw_asset: ContentBlob
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    method: Literal["utf8-strip-v1", "pypdf-text-v1", "ctgov-study-json-v1"]
    extractor_version: str = Field(min_length=1)
    record_selector: CtgovRecordSelector | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def _raw_path_and_method_are_bound(self) -> SourceTextDerivation:
        if self.raw_asset.byte_size < 1:
            raise ValueError("原始资产不得为空")
        digest = self.raw_asset.sha256
        if self.raw_asset.relative_path != f"evidence/raw/sha256/{digest[:2]}/{digest}.bin":
            raise ValueError("原始资产路径必须与摘要绑定")
        if (self.method == "pypdf-text-v1") != (self.raw_asset.media_type == "application/pdf"):
            raise ValueError("原始资产媒体类型与提取方法不一致")
        if (self.method == "ctgov-study-json-v1") != (self.record_selector is not None):
            raise ValueError("登记记录提取必须且只能绑定明确的记录选择器")
        if self.record_selector is not None and self.raw_asset.media_type != "application/json":
            raise ValueError("登记记录提取仅适用于原始JSON响应")
        return self


class SourceVersionRecord(BaseModel):
    """不可变来源版本；四类日期不得相互冒充。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    source_version_id: str
    source_id: str
    content_sha256: str
    content_relative_path: str
    media_type: str
    text_derivation: SourceTextDerivation | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    acquired_at: datetime
    acquired_locator: EvidenceLocator
    published_at: DateEvidence
    effective_at: DateEvidence
    first_disclosed_at: DateEvidence
    created_at: datetime

    @field_validator("source_version_id", "source_id", "content_relative_path", "media_type")
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("content_sha256")
    @classmethod
    def _content_digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("内容摘要必须是小写 SHA-256")
        return value

    @field_validator("acquired_at", "created_at")
    @classmethod
    def _record_datetimes_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _content_path_matches_digest(self) -> SourceVersionRecord:
        if self.text_derivation is not None and (
            self.text_derivation.text_sha256 != self.content_sha256
        ):
            raise ValueError("来源版本正文与原始资产派生摘要不一致")
        expected_path = (
            f"evidence/raw/sha256/{self.content_sha256[:2]}/"
            f"{self.content_sha256}.bin"
        )
        if self.content_relative_path != expected_path:
            raise ValueError("来源版本正文路径必须与内容摘要一致")
        return self


class EvidenceFragmentRecord(BaseModel):
    """来源原文中的一个可定位、不可变片段。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    fragment_id: str
    source_version_id: str
    locator: EvidenceLocator
    original_text: str
    content_sha256: str
    created_at: datetime

    @field_validator("fragment_id", "source_version_id", "original_text")
    @classmethod
    def _fragment_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("证据片段必须保留原文")
        return value

    @field_validator("content_sha256")
    @classmethod
    def _fragment_digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("片段摘要必须是小写 SHA-256")
        return value

    @field_validator("created_at")
    @classmethod
    def _created_at_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class SourceReceipt(BaseModel):
    """一次来源路线尝试的完整审计回执。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    receipt_id: str
    route_id: str
    strategy_unit_id: str
    entity_id: str
    gap_id: str
    claim_domain: str
    query_or_identifier: str
    language: str
    access_method: str
    attempt_index: int = Field(ge=1)
    started_at: datetime
    ended_at: datetime
    scheduled_backoff_ms: int = Field(ge=0)
    actual_backoff_ms: int = Field(ge=0)
    result_class: Literal[
        "content_acquired",
        "not_found",
        "network_error",
        "rate_limited",
        "captcha_required",
        "permission_denied",
        "proxy_error",
        "dns_error",
        "tls_error",
        "http_error",
        "parser_error",
        "tool_unavailable",
        "content_truncated",
    ]
    error_class: str | None
    completeness_checks: tuple[str, ...] = Field(min_length=1)
    alternative_paths: tuple[str, ...] = Field(min_length=1)
    source_version_id: str | None
    content_sha256: str | None
    diagnostic_confidence: Literal["low", "medium", "high"]
    parent_attempt_id: str | None
    recovery_round: int = Field(ge=0)

    @field_validator(
        "receipt_id",
        "route_id",
        "strategy_unit_id",
        "entity_id",
        "gap_id",
        "claim_domain",
        "query_or_identifier",
        "language",
        "access_method",
    )
    @classmethod
    def _receipt_text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("error_class", "parent_attempt_id", "source_version_id")
    @classmethod
    def _nullable_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @field_validator("completeness_checks", "alternative_paths")
    @classmethod
    def _list_items_are_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)

    @field_validator("content_sha256")
    @classmethod
    def _receipt_digest_is_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if _SHA256.fullmatch(value) is None:
            raise ValueError("回执内容摘要必须是小写 SHA-256")
        return value

    @field_validator("started_at", "ended_at")
    @classmethod
    def _receipt_datetimes_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _attempt_has_forward_time(self) -> SourceReceipt:
        if self.ended_at < self.started_at:
            raise ValueError("路线尝试结束时间不得早于开始时间")
        if self.result_class == "content_acquired" and (
            self.content_sha256 is None or self.source_version_id is None
        ):
            raise ValueError("取得内容时必须保存来源版本和内容摘要")
        if self.result_class != "content_acquired" and self.error_class is None:
            raise ValueError("未取得内容时必须保存错误分类")
        if self.result_class != "content_acquired" and self.source_version_id is not None:
            raise ValueError("未取得内容时不得伪造来源版本")
        return self


class InformationGainDiff(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    round: int = Field(ge=1)
    new_fields: tuple[str, ...]
    new_source_versions: tuple[str, ...]
    new_evidence_fragment_ids: tuple[str, ...] = ()
    changed_gate_unit_ids: tuple[str, ...] = ()
    reduced_conflict_set_ids: tuple[str, ...] = ()

    @field_validator(
        "new_fields",
        "new_source_versions",
        "new_evidence_fragment_ids",
        "changed_gate_unit_ids",
        "reduced_conflict_set_ids",
    )
    @classmethod
    def _gain_ids_are_unique_and_nonblank(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(normalized) != len(set(normalized)):
            raise ValueError("信息增益标识不得重复")
        return normalized


class EvidenceGap(BaseModel):
    """证据缺口及已穷尽策略和下一合法动作。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    gap_id: str
    gate_spec_id: str
    object_type: str
    object_id: str
    field_id: str
    current_state: Literal[
        "not_reported",
        "not_publicly_disclosed",
        "conflicting",
        "unresolved_due_to_route",
    ]
    required_context: str
    candidate_sources: tuple[str, ...] = Field(min_length=1)
    completed_strategies: tuple[str, ...]
    information_gain_diff: tuple[InformationGainDiff, ...] = Field(min_length=1)
    next_legal_action: str

    @field_validator(
        "gap_id",
        "gate_spec_id",
        "object_type",
        "object_id",
        "field_id",
        "required_context",
        "next_legal_action",
    )
    @classmethod
    def _gap_text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("candidate_sources", "completed_strategies")
    @classmethod
    def _gap_list_items_are_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)

    @model_validator(mode="after")
    def _information_gain_rounds_are_contiguous(self) -> EvidenceGap:
        rounds = tuple(item.round for item in self.information_gain_diff)
        if rounds != tuple(range(1, len(rounds) + 1)):
            raise ValueError("信息增益轮次必须从一开始连续递增")
        return self
