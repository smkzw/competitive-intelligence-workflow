"""Reviewed source fact acceptance regression family (ci-r24-114).

The family builds genuine fresh-ingested candidate projects (real SQLite,
content-addressed source bytes, immutable evidence snapshots), publishes the
existing authoritative scientific review context without a portal report, and
exercises the missing receipt-backed materialization seam:

- a valid independently issued ``scientific-review-v1`` receipt accepts exactly
  the receipt-bound fact set (and only fully covered claims) while unrelated
  candidates and immutable scientific bytes stay untouched;
- absent, unissued, expired, substituted or drifted material fails closed with
  no decision artifact, no event and no state change;
- same-receipt replay is idempotent and repairs a lost acceptance event.

The file intentionally imports ``ci_workflow.application.source_fact_acceptance``
before it exists so the first run is RED at collection time.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.application import source_fact_acceptance as acceptance_service
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
)
from ci_workflow.application.scientific_review_transition import (
    build_scientific_review_context,
    capture_portal_artifact_binding,
    production_context_publication_path,
    publish_production_context,
    publish_scientific_review_request,
    scientific_review_receipt_path,
)
from ci_workflow.application.source_fact_acceptance import (
    SourceFactAcceptanceError,
    accept_reviewed_source_facts,
    source_fact_acceptance_decision_path,
)
from ci_workflow.cli import main
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.hosts.receipt import (
    HostExecutableEvidence as ReviewExecutableEvidence,
)
from ci_workflow.hosts.receipt import (
    HostProcessBinding as ReviewProcessEvidence,
)
from ci_workflow.hosts.receipt import (
    HostSessionBinding as ReviewHostSession,
)
from ci_workflow.qc.review_receipt import (
    ReviewArtifactBinding,
    ReviewContentBinding,
    ReviewContextEvidence,
    ReviewProductionContext,
    ScientificReviewReceipt,
    build_scientific_review_receipt,
)
from ci_workflow.qc.scientific import (
    ScientificQcCurrentContext,
    ScientificQcReviewBundle,
    ScientificQcVerdict,
)
from ci_workflow.storage.event_store import EventStore
from ci_workflow.storage.snapshot_store import compute_locked_snapshot
from ci_workflow.storage.sqlite import open_database

PRODUCED_AT = datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
REVIEW_STARTED_AT = datetime(2026, 9, 5, 2, 0, tzinfo=UTC)
REVIEW_FINISHED_AT = datetime(2026, 9, 5, 2, 30, tzinfo=UTC)
ISSUED_AT = datetime(2026, 9, 5, 3, 0, tzinfo=UTC)
CHECKED_AT = datetime(2026, 9, 5, 4, 0, tzinfo=UTC)
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
VERDICT_RELATIVE = "receipts/scientific_review/A/verdict.json"
PORTAL_MANIFEST = "reports/A/v1/html.manifest.json"
PORTAL_SITE = "reports/A/v1/html"


def _primary_source() -> SourceCapture:
    return SourceCapture(
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
        acquired_at=PRODUCED_AT,
        published_at=PRODUCED_AT,
        effective_at=None,
        first_disclosed_at=PRODUCED_AT,
        locator=EvidenceLocator(document_role="测试用主要登记来源", field_path="$.result.quote"),
    )


def _supporting_source() -> SourceCapture:
    return SourceCapture(
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
        acquired_at=PRODUCED_AT,
        published_at=PRODUCED_AT,
        effective_at=None,
        first_disclosed_at=PRODUCED_AT,
        locator=EvidenceLocator(document_role="测试用辅助来源", field_path="$.finding.text"),
    )


def _sources() -> tuple[SourceCapture, ...]:
    return (_primary_source(), _supporting_source())


def _primary_result_locator() -> EvidenceLocator:
    return EvidenceLocator(document_role="测试用主要登记来源", field_path="$.result.quote")


def _facts() -> tuple[ResearchFact, ...]:
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
            locator=_primary_result_locator(),
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
            locator=EvidenceLocator(document_role="测试用辅助来源", field_path="$.finding.text"),
            original_text="安全性事件例数为 12 例。",
        ),
    )


def _claims() -> tuple[ResearchClaim, ...]:
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


# ── 无关候选与同逻辑事实冲突摄取（真实摄取路径，非手写接受 SQL） ──────────────


def _ingest_unrelated(root: Path, project_id: str) -> ResearchEvidenceLineage:
    source = SourceCapture(
        source_id="src-unrelated",
        route_id="route-unrelated",
        source_type="registry",
        title="无关来源",
        url="https://example.org/unrelated",
        query_or_identifier="NCT00000009",
        language="en",
        access_method="public_registry",
        media_type="application/json",
        content_text=json.dumps({"unrelated": {"text": "无关候选事实。"}}, ensure_ascii=False),
        acquired_at=PRODUCED_AT,
        published_at=PRODUCED_AT,
        effective_at=None,
        first_disclosed_at=PRODUCED_AT,
        locator=EvidenceLocator(document_role="测试用无关来源", field_path="$.unrelated.text"),
    )
    fact = ResearchFact(
        fact_id="fact-unrelated",
        row_ref="safety:unrelated",
        entity_id="product-beta",
        entity_type="product",
        canonical_name="产品乙",
        field_id="status",
        raw_value="无关候选事实。",
        normalized_value=None,
        disclosure_state="reported_value",
        source_id="src-unrelated",
        locator=EvidenceLocator(document_role="测试用无关来源", field_path="$.unrelated.text"),
        original_text="无关候选事实。",
    )
    claim = ResearchClaim(
        claim_id="claim-unrelated",
        claim_text="无关候选事实记录。",
        claim_kind="direct_evidence",
        fact_ids=("fact-unrelated",),
    )
    return ingest_research_evidence(
        project_root=root,
        project_id=project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=DATA_CUTOFF,
        scientific_content_digest=hashlib.sha256(b"unrelated-digest").hexdigest(),
        created_at=PRODUCED_AT,
        sources=(source,),
        route_attempts=(),
        facts=(fact,),
        claims=(claim,),
    )


def _ingest_conflicting_reingest(root: Path, project_id: str) -> ResearchEvidenceLineage:
    source = SourceCapture(
        source_id="src-conflict",
        route_id="route-conflict",
        source_type="registry",
        title="冲突来源",
        url="https://example.org/conflict",
        query_or_identifier="NCT00000010",
        language="en",
        access_method="public_registry",
        media_type="application/json",
        content_text=json.dumps(
            {"result": {"quote": "客观缓解率 75%（30/40）。", "count": "30/40"}},
            ensure_ascii=False,
        ),
        acquired_at=PRODUCED_AT,
        published_at=PRODUCED_AT,
        effective_at=None,
        first_disclosed_at=PRODUCED_AT,
        locator=EvidenceLocator(document_role="测试用冲突来源", field_path="$.result.quote"),
    )
    fact = ResearchFact(
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
        locator=EvidenceLocator(document_role="测试用冲突来源", field_path="$.result.quote"),
        original_text="客观缓解率 75%（30/40）。",
    )
    claim = ResearchClaim(
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
        created_at=PRODUCED_AT,
        sources=(source,),
        route_attempts=(),
        facts=(fact,),
        claims=(claim,),
    )


# ── 项目世界：真实摄取 + 既有上下文物化 + 真实签发入口（测试 runner seam） ────


@dataclass(frozen=True)
class _World:
    root: Path
    project_id: str
    content_digest: str
    lineage: ResearchEvidenceLineage
    context: ScientificQcCurrentContext
    claim_snapshot_id: str
    receipt: ScientificReviewReceipt


def _build_context(
    project_id: str, content_digest: str, lineage: ResearchEvidenceLineage
) -> tuple[ScientificQcCurrentContext, str]:
    claim_snapshot_id = stable_id(
        "claim-snapshot", project_id, content_digest, *lineage.claim_version_ids
    )
    coverage_set_id = stable_id(
        "coverage-set", project_id, "A", lineage.evidence_snapshot.snapshot_id, claim_snapshot_id
    )
    context = build_scientific_review_context(
        project_id=project_id,
        report_kind="A",
        report_version="v1",
        producer_id="producer-agent",
        candidate_snapshot_id="report-snapshot-development",
        candidate_content_digest=content_digest,
        criteria_version="A-v1",
        gate_result_key="gate-key-1",
        contract_version="1",
        coverage_set_id=coverage_set_id,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        sources=_sources(),
        facts=_facts(),
        claims=_claims(),
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


def _verdict_payload(context: ScientificQcCurrentContext) -> dict[str, Any]:
    verdict = ScientificQcVerdict(
        criteria_version=context.criteria_version,
        verdict_id="verdict-independent-1",
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
        reviewed_at=REVIEW_FINISHED_AT,
        valid_until=VALID_UNTIL,
    )
    return verdict.model_dump(mode="json")


def _publish(root: Path, context: ScientificQcCurrentContext) -> None:
    manifest_path = root / PORTAL_MANIFEST
    site_path = root / PORTAL_SITE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    site_path.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text('{"kind":"artifact-manifest"}\n', encoding="utf-8")
    (site_path / "index.html").write_text("<!doctype html><title>A</title>", encoding="utf-8")
    publish_production_context(root, "A", context)
    publish_scientific_review_request(
        root,
        "A",
        context,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=capture_portal_artifact_binding(
            root,
            "A",
            manifest_relative=PORTAL_MANIFEST,
            site_relative=PORTAL_SITE,
        ),
    )


def _issue_receipt(root: Path, context: ScientificQcCurrentContext) -> ScientificReviewReceipt:
    payload = _verdict_payload(context)

    def _runner(
        argv: tuple[str, ...], cwd: str, timeout: float
    ) -> ExternalProcessResult:
        assert argv == (HOST_PATH, *REVIEW_ARGV)
        assert cwd == str(root)
        assert timeout > 0
        verdict_path = root / VERDICT_RELATIVE
        verdict_path.parent.mkdir(parents=True, exist_ok=True)
        verdict_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return ExternalProcessResult(
            pid=4242,
            argv=argv,
            cwd=cwd,
            started_at=REVIEW_STARTED_AT,
            finished_at=REVIEW_FINISHED_AT,
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
        verdict_relative_path=VERDICT_RELATIVE,
        session=REVIEW_SESSION,
        runner=_runner,
        clock=lambda: ISSUED_AT,
    )
    return outcome.receipt


def _build_world(tmp_path: Path, *, name: str = "project") -> _World:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    root = create_project_workspace(tmp_path / name, contract)
    content_digest = hashlib.sha256(f"research-content-{name}".encode()).hexdigest()
    lineage = ingest_research_evidence(
        project_root=root,
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        report_kind="A",
        data_cutoff=DATA_CUTOFF,
        scientific_content_digest=content_digest,
        created_at=PRODUCED_AT,
        sources=_sources(),
        route_attempts=(),
        facts=_facts(),
        claims=_claims(),
    )
    context, claim_snapshot_id = _build_context(contract.project_id, content_digest, lineage)
    _publish(root, context)
    receipt = _issue_receipt(root, context)
    return _World(
        root=root,
        project_id=contract.project_id,
        content_digest=content_digest,
        lineage=lineage,
        context=context,
        claim_snapshot_id=claim_snapshot_id,
        receipt=receipt,
    )


def _accept(
    world: _World,
    *,
    evidence_snapshot_id: str | None = None,
    claim_snapshot_id: str | None = None,
    checked_at: datetime | None = None,
) -> Any:
    return accept_reviewed_source_facts(
        project_root=world.root,
        report_kind="A",
        evidence_snapshot_id=evidence_snapshot_id
        or world.lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_id or world.claim_snapshot_id,
        checked_at=checked_at or CHECKED_AT,
    )


# ── 事实/声明状态与不可变字节读取 ─────────────────────────────────────────────


def _fact_states(root: Path) -> dict[str, tuple[Any, ...]]:
    with open_database(root / "state/project.sqlite") as database:
        rows = database.execute(
            "SELECT fact_version_id,review_state,content_sha256,scientific_context_json,"
            "raw_value,normalized_value,primary_fragment_id,supersedes_fact_version_id "
            "FROM fact_versions ORDER BY fact_version_id"
        ).fetchall()
    return {str(row[0]): tuple(row[1:]) for row in rows}


def _claim_states(root: Path) -> dict[str, str]:
    with open_database(root / "state/project.sqlite") as database:
        rows = database.execute(
            "SELECT claim_version_id,review_state FROM claim_versions ORDER BY claim_version_id"
        ).fetchall()
    return {str(row[0]): str(row[1]) for row in rows}


def _fact_version_count(root: Path) -> int:
    with open_database(root / "state/project.sqlite") as database:
        return int(database.execute("SELECT COUNT(*) FROM fact_versions").fetchone()[0])


def _file_digests(root: Path, relative: str) -> dict[str, str]:
    base = root / relative
    if not base.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _acceptance_events(root: Path, receipt_digest: str) -> list[Any]:
    key = f"source.fact.acceptance:{receipt_digest}"
    return [
        event for event in EventStore(root).read_all() if event.idempotency_key == key
    ]


def _bound_fact_version_ids(world: _World) -> tuple[str, ...]:
    return tuple(
        sorted({item for ref in world.context.source_refs for item in ref.fact_version_ids})
    )


def _expected_claim_version_ids(world: _World) -> tuple[str, ...]:
    return tuple(sorted(world.lineage.claim_version_ids))


# ── 1. 有效真实签发接受精确绑定集合 ──────────────────────────────────────────


def test_valid_issuer_accepts_exact_bound_set_and_leaves_unrelated_candidate(
    tmp_path: Path,
) -> None:
    world = _build_world(tmp_path)
    unrelated = _ingest_unrelated(world.root, world.project_id)
    unrelated_version = unrelated.fact_version_ids[0]
    unrelated_claims = {version_id: "candidate" for version_id in unrelated.claim_version_ids}

    facts_before = _fact_states(world.root)
    claims_before = _claim_states(world.root)
    snapshots_before = _file_digests(world.root, "snapshots")
    context_before = (world.root / production_context_publication_path("A")).read_bytes()
    receipt_before = (world.root / scientific_review_receipt_path("A")).read_bytes()
    request_before = (
        world.root / "state/scientific_review/A/review_request.json"
    ).read_bytes()

    result = _accept(world)

    expected_facts = _bound_fact_version_ids(world)
    assert result.accepted_fact_version_ids == expected_facts
    assert result.evidence_snapshot_id == world.lineage.evidence_snapshot.snapshot_id
    assert result.claim_snapshot_id == world.claim_snapshot_id
    assert result.receipt_digest == world.receipt.receipt_digest
    assert result.reviewer_id == "independent-reviewer"
    assert result.verdict_id == "verdict-independent-1"
    assert result.boundary_claim_version_ids == ()
    assert set(result.accepted_claim_version_ids) == set(_expected_claim_version_ids(world))

    facts_after = _fact_states(world.root)
    for version_id in expected_facts:
        assert facts_after[version_id][0] == "accepted"
        # 科学载荷、内容摘要与来源绑定逐字节不变（review_state 正交）
        assert facts_after[version_id][1:] == facts_before[version_id][1:]
    # 无关候选事实保持 candidate 且不可变
    assert facts_after[unrelated_version][0] == "candidate"
    assert facts_after[unrelated_version][1:] == facts_before[unrelated_version][1:]

    claims_after = _claim_states(world.root)
    for version_id in result.accepted_claim_version_ids:
        assert claims_before[version_id] == "candidate"
        assert claims_after[version_id] == "accepted"
    for version_id in unrelated_claims:
        assert claims_after[version_id] == "candidate"

    decision_path = world.root / source_fact_acceptance_decision_path(
        "A", world.receipt.receipt_digest
    )
    assert decision_path.is_file()
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["record_kind"] == "source-fact-acceptance-decision-v1"
    assert decision["receipt_digest"] == world.receipt.receipt_digest
    assert tuple(decision["accepted_fact_version_ids"]) == expected_facts
    assert result.decision_digest == hashlib.sha256(decision_path.read_bytes()).hexdigest()

    events = _acceptance_events(world.root, world.receipt.receipt_digest)
    assert len(events) == 1
    assert events[0].payload["result"]["receipt_digest"] == world.receipt.receipt_digest
    assert tuple(events[0].payload["result"]["accepted_fact_version_ids"]) == expected_facts

    # 不产生当前交付或报告写入；既有权威物化与快照逐字节不变
    assert not (world.root / "reports/current.json").exists()
    assert (world.root / production_context_publication_path("A")).read_bytes() == context_before
    assert (world.root / scientific_review_receipt_path("A")).read_bytes() == receipt_before
    assert (
        world.root / "state/scientific_review/A/review_request.json"
    ).read_bytes() == request_before
    assert _file_digests(world.root, "snapshots") == snapshots_before

    # 只追加守卫在物化事务后原样恢复：科学真源仍然拒绝任何状态改写
    with open_database(world.root / "state/project.sqlite") as database:
        for trigger in ("fact_versions_no_update", "claim_versions_no_update"):
            assert (
                database.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
                    (trigger,),
                ).fetchone()
                is not None
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "UPDATE fact_versions SET review_state='candidate' "
                "WHERE fact_version_id=?",
                (expected_facts[0],),
            )


# ── 2. 同回执重放幂等 + 迟到事件失败恢复 ─────────────────────────────────────


def test_same_receipt_replay_is_idempotent(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    first = _accept(world)
    facts_after_first = _fact_states(world.root)
    claims_after_first = _claim_states(world.root)
    versions_after_first = _fact_version_count(world.root)

    replay = _accept(world)

    assert replay == first
    assert _fact_states(world.root) == facts_after_first
    assert _claim_states(world.root) == claims_after_first
    assert _fact_version_count(world.root) == versions_after_first
    assert len(_acceptance_events(world.root, world.receipt.receipt_digest)) == 1


def test_late_event_failure_is_repaired_by_same_receipt_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = _build_world(tmp_path)

    def _failing_append(self: EventStore, event: Any) -> Any:
        raise OSError("injected event append failure")

    monkeypatch.setattr(EventStore, "append", _failing_append)
    with pytest.raises(OSError, match="injected event append failure"):
        _accept(world)

    # 物化事务已提交且幂等键已记录；事件尚未写入
    facts_after_fault = _fact_states(world.root)
    for version_id in _bound_fact_version_ids(world):
        assert facts_after_fault[version_id][0] == "accepted"
    assert _acceptance_events(world.root, world.receipt.receipt_digest) == []
    with open_database(world.root / "state/project.sqlite") as database:
        ledger = database.execute(
            "SELECT operation FROM idempotency_keys WHERE idempotency_key=?",
            (f"source.fact.acceptance:{world.receipt.receipt_digest}",),
        ).fetchone()
    assert ledger == ("source.fact.acceptance",)

    monkeypatch.undo()
    result = _accept(world)

    assert result.accepted_fact_version_ids == _bound_fact_version_ids(world)
    assert _fact_states(world.root) == facts_after_fault
    assert len(_acceptance_events(world.root, world.receipt.receipt_digest)) == 1


@pytest.mark.parametrize("stage", ["before_transaction", "after_updates"])
def test_precommit_failure_retries_original_intent_at_later_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """A real SQLite rollback must not strand the already durable intent."""
    world = _build_world(tmp_path)
    before = _fact_states(world.root)
    claims_before = _claim_states(world.root)
    snapshots_before = _file_digests(world.root, "snapshots")

    def injected_failure(*args: Any, **kwargs: Any) -> None:
        raise OSError("injected precommit failure")

    target = "_materialize" if stage == "before_transaction" else "_restore_append_only_guards"
    with monkeypatch.context() as patch:
        patch.setattr(acceptance_service, target, injected_failure)
        with pytest.raises(OSError, match="injected precommit failure"):
            _accept(world)

    path = world.root / source_fact_acceptance_decision_path("A", world.receipt.receipt_digest)
    decision_before = path.read_bytes()
    assert datetime.fromisoformat(json.loads(decision_before)["accepted_at"]) == CHECKED_AT
    assert _fact_states(world.root) == before
    assert _claim_states(world.root) == claims_before
    assert _acceptance_events(world.root, world.receipt.receipt_digest) == []
    with open_database(world.root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT 1 FROM idempotency_keys WHERE idempotency_key=?",
            (f"source.fact.acceptance:{world.receipt.receipt_digest}",),
        ).fetchone() is None
        for trigger in ("fact_versions_no_update", "claim_versions_no_update"):
            assert database.execute(
                "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?", (trigger,)
            ).fetchone() is not None

    result = _accept(world, checked_at=CHECKED_AT + timedelta(hours=1))
    assert result.accepted_at == CHECKED_AT
    assert path.read_bytes() == decision_before
    assert result.accepted_fact_version_ids == _bound_fact_version_ids(world)
    assert _accept(world, checked_at=CHECKED_AT + timedelta(hours=2)) == result
    assert len(_acceptance_events(world.root, world.receipt.receipt_digest)) == 1
    assert _file_digests(world.root, "snapshots") == snapshots_before
    assert not (world.root / "reports/current.json").exists()


@pytest.mark.parametrize("drift", ["fact_set", "future_time"])
def test_uncommitted_intent_drift_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    world = _build_world(tmp_path)
    before = _fact_states(world.root)

    def injected_failure(*args: Any, **kwargs: Any) -> None:
        raise OSError("injected precommit failure")

    with monkeypatch.context() as patch:
        patch.setattr(acceptance_service, "_materialize", injected_failure)
        with pytest.raises(OSError, match="injected precommit failure"):
            _accept(world)

    path = world.root / source_fact_acceptance_decision_path("A", world.receipt.receipt_digest)
    payload = json.loads(path.read_bytes())
    if drift == "fact_set":
        payload["accepted_fact_version_ids"] = []
    else:
        payload["accepted_at"] = (CHECKED_AT + timedelta(days=1)).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    drifted_bytes = path.read_bytes()
    with pytest.raises(SourceFactAcceptanceError):
        _accept(world, checked_at=CHECKED_AT + timedelta(hours=1))
    assert _fact_states(world.root) == before
    assert path.read_bytes() == drifted_bytes
    assert _acceptance_events(world.root, world.receipt.receipt_digest) == []


# ── 3. 缺失 / 未签发 / 过期回执失败关闭 ──────────────────────────────────────


def test_absent_receipt_fails_closed(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    (world.root / scientific_review_receipt_path("A")).unlink()
    (world.root / review_issuance_record_path("A")).unlink()
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="回执"):
        _accept(world)

    assert _fact_states(world.root) == before


def _hand_written_receipt(
    world: _World,
    *,
    reviewer_id: str = "independent-reviewer",
    session_id: str = "review-session-9",
) -> ScientificReviewReceipt:
    context = world.context
    artifact_digest = hashlib.sha256((world.root / VERDICT_RELATIVE).read_bytes()).hexdigest()
    return build_scientific_review_receipt(
        host="codex",
        issued_at=ISSUED_AT,
        production=ReviewProductionContext(
            project_id=context.project_id,
            report_kind="A",
            report_version=context.report_version,
            report_object_id=context.report_object_id,
            candidate_snapshot_id=context.candidate_snapshot_id,
            candidate_content_digest=context.candidate_content_digest,
            producer_id=context.producer_id,
            producer_session_id="producer-session-1",
            criteria_version=context.criteria_version,
            gate_result_key=context.gate_result_key,
            produced_at=PRODUCED_AT,
            production_context_digest=context.context_digest,
        ),
        review=ReviewContextEvidence(
            reviewer_id=reviewer_id,
            host_executable=HOST_EXECUTABLE,
            session=ReviewHostSession(
                session_id=session_id,
                launcher_pid=REVIEW_SESSION.launcher_pid,
                launcher_parent_pid=REVIEW_SESSION.launcher_parent_pid,
            ),
            process=ReviewProcessEvidence(
                kind="external_subprocess",
                pid=4242,
                argv=(HOST_PATH, *REVIEW_ARGV),
                cwd="/tmp/项目-r24-114",
                started_at=REVIEW_STARTED_AT,
                finished_at=REVIEW_FINISHED_AT,
                returncode=0,
            ),
            independent_context="external_subprocess_session",
        ),
        content=ReviewContentBinding(
            reviewed_content_digest=context.candidate_content_digest,
            review_input_digest=_review_bundle(context).input_digest,
        ),
        artifact=ReviewArtifactBinding(
            artifact_kind="scientific_qc_verdict",
            path=VERDICT_RELATIVE,
            artifact_sha256=artifact_digest,
        ),
    )


def test_self_consistent_manual_receipt_without_issuer_record_fails_closed(
    tmp_path: Path,
) -> None:
    world = _build_world(tmp_path)
    hand = _hand_written_receipt(world)
    (world.root / scientific_review_receipt_path("A")).write_text(
        json.dumps(hand.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
    )
    (world.root / review_issuance_record_path("A")).unlink()
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="签发记录"):
        _accept(world)

    assert _fact_states(world.root) == before
    assert not (
        world.root / source_fact_acceptance_decision_path("A", hand.receipt_digest)
    ).exists()
    assert _acceptance_events(world.root, hand.receipt_digest) == []


def test_expired_verdict_refuses_acceptance(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="失效"):
        _accept(world, checked_at=VALID_UNTIL)

    assert _fact_states(world.root) == before
    assert not (
        world.root / source_fact_acceptance_decision_path("A", world.receipt.receipt_digest)
    ).exists()


def test_unverified_receipt_artifact_drift_fails_closed(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    (world.root / VERDICT_RELATIVE).write_bytes(b"tampered verdict bytes\n")
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="复核产物"):
        _accept(world)

    assert _fact_states(world.root) == before
    assert not (
        world.root / source_fact_acceptance_decision_path("A", world.receipt.receipt_digest)
    ).exists()
    assert _acceptance_events(world.root, world.receipt.receipt_digest) == []


def test_replaced_receipt_with_genuine_issuer_record_fails_closed(
    tmp_path: Path,
) -> None:
    world = _build_world(tmp_path)
    hand = _hand_written_receipt(world)
    (world.root / scientific_review_receipt_path("A")).write_text(
        json.dumps(hand.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
    )
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="不一致|替换"):
        _accept(world)

    assert _fact_states(world.root) == before
    assert not (
        world.root / source_fact_acceptance_decision_path("A", hand.receipt_digest)
    ).exists()
    assert _acceptance_events(world.root, hand.receipt_digest) == []


def test_self_review_and_same_session_receipts_fail_closed(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    before = _fact_states(world.root)

    # 生产环境在回执构造期就拒绝生产者自审身份与同会话复核：伪回执根本
    # 无法构造；无真实签发记录的文件路径由专项用例覆盖。
    with pytest.raises(PydanticValidationError, match="不同身份"):
        _hand_written_receipt(world, reviewer_id=world.context.producer_id)
    with pytest.raises(PydanticValidationError, match="同会话"):
        _hand_written_receipt(world, session_id="producer-session-1")

    assert _fact_states(world.root) == before
    assert _acceptance_events(world.root, world.receipt.receipt_digest) == []


# ── 4. 快照/事实集替换与快照字节漂移失败关闭 ────────────────────────────────


def test_snapshot_identity_substitution_refused(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    unrelated = _ingest_unrelated(world.root, world.project_id)
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="快照|绑定|覆盖"):
        _accept(world, claim_snapshot_id=unrelated.evidence_snapshot.snapshot_id)

    assert _fact_states(world.root) == before


def test_other_project_snapshot_identity_refused(tmp_path: Path) -> None:
    world = _build_world(tmp_path, name="world-a")
    other = _build_world(tmp_path, name="world-b")
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="快照|绑定|覆盖"):
        _accept(world, evidence_snapshot_id=other.lineage.evidence_snapshot.snapshot_id)

    assert _fact_states(world.root) == before


def test_evidence_snapshot_byte_drift_refused(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    snapshot_path = world.root / world.lineage.evidence_snapshot.relative_path
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["closure"]["claims"][0]["claim"]["claim_text"] = "被篡改的声明文本"
    snapshot_path.write_text(
        json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="快照"):
        _accept(world)

    assert _fact_states(world.root) == before


def test_historical_snapshot_schema_refused(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    historical = {
        "schema_version": "1.0",
        "project_id": world.project_id,
        "contract_version": 1,
        "data_cutoff": DATA_CUTOFF.isoformat(),
        "source_version_ids": list(world.lineage.source_version_ids),
        "fragment_ids": list(world.lineage.fragment_ids),
        "fact_version_ids": list(world.lineage.fact_version_ids),
        "scientific_content_digest": world.content_digest,
        "created_at": PRODUCED_AT.isoformat(),
    }
    locked = compute_locked_snapshot(kind="evidence", report=None, manifest=historical)
    historical_path = world.root / locked.relative_path
    historical_path.write_text(
        json.dumps(historical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="历史|快照"):
        _accept(world, evidence_snapshot_id=locked.snapshot_id)

    assert _fact_states(world.root) == before


# ── 5. 未解决的来源冲突与用户层兄弟版本 ─────────────────────────────────────


def test_unresolved_source_conflict_refuses_acceptance(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    _ingest_conflicting_reingest(world.root, world.project_id)
    before = _fact_states(world.root)

    with pytest.raises(SourceFactAcceptanceError, match="冲突"):
        _accept(world)

    assert _fact_states(world.root) == before


def test_user_modified_sibling_stays_user_modified(tmp_path: Path) -> None:
    world = _build_world(tmp_path)
    bound_version = _bound_fact_version_ids(world)[0]
    with open_database(world.root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT fact_id,entity_id,field_id,raw_value,normalized_value,disclosure_state,"
            "primary_fragment_id,content_sha256,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?",
            (bound_version,),
        ).fetchone()
        assert row is not None
        user_version = stable_id("fact-version", "test-user-modification", bound_version)
        database.execute(
            "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,raw_value,"
            "normalized_value,disclosure_state,review_state,primary_fragment_id,"
            "supersedes_fact_version_id,created_at,content_sha256,scientific_context_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                user_version,
                str(row[0]),
                str(row[1]),
                str(row[2]),
                "30% (24/80)",
                "30.0",
                str(row[5]),
                "user_modified",
                str(row[6]),
                bound_version,
                CHECKED_AT.isoformat(),
                str(row[7]),
                str(row[8]),
            ),
        )

    result = _accept(world)

    assert result.accepted_fact_version_ids == _bound_fact_version_ids(world)
    with open_database(world.root / "state/project.sqlite") as database:
        user_row = database.execute(
            "SELECT review_state,raw_value,normalized_value,supersedes_fact_version_id "
            "FROM fact_versions WHERE fact_version_id=?",
            (user_version,),
        ).fetchone()
        bound_state = database.execute(
            "SELECT review_state FROM fact_versions WHERE fact_version_id=?",
            (bound_version,),
        ).fetchone()
    assert user_row == ("user_modified", "30% (24/80)", "30.0", bound_version)
    assert bound_state == ("accepted",)


# ── 6. 公开面锁定：无调用方布尔或裸事实标识 ─────────────────────────────────


def test_public_surface_accepts_no_caller_fact_ids_or_booleans() -> None:
    import inspect

    parameters = inspect.signature(accept_reviewed_source_facts).parameters
    assert set(parameters) == {
        "project_root",
        "report_kind",
        "evidence_snapshot_id",
        "claim_snapshot_id",
        "checked_at",
    }


@pytest.mark.parametrize("issued", [True, False])
def test_native_cli_materializes_only_the_genuinely_issued_fixture_set(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], issued: bool,
) -> None:
    """The issuer runner is a unit simulation, not actual clinical acceptance."""
    world = _build_world(tmp_path)
    if not issued:
        (world.root / review_issuance_record_path("A")).unlink()
    before = _fact_states(world.root)
    args = [
        "review", "accept-source-facts", "--root", str(world.root), "--report", "A",
        "--evidence-snapshot", world.lineage.evidence_snapshot.snapshot_id,
        "--claim-snapshot", world.claim_snapshot_id,
    ]
    code = main(args)
    output = capsys.readouterr()
    if issued:
        assert code == 0, output.err
        result = json.loads(output.out.removeprefix("SOURCE_FACTS_ACCEPTED "))
        assert result["accepted_fact_version_ids"] == list(_bound_fact_version_ids(world))
        assert main(args) == 0
        assert len(_acceptance_events(world.root, world.receipt.receipt_digest)) == 1
    else:
        assert code == 2
        assert "签发记录" in output.err
        assert _fact_states(world.root) == before
        assert _acceptance_events(world.root, world.receipt.receipt_digest) == []
    assert not (world.root / "reports/current.json").exists()
