"""B 类 fresh-source 研究包：类型化科学内容、GateSpec 评估、独立 QC 绑定与快照投影。

合同来源：v1.3 第 3、5、6、8 节（B 类证据比较室）。与 A 类兼容实现
（``source_research_service``）等价但不复制 A 门户模型：本模块不内嵌
渲染器数据模型，而是绑定 ``reports/b`` 的类型化事实观察（基线、疗效、
安全性、处置）与新增的试验设计事实，并把 B-v1 GateSpec 评估、独立科学
复核摘要绑定和不可变 B 报告快照投影组合成一个失败关闭的交接边界。

失败关闭合同（v1.3/R2.4）：
- 适应症/数据截止不一致（来源在截止后首次披露、证据快照摘要或截止不一致）；
- 独立科学复核被拒绝、复核身份与生产者相同或复核摘要与重算摘要不一致；
- 关键医学语义字段缺失（由 B-v1 GateSpec 逐对象评估失败关闭）；
- 报告类型不一致（``report_kind`` 只接受 ``B``）。

共享原语（来源采集、事实、声明、路线尝试、独立复核）通过
``fresh_research_primitives`` 的稳定导入面复用既有类型；持久化谱系原语由共享模块提供，
本模块只通过 :class:`FreshBEvidenceLineage` 消费其最小投影输入视图。
``rendered_unreviewed`` 的 report-data 快捷路径保持不变。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.application.fresh_research_primitives import (
    ResearchClaim,
    ResearchFact,
    RouteAttempt,
    ScientificReview,
    SourceCapture,
)
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    ConflictDisposition,
    DisclosureMaturity,
    EmptySetProof,
    EmptySetReasonCode,
    FactDomain,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    GateSpec,
    ObservationKind,
    ReportDecision,
    ReportGateResult,
    SourceRole,
    TrialDesignEvidence,
    TrialDesignKind,
    UniverseEdge,
    compute_universe_summary,
)
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from ci_workflow.reports.b.baseline import (
    _AGE_CONCEPTS,
    _SAMPLE_SIZE_CONCEPTS,
    _SEX_CONCEPTS,
    BaselineObservation,
    BaselineObservationError,
    BaselineStatisticForm,
    BaselineVariableDomain,
    build_baseline_gate_bindings,
)
from ci_workflow.reports.b.disposition import TrialDispositionObservation
from ci_workflow.reports.b.efficacy import EfficacyFactRow
from ci_workflow.reports.b.safety import SafetyFactRow, SafetyFamily
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    LockedSnapshot,
    ReportSnapshotManifest,
    SnapshotIntegrityError,
    SnapshotStore,
)
from ci_workflow.storage.sqlite import open_database

_GATE_SPEC_PATH = Path(__file__).resolve().parents[3] / "policies" / "gates" / "B-v1.yaml"

# SafetyFactRow 的封闭事件族到 B-v1 扩展单元的映射；
# treatment_related_teae 在 B-v1 中没有对应单元，只进入报告视图。
_SAFETY_FAMILY_UNITS: dict[SafetyFamily, str] = {
    SafetyFamily.TEAE: "b_safety_event_teae",
    SafetyFamily.SAE: "b_safety_event_sae",
    SafetyFamily.AESI: "b_safety_event_aesi",
    SafetyFamily.COMMON_AE: "b_safety_event_common",
    SafetyFamily.DEATH: "b_safety_event_death",
    SafetyFamily.GRADE_3_OR_HIGHER: "b_safety_event_grade3plus",
    SafetyFamily.DISCONTINUATION_DUE_TO_AE: "b_safety_event_discontinuation",
}

# b_safety_minimum_record 只接受 TEAE/SAE 最低数值记录作为关键安全证据。
_MINIMUM_RECORD_FAMILIES = frozenset({SafetyFamily.TEAE, SafetyFamily.SAE})

_REPORTED_STATES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)


class FreshBResearchPackageError(ValueError):
    """B 类新鲜来源研究包不能形成可审计的科学真源。"""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _text(value: str, *, label: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label}不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含明确时区")
    return value


def _unique_text(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, label=label) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label}不得重复")
    return normalized


def _locator_location(locator: EvidenceLocator) -> str:
    """把结构化定位压缩为门槛绑定的非空精确定位字段。"""
    if locator.field_path is not None:
        return locator.field_path
    parts: list[str] = [locator.document_role]
    for candidate in (
        locator.heading,
        locator.table,
        locator.row,
        locator.column,
        None if locator.page is None else f"page={locator.page}",
        locator.paragraph,
        locator.url,
    ):
        if candidate is not None:
            parts.append(candidate)
    return " / ".join(parts)


# ── B 类试验设计事实（试验/组别/比较/终点/效应差值） ─────────────────────────


class BFactProvenance(_StrictModel):
    """B 类事实的证据谱系绑定：来源角色、披露状态与不可变事实版本。"""

    source_id: str
    source_role: SourceRole
    disclosure_maturity: DisclosureMaturity
    disclosure_state: FactDisclosureState
    review_state: FactReviewState
    conflict_disposition: ConflictDisposition
    fact_id: str
    fact_version_id: str
    source_location: str | None = None
    route_receipt_id: str | None = None
    applicability_predicate_id: str | None = None
    reported_zero_text: str | None = None

    @field_validator("source_id", "fact_id", "fact_version_id")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("source_location", "route_receipt_id", "applicability_predicate_id")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, label="证据定位")

    @field_validator("reported_zero_text")
    @classmethod
    def _zero_text(cls, value: str | None) -> str | None:
        return None if value is None else value.strip() or None

    @model_validator(mode="after")
    def _disclosure_contract(self) -> Self:
        if self.disclosure_state is FactDisclosureState.CONFLICTING:
            if self.conflict_disposition is not ConflictDisposition.OPEN_CONFLICT_PRESERVED:
                raise ValueError("冲突事实必须保留开放冲突处置")
        elif self.conflict_disposition is not ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT:
            raise ValueError("非冲突事实必须选择已接受事实")
        if self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            if self.reported_zero_text is None:
                raise ValueError("已报告零值必须保留零值原文")
        elif self.reported_zero_text is not None:
            raise ValueError("非零值事实不得携带零值原文")
        if self.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE and (
            self.route_receipt_id is None
        ):
            raise ValueError("路线未解决事实必须链接路由回执")
        if self.disclosure_state is FactDisclosureState.NOT_APPLICABLE and (
            self.applicability_predicate_id is None
        ):
            raise ValueError("不适用事实必须链接适用性依据")
        return self


class BGroupRecord(_StrictModel):
    """一个试验组别的身份与比较角色。"""

    group_id: str
    trial_id: str
    label_zh: str
    arm_role: Literal["treatment", "control"]

    @field_validator("group_id", "trial_id", "label_zh")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))


class BEndpointRecord(_StrictModel):
    """一个核心终点的原始身份与定义。"""

    endpoint_id: str
    trial_id: str
    endpoint_role: str
    label: str
    definition: str

    @field_validator("endpoint_id", "trial_id", "endpoint_role", "label", "definition")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))


class BComparisonRecord(_StrictModel):
    """一个治疗—对照比较的身份、组别与终点关联。"""

    comparison_id: str
    trial_id: str
    treatment_group_id: str
    control_group_id: str
    treatment_group_label_zh: str
    control_group_label_zh: str
    endpoint_ids: tuple[str, ...] = Field(min_length=1)
    provenance: BFactProvenance

    @field_validator(
        "comparison_id",
        "trial_id",
        "treatment_group_id",
        "control_group_id",
        "treatment_group_label_zh",
        "control_group_label_zh",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("endpoint_ids")
    @classmethod
    def _endpoint_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text(values, label="比较终点标识")

    @model_validator(mode="after")
    def _comparison_groups_are_distinct(self) -> Self:
        if self.treatment_group_id == self.control_group_id:
            raise ValueError("治疗与对照必须绑定不同组别")
        return self


class BEffectDifferenceRecord(_StrictModel):
    """一条来源直接支持的组间效应记录；不由两臂数值自行相减。"""

    difference_id: str
    trial_id: str
    comparison_id: str
    endpoint_id: str
    definition: str
    direction: str
    unit: str
    value: int | float
    source_location: str
    provenance: BFactProvenance

    @field_validator(
        "difference_id",
        "trial_id",
        "comparison_id",
        "endpoint_id",
        "definition",
        "direction",
        "unit",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("source_location")
    @classmethod
    def _source_location_text(cls, value: str) -> str:
        return _text(value, label="效应来源定位")

    @field_validator("value")
    @classmethod
    def _finite_value(cls, value: int | float) -> int | float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("效应值必须是数值")
        return value


class BTrialRecord(_StrictModel):
    """一项 B 类核心结果试验的身份、设计、组别与终点记录。"""

    trial_id: str
    product_id: str
    display_name: str
    phase: str
    study_role: str
    design_kind: TrialDesignKind
    target_population_zh: str
    group_ids: tuple[str, ...] = Field(min_length=1)
    groups: tuple[BGroupRecord, ...] = Field(min_length=1)
    endpoints: tuple[BEndpointRecord, ...] = ()
    comparison: BComparisonRecord | None = None
    effect_differences: tuple[BEffectDifferenceRecord, ...] = ()
    identity_provenance: BFactProvenance
    population_provenance: BFactProvenance
    result_source_provenance: BFactProvenance

    @field_validator(
        "trial_id",
        "product_id",
        "display_name",
        "phase",
        "study_role",
        "target_population_zh",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("group_ids")
    @classmethod
    def _group_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text(values, label="试验组别标识")

    @model_validator(mode="after")
    def _trial_references_are_closed(self) -> Self:
        group_by_id = {group.group_id: group for group in self.groups}
        if len(group_by_id) != len(self.groups):
            raise ValueError("试验组别记录标识不得重复")
        if set(group_by_id) != set(self.group_ids):
            raise ValueError("试验组别标识与组别记录不一致")
        if any(group.trial_id != self.trial_id for group in self.groups):
            raise ValueError("组别记录必须绑定所属试验")
        endpoint_ids = tuple(endpoint.endpoint_id for endpoint in self.endpoints)
        if len(set(endpoint_ids)) != len(endpoint_ids):
            raise ValueError("试验终点标识不得重复")
        if any(endpoint.trial_id != self.trial_id for endpoint in self.endpoints):
            raise ValueError("终点记录必须绑定所属试验")
        endpoint_set = set(endpoint_ids)
        is_comparative = self.design_kind is TrialDesignKind.COMPARATIVE
        if (self.comparison is not None) is not is_comparative:
            raise ValueError("比较设计试验必须有比较记录，单臂设计不得携带比较记录")
        if self.comparison is not None:
            comparison = self.comparison
            if comparison.trial_id != self.trial_id:
                raise ValueError("比较记录必须绑定所属试验")
            if not set(comparison.endpoint_ids) <= endpoint_set:
                raise ValueError("比较记录引用了试验未声明的终点")
            if comparison.treatment_group_id not in group_by_id:
                raise ValueError("比较记录的治疗组别未知")
            if comparison.control_group_id not in group_by_id:
                raise ValueError("比较记录的对照组别未知")
            if (
                comparison.treatment_group_label_zh
                != group_by_id[comparison.treatment_group_id].label_zh
                or comparison.control_group_label_zh
                != group_by_id[comparison.control_group_id].label_zh
            ):
                raise ValueError("比较记录的组别标签必须与组别记录一致")
        difference_ids = tuple(item.difference_id for item in self.effect_differences)
        if len(set(difference_ids)) != len(difference_ids):
            raise ValueError("效应差值记录标识不得重复")
        for difference in self.effect_differences:
            if difference.trial_id != self.trial_id:
                raise ValueError("效应差值记录必须绑定所属试验")
            if self.comparison is None or difference.comparison_id != self.comparison.comparison_id:
                raise ValueError("效应差值记录必须绑定本试验的比较")
            if difference.endpoint_id not in endpoint_set:
                raise ValueError("效应差值记录引用了试验未声明的终点")
        if (
            self.result_source_provenance.disclosure_state in _REPORTED_STATES
            and self.result_source_provenance.source_location is None
        ):
            raise ValueError("已披露结果必须保存精确定位")
        return self


class BFactReviewBinding(_StrictModel):
    """疗效/安全性事实行进入门槛与谱系所需的复核谱系补全。"""

    row_id: str
    review_state: FactReviewState
    disclosure_maturity: DisclosureMaturity
    source_role: SourceRole
    conflict_disposition: ConflictDisposition

    @field_validator("row_id")
    @classmethod
    def _row_id(cls, value: str) -> str:
        return _text(value, label="事实行标识")


# ── 可摘要的 B 类科学内容与完整研究包 ────────────────────────────────────────


class FreshBResearchContent(BaseModel):
    """独立科学复核前可规范化、可摘要的 B 类科学内容。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["1.0"]
    report_kind: Literal["B"]
    project_id: str
    indication: str
    data_cutoff: datetime
    report_version: str
    producer_id: str
    universe_closed: Literal[True]
    universe_product_ids: tuple[str, ...] = Field(min_length=1)
    research_role_set_id: str
    indication_rule_set_id: str
    severity_anchor_concepts: tuple[str, ...] = Field(min_length=1)
    trials: tuple[BTrialRecord, ...] = Field(min_length=1)
    baseline: tuple[BaselineObservation, ...] = ()
    efficacy: tuple[EfficacyFactRow, ...] = ()
    safety: tuple[SafetyFactRow, ...] = ()
    disposition: tuple[TrialDispositionObservation, ...] = ()
    efficacy_review: tuple[BFactReviewBinding, ...] = ()
    safety_review: tuple[BFactReviewBinding, ...] = ()
    sources: tuple[SourceCapture, ...] = Field(min_length=1)
    route_attempts: tuple[RouteAttempt, ...] = ()
    facts: tuple[ResearchFact, ...] = Field(min_length=1)
    claims: tuple[ResearchClaim, ...] = Field(min_length=1)
    report_data: ReportBPortalData | None = None

    @field_validator("project_id", "indication", "report_version", "producer_id")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("data_cutoff")
    @classmethod
    def _cutoff_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("universe_product_ids")
    @classmethod
    def _product_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text(values, label="竞品宇宙产品标识")

    @field_validator("severity_anchor_concepts")
    @classmethod
    def _anchor_concepts(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_text(values, label="严重程度锚点概念")

    @field_validator("research_role_set_id", "indication_rule_set_id")
    @classmethod
    def _rule_set_ids(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @model_validator(mode="after")
    def _content_is_closed(self) -> Self:
        _assert_content_references_closed(self)
        _assert_sources_within_cutoff(self)
        result = evaluate_fresh_b_gate(
            self,
            evidence_snapshot_id=stable_id(
                "b-intake-gate", self.project_id, self.report_version
            ),
            contract_version="intake-validation",
        )
        if result.decision is ReportDecision.PASSED and self.report_data is None:
            raise ValueError("B 类门槛通过的研究包必须携带科学事实绑定的门户投影")
        if self.report_data is not None:
            self._validate_portal_projection()
        return self

    def _validate_portal_projection(self) -> None:
        """门户是科学内容的只读投影，不能成为第二套可漂移事实。"""
        portal = self.report_data
        if portal is None:
            raise ValueError("B 类门户投影不存在")
        if portal.indication != self.indication:
            raise ValueError("B 类门户投影的适应症与研究内容不一致")
        if portal.data_cutoff != self.data_cutoff:
            raise ValueError("B 类门户投影的数据截止与研究内容不一致")
        if portal.report_version != self.report_version:
            raise ValueError("B 类门户投影的报告版本与研究内容不一致")
        if portal.report_snapshot_id is not None:
            raise ValueError("研究包中的 B 类门户投影不得预填报告快照标识")
        if {item.id for item in portal.products} != set(self.universe_product_ids):
            raise ValueError("B 类门户投影的产品宇宙与研究内容不一致")
        if {item.id for item in portal.trials} != {item.trial_id for item in self.trials}:
            raise ValueError("B 类门户投影的试验宇宙与研究内容不一致")

        portal_efficacy = {item.row_id: item for item in portal.efficacy}
        if set(portal_efficacy) != {item.row_id for item in self.efficacy}:
            raise ValueError("B 类门户疗效投影的事实行集合与研究内容不一致")
        for efficacy_row in self.efficacy:
            efficacy_projection = portal_efficacy[efficacy_row.row_id]
            if (
                efficacy_projection.product_id != efficacy_row.product_id
                or efficacy_projection.trial_id != efficacy_row.trial_id
                or efficacy_projection.value != efficacy_row.value
                or efficacy_projection.numerator != efficacy_row.numerator
                or efficacy_projection.denominator != efficacy_row.denominator
                or efficacy_projection.unit != efficacy_row.unit
            ):
                raise ValueError(
                    f"B 类门户疗效投影改写了科学事实：{efficacy_row.row_id}"
                )

        portal_safety = {item.row_id: item for item in portal.safety}
        if set(portal_safety) != {item.row_id for item in self.safety}:
            raise ValueError("B 类门户安全性投影的事实行集合与研究内容不一致")
        for safety_row in self.safety:
            safety_projection = portal_safety[safety_row.row_id]
            if (
                safety_projection.product_id != safety_row.product_id
                or safety_projection.trial_id != safety_row.trial_id
                or safety_projection.value != safety_row.value
                or safety_projection.numerator != safety_row.numerator
                or safety_projection.denominator != safety_row.denominator
                or safety_projection.unit != safety_row.unit
            ):
                raise ValueError(
                    f"B 类门户安全性投影改写了科学事实：{safety_row.row_id}"
                )

        required_views: dict[str, Sequence[BaseModel]] = {
            "baseline_views": self.baseline,
            "efficacy_views": self.efficacy,
            "safety_views": self.safety,
            "disposition_views": self.disposition,
        }
        for field_name, rows in required_views.items():
            view = getattr(portal, field_name)
            if not isinstance(view, Mapping) or "facts" not in view:
                raise ValueError(f"B 类门户投影缺少 {field_name}.facts 科学事实绑定")
            expected = [item.model_dump(mode="json") for item in rows]
            try:
                projected_rows = [
                    type(template).model_validate(raw).model_dump(mode="json")
                    for template, raw in zip(rows, view["facts"], strict=True)
                ]
            except (TypeError, ValueError) as error:
                raise ValueError(f"B 类门户 {field_name}.facts 无法还原科学事实") from error
            if projected_rows != expected:
                label = field_name.removesuffix("_views")
                raise ValueError(f"B 类门户{label}投影与研究事实不一致")


class FreshBResearchPackage(FreshBResearchContent):
    """可由宿主 Agent 生成、由本地执行器验真的完整 B 类交接包。"""

    scientific_review: ScientificReview

    @property
    def research_content(self) -> dict[str, object]:
        return dict(
            FreshBResearchContent.model_validate(
                self.model_dump(mode="json", exclude={"scientific_review"})
            ).model_dump(mode="json")
        )

    @property
    def research_content_digest(self) -> str:
        return _digest(self.research_content)

    @model_validator(mode="after")
    def _package_is_independently_accepted(self) -> Self:
        if self.scientific_review.status != "accepted":
            raise ValueError("独立科学复核未接受，不得生成 B 类报告")
        if self.scientific_review.reviewer_id == self.producer_id:
            raise ValueError("独立科学复核不得由研究包生产者身份自行批准")
        if self.scientific_review.reviewed_at < max(
            source.acquired_at for source in self.sources
        ):
            raise ValueError("独立科学复核时间不得早于研究包来源获取时间")
        if self.scientific_review.reviewed_content_digest != self.research_content_digest:
            raise ValueError("独立科学复核与当前 B 类研究内容摘要不一致")
        return self


def compute_fresh_b_research_content_digest(payload: Mapping[str, object]) -> str:
    """供宿主在提交独立复核前计算与执行器一致的 B 类内容摘要。"""
    try:
        candidate = dict(payload)
        candidate.pop("scientific_review", None)
        normalized = FreshBResearchContent.model_validate(candidate)
        return _digest(normalized.model_dump(mode="json"))
    except ValueError as error:
        raise FreshBResearchPackageError(str(error)) from error


def load_fresh_b_research_package(path: Path) -> FreshBResearchPackage:
    """读取并验真 B 类新鲜来源研究包；任何合同违反都失败关闭。"""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FreshBResearchPackageError("无法读取 B 类新鲜来源研究包") from exc
    try:
        return FreshBResearchPackage.model_validate(value)
    except ValueError as exc:
        raise FreshBResearchPackageError(f"B 类新鲜来源研究包不符合合同：{exc}") from exc


# ── 内容引用闭合与截止检查 ──────────────────────────────────────────────────


def _assert_content_references_closed(content: FreshBResearchContent) -> None:
    product_set = set(content.universe_product_ids)
    trial_ids = tuple(trial.trial_id for trial in content.trials)
    if len(set(trial_ids)) != len(trial_ids):
        raise ValueError("B 类试验标识不得重复")
    trial_by_id = {trial.trial_id: trial for trial in content.trials}
    for trial in content.trials:
        if trial.product_id not in product_set:
            raise ValueError(f"试验引用了竞品宇宙之外的产品：{trial.trial_id}")
    source_ids = tuple(source.source_id for source in content.sources)
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("来源标识重复")
    source_set = set(source_ids)
    trial_id_set = set(trial_ids)

    def _check_observation_trial(trial_id: str, *, row_id: str) -> BTrialRecord:
        if trial_id not in trial_id_set:
            raise ValueError(f"观察引用了未声明试验：{row_id} -> {trial_id}")
        return trial_by_id[trial_id]

    for observation in content.baseline:
        baseline_trial = _check_observation_trial(
            observation.trial_id, row_id=observation.row_id
        )
        if observation.group_id not in baseline_trial.group_ids:
            raise ValueError(f"基线观察引用了未声明组别：{observation.row_id}")
        if observation.product_id not in product_set:
            raise ValueError(f"基线观察引用了宇宙之外产品：{observation.row_id}")
        if observation.source_version_id not in source_set:
            raise ValueError(f"基线观察引用了包外来源：{observation.row_id}")
    for efficacy_row in content.efficacy:
        efficacy_trial = _check_observation_trial(
            efficacy_row.trial_id, row_id=efficacy_row.row_id
        )
        if efficacy_row.endpoint_family_id not in {
            item.endpoint_id for item in efficacy_trial.endpoints
        }:
            raise ValueError(f"疗效事实引用了未声明终点：{efficacy_row.row_id}")
        if efficacy_row.arm_id not in efficacy_trial.group_ids:
            raise ValueError(f"疗效事实引用了未声明组别：{efficacy_row.row_id}")
        if efficacy_row.source_version_id not in source_set:
            raise ValueError(f"疗效事实引用了包外来源：{efficacy_row.row_id}")
    for safety_row in content.safety:
        safety_trial = _check_observation_trial(
            safety_row.trial_id, row_id=safety_row.row_id
        )
        if safety_row.arm_id not in safety_trial.group_ids:
            raise ValueError(f"安全性事实引用了未声明组别：{safety_row.row_id}")
        if safety_row.source_version_id not in source_set:
            raise ValueError(f"安全性事实引用了包外来源：{safety_row.row_id}")
    for disposition_row in content.disposition:
        disposition_trial = _check_observation_trial(
            disposition_row.trial_id, row_id=disposition_row.row_id
        )
        if (
            disposition_row.group_id is not None
            and disposition_row.group_id not in disposition_trial.group_ids
        ):
            raise ValueError(f"处置事实引用了未声明组别：{disposition_row.row_id}")
        if disposition_row.source_version_id not in source_set:
            raise ValueError(f"处置事实引用了包外来源：{disposition_row.row_id}")

    _assert_review_bindings_match(content)
    _assert_fact_coverage(content, source_set)


def _assert_review_bindings_match(content: FreshBResearchContent) -> None:
    def _bindings_match_rows(
        rows: tuple[Any, ...], bindings: tuple[BFactReviewBinding, ...], *, label: str
    ) -> dict[str, BFactReviewBinding]:
        row_ids = tuple(str(row.row_id) for row in rows)
        if len(set(row_ids)) != len(row_ids):
            raise ValueError(f"{label}事实行标识重复")
        binding_by_row = {binding.row_id: binding for binding in bindings}
        if len(binding_by_row) != len(bindings):
            raise ValueError(f"{label}复核谱系行标识重复")
        if set(binding_by_row) != set(row_ids):
            missing = sorted(set(row_ids) - set(binding_by_row))
            extra = sorted(set(binding_by_row) - set(row_ids))
            raise ValueError(
                f"{label}事实行与复核谱系不一致：缺少 {missing}；多余 {extra}"
            )
        return binding_by_row

    _bindings_match_rows(content.efficacy, content.efficacy_review, label="疗效")
    safety_review = _bindings_match_rows(
        content.safety, content.safety_review, label="安全性"
    )
    for safety_row in content.safety:
        if (
            safety_row.source_role is not None
            and safety_row.source_role != safety_review[safety_row.row_id].source_role.value
        ):
            raise ValueError(f"安全性事实行来源角色与复核谱系不一致：{safety_row.row_id}")
        has_conflict = (
            bool(safety_row.conflicting_source_row_ids) or safety_row.conflict_note is not None
        )
        expected = (
            ConflictDisposition.OPEN_CONFLICT_PRESERVED
            if has_conflict
            else ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
        )
        if safety_review[safety_row.row_id].conflict_disposition is not expected:
            raise ValueError(f"安全性事实行冲突处置与复核谱系不一致：{safety_row.row_id}")


def _assert_fact_coverage(content: FreshBResearchContent, source_set: set[str]) -> None:
    fact_ids = tuple(fact.fact_id for fact in content.facts)
    if len(set(fact_ids)) != len(fact_ids):
        raise ValueError("事实标识重复")
    row_refs = tuple(fact.row_ref for fact in content.facts)
    if len(set(row_refs)) != len(row_refs):
        raise ValueError("事实行引用标识重复")
    fact_id_set = set(fact_ids)
    required_refs: set[str] = set()
    for trial in content.trials:
        required_refs.add(trial.identity_provenance.fact_id)
        required_refs.add(trial.population_provenance.fact_id)
        required_refs.add(trial.result_source_provenance.fact_id)
        if trial.comparison is not None:
            required_refs.add(trial.comparison.provenance.fact_id)
        required_refs.update(item.provenance.fact_id for item in trial.effect_differences)
    # 基线与处置观察的行标识由模型从科学身份派生，事实绑定改用其保留的
    # 观察标识；疗效与安全性事实行保留调用方提供的行标识。
    for observation in content.baseline:
        required_refs.add(observation.observation_id)
    for disposition_row in content.disposition:
        required_refs.add(disposition_row.observation_id)
    for efficacy_row in content.efficacy:
        required_refs.add(efficacy_row.row_id)
    for safety_row in content.safety:
        required_refs.add(safety_row.row_id)
    missing = sorted(required_refs - set(row_refs))
    if missing:
        raise ValueError("核心 B 类事实缺少来源绑定：" + "、".join(missing[:5]))
    for fact in content.facts:
        if fact.source_id not in source_set:
            raise ValueError(f"事实引用了研究包外来源：{fact.fact_id}")
    for claim in content.claims:
        if not set(claim.fact_ids) <= fact_id_set:
            raise ValueError(f"声明引用了研究包外事实：{claim.claim_id}")
    claim_ids = tuple(claim.claim_id for claim in content.claims)
    if len(set(claim_ids)) != len(claim_ids):
        raise ValueError("声明标识重复")


def _assert_sources_within_cutoff(content: FreshBResearchContent) -> None:
    for source in content.sources:
        if not source.date_evidence("first_disclosed_at").is_known_by(content.data_cutoff):
            raise ValueError(
                "截止日之后或无法证明截止时点前首次披露的来源不得进入当前 B 类快照："
                f"{source.source_id}"
            )


# ── GateSpec 评估：宇宙快照与证据绑定构建 ────────────────────────────────────


def load_b_gate_spec() -> GateSpec:
    """严格加载 B-v1 门槛说明书并核对报告类型。"""
    spec = GateSpec.from_yaml(_GATE_SPEC_PATH)
    if spec.report_kind is not ReportKind.B:
        raise FreshBResearchPackageError("B 类门槛说明书的报告类型不一致")
    return spec


def build_b_gate_universe(
    content: FreshBResearchContent, *, evidence_snapshot_id: str
) -> ApplicableUniverseSnapshot:
    """由类型化 B 内容确定性构建已闭合适用宇宙快照。"""
    trial_ids: list[str] = []
    group_ids: list[str] = []
    comparison_ids: list[str] = []
    endpoint_ids: list[str] = []
    edges: list[UniverseEdge] = []
    design_evidence: list[TrialDesignEvidence] = []
    for trial in content.trials:
        trial_ids.append(trial.trial_id)
        edges.append(
            UniverseEdge(
                parent_type=GateObjectType.PRODUCT,
                parent_id=trial.product_id,
                child_type=GateObjectType.TRIAL,
                child_id=trial.trial_id,
            )
        )
        for group_id in trial.group_ids:
            group_ids.append(group_id)
            edges.append(
                UniverseEdge(
                    parent_type=GateObjectType.TRIAL,
                    parent_id=trial.trial_id,
                    child_type=GateObjectType.GROUP,
                    child_id=group_id,
                )
            )
        for endpoint in trial.endpoints:
            endpoint_ids.append(endpoint.endpoint_id)
            edges.append(
                UniverseEdge(
                    parent_type=GateObjectType.TRIAL,
                    parent_id=trial.trial_id,
                    child_type=GateObjectType.ENDPOINT,
                    child_id=endpoint.endpoint_id,
                )
            )
            # 终点→组别关联边：疗效绑定携带终点+组别作用域时必须可回溯；
            # 比较设计试验的权威评估组别仍由比较关联解析，不因关联边改变。
            for group_id in trial.group_ids:
                edges.append(
                    UniverseEdge(
                        parent_type=GateObjectType.ENDPOINT,
                        parent_id=endpoint.endpoint_id,
                        child_type=GateObjectType.GROUP,
                        child_id=group_id,
                    )
                )
        if trial.comparison is not None:
            comparison = trial.comparison
            comparison_ids.append(comparison.comparison_id)
            edges.append(
                UniverseEdge(
                    parent_type=GateObjectType.TRIAL,
                    parent_id=trial.trial_id,
                    child_type=GateObjectType.COMPARISON,
                    child_id=comparison.comparison_id,
                )
            )
            for group_id in (comparison.treatment_group_id, comparison.control_group_id):
                edges.append(
                    UniverseEdge(
                        parent_type=GateObjectType.COMPARISON,
                        parent_id=comparison.comparison_id,
                        child_type=GateObjectType.GROUP,
                        child_id=group_id,
                    )
                )
            for endpoint_id in comparison.endpoint_ids:
                edges.append(
                    UniverseEdge(
                        parent_type=GateObjectType.COMPARISON,
                        parent_id=comparison.comparison_id,
                        child_type=GateObjectType.ENDPOINT,
                        child_id=endpoint_id,
                    )
                )
        design_label = (
            "比较设计" if trial.design_kind is TrialDesignKind.COMPARATIVE else "单臂设计"
        )
        design_evidence.append(
            TrialDesignEvidence(
                trial_id=trial.trial_id,
                design_kind=trial.design_kind,
                evidence_version_id=f"{trial.trial_id}:design",
                explanation_zh=(
                    f"试验 {trial.display_name} 的登记与主要报告记录为{design_label}"
                ),
            )
        )
    empty_set_proofs: list[EmptySetProof] = []
    if not comparison_ids:
        empty_set_proofs.append(
            EmptySetProof(
                object_type=GateObjectType.COMPARISON,
                reason_code=EmptySetReasonCode.STUDY_DESIGN_SINGLE_ARM,
                evidence_version_id="comparison:empty:single-arm-design",
                explanation_zh="全部核心试验均为单臂设计，不存在治疗—对照比较对象",
            )
        )
    if not endpoint_ids:
        empty_set_proofs.append(
            EmptySetProof(
                object_type=GateObjectType.ENDPOINT,
                reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
                evidence_version_id="endpoint:empty:no-declared-endpoint",
                explanation_zh="当前核心试验未声明任何核心终点对象",
            )
        )
    # B 类核心层不把时间点建为独立对象；时间窗保留在终点与安全性观察内。
    empty_set_proofs.append(
        EmptySetProof(
            object_type=GateObjectType.TIMEPOINT,
            reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
            evidence_version_id="timepoint:empty:observation-embedded",
            explanation_zh="B 类核心层未声明独立时间点对象，时间窗保留在观察内",
        )
    )
    proofs = tuple(empty_set_proofs)
    summary = compute_universe_summary(
        project_id=content.project_id,
        evidence_snapshot_id=evidence_snapshot_id,
        research_role_set_id=content.research_role_set_id,
        product_ids=content.universe_product_ids,
        trial_ids=tuple(trial_ids),
        comparison_ids=tuple(comparison_ids),
        group_ids=tuple(group_ids),
        endpoint_ids=tuple(endpoint_ids),
        empty_set_proofs=proofs,
        relationship_edges=tuple(edges),
        trial_design_evidence=tuple(design_evidence),
        indication_rule_set_id=content.indication_rule_set_id,
    )
    return ApplicableUniverseSnapshot(
        project_id=content.project_id,
        evidence_snapshot_id=evidence_snapshot_id,
        research_role_set_id=content.research_role_set_id,
        indication_rule_set_id=content.indication_rule_set_id,
        product_ids=content.universe_product_ids,
        trial_ids=tuple(trial_ids),
        comparison_ids=tuple(comparison_ids),
        group_ids=tuple(group_ids),
        endpoint_ids=tuple(endpoint_ids),
        empty_set_proofs=proofs,
        relationship_edges=tuple(edges),
        trial_design_evidence=tuple(design_evidence),
        universe_summary=summary,
        enumeration_complete=True,
    )


def _baseline_unit_id(
    observation: BaselineObservation, *, severity_concepts: frozenset[str]
) -> str:
    concept = observation.standardized_concept.casefold().replace("-", "_").replace(" ", "_")
    if observation.variable_domain is BaselineVariableDomain.BASELINE_SEVERITY:
        if concept not in severity_concepts:
            raise ValueError(
                f"严重程度锚点概念未被当前适应症认可：{observation.row_id}（{concept}）"
            )
        return "b_baseline_severity_anchor"
    if observation.statistic_form is BaselineStatisticForm.SAMPLE_SIZE:
        if concept not in _SAMPLE_SIZE_CONCEPTS:
            raise ValueError(f"样本量事实概念不规范：{observation.row_id}")
        return "b_baseline_sample_size"
    if concept in _AGE_CONCEPTS:
        return "b_baseline_age"
    if concept in _SEX_CONCEPTS:
        return "b_baseline_sex"
    raise ValueError(f"基线事实无法确定 B-v1 门槛单元：{observation.row_id}")


def _timepoint_text(value: int | float | str, unit: str) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    return f"{value:g} {unit}".strip()


def _trial_level_binding(
    trial: BTrialRecord,
    provenance: BFactProvenance,
    *,
    unit_id: str,
) -> GateEvidenceBinding:
    return GateEvidenceBinding(
        binding_id=stable_id("b-gate-binding", unit_id, provenance.fact_version_id),
        unit_id=unit_id,
        object_id=trial.trial_id,
        fact_version_id=provenance.fact_version_id,
        trial_id=trial.trial_id,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        source_location=provenance.source_location,
        route_receipt_id=provenance.route_receipt_id,
        review_state=provenance.review_state,
        disclosure_state=provenance.disclosure_state,
        disclosure_maturity=provenance.disclosure_maturity,
        source_role=provenance.source_role,
        conflict_disposition=provenance.conflict_disposition,
        applicability_predicate_id=provenance.applicability_predicate_id,
        reported_zero_text=provenance.reported_zero_text,
    )


def _safety_evidence_binding(
    unit_id: str,
    safety_row: SafetyFactRow,
    review: BFactReviewBinding,
    *,
    treatment_label: str | None,
    control_label: str | None,
) -> GateEvidenceBinding:
    """把一条安全性事实行严格转换为指定单元的证据绑定。"""
    return GateEvidenceBinding(
        binding_id=stable_id("b-gate-binding", unit_id, safety_row.row_id),
        unit_id=unit_id,
        object_id=safety_row.arm_id,
        fact_version_id=safety_row.row_id,
        trial_id=safety_row.trial_id,
        group_id=safety_row.arm_id,
        fact_domain=FactDomain.SAFETY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=safety_row.value,
        denominator=safety_row.denominator,
        event_definition=safety_row.event_definition_zh,
        time_window=safety_row.time_window_zh,
        analysis_population=safety_row.analysis_population_zh,
        treatment_group=treatment_label,
        control_group=control_label,
        source_location=_locator_location(safety_row.source_locator),
        route_receipt_id=safety_row.unresolved_route_receipt_id,
        review_state=review.review_state,
        disclosure_state=safety_row.disclosure_state,
        disclosure_maturity=review.disclosure_maturity,
        source_role=review.source_role,
        conflict_disposition=review.conflict_disposition,
        applicability_predicate_id=safety_row.applicability_predicate_id,
        # G20-2：SafetyFactRow 无独立零值原文字段；真实登记零的原文由
        # 事件定义与原始值共同构成（来源可回到登记记录），不另造证据。
        reported_zero_text=(
            f"{safety_row.event_definition_zh or safety_row.source_term}"
            f"（登记原始值：{safety_row.raw_value}）"
            if safety_row.disclosure_state is FactDisclosureState.REPORTED_ZERO
            and safety_row.raw_value is not None
            else None
        ),
    )


def build_b_gate_bindings(
    content: FreshBResearchContent,
) -> tuple[GateEvidenceBinding, ...]:
    """由类型化 B 内容确定性构建 B-v1 证据绑定；不聚合、不借值、不改状态。"""
    bindings: list[GateEvidenceBinding] = []

    if content.baseline:
        unit_ids = tuple(
            _baseline_unit_id(
                observation, severity_concepts=frozenset(content.severity_anchor_concepts)
            )
            for observation in content.baseline
        )
        try:
            bindings.extend(
                build_baseline_gate_bindings(
                    content.baseline,
                    unit_ids,
                    severity_anchor_concepts=frozenset(content.severity_anchor_concepts),
                )
            )
        except BaselineObservationError as error:
            raise FreshBResearchPackageError(str(error)) from error

    trial_by_id = {trial.trial_id: trial for trial in content.trials}
    for trial in content.trials:
        bindings.append(
            _trial_level_binding(
                trial,
                trial.identity_provenance,
                unit_id="b_trial_identity_role",
            )
        )
        bindings.append(
            _trial_level_binding(
                trial,
                trial.population_provenance,
                unit_id="b_target_population_groups",
            )
        )
        bindings.append(
            _trial_level_binding(
                trial,
                trial.result_source_provenance,
                unit_id="b_source_role_maturity_location",
            )
        )
        if trial.comparison is not None:
            comparison = trial.comparison
            bindings.append(
                GateEvidenceBinding(
                    binding_id=stable_id(
                        "b-gate-binding",
                        "b_treatment_control_identity",
                        comparison.provenance.fact_version_id,
                    ),
                    unit_id="b_treatment_control_identity",
                    object_id=comparison.comparison_id,
                    fact_version_id=comparison.provenance.fact_version_id,
                    trial_id=trial.trial_id,
                    comparison_id=comparison.comparison_id,
                    fact_domain=FactDomain.TRIAL_DESIGN,
                    observation_kind=ObservationKind.OBSERVED_RESULT,
                    treatment_group=comparison.treatment_group_label_zh,
                    control_group=comparison.control_group_label_zh,
                    source_location=comparison.provenance.source_location,
                    review_state=comparison.provenance.review_state,
                    disclosure_state=comparison.provenance.disclosure_state,
                    disclosure_maturity=comparison.provenance.disclosure_maturity,
                    source_role=comparison.provenance.source_role,
                    conflict_disposition=comparison.provenance.conflict_disposition,
                    applicability_predicate_id=comparison.provenance.applicability_predicate_id,
                )
            )
        for difference in trial.effect_differences:
            bindings.append(
                GateEvidenceBinding(
                    binding_id=stable_id(
                        "b-gate-binding",
                        "b_effect_difference_support",
                        difference.provenance.fact_version_id,
                    ),
                    unit_id="b_effect_difference_support",
                    object_id=difference.comparison_id,
                    fact_version_id=difference.provenance.fact_version_id,
                    trial_id=difference.trial_id,
                    comparison_id=difference.comparison_id,
                    endpoint_id=difference.endpoint_id,
                    fact_domain=FactDomain.EFFICACY,
                    observation_kind=ObservationKind.OBSERVED_RESULT,
                    numeric_value=difference.value,
                    definition=difference.definition,
                    direction=difference.direction,
                    unit=difference.unit,
                    source_location=difference.source_location,
                    review_state=difference.provenance.review_state,
                    disclosure_state=difference.provenance.disclosure_state,
                    disclosure_maturity=difference.provenance.disclosure_maturity,
                    source_role=difference.provenance.source_role,
                    conflict_disposition=difference.provenance.conflict_disposition,
                )
            )

    efficacy_review = {binding.row_id: binding for binding in content.efficacy_review}
    for efficacy_row in content.efficacy:
        review = efficacy_review[efficacy_row.row_id]
        bindings.append(
            GateEvidenceBinding(
                binding_id=stable_id(
                    "b-gate-binding", "b_core_efficacy_endpoint", efficacy_row.row_id
                ),
                unit_id="b_core_efficacy_endpoint",
                object_id=efficacy_row.endpoint_family_id,
                fact_version_id=efficacy_row.row_id,
                trial_id=efficacy_row.trial_id,
                endpoint_id=efficacy_row.endpoint_family_id,
                group_id=efficacy_row.arm_id,
                fact_domain=FactDomain.EFFICACY,
                observation_kind=ObservationKind.OBSERVED_RESULT,
                numeric_value=efficacy_row.value,
                unit=efficacy_row.unit,
                denominator=efficacy_row.denominator,
                definition=efficacy_row.original_definition,
                direction=efficacy_row.direction.value,
                timepoint=_timepoint_text(
                    efficacy_row.actual_timepoint, efficacy_row.actual_timepoint_unit
                ),
                analysis_population=efficacy_row.analysis_population,
                source_location=_locator_location(efficacy_row.source_locator),
                review_state=review.review_state,
                disclosure_state=efficacy_row.disclosure_state,
                disclosure_maturity=review.disclosure_maturity,
                source_role=review.source_role,
                conflict_disposition=review.conflict_disposition,
            )
        )

    safety_review = {binding.row_id: binding for binding in content.safety_review}
    for safety_row in content.safety:
        review = safety_review[safety_row.row_id]
        trial = trial_by_id[safety_row.trial_id]
        safety_comparison = trial.comparison
        treatment_label = (
            safety_comparison.treatment_group_label_zh
            if safety_comparison is not None
            else next(
                (
                    group.label_zh
                    for group in trial.groups
                    if group.group_id == safety_row.arm_id
                ),
                None,
            )
        )
        control_label = (
            safety_comparison.control_group_label_zh if safety_comparison is not None else None
        )
        unit_id = _SAFETY_FAMILY_UNITS.get(safety_row.family)
        if unit_id is not None:
            bindings.append(
                _safety_evidence_binding(
                    unit_id,
                    safety_row,
                    review,
                    treatment_label=treatment_label,
                    control_label=control_label,
                )
            )
        if (
            safety_row.family in _MINIMUM_RECORD_FAMILIES
            and safety_row.event_definition_zh is not None
            and safety_row.time_window_zh is not None
        ):
            bindings.append(
                _safety_evidence_binding(
                    "b_safety_minimum_record",
                    safety_row,
                    review,
                    treatment_label=treatment_label,
                    control_label=control_label,
                )
            )

    for disposition_row in content.disposition:
        reported = disposition_row.disclosure_state in _REPORTED_STATES
        bindings.append(
            GateEvidenceBinding(
                binding_id=stable_id(
                    "b-gate-binding", "b_trial_disposition", disposition_row.row_id
                ),
                unit_id="b_trial_disposition",
                object_id=disposition_row.trial_id,
                fact_version_id=disposition_row.row_id,
                trial_id=disposition_row.trial_id,
                fact_domain=FactDomain.TRIAL_DESIGN,
                observation_kind=ObservationKind.OBSERVED_RESULT,
                numeric_value=disposition_row.value if reported else None,
                denominator=disposition_row.denominator if reported else None,
                source_location=_locator_location(disposition_row.source_locator),
                route_receipt_id=disposition_row.route_receipt_id,
                review_state=disposition_row.review_state,
                disclosure_state=disposition_row.disclosure_state,
                disclosure_maturity=disposition_row.disclosure_maturity,
                source_role=disposition_row.source_role,
                conflict_disposition=disposition_row.conflict_disposition,
                applicability_predicate_id=disposition_row.applicability_predicate_id,
                reported_zero_text=disposition_row.reported_zero_text,
            )
        )
    return tuple(bindings)


def evaluate_fresh_b_gate(
    content: FreshBResearchContent,
    *,
    evidence_snapshot_id: str,
    contract_version: str,
    fact_version_by_ref: Mapping[str, str] | None = None,
) -> ReportGateResult:
    """对 B 类内容执行 B-v1 GateSpec 确定性评估。"""
    try:
        universe = build_b_gate_universe(content, evidence_snapshot_id=evidence_snapshot_id)
        bindings = build_b_gate_bindings(content)
        if fact_version_by_ref is not None:
            aliases = _b_fact_version_aliases(content, fact_version_by_ref)
            missing = sorted(
                {item.fact_version_id for item in bindings} - set(aliases)
            )
            if missing:
                raise FreshBResearchPackageError(
                    "B 类门槛绑定无法解析到已摄取事实版本：" + "、".join(missing[:5])
                )
            bindings = tuple(
                item.model_copy(
                    update={"fact_version_id": aliases[item.fact_version_id]}
                )
                for item in bindings
            )
        return evaluate_report(
            load_b_gate_spec(),
            universe,
            bindings,
            contract_version=contract_version,
        )
    except (GateEvaluationError, ValueError) as error:
        if isinstance(error, FreshBResearchPackageError):
            raise
        raise FreshBResearchPackageError(f"B 类证据门槛评估失败：{error}") from error


# ── 报告快照投影 ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FreshBEvidenceLineage:
    """共享谱系原语在 B 投影边界的最小输入视图。

    共享模块负责来源/事实/声明的真实摄取并锁定证据快照；本视图只携带
    B 报告快照投影所需的身份与版本清单。
    """

    evidence_snapshot: LockedSnapshot
    source_version_ids: tuple[str, ...]
    fragment_ids: tuple[str, ...]
    fact_version_ids: tuple[str, ...]
    fact_version_by_ref: Mapping[str, str] = field(default_factory=dict)


def _b_fact_version_aliases(
    content: FreshBResearchContent,
    persisted: Mapping[str, str],
) -> dict[str, str]:
    aliases = dict(persisted)
    for baseline_row in content.baseline:
        if baseline_row.observation_id in persisted:
            aliases[baseline_row.row_id] = persisted[baseline_row.observation_id]
    for disposition_row in content.disposition:
        if disposition_row.observation_id in persisted:
            aliases[disposition_row.row_id] = persisted[disposition_row.observation_id]
    provenances: list[BFactProvenance] = []
    for trial in content.trials:
        provenances.extend(
            (
                trial.identity_provenance,
                trial.population_provenance,
                trial.result_source_provenance,
            )
        )
        if trial.comparison is not None:
            provenances.append(trial.comparison.provenance)
        provenances.extend(item.provenance for item in trial.effect_differences)
    for provenance in provenances:
        if provenance.fact_id in persisted:
            aliases[provenance.fact_version_id] = persisted[provenance.fact_id]
    return aliases


@dataclass(frozen=True)
class FreshBReportProjection:
    """B 报告快照投影结果：不可变快照身份与门槛绑定。"""

    report_snapshot: LockedSnapshot
    manifest: ReportSnapshotManifest
    evidence_snapshot_id: str
    claim_snapshot_id: str
    coverage_set_id: str
    gate_result: ReportGateResult


def project_fresh_b_report_snapshot(
    package: FreshBResearchPackage,
    *,
    project_root: Path,
    project_id: str,
    contract_version: int,
    lineage: FreshBEvidenceLineage,
    created_at: datetime,
) -> FreshBReportProjection:
    """在 GateSpec 通过且独立 QC 接受后锁定 B 类不可变报告快照。

    - 证据快照必须真实存在、完整可读，且其科学内容摘要与当前包一致；
    - 门槛结果用真实证据快照标识重算，任何阻断都拒绝生成快照；
    - 报告快照与门槛评估记录幂等（同内容同身份，不覆盖历史）。
    coverage_sets/coverage_projections 行引用渲染产物，由渲染后的持久化
    绑定步骤写入；``rendered_unreviewed`` 的 report-data 快捷路径不变。
    """
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise FreshBResearchPackageError("投影时间必须包含明确时区")
    if not lineage.source_version_ids or not lineage.fact_version_ids:
        raise FreshBResearchPackageError("B 类证据谱系缺少来源或事实版本清单")
    if lineage.evidence_snapshot.kind != "evidence":
        raise FreshBResearchPackageError("B 类报告快照必须绑定证据快照")
    store = SnapshotStore(project_root)
    try:
        payload = store.read(lineage.evidence_snapshot)
    except (SnapshotIntegrityError, OSError, ValueError) as error:
        raise FreshBResearchPackageError(f"B 类证据快照不可信：{error}") from error
    evidence_manifest = EvidenceSnapshotManifest.model_validate(payload)
    if evidence_manifest.scientific_content_digest != package.research_content_digest:
        raise FreshBResearchPackageError(
            "证据快照摘要与当前 B 类研究内容不一致，拒绝投影报告快照"
        )
    if evidence_manifest.project_id != project_id:
        raise FreshBResearchPackageError("证据快照与项目身份不一致")
    if evidence_manifest.data_cutoff != package.data_cutoff:
        raise FreshBResearchPackageError("证据快照与 B 类研究包的数据截止不一致")

    gate_result = evaluate_fresh_b_gate(
        package,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        contract_version=str(contract_version),
        fact_version_by_ref=lineage.fact_version_by_ref or None,
    )
    if lineage.fact_version_by_ref and not set(
        fact_version_id
        for result in gate_result.unit_results
        for fact_version_id in result.fact_version_ids
    ) <= set(lineage.fact_version_ids):
        raise FreshBResearchPackageError("B 类门槛引用了证据快照之外的事实版本")
    if gate_result.decision is not ReportDecision.PASSED:
        raise FreshBResearchPackageError(
            f"B 类关键证据门槛未通过，不得锁定报告快照：{gate_result.user_summary_zh}"
        )

    claim_ids = tuple(claim.claim_id for claim in package.claims)
    claim_snapshot_id = stable_id(
        "claim-snapshot", project_id, package.research_content_digest, *claim_ids
    )
    coverage_set_id = stable_id(
        "coverage-set",
        project_id,
        "B",
        lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id,
    )
    report_manifest = ReportSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=contract_version,
        report="B",
        report_version=package.report_version,
        data_cutoff=package.data_cutoff,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        claim_ids=claim_ids,
        created_at=created_at,
    )
    locked = store.lock_report_snapshot(
        report="B", manifest=report_manifest.model_dump(mode="json")
    )
    _record_projection_rows(
        project_root,
        project_id=project_id,
        package=package,
        lineage=lineage,
        gate_result=gate_result,
        spec=load_b_gate_spec(),
        created_at=created_at,
    )
    return FreshBReportProjection(
        report_snapshot=locked,
        manifest=report_manifest,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        gate_result=gate_result,
    )


def _record_projection_rows(
    project_root: Path,
    *,
    project_id: str,
    package: FreshBResearchPackage,
    lineage: FreshBEvidenceLineage,
    gate_result: ReportGateResult,
    spec: GateSpec,
    created_at: datetime,
) -> None:
    timestamp = created_at.isoformat()
    gate_details = json.dumps(
        {
            "result_key": gate_result.result_key,
            "spec_fingerprint": gate_result.spec_fingerprint,
            "universe_summary": gate_result.universe_summary,
            "evidence_snapshot_id": lineage.evidence_snapshot.snapshot_id,
            "scientific_reviewer": package.scientific_review.reviewer_id,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    with open_database(project_root / "state" / "project.sqlite") as database:
        database.execute(
            """
            INSERT OR IGNORE INTO gate_evaluations (
                gate_evaluation_id,project_id,report_kind,gate_id,result,details_json,created_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                stable_id("gate-evaluation", project_id, "B", gate_result.result_key),
                project_id,
                "B",
                spec.spec_id,
                "passed",
                gate_details,
                timestamp,
            ),
        )


__all__ = [
    "BComparisonRecord",
    "BEffectDifferenceRecord",
    "BEndpointRecord",
    "BFactProvenance",
    "BFactReviewBinding",
    "BGroupRecord",
    "BTrialRecord",
    "FreshBEvidenceLineage",
    "FreshBReportProjection",
    "FreshBResearchContent",
    "FreshBResearchPackage",
    "FreshBResearchPackageError",
    "build_b_gate_bindings",
    "build_b_gate_universe",
    "compute_fresh_b_research_content_digest",
    "evaluate_fresh_b_gate",
    "load_b_gate_spec",
    "load_fresh_b_research_package",
    "project_fresh_b_report_snapshot",
]
