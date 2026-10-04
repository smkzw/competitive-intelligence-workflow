"""R141: authority stays bound during long review, exact replay, and bad pointers.

Uses the production epoch/issuer APIs and real temporary SQLite/CAS. External
review is an explicitly simulated process seam, never a clinical approval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.review_issuer import (
    ExternalProcessResult,
    ReviewIssuanceError,
    issue_review_receipt,
)
from ci_workflow.application.scientific_review_transition import (
    ScientificReviewTransitionError,
    active_scientific_review_scope,
    advance_scientific_review_epoch,
    capture_portal_artifact_binding,
)
from ci_workflow.storage.scientific_review_epoch import (
    build_scientific_review_epoch_pointer,
    epoch_pointer_path,
    read_epoch_pointer,
    write_epoch_pointer,
)
from tests.integration import test_r24_scientific_review_epochs as fixture


@pytest.mark.parametrize("changed", ["portal", "producer", "produced_at"])
def test_exact_activation_replay_rejects_changed_request_binding(
    tmp_path: Path, changed: str,
) -> None:
    world = fixture._build_world(tmp_path)
    context, _, _ = fixture._context_for_epoch(world, epoch=1)
    fixture._advance(world.root, world.context, context, epoch=1)
    pointer_before = (world.root / epoch_pointer_path("A")).read_bytes()
    manifest, site = fixture._portal_relative(1)
    binding = capture_portal_artifact_binding(
        world.root, "A", manifest_relative=manifest, site_relative=site,
    )
    producer = "producer-run-e1"
    produced_at = fixture.EPOCH_TIMELINES[1]["produced"]
    if changed == "portal":
        binding = binding.model_copy(update={"site_sha256": "f" * 64})
    elif changed == "producer":
        producer = "another-producer-session"
    else:
        produced_at = fixture.EPOCH_TIMELINES[2]["produced"]
    with pytest.raises(ScientificReviewTransitionError, match="重放|绑定|请求"):
        advance_scientific_review_epoch(
            project_root=world.root, report_kind="A",
            expected_predecessor_context=world.context, next_context=context,
            producer_session_id=producer, produced_at=produced_at,
            portal_binding=binding, advanced_at=fixture.ADVANCED_AT[1],
        )
    assert (world.root / epoch_pointer_path("A")).read_bytes() == pointer_before


def test_long_review_cannot_write_old_authority_into_next_epoch(
    tmp_path: Path,
) -> None:
    world = fixture._build_world(tmp_path)
    context1, _, _ = fixture._context_for_epoch(world, epoch=1)
    context2, _, _ = fixture._context_for_epoch(world, epoch=2)
    fixture._advance(world.root, world.context, context1, epoch=1)
    old_scope = active_scientific_review_scope(world.root, "A")
    next_receipt: Path | None = None

    def runner(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        nonlocal next_receipt
        fixture._advance(world.root, context1, context2, epoch=2)
        scope = active_scientific_review_scope(world.root, "A")
        next_receipt = world.root / scope.receipt_relative
        import json

        verdict = world.root / fixture._verdict_relative(1)
        verdict.parent.mkdir(parents=True, exist_ok=True)
        verdict.write_text(json.dumps(fixture._verdict_payload(context1, 1)))
        timeline = fixture.EPOCH_TIMELINES[1]
        return ExternalProcessResult(
            pid=4243, argv=argv, cwd=cwd, returncode=0,
            started_at=timeline["started"], finished_at=timeline["finished"],
        )

    with pytest.raises(ReviewIssuanceError, match="作用域|纪元|请求|上下文"):
        issue_review_receipt(
            project_root=world.root, report_kind="A",
            reviewer_id="independent-reviewer", review_session_id="review-session-9",
            host="codex", host_executable=fixture.HOST_EXECUTABLE,
            review_argv=fixture.REVIEW_ARGV,
            verdict_relative_path=fixture._verdict_relative(1),
            session=fixture.REVIEW_SESSION, runner=runner,
            clock=lambda: fixture.EPOCH_TIMELINES[1]["issued"],
        )
    assert next_receipt is not None and not next_receipt.exists()
    assert not (world.root / old_scope.receipt_relative).exists()


def test_issued_epoch_is_not_overwritten_or_executed_again(tmp_path: Path) -> None:
    world = fixture._build_world(tmp_path)
    fixture._issue(world.root, world.context, epoch=0)
    before = fixture._lifecycle_digests(world.root, epochs=(0,))
    calls: list[tuple[str, ...]] = []

    def runner(argv: tuple[str, ...], cwd: str, timeout: float) -> Any:
        calls.append(argv)
        raise AssertionError("an issued immutable scope must reject before execution")

    with pytest.raises(ReviewIssuanceError, match="已签发|不可覆盖|纪元"):
        issue_review_receipt(
            project_root=world.root, report_kind="A",
            reviewer_id="independent-reviewer", review_session_id="review-session-9",
            host="codex", host_executable=fixture.HOST_EXECUTABLE,
            review_argv=fixture.REVIEW_ARGV,
            verdict_relative_path=fixture._verdict_relative(0),
            session=fixture.REVIEW_SESSION, runner=runner,
            clock=lambda: fixture.EPOCH_TIMELINES[0]["issued"],
        )
    assert calls == []
    assert fixture._lifecycle_digests(world.root, epochs=(0,)) == before


def test_non_file_pointer_does_not_reactivate_legacy_scope(tmp_path: Path) -> None:
    world = fixture._build_world(tmp_path)
    (world.root / epoch_pointer_path("A")).mkdir()
    with pytest.raises(ScientificReviewTransitionError, match="指针"):
        active_scientific_review_scope(world.root, "A")


def test_valid_pointer_for_other_report_cannot_select_scope(tmp_path: Path) -> None:
    world = fixture._build_world(tmp_path)
    context, _, _ = fixture._context_for_epoch(world, epoch=1)
    fixture._advance(world.root, world.context, context, epoch=1)
    pointer = read_epoch_pointer(world.root, "A")
    assert pointer is not None
    foreign = build_scientific_review_epoch_pointer(
        project_id=pointer.project_id, report_kind="B",
        epochs=pointer.epochs, active_epoch=pointer.active_epoch,
    )
    write_epoch_pointer(world.root, "A", foreign)
    with pytest.raises(ScientificReviewTransitionError, match="指针"):
        active_scientific_review_scope(world.root, "A")
