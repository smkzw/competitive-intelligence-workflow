"""Task 5.1 全宇宙无 Top-N、不得删除缺证项目的失败测试（强输入）。

合同断言（先失败后通过）：
- 整批分析消费 Phase 3 的已闭合宇宙快照、已接受绑定与强类型已发布结果证据；
- 项目 ID 与 snapshot.product_ids 精确一一对应：重复项目、缺失/多余项目、
  空项目集均失败关闭；空宇宙由快照合同本身拒绝；
- 全部传入项目按原顺序保留：不按成熟度、结果好坏、字段缺口或固定数量截断
  （无 Top-N）；上市、申报、临床、公开披露的临床前、暂停/终止/撤回/放弃
  项目全部保留并分层；
- 证据缺失项目不删除、不降级：保留身份、成熟度层与精确缺失字段；任一项目
  证据未达门槛即整个 A 报告不可生成（失败关闭）；
- 每个被阻断产品都有独立的中文阻断说明：含产品名、成熟度层、缺失字段中文
  标签与中文诊断；公共构造边界拒绝无中文字符的说明；
- 整批分析为纯函数：无 Top-N/删除/降级参数，同输入结果确定且一致。
"""

from __future__ import annotations

import inspect

import pytest
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
from ci_workflow.reports.a.analysis import (
    BlockingExplanation,
    UniverseAnalysisResult,
    UniverseProjectResult,
    analyze_universe,
    evaluate_maturity_gate,
)
from ci_workflow.reports.a.contracts import (
    ANCHOR_TRIAL,
    CORE_EFFICACY_RECORD,
    SAFETY_SUMMARY_RECORD,
    AnchorTrialRecord,
    AProjectContract,
    CoreTrialRecord,
    CoreTrialRole,
    MaturityLevel,
    RegistryResultsPostedEvidence,
    RegulatoryEventKind,
    RegulatoryEventRecord,
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
    project_id: str = "report-universe",
    product_ids: tuple[str, ...],
    trial_ids: tuple[str, ...] = (),
    trial_products: dict[str, str] | None = None,
    design_kinds: dict[str, TrialDesignKind] | None = None,
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
        project_id=project_id,
        evidence_snapshot_id="snap-ev-1",
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
        project_id=project_id,
        evidence_snapshot_id="snap-ev-1",
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
    """构建一个所有必需字段齐备的 A 项目；测试用 overrides 制造缺口。"""
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
                event_id="ev-1",
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


def _mixed_universe() -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    tuple[GateEvidenceBinding, ...],
    tuple[RegistryResultsPostedEvidence, ...],
]:
    """覆盖全部生命周期与通过/阻断两种状态的代表性全宇宙。"""
    projects = [
        _complete_project(),  # project-dupilumab 度普利尤单抗：已批准 + 结果齐备
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
            project_id="p-submission",
            canonical_name="申报示例药",
            core_trials=(
                CoreTrialRecord(
                    trial_id="NCT-sub-1",
                    role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                    status="审评中",
                ),
            ),
            regulatory_events=(
                RegulatoryEventRecord(
                    event_id="ev-2",
                    event_kind=RegulatoryEventKind.SUBMISSION,
                    jurisdiction=_field(value="中国"),
                    event_date=_field(value="2025-03-01"),
                ),
            ),
            anchor_trials=(),
        ),
        _complete_project(
            project_id="p-terminated-ok",
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
                    event_id="ev-3",
                    event_kind=RegulatoryEventKind.TERMINATION,
                    jurisdiction=_field(value="境外"),
                    event_date=_field(value="2023-11-01"),
                ),
            ),
            anchor_trials=(),
        ),
        _complete_project(  # p-blocked-safety 缺安全摘要药：已批准 + 结果但缺安全摘要
            project_id="p-blocked-safety",
            canonical_name="缺安全摘要药",
            core_trials=(
                CoreTrialRecord(
                    trial_id="NCT-blk-saf-1",
                    role=CoreTrialRole.REGISTRATION_OR_PIVOTAL,
                    status="已完成",
                ),
            ),
            anchor_trials=(
                AnchorTrialRecord(
                    trial_id="NCT-blk-saf-1",
                    fact_version_ids=("fact-bs-eff",),
                ),
            ),
        ),
        _complete_project(  # p-blocked-clinical 缺试验药：临床但无核心试验
            project_id="p-blocked-clinical",
            canonical_name="缺试验药",
            core_trials=(),
            regulatory_events=(),
            anchor_trials=(),
        ),
    ]
    snapshot = _snapshot(
        product_ids=(
            "project-dupilumab",
            "p-clinical",
            "p-preclinical",
            "p-submission",
            "p-terminated-ok",
            "p-blocked-safety",
            "p-blocked-clinical",
        ),
        trial_ids=(
            "NCT02407756",
            "NCT-clin-1",
            "NCT-sub-1",
            "NCT-term-1",
            "NCT-blk-saf-1",
            "NCT-clin-2",
        ),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-sub-1": "p-submission",
            "NCT-term-1": "p-terminated-ok",
            "NCT-blk-saf-1": "p-blocked-safety",
            "NCT-clin-2": "p-blocked-clinical",
        },
    )
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
        # p-submission：设计事实 + 监管材料（结果未公开）
        _design_binding(
            binding_id="b-sub-design",
            object_id="p-submission",
            trial_id="NCT-sub-1",
            fact_version_id="fact-sub-design",
        ),
        _binding(
            binding_id="b-sub-reg",
            object_id="p-submission",
            trial_id=None,
            fact_version_id="fact-sub-reg",
            source_role=SourceRole.REGULATORY_MATERIAL,
            disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
            numeric_value=None,
            denominator=None,
            definition=None,
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
        ),
        # p-terminated-ok：设计事实 + 监管不适用（终止）
        _design_binding(
            binding_id="b-term-design",
            object_id="p-terminated-ok",
            trial_id="NCT-term-1",
            fact_version_id="fact-term-design",
        ),
        _binding(
            binding_id="b-term-reg",
            unit_id="a_regulatory_termination",
            object_id="p-terminated-ok",
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
        # p-blocked-safety：监管观察值 + 疗效，无安全摘要
        _binding(
            binding_id="b-bs-reg",
            object_id="p-blocked-safety",
            trial_id="NCT-blk-saf-1",
            fact_version_id="fact-bs-reg",
            source_role=SourceRole.REGULATORY_MATERIAL,
            definition=None,
            direction=None,
            timepoint=None,
            analysis_population=None,
            treatment_group=None,
        ),
        _binding(
            binding_id="b-bs-eff",
            object_id="p-blocked-safety",
            trial_id="NCT-blk-saf-1",
            fact_version_id="fact-bs-eff",
        ),
        # p-blocked-clinical：设计事实（无核心试验记录）
        _design_binding(
            binding_id="b-bc-clin",
            object_id="p-blocked-clinical",
            trial_id="NCT-clin-2",
            fact_version_id="fact-bc-clin",
        ),
    )
    return projects, snapshot, bindings, ()


def _preclinical_contract(project_id: str, name: str, *, blocked: bool) -> AProjectContract:
    overrides: dict[str, object] = {
        "project_id": project_id,
        "canonical_name": name,
    }
    if blocked:
        overrides["target_mechanism"] = _field(state=EvidenceFieldState.NOT_YET_DISCLOSED)
    return _complete_project(
        core_trials=(),
        regulatory_events=(),
        anchor_trials=(),
        **overrides,
    )


# ── 整批分析合同：强输入、无 Top-N/删除/降级参数 ───────────────────────────


def test_analyze_universe_has_no_top_n_drop_or_override_parameters() -> None:
    """整批分析只消费强输入：不存在 Top-N、删除或降级出口。"""
    assert set(inspect.signature(analyze_universe).parameters) == {
        "projects",
        "snapshot",
        "bindings",
        "results_posted_evidence",
    }


def test_duplicate_projects_fail_closed() -> None:
    """项目清单包含重复项目必须失败关闭。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    with pytest.raises(GateEvaluationError):
        analyze_universe(projects + [projects[0]], snapshot, bindings, flags)


def test_project_set_must_match_snapshot_product_ids() -> None:
    """项目集与宇宙快照产品清单必须精确一一对应；缺失或多余均失败关闭。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    with pytest.raises(GateEvaluationError):
        analyze_universe(projects[:-1], snapshot, bindings, flags)
    extra = projects + [
        _preclinical_contract("p-extra", "多余药", blocked=False),
    ]
    with pytest.raises(GateEvaluationError):
        analyze_universe(extra, snapshot, bindings, flags)


def test_empty_projects_fail_closed() -> None:
    """空项目集与任何非空快照都不一致，必须失败关闭。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    with pytest.raises(GateEvaluationError):
        analyze_universe([], snapshot, bindings, flags)


def test_empty_snapshot_rejected_by_contract() -> None:
    """空宇宙由快照合同本身拒绝：产品清单不可为空。"""
    with pytest.raises(ValidationError):
        _snapshot(product_ids=())


def test_universe_result_rejects_explanation_mismatch() -> None:
    """逐产品中文阻断说明必须与阻断项目一一对应且顺序一致。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    gate = evaluate_maturity_gate(projects[5], snapshot, bindings, flags)
    entry = UniverseProjectResult(
        project_id=projects[5].project_id,
        canonical_name=projects[5].canonical_name,
        gate=gate,
    )
    with pytest.raises(ValidationError):
        UniverseAnalysisResult(
            projects=(entry,),
            blocking_explanations_zh=(),
            report_ready=False,
        )
    with pytest.raises(ValidationError):
        UniverseAnalysisResult(
            projects=(entry,),
            blocking_explanations_zh=(
                BlockingExplanation(
                    project_id="other-project",
                    canonical_name="其他药",
                    message_zh="该产品关键证据尚不完整，报告暂无法生成",
                ),
            ),
            report_ready=False,
        )


def test_universe_result_rejects_report_ready_contradiction() -> None:
    """任一项目阻断时 report_ready 必须为假，反之必须为真。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    gate = evaluate_maturity_gate(projects[5], snapshot, bindings, flags)
    entry = UniverseProjectResult(
        project_id=projects[5].project_id,
        canonical_name=projects[5].canonical_name,
        gate=gate,
    )
    with pytest.raises(ValidationError):
        UniverseAnalysisResult(
            projects=(entry,),
            blocking_explanations_zh=(
                BlockingExplanation(
                    project_id=projects[5].project_id,
                    canonical_name=projects[5].canonical_name,
                    message_zh="该产品关键证据尚不完整，报告暂无法生成",
                ),
            ),
            report_ready=True,
        )


def test_universe_project_result_rejects_identity_mismatch() -> None:
    """整批分析项目身份必须与门槛判定绑定一致。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    gate = evaluate_maturity_gate(projects[5], snapshot, bindings, flags)
    with pytest.raises(ValidationError):
        UniverseProjectResult(
            project_id="another-id",
            canonical_name=projects[5].canonical_name,
            gate=gate,
        )


def test_blocking_explanation_rejects_pure_english() -> None:
    """中文阻断说明的公共构造边界拒绝无中文字符的文本。"""
    with pytest.raises(ValidationError):
        BlockingExplanation(
            project_id="p-x",
            canonical_name="示例药",
            message_zh="A report cannot be generated because evidence is incomplete",
        )
    BlockingExplanation(
        project_id="p-x",
        canonical_name="示例药",
        message_zh="该产品关键证据尚不完整，报告暂无法生成",
    )
    with pytest.raises(ValidationError):
        BlockingExplanation(
            project_id="p-x",
            canonical_name="示例药",
            message_zh="该产品证据未达门槛，报告暂无法生成",
        )


# ── 全宇宙保留：无 Top-N、生命周期分层、身份与顺序稳定 ────────────────────


def test_universe_keeps_every_project_in_input_order() -> None:
    """全部传入项目按原顺序进入结果，一个不少，身份与顺序稳定。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    assert [item.project_id for item in result.projects] == [
        project.project_id for project in projects
    ]
    assert result.total_projects == len(projects) == len(result.projects)


def test_universe_keeps_every_lifecycle_stage_retained() -> None:
    """上市、申报、临床、临床前、暂停/终止/撤回/放弃项目全部保留并分层。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    by_id = {item.project_id: item for item in result.projects}
    assert by_id["p-preclinical"].maturity_level is MaturityLevel.ALL_PROJECTS
    assert by_id["p-clinical"].maturity_level is MaturityLevel.CLINICAL
    assert by_id["p-submission"].maturity_level is MaturityLevel.FILING_APPROVAL_TERMINATION
    assert by_id["p-terminated-ok"].maturity_level is MaturityLevel.FILING_APPROVAL_TERMINATION
    assert by_id["project-dupilumab"].maturity_level is MaturityLevel.RESULT_BEARING


def test_large_universe_is_not_truncated_by_fixed_quantity() -> None:
    """项目数量超过任何常见展示上限时全部保留，不按固定数量截断。"""
    projects = [
        _preclinical_contract(
            f"p-{index:02d}",
            f"示例药物{index:02d}",
            blocked=index % 7 == 0,
        )
        for index in range(40)
    ]
    snapshot = _snapshot(product_ids=tuple(project.project_id for project in projects))
    result = analyze_universe(projects, snapshot, ())
    assert len(result.projects) == 40
    assert [item.project_id for item in result.projects] == [p.project_id for p in projects]
    assert result.blocked_projects == 6


def test_analysis_is_deterministic_and_preserves_identity() -> None:
    """同输入两次结果完全一致；项目规范名与别名不被改写。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    first = analyze_universe(projects, snapshot, bindings, flags)
    second = analyze_universe(projects, snapshot, bindings, flags)
    assert first == second
    entry = first.projects[0]
    assert entry.project_id == projects[0].project_id == "project-dupilumab"
    assert entry.canonical_name == "度普利尤单抗"
    assert projects[0].aliases == ("Dupixent", "Dupilumab")


# ── 不得删除缺证项目：保留、阻断与失败关闭 ─────────────────────────────────


def test_blocked_project_is_retained_with_identity_level_and_missing_keys() -> None:
    """证据缺失项目不删除、不降级：身份、结果层与精确缺失字段保留。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    entry = next(item for item in result.projects if item.project_id == "p-blocked-safety")
    assert entry.blocked
    assert entry.project_id == "p-blocked-safety"
    assert entry.canonical_name == "缺安全摘要药"
    assert entry.maturity_level is MaturityLevel.RESULT_BEARING
    assert entry.missing_fields == entry.gate.missing_fields
    assert entry.gate.missing_keys == frozenset({SAFETY_SUMMARY_RECORD})


def test_blocked_flag_triggered_project_stays_in_result_layer_not_no_result() -> None:
    """只有已发布结果标志而值不完整的项目进入恢复层：成熟度保持结果层。"""
    project = _complete_project(
        project_id="p-flag-only",
        canonical_name="仅标志药",
        anchor_trials=(
            AnchorTrialRecord(trial_id="NCT02407756", fact_version_ids=("flag-fact-1",)),
        ),
    )
    snapshot = _snapshot(product_ids=("p-flag-only",), trial_ids=("NCT02407756",))
    flag = RegistryResultsPostedEvidence(
        project_id="p-flag-only",
        trial_id="NCT02407756",
        fact_version_id="flag-fact-1",
        source_location="CT.gov/results/ver-2",
    )
    flag_binding = _binding(
        binding_id="binding-flag-fact-1",
        unit_id="a_registry_results_posted",
        object_id="p-flag-only",
        trial_id="NCT02407756",
        fact_version_id="flag-fact-1",
        fact_domain=FactDomain.TRIAL_DESIGN,
        numeric_value=None,
        unit=None,
        denominator=None,
        definition="官方登记已发布结果",
        direction=None,
        timepoint=None,
        analysis_population=None,
        treatment_group=None,
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
        source_location=flag.source_location,
    )
    result = analyze_universe([project], snapshot, (flag_binding,), (flag,))
    entry = result.projects[0]
    assert entry.blocked
    assert entry.maturity_level is MaturityLevel.RESULT_BEARING
    assert {
        CORE_EFFICACY_RECORD,
        SAFETY_SUMMARY_RECORD,
    } <= entry.gate.missing_keys
    assert ANCHOR_TRIAL not in entry.gate.missing_keys


def test_report_not_ready_when_any_project_blocked() -> None:
    """任一项目证据未达门槛即整个 A 报告不可生成，不因其他项目通过而放行。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    assert not result.report_ready
    assert result.blocked_projects == 2
    assert result.total_projects == 7
    assert result.pass_count == 5


def test_report_ready_when_every_project_passes() -> None:
    """全部项目证据齐备时整批分析可生成 A 报告。"""
    projects = [
        _preclinical_contract(f"p-{index}", f"通过药物{index}", blocked=False) for index in range(3)
    ]
    snapshot = _snapshot(product_ids=tuple(project.project_id for project in projects))
    result = analyze_universe(projects, snapshot, ())
    assert result.report_ready
    assert result.blocked_projects == 0


def test_blocked_project_ids_preserve_universe_order() -> None:
    """被阻断项目按宇宙顺序列出，不按成熟度或字段缺口重排。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    assert result.blocked_project_ids == ("p-blocked-safety", "p-blocked-clinical")


# ── 逐产品中文阻断说明 ─────────────────────────────────────────────────────


def test_every_blocked_product_has_exactly_one_explanation() -> None:
    """每个被阻断产品恰有一条中文阻断说明，与阻断项目一一对应。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    assert len(result.blocking_explanations_zh) == result.blocked_projects == 2
    assert [item.project_id for item in result.blocking_explanations_zh] == list(
        result.blocked_project_ids
    )


def test_explanation_carries_product_name_maturity_and_missing_labels() -> None:
    """阻断说明含产品名、成熟度层与缺失字段中文标签，用户可据此补证。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    message = result.blocking_explanations_zh[0].message_zh
    assert "缺安全摘要药" in message
    assert "已有临床结果公开" in message
    assert "TEAE/SAE 数值摘要" in message


def test_explanation_distinguishes_missing_states() -> None:
    """尚未公开与穷尽检索后未找到是不同的缺失状态，说明分别表述。"""
    undeclared = _preclinical_contract("p-undeclared", "未公开药", blocked=True)
    not_found = _complete_project(
        project_id="p-not-found",
        canonical_name="检索未获药",
        core_trials=(),
        regulatory_events=(),
        anchor_trials=(),
        target_mechanism=_field(state=EvidenceFieldState.SOURCE_NOT_LISTED),
    )
    projects = [undeclared, not_found]
    snapshot = _snapshot(product_ids=tuple(project.project_id for project in projects))
    result = analyze_universe(projects, snapshot, ())
    by_id = {item.project_id: item for item in result.blocking_explanations_zh}
    assert "尚未公开" in by_id["p-undeclared"].message_zh
    assert "穷尽检索后未找到" in by_id["p-not-found"].message_zh
    assert by_id["p-undeclared"].message_zh != by_id["p-not-found"].message_zh


def test_explanations_are_native_chinese_without_engineering_labels() -> None:
    """阻断说明是中文临床/开发语言：不暴露字段键、判定状态或工程命名。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    for explanation in result.blocking_explanations_zh:
        message = explanation.message_zh
        assert any("\u4e00" <= ch <= "\u9fff" for ch in message)
        assert "产品「" in message
        assert "_" not in message
        for token in (
            "blocked",
            "missing",
            "ready",
            "top_n",
            "result_bearing",
            "maturity",
            "clinical",
            "preclinical",
            "approved",
            "universe",
            "snapshot",
            "binding",
            "NCT",
            "门槛",
            "竞品宇宙",
            "基础层",
        ):
            assert token not in message


def test_explanations_are_per_product_and_not_collapsed() -> None:
    """每个产品的说明独立成条：只含自身产品名，不合并掩盖其他产品缺口。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    first, second = result.blocking_explanations_zh
    assert first.canonical_name == "缺安全摘要药"
    assert second.canonical_name == "缺试验药"
    assert "缺试验药" not in first.message_zh
    assert "缺安全摘要药" not in second.message_zh
    assert first.message_zh != second.message_zh


def test_batch_missing_fields_match_per_project_gate_exactly() -> None:
    """整批分析逐项目缺失字段与单项目门槛判定完全一致，不增不减。"""
    projects, snapshot, bindings, flags = _mixed_universe()
    result = analyze_universe(projects, snapshot, bindings, flags)
    for entry in result.projects:
        single = evaluate_maturity_gate(
            next(p for p in projects if p.project_id == entry.project_id),
            snapshot,
            bindings,
            flags,
        )
        assert entry.gate.missing_keys == single.missing_keys
        assert entry.gate.maturity_level is single.maturity_level
