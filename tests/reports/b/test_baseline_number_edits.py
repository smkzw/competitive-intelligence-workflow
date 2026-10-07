"""Source NUMBER is editable without rewriting it to MEAN/count or a rate."""

from copy import deepcopy

import pytest

from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    _project_active_facts_b,
    active_fact_binding_for_b,
    validate_active_fact_revision_b,
)
from tests.reports.b.test_baseline_active_projection import _data, _revision
from tests.reports.b.test_source_baseline_view import _view
from tests.unit.test_ctgov_baseline_atoms import _module, _record


def number_data(unit="Participants"):
    record = _record()
    measure = _module(record)["measures"][1]
    measure["paramType"] = "NUMBER"
    measure["unitOfMeasure"] = unit
    return ReportBPortalData.model_validate({
        **_data().model_dump(mode="json"), "baseline_views": _view(record),
    })


@pytest.mark.parametrize("unit,number,object_type", [
    ("Participants", 6, "participants"), ("change points", -1.5, "reported_measure"),
])
def test_NUMBER_keeps_original_type_and_scope_through_set_and_clear(unit, number, object_type):
    data = number_data(unit)
    before = deepcopy(data.model_dump(mode="json"))
    row = next(r for r in data.baseline_views["facts"]
               if r["statistic_form"] == "NUMBER" and r["group_id"] == "BG1")
    binding = active_fact_binding_for_b(data, "baseline", row["row_id"])
    assert binding.statistical_form == "reported_number"
    assert binding.measure_object == object_type and binding.product_id is None
    for cleared in (False, True):
        revision, _ = _revision(data, row, number=number, cleared=cleared)
        validate_active_fact_revision_b(data, revision)
        projected, _ = _project_active_facts_b(data, revision)
        current = next(r for r in projected.baseline_views["facts"]
                       if r["row_id"] == row["row_id"])
        assert current["value"] == (None if cleared else number)
        assert current["statistic_form"] == current["source_param_type"] == "NUMBER"
        assert current["source_value_role"] == "reported_measure"
        assert current["source_text"] == row["source_text"]
        assert "numerator" not in current and "denominator" not in current
    assert data.model_dump(mode="json") == before


@pytest.mark.parametrize("value", [-1, 0.5, True, float("nan"), float("inf")])
def test_participant_NUMBER_has_integer_domain_but_not_inferred_statistic(value):
    data = number_data()
    row = next(r for r in data.baseline_views["facts"] if r["statistic_form"] == "NUMBER")
    binding = active_fact_binding_for_b(data, "baseline", row["row_id"])
    assert binding.statistical_form == "reported_number"
    revision, _ = _revision(data, row, number=value)
    with pytest.raises(ValueError):
        validate_active_fact_revision_b(data, revision)


def test_participant_NUMBER_respects_only_explicit_same_group_N():
    data = number_data()
    row = next(r for r in data.baseline_views["facts"]
               if r["statistic_form"] == "NUMBER" and r["group_id"] == "BG1")
    revision, _ = _revision(data, row, number=11)
    with pytest.raises(ValueError, match="作用域N"):
        validate_active_fact_revision_b(data, revision)
    rows = deepcopy(data.baseline_views["facts"])
    for r in rows:
        if r["source_value_role"] == "denominator":
            r["unit"] = "samples"
    unknown = data.model_copy(update={"baseline_views": {**data.baseline_views, "facts": rows}})
    validate_active_fact_revision_b(unknown, revision)


def test_NUMBER_without_unit_or_value_is_not_editable():
    data = number_data()
    for field, bad in (("unit", ""), ("value", None)):
        rows = deepcopy(data.baseline_views["facts"])
        row = next(r for r in rows if r["statistic_form"] == "NUMBER")
        row[field] = bad
        incomplete = data.model_copy(update={
            "baseline_views": {**data.baseline_views, "facts": rows},
        })
        with pytest.raises(ValueError):
            active_fact_binding_for_b(incomplete, "baseline", row["row_id"])
