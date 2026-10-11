"""Receipt-backed nineteen-fact adoption; retain history and committed current."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.review_issuer import verify_receipt_issuance
from ci_workflow.application.source_fact_acceptance import (
    accept_reviewed_source_facts,
    load_materialized_source_acceptance,
)

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
FORMAL = PROJECT / "runs/source-definition-formal-v4"
OUT = ROOT / ".artifacts/1007-source-definition-adoption-v4"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(encoded(value))


def database_state() -> tuple[dict[str, list[str]], dict[str, list[tuple[object, ...]]]]:
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        columns = {
            name: [row[1] for row in db.execute(
                'PRAGMA table_info("' + name.replace('"', '""') + '")')]
            for name in names
        }
        rows = {name: [tuple(row) for row in db.execute(
            'SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}
    return columns, rows


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing adoption journal: reopen result before any retry")
    terminal = json.loads((FORMAL / "issuer-terminal.json").read_bytes())
    assert terminal["exit_code"] == 0
    now = datetime.now(UTC)
    issued = verify_receipt_issuance(project_root=PROJECT, report_kind="A", checked_at=now)
    prepared = json.loads((FORMAL / "preparation.json").read_bytes())
    assert prepared["epoch"] == 2
    assert all(sha(ROOT / path) == digest
               for path, digest in prepared["production_source_hashes"].items())
    snapshot = prepared["evidence_snapshot"]
    assert snapshot["snapshot_id"] == "evidence-snapshot_f4750ceaf3d5587db9fee2e2"
    assert sha(PROJECT / snapshot["relative_path"]) == snapshot["sha256"]
    current_sha = sha(PROJECT / "reports/current.json")
    assert current_sha == prepared["current_sha256"]
    protected = {path: sha(path)
                 for directory in ("reports", "snapshots", "receipts", "state/scientific_review")
                 for path in (PROJECT / directory).rglob("*") if path.is_file()}
    columns, before = database_state()
    OUT.mkdir()
    with (
        sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db,
        sqlite3.connect(OUT / "database-before.sqlite") as backup,
    ):
        db.backup(backup)
    write("prewrite.json", {
        "state": "VALID_ISSUER_NORMAL_ADOPTION_READY_NOT_CURRENT",
        "receipt_digest": issued.receipt_digest, "snapshot": snapshot,
        "claim_snapshot_id": prepared["claim_snapshot_id"], "current_sha256": current_sha,
        "backup_sha256": sha(OUT / "database-before.sqlite"),
        "recipe_sha256": sha(Path(__file__)),
        "protected_files": {path.relative_to(PROJECT).as_posix(): digest
                            for path, digest in protected.items()},
    })
    try:
        result = accept_reviewed_source_facts(
            project_root=PROJECT, report_kind="A", evidence_snapshot_id=snapshot["snapshot_id"],
            claim_snapshot_id=prepared["claim_snapshot_id"], checked_at=now,
        )
        write("adoption-return.json", result.model_dump(mode="json"))
        assert load_materialized_source_acceptance(
            project_root=PROJECT, report_kind="A", evidence_snapshot_id=snapshot["snapshot_id"],
        ) == result
        after_columns, after = database_state()
        assert after_columns == columns
        for name, ids in (("fact_versions", result.accepted_fact_version_ids),
                          ("claim_versions", result.accepted_claim_version_ids)):
            state_index = columns[name].index("review_state")
            key_index = columns[name].index(
                "fact_version_id" if name == "fact_versions" else "claim_version_id")
            by_id = {row[key_index]: row for row in after[name]}
            assert len(by_id) == len(before[name])
            for old in before[name]:
                new = by_id[old[key_index]]
                assert old[:state_index] + old[state_index + 1:] == (
                    new[:state_index] + new[state_index + 1:])
                if old[key_index] in ids:
                    assert old[state_index] in {"candidate", "accepted"}
                    assert new[state_index] == "accepted"
                else:
                    assert old == new
        for name, rows in before.items():
            if name in {"fact_versions", "claim_versions"}:
                continue
            old, new = Counter(encoded(row) for row in rows), Counter(
                encoded(row) for row in after[name])
            assert not (old - new), name
            if name != "idempotency_keys":
                assert old == new, name
        assert all(sha(path) == digest for path, digest in protected.items())
        assert sha(PROJECT / "reports/current.json") == current_sha
        assert len(result.accepted_fact_version_ids) == 19
        write("verified.json", {
            "state": "NORMAL_NINETEEN_SOURCE_ADOPTION_ONLY_NOT_CURRENT",
            "accepted_facts": len(result.accepted_fact_version_ids),
            "accepted_claims": len(result.accepted_claim_version_ids),
            "scope_corrections": len(result.source_scope_corrections),
            "decision_digest": result.decision_digest,
            "old_scientific_material_user_layers_conflicts_bindings_preserved": True,
            "protected_file_count": len(protected), "current_sha256": current_sha,
            "finished_at": datetime.now(UTC).isoformat(),
            "limits": "No consumer/current/report/universe/freshness/coaxis/browser/RC acceptance",
        })
    except Exception as error:
        write("failure.json", {"state": "INSPECT_BEFORE_RETRY", "type": type(error).__name__,
                               "message": str(error)})
        raise
    print(encoded({"state": "SOURCE_ADOPTED_ONLY", "facts": 19,
                   "decision_digest": result.decision_digest}))


if __name__ == "__main__":
    main()
