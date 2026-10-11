"""New exact source-only epoch; current A21 is only a presentation anchor."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.scientific_review_transition import (
    build_scientific_review_context,
    capture_portal_artifact_binding,
    prepare_rendered_scientific_review,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.scientific_review_epoch import epoch_pointer_path
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
INGESTION = ROOT / ".artifacts/1007-source-definition-ingestion-v4"
OUT = PROJECT / "runs/source-definition-formal-v4"
PACKAGE_SHA = "7deea74f488f879fc7e90130229815535433464e42cc31406e9cf4251d8aca9b"
CODE_PATHS = (
    "src/ci_workflow/application/source_research_service.py",
    "src/ci_workflow/application/source_fact_acceptance.py",
    "tools/build_a_payload.py",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing preparation: inspect original scope; never overwrite/replay")
    verified = json.loads((INGESTION / "verified.json").read_bytes())
    assert verified["source_package_sha256"] == PACKAGE_SHA
    code = {path: sha(ROOT / path) for path in CODE_PATHS}
    assert code == verified["production_source_hashes"]
    receipt = json.loads((INGESTION / "ingestion-return.json").read_bytes())
    locked = LockedSnapshot.model_validate(receipt["evidence_snapshot"])
    snapshot = SnapshotStore(PROJECT).read(locked)
    closure = snapshot["closure"]
    sources = tuple(SourceCapture.model_validate(x["capture"]) for x in closure["sources"])
    facts = tuple(ResearchFact.model_validate(
        {**x["fact"], "row_ref": x["consumer_binding"]["row_ref"]}) for x in closure["facts"])
    claims = tuple(ResearchClaim.model_validate(x["claim"]) for x in closure["claims"])
    assert (len(sources), len(facts), len(claims)) == (4, 19, 19)
    assert snapshot["scientific_content_digest"] == PACKAGE_SHA
    pid = snapshot["project_id"]
    claim_snapshot_id = stable_id(
        "claim-snapshot", pid, PACKAGE_SHA, *snapshot["claim_version_ids"])
    coverage_set_id = stable_id("coverage-set", pid, "A", locked.snapshot_id, claim_snapshot_id)
    context = build_scientific_review_context(
        project_id=pid, report_kind="A", report_version="v1-1007-source-definition-v4",
        producer_id="owner-1007-source-definition-v4",
        candidate_snapshot_id=locked.snapshot_id, candidate_content_digest=PACKAGE_SHA,
        criteria_version="1007V1-source-definition-and-exclusive-domain-scope-v4",
        gate_result_key=stable_id("source-definition-check", locked.sha256, PACKAGE_SHA),
        contract_version=str(snapshot["contract_version"]), coverage_set_id=coverage_set_id,
        evidence_snapshot_id=locked.snapshot_id, claim_snapshot_id=claim_snapshot_id,
        sources=sources, facts=facts, claims=claims,
        fact_version_by_ref=receipt["fact_version_by_ref"],
    )
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 21
    presentation = next(report for report in current.reports if report.report == "A")
    db_before = sha(PROJECT / "state/project.sqlite")
    current_sha = sha(PROJECT / "reports/current.json")
    pointer = PROJECT / epoch_pointer_path("A")
    protected = {
        path: sha(path)
        for directory in ("snapshots", "receipts", "state/scientific_review", "reports")
        for path in (PROJECT / directory).rglob("*") if path.is_file() and path != pointer
    }
    OUT.mkdir()
    write("prewrite.json", {
        "state": "SOURCE_ONLY_PREPARE_NOT_ACCEPTANCE", "context_digest": context.context_digest,
        "database_before_sha256": db_before, "current_sha256": current_sha,
        "snapshot_sha256": locked.sha256, "production_source_hashes": code,
        "recipe_sha256": sha(Path(__file__)),
    })
    write("source-binding-manifest.json", {
        "schema_version": "source-only-definition-binding-1", "report": "A",
        "evidence_snapshot": locked.model_dump(mode="json"),
        "source_package_sha256": PACKAGE_SHA, "production_source_hashes": code,
        "claim_snapshot_id": claim_snapshot_id, "coverage_set_id": coverage_set_id,
        "fact_version_ids": snapshot["fact_version_ids"],
        "claim_version_ids": snapshot["claim_version_ids"],
        "presentation_anchor": presentation.model_dump(mode="json"),
        "limits": "Exact nineteen-source scope only; A21 anchor is NOT report acceptance. "
                  "No universe/publication/freshness/current/browser/sharing/RC acceptance.",
    })
    binding = capture_portal_artifact_binding(
        PROJECT, "A", manifest_relative=(OUT / "source-binding-manifest.json")
        .relative_to(PROJECT).as_posix(), site_relative=presentation.site_relative_path,
    )
    scope = prepare_rendered_scientific_review(
        project_root=PROJECT, report_kind="A", context=context,
        producer_session_id="owner-1007-source-definition-formal-v4", produced_at=datetime.now(UTC),
        portal_binding=binding, gate_result=None,
    )
    write("scope-return.json", scope.model_dump(mode="json"))
    assert all(sha(path) == digest for path, digest in protected.items())
    assert sha(PROJECT / "state/project.sqlite") == db_before
    assert sha(PROJECT / "reports/current.json") == current_sha
    write("preparation.json", {
        "state": "SOURCE_ONLY_NEW_EPOCH_READY_NOT_ACCEPTED_NOT_CURRENT",
        "context_digest": context.context_digest, "epoch": scope.epoch,
        "request_relative": scope.review_request_relative,
        "production_context_relative": scope.production_context_relative,
        "receipt_relative": scope.receipt_relative,
        "evidence_snapshot": locked.model_dump(mode="json"),
        "source_package_sha256": PACKAGE_SHA, "production_source_hashes": code,
        "claim_snapshot_id": claim_snapshot_id, "coverage_set_id": coverage_set_id,
        "portal_binding": binding.model_dump(mode="json"),
        "database_sha256": db_before, "current_sha256": current_sha,
        "protected_file_count": len(protected), "full_report_gate": "NOT_RUN",
    })
    print(json.dumps({"state": "SOURCE_REVIEW_READY", "epoch": scope.epoch,
                      "context_digest": context.context_digest,
                      "request": scope.review_request_relative}))


if __name__ == "__main__":
    main()
