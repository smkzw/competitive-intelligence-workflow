"""Public article coordinates are not local filesystem paths or acceptance."""

import json
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.renderers.portal import report_b
from ci_workflow.reports.b.source_publication import build_source_publication_views
from ci_workflow.reports.common.evidence_view import (
    EvidenceObservationKind,
    clean_evidence_locator,
    locator_local_path_fields,
)
from tests.unit.test_source_publication_view import _fact

PATH = "/article/body[1]/sec[2]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[2]"
URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10202800/"


@pytest.mark.parametrize(
    "path",
    [PATH, "/article/body[1]/sec[1]/p[5]", "/article/front[1]/article-meta[1]/article-title[1]"],
)
def test_public_article_leaf_coordinate_is_retained_exactly(path):
    locator = EvidenceLocator(document_role="primary_results_publication", field_path=path, url=URL)
    assert clean_evidence_locator(locator) == locator
    assert locator_local_path_fields(locator) == ()
    assert report_b._exact_source_locator({"source_locator": locator.model_dump()}) == locator


@pytest.mark.parametrize(
    "path,url",
    [
        (PATH, None),
        (PATH, "file:///Users/example/source.xml"),
        (PATH, "http://localhost/article"),
        (PATH, "https://user:secret@example.org/article"),
        ("/Users/example/source.xml", URL),
        ("/article/body[1]/../private.xml", URL),
        ("/article/body[1]/sec[1]", URL),
        ("/article/body[1]/p[0]", URL),
        ("/article/body[1]/p[1]/secrets.json", URL),
    ],
)
def test_xml_namespace_cannot_exempt_local_or_coarse_coordinates(path, url):
    locator = EvidenceLocator(document_role="primary_results_publication", field_path=path, url=url)
    cleaned = clean_evidence_locator(locator)
    assert cleaned is None or cleaned.field_path is None
    assert report_b._exact_source_locator({"source_locator": locator.model_dump()}) is None


def test_xpath_in_a_different_locator_field_stays_local():
    locator = EvidenceLocator(document_role="primary_results_publication", table=PATH, url=URL)
    assert "table" in locator_local_path_fields(locator)
    assert clean_evidence_locator(locator).table is None


def test_ordinary_b_evidence_keeps_printed_composite_and_related_source_clauses():
    fact = _fact("14 (18.4)")
    source = build_source_publication_views(
        [fact],
        source_versions={fact.source_id: "source-v1"},
        fact_versions={fact.fact_id: "fact-v1"},
    )["efficacy"]["facts"][0]
    row = report_b._project_record(
        source,
        domain="efficacy",
        names={},
        trial_names={},
        fallback="primary-result",
    )
    root = Path(__file__).resolve().parents[3]
    payload = json.loads(
        (root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_bytes()
    )
    data = report_b.ReportBPortalData.model_validate(payload)
    view = report_b._evidence_view(
        data,
        row=row,
        source=source,
        page_id="efficacy-compare",
        observation_kind=EvidenceObservationKind.GENERAL,
        names={},
        trial_names={},
    )
    assert view.source_trace_state == "located"
    assert view.original_text == source["source_text"] == "14 (18.4)"
    assert view.locator.field_path == source["source_locator"]["field_path"]
    assert view.source_clause_context
    assert view.source_version_id == source["source_version_id"]
