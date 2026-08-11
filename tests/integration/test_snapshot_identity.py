from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> Draft202012Validator:
    payload = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return Draft202012Validator(payload, format_checker=FormatChecker())


def test_snapshot_identity_is_content_stable_and_immutable(tmp_path: Path) -> None:
    from ci_workflow.storage.snapshot_store import (
        SnapshotIntegrityError,
        SnapshotStore,
    )

    project_root = tmp_path / "项目"
    store = SnapshotStore(project_root)
    evidence = {
        "schema_version": "1.0",
        "project_id": "project_001",
        "contract_version": 1,
        "data_cutoff": "2026-08-10T23:59:59.999999+08:00",
        "source_version_ids": ["source-version_001"],
        "fragment_ids": ["fragment_001"],
        "fact_version_ids": ["fact-version_001"],
        "created_at": "2026-08-11T20:55:00+08:00",
    }
    first = store.lock_evidence_snapshot(evidence)
    same = store.lock_evidence_snapshot(evidence)
    changed = store.lock_evidence_snapshot(
        {**evidence, "fact_version_ids": ["fact-version_001", "fact-version_002"]}
    )
    assert same == first
    assert changed.snapshot_id != first.snapshot_id
    assert changed.relative_path != first.relative_path
    assert store.read(first) == evidence
    _schema("evidence-snapshot-manifest.schema.json").validate(store.read(first))

    report = store.lock_report_snapshot(
        report="B",
        manifest={
            "schema_version": "1.0",
            "project_id": "project_001",
            "contract_version": 1,
            "report": "B",
            "report_version": "v1",
            "data_cutoff": "2026-08-10T23:59:59.999999+08:00",
            "evidence_snapshot_id": first.snapshot_id,
            "claim_snapshot_id": "claim-snapshot_001",
            "coverage_set_id": "coverage-set_001",
            "claim_ids": ["claim_001"],
            "created_at": "2026-08-11T20:56:00+08:00",
        },
    )
    assert store.read(report)["evidence_snapshot_id"] == first.snapshot_id
    _schema("report-snapshot-manifest.schema.json").validate(store.read(report))

    moved_root = tmp_path / "已移动项目"
    project_root.rename(moved_root)
    moved_store = SnapshotStore(moved_root)
    assert moved_store.read(first) == evidence

    path = moved_root / first.relative_path
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        moved_store.read(first)
