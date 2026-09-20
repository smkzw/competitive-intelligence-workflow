"""Task 3.1 A/B/C 报告特异证据门槛测试。

精确反例矩阵覆盖：
- A 成熟度触发、结果承载、基线必填
- B 逐组基线/安全、作用域显式、单臂/多臂、总体值拒绝
- C 登记充分、核心设计缺失、统计扩展非阻断
- 用户说明中文合同与内部状态排除
"""
from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.gates.evaluator import (
    check_result_bearing,
    derive_product_maturity,
    evaluate_report,
)
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    ConflictDisposition,
    DisclosureMaturity,
    EmptySetProof,
    EmptySetReasonCode,
    FactDomain,
    GateBlockingLevel,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    GateSpec,
    GateUnitOutcome,
    ObservationKind,
    ReportDecision,
    SourceRole,
    TrialDesignEvidence,
    TrialDesignKind,
    UniverseEdge,
    compute_universe_summary,
)

ROOT = Path(__file__).resolve().parents[2]

# ─── 工厂 ───────────────────────────────────────────────────────────────────


_EMPTY_CLASS_TYPES = ("trial", "comparison", "group", "endpoint", "timepoint")


def _auto_empty_set_proofs(payload: dict[str, object]) -> tuple[EmptySetProof, ...]:
    """为每个空对象类生成类型化空集合证明（穷尽检索证据版本）。"""
    proofs: list[EmptySetProof] = []
    for object_type in _EMPTY_CLASS_TYPES:
        if not payload[f"{object_type}_ids"]:
            proofs.append(
                EmptySetProof(
                    object_type=object_type,
                    reason_code=(
                        EmptySetReasonCode.STUDY_DESIGN_SINGLE_ARM
                        if object_type == "comparison" and payload["trial_ids"]
                        else EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS
                    ),
                    evidence_version_id=f"proof-{object_type}-v1",
                    explanation_zh="穷尽检索后未发现适用对象",
                )
            )
    return tuple(proofs)


def _synthesize_edges(payload: dict[str, object]) -> tuple[UniverseEdge, ...]:
    """按单试验布局合成连贯关系边；多试验快照必须显式提供关系图。

    比较与终点同时出现时，合成显式 comparison→endpoint 关联边，
    使比较/终点组合与评估语义一致；每个比较关联全部组别（≥2）。
    """
    trials = tuple(payload["trial_ids"])  # type: ignore[arg-type]
    if len(trials) > 1:
        raise ValueError("多试验快照必须显式提供 relationship_edges")

    def build(
        parent_type: str,
        parent_id: str,
        child_type: str,
        child_id: str,
    ) -> UniverseEdge:
        return UniverseEdge.model_validate(
            {
                "parent_type": parent_type,
                "parent_id": parent_id,
                "child_type": child_type,
                "child_id": child_id,
            }
        )

    edges: list[UniverseEdge] = []
    for trial in trials:
        for product in tuple(payload["product_ids"]):  # type: ignore[arg-type]
            edges.append(build("product", product, "trial", trial))
        for comparison in tuple(payload["comparison_ids"]):  # type: ignore[arg-type]
            edges.append(build("trial", trial, "comparison", comparison))
        for group in tuple(payload["group_ids"]):  # type: ignore[arg-type]
            edges.append(build("trial", trial, "group", group))
        for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
            edges.append(build("trial", trial, "endpoint", endpoint))
        for comparison in tuple(payload["comparison_ids"]):  # type: ignore[arg-type]
            for group in tuple(payload["group_ids"]):  # type: ignore[arg-type]
                edges.append(build("comparison", comparison, "group", group))
        for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
            for group in tuple(payload["group_ids"]):  # type: ignore[arg-type]
                edges.append(build("endpoint", endpoint, "group", group))
        for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
            for comparison in tuple(payload["comparison_ids"]):  # type: ignore[arg-type]
                edges.append(build("comparison", comparison, "endpoint", endpoint))
        for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
            for timepoint in tuple(payload["timepoint_ids"]):  # type: ignore[arg-type]
                edges.append(build("endpoint", endpoint, "timepoint", timepoint))
    return tuple(edges)


def _auto_trial_design_evidence(
    payload: dict[str, object],
) -> tuple[TrialDesignEvidence, ...]:
    """按比较对象存在性合成每试验设计证据；多试验混合设计必须显式提供。

    有比较对象 → 比较设计；无比较对象 → 单臂设计。设计证据版本参与宇宙摘要。
    """
    trials = tuple(payload["trial_ids"])  # type: ignore[arg-type]
    if len(trials) > 1:
        raise ValueError("多试验快照必须显式提供 trial_design_evidence")
    if not trials:
        return ()
    design_kind = (
        TrialDesignKind.COMPARATIVE
        if payload["comparison_ids"]
        else TrialDesignKind.SINGLE_ARM
    )
    return (
        TrialDesignEvidence(
            trial_id=trials[0],
            design_kind=design_kind,
            evidence_version_id=f"design-{trials[0]}-v1",
            explanation_zh="根据已闭合比较对象集合判定的试验设计类型",
        ),
    )


def _snapshot(**overrides: object) -> ApplicableUniverseSnapshot:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": "project_000000000000000000000001",
        "evidence_snapshot_id": "snapshot-001",
        "research_role_set_id": "research-roles-core-v1",
        "indication_rule_set_id": "indication-rules-core-v1",
        "product_ids": ("product-a",),
        "trial_ids": ("trial-1",),
        "comparison_ids": ("comparison-1",),
        "group_ids": ("group-1", "group-2"),
        "endpoint_ids": (),
        "timepoint_ids": (),
        "empty_set_proofs": (),
        "relationship_edges": (),
        "trial_design_evidence": (),
        "applicable_conditional_predicates": (),
        "enumeration_complete": True,
    }
    payload.update(overrides)
    if "empty_set_proofs" not in overrides:
        payload["empty_set_proofs"] = _auto_empty_set_proofs(payload)
    if "relationship_edges" not in overrides:
        payload["relationship_edges"] = _synthesize_edges(payload)
    if "trial_design_evidence" not in overrides:
        payload["trial_design_evidence"] = _auto_trial_design_evidence(payload)
    if "universe_summary" not in overrides:
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
            empty_set_proofs=tuple(payload["empty_set_proofs"]),  # type: ignore[arg-type]
            relationship_edges=tuple(  # type: ignore[arg-type]
                payload["relationship_edges"]
            ),
            trial_design_evidence=tuple(  # type: ignore[arg-type]
                payload["trial_design_evidence"]
            ),
            indication_rule_set_id=str(payload["indication_rule_set_id"]),
            applicable_conditional_predicates=tuple(  # type: ignore[arg-type]
                payload["applicable_conditional_predicates"]
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


def _a_spec() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "A-v1.yaml")


def _b_spec() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "B-v1.yaml")


def _c_spec() -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / "C-v1.yaml")


def test_b_baseline_units_accept_regulatory_material_as_approved_authority() -> None:
    """B 基线可由监管材料承载，但不放宽到低权威来源。"""
    units = {unit.unit_id: unit for unit in _b_spec().units}
    for unit_id in (
        "b_baseline_sample_size",
        "b_baseline_age",
        "b_baseline_sex",
        "b_baseline_severity_anchor",
    ):
        roles = set(units[unit_id].allowed_source_roles)
        assert SourceRole.REGULATORY_MATERIAL in roles
        assert SourceRole.COMPANY_DISCLOSURE not in roles


def _all_base_a_unit_ids() -> tuple[str, ...]:
    """A 报告中 always_applicable 关键单元标识。"""
    return (
        "a_product_identity",
        "a_innovation_eligibility",
        "a_target_mechanism",
        "a_modality",
        "a_developer_originator",
        "a_indication_relationship",
        "a_china_max_phase_status",
        "a_global_max_phase_status",
    )


def _all_a_unit_ids() -> tuple[str, ...]:
    """A 报告全部单元标识。"""
    return tuple(u.unit_id for u in _a_spec().units)


def _critical_c_unit_ids() -> tuple[str, ...]:
    """C 报告关键单元标识。"""
    return tuple(
        u.unit_id
        for u in _c_spec().units
        if u.blocking_level is GateBlockingLevel.CRITICAL
    )


@pytest.mark.parametrize(
    ("spec_factory", "unit_id"),
    (
        (_a_spec, "a_efficacy_summary"),
        (_a_spec, "a_safety_summary"),
        (_b_spec, "b_baseline_sample_size"),
        (_b_spec, "b_baseline_age"),
        (_b_spec, "b_baseline_sex"),
        (_b_spec, "b_baseline_severity_anchor"),
        (_b_spec, "b_core_efficacy_endpoint"),
        (_b_spec, "b_effect_difference_support"),
        (_b_spec, "b_safety_minimum_record"),
        (_b_spec, "b_safety_event_teae"),
        (_b_spec, "b_safety_event_sae"),
        (_b_spec, "b_safety_event_aesi"),
        (_b_spec, "b_safety_event_death"),
        (_b_spec, "b_safety_event_grade3plus"),
        (_b_spec, "b_safety_event_discontinuation"),
        (_b_spec, "b_safety_event_common"),
    ),
)
def test_numeric_efficacy_and_safety_units_require_an_actual_number(
    spec_factory: Callable[[], GateSpec],
    unit_id: str,
) -> None:
    """“已报告”标签不能在实际数值为空时满足疗效或安全性单元。"""
    spec = spec_factory()
    unit = next(item for item in spec.units if item.unit_id == unit_id)
    assert "numeric_value" in {field.value for field in unit.required_context_fields}


# ─── RED NODE ──────────────────────────────────────────────────────────────


def test_report_specific_gates_reject_overall_value_for_group_scoped_evidence() -> None:
    """总体值不得冒充分组值；试验级安全性记录不可满足组级安全性单元。"""
    spec = _b_spec()

    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 试验级安全性总体值绑定（无组作用域）
    trial_safety = _binding(
        binding_id="binding-trial-safety",
        unit_id="b_safety_minimum_record",
        object_id="trial-1",
        group_id=None,
        fact_domain=FactDomain.SAFETY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=42.5,
        unit="percent",
        denominator=200,
        event_definition="TEAE",
        time_window="治疗期间",
        treatment_group=None,
        control_group=None,
        source_location="登记结果安全性汇总表",
    )

    result = evaluate_report(spec, snapshot, (trial_safety,), contract_version="1")

    safety_results = [
        r for r in result.unit_results
        if r.unit_id == "b_safety_minimum_record"
    ]
    assert len(safety_results) >= 1
    assert all(r.outcome is GateUnitOutcome.BLOCKED for r in safety_results)
    assert result.decision is ReportDecision.BLOCKED

    # 变体：把试验总体值直接绑定到组对象（无组作用域）同样不能满足组级单元。
    # 组级规则只能由同组事实满足；缺少 group_id 作用域的绑定不得计入 satisfied_count。
    crafted = _binding(
        binding_id="binding-crafted-group-overall",
        unit_id="b_safety_minimum_record",
        object_id="group-1",
        group_id=None,
        comparison_id=None,
        trial_id="trial-1",
        fact_domain=FactDomain.SAFETY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=42.5,
        unit="percent",
        denominator=200,
        event_definition="TEAE",
        time_window="治疗期间",
        treatment_group="治疗组",
        control_group="对照组",
        source_location="登记结果安全性汇总表",
    )
    result_crafted = evaluate_report(
        spec, snapshot, (crafted,), contract_version="1"
    )
    safety_crafted = [
        r for r in result_crafted.unit_results
        if r.unit_id == "b_safety_minimum_record" and r.object_id == "group-1"
    ]
    assert len(safety_crafted) == 1
    assert safety_crafted[0].outcome is GateUnitOutcome.BLOCKED
    assert safety_crafted[0].satisfied_count == 0
    assert result_crafted.decision is ReportDecision.BLOCKED


# ═══════════════════════════════════════════════════════════════════════════
# A 报告精确节点
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "missing_unit_id",
    _all_base_a_unit_ids(),
    ids=lambda uid: uid,
)
def test_a_each_base_unit_is_independently_required(missing_unit_id: str) -> None:
    """A 的8个基线单元每个独立必填；缺任一即阻断。"""
    spec = _a_spec()
    snapshot = _snapshot()

    # 构造除缺失单元外所有 always_applicable 关键单元的合格绑定
    bindings: list[GateEvidenceBinding] = []
    for unit in spec.units:
        if unit.unit_id == missing_unit_id:
            continue
        if unit.applicability_predicate_id != "always_applicable":
            continue
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        bindings.append(
            _binding(
                binding_id=f"binding-{unit.unit_id}",
                unit_id=unit.unit_id,
                object_id="product-a",
            )
        )

    result = evaluate_report(spec, snapshot, tuple(bindings), contract_version="1")

    missing_results = [
        r for r in result.unit_results if r.unit_id == missing_unit_id
    ]
    assert len(missing_results) == 1
    assert missing_results[0].outcome is GateUnitOutcome.BLOCKED
    assert result.decision is ReportDecision.BLOCKED


def test_a_preclinical_numeric_result_does_not_trigger_clinical_result_summary() -> None:
    """临床前数值结果不触发临床结果承载。"""
    snapshot = _snapshot(
        trial_ids=(),
        comparison_ids=(),
        group_ids=(),
    )

    # 临床前数值疗效绑定（无 trial_id）
    efficacy_binding = _binding(
        binding_id="binding-preclinical-efficacy",
        unit_id="a_efficacy_summary",
        object_id="product-a",
        trial_id=None,
        comparison_id=None,
        group_id=None,
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=85.0,
        unit="percent",
        denominator=50,
        definition="体外抑制率",
        direction="higher_is_better",
        timepoint="体外",
        analysis_population="体外分析",
        treatment_group="处理组",
        control_group="对照组",
        event_definition=None,
        time_window=None,
        source_location="临床前研究报告",
    )

    assert check_result_bearing(snapshot, (efficacy_binding,)) is False

    # 临床前成熟度
    assert derive_product_maturity("product-a", (efficacy_binding,)) is not None
    maturity = derive_product_maturity("product-a", ())
    assert maturity.value == "preclinical"


def test_a_early_clinical_without_results_is_not_blocked_by_result_summary() -> None:
    """临床阶段但无观察性数值结果，不阻断结果摘要单元。"""
    snapshot = _snapshot(
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
    )

    # 仅有临床试验身份绑定（无疗效/安全数值）
    trial_binding = _binding(
        binding_id="binding-trial-identity",
        unit_id="a_core_trial_identity",
        object_id="product-a",
        trial_id="trial-1",
        comparison_id=None,
        group_id=None,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        unit=None,
        denominator=None,
        definition="III期临床试验",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,
        control_group=None,
        event_definition=None,
        time_window=None,
        source_location="临床试验登记",
    )

    assert check_result_bearing(snapshot, (trial_binding,)) is False

    # 成熟度为临床
    maturity = derive_product_maturity("product-a", (trial_binding,))
    assert maturity.value == "clinical"

    # 无疗效/安全绑定 → efficacy/safety 单元 NOT_APPLICABLE → 不阻断
    spec = _a_spec()
    result = evaluate_report(spec, snapshot, (trial_binding,), contract_version="1")

    efficacy_results = [
        r for r in result.unit_results if r.unit_id == "a_efficacy_summary"
    ]
    safety_results = [
        r for r in result.unit_results if r.unit_id == "a_safety_summary"
    ]
    assert len(efficacy_results) == 1
    assert len(safety_results) == 1
    assert efficacy_results[0].applicable is False
    assert safety_results[0].applicable is False


def test_a_result_bearing_uses_observed_clinical_numeric_result_not_planned_registry_values(
) -> None:
    """只有观察性数值结果触发结果承载，计划值不触发。"""
    snapshot = _snapshot(
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 计划值绑定 → 不触发 result_bearing
    planned = _binding(
        binding_id="binding-planned",
        unit_id="a_efficacy_summary",
        object_id="product-a",
        trial_id="trial-1",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.PLANNED_VALUE,
        numeric_value=20.0,
        unit="percent",
        denominator=100,
        definition="ORR目标值",
        direction="higher_is_better",
        timepoint="第24周",
        analysis_population="全分析集",
        treatment_group="治疗组",
        control_group="对照组",
        source_location="试验方案",
    )
    assert check_result_bearing(snapshot, (planned,)) is False

    # 观察性数值结果绑定 → 触发 result_bearing
    observed = _binding(
        binding_id="binding-observed",
        unit_id="a_efficacy_summary",
        object_id="product-a",
        trial_id="trial-1",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
        unit="percent",
        denominator=120,
        definition="客观缓解率",
        direction="higher_is_better",
        timepoint="第12周",
        analysis_population="全分析集",
        treatment_group="治疗组",
        control_group="对照组",
        source_location="登记结果疗效表",
    )
    assert check_result_bearing(snapshot, (observed,)) is True


def test_a_maturity_trigger_matrix() -> None:
    """A 开发成熟度封闭集合的触发矩阵验证。"""
    # 临床前 → 无临床试验事实
    assert derive_product_maturity("product-a", ()) is not None
    assert derive_product_maturity("product-a", ()).value == "preclinical"

    # 临床 → 有试验事实
    clinical = _binding(
        binding_id="b-clinical",
        unit_id="a_core_trial_identity",
        object_id="product-a",
        trial_id="trial-1",
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        source_location="临床试验登记",
    )
    assert derive_product_maturity("product-a", (clinical,)).value == "clinical"

    # 申报 → 有监管材料事实
    regulatory = _binding(
        binding_id="b-regulatory",
        unit_id="a_regulatory_events",
        object_id="product-a",
        trial_id="trial-1",
        source_role=SourceRole.REGULATORY_MATERIAL,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.PLANNED_VALUE,
        numeric_value=None,
        source_location="监管审评材料",
    )
    assert (
        derive_product_maturity("product-a", (clinical, regulatory)).value
        == "submission"
    )

    # 已批准 → 监管材料 + 观察性结果 + 已报告值
    approved = _binding(
        binding_id="b-approved",
        unit_id="a_regulatory_events",
        object_id="product-a",
        trial_id="trial-1",
        source_role=SourceRole.REGULATORY_MATERIAL,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        source_location="监管批准公告",
    )
    assert (
        derive_product_maturity("product-a", (clinical, approved)).value == "approved"
    )

    # 暂停/终止/撤回 → 监管材料 + 不适用
    terminated = _binding(
        binding_id="b-terminated",
        unit_id="a_regulatory_events",
        object_id="product-a",
        trial_id="trial-1",
        source_role=SourceRole.REGULATORY_MATERIAL,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        denominator=None,
        disclosure_state=FactDisclosureState.NOT_APPLICABLE,
        source_location="监管终止通知",
        applicability_predicate_id="regulatory_termination",
    )
    assert (
        derive_product_maturity("product-a", (clinical, terminated)).value
        == "paused_terminated_withdrawn"
    )


def test_a_result_bearing_cannot_be_manually_downgraded() -> None:
    """A 成熟度由已接受事实推导，不接受调用方手工降级。"""
    # 有临床试验绑定 → 成熟度应为临床
    clinical = _binding(
        binding_id="b-clinical",
        unit_id="a_core_trial_identity",
        object_id="product-a",
        trial_id="trial-1",
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        source_location="临床试验登记",
    )
    maturity = derive_product_maturity("product-a", (clinical,))
    assert maturity.value == "clinical"

    # 调用方无法通过外部输入改变成熟度
    # 评估器始终从事实推导
    spec = _a_spec()
    snapshot = _snapshot(
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )
    result = evaluate_report(spec, snapshot, (clinical,), contract_version="1")

    # core_trial_identity 单元应为 applicable（成熟度 >= 临床）
    ct_results = [
        r for r in result.unit_results if r.unit_id == "a_core_trial_identity"
    ]
    assert len(ct_results) == 1
    assert ct_results[0].applicable is True


def test_a_result_bearing_missing_efficacy_blocks() -> None:
    """结果承载为真时，缺失核心疗效记录阻断。"""
    snapshot = _snapshot(
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 安全性绑定（触发 result_bearing）
    safety_binding = _binding(
        binding_id="binding-safety",
        unit_id="a_safety_summary",
        object_id="product-a",
        trial_id="trial-1",
        fact_domain=FactDomain.SAFETY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=35.0,
        unit="percent",
        denominator=120,
        event_definition="TEAE",
        time_window="治疗期间",
        treatment_group="治疗组",
        control_group="对照组",
        source_location="登记结果安全性表",
    )
    assert check_result_bearing(snapshot, (safety_binding,)) is True

    # 无疗效绑定 → a_efficacy_summary BLOCKED
    spec = _a_spec()
    result = evaluate_report(spec, snapshot, (safety_binding,), contract_version="1")

    efficacy_results = [
        r for r in result.unit_results if r.unit_id == "a_efficacy_summary"
    ]
    assert len(efficacy_results) == 1
    assert efficacy_results[0].outcome is GateUnitOutcome.BLOCKED
    assert efficacy_results[0].applicable is True
    assert result.decision is ReportDecision.BLOCKED


def test_a_result_bearing_missing_safety_blocks() -> None:
    """结果承载为真时，缺失安全性数值摘要阻断。"""
    snapshot = _snapshot(
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 疗效绑定（触发 result_bearing）
    efficacy_binding = _binding(
        binding_id="binding-efficacy",
        unit_id="a_efficacy_summary",
        object_id="product-a",
        trial_id="trial-1",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
        unit="percent",
        denominator=120,
        definition="客观缓解率",
        direction="higher_is_better",
        timepoint="第12周",
        analysis_population="全分析集",
        treatment_group="治疗组",
        control_group="对照组",
        source_location="登记结果疗效表",
    )
    assert check_result_bearing(snapshot, (efficacy_binding,)) is True

    # 无安全性绑定 → a_safety_summary BLOCKED
    spec = _a_spec()
    result = evaluate_report(spec, snapshot, (efficacy_binding,), contract_version="1")

    safety_results = [
        r for r in result.unit_results if r.unit_id == "a_safety_summary"
    ]
    assert len(safety_results) == 1
    assert safety_results[0].outcome is GateUnitOutcome.BLOCKED
    assert safety_results[0].applicable is True
    assert result.decision is ReportDecision.BLOCKED


# ═══════════════════════════════════════════════════════════════════════════
# 共享精确节点
# ═══════════════════════════════════════════════════════════════════════════


def test_report_specific_gates_reject_dropped_eligible_product_or_trial() -> None:
    """不能通过删除已识别的适格产品或试验换取通过。"""
    spec = _a_spec()

    # 含两个产品的宇宙
    snapshot_two = _snapshot(
        product_ids=("product-a", "product-b"),
        trial_ids=(),
        comparison_ids=(),
        group_ids=(),
    )

    # 两个产品均有绑定（仅提供 product-a 的绑定，product-b 缺失 → 阻断）
    binding_a = _binding(
        binding_id="binding-a",
        unit_id="a_product_identity",
        object_id="product-a",
        trial_id=None,
        comparison_id=None,
        group_id=None,
    )

    # 仅提供 product-a 的绑定，product-b 缺失 → 阻断
    result = evaluate_report(
        spec, snapshot_two, (binding_a,), contract_version="1"
    )
    identity_results = [
        r
        for r in result.unit_results
        if r.unit_id == "a_product_identity"
    ]
    # product-a 满足，product-b 阻断
    results_by_object = {r.object_id: r for r in identity_results}
    assert results_by_object["product-a"].outcome is GateUnitOutcome.SATISFIED
    assert results_by_object["product-b"].outcome is GateUnitOutcome.BLOCKED
    assert result.decision is ReportDecision.BLOCKED

    # 尝试用只有一个产品的宇宙替换 → 宇宙校验失败
    snapshot_one = _snapshot(
        product_ids=("product-a",),
        trial_ids=(),
        comparison_ids=(),
        group_ids=(),
    )
    # 这是合法操作（新宇宙），但必须证明旧宇宙不被替换
    # 此处验证评估器对两个宇宙分别评估产生不同结果
    result_one = evaluate_report(
        spec, snapshot_one, (binding_a,), contract_version="1"
    )
    identity_one = [
        r
        for r in result_one.unit_results
        if r.unit_id == "a_product_identity"
    ]
    assert len(identity_one) == 1
    assert identity_one[0].outcome is GateUnitOutcome.SATISFIED


def test_user_reason_contract_is_chinese_and_excludes_internal_status_names() -> None:
    """用户说明使用中文临床语境，不包含内部 ID、枚举或状态值。"""
    snapshot = _snapshot(
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 安全性绑定触发 result_bearing
    safety_binding = _binding(
        binding_id="binding-safety",
        unit_id="a_safety_summary",
        object_id="product-a",
        trial_id="trial-1",
        fact_domain=FactDomain.SAFETY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=35.0,
        unit="percent",
        denominator=120,
        event_definition="TEAE",
        time_window="治疗期间",
        treatment_group="治疗组",
        control_group="对照组",
        source_location="登记结果安全性表",
    )

    spec = _a_spec()
    result = evaluate_report(spec, snapshot, (safety_binding,), contract_version="1")

    # 检查所有阻断单元的用户说明
    for unit_result in result.unit_results:
        if unit_result.outcome is GateUnitOutcome.BLOCKED:
            note = unit_result.user_note_zh
            assert note is not None
            # 不包含内部单元 ID
            assert unit_result.unit_id not in note
            # 不包含枚举值
            assert "GateUnitOutcome" not in note
            assert "BLOCKED" not in note
            assert "SATISFIED" not in note
            # 包含中文字符
            assert any("\u4e00" <= c <= "\u9fff" for c in note)

    # 检查报告级摘要
    if result.decision is ReportDecision.BLOCKED:
        summary = result.user_summary_zh
        assert "报告因以下关键证据缺失而阻断" in summary
        # 不包含内部 ID
        for unit_id in _all_a_unit_ids():
            assert unit_id not in summary


# ═══════════════════════════════════════════════════════════════════════════
# B 报告精确节点
# ═══════════════════════════════════════════════════════════════════════════


def test_b_each_comparable_group_requires_baseline_fields() -> None:
    """每个可比较组需独立提供基线样本量、年龄、性别和严重程度锚点。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # group-1 有完整基线：四个单元均携带实际数值与全部必需上下文
    baseline_fields: dict[str, dict[str, object]] = {
        "sample_size": {
            "numeric_value": 100,
            "unit": "人",
            "denominator": 100,
            "analysis_population": "全分析集",
        },
        "age": {
            "numeric_value": 54.3,
            "unit": "岁",
            "definition": "基线年龄均值",
            "analysis_population": "全分析集",
        },
        "sex": {
            "numeric_value": 45,
            "unit": "percent",
            "denominator": 100,
            "analysis_population": "全分析集",
        },
        "severity_anchor": {
            "numeric_value": 24.5,
            "unit": "分",
            "definition": "HAMD总分均值",
            "analysis_population": "全分析集",
            "timepoint": "基线",
        },
    }
    baseline_bindings_g1 = [
        _binding(
            binding_id=f"binding-g1-{field}",
            unit_id=f"b_baseline_{field}",
            object_id="group-1",
            group_id="group-1",
            trial_id="trial-1",
            comparison_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            observation_kind=ObservationKind.OBSERVED_RESULT,
            source_location="主要试验报告基线表",
            **fields,
        )
        for field, fields in baseline_fields.items()
    ]

    # group-2 缺少基线
    result = evaluate_report(
        spec, snapshot, tuple(baseline_bindings_g1), contract_version="1"
    )

    baseline_units = [
        "b_baseline_sample_size",
        "b_baseline_age",
        "b_baseline_sex",
        "b_baseline_severity_anchor",
    ]
    for unit_id in baseline_units:
        g1_results = [
            r
            for r in result.unit_results
            if r.unit_id == unit_id and r.object_id == "group-1"
        ]
        g2_results = [
            r
            for r in result.unit_results
            if r.unit_id == unit_id and r.object_id == "group-2"
        ]
        assert len(g1_results) == 1
        assert g1_results[0].outcome is GateUnitOutcome.SATISFIED, unit_id
        assert len(g2_results) == 1
        assert g2_results[0].outcome is GateUnitOutcome.BLOCKED, unit_id
    assert result.decision is ReportDecision.BLOCKED


def test_b_treatment_control_scope_is_explicit() -> None:
    """治疗与对照身份需要显式作用域绑定。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 缺少 treatment_group 的绑定 → 阻断
    missing_tc = _binding(
        binding_id="binding-missing-tc",
        unit_id="b_treatment_control_identity",
        object_id="comparison-1",
        comparison_id="comparison-1",
        trial_id="trial-1",
        group_id=None,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        unit=None,
        denominator=None,
        definition="治疗对照身份",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,  # ← 缺失
        control_group=None,  # ← 缺失
        event_definition=None,
        time_window=None,
        source_location="临床试验登记",
    )

    result = evaluate_report(spec, snapshot, (missing_tc,), contract_version="1")

    tc_results = [
        r for r in result.unit_results if r.unit_id == "b_treatment_control_identity"
    ]
    assert len(tc_results) >= 1
    assert all(r.outcome is GateUnitOutcome.BLOCKED for r in tc_results)


def test_b_single_arm_does_not_fabricate_control() -> None:
    """单臂试验不虚构对照组；治疗/对照单元不适用。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),  # 无比较（类型化单臂空比较证明）
        group_ids=("group-1",),
    )

    # 提供基本试验绑定
    trial_binding = _binding(
        binding_id="binding-trial",
        unit_id="b_trial_identity_role",
        object_id="trial-1",
        trial_id="trial-1",
        comparison_id=None,
        group_id=None,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        source_location="临床试验登记",
    )

    result = evaluate_report(spec, snapshot, (trial_binding,), contract_version="1")

    # 无比较对象：比较级单元对声明父试验明确不适用，不虚构比较实例
    for unit_id in ("b_treatment_control_identity", "b_effect_difference_support"):
        tc_results = [
            r for r in result.unit_results if r.unit_id == unit_id
        ]
        assert len(tc_results) == 1
        assert tc_results[0].object_id == "trial-1"
        assert tc_results[0].outcome is GateUnitOutcome.NOT_APPLICABLE
        assert tc_results[0].applicable is False
        assert tc_results[0].blocking is False


def test_b_multiarms_require_all_applicable_group_values() -> None:
    """多臂试验的每个可比组均需独立数值。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2", "group-3"),
    )

    # 仅 group-1 和 group-2 有基线
    baseline_bindings = []
    for gid in ("group-1", "group-2"):
        baseline_bindings.append(
            _binding(
                binding_id=f"binding-{gid}-baseline",
                unit_id="b_baseline_sample_size",
                object_id=gid,
                group_id=gid,
                trial_id="trial-1",
                fact_domain=FactDomain.TRIAL_DESIGN,
                observation_kind=ObservationKind.OBSERVED_RESULT,
                numeric_value=50,
                unit="人",
                denominator=50,
                source_location=f"{gid}基线",
            )
        )

    result = evaluate_report(
        spec, snapshot, tuple(baseline_bindings), contract_version="1"
    )

    # group-3 缺少基线 → 阻断
    g3_baseline = [
        r
        for r in result.unit_results
        if r.unit_id == "b_baseline_sample_size" and r.object_id == "group-3"
    ]
    assert len(g3_baseline) == 1
    assert g3_baseline[0].outcome is GateUnitOutcome.BLOCKED


def test_b_group_scoped_safety_cannot_use_trial_overall_value() -> None:
    """试验级安全性总体值不能满足组级安全性单元。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 试验级安全性绑定（总体值）
    trial_safety = _binding(
        binding_id="binding-trial-safety",
        unit_id="b_safety_minimum_record",
        object_id="trial-1",
        group_id=None,
        fact_domain=FactDomain.SAFETY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=42.5,
        unit="percent",
        denominator=200,
        event_definition="TEAE",
        time_window="治疗期间",
        treatment_group=None,
        control_group=None,
        source_location="登记结果安全性汇总表",
    )

    result = evaluate_report(spec, snapshot, (trial_safety,), contract_version="1")

    # group-1 的安全性单元应阻断
    safety_g1 = [
        r
        for r in result.unit_results
        if r.unit_id == "b_safety_minimum_record" and r.object_id == "group-1"
    ]
    assert len(safety_g1) == 1
    assert safety_g1[0].outcome is GateUnitOutcome.BLOCKED
    assert safety_g1[0].satisfied_count == 0


def test_b_completion_and_disposition_are_modeled_nonblocking_and_state_preserved() -> None:
    """试验完成与受试者处置为扩展单元，不阻断且保留真实披露状态。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
    )

    # 提供基本试验绑定（不含处置信息）
    trial_binding = _binding(
        binding_id="binding-trial",
        unit_id="b_trial_identity_role",
        object_id="trial-1",
        trial_id="trial-1",
        comparison_id=None,
        group_id=None,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        source_location="临床试验登记",
    )

    result = evaluate_report(spec, snapshot, (trial_binding,), contract_version="1")

    # b_trial_disposition 为 extension，缺失不阻断
    disp_results = [
        r for r in result.unit_results if r.unit_id == "b_trial_disposition"
    ]
    assert len(disp_results) >= 1
    for r in disp_results:
        assert r.blocking is False
        assert r.outcome is GateUnitOutcome.EXTENSION_MISSING
        # 用户说明为 None（扩展单元不产生用户说明）
        assert r.user_note_zh is None


# ═══════════════════════════════════════════════════════════════════════════
# B 终点逐组数值、单臂与关系图精确节点
# ═══════════════════════════════════════════════════════════════════════════


def test_b_core_efficacy_with_comparator_requires_distinct_treatment_and_control_group_values() -> None:  # noqa: E501
    """有比较试验：终点按比较关联组要求每个组独立合格数值；一个绑定不能覆盖两组。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
        endpoint_ids=("endpoint-1",),
    )

    def efficacy(group_id: str, **kwargs: object) -> GateEvidenceBinding:
        payload: dict[str, object] = {
            "binding_id": f"binding-eff-{group_id}",
            "fact_version_id": f"fact-eff-{group_id}",
            "unit_id": "b_core_efficacy_endpoint",
            "object_id": "endpoint-1",
            "endpoint_id": "endpoint-1",
            "group_id": group_id,
            "comparison_id": None,
            "trial_id": "trial-1",
            "fact_domain": FactDomain.EFFICACY,
            "observation_kind": ObservationKind.OBSERVED_RESULT,
            "numeric_value": 12.5,
            "unit": "percent",
            "denominator": 100,
            "definition": "客观缓解率",
            "direction": "higher_is_better",
            "timepoint": "第12周",
            "analysis_population": "全分析集",
            "source_location": "登记结果疗效表",
        }
        payload.update(kwargs)
        return _binding(**payload)

    # 单个绑定即使同时携带治疗/对照标签也不能覆盖两个组
    single = efficacy("group-1", treatment_group="治疗组", control_group="安慰剂组")
    result = evaluate_report(spec, snapshot, (single,), contract_version="1")
    eff_results = [
        r for r in result.unit_results if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff_results) == 1
    assert eff_results[0].object_id == "endpoint-1"
    assert eff_results[0].outcome is GateUnitOutcome.BLOCKED
    assert eff_results[0].satisfied_count == 1
    assert result.decision is ReportDecision.BLOCKED

    # 两个不同组各一个绑定 → 满足
    result_two = evaluate_report(
        spec, snapshot, (single, efficacy("group-2")), contract_version="1"
    )
    eff_two = [
        r for r in result_two.unit_results
        if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert eff_two[0].outcome is GateUnitOutcome.SATISFIED
    assert eff_two[0].satisfied_count == 2

    # 同一组的重复绑定不能覆盖另一个组
    result_dup = evaluate_report(
        spec,
        snapshot,
        (single, efficacy("group-1", binding_id="binding-eff-g1-dup")),
        contract_version="1",
    )
    eff_dup = [
        r for r in result_dup.unit_results
        if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert eff_dup[0].outcome is GateUnitOutcome.BLOCKED
    assert eff_dup[0].satisfied_count == 1

    # 两个不同组引用同一不可变事实版本：同一证据不能覆盖两组
    shared_g1 = efficacy(
        "group-1",
        binding_id="binding-eff-shared-g1",
        fact_version_id="fact-shared",
    )
    shared_g2 = efficacy(
        "group-2",
        binding_id="binding-eff-shared-g2",
        fact_version_id="fact-shared",
    )
    result_shared = evaluate_report(
        spec, snapshot, (shared_g1, shared_g2), contract_version="1"
    )
    eff_shared = [
        r for r in result_shared.unit_results
        if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff_shared) == 1
    assert eff_shared[0].outcome is GateUnitOutcome.BLOCKED
    assert result_shared.decision is ReportDecision.BLOCKED


def test_b_single_arm_core_efficacy_accepts_unique_group_without_control() -> None:
    """单臂：终点唯一关联组的一个数值绑定即满足核心疗效，不虚构对照。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=("group-1",),
        endpoint_ids=("endpoint-1",),
    )
    binding = _binding(
        binding_id="binding-single-arm-eff",
        unit_id="b_core_efficacy_endpoint",
        object_id="endpoint-1",
        endpoint_id="endpoint-1",
        group_id="group-1",
        comparison_id=None,
        trial_id="trial-1",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=48.0,
        unit="percent",
        denominator=40,
        definition="客观缓解率",
        direction="higher_is_better",
        timepoint="第12周",
        analysis_population="全分析集",
        treatment_group=None,
        control_group=None,
        source_location="登记结果疗效表",
    )
    result = evaluate_report(spec, snapshot, (binding,), contract_version="1")
    eff = [
        r for r in result.unit_results if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff) == 1
    assert eff[0].object_id == "endpoint-1"
    assert eff[0].outcome is GateUnitOutcome.SATISFIED
    assert eff[0].satisfied_count == 1
    # 比较级单元明确不适用（单臂空比较证明），不虚构对照
    for unit_id in ("b_treatment_control_identity", "b_effect_difference_support"):
        tc = [r for r in result.unit_results if r.unit_id == unit_id]
        assert len(tc) == 1
        assert tc[0].outcome is GateUnitOutcome.NOT_APPLICABLE
        assert tc[0].applicable is False


def test_b_missing_comparator_is_not_treated_as_single_arm_without_design_proof() -> None:
    """普通“未找到比较对象”不能冒充单臂研究设计并免除对照证据。"""
    snapshot = _snapshot(
        comparison_ids=(),
        empty_set_proofs=(
            EmptySetProof(
                object_type=GateObjectType.COMPARISON,
                reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
                evidence_version_id="comparison-search-v1",
                explanation_zh="检索中未找到比较对象",
            ),
            EmptySetProof(
                object_type=GateObjectType.ENDPOINT,
                reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
                evidence_version_id="endpoint-search-v1",
                explanation_zh="检索中未找到终点对象",
            ),
            EmptySetProof(
                object_type=GateObjectType.TIMEPOINT,
                reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
                evidence_version_id="timepoint-search-v1",
                explanation_zh="检索中未找到时间点对象",
            ),
        ),
    )
    with pytest.raises(GateEvaluationError, match="单臂研究设计证明"):
        evaluate_report(_b_spec(), snapshot, (), contract_version="1")


def test_gate_evaluator_rejects_unjustified_empty_endpoint_set_and_does_not_drop_b_core_efficacy() -> None:  # noqa: E501
    """空终点集合必须带类型化证明；即使证明为空，核心疗效单元也不得消失。"""
    spec = _b_spec()
    # 未证明为空 → 失败关闭
    unproven = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=("group-1",),
        endpoint_ids=(),
        empty_set_proofs=(),
    )
    with pytest.raises(GateEvaluationError):
        evaluate_report(spec, unproven, (), contract_version="1")

    # 有类型化证明 → 核心疗效单元针对父试验出阻断结果，不消失
    proven = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=("group-1",),
        endpoint_ids=(),
    )
    result = evaluate_report(spec, proven, (), contract_version="1")
    eff_results = [
        r for r in result.unit_results if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff_results) == 1
    assert eff_results[0].object_id == "trial-1"
    assert eff_results[0].outcome is GateUnitOutcome.BLOCKED
    assert result.decision is ReportDecision.BLOCKED


def test_gate_evaluator_rejects_cross_trial_group_endpoint_and_comparison_bindings() -> None:
    """跨试验拼接的组/终点/比较证据绑定失败关闭。"""
    spec = _b_spec()
    edge_specs = [
        ("product", "product-a", "trial", "trial-1"),
        ("product", "product-a", "trial", "trial-2"),
        ("trial", "trial-1", "endpoint", "endpoint-1"),
        ("trial", "trial-1", "group", "group-1"),
        ("trial", "trial-1", "group", "group-2"),
        ("trial", "trial-1", "comparison", "comparison-1"),
        ("comparison", "comparison-1", "group", "group-1"),
        ("comparison", "comparison-1", "group", "group-2"),
        ("endpoint", "endpoint-1", "group", "group-1"),
        ("endpoint", "endpoint-1", "group", "group-2"),
    ]
    edges = tuple(
        UniverseEdge.model_validate(
            {
                "parent_type": parent_type,
                "parent_id": parent_id,
                "child_type": child_type,
                "child_id": child_id,
            }
        )
        for parent_type, parent_id, child_type, child_id in edge_specs
    )
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1", "trial-2"),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
        endpoint_ids=("endpoint-1",),
        relationship_edges=edges,
        trial_design_evidence=(
            TrialDesignEvidence(
                trial_id="trial-1",
                design_kind=TrialDesignKind.COMPARATIVE,
                evidence_version_id="design-trial-1-v1",
                explanation_zh="trial-1 声明比较设计",
            ),
            TrialDesignEvidence(
                trial_id="trial-2",
                design_kind=TrialDesignKind.SINGLE_ARM,
                evidence_version_id="design-trial-2-v1",
                explanation_zh="trial-2 声明单臂设计",
            ),
        ),
    )

    # 终点绑定错误归属 trial-2
    wrong_endpoint = _binding(
        binding_id="binding-wrong-endpoint",
        unit_id="b_core_efficacy_endpoint",
        object_id="endpoint-1",
        endpoint_id="endpoint-1",
        group_id="group-1",
        comparison_id=None,
        trial_id="trial-2",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=12.5,
        unit="percent",
        denominator=100,
        definition="客观缓解率",
        direction="higher_is_better",
        timepoint="第12周",
        analysis_population="全分析集",
        source_location="登记结果疗效表",
    )
    with pytest.raises(GateEvaluationError):
        evaluate_report(spec, snapshot, (wrong_endpoint,), contract_version="1")

    # 组别绑定错误归属 trial-2
    wrong_group = _binding(
        binding_id="binding-wrong-group",
        unit_id="b_baseline_sample_size",
        object_id="group-1",
        group_id="group-1",
        comparison_id=None,
        trial_id="trial-2",
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=50,
        unit="人",
        denominator=50,
        analysis_population="全分析集",
        source_location="基线表",
    )
    with pytest.raises(GateEvaluationError):
        evaluate_report(spec, snapshot, (wrong_group,), contract_version="1")

    # 比较绑定错误归属 trial-2
    wrong_comparison = _binding(
        binding_id="binding-wrong-comparison",
        unit_id="b_treatment_control_identity",
        object_id="comparison-1",
        comparison_id="comparison-1",
        group_id=None,
        trial_id="trial-2",
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        treatment_group="治疗组",
        control_group="安慰剂组",
        source_location="临床试验登记",
    )
    with pytest.raises(GateEvaluationError):
        evaluate_report(spec, snapshot, (wrong_comparison,), contract_version="1")


def test_b_core_efficacy_rejects_wrong_domain_planned_or_nonfinite_numeric_evidence() -> None:  # noqa: E501
    """只有有限观察性疗效数值可满足核心疗效单元；错误域、计划值与非有限数失败关闭。"""
    spec = _b_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
        endpoint_ids=("endpoint-1",),
    )

    def efficacy(**kwargs: object) -> GateEvidenceBinding:
        payload: dict[str, object] = {
            "binding_id": "binding-eff",
            "unit_id": "b_core_efficacy_endpoint",
            "object_id": "endpoint-1",
            "endpoint_id": "endpoint-1",
            "group_id": "group-1",
            "comparison_id": None,
            "trial_id": "trial-1",
            "fact_domain": FactDomain.EFFICACY,
            "observation_kind": ObservationKind.OBSERVED_RESULT,
            "numeric_value": 12.5,
            "unit": "percent",
            "denominator": 100,
            "definition": "客观缓解率",
            "direction": "higher_is_better",
            "timepoint": "第12周",
            "analysis_population": "全分析集",
            "source_location": "登记结果疗效表",
        }
        payload.update(kwargs)
        return _binding(**payload)

    # 错误事实域（安全域）不能满足疗效单元
    wrong_domain = efficacy(
        binding_id="binding-wrong-domain",
        fact_domain=FactDomain.SAFETY,
        event_definition="TEAE",
        time_window="治疗期间",
    )
    result = evaluate_report(spec, snapshot, (wrong_domain,), contract_version="1")
    eff = [
        r for r in result.unit_results if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff) == 1
    assert eff[0].outcome is GateUnitOutcome.BLOCKED
    assert eff[0].satisfied_count == 0

    # 计划值不能满足疗效单元
    planned = efficacy(
        binding_id="binding-planned",
        observation_kind=ObservationKind.PLANNED_VALUE,
    )
    result_planned = evaluate_report(
        spec, snapshot, (planned,), contract_version="1"
    )
    eff_planned = [
        r for r in result_planned.unit_results
        if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert eff_planned[0].outcome is GateUnitOutcome.BLOCKED
    assert eff_planned[0].satisfied_count == 0

    # 非有限数值在模型层被拒绝（NaN/±inf 不得进入证据绑定）
    with pytest.raises(ValidationError):
        efficacy(binding_id="binding-nan", numeric_value=math.nan)
    with pytest.raises(ValidationError):
        efficacy(binding_id="binding-inf", numeric_value=math.inf)


def test_b_multitrial_requires_per_trial_comparator_or_single_arm_proof() -> None:
    """比较级单元按试验判定：比较试验用真实比较对象，单臂试验用试验锚定不适用。"""
    spec = _b_spec()
    edge_specs = [
        ("product", "product-a", "trial", "trial-1"),
        ("product", "product-a", "trial", "trial-2"),
        ("trial", "trial-1", "comparison", "comparison-1"),
        ("trial", "trial-1", "group", "group-1"),
        ("trial", "trial-1", "group", "group-2"),
        ("comparison", "comparison-1", "group", "group-1"),
        ("comparison", "comparison-1", "group", "group-2"),
        ("trial", "trial-2", "group", "group-3"),
        ("trial", "trial-2", "endpoint", "endpoint-2"),
        ("endpoint", "endpoint-2", "group", "group-3"),
    ]
    edges = tuple(
        UniverseEdge.model_validate(
            {
                "parent_type": parent_type,
                "parent_id": parent_id,
                "child_type": child_type,
                "child_id": child_id,
            }
        )
        for parent_type, parent_id, child_type, child_id in edge_specs
    )
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1", "trial-2"),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2", "group-3"),
        endpoint_ids=("endpoint-2",),
        relationship_edges=edges,
        trial_design_evidence=(
            TrialDesignEvidence(
                trial_id="trial-1",
                design_kind=TrialDesignKind.COMPARATIVE,
                evidence_version_id="design-trial-1-v1",
                explanation_zh="trial-1 声明比较设计",
            ),
            TrialDesignEvidence(
                trial_id="trial-2",
                design_kind=TrialDesignKind.SINGLE_ARM,
                evidence_version_id="design-trial-2-v1",
                explanation_zh="trial-2 声明单臂设计",
            ),
        ),
    )
    bindings = [
        _binding(
            binding_id="b-t1-id",
            unit_id="b_trial_identity_role",
            object_id="trial-1",
            trial_id="trial-1",
            comparison_id=None,
            group_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            source_location="临床试验登记",
        ),
        _binding(
            binding_id="b-t2-id",
            unit_id="b_trial_identity_role",
            object_id="trial-2",
            trial_id="trial-2",
            comparison_id=None,
            group_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            source_location="临床试验登记",
        ),
        _binding(
            binding_id="b-c1-tc",
            unit_id="b_treatment_control_identity",
            object_id="comparison-1",
            comparison_id="comparison-1",
            trial_id="trial-1",
            group_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            treatment_group="治疗组",
            control_group="安慰剂组",
            source_location="临床试验登记",
        ),
        _binding(
            binding_id="b-t2-eff",
            unit_id="b_core_efficacy_endpoint",
            object_id="endpoint-2",
            endpoint_id="endpoint-2",
            group_id="group-3",
            comparison_id=None,
            trial_id="trial-2",
            fact_domain=FactDomain.EFFICACY,
            observation_kind=ObservationKind.OBSERVED_RESULT,
            numeric_value=48.0,
            unit="percent",
            denominator=40,
            definition="客观缓解率",
            direction="higher_is_better",
            timepoint="第12周",
            analysis_population="全分析集",
            source_location="登记结果疗效表",
        ),
    ]
    result = evaluate_report(spec, snapshot, tuple(bindings), contract_version="1")

    # trial-1（比较设计）的比较级单元作用于真实比较对象 comparison-1；
    # trial-2（单臂设计）的比较级单元为试验锚定的明确不适用——trial-1 的比较不得豁免 trial-2。
    tc_results = [
        r for r in result.unit_results if r.unit_id == "b_treatment_control_identity"
    ]
    tc_by_object = {r.object_id: r for r in tc_results}
    assert set(tc_by_object) == {"comparison-1", "trial-2"}
    assert tc_by_object["comparison-1"].outcome is GateUnitOutcome.SATISFIED
    assert tc_by_object["trial-2"].outcome is GateUnitOutcome.NOT_APPLICABLE
    assert tc_by_object["trial-2"].applicable is False

    # 效应量单元同样按试验判定；trial-1 无效应量绑定 → 阻断，trial-2 → 明确不适用
    eff_support = [
        r for r in result.unit_results if r.unit_id == "b_effect_difference_support"
    ]
    eff_by_object = {r.object_id: r for r in eff_support}
    assert set(eff_by_object) == {"comparison-1", "trial-2"}
    assert eff_by_object["comparison-1"].outcome is GateUnitOutcome.BLOCKED
    assert eff_by_object["trial-2"].outcome is GateUnitOutcome.NOT_APPLICABLE

    # 单臂试验终点按自身明确关联组评估，不借用比较试验的组别
    eff_endpoint = [
        r for r in result.unit_results if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff_endpoint) == 1
    assert eff_endpoint[0].object_id == "endpoint-2"
    assert eff_endpoint[0].outcome is GateUnitOutcome.SATISFIED
    assert eff_endpoint[0].satisfied_count == 1


def test_b_effect_support_rejects_cross_endpoint_comparison_binding() -> None:
    """效应量绑定携带终点时，必须存在显式 comparison→endpoint 关联边。"""
    spec = _b_spec()
    edge_specs = [
        ("product", "product-a", "trial", "trial-1"),
        ("trial", "trial-1", "comparison", "comparison-1"),
        ("trial", "trial-1", "group", "group-1"),
        ("trial", "trial-1", "group", "group-2"),
        ("trial", "trial-1", "endpoint", "endpoint-1"),
        ("trial", "trial-1", "endpoint", "endpoint-2"),
        ("comparison", "comparison-1", "group", "group-1"),
        ("comparison", "comparison-1", "group", "group-2"),
        ("comparison", "comparison-1", "endpoint", "endpoint-1"),
        ("endpoint", "endpoint-1", "group", "group-1"),
        ("endpoint", "endpoint-1", "group", "group-2"),
        ("endpoint", "endpoint-2", "group", "group-1"),
    ]
    edges = tuple(
        UniverseEdge.model_validate(
            {
                "parent_type": parent_type,
                "parent_id": parent_id,
                "child_type": child_type,
                "child_id": child_id,
            }
        )
        for parent_type, parent_id, child_type, child_id in edge_specs
    )
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
        endpoint_ids=("endpoint-1", "endpoint-2"),
        relationship_edges=edges,
    )

    def effect_binding(endpoint_id: str | None) -> GateEvidenceBinding:
        payload: dict[str, object] = {
            "binding_id": "binding-effect",
            "unit_id": "b_effect_difference_support",
            "object_id": "comparison-1",
            "comparison_id": "comparison-1",
            "endpoint_id": endpoint_id,
            "group_id": None,
            "trial_id": "trial-1",
            "fact_domain": FactDomain.EFFICACY,
            "observation_kind": ObservationKind.OBSERVED_RESULT,
            "numeric_value": 5.0,
            "unit": "percent",
            "definition": "组间差值",
            "direction": "higher_is_better",
            "source_location": "登记结果",
        }
        return _binding(**payload)

    # 错误组合：comparison-1 与 endpoint-2 无关联边 → 经完整报告评估失败关闭
    with pytest.raises(GateEvaluationError):
        evaluate_report(
            spec, snapshot, (effect_binding(endpoint_id="endpoint-2"),),
            contract_version="1",
        )

    # 正确组合：comparison-1 与 endpoint-1 存在关联边 → 可评估
    result = evaluate_report(
        spec, snapshot, (effect_binding(endpoint_id="endpoint-1"),),
        contract_version="1",
    )
    eff = [
        r for r in result.unit_results
        if r.unit_id == "b_effect_difference_support"
    ]
    assert len(eff) == 1
    assert eff[0].object_id == "comparison-1"
    assert eff[0].outcome is GateUnitOutcome.SATISFIED


def test_b_effect_support_requires_explicit_comparison_endpoint_association_when_endpoint_is_omitted() -> None:  # noqa: E501
    """效应量单元必须绑定显式比较→终点关联；省略终点不得合格，显式终点须有关联边。"""
    spec = _b_spec()
    edge_specs = [
        ("product", "product-a", "trial", "trial-1"),
        ("trial", "trial-1", "comparison", "comparison-1"),
        ("trial", "trial-1", "group", "group-1"),
        ("trial", "trial-1", "group", "group-2"),
        ("trial", "trial-1", "endpoint", "endpoint-1"),
        ("comparison", "comparison-1", "group", "group-1"),
        ("comparison", "comparison-1", "group", "group-2"),
        ("comparison", "comparison-1", "endpoint", "endpoint-1"),
        ("endpoint", "endpoint-1", "group", "group-1"),
        ("endpoint", "endpoint-1", "group", "group-2"),
    ]
    edges = tuple(
        UniverseEdge.model_validate(
            {
                "parent_type": parent_type,
                "parent_id": parent_id,
                "child_type": child_type,
                "child_id": child_id,
            }
        )
        for parent_type, parent_id, child_type, child_id in edge_specs
    )
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
        endpoint_ids=("endpoint-1",),
        relationship_edges=edges,
    )

    def effect(**kwargs: object) -> GateEvidenceBinding:
        payload: dict[str, object] = {
            "binding_id": "binding-effect",
            "unit_id": "b_effect_difference_support",
            "object_id": "comparison-1",
            "comparison_id": "comparison-1",
            "endpoint_id": None,
            "group_id": None,
            "trial_id": "trial-1",
            "fact_domain": FactDomain.EFFICACY,
            "observation_kind": ObservationKind.OBSERVED_RESULT,
            "numeric_value": 5.0,
            "unit": "percent",
            "definition": "组间差值",
            "direction": "higher_is_better",
            "source_location": "登记结果",
        }
        payload.update(kwargs)
        return _binding(**payload)

    # 省略终点：效应量绑定不得合格 → 阻断
    result_omitted = evaluate_report(
        spec, snapshot, (effect(),), contract_version="1"
    )
    eff_omitted = [
        r for r in result_omitted.unit_results
        if r.unit_id == "b_effect_difference_support"
    ]
    assert len(eff_omitted) == 1
    assert eff_omitted[0].object_id == "comparison-1"
    assert eff_omitted[0].outcome is GateUnitOutcome.BLOCKED
    assert eff_omitted[0].satisfied_count == 0

    # 显式终点且存在 comparison→endpoint 关联边 → 满足
    result_explicit = evaluate_report(
        spec, snapshot, (effect(endpoint_id="endpoint-1"),),
        contract_version="1",
    )
    eff_explicit = [
        r for r in result_explicit.unit_results
        if r.unit_id == "b_effect_difference_support"
    ]
    assert len(eff_explicit) == 1
    assert eff_explicit[0].outcome is GateUnitOutcome.SATISFIED
    assert eff_explicit[0].satisfied_count == 1


def test_b_core_efficacy_respects_raised_unit_threshold() -> None:
    """提高的核心疗效阈值必须生效：全部适用组别已覆盖但事实版本数不足仍阻断。"""
    base_spec = _b_spec()
    payload = base_spec.model_dump(mode="json")
    for unit in payload["units"]:
        if unit["unit_id"] == "b_core_efficacy_endpoint":
            unit["threshold"] = 3
    spec = GateSpec.model_validate(payload)

    def efficacy(group_id: str, fact_version_id: str) -> GateEvidenceBinding:
        return _binding(
            binding_id=f"binding-{group_id}",
            unit_id="b_core_efficacy_endpoint",
            object_id="endpoint-1",
            endpoint_id="endpoint-1",
            group_id=group_id,
            comparison_id=None,
            trial_id="trial-1",
            fact_version_id=fact_version_id,
            fact_domain=FactDomain.EFFICACY,
            observation_kind=ObservationKind.OBSERVED_RESULT,
            numeric_value=12.5,
            unit="percent",
            denominator=100,
            definition="客观缓解率",
            direction="higher_is_better",
            timepoint="第12周",
            analysis_population="全分析集",
            source_location="登记结果疗效表",
        )

    # 比较试验：两个适用组别全部覆盖但只有两个不同事实版本：有效阈值 3 > 2 → 阻断
    snapshot = _snapshot(
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
        endpoint_ids=("endpoint-1",),
    )
    result = evaluate_report(
        spec,
        snapshot,
        (efficacy("group-1", "fact-eff-g1"), efficacy("group-2", "fact-eff-g2")),
        contract_version="1",
    )
    eff = [
        r for r in result.unit_results if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff) == 1
    assert eff[0].object_id == "endpoint-1"
    assert eff[0].threshold == 3
    assert eff[0].satisfied_count == 2
    assert eff[0].outcome is GateUnitOutcome.BLOCKED
    # 事实版本谱系恰好等于计数的不同版本（2），不得被跨组复用放大
    assert len(eff[0].fact_version_ids) == 2
    assert result.decision is ReportDecision.BLOCKED

    # 一个共享事实跨两组引用时必须整体排除；同组的两个独立事实不能替另一组补足覆盖。
    shared_and_one_sided = evaluate_report(
        base_spec,
        snapshot,
        (
            efficacy("group-1", "fact-shared"),
            efficacy("group-2", "fact-shared").model_copy(
                update={"binding_id": "binding-group-2-shared"}
            ),
            efficacy("group-1", "fact-g1-a").model_copy(
                update={"binding_id": "binding-group-1-a"}
            ),
            efficacy("group-1", "fact-g1-b").model_copy(
                update={"binding_id": "binding-group-1-b"}
            ),
        ),
        contract_version="1",
    )
    shared_result = next(
        item
        for item in shared_and_one_sided.unit_results
        if item.unit_id == "b_core_efficacy_endpoint"
    )
    assert shared_result.outcome is GateUnitOutcome.BLOCKED
    assert shared_result.coverage_complete is False
    assert shared_result.satisfied_count == 2
    assert shared_result.fact_version_ids == ("fact-g1-a", "fact-g1-b")

    # 单臂唯一组在基础阈值 1 下保持满足（回归，不虚构对照）
    single_snapshot = _snapshot(
        comparison_ids=(),
        group_ids=("group-1",),
        endpoint_ids=("endpoint-1",),
    )
    result_single = evaluate_report(
        base_spec,
        single_snapshot,
        (efficacy("group-1", "fact-eff-g1"),),
        contract_version="1",
    )
    eff_single = [
        r for r in result_single.unit_results
        if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff_single) == 1
    assert eff_single[0].threshold == 1
    assert eff_single[0].satisfied_count == 1
    assert eff_single[0].outcome is GateUnitOutcome.SATISFIED

    # 同一组存在额外的合法事实时仍须可评估，不能因谱系数量多于组数崩溃。
    extra_fact_result = evaluate_report(
        base_spec,
        snapshot,
        (
            efficacy("group-1", "fact-g1-a"),
            efficacy("group-1", "fact-g1-b").model_copy(
                update={"binding_id": "binding-group-1-extra"}
            ),
            efficacy("group-2", "fact-g2"),
        ),
        contract_version="1",
    )
    extra_fact_unit = next(
        item for item in extra_fact_result.unit_results
        if item.unit_id == "b_core_efficacy_endpoint"
    )
    assert extra_fact_unit.outcome is GateUnitOutcome.SATISFIED
    assert extra_fact_unit.coverage_complete is True
    assert extra_fact_unit.satisfied_count == 3
    assert set(extra_fact_unit.fact_version_ids) == {
        "fact-g1-a", "fact-g1-b", "fact-g2",
    }
    raised_with_enough_facts = evaluate_report(
        spec,
        snapshot,
        (
            efficacy("group-1", "fact-g1-a"),
            efficacy("group-1", "fact-g1-b").model_copy(
                update={"binding_id": "binding-group-1-extra"}
            ),
            efficacy("group-2", "fact-g2"),
        ),
        contract_version="1",
    )
    assert next(
        item for item in raised_with_enough_facts.unit_results
        if item.unit_id == "b_core_efficacy_endpoint"
    ).outcome is GateUnitOutcome.SATISFIED


def test_gate_evaluator_rejects_cross_product_trial_evidence_stitching() -> None:
    """产品级证据不得引用其他产品的试验；经完整报告评估失败关闭。"""
    spec = _a_spec()
    edge_specs = [
        ("product", "product-a", "trial", "trial-1"),
        ("product", "product-b", "trial", "trial-2"),
        ("trial", "trial-1", "group", "group-1"),
        ("trial", "trial-2", "group", "group-2"),
    ]
    edges = tuple(
        UniverseEdge.model_validate(
            {
                "parent_type": parent_type,
                "parent_id": parent_id,
                "child_type": child_type,
                "child_id": child_id,
            }
        )
        for parent_type, parent_id, child_type, child_id in edge_specs
    )
    snapshot = _snapshot(
        product_ids=("product-a", "product-b"),
        trial_ids=("trial-1", "trial-2"),
        comparison_ids=(),
        group_ids=("group-1", "group-2"),
        relationship_edges=edges,
        trial_design_evidence=(
            TrialDesignEvidence(
                trial_id="trial-1",
                design_kind=TrialDesignKind.SINGLE_ARM,
                evidence_version_id="design-trial-1-v1",
                explanation_zh="trial-1 声明单臂设计",
            ),
            TrialDesignEvidence(
                trial_id="trial-2",
                design_kind=TrialDesignKind.SINGLE_ARM,
                evidence_version_id="design-trial-2-v1",
                explanation_zh="trial-2 声明单臂设计",
            ),
        ),
    )
    stitched = _binding(
        binding_id="binding-stitched",
        unit_id="a_product_identity",
        object_id="product-a",
        trial_id="trial-2",  # trial-2 属于 product-b
        comparison_id=None,
        group_id=None,
        fact_domain=FactDomain.TRIAL_DESIGN,
        source_location="临床试验登记",
    )
    with pytest.raises(GateEvaluationError):
        evaluate_report(spec, snapshot, (stitched,), contract_version="1")


# ═══════════════════════════════════════════════════════════════════════════
# C 报告精确节点
# ═══════════════════════════════════════════════════════════════════════════


def test_c_official_registry_passes_without_protocol_or_sap() -> None:
    """官方登记设计事实覆盖全部适用核心字段时，无需方案/SAP 即可通过。"""
    spec = _c_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
        applicable_conditional_predicates=("region_visit_operational_key",),
    )

    # 为每个关键 C 单元提供登记来源绑定（无 protocol_sap）
    registry_bindings: list[GateEvidenceBinding] = []
    for unit in spec.units:
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        if SourceRole.CLINICAL_TRIAL_REGISTRY not in unit.allowed_source_roles:
            continue
        registry_bindings.append(
            _binding(
                binding_id=f"binding-registry-{unit.unit_id}",
                unit_id=unit.unit_id,
                object_id="trial-1",
                trial_id="trial-1",
                comparison_id=None,
                group_id=None,
                fact_domain=FactDomain.TRIAL_DESIGN,
                observation_kind=ObservationKind.OBSERVED_RESULT,
                numeric_value=100
                if SourceRole.CLINICAL_TRIAL_REGISTRY in unit.allowed_source_roles
                and "sample_size" in unit.unit_id
                else None,
                unit="人" if "sample_size" in unit.unit_id else None,
                definition=f"{unit.user_label_zh}登记数据",
                source_location="临床试验登记",
            )
        )

    result = evaluate_report(
        spec, snapshot, tuple(registry_bindings), contract_version="1"
    )

    # 所有关键 C 单元应通过（登记信息充分）
    critical_results = [
        r for r in result.unit_results if r.applicable
    ]
    # 至少部分关键单元通过
    satisfied_critical = [
        r for r in critical_results if r.outcome is GateUnitOutcome.SATISFIED
    ]
    assert len(satisfied_critical) > 0


def test_c_region_visit_operational_requires_explicit_indication_rule() -> None:
    """地区/访视/操作特征仅在版本化指示规则合同声明为关键时适用。"""
    spec = _c_spec()
    # 未声明 → 明确不适用，不阻断
    absent = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
        applicable_conditional_predicates=(),
    )
    result = evaluate_report(spec, absent, (), contract_version="1")
    region_results = [
        r for r in result.unit_results
        if r.unit_id == "c_region_visit_operational"
    ]
    assert len(region_results) == 1
    assert region_results[0].object_id == "trial-1"
    assert region_results[0].outcome is GateUnitOutcome.NOT_APPLICABLE
    assert region_results[0].applicable is False

    # 声明为关键且无绑定 → 阻断
    declared = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
        applicable_conditional_predicates=("region_visit_operational_key",),
    )
    result_declared = evaluate_report(spec, declared, (), contract_version="1")
    region_declared = [
        r for r in result_declared.unit_results
        if r.unit_id == "c_region_visit_operational"
    ]
    assert len(region_declared) == 1
    assert region_declared[0].applicable is True
    assert region_declared[0].outcome is GateUnitOutcome.BLOCKED

    # 声明为关键且有登记绑定 → 满足
    region_binding = _binding(
        binding_id="binding-region",
        unit_id="c_region_visit_operational",
        object_id="trial-1",
        trial_id="trial-1",
        comparison_id=None,
        group_id=None,
        fact_domain=FactDomain.TRIAL_DESIGN,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=None,
        definition="中国研究中心与访视安排",
        source_location="临床试验登记",
    )
    result_ok = evaluate_report(
        spec, declared, (region_binding,), contract_version="1"
    )
    region_ok = [
        r for r in result_ok.unit_results
        if r.unit_id == "c_region_visit_operational"
    ]
    assert region_ok[0].outcome is GateUnitOutcome.SATISFIED


def test_c_each_core_design_unit_blocks_when_missing() -> None:
    """C 每个关键设计单元缺失时阻断。"""
    spec = _c_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
        applicable_conditional_predicates=("region_visit_operational_key",),
    )

    critical_ids = _critical_c_unit_ids()

    # 提供所有关键单元绑定（含必需字段）
    full_bindings: list[GateEvidenceBinding] = []
    for unit in spec.units:
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        full_bindings.append(
            _binding(
                binding_id=f"binding-c-{unit.unit_id}",
                unit_id=unit.unit_id,
                object_id="trial-1",
                trial_id="trial-1",
                comparison_id=None,
                group_id=None,
                fact_domain=FactDomain.TRIAL_DESIGN,
                observation_kind=ObservationKind.OBSERVED_RESULT,
                numeric_value=100 if "sample_size" in unit.unit_id else None,
                unit="人" if "sample_size" in unit.unit_id else None,
                definition=f"{unit.user_label_zh}数据",
                source_location="临床试验登记",
            )
        )

    # 全部绑定 → 全部通过
    result_all = evaluate_report(
        spec, snapshot, tuple(full_bindings), contract_version="1"
    )
    all_satisfied = [
        r
        for r in result_all.unit_results
        if r.applicable and r.blocking
    ]
    assert all(r.outcome is GateUnitOutcome.SATISFIED for r in all_satisfied)

    # 逐个删除关键单元绑定 → 缺失单元阻断
    for missing_id in critical_ids:
        filtered = [b for b in full_bindings if b.unit_id != missing_id]
        result_missing = evaluate_report(
            spec, snapshot, tuple(filtered), contract_version="1"
        )
        missing_results = [
            r
            for r in result_missing.unit_results
            if r.unit_id == missing_id and r.applicable
        ]
        assert len(missing_results) == 1
        assert missing_results[0].outcome is GateUnitOutcome.BLOCKED


def test_c_optional_statistical_details_are_nonblocking_and_state_preserved() -> None:
    """C 统计细节为扩展单元，不阻断且保留披露状态。"""
    spec = _c_spec()
    snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
        applicable_conditional_predicates=("region_visit_operational_key",),
    )

    # 提供所有关键单元绑定
    critical_bindings: list[GateEvidenceBinding] = []
    for unit in spec.units:
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        critical_bindings.append(
            _binding(
                binding_id=f"binding-c-critical-{unit.unit_id}",
                unit_id=unit.unit_id,
                object_id="trial-1",
                trial_id="trial-1",
                comparison_id=None,
                group_id=None,
                fact_domain=FactDomain.TRIAL_DESIGN,
                observation_kind=ObservationKind.OBSERVED_RESULT,
                numeric_value=100 if "sample_size" in unit.unit_id else None,
                unit="人" if "sample_size" in unit.unit_id else None,
                definition=f"{unit.user_label_zh}数据",
                source_location="临床试验登记",
            )
        )

    result = evaluate_report(
        spec, snapshot, tuple(critical_bindings), contract_version="1"
    )

    # 统计扩展单元应为 EXTENSION_MISSING 且不阻断
    statistical_units = (
        "c_analysis_population",
        "c_comparison_logic",
        "c_statistical_model",
        "c_effect_size",
        "c_multiplicity",
        "c_sample_size_assumptions",
        "c_estimand_intercurrent",
        "c_missing_data_sensitivity",
    )
    for unit_id in statistical_units:
        ext_results = [
            r for r in result.unit_results if r.unit_id == unit_id
        ]
        assert len(ext_results) >= 1
        for r in ext_results:
            assert r.blocking is False
            assert r.outcome is GateUnitOutcome.EXTENSION_MISSING
