"""Task 5.1 result-bearing 确定性触发与疗效/TEAE-SAE 最低记录失败测试（强输入）。

合同断言（先失败后通过）：
- result_bearing 只由 Phase 3 已接受绑定确定性触发：监管材料、主要试验报告、
  会议/公司数值披露、指定权威来源出现可归属该适应症试验的观察性数值结果；
  计划值、目标值与方案假设不得触发；候选/未接受事实不得触发；
- 官方登记"已发布结果"由强类型只读证据触发（RegistryResultsPostedEvidence）：
  绑定产品、试验、事实版本、精确来源定位、官方登记来源、已接受状态与
  ``Literal[True]`` 标志；不得用自由布尔或未知试验；
- 触发后每个成熟项目最低记录直接从已接受绑定判定：真实有限数值（已报告零值
  必须是数值零）、正分母、完整定义/单位/时间点/分析人群/治疗组、精确来源定位，
  且试验属于本产品与快照并与适格锚定试验一致；安全性必须 SAFETY 域且 TEAE/SAE
  封闭单位；对照组仅单臂设计可缺省；
- 跨产品试验、未知试验、锚定试验非核心试验均失败关闭；
- 阻断不删除、不降级：项目身份与成熟度层保持稳定。
"""

from __future__ import annotations

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
    evaluate_maturity_gate,
)
from ci_workflow.reports.a.contracts import (
    ANCHOR_TRIAL,
    CORE_EFFICACY_RECORD,
    SAFETY_SUMMARY_RECORD,
    AnchorTrialRecord,
    AProjectContract,
    CoreTrialRecord,
    CoreTrialRole,
    MaturityLevel,
    RegistryResultsPostedEvidence,
    RegulatoryEventKind,
    RegulatoryEventRecord,
    RequiredFieldKey,
    SafetyEventUnitId,
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
    endpoint_ids: tuple[str, ...] = (),
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
    for endpoint_id in endpoint_ids:
        edges.append(
            UniverseEdge(
                parent_type=GateObjectType.TRIAL,
                parent_id=trial_ids[0],
                child_type=GateObjectType.ENDPOINT,
                child_id=endpoint_id,
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
        GateObjectType.COMPARISON: tuple(comparison_ids),
        GateObjectType.GROUP: tuple(group_ids),
        GateObjectType.ENDPOINT: endpoint_ids,
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
        endpoint_ids=endpoint_ids,
        empty_set_proofs=tuple(empty_proofs),
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id="ind-rule-1",
    )
    return ApplicableUniverseSnapshot(
        project_id=project_id,
        evidence_snapshot_id="snap-ev-1",
        research_role_set_id="role-set-1",
        product_ids=product_ids,
        trial_ids=trial_ids,
        comparison_ids=tuple(comparison_ids),
        group_ids=tuple(group_ids),
        endpoint_ids=endpoint_ids,
        empty_set_proofs=tuple(empty_proofs),
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id="ind-rule-1",
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


def _efficacy(**overrides: object) -> GateEvidenceBinding:
    return _binding(**{"fact_version_id": "fact-v-2", **overrides})


def _safety(**overrides: object) -> GateEvidenceBinding:
    return _binding(
        **{
            "binding_id": "b-saf",
            "fact_version_id": "fact-v-3",
            "fact_domain": FactDomain.SAFETY,
            "unit_id": SafetyEventUnitId.TEAE.value,
            "unit": "%",
            "definition": None,
            "direction": None,
            "timepoint": None,
            "event_definition": "治疗期间不良事件",
            "time_window": "治疗期间",
            **overrides,
        }
    )


def _regulatory(**overrides: object) -> GateEvidenceBinding:
    return _binding(
        **{
            "binding_id": "b-reg",
            "fact_version_id": "fact-v-1",
            "source_role": SourceRole.REGULATORY_MATERIAL,
            "definition": None,
            "direction": None,
            "timepoint": None,
            "analysis_population": None,
            "treatment_group": None,
            **overrides,
        }
    )


def _flag(
    *,
    project_id: str = "project-dupilumab",
    trial_id: str = "NCT02407756",
    fact_version_id: str = "flag-fact-1",
) -> RegistryResultsPostedEvidence:
    return RegistryResultsPostedEvidence(
        project_id=project_id,
        trial_id=trial_id,
        fact_version_id=fact_version_id,
        source_location="CT.gov/results/ver-2",
    )


def _flag_binding(flag: RegistryResultsPostedEvidence) -> GateEvidenceBinding:
    return _binding(
        binding_id=f"binding-{flag.fact_version_id}",
        unit_id="a_registry_results_posted",
        object_id=flag.project_id,
        trial_id=flag.trial_id,
        fact_version_id=flag.fact_version_id,
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        unit=None,
        denominator=None,
        definition="官方登记已发布结果",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
        source_location=flag.source_location,
    )


def _complete_bindings() -> tuple[GateEvidenceBinding, ...]:
    """默认已接受绑定：批准（监管观察值）+ 核心疗效 + TEAE 摘要。"""
    return (_regulatory(), _efficacy(), _safety())


def _evaluate(
    project: AProjectContract,
    *,
    snapshot: ApplicableUniverseSnapshot | None = None,
    bindings: tuple[GateEvidenceBinding, ...] | None = None,
    flag_evidence: tuple[RegistryResultsPostedEvidence, ...] = (),
) -> MaturityGateResult:
    if snapshot is None:
        snapshot = _snapshot()
    if bindings is None:
        bindings = _complete_bindings()
    for flag in flag_evidence:
        if not any(binding.fact_version_id == flag.fact_version_id for binding in bindings):
            bindings = (*bindings, _flag_binding(flag))
    return evaluate_maturity_gate(project, snapshot, bindings, flag_evidence)


def _missing_keys(result: MaturityGateResult) -> frozenset[RequiredFieldKey]:
    return frozenset(result.missing_keys)


# ── 确定性触发：只由已接受观察性数值绑定触发 ──────────────────────────────


def test_accepted_efficacy_binding_triggers_result_bearing() -> None:
    """已接受、已报告、可归属适格试验的疗效数值绑定确定性触发。"""
    result = _evaluate(_complete_project())
    assert result.result_bearing is True
    assert result.maturity_level is MaturityLevel.RESULT_BEARING


def test_trial_scoped_results_are_kept_for_their_product() -> None:
    """试验级已接受结果不得被产品级筛选器误删。"""
    efficacy = _efficacy(object_id="NCT02407756")
    safety = _safety(object_id="NCT02407756")
    result = _evaluate(_complete_project(), bindings=(_regulatory(), efficacy, safety))
    assert result.result_bearing is True
    assert result.blocked is False


def test_endpoint_scoped_result_can_anchor_its_trial() -> None:
    """同一适格试验的终点级事实可作为锚定证据，不被对象层级误拒。"""
    snapshot = _snapshot(endpoint_ids=("endpoint-core-1",))
    efficacy = GateEvidenceBinding.model_validate(
        {
            **_efficacy(fact_version_id="fact-endpoint").model_dump(),
            "object_id": "endpoint-core-1",
            "endpoint_id": "endpoint-core-1",
        }
    )
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("fact-endpoint",)),
        ),
    )
    result = _evaluate(project, snapshot=snapshot, bindings=(_regulatory(), efficacy, _safety()))
    assert not result.blocked


def test_protocol_or_sap_numeric_rows_cannot_satisfy_result_minimums() -> None:
    """方案/SAP 中的计划或误标数值不得冒充实际疗效、安全性结果。"""
    efficacy_from_protocol = _efficacy(source_role=SourceRole.PROTOCOL_SAP)
    result = _evaluate(
        _complete_project(),
        bindings=(_regulatory(), efficacy_from_protocol, _safety()),
    )
    assert CORE_EFFICACY_RECORD in _missing_keys(result)
    safety_from_protocol = _safety(source_role=SourceRole.PROTOCOL_SAP)
    result = _evaluate(
        _complete_project(),
        bindings=(_regulatory(), _efficacy(), safety_from_protocol),
    )
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)


def test_boolean_numeric_value_and_denominator_are_rejected() -> None:
    """布尔值不得被偷转成 0/1 后冒充临床数值或分母。"""
    with pytest.raises(ValidationError):
        _efficacy(numeric_value=False)
    with pytest.raises(ValidationError):
        _efficacy(denominator=True)


def test_single_project_must_belong_to_snapshot() -> None:
    """单项目入口也必须绑定当前闭合产品清单。"""
    with pytest.raises(GateEvaluationError):
        _evaluate(_complete_project(project_id="not-in-snapshot"), bindings=())


def test_dormant_core_or_anchor_trial_is_still_scope_checked() -> None:
    """早期项目携带的越界高层记录不得因当前层级较低而逃过校验。"""
    foreign_core = CoreTrialRecord(
        trial_id="NCT-foreign",
        role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
        status="已完成",
    )
    with pytest.raises(GateEvaluationError):
        _evaluate(
            _complete_project(core_trials=(foreign_core,), anchor_trials=()),
            bindings=(),
        )
    with pytest.raises(GateEvaluationError):
        _evaluate(
            _complete_project(
                core_trials=(),
                anchor_trials=(
                    AnchorTrialRecord(trial_id="NCT-foreign", fact_version_ids=("fact-x",)),
                ),
            ),
            bindings=(),
        )


def test_safety_event_kind_uses_rule_unit_not_measurement_unit() -> None:
    """TEAE/SAE 类别写入规则单元，发生率单位仍为百分比。"""
    valid = _safety(unit_id=SafetyEventUnitId.TEAE.value, unit="%")
    assert not _evaluate(_complete_project(), bindings=(_regulatory(), _efficacy(), valid)).blocked
    misplaced = _safety(unit_id="a-unit-1", unit="teae")
    result = _evaluate(_complete_project(), bindings=(_regulatory(), _efficacy(), misplaced))
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)


def test_candidate_binding_never_triggers() -> None:
    """候选/未接受事实不触发结果承载。"""
    bindings = (
        _efficacy(review_state=FactReviewState.CANDIDATE),
        _safety(review_state=FactReviewState.CANDIDATE),
    )
    result = _evaluate(_complete_project(anchor_trials=()), bindings=bindings)
    assert result.result_bearing is False
    assert result.maturity_level is not MaturityLevel.RESULT_BEARING


@pytest.mark.parametrize(
    "observation_kind",
    [
        ObservationKind.PLANNED_VALUE,
        ObservationKind.TARGET_VALUE,
        ObservationKind.PROTOCOL_ASSUMPTION,
    ],
)
def test_planned_target_and_assumption_values_never_trigger(
    observation_kind: ObservationKind,
) -> None:
    """计划值、目标值与方案假设不得触发结果承载。"""
    bindings = (
        _efficacy(observation_kind=observation_kind, fact_version_id="fact-v-1"),
        _safety(observation_kind=observation_kind),
    )
    result = _evaluate(_complete_project(), bindings=bindings)
    assert result.result_bearing is False
    assert result.maturity_level is not MaturityLevel.RESULT_BEARING


def test_trial_design_fact_never_triggers() -> None:
    """设计域事实（非疗效/安全数值）不触发结果承载。"""
    bindings = (
        _binding(
            fact_domain=FactDomain.TRIAL_DESIGN,
            definition="随机对照试验设计",
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
        ),
    )
    result = _evaluate(_complete_project(), bindings=bindings)
    assert result.result_bearing is False


def test_manual_result_bearing_fields_are_rejected_as_extra() -> None:
    """A 项目合同不存在自由 result-bearing 字段；手工填写即拒绝。"""
    with pytest.raises(ValidationError):
        _complete_project(result_bearing=True)
    with pytest.raises(ValidationError):
        _complete_project(result_bearing_basis_ids=("basis-1",))
    with pytest.raises(ValidationError):
        _complete_project(development_maturity=DevelopmentMaturity.APPROVED)


def test_registry_results_posted_evidence_is_strictly_typed() -> None:
    """已发布结果证据是强类型只读合同：标志、来源、状态均为字面量。"""
    with pytest.raises(ValidationError):
        RegistryResultsPostedEvidence(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="flag-fact-1",
            source_location="CT.gov/results/ver-2",
            official_results_posted=False,
        )
    with pytest.raises(ValidationError):
        RegistryResultsPostedEvidence(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="flag-fact-1",
            source_location="CT.gov/results/ver-2",
            source_role=SourceRole.REGULATORY_MATERIAL,
        )
    with pytest.raises(ValidationError):
        RegistryResultsPostedEvidence(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="flag-fact-1",
            source_location="CT.gov/results/ver-2",
            review_state=FactReviewState.CANDIDATE,
        )
    with pytest.raises(ValidationError):
        RegistryResultsPostedEvidence(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="flag-fact-1",
            source_location=" ",
        )


def test_results_posted_flag_triggers_without_numeric_values() -> None:
    """官方登记已发布结果标志单独即触发结果承载。"""
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("flag-fact-1",)),
        ),
    )
    result = _evaluate(project, bindings=(), flag_evidence=(_flag(),))
    assert result.result_bearing is True
    assert result.maturity_level is MaturityLevel.RESULT_BEARING


def test_results_posted_flag_requires_matching_accepted_registry_binding() -> None:
    """强类型标志仍必须解析到 Phase 3 已接受事实，任意事实号不得触发。"""
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("flag-fact-1",)),
        ),
    )
    with pytest.raises(GateEvaluationError):
        evaluate_maturity_gate(project, _snapshot(), (), (_flag(),))


def test_flag_trigger_with_incomplete_values_enters_recovery_not_no_result_layer() -> None:
    """标志触发后若疗效/安全性值不完整，门槛阻断且成熟度保持结果层。"""
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("flag-fact-1",)),
        ),
    )
    result = _evaluate(project, bindings=(), flag_evidence=(_flag(),))
    assert result.result_bearing is True
    assert result.maturity_level is MaturityLevel.RESULT_BEARING
    assert result.blocked
    assert CORE_EFFICACY_RECORD in _missing_keys(result)
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)
    assert ANCHOR_TRIAL not in _missing_keys(result)


def test_flag_with_unknown_trial_fails_closed() -> None:
    """已发布结果证据引用未知试验必须失败关闭。"""
    flag = _flag(trial_id="NCT-unknown")
    with pytest.raises(GateEvaluationError):
        _evaluate(_complete_project(), bindings=(), flag_evidence=(flag,))


def test_flag_with_cross_product_trial_fails_closed() -> None:
    """已发布结果证据引用其他产品的试验必须失败关闭。"""
    snapshot = _snapshot(
        product_ids=("project-dupilumab", "p-other"),
        trial_ids=("NCT02407756", "NCT-other-1"),
        trial_products={"NCT02407756": "project-dupilumab", "NCT-other-1": "p-other"},
    )
    flag = _flag(trial_id="NCT-other-1")
    with pytest.raises(GateEvaluationError):
        _evaluate(_complete_project(), snapshot=snapshot, bindings=(), flag_evidence=(flag,))


def test_cross_product_binding_fails_closed() -> None:
    """产品级绑定引用其他产品的试验必须失败关闭。"""
    snapshot = _snapshot(
        product_ids=("project-dupilumab", "p-other"),
        trial_ids=("NCT02407756", "NCT-other-1"),
        trial_products={"NCT02407756": "project-dupilumab", "NCT-other-1": "p-other"},
    )
    bindings = (_efficacy(trial_id="NCT-other-1"),)
    with pytest.raises(GateEvaluationError):
        _evaluate(_complete_project(), snapshot=snapshot, bindings=bindings)


# ── 疗效最低记录：真实数值、正分母、完整成分、锚定试验一致 ────────────────


def test_reported_value_without_numeric_value_blocks() -> None:
    """已报告值但无数值的事实不构成疗效记录：结果承载后阻断。"""
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("flag-fact-1",)),
        ),
    )
    bindings = (_efficacy(numeric_value=None), _safety())
    result = _evaluate(project, bindings=bindings, flag_evidence=(_flag(),))
    assert result.result_bearing is True
    assert CORE_EFFICACY_RECORD in _missing_keys(result)


def test_reported_zero_is_complete_and_zero_is_real() -> None:
    """已报告零值必须是数值零并携带零值原文；零是确定数值不是缺失。"""
    zero_binding = _efficacy(
        disclosure_state=FactDisclosureState.REPORTED_ZERO,
        numeric_value=0,
        reported_zero_text="报告 0 例应答",
        fact_version_id="fact-zero",
    )
    project = _complete_project(
        anchor_trials=(AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("fact-zero",)),),
    )
    result = _evaluate(project, bindings=(zero_binding, _safety()))
    assert not result.blocked
    assert CORE_EFFICACY_RECORD not in _missing_keys(result)

    value_zero = _efficacy(
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        numeric_value=0,
        fact_version_id="fact-zero-value",
    )
    project2 = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("fact-zero-value",)),
        ),
    )
    result2 = _evaluate(project2, bindings=(value_zero, _safety()))
    assert not result2.blocked


def test_denominator_missing_blocks() -> None:
    """疗效/安全数值记录分母缺失（不适用/空白）即阻断，不允许冒充。"""
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("flag-fact-1",)),
        ),
    )
    bindings = (_efficacy(denominator=None), _safety())
    result = _evaluate(project, bindings=bindings, flag_evidence=(_flag(),))
    assert CORE_EFFICACY_RECORD in _missing_keys(result)

    bindings_safety = (_efficacy(), _safety(denominator=None))
    result_safety = _evaluate(project, bindings=bindings_safety, flag_evidence=(_flag(),))
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result_safety)


def test_single_arm_allows_missing_control_group() -> None:
    """单臂设计试验允许对照组缺省；疗效与安全性记录仍完整。"""
    result = _evaluate(_complete_project())
    assert not result.blocked


def test_comparative_requires_control_group() -> None:
    """比较设计试验必须提供对照组；缺失即疗效记录不完整。"""
    snapshot = _snapshot(
        design_kinds={"NCT02407756": TrialDesignKind.COMPARATIVE},
        comparison_groups={
            "NCT02407756": {"cmp-1": ("g-treat", "g-ctrl")},
        },
    )
    bindings = (_regulatory(), _efficacy(control_group=None), _safety(control_group=None))
    project = _complete_project()
    result = _evaluate(project, snapshot=snapshot, bindings=bindings)
    assert result.result_bearing is True
    assert CORE_EFFICACY_RECORD in _missing_keys(result)
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)

    complete = _evaluate(
        project,
        snapshot=snapshot,
        bindings=(
            _regulatory(),
            _efficacy(control_group="安慰剂"),
            _safety(control_group="安慰剂"),
        ),
    )
    assert not complete.blocked


def test_anchor_must_be_a_core_trial_fails_closed() -> None:
    """适格锚定试验必须是本产品核心试验；不一致失败关闭。"""
    project = _complete_project(
        anchor_trials=(AnchorTrialRecord(trial_id="NCT-other", fact_version_ids=("fact-v-2",)),),
    )
    with pytest.raises(GateEvaluationError):
        _evaluate(project)


def test_anchor_evidence_must_resolve_to_accepted_bindings_fails_closed() -> None:
    """锚定试验证据版本必须能在已接受绑定或已发布结果证据中找到。"""
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("forged-fragment",)),
        ),
    )
    with pytest.raises(GateEvaluationError):
        _evaluate(project)


def test_efficacy_from_non_anchor_trial_blocks() -> None:
    """疗效记录来自非锚定试验不能构成最低记录：结果承载后阻断。"""
    snapshot = _snapshot(
        trial_ids=("NCT02407756", "NCT-second-1"),
        design_kinds={
            "NCT02407756": TrialDesignKind.SINGLE_ARM,
            "NCT-second-1": TrialDesignKind.SINGLE_ARM,
        },
    )
    project = _complete_project(
        core_trials=(
            CoreTrialRecord(
                trial_id="NCT02407756", role=CoreTrialRole.REGISTRATION_OR_PIVOTAL, status="已完成"
            ),
            CoreTrialRecord(
                trial_id="NCT-second-1", role=CoreTrialRole.SUPPORTING, status="已完成"
            ),
        ),
    )
    anchor_design = _binding(
        binding_id="b-design",
        fact_domain=FactDomain.TRIAL_DESIGN,
        definition="核心试验设计",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,
        fact_version_id="fact-v-1",
        source_role=SourceRole.PROTOCOL_SAP,
    )
    bindings = (
        anchor_design,
        _efficacy(trial_id="NCT-second-1", fact_version_id="fact-second"),
        _safety(),
    )
    result = _evaluate(project, snapshot=snapshot, bindings=bindings)
    assert result.result_bearing is True
    assert CORE_EFFICACY_RECORD in _missing_keys(result)


def test_safety_from_non_anchor_trial_blocks() -> None:
    """安全性记录来自非锚定试验不能构成最低记录：结果承载后阻断。"""
    snapshot = _snapshot(
        trial_ids=("NCT02407756", "NCT-second-1"),
        design_kinds={
            "NCT02407756": TrialDesignKind.SINGLE_ARM,
            "NCT-second-1": TrialDesignKind.SINGLE_ARM,
        },
    )
    project = _complete_project(
        core_trials=(
            CoreTrialRecord(
                trial_id="NCT02407756", role=CoreTrialRole.REGISTRATION_OR_PIVOTAL, status="已完成"
            ),
            CoreTrialRecord(
                trial_id="NCT-second-1", role=CoreTrialRole.SUPPORTING, status="已完成"
            ),
        ),
    )
    bindings = (
        _regulatory(),
        _efficacy(),
        _safety(trial_id="NCT-second-1", fact_version_id="fact-second-safety"),
    )
    result = _evaluate(project, snapshot=snapshot, bindings=bindings)
    assert result.result_bearing is True
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)


# ── 安全性最低记录：封闭 TEAE/SAE 单位与完整成分 ──────────────────────────


def test_safety_requires_closed_teae_sae_unit() -> None:
    """安全性最低记录只认封闭的 TEAE/SAE 规则单元；任意单元不得冒充。"""
    bindings = (_regulatory(), _efficacy(), _safety(unit_id="a_safety_event_other"))
    result = _evaluate(_complete_project(), bindings=bindings)
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)


def test_aesi_does_not_satisfy_teae_sae_minimum() -> None:
    """安全性最低记录必须是 TEAE 或 SAE；仅有 AESI 行仍阻断。"""
    bindings = (_regulatory(), _efficacy(), _safety(unit_id="a_safety_event_aesi"))
    result = _evaluate(_complete_project(), bindings=bindings)
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)


def test_sae_is_a_valid_minimum_unit() -> None:
    """SAE 是封闭单位之一，可满足安全性最低记录。"""
    bindings = (
        _regulatory(),
        _efficacy(),
        _safety(unit_id=SafetyEventUnitId.SAE.value),
    )
    result = _evaluate(_complete_project(), bindings=bindings)
    assert not result.blocked
    assert SAFETY_SUMMARY_RECORD not in _missing_keys(result)


def test_safety_record_requires_event_definition_and_time_window() -> None:
    """安全性记录缺事件定义或时间窗即不完整。"""
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("flag-fact-1",)),
        ),
    )
    no_definition = (_efficacy(), _safety(event_definition=None))
    result = _evaluate(project, bindings=no_definition, flag_evidence=(_flag(),))
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result)

    no_window = (_efficacy(), _safety(time_window=None))
    result_window = _evaluate(project, bindings=no_window, flag_evidence=(_flag(),))
    assert SAFETY_SUMMARY_RECORD in _missing_keys(result_window)


# ── 阻断不删除、不降级 ─────────────────────────────────────────────────────


def test_blocked_result_bearing_project_keeps_identity_level_and_missing_keys() -> None:
    """阻断不删除、不降级：项目身份与结果层保持，逐产品保留缺失诊断。"""
    project = _complete_project()
    bindings = (_regulatory(), _efficacy())
    result = _evaluate(project, bindings=bindings)
    assert result.blocked
    assert result.project_id == project.project_id == "project-dupilumab"
    assert result.maturity_level is MaturityLevel.RESULT_BEARING
    assert _missing_keys(result) == frozenset({SAFETY_SUMMARY_RECORD})
    assert "TEAE" in result.missing_fields[0].reason_zh
