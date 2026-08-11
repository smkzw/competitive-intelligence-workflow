from __future__ import annotations

import shutil
from pathlib import Path

from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract


def test_project_remains_verifiable_after_move_and_contains_no_machine_path(
    tmp_path: Path,
) -> None:
    original = tmp_path / "原始位置" / "竞品调研"
    contract = create_project_contract(
        indication="阵发性睡眠性血红蛋白尿症",
        reports=["A", "B"],
        outputs=["pdf"],
        timezone="Asia/Shanghai",
        cutoff="2026-08-10",
    )
    create_project_workspace(original, contract)

    moved = tmp_path / "另一台电脑的模拟目录" / "已改名项目"
    moved.parent.mkdir(parents=True)
    shutil.move(str(original), moved)

    result = verify_project_workspace(moved)
    assert result.contract == contract
    assert result.project_root == moved.resolve()

    original_path = str(original.resolve()).encode()
    moved_path = str(moved.resolve()).encode()
    for file_path in moved.rglob("*"):
        if not file_path.is_file() or file_path.suffix == ".sqlite":
            continue
        content = file_path.read_bytes()
        assert original_path not in content
        assert moved_path not in content
