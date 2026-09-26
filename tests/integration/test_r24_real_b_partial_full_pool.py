"""A partial real PNH source view must not erase B's related-study pool."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from tests.integration.test_w04_source_consumer_registry import _b_direct_source_view

SOURCE_DB_SHA256 = "74330a821f722f22f56174b859cf098f289c6b1bd1f2307789f93e16db56d030"
RECEIPT_SHA256 = "f6f7bfa8aab3d5635f3b93ebae340d5e8c676bb1ad07b983687699a695275e1b"


def test_real_one_precise_b_view_keeps_every_other_related_efficacy_row(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2] / ".artifacts/r24-pnh-refresh-slice-20260926"
    database_path = root / "state/project.sqlite"
    receipt_path = root / "receipts/r24-46-nct04820530-candidate.json"
    report_path = root / "inputs/r24-46-nct04820530-a-bound.json"
    if not all(path.exists() for path in (database_path, receipt_path, report_path)):
        pytest.skip("pinned current CT.gov source slice unavailable; no real-source PASS")
    assert hashlib.sha256(database_path.read_bytes()).hexdigest() == SOURCE_DB_SHA256
    assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == RECEIPT_SHA256
    report = ReportAPortalData.model_validate_json(report_path.read_bytes())
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    first_row = next(row for row in report.efficacy if row.source_version_id)
    source_fact_version = next(
        item["fact_version_id"] for item in receipt["fact_bindings"]
        if item["row_ref"] == f"efficacy:{first_row.row_id}"
    )
    with sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        locator, quote = db.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (source_fact_version,),
        ).fetchone()
    b_source_view = _b_direct_source_view(report, locator, source_text=quote)
    payload = b_source_view.model_dump(mode="json")
    payload["efficacy_views"]["coverage_mode"] = "partial"
    b_report = ReportBPortalData.model_validate(payload)
    site = tmp_path / "b-full-related-pool-partial-source"
    render_report_b_site(b_report, site)
    html = (site / "efficacy.html").read_text(encoding="utf-8")
    evidence = json.loads(
        html.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].split(";\n", 1)[0]
    )
    expected = {row.row_id for row in report.efficacy}
    actual = {view["row"]["row_id"] for view in evidence}
    assert len(actual) == len(evidence) == len(expected)
    assert actual == expected
    chart_literal = html.split("window.__CHART_GROUPS__ = ", 1)[1]
    chart_groups, end = json.JSONDecoder().raw_decode(chart_literal)
    assert chart_literal[end] == ";"
    assert len(chart_groups) > 48  # the B pager must mount a subset, not truncate the source set
    chart_ids = {row["row_id"] for group in chart_groups for row in group["rows"]}
    assert chart_ids == expected
    page_size = 24
    page_id_union = {
        row["row_id"]
        for start in range(0, len(chart_groups), page_size)
        for group in chart_groups[start : start + page_size]
        for row in group["rows"]
    }
    assert page_id_union == expected
    located = {view["row"]["row_id"]: view for view in evidence
               if view["source_trace_state"] == "located"}
    assert set(located) == set(receipt["registered_a_efficacy_consumers"])
    assert located[first_row.row_id]["original_text"] == quote
    uncovered = next(view for view in evidence if view["row"]["row_id"] not in located)
    assert uncovered["source_trace_state"] != "located"
    assert uncovered["original_text_status"] != "provided"
