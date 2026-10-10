"""Fresh bounded candidate; preserve the rejected v1, all sources and current21."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

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
POOL = ROOT / ".artifacts/1007-scoped-source-pool-reconcile-v2/candidate.json"
OLD = ROOT / ".artifacts/1007-half-life-candidate-owner-v1"
OUT = ROOT / ".artifacts/1007-measured-pk-safety-candidate-v2"


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
    assert not OUT.exists(), "Collect original attempt, never overwrite/replay"
    assert sha(SNAPSHOT) == "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237"
    assert sha(GAP) == "66e0e572975d6c0881420bf263be6fc222422bb5a3a92376ce1f6f163356f664"
    assert sha(POOL) == "9aae15b65841b35910c51469ac0db875729d17fa47454e71e6cc281aa8f22587"
    before = pins()
    snapshot = json.loads(SNAPSHOT.read_bytes())
    gap = json.loads(GAP.read_bytes())
    sources = {item["capture"]["source_id"]: SourceCapture.model_validate(item["capture"])
               for item in snapshot["closure"]["sources"]}
    source_ids = sorted({row["fact_context"]["source_id"] for row in gap["rows"]}
                        | {"ctgov-nct05405985"})
    by_source = {sid: extract_ctgov_atomic_results(sources[sid]) for sid in source_ids}
    facts: list[ResearchFact] = []
    reused: dict[str, str] = {}
    corrected: list[dict[str, Any]] = []
    with sqlite3.connect((PROJECT / "state/project.sqlite").resolve().as_uri()
                         + "?mode=ro", uri=True) as db:
        for row in gap["rows"]:
            old = ResearchFact.model_validate({**row["fact_context"], "row_ref": row["row_ref"]})
            matches = [a for a in by_source[old.source_id][0]
                       if a.value_locator == old.locator]
            assert len(matches) == 1
            generated = research_facts_from_ctgov_atom(matches[0], report_row_ref=old.row_ref)
            fresh = generated[0]
            assert (fresh.raw_value, fresh.original_text, fresh.locator) == (
                old.raw_value, old.original_text, old.locator)
            if fresh.model_dump(exclude={"row_ref"}) == old.model_dump(exclude={"row_ref"}):
                stored = db.execute("SELECT review_state FROM fact_versions "
                                    "WHERE fact_version_id=?", (row["fact_version_id"],)).fetchone()
                assert stored == ("candidate",)
                facts.append(fresh)
                reused[fresh.fact_id] = row["fact_version_id"]
            else:
                assert matches[0].trial_id.casefold() == "nct04202679"
                assert matches[0].class_title == "TESAEs"
                assert fresh.raw_value == "2" and matches[0].denominator == 77
                assert fresh.result_context and fresh.result_context.category == "common_ae"
                facts.extend(generated)
                corrected.append({"kind": "TESAE_SUBSET", "old_fact_id": old.fact_id,
                                  "new_fact_id": fresh.fact_id,
                                  "old_version": row["fact_version_id"],
                                  "locator": fresh.locator.model_dump(mode="json"),
                                  "value": "2", "N": 77, "old_version_preserved": True})
        half_lives = [a for a in by_source["ctgov-nct05405985"][0]
                      if a.endpoint == "Half-life (t1/2) of Nemolizumab"]
        assert len(half_lives) == 2
        for atom in half_lives:
            generated = research_facts_from_ctgov_atom(atom)
            assert len(generated) == 2 and atom.domain == "pk_pd"
            assert atom.dispersion_quote in {"5.91", "4.52"}
            fresh = generated[0]
            previous = list(db.execute(
                "SELECT fact_version_id,review_state,scientific_context_json "
                "FROM fact_versions WHERE fact_id=?", (fresh.fact_id,)))
            assert len(previous) == 1 and previous[0][1] == "accepted"
            original = json.loads(previous[0][2])
            expected = {**original, "result_context": {
                **original["result_context"], "domain": "pk_pd"}}
            assert expected == fresh.model_dump(mode="json", exclude={"row_ref"})
            corrected.append({"kind": "PK_DOMAIN_AND_SOURCE_SD", "fact_id": fresh.fact_id,
                              "old_version": previous[0][0], "raw_value": atom.value_quote,
                              "spread": atom.dispersion_quote,
                              "N": atom.denominator_candidates[0].parsed_value,
                              "old_version_preserved": True})
            facts.extend(generated)
    assert len(reused) == 13 and len(facts) == 19 and len(corrected) == 3
    assert len({f.fact_id for f in facts}) == 19
    captures = tuple(sources[s] for s in source_ids)
    for fact in facts:
        source = sources[fact.source_id]
        assert extract_locator_quote(source.content_text, media_type=source.media_type,
                                     locator=fact.locator) == fact.original_text
    claims = tuple(ResearchClaim(
        claim_id=stable_id("measured-source-delta-claim", fact.fact_id,
                           fact.result_context.domain if fact.result_context else "unknown"),
        claim_text=fact.original_text, claim_kind="direct_evidence", fact_ids=(fact.fact_id,),
    ) for fact in facts)
    _validate_references(captures, facts, claims)
    OUT.mkdir()
    command = list(json.loads(POOL.read_bytes())["command"])
    command[0] = sys.executable
    command[command.index("--output") + 1] = str(OUT / "a-candidate.json")
    write("prewrite.json", {"durable_project_pins": before, "command": command})
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    write("builder-return.json", {"exit_code": run.returncode,
                                  "stdout": run.stdout, "stderr": run.stderr})
    assert run.returncode == 0, run.stderr
    candidate = json.loads((OUT / "a-candidate.json").read_bytes())
    old_candidate = json.loads((OLD / "a-candidate.json").read_bytes())
    assert candidate["trials"] == old_candidate["trials"] and len(candidate["trials"]) == 46
    pk = [r for r in candidate["additional_observations"]
          if r["endpoint"] == "Half-life (t1/2) of Nemolizumab"]
    assert {(r["raw_value"], r["raw_dispersion"], r["analysis_n"]) for r in pk} == {
        ("18.0", "5.91", 95), ("18.5", "4.52", 96)}
    assert pins() == before
    package = {"project_id": snapshot["project_id"],
               "contract_version": snapshot["contract_version"],
               "data_cutoff": snapshot["data_cutoff"],
               "sources": [s.model_dump(mode="json") for s in captures],
               "facts": [f.model_dump(mode="json") for f in facts],
               "claims": [c.model_dump(mode="json") for c in claims]}
    write("source-package.json", package)
    write("actual.json", {
        "state": "MEASURED_PK_SAFETY_CANDIDATE_ONLY_NOT_INGESTED_ACCEPTED_OR_CURRENT",
        "recipe_sha256": sha(Path(__file__)), "snapshot_sha256": sha(SNAPSHOT),
        "classifier_sha256": sha(ROOT / "src/ci_workflow/application/source_research_service.py"),
        "safety_concepts_sha256": sha(ROOT / "src/ci_workflow/reports/b/safety_concepts.py"),
        "builder_sha256": sha(ROOT / "tools/build_a_payload.py"),
        "payload_sha256": sha(OUT / "a-candidate.json"),
        "derivation_sha256": sha(OUT / "a-candidate.derivation.json"),
        "source_package_sha256": sha(OUT / "source-package.json"),
        "sources": len(captures), "facts": len(facts), "claims": len(claims),
        "existing_candidate_versions": reused, "corrections": corrected,
        "source_issues": {sid: [i.model_dump(mode="json") for i in result[1]]
                          for sid, result in by_source.items()},
        "durable_project_files_unchanged": len(before),
        "source_writes": 0, "adoptions": 0, "registrations": 0, "saves": 0,
        "limits": "Prior rejected16-fact candidate and historical sources retained; "
                  "freshness/24-week safety context/coaxis/universe not upgraded. "
                  "Targeted same-session science follow-up and formal issuer still required.",
    })
    print(canonical({"state": "PREPARED_NOT_ACCEPTED", "facts": len(facts),
                     "reused_candidates": len(reused), "corrections": len(corrected)}))


if __name__ == "__main__":
    main()
