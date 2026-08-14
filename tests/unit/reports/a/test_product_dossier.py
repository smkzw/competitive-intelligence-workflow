"""Task 5.2 AV02 产品总览 + AV03 逐产品档案失败测试。

合同断言（先失败后通过）：
- 产品总览为全量可筛选事实表：行集等于锁定快照且顺序稳定，无 Top-N；
  筛选选项由行数据闭合生成，未知筛选值失败关闭；筛选/排序不改变快照绑定；
- 每个产品有完整档案与稳定路由：档案集等于锁定快照，路由来自冻结目录
  动态路由模板，逐产品唯一且两次构建一致；未知产品查询失败关闭；
- 证据缺失用显式中文状态表达，不用空字符串或推断结论填补；
- 构建器不存在 Top-N/删除/降级参数，视图不可变且确定性。
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
    AEvidenceContext,
    ClinicalTrialLayer,
    ClinicalTrialRegionRecord,
    ProductDossierView,
    ProductOverviewSortKey,
    ProductOverviewView,
    RegulatoryEventVersionRecord,
    build_product_dossier_view,
    build_product_overview_view,
)
from ci_workflow.reports.common.evidence_view import EvidenceField, EvidenceFieldState


def _field(value: str | None = None, state: EvidenceFieldState | None = None) -> EvidenceField:
    return EvidenceField(value=value, state=state)


def _display(field: EvidenceField) -> str:
    """镜像视图语义：确定值原样，互斥状态用中文状态标签。"""
    if field.value is not None:
        return field.value
    assert field.state is not None
    from ci_workflow.reports.common.evidence_view import EVIDENCE_FIELD_STATE_LABELS_ZH

    return EVIDENCE_FIELD_STATE_LABELS_ZH[field.state]


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
        "fact-term-reg": (
            "p-terminated",
            "regulatory_event",
            "终止 2023-11-01 境外",
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
        "fact-region-dup-os": (
            "project-dupilumab",
            "clinical_trial_region",
            "III期 已完成 境外",
            "CT.gov/results/portfolio-1",
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
            regulatory_events=(),
            anchor_trials=(),
        ),
        _complete_project(
            project_id="p-preclinical",
            canonical_name="临床前示例药",
            core_trials=(),
            regulatory_events=(),
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
            regulatory_events=(),
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
    """覆盖锁定快照全部产品→试验关系：档案临床组合部分。"""
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


def _versioned_events() -> tuple[RegulatoryEventVersionRecord, ...]:
    """与合同监管事件按 event_id 精确对应的版本化事件。"""
    return (
        RegulatoryEventVersionRecord(
            project_id="project-dupilumab",
            event_id="ev-approval-cn",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction=_field(value="中国"),
            event_date=_field(value="2020-06-19"),
            fact_version_id="fact-reg",
            source_location="NMPA/approval-notice-2020",
        ),
        RegulatoryEventVersionRecord(
            project_id="p-terminated",
            event_id="ev-term-1",
            event_kind=RegulatoryEventKind.TERMINATION,
            jurisdiction=_field(value="境外"),
            event_date=_field(value="2023-11-01"),
            fact_version_id="fact-term-reg",
            source_location="NMPA/approval-notice-2020",
        ),
    )


def _analyzed(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    ProductOverviewView,
    ProductDossierView,
]:
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    overview = build_product_overview_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    dossiers = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        trial_region_records=_portfolio_records(),
        versioned_events=_versioned_events(),
    )
    return projects, snapshot, overview, dossiers


# ── AV02 精确验收节点 ───────────────────────────────────────────────────────


def test_product_overview_is_complete_filterable_and_not_top_n(tmp_path) -> None:
    """产品总览为全量可筛选事实表：完整、可筛选、无 Top-N。"""
    projects, snapshot, overview, _ = _analyzed(tmp_path)
    ids = tuple(row.project_id for row in overview.products)
    assert ids == snapshot.product_ids
    assert overview.total_products == len(snapshot.product_ids) == 5

    by_id = {project.project_id: project for project in projects}
    for row in overview.products:
        contract = by_id[row.project_id]
        assert row.canonical_name == contract.canonical_name
        assert row.target_mechanism == _display(contract.target_mechanism)
        assert row.modality == _display(contract.modality)
        assert row.developer == _display(contract.developer)
        assert row.originator == _display(contract.originator)
        assert row.indication_relation == _display(contract.indication_relation)
        assert row.china_stage == _display(contract.china.highest_stage)
        assert row.china_status == _display(contract.china.highest_status)
        assert row.china_date == _display(contract.china.date)
        assert row.overseas_stage == _display(contract.overseas.highest_stage)
        assert row.overseas_status == _display(contract.overseas.highest_status)
        assert row.overseas_date == _display(contract.overseas.date)
        assert row.lifecycle_zh
        assert row.development_status_zh
        assert row.route.startswith("/a/products/")

    # 筛选选项由行数据闭合生成，且覆盖视图内全部取值。
    assert overview.filter_options.targets == tuple(
        sorted({row.target_mechanism for row in overview.products})
    )
    assert overview.filter_options.modalities == tuple(
        sorted({row.modality for row in overview.products})
    )
    assert overview.filter_options.lifecycles == tuple(
        sorted({row.lifecycle_zh for row in overview.products})
    )
    assert overview.filter_options.development_statuses == tuple(
        sorted({row.development_status_zh for row in overview.products})
    )

    # 筛选只按注册维度值进行，结果仍绑定锁定快照身份。
    clinical = overview.filtered(lifecycle_zh="已进入临床开发阶段")
    assert [row.project_id for row in clinical.products] == ["p-clinical"]
    assert clinical.identity == overview.identity
    assert clinical.identity.product_ids == snapshot.product_ids

    china = overview.filtered(target="IL-4Rα 受体阻断", modality="单克隆抗体")
    assert {row.project_id for row in china.products} == {
        "project-dupilumab",
        "p-clinical",
        "p-preclinical",
        "p-terminated",
        "p-china-only",
    }
    assert china.identity == overview.identity

    # 无筛选时筛选结果等于原产品集；筛选子视图与完整视图作用域明确不同。
    assert overview.filtered().products == overview.products
    assert overview.filtered().view_scope != overview.view_scope
    assert overview.filtered(lifecycle_zh="已进入临床开发阶段").filter_options == (
        overview.filter_options
    )


# ── AV03 精确验收节点 ───────────────────────────────────────────────────────


def test_every_product_has_complete_dossier_and_stable_route(tmp_path) -> None:
    """每个产品都有完整档案，路由稳定、唯一且来自冻结目录模板。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    dossiers = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        trial_region_records=_portfolio_records(),
        versioned_events=_versioned_events(),
    )
    assert tuple(d.project_id for d in dossiers.dossiers) == snapshot.product_ids
    assert dossiers.total_products == len(snapshot.product_ids) == 5

    routes = [d.route for d in dossiers.dossiers]
    assert len(routes) == len(set(routes))
    assert all(route.startswith("/a/products/") for route in routes)
    for dossier in dossiers.dossiers:
        assert dossier.route == f"/a/products/{dossier.project_id}"

    by_id = {project.project_id: project for project in projects}
    for dossier in dossiers.dossiers:
        contract = by_id[dossier.project_id]
        assert dossier.canonical_name == contract.canonical_name
        assert dossier.aliases == contract.aliases
        assert dossier.aliases_absence_basis == contract.aliases_absence_basis
        assert dossier.identity_basis == contract.identity_basis
        assert dossier.target_mechanism == _display(contract.target_mechanism)
        assert dossier.modality == _display(contract.modality)
        assert dossier.developer == _display(contract.developer)
        assert dossier.originator == _display(contract.originator)
        assert dossier.indication_relation == _display(contract.indication_relation)
        assert dossier.china.highest_stage == _display(contract.china.highest_stage)
        assert dossier.china.highest_status == _display(contract.china.highest_status)
        assert dossier.china.date == _display(contract.china.date)
        assert dossier.overseas.highest_stage == _display(contract.overseas.highest_stage)
        assert dossier.overseas.highest_status == _display(contract.overseas.highest_status)
        assert dossier.overseas.date == _display(contract.overseas.date)
        assert dossier.lifecycle_zh
        assert dossier.development_status_zh
        trial_ids = [trial.trial_id for trial in dossier.core_trials]
        assert trial_ids == [record.trial_id for record in contract.core_trials]
        kinds = [event.kind_zh for event in dossier.regulatory_events]
        assert kinds == [
            _regulatory_kind_zh(record.event_kind) for record in contract.regulatory_events
        ]
        anchor_ids = [anchor.trial_id for anchor in dossier.anchor_trials]
        assert anchor_ids == [anchor.trial_id for anchor in contract.anchor_trials]

    # 同一锁定输入两次构建的档案完全一致（稳定路由与稳定身份）。
    second = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        trial_region_records=_portfolio_records(),
        versioned_events=_versioned_events(),
    )
    assert dossiers == second


def _regulatory_kind_zh(kind: RegulatoryEventKind) -> str:
    return {
        RegulatoryEventKind.SUBMISSION: "申报",
        RegulatoryEventKind.APPROVAL: "批准",
        RegulatoryEventKind.WITHDRAWAL: "撤回",
        RegulatoryEventKind.TERMINATION: "终止",
        RegulatoryEventKind.ABANDONMENT: "放弃",
        RegulatoryEventKind.PAUSE: "暂停",
    }[kind]


# ── 总览筛选/排序失败关闭与不变量 ───────────────────────────────────────────


def test_overview_filter_unknown_value_fails_closed(tmp_path) -> None:
    """未知筛选维度值失败关闭，不得静默返回空或伪造选项。"""
    _, _, overview, _ = _analyzed(tmp_path)
    with pytest.raises(GateEvaluationError):
        overview.filtered(lifecycle_zh="已上市")
    with pytest.raises(GateEvaluationError):
        overview.filtered(modality="基因治疗")
    with pytest.raises(GateEvaluationError):
        overview.filtered(indication_relation="不存在的关系")


def test_overview_sort_preserves_product_set(tmp_path) -> None:
    """排序只改变展示顺序，不改变产品集合与快照绑定。"""
    _, snapshot, overview, _ = _analyzed(tmp_path)
    for key in ProductOverviewSortKey:
        ordered = overview.sorted_by(key)
        assert {row.project_id for row in ordered.products} == set(snapshot.product_ids)
        assert ordered.identity == overview.identity
        assert ordered.filter_options == overview.filter_options
    by_name = overview.sorted_by(ProductOverviewSortKey.CANONICAL_NAME)
    names = [row.canonical_name for row in by_name.products]
    assert names == sorted(names)
    assert by_name.products != overview.products


def test_overview_and_dossiers_reject_unknown_or_missing_products(tmp_path) -> None:
    """未知/缺失产品在档案与总览均失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects[:-1],
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects[:-1],
            snapshot,
            evidence,
            bindings,
            trial_region_records=_portfolio_records(),
            versioned_events=_versioned_events(),
            authoritative_contract_store=evidence.contract_store,
        )
    extra = _complete_project(
        project_id="p-extra",
        canonical_name="多余药",
        core_trials=(),
        regulatory_events=(),
        anchor_trials=(),
    )
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            [*projects, extra],
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            [*projects, extra],
            snapshot,
            evidence,
            bindings,
            trial_region_records=_portfolio_records(),
            versioned_events=_versioned_events(),
            authoritative_contract_store=evidence.contract_store,
        )


def test_dossier_lookup_unknown_product_fails_closed(tmp_path) -> None:
    """档案查询未知产品失败关闭。"""
    _, _, _, dossiers = _analyzed(tmp_path)
    with pytest.raises(KeyError):
        dossiers.dossier("p-unknown")
    assert dossiers.dossier("p-clinical").canonical_name == "临床示例药"


def test_dossier_preserves_blocked_product_missing_evidence(tmp_path) -> None:
    """关键证据不足时权威档案视图拒绝生成（P0 阻断），阻断说明留在分析层。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    blocked = _complete_project(
        project_id="p-blocked",
        canonical_name="缺证据药",
        target_mechanism=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
        core_trials=(),
        regulatory_events=(),
        anchor_trials=(),
    )
    projects.append(blocked)
    trial_products = {
        "NCT02407756": "project-dupilumab",
        "NCT-clin-1": "p-clinical",
        "NCT-term-1": "p-terminated",
    }
    blocked_snapshot = _snapshot(
        product_ids=(
            "project-dupilumab",
            "p-clinical",
            "p-preclinical",
            "p-terminated",
            "p-china-only",
            "p-blocked",
        ),
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products=trial_products,
        evidence_snapshot_id=evidence.locked.snapshot_id,
    )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            blocked_snapshot,
            evidence,
            bindings,
            trial_region_records=_portfolio_records(),
            versioned_events=_versioned_events(),
            authoritative_contract_store=evidence.contract_store,
        )


def test_overview_preserves_explicit_missing_states_as_chinese_labels(tmp_path) -> None:
    """境外整组不适用必须显式表达为中文状态，不得用空字符串填补。"""
    _, _, overview, dossiers = _analyzed(tmp_path)
    row = next(row for row in overview.products if row.project_id == "p-china-only")
    assert row.overseas_stage == "不适用"
    assert row.overseas_status == "不适用"
    assert row.overseas_date == "不适用"
    dossier = dossiers.dossier("p-china-only")
    assert dossier.overseas.highest_stage == "不适用"
    assert dossier.overseas.highest_status == "不适用"
    assert dossier.overseas.date == "不适用"


def test_overview_and_dossier_builders_have_no_top_n_parameters(tmp_path) -> None:
    """总览与档案构建器不存在 Top-N、删除或降级出口。"""
    assert set(inspect.signature(build_product_overview_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "results_posted_evidence",
    }
    assert set(inspect.signature(build_product_dossier_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "trial_region_records",
        "versioned_events",
        "organization_roles",
        "relationships",
        "geographic_rights",
        "transaction_events",
        "public_terms",
        "families",
        "members",
        "scopes",
        "terms",
        "exclusivities",
        "historical_statuses",
        "adjacent_observations",
        "results_posted_evidence",
    }


def test_overview_and_dossier_views_are_immutable(tmp_path) -> None:
    """总览与档案视图不可变：行字段不可改写。"""
    _, _, overview, dossiers = _analyzed(tmp_path)
    with pytest.raises(ValidationError):
        overview.products[0].canonical_name = "改写"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        dossiers.dossiers[0].canonical_name = "改写"  # type: ignore[misc]
