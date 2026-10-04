"""R142: ordinary manual reruns advance review scope, never reuse old approval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application import scientific_review_transition as transition
from ci_workflow.application.fresh_research_primitives import compute_research_content_digest
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.run_service import RunContext
from ci_workflow.domain.contracts import create_project_contract
from tests.integration import test_fresh_a_scientific_review as runtime
from tests.integration import test_fresh_c_research_package as c_fixture
from tests.integration import test_r24_scientific_review_epochs as fixture
from tests.unit.reports.b import test_fresh_b_research_package as b_fixture


@pytest.mark.parametrize("previously_reviewed", [False, True])
def test_ordinary_a_rerun_creates_new_unreviewed_epoch_without_rewriting_history(
    tmp_path: Path, previously_reviewed: bool,
) -> None:
    project = runtime._write_a_project(tmp_path)
    runtime._run_ready_project(project)
    if previously_reviewed:
        runtime._stage_verified_receipt(project)
        runtime._run_ready_project(project, resume=True)
    previous_scope = transition.active_scientific_review_scope(project, "A")
    old_paths = [previous_scope.production_context_relative, previous_scope.review_request_relative]
    if previously_reviewed:
        old_paths += [previous_scope.receipt_relative, "state/scientific_review/A/issuance.json"]
    before = {path: (project / path).read_bytes() for path in old_paths}
    package_path = project / "evidence/library/a-research-package.json"
    payload = json.loads(package_path.read_text())
    payload["report_version"] = "v2"
    payload["report_data"]["report_version"] = "v2"
    payload["scientific_review"]["reviewed_content_digest"] = (
        compute_research_content_digest(payload)
    )
    package_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = runtime._run_ready_project(project, resume=True)

    assert result.outcome == "completed"
    scope = transition.active_scientific_review_scope(project, "A")
    assert scope.epoch == 1
    assert not (project / scope.receipt_relative).exists()
    assert transition.reload_production_context(project, "A").report_version == "v2"
    manifest = runtime._run_manifest(project)
    assert manifest["report_states"]["A"] == transition.RENDERED_UNREVIEWED
    assert "scientific_review_receipts" not in manifest
    assert "scientific_qc:A" not in result.node_summary
    assert {path: (project / path).read_bytes() for path in old_paths} == before


@pytest.mark.parametrize("kind", ["B", "C"])
@pytest.mark.parametrize("previously_reviewed", [False, True])
def test_ordinary_bc_rerun_has_its_own_review_scope(
    tmp_path: Path, kind: str, previously_reviewed: bool,
) -> None:
    contract = create_project_contract(
        indication="特应性皮炎", reports=[kind], outputs=["html"], cutoff="2026-09-01",
    )
    project = create_project_workspace(tmp_path / kind, contract)
    if kind == "B":
        payload = b_fixture._with_review(b_fixture._package_payload(contract.project_id))
        refresh_digest = b_fixture.compute_fresh_b_research_content_digest
    else:
        module = c_fixture._module()
        payload = c_fixture._ready_package_payload(module)
        payload["scientific_review"] = c_fixture._review(
            module, module.validate_fresh_c_content(payload).content_digest,
        )
        def refresh_digest(value):
            scientific_content = {
                key: item for key, item in value.items() if key != "scientific_review"
            }
            return module.validate_fresh_c_content(scientific_content).content_digest
    package_path = project / f"inputs/{kind.lower()}-research-package.json"
    package_path.parent.mkdir(parents=True)
    package_path.write_text(json.dumps(payload, default=str, ensure_ascii=False))

    def run():
        return runtime._run_ready_project(
            project, resume=(project / "manifests/current_run.json").exists(),
            run_context=RunContext(
                project_root=project, contract=contract, research_package_path=package_path,
            ),
        )

    run()
    if previously_reviewed:
        manifest = runtime._run_manifest(project)
        b_fixture._write_verified_scientific_review(
            project, manifest["scientific_review_contexts"][kind],
        )
        run()
    previous_scope = transition.active_scientific_review_scope(project, kind)
    old_paths = [previous_scope.production_context_relative, previous_scope.review_request_relative]
    if previously_reviewed:
        old_paths += [
            previous_scope.receipt_relative, f"state/scientific_review/{kind}/issuance.json",
        ]
    before = {path: (project / path).read_bytes() for path in old_paths}
    payload["report_version"] = "v2"
    if "report_data" in payload:
        payload["report_data"]["report_version"] = "v2"
    payload["scientific_review"]["reviewed_content_digest"] = refresh_digest(payload)
    package_path.write_text(json.dumps(payload, default=str, ensure_ascii=False))
    result = run()
    assert result.outcome == "completed"
    scope = transition.active_scientific_review_scope(project, kind)
    assert scope.epoch == 1
    assert transition.reload_production_context(project, kind).report_version == "v2"
    assert not (project / scope.receipt_relative).exists()
    manifest = runtime._run_manifest(project)
    assert manifest["report_states"][kind] == transition.RENDERED_UNREVIEWED
    assert manifest["scientific_review_epochs"][kind] == 1
    assert "scientific_review_receipts" not in manifest
    assert f"scientific_qc:{kind}" not in result.node_summary
    assert {path: (project / path).read_bytes() for path in old_paths} == before


def test_runtime_prepare_resumes_same_candidate_and_rejects_tampered_artifact(
    tmp_path: Path,
) -> None:
    world = fixture._build_world(tmp_path)
    context, _, _ = fixture._context_for_epoch(world, epoch=1)
    manifest, site = fixture._portal_relative(1)
    fixture._write_portal_bytes(world.root, 1)
    binding = transition.capture_portal_artifact_binding(
        world.root, "A", manifest_relative=manifest, site_relative=site,
    )
    prepare = transition.prepare_rendered_scientific_review
    scope = prepare(
        project_root=world.root, report_kind="A", context=context,
        producer_session_id="producer-run-e1",
        produced_at=fixture.EPOCH_TIMELINES[1]["produced"], portal_binding=binding,
    )
    original = (world.root / scope.review_request_relative).read_bytes()
    assert prepare(
        project_root=world.root, report_kind="A", context=context,
        producer_session_id="resume-run-different-id",
        produced_at=fixture.EPOCH_TIMELINES[2]["produced"], portal_binding=binding,
    ) == scope
    assert (world.root / scope.review_request_relative).read_bytes() == original
    (world.root / site / "index.html").write_text("tampered")
    with pytest.raises(transition.ScientificReviewTransitionError, match="门户|漂移"):
        prepare(
            project_root=world.root, report_kind="A", context=context,
            producer_session_id="producer-run-e1",
            produced_at=fixture.EPOCH_TIMELINES[1]["produced"], portal_binding=binding,
        )
    assert (world.root / scope.review_request_relative).read_bytes() == original
