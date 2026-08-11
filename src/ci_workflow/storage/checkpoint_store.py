from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.event_store import EventStore, StoredWorkflowEvent

_SAFE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class CheckpointIntegrityError(RuntimeError):
    """检查点不能由当前规范事件流安全恢复。"""


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
        raise CheckpointIntegrityError("检查点状态必须是有限、可序列化的 JSON") from error


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("检查点字段不能为空")
    return normalized


class WorkflowCheckpoint(BaseModel):
    """可由事件流验证的规范项目检查点。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    checkpoint_id: str
    project_id: str
    run_id: str
    last_sequence: int = Field(ge=0)
    applied_event_ids: tuple[str, ...]
    state: dict[str, Any]
    state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_stream_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime

    @field_validator("checkpoint_id", "project_id", "run_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("created_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("检查点时间必须包含明确时区偏移")
        return value


Reducer = Callable[[dict[str, Any], StoredWorkflowEvent], dict[str, Any]]


class IdempotentSideEffect(Protocol):
    """可重放副作用。

    检查点只能在回调成功后保存；若进程在副作用完成后、检查点保存前中断，
    回调会再次收到同一事件，因此实现必须用 ``event.idempotency_key`` 去重。
    """

    def __call__(self, event: StoredWorkflowEvent) -> None: ...


class CheckpointStore:
    """只依赖规范事件流的项目检查点与重放服务。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.directory = self.project_root / "state" / "checkpoints"
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, checkpoint: WorkflowCheckpoint) -> Path:
        if _SAFE_TOKEN.fullmatch(checkpoint.run_id) is None:
            raise CheckpointIntegrityError("运行标识不能安全用于检查点文件名")
        name = (
            f"{checkpoint.run_id}--{checkpoint.last_sequence:012d}--"
            f"{checkpoint.checkpoint_id}.json"
        )
        return self.directory / name

    def save(self, checkpoint: WorkflowCheckpoint) -> Path:
        if checkpoint.state_digest != _digest(checkpoint.state):
            raise CheckpointIntegrityError("检查点状态摘要不匹配")
        encoded = _canonical_json(checkpoint.model_dump(mode="json"))
        path = self._path(checkpoint)
        if path.exists():
            if path.read_bytes() != encoded:
                raise CheckpointIntegrityError("同一检查点身份对应了不同内容")
            return path
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=self.directory
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def _read_path(self, path: Path) -> WorkflowCheckpoint:
        try:
            checkpoint = WorkflowCheckpoint.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as error:
            raise CheckpointIntegrityError("检查点文件无效") from error
        if self._path(checkpoint) != path:
            raise CheckpointIntegrityError("检查点文件名与内容身份不一致")
        if checkpoint.state_digest != _digest(checkpoint.state):
            raise CheckpointIntegrityError("检查点状态已被改写")
        return checkpoint

    def latest(self, *, run_id: str) -> WorkflowCheckpoint | None:
        if _SAFE_TOKEN.fullmatch(run_id) is None:
            raise CheckpointIntegrityError("运行标识不能安全用于检查点检索")
        candidates = sorted(self.directory.glob(f"{run_id}--*.json"))
        return None if not candidates else self._read_path(candidates[-1])

    def replay(
        self,
        event_store: EventStore,
        *,
        run_id: str,
        initial_state: dict[str, Any],
        reducer: Reducer,
        side_effect: IdempotentSideEffect,
    ) -> WorkflowCheckpoint:
        """重放尚未写入检查点的事件。

        ``side_effect`` 必须遵守 :class:`IdempotentSideEffect` 合同；事件流保证同一
        业务事件的幂等键稳定，但无法把外部副作用与本地检查点原子提交。
        """
        events = tuple(event for event in event_store.read_all() if event.run_id == run_id)
        current = self.latest(run_id=run_id)
        if current is None:
            if not events:
                raise CheckpointIntegrityError("没有属于该运行的规范事件，不能建立检查点")
            state = dict(initial_state)
            applied: list[str] = []
            last_sequence = 0
            project_ids = {event.project_id for event in events}
            if len(project_ids) != 1:
                raise CheckpointIntegrityError("同一运行的事件必须属于一个项目")
            project_id = next(iter(project_ids))
        else:
            state = dict(current.state)
            applied = list(current.applied_event_ids)
            last_sequence = current.last_sequence
            project_id = current.project_id
            if current.run_id != run_id:
                raise CheckpointIntegrityError("检查点运行身份不匹配")
            if current.event_stream_digest != event_store.stream_digest(
                through_sequence=last_sequence
            ):
                raise CheckpointIntegrityError("检查点引用的事件流前缀已变化")
            expected_ids = tuple(
                event.event_id
                for event in event_store.read_all()[:last_sequence]
                if event.run_id == run_id
            )
            if current.applied_event_ids != expected_ids:
                raise CheckpointIntegrityError("检查点事件列表与规范事件流不一致")

        new_events = tuple(event for event in events if event.sequence > last_sequence)
        if not new_events and current is not None:
            return current
        for event in new_events:
            if event.project_id != project_id:
                raise CheckpointIntegrityError("运行事件跨越了项目边界")
            state = reducer(state, event)
            _canonical_json(state)
            side_effect(event)
            applied.append(event.event_id)
            last_sequence = event.sequence

        state_digest = _digest(state)
        event_digest = event_store.stream_digest(through_sequence=last_sequence)
        checkpoint_id = stable_id(
            "checkpoint", project_id, run_id, str(last_sequence), state_digest, event_digest
        )
        checkpoint = WorkflowCheckpoint(
            schema_version="1.0",
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            run_id=run_id,
            last_sequence=last_sequence,
            applied_event_ids=tuple(applied),
            state=state,
            state_digest=state_digest,
            event_stream_digest=event_digest,
            created_at=datetime.now(UTC),
        )
        self.save(checkpoint)
        return checkpoint
