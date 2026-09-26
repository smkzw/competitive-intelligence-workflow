"""Current captured CT.gov source, two reports, one hypothetical edit, no old-current switch."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_registry import register_b_shared_source_consumers
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import render_report_b_site
from ci_workflow.storage.snapshot_store import LockedSnapshot
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_w04_source_consumer_registry import _b_direct_source_view
from tools.materialize_ctgov_a_candidate import materialize

ROW_ID = "eff-9f54cd0202c1f000619a"
SOURCE_VERSION = "fact-version_fc4fd5ad5d1c3bafae8a3055"
OLD_CURRENT_SHA256 = "fd9ad81d4d7122dbfd3f1c15af75b5c0800ff2ca2de44aca58c0e906b6f5bca1"
AT = datetime(2026, 9, 26, 10, 5, tzinfo=UTC)


def test_current_capture_has_legitimate_a_b_fanout_without_migrating_old_project(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    source = repo / ".artifacts/r24-pnh-current-ctgov-20260926"
    old = repo / ".artifacts/r24-pnh-real-ab-20260926"
    payload = source / "report-a-ctgov-20260926-sponsor-separate-v5.json"
    sidecar = source / "report-a-ctgov-20260926-sponsor-separate-v5.derivation.json"
    if not all(path.exists() for path in (payload, sidecar, old / "project.yaml")):
        pytest.skip("pinned current source or old development project unavailable")
    old_db = old / "state/project.sqlite"
    assert hashlib.sha256(old_db.read_bytes()).hexdigest() == OLD_CURRENT_SHA256
    root = tmp_path / "current-source-ab-development"
    contract = verify_project_workspace(old).contract
    create_project_workspace(root, contract)
    a_input = root / "inputs/r24-46-a-bound.json"
    receipt = materialize(
        project_root=root,
        cas_dir=source,
        payload_path=payload,
        sidecar_path=sidecar,
        observed_at=AT,
        selected_trials={"nct04820530"},
        bound_report_output=a_input,
    )
    assert receipt["counts"]["registered_a_efficacy_consumers"] == 18
    assert receipt["source_pages"]["nct04820530"] == (
        "342612879ac3dcab9c4fa226133a85fbe4d7dafe9ce426483f7e211f280177f9"
    )
    versions = {item["row_ref"]: item["fact_version_id"]
                for item in receipt["fact_bindings"]}
    assert versions[f"efficacy:{ROW_ID}"] == SOURCE_VERSION
    snapshot_file = root / receipt["snapshot_relative_path"]
    snapshot = LockedSnapshot(
        snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"],
        relative_path=receipt["snapshot_relative_path"],
        byte_size=snapshot_file.stat().st_size,
    )
    a_report = ReportAPortalData.model_validate_json(a_input.read_bytes())
    with open_database(root / "state/project.sqlite") as database:
        locator, quote = database.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (SOURCE_VERSION,),
        ).fetchone()
    assert quote == "92.2"
    b_report = _b_direct_source_view(a_report, locator, source_text=quote)
    assert b_report.model_dump(mode="json")["efficacy_views"]["facts"][0]["row_id"] == ROW_ID
    b_binding = register_b_shared_source_consumers(
        root, snapshot, b_report, {f"efficacy:{ROW_ID}": SOURCE_VERSION},
        registered_at=AT,
    )[0]
    assert (b_binding.report, b_binding.source_version_id) == (
        "B", receipt["source_version_ids"][0],
    )
    with open_database(root / "state/project.sqlite") as database:
        registered = database.execute(
            "SELECT source_fact_version_id FROM source_portal_consumer_bindings "
            "WHERE report='B' AND collection='efficacy' AND row_id=?",
            (ROW_ID,),
        ).fetchone()
    assert registered == (SOURCE_VERSION,)

    b_input = root / "inputs/r24-46-b-direct-source.json"
    b_input.write_text(b_report.model_dump_json(), encoding="utf-8")
    sites = {"A": root / "reports/A/development/html",
             "B": root / "reports/B/development/html"}
    render_report_a_site(a_report, sites["A"])
    render_report_b_site(b_report, sites["B"])
    service = UserFactEditService(root)
    service.initialize_current_delivery(
        project_id=contract.project_id, report_sites=sites,
        report_data_paths={"A": a_input, "B": b_input},
        fact_version_ids=tuple(
            versions[f"efficacy:{row_id}"]
            for row_id in receipt["registered_a_efficacy_consumers"]
        ),
        created_at=AT,
    )
    fact = service._fact_row(SOURCE_VERSION)
    command = UserFactSaveCommand(
        request_id="r24-46-current-cas-ab-hypothetical-edit",
        project_id=contract.project_id, expected_revision=0,
        target=FactTargetIdentity(
            fact_id=fact["fact_id"], fact_version_id=SOURCE_VERSION,
            entity_id=fact["entity_id"], field_id=fact["field_id"],
        ),
        edits=FactEdit(raw_value="90.1", normalized_value=90.1),
        user_basis="开发演练假设值，非医学订正", saved_by="test", saved_at=AT,
    )
    saved = service.save(command)
    assert saved.rebuilt_reports == ("A", "B")
    current = service.read_current_delivery()
    assert current is not None and current.revision == 1
    for item in current.reports:
        site = root / item.site_relative_path
        projection = json.loads(
            (site / "data/report.js").read_text(encoding="utf-8")
            .split("=", 1)[1].rstrip(" ;\n")
        )
        row = next(value for value in projection["efficacy"] if value["row_id"] == ROW_ID)
        assert row["value"] == 90.1 and row["source_text"] == "92.2"
        assert row["source_version_id"] == receipt["source_version_ids"][0]
        assert projection["user_edits"][ROW_ID]["original_value"] == (
            "92.2 Percentage of responders"
        )
        if item.report == "B":
            html = (site / "efficacy.html").read_text(encoding="utf-8")
            evidence = json.loads(
                html.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].split(";\n", 1)[0]
            )
            assert evidence[0]["user_edit"]["original_value"] == (
                "92.2 Percentage of responders"
            )
            assert "Day 126 and Day 168" in evidence[0]["timepoint"]["value"]
    assert hashlib.sha256(old_db.read_bytes()).hexdigest() == OLD_CURRENT_SHA256
