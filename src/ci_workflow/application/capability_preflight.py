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
OutputName = Literal["html", "pdf", "html-ppt", "pptx"]
HostName = Literal["local", "codex", "hermes", "omp"]
CapabilityState = Literal["ready", "blocked", "not_applicable"]
MatrixState = Literal["ready", "partially_available", "blocked"]

CAPABILITY_IDS = (
    "project_file_io",
    "script_runtime",
    "http_network",
    "search_browser",
    "login_browser",
    "document_ingestion",
    "ocr",
    "browser_validation",
    "native_pdf",
    "html_ppt_runtime",
    "ppt_master",
    "office_renderer",
)

CAPABILITY_LABELS = {
    "project_file_io": "项目文件读写",
    "script_runtime": "本地脚本运行",
    "http_network": "公开网络访问",
    "search_browser": "网页检索浏览器",
    "login_browser": "登录资料浏览器",
    "document_ingestion": "PDF 与文档读取",
    "ocr": "扫描件文字识别",
    "browser_validation": "真实浏览器验收",
    "native_pdf": "原生 PDF 生成与检查",
    "html_ppt_runtime": "HTML 演示稿运行组件",
    "ppt_master": "可编辑 PPTX 生成组件",
    "office_renderer": "PowerPoint 或指定 Office 验收",
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
    "native_pdf": "请恢复原生 PDF 生成与阅读检查组件。",
    "html_ppt_runtime": "请恢复 HTML 演示稿运行组件后再生成该格式。",
    "ppt_master": "请安装或恢复 PPT Master，再继续生成可编辑 PPTX。",
    "office_renderer": "请安装或恢复 PowerPoint/指定 Office，再进行可编辑性和视觉检查。",
}


class CapabilityProbeFailure(RuntimeError):
    """已经完成适用的轻量重试，但能力仍不可用。"""


class CapabilitySelection(BaseModel):
    """最小用户输入推导出的能力适用范围。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reports: tuple[ReportName, ...] = Field(min_length=1)
    outputs: tuple[OutputName, ...] = Field(min_length=1)
    source_routes: tuple[
        Literal["public-http", "public-browser", "authenticated-browser"], ...
    ] = Field(min_length=1)
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

    def __init__(self) -> None:
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
        self.cache: dict[str, ProbeOutcome] = {}

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
        if capability_id in {"search_browser", "login_browser", "browser_validation"}:
            return "Chromium 无法启动或完成页面渲染"
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
        if capability_id in {"search_browser", "login_browser", "browser_validation"}:
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
                importlib.util.find_spec(module) is not None
                for module in ("pypdf", "pdfplumber")
            )
            return available, "PDF 与文档读取组件已发现"
        if capability_id == "ocr":
            gate = os.environ.get("CI_WORKFLOW_OCR_GATE")
            available = bool(gate and Path(gate).is_file()) or shutil.which("omlx") is not None
            return available, "扫描件文字识别入口已发现" if available else "未发现文字识别入口"
        if capability_id == "native_pdf":
            modules = importlib.util.find_spec("reportlab") is not None
            poppler = shutil.which("pdftoppm") or shutil.which("pdftocairo")
            return bool(modules and poppler), "原生 PDF 与页面渲染组件已发现"
        if capability_id == "html_ppt_runtime":
            package_root = Path(__file__).resolve().parents[3]
            manifest = package_root / "assets/html-ppt/manifest.json"
            return manifest.is_file(), "HTML 演示稿运行组件已发现"
        if capability_id == "ppt_master":
            configured = os.environ.get("CI_WORKFLOW_PPT_MASTER_PATH")
            candidates = (
                Path(configured) if configured else Path("/__not_configured__"),
                Path.home() / ".cc-switch/skills/ppt-master/SKILL.md",
                Path.home() / ".codex/skills/ppt-master/SKILL.md",
            )
            return any(path.is_file() for path in candidates), "PPT Master 已发现"
        if capability_id == "office_renderer":
            configured = os.environ.get("CI_WORKFLOW_OFFICE_COMMAND")
            available = bool(configured and shutil.which(configured)) or Path(
                "/Applications/Microsoft PowerPoint.app"
            ).exists()
            return available, "PowerPoint 或指定 Office 已发现"
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


class CapabilityMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    host: HostName
    selection: CapabilitySelection
    capabilities: tuple[CapabilityRecord, ...]
    research: tuple[ResearchReadiness, ...]
    deliveries: tuple[DeliveryReadiness, ...]
    overall_state: MatrixState
    user_messages: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _matrix_is_complete_and_internally_consistent(self) -> CapabilityMatrix:
        capability_ids = tuple(item.capability_id for item in self.capabilities)
        if capability_ids != CAPABILITY_IDS:
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
        states = [item.state for item in self.research] + [
            item.state for item in self.deliveries
        ]
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


class RecoveryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repaired_capability_ids: tuple[str, ...]
    requeue_node_ids: tuple[str, ...]


def _applicable_capabilities(selection: CapabilitySelection) -> set[str]:
    applicable = {"project_file_io", "script_runtime", "browser_validation"}
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
    if "pdf" in selection.outputs:
        applicable.add("native_pdf")
    if "html-ppt" in selection.outputs:
        applicable.add("html_ppt_runtime")
    if "pptx" in selection.outputs:
        applicable.update(("ppt_master", "office_renderer"))
    return applicable


def _research_dependencies(selection: CapabilitySelection) -> tuple[str, ...]:
    candidates = (
        "project_file_io",
        "script_runtime",
        "http_network",
        "search_browser",
        "login_browser",
        "document_ingestion",
        "ocr",
    )
    applicable = _applicable_capabilities(selection)
    return tuple(item for item in candidates if item in applicable)


def _delivery_dependencies(output: OutputName) -> tuple[str, ...]:
    if output == "html":
        return ("browser_validation",)
    if output == "pdf":
        return ("native_pdf",)
    if output == "html-ppt":
        return ("browser_validation", "html_ppt_runtime")
    return ("ppt_master", "office_renderer")


def _required_by(selection: CapabilitySelection) -> dict[str, tuple[str, ...]]:
    values: dict[str, list[str]] = {capability_id: [] for capability_id in CAPABILITY_IDS}
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
    if overall_state == "ready":
        return ("所选报告和交付格式所需能力均可用，可以开始调研。",)
    blocked = [record for record in records.values() if record.state == "blocked"]
    messages: list[str] = []
    ppt_blocked = [
        record
        for record in blocked
        if record.capability_id in {"ppt_master", "office_renderer"}
    ]
    if ppt_blocked:
        unaffected = [
            {"html": "HTML", "pdf": "PDF", "html-ppt": "HTML 演示稿"}[output]
            for output in selection.outputs
            if output != "pptx"
        ]
        reasons = "；".join(dict.fromkeys(item.detail.rstrip("。") for item in ppt_blocked))
        actions = "；".join(
            dict.fromkeys(item.user_action.rstrip("。") for item in ppt_blocked)
        )
        suffix = f"；{'、'.join(unaffected)} 不受影响。" if unaffected else "。"
        messages.append(f"可编辑 PPTX 暂时无法生成：{reasons}。{actions}{suffix}")
    for record in blocked:
        capability_id = record.capability_id
        if capability_id in {"project_file_io", "script_runtime"}:
            messages.append(
                f"{record.label}暂时不可用，所选报告尚不能启动。{record.user_action}"
            )
        elif capability_id in {"ppt_master", "office_renderer"}:
            continue
        else:
            messages.append(
                f"{record.label}暂时不可用：{record.detail.rstrip('。')}。"
                f"{record.user_action}"
            )
    return tuple(dict.fromkeys(messages))


def run_capability_preflight(
    selection: CapabilitySelection,
    *,
    host: HostName,
    probe: CapabilityProbe,
    project_root: Path,
) -> CapabilityMatrix:
    applicable = _applicable_capabilities(selection)
    required_by = _required_by(selection)
    records: dict[str, CapabilityRecord] = {}
    for capability_id in CAPABILITY_IDS:
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
    source_routes: tuple[
        Literal["public-http", "public-browser", "authenticated-browser"], ...
    ] = ("public-http", "public-browser"),
    needs_document_ingestion: bool = True,
    needs_ocr: bool = False,
) -> CapabilitySelection:
    contract = verify_project_workspace(project_root).contract
    return CapabilitySelection(
        reports=tuple(report.value for report in contract.reports),
        outputs=tuple(output.value for output in contract.outputs),
        source_routes=source_routes,
        needs_document_ingestion=needs_document_ingestion,
        needs_ocr=needs_ocr,
    )


def plan_environment_recovery(
    previous: CapabilityMatrix, current: CapabilityMatrix
) -> RecoveryPlan:
    if previous.host != current.host or previous.selection != current.selection:
        raise ValueError("环境恢复比较必须使用同一宿主和用户选择")
    repaired = tuple(
        capability_id
        for capability_id in CAPABILITY_IDS
        if previous.capability(capability_id).state == "blocked"
        and current.capability(capability_id).state == "ready"
    )
    nodes: list[str] = []
    for capability_id in repaired:
        for requirement in previous.capability(capability_id).required_by:
            parts = requirement.split(":")
            if parts[0] == "research":
                report = cast(ReportName, parts[1])
                current_research = next(
                    item for item in current.research if item.report == report
                )
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
                        nodes.extend(
                            (f"render:{report}:{output}", f"verify:{report}:{output}")
                        )
            else:
                _, raw_report, raw_output = parts
                delivery_report = cast(ReportName, raw_report)
                delivery_output = cast(OutputName, raw_output)
                current_delivery = next(
                    item
                    for item in current.deliveries
                    if item.report == delivery_report
                    and item.output == delivery_output
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
