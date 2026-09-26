"""The fixed 50-study source corpus can locate B safety without arm inference."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_registry import project_b_safety_source_views
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.storage.snapshot_store import LockedSnapshot


def test_fixed_full_b_safety_source_views_preserve_all_unknown_product_rows(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    root = repo / ".artifacts/r24-pnh-auto-binding-full-20260926"
    receipt_path = root / "logs/diagnostics/r24-22-all50-final.json"
    report_path = root / "inputs/report-a-r24-22-bound.json"
    required = (receipt_path, report_path, root / "state/project.sqlite")
    if not all(path.exists() for path in required):
        pytest.skip("fixed 50-study offline source candidate is not in this checkout")
    assert sha256(receipt_path.read_bytes()).hexdigest() == (
        "67b55385f6d6f34405068517a3ecf66962098767a7c387aa84be089d82a90ea1"
    )
    assert sha256(report_path.read_bytes()).hexdigest() == (
        "9a13e4b867e0f27341a616409bdd179851d8467cf7b6cf411a04d54f5b39b45d"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    report = ReportAPortalData.model_validate_json(report_path.read_bytes())
    manifest_path = root / receipt["snapshot_relative_path"]
    snapshot = LockedSnapshot(
        snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"],
        relative_path=receipt["snapshot_relative_path"],
        byte_size=manifest_path.stat().st_size,
    )
    versions = {
        item["row_ref"]: item["fact_version_id"]
        for item in receipt["fact_bindings"]
        if item["row_ref"].startswith("safety:")
        and not item["row_ref"].endswith(":denominator")
    }
    assert len(versions) == len(report.safety) == 514
    database_before = sha256((root / "state/project.sqlite").read_bytes()).hexdigest()
    views = project_b_safety_source_views(root, snapshot, report, versions)
    assert len(views) == 514
    assert sum(view["group_assignment_state"] == "unknown" for view in views) == 414
    assert {view["row_id"] for view in views} == {row.row_id for row in report.safety}
    assert all(view["source_locator"]["field_path"] == view["source_field_path"] for view in views)
    assert (row := next(view for view in views if view["row_id"] == "safe-364"))["unit"] == "%"
    assert row["source_text"] == "66.7"
    assert any(view["unit"] == "次" for view in views)

    b_report = ReportBPortalData.model_validate({
        **report.model_dump(mode="json"),
        "safety_views": {"coverage_mode": "complete", "facts": views},
    })
    site = tmp_path / "full-b-safety"
    render_report_b_site(b_report, site)
    page = (site / "safety.html").read_text(encoding="utf-8")
    evidence, _ = json.JSONDecoder().raw_decode(
        page.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].lstrip()
    )
    groups, _ = json.JSONDecoder().raw_decode(
        page.split("window.__CHART_GROUPS__ = ", 1)[1].lstrip()
    )
    by_id = {
        item["row"]["row_id"]: item for item in evidence
        if item["row"]["row_id"] in {view["row_id"] for view in views}
    }
    chart = {
        row["row_id"]: row for group in groups for row in group.get("rows", [])
        if row.get("row_id") in by_id
    }
    assert len(by_id) == len(chart) == 514
    assert all(item["source_trace_state"] == "located" for item in by_id.values())
    for view in views:
        item = by_id[view["row_id"]]
        assert item["original_text"] == view["source_text"]
        if view["group_assignment_state"] == "unknown":
            assert item["row"]["product_id"] is None
            assert chart[view["row_id"]]["renderable"] is False
    assert sha256((root / "state/project.sqlite").read_bytes()).hexdigest() == database_before
