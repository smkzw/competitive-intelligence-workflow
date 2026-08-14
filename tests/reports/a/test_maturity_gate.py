"""Task 5.1 成熟度递增字段失败测试（强输入：Phase 3 snapshot + bindings）。

合同断言（先失败后通过）：
- A 项目合同拒绝空值冒充：空白字符串、缺失别名记录、非纳入资格均无法构造；
  手工填写成熟度/result-bearing 的自由字段成为 extra 并被拒绝；
- 成熟度分层逐层递增必需字段；任何一层必需字段缺失独立阻断，不适用必须
  显式表达，不允许用空值、默认零或未公开状态冒充；
- 成熟度与 result-bearing 由当前不可变 snapshot + 已接受绑定推导，不接受
  调用方手工降级或手工触发；
- 临床项目必需核心试验身份/开发角色/状态且试验必须属于本产品与 snapshot；
- 申报/上市/终止项目必需事件、地域与日期，且地域与日期由同一条事件同时
  满足，不得跨事件拼接；
- 当前开发者/原研方整组不适用仅限暂停/终止/撤回项目；中国/境外整组不适用
  若与同地域监管事件矛盾则阻断；
- 已公开结果项目必需适格锚定试验、可解释核心疗效记录与 TEAE/SAE 数值摘要，
  全部由已接受证据绑定判定。
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    ConflictDisposition,
    DevelopmentMaturity,
    DisclosureMaturity,
    EmptySetProof,
    EmptySetReasonCode,
    FactDomain,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    ObservationKind,
    SourceRole,
    TrialDesignEvidence,
    TrialDesignKind,
    UniverseEdge,
    compute_universe_summary,
)
from ci_workflow.reports.a.analysis import (
    MaturityGateResult,
    determine_maturity_level,
    evaluate_maturity_gate,
)
from ci_workflow.reports.a.contracts import (
    ANCHOR_TRIAL,
    CHINA_STAGE_STATUS_DATE,
    CORE_EFFICACY_RECORD,
    CORE_TRIAL_DEVELOPMENT_ROLE,
    CORE_TRIAL_IDENTITY,
    CORE_TRIAL_STATUS,
    DEVELOPER_ORIGINATOR,
    INDICATION_RELATION,
    MODALITY,
    OVERSEAS_STAGE_STATUS_DATE,
    REGULATORY_EVENT,
    REGULATORY_EVENT_DATE,
    REGULATORY_EVENT_JURISDICTION,
    SAFETY_SUMMARY_RECORD,
    TARGET_MECHANISM,
    AnchorTrialRecord,
    AProjectContract,
    CoreTrialRecord,
    CoreTrialRole,
    MaturityLevel,
    RegulatoryEventKind,
    RegulatoryEventRecord,
    RequiredFieldKey,
    assert_ladder_monotonic,
    required_fields_for,
)
from ci_workflow.reports.common.evidence_view import EvidenceField, EvidenceFieldState


def _field(value: str | None = None, state: EvidenceFieldState | None = None) -> EvidenceField:
    return EvidenceField(value=value, state=state)


def _region(stage: str, status: str, date: str) -> dict[str, EvidenceField]:
    return {
        "highest_stage": _field(value=stage),
        "highest_status": _field(value=status),
        "date": _field(value=date),
    }


def _snapshot(
    *,
    project_id: str = "report-universe",
    product_ids: tuple[str, ...] = ("project-dupilumab",),
    trial_ids: tuple[str, ...] = ("NCT02407756",),
    trial_products: dict[str, str] | None = None,
    design_kinds: dict[str, TrialDesignKind] | None = None,
    comparison_groups: dict[str, dict[str, tuple[str, str]]] | None = None,
    applicable_conditional_predicates: tuple[str, ...] = (),
) -> ApplicableUniverseSnapshot:
    """构建已闭合的适用宇宙快照；比较设计试验必须提供比较/组别图。"""
    trial_products = trial_products or {trial: product_ids[0] for trial in trial_ids}
    design_kinds = design_kinds or {trial: TrialDesignKind.SINGLE_ARM for trial in trial_ids}
    edges: list[UniverseEdge] = []
    for trial in trial_ids:
        edges.append(
            UniverseEdge(
                parent_type=GateObjectType.PRODUCT,
                parent_id=trial_products[trial],
                child_type=GateObjectType.TRIAL,
                child_id=trial,
            )
        )
    comparison_ids: list[str] = []
    group_ids: list[str] = []
    for trial, comparisons in (comparison_groups or {}).items():
        for comparison_id, groups in comparisons.items():
            comparison_ids.append(comparison_id)
            edges.append(
                UniverseEdge(
                    parent_type=GateObjectType.TRIAL,
                    parent_id=trial,
                    child_type=GateObjectType.COMPARISON,
                    child_id=comparison_id,
                )
            )
            for group_id in groups:
                group_ids.append(group_id)
                edges.append(
                    UniverseEdge(
                        parent_type=GateObjectType.TRIAL,
                        parent_id=trial,
                        child_type=GateObjectType.GROUP,
                        child_id=group_id,
                    )
                )
                edges.append(
                    UniverseEdge(
                        parent_type=GateObjectType.COMPARISON,
                        parent_id=comparison_id,
                        child_type=GateObjectType.GROUP,
                        child_id=group_id,
                    )
                )
    trial_design_evidence = tuple(
        TrialDesignEvidence(
            trial_id=trial,
            design_kind=design_kinds[trial],
            evidence_version_id=f"design-ev-{trial}",
            explanation_zh="试验设计类型已核验",
        )
        for trial in trial_ids
    )
    empty_proofs: list[EmptySetProof] = []
    present: dict[GateObjectType, tuple[str, ...]] = {
        GateObjectType.TRIAL: trial_ids,
        GateObjectType.COMPARISON: tuple(comparison_ids),
        GateObjectType.GROUP: tuple(group_ids),
        GateObjectType.ENDPOINT: (),
        GateObjectType.TIMEPOINT: (),
    }
    for object_type, ids in present.items():
        if not ids:
            empty_proofs.append(
                EmptySetProof(
                    object_type=object_type,
                    reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
                    evidence_version_id=f"empty-ev-{object_type.value}",
                    explanation_zh="穷尽检索后未发现相关对象",
                )
            )
    summary = compute_universe_summary(
        project_id=project_id,
        evidence_snapshot_id="snap-ev-1",
        research_role_set_id="role-set-1",
        product_ids=product_ids,
        trial_ids=trial_ids,
        comparison_ids=tuple(comparison_ids),
        group_ids=tuple(group_ids),
        empty_set_proofs=tuple(empty_proofs),
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id="ind-rule-1",
        applicable_conditional_predicates=applicable_conditional_predicates,
    )
    return ApplicableUniverseSnapshot(
        project_id=project_id,
        evidence_snapshot_id="snap-ev-1",
        research_role_set_id="role-set-1",
        product_ids=product_ids,
        trial_ids=trial_ids,
        comparison_ids=tuple(comparison_ids),
        group_ids=tuple(group_ids),
        empty_set_proofs=tuple(empty_proofs),
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id="ind-rule-1",
        applicable_conditional_predicates=applicable_conditional_predicates,
        universe_summary=summary,
        enumeration_complete=True,
    )


def _binding(
    *,
    binding_id: str = "b-1",
    unit_id: str = "a-unit-1",
    object_id: str = "project-dupilumab",
    trial_id: str | None = "NCT02407756",
    fact_version_id: str = "fact-v-1",
    fact_domain: FactDomain = FactDomain.EFFICACY,
    observation_kind: ObservationKind = ObservationKind.OBSERVED_RESULT,
    numeric_value: int | float | None = 52.3,
    unit: str | None = "应答率 %",
    denominator: int | None = 224,
    definition: str | None = "特应性皮炎研究者总体评估 0 或 1 且较基线改善≥2 分",
    direction: str | None = "应答率越高越好",
    timepoint: str | None = "第 16 周",
    analysis_population: str | None = "意向治疗集",
    treatment_group: str | None = "度普利尤单抗 300mg 每两周",
    control_group: str | None = None,
    event_definition: str | None = None,
    time_window: str | None = None,
    review_state: FactReviewState = FactReviewState.ACCEPTED,
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    source_role: SourceRole = SourceRole.PRIMARY_TRIAL_REPORT,
    source_location: str | None = "CT.gov/results/table-1",
    applicability_predicate_id: str | None = None,
    reported_zero_text: str | None = None,
) -> GateEvidenceBinding:
    return GateEvidenceBinding(
        binding_id=binding_id,
        unit_id=unit_id,
        object_id=object_id,
        fact_version_id=fact_version_id,
        trial_id=trial_id,
        fact_domain=fact_domain,
        observation_kind=observation_kind,
        numeric_value=numeric_value,
        unit=unit,
        denominator=denominator,
        definition=definition,
        direction=direction,
        timepoint=timepoint,
        analysis_population=analysis_population,
        treatment_group=treatment_group,
        control_group=control_group,
        event_definition=event_definition,
        time_window=time_window,
        source_location=source_location,
        review_state=review_state,
        disclosure_state=disclosure_state,
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        source_role=source_role,
        conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        applicability_predicate_id=applicability_predicate_id,
        reported_zero_text=reported_zero_text,
    )


def _complete_project(**overrides: object) -> AProjectContract:
    """构建一个所有必需字段齐备的 A 项目；测试用 overrides 制造缺口。"""
    payload: dict[str, object] = {
        "project_id": "project-dupilumab",
        "canonical_name": "度普利尤单抗",
        "aliases": ("Dupixent", "Dupilumab"),
        "identity_basis": "以登记名称、INN 与别名一致性为身份依据",
        "eligibility": "included",
        "eligibility_policy_id": "innovation-therapy-v1",
        "eligibility_rule_id": "include-monoclonal-antibody",
        "target_mechanism": _field(value="IL-4Rα 受体阻断"),
        "modality": _field(value="单克隆抗体"),
        "developer": _field(value="赛诺菲"),
        "originator": _field(value="再生元"),
        "indication_relation": _field(value="目标适应症已确立的核心竞品"),
        "china": _region("上市", "已批准", "2020-06-19"),
        "overseas": _region("上市", "已批准", "2017-03-28"),
        "core_trials": (
            CoreTrialRecord(
                trial_id="NCT02407756",
                role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                status="已完成",
            ),
        ),
        "regulatory_events": (
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.APPROVAL,
                jurisdiction=_field(value="中国"),
                event_date=_field(value="2020-06-19"),
            ),
        ),
        "anchor_trials": (
            AnchorTrialRecord(
                trial_id="NCT02407756",
                fact_version_ids=("fact-v-1",),
            ),
        ),
    }
    payload.update(overrides)
    return AProjectContract.model_validate(payload)


def _default_bindings() -> tuple[GateEvidenceBinding, ...]:
    """默认已接受绑定：批准（监管观察值）+ 核心疗效 + TEAE 摘要。"""
    return (
        _binding(
            binding_id="b-reg",
            fact_version_id="fact-v-1",
            source_role=SourceRole.REGULATORY_MATERIAL,
            definition=None,
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
        ),
        _binding(
            binding_id="b-eff",
            fact_version_id="fact-v-2",
        ),
        _binding(
            binding_id="b-saf",
            unit_id="a_safety_event_teae",
            fact_version_id="fact-v-3",
            fact_domain=FactDomain.SAFETY,
            unit="%",
            definition=None,
            direction=None,
            timepoint=None,
            control_group=None,
            event_definition="治疗期间不良事件",
            time_window="治疗期间",
        ),
    )


def _evaluate(
    project: AProjectContract,
    *,
    snapshot: ApplicableUniverseSnapshot | None = None,
    bindings: tuple[GateEvidenceBinding, ...] | None = None,
) -> MaturityGateResult:
    if snapshot is None:
        snapshot = _snapshot()
    if bindings is None:
        bindings = _default_bindings()
    return evaluate_maturity_gate(project, snapshot, bindings)


def _missing_keys(result: MaturityGateResult) -> frozenset[RequiredFieldKey]:
    return frozenset(result.missing_keys)


def _clinical_project(**overrides: object) -> AProjectContract:
    base: dict[str, object] = {
        "project_id": "p-clinical",
        "canonical_name": "临床示例药",
        "core_trials": (
            CoreTrialRecord(
                trial_id="NCT-clin-1",
                role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                status="进行中",
            ),
        ),
        "regulatory_events": (),
        "anchor_trials": (),
    }
    return _complete_project(**{**base, **overrides})


def _clinical_snapshot() -> ApplicableUniverseSnapshot:
    return _snapshot(product_ids=("p-clinical",), trial_ids=("NCT-clin-1",))


def _clinical_bindings() -> tuple[GateEvidenceBinding, ...]:
    return (
        _binding(
            binding_id="b-clin",
            object_id="p-clinical",
            trial_id="NCT-clin-1",
            fact_domain=FactDomain.TRIAL_DESIGN,
            numeric_value=None,
            unit=None,
            denominator=None,
            definition="随机对照试验设计",
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
            fact_version_id="fact-clin",
            source_role=SourceRole.PROTOCOL_SAP,
        ),
    )


def _preclinical_project(**overrides: object) -> AProjectContract:
    return _complete_project(
        project_id="p-preclinical",
        canonical_name="临床前示例药",
        core_trials=(),
        regulatory_events=(),
        anchor_trials=(),
        **overrides,
    )


def _preclinical_snapshot() -> ApplicableUniverseSnapshot:
    return _snapshot(product_ids=("p-preclinical",), trial_ids=())


def _terminated_project(**overrides: object) -> AProjectContract:
    base: dict[str, object] = {
        "project_id": "p-terminated",
        "canonical_name": "终止示例药",
        "core_trials": (
            CoreTrialRecord(
                trial_id="NCT-term-1",
                role=CoreTrialRole.EARLY_DECISION,
                status="已终止",
            ),
        ),
        "regulatory_events": (
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.TERMINATION,
                jurisdiction=_field(value="境外"),
                event_date=_field(value="2023-11-01"),
            ),
        ),
        "anchor_trials": (),
    }
    return _complete_project(**{**base, **overrides})


def _terminated_snapshot() -> ApplicableUniverseSnapshot:
    return _snapshot(
        product_ids=("p-terminated",),
        trial_ids=("NCT-term-1",),
        applicable_conditional_predicates=("termination-rule-1",),
    )


def _terminated_bindings() -> tuple[GateEvidenceBinding, ...]:
    return (
        _binding(
            binding_id="b-term-design",
            object_id="p-terminated",
            trial_id="NCT-term-1",
            fact_domain=FactDomain.TRIAL_DESIGN,
            numeric_value=None,
            unit=None,
            denominator=None,
            definition="早期决策试验",
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
            fact_version_id="fact-term-design",
            source_role=SourceRole.PROTOCOL_SAP,
        ),
        _binding(
            binding_id="b-term-reg",
            unit_id="a_regulatory_termination",
            object_id="p-terminated",
            trial_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            numeric_value=None,
            unit=None,
            denominator=None,
            definition=None,
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
            fact_version_id="fact-term-reg",
            source_role=SourceRole.REGULATORY_MATERIAL,
            disclosure_state=FactDisclosureState.NOT_APPLICABLE,
            applicability_predicate_id="termination-rule-1",
        ),
    )


# ── 合同层：空值与降级不得构造 ─────────────────────────────────────────────


def test_blank_text_cannot_be_constructed() -> None:
    """空白或纯空格字符串在任何必需字段中都不被接受。"""
    with pytest.raises(ValidationError):
        _complete_project(canonical_name="   ")
    with pytest.raises(ValidationError):
        _complete_project(aliases=("度普利尤单抗", "  "))
    with pytest.raises(ValidationError):
        _complete_project(
            core_trials=(
                CoreTrialRecord(
                    trial_id="  ",
                    role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                    status="已完成",
                ),
            )
        )


def test_aliases_require_values_or_explicit_absence_basis() -> None:
    """无别名不是空白：必须保存明确的检索后无别名依据。"""
    with pytest.raises(ValidationError):
        _complete_project(aliases=())
    project = _complete_project(
        aliases=(), aliases_absence_basis="已核对 INN、登记名称与企业公开资料，未发现其他别名"
    )
    assert project.aliases == ()
    with pytest.raises(ValidationError):
        _complete_project(aliases=("Dupixent",), aliases_absence_basis="未发现别名")


def test_excluded_or_pending_eligibility_cannot_enter_contract() -> None:
    """只有已通过创新本体资格的项目可以进入 A 项目合同。"""
    with pytest.raises(ValidationError):
        _complete_project(eligibility="excluded")
    with pytest.raises(ValidationError):
        _complete_project(eligibility="review_pending")
    with pytest.raises(ValidationError):
        _complete_project(eligibility_policy_id=" ")


def test_manual_maturity_and_result_bearing_fields_are_rejected() -> None:
    """手工填写成熟度/result-bearing 的自由字段成为 extra 并被拒绝。"""
    with pytest.raises(ValidationError):
        _complete_project(development_maturity=DevelopmentMaturity.APPROVED)
    with pytest.raises(ValidationError):
        _complete_project(result_bearing=True)
    with pytest.raises(ValidationError):
        _complete_project(result_bearing_basis_ids=("basis-1",))


def test_unknown_inactive_predicate_and_event_mismatch_fail_closed() -> None:
    """停止开发状态必须由快照声明的谓词及相符监管事件共同支持。"""
    project = _terminated_project()
    unknown_snapshot = _snapshot(product_ids=("p-terminated",), trial_ids=("NCT-term-1",))
    with pytest.raises(GateEvaluationError):
        _evaluate(project, snapshot=unknown_snapshot, bindings=_terminated_bindings())

    mismatched = _complete_project(
        project_id="p-terminated",
        canonical_name="事件不匹配药",
        core_trials=project.core_trials,
        regulatory_events=(
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.APPROVAL,
                jurisdiction=_field(value="境外"),
                event_date=_field(value="2023-11-01"),
            ),
        ),
        anchor_trials=(),
    )
    with pytest.raises(GateEvaluationError):
        _evaluate(
            mismatched,
            snapshot=_terminated_snapshot(),
            bindings=_terminated_bindings(),
        )


# ── 成熟度分层：逐层递增必需字段 ───────────────────────────────────────────


def test_ladder_required_fields_increase_layer_by_layer() -> None:
    """每一层都严格增加必需字段；不适用显式表达字段随层声明。"""
    assert_ladder_monotonic()
    base = set(required_fields_for(MaturityLevel.ALL_PROJECTS))
    clinical = set(required_fields_for(MaturityLevel.CLINICAL))
    filing = set(required_fields_for(MaturityLevel.FILING_APPROVAL_TERMINATION))
    result = set(required_fields_for(MaturityLevel.RESULT_BEARING))
    assert clinical > base
    assert filing > clinical
    assert result > filing


def test_required_field_registry_is_complete_and_disjoint_by_layer() -> None:
    """规格注册表覆盖全部必需字段键，且每键只归属一个成熟度层。"""
    from ci_workflow.reports.a.contracts import REQUIRED_FIELD_SPECS

    keys = {spec.key for spec in REQUIRED_FIELD_SPECS}
    assert keys == set(RequiredFieldKey)
    layers = {spec.layer for spec in REQUIRED_FIELD_SPECS}
    assert layers == set(MaturityLevel)
    for key in RequiredFieldKey:
        owners = [spec for spec in REQUIRED_FIELD_SPECS if spec.key is key]
        assert len(owners) == 1


def test_maturity_level_is_derived_from_accepted_verdicts() -> None:
    """成熟度分层由开发成熟度与结果承载判定推导，且逐层单调。"""
    assert (
        determine_maturity_level(DevelopmentMaturity.APPROVED, True) is MaturityLevel.RESULT_BEARING
    )
    assert determine_maturity_level(DevelopmentMaturity.CLINICAL, False) is MaturityLevel.CLINICAL
    assert (
        determine_maturity_level(DevelopmentMaturity.SUBMISSION, False)
        is MaturityLevel.FILING_APPROVAL_TERMINATION
    )
    assert (
        determine_maturity_level(DevelopmentMaturity.PRECLINICAL, False)
        is MaturityLevel.ALL_PROJECTS
    )
    result = _evaluate(_complete_project())
    assert result.maturity_level is MaturityLevel.RESULT_BEARING
    clinical = _evaluate(
        _clinical_project(),
        snapshot=_clinical_snapshot(),
        bindings=_clinical_bindings(),
    )
    assert clinical.maturity_level is MaturityLevel.CLINICAL
    preclinical = _evaluate(
        _preclinical_project(),
        snapshot=_preclinical_snapshot(),
        bindings=(),
    )
    assert preclinical.maturity_level is MaturityLevel.ALL_PROJECTS


# ── L1 所有项目 ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("override", "expected_key"),
    [
        (
            {"target_mechanism": _field(state=EvidenceFieldState.NOT_YET_DISCLOSED)},
            TARGET_MECHANISM,
        ),
        (
            {"modality": _field(state=EvidenceFieldState.SOURCE_NOT_LISTED)},
            MODALITY,
        ),
        (
            {"developer": _field(state=EvidenceFieldState.NOT_YET_DISCLOSED)},
            DEVELOPER_ORIGINATOR,
        ),
        (
            {"originator": _field(state=EvidenceFieldState.NOT_YET_DISCLOSED)},
            DEVELOPER_ORIGINATOR,
        ),
        (
            {"indication_relation": _field(state=EvidenceFieldState.NOT_YET_DISCLOSED)},
            INDICATION_RELATION,
        ),
        (
            {
                "china": {
                    **_region("上市", "已批准", "2020-06-19"),
                    "date": _field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
                }
            },
            CHINA_STAGE_STATUS_DATE,
        ),
        (
            {
                "overseas": {
                    **_region("上市", "已批准", "2017-03-28"),
                    "highest_status": _field(state=EvidenceFieldState.SOURCE_NOT_LISTED),
                }
            },
            OVERSEAS_STAGE_STATUS_DATE,
        ),
    ],
)
def test_l1_required_field_missing_blocks_independently(
    override: dict[str, object], expected_key: RequiredFieldKey
) -> None:
    """第一层必需字段各自独立必填：未公开/检索后未找到即阻断，不合并掩盖。"""
    result = _evaluate(_complete_project(**override))
    assert result.blocked
    assert expected_key in _missing_keys(result)


def test_l1_region_requires_stage_status_date_together_or_uniform_not_applicable() -> None:
    """区域阶段/状态/日期要么齐备，要么整组显式声明不适用；混合即缺失。"""
    china_only = _complete_project(
        overseas={
            "highest_stage": _field(state=EvidenceFieldState.NOT_APPLICABLE),
            "highest_status": _field(state=EvidenceFieldState.NOT_APPLICABLE),
            "date": _field(state=EvidenceFieldState.NOT_APPLICABLE),
        }
    )
    result = _evaluate(china_only)
    assert not result.blocked
    assert OVERSEAS_STAGE_STATUS_DATE not in _missing_keys(result)

    mixed = _complete_project(
        overseas={
            "highest_stage": _field(value="临床 III 期"),
            "highest_status": _field(value="进行中"),
            "date": _field(state=EvidenceFieldState.NOT_APPLICABLE),
        }
    )
    assert OVERSEAS_STAGE_STATUS_DATE in _missing_keys(_evaluate(mixed))


def test_not_applicable_is_rejected_where_ladder_does_not_allow_it() -> None:
    """不适用只能在规格声明允许的字段使用；靶点/机制等不允许以不适用冒充。"""
    project = _complete_project(target_mechanism=_field(state=EvidenceFieldState.NOT_APPLICABLE))
    result = _evaluate(project)
    assert result.blocked
    assert TARGET_MECHANISM in _missing_keys(result)


def test_developer_originator_na_blocked_for_active_projects() -> None:
    """上市/申报/临床等非终止项目不允许当前开发者/原研方整组不适用。"""
    project = _complete_project(
        developer=_field(state=EvidenceFieldState.NOT_APPLICABLE),
        originator=_field(state=EvidenceFieldState.NOT_APPLICABLE),
    )
    result = _evaluate(project)
    assert result.blocked
    assert DEVELOPER_ORIGINATOR in _missing_keys(result)

    half = _complete_project(
        developer=_field(value="赛诺菲"),
        originator=_field(state=EvidenceFieldState.NOT_APPLICABLE),
    )
    assert DEVELOPER_ORIGINATOR in _missing_keys(_evaluate(half))


def test_developer_originator_na_allowed_only_for_terminated_whole_group() -> None:
    """暂停/终止/撤回项目允许当前开发者/原研方整组显式不适用。"""
    project = _terminated_project(
        developer=_field(state=EvidenceFieldState.NOT_APPLICABLE),
        originator=_field(state=EvidenceFieldState.NOT_APPLICABLE),
    )
    result = _evaluate(project, snapshot=_terminated_snapshot(), bindings=_terminated_bindings())
    assert not result.blocked
    assert DEVELOPER_ORIGINATOR not in _missing_keys(result)


def test_region_na_conflicts_with_same_region_regulatory_event() -> None:
    """中国/境外整组不适用若与同地域监管事件矛盾则阻断。"""
    china_na = _complete_project(
        china={
            "highest_stage": _field(state=EvidenceFieldState.NOT_APPLICABLE),
            "highest_status": _field(state=EvidenceFieldState.NOT_APPLICABLE),
            "date": _field(state=EvidenceFieldState.NOT_APPLICABLE),
        }
    )
    assert CHINA_STAGE_STATUS_DATE in _missing_keys(_evaluate(china_na))

    overseas_na = _complete_project(
        overseas={
            "highest_stage": _field(state=EvidenceFieldState.NOT_APPLICABLE),
            "highest_status": _field(state=EvidenceFieldState.NOT_APPLICABLE),
            "date": _field(state=EvidenceFieldState.NOT_APPLICABLE),
        },
        regulatory_events=(
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.APPROVAL,
                jurisdiction=_field(value="境外"),
                event_date=_field(value="2017-03-28"),
            ),
        ),
    )
    assert OVERSEAS_STAGE_STATUS_DATE in _missing_keys(_evaluate(overseas_na))


# ── L2 临床项目 ─────────────────────────────────────────────────────────────


def test_clinical_project_requires_core_trial_identity_role_and_status() -> None:
    """临床项目缺少核心试验身份/角色/状态分别阻断；临床前项目不因无试验失败。"""
    clinical = _clinical_project(core_trials=())
    result = _evaluate(clinical, snapshot=_clinical_snapshot(), bindings=_clinical_bindings())
    assert result.blocked
    assert {
        CORE_TRIAL_IDENTITY,
        CORE_TRIAL_DEVELOPMENT_ROLE,
        CORE_TRIAL_STATUS,
    } <= _missing_keys(result)

    preclinical = _evaluate(
        _preclinical_project(),
        snapshot=_preclinical_snapshot(),
        bindings=(),
    )
    assert not preclinical.blocked


def test_clinical_project_with_complete_trial_passes_l2() -> None:
    """临床项目核心试验齐备且无申报事件时，不因缺少申报字段失败。"""
    result = _evaluate(
        _clinical_project(),
        snapshot=_clinical_snapshot(),
        bindings=_clinical_bindings(),
    )
    assert not result.blocked
    assert REGULATORY_EVENT not in _missing_keys(result)


def test_core_trial_outside_snapshot_fails_closed() -> None:
    """核心试验引用未知试验对象必须失败关闭，不得进入门槛判定。"""
    project = _clinical_project(
        core_trials=(
            CoreTrialRecord(
                trial_id="NCT-unknown",
                role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                status="进行中",
            ),
        )
    )
    with pytest.raises(GateEvaluationError):
        _evaluate(project, snapshot=_clinical_snapshot(), bindings=_clinical_bindings())


def test_core_trial_of_other_product_fails_closed() -> None:
    """核心试验属于其他产品必须失败关闭，不得跨产品拼接。"""
    snapshot = _snapshot(
        product_ids=("p-clinical", "p-other"),
        trial_ids=("NCT-clin-1", "NCT-other-1"),
        trial_products={"NCT-clin-1": "p-clinical", "NCT-other-1": "p-other"},
    )
    project = _clinical_project(
        core_trials=(
            CoreTrialRecord(
                trial_id="NCT-other-1",
                role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                status="进行中",
            ),
        )
    )
    with pytest.raises(GateEvaluationError):
        _evaluate(project, snapshot=snapshot, bindings=_clinical_bindings())


# ── L3 申报/上市/终止项目 ───────────────────────────────────────────────────


def test_filing_project_requires_regulatory_events_with_jurisdiction_and_date() -> None:
    """申报/上市/终止项目缺事件、地域或日期分别阻断。"""
    no_events = _complete_project(regulatory_events=())
    result = _evaluate(no_events)
    assert result.blocked
    assert {
        REGULATORY_EVENT,
        REGULATORY_EVENT_JURISDICTION,
        REGULATORY_EVENT_DATE,
    } <= _missing_keys(result)

    missing_jurisdiction = _complete_project(
        regulatory_events=(
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.APPROVAL,
                jurisdiction=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
                event_date=_field(value="2020-06-19"),
            ),
        )
    )
    assert REGULATORY_EVENT_JURISDICTION in _missing_keys(_evaluate(missing_jurisdiction))


def test_regulatory_jurisdiction_and_date_require_same_event() -> None:
    """地域与日期必须由同一条监管事件同时满足，不得跨事件拼接。"""
    stitched = _complete_project(
        regulatory_events=(
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.APPROVAL,
                jurisdiction=_field(value="中国"),
                event_date=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
            ),
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.APPROVAL,
                jurisdiction=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
                event_date=_field(value="2020-06-19"),
            ),
        )
    )
    result = _evaluate(stitched)
    assert REGULATORY_EVENT_JURISDICTION in _missing_keys(result)
    assert REGULATORY_EVENT_DATE in _missing_keys(result)

    complete = _complete_project(
        regulatory_events=(
            RegulatoryEventRecord(
                event_kind=RegulatoryEventKind.APPROVAL,
                jurisdiction=_field(value="中国"),
                event_date=_field(value="2020-06-19"),
            ),
        )
    )
    assert REGULATORY_EVENT_JURISDICTION not in _missing_keys(_evaluate(complete))
    assert REGULATORY_EVENT_DATE not in _missing_keys(_evaluate(complete))


def test_terminated_project_keeps_termination_event_requirement() -> None:
    """终止/放弃项目仍属申报层：事件与地域缺失阻断，不允许当临床项目放行。"""
    terminated = _terminated_project(regulatory_events=())
    result = _evaluate(terminated, snapshot=_terminated_snapshot(), bindings=_terminated_bindings())
    assert result.blocked
    assert REGULATORY_EVENT in _missing_keys(result)


# ── L4 已公开结果的成熟项目 ─────────────────────────────────────────────────


def test_result_bearing_project_requires_anchor_efficacy_and_safety_summary() -> None:
    """结果承载项目缺锚定试验、核心疗效记录或 TEAE/SAE 数值摘要即阻断。"""
    no_anchor = _complete_project(anchor_trials=())
    result = _evaluate(no_anchor)
    assert ANCHOR_TRIAL in _missing_keys(result)
    assert CORE_EFFICACY_RECORD in _missing_keys(result)
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)

    regulatory, efficacy, safety = _default_bindings()
    no_efficacy = _evaluate(_complete_project(), bindings=(regulatory, safety))
    assert CORE_EFFICACY_RECORD in _missing_keys(no_efficacy)

    no_safety = _evaluate(_complete_project(), bindings=(regulatory, efficacy))
    assert SAFETY_SUMMARY_RECORD in _missing_keys(no_safety)


def test_result_bearing_project_with_complete_records_passes() -> None:
    """锚定试验、核心疗效记录与 TEAE/SAE 数值摘要齐备时第四层放行。"""
    result = _evaluate(_complete_project())
    assert not result.blocked
    assert ANCHOR_TRIAL not in _missing_keys(result)
    assert CORE_EFFICACY_RECORD not in _missing_keys(result)
    assert SAFETY_SUMMARY_RECORD not in _missing_keys(result)


# ── 防降级与稳定身份 ────────────────────────────────────────────────────────


def test_evaluation_has_no_skip_drop_or_override_parameters() -> None:
    """评估接口只消费项目与强输入：不存在跳过、删除或降级出口。"""
    assert set(inspect.signature(evaluate_maturity_gate).parameters) == {
        "project",
        "snapshot",
        "bindings",
        "results_posted_evidence",
    }
    assert set(inspect.signature(determine_maturity_level).parameters) == {
        "maturity",
        "result_bearing",
    }


def test_evaluation_preserves_identity_and_is_deterministic() -> None:
    """评估不重命名、不重排、不删除项目；同输入两次结果一致。"""
    project = _complete_project()
    first = _evaluate(project)
    second = _evaluate(project)
    assert first == second
    assert first.project_id == project.project_id == "project-dupilumab"
    assert project.canonical_name == "度普利尤单抗"
    assert project.aliases == ("Dupixent", "Dupilumab")


def test_blocked_result_carries_chinese_medical_reasons() -> None:
    """阻断原因使用中文临床开发语言，不暴露工程状态。"""
    with pytest.raises(ValidationError):
        _complete_project(safety_summaries=())
    blocked = _complete_project(
        target_mechanism=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
    )
    result = _evaluate(blocked)
    reasons = "".join(item.reason_zh for item in result.missing_fields)
    assert any("\u4e00" <= ch <= "\u9fff" for ch in reasons)
    assert "靶点" in reasons
