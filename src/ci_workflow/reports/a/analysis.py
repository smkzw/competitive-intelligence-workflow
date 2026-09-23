"""Task 5.1 A 类成熟度分层与逐层必需字段判定（强输入）。

直接消费 Phase 3 已接受的 ``ApplicableUniverseSnapshot`` 与
``GateEvidenceBinding``：成熟度由 ``derive_product_maturity`` 推导，
result-bearing 由 ``derive_result_bearing`` 或强类型官方已发布结果证据触发；
调用方不能手工降级、删除项目或手工触发。证据作用域由
``assert_bindings_in_universe`` 闭合：未知试验、跨产品拼接失败关闭。

逐层语义（§12.2）：
- 适用层 = 成熟度分层及以下各层；必需字段逐层累计；
- 不适用只能显式表达且仅限规格声明允许的字段；未公开、检索后未找到、
  技术不可用均为独立缺失状态，阻断必需字段；
- 结果承载项目的最低疗效/TEAE-SAE 记录直接从已接受绑定判定：真实有限数值
  （已报告零值必须是数值零）、正分母、完整成分、精确来源定位，且来自适格
  锚定试验；对照组仅单臂设计可缺省；
- 结果承载项目缺适格锚定试验、可解释核心疗效记录或 TEAE/SAE 数值摘要时
  A 门槛失败，不删除产品继续。
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.gates.evaluator import derive_product_maturity
from ci_workflow.gates.models import (
    RESULT_BEARING_SOURCE_ROLES,
    ApplicableUniverseSnapshot,
    DevelopmentMaturity,
    FactDomain,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    ObservationKind,
    SourceRole,
    TrialDesignKind,
    assert_applicable_universe_closed,
    assert_bindings_in_universe,
    derive_result_bearing,
    disclosure_maturity_rank,
)
from ci_workflow.reports.a.contracts import (
    _SPEC_BY_KEY,
    ANCHOR_TRIAL,
    CANONICAL_IDENTITY_AND_ALIASES,
    CHINA_STAGE_STATUS_DATE,
    CORE_EFFICACY_RECORD,
    CORE_TRIAL_DEVELOPMENT_ROLE,
    CORE_TRIAL_IDENTITY,
    CORE_TRIAL_STATUS,
    DEVELOPER_ORIGINATOR,
    INDICATION_RELATION,
    INNOVATION_ELIGIBILITY,
    MODALITY,
    OVERSEAS_STAGE_STATUS_DATE,
    REGULATORY_EVENT,
    REGULATORY_EVENT_DATE,
    REGULATORY_EVENT_JURISDICTION,
    SAFETY_SUMMARY_RECORD,
    TARGET_MECHANISM,
    AProjectContract,
    CoreTrialRole,
    MaturityLevel,
    RegionDevelopment,
    RegistryResultsPostedEvidence,
    RegulatoryEventKind,
    RegulatoryEventRecord,
    RequiredFieldKey,
    RequiredFieldSpec,
    SafetyEventUnitId,
    SafetyMeasurementUnit,
    required_fields_for,
)
from ci_workflow.reports.common.evidence_view import EvidenceField, EvidenceFieldState

_CLINICAL_MATURITIES: frozenset[DevelopmentMaturity] = frozenset(
    {
        DevelopmentMaturity.CLINICAL,
        DevelopmentMaturity.SUBMISSION,
        DevelopmentMaturity.APPROVED,
        DevelopmentMaturity.PAUSED_TERMINATED_WITHDRAWN,
    }
)

_SUBMISSION_MATURITIES: frozenset[DevelopmentMaturity] = frozenset(
    {
        DevelopmentMaturity.SUBMISSION,
        DevelopmentMaturity.APPROVED,
        DevelopmentMaturity.PAUSED_TERMINATED_WITHDRAWN,
    }
)

# 携带确定数值的披露状态；未报告/未公开不算数值摘要。
_REPORTED_STATES: frozenset[FactDisclosureState] = frozenset(
    {
        FactDisclosureState.REPORTED_VALUE,
        FactDisclosureState.REPORTED_ZERO,
    }
)

# 安全性最低记录只认封闭的 TEAE/SAE 规则单元；数值单位仍保存在 binding.unit。
_SAFETY_UNIT_IDS: frozenset[str] = frozenset(
    {SafetyEventUnitId.TEAE.value, SafetyEventUnitId.SAE.value}
)
_REGISTRY_RESULTS_POSTED_UNIT_ID = "a_registry_results_posted"
_SAFETY_MEASUREMENT_UNITS: frozenset[str] = frozenset(unit.value for unit in SafetyMeasurementUnit)
_INACTIVE_EVENT_UNITS: dict[str, RegulatoryEventKind] = {
    "a_regulatory_pause": RegulatoryEventKind.PAUSE,
    "a_regulatory_termination": RegulatoryEventKind.TERMINATION,
    "a_regulatory_withdrawal": RegulatoryEventKind.WITHDRAWAL,
    "a_regulatory_abandonment": RegulatoryEventKind.ABANDONMENT,
}

_MISSING_STATE_LABELS_ZH: dict[EvidenceFieldState, str] = {
    EvidenceFieldState.NOT_YET_DISCLOSED: "尚未公开",
    EvidenceFieldState.SOURCE_NOT_LISTED: "穷尽检索后未找到",
    EvidenceFieldState.TECHNICALLY_UNAVAILABLE: "技术暂不可用",
    EvidenceFieldState.USER_CLEARED: "用户清除，待重新核实",
}

# 用户可见成熟度层中文名；阻断说明只使用中文临床/开发语言。
_MATURITY_LABELS_ZH: dict[MaturityLevel, str] = {
    MaturityLevel.ALL_PROJECTS: "处于早期研发阶段",
    MaturityLevel.CLINICAL: "已进入临床开发阶段",
    MaturityLevel.FILING_APPROVAL_TERMINATION: "处于申报、上市或停止开发阶段",
    MaturityLevel.RESULT_BEARING: "已有临床结果公开",
}

# 监管事件地域标签 → 区域；用于区域不适用与同地域事件的矛盾检测。
_REGION_EVENT_LABELS: dict[RequiredFieldKey, str] = {
    CHINA_STAGE_STATUS_DATE: "中国",
    OVERSEAS_STAGE_STATUS_DATE: "境外",
}


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("成熟度判定文本字段不能为空")
    return normalized


class FieldVerdict(StrEnum):
    """逐字段判定：满足、显式不适用、缺失（阻断）。"""

    SATISFIED = "satisfied"
    EXPLICITLY_NOT_APPLICABLE = "explicitly_not_applicable"
    MISSING = "missing"


class FieldOutcome(BaseModel):
    """一个必需字段的判定结果与中文诊断。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: RequiredFieldKey
    label_zh: str
    verdict: FieldVerdict
    reason_zh: str

    @field_validator("label_zh", "reason_zh")
    @classmethod
    def _outcome_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class MaturityGateResult(BaseModel):
    """单个 A 项目的成熟度门槛判定；绑定项目身份，不可变。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    maturity_level: MaturityLevel
    development_maturity: DevelopmentMaturity
    result_bearing: bool
    outcomes: tuple[FieldOutcome, ...]

    @field_validator("project_id")
    @classmethod
    def _project_id_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @property
    def blocked(self) -> bool:
        """存在任一必需字段缺失即整体阻断（失败关闭）。"""
        return any(item.verdict is FieldVerdict.MISSING for item in self.outcomes)

    @property
    def missing_fields(self) -> tuple[FieldOutcome, ...]:
        return tuple(item for item in self.outcomes if item.verdict is FieldVerdict.MISSING)

    @property
    def missing_keys(self) -> frozenset[RequiredFieldKey]:
        return frozenset(item.key for item in self.missing_fields)


class BlockingExplanation(BaseModel):
    """一个被阻断产品的用户可见中文阻断说明。

    公共构造边界拒绝无中文字符的文本；只使用中文临床/开发语言：产品名、
    成熟度层、缺失字段标签与中文诊断；不暴露字段键、判定状态、后端标签
    或工程命名。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    message_zh: str

    @field_validator("project_id", "canonical_name")
    @classmethod
    def _explanation_identity_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("message_zh")
    @classmethod
    def _message_is_native_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not any("\u4e00" <= ch <= "\u9fff" for ch in normalized):
            raise ValueError("中文阻断说明必须包含中文字符")
        lowered = normalized.lower()
        forbidden = (
            "门槛",
            "竞品宇宙",
            "基础层",
            "blocked",
            "missing",
            "result_bearing",
            "snapshot",
            "binding",
        )
        if any(token in lowered for token in forbidden):
            raise ValueError("中文阻断说明不得包含后端、日志或提示词语言")
        return normalized


class UniverseProjectResult(BaseModel):
    """全宇宙中一个项目的整批分析结果；身份与顺序稳定。

    阻断不删除、不降级：项目身份、成熟度层与精确缺失字段全部保留，
    供逐产品说明与后续视图消费。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    gate: MaturityGateResult

    @field_validator("project_id", "canonical_name")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _identity_is_bound_to_gate(self) -> Self:
        if self.project_id != self.gate.project_id:
            raise ValueError("整批分析项目身份必须与门槛判定绑定一致")
        return self

    @property
    def blocked(self) -> bool:
        return self.gate.blocked

    @property
    def maturity_level(self) -> MaturityLevel:
        return self.gate.maturity_level

    @property
    def missing_fields(self) -> tuple[FieldOutcome, ...]:
        return self.gate.missing_fields


class UniverseAnalysisResult(BaseModel):
    """A 报告全宇宙整批分析结果：全部项目保留、身份与顺序稳定。

    失败关闭：任一项目必需证据缺失即整个 A 报告不可生成（``report_ready``
    为假），但每个被阻断产品都保留中文阻断说明，不得删除产品继续。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    projects: tuple[UniverseProjectResult, ...]
    blocking_explanations_zh: tuple[BlockingExplanation, ...]
    report_ready: bool

    @model_validator(mode="after")
    def _explanations_match_blocked_projects(self) -> Self:
        blocked_ids = tuple(item.project_id for item in self.projects if item.blocked)
        explained_ids = tuple(item.project_id for item in self.blocking_explanations_zh)
        if explained_ids != blocked_ids:
            raise ValueError("逐产品中文阻断说明必须与阻断项目一一对应且顺序一致")
        if self.report_ready != (not blocked_ids):
            raise ValueError("任一项目证据未达门槛时 A 报告不可生成，反之才可生成")
        return self

    @property
    def total_projects(self) -> int:
        return len(self.projects)

    @property
    def blocked_projects(self) -> int:
        return len(self.blocking_explanations_zh)

    @property
    def pass_count(self) -> int:
        return self.total_projects - self.blocked_projects

    @property
    def blocked_project_ids(self) -> tuple[str, ...]:
        return tuple(item.project_id for item in self.projects if item.blocked)


def determine_maturity_level(
    maturity: DevelopmentMaturity,
    result_bearing: bool,
) -> MaturityLevel:
    """从已接受判定推导成熟度分层；不接受调用方手工降级。

    开发成熟度进入临床即达临床层，进入申报/批准/终止即达申报层，
    结果承载判定为真即达结果层；分层单调递增。
    """
    level = MaturityLevel.ALL_PROJECTS
    if maturity in _CLINICAL_MATURITIES:
        level = MaturityLevel.CLINICAL
    if maturity in _SUBMISSION_MATURITIES:
        level = MaturityLevel.FILING_APPROVAL_TERMINATION
    if result_bearing:
        level = MaturityLevel.RESULT_BEARING
    return level


def _field_present(field: EvidenceField) -> bool:
    return field.value is not None


def _field_explicit_na(field: EvidenceField) -> bool:
    return field.state is EvidenceFieldState.NOT_APPLICABLE


def _outcome(key: RequiredFieldKey, verdict: FieldVerdict, reason_zh: str) -> FieldOutcome:
    spec: RequiredFieldSpec = _SPEC_BY_KEY[key]
    return FieldOutcome(
        key=key,
        label_zh=spec.label_zh,
        verdict=verdict,
        reason_zh=reason_zh,
    )


def _satisfied(key: RequiredFieldKey, reason_zh: str) -> FieldOutcome:
    return _outcome(key, FieldVerdict.SATISFIED, reason_zh)


def _missing(key: RequiredFieldKey, reason_zh: str) -> FieldOutcome:
    return _outcome(key, FieldVerdict.MISSING, reason_zh)


def _missing_state_reason(label_zh: str, field: EvidenceField) -> str:
    state_label = _MISSING_STATE_LABELS_ZH[field.state] if field.state is not None else "状态未明确"
    return f"必需字段{label_zh}：{state_label}，无法构成完整证据"


def _scalar_field_outcome(
    project: AProjectContract,
    key: RequiredFieldKey,
    field: EvidenceField,
    *,
    allows_not_applicable: bool,
    na_reason_zh: str,
) -> FieldOutcome:
    if _field_present(field):
        return _satisfied(key, f"{_SPEC_BY_KEY[key].label_zh}已获取可核验信息")
    if _field_explicit_na(field) and allows_not_applicable:
        return _outcome(key, FieldVerdict.EXPLICITLY_NOT_APPLICABLE, na_reason_zh)
    if _field_explicit_na(field):
        return _missing(
            key,
            f"{_SPEC_BY_KEY[key].label_zh}为 A 类必需字段，不允许声明不适用",
        )
    return _missing(key, _missing_state_reason(_SPEC_BY_KEY[key].label_zh, field))


def _developer_originator_outcome(
    project: AProjectContract,
    maturity: DevelopmentMaturity,
) -> FieldOutcome:
    developer, originator = project.developer, project.originator
    if _field_present(developer) and _field_present(originator):
        return _satisfied(DEVELOPER_ORIGINATOR, "当前开发者与原研方均已获取可核验信息")
    if _field_explicit_na(developer) and _field_explicit_na(originator):
        if maturity is DevelopmentMaturity.PAUSED_TERMINATED_WITHDRAWN:
            return _outcome(
                DEVELOPER_ORIGINATOR,
                FieldVerdict.EXPLICITLY_NOT_APPLICABLE,
                "暂停/终止/撤回项目已显式声明当前开发者与原研方不适用",
            )
        return _missing(
            DEVELOPER_ORIGINATOR,
            "当前开发者/原研方不适用仅限暂停/终止/撤回项目，其余项目必须提供",
        )
    na_parts = [
        part
        for part, field in (("当前开发者", developer), ("原研方", originator))
        if _field_explicit_na(field)
    ]
    if na_parts:
        return _missing(
            DEVELOPER_ORIGINATOR,
            f"当前开发者/原研方不适用必须整组声明，且仅限暂停/终止/撤回项目；"
            f"{'、'.join(na_parts)}不得单独声明不适用",
        )
    missing_parts = [
        part
        for part, field in (("当前开发者", developer), ("原研方", originator))
        if not (_field_present(field) or _field_explicit_na(field))
    ]
    return _missing(
        DEVELOPER_ORIGINATOR,
        f"必需字段当前开发者/原研方：{'、'.join(missing_parts)}未获得可核验信息",
    )


def _same_region_event_exists(
    events: Sequence[RegulatoryEventRecord],
    region_label: str,
) -> bool:
    return any(
        event.jurisdiction.value is not None and region_label in event.jurisdiction.value
        for event in events
    )


def _region_outcome(
    project: AProjectContract,
    key: RequiredFieldKey,
    region: RegionDevelopment,
    events: Sequence[RegulatoryEventRecord],
) -> FieldOutcome:
    slots = (
        (region.highest_stage, "最高阶段"),
        (region.highest_status, "状态"),
        (region.date, "日期"),
    )
    fields = tuple(slot[0] for slot in slots)
    if all(_field_present(field) for field in fields):
        return _satisfied(key, f"{_SPEC_BY_KEY[key].label_zh}均已获取可核验信息")
    if all(_field_explicit_na(field) for field in fields):
        region_label = _REGION_EVENT_LABELS[key]
        if _same_region_event_exists(events, region_label):
            return _missing(
                key,
                f"该区域已整组声明不适用，但存在同地域（{region_label}）监管事件，证据矛盾",
            )
        return _outcome(
            key,
            FieldVerdict.EXPLICITLY_NOT_APPLICABLE,
            "已显式声明该区域开发不适用",
        )
    missing_parts = [
        label for field, label in slots if not (_field_present(field) or _field_explicit_na(field))
    ]
    if missing_parts:
        return _missing(
            key,
            f"必需字段{_SPEC_BY_KEY[key].label_zh}：{'、'.join(missing_parts)}未获得可核验信息",
        )
    return _missing(
        key,
        f"必需字段{_SPEC_BY_KEY[key].label_zh}必须齐备或整组显式声明不适用",
    )


def _trial_product_map(snapshot: ApplicableUniverseSnapshot) -> dict[str, str]:
    return {
        edge.child_id: edge.parent_id
        for edge in snapshot.relationship_edges
        if edge.parent_type is GateObjectType.PRODUCT and edge.child_type is GateObjectType.TRIAL
    }


def _product_bindings(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> tuple[GateEvidenceBinding, ...]:
    """该产品的证据绑定：产品级事实（含试验归属）或本产品试验级事实。

    result-bearing 按产品判定，不跨产品拼接；其他产品的数值事实不得抬高
    本产品的成熟度分层。
    """
    trial_ids = {
        trial
        for trial, product in _trial_product_map(snapshot).items()
        if product == project.project_id
    }
    return tuple(
        binding
        for binding in bindings
        if binding.object_id == project.project_id
        or binding.object_id in trial_ids
        or binding.trial_id in trial_ids
    )


def _assert_core_trials_in_scope(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
) -> None:
    trial_product = _trial_product_map(snapshot)
    for record in project.core_trials:
        if record.trial_id not in snapshot.trial_ids:
            raise GateEvaluationError("核心试验引用未知试验对象，必须失败关闭")
        if trial_product.get(record.trial_id) != project.project_id:
            raise GateEvaluationError("核心试验引用其他产品的试验，必须失败关闭")


def _validate_inactive_maturity_evidence(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> None:
    """停止开发状态只能由快照声明的谓词和相符监管事件推导。"""
    for binding in bindings:
        if (
            binding.object_id != project.project_id
            or binding.source_role is not SourceRole.REGULATORY_MATERIAL
            or binding.disclosure_state is not FactDisclosureState.NOT_APPLICABLE
        ):
            continue
        predicate = binding.applicability_predicate_id
        if predicate not in snapshot.applicable_conditional_predicates:
            raise GateEvaluationError("停止开发状态引用了快照未声明的适用性依据")
        expected_event = _INACTIVE_EVENT_UNITS.get(binding.unit_id)
        if expected_event is None:
            raise GateEvaluationError("停止开发状态必须使用明确的监管事件规则单元")
        if project.regulatory_events and not any(
            event.event_kind is expected_event for event in project.regulatory_events
        ):
            raise GateEvaluationError("停止开发状态与项目监管事件类型不一致")


def _core_trial_outcome(
    project: AProjectContract,
    key: RequiredFieldKey,
    snapshot: ApplicableUniverseSnapshot,
) -> FieldOutcome:
    if project.core_trials:
        _assert_core_trials_in_scope(project, snapshot)
        return _satisfied(key, f"{_SPEC_BY_KEY[key].label_zh}已登记且属于本产品")
    reasons: dict[RequiredFieldKey, str] = {
        CORE_TRIAL_IDENTITY: "临床项目缺少核心试验身份记录",
        CORE_TRIAL_DEVELOPMENT_ROLE: "临床项目核心试验缺少开发角色",
        CORE_TRIAL_STATUS: "临床项目核心试验缺少状态",
    }
    return _missing(key, reasons[key])


def _regulatory_event_outcome(
    project: AProjectContract,
    key: RequiredFieldKey,
) -> FieldOutcome:
    if not project.regulatory_events:
        return _missing(
            key,
            "必需字段申报/批准/撤回/终止/放弃事件：事件缺失，报告无法继续生成",
        )
    if key is REGULATORY_EVENT:
        return _satisfied(key, "申报/批准/撤回/终止/放弃事件已登记")
    complete = [
        event
        for event in project.regulatory_events
        if _field_present(event.jurisdiction) and _field_present(event.event_date)
    ]
    if complete:
        if key is REGULATORY_EVENT_JURISDICTION:
            return _satisfied(key, "监管事件地域已由同一事件提供可核验信息")
        return _satisfied(key, "监管事件日期已由同一事件提供可核验信息")
    if key is REGULATORY_EVENT_JURISDICTION:
        return _missing(
            key,
            "必需字段事件地域：现有监管事件残缺，地域与日期必须由同一条事件同时提供",
        )
    return _missing(
        key,
        "必需字段事件日期：现有监管事件残缺，地域与日期必须由同一条事件同时提供",
    )


def _anchor_evidence_versions(
    project: AProjectContract,
    anchor_trial: str,
    bindings: Sequence[GateEvidenceBinding],
    flag_evidence: Sequence[RegistryResultsPostedEvidence],
) -> set[str]:
    versions: set[str] = set()
    for binding in bindings:
        if binding.review_state is not FactReviewState.ACCEPTED:
            continue
        if binding.trial_id == anchor_trial:
            versions.add(binding.fact_version_id)
    for flag in flag_evidence:
        if flag.project_id == project.project_id and flag.trial_id == anchor_trial:
            versions.add(flag.fact_version_id)
    return versions


def _anchor_trial_outcome(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    flag_evidence: Sequence[RegistryResultsPostedEvidence],
) -> FieldOutcome:
    if not project.anchor_trials:
        return _missing(ANCHOR_TRIAL, "已公开结果的成熟项目缺少适格锚定试验记录")
    core_ids = {record.trial_id for record in project.core_trials}
    trial_product = _trial_product_map(snapshot)
    for anchor in project.anchor_trials:
        if anchor.trial_id not in core_ids:
            raise GateEvaluationError("适格锚定试验必须是本产品核心试验，必须失败关闭")
        if anchor.trial_id not in snapshot.trial_ids:
            raise GateEvaluationError("适格锚定试验引用未知试验对象，必须失败关闭")
        if trial_product.get(anchor.trial_id) != project.project_id:
            raise GateEvaluationError("适格锚定试验引用其他产品的试验，必须失败关闭")
        versions = _anchor_evidence_versions(project, anchor.trial_id, bindings, flag_evidence)
        if not set(anchor.fact_version_ids) <= versions:
            raise GateEvaluationError(
                "适格锚定试验的证据版本无法在已接受绑定或已发布结果证据中找到，必须失败关闭"
            )
    return _satisfied(ANCHOR_TRIAL, "适格锚定试验已登记并绑定已接受证据")


def _trial_design_kind(snapshot: ApplicableUniverseSnapshot, trial_id: str) -> TrialDesignKind:
    for record in snapshot.trial_design_evidence:
        if record.trial_id == trial_id:
            return record.design_kind
    raise GateEvaluationError(f"缺少试验设计证据：{trial_id}")


def _minimum_binding_matches(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    binding: GateEvidenceBinding,
    anchor_ids: frozenset[str],
    *,
    domain: FactDomain,
) -> bool:
    """一条绑定是否构成适格锚定试验的最低疗效/安全性记录。"""
    if binding.trial_id is None or binding.trial_id not in anchor_ids:
        return False
    if binding.review_state is not FactReviewState.ACCEPTED:
        return False
    if binding.observation_kind is not ObservationKind.OBSERVED_RESULT:
        return False
    if binding.disclosure_state not in _REPORTED_STATES:
        return False
    if binding.numeric_value is None:
        return False
    if binding.denominator is None:
        return False
    if binding.source_location is None:
        return False
    if binding.fact_domain is not domain:
        return False
    if binding.source_role not in RESULT_BEARING_SOURCE_ROLES:
        return False
    design = _trial_design_kind(snapshot, binding.trial_id)
    if design is TrialDesignKind.COMPARATIVE and binding.control_group is None:
        return False
    if domain is FactDomain.EFFICACY:
        return all(
            value is not None
            for value in (
                binding.definition,
                binding.direction,
                binding.unit,
                binding.timepoint,
                binding.analysis_population,
                binding.treatment_group,
            )
        )
    return (
        binding.unit_id in _SAFETY_UNIT_IDS
        and binding.unit in _SAFETY_MEASUREMENT_UNITS
        and all(
            value is not None
            for value in (
                binding.event_definition,
                binding.time_window,
                binding.analysis_population,
                binding.treatment_group,
            )
        )
    )


def _core_efficacy_outcome(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> FieldOutcome:
    anchor_ids = frozenset(anchor.trial_id for anchor in project.anchor_trials)
    if not anchor_ids:
        return _missing(CORE_EFFICACY_RECORD, "缺少适格锚定试验，无法判定疗效记录归属")
    if any(
        _minimum_binding_matches(project, snapshot, binding, anchor_ids, domain=FactDomain.EFFICACY)
        for binding in bindings
    ):
        return _satisfied(
            CORE_EFFICACY_RECORD,
            "核心疗效记录来自适格锚定试验且成分完整、携带可核验数值",
        )
    return _missing(
        CORE_EFFICACY_RECORD,
        "核心疗效记录缺失或成分不完整（需原始定义、方向、单位、时间点、分析人群、"
        "治疗组、对照组与分母，且来自适格锚定试验）",
    )


def _safety_summary_outcome(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> FieldOutcome:
    anchor_ids = frozenset(anchor.trial_id for anchor in project.anchor_trials)
    if not anchor_ids:
        return _missing(SAFETY_SUMMARY_RECORD, "缺少适格锚定试验，无法判定安全性记录归属")
    if any(
        _minimum_binding_matches(project, snapshot, binding, anchor_ids, domain=FactDomain.SAFETY)
        for binding in bindings
    ):
        return _satisfied(
            SAFETY_SUMMARY_RECORD,
            "TEAE/SAE 数值摘要来自适格锚定试验且成分完整、携带可核验数值",
        )
    return _missing(
        SAFETY_SUMMARY_RECORD,
        "TEAE/SAE 数值摘要缺失或成分不完整（需事件定义、时间窗、治疗组、对照组与"
        "分母，携带报告值/零，且来自适格锚定试验）",
    )


def _flag_triggers_result_bearing(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    flag_evidence: Sequence[RegistryResultsPostedEvidence],
) -> bool:
    """已发布结果证据触发；必须解析到同一已接受登记事实绑定。"""
    trial_product = _trial_product_map(snapshot)
    for flag in flag_evidence:
        if flag.project_id not in snapshot.product_ids:
            raise GateEvaluationError("已发布结果证据引用未知产品，必须失败关闭")
        if flag.trial_id not in snapshot.trial_ids:
            raise GateEvaluationError("已发布结果证据引用未知试验对象，必须失败关闭")
        if trial_product.get(flag.trial_id) != flag.project_id:
            raise GateEvaluationError("已发布结果证据引用其他产品的试验，必须失败关闭")
        matching = tuple(
            binding
            for binding in bindings
            if binding.fact_version_id == flag.fact_version_id
            and binding.trial_id == flag.trial_id
            and binding.source_role is flag.source_role
            and binding.review_state is flag.review_state
            and binding.source_location == flag.source_location
            and binding.unit_id == _REGISTRY_RESULTS_POSTED_UNIT_ID
            and binding.object_id in (flag.project_id, flag.trial_id)
        )
        if len(matching) != 1:
            raise GateEvaluationError(
                "已发布结果证据必须解析到同一项已接受的官方登记事实，必须失败关闭"
            )
    return any(flag.project_id == project.project_id for flag in flag_evidence)


def _evaluate_key(
    project: AProjectContract,
    key: RequiredFieldKey,
    *,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    flag_evidence: Sequence[RegistryResultsPostedEvidence],
    maturity: DevelopmentMaturity,
) -> FieldOutcome:
    if key is CANONICAL_IDENTITY_AND_ALIASES or key is INNOVATION_ELIGIBILITY:
        return _satisfied(
            key,
            "规范身份、别名与创新本体资格由合同与已接受判定绑定",
        )
    if key is TARGET_MECHANISM:
        return _scalar_field_outcome(
            project,
            key,
            project.target_mechanism,
            allows_not_applicable=False,
            na_reason_zh="",
        )
    if key is MODALITY:
        return _scalar_field_outcome(
            project,
            key,
            project.modality,
            allows_not_applicable=False,
            na_reason_zh="",
        )
    if key is INDICATION_RELATION:
        return _scalar_field_outcome(
            project,
            key,
            project.indication_relation,
            allows_not_applicable=False,
            na_reason_zh="",
        )
    if key is DEVELOPER_ORIGINATOR:
        return _developer_originator_outcome(project, maturity)
    if key is CHINA_STAGE_STATUS_DATE:
        return _region_outcome(project, key, project.china, project.regulatory_events)
    if key is OVERSEAS_STAGE_STATUS_DATE:
        return _region_outcome(project, key, project.overseas, project.regulatory_events)
    if key in (CORE_TRIAL_IDENTITY, CORE_TRIAL_DEVELOPMENT_ROLE, CORE_TRIAL_STATUS):
        return _core_trial_outcome(project, key, snapshot)
    if key in (REGULATORY_EVENT, REGULATORY_EVENT_JURISDICTION, REGULATORY_EVENT_DATE):
        return _regulatory_event_outcome(project, key)
    if key is ANCHOR_TRIAL:
        return _anchor_trial_outcome(project, snapshot, bindings, flag_evidence)
    if key is CORE_EFFICACY_RECORD:
        return _core_efficacy_outcome(project, snapshot, bindings)
    if key is SAFETY_SUMMARY_RECORD:
        return _safety_summary_outcome(project, snapshot, bindings)
    raise AssertionError(f"未实现必需字段判定：{key.value}")


def evaluate_maturity_gate(
    project: AProjectContract,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> MaturityGateResult:
    """对单个 A 项目执行成熟度门槛判定；纯函数，绑定项目身份。

    成熟度与 result-bearing 从当前不可变快照与已接受绑定推导；证据作用域
    由 ``assert_bindings_in_universe`` 闭合，未知/跨产品引用失败关闭。
    """
    assert_applicable_universe_closed(snapshot)
    assert_bindings_in_universe(snapshot, bindings)
    if project.project_id not in snapshot.product_ids:
        raise GateEvaluationError("单项目评估对象不属于当前竞品清单，必须失败关闭")
    product_bindings = _product_bindings(project, snapshot, bindings)
    _validate_inactive_maturity_evidence(project, snapshot, product_bindings)
    maturity = derive_product_maturity(project.project_id, product_bindings)
    numeric_trigger = derive_result_bearing(snapshot, product_bindings)
    flag_trigger = _flag_triggers_result_bearing(
        project, snapshot, bindings, results_posted_evidence
    )
    _assert_core_trials_in_scope(project, snapshot)
    if project.anchor_trials:
        _anchor_trial_outcome(project, snapshot, bindings, results_posted_evidence)
    result_bearing = numeric_trigger or flag_trigger
    level = determine_maturity_level(maturity, result_bearing)
    outcomes = tuple(
        _evaluate_key(
            project,
            key,
            snapshot=snapshot,
            bindings=bindings,
            flag_evidence=results_posted_evidence,
            maturity=maturity,
        )
        for key in required_fields_for(level)
    )
    return MaturityGateResult(
        project_id=project.project_id,
        maturity_level=level,
        development_maturity=maturity,
        result_bearing=result_bearing,
        outcomes=outcomes,
    )


def _blocking_message_zh(project: AProjectContract, gate: MaturityGateResult) -> str:
    """生成一个被阻断产品的用户可见中文阻断说明。

    只使用中文临床/开发语言：产品名、成熟度层中文名、缺失字段中文标签
    与中文诊断；不暴露字段键、判定状态、后端标签或工程命名。
    """
    details = "；".join(
        f"{index}.{outcome.label_zh}：{outcome.reason_zh}"
        for index, outcome in enumerate(gate.missing_fields, start=1)
    )
    return (
        f"产品「{project.canonical_name}」{_MATURITY_LABELS_ZH[gate.maturity_level]}，"
        f"生成报告所需的关键证据尚不完整：{details}。报告暂无法生成；"
        "补齐上述信息后可继续生成。"
    )


def analyze_universe(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> UniverseAnalysisResult:
    """整批分析：全宇宙保留、逐项目门槛判定、逐产品中文阻断说明。

    纯函数，无 Top-N、无删除、无降级参数：
    - 项目 ID 与 snapshot.product_ids 精确一一对应：重复项目、缺失/多余
      项目、空项目集均失败关闭；空宇宙由快照合同本身拒绝；
    - 全部传入项目按原顺序进入结果，身份与顺序稳定，不按成熟度、结果好坏、
      字段缺口或固定数量截断；
    - 任一项目必需证据缺失即整个 A 报告不可生成（失败关闭）；
    - 每个被阻断产品保留独立中文阻断说明，不得删除该产品继续生成。
    """
    assert_applicable_universe_closed(snapshot)
    project_ids = [project.project_id for project in projects]
    if len(project_ids) != len(set(project_ids)):
        raise GateEvaluationError("项目清单不得包含重复项目，必须失败关闭")
    if len(project_ids) != len(snapshot.product_ids) or set(project_ids) != set(
        snapshot.product_ids
    ):
        raise GateEvaluationError("项目集必须与宇宙快照产品清单精确一一对应，必须失败关闭")
    universe_results: list[UniverseProjectResult] = []
    explanations: list[BlockingExplanation] = []
    for project in projects:
        gate = evaluate_maturity_gate(project, snapshot, bindings, results_posted_evidence)
        universe_results.append(
            UniverseProjectResult(
                project_id=project.project_id,
                canonical_name=project.canonical_name,
                gate=gate,
            )
        )
        if gate.blocked:
            explanations.append(
                BlockingExplanation(
                    project_id=project.project_id,
                    canonical_name=project.canonical_name,
                    message_zh=_blocking_message_zh(project, gate),
                )
            )
    return UniverseAnalysisResult(
        projects=tuple(universe_results),
        blocking_explanations_zh=tuple(explanations),
        report_ready=not explanations,
    )


# ── Task 5.3：疗效、安全性热图与疗效—安全性气泡矩阵 ───────────────────────


class ArmRole(StrEnum):
    """试验组别在比较中的角色。"""

    TREATMENT = "treatment"
    CONTROL = "control"


class EndpointDirection(StrEnum):
    """疗效指标方向；只用于坐标方向校正，不生成综合分数。"""

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class SafetyFamily(StrEnum):
    """安全性热图的临床维度。"""

    TEAE = "teae"
    SAE = "sae"
    AESI = "aesi"
    COMMON_AE = "common_ae"


class ProductResultState(StrEnum):
    """产品在本次快照中的结果公开状态。"""

    HAS_PUBLIC_RESULTS = "has_public_results"
    NO_PUBLIC_RESULTS = "no_public_results"


class TrialSelectionRecord(BaseModel):
    """锚定试验选择所需的非结果属性；证据版本绑定快照设计证据。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    trial_id: str
    phase_label_zh: str
    phase_rank: int = Field(ge=0, le=4)
    evidence_version_id: str
    phase_fact_version_id: str

    @field_validator(
        "project_id",
        "trial_id",
        "phase_label_zh",
        "evidence_version_id",
        "phase_fact_version_id",
    )
    @classmethod
    def _selection_text(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _phase_label_matches_rank(self) -> Self:
        expected = {0: "早期临床", 1: "I期", 2: "II期", 3: "III期", 4: "IV期"}
        if self.phase_label_zh != expected[self.phase_rank]:
            raise ValueError("试验阶段中文标签与阶段序位不一致")
        return self


class EndpointFamilySpec(BaseModel):
    """可横向匹配的疗效指标族。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    family_id: str
    label_zh: str
    direction: EndpointDirection
    compatibility_rule_id: str
    compatible_endpoint_ids: tuple[str, ...] = Field(min_length=1)
    compatible_units: tuple[str, ...] = Field(min_length=1)
    compatible_timepoints: tuple[str, ...] = Field(min_length=1)
    compatible_analysis_populations: tuple[str, ...] = Field(min_length=1)
    definition_required_terms: tuple[str, ...] = Field(min_length=1)
    compatible_direction_texts: tuple[str, ...] = Field(min_length=1)

    @field_validator("family_id", "label_zh", "compatibility_rule_id")
    @classmethod
    def _endpoint_text(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "compatible_endpoint_ids",
        "compatible_units",
        "compatible_timepoints",
        "compatible_analysis_populations",
        "definition_required_terms",
        "compatible_direction_texts",
    )
    @classmethod
    def _units_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("疗效指标族的兼容规则条目不得重复")
        return normalized

    @model_validator(mode="after")
    def _direction_text_matches_direction(self) -> Self:
        allowed = {
            EndpointDirection.HIGHER_IS_BETTER: {
                "应答率越高越好",
                "数值越高越好",
                "增加越多越好",
            },
            EndpointDirection.LOWER_IS_BETTER: {
                "发生率越低越好",
                "数值越低越好",
                "减少越多越好",
            },
        }
        for text in self.compatible_direction_texts:
            if text not in allowed[self.direction]:
                raise ValueError("疗效方向文本必须来自与方向一致的封闭白名单")
        return self


class TrialGroupRoleRecord(BaseModel):
    """当前试验设计证据中的强类型组别角色。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    trial_id: str
    comparison_id: str | None
    group_id: str
    group_label_zh: str
    arm_role: ArmRole
    evidence_fact_version_id: str

    @field_validator(
        "project_id",
        "trial_id",
        "group_id",
        "group_label_zh",
        "evidence_fact_version_id",
    )
    @classmethod
    def _group_role_text(cls, value: str) -> str:
        return _text(value)


class EfficacyMeasureRecord(BaseModel):
    """一条疗效事实到指标族和组别角色的显式映射。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    fact_version_id: str
    endpoint_family_id: str
    arm_role: ArmRole

    @field_validator("fact_version_id", "endpoint_family_id")
    @classmethod
    def _efficacy_record_text(cls, value: str) -> str:
        return _text(value)


class SafetyMeasureRecord(BaseModel):
    """一条安全性事实到热图维度和组别角色的显式映射。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    fact_version_id: str
    family: SafetyFamily
    term_id: str
    arm_role: ArmRole
    matrix_default: bool = False

    @field_validator("fact_version_id", "term_id")
    @classmethod
    def _safety_record_text(cls, value: str) -> str:
        return _text(value)


class AAnalysisIdentity(BaseModel):
    """A 类汇总绑定的项目、快照与研究角色身份。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    universe_project_id: str
    evidence_snapshot_id: str
    research_role_set_id: str
    universe_summary: str
    indication_rule_set_id: str


class TargetProductGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    target_mechanism_zh: str
    product_ids: tuple[str, ...] = Field(min_length=1)


class AnchorTrialSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    trial_id: str
    phase_label_zh: str
    phase_rank: int
    development_role: CoreTrialRole
    disclosure_maturity_rank: int


class ProductResultSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    canonical_name: str
    state: ProductResultState


class EfficacyPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    trial_id: str
    endpoint_id: str
    endpoint_family_id: str
    endpoint_label_zh: str
    definition_zh: str
    direction_zh: str
    arm_role: ArmRole
    group_id: str | None
    group_label_zh: str
    raw_value: float | int | None
    direction_corrected_value: float | int | None
    unit: str | None
    denominator: int | None
    timepoint_zh: str | None
    analysis_population_zh: str | None
    disclosure_state: FactDisclosureState
    fact_version_id: str
    source_location: str | None


class SafetyHeatmapCell(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    trial_id: str
    family: SafetyFamily
    term_id: str
    arm_role: ArmRole
    group_id: str | None
    group_label_zh: str
    raw_value: float | int | None
    unit: str | None
    denominator: int | None
    event_definition_zh: str | None
    time_window_zh: str | None
    analysis_population_zh: str | None
    disclosure_state: FactDisclosureState
    matrix_default: bool
    comparison_rate_percent: float | None = Field(default=None, ge=0, le=100)
    relative_intensity: float | None = Field(default=None, ge=0, le=1)
    fact_version_id: str
    source_location: str | None


def _canonical_analysis_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonical_analysis_value(value.model_dump(mode="json"))
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_canonical_analysis_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical_analysis_value(item) for key, item in sorted(value.items())}
    return value


def _analysis_digest(fields: Mapping[str, object]) -> str:
    canonical = json.dumps(
        _canonical_analysis_value(dict(fields)),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AEfficacySafetySummaryView(BaseModel):
    """A 类首页及细节页共享的完整疗效与安全性数据视图。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    identity: AAnalysisIdentity
    product_ids: tuple[str, ...] = Field(min_length=1)
    target_groups: tuple[TargetProductGroup, ...] = Field(min_length=1)
    product_results: tuple[ProductResultSummary, ...] = Field(min_length=1)
    anchors: tuple[AnchorTrialSummary, ...]
    endpoint_families: tuple[EndpointFamilySpec, ...] = Field(min_length=1)
    default_endpoint_family_id: str
    efficacy_points: tuple[EfficacyPoint, ...]
    safety_cells: tuple[SafetyHeatmapCell, ...]
    content_digest: str

    @model_validator(mode="after")
    def _summary_digest_matches(self) -> Self:
        fields = self.model_dump(mode="json", exclude={"content_digest"})
        if self.content_digest != _analysis_digest(fields):
            raise ValueError("疗效安全性汇总内容摘要与当前内容不一致")
        return self


class BubblePoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    trial_id: str
    group_id: str
    group_label_zh: str
    endpoint_family_id: str
    efficacy_fact_version_id: str
    safety_family: SafetyFamily
    safety_term_id: str
    safety_event_definition_zh: str
    safety_time_window_zh: str
    safety_analysis_population_zh: str
    safety_fact_version_id: str
    arm_role: ArmRole
    efficacy_position: float
    raw_efficacy_value: float
    raw_safety_rate: float
    safety_position: float
    sample_size: int = Field(gt=0)
    radius: float = Field(gt=0)


class UnplottableBubbleProduct(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    group_id: str | None = None
    group_label_zh: str | None = None
    reason_zh: str


class ABubbleMatrixView(BaseModel):
    """无综合分数、无默认名次的疗效—安全性气泡矩阵。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_summary_digest: str
    endpoint_family_id: str
    safety_family: SafetyFamily
    safety_term_id: str | None
    safety_event_definition_zh: str | None
    safety_time_window_zh: str | None
    safety_analysis_population_zh: str | None
    radius_scale: float = Field(gt=0)
    y_axis_note_zh: str
    points: tuple[BubblePoint, ...]
    unplottable_products: tuple[UnplottableBubbleProduct, ...]
    content_digest: str

    @model_validator(mode="after")
    def _bubble_digest_matches(self) -> Self:
        fields = self.model_dump(mode="json", exclude={"content_digest"})
        if self.content_digest != _analysis_digest(fields):
            raise ValueError("气泡矩阵内容摘要与当前内容不一致")
        return self


_ROLE_RANK: dict[CoreTrialRole, int] = {
    CoreTrialRole.REGISTRATION_OR_PIVOTAL: 3,
    CoreTrialRole.EARLY_DECISION: 2,
    CoreTrialRole.SUPPORTING: 1,
}
_ARM_ORDER: dict[ArmRole, int] = {ArmRole.TREATMENT: 0, ArmRole.CONTROL: 1}


def _trial_product_map_for_summary(snapshot: ApplicableUniverseSnapshot) -> dict[str, str]:
    return {
        edge.child_id: edge.parent_id
        for edge in snapshot.relationship_edges
        if edge.parent_type is GateObjectType.PRODUCT and edge.child_type is GateObjectType.TRIAL
    }


def _reported(binding: GateEvidenceBinding) -> bool:
    return binding.disclosure_state in _REPORTED_STATES and binding.numeric_value is not None


def _assert_result_source(binding: GateEvidenceBinding) -> None:
    if (
        binding.review_state is not FactReviewState.ACCEPTED
        or binding.observation_kind is not ObservationKind.OBSERVED_RESULT
        or binding.source_role not in RESULT_BEARING_SOURCE_ROLES
    ):
        raise GateEvaluationError("疗效或安全性结果必须来自已接受的观察性结果来源")


def _assert_numeric_measure_valid(binding: GateEvidenceBinding) -> None:
    if binding.disclosure_state in _REPORTED_STATES and binding.numeric_value is None:
        raise GateEvaluationError("已报告疗效或安全性结果必须保留明确数值")
    if binding.disclosure_state not in _REPORTED_STATES and binding.numeric_value is not None:
        raise GateEvaluationError("未报告或未公开状态不得携带结果数值")
    if not _reported(binding):
        return
    if binding.denominator is None:
        raise GateEvaluationError("已报告疗效或安全性数值必须保留正分母")
    value = binding.numeric_value
    assert value is not None
    if binding.unit is not None and binding.unit.endswith("%") and not 0 <= value <= 100:
        raise GateEvaluationError("百分比结果必须位于0至100之间")
    if binding.unit == SafetyMeasurementUnit.PARTICIPANT_COUNT.value:
        if not isinstance(value, int) or isinstance(value, bool):
            raise GateEvaluationError("受试者人数必须是整数")
        if value < 0 or value > binding.denominator:
            raise GateEvaluationError("受试者人数必须位于0与分母之间")
    if binding.unit == SafetyMeasurementUnit.EVENT_COUNT.value and (
        not isinstance(value, int) or isinstance(value, bool) or value < 0
    ):
        raise GateEvaluationError("事件数必须是大于或等于零的整数")
    if binding.unit == SafetyMeasurementUnit.EXPOSURE_ADJUSTED_RATE.value and value < 0:
        raise GateEvaluationError("暴露校正发生率不得为负数")


def _assert_safety_family_matches_binding(
    record: SafetyMeasureRecord,
    binding: GateEvidenceBinding,
) -> None:
    """TEAE/SAE 双向绑定固定规则单元，其他事件族不得冒用二者。"""
    expected = {
        SafetyFamily.TEAE: SafetyEventUnitId.TEAE.value,
        SafetyFamily.SAE: SafetyEventUnitId.SAE.value,
    }
    if record.family in expected and binding.unit_id != expected[record.family]:
        raise GateEvaluationError("安全性事件类别与事实规则单元不一致")
    if record.family not in expected and binding.unit_id in set(expected.values()):
        raise GateEvaluationError("TEAE或SAE事实不得映射为其他安全性事件类别")
    if record.matrix_default and record.family is not SafetyFamily.TEAE:
        raise GateEvaluationError("疗效安全矩阵的默认安全性记录只能是总体治疗期间不良事件")


def _current_measure_bindings(
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> dict[str, GateEvidenceBinding]:
    try:
        validated_bindings = [
            GateEvidenceBinding.model_validate(binding.model_dump(mode="python"))
            for binding in bindings
        ]
    except ValueError as error:
        raise GateEvaluationError("证据绑定内容无效，拒绝旁路篡改") from error
    assert_bindings_in_universe(snapshot, validated_bindings)
    by_fact: dict[str, GateEvidenceBinding] = {}
    for binding in validated_bindings:
        if binding.review_state is not FactReviewState.ACCEPTED:
            continue
        if binding.fact_version_id in by_fact:
            raise GateEvaluationError("同一事实版本存在重复已接受绑定，必须失败关闭")
        by_fact[binding.fact_version_id] = binding
    return by_fact


def _validated_group_roles(
    snapshot: ApplicableUniverseSnapshot,
    bindings: Mapping[str, GateEvidenceBinding],
    records: Sequence[TrialGroupRoleRecord],
) -> dict[str, TrialGroupRoleRecord]:
    trial_product = _trial_product_map_for_summary(snapshot)
    roles: dict[str, TrialGroupRoleRecord] = {}
    expected_definition = {
        ArmRole.TREATMENT: "治疗组",
        ArmRole.CONTROL: "对照组",
    }
    for record in records:
        if record.group_id in roles:
            raise GateEvaluationError("同一试验组只能有一条权威组别角色记录")
        fact = bindings.get(record.evidence_fact_version_id)
        if (
            fact is None
            or fact.fact_domain is not FactDomain.TRIAL_DESIGN
            or fact.review_state is not FactReviewState.ACCEPTED
            or fact.trial_id != record.trial_id
            or fact.comparison_id != record.comparison_id
            or fact.group_id != record.group_id
            or fact.object_id != record.group_id
            or fact.definition != expected_definition[record.arm_role]
            or fact.treatment_group != record.group_label_zh
            or trial_product.get(record.trial_id) != record.project_id
        ):
            raise GateEvaluationError("组别角色必须绑定当前快照中相符的已接受设计事实")
        roles[record.group_id] = record
    if set(roles) != set(snapshot.group_ids):
        raise GateEvaluationError("组别角色记录必须完整覆盖当前快照的全部试验组")
    designs = {item.trial_id: item.design_kind for item in snapshot.trial_design_evidence}
    for trial_id in snapshot.trial_ids:
        trial_roles = [record for record in records if record.trial_id == trial_id]
        if designs[trial_id] is TrialDesignKind.SINGLE_ARM:
            if trial_roles and (
                len(trial_roles) != 1 or trial_roles[0].arm_role is not ArmRole.TREATMENT
            ):
                raise GateEvaluationError("单臂试验必须且只能有一个治疗组")
        elif trial_roles:
            role_set = {record.arm_role for record in trial_roles}
            if not {ArmRole.TREATMENT, ArmRole.CONTROL} <= role_set:
                raise GateEvaluationError("比较试验必须同时包含治疗组和对照组")
    return roles


def _validate_measure_coverage(
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    efficacy_records: Sequence[EfficacyMeasureRecord],
    safety_records: Sequence[SafetyMeasureRecord],
) -> None:
    mapped = [record.fact_version_id for record in efficacy_records]
    mapped.extend(record.fact_version_id for record in safety_records)
    if len(mapped) != len(set(mapped)):
        raise GateEvaluationError("疗效或安全性事实映射重复，必须失败关闭")
    applicable = {
        binding.fact_version_id
        for binding in bindings
        if binding.review_state is FactReviewState.ACCEPTED
        and binding.observation_kind is ObservationKind.OBSERVED_RESULT
        and binding.fact_domain in {FactDomain.EFFICACY, FactDomain.SAFETY}
        and not (
            binding.source_role is SourceRole.REGULATORY_MATERIAL
            and binding.object_id in snapshot.product_ids
            and binding.group_id is None
            and binding.endpoint_id is None
        )
    }
    if set(mapped) != applicable:
        raise GateEvaluationError("疗效与安全性事实映射必须完整覆盖本次快照，不得选择性遗漏")


def _select_anchors(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    records: Sequence[TrialSelectionRecord],
    eligible_trial_ids: frozenset[str],
) -> tuple[AnchorTrialSummary, ...]:
    selection_by_trial: dict[str, TrialSelectionRecord] = {}
    design_versions = {
        item.trial_id: item.evidence_version_id for item in snapshot.trial_design_evidence
    }
    binding_by_fact = {binding.fact_version_id: binding for binding in bindings}
    for record in records:
        if record.trial_id in selection_by_trial:
            raise GateEvaluationError("同一试验的锚定选择属性不得重复")
        if design_versions.get(record.trial_id) != record.evidence_version_id:
            raise GateEvaluationError("锚定选择属性必须绑定本次快照的试验设计证据版本")
        phase_fact = binding_by_fact.get(record.phase_fact_version_id)
        if (
            phase_fact is None
            or phase_fact.fact_domain is not FactDomain.TRIAL_DESIGN
            or phase_fact.review_state is not FactReviewState.ACCEPTED
            or phase_fact.trial_id != record.trial_id
            or phase_fact.numeric_value != record.phase_rank
            or phase_fact.definition != record.phase_label_zh
        ):
            raise GateEvaluationError("试验阶段必须绑定当前已接受的强类型阶段事实")
        selection_by_trial[record.trial_id] = record
    anchors: list[AnchorTrialSummary] = []
    for project in projects:
        if not project.anchor_trials:
            continue
        core_by_trial = {record.trial_id: record for record in project.core_trials}
        candidates: list[tuple[tuple[int, int, int, str], AnchorTrialSummary]] = []
        for anchor in project.anchor_trials:
            if anchor.trial_id not in eligible_trial_ids:
                continue
            selection = selection_by_trial.get(anchor.trial_id)
            core = core_by_trial.get(anchor.trial_id)
            if selection is None or core is None or selection.project_id != project.project_id:
                raise GateEvaluationError("适格锚定试验缺少与项目一致的阶段选择属性")
            if core.role is CoreTrialRole.SUPPORTING:
                continue
            maturity_rank = max(
                (
                    disclosure_maturity_rank(binding.disclosure_maturity)
                    for binding in bindings
                    if binding.trial_id == anchor.trial_id
                    and binding.review_state is FactReviewState.ACCEPTED
                    and binding.observation_kind is ObservationKind.OBSERVED_RESULT
                    and binding.fact_domain in {FactDomain.EFFICACY, FactDomain.SAFETY}
                ),
                default=0,
            )
            item = AnchorTrialSummary(
                project_id=project.project_id,
                trial_id=anchor.trial_id,
                phase_label_zh=selection.phase_label_zh,
                phase_rank=selection.phase_rank,
                development_role=core.role,
                disclosure_maturity_rank=maturity_rank,
            )
            key = (-_ROLE_RANK[core.role], -selection.phase_rank, -maturity_rank, anchor.trial_id)
            candidates.append((key, item))
        if not candidates:
            raise GateEvaluationError("本产品没有同时满足关键疗效与安全性结果要求的锚定试验")
        anchors.append(min(candidates, key=lambda pair: pair[0])[1])
    return tuple(anchors)


def _eligible_anchor_trials(
    efficacy_points: Sequence[EfficacyPoint],
    safety_cells: Sequence[SafetyHeatmapCell],
    snapshot: ApplicableUniverseSnapshot,
) -> frozenset[str]:
    """逐试验确认关键疗效与 TEAE/SAE 均可解释，不跨锚定候选拼接。"""
    design = {item.trial_id: item.design_kind for item in snapshot.trial_design_evidence}
    eligible: set[str] = set()
    for trial_id in snapshot.trial_ids:
        efficacy_roles = {
            point.arm_role
            for point in efficacy_points
            if point.trial_id == trial_id
            and point.raw_value is not None
            and point.denominator is not None
        }
        safety_roles = {
            cell.arm_role
            for cell in safety_cells
            if cell.trial_id == trial_id
            and cell.family in {SafetyFamily.TEAE, SafetyFamily.SAE}
            and cell.raw_value is not None
            and cell.denominator is not None
        }
        required_roles = {ArmRole.TREATMENT}
        if design[trial_id] is TrialDesignKind.COMPARATIVE:
            required_roles.add(ArmRole.CONTROL)
        if required_roles <= efficacy_roles and required_roles <= safety_roles:
            eligible.add(trial_id)
    return frozenset(eligible)


def _target_groups(projects: Sequence[AProjectContract]) -> tuple[TargetProductGroup, ...]:
    grouped: dict[str, list[str]] = {}
    for project in projects:
        if project.target_mechanism.value is None:
            raise GateEvaluationError("产品缺少靶点/机制，无法生成按靶点分组的汇总")
        grouped.setdefault(project.target_mechanism.value, []).append(project.project_id)
    return tuple(
        TargetProductGroup(target_mechanism_zh=target, product_ids=tuple(sorted(ids)))
        for target, ids in sorted(grouped.items())
    )


def _default_endpoint(
    families: Sequence[EndpointFamilySpec],
    points: Sequence[EfficacyPoint],
    snapshot: ApplicableUniverseSnapshot,
) -> str:
    design = {item.trial_id: item.design_kind for item in snapshot.trial_design_evidence}
    counts: dict[str, tuple[int, int]] = {}
    for family in families:
        family_points = [
            point
            for point in points
            if point.endpoint_family_id == family.family_id and point.raw_value is not None
        ]
        products = {
            point.project_id for point in family_points if point.arm_role is ArmRole.TREATMENT
        }
        complete_pairs = 0
        for project_id, trial_id in {(point.project_id, point.trial_id) for point in family_points}:
            roles = {
                point.arm_role
                for point in family_points
                if point.project_id == project_id and point.trial_id == trial_id
            }
            if ArmRole.TREATMENT in roles and (
                design[trial_id] is TrialDesignKind.SINGLE_ARM or ArmRole.CONTROL in roles
            ):
                complete_pairs += 1
        counts[family.family_id] = (len(products), complete_pairs)
    return min(
        families,
        key=lambda family: (
            -counts[family.family_id][0],
            -counts[family.family_id][1],
            family.family_id,
        ),
    ).family_id


def build_efficacy_safety_summary(
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    trial_selection: Sequence[TrialSelectionRecord],
    group_roles: Sequence[TrialGroupRoleRecord],
    endpoint_families: Sequence[EndpointFamilySpec],
    efficacy_records: Sequence[EfficacyMeasureRecord],
    safety_records: Sequence[SafetyMeasureRecord],
) -> AEfficacySafetySummaryView:
    """构建完整疗效比较与安全性热图数据；关键证据不足时不生成草稿。"""
    try:
        projects = tuple(
            AProjectContract.model_validate(project.model_dump(mode="python"))
            for project in projects
        )
        snapshot = ApplicableUniverseSnapshot.model_validate(snapshot.model_dump(mode="python"))
        bindings = tuple(
            GateEvidenceBinding.model_validate(binding.model_dump(mode="python"))
            for binding in bindings
        )
        trial_selection = tuple(
            TrialSelectionRecord.model_validate(record.model_dump(mode="python"))
            for record in trial_selection
        )
        group_roles = tuple(
            TrialGroupRoleRecord.model_validate(record.model_dump(mode="python"))
            for record in group_roles
        )
        endpoint_families = tuple(
            EndpointFamilySpec.model_validate(family.model_dump(mode="python"))
            for family in endpoint_families
        )
        efficacy_records = tuple(
            EfficacyMeasureRecord.model_validate(record.model_dump(mode="python"))
            for record in efficacy_records
        )
        safety_records = tuple(
            SafetyMeasureRecord.model_validate(record.model_dump(mode="python"))
            for record in safety_records
        )
    except ValueError as error:
        raise GateEvaluationError("疗效安全性汇总输入无效，拒绝旁路篡改") from error
    analysis = analyze_universe(projects, snapshot, bindings)
    if not analysis.report_ready:
        raise GateEvaluationError("存在关键证据不足的产品，疗效安全性汇总不得生成草稿")
    if not endpoint_families:
        raise GateEvaluationError("至少需要一个可横向比较的疗效指标族")
    if len({family.family_id for family in endpoint_families}) != len(endpoint_families):
        raise GateEvaluationError("疗效指标族标识不得重复")
    if any(
        not set(family.compatible_endpoint_ids) <= set(snapshot.endpoint_ids)
        for family in endpoint_families
    ):
        raise GateEvaluationError("疗效指标族引用了当前快照之外的终点")
    _validate_measure_coverage(snapshot, bindings, efficacy_records, safety_records)
    current = _current_measure_bindings(snapshot, bindings)
    role_by_group = _validated_group_roles(snapshot, current, group_roles)
    family_by_id = {family.family_id: family for family in endpoint_families}
    trial_product = _trial_product_map_for_summary(snapshot)

    efficacy_points: list[EfficacyPoint] = []
    for efficacy_record in efficacy_records:
        binding = current.get(efficacy_record.fact_version_id)
        family = family_by_id.get(efficacy_record.endpoint_family_id)
        if binding is None or binding.fact_domain is not FactDomain.EFFICACY or family is None:
            raise GateEvaluationError("疗效事实映射引用未知事实或未知疗效指标族")
        _assert_result_source(binding)
        _assert_numeric_measure_valid(binding)
        if (
            binding.trial_id is None
            or binding.endpoint_id not in family.compatible_endpoint_ids
            or binding.unit not in family.compatible_units
            or binding.timepoint not in family.compatible_timepoints
            or binding.analysis_population not in family.compatible_analysis_populations
            or binding.definition is None
            or not all(term in binding.definition for term in family.definition_required_terms)
            or binding.direction not in family.compatible_direction_texts
        ):
            raise GateEvaluationError("疗效事实的终点、定义、方向或单位与指标族不兼容")
        if (
            binding.group_id is None
            or binding.group_id not in role_by_group
            or efficacy_record.arm_role is not role_by_group[binding.group_id].arm_role
        ):
            raise GateEvaluationError("疗效事实必须绑定当前设计证据中的治疗组或对照组角色")
        group_role = role_by_group[binding.group_id]
        if (
            group_role.arm_role is ArmRole.TREATMENT
            and binding.treatment_group != group_role.group_label_zh
        ) or (
            group_role.arm_role is ArmRole.CONTROL
            and binding.control_group != group_role.group_label_zh
        ):
            raise GateEvaluationError("疗效事实组名与当前试验设计角色不一致")
        group_label = group_role.group_label_zh
        raw = binding.numeric_value if _reported(binding) else None
        corrected = (
            None
            if raw is None
            else (raw if family.direction is EndpointDirection.HIGHER_IS_BETTER else -raw)
        )
        efficacy_points.append(
            EfficacyPoint(
                project_id=trial_product[binding.trial_id],
                trial_id=binding.trial_id,
                endpoint_id=binding.endpoint_id,
                endpoint_family_id=family.family_id,
                endpoint_label_zh=family.label_zh,
                definition_zh=binding.definition,
                direction_zh=binding.direction,
                arm_role=efficacy_record.arm_role,
                group_id=binding.group_id,
                group_label_zh=group_label,
                raw_value=raw,
                direction_corrected_value=corrected,
                unit=binding.unit,
                denominator=binding.denominator,
                timepoint_zh=binding.timepoint,
                analysis_population_zh=binding.analysis_population,
                disclosure_state=binding.disclosure_state,
                fact_version_id=binding.fact_version_id,
                source_location=binding.source_location,
            )
        )
    efficacy_points.sort(
        key=lambda point: (
            point.project_id,
            point.trial_id,
            point.endpoint_family_id,
            _ARM_ORDER[point.arm_role],
            point.fact_version_id,
        )
    )
    design = {item.trial_id: item.design_kind for item in snapshot.trial_design_evidence}
    efficacy_keys = [
        (point.trial_id, point.endpoint_family_id, point.group_id) for point in efficacy_points
    ]
    if len(efficacy_keys) != len(set(efficacy_keys)):
        raise GateEvaluationError("同一试验、指标族和组别存在多条疗效事实，必须先消除歧义")
    for trial_id, family_id in {
        (point.trial_id, point.endpoint_family_id) for point in efficacy_points
    }:
        contexts = {
            (
                point.timepoint_zh,
                point.analysis_population_zh,
                point.unit,
                point.endpoint_id,
            )
            for point in efficacy_points
            if point.trial_id == trial_id and point.endpoint_family_id == family_id
        }
        if len(contexts) != 1:
            raise GateEvaluationError("同一疗效比较的时间点、分析集与单位必须兼容")
        observed_groups = {
            point.group_id
            for point in efficacy_points
            if point.trial_id == trial_id and point.endpoint_family_id == family_id
        }
        expected_groups = {record.group_id for record in group_roles if record.trial_id == trial_id}
        if observed_groups != expected_groups:
            raise GateEvaluationError("同一疗效比较必须完整保留全部治疗组和对照组")
        roles = {
            point.arm_role
            for point in efficacy_points
            if point.trial_id == trial_id and point.endpoint_family_id == family_id
        }
        if ArmRole.TREATMENT not in roles:
            raise GateEvaluationError("疗效横向比较缺少治疗组")
        if design[trial_id] is TrialDesignKind.COMPARATIVE and ArmRole.CONTROL not in roles:
            raise GateEvaluationError("比较设计的疗效横向比较必须同时保留对照组")

    safety_cells_base: list[SafetyHeatmapCell] = []
    for safety_record in safety_records:
        binding = current.get(safety_record.fact_version_id)
        if (
            binding is None
            or binding.fact_domain is not FactDomain.SAFETY
            or binding.trial_id is None
        ):
            raise GateEvaluationError("安全性事实映射引用未知或非安全性事实")
        _assert_safety_family_matches_binding(safety_record, binding)
        _assert_result_source(binding)
        _assert_numeric_measure_valid(binding)
        if binding.unit not in _SAFETY_MEASUREMENT_UNITS:
            raise GateEvaluationError("安全性结果必须使用预先定义的规范测量单位")
        if (
            binding.event_definition is None
            or binding.time_window is None
            or binding.analysis_population is None
        ):
            raise GateEvaluationError("安全性结果必须保留事件定义、观察时间窗和分析集")
        if (
            binding.group_id is None
            or binding.group_id not in role_by_group
            or safety_record.arm_role is not role_by_group[binding.group_id].arm_role
        ):
            raise GateEvaluationError("安全性事实必须绑定当前设计证据中的治疗组或对照组角色")
        group_role = role_by_group[binding.group_id]
        if (
            group_role.arm_role is ArmRole.TREATMENT
            and binding.treatment_group != group_role.group_label_zh
        ) or (
            group_role.arm_role is ArmRole.CONTROL
            and binding.control_group != group_role.group_label_zh
        ):
            raise GateEvaluationError("安全性事实组名与当前试验设计角色不一致")
        group_label = group_role.group_label_zh
        raw_value = binding.numeric_value if _reported(binding) else None
        comparison_rate: float | None = None
        if raw_value is not None and binding.unit == SafetyMeasurementUnit.PERCENT.value:
            comparison_rate = float(raw_value)
        elif (
            raw_value is not None
            and binding.unit == SafetyMeasurementUnit.PARTICIPANT_COUNT.value
            and binding.denominator is not None
        ):
            comparison_rate = float(raw_value) / binding.denominator * 100
        if comparison_rate is not None and not 0 <= comparison_rate <= 100:
            raise GateEvaluationError("安全性发生率必须位于0至100之间")
        safety_cells_base.append(
            SafetyHeatmapCell(
                project_id=trial_product[binding.trial_id],
                trial_id=binding.trial_id,
                family=safety_record.family,
                term_id=safety_record.term_id,
                arm_role=safety_record.arm_role,
                group_id=binding.group_id,
                group_label_zh=group_label,
                raw_value=raw_value,
                unit=binding.unit,
                denominator=binding.denominator,
                event_definition_zh=binding.event_definition,
                time_window_zh=binding.time_window,
                analysis_population_zh=binding.analysis_population,
                disclosure_state=binding.disclosure_state,
                matrix_default=safety_record.matrix_default,
                comparison_rate_percent=comparison_rate,
                fact_version_id=binding.fact_version_id,
                source_location=binding.source_location,
            )
        )
    safety_keys = [
        (
            cell.trial_id,
            cell.family,
            cell.term_id,
            cell.event_definition_zh,
            cell.time_window_zh,
            cell.analysis_population_zh,
            cell.group_id,
        )
        for cell in safety_cells_base
    ]
    if len(safety_keys) != len(set(safety_keys)):
        raise GateEvaluationError("同一试验组和安全性语境存在多条事实，必须先消除歧义")
    defaults_by_trial_group: dict[tuple[str, str], list[SafetyHeatmapCell]] = {}
    for cell in safety_cells_base:
        if not cell.matrix_default:
            continue
        if (
            cell.term_id != "teae-any"
            or cell.event_definition_zh != "治疗期间不良事件"
            or cell.time_window_zh != "治疗期间"
            or cell.group_id is None
        ):
            raise GateEvaluationError("默认安全性矩阵记录必须是总体治疗期间不良事件")
        defaults_by_trial_group.setdefault((cell.trial_id, cell.group_id), []).append(cell)
    if any(len(cells) != 1 for cells in defaults_by_trial_group.values()):
        raise GateEvaluationError("同一试验和组别只能有一条默认安全性矩阵记录")
    for trial_id in snapshot.trial_ids:
        has_teae = any(
            cell.trial_id == trial_id and cell.family is SafetyFamily.TEAE
            for cell in safety_cells_base
        )
        trial_group_ids = {record.group_id for record in group_roles if record.trial_id == trial_id}
        if has_teae and any(
            len(defaults_by_trial_group.get((trial_id, group_id), [])) != 1
            for group_id in trial_group_ids
        ):
            raise GateEvaluationError("有结果试验的每个组别都必须保留总体治疗期间不良事件默认记录")
        default_contexts = {
            (
                cells[0].term_id,
                cells[0].event_definition_zh,
                cells[0].time_window_zh,
                cells[0].analysis_population_zh,
            )
            for (record_trial, _group_id), cells in defaults_by_trial_group.items()
            if record_trial == trial_id
        }
        if len(default_contexts) > 1:
            raise GateEvaluationError("各组默认安全性矩阵语境必须一致")
    for trial_id, safety_family_key, term_id, event_definition, time_window, population in {
        (
            cell.trial_id,
            cell.family,
            cell.term_id,
            cell.event_definition_zh,
            cell.time_window_zh,
            cell.analysis_population_zh,
        )
        for cell in safety_cells_base
    }:
        observed_groups = {
            cell.group_id
            for cell in safety_cells_base
            if cell.trial_id == trial_id
            and cell.family is safety_family_key
            and cell.term_id == term_id
            and cell.event_definition_zh == event_definition
            and cell.time_window_zh == time_window
            and cell.analysis_population_zh == population
        }
        expected_groups = {record.group_id for record in group_roles if record.trial_id == trial_id}
        if observed_groups != expected_groups:
            raise GateEvaluationError("同一安全性语境必须完整保留全部治疗组和对照组")
    safety_cells: list[SafetyHeatmapCell] = []
    for cell in safety_cells_base:
        peers = [
            peer.comparison_rate_percent
            for peer in safety_cells_base
            if peer.family is cell.family
            and peer.term_id == cell.term_id
            and peer.arm_role is cell.arm_role
            and peer.event_definition_zh == cell.event_definition_zh
            and peer.time_window_zh == cell.time_window_zh
            and peer.analysis_population_zh == cell.analysis_population_zh
            and peer.comparison_rate_percent is not None
        ]
        maximum = max((float(value) for value in peers), default=0.0)
        intensity = (
            None
            if cell.comparison_rate_percent is None
            else (0.0 if maximum == 0 else cell.comparison_rate_percent / maximum)
        )
        safety_cells.append(cell.model_copy(update={"relative_intensity": intensity}))
    safety_cells.sort(
        key=lambda cell: (
            cell.family.value,
            cell.term_id,
            cell.project_id,
            cell.trial_id,
            _ARM_ORDER[cell.arm_role],
            cell.fact_version_id,
        )
    )

    eligible_anchor_trials = _eligible_anchor_trials(efficacy_points, safety_cells, snapshot)
    anchors = _select_anchors(
        projects,
        snapshot,
        bindings,
        trial_selection,
        eligible_anchor_trials,
    )
    result_by_project = {item.project_id: item.gate.result_bearing for item in analysis.projects}
    fields: dict[str, object] = {
        "identity": AAnalysisIdentity(
            universe_project_id=snapshot.project_id,
            evidence_snapshot_id=snapshot.evidence_snapshot_id,
            research_role_set_id=snapshot.research_role_set_id,
            universe_summary=snapshot.universe_summary,
            indication_rule_set_id=snapshot.indication_rule_set_id,
        ),
        "product_ids": tuple(project.project_id for project in projects),
        "target_groups": _target_groups(projects),
        "product_results": tuple(
            ProductResultSummary(
                project_id=project.project_id,
                canonical_name=project.canonical_name,
                state=(
                    ProductResultState.HAS_PUBLIC_RESULTS
                    if result_by_project[project.project_id]
                    else ProductResultState.NO_PUBLIC_RESULTS
                ),
            )
            for project in projects
        ),
        "anchors": anchors,
        "endpoint_families": tuple(endpoint_families),
        "default_endpoint_family_id": _default_endpoint(
            endpoint_families, efficacy_points, snapshot
        ),
        "efficacy_points": tuple(efficacy_points),
        "safety_cells": tuple(safety_cells),
    }
    return AEfficacySafetySummaryView.model_validate(
        {**fields, "content_digest": _analysis_digest(fields)}
    )


def assert_efficacy_safety_summary_authoritative(
    view: AEfficacySafetySummaryView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    trial_selection: Sequence[TrialSelectionRecord],
    group_roles: Sequence[TrialGroupRoleRecord],
    endpoint_families: Sequence[EndpointFamilySpec],
    efficacy_records: Sequence[EfficacyMeasureRecord],
    safety_records: Sequence[SafetyMeasureRecord],
) -> None:
    """重建并比较当前权威输入，拒绝旁路伪造、旧快照或残缺产品集。"""
    try:
        validated = AEfficacySafetySummaryView.model_validate(view.model_dump(mode="json"))
    except ValueError as error:
        raise GateEvaluationError("疗效安全性汇总无法通过内容摘要复核") from error
    rebuilt = build_efficacy_safety_summary(
        projects=projects,
        snapshot=snapshot,
        bindings=bindings,
        trial_selection=trial_selection,
        group_roles=group_roles,
        endpoint_families=endpoint_families,
        efficacy_records=efficacy_records,
        safety_records=safety_records,
    )
    if validated != rebuilt:
        raise GateEvaluationError("疗效安全性汇总与当前权威输入不一致")


_BUBBLE_Y_NOTE_ZH = "向上 = 发生率更低 = 观察到的安全性位置更有利"


def _assert_summary_intrinsic(view: AEfficacySafetySummaryView) -> AEfficacySafetySummaryView:
    try:
        return AEfficacySafetySummaryView.model_validate(view.model_dump(mode="json"))
    except ValueError as error:
        raise GateEvaluationError("疗效安全性汇总内容摘要无效") from error


def build_bubble_matrix(
    summary: AEfficacySafetySummaryView,
    *,
    current_universe_summary: str,
    endpoint_family_id: str | None = None,
    safety_family: SafetyFamily = SafetyFamily.TEAE,
    safety_term_id: str | None = None,
    safety_event_definition_zh: str | None = None,
    safety_time_window_zh: str | None = None,
    safety_analysis_population_zh: str | None = None,
    radius_scale: float = 1.0,
) -> ABubbleMatrixView:
    """从权威汇总构建可调维度气泡矩阵；默认 TEAE，不做替代或综合评分。"""
    if not math.isfinite(radius_scale) or radius_scale <= 0:
        raise ValueError("气泡半径系数必须是大于零的有限数值")
    summary = _assert_summary_intrinsic(summary)
    if summary.identity.universe_summary != _text(current_universe_summary):
        raise GateEvaluationError("疗效安全性汇总不属于当前竞品宇宙快照")
    selected_endpoint = endpoint_family_id or summary.default_endpoint_family_id
    if selected_endpoint not in {family.family_id for family in summary.endpoint_families}:
        raise GateEvaluationError("所选疗效指标不属于本次报告")
    if safety_family is not SafetyFamily.TEAE and safety_term_id is None:
        raise GateEvaluationError("选择其他安全性维度时必须明确具体事件")
    family_treatment_cells = [
        cell
        for cell in summary.safety_cells
        if cell.family is safety_family and cell.arm_role is ArmRole.TREATMENT
    ]
    if safety_term_id is not None and safety_term_id not in {
        cell.term_id for cell in family_treatment_cells
    }:
        raise GateEvaluationError("所选安全性事件不属于本次报告")
    selected_safety_cells = [
        cell
        for cell in family_treatment_cells
        if (safety_term_id is None and cell.matrix_default) or cell.term_id == safety_term_id
    ]
    if safety_time_window_zh is not None and safety_time_window_zh not in {
        cell.time_window_zh for cell in selected_safety_cells
    }:
        raise GateEvaluationError("所选安全性时间窗不属于本次报告")
    if safety_event_definition_zh is not None and safety_event_definition_zh not in {
        cell.event_definition_zh for cell in selected_safety_cells
    }:
        raise GateEvaluationError("所选安全性事件定义不属于本次报告")
    if safety_analysis_population_zh is not None and safety_analysis_population_zh not in {
        cell.analysis_population_zh for cell in selected_safety_cells
    }:
        raise GateEvaluationError("所选安全性分析集不属于本次报告")
    resolved_safety_time_window = safety_time_window_zh
    if safety_term_id is not None and resolved_safety_time_window is None:
        candidate_windows = {
            cell.time_window_zh
            for cell in summary.safety_cells
            if cell.family is safety_family
            and cell.term_id == safety_term_id
            and cell.arm_role is ArmRole.TREATMENT
            and cell.time_window_zh is not None
        }
        if len(candidate_windows) > 1:
            raise GateEvaluationError("同一安全性事件存在多个时间窗，请明确选择后再比较")
        if len(candidate_windows) == 1:
            resolved_safety_time_window = next(iter(candidate_windows))
    points: list[BubblePoint] = []
    unplottable: list[UnplottableBubbleProduct] = []
    anchor_by_product = {anchor.project_id: anchor.trial_id for anchor in summary.anchors}
    for product_id in summary.product_ids:
        anchor_trial_id = anchor_by_product.get(product_id)
        efficacies = [
            point
            for point in summary.efficacy_points
            if point.project_id == product_id
            and point.trial_id == anchor_trial_id
            and point.endpoint_family_id == selected_endpoint
            and point.arm_role is ArmRole.TREATMENT
            and point.raw_value is not None
            and point.direction_corrected_value is not None
            and point.denominator is not None
            and point.group_id is not None
        ]
        if not efficacies:
            unplottable.append(
                UnplottableBubbleProduct(
                    project_id=product_id,
                    reason_zh="所选疗效指标尚无可量化结果",
                )
            )
            continue
        for efficacy in efficacies:
            safety_candidates = [
                cell
                for cell in summary.safety_cells
                if cell.project_id == product_id
                and cell.trial_id == efficacy.trial_id
                and cell.group_id == efficacy.group_id
                and cell.family is safety_family
                and (
                    (safety_term_id is None and cell.matrix_default)
                    or cell.term_id == safety_term_id
                )
                and (
                    safety_event_definition_zh is None
                    or cell.event_definition_zh == safety_event_definition_zh
                )
                and (
                    resolved_safety_time_window is None
                    or cell.time_window_zh == resolved_safety_time_window
                )
                and (
                    safety_analysis_population_zh is None
                    or cell.analysis_population_zh == safety_analysis_population_zh
                )
                and cell.arm_role is ArmRole.TREATMENT
            ]
            if len(safety_candidates) > 1:
                raise GateEvaluationError(
                    "同一治疗组存在多个安全性完整语境，请明确事件定义、时间窗和分析集"
                )
            safety = safety_candidates[0] if safety_candidates else None
            if (
                safety is None
                or safety.comparison_rate_percent is None
                or safety.denominator is None
            ):
                labels_zh = {
                    SafetyFamily.TEAE: "治疗期间不良事件",
                    SafetyFamily.SAE: "严重不良事件",
                    SafetyFamily.AESI: "特别关注的不良事件",
                    SafetyFamily.COMMON_AE: "常见不良事件",
                }
                unplottable.append(
                    UnplottableBubbleProduct(
                        project_id=product_id,
                        group_id=efficacy.group_id,
                        group_label_zh=efficacy.group_label_zh,
                        reason_zh=f"{labels_zh[safety_family]}发生率尚无可量化结果",
                    )
                )
                continue
            assert efficacy.group_id is not None
            assert efficacy.raw_value is not None
            assert efficacy.direction_corrected_value is not None
            assert safety.comparison_rate_percent is not None
            assert safety.denominator is not None
            assert safety.event_definition_zh is not None
            assert safety.time_window_zh is not None
            assert safety.analysis_population_zh is not None
            raw_safety = safety.comparison_rate_percent
            sample_size = safety.denominator
            points.append(
                BubblePoint(
                    project_id=product_id,
                    trial_id=efficacy.trial_id,
                    group_id=efficacy.group_id,
                    group_label_zh=efficacy.group_label_zh,
                    endpoint_family_id=selected_endpoint,
                    efficacy_fact_version_id=efficacy.fact_version_id,
                    safety_family=safety_family,
                    safety_term_id=safety.term_id,
                    safety_event_definition_zh=safety.event_definition_zh,
                    safety_time_window_zh=safety.time_window_zh,
                    safety_analysis_population_zh=safety.analysis_population_zh,
                    safety_fact_version_id=safety.fact_version_id,
                    arm_role=ArmRole.TREATMENT,
                    efficacy_position=float(efficacy.direction_corrected_value),
                    raw_efficacy_value=float(efficacy.raw_value),
                    raw_safety_rate=raw_safety,
                    safety_position=100.0 - raw_safety,
                    sample_size=sample_size,
                    radius=radius_scale * math.sqrt(sample_size / math.pi),
                )
            )
    selected_contexts = {
        (
            point.safety_term_id,
            point.safety_event_definition_zh,
            point.safety_time_window_zh,
            point.safety_analysis_population_zh,
        )
        for point in points
    }
    if len(selected_contexts) > 1:
        raise GateEvaluationError(
            "气泡矩阵包含多个安全性完整语境，请明确事件、定义、时间窗和分析集"
        )
    selected_term_id: str | None = safety_term_id
    selected_event_definition: str | None = safety_event_definition_zh
    selected_time_window: str | None = resolved_safety_time_window
    selected_analysis_population: str | None = safety_analysis_population_zh
    if selected_contexts:
        (
            selected_term_id,
            selected_event_definition,
            selected_time_window,
            selected_analysis_population,
        ) = next(iter(selected_contexts))
    fields: dict[str, object] = {
        "source_summary_digest": summary.content_digest,
        "endpoint_family_id": selected_endpoint,
        "safety_family": safety_family,
        "safety_term_id": selected_term_id,
        "safety_event_definition_zh": selected_event_definition,
        "safety_time_window_zh": selected_time_window,
        "safety_analysis_population_zh": selected_analysis_population,
        "radius_scale": radius_scale,
        "y_axis_note_zh": _BUBBLE_Y_NOTE_ZH,
        "points": tuple(points),
        "unplottable_products": tuple(unplottable),
    }
    return ABubbleMatrixView.model_validate({**fields, "content_digest": _analysis_digest(fields)})
