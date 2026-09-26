"""R24 source semantics: production parser, synthetic registry records only.

The reviewed ZIP contains starting probes, not an executed product receipt.
These tests exercise the actual parser and assert source-count preservation even
when a denominator cannot support a percentage projection.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from ci_workflow.application.source_research_service import (
    _iter_adverse_event_results,
    _iter_outcome_results,
    _outcome_category,
    _outcome_report_term,
    classify_source_outcome,
)
from ci_workflow.reports.b.safety_concepts import describe_safety_concept


def _record(
    observations: list[tuple[str, str]],
    denominators: list[tuple[str, str, str]],
    *,
    title: str = "Number of Participants With Clinical Response",
) -> dict[str, Any]:
    groups = sorted({group_id for group_id, _ in observations})
    return {"resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{
        "title": title,
        "timeFrame": "Week 24",
        "unitOfMeasure": "Participants",
        "paramType": "COUNT_OF_PARTICIPANTS",
        "groups": [{"id": group_id, "title": group_id} for group_id in groups],
        "denoms": [{"units": units, "counts": [{"groupId": group_id, "value": value}]}
                   for group_id, value, units in denominators],
        "classes": [{"categories": [{"measurements": [
            {"groupId": group_id, "value": value}
            for group_id, value in observations
        ]}]}],
    }]}}}


def _parse(payload: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    issues: list[Any] = []
    results = _iter_outcome_results(
        record=deepcopy(payload), trial_id="NCT00000000",
        source_id="synthetic-r24", issues=issues,
    )
    return results, issues


@pytest.mark.parametrize(("title", "class_title", "expected"), [
    ("Non-serious adverse events", "", "common_ae"),
    ("Participants without SAEs", "", "common_ae"),
    ("Adverse Events", "Non-serious adverse events", "common_ae"),
    ("Adverse Events", "Adverse events", "common_ae"),
    ("Serious adverse events", "", "sae"),
    ("Treatment-emergent adverse events", "", "teae"),
])
def test_outcome_category_does_not_invent_seriousness_or_emergence(
    title: str, class_title: str, expected: str,
) -> None:
    assert _outcome_category(title, class_title) == expected


def test_major_adverse_vascular_event_rate_is_not_generic_treatment_ae() -> None:
    title = "Adjusted Annualized Major Adverse Vascular Events Rate in the Core Treatment Period"
    assert describe_safety_concept(title).key == "unknown"
    assert _outcome_category(title) == "outcome"
    assert classify_source_outcome(title) == "efficacy"


def test_conflicting_denominators_keep_count_and_are_order_independent() -> None:
    denoms = [("OG1", "100", "Participants"), ("OG1", "40", "Participants")]
    observations = [("OG1", "20")]
    for candidates in (denoms, list(reversed(denoms))):
        results, issues = _parse(_record(observations, candidates))
        assert len(results) == 1
        assert results[0].numerator == 20
        assert results[0].denominator is None
        assert (results[0].value, results[0].unit) == (20, "人")
        assert any(issue.status == "conflicting" and ".denoms" in issue.source_path
                   for issue in issues)


def test_equal_denominator_with_different_statistical_units_is_not_merged() -> None:
    results, issues = _parse(_record(
        [("OG1", "20")],
        [("OG1", "100", "Participants"), ("OG1", "100", "Events")],
    ))
    assert len(results) == 1 and results[0].denominator is None
    assert any(issue.status == "conflicting" for issue in issues)


def test_missing_denominator_does_not_drop_later_group_or_reported_count() -> None:
    observations = [("OG1", "10"), ("OG2", "20")]
    for values in (observations, list(reversed(observations))):
        results, issues = _parse(_record(values, [("OG2", "100", "Participants")]))
        by_group = {item.group_id: item for item in results}
        assert set(by_group) == {"OG1", "OG2"}
        assert (by_group["OG1"].value, by_group["OG1"].unit,
                by_group["OG1"].denominator) == (10, "人", None)
        assert by_group["OG2"].numerator == 20
        assert by_group["OG2"].denominator == 100
        assert any(issue.status == "missing" and "OG1" in issue.reason_zh
                   for issue in issues)


def test_explicit_zero_over_zero_retains_count_without_a_zero_rate() -> None:
    results, issues = _parse(_record(
        [("OG1", "0"), ("OG2", "2")],
        [("OG1", "0", "Participants"), ("OG2", "10", "Participants")],
    ))
    by_group = {item.group_id: item for item in results}
    assert by_group["OG1"].numerator == 0
    assert by_group["OG1"].value == 0
    assert by_group["OG1"].unit == "人"
    assert by_group["OG2"].denominator == 10
    assert any("0/0" in issue.reason_zh for issue in issues)


def test_n_greater_than_n_records_conflict_without_dropping_other_group() -> None:
    results, issues = _parse(_record(
        [("OG1", "11"), ("OG2", "2")],
        [("OG1", "10", "Participants"), ("OG2", "10", "Participants")],
    ))
    by_group = {item.group_id: item for item in results}
    assert by_group["OG1"].numerator == 11
    assert by_group["OG1"].denominator is None
    assert by_group["OG2"].denominator == 10
    assert any(issue.status == "conflicting" for issue in issues)


def test_specific_serious_event_subset_is_not_labeled_any_sae() -> None:
    title = "Serious adverse events leading to hospitalization"
    assert _outcome_report_term("sae", title, "") == title


def test_ae_event_groups_preserve_zero_and_missing_denominator_counts() -> None:
    record = {"resultsSection": {"adverseEventsModule": {
        "timeFrame": "Week 28",
        "eventGroups": [
            {"id": "EG1", "title": "Drug", "seriousNumAffected": 0,
             "seriousNumAtRisk": 0},
            {"id": "EG2", "title": "Control", "seriousNumAffected": 2,
             "seriousNumAtRisk": 10},
            {"id": "EG3", "title": "Other", "seriousNumAffected": 3},
        ],
    }}}
    issues: list[Any] = []
    results = _iter_adverse_event_results(
        record=record, trial_id="NCT00000000", source_id="r24-ae", issues=issues,
    )
    by_group = {item.group_id: item for item in results if item.category == "sae"}
    assert set(by_group) == {"EG1", "EG2", "EG3"}
    assert (by_group["EG1"].numerator, by_group["EG1"].denominator,
            by_group["EG1"].value, by_group["EG1"].unit) == (0, 0, 0, "人")
    assert by_group["EG2"].value == 20
    assert (by_group["EG3"].numerator, by_group["EG3"].denominator,
            by_group["EG3"].value) == (3, None, 3)
    assert any(item.status == "missing" and "0/0" in item.reason_zh for item in issues)
    assert any(item.status == "missing" and "EG3" in item.reason_zh for item in issues)


def test_death_event_group_missing_is_unknown_and_explicit_zero_is_not_a_rate() -> None:
    record = {"resultsSection": {"adverseEventsModule": {
        "timeFrame": "Week 48",
        "eventGroups": [
            {"id": "EG1", "title": "Unknown", "deathsNumAtRisk": 40},
            {"id": "EG2", "title": "Zero denominator", "deathsNumAffected": 0,
             "deathsNumAtRisk": 0},
        ],
    }}}
    issues: list[Any] = []
    results = _iter_adverse_event_results(
        record=record, trial_id="NCT00000000", source_id="r24-death", issues=issues,
    )
    death_rows = [row for row in results if row.category == "death"]
    assert len(death_rows) == 1 and death_rows[0].group_id == "EG2"
    assert (death_rows[0].numerator, death_rows[0].denominator,
            death_rows[0].value, death_rows[0].unit) == (0, 0, 0, "人")
    assert any(item.category == "death" and "未知" in item.reason_zh for item in issues)
    assert any(item.category == "death" and "0/0" in item.reason_zh for item in issues)
