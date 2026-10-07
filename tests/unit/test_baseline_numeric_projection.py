"""Baseline descriptive frames preserve raw units and statistical objects."""

import pytest

from ci_workflow.reports.common.numeric_projection import (
    NumericMeasureKind as Kind,
)
from ci_workflow.reports.common.numeric_projection import (
    infer_numeric_kind,
    project_numeric,
)


@pytest.mark.parametrize("stat", ["MEAN", "MEDIAN", "STANDARD_DEVIATION"])
def test_age_statistics_are_continuous_not_participant_counts(stat) -> None:
    assert infer_numeric_kind(statistic_form=stat, unit="Years", domain="baseline") is (
        Kind.CONTINUOUS_MEASURE
    )


def test_year_case_is_only_a_display_unit_normalization() -> None:
    lower = project_numeric(value=51, unit="years", kind=Kind.CONTINUOUS_MEASURE)
    upper = project_numeric(value=51, unit="Years", kind=Kind.CONTINUOUS_MEASURE)
    assert lower.plot_unit == upper.plot_unit == "years"
    assert upper.raw_unit == "Years"
    assert project_numeric(value=2, unit="Mg", kind=Kind.CONTINUOUS_MEASURE).plot_unit == "Mg"


@pytest.mark.parametrize(("stat", "unit", "expected"), [
    ("COUNT_OF_PARTICIPANTS", "Participants", Kind.PARTICIPANT_COUNT),
    ("NUMBER", "Participants", Kind.PARTICIPANT_COUNT),
    ("MEAN", "", Kind.PARTICIPANT_COUNT),
    ("NUMBER", "Years", Kind.PARTICIPANT_COUNT),
    ("MEAN", "%", Kind.PARTICIPANT_COUNT),
    ("LS MEAN", "Years", Kind.ADJUSTED_ESTIMATE),
    ("MEAN", "Percentage of participants", Kind.PARTICIPANT_PROPORTION),
])
def test_explicit_types_and_unknown_number_are_not_reinterpreted(stat, unit, expected) -> None:
    assert infer_numeric_kind(statistic_form=stat, unit=unit, domain="baseline") is expected
