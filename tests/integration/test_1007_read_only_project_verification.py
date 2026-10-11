"""Reading locked evidence must not perform schema upgrades or alter bytes."""
from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract


def test_read_only_verification_does_not_migrate_or_change_durable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "locked"
    create_project_workspace(root, create_project_contract(
        indication="结节性痒疹", reports=["A", "B"], outputs=["html"], cutoff="2026-10-07",
    ))
    # SQLite may create volatile WAL coordination sidecars even in mode=ro.
    # Do not use immutable=1 to hide concurrent WAL facts. Durable source/state
    # bytes, schema and contract files must remain unchanged.
    volatile = {"project.sqlite-wal", "project.sqlite-shm"}
    before = {p.relative_to(root): sha256(p.read_bytes()).hexdigest()
              for p in root.rglob("*") if p.is_file() and p.name not in volatile}

    def forbidden_migration(_path: Path) -> None:
        raise AssertionError("read-only verification may not invoke migrations")

    monkeypatch.setattr(
        "ci_workflow.application.project_service.apply_migrations", forbidden_migration,
    )
    assert verify_project_workspace(root, read_only=True).contract.indication == "结节性痒疹"
    assert {p.relative_to(root): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and p.name not in volatile} == before


def test_read_only_missing_contract_schema_fails_without_repair(tmp_path: Path) -> None:
    root = tmp_path / "requires-explicit-upgrade"
    create_project_workspace(root, create_project_contract(
        indication="结节性痒疹", reports=["B"], outputs=["html"], cutoff="2026-10-07",
    ))
    database_path = root / "state/project.sqlite"
    with sqlite3.connect(database_path) as database:
        database.execute("DROP TABLE project_contract_versions")
    before = sha256(database_path.read_bytes()).hexdigest()
    with pytest.raises(ProjectWorkspaceError, match="数据库无法读取"):
        verify_project_workspace(root, read_only=True)
    assert sha256(database_path.read_bytes()).hexdigest() == before
