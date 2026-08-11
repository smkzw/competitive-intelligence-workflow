from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ci_workflow.domain.ids import stable_id

_SHA256 = re.compile(r"[0-9a-f]{64}")


class SnapshotIntegrityError(RuntimeError):
    """快照身份、路径、内容或摘要不一致。"""


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
        raise SnapshotIntegrityError("快照必须是有限、可序列化的 JSON") from error


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("快照字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("快照时间必须包含明确时区偏移")
    return value


class EvidenceSnapshotManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    project_id: str
    contract_version: int = Field(ge=1)
    data_cutoff: datetime
    source_version_ids: tuple[str, ...] = Field(min_length=1)
    fragment_ids: tuple[str, ...] = Field(min_length=1)
    fact_version_ids: tuple[str, ...] = Field(min_length=1)
    created_at: datetime

    @field_validator("project_id")
    @classmethod
    def _project_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("source_version_ids", "fragment_ids", "fact_version_ids")
    @classmethod
    def _ids_are_unique_and_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("快照标识列表不得重复")
        return normalized

    @field_validator("data_cutoff", "created_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class ReportSnapshotManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    project_id: str
    contract_version: int = Field(ge=1)
    report: Literal["A", "B", "C"]
    report_version: str
    data_cutoff: datetime
    evidence_snapshot_id: str
    claim_snapshot_id: str
    coverage_set_id: str
    claim_ids: tuple[str, ...] = Field(min_length=1)
    created_at: datetime

    @field_validator(
        "project_id",
        "report_version",
        "evidence_snapshot_id",
        "claim_snapshot_id",
        "coverage_set_id",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("claim_ids")
    @classmethod
    def _claims_are_unique_and_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("报告快照声明不得重复")
        return normalized

    @field_validator("data_cutoff", "created_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class LockedSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    kind: Literal["evidence", "report"]
    report: Literal["A", "B", "C"] | None
    sha256: str
    relative_path: str
    byte_size: int = Field(ge=1)

    @field_validator("snapshot_id", "relative_path")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("快照摘要必须是小写 SHA-256")
        return value


class SnapshotStore:
    """项目内不可覆盖、按规范 JSON 内容寻址的证据与报告快照。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def _lock(
        self,
        *,
        kind: Literal["evidence", "report"],
        report: Literal["A", "B", "C"] | None,
        payload: dict[str, Any],
    ) -> LockedSnapshot:
        encoded = _canonical_json(payload)
        digest = hashlib.sha256(encoded).hexdigest()
        identity_parts = (digest,) if report is None else (report, digest)
        snapshot_id = stable_id(f"{kind}-snapshot", *identity_parts)
        if kind == "evidence":
            relative = PurePosixPath("snapshots", "evidence", f"{snapshot_id}.json")
        else:
            if report is None:
                raise SnapshotIntegrityError("报告快照必须声明报告类型")
            relative = PurePosixPath(
                "snapshots", "reports", report, f"{snapshot_id}.json"
            )
        path = self.project_root.joinpath(*relative.parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != encoded:
                raise SnapshotIntegrityError("同一快照身份对应了不同内容")
        else:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
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
        return LockedSnapshot(
            snapshot_id=snapshot_id,
            kind=kind,
            report=report,
            sha256=digest,
            relative_path=relative.as_posix(),
            byte_size=len(encoded),
        )

    def lock_evidence_snapshot(self, manifest: dict[str, Any]) -> LockedSnapshot:
        validated = EvidenceSnapshotManifest.model_validate(manifest)
        return self._lock(
            kind="evidence", report=None, payload=validated.model_dump(mode="json")
        )

    def lock_report_snapshot(
        self, *, report: Literal["A", "B", "C"], manifest: dict[str, Any]
    ) -> LockedSnapshot:
        validated = ReportSnapshotManifest.model_validate(manifest)
        if validated.report != report:
            raise SnapshotIntegrityError("报告快照的路径和报告类型不一致")
        return self._lock(
            kind="report", report=report, payload=validated.model_dump(mode="json")
        )

    def _resolve(self, relative_path: str) -> Path:
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in relative_path:
            raise SnapshotIntegrityError("快照路径必须是项目内相对路径")
        path = self.project_root.joinpath(*pure.parts).resolve()
        if not path.is_relative_to(self.project_root):
            raise SnapshotIntegrityError("快照路径离开了项目目录")
        return path

    def read(self, snapshot: LockedSnapshot) -> dict[str, Any]:
        path = self._resolve(snapshot.relative_path)
        try:
            encoded = path.read_bytes()
        except OSError as error:
            raise SnapshotIntegrityError("快照文件不存在或不可读") from error
        if len(encoded) != snapshot.byte_size:
            raise SnapshotIntegrityError("快照字节数不匹配")
        if hashlib.sha256(encoded).hexdigest() != snapshot.sha256:
            raise SnapshotIntegrityError("快照摘要不匹配")
        try:
            payload = json.loads(encoded)
        except json.JSONDecodeError as error:
            raise SnapshotIntegrityError("快照不是有效 JSON") from error
        if not isinstance(payload, dict):
            raise SnapshotIntegrityError("快照根节点必须是对象")
        if snapshot.kind == "evidence":
            EvidenceSnapshotManifest.model_validate(payload)
        else:
            validated = ReportSnapshotManifest.model_validate(payload)
            if validated.report != snapshot.report:
                raise SnapshotIntegrityError("报告快照身份不匹配")
        return payload
