from __future__ import annotations

import importlib.util
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Protocol, cast
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.application.project_service import verify_project_workspace

ReportName = Literal["A", "B", "C"]
OutputName = Literal["html"]
HostName = Literal["local", "codex", "hermes", "omp"]
CapabilityState = Literal["ready", "blocked", "not_applicable"]
MatrixState = Literal["ready", "partially_available", "blocked"]
CAPABILITY_MATRIX_RELATIVE_PATH = "capabilities/preflight.json"

V1_CAPABILITY_IDS = (
    "project_file_io",
    "script_runtime",
    "http_network",
    "search_browser",
    "login_browser",
    "document_ingestion",
    "ocr",
    "browser_validation",
    "independent_context",
)
CAPABILITY_IDS = V1_CAPABILITY_IDS

CAPABILITY_LABELS = {
    "project_file_io": "项目文件读写",
    "script_runtime": "本地脚本运行",
    "http_network": "公开网络访问",
    "search_browser": "网页检索浏览器",
    "login_browser": "登录资料浏览器",
    "document_ingestion": "PDF 与文档读取",
    "ocr": "扫描件文字识别",
    "browser_validation": "真实浏览器验收",
    "independent_context": "独立上下文审阅",
}

CAPABILITY_ACTIONS = {
    "project_file_io": "请确认项目目录仍可访问，并允许 Agent 在项目内保存文件。",
    "script_runtime": "请恢复当前 Agent 的本地脚本运行能力后重试。",
    "http_network": "请确认网络可用；Agent 会在恢复后只重试尚未完成的来源。",
    "search_browser": "请恢复浏览器能力；已完成的资料不会重新检索。",
    "login_browser": "请在浏览器中完成必要登录，随后让 Agent 继续。",
    "document_ingestion": "请恢复 PDF/文档读取组件，或把无法读取的原文交给 Agent。",
    "ocr": "请恢复扫描件文字识别能力；可正常读取的文本资料不受影响。",
    "browser_validation": "请恢复真实浏览器后再验收网页产物。",
    "independent_context": (
        "请启用宿主子Agent、独立会话或兼容执行器，并配置可执行的独立上下文探针；"
        "主 Agent 不能自证首份宇宙闭包。"
    ),
}


class CapabilityProbeFailure(RuntimeError):
    """已经完成适用的轻量重试，但能力仍不可用。"""


class CapabilityPersistenceError(RuntimeError):
    """能力矩阵不能在项目边界内安全保存或重新打开。"""


class CapabilitySelection(BaseModel):
    """最小用户输入推导出的能力适用范围。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reports: tuple[ReportName, ...] = Field(min_length=1)
    outputs: tuple[OutputName, ...] = Field(min_length=1)
    source_routes: tuple[Literal["public-http", "public-browser", "authenticated-browser"], ...] = (
        Field(min_length=1)
    )
    needs_document_ingestion: bool
    needs_ocr: bool

    @field_validator("reports", "outputs", "source_routes")
    @classmethod
    def _values_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("能力预检选择项不能重复")
        return values

    @model_validator(mode="after")
    def _html_and_ocr_dependencies_are_explicit(self) -> CapabilitySelection:
        if self.outputs[0] != "html" or "html" not in self.outputs:
            raise ValueError("站点式 HTML 必须是首个交付格式")
        if self.needs_ocr and not self.needs_document_ingestion:
            raise ValueError("扫描件文字识别必须建立在文档读取能力之上")
        return self


class ProbeOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    detail: str
    user_action: str

    @field_validator("detail", "user_action")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("能力诊断说明不能为空")
        return value


class IndependentContextProbeReceipt(BaseModel):
    """Receipt emitted by a separately executed host capability probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    available: bool
    mechanism: Literal["native_subagent", "independent_session", "compatible_executor"]
    producer_context: str
    reviewer_context: str
    invocation_id: str

    @field_validator("producer_context", "reviewer_context", "invocation_id")
    @classmethod
    def _nonblank(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("独立上下文探针回执字段不能为空")
        return value

    @model_validator(mode="after")
    def _contexts_are_independent(self) -> IndependentContextProbeReceipt:
        if self.available and self.producer_context == self.reviewer_context:
            raise ValueError("生产者与复核者上下文必须不同")
        return self


class CapabilityProbe(Protocol):
    def check(self, capability_id: str, *, project_root: Path) -> ProbeOutcome: ...


class StaticCapabilityProbe:
    """供合同和工作流测试使用的确定性能力探针。"""

    def __init__(self, *, blocked: tuple[str, ...] = ()) -> None:
        unknown = set(blocked) - set(CAPABILITY_IDS)
        if unknown:
            raise ValueError(f"未知能力：{sorted(unknown)}")
        self.blocked = frozenset(blocked)

    def check(self, capability_id: str, *, project_root: Path) -> ProbeOutcome:
        del project_root
        available = capability_id not in self.blocked
        return ProbeOutcome(
            available=available,
            detail="已确认可用" if available else f"未能使用{CAPABILITY_LABELS[capability_id]}",
            user_action="无需处理" if available else CAPABILITY_ACTIONS[capability_id],
        )


class RuntimeCapabilityProbe:
    """本地确定性执行器使用的轻量实机探针。"""

    def __init__(self, *, independent_context_probe: Path | None = None) -> None:
        raw = (
            os.environ.get("CI_WORKFLOW_CAPABILITY_OVERRIDES", "")
            if os.environ.get("CI_WORKFLOW_TEST_MODE") == "1"
            else ""
        )
        if raw:
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError("宿主能力声明不是有效 JSON") from error
            if not isinstance(value, dict) or any(
                key not in CAPABILITY_IDS or not isinstance(available, bool)
                for key, available in value.items()
            ):
                raise ValueError("宿主能力声明包含未知能力或非布尔结果")
            self.overrides = cast(dict[str, bool], value)
        else:
            self.overrides = {}
        configured_probe = independent_context_probe
        if configured_probe is None:
            raw_probe = os.environ.get("CI_WORKFLOW_INDEPENDENT_CONTEXT_PROBE", "").strip()
            configured_probe = Path(raw_probe) if raw_probe else None
        self.independent_context_probe = configured_probe
        self.cache: dict[str, ProbeOutcome] = {}

    def reset(self) -> None:
        """Discard observations from a previous preflight flight."""
        self.cache.clear()

    def check(self, capability_id: str, *, project_root: Path) -> ProbeOutcome:
        if capability_id in self.overrides:
            available = self.overrides[capability_id]
            return ProbeOutcome(
                available=available,
                detail="宿主已确认可用" if available else "宿主报告此能力不可用",
                user_action="无需处理" if available else CAPABILITY_ACTIONS[capability_id],
            )
        if capability_id in self.cache:
            return self.cache[capability_id]
        try:
            available, detail = self._check_real(capability_id, project_root=project_root)
        except Exception as error:  # noqa: BLE001 - typed user diagnostic boundary
            available, detail = False, self._failure_detail(capability_id, error)
        outcome = ProbeOutcome(
            available=available,
            detail=detail,
            user_action="无需处理" if available else CAPABILITY_ACTIONS[capability_id],
        )
        self.cache[capability_id] = outcome
        return outcome

    @staticmethod
    def _failure_detail(capability_id: str, error: Exception) -> str:
        if isinstance(error, CapabilityProbeFailure):
            return str(error)
        if capability_id == "http_network":
            if isinstance(error, TimeoutError):
                return "连接 ClinicalTrials.gov 超时"
            return "无法连接 ClinicalTrials.gov"
        if capability_id == "login_browser":
            return "宿主未提供可验证的已登录浏览器会话观察"
        if capability_id in {"search_browser", "browser_validation"}:
            return "Chromium 无法启动或完成页面渲染"
        if capability_id == "independent_context":
            return "宿主未声明独立上下文审阅者"
        if capability_id == "project_file_io":
            return "项目目录无法完成临时文件读写"
        if capability_id == "script_runtime":
            return "本地脚本无法正常启动"
        return f"{CAPABILITY_LABELS[capability_id]}检查未完成"

    def _check_real(self, capability_id: str, *, project_root: Path) -> tuple[bool, str]:
        if capability_id == "project_file_io":
            target = project_root / "state" if (project_root / "state").is_dir() else project_root
            target.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(prefix=".preflight-", dir=target)
            os.close(descriptor)
            Path(temporary_name).unlink()
            return True, "项目目录可以读写"
        if capability_id == "script_runtime":
            result = subprocess.run(
                [sys.executable, "-c", "print('ok')"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0 and result.stdout.strip() == "ok", "脚本运行检查完成"
        if capability_id == "http_network":
            request = Request(
                "https://clinicaltrials.gov/api/v2/studies?pageSize=1",
                headers={"User-Agent": "ci-workflow-preflight/0.1"},
            )
            last_error: Exception | None = None
            for attempt in range(1, 4):
                try:
                    with urlopen(
                        request, timeout=5, context=ssl.create_default_context()
                    ) as response:
                        return (
                            200 <= response.status < 400,
                            f"ClinicalTrials.gov 第 {attempt} 次检查返回 {response.status}",
                        )
                except (OSError, TimeoutError) as error:
                    last_error = error
                    if attempt < 3:
                        time.sleep(0.25 * (2 ** (attempt - 1)))
            raise CapabilityProbeFailure(
                "连续 3 次无法连接 ClinicalTrials.gov；已完成短间隔重试"
            ) from last_error
        if capability_id == "login_browser":
            return False, "宿主未提供可验证的已登录浏览器会话观察"
        if capability_id in {"search_browser", "browser_validation"}:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content("<!doctype html><title>能力检查</title><p>可用</p>")
                ready = page.title() == "能力检查" and page.locator("p").inner_text() == "可用"
                browser.close()
            return ready, "真实 Chromium 页面已完成渲染"
        if capability_id == "document_ingestion":
            available = all(
                importlib.util.find_spec(module) is not None for module in ("pypdf", "pdfplumber")
            )
            return available, "PDF 与文档读取组件已发现"
        if capability_id == "ocr":
            gate = os.environ.get("CI_WORKFLOW_OCR_GATE")
            available = bool(gate and Path(gate).is_file()) or shutil.which("omlx") is not None
            return available, "扫描件文字识别入口已发现" if available else "未发现文字识别入口"
        if capability_id == "independent_context":
            probe = self.independent_context_probe
            if probe is None:
                return False, "未配置可执行的独立上下文探针，静态声明不构成能力证据"
            path = probe.expanduser().resolve()
            if not path.is_file() or path.is_symlink() or not os.access(path, os.X_OK):
                return False, "独立上下文探针不是可执行的普通文件"
            completed = subprocess.run(
                [str(path)],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if completed.returncode != 0:
                return False, f"独立上下文探针执行失败（退出码 {completed.returncode}）"
            try:
                receipt = IndependentContextProbeReceipt.model_validate_json(completed.stdout)
            except ValueError as error:
                raise CapabilityProbeFailure("独立上下文探针未返回有效运行时回执") from error
            if not receipt.available:
                return False, f"独立上下文探针回执不可用（{receipt.invocation_id}）"
            return (
                True,
                f"独立上下文探针已执行：{receipt.mechanism}；回执 {receipt.invocation_id}",
            )
        raise ValueError(f"未知能力：{capability_id}")


class CapabilityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability_id: str
    label: str
    state: CapabilityState
    required_by: tuple[str, ...]
    detail: str
    user_action: str


class ResearchReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportName
    state: Literal["ready", "blocked"]
    blocked_by: tuple[str, ...]


class DeliveryReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportName
    output: OutputName
    state: Literal["ready", "blocked"]
    blocked_by: tuple[str, ...]


def _capability_ids_for_selection(selection: CapabilitySelection) -> tuple[str, ...]:
    del selection
    return CAPABILITY_IDS


class CapabilityMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    host: HostName
    selection: CapabilitySelection
    capabilities: tuple[CapabilityRecord, ...]
    research: tuple[ResearchReadiness, ...]
    deliveries: tuple[DeliveryReadiness, ...]
    overall_state: MatrixState
    user_messages: tuple[str, ...]

    @model_validator(mode="after")
    def _matrix_is_complete_and_internally_consistent(self) -> CapabilityMatrix:
        capability_ids = tuple(item.capability_id for item in self.capabilities)
        if capability_ids != _capability_ids_for_selection(self.selection):
            raise ValueError("能力矩阵必须按冻结清单完整且唯一")
        records = {item.capability_id: item for item in self.capabilities}
        if tuple(item.report for item in self.research) != self.selection.reports:
            raise ValueError("报告研究状态与用户选择不一致")
        expected_deliveries = tuple(
            (report, output)
            for report in self.selection.reports
            for output in self.selection.outputs
        )
        actual_deliveries = tuple((item.report, item.output) for item in self.deliveries)
        if actual_deliveries != expected_deliveries:
            raise ValueError("格式状态必须完整覆盖所选报告与格式")
        for item in self.research:
            has_blocker = bool(item.blocked_by)
            if (item.state == "blocked") != has_blocker:
                raise ValueError("阻断状态必须列出准确的依赖能力")
            if any(
                blocker not in records or records[blocker].state != "blocked"
                for blocker in item.blocked_by
            ):
                raise ValueError("阻断状态引用了未阻断或不存在的能力")
        for delivery_item in self.deliveries:
            has_blocker = bool(delivery_item.blocked_by)
            if (delivery_item.state == "blocked") != has_blocker:
                raise ValueError("阻断状态必须列出准确的依赖能力")
            if any(
                blocker not in records or records[blocker].state != "blocked"
                for blocker in delivery_item.blocked_by
            ):
                raise ValueError("阻断状态引用了未阻断或不存在的能力")
        states = [item.state for item in self.research] + [item.state for item in self.deliveries]
        expected_state: MatrixState
        if all(state == "ready" for state in states):
            expected_state = "ready"
        elif all(state == "blocked" for state in states):
            expected_state = "blocked"
        else:
            expected_state = "partially_available"
        if self.overall_state != expected_state:
            raise ValueError("能力矩阵总状态与各报告/格式状态不一致")
        return self

    def capability(self, capability_id: str) -> CapabilityRecord:
        for item in self.capabilities:
            if item.capability_id == capability_id:
                return item
        raise KeyError(capability_id)


def _capability_matrix_path(project_root: Path, *, create_directory: bool) -> Path:
    root = verify_project_workspace(project_root).project_root
    directory = root / "capabilities"
    if directory.is_symlink():
        raise CapabilityPersistenceError("能力回执目录不能是软链接")
    if directory.exists() and not directory.is_dir():
        raise CapabilityPersistenceError("能力回执目录必须是普通目录")
    if create_directory:
        directory.mkdir(parents=True, exist_ok=True)
    path = directory / "preflight.json"
    if path.is_symlink():
        raise CapabilityPersistenceError("能力回执文件不能是软链接")
    if path.exists() and not path.is_file():
        raise CapabilityPersistenceError("能力回执目标必须是普通文件")
    return path


def persist_capability_matrix(project_root: Path, matrix: CapabilityMatrix) -> Path:
    """原子保存当前能力回执；它是易变运行事实，不是第二状态库。"""
    path = _capability_matrix_path(project_root, create_directory=True)
    encoded = (
        json.dumps(
            matrix.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise CapabilityPersistenceError("能力回执目标在写入期间发生变化")
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return path


def load_persisted_capability_matrix(project_root: Path) -> CapabilityMatrix:
    """重新打开当前能力回执并执行完整类型校验。"""
    path = _capability_matrix_path(project_root, create_directory=False)
    if not path.is_file():
        raise CapabilityPersistenceError("能力回执尚未生成")
    try:
        return CapabilityMatrix.model_validate_json(path.read_bytes())
    except (OSError, ValueError) as error:
        raise CapabilityPersistenceError("能力回执损坏或不符合合同") from error


class RecoveryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repaired_capability_ids: tuple[str, ...]
    requeue_node_ids: tuple[str, ...]


def _applicable_capabilities(selection: CapabilitySelection) -> set[str]:
    applicable = {
        "project_file_io",
        "script_runtime",
        "browser_validation",
        "independent_context",
    }
    if "public-http" in selection.source_routes:
        applicable.add("http_network")
    if "public-browser" in selection.source_routes:
        applicable.add("search_browser")
    if "authenticated-browser" in selection.source_routes:
        applicable.add("login_browser")
    if selection.needs_document_ingestion:
        applicable.add("document_ingestion")
    if selection.needs_ocr:
        applicable.add("ocr")
    return applicable


def _research_dependencies(selection: CapabilitySelection) -> tuple[str, ...]:
    candidates = (
        "project_file_io",
        "script_runtime",
        "http_network",
        "search_browser",
        "document_ingestion",
        "ocr",
        "independent_context",
    )
    applicable = _applicable_capabilities(selection)
    return tuple(item for item in candidates if item in applicable)


def _delivery_dependencies(output: OutputName) -> tuple[str, ...]:
    if output != "html":
        raise ValueError("首版交付格式必须是 html")
    return ("browser_validation",)


def _required_by(selection: CapabilitySelection) -> dict[str, tuple[str, ...]]:
    values: dict[str, list[str]] = {
        capability_id: [] for capability_id in _capability_ids_for_selection(selection)
    }
    research_dependencies = _research_dependencies(selection)
    for report in selection.reports:
        for capability_id in research_dependencies:
            values[capability_id].append(f"research:{report}")
        for output in selection.outputs:
            for capability_id in ("project_file_io", "script_runtime"):
                values[capability_id].append(f"delivery:{report}:{output}")
            for capability_id in _delivery_dependencies(output):
                values[capability_id].append(f"delivery:{report}:{output}")
    return {key: tuple(dict.fromkeys(items)) for key, items in values.items()}


def _user_messages(
    selection: CapabilitySelection,
    records: Mapping[str, CapabilityRecord],
    overall_state: MatrixState,
) -> tuple[str, ...]:
    optional_login_blocked = (
        "authenticated-browser" in selection.source_routes
        and records["login_browser"].state == "blocked"
    )
    messages: list[str] = []
    if overall_state == "ready":
        messages.append("所选报告和 HTML 门户交付所需核心能力均可用，可以开始调研。")
    if optional_login_blocked:
        record = records["login_browser"]
        messages.append(
            "药智网可选路线暂不可用："
            f"{record.detail.rstrip('。')}。请在浏览器中自行登录后继续该辅助路线；"
            "其他适格来源与核心研究不受阻断。"
        )
    if overall_state == "ready":
        return tuple(messages)
    blocked = [record for record in records.values() if record.state == "blocked"]
    for record in blocked:
        if record.capability_id == "login_browser" and not record.required_by:
            continue
        if record.capability_id in {"project_file_io", "script_runtime"}:
            messages.append(f"{record.label}暂时不可用，所选报告尚不能启动。{record.user_action}")
        else:
            messages.append(
                f"{record.label}暂时不可用：{record.detail.rstrip('。')}。{record.user_action}"
            )
    return tuple(dict.fromkeys(messages))


def run_capability_preflight(
    selection: CapabilitySelection,
    *,
    host: HostName,
    probe: CapabilityProbe,
    project_root: Path,
) -> CapabilityMatrix:
    if isinstance(probe, RuntimeCapabilityProbe):
        probe.reset()
    applicable = _applicable_capabilities(selection)
    capability_ids = _capability_ids_for_selection(selection)
    required_by = _required_by(selection)
    records: dict[str, CapabilityRecord] = {}
    for capability_id in capability_ids:
        if capability_id not in applicable:
            records[capability_id] = CapabilityRecord(
                capability_id=capability_id,
                label=CAPABILITY_LABELS[capability_id],
                state="not_applicable",
                required_by=(),
                detail="本次选择不需要此能力",
                user_action="无需处理",
            )
            continue
        outcome = probe.check(capability_id, project_root=project_root)
        records[capability_id] = CapabilityRecord(
            capability_id=capability_id,
            label=CAPABILITY_LABELS[capability_id],
            state="ready" if outcome.available else "blocked",
            required_by=required_by[capability_id],
            detail=outcome.detail,
            user_action=outcome.user_action,
        )

    research_dependencies = _research_dependencies(selection)
    research: list[ResearchReadiness] = []
    research_blocked_by: dict[str, tuple[str, ...]] = {}
    for report in selection.reports:
        blocked_by = tuple(
            item for item in research_dependencies if records[item].state == "blocked"
        )
        research_blocked_by[report] = blocked_by
        research.append(
            ResearchReadiness(
                report=report,
                state="blocked" if blocked_by else "ready",
                blocked_by=blocked_by,
            )
        )

    deliveries: list[DeliveryReadiness] = []
    for report in selection.reports:
        for output in selection.outputs:
            dependencies = (
                *research_blocked_by[report],
                "project_file_io",
                "script_runtime",
                *_delivery_dependencies(output),
            )
            blocked_by = tuple(
                dict.fromkeys(item for item in dependencies if records[item].state == "blocked")
            )
            deliveries.append(
                DeliveryReadiness(
                    report=report,
                    output=output,
                    state="blocked" if blocked_by else "ready",
                    blocked_by=blocked_by,
                )
            )

    all_states = [item.state for item in research] + [item.state for item in deliveries]
    if all(state == "ready" for state in all_states):
        overall_state: MatrixState = "ready"
    elif all(state == "blocked" for state in all_states):
        overall_state = "blocked"
    else:
        overall_state = "partially_available"
    return CapabilityMatrix(
        schema_version="1.0",
        host=host,
        selection=selection,
        capabilities=tuple(records.values()),
        research=tuple(research),
        deliveries=tuple(deliveries),
        overall_state=overall_state,
        user_messages=_user_messages(selection, records, overall_state),
    )


def selection_from_project(
    project_root: Path,
    *,
    source_routes: tuple[Literal["public-http", "public-browser", "authenticated-browser"], ...] = (
        "public-http",
        "public-browser",
    ),
    needs_document_ingestion: bool = True,
    needs_ocr: bool = False,
) -> CapabilitySelection:
    contract = verify_project_workspace(project_root).contract
    from ci_workflow.application.yaozh_access import load_yaozh_access_record

    yaozh_record = load_yaozh_access_record(project_root)
    resolved_routes = source_routes
    if (
        yaozh_record is not None
        and yaozh_record.route_enabled
        and "authenticated-browser" not in resolved_routes
    ):
        resolved_routes = (*resolved_routes, "authenticated-browser")
    return CapabilitySelection(
        reports=tuple(report.value for report in contract.reports),
        outputs=tuple(output.value for output in contract.outputs),
        source_routes=resolved_routes,
        needs_document_ingestion=needs_document_ingestion,
        needs_ocr=needs_ocr,
    )


def plan_environment_recovery(
    previous: CapabilityMatrix, current: CapabilityMatrix
) -> RecoveryPlan:
    if previous.host != current.host or previous.selection != current.selection:
        raise ValueError("环境恢复比较必须使用同一宿主和用户选择")
    capability_ids = tuple(item.capability_id for item in previous.capabilities)
    repaired = tuple(
        capability_id
        for capability_id in capability_ids
        if previous.capability(capability_id).state == "blocked"
        and current.capability(capability_id).state == "ready"
    )
    nodes: list[str] = []
    for capability_id in repaired:
        for requirement in previous.capability(capability_id).required_by:
            parts = requirement.split(":")
            if parts[0] == "research":
                report = cast(ReportName, parts[1])
                current_research = next(item for item in current.research if item.report == report)
                if current_research.state != "ready":
                    continue
                nodes.extend(
                    (
                        f"research:{report}",
                        f"analyze:{report}",
                        f"snapshot:{report}",
                    )
                )
                for output in current.selection.outputs:
                    current_delivery = next(
                        item
                        for item in current.deliveries
                        if item.report == report and item.output == output
                    )
                    if current_delivery.state == "ready":
                        nodes.extend((f"render:{report}:{output}", f"verify:{report}:{output}"))
            else:
                _, raw_report, raw_output = parts
                delivery_report = cast(ReportName, raw_report)
                delivery_output = cast(OutputName, raw_output)
                current_delivery = next(
                    item
                    for item in current.deliveries
                    if item.report == delivery_report and item.output == delivery_output
                )
                if current_delivery.state == "ready":
                    nodes.extend(
                        (
                            f"render:{delivery_report}:{delivery_output}",
                            f"verify:{delivery_report}:{delivery_output}",
                        )
                    )
    return RecoveryPlan(
        repaired_capability_ids=repaired,
        requeue_node_ids=tuple(dict.fromkeys(nodes)),
    )
