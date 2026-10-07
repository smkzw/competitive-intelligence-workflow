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
    {"actual_timepoint": 24}, {"semantic_analysis_set": "per_protocol"},
    {"semantic_instrument_or_scale": "EASI v2.0"},
    {"semantic_estimand": "hypothetical"}, {"unit": "points"},
])
def test_known_question_has_one_matrix_column_but_keeps_conflicting_numeric_facets(change) -> None:
    first, second, _ = _records()
    second[0].update(change)
    records = (first, second)
    groups = report_b._groups_for_page("efficacy", records)
    assert len(groups) == 2  # Different scientific conditions never get a joint axis.
    before = json.dumps(groups, sort_keys=True, ensure_ascii=False)
    workspace = report_b._comparison_workspace(records, groups, ())
    assert len(workspace["columns"]) == 1
    column = workspace["columns"][0]
    assert set(column["row_ids"]) == {"first", "second"}
    assert column["cells"] == {"trial-a": ["first"], "trial-b": ["second"]}
    assert set(column["scientific_facet_ids"]) == {g["scientific_group_id"] for g in groups}
    assert {f["id"] for f in column["scientific_facets"]} == set(column["scientific_facet_ids"])
    assert set(column["facet_label_by_row"]) == {"first", "second"}
    assert column["comparison_purpose"] == "clinical_question_descriptive"
    assert column["cross_trial"] is False  # The column itself is not an equivalent numeric frame.
    assert json.dumps(groups, sort_keys=True, ensure_ascii=False) == before


def test_unknown_construct_is_not_inferred_from_the_only_known_question() -> None:
    first, second, _ = _records()
    second[0].update(clinical_concept="unknown", semantic_definition="unknown")
    groups = report_b._groups_for_page("efficacy", (first, second))
    workspace = report_b._comparison_workspace((first, second), groups, ())
    assert len(workspace["columns"]) == 2
    assert set(workspace["membership"]["row_ids"]) == {"first", "second"}


@pytest.mark.parametrize("change", [
    {"clinical_concept": "efficacy:not_reported", "semantic_definition": "unknown"},
    {"semantic_definition": "unknown"}, {"source_domain": "immunogenicity"},
])
def test_unresolved_question_columns_do_not_recombine_in_client_question_inventory(change) -> None:
    first, second, _ = _records()
    first[0].update(change)
    second[0].update(change)
    groups = report_b._groups_for_page("efficacy", (first, second))
    workspace = report_b._comparison_workspace((first, second), groups, ())
    columns = workspace["columns"]
    assert len(columns) == 2
    assert len({c["question_id"] for c in columns}) == 2
    assert all(c["question_known"] is False and c["question_state_reason"] for c in columns)
    assert set(report_b._comparison_query_inventory(workspace).values()) == {1}
    assert set(workspace["membership"]["row_ids"]) == {"first", "second"}


def test_matrix_study_labels_use_existing_display_identity_not_internal_row_keys() -> None:
    records = _records()
    groups = report_b._groups_for_page("efficacy", records)
    labels = {"trial-a": "PRIME｜NCT04202679", "trial-b": "ARCADIA｜NCT04501666",
              "trial-no-results": "研究无已公开结果｜NCT12345678"}
    workspace = report_b._comparison_workspace(records, groups, tuple(labels), study_labels=labels)
    assert workspace["study_labels"]["trial-a"] == labels["trial-a"]
    assert workspace["study_labels"]["trial-no-results"] == labels["trial-no-results"]
    assert set(labels) <= set(workspace["study_ids"])


def test_question_column_union_does_not_drop_cleared_or_unknown_definition_rows() -> None:
    records = _records()
    groups = report_b._groups_for_page("efficacy", records)
    workspace = report_b._comparison_workspace(records, groups, ())
    assert set().union(*(set(c["row_ids"]) for c in workspace["columns"])) == {
        "first", "second", "unknown",
    }
    assert any(set(c["row_ids"]) == {"unknown"} for c in workspace["columns"])
    assert workspace["numeric_eligibility"]["undrawable_reasons"]["unknown"] == (
        "用户清除，待重新核实"
    )


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
