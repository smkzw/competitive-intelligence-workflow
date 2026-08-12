"""Task 3.1 证据门槛封闭模型与确定性决策内核。

GateSpec/GateResult/GateOverride 只描述关键证据单元、对象粒度、适用性谓词、
允许来源/披露状态、缺失/冲突策略和阈值；不负责搜索，也不生成用户报告。
评估输入必须绑定已闭合竞品宇宙，未知、重复、漏评或未证明为空的对象集合失败关闭。
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import (
    FactDisclosureState,
    FactReviewState,
    ReportKind,
)
from ci_workflow.domain.ids import stable_id

_REPORTED_STATES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)
_MISSING_STATES = frozenset(
    {
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    }
)
_SATISFYING_FACT_STATES = frozenset(
    {
        FactDisclosureState.REPORTED_VALUE,
        FactDisclosureState.REPORTED_ZERO,
        FactDisclosureState.NOT_APPLICABLE,
    }
)


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("证据门槛文本字段不能为空")
    return normalized


def _optional_text(value: str | None) -> str | None:
    return None if value is None else _text(value)


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("证据门槛日期时间必须包含明确时区")
    return value


class GateEvaluationError(RuntimeError):
    """评估输入未达到失败关闭要求。"""


class SourceRole(StrEnum):
    """规则来源角色封闭集合；不从自由文本推断。"""

    CLINICAL_TRIAL_REGISTRY = "clinical_trial_registry"
    REGULATORY_MATERIAL = "regulatory_material"
    PRIMARY_TRIAL_REPORT = "primary_trial_report"
    PROTOCOL_SAP = "protocol_sap"
    CONFERENCE_DISCLOSURE = "conference_disclosure"
    COMPANY_DISCLOSURE = "company_disclosure"
    DESIGNATED_INDUSTRY_SOURCE = "designated_industry_source"


class DisclosureMaturity(StrEnum):
    """披露成熟度按可比较序列保存，只用于比较，不替代 C 的来源角色判定。"""

    ATTRIBUTABLE_NUMERIC_DISCLOSURE = "attributable_numeric_disclosure"
    CONFERENCE_COMPLETE_NUMERICS = "conference_complete_numerics"
    REGISTRY_RESULT_OR_PRIMARY_REPORT = "registry_result_or_primary_report"
    FINAL_REGULATORY_CONCLUSION = "final_regulatory_conclusion"


class ConflictDisposition(StrEnum):
    """冲突可接受处置：关键单元只接受已解决并选择已接受事实。"""

    RESOLVED_SELECTED_ACCEPTED_FACT = "resolved_selected_accepted_fact"
    OPEN_CONFLICT_PRESERVED = "open_conflict_preserved"


class ConflictStrategy(StrEnum):
    """单元级冲突策略：关键单元只接受已解决冲突。"""

    RESOLVED_ONLY = "resolved_only"
    PRESERVE_OPEN = "preserve_open"


class MissingStrategy(StrEnum):
    """缺失策略：关键单元阻断；扩展单元保留准确披露状态。"""

    BLOCK = "block"
    PRESERVE_DISCLOSURE_STATE = "preserve_disclosure_state"


class GateBlockingLevel(StrEnum):
    """关键/扩展级别：阻断与建模但非阻断分层。"""

    CRITICAL = "critical"
    EXTENSION = "extension"


class GateObjectType(StrEnum):
    """对象范围：产品、试验、比较、组别、终点、时间点。"""

    PRODUCT = "product"
    TRIAL = "trial"
    COMPARISON = "comparison"
    GROUP = "group"
    ENDPOINT = "endpoint"
    TIMEPOINT = "timepoint"


class FactDomain(StrEnum):
    """事实域：设计、疗效、安全。"""

    TRIAL_DESIGN = "trial_design"
    EFFICACY = "efficacy"
    SAFETY = "safety"


class ObservationKind(StrEnum):
    """观察类型：只有观察性数值结果可触发；计划值不得触发。"""

    OBSERVED_RESULT = "observed_result"
    PLANNED_VALUE = "planned_value"
    TARGET_VALUE = "target_value"
    PROTOCOL_ASSUMPTION = "protocol_assumption"


class DevelopmentMaturity(StrEnum):
    """A 开发成熟度封闭集合；按状态集合适用规则，不当作单一线性排名。"""

    PRECLINICAL = "preclinical"
    CLINICAL = "clinical"
    SUBMISSION = "submission"
    APPROVED = "approved"
    PAUSED_TERMINATED_WITHDRAWN = "paused_terminated_withdrawn"


class ClinicalResultState(StrEnum):
    """A 临床结果状态封闭集合。"""

    NO_ELIGIBLE_CLINICAL_TRIAL = "no_eligible_clinical_trial"
    ELIGIBLE_TRIAL_WITHOUT_OBSERVED_NUMERIC_RESULTS = (
        "eligible_trial_without_observed_numeric_results"
    )
    HAS_OBSERVED_CLINICAL_NUMERIC_RESULTS = (
        "has_observed_clinical_numeric_results"
    )


class ContextField(StrEnum):
    """必需上下文字段封闭集合。"""

    NUMERIC_VALUE = "numeric_value"
    UNIT = "unit"
    DENOMINATOR = "denominator"
    SOURCE_LOCATION = "source_location"
    DEFINITION = "definition"
    DIRECTION = "direction"
    TIMEPOINT = "timepoint"
    ANALYSIS_POPULATION = "analysis_population"
    TREATMENT_GROUP = "treatment_group"
    CONTROL_GROUP = "control_group"
    EVENT_DEFINITION = "event_definition"
    TIME_WINDOW = "time_window"
    ENDPOINT_ID = "endpoint_id"


class GateUnitOutcome(StrEnum):
    """逐单元决定：满足、阻断、明确不适用、扩展缺失。"""

    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    EXTENSION_MISSING = "extension_missing"


class ReportDecision(StrEnum):
    """报告决定：全部适用关键单元满足才通过。"""

    PASSED = "passed"
    BLOCKED = "blocked"


class EmptySetReasonCode(StrEnum):
    """空对象集合证明的封闭原因代码；任意字符串不得证明空对象类。"""

    EXHAUSTIVE_SEARCH_NO_OBJECTS = "exhaustive_search_no_objects"
    INDICATION_RULE_EXCLUDES_OBJECT_CLASS = "indication_rule_excludes_object_class"
    STUDY_DESIGN_SINGLE_ARM = "study_design_single_arm"


class TrialDesignKind(StrEnum):
    """每项试验的设计类型封闭枚举：比较设计与单臂设计。"""

    COMPARATIVE = "comparative"
    SINGLE_ARM = "single_arm"


RESULT_BEARING_SOURCE_ROLES: tuple[SourceRole, ...] = (
    SourceRole.CLINICAL_TRIAL_REGISTRY,
    SourceRole.REGULATORY_MATERIAL,
    SourceRole.PRIMARY_TRIAL_REPORT,
    SourceRole.CONFERENCE_DISCLOSURE,
    SourceRole.COMPANY_DISCLOSURE,
    SourceRole.DESIGNATED_INDUSTRY_SOURCE,
)

_DISCLOSURE_MATURITY_RANK: dict[DisclosureMaturity, int] = {
    DisclosureMaturity.ATTRIBUTABLE_NUMERIC_DISCLOSURE: 1,
    DisclosureMaturity.CONFERENCE_COMPLETE_NUMERICS: 2,
    DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT: 3,
    DisclosureMaturity.FINAL_REGULATORY_CONCLUSION: 4,
}

_CONTEXT_FIELD_ATTRS: dict[ContextField, str] = {
    ContextField.NUMERIC_VALUE: "numeric_value",
    ContextField.UNIT: "unit",
    ContextField.DENOMINATOR: "denominator",
    ContextField.SOURCE_LOCATION: "source_location",
    ContextField.DEFINITION: "definition",
    ContextField.DIRECTION: "direction",
    ContextField.TIMEPOINT: "timepoint",
    ContextField.ANALYSIS_POPULATION: "analysis_population",
    ContextField.TREATMENT_GROUP: "treatment_group",
    ContextField.CONTROL_GROUP: "control_group",
    ContextField.EVENT_DEFINITION: "event_definition",
    ContextField.TIME_WINDOW: "time_window",
    ContextField.ENDPOINT_ID: "endpoint_id",
}

_SCOPE_ATTRIBUTE_IDS: tuple[tuple[str, str], ...] = (
    ("trial_id", "trial_ids"),
    ("comparison_id", "comparison_ids"),
    ("group_id", "group_ids"),
    ("endpoint_id", "endpoint_ids"),
    ("timepoint_id", "timepoint_ids"),
)

_PREFERRED_DISCLOSURE_ORDER: tuple[FactDisclosureState, ...] = (
    FactDisclosureState.REPORTED_VALUE,
    FactDisclosureState.REPORTED_ZERO,
    FactDisclosureState.BELOW_REPORTING_THRESHOLD,
    FactDisclosureState.CONFLICTING,
    FactDisclosureState.NOT_APPLICABLE,
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    FactDisclosureState.NOT_REPORTED,
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
)

ALL_FACT_DOMAINS: tuple[FactDomain, ...] = tuple(FactDomain)
ALL_OBSERVATION_KINDS: tuple[ObservationKind, ...] = tuple(ObservationKind)


def disclosure_maturity_rank(maturity: DisclosureMaturity) -> int:
    return _DISCLOSURE_MATURITY_RANK[maturity]


class GateVocabulary(BaseModel):
    """A/B/C 封闭词表；未知值在 YAML/JSON Schema 与 Pydantic 均被拒绝。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    development_maturity: tuple[DevelopmentMaturity, ...] = Field(min_length=1)
    clinical_result_states: tuple[ClinicalResultState, ...] = Field(min_length=1)
    observation_kinds: tuple[ObservationKind, ...] = Field(min_length=1)
    result_bearing_source_roles: tuple[SourceRole, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _vocabulary_is_closed_and_exact(self) -> GateVocabulary:
        if set(self.development_maturity) != set(DevelopmentMaturity):
            raise ValueError("开发成熟度必须是固定封闭集合")
        if set(self.clinical_result_states) != set(ClinicalResultState):
            raise ValueError("临床结果状态必须是固定封闭集合")
        if set(self.observation_kinds) != set(ObservationKind):
            raise ValueError("观察类型必须是固定封闭集合")
        if set(self.result_bearing_source_roles) != set(RESULT_BEARING_SOURCE_ROLES):
            raise ValueError("触发结果承载的来源角色必须是固定封闭集合")
        return self


class GateUnitSpec(BaseModel):
    """一个关键证据单元的封闭规格。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str
    report_kind: ReportKind
    blocking_level: GateBlockingLevel
    object_type: GateObjectType
    scope_parent: GateObjectType | None = None
    applicability_predicate_id: str
    required_context_fields: tuple[ContextField, ...] = Field(default=())
    allowed_source_roles: tuple[SourceRole, ...] = Field(min_length=1)
    allowed_fact_domains: tuple[FactDomain, ...] = Field(
        default=ALL_FACT_DOMAINS, min_length=1
    )
    allowed_observation_kinds: tuple[ObservationKind, ...] = Field(
        default=ALL_OBSERVATION_KINDS, min_length=1
    )
    minimum_disclosure_maturity: DisclosureMaturity
    accepted_fact_states: tuple[FactDisclosureState, ...] = Field(min_length=1)
    missing_strategy: MissingStrategy
    conflict_strategy: ConflictStrategy
    threshold: int = Field(default=1, ge=1)
    user_label_zh: str
    missing_impact_zh: str
    user_next_step_zh: str

    @field_validator(
        "unit_id",
        "applicability_predicate_id",
        "user_label_zh",
        "missing_impact_zh",
        "user_next_step_zh",
    )
    @classmethod
    def _unit_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "required_context_fields",
        "allowed_source_roles",
        "allowed_fact_domains",
        "allowed_observation_kinds",
    )
    @classmethod
    def _unit_lists_are_unique(cls, values: tuple[object, ...]) -> tuple[object, ...]:
        if len(set(values)) != len(values):
            raise ValueError("证据门槛单元清单不得重复")
        return values

    @model_validator(mode="after")
    def _unit_policy_is_consistent(self) -> GateUnitSpec:
        if self.object_type is self.scope_parent:
            raise ValueError("父子对象范围不得相同")
        if not set(self.accepted_fact_states) <= _SATISFYING_FACT_STATES:
            raise ValueError("关键证据不得接受缺失或未决冲突状态")
        if self.blocking_level is GateBlockingLevel.CRITICAL:
            if self.missing_strategy is not MissingStrategy.BLOCK:
                raise ValueError("关键单元缺失策略必须为阻断")
            if self.conflict_strategy is not ConflictStrategy.RESOLVED_ONLY:
                raise ValueError("关键单元只能接受已解决冲突")
        elif self.missing_strategy is not MissingStrategy.PRESERVE_DISCLOSURE_STATE:
            raise ValueError("扩展单元缺失策略必须保留披露状态")
        return self


class GateSpec(BaseModel):
    """版本化的报告证据规则说明书（对应 policy YAML）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    spec_id: str
    version: str
    report_kind: ReportKind
    vocabulary: GateVocabulary | None = None
    units: tuple[GateUnitSpec, ...] = Field(min_length=1)
    updated_at: datetime

    @field_validator("spec_id", "version")
    @classmethod
    def _spec_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("updated_at")
    @classmethod
    def _spec_time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _units_are_unique_and_scoped(self) -> GateSpec:
        unit_ids = tuple(unit.unit_id for unit in self.units)
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("证据门槛单元标识不得重复")
        if any(unit.report_kind is not self.report_kind for unit in self.units):
            raise ValueError("证据门槛单元报告类型必须与说明书一致")
        return self

    @property
    def spec_fingerprint(self) -> str:
        """由规范内容确定性生成的不可变规则指纹；覆盖重算必须校验父指纹。"""
        return compute_spec_fingerprint(self)

    @classmethod
    def from_yaml(cls, path: Path) -> GateSpec:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise ValueError("无法读取证据门槛说明书") from error
        if not isinstance(payload, dict):
            raise ValueError("证据门槛说明书顶层必须是对象")
        return cls.model_validate(cast(dict[str, object], payload))


_ALLOWED_PARENT_EDGES: frozenset[tuple[GateObjectType, GateObjectType]] = frozenset(
    {
        (GateObjectType.PRODUCT, GateObjectType.TRIAL),
        (GateObjectType.TRIAL, GateObjectType.COMPARISON),
        (GateObjectType.TRIAL, GateObjectType.GROUP),
        (GateObjectType.TRIAL, GateObjectType.ENDPOINT),
        (GateObjectType.COMPARISON, GateObjectType.GROUP),
        (GateObjectType.COMPARISON, GateObjectType.ENDPOINT),
        (GateObjectType.ENDPOINT, GateObjectType.GROUP),
        (GateObjectType.ENDPOINT, GateObjectType.TIMEPOINT),
    }
)

# 多对多关联边：同一组别可以同时参与多个比较与多个终点，同一终点也可以
# 由多个比较共同评估。关联边不构成唯一层级父关系，允许同一子对象的多个
# 同类关联边，也允许同秩对象相连（比较↔终点）。
_ASSOCIATION_EDGE_TYPES: frozenset[tuple[GateObjectType, GateObjectType]] = frozenset(
    {
        (GateObjectType.COMPARISON, GateObjectType.GROUP),
        (GateObjectType.COMPARISON, GateObjectType.ENDPOINT),
        (GateObjectType.ENDPOINT, GateObjectType.GROUP),
    }
)

# 对象层级秩：父秩必须严格小于子秩，保证关系图无环。
_OBJECT_RANK: dict[GateObjectType, int] = {
    GateObjectType.PRODUCT: 0,
    GateObjectType.TRIAL: 1,
    GateObjectType.COMPARISON: 2,
    GateObjectType.ENDPOINT: 2,
    GateObjectType.GROUP: 3,
    GateObjectType.TIMEPOINT: 3,
}


class EmptySetProof(BaseModel):
    """空对象集合的类型化证明：对象类、原因、不可变证据版本与中文说明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    object_type: GateObjectType
    reason_code: EmptySetReasonCode
    evidence_version_id: str
    explanation_zh: str

    @field_validator("evidence_version_id", "explanation_zh")
    @classmethod
    def _proof_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _proof_object_class_can_never_be_product(self) -> EmptySetProof:
        if self.object_type is GateObjectType.PRODUCT:
            raise ValueError("产品对象集合不可能为空，不得携带空集合证明")
        return self


class UniverseEdge(BaseModel):
    """类型化对象关系边：父对象 → 子对象，用于证明完整作用域路径。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    parent_type: GateObjectType
    parent_id: str
    child_type: GateObjectType
    child_id: str

    @field_validator("parent_id", "child_id")
    @classmethod
    def _edge_ids_are_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _edge_is_hierarchical_and_supported(self) -> UniverseEdge:
        pair = (self.parent_type, self.child_type)
        if pair not in _ALLOWED_PARENT_EDGES:
            raise ValueError("不支持的对象关系边类型")
        if (
            pair not in _ASSOCIATION_EDGE_TYPES
            and _OBJECT_RANK[self.parent_type] >= _OBJECT_RANK[self.child_type]
        ):
            raise ValueError("对象关系边必须严格从父级指向子级，不得成环")
        return self


class TrialDesignEvidence(BaseModel):
    """每项试验的设计证据：类型、不可变证据版本与中文说明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    design_kind: TrialDesignKind
    evidence_version_id: str
    explanation_zh: str

    @field_validator("trial_id", "evidence_version_id", "explanation_zh")
    @classmethod
    def _design_evidence_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class ApplicableUniverseSnapshot(BaseModel):
    """评估输入必须绑定的已闭合竞品宇宙和研究角色集合。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    evidence_snapshot_id: str
    research_role_set_id: str
    product_ids: tuple[str, ...] = Field(min_length=1)
    trial_ids: tuple[str, ...] = Field(default=())
    comparison_ids: tuple[str, ...] = Field(default=())
    group_ids: tuple[str, ...] = Field(default=())
    endpoint_ids: tuple[str, ...] = Field(default=())
    timepoint_ids: tuple[str, ...] = Field(default=())
    empty_set_proofs: tuple[EmptySetProof, ...] = Field(default=())
    relationship_edges: tuple[UniverseEdge, ...] = Field(default=())
    trial_design_evidence: tuple[TrialDesignEvidence, ...] = Field(default=())
    indication_rule_set_id: str
    applicable_conditional_predicates: tuple[str, ...] = Field(default=())
    universe_summary: str
    enumeration_complete: bool

    @field_validator(
        "project_id",
        "evidence_snapshot_id",
        "research_role_set_id",
        "indication_rule_set_id",
    )
    @classmethod
    def _snapshot_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("applicable_conditional_predicates")
    @classmethod
    def _conditional_predicates_are_unique_and_conditional(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("条件谓词标识不得重复")
        if "always_applicable" in normalized:
            raise ValueError("条件谓词集合不得包含无条件谓词")
        return normalized

    @model_validator(mode="after")
    def _summary_matches_content(self) -> ApplicableUniverseSnapshot:
        if self.universe_summary != compute_universe_summary(
            project_id=self.project_id,
            evidence_snapshot_id=self.evidence_snapshot_id,
            research_role_set_id=self.research_role_set_id,
            product_ids=self.product_ids,
            trial_ids=self.trial_ids,
            comparison_ids=self.comparison_ids,
            group_ids=self.group_ids,
            endpoint_ids=self.endpoint_ids,
            timepoint_ids=self.timepoint_ids,
            empty_set_proofs=self.empty_set_proofs,
            relationship_edges=self.relationship_edges,
            trial_design_evidence=self.trial_design_evidence,
            indication_rule_set_id=self.indication_rule_set_id,
            applicable_conditional_predicates=self.applicable_conditional_predicates,
        ):
            raise ValueError("适用对象集合摘要与内容不一致")
        if len({proof.object_type for proof in self.empty_set_proofs}) != len(
            self.empty_set_proofs
        ):
            raise ValueError("同一对象类型的空集合证明不得重复")
        return self

    @model_validator(mode="after")
    def _trial_design_evidence_covers_exactly_each_trial(
        self,
    ) -> ApplicableUniverseSnapshot:
        record_trials = tuple(
            record.trial_id for record in self.trial_design_evidence
        )
        if len(set(record_trials)) != len(record_trials):
            raise ValueError("每项试验只能有一条设计证据")
        if set(record_trials) != set(self.trial_ids):
            raise ValueError("每项试验必须有且仅有一条设计证据")
        return self


class GateEvidenceBinding(BaseModel):
    """规则单元到不可变事实版本的证据绑定；数值与披露状态严格分离。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    binding_id: str
    unit_id: str
    object_id: str
    fact_version_id: str
    trial_id: str | None = None
    comparison_id: str | None = None
    group_id: str | None = None
    endpoint_id: str | None = None
    timepoint_id: str | None = None
    fact_domain: FactDomain
    observation_kind: ObservationKind
    numeric_value: int | float | None = None
    unit: str | None = None
    denominator: int | None = Field(default=None, gt=0)
    definition: str | None = None
    direction: str | None = None
    timepoint: str | None = None
    analysis_population: str | None = None
    treatment_group: str | None = None
    control_group: str | None = None
    event_definition: str | None = None
    time_window: str | None = None
    source_location: str | None = None
    route_receipt_id: str | None = None
    review_state: FactReviewState
    disclosure_state: FactDisclosureState
    disclosure_maturity: DisclosureMaturity
    source_role: SourceRole
    conflict_disposition: ConflictDisposition
    applicability_predicate_id: str | None = None
    reported_zero_text: str | None = None

    @field_validator(
        "binding_id",
        "unit_id",
        "object_id",
        "fact_version_id",
    )
    @classmethod
    def _binding_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "unit",
        "definition",
        "direction",
        "timepoint",
        "analysis_population",
        "treatment_group",
        "control_group",
        "event_definition",
        "time_window",
        "source_location",
        "route_receipt_id",
        "applicability_predicate_id",
        "reported_zero_text",
    )
    @classmethod
    def _optional_binding_text_is_not_blank(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @field_validator("numeric_value")
    @classmethod
    def _numeric_value_is_finite(
        cls, value: int | float | None
    ) -> int | float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("证据数值必须是有限数值，不得为 NaN 或无穷")
        return value

    @model_validator(mode="after")
    def _binding_preserves_disclosure_contract(self) -> GateEvidenceBinding:
        if self.disclosure_state in _MISSING_STATES:
            if self.numeric_value is not None:
                raise ValueError("未报告或未公开状态不得携带数值，更不能转成数值零")
            if self.denominator is not None:
                raise ValueError("未报告或未公开状态不得携带分母")
        if self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            if self.numeric_value != 0:
                raise ValueError("已报告零值的规范数值必须为零")
            if self.reported_zero_text is None:
                raise ValueError("已报告零值必须有明确零值原文证据")
        elif self.reported_zero_text is not None:
            raise ValueError("非零值报告不得携带零值原文")
        if self.disclosure_state in _REPORTED_STATES and self.source_location is None:
            raise ValueError("已披露事实必须保存精确来源定位")
        if self.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
            if self.applicability_predicate_id is None:
                raise ValueError("不适用事实必须链接适用性依据")
            if self.numeric_value is not None or self.denominator is not None:
                raise ValueError("不适用事实不得携带数值或分母")
        if (
            self.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE
            and self.route_receipt_id is None
        ):
            raise ValueError("路线未解决事实必须链接路由回执")
        if self.disclosure_state is FactDisclosureState.CONFLICTING:
            if (
                self.conflict_disposition
                is not ConflictDisposition.OPEN_CONFLICT_PRESERVED
            ):
                raise ValueError("冲突状态必须保留开放冲突处置")
        else:
            if (
                self.conflict_disposition
                is not ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
            ):
                raise ValueError("非冲突事实必须选择已接受事实")
        return self


class GateUnitResult(BaseModel):
    """逐对象、逐单元的阈值输出；用户说明与内部状态分层。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str
    report_kind: ReportKind
    object_id: str
    applicable: bool
    outcome: GateUnitOutcome
    blocking: bool
    threshold: int = Field(ge=1)
    satisfied_count: int = Field(ge=0)
    fact_version_ids: tuple[str, ...] = Field(default=())
    source_locations: tuple[str, ...] = Field(default=())
    disclosure_state: FactDisclosureState | None = None
    failure_code: str | None = None
    user_note_zh: str | None = None

    @model_validator(mode="after")
    def _unit_result_is_internally_consistent(self) -> GateUnitResult:
        if len(set(self.fact_version_ids)) != len(self.fact_version_ids):
            raise ValueError("事实版本标识不得重复")
        if self.outcome is GateUnitOutcome.SATISFIED and not (
            self.applicable
            and not self.blocking
            and self.satisfied_count >= self.threshold
            and self.satisfied_count == len(self.fact_version_ids)
        ):
            raise ValueError(
                "满足结果必须适用、非阻断、达标数量达到阈值，"
                "且由相同数量的不同事实版本支撑"
            )
        if self.outcome is GateUnitOutcome.BLOCKED and not (
            self.applicable
            and self.blocking
            and self.satisfied_count < self.threshold
        ):
            raise ValueError("阻断结果必须适用、阻断且达标数量低于阈值")
        if self.outcome is GateUnitOutcome.NOT_APPLICABLE and not (
            not self.applicable
            and not self.blocking
            and self.satisfied_count == 0
            and not self.fact_version_ids
        ):
            raise ValueError("不适用结果必须不适用、非阻断、达标数量为零且不带事实版本")
        if self.outcome is GateUnitOutcome.EXTENSION_MISSING and not (
            self.applicable
            and not self.blocking
            and self.satisfied_count < self.threshold
        ):
            raise ValueError("扩展缺失结果必须适用、非阻断且达标数量低于阈值")
        if (
            self.outcome
            in (GateUnitOutcome.BLOCKED, GateUnitOutcome.EXTENSION_MISSING)
            and self.satisfied_count > len(self.fact_version_ids)
        ):
            raise ValueError("达标数量不得超过事实版本数")
        return self


class ReportGateResult(BaseModel):
    """报告级门槛结果：全部适用阻断单元的确定性合取。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    result_key: str
    report_kind: ReportKind
    evidence_snapshot_id: str
    spec_version: str
    contract_version: str
    universe_summary: str
    spec_fingerprint: str
    decision: ReportDecision
    unit_results: tuple[GateUnitResult, ...] = Field(min_length=1)
    applicable_unit_ids: tuple[str, ...] = Field(default=())
    blocked_unit_ids: tuple[str, ...] = Field(default=())
    user_summary_zh: str

    @model_validator(mode="after")
    def _result_is_deterministically_consistent(self) -> ReportGateResult:
        if any(
            result.report_kind is not self.report_kind
            for result in self.unit_results
        ):
            raise ValueError("单元结果报告类型与报告结果不一致")
        unit_object_pairs = tuple(
            (result.unit_id, result.object_id) for result in self.unit_results
        )
        if len(set(unit_object_pairs)) != len(unit_object_pairs):
            raise ValueError("同一对象同一单元结果不得重复")
        blocked = tuple(
            result
            for result in self.unit_results
            if result.outcome is GateUnitOutcome.BLOCKED
        )
        for result in blocked:
            if result.user_note_zh is None:
                raise ValueError("阻断单元必须携带中文用户说明")
        decision = ReportDecision.BLOCKED if blocked else ReportDecision.PASSED
        applicable_unit_ids = tuple(
            sorted(
                {result.unit_id for result in self.unit_results if result.applicable}
            )
        )
        blocked_unit_ids = tuple(sorted({result.unit_id for result in blocked}))
        if blocked:
            user_summary_zh = "报告因以下关键证据缺失而阻断：" + "；".join(
                cast(str, result.user_note_zh) for result in blocked
            )
        else:
            user_summary_zh = "全部适用关键证据单元已满足。"
        expected_key = compute_gate_result_key(
            self.report_kind,
            self.evidence_snapshot_id,
            self.spec_version,
            self.contract_version,
            self.universe_summary,
            spec_fingerprint=self.spec_fingerprint,
        )
        if self.decision is not decision:
            raise ValueError("报告决定与单元结果合取不一致")
        if self.applicable_unit_ids != applicable_unit_ids:
            raise ValueError("适用单元标识集合与单元结果不一致")
        if self.blocked_unit_ids != blocked_unit_ids:
            raise ValueError("阻断单元标识集合与单元结果不一致")
        if self.user_summary_zh != user_summary_zh:
            raise ValueError("用户说明与单元结果不一致")
        if self.result_key != expected_key:
            raise ValueError("结果键与标识字段不一致")
        return self

    @classmethod
    def from_unit_results(
        cls,
        *,
        report_kind: ReportKind,
        unit_results: Sequence[GateUnitResult],
        evidence_snapshot_id: str,
        spec_version: str,
        contract_version: str,
        universe_summary: str,
        spec_fingerprint: str,
    ) -> ReportGateResult:
        blocked = tuple(
            result
            for result in unit_results
            if result.outcome is GateUnitOutcome.BLOCKED
        )
        for result in blocked:
            if result.user_note_zh is None:
                raise GateEvaluationError("阻断单元必须携带中文用户说明")
        decision = ReportDecision.BLOCKED if blocked else ReportDecision.PASSED
        applicable_unit_ids = tuple(
            sorted({result.unit_id for result in unit_results if result.applicable})
        )
        blocked_unit_ids = tuple(sorted({result.unit_id for result in blocked}))
        if blocked:
            user_summary_zh = "报告因以下关键证据缺失而阻断：" + "；".join(
                cast(str, result.user_note_zh) for result in blocked
            )
        else:
            user_summary_zh = "全部适用关键证据单元已满足。"
        result_key = compute_gate_result_key(
            report_kind,
            evidence_snapshot_id,
            spec_version,
            contract_version,
            universe_summary,
            spec_fingerprint=spec_fingerprint,
        )
        return cls(
            result_key=result_key,
            report_kind=report_kind,
            evidence_snapshot_id=evidence_snapshot_id,
            spec_version=spec_version,
            contract_version=contract_version,
            universe_summary=universe_summary,
            spec_fingerprint=spec_fingerprint,
            decision=decision,
            unit_results=tuple(unit_results),
            applicable_unit_ids=applicable_unit_ids,
            blocked_unit_ids=blocked_unit_ids,
            user_summary_zh=user_summary_zh,
        )


class GateOverride(BaseModel):
    """项目合同覆盖版本：只追加新版本，父结果不可变。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    override_id: str
    base_spec_version: str
    parent_contract_version: str
    child_contract_version: str
    change_summary_zh: str
    changed_unit_ids: tuple[str, ...] = Field(min_length=1)
    affected_report_kinds: tuple[ReportKind, ...] = Field(min_length=1)
    created_at: datetime

    @field_validator(
        "override_id",
        "base_spec_version",
        "parent_contract_version",
        "child_contract_version",
        "change_summary_zh",
    )
    @classmethod
    def _override_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("changed_unit_ids")
    @classmethod
    def _changed_units_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(values)) != len(values):
            raise ValueError("覆盖依赖单元不得重复")
        return values

    @field_validator("affected_report_kinds")
    @classmethod
    def _affected_reports_are_unique(
        cls, values: tuple[ReportKind, ...]
    ) -> tuple[ReportKind, ...]:
        if len(set(values)) != len(values):
            raise ValueError("受影响报告类型不得重复")
        return values

    @field_validator("created_at")
    @classmethod
    def _override_time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _override_versions_are_distinct(self) -> GateOverride:
        if self.child_contract_version == self.parent_contract_version:
            raise ValueError("覆盖必须产生新的项目合同版本")
        return self


def compute_spec_fingerprint(spec: GateSpec) -> str:
    """由 GateSpec 规范内容确定性生成不可变指纹；内容相同则指纹相同。"""
    canonical = json.dumps(
        spec.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return stable_id("gate-spec", canonical)


def compute_universe_summary(
    *,
    project_id: str,
    evidence_snapshot_id: str,
    research_role_set_id: str,
    product_ids: Sequence[str],
    trial_ids: Sequence[str] = (),
    comparison_ids: Sequence[str] = (),
    group_ids: Sequence[str] = (),
    endpoint_ids: Sequence[str] = (),
    timepoint_ids: Sequence[str] = (),
    empty_set_proofs: Sequence[EmptySetProof] = (),
    relationship_edges: Sequence[UniverseEdge] = (),
    trial_design_evidence: Sequence[TrialDesignEvidence] = (),
    indication_rule_set_id: str,
    applicable_conditional_predicates: Sequence[str] = (),
) -> str:
    """由对象集合、研究角色集、类型化空集合证明、关系图、设计证据与指示规则生成摘要。

    空集合证明、关系边与每试验设计证据的内容均参与摘要；研究角色集版本变化
    同样改变摘要。调用方不能伪造或省略证明/关系/设计证据来改变摘要。
    """
    proof_parts = tuple(
        sorted(
            f"proof:{proof.object_type.value}:{proof.reason_code.value}:"
            f"{proof.evidence_version_id}"
            for proof in empty_set_proofs
        )
    )
    edge_parts = tuple(
        sorted(
            f"edge:{edge.parent_type.value}:{edge.parent_id}:"
            f"{edge.child_type.value}:{edge.child_id}"
            for edge in relationship_edges
        )
    )
    design_parts = tuple(
        sorted(
            f"design:{record.trial_id}:{record.design_kind.value}:"
            f"{record.evidence_version_id}"
            for record in trial_design_evidence
        )
    )
    return stable_id(
        "universe-summary",
        project_id,
        evidence_snapshot_id,
        research_role_set_id,
        indication_rule_set_id,
        *tuple(sorted(applicable_conditional_predicates)),
        *tuple(sorted(product_ids)),
        *tuple(sorted(trial_ids)),
        *tuple(sorted(comparison_ids)),
        *tuple(sorted(group_ids)),
        *tuple(sorted(endpoint_ids)),
        *tuple(sorted(timepoint_ids)),
        *design_parts,
        *proof_parts,
        *edge_parts,
    )


def compute_gate_result_key(
    report_kind: ReportKind,
    evidence_snapshot_id: str,
    spec_version: str,
    contract_version: str,
    universe_summary: str,
    *,
    spec_fingerprint: str,
) -> str:
    """结果不可变键：报告类型、证据快照、规则指纹、合同版本与集合摘要。"""
    return stable_id(
        "gate-result",
        report_kind.value,
        evidence_snapshot_id,
        spec_version,
        contract_version,
        universe_summary,
        spec_fingerprint,
    )


def compute_unit_results_digest(
    unit_results: Sequence[GateUnitResult],
) -> str:
    """按顺序规范化全部单元结果并生成内容摘要；顺序参与摘要。"""
    canonical = json.dumps(
        [result.model_dump(mode="json") for result in unit_results],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return stable_id("unit-results", canonical)


def compute_batch_key(
    *,
    report_kind: ReportKind,
    evidence_snapshot_id: str,
    universe_summary: str,
    spec_fingerprint: str,
    unit_results_digest: str,
) -> str:
    """评估批不可变键：报告类型、宇宙身份、规则指纹与全部单元结果摘要。"""
    return stable_id(
        "gate-batch",
        report_kind.value,
        evidence_snapshot_id,
        universe_summary,
        spec_fingerprint,
        unit_results_digest,
    )


class _GateEvaluationBatch(BaseModel):
    """不可变评估批（内部机器）：绑定报告类型、宇宙身份、规则指纹与全部有序单元结果。

    批键由上述身份与全部单元结果的规范化内容摘要确定性生成；
    任何结果对象或顺序变化都改变批键。聚合入口必须显式重验内容与键，
    不能依赖对象曾通过 Pydantic 构造（model_copy 会绕过构造期校验）。
    正常构造只通过 from_evaluation：身份只取自规范 GateSpec 与已验证宇宙快照。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    batch_key: str
    report_kind: ReportKind
    evidence_snapshot_id: str
    universe_summary: str
    spec_fingerprint: str
    unit_results: tuple[GateUnitResult, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _batch_is_consistent(self) -> _GateEvaluationBatch:
        if any(
            result.report_kind is not self.report_kind
            for result in self.unit_results
        ):
            raise ValueError("单元结果报告类型与评估批不一致")
        pairs = tuple(
            (result.unit_id, result.object_id) for result in self.unit_results
        )
        if len(set(pairs)) != len(pairs):
            raise ValueError("同一对象同一单元结果不得重复")
        digest = compute_unit_results_digest(self.unit_results)
        expected = compute_batch_key(
            report_kind=self.report_kind,
            evidence_snapshot_id=self.evidence_snapshot_id,
            universe_summary=self.universe_summary,
            spec_fingerprint=self.spec_fingerprint,
            unit_results_digest=digest,
        )
        if self.batch_key != expected:
            raise ValueError("评估批键与内容不一致")
        return self

    @classmethod
    def from_evaluation(
        cls,
        *,
        spec: GateSpec,
        snapshot: ApplicableUniverseSnapshot,
        unit_results: Sequence[GateUnitResult],
    ) -> _GateEvaluationBatch:
        """内部构造入口：身份只取自规范 GateSpec 与已验证宇宙快照。

        不接受调用方提供的快照/规格身份字符串；报告类型、规则指纹、
        证据快照与宇宙摘要全部由对象派生，快照先经闭合校验。
        本构造器为内部机器，不导出到包根；公共原子路径是评估器的 evaluate_report。
        """
        assert_applicable_universe_closed(snapshot)
        return cls(
            batch_key=compute_batch_key(
                report_kind=spec.report_kind,
                evidence_snapshot_id=snapshot.evidence_snapshot_id,
                universe_summary=snapshot.universe_summary,
                spec_fingerprint=spec.spec_fingerprint,
                unit_results_digest=compute_unit_results_digest(unit_results),
            ),
            report_kind=spec.report_kind,
            evidence_snapshot_id=snapshot.evidence_snapshot_id,
            universe_summary=snapshot.universe_summary,
            spec_fingerprint=spec.spec_fingerprint,
            unit_results=tuple(unit_results),
        )


def _assert_batch_integrity(batch: _GateEvaluationBatch) -> None:
    """聚合前显式重验评估批：键必须等于当前规范化内容的派生键。

    不依赖对象曾通过 Pydantic 构造：model_copy 会绕过构造期校验，
    因此必须从当前序列化内容重新派生摘要与键，任何篡改都会改变键。
    """
    digest = compute_unit_results_digest(batch.unit_results)
    expected = compute_batch_key(
        report_kind=batch.report_kind,
        evidence_snapshot_id=batch.evidence_snapshot_id,
        universe_summary=batch.universe_summary,
        spec_fingerprint=batch.spec_fingerprint,
        unit_results_digest=digest,
    )
    if batch.batch_key != expected:
        raise GateEvaluationError("评估批键与内容不一致，必须失败关闭")


def assert_applicable_universe_closed(snapshot: ApplicableUniverseSnapshot) -> None:
    """未知、重复、漏评或未证明为空的对象集合与关系图均失败关闭。

    每种空对象类必须恰好有一个对应类型化证明；非空对象类不得携带证明。
    每个非产品对象必须具有规定父边；未知、重复、跨类型重叠或成环的边失败关闭。
    """
    if not snapshot.enumeration_complete:
        raise GateEvaluationError("适用对象集合未完成穷举，必须失败关闭")
    collections: tuple[tuple[GateObjectType, tuple[str, ...]], ...] = (
        (GateObjectType.PRODUCT, snapshot.product_ids),
        (GateObjectType.TRIAL, snapshot.trial_ids),
        (GateObjectType.COMPARISON, snapshot.comparison_ids),
        (GateObjectType.GROUP, snapshot.group_ids),
        (GateObjectType.ENDPOINT, snapshot.endpoint_ids),
        (GateObjectType.TIMEPOINT, snapshot.timepoint_ids),
    )
    proofs_by_type: dict[GateObjectType, EmptySetProof] = {}
    for proof in snapshot.empty_set_proofs:
        if proof.object_type in proofs_by_type:
            raise GateEvaluationError("同一对象类型的空集合证明不得重复，必须失败关闭")
        proofs_by_type[proof.object_type] = proof
    if GateObjectType.PRODUCT in proofs_by_type:
        raise GateEvaluationError("产品对象集合不可能为空，不得携带空集合证明")
    seen_ids: dict[str, GateObjectType] = {}
    for object_type, ids in collections:
        if len(set(ids)) != len(ids):
            raise GateEvaluationError(f"{object_type.value} 包含重复对象，必须失败关闭")
        if not ids:
            if object_type not in proofs_by_type:
                raise GateEvaluationError(
                    f"{object_type.value} 为空且没有对应类型化空集合证明，必须失败关闭"
                )
        elif object_type in proofs_by_type:
            raise GateEvaluationError(
                f"{object_type.value} 非空但携带空集合证明，必须失败关闭"
            )
        for object_id in ids:
            existing = seen_ids.get(object_id)
            if existing is not None and existing is not object_type:
                raise GateEvaluationError(
                    "对象标识跨对象类型重复，必须失败关闭"
                )
            seen_ids[object_id] = object_type
    _assert_relationship_graph_closed(snapshot, seen_ids, collections)
    _assert_trial_design_closed(snapshot)
    if snapshot.universe_summary != compute_universe_summary(
        project_id=snapshot.project_id,
        evidence_snapshot_id=snapshot.evidence_snapshot_id,
        research_role_set_id=snapshot.research_role_set_id,
        product_ids=snapshot.product_ids,
        trial_ids=snapshot.trial_ids,
        comparison_ids=snapshot.comparison_ids,
        group_ids=snapshot.group_ids,
        endpoint_ids=snapshot.endpoint_ids,
        timepoint_ids=snapshot.timepoint_ids,
        empty_set_proofs=snapshot.empty_set_proofs,
        relationship_edges=snapshot.relationship_edges,
        trial_design_evidence=snapshot.trial_design_evidence,
        indication_rule_set_id=snapshot.indication_rule_set_id,
        applicable_conditional_predicates=snapshot.applicable_conditional_predicates,
    ):
        raise GateEvaluationError("适用对象集合摘要与内容不一致，必须失败关闭")


def _assert_trial_design_closed(snapshot: ApplicableUniverseSnapshot) -> None:
    """每试验设计类型与关系图一致，且每个比较关联至少两个同试验组别。

    比较设计必须有至少一条 trial→comparison 边；单臂设计不得有比较边。
    每个比较必须关联至少两个不同组别，且全部组别位于比较所属试验内。
    """
    design_by_trial = {
        record.trial_id: record for record in snapshot.trial_design_evidence
    }
    comparison_edges_by_trial: dict[str, int] = {}
    comparison_trial: dict[str, str] = {}
    group_trial: dict[str, str] = {}
    comparison_group_count: dict[str, set[str]] = {}
    for edge in snapshot.relationship_edges:
        if edge.parent_type is GateObjectType.TRIAL:
            if edge.child_type is GateObjectType.COMPARISON:
                comparison_edges_by_trial[edge.parent_id] = (
                    comparison_edges_by_trial.get(edge.parent_id, 0) + 1
                )
                comparison_trial[edge.child_id] = edge.parent_id
            elif edge.child_type is GateObjectType.GROUP:
                group_trial[edge.child_id] = edge.parent_id
        elif (
            edge.parent_type is GateObjectType.COMPARISON
            and edge.child_type is GateObjectType.GROUP
        ):
            comparison_group_count.setdefault(edge.parent_id, set()).add(
                edge.child_id
            )
    for trial_id, record in design_by_trial.items():
        comparison_count = comparison_edges_by_trial.get(trial_id, 0)
        if record.design_kind is TrialDesignKind.COMPARATIVE:
            if comparison_count < 1:
                raise GateEvaluationError(
                    f"比较设计试验缺少 trial→comparison 边：{trial_id}"
                )
        elif comparison_count > 0:
            raise GateEvaluationError(
                f"单臂设计试验不得存在比较边：{trial_id}"
            )
    # 遍历全部比较对象，而不是只遍历实际收到比较→组别关联边的比较：
    # 零关联边的比较同样必须失败关闭。
    for comparison_id in snapshot.comparison_ids:
        group_ids: set[str] = comparison_group_count.get(comparison_id, set())
        if len(group_ids) < 2:
            raise GateEvaluationError(
                f"比较必须关联至少两个不同组别：{comparison_id}"
            )
        parent_trial = comparison_trial.get(comparison_id)
        if parent_trial is None:
            raise GateEvaluationError(f"比较缺少所属试验：{comparison_id}")
        for group_id in group_ids:
            if group_trial.get(group_id) != parent_trial:
                raise GateEvaluationError(
                    f"比较的组别必须全部位于同一试验内：{comparison_id}/{group_id}"
                )


def _assert_relationship_graph_closed(
    snapshot: ApplicableUniverseSnapshot,
    seen_ids: dict[str, GateObjectType],
    collections: tuple[tuple[GateObjectType, tuple[str, ...]], ...],
) -> None:
    """校验关系图：未知/重复边与歧义层级父边失败关闭，非产品对象必有规定父边。

    层级父关系（product→trial、trial→comparison/group/endpoint、endpoint→timepoint）
    是唯一关系，同一子对象每类只允许一个父边；比较→组别与终点→组别是多对多
    关联边，允许同一组别的多个同类关联边，但完全相同的边仍不得重复。
    """
    parents: dict[tuple[GateObjectType, str], dict[GateObjectType, str]] = {}
    seen_edges: set[tuple[GateObjectType, str, GateObjectType, str]] = set()
    for edge in snapshot.relationship_edges:
        edge_key = (
            edge.parent_type,
            edge.parent_id,
            edge.child_type,
            edge.child_id,
        )
        if edge_key in seen_edges:
            raise GateEvaluationError("对象关系边重复，必须失败关闭")
        seen_edges.add(edge_key)
        for object_type, object_id in (
            (edge.parent_type, edge.parent_id),
            (edge.child_type, edge.child_id),
        ):
            if seen_ids.get(object_id) is not object_type:
                raise GateEvaluationError(
                    f"对象关系边引用未知对象：{object_type.value}/{object_id}"
                )
        if (edge.parent_type, edge.child_type) in _ASSOCIATION_EDGE_TYPES:
            continue
        child_key = (edge.child_type, edge.child_id)
        parent_slots = parents.setdefault(child_key, {})
        if edge.parent_type in parent_slots:
            raise GateEvaluationError(
                "同一子对象不允许存在多个同类父边，必须失败关闭"
            )
        parent_slots[edge.parent_type] = edge.parent_id
    required_parent: dict[GateObjectType, GateObjectType] = {
        GateObjectType.TRIAL: GateObjectType.PRODUCT,
        GateObjectType.COMPARISON: GateObjectType.TRIAL,
        GateObjectType.GROUP: GateObjectType.TRIAL,
        GateObjectType.ENDPOINT: GateObjectType.TRIAL,
        GateObjectType.TIMEPOINT: GateObjectType.ENDPOINT,
    }
    for object_type, ids in collections:
        needed = required_parent.get(object_type)
        if needed is None:
            continue
        for object_id in ids:
            if parents.get((object_type, object_id), {}).get(needed) is None:
                raise GateEvaluationError(
                    f"{object_type.value} 对象缺少必需父边：{object_id}"
                )


def assert_bindings_in_universe(
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> None:
    """证据绑定引用的对象必须属于已闭合宇宙且处于同一条作用域路径。

    未知对象失败关闭；试验/比较/组别/终点/时间点各自已知但不在同一条
    父子路径上的作用域元组（如跨试验拼接）失败关闭。
    组别基线与安全绑定只需 trial→group 层级边匹配；比较/终点是可选的
    多对多关联作用域，显式携带时必须精确匹配图中关联边，省略时不予要求。
    """
    known_ids: dict[str, GateObjectType] = {}
    for object_type, ids in (
        (GateObjectType.PRODUCT, snapshot.product_ids),
        (GateObjectType.TRIAL, snapshot.trial_ids),
        (GateObjectType.COMPARISON, snapshot.comparison_ids),
        (GateObjectType.GROUP, snapshot.group_ids),
        (GateObjectType.ENDPOINT, snapshot.endpoint_ids),
        (GateObjectType.TIMEPOINT, snapshot.timepoint_ids),
    ):
        for object_id in ids:
            existing = known_ids.get(object_id)
            if existing is not None and existing is not object_type:
                raise GateEvaluationError(
                    "对象标识跨对象类型重复，无法判定证据作用域，必须失败关闭"
                )
            known_ids[object_id] = object_type
    trial_product: dict[str, str] = {}
    comparison_trial: dict[str, str] = {}
    group_trial: dict[str, str] = {}
    group_comparison: dict[str, set[str]] = {
        group_id: set() for group_id in snapshot.group_ids
    }
    group_endpoint: dict[str, set[str]] = {
        group_id: set() for group_id in snapshot.group_ids
    }
    comparison_endpoint: dict[str, set[str]] = {
        comparison_id: set() for comparison_id in snapshot.comparison_ids
    }
    endpoint_trial: dict[str, str] = {}
    timepoint_endpoint: dict[str, str] = {}
    for edge in snapshot.relationship_edges:
        if edge.parent_type is GateObjectType.PRODUCT:
            trial_product[edge.child_id] = edge.parent_id
        elif edge.parent_type is GateObjectType.TRIAL:
            if edge.child_type is GateObjectType.COMPARISON:
                comparison_trial[edge.child_id] = edge.parent_id
            elif edge.child_type is GateObjectType.GROUP:
                group_trial[edge.child_id] = edge.parent_id
            else:
                endpoint_trial[edge.child_id] = edge.parent_id
        elif edge.parent_type is GateObjectType.COMPARISON:
            if edge.child_type is GateObjectType.GROUP:
                group_comparison[edge.child_id].add(edge.parent_id)
            else:
                comparison_endpoint[edge.parent_id].add(edge.child_id)
        elif edge.child_type is GateObjectType.GROUP:
            group_endpoint[edge.child_id].add(edge.parent_id)
        else:
            timepoint_endpoint[edge.child_id] = edge.parent_id
    for binding in bindings:
        object_kind = known_ids.get(binding.object_id)
        if object_kind is None:
            raise GateEvaluationError(f"证据绑定引用未知对象：{binding.object_id}")
        for attribute, _collection in _SCOPE_ATTRIBUTE_IDS:
            value = getattr(binding, attribute)
            if value is not None and value not in known_ids:
                raise GateEvaluationError(
                    f"证据绑定引用未知作用域对象：{attribute}={value}"
                )
        if binding.comparison_id is not None and (
            binding.trial_id is None
            or comparison_trial.get(binding.comparison_id) != binding.trial_id
        ):
            raise GateEvaluationError("比较作用域缺少或错误匹配其所属试验")
        if binding.group_id is not None:
            if (
                binding.trial_id is None
                or group_trial.get(binding.group_id) != binding.trial_id
            ):
                raise GateEvaluationError("组别作用域缺少或错误匹配其所属试验")
            if binding.comparison_id is not None and (
                binding.comparison_id
                not in group_comparison.get(binding.group_id, set())
            ):
                raise GateEvaluationError("组别作用域与其所属比较不一致")
            if binding.endpoint_id is not None and (
                binding.endpoint_id not in group_endpoint.get(binding.group_id, set())
            ):
                raise GateEvaluationError("组别作用域与其所属终点不一致")
        if binding.endpoint_id is not None and (
            binding.trial_id is None
            or endpoint_trial.get(binding.endpoint_id) != binding.trial_id
        ):
            raise GateEvaluationError("终点作用域缺少或错误匹配其所属试验")
        if binding.timepoint_id is not None and (
            binding.endpoint_id is None
            or timepoint_endpoint.get(binding.timepoint_id) != binding.endpoint_id
        ):
            raise GateEvaluationError("时间点作用域缺少或错误匹配其所属终点")
        if (
            binding.comparison_id is not None
            and binding.endpoint_id is not None
            and binding.endpoint_id
            not in comparison_endpoint.get(binding.comparison_id, set())
        ):
            raise GateEvaluationError(
                "比较与终点缺少显式关联边，必须失败关闭"
            )
        if (
            object_kind is GateObjectType.PRODUCT
            and binding.trial_id is not None
            and trial_product.get(binding.trial_id) != binding.object_id
        ):
            raise GateEvaluationError(
                "产品作用域证据引用其他产品的试验，必须失败关闭"
            )
        if object_kind is GateObjectType.TRIAL and binding.trial_id not in (
            None,
            binding.object_id,
        ):
            raise GateEvaluationError("试验对象的证据作用域与评估对象不一致")
        if object_kind is GateObjectType.COMPARISON and binding.comparison_id not in (
            None,
            binding.object_id,
        ):
            raise GateEvaluationError("比较对象的证据作用域与评估对象不一致")
        if object_kind is GateObjectType.GROUP and binding.group_id not in (
            None,
            binding.object_id,
        ):
            raise GateEvaluationError("组别对象的证据作用域与评估对象不一致")
        if object_kind is GateObjectType.ENDPOINT and binding.endpoint_id not in (
            None,
            binding.object_id,
        ):
            raise GateEvaluationError("终点对象的证据作用域与评估对象不一致")
        if object_kind is GateObjectType.TIMEPOINT and binding.timepoint_id not in (
            None,
            binding.object_id,
        ):
            raise GateEvaluationError("时间点对象的证据作用域与评估对象不一致")


def _context_field_value(
    binding: GateEvidenceBinding, field: ContextField
) -> object:
    return cast(object, getattr(binding, _CONTEXT_FIELD_ATTRS[field]))


def _best_disclosure_state(
    bindings: Sequence[GateEvidenceBinding],
) -> FactDisclosureState | None:
    best_rank = len(_PREFERRED_DISCLOSURE_ORDER)
    best: FactDisclosureState | None = None
    for binding in bindings:
        rank = _PREFERRED_DISCLOSURE_ORDER.index(binding.disclosure_state)
        if rank < best_rank:
            best_rank = rank
            best = binding.disclosure_state
    return best


def evidence_binding_qualifies(
    binding: GateEvidenceBinding,
    unit: GateUnitSpec,
    *,
    snapshot: ApplicableUniverseSnapshot | None = None,
) -> bool:
    """确定性逐字段判定：来源、成熟度、事实状态、冲突与上下文齐备才算满足。

    不适用绑定只在下列条件同时成立时才可满足单元：
    - 单元本身不是无条件适用（always_applicable）；
    - 绑定谓词与单元谓词完全一致；
    - 谓词由版本化指示规则合同在评估时承认（存在于适用条件谓词集合）。
    """
    if binding.review_state is not FactReviewState.ACCEPTED:
        return False
    if binding.fact_domain not in unit.allowed_fact_domains:
        return False
    if binding.observation_kind not in unit.allowed_observation_kinds:
        return False
    if binding.disclosure_state not in unit.accepted_fact_states:
        return False
    if binding.source_role not in unit.allowed_source_roles:
        return False
    if (
        disclosure_maturity_rank(binding.disclosure_maturity)
        < disclosure_maturity_rank(unit.minimum_disclosure_maturity)
    ):
        return False
    if (
        unit.conflict_strategy is ConflictStrategy.RESOLVED_ONLY
        and binding.conflict_disposition
        is not ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
    ):
        return False
    if binding.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
        if unit.applicability_predicate_id == "always_applicable":
            return False
        if binding.applicability_predicate_id != unit.applicability_predicate_id:
            return False
        if (
            snapshot is None
            or binding.applicability_predicate_id
            not in snapshot.applicable_conditional_predicates
        ):
            return False
    for field in unit.required_context_fields:
        if _context_field_value(binding, field) is None:
            return False
    return True


def evaluate_unit_decision(
    unit: GateUnitSpec,
    *,
    object_id: str,
    applicable: bool,
    applicability_justified: bool,
    bindings: Sequence[GateEvidenceBinding],
    snapshot: ApplicableUniverseSnapshot | None = None,
) -> GateUnitResult:
    """对单个对象的单个单元做确定性决定；适用性未确定时失败关闭。"""
    if not applicable and unit.applicability_predicate_id == "always_applicable":
        raise GateEvaluationError("无条件适用单元不得被判定为不适用，必须失败关闭")
    if not applicable:
        if not applicability_justified:
            raise GateEvaluationError("适用性未确定时必须失败关闭")
        return GateUnitResult(
            unit_id=unit.unit_id,
            report_kind=unit.report_kind,
            object_id=object_id,
            applicable=False,
            outcome=GateUnitOutcome.NOT_APPLICABLE,
            blocking=False,
            threshold=unit.threshold,
            satisfied_count=0,
        )
    scope_bindings = tuple(
        binding
        for binding in bindings
        if binding.object_id == object_id and binding.unit_id == unit.unit_id
    )
    qualifying = tuple(
        binding
        for binding in scope_bindings
        if evidence_binding_qualifies(binding, unit, snapshot=snapshot)
    )
    # 阈值按不同不可变事实版本计数：同一事实版本的重复绑定只计一次。
    distinct_fact_version_ids = frozenset(
        binding.fact_version_id for binding in qualifying
    )
    satisfied_count = len(distinct_fact_version_ids)
    if satisfied_count >= unit.threshold:
        outcome = GateUnitOutcome.SATISFIED
        blocking = False
        failure_code = None
        user_note_zh = None
    elif unit.blocking_level is GateBlockingLevel.CRITICAL:
        outcome = GateUnitOutcome.BLOCKED
        blocking = True
        failure_code = "missing_required_evidence"
        user_note_zh = (
            f"{unit.user_label_zh}缺失：{unit.missing_impact_zh}。"
            f"{unit.user_next_step_zh}"
        )
    else:
        outcome = GateUnitOutcome.EXTENSION_MISSING
        blocking = False
        failure_code = "missing_extension_evidence"
        user_note_zh = None
    return GateUnitResult(
        unit_id=unit.unit_id,
        report_kind=unit.report_kind,
        object_id=object_id,
        applicable=True,
        outcome=outcome,
        blocking=blocking,
        threshold=unit.threshold,
        satisfied_count=satisfied_count,
        fact_version_ids=tuple(sorted(distinct_fact_version_ids)),
        source_locations=tuple(
            sorted(
                binding.source_location
                for binding in qualifying
                if binding.source_location is not None
            )
        ),
        disclosure_state=(
            None
            if outcome is GateUnitOutcome.NOT_APPLICABLE
            else _best_disclosure_state(scope_bindings)
        ),
        failure_code=failure_code,
        user_note_zh=user_note_zh,
    )


def derive_expected_unit_object_pairs(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
) -> tuple[tuple[str, str], ...]:
    """由规范 GateSpec 与已闭合宇宙独立推导完整 (unit_id, object_id) 期望矩阵。

    与评估共用同一对象/空类锚点/按试验比较判定契约：
    - 比较级单元：每个试验的真实比较对象，单臂试验给出试验锚点，无试验时给出产品锚点；
    - 其余对象类：逐真实对象；对象类为空时给出声明父对象（必要时产品集合）锚点。
    顺序确定：按规格单元顺序，对象按快照集合顺序，试验内比较按标识排序。
    """
    trial_comparisons: dict[str, list[str]] = {
        trial_id: [] for trial_id in snapshot.trial_ids
    }
    for edge in snapshot.relationship_edges:
        if (
            edge.parent_type is GateObjectType.TRIAL
            and edge.child_type is GateObjectType.COMPARISON
        ):
            trial_comparisons.setdefault(edge.parent_id, []).append(edge.child_id)
    object_mapping: dict[GateObjectType, tuple[str, ...]] = {
        GateObjectType.PRODUCT: snapshot.product_ids,
        GateObjectType.TRIAL: snapshot.trial_ids,
        GateObjectType.COMPARISON: snapshot.comparison_ids,
        GateObjectType.GROUP: snapshot.group_ids,
        GateObjectType.ENDPOINT: snapshot.endpoint_ids,
        GateObjectType.TIMEPOINT: snapshot.timepoint_ids,
    }
    pairs: list[tuple[str, str]] = []
    for unit in spec.units:
        if unit.object_type is GateObjectType.COMPARISON:
            if not snapshot.trial_ids:
                pairs.extend(
                    (unit.unit_id, product_id)
                    for product_id in snapshot.product_ids
                )
                continue
            for trial_id in snapshot.trial_ids:
                comparisons = tuple(sorted(trial_comparisons.get(trial_id, ())))
                if comparisons:
                    pairs.extend(
                        (unit.unit_id, comparison_id)
                        for comparison_id in comparisons
                    )
                else:
                    pairs.append((unit.unit_id, trial_id))
            continue
        objects = object_mapping.get(unit.object_type, ())
        if objects:
            pairs.extend((unit.unit_id, object_id) for object_id in objects)
            continue
        if unit.scope_parent is None:
            anchors = snapshot.product_ids
        else:
            anchors = (
                object_mapping.get(unit.scope_parent, ()) or snapshot.product_ids
            )
        pairs.extend((unit.unit_id, anchor_id) for anchor_id in anchors)
    return tuple(pairs)


def _aggregate_report_gates(
    *,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    batch: _GateEvaluationBatch,
    contract_version: str,
) -> ReportGateResult:
    """报告结果是全部适用阻断单元的确定性合取；绑定规范指纹、宇宙与完整矩阵。

    内部聚合机器（不导出到包根）：接受规范 GateSpec、已闭合宇宙快照与内部评估批。
    入口先显式重验批内容与键（model_copy 会绕过 Pydantic 构造期校验），
    再校验批的报告类型、证据快照、宇宙摘要与规则指纹必须与 spec+snapshot 一致；
    随后独立推导完整 (unit_id, object_id) 期望矩阵，任何缺失或多余结果对失败关闭。
    结果标识取自已验证快照与规范规格。保留全部 P0 语义检查。
    公共原子路径是评估器的 evaluate_report；本函数不接收脱离的 unit_results。
    """
    assert_applicable_universe_closed(snapshot)
    _assert_batch_integrity(batch)
    if batch.report_kind is not spec.report_kind:
        raise GateEvaluationError("评估批报告类型与规格不一致，必须失败关闭")
    if batch.evidence_snapshot_id != snapshot.evidence_snapshot_id:
        raise GateEvaluationError(
            "评估批证据快照与宇宙快照不一致，必须失败关闭"
        )
    if batch.universe_summary != snapshot.universe_summary:
        raise GateEvaluationError("评估批宇宙摘要与宇宙快照不一致，必须失败关闭")
    if batch.spec_fingerprint != spec.spec_fingerprint:
        raise GateEvaluationError("评估批规则指纹与规格不一致，必须失败关闭")
    unit_results = batch.unit_results
    spec_units = {unit.unit_id: unit for unit in spec.units}
    actual_pairs = tuple(
        (result.unit_id, result.object_id) for result in unit_results
    )
    if len(actual_pairs) != len(set(actual_pairs)):
        raise GateEvaluationError("同一对象同一单元结果重复，必须失败关闭")
    for result in unit_results:
        if result.report_kind is not spec.report_kind:
            raise GateEvaluationError(
                f"单元结果报告类型与规格不一致：{result.unit_id}"
            )
        unit_spec = spec_units.get(result.unit_id)
        if unit_spec is None:
            raise GateEvaluationError(f"单元结果不属于当前规格：{result.unit_id}")
        if (
            result.outcome is GateUnitOutcome.NOT_APPLICABLE
            and unit_spec.applicability_predicate_id == "always_applicable"
        ):
            raise GateEvaluationError(
                f"无条件适用单元不得产生不适用结果：{result.unit_id}"
            )
        if (
            result.outcome is GateUnitOutcome.EXTENSION_MISSING
            and unit_spec.blocking_level is GateBlockingLevel.CRITICAL
        ):
            raise GateEvaluationError(
                f"关键单元不得产生扩展缺失结果：{result.unit_id}"
            )
    expected_pairs = derive_expected_unit_object_pairs(spec, snapshot)
    expected_set = frozenset(expected_pairs)
    actual_set = frozenset(actual_pairs)
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    if missing or extra:
        raise GateEvaluationError(
            "单元结果集合与规格+宇宙推导的完整矩阵不一致，必须失败关闭"
        )
    return ReportGateResult.from_unit_results(
        report_kind=spec.report_kind,
        unit_results=unit_results,
        evidence_snapshot_id=snapshot.evidence_snapshot_id,
        spec_version=spec.version,
        contract_version=contract_version,
        universe_summary=snapshot.universe_summary,
        spec_fingerprint=spec.spec_fingerprint,
    )


def derive_result_bearing(
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    *,
    result_bearing_source_roles: Sequence[SourceRole] = RESULT_BEARING_SOURCE_ROLES,
) -> bool:
    """result_bearing 只由已接受的观察性疗效/安全数值事实推导。

    计划样本量、计划终点、计划时间点、目标值和方案假设均不得触发；
    调用方不能直接传入布尔值。事实必须属于适格试验且不跨产品拼接。
    """
    trial_product = {
        edge.child_id: edge.parent_id
        for edge in snapshot.relationship_edges
        if edge.parent_type is GateObjectType.PRODUCT
        and edge.child_type is GateObjectType.TRIAL
    }
    for binding in bindings:
        if binding.review_state is not FactReviewState.ACCEPTED:
            continue
        if binding.fact_domain not in (FactDomain.EFFICACY, FactDomain.SAFETY):
            continue
        if binding.observation_kind is not ObservationKind.OBSERVED_RESULT:
            continue
        if binding.numeric_value is None:
            continue
        if binding.disclosure_state not in _REPORTED_STATES:
            continue
        if binding.source_role not in result_bearing_source_roles:
            continue
        # 合同要求：事实必须属于适格试验；无试验归属不得触发，未知试验失败关闭。
        if binding.trial_id is None:
            continue
        if binding.trial_id not in snapshot.trial_ids:
            raise GateEvaluationError("结果承载判定引用未知试验对象")
        if (
            binding.object_id in snapshot.product_ids
            and trial_product.get(binding.trial_id) != binding.object_id
        ):
            raise GateEvaluationError(
                "结果承载判定引用其他产品的试验，必须失败关闭"
            )
        return True
    return False
