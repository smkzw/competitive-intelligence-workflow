"""Task 3.4 本地确定性执行器：基于既有 EventStore/CheckpointStore 编排图。

- 迁移请求 → 声明边/守卫求值 → 接受或拒绝规范事件（拒绝也可审计）；
- 节点完成 → 按节点合同校验后写规范事件；
- 事件流 → 规范状态（graph_reducer）；检查点重放由 CheckpointStore 承担；
- publish/move/approve/delete 四类副作用以事件幂等键 + 目标身份去重，
  配合文件系统幂等与 JSONL 账本，崩溃窗口重放不会重复执行。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.definitions import node_contract
from ci_workflow.graph.reducer import derive_side_effect_target, graph_reducer
from ci_workflow.graph.registry import TRANSITION_REGISTRY
from ci_workflow.graph.state import FAMILY_DEFAULT_STATES, initial_state
from ci_workflow.graph.types import (
    DeclaredEdge,
    TransitionRequest,
    validate_typed_outputs,
)
from ci_workflow.storage.checkpoint_store import CheckpointStore, WorkflowCheckpoint
from ci_workflow.storage.event_store import (
    EventConflictError,
    EventStore,
    StoredWorkflowEvent,
    WorkflowEvent,
)


class SideEffectError(RuntimeError):
    """副作用无法安全执行（幂等重放无法收敛）。"""


class SideEffectConflictError(SideEffectError):
    """同一幂等键/目标身份被另一份业务载荷复用。"""


def _canonical_json(value: object) -> bytes:
    try:
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
    except (TypeError, ValueError) as error:
        raise SideEffectError("副作用载荷必须是有限、可序列化的 JSON") from error


def _payload_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_copy(source: Path, destination: Path) -> None:
    """原子复制：临时文件 + fsync + os.replace。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(source.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _append_jsonl(path: Path, record: dict[str, str]) -> None:
    encoded = _canonical_json(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        try:
            os.write(descriptor, encoded)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise SideEffectError("无法追加副作用账本") from error


def _load_jsonl(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if not path.exists():
        return records
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SideEffectError("无法读取副作用账本") from error
    for line in lines:
        if not line.strip():
            continue
        payload = json.loads(line)
        records.append({key: str(value) for key, value in payload.items()})
    return records


class IdempotentSideEffects:
    """publish/move/approve/delete 四类可重放副作用。

    去重键 = 事件幂等键 + 目标身份；操作本身对文件系统幂等，
    配合 state/side_effect_ledger.jsonl 账本与审批账本，
    崩溃窗口重放不会重复发布、移动、批准或删除。
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.ledger_path = self.project_root / "state" / "side_effect_ledger.jsonl"
        self.approvals_path = self.project_root / "state" / "approvals.jsonl"
        self._ledger = _load_jsonl(self.ledger_path)

    def __call__(self, event: StoredWorkflowEvent) -> None:
        operations: dict[str, Callable[[StoredWorkflowEvent], None]] = {
            "artifact.publish": self._publish,
            "artifact.move": self._move,
            "revision.approve": self._approve,
            "artifact.delete": self._delete,
        }
        operation = operations.get(event.event_type)
        if operation is not None:
            operation(event)

    def _relative(self, raw: str) -> Path:
        """相对项目根的路径解析；绝对路径或越界一律失败关闭。"""
        candidate = Path(raw)
        if candidate.is_absolute():
            raise SideEffectError("副作用路径必须是相对路径")
        resolved = (self.project_root / candidate).resolve()
        if not resolved.is_relative_to(self.project_root):
            raise SideEffectError("副作用路径越界")
        return resolved

    def _guard_ledger(
        self,
        *,
        event: StoredWorkflowEvent,
        target_identity: str,
        payload_digest: str,
    ) -> bool:
        """账本去重：已应用（同载荷）→ True 跳过；同键不同载荷 → 冲突。"""
        for entry in self._ledger:
            if (
                entry.get("op") == event.event_type
                and entry.get("idempotency_key") == event.idempotency_key
                and entry.get("target_identity") == target_identity
            ):
                if entry.get("payload_digest") != payload_digest:
                    raise SideEffectConflictError(
                        f"同一幂等键/目标身份对应了不同副作用载荷: {event.idempotency_key}"
                    )
                return True
        return False

    def _record(
        self,
        *,
        event: StoredWorkflowEvent,
        target_identity: str,
        payload_digest: str,
    ) -> None:
        entry = {
            "op": event.event_type,
            "event_id": event.event_id,
            "idempotency_key": event.idempotency_key,
            "target_identity": target_identity,
            "payload_digest": payload_digest,
        }
        _append_jsonl(self.ledger_path, entry)
        self._ledger.append(entry)

    def _publish(self, event: StoredWorkflowEvent) -> None:
        payload = event.payload
        target_identity = derive_side_effect_target(event.event_type, payload)
        digest = _payload_digest(payload)
        if self._guard_ledger(event=event, target_identity=target_identity, payload_digest=digest):
            return
        source = self._relative(str(payload["source_path"]))
        destination = self._relative(str(payload["destination_path"]))
        if destination.exists():
            if source.exists() and _file_digest(destination) != _file_digest(source):
                raise SideEffectConflictError("发布目标已存在且内容不同")
        else:
            if not source.exists():
                raise SideEffectError("发布源不存在")
            _atomic_copy(source, destination)
        self._record(event=event, target_identity=target_identity, payload_digest=digest)

    def _move(self, event: StoredWorkflowEvent) -> None:
        payload = event.payload
        target_identity = derive_side_effect_target(event.event_type, payload)
        digest = _payload_digest(payload)
        if self._guard_ledger(event=event, target_identity=target_identity, payload_digest=digest):
            return
        source = self._relative(str(payload["source_path"]))
        destination = self._relative(str(payload["destination_path"]))
        if source.exists() and destination.exists():
            if _file_digest(source) != _file_digest(destination):
                raise SideEffectConflictError("移动目标已存在且内容不同")
            source.unlink()
        elif source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
        elif not destination.exists():
            raise SideEffectError("移动源与目标均不存在")
        self._record(event=event, target_identity=target_identity, payload_digest=digest)

    def _approve(self, event: StoredWorkflowEvent) -> None:
        payload = event.payload
        approval_id = derive_side_effect_target(event.event_type, payload)
        decision = str(payload["decision"])
        digest = _payload_digest(payload)
        if self._guard_ledger(event=event, target_identity=approval_id, payload_digest=digest):
            return
        approvals = _load_jsonl(self.approvals_path)
        existing = next(
            (record for record in approvals if record.get("approval_id") == approval_id),
            None,
        )
        if existing is not None:
            if existing.get("decision") != decision:
                raise SideEffectConflictError(f"同一审批 ID 对应了不同决定: {approval_id}")
        else:
            _append_jsonl(
                self.approvals_path,
                {
                    "approval_id": approval_id,
                    "decision": decision,
                    "approver": str(payload.get("approver", "")),
                },
            )
        self._record(event=event, target_identity=approval_id, payload_digest=digest)

    def _delete(self, event: StoredWorkflowEvent) -> None:
        payload = event.payload
        target_identity = derive_side_effect_target(event.event_type, payload)
        digest = _payload_digest(payload)
        if self._guard_ledger(event=event, target_identity=target_identity, payload_digest=digest):
            return
        path = self._relative(str(payload["path"]))
        if path.exists():
            path.unlink()
        self._record(event=event, target_identity=target_identity, payload_digest=digest)


class GraphExecutor:
    """本地确定性执行器：迁移请求/节点完成 → 规范事件 → 状态与检查点。"""

    def __init__(
        self,
        project_root: Path,
        *,
        run_id: str,
        event_store: EventStore | None = None,
        checkpoint_store: CheckpointStore | None = None,
        side_effects: IdempotentSideEffects | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.run_id = run_id
        self.store = event_store or EventStore(self.project_root)
        self.checkpoints = checkpoint_store or CheckpointStore(self.project_root)
        self.side_effects = side_effects or IdempotentSideEffects(self.project_root)

    # ── 迁移 ───────────────────────────────────────────────────────────────
    def submit(self, request: TransitionRequest) -> StoredWorkflowEvent:
        """把一次迁移尝试归约为接受或拒绝规范事件。

        执行器产生的全部事件都属于 self.run_id，且锚定项目根已确立的项目身份。
        失败关闭顺序：精确重放预检 → 项目身份 → 运行身份 → 未声明边 →
        trigger → 规范当前状态 → 结构化守卫。每次尝试都追加一个确定性事件。
        """
        if request.family not in TRANSITION_REGISTRY.families():
            raise ValueError(f"未知状态族: {request.family}")
        request_digest = _payload_digest(request.model_dump(mode="json"))
        established = self._established_project()
        event_project = established if established is not None else request.project_id
        event_run = self.run_id
        event_id = stable_id(
            "graph-transition",
            event_project,
            event_run,
            request.family,
            request.object_id,
            request.request_id,
        )

        # 精确重放预检：同一请求身份已产生事件则直接返回，不再对已变化的状态重求值
        existing = self._existing_transition_event(event_id)
        if existing is not None:
            if existing.payload.get("request_digest") == request_digest:
                return existing
            raise EventConflictError("同一请求标识对应了不同内容")

        # 项目身份：项目根一旦确立一个项目，其他项目的请求失败关闭
        if established is not None and request.project_id != established:
            event = self._rejection_event(
                request,
                reason="project_mismatch",
                request_digest=request_digest,
                event_id=event_id,
                event_project=event_project,
                event_run=event_run,
                expected_project_id=established,
            )
            return self.store.append(event)

        # 运行身份必须与执行器一致；拒绝事件仍存储在执行器运行下
        if request.run_id != self.run_id:
            event = self._rejection_event(
                request,
                reason="run_mismatch",
                request_digest=request_digest,
                event_id=event_id,
                event_project=event_project,
                event_run=event_run,
                expected_run_id=self.run_id,
            )
            return self.store.append(event)

        edge = TRANSITION_REGISTRY.declared(request.family, request.from_state, request.to_state)
        if edge is None:
            event = self._rejection_event(
                request,
                reason="undeclared_transition",
                request_digest=request_digest,
                event_id=event_id,
                event_project=event_project,
                event_run=event_run,
            )
            return self.store.append(event)

        # trigger 必须与声明边一致
        if request.trigger != edge.trigger:
            event = self._rejection_event(
                request,
                reason="trigger_mismatch",
                guard_id=edge.guard_id,
                request_digest=request_digest,
                event_id=event_id,
                event_project=event_project,
                event_run=event_run,
                expected_trigger=edge.trigger,
            )
            return self.store.append(event)

        # from_state 必须等于该 family/object 在本运行的规范当前状态
        expected_state = self._canonical_current_state(request.family, request.object_id)
        if request.from_state != expected_state:
            event = self._rejection_event(
                request,
                reason="current_state_mismatch",
                guard_id=edge.guard_id,
                request_digest=request_digest,
                event_id=event_id,
                event_project=event_project,
                event_run=event_run,
                expected_state=expected_state,
            )
            return self.store.append(event)

        guard = TRANSITION_REGISTRY.evaluate_guard(
            edge.guard_id,
            request.evidence,
            target_family=request.family,
            target_object_id=request.object_id,
        )
        if guard.allowed:
            event = self._acceptance_event(
                request,
                edge,
                request_digest=request_digest,
                event_id=event_id,
                event_project=event_project,
                event_run=event_run,
            )
        else:
            event = self._rejection_event(
                request,
                reason="guard_failed",
                guard_id=edge.guard_id,
                guard_reason=guard.reason,
                request_digest=request_digest,
                event_id=event_id,
                event_project=event_project,
                event_run=event_run,
            )
        return self.store.append(event)

    def _established_project(self) -> str | None:
        """项目根已确立的项目身份；无事件 → None，多项目混杂 → 失败关闭。"""
        projects = {event.project_id for event in self.store.read_all()}
        if not projects:
            return None
        if len(projects) > 1:
            raise ValueError("项目根已混入多个项目事件")
        return next(iter(projects))

    def _existing_transition_event(self, event_id: str) -> StoredWorkflowEvent | None:
        """按事件标识查找已归约的迁移事件（接受或拒绝皆命中）。"""
        for record in self.store.read_all():
            if record.event_id == event_id:
                return record
        return None

    def _canonical_current_state(self, family: str, object_id: str) -> str | None:
        """family/object 在本运行的规范当前状态；未见对象取固定类型化起始状态。"""
        reduced = self.state()
        current = reduced.get(family, {}).get(object_id)
        if current is None:
            return FAMILY_DEFAULT_STATES[family]
        return str(current)

    def _acceptance_event(
        self,
        request: TransitionRequest,
        edge: DeclaredEdge,
        *,
        event_id: str,
        event_project: str,
        event_run: str,
        request_digest: str,
    ) -> WorkflowEvent:
        return WorkflowEvent(
            schema_version="1.0",
            event_id=event_id,
            project_id=event_project,
            run_id=event_run,
            event_type="graph.transition.accepted",
            occurred_at=request.occurred_at,
            actor_id=request.actor_id,
            idempotency_key=(
                f"graph.transition:{event_run}:{request.family}:{request.object_id}:{request.request_id}"
            ),
            payload={
                "family": request.family,
                "object_id": request.object_id,
                "from_state": request.from_state,
                "to_state": request.to_state,
                "trigger": request.trigger,
                "guard_id": edge.guard_id,
                "guard_evidence": request.evidence,
                "request_digest": request_digest,
            },
        )

    def _rejection_event(
        self,
        request: TransitionRequest,
        *,
        reason: str,
        request_digest: str,
        event_id: str,
        event_project: str,
        event_run: str,
        guard_id: str | None = None,
        guard_reason: str | None = None,
        expected_project_id: str | None = None,
        expected_run_id: str | None = None,
        expected_trigger: str | None = None,
        expected_state: str | None = None,
    ) -> WorkflowEvent:
        payload: dict[str, Any] = {
            "family": request.family,
            "object_id": request.object_id,
            "from_state": request.from_state,
            "to_state": request.to_state,
            "trigger": request.trigger,
            "reason": reason,
            "guard_evidence": request.evidence,
            "request_digest": request_digest,
        }
        if guard_id is not None:
            payload["guard_id"] = guard_id
        if guard_reason is not None:
            payload["guard_reason"] = guard_reason
        if expected_project_id is not None:
            payload["requested_project_id"] = request.project_id
            payload["expected_project_id"] = expected_project_id
        if expected_run_id is not None:
            payload["requested_run_id"] = request.run_id
            payload["expected_run_id"] = expected_run_id
        if expected_trigger is not None:
            payload["expected_trigger"] = expected_trigger
        if expected_state is not None:
            payload["expected_state"] = expected_state
        return WorkflowEvent(
            schema_version="1.0",
            event_id=event_id,
            project_id=event_project,
            run_id=event_run,
            event_type="graph.transition.rejected",
            occurred_at=request.occurred_at,
            actor_id=request.actor_id,
            idempotency_key=(
                f"graph.transition:{event_run}:{request.family}:{request.object_id}:{request.request_id}"
            ),
            payload=payload,
        )

    # ── 节点完成 ───────────────────────────────────────────────────────────
    def complete_node(
        self,
        node_id: str,
        *,
        outputs: dict[str, Any],
        input_digest: str,
        report_kind: str | None = None,
        project_id: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredWorkflowEvent:
        """按节点合同校验输出并写完成事件；身份锚定项目/运行/节点/输入摘要。

        幂等身份 = project_id + run_id + node_id + report-or-shared + input_digest；
        同一输入身份同一输出（更晚时间戳）返回原事件；同一输入身份输出漂移
        失败关闭；不同输入摘要可产生新完成；不同运行保持独立。
        """
        contract = node_contract(node_id)
        if not isinstance(input_digest, str) or not input_digest.strip():
            raise ValueError("input_digest 不能为空")
        normalized_digest = " ".join(input_digest.split())
        if contract.scope in ("report", "artifact"):
            if report_kind not in ("A", "B", "C"):
                raise ValueError(f"{node_id} 需要报告类型 A/B/C")
        elif report_kind is not None:
            raise ValueError(f"{node_id} 是 shared 节点，不接受 report_kind")
        # 项目身份：项目根一旦确立一个项目，其他项目的完成调用写前失败关闭
        established = self._established_project()
        if established is not None and project_id != established:
            raise ValueError(
                f"项目身份不匹配: requested={project_id} expected={established}"
            )
        declared_names = {field.name for field in contract.typed_outputs}
        if set(outputs) != declared_names:
            raise ValueError(
                f"{node_id} 输出与声明不符: {sorted(set(outputs) ^ declared_names)}"
            )
        if not contract.completion_predicate(outputs):
            raise ValueError(f"{node_id} 输出未满足完成谓词（不完整或为空）")
        validate_typed_outputs(contract, outputs)
        completion_digest = _payload_digest(
            {
                "node_id": node_id,
                "report_kind": report_kind,
                "input_digest": normalized_digest,
                "outputs": outputs,
            }
        )
        event_id = stable_id(
            "graph-node-completed",
            project_id,
            self.run_id,
            node_id,
            report_kind or "shared",
            normalized_digest,
        )
        existing = self._existing_completion_event(event_id)
        if existing is not None:
            if existing.payload.get("completion_digest") == completion_digest:
                return existing
            raise EventConflictError("同一输入身份对应了不同完成内容")
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=event_id,
            project_id=project_id,
            run_id=self.run_id,
            event_type="graph.node.completed",
            occurred_at=occurred_at,
            actor_id=actor_id,
            idempotency_key=(
                f"graph.node.completed:{project_id}:{self.run_id}:{node_id}:"
                f"{report_kind or 'shared'}:{normalized_digest}"
            ),
            payload={
                "node_id": node_id,
                "report_kind": report_kind,
                "scope": contract.scope,
                "input_digest": normalized_digest,
                "completion_digest": completion_digest,
                "outputs": outputs,
            },
        )
        return self.store.append(event)

    def _existing_completion_event(self, event_id: str) -> StoredWorkflowEvent | None:
        """按事件标识查找已写入的节点完成事件。"""
        for record in self.store.read_all():
            if record.event_id == event_id:
                return record
        return None

    # ── 状态与检查点 ───────────────────────────────────────────────────────
    def state(self) -> dict[str, Any]:
        """把本运行的全部规范事件归约为规范状态。"""
        state = initial_state()
        for event in self.store.read_all():
            if event.run_id != self.run_id:
                continue
            state = graph_reducer(state, event)
        return state

    def replay(self) -> WorkflowCheckpoint:
        """重放尚未写入检查点的事件；副作用由 IdempotentSideEffects 去重。"""
        return self.checkpoints.replay(
            self.store,
            run_id=self.run_id,
            initial_state=initial_state(),
            reducer=graph_reducer,
            side_effect=self.side_effects,
        )
