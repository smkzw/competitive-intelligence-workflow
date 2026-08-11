from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ci_workflow", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_help_is_chinese_native_and_exposes_only_the_frozen_catalog() -> None:
    root_help = _run("--help")
    assert root_help.returncode == 0
    assert "竞品调研工作流" in root_help.stdout
    assert "package" in root_help.stdout
    assert "project" in root_help.stdout
    assert "capability" in root_help.stdout
    assert "fixture" in root_help.stdout
    assert "verify-project" not in root_help.stdout
    assert "host preflight" not in root_help.stdout
    for english_boilerplate in (
        "usage:",
        "positional arguments:",
        "options:",
        "show this help message",
        "show program's version",
    ):
        assert english_boilerplate not in root_help.stdout

    expected_help = {
        ("package", "--help"): ("verify", "核验安装包"),
        ("project", "--help"): ("create", "verify", "run", "创建竞品调研项目"),
        ("capability", "--help"): ("preflight", "检查所选任务所需能力"),
        ("fixture", "--help"): ("run", "运行固定验收案例"),
    }
    for args, expected_labels in expected_help.items():
        result = _run(*args)
        assert result.returncode == 0
        for label in expected_labels:
            assert label in result.stdout

    version = _run("--version")
    assert version.returncode == 0
    assert version.stdout.strip() == "ci-workflow 0.1.0a0"

    missing = _run("project", "create")
    assert missing.returncode == 2
    assert "缺少必填参数" in missing.stderr
    assert "error:" not in missing.stderr
    assert "the following arguments are required" not in missing.stderr
