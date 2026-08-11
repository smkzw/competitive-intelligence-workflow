from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ci_workflow.domain.evidence import SourceVersionRecord

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "synthetic" / "historical-cutoff"
CUTOFF = datetime.fromisoformat("2026-08-09T23:59:59.999999+08:00")


def _source(name: str) -> SourceVersionRecord:
    return SourceVersionRecord.model_validate_json(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


def test_acquired_after_cutoff_but_first_disclosed_before_cutoff_is_snapshot_eligible() -> None:  # noqa: E501
    from ci_workflow.sources.planner import (
        HistoricalCutoffState,
        assess_historical_source,
    )

    source = _source("acquired-after-disclosed-before.json")
    assert source.acquired_at > CUTOFF
    assessment = assess_historical_source(source, cutoff=CUTOFF, key_evidence=True)
    assert assessment.state is HistoricalCutoffState.SNAPSHOT_ELIGIBLE
    assert assessment.can_enter_snapshot is True
    assert assessment.refresh_candidate is False


def test_first_disclosed_after_cutoff_cannot_enter_snapshot_and_becomes_refresh_candidate() -> None:  # noqa: E501
    from ci_workflow.sources.planner import (
        HistoricalCutoffState,
        assess_historical_source,
    )

    source = _source("disclosed-after-cutoff.json")
    assessment = assess_historical_source(source, cutoff=CUTOFF, key_evidence=True)
    assert assessment.state is HistoricalCutoffState.REFRESH_CANDIDATE
    assert assessment.can_enter_snapshot is False
    assert assessment.refresh_candidate is True
    assert assessment.recovery_required is False


def test_unknown_first_disclosure_for_key_historical_evidence_fails_closed() -> None:
    from ci_workflow.sources.planner import (
        HistoricalCutoffState,
        assess_historical_source,
    )

    source = _source("unknown-first-disclosure.json")
    assessment = assess_historical_source(source, cutoff=CUTOFF, key_evidence=True)
    assert assessment.state is HistoricalCutoffState.BLOCKED_UNKNOWN_DISCLOSURE
    assert assessment.can_enter_snapshot is False
    assert assessment.refresh_candidate is False
    assert assessment.recovery_required is True
    assert "首次披露时间" in assessment.rationale_zh


def test_calendar_day_disclosure_is_blocked_inside_that_day_and_resolves_at_day_end() -> None:
    from ci_workflow.domain.evidence import DateEvidence
    from ci_workflow.sources.planner import (
        HistoricalCutoffState,
        assess_historical_source,
    )

    source = _source("acquired-after-disclosed-before.json")
    source = source.model_copy(
        update={
            "first_disclosed_at": DateEvidence(
                state="reported",
                value="2026-08-09T00:00:00+08:00",
                precision="calendar_day",
                locator=source.first_disclosed_at.locator,
            )
        }
    )

    ambiguous = assess_historical_source(
        source,
        cutoff=datetime.fromisoformat("2026-08-09T12:00:00+08:00"),
        key_evidence=True,
    )
    assert ambiguous.state is HistoricalCutoffState.BLOCKED_AMBIGUOUS_DISCLOSURE_DAY
    assert ambiguous.can_enter_snapshot is False
    assert ambiguous.recovery_required is True

    end_of_day = assess_historical_source(source, cutoff=CUTOFF, key_evidence=True)
    assert end_of_day.state is HistoricalCutoffState.SNAPSHOT_ELIGIBLE
    assert end_of_day.can_enter_snapshot is True
