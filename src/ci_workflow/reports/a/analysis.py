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

from collections.abc import Sequence
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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
