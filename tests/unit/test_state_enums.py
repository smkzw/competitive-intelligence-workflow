from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_task_1_1_freezes_all_nine_state_families_without_interchangeability() -> None:
    assert (ROOT / "src/ci_workflow/domain/enums.py").is_file()
    from ci_workflow.domain.enums import (
        DownloadRequestState,
        FactDisclosureState,
        FactReviewState,
        FormatArtifactState,
        ProjectRunState,
        ReportEvidenceState,
        RevisionApprovalState,
        RouteAttemptResult,
        RouteCompletion,
    )

    expected = {
        RouteAttemptResult: {
            "success_with_evidence",
            "success_irrelevant_only",
            "searched_no_evidence",
            "not_publicly_disclosed",
            "access_or_permission_blocked",
            "transient_network_failure",
            "rate_limited",
            "anti_bot_or_captcha",
            "source_unavailable",
            "parser_or_schema_failure",
            "tool_capability_gap",
            "content_truncated",
        },
        RouteCompletion: {"completed", "not_applicable", "access_blocked"},
        FactDisclosureState: {
            "reported_value",
            "reported_zero",
            "not_reported",
            "below_reporting_threshold",
            "not_publicly_disclosed",
            "not_applicable",
            "conflicting",
            "unresolved_due_to_route",
        },
        FactReviewState: {"candidate", "accepted", "rejected", "superseded", "user_modified"},
        ProjectRunState: {
            "running",
            "awaiting_user",
            "partially_delivered",
            "partial_delivery_blocked",
            "blocked",
            "complete",
        },
        ReportEvidenceState: {
            "queued",
            "collecting",
            "recovering",
            "awaiting_user",
            "scientific_qc",
            "snapshot_locked",
            "evidence_blocked",
            "superseded",
        },
        FormatArtifactState: {
            "queued",
            "generating",
            "quality_check",
            "passed",
            "delivery_ready",
            "blocked",
            "superseded",
        },
        DownloadRequestState: {
            "awaiting_user",
            "file_detected",
            "matched",
            "accepted",
            "needs_re_download",
            "not_required",
        },
        RevisionApprovalState: {
            "submitted",
            "needs_evidence",
            "rejected",
            "validated_pending_user_approval",
            "approved",
            "published",
        },
    }
    for state_type, values in expected.items():
        assert {item.value for item in state_type} == values

    assert type(ProjectRunState.AWAITING_USER) is not type(ReportEvidenceState.AWAITING_USER)
    with pytest.raises(ValueError):
        FactDisclosureState("")
    with pytest.raises(ValueError):
        FactDisclosureState(0)
    with pytest.raises(ValueError):
        FactDisclosureState(None)
    with pytest.raises(ValueError):
        FactDisclosureState(RouteAttemptResult.TRANSIENT_NETWORK_FAILURE)
    state_types = (
        RouteAttemptResult,
        RouteCompletion,
        FactDisclosureState,
        FactReviewState,
        ProjectRunState,
        ReportEvidenceState,
        FormatArtifactState,
        DownloadRequestState,
        RevisionApprovalState,
    )
    shared_value_probes = 0
    for target_type in state_types:
        target_values = {item.value for item in target_type}
        for foreign_type in state_types:
            if foreign_type is target_type:
                continue
            for foreign_member in foreign_type:
                if foreign_member.value in target_values:
                    shared_value_probes += 1
                    with pytest.raises(ValueError):
                        target_type(foreign_member)
    assert shared_value_probes >= 20
