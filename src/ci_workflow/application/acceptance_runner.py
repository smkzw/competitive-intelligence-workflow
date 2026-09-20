"""Task 10.3 pre-RC 全矩阵验收 runner：catalog 真值、项目运行、浏览器回执与场景预演回执严格绑定。

本模块实现验收编排的前三个阶段——catalog/输入核验、同源输入的空项目
HTML-only 运行、A/B/C 三个 HTML 当前产物与 Codex 在 ego(lite) 中生成的
浏览器回执的严格绑定——第四层 ``required-v12`` full-matrix 场景
rehearsal 回执聚合（``--suite full``），以及第五层候选安装根三宿主真实
smoke（``build_host_smoke_stage``）、最终项目核验
（``build_project_verify_stage``）与六阶段续跑编排
（``complete_pre_rc_rehearsal``）。只把本轮真正预演过的首版
case/子 case 记为 ``pre_rc_rehearsal``，恢复、切换与未来格式责任保持
``pending_future_owner``，``release_cases_closed`` 恒为 0。本模块自身不
启动任何浏览器、不读取任何特定浏览器框架的结论文件；真实浏览器验收由
Codex 使用 ego(lite) 完成，回执按约定路径与字段提供后才能通过本阶段。
科学真值——适应症、时区、数据截止、报告集合、输出格式与逐文件 SHA-256
——只来自 ``fixtures/acceptance/catalog.yaml`` 及其案例目录；命令行不得
覆盖。案例目录布局与 Task 10.1 一致：``full-matrix-v1`` 与
``historical-cutoff-*`` 共用 ``full-matrix-v1/``，其余案例位于
``required-v12/<case_id>/``。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from jsonschema import Draft202012Validator

from ci_workflow.application.acceptance_catalog import compute_case_digest
from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.real_source_acceptance import (
    _artifact_output,
    _parse_datetime,
)
from ci_workflow.application.run_service import (
    RunContext,
    RunError,
    run_project,
    validate_run_manifest,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.browser import (
    LockedSitemapSourceError,
    derive_sitemap_contract,
    load_locked_sitemap_source,
    route_to_site_path,
)
from ci_workflow.reports.common.page_registry import PageRegistry

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOG_PATH = ROOT / "fixtures" / "acceptance" / "catalog.yaml"
_CATALOG_SCHEMA_PATH = ROOT / "schemas" / "acceptance-catalog.schema.json"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_SCOPE = "site_html_v1"
_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
_EXTRA_CASE_POLICY = "reject_unless_explicitly_registered"
_DEFAULT_CASE_ID = "full-matrix-v1"
_FULL_MATRIX_FIXTURE_ROOT = "full-matrix-v1"
_REQUIRED_V12_FIXTURE_ROOT = "required-v12"
_HISTORICAL_PREFIX = "historical-cutoff-"

# ─── required-v12 full-matrix 场景 rehearsal 回执常量 ──────────────────────
_FULL_MATRIX_EXECUTION_SCOPE = "full-matrix"
_CONDITIONAL_EXTENSION_SCOPE = "conditional-extension"
_KNOWN_EXECUTION_SCOPES = frozenset(
    {"full-matrix", "recovery", "legacy-cutover", "conditional-extension"}
)
REHEARSAL_STATUS = "pre_rc_rehearsal"
PENDING_FUTURE_OWNER_STATUS = "pending_future_owner"
NOT_APPLICABLE_STATUS = "not_applicable"
_OUTSIDE_SUITE_STATUS = "outside_suite"
_ALLOWED_RECEIPT_STATUSES = frozenset(
    {
        REHEARSAL_STATUS,
        PENDING_FUTURE_OWNER_STATUS,
        NOT_APPLICABLE_STATUS,
        _OUTSIDE_SUITE_STATUS,
    }
)
# 任何回执一旦出现这些状态即视为“发布案例被关闭”；本 runner 永不产生它们。
_RELEASE_CLOSED_STATUSES = frozenset(
    {"accepted", "verified", "release_accepted", "release_closed", "closed"}
)
_CATALOG_OWNER_STATUSES = frozenset(
    {"current_owner", "pending_future_owner", "not_applicable"}
)
_SCENARIO_RELATIVE_PATH = "inputs/scenario.json"
_DEFERRED_FORMATS: tuple[str, ...] = ("pdf", "html-ppt", "pptx")
_PRE_RC_HOSTS: tuple[str, ...] = ("codex", "hermes", "omp")
_VERIFIER_TIMEOUT_SECONDS = 600
class AcceptanceRunnerError(ValueError):
    """验收 catalog、输入摘要或项目根合同违反时的失败关闭错误。"""


@dataclass(frozen=True)
class AcceptanceCaseInput:
    """一份已核验的案例输入：声明摘要与实际字节摘要一致。"""

    path: str
    purpose_zh: str
    role: str | None
    sha256: str
    verified_sha256: str


@dataclass(frozen=True)
class AcceptanceExpectedFile:
    """一份已核验的预期文件：声明摘要与实际字节摘要一致。"""

    path: str
    purpose_zh: str
    sha256: str
    verified_sha256: str


@dataclass(frozen=True)
class AcceptanceCatalog:
    """通过 schema 与首版范围检查后的验收目录。"""

    path: Path
    sha256: str
    release_scope: str
    digest_algorithm: str
    allowed_formats: tuple[str, ...]
    approved_case_families: tuple[str, ...]
    extra_case_policy: str
    cases: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True)
class ResolvedAcceptanceCase:
    """从 catalog 解析出的案例科学真值；逐文件摘要已对实际字节核验。"""

    case_id: str
    name_zh: str | None
    family: str
    execution_scope: str
    owner_task: str
    indication: str
    timezone: str
    data_cutoff_text: str
    data_cutoff: datetime
    created_at: datetime
    reports: tuple[str, ...]
    formats: tuple[str, ...]
    inputs: tuple[AcceptanceCaseInput, ...]
    expected_files: tuple[AcceptanceExpectedFile, ...]
    case_digest: str
    fixture_root: Path

    @property
    def input_digests(self) -> dict[str, str]:
        """逐文件摘要映射；已核验值与声明值一致。"""

        return {item.path: item.verified_sha256 for item in self.inputs}

    @property
    def expected_digests(self) -> dict[str, str]:
        return {item.path: item.verified_sha256 for item in self.expected_files}


# ─── 基础解析与校验 ────────────────────────────────────────────────────────


class _UniqueKeyLoader(yaml.SafeLoader):
    """拒绝重复键的 YAML 加载器：目录解析不允许歧义。"""


def _unique_key_constructor(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise AcceptanceRunnerError(f"验收 catalog 存在重复键：{key}")
        mapping[key] = loader.construct_object(value_node)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _unique_key_constructor,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceRunnerError(f"{label}不能为空")
    return value


def _parse_sha256(value: object, label: str) -> str:
    text = _required_str(value, label)
    if _SHA256_RE.fullmatch(text) is None:
        raise AcceptanceRunnerError(f"{label}必须是小写 SHA-256：{text}")
    return text


def _parse_offset_datetime(text: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AcceptanceRunnerError(f"{label}不是有效 ISO 日期时间：{text}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AcceptanceRunnerError(f"{label}必须包含明确时区偏移：{text}")
    return parsed


def _assert_relative_path(value: object, *, label: str) -> str:
    text = _required_str(value, label)
    if (
        Path(text).is_absolute()
        or PureWindowsPath(text).drive
        or "\\" in text
        or ".." in Path(text).parts
    ):
        raise AcceptanceRunnerError(f"{label}必须是目录内 POSIX 相对路径：{text}")
    return text


def _load_yaml_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AcceptanceRunnerError(f"无法读取{label}：{path}") from exc
    try:
        data = yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise AcceptanceRunnerError(f"{label}不是有效 YAML：{exc}") from exc
    if not isinstance(data, dict):
        raise AcceptanceRunnerError(f"{label}顶层必须是对象：{path}")
    return data


def _validate_catalog_schema(payload: Mapping[str, Any]) -> None:
    try:
        schema = json.loads(_CATALOG_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceRunnerError("无法读取 acceptance catalog schema") from exc
    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if errors:
        raise AcceptanceRunnerError(f"catalog 不符合 acceptance schema：{errors[0].message}")


# ─── catalog 加载与 HTML-only 真值解析 ─────────────────────────────────────


def load_acceptance_catalog(catalog_path: Path | None = None) -> AcceptanceCatalog:
    """加载并校验验收 catalog；schema 与首版 HTML-only 范围任一不符即失败关闭。"""

    path = (catalog_path or DEFAULT_CATALOG_PATH).expanduser().resolve()
    payload = _load_yaml_object(path, label="验收 catalog")
    _validate_catalog_schema(payload)

    release_scope = _required_str(payload.get("release_scope"), "catalog release_scope")
    if release_scope != _RELEASE_SCOPE:
        raise AcceptanceRunnerError(
            f"catalog release_scope 必须为 {_RELEASE_SCOPE}，实际 {release_scope}"
        )
    digest_algorithm = _required_str(payload.get("digest_algorithm"), "catalog digest_algorithm")
    if digest_algorithm != _DIGEST_ALGORITHM:
        raise AcceptanceRunnerError(
            f"catalog digest_algorithm 必须为 {_DIGEST_ALGORITHM}，实际 {digest_algorithm}"
        )

    requirements = payload.get("requirements")
    if not isinstance(requirements, dict):
        raise AcceptanceRunnerError("catalog 缺少 requirements 对象")
    raw_allowed = requirements.get("allowed_formats")
    if not isinstance(raw_allowed, list) or not all(isinstance(item, str) for item in raw_allowed):
        raise AcceptanceRunnerError("catalog requirements.allowed_formats 必须是字符串数组")
    allowed_formats = tuple(raw_allowed)
    if allowed_formats != ("html",):
        raise AcceptanceRunnerError(
            f"catalog 允许格式必须只有 html，实际 {list(allowed_formats)}"
        )
    raw_families = requirements.get("approved_case_families")
    if not isinstance(raw_families, list) or not all(
        isinstance(item, str) for item in raw_families
    ):
        raise AcceptanceRunnerError("catalog requirements.approved_case_families 无效")
    extra_case_policy = _required_str(
        requirements.get("extra_case_policy"),
        "catalog requirements.extra_case_policy",
    )
    if extra_case_policy != _EXTRA_CASE_POLICY:
        raise AcceptanceRunnerError(
            f"catalog extra_case_policy 必须为 {_EXTRA_CASE_POLICY}，实际 {extra_case_policy}"
        )

    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise AcceptanceRunnerError("catalog 必须包含非空 cases 列表")
    cases: dict[str, dict[str, Any]] = {}
    for index, raw_case in enumerate(raw_cases):
        if not isinstance(raw_case, dict):
            raise AcceptanceRunnerError(f"catalog 案例 #{index} 必须是对象")
        case_id = _required_str(raw_case.get("id"), f"catalog 案例 #{index} id")
        if case_id in cases:
            raise AcceptanceRunnerError(f"catalog 存在重复案例：{case_id}")
        cases[case_id] = raw_case

    return AcceptanceCatalog(
        path=path,
        sha256=_sha256_file(path),
        release_scope=release_scope,
        digest_algorithm=digest_algorithm,
        allowed_formats=allowed_formats,
        approved_case_families=tuple(raw_families),
        extra_case_policy=extra_case_policy,
        cases=cases,
    )


def _assert_case_html_only(
    case: Mapping[str, Any],
    *,
    allowed_formats: Sequence[str],
    case_id: str,
) -> None:
    """拒绝任何离开 HTML-only 首版范围的格式声明（schema 之上的显式防线）。"""

    if tuple(allowed_formats) != ("html",):
        raise AcceptanceRunnerError(
            f"catalog 允许格式必须只有 html，实际 {list(allowed_formats)}"
        )
    raw_formats = case.get("formats")
    formats = (
        tuple(raw_formats)
        if isinstance(raw_formats, Sequence) and not isinstance(raw_formats, str)
        else ()
    )
    if formats != ("html",):
        raise AcceptanceRunnerError(
            f"案例 {case_id} 首版格式必须严格为 [html]，实际 {raw_formats!r}"
        )


def _default_case_fixture_root(catalog_path: Path, case_id: str) -> Path:
    """与 Task 10.1 目录布局一致的案例目录推导。"""

    if case_id == _DEFAULT_CASE_ID or case_id.startswith(_HISTORICAL_PREFIX):
        return catalog_path.parent / _FULL_MATRIX_FIXTURE_ROOT
    return catalog_path.parent / _REQUIRED_V12_FIXTURE_ROOT / case_id


def _verify_case_file(
    fixture_root: Path,
    relative_path: str,
    declared_sha256: str,
    *,
    kind: str,
) -> str:
    """核验案例目录内一份声明文件的存在性与逐字节摘要。"""

    path = fixture_root / relative_path
    resolved = path.resolve()
    root = fixture_root.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise AcceptanceRunnerError(f"{kind}路径越出案例目录：{relative_path}")
    if not path.is_file():
        raise AcceptanceRunnerError(f"{kind}文件不存在：{relative_path}")
    actual = _sha256_file(path)
    if actual != declared_sha256:
        raise AcceptanceRunnerError(
            f"{kind}摘要与文件不一致：{relative_path}"
            f"（声明 {declared_sha256}，实际 {actual}）"
        )
    return actual


def resolve_acceptance_case(
    case_id: str,
    catalog: AcceptanceCatalog | None = None,
    *,
    fixture_root: Path | None = None,
) -> ResolvedAcceptanceCase:
    """从 catalog 解析案例科学真值，并核验全部声明文件的逐字节摘要。"""

    catalog = catalog or load_acceptance_catalog()
    case = catalog.cases.get(case_id)
    if case is None:
        raise AcceptanceRunnerError(
            f"案例 {case_id} 未在验收目录登记：{catalog.path}；"
            f"已登记案例：{', '.join(sorted(catalog.cases))}"
        )
    _assert_case_html_only(case, allowed_formats=catalog.allowed_formats, case_id=case_id)

    declared_digest = _parse_sha256(case.get("case_digest"), f"案例 {case_id} case_digest")
    actual_digest = compute_case_digest(case)
    if actual_digest != declared_digest:
        raise AcceptanceRunnerError(
            f"案例 {case_id} case_digest 不匹配："
            f"期望 {declared_digest}，实际 {actual_digest}"
        )

    family = _required_str(case.get("family"), f"案例 {case_id} family")
    if family not in catalog.approved_case_families:
        raise AcceptanceRunnerError(
            f"案例 {case_id} family 不在目录批准集合：{family}"
        )

    indication = _required_str(case.get("indication"), f"案例 {case_id} indication")
    timezone = _required_str(case.get("timezone"), f"案例 {case_id} timezone")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise AcceptanceRunnerError(
            f"案例 {case_id} timezone 不是可解析的 IANA 时区：{timezone}"
        ) from exc
    data_cutoff_text = _required_str(case.get("data_cutoff"), f"案例 {case_id} data_cutoff")
    data_cutoff = _parse_offset_datetime(data_cutoff_text, f"案例 {case_id} data_cutoff")
    created_at = _parse_offset_datetime(
        _required_str(case.get("created_at"), f"案例 {case_id} created_at"),
        f"案例 {case_id} created_at",
    )

    raw_reports = case.get("reports")
    if not isinstance(raw_reports, list) or not all(isinstance(item, str) for item in raw_reports):
        raise AcceptanceRunnerError(f"案例 {case_id} reports 必须是字符串数组")
    if not raw_reports:
        raise AcceptanceRunnerError(f"案例 {case_id} reports 不能为空")

    root = (
        fixture_root or _default_case_fixture_root(catalog.path, case_id)
    ).expanduser().resolve()
    if not root.is_dir():
        raise AcceptanceRunnerError(f"案例 {case_id} 案例目录不存在：{root}")

    raw_inputs = case.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise AcceptanceRunnerError(f"案例 {case_id} 缺少输入文件声明")
    inputs: list[AcceptanceCaseInput] = []
    for index, raw_input in enumerate(raw_inputs):
        if not isinstance(raw_input, dict):
            raise AcceptanceRunnerError(f"案例 {case_id} 输入 #{index} 必须是对象")
        relative = _assert_relative_path(
            raw_input.get("path"),
            label=f"案例 {case_id} 输入 #{index} 路径",
        )
        declared = _parse_sha256(
            raw_input.get("sha256"),
            f"案例 {case_id} 输入 {relative} sha256",
        )
        purpose_zh = _required_str(
            raw_input.get("purpose_zh"),
            f"案例 {case_id} 输入 {relative} purpose_zh",
        )
        role = raw_input.get("role")
        inputs.append(
            AcceptanceCaseInput(
                path=relative,
                purpose_zh=purpose_zh,
                role=role if isinstance(role, str) else None,
                sha256=declared,
                verified_sha256=_verify_case_file(root, relative, declared, kind="输入"),
            )
        )

    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise AcceptanceRunnerError(f"案例 {case_id} 缺少 expected 对象")
    raw_expected_files = expected.get("expected_files", [])
    if not isinstance(raw_expected_files, list):
        raise AcceptanceRunnerError(f"案例 {case_id} expected_files 必须是数组")
    expected_files: list[AcceptanceExpectedFile] = []
    for index, raw_file in enumerate(raw_expected_files):
        if not isinstance(raw_file, dict):
            raise AcceptanceRunnerError(f"案例 {case_id} 预期文件 #{index} 必须是对象")
        relative = _assert_relative_path(
            raw_file.get("path"),
            label=f"案例 {case_id} 预期文件 #{index} 路径",
        )
        declared = _parse_sha256(
            raw_file.get("sha256"),
            f"案例 {case_id} 预期文件 {relative} sha256",
        )
        purpose_zh = _required_str(
            raw_file.get("purpose_zh"),
            f"案例 {case_id} 预期文件 {relative} purpose_zh",
        )
        expected_files.append(
            AcceptanceExpectedFile(
                path=relative,
                purpose_zh=purpose_zh,
                sha256=declared,
                verified_sha256=_verify_case_file(root, relative, declared, kind="预期文件"),
            )
        )

    name_zh = case.get("name_zh")
    owner_task = _required_str(case.get("owner_task"), f"案例 {case_id} owner_task")
    execution_scope = _required_str(case.get("execution_scope"), f"案例 {case_id} execution_scope")
    return ResolvedAcceptanceCase(
        case_id=case_id,
        name_zh=name_zh if isinstance(name_zh, str) else None,
        family=family,
        execution_scope=execution_scope,
        owner_task=owner_task,
        indication=indication,
        timezone=timezone,
        data_cutoff_text=data_cutoff_text,
        data_cutoff=data_cutoff,
        created_at=created_at,
        reports=tuple(raw_reports),
        formats=("html",),
        inputs=tuple(inputs),
        expected_files=tuple(expected_files),
        case_digest=declared_digest,
        fixture_root=root,
    )


# ─── 空项目失败关闭合同 ────────────────────────────────────────────────────

_KNOWN_ROOT_ARTIFACTS: Mapping[str, str] = {
    "project.yaml": "预存项目工作区文件",
    "state": "预存项目状态数据库",
    "manifests": "预存运行清单",
    "reports": "预存报告站点或产物",
    "snapshots": "预存报告快照",
    "receipts": "预存来源回执",
    "verification": "预存浏览器验收结论",
    "host-smoke": "预存宿主回执",
    "blockers": "预存阻断记录",
    "evidence": "预存证据库",
    "coverage": "预存覆盖状态",
    "logs": "预存运行日志",
    "corrections": "预存补件收件箱",
    "monitoring": "预存监控收件箱",
}


def _require_absent_or_empty_root(root: Path, *, label: str) -> Path:
    """共享的“不存在或为空”失败关闭检查；``label`` 说明该根的验收语义。"""

    raw_root = root.expanduser()
    if raw_root.is_symlink():
        raise AcceptanceRunnerError(
            f"{label}必须不存在或为空；路径不得是软链接：{raw_root}"
        )
    resolved = raw_root.resolve()
    if not resolved.exists():
        return resolved
    if not resolved.is_dir():
        raise AcceptanceRunnerError(
            f"{label}必须不存在或为空；路径已存在且不是目录：{resolved}"
        )
    labels = [
        f"{entry.name}={_KNOWN_ROOT_ARTIFACTS.get(entry.name, '未识别内容')}"
        for entry in sorted(resolved.iterdir(), key=lambda item: item.name)
    ]
    if labels:
        raise AcceptanceRunnerError(
            f"{label}必须不存在或为空；发现预存内容："
            + "、".join(labels)
            + f"：{resolved}"
        )
    return resolved


def require_empty_project_root(project_root: Path) -> Path:
    """新项目根必须不存在或为空；任何预存内容一律失败关闭并给出诊断。"""

    return _require_absent_or_empty_root(Path(project_root), label="验收项目根")


# ─── 编排第一阶段：catalog/输入核验 ────────────────────────────────────────


def _catalog_stage_payload(
    catalog: AcceptanceCatalog,
    resolved: ResolvedAcceptanceCase,
    checked_root: Path,
) -> dict[str, Any]:
    """阶段 1 绑定摘要：catalog/案例/输入/项目根状态。"""

    return {
        "stage": "catalog-and-input-verification",
        "ok": True,
        "catalog_path": str(catalog.path),
        "catalog_sha256": catalog.sha256,
        "release_scope": catalog.release_scope,
        "case_id": resolved.case_id,
        "case_digest": resolved.case_digest,
        "indication": resolved.indication,
        "timezone": resolved.timezone,
        "data_cutoff": resolved.data_cutoff_text,
        "reports": list(resolved.reports),
        "formats": list(resolved.formats),
        "inputs": resolved.input_digests,
        "expected_files": resolved.expected_digests,
        "project_root": str(checked_root),
        "project_root_state": "empty" if checked_root.exists() else "absent",
    }


def run_catalog_input_stage(
    *,
    catalog_path: Path | None = None,
    case_id: str = _DEFAULT_CASE_ID,
    project_root: Path,
) -> dict[str, Any]:
    """执行 catalog 真值解析、输入摘要核验与空项目检查，返回绑定摘要。"""

    catalog = load_acceptance_catalog(catalog_path)
    resolved = resolve_acceptance_case(case_id, catalog)
    checked_root = require_empty_project_root(project_root)
    return _catalog_stage_payload(catalog, resolved, checked_root)


# ─── 编排第二阶段：同源输入的空项目 HTML-only 运行 ─────────────────────────

_REPORT_DATA_BASENAME_TO_KIND: Mapping[str, str] = {
    "report-a-data.json": "A",
    "report-b-data.json": "B",
    "report-c-data.json": "C",
}
_RUN_BINDING_CONTRACT_RELATIVE_PATH = "inputs/run-binding-contract.json"
_PRE_RC_RUN_METADATA_KEY = "pre_rc_run_id"


@dataclass(frozen=True)
class RunBindingContract:
    """案例目录内 run-binding-contract.json 的当次运行绑定规则。

    每个字段都已在加载时与验收 catalog 锁定的科学真值逐项对齐；
    ``input_hashes`` 中的路径与摘要必须同时出现在 catalog 声明里。
    """

    report_version: str
    report_snapshot_id: str
    input_hashes: Mapping[str, str]


def _load_run_binding_contract(resolved: ResolvedAcceptanceCase) -> RunBindingContract:
    """解析并核验运行绑定合同；与 catalog 真值任一不一致即失败关闭。"""

    relative = _RUN_BINDING_CONTRACT_RELATIVE_PATH
    declared_digest = resolved.input_digests.get(relative)
    if declared_digest is None:
        raise AcceptanceRunnerError(
            f"案例 {resolved.case_id} 缺少运行绑定合同输入：{relative}"
        )
    # 距阶段 1 可能已执行其他步骤：重新核验合同文件字节后再解析。
    _verify_case_file(resolved.fixture_root, relative, declared_digest, kind="输入")
    path = resolved.fixture_root / relative
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcceptanceRunnerError(f"运行绑定合同无法读取：{relative}") from exc
    if not isinstance(payload, dict):
        raise AcceptanceRunnerError("运行绑定合同顶层必须是对象")

    case_id = _required_str(payload.get("case_id"), "运行绑定合同 case_id")
    if case_id != resolved.case_id:
        raise AcceptanceRunnerError(
            f"运行绑定合同 case_id 与验收案例不一致：{case_id} ≠ {resolved.case_id}"
        )
    indication = _required_str(payload.get("indication"), "运行绑定合同 indication")
    if " ".join(indication.split()) != " ".join(resolved.indication.split()):
        raise AcceptanceRunnerError("运行绑定合同适应症与验收案例不一致")
    timezone = _required_str(payload.get("timezone"), "运行绑定合同 timezone")
    if timezone != resolved.timezone:
        raise AcceptanceRunnerError("运行绑定合同时区与验收案例不一致")
    contract_cutoff = _parse_offset_datetime(
        _required_str(payload.get("data_cutoff"), "运行绑定合同 data_cutoff"),
        "运行绑定合同 data_cutoff",
    )
    if contract_cutoff != resolved.data_cutoff:
        raise AcceptanceRunnerError("运行绑定合同数据截止与验收案例不一致")
    raw_reports = payload.get("reports")
    if not isinstance(raw_reports, list) or list(raw_reports) != list(resolved.reports):
        raise AcceptanceRunnerError("运行绑定合同报告集合与验收案例不一致")
    raw_formats = payload.get("formats")
    if raw_formats != ["html"]:
        raise AcceptanceRunnerError(
            f"运行绑定合同首版格式必须严格为 [html]，实际 {raw_formats!r}"
        )
    report_version = _required_str(payload.get("report_version"), "运行绑定合同 report_version")
    report_snapshot_id = _required_str(
        payload.get("report_snapshot_id"), "运行绑定合同 report_snapshot_id"
    )

    raw_hashes = payload.get("input_hashes")
    if not isinstance(raw_hashes, dict) or not raw_hashes:
        raise AcceptanceRunnerError("运行绑定合同缺少 input_hashes 对象")
    input_hashes: dict[str, str] = {}
    for raw_path, raw_digest in raw_hashes.items():
        path_text = _assert_relative_path(raw_path, label="运行绑定合同输入路径")
        digest = _parse_sha256(raw_digest, f"运行绑定合同输入摘要 {path_text}")
        catalog_digest = resolved.input_digests.get(path_text)
        if catalog_digest is None:
            raise AcceptanceRunnerError(f"运行绑定合同引用了未声明输入：{path_text}")
        if catalog_digest != digest:
            raise AcceptanceRunnerError(
                f"运行绑定合同输入摘要与 catalog 真值不一致：{path_text}"
            )
        input_hashes[path_text] = digest

    return RunBindingContract(
        report_version=report_version,
        report_snapshot_id=report_snapshot_id,
        input_hashes=input_hashes,
    )


def run_project_stage(
    *,
    catalog: AcceptanceCatalog,
    resolved: ResolvedAcceptanceCase,
    project_root: Path,
    pre_rc_run_id: str,
) -> dict[str, Any]:
    """在空项目根以 HTML-only 同源输入运行项目，并把运行清单绑定到 catalog 真值。

    顺序：复核项目根为空 → 解析运行绑定合同 → 以案例真值创建项目合同 →
    逐文件入库输入（入库后重验摘要）→ 调用既有 RunService 真实运行 →
    重开校验运行清单 → 逐项核对 case/case_digest/pre-RC 运行身份/输入摘要/
    新鲜度。任一步失败即失败关闭，不产出任何通过信号。
    """

    checked_root = require_empty_project_root(project_root)
    binding = _load_run_binding_contract(resolved)
    try:
        contract = create_project_contract(
            indication=resolved.indication,
            reports=list(resolved.reports),
            outputs=["html"],
            timezone=resolved.timezone,
            cutoff=resolved.data_cutoff,
            created_at=resolved.created_at,
        )
        create_project_workspace(checked_root, contract)
    except (ValueError, ProjectWorkspaceError) as exc:
        raise AcceptanceRunnerError(f"验收项目创建失败关闭：{exc}") from exc

    run_inputs: dict[str, str] = {
        "case_id": resolved.case_id,
        "case_digest": resolved.case_digest,
    }
    report_data_paths: dict[str, Path] = {}
    for item in resolved.inputs:
        source = resolved.fixture_root / item.path
        target = checked_root / "evidence" / "library" / Path(item.path).name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        except OSError as exc:
            raise AcceptanceRunnerError(f"无法写入验收输入文件：{item.path}") from exc
        if _sha256_file(target) != item.verified_sha256:
            raise AcceptanceRunnerError(f"验收输入入库后摘要漂移：{item.path}")
        run_inputs[item.path] = item.verified_sha256
        kind = _REPORT_DATA_BASENAME_TO_KIND.get(Path(item.path).name)
        if item.role == "report_data" and kind is not None:
            report_data_paths[kind] = target
    if sorted(report_data_paths) != sorted(resolved.reports):
        raise AcceptanceRunnerError(
            f"案例 {resolved.case_id} 的报告数据包 {sorted(report_data_paths)} "
            f"与声明报告 {sorted(resolved.reports)} 不一致"
        )

    context = RunContext(
        project_root=checked_root,
        contract=contract,
        report_data_paths=report_data_paths,
        run_inputs=run_inputs,
        runtime_metadata={_PRE_RC_RUN_METADATA_KEY: pre_rc_run_id},
    )
    try:
        run_result = run_project(checked_root, resume=False, run_context=context)
    except RunError as exc:
        raise AcceptanceRunnerError(f"验收项目运行失败关闭：{exc}") from exc
    if run_result.outcome != "completed":
        raise AcceptanceRunnerError(
            f"验收项目运行未以完成终态结束：{run_result.outcome}"
        )
    try:
        manifest = validate_run_manifest(checked_root)
    except RunError as exc:
        raise AcceptanceRunnerError(f"当前运行清单无法校验：{exc}") from exc

    # 当前运行与 catalog 真值逐项绑定；任一漂移失败关闭。
    if manifest.get("run_id") != run_result.run_id:
        raise AcceptanceRunnerError("当前运行清单运行标识与运行结果不一致")
    if manifest.get("resume") is not False:
        raise AcceptanceRunnerError("验收运行禁止 resume 或缺少新运行标记")
    if manifest.get("case_id") != resolved.case_id:
        raise AcceptanceRunnerError("当前运行清单案例标识与验收目录不一致")
    if manifest.get("case_digest") != resolved.case_digest:
        raise AcceptanceRunnerError("当前运行清单案例摘要与验收目录锁定值不一致")
    if manifest.get(_PRE_RC_RUN_METADATA_KEY) != pre_rc_run_id:
        raise AcceptanceRunnerError("当前运行清单未绑定本次 pre-RC 运行身份")
    if manifest.get("reused") != [] or manifest.get("reused_artifacts") != []:
        raise AcceptanceRunnerError("验收运行包含复用节点或复用产物，拒绝旧运行复用")
    manifest_inputs = manifest.get("input_hashes")
    if not isinstance(manifest_inputs, dict) or not manifest_inputs:
        raise AcceptanceRunnerError("当前运行清单缺少输入摘要")
    declared_paths = set(resolved.input_digests)
    for raw_path, raw_digest in manifest_inputs.items():
        if not isinstance(raw_path, str) or raw_path not in declared_paths:
            raise AcceptanceRunnerError(
                f"当前运行清单引用了未声明输入：{raw_path}"
            )
        if raw_digest != resolved.input_digests[raw_path]:
            raise AcceptanceRunnerError(f"当前运行清单输入摘要与 catalog 不一致：{raw_path}")
    for path_text, digest in binding.input_hashes.items():
        if manifest_inputs.get(path_text) != digest:
            raise AcceptanceRunnerError(
                f"当前运行清单输入摘要与运行绑定合同不一致：{path_text}"
            )
    started_at = _parse_datetime(manifest.get("started_at"), "当前运行开始时间")
    finished_at = _parse_datetime(manifest.get("finished_at"), "当前运行结束时间")
    if finished_at < started_at:
        raise AcceptanceRunnerError("当前运行结束时间早于开始时间")
    manifest_path = checked_root / "manifests" / "current_run.json"
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise AcceptanceRunnerError("当前运行清单缺少产物记录")

    return {
        "stage": "project-run",
        "ok": True,
        "pre_rc_run_id": pre_rc_run_id,
        "run_id": run_result.run_id,
        "project_id": run_result.project_id,
        "outcome": run_result.outcome,
        "case_id": resolved.case_id,
        "case_digest": resolved.case_digest,
        "indication": resolved.indication,
        "formats": ["html"],
        "input_hashes": dict(manifest_inputs),
        "manifest_relative_path": "manifests/current_run.json",
        "manifest_sha256": _sha256_file(manifest_path),
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "output_count": len(outputs),
    }


# ─── 编排第三阶段：A/B/C 当前产物与 ego(lite) 浏览器回执严格绑定 ────────────

EGO_LITE_TOOL_IDENTITY = "ego-lite"
EGO_RECEIPT_FILENAME = "ego-receipt.json"
EGO_RECEIPT_SCHEMA_VERSION = "1.0"
# 首版站点验收的四档桌面视口；回执必须逐项声明覆盖。
PRESCRIBED_VIEWPORTS: tuple[tuple[int, int], ...] = (
    (1024, 768),
    (1280, 800),
    (1440, 900),
    (1920, 1080),
)
_ReportValue = Literal["A", "B", "C"]


class EgoReceiptPendingError(AcceptanceRunnerError):
    """ego(lite) 浏览器回执尚未提供；等待 Codex 生成，不属于验收失败判定。"""

    def __init__(self, missing_paths: Sequence[Path], guidance: str) -> None:
        self.missing_paths = tuple(missing_paths)
        super().__init__(guidance)


@dataclass(frozen=True)
class CurrentHtmlArtifact:
    """当前运行的一个 A/B/C 站点式 HTML 产物记录。"""

    report: str
    version: str
    site_relative_path: str
    site_sha256: str
    site_byte_size: int
    manifest_relative_path: str
    manifest_sha256: str
    manifest_id: str
    report_snapshot_id: str
    generated_at: str
    entry_route: str
    entry_relative_path: str
    entry_sha256: str
    routes: tuple[str, ...]

    def to_summary(self) -> dict[str, Any]:
        return {
            "report": self.report,
            "version": self.version,
            "site_relative_path": self.site_relative_path,
            "site_sha256": self.site_sha256,
            "site_byte_size": self.site_byte_size,
            "manifest_relative_path": self.manifest_relative_path,
            "manifest_sha256": self.manifest_sha256,
            "manifest_id": self.manifest_id,
            "report_snapshot_id": self.report_snapshot_id,
            "generated_at": self.generated_at,
            "entry_route": self.entry_route,
            "entry_relative_path": self.entry_relative_path,
            "entry_sha256": self.entry_sha256,
            "route_count": len(self.routes),
        }


def _discover_current_html_artifacts(
    project_root: Path,
    *,
    resolved: ResolvedAcceptanceCase,
    pre_rc_run_id: str,
) -> tuple[dict[str, CurrentHtmlArtifact], dict[str, Any], dict[str, Any]]:
    """从当前运行清单发现 A/B/C 三个 HTML 产物并逐项核验绑定。

    复用运行清单完整性校验（逐文件摘要与精确 mtime），要求每类报告恰有一份
    HTML 产物清单；任何 PDF/PPTX/HTML-PPT 产物出现在当前运行即失败关闭。
    """

    try:
        manifest = validate_run_manifest(project_root)
    except RunError as exc:
        raise AcceptanceRunnerError(f"当前运行清单无法校验：{exc}") from exc
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise AcceptanceRunnerError("当前运行标识不能为空")
    if manifest.get(_PRE_RC_RUN_METADATA_KEY) != pre_rc_run_id:
        raise AcceptanceRunnerError("当前运行清单未绑定本次 pre-RC 运行身份")
    started_at = _parse_datetime(manifest.get("started_at"), "当前运行开始时间")
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise AcceptanceRunnerError("当前运行清单缺少产物记录")
    for raw in outputs:
        if not isinstance(raw, dict):
            raise AcceptanceRunnerError("当前运行产物记录必须是对象")
        lower = str(raw.get("relative_path", "")).casefold()
        if lower.endswith((".pdf", ".pptx")) or "/html-ppt/" in lower:
            raise AcceptanceRunnerError(
                f"首版 artifact 集合出现范围外格式产物：{raw.get('relative_path')}"
            )

    binding = _load_run_binding_contract(resolved)
    artifacts: dict[str, CurrentHtmlArtifact] = {}
    sources: dict[str, Any] = {}
    for report in resolved.reports:
        report_value = cast(_ReportValue, report)
        try:
            _output_record, manifest_rel = _artifact_output(
                manifest,
                report=report_value,
            )
        except ValueError as exc:
            raise AcceptanceRunnerError(str(exc)) from exc
        version = manifest_rel.split("/")[2]
        if version != binding.report_version:
            raise AcceptanceRunnerError(
                f"{report} 类产物版本与运行绑定合同不一致：{version} ≠ {binding.report_version}"
            )
        try:
            source = load_locked_sitemap_source(project_root, ReportKind(report), version)
        except (LockedSitemapSourceError, OSError, ValueError) as exc:
            raise AcceptanceRunnerError(
                f"{report} 类当前 HTML 产物清单无法核验：{exc}"
            ) from exc
        if source.manifest.report_version != version:
            raise AcceptanceRunnerError(f"{report} 类产物清单版本与目录不一致")
        try:
            sitemap = derive_sitemap_contract(
                PageRegistry.load(),
                ReportKind(report),
                product_ids=source.product_ids,
                trial_ids=source.trial_ids,
            )
        except Exception as exc:  # noqa: BLE001 - 站点地图边界错误统一失败关闭
            raise AcceptanceRunnerError(f"{report} 类站点地图合同推导失败：{exc}") from exc

        artifact_manifest = source.manifest
        manifest_path = project_root / manifest_rel
        site_root = project_root / "reports" / report / version / "html"
        entry_route = tuple(sitemap.routes)[0]
        entry_path = site_root / route_to_site_path(entry_route)
        if not entry_path.is_file():
            raise AcceptanceRunnerError(
                f"{report} 类站点缺少入口首页物理文件：{entry_route}"
            )
        artifacts[report] = CurrentHtmlArtifact(
            report=report,
            version=version,
            site_relative_path=str(artifact_manifest.artifact.relative_path),
            site_sha256=artifact_manifest.artifact.sha256,
            site_byte_size=artifact_manifest.artifact.byte_size,
            manifest_relative_path=manifest_rel,
            manifest_sha256=_sha256_file(manifest_path),
            manifest_id=artifact_manifest.manifest_id,
            report_snapshot_id=artifact_manifest.report_snapshot_id,
            generated_at=artifact_manifest.generated_at.isoformat(),
            entry_route=entry_route,
            entry_relative_path=entry_path.relative_to(project_root).as_posix(),
            entry_sha256=_sha256_file(entry_path),
            routes=tuple(sitemap.routes),
        )
        sources[report] = source
    run_info = {
        "run_id": run_id,
        "started_at": started_at,
        "pre_rc_run_id": pre_rc_run_id,
    }
    return artifacts, sources, run_info


def expected_ego_receipt_path(project_root: Path, report: str, version: str) -> Path:
    """ego(lite) 回执的约定路径：``verification/<报告>/<版本>/ego-receipt.json``。"""

    return (
        project_root.resolve() / "verification" / report / version / EGO_RECEIPT_FILENAME
    )


def _ego_receipt_guidance(
    missing: Sequence[Path],
    *,
    run_id: str,
    pre_rc_run_id: str,
) -> str:
    listing = "\n".join(f"  - {path}" for path in missing)
    return (
        "等待 ego(lite) 浏览器回执：请由 Codex 使用 ego(lite) 对当前运行的 "
        f"A/B/C 站点完成真实浏览器验收，并将回执写入以下路径（每类报告一份）：\n"
        f"{listing}\n"
        f"回执必须声明 tool=\"{EGO_LITE_TOOL_IDENTITY}\" 并绑定当前 run id "
        f"（{run_id}）、pre-RC 运行身份（{pre_rc_run_id}）、当前产物清单标识、"
        "报告快照标识、站点摘要、实际路由集合、规定视口 "
        "[1024x768, 1280x800, 1440x900, 1920x1080] 与验收时间；任一页面失败、缺页、"
        "摘要不符或回执早于本次运行都会失败关闭。本入口不回退、也不接受"
        "任何其他浏览器。"
    )


def _load_and_bind_ego_receipt(
    path: Path,
    *,
    report: str,
    artifact: CurrentHtmlArtifact,
    project_root: Path,
    run_id: str,
    started_at: datetime,
    pre_rc_run_id: str,
) -> dict[str, Any]:
    """严格绑定一份 ego(lite) 浏览器回执到当前运行与当前产物。

    绑定项：当前 run id、pre-RC 运行身份、当前 HTML 产物清单标识、报告快照
    标识、站点摘要、实际路由集合、规定视口与验收时间。旧回执、缺页、摘要
    不符、非 ego(lite) 工具或任一页面失败均失败关闭。
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执无法读取：{path}") from exc
    if not isinstance(payload, dict):
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执顶层必须是对象：{path}")
    if payload.get("schema_version") != EGO_RECEIPT_SCHEMA_VERSION:
        raise AcceptanceRunnerError(
            f"{report} 类 ego(lite) 回执 schema_version 必须为 "
            f"{EGO_RECEIPT_SCHEMA_VERSION}，实际 {payload.get('schema_version')!r}"
        )
    if payload.get("tool") != EGO_LITE_TOOL_IDENTITY:
        raise AcceptanceRunnerError(
            f"{report} 类浏览器回执不是 ego(lite) 产物：tool={payload.get('tool')!r}；"
            f"本验收只接受 ego(lite)（{EGO_LITE_TOOL_IDENTITY}）回执，"
            "不回退任何其他浏览器"
        )
    if payload.get("ok") is not True:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执总结果未通过")
    if payload.get("report") != report:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执的报告标识不一致")
    if payload.get("version") != artifact.version:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执的报告版本不一致")
    if payload.get("run_id") != run_id:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执未绑定当前运行标识")
    if payload.get("pre_rc_run_id") != pre_rc_run_id:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执未绑定本次 pre-RC 运行身份")
    if payload.get("manifest_id") != artifact.manifest_id:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执未绑定当前产物清单标识")
    if payload.get("report_snapshot_id") != artifact.report_snapshot_id:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执未绑定当前报告快照标识")
    site_digest = payload.get("site_digest")
    if not isinstance(site_digest, str) or _SHA256_RE.fullmatch(site_digest) is None:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执站点摘要无效")
    if site_digest != artifact.site_sha256:
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执站点摘要与当前产物不一致")

    routes = payload.get("routes")
    if not isinstance(routes, list) or not all(isinstance(item, str) for item in routes):
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执路由集合无效")
    if len(routes) != len(set(routes)) or set(routes) != set(artifact.routes):
        raise AcceptanceRunnerError(
            f"{report} 类 ego(lite) 回执路由集合与当前站点地图不一致："
            f"缺少 {sorted(set(artifact.routes) - set(routes))}，"
            f"多余 {sorted(set(routes) - set(artifact.routes))}"
        )
    viewports = payload.get("viewports")
    prescribed = [list(viewport) for viewport in PRESCRIBED_VIEWPORTS]
    if viewports != prescribed:
        raise AcceptanceRunnerError(
            f"{report} 类 ego(lite) 回执必须逐项声明规定视口 {prescribed}，"
            f"实际 {viewports!r}"
        )
    pages = payload.get("pages")
    if not isinstance(pages, list) or len(pages) != len(artifact.routes):
        raise AcceptanceRunnerError(
            f"{report} 类 ego(lite) 回执页面结论数量与路由数量不一致"
        )
    seen_pages: set[str] = set()
    for raw_page in pages:
        if not isinstance(raw_page, dict):
            raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执页面结论必须是对象")
        page_route = raw_page.get("route")
        if not isinstance(page_route, str) or page_route not in artifact.routes:
            raise AcceptanceRunnerError(
                f"{report} 类 ego(lite) 回执页面路由不在当前站点地图：{page_route!r}"
            )
        if page_route in seen_pages:
            raise AcceptanceRunnerError(
                f"{report} 类 ego(lite) 回执页面路由重复：{page_route}"
            )
        seen_pages.add(page_route)
        if raw_page.get("ok") is not True:
            raise AcceptanceRunnerError(
                f"{report} 类 ego(lite) 回执页面未通过：{page_route}"
            )
    if seen_pages != set(artifact.routes):
        raise AcceptanceRunnerError(f"{report} 类 ego(lite) 回执缺少页面结论")

    verified_at = _parse_datetime(payload.get("verified_at"), f"{report} 类回执验收时间")
    started_ns = int(started_at.timestamp() * 1_000_000_000)
    if int(verified_at.timestamp() * 1_000_000_000) + 1_000_000_000 < started_ns:
        raise AcceptanceRunnerError(
            f"{report} 类 ego(lite) 回执验收时间早于当前运行，疑似复用旧回执"
        )
    if path.stat().st_mtime_ns + 1_000_000_000 < started_ns:
        raise AcceptanceRunnerError(
            f"{report} 类 ego(lite) 回执文件早于当前运行，疑似复用旧回执"
        )

    return {
        "report": report,
        "ok": True,
        "tool": EGO_LITE_TOOL_IDENTITY,
        "version": artifact.version,
        "run_id": run_id,
        "pre_rc_run_id": pre_rc_run_id,
        "manifest_id": artifact.manifest_id,
        "report_snapshot_id": artifact.report_snapshot_id,
        "site_digest": artifact.site_sha256,
        "route_count": len(artifact.routes),
        "viewports": prescribed,
        "verified_at": verified_at.isoformat(),
        "receipt_relative_path": path.relative_to(project_root).as_posix(),
        "receipt_sha256": _sha256_file(path),
        "bound_to_current_artifact": True,
    }


def run_ego_receipt_stage(
    *,
    project_root: Path,
    resolved: ResolvedAcceptanceCase,
    pre_rc_run_id: str | None = None,
) -> dict[str, Any]:
    """接收并严格绑定 Codex 在 ego(lite) 中生成的 A/B/C 浏览器回执。

    本阶段不启动任何浏览器。回执必须由 Codex 使用 ego(lite) 对当前产物
    完成真实浏览器验收后写入约定路径；任一缺失时失败关闭并给出明确指引，
    存在但与当前运行/产物任一绑定不符时同样失败关闭。``pre_rc_run_id``
    缺省时从当前运行清单读取（用于项目已运行后的回执绑定入口）。
    """

    root = project_root.resolve()
    try:
        manifest = validate_run_manifest(root)
    except RunError as exc:
        raise AcceptanceRunnerError(f"当前运行清单无法校验：{exc}") from exc
    manifest_pre_rc = manifest.get(_PRE_RC_RUN_METADATA_KEY)
    if pre_rc_run_id is not None and manifest_pre_rc != pre_rc_run_id:
        raise AcceptanceRunnerError("当前运行清单的 pre-RC 运行身份与请求不一致")
    if pre_rc_run_id is None:
        if not isinstance(manifest_pre_rc, str) or not manifest_pre_rc.strip():
            raise AcceptanceRunnerError("当前运行清单缺少 pre-RC 运行身份，无法绑定回执")
        pre_rc_run_id = manifest_pre_rc

    artifacts, _sources, run_info = _discover_current_html_artifacts(
        root,
        resolved=resolved,
        pre_rc_run_id=pre_rc_run_id,
    )
    run_id = str(run_info["run_id"])
    started_at = cast(datetime, run_info["started_at"])
    receipt_paths = {
        report: expected_ego_receipt_path(root, report, artifacts[report].version)
        for report in resolved.reports
    }
    missing = [path for path in receipt_paths.values() if not path.is_file()]
    if missing:
        raise EgoReceiptPendingError(
            missing,
            _ego_receipt_guidance(missing, run_id=run_id, pre_rc_run_id=pre_rc_run_id),
        )
    receipts = {
        report: _load_and_bind_ego_receipt(
            receipt_paths[report],
            report=report,
            artifact=artifacts[report],
            project_root=root,
            run_id=run_id,
            started_at=started_at,
            pre_rc_run_id=pre_rc_run_id,
        )
        for report in resolved.reports
    }
    return {
        "stage": "html-artifacts-browser-verdicts",
        "ok": True,
        "pre_rc_run_id": pre_rc_run_id,
        "run_id": run_id,
        "reports": list(resolved.reports),
        "formats": ["html"],
        "artifacts": {report: artifacts[report].to_summary() for report in resolved.reports},
        "receipts": receipts,
        "receipt_paths": {
            report: str(receipt_paths[report]) for report in resolved.reports
        },
    }


# ─── pre-RC 全矩阵编排：固定阶段顺序与失败关闭 ─────────────────────────────

PRE_RC_STAGE_ORDER: tuple[str, ...] = (
    "catalog-and-input-verification",
    "project-run",
    "html-artifacts-browser-verdicts",
    "host-smoke",
    "project-verify",
    "pre-rc-receipts",
)
PreRCStageHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _new_pre_rc_run_id(catalog: AcceptanceCatalog, resolved: ResolvedAcceptanceCase) -> str:
    """为本次 pre-RC 预演生成独立运行身份，绑定 catalog 与案例摘要。"""

    return stable_id(
        "pre-rc-run",
        catalog.sha256,
        resolved.case_digest,
        datetime.now(UTC).isoformat(),
        os.urandom(8).hex(),
    )


def _run_catalog_project_html_stages(
    *,
    catalog: AcceptanceCatalog,
    resolved: ResolvedAcceptanceCase,
    project_root: Path,
    pre_rc_run_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """顺序执行前三阶段，返回 (阶段摘要列表, 后续阶段上下文)。

    第三阶段等待 ego(lite) 回执时抛出 ``EgoReceiptPendingError``，由调用方
    指引 Codex 生成回执；回执不完整时绝不进入后续阶段。
    """

    stage_results: list[dict[str, Any]] = [
        _catalog_stage_payload(catalog, resolved, project_root),
    ]
    context: dict[str, Any] = {
        "pre_rc_run_id": pre_rc_run_id,
        "project_root": str(project_root),
        "catalog_sha256": catalog.sha256,
        "case_id": resolved.case_id,
        "case_digest": resolved.case_digest,
        "release_scope": catalog.release_scope,
    }
    project_summary = run_project_stage(
        catalog=catalog,
        resolved=resolved,
        project_root=project_root,
        pre_rc_run_id=pre_rc_run_id,
    )
    stage_results.append(project_summary)
    context["project_run"] = project_summary
    receipt_summary = run_ego_receipt_stage(
        project_root=project_root,
        resolved=resolved,
        pre_rc_run_id=pre_rc_run_id,
    )
    stage_results.append(receipt_summary)
    context["html_pipeline"] = receipt_summary
    return stage_results, context


def _pipeline_summary(
    *,
    pre_rc_run_id: str,
    catalog: AcceptanceCatalog,
    resolved: ResolvedAcceptanceCase,
    project_root: Path,
    stage_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "pre_rc_run_id": pre_rc_run_id,
        "release_scope": catalog.release_scope,
        "case_id": resolved.case_id,
        "case_digest": resolved.case_digest,
        "indication": resolved.indication,
        "reports": list(resolved.reports),
        "formats": list(resolved.formats),
        "project_root": str(project_root),
        "stage_order": list(PRE_RC_STAGE_ORDER),
        "stages": stage_results,
    }


def run_html_pipeline(
    *,
    project_root: Path,
    catalog_path: Path | None = None,
    case_id: str = _DEFAULT_CASE_ID,
    pre_rc_run_id: str | None = None,
) -> dict[str, Any]:
    """执行 HTML 首版前三阶段：catalog/输入核验 → 项目运行 → ego(lite) 回执绑定。

    项目运行完成后若 ego(lite) 回执尚未提供，抛出 ``EgoReceiptPendingError``
    并指引用 Codex 使用 ego(lite) 生成回执；入口绝不回退到任何其他浏览器。
    宿主冒烟、最终项目核验与回执聚合尚未接入前，
    ``PRE_RC_REHEARSAL_OK`` 全量成功信号不会由任何入口输出。
    """

    catalog = load_acceptance_catalog(catalog_path)
    resolved = resolve_acceptance_case(case_id, catalog)
    checked_root = require_empty_project_root(project_root)
    run_id = pre_rc_run_id or _new_pre_rc_run_id(catalog, resolved)
    stage_results, _context = _run_catalog_project_html_stages(
        catalog=catalog,
        resolved=resolved,
        project_root=checked_root,
        pre_rc_run_id=run_id,
    )
    return _pipeline_summary(
        pre_rc_run_id=run_id,
        catalog=catalog,
        resolved=resolved,
        project_root=checked_root,
        stage_results=stage_results,
    )


def _reverify_and_bind_current_run(
    *,
    catalog: AcceptanceCatalog,
    resolved: ResolvedAcceptanceCase,
    project_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    """对已运行项目重新核验阶段 1-3 并绑定 ego(lite) 回执。

    不重跑项目：重新核验 catalog/案例摘要、当前运行清单完整性、案例与
    pre-RC 绑定，再执行回执严格绑定。返回 ``(阶段摘要列表, 后续阶段上下文,
    pre-RC 运行身份)``；项目根为空或缺少有效当前运行清单时失败关闭。
    """

    root = project_root.expanduser().resolve()
    if not root.is_dir() or not any(root.iterdir()):
        raise AcceptanceRunnerError(
            f"回执绑定要求项目已完成运行；项目根不存在或为空：{root}"
        )
    try:
        manifest = validate_run_manifest(root)
    except RunError as exc:
        raise AcceptanceRunnerError(f"当前运行清单无法校验：{exc}") from exc
    if manifest.get("case_id") != resolved.case_id:
        raise AcceptanceRunnerError("当前运行清单案例标识与验收目录不一致")
    if manifest.get("case_digest") != resolved.case_digest:
        raise AcceptanceRunnerError("当前运行清单案例摘要与验收目录锁定值不一致")
    pre_rc_run_id = manifest.get(_PRE_RC_RUN_METADATA_KEY)
    if not isinstance(pre_rc_run_id, str) or not pre_rc_run_id.strip():
        raise AcceptanceRunnerError("当前运行清单缺少 pre-RC 运行身份，无法绑定回执")

    catalog_payload = _catalog_stage_payload(catalog, resolved, root)
    catalog_payload["project_root_state"] = "current_run"
    project_payload: dict[str, Any] = {
        "stage": "project-run",
        "ok": True,
        "reverified": True,
        "pre_rc_run_id": pre_rc_run_id,
        "run_id": manifest.get("run_id"),
        "case_id": resolved.case_id,
        "case_digest": resolved.case_digest,
        "indication": resolved.indication,
        "formats": ["html"],
        "manifest_relative_path": "manifests/current_run.json",
        "manifest_sha256": _sha256_file(root / "manifests" / "current_run.json"),
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
    }
    receipt_summary = run_ego_receipt_stage(
        project_root=root,
        resolved=resolved,
        pre_rc_run_id=pre_rc_run_id,
    )
    stage_results = [catalog_payload, project_payload, receipt_summary]
    context: dict[str, Any] = {
        "pre_rc_run_id": pre_rc_run_id,
        "project_root": str(root),
        "catalog_sha256": catalog.sha256,
        "case_id": resolved.case_id,
        "case_digest": resolved.case_digest,
        "release_scope": catalog.release_scope,
        "project_run": project_payload,
        "html_pipeline": receipt_summary,
    }
    return stage_results, context, pre_rc_run_id


def bind_ego_receipts_pipeline(
    *,
    project_root: Path,
    catalog_path: Path | None = None,
    case_id: str = _DEFAULT_CASE_ID,
) -> dict[str, Any]:
    """对已运行的项目重新核验 catalog 真值与当前运行，并绑定 ego(lite) 回执。

    用于 Codex 完成 ego(lite) 验收后的回执绑定入口：不重跑项目，仅重新核验
    catalog/案例摘要、当前运行清单完整性、案例与 pre-RC 绑定，再执行回执
    严格绑定。项目根为空或缺少有效当前运行清单时失败关闭。
    """

    catalog = load_acceptance_catalog(catalog_path)
    resolved = resolve_acceptance_case(case_id, catalog)
    stage_results, _context, pre_rc_run_id = _reverify_and_bind_current_run(
        catalog=catalog,
        resolved=resolved,
        project_root=project_root,
    )
    return _pipeline_summary(
        pre_rc_run_id=pre_rc_run_id,
        catalog=catalog,
        resolved=resolved,
        project_root=Path(project_root).expanduser().resolve(),
        stage_results=stage_results,
    )


def run_pre_rc_rehearsal(
    *,
    project_root: Path,
    catalog_path: Path | None = None,
    case_id: str = _DEFAULT_CASE_ID,
    host_smoke_stage: PreRCStageHandler | None = None,
    project_verify_stage: PreRCStageHandler | None = None,
    receipts_stage: PreRCStageHandler | None = None,
    pre_rc_run_id: str | None = None,
) -> dict[str, Any]:
    """pre-RC 全矩阵预演：固定阶段顺序执行，任一阶段缺失或失败即失败关闭。

    阶段顺序固定为 ``PRE_RC_STAGE_ORDER``；第三阶段等待 Codex 在 ego(lite)
    中生成的浏览器回执（缺失时抛出 ``EgoReceiptPendingError``，绝不回退到
    其他浏览器）。宿主冒烟、最终项目核验与回执聚合由后续阶段以注入处理器
    方式接入；处理器收到的上下文包含 pre-RC 运行身份与全部前置阶段摘要，
    返回值作为该阶段绑定摘要按顺序追加。任何异常向上传播，调用方不得输出
    通过信号。
    """

    handlers = _require_pre_rc_handlers(
        (
            ("host-smoke", host_smoke_stage),
            ("project-verify", project_verify_stage),
            ("pre-rc-receipts", receipts_stage),
        )
    )

    catalog = load_acceptance_catalog(catalog_path)
    resolved = resolve_acceptance_case(case_id, catalog)
    checked_root = require_empty_project_root(project_root)
    run_id = pre_rc_run_id or _new_pre_rc_run_id(catalog, resolved)
    stage_results, context = _run_catalog_project_html_stages(
        catalog=catalog,
        resolved=resolved,
        project_root=checked_root,
        pre_rc_run_id=run_id,
    )
    _append_stage_outcomes(handlers, stage_results=stage_results, context=context)
    return _pipeline_summary(
        pre_rc_run_id=run_id,
        catalog=catalog,
        resolved=resolved,
        project_root=checked_root,
        stage_results=stage_results,
    )


def _require_pre_rc_handlers(
    declared: Sequence[tuple[str, PreRCStageHandler | None]],
) -> list[tuple[str, PreRCStageHandler]]:
    """预检后三阶段处理器：缺任何一个都在执行任何阶段之前失败关闭。"""

    missing = [name for name, handler in declared if handler is None]
    if missing:
        raise AcceptanceRunnerError(
            "以下 pre-RC 阶段尚未接入编排，失败关闭，不执行任何阶段："
            + "、".join(missing)
        )
    return [(name, handler) for name, handler in declared if handler is not None]


def _append_stage_outcomes(
    handlers: Sequence[tuple[str, PreRCStageHandler]],
    *,
    stage_results: list[dict[str, Any]],
    context: dict[str, Any],
) -> None:
    """按声明顺序执行处理器，并把绑定摘要追加进阶段列表与上下文。"""

    for stage_name, handler in handlers:
        outcome = handler(context)
        if not isinstance(outcome, Mapping):
            raise AcceptanceRunnerError(
                f"阶段 {stage_name} 处理器未返回绑定摘要，失败关闭"
            )
        summary = {"stage": stage_name, "ok": True, **dict(outcome)}
        stage_results.append(summary)
        context[stage_name.replace("-", "_")] = summary


# ─── F05：候选安装根三宿主真实 smoke 与最终项目核验 ─────────────────────────

DEFAULT_CANDIDATE_INSTALL_ROOT = (
    Path.home()
    / ".cc-switch"
    / "skills"
    / "clinical-research"
    / "competitive-intelligence-workflow"
)
HostSmokeBatchRunner = Callable[..., Any]
_HOST_SMOKE_EVIDENCE_DIRECTORY = "host-smoke"
_HOST_SMOKE_PROJECTS_DIRECTORY = "host-projects"


def _load_candidate_package_identity(manifest_path: Path) -> tuple[str, str]:
    """读取候选包清单中的名称/版本，供三宿主回执绑定到同一包。"""

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcceptanceRunnerError(
            f"候选包 package-manifest.json 无法读取：{manifest_path}"
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("package"), dict):
        raise AcceptanceRunnerError("候选包 package-manifest.json 缺少 package 对象")
    package = cast(dict[str, Any], payload["package"])
    name = _required_str(package.get("name"), "候选包名称")
    version = _required_str(package.get("version"), "候选包版本")
    return name, version


def _require_exact_evidence_path(
    value: object,
    *,
    expected: Path,
    label: str,
) -> Path:
    """要求 runner 返回的落盘路径正是本次隔离证据根中的约定文件。"""

    if not isinstance(value, (str, Path)):
        raise AcceptanceRunnerError(f"{label}路径类型无效，失败关闭")
    raw_path = Path(value).expanduser()
    expected_raw = expected.expanduser()
    if raw_path.is_symlink() or expected_raw.is_symlink():
        raise AcceptanceRunnerError(f"{label}不得是软链接，失败关闭")
    actual = raw_path.resolve(strict=False)
    expected_resolved = expected_raw.resolve(strict=False)
    if actual != expected_resolved:
        raise AcceptanceRunnerError(
            f"{label}未落在本次隔离证据根的约定路径：{actual} ≠ {expected_resolved}"
        )
    return actual


def _normalise_project_root(value: object, *, host: str) -> Path:
    """解析宿主回执中的项目根，拒绝缺失、空值和非路径值。"""

    if isinstance(value, str):
        if not value.strip():
            raise AcceptanceRunnerError(f"宿主 {host} 的项目根缺失，失败关闭")
    elif not isinstance(value, Path):
        raise AcceptanceRunnerError(f"宿主 {host} 的项目根缺失，失败关闭")
    return Path(value).expanduser().resolve(strict=False)

def _receipt_projection(receipt: object) -> dict[str, Any]:
    """把宿主回执统一为字典投影：合同模型走 ``model_dump``，JSON 走原样。"""

    dump = getattr(receipt, "model_dump", None)
    if callable(dump):
        return cast(dict[str, Any], dump(mode="json"))
    if isinstance(receipt, Mapping):
        return dict(receipt)
    raise AcceptanceRunnerError("宿主回执既不是合同模型也不是 JSON 对象，无法绑定")


def _receipt_field(projection: Mapping[str, Any], dotted: str, *, host: str) -> Any:
    value: Any = projection
    for part in dotted.split("."):
        if not isinstance(value, Mapping):
            raise AcceptanceRunnerError(f"宿主 {host} 的回执缺少绑定字段：{dotted}")
        value = value.get(part)
    return value


def _require_host_receipt_binding(
    projection: Mapping[str, Any],
    *,
    host: str,
) -> None:
    """单宿主回执的候选包真实冒烟绑定：种类、状态与宿主可执行来源。"""

    if _receipt_field(projection, "host", host=host) != host:
        raise AcceptanceRunnerError(f"宿主回执的宿主标识不符：期望 {host}")
    if _receipt_field(projection, "receipt_kind", host=host) != "host-smoke-v1":
        raise AcceptanceRunnerError(
            f"宿主 {host} 的回执不是 host-smoke-v1 冒烟回执"
        )
    if _receipt_field(projection, "status", host=host) != "verified":
        raise AcceptanceRunnerError(
            f"宿主 {host} 的冒烟回执状态不是 verified，失败关闭"
        )
    if _receipt_field(projection, "host_executable.provenance", host=host) != (
        "path_resolved"
    ):
        raise AcceptanceRunnerError(
            f"宿主 {host} 的可执行文件不是 PATH 真实解析，不构成真实宿主通过"
        )


def _bind_host_smoke_batch(
    result: Any,
    *,
    layout: Any,
    evidence_root: Path,
    projects_root: Path,
    package_manifest_sha256: str,
    package_name: str,
    package_version: str,
    pre_rc_run_id: str,
) -> dict[str, Any]:
    """绑定一次三宿主真实冒烟批次结果，并核验互异与同包摘要。

    互异：三宿主会话、外部进程、运行标识与项目根两两不同——同进程
    伪造三宿主在本层再次拒绝。同包摘要：三宿主回执绑定同一候选包，
    且包内容摘要与本次候选安装根 ``package-manifest.json`` 的磁盘重算值
    一致。落盘证据：每份回执文件与批次文件必须位于本次隔离证据根的
    约定路径，并与批次结果逐字节一致，防止旧回执复用或事后替换。
    """

    from ci_workflow.application.host_smoke import receipt_digest

    verdict = getattr(result, "verdict", None)
    if verdict is None or getattr(verdict, "real_host_pass", None) is not True:
        reasons = getattr(verdict, "rejection_reasons", None) or {}
        summary_zh = getattr(verdict, "summary_zh", "批次结论缺失")
        detail = "；".join(f"{host}={reason}" for host, reason in sorted(reasons.items()))
        raise AcceptanceRunnerError(
            "三宿主真实冒烟批次未通过，失败关闭：" + str(summary_zh)
            + (f"（{detail}）" if detail else "")
        )
    receipts = getattr(result, "receipts", None)
    if not isinstance(receipts, Mapping) or set(receipts) != set(_PRE_RC_HOSTS):
        raise AcceptanceRunnerError(
            "三宿主冒烟批次必须恰好返回 codex/hermes/omp 三份回执，"
            f"实际 {sorted(receipts) if isinstance(receipts, Mapping) else receipts!r}"
        )
    receipt_paths = getattr(result, "receipt_paths", None)
    batch_path = getattr(result, "batch_path", None)
    if not isinstance(receipt_paths, Mapping) or set(receipt_paths) != set(_PRE_RC_HOSTS):
        raise AcceptanceRunnerError("三宿主冒烟批次缺少逐宿主回执落盘路径")
    if not isinstance(batch_path, Path):
        raise AcceptanceRunnerError("三宿主冒烟批次缺少批次结论落盘路径")

    raw_evidence_root = evidence_root.expanduser()
    raw_projects_root = projects_root.expanduser()
    if raw_evidence_root.is_symlink() or raw_projects_root.is_symlink():
        raise AcceptanceRunnerError("宿主冒烟证据或项目根不得是软链接，失败关闭")
    evidence = raw_evidence_root.resolve()
    projects = raw_projects_root.resolve()
    bound_receipt_paths = {
        host: _require_exact_evidence_path(
            receipt_paths[host],
            expected=evidence / f"{host}.json",
            label=f"宿主 {host} 回执",
        )
        for host in _PRE_RC_HOSTS
    }
    bound_batch_path = _require_exact_evidence_path(
        batch_path,
        expected=evidence / "batch.json",
        label="三宿主批次结论",
    )
    raw_project_roots = getattr(result, "project_roots", None)
    if not isinstance(raw_project_roots, Mapping) or set(raw_project_roots) != set(
        _PRE_RC_HOSTS
    ):
        raise AcceptanceRunnerError("三宿主冒烟批次缺少逐宿主项目根结果，失败关闭")
    expected_project_roots = {
        host: projects / host
        for host in _PRE_RC_HOSTS
    }
    for host in _PRE_RC_HOSTS:
        if _normalise_project_root(raw_project_roots[host], host=host) != (
            expected_project_roots[host]
        ):
            raise AcceptanceRunnerError(
                f"宿主 {host} 的批次项目根未落在本次隔离宿主项目根，失败关闭"
            )

    result_project_roots = {
        host: _normalise_project_root(raw_project_roots[host], host=host)
        for host in _PRE_RC_HOSTS
    }


    projections: dict[str, dict[str, Any]] = {}
    for host in _PRE_RC_HOSTS:
        projection = _receipt_projection(receipts[host])
        _require_host_receipt_binding(projection, host=host)
        projections[host] = projection

    # 互异核验：会话、外部进程、运行标识与项目根两两不同。
    for dotted, label in (
        ("session.session_id", "会话标识"),
        ("process.pid", "外部进程标识"),
        ("run.run_id", "运行标识"),
    ):
        values = {
            host: _receipt_field(projections[host], dotted, host=host)
            for host in _PRE_RC_HOSTS
        }
        for host, value in values.items():
            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                raise AcceptanceRunnerError(f"宿主 {host} 的{label}缺失，失败关闭")
        for host, value in values.items():
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise AcceptanceRunnerError(f"宿主 {host} 的{label}类型无效，失败关闭")
        if len(set(values.values())) != len(_PRE_RC_HOSTS):
            raise AcceptanceRunnerError(
                f"三宿主{label}出现复用（同进程伪造三宿主），失败关闭：{values}"
            )

    project_roots = {
        host: _normalise_project_root(
            _receipt_field(projections[host], "run.project_root", host=host),
            host=host,
        )
        for host in _PRE_RC_HOSTS
    }
    if len(set(project_roots.values())) != len(_PRE_RC_HOSTS):
        raise AcceptanceRunnerError(
            f"三宿主项目根出现复用（同一运行冒充三宿主），失败关闭：{project_roots}"
        )
    for host in _PRE_RC_HOSTS:
        if (
            project_roots[host] != expected_project_roots[host]
            or project_roots[host] != result_project_roots[host]
        ):
            raise AcceptanceRunnerError(
                f"宿主 {host} 的回执项目根未绑定本次隔离宿主项目根，失败关闭"
            )


    for field, expected, label in (
        ("package.name", package_name, "包名称"),
        ("package.version", package_version, "包版本"),
    ):
        values = {
            host: _receipt_field(projections[host], field, host=host)
            for host in _PRE_RC_HOSTS
        }
        for host, value in values.items():
            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                raise AcceptanceRunnerError(f"宿主 {host} 的{label}缺失，失败关闭")
        if any(value != expected for value in values.values()):
            raise AcceptanceRunnerError(
                f"三宿主回执的{label}与候选 package-manifest.json 不一致："
                f"期望 {expected}，实际 {values}"
            )

    # 同包摘要：三宿主运行同一候选包，且与磁盘上的包清单重算值一致。
    package_digests = {
        host: _receipt_field(projections[host], "package.package_digest", host=host)
        for host in _PRE_RC_HOSTS
    }
    for host, value in package_digests.items():
        if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
            raise AcceptanceRunnerError(f"宿主 {host} 的候选包摘要无效，失败关闭")
    if len(set(package_digests.values())) != 1:
        raise AcceptanceRunnerError(
            f"三宿主回执绑定的候选包摘要不一致，失败关闭：{package_digests}"
        )
    bound_digest = next(iter(package_digests.values()))
    if bound_digest != package_manifest_sha256:
        raise AcceptanceRunnerError(
            "三宿主回执绑定的候选包摘要与候选安装根 package-manifest.json "
            f"不一致：回执 {bound_digest} ≠ 磁盘 {package_manifest_sha256}"
        )

    case_ids = {
        host: _receipt_field(projections[host], "fixture.case_id", host=host)
        for host in _PRE_RC_HOSTS
    }
    if set(case_ids.values()) != {"host-smoke-v1"}:
        raise AcceptanceRunnerError(
            f"三宿主冒烟必须绑定唯一案例 host-smoke-v1，实际 {set(case_ids.values())}"
        )
    case_digests = {
        host: _receipt_field(projections[host], "fixture.case_digest", host=host)
        for host in _PRE_RC_HOSTS
    }
    for host, value in case_digests.items():
        if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
            raise AcceptanceRunnerError(f"宿主 {host} 的案例摘要无效，失败关闭")
    if len(set(case_digests.values())) != 1:
        raise AcceptanceRunnerError(
            f"三宿主回执绑定的案例摘要不一致，失败关闭：{case_digests}"
        )

    # 落盘证据核验：磁盘回执必须与本次批次结果一致，防复用与事后替换。
    for host in _PRE_RC_HOSTS:
        path = bound_receipt_paths[host]
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AcceptanceRunnerError(
                f"宿主 {host} 的冒烟回执文件无法读取：{path}"
            ) from exc
        if not isinstance(loaded, dict):
            raise AcceptanceRunnerError(f"宿主 {host} 的冒烟回执文件必须是 JSON 对象")
        if receipt_digest(loaded) != receipt_digest(projections[host]):
            raise AcceptanceRunnerError(
                f"宿主 {host} 的落盘回执与本次批次结果不一致，疑似复用旧回执：{path}"
            )
        if loaded.get("receipt_digest") != receipt_digest(loaded):
            raise AcceptanceRunnerError(
                f"宿主 {host} 的落盘回执自摘要不一致，疑似损坏或伪造：{path}"
            )
    try:
        batch_payload = json.loads(bound_batch_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcceptanceRunnerError(
            f"三宿主批次结论文件无法读取：{bound_batch_path}"
        ) from exc
    if not isinstance(batch_payload, dict):
        raise AcceptanceRunnerError("三宿主批次结论必须是 JSON 对象")
    if batch_payload.get("schema_version") != "1.0":
        raise AcceptanceRunnerError("三宿主批次结论 schema_version 不受支持，失败关闭")
    if batch_payload.get("receipt_kind") != "host-smoke-v1":
        raise AcceptanceRunnerError("三宿主批次结论不是 host-smoke-v1，失败关闭")
    if batch_payload.get("real_host_pass") is not True:
        raise AcceptanceRunnerError("三宿主批次结论未记录真实宿主通过，失败关闭")
    if batch_payload.get("bundle_digest") != layout.bundle_digest:
        raise AcceptanceRunnerError(
            "三宿主批次结论绑定的候选包 digest 与本次候选安装根不一致"
        )
    if batch_payload.get("package_manifest_sha256") != package_manifest_sha256:
        raise AcceptanceRunnerError(
            "三宿主批次结论绑定的 package-manifest 摘要与本次候选安装根不一致"
        )
    if batch_payload.get("receipt_paths") != {
        host: f"{host}.json" for host in _PRE_RC_HOSTS
    }:
        raise AcceptanceRunnerError("三宿主批次结论的回执路径不是本次隔离证据根")
    if batch_payload.get("statuses") != {
        host: "verified" for host in _PRE_RC_HOSTS
    }:
        raise AcceptanceRunnerError("三宿主批次结论未逐项记录 verified 状态")
    if batch_payload.get("rejection_reasons") != {}:
        raise AcceptanceRunnerError("三宿主批次结论仍包含拒绝原因，失败关闭")
    batch_projects = batch_payload.get("project_roots")
    if not isinstance(batch_projects, Mapping) or set(batch_projects) != set(_PRE_RC_HOSTS):
        raise AcceptanceRunnerError("三宿主批次结论缺少逐宿主项目根绑定")
    for host in _PRE_RC_HOSTS:
        if _normalise_project_root(batch_projects[host], host=host) != project_roots[host]:
            raise AcceptanceRunnerError(
                f"宿主 {host} 的批次项目根与宿主回执不一致，失败关闭"
            )

    hosts_summary: dict[str, dict[str, Any]] = {}
    for host in _PRE_RC_HOSTS:
        path = bound_receipt_paths[host]
        hosts_summary[host] = {
            "ok": True,
            "status": "verified",
            "session_id": _receipt_field(projections[host], "session.session_id", host=host),
            "process_pid": _receipt_field(projections[host], "process.pid", host=host),
            "run_id": _receipt_field(projections[host], "run.run_id", host=host),
            "package_digest": package_digests[host],
            "host_executable_provenance": "path_resolved",
            "receipt_relative_path": path.parent.name + "/" + path.name,
            "receipt_sha256": _sha256_file(path),
        }
    return {
        "pre_rc_run_id": pre_rc_run_id,
        "install_root": str(layout.install_root),
        "bundle_digest": layout.bundle_digest,
        "package_manifest_sha256": package_manifest_sha256,
        "case_id": "host-smoke-v1",
        "fixture_case_digest": next(iter(case_digests.values())),
        "real_host_pass": True,
        "hosts": hosts_summary,
        "distinctness": {"session_ids": 3, "process_pids": 3, "run_ids": 3},
        "batch_relative_path": bound_batch_path.name,
        "batch_sha256": _sha256_file(bound_batch_path),
        "summary_zh": str(getattr(verdict, "summary_zh", "")),
    }



def build_host_smoke_stage(
    *,
    install_root: Path,
    acceptance_root: Path,
    expected_bundle_digest: str | None = None,
    smoke_runner: HostSmokeBatchRunner | None = None,
) -> PreRCStageHandler:
    """构造 pre-RC 编排中的 ``host-smoke`` 阶段处理器。

    候选安装根在构建时即核验（失败关闭先于任何阶段执行）；处理器执行时
    重新加载安装根并比对构建时的 bundle digest，防止构建与执行之间发生
    候选包漂移。冒烟回执与宿主项目全部落在隔离验收根下，不写候选安装根，
    也不复用 Task 9.5 的既有宿主回执（证据根预存内容一律失败关闭）。
    ``smoke_runner`` 只供合同测试注入替身批次；缺省使用真实三宿主批次
    ``run_installed_host_smoke``，其批次结论 ``real_host_pass`` 必须为真。
    """

    from ci_workflow.application.fresh_install import (
        FreshInstallError,
        load_fresh_install_layout,
    )

    try:
        layout = load_fresh_install_layout(install_root)
        package_name, package_version = _load_candidate_package_identity(
            layout.package_manifest
        )
        buildtime_entrypoint_sha256 = _sha256_file(layout.entrypoint)
    except FreshInstallError as exc:
        raise AcceptanceRunnerError(f"候选安装根无法核验：{exc}") from exc
    except (AcceptanceRunnerError, OSError) as exc:
        raise AcceptanceRunnerError(f"候选安装根无法核验：{exc}") from exc
    if expected_bundle_digest is not None and expected_bundle_digest != layout.bundle_digest:
        raise AcceptanceRunnerError(
            "候选安装根与预期 bundle 摘要不一致："
            f"期望 {expected_bundle_digest}，实际 {layout.bundle_digest}"
        )
    buildtime_bundle_digest = layout.bundle_digest
    try:
        buildtime_package_manifest_sha256 = _sha256_file(layout.package_manifest)
    except OSError as exc:
        raise AcceptanceRunnerError(f"候选安装根无法核验：{exc}") from exc
    evidence_root = _require_absent_or_empty_root(
        acceptance_root / _HOST_SMOKE_EVIDENCE_DIRECTORY,
        label="宿主冒烟证据根",
    )
    projects_root = _require_absent_or_empty_root(
        acceptance_root / _HOST_SMOKE_PROJECTS_DIRECTORY,
        label="宿主冒烟项目根",
    )
    bundle_root = layout.bundle_root.resolve()
    for protected, label in (
        (evidence_root, "宿主冒烟证据根"),
        (projects_root, "宿主冒烟项目根"),
    ):
        try:
            protected.relative_to(bundle_root)
        except ValueError:
            continue
        raise AcceptanceRunnerError(
            f"{label}不得写入不可变候选 bundle：{protected}"
        )

    def handler(context: Mapping[str, Any]) -> Mapping[str, Any]:
        from ci_workflow.application.host_smoke_runner import HostSmokeRunnerError

        pre_rc_run_id = context.get("pre_rc_run_id")
        if not isinstance(pre_rc_run_id, str) or not pre_rc_run_id.strip():
            raise AcceptanceRunnerError("宿主冒烟阶段缺少本次 pre-RC 运行身份，失败关闭")
        try:
            current_layout = load_fresh_install_layout(install_root)
        except FreshInstallError as exc:
            raise AcceptanceRunnerError(
                f"宿主冒烟执行时候选安装根无法核验（疑似漂移）：{exc}"
            ) from exc
        if current_layout.bundle_digest != buildtime_bundle_digest:
            raise AcceptanceRunnerError(
                "候选安装根在构建与执行之间发生漂移："
                f"构建时 {buildtime_bundle_digest}，执行时 {current_layout.bundle_digest}"
            )
        try:
            current_package_manifest_sha256 = _sha256_file(
                current_layout.package_manifest
            )
            current_package_name, current_package_version = _load_candidate_package_identity(
                current_layout.package_manifest
            )
            current_entrypoint_sha256 = _sha256_file(current_layout.entrypoint)
        except (AcceptanceRunnerError, OSError) as exc:
            raise AcceptanceRunnerError(
                f"宿主冒烟执行时候选安装根无法核验（疑似漂移）：{exc}"
            ) from exc
        if current_package_manifest_sha256 != buildtime_package_manifest_sha256:
            raise AcceptanceRunnerError("候选包清单在构建与执行之间发生漂移，失败关闭")
        if (
            current_package_name != package_name
            or current_package_version != package_version
        ):
            raise AcceptanceRunnerError(
                "候选包身份在构建与执行之间发生漂移，失败关闭"
            )
        if current_entrypoint_sha256 != buildtime_entrypoint_sha256:
            raise AcceptanceRunnerError(
                "候选包真实入口在构建与执行之间发生漂移，失败关闭"
            )
        _require_absent_or_empty_root(evidence_root, label="宿主冒烟证据根")
        _require_absent_or_empty_root(projects_root, label="宿主冒烟项目根")

        runner = smoke_runner
        if runner is None:
            from ci_workflow.application.host_smoke_runner import (
                run_installed_host_smoke,
            )

            runner = run_installed_host_smoke
        try:
            result = runner(
                current_layout,
                evidence_root=evidence_root,
                project_root=projects_root,
            )
        except HostSmokeRunnerError as exc:
            raise AcceptanceRunnerError(f"三宿主真实冒烟失败关闭：{exc}") from exc
        except Exception as exc:  # noqa: BLE001 - 任一宿主异常都必须失败关闭
            raise AcceptanceRunnerError(f"三宿主真实冒烟失败关闭：{exc}") from exc
        return _bind_host_smoke_batch(
            result,
            layout=current_layout,
            evidence_root=evidence_root,
            projects_root=projects_root,
            package_manifest_sha256=current_package_manifest_sha256,
            package_name=package_name,
            package_version=package_version,
            pre_rc_run_id=pre_rc_run_id,
        )

    return handler


def build_project_verify_stage(
    *,
    catalog_path: Path | None = None,
    case_id: str = _DEFAULT_CASE_ID,
) -> PreRCStageHandler:
    """构造 pre-RC 编排中的 ``project-verify`` 阶段处理器（最终项目核验）。

    在三宿主真实冒烟之后重新打开并核验当前运行：清单完整性、案例与
    pre-RC 绑定、A/B/C 三个 HTML 当前产物的逐项摘要，以及三份 ego(lite)
    回执的逐字节一致性。宿主冒烟期间任何对当前运行或产物的改动都会在
    本阶段失败关闭。
    """

    def handler(context: Mapping[str, Any]) -> Mapping[str, Any]:
        pre_rc_run_id = context.get("pre_rc_run_id")
        if not isinstance(pre_rc_run_id, str) or not pre_rc_run_id.strip():
            raise AcceptanceRunnerError("最终项目核验缺少本次 pre-RC 运行身份，失败关闭")
        raw_root = context.get("project_root")
        if not isinstance(raw_root, str) or not raw_root.strip():
            raise AcceptanceRunnerError("最终项目核验缺少项目根路径，失败关闭")
        root = Path(raw_root).expanduser().resolve()
        catalog = load_acceptance_catalog(catalog_path)
        context_catalog_sha256 = context.get("catalog_sha256")
        if isinstance(context_catalog_sha256, str) and context_catalog_sha256 != (
            catalog.sha256
        ):
            raise AcceptanceRunnerError("验收 catalog 在运行中途发生漂移，失败关闭")
        resolved = resolve_acceptance_case(case_id, catalog)
        if context.get("case_id") != resolved.case_id:
            raise AcceptanceRunnerError("最终项目核验的案例标识与编排上下文不一致")
        if context.get("case_digest") != resolved.case_digest:
            raise AcceptanceRunnerError("最终项目核验的案例摘要与 catalog 锁定值不一致")

        project_run = context.get("project_run")
        html_pipeline = context.get("html_pipeline")
        if not isinstance(project_run, Mapping) or not isinstance(html_pipeline, Mapping):
            raise AcceptanceRunnerError(
                "最终项目核验缺少前置项目运行或浏览器回执阶段摘要，失败关闭"
            )
        bound_run_id = project_run.get("run_id")
        bound_artifacts = html_pipeline.get("artifacts")
        bound_receipts = html_pipeline.get("receipts")
        if (
            not isinstance(bound_run_id, str)
            or not bound_run_id.strip()
            or not isinstance(bound_artifacts, Mapping)
            or not isinstance(bound_receipts, Mapping)
        ):
            raise AcceptanceRunnerError(
                "最终项目核验的前置阶段摘要缺少运行标识、产物或回执绑定，失败关闭"
            )

        try:
            project_verification = verify_project_workspace(root)
        except ProjectWorkspaceError as exc:
            raise AcceptanceRunnerError(
                f"最终项目核验无法校验项目合同：{exc}"
            ) from exc
        contract = project_verification.contract
        contract_reports = tuple(report.value for report in contract.reports)
        if contract_reports != resolved.reports:
            raise AcceptanceRunnerError(
                "最终项目核验的项目合同报告集合与 catalog 不一致："
                f"{contract_reports} ≠ {resolved.reports}"
            )
        contract_formats = tuple(output.value for output in contract.outputs)
        if contract_formats != ("html",):
            raise AcceptanceRunnerError(
                "最终项目核验的项目合同格式必须严格为 html："
                f"{contract_formats}"
            )
        if contract.indication != resolved.indication:
            raise AcceptanceRunnerError("最终项目核验的项目合同适应症与 catalog 不一致")
        if contract.timezone != resolved.timezone:
            raise AcceptanceRunnerError("最终项目核验的项目合同时间区与 catalog 不一致")
        # ProjectContract 将截止规范化为该日期的 23:59:59.999999；比较
        # 日期与时区偏移，不把无意义的微秒规范化差异当作科学漂移。
        contract_cutoff = contract.data_cutoff.astimezone(
            ZoneInfo(resolved.timezone)
        )
        resolved_cutoff = resolved.data_cutoff.astimezone(ZoneInfo(resolved.timezone))
        if (
            contract_cutoff.date() != resolved_cutoff.date()
            or contract_cutoff.utcoffset() != resolved_cutoff.utcoffset()
        ):
            raise AcceptanceRunnerError("最终项目核验的项目合同截止与 catalog 不一致")

        try:
            manifest = validate_run_manifest(root)
        except RunError as exc:
            raise AcceptanceRunnerError(f"最终项目核验无法校验当前运行清单：{exc}") from exc
        if manifest.get("run_id") != bound_run_id:
            raise AcceptanceRunnerError(
                "当前运行标识与项目运行阶段绑定不一致："
                f"{manifest.get('run_id')!r} ≠ {bound_run_id!r}"
            )
        if manifest.get(_PRE_RC_RUN_METADATA_KEY) != pre_rc_run_id:
            raise AcceptanceRunnerError("当前运行清单未绑定本次 pre-RC 运行身份")

        artifacts, _sources, run_info = _discover_current_html_artifacts(
            root,
            resolved=resolved,
            pre_rc_run_id=pre_rc_run_id,
        )
        current_run_id = run_info["run_id"]
        if current_run_id != bound_run_id:
            raise AcceptanceRunnerError("当前运行标识在核验之间发生变化，失败关闭")
        compared_fields = (
            "version",
            "site_relative_path",
            "site_sha256",
            "site_byte_size",
            "manifest_relative_path",
            "manifest_sha256",
            "manifest_id",
            "report_snapshot_id",
            "generated_at",
            "entry_route",
            "entry_relative_path",
            "entry_sha256",
            "route_count",
        )
        for report in resolved.reports:
            current = artifacts[report].to_summary()
            bound = bound_artifacts.get(report)
            if not isinstance(bound, Mapping):
                raise AcceptanceRunnerError(f"{report} 类产物缺少浏览器阶段绑定摘要")
            drifted = [
                field
                for field in compared_fields
                if current.get(field) != bound.get(field)
            ]
            if drifted:
                raise AcceptanceRunnerError(
                    f"{report} 类 HTML 产物在浏览器验收之后被改动，失败关闭："
                    + "、".join(drifted)
                )

        rebound = run_ego_receipt_stage(
            project_root=root,
            resolved=resolved,
            pre_rc_run_id=pre_rc_run_id,
        )
        for report in resolved.reports:
            current_receipt = rebound["receipts"][report]
            bound_receipt = bound_receipts.get(report)
            if not isinstance(bound_receipt, Mapping):
                raise AcceptanceRunnerError(f"{report} 类回执缺少浏览器阶段绑定摘要")
            if current_receipt["receipt_sha256"] != bound_receipt.get("receipt_sha256"):
                raise AcceptanceRunnerError(
                    f"{report} 类 ego(lite) 回执文件在绑定之后被改动，失败关闭"
                )

        return {
            "pre_rc_run_id": pre_rc_run_id,
            "run_id": current_run_id,
            "case_id": resolved.case_id,
            "case_digest": resolved.case_digest,
            "manifest_relative_path": "manifests/current_run.json",
            "manifest_sha256": _sha256_file(root / "manifests" / "current_run.json"),
            "artifacts": {
                report: artifacts[report].to_summary() for report in resolved.reports
            },
            "browser_receipts_unchanged": True,
            "verified_zh": (
                "最终项目核验通过：当前运行清单、A/B/C 三个站点式 HTML 产物与三份 "
                "ego(lite) 浏览器回执在三宿主冒烟之后逐项一致，未被改动。"
            ),
        }

    return handler


def complete_pre_rc_rehearsal(
    *,
    project_root: Path,
    catalog_path: Path | None = None,
    case_id: str = _DEFAULT_CASE_ID,
    host_smoke_stage: PreRCStageHandler | None = None,
    project_verify_stage: PreRCStageHandler | None = None,
    receipts_stage: PreRCStageHandler | None = None,
) -> dict[str, Any]:
    """在已完成 ego(lite) 回执绑定的当前运行上继续 pre-RC 后三阶段。

    阶段 1-3 按 ``bind_ego_receipts_pipeline`` 同一合同重新核验（不重跑
    项目），随后按固定顺序执行宿主真实冒烟 → 最终项目核验 → 场景回执
    聚合。任何处理器缺失或阶段失败都向上抛出，调用方不得输出通过信号；
    ``PRE_RC_REHEARSAL_OK`` 只能由本入口在六个阶段全部通过后渲染。
    """

    handlers = _require_pre_rc_handlers(
        (
            ("host-smoke", host_smoke_stage),
            ("project-verify", project_verify_stage),
            ("pre-rc-receipts", receipts_stage),
        )
    )
    catalog = load_acceptance_catalog(catalog_path)
    resolved = resolve_acceptance_case(case_id, catalog)
    stage_results, context, run_id = _reverify_and_bind_current_run(
        catalog=catalog,
        resolved=resolved,
        project_root=project_root,
    )
    _append_stage_outcomes(handlers, stage_results=stage_results, context=context)
    return _pipeline_summary(
        pre_rc_run_id=run_id,
        catalog=catalog,
        resolved=resolved,
        project_root=Path(str(context["project_root"])),
        stage_results=stage_results,
    )


# ─── required-v12 full-matrix 场景 rehearsal 回执与未来责任保护 ─────────────


@dataclass(frozen=True)
class ScenarioVerifierOutcome:
    """一次场景 verifier 预演的结果；只保存精简摘要与输出摘要，不保存原始日志。"""

    case_id: str
    target: str
    command: str
    ok: bool
    exit_code: int | None
    duration_ms: int
    output_sha256: str
    error_zh: str | None = None

    def to_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "target": self.target,
            "command": self.command,
            "ok": self.ok,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "output_sha256": self.output_sha256,
        }
        if self.error_zh is not None:
            summary["error_zh"] = self.error_zh
        return summary


VerifierRunner = Callable[[str, str, str], ScenarioVerifierOutcome]


def subprocess_verifier_runner(case_id: str, target: str, command: str) -> ScenarioVerifierOutcome:
    """默认 verifier 执行器：以仓库根为工作目录运行 catalog 声明的 pytest 命令。

    只执行 catalog 逐字声明的命令（``uv run pytest …``）；输出不落盘，仅记录
    输出摘要、退出码与耗时。超时或无法启动按失败处理，不猜测通过。
    """

    started = time.monotonic()
    error_zh: str | None = None
    output_text = ""
    ok = False
    exit_code: int | None = None
    try:
        argv = shlex.split(command)
        completed = subprocess.run(  # noqa: S603 - 命令逐字来自 digest 锁定的 catalog
            argv,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=_VERIFIER_TIMEOUT_SECONDS,
            check=False,
        )
        exit_code = completed.returncode
        ok = completed.returncode == 0
        output_text = f"{completed.stdout or ''}\x00{completed.stderr or ''}"
    except subprocess.TimeoutExpired as exc:
        error_zh = f"verifier 超时（超过 {_VERIFIER_TIMEOUT_SECONDS} 秒），按失败处理"
        stdout_text = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else str(exc.stdout or "")
        )
        stderr_text = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else str(exc.stderr or "")
        )
        output_text = f"{stdout_text}\x00{stderr_text}"
    except OSError as exc:
        error_zh = f"verifier 无法启动：{exc}"
    duration_ms = int((time.monotonic() - started) * 1000)
    return ScenarioVerifierOutcome(
        case_id=case_id,
        target=target,
        command=command,
        ok=ok,
        exit_code=exit_code,
        duration_ms=duration_ms,
        output_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        error_zh=error_zh,
    )


def resolve_full_matrix_suite(catalog: AcceptanceCatalog) -> tuple[ResolvedAcceptanceCase, ...]:
    """从 catalog 解析 ``--suite full`` 套件：全部 ``execution_scope=full-matrix`` 案例。

    套件成员完全由 catalog 决定；出现未登记的执行范围、或套件为空时失败关闭。
    每个成员都经过完整的 HTML-only、案例摘要与逐文件输入摘要核验。
    """

    suite: list[ResolvedAcceptanceCase] = []
    for case_id, case in catalog.cases.items():
        scope = _required_str(case.get("execution_scope"), f"案例 {case_id} execution_scope")
        if scope not in _KNOWN_EXECUTION_SCOPES:
            raise AcceptanceRunnerError(
                f"案例 {case_id} 执行范围未登记，拒绝静默归类或关闭：{scope}"
            )
        if scope == _FULL_MATRIX_EXECUTION_SCOPE:
            suite.append(resolve_acceptance_case(case_id, catalog))
    if not suite:
        raise AcceptanceRunnerError("catalog 中没有任何 execution_scope=full-matrix 的首版案例")
    if all(resolved.case_id != _DEFAULT_CASE_ID for resolved in suite):
        raise AcceptanceRunnerError(
            f"full-matrix 套件必须包含 A/B/C 全量基准案例 {_DEFAULT_CASE_ID}"
        )
    return tuple(suite)


def _load_case_subscenarios(resolved: ResolvedAcceptanceCase) -> tuple[dict[str, str], ...]:
    """解析案例声明的子场景（inputs/scenario.json）；未声明则返回空。

    scenario.json 已在阶段 1 通过 catalog 摘要核验；此处重新核验字节后解析，
    并逐项检查 case_id、release_scope、formats 与子场景结构，任一漂移失败关闭。
    """

    relative = _SCENARIO_RELATIVE_PATH
    if relative not in resolved.input_digests:
        return ()
    declared_digest = resolved.input_digests[relative]
    _verify_case_file(resolved.fixture_root, relative, declared_digest, kind="输入")
    path = resolved.fixture_root / relative
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcceptanceRunnerError(
            f"案例 {resolved.case_id} 子场景定义无法读取：{relative}"
        ) from exc
    if not isinstance(payload, dict):
        raise AcceptanceRunnerError(f"案例 {resolved.case_id} 子场景定义顶层必须是对象")
    if payload.get("case_id") != resolved.case_id:
        raise AcceptanceRunnerError(f"案例 {resolved.case_id} 子场景定义 case_id 不一致")
    if payload.get("release_scope") != _RELEASE_SCOPE:
        raise AcceptanceRunnerError(
            f"案例 {resolved.case_id} 子场景 release_scope 必须为 {_RELEASE_SCOPE}"
        )
    if payload.get("formats") != ["html"]:
        raise AcceptanceRunnerError(
            f"案例 {resolved.case_id} 子场景格式必须严格为 [html]，实际 {payload.get('formats')!r}"
        )
    raw_subscenarios = payload.get("subscenarios")
    if not isinstance(raw_subscenarios, list) or not raw_subscenarios:
        raise AcceptanceRunnerError(f"案例 {resolved.case_id} 缺少 subscenarios 声明")
    subscenarios: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_subscenarios):
        if not isinstance(raw, dict):
            raise AcceptanceRunnerError(f"案例 {resolved.case_id} 子场景 #{index} 必须是对象")
        sub_id = raw.get("id")
        description = raw.get("description_zh")
        if not isinstance(sub_id, str) or not sub_id.strip():
            raise AcceptanceRunnerError(f"案例 {resolved.case_id} 子场景 #{index} 缺少 id")
        if not isinstance(description, str) or not description.strip():
            raise AcceptanceRunnerError(f"案例 {resolved.case_id} 子场景 {sub_id} 缺少中文说明")
        if sub_id in seen:
            raise AcceptanceRunnerError(f"案例 {resolved.case_id} 子场景存在重复 id：{sub_id}")
        seen.add(sub_id)
        subscenarios.append({"id": sub_id, "description_zh": description})
    return tuple(subscenarios)


def _declared_verifier_commands(
    case_id: str,
    case: Mapping[str, Any],
) -> tuple[tuple[str, str], ...]:
    """读取案例声明的 verifier 列表，返回 (target, command) 序列。

    字符串形式按 ``uv run pytest <target> -q`` 执行；结构形式必须声明
    ``kind: pytest`` 且命令逐字以 ``uv run pytest`` 开头并包含其 target。
    任何其他 kind 或命令形态都失败关闭：catalog 不得借 verifier 执行任意命令。
    """

    raw_verifiers = case.get("verifiers")
    if not isinstance(raw_verifiers, list) or not raw_verifiers:
        raise AcceptanceRunnerError(f"案例 {case_id} 缺少 verifier 声明，无法预演")
    commands: list[tuple[str, str]] = []
    for index, raw in enumerate(raw_verifiers):
        if isinstance(raw, str):
            if not raw.strip():
                raise AcceptanceRunnerError(f"案例 {case_id} verifier #{index} 不能为空")
            target = raw
            command = f"uv run pytest {target} -q"
        elif isinstance(raw, dict):
            kind = raw.get("kind")
            if kind != "pytest":
                raise AcceptanceRunnerError(
                    f"案例 {case_id} verifier #{index} kind 必须为 pytest，实际 {kind!r}"
                )
            target = _required_str(raw.get("target"), f"案例 {case_id} verifier #{index} target")
            command = _required_str(raw.get("command"), f"案例 {case_id} verifier #{index} command")
            if target not in command:
                raise AcceptanceRunnerError(
                    f"案例 {case_id} verifier #{index} command 未包含其 target：{command}"
                )
        else:
            raise AcceptanceRunnerError(f"案例 {case_id} verifier #{index} 必须是字符串或对象")
        argv = shlex.split(command)
        if argv[:3] != ["uv", "run", "pytest"]:
            raise AcceptanceRunnerError(
                f"案例 {case_id} verifier 命令必须以 'uv run pytest' 开头：{command}"
            )
        commands.append((target, command))
    return tuple(commands)


def _rehearse_case_verifiers(
    resolved: ResolvedAcceptanceCase,
    case: Mapping[str, Any],
    runner: VerifierRunner,
) -> tuple[ScenarioVerifierOutcome, ...]:
    """逐条执行案例声明的 verifier 并收集结果；任一失败由调用方失败关闭。"""

    outcomes = [
        runner(resolved.case_id, target, command)
        for target, command in _declared_verifier_commands(resolved.case_id, case)
    ]
    if not outcomes:
        raise AcceptanceRunnerError(f"案例 {resolved.case_id} 没有可执行的 verifier")
    return tuple(outcomes)


def _bind_host_smoke_summary(
    host_smoke_summary: Mapping[str, Any] | None,
    *,
    pre_rc_run_id: str,
) -> tuple[tuple[str, ...], bool]:
    """校验宿主冒烟阶段摘要的三宿主绑定，返回 (宿主序列, 是否绑定)。

    合同：``ok is True`` 且 ``hosts`` 恰好覆盖 ``codex``/``hermes``/``omp``
    三个宿主、每个宿主条目 ``ok is True``；摘要若携带 ``pre_rc_run_id``，
    必须与本次运行身份一致。宿主进程/会话/运行互异的深核验由宿主冒烟阶段
    自身负责；本层只绑定宿主集合与总结果，防止在缺宿主证据时输出通过信号。
    """

    if host_smoke_summary is None:
        return (), False
    if not isinstance(host_smoke_summary, Mapping) or host_smoke_summary.get("ok") is not True:
        raise AcceptanceRunnerError("宿主冒烟阶段摘要缺失或未通过，拒绝生成场景回执")
    summary_pre_rc = host_smoke_summary.get("pre_rc_run_id")
    if summary_pre_rc is not None:
        if not isinstance(summary_pre_rc, str) or not summary_pre_rc.strip():
            raise AcceptanceRunnerError("宿主冒烟阶段摘要的 pre-RC 运行身份无效")
        if summary_pre_rc != pre_rc_run_id:
            raise AcceptanceRunnerError(
                "宿主冒烟阶段摘要绑定了另一次 pre-RC 运行，拒绝复用旧宿主回执"
            )
    raw_hosts = host_smoke_summary.get("hosts")
    if not isinstance(raw_hosts, Mapping) or set(raw_hosts) != set(_PRE_RC_HOSTS):
        raise AcceptanceRunnerError(
            "宿主冒烟阶段必须恰好绑定 codex/hermes/omp 三个宿主，"
            f"实际 {sorted(raw_hosts) if isinstance(raw_hosts, Mapping) else raw_hosts!r}"
        )
    for host in _PRE_RC_HOSTS:
        entry = raw_hosts[host]
        if not isinstance(entry, Mapping) or entry.get("ok") is not True:
            raise AcceptanceRunnerError(f"宿主 {host} 的冒烟绑定未通过，拒绝生成场景回执")
    return _PRE_RC_HOSTS, True


def _classifiable_catalog_case(case_id: str, case: Mapping[str, Any]) -> dict[str, Any]:
    """读取非套件案例的分类所需字段；回执所有权缺失或未登记时失败关闭。"""

    receipt = case.get("receipt")
    if not isinstance(receipt, dict):
        raise AcceptanceRunnerError(f"案例 {case_id} 缺少 receipt 声明，无法分类责任归属")
    owner_status = receipt.get("owner_status")
    if not isinstance(owner_status, str) or owner_status not in _CATALOG_OWNER_STATUSES:
        raise AcceptanceRunnerError(
            f"案例 {case_id} catalog 回执 owner_status 未登记或不可识别：{owner_status!r}"
        )
    scope = _required_str(case.get("execution_scope"), f"案例 {case_id} execution_scope")
    if scope not in _KNOWN_EXECUTION_SCOPES:
        raise AcceptanceRunnerError(f"案例 {case_id} 执行范围未登记：{scope}")
    return {
        "owner_status": owner_status,
        "scope": scope,
        "receipt_relative_path": receipt.get("relative_path"),
    }


_FUTURE_OWNER_REASON_ZH: Mapping[str, str] = {
    "recovery": (
        "最终恢复演练属于 Task 10.6 恢复责任阶段：恢复包安装、恢复、刷新与"
        "代表性 HTML 重建未由本 runner 执行，保持 pending_future_owner，不得提前关闭。"
    ),
    "legacy-cutover": (
        "旧根处置属于 Task 10.8 切换授权阶段：需最终恢复完成且获得用户明确授权后"
        "按精确清单核验，本 runner 不提前删除或登记无残留，保持 pending_future_owner。"
    ),
}


def build_full_matrix_suite_receipts(
    catalog: AcceptanceCatalog,
    *,
    pre_rc_run_id: str,
    host_smoke_summary: Mapping[str, Any] | None = None,
    pipeline_binding: Mapping[str, Any] | None = None,
    verifier_runner: VerifierRunner | None = None,
) -> dict[str, Any]:
    """构建 ``--suite full`` 场景 rehearsal 回执并保护全部未来责任。

    只把本轮真正预演过的 ``execution_scope=full-matrix`` case/子 case 记为
    ``pre_rc_rehearsal``：每个案例逐条执行其 catalog 声明的 verifier 并绑定
    结果摘要，子场景从案例目录的 ``scenario.json`` 逐项枚举。恢复、切换案例
    按 catalog 回执所有权保持 ``pending_future_owner``；条件扩展案例保持
    ``not_applicable``；Task 10.1 已持有的案例记录在套件之外。任何发布案例
    关闭计数都不为 0——``release_cases_closed`` 恒为 0，否则失败关闭。
    PDF、HTML-PPT 与 PPTX 作为未来格式单独记录，不进入任何回执的格式集合。
    """

    if not isinstance(pre_rc_run_id, str) or not pre_rc_run_id.strip():
        raise AcceptanceRunnerError("场景回执必须绑定本次 pre-RC 运行身份")
    runner = verifier_runner or subprocess_verifier_runner
    suite = resolve_full_matrix_suite(catalog)
    suite_by_id = {resolved.case_id: resolved for resolved in suite}
    if _DEFAULT_CASE_ID not in suite_by_id:
        raise AcceptanceRunnerError(
            f"full-matrix 套件缺少 A/B/C 全量基准案例 {_DEFAULT_CASE_ID}"
        )
    hosts, host_smoke_bound = _bind_host_smoke_summary(
        host_smoke_summary, pre_rc_run_id=pre_rc_run_id
    )

    binding: dict[str, Any] | None = None
    if pipeline_binding is not None:
        if not isinstance(pipeline_binding, Mapping) or pipeline_binding.get("ok") is not True:
            raise AcceptanceRunnerError("当前运行绑定摘要缺失或未通过，拒绝生成场景回执")
        if pipeline_binding.get("reports") != ["A", "B", "C"]:
            raise AcceptanceRunnerError("当前运行绑定摘要的报告集合不是 A/B/C")
        if pipeline_binding.get("formats") != ["html"]:
            raise AcceptanceRunnerError("当前运行绑定摘要出现首版范围外格式")
        if pipeline_binding.get("case_id") != _DEFAULT_CASE_ID:
            raise AcceptanceRunnerError("当前运行绑定摘要的案例不是 A/B/C 全量基准")
        binding = dict(pipeline_binding)

    receipts: list[dict[str, Any]] = []
    for case_id, case in catalog.cases.items():
        scope = _required_str(case.get("execution_scope"), f"案例 {case_id} execution_scope")
        if scope not in _KNOWN_EXECUTION_SCOPES:
            raise AcceptanceRunnerError(f"案例 {case_id} 执行范围未登记：{scope}")
        meta = _classifiable_catalog_case(case_id, case)
        base = {
            "case_id": case_id,
            "name_zh": case.get("name_zh") if isinstance(case.get("name_zh"), str) else None,
            "family": _required_str(case.get("family"), f"案例 {case_id} family"),
            "execution_scope": scope,
            "owner_task": _required_str(case.get("owner_task"), f"案例 {case_id} owner_task"),
            "catalog_receipt_owner_status": meta["owner_status"],
            "catalog_receipt_relative_path": meta["receipt_relative_path"],
        }
        if scope == _FULL_MATRIX_EXECUTION_SCOPE:
            if meta["owner_status"] == NOT_APPLICABLE_STATUS:
                raise AcceptanceRunnerError(
                    f"案例 {case_id} 属于 full-matrix 预演套件，catalog 回执不得为 not_applicable"
                )
            resolved = suite_by_id[case_id]
            outcomes = _rehearse_case_verifiers(resolved, case, runner)
            failed = [outcome for outcome in outcomes if not outcome.ok]
            if failed:
                details = "；".join(
                    f"{outcome.target}（退出码 {outcome.exit_code}）" for outcome in failed
                )
                raise AcceptanceRunnerError(
                    f"案例 {case_id} 场景预演存在未通过的 verifier，失败关闭：{details}"
                )
            subscenarios = _load_case_subscenarios(resolved)
            receipts.append(
                {
                    **base,
                    "case_digest": resolved.case_digest,
                    "reports": list(resolved.reports),
                    "formats": list(resolved.formats),
                    "status": REHEARSAL_STATUS,
                    "release_case_closed": False,
                    "pre_rc_run_id": pre_rc_run_id,
                    "verified_input_count": len(resolved.inputs),
                    "evidence_kind": "catalog-verifier-rehearsal",
                    "verifiers": [outcome.to_summary() for outcome in outcomes],
                    "subscenarios": [
                        {
                            "case_id": case_id,
                            "id": sub["id"],
                            "description_zh": sub["description_zh"],
                            "status": REHEARSAL_STATUS,
                            "release_case_closed": False,
                        }
                        for sub in subscenarios
                    ],
                }
            )
            continue

        raw_formats = case.get("formats")
        if raw_formats != ["html"]:
            raise AcceptanceRunnerError(
                f"案例 {case_id} 首版格式必须严格为 [html]，实际 {raw_formats!r}"
            )
        declared_digest = _parse_sha256(case.get("case_digest"), f"案例 {case_id} case_digest")
        owner_status = meta["owner_status"]
        if owner_status == PENDING_FUTURE_OWNER_STATUS:
            status = PENDING_FUTURE_OWNER_STATUS
            reason_zh = _FUTURE_OWNER_REASON_ZH.get(
                scope,
                "该案例的验收回执属于未来责任阶段；本 runner 不预演、不关闭。",
            )
        elif owner_status == NOT_APPLICABLE_STATUS:
            status = NOT_APPLICABLE_STATUS
            reason_zh = (
                "按项目合同该场景条件不适用（可选适配器未被首版合同选择）；"
                "本 runner 不猜测合同选择，回执保持 not_applicable，不计入发布通过。"
            )
        else:
            status = _OUTSIDE_SUITE_STATUS
            reason_zh = (
                "该案例由既有责任阶段持有（Task 10.1 已登记 current_owner），"
                "不属于本次 full-matrix 预演套件，本 runner 不重复预演或改写其归属。"
            )
        receipts.append(
            {
                **base,
                "case_digest": declared_digest,
                "reports": list(case.get("reports") or []),
                "formats": ["html"],
                "status": status,
                "release_case_closed": False,
                "reason_zh": reason_zh,
            }
        )

    for receipt in receipts:
        if receipt["formats"] != ["html"]:
            raise AcceptanceRunnerError(
                f"案例 {receipt['case_id']} 回执出现首版范围外格式：{receipt['formats']}"
            )
    closed_ids = [
        receipt["case_id"]
        for receipt in receipts
        if receipt.get("release_case_closed") is True
        or receipt["status"] in _RELEASE_CLOSED_STATUSES
    ]
    if closed_ids:
        raise AcceptanceRunnerError(
            "场景回执出现发布案例关闭记录，失败关闭"
            f"（Task 10.6/恢复/切换责任不得由本 runner 关闭）：{'、'.join(closed_ids)}"
        )

    counts = {
        "catalog_cases_total": len(receipts),
        "suite_cases": len(suite),
        "rehearsed": sum(1 for r in receipts if r["status"] == REHEARSAL_STATUS),
        "pending_future_owner": sum(
            1 for r in receipts if r["status"] == PENDING_FUTURE_OWNER_STATUS
        ),
        "not_applicable": sum(1 for r in receipts if r["status"] == NOT_APPLICABLE_STATUS),
        "outside_suite": sum(1 for r in receipts if r["status"] == _OUTSIDE_SUITE_STATUS),
    }
    return {
        "suite": "full",
        "pre_rc_run_id": pre_rc_run_id,
        "catalog_path": str(catalog.path),
        "catalog_sha256": catalog.sha256,
        "release_scope": catalog.release_scope,
        "primary_case_id": _DEFAULT_CASE_ID,
        "formats": ["html"],
        "hosts": list(hosts),
        "host_smoke_bound": host_smoke_bound,
        "pipeline_binding": binding,
        "suite_case_ids": [resolved.case_id for resolved in suite],
        "receipts": receipts,
        "counts": counts,
        "release_cases_closed": 0,
        "closed_case_ids": [],
        "future_formats": {
            "deferred_formats": list(_DEFERRED_FORMATS),
            "status": PENDING_FUTURE_OWNER_STATUS,
            "release_case_closed": False,
            "basis": "ADR 0013",
            "note_zh": (
                "PDF、HTML-PPT、PPTX 保留既有 Phase 8 检查点与未来责任；本次不生成、"
                "不验证、不因缺失阻断站点式 HTML，也不计入首版 artifact 集合。"
            ),
        },
    }


def build_pre_rc_receipts_stage(
    *,
    catalog_path: Path | None = None,
    case_id: str = _DEFAULT_CASE_ID,
    verifier_runner: VerifierRunner | None = None,
) -> PreRCStageHandler:
    """构造 pre-RC 编排中的 ``pre-rc-receipts`` 阶段处理器。

    处理器从上游上下文读取当前运行绑定（pre-RC 运行身份、案例/摘要、项目
    运行与浏览器回执阶段摘要）和宿主冒烟阶段摘要，重新核验 catalog 未漂移后
    生成 full-matrix 套件回执。宿主冒烟摘要必须恰好绑定三个宿主并通过。
    """

    def handler(context: Mapping[str, Any]) -> Mapping[str, Any]:
        pre_rc_run_id = context.get("pre_rc_run_id")
        if not isinstance(pre_rc_run_id, str) or not pre_rc_run_id.strip():
            raise AcceptanceRunnerError("场景回执阶段缺少 pre-RC 运行身份，失败关闭")
        context_case_id = context.get("case_id")
        context_case_digest = context.get("case_digest")
        context_catalog_sha256 = context.get("catalog_sha256")
        if not isinstance(context_case_id, str) or context_case_id != case_id:
            raise AcceptanceRunnerError(
                f"场景回执阶段案例标识与编排上下文不一致：{context_case_id!r} ≠ {case_id!r}"
            )
        host_summary = context.get("host_smoke")
        catalog = load_acceptance_catalog(catalog_path)
        if (
            isinstance(context_catalog_sha256, str)
            and context_catalog_sha256 != catalog.sha256
        ):
            raise AcceptanceRunnerError("验收 catalog 在运行中途发生漂移，失败关闭")
        resolved = resolve_acceptance_case(case_id, catalog)
        if not isinstance(context_case_digest, str) or context_case_digest != resolved.case_digest:
            raise AcceptanceRunnerError("场景回执阶段案例摘要与 catalog 锁定值不一致")

        project_run = context.get("project_run")
        html_pipeline = context.get("html_pipeline")
        project_run_id = (
            project_run.get("run_id") if isinstance(project_run, Mapping) else None
        )
        html_reports = (
            html_pipeline.get("reports") if isinstance(html_pipeline, Mapping) else None
        )
        browser_receipt_count = (
            len(html_pipeline.get("receipts") or {})
            if isinstance(html_pipeline, Mapping)
            else None
        )
        if html_reports != ["A", "B", "C"] or browser_receipt_count != 3:
            raise AcceptanceRunnerError(
                "场景回执阶段要求前置 HTML 流水线已绑定 A/B/C 三报告与三份浏览器回执"
            )
        if not isinstance(project_run_id, str) or not project_run_id.strip():
            raise AcceptanceRunnerError("场景回执阶段缺少当前项目运行标识")
        binding: dict[str, Any] = {
            "ok": True,
            "case_id": context_case_id,
            "case_digest": resolved.case_digest,
            "project_run_id": project_run_id,
            "reports": html_reports,
            "formats": ["html"],
            "browser_receipt_count": browser_receipt_count,
        }

        if host_summary is None:
            raise AcceptanceRunnerError(
                "场景回执阶段缺少宿主冒烟阶段摘要，失败关闭：必须先完成三宿主真实冒烟"
            )

        payload = build_full_matrix_suite_receipts(
            catalog,
            pre_rc_run_id=pre_rc_run_id,
            host_smoke_summary=host_summary,
            pipeline_binding=binding,
            verifier_runner=verifier_runner,
        )
        return payload

    return handler


def run_full_matrix_suite_rehearsal(
    *,
    catalog_path: Path | None = None,
    verifier_runner: VerifierRunner | None = None,
) -> dict[str, Any]:
    """独立执行 ``--suite full`` 场景 rehearsal：catalog 真值 + verifier 预演 + 责任分类。

    本入口不运行项目、不启动浏览器、不执行宿主冒烟，因此其回执不绑定宿主
    （``host_smoke_bound=False``），也绝不能用于输出 ``PRE_RC_REHEARSAL_OK``
    全量成功信号——该信号只能来自完整六阶段流水线。
    """

    catalog = load_acceptance_catalog(catalog_path)
    suite_run_id = stable_id(
        "pre-rc-suite",
        catalog.sha256,
        datetime.now(UTC).isoformat(),
        os.urandom(8).hex(),
    )
    payload = build_full_matrix_suite_receipts(
        catalog,
        pre_rc_run_id=suite_run_id,
        verifier_runner=verifier_runner,
    )
    return {
        "stage": "pre-rc-receipts",
        "mode": "standalone-catalog-rehearsal",
        "ok": True,
        **payload,
    }


def format_pre_rc_rehearsal_ok(summary: Mapping[str, Any]) -> str:
    """渲染固定的全量成功信号；任何不完整或越责的摘要都拒绝渲染。

    信号格式固定为
    ``PRE_RC_REHEARSAL_OK reports=3 formats=1 hosts=3 ... release_cases_closed=0 ...``；
    仅当六阶段全部通过、首版格式严格为 html、三宿主真实冒烟已绑定、且没有任何
    未来责任被关闭时才允许输出。
    """

    if not isinstance(summary, Mapping) or summary.get("ok") is not True:
        raise AcceptanceRunnerError("成功信号被拒绝：流水线总结果未通过")
    stages = summary.get("stages")
    if not isinstance(stages, list) or len(stages) != len(PRE_RC_STAGE_ORDER) or any(
        not isinstance(stage, Mapping) for stage in stages
    ):
        raise AcceptanceRunnerError("成功信号被拒绝：流水线阶段记录不完整")
    if [stage.get("stage") for stage in stages] != list(PRE_RC_STAGE_ORDER):
        raise AcceptanceRunnerError("成功信号被拒绝：流水线阶段顺序与合同不一致")
    if any(stage.get("ok") is not True for stage in stages):
        raise AcceptanceRunnerError("成功信号被拒绝：存在未通过的阶段")
    if summary.get("reports") != ["A", "B", "C"]:
        raise AcceptanceRunnerError("成功信号被拒绝：报告集合不是 A/B/C")
    if summary.get("formats") != ["html"]:
        raise AcceptanceRunnerError(
            f"成功信号被拒绝：首版格式必须严格为 html，实际 {summary.get('formats')!r}；"
            "PDF、HTML-PPT、PPTX 属未来格式，不得计入首版信号"
        )
    receipts_stage = stages[-1]
    if receipts_stage.get("stage") != "pre-rc-receipts":
        raise AcceptanceRunnerError("成功信号被拒绝：缺少场景回执聚合阶段")
    receipts = receipts_stage.get("receipts")
    counts = receipts_stage.get("counts")
    if not isinstance(receipts, list) or not isinstance(counts, Mapping):
        raise AcceptanceRunnerError("成功信号被拒绝：场景回执聚合不完整")
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise AcceptanceRunnerError("成功信号被拒绝：场景回执记录无效")
        if receipt.get("status") not in _ALLOWED_RECEIPT_STATUSES:
            raise AcceptanceRunnerError(
                f"成功信号被拒绝：回执状态越出允许集合："
                f"{receipt.get('case_id')}={receipt.get('status')!r}"
            )
        if receipt.get("release_case_closed") is True:
            raise AcceptanceRunnerError(
                f"成功信号被拒绝：未来责任被误关闭：{receipt.get('case_id')}"
            )
    declared_closed = receipts_stage.get("release_cases_closed")
    closed_ids = receipts_stage.get("closed_case_ids")
    if declared_closed != 0 or closed_ids != []:
        raise AcceptanceRunnerError(
            "成功信号被拒绝：release_cases_closed 必须为 0——Task 10.6 最终 release "
            "case、恢复演练与切换授权不得由 pre-RC 预演关闭"
        )
    hosts = receipts_stage.get("hosts")
    if not isinstance(hosts, list) or sorted(hosts) != sorted(_PRE_RC_HOSTS):
        raise AcceptanceRunnerError(
            "成功信号被拒绝：缺少 codex/hermes/omp 三宿主真实冒烟绑定"
        )
    for key in (
        "catalog_cases_total",
        "suite_cases",
        "rehearsed",
        "pending_future_owner",
        "not_applicable",
        "outside_suite",
    ):
        if not isinstance(counts.get(key), int):
            raise AcceptanceRunnerError(f"成功信号被拒绝：回执计数缺少 {key}")
    pre_rc_run_id = summary.get("pre_rc_run_id")
    if not isinstance(pre_rc_run_id, str) or not pre_rc_run_id.strip():
        raise AcceptanceRunnerError("成功信号被拒绝：缺少 pre-RC 运行身份")
    return (
        f"PRE_RC_REHEARSAL_OK reports={len(summary['reports'])} "
        f"formats={len(summary['formats'])} hosts={len(hosts)} "
        f"cases={counts['catalog_cases_total']} rehearsed={counts['rehearsed']} "
        f"future_owner={counts['pending_future_owner']} "
        f"not_applicable={counts['not_applicable']} "
        f"outside_suite={counts['outside_suite']} release_cases_closed=0 "
        f"pre_rc_run_id={pre_rc_run_id}"
    )


__all__ = [
    "AcceptanceCaseInput",
    "AcceptanceCatalog",
    "AcceptanceExpectedFile",
    "AcceptanceRunnerError",
    "CurrentHtmlArtifact",
    "DEFAULT_CANDIDATE_INSTALL_ROOT",
    "DEFAULT_CATALOG_PATH",
    "EGO_LITE_TOOL_IDENTITY",
    "EGO_RECEIPT_FILENAME",
    "EgoReceiptPendingError",
    "NOT_APPLICABLE_STATUS",
    "PENDING_FUTURE_OWNER_STATUS",
    "PRESCRIBED_VIEWPORTS",
    "PRE_RC_STAGE_ORDER",
    "REHEARSAL_STATUS",
    "ResolvedAcceptanceCase",
    "RunBindingContract",
    "ScenarioVerifierOutcome",
    "bind_ego_receipts_pipeline",
    "build_full_matrix_suite_receipts",
    "build_host_smoke_stage",
    "build_pre_rc_receipts_stage",
    "build_project_verify_stage",
    "complete_pre_rc_rehearsal",
    "expected_ego_receipt_path",
    "format_pre_rc_rehearsal_ok",
    "load_acceptance_catalog",
    "require_empty_project_root",
    "resolve_acceptance_case",
    "resolve_full_matrix_suite",
    "run_catalog_input_stage",
    "run_ego_receipt_stage",
    "run_full_matrix_suite_rehearsal",
    "run_html_pipeline",
    "run_pre_rc_rehearsal",
    "run_project_stage",
    "subprocess_verifier_runner",
]
