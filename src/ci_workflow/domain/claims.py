from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactReviewState

ClaimKind = Literal["direct_evidence", "deterministic_calculation", "synthesis"]


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("声明字段不能为空")
    return normalized


class ClaimFactLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_version_id: str
    support_role: Literal["supports", "limits", "contradicts"]
    fact_review_state: Literal["accepted"]

    @field_validator("fact_version_id")
    @classmethod
    def _fact_version_id_is_not_blank(cls, value: str) -> str:
        return _text(value)


class DeterministicCalculationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["treatment_minus_control"]
    formula_zh: str
    input_fact_version_ids: tuple[str, str]
    input_values: tuple[float, float]
    result: float
    unit: str

    @field_validator("formula_zh", "unit")
    @classmethod
    def _calculation_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("input_fact_version_ids")
    @classmethod
    def _calculation_facts_are_distinct(cls, values: tuple[str, str]) -> tuple[str, str]:
        normalized = tuple(_text(value) for value in values)
        if normalized[0] == normalized[1]:
            raise ValueError("确定性计算必须引用两个不同事实")
        return (normalized[0], normalized[1])

    @model_validator(mode="after")
    def _result_is_reproducible(self) -> DeterministicCalculationRecord:
        expected = round(self.input_values[0] - self.input_values[1], 12)
        if self.result != expected:
            raise ValueError("确定性计算结果不能由输入值复算")
        return self


class ClaimVersion(BaseModel):
    """由事实支持的不可变报告声明版本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    claim_id: str
    claim_version_id: str
    claim_text: str
    claim_kind: ClaimKind
    fact_links: tuple[ClaimFactLink, ...] = Field(min_length=1)
    supporting_fact_version_ids: tuple[str, ...] = Field(min_length=1)
    calculation: DeterministicCalculationRecord | None
    synthesis_method_zh: str | None
    ai_disclosure_label_zh: Literal["AI 综合判断"] | None
    review_state: FactReviewState
    created_at: datetime
    supersedes_claim_version_id: str | None = None

    @field_validator("claim_id", "claim_version_id", "claim_text")
    @classmethod
    def _claim_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("synthesis_method_zh", "supersedes_claim_version_id")
    @classmethod
    def _optional_claim_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("supporting_fact_version_ids")
    @classmethod
    def _supporting_facts_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("声明支持事实不得重复")
        return normalized

    @field_validator("created_at")
    @classmethod
    def _created_at_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("声明创建时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _claim_kind_contract_is_explicit(self) -> ClaimVersion:
        linked_ids = tuple(link.fact_version_id for link in self.fact_links)
        if linked_ids != self.supporting_fact_version_ids:
            raise ValueError("声明支持事实与事实链接不一致")
        if self.claim_kind == "direct_evidence":
            if (
                self.calculation is not None
                or self.synthesis_method_zh is not None
                or self.ai_disclosure_label_zh is not None
            ):
                raise ValueError("直接证据声明不得携带计算或 AI 综合字段")
        elif self.claim_kind == "deterministic_calculation":
            if self.calculation is None:
                raise ValueError("确定性计算声明必须保存可复算记录")
            if set(self.calculation.input_fact_version_ids) != set(
                self.supporting_fact_version_ids
            ):
                raise ValueError("确定性计算输入与支持事实不一致")
            if self.synthesis_method_zh is not None or self.ai_disclosure_label_zh is not None:
                raise ValueError("确定性计算声明不得冒充 AI 综合判断")
        elif (
            self.calculation is not None
            or self.synthesis_method_zh is None
            or self.ai_disclosure_label_zh != "AI 综合判断"
        ):
            raise ValueError("AI 综合判断必须明确标识方法，且不得冒充确定性计算")
        if self.claim_kind == "synthesis" and not self.claim_text.startswith(
            "AI 综合判断："
        ):
            raise ValueError("AI 综合判断必须在文字中明确标识")
        return self
