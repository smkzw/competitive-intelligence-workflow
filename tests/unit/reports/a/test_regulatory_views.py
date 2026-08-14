"""Task 5.2 AV05 中国/境外监管分轨视图 + 版本化事件失败测试。

合同断言（先失败后通过）：
- 监管视图绑定单一锁定快照身份，产品集必须与 ``snapshot.product_ids``
  精确一一对应且顺序一致；
- 每个监管事件都是版本化扩展记录：事件类型、地域、日期、不可变事实版本
  与精确来源定位；事件记录必须与产品合同监管事件一一对应（同类型/地域/
  日期多重集相等），缺失或多余记录均失败关闭；
- 中国与境外事件严格分轨：地域必须解析为「中国」或「境外」确定值，
  无法分轨的事件失败关闭；同一产品的两轨各自保留事件与版本血统；
- 未知产品、重复事件记录、空白事实版本/来源定位均失败关闭；
- 无监管事件产品保留显式空轨（不失败、不删除）；
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
    RegulatoryEventVersionRecord,
    RegulatoryView,
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


def _event_record(
    *,
    project_id: str,
    event_id: str,
    event_kind: RegulatoryEventKind,
    jurisdiction: str,
    event_date: str,
    fact_version_id: str = "fact-reg",
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
    """与产品合同监管事件一一对应的版本化事件记录（中国+境外分轨）。"""
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
            project_id="p-terminated",
            event_id="ev-term-1",
            event_kind=RegulatoryEventKind.TERMINATION,
            jurisdiction="境外",
            event_date="2023-11-01",
            fact_version_id="fact-term-reg",
        ),
    )


def _regulatory_universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    AEvidenceContext,
    RegulatoryView,
]:
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    view = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _versioned_events(),
        authoritative_contract_store=evidence.contract_store,
    )
    return projects, snapshot, evidence, view


# ── AV05 精确验收节点 ───────────────────────────────────────────────────────


def test_china_and_global_regulatory_events_are_separate_and_versioned(tmp_path) -> None:
    """中国与境外监管事件严格分轨，事件与版本血统完整保留。"""
    projects, snapshot, _, view = _regulatory_universe(tmp_path)
    assert tuple(product.project_id for product in view.products) == snapshot.product_ids

    dupilumab = next(p for p in view.products if p.project_id == "project-dupilumab")
    assert tuple((row.kind_zh, row.event_date) for row in dupilumab.china_events) == (
        ("批准", "2020-06-19"),
    )
    assert dupilumab.overseas_events == ()
    for row in dupilumab.china_events:
        assert row.fact_version_id == "fact-reg"
        assert row.source_location == "NMPA/approval-notice-2020"

    terminated = next(p for p in view.products if p.project_id == "p-terminated")
    assert terminated.china_events == ()
    assert tuple((row.kind_zh, row.event_date) for row in terminated.overseas_events) == (
        ("终止", "2023-11-01"),
    )
    for row in terminated.overseas_events:
        assert row.fact_version_id == "fact-term-reg"
        assert row.source_location

    # 无监管事件产品保留显式空轨。
    for product in view.products:
        if product.project_id in ("p-clinical", "p-preclinical", "p-china-only"):
            assert product.china_events == ()
            assert product.overseas_events == ()


# ── 版本化事件：未知产品、重复、合同失配、空白定位 ──────────────────────────


def test_regulatory_rejects_unknown_product_event(tmp_path) -> None:
    """版本化事件引用未知产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    events = (
        *_versioned_events(),
        _event_record(
            project_id="p-extra",
            event_id="ev-extra-2",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction="中国",
            event_date="2024-01-01",
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


def test_regulatory_rejects_duplicate_event_record(tmp_path) -> None:
    """同一产品同一类型/地域/日期的事件记录重复必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    duplicate = _event_record(
        project_id="project-dupilumab",
        event_id="ev-approval-cn",
        event_kind=RegulatoryEventKind.APPROVAL,
        jurisdiction="中国",
        event_date="2020-06-19",
        fact_version_id="fact-reg-dup",
    )
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            (*_versioned_events(), duplicate),
            authoritative_contract_store=evidence.contract_store,
        )


def test_regulatory_rejects_missing_version_for_contract_event(tmp_path) -> None:
    """合同监管事件缺少版本化记录（事件无版本血统）必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            _versioned_events()[:1],
            authoritative_contract_store=evidence.contract_store,
        )


def test_regulatory_rejects_extra_event_not_in_contract(tmp_path) -> None:
    """版本化记录超出合同监管事件（多余事件）必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    extra = _event_record(
        project_id="project-dupilumab",
        event_id="ev-extra-1",
        event_kind=RegulatoryEventKind.SUBMISSION,
        jurisdiction="境外",
        event_date="2016-09-01",
    )
    with pytest.raises(GateEvaluationError):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            (*_versioned_events(), extra),
            authoritative_contract_store=evidence.contract_store,
        )


def test_regulatory_rejects_blank_version_or_locator(tmp_path) -> None:
    """版本化事件不得携带空白事实版本或来源定位。"""
    with pytest.raises(ValidationError):
        RegulatoryEventVersionRecord(
            project_id="project-dupilumab",
            event_id="ev-approval-cn",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction=_field(value="中国"),
            event_date=_field(value="2020-06-19"),
            fact_version_id=" ",
            source_location="NMPA/approval-notice-2020",
        )
    with pytest.raises(ValidationError):
        RegulatoryEventVersionRecord(
            project_id="project-dupilumab",
            event_id="ev-approval-cn",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction=_field(value="中国"),
            event_date=_field(value="2020-06-19"),
            fact_version_id="fact-reg",
            source_location="  ",
        )


def test_regulatory_rejects_unresolvable_jurisdiction_track(tmp_path) -> None:
    """事件地域必须解析为中国/境外确定值，无法分轨在记录构造即失败关闭。"""
    with pytest.raises(ValidationError):
        RegulatoryEventVersionRecord(
            project_id="project-dupilumab",
            event_id="ev-approval-cn",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction=_field(state=EvidenceFieldState.NOT_YET_DISCLOSED),
            event_date=_field(value="2020-06-19"),
            fact_version_id="fact-reg",
            source_location="NMPA/approval-notice-2020",
        )


def test_regulatory_rejects_non_track_jurisdiction_value(tmp_path) -> None:
    """地域值必须是中国/境外，其他法域值无法分轨必须失败关闭。"""
    with pytest.raises(ValidationError):
        _event_record(
            project_id="project-dupilumab",
            event_id="ev-approval-cn",
            event_kind=RegulatoryEventKind.APPROVAL,
            jurisdiction="全球",
            event_date="2020-06-19",
        )


# ── 视图不变量：不可变、确定性、无 Top-N 参数 ───────────────────────────────


def test_build_regulatory_has_no_top_n_or_drop_parameters() -> None:
    """监管构建器不存在 Top-N、删除或降级出口。"""
    assert set(inspect.signature(build_regulatory_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "versioned_events",
        "results_posted_evidence",
    }


def test_regulatory_view_is_immutable_and_deterministic(tmp_path) -> None:
    """视图不可变：事件不可改写，同输入两次构建结果一致。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    first = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _versioned_events(),
        authoritative_contract_store=evidence.contract_store,
    )
    second = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        _versioned_events(),
        authoritative_contract_store=evidence.contract_store,
    )
    assert first == second
    with pytest.raises(ValidationError):
        first.products[0].china_events[0].event_date = "改写"


def test_regulatory_labels_are_professional_chinese(tmp_path) -> None:
    """事件类型标签为专业中文，不暴露后端枚举或工程状态。"""
    _, _, _, view = _regulatory_universe(tmp_path)
    labels = "".join(
        row.kind_zh
        for product in view.products
        for row in (*product.china_events, *product.overseas_events)
    )
    assert all("\u4e00" <= ch <= "\u9fff" for ch in labels)
    lowered = labels.lower()
    for token in ("approval", "termination", "submission", "snapshot", "binding"):
        assert token not in lowered


def test_regulatory_view_contract_events_are_exactly_covered(tmp_path) -> None:
    """事件记录与合同监管事件一一对应：每产品视图事件数=合同事件数。"""
    projects, _, _, _ = _mixed_universe(tmp_path)
    _, _, _, view = _regulatory_universe(tmp_path)
    contract_by_project = {project.project_id: project for project in projects}
    for product in view.products:
        contract = contract_by_project[product.project_id]
        view_count = len(product.china_events) + len(product.overseas_events)
        assert view_count == len(contract.regulatory_events)
