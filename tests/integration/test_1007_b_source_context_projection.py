"""Source statistics/context must reach ordinary B without inventing equivalence."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.b_efficacy_source_views import project_b_efficacy_source_views
from ci_workflow.domain.source_clause_context import SourceClauseContext
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import _project_record
from ci_workflow.reports.common.numeric_projection import NumericMeasureKind, infer_numeric_kind
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore


def _project(**changes: object) -> dict[str, object]:
    return _project_record({
        "row_id": "observation", "product_id": "p", "trial_id": "s",
        "endpoint": "Score change", "value": -24.6, "unit": "%",
        "population": "登记结果人群", "analysis_population": "登记结果人群",
        "timepoint": "Week 24", "source_param_type": "LEAST_SQUARES_MEAN",
        "source_analysis_population": "All randomized participants, excluding site X.",
        "source_measure_definition": "Change from baseline; rescue handled as nonresponse.",
        **changes,
    }, domain="efficacy", names={"p": "产品"}, trial_names={"s": "研究"}, fallback="row")


@pytest.mark.parametrize("form", ["LEAST_SQUARES_MEAN", "least_squares_mean", "LS mean"])
@pytest.mark.parametrize("unit", ["%", "percentage of participants"])
def test_explicit_adjusted_form_precedes_percent_unit(form: str, unit: str) -> None:
    assert infer_numeric_kind(statistic_form=form, unit=unit, domain="efficacy") is (
        NumericMeasureKind.ADJUSTED_ESTIMATE
    )


def test_ordinary_projection_consumes_source_statistics_without_count_conversion() -> None:
    row = _project(numerator=51, denominator=60, value=82.3)
    assert row["statistical_form_family"] == "least_squares_mean"
    assert row["semantic_analysis_form"] == "least_squares_mean"
    assert row["population"] == "All randomized participants, excluding site X."
    assert row["semantic_definition"] == (
        "Change from baseline; rescue handled as nonresponse."
    )
    numeric = row["numeric_projection"]
    assert numeric["kind"] == "adjusted_estimate"
    assert numeric["raw_value"] == numeric["plot_value"] == 82.3
    assert numeric["numerator"] is None and numeric["denominator"] is None
    assert row["numerator"] == 51 and row["denominator"] == 60
    # Source preservation is not a clinical direction/estimand/scale decision.
    assert row["semantic_estimand"] == "estimand-not-reported"
    assert row["semantic_direction"] == "direction-not-reported"
    assert row["semantic_instrument_or_scale"] == "instrument-or-scale-not-reported"


@pytest.mark.parametrize("form", ["NUMBER", "UNKNOWN_NEW_FORM", None])
def test_unresolved_source_statistic_is_not_unit_guessed_as_response_or_mean(form) -> None:
    row = _project(source_param_type=form, unit="%")
    assert row["statistical_form_family"] == "not_reported"
    assert row["source_param_type"] == form


@pytest.mark.parametrize("population", [None, ""])
def test_missing_source_population_cannot_borrow_generic_display_population(population) -> None:
    row = _project(source_analysis_population=population)
    assert row["population_context"] == "not_reported"
    assert row["semantic_analysis_set"] == "not_reported"


def test_source_population_clauses_are_not_reduced_to_itt_keyword() -> None:
    first = _project(source_analysis_population="ITT: all randomized, excluding site X.")
    second = _project(source_analysis_population="ITT: all randomized, including site X.")
    assert first["semantic_analysis_set"] != second["semantic_analysis_set"]


def test_real_source_bridge_exposes_full_verbatim_measure_context_read_only() -> None:
    root = Path(__file__).resolve().parents[2] / ".artifacts/1007-outcome-scope-current-v2"
    receipt_path = root / "receipt.json"
    if not receipt_path.is_file():
        pytest.skip("current real PN source candidate absent; not scientific acceptance")
    receipt = json.loads(receipt_path.read_bytes())
    project = root / "project"
    snapshot_path = project / receipt["snapshot_relative_path"]
    tracked = [receipt_path, snapshot_path, project / "state/project.sqlite",
               project / "inputs/a-bound.json", project / "inputs/b-bound.json"]
    before = {p: sha256(p.read_bytes()).hexdigest() for p in tracked}
    snapshot = LockedSnapshot(snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"], relative_path=receipt["snapshot_relative_path"],
        byte_size=snapshot_path.stat().st_size)
    report = ReportAPortalData.model_validate_json((project / "inputs/a-bound.json").read_bytes())
    versions = {b["row_ref"]: b["fact_version_id"] for b in receipt["fact_bindings"]}
    selected = {f"efficacy:{row}": versions[f"efficacy:{row}"]
                for row in receipt["registered_a_efficacy_consumers"]}
    views = project_b_efficacy_source_views(project, snapshot, report, selected)
    closure = SnapshotStore(project).read(snapshot)["closure"]
    sources = {s["source_version_id"]: s["capture"] for s in closure["sources"]}
    assert len(views) == 91
    for view in views:
        capture = sources[view["source_version_id"]]
        record = json.loads(capture["content_text"])
        path = view["source_measure_path"]
        index = int(path.rsplit("[", 1)[1][:-1])
        measure = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][index]
        assert view["source_measure_definition"] == measure.get("description", "")
        clause = SourceClauseContext.model_validate(view["source_clause_context"])
        refs = {r.locator.field_path: r.original_text for r in clause.continuations}
        if measure.get("description"):
            assert refs[f"$.{path}.description"] == measure["description"]
        if measure.get("populationDescription"):
            assert refs[f"$.{path}.populationDescription"] == measure["populationDescription"]
        row = _project_record(view, domain="efficacy", names={}, trial_names={}, fallback="row")
        assert row["population"] == (measure.get("populationDescription") or "")
        assert row["semantic_definition"] == (measure.get("description") or view["endpoint"])
        assert row["source_param_type"] == measure.get("paramType")
        assert row["value"] == view["value"]
    assert {p: sha256(p.read_bytes()).hexdigest() for p in tracked} == before
