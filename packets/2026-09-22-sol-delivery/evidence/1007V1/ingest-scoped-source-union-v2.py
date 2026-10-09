"""One normal candidate-only ingestion; preserve old rows and committed current.

Never re-run an existing attempt. Reopen its journal, receipt and backup instead.
This is not scientific acceptance, a freshness check or a report/current switch.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.fresh_research_ingestion import (
    _validate_references,
    ingest_research_evidence,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.application.user_fact_edit import current_delivery_lock
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.source_derivation import (
    extract_locator_quote,
    verify_source_text_derivation,
)

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
INPUT = ROOT / ".artifacts/1007-scoped-source-union-preparation-v2/source-package.json"
PROOF = INPUT.parent / "proof.json"
OUT = ROOT / ".artifacts/1007-scoped-source-union-ingestion-v2"
PACKAGE_SHA = "7d4fc6006cc520e9b9923f2b909c0df907bc6da5a0cdd2e558898abb99447654"
CURRENT_SHA = "7336654514605085b9ee86e3fedaa664e83406f0c358125fa653683767374d24"
DATABASE_SHA = "783e2dec1156b5793087412a724762ed2131e47112330cc2d86f5d982489d03d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(encoded(value))


def table_rows() -> dict[str, Counter[str]]:
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {
            name: Counter(
                hashlib.sha256(encoded(tuple(row)).encode()).hexdigest()
                for row in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')
            )
            for name in names
        }


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing attempt: inspect original journal/receipt; never blind retry")
    assert sha(INPUT) == PACKAGE_SHA
    package, proof = json.loads(INPUT.read_bytes()), json.loads(PROOF.read_bytes())
    assert proof["source_package_sha256"] == PACKAGE_SHA
    sources = tuple(SourceCapture.model_validate(x) for x in package["sources"])
    facts = tuple(ResearchFact.model_validate(x) for x in package["facts"])
    claims = tuple(ResearchClaim.model_validate(x) for x in package["claims"])
    assert (len(sources), len(facts), len(claims)) == (20, 3989, 3572)
    cutoff = datetime.fromisoformat(package["data_cutoff"])
    assert cutoff.isoformat() == "2026-10-07T23:59:59.999999+08:00"
    _validate_references(sources, facts, claims)
    by_source = {s.source_id: s for s in sources}
    for source in sources:
        assert source.is_available_by(cutoff)
        assert source.text_derivation is not None
        verify_source_text_derivation(PROJECT, source.text_derivation, source.content_text)
    for fact in facts:
        source = by_source[fact.source_id]
        assert (
            extract_locator_quote(
                source.content_text,
                media_type=source.media_type,
                locator=fact.locator,
            )
            == fact.original_text
        )
    with current_delivery_lock(PROJECT):
        current_path, db_path = PROJECT / "reports/current.json", PROJECT / "state/project.sqlite"
        assert sha(current_path) == CURRENT_SHA
        assert sha(db_path) == DATABASE_SHA
        protected = {
            p: sha(p)
            for directory in ("reports", "snapshots", "receipts", "state/scientific_review")
            for p in (PROJECT / directory).rglob("*")
            if p.is_file() and p != PROJECT / "receipts/source_receipts.jsonl"
        }
        source_receipts = (PROJECT / "receipts/source_receipts.jsonl").read_bytes()
        before = table_rows()
        OUT.mkdir()
        backup = OUT / "database-before.sqlite"
        with (
            sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db,
            sqlite3.connect(backup) as target,
        ):
            db.backup(target)
        write(
            "prewrite.json",
            {
                "status": "PREVALIDATED_NORMAL_CANDIDATE_INGESTION_READY",
                "current_sha256": CURRENT_SHA,
                "database_sha256": DATABASE_SHA,
                "consistent_backup_sha256": sha(backup),
                "source_package_sha256": PACKAGE_SHA,
                "proof_sha256": sha(PROOF),
                "old_tables": {k: dict(v) for k, v in before.items()},
                "protected_files": {
                    p.relative_to(PROJECT).as_posix(): h for p, h in protected.items()
                },
                "old_source_receipts_sha256": hashlib.sha256(source_receipts).hexdigest(),
                "limits": (
                    "Local CAS replay only; no freshness, acceptance, current, browser or RC claim"
                ),
            },
        )
        now = datetime.now(UTC)
        try:
            lineage = ingest_research_evidence(
                project_root=PROJECT,
                project_id=package["project_id"],
                contract_version=package["contract_version"],
                report_kind="A",
                data_cutoff=cutoff,
                scientific_content_digest=PACKAGE_SHA,
                created_at=now,
                sources=sources,
                route_attempts=(),
                facts=facts,
                claims=claims,
                request_id="owner-1007-scoped-source-union-v2",
            )
            # Persist the real API result before postconditions; a failed assertion
            # after this point must never lead to repeated ingestion.
            write(
                "ingestion-return.json",
                {
                    "evidence_snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
                    "scientific_content_digest": PACKAGE_SHA,
                    "source_version_ids": lineage.source_version_ids,
                    "fact_version_ids": lineage.fact_version_ids,
                    "claim_version_ids": lineage.claim_version_ids,
                    "fact_version_by_ref": dict(lineage.fact_version_by_ref),
                },
            )
            after = table_rows()
            assert all(not (rows - after[name]) for name, rows in before.items()), "Old row changed"
            assert all(sha(p) == h for p, h in protected.items()), "Old artifact changed"
            assert (
                (PROJECT / "receipts/source_receipts.jsonl")
                .read_bytes()
                .startswith(source_receipts)
            )
            assert sha(current_path) == CURRENT_SHA
            snapshot = SnapshotStore(PROJECT).read(lineage.evidence_snapshot)
            assert len(snapshot["fact_version_ids"]) == 3989
            assert len(snapshot["claim_version_ids"]) == 3572
            old = proof["exact_old_accepted_ancestor_versions"]
            assert all(lineage.fact_version_by_ref[k] == v for k, v in old.items())
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
                states = {
                    f.fact_id: db.execute(
                        "SELECT review_state FROM fact_versions WHERE fact_version_id=?",
                        (lineage.fact_version_by_ref[f.fact_id],),
                    ).fetchone()[0]
                    for f in facts
                }
            assert all(states[k] == "accepted" for k in old)
            new = {k: v for k, v in states.items() if k not in old}
            assert Counter(new.values()) == {"candidate": 3884}
            write(
                "verified.json",
                {
                    "status": "NORMAL_INGESTED_CANDIDATE_ONLY_OLD_ROWS_AND_CURRENT_PRESERVED",
                    "evidence_snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
                    "counts": {
                        "sources": 20,
                        "facts": 3989,
                        "claims": 3572,
                        "reused_accepted_facts": 105,
                        "new_candidate_facts": 3884,
                    },
                    "old_table_rows_unchanged": True,
                    "protected_file_count": len(protected),
                    "source_receipts_append_only": True,
                    "current_sha256": CURRENT_SHA,
                    "database_after_sha256": sha(db_path),
                    "created_at": now.isoformat(),
                    "limits": "NOT accepted, NOT current, NOT universe/freshness/browser/RC",
                },
            )
        except Exception as error:
            write(
                "failure.json",
                {
                    "status": "FAILED_INSPECT_BEFORE_ANY_RETRY",
                    "error_type": type(error).__name__,
                    "message": str(error),
                },
            )
            raise
    print(
        encoded(
            {"status": "CANDIDATE_ONLY_INGESTED", "snapshot": lineage.evidence_snapshot.snapshot_id}
        )
    )


if __name__ == "__main__":
    main()
