"""Task 5.2 AV08 历史与边缘视图：暂停/终止/撤回/放弃及邻近机制观察显式保留。

合同断言（先失败后通过）：
- 历史与边缘视图绑定单一锁定快照身份，产品集必须与 ``snapshot.product_ids``
  精确一一对应且顺序一致；
- 暂停、终止、撤回、放弃都是版本化历史状态记录，各自绑定产品、不可变事实
  版本与精确来源定位；历史状态地域只接受中国/境外分轨；
- 邻近机制观察是显式声明的版本化记录，携带机制关系依据与版本血统；
- 视图不存在任何状态筛选/删除出口：无论当前开发状态如何，全部产品同等
  保留，停止开发产品不消失、不降级；活跃产品保留显式空历史集合；
- 未知产品、重复记录身份、空白事实版本/来源定位/机制关系依据均失败关闭；
- 视图为不可变、确定性纯投影：无 Top-N/删除/降级参数。
"""

from __future__ import annotations

import inspect
from typing import TypedDict

import pytest
from _evidence_factory import build_evidence_context
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    ConflictDisposition,
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
from ci_workflow.reports.a.contracts import (
    AnchorTrialRecord,
    AProjectContract,
    CoreTrialRecord,
    CoreTrialRole,
    RegulatoryEventKind,
    RegulatoryEventRecord,
)
from ci_workflow.reports.a.pages import (
    AdjacentObservationRecord,
    AEvidenceContext,
    HistoricalStatusKind,
    HistoricalStatusRecord,
    HistoryEdgeProduct,
    HistoryEdgeView,
    build_history_edge_view,
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
    product_ids: tuple[str, ...],
    trial_ids: tuple[str, ...] = (),
    trial_products: dict[str, str] | None = None,
    design_kinds: dict[str, TrialDesignKind] | None = None,
    enumeration_complete: bool = True,
    evidence_snapshot_id: str = "snap-ev-1",
) -> ApplicableUniverseSnapshot:
    """构建已闭合的适用宇宙快照（单臂试验，无比较/组别对象）。"""
    trial_products = trial_products or {trial: product_ids[0] for trial in trial_ids}
    design_kinds = design_kinds or {trial: TrialDesignKind.SINGLE_ARM for trial in trial_ids}
    edges = tuple(
        UniverseEdge(
            parent_type=GateObjectType.PRODUCT,
            parent_id=trial_products[trial],
            child_type=GateObjectType.TRIAL,
            child_id=trial,
        )
        for trial in trial_ids
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
    empty_proofs = tuple(
        EmptySetProof(
            object_type=object_type,
            reason_code=EmptySetReasonCode.EXHAUSTIVE_SEARCH_NO_OBJECTS,
            evidence_version_id=f"empty-ev-{object_type.value}",
            explanation_zh="穷尽检索后未发现相关对象",
        )
        for object_type in (
            GateObjectType.TRIAL,
            GateObjectType.COMPARISON,
            GateObjectType.GROUP,
            GateObjectType.ENDPOINT,
            GateObjectType.TIMEPOINT,
        )
        if not (object_type is GateObjectType.TRIAL and trial_ids)
    )
    summary = compute_universe_summary(
        project_id="report-universe",
        evidence_snapshot_id=evidence_snapshot_id,
        research_role_set_id="role-set-1",
        product_ids=product_ids,
        trial_ids=trial_ids,
        empty_set_proofs=empty_proofs,
        relationship_edges=edges,
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id="ind-rule-1",
        applicable_conditional_predicates=("termination-rule-1",),
    )
    return ApplicableUniverseSnapshot(
        project_id="report-universe",
        evidence_snapshot_id=evidence_snapshot_id,
        research_role_set_id="role-set-1",
        product_ids=product_ids,
        trial_ids=trial_ids,
        empty_set_proofs=empty_proofs,
        relationship_edges=edges,
        trial_design_evidence=trial_design_evidence,
        indication_rule_set_id="ind-rule-1",
        applicable_conditional_predicates=("termination-rule-1",),
        universe_summary=summary,
        enumeration_complete=enumeration_complete,
    )


def _binding(
    *,
    binding_id: str,
    unit_id: str = "a-unit-1",
    object_id: str,
    trial_id: str | None,
    fact_version_id: str,
    fact_domain: FactDomain = FactDomain.EFFICACY,
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
) -> GateEvidenceBinding:
    return GateEvidenceBinding(
        binding_id=binding_id,
        unit_id=unit_id,
        object_id=object_id,
        fact_version_id=fact_version_id,
        trial_id=trial_id,
        fact_domain=fact_domain,
        observation_kind=ObservationKind.OBSERVED_RESULT,
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
    )


def _complete_project(**overrides: object) -> AProjectContract:
    """构建一个所有必需字段齐备的 A 项目；测试用 overrides 制造差异。"""
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
                event_id="ev-approval-cn",
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


def _design_binding(
    *,
    binding_id: str,
    object_id: str,
    trial_id: str,
    fact_version_id: str,
) -> GateEvidenceBinding:
    return _binding(
        binding_id=binding_id,
        object_id=object_id,
        trial_id=trial_id,
        fact_version_id=fact_version_id,
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        unit=None,
        denominator=None,
        definition="随机对照试验设计",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,
        source_role=SourceRole.PROTOCOL_SAP,
    )


def _facts() -> dict[str, tuple[str, str, str, str]]:
    """fact_version_id -> (entity_id, field_id, raw_value, locator)。"""
    return {
        "fact-reg": (
            "project-dupilumab",
            "regulatory_event",
            "批准 2020-06-19 中国",
            "NMPA/approval-notice-2020",
        ),
        "fact-v-1": (
            "project-dupilumab",
            "core_efficacy",
            "52.3 应答率 %",
            "CT.gov/results/table-1",
        ),
        "fact-v-2": ("project-dupilumab", "safety_summary", "52.3 %", "CT.gov/results/table-1"),
        "fact-clin": (
            "p-clinical",
            "clinical_trial_region",
            "II期 进行中 中国",
            "CT.gov/results/portfolio-1",
        ),
        "fact-term-design": (
            "p-terminated",
            "clinical_trial_region",
            "II期 已终止 境外",
            "CT.gov/results/portfolio-1",
        ),
        "fact-term-reg": (
            "p-terminated",
            "regulatory_event",
            "终止 2023-11-01 境外",
            "NMPA/approval-notice-2020",
        ),
        "fact-hist-suspend": (
            "p-clinical",
            "historical_status",
            "暂停 2023-03-01 中国",
            "registry/status-history-1",
        ),
        "fact-hist-abandon": (
            "p-preclinical",
            "historical_status",
            "放弃 2022-09-15 境外",
            "registry/status-history-2",
        ),
        "fact-hist-term": (
            "p-terminated",
            "historical_status",
            "终止 2023-11-01 境外",
            "registry/status-history-3",
        ),
        "fact-hist-withdraw": (
            "p-china-only",
            "historical_status",
            "撤回 2024-02-10 中国",
            "registry/status-history-4",
        ),
        "fact-adjacent-1": (
            "p-preclinical",
            "adjacent_mechanism_observation",
            "靶点与目标适应症机制相关，适应症关系未确立，独立观察",
            "literature/review-1",
        ),
    }


def _mixed_universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    tuple[GateEvidenceBinding, ...],
    AEvidenceContext,
]:
    """覆盖上市/临床/临床前/终止/仅中国开发五种生命周期的全宇宙。"""
    projects = [
        _complete_project(),  # project-dupilumab：上市 + 结果齐备
        _complete_project(
            project_id="p-clinical",
            canonical_name="临床示例药",
            core_trials=(
                CoreTrialRecord(
                    trial_id="NCT-clin-1",
                    role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                    status="进行中",
                ),
            ),
            regulatory_events=(
                RegulatoryEventRecord(
                    event_id="ev-pause-1",
                    event_kind=RegulatoryEventKind.PAUSE,
                    jurisdiction=_field(value="中国"),
                    event_date=_field(value="2023-03-01"),
                ),
            ),
            anchor_trials=(),
        ),
        _complete_project(
            project_id="p-preclinical",
            canonical_name="临床前示例药",
            core_trials=(),
            regulatory_events=(
                RegulatoryEventRecord(
                    event_id="ev-abandon-1",
                    event_kind=RegulatoryEventKind.ABANDONMENT,
                    jurisdiction=_field(value="境外"),
                    event_date=_field(value="2022-09-15"),
                ),
            ),
            anchor_trials=(),
        ),
        _complete_project(
            project_id="p-terminated",
            canonical_name="终止示例药",
            core_trials=(
                CoreTrialRecord(
                    trial_id="NCT-term-1",
                    role=CoreTrialRole.EARLY_DECISION,
                    status="已终止",
                ),
            ),
            regulatory_events=(
                RegulatoryEventRecord(
                    event_id="ev-term-1",
                    event_kind=RegulatoryEventKind.TERMINATION,
                    jurisdiction=_field(value="境外"),
                    event_date=_field(value="2023-11-01"),
                ),
            ),
            anchor_trials=(),
        ),
        _complete_project(  # p-china-only：境外整组显式不适用
            project_id="p-china-only",
            canonical_name="仅中国开发药",
            core_trials=(),
            regulatory_events=(
                RegulatoryEventRecord(
                    event_id="ev-withdraw-1",
                    event_kind=RegulatoryEventKind.WITHDRAWAL,
                    jurisdiction=_field(value="中国"),
                    event_date=_field(value="2024-02-10"),
                ),
            ),
            anchor_trials=(),
            overseas={
                "highest_stage": _field(state=EvidenceFieldState.NOT_APPLICABLE),
                "highest_status": _field(state=EvidenceFieldState.NOT_APPLICABLE),
                "date": _field(state=EvidenceFieldState.NOT_APPLICABLE),
            },
        ),
    ]
    bindings = (
        # project-dupilumab：监管观察值 + 疗效 + TEAE 摘要
        _binding(
            binding_id="b-reg",
            object_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="fact-reg",
            source_role=SourceRole.REGULATORY_MATERIAL,
            definition=None,
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
        ),
        _binding(
            binding_id="b-eff",
            object_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="fact-v-1",
        ),
        _binding(
            binding_id="b-saf",
            unit_id="a_safety_event_teae",
            object_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="fact-v-2",
            fact_domain=FactDomain.SAFETY,
            unit="%",
            definition=None,
            direction=None,
            timepoint=None,
            event_definition="治疗期间不良事件",
            time_window="治疗期间",
        ),
        # p-clinical：设计事实
        _design_binding(
            binding_id="b-clin",
            object_id="p-clinical",
            trial_id="NCT-clin-1",
            fact_version_id="fact-clin",
        ),
        # p-terminated：设计事实 + 监管不适用（终止）
        _design_binding(
            binding_id="b-term-design",
            object_id="p-terminated",
            trial_id="NCT-term-1",
            fact_version_id="fact-term-design",
        ),
        _binding(
            binding_id="b-term-reg",
            unit_id="a_regulatory_termination",
            object_id="p-terminated",
            trial_id=None,
            fact_version_id="fact-term-reg",
            source_role=SourceRole.REGULATORY_MATERIAL,
            disclosure_state=FactDisclosureState.NOT_APPLICABLE,
            applicability_predicate_id="termination-rule-1",
            numeric_value=None,
            denominator=None,
            definition=None,
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
        ),
    )
    evidence = build_evidence_context(tmp_path, project_id="report-universe", facts=_facts())
    snapshot = _snapshot(
        product_ids=(
            "project-dupilumab",
            "p-clinical",
            "p-preclinical",
            "p-terminated",
            "p-china-only",
        ),
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
        },
        evidence_snapshot_id=evidence.locked.snapshot_id,
    )
    return projects, snapshot, bindings, evidence


class HistoryEdgeRecordBundle(TypedDict):
    """两类版本化记录的类型化捆绑：键名与构建器关键字一致。"""

    historical_statuses: tuple[HistoricalStatusRecord, ...]
    adjacent_observations: tuple[AdjacentObservationRecord, ...]


def _historical_statuses() -> tuple[HistoricalStatusRecord, ...]:
    """四类历史状态版本化记录：暂停/放弃/终止/撤回各一条。"""
    return (
        HistoricalStatusRecord(
            project_id="p-clinical",
            regulatory_event_id="ev-pause-1",
            status_kind=HistoricalStatusKind.SUSPENDED,
            jurisdiction="中国",
            status_date=_field(value="2023-03-01"),
            fact_version_id="fact-hist-suspend",
            source_location="registry/status-history-1",
        ),
        HistoricalStatusRecord(
            project_id="p-preclinical",
            regulatory_event_id="ev-abandon-1",
            status_kind=HistoricalStatusKind.ABANDONED,
            jurisdiction="境外",
            status_date=_field(value="2022-09-15"),
            fact_version_id="fact-hist-abandon",
            source_location="registry/status-history-2",
        ),
        HistoricalStatusRecord(
            project_id="p-terminated",
            regulatory_event_id="ev-term-1",
            status_kind=HistoricalStatusKind.TERMINATED,
            jurisdiction="境外",
            status_date=_field(value="2023-11-01"),
            fact_version_id="fact-hist-term",
            source_location="registry/status-history-3",
        ),
        HistoricalStatusRecord(
            project_id="p-china-only",
            regulatory_event_id="ev-withdraw-1",
            status_kind=HistoricalStatusKind.WITHDRAWN,
            jurisdiction="中国",
            status_date=_field(value="2024-02-10"),
            fact_version_id="fact-hist-withdraw",
            source_location="registry/status-history-4",
        ),
    )


def _adjacent_observations() -> tuple[AdjacentObservationRecord, ...]:
    """邻近机制观察显式声明记录：机制相关但适应症关系未确立。"""
    return (
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh="靶点与目标适应症机制相关，适应症关系未确立，独立观察",
            fact_version_id="fact-adjacent-1",
            source_location="literature/review-1",
        ),
    )


def _history_edge_universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    AEvidenceContext,
    HistoryEdgeView,
]:
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    view = build_history_edge_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        historical_statuses=_historical_statuses(),
        adjacent_observations=_adjacent_observations(),
    )
    return projects, snapshot, evidence, view


# ── AV08 精确验收节点 ───────────────────────────────────────────────────────


def test_suspended_terminated_withdrawn_and_abandoned_programs_remain_visible(tmp_path) -> None:
    """暂停、终止、撤回、放弃产品全部保留，且邻近机制观察显式可见。"""
    projects, snapshot, _, view = _history_edge_universe(tmp_path)
    assert tuple(product.project_id for product in view.products) == snapshot.product_ids

    by_id = {product.project_id: product for product in view.products}
    assert tuple(
        (row.status_kind_zh, row.jurisdiction, row.status_date)
        for row in by_id["p-clinical"].historical_statuses
    ) == (("暂停", "中国", "2023-03-01"),)
    assert tuple(
        (row.status_kind_zh, row.jurisdiction, row.status_date)
        for row in by_id["p-preclinical"].historical_statuses
    ) == (("放弃", "境外", "2022-09-15"),)
    assert tuple(
        (row.status_kind_zh, row.jurisdiction, row.status_date)
        for row in by_id["p-terminated"].historical_statuses
    ) == (("终止", "境外", "2023-11-01"),)
    assert tuple(
        (row.status_kind_zh, row.jurisdiction, row.status_date)
        for row in by_id["p-china-only"].historical_statuses
    ) == (("撤回", "中国", "2024-02-10"),)

    # 每条历史状态携带版本血统。
    for product in view.products:
        for row in product.historical_statuses:
            assert row.fact_version_id
            assert row.source_location

    # 活跃（上市）产品保留显式空历史集合，不删除、不占位。
    assert by_id["project-dupilumab"].historical_statuses == ()
    assert by_id["project-dupilumab"].adjacent_observations == ()

    # 邻近机制观察显式保留（展示保留自然中文标点）。
    assert tuple(row.relation_basis_zh for row in by_id["p-preclinical"].adjacent_observations) == (
        "靶点与目标适应症机制相关，适应症关系未确立，独立观察",
    )
    for row in by_id["p-preclinical"].adjacent_observations:
        assert row.fact_version_id
        assert row.source_location


def test_history_edge_view_never_filters_by_development_status(tmp_path) -> None:
    """视图无任何状态筛选/删除出口：停止开发产品与其他产品同等保留。"""
    _, _, _, view = _history_edge_universe(tmp_path)
    ids = [product.project_id for product in view.products]
    assert "p-terminated" in ids
    assert "p-clinical" in ids
    assert "p-preclinical" in ids
    assert "p-china-only" in ids
    assert "project-dupilumab" in ids
    assert len(ids) == len(set(ids))
    assert not hasattr(view, "filtered")
    assert not hasattr(view, "by_status")


def test_history_edge_rows_carry_professional_status_context(tmp_path) -> None:
    """每行携带开发状态中文标签，停止开发产品带明确状态但不被过滤。"""
    _, _, _, view = _history_edge_universe(tmp_path)
    by_id = {product.project_id: product for product in view.products}
    assert by_id["p-terminated"].development_status_zh == "停止开发"
    assert by_id["project-dupilumab"].development_status_zh == "上市"
    assert by_id["p-preclinical"].development_status_zh == "临床前"


def test_history_edge_products_exactly_match_locked_snapshot(tmp_path) -> None:
    """历史与边缘视图产品集必须等于锁定快照且顺序一致。"""
    _, snapshot, _, view = _history_edge_universe(tmp_path)
    assert tuple(p.project_id for p in view.products) == snapshot.product_ids
    assert isinstance(view.products[0], HistoryEdgeProduct)


# ── 版本化记录：未知产品、重复身份、空白定位 ────────────────────────────────


def test_history_rejects_unknown_product_status(tmp_path) -> None:
    """历史状态记录引用未知产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    statuses = (
        *_historical_statuses(),
        HistoricalStatusRecord(
            project_id="p-extra",
            regulatory_event_id="ev-pause-1",
            status_kind=HistoricalStatusKind.SUSPENDED,
            jurisdiction="中国",
            status_date=_field(value="2024-01-01"),
            fact_version_id="fact-extra",
            source_location="registry/status-history-x",
        ),
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            historical_statuses=statuses,
            adjacent_observations=_adjacent_observations(),
        )


def test_history_rejects_unknown_product_observation(tmp_path) -> None:
    """邻近观察记录引用未知产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    observations = (
        *_adjacent_observations(),
        AdjacentObservationRecord(
            project_id="p-extra",
            relation_basis_zh="机制相关，独立观察",
            fact_version_id="fact-extra-obs",
            source_location="literature/review-x",
        ),
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            historical_statuses=_historical_statuses(),
            adjacent_observations=observations,
        )


def test_history_rejects_duplicate_status_record(tmp_path) -> None:
    """同一产品同一状态同一地域同一日期重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    statuses = (
        *_historical_statuses(),
        HistoricalStatusRecord(
            project_id="p-clinical",
            regulatory_event_id="ev-pause-1",
            status_kind=HistoricalStatusKind.SUSPENDED,
            jurisdiction="中国",
            status_date=_field(value="2023-03-01"),
            fact_version_id="fact-hist-suspend-dup",
            source_location="registry/status-history-dup",
        ),
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            historical_statuses=statuses,
            adjacent_observations=_adjacent_observations(),
        )


def test_history_rejects_duplicate_adjacent_observation(tmp_path) -> None:
    """同一产品同一机制关系依据重复声明必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    observations = (
        *_adjacent_observations(),
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh="靶点与目标适应症机制相关，适应症关系未确立，独立观察",
            fact_version_id="fact-adjacent-dup",
            source_location="literature/review-dup",
        ),
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            historical_statuses=_historical_statuses(),
            adjacent_observations=observations,
        )


def test_history_record_rejects_blank_lineage(tmp_path) -> None:
    """历史记录不得携带空白事实版本或来源定位。"""
    with pytest.raises(ValidationError):
        HistoricalStatusRecord(
            project_id="p-clinical",
            status_kind=HistoricalStatusKind.SUSPENDED,
            jurisdiction="中国",
            status_date=_field(value="2023-03-01"),
            fact_version_id=" ",
            source_location="registry/status-history-1",
        )
    with pytest.raises(ValidationError):
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh="靶点与目标适应症机制相关",
            fact_version_id="fact-adjacent-blank",
            source_location="  ",
        )


def test_history_status_rejects_non_track_jurisdiction(tmp_path) -> None:
    """历史状态地域只接受中国/境外分轨，其余值失败关闭。"""
    with pytest.raises(ValidationError):
        HistoricalStatusRecord(
            project_id="p-clinical",
            status_kind=HistoricalStatusKind.SUSPENDED,
            jurisdiction="全球",
            status_date=_field(value="2023-03-01"),
            fact_version_id="fact-jur",
            source_location="registry/status-history-jur",
        )


def test_history_observation_rejects_blank_relation_basis(tmp_path) -> None:
    """邻近观察必须携带明确的机制关系依据，空白依据失败关闭。"""
    with pytest.raises(ValidationError):
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh=" ",
            fact_version_id="fact-adjacent-blank-basis",
            source_location="literature/review-blank",
        )


def test_history_status_rejects_blank_status_date(tmp_path) -> None:
    """历史状态必须携带状态日期确定值或互斥状态，空白失败关闭。"""
    with pytest.raises(ValidationError):
        HistoricalStatusRecord(
            project_id="p-clinical",
            status_kind=HistoricalStatusKind.SUSPENDED,
            jurisdiction="中国",
            status_date=_field(),
            fact_version_id="fact-date-blank",
            source_location="registry/status-history-date",
        )


# ── 视图不变量：不可变、确定性、无 Top-N/筛选参数 ──────────────────────────


def test_build_history_edge_has_no_filter_or_drop_parameters() -> None:
    """历史与边缘构建器不存在 Top-N、状态筛选、删除或降级出口。"""
    assert set(inspect.signature(build_history_edge_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "historical_statuses",
        "adjacent_observations",
        "results_posted_evidence",
    }


def test_history_edge_view_is_immutable_and_deterministic(tmp_path) -> None:
    """视图不可变：记录不可改写，同输入两次构建结果一致。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    first = build_history_edge_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        historical_statuses=_historical_statuses(),
        adjacent_observations=_adjacent_observations(),
    )
    second = build_history_edge_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        historical_statuses=_historical_statuses(),
        adjacent_observations=_adjacent_observations(),
    )
    assert first == second
    with pytest.raises(ValidationError):
        first.products[1].historical_statuses[0].status_date = "改写"


def test_history_edge_labels_are_professional_chinese(tmp_path) -> None:
    """状态类型标签为专业中文，不暴露后端枚举或工程状态。"""
    _, _, _, view = _history_edge_universe(tmp_path)
    labels = "".join(
        row.status_kind_zh for product in view.products for row in product.historical_statuses
    )
    assert all("\u4e00" <= ch <= "\u9fff" for ch in labels)
    lowered = labels.lower()
    for token in ("suspended", "terminated", "withdrawn", "abandoned", "snapshot", "binding"):
        assert token not in lowered
