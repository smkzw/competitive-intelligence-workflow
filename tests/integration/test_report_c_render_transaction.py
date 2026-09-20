"""ci-r2：C 类 HTML 渲染接入共享未发布渲染目录事务边界。

覆盖 run_service._render_html_c_minimal：
- 未发布中断残留可恢复，且只清理当前项目内当前 C 版本目录；
- 已有 manifest / 覆盖投影 / 产物清单存储绑定一律拒绝覆盖。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ci_workflow.application.run_service import (
    ContractConfigError,
    RunContext,
    _render_html_c_minimal,
)
from ci_workflow.storage.manifest_store import ArtifactManifest, ManifestStore

ROOT = Path(__file__).resolve().parents[2]
C_FIXTURE = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"

PROJECT_ID = "proj-render-txn-c"
CONTRACT_VERSION = 1
RUN_ID = "run-render-txn-c-1"


def _report_data() -> dict[str, object]:
    """从真实 C 夹具收缩出最小但能通过设计门槛的数据包。"""
    payload = json.loads(C_FIXTURE.read_text(encoding="utf-8"))
    trial = payload["trials"][0]
    product_id = trial["product_id"]
    trial_id = trial["id"]
    return {
        "schema_version": payload["schema_version"],
        "report_version": "v1",
        "indication": payload["indication"],
        "indication_id": payload["indication_id"],
        "data_cutoff": payload["data_cutoff"],
        "products": [item for item in payload["products"] if item["id"] == product_id],
        "trials": [item for item in payload["trials"] if item["id"] == trial_id],
        "observations": [
            item for item in payload["observations"] if item["trial_id"] == trial_id
        ],
    }


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return tmp_path / "项目"


def _data_path(tmp_path: Path) -> Path:
    path = tmp_path / "report-c-data.json"
    path.write_text(json.dumps(_report_data(), ensure_ascii=False), encoding="utf-8")
    return path


def _context(project_root: Path) -> RunContext:
    return RunContext(
        project_root=project_root,
        contract=SimpleNamespace(
            project_id=PROJECT_ID,
            contract_version=CONTRACT_VERSION,
        ),
    )


def _build(project_root: Path, tmp_path: Path, *, run_id: str = RUN_ID) -> tuple[str, str]:
    return _render_html_c_minimal(_context(project_root), run_id, _data_path(tmp_path))


def test_interrupted_residue_is_recoverable(project_root: Path, tmp_path: Path) -> None:
    residue = project_root / "reports" / "C" / "v1" / "html"
    residue.mkdir(parents=True)
    (residue / "index.html").write_text("<html>中断残留</html>", encoding="utf-8")

    site_rel, manifest_rel = _build(project_root, tmp_path)

    assert site_rel == "reports/C/v1/html"
    assert manifest_rel == "reports/C/v1/html.manifest.json"
    site_root = project_root / site_rel
    manifest_path = project_root / manifest_rel
    assert (site_root / "overview.html").read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "generated"
    assert manifest["artifact"]["relative_path"] == "reports/C/v1/html"
    assert not list((project_root / "reports" / "C" / "v1").glob(".render-staging.*"))


def test_recovery_cleans_only_current_project_version(
    project_root: Path, tmp_path: Path
) -> None:
    own = project_root / "reports" / "C" / "v1" / "html"
    own.mkdir(parents=True)
    (own / "index.html").write_text("<html>本版本残留</html>", encoding="utf-8")

    other_version = project_root / "reports" / "C" / "v2" / "html"
    other_version.mkdir(parents=True)
    (other_version / "index.html").write_text("<html>其他版本</html>", encoding="utf-8")

    other_report = project_root / "reports" / "B" / "v1" / "html"
    other_report.mkdir(parents=True)
    (other_report / "index.html").write_text("<html>其他报告</html>", encoding="utf-8")

    site_rel, _manifest_rel = _build(project_root, tmp_path)

    assert (project_root / site_rel / "overview.html").exists()
    assert (other_version / "index.html").read_text(encoding="utf-8") == "<html>其他版本</html>"
    assert (other_report / "index.html").read_text(encoding="utf-8") == "<html>其他报告</html>"


def test_refuses_to_overwrite_completed_binding(project_root: Path, tmp_path: Path) -> None:
    site_rel, manifest_rel = _build(project_root, tmp_path)
    site_root = project_root / site_rel
    manifest_path = project_root / manifest_rel
    original_manifest = manifest_path.read_bytes()
    original_index = (site_root / "overview.html").read_bytes()

    with pytest.raises(ContractConfigError, match="拒绝覆盖"):
        _build(project_root, tmp_path, run_id="run-render-txn-c-2")

    assert manifest_path.read_bytes() == original_manifest
    assert (site_root / "overview.html").read_bytes() == original_index


def test_refuses_when_manifest_exists_without_site(
    project_root: Path, tmp_path: Path
) -> None:
    version_root = project_root / "reports" / "C" / "v1"
    version_root.mkdir(parents=True)
    manifest = version_root / "html.manifest.json"
    manifest.write_bytes(b'{"status": "generated"}\n')

    with pytest.raises(ContractConfigError, match="拒绝覆盖"):
        _build(project_root, tmp_path)

    assert manifest.read_bytes() == b'{"status": "generated"}\n'
    assert not (version_root / "html").exists()


def test_refuses_when_artifact_store_already_binds_version(
    project_root: Path, tmp_path: Path
) -> None:
    store = project_root / "manifests" / "artifacts"
    store.mkdir(parents=True)
    (store / "accepted.json").write_text(
        json.dumps({"artifact": {"relative_path": "reports/C/v1/html"}}),
        encoding="utf-8",
    )

    with pytest.raises(ContractConfigError, match="产物清单存储"):
        _build(project_root, tmp_path)

    assert not (project_root / "reports" / "C" / "v1" / "html").exists()


def test_refuses_when_coverage_projection_exists(
    project_root: Path, tmp_path: Path
) -> None:
    version_root = project_root / "reports" / "C" / "v1"
    version_root.mkdir(parents=True)
    projection = version_root / "html.coverage-projection.json"
    projection.write_bytes(b"{}\n")

    with pytest.raises(ContractConfigError, match="覆盖投影"):
        _build(project_root, tmp_path)

    assert projection.read_bytes() == b"{}\n"


def test_committed_site_survives_manifest_store_verification(
    project_root: Path, tmp_path: Path
) -> None:
    _site_rel, manifest_rel = _build(project_root, tmp_path)
    manifest_path = project_root / manifest_rel

    manifest = ArtifactManifest.model_validate_json(manifest_path.read_bytes())
    ManifestStore(project_root).verify_artifact(manifest)
