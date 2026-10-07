"""Source scalar editing, not rate derivation or inferred product membership."""

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


def _extended_data():
    record = _record()
    measurement = _module(record)["measures"][0]["classes"][0]["categories"][0][
        "measurements"
    ][0]
    measurement.update(lowerLimit="40", upperLimit="60")
    return ReportBPortalData.model_validate({
        **_data().model_dump(mode="json"), "baseline_views": _view(record),
    })


@pytest.mark.parametrize("role,stat,number,form", [
    ("participant_count", "count", 7, "count"),
    ("denominator", "count", 25, "denominator"),
    ("reported_measure", "下限", 41.5, "lower_limit"),
    ("reported_measure", "上限", 62.5, "upper_limit"),
])
def test_raw_count_N_and_limits_can_edit_clear_without_deriving_rates(
    role, stat, number, form,
):
    data = _extended_data()
    original = deepcopy(data.model_dump(mode="json"))
    row = next(r for r in data.baseline_views["facts"]
               if r["source_value_role"] == role and r["statistic_form"] == stat)
    binding = active_fact_binding_for_b(data, "baseline", row["row_id"])
    assert binding.statistical_form == form
    assert binding.product_id is None
    revision, _ = _revision(data, row, number=number)
    validate_active_fact_revision_b(data, revision)
    projected, nodes = _project_active_facts_b(data, revision)
    changed = next(r for r in projected.baseline_views["facts"]
                   if r["row_id"] == row["row_id"])
    assert changed["value"] == number
    assert changed["source_text"] == row["source_text"]
    assert "numerator" not in changed and "denominator" not in changed
    assert nodes[0].binding_identity == binding
    cleared, _ = _revision(data, row, cleared=True)
    projected, _ = _project_active_facts_b(data, cleared)
    changed = next(r for r in projected.baseline_views["facts"]
                   if r["row_id"] == row["row_id"])
    assert changed["value"] is None and changed["disclosure_state"] == "user_cleared"
    assert data.model_dump(mode="json") == original


@pytest.mark.parametrize("role", ["participant_count", "denominator"])
@pytest.mark.parametrize("number", [-1, 2.5, float("inf"), float("nan")])
def test_current_counts_reject_invalid_integers(role, number):
    data = _extended_data()
    row = next(r for r in data.baseline_views["facts"]
               if r["source_value_role"] == role)
    revision, _ = _revision(data, row, number=number)
    with pytest.raises(ValueError):
        validate_active_fact_revision_b(data, revision)


@pytest.mark.parametrize("stat,number", [("下限", 61), ("上限", 39)])
def test_current_source_limit_pair_rejects_inverted_bounds(stat, number):
    data = _extended_data()
    row = next(r for r in data.baseline_views["facts"] if r["statistic_form"] == stat)
    revision, _ = _revision(data, row, number=number)
    with pytest.raises(ValueError, match="上下限"):
        validate_active_fact_revision_b(data, revision)
    with pytest.raises(ValueError, match="上下限"):
        _project_active_facts_b(data, revision)


def test_zero_N_and_count_without_N_remain_independent_scalars():
    record = _record()
    _module(record).pop("denoms")
    data = ReportBPortalData.model_validate({
        **_data().model_dump(mode="json"), "baseline_views": _view(record),
    })
    row = next(r for r in data.baseline_views["facts"]
               if r["source_value_role"] == "participant_count")
    revision, _ = _revision(data, row, number=0)
    projected, _ = _project_active_facts_b(data, revision)
    changed = next(r for r in projected.baseline_views["facts"]
                   if r["row_id"] == row["row_id"])
    assert changed["value"] == 0 and changed["disclosure_state"] == "reported_zero"
    assert "denominator" not in changed


@pytest.mark.parametrize("role,number", [("participant_count", 11), ("denominator", 4)])
def test_edited_counts_cannot_contradict_explicit_same_source_group_N(role, number):
    data = _extended_data()
    row = next(r for r in data.baseline_views["facts"]
               if r["source_value_role"] == role and r["group_id"] == "BG1")
    revision, _ = _revision(data, row, number=number)
    with pytest.raises(ValueError, match="作用域N"):
        validate_active_fact_revision_b(data, revision)


def test_explicit_zero_zero_remains_source_counts_without_rate():
    data = _extended_data()
    row = next(r for r in data.baseline_views["facts"]
               if r["source_value_role"] == "denominator" and r["group_id"] == "BG7")
    revision, _ = _revision(data, row, number=0)
    projected, _ = _project_active_facts_b(data, revision)
    assert next(r for r in projected.baseline_views["facts"]
                if r["row_id"] == row["row_id"])["value"] == 0


@pytest.mark.parametrize("unit,number", [("samples", 2), ("participants", -3),
                                        ("participants", 2.5)])
def test_unverified_source_N_type_cannot_become_a_participant_cap(unit, number):
    data = _extended_data()
    rows = deepcopy(data.baseline_views["facts"])
    n = next(r for r in rows if r["source_value_role"] == "denominator"
             and r["group_id"] == "BG1")
    n.update(unit=unit, value=number)
    data = data.model_copy(update={"baseline_views": {**data.baseline_views, "facts": rows}})
    count = next(r for r in rows if r["source_value_role"] == "participant_count"
                 and r["group_id"] == "BG1")
    revision, _ = _revision(data, count, number=7)
    validate_active_fact_revision_b(data, revision)
    projected, _ = _project_active_facts_b(data, revision)
    assert next(r for r in projected.baseline_views["facts"]
                if r["row_id"] == count["row_id"])["value"] == 7
