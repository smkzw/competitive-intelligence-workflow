"""Accepted-source versions through the ordinary B row and question adapters."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.source_research_service import ResearchFact
from ci_workflow.renderers.portal import report_b
from ci_workflow.reports.b.semantic_grouping import semantic_row_digest
from ci_workflow.reports.b.source_publication import build_source_publication_views
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
RUN = PROJECT / "runs/publication-object-formal-v1"
OUT = ROOT / ".artifacts/1007-publication-source-view-owner-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Reopen completed evidence; do not repeat/overwrite"
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 34
    package = RUN / "source-package.json"
    assert sha(package) == "e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0"
    payload = json.loads(package.read_bytes())
    ingestion = json.loads((RUN / "ingestion-return.json").read_bytes())
    snapshot = LockedSnapshot.model_validate(ingestion["evidence_snapshot"])
    locked = SnapshotStore(PROJECT).read(snapshot)
    facts = tuple(ResearchFact.model_validate(raw) for raw in payload["facts"])
    originals = tuple(fact.model_dump_json() for fact in facts)
    version_by_fact = ingestion["fact_version_by_ref"]
    source_versions: dict[str, str] = {}
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        for version in locked["source_version_ids"]:
            source = db.execute("SELECT source_id FROM source_versions WHERE source_version_id=?",
                                (version,)).fetchone()[0]
            assert source not in source_versions
            source_versions[source] = version
        for fact in facts:
            version = version_by_fact[fact.fact_id]
            assert version in locked["fact_version_ids"]
            assert db.execute("SELECT review_state FROM fact_versions WHERE fact_version_id=?",
                              (version,)).fetchone() == ("accepted",)
    view = build_source_publication_views(facts, source_versions=source_versions,
                                         fact_versions=version_by_fact)
    rows = (*view["efficacy"]["facts"], *view["safety"]["facts"])
    assert len(rows) == 38 and len(view["unhandled"]) == 80
    assert sum(row["value"] is not None for row in rows) == 34
    assert sum(row["disclosure_state"] == "unresolved_due_to_route" for row in rows) == 4
    records, questions = [], []
    for source in view["efficacy"]["facts"]:
        row = report_b._project_record(source, domain="efficacy", names={}, trial_names={},
                                       fallback=source["row_id"])
        assert "source_param_type" not in row
        assert row["reported_count"] == source["reported_count"]
        assert row["value"] == source["value"] and not row["renderable"]
        assert row["source_fact"] == source["source_fact"]
        assert row["source_metric"] == "unresolved"
        assert row["source_fact"]["normalized_value"] is None
        assert report_b._publication_component_statistic(row) == "source_printed_n_percent"
        records.append((row, source))
        clause = source["source_clause_context"]
        label = clause["scientific_scope"]["row_label_path"]
        reference = next(ref for ref in clause["continuations"]
                         if ref["locator"]["field_path"] == label)
        questions.append({"source_version_id": source["source_version_id"],
            "source_measure_path": source["source_measure_path"],
            "question_id": "q-pruritus-nrs-ge4-improvement",
            "question_label_zh": "瘙痒评分改善≥4分",
            "basis_reference_ids": [reference["reference_id"]],
            "comparison_purpose": "clinical_question_descriptive"})
    groups = report_b._groups_for_page("efficacy", records)
    studies = tuple(sorted({row["trial_id"] for row, _ in records}))
    digests = tuple(semantic_row_digest(row) for row, _ in records)
    before = report_b._comparison_workspace(records, groups, studies)
    after = report_b._comparison_workspace(records, groups, studies, question_projections=questions)
    assert len(after["columns"]) == 1 and len(after["columns"][0]["cells"]) == 2
    assert len(after["membership"]["row_ids"]) == 4 and not after["descriptive_groups"]
    assert all(before[key] == after[key] for key in ("membership", "facets", "numeric_eligibility"))
    assert digests == tuple(semantic_row_digest(row) for row, _ in records)
    assert originals == tuple(fact.model_dump_json() for fact in facts)
    assert read_current_delivery(PROJECT) == current
    OUT.mkdir()
    result = {"state": "REAL_ACCEPTED_SOURCE_VIEW_AND_ORDINARY_ROW_QUERY_PASSED",
        "source_package_sha256": sha(package), "recipe_sha256": sha(Path(__file__)),
        "current_revision": current.revision, "generation": current_bundle_sha256(current),
        "accepted_facts": 118, "routed": 38, "printed_percent": 34, "parsing_unresolved": 4,
        "unhandled": 80, "actual_source_versions": source_versions,
        "ordinary_question_rows": 4, "ordinary_question_studies": 2,
        "source_current_writes": 0, "original_science_preserved": True,
        "unknown_product_not_guessed": True,
        "real_portal_consumers_browser_current_edit": "NOT_RUN",
        "author_sha256": {path: sha(ROOT / path) for path in (
            "src/ci_workflow/renderers/portal/report_b.py",
            "src/ci_workflow/reports/b/publication_components.py",
            "src/ci_workflow/reports/b/source_publication.py")},
        "rows": [{key: row[key] for key in ("row_id", "source_fact_version_id",
            "source_version_id", "raw_value", "value", "reported_count", "disclosure_state",
            "source_component_projection")} for row in rows]}
    (OUT / "actual.json").write_text(json.dumps(
        result, ensure_ascii=False, sort_keys=True, indent=1))
    print(json.dumps({key: result[key] for key in ("state", "routed", "printed_percent",
                                                 "parsing_unresolved", "unhandled")}), flush=True)


if __name__ == "__main__":
    main()
