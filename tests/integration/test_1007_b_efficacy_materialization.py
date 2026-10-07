"""Ordinary source materialization must connect B, not just a stand-alone helper.

Fixed real four-study vertical slice; missing local raw corpus is SKIP, never
scientific acceptance. No rendering/current promotion or external source access.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from ci_workflow.storage.sqlite import open_database
from tools.materialize_ctgov_a_candidate import materialize


def test_ordinary_materializer_registers_partial_shared_efficacy_without_losing_pool(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    cas = repo / ".artifacts/1007-pn-current-source-v1"
    payload = cas / "a-source-payload-v3.json"
    sidecar = cas / "a-source-payload-v3.derivation.json"
    if not payload.is_file() or not sidecar.is_file():
        pytest.skip("fixed real PN source corpus unavailable; not accepted")
    source_bytes = {p.name: sha256(p.read_bytes()).hexdigest() for p in (payload, sidecar)}
    # Rebuild from the pinned original raw page using CURRENT extraction rules;
    # old v3 rows are historical inputs, not a new source-correctness acceptance.
    descriptor = json.loads((cas / "raw-descriptor.json").read_bytes())
    raw = (cas / descriptor["relative_path"]).read_bytes()
    assert sha256(raw).hexdigest() == descriptor["sha256"]
    replay = tmp_path / "replay/evidence/raw"
    replay.mkdir(parents=True)
    (replay / "source.bin").write_bytes(raw)
    rebuilt = tmp_path / "rebuilt.json"
    subprocess.run([
        sys.executable, str(repo / "tools/build_a_payload.py"),
        "--cas-dir", str(tmp_path / "replay"),
        "--alias-map", str(cas / "empty-source-alias-map.json"),
        "--indication", "结节性痒疹", "--indication-id", "pn",
        "--cutoff", "2026-10-07", "--output", str(rebuilt),
    ], check=True, capture_output=True, text=True, cwd=repo)
    payload_input = rebuilt
    sidecar_input = tmp_path / "rebuilt.derivation.json"
    original = ReportAPortalData.model_validate_json(payload_input.read_bytes())
    at = datetime(2026, 10, 7, 9, 50, 52, 585475, tzinfo=UTC)
    contract = create_project_contract(indication=original.indication, reports=["A", "B"],
        outputs=["html"], cutoff="2026-10-07", created_at=at)
    root = tmp_path / "real-source-bridge"
    create_project_workspace(root, contract)
    a_path, b_path = root / "inputs/a.json", root / "inputs/b.json"
    receipt = materialize(project_root=root, cas_dir=cas, payload_path=payload_input,
        sidecar_path=sidecar_input, observed_at=at,
        selected_trials={"nct04183335", "nct04202679", "nct04501666", "nct04501679"},
        bound_report_output=a_path, bound_b_report_output=b_path)
    a = ReportAPortalData.model_validate_json(a_path.read_bytes())
    b = ReportBPortalData.model_validate_json(b_path.read_bytes())
    assert b.efficacy_views, "ordinary B input has no precise efficacy source views"
    assert b.efficacy_views["coverage_mode"] == "partial"
    views = b.efficacy_views["facts"]
    expected = set(receipt["registered_a_efficacy_consumers"])
    assert len(expected) == 91
    assert {view["row_id"] for view in views} == expected
    assert len(views) == len(expected)
    assert {row.row_id for row in b.efficacy} == {row.row_id for row in original.efficacy}
    assert len(b.efficacy) == 3544
    assert b.efficacy == a.efficacy
    assert {view["source_fact_version_id"] for view in views} <= set(
        receipt["fact_version_ids"])
    assert all(view["source_text"] and view["source_locator"] for view in views)
    assert receipt["counts"]["located_b_efficacy_source_views"] == 91
    assert set(receipt["registered_b_efficacy_consumers"]) == expected
    with open_database(root / "state/project.sqlite") as database:
        a_ids = database.execute("SELECT source_fact_version_id FROM "
            "source_portal_consumer_bindings WHERE report='A' AND collection='efficacy'").fetchall()
        b_ids = database.execute("SELECT source_fact_version_id FROM "
            "source_portal_consumer_bindings WHERE report='B' AND collection='efficacy'").fetchall()
        assert set(a_ids) == set(b_ids) and len(b_ids) == 91
        assert database.execute("SELECT COUNT(*) FROM user_fact_edit_requests").fetchone()[0] == 0
    assert not (root / "reports/current.json").exists()
    assert {p.name: sha256(p.read_bytes()).hexdigest() for p in (payload, sidecar)} == source_bytes
