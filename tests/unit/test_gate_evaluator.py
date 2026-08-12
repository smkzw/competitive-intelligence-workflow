from __future__ import annotations

import importlib
import json
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    ConflictDisposition,
    ConflictStrategy,
    DevelopmentMaturity,
    DisclosureMaturity,
    EmptySetProof,
    FactDomain,
    GateBlockingLevel,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    GateOverride,
    GateSpec,
    GateUnitOutcome,
    GateUnitResult,
    GateUnitSpec,
    MissingStrategy,
    ObservationKind,
    ReportDecision,
    ReportGateResult,
    SourceRole,
    TrialDesignEvidence,
    UniverseEdge,
    _aggregate_report_gates,
    _GateEvaluationBatch,
    assert_applicable_universe_closed,
    assert_bindings_in_universe,
    compute_gate_result_key,
    compute_universe_summary,
    derive_expected_unit_object_pairs,
    derive_result_bearing,
    evaluate_unit_decision,
)

ROOT = Path(__file__).resolve().parents[2]

_MISSING_DISCLOSURE_STATES = (
    FactDisclosureState.NOT_REPORTED,
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
    FactDisclosureState.BELOW_REPORTING_THRESHOLD,
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
)

_UNKNOWN_SOURCE_ROLE = "made_up_source_role"
_UNKNOWN_MATURITY = "ultra_mature"
_UNKNOWN_FACT_STATE = "total_completed_rate"
_UNKNOWN_CONFLICT_STRATEGY = "merge_everything"
_UNKNOWN_MISSING_STRATEGY = "ask_user_now"
_UNKNOWN_BLOCKING_LEVEL = "medium"
_UNKNOWN_OBJECT_TYPE = "company"
_UNKNOWN_REPORT_KIND = "D"


def _proof_payload(object_type: str, label_zh: str) -> dict[str, object]:
    return {
        "object_type": object_type,
        "reason_code": "exhaustive_search_no_objects",
        "evidence_version_id": f"evidence-{object_type}-empty-v1",
        "explanation_zh": f"穷尽检索后未发现适用{label_zh}对象",
    }


def _edge_payload(
    parent_type: str, parent_id: str, child_type: str, child_id: str
) -> dict[str, object]:
    return {
        "parent_type": parent_type,
        "parent_id": parent_id,
        "child_type": child_type,
        "child_id": child_id,
    }


def _design_record(trial_id: str, design_kind: str) -> dict[str, object]:
    return {
        "trial_id": trial_id,
        "design_kind": design_kind,
        "evidence_version_id": f"evidence-{trial_id}-{design_kind}-v1",
        "explanation_zh": (
            f"登记结果显示试验 {trial_id} 为"
            f"{'比较' if design_kind == 'comparative' else '单臂'}设计"
        ),
    }


def _snapshot(**overrides: object) -> ApplicableUniverseSnapshot:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": "project_000000000000000000000001",
        "evidence_snapshot_id": "snapshot-001",
        "research_role_set_id": "research-roles-core-v1",
        "indication_rule_set_id": "indication-rules-core-v1",
        "applicable_conditional_predicates": (),
        "product_ids": ("product-a",),
        "trial_ids": ("trial-1",),
        "comparison_ids": ("comparison-1",),
        "group_ids": ("group-1", "group-2"),
        "endpoint_ids": (),
        "timepoint_ids": (),
        "enumeration_complete": True,
    }
    payload.update(overrides)
    if "empty_set_proofs" not in overrides:
        empty_set_proofs: tuple[object, ...] = ()
        for object_type, label in (
            ("trial", "试验"),
            ("comparison", "比较"),
            ("group", "组别"),
            ("endpoint", "终点"),
            ("timepoint", "时间点"),
        ):
            if not tuple(payload[f"{object_type}_ids"]):  # type: ignore[arg-type]
                empty_set_proofs += (_proof_payload(object_type, label),)
        payload["empty_set_proofs"] = empty_set_proofs
    if "relationship_edges" not in overrides:
        payload["relationship_edges"] = (
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
            _edge_payload("trial", "trial-1", "group", "group-2"),
            _edge_payload("comparison", "comparison-1", "group", "group-1"),
            _edge_payload("comparison", "comparison-1", "group", "group-2"),
        )
    if "trial_design_evidence" not in overrides:
        payload["trial_design_evidence"] = tuple(
            _design_record(str(trial_id), "comparative")
            for trial_id in tuple(payload["trial_ids"])  # type: ignore[arg-type]
        )
    if "universe_summary" not in overrides:
        proof_models = tuple(
            EmptySetProof.model_validate(item)
            for item in tuple(payload["empty_set_proofs"])  # type: ignore[arg-type]
        )
        edge_models = tuple(
            UniverseEdge.model_validate(item)
            for item in tuple(payload["relationship_edges"])  # type: ignore[arg-type]
        )
        design_models = tuple(
            TrialDesignEvidence.model_validate(item)
            for item in tuple(payload["trial_design_evidence"])  # type: ignore[arg-type]
        )
        payload["universe_summary"] = compute_universe_summary(
            project_id=str(payload["project_id"]),
            evidence_snapshot_id=str(payload["evidence_snapshot_id"]),
            research_role_set_id=str(payload["research_role_set_id"]),
            product_ids=tuple(payload["product_ids"]),  # type: ignore[arg-type]
            trial_ids=tuple(payload["trial_ids"]),  # type: ignore[arg-type]
            comparison_ids=tuple(payload["comparison_ids"]),  # type: ignore[arg-type]
            group_ids=tuple(payload["group_ids"]),  # type: ignore[arg-type]
            endpoint_ids=tuple(payload["endpoint_ids"]),  # type: ignore[arg-type]
            timepoint_ids=tuple(payload["timepoint_ids"]),  # type: ignore[arg-type]
            empty_set_proofs=proof_models,
            relationship_edges=edge_models,
            trial_design_evidence=design_models,
            indication_rule_set_id=str(payload["indication_rule_set_id"]),
            applicable_conditional_predicates=tuple(
                payload["applicable_conditional_predicates"]  # type: ignore[arg-type]
            ),
        )
    return ApplicableUniverseSnapshot.model_validate(payload)


def _binding(**overrides: object) -> GateEvidenceBinding:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "binding_id": "binding-1",
        "unit_id": "a_safety_summary",
        "object_id": "product-a",
        "fact_version_id": "fact-1",
        "trial_id": "trial-1",
        "comparison_id": "comparison-1",
        "group_id": "group-1",
        "endpoint_id": None,
        "timepoint_id": None,
        "fact_domain": FactDomain.SAFETY,
        "observation_kind": ObservationKind.OBSERVED_RESULT,
        "numeric_value": None,
        "unit": "percent",
        "denominator": 120,
        "definition": "治疗期间不良事件",
        "direction": None,
        "timepoint": None,
        "analysis_population": "安全性分析集",
        "treatment_group": "治疗组",
        "control_group": "对照组",
        "event_definition": "TEAE",
        "time_window": "治疗期间",
        "source_location": "登记结果安全性表",
        "route_receipt_id": None,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": FactDisclosureState.REPORTED_VALUE,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "source_role": SourceRole.CLINICAL_TRIAL_REGISTRY,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "applicability_predicate_id": None,
        "reported_zero_text": None,
    }
    payload.update(overrides)
    return GateEvidenceBinding.model_validate(payload)


def _unit(**overrides: object) -> GateUnitSpec:
    payload: dict[str, object] = {
        "unit_id": "a_safety_summary",
        "report_kind": ReportKind.A,
        "blocking_level": GateBlockingLevel.CRITICAL,
        "object_type": GateObjectType.PRODUCT,
        "scope_parent": None,
        "applicability_predicate_id": "result_bearing",
        "required_context_fields": (
            "event_definition",
            "time_window",
            "treatment_group",
            "control_group",
            "denominator",
        ),
        "allowed_source_roles": (
            SourceRole.CLINICAL_TRIAL_REGISTRY,
            SourceRole.REGULATORY_MATERIAL,
            SourceRole.PRIMARY_TRIAL_REPORT,
            SourceRole.CONFERENCE_DISCLOSURE,
            SourceRole.COMPANY_DISCLOSURE,
            SourceRole.DESIGNATED_INDUSTRY_SOURCE,
        ),
        "minimum_disclosure_maturity": DisclosureMaturity.ATTRIBUTABLE_NUMERIC_DISCLOSURE,
        "accepted_fact_states": (
            FactDisclosureState.REPORTED_VALUE,
            FactDisclosureState.REPORTED_ZERO,
        ),
        "missing_strategy": MissingStrategy.BLOCK,
        "conflict_strategy": ConflictStrategy.RESOLVED_ONLY,
        "threshold": 1,
        "user_label_zh": "安全性数值摘要",
        "missing_impact_zh": "无法判断该产品的关键安全性风险",
        "user_next_step_zh": "请提供官方登记结果或主要试验报告中的不良事件数值摘要",
    }
    payload.update(overrides)
    return GateUnitSpec.model_validate(payload)


def _identity_unit(**overrides: object) -> GateUnitSpec:
    return _unit(
        unit_id="a_product_identity",
        applicability_predicate_id="always_applicable",
        required_context_fields=(),
        user_label_zh="产品规范身份与别名",
        missing_impact_zh="无法确认产品身份，影响竞品识别与定位",
        user_next_step_zh="请提供官方登记或监管材料中的产品名称、代码与别名",
        **overrides,
    )


def _minimal_spec(*units: GateUnitSpec, version: str = "1.0") -> GateSpec:
    return GateSpec(
        spec_id="gate-spec-test",
        version=version,
        report_kind=ReportKind.A,
        units=tuple(units),
        updated_at=datetime(2026, 8, 12, 9, 0, tzinfo=timezone(timedelta(hours=8))),
    )


def _spec_validator() -> Draft202012Validator:
    schema = json.loads(
        (ROOT / "schemas" / "gate-spec.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _spec_document() -> dict[str, object]:
    import yaml

    return yaml.safe_load(
        (ROOT / "policies" / "gates" / "A-v1.yaml").read_text(encoding="utf-8")
    )


def _matrix_results(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    *,
    outcome: GateUnitOutcome = GateUnitOutcome.SATISFIED,
) -> list[GateUnitResult]:
    """为规范 spec×snapshot 期望矩阵生成完整一致的结果集（默认全部满足）。"""
    spec_units = {unit.unit_id: unit for unit in spec.units}
    results: list[GateUnitResult] = []
    for unit_id, object_id in derive_expected_unit_object_pairs(spec, snapshot):
        unit = spec_units[unit_id]
        if outcome is GateUnitOutcome.SATISFIED:
            count = max(1, unit.threshold)
            results.append(
                GateUnitResult(
                    unit_id=unit_id,
                    report_kind=spec.report_kind,
                    object_id=object_id,
                    applicable=True,
                    outcome=GateUnitOutcome.SATISFIED,
                    blocking=False,
                    threshold=unit.threshold,
                    satisfied_count=count,
                    fact_version_ids=tuple(
                        f"fact-{unit_id}-{index}" for index in range(count)
                    ),
                )
            )
        elif outcome is GateUnitOutcome.BLOCKED:
            results.append(
                GateUnitResult(
                    unit_id=unit_id,
                    report_kind=spec.report_kind,
                    object_id=object_id,
                    applicable=True,
                    outcome=GateUnitOutcome.BLOCKED,
                    blocking=True,
                    threshold=unit.threshold,
                    satisfied_count=0,
                    fact_version_ids=(),
                    failure_code="missing_required_evidence",
                    user_note_zh=(
                        f"{unit.user_label_zh}缺失：{unit.missing_impact_zh}。"
                    ),
                )
            )
        elif outcome is GateUnitOutcome.EXTENSION_MISSING:
            results.append(
                GateUnitResult(
                    unit_id=unit_id,
                    report_kind=spec.report_kind,
                    object_id=object_id,
                    applicable=True,
                    outcome=GateUnitOutcome.EXTENSION_MISSING,
                    blocking=False,
                    threshold=unit.threshold,
                    satisfied_count=0,
                    fact_version_ids=(),
                )
            )
        else:
            results.append(
                GateUnitResult(
                    unit_id=unit_id,
                    report_kind=spec.report_kind,
                    object_id=object_id,
                    applicable=False,
                    outcome=GateUnitOutcome.NOT_APPLICABLE,
                    blocking=False,
                    threshold=unit.threshold,
                    satisfied_count=0,
                    fact_version_ids=(),
                )
            )
    return results


def _aggregate(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    unit_results: Sequence[GateUnitResult],
    *,
    contract_version: str = "1",
) -> ReportGateResult:
    """内部测试钩子：从规范对象构造评估批并聚合（非公共契约）。"""
    batch = _GateEvaluationBatch.from_evaluation(
        spec=spec, snapshot=snapshot, unit_results=unit_results
    )
    return _aggregate_report_gates(
        spec=spec,
        snapshot=snapshot,
        batch=batch,
        contract_version=contract_version,
    )


def _identity_binding() -> GateEvidenceBinding:
    return _binding(
        binding_id="binding-identity",
        unit_id="a_product_identity",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        denominator=None,
        definition="产品甲",
        source_location="官方登记",
    )


def test_gate_evaluator_fails_closed_on_result_bearing_missing_safety_summary() -> None:
    snapshot = _snapshot()
    assert_applicable_universe_closed(snapshot)

    efficacy_binding = _binding(
        binding_id="binding-efficacy",
        unit_id="a_efficacy_summary",
        fact_domain=FactDomain.EFFICACY,
        numeric_value=12.5,
        unit="%",
        denominator=120,
        definition="客观缓解率",
        direction="higher_is_better",
        timepoint="第12周",
        analysis_population="全分析集",
        treatment_group="治疗组",
        control_group="对照组",
        source_location="登记结果疗效表",
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
    )
    safety_binding = _binding(
        binding_id="binding-safety-missing",
        numeric_value=None,
        denominator=None,
        source_location=None,
        disclosure_state=FactDisclosureState.NOT_REPORTED,
    )

    assert derive_result_bearing(snapshot, (efficacy_binding, safety_binding)) is True

    spec = GateSpec.from_yaml(ROOT / "policies" / "gates" / "A-v1.yaml")
    efficacy_unit = next(u for u in spec.units if u.unit_id == "a_efficacy_summary")
    safety_unit = next(u for u in spec.units if u.unit_id == "a_safety_summary")

    efficacy_result = evaluate_unit_decision(
        efficacy_unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(efficacy_binding, safety_binding),
    )
    safety_result = evaluate_unit_decision(
        safety_unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(efficacy_binding, safety_binding),
    )
    assert efficacy_result.outcome is GateUnitOutcome.SATISFIED
    assert safety_result.outcome is GateUnitOutcome.BLOCKED

    full_matrix = [
        result
        for result in _matrix_results(spec, snapshot)
        if result.unit_id not in ("a_efficacy_summary", "a_safety_summary")
    ]
    report = _aggregate(
        spec, snapshot, (*full_matrix, efficacy_result, safety_result)
    )
    assert report.decision is ReportDecision.BLOCKED
    assert report.blocked_unit_ids == ("a_safety_summary",)
    assert "安全性数值摘要" in report.user_summary_zh
    assert "a_safety_summary" not in report.user_summary_zh

    planned_only = _binding(
        binding_id="binding-planned",
        unit_id="a_efficacy_summary",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.PLANNED_VALUE,
        numeric_value=20.0,
        definition="客观缓解率目标值",
    )
    assert derive_result_bearing(snapshot, (planned_only,)) is False


@pytest.mark.parametrize(
    ("case", "overrides"),
    [
        (
            "enumeration_incomplete",
            {"enumeration_complete": False},
        ),
        (
            "duplicate_product",
            {"product_ids": ("product-a", "product-a")},
        ),
        (
            "unproven_empty_trials",
            {"trial_ids": (), "empty_set_proofs": ()},
        ),
        (
            "proof_for_nonempty_class",
            {
                "empty_set_proofs": (
                    _proof_payload("trial", "试验"),
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                )
            },
        ),
    ],
)
def test_gate_evaluator_fails_closed_on_incomplete_applicable_universe(
    case: str, overrides: dict[str, object]
) -> None:
    snapshot = _snapshot(**overrides)
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(snapshot)


@pytest.mark.parametrize(
    ("case", "overrides"),
    [
        ("unknown_binding_object", {"object_id": "product-x"}),
        ("unknown_binding_scope", {"trial_id": "trial-999"}),
    ],
)
def test_gate_evaluator_fails_closed_on_unknown_binding_objects(
    case: str, overrides: dict[str, object]
) -> None:
    snapshot = _snapshot()
    assert_applicable_universe_closed(snapshot)
    with pytest.raises(GateEvaluationError):
        assert_bindings_in_universe(
            snapshot,
            (_binding(binding_id=f"binding-{case}", **overrides),),
        )


def test_gate_evaluator_fails_closed_on_forged_universe_summary() -> None:
    with pytest.raises(PydanticValidationError, match="摘要与内容不一致"):
        _snapshot(universe_summary="forged-summary")


@pytest.mark.parametrize("state", _MISSING_DISCLOSURE_STATES, ids=lambda s: s.value)
def test_gate_evaluator_never_coerces_missing_numeric_value_to_zero(
    state: FactDisclosureState,
) -> None:
    for numeric in (0, 0.0, 5.0, -1):
        with pytest.raises(PydanticValidationError, match="不得携带数值"):
            _binding(
                disclosure_state=state,
                numeric_value=numeric,
                source_location=None,
                route_receipt_id="receipt-1" if state.value == "unresolved_due_to_route" else None,
            )
    with pytest.raises(PydanticValidationError, match="不得携带分母"):
        _binding(
            disclosure_state=state,
            denominator=100,
            source_location=None,
            route_receipt_id="receipt-1" if state.value == "unresolved_due_to_route" else None,
        )

    missing = _binding(
        binding_id="binding-missing",
        disclosure_state=state,
        numeric_value=None,
        denominator=None,
        source_location=None,
        route_receipt_id="receipt-1" if state.value == "unresolved_due_to_route" else None,
    )
    unit = _unit()
    result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(missing,),
    )
    assert result.outcome is GateUnitOutcome.BLOCKED
    assert result.satisfied_count == 0

    with pytest.raises(PydanticValidationError, match="零值原文"):
        _binding(disclosure_state=FactDisclosureState.REPORTED_ZERO, numeric_value=0)
    zero = _binding(
        binding_id="binding-zero",
        disclosure_state=FactDisclosureState.REPORTED_ZERO,
        numeric_value=0,
        reported_zero_text="0 例（0%）",
    )
    zero_result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(zero,),
    )
    assert zero_result.outcome is GateUnitOutcome.SATISFIED


def test_gate_evaluator_enforces_field_source_role_floor() -> None:
    unit = _unit(
        unit_id="b_baseline_sample_size",
        report_kind=ReportKind.B,
        object_type=GateObjectType.GROUP,
        scope_parent=GateObjectType.TRIAL,
        applicability_predicate_id="always_applicable",
        required_context_fields=("numeric_value", "denominator", "analysis_population"),
        allowed_source_roles=(
            SourceRole.PRIMARY_TRIAL_REPORT,
            SourceRole.CLINICAL_TRIAL_REGISTRY,
        ),
        minimum_disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        user_label_zh="组别基线样本量",
        missing_impact_zh="无法确认各可比较组的基线规模",
        user_next_step_zh="请提供主要试验报告或官方登记中的组别基线样本量与人群",
    )
    acceptable = _binding(
        binding_id="binding-acceptable",
        unit_id="b_baseline_sample_size",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=120,
        denominator=120,
        analysis_population="全分析集",
        source_location="主要论文基线表",
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        source_role=SourceRole.PRIMARY_TRIAL_REPORT,
    )
    assert (
        evaluate_unit_decision(
            unit,
            object_id="product-a",
            applicable=True,
            applicability_justified=True,
            bindings=(acceptable,),
        ).outcome
        is GateUnitOutcome.SATISFIED
    )

    disallowed_role = _binding(
        binding_id="binding-disallowed-role",
        unit_id="b_baseline_sample_size",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=120,
        denominator=120,
        analysis_population="全分析集",
        source_location="企业披露",
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        source_role=SourceRole.COMPANY_DISCLOSURE,
    )
    assert (
        evaluate_unit_decision(
            unit,
            object_id="product-a",
            applicable=True,
            applicability_justified=True,
            bindings=(disallowed_role,),
        ).outcome
        is GateUnitOutcome.BLOCKED
    )

    below_floor = _binding(
        binding_id="binding-below-floor",
        unit_id="b_baseline_sample_size",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=120,
        denominator=120,
        analysis_population="全分析集",
        source_location="会议披露摘要",
        disclosure_maturity=DisclosureMaturity.ATTRIBUTABLE_NUMERIC_DISCLOSURE,
        source_role=SourceRole.PRIMARY_TRIAL_REPORT,
    )
    assert (
        evaluate_unit_decision(
            unit,
            object_id="product-a",
            applicable=True,
            applicability_justified=True,
            bindings=(below_floor,),
        ).outcome
        is GateUnitOutcome.BLOCKED
    )


@pytest.mark.parametrize(
    ("field", "unknown"),
    [
        ("allowed_source_roles", _UNKNOWN_SOURCE_ROLE),
        ("minimum_disclosure_maturity", _UNKNOWN_MATURITY),
        ("accepted_fact_states", _UNKNOWN_FACT_STATE),
        ("conflict_strategy", _UNKNOWN_CONFLICT_STRATEGY),
        ("missing_strategy", _UNKNOWN_MISSING_STRATEGY),
        ("blocking_level", _UNKNOWN_BLOCKING_LEVEL),
        ("object_type", _UNKNOWN_OBJECT_TYPE),
        ("report_kind", _UNKNOWN_REPORT_KIND),
    ],
)
def test_gate_spec_uses_closed_source_role_maturity_fact_state_and_conflict_enums(
    field: str, unknown: object
) -> None:
    with pytest.raises(PydanticValidationError):
        _unit(**{field: unknown})

    document = _spec_document()
    unit = document["units"][0]
    assert isinstance(unit, dict)
    unit[field] = unknown
    with pytest.raises(JsonSchemaValidationError):
        _spec_validator().validate(document)


def test_gate_spec_rejects_unknown_vocabulary_maturity_in_yaml_and_schema() -> None:
    payload = _spec_document()
    vocabulary = payload["vocabulary"]
    assert isinstance(vocabulary, dict)
    vocabulary["development_maturity"] = ["preclinical", "magic_stage"]
    with pytest.raises(JsonSchemaValidationError):
        _spec_validator().validate(payload)

    from ci_workflow.gates.models import GateVocabulary

    with pytest.raises(PydanticValidationError):
        GateVocabulary.model_validate(
            {
                "development_maturity": ["preclinical", "magic_stage"],
                "clinical_result_states": ["no_eligible_clinical_trial"],
                "observation_kinds": ["observed_result"],
                "result_bearing_source_roles": ["clinical_trial_registry"],
            }
        )


def test_required_unresolved_conflict_blocks() -> None:
    unresolved = _binding(
        binding_id="binding-conflict",
        disclosure_state=FactDisclosureState.CONFLICTING,
        conflict_disposition=ConflictDisposition.OPEN_CONFLICT_PRESERVED,
        numeric_value=10.0,
    )
    critical = _unit(conflict_strategy=ConflictStrategy.RESOLVED_ONLY)
    blocked = evaluate_unit_decision(
        critical,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(unresolved,),
    )
    assert blocked.outcome is GateUnitOutcome.BLOCKED

    preserved_open = _unit(
        unit_id="b_trial_disposition",
        report_kind=ReportKind.B,
        blocking_level=GateBlockingLevel.EXTENSION,
        applicability_predicate_id="always_applicable",
        required_context_fields=(),
        missing_strategy=MissingStrategy.PRESERVE_DISCLOSURE_STATE,
        conflict_strategy=ConflictStrategy.PRESERVE_OPEN,
        user_label_zh="试验完成与受试者处置字段",
        missing_impact_zh="完成与处置字段缺失不影响报告通过，将保留真实披露状态",
        user_next_step_zh="如已公开，请提供筛选、随机、完成与退出等流转数值来源",
    )
    extension = evaluate_unit_decision(
        preserved_open,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(
            _binding(
                binding_id="binding-disposition-conflict",
                unit_id="b_trial_disposition",
                disclosure_state=FactDisclosureState.CONFLICTING,
                conflict_disposition=ConflictDisposition.OPEN_CONFLICT_PRESERVED,
                numeric_value=10.0,
            ),
        ),
    )
    assert extension.outcome is GateUnitOutcome.EXTENSION_MISSING
    assert extension.blocking is False
    assert extension.disclosure_state is FactDisclosureState.CONFLICTING

    resolved = _binding(
        binding_id="binding-resolved",
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        numeric_value=8.0,
    )
    satisfied = evaluate_unit_decision(
        critical,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(resolved,),
    )
    assert satisfied.outcome is GateUnitOutcome.SATISFIED


@pytest.mark.parametrize(
    "state",
    [
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.CONFLICTING,
        FactDisclosureState.NOT_APPLICABLE,
    ],
    ids=lambda s: s.value,
)
def test_nonblocking_missing_preserves_disclosure_state(
    state: FactDisclosureState,
) -> None:
    unit = _unit(
        unit_id="b_trial_disposition",
        report_kind=ReportKind.B,
        blocking_level=GateBlockingLevel.EXTENSION,
        applicability_predicate_id="always_applicable",
        required_context_fields=(),
        missing_strategy=MissingStrategy.PRESERVE_DISCLOSURE_STATE,
        conflict_strategy=ConflictStrategy.PRESERVE_OPEN,
        user_label_zh="试验完成与受试者处置字段",
        missing_impact_zh="完成与处置字段缺失不影响报告通过，将保留真实披露状态",
        user_next_step_zh="如已公开，请提供筛选、随机、完成与退出等流转数值来源",
    )
    binding = _binding(
        binding_id="binding-disposition",
        unit_id="b_trial_disposition",
        disclosure_state=state,
        numeric_value=None,
        denominator=None,
        source_location=None,
        conflict_disposition=(
            ConflictDisposition.OPEN_CONFLICT_PRESERVED
            if state is FactDisclosureState.CONFLICTING
            else ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
        ),
        applicability_predicate_id=(
            "exhaustive_search_proved_no_applicable_object"
            if state is FactDisclosureState.NOT_APPLICABLE
            else None
        ),
    )
    result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(binding,),
    )
    assert result.outcome is GateUnitOutcome.EXTENSION_MISSING
    assert result.blocking is False
    assert result.disclosure_state is state
    assert result.user_note_zh is None


def test_report_fails_when_any_applicable_gate_is_blocked() -> None:
    snapshot = _snapshot()
    identity = _identity_unit()
    safety = _unit()
    identity_binding = _binding(
        binding_id="binding-identity",
        unit_id="a_product_identity",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        denominator=None,
        definition="产品甲",
        source_location="官方登记",
    )
    identity_result = evaluate_unit_decision(
        identity,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(identity_binding,),
    )
    safety_result = evaluate_unit_decision(
        safety,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(),
    )
    assert identity_result.outcome is GateUnitOutcome.SATISFIED
    assert safety_result.outcome is GateUnitOutcome.BLOCKED

    spec = _minimal_spec(identity, safety)
    blocked_report = _aggregate(
        spec, snapshot, (identity_result, safety_result)
    )
    assert blocked_report.decision is ReportDecision.BLOCKED
    assert blocked_report.blocked_unit_ids == ("a_safety_summary",)
    assert blocked_report.applicable_unit_ids == (
        "a_product_identity",
        "a_safety_summary",
    )
    assert "安全性数值摘要" in blocked_report.user_summary_zh
    for internal in ("a_safety_summary", "blocked", "critical"):
        assert internal not in blocked_report.user_summary_zh

    passed_safety = next(
        result
        for result in _matrix_results(spec, snapshot)
        if result.unit_id == "a_safety_summary"
    )
    passed_report = _aggregate(
        spec, snapshot, (identity_result, passed_safety)
    )
    assert passed_report.decision is ReportDecision.PASSED
    assert passed_report.blocked_unit_ids == ()
    assert passed_report.user_summary_zh == "全部适用关键证据单元已满足。"


def test_a_b_c_gate_spec_yaml_files_validate_against_schema() -> None:
    validator = _spec_validator()
    for name, expected_kind, expected_units in (
        ("A-v1", ReportKind.A, 17),
        ("B-v1", ReportKind.B, 19),
        ("C-v1", ReportKind.C, 16),
    ):
        path = ROOT / "policies" / "gates" / f"{name}.yaml"
        spec = GateSpec.from_yaml(path)
        assert spec.report_kind is expected_kind
        assert len(spec.units) == expected_units
        validator.validate(spec.model_dump(mode="json"))
        assert {unit.unit_id for unit in spec.units} == {
            unit.unit_id for unit in spec.units
        }

    a_spec = GateSpec.from_yaml(ROOT / "policies" / "gates" / "A-v1.yaml")
    vocabulary = a_spec.vocabulary
    assert vocabulary is not None
    assert set(vocabulary.development_maturity) == set(DevelopmentMaturity)


def test_gate_result_and_override_documents_validate_against_schemas() -> None:
    snapshot = _snapshot()
    result = ReportGateResult.from_unit_results(
        report_kind=ReportKind.A,
        unit_results=(
            evaluate_unit_decision(
                _identity_unit(),
                object_id="product-a",
                applicable=True,
                applicability_justified=True,
                bindings=(
                    _binding(
                        binding_id="binding-identity",
                        unit_id="a_product_identity",
                        fact_domain=FactDomain.TRIAL_DESIGN,
                        numeric_value=None,
                        denominator=None,
                        definition="产品甲",
                        source_location="官方登记",
                    ),
                ),
            ),
        ),
        evidence_snapshot_id=snapshot.evidence_snapshot_id,
        spec_version="1.0",
        contract_version="1",
        universe_summary=snapshot.universe_summary,
        spec_fingerprint="gate-spec_test",
    )
    result_schema = json.loads(
        (ROOT / "schemas" / "gate-result.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(result_schema)
    result_validator = Draft202012Validator(
        result_schema, format_checker=FormatChecker()
    )
    result_payload = result.model_dump(mode="json")
    result_validator.validate(result_payload)
    with pytest.raises(JsonSchemaValidationError):
        result_validator.validate({**result_payload, "decision": "partial"})
    with pytest.raises(JsonSchemaValidationError):
        result_validator.validate(
            {
                **result_payload,
                "unit_results": [
                    {
                        **result_payload["unit_results"][0],
                        "outcome": "half_satisfied",
                    }
                ],
            }
        )

    override = GateOverride(
        override_id="override-1",
        base_spec_version="1.0",
        parent_contract_version="1",
        child_contract_version="2",
        change_summary_zh="将安全性数值摘要改为必须同时提供分母",
        changed_unit_ids=("a_safety_summary",),
        affected_report_kinds=(ReportKind.A,),
        created_at=datetime(2026, 8, 12, 9, 0, tzinfo=timezone(timedelta(hours=8))),
    )
    override_schema = json.loads(
        (ROOT / "schemas" / "gate-override.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(override_schema)
    override_validator = Draft202012Validator(
        override_schema, format_checker=FormatChecker()
    )
    override_payload = override.model_dump(mode="json")
    override_validator.validate(override_payload)
    with pytest.raises(JsonSchemaValidationError):
        override_validator.validate({**override_payload, "affected_report_kinds": ["D"]})


def test_gate_result_key_binds_report_evidence_rule_contract_and_universe() -> None:
    key = compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        "1.0",
        "1",
        "universe-summary-abc",
        spec_fingerprint="gate-spec-a-v1",
    )
    assert key.startswith("gate-result_")
    assert key != compute_gate_result_key(
        ReportKind.B,
        "snapshot-001",
        "1.0",
        "1",
        "universe-summary-abc",
        spec_fingerprint="gate-spec-a-v1",
    )
    assert key != compute_gate_result_key(
        ReportKind.A,
        "snapshot-002",
        "1.0",
        "1",
        "universe-summary-abc",
        spec_fingerprint="gate-spec-a-v1",
    )
    assert key != compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        "1.1",
        "1",
        "universe-summary-abc",
        spec_fingerprint="gate-spec-a-v1",
    )
    assert key != compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        "1.0",
        "2",
        "universe-summary-abc",
        spec_fingerprint="gate-spec-a-v1",
    )
    assert key != compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        "1.0",
        "1",
        "universe-summary-xyz",
        spec_fingerprint="gate-spec-a-v1",
    )
    assert key != compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        "1.0",
        "1",
        "universe-summary-abc",
        spec_fingerprint="gate-spec-a-v2",
    )


def _closed_snapshot(**overrides: object) -> ApplicableUniverseSnapshot:
    return _snapshot(**overrides)


def test_empty_set_proofs_are_typed_per_object_class_and_digest_bound() -> None:
    snapshot = _closed_snapshot()
    assert_applicable_universe_closed(snapshot)
    assert snapshot.universe_summary.startswith("universe-summary_")

    # 每种空对象类必须有恰好一个对应类型化证明，且证明必须绑定不可变证据版本
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(_closed_snapshot(empty_set_proofs=()))
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _closed_snapshot(
                empty_set_proofs=(_proof_payload("endpoint", "终点"),)
            )
        )

    # 非空对象类不得携带空集合证明
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _closed_snapshot(
                empty_set_proofs=(
                    _proof_payload("trial", "试验"),
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                )
            )
        )

    # 同一对象类证明重复在模型层拒绝
    with pytest.raises(PydanticValidationError):
        _closed_snapshot(
            empty_set_proofs=(
                _proof_payload("endpoint", "终点"),
                _proof_payload("endpoint", "终点"),
                _proof_payload("timepoint", "时间点"),
            )
        )

    # 产品对象类不可能为空，携带证明即拒绝
    with pytest.raises(PydanticValidationError):
        _closed_snapshot(
            empty_set_proofs=(
                _proof_payload("product", "产品"),
                _proof_payload("endpoint", "终点"),
                _proof_payload("timepoint", "时间点"),
            )
        )

    # 未知原因代码在模型层拒绝，任意字符串不得证明空对象类
    with pytest.raises(PydanticValidationError):
        _closed_snapshot(
            empty_set_proofs=(
                {
                    "object_type": "endpoint",
                    "reason_code": "because_i_say_so",
                    "evidence_version_id": "evidence-endpoint-empty-v1",
                    "explanation_zh": "任意理由",
                },
                _proof_payload("timepoint", "时间点"),
            )
        )

    # 证明内容参与宇宙摘要：同类集合不同证明产生不同摘要
    altered = _closed_snapshot(
        empty_set_proofs=(
            {
                "object_type": "endpoint",
                "reason_code": "indication_rule_excludes_object_class",
                "evidence_version_id": "evidence-endpoint-empty-v1",
                "explanation_zh": "适应症规则明确排除终点对象类",
            },
            _proof_payload("timepoint", "时间点"),
        )
    )
    assert altered.universe_summary != snapshot.universe_summary


def test_universe_relationship_graph_is_required_and_rejects_cross_trial_scope_binding() -> None:
    snapshot = _closed_snapshot()
    assert_applicable_universe_closed(snapshot)

    # 缺少产品→试验边
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _closed_snapshot(
                relationship_edges=(
                    _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                ),
            )
        )
    # 缺少试验→比较边
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _closed_snapshot(
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                ),
            )
        )
    # 边引用未知子对象
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _closed_snapshot(
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                    _edge_payload("trial", "trial-1", "endpoint", "endpoint-x"),
                ),
            )
        )
    # 对象标识跨对象类型重复
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _closed_snapshot(trial_ids=("product-a",), empty_set_proofs=())
        )
    # 反向/循环边在模型层拒绝
    with pytest.raises(PydanticValidationError):
        _closed_snapshot(
            relationship_edges=(
                _edge_payload("product", "product-a", "trial", "trial-1"),
                _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                _edge_payload("trial", "trial-1", "group", "group-1"),
                _edge_payload("group", "group-1", "trial", "trial-1"),
            )
        )

    # 跨试验作用域绑定被拒绝，同一路径的绑定被接受
    endpoint_snapshot = _closed_snapshot(
        endpoint_ids=("endpoint-1",),
        empty_set_proofs=(_proof_payload("timepoint", "时间点"),),
        relationship_edges=(
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
            _edge_payload("trial", "trial-1", "group", "group-2"),
            _edge_payload("comparison", "comparison-1", "group", "group-1"),
            _edge_payload("comparison", "comparison-1", "group", "group-2"),
            _edge_payload("trial", "trial-1", "endpoint", "endpoint-1"),
            _edge_payload("endpoint", "endpoint-1", "group", "group-1"),
            _edge_payload("comparison", "comparison-1", "endpoint", "endpoint-1"),
        ),
    )
    assert_applicable_universe_closed(endpoint_snapshot)
    cross_trial = _binding(
        binding_id="binding-cross-trial",
        unit_id="b_core_efficacy_endpoint",
        object_id="endpoint-1",
        endpoint_id="endpoint-1",
        trial_id="trial-2",
    )
    with pytest.raises(GateEvaluationError):
        assert_bindings_in_universe(endpoint_snapshot, (cross_trial,))
    coherent = _binding(
        binding_id="binding-coherent",
        unit_id="b_core_efficacy_endpoint",
        object_id="endpoint-1",
        endpoint_id="endpoint-1",
        trial_id="trial-1",
    )
    assert_bindings_in_universe(endpoint_snapshot, (coherent,))


def test_a_always_applicable_critical_unit_rejects_unproven_not_applicable_binding() -> None:
    identity = _unit(
        unit_id="a_product_identity",
        applicability_predicate_id="always_applicable",
        required_context_fields=(),
        accepted_fact_states=(
            FactDisclosureState.REPORTED_VALUE,
            FactDisclosureState.REPORTED_ZERO,
            FactDisclosureState.NOT_APPLICABLE,
        ),
        user_label_zh="产品规范身份与别名",
        missing_impact_zh="无法确认产品身份，影响竞品识别与定位",
        user_next_step_zh="请提供官方登记或监管材料中的产品名称、代码与别名",
    )
    unproven_na = _binding(
        binding_id="binding-na-arbitrary",
        unit_id="a_product_identity",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        denominator=None,
        definition=None,
        disclosure_state=FactDisclosureState.NOT_APPLICABLE,
        applicability_predicate_id="arbitrary_not_applicable",
    )
    result = evaluate_unit_decision(
        identity,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(unproven_na,),
    )
    assert result.outcome is GateUnitOutcome.BLOCKED
    assert result.failure_code == "missing_required_evidence"

    # 匹配受控条件谓词且由版本化规则合同承认时，不适用绑定可以满足条件单元
    conditional = _unit(
        unit_id="c_region_visit_operational",
        report_kind=ReportKind.C,
        applicability_predicate_id="region_visit_operational_key",
        required_context_fields=(),
        accepted_fact_states=(
            FactDisclosureState.REPORTED_VALUE,
            FactDisclosureState.REPORTED_ZERO,
            FactDisclosureState.NOT_APPLICABLE,
        ),
        user_label_zh="地区、访视与操作特征",
        missing_impact_zh="无法确认关键地区、访视或操作特征",
        user_next_step_zh="请提供官方登记中的地区、访视与操作信息",
    )
    snapshot = _closed_snapshot(
        applicable_conditional_predicates=("region_visit_operational_key",)
    )
    proven_na = _binding(
        binding_id="binding-na-recognized",
        unit_id="c_region_visit_operational",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        denominator=None,
        definition=None,
        disclosure_state=FactDisclosureState.NOT_APPLICABLE,
        applicability_predicate_id="region_visit_operational_key",
    )
    recognized = evaluate_unit_decision(
        conditional,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(proven_na,),
        snapshot=snapshot,
    )
    assert recognized.outcome is GateUnitOutcome.SATISFIED

    # 无版本化规则合同承认时，即使谓词匹配也不得满足
    unverified = evaluate_unit_decision(
        conditional,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(proven_na,),
    )
    assert unverified.outcome is GateUnitOutcome.BLOCKED


def test_derive_result_bearing_requires_eligible_trial_scope() -> None:
    snapshot = _closed_snapshot()
    assert_applicable_universe_closed(snapshot)

    observed_without_trial = _binding(
        binding_id="binding-no-trial",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
        trial_id=None,
    )
    assert derive_result_bearing(snapshot, (observed_without_trial,)) is False

    observed_unknown_trial = _binding(
        binding_id="binding-unknown-trial",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
        trial_id="trial-999",
    )
    with pytest.raises(GateEvaluationError):
        derive_result_bearing(snapshot, (observed_unknown_trial,))

    observed_eligible = _binding(
        binding_id="binding-eligible-trial",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
        trial_id="trial-1",
    )
    assert derive_result_bearing(snapshot, (observed_eligible,)) is True


def test_aggregate_report_rejects_satisfied_unit_below_threshold() -> None:
    with pytest.raises(PydanticValidationError):
        GateUnitResult(
            unit_id="a_product_identity",
            report_kind=ReportKind.A,
            object_id="product-a",
            applicable=True,
            outcome=GateUnitOutcome.SATISFIED,
            blocking=False,
            threshold=1,
            satisfied_count=0,
        )
    with pytest.raises(PydanticValidationError):
        GateUnitResult(
            unit_id="a_product_identity",
            report_kind=ReportKind.A,
            object_id="product-a",
            applicable=True,
            outcome=GateUnitOutcome.BLOCKED,
            blocking=False,
            threshold=1,
            satisfied_count=0,
        )
    with pytest.raises(PydanticValidationError):
        GateUnitResult(
            unit_id="a_product_identity",
            report_kind=ReportKind.A,
            object_id="product-a",
            applicable=False,
            outcome=GateUnitOutcome.NOT_APPLICABLE,
            blocking=False,
            threshold=1,
            satisfied_count=1,
        )
    with pytest.raises(PydanticValidationError):
        GateUnitResult(
            unit_id="a_product_identity",
            report_kind=ReportKind.A,
            object_id="product-a",
            applicable=True,
            outcome=GateUnitOutcome.EXTENSION_MISSING,
            blocking=False,
            threshold=1,
            satisfied_count=1,
        )
    consistent = GateUnitResult(
        unit_id="a_product_identity",
        report_kind=ReportKind.A,
        object_id="product-a",
        applicable=True,
        outcome=GateUnitOutcome.SATISFIED,
        blocking=False,
        threshold=1,
        satisfied_count=1,
        fact_version_ids=("fact-v1",),
    )
    assert consistent.outcome is GateUnitOutcome.SATISFIED


def test_gate_result_binds_canonical_spec_fingerprint() -> None:
    spec = _minimal_spec(_identity_unit())
    fingerprint = spec.spec_fingerprint
    assert fingerprint.startswith("gate-spec_")
    assert fingerprint == _minimal_spec(_identity_unit()).spec_fingerprint

    snapshot = _closed_snapshot()
    unit_result = evaluate_unit_decision(
        _identity_unit(),
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(
            _binding(
                binding_id="binding-identity",
                unit_id="a_product_identity",
                fact_domain=FactDomain.TRIAL_DESIGN,
                numeric_value=None,
                denominator=None,
                definition="产品甲",
                source_location="官方登记",
            ),
        ),
    )
    report = _aggregate(spec, snapshot, (unit_result,))
    assert report.spec_fingerprint == fingerprint
    # 同批在内容不同的规格下必须失败关闭（指纹不一致），不得重新绑定生成结果
    tampered_spec = _minimal_spec(_identity_unit(), version="1.1")
    batch = _GateEvaluationBatch.from_evaluation(
        spec=spec, snapshot=snapshot, unit_results=(unit_result,)
    )
    with pytest.raises(GateEvaluationError, match="规则指纹"):
        _aggregate_report_gates(
            spec=tampered_spec,
            snapshot=snapshot,
            batch=batch,
            contract_version="1",
        )


def test_group_relationships_allow_multiple_endpoint_and_comparison_associations_without_forcing_optional_scope() -> None:  # noqa: E501
    snapshot = _snapshot(
        comparison_ids=("comparison-1", "comparison-2", "comparison-3"),
        endpoint_ids=("endpoint-1", "endpoint-2", "endpoint-3"),
        group_ids=("group-1", "group-2", "group-3"),
        empty_set_proofs=(_proof_payload("timepoint", "时间点"),),
        relationship_edges=(
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-2"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-3"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
            _edge_payload("trial", "trial-1", "group", "group-2"),
            _edge_payload("trial", "trial-1", "group", "group-3"),
            _edge_payload("comparison", "comparison-1", "group", "group-1"),
            _edge_payload("comparison", "comparison-1", "group", "group-2"),
            _edge_payload("comparison", "comparison-2", "group", "group-1"),
            _edge_payload("comparison", "comparison-2", "group", "group-2"),
            _edge_payload("comparison", "comparison-3", "group", "group-2"),
            _edge_payload("comparison", "comparison-3", "group", "group-3"),
            _edge_payload("trial", "trial-1", "endpoint", "endpoint-1"),
            _edge_payload("trial", "trial-1", "endpoint", "endpoint-2"),
            _edge_payload("trial", "trial-1", "endpoint", "endpoint-3"),
            _edge_payload("endpoint", "endpoint-1", "group", "group-1"),
            _edge_payload("endpoint", "endpoint-2", "group", "group-1"),
        ),
    )
    assert_applicable_universe_closed(snapshot)

    # 组别基线与安全绑定不带比较/终点作用域是合法路径（trial→group 匹配即可）
    baseline = _binding(
        binding_id="binding-baseline",
        unit_id="b_baseline_sample_size",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=120,
        denominator=120,
        comparison_id=None,
        endpoint_id=None,
        analysis_population="全分析集",
        source_location="主要论文基线表",
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
    )
    assert_bindings_in_universe(snapshot, (baseline,))

    safety = _binding(
        binding_id="binding-safety",
        unit_id="b_safety_teae",
        fact_domain=FactDomain.SAFETY,
        numeric_value=25,
        denominator=120,
        comparison_id=None,
        endpoint_id=None,
        event_definition="TEAE",
        time_window="治疗期间",
        source_location="登记结果安全性表",
    )
    assert_bindings_in_universe(snapshot, (safety,))

    # 显式携带的关联作用域必须精确匹配图中的关联边
    associated_comparison = _binding(
        binding_id="binding-assoc-comparison",
        unit_id="b_core_efficacy_endpoint",
        object_id="comparison-1",
        comparison_id="comparison-1",
        endpoint_id=None,
        fact_domain=FactDomain.EFFICACY,
        numeric_value=12.5,
        source_location="登记结果疗效表",
    )
    assert_bindings_in_universe(snapshot, (associated_comparison,))

    associated_endpoint = _binding(
        binding_id="binding-assoc-endpoint",
        unit_id="b_core_efficacy_endpoint",
        object_id="endpoint-1",
        endpoint_id="endpoint-1",
        comparison_id=None,
        fact_domain=FactDomain.EFFICACY,
        numeric_value=12.5,
        source_location="登记结果疗效表",
    )
    assert_bindings_in_universe(snapshot, (associated_endpoint,))

    # 已知但与组别无关联边的比较/终点不得拼接
    mismatched_comparison = _binding(
        binding_id="binding-mismatch-comparison",
        unit_id="b_core_efficacy_endpoint",
        object_id="comparison-3",
        comparison_id="comparison-3",
        endpoint_id=None,
        fact_domain=FactDomain.EFFICACY,
        numeric_value=12.5,
        source_location="登记结果疗效表",
    )
    with pytest.raises(GateEvaluationError):
        assert_bindings_in_universe(snapshot, (mismatched_comparison,))

    mismatched_endpoint = _binding(
        binding_id="binding-mismatch-endpoint",
        unit_id="b_core_efficacy_endpoint",
        object_id="endpoint-3",
        endpoint_id="endpoint-3",
        comparison_id=None,
        fact_domain=FactDomain.EFFICACY,
        numeric_value=12.5,
        source_location="登记结果疗效表",
    )
    with pytest.raises(GateEvaluationError):
        assert_bindings_in_universe(snapshot, (mismatched_endpoint,))

    # 同一组别的多个关联边允许，但完全相同的边不得重复
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _snapshot(
                comparison_ids=("comparison-1",),
                endpoint_ids=(),
                empty_set_proofs=(
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                ),
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                    _edge_payload("comparison", "comparison-1", "group", "group-1"),
                    _edge_payload("comparison", "comparison-1", "group", "group-1"),
                ),
            )
        )


def test_trial_design_evidence_is_per_trial_and_comparison_requires_two_groups() -> None:
    # 单臂试验：无比较边，合法
    single_arm = _snapshot(
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=("group-1",),
        empty_set_proofs=(
            _proof_payload("comparison", "比较"),
            _proof_payload("endpoint", "终点"),
            _proof_payload("timepoint", "时间点"),
        ),
        relationship_edges=(
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
        ),
        trial_design_evidence=(_design_record("trial-1", "single_arm"),),
    )
    assert_applicable_universe_closed(single_arm)

    # 单臂试验携带比较边 → 失败关闭
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _snapshot(
                comparison_ids=("comparison-1",),
                empty_set_proofs=(
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                ),
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                    _edge_payload("trial", "trial-1", "group", "group-2"),
                    _edge_payload("comparison", "comparison-1", "group", "group-1"),
                    _edge_payload("comparison", "comparison-1", "group", "group-2"),
                ),
                trial_design_evidence=(_design_record("trial-1", "single_arm"),),
            )
        )

    # 比较设计试验缺少比较边 → 失败关闭
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _snapshot(
                comparison_ids=(),
                empty_set_proofs=(
                    _proof_payload("comparison", "比较"),
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                ),
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                    _edge_payload("trial", "trial-1", "group", "group-2"),
                ),
            )
        )

    # 比较必须关联至少两个不同组别
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _snapshot(
                empty_set_proofs=(
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                ),
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                    _edge_payload("comparison", "comparison-1", "group", "group-1"),
                ),
            )
        )

    # 比较的两个组别必须全部位于所属试验内（跨试验拼接失败关闭）
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _snapshot(
                product_ids=("product-a", "product-b"),
                trial_ids=("trial-1", "trial-2"),
                comparison_ids=("comparison-1",),
                group_ids=("group-1", "group-2"),
                empty_set_proofs=(
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                ),
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("product", "product-b", "trial", "trial-2"),
                    _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                    _edge_payload("trial", "trial-2", "group", "group-2"),
                    _edge_payload("comparison", "comparison-1", "group", "group-1"),
                    _edge_payload("comparison", "comparison-1", "group", "group-2"),
                ),
                trial_design_evidence=(
                    _design_record("trial-1", "comparative"),
                    _design_record("trial-2", "single_arm"),
                ),
            )
        )

    # 每项试验必须有且仅有一条设计证据；无试验时不得有记录
    with pytest.raises(PydanticValidationError):
        _snapshot(trial_design_evidence=())
    with pytest.raises(PydanticValidationError):
        _snapshot(
            trial_design_evidence=(
                _design_record("trial-1", "comparative"),
                _design_record("trial-1", "single_arm"),
            )
        )
    with pytest.raises(PydanticValidationError):
        _snapshot(trial_ids=(), trial_design_evidence=(_design_record("trial-1", "single_arm"),))

    # 设计证据内容参与宇宙摘要
    altered = _snapshot(
        trial_design_evidence=(_design_record("trial-1", "single_arm"),)
    )
    assert altered.universe_summary != _snapshot().universe_summary


def test_gate_evaluator_rejects_cross_product_trial_evidence_stitching() -> None:
    snapshot = _snapshot(
        product_ids=("product-a", "product-b"),
        trial_ids=("trial-1", "trial-2"),
        comparison_ids=(),
        group_ids=("group-1", "group-2"),
        empty_set_proofs=(
            _proof_payload("comparison", "比较"),
            _proof_payload("endpoint", "终点"),
            _proof_payload("timepoint", "时间点"),
        ),
        relationship_edges=(
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("product", "product-b", "trial", "trial-2"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
            _edge_payload("trial", "trial-2", "group", "group-2"),
        ),
        trial_design_evidence=(
            _design_record("trial-1", "single_arm"),
            _design_record("trial-2", "single_arm"),
        ),
    )
    assert_applicable_universe_closed(snapshot)

    stitched = _binding(
        binding_id="binding-cross-product",
        unit_id="a_maturity",
        object_id="product-a",
        trial_id="trial-2",
        comparison_id=None,
        group_id=None,
        endpoint_id=None,
    )
    with pytest.raises(GateEvaluationError):
        assert_bindings_in_universe(snapshot, (stitched,))

    coherent = _binding(
        binding_id="binding-coherent-product",
        unit_id="a_maturity",
        object_id="product-a",
        trial_id="trial-1",
        comparison_id=None,
        group_id=None,
        endpoint_id=None,
    )
    assert_bindings_in_universe(snapshot, (coherent,))

    bearing_stitched = _binding(
        binding_id="binding-bearing-stitched",
        unit_id="a_efficacy_summary",
        object_id="product-a",
        trial_id="trial-2",
        comparison_id=None,
        group_id=None,
        endpoint_id=None,
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
    )
    with pytest.raises(GateEvaluationError):
        derive_result_bearing(snapshot, (bearing_stitched,))


def test_comparison_endpoint_association_is_explicit_and_digest_bound() -> None:
    snapshot = _snapshot(
        comparison_ids=("comparison-1",),
        endpoint_ids=("endpoint-1",),
        empty_set_proofs=(_proof_payload("timepoint", "时间点"),),
        relationship_edges=(
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
            _edge_payload("trial", "trial-1", "group", "group-2"),
            _edge_payload("comparison", "comparison-1", "group", "group-1"),
            _edge_payload("comparison", "comparison-1", "group", "group-2"),
            _edge_payload("trial", "trial-1", "endpoint", "endpoint-1"),
            _edge_payload("comparison", "comparison-1", "endpoint", "endpoint-1"),
        ),
    )
    assert_applicable_universe_closed(snapshot)

    effect = _binding(
        binding_id="binding-effect",
        unit_id="b_core_efficacy_endpoint",
        object_id="comparison-1",
        comparison_id="comparison-1",
        endpoint_id="endpoint-1",
        group_id=None,
        fact_domain=FactDomain.EFFICACY,
        numeric_value=5.0,
    )
    assert_bindings_in_universe(snapshot, (effect,))

    without_edge = _snapshot(
        comparison_ids=("comparison-1",),
        endpoint_ids=("endpoint-1",),
        empty_set_proofs=(_proof_payload("timepoint", "时间点"),),
        relationship_edges=(
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
            _edge_payload("trial", "trial-1", "group", "group-2"),
            _edge_payload("comparison", "comparison-1", "group", "group-1"),
            _edge_payload("comparison", "comparison-1", "group", "group-2"),
            _edge_payload("trial", "trial-1", "endpoint", "endpoint-1"),
        ),
    )
    assert_applicable_universe_closed(without_edge)
    with pytest.raises(GateEvaluationError):
        assert_bindings_in_universe(without_edge, (effect,))
    # 关联边内容参与宇宙摘要
    assert without_edge.universe_summary != snapshot.universe_summary


def test_research_role_set_id_changes_universe_summary() -> None:
    base = _snapshot()
    changed = _snapshot(research_role_set_id="research-roles-v2")
    assert changed.universe_summary != base.universe_summary
    assert changed.research_role_set_id == "research-roles-v2"


def test_gate_binding_rejects_nonfinite_numeric_values() -> None:
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(PydanticValidationError, match="有限数值"):
            _binding(numeric_value=value)


def test_gate_unit_enforces_allowed_fact_domain_and_observation_kind() -> None:
    unit = _unit(
        allowed_fact_domains=(FactDomain.EFFICACY,),
        allowed_observation_kinds=(ObservationKind.OBSERVED_RESULT,),
    )
    wrong_domain = _binding(
        binding_id="binding-wrong-domain",
        fact_domain=FactDomain.SAFETY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
    )
    result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(wrong_domain,),
    )
    assert result.outcome is GateUnitOutcome.BLOCKED

    planned = _binding(
        binding_id="binding-planned",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.PLANNED_VALUE,
        numeric_value=20.0,
    )
    result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(planned,),
    )
    assert result.outcome is GateUnitOutcome.BLOCKED

    correct = _binding(
        binding_id="binding-correct",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
    )
    result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(correct,),
    )
    assert result.outcome is GateUnitOutcome.SATISFIED

    with pytest.raises(PydanticValidationError):
        _unit(allowed_fact_domains=("mechanism",))
    with pytest.raises(PydanticValidationError):
        _unit(allowed_observation_kinds=("estimated_value",))


def test_evaluate_unit_decision_cannot_force_always_applicable_unit_to_not_applicable() -> None:
    identity = _identity_unit()
    with pytest.raises(GateEvaluationError):
        evaluate_unit_decision(
            identity,
            object_id="product-a",
            applicable=False,
            applicability_justified=True,
            bindings=(),
        )


def test_threshold_counts_distinct_fact_versions_not_duplicate_bindings() -> None:
    unit = _unit(threshold=2)
    duplicate = (
        _binding(binding_id="binding-dup-1", fact_version_id="same-fact-v1"),
        _binding(binding_id="binding-dup-2", fact_version_id="same-fact-v1"),
    )
    result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=duplicate,
    )
    assert result.outcome is GateUnitOutcome.BLOCKED
    assert result.satisfied_count == 1
    assert result.fact_version_ids == ("same-fact-v1",)

    distinct = (
        _binding(binding_id="binding-a", fact_version_id="fact-a-v1"),
        _binding(binding_id="binding-b", fact_version_id="fact-b-v1"),
    )
    result = evaluate_unit_decision(
        unit,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=distinct,
    )
    assert result.outcome is GateUnitOutcome.SATISFIED
    assert result.satisfied_count == 2
    assert result.fact_version_ids == ("fact-a-v1", "fact-b-v1")


def test_aggregate_rejects_malformed_or_cross_report_unit_results() -> None:
    snapshot = _snapshot()
    identity = _identity_unit()
    spec = _minimal_spec(identity)
    identity_result = evaluate_unit_decision(
        identity,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(
            _binding(
                binding_id="binding-identity",
                unit_id="a_product_identity",
                fact_domain=FactDomain.TRIAL_DESIGN,
                numeric_value=None,
                denominator=None,
                definition="产品甲",
                source_location="官方登记",
            ),
        ),
    )

    # 未知单元：评估批可构造（内容自洽），聚合边界拒绝
    with pytest.raises(GateEvaluationError, match="不属于当前规格"):
        _aggregate_report_gates(
            spec=spec,
            snapshot=snapshot,
            batch=_GateEvaluationBatch.from_evaluation(
                spec=spec,
                snapshot=snapshot,
                unit_results=(
                    GateUnitResult(
                        unit_id="b_unknown",
                        report_kind=ReportKind.A,
                        object_id="product-a",
                        applicable=True,
                        outcome=GateUnitOutcome.BLOCKED,
                        blocking=True,
                        threshold=1,
                        satisfied_count=0,
                        user_note_zh="测试",
                    ),
                ),
            ),
            contract_version="1",
        )
    # 跨报告类型结果：评估批构造阶段即拒绝
    with pytest.raises(PydanticValidationError, match="报告类型"):
        _GateEvaluationBatch.from_evaluation(
            spec=spec,
            snapshot=snapshot,
            unit_results=(
                GateUnitResult(
                    unit_id="a_product_identity",
                    report_kind=ReportKind.B,
                    object_id="product-a",
                    applicable=True,
                    outcome=GateUnitOutcome.SATISFIED,
                    blocking=False,
                    threshold=1,
                    satisfied_count=1,
                    fact_version_ids=("fact-v1",),
                ),
            ),
        )
    # 重复 (unit_id, object_id) 对：评估批构造阶段即拒绝
    with pytest.raises(PydanticValidationError, match="不得重复"):
        _GateEvaluationBatch.from_evaluation(
            spec=spec,
            snapshot=snapshot,
            unit_results=(identity_result, identity_result),
        )
    # 无条件适用单元的不适用结果：聚合边界拒绝
    with pytest.raises(GateEvaluationError, match="无条件适用"):
        _aggregate_report_gates(
            spec=spec,
            snapshot=snapshot,
            batch=_GateEvaluationBatch.from_evaluation(
                spec=spec,
                snapshot=snapshot,
                unit_results=(
                    GateUnitResult(
                        unit_id="a_product_identity",
                        report_kind=ReportKind.A,
                        object_id="product-a",
                        applicable=False,
                        outcome=GateUnitOutcome.NOT_APPLICABLE,
                        blocking=False,
                        threshold=1,
                        satisfied_count=0,
                    ),
                ),
            ),
            contract_version="1",
        )
    # 关键单元的扩展缺失结果：聚合边界拒绝
    with pytest.raises(GateEvaluationError, match="扩展缺失"):
        _aggregate_report_gates(
            spec=spec,
            snapshot=snapshot,
            batch=_GateEvaluationBatch.from_evaluation(
                spec=spec,
                snapshot=snapshot,
                unit_results=(
                    GateUnitResult(
                        unit_id="a_product_identity",
                        report_kind=ReportKind.A,
                        object_id="product-a",
                        applicable=True,
                        outcome=GateUnitOutcome.EXTENSION_MISSING,
                        blocking=False,
                        threshold=1,
                        satisfied_count=0,
                    ),
                ),
            ),
            contract_version="1",
        )

    passed = _aggregate(spec, snapshot, (identity_result,))
    assert passed.decision is ReportDecision.PASSED


def test_report_gate_result_rejects_direct_decision_or_summary_inconsistency() -> None:
    snapshot = _snapshot()
    identity = _identity_unit()
    safety = _unit()
    spec = _minimal_spec(identity, safety)
    identity_result = evaluate_unit_decision(
        identity,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(
            _binding(
                binding_id="binding-identity",
                unit_id="a_product_identity",
                fact_domain=FactDomain.TRIAL_DESIGN,
                numeric_value=None,
                denominator=None,
                definition="产品甲",
                source_location="官方登记",
            ),
        ),
    )
    safety_result = evaluate_unit_decision(
        safety,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(),
    )
    passed_safety = next(
        result
        for result in _matrix_results(spec, snapshot)
        if result.unit_id == "a_safety_summary"
    )
    passed = _aggregate(spec, snapshot, (identity_result, passed_safety))
    passed_payload = passed.model_dump()
    with pytest.raises(PydanticValidationError, match="合取不一致"):
        ReportGateResult.model_validate({**passed_payload, "decision": "blocked"})
    with pytest.raises(PydanticValidationError, match="用户说明"):
        ReportGateResult.model_validate(
            {**passed_payload, "user_summary_zh": "伪造说明"}
        )
    with pytest.raises(PydanticValidationError, match="结果键"):
        ReportGateResult.model_validate(
            {**passed_payload, "result_key": "gate-result_forged"}
        )
    with pytest.raises(PydanticValidationError, match="报告类型"):
        ReportGateResult.model_validate(
            {
                **passed_payload,
                "unit_results": [
                    {**unit, "report_kind": "B"}
                    for unit in passed_payload["unit_results"]
                ],
            }
        )
    with pytest.raises(PydanticValidationError, match="重复"):
        ReportGateResult.model_validate(
            {
                **passed_payload,
                "unit_results": [
                    *passed_payload["unit_results"],
                    *passed_payload["unit_results"],
                ],
            }
        )

    blocked = _aggregate(spec, snapshot, (identity_result, safety_result))
    blocked_payload = blocked.model_dump()
    with pytest.raises(PydanticValidationError, match="中文用户说明"):
        ReportGateResult.model_validate(
            {
                **blocked_payload,
                "unit_results": [
                    {**unit, "user_note_zh": None}
                    if unit["outcome"] == "blocked"
                    else unit
                    for unit in blocked_payload["unit_results"]
                ],
            }
        )


def test_aggregate_rejects_incomplete_spec_unit_result_set() -> None:
    """权威聚合必须接受规范快照并校验完整 (unit_id, object_id) 矩阵。"""
    snapshot = _snapshot()
    identity = _identity_unit()
    safety = _unit()
    spec = _minimal_spec(identity, safety)
    identity_result = evaluate_unit_decision(
        identity,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(_identity_binding(),),
    )

    # 缺失矩阵中的一个对象结果 → 失败关闭
    with pytest.raises(GateEvaluationError, match="完整矩阵"):
        _aggregate(spec, snapshot, (identity_result,))
    # 同一单元在多产品宇宙中漏掉第二个对象，也不得因 unit_id 已出现而通过。
    multi_product_snapshot = _snapshot(product_ids=("product-a", "product-b"))
    identity_only_spec = _minimal_spec(identity)
    with pytest.raises(GateEvaluationError, match="完整矩阵"):
        _aggregate(identity_only_spec, multi_product_snapshot, (identity_result,))
    # 矩阵外多余结果 → 失败关闭
    extra_result = GateUnitResult(
        unit_id="a_product_identity",
        report_kind=ReportKind.A,
        object_id="product-unknown",
        applicable=True,
        outcome=GateUnitOutcome.SATISFIED,
        blocking=False,
        threshold=1,
        satisfied_count=1,
        fact_version_ids=("fact-extra-v1",),
    )
    with pytest.raises(GateEvaluationError, match="完整矩阵"):
        _aggregate(spec, snapshot, (identity_result, extra_result))
    # 完整矩阵 → 通过；结果标识必须来自已验证快照，而非调用方独立字符串
    safety_result = GateUnitResult(
        unit_id="a_safety_summary",
        report_kind=ReportKind.A,
        object_id="product-a",
        applicable=True,
        outcome=GateUnitOutcome.SATISFIED,
        blocking=False,
        threshold=1,
        satisfied_count=1,
        fact_version_ids=("fact-safety-v1",),
    )
    report = _aggregate(spec, snapshot, (identity_result, safety_result))
    assert report.decision is ReportDecision.PASSED
    assert report.evidence_snapshot_id == snapshot.evidence_snapshot_id
    assert report.universe_summary == snapshot.universe_summary
    assert report.contract_version == "1"


def test_aggregate_rejects_unit_result_batch_from_different_snapshot_or_spec() -> None:
    """评估批绑定宇宙与规格身份：换快照、换规格或伪造批键均不得聚合。"""
    identity = _identity_unit()
    safety = _unit()
    spec = _minimal_spec(identity, safety)
    snapshot = _snapshot()

    results = _matrix_results(spec, snapshot)
    batch = _GateEvaluationBatch.from_evaluation(
        spec=spec, snapshot=snapshot, unit_results=results
    )
    batch_bytes = batch.model_dump_json()

    # 快照 A 下聚合成功
    report = _aggregate_report_gates(
        spec=spec, snapshot=snapshot, batch=batch, contract_version="1"
    )
    assert report.decision is ReportDecision.PASSED
    assert report.evidence_snapshot_id == snapshot.evidence_snapshot_id

    # 对象集合相同但证据快照不同的快照 B：聚合前必须拒绝
    snapshot_b = _snapshot(evidence_snapshot_id="snapshot-002")
    with pytest.raises(GateEvaluationError, match="证据快照"):
        _aggregate_report_gates(
            spec=spec, snapshot=snapshot_b, batch=batch, contract_version="1"
        )

    # 同版本但内容不同的规格 B（阈值不同 → 指纹不同）：聚合前必须拒绝
    spec_b = _minimal_spec(
        _identity_unit(threshold=2),
        safety,
        version="1.0",
    )
    with pytest.raises(GateEvaluationError, match="规则指纹"):
        _aggregate_report_gates(
            spec=spec_b, snapshot=snapshot, batch=batch, contract_version="1"
        )

    # 伪造批键：模型层直接拒绝
    with pytest.raises(PydanticValidationError, match="批键"):
        _GateEvaluationBatch.model_validate(
            {**batch.model_dump(), "batch_key": "gate-batch_forged"}
        )

    # 源评估批保持字节级不变
    assert batch.model_dump_json() == batch_bytes


def test_aggregate_rejects_model_copy_tampered_batch_key_or_unit_results() -> None:
    """聚合入口必须显式重验评估批：model_copy 绕过 Pydantic 校验不得产生假通过。"""
    identity = _identity_unit()
    safety = _unit()
    spec = _minimal_spec(identity, safety)
    snapshot = _snapshot()
    results = _matrix_results(spec, snapshot)

    # 合法批次聚合通过
    batch = _GateEvaluationBatch.from_evaluation(
        spec=spec, snapshot=snapshot, unit_results=results
    )
    batch_bytes = batch.model_dump_json()
    report = _aggregate_report_gates(
        spec=spec, snapshot=snapshot, batch=batch, contract_version="1"
    )
    assert report.decision is ReportDecision.PASSED

    # 伪造批键：聚合前必须拒绝
    forged_key = batch.model_copy(update={"batch_key": "gate-batch_forged"})
    with pytest.raises(GateEvaluationError, match="批键"):
        _aggregate_report_gates(
            spec=spec, snapshot=snapshot, batch=forged_key, contract_version="1"
        )

    # 嵌套 model_copy 篡改单元结果事实链路（合法数量但内容不同）：聚合前必须拒绝
    tampered_results = tuple(
        result
        if result.unit_id != "a_product_identity"
        else GateUnitResult.model_validate(
            {**result.model_dump(), "fact_version_ids": ("fact-forged",)}
        )
        for result in batch.unit_results
    )
    tampered_batch = batch.model_copy(update={"unit_results": tampered_results})
    with pytest.raises(GateEvaluationError):
        _aggregate_report_gates(
            spec=spec, snapshot=snapshot, batch=tampered_batch, contract_version="1"
        )

    # 源评估批保持字节级不变
    assert batch.model_dump_json() == batch_bytes


def test_public_batch_constructor_rejects_detached_unit_results_from_changed_snapshot_or_spec() -> None:  # noqa: E501
    """公共 API 只暴露评估器原子路径；脱离批/聚合构造不复存在，结果按源重算。"""
    package = importlib.import_module("ci_workflow.gates")
    assert not hasattr(package, "GateEvaluationBatch")
    assert not hasattr(package, "aggregate_report_gates")
    assert "GateEvaluationBatch" not in package.__all__
    assert "aggregate_report_gates" not in package.__all__

    identity = _identity_unit()
    spec_a = _minimal_spec(identity)
    snapshot_a = _snapshot()
    identity_binding = _identity_binding()

    # 快照 A 下公共路径通过
    result_a = evaluate_report(
        spec_a, snapshot_a, (identity_binding,), contract_version="1"
    )
    assert result_a.decision is ReportDecision.PASSED

    # 对象相同的快照 B：公共路径必须用 B 自身重算，不得贴 A 的结果
    snapshot_b = _snapshot(evidence_snapshot_id="snapshot-002")
    result_b = evaluate_report(
        spec_a, snapshot_b, (identity_binding,), contract_version="1"
    )
    assert result_b.evidence_snapshot_id == snapshot_b.evidence_snapshot_id
    assert result_b.universe_summary == snapshot_b.universe_summary
    assert result_b.result_key != result_a.result_key

    # 同版本但阈值提高的规格：公共路径必须重算并阻断旧阈值结果
    spec_raised = _minimal_spec(_identity_unit(threshold=2), version="1.0")
    result_raised = evaluate_report(
        spec_raised, snapshot_a, (identity_binding,), contract_version="1"
    )
    identity_results = [
        r for r in result_raised.unit_results
        if r.unit_id == "a_product_identity"
    ]
    assert len(identity_results) == 1
    assert identity_results[0].outcome is GateUnitOutcome.BLOCKED
    assert result_raised.decision is ReportDecision.BLOCKED


def test_comparative_trial_rejects_comparison_with_zero_group_associations() -> None:
    # 比较存在于宇宙中但没有任何 comparison→group 关联边 → 失败关闭
    with pytest.raises(GateEvaluationError):
        assert_applicable_universe_closed(
            _snapshot(
                empty_set_proofs=(
                    _proof_payload("endpoint", "终点"),
                    _proof_payload("timepoint", "时间点"),
                ),
                relationship_edges=(
                    _edge_payload("product", "product-a", "trial", "trial-1"),
                    _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
                    _edge_payload("trial", "trial-1", "group", "group-1"),
                    _edge_payload("trial", "trial-1", "group", "group-2"),
                ),
            )
        )

    # 恰好两个同试验组别 → 通过
    satisfied = _snapshot(
        empty_set_proofs=(
            _proof_payload("endpoint", "终点"),
            _proof_payload("timepoint", "时间点"),
        ),
        relationship_edges=(
            _edge_payload("product", "product-a", "trial", "trial-1"),
            _edge_payload("trial", "trial-1", "comparison", "comparison-1"),
            _edge_payload("trial", "trial-1", "group", "group-1"),
            _edge_payload("trial", "trial-1", "group", "group-2"),
            _edge_payload("comparison", "comparison-1", "group", "group-1"),
            _edge_payload("comparison", "comparison-1", "group", "group-2"),
        ),
    )
    assert_applicable_universe_closed(satisfied)


def test_aggregate_rejects_satisfied_result_without_distinct_fact_lineage() -> None:
    # 满足结果必须由足够的不同不可变事实版本支撑，空谱系不得通过
    with pytest.raises(PydanticValidationError, match="事实版本"):
        GateUnitResult(
            unit_id="a_product_identity",
            report_kind=ReportKind.A,
            object_id="product-a",
            applicable=True,
            outcome=GateUnitOutcome.SATISFIED,
            blocking=False,
            threshold=1,
            satisfied_count=1,
            fact_version_ids=(),
        )
    # 重复事实版本不能支撑达标数量
    with pytest.raises(PydanticValidationError, match="不得重复"):
        GateUnitResult(
            unit_id="a_product_identity",
            report_kind=ReportKind.A,
            object_id="product-a",
            applicable=True,
            outcome=GateUnitOutcome.SATISFIED,
            blocking=False,
            threshold=2,
            satisfied_count=2,
            fact_version_ids=("same-fact", "same-fact"),
        )
    # 阻断结果可携带部分证据，但达标数量不得超过事实版本数
    blocked = GateUnitResult(
        unit_id="a_safety_summary",
        report_kind=ReportKind.A,
        object_id="product-a",
        applicable=True,
        outcome=GateUnitOutcome.BLOCKED,
        blocking=True,
        threshold=2,
        satisfied_count=1,
        fact_version_ids=("fact-a-v1",),
        user_note_zh="安全性数值摘要缺失：无法判断产品的关键安全性风险。请提供官方登记结果。",
    )
    assert blocked.outcome is GateUnitOutcome.BLOCKED

    # 合法谱系通过聚合路径保持通过
    snapshot = _snapshot()
    identity = _identity_unit()
    spec = _minimal_spec(identity)
    identity_result = evaluate_unit_decision(
        identity,
        object_id="product-a",
        applicable=True,
        applicability_justified=True,
        bindings=(
            _binding(
                binding_id="binding-identity",
                unit_id="a_product_identity",
                fact_domain=FactDomain.TRIAL_DESIGN,
                numeric_value=None,
                denominator=None,
                definition="产品甲",
                source_location="官方登记",
            ),
        ),
    )
    report = _aggregate(spec, snapshot, (identity_result,))
    assert report.decision is ReportDecision.PASSED
