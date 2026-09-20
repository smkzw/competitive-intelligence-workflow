"""HTML-only partial delivery remains report-scoped and contract-bound."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.graph.test_visual_finalization_graph_negative import (
    _candidate_evidence,
    _delivery_evidence,
    _passed_evidence,
    _queued_generation_evidence,
)

NOW = datetime(2026, 9, 5, 1, 0, tzinfo=UTC)


def _digest(value: object) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_reports_progress_independently_with_html_only_partial_delivery(
    tmp_path: Path,
) -> None:
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.graph.recovery import (
        DeliveryContract,
        PartialDeliveryCoordinator,
        format_object_id,
    )
    from ci_workflow.graph.types import TransitionRequest
    from tests.graph._qc_authorization_fixture import issue_test_qc_authorization

    executor = GraphExecutor(tmp_path / "project", run_id="run-html-only")
    coordinator = PartialDeliveryCoordinator(executor)
    contract = DeliveryContract(
        contract_id="contract-html-only",
        contract_version=1,
        reports=("A", "B", "C"),
    )
    with pytest.raises(ValueError, match="HTML|html"):
        DeliveryContract(
            contract_id="invalid-format",
            contract_version=1,
            reports=("A",),
            optional_formats=("pptx",),
        )

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
            evidence_digest = _digest(
                {key: value for key, value in evidence.items() if key != "qc_authorization_id"}
            )
            evidence["qc_authorization_id"] = issue_test_qc_authorization(
                executor,
                report_object_id=object_id,
                from_state=str(from_state),
                to_state=to_state,
                verdict="accepted",
                evidence_digest=evidence_digest,
                actor_id="test-executor",
                project_id="project-html-only",
                occurred_at=NOW,
            )
        event = executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id="project-html-only",
                run_id="run-html-only",
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

    submit(
        "project",
        "project-1",
        None,
        "running",
        "project_contract_and_preflight",
        {"project_contract_established": True, "preflight_records_established": True},
        "project:create",
    )
    for from_state, to_state, trigger, evidence in (
        ("queued", "collecting", "candidate_scope_locked", {"candidate_scope_locked": True}),
        (
            "collecting",
            "scientific_qc",
            "gate_deterministic_pass",
            {"gate_deterministic_pass": True, "candidate_snapshot_established": True},
        ),
        (
            "scientific_qc",
            "snapshot_locked",
            "isolated_qc_accepted",
            {
                "isolated_qc_accepted": True,
                "qc_verdict_id": "qc-1",
                "qc_verdict_digest": "a" * 64,
                "qc_candidate_snapshot_id": "snapshot-1",
                "qc_candidate_content_digest": "b" * 64,
                "qc_review_input_digest": "c" * 64,
                "qc_report_object_id": "report_A",
                "qc_context_digest": "d" * 64,
            },
        ),
    ):
        submit(
            "report_evidence",
            "report_A",
            from_state,
            to_state,
            trigger,
            evidence,
            f"A:{to_state}",
        )
    submit(
        "report_evidence", "report_B", "queued", "collecting", "candidate_scope_locked",
        {"candidate_scope_locked": True}, "B:collecting",
    )
    submit(
        "report_evidence", "report_B", "collecting", "evidence_blocked",
        "recovery_exhausted_gap_remains",
        {
            "critical_units_still_failing": True,
            "recovery_exhausted": True,
            "independent_review_exhausted": True,
            "no_continuable_user_action": True,
        },
        "B:blocked",
    )
    submit(
        "report_evidence", "report_C", "queued", "collecting", "candidate_scope_locked",
        {"candidate_scope_locked": True}, "C:collecting",
    )
    html_id = format_object_id("report_A", "html")
    for from_state, to_state, trigger, evidence in (
        ("queued", "generating", "snapshot_locked_ready", _queued_generation_evidence()),
        ("generating", "quality_check", "artifact_built", _candidate_evidence()),
        ("quality_check", "passed", "acceptance_records_complete", _passed_evidence()),
        ("passed", "delivery_ready", "atomic_publish_manifest", _delivery_evidence()),
    ):
        submit(
            "format_artifact",
            html_id,
            from_state,
            to_state,
            trigger,
            evidence,
            f"A:html:{to_state}",
        )

    result = coordinator.reconcile(contract, actor_id="coordinator", occurred_at=NOW)
    assert result.submitted is not None
    assert result.submitted.payload["to_state"] == "partially_delivered"
    assert {target.object_id for target in result.conditions.delivered_targets} == {html_id}
    assert {target.object_id for target in result.conditions.terminal_blocked_targets} == {
        format_object_id("report_B", "html")
    }
    assert {target.object_id for target in result.conditions.continuable_targets} == {
        format_object_id("report_C", "html")
    }
    assert all(target.fmt == "html" for target in result.conditions.target_matrix)
