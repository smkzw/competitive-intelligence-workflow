"""Task 10.2 R01-R02: B 类真实来源项目当前运行闭合验收。"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from ci_workflow.application.real_source_acceptance import (
    RealSourceAcceptanceError,
    current_package_digest,
    current_source_commit,
    verify_current_run_exact,
)

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ACCEPTANCE_ROOT = Path(
    "/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance"
) / "task-10.2-20260901-123524"
_CUTOFF = datetime.fromisoformat("2026-07-31T23:59:59+08:00")


def _b_project() -> Path:
    configured = os.environ.get("CI_WORKFLOW_REAL_ACCEPTANCE_ROOT")
    if configured is None and not _DEFAULT_ACCEPTANCE_ROOT.exists():
        pytest.skip("Task 10.2 真实根尚未由 Codex 创建")
    return Path(configured or _DEFAULT_ACCEPTANCE_ROOT) / "b-real"


def test_real_b_acceptance_binds_current_run_snapshot_manifest_artifact_and_browser_verdicts(
) -> None:
    """B 节点必须从当前运行闭合到快照、清单、站点和双浏览器全路由结论。"""

    result = verify_current_run_exact(
        _b_project(),
        report="B",
        expected_indication="阵发性睡眠性血红蛋白尿",
        expected_data_cutoff=_CUTOFF,
        expected_source_commit=current_source_commit(ROOT),
        expected_package_digest=current_package_digest(),
    )

    assert result.report == "B"
    assert result.run_id
    assert result.report_snapshot_id
    assert result.manifest_id
    assert result.routes
    assert result.browsers == ("chromium", "webkit")
    assert result.browser_run_digest


def test_real_b_acceptance_fails_closed_on_empty_root(tmp_path: Path) -> None:
    """空根没有当前运行证据，不能被当作真实来源通过。"""

    with pytest.raises(RealSourceAcceptanceError, match="项目根不是可验收的新鲜项目"):
        verify_current_run_exact(
            tmp_path / "empty",
            report="B",
            expected_indication="阵发性睡眠性血红蛋白尿",
            expected_data_cutoff=_CUTOFF,
            expected_source_commit="0" * 40,
            expected_package_digest="0" * 64,
        )
