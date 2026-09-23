from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState

NormalizedValue = str | int | float | bool
_ZERO_EVIDENCE = re.compile(r"(?<![0-9.])0(?:\.0+)?\s*(?:%|/|$|\))")
_NUMERIC_DISCLOSURE = re.compile(
    r"^\s*[<>≤≥~≈]?\s*[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
    r"\s*(?:[%％]|[A-Za-z\u4e00-\u9fff][^\n]*)?\s*$"
)


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("事实字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("事实日期时间必须包含明确时区")
    return value


class NormalizationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    rule_version: str
    method_zh: str
    original_raw_value: str
    normalized_value: NormalizedValue
    normalized_unit: str | None
    reversible: Literal[True] = True
    reverse_expression: str
    created_at: datetime

    @field_validator(
        "rule_id",
        "rule_version",
        "method_zh",
        "original_raw_value",
        "reverse_expression",
    )
    @classmethod
    def _normalization_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("normalized_unit")
    @classmethod
    def _normalized_unit_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("created_at")
    @classmethod
    def _normalization_time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class AtomicFactVersion(BaseModel):
    """来源片段支持的一个不可变原子事实版本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    fact_id: str
    fact_version_id: str
    entity_id: str
    field_id: str
    raw_value: str | None
    normalized_value: NormalizedValue | None = None
    unit: str | None
    normalized_unit: str | None = None
    context: str
    arm_id: str | None
    cohort_id: str | None
    population: str
    timepoint: str | None
    time_window: str | None
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    primary_fragment_id: str
    source_fragment_ids: tuple[str, ...] = Field(min_length=1)
    extraction_method: str
    quality_state: str
    disclosure_maturity: str
    source_role: str
    disclosure_state: FactDisclosureState
    review_state: FactReviewState
    normalization: NormalizationRecord | None = None
    applicability_predicate_id: str | None = None
    unresolved_route_receipt_id: str | None = None
    published_at: datetime | None
    effective_at: datetime | None
    created_at: datetime
    supersedes_fact_version_id: str | None = None

    @field_validator(
        "fact_id",
        "fact_version_id",
        "entity_id",
        "field_id",
        "context",
        "population",
        "primary_fragment_id",
        "extraction_method",
        "quality_state",
        "disclosure_maturity",
        "source_role",
    )
    @classmethod
    def _fact_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "raw_value",
        "unit",
        "normalized_unit",
        "arm_id",
        "cohort_id",
        "timepoint",
        "time_window",
        "applicability_predicate_id",
        "unresolved_route_receipt_id",
        "supersedes_fact_version_id",
    )
    @classmethod
    def _optional_fact_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("source_fragment_ids")
    @classmethod
    def _fragment_ids_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("事实来源片段不得重复")
        return normalized

    @field_validator("published_at", "effective_at", "created_at")
    @classmethod
    def _fact_times_have_offsets(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _offset_datetime(value)

    @model_validator(mode="after")
    def _fact_contract_is_consistent(self) -> AtomicFactVersion:
        if self.disclosure_state is FactDisclosureState.USER_CLEARED:
            raise ValueError("用户清除是当前呈现状态，不得伪装为来源事实披露状态")
        if self.primary_fragment_id not in self.source_fragment_ids:
            raise ValueError("主要来源片段必须包含在事实来源片段中")
        if self.timepoint is None and self.time_window is None:
            raise ValueError("事实必须保存时间点或时间窗")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("事实分子不得大于分母")
        reported_states = {
            FactDisclosureState.REPORTED_VALUE,
            FactDisclosureState.REPORTED_ZERO,
            FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        }
        if self.disclosure_state in reported_states and self.raw_value is None:
            raise ValueError("已披露事实必须保留原始表达")
        if self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            if self.raw_value is None or _ZERO_EVIDENCE.search(self.raw_value) is None:
                raise ValueError("已报告零值必须有明确零值原文证据")
            if self.numerator is not None and self.numerator != 0:
                raise ValueError("已报告零值的分子必须为零")
            if isinstance(self.normalized_value, bool) or self.normalized_value not in (
                0,
                0.0,
                None,
            ):
                raise ValueError("已报告零值的规范值必须为零")
        missing_states = {
            FactDisclosureState.NOT_REPORTED,
            FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        }
        if (
            self.disclosure_state in missing_states
            and self.raw_value is not None
            and _NUMERIC_DISCLOSURE.fullmatch(self.raw_value) is not None
        ):
            raise ValueError("未报告或未公开状态不得携带数值型原始表达")
        if (
            self.disclosure_state is FactDisclosureState.NOT_APPLICABLE
            and self.applicability_predicate_id is None
        ):
            raise ValueError("不适用事实必须链接适用性谓词")
        if (
            self.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE
            and self.unresolved_route_receipt_id is None
        ):
            raise ValueError("路线未解决事实必须链接路由回执")
        if self.normalization is None:
            if self.normalized_value is not None or self.normalized_unit is not None:
                raise ValueError("规范值必须链接规范化记录")
        elif (
            self.normalized_value != self.normalization.normalized_value
            or self.normalized_unit != self.normalization.normalized_unit
            or self.raw_value != self.normalization.original_raw_value
        ):
            raise ValueError("规范值、原始值与规范化记录不一致")
        return self


class FactConflictMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_version_id: str
    observed_value: str
    source_fragment_ids: tuple[str, ...] = Field(min_length=1)
    source_role: str

    @field_validator("fact_version_id", "observed_value", "source_role")
    @classmethod
    def _conflict_member_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class FactConflictSet(BaseModel):
    """同一字段与比较范围内并存的互斥事实值。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    conflict_set_id: str
    entity_id: str
    field_id: str
    context: str
    arm_id: str | None
    cohort_id: str | None
    population: str
    timepoint: str | None
    time_window: str | None
    members: tuple[FactConflictMember, ...] = Field(min_length=2)
    member_fact_version_ids: tuple[str, ...] = Field(min_length=2)
    observed_values: tuple[str, ...] = Field(min_length=2)
    resolution_state: Literal["open", "resolved"]
    selected_fact_version_id: str | None
    resolution_note: str | None
    created_at: datetime

    @field_validator(
        "conflict_set_id", "entity_id", "field_id", "context", "population"
    )
    @classmethod
    def _conflict_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "arm_id",
        "cohort_id",
        "timepoint",
        "time_window",
        "selected_fact_version_id",
        "resolution_note",
    )
    @classmethod
    def _optional_conflict_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("created_at")
    @classmethod
    def _conflict_time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _conflict_members_and_resolution_are_consistent(self) -> FactConflictSet:
        expected_ids = tuple(member.fact_version_id for member in self.members)
        expected_values = tuple(sorted({member.observed_value for member in self.members}))
        if self.member_fact_version_ids != expected_ids:
            raise ValueError("冲突成员标识与成员明细不一致")
        if self.observed_values != expected_values or len(expected_values) < 2:
            raise ValueError("冲突集合必须保留至少两个不同值")
        if self.resolution_state == "open" and (
            self.selected_fact_version_id is not None or self.resolution_note is not None
        ):
            raise ValueError("未决冲突不得预选事实或填写裁决")
        if self.resolution_state == "resolved" and (
            self.selected_fact_version_id not in self.member_fact_version_ids
            or self.resolution_note is None
        ):
            raise ValueError("已裁决冲突必须选择成员事实并记录理由")
        return self
