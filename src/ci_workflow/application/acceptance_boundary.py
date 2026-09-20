"""Fail-closed origin-state gate for scientific, visual, and release acceptance."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class AcceptanceBoundaryError(ValueError):
    """The current run is not eligible to produce an accepted successor."""


ACCEPTED_ORIGIN_REPORT_STATES = frozenset(
    {"scientifically_reviewed_rendered_candidate", "snapshot_locked"}
)
PREVIEW_ONLY_REPORT_STATES = frozenset(
    {"rendered_unreviewed", "recovery_required", "evidence_blocked"}
)


def require_accepted_origin_report_states(
    run_manifest: Mapping[str, Any], *, reports: Sequence[str]
) -> dict[str, str]:
    """Require every requested report to have a scientifically accepted origin."""
    states = run_manifest.get("report_states")
    if not isinstance(states, Mapping):
        raise AcceptanceBoundaryError(
            "当前运行清单缺少有效的 report_states，无法证明科学来源"
        )
    verified: dict[str, str] = {}
    for report in reports:
        state = states.get(report)
        if not isinstance(state, str) or state not in ACCEPTED_ORIGIN_REPORT_STATES:
            raise AcceptanceBoundaryError(
                f"report_states[{report}]={state!r} 仅可作为开发预览，"
                "不得产生科学、视觉或发布接受后继"
            )
        verified[report] = state
    return verified
