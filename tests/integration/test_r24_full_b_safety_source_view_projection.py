"""Immutable legacy closure and current exact source views are separate contracts."""

from __future__ import annotations

import json
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


def test_fixed_full_legacy_closure_is_immutable_not_current_semantic_acceptance() -> None:
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
    assert sum(row.group_assignment_state == "unknown" for row in report.safety) == 414
    # Historical classification is not a licence to bypass the current semantic
    # boundary. Never rewrite the locked source/report to make it acceptable.
    with pytest.raises(PortalConsumerRegistrationError, match="measure_context"):
        project_b_safety_source_views(root, snapshot, report, versions)
    assert sha256((root / "state/project.sqlite").read_bytes()).hexdigest() == database_before
    assert sha256(report_path.read_bytes()).hexdigest() == (
        "9a13e4b867e0f27341a616409bdd179851d8467cf7b6cf411a04d54f5b39b45d"
    )
    assert sha256(receipt_path.read_bytes()).hexdigest() == (
        "67b55385f6d6f34405068517a3ecf66962098767a7c387aa84be089d82a90ea1"
    )


@pytest.mark.parametrize(
    ("project_relative", "receipt_name", "receipt_sha", "unknown_count", "prime2_state"),
    [
        (
            ".artifacts/1007-pn-current-project-v1",
            "owner-pn-current-four-study-materialize-v1.json",
            "8bb98259299f1032e585e984bf5452f6df947e3cd05c8cdcefc41660ecbae6b6",
            26,
            "unknown",
        ),
        (
            ".artifacts/1007-pn-source-v3-candidate/project",
            "owner-pn-current-four-study-materialize-v3.json",
            "be0f695a70aac210797380c1ab4b06459a60df050d1c335261747bd5a5b23e4c",
            22,
            "declared",
        ),
    ],
    ids=["immutable-v1-display", "current-v3-attribution"],
)
def test_source_revision_views_preserve_unknown_rows_and_full_b_query(
    tmp_path: Path,
    project_relative: str,
    receipt_name: str,
    receipt_sha: str,
    unknown_count: int,
    prime2_state: str,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    root = repo / project_relative
    receipt_path = repo / "runs/execution/ci-1007-display" / receipt_name
    if not receipt_path.is_file() or not (root / "state/project.sqlite").is_file():
        pytest.skip("pinned four-study source revision is not in this checkout")
    assert sha256(receipt_path.read_bytes()).hexdigest() == receipt_sha
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    report_path = root / receipt["bound_report_data"]["relative_path"]
    b_path = root / receipt["bound_b_report_data"]["relative_path"]
    assert sha256(report_path.read_bytes()).hexdigest() == receipt["bound_report_data"]["sha256"]
    assert sha256(b_path.read_bytes()).hexdigest() == receipt["bound_b_report_data"]["sha256"]
    report = ReportAPortalData.model_validate_json(report_path.read_bytes())
    bound_b = ReportBPortalData.model_validate_json(b_path.read_bytes())
    selected_ids = {row["row_id"] for row in bound_b.safety_views["facts"]}
    # This is the complete precise-view slice of four real studies, not an
    # assertion of universe/source completeness. All 189 related rows remain.
    assert len(selected_ids) == 36
    assert len(report.safety) == 189
    versions = {
        item["row_ref"]: item["fact_version_id"]
        for item in receipt["fact_bindings"]
        if item["row_ref"].startswith("safety:")
        and item["row_ref"].removeprefix("safety:") in selected_ids
    }
    assert {key.removeprefix("safety:") for key in versions} == selected_ids
    manifest_path = root / receipt["snapshot_relative_path"]
    assert sha256(manifest_path.read_bytes()).hexdigest() == receipt["snapshot_sha256"]
    snapshot = LockedSnapshot(
        snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"],
        relative_path=receipt["snapshot_relative_path"],
        byte_size=manifest_path.stat().st_size,
    )
    database_before = sha256((root / "state/project.sqlite").read_bytes()).hexdigest()
    views = project_b_safety_source_views(root, snapshot, report, versions)
    assert len(views) == 36
    assert sum(view["group_assignment_state"] == "unknown" for view in views) == unknown_count
    assert {view["row_id"] for view in views} == selected_ids
    prime2_ids = {
        "safe-45b7532dc2da8a8de661", "safe-e5e0b4524553ae12affb",
        "safe-1c409ad9a8b3e6c96a19", "safe-9e56eeec839114a66dd1",
    }
    assert prime2_ids <= selected_ids
    assert all(
        view["group_assignment_state"] == prime2_state
        for view in views if view["row_id"] in prime2_ids
    )
    if prime2_state == "declared":
        # The same rebuilt input includes PRISM, although precise-source
        # ingestion is limited to four other studies. Do not credit its source
        # closure here, but do prove the old placebo exposure is not retained.
        prism_placebo = [
            row for row in report.safety
            if row.trial_id == "nct03497975" and row.arm == "Placebo"
        ]
        assert len(prism_placebo) == 3
        assert all(row.group_assignment_state == "unknown" for row in prism_placebo)
    assert all(view["source_locator"]["field_path"] == view["source_field_path"] for view in views)
    assert all(view["unit"] == "人" and view["source_text"] is not None for view in views)
    assert all(
        view["source_locator"]["url"].startswith("https://clinicaltrials.gov/study/")
        for view in views
    )

    b_report = ReportBPortalData.model_validate({
        **report.model_dump(mode="json"),
        "safety_views": {"coverage_mode": "partial", "facts": views},
    })
    site = tmp_path / "full-b-safety"
    render_report_b_site(b_report, site)
    evidence = _page_json_assignment(site, "safety.html", "__EVIDENCE_VIEWS__")
    groups = _page_json_assignment(site, "safety.html", "__CHART_GROUPS__")
    by_id = {
        item["row"]["row_id"]: item for item in evidence
        if item["row"]["row_id"] in {view["row_id"] for view in views}
    }
    full_chart = {
        row["row_id"]: row for group in groups for row in group.get("rows", [])
        if row.get("_domain") == "safety"
    }
    assert set(full_chart) == {row.row_id for row in report.safety}
    assert len(full_chart) == 189
    assert set(by_id) == selected_ids
    assert len(by_id) == 36
    assert all(item["source_trace_state"] == "located" for item in by_id.values())
    for view in views:
        item = by_id[view["row_id"]]
        assert item["original_text"] == view["source_text"]
        if view["group_assignment_state"] == "unknown":
            assert item["row"]["product_id"] is None
            assert full_chart[view["row_id"]]["renderable"] is False
        assert full_chart[view["row_id"]]["value"] == view["value"]
    assert sha256((root / "state/project.sqlite").read_bytes()).hexdigest() == database_before
    assert sha256(report_path.read_bytes()).hexdigest() == receipt["bound_report_data"]["sha256"]
    assert sha256(b_path.read_bytes()).hexdigest() == receipt["bound_b_report_data"]["sha256"]
