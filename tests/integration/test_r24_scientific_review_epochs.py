"""R24 科学复核 epoch 生命周期回归族（ci-r24-133）。

同项目重复科学复核必须经由显式、版本化的 epoch 推进完成：预期前驱上下文
（摘要等于当前活跃上下文）、同项目/同报告、真实新科学上下文（摘要不等于
活跃或任何历史纪元）与真实门户字节（重验磁盘）全部绑定后，才在版本化目录
物化新纪元上下文/请求并原子激活指针；staged 失败保留旧活跃作用域，精确
重试幂等。历史纪元的上下文/请求/回执/签发/结论字节保持逐字节不可变，
既有单例布局的隐式拒绝语义原样保留。活跃 epoch 是 issuer 签发、回执重验、
晋级与来源接受授权的唯一作用域；旧回执无法授权新纪元。新真实复核可精确
复用此前已接受的同一版本来源原子（字节与状态保留），user_modified/拒绝/
替代/未解决冲突仍然失败关闭，绝不把用户修订或旧冲突晋升为已接受。

首次运行以 RED 起族：显式 epoch API 与 epoch 指针存储助手尚不存在（收集期
导入失败）。测试中的 issuer runner 是单元模拟，不是真实临床接受。
"""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application import scientific_review_transition as transition
from ci_workflow.application.fresh_research_ingestion import (
    ResearchEvidenceLineage,
    ingest_research_evidence,
)
from ci_workflow.application.fresh_research_primitives import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.review_issuer import (
    ExternalProcessResult,
    issue_review_receipt,
    review_issuance_record_path,
    verify_receipt_issuance,
)
from ci_workflow.application.scientific_review_transition import (
    RENDERED_UNREVIEWED,
    SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE,
    ScientificReviewTransitionError,
    active_scientific_review_scope,
    advance_scientific_review_epoch,
    build_scientific_review_context,
    capture_portal_artifact_binding,
    promote_rendered_candidate,
    publish_production_context,
    publish_scientific_review_request,
    reload_production_context,
    scientific_review_receipt_path,
)
from ci_workflow.application.source_fact_acceptance import (
    SourceFactAcceptanceError,
    accept_reviewed_source_facts,
    source_fact_acceptance_decision_path,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.hosts.receipt import (
    HostExecutableEvidence as ReviewExecutableEvidence,
)
from ci_workflow.hosts.receipt import (
    HostSessionBinding as ReviewHostSession,
)
from ci_workflow.qc.scientific import (
    ScientificQcCurrentContext,
    ScientificQcReviewBundle,
    ScientificQcVerdict,
)
from ci_workflow.storage.scientific_review_epoch import (
    epoch_pointer_path,
    epoch_receipt_path,
    read_epoch_pointer,
)
from ci_workflow.storage.sqlite import open_database

# ── 时间线：每个 epoch 一段自洽的生产/复核/签发/推进/接受时间 ──────────────────

EPOCH_TIMELINES: dict[int, dict[str, datetime]] = {
    0: {
        "produced": datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
        "started": datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
        "finished": datetime(2026, 9, 5, 2, 30, tzinfo=UTC),
        "issued": datetime(2026, 9, 5, 3, 0, tzinfo=UTC),
    },
    1: {
        "produced": datetime(2026, 9, 5, 4, 0, tzinfo=UTC),
        "started": datetime(2026, 9, 5, 5, 0, tzinfo=UTC),
        "finished": datetime(2026, 9, 5, 5, 30, tzinfo=UTC),
        "issued": datetime(2026, 9, 5, 6, 0, tzinfo=UTC),
    },
    2: {
        "produced": datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
        "started": datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
        "finished": datetime(2026, 9, 5, 9, 30, tzinfo=UTC),
        "issued": datetime(2026, 9, 5, 10, 0, tzinfo=UTC),
    },
}
ADVANCED_AT = {
    1: datetime(2026, 9, 5, 4, 30, tzinfo=UTC),
    2: datetime(2026, 9, 5, 8, 30, tzinfo=UTC),
}
ACCEPTED_AT = {
    0: datetime(2026, 9, 5, 3, 30, tzinfo=UTC),
    1: datetime(2026, 9, 5, 6, 30, tzinfo=UTC),
}
VALID_UNTIL = datetime(2099, 1, 1, tzinfo=UTC)
DATA_CUTOFF = datetime(2026, 7, 31, 15, 59, 59, tzinfo=UTC)

HOST_PATH = "/opt/homebrew/bin/codex"
REVIEW_ARGV = ("exec", "scientific-review")
REVIEW_SESSION = ReviewHostSession(
    session_id="review-session-9", launcher_pid=777, launcher_parent_pid=1
)
HOST_EXECUTABLE = ReviewExecutableEvidence(
    provenance="path_resolved",
    path=HOST_PATH,
    resolved_realpath=HOST_PATH,
    version="codex-cli 0.42.0",
)


# ── 研究材料：与既有 R24 验收族同一形态的真实摄取输入 ─────────────────────────


def _base_sources() -> tuple[SourceCapture, ...]:
    produced = EPOCH_TIMELINES[0]["produced"]
    return (
        SourceCapture(
            source_id="src-primary",
            route_id="route-primary",
            source_type="registry",
            title="主要登记来源",
            url="https://example.org/primary",
            query_or_identifier="NCT00000001",
            language="en",
            access_method="public_registry",
            media_type="application/json",
            content_text=json.dumps(
                {"result": {"quote": "客观缓解率 80%（32/40）。", "count": "32/40"}},
                ensure_ascii=False,
            ),
            acquired_at=produced,
            published_at=produced,
            effective_at=None,
            first_disclosed_at=produced,
            locator=EvidenceLocator(
                document_role="测试用主要登记来源", field_path="$.result.quote"
            ),
        ),
        SourceCapture(
            source_id="src-supporting",
            route_id="route-supporting",
            source_type="registry",
            title="辅助来源",
            url="https://example.org/supporting",
            query_or_identifier="NCT00000002",
            language="en",
            access_method="public_registry",
            media_type="application/json",
            content_text=json.dumps(
                {"finding": {"text": "安全性事件例数为 12 例。"}}, ensure_ascii=False
            ),
            acquired_at=produced,
            published_at=produced,
            effective_at=None,
            first_disclosed_at=produced,
            locator=EvidenceLocator(
                document_role="测试用辅助来源", field_path="$.finding.text"
            ),
        ),
    )


def _base_facts() -> tuple[ResearchFact, ...]:
    return (
        ResearchFact(
            fact_id="fact-1",
            row_ref="safety:f1",
            entity_id="product-alpha",
            entity_type="product",
            canonical_name="产品甲",
            field_id="orr",
            raw_value="80% (32/40)",
            normalized_value="80.0",
            disclosure_state="reported_value",
            source_id="src-primary",
            locator=EvidenceLocator(
                document_role="测试用主要登记来源", field_path="$.result.quote"
            ),
            original_text="客观缓解率 80%（32/40）。",
        ),
        ResearchFact(
            fact_id="fact-2",
            row_ref="safety:f2",
            entity_id="product-alpha",
            entity_type="product",
            canonical_name="产品甲",
            field_id="orr_count",
            raw_value="32/40",
            normalized_value=None,
            disclosure_state="reported_value",
            source_id="src-primary",
            locator=EvidenceLocator(
                document_role="测试用主要登记来源", field_path="$.result.count"
            ),
            original_text="32/40",
        ),
        ResearchFact(
            fact_id="fact-3",
            row_ref="safety:f3",
            entity_id="product-alpha",
            entity_type="product",
            canonical_name="产品甲",
            field_id="safety_events",
            raw_value="12 例",
            normalized_value="12",
            disclosure_state="reported_value",
            source_id="src-supporting",
            locator=EvidenceLocator(
                document_role="测试用辅助来源", field_path="$.finding.text"
            ),
            original_text="安全性事件例数为 12 例。",
        ),
    )


def _base_claims() -> tuple[ResearchClaim, ...]:
    return (
        ResearchClaim(
            claim_id="claim-primary",
            claim_text="主要来源报告的客观缓解率为 80%。",
            claim_kind="direct_evidence",
            fact_ids=("fact-1", "fact-2"),
        ),
        ResearchClaim(
            claim_id="claim-supporting",
            claim_text="辅助来源报告安全性事件 12 例。",
            claim_kind="direct_evidence",
            fact_ids=("fact-3",),
        ),
    )


@dataclass(frozen=True)
class _Materials:
    """一次摄取的完整材料：来源/事实/声明与报告科学内容摘要。"""

    sources: tuple[SourceCapture, ...]
    facts: tuple[ResearchFact, ...]
    claims: tuple[ResearchClaim, ...]
    content_digest: str


def _base_materials(epoch: int) -> _Materials:
    return _Materials(
        sources=_base_sources(),
        facts=_base_facts(),
        claims=_base_claims(),
        content_digest=hashlib.sha256(
            f"research-content-e{epoch}".encode()
        ).hexdigest(),
    )


def _late_materials(epoch: int) -> _Materials:
    """epoch 1 新增无关来源/事实/声明：混合“已接受 + 候选”精确集合。"""
    produced = EPOCH_TIMELINES[epoch]["produced"]
    late_source = SourceCapture(
        source_id="src-late",
        route_id="route-late",
        source_type="registry",
        title="后续披露来源",
        url="https://example.org/late",
        query_or_identifier="NCT00000003",
        language="en",
        access_method="public_registry",
        media_type="application/json",
        content_text=json.dumps(
            {"update": {"text": "后续披露：持续缓解时间为 9.1 个月。"}},
            ensure_ascii=False,
        ),
        acquired_at=produced,
        published_at=produced,
        effective_at=None,
        first_disclosed_at=produced,
        locator=EvidenceLocator(
            document_role="测试用后续披露来源", field_path="$.update.text"
        ),
    )
    late_fact = ResearchFact(
        fact_id="fact-4",
        row_ref="safety:f4",
        entity_id="product-alpha",
        entity_type="product",
        canonical_name="产品甲",
        field_id="duration_of_response",
        raw_value="9.1 个月",
        normalized_value="9.1",
        disclosure_state="reported_value",
        source_id="src-late",
        locator=EvidenceLocator(
            document_role="测试用后续披露来源", field_path="$.update.text"
        ),
        original_text="后续披露：持续缓解时间为 9.1 个月。",
    )
    late_claim = ResearchClaim(
        claim_id="claim-late",
        claim_text="后续披露来源报告持续缓解时间 9.1 个月。",
        claim_kind="direct_evidence",
        fact_ids=("fact-4",),
    )
    return _Materials(
        sources=(*_base_sources(), late_source),
        facts=(*_base_facts(), late_fact),
        claims=(*_base_claims(), late_claim),
        content_digest=hashlib.sha256(
            f"research-content-e{epoch}-late".encode()
        ).hexdigest(),
    )


def _conflicting_reingest(root: Path, project_id: str) -> ResearchEvidenceLineage:
    """与已接受 fact-1 同一逻辑事实、不同内容的独立冲突摄取（邻居族同型）。"""
    produced = EPOCH_TIMELINES[1]["produced"]
    conflict_source = SourceCapture(
        source_id="src-conflict",
        route_id="route-conflict",
        source_type="registry",
        title="冲突来源",
        url="https://example.org/conflict",
        query_or_identifier="NCT00000004",
        language="en",
        access_method="public_registry",
        media_type="application/json",
        content_text=json.dumps(
            {"result": {"quote": "客观缓解率 75%（30/40）。", "count": "30/40"}},
            ensure_ascii=False,
        ),
        acquired_at=produced,
        published_at=produced,
        effective_at=None,
        first_disclosed_at=produced,
        locator=EvidenceLocator(
            document_role="测试用冲突来源", field_path="$.result.quote"
        ),
    )
    conflict_fact = ResearchFact(
        fact_id="fact-1",
        row_ref="safety:f1",
        entity_id="product-alpha",
        entity_type="product",
        canonical_name="产品甲",
        field_id="orr",
        raw_value="75% (30/40)",
        normalized_value="75.0",
        disclosure_state="reported_value",
        source_id="src-conflict",
        locator=EvidenceLocator(
            document_role="测试用冲突来源", field_path="$.result.quote"
        ),
        original_text="客观缓解率 75%（30/40）。",
    )
    conflict_claim = ResearchClaim(
        claim_id="claim-conflict",
        claim_text="冲突来源报告的客观缓解率为 75%。",
        claim_kind="direct_evidence",
        fact_ids=("fact-1",),
    )
    return ingest_research_evidence(
        project_root=root,
        project_id=project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=DATA_CUTOFF,
        scientific_content_digest=hashlib.sha256(b"conflict-digest").hexdigest(),
        created_at=produced,
        sources=(conflict_source,),
        route_attempts=(),
        facts=(conflict_fact,),
        claims=(conflict_claim,),
    )


# ── 世界构建：真实摄取 + 既有发布/签发入口（测试 runner 模拟） ─────────────────


@dataclass(frozen=True)
class _World:
    root: Path
    project_id: str
    materials: _Materials
    context: ScientificQcCurrentContext
    claim_snapshot_id: str
    lineage: ResearchEvidenceLineage


def _portal_relative(epoch: int) -> tuple[str, str]:
    return (
        f"reports/A/v{epoch + 1}/html.manifest.json",
        f"reports/A/v{epoch + 1}/html",
    )


def _write_portal_bytes(root: Path, epoch: int) -> None:
    manifest_relative, site_relative = _portal_relative(epoch)
    manifest_path = root / manifest_relative
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"kind": "artifact-manifest", "epoch": epoch}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    page = root / site_relative / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        f"<!doctype html><title>门户 epoch {epoch}</title>", encoding="utf-8"
    )


def _ingest(
    root: Path, project_id: str, materials: _Materials, *, epoch: int
) -> ResearchEvidenceLineage:
    return ingest_research_evidence(
        project_root=root,
        project_id=project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=DATA_CUTOFF,
        scientific_content_digest=materials.content_digest,
        created_at=EPOCH_TIMELINES[epoch]["produced"],
        sources=materials.sources,
        route_attempts=(),
        facts=materials.facts,
        claims=materials.claims,
    )


def _build_context(
    project_id: str,
    materials: _Materials,
    lineage: ResearchEvidenceLineage,
    *,
    epoch: int,
) -> tuple[ScientificQcCurrentContext, str]:
    claim_snapshot_id = stable_id(
        "claim-snapshot",
        project_id,
        materials.content_digest,
        *lineage.claim_version_ids,
    )
    coverage_set_id = stable_id(
        "coverage-set",
        project_id,
        "A",
        lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id,
    )
    context = build_scientific_review_context(
        project_id=project_id,
        report_kind="A",
        report_version=f"v{epoch + 1}",
        producer_id="producer-agent",
        candidate_snapshot_id=f"report-snapshot-development-e{epoch}",
        candidate_content_digest=materials.content_digest,
        criteria_version="A-v1",
        gate_result_key=f"gate-key-e{epoch}",
        contract_version="1",
        coverage_set_id=coverage_set_id,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        sources=materials.sources,
        facts=materials.facts,
        claims=materials.claims,
        fact_version_by_ref=lineage.fact_version_by_ref,
    )
    return context, claim_snapshot_id


def _review_bundle(context: ScientificQcCurrentContext) -> ScientificQcReviewBundle:
    return ScientificQcReviewBundle(
        producer_id=context.producer_id,
        project_id=context.project_id,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        criteria_version=context.criteria_version,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
    )


def _verdict_payload(context: ScientificQcCurrentContext, epoch: int) -> dict[str, Any]:
    verdict = ScientificQcVerdict(
        criteria_version=context.criteria_version,
        verdict_id=f"verdict-independent-e{epoch}",
        verdict="accepted",
        project_id=context.project_id,
        contract_version=context.contract_version,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
        reviewer_id="independent-reviewer",
        review_input_digest=_review_bundle(context).input_digest,
        reviewed_at=EPOCH_TIMELINES[epoch]["finished"],
        valid_until=VALID_UNTIL,
    )
    return verdict.model_dump(mode="json")


def _publish(root: Path, context: ScientificQcCurrentContext, *, epoch: int) -> None:
    manifest_relative, site_relative = _portal_relative(epoch)
    _write_portal_bytes(root, epoch)
    publish_production_context(root, "A", context)
    publish_scientific_review_request(
        root,
        "A",
        context,
        producer_session_id=f"producer-run-e{epoch}",
        produced_at=EPOCH_TIMELINES[epoch]["produced"],
        portal_binding=capture_portal_artifact_binding(
            root,
            "A",
            manifest_relative=manifest_relative,
            site_relative=site_relative,
        ),
    )


def _verdict_relative(epoch: int) -> str:
    if epoch == 0:
        return "receipts/scientific_review/A/verdict.json"
    return f"receipts/scientific_review/A/epochs/e{epoch}/verdict.json"


def _issue(root: Path, context: ScientificQcCurrentContext, *, epoch: int) -> Any:
    payload = _verdict_payload(context, epoch)
    verdict_relative = _verdict_relative(epoch)
    timeline = EPOCH_TIMELINES[epoch]

    def _runner(
        argv: tuple[str, ...], cwd: str, timeout: float
    ) -> ExternalProcessResult:
        assert argv == (HOST_PATH, *REVIEW_ARGV)
        assert cwd == str(root)
        assert timeout > 0
        verdict_path = root / verdict_relative
        verdict_path.parent.mkdir(parents=True, exist_ok=True)
        verdict_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return ExternalProcessResult(
            pid=4242 + epoch,
            argv=argv,
            cwd=cwd,
            started_at=timeline["started"],
            finished_at=timeline["finished"],
            returncode=0,
            stdout_tail="SCIENTIFIC_REVIEW_DONE verdict=accepted\n",
            stderr_tail="",
        )

    outcome = issue_review_receipt(
        project_root=root,
        report_kind="A",
        reviewer_id="independent-reviewer",
        review_session_id="review-session-9",
        host="codex",
        host_executable=HOST_EXECUTABLE,
        review_argv=REVIEW_ARGV,
        verdict_relative_path=verdict_relative,
        session=REVIEW_SESSION,
        runner=_runner,
        clock=lambda: timeline["issued"],
    )
    return outcome.receipt


def _promote(
    root: Path, context: ScientificQcCurrentContext, receipt: Any, *, epoch: int
) -> str:
    return promote_rendered_candidate(
        project_root=root,
        current_state=RENDERED_UNREVIEWED,
        context=context,
        receipt=receipt,
        promoted_at=EPOCH_TIMELINES[epoch]["issued"] + timedelta(minutes=30),
    )


def _advance(
    root: Path,
    predecessor: ScientificQcCurrentContext,
    next_context: ScientificQcCurrentContext,
    *,
    epoch: int,
) -> Any:
    manifest_relative, site_relative = _portal_relative(epoch)
    _write_portal_bytes(root, epoch)
    return advance_scientific_review_epoch(
        project_root=root,
        report_kind="A",
        expected_predecessor_context=predecessor,
        next_context=next_context,
        producer_session_id=f"producer-run-e{epoch}",
        produced_at=EPOCH_TIMELINES[epoch]["produced"],
        portal_binding=capture_portal_artifact_binding(
            root,
            "A",
            manifest_relative=manifest_relative,
            site_relative=site_relative,
        ),
        advanced_at=ADVANCED_AT[epoch],
    )


def _build_world(tmp_path: Path, *, name: str = "epoch-project") -> _World:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    root = create_project_workspace(tmp_path / name, contract)
    materials = _base_materials(0)
    lineage = _ingest(root, contract.project_id, materials, epoch=0)
    context, claim_snapshot_id = _build_context(
        contract.project_id, materials, lineage, epoch=0
    )
    _publish(root, context, epoch=0)
    return _World(
        root=root,
        project_id=contract.project_id,
        materials=materials,
        context=context,
        claim_snapshot_id=claim_snapshot_id,
        lineage=lineage,
    )


def _context_for_epoch(
    world: _World, *, epoch: int, materials: _Materials | None = None
) -> tuple[ScientificQcCurrentContext, str, ResearchEvidenceLineage]:
    epoch_materials = materials if materials is not None else _base_materials(epoch)
    lineage = _ingest(world.root, world.project_id, epoch_materials, epoch=epoch)
    context, claim_snapshot_id = _build_context(
        world.project_id, epoch_materials, lineage, epoch=epoch
    )
    return context, claim_snapshot_id, lineage


# ── 状态与字节读取 ─────────────────────────────────────────────────────────────


def _fact_rows(root: Path) -> dict[str, tuple[Any, ...]]:
    with open_database(root / "state/project.sqlite") as database:
        rows = database.execute(
            "SELECT fact_version_id,review_state,content_sha256,scientific_context_json,"
            "raw_value,normalized_value,primary_fragment_id,supersedes_fact_version_id "
            "FROM fact_versions ORDER BY fact_version_id"
        ).fetchall()
    return {str(row[0]): tuple(row[1:]) for row in rows}


def _claim_rows(root: Path) -> dict[str, tuple[Any, ...]]:
    with open_database(root / "state/project.sqlite") as database:
        rows = database.execute(
            "SELECT claim_version_id,review_state,claim_text,claim_kind "
            "FROM claim_versions ORDER BY claim_version_id"
        ).fetchall()
    return {str(row[0]): tuple(row[1:]) for row in rows}


def _fact_version_count(root: Path) -> int:
    with open_database(root / "state/project.sqlite") as database:
        return int(
            database.execute("SELECT COUNT(*) FROM fact_versions").fetchone()[0]
        )


def _file_digest(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def _lifecycle_digests(root: Path, epochs: tuple[int, ...]) -> dict[str, str]:
    """历史纪元全部生命周期材料的逐字节摘要（上下文/请求/签发/回执/结论）。"""
    relatives = [
        "state/scientific_review/A/production_context.json",
        "state/scientific_review/A/review_request.json",
        "state/scientific_review/A/issuance.json",
        "receipts/scientific_review/A/receipt.json",
        "receipts/scientific_review/A/verdict.json",
    ]
    for epoch in epochs:
        if epoch == 0:
            continue
        scope = f"state/scientific_review/A/epochs/e{epoch}"
        relatives += [
            f"{scope}/production_context.json",
            f"{scope}/review_request.json",
            f"{scope}/issuance.json",
            epoch_receipt_path("A", epoch).as_posix(),
            _verdict_relative(epoch),
        ]
    return {relative: _file_digest(root, relative) for relative in relatives}


def _accept(
    world: _World,
    *,
    evidence_snapshot_id: str,
    claim_snapshot_id: str,
    epoch: int,
) -> Any:
    return accept_reviewed_source_facts(
        project_root=world.root,
        report_kind="A",
        evidence_snapshot_id=evidence_snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        checked_at=ACCEPTED_AT[epoch],
    )


# ── 1. 两个连续 epoch：旧材料逐字节不可变，活跃 epoch 权威 ─────────────────────


def test_two_sequential_epochs_preserve_all_prior_materials(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    receipt0 = _issue(world.root, world.context, epoch=0)
    assert (
        _promote(world.root, world.context, receipt0, epoch=0)
        == SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE
    )

    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    advance1 = _advance(world.root, world.context, context1, epoch=1)
    assert advance1.activated_epoch == 1
    assert advance1.active_context_digest == context1.context_digest
    assert advance1.predecessor_context_digest == world.context.context_digest
    assert advance1.advanced_at == ADVANCED_AT[1]
    assert reload_production_context(world.root, "A") == context1
    pointer = read_epoch_pointer(world.root, "A")
    assert pointer is not None
    assert pointer.active_epoch == 1
    assert pointer.epochs[0].predecessor_context_digest == world.context.context_digest

    receipt1 = _issue(world.root, context1, epoch=1)
    assert (
        _promote(world.root, context1, receipt1, epoch=1)
        == SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE
    )

    before_epoch2 = _lifecycle_digests(world.root, epochs=(0, 1))
    context2, _claim_snapshot_2, _lineage2 = _context_for_epoch(world, epoch=2)
    advance2 = _advance(world.root, context1, context2, epoch=2)
    assert advance2.activated_epoch == 2
    assert reload_production_context(world.root, "A") == context2

    assert _lifecycle_digests(world.root, epochs=(0, 1)) == before_epoch2, (
        "历史 epoch 材料必须逐字节不可变"
    )

    receipt2 = _issue(world.root, context2, epoch=2)
    assert (
        _promote(world.root, context2, receipt2, epoch=2)
        == SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE
    )

    final_pointer = read_epoch_pointer(world.root, "A")
    assert final_pointer is not None
    assert final_pointer.active_epoch == 2
    assert [entry.epoch for entry in final_pointer.epochs] == [1, 2]
    assert final_pointer.epochs[1].predecessor_context_digest == context1.context_digest
    # 三份回执在不同作用域，逐字节互不相同
    receipt_digests = {
        _file_digest(world.root, scientific_review_receipt_path("A").as_posix()),
        _file_digest(world.root, epoch_receipt_path("A", 1).as_posix()),
        _file_digest(world.root, epoch_receipt_path("A", 2).as_posix()),
    }
    assert len(receipt_digests) == 3


def test_active_epoch_scope_is_authoritative_for_issuance_and_receipt_verify(
    tmp_path: Path,
) -> None:
    world = _build_world(tmp_path)
    _issue(world.root, world.context, epoch=0)
    legacy_receipt_digest = _file_digest(
        world.root, scientific_review_receipt_path("A").as_posix()
    )
    legacy_issuance_digest = _file_digest(
        world.root, review_issuance_record_path("A").as_posix()
    )
    scope0 = active_scientific_review_scope(world.root, "A")
    assert scope0.epoch == 0
    assert scope0.receipt_relative == scientific_review_receipt_path("A").as_posix()

    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    _advance(world.root, world.context, context1, epoch=1)
    scope1 = active_scientific_review_scope(world.root, "A")
    assert scope1.epoch == 1
    assert scope1.receipt_relative == epoch_receipt_path("A", 1).as_posix()

    receipt1 = _issue(world.root, context1, epoch=1)
    # epoch 1 签发写入版本化作用域；epoch 0 回执与签发记录逐字节不变
    assert (
        _file_digest(world.root, scientific_review_receipt_path("A").as_posix())
        == legacy_receipt_digest
    )
    assert (
        _file_digest(world.root, review_issuance_record_path("A").as_posix())
        == legacy_issuance_digest
    )
    verified = verify_receipt_issuance(world.root, "A", checked_at=ACCEPTED_AT[1])
    assert verified.receipt_digest == receipt1.receipt_digest


# ── 2. 既有单例布局的隐式拒绝语义原样保留 ─────────────────────────────────────


def test_legacy_publish_collisions_still_fail_closed(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)

    # epoch 0（无指针）：不同候选与外项目上下文都不得隐式覆盖既有材料
    with pytest.raises(ScientificReviewTransitionError, match="候选"):
        publish_production_context(world.root, "A", context1)
    foreign = context1.model_copy(update={"project_id": "project-other"})
    with pytest.raises(ScientificReviewTransitionError, match="候选|项目"):
        publish_production_context(world.root, "A", foreign)

    # 推进到 epoch 1 之后：隐式发布者既不得复活旧前驱，也不得写入其他候选
    _advance(world.root, world.context, context1, epoch=1)
    with pytest.raises(ScientificReviewTransitionError, match="候选"):
        publish_production_context(world.root, "A", world.context)
    drifted = context1.model_copy(update={"report_version": "vX"})
    with pytest.raises(ScientificReviewTransitionError, match="候选"):
        publish_scientific_review_request(
            world.root,
            "A",
            drifted,
            producer_session_id="producer-run-x",
            produced_at=EPOCH_TIMELINES[1]["produced"],
            portal_binding=capture_portal_artifact_binding(
                world.root,
                "A",
                manifest_relative=_portal_relative(1)[0],
                site_relative=_portal_relative(1)[1],
            ),
        )


# ── 3. 旧回执不能授权新纪元；复制到新作用域同样失败关闭 ────────────────────────


def test_old_receipt_cannot_authorize_new_active_epoch(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    receipt0 = _issue(world.root, world.context, epoch=0)
    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    _advance(world.root, world.context, context1, epoch=1)

    # 旧回执 + 旧上下文在活跃 epoch 1 下不得晋级：请求作用域已属于新纪元
    with pytest.raises(ScientificReviewTransitionError):
        promote_rendered_candidate(
            project_root=world.root,
            current_state=RENDERED_UNREVIEWED,
            context=world.context,
            receipt=receipt0,
        )

    # 把旧回执字节复制进新作用域同样失败关闭（绑定/签发记录不一致）
    legacy_receipt_bytes = (world.root / scientific_review_receipt_path("A")).read_bytes()
    replay_path = world.root / epoch_receipt_path("A", 1)
    replay_path.parent.mkdir(parents=True, exist_ok=True)
    replay_path.write_bytes(legacy_receipt_bytes)
    replayed = transition.load_scientific_review_receipt(world.root, "A")
    with pytest.raises((ScientificReviewTransitionError, ValueError)):
        promote_rendered_candidate(
            project_root=world.root,
            current_state=RENDERED_UNREVIEWED,
            context=context1,
            receipt=replayed,
        )
    assert reload_production_context(world.root, "A") == context1


# ── 4. epoch 推进的拒绝分支：陈旧前驱/同上下文/回退/跨项目 ─────────────────────


def test_epoch_advance_rejects_stale_duplicate_revert_and_cross_project(
    tmp_path: Path,
) -> None:
    world = _build_world(tmp_path)
    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    _advance(world.root, world.context, context1, epoch=1)
    context2, _claim_snapshot_2, _lineage2 = _context_for_epoch(world, epoch=2)

    # 陈旧前驱：epoch 1 已活跃，epoch 0 上下文不再是可接受前驱
    with pytest.raises(ScientificReviewTransitionError, match="前驱"):
        _advance(world.root, world.context, context2, epoch=2)

    # 同上下文重复推进：不是真实新科学复核对象
    with pytest.raises(ScientificReviewTransitionError, match="上下文"):
        _advance(world.root, context1, context1, epoch=2)

    # 回退到历史 epoch 上下文摘要同样拒绝
    with pytest.raises(ScientificReviewTransitionError, match="上下文"):
        _advance(world.root, context1, world.context, epoch=2)

    # 跨项目新上下文拒绝
    foreign_next = context2.model_copy(update={"project_id": "project-other"})
    with pytest.raises(ScientificReviewTransitionError, match="项目"):
        _advance(world.root, context1, foreign_next, epoch=2)

    assert reload_production_context(world.root, "A") == context1
    pointer = read_epoch_pointer(world.root, "A")
    assert pointer is not None
    assert pointer.active_epoch == 1


def test_exact_epoch_retry_is_idempotent(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    first = _advance(world.root, world.context, context1, epoch=1)

    second = _advance(world.root, world.context, context1, epoch=1)

    assert second == first
    assert second.advanced_at == ADVANCED_AT[1]
    pointer = read_epoch_pointer(world.root, "A")
    assert pointer is not None
    assert pointer.active_epoch == 1
    assert len(pointer.epochs) == 1
    assert reload_production_context(world.root, "A") == context1


# ── 5. 门户字节漂移与激活故障：旧活跃作用域原样保留 ────────────────────────────


def test_epoch_advance_rejects_portal_byte_drift(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    manifest_relative, site_relative = _portal_relative(1)
    _write_portal_bytes(world.root, epoch=1)
    binding = capture_portal_artifact_binding(
        world.root,
        "A",
        manifest_relative=manifest_relative,
        site_relative=site_relative,
    )
    page = world.root / site_relative / "index.html"
    page.write_text("<!doctype html><title>推进前被篡改</title>", encoding="utf-8")

    with pytest.raises(ScientificReviewTransitionError, match="门户"):
        advance_scientific_review_epoch(
            project_root=world.root,
            report_kind="A",
            expected_predecessor_context=world.context,
            next_context=context1,
            producer_session_id="producer-run-e1",
            produced_at=EPOCH_TIMELINES[1]["produced"],
            portal_binding=binding,
            advanced_at=ADVANCED_AT[1],
        )
    assert reload_production_context(world.root, "A") == world.context
    assert read_epoch_pointer(world.root, "A") is None


def test_activation_fault_preserves_old_active_and_retry_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = _build_world(tmp_path)
    _issue(world.root, world.context, epoch=0)
    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    legacy_digests = _lifecycle_digests(world.root, epochs=())

    def _failing_activation(root: Path, kind: str, pointer: Any) -> Any:
        raise OSError("injected pointer activation failure")

    monkeypatch.setattr(transition, "_activate_epoch_pointer", _failing_activation)
    with pytest.raises(OSError, match="injected pointer activation failure"):
        _advance(world.root, world.context, context1, epoch=1)
    monkeypatch.undo()

    # staged 失败：指针未激活，旧活跃上下文与全部旧材料原样保留
    assert read_epoch_pointer(world.root, "A") is None
    assert reload_production_context(world.root, "A") == world.context
    assert _lifecycle_digests(world.root, epochs=()) == legacy_digests

    result = _advance(world.root, world.context, context1, epoch=1)
    assert result.activated_epoch == 1
    assert reload_production_context(world.root, "A") == context1
    retry = _advance(world.root, world.context, context1, epoch=1)
    assert retry == result


def test_epoch_pointer_tamper_fails_closed(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    context1, _claim_snapshot_1, _lineage1 = _context_for_epoch(world, epoch=1)
    _advance(world.root, world.context, context1, epoch=1)
    pointer_path = world.root / epoch_pointer_path("A")
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    payload["active_epoch"] = 2
    pointer_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ScientificReviewTransitionError, match="epoch 指针"):
        reload_production_context(world.root, "A")
    with pytest.raises(ScientificReviewTransitionError, match="epoch 指针"):
        active_scientific_review_scope(world.root, "A")


# ── 6. epoch 推进公开面：全部关键字参数、完整上下文绑定、无调用方布尔 ──────────


def test_epoch_advance_public_surface_binds_full_contexts() -> None:
    parameters = inspect.signature(advance_scientific_review_epoch).parameters
    assert set(parameters) == {
        "project_root",
        "report_kind",
        "expected_predecessor_context",
        "next_context",
        "producer_session_id",
        "produced_at",
        "portal_binding",
        "advanced_at",
        "gate_result",
    }
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in parameters.values()
    )


# ── 7. 新纪元复用既有已接受精确原子：字节与状态保留，无新版本行 ────────────────


def test_new_epoch_reuses_exact_previously_accepted_atoms(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    _issue(world.root, world.context, epoch=0)
    result0 = _accept(
        world,
        evidence_snapshot_id=world.lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        epoch=0,
    )
    facts_before = _fact_rows(world.root)
    claims_before = _claim_rows(world.root)
    versions_before = _fact_version_count(world.root)

    # 同一原子集合、真实新科学上下文（新快照/新门槛键/新报告版本）
    context1, claim_snapshot_1, lineage1 = _context_for_epoch(world, epoch=1)
    assert context1.source_refs == world.context.source_refs
    _advance(world.root, world.context, context1, epoch=1)
    receipt1 = _issue(world.root, context1, epoch=1)

    result1 = _accept(
        world,
        evidence_snapshot_id=lineage1.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_1,
        epoch=1,
    )

    assert set(result1.accepted_fact_version_ids) == set(
        result0.accepted_fact_version_ids
    )
    assert set(result1.accepted_claim_version_ids) == set(
        result0.accepted_claim_version_ids
    )
    assert result1.receipt_digest == receipt1.receipt_digest
    # 全部事实/声明行逐字节不变（含已接受状态），不产生新版本行
    assert _fact_rows(world.root) == facts_before
    assert _claim_rows(world.root) == claims_before
    assert _fact_version_count(world.root) == versions_before
    # 新决策按新回执摘要落盘；旧决策记录保持原样
    assert (
        world.root
        / source_fact_acceptance_decision_path("A", receipt1.receipt_digest)
    ).is_file()
    old_decision = (
        world.root
        / source_fact_acceptance_decision_path("A", result0.receipt_digest)
    )
    assert old_decision.is_file()


# ── 8. 混合“已接受 + 候选”精确集合：只接受真实覆盖的候选原子 ───────────────────


def test_mixed_accepted_and_candidate_scope_accepts_genuinely_covered(
    tmp_path: Path,
) -> None:
    world = _build_world(tmp_path)
    _issue(world.root, world.context, epoch=0)
    result0 = _accept(
        world,
        evidence_snapshot_id=world.lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        epoch=0,
    )
    facts_before = _fact_rows(world.root)

    context1, claim_snapshot_1, lineage1 = _context_for_epoch(
        world, epoch=1, materials=_late_materials(1)
    )
    _advance(world.root, world.context, context1, epoch=1)
    _issue(world.root, context1, epoch=1)

    result1 = _accept(
        world,
        evidence_snapshot_id=lineage1.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_1,
        epoch=1,
    )

    new_facts = set(lineage1.fact_version_ids) - set(world.lineage.fact_version_ids)
    new_claims = set(result1.accepted_claim_version_ids) - set(
        result0.accepted_claim_version_ids
    )
    assert len(result1.accepted_fact_version_ids) == len(
        result0.accepted_fact_version_ids
    ) + 1
    assert set(result1.accepted_fact_version_ids) - set(
        result0.accepted_fact_version_ids
    ) == new_facts
    assert result1.boundary_claim_version_ids == ()
    assert len(new_claims) == 1
    facts_after = _fact_rows(world.root)
    for version_id, row in facts_before.items():
        assert facts_after[version_id] == row, "既有原子字节与状态必须逐字节保留"
    for version_id in new_facts:
        assert facts_after[version_id][0] == "accepted"
    (late_claim_version,) = tuple(new_claims)
    assert _claim_rows(world.root)[late_claim_version] == (
        "accepted",
        "后续披露来源报告持续缓解时间 9.1 个月。",
        "direct_evidence",
    )


# ── 9. 复用不晋升用户修订；与已接受兄弟冲突的新内容保持阻塞 ────────────────────


def test_epoch_reuse_keeps_user_edits_unpromoted(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    _issue(world.root, world.context, epoch=0)
    result0 = _accept(
        world,
        evidence_snapshot_id=world.lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        epoch=0,
    )
    bound_version = sorted(result0.accepted_fact_version_ids)[0]
    with open_database(world.root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT fact_id,entity_id,field_id,disclosure_state,primary_fragment_id,"
            "content_sha256,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?",
            (bound_version,),
        ).fetchone()
        assert row is not None
        user_version = stable_id(
            "fact-version", "test-user-modification", bound_version
        )
        database.execute(
            "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,"
            "raw_value,normalized_value,disclosure_state,review_state,"
            "primary_fragment_id,supersedes_fact_version_id,created_at,content_sha256,"
            "scientific_context_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                user_version,
                str(row[0]),
                str(row[1]),
                str(row[2]),
                "30% (24/80)",
                "30.0",
                str(row[3]),
                "user_modified",
                str(row[4]),
                bound_version,
                ACCEPTED_AT[0].isoformat(),
                str(row[5]),
                str(row[6]),
            ),
        )
    facts_before = _fact_rows(world.root)

    context1, claim_snapshot_1, lineage1 = _context_for_epoch(world, epoch=1)
    _advance(world.root, world.context, context1, epoch=1)
    _issue(world.root, context1, epoch=1)
    result1 = _accept(
        world,
        evidence_snapshot_id=lineage1.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_1,
        epoch=1,
    )

    assert set(result1.accepted_fact_version_ids) == set(
        result0.accepted_fact_version_ids
    )
    assert _fact_rows(world.root) == facts_before
    assert _fact_rows(world.root)[user_version][0] == "user_modified"


def test_new_content_conflicting_with_accepted_sibling_stays_blocked(
    tmp_path: Path,
) -> None:
    world = _build_world(tmp_path)
    _issue(world.root, world.context, epoch=0)
    _accept(
        world,
        evidence_snapshot_id=world.lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        epoch=0,
    )
    facts_before = _fact_rows(world.root)

    context1, claim_snapshot_1, lineage1 = _context_for_epoch(world, epoch=1)
    _advance(world.root, world.context, context1, epoch=1)
    _issue(world.root, context1, epoch=1)
    # 新纪元签发后到达的冲突摄取：同一逻辑事实出现不同内容的新候选版本
    _conflicting_reingest(world.root, world.project_id)
    facts_before = _fact_rows(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="已接受|冲突"):
        _accept(
            world,
            evidence_snapshot_id=lineage1.evidence_snapshot.snapshot_id,
            claim_snapshot_id=claim_snapshot_1,
            epoch=1,
        )
    assert _fact_rows(world.root) == facts_before
    with open_database(world.root / "state/project.sqlite") as database:
        open_conflicts = int(
            database.execute(
                "SELECT COUNT(*) FROM conflict_sets WHERE resolution_state='open'"
            ).fetchone()[0]
        )
    assert open_conflicts >= 1


# ── 10. 已被显式拒绝的原子不得在新纪元被重新接受 ───────────────────────────────


def test_rejected_bound_row_rejects_new_epoch_acceptance(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    _issue(world.root, world.context, epoch=0)
    _accept(
        world,
        evidence_snapshot_id=world.lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        epoch=0,
    )
    facts_after_epoch0 = _fact_rows(world.root)
    accepted_version = sorted(facts_after_epoch0)[0]
    # 既有守卫触发器拒绝任何状态改写；本用例模拟的是接受层之外的显式裁决
    # （守卫逐字重建，与迁移 0012 定义一致），已接受原子被改为 rejected 后，
    # 新纪元接受必须失败关闭且不回滚该裁决。
    with open_database(world.root / "state/project.sqlite") as database:
        database.execute("DROP TRIGGER fact_versions_no_update")
        database.execute(
            "UPDATE fact_versions SET review_state='rejected' WHERE fact_version_id=?",
            (accepted_version,),
        )
        database.execute(
            "CREATE TRIGGER fact_versions_no_update BEFORE UPDATE ON fact_versions "
            "BEGIN SELECT RAISE(ABORT, 'append-only: fact_versions'); END"
        )
    facts_before = _fact_rows(world.root)

    context1, claim_snapshot_1, lineage1 = _context_for_epoch(world, epoch=1)
    _advance(world.root, world.context, context1, epoch=1)
    _issue(world.root, context1, epoch=1)

    with pytest.raises(SourceFactAcceptanceError, match="rejected|修订|拒绝"):
        _accept(
            world,
            evidence_snapshot_id=lineage1.evidence_snapshot.snapshot_id,
            claim_snapshot_id=claim_snapshot_1,
            epoch=1,
        )
    assert _fact_rows(world.root) == facts_before
