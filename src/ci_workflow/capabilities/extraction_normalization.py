from __future__ import annotations

import hashlib
import json
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceFragmentRecord, SourceVersionRecord
from ci_workflow.domain.facts import (
    AtomicFactVersion,
    NormalizationRecord,
    NormalizedValue,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.content_store import EvidenceRepository

_VERIFIED_FRAGMENT_TOKEN = object()


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("事实抽取字段不能为空")
    return normalized


class VerifiedEvidenceFragment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fragment: EvidenceFragmentRecord
    reopened_original_text: str
    source_version: SourceVersionRecord

    @model_validator(mode="before")
    @classmethod
    def _requires_repository_verification(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if (info.context or {}).get("verified_fragment_token") is not _VERIFIED_FRAGMENT_TOKEN:
            raise ValueError("已重开证据片段只能由项目真源库验真后创建")
        return value

    @field_validator("reopened_original_text")
    @classmethod
    def _reopened_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("重开的证据片段不能为空")
        return value

    @model_validator(mode="after")
    def _reopened_text_matches_fragment(self) -> VerifiedEvidenceFragment:
        digest = hashlib.sha256(self.fragment.original_text.encode("utf-8")).hexdigest()
        if digest != self.fragment.content_sha256:
            raise ValueError("证据片段原文与摘要不一致")
        if self.reopened_original_text != self.fragment.original_text:
            raise ValueError("重开原文与证据片段不一致")
        if self.source_version.source_version_id != self.fragment.source_version_id:
            raise ValueError("已重开片段与来源版本不一致")
        return self


def verify_reopened_fragment(
    fragment: EvidenceFragmentRecord,
    *,
    reopened_original_text: str,
    source_version_id: str,
    repository: EvidenceRepository,
) -> VerifiedEvidenceFragment:
    normalized_source_version_id = _text(source_version_id)
    source_version = repository.verify_reopened_fragment_record(
        fragment,
        reopened_original_text=reopened_original_text,
        source_version_id=normalized_source_version_id,
    )
    return VerifiedEvidenceFragment.model_validate(
        {
            "fragment": fragment,
            "reopened_original_text": reopened_original_text,
            "source_version": source_version,
        },
        context={"verified_fragment_token": _VERIFIED_FRAGMENT_TOKEN},
    )


class AtomicFactExtractionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: str
    field_id: str
    raw_value: str
    unit: str | None
    context: str
    arm_id: str | None
    cohort_id: str | None
    population: str
    timepoint: str | None
    time_window: str | None
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    extraction_method: str
    quality_state: str
    disclosure_maturity: str
    source_role: str
    disclosure_state: FactDisclosureState
    review_state: FactReviewState
    published_at: datetime | None
    effective_at: datetime | None
    created_at: datetime
    verified_fragment: VerifiedEvidenceFragment

    @field_validator(
        "entity_id",
        "field_id",
        "raw_value",
        "context",
        "population",
        "extraction_method",
        "quality_state",
        "disclosure_maturity",
        "source_role",
    )
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("unit", "arm_id", "cohort_id", "timepoint", "time_window")
    @classmethod
    def _optional_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("published_at", "effective_at", "created_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("事实抽取日期时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _raw_value_is_the_reopened_fragment(self) -> AtomicFactExtractionInput:
        if self.raw_value != self.verified_fragment.reopened_original_text:
            raise ValueError("事实原始表达必须等于精确重开的最小证据片段")
        return self


def extract_atomic_fact(input_data: AtomicFactExtractionInput) -> AtomicFactVersion:
    fragment = input_data.verified_fragment.fragment
    fact_id = stable_id(
        "fact",
        input_data.entity_id,
        input_data.field_id,
        input_data.context,
        input_data.arm_id or "not-applicable",
        input_data.cohort_id or "not-applicable",
        input_data.population,
        input_data.timepoint or "not-applicable",
        input_data.time_window or "not-applicable",
    )
    version_payload = json.dumps(
        input_data.model_dump(
            mode="json", exclude={"verified_fragment", "created_at", "review_state"}
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return AtomicFactVersion(
        fact_id=fact_id,
        fact_version_id=stable_id(
            "fact-version", fact_id, fragment.fragment_id, version_payload
        ),
        entity_id=input_data.entity_id,
        field_id=input_data.field_id,
        raw_value=input_data.raw_value,
        unit=input_data.unit,
        context=input_data.context,
        arm_id=input_data.arm_id,
        cohort_id=input_data.cohort_id,
        population=input_data.population,
        timepoint=input_data.timepoint,
        time_window=input_data.time_window,
        numerator=input_data.numerator,
        denominator=input_data.denominator,
        primary_fragment_id=fragment.fragment_id,
        source_fragment_ids=(fragment.fragment_id,),
        extraction_method=input_data.extraction_method,
        quality_state=input_data.quality_state,
        disclosure_maturity=input_data.disclosure_maturity,
        source_role=input_data.source_role,
        disclosure_state=input_data.disclosure_state,
        review_state=input_data.review_state,
        published_at=input_data.published_at,
        effective_at=input_data.effective_at,
        created_at=input_data.created_at,
    )


class FactNormalizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    rule_version: str
    method_zh: str
    normalized_value: NormalizedValue
    normalized_unit: str | None
    reverse_expression: str
    created_at: datetime

    @field_validator("rule_id", "rule_version", "method_zh", "reverse_expression")
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
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("规范化日期时间必须包含明确时区")
        return value


def normalize_fact(
    fact: AtomicFactVersion, normalization_input: FactNormalizationInput
) -> AtomicFactVersion:
    if fact.raw_value is None:
        raise ValueError("没有原始表达的事实不能规范化")
    if fact.normalization is not None:
        previous = fact.normalization
        same_rule = (
            previous.rule_id == normalization_input.rule_id
            and previous.rule_version == normalization_input.rule_version
        )
        if same_rule:
            same_result = (
                previous.method_zh == normalization_input.method_zh
                and previous.normalized_value == normalization_input.normalized_value
                and previous.normalized_unit == normalization_input.normalized_unit
                and previous.reverse_expression == normalization_input.reverse_expression
            )
            if same_result:
                return fact
            raise ValueError("同一规范化规则版本不得产生不同结果")
    record = NormalizationRecord(
        rule_id=normalization_input.rule_id,
        rule_version=normalization_input.rule_version,
        method_zh=normalization_input.method_zh,
        original_raw_value=fact.raw_value,
        normalized_value=normalization_input.normalized_value,
        normalized_unit=normalization_input.normalized_unit,
        reverse_expression=normalization_input.reverse_expression,
        created_at=normalization_input.created_at,
    )
    record_json = json.dumps(
        record.model_dump(mode="json", exclude={"created_at"}),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return AtomicFactVersion.model_validate(
        {
            **fact.model_dump(),
            "fact_version_id": stable_id(
                "fact-version",
                fact.fact_id,
                fact.fact_version_id,
                record_json,
            ),
            "normalized_value": record.normalized_value,
            "normalized_unit": record.normalized_unit,
            "normalization": record.model_dump(),
            "created_at": normalization_input.created_at,
            "supersedes_fact_version_id": fact.fact_version_id,
        }
    )


def reverse_normalized_fact(fact: AtomicFactVersion) -> str:
    if fact.normalization is None:
        raise ValueError("事实没有可反向查看的规范化记录")
    if fact.raw_value != fact.normalization.original_raw_value:
        raise ValueError("事实原始表达与规范化记录不一致")
    return fact.normalization.original_raw_value
