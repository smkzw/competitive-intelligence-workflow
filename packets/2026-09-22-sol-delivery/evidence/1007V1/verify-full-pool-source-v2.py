"""Owner verification/recovery, never ingestion or scientific acceptance.

Retains the original worker output. Completes missing denominator payloads from
the same production atom converter and audits current source ancestry, not just
whether source IDs equal edited current version IDs.
"""

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.evidence import source_version_identity
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import extract_locator_quote
from tools.audit_ctgov_a_source_map import _raw_at_path

repo = Path(__file__).resolve().parents[4]
here = repo / ".artifacts/1007-joint-full-pool-source-audit-v1"
source_root = repo / ".artifacts/1007-pn-current-source-v1"
project = repo / ".artifacts/1007-abc-current-integration-v1/working/project"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=here / "verified-and-complete-v2.json")
out = parser.parse_args().output.resolve()
if not out.is_relative_to(here.resolve()):
    raise SystemExit("Verification output must stay in the dedicated audit directory.")
if out.exists():
    raise SystemExit("Existing owner verification: do not repeat or overwrite.")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


original = here / "coverage-and-candidates.json"
worker = json.loads(original.read_bytes())
generation_path = project / worker["reconciliation"]["current9"]["generation_file"]
paths = {
    "a-source-payload-v3.json": source_root / "a-source-payload-v3.json",
    "a-source-payload-v3.derivation.json": source_root / "a-source-payload-v3.derivation.json",
    "raw-descriptor.json": source_root / "raw-descriptor.json",
    "current9-generation.json": generation_path,
    "project.sqlite": project / "state/project.sqlite",
    "receipt-recovered-v1.json": project
    / "evidence/library/joint-ab-source-context-v1/receipt-recovered-v1.json",
    **{
        name: project / "evidence/library" / name
        for name in (
            "a-candidate-v5.json",
            "b-candidate-v5.json",
            "combined-source-receipt-v5.json",
        )
    },
}
descriptor = json.loads(paths["raw-descriptor.json"].read_bytes())
paths["raw-page.bin"] = source_root / descriptor["relative_path"]
if digest(paths["project.sqlite"]) != worker["pinned_inputs"]["project.sqlite"]["sha256"]:
    old_sha = worker["pinned_inputs"]["project.sqlite"]["sha256"]
    paths["project.sqlite"] = (
        repo
        / ".artifacts/1007-abc-current-integration-v1/recovery-cas"
        / "evidence/raw/sha256"
        / old_sha[:2]
        / (old_sha + ".bin")
    )
for name, path in paths.items():
    assert digest(path) == worker["pinned_inputs"][name]["sha256"], name
protected = {str(p): digest(p) for p in paths.values()}
protected[str(original)] = digest(original)
raw = json.loads(paths["raw-page.bin"].read_bytes())
records = {
    s["protocolSection"]["identificationModule"]["nctId"].casefold(): s for s in raw["studies"]
}
sidecar = json.loads(paths["a-source-payload-v3.derivation.json"].read_bytes())
refs = sidecar["row_source_map"]
assert len({(r["domain"], r["row_id"]) for r in refs}) == 3781
for r in refs:
    value = _raw_at_path(records[r["trial_id"].casefold()], r["value_path"])
    assert value == r["raw_value"] and type(value).__name__ == r["raw_value_type"]

adoption = json.loads((project / "runs/joint-ab-formal-source-v1/adoption.json").read_bytes())
decision = json.loads((project / adoption["acceptance"]["decision_relative_path"]).read_bytes())
accepted_ids = set(adoption["acceptance"]["accepted_fact_version_ids"])
generation = json.loads(generation_path.read_bytes())
db = sqlite3.connect(
    "file:" + quote(str(paths["project.sqlite"])) + "?mode=ro&immutable=1", uri=True
)
facts = {
    r[0]: r
    for r in db.execute(
        "SELECT fact_version_id,fact_id,supersedes_fact_version_id,review_state FROM fact_versions"
    )
}
ancestors = set()
for version in generation["active_fact_version_ids"]:
    visited = set()
    fact_id = facts[version][1]
    while version:
        assert version not in visited and facts[version][1] == fact_id
        visited.add(version)
        ancestors.add(version)
        version = facts[version][2]
assert all(facts[v][3] == "accepted" for v in accepted_ids)
rows = {
    (collection, row_id)
    for collection, row_id, version in db.execute(
        "SELECT collection,row_id,source_fact_version_id FROM source_portal_consumer_bindings "
        "WHERE report IN ('A','B') AND evidence_snapshot_id=?",
        (adoption["acceptance"]["evidence_snapshot_id"],),
    )
    if version in ancestors and version in accepted_ids
}
db.close()
assert len(rows) == 91
assert len(decision["source_scope_corrections"]) == 33
assert len(adoption["acceptance"]["source_scope_corrections"]) == 33

store = ContentAddressedStore(here / "cas")
blob = store.put_bytes(paths["raw-page.bin"].read_bytes(), media_type="application/json")
captures, atoms_by_path, completed = {}, {}, []
missing = quote_count = 0
for entry in worker["remaining_candidates"]:
    version = entry["source_version_id"]
    if version not in captures:
        from datetime import datetime

        study = derive_saved_ctgov_record(
            here / "cas",
            blob,
            entry["trial_id"].upper(),
            replayed_at=datetime.fromisoformat(worker["observed_at"]),
        )
        capture = source_capture_from_ctgov_study(here / "cas", study)
        actual_version = source_version_identity(
            capture.source_id,
            hashlib.sha256(capture.content_text.encode()).hexdigest(),
            published_at=capture.date_evidence("published_at"),
            effective_at=capture.date_evidence("effective_at"),
            first_disclosed_at=capture.date_evidence("first_disclosed_at"),
            text_derivation=capture.text_derivation,
        )
        assert actual_version == version
        captures[version] = capture
        atoms, _ = extract_ctgov_atomic_results(capture)
        paths_to_atoms = {}
        for atom in atoms:
            paths_to_atoms.setdefault(atom.value_locator.field_path, []).append(atom)
        atoms_by_path[version] = paths_to_atoms
    assert tuple(entry["row_ref"].split(":", 1)) not in rows
    matching = atoms_by_path[version].get(entry["locator"]["value_path"], [])
    assert len(matching) == 1
    full = research_facts_from_ctgov_atom(matching[0], report_row_ref=entry["row_ref"])
    claim = ResearchClaim.model_validate(entry["claim"])
    assert set(claim.fact_ids) == {f.fact_id for f in full}
    by_id = {f.fact_id: f for f in full}
    for old in entry["facts"]:
        fact = ResearchFact.model_validate(old)
        assert by_id[fact.fact_id] == fact
    missing += len(full) - len(entry["facts"])
    for fact in full:
        assert (
            extract_locator_quote(
                captures[version].content_text, media_type="application/json", locator=fact.locator
            )
            == fact.original_text
        )
        quote_count += 1
    completed.append({**entry, "facts": [f.model_dump(mode="json") for f in full]})
assert len(completed) == 1698 and missing == 224
assert all(digest(Path(path)) == sha for path, sha in protected.items())
result = {
    "status": "OWNER_VERIFIED_COMPLETE_CANDIDATES_NOT_INGESTED_NOT_ACCEPTED",
    "worker_output_sha256": digest(original),
    "protected_inputs_unchanged": protected,
    "exact_original_locators_verified": len(refs),
    "candidates": len(completed),
    "source_facts_verified": quote_count,
    "missing_denominator_payloads_recovered": missing,
    "original_worker_record_unchanged": True,
    "current_revision_unchanged": 9,
    "corrected_partition": {
        "accepted_source_rows_with_current_ancestry": 91,
        "remaining_v5_display_rows_not_accepted": 279,
        "remaining_new_candidates": 1698,
        "remaining_scoped_gaps": 1665,
        "additional_domain_separate": 48,
    },
    "source_scope_proofs_formal": 33,
    "historical_changed_N_entries": len(
        json.loads(paths["receipt-recovered-v1.json"].read_bytes())["source_N_corrections"]
    ),
    "source_captures": {key: cap.model_dump(mode="json") for key, cap in captures.items()},
    "remaining_candidates": completed,
    "remaining_gaps": worker["remaining_gaps"],
    "gap_counts_by_trial": dict(Counter(g["trial_id"] for g in worker["remaining_gaps"])),
    "limits": (
        "Offline exact-source replay, not live/as-of/completeness/numeric/report acceptance. "
        "No re-adoption, source refresh, current change or DB writes."
    ),
}
with out.open("x") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=1)
    handle.write("\n")
assert out.stat().st_size <= 50 * 1024 * 1024
print(
    json.dumps(
        {
            k: result[k]
            for k in (
                "status",
                "exact_original_locators_verified",
                "candidates",
                "source_facts_verified",
                "missing_denominator_payloads_recovered",
                "corrected_partition",
                "source_scope_proofs_formal",
            )
        },
        ensure_ascii=False,
    )
)
