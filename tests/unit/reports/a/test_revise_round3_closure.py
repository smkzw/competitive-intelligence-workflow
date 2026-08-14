"""Task 5.2 第 3 轮（Luna round 2）反例回归：P0/P1-A/P1-B/P1-C/P1-D/P1-E/P2。

每类反例在修复前可复现（Luna round 2 报告给出最小构造）；本文件把每个可运行
反例原样转成回归测试，作为本轮修复的验收面。不做字符串黑名单扩张、不打补丁。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from _evidence_factory import build_evidence_context

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    GateEvaluationError,
    GateEvidenceBinding,
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
    ClinicalTrialLayer,
    ClinicalTrialRegionRecord,
    HistoricalStatusKind,
    HistoricalStatusRecord,
    RegulatoryEventVersionRecord,
    assert_clinical_portfolio_view_authoritative,
    assert_company_deal_view_authoritative,
    assert_history_edge_view_authoritative,
    assert_landscape_view_authoritative,
    assert_patent_protection_view_authoritative,
    assert_product_dossier_view_authoritative,
    assert_product_overview_view_authoritative,
    assert_regulatory_view_authoritative,
    build_clinical_portfolio_view,
    build_company_deal_view,
    build_history_edge_view,
    build_landscape_view,
    build_patent_protection_view,
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
    evidence_snapshot_id: str,
    schema_version: str = "1.0",
    enumeration_complete: bool = True,
) -> ApplicableUniverseSnapshot:
    from ci_workflow.gates.models import (
        EmptySetProof,
        EmptySetReasonCode,
        GateObjectType,
        TrialDesignEvidence,
        TrialDesignKind,
        UniverseEdge,
        compute_universe_summary,
    )

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
    return ApplicableUniverseSnapshot.model_construct(
        **{
            "schema_version": schema_version,
            "project_id": "report-universe",
            "evidence_snapshot_id": evidence_snapshot_id,
            "research_role_set_id": "role-set-1",
            "product_ids": product_ids,
            "trial_ids": trial_ids,
            "comparison_ids": (),
            "group_ids": (),
            "endpoint_ids": (),
            "timepoint_ids": (),
            "empty_set_proofs": empty_proofs,
            "relationship_edges": edges,
            "trial_design_evidence": trial_design_evidence,
            "indication_rule_set_id": "ind-rule-1",
            "applicable_conditional_predicates": ("termination-rule-1",),
            "universe_summary": summary,
            "enumeration_complete": enumeration_complete,
        }
    )


def _binding(
    *,
    binding_id: str,
    object_id: str,
    trial_id: str | None,
    fact_version_id: str,
    unit_id: str = "a-unit-1",
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
    source_role: str = "primary_trial_report",
    source_location: str | None = "CT.gov/results/table-1",
    applicability_predicate_id: str | None = None,
    review_state: FactReviewState = FactReviewState.ACCEPTED,
    fact_domain: str = "efficacy",
) -> GateEvidenceBinding:
    from ci_workflow.gates.models import (
        ConflictDisposition,
        DisclosureMaturity,
        FactDomain,
        ObservationKind,
        SourceRole,
    )

    return GateEvidenceBinding(
        binding_id=binding_id,
        unit_id=unit_id,
        object_id=object_id,
        fact_version_id=fact_version_id,
        trial_id=trial_id,
        fact_domain=FactDomain(fact_domain),
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
        source_role=SourceRole(source_role),
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
            "首付款 2 亿美元,里程碑付款最高 10 亿美元",
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
            "靶点与目标适应症机制相关,适应症关系未确立,独立观察",
            "literature/review-1",
        ),
        "study-role-nct1": ("NCT02407756", "study_role", "注册/关键", "CT.gov/results/role-1"),
        "study-role-clin": ("NCT-clin-1", "study_role", "注册/关键", "CT.gov/results/role-2"),
        "study-role-term": ("NCT-term-1", "study_role", "特殊核心", "CT.gov/results/role-3"),
    }


def _universe(
    tmp_path, *, blocked: bool = False
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    tuple[GateEvidenceBinding, ...],
    AEvidenceContext,
]:
    projects = [
        _complete_project(),
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
    if blocked:
        projects[0] = _complete_project(
            target_mechanism=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED)
        )
    bindings = (
        _binding(
            binding_id="b-reg",
            object_id="project-dupilumab",
            trial_id="NCT02407756",
            fact_version_id="fact-reg",
            source_role="regulatory_material",
            numeric_value=None,
            unit=None,
            denominator=None,
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
            fact_domain="safety",
            numeric_value=52.3,
            unit="%",
            denominator=224,
            definition=None,
            direction=None,
            timepoint=None,
            analysis_population="意向治疗集",
            treatment_group="度普利尤单抗 300mg 每两周",
            event_definition="治疗期间不良事件",
            time_window="治疗期间",
        ),
        _binding(
            binding_id="b-clin",
            object_id="p-clinical",
            trial_id="NCT-clin-1",
            fact_version_id="fact-clin",
            numeric_value=None,
            unit=None,
            denominator=None,
            definition="随机对照试验设计",
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
            source_role="protocol_sap",
        ),
        _binding(
            binding_id="b-term-design",
            object_id="p-terminated",
            trial_id="NCT-term-1",
            fact_version_id="fact-term-design",
            numeric_value=None,
            unit=None,
            denominator=None,
            definition="随机对照试验设计",
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
            source_role="protocol_sap",
        ),
        _binding(
            binding_id="b-term-reg",
            unit_id="a_regulatory_termination",
            object_id="p-terminated",
            trial_id=None,
            fact_version_id="fact-term-reg",
            source_role="regulatory_material",
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
                term_zh="首付款 2 亿美元,里程碑付款最高 10 亿美元",
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


def _adjacent_observations() -> tuple[AdjacentObservationRecord, ...]:
    return (
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh="靶点与目标适应症机制相关,适应症关系未确立,独立观察",
            fact_version_id="fact-adjacent-1",
            source_location="literature/review-1",
        ),
    )


def kwargs_for_authority(authority) -> dict[str, object]:
    if authority is assert_product_dossier_view_authoritative:
        return _all_record_kwargs()
    if authority is assert_clinical_portfolio_view_authoritative:
        return {"trial_region_records": _portfolio_records()}
    if authority is assert_regulatory_view_authoritative:
        return {"versioned_events": _versioned_events()}
    if authority is assert_company_deal_view_authoritative:
        return dict(_company_records())
    if authority is assert_patent_protection_view_authoritative:
        return dict(_patent_records())
    if authority is assert_history_edge_view_authoritative:
        return {
            "historical_statuses": _historical_statuses(),
            "adjacent_observations": _adjacent_observations(),
        }
    return {}


def _kwargs_for(builder) -> dict[str, object]:
    if builder is build_clinical_portfolio_view:
        return {"trial_region_records": _portfolio_records()}
    if builder is build_regulatory_view:
        return {"versioned_events": _versioned_events()}
    if builder is build_company_deal_view:
        return dict(_company_records())
    if builder is build_patent_protection_view:
        return dict(_patent_records())
    if builder is build_history_edge_view:
        return {
            "historical_statuses": _historical_statuses(),
            "adjacent_observations": _adjacent_observations(),
        }
    if builder is build_product_dossier_view:
        return _all_record_kwargs()
    return {}


def _all_record_kwargs() -> dict[str, object]:
    return {
        "trial_region_records": _portfolio_records(),
        "versioned_events": _versioned_events(),
        **_company_records(),
        **_patent_records(),
        "historical_statuses": _historical_statuses(),
        "adjacent_observations": _adjacent_observations(),
    }


# ── P0 关键证据阻断时绝不生成 ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "builder",
    [
        build_landscape_view,
        build_product_overview_view,
        build_product_dossier_view,
        build_clinical_portfolio_view,
        build_regulatory_view,
        build_company_deal_view,
        build_patent_protection_view,
        build_history_edge_view,
    ],
)
def test_builders_reject_when_report_not_ready(tmp_path, builder) -> None:
    """任一产品关键证据不足（report_ready=False）时，全部权威门户视图拒绝生成。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path, blocked=True)
    with pytest.raises(GateEvaluationError):
        builder(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **_kwargs_for(builder),
        )


@pytest.mark.parametrize(
    "authority",
    [
        assert_landscape_view_authoritative,
        assert_product_overview_view_authoritative,
        assert_product_dossier_view_authoritative,
        assert_clinical_portfolio_view_authoritative,
        assert_regulatory_view_authoritative,
        assert_company_deal_view_authoritative,
        assert_patent_protection_view_authoritative,
        assert_history_edge_view_authoritative,
    ],
)
def test_authority_rejects_blocked_context(tmp_path, authority) -> None:
    """渲染权威边界同样拒绝关键证据不足的项目上下文。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path, blocked=True)
    with pytest.raises(GateEvaluationError):
        authority(
            None,  # type: ignore[arg-type]
            projects=projects,
            snapshot=snapshot,
            evidence=evidence,
            authoritative_contract_store=evidence.contract_store,
            bindings=bindings,
            **kwargs_for_authority(authority),
        )


def test_blocked_universe_has_no_draft_with_not_yet_disclosed(tmp_path) -> None:
    """阻断宇宙不得生成含'尚未公开'的草稿总览。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path, blocked=True)
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


# ── P1-A 权威项目合同与内容寻址快照 ─────────────────────────────────────────


def test_tampered_locked_sha256_rejected(tmp_path) -> None:
    """篡改锁定快照 sha256/relative_path/byte_size 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = evidence.model_copy(
        update={"locked": evidence.locked.model_copy(update={"sha256": "0" * 64})}
    )
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )
    forged = evidence.model_copy(
        update={"locked": evidence.locked.model_copy(update={"relative_path": "forged.json"})}
    )
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )
    forged = evidence.model_copy(
        update={"locked": evidence.locked.model_copy(update={"byte_size": 1})}
    )
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )


def test_tampered_manifest_contract_version_rejected(tmp_path) -> None:
    """篡改 manifest contract_version 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = evidence.model_copy(
        update={"manifest": evidence.manifest.model_copy(update={"contract_version": 999})}
    )
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )


def test_tampered_manifest_data_cutoff_rejected(tmp_path) -> None:
    """篡改 manifest data_cutoff（含未来日期）必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = evidence.model_copy(
        update={
            "manifest": evidence.manifest.model_copy(
                update={"data_cutoff": datetime(2099, 1, 1, tzinfo=UTC)}
            )
        }
    )
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )


def test_tampered_project_contract_version_rejected(tmp_path) -> None:
    """篡改项目合同 contract_version 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = evidence.model_copy(
        update={
            "project_contract": evidence.project_contract.model_copy(update={"contract_version": 7})
        }
    )
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )


def test_tampered_project_contract_cutoff_rejected(tmp_path) -> None:
    """篡改项目合同 data_cutoff 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = evidence.model_copy(
        update={
            "project_contract": evidence.project_contract.model_copy(
                update={"data_cutoff": datetime(2099, 1, 1, tzinfo=UTC)}
            )
        }
    )
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )


# ── P1-B 所有公共输入重新验证 ───────────────────────────────────────────────


def test_forged_eligibility_excluded_rejected(tmp_path) -> None:
    """AProjectContract.model_copy 把 eligibility 改成 excluded 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = [
        (
            project.model_copy(update={"eligibility": "excluded"})
            if project.project_id == "project-dupilumab"
            else project
        )
        for project in projects
    ]
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            forged,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_forged_snapshot_schema_version_rejected(tmp_path) -> None:
    """ApplicableUniverseSnapshot.model_construct(schema_version=9.9) 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _snapshot(
        product_ids=snapshot.product_ids,
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
        },
        evidence_snapshot_id=evidence.locked.snapshot_id,
        schema_version="9.9",
    )
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects,
            forged,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_forged_unregistered_binding_rejected(tmp_path) -> None:
    """GateEvidenceBinding.model_copy 指向未注册事实版本必须失败关闭（所有视图）。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = tuple(
        (
            binding.model_copy(update={"fact_version_id": "fact-not-registered"})
            if binding.binding_id == "b-eff"
            else binding
        )
        for binding in bindings
    )
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects,
            snapshot,
            evidence,
            forged,
            authoritative_contract_store=evidence.contract_store,
        )


def test_forged_binding_missing_state_with_value_rejected(tmp_path) -> None:
    """model_construct 的'未报告却带数值'非法绑定必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    from ci_workflow.gates.models import (
        ConflictDisposition,
        DisclosureMaturity,
        FactDomain,
        ObservationKind,
        SourceRole,
    )

    forged = GateEvidenceBinding.model_construct(
        binding_id="b-forged",
        unit_id="a-unit-1",
        object_id="project-dupilumab",
        fact_version_id="fact-v-1",
        trial_id="NCT02407756",
        fact_domain=FactDomain.EFFICACY,
        observation_kind=ObservationKind.OBSERVED_RESULT,
        numeric_value=52.3,
        denominator=0,
        source_location="CT.gov/results/table-1",
        review_state=FactReviewState.ACCEPTED,
        disclosure_state=FactDisclosureState.NOT_REPORTED,
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
    )
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects,
            snapshot,
            evidence,
            (*bindings, forged),
            authoritative_contract_store=evidence.contract_store,
        )


def test_forged_registry_raw_value_rejected(tmp_path) -> None:
    """ScientificLineageRegistry.model_copy 篡改事实原文但保留 ID 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    tampered_fact = next(
        f for f in evidence.registry.accepted_facts if f.fact_version_id == "fact-reg"
    ).model_copy(update={"raw_value": "已撤回"})
    tampered_registry = evidence.registry.model_copy(
        update={
            "accepted_facts": tuple(
                tampered_fact if f.fact_version_id == "fact-reg" else f
                for f in evidence.registry.accepted_facts
            )
        }
    )
    forged = evidence.model_copy(update={"registry": tampered_registry})
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            forged,
            bindings,
            _versioned_events(),
            authoritative_contract_store=forged.contract_store,
        )


# ── P1-C 展示值必须由事实值支持 ─────────────────────────────────────────────


def test_tampered_region_display_rejected(tmp_path) -> None:
    """同一事实，阶段/状态改为 I期/进行中 必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    records = list(_portfolio_records())
    records[0] = _region_record(
        project_id="project-dupilumab",
        trial_id="NCT02407756",
        region="中国",
        phase="I期",
        status="进行中",
        layer=ClinicalTrialLayer.CORE,
        fact_version_id="fact-region-dup-cn",
    )
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            snapshot,
            evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


def test_tampered_org_name_rejected(tmp_path) -> None:
    """同一事实，组织名改为'伪造企业'必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    from ci_workflow.reports.a.pages import CompanyRoleKind, OrganizationRoleRecord

    records = dict(_company_records())
    records["organization_roles"] = (
        OrganizationRoleRecord(
            project_id="project-dupilumab",
            organization_zh="伪造企业",
            role=CompanyRoleKind.ORIGINATOR,
            fact_version_id="fact-org-origin",
            source_location="company/press-release-1",
        ),
        *records["organization_roles"][1:],
    )
    with pytest.raises(GateEvaluationError):
        build_company_deal_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **records,
        )


def test_tampered_patent_expiry_rejected(tmp_path) -> None:
    """同一事实，专利到期日改为 2099-12-31 必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    from ci_workflow.reports.a.pages import PatentTermRecord

    records = dict(_patent_records())
    records["terms"] = (
        PatentTermRecord(
            project_id="project-dupilumab",
            member_id="member-us-1",
            term_zh="自申请日起 20 年",
            expiry=_field(value="2099-12-31"),
            fact_version_id="fact-term-us",
            source_location="USPTO/status-1",
        ),
        *records["terms"][1:],
    )
    with pytest.raises(GateEvaluationError):
        build_patent_protection_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **records,
        )


def test_tampered_history_date_rejected(tmp_path) -> None:
    """同一事实，历史状态日期改为 2099-12-31 必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    statuses = list(_historical_statuses())
    statuses[0] = HistoricalStatusRecord(
        project_id="p-clinical",
        regulatory_event_id="ev-pause-1",
        status_kind=HistoricalStatusKind.SUSPENDED,
        jurisdiction="中国",
        status_date=_field(value="2099-12-31"),
        fact_version_id="fact-hist-suspend",
        source_location="registry/status-history-1",
    )
    with pytest.raises(GateEvaluationError):
        build_history_edge_view(
            projects,
            snapshot,
            evidence,
            bindings,
            historical_statuses=tuple(statuses),
            authoritative_contract_store=evidence.contract_store,
            adjacent_observations=_adjacent_observations(),
        )


def test_tampered_efficacy_value_rejected(tmp_path) -> None:
    """同一 fact ID，疗效摘要改为 999.9 伪造单位 必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged_bindings = tuple(
        (
            b.model_copy(update={"numeric_value": 999.9, "unit": "伪造单位"})
            if b.binding_id == "b-eff"
            else b
        )
        for b in bindings
    )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged_bindings,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


def test_tampered_safety_value_rejected(tmp_path) -> None:
    """同一 fact ID，安全摘要改为 0.1 伪造安全单位 必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged_bindings = tuple(
        (
            b.model_copy(update={"numeric_value": 0.1, "unit": "伪造安全单位"})
            if b.binding_id == "b-saf"
            else b
        )
        for b in bindings
    )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged_bindings,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


def test_same_fact_for_two_events_rejected(tmp_path) -> None:
    """不同监管 event_id 不得复用同一事实版本。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    events = (
        *_versioned_events(),
        _event_record(
            project_id="project-dupilumab",
            event_id="ev-approval-cn-dup",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction="中国",
            event_date="2020-06-19",
            fact_version_id="fact-reg",
        ),
    )
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            events,
            authoritative_contract_store=evidence.contract_store,
        )


def test_same_fact_for_conflicting_records_rejected(tmp_path) -> None:
    """同一事实版本不得支撑两个相互独立/冲突的页面记录。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    company = _company_records()
    from ci_workflow.reports.a.pages import CompanyRoleKind, OrganizationRoleRecord

    company["organization_roles"] = (
        *company["organization_roles"],
        OrganizationRoleRecord(
            project_id="project-dupilumab",
            organization_zh="伪造第二企业",
            role=CompanyRoleKind.DEVELOPER,
            fact_version_id="fact-org-origin",
            source_location="company/press-release-1",
        ),
    )
    with pytest.raises(GateEvaluationError):
        build_company_deal_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **company,
        )


# ── P1-D 完整档案是当前证据的完整投影 ───────────────────────────────────────


def test_dossier_omitting_company_records_rejected(tmp_path) -> None:
    """registry 已有企业事实而调用方省略企业记录，完整档案必须失败。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    kwargs = _all_record_kwargs()
    kwargs.pop("organization_roles")
    kwargs.pop("relationships")
    kwargs.pop("geographic_rights")
    kwargs.pop("transaction_events")
    kwargs.pop("public_terms")
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **kwargs,
        )


def test_dossier_omitting_patent_records_rejected(tmp_path) -> None:
    """registry 已有专利事实而调用方省略专利记录，完整档案必须失败。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    kwargs = _all_record_kwargs()
    kwargs.pop("families")
    kwargs.pop("members")
    kwargs.pop("scopes")
    kwargs.pop("terms")
    kwargs.pop("exclusivities")
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **kwargs,
        )


def test_dossier_omitting_history_records_rejected(tmp_path) -> None:
    """registry 已有历史事实而调用方省略历史记录，完整档案必须失败。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    kwargs = _all_record_kwargs()
    kwargs.pop("historical_statuses")
    kwargs.pop("adjacent_observations")
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **kwargs,
        )


def test_dossier_omitting_one_region_record_rejected(tmp_path) -> None:
    """registry 已有临床组合事实而调用方漏一条记录，完整档案必须失败。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    kwargs = _all_record_kwargs()
    kwargs["trial_region_records"] = _portfolio_records()[:-1]
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
            **kwargs,
        )


# ── P1-E 试验角色证据 ────────────────────────────────────────────────────────


def test_early_decision_other_eligible_without_special_core_fact_rejected(tmp_path) -> None:
    """EARLY_DECISION 不得无条件映射为其他适格：无'特殊核心'事实即拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    records = tuple(
        _region_record(
            project_id="p-terminated",
            trial_id="NCT-term-1",
            region="境外",
            phase="II期",
            status="已终止",
            layer=ClinicalTrialLayer.OTHER_ELIGIBLE,
            fact_version_id="fact-term-design",
        )
        if record.trial_id == "NCT-term-1"
        else record
        for record in _portfolio_records()
    )
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            snapshot,
            evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


def test_early_decision_special_core_requires_fact(tmp_path) -> None:
    """EARLY_DECISION 只有独立事实明确支持'特殊核心'时才进入 SPECIAL_CORE。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    # 移除 p-terminated 的 study-role 事实：无证据默认排除。
    facts = dict(_facts())
    facts.pop("study-role-term")
    missing_evidence = build_evidence_context(tmp_path, project_id="report-universe", facts=facts)
    missing_snapshot = _snapshot(
        product_ids=snapshot.product_ids,
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
        },
        evidence_snapshot_id=missing_evidence.locked.snapshot_id,
    )
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            missing_snapshot,
            missing_evidence,
            bindings,
            _portfolio_records(),
            authoritative_contract_store=missing_evidence.contract_store,
        )


def test_special_core_layer_accepted_with_fact(tmp_path) -> None:
    """EARLY_DECISION + '特殊核心'事实 → SPECIAL_CORE 正常接受（正向）。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_clinical_portfolio_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _portfolio_records(),
        authoritative_contract_store=evidence.contract_store,
    )
    terminated = view.product("p-terminated")
    assert any(row.layer_zh == "特殊核心" for row in terminated.trial_rows)


# ── P2 中文用户文本规范化 ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "banned",
    [
        "Gate",
        "BackendState",
        "back-end",
        "back\u200bend",
        "\uff42\uff41\uff43\uff4b\uff45\uff4e\uff44",
        "model-copy",
        "prompt",
        "backend_state",
    ],
)
def test_engineering_word_variants_rejected(banned: str) -> None:
    """工程词变体（大小写/camel-case/连字符/零宽/全角/下划线）必须拒绝。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AdjacentObservationRecord(
            project_id="p-preclinical",
            relation_basis_zh=f"机制观察 {banned} 相关内容",
            fact_version_id="fact-adjacent-1",
            source_location="literature/review-1",
        )


@pytest.mark.parametrize(
    "allowed",
    ["Dupixent", "IL-4Rα", "NCT02407756", "Novartis", "aggregate", "度普利尤单抗"],
)
def test_medical_english_and_normal_words_allowed(allowed: str) -> None:
    """医学合理英文与正常词（含 aggregate 子串 gate）必须通过。"""
    record = AdjacentObservationRecord(
        project_id="p-preclinical",
        relation_basis_zh=f"机制观察 {allowed} 相关内容",
        fact_version_id="fact-adjacent-1",
        source_location="literature/review-1",
    )
    assert allowed in record.relation_basis_zh
