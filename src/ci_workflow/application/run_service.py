"""Task 3.6 项目运行与 fixture 运行共用的真实执行器服务。

RunService 从已保存项目合同启动真实类型化图执行器，持久化新运行身份、
事件/检查点和当前运行清单；清单与追加式事件流互相绑定
（``run.manifest.recorded`` 事件）。FixtureRunner 验证目录和用例输入后
创建隔离项目并调用同一 RunService。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from ci_workflow.application.capability_preflight import (
    CapabilityMatrix,
    CapabilityProbe,
    HostName,
)
from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    verify_project_workspace,
)
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.recovery import DeliveryContract, PartialDeliveryCoordinator
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.storage.event_store import (
    EventStore,
    StoredWorkflowEvent,
    WorkflowEvent,
)
from ci_workflow.storage.paths import ArtifactPathService, ArtifactPathViolation


class RunError(RuntimeError):
    """运行级错误。"""


class ContractConfigError(RunError):
    """合同/配置/数据级失败（exit 2）。"""


class RendererUnavailableError(RunError):
    """渲染器不可用（exit 3）。"""


class EvidenceBlockedError(RunError):
    """证据不足阻断完成（exit 4）。"""


# ─── Types ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RunOutputFile:
    """当前运行清单中的单个产出文件。"""

    relative_path: str
    sha256: str
    byte_size: int
    mtime_ns: int
    modified_at: datetime
    media_type: str


@dataclass(frozen=True)
class RunResult:
    """RunService 返回值。"""

    run_id: str
    project_id: str
    contract_version: int
    outcome: Literal[
        "completed",
        "running",
        "awaiting_user",
        "recovery_required",
        "evidence_blocked",
        "capability_blocked",
        "renderer_unavailable",
        "failed",
    ]
    exit_code: int
    node_summary: dict[str, str]
    reused: tuple[dict[str, str], ...]
    outputs: tuple[RunOutputFile, ...]
    case_id: str | None = None
    case_digest: str | None = None
    input_hashes: dict[str, str] = field(default_factory=dict)


@dataclass
class RunContext:
    """运行上下文：项目根、合同、输入路径。"""

    project_root: Path
    contract: Any
    universe_input_path: Path | None = None
    report_data_path: Path | None = None
    report_data_paths: dict[str, Path] = field(default_factory=dict)
    research_package_path: Path | None = None
    research_lineage: Any = None
    research_projection: Any = None
    universe_evidence: Any = None
    run_inputs: dict[str, str] = field(default_factory=dict)
    runtime_metadata: dict[str, Any] = field(default_factory=dict)
    capability_probe: CapabilityProbe | None = None
    capability_host: HostName = "local"
    capability_matrix: CapabilityMatrix | None = None
    recover_committed_render: bool = False
    indication: str = field(init=False)
    reports: tuple[str, ...] = field(init=False)
    data_cutoff: datetime = field(init=False)
    source_input_paths: dict[str, Path] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.project_root = self.project_root.expanduser().resolve()
        self.indication = str(self.contract.indication)
        self.reports = tuple(report.value for report in self.contract.reports)
        self.data_cutoff = self.contract.data_cutoff
        for name, path in (
            ("universe", self.universe_input_path),
            ("report-data", self.report_data_path),
            ("research-package", self.research_package_path),
        ):
            if path is not None:
                self.bind_source_input(name, path)
        for report, path in self.report_data_paths.items():
            self.bind_source_input(f"report-data:{report}", path)

    def bind_source_input(self, name: str, path: Path | None) -> None:
        if path is None:
            self.source_input_paths.pop(name, None)
            return
        resolved = path.expanduser().resolve()
        if not resolved.is_relative_to(self.project_root):
            raise ContractConfigError("运行输入必须位于显式项目根内")
        self.source_input_paths[name] = resolved


# ─── Constants ─────────────────────────────────────────────────────────────


MANIFEST_RELATIVE_PATH = "manifests/current_run.json"
MANIFEST_RECORDED_EVENT = "run.manifest.recorded"
NODE_REUSED_EVENT = "run.node.reused"
TERMINAL_DECISION_EVENT = "run.terminal_decision.recorded"
CANONICAL_UNIVERSE_RELATIVE_PATH = "evidence/library/universe.json"
CANONICAL_REPORT_DATA_RELATIVE_PATH = "evidence/library/report-data.json"
CANONICAL_A_RESEARCH_PACKAGE_RELATIVE_PATH = "evidence/library/a-research-package.json"
CANONICAL_B_RESEARCH_PACKAGE_RELATIVE_PATH = "evidence/library/b-research-package.json"
CANONICAL_C_RESEARCH_PACKAGE_RELATIVE_PATH = "evidence/library/c-research-package.json"
CANONICAL_RESEARCH_PACKAGE_PATHS = {
    "A": CANONICAL_A_RESEARCH_PACKAGE_RELATIVE_PATH,
    "B": CANONICAL_B_RESEARCH_PACKAGE_RELATIVE_PATH,
    "C": CANONICAL_C_RESEARCH_PACKAGE_RELATIVE_PATH,
}

_VERSION_PATTERN = re.compile(
    r"^v(?:[0-9]+(?:\.[0-9]+){0,2}(?:-[a-z0-9][a-z0-9.-]*)?|-fixture-[a-z0-9][a-z0-9.-]*)$"
)
_ARTIFACT_PATH_SERVICE = ArtifactPathService()


# ─── Helpers ──────────────────────────────────────────────────────────────


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def compute_event_stream_digest(events: tuple[StoredWorkflowEvent, ...]) -> str:
    """按事件流顺序对事件摘要列表求确定性摘要。"""
    return _sha256_bytes(_canonical_json([event.event_digest for event in events]))


def compute_input_hashes_digest(input_hashes: dict[str, str]) -> str:
    """确定性摘要：排序后的输入路径→SHA-256 映射。"""
    return _sha256_bytes(_canonical_json({key: input_hashes[key] for key in sorted(input_hashes)}))


def _new_run_id(project_id: str) -> str:
    return stable_id(
        "run",
        project_id,
        datetime.now(UTC).isoformat(),
        os.urandom(8).hex(),
    )


def _node_key(node_id: str, report_kind: str | None) -> str:
    return f"{node_id}:{report_kind}" if report_kind else node_id


def _derive_completed_nodes(
    events: tuple[StoredWorkflowEvent, ...],
) -> dict[str, dict[str, dict[str, Any]]]:
    """从全部事件流派生已完成节点集合。

    key = node_key → input_digest → completion payload + run_id。同一节点在
    多报告联合执行中会按报告研究包得到不同输入摘要，按摘要索引保证每个
    报告只复用自己的完成记录。
    """
    completed: dict[str, dict[str, dict[str, Any]]] = {}
    for event in events:
        if event.event_type == "graph.node.completed":
            p = event.payload
            key = _node_key(str(p["node_id"]), p.get("report_kind"))
            completed.setdefault(key, {})[str(p["input_digest"])] = {
                "outputs": dict(p["outputs"]),
                "input_digest": str(p["input_digest"]),
                "completion_digest": str(p["completion_digest"]),
                "run_id": event.run_id,
                "event_id": event.event_id,
            }
    return completed


def _had_universe_attempt(events: tuple[StoredWorkflowEvent, ...]) -> bool:
    """事件流中是否已尝试过 universe 节点（完成或失败）。"""
    return any(
        event.payload.get("node_id") == "universe"
        for event in events
        if event.event_type in ("graph.node.completed", "run.node.failed")
    )


def _last_completed_node(
    events: tuple[StoredWorkflowEvent, ...],
    node_id: str,
    report_kind: str | None,
) -> dict[str, Any] | None:
    """事件流中最后一个节点完成载荷（含 input_digest）。"""
    for event in reversed(events):
        if (
            event.event_type == "graph.node.completed"
            and event.payload.get("node_id") == node_id
            and event.payload.get("report_kind") == report_kind
        ):
            return event.payload
    return None


def _last_evidence_blocked_transition(
    events: tuple[StoredWorkflowEvent, ...],
    report_object_id: str,
) -> StoredWorkflowEvent | None:
    """事件流中报告对象最后一次进入证据阻断的迁移事件。"""
    for event in reversed(events):
        if (
            event.event_type == "graph.transition.accepted"
            and event.payload.get("family") == "report_evidence"
            and event.payload.get("object_id") == report_object_id
            and event.payload.get("to_state") == "evidence_blocked"
        ):
            return event
    return None


def _last_terminal_decision_event(
    events: tuple[StoredWorkflowEvent, ...],
    report_object_id: str,
) -> StoredWorkflowEvent | None:
    """事件流中报告对象最后一次终态决策记录事件（产物引用的权威绑定）。"""
    for event in reversed(events):
        if (
            event.event_type == TERMINAL_DECISION_EVENT
            and event.payload.get("report_object_id") == report_object_id
        ):
            return event
    return None


def _derive_full_family_state(
    events: tuple[StoredWorkflowEvent, ...],
    family: str,
) -> dict[str, str]:
    """从全部事件流机械推导指定族的最后状态（last-wins per object）。"""
    state: dict[str, str] = {}
    for event in events:
        if (
            event.event_type == "graph.transition.accepted"
            and event.payload.get("family") == family
        ):
            object_id = str(event.payload["object_id"])
            to_state = str(event.payload["to_state"])
            state[object_id] = to_state
    return state


def _merge_report_metadata(target: dict[str, Any], update: dict[str, Any]) -> None:
    """按报告键合并运行元数据：同键下的报告字典逐报告累积，不互相覆盖。"""
    for key, value in update.items():
        existing = target.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            target[key] = {**existing, **value}
        else:
            target[key] = value


def _aggregate_multi_report_outcome(per_report: dict[str, str]) -> str:
    """多报告联合产品的诚实聚合。

    技术失败 > 任一报告等待恢复（仍有可推进工作，不得宣称终态）> 任一报告
    证据不足阻断（无可恢复工作剩余）> 全部报告完成渲染。
    """
    values = tuple(per_report.values())
    if "failed" in values:
        return "failed"
    if "awaiting_user" in values:
        return "awaiting_user"
    if "recovery_required" in values:
        return "recovery_required"
    if "running" in values:
        return "running"
    if "capability_blocked" in values:
        return "capability_blocked"
    if "evidence_blocked" in values:
        return "evidence_blocked"
    return "completed"


# ─── Universe evidence binding ─────────────────────────────────────────────


def _hydrate_universe_evidence(ctx: RunContext) -> None:
    """从已绑定输入确定性重建宇宙证据（解析+类型化校验+项目身份绑定）。"""
    from ci_workflow.gates.blocker_audit import EmptyUniverseEvidence

    if ctx.universe_input_path is None or not ctx.universe_input_path.is_file():
        raise ContractConfigError(f"宇宙证据文件不存在：{ctx.universe_input_path}")
    try:
        raw = json.loads(ctx.universe_input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractConfigError(f"宇宙证据文件不是有效 JSON：{ctx.universe_input_path}") from exc
    if not isinstance(raw, dict):
        raise ContractConfigError(f"宇宙证据文件顶层必须是对象：{ctx.universe_input_path}")
    actual_project_id = ctx.contract.project_id
    raw["project_id"] = actual_project_id
    if "exhaustion" in raw and isinstance(raw["exhaustion"], dict):
        raw["exhaustion"]["project_id"] = actual_project_id
    try:
        evidence = EmptyUniverseEvidence.model_validate(raw)
    except ValueError as exc:
        raise ContractConfigError(
            f"宇宙证据文件不符合类型化合同：{ctx.universe_input_path}（{exc}）"
        ) from exc
    ctx.universe_evidence = evidence


def _check_resume_terminal(
    events: tuple[StoredWorkflowEvent, ...],
    contract: Any,
    ctx: RunContext,
    project_root: Path,
    research_package_paths: dict[str, Path] | None = None,
) -> None:
    """恢复前的终态校验：终态阻断项目必须绑定未变化的宇宙证据与阻断说明，
    否则失败关闭。

    证据内容或阻断说明文件已变化时不得用 --resume 重提终态迁移，必须走
    显式重新打开流程。阻断说明只与决策记录绑定，运行前基线中的修改不能
    成为新的可复用事实。
    """
    report_states = _derive_full_family_state(events, "report_evidence")
    terminal_kinds = [
        kind.value
        for kind in contract.reports
        if report_states.get(f"report_{kind.value}") == "evidence_blocked"
    ]
    if ctx.universe_input_path is None and ctx.research_package_path is None:
        if terminal_kinds:
            raise ContractConfigError(
                "项目处于证据不足阻断状态，且项目内没有宇宙证据文件"
                f"（{CANONICAL_UNIVERSE_RELATIVE_PATH}）。"
                "请恢复该文件后重新 --resume，或使用显式的项目重新打开流程。"
            )
        if _had_universe_attempt(events) and ctx.research_package_path is None:
            raise ContractConfigError(
                "上次运行因缺少宇宙证据而中断，且项目内仍没有宇宙证据文件。"
                f"请将证据文件放入 {CANONICAL_UNIVERSE_RELATIVE_PATH} 后重新 --resume。"
            )
        return
    for kind_value in terminal_kinds:
        package_path = (
            research_package_paths.get(kind_value)
            if research_package_paths is not None
            else ctx.research_package_path
        )
        if ctx.universe_evidence is not None:
            evidence_digest = ctx.universe_evidence.evidence_digest
        elif package_path is not None and package_path.is_file():
            evidence_digest = _research_package_content_digest(package_path, kind_value)
        else:
            raise ContractConfigError(
                f"报告 {kind_value} 的证据不足结论缺少当前研究包，无法安全恢复。"
            )
        gate_digest = _compute_input_digest(
            "gate",
            kind_value,
            contract.contract_version,
            extra=evidence_digest,
        )
        last_gate = _last_completed_node(events, "gate", kind_value)
        if last_gate is None or str(last_gate["input_digest"]) != gate_digest:
            raise ContractConfigError(
                "宇宙证据内容已变化，既有的「证据不足」结论不再适用。"
                "请勿用 --resume 直接重跑；"
                "请使用显式的项目重新打开流程重新核对证据。"
            )
        # 阻断说明必须与决策记录绑定的产物元组一致（路径/SHA/字节/mtime）
        object_id = f"report_{kind_value}"
        terminal_event = _last_terminal_decision_event(events, object_id)
        if terminal_event is None:
            raise ContractConfigError(
                f"找不到报告 {kind_value} 的阻断决策记录，无法校验阻断说明。"
                "请恢复原始阻断说明文件后重试 --resume，"
                "或使用显式的项目重新打开流程。"
            )
        for artifact in terminal_event.payload.get("artifacts") or []:
            rel = str(artifact["relative_path"])
            absolute = project_root / rel
            if not absolute.is_file():
                raise ContractConfigError(
                    f"阻断说明文件缺失：{rel}。请恢复原始文件后重试 --resume，"
                    "或使用显式的项目重新打开流程。"
                )
            stat = absolute.stat()
            if (
                _sha256_file(absolute) != artifact["sha256"]
                or stat.st_size != artifact["byte_size"]
                or stat.st_mtime_ns != artifact["mtime_ns"]
            ):
                raise ContractConfigError(
                    f"阻断说明文件与决策记录不一致（可能已被修改）：{rel}。"
                    "请恢复原始文件后重试 --resume，"
                    "或使用显式的项目重新打开流程。"
                )


def _research_package_content_digest(path: Path, report_kind: str) -> str:
    """Load one specialized package and return the digest used by its gate node."""
    try:
        if report_kind == "A":
            from ci_workflow.application.source_research_service import (
                load_fresh_a_research_package,
            )

            return str(load_fresh_a_research_package(path).research_content_digest)
        if report_kind == "B":
            from ci_workflow.application.fresh_b_research_package import (
                load_fresh_b_research_package,
            )

            return str(load_fresh_b_research_package(path).research_content_digest)
        if report_kind == "C":
            from ci_workflow.application.fresh_c_research_package import (
                load_fresh_c_research_package,
            )

            return str(load_fresh_c_research_package(path).research_content_digest)
    except ValueError as error:
        raise ContractConfigError(f"报告 {report_kind} 的研究包已失效，拒绝恢复。") from error
    raise ContractConfigError(f"未知报告类型：{report_kind}")


# ─── Node handlers ────────────────────────────────────────────────────────


def _handler_intake(ctx: RunContext) -> dict[str, Any]:
    return {"project_contract_id": ctx.contract.project_id}


def _handler_preflight(ctx: RunContext) -> dict[str, Any]:
    from ci_workflow.application.capability_preflight import (
        RuntimeCapabilityProbe,
        persist_capability_matrix,
        run_capability_preflight,
        selection_from_project,
    )

    selection = selection_from_project(
        ctx.project_root,
        needs_document_ingestion=True,
        needs_ocr=False,
    )
    matrix = run_capability_preflight(
        selection,
        host=ctx.capability_host,
        probe=ctx.capability_probe or RuntimeCapabilityProbe(),
        project_root=ctx.project_root,
    )
    receipt_path = persist_capability_matrix(ctx.project_root, matrix)
    ctx.capability_matrix = matrix
    matrix_digest = _sha256_bytes(_canonical_json(matrix.model_dump(mode="json")))
    ctx.runtime_metadata["capability_preflight"] = {
        "matrix_id": stable_id("capability-matrix", ctx.contract.project_id, matrix_digest),
        "matrix_sha256": matrix_digest,
        "receipt_relative_path": receipt_path.relative_to(ctx.project_root).as_posix(),
        "overall_state": matrix.overall_state,
    }
    return {"capability_matrix_id": ctx.runtime_metadata["capability_preflight"]["matrix_id"]}


def _handler_universe(ctx: RunContext) -> dict[str, Any]:
    """Universe handler: 无输入路径时证据管线待定（非失败），有路径但不存在时失败。"""
    if ctx.universe_input_path is None:
        raise RunError("universe 输入待定，证据管线尚未启用")
    if not ctx.universe_input_path.is_file():
        raise ContractConfigError(f"universe 输入文件不存在：{ctx.universe_input_path}")
    # 永远从当前文件字节重新水合：不得信任缓存的 ctx.universe_evidence
    _hydrate_universe_evidence(ctx)
    evidence = ctx.universe_evidence
    return {
        "universe_receipt_id": stable_id(
            "universe-receipt",
            evidence.evidence_id,
            evidence.evidence_digest,
        )
    }


def _handler_gate_a(ctx: RunContext) -> dict[str, Any]:
    evidence = ctx.universe_evidence
    if evidence is None:
        raise RunError("A gate 需要 universe evidence")
    from ci_workflow.gates.blocker_audit import classify_empty_universe

    kind = classify_empty_universe(ReportKind.A, eligible_product_ids=evidence.eligible_product_ids)
    if kind is None:
        raise ContractConfigError("非空宇宙路径尚未实现")
    return {
        "gate_passed": False,
        "failures": (),
        "evidence_digest": evidence.evidence_digest,
    }


def _handler_recovery_a(ctx: RunContext) -> dict[str, Any]:
    evidence = ctx.universe_evidence
    if evidence is None:
        raise RunError("A recovery 需要 universe evidence")
    return {"recovery_receipt": evidence.exhaustion.record_digest}


# ─── Shared dispatch sequence ─────────────────────────────────────────────


_SHARED_NODES: list[tuple[str, None, Any]] = [
    ("intake", None, _handler_intake),
    ("preflight", None, _handler_preflight),
]


def _compute_input_digest(
    node_id: str,
    report_kind: str | None,
    contract_version: int,
    extra: str = "",
) -> str:
    """节点输入摘要：确定性、跨运行稳定。"""
    return _sha256_bytes(
        _canonical_json(
            {
                "node_id": node_id,
                "report_kind": report_kind,
                "contract_version": contract_version,
                "extra": extra,
            }
        )
    )


def _universe_input_digest(contract: Any, path: Path) -> str:
    """universe 输入摘要：包含内容哈希，新创建或变更的内容不能复用旧输出。"""
    extra = f"{path}:{_sha256_file(path)}" if path.is_file() else str(path)
    return _compute_input_digest("universe", None, contract.contract_version, extra=extra)


def _write_source_research_work_item(project_root: Path, contract: Any) -> Path:
    """无研究输入时留下可恢复的宿主任务，不用含糊的 skipped 代替下一步。"""
    from ci_workflow.application.autonomous_research import (
        AutonomousResearchTask,
        build_autonomous_research_task,
        load_default_source_policy,
    )
    from ci_workflow.application.yaozh_access import load_yaozh_access_record

    package_root = Path(__file__).resolve().parents[3]
    task = build_autonomous_research_task(
        contract,
        source_policy=load_default_source_policy(package_root),
        yaozh_record=load_yaozh_access_record(project_root),
    )
    path = project_root / "state/work-items/source-research.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json(task.model_dump(mode="json"))
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise ContractConfigError("待办研究任务必须是普通文件")
        existing_bytes = path.read_bytes()
        if existing_bytes == encoded:
            return path
        try:
            existing = AutonomousResearchTask.model_validate_json(existing_bytes)
        except ValueError as error:
            raise ContractConfigError("待办研究任务已损坏，拒绝覆盖") from error
        if (
            existing.project_id != contract.project_id
            or existing.contract_version != contract.contract_version
        ):
            raise ContractConfigError("待办研究任务与当前项目合同不一致")
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return path


def _write_gate_recovery_work_item(
    project_root: Path,
    contract: Any,
    report_kind: str,
    package: Any,
    gate_result: Any,
) -> Path:
    """Persist a resumable task instead of misclassifying unexhausted gaps."""
    work_item = {
        "schema_version": "1.0",
        "work_item_id": stable_id(
            "gate-recovery-work-item",
            contract.project_id,
            report_kind,
            package.research_content_digest,
            gate_result.result_key,
        ),
        "project_id": contract.project_id,
        "contract_version": contract.contract_version,
        "report_kind": report_kind,
        "report_version": package.report_version,
        "data_cutoff": package.data_cutoff.isoformat(),
        "evidence_snapshot_id": gate_result.evidence_snapshot_id,
        "gate_result_key": gate_result.result_key,
        "blocked_unit_ids": list(gate_result.blocked_unit_ids),
        "state": "等待两轮差异化恢复检索与独立遗漏复核",
        "next_action": (
            "由宿主针对每个阻断单元执行两轮不同策略的恢复检索，保存路线回执，"
            "再由独立上下文复核遗漏；未形成双重穷尽记录前不得发布证据不足页。"
        ),
    }
    path = project_root / f"state/work-items/{report_kind.lower()}-evidence-recovery.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json(work_item)
    if path.is_file() and path.read_bytes() != encoded:
        raise ContractConfigError("恢复检索任务与当前证据快照不一致")
    path.write_bytes(encoded)
    return path


# ─── Renderer registry ─────────────────────────────────────────────────────


def _publication_limitation(ctx: RunContext, report_kind: str) -> str | None:
    reports = ctx.runtime_metadata.get("publication_limitation_reports", ())
    if report_kind not in reports:
        return None
    value = ctx.runtime_metadata.get("publication_limitation_zh")
    return value if isinstance(value, str) and value.strip() else None


def _render_html_a(ctx: RunContext, run_id: str) -> tuple[str, str]:
    """当前唯一生产 HTML 渲染适配：A 类已校验报告数据包。"""
    if ctx.report_data_path is None:
        raise ContractConfigError("A 类 HTML 渲染缺少报告数据包")
    from ci_workflow.renderers.portal.report_a import (
        ReportALineageBinding,
        build_report_a_artifact,
    )

    binding = None
    public_provenance = None
    if ctx.research_lineage is not None:
        from ci_workflow.application.source_research_service import (
            load_fresh_a_research_package,
            project_a_public_provenance,
        )

        if ctx.research_package_path is None:
            raise ContractConfigError("A 类公共来源缺少已绑定研究包")
        lineage = ctx.research_lineage
        public_provenance = project_a_public_provenance(
            load_fresh_a_research_package(ctx.research_package_path), lineage
        )
        binding = ReportALineageBinding(
            evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
            claim_snapshot_id=lineage.claim_snapshot_id,
            coverage_set_id=lineage.coverage_set_id,
            coverage_projection_id=lineage.coverage_projection_id,
            claim_ids=lineage.claim_ids,
            source_version_ids=lineage.source_version_ids,
        )

    site_root, manifest_path = build_report_a_artifact(
        project_root=ctx.project_root,
        data_path=ctx.report_data_path,
        project_id=ctx.contract.project_id,
        contract_version=ctx.contract.contract_version,
        run_id=run_id,
        lineage=binding,
        public_provenance=public_provenance,
        publication_limitation_zh=_publication_limitation(ctx, "A"),
        recover_committed=ctx.recover_committed_render,
    )
    return (
        site_root.relative_to(ctx.project_root).as_posix(),
        manifest_path.relative_to(ctx.project_root).as_posix(),
    )


def _render_html_b(ctx: RunContext, run_id: str) -> tuple[str, str, str]:
    """B 类站点渲染、报告快照与产物清单适配。"""
    if ctx.report_data_path is None:
        raise ContractConfigError("B 类 HTML 渲染缺少报告数据包")
    from ci_workflow.application.semantic_review_task import (
        load_semantic_adjudications_for_render,
    )
    from ci_workflow.renderers.portal.report_b import build_report_b_artifact

    project_adjudications = load_semantic_adjudications_for_render(
        ctx.project_root,
        report="B",
        data_path=ctx.report_data_path,
        project_id=ctx.contract.project_id,
    )
    site_root, manifest_path, snapshot_id = build_report_b_artifact(
        project_root=ctx.project_root,
        data_path=ctx.report_data_path,
        project_id=ctx.contract.project_id,
        contract_version=ctx.contract.contract_version,
        run_id=run_id,
        publication_limitation_zh=_publication_limitation(ctx, "B"),
        extra_adjudications=project_adjudications,
    )
    return (
        site_root.relative_to(ctx.project_root).as_posix(),
        manifest_path.relative_to(ctx.project_root).as_posix(),
        snapshot_id,
    )


def _render_html_c_minimal(ctx: RunContext, run_id: str, data_path: Path) -> tuple[str, str]:
    """C 类站点最小产物写入：供 three-report-complete 多报告路径使用。

    通过共享未发布渲染事务写入：中断残留可恢复；已绑定产物拒绝覆盖。
    """
    from datetime import UTC

    from ci_workflow.domain.enums import ReportKind
    from ci_workflow.domain.ids import stable_id
    from ci_workflow.qc.browser import site_directory_digest
    from ci_workflow.renderers.portal.report_a import _git_commit
    from ci_workflow.renderers.portal.report_c import (
        load_report_c_data,
        render_report_c_site,
    )
    from ci_workflow.reports.common.page_registry import PageRegistry
    from ci_workflow.storage.manifest_store import (
        ArtifactFileBinding,
        ArtifactManifest,
        DesignContractBinding,
        DeterministicCheck,
        RendererBinding,
        RenderVerdict,
    )
    from ci_workflow.storage.render_transaction import (
        RenderTransactionError,
        UnpublishedRenderTransaction,
    )
    from ci_workflow.storage.snapshot_store import (
        LockedSnapshot,
        ReportSnapshotManifest,
        SnapshotIntegrityError,
        SnapshotStore,
        compute_locked_snapshot,
    )

    data = load_report_c_data(data_path)
    started_at = datetime.now(UTC)
    transaction = UnpublishedRenderTransaction(
        ctx.project_root,
        report="C",
        report_version=data.report_version,
        run_id=run_id,
    )
    try:
        staging_root = transaction.begin()
    except RenderTransactionError as error:
        raise ContractConfigError(str(error)) from error
    render_report_c_site(
        data,
        staging_root,
        publication_limitation_zh=_publication_limitation(ctx, "C"),
    )
    data_digest = hashlib.sha256(_canonical_json(data.model_dump(mode="json"))).hexdigest()
    claim_ids = tuple(
        stable_id("claim", observation.observation_id) for observation in data.observations
    )
    if not claim_ids:
        raise ContractConfigError("C 类报告没有可锁定的观察事实")
    evidence_snapshot_id = stable_id("evidence-snapshot", ctx.contract.project_id, data_digest)
    claim_snapshot_id = stable_id("claim-snapshot", ctx.contract.project_id, data_digest)
    coverage_set_id = stable_id("coverage-set", ctx.contract.project_id, "C", data_digest)
    coverage_projection_id = stable_id(
        "coverage-projection", ctx.contract.project_id, "C", data.report_version
    )
    declared_snapshot: ReportSnapshotManifest | None = None
    locked: LockedSnapshot | None = None
    if data.report_snapshot_id is not None:
        snapshot_file = (
            ctx.project_root / "snapshots" / "reports" / "C" / f"{data.report_snapshot_id}.json"
        )
        if snapshot_file.is_file():
            try:
                declared_snapshot = ReportSnapshotManifest.model_validate_json(
                    snapshot_file.read_bytes()
                )
                locked = compute_locked_snapshot(
                    kind="report",
                    report="C",
                    manifest=declared_snapshot.model_dump(mode="json"),
                )
            except (OSError, ValueError, SnapshotIntegrityError) as error:
                raise ContractConfigError("C 类门户引用的报告快照存在但不可信") from error
            if (
                locked.snapshot_id != data.report_snapshot_id
                or declared_snapshot.project_id != ctx.contract.project_id
                or declared_snapshot.contract_version != ctx.contract.contract_version
                or declared_snapshot.report_version != data.report_version
                or declared_snapshot.data_cutoff != data.data_cutoff
            ):
                raise ContractConfigError("C 类门户与已锁定报告快照身份不一致")
            evidence_snapshot_id = declared_snapshot.evidence_snapshot_id
            claim_snapshot_id = declared_snapshot.claim_snapshot_id
            coverage_set_id = declared_snapshot.coverage_set_id
            claim_ids = declared_snapshot.claim_ids
    if declared_snapshot is None or locked is None:
        snapshot_payload = ReportSnapshotManifest(
            schema_version="1.0",
            project_id=ctx.contract.project_id,
            contract_version=ctx.contract.contract_version,
            report="C",
            report_version=data.report_version,
            data_cutoff=data.data_cutoff,
            evidence_snapshot_id=evidence_snapshot_id,
            claim_snapshot_id=claim_snapshot_id,
            coverage_set_id=coverage_set_id,
            claim_ids=claim_ids,
            created_at=started_at,
        )
        locked = SnapshotStore(ctx.project_root).lock_report_snapshot(
            report="C", manifest=snapshot_payload.model_dump(mode="json")
        )
        declared_snapshot = snapshot_payload
    assert locked is not None
    files = [path for path in staging_root.rglob("*") if path.is_file()]
    site_digest, site_bytes = site_directory_digest(staging_root)
    modified_at = datetime.fromtimestamp(max(path.stat().st_mtime for path in files), tz=UTC)
    package_digest = hashlib.sha256(
        (Path(__file__).resolve().parents[3] / "package-manifest.json").read_bytes()
    ).hexdigest()
    catalog = PageRegistry.load().catalog(ReportKind.C)
    source_commit = _git_commit()
    manifest = ArtifactManifest(
        schema_version="1.0",
        manifest_id=stable_id(
            "artifact-manifest",
            ctx.contract.project_id,
            run_id,
            "C",
            data.report_version,
        ),
        project_id=ctx.contract.project_id,
        contract_version=ctx.contract.contract_version,
        report="C",
        report_version=data.report_version,
        data_cutoff=data.data_cutoff,
        producer_run_id=run_id,
        source_commit=source_commit,
        package_digest=package_digest,
        evidence_snapshot_id=evidence_snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        report_snapshot_id=locked.snapshot_id,
        coverage_set_id=coverage_set_id,
        coverage_projection_id=coverage_projection_id,
        structured_exceptions=(),
        pages_or_sections=tuple(page.id for page in catalog.pages),
        product_ids=data.product_ids,
        trial_ids=data.trial_ids,
        claim_ids=claim_ids,
        chart_ids=("design-map", "endpoint-matrix", "visit-timeline"),
        table_ids=("eligibility", "interventions", "endpoints", "statistics"),
        evidence_reference_ids=tuple(
            stable_id("source", observation.observation_id) for observation in data.observations[:8]
        ),
        design_contract=DesignContractBinding(
            roles=("report-portal",),
            digest=package_digest,
            applicable_sections=("项目设计合同", "站点式门户"),
        ),
        renderer=RendererBinding(name="report-c-portal", version="1.0"),
        filter_state={},
        generated_at=started_at,
        deterministic_checks=(
            DeterministicCheck(
                check_id="c-static-routes",
                status="passed",
                receipt=data_digest,
            ),
        ),
        render_verdict=RenderVerdict(
            verdict_id=stable_id("render-verdict", run_id, "c-awaiting-review"),
            status="rejected",
            verified_at=modified_at,
            anchor_ids=("尚待独立浏览器验收",),
        ),
        accepted_by=None,
        artifact=ArtifactFileBinding(
            relative_path=f"reports/C/{data.report_version}/html",
            sha256=site_digest,
            byte_size=max(site_bytes, 1),
            modified_at=modified_at,
            media_type="directory",
        ),
        status="generated",
        supersedes_manifest_id=None,
    )
    try:
        site_root, manifest_path = transaction.commit(
            _canonical_json(manifest.model_dump(mode="json"))
        )
    except RenderTransactionError as error:
        raise ContractConfigError(str(error)) from error
    return (
        site_root.relative_to(ctx.project_root).as_posix(),
        manifest_path.relative_to(ctx.project_root).as_posix(),
    )


def _check_renderer_availability(outputs: list[str]) -> None:
    if any(fmt != "html" for fmt in outputs):
        raise RendererUnavailableError("首版只支持站点式 HTML 渲染")


# ─── Canonical output paths ────────────────────────────────────────────────


def validate_run_output_path(rel: str) -> PurePosixPath:
    """生产输出路径校验：只接受规范 blockers 或 ArtifactPathService 规范报告路径。

    拒绝绝对路径、路径穿越、任意命名空间、非规范阻断文件名与非规范报告产物名。
    """
    if "\\" in rel:
        raise RunError(f"输出路径必须使用 POSIX 相对路径：{rel}")
    path = PurePosixPath(rel)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RunError(f"输出路径必须是安全的项目相对路径：{rel}")
    if path.parts[0] == "reports":
        try:
            return _ARTIFACT_PATH_SERVICE.validate_persisted_path(path)
        except ArtifactPathViolation as exc:
            raise RunError(f"报告产物路径不在规范位置：{rel}") from exc
    if path.parts[0] == "blockers":
        if len(path.parts) != 4:
            raise RunError(f"阻断产物路径必须为 blockers/报告/版本/文件名：{rel}")
        if path.parts[1] not in ("A", "B", "C"):
            raise RunError(f"阻断产物报告目录只允许 A、B、C：{rel}")
        if _VERSION_PATTERN.fullmatch(path.parts[2]) is None:
            raise RunError(f"阻断产物版本必须是安全路径段：{rel}")
        if path.parts[3] not in ("audit.json", "audit.md"):
            raise RunError(f"阻断产物文件名必须是 audit.json 或 audit.md：{rel}")
        return path
    raise RunError(f"输出路径不在规范命名空间：{rel}")


# ─── Run manifest ─────────────────────────────────────────────────────────


_MEDIA_TYPES = {
    ".json": "application/json",
    ".md": "text/markdown",
    ".html": "text/html",
}


def _compute_output_file(project_root: Path, rel: str) -> RunOutputFile:
    absolute = project_root / rel
    stat = absolute.stat()
    suffix = Path(rel).suffix
    return RunOutputFile(
        relative_path=rel,
        sha256=_sha256_file(absolute),
        byte_size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        modified_at=datetime.fromtimestamp(stat.st_mtime_ns / 1e9, UTC),
        media_type=_MEDIA_TYPES.get(suffix, "application/octet-stream"),
    )


def _output_file_dict(output: RunOutputFile) -> dict[str, Any]:
    """RunOutputFile 的规范 JSON 形态（清单与终态决策事件共用）。"""
    return {
        "relative_path": output.relative_path,
        "sha256": output.sha256,
        "byte_size": output.byte_size,
        "modified_at": output.modified_at.isoformat(),
        "mtime_ns": output.mtime_ns,
        "media_type": output.media_type,
    }


def _capture_output_baseline(
    project_root: Path,
) -> dict[str, tuple[str, int, int]]:
    """运行开始时的产物基线：(sha256, 字节数, st_mtime_ns)。"""
    baseline: dict[str, tuple[str, int, int]] = {}
    for namespace in ("blockers", "reports"):
        base = project_root / namespace
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(project_root).as_posix()
            stat = path.stat()
            baseline[rel] = (_sha256_file(path), stat.st_size, stat.st_mtime_ns)
    return baseline


def _write_run_manifest(
    project_root: Path,
    *,
    run_id: str,
    project_id: str,
    contract_version: int,
    started_at: datetime,
    finished_at: datetime,
    resume: bool,
    case_id: str | None,
    case_digest: str | None,
    input_hashes: dict[str, str],
    node_summary: dict[str, str],
    reused: list[dict[str, str]],
    outputs: list[RunOutputFile],
    reused_artifacts: list[RunOutputFile],
    event_store: EventStore,
    checkpoint_id: str | None,
    outcome: str,
    runtime_metadata: dict[str, Any] | None = None,
) -> tuple[str, str, int]:
    """持久化当前运行清单；返回 (manifest_digest, 写入前运行事件流摘要, 写入前运行事件数)。"""
    run_events = tuple(event for event in event_store.read_all() if event.run_id == run_id)
    pre_record_event_stream_digest = compute_event_stream_digest(run_events)

    manifest_content: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "project_id": project_id,
        "contract_version": contract_version,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "resume": resume,
        "case_id": case_id,
        "case_digest": case_digest,
        "input_hashes": input_hashes,
        "node_summary": node_summary,
        "reused": reused,
        "outputs": [_output_file_dict(o) for o in outputs],
        "reused_artifacts": [_output_file_dict(o) for o in reused_artifacts],
        "event_count": len(run_events),
        "event_stream_digest": pre_record_event_stream_digest,
        "checkpoint_id": checkpoint_id,
        "outcome": outcome,
    }
    manifest_content.update(runtime_metadata or {})
    manifest_digest = hashlib.sha256(_canonical_json(manifest_content)).hexdigest()
    manifest_content["manifest_digest"] = manifest_digest

    manifest_path = project_root / MANIFEST_RELATIVE_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".current_run.json.",
        suffix=".tmp",
        dir=manifest_path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:
            json.dump(manifest_content, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, manifest_path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return manifest_digest, pre_record_event_stream_digest, len(run_events)


def validate_run_manifest(project_root: Path) -> dict[str, Any]:
    """重新打开校验运行清单：路径、SHA-256、字节、精确 mtime_ns 与事件绑定。"""
    path = project_root / MANIFEST_RELATIVE_PATH
    if not path.is_file():
        raise RunError(f"运行清单不存在：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunError("运行清单不是有效 JSON") from exc
    run_id = str(data.get("run_id", ""))
    for output in data.get("outputs", []):
        rel = str(output["relative_path"])
        validate_run_output_path(rel)
        absolute = project_root / rel
        if not absolute.is_file():
            raise RunError(f"运行清单引用的产出文件不存在：{rel}")
        stat = absolute.stat()
        actual_sha = _sha256_file(absolute)
        if actual_sha != output["sha256"]:
            raise RunError(f"输出文件摘要不匹配：{rel}")
        if stat.st_size != output["byte_size"]:
            raise RunError(f"输出文件大小不匹配：{rel}")
        if stat.st_mtime_ns != output["mtime_ns"]:
            raise RunError(f"输出文件修改时间不匹配：{rel}")
    manifest_content = {k: v for k, v in data.items() if k != "manifest_digest"}
    expected_digest = hashlib.sha256(_canonical_json(manifest_content)).hexdigest()
    if data.get("manifest_digest") != expected_digest:
        raise RunError("运行清单摘要不匹配")

    # 事件绑定：当前运行的 run.manifest.recorded 事件必须存在且逐项一致
    events = EventStore(project_root).read_all()
    recorded = [
        event
        for event in events
        if event.event_type == MANIFEST_RECORDED_EVENT and event.run_id == run_id
    ]
    if len(recorded) != 1:
        raise RunError(f"运行清单缺少唯一对应的运行记录事件：{run_id}")
    payload = recorded[0].payload
    if payload.get("manifest_relative_path") != MANIFEST_RELATIVE_PATH:
        raise RunError("运行记录事件携带的清单路径不一致")
    if payload.get("manifest_digest") != data.get("manifest_digest"):
        raise RunError("运行记录事件携带的清单摘要不一致")
    if payload.get("case_id") != data.get("case_id"):
        raise RunError("运行记录事件携带的案例标识不一致")
    if payload.get("case_digest") != data.get("case_digest"):
        raise RunError("运行记录事件携带的案例摘要不一致")
    input_hashes = {str(key): str(value) for key, value in data.get("input_hashes", {}).items()}
    if payload.get("input_hashes_digest") != compute_input_hashes_digest(input_hashes):
        raise RunError("运行记录事件携带的输入摘要不一致")
    pre_record = tuple(
        event
        for event in events
        if event.run_id == run_id and event.event_type != MANIFEST_RECORDED_EVENT
    )
    if payload.get("pre_record_event_stream_digest") != compute_event_stream_digest(pre_record):
        raise RunError("运行记录事件携带的写入前事件流摘要不一致")
    if payload.get("pre_record_event_count") != len(pre_record):
        raise RunError("运行记录事件携带的写入前事件数不一致")
    if payload.get("pre_record_event_stream_digest") != data.get("event_stream_digest"):
        raise RunError("运行清单写入前事件流摘要与运行记录不一致")
    if payload.get("pre_record_event_count") != data.get("event_count"):
        raise RunError("运行清单写入前事件数与运行记录不一致")

    # 复用产物引用：路径/SHA/字节/精确 mtime_ns，篡改失败关闭
    for artifact in data.get("reused_artifacts", []):
        rel = str(artifact["relative_path"])
        validate_run_output_path(rel)
        absolute = project_root / rel
        if not absolute.is_file():
            raise RunError(f"复用产物文件不存在：{rel}")
        stat = absolute.stat()
        if _sha256_file(absolute) != artifact["sha256"]:
            raise RunError(f"复用产物摘要不匹配：{rel}")
        if stat.st_size != artifact["byte_size"]:
            raise RunError(f"复用产物大小不匹配：{rel}")
        if stat.st_mtime_ns != artifact["mtime_ns"]:
            raise RunError(f"复用产物修改时间不匹配：{rel}")

    # 清单文件未变不代表其站点/快照未变：所有报告引用验证完整锁定链。
    from ci_workflow.qc.browser import load_locked_sitemap_source

    for artifact in (*data.get("outputs", []), *data.get("reused_artifacts", [])):
        parts = Path(artifact["relative_path"]).parts
        if len(parts) == 4 and parts[0] == "reports" and parts[3] == "html.manifest.json":
            locked = load_locked_sitemap_source(project_root, ReportKind(parts[1]), parts[2])
            if (
                locked.manifest.project_id != data["project_id"]
                or locked.manifest.contract_version != data["contract_version"]
            ):
                raise RunError("报告产物与运行项目/合同身份不一致")

    # 终态决策事件：证据阻断运行必须有当前运行记录事件，产物引用与清单一致
    if data.get("outcome") == "evidence_blocked":
        terminal_events = [
            event
            for event in events
            if event.event_type == TERMINAL_DECISION_EVENT and event.run_id == run_id
        ]
        if not terminal_events:
            raise RunError("证据阻断运行缺少终态决策事件")
        manifest_artifacts = list(data.get("outputs", [])) + list(data.get("reused_artifacts", []))
        for terminal_event in terminal_events:
            kind = str(terminal_event.payload.get("report_kind"))
            expected = [
                artifact
                for artifact in manifest_artifacts
                if str(artifact.get("relative_path", "")).startswith(f"blockers/{kind}/")
            ]
            if terminal_event.payload.get("artifacts") != expected:
                raise RunError("终态决策事件的产物引用与运行清单不一致")
            if terminal_event.payload.get("gate_input_digest") is None:
                raise RunError("终态决策事件缺少当前证据摘要引用")
            source_run_id = str(terminal_event.payload.get("source_run_id") or "")
            source_event_id = str(terminal_event.payload.get("source_event_id") or "")
            if terminal_event.payload.get("decision_source") == "reused":
                if source_run_id == run_id:
                    raise RunError("终态决策事件错误地引用当前运行")
                source = next(
                    (event for event in events if event.event_id == source_event_id),
                    None,
                )
                if source is None or source.event_type != "graph.transition.accepted":
                    raise RunError("终态决策事件引用的原决策事件不存在")
            else:
                if source_run_id != run_id:
                    raise RunError("终态决策事件错误地引用其他运行")

    # 节点复用事件：清单 reused 每项必须有当前运行的复用事件
    for item in data.get("reused", []):
        key = str(item["node_id"])
        node_id, _, kind_part = key.partition(":")
        report_kind: str | None = kind_part or None
        if not any(
            event.event_type == NODE_REUSED_EVENT
            and event.run_id == run_id
            and event.payload.get("node_id") == node_id
            and event.payload.get("report_kind") == report_kind
            and event.payload.get("input_digest") == item.get("input_digest")
            and event.payload.get("source_run_id") == item.get("run_id")
            for event in events
        ):
            raise RunError(f"运行清单缺少对应的节点复用事件：{key}")
    return cast(dict[str, Any], data)


# ─── Main run_project dispatch ─────────────────────────────────────────────


def run_project(
    project_root: Path,
    *,
    resume: bool = False,
    run_context: RunContext | None = None,
    require_bound_submission: bool = False,
    capability_probe: CapabilityProbe | None = None,
    capability_host: HostName | None = None,
) -> RunResult:
    """真实项目运行：加载合同、启动类型化图执行器、运行已注册节点、持久化清单。"""
    project_root = project_root.expanduser().resolve()
    try:
        verification = verify_project_workspace(project_root)
    except ProjectWorkspaceError as exc:
        raise ContractConfigError(str(exc)) from exc
    contract = verification.contract

    started_at = datetime.now(UTC)
    run_id = _new_run_id(contract.project_id)
    event_store = EventStore(project_root)
    all_events = event_store.read_all()
    baseline = _capture_output_baseline(project_root)

    # ── resume 语义：只有 resume=True 允许复用历史节点 ──────────────────
    if not resume and all_events:
        raise ContractConfigError(
            "项目已有历史运行记录，不能直接重新开始。"
            "请使用 --resume 从检查点继续，或使用新的项目目录创建全新项目。"
        )

    # ── Resume: derive completed nodes from the persisted event stream ──
    completed = _derive_completed_nodes(all_events)

    # ── Create per-run executor ─────────────────────────────────────────
    executor = GraphExecutor(project_root, run_id=run_id)
    coordinator = PartialDeliveryCoordinator(executor)
    delivery_contract = DeliveryContract(
        contract_id=contract.project_id,
        contract_version=contract.contract_version,
        reports=tuple(r.value for r in contract.reports),
        optional_formats=tuple(sorted(o.value for o in contract.outputs if o.value != "html")),
    )

    # ── Run context for handlers ────────────────────────────────────────
    ctx = run_context or RunContext(project_root=project_root, contract=contract)
    if ctx.project_root != project_root:
        raise ContractConfigError("RunContext 项目根与当前项目不一致")
    if (
        ctx.contract.project_id != contract.project_id
        or ctx.indication != contract.indication
        or ctx.reports != tuple(report.value for report in contract.reports)
        or ctx.data_cutoff != contract.data_cutoff
    ):
        raise ContractConfigError("RunContext 项目、适应症、报告或截止日与当前合同不一致")
    ctx.recover_committed_render = resume
    if capability_probe is not None:
        ctx.capability_probe = capability_probe
    if capability_host is not None:
        ctx.capability_host = capability_host
    submitted_report_packages: dict[str, Path] | None = None
    submitted_audit_package: Any = None
    submitted_audit_digest: str | None = None
    submission_manifest = project_root / "manifests/research-package-submission.json"
    if run_context is None and submission_manifest.is_file():
        from ci_workflow.application.research_package_submission import (
            ResearchPackageSubmissionError,
            load_product_research_submission,
        )

        try:
            submission = load_product_research_submission(project_root)
        except ResearchPackageSubmissionError as error:
            raise ContractConfigError(str(error)) from error
        # The audited package is the project-level universe authority shared by
        # every selected report.  Report packages may project different facts,
        # but must not create report-specific universe identities.
        submitted_audit_package = submission.package
        submitted_audit_digest = _sha256_file(submission.audit_package_path)
        ctx.runtime_metadata["universe_closure_digest"] = submitted_audit_digest
        selected_reports = tuple(report.value for report in contract.reports)
        if len(selected_reports) == 1:
            ctx.research_package_path = submission.report_package_paths[
                cast(Literal["A", "B", "C"], selected_reports[0])
            ]
            ctx.bind_source_input("research-package", ctx.research_package_path)
        else:
            # 多报告严格提交：逐报告独立执行；先绑定首个研究包供共享
            # resume 终态校验识别“已有研究输入”，执行期再按报告重绑。
            submitted_report_packages = {
                name: submission.report_package_paths[cast(Literal["A", "B", "C"], name)]
                for name in selected_reports
            }
            ctx.research_package_path = submitted_report_packages[selected_reports[0]]
            ctx.bind_source_input("research-package", ctx.research_package_path)
        for bound_path in (
            submission.audit_package_path,
            submission.manifest_path,
            *(
                submitted_report_packages.values()
                if submitted_report_packages is not None
                else (ctx.research_package_path,)
            ),
        ):
            relative = bound_path.relative_to(project_root).as_posix()
            ctx.run_inputs.setdefault(relative, _sha256_file(bound_path))
    if (
        not require_bound_submission
        and ctx.research_package_path is None
        and len(contract.reports) == 1
    ):
        canonical_relative = CANONICAL_RESEARCH_PACKAGE_PATHS[contract.reports[0].value]
        canonical_research_package = project_root / canonical_relative
        if canonical_research_package.is_file():
            ctx.research_package_path = canonical_research_package
            ctx.bind_source_input("research-package", ctx.research_package_path)
            ctx.run_inputs.setdefault(
                canonical_relative,
                _sha256_file(canonical_research_package),
            )
    if not require_bound_submission and ctx.report_data_path is None:
        canonical_report_data = project_root / CANONICAL_REPORT_DATA_RELATIVE_PATH
        if canonical_report_data.is_file():
            ctx.report_data_path = canonical_report_data
            ctx.bind_source_input("report-data", ctx.report_data_path)
            ctx.run_inputs.setdefault(
                CANONICAL_REPORT_DATA_RELATIVE_PATH,
                _sha256_file(canonical_report_data),
            )
    if require_bound_submission and not submission_manifest.is_file():
        loose_inputs = [
            project_root / CANONICAL_REPORT_DATA_RELATIVE_PATH,
            *(
                project_root / CANONICAL_RESEARCH_PACKAGE_PATHS[report.value]
                for report in contract.reports
            ),
        ]
        if any(path.is_file() for path in loose_inputs):
            raise ContractConfigError(
                "发现未通过 research submit 绑定的研究文件；产品运行拒绝读取松散输入。"
            )

    # ── resume：派发任何节点前绑定规范宇宙输入并校验终态证据 ────────────
    if resume:
        if ctx.universe_input_path is None:
            canonical = project_root / CANONICAL_UNIVERSE_RELATIVE_PATH
            if canonical.is_file():
                ctx.universe_input_path = canonical
                ctx.bind_source_input("universe", ctx.universe_input_path)
        if ctx.universe_input_path is not None:
            if not ctx.universe_input_path.is_file():
                raise ContractConfigError(f"宇宙证据文件不存在：{ctx.universe_input_path}")
            # 无条件从当前文件字节重新水合：复用同一 RunContext 对象时
            # 不得用旧摘要认证新证据
            _hydrate_universe_evidence(ctx)
        _check_resume_terminal(
            all_events,
            contract,
            ctx,
            project_root,
            research_package_paths=submitted_report_packages,
        )

    now = datetime.now(UTC)
    node_summary: dict[str, str] = {}
    reused: list[dict[str, str]] = []
    current_outputs: dict[tuple[str, str], dict[str, Any]] = {}
    outcome: str = "completed"

    def _run_node(
        node_id: str,
        report_kind: str | None,
        handler: Any,
        *,
        input_digest: str,
        allow_reuse: bool = True,
    ) -> dict[str, Any]:
        nonlocal outcome
        key = _node_key(node_id, report_kind)
        current_key = (key, input_digest)
        if allow_reuse and current_key in current_outputs:
            return current_outputs[current_key]
        prev = completed.get(key, {}).get(input_digest)
        if allow_reuse and prev is not None:
            if node_id == "format" and not all(
                prev["outputs"].get(field)
                for field in ("site_relative_path", "manifest_relative_path")
            ):
                raise RunError("历史格式节点缺少显式产物引用；保留历史，需在新候选中重新生成")
            node_summary[key] = "reused"
            reused.append(
                {
                    "node_id": key,
                    "run_id": prev["run_id"],
                    "input_digest": prev["input_digest"],
                }
            )
            # 当前运行类型化复用事件：绑定节点/报告、原运行/事件/摘要与当前输入摘要
            event_store.append(
                WorkflowEvent(
                    schema_version="1.0",
                    event_id=stable_id(
                        "run-node-reused",
                        contract.project_id,
                        run_id,
                        node_id,
                        report_kind or "shared",
                        input_digest,
                    ),
                    project_id=contract.project_id,
                    run_id=run_id,
                    event_type=NODE_REUSED_EVENT,
                    occurred_at=now,
                    actor_id="run_service",
                    idempotency_key=(
                        f"run.node.reused:{contract.project_id}:{run_id}:"
                        f"{node_id}:{report_kind or 'shared'}:{input_digest}"
                    ),
                    payload={
                        "node_id": node_id,
                        "report_kind": report_kind,
                        "input_digest": input_digest,
                        "source_run_id": prev["run_id"],
                        "source_event_id": prev["event_id"],
                        "source_input_digest": prev["input_digest"],
                        "source_completion_digest": prev["completion_digest"],
                    },
                )
            )
            outputs = cast(dict[str, Any], prev["outputs"])
            current_outputs[current_key] = outputs
            return outputs
        if node_id == "format" and report_kind is not None:
            matrix = ctx.capability_matrix
            if matrix is None:
                raise RunError("HTML 交付前缺少本次能力矩阵")
            delivery = next(
                item
                for item in matrix.deliveries
                if item.report == report_kind and item.output == "html"
            )
            if delivery.state == "blocked":
                node_summary[key] = "capability_blocked"
                outcome = "capability_blocked"
                _merge_report_metadata(
                    ctx.runtime_metadata,
                    {
                        "report_states": {report_kind: "delivery_capability_blocked"},
                        "format_states": {report_kind: {"html": "capability_blocked"}},
                    },
                )
                return {}
        # 输入摘要变化或节点曾失败：重新派发执行
        try:
            outputs = handler(ctx)
        except RunError:
            raise
        except Exception as exc:
            _append_failure_event(
                event_store,
                project_id=contract.project_id,
                run_id=run_id,
                node_id=node_id,
                report_kind=report_kind,
                input_digest=input_digest,
                reason=str(exc),
                occurred_at=now,
            )
            node_summary[key] = "failed"
            outcome = "failed"
            return {}
        executor.complete_node(
            node_id,
            outputs=outputs,
            input_digest=input_digest,
            report_kind=report_kind,
            project_id=contract.project_id,
            actor_id="run_service",
            occurred_at=now,
        )
        node_summary[key] = "completed"
        typed_outputs = cast(dict[str, Any], outputs)
        current_outputs[current_key] = typed_outputs
        return typed_outputs

    def _finalize(current_outcome: str) -> RunResult:
        """重放并持久化检查点后写当前运行清单；失败路径同样先落检查点。"""
        checkpoint_id: str | None = None
        stream = event_store.read_all()
        current_run_events = [event for event in stream if event.run_id == run_id]
        if current_outcome == "evidence_blocked" and not current_run_events:
            raise RunError("证据阻断结论缺少本次运行的证据引用，拒绝生成运行清单")
        if current_run_events:
            checkpoint_id = executor.replay().checkpoint_id
        report_states = _derive_full_family_state(stream, "report_evidence")
        has_terminal_report = any(
            report_states.get(f"report_{report.value}") == "evidence_blocked"
            for report in contract.reports
        )
        collection_outcome = "evidence_blocked" if has_terminal_report else current_outcome
        created, reused_artifacts = _collect_outputs(
            project_root, baseline, collection_outcome, report_outcome=current_outcome,
            report_references=_report_references_from_nodes(current_outputs),
            project_id=contract.project_id,
            contract_version=contract.contract_version,
        )
        if has_terminal_report and (created or reused_artifacts):
            _append_terminal_decision_events(
                event_store,
                project_root,
                contract,
                run_id,
                ctx,
                created,
                reused_artifacts,
                now,
                research_package_paths=submitted_report_packages,
            )
        return _finalize_run(
            project_root,
            run_id,
            contract,
            started_at,
            resume,
            ctx,
            node_summary,
            reused,
            created,
            current_outcome,
            event_store,
            checkpoint_id=checkpoint_id,
            reused_artifacts=reused_artifacts,
        )

    # ── Shared nodes ────────────────────────────────────────────────────
    for node_id, _report_kind, handler in _SHARED_NODES:
        extra = ""
        if node_id == "preflight":
            yaozh_record_path = project_root / "state/yaozh-access.json"
            if yaozh_record_path.is_symlink():
                extra = "invalid-yaozh-record"
            elif yaozh_record_path.is_file():
                extra = _sha256_file(yaozh_record_path)
            else:
                extra = "yaozh-answer-pending"
        inp_digest = _compute_input_digest(node_id, None, contract.contract_version, extra=extra)
        _run_node(
            node_id,
            None,
            handler,
            input_digest=inp_digest,
            allow_reuse=node_id != "preflight",
        )

    if outcome == "failed":
        return _finalize("failed")
    matrix = ctx.capability_matrix
    if matrix is None:
        raise RunError("能力预检未生成本次运行矩阵")
    if all(item.state == "blocked" for item in matrix.research):
        return _finalize("capability_blocked")

    manual_blocked_reports: set[str] = set()
    manual_evidence_blocked_reports: set[str] = set()
    if submitted_audit_package is not None and submitted_audit_digest is not None:
        from ci_workflow.application.publication_manual_gate import (
            PublicationManualGateError,
            materialize_publication_manual_gate,
        )

        try:
            materialized_gate = materialize_publication_manual_gate(
                project_root,
                submitted_audit_package,
                snapshot_id=submitted_audit_digest,
            )
        except PublicationManualGateError as error:
            raise ContractConfigError(str(error)) from error
        if materialized_gate is not None:
            gate = materialized_gate.gate
            ctx.runtime_metadata["manual_supply_gate"] = {
                "gate_id": gate.gate_id,
                "snapshot_id": gate.snapshot_id,
                "relative_path": materialized_gate.relative_path,
                "state": gate.state,
                "user_response_count": gate.user_response_count,
                "affected_reports": list(gate.affected_reports),
                "replayed": materialized_gate.replayed,
            }
            if gate.state == "awaiting_user":
                manual_blocked_reports.update(gate.affected_reports)
            elif gate.state == "accepted":
                manual_blocked_reports.update(gate.affected_reports)
                ctx.runtime_metadata["manual_re_extraction_required"] = list(gate.affected_reports)
            elif gate.evidence_insufficiency_page:
                manual_evidence_blocked_reports.update(gate.affected_reports)
                ctx.runtime_metadata["manual_evidence_insufficient"] = list(gate.affected_reports)
            elif gate.limitation_zh:
                ctx.runtime_metadata["publication_limitation_zh"] = gate.limitation_zh
                ctx.runtime_metadata["publication_limitation_reports"] = list(
                    gate.affected_reports
                )

    # ── B/C 新鲜来源研究包：真实证据、确定性门槛、快照、独立复核 ──────
    research_kinds = tuple(report.value for report in contract.reports)

    def _execute_research_bc(report_kind: str) -> str:
        """单报告 B/C 新鲜来源研究包执行；返回该报告对联合结局的贡献。"""
        if tuple(output.value for output in contract.outputs) != ("html",):
            raise ContractConfigError(f"{report_kind} 类新鲜来源研究包只允许站点式 HTML")
        if ctx.research_package_path is None or not ctx.research_package_path.is_file():
            raise ContractConfigError(
                f"{report_kind} 类新鲜来源研究包不存在：{ctx.research_package_path}"
            )
        research_package_path = ctx.research_package_path

        from ci_workflow.application.fresh_research_ingestion import (
            ingest_research_evidence,
        )

        package_digest = _sha256_file(research_package_path)
        universe_closure_digest = cast(
            str,
            ctx.runtime_metadata.get("universe_closure_digest", package_digest),
        )
        package: Any
        if report_kind == "B":
            from ci_workflow.application.fresh_b_research_package import (
                FreshBEvidenceLineage,
                FreshBResearchPackageError,
                build_b_gate_universe,
                evaluate_fresh_b_gate,
                load_fresh_b_research_package,
                project_fresh_b_report_snapshot,
            )

            try:
                package = load_fresh_b_research_package(research_package_path)
            except FreshBResearchPackageError as error:
                raise ContractConfigError(str(error)) from error
            if package.project_id != contract.project_id:
                raise ContractConfigError("B 类研究包的项目身份与项目合同不一致")
            facts = package.facts
        else:
            from ci_workflow.application.fresh_c_research_package import (
                FreshCPackageError,
                derive_c_research_facts,
                evaluate_c_report_gate,
                load_fresh_c_research_package,
                project_c_report_snapshot,
            )

            try:
                package = load_fresh_c_research_package(research_package_path)
            except FreshCPackageError as error:
                raise ContractConfigError(str(error)) from error
            facts = derive_c_research_facts(package)

        if " ".join(package.indication.split()) != contract.indication:
            raise ContractConfigError(f"{report_kind} 类研究包的适应症与项目合同不一致")
        if package.data_cutoff > contract.data_cutoff:
            raise ContractConfigError(f"{report_kind} 类研究包包含项目截止日之后首次披露的资料")

        initial_nodes: tuple[tuple[str, dict[str, Any]], ...] = (
            (
                "universe",
                {
                    "universe_receipt_id": stable_id(
                        "universe-receipt",
                        contract.project_id,
                        universe_closure_digest,
                    )
                },
            ),
            (
                "route",
                {
                    "source_graph_id": stable_id(
                        "source-graph",
                        contract.project_id,
                        *sorted({item.route_id for item in package.sources}),
                    )
                },
            ),
        )
        for node_id, node_outputs in initial_nodes:
            _run_node(
                node_id,
                None,
                lambda _current, value=node_outputs: value,
                input_digest=_compute_input_digest(
                    node_id,
                    None,
                    contract.contract_version,
                    extra=(universe_closure_digest if node_id == "universe" else package_digest),
                ),
            )

        def _ingest_bc(current: RunContext) -> dict[str, Any]:
            current.research_lineage = ingest_research_evidence(
                project_root=project_root,
                project_id=contract.project_id,
                contract_version=contract.contract_version,
                report_kind=cast(Literal["A", "B", "C"], report_kind),
                data_cutoff=package.data_cutoff,
                scientific_content_digest=package.research_content_digest,
                created_at=package.scientific_review.reviewed_at,
                sources=package.sources,
                route_attempts=package.route_attempts,
                facts=facts,
                claims=package.claims,
            )
            return {
                "ingest_receipt_id": stable_id(
                    "ingest-receipt",
                    contract.project_id,
                    current.research_lineage.evidence_snapshot.snapshot_id,
                )
            }

        _run_node(
            "ingest",
            None,
            _ingest_bc,
            input_digest=_compute_input_digest(
                "ingest", None, contract.contract_version, extra=package.research_content_digest
            ),
        )
        if ctx.research_lineage is None:
            _ingest_bc(ctx)
        lineage = ctx.research_lineage
        evidence_nodes: tuple[tuple[str, dict[str, Any]], ...] = (
            (
                "extract",
                {
                    "extract_receipt_id": stable_id(
                        "extract-receipt", contract.project_id, package_digest
                    )
                },
            ),
            (
                "resolve",
                {
                    "evidence_references": tuple(
                        {
                            "fragment_id": fragment_id,
                            "sha256": _sha256_bytes(source.content_text.encode("utf-8")),
                        }
                        for fragment_id, source in zip(
                            lineage.source_fragment_ids, package.sources, strict=True
                        )
                    )
                },
            ),
        )
        for node_id, node_outputs in evidence_nodes:
            _run_node(
                node_id,
                None,
                lambda _current, value=node_outputs: value,
                input_digest=_compute_input_digest(
                    node_id,
                    None,
                    contract.contract_version,
                    extra=package.research_content_digest,
                ),
            )

        gate_outcome: Any
        if report_kind == "B":
            gate_outcome = evaluate_fresh_b_gate(
                package,
                evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
                contract_version=str(contract.contract_version),
                fact_version_by_ref=lineage.fact_version_by_ref,
            )
        else:
            gate_outcome = evaluate_c_report_gate(
                package,
                project_id=contract.project_id,
                evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
                contract_version=str(contract.contract_version),
                fact_version_by_ref=lineage.fact_version_by_ref,
            )
        gate_result = gate_outcome if report_kind == "B" else gate_outcome.result
        _run_node(
            "gate",
            report_kind,
            lambda _current: {
                "gate_passed": gate_result.decision.value == "passed",
                "failures": gate_result.blocked_unit_ids,
                "evidence_digest": package.research_content_digest,
            },
            input_digest=_compute_input_digest(
                "gate", report_kind, contract.contract_version, package.research_content_digest
            ),
        )
        if gate_result.decision.value != "passed":
            from ci_workflow.application.terminal_recovery import (
                load_double_exhaustion,
                publish_terminal_blocker,
            )
            from ci_workflow.gates.models import GateSpec

            exhaustion = load_double_exhaustion(project_root, ReportKind(report_kind))
            if exhaustion is not None:
                snapshot = (
                    build_b_gate_universe(
                        package,
                        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
                    )
                    if report_kind == "B"
                    else gate_outcome.snapshot
                )
                spec = GateSpec.from_yaml(
                    Path(__file__).resolve().parents[3]
                    / "policies"
                    / f"gates/{report_kind}-v1.yaml"
                )
                report_object_id = f"report_{report_kind}"
                blocker_json, blocker_markdown = publish_terminal_blocker(
                    project_root=project_root,
                    project_id=contract.project_id,
                    contract_version=str(contract.contract_version),
                    report_kind=ReportKind(report_kind),
                    spec=spec,
                    snapshot=snapshot,
                    gate_result=gate_result,
                    exhaustion=exhaustion,
                    source_links=tuple(
                        dict.fromkeys(source.url for source in package.sources)
                    ),
                )
                report_states = _derive_full_family_state(event_store.read_all(), "report_evidence")
                if report_states.get(report_object_id) != "evidence_blocked":
                    _submit_transition(
                        executor,
                        project_id=contract.project_id,
                        family="report_evidence",
                        object_id=report_object_id,
                        from_state="queued",
                        to_state="collecting",
                        trigger="candidate_scope_locked",
                        evidence={"candidate_scope_locked": True},
                        request_id=stable_id("transition", run_id, report_object_id, "collecting"),
                        run_id=run_id,
                        occurred_at=now,
                    )
                    _submit_transition(
                        executor,
                        project_id=contract.project_id,
                        family="report_evidence",
                        object_id=report_object_id,
                        from_state="collecting",
                        to_state="evidence_blocked",
                        trigger="recovery_exhausted_gap_remains",
                        evidence={
                            "critical_units_still_failing": True,
                            "recovery_exhausted": True,
                            "independent_review_exhausted": True,
                            "no_continuable_user_action": True,
                        },
                        request_id=stable_id(
                            "transition", run_id, report_object_id, "evidence-blocked"
                        ),
                        run_id=run_id,
                        occurred_at=now,
                    )
                _merge_report_metadata(
                    ctx.runtime_metadata,
                    {
                        "report_states": {report_kind: "evidence_blocked"},
                        "format_states": {report_kind: {"html": "not_generated"}},
                        "gate_result_keys": {report_kind: gate_result.result_key},
                        "blocked_unit_ids": {report_kind: list(gate_result.blocked_unit_ids)},
                        "blocker_artifacts": {
                            report_kind: [
                                blocker_json.relative_to(project_root).as_posix(),
                                blocker_markdown.relative_to(project_root).as_posix(),
                            ]
                        },
                    },
                )
                node_summary[f"recovery:{report_kind}"] = "exhausted"
                return "evidence_blocked"
            work_item = _write_gate_recovery_work_item(
                project_root, contract, report_kind, package, gate_result
            )
            _merge_report_metadata(
                ctx.runtime_metadata,
                {
                    "report_states": {report_kind: "recovery_required"},
                    "format_states": {report_kind: {"html": "not_generated"}},
                    "gate_result_keys": {report_kind: gate_result.result_key},
                    "blocked_unit_ids": {report_kind: list(gate_result.blocked_unit_ids)},
                    "recovery_work_item": work_item.relative_to(project_root).as_posix(),
                },
            )
            node_summary[f"recovery:{report_kind}"] = "awaiting_recovery"
            return "running"

        def _project_bc(current: RunContext) -> dict[str, Any]:
            projection: Any
            if report_kind == "B":
                b_lineage = FreshBEvidenceLineage(
                    evidence_snapshot=lineage.evidence_snapshot,
                    source_version_ids=lineage.source_version_ids,
                    fragment_ids=lineage.fragment_ids,
                    fact_version_ids=lineage.fact_version_ids,
                    fact_version_by_ref=lineage.fact_version_by_ref,
                )
                projection = project_fresh_b_report_snapshot(
                    package,
                    project_root=project_root,
                    project_id=contract.project_id,
                    contract_version=contract.contract_version,
                    lineage=b_lineage,
                    created_at=package.scientific_review.reviewed_at,
                )
                if package.report_data is None:
                    raise ContractConfigError("B 类门槛通过但缺少门户投影")
                portal_data = package.report_data.model_copy(
                    update={"report_snapshot_id": projection.report_snapshot.snapshot_id}
                )
            else:
                projection = project_c_report_snapshot(
                    package,
                    outcome=gate_outcome,
                    project_root=project_root,
                    project_id=contract.project_id,
                    contract_version=contract.contract_version,
                    evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
                    evidence_snapshot=lineage.evidence_snapshot,
                    fact_version_ids=lineage.fact_version_ids,
                )
                portal_data = projection.portal_data
            current.research_projection = projection
            derived = project_root / f"state/derived/report-{report_kind.lower()}-data.json"
            derived.parent.mkdir(parents=True, exist_ok=True)
            derived.write_bytes(_canonical_json(portal_data.model_dump(mode="json")))
            current.report_data_path = derived
            current.run_inputs.setdefault(
                derived.relative_to(project_root).as_posix(), _sha256_file(derived)
            )
            return {"snapshot_id": projection.report_snapshot.snapshot_id}

        _run_node(
            "snapshot",
            report_kind,
            _project_bc,
            input_digest=_compute_input_digest(
                "snapshot", report_kind, contract.contract_version, package.research_content_digest
            ),
        )
        if ctx.research_projection is None:
            _project_bc(ctx)
        projection = ctx.research_projection

        from ci_workflow.application.review_issuer import (
            ReviewIssuanceError,
            verify_receipt_issuance,
        )
        from ci_workflow.application.scientific_review_transition import (
            RENDERED_UNREVIEWED,
            ScientificReviewTransitionError,
            accepted_verdict_from_receipt,
            build_scientific_review_context,
            capture_portal_artifact_binding,
            promote_rendered_candidate,
            publish_production_context,
            publish_scientific_review_request,
            scientific_review_receipt_path,
        )
        from ci_workflow.qc.review_receipt import ScientificReviewReceiptError

        _run_node(
            "analyze",
            report_kind,
            lambda _current: {
                "pages": tuple(
                    page.id for page in PageRegistry.load().catalog(ReportKind(report_kind)).pages
                )
            },
            input_digest=_compute_input_digest(
                "analyze", report_kind, contract.contract_version, package.research_content_digest
            ),
        )

        def _render_bc(current: RunContext) -> dict[str, Any]:
            if report_kind == "B":
                site_path, manifest_relative, _snapshot_id = _render_html_b(current, run_id)
            else:
                if current.report_data_path is None:
                    raise ContractConfigError("C 类 HTML 渲染缺少报告数据包")
                site_path, manifest_relative = _render_html_c_minimal(
                    current, run_id, current.report_data_path
                )
            manifest_path = project_root / manifest_relative
            from ci_workflow.storage.manifest_store import ArtifactManifest

            manifest = ArtifactManifest.model_validate_json(manifest_path.read_bytes())
            return {
                "format": "html",
                "artifact_id": stable_id("artifact", site_path, manifest_relative),
                "site_relative_path": site_path,
                "manifest_relative_path": manifest_relative,
                "candidate_artifact_digest": manifest.artifact.sha256,
                "visual_plan_digest": _compute_input_digest(
                    "visual-plan", report_kind, contract.contract_version, package_digest
                ),
            }

        _run_node(
            "format",
            report_kind,
            _render_bc,
            input_digest=_compute_input_digest(
                "format", report_kind, contract.contract_version, package.research_content_digest
            ),
        )
        if outcome in {"failed", "capability_blocked"}:
            return outcome

        # ── format 完成后才允许科学晋级：先绑定门户字节，再发布复核请求 ──
        artifact_manifest_relative = (
            f"reports/{report_kind}/{package.report_version}/html.manifest.json"
        )
        artifact_manifest_path = project_root / artifact_manifest_relative
        if not artifact_manifest_path.is_file():
            raise ContractConfigError(
                f"{report_kind} 类 HTML 产物清单不存在：{artifact_manifest_path}"
            )
        site_relative = f"reports/{report_kind}/{package.report_version}/html"
        try:
            portal_binding = capture_portal_artifact_binding(
                project_root,
                report_kind,
                manifest_relative=artifact_manifest_relative,
                site_relative=site_relative,
            )
        except ScientificReviewTransitionError as error:
            raise ContractConfigError(str(error)) from error

        if report_kind == "B":
            criteria_version = projection.gate_result.spec_version
            gate_result_key = projection.gate_result.result_key
            evidence_snapshot_id = projection.evidence_snapshot_id
        else:
            criteria_version = gate_outcome.spec_version
            gate_result_key = projection.gate_result_key
            evidence_snapshot_id = lineage.evidence_snapshot.snapshot_id
        try:
            review_context = build_scientific_review_context(
                project_id=contract.project_id,
                report_kind=report_kind,
                report_version=package.report_version,
                producer_id=package.producer_id,
                candidate_snapshot_id=projection.report_snapshot.snapshot_id,
                candidate_content_digest=package.research_content_digest,
                criteria_version=criteria_version,
                gate_result_key=gate_result_key,
                contract_version=str(contract.contract_version),
                coverage_set_id=projection.coverage_set_id,
                evidence_snapshot_id=evidence_snapshot_id,
                claim_snapshot_id=projection.claim_snapshot_id,
                sources=package.sources,
                facts=facts,
                claims=package.claims,
                fact_version_by_ref=lineage.fact_version_by_ref,
            )
        except ScientificReviewTransitionError as error:
            raise ContractConfigError(str(error)) from error
        publish_production_context(project_root, report_kind, review_context)
        try:
            publish_scientific_review_request(
                project_root,
                report_kind,
                review_context,
                producer_session_id=run_id,
                produced_at=datetime.now(UTC),
                portal_binding=portal_binding,
            )
        except ScientificReviewTransitionError as error:
            raise ContractConfigError(str(error)) from error

        report_state = RENDERED_UNREVIEWED
        receipt_relative = scientific_review_receipt_path(report_kind)
        if (project_root / receipt_relative).is_file():
            try:
                promoted_at = datetime.now(UTC)
                receipt = verify_receipt_issuance(project_root, report_kind, checked_at=promoted_at)
                report_state = promote_rendered_candidate(
                    project_root=project_root,
                    current_state=RENDERED_UNREVIEWED,
                    context=review_context,
                    receipt=receipt,
                    promoted_at=promoted_at,
                )
                verdict = accepted_verdict_from_receipt(
                    project_root=project_root,
                    context=review_context,
                    receipt=receipt,
                )
            except (
                ScientificReviewTransitionError,
                ScientificReviewReceiptError,
                ReviewIssuanceError,
            ) as error:
                raise ContractConfigError(
                    f"独立科学复核状态迁移被拒绝，候选保持未复核：{error}"
                ) from error
            _merge_report_metadata(
                ctx.runtime_metadata,
                {"scientific_review_receipts": {report_kind: receipt.receipt_digest}},
            )
            _run_node(
                "scientific_qc",
                report_kind,
                lambda _current: {
                    "qc_verdict": {
                        "verdict_id": verdict.verdict_id,
                        "verdict_digest": verdict.verdict_digest,
                        "candidate_snapshot_id": verdict.candidate_snapshot_id,
                        "candidate_content_digest": verdict.candidate_content_digest,
                        "review_input_digest": verdict.review_input_digest,
                    }
                },
                input_digest=_compute_input_digest(
                    "scientific_qc",
                    report_kind,
                    contract.contract_version,
                    receipt.receipt_digest,
                ),
            )
        elif _last_completed_node(all_events, "scientific_qc", report_kind) is not None:
            raise ContractConfigError(
                f"{report_kind} 类候选此前已晋级为科学复核完成状态，"
                "但当前独立复核回执缺失或不可验证："
                "已晋级候选不可回退为未复核，也不接受无关历史。"
                f"请恢复 {scientific_review_receipt_path(report_kind)} 后重试 --resume。"
            )
        _merge_report_metadata(
            ctx.runtime_metadata,
            {
                "report_states": {report_kind: report_state},
                "format_states": {report_kind: {"html": "quality_check"}},
                "snapshot_ids": {report_kind: projection.report_snapshot.snapshot_id},
                "artifact_manifest_sha256": {
                    report_kind: {"html": _sha256_file(artifact_manifest_path)}
                },
                "scientific_review_contexts": {report_kind: review_context.model_dump(mode="json")},
                "scientific_review_portal_bindings": {
                    report_kind: portal_binding.model_dump(mode="json")
                },
            },
        )
        return "completed"

    def _execute_research_a() -> str:
        """单报告 A 新鲜来源研究包执行；返回该报告对联合结局的贡献。"""
        if tuple(output.value for output in contract.outputs) != ("html",):
            raise ContractConfigError("A 类新鲜来源研究包只允许生成站点式 HTML")
        if ctx.research_package_path is None or not ctx.research_package_path.is_file():
            raise ContractConfigError(f"A 类新鲜来源研究包不存在：{ctx.research_package_path}")
        research_package_path = ctx.research_package_path
        from ci_workflow.application.source_research_service import (
            ingest_fresh_a_research_package,
            load_fresh_a_research_package,
            persist_report_a_projection,
        )

        package = load_fresh_a_research_package(research_package_path)
        if " ".join(package.indication.split()) != contract.indication:
            raise ContractConfigError("A 类研究包的适应症与项目合同不一致")
        if package.data_cutoff > contract.data_cutoff:
            raise ContractConfigError("A 类研究包包含项目截止日之后首次披露的资料")
        package_digest = _sha256_file(research_package_path)
        universe_closure_digest = cast(
            str,
            ctx.runtime_metadata.get("universe_closure_digest", package_digest),
        )
        derived_data_path = project_root / "state/derived/report-a-data.json"
        derived_data_path.parent.mkdir(parents=True, exist_ok=True)
        derived_data_path.write_bytes(_canonical_json(package.report_data.model_dump(mode="json")))
        ctx.report_data_path = derived_data_path
        ctx.bind_source_input("report-data", ctx.report_data_path)
        ctx.run_inputs.setdefault(
            "state/derived/report-a-data.json", _sha256_file(derived_data_path)
        )

        _run_node(
            "universe",
            None,
            lambda _current: {
                "universe_receipt_id": stable_id(
                    "universe-receipt",
                    contract.project_id,
                    universe_closure_digest,
                ),
            },
            input_digest=_compute_input_digest(
                "universe",
                None,
                contract.contract_version,
                extra=universe_closure_digest,
            ),
        )
        _run_node(
            "route",
            None,
            lambda _current: {
                "source_graph_id": stable_id(
                    "source-graph",
                    contract.project_id,
                    *sorted({item.route_id for item in package.sources}),
                ),
            },
            input_digest=_compute_input_digest(
                "route", None, contract.contract_version, extra=package_digest
            ),
        )

        def _ingest_research(current: RunContext) -> dict[str, Any]:
            current.research_lineage = ingest_fresh_a_research_package(
                project_root=project_root,
                project_id=contract.project_id,
                contract_version=contract.contract_version,
                package=package,
            )
            return {
                "ingest_receipt_id": stable_id(
                    "ingest-receipt",
                    contract.project_id,
                    current.research_lineage.evidence_snapshot.snapshot_id,
                )
            }

        _run_node(
            "ingest",
            None,
            _ingest_research,
            input_digest=_compute_input_digest(
                "ingest", None, contract.contract_version, extra=package_digest
            ),
        )
        if ctx.research_lineage is None:
            _ingest_research(ctx)
        lineage = ctx.research_lineage
        evidence_references = tuple(
            {
                "fragment_id": fragment_id,
                "sha256": _sha256_bytes(capture.content_text.encode("utf-8")),
            }
            for fragment_id, capture in zip(
                lineage.source_fragment_ids, package.sources, strict=True
            )
        )
        shared_nodes: tuple[tuple[str, dict[str, Any]], ...] = (
            (
                "extract",
                {
                    "extract_receipt_id": stable_id(
                        "extract-receipt", contract.project_id, package_digest
                    )
                },
            ),
            ("resolve", {"evidence_references": evidence_references}),
        )
        for node_id, outputs in shared_nodes:
            _run_node(
                node_id,
                None,
                lambda _current, value=outputs: value,
                input_digest=_compute_input_digest(
                    node_id,
                    None,
                    contract.contract_version,
                    extra=package.research_content_digest,
                ),
            )

        report_nodes: tuple[tuple[str, dict[str, Any]], ...] = (
            (
                "gate",
                {
                    "gate_passed": True,
                    "failures": (),
                    "evidence_digest": package.research_content_digest,
                },
            ),
            (
                "snapshot",
                {"snapshot_id": lineage.evidence_snapshot.snapshot_id},
            ),
            (
                "analyze",
                {
                    "pages": tuple(
                        page.id for page in PageRegistry.load().catalog(ReportKind.A).pages
                    )
                },
            ),
        )
        for node_id, outputs in report_nodes:
            _run_node(
                node_id,
                "A",
                lambda _current, value=outputs: value,
                input_digest=_compute_input_digest(
                    node_id,
                    "A",
                    contract.contract_version,
                    extra=package.research_content_digest,
                ),
            )

        def _render_fresh_a(current: RunContext) -> dict[str, Any]:
            site_path, manifest_relative = _render_html_a(current, run_id)
            manifest_path = project_root / manifest_relative
            persist_report_a_projection(
                project_root=project_root,
                lineage=current.research_lineage,
                manifest_path=manifest_path,
            )
            return {
                "format": "html",
                "artifact_id": stable_id("artifact", site_path, manifest_relative, package_digest),
                "site_relative_path": site_path,
                "manifest_relative_path": manifest_relative,
                "candidate_artifact_digest": _sha256_file(manifest_path),
                "visual_plan_digest": _compute_input_digest(
                    "visual-plan",
                    "A",
                    contract.contract_version,
                    extra=package_digest,
                ),
            }

        _run_node(
            "format",
            "A",
            _render_fresh_a,
            input_digest=_compute_input_digest(
                "format", "A", contract.contract_version, extra=package_digest
            ),
        )
        if outcome in {"failed", "capability_blocked"}:
            return outcome

        # A 类研究包内的审阅材料仅证明摄取前研究质量，不授权报告候选晋级。
        # 门户必须先完成渲染并绑定真实字节，再由独立宿主签发正式回执。
        from ci_workflow.application.review_issuer import (
            ReviewIssuanceError,
            verify_receipt_issuance,
        )
        from ci_workflow.application.scientific_review_transition import (
            RENDERED_UNREVIEWED,
            ScientificReviewTransitionError,
            accepted_verdict_from_receipt,
            build_scientific_review_context,
            capture_portal_artifact_binding,
            promote_rendered_candidate,
            publish_production_context,
            publish_scientific_review_request,
            scientific_review_receipt_path,
        )
        from ci_workflow.qc.review_receipt import ScientificReviewReceiptError
        from ci_workflow.storage.manifest_store import ArtifactManifest
        from ci_workflow.storage.sqlite import open_database

        artifact_manifest_relative = f"reports/A/{package.report_version}/html.manifest.json"
        artifact_manifest_path = project_root / artifact_manifest_relative
        if not artifact_manifest_path.is_file():
            raise ContractConfigError(f"A 类 HTML 产物清单不存在：{artifact_manifest_path}")
        site_relative = f"reports/A/{package.report_version}/html"
        try:
            portal_binding = capture_portal_artifact_binding(
                project_root,
                "A",
                manifest_relative=artifact_manifest_relative,
                site_relative=site_relative,
            )
        except ScientificReviewTransitionError as error:
            raise ContractConfigError(str(error)) from error

        candidate_manifest = ArtifactManifest.model_validate_json(
            artifact_manifest_path.read_bytes()
        )
        package_fact_ids = {fact.fact_id for fact in package.facts}
        with open_database(project_root / "state/project.sqlite") as database:
            fact_version_rows = database.execute(
                "SELECT fact_id, fact_version_id FROM fact_versions"
            ).fetchall()
        fact_version_by_ref: dict[str, str] = {}
        for fact_id, version_id in fact_version_rows:
            if fact_id not in package_fact_ids:
                continue
            if fact_id in fact_version_by_ref:
                raise ContractConfigError(
                    f"研究事实 {fact_id} 存在多个持久化事实版本，拒绝重建来源引用"
                )
            fact_version_by_ref[fact_id] = str(version_id)
        missing_fact_ids = sorted(package_fact_ids - set(fact_version_by_ref))
        if missing_fact_ids:
            raise ContractConfigError(
                "研究事实缺少持久化事实版本：" + "、".join(missing_fact_ids[:5])
            )

        try:
            review_context = build_scientific_review_context(
                project_id=contract.project_id,
                report_kind="A",
                report_version=package.report_version,
                producer_id=stable_id(
                    "fresh-a-producer",
                    contract.project_id,
                    package.research_content_digest,
                ),
                candidate_snapshot_id=candidate_manifest.report_snapshot_id,
                candidate_content_digest=package.research_content_digest,
                criteria_version="A_MATURITY_V1",
                gate_result_key=stable_id(
                    "gate-evaluation",
                    contract.project_id,
                    "A",
                    package.research_content_digest,
                ),
                contract_version=str(contract.contract_version),
                coverage_set_id=lineage.coverage_set_id,
                evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
                claim_snapshot_id=lineage.claim_snapshot_id,
                sources=package.sources,
                facts=package.facts,
                claims=package.claims,
                fact_version_by_ref=fact_version_by_ref,
            )
            publish_production_context(project_root, "A", review_context)
            publish_scientific_review_request(
                project_root,
                "A",
                review_context,
                producer_session_id=run_id,
                produced_at=datetime.now(UTC),
                portal_binding=portal_binding,
            )
        except ScientificReviewTransitionError as error:
            raise ContractConfigError(str(error)) from error

        report_state = RENDERED_UNREVIEWED
        receipt_relative = scientific_review_receipt_path("A")
        if (project_root / receipt_relative).is_file():
            try:
                promoted_at = datetime.now(UTC)
                receipt = verify_receipt_issuance(project_root, "A", checked_at=promoted_at)
                report_state = promote_rendered_candidate(
                    project_root=project_root,
                    current_state=RENDERED_UNREVIEWED,
                    context=review_context,
                    receipt=receipt,
                    promoted_at=promoted_at,
                )
                verdict = accepted_verdict_from_receipt(
                    project_root=project_root,
                    context=review_context,
                    receipt=receipt,
                )
            except (
                ReviewIssuanceError,
                ScientificReviewTransitionError,
                ScientificReviewReceiptError,
            ) as error:
                raise ContractConfigError(
                    f"独立科学复核状态迁移被拒绝，候选保持未复核：{error}"
                ) from error
            _merge_report_metadata(
                ctx.runtime_metadata,
                {"scientific_review_receipts": {"A": receipt.receipt_digest}},
            )
            _run_node(
                "scientific_qc",
                "A",
                lambda _current: {
                    "qc_verdict": {
                        "verdict_id": verdict.verdict_id,
                        "verdict_digest": verdict.verdict_digest,
                        "candidate_snapshot_id": verdict.candidate_snapshot_id,
                        "candidate_content_digest": verdict.candidate_content_digest,
                        "review_input_digest": verdict.review_input_digest,
                    }
                },
                input_digest=_compute_input_digest(
                    "scientific_qc",
                    "A",
                    contract.contract_version,
                    receipt.receipt_digest,
                ),
            )
        elif _last_completed_node(all_events, "scientific_qc", "A") is not None:
            raise ContractConfigError(
                "A 类候选此前已晋级为科学复核完成状态，但当前独立复核回执"
                "缺失或不可验证：已晋级候选不可回退为未复核。"
                f"请恢复 {receipt_relative} 后重试 --resume。"
            )
        _merge_report_metadata(
            ctx.runtime_metadata,
            {
                "report_states": {"A": report_state},
                "format_states": {"A": {"html": "quality_check"}},
                "snapshot_ids": {"A": candidate_manifest.report_snapshot_id},
                "artifact_manifest_sha256": {"A": {"html": _sha256_file(artifact_manifest_path)}},
                "scientific_review_contexts": {"A": review_context.model_dump(mode="json")},
                "scientific_review_portal_bindings": {"A": portal_binding.model_dump(mode="json")},
            },
        )
        return "completed"

    # ── 已提交多报告产品运行：逐报告独立执行、诚实聚合，不建融合门户 ──
    if submitted_report_packages is not None:
        per_report_outcomes: dict[str, str] = {}
        for report_enum in contract.reports:
            report_name = report_enum.value
            if report_name in manual_evidence_blocked_reports:
                report_object_id = f"report_{report_name}"
                _drive_publication_manual_report_state(
                    executor,
                    contract,
                    run_id,
                    now,
                    report_name,
                    report_object_id,
                    gate_relative_path=cast(
                        str,
                        cast(dict[str, Any], ctx.runtime_metadata["manual_supply_gate"])[
                            "relative_path"
                        ],
                    ),
                    target="evidence_blocked",
                )
                _write_publication_evidence_insufficiency(
                    project_root,
                    contract,
                    report_name,
                    submitted_audit_digest or "",
                )
                per_report_outcomes[report_name] = "evidence_blocked"
                node_summary[f"publication_manual_gate:{report_name}"] = "evidence_blocked"
                _merge_report_metadata(
                    ctx.runtime_metadata,
                    {
                        "report_states": {report_name: "evidence_blocked"},
                        "format_states": {report_name: {"html": "not_generated"}},
                    },
                )
                continue
            if report_name in manual_blocked_reports:
                manual_state = (
                    "recovery_required"
                    if "manual_re_extraction_required" in ctx.runtime_metadata
                    else "awaiting_user"
                )
                _drive_publication_manual_report_state(
                    executor,
                    contract,
                    run_id,
                    now,
                    report_name,
                    f"report_{report_name}",
                    gate_relative_path=cast(
                        str,
                        cast(dict[str, Any], ctx.runtime_metadata["manual_supply_gate"])[
                            "relative_path"
                        ],
                    ),
                    target=manual_state,
                )
                per_report_outcomes[report_name] = manual_state
                node_summary[f"publication_manual_gate:{report_name}"] = manual_state
                _merge_report_metadata(
                    ctx.runtime_metadata,
                    {
                        "report_states": {
                            report_name: (
                                "re_extraction_required"
                                if manual_state == "recovery_required"
                                else "awaiting_user"
                            )
                        },
                        "format_states": {report_name: {"html": "not_generated"}},
                    },
                )
                continue
            readiness = next(item for item in matrix.research if item.report == report_name)
            if readiness.state == "blocked":
                per_report_outcomes[report_name] = "capability_blocked"
                continue
            # 每个报告只消费自己的科学载荷；谱系/投影/报告数据按报告重置，
            # 避免上一报告的运行上下文泄入下一报告。
            ctx.research_package_path = submitted_report_packages[report_name]
            ctx.bind_source_input("research-package", ctx.research_package_path)
            ctx.research_lineage = None
            ctx.research_projection = None
            ctx.report_data_path = None
            ctx.bind_source_input("report-data", None)
            if report_name == "A":
                report_outcome = _execute_research_a()
            else:
                report_outcome = _execute_research_bc(report_name)
            per_report_outcomes[report_name] = report_outcome
            if report_outcome == "failed" or outcome == "failed":
                return _finalize("failed")
        _merge_report_metadata(ctx.runtime_metadata, {"per_report_outcomes": per_report_outcomes})
        return _finalize(_aggregate_multi_report_outcome(per_report_outcomes))

    if ctx.research_package_path is not None and research_kinds in {("B",), ("C",)}:
        if research_kinds[0] in manual_evidence_blocked_reports:
            report_name = research_kinds[0]
            _drive_publication_manual_report_state(
                executor,
                contract,
                run_id,
                now,
                report_name,
                f"report_{report_name}",
                gate_relative_path=cast(
                    str,
                    cast(dict[str, Any], ctx.runtime_metadata["manual_supply_gate"])[
                        "relative_path"
                    ],
                ),
                target="evidence_blocked",
            )
            _write_publication_evidence_insufficiency(
                project_root,
                contract,
                report_name,
                submitted_audit_digest or "",
            )
            node_summary[f"publication_manual_gate:{report_name}"] = "evidence_blocked"
            return _finalize("evidence_blocked")
        if research_kinds[0] in manual_blocked_reports:
            manual_state = (
                "recovery_required"
                if "manual_re_extraction_required" in ctx.runtime_metadata
                else "awaiting_user"
            )
            _drive_publication_manual_report_state(
                executor,
                contract,
                run_id,
                now,
                research_kinds[0],
                f"report_{research_kinds[0]}",
                gate_relative_path=cast(
                    str,
                    cast(dict[str, Any], ctx.runtime_metadata["manual_supply_gate"])[
                        "relative_path"
                    ],
                ),
                target=manual_state,
            )
            node_summary[f"publication_manual_gate:{research_kinds[0]}"] = manual_state
            _merge_report_metadata(
                ctx.runtime_metadata,
                {
                    "report_states": {
                        research_kinds[0]: (
                            "re_extraction_required"
                            if manual_state == "recovery_required"
                            else "awaiting_user"
                        )
                    },
                    "format_states": {research_kinds[0]: {"html": "not_generated"}},
                    "per_report_outcomes": {research_kinds[0]: manual_state},
                },
            )
            return _finalize(manual_state)
        return _finalize(_execute_research_bc(research_kinds[0]))

    if ctx.research_package_path is not None:
        if research_kinds != ("A",):
            raise ContractConfigError("A 类新鲜来源研究包只允许生成 A 类报告")
        if "A" in manual_evidence_blocked_reports:
            _drive_publication_manual_report_state(
                executor,
                contract,
                run_id,
                now,
                "A",
                "report_A",
                gate_relative_path=cast(
                    str,
                    cast(dict[str, Any], ctx.runtime_metadata["manual_supply_gate"])[
                        "relative_path"
                    ],
                ),
                target="evidence_blocked",
            )
            _write_publication_evidence_insufficiency(
                project_root,
                contract,
                "A",
                submitted_audit_digest or "",
            )
            node_summary["publication_manual_gate:A"] = "evidence_blocked"
            return _finalize("evidence_blocked")
        if "A" in manual_blocked_reports:
            manual_state = (
                "recovery_required"
                if "manual_re_extraction_required" in ctx.runtime_metadata
                else "awaiting_user"
            )
            _drive_publication_manual_report_state(
                executor,
                contract,
                run_id,
                now,
                "A",
                "report_A",
                gate_relative_path=cast(
                    str,
                    cast(dict[str, Any], ctx.runtime_metadata["manual_supply_gate"])[
                        "relative_path"
                    ],
                ),
                target=manual_state,
            )
            node_summary["publication_manual_gate:A"] = manual_state
            _merge_report_metadata(
                ctx.runtime_metadata,
                {
                    "report_states": {
                        "A": (
                            "re_extraction_required"
                            if manual_state == "recovery_required"
                            else "awaiting_user"
                        )
                    },
                    "format_states": {"A": {"html": "not_generated"}},
                    "per_report_outcomes": {"A": manual_state},
                },
            )
            return _finalize(manual_state)
        return _finalize(_execute_research_a())

    # ── 多报告数据包：A/B/C 站点式 HTML ───────────────────────────────────
    if ctx.report_data_paths:
        report_values = tuple(report.value for report in contract.reports)
        output_values = tuple(output.value for output in contract.outputs)
        if output_values != ("html",):
            raise ContractConfigError("多报告数据包首版只允许生成站点式 HTML")
        expected_kinds = tuple(sorted(ctx.report_data_paths))
        if sorted(report_values) != list(expected_kinds):
            raise ContractConfigError("多报告数据包与项目合同报告集合不一致，拒绝生成。")

        loaded: dict[str, Any] = {}
        for kind in report_values:
            data_path = ctx.report_data_paths[kind]
            if not data_path.is_file():
                raise ContractConfigError(f"{kind} 类报告数据包不存在：{data_path}")
            if kind == "A":
                from ci_workflow.renderers.portal.report_a import load_report_a_data

                loaded[kind] = load_report_a_data(data_path)
            elif kind == "B":
                from ci_workflow.renderers.portal.report_b import (
                    load_report_b_data,
                    report_b_baseline_gate_failures,
                )

                loaded[kind] = load_report_b_data(data_path)
                failures = report_b_baseline_gate_failures(loaded[kind])
                if failures:
                    raise ContractConfigError(
                        "B 类基线门槛未通过，拒绝生成 HTML："
                        + ",".join(
                            f"{item['failure_code']}:{item['trial_id']}:{item['group_id']}"
                            for item in failures
                        )
                    )
            else:
                from ci_workflow.renderers.portal.report_c import load_report_c_data

                loaded[kind] = load_report_c_data(data_path)
            report_data = loaded[kind]
            if " ".join(report_data.indication.split()) != contract.indication:
                raise ContractConfigError(
                    f"{kind} 类报告数据包的适应症与项目合同不一致，拒绝生成。"
                )
            if report_data.data_cutoff > contract.data_cutoff:
                raise ContractConfigError(
                    f"{kind} 类报告数据包包含项目截止日之后的资料，拒绝生成。"
                )

        html_manifest_digests: dict[str, str] = {}
        for kind in report_values:
            data_path = ctx.report_data_paths[kind]
            render_digest = _compute_input_digest(
                "format",
                kind,
                contract.contract_version,
                extra=_sha256_file(data_path) + ":html",
            )

            def _render_kind(
                current: RunContext,
                *,
                _kind: str = kind,
                _data_path: Path = data_path,
            ) -> dict[str, Any]:
                current.report_data_path = _data_path
                if _kind == "A":
                    site_path, manifest_path = _render_html_a(current, run_id)
                elif _kind == "B":
                    site_path, manifest_path, _snapshot_id = _render_html_b(current, run_id)
                else:
                    site_path, manifest_path = _render_html_c_minimal(current, run_id, _data_path)
                manifest_digest = _sha256_file(project_root / manifest_path)
                html_manifest_digests[_kind] = manifest_digest
                return {
                    "format": "html",
                    "artifact_id": stable_id("artifact", site_path, manifest_path),
                    "site_relative_path": site_path,
                    "manifest_relative_path": manifest_path,
                    "candidate_artifact_digest": manifest_digest,
                    "visual_plan_digest": _compute_input_digest(
                        "visual-plan",
                        _kind,
                        contract.contract_version,
                        extra=manifest_digest,
                    ),
                }

            _run_node("format", kind, _render_kind, input_digest=render_digest)
            if outcome in {"failed", "capability_blocked"}:
                return _finalize(outcome)

        for kind in report_values:
            manifest_path = (
                project_root / "reports" / kind / loaded[kind].report_version / "html.manifest.json"
            )
            if not manifest_path.is_file():
                raise ContractConfigError(f"{kind} 类 HTML 产物清单不存在：{manifest_path}")
            html_manifest_digests.setdefault(kind, _sha256_file(manifest_path))

        ctx.runtime_metadata.update(
            {
                "report_states": {kind: "rendered_unreviewed" for kind in report_values},
                "format_states": {kind: {"html": "generated"} for kind in report_values},
                "html_manifest_sha256": html_manifest_digests,
            }
        )
        return _finalize("completed")

    # ── 已验证报告数据包：A/B/C 站点式 HTML ──────────────────────────────
    if ctx.report_data_path is not None:
        report_data_path = ctx.report_data_path
        from ci_workflow.storage.manifest_store import ArtifactManifest

        report_values = tuple(report.value for report in contract.reports)
        if len(report_values) != 1 or report_values[0] not in {"A", "B", "C"}:
            raise ContractConfigError("当前报告数据包只允许单独生成 A、B 或 C 类报告")
        output_values = tuple(output.value for output in contract.outputs)
        if output_values != ("html",):
            raise ContractConfigError("当前报告数据包首版只允许生成站点式 HTML")
        if not report_data_path.is_file():
            raise ContractConfigError(f"报告数据包不存在：{report_data_path}")
        report_kind = report_values[0]
        if report_kind == "A":
            from ci_workflow.renderers.portal.report_a import load_report_a_data

            report_data = load_report_a_data(ctx.report_data_path)
        elif report_kind == "B":
            from ci_workflow.renderers.portal.report_b import load_report_b_data

            report_data = load_report_b_data(ctx.report_data_path)
        else:
            from ci_workflow.renderers.portal.report_c import load_report_c_data

            report_data = load_report_c_data(ctx.report_data_path)
        if " ".join(report_data.indication.split()) != contract.indication:
            raise ContractConfigError(
                f"{report_kind} 类报告数据包的适应症与项目合同不一致，拒绝生成。"
            )
        if report_data.data_cutoff > contract.data_cutoff:
            raise ContractConfigError(
                f"{report_kind} 类报告数据包包含项目截止日之后的资料，拒绝生成。"
            )
        render_digest = _compute_input_digest(
            "render",
            report_kind,
            contract.contract_version,
            extra=_sha256_file(report_data_path),
        )

        if report_kind == "B":
            from ci_workflow.renderers.portal.report_b import (
                report_b_baseline_gate_failures,
            )

            gate_failures = report_b_baseline_gate_failures(report_data)
            _run_node(
                "gate",
                "B",
                lambda _current: {
                    "gate_passed": not gate_failures,
                    "failures": [
                        f"{item['failure_code']}:{item['trial_id']}:{item['group_id']}"
                        for item in gate_failures
                    ],
                    "evidence_digest": _sha256_file(report_data_path),
                },
                input_digest=_compute_input_digest(
                    "gate",
                    "B",
                    contract.contract_version,
                    extra=_sha256_file(report_data_path),
                ),
            )
            if outcome == "failed":
                return _finalize("failed")
            if gate_failures:
                ctx.runtime_metadata.update(
                    {
                        "report_states": {"B": "recovery_required"},
                        "format_states": {"B": {"html": "not_generated"}},
                        "gate_failures": [dict(item) for item in gate_failures],
                    }
                )
                node_summary["recovery:B"] = "required"
                return _finalize("recovery_required")

            def _render_positive_b(current: RunContext) -> dict[str, Any]:
                site_path, manifest_path, snapshot_id = _render_html_b(current, run_id)
                manifest_file = project_root / manifest_path
                manifest_sha = _sha256_file(manifest_file)
                from ci_workflow.storage.manifest_store import ArtifactManifest

                artifact_manifest = ArtifactManifest.model_validate_json(manifest_file.read_bytes())
                current.runtime_metadata.update(
                    {
                        "report_states": {"B": "rendered_unreviewed"},
                        "format_states": {"B": {"html": "quality_check"}},
                        "snapshot_ids": {"B": snapshot_id},
                        "artifact_manifest_sha256": {"B": {"html": manifest_sha}},
                        "gate_failures": [],
                    }
                )
                return {
                    "format": "html",
                    "artifact_id": stable_id("artifact", site_path, manifest_path),
                    "site_relative_path": site_path,
                    "manifest_relative_path": manifest_path,
                    "candidate_artifact_digest": artifact_manifest.artifact.sha256,
                    "visual_plan_digest": _compute_input_digest(
                        "visual-plan",
                        "B",
                        contract.contract_version,
                        extra=render_digest,
                    ),
                }

            _run_node("format", "B", _render_positive_b, input_digest=render_digest)
            if outcome in {"failed", "capability_blocked"}:
                return _finalize(outcome)
            return _finalize("completed")

        if report_kind == "C":

            def _render_positive_c(current: RunContext) -> dict[str, Any]:
                site_path, manifest_path = _render_html_c_minimal(current, run_id, report_data_path)
                manifest_file = project_root / manifest_path
                manifest = ArtifactManifest.model_validate_json(manifest_file.read_bytes())
                current.runtime_metadata.update(
                    {
                        "report_states": {"C": "rendered_unreviewed"},
                        "format_states": {"C": {"html": "quality_check"}},
                        "snapshot_ids": {"C": manifest.report_snapshot_id},
                        "artifact_manifest_sha256": {"C": {"html": _sha256_file(manifest_file)}},
                    }
                )
                return {
                    "format": "html",
                    "artifact_id": stable_id("artifact", site_path, manifest_path),
                    "site_relative_path": site_path,
                    "manifest_relative_path": manifest_path,
                    "candidate_artifact_digest": manifest.artifact.sha256,
                    "visual_plan_digest": _compute_input_digest(
                        "visual-plan",
                        "C",
                        contract.contract_version,
                        extra=render_digest,
                    ),
                }

            _run_node("format", "C", _render_positive_c, input_digest=render_digest)
            if outcome in {"failed", "capability_blocked"}:
                return _finalize(outcome)
            return _finalize("completed")

        def _render_positive_a(current: RunContext) -> dict[str, Any]:
            site_path, manifest_path = _render_html_a(current, run_id)
            manifest_file = project_root / manifest_path
            manifest = ArtifactManifest.model_validate_json(manifest_file.read_bytes())
            current.runtime_metadata.update(
                {
                    "report_states": {"A": "rendered_unreviewed"},
                    "format_states": {"A": {"html": "quality_check"}},
                    "snapshot_ids": {"A": manifest.report_snapshot_id},
                    "artifact_manifest_sha256": {"A": {"html": _sha256_file(manifest_file)}},
                }
            )
            return {
                "format": "html",
                "artifact_id": stable_id("artifact", site_path, manifest_path),
                "site_relative_path": site_path,
                "manifest_relative_path": manifest_path,
                "candidate_artifact_digest": manifest.artifact.sha256,
                "visual_plan_digest": _compute_input_digest(
                    "visual-plan",
                    "A",
                    contract.contract_version,
                    extra=render_digest,
                ),
            }

        _run_node("format", "A", _render_positive_a, input_digest=render_digest)
        if outcome in {"failed", "capability_blocked"}:
            return _finalize(outcome)
        return _finalize("completed")

    # ── 项目对象在当前运行内确立（新项目或失败后恢复驱动终态）──────────
    # 持久化状态为 None（从未建立）或 running（先前运行 bootstrap 后失败）时，
    # 在当前运行内经声明迁移重新确立项目对象，随后协调器才能按声明契约把
    # 项目驱动到 blocked；终态（blocked）项目不重提项目迁移（--resume 非重开）。
    project_object_id = stable_id("project-obj", contract.project_id)
    persisted_project_state = _derive_full_family_state(all_events, "project").get(
        project_object_id
    )
    if persisted_project_state in (None, "running"):
        _submit_transition(
            executor,
            project_id=contract.project_id,
            family="project",
            object_id=project_object_id,
            from_state=None,
            to_state="running",
            trigger="project_contract_and_preflight",
            evidence={
                "project_contract_established": True,
                "preflight_records_established": True,
            },
            request_id=f"{run_id}:project:create",
            run_id=run_id,
            occurred_at=now,
        )

    # ── Universe node ───────────────────────────────────────────────────
    if ctx.universe_input_path is None:
        _write_source_research_work_item(project_root, contract)
        node_summary["universe"] = "awaiting_source_research"
    elif not ctx.universe_input_path.is_file():
        outcome = "failed"
        node_summary["universe"] = "failed"
        _append_failure_event(
            event_store,
            project_id=contract.project_id,
            run_id=run_id,
            node_id="universe",
            report_kind=None,
            input_digest=_universe_input_digest(contract, ctx.universe_input_path),
            reason=f"universe 输入文件不存在：{ctx.universe_input_path}",
            occurred_at=now,
        )
    else:
        inp_digest = _universe_input_digest(contract, ctx.universe_input_path)
        try:
            _run_node("universe", None, _handler_universe, input_digest=inp_digest)
        except RunError as exc:
            outcome = "failed"
            node_summary["universe"] = "failed"
            _append_failure_event(
                event_store,
                project_id=contract.project_id,
                run_id=run_id,
                node_id="universe",
                report_kind=None,
                input_digest=inp_digest,
                reason=str(exc),
                occurred_at=now,
            )

    if outcome == "failed":
        return _finalize("failed")

    # ── Report nodes for each report kind in the contract ───────────────
    for report_enum in contract.reports:
        kind_value = report_enum.value
        report_object_id = f"report_{kind_value}"

        # Gate node (only if universe evidence available)
        gate_key = f"gate:{kind_value}"
        if kind_value == "A" and ctx.universe_evidence is not None:
            gate_digest = _compute_input_digest(
                "gate",
                kind_value,
                contract.contract_version,
                extra=ctx.universe_evidence.evidence_digest,
            )
            try:
                _run_node(
                    "gate",
                    kind_value,
                    _handler_gate_a,
                    input_digest=gate_digest,
                )
            except RunError as exc:
                outcome = "failed"
                node_summary[gate_key] = "failed"
                _append_failure_event(
                    event_store,
                    project_id=contract.project_id,
                    run_id=run_id,
                    node_id="gate",
                    report_kind=kind_value,
                    input_digest=gate_digest,
                    reason=str(exc),
                    occurred_at=now,
                )
        else:
            node_summary[gate_key] = "skipped"
            continue

        if outcome == "failed":
            break

        # Recovery node
        rec_key = f"recovery:{kind_value}"
        if kind_value == "A" and ctx.universe_evidence is not None:
            rec_digest = _compute_input_digest(
                "recovery",
                kind_value,
                contract.contract_version,
                extra=ctx.universe_evidence.exhaustion.record_digest,
            )
            try:
                _run_node(
                    "recovery",
                    kind_value,
                    _handler_recovery_a,
                    input_digest=rec_digest,
                )
            except RunError as exc:
                outcome = "failed"
                node_summary[rec_key] = "failed"
                _append_failure_event(
                    event_store,
                    project_id=contract.project_id,
                    run_id=run_id,
                    node_id="recovery",
                    report_kind=kind_value,
                    input_digest=rec_digest,
                    reason=str(exc),
                    occurred_at=now,
                )
        else:
            node_summary[rec_key] = "skipped"

        if outcome == "failed":
            break

        # ── Report transitions (per-run fresh；终态报告不重提迁移) ────
        report_states = _derive_full_family_state(event_store.read_all(), "report_evidence")
        if report_states.get(report_object_id) == "evidence_blocked":
            # 终态阻断：保留既有决策；当前运行复用/终态决策事件与复用产物
            # 引用由 _finalize 记录（--resume 不是隐式重新打开）
            package_dir = project_root / "blockers" / kind_value / "v1"
            from ci_workflow.gates.blocker_audit import (
                BlockerAuditDriftError,
                BlockerPackageIntegrityError,
                assert_no_report_downstream_artifacts,
                validate_existing_blocker_package,
            )

            try:
                validate_existing_blocker_package(
                    package_dir,
                    project_id=contract.project_id,
                    report_kind=ReportKind(kind_value),
                    report_version="v1",
                )
                assert_no_report_downstream_artifacts(
                    project_root / "state" / "project.sqlite",
                    project_id=contract.project_id,
                    report_kind=ReportKind(kind_value),
                    report_version="v1",
                    workspace_root=project_root,
                )
            except (BlockerAuditDriftError, BlockerPackageIntegrityError, ValueError) as exc:
                raise ContractConfigError(
                    "证据不足阻断项目的阻断说明缺失、漂移或不符合合同；"
                    "请恢复该审计包后重试 --resume，或使用显式的项目重新打开流程。"
                ) from exc
            node_summary[f"decision:{kind_value}"] = "preserved"
            continue
        _drive_report_transitions(
            executor,
            contract,
            run_id,
            now,
            project_object_id,
            kind_value,
            report_object_id,
        )

        # ── Write blocker package if evidence blocked ─────────────────
        _drive_blocker_write(project_root, contract, kind_value, ctx)

    if outcome == "failed":
        return _finalize("failed")

    # ── Coordinator: 只在本运行提交过项目迁移时推进终态 ────────────────
    current_run_events = [event for event in event_store.read_all() if event.run_id == run_id]
    has_project_event = any(
        e.event_type == "graph.transition.accepted" and e.payload.get("family") == "project"
        for e in current_run_events
    )
    if has_project_event:
        coordinator.reconcile(
            delivery_contract,
            actor_id="run_service",
            occurred_at=now,
        )

    # ── Determine outcome from report states ────────────────────────────
    report_states = _derive_full_family_state(event_store.read_all(), "report_evidence")
    if any(state == "evidence_blocked" for state in report_states.values()):
        outcome = "evidence_blocked"
    elif node_summary.get("universe") == "awaiting_source_research":
        # 无研究输入：有明确可恢复待办 → running（不说完成）
        outcome = "running"

    return _finalize(outcome)


# ─── Report transitions ────────────────────────────────────────────────────


def _drive_publication_manual_report_state(
    executor: GraphExecutor,
    contract: Any,
    run_id: str,
    now: datetime,
    kind_value: str,
    report_object_id: str,
    *,
    gate_relative_path: str,
    target: str,
) -> None:
    """Persist the real wait/recovery path for one publication-gated report."""

    current = str(
        executor.state().get("report_evidence", {}).get(report_object_id, "queued")
    )
    if current == "queued":
        event = _submit_transition(
            executor,
            project_id=contract.project_id,
            family="report_evidence",
            object_id=report_object_id,
            from_state="queued",
            to_state="collecting",
            trigger="candidate_scope_locked",
            evidence={"candidate_scope_locked": True},
            request_id=stable_id(
                "publication-manual-transition", report_object_id, gate_relative_path, "collecting"
            ),
            run_id=run_id,
            occurred_at=now,
        )
        if event.event_type != "graph.transition.accepted":
            raise ContractConfigError("Publication 补件报告无法进入 collecting")
        current = "collecting"
    if current == "collecting":
        event = _submit_transition(
            executor,
            project_id=contract.project_id,
            family="report_evidence",
            object_id=report_object_id,
            from_state="collecting",
            to_state="awaiting_user",
            trigger="recovery_exhausted_need_user",
            evidence={
                "recovery_exhausted": True,
                "critical_gap_remains": True,
                "audit_package_written": True,
                "request_written": True,
                "audit_package_path": gate_relative_path,
            },
            request_id=stable_id(
                "publication-manual-transition",
                report_object_id,
                gate_relative_path,
                "awaiting-user",
            ),
            run_id=run_id,
            occurred_at=now,
        )
        if event.event_type != "graph.transition.accepted":
            raise ContractConfigError("Publication 补件报告无法进入 awaiting_user")
        current = "awaiting_user"
    if target == "awaiting_user" or current == target:
        return
    if current == "awaiting_user":
        accepted = target == "recovery_required"
        event = _submit_transition(
            executor,
            project_id=contract.project_id,
            family="report_evidence",
            object_id=report_object_id,
            from_state="awaiting_user",
            to_state="recovering",
            trigger="user_input_accepted",
            evidence={
                (
                    "required_file_accepted"
                    if accepted
                    else "user_confirmed_material_unavailable"
                ): True
            },
            request_id=stable_id(
                "publication-manual-transition",
                report_object_id,
                gate_relative_path,
                "recovering",
            ),
            run_id=run_id,
            occurred_at=now,
        )
        if event.event_type != "graph.transition.accepted":
            raise ContractConfigError("Publication 补件报告无法进入 recovering")
        current = "recovering"
    if target == "recovery_required" or current == target:
        return
    if target == "evidence_blocked" and current == "recovering":
        event = _submit_transition(
            executor,
            project_id=contract.project_id,
            family="report_evidence",
            object_id=report_object_id,
            from_state="recovering",
            to_state="evidence_blocked",
            trigger="recovery_exhausted_gap_remains",
            evidence={
                "critical_units_still_failing": True,
                "recovery_exhausted": True,
                "independent_review_exhausted": True,
                "no_continuable_user_action": True,
            },
            request_id=stable_id(
                "publication-manual-transition",
                report_object_id,
                gate_relative_path,
                "evidence-blocked",
            ),
            run_id=run_id,
            occurred_at=now,
        )
        if event.event_type != "graph.transition.accepted":
            raise ContractConfigError("Publication 补件报告无法进入 evidence_blocked")
        return
    raise ContractConfigError(
        f"Publication 补件门无法从 {current} 推进 {kind_value} 到 {target}"
    )


def _drive_report_transitions(
    executor: GraphExecutor,
    contract: Any,
    run_id: str,
    now: datetime,
    project_object_id: str,
    kind_value: str,
    report_object_id: str,
) -> None:
    """驱动单个报告的收集→证据阻断迁移链。"""
    _submit_transition(
        executor,
        project_id=contract.project_id,
        family="report_evidence",
        object_id=report_object_id,
        from_state="queued",
        to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True},
        request_id=f"{run_id}:{kind_value}:collecting",
        run_id=run_id,
        occurred_at=now,
    )
    _submit_transition(
        executor,
        project_id=contract.project_id,
        family="report_evidence",
        object_id=report_object_id,
        from_state="collecting",
        to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        evidence={
            "critical_units_still_failing": True,
            "recovery_exhausted": True,
            "independent_review_exhausted": True,
            "no_continuable_user_action": True,
        },
        request_id=f"{run_id}:{kind_value}:evidence_blocked",
        run_id=run_id,
        occurred_at=now,
    )


def _write_publication_evidence_insufficiency(
    project_root: Path, contract: Any, report_kind: str, snapshot_id: str
) -> None:
    """发布一次性补件不可得的类型化、原子、可恢复校验 blocker。"""
    from ci_workflow.gates.blocker_audit import (
        BlockerAuditDriftError,
        BlockerPackageIntegrityError,
        build_and_write_publication_blocker_package,
    )
    from ci_workflow.ingestion.publication_gate import ManualSupplyGate

    gate_path = project_root / f"state/manual-supply-gates/{snapshot_id}.json"
    try:
        gate = ManualSupplyGate.model_validate_json(gate_path.read_bytes())
        build_and_write_publication_blocker_package(
            project_id=contract.project_id,
            report_kind=ReportKind(report_kind),
            contract_version=str(contract.contract_version),
            report_version="v1",
            manual_gate=gate,
            workspace_root=project_root,
            database_path=project_root / "state/project.sqlite",
        )
    except (
        OSError,
        ValueError,
        BlockerAuditDriftError,
        BlockerPackageIntegrityError,
    ) as error:
        raise ContractConfigError(
            "Publication 证据不足阻断包不可验证或发生漂移，拒绝发布。"
        ) from error


def _drive_blocker_write(
    project_root: Path,
    contract: Any,
    kind_value: str,
    ctx: RunContext,
) -> None:
    """写入证据不足阻断包（空宇宙路径）；内容确定性取自已绑定记录。"""
    from ci_workflow.gates.blocker_audit import (
        BlockerAuditDriftError,
        BlockerPackageIntegrityError,
        build_and_write_blocker_package,
    )
    from ci_workflow.gates.models import GateSpec

    report_kind = ReportKind(kind_value)
    spec = GateSpec.from_yaml(
        Path(__file__).resolve().parents[3] / "policies" / f"gates/{kind_value}-v1.yaml"
    )
    evidence = ctx.universe_evidence
    if evidence is None:
        raise ContractConfigError("空宇宙阻断写入缺少已绑定的宇宙证据")

    db_path = project_root / "state" / "project.sqlite"
    _JUSTIFICATIONS = {
        "A": "本轮未识别出符合条件的创新产品（适格创新药产品为空），故产品格局报告无法开展。",
        "B": "本项目没有达到最低结果报告要求的适格试验，故临床证据报告无法开展。",
        "C": "本项目没有达到核心设计最低门槛的适格试验，故试验设计报告无法开展。",
    }
    try:
        build_and_write_blocker_package(
            project_id=contract.project_id,
            report_kind=report_kind,
            contract_version=str(contract.contract_version),
            report_version="v1",
            spec=spec,
            snapshot=None,
            gate_result=None,
            failed_units=(),
            exhaustion=evidence.exhaustion,
            empty_universe=evidence.kind(),
            empty_evidence=evidence,
            empty_justification_zh=_JUSTIFICATIONS[kind_value],
            residual_uncertainty_zh="部分来源可能需要再次核对。",
            user_help_needed=False,
            user_input_directory=None,
            minimal_user_action_zh="无需用户操作。",
            source_links=(),
            resume_instruction_zh="补充材料后请重新运行本报告的证据核对。",
            workspace_root=project_root,
            database_path=db_path,
        )
    except (BlockerAuditDriftError, BlockerPackageIntegrityError, ValueError) as exc:
        raise ContractConfigError(
            "阻断说明写入失败：既有阻断说明内容或目录与本次结果不一致，"
            "拒绝覆盖。请恢复原始阻断说明文件后重试，"
            "或使用显式的项目重新打开流程。"
        ) from exc


# ─── Terminal decision reuse ───────────────────────────────────────────────


def _append_terminal_decision_events(
    event_store: EventStore,
    project_root: Path,
    contract: Any,
    run_id: str,
    ctx: RunContext,
    created: list[RunOutputFile],
    reused: list[RunOutputFile],
    now: datetime,
    research_package_paths: dict[str, Path] | None = None,
) -> None:
    """为阻断产物写当前运行的终态决策记录事件（每个终态报告一条）。

    绑定决策来源（本次运行新决策或复用先前运行决策）、原决策事件、
    当前证据输入摘要与精确产物引用；不重提终态迁移。新决策（创建产物）
    与复用决策都记录事件，使阻断产物的权威元组在事件流中持续可校验。
    """
    stream = event_store.read_all()
    report_states = _derive_full_family_state(stream, "report_evidence")
    for report_kind in contract.reports:
        kind_value = report_kind.value
        object_id = f"report_{kind_value}"
        if report_states.get(object_id) != "evidence_blocked":
            continue
        artifacts = [
            output
            for output in (*created, *reused)
            if output.relative_path.startswith(f"blockers/{kind_value}/")
        ]
        if not artifacts:
            raise ContractConfigError(
                "证据不足阻断项目的阻断说明文件缺失或已被改写"
                f"（blockers/{kind_value}/v1/audit.json 与 audit.md）。"
                "请恢复该文件后重试 --resume，或使用显式的项目重新打开流程。"
            )
        source = _last_evidence_blocked_transition(stream, object_id)
        if source is None:
            raise RunError(f"找不到报告 {kind_value} 的证据阻断迁移事件")
        package_path = (
            research_package_paths.get(kind_value)
            if research_package_paths is not None
            else ctx.research_package_path
        )
        if ctx.universe_evidence is not None:
            evidence_digest = ctx.universe_evidence.evidence_digest
        elif package_path is not None and package_path.is_file():
            evidence_digest = _research_package_content_digest(package_path, kind_value)
        elif ctx.report_data_path is not None and ctx.report_data_path.is_file():
            evidence_digest = _sha256_file(ctx.report_data_path)
        else:
            raise RunError("终态决策事件缺少当前证据引用")
        gate_input_digest = _compute_input_digest(
            "gate",
            kind_value,
            contract.contract_version,
            extra=evidence_digest,
        )
        event_store.append(
            WorkflowEvent(
                schema_version="1.0",
                event_id=stable_id(
                    "run-terminal-decision",
                    contract.project_id,
                    run_id,
                    object_id,
                ),
                project_id=contract.project_id,
                run_id=run_id,
                event_type=TERMINAL_DECISION_EVENT,
                occurred_at=now,
                actor_id="run_service",
                idempotency_key=(
                    f"run.terminal_decision.recorded:{contract.project_id}:{run_id}:{object_id}"
                ),
                payload={
                    "report_kind": kind_value,
                    "report_object_id": object_id,
                    "decision_source": ("current" if source.run_id == run_id else "reused"),
                    "source_run_id": source.run_id,
                    "source_event_id": source.event_id,
                    "gate_input_digest": gate_input_digest,
                    "artifacts": [_output_file_dict(output) for output in artifacts],
                },
            )
        )


# ─── Collect outputs ────────────────────────────────────────────────────────


def _report_references_from_nodes(
    outputs: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, str]:
    references: dict[str, str] = {}
    for (node_key, _input_digest), value in outputs.items():
        if not node_key.startswith("format:"):
            continue
        manifest = value.get("manifest_relative_path")
        site = value.get("site_relative_path")
        if (
            value.get("format") != "html"
            or not isinstance(manifest, str) or not isinstance(site, str)
        ):
            raise RunError("格式节点缺少显式HTML产物引用")
        parts = Path(manifest).parts
        if (
            len(parts) != 4 or parts[0] != "reports"
            or parts[1] != node_key.removeprefix("format:")
            or parts[3] != "html.manifest.json" or manifest in references
        ):
            raise RunError("格式节点报告类型或唯一产物引用不一致")
        references[manifest] = site
    return references


def _collect_outputs(
    project_root: Path,
    baseline: dict[str, tuple[str, int, int]],
    outcome: str,
    *, report_outcome: str | None = None,
    report_references: dict[str, str] | None = None,
    project_id: str | None = None,
    contract_version: int | None = None,
) -> tuple[list[RunOutputFile], list[RunOutputFile]]:
    """收集本次运行的规范阻断文件：(created, reused)。

    created = 运行前不存在或三元组（sha256, 字节, mtime_ns）变化的文件（新产出）；
    reused = 运行前已存在且未变化的阻断文件，仅在证据阻断结局下作为
    复用产物/证据引用，不冒充本次创建。
    """
    created: list[RunOutputFile] = []
    reused: list[RunOutputFile] = []
    base = project_root / "blockers"
    if base.is_dir():
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(project_root).as_posix()
            try:
                validate_run_output_path(rel)
            except RunError:
                continue
            stat = path.stat()
            sha = _sha256_file(path)
            if rel in baseline and baseline[rel] == (sha, stat.st_size, stat.st_mtime_ns):
                if outcome == "evidence_blocked":
                    reused.append(_compute_output_file(project_root, rel))
            else:
                created.append(_compute_output_file(project_root, rel))
    from ci_workflow.qc.browser import load_locked_sitemap_source

    for rel, site_rel in sorted((report_references or {}).items()):
        validate_run_output_path(rel)
        parts = Path(rel).parts
        if len(parts) != 4 or parts[0] != "reports" or parts[3] != "html.manifest.json":
            raise RunError("格式节点没有引用规范报告清单")
        locked = load_locked_sitemap_source(project_root, ReportKind(parts[1]), parts[2])
        if (
            locked.manifest.project_id != project_id
            or locked.manifest.contract_version != contract_version
            or locked.manifest.artifact.relative_path != site_rel
        ):
            raise RunError("格式节点引用的产物身份或站点不一致")
        path = project_root / rel
        stat = path.stat()
        sha = _sha256_file(path)
        if rel not in baseline or baseline[rel] != (sha, stat.st_size, stat.st_mtime_ns):
            created.append(_compute_output_file(project_root, rel))
        elif (report_outcome or outcome) == "completed":
            reused.append(_compute_output_file(project_root, rel))
    return created, reused


# ─── Failure event ──────────────────────────────────────────────────────────


def _append_failure_event(
    event_store: EventStore,
    *,
    project_id: str,
    run_id: str,
    node_id: str,
    report_kind: str | None,
    input_digest: str,
    reason: str,
    occurred_at: datetime,
) -> None:
    event_id = stable_id(
        "node-failed",
        project_id,
        run_id,
        node_id,
        report_kind or "shared",
        input_digest,
    )
    event_store.append(
        WorkflowEvent(
            schema_version="1.0",
            event_id=event_id,
            project_id=project_id,
            run_id=run_id,
            event_type="run.node.failed",
            occurred_at=occurred_at,
            actor_id="run_service",
            idempotency_key=(
                f"run.node.failed:{project_id}:{run_id}:{node_id}:"
                f"{report_kind or 'shared'}:{input_digest}"
            ),
            payload={
                "node_id": node_id,
                "report_kind": report_kind,
                "input_digest": input_digest,
                "reason": reason,
            },
        )
    )


# ─── Transition helper ─────────────────────────────────────────────────────


def _submit_transition(
    executor: GraphExecutor,
    *,
    project_id: str,
    family: str,
    object_id: str,
    from_state: str | None,
    to_state: str,
    trigger: str,
    evidence: dict[str, object],
    request_id: str,
    run_id: str,
    occurred_at: datetime,
) -> StoredWorkflowEvent:
    return executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=request_id,
            project_id=project_id,
            run_id=run_id,
            family=family,
            object_id=object_id,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            evidence=evidence,
            actor_id="run_service",
            occurred_at=occurred_at,
        )
    )


# ─── Finalize ──────────────────────────────────────────────────────────────


def _finalize_run(
    project_root: Path,
    run_id: str,
    contract: Any,
    started_at: datetime,
    resume: bool,
    run_context: RunContext | None,
    node_summary: dict[str, str],
    reused: list[dict[str, str]],
    outputs: list[RunOutputFile],
    outcome: str,
    event_store: EventStore,
    checkpoint_id: str | None = None,
    reused_artifacts: list[RunOutputFile] | None = None,
) -> RunResult:
    finished_at = datetime.now(UTC)
    case_id = run_context.run_inputs.get("case_id") if run_context else None
    case_digest = run_context.run_inputs.get("case_digest") if run_context else None
    input_hashes = {
        k: v
        for k, v in (run_context.run_inputs.items() if run_context else {})
        if k not in ("case_id", "case_digest")
    }
    manifest_digest, pre_record_stream_digest, pre_record_count = _write_run_manifest(
        project_root,
        run_id=run_id,
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        started_at=started_at,
        finished_at=finished_at,
        resume=resume,
        case_id=case_id,
        case_digest=case_digest,
        input_hashes=input_hashes,
        node_summary=node_summary,
        reused=reused,
        outputs=outputs,
        reused_artifacts=reused_artifacts or [],
        event_store=event_store,
        checkpoint_id=checkpoint_id,
        outcome=outcome,
        runtime_metadata=run_context.runtime_metadata if run_context else None,
    )

    # 清单从追加式事件流绑定：写入后追加同 run_id 的持久化记录事件
    event_store.append(
        WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id("run-manifest-recorded", contract.project_id, run_id),
            project_id=contract.project_id,
            run_id=run_id,
            event_type=MANIFEST_RECORDED_EVENT,
            occurred_at=finished_at,
            actor_id="run_service",
            idempotency_key=(f"run.manifest.recorded:{contract.project_id}:{run_id}"),
            payload={
                "manifest_relative_path": MANIFEST_RELATIVE_PATH,
                "manifest_digest": manifest_digest,
                "case_id": case_id,
                "case_digest": case_digest,
                "input_hashes_digest": compute_input_hashes_digest(input_hashes),
                "pre_record_event_stream_digest": pre_record_stream_digest,
                "pre_record_event_count": pre_record_count,
            },
        )
    )

    # Update status.md — native Chinese, no backend labels
    status_path = project_root / "logs" / "status.md"
    if outcome == "evidence_blocked":
        status_path.write_text(
            "# 项目状态\n\n"
            "项目因关键证据不足暂时无法继续。"
            "请查看项目目录中的「证据不足说明」了解详情。\n",
            encoding="utf-8",
        )
    elif outcome == "capability_blocked":
        status_path.write_text(
            "# 项目状态\n\n"
            "当前执行环境缺少本次研究或 HTML 交付所需能力，项目已安全暂停。"
            "请按能力预检说明恢复后，从同一项目继续。\n",
            encoding="utf-8",
        )
    elif outcome == "failed":
        status_path.write_text(
            "# 项目状态\n\n本轮运行遇到技术问题，未能完成。请查看运行记录了解详情。\n",
            encoding="utf-8",
        )
    elif outcome == "running":
        status_path.write_text(
            "# 项目状态\n\n项目已启动，证据采集工作正在进行中。\n",
            encoding="utf-8",
        )
    elif outcome == "awaiting_user":
        status_path.write_text(
            "# 项目状态\n\n项目正在等待一次性补充关键公开资料。"
            "请查看「需要补充的公开资料」清单，补件后从同一项目继续。\n",
            encoding="utf-8",
        )
    elif outcome == "recovery_required":
        status_path.write_text(
            "# 项目状态\n\n补充资料已完成核验，受影响报告正在等待 Agent 按重抽取任务"
            "重建并重新提交科学载荷；当前未发布旧载荷报告。\n",
            encoding="utf-8",
        )
    else:
        status_path.write_text(
            "# 项目状态\n\n项目运行完成。\n",
            encoding="utf-8",
        )

    exit_codes = {
        "completed": 0,
        "running": 0,
        "awaiting_user": 6,
        "recovery_required": 7,
        "evidence_blocked": 4,
        "capability_blocked": 5,
        "renderer_unavailable": 3,
        "failed": 2,
    }
    return RunResult(
        run_id=run_id,
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        outcome=cast(Any, outcome),
        exit_code=exit_codes.get(outcome, 2),
        node_summary=node_summary,
        reused=tuple(reused),
        outputs=tuple(outputs),
        case_id=case_id,
        case_digest=case_digest,
        input_hashes=input_hashes,
    )
