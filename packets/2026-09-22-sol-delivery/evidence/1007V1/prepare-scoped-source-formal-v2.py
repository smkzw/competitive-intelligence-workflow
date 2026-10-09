"""Bind exact source-only union to a normal new review epoch, not a report gate."""

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
INGESTION = ROOT / ".artifacts/1007-scoped-source-union-ingestion-v2/ingestion-return.json"
OUT = PROJECT / "runs/scoped-source-formal-v2"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing formal preparation; inspect original, never overwrite")
    assert sha(INGESTION) == "81822f196f2f0f661495b6e3d338b46446aa2da4e7739cf5564682f5030d19c4"
    receipt = json.loads(INGESTION.read_bytes())
    locked = LockedSnapshot.model_validate(receipt["evidence_snapshot"])
    assert locked.sha256 == "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237"
    snapshot = SnapshotStore(PROJECT).read(locked)
    closure = snapshot["closure"]
    sources = tuple(SourceCapture.model_validate(x["capture"]) for x in closure["sources"])
    facts = tuple(
        ResearchFact.model_validate({**x["fact"], "row_ref": x["consumer_binding"]["row_ref"]})
        for x in closure["facts"]
    )
    claims = tuple(ResearchClaim.model_validate(x["claim"]) for x in closure["claims"])
    assert (len(sources), len(facts), len(claims)) == (20, 3989, 3572)
    content = snapshot["scientific_content_digest"]
    assert content == "7d4fc6006cc520e9b9923f2b909c0df907bc6da5a0cdd2e558898abb99447654"
    pid = snapshot["project_id"]
    claim_snapshot_id = stable_id("claim-snapshot", pid, content, *snapshot["claim_version_ids"])
    coverage_set_id = stable_id("coverage-set", pid, "A", locked.snapshot_id, claim_snapshot_id)
    context = build_scientific_review_context(
        project_id=pid,
        report_kind="A",
        report_version="v1-1007-scoped-source-union-v2",
        producer_id="owner-1007-scoped-source-union-v2",
        candidate_snapshot_id=locked.snapshot_id,
        candidate_content_digest=content,
        criteria_version="1007V1-fixed-registry-source-union-only-v2",
        gate_result_key=stable_id("source-union-check", locked.sha256, content),
        contract_version=str(snapshot["contract_version"]),
        coverage_set_id=coverage_set_id,
        evidence_snapshot_id=locked.snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        sources=sources,
        facts=facts,
        claims=claims,
        fact_version_by_ref=receipt["fact_version_by_ref"],
    )
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 11
    presentation = next(r for r in current.reports if r.report == "A")
    before_db = sha(PROJECT / "state/project.sqlite")
    current_sha = sha(PROJECT / "reports/current.json")
    mutable_pointer = PROJECT / epoch_pointer_path("A")
    protected = {
        p: sha(p)
        for directory in ("snapshots", "receipts", "state/scientific_review", "reports")
        for p in (PROJECT / directory).rglob("*")
        if p.is_file() and p != mutable_pointer
    }
    OUT.mkdir()
    write(
        "prewrite.json",
        {
            "status": "PREPARE_SOURCE_ONLY_EPOCH_NOT_ACCEPTANCE",
            "context_digest": context.context_digest,
            "snapshot_sha256": locked.sha256,
            "database_before_sha256": before_db,
            "current_sha256": current_sha,
            "existing_pointer_sha256": sha(mutable_pointer) if mutable_pointer.is_file() else None,
        },
    )
    write(
        "source-binding-manifest.json",
        {
            "schema_version": "source-only-union-binding-1",
            "report": "A",
            "evidence_snapshot": locked.model_dump(mode="json"),
            "source_package_sha256": content,
            "claim_snapshot_id": claim_snapshot_id,
            "coverage_set_id": coverage_set_id,
            "fact_version_ids": snapshot["fact_version_ids"],
            "claim_version_ids": snapshot["claim_version_ids"],
            "presentation_anchor": presentation.model_dump(mode="json"),
            "limits": (
                "Exact source union only. Existing A11 site is unchanged presentation anchor, "
                "NOT new-source rendering or report acceptance. Full report gate/universe/"
                "publications/freshness/arm attribution/numeric equivalence/current/RC NOT_RUN."
            ),
        },
    )
    binding = capture_portal_artifact_binding(
        PROJECT,
        "A",
        manifest_relative=(OUT / "source-binding-manifest.json").relative_to(PROJECT).as_posix(),
        site_relative=presentation.site_relative_path,
    )
    now = datetime.now(UTC)
    scope = prepare_rendered_scientific_review(
        project_root=PROJECT,
        report_kind="A",
        context=context,
        producer_session_id="owner-1007-scoped-source-formal-v2",
        produced_at=now,
        portal_binding=binding,
        gate_result=None,
    )
    write("scope-return.json", scope.model_dump(mode="json"))
    assert all(sha(p) == h for p, h in protected.items()), "Old evidence changed"
    assert sha(PROJECT / "state/project.sqlite") == before_db
    assert sha(PROJECT / "reports/current.json") == current_sha
    write(
        "preparation.json",
        {
            "status": "SOURCE_ONLY_NEW_EPOCH_READY_UNREVIEWED_NOT_ACCEPTED_NOT_CURRENT",
            "context_digest": context.context_digest,
            "request_relative": scope.review_request_relative,
            "production_context_relative": scope.production_context_relative,
            "receipt_relative": scope.receipt_relative,
            "epoch": scope.epoch,
            "evidence_snapshot": locked.model_dump(mode="json"),
            "source_package_sha256": content,
            "claim_snapshot_id": claim_snapshot_id,
            "coverage_set_id": coverage_set_id,
            "portal_binding": binding.model_dump(mode="json"),
            "created_at": now.isoformat(),
            "database_sha256": before_db,
            "current_sha256": current_sha,
            "protected_file_count": len(protected),
            "full_report_gate": "NOT_RUN",
            "limits": (
                "Source-only criterion; current11 presentation anchor is NOT new candidate report"
            ),
        },
    )
    print(
        json.dumps(
            {
                "status": "SOURCE_REVIEW_READY",
                "epoch": scope.epoch,
                "context_digest": context.context_digest,
                "request": scope.review_request_relative,
            }
        )
    )


if __name__ == "__main__":
    main()
