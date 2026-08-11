from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.storage.sqlite import open_database

_MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{4})_[a-z0-9_]+\.sql$")


class MigrationError(RuntimeError):
    """数据库迁移合同无法安全执行。"""


class MigrationSequenceError(MigrationError):
    """迁移版本不连续或文件名不符合合同。"""


class MigrationDriftError(MigrationError):
    """已应用迁移的内容摘要发生漂移。"""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sha256: str
    sql: str


def migration_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "migrations"


def _load_migrations(root: Path) -> tuple[Migration, ...]:
    migrations: list[Migration] = []
    for path in sorted(root.glob("*.sql")):
        match = _MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise MigrationSequenceError(f"迁移文件名不符合合同：{path.name}")
        content = path.read_text(encoding="utf-8")
        migrations.append(
            Migration(
                version=int(match.group("version")),
                name=path.name,
                sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                sql=content,
            )
        )
    versions = [migration.version for migration in migrations]
    if not versions or versions != list(range(1, len(versions) + 1)):
        raise MigrationSequenceError("迁移版本必须从 0001 开始且连续")
    return tuple(migrations)


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def apply_migrations(
    database_path: Path,
    migrations_root: Path | None = None,
) -> tuple[Migration, ...]:
    migrations = _load_migrations(
        migration_directory() if migrations_root is None else migrations_root
    )
    applied_now: list[Migration] = []
    with open_database(database_path) as database:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                sha256 TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        database.commit()
        existing = {
            int(row[0]): (str(row[1]), str(row[2]))
            for row in database.execute(
                "SELECT version, name, sha256 FROM schema_migrations"
            )
        }
        for migration in migrations:
            recorded = existing.get(migration.version)
            if recorded is not None:
                if recorded != (migration.name, migration.sha256):
                    raise MigrationDriftError(
                        f"已应用迁移的文件名或摘要不一致：{migration.name}"
                    )
                continue
            name = _escape_sql_literal(migration.name)
            digest = _escape_sql_literal(migration.sha256)
            script = (
                "BEGIN IMMEDIATE;\n"
                f"{migration.sql}\n"
                "INSERT INTO schema_migrations (version, name, sha256, applied_at) "
                f"VALUES ({migration.version}, '{name}', '{digest}', "
                "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));\n"
                f"PRAGMA user_version = {migration.version};\n"
                "COMMIT;\n"
            )
            try:
                database.executescript(script)
            except sqlite3.DatabaseError:
                database.rollback()
                raise
            applied_now.append(migration)
    return tuple(applied_now)


def persist_project_contract(database_path: Path, contract: ProjectContract) -> None:
    apply_migrations(database_path)
    payload = json.dumps(contract.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    with open_database(database_path) as database:
        existing = database.execute(
            """
            SELECT contract_json FROM project_contract_versions
            WHERE project_id = ? AND contract_version = ?
            """,
            (contract.project_id, contract.contract_version),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != payload:
                raise MigrationDriftError("同一项目合同版本的内容不一致")
            return
        database.execute(
            """
            INSERT INTO project_contract_versions (
                project_id, contract_version, contract_json, timezone, data_cutoff, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                contract.project_id,
                contract.contract_version,
                payload,
                contract.timezone,
                contract.data_cutoff.isoformat(),
                contract.created_at.isoformat(),
            ),
        )
