"""One normal receipt-backed source adoption; never retry an existing attempt."""

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
FORMAL = PROJECT / "runs/scoped-source-formal-v2"
OUT = ROOT / ".artifacts/1007-scoped-source-union-adoption-v2"
CURRENT_SHA = "7336654514605085b9ee86e3fedaa664e83406f0c358125fa653683767374d24"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        stream.write(canonical(value))


def database_state() -> tuple[dict[str, list[str]], dict[str, list[tuple[object, ...]]]]:
    with sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        columns = {
            n: [r[1] for r in db.execute('PRAGMA table_info("' + n.replace('"', '""') + '")')]
            for n in names
        }
        rows = {
            n: [tuple(r) for r in db.execute('SELECT * FROM "' + n.replace('"', '""') + '"')]
            for n in names
        }
    return columns, rows


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing adoption attempt: reopen return/decision; never blind retry")
    now = datetime.now(UTC)
    issued = verify_receipt_issuance(project_root=PROJECT, report_kind="A", checked_at=now)
    prepared = json.loads((FORMAL / "preparation.json").read_bytes())
    assert prepared["epoch"] == 1
    snapshot = prepared["evidence_snapshot"]
    assert snapshot["sha256"] == "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237"
    assert sha(PROJECT / snapshot["relative_path"]) == snapshot["sha256"]
    assert sha(PROJECT / "reports/current.json") == CURRENT_SHA
    protected = {
        p: sha(p)
        for directory in ("reports", "snapshots", "receipts", "state/scientific_review")
        for p in (PROJECT / directory).rglob("*")
        if p.is_file()
    }
    columns, before = database_state()
    OUT.mkdir()
    backup = OUT / "database-before.sqlite"
    with (
        sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True) as db,
        sqlite3.connect(backup) as target,
    ):
        db.backup(target)
    write(
        "prewrite.json",
        {
            "status": "VALID_ISSUANCE_NORMAL_ADOPTION_READY_NOT_CURRENT",
            "receipt_digest": issued.receipt_digest,
            "snapshot": snapshot,
            "claim_snapshot_id": prepared["claim_snapshot_id"],
            "current_sha256": CURRENT_SHA,
            "backup_sha256": sha(backup),
            "protected_files": {p.relative_to(PROJECT).as_posix(): h for p, h in protected.items()},
            "tables_before": {
                n: dict(Counter(canonical(r) for r in rows)) for n, rows in before.items()
            },
        },
    )
    try:
        result = accept_reviewed_source_facts(
            project_root=PROJECT,
            report_kind="A",
            evidence_snapshot_id=snapshot["snapshot_id"],
            claim_snapshot_id=prepared["claim_snapshot_id"],
            checked_at=now,
        )
        # A postcondition failure must reopen this result, never repeat adoption.
        write("adoption-return.json", result.model_dump(mode="json"))
        reopened = load_materialized_source_acceptance(
            project_root=PROJECT,
            report_kind="A",
            evidence_snapshot_id=snapshot["snapshot_id"],
        )
        assert reopened == result
        after_columns, after = database_state()
        assert after_columns == columns
        for name, ids in (
            ("fact_versions", result.accepted_fact_version_ids),
            ("claim_versions", result.accepted_claim_version_ids),
        ):
            state_index = columns[name].index("review_state")
            key_index = columns[name].index(
                "fact_version_id" if name == "fact_versions" else "claim_version_id"
            )
            after_by_id = {r[key_index]: r for r in after[name]}
            assert len(after_by_id) == len(before[name])
            for old in before[name]:
                new = after_by_id[old[key_index]]
                assert old[:state_index] + old[state_index + 1 :] == (
                    new[:state_index] + new[state_index + 1 :]
                )
                if old[key_index] in ids:
                    assert old[state_index] in ("accepted", "candidate")
                    assert new[state_index] == "accepted"
                else:
                    assert old == new
        for name, rows in before.items():
            if name in ("fact_versions", "claim_versions"):
                continue
            old, new = (
                Counter(canonical(r) for r in rows),
                Counter(canonical(r) for r in after[name]),
            )
            assert not (old - new), name
            if name != "idempotency_keys":
                assert old == new, name
        assert all(sha(p) == h for p, h in protected.items())
        assert sha(PROJECT / "reports/current.json") == CURRENT_SHA
        assert len(result.accepted_fact_version_ids) == 3989
        write(
            "verified.json",
            {
                "status": "NORMAL_SOURCE_ADOPTION_ONLY_NOT_CURRENT_NOT_REPORT_ACCEPTANCE",
                "accepted_facts": len(result.accepted_fact_version_ids),
                "accepted_claims": len(result.accepted_claim_version_ids),
                "boundary_claims": len(result.boundary_claim_version_ids),
                "scope_corrections": len(result.source_scope_corrections),
                "decision_digest": result.decision_digest,
                "original_scientific_rows_user_layers_conflicts_bindings_preserved": True,
                "protected_files": len(protected),
                "current_sha256": CURRENT_SHA,
                "database_after_sha256": sha(PROJECT / "state/project.sqlite"),
                "finished_at": datetime.now(UTC).isoformat(),
                "limits": "No consumers/current/new report/universe/freshness/coaxis/RC acceptance",
            },
        )
    except Exception as error:
        write(
            "failure.json",
            {
                "status": "FAILED_REOPEN_BEFORE_RETRY",
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
        raise
    print(canonical({"status": "SOURCE_ADOPTED_ONLY", "decision_digest": result.decision_digest}))


if __name__ == "__main__":
    main()
