"""Freeze corrected exact-source19 candidates; no ingestion, acceptance or current writes."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
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
OLD = ROOT / ".artifacts/1007-measured-pk-safety-candidate-v2"
OUT = ROOT / ".artifacts/1007-source-context-candidate-v3"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins() -> dict[str, str]:
    excluded = {"user-fact-edit.lock", "project.sqlite-wal", "project.sqlite-shm"}
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in PROJECT.rglob("*")
            if p.is_file() and p.name not in excluded}


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False)


def main() -> None:
    assert not OUT.exists(), "Exclusive candidate; never overwrite historical results"
    assert sha(OLD / "source-package.json") == (
        "86199fda5c3b681b8c774a317746a438579144957bd268f97951bf17be2560ad")
    previous = json.loads((OLD / "source-package.json").read_bytes())
    before = pins()
    assert len(before) == 11716
    sources = tuple(SourceCapture.model_validate(s) for s in previous["sources"])
    by_source = {source.source_id: source for source in sources}
    generated: dict[tuple[str, str, str], list[ResearchFact]] = {}
    for source in sources:
        atoms, _issues = extract_ctgov_atomic_results(source)
        for atom in atoms:
            for fact in research_facts_from_ctgov_atom(atom):
                assert fact.result_context
                key = (fact.source_id, fact.locator.field_path or "", fact.result_context.value_role)
                # One N locator can support multiple distinct measurement
                # contexts. Never collapse these by locator or choose first.
                generated.setdefault(key, []).append(fact)
    facts = []
    changes = []
    for record in previous["facts"]:
        old = ResearchFact.model_validate(record)
        assert old.result_context
        key = (old.source_id, old.locator.field_path or "", old.result_context.value_role)
        context = old.result_context.model_dump(exclude={"category", "result_key"})
        matches = [f for f in generated[key] if f.result_context and
                   f.result_context.model_dump(exclude={"category", "result_key"}) == context]
        assert len(matches) == 1, "Exact source/statistical object is not unique"
        fresh = matches[0].model_copy(update={"row_ref": old.row_ref})
        source = by_source[fresh.source_id]
        assert (fresh.raw_value, fresh.original_text, fresh.locator) == (
            old.raw_value, old.original_text, old.locator)
        assert extract_locator_quote(source.content_text, media_type=source.media_type,
                                     locator=fresh.locator) == fresh.original_text
        if fresh != old:
            assert old.result_context.category == "common_ae"
            assert fresh.result_context and fresh.result_context.category == "tesae"
            changes.append({"old_fact_id": old.fact_id, "new_fact_id": fresh.fact_id,
                            "source_id": fresh.source_id, "path": fresh.locator.field_path,
                            "role": fresh.result_context.value_role})
        facts.append(fresh)
    assert len(facts) == len({f.fact_id for f in facts}) == 19
    assert len(changes) == 2  # TESAE participant count and its same-measure N.
    claims = tuple(ResearchClaim(
        claim_id=stable_id("source-context-v3-claim", f.fact_id),
        claim_text=f.original_text, claim_kind="direct_evidence", fact_ids=(f.fact_id,),
    ) for f in facts)
    _validate_references(sources, tuple(facts), claims)
    command = json.loads((OLD / "prewrite.json").read_bytes())["command"]
    command[0] = sys.executable
    command[command.index("--output") + 1] = str(OUT / "a-candidate.json")
    OUT.mkdir()
    write("prewrite.json", {"durable_project_pins": before, "command": command})
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    write("builder-return.json", {"exit_code": result.returncode,
                                  "stdout": result.stdout, "stderr": result.stderr})
    assert result.returncode == 0, result.stderr
    report = json.loads((OUT / "a-candidate.json").read_bytes())
    assert len(report["trials"]) == 46
    assert all(not row.get("analysis_n_source_path", "").startswith("$.$.")
               for row in report["additional_observations"])
    assert pins() == before
    write("source-package.json", {**previous,
        "facts": [f.model_dump(mode="json") for f in facts],
        "claims": [c.model_dump(mode="json") for c in claims]})
    write("actual.json", {
        "state": "FROZEN_SOURCE_CONTEXT_CANDIDATE_NOT_INGESTED_ACCEPTED_OR_CURRENT",
        "recipe_sha256": sha(Path(__file__)), "facts": len(facts), "sources": len(sources),
        "source_package_sha256": sha(OUT / "source-package.json"),
        "payload_sha256": sha(OUT / "a-candidate.json"),
        "derivation_sha256": sha(OUT / "a-candidate.derivation.json"),
        "classifier_sha256": sha(ROOT / "src/ci_workflow/application/source_research_service.py"),
        "acceptance_sha256": sha(ROOT / "src/ci_workflow/application/source_fact_acceptance.py"),
        "builder_sha256": sha(ROOT / "tools/build_a_payload.py"),
        "source_context_changes": changes, "durable_project_files_unchanged": len(before),
        "adoptions": 0, "registrations": 0, "saves": 0, "current_changes": 0,
        "limits": "New candidate only; independent source/trust review and formal issuer still required",
    })
    print(json.dumps({"state": "PREPARED_NOT_ACCEPTED", "facts": len(facts),
                      "tesae_changed_atoms": len(changes)}))


if __name__ == "__main__":
    main()
