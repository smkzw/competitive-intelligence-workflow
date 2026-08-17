"""Task 5.3 A 类疗效比较与安全性热图合同。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.gates.models import (
    FactDomain,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    SourceRole,
    TrialDesignKind,
    UniverseEdge,
    compute_universe_summary,
)
from ci_workflow.reports.a.analysis import (
    ArmRole,
    EfficacyMeasureRecord,
    EndpointDirection,
    EndpointFamilySpec,
    ProductResultState,
    SafetyFamily,
    SafetyMeasureRecord,
    TrialGroupRoleRecord,
    TrialSelectionRecord,
    assert_efficacy_safety_summary_authoritative,
    build_efficacy_safety_summary,
)
from ci_workflow.reports.a.contracts import AnchorTrialRecord, CoreTrialRole
from tests.reports.a.test_result_bearing_gate import (
    _binding,
    _complete_project,
    _efficacy,
    _regulatory,
    _safety,
    _snapshot,
)


def _comparative_snapshot():
    snapshot = _snapshot(
        design_kinds={"NCT02407756": TrialDesignKind.COMPARATIVE},
        comparison_groups={"NCT02407756": {"cmp-1": ("grp-active", "grp-control")}},
        endpoint_ids=("ep-easi75",),
    )
    edges = (
        *snapshot.relationship_edges,
        UniverseEdge(
            parent_type=GateObjectType.COMPARISON,
            parent_id="cmp-1",
            child_type=GateObjectType.ENDPOINT,
            child_id="ep-easi75",
        ),
        UniverseEdge(
            parent_type=GateObjectType.ENDPOINT,
            parent_id="ep-easi75",
            child_type=GateObjectType.GROUP,
            child_id="grp-active",
        ),
        UniverseEdge(
            parent_type=GateObjectType.ENDPOINT,
            parent_id="ep-easi75",
            child_type=GateObjectType.GROUP,
            child_id="grp-control",
        ),
    )
    summary = compute_universe_summary(
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
        relationship_edges=edges,
        trial_design_evidence=snapshot.trial_design_evidence,
        indication_rule_set_id=snapshot.indication_rule_set_id,
    )
    return snapshot.model_copy(update={"relationship_edges": edges, "universe_summary": summary})


def _scoped(
    binding: GateEvidenceBinding,
    *,
    fact: str,
    group: str,
    value: float | None,
):
    return GateEvidenceBinding.model_validate(
        {
            **binding.model_dump(),
            "binding_id": f"binding-{fact}",
            "fact_version_id": fact,
            "object_id": group,
            "comparison_id": "cmp-1",
            "group_id": group,
            "endpoint_id": "ep-easi75" if binding.fact_domain is FactDomain.EFFICACY else None,
            "numeric_value": value,
            "treatment_group": "度普利尤单抗" if group == "grp-active" else "安慰剂",
            "control_group": "安慰剂",
        }
    )


def _case():
    snapshot = _comparative_snapshot()
    efficacy_base = _efficacy(
        definition="湿疹面积和严重程度指数较基线改善至少75%",
        direction="应答率越高越好",
    )
    efficacy_active = _scoped(efficacy_base, fact="eff-active", group="grp-active", value=51.2)
    efficacy_control = _scoped(efficacy_base, fact="eff-control", group="grp-control", value=24.6)
    safety_active = _scoped(_safety(), fact="teae-active", group="grp-active", value=78.0)
    safety_control = _scoped(_safety(), fact="teae-control", group="grp-control", value=72.0)
    phase_fact = _binding(
        binding_id="binding-phase",
        unit_id="a_trial_phase",
        object_id="NCT02407756",
        fact_version_id="phase-fact-v1",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=3,
        unit="阶段序位",
        denominator=None,
        definition="III期",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,
        control_group=None,
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
    )
    role_facts = tuple(
        GateEvidenceBinding.model_validate(
            {
                **_binding(
                    binding_id=f"binding-role-{group_id}",
                    unit_id="a_trial_group_role",
                    object_id=group_id,
                    fact_version_id=f"role-fact-{group_id}",
                    fact_domain=FactDomain.TRIAL_DESIGN,
                    numeric_value=None,
                    unit=None,
                    denominator=None,
                    definition=definition,
                    direction=None,
                    timepoint=None,
                    analysis_population=None,
                    treatment_group=group_label,
                    control_group=None,
                    source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
                ).model_dump(),
                "comparison_id": "cmp-1",
                "group_id": group_id,
            }
        )
        for group_id, definition, group_label in (
            ("grp-active", "治疗组", "度普利尤单抗"),
            ("grp-control", "对照组", "安慰剂"),
        )
    )
    project = _complete_project(
        anchor_trials=(
            AnchorTrialRecord(
                trial_id="NCT02407756",
                fact_version_ids=("eff-active",),
            ),
        )
    )
    bindings = (
        _regulatory(),
        efficacy_active,
        efficacy_control,
        safety_active,
        safety_control,
        phase_fact,
        *role_facts,
    )
    trial_selection = (
        TrialSelectionRecord(
            project_id=project.project_id,
            trial_id="NCT02407756",
            phase_label_zh="III期",
            phase_rank=3,
            evidence_version_id="design-ev-NCT02407756",
            phase_fact_version_id="phase-fact-v1",
        ),
    )
    endpoint_families = (
        EndpointFamilySpec(
            family_id="easi75-week16",
            label_zh="第16周 EASI-75 应答率",
            direction=EndpointDirection.HIGHER_IS_BETTER,
            compatibility_rule_id="endpoint-family-easi75-v1",
            compatible_endpoint_ids=("ep-easi75",),
            compatible_units=("应答率 %",),
            compatible_timepoints=("第 16 周",),
            compatible_analysis_populations=("意向治疗集",),
            definition_required_terms=("湿疹面积和严重程度指数", "75%"),
            compatible_direction_texts=("应答率越高越好",),
        ),
    )
    efficacy_records = (
        EfficacyMeasureRecord(
            fact_version_id="eff-active",
            endpoint_family_id="easi75-week16",
            arm_role=ArmRole.TREATMENT,
        ),
        EfficacyMeasureRecord(
            fact_version_id="eff-control",
            endpoint_family_id="easi75-week16",
            arm_role=ArmRole.CONTROL,
        ),
    )
    safety_records = (
        SafetyMeasureRecord(
            fact_version_id="teae-active",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.TREATMENT,
            matrix_default=True,
        ),
        SafetyMeasureRecord(
            fact_version_id="teae-control",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.CONTROL,
            matrix_default=True,
        ),
    )
    group_roles = (
        TrialGroupRoleRecord(
            project_id=project.project_id,
            trial_id="NCT02407756",
            comparison_id="cmp-1",
            group_id="grp-active",
            group_label_zh="度普利尤单抗",
            arm_role=ArmRole.TREATMENT,
            evidence_fact_version_id="role-fact-grp-active",
        ),
        TrialGroupRoleRecord(
            project_id=project.project_id,
            trial_id="NCT02407756",
            comparison_id="cmp-1",
            group_id="grp-control",
            group_label_zh="安慰剂",
            arm_role=ArmRole.CONTROL,
            evidence_fact_version_id="role-fact-grp-control",
        ),
    )
    return (
        project,
        snapshot,
        bindings,
        trial_selection,
        endpoint_families,
        efficacy_records,
        safety_records,
        group_roles,
    )


def test_summary_preserves_target_group_anchor_treatment_control_and_heatmap_context() -> None:
    args = _case()
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=args[2],
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    assert view.product_ids == ("project-dupilumab",)
    assert view.target_groups[0].target_mechanism_zh == "IL-4Rα 受体阻断"
    assert view.anchors[0].trial_id == "NCT02407756"
    assert view.default_endpoint_family_id == "easi75-week16"
    assert [point.arm_role for point in view.efficacy_points] == [
        ArmRole.TREATMENT,
        ArmRole.CONTROL,
    ]
    assert [point.raw_value for point in view.efficacy_points] == [51.2, 24.6]
    assert all(
        point.definition_zh == "湿疹面积和严重程度指数较基线改善至少75%"
        for point in view.efficacy_points
    )
    assert all(point.direction_zh == "应答率越高越好" for point in view.efficacy_points)
    assert all(cell.event_definition_zh == "治疗期间不良事件" for cell in view.safety_cells)
    assert all(cell.time_window_zh == "治疗期间" for cell in view.safety_cells)
    assert [cell.denominator for cell in view.safety_cells] == [224, 224]


def test_anchor_selection_never_uses_efficacy_or_safety_magnitude() -> None:
    args = _case()
    first = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=args[2],
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    changed = tuple(
        binding.model_copy(update={"numeric_value": 0.1})
        if binding.fact_domain in {FactDomain.EFFICACY, FactDomain.SAFETY}
        else binding
        for binding in args[2]
    )
    second = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=changed,
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    assert first.anchors == second.anchors


def test_comparative_efficacy_without_control_is_rejected() -> None:
    args = _case()
    bindings_without_control = tuple(
        binding for binding in args[2] if binding.fact_version_id != "eff-control"
    )
    with pytest.raises(GateEvaluationError, match="对照"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings_without_control,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=(args[5][0],),
            safety_records=args[6],
        )


def test_model_copy_tampering_is_rejected_by_authoritative_assertion() -> None:
    args = _case()
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=args[2],
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    forged = view.model_copy(update={"product_ids": ()})
    with pytest.raises((GateEvaluationError, ValidationError, ValueError)):
        assert_efficacy_safety_summary_authoritative(
            forged,
            projects=(args[0],),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_authoritative_assertion_rejects_changed_universe_rule_set() -> None:
    args = _case()
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=args[2],
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    snapshot = args[1]
    changed_rule = "ind-rule-2"
    changed_summary = compute_universe_summary(
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
        indication_rule_set_id=changed_rule,
    )
    changed_snapshot = snapshot.model_copy(
        update={
            "indication_rule_set_id": changed_rule,
            "universe_summary": changed_summary,
        }
    )
    with pytest.raises(GateEvaluationError, match="权威输入"):
        assert_efficacy_safety_summary_authoritative(
            view,
            projects=(args[0],),
            snapshot=changed_snapshot,
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_unreferenced_or_duplicate_measure_fact_is_rejected() -> None:
    args = _case()
    duplicate = (*args[5], args[5][0])
    with pytest.raises(GateEvaluationError, match="重复"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=duplicate,
            safety_records=args[6],
        )


def test_sae_fact_cannot_be_mislabeled_as_teae() -> None:
    args = _case()
    mislabeled = args[6][0].model_copy(update={"family": SafetyFamily.SAE})
    with pytest.raises(GateEvaluationError, match="事件类别"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=(mislabeled, args[6][1]),
        )


def test_reported_measure_without_denominator_is_rejected() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"denominator": None})
        if binding.fact_version_id == "teae-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="正分母"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


@pytest.mark.parametrize("invalid_denominator", [0, -5])
def test_model_copy_cannot_bypass_positive_denominator(
    invalid_denominator: int,
) -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"denominator": invalid_denominator})
        if binding.fact_version_id == "eff-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="旁路篡改"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_treatment_and_control_roles_cannot_be_swapped() -> None:
    args = _case()
    swapped_efficacy = (
        args[5][0].model_copy(update={"arm_role": ArmRole.CONTROL}),
        args[5][1].model_copy(update={"arm_role": ArmRole.TREATMENT}),
    )
    with pytest.raises(GateEvaluationError, match="设计证据中的.*角色"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=swapped_efficacy,
            safety_records=args[6],
        )


def test_supporting_trial_cannot_be_selected_as_anchor() -> None:
    args = _case()
    supporting_core = args[0].core_trials[0].model_copy(update={"role": CoreTrialRole.SUPPORTING})
    project = args[0].model_copy(update={"core_trials": (supporting_core,)})
    with pytest.raises(GateEvaluationError, match="没有同时满足"):
        build_efficacy_safety_summary(
            projects=(project,),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_incompatible_treatment_and_control_timepoints_are_rejected() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"timepoint": "第24周"})
        if binding.fact_version_id == "eff-control"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="指标族不兼容"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_comparative_safety_without_control_record_is_rejected() -> None:
    args = _case()
    bindings = tuple(binding for binding in args[2] if binding.fact_version_id != "teae-control")
    with pytest.raises(GateEvaluationError, match="每个组别.*不良事件"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=(args[6][0],),
        )


def test_same_unit_but_incompatible_endpoint_definition_is_rejected() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"definition": "研究者总体评价达到0或1分"})
        if binding.fact_version_id == "eff-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="指标族不兼容"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_protocol_numeric_result_cannot_enter_formal_summary() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"source_role": SourceRole.PROTOCOL_SAP})
        if binding.fact_version_id in {"eff-active", "teae-active"}
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="观察性结果来源"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


@pytest.mark.parametrize("invalid_percentage", [-1.0, 150.0])
def test_percentage_measure_must_be_between_zero_and_one_hundred(
    invalid_percentage: float,
) -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"numeric_value": invalid_percentage})
        if binding.fact_version_id == "eff-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="0至100"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_duplicate_efficacy_for_same_trial_family_and_group_is_rejected() -> None:
    args = _case()
    duplicate_binding = next(
        binding for binding in args[2] if binding.fact_version_id == "eff-active"
    ).model_copy(
        update={
            "binding_id": "binding-eff-active-duplicate",
            "fact_version_id": "eff-active-duplicate",
        }
    )
    duplicate_record = EfficacyMeasureRecord(
        fact_version_id="eff-active-duplicate",
        endpoint_family_id="easi75-week16",
        arm_role=ArmRole.TREATMENT,
    )
    with pytest.raises(GateEvaluationError, match="多条疗效事实"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=(*args[2], duplicate_binding),
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=(*args[5], duplicate_record),
            safety_records=args[6],
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "9.9"),
        ("enumeration_complete", False),
    ],
)
def test_snapshot_model_copy_is_revalidated(field: str, value: object) -> None:
    args = _case()
    snapshot = args[1].model_copy(update={field: value})
    with pytest.raises(GateEvaluationError):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=snapshot,
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_default_teae_requires_canonical_term_and_treatment_window() -> None:
    args = _case()
    wrong_default = args[6][0].model_copy(update={"term_id": "rash"})
    with pytest.raises(GateEvaluationError, match="总体治疗期间"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=(wrong_default, args[6][1]),
        )


def test_early_product_without_public_results_remains_visible_without_draft_block() -> None:
    project = _complete_project(anchor_trials=(), regulatory_events=())
    snapshot = _snapshot(product_ids=(project.project_id,), endpoint_ids=("ep-easi75",))
    trial_binding = _binding(
        binding_id="trial-identity",
        fact_version_id="trial-identity-v1",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        unit=None,
        denominator=None,
        definition="适格临床试验身份已核验",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,
    )
    family = EndpointFamilySpec(
        family_id="easi75-week16",
        label_zh="第16周 EASI-75 应答率",
        direction=EndpointDirection.HIGHER_IS_BETTER,
        compatibility_rule_id="endpoint-family-easi75-v1",
        compatible_endpoint_ids=("ep-easi75",),
        compatible_units=("应答率 %",),
        compatible_timepoints=("第 16 周",),
        compatible_analysis_populations=("意向治疗集",),
        definition_required_terms=("湿疹面积和严重程度指数", "75%"),
        compatible_direction_texts=("应答率越高越好",),
    )
    view = build_efficacy_safety_summary(
        projects=(project,),
        snapshot=snapshot,
        bindings=(trial_binding,),
        trial_selection=(),
        group_roles=(),
        endpoint_families=(family,),
        efficacy_records=(),
        safety_records=(),
    )
    assert view.product_results[0].state is ProductResultState.NO_PUBLIC_RESULTS
    assert view.efficacy_points == ()
    assert view.safety_cells == ()


def test_heatmap_preserves_not_publicly_disclosed_as_missing_not_zero() -> None:
    args = _case()
    missing_base = _safety(
        unit_id="a_safety_event_injection_site_reaction",
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        numeric_value=None,
        denominator=None,
        source_location=None,
    )
    missing = _scoped(
        missing_base,
        fact="common-ae-missing",
        group="grp-active",
        value=None,
    )
    missing_control = _scoped(
        missing_base,
        fact="common-ae-missing-control",
        group="grp-control",
        value=None,
    )
    safety_records = (
        *args[6],
        SafetyMeasureRecord(
            fact_version_id="common-ae-missing",
            family=SafetyFamily.COMMON_AE,
            term_id="injection-site-reaction",
            arm_role=ArmRole.TREATMENT,
        ),
        SafetyMeasureRecord(
            fact_version_id="common-ae-missing-control",
            family=SafetyFamily.COMMON_AE,
            term_id="injection-site-reaction",
            arm_role=ArmRole.CONTROL,
        ),
    )
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=(*args[2], missing, missing_control),
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=safety_records,
    )
    cell = next(item for item in view.safety_cells if item.fact_version_id == "common-ae-missing")
    assert cell.raw_value is None
    assert cell.denominator is None
    assert cell.relative_intensity is None
    assert cell.disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED


def test_heatmap_converts_participant_count_to_rate_before_color_intensity() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"numeric_value": 39, "denominator": 50, "unit": "例"})
        if binding.fact_version_id == "teae-active"
        else binding
        for binding in args[2]
    )
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=bindings,
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    cell = next(item for item in view.safety_cells if item.fact_version_id == "teae-active")
    assert cell.raw_value == 39
    assert cell.denominator == 50
    assert cell.comparison_rate_percent == 78.0
    assert cell.relative_intensity == 1.0


def test_participant_count_rejects_fractional_people() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"numeric_value": 39.5, "unit": "例"})
        if binding.fact_version_id == "teae-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="人数必须是整数"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_heatmap_color_scale_does_not_mix_treatment_and_followup_windows() -> None:
    args = _case()
    followup_base = _safety(time_window="随访期", numeric_value=10.0)
    followup_active = _scoped(
        followup_base,
        fact="teae-followup-active",
        group="grp-active",
        value=10.0,
    )
    followup_control = _scoped(
        followup_base,
        fact="teae-followup-control",
        group="grp-control",
        value=8.0,
    )
    safety_records = (
        *args[6],
        SafetyMeasureRecord(
            fact_version_id="teae-followup-active",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.TREATMENT,
        ),
        SafetyMeasureRecord(
            fact_version_id="teae-followup-control",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.CONTROL,
        ),
    )
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=(*args[2], followup_active, followup_control),
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=safety_records,
    )
    treatment_cells = [
        cell
        for cell in view.safety_cells
        if cell.arm_role is ArmRole.TREATMENT and cell.term_id == "teae-any"
    ]
    assert {cell.time_window_zh for cell in treatment_cells} == {"治疗期间", "随访期"}
    assert all(cell.relative_intensity == 1.0 for cell in treatment_cells)


def test_display_group_label_comes_from_authoritative_design_record() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"treatment_group": "错误药物名称"})
        if binding.fact_version_id in {"eff-control", "teae-control"}
        else binding
        for binding in args[2]
    )
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=bindings,
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    control_efficacy = next(
        point for point in view.efficacy_points if point.arm_role is ArmRole.CONTROL
    )
    control_safety = next(
        cell
        for cell in view.safety_cells
        if cell.arm_role is ArmRole.CONTROL and cell.matrix_default
    )
    assert control_efficacy.group_label_zh == "安慰剂"
    assert control_safety.group_label_zh == "安慰剂"


def test_duplicate_safety_fact_for_same_group_and_context_is_rejected() -> None:
    args = _case()
    original = next(binding for binding in args[2] if binding.fact_version_id == "teae-active")
    duplicate = original.model_copy(
        update={
            "binding_id": "binding-teae-active-duplicate",
            "fact_version_id": "teae-active-duplicate",
        }
    )
    record = SafetyMeasureRecord(
        fact_version_id="teae-active-duplicate",
        family=SafetyFamily.TEAE,
        term_id="teae-any",
        arm_role=ArmRole.TREATMENT,
    )
    with pytest.raises(GateEvaluationError, match="安全性语境存在多条事实"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=(*args[2], duplicate),
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=(*args[6], record),
        )


def test_direction_text_cannot_bypass_closed_clinical_wording() -> None:
    args = _case()
    family = args[4][0].model_copy(update={"compatible_direction_texts": ("应答率不是越高越好",)})
    with pytest.raises(GateEvaluationError, match="输入无效"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=(family,),
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_unused_endpoint_family_must_still_belong_to_current_snapshot() -> None:
    args = _case()
    unused = args[4][0].model_copy(
        update={
            "family_id": "old-endpoint-family",
            "compatible_endpoint_ids": ("old-endpoint",),
        }
    )
    with pytest.raises(GateEvaluationError, match="当前快照之外"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=args[2],
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=(*args[4], unused),
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_reported_safety_state_requires_numeric_value_and_denominator() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"numeric_value": None, "denominator": None})
        if binding.fact_version_id == "teae-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="必须保留明确数值"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_safety_measure_rejects_unknown_unit() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"unit": "未知单位"})
        if binding.fact_version_id == "teae-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="规范测量单位"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


@pytest.mark.parametrize(
    ("unit", "value", "message"),
    [
        ("事件数", -3, "事件数必须"),
        ("事件数", 3.5, "事件数必须"),
        ("每100患者年", -1, "暴露校正发生率"),
    ],
)
def test_safety_measure_rejects_impossible_count_or_rate(
    unit: str,
    value: float,
    message: str,
) -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"unit": unit, "numeric_value": value})
        if binding.fact_version_id == "teae-active"
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match=message):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_result_group_text_must_match_authoritative_design_role() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(
            update={
                "treatment_group": "安慰剂",
                "control_group": "度普利尤单抗",
            }
        )
        if binding.fact_version_id in {"eff-active", "eff-control", "teae-active", "teae-control"}
        else binding
        for binding in args[2]
    )
    with pytest.raises(GateEvaluationError, match="组名与当前试验设计角色不一致"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=bindings,
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


@pytest.mark.parametrize(
    "broken_binding",
    [
        _scoped(
            _efficacy(definition=None),
            fact="extra-efficacy-missing-definition",
            group="grp-active",
            value=50.0,
        ),
        _scoped(
            _safety(event_definition=None),
            fact="extra-safety-missing-definition",
            group="grp-active",
            value=10.0,
        ),
        _scoped(
            _safety(time_window=None),
            fact="extra-safety-missing-window",
            group="grp-active",
            value=10.0,
        ),
    ],
)
def test_incomplete_accepted_result_cannot_be_silently_excluded(
    broken_binding: GateEvidenceBinding,
) -> None:
    args = _case()
    with pytest.raises(GateEvaluationError, match="完整覆盖"):
        build_efficacy_safety_summary(
            projects=(args[0],),
            snapshot=args[1],
            bindings=(*args[2], broken_binding),
            trial_selection=args[3],
            group_roles=args[7],
            endpoint_families=args[4],
            efficacy_records=args[5],
            safety_records=args[6],
        )


def test_regulatory_material_can_carry_group_scoped_efficacy_and_safety_results() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"source_role": SourceRole.REGULATORY_MATERIAL})
        if binding.fact_version_id in {"eff-active", "teae-active"}
        else binding
        for binding in args[2]
    )
    view = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=bindings,
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    assert (
        next(
            point for point in view.efficacy_points if point.fact_version_id == "eff-active"
        ).raw_value
        == 51.2
    )
    assert (
        next(
            cell for cell in view.safety_cells if cell.fact_version_id == "teae-active"
        ).comparison_rate_percent
        == 78.0
    )
