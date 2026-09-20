from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.run_service import (
    RunContext,
    run_project,
    validate_run_manifest,
)
from ci_workflow.application.visual_acceptance import (
    VisualAcceptanceError,
    accept_visual_artifact,
)
from ci_workflow.cli import main
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import ReportKind
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.recovery import format_object_id
from ci_workflow.graph.visual_finalization import visual_contract_digest
from ci_workflow.qc.browser import load_locked_sitemap_source
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import compute_locked_snapshot

DOMAINS = (
    "copy_zh",
    "hierarchy_density",
    "typography_spacing",
    "color_legibility",
    "charts_tables",
    "interaction_consistency",
    "format_rendering",
)
TRIGGERS = (
    "page_load",
    "filter_change",
    "drill_down",
    "search",
    "keyboard",
    "reduced_motion",
)
ENGINES = ("chromium", "webkit")
WIDTHS = (768, 1024, 1440)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _target(engine: str, width: int) -> dict[str, Any]:
    return {
        "target_id": f"{engine}-{width}",
        "engine": engine,
        "page_id": "overview",
        "viewport": {"width": width, "height": 900},
        "screenshot_path": f"reviews/screenshots/{engine}-{width}.png",
        "screenshot_sha256": "c" * 64,
        "metrics": {
            "horizontal_overflow_px": 0,
            "clipped_text_count": 0,
            "label_overlap_count": 0,
            "unreadable_label_count": 0,
        },
        "unavailable_required_fields": [],
        "responsive_alternatives": [],
        "interaction_checks": [
            {
                "trigger": trigger,
                "passed": True,
                "evidence": f"{trigger}状态已在真实浏览器复核",
            }
            for trigger in TRIGGERS
        ],
        "visible_text_scan": {
            "passed": True,
            "engineering_tokens_found": [],
            "untranslated_tokens_found": [],
        },
    }


def _plan(
    candidate: ArtifactManifest, snapshot: Any, snapshot_sha256: str
) -> dict[str, Any]:
    return {
        "$schema": "schemas/visual-finalization-plan.schema.json",
        "schema_version": "1.0",
        "plan_id": f"visual-plan-{candidate.report}-html-v1",
        "report_kind": candidate.report,
        "report_version": candidate.report_version,
        "format": "html",
        "route_id": "portal",
        "report_snapshot_sha256": snapshot_sha256,
        "report_snapshot": {
            "snapshot_id": candidate.report_snapshot_id,
            "report": candidate.report,
            "report_version": candidate.report_version,
            "evidence_snapshot_id": snapshot.evidence_snapshot_id,
            "claim_snapshot_id": snapshot.claim_snapshot_id,
            "coverage_set_id": snapshot.coverage_set_id,
        },
        "design_contract_sha256": candidate.design_contract.digest,
        "design_contract": {
            "manifest": "contracts/kangzhe/manifest.json",
            "contract_version": "1.0",
            "route_id": "portal",
            "loaded_files": [
                "contracts/kangzhe/design_specs/ROUTER.md",
                "contracts/kangzhe/design_specs/core.md",
                "contracts/kangzhe/design_specs/project_profile.md",
                "contracts/kangzhe/design_specs/track_site.md",
            ],
        },
        "scientific_snapshot_immutable": True,
        "audience": {
            "primary_role": "资深临床试验医学人员",
            "language": "zh-CN",
            "reading_tasks": ["比较疗效与安全性", "下钻到试验和证据定位"],
            "visible_program_state": False,
        },
        "page_responsibilities": [
            {
                "page_id": "overview",
                "page_type": "首页",
                "primary_question": "当前竞品格局的关键差异是什么？",
                "purpose": "先呈现总体比较，再提供详情入口",
                "information_hierarchy": ["总体结论", "关键疗效", "关键安全性"],
                "claim_ids": ["claim-b-001"],
                "source_facts_preserved": True,
            }
        ],
        "visual_variables": {
            "theme": "kangzhe",
            "palette_tokens": ["kz-orange", "kz-yellow", "kz-risk", "kz-med-blue"],
            "department_tokens": {
                "MED": "kz-orange",
                "CO": "kz-med-blue",
                "DMST": "kz-stats-green",
                "PV": "kz-pv",
            },
            "surface_tokens": ["kz-white", "kz-bg", "kz-surface-warm"],
            "font_stack": ["Microsoft YaHei", "Arial"],
            "font_sizes_px": [16, 19, 32],
            "spacing_tokens_px": [4, 8, 12, 16, 24, 32, 40, 56],
            "motion_tokens": ["none", "dur", "ease-out"],
            "reduced_motion_supported": True,
            "export_freeze_supported": True,
        },
        "chart_syntax": [
            {
                "chart_id": "efficacy-overview",
                "question": "各治疗组主要终点变化如何？",
                "mark": "bar",
                "dimensions": {
                    "x": "治疗组",
                    "y": "主要终点变化值",
                    "color": "治疗组",
                    "label": "数值与时间点",
                },
                "source_claim_ids": ["claim-b-001"],
            }
        ],
        "table_syntax": [
            {
                "table_id": "efficacy-detail",
                "purpose": "保留图表对应的完整数据行",
                "columns": ["产品", "终点", "时间点", "治疗组值", "对照组值"],
                "completeness": "complete",
                "after_chart": True,
                "source_claim_ids": ["claim-b-001"],
            }
        ],
        "interaction_states": [
            {
                "state_id": trigger.replace("_", "-"),
                "trigger": trigger,
                "expected_behavior": "状态变化后仍可读、可恢复并保留证据依据",
                "keyboard_accessible": True,
                "reduced_motion_behavior": "不依赖动画承载信息",
                "frozen_behavior": "导出时保持稳定终态",
            }
            for trigger in TRIGGERS
        ],
        "acceptance_matrix": [
            {
                "domain": domain,
                "criteria": [f"在真实呈现截图中核对{domain}的具体对象、状态与数值"],
                "required": True,
            }
            for domain in DOMAINS
        ],
        "planner_identity": "visual-design-director/test-run",
        "planner_role": "visual-design-director",
        "created_at": candidate.generated_at.isoformat(),
    }


def _evidence(
    candidate: ArtifactManifest, plan_digest: str, created_at: datetime
) -> dict[str, Any]:
    return {
        "$schema": "schemas/visual-render-evidence.schema.json",
        "schema_version": "1.0",
        "evidence_id": f"render-evidence-{candidate.report}-html-v1",
        "report_kind": candidate.report,
        "report_version": candidate.report_version,
        "format": "html",
        "run_id": "render-deliver-test-run",
        "visual_plan_digest": plan_digest,
        "candidate_artifact_digest": candidate.artifact.sha256,
        "producer_identity": "render-deliver/test-run",
        "render_targets": [
            _target(engine, width) for engine in ENGINES for width in WIDTHS
        ],
        "defects": [],
        "created_at": created_at.isoformat(),
    }


def _verdict(
    candidate: ArtifactManifest,
    plan_digest: str,
    render_digest: str,
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "$schema": "schemas/visual-verification-reference.schema.json",
        "schema_version": "1.0",
        "verdict_id": f"visual-verdict-{candidate.report}-html-v1",
        "format": "html",
        "visual_plan_digest": plan_digest,
        "candidate_artifact_digest": candidate.artifact.sha256,
        "render_evidence_digest": render_digest,
        "producer_identity": "render-deliver/test-run",
        "verifier_identity": "visual-package-qc/test-review",
        "verdict": "accepted",
        "domains": [
            {
                "domain": domain,
                "status": "accepted",
                "criteria": [f"在截图中核对{domain}对应对象、状态和数值"],
                "evidence_refs": ["chromium-768#" + domain],
            }
            for domain in DOMAINS
        ],
        "created_at": created_at.isoformat(),
    }


def _run_scientific_b_project(project: Path) -> None:
    import importlib.util

    helpers_path = (
        Path(__file__).resolve().parents[1]
        / "unit"
        / "reports"
        / "b"
        / "test_fresh_b_research_package.py"
    )
    spec = importlib.util.spec_from_file_location("_fresh_b_package_fixture", helpers_path)
    assert spec is not None and spec.loader is not None
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["B"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    create_project_workspace(project, contract)
    package_path = project / "evidence/library/b-research-package.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps(
            helpers._with_review(helpers._package_payload(contract.project_id)),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result = run_project(
        project,
        capability_probe=StaticCapabilityProbe(),
        run_context=RunContext(
            project_root=project,
            contract=contract,
            research_package_path=package_path,
        ),
    )
    assert result.outcome == "completed"
    preview = validate_run_manifest(project)
    assert preview["report_states"] == {"B": "rendered_unreviewed"}
    helpers._write_verified_scientific_review(
        project, preview["scientific_review_contexts"]["B"]
    )
    reviewed = run_project(
        project,
        capability_probe=StaticCapabilityProbe(),
        resume=True,
        run_context=RunContext(
            project_root=project,
            contract=contract,
            research_package_path=package_path,
        ),
    )
    assert reviewed.outcome == "completed"


def _prepare_case(tmp_path: Path) -> tuple[Path, ArtifactManifest, Path, Path, Path]:
    project = tmp_path / "b-scientific-visual-acceptance"
    _run_scientific_b_project(project)
    run_manifest = validate_run_manifest(project)
    assert run_manifest["report_states"] == {
        "B": "scientifically_reviewed_rendered_candidate"
    }
    candidate_path = project / "reports/B/v1/html.manifest.json"
    assert candidate_path.is_file()
    candidate = ArtifactManifest.model_validate(_load(candidate_path))
    assert candidate.status == "quality_check"

    source = load_locked_sitemap_source(
        project, ReportKind.B, candidate.report_version
    )
    snapshot_sha256 = compute_locked_snapshot(
        kind="report",
        report="B",
        manifest=source.snapshot.model_dump(mode="json"),
    ).sha256
    plan = _plan(candidate, source.snapshot, snapshot_sha256)
    plan_path = project / "reviews" / "visual-plan.json"
    evidence_path = project / "reviews" / "render-evidence.json"
    verdict_path = project / "reviews" / "visual-verdict.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    now = max(datetime.now(UTC), candidate.artifact.modified_at.astimezone(UTC))
    evidence = _evidence(candidate, visual_contract_digest(plan), now)
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    verdict = _verdict(
        candidate,
        visual_contract_digest(plan),
        visual_contract_digest(evidence),
        now,
    )
    verdict_path.write_text(json.dumps(verdict, ensure_ascii=False), encoding="utf-8")
    return project, candidate, plan_path, evidence_path, verdict_path


def test_visual_acceptance_persists_successor_and_preserves_run_manifest(tmp_path: Path) -> None:
    project, candidate, plan_path, evidence_path, verdict_path = _prepare_case(tmp_path)

    result = accept_visual_artifact(
        project,
        version=candidate.report_version,
        visual_plan_path=plan_path,
        render_evidence_path=evidence_path,
        verification_reference_path=verdict_path,
    )

    assert result.manifest.status == "accepted"
    from ci_workflow.application.delivered_artifacts import read_accepted_html_artifacts

    assert read_accepted_html_artifacts(project) == (result.manifest,)
    assert result.manifest.supersedes_manifest_id == candidate.manifest_id
    assert result.stored_manifest_path.is_file()
    assert result.predecessor_manifest_path.is_file()
    assert (
        ArtifactManifest.model_validate_json(result.stored_manifest_path.read_bytes())
        == result.manifest
    )
    assert ArtifactManifest.model_validate_json(
        result.predecessor_manifest_path.read_bytes()
    ) == candidate
    assert ArtifactManifest.model_validate_json(
        (project / "reports" / "B" / candidate.report_version / "html.manifest.json").read_bytes()
    ).status == "quality_check"

    state = GraphExecutor(project, run_id=result.acceptance_run_id).state()
    assert state["format_artifact"][format_object_id("report_B", "html")] == "delivery_ready"
    validate_run_manifest(project)

    assert (
        main(
            [
                "project",
                "accept-visual",
                "--root",
                str(project),
                "--version",
                candidate.report_version,
                "--visual-plan",
                str(plan_path),
                "--render-evidence",
                str(evidence_path),
                "--verification-reference",
                str(verdict_path),
            ]
        )
        == 0
    )
    replay = accept_visual_artifact(
        project,
        version=candidate.report_version,
        visual_plan_path=plan_path,
        render_evidence_path=evidence_path,
        verification_reference_path=verdict_path,
    )
    assert replay.manifest == result.manifest
    assert replay.transition_event_ids == ()


def test_visual_acceptance_rejects_stale_render_evidence(tmp_path: Path) -> None:
    project, candidate, plan_path, evidence_path, verdict_path = _prepare_case(tmp_path)
    evidence = _load(evidence_path)
    evidence["created_at"] = (
        candidate.artifact.modified_at.astimezone(UTC) - timedelta(seconds=1)
    ).isoformat()
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(VisualAcceptanceError, match="早于当前 HTML 候选产物"):
        accept_visual_artifact(
            project,
            version=candidate.report_version,
            visual_plan_path=plan_path,
            render_evidence_path=evidence_path,
            verification_reference_path=verdict_path,
        )


def test_visual_acceptance_rejects_mismatched_render_artifact(tmp_path: Path) -> None:
    project, candidate, plan_path, evidence_path, verdict_path = _prepare_case(tmp_path)
    evidence = _load(evidence_path)
    evidence["candidate_artifact_digest"] = "a" * 64
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(VisualAcceptanceError, match="当前候选产物"):
        accept_visual_artifact(
            project,
            version=candidate.report_version,
            visual_plan_path=plan_path,
            render_evidence_path=evidence_path,
            verification_reference_path=verdict_path,
        )


def test_visual_acceptance_rejects_missing_verification_evidence(tmp_path: Path) -> None:
    project, candidate, plan_path, evidence_path, verdict_path = _prepare_case(tmp_path)
    verdict_path.unlink()

    with pytest.raises(VisualAcceptanceError, match="缺少独立视觉审阅结论"):
        accept_visual_artifact(
            project,
            version=candidate.report_version,
            visual_plan_path=plan_path,
            render_evidence_path=evidence_path,
            verification_reference_path=verdict_path,
        )
