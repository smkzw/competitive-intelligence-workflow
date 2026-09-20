"""Task 3.2 阻断时无草稿/无下游产物的集成测试（含共享夹具）。

第一层：A/B/C 三个空/无适格对象场景（真实 EmptyUniverseEvidence，gate_result=None）；
第二层：从 A/B/C GateSpec 枚举每个适用关键单元，经真实 evaluate_report 证明
       “非空候选只缺该单元”，仅生成 blockers 阻断包，无任何下游报告产物。
全部写盘用例都经过唯一公共原子入口 build_and_write_blocker_package；
私有构造/写入不承担正式路径验收（仅允许对纯构造函数做局部单测）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import (
    EvidenceGap,
    InformationGainDiff,
    SourceReceipt,
    SourceVersionRecord,
)
from ci_workflow.gates.blocker_audit import (
    BlockerAudit,
    EmptyUniverseEvidence,
    EmptyUniverseKind,
    FailedGateUnit,
    assert_no_report_downstream_artifacts,
    classify_empty_universe,
    compute_empty_universe_discovery_summary,
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
    compute_reviewer_inputs_digest_from_parts,
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
    reviewer_role_id: str = "reviewer-independent",
    reviewed_inputs_digest: str | None = None,
) -> GapOmissionReview:
    return GapOmissionReview(
        gap_id=gap_id,
        reviewer_role_id=reviewer_role_id,
        producer_context_digest="a" * 64,
        reviewer_context_digest="b" * 64,
        conclusion=conclusion,
        review_notes_zh=(
            "已按缺口逐项复核，未发现可归因遗漏。"
            if conclusion is OmissionReviewConclusion.NO_MATERIAL_OMISSION
            else "确认该缺口源于技术访问未解决，非内容缺失。"
            if conclusion is OmissionReviewConclusion.TECHNICAL_ACCESS_UNRESOLVED
            else "复核发现存在可归因遗漏，需继续恢复。"
        ),
        reviewed_inputs_digest=(
            reviewed_inputs_digest or f"fixture-inputs-{gap_id}"
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
    entity_id: str = "trial-1",
    access_method: str = "公开检索",
) -> dict[str, object]:
    start = now() + timedelta(minutes=round_index)
    return {
        "schema_version": "1.0",
        "receipt_id": receipt_id,
        "route_id": route_id,
        "strategy_unit_id": strategy_unit_id,
        "entity_id": entity_id,
        "gap_id": gap_id,
        "claim_domain": "trial_identity_design_status",
        "query_or_identifier": strategy_unit_id,
        "language": "zh",
        "access_method": access_method,
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
    entity_id: str = "trial-1",
    access_methods: tuple[str, ...] = ("公开检索", "交叉核对"),
    receipt_prefix: str = "receipt",
    strategy_prefix: str = "round",
) -> tuple[SourceReceipt, ...]:
    acquired = receipt_result_class == "content_acquired"
    return (
        SourceReceipt.model_validate(
            receipt_payload(
                f"{receipt_prefix}-1",
                f"{strategy_prefix}-1",
                gap_id,
                1,
                result_class=receipt_result_class,
                error_class=error_class,
                route_id=route_id,
                entity_id=entity_id,
                access_method=access_methods[0],
            )
            | {
                "source_version_id": (
                    f"sv-{receipt_prefix}-1" if acquired else None
                ),
                "content_sha256": ("a" * 64 if acquired else None),
            }
        ),
        SourceReceipt.model_validate(
            receipt_payload(
                f"{receipt_prefix}-2",
                f"{strategy_prefix}-2",
                gap_id,
                2,
                result_class=receipt_result_class,
                error_class=error_class,
                route_id=route_id,
                entity_id=entity_id,
                access_method=access_methods[1],
            )
            | {
                "source_version_id": (
                    f"sv-{receipt_prefix}-2" if acquired else None
                ),
                "content_sha256": ("a" * 64 if acquired else None),
            }
        ),
    )


def saturated_exhaustion_proof(
    gap_id: str,
    *,
    entity_id: str = "trial-1",
    access_methods: tuple[str, ...] = ("公开检索", "交叉核对"),
    route_id: str = "clinicaltrials-global-baseline",
    receipt_prefix: str = "receipt",
    strategy_prefix: str = "round",
    strategy_values: tuple[str, str] = ("药物研发代号", "NCT→注册号交叉核对"),
    receipt_result_class: str = "not_found",
    error_class: str | None = "未找到适格内容",
) -> RecoveryExhaustionProof:
    """两轮不同策略、均饱和、无关键信息增益的科学穷尽证明（逐路线）。"""
    from ci_workflow.sources.retries import (
        AlternativePathAudit,
        RecoveryExhaustionProof,
        RecoveryPolicy,
    )

    policy = RecoveryPolicy.from_yaml(ROOT / "policies" / "recovery" / "source-strategies-v1.yaml")
    receipts = _receipts_for(
        gap_id,
        entity_id=entity_id,
        access_methods=access_methods,
        route_id=route_id,
        receipt_prefix=receipt_prefix,
        strategy_prefix=strategy_prefix,
        receipt_result_class=receipt_result_class,
        error_class=error_class,
    )
    digest_hex = "a" * 64
    source_versions = (
        tuple(
            SourceVersionRecord.model_validate(
                {
                    "schema_version": "1.0",
                    "source_version_id": f"sv-{receipt_prefix}-{index}",
                    "source_id": f"source-{receipt_prefix}-{index}",
                    "content_sha256": digest_hex,
                    "content_relative_path": (
                        f"evidence/raw/sha256/{digest_hex[:2]}/"
                        f"{digest_hex}.bin"
                    ),
                    "media_type": "text/html",
                    "acquired_at": now().isoformat(),
                    "acquired_locator": {
                        "document_role": "source_primary",
                        "field_path": f"{receipt_prefix}-{index}",
                        "heading": "证据来源",
                        "page": None,
                        "table": None,
                        "row": None,
                        "column": None,
                        "paragraph": None,
                        "url": f"https://example.org/{receipt_prefix}-{index}",
                    },
                    "published_at": {
                        "state": "reported",
                        "value": "2026-08-12T00:00:00+08:00",
                        "locator": {
                            "document_role": "source_primary",
                            "url": f"https://example.org/{receipt_prefix}-{index}",
                        },
                    },
                    "effective_at": {
                        "state": "reported",
                        "value": "2026-08-12T00:00:00+08:00",
                        "locator": {
                            "document_role": "source_primary",
                            "url": f"https://example.org/{receipt_prefix}-{index}",
                        },
                    },
                    "first_disclosed_at": {
                        "state": "reported",
                        "value": "2026-08-12T00:00:00+08:00",
                        "locator": {
                            "document_role": "source_primary",
                            "url": f"https://example.org/{receipt_prefix}-{index}",
                        },
                    },
                    "created_at": now().isoformat(),
                }
            )
            for index in (1, 2)
        )
        if receipt_result_class == "content_acquired"
        else ()
    )

    first_round = RecoveryRound(
        round_index=1,
        gap_id=gap_id,
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id=f"{strategy_prefix}-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value=strategy_values[0],
            ),
        ),
        source_receipts=(receipts[0],),
        source_versions=(
            (source_versions[0],) if source_versions else ()
        ),
        information_gain=InformationGain(),
    )
    second_round = RecoveryRound(
        round_index=2,
        gap_id=gap_id,
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id=f"{strategy_prefix}-2",
                kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
                value=strategy_values[1],
            ),
        ),
        source_receipts=(receipts[1],),
        source_versions=(
            (source_versions[1],) if source_versions else ()
        ),
        information_gain=InformationGain(),
    )
    history = RecoveryHistory(gap_id=gap_id).add_round(first_round).add_round(second_round)
    alternative_paths = AlternativePathAudit(
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id=f"{strategy_prefix}-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value=strategy_values[0],
            ),
            RecoveryStrategyUnit(
                strategy_unit_id=f"{strategy_prefix}-2",
                kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
                value=strategy_values[1],
            ),
        ),
        source_receipts=receipts,
        source_versions=source_versions,
        policy=policy,
    )
    return RecoveryExhaustionProof(
        alternative_paths=alternative_paths,
        recovery_history=history,
    )


def technical_retry_audit(
    gap_id: str,
    *,
    entity_id: str = "trial-1",
    terminal_result_class: str = "rate_limited",
    terminal_error_class: str | None = "接口限流",
) -> SamePathRetryAudit:
    from ci_workflow.sources.retries import RecoveryPolicy

    policy = RecoveryPolicy.from_yaml(ROOT / "policies" / "recovery" / "source-strategies-v1.yaml")
    start = now() + timedelta(minutes=10)
    receipts: list[SourceReceipt] = []
    for attempt in (1, 2, 3):
        ended = start + timedelta(seconds=1)
        is_terminal = attempt == 3
        payload = {
            "schema_version": "1.0",
            "receipt_id": f"retry-{gap_id}-{attempt}",
            "route_id": "clinicaltrials-global-baseline",
            "strategy_unit_id": "registry-nct-id",
            "entity_id": entity_id,
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
            "result_class": (
                terminal_result_class if is_terminal else "rate_limited"
            ),
            "error_class": (
                terminal_error_class if is_terminal else "接口限流"
            ),
            "source_version_id": (
                "sv-terminal"
                if is_terminal and terminal_result_class == "content_acquired"
                else None
            ),
            "content_sha256": (
                "b" * 64
                if is_terminal and terminal_result_class == "content_acquired"
                else None
            ),
            "completeness_checks": ("已核对返回内容",),
            "alternative_paths": ("下一条恢复策略",),
            "diagnostic_confidence": "medium",
            "parent_attempt_id": "recovery-root",
            "recovery_round": 1,
        }
        receipts.append(SourceReceipt.model_validate(payload))
        start = ended + timedelta(seconds=1)
    return SamePathRetryAudit(receipts=tuple(receipts), policy=policy)


def technical_alternative_audit(
    gap_id: str,
    *,
    entity_id: str = "trial-1",
) -> AlternativePathAudit:
    from ci_workflow.sources.retries import RecoveryPolicy

    policy = RecoveryPolicy.from_yaml(ROOT / "policies" / "recovery" / "source-strategies-v1.yaml")
    receipts = _receipts_for(
        gap_id,
        receipt_result_class="rate_limited",
        error_class="接口限流",
        route_id="clinicaltrials-global-baseline",
        entity_id=entity_id,
        access_methods=("公开来源检索", "公开来源检索"),
    )
    return AlternativePathAudit(
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="round-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value="药物研发代号",
            ),
            RecoveryStrategyUnit(
                strategy_unit_id="round-2",
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
    associated_entity_ids: tuple[str, ...] | None = None,
    entity_id: str | None = None,
    gate_spec_id: str = "gate-spec-a-v1",
    field_id: str | None = None,
    route_ids: tuple[str, ...] | None = None,
    sci_receipt_result_class: str = "not_found",
    sci_receipt_error_class: str | None = "未找到适格内容",
    tech_terminal_result_class: str = "rate_limited",
    tech_terminal_error_class: str | None = "接口限流",
    duplicate_route: bool = False,
) -> GapDoubleExhaustion:
    """构造双重穷尽缺口；科学缺口绑定逐路线饱和证明，技术缺口绑定技术证据。

    每条适用路线都必须恰有一个已验证的 route evidence：
    - 技术缺口：每条路线必须访问阻断，回执来自本路线重试/替代审计；
    - 科学缺口：每条路线恰有一份 recovery proof。
    复核输入摘要由缺口内容纯函数计算，复核结论精确绑定该摘要；
    Phase2 EvidenceGap 锚点与缺口身份/候选路线/信息增益/已完成策略精确一致。
    """
    resolved_entity = entity_id or (
        "trial-1" if object_type == "product" else object_id
    )
    resolved_associated = (
        associated_entity_ids
        if associated_entity_ids is not None
        else (("trial-1",) if object_type == "product" else ())
    )
    resolved_routes = route_ids or ("clinicaltrials-global-baseline",)
    is_technical = technical or current_state == "unresolved_due_to_route"

    diagnosis = None
    same_path_retry = None
    alternative_path = None
    proofs: tuple[RecoveryExhaustionProof, ...] = ()
    route_evidence_list: list[GapRouteEvidence] = []
    review_conclusion = omission_conclusion
    completed_strategies: set[str] = set()
    if is_technical:
        diagnosis = technical_diagnosis(gap_id, reviewer_role_id=reviewer_role_id)
        same_path_retry = technical_retry_audit(
            gap_id,
            entity_id=resolved_entity,
            terminal_result_class=tech_terminal_result_class,
            terminal_error_class=tech_terminal_error_class,
        )
        alternative_path = technical_alternative_audit(gap_id, entity_id=resolved_entity)
        current_state = "unresolved_due_to_route"
        review_conclusion = (
            review_conclusion
            or OmissionReviewConclusion.TECHNICAL_ACCESS_UNRESOLVED
        )
        tech_receipts = (
            *same_path_retry.receipts,
            *alternative_path.source_receipts,
        )
        for route_id in resolved_routes:
            route_receipts = tuple(
                receipt for receipt in tech_receipts
                if receipt.route_id == route_id
            )
            if not route_receipts:
                raise ValueError(
                    f"技术路线 {route_id} 缺少本路线重试/替代回执（假证据拒绝）"
                )
            route_evidence_list.append(
                GapRouteEvidence(
                    route_id=route_id,
                    route_name_zh="全球临床试验登记库",
                    completion="route_access_blocked",
                    final_result_class="rate_limited",
                    attempt_count=len(route_receipts),
                    receipt_ids=tuple(
                        sorted(r.receipt_id for r in route_receipts)
                    ),
                    access_methods=tuple(
                        sorted({r.access_method for r in route_receipts})
                    ),
                )
            )
        completed_strategies.update(
            receipt.strategy_unit_id for receipt in tech_receipts
        )
    else:
        for index, route_id in enumerate(resolved_routes):
            prefix = f"route{index + 1}"
            proof = saturated_exhaustion_proof(
                gap_id,
                entity_id=resolved_entity,
                route_id=route_id,
                receipt_prefix=f"receipt-{prefix}",
                strategy_prefix=f"{prefix}-round",
                strategy_values=(
                    f"路线{index + 1}别名核对",
                    f"路线{index + 1}标识交叉核对",
                ),
                receipt_result_class=sci_receipt_result_class,
                error_class=sci_receipt_error_class,
            )
            proofs = (*proofs, proof)
            route_receipts = _proof_receipts_flat(proof)
            route_evidence_list.append(
                GapRouteEvidence(
                    route_id=route_id,
                    route_name_zh=(
                        "全球临床试验登记库"
                        if index == 0
                        else "监管审评信息库"
                    ),
                    completion=route_completion,
                    final_result_class=final_result_class,
                    attempt_count=len(route_receipts),
                    receipt_ids=tuple(
                        sorted(r.receipt_id for r in route_receipts)
                    ),
                    access_methods=tuple(
                        sorted({r.access_method for r in route_receipts})
                    ),
                )
            )
        for proof in proofs:
            completed_strategies.update(proof.completed_strategy_unit_ids)
        review_conclusion = (
            review_conclusion or OmissionReviewConclusion.NO_MATERIAL_OMISSION
        )

    if duplicate_route and route_evidence_list:
        route_evidence_list.append(
            GapRouteEvidence(
                route_id=route_evidence_list[0].route_id,
                route_name_zh=route_evidence_list[0].route_name_zh,
                completion=route_evidence_list[0].completion,
                final_result_class=route_evidence_list[0].final_result_class,
                attempt_count=99,
                receipt_ids=("phantom-receipt",),
                access_methods=("伪造访问",),
            )
        )
    rounds = (
        information_gain_rounds
        if information_gain_rounds is not None
        else (info_gain_diff(1), info_gain_diff(2))
    )
    evidence_gap = EvidenceGap(
        schema_version="1.0",
        gap_id=gap_id,
        gate_spec_id=gate_spec_id,
        object_type=object_type,
        object_id=object_id,
        field_id=field_id or gate_unit_id,
        current_state=current_state,
        required_context="该字段缺少合格来源证据，需逐路线穷尽核对",
        candidate_sources=tuple(sorted(resolved_routes)),
        completed_strategies=tuple(sorted(completed_strategies)),
        information_gain_diff=rounds,
        next_legal_action="补充材料后重新运行本报告的证据核对",
    )
    reviewed_digest = compute_reviewer_inputs_digest_from_parts(
        gap_id=gap_id,
        gate_unit_id=gate_unit_id,
        object_type=object_type,
        object_id=object_id,
        current_state=current_state,
        applicable_route_ids=tuple(sorted(resolved_routes)),
        route_evidence=tuple(route_evidence_list),
        recovery_exhaustion_proofs=proofs,
        same_path_retry_audit=same_path_retry,
        alternative_path_audit=alternative_path,
        information_gain_rounds=rounds,
        associated_entity_ids=resolved_associated,
        evidence_gap=evidence_gap,
    )
    review = omission_review(
        gap_id,
        conclusion=review_conclusion,
        reviewer_role_id=reviewer_role_id,
        reviewed_inputs_digest=reviewed_digest,
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
        applicable_route_ids=tuple(sorted(resolved_routes)),
        route_evidence=tuple(route_evidence_list),
        recovery_exhaustion_proofs=proofs,
        same_path_retry_audit=same_path_retry,
        alternative_path_audit=alternative_path,
        omission_review=review,
        technical_diagnosis=diagnosis,
        information_gain_rounds=rounds,
        associated_entity_ids=resolved_associated,
        evidence_gap=evidence_gap,
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


def _proof_receipts_flat(proof: RecoveryExhaustionProof) -> tuple[SourceReceipt, ...]:
    by_id: dict[str, SourceReceipt] = {}
    for round_ in proof.recovery_history.rounds:
        for receipt in round_.source_receipts:
            by_id.setdefault(receipt.receipt_id, receipt)
    for receipt in proof.alternative_paths.source_receipts:
        by_id.setdefault(receipt.receipt_id, receipt)
    for audit in proof.same_path_retries:
        for receipt in audit.receipts:
            by_id.setdefault(receipt.receipt_id, receipt)
    return tuple(by_id.values())


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
    blocked_unit_ids: tuple[str, ...] | None = None,
) -> tuple[GateEvidenceBinding, ...]:
    """为报告构造非空候选绑定：除阻断单元外全部关键单元均有合格证据。"""
    excluded = (
        {blocked_unit_id} if blocked_unit_id is not None else set(blocked_unit_ids or ())
    )
    bindings: list[GateEvidenceBinding] = []
    for unit in spec.units:
        if unit.blocking_level is not GateBlockingLevel.CRITICAL:
            continue
        if unit.unit_id in excluded:
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


def _make_record(
    report_kind: ReportKind,
    failed_units: tuple[FailedGateUnit, ...],
    *,
    technical: bool = False,
    gap_states: dict[str, str] | None = None,
) -> DoubleExhaustionRecord:
    resolved_states = gap_states or {}
    return DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=tuple(
            gap_exhaustion(
                gap_id=f"gap-{index}",
                gate_unit_id=unit.unit_id,
                object_id=unit.object_id,
                object_type=unit.object_type,
                current_state=resolved_states.get(
                    unit.unit_id, unit.current_state
                ),
                technical=(
                    technical
                    or resolved_states.get(unit.unit_id)
                    == "unresolved_due_to_route"
                ),
                gate_spec_id=f"gate-spec-{report_kind.value.lower()}-v1",
                field_id=unit.field_ids[0],
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
    """经唯一公共原子入口构建（不写盘，供测试读取与打包断言）。"""
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


def public_write_blocker_package(
    *,
    report_kind: ReportKind,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot | None,
    gate_result: ReportGateResult | None,
    failed_units: tuple[FailedGateUnit, ...],
    record: DoubleExhaustionRecord,
    workspace_root: Path,
    empty_universe: EmptyUniverseKind | None = None,
    empty_evidence: EmptyUniverseEvidence | None = None,
    empty_justification_zh: str | None = None,
    user_help_needed: bool = False,
    user_input_directory: str | None = None,
    minimal_user_action_zh: str = "无需用户操作。",
    created_at: datetime | None = None,
) -> tuple[Path, Path]:
    """唯一公共原子发布入口：所有写盘用例的正式验收路径。"""
    from ci_workflow.gates.blocker_audit import build_and_write_blocker_package

    return build_and_write_blocker_package(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        contract_version="1",
        report_version="v1",
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed_units,
        exhaustion=record,
        empty_universe=empty_universe,
        empty_evidence=empty_evidence,
        empty_justification_zh=empty_justification_zh,
        residual_uncertainty_zh="部分来源可能需要再次核对。",
        user_help_needed=user_help_needed,
        user_input_directory=user_input_directory,
        minimal_user_action_zh=minimal_user_action_zh,
        source_links=("https://clinicaltrials.gov/study/NCT01234567",),
        resume_instruction_zh="补充材料后请重新运行本报告的证据核对。",
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
        created_at=created_at,
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


# 各模型的计算摘要键（按所在模型判定）：BlockerAudit 顶层只有 audit_digest；
# empty_evidence 顶层 evidence_digest；其 exhaustion 及其嵌套缺口/复核/诊断为计算键；
# per_gap_audits.gap_digest 是真实存储字段，不得剥离。
_COMPUTED_BY_PARENT = {
    (): frozenset({"audit_digest"}),
    ("empty_evidence",): frozenset(
        {"evidence_digest", "universe_closure_digest"}
    ),
    ("empty_evidence", "exhaustion"): frozenset({"record_digest"}),
    ("empty_evidence", "exhaustion", "gaps", "<item>"): frozenset(
        {"gap_digest", "reviewer_inputs_digest"}
    ),
    ("empty_evidence", "exhaustion", "gaps", "<item>", "omission_review"): frozenset(
        {"conclusion_digest"}
    ),
    (
        "empty_evidence",
        "exhaustion",
        "gaps",
        "<item>",
        "technical_diagnosis",
    ): frozenset({"diagnosis_digest"}),
    (
        "empty_evidence",
        "exhaustion",
        "gaps",
        "<item>",
        "same_path_retry_audit",
    ): frozenset(),
    (
        "empty_evidence",
        "exhaustion",
        "gaps",
        "<item>",
        "alternative_path_audit",
    ): frozenset(),
}


def _strip_computed(node: object, path: tuple[str, ...] = ()) -> object:
    """按模型位置剔除计算字段后供 Pydantic 重读（写出的 JSON 含计算摘要）。"""
    if isinstance(node, dict):
        computed = _COMPUTED_BY_PARENT.get(path, frozenset())
        out: dict[str, object] = {}
        for key, value in node.items():
            if key in computed:
                continue
            out[key] = _strip_computed(value, (*path, key))
        return out
    if isinstance(node, list):
        return [
            _strip_computed(item, (*path, "<item>"))
            for item in node
        ]
    return node


def load_audit_json(path: Path) -> BlockerAudit:
    """读取写出的 audit.json（剥离计算摘要后重验证）。"""
    import json as _json

    payload = _strip_computed(_json.loads(path.read_text(encoding="utf-8")))
    return BlockerAudit.model_validate(payload)


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
    candidate_product_ids: tuple[str, ...],
    candidate_trial_ids: tuple[str, ...] = (),
    excluded_product_ids: tuple[str, ...] | None = None,
    excluded_trial_ids: tuple[str, ...] | None = None,
    search_scope_id: str | None = None,
    exclusion_receipt: str = "资格检索回执：已按资格规则逐项核对并排除",
    gate_spec_id: str | None = None,
    field_id: str | None = None,
    gap_object_id: str | None = None,
    extra_gap: GapDoubleExhaustion | None = None,
) -> EmptyUniverseEvidence:
    spec = spec_yaml(report_kind.value)
    kind = {
        ReportKind.A: EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
        ReportKind.B: EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
        ReportKind.C: EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL,
    }[report_kind]
    scope = search_scope_id or f"scope-{report_kind.value}-1"
    gap_object = gap_object_id or scope
    record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=(
            gap_exhaustion(
                gap_id="gap-eligibility",
                gate_unit_id=kind.eligibility_gate_unit_id(),
                object_id=gap_object,
                object_type="product",
                current_state="not_publicly_disclosed",
                entity_id=gap_object,
                associated_entity_ids=(),
                gate_spec_id=gate_spec_id or spec.spec_id,
                field_id=field_id or kind.eligibility_gate_unit_id(),
            ),
            *((extra_gap,) if extra_gap is not None else ()),
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
        discovery_summary=compute_empty_universe_discovery_summary(
            EmptyUniverseEvidence.model_construct(
                report_kind=report_kind,
                candidate_product_ids=candidate_product_ids,
                candidate_trial_ids=candidate_trial_ids,
                eligible_product_ids=(),
                eligible_trial_ids=(),
            )
        ),
        candidate_product_ids=candidate_product_ids,
        eligible_product_ids=(),
        excluded_product_ids=(
            excluded_product_ids
            if excluded_product_ids is not None
            else candidate_product_ids
        ),
        candidate_trial_ids=candidate_trial_ids,
        eligible_trial_ids=(),
        excluded_trial_ids=(
            excluded_trial_ids
            if excluded_trial_ids is not None
            else candidate_trial_ids
        ),
        search_scope_id=scope,
        exclusion_receipt_summary=(exclusion_receipt,),
        exclusion_receipt_ids=tuple(
            sorted(
                {
                    receipt.receipt_id
                    for receipt in record.gaps[0]._all_receipts()
                }
            )
        ),
        exhaustion=record,
        created_at=now(),
    )


EMPTY_CASES = (
    (
        ReportKind.A,
        EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
        "本轮未识别出符合条件的创新产品（适格创新药产品为空），故产品格局报告无法开展。",
        (),
        (),
    ),
    (
        ReportKind.B,
        EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
        "本项目没有达到最低结果报告要求的适格试验，故临床证据报告无法开展。",
        ("product-a",),
        ("trial-1",),
    ),
    (
        ReportKind.C,
        EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL,
        "本项目没有达到核心设计最低门槛的适格试验，故试验设计报告无法开展。",
        ("product-a",),
        ("trial-1",),
    ),
)


@pytest.mark.parametrize(
    ("report_kind", "kind", "justification", "products", "trials"),
    EMPTY_CASES,
    ids=lambda value: value.value if isinstance(value, EmptyUniverseKind) else value,
)
def test_empty_no_eligible_case_writes_only_blocker_package(
    report_kind: ReportKind,
    kind: EmptyUniverseKind,
    justification: str,
    products: tuple[str, ...],
    trials: tuple[str, ...],
    tmp_path: Path,
) -> None:
    """空/无适格对象场景（真实 EmptyUniverseEvidence，gate_result=None）只生成阻断包。

    影响产品/试验分别派生：B/C 的 candidate_trial_ids 绝不冒充 impacted_products。
    """
    spec = spec_yaml(report_kind.value)
    snapshot = None if report_kind is ReportKind.A else snapshot_for(report_kind)
    evidence = empty_evidence_for(
        report_kind,
        candidate_product_ids=products,
        candidate_trial_ids=trials,
    )

    workspace_root = prepare_workspace(tmp_path)
    json_path, md_path = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=None,
        failed_units=(),
        record=evidence.exhaustion,
        workspace_root=workspace_root,
        empty_universe=kind,
        empty_evidence=evidence,
        empty_justification_zh=justification,
        user_help_needed=False,
        user_input_directory=None,
    )
    assert json_path.exists() and md_path.exists()
    audit = load_audit_json(json_path)
    assert audit.empty_universe is kind
    assert audit.failed_units == ()
    assert audit.empty_evidence is not None
    assert audit.gate_result_key is None
    # 影响对象分别派生，绝不混写
    assert audit.impacted_products == tuple(sorted(products))
    assert audit.impacted_trials == tuple(sorted(trials))

    markdown = render_audit_markdown_zh(audit)
    assert justification in markdown
    assert "不存在符合条件的对象" in markdown  # 空宇宙不得误报为"来源未披露"
    assert "来源未披露或尚未公开" not in markdown
    assert "目前不需要您提供材料" in markdown

    assert_no_downstream_artifacts(
        workspace_root,
        project_id=audit.project_id,
        report_kind=report_kind,
        report_version=audit.report_version,
    )
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

    # 适格集合非空 → 拒绝（A 适格产品；B/C 适格试验）
    if report_kind is ReportKind.A:
        with pytest.raises(ValueError):
            EmptyUniverseEvidence.model_validate(
                {
                    **empty_evidence_for(
                        report_kind, candidate_product_ids=()
                    ).model_dump(mode="json", exclude={"evidence_digest"}),
                    "eligible_product_ids": ("product-1",),
                }
            )
    else:
        with pytest.raises(ValidationError):
            EmptyUniverseEvidence.model_validate(
                {
                    **empty_evidence_for(
                        report_kind,
                        candidate_product_ids=("product-a",),
                        candidate_trial_ids=("trial-1",),
                    ).model_dump(mode="json", exclude={"evidence_digest"}),
                    "eligible_trial_ids": ("trial-1",),
                }
            )
    # 跨项目 → 拒绝
    evidence = empty_evidence_for(report_kind, candidate_product_ids=())
    with pytest.raises(ValidationError):
        EmptyUniverseEvidence.model_validate(
            {
                **evidence.model_dump(mode="json", exclude={"evidence_digest"}),
                "project_id": "project-other",
            }
        )
    # 跨报告类型 → 拒绝
    other_kind = ReportKind.B if report_kind is ReportKind.A else ReportKind.A
    with pytest.raises(ValidationError):
        EmptyUniverseEvidence.model_validate(
            {
                **evidence.model_dump(mode="json", exclude={"evidence_digest"}),
                "report_kind": other_kind.value,
            }
        )


def test_a_empty_represents_truly_zero_products() -> None:
    """A 空路径必须能表示真正 0 个产品，不依赖 Task3.1 snapshot 的产品下限。"""
    evidence = empty_evidence_for(
        ReportKind.A,
        candidate_product_ids=(),
        candidate_trial_ids=(),
        exclusion_receipt="资格检索回执：未发现任何候选创新产品",
    )
    assert evidence.candidate_product_ids == ()
    assert evidence.candidate_trial_ids == ()
    assert evidence.eligible_product_ids == ()
    assert evidence.eligible_trial_ids == ()
    assert evidence.evidence_digest
    assert evidence.search_scope_id is not None


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
    """真实评估证明：非空候选只缺该适用关键单元，经公共入口仅生成阻断包。"""
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

    failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in sorted(blocked_pairs)
    )
    record = _make_record(report_kind, failed)
    workspace_root = prepare_workspace(tmp_path)
    json_path, md_path = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=record,
        workspace_root=workspace_root,
    )
    audit = load_audit_json(json_path)
    assert audit.empty_universe is None
    assert audit.gate_result_key == gate_result.result_key
    assert {unit.unit_id for unit in audit.failed_units} == {unit_id}
    assert audit.failed_units
    assert md_path.exists()
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=audit.project_id,
        report_kind=report_kind,
        report_version=audit.report_version,
    )
    assert (workspace_root / "reports" / report_kind.value / "v1").exists() is False


# ─── 门槛结果/宇宙强绑定与调包反例（全部经公共入口） ──────────────────────────


def test_gate_spec_and_snapshot_are_mechanically_bound(tmp_path: Path) -> None:
    """GateSpec 身份与项目宇宙必须机械绑定：错误 spec id、同版本异指纹、跨项目拒绝。"""
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

    # 正确绑定 → 通过
    audit = routed_audit(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        exhausted=record,
    )
    assert audit.spec_fingerprint == spec.spec_fingerprint
    assert audit.rule_spec_id == spec.spec_id

    def expect_reject(**overrides: object) -> None:
        import pytest as _pytest

        kwargs: dict[str, object] = {
            "report_kind": report_kind,
            "spec": spec,
            "snapshot": snapshot,
            "gate_result": gate_result,
            "failed_units": failed,
            "record": record,
            "workspace_root": workspace_root,
        }
        kwargs.update(overrides)
        with _pytest.raises(ValueError):
            public_write_blocker_package(**kwargs)  # type: ignore[arg-type]

    # 错误 spec id → 拒绝
    forged_spec = spec.model_copy(update={"spec_id": "gate-spec-forged"})
    expect_reject(spec=forged_spec)

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
    expect_reject(spec=altered_spec)

    # 跨项目快照 → 拒绝
    other_snapshot = _snapshot(project_id="project-other")
    expect_reject(snapshot=other_snapshot)
    assert (workspace_root / "blockers").exists() is False


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
    for gap in audit.per_gap_audits:
        assert gap.gap_digest in gap_digests
        assert gap.route_summaries


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


def test_omission_conclusion_must_match_gap_type() -> None:
    """不相容的遗漏结论在终态缺口模型入口即失败，不等到写包阶段。"""
    for conclusion in (
        OmissionReviewConclusion.TECHNICAL_ACCESS_UNRESOLVED,
        OmissionReviewConclusion.MATERIAL_OMISSION_FOUND,
    ):
        with pytest.raises(ValueError):
            gap_exhaustion(
                gap_id=f"gap-invalid-{conclusion.value}",
                current_state="not_reported",
                omission_conclusion=conclusion,
            )


def test_mixed_gaps_via_full_production_path(tmp_path: Path) -> None:
    """真实 B 评估同时阻断科学缺失与技术访问：公共入口写包、Schema 通过、零下游、
    Markdown 分别说明两类状态。"""
    import json as jsonlib

    from jsonschema import Draft202012Validator

    report_kind = ReportKind.B
    spec = spec_yaml("B")
    snapshot = snapshot_for(report_kind)
    units = applicable_critical_units(spec, snapshot)
    candidates: list[tuple[str, str]] = []
    for unit_id in units:
        unit = next(x for x in spec.units if x.unit_id == unit_id)
        if not unit.required_context_fields:
            continue
        for object_id in unit_object_ids(spec, snapshot, unit_id):
            candidates.append((unit_id, object_id))
    science_unit, science_object = candidates[0]
    tech_unit, tech_object = next(
        (u, o)
        for u, o in candidates[1:]
        if u != science_unit and o != science_object
    )

    # 真实评估：同时缺两个关键单元
    gate_result = evaluate_report(
        spec,
        snapshot,
        satisfying_bindings_for(
            spec,
            snapshot,
            blocked_unit_ids=(science_unit, tech_unit),
        ),
        contract_version="1",
    )
    assert gate_result.decision is ReportDecision.BLOCKED
    blocked = {
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    }
    assert (science_unit, science_object) in blocked
    assert (tech_unit, tech_object) in blocked

    blocked_sorted = sorted(blocked)
    failed = tuple(
        failed_gate_unit(
            spec,
            unit_id,
            object_id,
            current_state=(
                "not_reported"
                if unit_id == science_unit
                else "unresolved_due_to_route"
            ),
        )
        for unit_id, object_id in blocked_sorted
    )
    gaps = []
    for index, (unit_id, object_id) in enumerate(blocked_sorted, start=1):
        unit = next(x for x in spec.units if x.unit_id == unit_id)
        resolved_field = (
            unit.required_context_fields[0].value
            if unit.required_context_fields
            else unit.user_label_zh
        )
        if unit_id == science_unit:
            gaps.append(
                gap_exhaustion(
                    gap_id=f"gap-{index}",
                    gate_unit_id=unit_id,
                    object_id=object_id,
                    object_type=unit.object_type.value,
                    current_state="not_reported",
                    gate_spec_id="gate-spec-b-v1",
                    field_id=resolved_field,
                    information_gain_rounds=(
                        info_gain_diff(1),
                        info_gain_diff(2),
                    ),
                )
            )
        else:
            gaps.append(
                gap_exhaustion(
                    gap_id=f"gap-{index}",
                    gate_unit_id=unit_id,
                    object_id=object_id,
                    object_type=unit.object_type.value,
                    current_state="unresolved_due_to_route",
                    technical=True,
                    gate_spec_id="gate-spec-b-v1",
                    field_id=resolved_field,
                    information_gain_rounds=(
                        info_gain_diff(1),
                        info_gain_diff(2),
                    ),
                )
            )
    record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=tuple(gaps),
        created_at=now(),
    )
    workspace_root = prepare_workspace(tmp_path)
    json_path, md_path = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=record,
        workspace_root=workspace_root,
    )
    # Schema 通过
    schema = jsonlib.loads(
        (ROOT / "schemas" / "blocker-audit.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    payload = jsonlib.loads(json_path.read_text(encoding="utf-8"))
    assert list(validator.iter_errors(payload)) == []
    # 零下游
    assert_no_downstream_artifacts(
        workspace_root,
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        report_version="v1",
    )
    # Markdown 分别说明科学未列示与技术访问
    markdown = md_path.read_text(encoding="utf-8")
    assert "已核查的公开材料未列示该字段" in markdown
    assert "访问问题尚未解决，不能判断是否公开" in markdown
    assert "技术诊断" in markdown
    # 路线按中文名汇总为一行（同一路线累计尝试数）
    route_lines = [
        line for line in markdown.splitlines() if "累计完成" in line
    ]
    assert len(route_lines) == 1, f"同一路线应汇总为一行：{route_lines}"
    total_attempts = sum(
        2 if unit_id == science_unit else 5
        for unit_id, _ in blocked_sorted
    )
    assert f"累计完成 {total_attempts} 次尝试" in route_lines[0]


# ─── 第四轮加固：Schema、幂等、路径、公共入口不可绕过 ─────────────────────────


def _schema_validator():
    import json as jsonlib

    from jsonschema import Draft202012Validator

    schema = jsonlib.loads(
        (ROOT / "schemas" / "blocker-audit.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_blocker_audit_json_validates_against_schema(tmp_path: Path) -> None:
    """audit.json 必须通过 blocker-audit.schema.json（A/B/C 空与非空，外加混合缺口）。"""
    import json as jsonlib

    validator = _schema_validator()
    for report_kind in (ReportKind.A, ReportKind.B, ReportKind.C):
        # 非空
        unit_id = applicable_critical_units(
            spec_yaml(report_kind.value), snapshot_for(report_kind)
        )[0]
        workspace_root = prepare_workspace(tmp_path / f"{report_kind.value}-nonempty")
        audit = real_blocked_audit(report_kind, unit_id)
        from ci_workflow.gates.blocker_audit import _write_blocker_package

        json_path, _ = _write_blocker_package(
            audit,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
        errors = list(validator.iter_errors(jsonlib.loads(json_path.read_text())))
        assert errors == [], f"{report_kind.value} 非空: {errors}"
        # 空场景
        workspace_root = prepare_workspace(tmp_path / f"{report_kind.value}-empty")
        evidence = empty_evidence_for(
            report_kind,
            candidate_product_ids=(
                ()
                if report_kind is ReportKind.A
                else ("product-a",)
            ),
            candidate_trial_ids=(
                ()
                if report_kind is ReportKind.A
                else ("trial-1",)
            ),
        )
        json_path, _ = public_write_blocker_package(
            report_kind=report_kind,
            spec=spec_yaml(report_kind.value),
            snapshot=(
                None
                if report_kind is ReportKind.A
                else snapshot_for(report_kind)
            ),
            gate_result=None,
            failed_units=(),
            record=evidence.exhaustion,
            workspace_root=workspace_root,
            empty_universe={
                ReportKind.A: EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
                ReportKind.B: EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
                ReportKind.C: EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL,
            }[report_kind],
            empty_evidence=evidence,
            empty_justification_zh="本轮未识别出符合条件的对象。",
        )
        errors = list(validator.iter_errors(jsonlib.loads(json_path.read_text())))
        assert errors == [], f"{report_kind.value} 空: {errors}"


def test_schema_negative_cases(tmp_path: Path) -> None:
    """Schema 关键负例：空路径携带字符串键、非空路径键为 null、穷尽记录缺字段/多字段。"""
    from ci_workflow.gates.blocker_audit import _audit_content_dump

    validator = _schema_validator()
    report_kind = ReportKind.A
    unit_id = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[0]
    audit = real_blocked_audit(report_kind, unit_id)
    dump = _audit_content_dump(audit)

    # 空路径 + 字符串键 → 拒绝
    empty_dump = dict(dump)
    empty_dump["empty_universe"] = "a_no_eligible_innovative_product"
    empty_dump["gate_result_key"] = "gate-result-fake"
    empty_dump["failed_units"] = []
    assert list(validator.iter_errors(empty_dump))

    # 非空路径 + null 键 → 拒绝
    nonempty_dump = dict(dump)
    nonempty_dump["gate_result_key"] = None
    assert list(validator.iter_errors(nonempty_dump))

    # 穷尽记录缺 gaps → 拒绝
    broken = dict(dump)
    del broken["empty_evidence"]
    broken["empty_universe"] = None
    broken["gate_result_key"] = "some-key"
    broken["failed_units"] = [dict(dump["failed_units"][0])]
    assert list(validator.iter_errors(broken))


def test_blocker_package_write_is_idempotent_and_drift_fails(tmp_path: Path) -> None:
    """公共入口同参重复调用幂等（created_at 未传，字节不变）；漂移拒绝覆盖。"""
    from ci_workflow.gates.blocker_audit import BlockerAuditDriftError

    report_kind = ReportKind.A
    unit_id = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[0]
    spec = spec_yaml("A")
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
    record = _make_record(report_kind, failed)
    workspace_root = prepare_workspace(tmp_path)

    json1, md1 = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=record,
        workspace_root=workspace_root,
    )
    first = json1.read_bytes()
    json2, md2 = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=record,
        workspace_root=workspace_root,
    )
    assert json1 == json2 and md1 == md2
    assert json2.read_bytes() == first

    # 同一审计身份下内容漂移 → 拒绝覆盖已接受审计历史
    other_unit = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[1]
    other_gate_result = real_blocked_result_for(spec, snapshot, other_unit)
    other_blocked = [
        (r.unit_id, r.object_id)
        for r in other_gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    other_failed = tuple(
        failed_gate_unit(spec, u, o, current_state="not_reported")
        for u, o in other_blocked
    )
    with pytest.raises(BlockerAuditDriftError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=other_gate_result,
            failed_units=other_failed,
            record=_make_record(report_kind, other_failed),
            workspace_root=workspace_root,
        )
    after = json1.read_bytes()
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
    spec = spec_yaml("A")
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
    workspace_root = prepare_workspace(tmp_path)
    public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=_make_record(report_kind, failed),
        workspace_root=workspace_root,
    )
    blocker_dir = workspace_root / blocker_directory(report_kind, "v1")

    (blocker_dir / "notes.txt").write_text("第三个文件", encoding="utf-8")
    with pytest.raises(BlockerPackageIntegrityError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=failed,
            record=_make_record(report_kind, failed),
            workspace_root=workspace_root,
        )
    (blocker_dir / "notes.txt").unlink()


def test_blocker_package_first_write_is_atomic_and_cleans_temp(tmp_path: Path) -> None:
    """首次发布在临时目录写齐两文件后原子 rename，不残留临时目录。"""
    report_kind = ReportKind.B
    unit_id = applicable_critical_units(
        spec_yaml("B"), snapshot_for(report_kind)
    )[0]
    spec = spec_yaml("B")
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
    workspace_root = prepare_workspace(tmp_path)
    public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=_make_record(report_kind, failed),
        workspace_root=workspace_root,
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
    spec = spec_yaml("A")
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
    workspace_root = prepare_workspace(tmp_path)
    blocker_dir = workspace_root / "blockers" / "A" / "v1"
    blocker_dir.parent.mkdir(parents=True)
    blocker_dir.write_text("不是目录", encoding="utf-8")
    with pytest.raises(BlockerPackageIntegrityError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=failed,
            record=_make_record(report_kind, failed),
            workspace_root=workspace_root,
        )


def test_blocker_directory_and_files_reject_symlinks(tmp_path: Path) -> None:
    """阻断包不得沿符号链接写出工作区或在恢复时信任链接文件。"""
    from ci_workflow.gates.blocker_audit import (
        BlockerPackageIntegrityError,
        validate_existing_blocker_package,
    )

    report_kind = ReportKind.A
    spec = spec_yaml("A")
    snapshot = snapshot_for(report_kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    gate_result = real_blocked_result_for(spec, snapshot, unit_id)
    failed = tuple(
        failed_gate_unit(spec, result.unit_id, result.object_id, current_state="not_reported")
        for result in gate_result.unit_results
        if result.outcome is GateUnitOutcome.BLOCKED
    )
    workspace_root = prepare_workspace(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    blocker_dir = workspace_root / "blockers" / "A" / "v1"
    blocker_dir.parent.mkdir(parents=True)
    blocker_dir.symlink_to(outside, target_is_directory=True)
    with pytest.raises(BlockerPackageIntegrityError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=failed,
            record=_make_record(report_kind, failed),
            workspace_root=workspace_root,
        )

    blocker_dir.unlink()
    json_path, _ = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=_make_record(report_kind, failed),
        workspace_root=workspace_root,
    )
    json_bytes = json_path.read_bytes()
    json_path.unlink()
    outside_json = outside / "audit.json"
    outside_json.write_bytes(json_bytes)
    json_path.symlink_to(outside_json)
    with pytest.raises(BlockerPackageIntegrityError):
        validate_existing_blocker_package(
            blocker_dir,
            project_id="project-test",
            report_kind=report_kind,
            report_version="v1",
        )


def test_source_links_reject_arbitrary_or_jumping_paths(tmp_path: Path) -> None:
    """来源链接只接受 http/https 原文或工作区相对附件路径。"""
    from pydantic import ValidationError

    from ci_workflow.gates.blocker_audit import BlockerAudit, _audit_content_dump

    report_kind = ReportKind.A
    unit_id = applicable_critical_units(
        spec_yaml("A"), snapshot_for(report_kind)
    )[0]
    audit = real_blocked_audit(report_kind, unit_id)

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


def test_public_entry_revalidates_forged_inputs(tmp_path: Path) -> None:
    """公共入口从原始内容完整重验证：model_copy 伪造角色/结果键/回执/中文显示字段
    全部在写前失败，磁盘无 blockers 目录。"""
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

    def attempt(mutated_record: DoubleExhaustionRecord) -> None:
        with pytest.raises(ValueError):
            public_write_blocker_package(
                report_kind=report_kind,
                spec=spec,
                snapshot=snapshot,
                gate_result=gate_result,
                failed_units=failed,
                record=mutated_record,
                workspace_root=workspace_root,
            )

    # 伪造执行者角色（model_copy 跳过校验）
    bad_role = record.gaps[0].model_copy(
        update={"executor_role": ExhaustionRole.REVIEWER}
    )
    attempt(record.model_copy(update={"gaps": (bad_role,)}))

    # 伪造结果键
    forged_result = gate_result.model_copy(update={"result_key": "forged-key"})
    with pytest.raises(ValueError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=forged_result,
            failed_units=failed,
            record=record,
            workspace_root=workspace_root,
        )

    # 伪造路线回执（从证明中剥离一条）
    forged_route = record.gaps[0].route_evidence[0].model_copy(
        update={"receipt_ids": ("receipt-alias-1",)}
    )
    bad_route = record.gaps[0].model_copy(
        update={"route_evidence": (forged_route,)}
    )
    attempt(record.model_copy(update={"gaps": (bad_route,)}))

    # 伪造中文显示字段（纯英文内部标识 → 公共边界中文语境校验拒绝）
    forged_unit = failed[0].model_copy(update={"object_name_zh": "API"})
    forged_failed = tuple(
        forged_unit if (u.unit_id, u.object_id) == blocked_pairs[0] else u
        for u in failed
    )
    with pytest.raises(ValueError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=forged_failed,
            record=record,
            workspace_root=workspace_root,
        )

    # 伪造 failed_units 超集 → 拒绝
    extra_failed = (*failed, failed_gate_unit(
        spec, "a_innovation_eligibility", "forged-object",
        current_state="not_reported",
    ))
    with pytest.raises(ValueError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=extra_failed,
            record=record,
            workspace_root=workspace_root,
        )

    # 空场景伪造 gate_result → 拒绝
    evidence = empty_evidence_for(report_kind, candidate_product_ids=())
    with pytest.raises(ValueError):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=(),
            record=evidence.exhaustion,
            workspace_root=workspace_root,
            empty_universe=EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
            empty_evidence=evidence,
            empty_justification_zh="本轮未识别出符合条件的创新产品。",
        )
    assert (workspace_root / "blockers").exists() is False


def test_empty_evidence_identity_and_record_are_bound(tmp_path: Path) -> None:
    """空证据规则身份与穷尽记录必须绑定：错 rule id/version、替换 exhaustion 拒绝。"""
    from ci_workflow.gates.blocker_audit import _strip_computed

    report_kind = ReportKind.A
    spec = spec_yaml("A")
    evidence = empty_evidence_for(report_kind, candidate_product_ids=())

    # 错 rule id（model_validate 调包）→ 公共入口拒绝
    forged_evidence = EmptyUniverseEvidence.model_validate(
        {
            **_strip_computed(evidence.model_dump(mode="json")),
            "eligibility_rule_spec_id": "gate-spec-forged",
        }
    )
    workspace_root = prepare_workspace(tmp_path)
    with pytest.raises(ValueError, match="资格规则说明书"):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=None,
            gate_result=None,
            failed_units=(),
            record=forged_evidence.exhaustion,
            workspace_root=workspace_root,
            empty_universe=EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
            empty_evidence=forged_evidence,
            empty_justification_zh="本轮未识别出符合条件的创新产品。",
        )

    # 替换穷尽记录（不同 digest）→ 拒绝
    other_record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=(gap_exhaustion(gap_id="gap-other"),),
        created_at=now(),
    )
    with pytest.raises(ValueError, match="摘要不一致|内容不一致"):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=None,
            gate_result=None,
            failed_units=(),
            record=other_record,
            workspace_root=workspace_root,
            empty_universe=EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
            empty_evidence=evidence,
            empty_justification_zh="本轮未识别出符合条件的创新产品。",
        )
    assert (workspace_root / "blockers").exists() is False


def test_five_markdown_variants_render_native_chinese(tmp_path: Path) -> None:
    """五类完整 Markdown（not_reported/not_publicly_disclosed/conflict/technical/
    mixed-or-empty）必须实际渲染并断言原生中文、无内部标签。"""
    report_kind = ReportKind.B
    spec = spec_yaml("B")
    snapshot = snapshot_for(report_kind)
    units = applicable_critical_units(spec, snapshot)
    target_unit = next(
        u for u in units
        if next(x for x in spec.units if x.unit_id == u).required_context_fields
    )
    gate_result = real_blocked_result_for(spec, snapshot, target_unit)
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]

    variants: list[tuple[str, str]] = []
    for state, expected_fragment in (
        ("not_reported", "已核查的公开材料未列示该字段"),
        ("not_publicly_disclosed", "来源明确未披露或尚未公开"),
        ("conflicting", "不同来源信息不一致"),
        ("unresolved_due_to_route", "访问问题尚未解决，不能判断是否公开"),
    ):
        failed = tuple(
            failed_gate_unit(spec, u, o, current_state=state)
            for u, o in blocked_pairs
        )
        record = _make_record(
            report_kind,
            failed,
            gap_states={target_unit: state},
        )
        workspace_root = prepare_workspace(tmp_path / state)
        json_path, md_path = public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot,
            gate_result=gate_result,
            failed_units=failed,
            record=record,
            workspace_root=workspace_root,
        )
        markdown = md_path.read_text(encoding="utf-8")
        assert expected_fragment in markdown, state
        variants.append((state, markdown))
        cjk = sum(1 for c in markdown if "\u4e00" <= c <= "\u9fff")
        assert cjk > 100, f"{state} 中文不足"
        from ci_workflow.gates.blocker_audit import assert_user_facing_zh_clean

        assert_user_facing_zh_clean(markdown)

    # 空场景（第五类）
    evidence = empty_evidence_for(
        report_kind,
        candidate_product_ids=("product-a",),
        candidate_trial_ids=("trial-1",),
    )
    workspace_root = prepare_workspace(tmp_path / "empty")
    json_path, md_path = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=None,
        failed_units=(),
        record=evidence.exhaustion,
        workspace_root=workspace_root,
        empty_universe=EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
        empty_evidence=evidence,
        empty_justification_zh="本项目没有达到最低结果报告要求的适格试验。",
    )
    markdown = md_path.read_text(encoding="utf-8")
    assert "不存在符合条件的对象" in markdown
    cjk = sum(1 for c in markdown if "\u4e00" <= c <= "\u9fff")
    assert cjk > 50
    from ci_workflow.gates.blocker_audit import assert_user_facing_zh_clean

    empty_audit = load_audit_json(json_path)
    assert empty_audit.empty_evidence is not None
    assert "本次资格检索范围" in json_path.read_text(encoding="utf-8")
    assert_user_facing_zh_clean(markdown)


def test_route_binding_rejects_mismatched_receipts_and_entities(tmp_path: Path) -> None:
    """逐路线绑定：回执缺失/多余、attempt 数不符、访问方式不符、跨实体、跨路线
    证明全部在模型层或公共入口失败。"""
    from pydantic import ValidationError

    # 回执与证明不一致（多一条伪造回执）→ 拒绝
    gap = gap_exhaustion(gap_id="gap-route-bind")
    mutated = gap.model_dump(mode="json")
    # 剔除计算字段后重验证
    mutated["route_evidence"][0]["receipt_ids"] = [
        *mutated["route_evidence"][0]["receipt_ids"],
        "receipt-forged-extra",
    ]
    mutated = _strip_computed_for_gap(mutated)
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)

    # attempt_count 自报与派生不符 → 拒绝
    gap = gap_exhaustion(gap_id="gap-route-attempt")
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["route_evidence"][0]["attempt_count"] = 99
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)

    # 访问方式与回执不符 → 拒绝
    gap = gap_exhaustion(gap_id="gap-route-access")
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["route_evidence"][0]["access_methods"] = ["API"]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)

    # 回执实体既非缺口对象也非声明关联实体 → 拒绝
    gap = gap_exhaustion(gap_id="gap-route-entity")
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["recovery_exhaustion_proofs"][0]["recovery_history"]["rounds"][0][
        "source_receipts"
    ][0]["entity_id"] = "trial-arbitrary"
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


def _strip_computed_for_gap(dump: dict) -> dict:
    computed = {
        "gap_digest",
        "reviewer_inputs_digest",
        "conclusion_digest",
        "diagnosis_digest",
        "record_digest",
        "evidence_digest",
    }

    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in computed}
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node

    return strip(dump)


def test_reviewer_inputs_digest_is_bound_and_stale_rejected(tmp_path: Path) -> None:
    """复核结论必须精确绑定其审阅的输入：错摘要、换路线后沿用旧结论均失败。"""
    from pydantic import ValidationError

    gap = gap_exhaustion(gap_id="gap-digest-bound")
    assert gap.omission_review.reviewed_inputs_digest == gap.reviewer_inputs_digest

    # 错摘要 → 拒绝
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["omission_review"]["reviewed_inputs_digest"] = "stale-digest"
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)

    # 换路线后沿用旧结论（摘要不再匹配）→ 拒绝
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["route_evidence"][0]["receipt_ids"] = ["receipt-changed"]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


def test_information_gain_rounds_align_with_history() -> None:
    """信息增益轮次必须与恢复历史逐轮对齐：自报有增益而历史无增益 → 拒绝。"""
    from pydantic import ValidationError

    # 饱和证明（历史两轮无增益）却声明有增益 → 拒绝
    gap = gap_exhaustion(gap_id="gap-gain-mismatch")
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["information_gain_rounds"][1]["new_fields"] = ["source-1"]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)

    # 轮数不齐 → 拒绝
    gap = gap_exhaustion(gap_id="gap-gain-count")
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["information_gain_rounds"] = mutated["information_gain_rounds"][:1]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


# ─── 第五轮：EvidenceGap 锚点、空宇宙闭合、逐路线绑定、公共路径覆盖 ──────────


def test_two_scientific_routes_positive_via_public_entry(tmp_path: Path) -> None:
    """两个真实科学路线正向：逐路线证明、公共入口写包、Schema 通过、零下游。"""
    import json as jsonlib

    from jsonschema import Draft202012Validator

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
    routes = (
        "clinicaltrials-global-baseline",
        "regulatory-review-baseline",
    )
    record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=tuple(
            gap_exhaustion(
                gap_id=f"gap-{i}",
                gate_unit_id=u,
                object_id=o,
                object_type=next(x for x in spec.units if x.unit_id == u).object_type.value,
                current_state="not_reported",
                gate_spec_id=spec.spec_id,
                field_id=next(x for x in spec.units if x.unit_id == u).user_label_zh,
                route_ids=routes,
            )
            for i, (u, o) in enumerate(blocked_pairs, start=1)
        ),
        created_at=now(),
    )
    gap = record.gaps[0]
    assert len(gap.applicable_route_ids) == 2
    assert len(gap.route_evidence) == 2
    assert len(gap.recovery_exhaustion_proofs) == 2
    assert len({p.execution_context[0] for p in gap.recovery_exhaustion_proofs}) == 2

    workspace_root = prepare_workspace(tmp_path)
    json_path, md_path = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed,
        record=record,
        workspace_root=workspace_root,
    )
    validator = Draft202012Validator(
        jsonlib.loads(
            (ROOT / "schemas" / "blocker-audit.schema.json").read_text(encoding="utf-8")
        )
    )
    payload = jsonlib.loads(json_path.read_text(encoding="utf-8"))
    assert list(validator.iter_errors(payload)) == []
    assert_no_downstream_artifacts(
        workspace_root,
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        report_version="v1",
    )
    # 路线按中文名汇总：两条不同路线应打印两行
    markdown = md_path.read_text(encoding="utf-8")
    route_lines = [
        line for line in markdown.splitlines() if "累计完成" in line
    ]
    assert len(route_lines) == 2, route_lines


def test_technical_extra_fake_route_rejected() -> None:
    """技术缺口第二条假路线（带任意回执）必须拒绝：当前合同只接受访问阻断路线。"""
    from pydantic import ValidationError

    technical = gap_exhaustion(
        gap_id="gap-tech-routes",
        current_state="unresolved_due_to_route",
        technical=True,
    )
    mutated = _strip_computed_for_gap(technical.model_dump(mode="json"))
    # 第二条假路线：无本路线回执、任意 attempt/access
    mutated["route_evidence"].append(
        {
            "route_id": "fake-route-2",
            "route_name_zh": "伪造路线",
            "completion": "route_access_blocked",
            "final_result_class": "rate_limited",
            "attempt_count": 99,
            "receipt_ids": ["fake-receipt"],
            "access_methods": ["伪造访问"],
        }
    )
    mutated["applicable_route_ids"] = [
        *mutated["applicable_route_ids"],
        "fake-route-2",
    ]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)

    # 技术缺口携带已完成科学路线 → 拒绝
    mutated = _strip_computed_for_gap(technical.model_dump(mode="json"))
    mutated["route_evidence"][0]["completion"] = "route_completed"
    mutated["route_evidence"][0]["final_result_class"] = "not_found"
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


def test_duplicate_science_proof_route_rejected() -> None:
    """同一科学证明不得重复贴到同一路线；proof route id 必须唯一。"""
    from pydantic import ValidationError

    gap = gap_exhaustion(gap_id="gap-dup-route")
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["recovery_exhaustion_proofs"].append(
        mutated["recovery_exhaustion_proofs"][0]
    )
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


def test_evidence_gap_tamper_rejected() -> None:
    """换旧 EvidenceGap、删候选路线、错字段/对象/状态、信息增益调包均失败。"""
    from pydantic import ValidationError

    gap = gap_exhaustion(gap_id="gap-evidence-anchor")
    # 旧证据缺口（不同 gap_id）→ 拒绝
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["evidence_gap"]["gap_id"] = "gap-stale"
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)
    # 错对象 → 拒绝
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["evidence_gap"]["object_id"] = "product-other"
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)
    # 错状态 → 拒绝
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["evidence_gap"]["current_state"] = "conflicting"
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)
    # 删候选路线（candidate_sources 少一条）→ 拒绝
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["evidence_gap"]["candidate_sources"] = []
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)
    # 信息增益调包 → 拒绝
    mutated = _strip_computed_for_gap(gap.model_dump(mode="json"))
    mutated["evidence_gap"]["information_gain_diff"][1]["new_fields"] = ["source-1"]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


def test_empty_candidate_undisposed_rejected() -> None:
    """候选对象必须全部处置（candidate == eligible ∪ excluded）：遗留未判定候选拒绝。"""
    from pydantic import ValidationError

    report_kind = ReportKind.B
    evidence = empty_evidence_for(
        report_kind,
        candidate_product_ids=("product-a",),
        candidate_trial_ids=("trial-1",),
    )
    mutated = _strip_computed(evidence.model_dump(mode="json"))
    # 多出一个未处置候选产品
    mutated["candidate_product_ids"] = ["product-a", "product-b"]
    with pytest.raises(ValidationError):
        EmptyUniverseEvidence.model_validate(mutated)
    # 适格与排除交叠 → 拒绝
    mutated = _strip_computed(evidence.model_dump(mode="json"))
    mutated["eligible_product_ids"] = ["product-a"]
    mutated["excluded_product_ids"] = ["product-a"]
    with pytest.raises(ValidationError):
        EmptyUniverseEvidence.model_validate(mutated)


def test_empty_receipt_missing_one_rejected() -> None:
    """exclusion_receipt_ids 少一条（未覆盖全部路线回执）→ 拒绝。"""
    from pydantic import ValidationError

    report_kind = ReportKind.A
    evidence = empty_evidence_for(report_kind, candidate_product_ids=())
    assert evidence.exclusion_receipt_ids
    mutated = _strip_computed(evidence.model_dump(mode="json"))
    mutated["exclusion_receipt_ids"] = list(mutated["exclusion_receipt_ids"][:-1])
    with pytest.raises(ValidationError):
        EmptyUniverseEvidence.model_validate(mutated)


def test_a_empty_rejects_nonempty_snapshot(tmp_path: Path) -> None:
    """A 无适格创新产品路径不得传 Task3.1 非空快照。"""
    report_kind = ReportKind.A
    spec = spec_yaml("A")
    evidence = empty_evidence_for(report_kind, candidate_product_ids=())
    workspace_root = prepare_workspace(tmp_path)
    with pytest.raises(ValueError, match="非空宇宙快照"):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=snapshot_for(report_kind),
            gate_result=None,
            failed_units=(),
            record=evidence.exhaustion,
            workspace_root=workspace_root,
            empty_universe=EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
            empty_evidence=evidence,
            empty_justification_zh="本轮未识别出符合条件的创新产品。",
        )
    assert (workspace_root / "blockers").exists() is False


def test_bc_empty_rejects_bare_subset_snapshot(tmp_path: Path) -> None:
    """B/C 空场景候选集合必须等于闭合快照：裸子集拒绝。"""
    report_kind = ReportKind.B
    spec = spec_yaml("B")
    evidence = empty_evidence_for(
        report_kind,
        candidate_product_ids=("product-a",),
        candidate_trial_ids=("trial-1",),
    )
    # 快照含额外试验 → 候选集合是裸子集 → 拒绝
    bigger_snapshot = _snapshot(
        product_ids=("product-a",),
        trial_ids=("trial-1", "trial-2"),
        comparison_ids=(),
        group_ids=(),
        endpoint_ids=(),
        timepoint_ids=(),
        relationship_edges=(
            edge_payload("product", "product-a", "trial", "trial-1"),
            edge_payload("product", "product-a", "trial", "trial-2"),
        ),
        trial_design_evidence=(
            design_record("trial-1", "single_arm"),
            design_record("trial-2", "single_arm"),
        ),
    )
    workspace_root = prepare_workspace(tmp_path)
    with pytest.raises(
        ValueError,
        match="候选产品必须与闭合宇宙产品完全一致|候选试验必须与闭合宇宙试验完全一致",
    ):
        public_write_blocker_package(
            report_kind=report_kind,
            spec=spec,
            snapshot=bigger_snapshot,
            gate_result=None,
            failed_units=(),
            record=evidence.exhaustion,
            workspace_root=workspace_root,
            empty_universe=EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
            empty_evidence=evidence,
            empty_justification_zh="本项目没有达到最低结果报告要求的适格试验。",
        )
    assert (workspace_root / "blockers").exists() is False


def test_pure_english_labels_rejected() -> None:
    """中文标签去豁免：纯英文专名（含 ClinicalTrials.gov）一律拒绝。"""
    from pydantic import ValidationError

    from ci_workflow.gates.exhaustion import GapRouteEvidence

    for bad_name in ("ClinicalTrials.gov", "API", "NCT01234567"):
        with pytest.raises(ValidationError):
            GapRouteEvidence(
                route_id="r1",
                route_name_zh=bad_name,
                completion="route_completed",
                final_result_class="not_found",
                attempt_count=1,
                receipt_ids=("x",),
                access_methods=("公开检索",),
            )
    with pytest.raises(ValidationError):
        GapRouteEvidence(
            route_id="r2",
            route_name_zh="ClinicalTrials.gov 登记页",
            completion="route_completed",
            final_result_class="not_found",
            attempt_count=1,
            receipt_ids=("x",),
            access_methods=("API",),  # 访问方式纯英文拒绝
        )
    # 中文句内保留 NCT 标识符 → 允许
    ok = GapRouteEvidence(
        route_id="r3",
        route_name_zh="临床试验登记库（NCT01234567）",
        completion="route_completed",
        final_result_class="not_found",
        attempt_count=1,
        receipt_ids=("x",),
        access_methods=("公开检索",),
    )
    assert ok.route_name_zh


# ─── 第六轮：重复路线拒绝、终端结果类别派生、空宇宙锚点与单缺口 ──────────────


def test_duplicate_route_summary_rejected() -> None:
    """同一适用路线只允许一条路线摘要：重复 route_id 行（含幻影回执/虚增次数）拒绝。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        gap_exhaustion(gap_id="gap-dup-row", duplicate_route=True)


def test_scientific_final_class_must_derive_from_receipts() -> None:
    """科学路线最终结果类别必须由实际回执终端规则派生：
    全部回执 not_found 却声明 content_acquired → 拒绝。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        gap_exhaustion(
            gap_id="gap-class-sci",
            final_result_class="content_acquired",  # 回执实际全 not_found
        )

    # 反向合法：科学路线实际回执全部 content_acquired（内容已取得但缺所需字段）→ 允许
    acquired = gap_exhaustion(
        gap_id="gap-class-acquired",
        sci_receipt_result_class="content_acquired",
        sci_receipt_error_class=None,
        final_result_class="content_acquired",
    )
    assert acquired.route_evidence[0].final_result_class == "content_acquired"


def test_technical_access_blocked_route_rejects_successful_terminal() -> None:
    """技术访问阻断路线：终端回执成功（content_acquired）→ 拒绝。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        gap_exhaustion(
            gap_id="gap-class-tech",
            current_state="unresolved_due_to_route",
            technical=True,
            tech_terminal_result_class="content_acquired",
            tech_terminal_error_class=None,
        )


def test_empty_path_rejects_cross_report_gate_spec_and_wrong_field(tmp_path: Path) -> None:
    """A/B/C 空路径：evidence_gap.gate_spec_id 必须等于真实 spec，
    field_id 必须等于空场景资格单元字段。"""
    for report_kind, kind in (
        (ReportKind.A, EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT),
        (ReportKind.B, EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL),
        (ReportKind.C, EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL),
    ):
        spec = spec_yaml(report_kind.value)
        workspace_root = prepare_workspace(tmp_path / report_kind.value)
        snapshot_arg = (
            None if report_kind is ReportKind.A else snapshot_for(report_kind)
        )
        # 跨报告 gate_spec_id（摘要一致构造）→ 拒绝
        forged = empty_evidence_for(
            report_kind,
            candidate_product_ids=(
                ()
                if report_kind is ReportKind.A
                else ("product-a",)
            ),
            candidate_trial_ids=(
                ()
                if report_kind is ReportKind.A
                else ("trial-1",)
            ),
            gate_spec_id="gate-spec-forged",
        )
        with pytest.raises(ValueError, match="GateSpec 说明书标识"):
            public_write_blocker_package(
                report_kind=report_kind,
                spec=spec,
                snapshot=snapshot_arg,
                gate_result=None,
                failed_units=(),
                record=forged.exhaustion,
                workspace_root=workspace_root,
                empty_universe=kind,
                empty_evidence=forged,
                empty_justification_zh="本轮未识别出符合条件的对象。",
            )
        # 错资格字段（摘要一致构造）→ 拒绝
        forged_field = empty_evidence_for(
            report_kind,
            candidate_product_ids=(
                ()
                if report_kind is ReportKind.A
                else ("product-a",)
            ),
            candidate_trial_ids=(
                ()
                if report_kind is ReportKind.A
                else ("trial-1",)
            ),
            field_id="wrong-field-id",
        )
        with pytest.raises(ValueError, match="资格单元字段"):
            public_write_blocker_package(
                report_kind=report_kind,
                spec=spec,
                snapshot=snapshot_arg,
                gate_result=None,
                failed_units=(),
                record=forged_field.exhaustion,
                workspace_root=workspace_root,
                empty_universe=kind,
                empty_evidence=forged_field,
                empty_justification_zh="本轮未识别出符合条件的对象。",
            )
        assert (workspace_root / "blockers").exists() is False


def test_bc_empty_requires_closed_snapshot_but_a_true_zero_allows_none(
    tmp_path: Path,
) -> None:
    """B/C 空场景必须绑定闭合快照；A 真正零产品路径允许 snapshot=None。"""
    # B/C 缺快照 → 拒绝
    for report_kind, kind in (
        (ReportKind.B, EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL),
        (ReportKind.C, EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL),
    ):
        spec = spec_yaml(report_kind.value)
        evidence = empty_evidence_for(
            report_kind,
            candidate_product_ids=("product-a",),
            candidate_trial_ids=("trial-1",),
        )
        workspace_root = prepare_workspace(tmp_path / report_kind.value)
        with pytest.raises(ValueError, match="闭合宇宙快照"):
            public_write_blocker_package(
                report_kind=report_kind,
                spec=spec,
                snapshot=None,
                gate_result=None,
                failed_units=(),
                record=evidence.exhaustion,
                workspace_root=workspace_root,
                empty_universe=kind,
                empty_evidence=evidence,
                empty_justification_zh="本轮未识别出符合条件的对象。",
            )
        assert (workspace_root / "blockers").exists() is False
    # A 真零产品 + snapshot=None → 通过
    report_kind = ReportKind.A
    spec = spec_yaml("A")
    evidence = empty_evidence_for(report_kind, candidate_product_ids=())
    workspace_root = prepare_workspace(tmp_path / "A-zero")
    json_path, _ = public_write_blocker_package(
        report_kind=report_kind,
        spec=spec,
        snapshot=None,
        gate_result=None,
        failed_units=(),
        record=evidence.exhaustion,
        workspace_root=workspace_root,
        empty_universe=EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
        empty_evidence=evidence,
        empty_justification_zh="本轮未识别出符合条件的创新产品。",
    )
    assert json_path.exists()


def test_empty_evidence_requires_exactly_one_gap_with_scope_object() -> None:
    """空宇宙证据必须恰有一个资格缺口：第二缺口拒绝、对象必须等于检索范围、
    状态必须为科学缺失状态。"""
    from pydantic import ValidationError


    report_kind = ReportKind.A
    empty_evidence_for(report_kind, candidate_product_ids=())

    # 第二缺口（同资格单元、不同检索范围对象）→ 拒绝
    extra_gap = gap_exhaustion(
        gap_id="gap-extra",
        gate_unit_id="a_innovation_eligibility",
        object_id="scope-A-2",
        object_type="product",
        current_state="not_reported",
        gate_spec_id="gate-spec-a-v1",
        field_id="a_innovation_eligibility",
        entity_id="scope-A-2",
        associated_entity_ids=(),
    )
    with pytest.raises(ValidationError):
        empty_evidence_for(
            report_kind,
            candidate_product_ids=(),
            extra_gap=extra_gap,
        )

    # 资格缺口对象不等于检索范围（摘要一致构造）→ 拒绝
    with pytest.raises(ValidationError):
        empty_evidence_for(
            report_kind,
            candidate_product_ids=(),
            search_scope_id="scope-A-1",
            gap_object_id="product-a",  # 冒充产品对象
        )
