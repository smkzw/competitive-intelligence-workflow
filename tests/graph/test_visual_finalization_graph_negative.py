from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.registry import TRANSITION_REGISTRY
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.graph.visual_finalization import visual_contract_digest
from tests.contract.test_visual_render_evidence import _evidence, _verdict

_NOW = datetime(2026, 8, 29, 9, 0, tzinfo=UTC)


def _passed_evidence(format_name: str = "html") -> dict[str, Any]:
    render_evidence = _evidence()
    visual_verdict = _verdict()
    render_digest = visual_contract_digest(render_evidence)
    visual_verdict["render_evidence_digest"] = render_digest
    verdict_digest = visual_contract_digest(visual_verdict)
    return {
        "deterministic_check_recorded": True,
        "coverage_check_recorded": True,
        "real_render_check_recorded": True,
        "visual_plan_bound": True,
        "candidate_current": True,
        "render_evidence_current": True,
        "current_run": True,
        "real_artifact": True,
        "real_render": True,
        "receipts_current": True,
        "independent_visual_review_recorded": True,
        "visual_verdict_accepted": True,
        "visual_verdict_current": True,
        "independent_visual_verifier": True,
        "render_evidence_validated": True,
        "visual_verdict_validated": True,
        "required_render_targets_complete": True,
        "required_interactions_complete": True,
        "visible_text_scan_passed": True,
        "responsive_content_complete": True,
        "beautification_loop_complete": True,
        "no_visual_defects_remain": True,
        "visual_copy_check_passed": True,
        "visual_hierarchy_check_passed": True,
        "visual_layout_check_passed": True,
        "visual_color_check_passed": True,
        "visual_chart_table_check_passed": True,
        "visual_interaction_check_passed": True,
        "visual_format_render_check_passed": True,
        "snapshot_id": "snapshot-1",
        "format": format_name,
        "candidate_format": format_name,
        "visual_plan_digest": "a" * 64,
        "artifact_id": "artifact-1",
        "candidate_artifact_digest": "b" * 64,
        "candidate_snapshot_id": "snapshot-1",
        "candidate_visual_plan_digest": "a" * 64,
        "render_evidence_id": "render-1",
        "render_evidence_digest": render_digest,
        "rendered_artifact_digest": "b" * 64,
        "beautification_round": 1,
        "rendered_format": format_name,
        "beautification_record_digest": "d" * 64,
        "visual_verdict_id": "verdict-1",
        "visual_verdict_format": format_name,
        "visual_verdict_digest": verdict_digest,
        "visual_verdict_artifact_digest": "b" * 64,
        "visual_verdict_render_digest": render_digest,
        "visual_verdict_plan_digest": "a" * 64,
        "producer_identity": visual_verdict["producer_identity"],
        "verifier_identity": visual_verdict["verifier_identity"],
        "open_blocking_visual_defects": 0,
        "render_evidence": render_evidence,
        "visual_verdict": visual_verdict,
    }


def test_format_quality_check_rejects_flat_boolean_bag_without_typed_records() -> None:
    evidence = _passed_evidence()
    del evidence["render_evidence"]
    del evidence["visual_verdict"]
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        evidence,
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason.startswith("missing_evidence:render_evidence")

def _delivery_evidence() -> dict[str, Any]:
    evidence = _passed_evidence()
    evidence.update(
        atomic_publish_complete=True,
        manifest_digest_recorded=True,
        independent_visual_verdict_accepted=True,
    )
    return evidence


def _queued_generation_evidence(format_name: str = "html") -> dict[str, Any]:
    return {
        "report_snapshot_locked": True,
        "visual_plan_bound": True,
        "visual_plan_snapshot_matches": True,
        "visual_plan_format_matches": True,
        "visual_plan_design_contract_matches": True,
        "snapshot_id": "snapshot-1",
        "format": format_name,
        "visual_plan_id": "plan-1",
        "visual_plan_digest": "a" * 64,
        "visual_plan_snapshot_id": "snapshot-1",
        "visual_plan_format": format_name,
        "design_contract_digest": "b" * 64,
    }


def _candidate_evidence(format_name: str = "html") -> dict[str, Any]:
    return {
        "visual_plan_bound": True,
        "artifact_built": True,
        "candidate_current": True,
        "candidate_snapshot_matches": True,
        "candidate_visual_plan_matches": True,
        "snapshot_id": "snapshot-1",
        "format": format_name,
        "visual_plan_digest": "a" * 64,
        "artifact_id": "artifact-1",
        "candidate_artifact_digest": "b" * 64,
        "candidate_snapshot_id": "snapshot-1",
        "candidate_visual_plan_digest": "a" * 64,
        "candidate_format": format_name,
    }


def _beautification_evidence(format_name: str = "html") -> dict[str, Any]:
    return {
        "visual_plan_bound": True,
        "candidate_current": True,
        "real_render_check_recorded": True,
        "render_evidence_current": True,
        "beautification_round_available": True,
        "beautification_retest_recorded": True,
        "visual_defects_remain": True,
        "snapshot_id": "snapshot-1",
        "format": format_name,
        "rendered_format": format_name,
        "visual_plan_digest": "a" * 64,
        "candidate_artifact_digest": "b" * 64,
        "candidate_snapshot_id": "snapshot-1",
        "candidate_visual_plan_digest": "a" * 64,
        "candidate_format": format_name,
        "render_evidence_id": "render-1",
        "render_evidence_digest": "c" * 64,
        "rendered_artifact_digest": "b" * 64,
        "beautification_round": 1,
        "beautification_record_id": "beautification-1",
        "beautification_record_digest": "d" * 64,
    }




def test_format_quality_check_rejects_a_render_only_shortcut() -> None:
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        {"real_render_check_recorded": True},
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason.startswith("missing_evidence:")


def test_format_quality_check_accepts_complete_current_visual_evidence() -> None:
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        _passed_evidence(),
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is True


def test_format_quality_check_rejects_non_boolean_acceptance_shortcuts() -> None:
    evidence = _passed_evidence()
    evidence["real_render_check_recorded"] = "yes"
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        evidence,
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason.startswith("guard_not_satisfied:real_render_check_recorded")


def test_format_guard_rejects_evidence_from_another_family_or_object() -> None:
    evidence = _passed_evidence()
    wrong_family = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        {**evidence, "target_family": "report_evidence"},
        target_family="format_artifact",
        target_object_id="report_A:html",
    )
    wrong_object = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        {**evidence, "target_object_id": "report_B:html"},
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert wrong_family.allowed is False
    assert wrong_family.reason == "scope_mismatch:target_family:report_evidence"
    assert wrong_object.allowed is False
    assert wrong_object.reason == "scope_mismatch:target_object_id:report_B:html"


def test_format_generation_rejects_plan_binding_drift() -> None:
    for field, value in (
        ("visual_plan_snapshot_id", "snapshot-other"),
        ("visual_plan_format", "pdf"),
    ):
        evidence = _queued_generation_evidence()
        evidence[field] = value
        result = TRANSITION_REGISTRY.evaluate_guard(
            "g_format_queued_generating",
            evidence,
            target_family="format_artifact",
            target_object_id="report_A:html",
        )
        assert result.allowed is False
        assert result.reason.startswith("guard_not_satisfied:")


def test_format_candidate_rejects_snapshot_plan_or_format_drift() -> None:
    for field, value in (
        ("candidate_snapshot_id", "snapshot-other"),
        ("candidate_visual_plan_digest", "c" * 64),
        ("candidate_format", "pdf"),
    ):
        evidence = _candidate_evidence()
        evidence[field] = value
        result = TRANSITION_REGISTRY.evaluate_guard(
            "g_format_generating_quality_check",
            evidence,
            target_family="format_artifact",
            target_object_id="report_A:html",
        )
        assert result.allowed is False
        assert result.reason.startswith("guard_not_satisfied:")


def test_format_beautification_loop_rejects_rounds_outside_one_to_three() -> None:
    for round_number in (0, 4):
        evidence = _beautification_evidence()
        evidence["beautification_round"] = round_number
        result = TRANSITION_REGISTRY.evaluate_guard(
            "g_format_quality_check_generating",
            evidence,
            target_family="format_artifact",
            target_object_id="report_A:html",
        )
        assert result.allowed is False
        assert result.reason == "guard_not_satisfied:beautification_round"


def test_format_acceptance_rejects_self_signed_visual_verdict() -> None:
    evidence = _passed_evidence()
    evidence["verifier_identity"] = evidence["producer_identity"]
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        evidence,
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason == "guard_not_satisfied:producer_identity!=verifier_identity"


def test_format_acceptance_rejects_zero_beautification_round() -> None:
    evidence = _passed_evidence()
    evidence["beautification_round"] = 0
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        evidence,
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason == "guard_not_satisfied:beautification_round"


def test_format_blocking_accepts_either_visual_limit_or_non_visual_failure() -> None:
    common = {
        "format_recovery_exhausted": True,
        "failure_evidence_saved": True,
    }
    for reason in ("beautification_round_limit_reached", "non_visual_failure_recorded"):
        result = TRANSITION_REGISTRY.evaluate_guard(
            "g_format_quality_check_blocked",
            {**common, reason: True},
            target_family="format_artifact",
            target_object_id="report_A:html",
        )
        assert result.allowed is True


def test_format_acceptance_rejects_visual_verdict_digest_drift() -> None:
    evidence = _passed_evidence()
    evidence["visual_verdict_artifact_digest"] = "c" * 64
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_passed",
        evidence,
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason == (
        "guard_not_satisfied:visual_verdict_artifact_digest==candidate_artifact_digest"
    )


def test_format_visual_block_requires_three_rounds_or_non_visual_failure() -> None:
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_quality_check_blocked",
        {"format_recovery_exhausted": True, "failure_evidence_saved": True},
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason.startswith("missing_evidence:beautification_round_limit_reached")


def test_format_delivery_requires_a_current_visual_verdict() -> None:
    result = TRANSITION_REGISTRY.evaluate_guard(
        "g_format_passed_delivery_ready",
        {
            "atomic_publish_complete": True,
            "manifest_digest_recorded": True,
            "artifact_id": "artifact-1",
            "candidate_artifact_digest": "b" * 64,
        },
        target_family="format_artifact",
        target_object_id="report_A:html",
    )

    assert result.allowed is False
    assert result.reason.startswith("missing_evidence:visual_verdict_id")


def test_format_delivery_rejects_stale_visual_verification_plan_or_render_binding() -> None:
    allowed: list[bool] = []
    for top_level_field, verdict_field in (
        ("visual_verdict_plan_digest", "visual_plan_digest"),
        ("visual_verdict_render_digest", "render_evidence_digest"),
    ):
        evidence = _passed_evidence()
        evidence.update(
            atomic_publish_complete=True,
            manifest_digest_recorded=True,
            independent_visual_verdict_accepted=True,
        )
        stale_digest = "c" * 64
        evidence[top_level_field] = stale_digest
        evidence["visual_verdict"][verdict_field] = stale_digest
        evidence["visual_verdict_digest"] = visual_contract_digest(
            evidence["visual_verdict"]
        )
        result = TRANSITION_REGISTRY.evaluate_guard(
            "g_format_passed_delivery_ready",
            evidence,
            target_family="format_artifact",
            target_object_id="report_A:html",
        )

        allowed.append(result.allowed)
    assert allowed == [False, False]

def _request(
    *,
    request_id: str,
    object_id: str,
    from_state: str,
    to_state: str,
    trigger: str,
    evidence: dict[str, Any],
    run_id: str = "run_visual_negative",
) -> TransitionRequest:
    return TransitionRequest(
        schema_version="1.0",
        request_id=request_id,
        project_id="project_visual_negative",
        run_id=run_id,
        family="format_artifact",
        object_id=object_id,
        from_state=from_state,
        to_state=to_state,
        trigger=trigger,
        evidence=evidence,
        actor_id="visual-test",
        occurred_at=_NOW,
    )


def test_format_graph_rejects_a_queued_to_delivery_ready_jump(tmp_path: Path) -> None:
    executor = GraphExecutor(tmp_path / "project", run_id="run_visual_negative")

    event = executor.submit(
        _request(
            request_id="jump",
            object_id="report_A:html",
            from_state="queued",
            to_state="delivery_ready",
            trigger="atomic_publish_manifest",
            evidence={"atomic_publish_complete": True, "manifest_digest_recorded": True},
        )
    )

    assert event.event_type == "graph.transition.rejected"
    assert event.payload["reason"] == "undeclared_transition"
    assert executor.state()["format_artifact"] == {}


def test_format_graph_cannot_pass_without_current_render_evidence(tmp_path: Path) -> None:
    executor = GraphExecutor(tmp_path / "project", run_id="run_visual_negative")
    object_id = "report_A:html"

    generating = executor.submit(
        _request(
            request_id="generating",
            object_id=object_id,
            from_state="queued",
            to_state="generating",
            trigger="snapshot_locked_ready",
            evidence=_queued_generation_evidence(),
        )
    )
    quality_check = executor.submit(
        _request(
            request_id="quality-check",
            object_id=object_id,
            from_state="generating",
            to_state="quality_check",
            trigger="artifact_built",
            evidence=_candidate_evidence(),
        )
    )
    acceptance_evidence = _passed_evidence()
    del acceptance_evidence["real_render_check_recorded"]
    passed = executor.submit(
        _request(
            request_id="missing-render",
            object_id=object_id,
            from_state="quality_check",
            to_state="passed",
            trigger="acceptance_records_complete",
            evidence=acceptance_evidence,
        )
    )

    assert generating.event_type == "graph.transition.accepted"
    assert quality_check.event_type == "graph.transition.accepted"
    assert passed.event_type == "graph.transition.rejected"
    assert passed.payload["reason"] == "guard_failed"
    assert passed.payload["guard_reason"].startswith(
        "missing_evidence:real_render_check_recorded"
    )
    assert executor.state()["format_artifact"][object_id] == "quality_check"
