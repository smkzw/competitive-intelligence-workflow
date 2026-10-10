"""Prepare a bounded source delta, without ingestion, adoption or current writes.

Fourteen exact preexisting safety candidates retain their scientific content;
two source half-life facts retain identity/value and change only domain. Old
accepted versions remain untouched. Advisory review is not formal acceptance.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.fresh_research_ingestion import _validate_references
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
SNAPSHOT = PROJECT / "snapshots/evidence/evidence-snapshot_70170bf126764571d59faba8.json"
GAP = ROOT / ".artifacts/1007-safety-primary-gap-v1/actual.json"
REPLAY = ROOT / ".artifacts/1007-half-life-candidate-owner-v1/actual.json"
OUT = ROOT / ".artifacts/1007-pk-and-safety-source-delta-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def pins() -> dict[str, str]:
    excluded = {"user-fact-edit.lock", "project.sqlite-wal", "project.sqlite-shm"}
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in PROJECT.rglob("*")
            if p.is_file() and p.name not in excluded}


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        stream.write(canonical(value))


def main() -> None:
    assert not OUT.exists(), "Existing preparation: collect original, never overwrite/replay"
    assert sha(SNAPSHOT) == (
        "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237")
    assert sha(GAP) == "66e0e572975d6c0881420bf263be6fc222422bb5a3a92376ce1f6f163356f664"
    assert sha(REPLAY) == "0e9fdcdf38ec51ea410961323399202efbb6c1c0ea0df7f1cbe07c18c31731b0"
    classifier = ROOT / "src/ci_workflow/application/source_research_service.py"
    assert sha(classifier) == (
        "8ebaa39bef84de4a8e0a20d9d773d34a454b24b106d0729268261c78b1e0db09")
    before = pins()
    snapshot = json.loads(SNAPSHOT.read_bytes())
    gap = json.loads(GAP.read_bytes())
    sources = {item["capture"]["source_id"]: SourceCapture.model_validate(item["capture"])
               for item in snapshot["closure"]["sources"]}
    facts: list[ResearchFact] = []
    existing: dict[str, str] = {}
    changed: list[dict[str, object]] = []
    with sqlite3.connect((PROJECT / "state/project.sqlite").resolve().as_uri()
                         + "?mode=ro", uri=True) as db:
        for row in gap["rows"]:
            fact = ResearchFact.model_validate({**row["fact_context"], "row_ref": row["row_ref"]})
            scientific = canonical(fact.model_dump(mode="json", exclude={"row_ref"}))
            assert hashlib.sha256(scientific.encode()).hexdigest() == row["fact_content_sha256"]
            stored = db.execute("SELECT review_state,scientific_context_json "
                                "FROM fact_versions WHERE fact_version_id=?",
                                (row["fact_version_id"],)).fetchone()
            assert stored == ("candidate", scientific)
            existing[fact.fact_id] = row["fact_version_id"]
            facts.append(fact)
        atoms, issues = extract_ctgov_atomic_results(sources["ctgov-nct05405985"])
        assert not issues
        selected = [a for a in atoms if a.endpoint == "Half-life (t1/2) of Nemolizumab"]
        assert len(selected) == 2
        for atom in selected:
            generated = research_facts_from_ctgov_atom(atom)
            assert len(generated) == 1 and atom.domain == "pk_pd"
            fact = generated[0]
            fresh = fact.model_dump(mode="json", exclude={"row_ref"})
            previous = list(db.execute(
                "SELECT fact_version_id,review_state,scientific_context_json "
                "FROM fact_versions WHERE fact_id=?", (fact.fact_id,)))
            assert len(previous) == 1 and previous[0][1] == "accepted"
            original = json.loads(previous[0][2])
            corrected = {**original, "result_context": {
                **original["result_context"], "domain": "pk_pd"}}
            assert corrected == fresh, "Scientific change must be exactly efficacy→pk_pd"
            assert atom.value_quote in {"18.0", "18.5"}
            changed.append({"fact_id": fact.fact_id, "old_version": previous[0][0],
                            "source_locator": fact.locator.model_dump(mode="json"),
                            "old_domain": "efficacy", "new_domain": "pk_pd",
                            "raw_value": fact.raw_value, "old_version_preserved": True})
            facts.append(fact)
    assert len(facts) == 16 and len({f.fact_id for f in facts}) == 16
    captures = tuple(sources[s] for s in sorted({f.source_id for f in facts}))
    assert len(captures) == 4
    cutoff = datetime.fromisoformat(snapshot["data_cutoff"])
    assert cutoff.isoformat() == "2026-10-07T23:59:59.999999+08:00"
    for source in captures:
        assert source.is_available_by(cutoff)
    for fact in facts:
        source = sources[fact.source_id]
        assert extract_locator_quote(source.content_text, media_type=source.media_type,
                                     locator=fact.locator) == fact.original_text
    claims = tuple(ResearchClaim(
        claim_id=stable_id("source-delta-claim", fact.fact_id,
                           fact.result_context.domain if fact.result_context else "unknown"),
        claim_text=fact.original_text, claim_kind="direct_evidence", fact_ids=(fact.fact_id,),
    ) for fact in facts)
    _validate_references(captures, facts, claims)
    package = {"project_id": snapshot["project_id"],
               "contract_version": snapshot["contract_version"],
               "data_cutoff": snapshot["data_cutoff"],
               "sources": [s.model_dump(mode="json") for s in captures],
               "facts": [f.model_dump(mode="json") for f in facts],
               "claims": [c.model_dump(mode="json") for c in claims]}
    assert pins() == before, "Original project durable bytes changed"
    OUT.mkdir()
    write("source-package.json", package)
    write("proof.json", {
        "state": "PREPARED_SOURCE_DELTA_ONLY_NOT_ACCEPTED_NOT_CURRENT",
        "created_at": datetime.now(UTC).isoformat(), "source_commit":
        "e616f415eb61ba91a8d32cdcebb2460da31bff53", "script_sha256": sha(Path(__file__)),
        "package_sha256": sha(OUT / "source-package.json"),
        "classifier_sha256": sha(classifier), "original_snapshot_sha256": sha(SNAPSHOT),
        "existing_candidate_versions": existing, "scientific_domain_changes": changed,
        "sources": len(captures), "facts": len(facts), "claims": len(claims),
        "durable_project_files_unchanged": len(before),
        "source_writes": 0, "adoptions": 0, "registrations": 0, "renders": 0, "saves": 0,
        "limits": "Original metadata/cutoff unchanged; no current-page freshness adoption. "
                  "Fresh C03 and formal issuer still required; known model independence limited. "
                  "PK context correction must create a new scientific version, preserving old.",
    })
    print(canonical({"state": "PREPARED_NOT_INGESTED", "sources": len(captures),
                     "existing_candidates": len(existing), "domain_changes": len(changed)}))


if __name__ == "__main__":
    main()
