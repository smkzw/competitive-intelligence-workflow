"""Task 5.2 第 4 轮（Luna round 3）反例回归：P1-1…P1-4、P2-5、P2-6。

每个可运行反例原样转成回归测试；先 RED（旧实现接受攻击）后 GREEN（修复后
拒绝）。不做字符串黑名单扩张、不打补丁、不在工厂里预先规避攻击。
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from _evidence_factory import build_evidence_context
from test_revise_round3_closure import (
    _all_record_kwargs,
    _company_records,
    _historical_statuses,
    _patent_records,
    _portfolio_records,
    _universe,
    _versioned_events,
)

from ci_workflow.gates.models import GateEvaluationError, GateEvidenceBinding
from ci_workflow.reports.a.pages import (
    AdjacentObservationRecord,
    AEvidenceContext,
    CompanyRelationshipRecord,
    GeographicRightsRecord,
    HistoricalStatusRecord,
    OrganizationRoleRecord,
    PatentMemberRecord,
    PatentScopeRecord,
    PatentTermRecord,
    PublicTermRecord,
    RegulatoryEventVersionRecord,
    TransactionEventRecord,
    build_clinical_portfolio_view,
    build_company_deal_view,
    build_history_edge_view,
    build_patent_protection_view,
    build_product_dossier_view,
    build_product_overview_view,
    build_regulatory_view,
)
from ci_workflow.reports.common.evidence_view import EvidenceField, EvidenceFieldState
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    SnapshotStore,
    compute_locked_snapshot,
)


def _snapshot_r4(
    *,
    product_ids: tuple[str, ...],
    trial_ids: tuple[str, ...],
    trial_products: dict[str, str],
    evidence_snapshot_id: str,
):
    from test_revise_round3_closure import _snapshot

    return _snapshot(
        product_ids=product_ids,
        trial_ids=trial_ids,
        trial_products=trial_products,
        evidence_snapshot_id=evidence_snapshot_id,
    )


def _field(value: str | None = None, state: EvidenceFieldState | None = None) -> EvidenceField:
    return EvidenceField(value=value, state=state)


# ── P1-1 锁定快照必须绑定证据注册表内容 ─────────────────────────────────────


def _tamper_registry_synchronized(
    evidence: AEvidenceContext,
    *,
    fact_version_id: str,
    new_raw: str,
) -> AEvidenceContext:
    """同步伪造：同时改写事实 raw_value 与其主片段 original_text，重算片段
    content_sha256，保留全部 ID/locator；清单与锁定快照保持原样。"""
    facts = list(evidence.registry.accepted_facts)
    fragments = list(evidence.registry.verified_fragments)
    for index, fact in enumerate(facts):
        if fact.fact_version_id != fact_version_id:
            continue
        fragment = next(
            item for item in fragments if item.fragment.fragment_id == fact.primary_fragment_id
        )
        fragment_index = fragments.index(fragment)
        tampered_fragment = fragment.fragment.model_copy(
            update={
                "original_text": new_raw,
                "content_sha256": hashlib.sha256(new_raw.encode("utf-8")).hexdigest(),
            }
        )
        tampered_verified = fragment.model_copy(
            update={
                "fragment": tampered_fragment,
                "reopened_original_text": new_raw,
            }
        )
        fragments[fragment_index] = tampered_verified
        facts[index] = fact.model_copy(update={"raw_value": new_raw})
    tampered_registry = evidence.registry.model_copy(
        update={
            "accepted_facts": tuple(facts),
            "verified_fragments": tuple(fragments),
        }
    )
    return evidence.model_copy(update={"registry": tampered_registry})


@pytest.mark.parametrize(
    ("builder", "fact_version_id", "new_raw"),
    [
        (build_clinical_portfolio_view, "fact-region-dup-cn", "III期 已完成 美国"),
        (build_regulatory_view, "fact-reg", "批准 2099-01-01 中国"),
        (build_company_deal_view, "fact-org-origin", "原研 伪造企业"),
        (build_patent_protection_view, "fact-term-cn", "自申请日起 20 年 2099-12-31"),
        (build_history_edge_view, "fact-hist-term", "终止 2099-12-31 境外"),
    ],
)
def test_synchronized_registry_forgery_rejected(
    tmp_path, builder, fact_version_id, new_raw
) -> None:
    """同步改写事实原文+片段原文+摘要（保留全部 ID/locator）必须因注册表
    内容不属于锁定快照而拒绝（AV04–AV08 各一条）。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _tamper_registry_synchronized(
        evidence, fact_version_id=fact_version_id, new_raw=new_raw
    )
    if builder is build_clinical_portfolio_view:
        kwargs = {"trial_region_records": _portfolio_records()}
    elif builder is build_regulatory_view:
        kwargs = {"versioned_events": _versioned_events()}
    elif builder is build_company_deal_view:
        kwargs = dict(_company_records())
    elif builder is build_patent_protection_view:
        kwargs = dict(_patent_records())
    else:
        kwargs = {
            "historical_statuses": _historical_statuses(),
            "adjacent_observations": (),
        }
    with pytest.raises(GateEvaluationError):
        builder(
            projects,
            snapshot,
            forged,
            bindings,
            authoritative_contract_store=forged.contract_store,
            **kwargs,
        )


def test_locked_recompute_matches_store_read(tmp_path) -> None:
    """正向一致性：compute_locked_snapshot == _lock == store.read 内容一致。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    recomputed = compute_locked_snapshot(
        kind="evidence",
        report=None,
        manifest=evidence.manifest.model_dump(mode="json"),
    )
    assert recomputed == evidence.locked
    stored = evidence.store.read(evidence.locked)
    # The wire format omits optional v2 fields for v1 snapshots; compare the
    # validated scientific manifest, not an expanded Pydantic serialization.
    assert EvidenceSnapshotManifest.model_validate(stored) == evidence.manifest
    assert recomputed.snapshot_id == evidence.locked.snapshot_id
    assert recomputed.sha256 == evidence.locked.sha256
    assert recomputed.byte_size == evidence.locked.byte_size


def test_digest_sole_defense_consistent_forgery_rejected(tmp_path) -> None:
    """注册表与记录同步伪造且展示自洽时，内容摘要是唯一防线：必须拒绝。"""
    from ci_workflow.reports.a.pages import CompanyRoleKind, OrganizationRoleRecord

    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged_evidence = _tamper_registry_synchronized(
        evidence, fact_version_id="fact-org-origin", new_raw="原研 伪造企业"
    )
    company = dict(_company_records())
    company["organization_roles"] = (
        OrganizationRoleRecord(
            project_id="project-dupilumab",
            organization_zh="伪造企业",
            role=CompanyRoleKind.ORIGINATOR,
            fact_version_id="fact-org-origin",
            source_location="company/press-release-1",
        ),
        *company["organization_roles"][1:],
    )
    with pytest.raises(GateEvaluationError):
        build_company_deal_view(
            projects,
            snapshot,
            forged_evidence,
            bindings,
            authoritative_contract_store=forged_evidence.contract_store,
            **company,
        )


# ── P1-2 当前项目合同必须来自独立权威边界 ───────────────────────────────────


def test_self_consistent_forged_future_context_rejected(tmp_path) -> None:
    """上下文内部自洽地把合同/清单/锁定快照/内容寻址存储/宇宙快照全改成
    version 999 / cutoff 2099 并重锁，仍必须因权威当前合同不匹配而拒绝。"""
    from test_revise_round3_closure import _snapshot

    projects, snapshot, bindings, evidence = _universe(tmp_path)
    future_cutoff = datetime(2099, 1, 1, tzinfo=UTC)
    forged_manifest = evidence.manifest.model_copy(
        update={"contract_version": 999, "data_cutoff": future_cutoff}
    )
    forged_store = SnapshotStore(tmp_path / "forged-snapshots")
    forged_locked = forged_store.lock_evidence_snapshot(forged_manifest.model_dump(mode="json"))
    forged_contract = evidence.project_contract.model_copy(
        update={"contract_version": 999, "data_cutoff": future_cutoff}
    )
    forged_context = evidence.model_copy(
        update={
            "locked": forged_locked,
            "manifest": forged_manifest,
            "project_contract": forged_contract,
            "store": forged_store,
        }
    )
    forged_snapshot = _snapshot(
        product_ids=snapshot.product_ids,
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
        },
        evidence_snapshot_id=forged_locked.snapshot_id,
    )
    # 权威合同存储仍持真实 v1 当前合同 → 必须拒绝。
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects,
            forged_snapshot,
            forged_context,
            bindings,
            authoritative_contract_store=forged_context.contract_store,
        )


def test_current_contract_authority_passes(tmp_path) -> None:
    """正向：权威当前合同与清单一致时构建通过；resume 重读不漂移。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    authoritative = evidence.contract_store.load_current(snapshot.project_id)
    assert authoritative == evidence.project_contract
    assert evidence.contract_store.reload(authoritative) == authoritative
    view = build_product_overview_view(
        projects, snapshot, evidence, bindings, authoritative_contract_store=evidence.contract_store
    )
    assert view.products


def test_context_contract_diverging_from_authority_rejected(tmp_path) -> None:
    """上下文合同与权威当前合同不一致（即使清单/锁定也自洽）必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged_contract = evidence.project_contract.model_copy(
        update={"contract_version": evidence.project_contract.contract_version + 1}
    )
    forged = evidence.model_copy(update={"project_contract": forged_contract})
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects, snapshot, forged, bindings, authoritative_contract_store=forged.contract_store
        )


# ── P1-3 疗效/安全摘要必须完整绑定原子事实 ──────────────────────────────────


def _forged_binding(bindings, binding_id: str, **updates) -> tuple[GateEvidenceBinding, ...]:
    return tuple(
        (binding.model_copy(update=updates) if binding.binding_id == binding_id else binding)
        for binding in bindings
    )


def test_efficacy_denominator_mismatch_rejected(tmp_path) -> None:
    """事实分母 224、绑定分母 999：疗效摘要必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _forged_binding(bindings, "b-eff", denominator=999)
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


def test_safety_denominator_mismatch_rejected(tmp_path) -> None:
    """事实分母 224、绑定分母 999：安全摘要必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _forged_binding(bindings, "b-saf", denominator=999)
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"numeric_value": 999.9},
        {"unit": "伪造单位"},
        {"analysis_population": "伪造人群"},
        {"timepoint": "伪造时间点"},
        {"treatment_group": "伪造治疗组"},
    ],
)
def test_efficacy_field_mismatches_rejected(tmp_path, updates) -> None:
    """疗效逐字段错配（数值/单位/人群/时间点/治疗组）必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _forged_binding(bindings, "b-eff", **updates)
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"numeric_value": 0.1},
        {"unit": "伪造安全单位"},
        {"time_window": "伪造时间窗"},
        {"analysis_population": "伪造人群"},
    ],
)
def test_safety_field_mismatches_rejected(tmp_path, updates) -> None:
    """安全逐字段错配（数值/单位/时间窗/人群）必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _forged_binding(bindings, "b-saf", **updates)
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


# ── P1-4 AV04–AV08 所有扩展 DTO 重新验证 ────────────────────────────────────


def test_av04_forged_region_rejected(tmp_path) -> None:
    """合法临床组合记录 model_copy 把 region 改成'美国'（事实原文同为美国）
    必须被扩展记录重新验证拒绝（地域闭合是唯一防线）。"""
    from test_revise_round3_closure import _facts

    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged_facts = dict(_facts())
    forged_facts["fact-region-dup-cn"] = (
        "project-dupilumab",
        "clinical_trial_region",
        "III期 已完成 美国",
        "CT.gov/results/portfolio-1",
    )
    forged_evidence = build_evidence_context(
        tmp_path, project_id="report-universe", facts=forged_facts
    )
    forged_snapshot = _snapshot_r4(
        product_ids=snapshot.product_ids,
        trial_ids=("NCT02407756", "NCT-clin-1", "NCT-term-1"),
        trial_products={
            "NCT02407756": "project-dupilumab",
            "NCT-clin-1": "p-clinical",
            "NCT-term-1": "p-terminated",
        },
        evidence_snapshot_id=forged_evidence.locked.snapshot_id,
    )
    records = list(_portfolio_records())
    records[0] = records[0].model_copy(update={"region": "美国"})
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            forged_snapshot,
            forged_evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


def test_av04_forged_evidence_field_dual_rejected(tmp_path) -> None:
    """EvidenceField 同时含 value 与互斥 state（model_copy）必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    records = list(_portfolio_records())
    forged_phase = records[0].phase.model_copy(
        update={"state": EvidenceFieldState.NOT_YET_DISCLOSED}
    )
    records[0] = records[0].model_copy(update={"phase": forged_phase})
    with pytest.raises(GateEvaluationError):
        build_clinical_portfolio_view(
            projects,
            snapshot,
            evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


@pytest.mark.parametrize(
    "record, updates",
    [
        pytest.param(
            lambda: OrganizationRoleRecord(
                project_id="project-dupilumab",
                organization_zh="再生元",
                role=__import__(
                    "ci_workflow.reports.a.pages", fromlist=["CompanyRoleKind"]
                ).CompanyRoleKind.ORIGINATOR,
                fact_version_id="fact-org-origin",
                source_location="company/press-release-1",
            ),
            {"organization_zh": "   "},
            id="AV06-org-blank",
        ),
        pytest.param(
            lambda: CompanyRelationshipRecord(
                project_id="project-dupilumab",
                counterparty_zh="赛诺菲",
                relationship=__import__(
                    "ci_workflow.reports.a.pages", fromlist=["CompanyRelationshipKind"]
                ).CompanyRelationshipKind.COLLABORATION,
                fact_version_id="fact-rel-collab",
                source_location="company/contract-summary-1",
            ),
            {"counterparty_zh": ""},
            id="AV06-rel-blank",
        ),
        pytest.param(
            lambda: GeographicRightsRecord(
                project_id="project-dupilumab",
                region="中国",
                rights_zh="中国大陆独家商业化权利",
                fact_version_id="fact-rights-cn",
                source_location="company/contract-summary-2",
            ),
            {"region": "全球"},
            id="AV06-rights-region",
        ),
        pytest.param(
            lambda: TransactionEventRecord(
                project_id="project-dupilumab",
                event_kind=__import__(
                    "ci_workflow.reports.a.pages", fromlist=["TransactionEventKind"]
                ).TransactionEventKind.LICENSE,
                event_date=_field(value="2019-06-01"),
                fact_version_id="fact-tx-license",
                source_location="company/press-release-3",
            ),
            {"event_date": None},
            id="AV06-tx-dual-field",
        ),
        pytest.param(
            lambda: PublicTermRecord(
                project_id="project-dupilumab",
                term_zh="首付款 2 亿美元，里程碑付款最高 10 亿美元",
                fact_version_id="fact-term-milestone",
                source_location="company/press-release-4",
            ),
            {"term_zh": " "},
            id="AV06-term-blank",
        ),
        pytest.param(
            lambda: PatentMemberRecord(
                project_id="project-dupilumab",
                family_id="patent-family-1",
                member_id="member-cn-1",
                jurisdiction="中国",
                member_status=_field(value="已授权"),
                fact_version_id="fact-member-cn",
                source_location="CNIPA/gazette-1",
            ),
            {"jurisdiction": "  "},
            id="AV07-member-jurisdiction",
        ),
        pytest.param(
            lambda: PatentTermRecord(
                project_id="project-dupilumab",
                member_id="member-cn-1",
                term_zh="自申请日起 20 年",
                expiry=_field(value="2034-05-12"),
                fact_version_id="fact-term-cn",
                source_location="CNIPA/gazette-1",
            ),
            {"expiry": None},
            id="AV07-term-dual-field",
        ),
        pytest.param(
            lambda: PatentScopeRecord(
                project_id="project-dupilumab",
                family_id="patent-family-1",
                scope_zh="覆盖含目标抗体的组合物、制剂及其治疗用途",
                fact_version_id="fact-scope-1",
                source_location="patent-office/claims-summary-1",
            ),
            {"scope_zh": ""},
            id="AV07-scope-blank",
        ),
        pytest.param(
            lambda: HistoricalStatusRecord(
                project_id="p-clinical",
                regulatory_event_id="ev-pause-1",
                status_kind=__import__(
                    "ci_workflow.reports.a.pages", fromlist=["HistoricalStatusKind"]
                ).HistoricalStatusKind.SUSPENDED,
                jurisdiction="中国",
                status_date=_field(value="2023-03-01"),
                fact_version_id="fact-hist-suspend",
                source_location="registry/status-history-1",
            ),
            {"jurisdiction": "全球"},
            id="AV08-status-jurisdiction",
        ),
        pytest.param(
            lambda: AdjacentObservationRecord(
                project_id="p-preclinical",
                relation_basis_zh="靶点与目标适应症机制相关，适应症关系未确立，独立观察",
                fact_version_id="fact-adjacent-1",
                source_location="literature/review-1",
            ),
            {"relation_basis_zh": " "},
            id="AV08-adjacent-blank",
        ),
    ],
)
def test_extension_dto_model_copy_bypass_rejected(tmp_path, record, updates) -> None:
    """AV06–AV08 扩展记录 model_copy 绕过模型校验必须被重新验证拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    dual_event = EvidenceField.model_construct(
        value="2019-06-01", state=EvidenceFieldState.NOT_YET_DISCLOSED
    )
    dual_expiry = EvidenceField.model_construct(
        value="2034-05-12", state=EvidenceFieldState.NOT_YET_DISCLOSED
    )
    forged = record().model_copy(
        update=(
            {"event_date": dual_event}
            if updates == {"event_date": None}
            else ({"expiry": dual_expiry} if updates == {"expiry": None} else updates)
        )
    )
    if isinstance(
        forged,
        (
            OrganizationRoleRecord,
            CompanyRelationshipRecord,
            GeographicRightsRecord,
            TransactionEventRecord,
            PublicTermRecord,
        ),
    ):
        records = dict(_company_records())
        if isinstance(forged, OrganizationRoleRecord):
            records["organization_roles"] = (forged, *records["organization_roles"][1:])
        elif isinstance(forged, CompanyRelationshipRecord):
            records["relationships"] = (forged,)
        elif isinstance(forged, GeographicRightsRecord):
            records["geographic_rights"] = (forged,)
        elif isinstance(forged, TransactionEventRecord):
            records["transaction_events"] = (forged,)
        else:
            records["public_terms"] = (forged,)
        with pytest.raises(GateEvaluationError):
            build_company_deal_view(
                projects,
                snapshot,
                evidence,
                bindings,
                authoritative_contract_store=evidence.contract_store,
                **records,
            )
    elif isinstance(forged, (PatentMemberRecord, PatentTermRecord, PatentScopeRecord)):
        records = dict(_patent_records())
        if isinstance(forged, PatentMemberRecord):
            records["members"] = (forged, *records["members"][1:])
        elif isinstance(forged, PatentScopeRecord):
            records["scopes"] = (forged,)
        else:
            records["terms"] = (forged, *records["terms"][1:])
        with pytest.raises(GateEvaluationError):
            build_patent_protection_view(
                projects,
                snapshot,
                evidence,
                bindings,
                authoritative_contract_store=evidence.contract_store,
                **records,
            )
    else:
        with pytest.raises(GateEvaluationError):
            build_history_edge_view(
                projects,
                snapshot,
                evidence,
                bindings,
                authoritative_contract_store=evidence.contract_store,
                historical_statuses=(forged,)
                if isinstance(forged, HistoricalStatusRecord)
                else _historical_statuses(),
                adjacent_observations=(forged,)
                if isinstance(forged, AdjacentObservationRecord)
                else (),
            )


# ── P2-5 NFKC 等价日期 ───────────────────────────────────────────────────────


def test_fullwidth_date_equivalent_accepted(tmp_path) -> None:
    """全角等价日期 '２０２０-０６-１９' 与 '2020-06-19' 比较一致并规范输出。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    records = tuple(
        RegulatoryEventVersionRecord(
            project_id=record.project_id,
            event_id=record.event_id,
            event_kind=record.event_kind,
            jurisdiction=record.jurisdiction,
            event_date=_field(value="２０２０-０６-１９")
            if record.event_id == "ev-approval-cn"
            else record.event_date,
            fact_version_id=record.fact_version_id,
            source_location=record.source_location,
        )
        if record.project_id == "project-dupilumab"
        else record
        for record in _versioned_events()
    )
    view = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        records,
        authoritative_contract_store=evidence.contract_store,
    )
    dupilumab = view.product("project-dupilumab")
    assert tuple(row.event_date for row in dupilumab.china_events) == ("2020-06-19",)


def test_non_zero_padded_iso_date_normalized(tmp_path) -> None:
    """非零填充 ISO 日期 '2020-6-19' 与 '2020-06-19' 等价，输出规范 ISO。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    records = tuple(
        RegulatoryEventVersionRecord(
            project_id=record.project_id,
            event_id=record.event_id,
            event_kind=record.event_kind,
            jurisdiction=record.jurisdiction,
            event_date=_field(value="2020-6-19")
            if record.event_id == "ev-approval-cn"
            else record.event_date,
            fact_version_id=record.fact_version_id,
            source_location=record.source_location,
        )
        if record.project_id == "project-dupilumab"
        else record
        for record in _versioned_events()
    )
    view = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        records,
        authoritative_contract_store=evidence.contract_store,
    )
    dupilumab = view.product("project-dupilumab")
    assert tuple(row.event_date for row in dupilumab.china_events) == ("2020-06-19",)


def test_invalid_date_rejected(tmp_path) -> None:
    """非法日期（2020-13-45）必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    records = tuple(
        RegulatoryEventVersionRecord(
            project_id=record.project_id,
            event_id=record.event_id,
            event_kind=record.event_kind,
            jurisdiction=record.jurisdiction,
            event_date=_field(value="2020-13-45"),
            fact_version_id=record.fact_version_id,
            source_location=record.source_location,
        )
        if record.event_id == "ev-approval-cn"
        else record
        for record in _versioned_events()
    )
    with pytest.raises((GateEvaluationError, ValueError)):
        build_regulatory_view(
            projects,
            snapshot,
            evidence,
            bindings,
            records,
            authoritative_contract_store=evidence.contract_store,
        )


# ── P2-6 中文原生显示 ────────────────────────────────────────────────────────


def test_chinese_punctuation_preserved_in_display(tmp_path) -> None:
    """中文全角标点保留：'，' 不得被 NFKC 显示成 ','。"""
    record = AdjacentObservationRecord(
        project_id="p-preclinical",
        relation_basis_zh="靶点与目标适应症机制相关，适应症关系未确立，独立观察",
        fact_version_id="fact-adjacent-1",
        source_location="literature/review-1",
    )
    assert record.relation_basis_zh == "靶点与目标适应症机制相关，适应症关系未确立，独立观察"
    assert "，" in record.relation_basis_zh
    assert "," not in record.relation_basis_zh


def test_engineering_word_variants_still_rejected() -> None:
    """P2 工程词变体拦截不因显示规范化拆分而削弱。"""
    from pydantic import ValidationError

    for banned in ("Gate", "BackendState", "back-end", "model-copy", "ｂａｃｋｅｎｄ"):
        with pytest.raises(ValidationError):
            AdjacentObservationRecord(
                project_id="p-preclinical",
                relation_basis_zh=f"机制观察 {banned} 相关内容",
                fact_version_id="fact-adjacent-1",
                source_location="literature/review-1",
            )
