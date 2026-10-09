"""Prepare a new PN C report from genuine adopted source; never publish current.

Reuses production snapshot, projection, renderer and review-request APIs.
No source ingestion, review issuance, adoption or SQL mutations occur here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.c_portal_consumer_registry import project_reviewed_c_source_states
from ci_workflow.application.fresh_c_research_package import (
    derive_c_research_facts,
    evaluate_c_report_gate,
    validate_fresh_c_content,
)
from ci_workflow.application.fresh_research_ingestion import ResearchEvidenceLineage
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.run_service import RunContext, _render_html_c_minimal
from ci_workflow.application.scientific_review_transition import (
    build_scientific_review_context,
    capture_portal_artifact_binding,
    prepare_rendered_scientific_review,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import (
    ReportSnapshotManifest,
    SnapshotStore,
    compute_locked_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / ".artifacts/1007-c-source-review-bootstrap-worker-v1/project"
SOURCE_DIGEST = "dcf6d665dace3322b39c8414d0ac07aa7ce624ab6ccf6e2cd6f9a91239e17881"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(path: Path, payload: object) -> str:
    encoded = (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == encoded, f"refuse frozen overwrite: {path.name}"
    else:
        with path.open("xb") as stream:
            stream.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def main(
    *, candidate_number: int = 2, project_root: Path | None = None,
    source_digest: str | None = None, output_root: Path | None = None,
) -> None:
    if candidate_number < 2:
        raise ValueError("candidate number must be at least 2")
    project = PROJECT if project_root is None else project_root
    source_digest = SOURCE_DIGEST if source_digest is None else source_digest
    if re.fullmatch(r"[0-9a-f]{64}", source_digest) is None:
        raise ValueError("source digest must be a lowercase SHA-256")
    version = f"v{candidate_number}-r24-reviewed-source-report-candidate"
    if output_root is None:
        output_root = ROOT / ".artifacts/1007-c-source-repairs-v1"
    out = output_root / f"report-candidate-v{candidate_number}"
    if (out / "candidate-receipt.json").exists():
        raise SystemExit(
            "Candidate already prepared: reopen its receipt; do not rerender/re-adopt."
        )
    assert read_current_delivery(project) is None
    contract = verify_project_workspace(project).contract
    entry = json.loads(
        (
            project / f"evidence/library/c-source-review/{source_digest}/entry-receipt.json"
        ).read_bytes()
    )
    source_path = project / entry["evidence_snapshot_relative"]
    source = json.loads(source_path.read_bytes())
    locked = compute_locked_snapshot(kind="evidence", report=None, manifest=source)
    assert locked.snapshot_id == entry["evidence_snapshot_id"]
    SnapshotStore(project).read(locked)
    before = {str(p.relative_to(project)): sha(p) for p in project.rglob("*") if p.is_file()}
    data = project_reviewed_c_source_states(
        project, locked, project / entry["report_data_relative"]
    )
    assert len(data.observations) == 258
    assert all(row.review_state.value == "accepted" for row in data.observations)
    closure = source["closure"]
    fact_ids = {
        str(item["fact"]["fact_id"]): str(item["fact_version_id"]) for item in closure["facts"]
    }
    facts_by_ref = {
        str(ref): str(item["fact_version_id"])
        for item in closure["facts"]
        for ref in (item["fact"]["fact_id"], item["consumer_binding"]["row_ref"])
    }
    lineage = ResearchEvidenceLineage(
        evidence_snapshot=locked,
        source_version_ids=tuple(source["source_version_ids"]),
        source_fragment_ids=tuple(
            str(
                next(
                    fragment["fragment_id"]
                    for fragment in closure["fragments"]
                    if fragment["source_version_id"] == item["source_version_id"]
                    and fragment["locator"] == item["capture"]["locator"]
                    and fragment["original_text"] == item["capture"]["content_text"]
                )
            )
            for item in closure["sources"]
        ),
        fragment_ids=tuple(source["fragment_ids"]),
        fact_version_ids=tuple(source["fact_version_ids"]),
        claim_version_ids=tuple(source["claim_version_ids"]),
        derivation_ids=tuple(source["derivation_ids"]),
        receipt_ids=tuple(source["receipt_ids"]),
        claim_ids=tuple(str(item["claim"]["claim_id"]) for item in closure["claims"]),
        fact_version_by_ref=facts_by_ref,
        fragment_by_fact_id={
            str(item["fact"]["fact_id"]): str(item["primary_fragment_id"])
            for item in closure["facts"]
        },
    )
    stamp_path = out / "preparation-time.json"
    moment = (
        datetime.fromisoformat(json.loads(stamp_path.read_bytes())["created_at"])
        if stamp_path.exists()
        else datetime.now(UTC)
    )
    freeze(stamp_path, {"created_at": moment.isoformat()})
    report_snapshot = SnapshotStore(project).lock_report_snapshot(
        report="C",
        manifest=(
            ReportSnapshotManifest(
                schema_version="1.0",
                project_id=contract.project_id,
                contract_version=contract.contract_version,
                report="C",
                report_version=version,
                data_cutoff=data.data_cutoff,
                evidence_snapshot_id=locked.snapshot_id,
                claim_snapshot_id=entry["claim_snapshot_id"],
                coverage_set_id=entry["coverage_set_id"],
                claim_ids=lineage.claim_ids,
                created_at=moment,
            ).model_dump(mode="json")
        ),
    )
    data = data.model_copy(
        update={"report_version": version, "report_snapshot_id": report_snapshot.snapshot_id}
    )
    payload = json.loads((project / entry["content_relative"]).read_bytes())
    payload.update({"report_version": version, "report_data": data.model_dump(mode="json")})
    content = validate_fresh_c_content(payload)
    assert content.sources and derive_c_research_facts(content) == derive_c_research_facts(
        validate_fresh_c_content(json.loads((project / entry["content_relative"]).read_bytes()))
    )
    content_path = project / f"inputs/c-reviewed-report/v{candidate_number}-content.json"
    data_path = project / f"inputs/c-reviewed-report/v{candidate_number}-report-data.json"
    freeze(content_path, content.model_dump(mode="json"))
    freeze(data_path, data.model_dump(mode="json"))
    gate = evaluate_c_report_gate(
        content,
        project_id=contract.project_id,
        evidence_snapshot_id=locked.snapshot_id,
        contract_version=str(contract.contract_version),
        fact_version_by_ref=fact_ids,
    )
    assert gate.result.decision.value == "passed"
    freeze(out / "gate-result.json", gate.review_result.model_dump(mode="json"))
    run_id = stable_id("reviewed-c-report-run", contract.project_id, content.content_digest)
    context = RunContext(project_root=project, contract=contract, research_lineage=lineage)
    manifest_relative = f"reports/C/{version}/html.manifest.json"
    if (project / manifest_relative).is_file():
        manifest = ArtifactManifest.model_validate_json((project / manifest_relative).read_bytes())
        assert (
            manifest.producer_run_id == run_id
            and manifest.report_snapshot_id == report_snapshot.snapshot_id
        )
        site_relative = manifest.artifact.relative_path
    else:
        site_relative, manifest_relative = _render_html_c_minimal(context, run_id, data_path)
    binding = capture_portal_artifact_binding(
        project, "C", manifest_relative=manifest_relative, site_relative=site_relative
    )
    manifest = ArtifactManifest.model_validate_json((project / manifest_relative).read_bytes())
    assert manifest.artifact.sha256 == binding.site_sha256
    qc_context = build_scientific_review_context(
        project_id=contract.project_id,
        report_kind="C",
        report_version=version,
        producer_id=content.producer_id,
        candidate_snapshot_id=report_snapshot.snapshot_id,
        candidate_content_digest=content.content_digest,
        criteria_version=gate.spec_version,
        gate_result_key=gate.review_result.result_key,
        contract_version=str(contract.contract_version),
        coverage_set_id=entry["coverage_set_id"],
        evidence_snapshot_id=locked.snapshot_id,
        claim_snapshot_id=entry["claim_snapshot_id"],
        sources=content.sources,
        facts=derive_c_research_facts(content),
        claims=content.claims,
        fact_version_by_ref=facts_by_ref,
    )
    scope = prepare_rendered_scientific_review(
        project_root=project,
        report_kind="C",
        context=qc_context,
        producer_session_id=f"owner-reviewed-source-report-1007-v{candidate_number}",
        produced_at=moment,
        portal_binding=binding,
        gate_result=gate.review_result,
    )
    assert scope.epoch == candidate_number
    assert (
        project_reviewed_c_source_states(
            project, locked, project / entry["report_data_relative"]
        ).observations
        == data.observations
    )
    allowed_changed = {"state/scientific_review/C/epoch.json"}
    preserved = {path: digest for path, digest in before.items() if path not in allowed_changed}
    assert all(sha(project / path) == digest for path, digest in preserved.items())
    assert read_current_delivery(project) is None
    receipt = {
        "schema_version": "1007-reviewed-source-report-candidate-1",
        "project_relative": str(project.relative_to(ROOT)),
        "report_version": version,
        "source_content_digest": source_digest,
        "candidate_content_digest": content.content_digest,
        "source_evidence_snapshot_id": locked.snapshot_id,
        "report_snapshot_id": report_snapshot.snapshot_id,
        "context_digest": qc_context.context_digest,
        "epoch": scope.epoch,
        "accepted_observations": len(data.observations),
        "gate_decision": gate.result.decision.value,
        "gate_unit_states": dict(Counter(unit.outcome.value for unit in gate.result.unit_results)),
        "input_relative": str(content_path.relative_to(project)),
        "input_sha256": sha(content_path),
        "data_relative": str(data_path.relative_to(project)),
        "data_sha256": sha(data_path),
        "manifest_relative": manifest_relative,
        "manifest_sha256": sha(project / manifest_relative),
        "site_relative": site_relative,
        "site_sha256": binding.site_sha256,
        "site_total_bytes": binding.site_total_bytes,
        "historical_files_preserved": len(preserved),
        "database_unchanged": True,
        "original_source_adoption_reopened_after_new_epoch": True,
        "source_readopted": False,
        "current_switched": False,
        "report_scientific_review": "PENDING",
        "browser": "NOT_RUN",
        "release": False,
    }
    freeze(out / "candidate-receipt.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-number", type=int, default=2)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--source-content-digest")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    main(candidate_number=args.candidate_number, project_root=args.project_root,
         source_digest=args.source_content_digest, output_root=args.output_root)
