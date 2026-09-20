from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ci_workflow", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


EXPECTED_DIRECTORIES = {
    "state/checkpoints",
    "evidence/raw",
    "evidence/fragments",
    "evidence/library",
    "evidence/manual-inbox",
    "evidence/quarantine",
    "blockers/A",
    "blockers/B",
    "blockers/C",
    "snapshots/evidence",
    "snapshots/reports/A",
    "snapshots/reports/B",
    "snapshots/reports/C",
    "reports/A",
    "reports/B",
    "reports/C",
    "logs/diagnostics",
    "corrections/inbox",
    "monitoring/inbox",
}

EXPECTED_FILES = {
    "project.yaml",
    "state/project.sqlite",
    "events/events.jsonl",
    "receipts/source_receipts.jsonl",
    "receipts/download_requests.jsonl",
    "coverage/A.json",
    "coverage/B.json",
    "coverage/C.json",
    "logs/status.md",
    "logs/run_summary.md",
    "logs/download_requests.md",
    "manifests/artifact_manifest.json",
}


def test_project_create_builds_the_complete_v13_workspace(tmp_path: Path) -> None:
    project_root = tmp_path / "慢性鼻窦炎竞品项目"
    result = _run(
        "project",
        "create",
        "--root",
        str(project_root),
        "--indication",
        "慢性鼻窦炎伴鼻息肉",
        "--reports",
        "A,B,C",
        "--outputs",
        "html",
        "--timezone",
        "Asia/Shanghai",
        "--cutoff",
        "2026-08-10",
    )
    assert result.returncode == 0, result.stderr
    for relative in EXPECTED_DIRECTORIES:
        assert (project_root / relative).is_dir(), relative
    for relative in EXPECTED_FILES:
        assert (project_root / relative).is_file(), relative

    with sqlite3.connect(project_root / "state/project.sqlite") as database:
        assert database.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    verification = verify_project_workspace(project_root)
    assert verification.contract.indication == "慢性鼻窦炎伴鼻息肉"
    assert verification.contract.contract_version == 1
    assert verification.relative_file_count == len(EXPECTED_FILES)


def test_project_create_persists_timezone_and_cutoff_without_guessing(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "历史截点项目"
    created = _run(
        "project",
        "create",
        "--root",
        str(project_root),
        "--indication",
        "重症肌无力",
        "--reports",
        "B",
        "--outputs",
        "html",
        "--timezone",
        "America/New_York",
        "--cutoff",
        "2024-02-29",
    )
    assert created.returncode == 0, created.stderr

    project = json.loads((project_root / "project.yaml").read_text(encoding="utf-8"))
    assert project["schema_version"] == "1.0"
    assert project["active_contract_version"] == 1
    assert len(project["project_contract_versions"]) == 1
    contract = project["project_contract_versions"][0]
    assert contract["timezone"] == "America/New_York"
    assert contract["data_cutoff"] == "2024-02-29T23:59:59.999999-05:00"
    assert contract["outputs"] == ["html"]
    assert "root" not in project
    assert str(project_root) not in json.dumps(project, ensure_ascii=False)

    verified = _run("project", "verify", "--root", str(project_root))
    assert verified.returncode == 0, verified.stderr
    assert "项目可继续使用" in verified.stdout


def test_project_verify_rejects_missing_structure_absolute_data_and_broken_database(
    tmp_path: Path,
) -> None:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        cutoff="2026-08-10",
    )

    missing_root = tmp_path / "缺目录"
    create_project_workspace(missing_root, contract)
    (missing_root / "snapshots/reports/B").rmdir()
    with pytest.raises(ProjectWorkspaceError, match="缺少项目目录"):
        verify_project_workspace(missing_root)

    absolute_root = tmp_path / "绝对路径"
    create_project_workspace(absolute_root, contract)
    manifest_path = absolute_root / "manifests/artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = [{"path": "/Users/example/report.pdf"}]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ProjectWorkspaceError, match="不得包含机器绝对路径"):
        verify_project_workspace(absolute_root)

    broken_root = tmp_path / "损坏数据库"
    create_project_workspace(broken_root, contract)
    (broken_root / "state/project.sqlite").write_text("不是 SQLite", encoding="utf-8")
    with pytest.raises(ProjectWorkspaceError, match="数据库无法读取"):
        verify_project_workspace(broken_root)
