from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from ci_workflow import __version__
from ci_workflow.domain.contracts import ProjectContract, validate_project_contract_document
from ci_workflow.storage.migrations import (
    MigrationError,
    apply_migrations,
    persist_project_contract,
)

_DIRECTORIES = (
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
)

_INITIAL_TEXT_FILES = {
    "events/events.jsonl": "",
    "receipts/source_receipts.jsonl": "",
    "receipts/download_requests.jsonl": "",
    "logs/status.md": "# 项目状态\n\n项目已创建，尚未开始调研。\n",
    "logs/run_summary.md": "# 运行摘要\n\n暂无运行记录。\n",
    "logs/download_requests.md": "# 待补充资料\n\n当前无需用户补充的文件。\n",
}

_INITIAL_JSON_FILES: dict[str, dict[str, Any]] = {
    **{
        f"coverage/{report}.json": {
            "schema_version": "1.0",
            "report": report,
            "status": "not_started",
        }
        for report in ("A", "B", "C")
    },
    "manifests/artifact_manifest.json": {
        "schema_version": "1.0",
        "artifacts": [],
    },
}


class ProjectWorkspaceError(ValueError):
    """项目目录或持久合同不完整。"""


@dataclass(frozen=True)
class ProjectWorkspaceVerification:
    project_root: Path
    contract: ProjectContract
    relative_file_count: int


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _project_contract_schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    path = root / "schemas/project-contract.schema.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ProjectWorkspaceError("无法读取项目合同规则") from exc
    if not isinstance(value, dict):
        raise ProjectWorkspaceError("项目合同规则顶层必须是对象")
    return cast(dict[str, Any], value)


def _project_document(contract: ProjectContract) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "workflow_version": __version__,
        "active_contract_version": contract.contract_version,
        "project_contract_versions": [contract.model_dump(mode="json")],
    }


def create_project_workspace(root: Path, contract: ProjectContract) -> Path:
    project_root = root.expanduser().resolve()
    if project_root.exists() and any(project_root.iterdir()):
        raise ProjectWorkspaceError(f"项目目录不是空目录：{project_root}")
    project_root.mkdir(parents=True, exist_ok=True)
    for relative in _DIRECTORIES:
        (project_root / relative).mkdir(parents=True, exist_ok=True)

    _atomic_json_write(project_root / "project.yaml", _project_document(contract))
    for relative, text_content in _INITIAL_TEXT_FILES.items():
        path = project_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text_content, encoding="utf-8")
    for relative, json_content in _INITIAL_JSON_FILES.items():
        _atomic_json_write(project_root / relative, json_content)

    database_path = project_root / "state/project.sqlite"
    try:
        persist_project_contract(database_path, contract)
    except (MigrationError, sqlite3.DatabaseError) as exc:
        raise ProjectWorkspaceError("项目数据库无法初始化") from exc
    return project_root


def _assert_no_absolute_values(value: Any, *, location: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_no_absolute_values(item, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_absolute_values(item, location=f"{location}[{index}]")
    elif isinstance(value, str) and Path(value).is_absolute():
        raise ProjectWorkspaceError(f"持久数据不得包含机器绝对路径：{location}")


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProjectWorkspaceError(f"缺少项目文件：{path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectWorkspaceError(f"项目文件不是有效 JSON：{path.name}") from exc
    if not isinstance(value, dict):
        raise ProjectWorkspaceError(f"项目文件顶层必须是对象：{path.name}")
    return cast(dict[str, Any], value)


def verify_project_workspace(root: Path) -> ProjectWorkspaceVerification:
    project_root = root.expanduser().resolve()
    if not project_root.is_dir():
        raise ProjectWorkspaceError(f"项目目录不存在：{project_root}")
    for relative in _DIRECTORIES:
        if not (project_root / relative).is_dir():
            raise ProjectWorkspaceError(f"缺少项目目录：{relative}")
    expected_files = {
        "project.yaml",
        "state/project.sqlite",
        *_INITIAL_TEXT_FILES,
        *_INITIAL_JSON_FILES,
    }
    for relative in expected_files:
        if not (project_root / relative).is_file():
            raise ProjectWorkspaceError(f"缺少项目文件：{relative}")

    project = _load_json_object(project_root / "project.yaml")
    expected_project_fields = {
        "schema_version",
        "workflow_version",
        "active_contract_version",
        "project_contract_versions",
    }
    if set(project) != expected_project_fields or project["schema_version"] != "1.0":
        raise ProjectWorkspaceError("项目文件字段与当前合同不一致")
    if project["workflow_version"] != __version__:
        raise ProjectWorkspaceError("项目工作流版本与当前安装包不一致")
    versions = project["project_contract_versions"]
    if not isinstance(versions, list) or not versions:
        raise ProjectWorkspaceError("项目至少需要一个合同版本")
    schema = _project_contract_schema()
    try:
        contracts = [validate_project_contract_document(item, schema) for item in versions]
    except (
        TypeError,
        ValueError,
        JsonSchemaValidationError,
        PydanticValidationError,
    ) as exc:
        raise ProjectWorkspaceError("项目合同版本无法读取") from exc
    version_numbers = [contract.contract_version for contract in contracts]
    if len(version_numbers) != len(set(version_numbers)):
        raise ProjectWorkspaceError("项目合同版本号不得重复")
    active = project["active_contract_version"]
    active_contract = next(
        (contract for contract in contracts if contract.contract_version == active),
        None,
    )
    if active_contract is None:
        raise ProjectWorkspaceError("项目指定的当前合同版本不存在")

    for relative in ("project.yaml", *_INITIAL_JSON_FILES):
        payload = _load_json_object(project_root / relative)
        _assert_no_absolute_values(payload, location=relative)
    try:
        apply_migrations(project_root / "state/project.sqlite")
        with sqlite3.connect(project_root / "state/project.sqlite") as database:
            database.execute("PRAGMA foreign_keys = ON")
            integrity = database.execute("PRAGMA integrity_check").fetchone()
            stored_contract = database.execute(
                """
                SELECT contract_json FROM project_contract_versions
                WHERE project_id = ? AND contract_version = ?
                """,
                (active_contract.project_id, active_contract.contract_version),
            ).fetchone()
    except (MigrationError, sqlite3.DatabaseError) as exc:
        raise ProjectWorkspaceError("项目数据库无法读取") from exc
    if integrity != ("ok",):
        raise ProjectWorkspaceError("项目数据库完整性检查未通过")
    expected_contract_json = json.dumps(
        active_contract.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    )
    if stored_contract is None or str(stored_contract[0]) != expected_contract_json:
        raise ProjectWorkspaceError("数据库中的当前项目合同与项目文件不一致")
    return ProjectWorkspaceVerification(
        project_root=project_root,
        contract=active_contract,
        relative_file_count=len(expected_files),
    )
