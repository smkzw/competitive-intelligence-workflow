"""Task 5.2 AV07 专利与保护视图：专利族/法域成员/保护范围/期限/监管独占分离。

合同断言（先失败后通过）：
- 专利与保护视图绑定单一锁定快照身份，产品集必须与 ``snapshot.product_ids``
  精确一一对应且顺序一致；
- 专利族、法域成员、保护范围、期限与监管独占是五种独立类型化版本化记录，
  各自绑定产品、不可变事实版本与精确来源定位，绝不混写进一个字段；
- 法域成员携带单一确定法域，同一族的多法域成员各自独立成行，不做跨法域
  拼接；期限绑定法域成员，到期日不得跨成员/跨产品拼接；
- 到期日未知显式表达为「尚未公开」等互斥状态，绝不推断或填充默认日期；
  视图只呈现来源可定位的程序状态与到期事实，不做有效性法律结论；
- 未知产品、重复记录身份、引用未知专利族/未知法域成员、空白事实版本/
  来源定位/法域均失败关闭；
- 无专利/无独占产品保留显式空集合（不失败、不删除、不占位）；
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
    AEvidenceContext,
    PatentFamilyRecord,
    PatentMemberRecord,
    PatentProtectionProduct,
    PatentProtectionView,
    PatentScopeRecord,
    PatentTermRecord,
    RegulatoryExclusivityKind,
    RegulatoryExclusivityRecord,
    build_patent_protection_view,
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
            "registry/status-history-3",
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


class PatentRecordBundle(TypedDict):
    """五类版本化记录的类型化捆绑：键名与构建器关键字一致。"""

    families: tuple[PatentFamilyRecord, ...]
    members: tuple[PatentMemberRecord, ...]
    scopes: tuple[PatentScopeRecord, ...]
    terms: tuple[PatentTermRecord, ...]
    exclusivities: tuple[RegulatoryExclusivityRecord, ...]


def _patent_records() -> PatentRecordBundle:
    """五类独立版本化记录：专利族/法域成员/保护范围/期限/监管独占。"""
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


def _patent_universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    AEvidenceContext,
    PatentProtectionView,
]:
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    view = build_patent_protection_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_patent_records(),
    )
    return projects, snapshot, evidence, view


# ── AV07 精确验收节点 ───────────────────────────────────────────────────────


def test_patent_family_jurisdiction_expiry_and_exclusivity_are_separate(tmp_path) -> None:
    """专利族、法域成员、保护范围、期限与监管独占分列，不混写。"""
    projects, snapshot, _evidence, view = _patent_universe(tmp_path)
    assert tuple(product.project_id for product in view.products) == snapshot.product_ids

    dupilumab = next(p for p in view.products if p.project_id == "project-dupilumab")
    assert tuple((row.family_id, row.family_label_zh) for row in dupilumab.families) == (
        ("patent-family-1", "度普利尤单抗抗体制剂专利族"),
    )
    # 同一专利族下两个法域成员各自独立成行，不拼接为一个跨国条目。
    assert tuple(
        (row.member_id, row.jurisdiction, row.member_status) for row in dupilumab.members
    ) == (
        ("member-cn-1", "中国", "已授权"),
        ("member-us-1", "美国", "审评中"),
    )
    assert tuple(row.scope_zh for row in dupilumab.scopes) == (
        "覆盖含目标抗体的组合物、制剂及其治疗用途",
    )
    # 期限绑定法域成员：中国成员有确定到期日，美国成员到期日尚未公开——
    # 未知到期日不推断、不填充默认值。
    assert tuple((row.member_id, row.term_zh, row.expiry) for row in dupilumab.terms) == (
        ("member-cn-1", "自申请日起 20 年", "2034-05-12"),
        ("member-us-1", "自申请日起 20 年", "尚未公开"),
    )
    # 监管独占独立于专利：独占类型/法域/到期与专利记录分开保存。
    assert tuple(
        (row.exclusivity_kind_zh, row.jurisdiction, row.expiry) for row in dupilumab.exclusivities
    ) == (
        ("数据独占", "中国", "2025-06-19"),
        ("孤儿药独占", "境外", "2027-03-28"),
    )
    for family_row in dupilumab.families:
        assert family_row.fact_version_id
        assert family_row.source_location
    for member_row in dupilumab.members:
        assert member_row.fact_version_id
        assert member_row.source_location
    for scope_row in dupilumab.scopes:
        assert scope_row.fact_version_id
        assert scope_row.source_location
    for term_row in dupilumab.terms:
        assert term_row.fact_version_id
        assert term_row.source_location
    for exclusivity_row in dupilumab.exclusivities:
        assert exclusivity_row.fact_version_id
        assert exclusivity_row.source_location

    # 无专利/无独占产品保留显式空集合：不失败、不删除、不占位。
    for product in view.products:
        if product.project_id != "project-dupilumab":
            assert product.families == ()
            assert product.members == ()
            assert product.scopes == ()
            assert product.terms == ()
            assert product.exclusivities == ()


def test_patent_view_keeps_five_typed_collections_separate(tmp_path) -> None:
    """视图按五类独立类型保存，任何两类不得共享字段或互相替代。"""
    _, _, _, view = _patent_universe(tmp_path)
    dupilumab = next(p for p in view.products if p.project_id == "project-dupilumab")
    assert isinstance(dupilumab, PatentProtectionProduct)
    # 专利族字段与法域成员字段互异。
    family_fields = {field for field in type(dupilumab.families[0]).model_fields}
    member_fields = {field for field in type(dupilumab.members[0]).model_fields}
    assert "family_label_zh" in family_fields and "family_label_zh" not in member_fields
    assert "jurisdiction" in member_fields and "jurisdiction" not in family_fields
    # 期限字段与监管独占字段互异。
    term_fields = {field for field in type(dupilumab.terms[0]).model_fields}
    exclusivity_fields = {field for field in type(dupilumab.exclusivities[0]).model_fields}
    assert "term_zh" in term_fields and "term_zh" not in exclusivity_fields
    assert "exclusivity_kind_zh" in exclusivity_fields
    assert "exclusivity_kind_zh" not in term_fields


def test_patent_unknown_expiry_is_not_inferred(tmp_path) -> None:
    """到期日未知时视图显式表达尚未公开，绝不推断或填充默认日期。"""
    _, _, _, view = _patent_universe(tmp_path)
    dupilumab = next(p for p in view.products if p.project_id == "project-dupilumab")
    us_term = next(row for row in dupilumab.terms if row.member_id == "member-us-1")
    assert us_term.expiry == "尚未公开"
    assert "203" not in us_term.expiry  # 没有推断出的到期年份
    term_fields = set(type(us_term).model_fields)
    assert "expiry_inferred" not in term_fields
    assert "validity" not in term_fields


def test_patent_view_never_asserts_legal_validity(tmp_path) -> None:
    """视图只呈现来源可定位的程序状态与到期事实，不做有效性法律结论。"""
    _, _, _, view = _patent_universe(tmp_path)
    dupilumab = next(p for p in view.products if p.project_id == "project-dupilumab")
    member_labels = [row.member_status for row in dupilumab.members]
    allowed_statuses = ("已授权", "审评中", "尚未公开", "来源未列示", "不适用", "技术暂不可用")
    for label in member_labels:
        assert label in allowed_statuses
    for row in dupilumab.terms:
        assert "有效" not in row.expiry and "无效" not in row.expiry
    for row in dupilumab.exclusivities:
        assert "有效" not in row.expiry and "无效" not in row.expiry


# ── 版本化记录：未知产品、重复身份、拼接、空白定位 ──────────────────────────


def test_patent_rejects_unknown_product_record(tmp_path) -> None:
    """任一记录引用未知产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["families"] = (
        *records["families"],
        PatentFamilyRecord(
            project_id="p-extra",
            family_id="patent-family-x",
            family_label_zh="未知产品专利族",
            fact_version_id="fact-x",
            source_location="patent-office/x",
        ),
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


def test_patent_rejects_duplicate_family(tmp_path) -> None:
    """同一产品同一专利族重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["families"] = (
        *records["families"],
        PatentFamilyRecord(
            project_id="project-dupilumab",
            family_id="patent-family-1",
            family_label_zh="重复专利族",
            fact_version_id="fact-family-dup",
            source_location="patent-office/family-register-dup",
        ),
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


def test_patent_rejects_duplicate_member(tmp_path) -> None:
    """同一产品同一法域成员重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["members"] = (
        *records["members"],
        PatentMemberRecord(
            project_id="project-dupilumab",
            family_id="patent-family-1",
            member_id="member-cn-1",
            jurisdiction="中国",
            member_status=_field(value="已授权"),
            fact_version_id="fact-member-dup",
            source_location="CNIPA/gazette-dup",
        ),
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


def test_patent_rejects_duplicate_scope(tmp_path) -> None:
    """同一产品同一专利族同一保护范围重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["scopes"] = (
        *records["scopes"],
        PatentScopeRecord(
            project_id="project-dupilumab",
            family_id="patent-family-1",
            scope_zh="覆盖含目标抗体的组合物、制剂及其治疗用途",
            fact_version_id="fact-scope-dup",
            source_location="patent-office/claims-summary-dup",
        ),
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


def test_patent_rejects_duplicate_term(tmp_path) -> None:
    """同一产品同一成员同一期限同一到期日重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["terms"] = (
        *records["terms"],
        PatentTermRecord(
            project_id="project-dupilumab",
            member_id="member-cn-1",
            term_zh="自申请日起 20 年",
            expiry=_field(value="2034-05-12"),
            fact_version_id="fact-term-dup",
            source_location="CNIPA/gazette-dup",
        ),
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


def test_patent_rejects_duplicate_exclusivity(tmp_path) -> None:
    """同一产品同一独占类型同一法域同一到期日重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["exclusivities"] = (
        *records["exclusivities"],
        RegulatoryExclusivityRecord(
            project_id="project-dupilumab",
            exclusivity_kind=RegulatoryExclusivityKind.DATA_EXCLUSIVITY,
            jurisdiction="中国",
            expiry=_field(value="2025-06-19"),
            fact_version_id="fact-excl-dup",
            source_location="NMPA/exclusivity-notice-dup",
        ),
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


def test_patent_rejects_member_with_unknown_family(tmp_path) -> None:
    """法域成员引用未声明/跨产品的专利族必须失败关闭（跨产品族拼接）。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["members"] = (
        *records["members"],
        PatentMemberRecord(
            project_id="p-clinical",
            family_id="patent-family-1",  # 属于 project-dupilumab，p-clinical 未声明该族
            member_id="member-cross-1",
            jurisdiction="中国",
            member_status=_field(value="已授权"),
            fact_version_id="fact-cross-member",
            source_location="CNIPA/gazette-2",
        ),
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


def test_patent_rejects_term_with_unknown_member(tmp_path) -> None:
    """期限绑定未知/跨产品的法域成员必须失败关闭（跨法域拼接到期日）。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _patent_records()
    records["terms"] = (
        *records["terms"],
        PatentTermRecord(
            project_id="p-clinical",
            member_id="member-cn-1",  # 属于 project-dupilumab，p-clinical 未声明该成员
            term_zh="自申请日起 20 年",
            expiry=_field(value="2035-01-01"),
            fact_version_id="fact-term-cross",
            source_location="CNIPA/gazette-3",
        ),
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


def test_patent_record_rejects_blank_version_or_locator(tmp_path) -> None:
    """任一记录不得携带空白事实版本或来源定位。"""
    with pytest.raises(ValidationError):
        PatentFamilyRecord(
            project_id="project-dupilumab",
            family_id="patent-family-1",
            family_label_zh="空白版本专利族",
            fact_version_id=" ",
            source_location="patent-office/family-register-1",
        )
    with pytest.raises(ValidationError):
        PatentMemberRecord(
            project_id="project-dupilumab",
            family_id="patent-family-1",
            member_id="member-blank-loc",
            jurisdiction="中国",
            member_status=_field(value="已授权"),
            fact_version_id="fact-blank-loc",
            source_location="  ",
        )
    with pytest.raises(ValidationError):
        RegulatoryExclusivityRecord(
            project_id="project-dupilumab",
            exclusivity_kind=RegulatoryExclusivityKind.DATA_EXCLUSIVITY,
            jurisdiction="中国",
            expiry=_field(value="2025-06-19"),
            fact_version_id="",
            source_location="NMPA/exclusivity-notice-1",
        )


def test_patent_member_rejects_blank_jurisdiction(tmp_path) -> None:
    """法域成员必须携带单一确定法域，空白法域失败关闭。"""
    with pytest.raises(ValidationError):
        PatentMemberRecord(
            project_id="project-dupilumab",
            family_id="patent-family-1",
            member_id="member-blank-jur",
            jurisdiction="  ",
            member_status=_field(value="已授权"),
            fact_version_id="fact-blank-jur",
            source_location="CNIPA/gazette-4",
        )


def test_patent_term_rejects_blank_expiry(tmp_path) -> None:
    """期限必须携带到期日确定值或互斥状态，空白/缺失到期日失败关闭。"""
    with pytest.raises(ValidationError):
        PatentTermRecord(
            project_id="project-dupilumab",
            member_id="member-cn-1",
            term_zh="自申请日起 20 年",
            expiry=_field(),
            fact_version_id="fact-term-blank",
            source_location="CNIPA/gazette-5",
        )


# ── 视图不变量：不可变、确定性、无 Top-N 参数 ───────────────────────────────


def test_build_patent_has_no_top_n_or_drop_parameters() -> None:
    """专利与保护构建器不存在 Top-N、删除或降级出口。"""
    assert set(inspect.signature(build_patent_protection_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "families",
        "members",
        "scopes",
        "terms",
        "exclusivities",
        "results_posted_evidence",
    }


def test_patent_view_is_immutable_and_deterministic(tmp_path) -> None:
    """视图不可变：记录不可改写，同一锁定输入两次构建结果一致。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    first = build_patent_protection_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_patent_records(),
    )
    second = build_patent_protection_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_patent_records(),
    )
    assert first == second
    with pytest.raises(ValidationError):
        first.products[0].terms[0].expiry = "改写"


def test_patent_labels_are_professional_chinese(tmp_path) -> None:
    """独占类型标签为专业中文，不暴露后端枚举或工程状态。"""
    _, _, _, view = _patent_universe(tmp_path)
    labels = "".join(
        row.exclusivity_kind_zh for product in view.products for row in product.exclusivities
    )
    assert all("\u4e00" <= ch <= "\u9fff" for ch in labels)
    lowered = labels.lower()
    for token in ("data", "orphan", "pediatric", "biologics", "exclusivity", "snapshot", "binding"):
        assert token not in lowered
