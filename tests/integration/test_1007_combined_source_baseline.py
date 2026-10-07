"""The existing A/B source builder, not only a preview, must consume baseline atoms."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from tools.materialize_ctgov_a_candidate import materialize

ROOT = Path(__file__).resolve().parents[2]


def test_existing_combined_builder_sources_all_selected_baseline_observations(tmp_path) -> None:
    source = ROOT / ".artifacts/1007-pn-current-source-v1"
    payload = source / "a-source-payload-v3.json"
    sidecar = source / "a-source-payload-v3.derivation.json"
    if not payload.is_file() or not sidecar.is_file():
        pytest.skip("fixed source-set absent; this is NOT_RUN, not universe/scientific acceptance")
    before = {p: sha256(p.read_bytes()).hexdigest() for p in (payload, sidecar)}
    root = tmp_path / "combined-new-project"
    at = datetime(2026, 10, 7, 9, 50, 52, 585475, tzinfo=UTC)
    contract = create_project_contract(indication="结节性痒疹", reports=["A", "B", "C"],
                                       outputs=["html"], cutoff="2026-10-07", created_at=at)
    create_project_workspace(root, contract)
    b_output = root / "evidence/library/b-source-current.json"
    receipt = materialize(project_root=root, cas_dir=source, payload_path=payload,
        sidecar_path=sidecar, observed_at=at,
        selected_trials={"nct04202679", "nct04183335", "nct04501666", "nct04501679"},
        bound_b_report_output=b_output)
    b = json.loads(b_output.read_bytes())
    rows = b["baseline_views"]["facts"]
    assert len(rows) == 183 and len({r["row_id"] for r in rows}) == 183
    assert receipt["counts"]["baseline_numeric_atoms"] == 183
    assert receipt["counts"]["baseline_source_facts"] == 499
    assert receipt["baseline_source_issues"] == []
    eligible_ids = {r["row_id"] for r in rows if r["value"] is not None and r["unit"]
                    and r["statistic_form"] in {
                        "MEAN", "MEDIAN", "STANDARD_DEVIATION", "count", "下限", "上限", "NUMBER",
                    }}
    assert len(eligible_ids) > 24  # previous scalar coverage remains, now including n/N
    assert receipt["counts"]["registered_b_baseline_scalar_consumers"] == len(eligible_ids)
    assert set(receipt["baseline_edit_consumers"]) == eligible_ids
    assert len(eligible_ids) == 183  # six real NUMBER atoms remain NUMBER, not inferred counts
    assert "count_denominator" in receipt["baseline_edit_scope"]
    assert "no_implicit_rate" in receipt["baseline_edit_scope"]
    non_editable = receipt["non_editable_baseline_rows"]
    assert {r["row_id"] for r in non_editable} == {r["row_id"] for r in rows} - eligible_ids
    assert all(r["reason"] for r in non_editable)
    locked = LockedSnapshot(snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"], relative_path=receipt["snapshot_relative_path"],
        byte_size=(root / receipt["snapshot_relative_path"]).stat().st_size)
    snapshot = SnapshotStore(root).read(locked)
    assert all(r["source_fact_version_id"] in snapshot["fact_version_ids"] for r in rows)
    assert all(r["source_version_id"] in snapshot["source_version_ids"] for r in rows)
    assert all(r["product_id"] is None and r["arm_role"] == "unknown" for r in rows)
    assert sum(r["source_value_role"] == "dispersion" for r in rows) == 12
    assert read_current_delivery(root) is None
    assert {p: sha256(p.read_bytes()).hexdigest() for p in before} == before
