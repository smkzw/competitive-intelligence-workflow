"""Exact B safety provenance must not create an editable product consumer."""

from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_registry import (
    PortalConsumerRegistrationError,
    project_b_safety_source_views,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.storage.snapshot_store import LockedSnapshot
from tests.integration.reports.test_b_report_portal import _page_json_assignment


def _fixed_candidate() -> tuple[Path, ReportAPortalData, LockedSnapshot, dict[str, str]]:
    repo = Path(__file__).resolve().parents[2]
    root = repo / ".artifacts/r24-50-source-expansion-20260926/project-v2"
    receipt_path = repo / ".artifacts/r24-50-source-expansion-20260926/receipt-two-studies-v2.json"
    report_path = root / "inputs/r24-50-a-bound.json"
    required = (receipt_path, report_path, root / "state/project.sqlite")
    if not all(path.exists() for path in required):
        pytest.skip("fixed two-study CT.gov development candidate is not present")
    assert sha256(receipt_path.read_bytes()).hexdigest() == (
        "d07641e682fb6c12393d2e5546d2b642c8a7b82caebfc03e862979cdaa1e0e14"
    )
    assert sha256(report_path.read_bytes()).hexdigest() == (
        "fe2a3228888649820c0f71e6705381126c886bc1245856f85abc00acf5632f79"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest_path = root / receipt["snapshot_relative_path"]
    snapshot = LockedSnapshot(
        snapshot_id=receipt["snapshot_id"],
        kind="evidence",
        report=None,
        sha256=receipt["snapshot_sha256"],
        relative_path=receipt["snapshot_relative_path"],
        byte_size=manifest_path.stat().st_size,
    )
    versions = {
        item["row_ref"]: item["fact_version_id"]
        for item in receipt["fact_bindings"]
        if item["row_ref"].startswith("safety:") and not item["row_ref"].endswith(":denominator")
    }
    return root, ReportAPortalData.model_validate_json(report_path.read_bytes()), snapshot, versions


def test_historical_safety_closure_is_immutable_not_current_semantic_acceptance(
    tmp_path: Path,
) -> None:
    root, a_report, snapshot, versions = _fixed_candidate()
    database_path = root / "state/project.sqlite"
    database_before = sha256(database_path.read_bytes()).hexdigest()
    with sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True) as database:
        b_before = database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings WHERE report='B'"
        ).fetchone()[0]

    assert len(versions) == 92  # preserved historical accepted source set
    with pytest.raises(PortalConsumerRegistrationError, match="measure_context"):
        project_b_safety_source_views(root, snapshot, a_report, versions)
    # The two raw AE-group counts are unchanged. The old compound rows must be
    # re-extracted and reclassified in a new candidate, never edited in-place.
    stable_refs = {
        f"safety:{row_id}"
        for row_id in (
            "safe-9fe1ea2f8b52dd3ec294",
            "safe-7727c2ce1c1803f54bb0",
        )
    }
    views = project_b_safety_source_views(
        root,
        snapshot,
        a_report,
        {ref: versions[ref] for ref in stable_refs},
    )
    assert len(views) == 2
    assert len({view["row_id"] for view in views}) == 2
    assert all(view["group_assignment_state"] == "declared" for view in views)
    assert all(view["source_locator"]["field_path"] == view["source_field_path"] for view in views)
    assert all(
        view["source_locator"]["url"].startswith("https://clinicaltrials.gov/study/")
        for view in views
    )
    assert all(view["source_text"] is not None for view in views)

    b_report = ReportBPortalData.model_validate(
        {
            **a_report.model_dump(mode="json"),
            "safety_views": {"coverage_mode": "partial", "facts": views},
        }
    )
    site = tmp_path / "b-precise-safety"
    render_report_b_site(b_report, site)
    groups = _page_json_assignment(site, "safety.html", "__CHART_GROUPS__")
    evidence = _page_json_assignment(site, "safety.html", "__EVIDENCE_VIEWS__")
    safety_rows = {
        row["row_id"]: row
        for group in groups
        for row in group.get("rows", [])
        if row.get("_domain") == "safety"
    }
    assert len(safety_rows) == 514
    selected_evidence = {
        item["row"]["row_id"]: item
        for item in evidence
        if item["row"]["row_id"] in {view["row_id"] for view in views}
    }
    assert len(selected_evidence) == 2
    assert all(item["source_trace_state"] == "located" for item in selected_evidence.values())
    for view in views:
        item = selected_evidence[view["row_id"]]
        assert item["original_text"] == view["source_text"]
        if view["group_assignment_state"] == "unknown":
            assert item["row"]["product_id"] is None
            assert safety_rows[view["row_id"]]["renderable"] is False
            assert safety_rows[view["row_id"]]["value"] == view["value"]

    assert sha256(database_path.read_bytes()).hexdigest() == database_before
    with sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True) as database:
        assert (
            database.execute(
                "SELECT COUNT(*) FROM source_portal_consumer_bindings WHERE report='B'"
            ).fetchone()[0]
            == b_before
        )


def test_source_view_projection_rejects_quote_or_version_drift() -> None:
    root, a_report, snapshot, versions = _fixed_candidate()
    selected_ref = next(ref for ref in versions if ref.startswith("safety:"))
    selected_row_id = selected_ref.removeprefix("safety:")
    altered = a_report.model_dump(mode="json")
    row = next(item for item in altered["safety"] if item["row_id"] == selected_row_id)
    row["source_text"] = "not the locked quote"
    with pytest.raises(PortalConsumerRegistrationError):
        project_b_safety_source_views(
            root,
            snapshot,
            ReportAPortalData.model_validate(altered),
            {selected_ref: versions[selected_ref]},
        )
    other_version = next(value for key, value in versions.items() if key != selected_ref)
    with pytest.raises(PortalConsumerRegistrationError):
        project_b_safety_source_views(
            root,
            snapshot,
            a_report,
            {selected_ref: other_version},
        )
