from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventStoreError(RuntimeError):
    """规范事件流缺失、损坏或无法安全追加。"""


class EventConflictError(EventStoreError):
    """同一事件或幂等键被另一份业务载荷复用。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("事件字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("事件时间必须包含明确时区偏移")
    return value


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
        raise EventStoreError("事件载荷必须是有限、可序列化的 JSON") from error


class WorkflowEvent(BaseModel):
    """调用方提交的业务事件；序号与摘要由事件库分配。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    event_id: str
    project_id: str
    run_id: str
    event_type: str
    occurred_at: datetime
    actor_id: str
    idempotency_key: str
    payload: dict[str, Any]

    @field_validator(
        "event_id",
        "project_id",
        "run_id",
        "event_type",
        "actor_id",
        "idempotency_key",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("occurred_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class StoredWorkflowEvent(WorkflowEvent):
    """事件流中带连续序号与内容摘要的不可变记录。"""

    sequence: int = Field(ge=1)
    event_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def _event_body(event: WorkflowEvent, sequence: int) -> dict[str, Any]:
    return {
        **event.model_dump(mode="json"),
        "sequence": sequence,
    }


def _event_digest(event: WorkflowEvent, sequence: int) -> str:
    return hashlib.sha256(_canonical_json(_event_body(event, sequence))).hexdigest()


def _idempotency_fingerprint(event: WorkflowEvent) -> str:
    material = {
        "project_id": event.project_id,
        "run_id": event.run_id,
        "event_type": event.event_type,
        "idempotency_key": event.idempotency_key,
        "payload": event.payload,
    }
    return hashlib.sha256(_canonical_json(material)).hexdigest()


class EventStore:
    """项目内唯一的追加式 `events/events.jsonl` 事件真源。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.path = self.project_root / "events" / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def read_all(self) -> tuple[StoredWorkflowEvent, ...]:
        records: list[StoredWorkflowEvent] = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise EventStoreError("无法读取规范事件流") from error
        for expected_sequence, line in enumerate(lines, start=1):
            if not line.strip():
                raise EventStoreError("规范事件流不得包含空行")
            try:
                payload = json.loads(line)
                record = StoredWorkflowEvent.model_validate(payload)
            except (json.JSONDecodeError, ValueError) as error:
                raise EventStoreError("规范事件流包含无效记录") from error
            if record.sequence != expected_sequence:
                raise EventStoreError("规范事件序号不连续")
            source = WorkflowEvent.model_validate(
                record.model_dump(exclude={"sequence", "event_digest"})
            )
            if record.event_digest != _event_digest(source, record.sequence):
                raise EventStoreError("规范事件摘要不匹配")
            records.append(record)
        return tuple(records)

    def append(self, event: WorkflowEvent) -> StoredWorkflowEvent:
        # Validate JSON before consulting existing records so unsupported values fail closed.
        _canonical_json(event.model_dump(mode="json"))
        existing = self.read_all()
        fingerprint = _idempotency_fingerprint(event)
        for record in existing:
            source = WorkflowEvent.model_validate(
                record.model_dump(exclude={"sequence", "event_digest"})
            )
            if record.event_id == event.event_id:
                if source == event:
                    return record
                raise EventConflictError("同一事件标识对应了不同内容")
            if record.idempotency_key == event.idempotency_key:
                if _idempotency_fingerprint(source) == fingerprint:
                    return record
                raise EventConflictError("同一幂等键对应了不同业务载荷")

        sequence = len(existing) + 1
        record = StoredWorkflowEvent(
            **event.model_dump(),
            sequence=sequence,
            event_digest=_event_digest(event, sequence),
        )
        encoded = _canonical_json(record.model_dump(mode="json"))
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(descriptor, encoded)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise EventStoreError("无法追加规范事件") from error
        return record

    def stream_digest(self, *, through_sequence: int | None = None) -> str:
        records = self.read_all()
        selected = (
            records
            if through_sequence is None
            else tuple(record for record in records if record.sequence <= through_sequence)
        )
        if through_sequence is not None and len(selected) != through_sequence:
            raise EventStoreError("检查点引用了不存在的事件序号")
        material = [record.event_digest for record in selected]
        return hashlib.sha256(_canonical_json(material)).hexdigest()
