"""Task 3.1 项目覆盖逐字段偏序、不可变结果键与反向依赖重算测试。

精确反例矩阵覆盖：
- 只收紧偏序：增加单元/提高阈值接受，删除/降低/放宽拒绝
- 逐字段比较：每个单调字段独立比较，不以单元数量或总分代替
- 不可变结果键：结果绑定报告类型、证据快照、规则版本、合同版本与集合摘要
- 反向依赖：受影响报告由变更单元计算，调用方声明必须完全一致
- 父结果不可变：子版本只追加，未受影响报告结果保持不变
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.gates.coverage import (
    compute_affected_report_kinds,
    compute_changed_unit_ids,
    recompute_report_result,
    validate_override_declaration,
    validate_spec_override,
)
from ci_workflow.gates.evaluator import evaluate_report
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
    GateOverride,
    GateSpec,
    GateUnitOutcome,
    ObservationKind,
    ReportDecision,
    SourceRole,
    TrialDesignEvidence,
    TrialDesignKind,
    UniverseEdge,
    compute_candidate_snapshot_digest,
    compute_gate_result_key,
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
            explanation_zh=f"{trials[0]} 声明试验设计",
        ),
    )


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
        "fact_domain": FactDomain.TRIAL_DESIGN,
        "observation_kind": ObservationKind.OBSERVED_RESULT,
        "numeric_value": None,
        "unit": None,
        "denominator": None,
        "definition": None,
        "direction": None,
        "timepoint": None,
        "analysis_population": None,
        "treatment_group": None,
        "control_group": None,
        "event_definition": None,
        "time_window": None,
        "source_location": "临床试验登记",
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


def _spec_with_unit(spec: GateSpec, unit_id: str, **updates: object) -> GateSpec:
    """返回替换指定单元字段后的规格副本（经模型校验，证明是合法封闭规格）。"""
    payload = spec.model_dump(mode="json")
    units = payload["units"]
    new_units: list[dict[str, object]] = []
    found = False
    for unit in units:
        if unit["unit_id"] == unit_id:
            unit = {**unit, **updates}
            found = True
        new_units.append(unit)
    if not found:
        raise AssertionError(f"规格中不存在单元：{unit_id}")
    payload["units"] = new_units
    return GateSpec.model_validate(payload)


def _spec_with_added_unit(spec: GateSpec, new_unit_id: str) -> GateSpec:
    """返回追加一个新单元（复制既有单元模板）的规格副本。"""
    payload = spec.model_dump(mode="json")
    units = payload["units"]
    template = units[0]
    units.append({**template, "unit_id": new_unit_id})
    payload["units"] = units
    return GateSpec.model_validate(payload)


def _spec_without_unit(spec: GateSpec, unit_id: str) -> GateSpec:
    """返回删除指定单元后的规格副本。"""
    payload = spec.model_dump(mode="json")
    units = payload["units"]
    payload["units"] = [u for u in units if u["unit_id"] != unit_id]
    return GateSpec.model_validate(payload)


def _override(
    *,
    changed_unit_ids: Sequence[str] = ("a_developer_originator",),
    affected_report_kinds: Sequence[ReportKind] = (ReportKind.A,),
    base_spec_version: str = "1.0",
    parent_contract_version: str = "1",
    child_contract_version: str = "2",
) -> GateOverride:
    return GateOverride(
        schema_version="1.0",
        override_id="override-001",
        base_spec_version=base_spec_version,
        parent_contract_version=parent_contract_version,
        child_contract_version=child_contract_version,
        change_summary_zh="项目合同收紧覆盖：提高关键单元阈值",
        changed_unit_ids=tuple(changed_unit_ids),
        affected_report_kinds=tuple(affected_report_kinds),
        created_at=datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone(timedelta(hours=8))),
    )


def _satisfied_a_bindings(spec: GateSpec) -> tuple[GateEvidenceBinding, ...]:
    """构造使 A 报告全部适用关键单元满足的证据绑定（不触发结果承载）。"""
    bindings: list[GateEvidenceBinding] = []
    for unit in spec.units:
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        if unit.applicability_predicate_id not in (
            "always_applicable",
            "maturity_ge_clinical",
        ):
            continue
        bindings.append(
            _binding(
                binding_id=f"binding-{unit.unit_id}",
                unit_id=unit.unit_id,
                object_id="product-a",
                trial_id="trial-1",
            )
        )
    return tuple(bindings)


# ─── RED NODE ───────────────────────────────────────────────────────────────


def test_gate_override_rejects_relaxation_and_preserves_parent_result() -> None:
    """覆盖放松被拒绝；合法收紧覆盖生成子结果时父结果保持不可变。"""
    spec_a = _a_spec()
    snapshot = _snapshot()
    bindings = _satisfied_a_bindings(spec_a)

    # 父合同版本 1 的结果
    parent_result = evaluate_report(
        spec_a, snapshot, bindings, contract_version="1"
    )
    assert parent_result.decision is ReportDecision.PASSED
    parent_key = parent_result.result_key

    # 1) 放松覆盖（允许来源角色放宽）→ 失败关闭
    base_unit = next(
        unit for unit in spec_a.units if unit.unit_id == "a_developer_originator"
    )
    relaxed = _spec_with_unit(
        spec_a,
        "a_developer_originator",
        allowed_source_roles=[
            role.value for role in base_unit.allowed_source_roles
        ]
        + ["protocol_sap"],
    )
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=_override(),
            specs_by_report_kind={ReportKind.A: (spec_a, relaxed)},
            snapshot=snapshot,
            bindings=bindings,
        )

    # 2) 合法收紧覆盖（提高阈值）→ 子结果生成；父结果不可变
    tightened = _spec_with_unit(
        spec_a, "a_developer_originator", threshold=2
    )
    extra_binding = _binding(
        binding_id="binding-extra-developer",
        unit_id="a_developer_originator",
        object_id="product-a",
        trial_id="trial-1",
        fact_version_id="fact-2",
    )
    child_result = recompute_report_result(
        parent_result,
        override=_override(),
        specs_by_report_kind={ReportKind.A: (spec_a, tightened)},
        snapshot=snapshot,
        bindings=(*bindings, extra_binding),
    )

    assert parent_result.result_key == parent_key
    assert parent_result.contract_version == "1"
    assert child_result.contract_version == "2"
    assert child_result.result_key != parent_result.result_key
    assert child_result.decision is ReportDecision.PASSED


# ═══════════════════════════════════════════════════════════════════════════
# 只收紧偏序：接受方向
# ═══════════════════════════════════════════════════════════════════════════


def test_override_accepts_added_unit() -> None:
    """覆盖允许新增单元（单元集合只能增加）。"""
    parent = _a_spec()
    child = _spec_with_added_unit(parent, "a_project_added_unit")
    assert validate_spec_override(parent, child) == ()
    changed = compute_changed_unit_ids(parent, child)
    assert changed == ("a_project_added_unit",)
    assert compute_affected_report_kinds(
        changed, {ReportKind.A: child}
    ) == (ReportKind.A,)
    override = _override(
        changed_unit_ids=("a_project_added_unit",),
        affected_report_kinds=(ReportKind.A,),
    )
    assert validate_override_declaration(
        override, specs_by_report_kind={ReportKind.A: (parent, child)}
    ) == ()


def test_override_accepts_raised_threshold() -> None:
    """覆盖允许提高阈值（阈值只能提高）。"""
    parent = _a_spec()
    child = _spec_with_unit(parent, "a_developer_originator", threshold=2)
    assert validate_spec_override(parent, child) == ()
    assert compute_changed_unit_ids(parent, child) == (
        "a_developer_originator",
    )
    # 声明与计算一致 → 接受
    override = _override(
        changed_unit_ids=("a_developer_originator",),
        affected_report_kinds=(ReportKind.A,),
    )
    assert validate_override_declaration(
        override, specs_by_report_kind={ReportKind.A: (parent, child)}
    ) == ()


# ═══════════════════════════════════════════════════════════════════════════
# 只收紧偏序：拒绝方向
# ═══════════════════════════════════════════════════════════════════════════


def test_override_rejects_deleted_unit() -> None:
    """覆盖不得删除单元。"""
    parent = _a_spec()
    child = _spec_without_unit(parent, "a_product_identity")
    violations = validate_spec_override(parent, child)
    assert any("删除" in v for v in violations)
    # 重算路径同样失败关闭
    snapshot = _snapshot()
    parent_result = evaluate_report(
        parent, snapshot, _satisfied_a_bindings(parent), contract_version="1"
    )
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=_override(
                changed_unit_ids=("a_product_identity",),
                affected_report_kinds=(ReportKind.A,),
            ),
            specs_by_report_kind={ReportKind.A: (parent, child)},
            snapshot=snapshot,
            bindings=(),
        )


def test_override_rejects_lowered_threshold() -> None:
    """覆盖不得降低阈值。"""
    parent = _spec_with_unit(_a_spec(), "a_developer_originator", threshold=2)
    child = _spec_with_unit(parent, "a_developer_originator", threshold=1)
    violations = validate_spec_override(parent, child)
    assert any("阈值降低" in v for v in violations)


def test_override_rejects_applicability_scope_shrink() -> None:
    """适用对象集合不能缩小：谓词收窄拒绝，可证明拓宽接受。"""
    parent = _a_spec()
    # always_applicable → maturity_ge_clinical：适用集合缩小 → 拒绝
    shrink = _spec_with_unit(
        parent, "a_product_identity", applicability_predicate_id="maturity_ge_clinical"
    )
    violations = validate_spec_override(parent, shrink)
    assert any("适用性范围缩小" in v for v in violations)
    # maturity_ge_submission → maturity_ge_clinical：可证明拓宽 → 接受
    widen = _spec_with_unit(
        parent, "a_regulatory_events", applicability_predicate_id="maturity_ge_clinical"
    )
    assert validate_spec_override(parent, widen) == ()


@pytest.mark.parametrize("kind", ("source_roles", "maturity"))
def test_override_rejects_source_role_or_disclosure_maturity_relaxation(
    kind: str,
) -> None:
    """允许来源角色只能收窄；最低披露成熟度只能提高。"""
    parent = _a_spec()
    if kind == "source_roles":
        base_unit = next(
            unit
            for unit in parent.units
            if unit.unit_id == "a_developer_originator"
        )
        relaxed_roles = [
            role.value for role in base_unit.allowed_source_roles
        ] + ["protocol_sap"]
        child = _spec_with_unit(
            parent, "a_developer_originator", allowed_source_roles=relaxed_roles
        )
        marker = "允许来源角色放宽"
        # 合法方向：收窄来源角色 → 接受
        narrowed_roles = [
            role.value for role in base_unit.allowed_source_roles[:-1]
        ]
        assert validate_spec_override(
            parent,
            _spec_with_unit(
                parent,
                "a_developer_originator",
                allowed_source_roles=narrowed_roles,
            ),
        ) == ()
    else:
        child = _spec_with_unit(
            parent,
            "a_product_identity",
            minimum_disclosure_maturity="attributable_numeric_disclosure",
        )
        marker = "最低披露成熟度降低"
        # 合法方向：提高披露成熟度下限 → 接受
        assert validate_spec_override(
            parent,
            _spec_with_unit(
                parent,
                "a_product_identity",
                minimum_disclosure_maturity="final_regulatory_conclusion",
            ),
        ) == ()
    violations = validate_spec_override(parent, child)
    assert any(marker in v for v in violations)


@pytest.mark.parametrize("kind", ("missing", "conflict"))
def test_override_rejects_missing_or_conflict_policy_relaxation(kind: str) -> None:
    """非阻断缺失可改为阻断，阻断不得放松；可接受冲突处置只能收窄。"""
    if kind == "missing":
        # 关键单元（阻断缺失）→ 扩展单元（保留披露状态）：放松 → 拒绝
        parent = _a_spec()
        child = _spec_with_unit(
            parent,
            "a_product_identity",
            blocking_level="extension",
            missing_strategy="preserve_disclosure_state",
            conflict_strategy="preserve_open",
        )
        marker = "缺失策略放松"
        # 合法方向：扩展 → 关键（非阻断缺失可改为阻断）→ 接受
        tightened = _spec_with_unit(
            parent,
            "a_molecular_parameters",
            blocking_level="critical",
            missing_strategy="block",
            conflict_strategy="resolved_only",
        )
        assert validate_spec_override(parent, tightened) == ()
    else:
        # 扩展单元冲突处置 resolved_only → preserve_open：放宽 → 拒绝
        parent = _spec_with_unit(
            _a_spec(), "a_molecular_parameters", conflict_strategy="resolved_only"
        )
        child = _spec_with_unit(
            parent, "a_molecular_parameters", conflict_strategy="preserve_open"
        )
        marker = "可接受冲突处置放宽"
    violations = validate_spec_override(parent, child)
    assert any(marker in v for v in violations)


@pytest.mark.parametrize(
    "kind",
    (
        "threshold",
        "blocking_level",
        "source_roles",
        "maturity_floor",
        "accepted_fact_states",
        "conflict_strategy",
        "missing_strategy",
        "fact_domains",
        "observation_kinds",
        "required_context_fields",
        "applicability",
        "object_type",
        "scope_parent",
    ),
)
def test_override_compares_each_monotonic_field(kind: str) -> None:
    """逐字段偏序独立比较每个单调字段，不以单元数量或总分代替。"""
    parent = _a_spec()
    if kind == "threshold":
        parent = _spec_with_unit(parent, "a_developer_originator", threshold=2)
        child = _spec_with_unit(parent, "a_developer_originator", threshold=1)
        marker = "阈值降低"
    elif kind == "blocking_level":
        child = _spec_with_unit(
            parent,
            "a_product_identity",
            blocking_level="extension",
            missing_strategy="preserve_disclosure_state",
            conflict_strategy="preserve_open",
        )
        marker = "阻断级别放松"
    elif kind == "source_roles":
        base_unit = next(
            unit
            for unit in parent.units
            if unit.unit_id == "a_developer_originator"
        )
        child = _spec_with_unit(
            parent,
            "a_developer_originator",
            allowed_source_roles=[
                role.value for role in base_unit.allowed_source_roles
            ]
            + ["protocol_sap"],
        )
        marker = "允许来源角色放宽"
    elif kind == "maturity_floor":
        child = _spec_with_unit(
            parent,
            "a_product_identity",
            minimum_disclosure_maturity="attributable_numeric_disclosure",
        )
        marker = "最低披露成熟度降低"
    elif kind == "accepted_fact_states":
        parent = _b_spec()
        child = _spec_with_unit(
            parent,
            "b_core_efficacy_endpoint",
            accepted_fact_states=["reported_value", "reported_zero", "not_applicable"],
        )
        marker = "可接受事实状态放宽"
    elif kind == "conflict_strategy":
        parent = _spec_with_unit(
            parent, "a_molecular_parameters", conflict_strategy="resolved_only"
        )
        child = _spec_with_unit(
            parent, "a_molecular_parameters", conflict_strategy="preserve_open"
        )
        marker = "可接受冲突处置放宽"
    elif kind == "fact_domains":
        parent = _spec_with_unit(
            parent, "a_product_identity", allowed_fact_domains=["efficacy"]
        )
        child = _spec_with_unit(
            parent,
            "a_product_identity",
            allowed_fact_domains=["efficacy", "safety", "trial_design"],
        )
        marker = "允许事实域放宽"
    elif kind == "observation_kinds":
        parent = _spec_with_unit(
            parent,
            "a_product_identity",
            allowed_observation_kinds=["observed_result"],
        )
        child = _spec_with_unit(
            parent,
            "a_product_identity",
            allowed_observation_kinds=[
                "observed_result",
                "planned_value",
                "target_value",
                "protocol_assumption",
            ],
        )
        marker = "允许观察类型放宽"
    elif kind == "missing_strategy":
        child = _spec_with_unit(
            parent,
            "a_product_identity",
            blocking_level="extension",
            missing_strategy="preserve_disclosure_state",
            conflict_strategy="preserve_open",
        )
        marker = "缺失策略放松"
    elif kind == "required_context_fields":
        parent = _b_spec()
        base_unit = next(
            unit
            for unit in parent.units
            if unit.unit_id == "b_core_efficacy_endpoint"
        )
        child = _spec_with_unit(
            parent,
            "b_core_efficacy_endpoint",
            required_context_fields=[
                field.value for field in base_unit.required_context_fields[:-1]
            ],
        )
        marker = "必需上下文字段减少"
    elif kind == "applicability":
        child = _spec_with_unit(
            parent, "a_product_identity", applicability_predicate_id="maturity_ge_clinical"
        )
        marker = "适用性范围缩小"
    elif kind == "object_type":
        child = _spec_with_unit(parent, "a_product_identity", object_type="trial")
        marker = "适用对象类型变化"
    else:  # scope_parent
        child = _spec_with_unit(parent, "a_product_identity", scope_parent="trial")
        marker = "父子对象范围变化"
    violations = validate_spec_override(parent, child)
    assert violations
    assert any(marker in v for v in violations), (kind, violations)


# ═══════════════════════════════════════════════════════════════════════════
# 不可变结果键与反向依赖重算
# ═══════════════════════════════════════════════════════════════════════════


def _raised_threshold_setup() -> tuple[GateSpec, tuple[GateEvidenceBinding, ...]]:
    """构造 A 父规格、提高阈值的子规格和满足两个开发者绑定的证据。"""
    spec_a = _a_spec()
    child = _spec_with_unit(spec_a, "a_developer_originator", threshold=2)
    bindings = (
        *_satisfied_a_bindings(spec_a),
        _binding(
            binding_id="binding-extra-developer",
            unit_id="a_developer_originator",
            object_id="product-a",
            trial_id="trial-1",
            fact_version_id="fact-2",
        ),
    )
    return child, bindings


def test_override_binds_result_to_parent_version_and_evidence_snapshot() -> None:
    """结果键绑定报告类型、证据快照、规则版本、合同版本与集合摘要。"""
    spec_a = _a_spec()
    snapshot = _snapshot()
    child, bindings = _raised_threshold_setup()
    parent_result = evaluate_report(
        spec_a, snapshot, _satisfied_a_bindings(spec_a), contract_version="1"
    )
    override = _override()
    child_result = recompute_report_result(
        parent_result,
        override=override,
        specs_by_report_kind={ReportKind.A: (spec_a, child)},
        snapshot=snapshot,
        bindings=bindings,
    )
    assert child_result.result_key == compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot),
        "1.0",
        "2",
        snapshot.universe_summary,
        spec_fingerprint=child.spec_fingerprint,
    )
    assert parent_result.result_key == compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot),
        "1.0",
        "1",
        snapshot.universe_summary,
        spec_fingerprint=spec_a.spec_fingerprint,
    )
    # 基础规则版本与证据快照不变，只有项目合同版本变化
    assert child_result.spec_version == "1.0"
    assert child_result.evidence_snapshot_id == "snapshot-001"
    assert child_result.contract_version == "2"
    assert child_result.decision is ReportDecision.PASSED
    # 父合同不存在 → 不得生成子结果
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            None,
            override=override,
            specs_by_report_kind={ReportKind.A: (spec_a, child)},
            snapshot=snapshot,
            bindings=bindings,
        )
    # 父结果被错误替换（合同版本不匹配）→ 不得生成子结果
    replaced = evaluate_report(
        spec_a, snapshot, _satisfied_a_bindings(spec_a), contract_version="0"
    )
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            replaced,
            override=override,
            specs_by_report_kind={ReportKind.A: (spec_a, child)},
            snapshot=snapshot,
            bindings=bindings,
        )
    # 证据快照不一致 → 不得生成子结果
    other_snapshot = _snapshot(evidence_snapshot_id="snapshot-002")
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=override,
            specs_by_report_kind={ReportKind.A: (spec_a, child)},
            snapshot=other_snapshot,
            bindings=bindings,
        )
    # 适用对象集合摘要不一致 → 不得生成子结果
    other_universe = _snapshot(
        product_ids=("product-a", "product-b"),
        trial_ids=(),
        comparison_ids=(),
        group_ids=(),
    )
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=override,
            specs_by_report_kind={ReportKind.A: (spec_a, child)},
            snapshot=other_universe,
            bindings=bindings,
        )


def test_override_rejects_incorrect_affected_report_set() -> None:
    """调用方声明受影响报告集合必须与反向依赖计算完全一致。"""
    spec_a = _a_spec()
    child, bindings = _raised_threshold_setup()
    snapshot = _snapshot()
    parent_result = evaluate_report(
        spec_a, snapshot, _satisfied_a_bindings(spec_a), contract_version="1"
    )
    # 声明受影响 {A, B}，计算 {A} → 拒绝
    wrong_affected = _override(
        affected_report_kinds=(ReportKind.A, ReportKind.B)
    )
    violations = validate_override_declaration(
        wrong_affected, specs_by_report_kind={ReportKind.A: (spec_a, child)}
    )
    assert any("受影响报告集合" in v for v in violations)
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=wrong_affected,
            specs_by_report_kind={ReportKind.A: (spec_a, child)},
            snapshot=snapshot,
            bindings=bindings,
        )
    # 声明依赖单元不匹配 → 拒绝
    wrong_units = _override(changed_unit_ids=("a_product_identity",))
    violations = validate_override_declaration(
        wrong_units, specs_by_report_kind={ReportKind.A: (spec_a, child)}
    )
    assert any("依赖单元" in v for v in violations)
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=wrong_units,
            specs_by_report_kind={ReportKind.A: (spec_a, child)},
            snapshot=snapshot,
            bindings=bindings,
        )


def test_override_creates_child_version_without_mutating_parent() -> None:
    """子版本只追加；父结果不被就地覆盖。"""
    spec_a = _a_spec()
    snapshot = _snapshot()
    child, bindings = _raised_threshold_setup()
    parent_result = evaluate_report(
        spec_a, snapshot, _satisfied_a_bindings(spec_a), contract_version="1"
    )
    parent_key = parent_result.result_key
    parent_dump = parent_result.model_dump()
    override = _override()
    child_result = recompute_report_result(
        parent_result,
        override=override,
        specs_by_report_kind={ReportKind.A: (spec_a, child)},
        snapshot=snapshot,
        bindings=bindings,
    )
    # 父结果对象未被修改
    assert parent_result.result_key == parent_key
    assert parent_result.model_dump() == parent_dump
    assert parent_result.contract_version == "1"
    assert parent_result.decision is ReportDecision.PASSED
    # 子结果是新对象、新键、新合同版本
    assert child_result is not parent_result
    assert child_result.result_key != parent_key
    assert child_result.contract_version == "2"
    assert child_result.decision is ReportDecision.PASSED
    # 幂等：同一父结果再次重算产生相同子键
    again = recompute_report_result(
        parent_result,
        override=override,
        specs_by_report_kind={ReportKind.A: (spec_a, child)},
        snapshot=snapshot,
        bindings=bindings,
    )
    assert again.result_key == child_result.result_key


def test_override_recomputes_only_dependency_affected_reports() -> None:
    """只重算依赖变更单元的报告；未受影响报告保持父版本结果。"""
    spec_a = _a_spec()
    spec_b = _b_spec()
    spec_c = _c_spec()
    snapshot = _snapshot()
    child_a, a_bindings = _raised_threshold_setup()
    parent_a = evaluate_report(
        spec_a, snapshot, _satisfied_a_bindings(spec_a), contract_version="1"
    )
    parent_b = evaluate_report(spec_b, snapshot, (), contract_version="1")
    parent_c = evaluate_report(spec_c, snapshot, (), contract_version="1")

    child_a_result = recompute_report_result(
        parent_a,
        override=_override(),
        specs_by_report_kind={ReportKind.A: (spec_a, child_a)},
        snapshot=snapshot,
        bindings=a_bindings,
    )
    assert child_a_result.contract_version == "2"
    # 反向依赖：变更单元 a_developer_originator 只影响 A 报告
    affected = compute_affected_report_kinds(
        ("a_developer_originator",),
        {ReportKind.A: child_a, ReportKind.B: spec_b, ReportKind.C: spec_c},
    )
    assert affected == (ReportKind.A,)
    # B/C 未受影响：结果摘要与父版本一致
    assert parent_b.contract_version == "1"
    assert parent_b.result_key == compute_gate_result_key(
        ReportKind.B,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot),
        "1.0",
        "1",
        snapshot.universe_summary,
        spec_fingerprint=spec_b.spec_fingerprint,
    )
    assert parent_c.contract_version == "1"
    assert parent_c.result_key == compute_gate_result_key(
        ReportKind.C,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot),
        "1.0",
        "1",
        snapshot.universe_summary,
        spec_fingerprint=spec_c.spec_fingerprint,
    )


def test_unaffected_report_result_remains_unchanged() -> None:
    """未受影响报告的结果摘要保持不变（不被覆盖重算触碰）。"""
    spec_a = _a_spec()
    spec_b = _b_spec()
    snapshot = _snapshot()
    child_a, a_bindings = _raised_threshold_setup()
    parent_a = evaluate_report(
        spec_a, snapshot, _satisfied_a_bindings(spec_a), contract_version="1"
    )
    parent_b = evaluate_report(spec_b, snapshot, (), contract_version="1")
    parent_b_dump = parent_b.model_dump()
    parent_b_key = parent_b.result_key

    recompute_report_result(
        parent_a,
        override=_override(),
        specs_by_report_kind={ReportKind.A: (spec_a, child_a)},
        snapshot=snapshot,
        bindings=a_bindings,
    )
    # B 报告不在受影响集合：结果摘要逐字段不变
    assert parent_b.model_dump() == parent_b_dump
    assert parent_b.result_key == parent_b_key
    assert parent_b.contract_version == "1"
    assert parent_b.decision is ReportDecision.BLOCKED


# ─── P0-5 回归：父规格指纹校验 ─────────────────────────────────────────────


def test_recompute_rejects_parent_spec_fingerprint_mismatch_and_preserves_blocked_parent() -> None:
    """父结果必须绑定产生它的规则指纹；同版本但内容不同的父规格被拒绝。

    回归 P0-5：传入同版本/同 spec_id 但内容不同的缩减父规格时，
    必须在子结果生成前失败关闭，且原阻断父结果对象与键逐字节不变。
    """
    spec_a = _a_spec()
    snapshot = _snapshot()

    # 阻断父结果：全量 A 规格、无证据 → 全部关键单元阻断
    parent_result = evaluate_report(spec_a, snapshot, (), contract_version="1")
    assert parent_result.decision is ReportDecision.BLOCKED
    parent_dump = parent_result.model_dump()
    parent_key = parent_result.result_key
    assert parent_key == compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot),
        "1.0",
        "1",
        snapshot.universe_summary,
        spec_fingerprint=spec_a.spec_fingerprint,
    )

    # 同版本但内容不同的缩减父规格（P0-5 攻击面）
    reduced_parent = _spec_without_unit(spec_a, "a_modality")
    assert reduced_parent.version == spec_a.version
    assert reduced_parent.spec_id == spec_a.spec_id
    assert reduced_parent.spec_fingerprint != spec_a.spec_fingerprint
    reduced_child = _spec_with_unit(
        reduced_parent, "a_developer_originator", threshold=2
    )
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=_override(),
            specs_by_report_kind={ReportKind.A: (reduced_parent, reduced_child)},
            snapshot=snapshot,
            bindings=(),
        )

    # 原阻断父结果未被就地修改
    assert parent_result.model_dump() == parent_dump
    assert parent_result.result_key == parent_key
    assert parent_result.decision is ReportDecision.BLOCKED

    # 合法收紧子规格：新指纹绑定新键，父结果仍不可变
    tightened = _spec_with_unit(spec_a, "a_developer_originator", threshold=2)
    child_result = recompute_report_result(
        parent_result,
        override=_override(),
        specs_by_report_kind={ReportKind.A: (spec_a, tightened)},
        snapshot=snapshot,
        bindings=_raised_threshold_setup()[1],
    )
    assert child_result.spec_fingerprint == tightened.spec_fingerprint
    assert child_result.result_key == compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot),
        "1.0",
        "2",
        snapshot.universe_summary,
        spec_fingerprint=tightened.spec_fingerprint,
    )
    assert child_result.decision is ReportDecision.PASSED
    assert parent_result.model_dump() == parent_dump
    assert parent_result.result_key == parent_key


# ─── P1-2 回归：研究角色集合绑定 ───────────────────────────────────────────


def test_recompute_rejects_research_role_set_mismatch_and_binds_summary() -> None:
    """研究角色集合变化必须改变宇宙摘要/结果键；重算时快照不一致失败关闭。

    回归 P1-2：两个仅研究角色集合不同的快照必须产生不同摘要与结果键；
    用角色集合不匹配的快照重算必须在子结果生成前失败关闭，父结果保持逐字节不变。
    """
    spec_a = _a_spec()
    snapshot_v1 = _snapshot()
    snapshot_v2 = _snapshot(research_role_set_id="research-roles-v2")
    assert snapshot_v1.universe_summary != snapshot_v2.universe_summary

    parent_result = evaluate_report(
        spec_a,
        snapshot_v1,
        _satisfied_a_bindings(spec_a),
        contract_version="1",
    )
    assert parent_result.decision is ReportDecision.PASSED
    parent_dump = parent_result.model_dump()
    parent_key = parent_result.result_key
    assert parent_key == compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot_v1),
        "1.0",
        "1",
        snapshot_v1.universe_summary,
        spec_fingerprint=spec_a.spec_fingerprint,
    )
    # 同一证据快照、同一规则/合同版本，仅角色集合不同 → 结果键不同
    other_role_key = compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot_v2),
        "1.0",
        "1",
        snapshot_v2.universe_summary,
        spec_fingerprint=spec_a.spec_fingerprint,
    )
    assert other_role_key != parent_key

    child = _spec_with_unit(spec_a, "a_developer_originator", threshold=2)
    # 角色集合不匹配的快照 → 子结果生成前失败关闭
    with pytest.raises(GateEvaluationError):
        recompute_report_result(
            parent_result,
            override=_override(),
            specs_by_report_kind={ReportKind.A: (spec_a, child)},
            snapshot=snapshot_v2,
            bindings=_raised_threshold_setup()[1],
        )
    assert parent_result.model_dump() == parent_dump
    assert parent_result.result_key == parent_key
    # 同一角色集合的正常重算生成新合同版本子结果（指纹绑定键）
    child_result = recompute_report_result(
        parent_result,
        override=_override(),
        specs_by_report_kind={ReportKind.A: (spec_a, child)},
        snapshot=snapshot_v1,
        bindings=_raised_threshold_setup()[1],
    )
    assert child_result.contract_version == "2"
    assert child_result.result_key == compute_gate_result_key(
        ReportKind.A,
        "snapshot-001",
        compute_candidate_snapshot_digest(snapshot_v1),
        "1.0",
        "2",
        snapshot_v1.universe_summary,
        spec_fingerprint=child.spec_fingerprint,
    )


# ─── 事实域/观察类型只收紧偏序回归 ─────────────────────────────────────────


@pytest.mark.parametrize("kind", ("fact_domains", "observation_kinds"))
def test_override_rejects_fact_domain_or_observation_kind_relaxation(
    kind: str,
) -> None:
    """允许事实域/观察类型只能收窄；新增域或类型是放宽，失败关闭。"""
    parent = _a_spec()
    if kind == "fact_domains":
        # 拒绝方向：子规格新增父规格未允许的事实域 → 放宽
        domain_parent = _spec_with_unit(
            parent, "a_product_identity", allowed_fact_domains=["efficacy"]
        )
        domain_child = _spec_with_unit(
            domain_parent,
            "a_product_identity",
            allowed_fact_domains=["efficacy", "safety", "trial_design"],
        )
        violations = validate_spec_override(domain_parent, domain_child)
        assert any("允许事实域放宽" in v for v in violations)
        with pytest.raises(GateEvaluationError):
            recompute_report_result(
                evaluate_report(
                    domain_parent,
                    _snapshot(),
                    _satisfied_a_bindings(domain_parent),
                    contract_version="1",
                ),
                override=_override(),
                specs_by_report_kind={
                    ReportKind.A: (domain_parent, domain_child)
                },
                snapshot=_snapshot(),
                bindings=_satisfied_a_bindings(domain_child),
            )
        # 合法方向：收窄事实域 → 接受，声明与计算一致
        narrowed_child = _spec_with_unit(
            parent, "a_product_identity", allowed_fact_domains=["efficacy"]
        )
        assert validate_spec_override(parent, narrowed_child) == ()
        assert compute_changed_unit_ids(parent, narrowed_child) == (
            "a_product_identity",
        )
        assert validate_override_declaration(
            _override(
                changed_unit_ids=("a_product_identity",),
                affected_report_kinds=(ReportKind.A,),
            ),
            specs_by_report_kind={ReportKind.A: (parent, narrowed_child)},
        ) == ()
    else:
        # 拒绝方向：子规格新增父规格未允许的观察类型 → 放宽
        kinds_parent = _spec_with_unit(
            parent,
            "a_product_identity",
            allowed_observation_kinds=["observed_result"],
        )
        kinds_child = _spec_with_unit(
            kinds_parent,
            "a_product_identity",
            allowed_observation_kinds=[
                "observed_result",
                "planned_value",
                "target_value",
                "protocol_assumption",
            ],
        )
        violations = validate_spec_override(kinds_parent, kinds_child)
        assert any("允许观察类型放宽" in v for v in violations)
        with pytest.raises(GateEvaluationError):
            recompute_report_result(
                evaluate_report(
                    kinds_parent,
                    _snapshot(),
                    _satisfied_a_bindings(kinds_parent),
                    contract_version="1",
                ),
                override=_override(),
                specs_by_report_kind={ReportKind.A: (kinds_parent, kinds_child)},
                snapshot=_snapshot(),
                bindings=_satisfied_a_bindings(kinds_child),
            )
        # 合法方向：收窄观察类型 → 接受，声明与计算一致
        narrowed_child = _spec_with_unit(
            parent,
            "a_product_identity",
            allowed_observation_kinds=["observed_result"],
        )
        assert validate_spec_override(parent, narrowed_child) == ()
        assert compute_changed_unit_ids(parent, narrowed_child) == (
            "a_product_identity",
        )
        assert validate_override_declaration(
            _override(
                changed_unit_ids=("a_product_identity",),
                affected_report_kinds=(ReportKind.A,),
            ),
            specs_by_report_kind={ReportKind.A: (parent, narrowed_child)},
        ) == ()


# ─── P0-C 回归：重算路径下提高的核心疗效阈值生效 ────────────────────────────


def test_b_core_efficacy_respects_raised_unit_threshold_during_recompute() -> None:
    """重算路径：收紧覆盖提高核心疗效阈值必须生效，父结果保持通过且不可变。

    回归 P0-C：比较设计 B 快照（1 比较、2 同试验组、1 终点显式关联比较与两组）
    在基础阈值 1 下全部关键单元满足而通过；子规格只把 b_core_efficacy_endpoint
    阈值从 1 提高到 3 → 重算后阻断，端点单元有效阈值为 3、贡献事实版本恰好 2 个；
    父结果逐字节不变且保持通过；未受影响报告不重算、不被修改。
    """
    base_spec = _b_spec()
    snapshot = _snapshot(endpoint_ids=("endpoint-1",))

    def baseline(
        group_id: str, fact_version_id: str, unit_id: str, **ctx: object
    ) -> GateEvidenceBinding:
        payload: dict[str, object] = {
            "binding_id": f"{unit_id}-{group_id}",
            "unit_id": unit_id,
            "object_id": group_id,
            "group_id": group_id,
            "comparison_id": None,
            "trial_id": "trial-1",
            "fact_version_id": fact_version_id,
            "fact_domain": FactDomain.TRIAL_DESIGN,
            "source_location": "登记基线表",
        }
        payload.update(ctx)
        return _binding(**payload)

    def efficacy(group_id: str, fact_version_id: str) -> GateEvidenceBinding:
        return _binding(
            binding_id=f"binding-eff-{group_id}",
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

    def safety(group_id: str, fact_version_id: str) -> GateEvidenceBinding:
        return _binding(
            binding_id=f"binding-safety-{group_id}",
            unit_id="b_safety_minimum_record",
            object_id=group_id,
            group_id=group_id,
            comparison_id=None,
            trial_id="trial-1",
            fact_version_id=fact_version_id,
            fact_domain=FactDomain.SAFETY,
            observation_kind=ObservationKind.OBSERVED_RESULT,
            numeric_value=18.0,
            unit="percent",
            denominator=100,
            event_definition="TEAE",
            time_window="治疗期间",
            treatment_group="治疗组",
            control_group="安慰剂组",
            source_location="登记结果安全性表",
        )

    def effect_support() -> GateEvidenceBinding:
        return _binding(
            binding_id="binding-effect",
            unit_id="b_effect_difference_support",
            object_id="comparison-1",
            comparison_id="comparison-1",
            endpoint_id="endpoint-1",
            group_id=None,
            trial_id="trial-1",
            fact_version_id="fact-effect-1",
            fact_domain=FactDomain.EFFICACY,
            observation_kind=ObservationKind.OBSERVED_RESULT,
            numeric_value=5.0,
            unit="percent",
            definition="组间差值",
            direction="higher_is_better",
            source_location="登记结果",
        )

    bindings: list[GateEvidenceBinding] = [
        # 试验级关键单元
        _binding(
            binding_id="binding-trial-id",
            unit_id="b_trial_identity_role",
            object_id="trial-1",
            trial_id="trial-1",
            comparison_id=None,
            group_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            source_location="临床试验登记",
        ),
        _binding(
            binding_id="binding-trial-pop",
            unit_id="b_target_population_groups",
            object_id="trial-1",
            trial_id="trial-1",
            comparison_id=None,
            group_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            source_location="临床试验登记",
        ),
        _binding(
            binding_id="binding-trial-source",
            unit_id="b_source_role_maturity_location",
            object_id="trial-1",
            trial_id="trial-1",
            comparison_id=None,
            group_id=None,
            fact_domain=FactDomain.TRIAL_DESIGN,
            source_location="登记结果定位",
        ),
        # 比较级关键单元
        _binding(
            binding_id="binding-tc",
            unit_id="b_treatment_control_identity",
            object_id="comparison-1",
            comparison_id="comparison-1",
            group_id=None,
            trial_id="trial-1",
            fact_domain=FactDomain.TRIAL_DESIGN,
            treatment_group="治疗组",
            control_group="安慰剂组",
            source_location="临床试验登记",
        ),
        effect_support(),
        # 组级关键单元（每组的 4 基线 + 1 安全）
        baseline(
            "group-1",
            "fact-bs-g1",
            "b_baseline_sample_size",
            numeric_value=100,
            denominator=100,
            analysis_population="全分析集",
            unit="人数",
        ),
        baseline(
            "group-2",
            "fact-bs-g2",
            "b_baseline_sample_size",
            numeric_value=100,
            denominator=100,
            analysis_population="全分析集",
            unit="人数",
        ),
        baseline(
            "group-1",
            "fact-ba-g1",
            "b_baseline_age",
            numeric_value=58.0,
            definition="平均年龄",
            unit="岁",
            analysis_population="全分析集",
        ),
        baseline(
            "group-2",
            "fact-ba-g2",
            "b_baseline_age",
            numeric_value=57.5,
            definition="平均年龄",
            unit="岁",
            analysis_population="全分析集",
        ),
        baseline(
            "group-1",
            "fact-bx-g1",
            "b_baseline_sex",
            numeric_value=52,
            denominator=100,
            analysis_population="全分析集",
        ),
        baseline(
            "group-2",
            "fact-bx-g2",
            "b_baseline_sex",
            numeric_value=51,
            denominator=100,
            analysis_population="全分析集",
        ),
        baseline(
            "group-1",
            "fact-bv-g1",
            "b_baseline_severity_anchor",
            numeric_value=2.4,
            definition="基线严重程度均分",
            unit="分",
            analysis_population="全分析集",
            timepoint="基线",
        ),
        baseline(
            "group-2",
            "fact-bv-g2",
            "b_baseline_severity_anchor",
            numeric_value=2.3,
            definition="基线严重程度均分",
            unit="分",
            analysis_population="全分析集",
            timepoint="基线",
        ),
        safety("group-1", "fact-sf-g1"),
        safety("group-2", "fact-sf-g2"),
        # 终点级关键单元：每个适用组一个独立事实版本（两组两个版本）
        efficacy("group-1", "fact-eff-g1"),
        efficacy("group-2", "fact-eff-g2"),
    ]

    # 父结果：基础阈值 1 下全部关键单元满足 → 通过
    parent_result = evaluate_report(
        base_spec, snapshot, tuple(bindings), contract_version="1"
    )
    assert parent_result.decision is ReportDecision.PASSED
    parent_dump = parent_result.model_dump()
    parent_key = parent_result.result_key

    # 收紧子规格：只把核心疗效终点阈值从 1 提高到 3（只收紧，声明与计算一致）
    child_spec = _spec_with_unit(base_spec, "b_core_efficacy_endpoint", threshold=3)
    assert validate_spec_override(base_spec, child_spec) == ()
    assert compute_changed_unit_ids(base_spec, child_spec) == (
        "b_core_efficacy_endpoint",
    )
    override = _override(
        changed_unit_ids=("b_core_efficacy_endpoint",),
        affected_report_kinds=(ReportKind.B,),
    )
    assert validate_override_declaration(
        override, specs_by_report_kind={ReportKind.B: (base_spec, child_spec)}
    ) == ()
    # 反向依赖：变更单元只影响 B 报告
    assert compute_affected_report_kinds(
        ("b_core_efficacy_endpoint",),
        {
            ReportKind.A: _a_spec(),
            ReportKind.B: child_spec,
            ReportKind.C: _c_spec(),
        },
    ) == (ReportKind.B,)

    # 同一不可变快照与绑定重算 → 子结果阻断，父结果保持通过且逐字节不变
    child_result = recompute_report_result(
        parent_result,
        override=override,
        specs_by_report_kind={ReportKind.B: (base_spec, child_spec)},
        snapshot=snapshot,
        bindings=tuple(bindings),
    )

    # 子结果：有效阈值 3 > 2 个不同事实版本 → 阻断；键/合同版本/指纹绑定子规格
    assert child_result.decision is ReportDecision.BLOCKED
    assert child_result.contract_version == "2"
    assert child_result.spec_version == "1.0"
    assert child_result.spec_fingerprint == child_spec.spec_fingerprint
    assert child_result.result_key == compute_gate_result_key(
        ReportKind.B,
        snapshot.evidence_snapshot_id,
        compute_candidate_snapshot_digest(snapshot),
        "1.0",
        "2",
        snapshot.universe_summary,
        spec_fingerprint=child_spec.spec_fingerprint,
    )
    eff = [
        r
        for r in child_result.unit_results
        if r.unit_id == "b_core_efficacy_endpoint"
    ]
    assert len(eff) == 1
    assert eff[0].object_id == "endpoint-1"
    assert eff[0].threshold == 3
    assert eff[0].satisfied_count == 2
    assert len(eff[0].fact_version_ids) == 2
    assert eff[0].outcome is GateUnitOutcome.BLOCKED

    # 父结果：重算后逐字节不变且保持通过；未受影响报告不被重算或修改
    assert parent_result.model_dump() == parent_dump
    assert parent_result.result_key == parent_key
    assert parent_result.contract_version == "1"
    assert parent_result.decision is ReportDecision.PASSED
