"""Qualified Protocol/SAP plans coexist with actual registry N, never scalarized."""

import json

import pytest

from ci_workflow.domain.enums import FactReviewState
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _chart_groups,
    _evidence_view,
    _page_observations,
)
from ci_workflow.reports.c.contracts import DesignFieldFamily
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from tests.integration.test_r24_c_pdf_extension import _arguments, _builder


@pytest.fixture(scope="module")
def candidate(tmp_path_factory):
    args = _arguments(tmp_path_factory.mktemp("planned-sample-terms"))
    result = _builder()(**args)
    data = ReportCPortalData.model_validate_json(
        (args["output"] / "review-portal-data.json").read_bytes()
    )
    return args["output"], result, data


def _plans(data):
    return [r for r in data.observations if r.field == "planned_sample_size_terms"]


def test_planned_terms_keep_qualifiers_repeat_rule_and_actual_n(candidate):
    _, _, data = candidate
    rows = _plans(data)
    assert len(rows) == 5, "Native planned/cohort/completer terms remain deferred"
    assert {r.field_family for r in rows} == {DesignFieldFamily.SAMPLE_SIZE}
    assert all(r.review_state is FactReviewState.CANDIDATE for r in rows)
    assert all(r.threshold_value is None and r.threshold_unit is None for r in rows)
    quotes = "\n".join(r.source_text for r in rows)
    for text in (
        "approximately 15", "at least 6", "28 days", "approximately 50",
        "up to approximately 50", "more than one cohort", "medical benefit",
    ):
        assert text in " ".join(quotes.split())
    actual = [r for r in data.observations if r.field == "planned_or_actual_sample_size"]
    assert len(actual) == 2
    assert {r.source_text for r in actual} == {"9", "15"}
    assert all("ACTUAL" in r.display_text for r in actual)


def test_plans_share_complete_query_but_never_become_exact_numeric_n(candidate):
    _, _, data = candidate
    plans = _plans(data)
    assert plans, "No planned sample terms reached the report"
    query = _page_observations(data, "sample-analysis-statistics")
    groups = _chart_groups(data, query, page_id="sample-analysis-statistics", title="统计")
    indexed = {r["row_id"]: r for g in groups for r in g["rows"]}
    assert set(indexed) == {r.row_id for r in query}
    for observation in plans:
        row = indexed[observation.row_id]
        assert row["value"] == observation.source_text
        assert row["source_topic_zh"] == observation.source_clause_context.label_zh
        assert row["display_label_zh"] == "计划样本量与计数条件"
        assert "numeric_projection" not in row and "numeric_value" not in row
        view = _evidence_view(data, observation, page_id="sample-analysis-statistics")
        assert view.original_text == observation.source_text
        assert view.locator.page == observation.source_locator.page
    repeat = next(r for r in plans if r.source_row_id.endswith("sap-p8-medical-benefit-repeat"))
    assert _evidence_view(data, repeat, page_id="sample-analysis-statistics").conflicts


def test_planned_terms_have_source_bindings_without_acceptance_or_current(candidate):
    output, manifest, data = candidate
    rows = _plans(data)
    assert rows, "No planned terms were ingested"
    closure = SnapshotStore(output / "project").read(
        LockedSnapshot.model_validate(manifest["snapshot"])
    )["closure"]
    by_id = {f["fact"]["fact_id"]: f for f in closure["facts"]}
    for row in rows:
        fact = by_id[row.row_id]["fact"]
        assert fact["raw_value"] == fact["normalized_value"] == row.source_text
        assert fact["field_id"] == "c.sample_size.planned_sample_size_terms"
        assert manifest["fact_version_by_ref"][row.row_id] == by_id[row.row_id]["fact_version_id"]
    assert manifest["registered_consumers"] == len(data.observations) == 127
    assert manifest["scientific_acceptance"] is False
    assert manifest["current_generation_switched"] is False
    assert not (output / "project/reports/current.json").exists()
    assert len(closure["sources"]) == 33
    assert len(json.loads((output / "readable-review/index.json").read_text())["clauses"]) == 42
