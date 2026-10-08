"""Prepare a new PN C report from genuine adopted source; never publish current.

Reuses production snapshot, projection, renderer and review-request APIs.
No source ingestion, review issuance, adoption or SQL mutations occur here.
"""

from __future__ import annotations

import hashlib
import json
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
OUT = ROOT / ".artifacts/1007-c-source-repairs-v1/report-candidate-v2"
SOURCE_DIGEST = "dcf6d665dace3322b39c8414d0ac07aa7ce624ab6ccf6e2cd6f9a91239e17881"
VERSION = "v2-r24-reviewed-source-report-candidate"


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


def main() -> None:
    if (OUT / "candidate-receipt.json").exists():
        raise SystemExit(
            "Candidate already prepared: reopen its receipt; do not rerender/re-adopt."
        )
    assert read_current_delivery(PROJECT) is None
    contract = verify_project_workspace(PROJECT).contract
    entry = json.loads(
        (
            PROJECT / f"evidence/library/c-source-review/{SOURCE_DIGEST}/entry-receipt.json"
        ).read_bytes()
    )
    source_path = PROJECT / entry["evidence_snapshot_relative"]
    source = json.loads(source_path.read_bytes())
    locked = compute_locked_snapshot(kind="evidence", report=None, manifest=source)
    assert locked.snapshot_id == entry["evidence_snapshot_id"]
    SnapshotStore(PROJECT).read(locked)
    before = {str(p.relative_to(PROJECT)): sha(p) for p in PROJECT.rglob("*") if p.is_file()}
    data = project_reviewed_c_source_states(
        PROJECT, locked, PROJECT / entry["report_data_relative"]
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
        for ref in (item["fact"]["fact_id"], item["fact"]["row_ref"])
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
    stamp_path = OUT / "preparation-time.json"
    moment = (
        datetime.fromisoformat(json.loads(stamp_path.read_bytes())["created_at"])
        if stamp_path.exists()
        else datetime.now(UTC)
    )
    freeze(stamp_path, {"created_at": moment.isoformat()})
    report_snapshot = SnapshotStore(PROJECT).lock_report_snapshot(
        report="C",
        manifest=(
            ReportSnapshotManifest(
                schema_version="1.0",
                project_id=contract.project_id,
                contract_version=contract.contract_version,
                report="C",
                report_version=VERSION,
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
        update={"report_version": VERSION, "report_snapshot_id": report_snapshot.snapshot_id}
    )
    payload = json.loads((PROJECT / entry["content_relative"]).read_bytes())
    payload.update({"report_version": VERSION, "report_data": data.model_dump(mode="json")})
    content = validate_fresh_c_content(payload)
    assert content.sources and derive_c_research_facts(content) == derive_c_research_facts(
        validate_fresh_c_content(json.loads((PROJECT / entry["content_relative"]).read_bytes()))
    )
    content_path = PROJECT / "inputs/c-reviewed-report/v2-content.json"
    data_path = PROJECT / "inputs/c-reviewed-report/v2-report-data.json"
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
    freeze(OUT / "gate-result.json", gate.review_result.model_dump(mode="json"))
    run_id = stable_id("reviewed-c-report-run", contract.project_id, content.content_digest)
    context = RunContext(project_root=PROJECT, contract=contract, research_lineage=lineage)
    manifest_relative = f"reports/C/{VERSION}/html.manifest.json"
    if (PROJECT / manifest_relative).is_file():
        manifest = ArtifactManifest.model_validate_json((PROJECT / manifest_relative).read_bytes())
        assert (
            manifest.producer_run_id == run_id
            and manifest.report_snapshot_id == report_snapshot.snapshot_id
        )
        site_relative = manifest.artifact.relative_path
    else:
        site_relative, manifest_relative = _render_html_c_minimal(context, run_id, data_path)
    binding = capture_portal_artifact_binding(
        PROJECT, "C", manifest_relative=manifest_relative, site_relative=site_relative
    )
    manifest = ArtifactManifest.model_validate_json((PROJECT / manifest_relative).read_bytes())
    assert manifest.artifact.sha256 == binding.site_sha256
    qc_context = build_scientific_review_context(
        project_id=contract.project_id,
        report_kind="C",
        report_version=VERSION,
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
        project_root=PROJECT,
        report_kind="C",
        context=qc_context,
        producer_session_id="owner-reviewed-source-report-1007-v2",
        produced_at=moment,
        portal_binding=binding,
        gate_result=gate.review_result,
    )
    assert scope.epoch == 2
    assert (
        project_reviewed_c_source_states(
            PROJECT, locked, PROJECT / entry["report_data_relative"]
        ).observations
        == data.observations
    )
    allowed_changed = {"state/scientific_review/C/epoch.json"}
    preserved = {path: digest for path, digest in before.items() if path not in allowed_changed}
    assert all(sha(PROJECT / path) == digest for path, digest in preserved.items())
    assert read_current_delivery(PROJECT) is None
    receipt = {
        "schema_version": "1007-reviewed-source-report-candidate-1",
        "project_relative": str(PROJECT.relative_to(ROOT)),
        "report_version": VERSION,
        "source_content_digest": SOURCE_DIGEST,
        "candidate_content_digest": content.content_digest,
        "source_evidence_snapshot_id": locked.snapshot_id,
        "report_snapshot_id": report_snapshot.snapshot_id,
        "context_digest": qc_context.context_digest,
        "epoch": scope.epoch,
        "accepted_observations": len(data.observations),
        "gate_decision": gate.result.decision.value,
        "gate_unit_states": dict(Counter(unit.outcome.value for unit in gate.result.unit_results)),
        "input_relative": str(content_path.relative_to(PROJECT)),
        "input_sha256": sha(content_path),
        "data_relative": str(data_path.relative_to(PROJECT)),
        "data_sha256": sha(data_path),
        "manifest_relative": manifest_relative,
        "manifest_sha256": sha(PROJECT / manifest_relative),
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
    freeze(OUT / "candidate-receipt.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
