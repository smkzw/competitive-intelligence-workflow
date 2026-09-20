"""HTML-only terminal partial-delivery recovery contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.recovery import (
    ContractDriftError,
    CoordinationError,
    DeliveryContract,
    PartialDeliveryCoordinator,
    format_object_id,
)
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.storage.event_store import EventConflictError
from tests.graph._qc_authorization_fixture import issue_test_qc_authorization
from tests.graph.test_visual_finalization_graph_negative import (
    _candidate_evidence,
    _delivery_evidence,
    _passed_evidence,
    _queued_generation_evidence,
)

NOW = datetime(2026, 9, 5, 2, 0, tzinfo=UTC)
PROJECT_ID = "project-html-terminal"
Submit = Callable[[str, str, str | None, str, str, dict[str, object], str], None]


def _digest(value: object) -> str:
    encoded = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _submitter(executor: GraphExecutor, *, run_id: str) -> Submit:
    def submit(
        family: str,
        object_id: str,
        from_state: str | None,
        to_state: str,
        trigger: str,
        evidence: dict[str, object],
        request_id: str,
    ) -> None:
        if trigger == "isolated_qc_accepted":
            evidence = dict(evidence)
            evidence["qc_authorization_id"] = issue_test_qc_authorization(
                executor,
                report_object_id=object_id,
                from_state=str(from_state),
                to_state=to_state,
                verdict="accepted",
                evidence_digest=_digest(evidence),
                actor_id="test-executor",
                project_id=PROJECT_ID,
                occurred_at=NOW,
            )
        event = executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id=PROJECT_ID,
                run_id=run_id,
                family=family,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                evidence=evidence,
                actor_id="test-executor",
                occurred_at=NOW,
            )
        )
        assert event.event_type == "graph.transition.accepted", event.payload

    return submit


def _start_project(submit: Submit) -> None:
    submit(
        "project",
        "project-1",
        None,
        "running",
        "project_contract_and_preflight",
        {"project_contract_established": True, "preflight_records_established": True},
        "project:create",
    )


def _lock_report(submit: Submit, kind: str) -> None:
    object_id = f"report_{kind}"
    submit(
        "report_evidence",
        object_id,
        "queued",
        "collecting",
        "candidate_scope_locked",
        {"candidate_scope_locked": True},
        f"{kind}:collecting",
    )
    submit(
        "report_evidence",
        object_id,
        "collecting",
        "scientific_qc",
        "gate_deterministic_pass",
        {"gate_deterministic_pass": True, "candidate_snapshot_established": True},
        f"{kind}:qc",
    )
    submit(
        "report_evidence",
        object_id,
        "scientific_qc",
        "snapshot_locked",
        "isolated_qc_accepted",
        {
            "isolated_qc_accepted": True,
            "qc_verdict_id": f"qc-{kind}",
            "qc_verdict_digest": "a" * 64,
            "qc_candidate_snapshot_id": f"snapshot-{kind}",
            "qc_candidate_content_digest": "b" * 64,
            "qc_review_input_digest": "c" * 64,
            "qc_report_object_id": object_id,
            "qc_context_digest": "d" * 64,
        },
        f"{kind}:locked",
    )


def _deliver_html(submit: Submit, kind: str) -> None:
    object_id = format_object_id(f"report_{kind}", "html")
    for from_state, to_state, trigger, evidence in (
        ("queued", "generating", "snapshot_locked_ready", _queued_generation_evidence()),
        ("generating", "quality_check", "artifact_built", _candidate_evidence()),
        ("quality_check", "passed", "acceptance_records_complete", _passed_evidence()),
        ("passed", "delivery_ready", "atomic_publish_manifest", _delivery_evidence()),
    ):
        submit(
            "format_artifact",
            object_id,
            from_state,
            to_state,
            trigger,
            evidence,
            f"{kind}:html:{to_state}",
        )


def _terminal_partial_delivery(
    coordinator: PartialDeliveryCoordinator,
    contract: DeliveryContract,
) -> None:
    first = coordinator.reconcile(contract, actor_id="coordinator", occurred_at=NOW)
    assert first.submitted is not None
    if first.submitted.payload["to_state"] == "partially_delivered":
        second = coordinator.reconcile(contract, actor_id="coordinator", occurred_at=NOW)
        assert second.submitted is not None
        assert second.submitted.payload["to_state"] == "partial_delivery_blocked"
    else:
        assert first.submitted.payload["to_state"] == "partial_delivery_blocked"


def test_terminal_report_block_requires_reopen_and_new_target(tmp_path: Path) -> None:
    run_id = "run-report-recovery"
    executor = GraphExecutor(tmp_path / "report-recovery", run_id=run_id)
    coordinator = PartialDeliveryCoordinator(executor)
    contract = DeliveryContract(
        contract_id="contract-report-recovery",
        contract_version=1,
        reports=("A", "B"),
    )
    submit = _submitter(executor, run_id=run_id)
    _start_project(submit)
    _lock_report(submit, "A")
    _deliver_html(submit, "A")
    submit(
        "report_evidence",
        "report_B",
        "queued",
        "collecting",
        "candidate_scope_locked",
        {"candidate_scope_locked": True},
        "B:collecting",
    )
    submit(
        "report_evidence",
        "report_B",
        "collecting",
        "evidence_blocked",
        "recovery_exhausted_gap_remains",
        {
            "critical_units_still_failing": True,
            "recovery_exhausted": True,
            "independent_review_exhausted": True,
            "no_continuable_user_action": True,
        },
        "B:blocked",
    )
    _terminal_partial_delivery(coordinator, contract)

    before = len(executor.store.read_all())
    silent = coordinator.reconcile(contract, actor_id="coordinator", occurred_at=NOW)
    assert silent.submitted is None
    assert len(executor.store.read_all()) == before

    reopened = coordinator.reopen_project(
        contract,
        reason="user_material_accepted",
        actor_id="coordinator",
        occurred_at=NOW,
    )
    assert reopened.submitted is not None
    assert executor.state()["project"]["project-1"] == "running"

    rebound = coordinator.rebind_report(
        contract,
        kind="B",
        old_object_id="report_B",
        new_object_id="report_B_v2",
        reason="user_material_accepted",
        actor_id="coordinator",
        occurred_at=NOW,
    )
    assert rebound.submitted is not None
    assert executor.state()["report_evidence"]["report_B"] == "evidence_blocked"
    targets = {target.report_object_id for target in rebound.conditions.target_matrix}
    assert "report_B_v2" in targets
    assert "report_B" not in targets

    event_count = len(executor.store.read_all())
    replay = coordinator.rebind_report(
        contract,
        kind="B",
        old_object_id="report_B",
        new_object_id="report_B_v2",
        reason="user_material_accepted",
        actor_id="coordinator",
        occurred_at=NOW,
    )
    assert replay.submitted is None
    assert replay.note == "replay_noop"
    assert len(executor.store.read_all()) == event_count
    with pytest.raises(ContractDriftError):
        coordinator.rebind_report(
            contract,
            kind="B",
            old_object_id="report_B",
            new_object_id="report_B_v2",
            reason="environment_fix_confirmed",
            actor_id="coordinator",
            occurred_at=NOW,
        )


def test_blocked_html_reopens_only_by_explicit_format_recovery(tmp_path: Path) -> None:
    run_id = "run-html-recovery"
    executor = GraphExecutor(tmp_path / "html-recovery", run_id=run_id)
    coordinator = PartialDeliveryCoordinator(executor)
    contract = DeliveryContract(
        contract_id="contract-html-recovery",
        contract_version=1,
        reports=("A", "B"),
    )
    submit = _submitter(executor, run_id=run_id)
    _start_project(submit)
    _lock_report(submit, "A")
    _lock_report(submit, "B")
    _deliver_html(submit, "A")
    b_html = format_object_id("report_B", "html")
    submit(
        "format_artifact",
        b_html,
        "queued",
        "generating",
        "snapshot_locked_ready",
        _queued_generation_evidence(),
        "B:html:generating",
    )
    submit(
        "format_artifact",
        b_html,
        "generating",
        "blocked",
        "format_recovery_exhausted",
        {"format_recovery_exhausted": True, "failure_evidence_saved": True},
        "B:html:blocked",
    )
    _terminal_partial_delivery(coordinator, contract)

    with pytest.raises(CoordinationError):
        coordinator.reopen_format(
            contract,
            report_kind="B",
            fmt="html",
            reason="user_material_accepted",
            actor_id="coordinator",
            occurred_at=NOW,
        )
    reopened = coordinator.reopen_format(
        contract,
        report_kind="B",
        fmt="html",
        reason="generator_fixed",
        actor_id="coordinator",
        occurred_at=NOW,
    )
    assert reopened.submitted is not None
    assert executor.state()["format_artifact"][b_html] == "queued"

    event_count = len(executor.store.read_all())
    replay = coordinator.reopen_format(
        contract,
        report_kind="B",
        fmt="html",
        reason="generator_fixed",
        actor_id="coordinator",
        occurred_at=NOW,
    )
    assert replay.submitted is not None
    assert replay.note == "replay_noop"
    assert len(executor.store.read_all()) == event_count
    with pytest.raises(EventConflictError):
        coordinator.reopen_format(
            contract,
            report_kind="B",
            fmt="html",
            reason="environment_fixed",
            actor_id="coordinator",
            occurred_at=NOW,
        )
