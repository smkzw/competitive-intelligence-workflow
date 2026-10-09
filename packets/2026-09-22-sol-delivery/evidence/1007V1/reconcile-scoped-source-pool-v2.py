"""Refreeze the fixed source page after the dose-prefix root repair.

Keep v1/old source/accepted lineage/current intact. Preparation, not adoption.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.source_research_service import (
    CtgovARowSourceRef,
    build_ctgov_a_outcome_candidate_batch,
    build_ctgov_a_safety_candidate_batch,
    source_capture_from_ctgov_study,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[4]
OLD = ROOT / ".artifacts/1007-pn-current-source-v1"
V1 = ROOT / ".artifacts/1007-scoped-source-pool-reconcile-v1"
OUT = ROOT / ".artifacts/1007-scoped-source-pool-reconcile-v2"
SEPARATE = {"nct04183335", "nct04202679", "nct04501666", "nct04501679"}
RESTORED = {"nct03540160", "nct03546816", "nct03677401"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise SystemExit("V2 already exists; inspect original attempt, never overwrite/retry")
    descriptor = json.loads((OLD / "raw-descriptor.json").read_bytes())
    raw = OLD / descriptor["relative_path"]
    protected = {
        p: digest(p)
        for p in (
            raw,
            V1 / "candidate.json",
            V1 / "a-scoped.json",
            V1 / "a-scoped.derivation.json",
            OLD / "a-source-payload-v3.json",
            OLD / "a-source-payload-v3.derivation.json",
        )
    }
    assert protected[raw] == "82b4ed9ab0c63e227a2c4c34b85727dd988e55062850d42b41517f0749168edf"
    assert (
        protected[V1 / "candidate.json"]
        == "73ae5683f0de826dc125898173dac7b92a6e638316668ab259f4750b754ceb6c"
    )
    previous = ReportAPortalData.model_validate_json((V1 / "a-scoped.json").read_bytes())
    OUT.mkdir()
    cas = ContentAddressedStore(OUT / "cas")
    blob = cas.put_bytes(raw.read_bytes(), media_type="application/json")
    command = [
        str(ROOT / ".venv/bin/python"),
        "tools/build_a_payload.py",
        "--cas-dir",
        str(OUT / "cas"),
        "--alias-map",
        str(OLD / "empty-source-alias-map.json"),
        "--indication",
        previous.indication,
        "--indication-id",
        "pn",
        "--cutoff",
        "2026-10-07",
        "--output",
        str(OUT / "a-scoped.json"),
    ]
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    report = ReportAPortalData.model_validate_json((OUT / "a-scoped.json").read_bytes())
    sidecar = json.loads((OUT / "a-scoped.derivation.json").read_bytes())
    refs = {entry["row_id"]: entry for entry in sidecar["row_source_map"]}
    old_trials = {trial.id for trial in previous.trials}
    new_trials = {trial.id for trial in report.trials}
    assert new_trials - old_trials == RESTORED and old_trials <= new_trials
    for collection in ("efficacy", "safety"):
        after = {row.row_id: row for row in getattr(report, collection)}
        assert all(after[row.row_id] == row for row in getattr(previous, collection))
    facts, claims, bound, gaps, issues, captures = [], [], [], [], [], []
    observed = datetime.now(UTC)
    for trial_id in sorted(new_trials - SEPARATE):
        rows = [row for row in (*report.efficacy, *report.safety) if row.trial_id == trial_id]
        if not rows:
            continue
        study = derive_saved_ctgov_record(OUT / "cas", blob, trial_id.upper(), replayed_at=observed)
        source = source_capture_from_ctgov_study(OUT / "cas", study)
        captures.append(source)
        for collection, builder in (
            ("efficacy", build_ctgov_a_outcome_candidate_batch),
            ("safety", build_ctgov_a_safety_candidate_batch),
        ):
            selected = [row for row in getattr(report, collection) if row.trial_id == trial_id]
            row_refs = [
                CtgovARowSourceRef(
                    row_id=row.row_id,
                    trial_id=trial_id,
                    source_page_sha256=blob.sha256,
                    value_path=refs[row.row_id]["value_path"],
                    raw_class_title=refs[row.row_id].get("class_title"),
                    raw_category_title=refs[row.row_id].get("category_title"),
                    display_population=refs[row.row_id].get("display_population"),
                )
                for row in selected
            ]
            batch = builder((source,), selected, row_source_refs=row_refs)
            facts.extend(batch.facts)
            claims.extend(batch.claims)
            bound.extend(batch.bound_rows)
            gaps.extend({"trial_id": trial_id, **asdict(gap)} for gap in batch.gaps)
            issues.extend({"trial_id": trial_id, **asdict(issue)} for issue in batch.source_issues)
    source_by_id = {s.source_id: s for s in captures}
    fact_ids = {f.fact_id for f in facts}
    assert len(fact_ids) == len(facts) and all(set(c.fact_ids) <= fact_ids for c in claims)
    for fact in facts:
        source = source_by_id[fact.source_id]
        assert (
            extract_locator_quote(
                source.content_text, media_type=source.media_type, locator=fact.locator
            )
            == fact.original_text
        )
    frozen_v1 = json.loads((V1 / "candidate.json").read_bytes())
    original_bound = {row["row_id"] for row in frozen_v1["bound_rows"]}
    assert original_bound <= {row.row_id for row in bound}
    assert all(digest(path) == sha for path, sha in protected.items())
    record = {
        "status": "REFROZEN_DOSE_PREFIX_SOURCE_CANDIDATES_NOT_INGESTED_NOT_ACCEPTED_NOT_CURRENT",
        "source_access_method": "offline_fixed_page_replay_not_freshness_or_as_of",
        "input_hashes": {str(p.relative_to(ROOT)): v for p, v in protected.items()},
        "code": {
            p: digest(ROOT / p)
            for p in (
                "tools/build_a_payload.py",
                "src/ci_workflow/application/source_research_service.py",
            )
        },
        "command": command,
        "stdout": run.stdout,
        "payload_sha256": digest(OUT / "a-scoped.json"),
        "sidecar_sha256": digest(OUT / "a-scoped.derivation.json"),
        "restored_trials": sorted(RESTORED),
        "separate_trials": {
            t: {
                c: sum(row.trial_id == t for row in getattr(report, c))
                for c in ("efficacy", "safety")
            }
            for t in sorted(SEPARATE)
        },
        "scope": {
            "fixed_page_records": len(json.loads(raw.read_bytes())["studies"]),
            "report_trials": len(report.trials),
            "records_without_drug_intervention": sidecar["records_without_drug_intervention"],
            "old_gap_join_key": (
                "strip efficacy:/safety: prefix to row_id; "
                "old1665 IDs are a subset of v1 bound rows"
            ),
            "old_bound_rows_retained": len(original_bound),
            "group_assignment_states": dict(Counter(row.group_assignment_state for row in bound)),
        },
        "source_captures": {s.source_id: s.model_dump(mode="json") for s in captures},
        "facts": [f.model_dump(mode="json") for f in facts],
        "claims": [c.model_dump(mode="json") for c in claims],
        "bound_rows": [r.model_dump(mode="json") for r in bound],
        "gaps": gaps,
        "source_issues": issues,
        "counts": {
            "sources": len(captures),
            "facts": len(facts),
            "claims": len(claims),
            "bound": len(bound),
            "gaps": len(gaps),
        },
        "limits": (
            "Named four separate trials/370 rows retain prior status. Unknown arm links stay "
            "unknown, not declared. Seven prior true missing issues retained; "
            "no universe/co-axis/source adoption/current/freshness or RC claim."
        ),
    }
    with (OUT / "candidate.json").open("x") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=1)
    print(
        json.dumps(
            {
                "counts": record["counts"],
                "restored_trials": record["restored_trials"],
                "candidate_sha256": digest(OUT / "candidate.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
