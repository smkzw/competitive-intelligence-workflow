"""Read-only replay of accepted cells through shared production display functions."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.source_research_service import ResearchFact
from ci_workflow.renderers.portal import report_b
from ci_workflow.reports.b.publication_components import publication_value_components
from ci_workflow.reports.b.semantic_grouping import semantic_row_digest
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
RUN = PROJECT / "runs/publication-object-formal-v1"
OUT = ROOT / ".artifacts/1007-publication-components-owner-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Resume the completed receipt instead of replaying"
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 34
    package = RUN / "source-package.json"
    assert sha(package) == "e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0"
    payload = json.loads(package.read_bytes())
    ingestion = json.loads((RUN / "ingestion-return.json").read_bytes())
    snapshot = LockedSnapshot.model_validate(ingestion["evidence_snapshot"])
    locked = SnapshotStore(PROJECT).read(snapshot)
    facts = [ResearchFact.model_validate(raw) for raw in payload["facts"]]
    originals = [fact.model_dump_json() for fact in facts]
    results, records, questions = [], [], []
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        for fact in facts:
            fact_version = ingestion["fact_version_by_ref"][fact.fact_id]
            assert fact_version in locked["fact_version_ids"]
            assert db.execute("SELECT review_state FROM fact_versions WHERE fact_version_id=?",
                              (fact_version,)).fetchone() == ("accepted",)
            projected = publication_value_components(fact)["projection"]
            for component in projected["components"]:
                start, end = component["token_span"]
                assert fact.original_text[start:end] == component["raw_token"]
            results.append({"fact_id": fact.fact_id, "fact_version_id": fact_version,
                            "raw_value": fact.raw_value, "projection": projected})
            context, clause = fact.result_context, fact.source_clause_context
            if (not context or context.domain != "efficacy" or not clause
                    or context.raw_value_type != "composite_count_and_percent"):
                continue
            # Separate display metadata; the accepted scope/fact stays untouched.
            assert clause.continuations[0].source_id == fact.source_id == "pubmed-record-37142763"
            # Use the actual source version pinned by formal ingestion, not a name guess.
            source_versions = locked["source_version_ids"]
            version = next(v for v in source_versions if v.endswith("75ec971b64d21dc206421335"))
            display_clause = clause.model_dump(mode="json")
            display_clause["scientific_scope"].update(
                source_version_id=version, source_measure_path=context.source_measure_path)
            reference = next(ref for ref in clause.continuations
                if ref.locator.field_path == clause.scientific_scope["row_label_path"])
            row_input = {"row_id": fact.fact_id, "source_id": fact.source_id,
                "trial_id": fact.entity_id, "source_version_id": version,
                "source_measure_path": context.source_measure_path,
                "source_clause_context": display_clause, "source_domain": "efficacy",
                "source_measure_definition": context.endpoint,
                "endpoint": context.endpoint, "timepoint": context.timepoint,
                "unit": context.source_unit, "value": None,
                "source_analysis_population": context.analysis_population,
                "group_id": context.group_id, "group_label_zh": context.group_title}
            row = report_b._project_record(row_input, domain="efficacy", names={}, trial_names={},
                                           fallback=fact.fact_id)
            assert row["source_id"] == fact.source_id
            records.append(({**row, "_domain": "efficacy"}, row_input))
            questions.append({"source_version_id": version,
                "source_measure_path": context.source_measure_path,
                "question_id": "q-pruritus-nrs-ge4-improvement",
                "question_label_zh": "瘙痒评分改善≥4分",
                "basis_reference_ids": [reference.reference_id],
                "comparison_purpose": "clinical_question_descriptive"})
    assert len(records) == 4
    groups = report_b._groups_for_page("efficacy", records)
    studies = tuple(sorted({row["trial_id"] for row, _ in records}))
    digests = [semantic_row_digest(row) for row, _ in records]
    before = report_b._comparison_workspace(records, groups, studies)
    after = report_b._comparison_workspace(records, groups, studies, question_projections=questions)
    assert len(after["columns"]) == 1 and len(after["columns"][0]["cells"]) == 2
    assert set(after["columns"][0]["row_ids"]) == {fact["fact_id"] for fact in results
        if fact["fact_id"] in {row["row_id"] for row, _ in records}}
    assert all(after[key] == before[key] for key in ("membership", "facets", "numeric_eligibility"))
    assert digests == [semantic_row_digest(row) for row, _ in records]
    assert originals == [fact.model_dump_json() for fact in facts]
    assert read_current_delivery(PROJECT) == current
    counts = {state: sum(result["projection"]["state"] == state for result in results)
              for state in ("projected", "unresolved")}
    assert counts == {"projected": 34, "unresolved": 84}
    OUT.mkdir()
    (OUT / "actual.json").write_text(json.dumps({
        "state": "ACCEPTED_SOURCE_COMPONENT_AND_ORDINARY_QUESTION_PATH_REPLAY_PASSED",
        "recipe_sha256": sha(Path(__file__)), "source_package_sha256": sha(package),
        "author_sha256": {name: sha(ROOT / name) for name in (
            "src/ci_workflow/reports/b/publication_components.py",
            "src/ci_workflow/renderers/portal/report_b.py")},
        "results": results, "counts": counts, "source_question_rows": 4,
        "source_question_studies": 2, "scientific_identity_unchanged": True,
        "current_revision": current.revision, "generation": current_bundle_sha256(current),
        "source_current_writes": 0, "portal_numeric_consumer_or_browser_acceptance": "NOT_RUN",
    }, ensure_ascii=False, sort_keys=True, indent=1))
    print(json.dumps({"counts": counts, "source_question_rows": 4}), flush=True)


if __name__ == "__main__":
    main()
