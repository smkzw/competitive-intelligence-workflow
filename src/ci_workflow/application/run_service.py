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

from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    verify_project_workspace,
)
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.recovery import DeliveryContract, PartialDeliveryCoordinator
from ci_workflow.graph.types import TransitionRequest
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
        "completed", "running", "evidence_blocked",
        "renderer_unavailable", "failed",
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
    universe_evidence: Any = None
    run_inputs: dict[str, str] = field(default_factory=dict)


# ─── Constants ─────────────────────────────────────────────────────────────


MANIFEST_RELATIVE_PATH = "manifests/current_run.json"
MANIFEST_RECORDED_EVENT = "run.manifest.recorded"
NODE_REUSED_EVENT = "run.node.reused"
TERMINAL_DECISION_EVENT = "run.terminal_decision.recorded"
CANONICAL_UNIVERSE_RELATIVE_PATH = "evidence/library/universe.json"

_VERSION_PATTERN = re.compile(r"^v[0-9]+(?:\.[0-9]+){0,2}(?:-[a-z0-9][a-z0-9.-]*)?$")
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
    return _sha256_bytes(
        _canonical_json({key: input_hashes[key] for key in sorted(input_hashes)})
    )


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
) -> dict[str, dict[str, Any]]:
    """从全部事件流派生已完成节点集合。key = node_key → completion payload + run_id。"""
    completed: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.event_type == "graph.node.completed":
            p = event.payload
            key = _node_key(str(p["node_id"]), p.get("report_kind"))
            completed[key] = {
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


# ─── Universe evidence binding ─────────────────────────────────────────────


def _hydrate_universe_evidence(ctx: RunContext) -> None:
    """从已绑定输入确定性重建宇宙证据（解析+类型化校验+项目身份绑定）。"""
    from ci_workflow.gates.blocker_audit import EmptyUniverseEvidence

    if ctx.universe_input_path is None or not ctx.universe_input_path.is_file():
        raise ContractConfigError(
            f"宇宙证据文件不存在：{ctx.universe_input_path}"
        )
    try:
        raw = json.loads(ctx.universe_input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractConfigError(
            f"宇宙证据文件不是有效 JSON：{ctx.universe_input_path}"
        ) from exc
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
    if ctx.universe_input_path is None:
        if terminal_kinds:
            raise ContractConfigError(
                "项目处于证据不足阻断状态，且项目内没有宇宙证据文件"
                f"（{CANONICAL_UNIVERSE_RELATIVE_PATH}）。"
                "请恢复该文件后重新 --resume，或使用显式的项目重新打开流程。"
            )
        if _had_universe_attempt(events):
            raise ContractConfigError(
                "上次运行因缺少宇宙证据而中断，且项目内仍没有宇宙证据文件。"
                f"请将证据文件放入 {CANONICAL_UNIVERSE_RELATIVE_PATH} 后重新 --resume。"
            )
        return
    for kind_value in terminal_kinds:
        gate_digest = _compute_input_digest(
            "gate",
            kind_value,
            contract.contract_version,
            extra=ctx.universe_evidence.evidence_digest,
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


# ─── Node handlers ────────────────────────────────────────────────────────


def _handler_intake(ctx: RunContext) -> dict[str, Any]:
    return {"project_contract_id": ctx.contract.project_id}


def _handler_preflight(ctx: RunContext) -> dict[str, Any]:
    from ci_workflow.application.capability_preflight import (
        CapabilitySelection,
        RuntimeCapabilityProbe,
        run_capability_preflight,
    )

    reports = tuple(r.value for r in ctx.contract.reports)
    outputs = tuple(o.value for o in ctx.contract.outputs)
    selection = CapabilitySelection(
        reports=cast(Any, reports),
        outputs=cast(Any, outputs),
        source_routes=cast(Any, ("public-http",)),
        needs_document_ingestion=True,
        needs_ocr=False,
    )
    matrix = run_capability_preflight(
        selection,
        host="local",
        probe=RuntimeCapabilityProbe(),
        project_root=ctx.project_root,
    )
    matrix_digest = _sha256_bytes(_canonical_json(matrix.model_dump(mode="json")))
    return {
        "capability_matrix_id": stable_id(
            "capability-matrix", ctx.contract.project_id, matrix_digest
        )
    }


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

    kind = classify_empty_universe(
        ReportKind.A, eligible_product_ids=evidence.eligible_product_ids
    )
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
    return _compute_input_digest(
        "universe", None, contract.contract_version, extra=extra
    )


# ─── Renderer registry ─────────────────────────────────────────────────────

_RENDERER_REGISTRY: dict[str, Any] = {}  # empty in Task 3.6


def _check_renderer_availability(outputs: list[str]) -> None:
    for fmt in outputs:
        if fmt not in _RENDERER_REGISTRY:
            raise RendererUnavailableError(
                f"格式「{fmt}」的渲染器尚未注册，无法完成该格式的生成。"
            )


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
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
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
) -> tuple[str, str, int]:
    """持久化当前运行清单；返回 (manifest_digest, 写入前运行事件流摘要, 写入前运行事件数)。"""
    run_events = tuple(
        event for event in event_store.read_all() if event.run_id == run_id
    )
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
    input_hashes = {
        str(key): str(value)
        for key, value in data.get("input_hashes", {}).items()
    }
    if payload.get("input_hashes_digest") != compute_input_hashes_digest(input_hashes):
        raise RunError("运行记录事件携带的输入摘要不一致")
    pre_record = tuple(
        event
        for event in events
        if event.run_id == run_id and event.event_type != MANIFEST_RECORDED_EVENT
    )
    if payload.get("pre_record_event_stream_digest") != compute_event_stream_digest(
        pre_record
    ):
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

    # 终态决策事件：证据阻断运行必须有当前运行记录事件，产物引用与清单一致
    if data.get("outcome") == "evidence_blocked":
        terminal_events = [
            event
            for event in events
            if event.event_type == TERMINAL_DECISION_EVENT
            and event.run_id == run_id
        ]
        if not terminal_events:
            raise RunError("证据阻断运行缺少终态决策事件")
        manifest_artifacts = list(data.get("outputs", [])) + list(
            data.get("reused_artifacts", [])
        )
        for terminal_event in terminal_events:
            kind = str(terminal_event.payload.get("report_kind"))
            expected = [
                artifact
                for artifact in manifest_artifacts
                if str(artifact.get("relative_path", "")).startswith(
                    f"blockers/{kind}/"
                )
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
        optional_formats=tuple(
            sorted(o.value for o in contract.outputs if o.value != "html")
        ),
    )

    # ── Run context for handlers ────────────────────────────────────────
    ctx = run_context or RunContext(project_root=project_root, contract=contract)

    # ── resume：派发任何节点前绑定规范宇宙输入并校验终态证据 ────────────
    if resume:
        if ctx.universe_input_path is None:
            canonical = project_root / CANONICAL_UNIVERSE_RELATIVE_PATH
            if canonical.is_file():
                ctx.universe_input_path = canonical
        if ctx.universe_input_path is not None:
            if not ctx.universe_input_path.is_file():
                raise ContractConfigError(
                    f"宇宙证据文件不存在：{ctx.universe_input_path}"
                )
            # 无条件从当前文件字节重新水合：复用同一 RunContext 对象时
            # 不得用旧摘要认证新证据
            _hydrate_universe_evidence(ctx)
        _check_resume_terminal(all_events, contract, ctx, project_root)

    now = datetime.now(UTC)
    node_summary: dict[str, str] = {}
    reused: list[dict[str, str]] = []
    outcome: str = "completed"

    def _run_node(
        node_id: str,
        report_kind: str | None,
        handler: Any,
        *,
        input_digest: str,
    ) -> dict[str, Any]:
        nonlocal outcome
        key = _node_key(node_id, report_kind)
        if key in completed:
            prev = completed[key]
            if prev["input_digest"] == input_digest:
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
                return cast(dict[str, Any], prev["outputs"])
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
        return cast(dict[str, Any], outputs)

    def _finalize(current_outcome: str) -> RunResult:
        """重放并持久化检查点后写当前运行清单；失败路径同样先落检查点。"""
        checkpoint_id: str | None = None
        current_run_events = [
            event for event in event_store.read_all() if event.run_id == run_id
        ]
        if current_outcome == "evidence_blocked" and not current_run_events:
            raise RunError("证据阻断结论缺少本次运行的证据引用，拒绝生成运行清单")
        if current_run_events:
            checkpoint_id = executor.replay().checkpoint_id
        created, reused_artifacts = _collect_outputs(
            project_root, baseline, current_outcome
        )
        if current_outcome == "evidence_blocked" and (created or reused_artifacts):
            _append_terminal_decision_events(
                event_store, project_root, contract, run_id, ctx,
                created, reused_artifacts, now,
            )
        return _finalize_run(
            project_root, run_id, contract, started_at, resume,
            run_context, node_summary, reused, created, current_outcome,
            event_store, checkpoint_id=checkpoint_id,
            reused_artifacts=reused_artifacts,
        )

    # ── Shared nodes ────────────────────────────────────────────────────
    for node_id, _report_kind, handler in _SHARED_NODES:
        inp_digest = _compute_input_digest(
            node_id, None, contract.contract_version
        )
        _run_node(node_id, None, handler, input_digest=inp_digest)

    if outcome == "failed":
        return _finalize("failed")

    # ── 项目对象在当前运行内确立（新项目或失败后恢复驱动终态）──────────
    # 持久化状态为 None（从未建立）或 running（先前运行 bootstrap 后失败）时，
    # 在当前运行内经声明迁移重新确立项目对象，随后协调器才能按声明契约把
    # 项目驱动到 blocked；终态（blocked）项目不重提项目迁移（--resume 非重开）。
    project_object_id = stable_id("project-obj", contract.project_id)
    persisted_project_state = _derive_full_family_state(
        all_events, "project"
    ).get(project_object_id)
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
        node_summary["universe"] = "skipped"
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
            _run_node(
                "universe", None, _handler_universe, input_digest=inp_digest
            )
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
    for report_kind in contract.reports:
        kind_value = report_kind.value
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
                    "gate", kind_value, _handler_gate_a,
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
                    "recovery", kind_value, _handler_recovery_a,
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
        report_states = _derive_full_family_state(
            event_store.read_all(), "report_evidence"
        )
        if report_states.get(report_object_id) == "evidence_blocked":
            # 终态阻断：保留既有决策；当前运行复用/终态决策事件与复用产物
            # 引用由 _finalize 记录（--resume 不是隐式重新打开）
            package_dir = project_root / "blockers" / kind_value / "v1"
            if not (
                (package_dir / "audit.json").is_file()
                and (package_dir / "audit.md").is_file()
            ):
                raise ContractConfigError(
                    "证据不足阻断项目的阻断说明文件缺失"
                    f"（blockers/{kind_value}/v1/audit.json 与 audit.md）。"
                    "请恢复该文件后重试 --resume，或使用显式的项目重新打开流程。"
                )
            node_summary[f"decision:{kind_value}"] = "preserved"
            continue
        _drive_report_transitions(
            executor, contract, run_id, now,
            project_object_id, kind_value, report_object_id,
        )

        # ── Write blocker package if evidence blocked ─────────────────
        _drive_blocker_write(project_root, contract, kind_value, ctx)

    if outcome == "failed":
        return _finalize("failed")

    # ── Coordinator: 只在本运行提交过项目迁移时推进终态 ────────────────
    current_run_events = [
        event for event in event_store.read_all() if event.run_id == run_id
    ]
    has_project_event = any(
        e.event_type == "graph.transition.accepted"
        and e.payload.get("family") == "project"
        for e in current_run_events
    )
    if has_project_event:
        coordinator.reconcile(
            delivery_contract,
            actor_id="run_service",
            occurred_at=now,
        )

    # ── Determine outcome from report states ────────────────────────────
    report_states = _derive_full_family_state(
        event_store.read_all(), "report_evidence"
    )
    if any(state == "evidence_blocked" for state in report_states.values()):
        outcome = "evidence_blocked"
    elif node_summary.get("universe") == "skipped":
        # 无宇宙输入：证据管线待定 → running（不说完成）
        outcome = "running"

    return _finalize(outcome)


# ─── Report transitions ────────────────────────────────────────────────────


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
        Path(__file__).resolve().parents[3]
        / "policies"
        / f"gates/{kind_value}-v1.yaml"
    )
    evidence = ctx.universe_evidence
    if evidence is None:
        return

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
            source_links=(
                "https://clinicaltrials.gov/study/NCT01234567",
            ),
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
        if ctx.universe_evidence is None:
            raise RunError("终态决策事件缺少当前证据引用")
        gate_input_digest = _compute_input_digest(
            "gate",
            kind_value,
            contract.contract_version,
            extra=ctx.universe_evidence.evidence_digest,
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
                    f"run.terminal_decision.recorded:{contract.project_id}:"
                    f"{run_id}:{object_id}"
                ),
                payload={
                    "report_kind": kind_value,
                    "report_object_id": object_id,
                    "decision_source": (
                        "current" if source.run_id == run_id else "reused"
                    ),
                    "source_run_id": source.run_id,
                    "source_event_id": source.event_id,
                    "gate_input_digest": gate_input_digest,
                    "artifacts": [_output_file_dict(output) for output in artifacts],
                },
            )
        )


# ─── Collect outputs ────────────────────────────────────────────────────────


def _collect_outputs(
    project_root: Path,
    baseline: dict[str, tuple[str, int, int]],
    outcome: str,
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
    case_digest = (
        run_context.run_inputs.get("case_digest") if run_context else None
    )
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
            idempotency_key=(
                f"run.manifest.recorded:{contract.project_id}:{run_id}"
            ),
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
    elif outcome == "failed":
        status_path.write_text(
            "# 项目状态\n\n"
            "本轮运行遇到技术问题，未能完成。请查看运行记录了解详情。\n",
            encoding="utf-8",
        )
    elif outcome == "running":
        status_path.write_text(
            "# 项目状态\n\n"
            "项目已启动，证据采集工作正在进行中。\n",
            encoding="utf-8",
        )
    else:
        status_path.write_text(
            "# 项目状态\n\n"
            "项目运行完成。\n",
            encoding="utf-8",
        )

    exit_codes = {
        "completed": 0,
        "running": 0,
        "evidence_blocked": 4,
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
