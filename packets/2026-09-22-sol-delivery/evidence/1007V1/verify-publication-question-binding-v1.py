"""Replay exact adopted publication labels and isolate a frozen historical-page test.

Only a new private receipt is written. No historical bytes, source fact, current
generation, scientific facet or numeric eligibility can be changed by this check.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.source_research_service import ResearchFact
from ci_workflow.domain.source_clause_context import SourceClauseReference
from ci_workflow.renderers.portal import report_a, report_b
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
RUN = PROJECT / "runs/publication-object-formal-v1"
OUT = ROOT / ".artifacts/1007-publication-question-binding-v1"
HISTORICAL = ROOT / ".artifacts/1007-source-questions-current-v2"
BASELINE = "7670b4d94b8b2a8dcba45705d1ee2353a0e03b6d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Reopen the immutable terminal receipt; never blind replay"
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 34
    package = RUN / "source-package.json"
    assert sha(package) == "e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0"
    payload = json.loads(package.read_bytes())
    ingestion = json.loads((RUN / "ingestion-return.json").read_bytes())
    snapshot = LockedSnapshot.model_validate(ingestion["evidence_snapshot"])
    locked = SnapshotStore(PROJECT).read(snapshot)
    originals = {fact.fact_id: fact for raw in payload["facts"]
                 if (fact := ResearchFact.model_validate(raw))}
    checked = []
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as database:
        for fact in originals.values():
            context, clause = fact.result_context, fact.source_clause_context
            if (context is None or clause is None
                    or not clause.scientific_scope.get("row_label_path")):
                continue
            reference = next(ref for ref in clause.continuations
                             if ref.locator.field_path == clause.scientific_scope["row_label_path"])
            before = fact.model_dump_json()
            version = ingestion["fact_version_by_ref"][fact.fact_id]
            assert version in locked["fact_version_ids"]
            assert database.execute(
                "SELECT review_state FROM fact_versions WHERE fact_version_id=?",
                (version,)).fetchone() == ("accepted",)
            row = {"source_id": fact.source_id}
            assert report_b._question_reference_matches_measure(
                reference, clause.scientific_scope, row, context.source_measure_path or "")
            foreign = SourceClauseReference.model_validate({**reference.model_dump(mode="json"),
                                                           "source_id": "foreign-publication"})
            assert not report_b._question_reference_matches_measure(
                foreign, clause.scientific_scope, row, context.source_measure_path or "")
            assert fact.model_dump_json() == before
            checked.append({"fact_id": fact.fact_id, "fact_version_id": version,
                            "source_id": fact.source_id,
                            "row_label_path": reference.locator.field_path,
                            "cell_path": context.source_measure_path,
                            "quote": reference.original_text})
    assert checked
    # The earlier test used today's code to reproduce an old artifact's exact
    # presentation/science buckets. Compare the pre-change production definition
    # and current one on that very same immutable old input, without checkout.
    historical_input = HISTORICAL / "a-input.json"
    historical_page = HISTORICAL / "A/clinical-portfolio.html"
    pins = {str(path.relative_to(ROOT)): sha(path) for path in (historical_input, historical_page)}
    data = report_a.ReportAPortalData.model_validate_json(historical_input.read_bytes())
    source = subprocess.check_output(["git", "show", BASELINE +
        ":src/ci_workflow/renderers/portal/report_b.py"], cwd=ROOT, text=True)
    definition = next(node for node in ast.parse(source).body
                      if isinstance(node, ast.FunctionDef)
                      and node.name == "_question_display_groups")
    namespace = dict(vars(report_b))
    exec(compile(ast.Module(body=[definition], type_ignores=[]),
                 "prechange-registry-query", "exec"), namespace)
    changed = report_b._question_display_groups
    try:
        report_b._question_display_groups = namespace["_question_display_groups"]
        baseline_workspace, _, _ = report_a._a_comparison_workspace(data)
    finally:
        report_b._question_display_groups = changed
    current_workspace, _, _ = report_a._a_comparison_workspace(data)
    assert current_workspace == baseline_workspace, "XML repair changed the registry pipeline"
    frozen_workspace = json.JSONDecoder().raw_decode(historical_page.read_text().split(
        "window.__A_COMPARISON_WORKSPACE__ = ", 1)[1])[0]
    assert frozen_workspace != json.loads(json.dumps(baseline_workspace))
    assert pins == {str(path.relative_to(ROOT)): sha(path)
                    for path in (historical_input, historical_page)}
    assert sha(package) == "e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0"
    assert read_current_delivery(PROJECT) == current
    OUT.mkdir()
    (OUT / "actual.json").write_text(json.dumps({
        "state": "EXACT_ADOPTED_PUBLICATION_LABEL_BINDINGS_PASSED_REGISTRY_PATH_UNCHANGED",
        "recipe_sha256": sha(Path(__file__)), "author_sha256": sha(ROOT /
            "src/ci_workflow/renderers/portal/report_b.py"),
        "source_package_sha256": sha(package), "snapshot": snapshot.model_dump(mode="json"),
        "checked": checked, "adopted_publication_cells": len(checked),
        "foreign_source_negatives": len(checked), "historical_pins": pins,
        "historical_artifact_equal_to_prechange_code": False,
        "historical_artifact_equal_to_current_code": False,
        "prechange_and_current_registry_workspace_equal": True,
        "historical_test_classification": (
            "PREEXISTING_FROZEN_ARTIFACT_VERSUS_CURRENT_CODE_MISMATCH"),
        "current_revision": current.revision, "generation": current_bundle_sha256(current),
        "source_current_writes": 0, "numeric_coaxis_or_full_report_acceptance": "NOT_RUN",
    }, ensure_ascii=False, sort_keys=True, indent=1))
    print(json.dumps({"adopted_cells": len(checked), "registry_path_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
