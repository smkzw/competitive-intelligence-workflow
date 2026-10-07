"""Persist exact baseline source atoms using existing CAS/snapshot ingestion."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from tools.materialize_ctgov_baseline_candidate import materialize
from tools.render_baseline_source_candidate import build_preview


def _raw(root: Path):
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT12345678", "briefTitle": "Fixed source"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-10-01"}},
        },
        "resultsSection": {"baselineCharacteristicsModule": {
            "populationDescription": " All randomized participants. ",
            "groups": [{"id": "BG0", "title": "Total",
                        "description": "Total of all reporting groups"}],
            "denoms": [{"units": "Participants", "counts": [{"groupId": "BG0", "value": "0"}]}],
            "measures": [{"title": "Age", "paramType": "MEAN", "unitOfMeasure": "Years",
                          "classes": [{"categories": [{"measurements": [
                              {"groupId": "BG0", "value": "50"},
                          ]}]}]}],
        }},
    }
    raw = json.dumps({"studies": [record]}).encode()
    blob = ContentAddressedStore(root).put_bytes(raw, media_type="application/json")
    return raw, blob


def test_baseline_candidate_reopens_snapshot_and_never_switches_current(tmp_path: Path) -> None:
    source = tmp_path / "source"
    raw, blob = _raw(source)
    before = {p.relative_to(source).as_posix(): p.read_bytes()
              for p in source.rglob("*") if p.is_file()}
    output = tmp_path / "candidate"
    receipt = materialize(source_root=source, raw_asset=blob, output=output,
                          trial_ids=("nct12345678",), indication="结节性痒疹",
                          cutoff="2026-10-07", observed_at=datetime(2026, 10, 7, tzinfo=UTC))
    assert receipt["raw_asset"]["sha256"] == blob.sha256
    assert receipt["sources"] == 1 and receipt["numeric_atoms"] == 2
    assert receipt["scientific_acceptance"] == "not_accepted"
    assert receipt["current_generation_switched"] is False
    root = output / "project"
    assert not (root / "state/current.json").exists()
    locked = LockedSnapshot.model_validate(receipt["snapshot"])
    snapshot = SnapshotStore(root).read(locked)
    assert len(snapshot["fact_version_ids"]) == receipt["facts"]
    stored = json.loads((output / "facts.json").read_text())
    assert any(f["original_text"] == " All randomized participants. " for f in stored)
    assert any(f["raw_value"] == "0" and f["disclosure_state"] == "reported_zero" for f in stored)
    assert all(f.get("result_context", {}).get("arm", "unknown") == "unknown" for f in stored)
    assert {p.relative_to(source).as_posix(): p.read_bytes()
            for p in source.rglob("*") if p.is_file()} == before
    assert ContentAddressedStore(root).read_bytes(blob) == raw


@pytest.mark.parametrize("trials", [("NCT12345678", "nct12345678"), ("NCT99999999",)])
def test_bad_requested_study_set_fails_before_output_creation(tmp_path: Path, trials) -> None:
    source = tmp_path / "source"
    _, blob = _raw(source)
    output = tmp_path / "candidate"
    with pytest.raises(ValueError, match="研究"):
        materialize(source_root=source, raw_asset=blob, output=output, trial_ids=trials,
                    indication="结节性痒疹", cutoff="2026-10-07",
                    observed_at=datetime(2026, 10, 7, tzinfo=UTC))
    assert not output.exists()


def test_ordinary_preview_preserves_snapshot_and_explicit_source_version(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _, blob = _raw(source)
    candidate = tmp_path / "candidate"
    manifest = materialize(source_root=source, raw_asset=blob, output=candidate,
        trial_ids=("NCT12345678",), indication="结节性痒疹", cutoff="2026-10-07",
        observed_at=datetime(2026, 10, 7, tzinfo=UTC))
    before = {p.relative_to(candidate).as_posix(): p.read_bytes()
              for p in candidate.rglob("*") if p.is_file()}
    output = tmp_path / "preview"
    receipt = build_preview(candidate, output)
    assert receipt["source_numeric_atoms"] == 2 and receipt["pages"] > 1
    assert receipt["source_snapshot_sha256"] == manifest["snapshot"]["sha256"]
    assert receipt["current_generation_switched"] is False
    assert receipt["browser_acceptance"] == "not_run"
    payload = json.loads((output / "report-data.json").read_bytes())
    assert payload["related_studies"][0]["product_id"] is None
    rows = payload["baseline_views"]["facts"]
    assert {r["source_version_id"] for r in rows} == set(manifest["source_version_ids"])
    assert all(r["source_clause_context"]["continuations"] for r in rows)
    html = (output / "html/baseline-overview.html").read_text()
    assert "全研究横比" in html
    assert {p.relative_to(candidate).as_posix(): p.read_bytes()
            for p in candidate.rglob("*") if p.is_file()} == before
