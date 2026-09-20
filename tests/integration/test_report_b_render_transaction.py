"""ci-r2：B 类 HTML 渲染接入共享未发布渲染目录事务边界。

- 中断留下的未发布残留必须可恢复：重跑清理本版本精确残留并产出完整
  站点与清单，而不是永久拒绝。
- 任何已有 manifest 或完成绑定一律拒绝覆盖，既有字节保持不变。
- 清理动作只作用于当前项目内当前 B 版本目录，不触碰其他报告/版本。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_b import (
    ReportBPortalError,
    build_report_b_artifact,
)
from ci_workflow.storage.manifest_store import ArtifactManifest, ManifestStore

PROJECT_ID = "proj-render-txn-b"
CONTRACT_VERSION = 1
RUN_ID = "run-render-txn-b-1"


def _report_data() -> dict[str, object]:
    """最小但合同闭合的 B 类报告数据（兼容遗留 report-data 行合同）。"""
    return {
        "schema_version": "1.0",
        "report_version": "v1",
        "indication": "测试适应症",
        "data_cutoff": "2026-01-01T00:00:00+08:00",
        "products": [
            {
                "id": "demo-product",
                "name": "演示产品",
                "target": "IL-13",
                "modality": "单克隆抗体",
                "phase": "II期",
                "status": "开发中",
                "regions": ["中国"],
                "route": "皮下注射",
                "developer": "演示制药",
                "mechanism": "IL-13抑制剂",
                "result_status": "临床前",
            }
        ],
        "trials": [
            {
                "id": "nct00000001",
                "display_id": "NCT00000001",
                "product_id": "demo-product",
                "name": "Demo Trial",
                "phase": "II期",
                "region": "中国",
                "status": "RECRUITING",
                "sample_size": 120,
                "treatment_sample_size": 60,
                "role": "确证性研究",
            }
        ],
        "efficacy": [
            {
                "row_id": "eff-1",
                "product_id": "demo-product",
                "trial_id": "nct00000001",
                "endpoint": "EASI-75应答率",
                "timepoint": "第16周",
                "arm": "治疗组",
                "value": 60.0,
                "numerator": 36,
                "denominator": 60,
                "unit": "%",
                "population": "全分析集",
            }
        ],
        "safety": [
            {
                "row_id": "sae-1",
                "product_id": "demo-product",
                "trial_id": "nct00000001",
                "category": "治疗期间不良事件",
                "term": "头痛",
                "value": 10.0,
                "numerator": 6,
                "denominator": 60,
                "unit": "%",
                "time_window": "全程",
                "disclosure_state": "已公开",
            }
        ],
        "regulatory": [
            {
                "product_id": "demo-product",
                "track": "中国",
                "event": "临床试验批准",
                "date": "2025-01-01",
                "status": "已批准",
            }
        ],
        "companies": [
            {
                "product_id": "demo-product",
                "relationship": "授权引进",
                "licensor": "境外许可方",
                "licensee": "演示制药",
                "territory": "中国",
                "transaction": "许可合作",
            }
        ],
        "patents": [
            {
                "product_id": "demo-product",
                "family": "EP0000001",
                "display_family": "EP0000001",
                "jurisdiction": "中国",
                "scope": "化合物",
                "expiry": "2035-01-01",
                "exclusivity": "独占至2035年",
            }
        ],
        "history": [
            {
                "product_id": "demo-product",
                "status": "II期进行中",
                "date": "2026-01-01",
                "observation": "按计划推进",
            }
        ],
        "sources": [
            {
                "source": "ClinicalTrials.gov 公开登记",
                "scope": "试验登记",
                "maturity": "公开",
                "limitation": "登记更新存在延迟",
            }
        ],
    }


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return tmp_path / "项目"


def _data_path(tmp_path: Path) -> Path:
    path = tmp_path / "report-b-data.json"
    path.write_text(json.dumps(_report_data(), ensure_ascii=False), encoding="utf-8")
    return path


def _build(project_root: Path, tmp_path: Path, *, run_id: str = RUN_ID):
    return build_report_b_artifact(
        project_root=project_root,
        data_path=_data_path(tmp_path),
        project_id=PROJECT_ID,
        contract_version=CONTRACT_VERSION,
        run_id=run_id,
    )


def test_interrupted_residue_is_recoverable(project_root: Path, tmp_path: Path) -> None:
    residue = project_root / "reports" / "B" / "v1" / "html"
    residue.mkdir(parents=True)
    (residue / "index.html").write_text("<html>中断残留</html>", encoding="utf-8")

    site_root, manifest_path, _snapshot_id = _build(project_root, tmp_path)

    assert (site_root / "overview.html").read_text(encoding="utf-8")
    assert manifest_path == project_root / "reports" / "B" / "v1" / "html.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "quality_check"
    assert manifest["artifact"]["relative_path"] == "reports/B/v1/html"
    assert not list((project_root / "reports" / "B" / "v1").glob(".render-staging.*"))


def test_recovery_cleans_only_current_project_version(
    project_root: Path, tmp_path: Path
) -> None:
    own = project_root / "reports" / "B" / "v1" / "html"
    own.mkdir(parents=True)
    (own / "index.html").write_text("<html>本版本残留</html>", encoding="utf-8")

    other_version = project_root / "reports" / "B" / "v2" / "html"
    other_version.mkdir(parents=True)
    (other_version / "index.html").write_text("<html>其他版本</html>", encoding="utf-8")

    other_report = project_root / "reports" / "A" / "v1" / "html"
    other_report.mkdir(parents=True)
    (other_report / "index.html").write_text("<html>其他报告</html>", encoding="utf-8")

    site_root, _manifest_path, _snapshot_id = _build(project_root, tmp_path)

    assert (site_root / "overview.html").exists()
    assert (other_version / "index.html").read_text(encoding="utf-8") == "<html>其他版本</html>"
    assert (other_report / "index.html").read_text(encoding="utf-8") == "<html>其他报告</html>"


def test_refuses_to_overwrite_completed_binding(project_root: Path, tmp_path: Path) -> None:
    site_root, manifest_path, _snapshot_id = _build(project_root, tmp_path)
    original_manifest = manifest_path.read_bytes()
    original_index = (site_root / "overview.html").read_bytes()

    with pytest.raises(ReportBPortalError, match="拒绝覆盖"):
        _build(project_root, tmp_path, run_id="run-render-txn-b-2")

    assert manifest_path.read_bytes() == original_manifest
    assert (site_root / "overview.html").read_bytes() == original_index


def test_refuses_when_manifest_exists_without_site(
    project_root: Path, tmp_path: Path
) -> None:
    version_root = project_root / "reports" / "B" / "v1"
    version_root.mkdir(parents=True)
    manifest = version_root / "html.manifest.json"
    manifest.write_bytes(b'{"status": "quality_check"}\n')

    with pytest.raises(ReportBPortalError, match="拒绝覆盖"):
        _build(project_root, tmp_path)

    assert manifest.read_bytes() == b'{"status": "quality_check"}\n'
    assert not (version_root / "html").exists()


def test_refuses_when_artifact_store_already_binds_version(
    project_root: Path, tmp_path: Path
) -> None:
    store = project_root / "manifests" / "artifacts"
    store.mkdir(parents=True)
    (store / "accepted.json").write_text(
        json.dumps({"artifact": {"relative_path": "reports/B/v1/html"}}),
        encoding="utf-8",
    )

    with pytest.raises(ReportBPortalError, match="产物清单存储"):
        _build(project_root, tmp_path)

    assert not (project_root / "reports" / "B" / "v1" / "html").exists()


def test_refuses_when_coverage_projection_exists(
    project_root: Path, tmp_path: Path
) -> None:
    version_root = project_root / "reports" / "B" / "v1"
    version_root.mkdir(parents=True)
    projection = version_root / "html.coverage-projection.json"
    projection.write_bytes(b"{}\n")

    with pytest.raises(ReportBPortalError, match="覆盖投影"):
        _build(project_root, tmp_path)

    assert projection.read_bytes() == b"{}\n"


def test_committed_site_survives_manifest_store_verification(
    project_root: Path, tmp_path: Path
) -> None:
    _site_root, manifest_path, _snapshot_id = _build(project_root, tmp_path)

    manifest = ArtifactManifest.model_validate_json(manifest_path.read_bytes())
    ManifestStore(project_root).verify_artifact(manifest)
