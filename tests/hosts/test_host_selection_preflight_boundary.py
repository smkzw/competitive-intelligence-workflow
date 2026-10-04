"""R184：单宿主和全空批次必须在入口解析/写项目之前拒绝缺失选择器。"""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ci_workflow.application import host_smoke_runner as runner


def _unreachable_layout() -> Any:
    def must_not_verify() -> None:
        raise AssertionError("缺失选择器不得先核安装布局或解析入口")

    return SimpleNamespace(verify_layout=must_not_verify)


def test_empty_batch_selection_fails_before_layout_and_project_writes(tmp_path: Path) -> None:
    with pytest.raises(runner.HostSmokeRunnerError, match="必须显式指定"):
        runner.run_installed_host_smoke(
            _unreachable_layout(), project_root=tmp_path / "projects"
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("host", runner.HOSTS)
def test_missing_single_selection_fails_before_layout_and_project_writes(
    tmp_path: Path, host: str
) -> None:
    with pytest.raises(runner.HostSmokeRunnerError, match="必须显式指定"):
        runner.run_installed_single_host_smoke(
            _unreachable_layout(),
            host=host,
            receipt_path=tmp_path / "receipt.json",
            project_root=tmp_path / "project",
        )
    assert list(tmp_path.iterdir()) == []
