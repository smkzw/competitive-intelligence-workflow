"""Accepted source proof survives pending report review; no old release authority.

Uses real source ingestion, snapshot/consumer registration and product issuer
with the existing explicit test process seam. Not actual clinical acceptance.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.application.c_portal_consumer_registry import (
    CPortalReviewedProjectionError,
)
from ci_workflow.application.review_issuer import ExternalProcessResult, issue_review_receipt
from ci_workflow.application.scientific_review_transition import (
    advance_scientific_review_epoch,
    capture_portal_artifact_binding,
    reload_production_context,
)
from ci_workflow.application.source_fact_acceptance import (
    SourceFactAcceptanceError,
    accept_reviewed_source_facts,
    load_materialized_source_acceptance,
    source_fact_acceptance_decision_path,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.scientific import ScientificQcCurrentContext
from tests.integration.test_r24_reviewed_c_read_projection import (
    _CHECKED_AT,
    _HOST_EXECUTABLE,
    _HOST_PATH,
    _ISSUED_AT,
    _PORTAL_MANIFEST,
    _PORTAL_SITE,
    _REVIEW_ARGV,
    _REVIEW_SESSION,
    _SUBSET_ROWS,
    _VALID_UNTIL,
    _build_reviewed_c_world,
    _database_bytes,
    _file_digests,
    _logical_database_digest,
    _project,
    _review_verdict,
    _ReviewedCWorld,
)


def test_accepted_source_projection_survives_unsigned_next_report_epoch(tmp_path: Path) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = _project(world)
    predecessor = reload_production_context(world.root, "C")
    next_payload = predecessor.model_dump(mode="json", exclude={"context_digest"})
    next_payload.update({
        "context_id": stable_id("scientific-qc-context", world.root.name, "next-report"),
        "candidate_content_digest": hashlib.sha256(b"new-report-not-new-source").hexdigest(),
        "candidate_snapshot_id": stable_id("report-snapshot", "next-candidate"),
        "report_version": "v2-review-next-report",
        "gate_result_key": "next-report-review-gate",
    })
    next_context = ScientificQcCurrentContext.model_validate(next_payload)
    advance_scientific_review_epoch(
        project_root=world.root,
        report_kind="C",
        expected_predecessor_context=predecessor,
        next_context=next_context,
        producer_session_id="next-report-producer",
        produced_at=_CHECKED_AT + timedelta(hours=1),
        advanced_at=_CHECKED_AT + timedelta(hours=1),
        portal_binding=capture_portal_artifact_binding(
            world.root, "C", manifest_relative=_PORTAL_MANIFEST, site_relative=_PORTAL_SITE,
        ),
    )
    # Pending new report has no review receipt. It must not erase historical
    # source adoption, nor implicitly adopt/release anything in this new epoch.
    before = (_logical_database_digest(world.root), _database_bytes(world.root),
              _file_digests(world.root, "state/scientific_review"),
              _file_digests(world.root, "receipts"), _file_digests(world.root, "events"))
    assert _project(world) == original
    assert before == (_logical_database_digest(world.root), _database_bytes(world.root),
                      _file_digests(world.root, "state/scientific_review"),
                      _file_digests(world.root, "receipts"), _file_digests(world.root, "events"))


# ── Shared fixtures for the historical-reopen family ─────────────────────────

_NEXT_EPOCH_VERDICT = "receipts/scientific_review/C/epochs/e1/verdict.json"
_EPOCH_ZERO_RECEIPT = "receipts/scientific_review/C/receipt.json"


def _advance_to_unsigned_next_report_epoch(
    world: _ReviewedCWorld,
) -> ScientificQcCurrentContext:
    """Advance to a genuinely new report epoch that reuses the same source."""
    predecessor = reload_production_context(world.root, "C")
    payload = predecessor.model_dump(mode="json", exclude={"context_digest"})
    payload.update({
        "context_id": stable_id("scientific-qc-context", world.root.name, "next-report"),
        "candidate_content_digest": hashlib.sha256(b"new-report-not-new-source").hexdigest(),
        "candidate_snapshot_id": stable_id("report-snapshot", "next-candidate"),
        "report_version": "v2-review-next-report",
        "gate_result_key": "next-report-review-gate",
    })
    next_context = ScientificQcCurrentContext.model_validate(payload)
    advance_scientific_review_epoch(
        project_root=world.root, report_kind="C",
        expected_predecessor_context=predecessor, next_context=next_context,
        producer_session_id="next-report-producer",
        produced_at=_CHECKED_AT + timedelta(hours=1),
        advanced_at=_CHECKED_AT + timedelta(hours=1),
        portal_binding=capture_portal_artifact_binding(
            world.root, "C", manifest_relative=_PORTAL_MANIFEST, site_relative=_PORTAL_SITE,
        ),
    )
    return next_context


def _advance_to_same_source_next_epoch(world: _ReviewedCWorld) -> ScientificQcCurrentContext:
    """Advance to a new epoch reviewing the exact same evidence snapshot."""
    predecessor = reload_production_context(world.root, "C")
    payload = predecessor.model_dump(mode="json", exclude={"context_digest"})
    payload.update({"gate_result_key": "same-source-next-gate"})
    next_context = ScientificQcCurrentContext.model_validate(payload)
    advance_scientific_review_epoch(
        project_root=world.root, report_kind="C",
        expected_predecessor_context=predecessor, next_context=next_context,
        producer_session_id="same-source-producer",
        produced_at=_CHECKED_AT + timedelta(hours=1),
        advanced_at=_CHECKED_AT + timedelta(hours=1),
        portal_binding=capture_portal_artifact_binding(
            world.root, "C", manifest_relative=_PORTAL_MANIFEST, site_relative=_PORTAL_SITE,
        ),
    )
    return next_context


def _issue_active_scope_receipt(
    world: _ReviewedCWorld,
    context: ScientificQcCurrentContext,
    *,
    verdict_relative: str,
    valid_until: datetime | None = None,
) -> str:
    """Issue one more genuine receipt in the active (next) epoch scope."""
    started = _CHECKED_AT + timedelta(hours=2)
    finished = _CHECKED_AT + timedelta(hours=2, minutes=30)
    issued = _CHECKED_AT + timedelta(hours=3)
    verdict = _review_verdict(context).model_copy(
        update={
            "reviewed_at": finished,
            "valid_until": _VALID_UNTIL if valid_until is None else valid_until,
        }
    )

    def _runner(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        assert argv == (_HOST_PATH, *_REVIEW_ARGV)
        assert cwd == str(world.root)
        assert timeout > 0
        path = world.root / verdict_relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(verdict.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
        )
        return ExternalProcessResult(
            pid=5001, argv=argv, cwd=cwd, started_at=started, finished_at=finished,
            returncode=0, stdout_tail="SCIENTIFIC_REVIEW_DONE verdict=accepted\n",
            stderr_tail="",
        )

    outcome = issue_review_receipt(
        project_root=world.root, report_kind="C", reviewer_id="independent-reviewer",
        review_session_id="review-session-9", host="codex", host_executable=_HOST_EXECUTABLE,
        review_argv=_REVIEW_ARGV, verdict_relative_path=verdict_relative,
        session=_REVIEW_SESSION, runner=_runner, clock=lambda: issued,
    )
    return outcome.receipt.receipt_digest


def _epoch_zero_receipt_digest(world: _ReviewedCWorld) -> str:
    payload = json.loads((world.root / _EPOCH_ZERO_RECEIPT).read_bytes())
    return str(payload["receipt_digest"])


def _world_evidence(root: Path) -> tuple[object, ...]:
    return (
        _logical_database_digest(root),
        _database_bytes(root),
        _file_digests(root, "state/scientific_review"),
        _file_digests(root, "receipts"),
        _file_digests(root, "events"),
    )


def _damage_historical_material(world: _ReviewedCWorld, material: str) -> None:
    """Single-point real damage on the completed epoch-0 lifecycle material."""
    receipt_path = world.root / _EPOCH_ZERO_RECEIPT
    if material == "receipt":
        payload = json.loads(receipt_path.read_bytes())
        payload["issued_at"] = (_ISSUED_AT + timedelta(seconds=1)).isoformat()
        receipt_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return
    if material == "receipt_missing":
        receipt_path.unlink()
        return
    if material in {"issuance", "issuance_missing"}:
        path = world.root / "state/scientific_review/C/issuance.json"
        if material == "issuance_missing":
            path.unlink()
            return
        payload = json.loads(path.read_bytes())
        payload["reviewer_id"] = "replaced-reviewer"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return
    if material == "verdict":
        (world.root / "receipts/scientific_review/C/verdict.json").write_bytes(
            b"tampered verdict bytes\n"
        )
        return
    if material == "request":
        path = world.root / "state/scientific_review/C/review_request.json"
        payload = json.loads(path.read_bytes())
        payload["review_input_digest"] = "0" * 64
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return
    if material == "context":
        path = world.root / "state/scientific_review/C/production_context.json"
        payload = json.loads(path.read_bytes())
        payload["criteria_version"] = "tampered-criteria"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return
    if material == "decision":
        path = world.root / source_fact_acceptance_decision_path(
            "C", _epoch_zero_receipt_digest(world)
        )
        payload = json.loads(path.read_bytes())
        payload["accepted_fact_version_ids"] = list(payload["accepted_fact_version_ids"])[::-1]
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return
    if material == "ledger":
        # Simulate a lost materialization proof: the ledger row is the completion
        # evidence, so without it the era must not be readable.  The append-only
        # delete guard is restored verbatim after the mutation (same pattern as
        # the epoch family's rejected-row fixture).
        database = sqlite3.connect(world.root / "state/project.sqlite")
        try:
            database.execute("DROP TRIGGER idempotency_keys_no_delete")
            database.execute("DROP TRIGGER idempotency_keys_no_update")
            database.execute("DELETE FROM idempotency_keys")
            database.execute(
                "CREATE TRIGGER idempotency_keys_no_update BEFORE UPDATE ON "
                "idempotency_keys BEGIN SELECT RAISE(ABORT, 'append-only: "
                "idempotency_keys'); END"
            )
            database.execute(
                "CREATE TRIGGER idempotency_keys_no_delete BEFORE DELETE ON "
                "idempotency_keys BEGIN SELECT RAISE(ABORT, 'append-only: "
                "idempotency_keys'); END"
            )
            database.commit()
        finally:
            database.close()
        return
    if material == "pointer":
        path = world.root / "state/scientific_review/C/epoch.json"
        payload = json.loads(path.read_bytes())
        payload["active_epoch"] = 2
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return
    raise AssertionError(f"unknown damage material: {material}")


# ── Positive: a signed but unadopted next epoch keeps history readable ───────


def test_historical_acceptance_survives_signed_but_unadopted_next_epoch(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = _project(world)
    next_context = _advance_to_unsigned_next_report_epoch(world)
    # The new report epoch is genuinely signed but has adopted nothing: the new
    # signature must not erase or shadow the completed exact-source adoption,
    # and must not adopt or release anything by itself.
    _issue_active_scope_receipt(world, next_context, verdict_relative=_NEXT_EPOCH_VERDICT)
    before = _world_evidence(world.root)
    assert _project(world) == original
    assert _world_evidence(world.root) == before


def test_historical_read_after_epoch_advance_has_no_write_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = _project(world)
    _advance_to_unsigned_next_report_epoch(world)
    before = _world_evidence(world.root)

    from ci_workflow.application import source_fact_acceptance as acceptance

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("a historical read must not migrate, write, or append an event")

    monkeypatch.setattr(acceptance, "open_database", forbidden)
    monkeypatch.setattr(acceptance, "apply_migrations", forbidden)
    monkeypatch.setattr(acceptance, "_append_acceptance_event", forbidden)
    result = load_materialized_source_acceptance(
        project_root=world.root, report_kind="C",
        evidence_snapshot_id=world.snapshot.snapshot_id,
    )
    decision = json.loads(
        (
            world.root
            / source_fact_acceptance_decision_path("C", _epoch_zero_receipt_digest(world))
        ).read_bytes()
    )
    assert frozenset(result.accepted_fact_version_ids) == frozenset(
        decision["accepted_fact_version_ids"]
    )
    assert result.claim_snapshot_id == world.claim_snapshot_id
    assert _project(world) == original
    assert _world_evidence(world.root) == before


# ── Negative: damaged/unissued/unmaterialized historical material ────────────


_DAMAGE_EXPECTATIONS = (
    ("receipt", "回执"),
    ("receipt_missing", "尚未物化"),
    ("issuance", "签发记录"),
    ("issuance_missing", "签发记录"),
    ("verdict", "复核产物"),
    ("request", "请求"),
    ("context", "上下文"),
    ("decision", "台账"),
    ("ledger", "尚未物化"),
    ("pointer", "epoch 指针"),
)


@pytest.mark.parametrize(("material", "pattern"), _DAMAGE_EXPECTATIONS)
def test_projection_rejects_damaged_historical_material_without_writes(
    tmp_path: Path, material: str, pattern: str,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    _advance_to_unsigned_next_report_epoch(world)
    _damage_historical_material(world, material)
    before = _world_evidence(world.root)
    with pytest.raises(CPortalReviewedProjectionError, match=pattern):
        _project(world)
    # Fail closed without repairing, accepting, migrating or otherwise writing.
    assert _world_evidence(world.root) == before


def test_historical_read_rejects_wrong_report_and_unadopted_snapshot_scope(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    _advance_to_unsigned_next_report_epoch(world)
    # A C-project acceptance never authorizes the same snapshot for another
    # report kind.
    with pytest.raises(SourceFactAcceptanceError, match="尚未物化"):
        load_materialized_source_acceptance(
            project_root=world.root, report_kind="A",
            evidence_snapshot_id=world.snapshot.snapshot_id,
        )
    # An exact snapshot identifier with no completed acceptance anywhere is not
    # silently served by the nearest available decision.
    with pytest.raises(SourceFactAcceptanceError, match="尚未物化"):
        load_materialized_source_acceptance(
            project_root=world.root, report_kind="C",
            evidence_snapshot_id="evidence-snapshot_" + "0" * 24,
        )


# ── Duplicate legitimate decisions: deterministic newest-epoch resolution ────


def test_duplicate_legitimate_decisions_resolve_to_newest_epoch_deterministically(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = _project(world)
    epoch_zero_receipt = _epoch_zero_receipt_digest(world)
    next_context = _advance_to_same_source_next_epoch(world)
    next_receipt = _issue_active_scope_receipt(
        world, next_context, verdict_relative=_NEXT_EPOCH_VERDICT
    )
    adopted = accept_reviewed_source_facts(
        project_root=world.root, report_kind="C",
        evidence_snapshot_id=world.snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        checked_at=_CHECKED_AT + timedelta(hours=4),
    )
    assert adopted.receipt_digest == next_receipt
    before = _world_evidence(world.root)

    first = load_materialized_source_acceptance(
        project_root=world.root, report_kind="C",
        evidence_snapshot_id=world.snapshot.snapshot_id,
    )
    assert first == load_materialized_source_acceptance(
        project_root=world.root, report_kind="C",
        evidence_snapshot_id=world.snapshot.snapshot_id,
    )
    # The newest verified epoch owns the resolution; the older completed
    # decision record is neither deleted nor rewritten.
    assert first.receipt_digest == next_receipt
    assert first.receipt_digest != epoch_zero_receipt
    assert (
        world.root / source_fact_acceptance_decision_path("C", epoch_zero_receipt)
    ).is_file()
    assert (world.root / source_fact_acceptance_decision_path("C", next_receipt)).is_file()
    assert _project(world) == original
    assert _world_evidence(world.root) == before


def test_completed_historical_adoption_survives_later_verdict_expiry(
    tmp_path: Path,
) -> None:
    """Validity is verified at the original issuance/adoption times.

    The adoption below is completed while its verdict is valid but the validity
    window has long passed by the time of the read: a genuine completed adoption
    must not be retroactively rejected by the current clock.
    """
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = _project(world)
    next_context = _advance_to_same_source_next_epoch(world)
    next_receipt = _issue_active_scope_receipt(
        world, next_context, verdict_relative=_NEXT_EPOCH_VERDICT,
        valid_until=_CHECKED_AT + timedelta(hours=6),
    )
    adopted = accept_reviewed_source_facts(
        project_root=world.root, report_kind="C",
        evidence_snapshot_id=world.snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        checked_at=_CHECKED_AT + timedelta(hours=4),
    )
    assert adopted.receipt_digest == next_receipt
    before = _world_evidence(world.root)

    result = load_materialized_source_acceptance(
        project_root=world.root, report_kind="C",
        evidence_snapshot_id=world.snapshot.snapshot_id,
    )

    assert result.receipt_digest == next_receipt
    assert (world.root / source_fact_acceptance_decision_path("C", next_receipt)).is_file()
    assert _project(world) == original
    assert _world_evidence(world.root) == before


def test_historical_read_surface_takes_no_caller_authority() -> None:
    parameters = inspect.signature(load_materialized_source_acceptance).parameters
    assert set(parameters) == {"project_root", "report_kind", "evidence_snapshot_id"}


def test_signed_new_report_cannot_readopt_historical_source_snapshot(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = _project(world)
    next_context = _advance_to_unsigned_next_report_epoch(world)
    _issue_active_scope_receipt(world, next_context, verdict_relative=_NEXT_EPOCH_VERDICT)
    before = _world_evidence(world.root)
    with pytest.raises(SourceFactAcceptanceError, match="科学内容摘要.*候选内容不一致"):
        accept_reviewed_source_facts(
            project_root=world.root, report_kind="C",
            evidence_snapshot_id=world.snapshot.snapshot_id,
            claim_snapshot_id=world.claim_snapshot_id,
            checked_at=_CHECKED_AT + timedelta(hours=4),
        )
    assert _world_evidence(world.root) == before
    assert _project(world) == original


def test_historical_source_read_does_not_revalidate_old_report_surface(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = _project(world)
    _advance_to_unsigned_next_report_epoch(world)
    # Source evidence, pinned consumer input and review verdict remain intact;
    # changing only the old report surface cannot create or erase source proof.
    (world.root / _PORTAL_SITE / "index.html").write_text(
        "changed report surface, not source evidence", encoding="utf-8",
    )
    before = _world_evidence(world.root)
    assert _project(world) == original
    assert _world_evidence(world.root) == before
