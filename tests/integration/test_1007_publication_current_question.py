"""Current user values do not masquerade as printed publication components."""

from copy import deepcopy

import pytest

from ci_workflow.renderers.portal import report_b
from tests.integration.test_1007_source_question_projection import _component_inputs, _workspace


def _current_inputs(*, clear=False, undo=False, damage=None):
    records, _, projections = _component_inputs()
    source_row, source = records[1]
    row = deepcopy(source_row)
    current = None if clear else 60.0 if undo else 62.1
    row["value"] = current
    row["disclosure_state"] = "user_cleared" if clear else "reported_value"
    edit = {"review_state": "user_modified", "fact_id": row["source_fact"]["fact_id"],
        "fact_version_id": "edited-fact-v1", "request_id": "current-edit", "revision": 1,
        "primary_fragment_id": "source-cell", "source_version_id": row["source_version_id"],
        "source_locator": row["source_locator"], "current_value": (
            "用户清除，待重新核实" if clear else "45 (60.0)" if undo else "62.1%"),
        "original_value": "60%", "basis": "测试", "saved_by": "test",
        "saved_at": "2026-10-07T00:00:00+00:00", "operation": "undo" if undo else "save",
        "status_label_zh": "用户清除，待重新核实" if clear else "用户修订，未独立复核"}
    if damage == "source":
        edit["source_version_id"] = "foreign-source"
    elif damage == "fact":
        edit["fact_id"] = "foreign-fact"
    elif damage == "locator":
        edit["source_locator"] = {"field_path": "/other"}
    elif damage == "value":
        edit["current_value"] = "63.2%"
    elif damage == "count":
        row["reported_count"] = 46
    row["_user_edit"] = edit
    records[1] = (row, source)
    groups = report_b._groups_for_page("efficacy", records)
    return records, groups, projections


@pytest.mark.parametrize("undo", [False, True])
def test_current_edit_and_undo_keep_question_graph_and_immutable_source(undo):
    records, groups, projections = _current_inputs(undo=undo)
    before = deepcopy(records)
    result = _workspace(records, groups, projections)
    assert len(result["columns"]) == 1
    assert len(result["descriptive_groups"]) == 1
    plotted = result["descriptive_groups"][0]["rows"]
    assert {row["value"] for row in plotted} == {18.4, 60.0 if undo else 62.1}
    assert next(row for row in plotted if row["row_id"] == "row-1")["_user_edit"]
    assert records == before
    assert records[1][0]["source_fact"]["raw_value"] == "45 (60.0)"
    assert records[1][0]["source_fact"]["normalized_value"] is None


def test_clear_remains_in_question_table_but_cannot_plot_original_value():
    records, groups, projections = _current_inputs(clear=True)
    result = _workspace(records, groups, projections)
    assert len(result["columns"]) == 1
    assert set(result["columns"][0]["row_ids"]) == {"row-0", "row-1"}
    assert result["descriptive_groups"] == ()
    assert records[1][0]["value"] is None


@pytest.mark.parametrize("damage", ["source", "fact", "locator", "value", "count"])
def test_unbound_current_edit_is_not_authority_to_plot(damage):
    records, groups, projections = _current_inputs(damage=damage)
    result = _workspace(records, groups, projections)
    assert result["descriptive_groups"] == ()
    assert set(result["membership"]["row_ids"]) == {"row-0", "row-1"}
