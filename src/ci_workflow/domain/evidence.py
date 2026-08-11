from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256 = re.compile(r"[0-9a-f]{64}")
DateEvidenceState = Literal["reported", "not_publicly_disclosed", "not_applicable"]


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
    page: int | None = Field(default=None, ge=1)
    table: str | None = None
    paragraph: str | None = None
    url: str | None = None

    @field_validator("document_role")
    @classmethod
    def _role_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("field_path", "table", "paragraph", "url")
    @classmethod
    def _optional_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @model_validator(mode="after")
    def _has_precise_anchor(self) -> EvidenceLocator:
        if not any((self.field_path, self.page, self.table, self.paragraph, self.url)):
            raise ValueError("证据位置必须包含字段、页、表、段落或链接")
        return self


class DateEvidence(BaseModel):
    """一个来源日期及其披露状态和定位。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: DateEvidenceState
    value: datetime | None
    locator: EvidenceLocator

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
        return self


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


class SourceVersionRecord(BaseModel):
    """不可变来源版本；四类日期不得相互冒充。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    source_version_id: str
    source_id: str
    content_sha256: str
    content_relative_path: str
    media_type: str
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
    result_class: Literal[
        "content_acquired",
        "not_found",
        "access_blocked",
        "technical_failure",
        "unusable_content",
    ]
    error_class: str | None
    completeness_checks: tuple[str, ...] = Field(min_length=1)
    alternative_paths: tuple[str, ...] = Field(min_length=1)
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

    @field_validator("error_class", "parent_attempt_id")
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
        if self.result_class == "content_acquired" and self.content_sha256 is None:
            raise ValueError("取得内容时必须保存内容摘要")
        if self.result_class != "content_acquired" and self.error_class is None:
            raise ValueError("未取得内容时必须保存错误分类")
        return self


class InformationGainDiff(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    round: int = Field(ge=1)
    new_fields: tuple[str, ...]
    new_source_versions: tuple[str, ...]


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
