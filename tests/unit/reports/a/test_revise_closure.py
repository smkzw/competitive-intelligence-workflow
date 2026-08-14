"""Task 5.2 REVISE 八类反例回归：证据快照闭合、分析权威、完整档案、试验分层、
事件 ID 绑定、历史状态闭合、用户可见文本权威、视图作用域与渲染边界。

每类反例先 RED 后 GREEN：先写精确回归测试（本快照接受/换快照拒绝/伪
fact/locator 拒绝），再做最小完整修复。本文件使用共享证据夹具工厂
（``_evidence_factory``）构造真实 LockedSnapshot/Manifest/Registry 合同，
不在测试里散落伪摘要。
"""

from __future__ import annotations

import inspect

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
    ClinicalPortfolioView,
    ClinicalTrialLayer,
    ClinicalTrialRegionRecord,
    HistoricalStatusKind,
    HistoricalStatusRecord,
    ProductOverviewView,
    RegulatoryEventVersionRecord,
    ViewScope,
    assert_clinical_portfolio_view_authoritative,
    assert_landscape_view_authoritative,
    assert_product_overview_view_authoritative,
    assert_regulatory_view_authoritative,
    build_clinical_portfolio_view,
    build_history_edge_view,
    build_landscape_view,
    build_product_dossier_view,
    build_product_overview_view,
    build_regulatory_view,
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
    evidence_snapshot_id: str = "snap-ev-1",
) -> ApplicableUniverseSnapshot:
    """构建已闭合的适用宇宙快照（单臂试验，无比较/组别对象）。"""
    trial_products = trial_products or {trial: product_ids[0] for trial in trial_ids}
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
            design_kind=TrialDesignKind.SINGLE_ARM,
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
        enumeration_complete=True,
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
        review_state=FactReviewState.ACCEPTED,
        disclosure_state=disclosure_state,
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        source_role=source_role,
        conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        applicability_predicate_id=applicability_predicate_id,
    )


def _complete_project(**overrides: object) -> AProjectContract:
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


def _facts() -> dict[str, tuple[str, str, str, str]]:
    """fact_version_id -> (entity_id, field_id, raw_value, locator)。"""
    facts: dict[str, tuple[str, str, str, str]] = {
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
        "fact-v-2": (
            "project-dupilumab",
            "safety_summary",
            "52.3 %",
            "CT.gov/results/table-1",
        ),
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
        "fact-region-dup-cn": (
            "project-dupilumab",
            "clinical_trial_region",
            "III期 已完成 中国",
            "CT.gov/results/portfolio-1",
        ),
        "fact-region-dup-os": (
            "project-dupilumab",
            "clinical_trial_region",
            "III期 已完成 境外",
            "CT.gov/results/portfolio-1",
        ),
        "fact-term-reg": (
            "p-terminated",
            "regulatory_event",
            "终止 2023-11-01 境外",
            "NMPA/approval-notice-2020",
        ),
        "fact-pause": (
            "p-clinical",
            "regulatory_event",
            "暂停 2023-03-01 中国",
            "NMPA/approval-notice-2020",
        ),
        "fact-abandon": (
            "p-preclinical",
            "regulatory_event",
            "放弃 2022-09-15 境外",
            "NMPA/approval-notice-2020",
        ),
        "fact-withdraw": (
            "p-china-only",
            "regulatory_event",
            "撤回 2024-02-10 中国",
            "NMPA/approval-notice-2020",
        ),
        "fact-org-origin": (
            "project-dupilumab",
            "organization_role",
            "原研 再生元",
            "company/press-release-1",
        ),
        "fact-org-dev": (
            "project-dupilumab",
            "organization_role",
            "开发者 赛诺菲",
            "company/press-release-2",
        ),
        "fact-rel-collab": (
            "project-dupilumab",
            "company_relationship",
            "合作 赛诺菲",
            "company/contract-summary-1",
        ),
        "fact-rights-cn": (
            "project-dupilumab",
            "geographic_rights",
            "中国 中国大陆独家商业化权利",
            "company/contract-summary-2",
        ),
        "fact-tx-license": (
            "project-dupilumab",
            "transaction_event",
            "许可交易 2019-06-01",
            "company/press-release-3",
        ),
        "fact-term-milestone": (
            "project-dupilumab",
            "public_term",
            "首付款 2 亿美元，里程碑付款最高 10 亿美元",
            "company/press-release-4",
        ),
        "fact-family-1": (
            "project-dupilumab",
            "patent_family",
            "度普利尤单抗抗体制剂专利族",
            "patent-office/family-register-1",
        ),
        "fact-member-cn": (
            "project-dupilumab",
            "patent_member_status",
            "中国 已授权",
            "CNIPA/gazette-1",
        ),
        "fact-member-us": (
            "project-dupilumab",
            "patent_member_status",
            "美国 审评中",
            "USPTO/status-1",
        ),
        "fact-scope-1": (
            "project-dupilumab",
            "patent_scope",
            "覆盖含目标抗体的组合物、制剂及其治疗用途",
            "patent-office/claims-summary-1",
        ),
        "fact-term-cn": (
            "project-dupilumab",
            "patent_term_expiry",
            "自申请日起 20 年 2034-05-12",
            "CNIPA/gazette-1",
        ),
        "fact-term-us": (
            "project-dupilumab",
            "patent_term_expiry",
            "自申请日起 20 年 尚未公开",
            "USPTO/status-1",
        ),
        "fact-excl-cn": (
            "project-dupilumab",
            "regulatory_exclusivity_expiry",
            "数据独占 中国 2025-06-19",
            "NMPA/exclusivity-notice-1",
        ),
        "fact-excl-us": (
            "project-dupilumab",
            "regulatory_exclusivity_expiry",
            "孤儿药独占 境外 2027-03-28",
            "FDA/orphan-list-1",
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
        "study-role-nct1": (
            "NCT02407756",
            "study_role",
            "注册/关键",
            "CT.gov/results/role-1",
        ),
        "study-role-clin": (
            "NCT-clin-1",
            "study_role",
            "注册/关键",
            "CT.gov/results/role-2",
        ),
        "study-role-term": (
            "NCT-term-1",
            "study_role",
            "特殊核心",
            "CT.gov/results/role-3",
        ),
    }
    return facts


def _universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    tuple[GateEvidenceBinding, ...],
    AEvidenceContext,
]:
    """完整宇宙：五种生命周期 + 全部版本化记录所需事件。"""
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
        _complete_project(
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
        _binding(
            binding_id="b-clin",
            object_id="p-clinical",
            trial_id="NCT-clin-1",
            fact_version_id="fact-clin",
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
        ),
        _binding(
            binding_id="b-term-design",
            object_id="p-terminated",
            trial_id="NCT-term-1",
            fact_version_id="fact-term-design",
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


def _region_record(
    *,
    project_id: str,
    trial_id: str,
    region: str,
    phase: str,
    status: str,
    layer: ClinicalTrialLayer,
    fact_version_id: str,
) -> ClinicalTrialRegionRecord:
    return ClinicalTrialRegionRecord(
        project_id=project_id,
        trial_id=trial_id,
        region=region,
        phase=_field(value=phase),
        status=_field(value=status),
        layer=layer,
        fact_version_id=fact_version_id,
        source_location="CT.gov/results/portfolio-1",
    )


def _portfolio_records() -> tuple[ClinicalTrialRegionRecord, ...]:
    return (
        _region_record(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            region="中国",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
            fact_version_id="fact-region-dup-cn",
        ),
        _region_record(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            region="境外",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
            fact_version_id="fact-region-dup-os",
        ),
        _region_record(
            project_id="p-clinical",
            trial_id="NCT-clin-1",
            region="中国",
            phase="II期",
            status="进行中",
            layer=ClinicalTrialLayer.CORE,
            fact_version_id="fact-clin",
        ),
        _region_record(
            project_id="p-terminated",
            trial_id="NCT-term-1",
            region="境外",
            phase="II期",
            status="已终止",
            layer=ClinicalTrialLayer.SPECIAL_CORE,
            fact_version_id="fact-term-design",
        ),
    )


def _event_record(
    *,
    project_id: str,
    event_id: str,
    event_kind: RegulatoryEventKind,
    jurisdiction: str,
    event_date: str,
    fact_version_id: str,
) -> RegulatoryEventVersionRecord:
    return RegulatoryEventVersionRecord(
        project_id=project_id,
        event_id=event_id,
        event_kind=event_kind,
        jurisdiction=_field(value=jurisdiction),
        event_date=_field(value=event_date),
        fact_version_id=fact_version_id,
        source_location="NMPA/approval-notice-2020",
    )


def _versioned_events() -> tuple[RegulatoryEventVersionRecord, ...]:
    return (
        _event_record(
            project_id="project-dupilumab",
            event_id="ev-approval-cn",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction="中国",
            event_date="2020-06-19",
            fact_version_id="fact-reg",
        ),
        _event_record(
            project_id="p-clinical",
            event_id="ev-pause-1",
            event_kind=RegulatoryEventKind.PAUSE,
            jurisdiction="中国",
            event_date="2023-03-01",
            fact_version_id="fact-pause",
        ),
        _event_record(
            project_id="p-preclinical",
            event_id="ev-abandon-1",
            event_kind=RegulatoryEventKind.ABANDONMENT,
            jurisdiction="境外",
            event_date="2022-09-15",
            fact_version_id="fact-abandon",
        ),
        _event_record(
            project_id="p-terminated",
            event_id="ev-term-1",
            event_kind=RegulatoryEventKind.TERMINATION,
            jurisdiction="境外",
            event_date="2023-11-01",
            fact_version_id="fact-term-reg",
        ),
        _event_record(
            project_id="p-china-only",
            event_id="ev-withdraw-1",
            event_kind=RegulatoryEventKind.WITHDRAWAL,
            jurisdiction="中国",
            event_date="2024-02-10",
            fact_version_id="fact-withdraw",
        ),
    )


def _historical_statuses() -> tuple[HistoricalStatusRecord, ...]:
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


def _company_records() -> dict[str, tuple[object, ...]]:
    from ci_workflow.reports.a.pages import (
        CompanyRelationshipKind,
        CompanyRelationshipRecord,
        CompanyRoleKind,
        GeographicRightsRecord,
        OrganizationRoleRecord,
        PublicTermRecord,
        TransactionEventKind,
        TransactionEventRecord,
    )

    return {
        "organization_roles": (
            OrganizationRoleRecord(
                project_id="project-dupilumab",
                organization_zh="再生元",
                role=CompanyRoleKind.ORIGINATOR,
                fact_version_id="fact-org-origin",
                source_location="company/press-release-1",
            ),
            OrganizationRoleRecord(
                project_id="project-dupilumab",
                organization_zh="赛诺菲",
                role=CompanyRoleKind.DEVELOPER,
                fact_version_id="fact-org-dev",
                source_location="company/press-release-2",
            ),
        ),
        "relationships": (
            CompanyRelationshipRecord(
                project_id="project-dupilumab",
                counterparty_zh="赛诺菲",
                relationship=CompanyRelationshipKind.COLLABORATION,
                fact_version_id="fact-rel-collab",
                source_location="company/contract-summary-1",
            ),
        ),
        "geographic_rights": (
            GeographicRightsRecord(
                project_id="project-dupilumab",
                region="中国",
                rights_zh="中国大陆独家商业化权利",
                fact_version_id="fact-rights-cn",
                source_location="company/contract-summary-2",
            ),
        ),
        "transaction_events": (
            TransactionEventRecord(
                project_id="project-dupilumab",
                event_kind=TransactionEventKind.LICENSE,
                event_date=_field(value="2019-06-01"),
                fact_version_id="fact-tx-license",
                source_location="company/press-release-3",
            ),
        ),
        "public_terms": (
            PublicTermRecord(
                project_id="project-dupilumab",
                term_zh="首付款 2 亿美元，里程碑付款最高 10 亿美元",
                fact_version_id="fact-term-milestone",
                source_location="company/press-release-4",
            ),
        ),
    }


def _patent_records() -> dict[str, tuple[object, ...]]:
    from ci_workflow.reports.a.pages import (
        PatentFamilyRecord,
        PatentMemberRecord,
        PatentScopeRecord,
        PatentTermRecord,
        RegulatoryExclusivityKind,
        RegulatoryExclusivityRecord,
    )

    return {
        "families": (
            PatentFamilyRecord(
                project_id="project-dupilumab",
                family_id="patent-family-1",
                family_label_zh="度普利尤单抗抗体制剂专利族",
                fact_version_id="fact-family-1",
                source_location="patent-office/family-register-1",
            ),
        ),
        "members": (
            PatentMemberRecord(
                project_id="project-dupilumab",
                family_id="patent-family-1",
                member_id="member-cn-1",
                jurisdiction="中国",
                member_status=_field(value="已授权"),
                fact_version_id="fact-member-cn",
                source_location="CNIPA/gazette-1",
            ),
            PatentMemberRecord(
                project_id="project-dupilumab",
                family_id="patent-family-1",
                member_id="member-us-1",
                jurisdiction="美国",
                member_status=_field(value="审评中"),
                fact_version_id="fact-member-us",
                source_location="USPTO/status-1",
            ),
        ),
        "scopes": (
            PatentScopeRecord(
                project_id="project-dupilumab",
                family_id="patent-family-1",
                scope_zh="覆盖含目标抗体的组合物、制剂及其治疗用途",
                fact_version_id="fact-scope-1",
                source_location="patent-office/claims-summary-1",
            ),
        ),
        "terms": (
            PatentTermRecord(
                project_id="project-dupilumab",
                member_id="member-cn-1",
                term_zh="自申请日起 20 年",
                expiry=_field(value="2034-05-12"),
                fact_version_id="fact-term-cn",
                source_location="CNIPA/gazette-1",
            ),
            PatentTermRecord(
                project_id="project-dupilumab",
                member_id="member-us-1",
                term_zh="自申请日起 20 年",
                expiry=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
                fact_version_id="fact-term-us",
                source_location="USPTO/status-1",
            ),
        ),
        "exclusivities": (
            RegulatoryExclusivityRecord(
                project_id="project-dupilumab",
                exclusivity_kind=RegulatoryExclusivityKind.DATA_EXCLUSIVITY,
                jurisdiction="中国",
                expiry=_field(value="2025-06-19"),
                fact_version_id="fact-excl-cn",
                source_location="NMPA/exclusivity-notice-1",
            ),
            RegulatoryExclusivityRecord(
                project_id="project-dupilumab",
                exclusivity_kind=RegulatoryExclusivityKind.ORPHAN_DRUG_EXCLUSIVITY,
                jurisdiction="境外",
                expiry=_field(value="2027-03-28"),
                fact_version_id="fact-excl-us",
                source_location="FDA/orphan-list-1",
            ),
        ),
    }


# ── CE1 事实/定位必须属于当前证据快照 ───────────────────────────────────────


def test_record_fact_must_belong_to_current_evidence_snapshot(tmp_path) -> None:
    """同一业务记录搬入另一个 evidence_snapshot_id 的快照必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _versioned_events(),
        authoritative_contract_store=evidence.contract_store,
    )
    assert view.products

    # 构造另一个证据快照（新清单/新锁定 ID），同一记录不得继续被接受。
    other = build_evidence_context(tmp_path, project_id="report-universe", facts=_facts())
    other_snapshot = _snapshot(
        product_ids=snapshot.product_ids,
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
        },
        evidence_snapshot_id=other.locked.snapshot_id,
    )
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            other_snapshot,
            evidence,
            bindings,
            _versioned_events(),
            authoritative_contract_store=evidence.contract_store,
        )


def test_record_rejects_fabricated_fact_version(tmp_path) -> None:
    """记录引用未在当前证据快照注册的事实版本必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _event_record(
        project_id="project-dupilumab",
        event_id="ev-approval-cn",
        event_kind=RegulatoryEventKind.APPROVAL,
        jurisdiction="中国",
        event_date="2020-06-19",
        fact_version_id="fact-forged",
    )
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            (*_versioned_events(), forged),
            authoritative_contract_store=evidence.contract_store,
        )


def test_record_rejects_fabricated_locator(tmp_path) -> None:
    """记录来源定位与事实主片段定位不一致必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    records = list(_versioned_events())
    dupilumab = next(
        r for r in records if r.project_id == "project-dupilumab" and r.event_id == "ev-approval-cn"
    )
    swapped = RegulatoryEventVersionRecord(
        project_id=dupilumab.project_id,
        event_id=dupilumab.event_id,
        event_kind=dupilumab.event_kind,
        jurisdiction=dupilumab.jurisdiction,
        event_date=dupilumab.event_date,
        fact_version_id=dupilumab.fact_version_id,
        source_location="fabricated/other-location",
    )
    records = tuple(swapped if r is dupilumab else r for r in records)
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


# ── CE2 构建器不信任调用方分析结果 ──────────────────────────────────────────


def test_builders_do_not_accept_caller_analysis(tmp_path) -> None:
    """全部构建器签名不存在 analysis 输入，无法伪造分析结果。"""
    from ci_workflow.reports.a.pages import (
        build_company_deal_view,
        build_history_edge_view,
        build_patent_protection_view,
        build_product_dossier_view,
        build_product_overview_view,
    )

    for builder in (
        build_landscape_view,
        build_product_overview_view,
        build_product_dossier_view,
        build_clinical_portfolio_view,
        build_regulatory_view,
        build_company_deal_view,
        build_patent_protection_view,
        build_history_edge_view,
    ):
        assert "analysis" not in inspect.signature(builder).parameters


def test_render_boundary_rejects_stale_view(tmp_path) -> None:
    """渲染边界权威校验拒绝旧视图：换快照后旧视图不再权威。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_landscape_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    other = build_evidence_context(tmp_path, project_id="report-universe", facts=_facts())
    other_snapshot = _snapshot(
        product_ids=snapshot.product_ids,
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
        },
        evidence_snapshot_id=other.locked.snapshot_id,
    )
    with pytest.raises(GateEvaluationError):
        assert_landscape_view_authoritative(
            view,
            projects=projects,
            snapshot=other_snapshot,
            evidence=evidence,
            authoritative_contract_store=evidence.contract_store,
            bindings=bindings,
        )


# ── CE3 产品档案必须是真正的完整档案 ───────────────────────────────────────


def test_dossier_is_complete_profile_with_typed_evidence(tmp_path) -> None:
    """档案纳入临床组合、监管分轨、企业交易、专利保护、历史状态与疗效/安全。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        trial_region_records=_portfolio_records(),
        versioned_events=_versioned_events(),
        **_company_records(),
        **_patent_records(),
        historical_statuses=_historical_statuses(),
        adjacent_observations=(
            AdjacentObservationRecord(
                project_id="p-preclinical",
                relation_basis_zh="靶点与目标适应症机制相关，适应症关系未确立，独立观察",
                fact_version_id="fact-adjacent-1",
                source_location="literature/review-1",
            ),
        ),
    )
    dupilumab = view.dossier("project-dupilumab")
    # 临床组合
    assert {row.trial_id for row in dupilumab.clinical_rows} == {"NCT02407756"}
    assert {row.region for row in dupilumab.clinical_rows} == {"中国", "境外"}
    # 监管分轨：中国/境外分别保留，稳定事件 ID 可追溯
    assert {row.event_id for row in dupilumab.china_regulatory_events} == {"ev-approval-cn"}
    assert dupilumab.overseas_regulatory_events == ()
    # 企业角色/合作/交易/权益
    assert {row.organization_zh for row in dupilumab.organization_roles} == {"再生元", "赛诺菲"}
    assert dupilumab.relationships and dupilumab.geographic_rights
    assert dupilumab.transaction_events and dupilumab.public_terms
    # 专利/监管保护
    assert dupilumab.patent_families and dupilumab.patent_members
    assert dupilumab.patent_scopes and dupilumab.patent_terms
    assert {row.exclusivity_kind_zh for row in dupilumab.exclusivities} == {
        "数据独占",
        "孤儿药独占",
    }
    # 疗效/安全：第 5.1 步强类型绑定推导，非空解释文本
    assert dupilumab.core_efficacy_records
    assert dupilumab.safety_summary_records
    efficacy = dupilumab.core_efficacy_records[0]
    assert efficacy.definition and efficacy.direction and efficacy.unit
    assert efficacy.timepoint and efficacy.analysis_population and efficacy.treatment_group
    assert efficacy.denominator is not None and efficacy.reported_value
    safety = dupilumab.safety_summary_records[0]
    assert safety.event_definition and safety.time_window and safety.denominator
    # 稳定详情路由
    assert dupilumab.route == "/a/products/project-dupilumab"
    # 历史状态与边缘观察
    assert view.dossier("p-clinical").historical_statuses
    assert view.dossier("p-preclinical").adjacent_observations


# ── CE4 非核心试验不得凭自由记录进入临床组合 ───────────────────────────────


def test_non_core_trial_cannot_enter_clinical_portfolio(tmp_path) -> None:
    """默认排除：快照内但无合同核心角色证据的试验不得进入临床组合。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    # 快照新增一个不属于任何合同核心试验的对象（设计证据齐全但角色无证据）。
    snapshot_with_extra = _snapshot(
        product_ids=snapshot.product_ids,
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1", "NCT-extra"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
            "NCT-extra": "p-clinical",
        },
        evidence_snapshot_id=evidence.locked.snapshot_id,
    )
    records = (
        *_portfolio_records(),
        _region_record(
            project_id="p-clinical",
            trial_id="NCT-extra",
            region="中国",
            phase="I期",
            status="进行中",
            layer=ClinicalTrialLayer.CORE,
            fact_version_id="fact-clin",
        ),
    )
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            snapshot_with_extra,
            evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


def test_trial_layers_are_closed_and_consistent_with_contract_role(tmp_path) -> None:
    """分层语义封闭：注册/关键合同角色只允许核心/特殊核心分层。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    drifted = list(_portfolio_records())
    drifted[0] = _region_record(
        project_id="project-dupilumab",
        trial_id="NCT02407756",
        region="中国",
        phase="III期",
        status="已完成",
        layer=ClinicalTrialLayer.SUPPORTING,
        fact_version_id="fact-region-dup-cn",
    )
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            snapshot,
            evidence,
            bindings,
            tuple(drifted),
            authoritative_contract_store=evidence.contract_store,
        )


# ── CE5 监管事件按稳定不可变 event_id 精确绑定 ─────────────────────────────


def test_event_record_binds_by_stable_event_id(tmp_path) -> None:
    """类型/地域/日期一致但 event_id 不同的记录不得冒充合同事件。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    impostor = _event_record(
        project_id="p-terminated",
        event_id="ev-wrong-id",
        event_kind=RegulatoryEventKind.TERMINATION,
        jurisdiction="境外",
        event_date="2023-11-01",
        fact_version_id="fact-term-reg",
    )
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            (*_versioned_events(), impostor),
            authoritative_contract_store=evidence.contract_store,
        )


def test_contract_event_without_version_record_fails_closed(tmp_path) -> None:
    """合同事件缺少按 event_id 的版本化记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            _versioned_events()[:-1],
            authoritative_contract_store=evidence.contract_store,
        )


# ── CE6 历史状态必须与监管事件/产品成熟度闭合 ──────────────────────────────


def test_history_status_requires_matching_regulatory_event(tmp_path) -> None:
    """无对应监管事件的产品不得伪造撤回/终止/暂停/放弃历史状态。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    # dupilumab 只有批准事件，没有撤回事件：伪造撤回记录失败关闭。
    forged = HistoricalStatusRecord(
        project_id="project-dupilumab",
        regulatory_event_id="ev-withdraw-1",
        status_kind=HistoricalStatusKind.WITHDRAWN,
        jurisdiction="中国",
        status_date=_field(value="2024-02-10"),
        fact_version_id="fact-hist-withdraw",
        source_location="registry/status-history-4",
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            historical_statuses=(*_historical_statuses(), forged),
            adjacent_observations=(),
        )


def test_history_status_kind_must_match_event_kind(tmp_path) -> None:
    """状态类型必须与所引用监管事件类型一致：暂停事件不得支撑撤回状态。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    mismatched = HistoricalStatusRecord(
        project_id="p-clinical",
        regulatory_event_id="ev-pause-1",
        status_kind=HistoricalStatusKind.WITHDRAWN,
        jurisdiction="中国",
        status_date=_field(value="2023-03-01"),
        fact_version_id="fact-hist-suspend",
        source_location="registry/status-history-1",
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            historical_statuses=(*_historical_statuses(), mismatched),
            adjacent_observations=(),
        )


def test_history_status_rejects_nonexistent_event_reference(tmp_path) -> None:
    """历史状态引用不存在的稳定监管事件 ID 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = HistoricalStatusRecord(
        project_id="p-china-only",
        regulatory_event_id="ev-none",
        status_kind=HistoricalStatusKind.WITHDRAWN,
        jurisdiction="中国",
        status_date=_field(value="2024-02-10"),
        fact_version_id="fact-hist-withdraw",
        source_location="registry/status-history-4",
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            historical_statuses=(*_historical_statuses(), forged),
            adjacent_observations=(),
        )


def test_active_clinical_product_cannot_fabricate_terminal_status(tmp_path) -> None:
    """仍处于活跃临床开发的产品不得伪造终止/撤回/放弃状态。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    # p-clinical 为临床层；为其构造一个终止事件再伪造终止状态也不被接受。
    projects_with_event = [
        (
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
                        event_id="ev-term-clin",
                        event_kind=RegulatoryEventKind.TERMINATION,
                        jurisdiction=_field(value="中国"),
                        event_date=_field(value="2023-05-01"),
                    ),
                ),
                anchor_trials=(),
            )
            if project.project_id == "p-clinical"
            else project
        )
        for project in projects
    ]
    forged = HistoricalStatusRecord(
        project_id="p-clinical",
        regulatory_event_id="ev-term-clin",
        status_kind=HistoricalStatusKind.TERMINATED,
        jurisdiction="中国",
        status_date=_field(value="2023-05-01"),
        fact_version_id="fact-hist-suspend",
        source_location="registry/status-history-1",
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects_with_event,
            snapshot,
            evidence,
            bindings,
            historical_statuses=(*_historical_statuses(), forged),
            adjacent_observations=(),
            authoritative_contract_store=evidence.contract_store,
        )


def test_adjacent_observation_is_separate_from_regulatory_status(tmp_path) -> None:
    """相邻观察与正式监管状态分开：观察记录不携带监管事件引用。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_history_edge_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        historical_statuses=_historical_statuses(),
        adjacent_observations=(
            AdjacentObservationRecord(
                project_id="p-preclinical",
                relation_basis_zh="靶点与目标适应症机制相关，适应症关系未确立，独立观察",
                fact_version_id="fact-adjacent-1",
                source_location="literature/review-1",
            ),
        ),
    )
    preclinical = view.product("p-preclinical")
    assert preclinical.historical_statuses
    assert preclinical.adjacent_observations
    row = preclinical.adjacent_observations[0]
    assert "ev-" not in row.relation_basis_zh
    assert not hasattr(row, "regulatory_event_id")


# ── CE7 用户可见文本权威：拒绝程序员/日志语言，保留医学合理英文 ────────────


def test_user_facing_text_rejects_programmer_language(tmp_path) -> None:
    """prompt/log/backend_enum/下划线后台标识不得进入用户视图。"""
    with pytest.raises(ValidationError):
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh="prompt 相关机制观察",
            fact_version_id="fact-adjacent-1",
            source_location="literature/review-1",
        )
    with pytest.raises(ValidationError):
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh="机制观察 backend_enum",
            fact_version_id="fact-adjacent-1",
            source_location="literature/review-1",
        )
    with pytest.raises(ValidationError):
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh="机制观察_内部状态",
            fact_version_id="fact-adjacent-1",
            source_location="literature/review-1",
        )


def test_user_facing_text_allows_medical_english(tmp_path) -> None:
    """医学合理英文（药物名/靶点/机构/登记号）正常进入用户视图。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_product_overview_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    dupilumab = next(row for row in view.products if row.project_id == "project-dupilumab")
    assert "IL-4Rα" in dupilumab.target_mechanism
    assert "Dupixent" in dupilumab.aliases
    dossiers = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        trial_region_records=_portfolio_records(),
        versioned_events=_versioned_events(),
        **_company_records(),
        **_patent_records(),
        historical_statuses=_historical_statuses(),
        adjacent_observations=(
            AdjacentObservationRecord(
                project_id="p-preclinical",
                relation_basis_zh="靶点与目标适应症机制相关，适应症关系未确立，独立观察",
                fact_version_id="fact-adjacent-1",
                source_location="literature/review-1",
            ),
        ),
    )
    assert "NCT02407756" in {
        trial.trial_id for trial in dossiers.dossier("project-dupilumab").core_trials
    }


# ── CE8 视图作用域与渲染边界权威 ────────────────────────────────────────────


def test_complete_overview_view_rejects_empty_or_forged_rows(tmp_path) -> None:
    """直接构造/伪造的空或残缺完整总览不能成为权威输出。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_product_overview_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    identity = view.identity
    with pytest.raises(ValidationError):
        ProductOverviewView.model_validate(
            {
                "identity": identity,
                "products": (),
                "filter_options": view.filter_options,
                "view_scope": ViewScope.COMPLETE,
                "content_digest": "0" * 64,
            }
        )
    # 伪造内容摘要的手工 DTO：渲染边界权威校验拒绝。
    forged = ProductOverviewView.model_construct(
        identity=identity,
        products=view.products,
        filter_options=view.filter_options,
        view_scope=ViewScope.COMPLETE,
        content_digest="0" * 64,
    )
    with pytest.raises(GateEvaluationError):
        assert_product_overview_view_authoritative(
            forged,
            projects=projects,
            snapshot=snapshot,
            evidence=evidence,
            authoritative_contract_store=evidence.contract_store,
            bindings=bindings,
        )


def test_complete_portfolio_view_cannot_be_empty_or_subset(tmp_path) -> None:
    """完整临床组合视图必须等于锁定快照：空/残缺 DTO 失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_clinical_portfolio_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _portfolio_records(),
        authoritative_contract_store=evidence.contract_store,
    )
    with pytest.raises(ValidationError):
        ClinicalPortfolioView.model_validate(
            {
                "identity": view.identity,
                "products": (),
                "content_digest": "0" * 64,
            }
        )
    # 手工 DTO（产品子集）被渲染边界权威校验拒绝。
    forged = ClinicalPortfolioView.model_construct(
        identity=view.identity,
        products=view.products[:1],
        content_digest="0" * 64,
    )
    with pytest.raises(GateEvaluationError):
        assert_clinical_portfolio_view_authoritative(
            forged,
            projects=projects,
            snapshot=snapshot,
            evidence=evidence,
            authoritative_contract_store=evidence.contract_store,
            bindings=bindings,
            trial_region_records=_portfolio_records(),
        )


def test_render_boundary_accepts_current_views(tmp_path) -> None:
    """当前输入构建的视图通过渲染边界权威校验（正向对照）。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    landscape = build_landscape_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    assert_landscape_view_authoritative(
        landscape,
        projects=projects,
        snapshot=snapshot,
        evidence=evidence,
        authoritative_contract_store=evidence.contract_store,
        bindings=bindings,
    )
    overview = build_product_overview_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    assert_product_overview_view_authoritative(
        overview,
        projects=projects,
        snapshot=snapshot,
        evidence=evidence,
        authoritative_contract_store=evidence.contract_store,
        bindings=bindings,
    )
    regulatory = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _versioned_events(),
        authoritative_contract_store=evidence.contract_store,
    )
    assert_regulatory_view_authoritative(
        regulatory,
        projects=projects,
        snapshot=snapshot,
        evidence=evidence,
        authoritative_contract_store=evidence.contract_store,
        bindings=bindings,
        versioned_events=_versioned_events(),
    )
