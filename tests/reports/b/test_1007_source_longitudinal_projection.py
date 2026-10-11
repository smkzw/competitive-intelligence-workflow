"""Source-instance trajectories are real lines, not cross-trial equivalence."""

import copy

import pytest

from ci_workflow.renderers.portal import report_b
from tests.reports.b.test_r13_semantic_grouping import _project_efficacy


def _observations():
    rows = []
    for week in (24, 1, 4, 12, 16):
        row = _project_efficacy(f"week-{week}", "WI-NRS", timepoint=f"Week {week}")
        row.update(
            group_id="OG001", arm_role="unknown", source_version_id="source-v1",
            source_measure_path="resultsSection.outcomeMeasuresModule.outcomeMeasures[15]",
            source_measure_definition="同一登记测量实例的WI-NRS改善至少4分比例",
            source_param_type="NUMBER", source_analysis_population="ITT",
            source_value_role="reported_measure", source_class_title=f"Week {week}",
            source_category_title="", actual_timepoint_unit="",
            source_clause_context={"scientific_scope": {
                "source_version_id": "source-v1",
                "source_measure_path": "resultsSection.outcomeMeasuresModule.outcomeMeasures[15]",
            }},
        )
        rows.append((row, None))
    return rows


def test_source_measure_trajectory_keeps_unknown_arm_role_and_actual_visits() -> None:
    records = _observations()
    before = copy.deepcopy(records)
    groups = report_b._source_longitudinal_groups(records)
    assert len(groups) == 1
    group = groups[0]
    assert group["comparison_purpose"] == "within_source_measure_time_axis"
    assert group["cross_trial"] is False
    assert [row["_plot_time_value"] for row in group["rows"]] == [1, 4, 12, 16, 24]
    assert all(row["_plot_time_unit"] == "week" and row["_chart_type"] == "line"
               for row in group["rows"])
    assert set(row["row_id"] for row in group["rows"]) == {
        row["row_id"] for row, _ in records
    }
    assert records == before


def test_source_line_uses_complete_short_heading_and_shared_display_unit() -> None:
    records = _observations()
    for row, _ in records:
        row.update(unit="percentage of participants",
                   display_label_zh="Percentage of Participants at Weeks 1 through 24")
    before = copy.deepcopy(records)
    group = report_b._source_longitudinal_groups(records)[0]
    assert group["title_complete"] is True
    assert group["y_axis_label_zh"] == "受试者百分比"
    assert all(row["unit"] == "percentage of participants" for row in group["rows"])
    assert records == before


@pytest.mark.parametrize("field,value", (
    ("source_version_id", "source-v2"), ("source_measure_path", "other-measure"),
    ("source_analysis_population", "PP"), ("semantic_estimand", "hypothetical"),
    ("unit", "points"), ("source_param_type", "LEAST_SQUARES_MEAN"),
    ("source_category_title", "Female"), ("period", "extension"),
    ("cohort", "cohort-b"), ("source_value_role", "adjusted_estimate"),
))
def test_conflicting_context_is_not_inserted_into_source_trajectory(field, value) -> None:
    records = _observations()
    records[0][0][field] = value
    groups = report_b._source_longitudinal_groups(records)
    assert len(groups) == 1
    assert "week-24" not in {row["row_id"] for row in groups[0]["rows"]}


@pytest.mark.parametrize("kind", ("duplicate", "wrong-scope", "ambiguous-time", "no-group"))
def test_unqualified_or_duplicate_visits_stay_out_without_dropping_source_rows(kind) -> None:
    records = _observations()
    if kind == "duplicate":
        records.append((dict(records[0][0], row_id="other-at-24", value=62), None))
    elif kind == "wrong-scope":
        for row, _ in records:
            row["source_clause_context"]["scientific_scope"]["source_measure_path"] = "wrong"
    elif kind == "ambiguous-time":
        for row, _ in records:
            row["actual_timepoint"] = "Baseline, Week 24"
    else:
        for row, _ in records:
            row["group_id"] = ""
    before = copy.deepcopy(records)
    assert report_b._source_longitudinal_groups(records) == ()
    assert records == before


def test_zero_and_current_clear_remain_same_table_and_gap_identity() -> None:
    records = _observations()
    records[1][0].update(value=0, numeric_value=0)
    records[2][0].update(value=None, numeric_value=None, renderable=False,
                         disclosure_state="user_cleared")
    groups = report_b._source_longitudinal_groups(records)
    by_id = {row["row_id"]: row for row in groups[0]["rows"]}
    assert by_id["week-1"]["numeric_value"] == 0
    assert by_id["week-4"]["numeric_value"] is None
    assert by_id["week-4"]["disclosure_state"] == "user_cleared"


def test_normal_longitudinal_page_consumes_the_same_source_curve() -> None:
    records = _observations()
    groups = report_b._groups_for_page("longitudinal-results", records)
    assert len(groups) == 1
    assert groups[0]["comparison_purpose"] == "within_source_measure_time_axis"
    assert len(groups[0]["rows"]) == 5


def test_comparison_workspace_exposes_qualified_lines_without_changing_science_facets() -> None:
    records = _observations()
    science = report_b._groups_for_page("efficacy", records)
    before = copy.deepcopy(science)
    workspace = report_b._comparison_workspace(records, science, ("trial-a",))
    assert len(workspace["longitudinal_groups"]) == 1
    assert set(workspace["membership"]["row_ids"]) == {
        row["row_id"] for row in workspace["longitudinal_groups"][0]["rows"]
    }
    assert science == before
