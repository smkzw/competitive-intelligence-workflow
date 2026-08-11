from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.ids import stable_id

EligibilityDecision = Literal["included", "excluded", "review_pending"]
ResolvedDecision = Literal["included", "excluded"]


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("创新药本体字段不能为空")
    return normalized


class TherapyComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    modality: str
    evidence_fragment_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("name", "modality")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("evidence_fragment_ids")
    @classmethod
    def _evidence_is_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("创新药纳排证据不得重复")
        return normalized


class TherapyRegimen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    components: tuple[TherapyComponent, ...] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _name_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class EligibilityRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    label_zh: str
    reason_zh: str

    @field_validator("rule_id", "label_zh", "reason_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class BoundaryReviewPolicy(EligibilityRule):
    modalities: tuple[str, ...] = Field(min_length=1)

    @field_validator("modalities")
    @classmethod
    def _modalities_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("边界模态不得重复")
        return normalized


class InnovationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    policy_id: Literal["innovation-therapy-v1"]
    version: Literal["1.0"]
    included: dict[str, EligibilityRule]
    excluded: dict[str, EligibilityRule]
    boundary_review: BoundaryReviewPolicy

    @model_validator(mode="after")
    def _rule_sets_do_not_overlap(self) -> InnovationPolicy:
        overlap = set(self.included) & set(self.excluded)
        if overlap:
            raise ValueError(f"创新与排除规则重叠：{sorted(overlap)}")
        if set(self.boundary_review.modalities) & (set(self.included) | set(self.excluded)):
            raise ValueError("边界审查模态不能同时被明确纳入或排除")
        return self


class EligibilityReviewReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewer_id: str
    decision: ResolvedDecision
    rationale: str
    rule_version: str
    evidence_fragment_ids: tuple[str, ...] = Field(min_length=1)
    reviewed_at: datetime

    @field_validator("reviewer_id", "rationale", "rule_version")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("reviewed_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("审查回执时间必须包含时区")
        return value


class ComponentEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    component_id: str
    component_name: str
    modality: str
    decision: EligibilityDecision
    rule_id: str
    rule_version: str
    reason_zh: str
    evidence_fragment_ids: tuple[str, ...] = Field(min_length=1)
    boundary_reason: str | None
    review_receipt: EligibilityReviewReceipt | None


class RegimenEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    regimen_id: str
    regimen_name: str
    decision: EligibilityDecision
    rule_version: str
    component_results: tuple[ComponentEligibility, ...]
    competitor_component_ids: tuple[str, ...]
    competitor_profile_component_names: tuple[str, ...]
    innovation_component_count: int = Field(ge=0)
    regimen_count: int = Field(ge=0, le=1)
    reason_zh: str


class CompetitorUniverseDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    universe_closed: bool
    eligible_component_ids: tuple[str, ...]
    allowed_downstream_nodes: tuple[Literal["gate", "snapshot", "render"], ...]
    audit_records: tuple[ComponentEligibility, ...]


class InnovationOntology:
    def __init__(self, policy: InnovationPolicy) -> None:
        self.policy = policy

    @classmethod
    def from_yaml(cls, path: Path) -> InnovationOntology:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise ValueError("无法读取创新药本体规则") from error
        if not isinstance(payload, dict):
            raise ValueError("创新药本体规则顶层必须是对象")
        return cls(InnovationPolicy.model_validate(cast(dict[str, object], payload)))

    def evaluate_component(self, component: TherapyComponent) -> ComponentEligibility:
        modality = component.modality.casefold()
        if modality in self.policy.included:
            decision: EligibilityDecision = "included"
            rule = self.policy.included[modality]
            boundary_reason = None
        elif modality in self.policy.excluded:
            decision = "excluded"
            rule = self.policy.excluded[modality]
            boundary_reason = None
        else:
            decision = "review_pending"
            rule = self.policy.boundary_review
            boundary_reason = (
                f"{component.name}未命中明确创新或排除规则，需核验创新属性与适应症语境"
            )
        return ComponentEligibility(
            component_id=stable_id("therapy-component", component.name, modality),
            component_name=component.name,
            modality=modality,
            decision=decision,
            rule_id=rule.rule_id,
            rule_version=self.policy.version,
            reason_zh=rule.reason_zh,
            evidence_fragment_ids=component.evidence_fragment_ids,
            boundary_reason=boundary_reason,
            review_receipt=None,
        )

    def review_boundary(
        self,
        pending: ComponentEligibility,
        *,
        decision: ResolvedDecision,
        reviewer_id: str,
        rationale: str,
        evidence_fragment_ids: tuple[str, ...],
        reviewed_at: datetime | None = None,
    ) -> ComponentEligibility:
        if pending.decision != "review_pending" or pending.review_receipt is not None:
            raise ValueError("只有尚未处置的边界项目可以提交独立审查")
        receipt = EligibilityReviewReceipt(
            reviewer_id=reviewer_id,
            decision=decision,
            rationale=rationale,
            rule_version=self.policy.version,
            evidence_fragment_ids=evidence_fragment_ids,
            reviewed_at=reviewed_at or datetime.now(UTC),
        )
        return pending.model_copy(
            update={
                "decision": decision,
                "reason_zh": rationale,
                "review_receipt": receipt,
            }
        )

    def evaluate_regimen(self, regimen: TherapyRegimen) -> RegimenEligibility:
        component_results = tuple(
            self.evaluate_component(component) for component in regimen.components
        )
        included = tuple(item for item in component_results if item.decision == "included")
        pending = tuple(item for item in component_results if item.decision == "review_pending")
        if pending:
            decision: EligibilityDecision = "review_pending"
            reason = "方案含尚待独立审查的边界组件，竞品宇宙暂不能闭合"
            regimen_count = 0
        elif included:
            decision = "included"
            reason = "方案包含明确适格的创新组件；传统背景治疗不单独计为竞品"
            regimen_count = 1
        else:
            decision = "excluded"
            reason = "方案仅含传统或明确排除组件，不属于创新药竞品范围"
            regimen_count = 0
        return RegimenEligibility(
            regimen_id=stable_id(
                "therapy-regimen",
                regimen.name,
                *(item.component_id for item in component_results),
            ),
            regimen_name=regimen.name,
            decision=decision,
            rule_version=self.policy.version,
            component_results=component_results,
            competitor_component_ids=tuple(item.component_id for item in included),
            competitor_profile_component_names=tuple(
                item.component_name for item in included
            ),
            innovation_component_count=len(included),
            regimen_count=regimen_count,
            reason_zh=reason,
        )


def close_competitor_universe(
    component_results: tuple[ComponentEligibility, ...],
) -> CompetitorUniverseDecision:
    pending = any(item.decision == "review_pending" for item in component_results)
    return CompetitorUniverseDecision(
        universe_closed=not pending,
        eligible_component_ids=tuple(
            item.component_id for item in component_results if item.decision == "included"
        ),
        allowed_downstream_nodes=() if pending else ("gate", "snapshot", "render"),
        audit_records=component_results,
    )
