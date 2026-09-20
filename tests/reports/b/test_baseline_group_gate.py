"""Task 6.5 B-v1 基线逐试验逐组 GateSpec 绑定测试。"""

from __future__ import annotations

from pathlib import Path

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    EmptySetProof,
    EmptySetReasonCode,
    FactDomain,
    GateBlockingLevel,
    GateEvidenceBinding,
    GateObjectType,
    GateSpec,
    GateUnitOutcome,
    GateUnitResult,
    ObservationKind,
    ReportDecision,
    ReportGateResult,
    TrialDesignEvidence,
    TrialDesignKind,
    UniverseEdge,
    compute_universe_summary,
)
from ci_workflow.reports.b.baseline import (
    BaselineDataType,
    BaselineObservation,
    BaselineStatisticForm,
    BaselineVariableDomain,
    build_baseline_gate_bindings,
    to_gate_evidence_binding,
)
from tests.reports.b.test_baseline_observation_contract import _observation

ROOT = Path(__file__).resolve().parents[3]
BASELINE_UNIT_IDS = (
    "b_baseline_sample_size",
    "b_baseline_age",
    "b_baseline_sex",
    "b_baseline_severity_anchor",
)


def _snapshot(
    *,
    trial_ids: tuple[str, ...] = ("trial-1",),
    comparison_ids: tuple[str, ...] = ("comparison-1",),
    group_ids: tuple[str, ...] = ("group-1", "group-2"),
) -> ApplicableUniverseSnapshot:
    if len(trial_ids) == 1:
        trial_to_comparison = {trial_ids[0]: comparison_ids}
        trial_to_groups = {trial_ids[0]: group_ids}
    else:
        if len(comparison_ids) != len(trial_ids) or len(group_ids) != 2 * len(trial_ids):
            raise ValueError("多试验夹具必须为每项试验提供一个比较和两个组")
        trial_to_comparison = {
            trial_id: (comparison_ids[index],)
            for index, trial_id in enumerate(trial_ids)
        }
        trial_to_groups = {
            trial_id: group_ids[index * 2 : index * 2 + 2]
            for index, trial_id in enumerate(trial_ids)
        }

    edges: list[UniverseEdge] = []
    for trial_id in trial_ids:
        edges.extend(
            (
                UniverseEdge(
                    parent_type=GateObjectType.PRODUCT,
                    parent_id="product-a",
                    child_type=GateObjectType.TRIAL,
                    child_id=trial_id,
                ),
                *(
                    UniverseEdge(
                        parent_type=GateObjectType.TRIAL,
                        parent_id=trial_id,
                        child_type=GateObjectType.COMPARISON,
                        child_id=comparison_id,
                    )
                    for comparison_id in trial_to_comparison[trial_id]
                ),
                *(
                    UniverseEdge(
                        parent_type=GateObjectType.TRIAL,
                        parent_id=trial_id,
                        child_type=GateObjectType.GROUP,
                        child_id=group_id,
                    )
                    for group_id in trial_to_groups[trial_id]
                ),
                *(
                    UniverseEdge(
                        parent_type=GateObjectType.COMPARISON,
                        parent_id=comparison_id,
                        child_type=GateObjectType.GROUP,
                        child_id=group_id,
                    )
                    for comparison_id in trial_to_comparison[trial_id]
                    for group_id in trial_to_groups[trial_id]
                ),
            )
        )

    empty_proofs = (
        EmptySetProof(
            object_type=GateObjectType.ENDPOINT,
            reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
            evidence_version_id="proof-endpoint-v1",
            explanation_zh="穷尽检索后未发现核心疗效终点",
        ),
        EmptySetProof(
            object_type=GateObjectType.TIMEPOINT,
            reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
            evidence_version_id="proof-timepoint-v1",
            explanation_zh="穷尽检索后未发现独立时间点对象",
        ),
    )
    trial_design = tuple(
        TrialDesignEvidence(
            trial_id=trial_id,
            design_kind=TrialDesignKind.COMPARATIVE,
            evidence_version_id=f"design-{trial_id}-v1",
            explanation_zh="主要报告明确包含治疗组和对照组",
        )
        for trial_id in trial_ids
    )
    summary = compute_universe_summary(
        project_id="project-baseline-1",
        evidence_snapshot_id="snapshot-baseline-1",
        research_role_set_id="research-roles-core-v1",
        product_ids=("product-a",),
        trial_ids=trial_ids,
        comparison_ids=comparison_ids,
        group_ids=group_ids,
        endpoint_ids=(),
        timepoint_ids=(),
        empty_set_proofs=empty_proofs,
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design,
        indication_rule_set_id="indication-rules-core-v1",
        applicable_conditional_predicates=(),
    )
    return ApplicableUniverseSnapshot(
        project_id="project-baseline-1",
        evidence_snapshot_id="snapshot-baseline-1",
        research_role_set_id="research-roles-core-v1",
        indication_rule_set_id="indication-rules-core-v1",
        product_ids=("product-a",),
        trial_ids=trial_ids,
        comparison_ids=comparison_ids,
        group_ids=group_ids,
        endpoint_ids=(),
        timepoint_ids=(),
        empty_set_proofs=empty_proofs,
        relationship_edges=tuple(edges),
        trial_design_evidence=trial_design,
        applicable_conditional_predicates=(),
        universe_summary=summary,
        enumeration_complete=True,
    )


def _b_spec() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "B-v1.yaml")


def _baseline_observations(
    *,
    trial_id: str = "trial-1",
    group_id: str = "group-1",
) -> tuple[BaselineObservation, ...]:
    base = {
        "trial_id": trial_id,
        "cohort_id": f"cohort-{trial_id}",
        "group_id": group_id,
    }
    return (
        _observation(
            row_id=f"baseline-row-n-{group_id}",
            source_row_id=f"source-row-n-{group_id}",
            observation_id=f"baseline-observation-n-{group_id}",
            **base,
            source_name="N",
            source_definition="Number randomized to the group",
            standardized_concept="baseline_sample_size",
            variable_domain=BaselineVariableDomain.DEMOGRAPHICS,
            data_type=BaselineDataType.COUNT,
            statistic_form=BaselineStatisticForm.SAMPLE_SIZE,
            value=100,
            raw_value="100",
            unit="人",
            dispersion=None,
            denominator=100,
            denominator_role="随机化人群",
        ),
        _observation(
            row_id=f"baseline-row-age-{group_id}",
            source_row_id=f"source-row-age-{group_id}",
            observation_id=f"baseline-observation-age-{group_id}",
            **base,
            source_name="Age",
            source_definition="Age at baseline",
            standardized_concept="age",
            variable_domain=BaselineVariableDomain.DEMOGRAPHICS,
            statistic_form=BaselineStatisticForm.MEAN,
            value=54.3,
            raw_value="54.3 (12.1)",
            unit="岁",
            dispersion=12.1,
            denominator=100,
            denominator_role="随机化人群",
        ),
        _observation(
            row_id=f"baseline-row-sex-{group_id}",
            source_row_id=f"source-row-sex-{group_id}",
            observation_id=f"baseline-observation-sex-{group_id}",
            **base,
            source_name="Sex",
            source_definition="Sex at baseline",
            standardized_concept="sex",
            variable_domain=BaselineVariableDomain.DEMOGRAPHICS,
            data_type=BaselineDataType.CATEGORICAL,
            statistic_form=BaselineStatisticForm.PROPORTION,
            value=45.0,
            raw_value="45/100 (45%)",
            unit="%",
            dispersion=None,
            category_level="Female",
            numerator=45,
            denominator=100,
            denominator_role="随机化人群",
        ),
        _observation(
            row_id=f"baseline-row-severity-{group_id}",
            source_row_id=f"source-row-severity-{group_id}",
            observation_id=f"baseline-observation-severity-{group_id}",
            **base,
            source_name="EASI total score",
            source_definition="EASI total score at baseline",
            standardized_concept="easi_total_score",
            variable_domain=BaselineVariableDomain.BASELINE_SEVERITY,
            scale="EASI",
            scale_version="v1",
            direction="higher_is_more_severe",
            theoretical_range="0–72",
            statistic_form=BaselineStatisticForm.MEAN,
            value=24.5,
            raw_value="24.5 (8.1)",
            unit="分",
            dispersion=8.1,
            denominator=100,
            denominator_role="随机化人群",
        ),
    )


def _bindings_for(
    observations: tuple[BaselineObservation, ...],
    *,
    unit_ids: tuple[str, ...] = BASELINE_UNIT_IDS,
) -> tuple[GateEvidenceBinding, ...]:
    return build_baseline_gate_bindings(
        observations,
        unit_ids,
        severity_anchor_concepts=frozenset({"easi_total_score"}),
    )


def test_severity_anchor_requires_indication_recognized_concept() -> None:
    severity = _baseline_observations()[-1].model_copy(
        update={"standardized_concept": "arbitrary_score"}
    )
    try:
        to_gate_evidence_binding(
            severity,
            unit_id="b_baseline_severity_anchor",
            severity_anchor_concepts=frozenset({"easi_total_score"}),
        )
    except ValueError as error:
        assert "当前适应症认可" in str(error)
    else:  # pragma: no cover
        raise AssertionError("未认可严重度指标不得满足 Gate")


def _baseline_results(result: ReportGateResult, group_id: str) -> dict[str, GateUnitResult]:
    return {
        unit_id: next(
            item
            for item in result.unit_results
            if item.unit_id == unit_id and item.object_id == group_id
        )
        for unit_id in BASELINE_UNIT_IDS
    }


def test_b_v1_declares_four_independent_critical_group_baseline_units() -> None:
    spec = _b_spec()
    units = {
        unit.unit_id: unit
        for unit in spec.units
        if unit.unit_id in BASELINE_UNIT_IDS
    }

    assert set(units) == set(BASELINE_UNIT_IDS)
    for unit_id in BASELINE_UNIT_IDS:
        unit = units[unit_id]
        assert unit.blocking_level is GateBlockingLevel.CRITICAL
        assert unit.object_type is GateObjectType.GROUP
        assert unit.scope_parent is GateObjectType.TRIAL
        assert unit.applicability_predicate_id == "always_applicable"
        assert unit.allowed_fact_domains == (FactDomain.TRIAL_DESIGN,)
        assert unit.allowed_observation_kinds == (ObservationKind.OBSERVED_RESULT,)
        assert unit.threshold == 1


def test_baseline_conversion_reuses_existing_gate_binding_and_own_scope() -> None:
    observation = _baseline_observations()[1]
    binding = to_gate_evidence_binding(observation, unit_id="b_baseline_age")

    assert binding.unit_id == "b_baseline_age"
    assert binding.object_id == "group-1"
    assert binding.group_id == "group-1"
    assert binding.trial_id == "trial-1"
    assert binding.fact_domain is FactDomain.TRIAL_DESIGN
    assert binding.observation_kind.value == "observed_result"
    assert binding.numeric_value == 54.3
    assert binding.unit == "岁"
    assert binding.denominator == 100
    assert binding.analysis_population == "全分析集"
    assert binding.source_location == "Table 1.baseline"
    assert binding.fact_version_id == observation.row_id
    assert binding.disclosure_state is FactDisclosureState.REPORTED_VALUE


def test_each_core_trial_group_requires_all_four_independent_baseline_observations() -> None:
    snapshot = _snapshot()
    complete_group_one = _bindings_for(_baseline_observations(group_id="group-1"))
    result = evaluate_report(_b_spec(), snapshot, complete_group_one, contract_version="1")

    group_one = _baseline_results(result, "group-1")
    group_two = _baseline_results(result, "group-2")
    assert all(item.outcome is GateUnitOutcome.SATISFIED for item in group_one.values())
    assert all(item.outcome is GateUnitOutcome.BLOCKED for item in group_two.values())
    assert result.decision is ReportDecision.BLOCKED


def test_group_baseline_values_cannot_be_borrowed_from_another_group() -> None:
    snapshot = _snapshot()
    group_one = _bindings_for(_baseline_observations(group_id="group-1"))
    group_two = _bindings_for(_baseline_observations(group_id="group-2"))
    # Only group-1's source facts are supplied; no overall or treatment/control
    # alias may satisfy group-2's four independent units.
    result = evaluate_report(_b_spec(), snapshot, (*group_one,), contract_version="1")

    group_two_results = _baseline_results(result, "group-2")
    assert all(item.satisfied_count == 0 for item in group_two_results.values())
    assert all(item.outcome is GateUnitOutcome.BLOCKED for item in group_two_results.values())
    assert all(item.group_id == "group-1" for item in group_one)
    assert all(item.group_id == "group-2" for item in group_two)


def test_baseline_group_gate_does_not_cross_trial_scope() -> None:
    snapshot = _snapshot(
        trial_ids=("trial-1", "trial-2"),
        comparison_ids=("comparison-1", "comparison-2"),
        group_ids=("group-1", "group-2", "group-3", "group-4"),
    )
    trial_one = _bindings_for(
        _baseline_observations(trial_id="trial-1", group_id="group-1")
    )
    result = evaluate_report(_b_spec(), snapshot, trial_one, contract_version="1")

    trial_one_results = _baseline_results(result, "group-1")
    trial_two_results = tuple(
        _baseline_results(result, group_id)
        for group_id in ("group-3", "group-4")
    )
    assert all(item.outcome is GateUnitOutcome.SATISFIED for item in trial_one_results.values())
    assert all(
        item.outcome is GateUnitOutcome.BLOCKED
        for group_results in trial_two_results
        for item in group_results.values()
    )
    assert result.decision is ReportDecision.BLOCKED


def test_severity_anchor_is_independently_required_and_missing_it_blocks_draft() -> None:
    snapshot = _snapshot()
    observations = _baseline_observations()
    without_severity = observations[:-1]
    result = evaluate_report(
        _b_spec(),
        snapshot,
        _bindings_for(without_severity, unit_ids=BASELINE_UNIT_IDS[:-1]),
        contract_version="1",
    )

    severity = next(
        item
        for item in result.unit_results
        if item.unit_id == "b_baseline_severity_anchor" and item.object_id == "group-1"
    )
    assert severity.outcome is GateUnitOutcome.BLOCKED
    assert severity.blocking is True
    assert result.decision is ReportDecision.BLOCKED
    assert severity.user_note_zh is not None
    assert "严重程度" in severity.user_note_zh


def test_disclosed_baseline_value_cannot_be_replaced_by_missing_or_route_state() -> None:
    snapshot = _snapshot()
    missing_age = _observation(
        row_id="baseline-row-age-missing-g1",
        source_row_id="source-row-age-missing-g1",
        observation_id="baseline-observation-age-missing-g1",
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        value=None,
        raw_value="来源未公开",
        denominator=None,
        dispersion=None,
    )
    observations = (*_baseline_observations()[:1], missing_age, *_baseline_observations()[2:])
    result = evaluate_report(_b_spec(), snapshot, _bindings_for(observations), contract_version="1")

    age = next(
        item
        for item in result.unit_results
        if item.unit_id == "b_baseline_age" and item.object_id == "group-1"
    )
    assert age.outcome is GateUnitOutcome.BLOCKED
    assert age.disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED
    assert result.decision is ReportDecision.BLOCKED
