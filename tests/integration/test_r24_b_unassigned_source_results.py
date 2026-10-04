"""Actual source results survive missing product association without rate invention."""

from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.source_research_service import (
    SourceCapture,
    extract_ctgov_atomic_results,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site


def _source(title: str, unit: str, value: str, denominator: str | None) -> SourceCapture:
    record = {"protocolSection": {"identificationModule": {
        "nctId": "NCT00001999", "briefTitle": "相关研究原题",
    }}, "hasResults": True, "resultsSection": {"outcomeMeasuresModule": {
        "outcomeMeasures": [{
            "title": title, "unitOfMeasure": unit, "paramType": "NUMBER",
            "timeFrame": "Week 24", "groups": [
                {"id": "OG0", "title": "Registered group A"},
                {"id": "OG1", "title": "Registered group B"},
            ],
            "denoms": ([{"units": "Participants", "counts": [
                {"groupId": group, "value": denominator} for group in ("OG0", "OG1")
            ]}] if denominator is not None else []),
            "classes": [{"title": "Full analysis", "categories": [{
                "title": "All observed", "measurements": [
                    {"groupId": group, "value": value} for group in ("OG0", "OG1")
                ],
            }]}],
        }],
    }}}
    return SourceCapture(
        source_id="ctgov-nct00001999", route_id="synthetic-source-results",
        source_type="clinical_trial_registry", title="相关研究原题",
        url="https://clinicaltrials.gov/study/NCT00001999",
        query_or_identifier="NCT00001999", language="en", access_method="synthetic",
        media_type="application/json", content_text=json.dumps(record),
        acquired_at=datetime(2026, 10, 4, tzinfo=UTC), published_at=None,
        effective_at=None, first_disclosed_at=None,
        locator=EvidenceLocator(
            document_role="clinical_trial_registry",
            field_path="$.protocolSection.identificationModule.nctId",
        ),
    )


@pytest.mark.parametrize(("title", "unit", "value", "denominator", "domain"), (
    ("Number of Participants With Clinical Response", "Participants", "3", "10", "efficacy"),
    ("Serious Adverse Events", "Participants", "3", None, "adverse_events"),
    ("Serious Adverse Events", "Events", "3", "10", "adverse_events"),
    ("Serious Adverse Events", "Participants", "0", "10", "adverse_events"),
    ("Serious Adverse Events", "Participants", "0", "0", "adverse_events"),
    ("Anti Drug Antibodies", "Participants", "3", "10", "immunogenicity"),
    ("Pharmacokinetic Cmax", "ng/mL", "3.2", None, "pk_pd"),
))
def test_raw_source_views_reach_b_without_product_or_rate_guess(
    tmp_path: Path, title: str, unit: str, value: str,
    denominator: str | None, domain: str,
) -> None:
    source = _source(title, unit, value, denominator)
    atoms, _issues = extract_ctgov_atomic_results(source)
    assert len(atoms) == 2 and {atom.domain for atom in atoms} == {domain}
    project = importlib.import_module("ci_workflow.application.ctgov_b_result_views")
    views = project.project_unassigned_ctgov_results((source,))
    rows = (*views.efficacy, *views.safety, *views.supporting)
    assert len(rows) == 2
    assert {row["group_id"] for row in rows} == {"OG0", "OG1"}
    assert len({row["row_id"] for row in rows}) == 2
    for row, atom in zip(rows, atoms, strict=True):
        assert row["product_id"] is None and row["group_assignment_state"] == "unknown"
        assert row["value"] == float(value)  # 3 is not replaced by inferred 30%.
        assert row["unit"] == unit and row["raw_unit"] == unit
        assert row["source_text"] == atom.value_quote == value
        assert row["source_locator"] == atom.value_locator.model_dump(mode="json")
        assert row["source_class_title"] == atom.class_title
        assert row["source_category_title"] == atom.category_title
        assert row["domain"] == domain and row["review_state"] == "candidate"
        assert row["disclosure_state"] == (
            "reported_zero" if float(value) == 0 else "reported_value"
        )
        if domain == "adverse_events" and unit == "Events":
            assert row["count_basis"] == "events" and row["measure_object"] == "event_count"
        if denominator == "0":
            # The explicitly reported denominator stays zero; it is not a rate.
            assert row["denominator"] == 0 and row["denominator_quote"] == "0"
            assert row["denominator_candidates"][0]["raw_value"] == "0"
    fixture = (
        Path(__file__).resolve().parents[2]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    payload: dict[str, Any] = json.loads(fixture.read_bytes())
    payload["related_studies"] = [{
        **payload["trials"][0], "id": "nct00001999", "display_id": "NCT00001999",
        "name": "相关研究原题", "product_id": None,
    }]
    for field, values in (
        ("efficacy_views", views.efficacy), ("safety_views", views.safety),
        ("supporting_evidence_views", views.supporting),
    ):
        if values:
            payload[field] = {"coverage_mode": "partial", "facts": values}
    site = tmp_path / "site"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    page = ("efficacy" if views.efficacy else "safety" if views.safety
            else "subgroups-supporting-evidence")
    html = (site / f"{page}.html").read_text(encoding="utf-8")
    for row in rows:
        assert row["row_id"] in html and row["source_version_id"] in html
    if domain in {"efficacy", "adverse_events"}:
        assert "group_product_relationship_unresolved" in html
    assert "已验科学结论" in html  # source evidence does not auto-approve the candidate.


def test_duplicate_source_identity_is_rejected() -> None:
    source = _source("Serious Adverse Events", "Participants", "3", None)
    project = importlib.import_module("ci_workflow.application.ctgov_b_result_views")
    with pytest.raises(ValueError, match="重复"):
        project.project_unassigned_ctgov_results((source, source))
