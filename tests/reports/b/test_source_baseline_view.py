"""Exact source atoms reach the ordinary descriptive workspace without arm guesses."""

import json
from copy import deepcopy

import pytest

from ci_workflow.application.ctgov_baseline_atoms import extract_ctgov_baseline_atoms
from ci_workflow.renderers.portal import report_b
from ci_workflow.reports.b.source_baseline import build_source_baseline_view
from tests.unit.test_ctgov_baseline_atoms import _capture, _module, _record


def _view(record=None):
    facts = extract_ctgov_baseline_atoms(_capture(record or _record())).facts
    return build_source_baseline_view(
        facts, source_versions={"baseline-source": "source-v1"},
        fact_versions={f.fact_id: "version-" + f.fact_id for f in facts},
    )


def _project(view):
    return tuple((report_b._project_record(row, domain="baseline", names={},
        trial_names={row["trial_id"]: row["trial_id"]}, fallback=row["row_id"]), row)
        for row in view["facts"])


def test_every_numeric_atom_including_sd_and_zero_keeps_exact_source() -> None:
    view = _view()
    assert len(view["facts"]) == 9
    sd = [r for r in view["facts"] if r["source_value_role"] == "dispersion"]
    assert len(sd) == 2 and {r["statistic_form"] for r in sd} == {"STANDARD_DEVIATION"}
    assert {r["source_text"] for r in sd} == {"15.00", "15.2"}
    assert all(r["source_locator"]["field_path"].endswith(".spread") for r in sd)
    assert all(r["product_id"] is None and r["arm_role"] == "unknown" for r in view["facts"])
    assert any(r["disclosure_state"] == "reported_zero" and r["value"] == 0
               for r in view["facts"])
    assert any(r["is_source_aggregate"] and r["value"] == 30 for r in view["facts"])


@pytest.mark.parametrize("fields,expected", [
    ({"source_value_role": "dispersion", "source_dispersion_type": "STANDARD_DEVIATION"},
     "STANDARD_DEVIATION"),
    ({"source_value_role": "dispersion", "source_dispersion_type": None}, "not_reported"),
    ({"source_value_role": "denominator"}, "count"),
    ({"source_value_role": "participant_count"}, "count"),
])
def test_parent_param_type_never_overwrites_another_source_atom_role(fields, expected) -> None:
    source = {"source_param_type": "MEAN", **fields}
    assert report_b._source_statistic_form(source, source, "mean") == expected


def test_descriptive_common_age_column_retains_populations_and_separates_sd() -> None:
    first = _view()
    record = deepcopy(_record())
    record["protocolSection"]["identificationModule"]["nctId"] = "NCT87654321"
    _module(record)["populationDescription"] = (
        "Intent-to-treat (ITT) population included all randomized participants."
    )
    # Capture's identifier must correspond to its source; no identity guessing.
    source = _capture(_record()).model_copy(update={
        "source_id": "second-source", "query_or_identifier": "NCT87654321",
        "content_text": json.dumps(record),
    })
    facts = extract_ctgov_baseline_atoms(source).facts
    second = build_source_baseline_view(facts, source_versions={"second-source": "source-v2"},
        fact_versions={f.fact_id: "version-" + f.fact_id for f in facts})
    rows = _project({"facts": (*first["facts"], *second["facts"])})
    groups = report_b._groups_for_page("baseline-overview", rows)
    means = [g for g in groups if any(r["statistical_form_family"] == "mean"
                                    for r in g["rows"])]
    assert len(means) == 1
    assert {r["trial_id"] for r in means[0]["rows"]} == {"nct12345678", "nct87654321"}
    assert len({r["analysis_population"] for r in means[0]["rows"]}) == 2
    assert all(r["statistical_form_family"] == "mean" for r in means[0]["rows"])
    assert all(r["source_param_type"] == "MEAN" for r in means[0]["rows"])
    spreads = [r for g in groups for r in g["rows"]
               if r["source_value_role"] == "dispersion"]
    assert len(spreads) == 4
    assert all(r["statistical_form_family"] == "standard_deviation" for r in spreads)
    assert all(r["source_dispersion_type"] == "STANDARD_DEVIATION" for r in spreads)
    for row in spreads:
        repeated = report_b._project_record(row, domain="baseline", names={}, trial_names={},
                                           fallback=row["row_id"])
        assert repeated["statistical_form_family"] == "standard_deviation"
        assert repeated["source_value_role"] == "dispersion"
        assert repeated["value"] == row["value"]
    assert all(g["comparison_purpose"] == "baseline_descriptive_only" for g in groups)
    workspace = report_b._comparison_workspace(rows, groups, ())
    assert len(workspace["membership"]["row_ids"]) == 18
    assert any(len(c["cells"]) == 2 for c in workspace["columns"])


@pytest.mark.parametrize("population", ["Safety subset", "Not all randomized participants", ""])
def test_unresolved_or_different_population_is_not_given_common_identity(population) -> None:
    record = _record()
    _module(record)["populationDescription"] = population
    view = _view(record)
    assert all(r["population_context"] != "随机入组基线（仅描述性对照）"
               for r in view["facts"])


def test_source_or_fact_version_gap_fails_closed() -> None:
    facts = extract_ctgov_baseline_atoms(_capture(_record())).facts
    with pytest.raises(ValueError, match="版本"):
        build_source_baseline_view(facts, source_versions={}, fact_versions={})


def test_invalid_scalar_remains_technical_unknown_not_unpublished_or_zero() -> None:
    record = _record()
    _module(record)["measures"][0]["classes"][0]["categories"][0]["measurements"][0][
        "value"
    ] = "not a number"
    view = _view(record)
    row = next(r for r in view["facts"] if r["raw_value"] == "not a number")
    assert row["value"] is None and row["disclosure_state"] == "unresolved_due_to_route"
    projected = report_b._project_record(row, domain="baseline", names={},
                                         trial_names={}, fallback=row["row_id"])
    assert projected["renderable"] is False
