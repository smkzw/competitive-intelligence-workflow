"""Task 3.6 fixture 运行器：从唯一目录验证案例输入后创建隔离项目并调用 RunService。

案例必须通过 fixture-case schema（含 indication/timezone/data_cutoff/created_at
必填与真实日期校验）、case_digest 重算和逐输入 SHA-256 校验后才允许运行。
渲染器可用性检查位于完整 catalog/摘要/输入完整性校验之后。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    create_project_workspace,
)
from ci_workflow.application.run_service import (
    RunContext,
    RunResult,
    _check_renderer_availability,
    run_project,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import OutputFormat, ReportKind


class FixtureCaseError(ValueError):
    """案例目录、catalog、schema 或输入验证失败。"""


@dataclass(frozen=True)
class FixtureRunResult:
    """FixtureRunner 返回值。"""

    run_result: RunResult
    case_id: str
    case_digest: str
    project_root: Path


# ─── Schema validation ────────────────────────────────────────────────────

def _fixture_format_checker() -> FormatChecker:
    """fixture-case schema 的格式检查器：真实日期与带偏移日期时间。"""

    checker = FormatChecker()

    def is_iso_date_or_datetime(value: object) -> bool:
        if not isinstance(value, str) or not value:
            return False
        try:
            if "T" in value:
                datetime.fromisoformat(value)
            else:
                date.fromisoformat(value)
        except ValueError:
            return False
        return True

    def is_offset_datetime(value: object) -> bool:
        if not isinstance(value, str) or not value:
            return False
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return False
        return parsed.tzinfo is not None and parsed.utcoffset() is not None

    checker.checkers["iso-date-or-datetime"] = (is_iso_date_or_datetime, ())
    checker.checkers["offset-date-time"] = (is_offset_datetime, ())
    return checker


def _load_fixture_schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    path = root / "schemas" / "fixture-case.schema.json"
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise FixtureCaseError(f"无法读取 fixture-case schema：{path}") from exc
    return cast(dict[str, Any], schema)


def _validate_case_against_schema(case: dict[str, Any], schema: dict[str, Any]) -> None:
    Draft202012Validator(
        schema,
        format_checker=_fixture_format_checker(),
    ).validate(case)


# ─── Duplicate key detection ───────────────────────────────────────────────

class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _unique_key_constructor(
    loader: yaml.SafeLoader, node: yaml.MappingNode
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise FixtureCaseError(f"YAML 文件存在重复键：{key}")
        mapping[key] = loader.construct_object(value_node)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _unique_key_constructor,
)


# ─── Catalog loading and validation ────────────────────────────────────────

def _load_catalog(catalog_path: Path) -> dict[str, Any]:
    try:
        text = catalog_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixtureCaseError(f"无法读取 catalog：{catalog_path}") from exc
    try:
        data = yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise FixtureCaseError(f"catalog.yaml 不是有效 YAML：{exc}") from exc
    if not isinstance(data, dict):
        raise FixtureCaseError("catalog.yaml 顶层必须是对象")
    return data


def _compute_case_digest(case: dict[str, Any]) -> str:
    """案例内容确定性摘要：全部声明字段（含 indication/timezone/data_cutoff/created_at）。"""
    canonical = json.dumps(
        {
            "id": case["id"],
            "description_zh": case["description_zh"],
            "indication": case["indication"],
            "timezone": case["timezone"],
            "data_cutoff": case["data_cutoff"],
            "created_at": case["created_at"],
            "reports": sorted(case["reports"]),
            "outputs": sorted(case["outputs"]),
            "inputs": sorted(
                [
                    {"path": inp["path"], "role": inp["role"], "sha256": inp["sha256"]}
                    for inp in case["inputs"]
                ],
                key=lambda x: x["path"],
            ),
            "expected": case["expected"],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _inventory_case_files(case_dir: Path) -> set[str]:
    """列出 case_dir 下所有常规文件的相对 POSIX 路径。"""
    if not case_dir.is_dir():
        return set()
    return {
        str(path.relative_to(case_dir).as_posix())
        for path in case_dir.rglob("*")
        if path.is_file()
    }


def _validate_catalog(
    catalog: dict[str, Any],
    *,
    case_root_base: Path,
    schema: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """校验 catalog 及每个案例，返回 {case_id: case_dict}。"""
    if catalog.get("schema_version") != "1.0":
        raise FixtureCaseError("catalog.yaml schema_version 必须为 1.0")
    cases = catalog.get("cases")
    if not isinstance(cases, list) or not cases:
        raise FixtureCaseError("catalog.yaml 必须包含非空 cases 列表")
    seen_ids: set[str] = set()
    result: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise FixtureCaseError(f"案例 #{index} 不是对象")
        try:
            _validate_case_against_schema(case, schema)
        except JsonSchemaValidationError as exc:
            raise FixtureCaseError(
                f"案例 {case.get('id', index)} 不符合 fixture-case schema："
                f"{exc.message}"
            ) from exc
        case_id = case["id"]
        if case_id in seen_ids:
            raise FixtureCaseError(f"案例 ID 重复：{case_id}")
        seen_ids.add(case_id)
        expected_digest = case["case_digest"]
        actual_digest = _compute_case_digest(case)
        if actual_digest != expected_digest:
            raise FixtureCaseError(
                f"案例 {case_id} 的 case_digest 不匹配："
                f"期望 {expected_digest}，实际 {actual_digest}"
            )
        case_dir = case_root_base / case_id
        for inp in case["inputs"]:
            inp_path = case_dir / inp["path"]
            resolved = inp_path.resolve()
            case_resolved = case_dir.resolve()
            if not resolved.is_relative_to(case_resolved):
                raise FixtureCaseError(
                    f"案例 {case_id} 的输入路径越界：{inp['path']}"
                )
            if not inp_path.is_file():
                raise FixtureCaseError(
                    f"案例 {case_id} 的输入文件不存在：{inp['path']}"
                )
            actual_sha = hashlib.sha256(inp_path.read_bytes()).hexdigest()
            if actual_sha != inp["sha256"]:
                raise FixtureCaseError(
                    f"案例 {case_id} 的输入文件摘要不匹配：{inp['path']}"
                )
        declared_input_paths = {inp["path"] for inp in case["inputs"]}
        if case_dir.is_dir():
            actual_files = _inventory_case_files(case_dir)
            undeclared = actual_files - declared_input_paths
            if undeclared:
                raise FixtureCaseError(
                    f"案例 {case_id} 的输入目录包含未声明文件："
                    f"{', '.join(sorted(undeclared))}"
                )
        result[case_id] = case
    return result


# ─── Fixture run ───────────────────────────────────────────────────────────

def _get_case_root_base(catalog_path: Path) -> Path:
    """案例根目录：catalog.yaml 所在目录下的 synthetic/ 子目录。"""
    synthetic = catalog_path.parent / "synthetic"
    if synthetic.is_dir():
        return synthetic
    return catalog_path.parent


def _parse_case_dates(case: dict[str, Any]) -> tuple[str, datetime]:
    """解析案例日期字段；空值/无偏移/非法格式一律 FixtureCaseError。"""
    case_id = case["id"]
    data_cutoff = case["data_cutoff"]
    try:
        if "T" in data_cutoff:
            datetime.fromisoformat(data_cutoff)
        else:
            date.fromisoformat(data_cutoff)
    except ValueError as exc:
        raise FixtureCaseError(
            f"案例 {case_id} 的 data_cutoff 不是真实 ISO 日期或日期时间：{data_cutoff}"
        ) from exc
    try:
        created_at = datetime.fromisoformat(case["created_at"])
    except ValueError as exc:
        raise FixtureCaseError(
            f"案例 {case_id} 的 created_at 不是有效 ISO 日期时间：{case['created_at']}"
        ) from exc
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise FixtureCaseError(
            f"案例 {case_id} 的 created_at 必须包含明确时区偏移：{case['created_at']}"
        )
    return data_cutoff, created_at


def run_fixture_case(
    case_id: str,
    *,
    project_root: Path,
    reports: list[str],
    outputs: list[str],
    catalog_path: Path | None = None,
) -> FixtureRunResult:
    """运行 fixture 案例：先完整校验 catalog/用例/schema/输入，再检查渲染器，
    最后创建隔离项目并调用同一 RunService。"""
    project_root = project_root.expanduser().resolve()
    if catalog_path is None:
        catalog_path = (
            Path(__file__).resolve().parents[3] / "fixtures" / "catalog.yaml"
        )
    catalog_path = catalog_path.expanduser().resolve()

    catalog = _load_catalog(catalog_path)
    schema = _load_fixture_schema()
    case_root_base = _get_case_root_base(catalog_path)

    # 完整 catalog + case_digest + 输入完整性校验必须先通过
    cases = _validate_catalog(catalog, case_root_base=case_root_base, schema=schema)
    if case_id not in cases:
        raise FixtureCaseError(
            f"未知案例：{case_id}（可用案例：{', '.join(sorted(cases.keys()))}）"
        )
    case = cases[case_id]

    case_reports = sorted(case["reports"])
    if sorted(reports) != case_reports:
        raise FixtureCaseError(
            f"请求的报告类型 {sorted(reports)} 与案例声明 {case_reports} 不一致"
        )
    case_outputs = sorted(case["outputs"])
    if sorted(outputs) != case_outputs:
        raise FixtureCaseError(
            f"请求的输出格式 {sorted(outputs)} 与案例声明 {case_outputs} 不一致"
        )

    # 渲染器可用性：期望 rendered 的案例在创建项目前失败关闭
    if case["expected"]["outcome"] == "rendered":
        _check_renderer_availability(outputs)

    data_cutoff, created_at = _parse_case_dates(case)
    try:
        contract = create_project_contract(
            indication=case["indication"],
            reports=[ReportKind(r).value for r in case["reports"]],
            outputs=[OutputFormat(o).value for o in case["outputs"]],
            timezone=case["timezone"],
            cutoff=data_cutoff,
            created_at=created_at,
        )
        create_project_workspace(project_root, contract)
    except (ValueError, ProjectWorkspaceError) as exc:
        raise FixtureCaseError(f"项目创建失败：{exc}") from exc

    input_hashes: dict[str, str] = {}
    universe_input_path: Path | None = None
    report_data_path: Path | None = None
    for inp in case["inputs"]:
        src = case_root_base / case_id / inp["path"]
        dst = project_root / "evidence" / "library" / Path(inp["path"]).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        input_hashes[inp["path"]] = inp["sha256"]
        if inp["role"] == "universe_closure":
            universe_input_path = dst
        elif inp["role"] == "report_data":
            report_data_path = dst

    case_digest = _compute_case_digest(case)
    ctx = RunContext(
        project_root=project_root,
        contract=contract,
        universe_input_path=universe_input_path,
        report_data_path=report_data_path,
        run_inputs={
            "case_id": case_id,
            "case_digest": case_digest,
            **input_hashes,
        },
    )
    run_result = run_project(project_root, resume=False, run_context=ctx)
    expected_outcome = (
        "completed" if case["expected"]["outcome"] == "rendered"
        else case["expected"]["outcome"]
    )
    if run_result.outcome != expected_outcome:
        raise FixtureCaseError(
            f"案例 {case_id} 运行结果与预期不符："
            f"期望 {expected_outcome}，实际 {run_result.outcome}"
        )
    return FixtureRunResult(
        run_result=run_result,
        case_id=case_id,
        case_digest=case_digest,
        project_root=project_root,
    )


def validate_catalog(
    catalog_path: Path,
    *,
    case_root_base: Path | None = None,
) -> dict[str, Any]:
    """校验 catalog：供 FX05 测试使用。"""
    catalog = _load_catalog(catalog_path)
    schema = _load_fixture_schema()
    if case_root_base is None:
        case_root_base = _get_case_root_base(catalog_path)
    _validate_catalog(catalog, case_root_base=case_root_base, schema=schema)
    return catalog
