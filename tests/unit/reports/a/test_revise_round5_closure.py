"""Task 5.2 第 5 轮（Luna round 4）反例回归：P1-1…P1-4。

每个 Luna 原始攻击原样转成回归测试；先 RED（旧实现接受攻击）后 GREEN
（修复后拒绝）。不做字符串黑名单扩张、不打补丁、不在工厂里预先规避攻击。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from test_revise_round3_closure import (
    _all_record_kwargs,
    _snapshot,
    _universe,
)

from ci_workflow.capabilities.lineage_registry import compute_scientific_content_digest
from ci_workflow.gates.models import GateEvaluationError
from ci_workflow.reports.a.pages import (
    AEvidenceContext,
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
from ci_workflow.storage.project_contract_store import ProjectContractStore
from ci_workflow.storage.snapshot_store import SnapshotStore

# ── P1-1 完整来源版本进入科学证据摘要 ───────────────────────────────────────


def _tamper_source_version(evidence: AEvidenceContext, **updates) -> AEvidenceContext:
    """仅改来源版本内容/审计字段，保留全部 ID 与 manifest。"""
    fragments = list(evidence.registry.verified_fragments)
    tampered = fragments[0].source_version.model_copy(update=updates)
    fragments[0] = fragments[0].model_copy(update={"source_version": tampered})
    tampered_registry = evidence.registry.model_copy(
        update={"verified_fragments": tuple(fragments)}
    )
    return evidence.model_copy(update={"registry": tampered_registry})


@pytest.mark.parametrize(
    "updates",
    [
        {"content_sha256": "0" * 64},
        {"content_relative_path": "forged/source.pdf"},
        {"acquired_at": datetime(2099, 1, 1, tzinfo=UTC)},
        {"media_type": "application/pdf"},
        {"source_id": "forged-source"},
    ],
)
def test_source_version_field_tamper_rejected(tmp_path, updates) -> None:
    """仅改 source_version 内容/审计字段（保留 ID/locator/manifest）必须因
    摘要不匹配拒绝（AV01 入口验证）。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = _tamper_source_version(evidence, **updates)
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects,
            snapshot,
            forged,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_digest_includes_full_source_version(tmp_path) -> None:
    """摘要正向不漂移：完整 fragment+source_version+reopened 原文纳入，稳定。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    digest1 = compute_scientific_content_digest(evidence.registry)
    digest2 = compute_scientific_content_digest(evidence.registry)
    assert digest1 == digest2
    assert digest1 == evidence.manifest.scientific_content_digest
    # 只改 reopened 原文（与片段一致）也改变摘要。
    fragments = list(evidence.registry.verified_fragments)
    tampered = fragments[0].model_copy(
        update={"reopened_original_text": fragments[0].reopened_original_text + " "}
    )
    forged = evidence.registry.model_copy(update={"verified_fragments": (tampered, *fragments[1:])})
    assert compute_scientific_content_digest(forged) != digest1


# ── P1-2 当前合同权威移到 AEvidenceContext 之外 ─────────────────────────────


def test_full_contract_authority_replace_rejected(tmp_path) -> None:
    """攻击者整体替换合同根/持久化内容（含 context 内 contract_store），
    外部权威 store 保持原始：必须拒绝。"""

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
    forged_contract_store = ProjectContractStore(tmp_path / "forged-contracts")
    forged_contract_store.save(forged_contract)
    forged_context = evidence.model_copy(
        update={
            "locked": forged_locked,
            "manifest": forged_manifest,
            "project_contract": forged_contract,
            "store": forged_store,
            "contract_store": forged_contract_store,
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
    # 外部权威 store 仍为原始 store → 必须拒绝。
    with pytest.raises(GateEvaluationError):
        build_product_overview_view(
            projects,
            forged_snapshot,
            forged_context,
            bindings,
            authoritative_contract_store=evidence.contract_store,
        )


def test_authority_param_is_required_and_external(tmp_path) -> None:
    """8 个 build + 8 个 authoritative 入口必须携带显式外部权威 store 参数。"""
    import inspect

    builders = (
        build_landscape_view,
        build_product_overview_view,
        build_product_dossier_view,
        build_clinical_portfolio_view,
        build_regulatory_view,
        build_company_deal_view,
        build_patent_protection_view,
        build_history_edge_view,
    )
    authorities = (
        assert_landscape_view_authoritative,
        assert_product_overview_view_authoritative,
        assert_product_dossier_view_authoritative,
        assert_clinical_portfolio_view_authoritative,
        assert_regulatory_view_authoritative,
        assert_company_deal_view_authoritative,
        assert_patent_protection_view_authoritative,
        assert_history_edge_view_authoritative,
    )
    for fn in (*builders, *authorities):
        params = inspect.signature(fn).parameters
        assert "authoritative_contract_store" in params
        # 必填：无默认值。
        assert params["authoritative_contract_store"].default is inspect.Parameter.empty


def test_positive_authority_uses_external_store(tmp_path) -> None:
    """正向：真实外部 store 通过；8 个 authoritative 入口重建一致。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    landscape = build_landscape_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
    )
    assert_landscape_view_authoritative(
        landscape,
        projects=projects,
        snapshot=snapshot,
        evidence=evidence,
        bindings=bindings,
        authoritative_contract_store=evidence.contract_store,
    )
    dossier = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_all_record_kwargs(),
    )
    assert_product_dossier_view_authoritative(
        dossier,
        projects=projects,
        snapshot=snapshot,
        evidence=evidence,
        bindings=bindings,
        authoritative_contract_store=evidence.contract_store,
        **_all_record_kwargs(),
    )


# ── P1-3 结果绑定闭合产品、试验与来源血统 ───────────────────────────────────


def test_cross_product_result_binding_rejected(tmp_path) -> None:
    """把 project-dupilumab 的结果事实复制绑定到 p-clinical/NCT-clin-1 并加
    锚定试验：必须因事实实体/试验作用域不一致拒绝。"""
    from ci_workflow.reports.a.contracts import AnchorTrialRecord
    from ci_workflow.reports.a.pages import build_product_dossier_view

    projects, snapshot, bindings, evidence = _universe(tmp_path)
    # p-clinical 增加锚定试验（fact-v-1 已注册）。
    projects = [
        (
            project.model_copy(
                update={
                    "anchor_trials": (
                        AnchorTrialRecord(
                            trial_id="NCT-clin-1",
                            fact_version_ids=("fact-v-1",),
                        ),
                    )
                }
            )
            if project.project_id == "p-clinical"
            else project
        )
        for project in projects
    ]
    forged_bindings = tuple(
        binding.model_copy(
            update={
                "binding_id": f"{binding.binding_id}-copy",
                "object_id": "p-clinical",
                "trial_id": "NCT-clin-1",
            }
        )
        for binding in bindings
        if binding.binding_id in ("b-eff", "b-saf")
    )
    # 保留原绑定，仅追加伪造副本：原产品锚定仍满足，命中实体/试验作用域校验。
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            (*bindings, *forged_bindings),
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


def test_forged_result_source_location_rejected(tmp_path) -> None:
    """仅伪造结果绑定 source_location 必须拒绝。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = tuple(
        (
            binding.model_copy(update={"source_location": "forged/location"})
            if binding.binding_id == "b-eff"
            else binding
        )
        for binding in bindings
    )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


def test_forged_result_source_role_rejected(tmp_path) -> None:
    """仅伪造结果绑定 source_role（COMPANY_DISCLOSURE）必须拒绝。"""
    from ci_workflow.gates.models import SourceRole

    projects, snapshot, bindings, evidence = _universe(tmp_path)
    forged = tuple(
        (
            binding.model_copy(update={"source_role": SourceRole.COMPANY_DISCLOSURE})
            if binding.binding_id == "b-eff"
            else binding
        )
        for binding in bindings
    )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            forged,
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


# ── P1-4 结果事实和绑定唯一消费 ─────────────────────────────────────────────


def test_duplicate_binding_id_rejected(tmp_path) -> None:
    """复制 b-eff 仅改 binding_id：重复 binding_id 必须失败关闭。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    duplicate = next(b for b in bindings if b.binding_id == "b-eff").model_copy(
        update={"binding_id": "b-eff-duplicate"}
    )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            (*bindings, duplicate),
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


def test_duplicate_result_fact_rejected(tmp_path) -> None:
    """同一结果事实经复制 binding（改 binding_id）不得渲染两次。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    # 修改原 b-eff 的 binding_id 但保留事实 → 两个绑定都消费 fact-v-1。
    replaced = tuple(
        (
            binding.model_copy(update={"binding_id": "b-eff-a"})
            if binding.binding_id == "b-eff"
            else binding
        )
        for binding in bindings
    )
    duplicate = next(b for b in replaced if b.binding_id == "b-eff-a").model_copy(
        update={"binding_id": "b-eff-b"}
    )
    with pytest.raises(GateEvaluationError):
        build_product_dossier_view(
            projects,
            snapshot,
            evidence,
            (*replaced, duplicate),
            authoritative_contract_store=evidence.contract_store,
            **_all_record_kwargs(),
        )


def test_positive_result_bindings_unique_and_closed(tmp_path) -> None:
    """正向：疗效/安全各一条保持通过且唯一。"""
    projects, snapshot, bindings, evidence = _universe(tmp_path)
    view = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        authoritative_contract_store=evidence.contract_store,
        **_all_record_kwargs(),
    )
    dupilumab = view.dossier("project-dupilumab")
    assert len(dupilumab.core_efficacy_records) == 1
    assert len(dupilumab.safety_summary_records) == 1
    assert dupilumab.core_efficacy_records[0].fact_version_id == "fact-v-1"
    assert dupilumab.safety_summary_records[0].fact_version_id == "fact-v-2"
