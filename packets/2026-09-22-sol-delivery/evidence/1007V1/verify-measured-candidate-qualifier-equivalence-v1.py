"""Do not rewrite candidate hashes after a narrower ADA population qualifier."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.application.source_research_service import (
    ResearchFact,
    SourceCapture,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
)

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / ".artifacts/1007-measured-pk-safety-candidate-v2"
OUT = BASE / "qualifier-equivalence-v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Original evidence must not be overwritten"
    raw = json.loads((BASE / "source-package.json").read_bytes())
    expected = [ResearchFact.model_validate(f) for f in raw["facts"]]
    all_facts = {}
    counts = {}
    for capture in raw["sources"]:
        source = SourceCapture.model_validate(capture)
        atoms, issues = extract_ctgov_atomic_results(source)
        assert not issues
        counts[source.source_id] = len(atoms)
        for atom in atoms:
            for fact in research_facts_from_ctgov_atom(atom):
                all_facts[fact.fact_id] = fact
    for fact in expected:
        assert fact.model_dump(exclude={"row_ref"}) == all_facts[fact.fact_id].model_dump(
            exclude={"row_ref"})
    classifier = ROOT / "src/ci_workflow/application/source_research_service.py"
    proof = {"state": "CURRENT_CLASSIFIER_EXACT19_FACT_EQUIVALENCE_NOT_ACCEPTANCE",
             "candidate_proof_sha256": sha(BASE / "actual.json"),
             "source_package_sha256": sha(BASE / "source-package.json"),
             "classifier_sha256": sha(classifier), "recipe_sha256": sha(Path(__file__)),
             "verified_facts": len(expected), "all_source_atoms": counts,
             "limits": "Only ADA qualifier pattern narrowed after initial candidate. "
                       "Current source atoms re-extracted; original candidate hashes retained. "
                       "No ingestion/adoption/current/database/browser writes."}
    with OUT.open("x") as stream:
        json.dump(proof, stream, sort_keys=True, indent=1)
    print(json.dumps({"state": proof["state"], "facts": len(expected)}))


if __name__ == "__main__":
    main()
