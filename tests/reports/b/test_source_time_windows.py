"""A collection interval must not become a baseline or midpoint visit label."""

import pytest

from ci_workflow.renderers.portal.report_a import _native_timepoint_zh
from ci_workflow.renderers.portal.report_b import _time_band


@pytest.mark.parametrize(
    "source,expected",
    [
        (
            "From baseline (after first dose) to end of study (1 year).",
            "基线（首次给药后）至研究结束（1年）",
        ),
        ("From baseline to Week 26", "基线至第26周"),
        ("Baseline through Week 52", "基线至第52周"),
    ],
)
def test_baseline_anchored_interval_is_not_a_baseline_visit(source: str, expected: str) -> None:
    key, label = _time_band(source)
    assert key != "baseline"
    assert label == expected
    assert key != _time_band("Baseline")[0]


@pytest.mark.parametrize("source", ["4-16 weeks", "0-26 weeks", "48-56 weeks"])
def test_numeric_interval_is_not_a_midpoint_visit(source: str) -> None:
    key, label = _time_band(source)
    low, high = source.split()[0].split("-")
    assert key == f"week_{low}-{high}"
    assert label == f"第{low}–{high}周"


def test_single_visits_keep_approved_nearby_time_band() -> None:
    assert _time_band("Baseline")[0] == "baseline"
    assert _time_band("48 weeks")[0] == _time_band("50 weeks")[0] == "around_year_1"


def test_different_anchored_intervals_do_not_share_one_baseline_frame() -> None:
    assert _time_band("From baseline to Week 26")[0] != _time_band("Baseline through Week 52")[0]


@pytest.mark.parametrize("end_day,duration", [(30, 563), (90, 700)])
def test_first_to_last_dose_interval_retains_its_end_anchor(end_day: int, duration: int) -> None:
    source = (
        f"From first dose of study drug (Day 1) up to {end_day} days after "
        f"the last dose of study drug, up to approximately {duration} days."
    )
    assert _native_timepoint_zh(source) == (
        f"自首次给药（第1天）至末次给药后{end_day}天（最长约{duration}天）"
    )
    assert "末次给药后" in _time_band(source)[1]
