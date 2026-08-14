"""Task 5.2 AV06 企业与交易视图：组织角色/关系/地域权益/交易/条款分离。

合同断言（先失败后通过）：
- 企业与交易视图绑定单一锁定快照身份，产品集必须与 ``snapshot.product_ids``
  精确一一对应且顺序一致；
- 原研/开发者/许可方/被许可方组织角色、合作关系、地域权益、交易事件与
  公开条款是五种独立类型化版本化记录，各自绑定产品、不可变事实版本与
  精确来源定位，绝不混写进一个字段；
- 未知产品、同类记录重复、空白事实版本/来源定位均失败关闭；
- 无合作/无交易/无条款的产品保留显式空集合（空记录不失败、不删除），
  不允许用占位值或推断条款填补；
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
    CompanyDealProduct,
    CompanyDealView,
    CompanyRelationshipKind,
    CompanyRelationshipRecord,
    CompanyRoleKind,
    GeographicRightsRecord,
    OrganizationRoleRecord,
    PublicTermRecord,
    TransactionEventKind,
    TransactionEventRecord,
    build_company_deal_view,
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


class CompanyRecordBundle(TypedDict):
    """五类版本化记录的类型化捆绑：键名与构建器关键字一致。"""

    organization_roles: tuple[OrganizationRoleRecord, ...]
    relationships: tuple[CompanyRelationshipRecord, ...]
    geographic_rights: tuple[GeographicRightsRecord, ...]
    transaction_events: tuple[TransactionEventRecord, ...]
    public_terms: tuple[PublicTermRecord, ...]


def _company_records() -> CompanyRecordBundle:
    """五类独立版本化记录：组织角色/关系/地域权益/交易事件/公开条款。"""
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


def _company_universe(
    tmp_path,
) -> tuple[
    list[AProjectContract],
    ApplicableUniverseSnapshot,
    AEvidenceContext,
    CompanyDealView,
]:
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    view = build_company_deal_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_company_records(),
    )
    return projects, snapshot, evidence, view


# ── AV06 精确验收节点 ───────────────────────────────────────────────────────


def test_company_relationships_rights_and_transactions_are_not_conflated(tmp_path) -> None:
    """组织角色、关系、地域权益、交易事件与公开条款分列，不混写。"""
    projects, snapshot, _, view = _company_universe(tmp_path)
    assert tuple(product.project_id for product in view.products) == snapshot.product_ids

    dupilumab = next(p for p in view.products if p.project_id == "project-dupilumab")
    assert tuple((row.role_zh, row.organization_zh) for row in dupilumab.organization_roles) == (
        ("原研", "再生元"),
        ("开发者", "赛诺菲"),
    )
    assert tuple((row.relationship_zh, row.counterparty_zh) for row in dupilumab.relationships) == (
        ("合作", "赛诺菲"),
    )
    assert tuple((row.region, row.rights_zh) for row in dupilumab.geographic_rights) == (
        ("中国", "中国大陆独家商业化权利"),
    )
    assert tuple((row.event_kind_zh, row.event_date) for row in dupilumab.transaction_events) == (
        ("许可交易", "2019-06-01"),
    )
    assert tuple(row.term_zh for row in dupilumab.public_terms) == (
        # 展示保留自然中文标点：全角逗号不被 NFKC 改写。
        "首付款 2 亿美元，里程碑付款最高 10 亿美元",
    )
    for role_row in dupilumab.organization_roles:
        assert role_row.fact_version_id
        assert role_row.source_location
    for relationship_row in dupilumab.relationships:
        assert relationship_row.fact_version_id
        assert relationship_row.source_location
    for rights_row in dupilumab.geographic_rights:
        assert rights_row.fact_version_id
        assert rights_row.source_location
    for transaction_row in dupilumab.transaction_events:
        assert transaction_row.fact_version_id
        assert transaction_row.source_location
    for term_row in dupilumab.public_terms:
        assert term_row.fact_version_id
        assert term_row.source_location

    # 无合作/无交易/无条款产品保留显式空集合：不失败、不删除、不占位。
    for product in view.products:
        if product.project_id != "project-dupilumab":
            assert product.organization_roles == ()
            assert product.relationships == ()
            assert product.geographic_rights == ()
            assert product.transaction_events == ()
            assert product.public_terms == ()


def test_company_view_keeps_five_typed_collections_separate(tmp_path) -> None:
    """视图按五类独立类型保存，任何两类不得共享字段或互相替代。"""
    _, _, _, view = _company_universe(tmp_path)
    dupilumab = next(p for p in view.products if p.project_id == "project-dupilumab")
    assert isinstance(dupilumab, CompanyDealProduct)
    # 交易事件字段与公开条款字段类型互异。
    tx_fields = {field for field in type(dupilumab.transaction_events[0]).model_fields}
    term_fields = {field for field in type(dupilumab.public_terms[0]).model_fields}
    assert tx_fields != term_fields
    assert "term_zh" not in tx_fields
    assert "event_kind_zh" not in term_fields
    # 组织角色与关系字段互异。
    org_fields = {field for field in type(dupilumab.organization_roles[0]).model_fields}
    rel_fields = {field for field in type(dupilumab.relationships[0]).model_fields}
    assert "role_zh" in org_fields and "role_zh" not in rel_fields
    assert "counterparty_zh" in rel_fields and "counterparty_zh" not in org_fields


# ── 版本化记录：未知产品、重复、空白定位 ────────────────────────────────────


def test_company_rejects_unknown_product_record(tmp_path) -> None:
    """任一记录引用未知产品必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _company_records()
    records["transaction_events"] = (
        *records["transaction_events"],
        TransactionEventRecord(
            project_id="p-extra",
            event_kind=TransactionEventKind.MERGER_ACQUISITION,
            event_date=_field(value="2024-01-01"),
            fact_version_id="fact-extra",
            source_location="company/press-release-5",
        ),
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


def test_company_rejects_duplicate_organization_role(tmp_path) -> None:
    """同一产品同一组织同一角色重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _company_records()
    records["organization_roles"] = (
        *records["organization_roles"],
        OrganizationRoleRecord(
            project_id="project-dupilumab",
            organization_zh="再生元",
            role=CompanyRoleKind.ORIGINATOR,
            fact_version_id="fact-org-origin-dup",
            source_location="company/press-release-dup",
        ),
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


def test_company_rejects_duplicate_transaction_event(tmp_path) -> None:
    """同一产品同一交易类型同一日期重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _company_records()
    records["transaction_events"] = (
        *records["transaction_events"],
        TransactionEventRecord(
            project_id="project-dupilumab",
            event_kind=TransactionEventKind.LICENSE,
            event_date=_field(value="2019-06-01"),
            fact_version_id="fact-tx-dup",
            source_location="company/press-release-dup",
        ),
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


def test_company_rejects_duplicate_geographic_rights(tmp_path) -> None:
    """同一产品同一地域同一权益描述重复记录必须失败关闭。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    records = _company_records()
    records["geographic_rights"] = (
        *records["geographic_rights"],
        GeographicRightsRecord(
            project_id="project-dupilumab",
            region="中国",
            rights_zh="中国大陆独家商业化权利",
            fact_version_id="fact-rights-dup",
            source_location="company/contract-summary-dup",
        ),
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


def test_company_record_rejects_blank_version_or_locator(tmp_path) -> None:
    """任一记录不得携带空白事实版本或来源定位。"""
    with pytest.raises(ValidationError):
        OrganizationRoleRecord(
            project_id="project-dupilumab",
            organization_zh="再生元",
            role=CompanyRoleKind.ORIGINATOR,
            fact_version_id=" ",
            source_location="company/press-release-1",
        )
    with pytest.raises(ValidationError):
        TransactionEventRecord(
            project_id="project-dupilumab",
            event_kind=TransactionEventKind.LICENSE,
            event_date=_field(value="2019-06-01"),
            fact_version_id="fact-tx-license",
            source_location="",
        )
    with pytest.raises(ValidationError):
        PublicTermRecord(
            project_id="project-dupilumab",
            term_zh=" ",
            fact_version_id="fact-term-milestone",
            source_location="company/press-release-4",
        )


def test_company_geographic_rights_rejects_unknown_region(tmp_path) -> None:
    """地域权益只接受中国/境外分轨，其余值必须失败关闭。"""
    with pytest.raises(ValidationError):
        GeographicRightsRecord(
            project_id="project-dupilumab",
            region="全球",
            rights_zh="全球商业化权利",
            fact_version_id="fact-rights-global",
            source_location="company/contract-summary-3",
        )


# ── 视图不变量：不可变、确定性、无 Top-N 参数 ───────────────────────────────


def test_build_company_deal_has_no_top_n_or_drop_parameters() -> None:
    """企业与交易构建器不存在 Top-N、删除或降级出口。"""
    assert set(inspect.signature(build_company_deal_view).parameters) == {
        "projects",
        "snapshot",
        "evidence",
        "authoritative_contract_store",
        "bindings",
        "organization_roles",
        "relationships",
        "geographic_rights",
        "transaction_events",
        "public_terms",
        "results_posted_evidence",
    }


def test_company_deal_view_is_immutable_and_deterministic(tmp_path) -> None:
    """视图不可变：记录不可改写，同输入两次构建结果一致。"""
    projects, snapshot, bindings, evidence = _mixed_universe(tmp_path)
    first = build_company_deal_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_company_records(),
    )
    second = build_company_deal_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_company_records(),
    )
    assert first == second
    with pytest.raises(ValidationError):
        first.products[0].transaction_events[0].event_date = "改写"


def test_company_labels_are_professional_chinese(tmp_path) -> None:
    """角色/关系/交易类型标签为专业中文，不暴露后端枚举或工程状态。"""
    _, _, _, view = _company_universe(tmp_path)
    labels = "".join(
        [
            *(row.role_zh for p in view.products for row in p.organization_roles),
            *(row.relationship_zh for p in view.products for row in p.relationships),
            *(row.event_kind_zh for p in view.products for row in p.transaction_events),
        ]
    )
    assert all("\u4e00" <= ch <= "\u9fff" for ch in labels)
    lowered = labels.lower()
    for token in (
        "originator",
        "developer",
        "licensor",
        "licensee",
        "collaboration",
        "merger",
        "acquisition",
        "snapshot",
        "binding",
    ):
        assert token not in lowered
