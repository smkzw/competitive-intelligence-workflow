"""Task 10.2 R01-R02: A 类真实来源项目当前运行闭合验收。"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.real_source_acceptance import (
    RealSourceAcceptanceError,
    current_package_digest,
    current_source_commit,
    verify_current_run_exact,
)
from ci_workflow.application.run_service import RunContext, run_project, validate_run_manifest
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import ReportKind
from ci_workflow.qc.browser import (
    derive_sitemap_contract,
    load_locked_sitemap_source,
    site_directory_digest,
)
from ci_workflow.reports.common.page_registry import PageRegistry

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ACCEPTANCE_ROOT = Path(
    "/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance"
) / "task-10.2-20260901-123524"
_CUTOFF = datetime.fromisoformat("2026-07-31T23:59:59+08:00")
_SYNTHETIC_CUTOFF = datetime.fromisoformat("2026-09-01T23:59:59+08:00")
_SYNTHETIC_VERSION = "v1"
_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00"
)


def _synthetic_c_payload() -> dict[str, Any]:
    fields = (
        ("population", "target_population", "Adults and adolescents with atopic dermatitis"),
        (
            "grouping",
            "arm_randomization_blinding",
            "allocation=RANDOMIZED; interventionModel=PARALLEL; masking=DOUBLE",
        ),
        (
            "endpoint",
            "primary_endpoint_definition",
            "IGA 0 or 1 at week 16",
        ),
        ("timepoint", "primary_endpoint_timepoint", "Week 16"),
    )
    observations = [
        {
            "schema_version": "1.0",
            "row_id": f"synthetic-{field}",
            "source_row_id": f"registry-{field}",
            "observation_id": f"observation-{field}",
            "product_id": "synthetic-product",
            "trial_id": "synthetic-trial",
            "cohort_id": "synthetic-trial-all",
            "group_id": "synthetic-trial-all",
            "field_family": family,
            "field": field,
            "source_field_name": f"Registry {field}",
            "source_field_definition": "Official registry design field",
            "source_text": source_text,
            "scale": "IGA" if field == "primary_endpoint_definition" else None,
            "operator": ">=" if field == "primary_endpoint_definition" else None,
            "threshold_value": "5" if field == "primary_endpoint_definition" else None,
            "threshold_unit": "%" if field == "primary_endpoint_definition" else None,
            "assessment_timepoint": "Week 16",
            "stage": "Phase 2",
            "development_role": "key trial",
            "randomization": "randomized",
            "blinding": "double",
            "source_version_id": "synthetic-registry-v1",
            "source_locator": {
                "document_role": "ClinicalTrials.gov registry",
                "field_path": f"design.{field}",
                "url": "https://clinicaltrials.gov/study/NCT00000001",
            },
            "source_role": "clinical_trial_registry",
            "disclosure_maturity": "registry_result_or_primary_report",
            "review_state": "accepted",
            "disclosure_state": "reported_value",
            "conflict_disposition": "resolved_selected_accepted_fact",
            "compatibility_rule": "registry-current-design",
        }
        for family, field, source_text in fields
    ]
    return {
        "schema_version": "1.0",
        "report_version": _SYNTHETIC_VERSION,
        "indication_id": "atopic-dermatitis",
        "indication": "特应性皮炎",
        "data_cutoff": _CUTOFF.isoformat(),
        "report_snapshot_id": None,
        "products": [
            {
                "id": "synthetic-product",
                "name": "Synthetic design product",
                "target": "IL-13",
                "modality": "单克隆抗体",
                "phase": "II期",
                "status": "招募中",
                "regions": ["全球"],
                "route": "/c/trial-profile",
                "developer": "Synthetic sponsor",
                "mechanism": "IL-13 pathway",
                "result_status": "暂无公开关键结果",
            }
        ],
        "trials": [
            {
                "id": "synthetic-trial",
                "display_id": "NCT00000001",
                "product_id": "synthetic-product",
                "name": "Synthetic design study",
                "phase": "II期",
                "region": "全球",
                "status": "招募中",
                "sample_size": 100,
                "treatment_sample_size": 50,
                "role": "核心设计试验",
            }
        ],
        "observations": observations,
    }


def _build_synthetic_c_project(tmp_path: Path) -> Path:
    import importlib.util

    from ci_workflow.application import fresh_c_research_package as c_module

    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["C"],
        outputs=["html"],
        cutoff="2026-09-01",
        created_at=datetime.fromisoformat("2026-09-02T00:00:00+08:00"),
    )
    project = create_project_workspace(tmp_path / "synthetic-c", contract)
    c_helpers_path = ROOT / "tests/integration/test_fresh_c_research_package.py"
    c_spec = importlib.util.spec_from_file_location("_fresh_c_fixture", c_helpers_path)
    assert c_spec is not None and c_spec.loader is not None
    c_helpers = importlib.util.module_from_spec(c_spec)
    c_spec.loader.exec_module(c_helpers)
    payload = c_helpers._ready_package_payload(c_module)
    payload["data_cutoff"] = _SYNTHETIC_CUTOFF
    payload["report_data"]["data_cutoff"] = _SYNTHETIC_CUTOFF
    content = c_module.validate_fresh_c_content(payload)
    input_path = project / "evidence/library/c-research-package.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(
        json.dumps(
            {
                **payload,
                "scientific_review": c_helpers._review(
                    c_module, content.content_digest
                ),
            },
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    context = RunContext(
        project_root=project,
        contract=contract,
        research_package_path=input_path,
    )
    run = run_project(project, run_context=context)
    assert run.outcome == "completed"
    preview = validate_run_manifest(project)
    assert preview["report_states"] == {"C": "rendered_unreviewed"}

    b_helpers_path = ROOT / "tests/unit/reports/b/test_fresh_b_research_package.py"
    b_spec = importlib.util.spec_from_file_location("_scientific_review_fixture", b_helpers_path)
    assert b_spec is not None and b_spec.loader is not None
    b_helpers = importlib.util.module_from_spec(b_spec)
    b_spec.loader.exec_module(b_helpers)
    b_helpers._write_verified_scientific_review(
        project, preview["scientific_review_contexts"]["C"]
    )
    reviewed = run_project(project, resume=True, run_context=context)
    assert reviewed.outcome == "completed"
    assert validate_run_manifest(project)["report_states"] == {
        "C": "scientifically_reviewed_rendered_candidate"
    }
    manifest_path = project / "reports/C" / _SYNTHETIC_VERSION / "html.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    site_root = project / "reports/C" / _SYNTHETIC_VERSION / "html"
    site_digest, site_bytes = site_directory_digest(site_root)
    assert manifest["source_commit"] == current_source_commit(ROOT)
    assert manifest["artifact"]["sha256"] == site_digest
    assert manifest["artifact"]["byte_size"] == site_bytes
    return project


def _write_synthetic_browser_verdict(project: Path) -> Path:
    output_dir = project / "verification/C" / _SYNTHETIC_VERSION
    screenshot_dir = output_dir / "screenshots"
    trace_dir = output_dir / "traces"
    source = load_locked_sitemap_source(project, ReportKind.C, _SYNTHETIC_VERSION)
    sitemap = derive_sitemap_contract(
        PageRegistry.load(),
        ReportKind.C,
        product_ids=source.product_ids,
        trial_ids=source.trial_ids,
    )
    routes = sitemap.routes
    browsers = ("chromium", "webkit")
    viewports = ((1280, 800),)
    run_digest = hashlib.sha256(b"synthetic-browser-verdict").hexdigest()
    pages: list[dict[str, Any]] = []
    for route in routes:
        checks = [
            {
                "browser": browser,
                "viewport": list(viewport),
                "ok": True,
                "violations": [],
            }
            for browser in browsers
            for viewport in viewports
        ]
        pages.append({"route": route, "ok": True, "checks": checks})
        slug = route.lstrip("/").replace("/", "_")
        for browser in browsers:
            for width, height in viewports:
                shot = screenshot_dir / f"{slug}__{browser}__{width}x{height}.png"
                shot.parent.mkdir(parents=True, exist_ok=True)
                shot.write_bytes(_MINIMAL_PNG)

    traces: list[dict[str, str]] = []
    for browser in browsers:
        trace_path = trace_dir / f"trace__{browser}__{run_digest[:12]}.zip"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(trace_path, "w") as archive:
            archive.writestr(
                "trace.txt",
                f"run={run_digest}\n"
                f"site={source.manifest.artifact.sha256}\n",
            )
        traces.append(
            {
                "browser": browser,
                "path": f"traces/trace__{browser}__{run_digest[:12]}.zip",
                "run_digest": run_digest,
                "site_digest": source.manifest.artifact.sha256,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.json"
    payload = {
        "schema_version": "1.0",
        "tool": "verify_portal",
        "ok": True,
        "report": "C",
        "version": _SYNTHETIC_VERSION,
        "manifest_id": source.manifest.manifest_id,
        "report_snapshot_id": source.manifest.report_snapshot_id,
        "run_digest": run_digest,
        "site_digest": source.manifest.artifact.sha256,
        "browsers": list(browsers),
        "viewports": [list(viewport) for viewport in viewports],
        "routes": list(routes),
        "sitemap": {
            "ok": True,
            "expected_routes": list(routes),
            "actual_routes": list(routes),
            "message_zh": "synthetic sitemap passed",
        },
        "reachability": {
            "ok": True,
            "start_route": routes[0],
            "reachable_routes": list(routes),
            "unreachable_routes": [],
            "message_zh": "synthetic reachability passed",
        },
        "pages": pages,
        "screenshots": {
            "count": len(routes) * len(browsers) * len(viewports),
            "dir": str(screenshot_dir),
        },
        "traces": traces,
        "output_dir": str(output_dir),
        "message_zh": "synthetic browser verdict passed",
    }
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_path


def _verify_synthetic_project(project: Path) -> None:
    result = verify_current_run_exact(
        project,
        report="C",
        expected_indication="特应性皮炎",
        expected_data_cutoff=_SYNTHETIC_CUTOFF,
        expected_source_commit=current_source_commit(ROOT),
        expected_package_digest=current_package_digest(),
    )
    assert result.report == "C"


def _prepare_synthetic_project(tmp_path: Path) -> Path:
    project = _build_synthetic_c_project(tmp_path)
    _write_synthetic_browser_verdict(project)
    _verify_synthetic_project(project)
    return project


def _a_project() -> Path:
    configured = os.environ.get("CI_WORKFLOW_REAL_ACCEPTANCE_ROOT")
    if configured is None and not _DEFAULT_ACCEPTANCE_ROOT.exists():
        pytest.skip("Task 10.2 真实根尚未由 Codex 创建")
    return Path(configured or _DEFAULT_ACCEPTANCE_ROOT) / "a-real"


def test_real_a_acceptance_binds_current_run_snapshot_manifest_artifact_and_browser_verdicts(
) -> None:
    """A 节点必须从当前运行闭合到快照、清单、站点和双浏览器全路由结论。"""

    result = verify_current_run_exact(
        _a_project(),
        report="A",
        expected_indication="特应性皮炎",
        expected_data_cutoff=_CUTOFF,
        expected_source_commit=current_source_commit(ROOT),
        expected_package_digest=current_package_digest(),
    )

    assert result.report == "A"
    assert result.run_id
    assert result.report_snapshot_id
    assert result.manifest_id
    assert result.routes
    assert result.browsers == ("chromium", "webkit")
    assert result.browser_run_digest


def test_real_a_acceptance_fails_closed_on_empty_root(tmp_path: Path) -> None:
    """空根没有当前运行证据，不能被当作真实来源通过。"""

    with pytest.raises(RealSourceAcceptanceError, match="项目根不是可验收的新鲜项目"):
        verify_current_run_exact(
            tmp_path / "empty",
            report="A",
            expected_indication="特应性皮炎",
            expected_data_cutoff=_CUTOFF,
            expected_source_commit="0" * 40,
            expected_package_digest="0" * 64,
        )

def test_real_acceptance_fails_closed_on_stale_artifact_mtime(tmp_path: Path) -> None:
    """旧 HTML 产物 mtime 不得伪装成当前运行产物。"""

    project = _prepare_synthetic_project(tmp_path)
    site_root = project / "reports/C" / _SYNTHETIC_VERSION / "html"
    for path in site_root.rglob("*"):
        if path.is_file():
            os.utime(path, ns=(1_000_000_000, 1_000_000_000))

    with pytest.raises(RealSourceAcceptanceError, match="mtime|早于"):
        _verify_synthetic_project(project)


def test_real_acceptance_fails_closed_on_cross_run_manifest(tmp_path: Path) -> None:
    """跨运行 HTML 清单不得复用当前运行的产物记录。"""

    project = _prepare_synthetic_project(tmp_path)
    manifest_path = project / "reports/C" / _SYNTHETIC_VERSION / "html.manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["manifest_id"] = "cross-run-manifest"
    payload["producer_run_id"] = "cross-run-id"
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RealSourceAcceptanceError, match="复用产物摘要|输出文件摘要"):
        _verify_synthetic_project(project)


def test_real_acceptance_fails_closed_on_broken_local_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """站点中的本地断链必须在浏览器验收前失败关闭。"""

    from ci_workflow.renderers.portal import report_c

    original = report_c.render_report_c_site

    def render_with_broken_link(data: Any, site_root: Path) -> tuple[Path, ...]:
        generated = original(data, site_root)
        overview = site_root / "overview.html"
        content = overview.read_text(encoding="utf-8")
        assert "</body>" in content
        overview.write_text(
            content.replace(
                "</body>",
                '<a href="/c/not-a-real-route">断链</a></body>',
                1,
            ),
            encoding="utf-8",
        )
        return generated

    monkeypatch.setattr(report_c, "render_report_c_site", render_with_broken_link)
    project = _build_synthetic_c_project(tmp_path)

    with pytest.raises(RealSourceAcceptanceError, match="死链"):
        _verify_synthetic_project(project)


def test_real_acceptance_fails_closed_on_incomplete_browser_verdict(
    tmp_path: Path,
) -> None:
    """缺失任一浏览器/视口结论时不得接受伪通过报告。"""

    project = _prepare_synthetic_project(tmp_path)
    report_path = project / "verification/C" / _SYNTHETIC_VERSION / "report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    pages = payload["pages"]
    assert isinstance(pages, list) and pages
    checks = pages[0]["checks"]
    assert isinstance(checks, list) and len(checks) == 2
    checks.pop()
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RealSourceAcceptanceError, match="未覆盖全部浏览器/视口检查"):
        _verify_synthetic_project(project)
