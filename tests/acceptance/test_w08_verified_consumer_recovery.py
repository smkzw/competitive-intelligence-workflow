"""Opt-in fixed-source acceptance probe for registered consumer portability.

This test is not part of the fast development gate.  It requires two ignored,
fixed offline CT.gov development projects; missing inputs are SKIP, not PASS.
The source projects are opened read-only and all recovery writes are temporary.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_binding_recovery import (
    export_verified_consumer_bindings,
    recover_verified_consumer_bindings,
)
from ci_workflow.application.verified_candidate_recovery import (
    restore_verified_candidate,
    seal_verified_candidate,
)
from ci_workflow.storage.snapshot_store import SnapshotStore, compute_locked_snapshot

REPOSITORY = Path(__file__).resolve().parents[2]
CASES = (
    (
        "r24-pnh-real-ab-20260926",
        "evidence-snapshot_68fd97a331040c3637068faf",
        "36791d7ed49ff5d8d3eb4759556a6d4d3f907710030e22d1c3ed479d712a10f1",
        {"A": 18, "B": 1},
        "6e113cd9cedb14f77d857b4f1349b236c20880b37bb25c1c028688e8a41ccdb4",
    ),
    (
        "r24-pnh-auto-binding-full-20260926",
        "evidence-snapshot_df4bb81e97d8f0eae2fb3f7a",
        "0443339f94cdb54678e213182afaa82db4c6b4285656d880a7198f57964ec14d",
        {"A": 1206},
        "ebacfba447d8ba1d15c04ef3f67e8f97f5aaff9b2467ef94637fe39bd55a8c44",
    ),
)


@pytest.mark.parametrize(
    ("project_name", "snapshot_id", "snapshot_digest", "expected_counts", "sidecar_digest"),
    CASES,
)
def test_fixed_candidate_restores_only_verified_registry_rows(
    project_name: str,
    snapshot_id: str,
    snapshot_digest: str,
    expected_counts: dict[str, int],
    sidecar_digest: str,
) -> None:
    project = REPOSITORY / ".artifacts" / project_name
    manifest = project / "snapshots/evidence" / f"{snapshot_id}.json"
    database_path = project / "state/project.sqlite"
    if not manifest.is_file() or not database_path.is_file():
        pytest.skip("fixed offline source project is not present in this checkout")
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == snapshot_digest
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    locked = compute_locked_snapshot(kind="evidence", report=None, manifest=payload)
    assert locked.snapshot_id == snapshot_id and locked.sha256 == snapshot_digest

    with tempfile.TemporaryDirectory(prefix="ci-w08-binding-recovery-") as directory:
        work = Path(directory)
        source_copy = work / "source"
        snapshot_copy = source_copy / locked.relative_path
        snapshot_copy.parent.mkdir(parents=True)
        shutil.copy2(manifest, snapshot_copy)
        database_copy = source_copy / "state/project.sqlite"
        database_copy.parent.mkdir(parents=True)
        with sqlite3.connect(
            f"file:{database_path.resolve()}?mode=ro", uri=True
        ) as original:
            with sqlite3.connect(database_copy) as copied:
                original.backup(copied)
            expected = original.execute(
                "SELECT binding_id,binding_json,binding_sha256 "
                "FROM source_portal_consumer_bindings WHERE evidence_snapshot_id=? "
                "ORDER BY binding_id", (snapshot_id,),
            ).fetchall()

        sidecar = work / "verified-bindings.json"
        exported = export_verified_consumer_bindings(source_copy, locked, sidecar)
        assert hashlib.sha256(sidecar.read_bytes()).hexdigest() == sidecar_digest
        target = work / "restored"
        SnapshotStore(target).restore_evidence_manifest(manifest)
        with sqlite3.connect(target / "state/project.sqlite") as restored:
            assert restored.execute(
                "SELECT count(*) FROM source_portal_consumer_bindings"
            ).fetchone()[0] == 0
        recovered = recover_verified_consumer_bindings(target, sidecar)
        assert recovered == exported
        assert recover_verified_consumer_bindings(target, sidecar) == recovered
        with sqlite3.connect(target / "state/project.sqlite") as restored:
            actual = restored.execute(
                "SELECT binding_id,binding_json,binding_sha256 "
                "FROM source_portal_consumer_bindings WHERE evidence_snapshot_id=? "
                "ORDER BY binding_id", (snapshot_id,),
            ).fetchall()
            counts = dict(restored.execute(
                "SELECT report,count(*) FROM source_portal_consumer_bindings GROUP BY report"
            ).fetchall())
        assert actual == expected
        assert counts == expected_counts

        candidate_manifest = work / "candidate-recovery.json"
        candidate_digest = seal_verified_candidate(
            source_copy, locked, sidecar, candidate_manifest
        )
        atomic_target = work / "atomic-restored"
        atomic_locked, atomic_bindings = restore_verified_candidate(
            candidate_manifest, manifest, sidecar, atomic_target,
            expected_manifest_sha256=candidate_digest,
        )
        assert atomic_locked == locked
        assert atomic_bindings == exported
        with sqlite3.connect(atomic_target / "state/project.sqlite") as atomic_db:
            atomic_rows = atomic_db.execute(
                "SELECT binding_id,binding_json,binding_sha256 "
                "FROM source_portal_consumer_bindings WHERE evidence_snapshot_id=? "
                "ORDER BY binding_id", (snapshot_id,),
            ).fetchall()
        assert atomic_rows == expected
