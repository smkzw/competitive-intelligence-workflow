"""Task 5.2 AV04 临床组合视图 + 版本化扩展记录失败测试。

合同断言（先失败后通过）：
- 临床组合视图绑定单一锁定快照身份，产品集必须与 ``snapshot.product_ids``
  精确一一对应且顺序一致；缺失、重复、多余或顺序漂移失败关闭；
- 每一条产品—试验—地域组合记录必须是版本化扩展记录：绑定产品与试验，
  携带地域、阶段、状态、核心角色、不可变事实版本与精确来源定位；
- 未知产品、未知试验、跨产品引用试验、同一产品—试验—地域组合重复、
  与产品合同核心角色不一致均失败关闭；
- 关系闭合：视图必须恰好覆盖锁定快照内全部产品→试验关系，缺失或多余
  记录均失败关闭；
- 临床前等无试验产品保留空组合（显式空集合，不失败、不删除）；
- 视图为不可变、确定性纯投影：无 Top-N/删除/降级参数。
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
    ClinicalPortfolioView,
    ClinicalTrialLayer,
    ClinicalTrialRegionRecord,
    build_clinical_portfolio_view,
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
            "clinical_trial_region",
            "III期 已完成 中国",
            "CT.gov/results/portfolio-1",
        ),
        "fact-v-1-overseas": (
            "project-dupilumab",
            "clinical_trial_region",
            "III期 已完成 境外",
            "CT.gov/results/portfolio-1",
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
        "fact-term-reg": (
            "p-terminated",
            "regulatory_event",
            "终止 2023-11-01 境外",
            "NMPA/approval-notice-2020",
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
    fact_version_id: str = "fact-v-1",
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
    """覆盖锁定快照全部产品→试验关系：关系闭合的版本化临床组合记录。"""
    return (
        _region_record(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            region="中国",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
        ),
        _region_record(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            region="境外",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
            fact_version_id="fact-v-1-overseas",
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


def _portfolio_universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    AEvidenceContext,
    ClinicalPortfolioView,
]:
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    view = build_clinical_portfolio_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _portfolio_records(),
        authoritative_contract_store=evidence.contract_store,
    )
    return projects, snapshot, evidence, view


# ── AV04 精确验收节点 ───────────────────────────────────────────────────────


def test_clinical_portfolio_preserves_product_trial_region_phase_and_status(tmp_path) -> None:
    """临床组合保留产品—试验—地域—阶段—状态与核心角色，关系闭合。"""
    projects, snapshot, _, view = _portfolio_universe(tmp_path)
    assert tuple(product.project_id for product in view.products) == snapshot.product_ids

    by_id = {project.project_id: project for project in projects}
    dupilumab = view.products[0]
    assert dupilumab.project_id == "project-dupilumab"
    assert dupilumab.canonical_name == by_id["project-dupilumab"].canonical_name
    assert tuple((row.trial_id, row.region) for row in dupilumab.trial_rows) == (
        ("NCT02407756", "中国"),
        ("NCT02407756", "境外"),
    )
    for row in dupilumab.trial_rows:
        assert row.phase == "III期"
        assert row.status == "已完成"
        assert row.layer_zh == "注册/关键"
        assert row.fact_version_id
        assert row.source_location

    clinical = next(p for p in view.products if p.project_id == "p-clinical")
    assert tuple(
        (row.trial_id, row.region, row.phase, row.status, row.layer_zh)
        for row in clinical.trial_rows
    ) == (("NCT-clin-1", "中国", "II期", "进行中", "注册/关键"),)
    terminated = next(p for p in view.products if p.project_id == "p-terminated")
    assert tuple(
        (row.trial_id, row.region, row.phase, row.status, row.layer_zh)
        for row in terminated.trial_rows
    ) == (("NCT-term-1", "境外", "II期", "已终止", "特殊核心"),)
    # 临床前/仅中国产品保留空组合：显式空集合，不失败、不删除。
    for product in view.products:
        if product.project_id in ("p-preclinical", "p-china-only"):
            assert product.trial_rows == ()


# ── 版本化记录：未知产品/试验、跨产品、重复、角色漂移 ──────────────────────


def test_portfolio_rejects_unknown_product_record(tmp_path) -> None:
    """临床组合记录引用未知产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = (
        *_portfolio_records(),
        _region_record(
            project_id="p-extra",
            trial_id="NCT02407756",
            region="境外",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
        ),
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


def test_portfolio_rejects_unknown_trial_record(tmp_path) -> None:
    """临床组合记录引用未知试验必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = (
        *_portfolio_records(),
        _region_record(
            project_id="project-dupilumab",
            trial_id="NCT-unknown",
            region="境外",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
        ),
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


def test_portfolio_rejects_cross_product_trial_record(tmp_path) -> None:
    """临床组合记录跨产品引用其他产品的试验必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = (
        *_portfolio_records(),
        _region_record(
            project_id="p-clinical",
            trial_id="NCT02407756",  # 属于 project-dupilumab
            region="境外",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
        ),
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


def test_portfolio_rejects_duplicate_region_record(tmp_path) -> None:
    """同一产品—试验—地域组合重复必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    duplicate = _region_record(
        project_id="p-clinical",
        trial_id="NCT-clin-1",
        region="中国",
        phase="II期",
        status="进行中",
        layer=ClinicalTrialLayer.CORE,
        fact_version_id="fact-clin-dup",
    )
    records = (*_portfolio_records(), duplicate)
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            snapshot,
            evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


def test_portfolio_rejects_role_drift_from_contract(tmp_path) -> None:
    """记录分层与产品合同核心试验角色不一致必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    drifted = list(_portfolio_records())
    # p-clinical 合同角色为注册/关键，分层改为支持性（越权）。
    drifted[2] = _region_record(
        project_id="p-clinical",
        trial_id="NCT-clin-1",
        region="中国",
        phase="II期",
        status="进行中",
        layer=ClinicalTrialLayer.SUPPORTING,
        fact_version_id="fact-clin",
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


def test_portfolio_rejects_missing_trial_coverage(tmp_path) -> None:
    """关系闭合：缺少快照内任一产品→试验记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            snapshot,
            evidence,
            bindings,
            _portfolio_records()[:-1],
            authoritative_contract_store=evidence.contract_store,
        )


def test_portfolio_rejects_blank_version_or_locator(tmp_path) -> None:
    """版本化记录不得携带空白事实版本或来源定位。"""
    with pytest.raises(ValidationError):
        ClinicalTrialRegionRecord(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            region="中国",
            phase=_field(value="III期"),
            status=_field(value="已完成"),
            layer=ClinicalTrialLayer.CORE,
            fact_version_id="   ",
            source_location="CT.gov/results/portfolio-1",
        )
    with pytest.raises(ValidationError):
        ClinicalTrialRegionRecord(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            region="中国",
            phase=_field(value="III期"),
            status=_field(value="已完成"),
            layer=ClinicalTrialLayer.CORE,
            fact_version_id="fact-v-1",
            source_location="",
        )


def test_portfolio_record_rejects_unknown_region(tmp_path) -> None:
    """地域只接受中国/境外分轨，其余值必须失败关闭。"""
    with pytest.raises(ValidationError):
        _region_record(
            project_id="project-dupilumab",
            trial_id="NCT02407756",
            region="全球",
            phase="III期",
            status="已完成",
            layer=ClinicalTrialLayer.CORE,
        )


# ── 视图不变量：不可变、确定性、无 Top-N 参数 ───────────────────────────────


def test_build_clinical_portfolio_has_no_top_n_or_drop_parameters() -> None:
    """临床组合构建器不存在 Top-N、删除或降级出口。"""
    assert set(inspect.signature(build_clinical_portfolio_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "trial_region_records",
        "results_posted_evidence",
    }


def test_clinical_portfolio_view_is_immutable_and_deterministic(tmp_path) -> None:
    """视图不可变：行不可改写，同输入两次构建结果一致。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    first = build_clinical_portfolio_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _portfolio_records(),
        authoritative_contract_store=evidence.contract_store,
    )
    second = build_clinical_portfolio_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _portfolio_records(),
        authoritative_contract_store=evidence.contract_store,
    )
    assert first == second
    with pytest.raises(ValidationError):
        first.products[0].trial_rows[0].phase = "改写"


def test_clinical_portfolio_preserves_explicit_missing_states(tmp_path) -> None:
    """阶段/状态缺失用显式中文状态表达，不得用空字符串填补；展示值必须
    由事实原文支持（事实原文携带显式状态）。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    # 构造携带显式缺失状态的证据上下文：p-clinical 的临床组合事实原文即
    # "尚未公开 进行中 中国"（展示值与事实精确一致）。
    facts = dict(_facts())
    facts["fact-clin"] = (
        "p-clinical",
        "clinical_trial_region",
        "尚未公开 进行中 中国",
        "CT.gov/results/portfolio-1",
    )
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
    records = tuple(
        record
        for record in _portfolio_records()
        if not (record.project_id == "p-clinical" and record.trial_id == "NCT-clin-1")
    )
    record = ClinicalTrialRegionRecord(
        project_id="p-clinical",
        trial_id="NCT-clin-1",
        region="中国",
        phase=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
        status=_field(value="进行中"),
        layer=ClinicalTrialLayer.CORE,
        fact_version_id="fact-clin",
        source_location="CT.gov/results/portfolio-1",
    )
    view = build_clinical_portfolio_view(
        projects,
        missing_snapshot,
        missing_evidence,
        bindings,
        (*records, record),
        authoritative_contract_store=missing_evidence.contract_store,
    )
    clinical = next(p for p in view.products if p.project_id == "p-clinical")
    assert clinical.trial_rows[0].phase == "尚未公开"
    assert clinical.trial_rows[0].status == "进行中"
