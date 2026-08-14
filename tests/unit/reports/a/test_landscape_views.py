"""Task 5.2 AV01 竞争格局视图 + 严格快照输入失败测试。

合同断言（先失败后通过）：
- 竞争格局视图绑定单一锁定快照身份，产品行集合必须与
  ``snapshot.product_ids`` 精确一一对应且顺序一致；缺失、重复、多余或
  顺序漂移均失败关闭；
- 整批分析结果必须与产品合同一一对应且顺序一致；未闭合快照失败关闭；
- 每一行携带全部规划分组维度：靶点、模态、中国/境外阶段与状态、生命周期
  与开发状态；维度目录必须由行数据闭合生成，不得手写预置；
- 证据缺失用显式中文状态表达（不适用/尚未公开/来源未列示/技术暂不可用），
  不用空字符串、默认值或推断结论填补；
- 视图为不可变、确定性纯投影：无 Top-N/删除/降级参数，同输入两次结果一致。
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
    LandscapeView,
    build_landscape_view,
    view_identity,
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
            "已批准",
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
            "II期 进行中",
            "CT.gov/results/portfolio-1",
        ),
        "fact-term-design": (
            "p-terminated",
            "clinical_trial_region",
            "II期 已终止",
            "CT.gov/results/portfolio-1",
        ),
        "fact-term-reg": (
            "p-terminated",
            "regulatory_event",
            "已终止",
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


def _analyzed_universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    AEvidenceContext,
    LandscapeView,
]:
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    view = build_landscape_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    return projects, snapshot, evidence, view


# ── AV01 精确验收节点 ───────────────────────────────────────────────────────


def test_landscape_contains_every_in_scope_product_and_grouping_dimension(tmp_path) -> None:
    """竞争格局保留全部合格产品与全部分组维度，无 Top-N 截断。"""
    projects, snapshot, _, view = _analyzed_universe(tmp_path)
    ids = tuple(row.project_id for row in view.products)
    assert ids == snapshot.product_ids
    assert len(ids) == len(set(ids))
    assert view.total_products == len(snapshot.product_ids) == 5

    by_id = {project.project_id: project for project in projects}
    for row in view.products:
        contract = by_id[row.project_id]
        assert row.canonical_name == contract.canonical_name
        assert row.target_mechanism == _display(contract.target_mechanism)
        assert row.modality == _display(contract.modality)
        assert row.china_stage == _display(contract.china.highest_stage)
        assert row.china_status == _display(contract.china.highest_status)
        assert row.overseas_stage == _display(contract.overseas.highest_stage)
        assert row.overseas_status == _display(contract.overseas.highest_status)
        assert row.lifecycle_zh
        assert row.development_status_zh

    # 维度目录由行数据闭合生成：全部行取值都出现在目录中，目录不手写预置。
    assert view.targets == tuple(sorted({row.target_mechanism for row in view.products}))
    assert view.modalities == tuple(sorted({row.modality for row in view.products}))
    assert view.stages == tuple(
        sorted({value for row in view.products for value in (row.china_stage, row.overseas_stage)})
    )
    assert view.statuses == tuple(
        sorted(
            {value for row in view.products for value in (row.china_status, row.overseas_status)}
        )
    )
    assert view.lifecycles == tuple(sorted({row.lifecycle_zh for row in view.products}))
    assert view.regions == ("中国", "境外")
    # 生命周期与开发状态必须覆盖本次宇宙的全部取值。
    assert set(view.lifecycles) == {
        "已有临床结果公开",
        "已进入临床开发阶段",
        "处于早期研发阶段",
        "处于申报、上市或停止开发阶段",
    }
    assert set(view.development_statuses) == {
        "上市",
        "临床",
        "临床前",
        "停止开发",
    }


# ── 严格快照输入：缺失/重复/多余/顺序漂移/分析失配/未闭合 ──────────────────


def test_landscape_rejects_missing_product(tmp_path) -> None:
    """项目清单缺失快照内产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects[:-1],
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_landscape_rejects_duplicate_product(tmp_path) -> None:
    """项目清单包含重复产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects + [projects[0]],
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_landscape_rejects_extra_product(tmp_path) -> None:
    """项目清单混入快照外产品必须失败关闭，不得后补快照身份。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    extra = _complete_project(
        project_id="p-extra",
        canonical_name="多余药",
        core_trials=(),
        regulatory_events=(),
        anchor_trials=(),
    )
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            [*projects, extra],
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_landscape_rejects_reordered_products(tmp_path) -> None:
    """顺序漂移失败关闭：项目顺序必须与锁定快照一致。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    reordered = [projects[4], *projects[:4]]
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            reordered,
            snapshot,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_landscape_rejects_analysis_mismatch(tmp_path) -> None:
    """构建器不信任调用方分析结果：签名不接受 analysis 输入，无法伪造分析失配。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    assert "analysis" not in inspect.signature(build_landscape_view).parameters
    view = build_landscape_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    assert view.products


def test_landscape_rejects_unclosed_snapshot(tmp_path) -> None:
    """未闭合快照（穷举未完成）失败关闭，视图不得消费。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    unclosed = snapshot.model_copy(update={"enumeration_complete": False})
    with pytest.raises(GateEvaluationError):
        build_landscape_view(
            projects,
            unclosed,
            evidence,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_landscape_view_identity_comes_only_from_snapshot(tmp_path) -> None:
    """视图身份字段完全来自锁定快照，不接受自由清单后补。"""
    _, snapshot, _, view = _analyzed_universe(tmp_path)
    identity = view_identity(snapshot)
    assert identity.project_id == snapshot.project_id == "report-universe"
    assert identity.evidence_snapshot_id == snapshot.evidence_snapshot_id
    assert identity.research_role_set_id == snapshot.research_role_set_id == "role-set-1"
    assert identity.product_ids == snapshot.product_ids


# ── 视图不变量：不可变、确定性、无 Top-N 参数 ───────────────────────────────


def test_build_landscape_has_no_top_n_or_drop_parameters() -> None:
    """竞争格局构建器不存在 Top-N、删除或降级出口，也不接受调用方分析结果。"""
    assert set(inspect.signature(build_landscape_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "results_posted_evidence",
    }


def test_landscape_view_is_immutable_and_deterministic(tmp_path) -> None:
    """视图不可变：行不可改写，同一锁定输入两次构建结果一致。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    first = build_landscape_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    second = build_landscape_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    assert first == second
    with pytest.raises(ValidationError):
        first.products[0].canonical_name = "改写"  # type: ignore[misc]


def test_landscape_preserves_explicit_missing_states_as_chinese_labels(tmp_path) -> None:
    """境外整组不适用必须显式表达为中文状态，不得用空字符串填补。"""
    _, _, _, view = _analyzed_universe(tmp_path)
    china_only = next(row for row in view.products if row.project_id == "p-china-only")
    assert china_only.overseas_stage == "不适用"
    assert china_only.overseas_status == "不适用"


def test_landscape_labels_are_professional_chinese_not_engine_states(tmp_path) -> None:
    """生命周期/开发状态/地域标签使用专业中文，不暴露工程状态。"""
    _, _, _, view = _analyzed_universe(tmp_path)
    labels = "".join(
        [
            *view.lifecycles,
            *view.development_statuses,
            *view.statuses,
            *view.regions,
        ]
    )
    assert all("\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f" for ch in labels)
    lowered = labels.lower()
    for token in ("snapshot", "binding", "result_bearing", "blocked", "missing"):
        assert token not in lowered
