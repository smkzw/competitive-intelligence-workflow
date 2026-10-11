"""One normal nineteen-fact ingestion; no acceptance or committed report switch.

An existing output is a recovery journal, never a request to repeat ingestion.
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
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
)
from ci_workflow.application.user_fact_edit import current_delivery_lock
from ci_workflow.storage.source_derivation import (
    extract_locator_quote,
    verify_source_text_derivation,
)

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
INPUT = ROOT / ".artifacts/1007-source-definition-candidate-v4/source-package.json"
OUT = ROOT / ".artifacts/1007-source-definition-ingestion-v4"
PACKAGE_SHA = "7deea74f488f879fc7e90130229815535433464e42cc31406e9cf4251d8aca9b"
CODE = {
    "src/ci_workflow/application/source_research_service.py":
        "d5724ba6cd8dd321bd33b8b7be179956adf0f96942be70604cc53b113aeac126",
    "src/ci_workflow/application/source_fact_acceptance.py":
        "a5e3c15075370bc41beba7999150a7e60c55b44bce8ba54ed0fae6378554d664",
    "tools/build_a_payload.py":
        "9fed04ed242fd6d0691b691e815d5f0d243ac32b3b0e2caf16f59be4f9a90535",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        stream.write(encoded(value))


def table_rows() -> dict[str, Counter[str]]:
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {
            name: Counter(
                hashlib.sha256(encoded(tuple(row)).encode()).hexdigest()
                for row in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')
            ) for name in names
        }


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing journal: inspect original return/backup; do not replay")
    assert sha(INPUT) == PACKAGE_SHA
    assert all(sha(ROOT / path) == digest for path, digest in CODE.items())
    package = json.loads(INPUT.read_bytes())
    sources = tuple(SourceCapture.model_validate(x) for x in package["sources"])
    facts = tuple(ResearchFact.model_validate(x) for x in package["facts"])
    claims = tuple(ResearchClaim.model_validate(x) for x in package["claims"])
    assert (len(sources), len(facts), len(claims)) == (4, 19, 19)
    cutoff = datetime.fromisoformat(package["data_cutoff"])
    _validate_references(sources, facts, claims)
    by_source = {source.source_id: source for source in sources}
    reproduced: dict[str, list[ResearchFact]] = {}
    for source in sources:
        assert source.is_available_by(cutoff) and source.text_derivation is not None
        verify_source_text_derivation(PROJECT, source.text_derivation, source.content_text)
        atoms, _ = extract_ctgov_atomic_results(source)
        for atom in atoms:
            for fact in research_facts_from_ctgov_atom(atom):
                reproduced.setdefault(fact.fact_id, []).append(fact)
    for fact in facts:
        source = by_source[fact.source_id]
        assert extract_locator_quote(
            source.content_text, media_type=source.media_type, locator=fact.locator,
        ) == fact.original_text
        matches = [other for other in reproduced.get(fact.fact_id, []) if
                   other.model_dump(mode="json", exclude={"row_ref"}) ==
                   fact.model_dump(mode="json", exclude={"row_ref"})]
        assert len(matches) == 1, f"Non-unique latest production reproduction: {fact.fact_id}"
    with current_delivery_lock(PROJECT):
        current = read_current_delivery(PROJECT)
        assert current is not None and current.revision == 21
        with sqlite3.connect(
            f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True,
        ) as db:
            assert db.execute(
                "SELECT generation_sha256 FROM current_delivery_state WHERE singleton=1",
            ).fetchone() == (
                "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310",)
        current_sha = sha(PROJECT / "reports/current.json")
        db_path = PROJECT / "state/project.sqlite"
        protected = {
            path.relative_to(PROJECT).as_posix(): sha(path)
            for path in PROJECT.rglob("*") if path.is_file() and path.name not in {
                "user-fact-edit.lock", "project.sqlite", "project.sqlite-wal", "project.sqlite-shm"
            } and path != PROJECT / "receipts/source_receipts.jsonl"
        }
        source_receipts = (PROJECT / "receipts/source_receipts.jsonl").read_bytes()
        before = table_rows()
        OUT.mkdir()
        with (
            sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db,
            sqlite3.connect(OUT / "database-before.sqlite") as backup,
        ):
            db.backup(backup)
        write("prewrite.json", {
            "state": "NORMAL_CANDIDATE_ONLY_READY_NOT_ACCEPTANCE",
            "source_package_sha256": PACKAGE_SHA, "production_source_hashes": CODE,
            "recipe_sha256": sha(Path(__file__)), "current_sha256": current_sha,
            "database_sha256": sha(db_path),
            "consistent_backup_sha256": sha(OUT / "database-before.sqlite"),
            "protected_files": protected,
            "old_tables": {name: {"rows": sum(rows.values()),
                                 "row_set_sha256": hashlib.sha256(encoded(dict(rows)).encode())
                                 .hexdigest()} for name, rows in before.items()},
        })
        try:
            lineage = ingest_research_evidence(
                project_root=PROJECT, project_id=package["project_id"],
                contract_version=package["contract_version"], report_kind="A",
                data_cutoff=cutoff, scientific_content_digest=PACKAGE_SHA,
                created_at=datetime.now(UTC), sources=sources, route_attempts=(),
                facts=facts, claims=claims, request_id="owner-1007-source-definition-v4",
            )
            # First retain the real API return, even if a later postcondition fails.
            write("ingestion-return.json", {
                "evidence_snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
                "source_version_ids": lineage.source_version_ids,
                "fact_version_ids": lineage.fact_version_ids,
                "claim_version_ids": lineage.claim_version_ids,
                "fact_version_by_ref": dict(lineage.fact_version_by_ref),
            })
            after = table_rows()
            assert all(not (rows - after[name]) for name, rows in before.items())
            assert all(sha(PROJECT / path) == digest for path, digest in protected.items())
            assert (PROJECT / "receipts/source_receipts.jsonl").read_bytes().startswith(
                source_receipts)
            assert sha(PROJECT / "reports/current.json") == current_sha
            write("verified.json", {
                "state": "NINETEEN_NORMALLY_INGESTED_NOT_ACCEPTED_NOT_CURRENT",
                "facts": 19, "sources": 4, "claims": 19,
                "source_package_sha256": PACKAGE_SHA, "production_source_hashes": CODE,
                "protected_file_count": len(protected), "old_rows_unchanged": True,
                "current_sha256": current_sha, "source_receipts_append_only": True,
                "evidence_snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
            })
        except Exception as error:
            write("failure.json", {"state": "INSPECT_BEFORE_RETRY", "type": type(error).__name__,
                                   "message": str(error)})
            raise
    print(encoded({"state": "CANDIDATE_ONLY_INGESTED", "facts": 19,
                   "snapshot": lineage.evidence_snapshot.snapshot_id}))


if __name__ == "__main__":
    main()
