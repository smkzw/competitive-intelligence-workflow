"""Synthetic acceptance plumbing for independent A/C portals, not browser QA."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.delivered_artifacts import read_accepted_html_artifacts
from ci_workflow.application.latest_delivery import read_latest_delivery
from ci_workflow.application.run_service import run_project, validate_run_manifest
from ci_workflow.application.visual_acceptance import accept_visual_artifact
from ci_workflow.cli import main
from ci_workflow.domain.enums import ReportKind
from ci_workflow.graph.visual_finalization import visual_contract_digest
from ci_workflow.qc.browser import load_locked_sitemap_source
from ci_workflow.storage.snapshot_store import compute_locked_snapshot
from tests.acceptance.test_visual_acceptance import _evidence, _plan, _verdict
from tests.integration.test_multi_report_product_run import (
    _a_payload,
    _c_payload,
    _submit_multi_report_project,
)
from tests.unit.reports.b.test_fresh_b_research_package import _write_verified_scientific_review


@pytest.mark.parametrize("report", ["A", "C"])
def test_a_c_can_reach_public_visual_acceptance(tmp_path: Path, report: str) -> None:
    project = _submit_multi_report_project(
        tmp_path, (report,), {report: _a_payload if report == "A" else _c_payload},
    )
    probe = StaticCapabilityProbe()
    run_project(project, require_bound_submission=True, capability_probe=probe)
    run = validate_run_manifest(project)
    _write_verified_scientific_review(project, run["scientific_review_contexts"][report])
    run_project(project, resume=True, capability_probe=probe)
    source = load_locked_sitemap_source(project, ReportKind(report), "v1")
    candidate = source.manifest
    locked = compute_locked_snapshot(
        kind="report", report=report, manifest=source.snapshot.model_dump(mode="json"),
    )
    plan = _plan(candidate, source.snapshot, locked.sha256)
    plan["page_responsibilities"][0]["claim_ids"] = list(candidate.claim_ids)
    now = datetime.now(UTC)
    evidence = _evidence(candidate, visual_contract_digest(plan), now)
    verdict = _verdict(
        candidate, visual_contract_digest(plan), visual_contract_digest(evidence), now,
    )
    paths = [
        project / "reviews" / f"{report}-{kind}.json" for kind in ("plan", "render", "verdict")
    ]
    for path, value in zip(paths, (plan, evidence, verdict), strict=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False))
    result = accept_visual_artifact(
        project, report=report, version="v1", visual_plan_path=paths[0],
        render_evidence_path=paths[1], verification_reference_path=paths[2],
    )
    assert result.manifest.report == report
    assert read_accepted_html_artifacts(project) == (result.manifest,)
    latest = read_latest_delivery(project, report)
    assert latest is not None and latest.manifest_id == result.manifest.manifest_id
    assert main([
        "project", "accept-visual", "--project", str(project), "--report", report,
        "--version", "v1", "--visual-plan", str(paths[0]),
        "--render-evidence", str(paths[1]), "--verification-reference", str(paths[2]),
    ]) == 0
