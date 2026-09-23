from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ResearchIngestionError
from ci_workflow.application.research_package_submission import (
    submit_product_research_package,
)
from ci_workflow.application.review_issuer import ExternalProcessResult, issue_review_receipt
from ci_workflow.application.scientific_review_transition import (
    RENDERED_UNREVIEWED,
    SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE,
    build_scientific_review_context,
    capture_portal_artifact_binding,
    promote_rendered_candidate,
    publish_production_context,
    publish_scientific_review_request,
)
from ci_workflow.application.source_research_service import (
    FreshAResearchPackage,
    compute_research_content_digest,
)
from ci_workflow.qc.review_receipt import (
    ReviewExecutableEvidence,
    ReviewHostSession,
)
from ci_workflow.qc.scientific import ScientificQcReviewBundle, ScientificQcVerdict
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_research_package_submission import (
    _audit_payload,
    _project,
    _source_payload,
)
from tests.integration.test_review_r07_ingestion_invariants import _ingest, _prepare


def _fact_rows(project: Path) -> list[tuple[str, str]]:
    with open_database(project / "state/project.sqlite") as database:
        return [
            (str(row[0]), str(row[1]))
            for row in database.execute(
                "SELECT fact_version_id, review_state FROM fact_versions ORDER BY fact_version_id"
            )
        ]


def test_candidate_ingestion_never_self_assigns_independent_acceptance(
    tmp_path: Path,
) -> None:
    project, package, digest = _prepare(tmp_path)
    _ingest(project, package, digest)
    assert {state for _, state in _fact_rows(project)} == {"candidate"}
    with open_database(project / "state/project.sqlite") as database:
        claim_states = {
            str(row[0])
            for row in database.execute("SELECT review_state FROM claim_versions")
        }
    assert claim_states == {"candidate"}


@pytest.mark.parametrize(
    ("locator", "quote", "message"),
    [
        ({"document_role": "registry", "field_path": "studies[]"}, "伪造事实", "精确"),
        ({"document_role": "registry", "field_path": "$.products[0].name"}, "伪造事实", "原文"),
    ],
)
def test_fact_fragment_requires_exact_reextraction_from_persisted_source_bytes(
    tmp_path: Path,
    locator: dict[str, str],
    quote: str,
    message: str,
) -> None:
    def mutate(payload: dict[str, object]) -> None:
        facts = payload["facts"]
        assert isinstance(facts, list)
        facts[0]["locator"] = locator
        facts[0]["original_text"] = quote

    project, package, digest = _prepare(tmp_path, mutate_fact=mutate)
    with pytest.raises(ResearchIngestionError, match=message):
        _ingest(project, package, digest)


def test_fact_version_identity_changes_when_only_scientific_context_changes(
    tmp_path: Path,
) -> None:
    first_project, first_package, first_digest = _prepare(tmp_path / "first")
    first = _ingest(first_project, first_package, first_digest)

    def mutate(payload: dict[str, object]) -> None:
        facts = payload["facts"]
        assert isinstance(facts, list)
        facts[0]["canonical_name"] = str(facts[0]["canonical_name"]) + "（不同科学语境）"

    second_project, second_package, second_digest = _prepare(
        tmp_path / "second", mutate_fact=mutate
    )
    second = _ingest(second_project, second_package, second_digest)
    fact_id = first_package.facts[0].fact_id
    assert first.fact_version_by_ref[fact_id] != second.fact_version_by_ref[fact_id]


def test_manifest_and_returned_lineage_include_all_fact_fragments(tmp_path: Path) -> None:
    project, package, digest = _prepare(tmp_path)
    lineage = _ingest(project, package, digest)
    manifest = SnapshotStore(project).read(lineage.evidence_snapshot)
    with open_database(project / "state/project.sqlite") as database:
        adopted = {
            str(row[0])
            for row in database.execute(
                "SELECT fragment_id FROM fact_evidence WHERE evidence_role='primary'"
            )
        }
    assert adopted <= set(lineage.fragment_ids)
    assert adopted <= set(manifest["fragment_ids"])
    assert manifest["closure"]["facts"]
    assert manifest["closure"]["sources"]


def test_source_version_attempt_and_idempotency_request_are_separate(tmp_path: Path) -> None:
    project, package, digest = _prepare(tmp_path)
    first = _ingest(project, package, digest)
    replay = _ingest(project, package, digest)
    assert first.source_version_ids == replay.source_version_ids

    receipt_path = project / "receipts/source_receipts.jsonl"
    initial_receipts = [json.loads(line) for line in receipt_path.read_text().splitlines()]
    acquired = [row for row in initial_receipts if row["result_class"] == "content_acquired"]
    assert len(acquired) == len(package.sources)

    def mutate(payload: dict[str, object]) -> None:
        sources = payload["sources"]
        facts = payload["facts"]
        assert isinstance(sources, list) and isinstance(facts, list)
        source = json.loads(str(sources[0]["content_text"]))
        source["products"][0]["name"] += " 新字节"
        sources[0]["content_text"] = json.dumps(source, ensure_ascii=False)
        facts[0]["original_text"] += " 新字节"
        facts[0]["raw_value"] += " 新字节"
        facts[0]["normalized_value"] += " 新字节"
        sources[0]["acquired_at"] = "2026-08-19T09:00:00+08:00"

    (tmp_path / "changed").mkdir()
    _, changed_payload = _source_payload(tmp_path / "changed")
    mutate(changed_payload)
    changed_digest = compute_research_content_digest(changed_payload)
    changed_payload["scientific_review"]["reviewed_content_digest"] = changed_digest
    changed = FreshAResearchPackage.model_validate(changed_payload)
    second = _ingest(project, changed, changed_digest)
    assert first.source_version_ids != second.source_version_ids
    receipts = [json.loads(line) for line in receipt_path.read_text().splitlines()]
    acquired = [row for row in receipts if row["result_class"] == "content_acquired"]
    assert max(row["attempt_index"] for row in acquired) == 2
    assert len({row["receipt_id"] for row in acquired}) == len(acquired)


def test_manifest_alone_restores_adopted_source_fact_chain_into_empty_directory(
    tmp_path: Path,
) -> None:
    project, package, digest = _prepare(tmp_path / "source")
    lineage = _ingest(project, package, digest)
    exported = tmp_path / "manifest.json"
    shutil.copy2(project / lineage.evidence_snapshot.relative_path, exported)
    restored = tmp_path / "restored-empty"
    SnapshotStore(restored).restore_evidence_manifest(exported)
    with open_database(restored / "state/project.sqlite") as database:
        assert database.execute("SELECT COUNT(*) FROM fact_versions").fetchone()[0] == len(
            lineage.fact_version_ids
        )
        assert database.execute("SELECT COUNT(*) FROM evidence_fragments").fetchone()[0] == len(
            lineage.fragment_ids
        )


def test_research_submission_is_candidate_even_with_embedded_legacy_review(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    report_path, report = _source_payload(tmp_path)
    contract = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0]
    audit_payload = _audit_payload(contract["project_id"], report_path.read_bytes(), report)
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps(audit_payload, ensure_ascii=False), encoding="utf-8")
    submission = submit_product_research_package(
        project, audit_package=audit_path, report_packages={"A": report_path}
    )
    assert submission.authorization_state == "candidate_unreviewed"


def test_source_submit_db_snapshot_and_real_issuer_acceptance_chain(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    report_path, report = _source_payload(tmp_path)
    contract = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0]
    audit_payload = _audit_payload(contract["project_id"], report_path.read_bytes(), report)
    audit_path = tmp_path / "audit-chain.json"
    audit_path.write_text(json.dumps(audit_payload, ensure_ascii=False), encoding="utf-8")
    submission = submit_product_research_package(
        project, audit_package=audit_path, report_packages={"A": report_path}
    )
    package = FreshAResearchPackage.model_validate(report)
    lineage = _ingest(project, package, package.research_content_digest)

    context = build_scientific_review_context(
        project_id=contract["project_id"],
        report_kind="A",
        report_version=package.report_version,
        producer_id="research-producer",
        candidate_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        candidate_content_digest=package.research_content_digest,
        criteria_version="A-v1",
        gate_result_key="A_MATURITY_V1:passed",
        contract_version=str(contract["contract_version"]),
        coverage_set_id="coverage-A-w01",
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id="claim-snapshot-A-w01",
        sources=package.sources,
        facts=package.facts,
        claims=package.claims,
        fact_version_by_ref=lineage.fact_version_by_ref,
    )
    manifest_relative = "reports/A/w01/html.manifest.json"
    site_relative = "reports/A/w01/html"
    (project / manifest_relative).parent.mkdir(parents=True, exist_ok=True)
    (project / manifest_relative).write_text('{"kind":"artifact-manifest"}\n')
    (project / site_relative).mkdir(parents=True, exist_ok=True)
    (project / site_relative / "index.html").write_text("<!doctype html><title>A</title>")
    produced_at = datetime(2026, 8, 19, 0, 0, tzinfo=UTC)
    review_started = produced_at + timedelta(hours=1)
    review_finished = review_started + timedelta(minutes=20)
    issued_at = review_finished + timedelta(minutes=5)
    publish_production_context(project, "A", context)
    publish_scientific_review_request(
        project,
        "A",
        context,
        producer_session_id="producer-session-w01",
        produced_at=produced_at,
        portal_binding=capture_portal_artifact_binding(
            project,
            "A",
            manifest_relative=manifest_relative,
            site_relative=site_relative,
        ),
    )
    bundle = ScientificQcReviewBundle(
        producer_id=context.producer_id,
        project_id=context.project_id,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        criteria_version=context.criteria_version,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
    )
    verdict_path = project / "receipts/scientific_review/A/verdict.json"

    def runner(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        verdict = ScientificQcVerdict(
            criteria_version=context.criteria_version,
            verdict_id="verdict-w01",
            verdict="accepted",
            project_id=context.project_id,
            contract_version=context.contract_version,
            report_kind=context.report_kind,
            report_version=context.report_version,
            report_object_id=context.report_object_id,
            candidate_snapshot_id=context.candidate_snapshot_id,
            candidate_content_digest=context.candidate_content_digest,
            gate_result_key=context.gate_result_key,
            coverage_set_id=context.coverage_set_id,
            coverage_digest=context.coverage_digest,
            source_refs=context.source_refs,
            locators=context.locators,
            reviewer_id="independent-reviewer-w01",
            review_input_digest=bundle.input_digest,
            reviewed_at=review_finished,
            valid_until=datetime(2099, 1, 1, tzinfo=UTC),
        )
        verdict_path.parent.mkdir(parents=True, exist_ok=True)
        verdict_path.write_text(json.dumps(verdict.model_dump(mode="json"), ensure_ascii=False))
        return ExternalProcessResult(
            pid=4242,
            argv=argv,
            cwd=cwd,
            started_at=review_started,
            finished_at=review_finished,
            returncode=0,
        )

    outcome = issue_review_receipt(
        project_root=project,
        report_kind="A",
        reviewer_id="independent-reviewer-w01",
        review_session_id="review-session-w01",
        host="codex",
        host_executable=ReviewExecutableEvidence(
            provenance="path_resolved",
            path="/opt/homebrew/bin/codex",
            resolved_realpath="/opt/homebrew/bin/codex",
            version="codex-cli-test",
        ),
        review_argv=("exec", "scientific-review"),
        verdict_relative_path="receipts/scientific_review/A/verdict.json",
        session=ReviewHostSession(
            session_id="review-session-w01", launcher_pid=777, launcher_parent_pid=1
        ),
        runner=runner,
        clock=lambda: issued_at,
    )
    assert submission.authorization_state == "candidate_unreviewed"
    assert promote_rendered_candidate(
        project_root=project,
        current_state=RENDERED_UNREVIEWED,
        context=context,
        receipt=outcome.receipt,
        promoted_at=issued_at,
    ) == SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE
