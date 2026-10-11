"""Materialize the normal independent receipt's exact source set, never current.

Retain a consistent SQLite backup and exact report/snapshot hashes. No source
normalization, guessed study/arm mapping or direct review-state SQL updates.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.source_fact_acceptance import accept_reviewed_source_facts

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
RUN = PROJECT / "runs/publication-object-formal-v1"
OUT = ROOT / ".artifacts/1007-publication-object-source-adoption-v1"
DATABASE = PROJECT / "state/project.sqlite"
EVIDENCE = "evidence-snapshot_37d704c94fdfdc3e20c41f8c"
CLAIMS = "claim-snapshot_bc2e4500e448d4c74f3e383f"


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"))
                          .encode()).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def rows(table: str, *, without_review: bool = False) -> list[tuple[object, ...]]:
    allowed = {"fact_versions", "claim_versions", "fact_evidence", "evidence_fragments",
               "source_versions", "source_portal_consumer_bindings", "user_fact_derivations",
               "user_fact_edit_requests"}
    assert table in allowed
    with sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True) as database:
        fields = [str(item[1]) for item in database.execute(f"PRAGMA table_info({table})")]
        if without_review:
            fields.remove("review_state")
        return sorted(database.execute(f"SELECT {','.join(fields)} FROM {table}").fetchall(),
                      key=repr)


def main() -> None:
    assert not OUT.exists(), "Inspect durable intent/result, never blind reapply"
    terminal = json.loads((RUN / "issuer-resume1-terminal.json").read_bytes())
    verdict = json.loads((RUN / "verdict.json").read_bytes())
    assert terminal["exit_code"] == 0 and verdict["verdict"] == "accepted"
    assert verdict["candidate_snapshot_id"] == EVIDENCE
    assert verdict["candidate_content_digest"] == (
        "e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0"
    )
    expected_facts = sorted({item for ref in verdict["source_refs"]
                             for item in ref["fact_version_ids"]})
    assert len(expected_facts) == 118
    before = read_current_delivery(PROJECT)
    assert before is not None and before.revision == 33
    pins = {path.relative_to(PROJECT).as_posix(): file_sha(path)
            for folder in (PROJECT / "reports", PROJECT / "snapshots")
            for path in folder.rglob("*") if path.is_file()}
    review_tables = {"fact_versions", "claim_versions"}
    tables = {table: digest(rows(table, without_review=table in review_tables))
              for table in ("fact_versions", "claim_versions", "fact_evidence",
                            "evidence_fragments", "source_versions",
                            "source_portal_consumer_bindings", "user_fact_derivations",
                            "user_fact_edit_requests")}
    OUT.mkdir()
    with (
        sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True) as source,
        sqlite3.connect(OUT / "prewrite.sqlite") as target,
    ):
        source.backup(target)
    write("prewrite.json", {"recipe_sha256": file_sha(Path(__file__)), "pins": pins,
                           "tables_excluding_target_review_states": tables,
                           "current": before.model_dump(mode="json"),
                           "verdict_sha256": file_sha(RUN / "verdict.json")})
    result = accept_reviewed_source_facts(project_root=PROJECT, report_kind="B",
                                         evidence_snapshot_id=EVIDENCE, claim_snapshot_id=CLAIMS)
    write("acceptance-return.json", result.model_dump(mode="json"))
    assert sorted(result.accepted_fact_version_ids) == expected_facts
    assert len(result.accepted_claim_version_ids) == 118
    assert not result.boundary_claim_version_ids and not result.source_scope_corrections
    assert read_current_delivery(PROJECT) == before
    for relative, expected in pins.items():
        assert file_sha(PROJECT / relative) == expected, relative
    for table, expected in tables.items():
        assert digest(rows(table, without_review=table in review_tables)) == expected
    with sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True) as database:
        assert all(database.execute(
            "SELECT review_state FROM fact_versions WHERE fact_version_id=?",
            (version,)).fetchone() == ("accepted",)
                   for version in expected_facts)
    write("verified.json", {
        "state": "EXACT_118_PUBLICATION_SOURCE_FACTS_AND_CLAIMS_ADOPTED_CURRENT33_UNCHANGED",
        "accepted_source_facts": 118, "accepted_claims": 118, "current_revision": 33,
        "generation": current_bundle_sha256(before), "historical_pinned_files": len(pins),
        "decision_relative_path": result.decision_relative_path,
        "decision_digest": result.decision_digest, "receipt_digest": result.receipt_digest,
        "source_payloads_and_consumers_unchanged": True, "active_report_facts": 1505,
        "numeric_frame_and_publication_portal_consumers": "NOT_IMPLEMENTED_BY_THIS_OPERATION",
        "scientific_issues": [item["issue_id"] for item in verdict["issues"]],
        "release": "NOT_ACCEPTED",
    })
    print(json.dumps({"source_facts": 118, "claims": 118, "current_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
