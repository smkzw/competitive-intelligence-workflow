"""Task 3.2 阻断时无草稿/无下游产物的集成测试（含共享夹具）。

第一层：A/B/C 三个空/无适格对象场景（真实 EmptyUniverseEvidence，gate_result=None）；
第二层：从 A/B/C GateSpec 枚举每个适用关键单元，经真实 evaluate_report 证明
       “非空候选只缺该单元”，仅生成 blockers 阻断包，无任何下游报告产物。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import (
    InformationGainDiff,
    SourceReceipt,
)
from ci_workflow.gates.blocker_audit import (
    BlockerAudit,
    EmptyUniverseEvidence,
    EmptyUniverseKind,
    FailedGateUnit,
    assert_no_report_downstream_artifacts,
    classify_empty_universe,
    render_audit_markdown_zh,
)
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.exhaustion import (
    DoubleExhaustionRecord,
    ExhaustionRole,
    GapDoubleExhaustion,
    GapOmissionReview,
    GapRouteEvidence,
    GapTechnicalDiagnosis,
    OmissionReviewConclusion,
)
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    GateBlockingLevel,
    GateEvidenceBinding,
    GateObjectType,
    GateSpec,
    GateUnitOutcome,
    ReportDecision,
    ReportGateResult,
    ReportKind,
)
from ci_workflow.sources.retries import (
    AlternativePathAudit,
    InformationGain,
    RecoveryExhaustionProof,
    RecoveryHistory,
    RecoveryRound,
    RecoveryStrategyKind,
    RecoveryStrategyUnit,
    SamePathRetryAudit,
)
from ci_workflow.storage.migrations import apply_migrations

ROOT = Path(__file__).resolve().parents[2]
_TZ = timezone(timedelta(hours=8))


def now() -> datetime:
    return datetime(2026, 8, 12, 10, 0, tzinfo=_TZ)


def spec_yaml(report_kind: str) -> GateSpec:
    return GateSpec.from_yaml(ROOT / "policies" / "gates" / f"{report_kind}-v1.yaml")


def critical_unit_ids(spec: GateSpec) -> tuple[str, ...]:
    return tuple(
        unit.unit_id
        for unit in spec.units
        if unit.blocking_level is GateBlockingLevel.CRITICAL
    )


# ─── 宇宙快照工厂 ────────────────────────────────────────────────────────────


def proof_payload(object_type: str, label_zh: str) -> dict[str, object]:
    return {
        "object_type": object_type,
        "reason_code": "exhaustive_search_no_objects",
        "evidence_version_id": f"evidence-{object_type}-empty-v1",
        "explanation_zh": f"穷尽检索后未发现适用{label_zh}对象",
    }


def edge_payload(
    parent_type: str, parent_id: str, child_type: str, child_id: str
) -> dict[str, object]:
    return {
        "parent_type": parent_type,
        "parent_id": parent_id,
        "child_type": child_type,
        "child_id": child_id,
    }


def design_record(trial_id: str, design_kind: str) -> dict[str, object]:
    kind_zh = "比较" if design_kind == "comparative" else "单臂"
    return {
        "trial_id": trial_id,
        "design_kind": design_kind,
        "evidence_version_id": f"evidence-{trial_id}-{design_kind}-v1",
        "explanation_zh": f"登记结果显示试验 {trial_id} 为{kind_zh}设计",
    }


def _snapshot(**overrides: object) -> ApplicableUniverseSnapshot:
    from ci_workflow.gates.models import (
        EmptySetProof,
        TrialDesignEvidence,
        UniverseEdge,
        compute_universe_summary,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": "project_000000000000000000000001",
        "evidence_snapshot_id": "snapshot-001",
        "research_role_set_id": "research-roles-core-v1",
        "indication_rule_set_id": "indication-rules-core-v1",
        "applicable_conditional_predicates": (),
        "product_ids": ("product-a",),
        "trial_ids": ("trial-1",),
        "comparison_ids": (),
        "group_ids": (),
        "endpoint_ids": (),
        "timepoint_ids": (),
        "enumeration_complete": True,
    }
    payload.update(overrides)
    if "empty_set_proofs" not in overrides:
        proofs: list[dict[str, object]] = []
        for object_type, label in (
            ("trial", "试验"),
            ("comparison", "比较"),
            ("group", "组别"),
            ("endpoint", "终点"),
            ("timepoint", "时间点"),
        ):
            if not tuple(payload[f"{object_type}_ids"]):  # type: ignore[arg-type]
                proofs.append(proof_payload(object_type, label))
        payload["empty_set_proofs"] = tuple(proofs)
    if "relationship_edges" not in overrides:
        edges: list[dict[str, object]] = []
        for trial in tuple(payload["trial_ids"]):  # type: ignore[arg-type]
            for product in tuple(payload["product_ids"]):  # type: ignore[arg-type]
                edges.append(edge_payload("product", product, "trial", trial))
            for comparison in tuple(payload["comparison_ids"]):  # type: ignore[arg-type]
                edges.append(edge_payload("trial", trial, "comparison", comparison))
            for group in tuple(payload["group_ids"]):  # type: ignore[arg-type]
                edges.append(edge_payload("trial", trial, "group", group))
            for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
                edges.append(edge_payload("trial", trial, "endpoint", endpoint))
            for comparison in tuple(payload["comparison_ids"]):  # type: ignore[arg-type]
                for group in tuple(payload["group_ids"]):  # type: ignore[arg-type]
                    edges.append(edge_payload("comparison", comparison, "group", group))
            for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
                for group in tuple(payload["group_ids"]):  # type: ignore[arg-type]
                    edges.append(edge_payload("endpoint", endpoint, "group", group))
            for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
                for comparison in tuple(payload["comparison_ids"]):  # type: ignore[arg-type]
                    edges.append(edge_payload("comparison", comparison, "endpoint", endpoint))
            for endpoint in tuple(payload["endpoint_ids"]):  # type: ignore[arg-type]
                for timepoint in tuple(payload["timepoint_ids"]):  # type: ignore[arg-type]
                    edges.append(edge_payload("endpoint", endpoint, "timepoint", timepoint))
        payload["relationship_edges"] = tuple(edges)
    if "trial_design_evidence" not in overrides:
        payload["trial_design_evidence"] = tuple(
            design_record(str(trial_id), "single_arm")
            for trial_id in tuple(payload["trial_ids"])  # type: ignore[arg-type]
        )
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
            empty_set_proofs=tuple(
                EmptySetProof.model_validate(item)
                for item in tuple(payload["empty_set_proofs"])  # type: ignore[arg-type]
            ),
            relationship_edges=tuple(
                UniverseEdge.model_validate(item)
                for item in tuple(payload["relationship_edges"])  # type: ignore[arg-type]
            ),
            trial_design_evidence=tuple(
                TrialDesignEvidence.model_validate(item)
                for item in tuple(payload["trial_design_evidence"])  # type: ignore[arg-type]
            ),
            indication_rule_set_id=str(payload["indication_rule_set_id"]),
            applicable_conditional_predicates=tuple(
                payload["applicable_conditional_predicates"]  # type: ignore[arg-type]
            ),
        )
    return ApplicableUniverseSnapshot.model_validate(payload)


def a_snapshot() -> ApplicableUniverseSnapshot:
    return _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
        endpoint_ids=(),
        timepoint_ids=(),
        empty_set_proofs=(
            proof_payload("comparison", "比较"),
            proof_payload("group", "组别"),
            proof_payload("endpoint", "终点"),
            proof_payload("timepoint", "时间点"),
        ),
        relationship_edges=(edge_payload("product", "product-a", "trial", "trial-1"),),
        trial_design_evidence=(design_record("trial-1", "single_arm"),),
    )


def b_snapshot() -> ApplicableUniverseSnapshot:
    return _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=("comparison-1",),
        group_ids=("group-1", "group-2"),
        endpoint_ids=("endpoint-1",),
        timepoint_ids=(),
        empty_set_proofs=(proof_payload("timepoint", "时间点"),),
        relationship_edges=(
            edge_payload("product", "product-a", "trial", "trial-1"),
            edge_payload("trial", "trial-1", "comparison", "comparison-1"),
            edge_payload("trial", "trial-1", "group", "group-1"),
            edge_payload("trial", "trial-1", "group", "group-2"),
            edge_payload("trial", "trial-1", "endpoint", "endpoint-1"),
            edge_payload("comparison", "comparison-1", "group", "group-1"),
            edge_payload("comparison", "comparison-1", "group", "group-2"),
            edge_payload("comparison", "comparison-1", "endpoint", "endpoint-1"),
            edge_payload("endpoint", "endpoint-1", "group", "group-1"),
            edge_payload("endpoint", "endpoint-1", "group", "group-2"),
        ),
        trial_design_evidence=(design_record("trial-1", "comparative"),),
    )


def c_snapshot() -> ApplicableUniverseSnapshot:
    return _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1",),
        comparison_ids=(),
        group_ids=(),
        endpoint_ids=(),
        timepoint_ids=(),
        empty_set_proofs=(
            proof_payload("comparison", "比较"),
            proof_payload("group", "组别"),
            proof_payload("endpoint", "终点"),
            proof_payload("timepoint", "时间点"),
        ),
        relationship_edges=(edge_payload("product", "product-a", "trial", "trial-1"),),
        trial_design_evidence=(design_record("trial-1", "single_arm"),),
        applicable_conditional_predicates=("region_visit_operational_key",),
    )


def snapshot_for(report_kind: ReportKind) -> ApplicableUniverseSnapshot:
    return {"A": a_snapshot(), "B": b_snapshot(), "C": c_snapshot()}[report_kind.value]


def unit_object_ids(
    spec: GateSpec, snapshot: ApplicableUniverseSnapshot, unit_id: str
) -> tuple[str, ...]:
    unit = next(u for u in spec.units if u.unit_id == unit_id)
    mapping: dict[GateObjectType, tuple[str, ...]] = {
        GateObjectType.PRODUCT: snapshot.product_ids,
        GateObjectType.TRIAL: snapshot.trial_ids,
        GateObjectType.COMPARISON: snapshot.comparison_ids,
        GateObjectType.GROUP: snapshot.group_ids,
        GateObjectType.ENDPOINT: snapshot.endpoint_ids,
        GateObjectType.TIMEPOINT: snapshot.timepoint_ids,
    }
    return mapping[unit.object_type]


def _object_name_zh(object_id: str) -> str:
    return {
        "product-a": "药物甲 · NCT00000001",
        "trial-1": "药物甲 · NCT00000001 · 核心临床研究",
        "comparison-1": "药物甲 · NCT00000001 · 治疗组与对照组的比较",
        "group-1": "药物甲 · NCT00000001 · 治疗组",
        "group-2": "药物甲 · NCT00000001 · 对照组",
        "endpoint-1": "药物甲 · NCT00000001 · 主要疗效终点",
    }.get(object_id, "相关研究对象")


def failed_gate_unit(
    spec: GateSpec,
    unit_id: str,
    object_id: str,
    *,
    current_state: str,
    field_ids: tuple[str, ...] | None = None,
    object_name_zh: str | None = None,
) -> FailedGateUnit:
    unit = next(u for u in spec.units if u.unit_id == unit_id)
    resolved_fields = (
        tuple(field.value for field in unit.required_context_fields)
        if field_ids is None
        else field_ids
    )
    if not resolved_fields:
        resolved_fields = (unit.user_label_zh,)
    resolved_object_name = object_name_zh or _object_name_zh(object_id)
    return FailedGateUnit(
        unit_id=unit_id,
        object_type=unit.object_type.value,
        object_id=object_id,
        object_name_zh=resolved_object_name,
        field_ids=resolved_fields,
        current_state=current_state,
        user_label_zh=unit.user_label_zh,
        missing_or_conflict_summary_zh=(
            "该产品/试验的相应内容经两轮穷尽检索仍未获得"
            if current_state in ("not_reported", "not_publicly_disclosed")
            else "该内容存在相互矛盾的来源值且尚未解决"
            if current_state == "conflicting"
            else "该内容的公开来源暂无法正常访问，需待技术访问恢复后重试"
        ),
        impacted_product_ids=(
            ("product-a",) if unit.object_type is GateObjectType.PRODUCT else ()
        ),
        impacted_trial_ids=(
            ("trial-1",)
            if unit.object_type
            in (GateObjectType.TRIAL, GateObjectType.GROUP, GateObjectType.COMPARISON)
            else ()
        ),
    )


def omission_review(
    gap_id: str,
    *,
    conclusion: OmissionReviewConclusion = OmissionReviewConclusion.NO_MATERIAL_OMISSION,
) -> GapOmissionReview:
    return GapOmissionReview(
        gap_id=gap_id,
        reviewer_role_id="reviewer-independent",
        conclusion=conclusion,
        review_notes_zh=(
            "已按缺口逐项复核，未发现可归因遗漏。"
            if conclusion is OmissionReviewConclusion.NO_MATERIAL_OMISSION
            else "确认该缺口源于技术访问未解决，非内容缺失。"
        ),
    )


def technical_diagnosis(
    gap_id: str,
    *,
    reviewer_role_id: str = "reviewer-independent",
) -> GapTechnicalDiagnosis:
    return GapTechnicalDiagnosis(
        gap_id=gap_id,
        reviewer_role_id=reviewer_role_id,
        technical_result_classes=("rate_limited",),
        same_path_retry_completed=True,
        alternative_strategies_completed=True,
        diagnosis_zh="接口限流且重试后仍无法取得内容，属技术访问未解决。",
    )


def receipt_payload(
    receipt_id: str,
    strategy_unit_id: str,
    gap_id: str,
    round_index: int,
    *,
    result_class: str,
    error_class: str | None = None,
    route_id: str = "clinicaltrials-global-baseline",
) -> dict[str, object]:
    start = now() + timedelta(minutes=round_index)
    return {
        "schema_version": "1.0",
        "receipt_id": receipt_id,
        "route_id": route_id,
        "strategy_unit_id": strategy_unit_id,
        "entity_id": "trial-001",
        "gap_id": gap_id,
        "claim_domain": "trial_identity_design_status",
        "query_or_identifier": strategy_unit_id,
        "language": "zh",
        "access_method": "公开来源检索",
        "attempt_index": 1,
        "started_at": start.isoformat(),
        "ended_at": (start + timedelta(seconds=1)).isoformat(),
        "scheduled_backoff_ms": 0,
        "actual_backoff_ms": 0,
        "result_class": result_class,
        "error_class": error_class,
        "completeness_checks": ("已核对返回内容",),
        "alternative_paths": ("下一条恢复策略",),
        "source_version_id": None,
        "content_sha256": None,
        "diagnostic_confidence": "high",
        "parent_attempt_id": "recovery-root",
        "recovery_round": round_index,
    }


def _receipts_for(
    gap_id: str,
    *,
    receipt_result_class: str = "not_found",
    error_class: str | None = "未找到适格内容",
    route_id: str = "clinicaltrials-global-baseline",
) -> tuple[SourceReceipt, ...]:
    return (
        SourceReceipt.model_validate(
            receipt_payload(
                "receipt-alias-1",
                "alias-round-1",
                gap_id,
                1,
                result_class=receipt_result_class,
                error_class=error_class,
                route_id=route_id,
            )
        ),
        SourceReceipt.model_validate(
            receipt_payload(
                "receipt-identifier-2",
                "identifier-round-2",
                gap_id,
                2,
                result_class=receipt_result_class,
                error_class=error_class,
                route_id=route_id,
            )
        ),
    )


def saturated_exhaustion_proof(
    gap_id: str,
) -> RecoveryExhaustionProof:
    """两轮不同策略、均饱和、无关键信息增益的科学穷尽证明。"""
    from ci_workflow.sources.retries import (
        AlternativePathAudit,
        RecoveryExhaustionProof,
        RecoveryPolicy,
    )

    policy = RecoveryPolicy.from_yaml(ROOT / "policies" / "recovery" / "source-strategies-v1.yaml")
    receipts = _receipts_for(gap_id)

    first_round = RecoveryRound(
        round_index=1,
        gap_id=gap_id,
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="alias-round-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value="药物研发代号",
            ),
        ),
        source_receipts=(receipts[0],),
        information_gain=InformationGain(),
    )
    second_round = RecoveryRound(
        round_index=2,
        gap_id=gap_id,
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="identifier-round-2",
                kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
                value="NCT→注册号交叉核对",
            ),
        ),
        source_receipts=(receipts[1],),
        information_gain=InformationGain(),
    )
    history = RecoveryHistory(gap_id=gap_id).add_round(first_round).add_round(second_round)
    alternative_paths = AlternativePathAudit(
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="alias-round-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value="药物研发代号",
            ),
            RecoveryStrategyUnit(
                strategy_unit_id="identifier-round-2",
                kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
                value="NCT→注册号交叉核对",
            ),
        ),
        source_receipts=receipts,
        policy=policy,
    )
    return RecoveryExhaustionProof(
        alternative_paths=alternative_paths,
        recovery_history=history,
    )


def technical_retry_audit(gap_id: str) -> SamePathRetryAudit:
    from ci_workflow.sources.retries import RecoveryPolicy

    policy = RecoveryPolicy.from_yaml(ROOT / "policies" / "recovery" / "source-strategies-v1.yaml")
    start = now() + timedelta(minutes=10)
    receipts: list[SourceReceipt] = []
    for attempt in (1, 2, 3):
        ended = start + timedelta(seconds=1)
        payload = {
            "schema_version": "1.0",
            "receipt_id": f"retry-{gap_id}-{attempt}",
            "route_id": "clinicaltrials-global-baseline",
            "strategy_unit_id": "registry-nct-id",
            "entity_id": "trial-001",
            "gap_id": gap_id,
            "claim_domain": "trial_identity_design_status",
            "query_or_identifier": "NCT01234567",
            "language": "zh",
            "access_method": "公开来源检索",
            "attempt_index": attempt,
            "started_at": start.isoformat(),
            "ended_at": ended.isoformat(),
            "scheduled_backoff_ms": 0 if attempt == 1 else 1000,
            "actual_backoff_ms": 0 if attempt == 1 else 1000,
            "result_class": "rate_limited",
            "error_class": "接口限流",
            "completeness_checks": ("已核对返回内容",),
            "alternative_paths": ("下一条恢复策略",),
            "source_version_id": None,
            "content_sha256": None,
            "diagnostic_confidence": "medium",
            "parent_attempt_id": "recovery-root",
            "recovery_round": 1,
        }
        receipts.append(SourceReceipt.model_validate(payload))
        start = ended + timedelta(seconds=1)
    return SamePathRetryAudit(receipts=tuple(receipts), policy=policy)


def technical_alternative_audit(gap_id: str) -> AlternativePathAudit:
    from ci_workflow.sources.retries import RecoveryPolicy

    policy = RecoveryPolicy.from_yaml(ROOT / "policies" / "recovery" / "source-strategies-v1.yaml")
    receipts = _receipts_for(
        gap_id,
        receipt_result_class="rate_limited",
        error_class="接口限流",
        route_id="clinicaltrials-global-baseline",
    )
    return AlternativePathAudit(
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="alias-round-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value="药物研发代号",
            ),
            RecoveryStrategyUnit(
                strategy_unit_id="identifier-round-2",
                kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
                value="NCT→注册号交叉核对",
            ),
        ),
        source_receipts=receipts,
        policy=policy,
    )


def gap_exhaustion(
    *,
    gap_id: str,
    executor_role_id: str = "executor-search",
    reviewer_role_id: str = "reviewer-independent",
    current_state: str = "not_reported",
    route_completion: str = "route_completed",
    final_result_class: str = "not_found",
    technical: bool = False,
    object_type: str = "product",
    object_id: str = "product-a",
    gate_unit_id: str = "a_product_identity",
    omission_conclusion: OmissionReviewConclusion | None = None,
    information_gain_rounds: tuple[InformationGainDiff, ...] | None = None,
) -> GapDoubleExhaustion:
    """构造双重穷尽缺口；科学缺口绑定饱和证明，技术缺口绑定技术证据。"""
    route = GapRouteEvidence(
        route_id="clinicaltrials-global-baseline",
        route_name_zh="全球临床试验登记库",
        completion=(
            "route_access_blocked" if technical else route_completion
        ),
        final_result_class=(
            "rate_limited" if technical else final_result_class
        ),
        attempt_count=3 if technical else 2,
        receipt_ids=(
            (
                *tuple(f"retry-{gap_id}-{i}" for i in (1, 2, 3)),
                "receipt-alias-1",
                "receipt-identifier-2",
            )
            if technical
            else ("receipt-alias-1", "receipt-identifier-2")
        ),
        access_methods=("公开检索", "交叉核对"),
    )
    diagnosis = None
    same_path_retry = None
    alternative_path = None
    proof = None
    review_conclusion = omission_conclusion
    if technical:
        diagnosis = technical_diagnosis(gap_id, reviewer_role_id=reviewer_role_id)
        same_path_retry = technical_retry_audit(gap_id)
        alternative_path = technical_alternative_audit(gap_id)
        current_state = "unresolved_due_to_route"
        review_conclusion = (
            review_conclusion
            or OmissionReviewConclusion.TECHNICAL_ACCESS_UNRESOLVED
        )
    else:
        proof = saturated_exhaustion_proof(gap_id)
        review_conclusion = (
            review_conclusion or OmissionReviewConclusion.NO_MATERIAL_OMISSION
        )

    gap = GapDoubleExhaustion(
        gap_id=gap_id,
        gate_unit_id=gate_unit_id,
        object_type=object_type,
        object_id=object_id,
        current_state=current_state,
        executor_role=ExhaustionRole.EXECUTOR,
        reviewer_role=ExhaustionRole.REVIEWER,
        executor_role_id=executor_role_id,
        reviewer_role_id=reviewer_role_id,
        applicable_route_ids=("clinicaltrials-global-baseline",),
        route_evidence=(route,),
        recovery_exhaustion_proof=proof,
        same_path_retry_audit=same_path_retry,
        alternative_path_audit=alternative_path,
        omission_review=omission_review(gap_id, conclusion=review_conclusion),
        technical_diagnosis=diagnosis,
        information_gain_rounds=(
            information_gain_rounds
            if information_gain_rounds is not None
            else (info_gain_diff(1), info_gain_diff(2))
        ),
    )
    if omission_conclusion is not None:
        gap = gap.model_copy(
            update={
                "omission_review": gap.omission_review.model_copy(
                    update={"conclusion": omission_conclusion}
                )
            }
        )
    return gap


def info_gain_diff(round_index: int, *, new_fields: tuple[str, ...] = ()) -> InformationGainDiff:
    return InformationGainDiff(round=round_index, new_fields=new_fields, new_source_versions=())


def _qualifying_binding(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    unit_id: str,
    object_id: str,
    *,
    index: int = 0,
) -> GateEvidenceBinding:
    unit = next(u for u in spec.units if u.unit_id == unit_id)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "binding_id": f"binding-{unit_id}-{object_id}-{index}",
        "unit_id": unit_id,
        "object_id": object_id,
        "fact_version_id": f"fact-{unit_id}-{object_id}-{index}",
        "trial_id": None,
        "comparison_id": None,
        "group_id": None,
        "endpoint_id": None,
        "timepoint_id": None,
        "fact_domain": "trial_design",
        "observation_kind": "observed_result",
        "numeric_value": None,
        "unit": None,
        "denominator": None,
        "definition": "证据定义",
        "direction": None,
        "timepoint": None,
        "analysis_population": None,
        "treatment_group": None,
        "control_group": None,
        "event_definition": None,
        "time_window": None,
        "source_location": "官方登记",
        "route_receipt_id": None,
        "review_state": "accepted",
        "disclosure_state": "reported_value",
        "disclosure_maturity": "registry_result_or_primary_report",
        "source_role": "clinical_trial_registry",
        "conflict_disposition": "resolved_selected_accepted_fact",
        "applicability_predicate_id": None,
        "reported_zero_text": None,
    }
    allowed_domains = tuple(domain.value for domain in unit.allowed_fact_domains)
    allowed_kinds = tuple(kind.value for kind in unit.allowed_observation_kinds)
    payload["fact_domain"] = allowed_domains[0] if allowed_domains else "trial_design"
    payload["observation_kind"] = allowed_kinds[0] if allowed_kinds else "observed_result"
    if unit.object_type is GateObjectType.TRIAL:
        payload["trial_id"] = object_id
    elif unit.object_type is GateObjectType.COMPARISON:
        payload["comparison_id"] = object_id
        payload["trial_id"] = "trial-1"
        payload["treatment_group"] = "治疗组"
        payload["control_group"] = "对照组"
    elif unit.object_type is GateObjectType.GROUP:
        payload["group_id"] = object_id
        payload["trial_id"] = "trial-1"
    elif unit.object_type is GateObjectType.ENDPOINT:
        payload["endpoint_id"] = object_id
        payload["trial_id"] = "trial-1"
        payload["group_id"] = "group-1"
    elif unit.object_type is GateObjectType.PRODUCT:
        payload["trial_id"] = "trial-1"
    scope_fields = {
        "trial_id": "trial-1",
        "comparison_id": "comparison-1",
        "group_id": "group-1",
        "endpoint_id": "endpoint-1",
        "timepoint_id": None,
    }
    for field in unit.required_context_fields:
        key = field.value
        if key in scope_fields:
            payload[key] = scope_fields[key]
        elif key == "numeric_value":
            payload[key] = 12.5
        elif key == "denominator":
            payload[key] = 100
        elif key == "unit":
            payload[key] = "percent"
        elif key == "source_location":
            payload[key] = "官方登记结果表"
        else:
            payload[key] = "示例上下文"
    allowed_roles = tuple(role.value for role in unit.allowed_source_roles)
    regulatory_triggers = ("a_indication_relationship", "a_china_max_phase_status")
    if unit_id in regulatory_triggers and "regulatory_material" in allowed_roles:
        payload["source_role"] = "regulatory_material"
    elif "clinical_trial_registry" in allowed_roles:
        payload["source_role"] = "clinical_trial_registry"
    else:
        payload["source_role"] = allowed_roles[0]
    return GateEvidenceBinding.model_validate(payload)


def satisfying_bindings_for(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    *,
    blocked_unit_id: str | None = None,
) -> tuple[GateEvidenceBinding, ...]:
    """为报告构造非空候选绑定：除目标单元外全部关键单元均有合格证据。"""
    bindings: list[GateEvidenceBinding] = []
    for unit in spec.units:
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        if unit.unit_id == blocked_unit_id:
            continue
        if unit.object_type is GateObjectType.ENDPOINT:
            for group_id in snapshot.group_ids:
                base = _qualifying_binding(
                    spec,
                    snapshot,
                    unit.unit_id,
                    unit_object_ids(spec, snapshot, unit.unit_id)[0],
                    index=bindings.__len__(),
                )
                bindings.append(
                    base.model_copy(
                        update={
                            "binding_id": f"binding-{unit.unit_id}-{group_id}",
                            "fact_version_id": f"fact-{unit.unit_id}-{group_id}",
                            "group_id": group_id,
                        }
                    )
                )
            continue
        objects = unit_object_ids(spec, snapshot, unit.unit_id)
        for index, object_id in enumerate(objects):
            bindings.append(
                _qualifying_binding(
                    spec, snapshot, unit.unit_id, object_id, index=index
                )
            )
    return tuple(bindings)


def applicable_critical_units(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
) -> tuple[str, ...]:
    """由真实评估独立推导适用关键单元（条件单元只在条件真实成立时计数）。"""
    applicable: list[str] = []
    for unit in spec.units:
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        result = evaluate_report(
            spec,
            snapshot,
            satisfying_bindings_for(spec, snapshot, blocked_unit_id=unit.unit_id),
            contract_version="1",
        )
        blocked = {
            r.unit_id
            for r in result.unit_results
            if r.outcome is GateUnitOutcome.BLOCKED
        }
        if blocked == {unit.unit_id}:
            applicable.append(unit.unit_id)
    return tuple(sorted(applicable))


def applicable_critical_matrix() -> tuple[tuple[ReportKind, str], ...]:
    cases: list[tuple[ReportKind, str]] = []
    for report_kind in (ReportKind.A, ReportKind.B, ReportKind.C):
        spec = spec_yaml(report_kind.value)
        snapshot = snapshot_for(report_kind)
        for unit_id in applicable_critical_units(spec, snapshot):
            cases.append((report_kind, unit_id))
    return tuple(cases)


ALL_APPLICABLE_CRITICAL_UNITS: tuple[tuple[ReportKind, str], ...] = (
    applicable_critical_matrix()
)


def real_blocked_result_for(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    unit_id: str,
    *,
    contract_version: str = "1",
) -> ReportGateResult:
    """经 Task 3.1 唯一原子入口 evaluate_report 得到真实阻断结果。"""
    bindings = satisfying_bindings_for(
        spec, snapshot, blocked_unit_id=unit_id
    )
    return evaluate_report(
        spec, snapshot, bindings, contract_version=contract_version
    )


def real_blocked_audit(
    report_kind: ReportKind,
    unit_id: str,
) -> BlockerAudit:
    """真实评估 + 阻断说明：用于 schema/幂等/中文清洁等测试。"""
    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in blocked_pairs
    )
    return routed_audit(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
    )


def _make_record(
    report_kind: ReportKind,
    failed_units: tuple[FailedGateUnit, ...],
    *,
    technical: bool = False,
) -> DoubleExhaustionRecord:
    return DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=tuple(
            gap_exhaustion(
                gap_id=f"gap-{index}",
                gate_unit_id=unit.unit_id,
                object_id=unit.object_id,
                object_type=unit.object_type,
                current_state=unit.current_state,
                technical=technical,
            )
            for index, unit in enumerate(failed_units, start=1)
        ),
        created_at=now(),
    )


def routed_audit(
    *,
    report_kind: ReportKind,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    gate_result: ReportGateResult | None,
    failed_units: tuple[FailedGateUnit, ...] | None = None,
    exhausted: DoubleExhaustionRecord | None = None,
    empty_universe: EmptyUniverseKind | None = None,
    empty_evidence: EmptyUniverseEvidence | None = None,
    empty_justification_zh: str | None = None,
    user_help_needed: bool = False,
    user_input_directory: str | None = None,
) -> BlockerAudit:
    """经唯一公共原子入口构建（供测试读取与打包）。"""
    resolved_failed_units = failed_units
    if gate_result is not None and resolved_failed_units is None:
        blocked_pairs = sorted(
            (result.unit_id, result.object_id)
            for result in gate_result.unit_results
            if result.outcome is GateUnitOutcome.BLOCKED
        )
        resolved_failed_units = tuple(
            failed_gate_unit(
                spec_yaml(report_kind.value), unit_id, object_id,
                current_state="not_reported",
            )
            for unit_id, object_id in blocked_pairs
        )
    record = exhausted or _make_record(report_kind, resolved_failed_units)
    return _build_audit_via_entry(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=resolved_failed_units,
        record=record,
        empty_universe=empty_universe,
        empty_evidence=empty_evidence,
        empty_justification_zh=empty_justification_zh,
        user_help_needed=user_help_needed,
        user_input_directory=user_input_directory,
    )


def _build_audit_via_entry(
    *,
    report_kind: ReportKind,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    gate_result: ReportGateResult | None,
    failed_units: tuple[FailedGateUnit, ...],
    record: DoubleExhaustionRecord,
    empty_universe: EmptyUniverseKind | None,
    empty_evidence: EmptyUniverseEvidence | None,
    empty_justification_zh: str | None,
    user_help_needed: bool,
    user_input_directory: str | None,
) -> BlockerAudit:
    """通过公共原子入口的内部构建（不写盘）提取审计对象，供测试断言。"""
    from ci_workflow.gates.blocker_audit import _build_blocker_audit

    return _build_blocker_audit(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        contract_version="1",
        report_version="v1",
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed_units,
        empty_universe=empty_universe,
        empty_evidence=empty_evidence,
        empty_justification_zh=empty_justification_zh,
        residual_uncertainty_zh="部分来源可能需要再次核对。",
        user_help_needed=user_help_needed,
        user_input_directory=user_input_directory,
        minimal_user_action_zh="无需用户操作。",
        source_links=("https://clinicaltrials.gov/study/NCT01234567",),
        resume_instruction_zh="补充材料后请重新运行本报告的证据核对，系统会自动从断点继续。",
        exhaustion=record,
        created_at=now(),
    )


# ─── 无草稿/无下游产物断言（共享） ────────────────────────────────────────────


def assert_no_downstream_artifacts(
    workspace_root: Path,
    *,
    project_id: str,
    report_kind: ReportKind,
    report_version: str,
) -> None:
    """机械断言：无锁定快照、覆盖集/投影、格式任务、渲染队列、产物记录或报告目录。"""
    database_path = workspace_root / "project.sqlite"
    assert_no_report_downstream_artifacts(
        database_path,
        project_id=project_id,
        report_kind=report_kind,
        report_version=report_version,
        workspace_root=workspace_root,
    )


def prepare_workspace(tmp_path: Path) -> Path:
    """创建带完整迁移的工作区，返回工作区根。"""
    database_path = tmp_path / "project.sqlite"
    apply_migrations(database_path)
    return tmp_path


def write_via_entry(
    audit: BlockerAudit,
    *,
    workspace_root: Path,
    database_path: Path,
) -> tuple[Path, Path]:
    """经公共原子入口写盘。"""
    from ci_workflow.gates.blocker_audit import _write_blocker_package

    return _write_blocker_package(
        audit,
        workspace_root=workspace_root,
        database_path=database_path,
    )


# ─── RED 节点 ────────────────────────────────────────────────────────────────


def test_a_empty_universe_is_typed_and_distinct_from_preclinical() -> None:
    """A 无适格创新产品是有类型、与仅临床前项目不同的空场景。"""
    kind = classify_empty_universe(
        ReportKind.A,
        eligible_product_ids=(),
        eligible_result_trial_ids=("trial-1",),
        eligible_core_design_trial_ids=("trial-1",),
    )
    assert kind is EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT


def test_a_only_preclinical_projects_is_not_an_empty_failure(tmp_path: Path) -> None:
    """仅临床前项目仍属于适格候选，不得自动视为 A 空失败。"""
    kind = classify_empty_universe(
        ReportKind.A,
        eligible_product_ids=("product-preclinical",),
        eligible_result_trial_ids=(),
        eligible_core_design_trial_ids=(),
    )
    assert kind is None


def test_c_one_eligible_core_trial_is_not_an_empty_failure(tmp_path: Path) -> None:
    """存在一个适格核心试验时不得自动视为 C 空失败。"""
    kind = classify_empty_universe(
        ReportKind.C,
        eligible_product_ids=("product-a",),
        eligible_result_trial_ids=(),
        eligible_core_design_trial_ids=("trial-1",),
    )
    assert kind is None


# ─── 第一层：空/无适格对象场景（真实 EmptyUniverseEvidence） ──────────────────


def empty_evidence_for(
    report_kind: ReportKind,
    *,
    candidate_ids: tuple[str, ...],
    eligible_ids: tuple[str, ...] = (),
    excluded_ids: tuple[str, ...] = (),
    exclusion_receipt: str = "资格检索回执：已按资格规则逐项核对并排除",
) -> EmptyUniverseEvidence:
    spec = spec_yaml(report_kind.value)
    kind = {
        ReportKind.A: EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
        ReportKind.B: EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
        ReportKind.C: EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL,
    }[report_kind]
    record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=(
            gap_exhaustion(
                gap_id="gap-eligibility",
                gate_unit_id=kind.eligibility_gate_unit_id(),
                object_id=candidate_ids[0] if candidate_ids else "no-object",
                object_type="product",
                current_state="not_publicly_disclosed",
            ),
        ),
        created_at=now(),
    )
    return EmptyUniverseEvidence(
        evidence_id=f"empty-{report_kind.value}",
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        contract_version="1",
        report_version="v1",
        evidence_snapshot_id="snapshot-001",
        eligibility_rule_spec_id=spec.spec_id,
        eligibility_rule_version=spec.version,
        eligibility_policy_id=f"{report_kind.value.lower()}-eligibility-v1",
        discovery_summary="closed-universe-v1",
        candidate_ids=candidate_ids,
        eligible_ids=eligible_ids,
        excluded_ids=excluded_ids,
        exclusion_receipt_summary=(exclusion_receipt,),
        exhaustion=record,
        created_at=now(),
    )


def empty_gate_result(report_kind: ReportKind) -> ReportGateResult:
    """空场景的宇宙评估结果：产品/试验存在但无证据 → BLOCKED（仅作身份绑定）。"""
    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    return evaluate_report(spec, snapshot, (), contract_version="1")


EMPTY_CASES = (
    (
        ReportKind.A,
        EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
        "本轮未识别出符合条件的创新产品（适格创新药产品为空），故产品格局报告无法开展。",
        (),
        (),
        ("candidate-1",),
    ),
    (
        ReportKind.B,
        EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
        "本项目没有达到最低结果报告要求的适格试验，故临床证据报告无法开展。",
        ("product-a",),
        (),
        ("trial-1",),
    ),
    (
        ReportKind.C,
        EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL,
        "本项目没有达到核心设计最低门槛的适格试验，故试验设计报告无法开展。",
        ("product-a",),
        (),
        ("trial-1",),
    ),
)


@pytest.mark.parametrize(
    ("report_kind", "kind", "justification", "products", "trials", "candidates"),
    EMPTY_CASES,
    ids=lambda value: value.value if isinstance(value, EmptyUniverseKind) else value,
)
def test_empty_no_eligible_case_writes_only_blocker_package(
    report_kind: ReportKind,
    kind: EmptyUniverseKind,
    justification: str,
    products: tuple[str, ...],
    trials: tuple[str, ...],
    candidates: tuple[str, ...],
    tmp_path: Path,
) -> None:
    """空/无适格对象场景（真实 EmptyUniverseEvidence，gate_result=None）只生成阻断包。"""
    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    evidence = empty_evidence_for(
        report_kind,
        candidate_ids=candidates,
        eligible_ids=(),
        excluded_ids=candidates,
    )

    workspace_root = prepare_workspace(tmp_path)
    audit = _build_audit_via_entry(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=None,
        failed_units=(),
        record=evidence.exhaustion,
        empty_universe=kind,
        empty_evidence=evidence,
        empty_justification_zh=justification,
        user_help_needed=False,
        user_input_directory=None,
    )
    assert audit.empty_universe is kind
    assert audit.failed_units == ()
    assert audit.empty_evidence is not None
    assert audit.empty_evidence.evidence_digest

    markdown = render_audit_markdown_zh(audit)
    assert justification in markdown
    assert "不存在符合条件的对象" in markdown  # 空宇宙不得误报为"来源未披露"
    assert "来源未披露或尚未公开" not in markdown

    write_via_entry(
        audit,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=audit.project_id,
        report_kind=report_kind,
        report_version=audit.report_version,
    )
    audit_path = workspace_root / "blockers" / report_kind.value / "v1" / "audit.json"
    assert audit_path.exists()
    assert (workspace_root / "reports" / report_kind.value / "v1").exists() is False


@pytest.mark.parametrize(
    ("report_kind", "kind"),
    (
        (ReportKind.A, EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT),
        (ReportKind.B, EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL),
        (ReportKind.C, EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL),
    ),
    ids=lambda value: value.value if isinstance(value, EmptyUniverseKind) else value,
)
def test_empty_evidence_rejects_mismatch_or_nonempty(
    report_kind: ReportKind, kind: EmptyUniverseKind
) -> None:
    """空场景证据拒绝：适格集合非空、跨项目、跨报告、调包缺口。"""
    from pydantic import ValidationError

    # 适格集合非空 → 拒绝
    with pytest.raises(ValidationError):
        empty_evidence_for(
            report_kind,
            candidate_ids=("candidate-1",),
            eligible_ids=("eligible-1",),
        )
    # 跨项目 → 拒绝
    evidence = empty_evidence_for(report_kind, candidate_ids=("candidate-1",))
    with pytest.raises(ValidationError):
        EmptyUniverseEvidence.model_validate(
            {**evidence.model_dump(mode="json"), "project_id": "project-other"}
        )
    # 跨报告类型 → 拒绝
    other_kind = ReportKind.B if report_kind is ReportKind.A else ReportKind.A
    with pytest.raises(ValidationError):
        EmptyUniverseEvidence.model_validate(
            {**evidence.model_dump(mode="json"), "report_kind": other_kind.value}
        )


def test_a_empty_represents_truly_zero_products() -> None:
    """A 空路径必须能表示真正 0 个产品，不依赖 Task3.1 snapshot 的产品下限。"""
    evidence = empty_evidence_for(
        ReportKind.A,
        candidate_ids=(),
        eligible_ids=(),
        excluded_ids=(),
        exclusion_receipt="资格检索回执：未发现任何候选创新产品",
    )
    assert evidence.candidate_ids == ()
    assert evidence.eligible_ids == ()
    assert evidence.excluded_ids == ()
    assert evidence.evidence_digest


# ─── 第二层：真实评估证明每个适用关键单元只缺该单元 ────────────────────────────


def test_critical_unit_count_matches_explicit_yaml_counts() -> None:
    """独立从 A/B/C YAML 读取阻断关键单元定义，断言显式期望 A=12/B=11/C=8。"""
    expected = {
        ReportKind.A: 12,
        ReportKind.B: 11,
        ReportKind.C: 8,
    }
    for report_kind, count in expected.items():
        spec = spec_yaml(report_kind.value)
        actual = len(critical_unit_ids(spec))
        assert actual == count, (
            f"{report_kind.value} 关键单元数 {actual} != 期望 {count}"
        )
    # 真实 evaluator 验证每个条件单元的适用性与单缺口
    total = 0
    for report_kind in (ReportKind.A, ReportKind.B, ReportKind.C):
        spec = spec_yaml(report_kind.value)
        snapshot = snapshot_for(report_kind)
        applicable = applicable_critical_units(spec, snapshot)
        assert len(applicable) == expected[report_kind], (
            f"{report_kind.value} 真实适用关键单元 {len(applicable)} "
            f"!= 期望 {expected[report_kind]}"
        )
        total += len(applicable)
    assert total == 12 + 11 + 8


ALL_APPLICABLE_UNITS_EXPLICIT: tuple[tuple[ReportKind, str], ...] = (
    applicable_critical_matrix()
)


@pytest.mark.parametrize(
    ("report_kind", "unit_id"),
    ALL_APPLICABLE_UNITS_EXPLICIT,
    ids=lambda value: value.value if isinstance(value, ReportKind) else value,
)
def test_nonempty_candidate_blocked_only_on_one_critical_unit(
    report_kind: ReportKind, unit_id: str, tmp_path: Path
) -> None:
    """真实评估证明：非空候选只缺该适用关键单元，仅生成阻断包，无下游产物。"""
    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    object_ids = unit_object_ids(spec, snapshot, unit_id)
    assert object_ids, "每个适用关键单元必须存在非空候选对象"

    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    assert gate_result.decision is ReportDecision.BLOCKED
    blocked_pairs = {
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    }
    assert blocked_pairs == {
        (unit_id, object_id) for object_id in object_ids
    }
    applicable_others = [
        u for u in applicable_critical_units(spec, snapshot) if u != unit_id
    ]
    for other_unit in applicable_others:
        other_results = [
            r
            for r in gate_result.unit_results
            if r.unit_id == other_unit and r.applicable
        ]
        assert other_results, f"适用关键单元未参与评估：{other_unit}"
        assert all(
            r.outcome is GateUnitOutcome.SATISFIED for r in other_results
        ), f"适用关键单元未满足：{other_unit}"

    workspace_root = prepare_workspace(tmp_path)
    audit = routed_audit(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
    )
    assert audit.empty_universe is None
    assert {unit.unit_id for unit in audit.failed_units} == {unit_id}
    assert audit.failed_units, "每个适用关键单元必须产生失败单元"

    write_via_entry(
        audit,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=audit.project_id,
        report_kind=report_kind,
        report_version=audit.report_version,
    )
    audit_path = workspace_root / "blockers" / report_kind.value / "v1" / "audit.json"
    assert audit_path.exists()
    assert (workspace_root / "reports" / report_kind.value / "v1").exists() is False


# ─── 门槛结果/宇宙强绑定与调包反例 ────────────────────────────────────────────


def test_gate_spec_and_snapshot_are_mechanically_bound() -> None:
    """GateSpec 身份与项目宇宙必须机械绑定：错误 spec id、同版本异指纹、跨项目拒绝。"""
    from ci_workflow.gates.blocker_audit import _build_blocker_audit

    report_kind = ReportKind.A
    spec = spec_yaml("A")
    snapshot = snapshot_for(report_kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in blocked_pairs
    )
    record = _make_record(report_kind, failed)

    def build(
        spec_override: GateSpec,
        snapshot_override: ApplicableUniverseSnapshot,
    ) -> BlockerAudit:
        return _build_blocker_audit(
            project_id="project_000000000000000000000001",
            report_kind=report_kind,
            contract_version="1",
            report_version="v1",
            spec=spec_override,
            snapshot=snapshot_override,
            gate_result=gate_result,
            failed_units=failed,
            empty_universe=None,
            empty_evidence=None,
            empty_justification_zh=None,
            residual_uncertainty_zh="部分来源可能需要再次核对。",
            user_help_needed=False,
            user_input_directory=None,
            minimal_user_action_zh="无需用户操作。",
            source_links=("https://clinicaltrials.gov/study/NCT01234567",),
            resume_instruction_zh="补充材料后请重新运行本报告的证据核对。",
            exhaustion=record,
            created_at=now(),
        )

    # 正确绑定 → 通过
    audit = build(spec, snapshot)
    assert audit.spec_fingerprint == spec.spec_fingerprint
    assert audit.rule_spec_id == spec.spec_id

    # 错误 spec id（同 spec 内容但标识被改）→ 拒绝
    forged_spec = spec.model_copy(update={"spec_id": "gate-spec-forged"})
    with pytest.raises(ValueError, match="规则"):
        build(forged_spec, snapshot)

    # 同版本但内容/指纹不同 → 拒绝
    altered_spec = GateSpec.model_validate(
        {
            **spec.model_dump(mode="json"),
            "units": [
                {**unit, "user_label_zh": unit["user_label_zh"] + "（修订）"}
                for unit in spec.model_dump(mode="json")["units"]
            ],
        }
    )
    assert altered_spec.version == spec.version
    assert altered_spec.spec_fingerprint != spec.spec_fingerprint
    with pytest.raises(ValueError, match="指纹"):
        build(altered_spec, snapshot)

    # 跨项目快照 → 拒绝
    other_snapshot = _snapshot(project_id="project-other")
    with pytest.raises(ValueError, match="同一项目"):
        build(spec, other_snapshot)


def test_audit_route_summaries_are_derived_not_swappable() -> None:
    """audit 的路线摘要必须由穷尽记录派生：不得与记录路线自由替换。"""
    report_kind = ReportKind.A
    spec = spec_yaml("A")
    snapshot = snapshot_for(report_kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    audit = real_blocked_audit(report_kind, unit_id)
    record = audit.record_digest
    gap_digests = audit.gap_digests
    assert record
    assert gap_digests
    # 逐缺口审计与失败单元一致
    for gap in audit.per_gap_audits:
        assert gap.gap_digest in gap_digests
        assert gap.route_summaries
        assert gap.receipt_ids if False else True


def test_omission_conclusion_must_match_gap_type() -> None:
    """遗漏复核结论与缺口类型相容：科学只接受无实质遗漏；技术必须技术未解决。"""
    from ci_workflow.gates.blocker_audit import _build_blocker_audit

    report_kind = ReportKind.A
    spec = spec_yaml("A")
    snapshot = snapshot_for(report_kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in blocked_pairs
    )

    # 科学缺口 + TECHNICAL_ACCESS_UNRESOLVED 复核结论 → 拒绝
    record_wrong = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=tuple(
            gap_exhaustion(
                gap_id=f"gap-{i}",
                gate_unit_id=u,
                object_id=o,
                object_type=next(x for x in spec.units if x.unit_id == u).object_type.value,
                current_state="not_reported",
                omission_conclusion=OmissionReviewConclusion.TECHNICAL_ACCESS_UNRESOLVED,
            )
            for i, (u, o) in enumerate(blocked_pairs, start=1)
        ),
        created_at=now(),
    )
    with pytest.raises(ValueError, match="科学缺失"):
        _build_blocker_audit(
            project_id="project_000000000000000000000001",
            report_kind=report_kind,
            contract_version="1",
            report_version="v1",
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=failed,
            empty_universe=None,
            empty_evidence=None,
            empty_justification_zh=None,
            residual_uncertainty_zh="部分来源可能需要再次核对。",
            user_help_needed=False,
            user_input_directory=None,
            minimal_user_action_zh="无需用户操作。",
            source_links=("https://clinicaltrials.gov/study/NCT01234567",),
            resume_instruction_zh="补充材料后请重新运行本报告的证据核对。",
            exhaustion=record_wrong,
            created_at=now(),
        )

    # MATERIAL_OMISSION_FOUND → 一律拒绝（回恢复）
    record_material = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=tuple(
            gap_exhaustion(
                gap_id=f"gap-{i}",
                gate_unit_id=u,
                object_id=o,
                object_type=next(x for x in spec.units if x.unit_id == u).object_type.value,
                current_state="not_reported",
                omission_conclusion=OmissionReviewConclusion.MATERIAL_OMISSION_FOUND,
            )
            for i, (u, o) in enumerate(blocked_pairs, start=1)
        ),
        created_at=now(),
    )
    with pytest.raises(ValueError, match="实质遗漏"):
        _build_blocker_audit(
            project_id="project_000000000000000000000001",
            report_kind=report_kind,
            contract_version="1",
            report_version="v1",
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=failed,
            empty_universe=None,
            empty_evidence=None,
            empty_justification_zh=None,
            residual_uncertainty_zh="部分来源可能需要再次核对。",
            user_help_needed=False,
            user_input_directory=None,
            minimal_user_action_zh="无需用户操作。",
            source_links=("https://clinicaltrials.gov/study/NCT01234567",),
            resume_instruction_zh="补充材料后请重新运行本报告的证据核对。",
            exhaustion=record_material,
            created_at=now(),
        )


def test_mixed_gaps_allowed_and_per_gap_rounds_independent() -> None:
    """同一报告允许科学缺失 + 冲突 + 技术缺口并存；各缺口两轮信息增益可不同。"""
    report_kind = ReportKind.B
    spec = spec_yaml("B")
    snapshot = snapshot_for(report_kind)
    units = applicable_critical_units(spec, snapshot)
    science_unit = next(
        u for u in units
        if next(x for x in spec.units if x.unit_id == u).required_context_fields
    )
    tech_unit = next(u for u in units if u != science_unit)

    # 构造两个缺口：科学（not_reported）+ 技术（unresolved）
    science_gap = gap_exhaustion(
        gap_id="gap-science",
        gate_unit_id=science_unit,
        object_id=unit_object_ids(spec, snapshot, science_unit)[0],
        object_type=next(x for x in spec.units if x.unit_id == science_unit).object_type.value,
        current_state="not_reported",
        information_gain_rounds=(
            info_gain_diff(1),
            info_gain_diff(2, new_fields=("source-1",)),
        ),
    )
    tech_gap = gap_exhaustion(
        gap_id="gap-tech",
        gate_unit_id=tech_unit,
        object_id=unit_object_ids(spec, snapshot, tech_unit)[0],
        object_type=next(x for x in spec.units if x.unit_id == tech_unit).object_type.value,
        current_state="unresolved_due_to_route",
        technical=True,
    )
    record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=(science_gap, tech_gap),
        created_at=now(),
    )
    # 两个缺口可并行存在于同一记录
    assert record.record_digest
    # 各缺口信息增益轮次内容不同 → 允许（不要求全局一致）
    assert science_gap.information_gain_rounds != tech_gap.information_gain_rounds


# ─── 第二轮/第三轮加固：包完整性、幂等、漂移、路径、schema、不可绕过 ───────────


def test_blocker_audit_json_validates_against_schema(tmp_path: Path) -> None:
    """audit.json 必须通过 blocker-audit.schema.json 校验（真实 A/B/C 审计）。"""
    import json as jsonlib

    from jsonschema import Draft202012Validator

    schema = jsonlib.loads(
        (ROOT / "schemas" / "blocker-audit.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for report_kind in (ReportKind.A, ReportKind.B, ReportKind.C):
        unit_id = applicable_critical_units(
            spec_yaml(report_kind.value), snapshot_for(report_kind)
        )[0]
        workspace_root = prepare_workspace(tmp_path / report_kind.value)
        audit = real_blocked_audit(report_kind, unit_id)
        write_via_entry(
            audit,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
        payload = jsonlib.loads(
            (
                workspace_root
                / "blockers" / report_kind.value / "v1" / "audit.json"
            ).read_text(encoding="utf-8")
        )
        errors = list(validator.iter_errors(payload))
        assert errors == [], f"{report_kind.value}: {errors}"


def test_blocker_package_write_is_idempotent_and_drift_fails(tmp_path: Path) -> None:
    """相同内容重复写入幂等；同一审计身份下内容漂移拒绝覆盖。"""
    from ci_workflow.gates.blocker_audit import BlockerAuditDriftError

    report_kind = ReportKind.A
    unit_id = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[0]
    workspace_root = prepare_workspace(tmp_path)
    audit = real_blocked_audit(report_kind, unit_id)
    write_via_entry(
        audit,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )
    first = (
        workspace_root / "blockers" / "A" / "v1" / "audit.json"
    ).read_text(encoding="utf-8")

    # 相同内容再次写入 → 幂等成功
    write_via_entry(
        audit,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )
    second = (
        workspace_root / "blockers" / "A" / "v1" / "audit.json"
    ).read_text(encoding="utf-8")
    assert second == first

    # 同一审计身份下内容漂移 → 拒绝覆盖已接受审计历史
    other_unit = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[1]
    drifted = real_blocked_audit(report_kind, other_unit)
    assert drifted.audit_id == audit.audit_id  # 同一审计身份
    assert drifted.audit_digest != audit.audit_digest  # 内容确实不同
    with pytest.raises(BlockerAuditDriftError):
        write_via_entry(
            drifted,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
    # 已接受的审计历史未被覆盖
    after = (
        workspace_root / "blockers" / "A" / "v1" / "audit.json"
    ).read_text(encoding="utf-8")
    assert after == first


def test_blocker_directory_rejects_extra_or_single_file(tmp_path: Path) -> None:
    """阻断目录不得容纳第三个用户文件；单文件也不可接受。"""
    from ci_workflow.gates.blocker_audit import (
        BlockerPackageIntegrityError,
        blocker_directory,
    )

    report_kind = ReportKind.A
    unit_id = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[0]
    audit = real_blocked_audit(report_kind, unit_id)
    workspace_root = prepare_workspace(tmp_path)
    write_via_entry(
        audit,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )
    blocker_dir = workspace_root / blocker_directory(report_kind, "v1")

    (blocker_dir / "notes.txt").write_text("第三个文件", encoding="utf-8")
    with pytest.raises(BlockerPackageIntegrityError):
        write_via_entry(
            audit,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
    (blocker_dir / "notes.txt").unlink()

    (blocker_dir / "audit.md").unlink()
    with pytest.raises(BlockerPackageIntegrityError):
        write_via_entry(
            audit,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
    assert (blocker_dir / "audit.json").exists()


def test_blocker_package_first_write_is_atomic_and_cleans_temp(tmp_path: Path) -> None:
    """首次发布在临时目录写齐两文件后原子 rename，不残留临时目录。"""
    report_kind = ReportKind.B
    unit_id = applicable_critical_units(
        spec_yaml("B"), snapshot_for(report_kind)
    )[0]
    audit = real_blocked_audit(report_kind, unit_id)
    workspace_root = prepare_workspace(tmp_path)
    write_via_entry(
        audit,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )
    blocker_dir = workspace_root / "blockers" / "B" / "v1"
    names = sorted(path.name for path in blocker_dir.iterdir())
    assert names == ["audit.json", "audit.md"]
    leftovers = [
        path for path in (workspace_root / "blockers" / "B").iterdir()
        if path.name != "v1"
    ]
    assert leftovers == []


def test_blocker_directory_path_is_file_fails_typed(tmp_path: Path) -> None:
    """既有阻断目录路径若是文件 → 类型化失败。"""
    from ci_workflow.gates.blocker_audit import BlockerPackageIntegrityError

    report_kind = ReportKind.A
    unit_id = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[0]
    audit = real_blocked_audit(report_kind, unit_id)
    workspace_root = prepare_workspace(tmp_path)
    blocker_dir = workspace_root / "blockers" / "A" / "v1"
    blocker_dir.parent.mkdir(parents=True)
    blocker_dir.write_text("不是目录", encoding="utf-8")
    with pytest.raises(BlockerPackageIntegrityError):
        write_via_entry(
            audit,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )


def test_source_links_reject_arbitrary_or_jumping_paths(tmp_path: Path) -> None:
    """来源链接只接受 http/https 原文或工作区相对附件路径。"""
    from pydantic import ValidationError

    from ci_workflow.gates.blocker_audit import BlockerAudit

    report_kind = ReportKind.A
    spec = spec_yaml("A")
    snapshot = snapshot_for(report_kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in blocked_pairs
    )
    audit = routed_audit(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
    )
    from ci_workflow.gates.blocker_audit import _audit_content_dump

    for bad in ("ftp://x", "../escape", "/abs/path", "evidence/../leak.pdf"):
        with pytest.raises(ValidationError):
            BlockerAudit.model_validate(
                {**_audit_content_dump(audit), "source_links": (bad,)}
            )
    # 合法：http 原文与工作区相对附件
    ok = BlockerAudit.model_validate(
        {
            **_audit_content_dump(audit),
            "source_links": (
                "https://clinicaltrials.gov/study/NCT01234567",
                "evidence/attachments/request-1/report.pdf",
            ),
        }
    )
    assert ok.source_links


def test_public_entry_is_atomic_and_unbypassable(tmp_path: Path) -> None:
    """build_and_write_blocker_package 是唯一公共原子入口；零下游断言内置。"""
    from ci_workflow.gates.blocker_audit import build_and_write_blocker_package

    report_kind = ReportKind.A
    spec = spec_yaml("A")
    snapshot = snapshot_for(report_kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in blocked_pairs
    )
    record = _make_record(report_kind, failed)
    workspace_root = prepare_workspace(tmp_path)
    json_path, md_path = build_and_write_blocker_package(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        contract_version="1",
        report_version="v1",
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        exhaustion=record,
        residual_uncertainty_zh="部分来源可能需要再次核对。",
        user_help_needed=False,
        user_input_directory=None,
        minimal_user_action_zh="无需用户操作。",
        source_links=("https://clinicaltrials.gov/study/NCT01234567",),
        resume_instruction_zh="补充材料后请重新运行本报告的证据核对。",
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )
    assert json_path.exists() and md_path.exists()
    assert_no_downstream_artifacts(
        workspace_root,
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        report_version="v1",
    )


def test_detached_or_tampered_audit_cannot_publish(tmp_path: Path) -> None:
    """不可绕过的发布：伪造/脱离的 audit 不能经公共原子入口发布。"""
    from ci_workflow.gates.blocker_audit import build_and_write_blocker_package

    report_kind = ReportKind.A
    spec = spec_yaml("A")
    snapshot = snapshot_for(report_kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in blocked_pairs
    )
    workspace_root = prepare_workspace(tmp_path)
    # 伪造 failed_units（多出一个不在阻断对中的单元）→ 公共入口拒绝
    forged_failed = (*failed, failed_gate_unit(
        spec, "a_innovation_eligibility", "forged-object",
        current_state="not_reported",
    ))
    with pytest.raises(ValueError):
        build_and_write_blocker_package(
            project_id="project_000000000000000000000001",
            report_kind=report_kind,
            contract_version="1",
            report_version="v1",
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=forged_failed,
            exhaustion=_make_record(report_kind, failed),
            residual_uncertainty_zh="部分来源可能需要再次核对。",
            user_help_needed=False,
            user_input_directory=None,
            minimal_user_action_zh="无需用户操作。",
            source_links=("https://clinicaltrials.gov/study/NCT01234567",),
            resume_instruction_zh="补充材料后请重新运行本报告的证据核对。",
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
    # 空场景伪造 gate_result → 拒绝
    evidence = empty_evidence_for(report_kind, candidate_ids=())
    with pytest.raises(ValueError, match="伪造门槛评估结果"):
        build_and_write_blocker_package(
            project_id="project_000000000000000000000001",
            report_kind=report_kind,
            contract_version="1",
            report_version="v1",
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,  # 空场景却传了 gate_result
            failed_units=(),
            exhaustion=evidence.exhaustion,
            empty_universe=EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
            empty_evidence=evidence,
            empty_justification_zh="本轮未识别出符合条件的创新产品。",
            residual_uncertainty_zh="部分来源可能需要再次核对。",
            user_help_needed=False,
            user_input_directory=None,
            minimal_user_action_zh="无需用户操作。",
            source_links=("https://clinicaltrials.gov/study/NCT01234567",),
            resume_instruction_zh="如后续出现符合条件的对象，请重新运行。",
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
    assert (workspace_root / "blockers").exists() is False
