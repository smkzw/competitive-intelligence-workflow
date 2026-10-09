"""Rebuild the fixed raw page with the existing production scoped-N builder.

Candidate preparation only. No source access/freshness claim, DB or current
writes, adoption, historical rewrites or loosened binding guards.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from ci_workflow.application.source_research_service import (
    CtgovARowSourceRef,
    ResearchPackageError,
    SourceCapture,
    _bind_verified_ctgov_outcome_to_a_row,
    build_ctgov_a_outcome_candidate_batch,
    build_ctgov_a_safety_candidate_batch,
    extract_ctgov_atomic_results,
)
from ci_workflow.renderers.portal.report_a import EfficacyRow, ReportAPortalData
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import extract_locator_quote

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / ".artifacts/1007-scoped-source-pool-reconcile-v1"
OLD = REPO / ".artifacts/1007-pn-current-source-v1"
VERIFIED = REPO / ".artifacts/1007-joint-full-pool-source-audit-v1/verified-and-complete-v2.json"
DIAGNOSTIC = REPO / ".artifacts/1007-source-binding-gap-root-v1/root-families.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(entry: dict) -> CtgovARowSourceRef:
    return CtgovARowSourceRef(
        row_id=entry["row_id"],
        trial_id=entry["trial_id"],
        source_page_sha256=entry["source_page_sha256"],
        value_path=entry["value_path"],
        raw_class_title=entry.get("class_title"),
        raw_category_title=entry.get("category_title"),
        display_population=entry.get("display_population"),
    )


def main() -> None:
    if OUT.exists():
        raise SystemExit("New reconciliation directory already exists; never overwrite/retry")
    descriptor = json.loads((OLD / "raw-descriptor.json").read_bytes())
    raw = OLD / descriptor["relative_path"]
    protected = {
        p: digest(p)
        for p in (
            raw,
            VERIFIED,
            DIAGNOSTIC,
            OLD / "a-source-payload-v3.json",
            OLD / "a-source-payload-v3.derivation.json",
            OLD / "empty-source-alias-map.json",
        )
    }
    assert protected[raw] == descriptor["sha256"]
    assert protected[VERIFIED] == "cbc21dd68890fd7e99e30ebd05487270147cb1809b5ad7a848c14217f2bd622b"
    assert (
        protected[DIAGNOSTIC] == "61976e54b8a26d45c81db49e67e1333face1e616edef0f8af111b31e913d51ec"
    )
    OUT.mkdir()
    store = ContentAddressedStore(OUT / "cas")
    store.put_bytes(raw.read_bytes(), media_type="application/json")
    old = ReportAPortalData.model_validate_json((OLD / "a-source-payload-v3.json").read_bytes())
    command = [
        str(REPO / ".venv/bin/python"),
        "tools/build_a_payload.py",
        "--cas-dir",
        str(OUT / "cas"),
        "--alias-map",
        str(OLD / "empty-source-alias-map.json"),
        "--indication",
        old.indication,
        "--indication-id",
        "pn",
        "--cutoff",
        "2026-10-08",
        "--output",
        str(OUT / "a-scoped.json"),
    ]
    run = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=True)
    new = ReportAPortalData.model_validate_json((OUT / "a-scoped.json").read_bytes())
    sidecar = json.loads((OUT / "a-scoped.derivation.json").read_bytes())
    refs = {entry["row_id"]: entry for entry in sidecar["row_source_map"]}
    previous = {row.row_id: row for row in old.efficacy}
    current = {row.row_id: row for row in new.efficacy}
    assert previous.keys() == current.keys()
    n_changed = []
    for row_id, before in previous.items():
        after = current[row_id]
        assert before.model_dump(exclude={"denominator"}) == after.model_dump(
            exclude={"denominator"}
        )
        if before.denominator != after.denominator:
            n_changed.append(row_id)
    assert [row.model_dump() for row in old.safety] == [row.model_dump() for row in new.safety]
    audit = json.loads(VERIFIED.read_bytes())
    diagnostic = json.loads(DIAGNOSTIC.read_bytes())
    captures = [SourceCapture.model_validate(value) for value in audit["source_captures"].values()]
    by_trial = {source.query_or_identifier.casefold(): source for source in captures}
    old_gap_ids = {gap["row_ref"].split(":", 1)[1] for gap in audit["remaining_gaps"]}
    all_facts, all_claims, bound, gaps, issues = [], [], [], [], []
    for trial_id, source in sorted(by_trial.items()):
        rows = [row for row in new.efficacy if row.trial_id.casefold() == trial_id]
        result = build_ctgov_a_outcome_candidate_batch(
            (source,),
            rows,
            row_source_refs=[ref(refs[row.row_id]) for row in rows],
        )
        safety = [row for row in new.safety if (row.trial_id or "").casefold() == trial_id]
        result_safety = build_ctgov_a_safety_candidate_batch(
            (source,),
            safety,
            row_source_refs=[ref(refs[row.row_id]) for row in safety],
        )
        for batch in (result, result_safety):
            all_facts.extend(batch.facts)
            all_claims.extend(batch.claims)
            bound.extend(batch.bound_rows)
            gaps.extend({"trial_id": trial_id, **asdict(gap)} for gap in batch.gaps)
            issues.extend({"trial_id": trial_id, **asdict(issue)} for issue in batch.source_issues)
    bound_ids = {row.row_id for row in bound}
    assert old_gap_ids <= bound_ids, sorted(old_gap_ids - bound_ids)
    # Recheck the alleged14 latent class failures using the actual candidate
    # exact-path contract; corrected N is the only changed scientific row field.
    secondary = []
    atoms_by_trial = {}
    for gap_id in diagnostic["reconciliation"]["secondary_failure_gap_ids"]:
        row_id = gap_id.split(":", 1)[1]
        row = current[row_id]
        source = by_trial[row.trial_id.casefold()]
        if row.trial_id not in atoms_by_trial:
            atoms_by_trial[row.trial_id] = extract_ctgov_atomic_results(source)[0]
        atom = next(
            a
            for a in atoms_by_trial[row.trial_id]
            if a.value_locator.field_path == refs[row_id]["value_path"]
        )
        candidate = EfficacyRow.model_validate(
            {**row.model_dump(), "source_field_path": refs[row_id]["value_path"]}
        )
        actual, _ = _bind_verified_ctgov_outcome_to_a_row(source, atom, candidate)
        wrong_n = candidate.model_copy(update={"denominator": previous[row_id].denominator})
        try:
            _bind_verified_ctgov_outcome_to_a_row(source, atom, wrong_n)
        except ResearchPackageError as exc:
            error = str(exc)
        else:
            raise AssertionError("Production must still reject wrong-scope denominator")
        secondary.append(
            {
                "row_id": row_id,
                "corrected_denominator": actual.denominator,
                "old_denominator": wrong_n.denominator,
                "guard_exception": error,
            }
        )
    source_by_id = {source.source_id: source for source in captures}
    by_id = {fact.fact_id: fact for fact in all_facts}
    assert len(by_id) == len(all_facts)
    assert all(set(claim.fact_ids) <= by_id.keys() for claim in all_claims)
    for fact in all_facts:
        source = source_by_id[fact.source_id]
        assert (
            extract_locator_quote(
                source.content_text, media_type=source.media_type, locator=fact.locator
            )
            == fact.original_text
        )
    assert all(digest(path) == sha for path, sha in protected.items())
    output = {
        "status": "SCOPED_CANDIDATES_NOT_INGESTED_NOT_ACCEPTED_NOT_CURRENT",
        "source_access_method": "offline_fixed_page_replay_not_freshness_or_as_of",
        "code": {
            p: digest(REPO / p)
            for p in (
                "tools/build_a_payload.py",
                "src/ci_workflow/application/source_research_service.py",
            )
        },
        "pinned": {str(p.relative_to(REPO)): sha for p, sha in protected.items()},
        "command": command,
        "stdout": run.stdout,
        "payload_sha256": digest(OUT / "a-scoped.json"),
        "sidecar_sha256": digest(OUT / "a-scoped.derivation.json"),
        "efficacy_row_count": len(current),
        "values_units_identity_unchanged": True,
        "denominator_changed_row_ids": n_changed,
        "old_gap_count": len(old_gap_ids),
        "old_gaps_bound": len(old_gap_ids & bound_ids),
        "worker_secondary_class_failure_correction": secondary,
        "source_captures": {s.source_id: s.model_dump(mode="json") for s in captures},
        "facts": [f.model_dump(mode="json") for f in all_facts],
        "claims": [c.model_dump(mode="json") for c in all_claims],
        "bound_rows": [r.model_dump(mode="json") for r in bound],
        "gaps": gaps,
        "source_issues": issues,
        "counts": {
            "sources": len(captures),
            "facts": len(all_facts),
            "claims": len(all_claims),
            "bound": len(bound),
            "gaps": len(gaps),
        },
        "remaining": (
            "Four previously ingested trials/accepted rows remain separate. "
            "No database/current/scientific adoption or source refresh. "
            "Existing scientific and independent acceptance gates still apply."
        ),
    }
    with (OUT / "candidate.json").open("x") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=1)
    print(
        json.dumps(
            {
                "counts": output["counts"],
                "old_gaps_bound": output["old_gaps_bound"],
                "n_changed": len(n_changed),
                "candidate_sha256": digest(OUT / "candidate.json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
