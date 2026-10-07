"""The ordinary B adapter must expose study rows and shared semantic columns."""

import json

import pytest

from ci_workflow.renderers.portal import report_b
from tests.reports.b.test_r13_semantic_grouping import _project_efficacy


def _records():
    first = _project_efficacy("first", "EASI-75", timepoint=48)
    first.update(semantic_direction="higher_is_better", semantic_estimand="treatment_policy",
                 semantic_denominator="full_analysis_set", semantic_instrument_or_scale="EASI v1.0")
    second = dict(first, row_id="second", product_id="product-b", trial_id="trial-b",
                  actual_timepoint=50)
    unknown = dict(first, row_id="unknown", trial_id="trial-c", value=None,
                   renderable=False, disclosure_state="user_cleared", reason="用户清除，待重新核实",
                   semantic_definition="unknown")
    return ((first, None), (second, None), (unknown, None))


def test_shared_column_and_unresolved_study_both_remain_in_workspace() -> None:
    records = _records()
    groups = report_b._groups_for_page("efficacy", records)
    workspace = report_b._comparison_workspace(
        records, groups, ("trial-a", "trial-b", "trial-c", "trial-no-results"),
    )
    assert set(workspace["membership"]["row_ids"]) == {"first", "second", "unknown"}
    assert set(workspace["study_ids"]) == {"trial-a", "trial-b", "trial-c", "trial-no-results"}
    assert any(set(column["row_ids"]) == {"first", "second"} for column in workspace["columns"])
    assert set(workspace["numeric_eligibility"]["drawable_row_ids"]) == {"first", "second"}
    reasons = workspace["numeric_eligibility"]["undrawable_reasons"]
    assert reasons["unknown"] == "用户清除，待重新核实"
    assert "None" not in json.dumps(workspace, ensure_ascii=False)
    assert "不代表时间点相同" in json.dumps(workspace, ensure_ascii=False)


def test_duplicate_or_missing_scientific_facet_is_not_silently_dropped() -> None:
    records = _records()
    groups = report_b._groups_for_page("efficacy", records)
    with pytest.raises(ValueError):
        report_b._comparison_workspace(records, (*groups, groups[0]), ())
    with pytest.raises(ValueError):
        report_b._comparison_workspace(records, groups[:1], ())


def test_empty_module_placeholders_are_not_scientific_workspace_members() -> None:
    placeholder = {"row_id": "placeholder", "_synthetic": True, "_empty_state": True}
    workspace = report_b._comparison_workspace(((placeholder, None),), (), ("trial-empty",))
    assert workspace["membership"]["row_ids"] == []
    assert workspace["columns"] == ()
    assert workspace["study_ids"] == ("trial-empty",)


def test_source_domain_mismatch_stays_visible_but_not_in_efficacy_numeric_frame() -> None:
    first, second, _ = _records()
    second[0]["source_domain"] = "immunogenicity"
    groups = report_b._groups_for_page("efficacy", (first, second))
    workspace = report_b._comparison_workspace((first, second), groups, ())
    assert set(workspace["membership"]["row_ids"]) == {"first", "second"}
    assert "second" not in workspace["numeric_eligibility"]["drawable_row_ids"]
    assert "来源领域" in workspace["numeric_eligibility"]["undrawable_reasons"]["second"]


@pytest.mark.parametrize("change", [
    {"trial_id": "another-trial"}, {"group_id": "another-arm"},
    {"semantic_definition": "未知"}, {"source_domain": "immunogenicity"},
    {"arm_role": "control"}, {"arm_role": "unknown"},
])
def test_descriptive_time_axis_never_borrows_other_trial_arm_or_unknown_definition(change) -> None:
    first = _records()[0][0]
    first["group_id"] = "treatment-arm"
    second = dict(first, row_id="later", actual_timepoint=52, **change)
    groups = report_b._groups_for_page("longitudinal-results", ((first, None), (second, None)))
    assert len(groups) == 2
    assert all(group["cross_trial"] is False for group in groups)
    assert all(group["comparison_purpose"] == "within_trial_descriptive_time_axis"
               for group in groups)


def test_detail_retains_frame_identity_but_describes_only_visible_times() -> None:
    records = _records()[:2]
    groups = report_b._groups_for_page("efficacy", records)
    assert len(groups) == 1
    projected = report_b._project_scientific_groups(groups, records[:1])
    assert projected[0]["scientific_group_id"] == groups[0]["scientific_group_id"]
    assert projected[0]["actual_times"] == ("48 周",)
    assert projected[0]["frame_actual_times"] == ("48 周", "50 周")
    assert "实际观察时间：48 周 / 50 周" not in projected[0]["title_zh"]
    assert "原比较框" in projected[0]["time_window_note_zh"]


@pytest.mark.parametrize("metric", ["ada_positive", "anti-drug antibody", "cmax"])
def test_nonclinical_metric_is_retained_undrawable_on_the_ordinary_page(metric) -> None:
    first, second, _ = _records()
    second[0]["source_metric"] = metric
    groups = report_b._groups_for_page("efficacy", (first, second))
    workspace = report_b._comparison_workspace((first, second), groups, ())
    assert set(workspace["membership"]["row_ids"]) == {"first", "second"}
    assert "second" not in workspace["numeric_eligibility"]["drawable_row_ids"]
