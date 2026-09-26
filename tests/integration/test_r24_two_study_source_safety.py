"""Pinned CT.gov multi-study candidate: explicit zero is not an inferred zero."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_registry import (
    PortalConsumerRegistrationError,
    register_a_source_consumers,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from ci_workflow.storage.snapshot_store import LockedSnapshot
from ci_workflow.storage.sqlite import open_database
from tools.materialize_ctgov_a_candidate import materialize


def test_two_study_source_safety_binds_only_declared_original_counts(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    cas = repo / ".artifacts/r24-pnh-current-ctgov-20260926"
    payload = cas / "report-a-ctgov-20260926-sponsor-separate-v5.json"
    sidecar = cas / "report-a-ctgov-20260926-sponsor-separate-v5.derivation.json"
    previous = repo / ".artifacts/r24-pnh-refresh-slice-20260926"
    if not all(path.exists() for path in (cas, payload, sidecar, previous)):
        pytest.skip("fixed 2026-09-26 CT.gov source corpus is not in this checkout")
    assert sha256(payload.read_bytes()).hexdigest() == (
        "3ae2a238733eb06269c2fd58c171e4f6a1a3b8c97bc3a7069beec88ca08c952a"
    )
    assert sha256(sidecar.read_bytes()).hexdigest() == (
        "0ef8a7275bab87eccc4e0a296744b8ae624a0771ca1d082300a1fa081b78d655"
    )
    root = tmp_path / "two-study-source-candidate"
    create_project_workspace(root, verify_project_workspace(previous).contract)
    bound_input = root / "inputs/a-bound.json"
    b_input = root / "inputs/b-partial-source.json"
    observed_at = datetime(2026, 9, 26, 10, 5, tzinfo=UTC)
    receipt = materialize(
        project_root=root,
        cas_dir=cas,
        payload_path=payload,
        sidecar_path=sidecar,
        observed_at=observed_at,
        selected_trials={"nct02264639", "nct03829449"},
        bound_report_output=bound_input,
        bound_b_report_output=b_input,
    )
    assert receipt["raw_paths_verified"] == 190
    assert receipt["counts"]["facts"] == 374
    assert receipt["counts"]["registered_a_efficacy_consumers"] == 71
    assert receipt["counts"]["registered_a_safety_consumers"] == 2
    assert receipt["counts"]["located_b_safety_source_views"] == 92
    assert receipt["bound_b_report_data"]["sha256"] == sha256(b_input.read_bytes()).hexdigest()
    assert set(receipt["registered_a_safety_consumers"]) == {
        "safe-9fe1ea2f8b52dd3ec294",  # seriousNumAffected = 3
        "safe-7727c2ce1c1803f54bb0",  # deathsNumAffected = explicit 0
    }
    assert receipt["source_issue_statuses"] == {"missing": 1}

    report = ReportAPortalData.model_validate_json(bound_input.read_bytes())
    selected_safety = tuple(
        row for row in report.safety
        if row.trial_id in {"nct02264639", "nct03829449"}
    )
    assert len(selected_safety) == 92
    assert sum(row.value == 0 for row in selected_safety) == 43
    assert sum(row.group_assignment_state == "unknown" for row in selected_safety) == 90
    assert sum(row.denominator is None for row in selected_safety) == 26
    b_report = ReportBPortalData.model_validate_json(b_input.read_bytes())
    assert b_report.safety_views is not None
    assert b_report.safety_views["coverage_mode"] == "partial"
    b_views = b_report.safety_views["facts"]
    assert len(b_views) == 92
    assert sum(view["group_assignment_state"] == "unknown" for view in b_views) == 90
    assert all(
        view["source_locator"]["field_path"] == view["source_field_path"]
        for view in b_views
    )
    versions = {
        item["row_ref"]: item["fact_version_id"] for item in receipt["fact_bindings"]
    }
    with open_database(root / "state/project.sqlite") as database:
        registered = database.execute(
            "SELECT row_id, source_fact_version_id FROM source_portal_consumer_bindings "
            "WHERE report='A' AND collection='safety' ORDER BY row_id"
        ).fetchall()
        assert {row[0] for row in registered} == set(receipt["registered_a_safety_consumers"])
        assert {row[1] for row in registered} == {
            versions[f"safety:{row_id}"]
            for row_id in receipt["registered_a_safety_consumers"]
        }
        zero_source = database.execute(
            "SELECT v.raw_value,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?",
            (versions["safety:safe-7727c2ce1c1803f54bb0"],),
        ).fetchone()
        assert tuple(zero_source) == ("0", "0")

    manifest_path = root / receipt["snapshot_relative_path"]
    snapshot = LockedSnapshot(
        snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"],
        relative_path=receipt["snapshot_relative_path"],
        byte_size=manifest_path.stat().st_size,
    )
    unknown = next(row for row in selected_safety if row.group_assignment_state == "unknown")
    with pytest.raises(PortalConsumerRegistrationError, match="组别—产品归属"):
        register_a_source_consumers(
            root, snapshot, report,
            {f"safety:{unknown.row_id}": versions[f"safety:{unknown.row_id}"]},
            registered_at=observed_at,
        )
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings "
            "WHERE report='A' AND collection='safety'"
        ).fetchone()[0] == 2
        assert database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings WHERE report='B'"
        ).fetchone()[0] == 0
