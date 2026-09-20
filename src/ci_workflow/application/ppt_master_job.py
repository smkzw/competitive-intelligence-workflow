"""PPT Master 串行作业、阶段收据与可恢复中断合同。"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ReportKind = Literal["A", "B", "C"]
JobState = Literal[
    "created",
    "snapshot_locked",
    "running",
    "paused",
    "failed",
    "ready_for_acceptance",
    "accepted",
    "rejected",
    "cancelled",
]
ReceiptStatus = Literal["committed", "failed"]

STAGES: tuple[tuple[str, str], ...] = (
    ("initialize", "初始化"),
    ("content_design_lock", "内容策略与设计锁定"),
    ("page_svg", "逐页 SVG"),
    ("quality_check", "质量检查"),
    ("speaker_notes", "备注"),
    ("closeout", "收尾处理"),
    ("native_export", "原生导出"),
    ("editability_check", "可编辑性核验"),
    ("visual_check", "原分辨率逐页视觉检查"),
)
STAGE_IDS = tuple(stage_id for stage_id, _ in STAGES)
_SHA256_LENGTH = 64


class PptMasterJobError(RuntimeError):
    """作业合同在产生下一阶段副作用前拒绝请求。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


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


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含明确时区")
    return value


def _digest(value: str) -> str:
    if len(value) != _SHA256_LENGTH or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("摘要必须是 64 位小写 SHA-256")
    return value


class LockedReportSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str = Field(min_length=1)
    report: ReportKind
    report_version: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    snapshot_sha256: str
    claim_snapshot_id: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    coverage_set_id: str = Field(min_length=1)
    locked_at: datetime

    _validate_digest = field_validator("snapshot_sha256")(_digest)
    _validate_time = field_validator("locked_at")(_aware)


class StageArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    sha256: str
    byte_size: int = Field(ge=1)

    @field_validator("relative_path")
    @classmethod
    def _project_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("阶段产物必须使用项目内 POSIX 相对路径")
        if not value.strip():
            raise ValueError("阶段产物路径不能为空")
        return value

    _validate_digest = field_validator("sha256")(_digest)


class StageReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report: ReportKind
    snapshot_id: str = Field(min_length=1)
    snapshot_sha256: str
    stage_id: str
    stage_order: int = Field(ge=1, le=len(STAGES))
    attempt: int = Field(ge=1)
    input_digest: str
    output_digest: str
    predecessor_receipt_id: str | None
    artifacts: tuple[StageArtifact, ...]
    status: ReceiptStatus
    committed_at: datetime
    receipt_sha256: str
    failure_reason: str | None = None

    @field_validator("snapshot_sha256", "input_digest", "output_digest", "receipt_sha256")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _digest(value)

    @field_validator("committed_at")
    @classmethod
    def _time_is_aware(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def _stage_and_failure_are_consistent(self) -> StageReceipt:
        expected_stage = STAGE_IDS[self.stage_order - 1]
        if self.stage_id != expected_stage:
            raise ValueError("阶段标识与固定顺序不一致")
        if self.status == "failed" and not (self.failure_reason or "").strip():
            raise ValueError("失败收据必须说明原因")
        if self.status == "committed" and self.failure_reason is not None:
            raise ValueError("成功收据不能携带失败原因")
        if self.status == "committed" and not self.artifacts:
            raise ValueError("成功收据必须绑定至少一个阶段产物")
        if self.output_digest != stage_output_digest(self.artifacts):
            raise ValueError("阶段输出摘要与产物清单不一致")
        if self.receipt_sha256 != receipt_digest(self):
            raise ValueError("阶段收据摘要不一致")
        return self


class PptMasterJob(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    contract_version: Literal["8.7"]
    job_id: str = Field(min_length=1)
    snapshot: LockedReportSnapshot
    state: JobState
    next_stage: str | None
    active_stage: str | None = None
    receipts: tuple[StageReceipt, ...]
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator("expires_at", "created_at", "updated_at")
    @classmethod
    def _times_are_aware(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def _receipt_chain_is_consistent(self) -> PptMasterJob:
        committed = [receipt for receipt in self.receipts if receipt.status == "committed"]
        expected_order = 1
        predecessor_id: str | None = None
        seen_receipts: set[str] = set()
        for receipt in self.receipts:
            if receipt.receipt_id in seen_receipts:
                raise ValueError("阶段收据标识不得重复")
            seen_receipts.add(receipt.receipt_id)
            if (
                receipt.job_id != self.job_id
                or receipt.project_id != self.snapshot.project_id
                or receipt.report != self.snapshot.report
                or receipt.snapshot_id != self.snapshot.snapshot_id
                or receipt.snapshot_sha256 != self.snapshot.snapshot_sha256
            ):
                raise ValueError("阶段收据与作业或锁定快照不一致")
            if receipt.status == "committed":
                if receipt.stage_order != expected_order:
                    raise ValueError("成功收据必须按固定阶段连续提交")
                if receipt.predecessor_receipt_id != predecessor_id:
                    raise ValueError("成功收据未连接到上一份成功收据")
                predecessor_id = receipt.receipt_id
                expected_order += 1

        derived_next = None if len(committed) == len(STAGES) else STAGE_IDS[len(committed)]
        if self.next_stage != derived_next:
            raise ValueError("恢复指针必须由最后一份成功收据推导")
        if self.state == "ready_for_acceptance" and derived_next is not None:
            raise ValueError("阶段未全部完成，不能进入待独立验收")
        if derived_next is None and self.state not in {
            "ready_for_acceptance",
            "accepted",
            "rejected",
            "cancelled",
        }:
            raise ValueError("九阶段完成后只能进入验收或终态")
        if self.state == "running":
            if self.active_stage != self.next_stage or self.active_stage is None:
                raise ValueError("运行中的阶段必须等于恢复指针")
        elif self.active_stage is not None:
            raise ValueError("非运行状态不能保留活动阶段")
        if self.updated_at < self.created_at:
            raise ValueError("更新时间不得早于创建时间")
        return self


class ExecutionLease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    lock_name: Literal["ppt_master_global"]
    job_id: str
    project_id: str
    report: ReportKind
    snapshot_id: str
    owner_id: str
    acquired_at: datetime
    expires_at: datetime

    @field_validator("acquired_at", "expires_at")
    @classmethod
    def _times_are_aware(cls, value: datetime) -> datetime:
        return _aware(value)


def stage_output_digest(artifacts: tuple[StageArtifact, ...]) -> str:
    return _sha256([artifact.model_dump(mode="json") for artifact in artifacts])


def _updated_job(job: PptMasterJob, **changes: object) -> PptMasterJob:
    return PptMasterJob.model_validate({**job.model_dump(mode="json"), **changes})


def receipt_digest(receipt: StageReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_sha256"})
    return _sha256(payload)


def build_receipt(
    *,
    job: PptMasterJob,
    receipt_id: str,
    stage_id: str,
    attempt: int,
    input_digest: str,
    artifacts: tuple[StageArtifact, ...],
    status: ReceiptStatus,
    committed_at: datetime,
    failure_reason: str | None = None,
) -> StageReceipt:
    if stage_id not in STAGE_IDS:
        raise PptMasterJobError("UNKNOWN_STAGE", "无法识别该 PPT Master 阶段。")
    stage_order = STAGE_IDS.index(stage_id) + 1
    committed = [item for item in job.receipts if item.status == "committed"]
    predecessor = committed[-1].receipt_id if committed else None
    base = {
        "receipt_id": receipt_id,
        "job_id": job.job_id,
        "project_id": job.snapshot.project_id,
        "report": job.snapshot.report,
        "snapshot_id": job.snapshot.snapshot_id,
        "snapshot_sha256": job.snapshot.snapshot_sha256,
        "stage_id": stage_id,
        "stage_order": stage_order,
        "attempt": attempt,
        "input_digest": _digest(input_digest),
        "output_digest": stage_output_digest(artifacts),
        "predecessor_receipt_id": predecessor,
        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
        "status": status,
        "committed_at": committed_at.isoformat().replace("+00:00", "Z"),
        "failure_reason": failure_reason,
    }
    return StageReceipt.model_validate({**base, "receipt_sha256": _sha256(base)})


def create_job(
    *,
    job_id: str,
    snapshot: LockedReportSnapshot,
    now: datetime,
    ttl: timedelta,
) -> PptMasterJob:
    _aware(now)
    return PptMasterJob(
        schema_version="1.0",
        contract_version="8.7",
        job_id=job_id,
        snapshot=snapshot,
        state="created",
        next_stage=STAGE_IDS[0],
        receipts=(),
        expires_at=now + ttl,
        created_at=now,
        updated_at=now,
    )


def lock_snapshot(job: PptMasterJob, *, now: datetime) -> PptMasterJob:
    if job.state != "created":
        raise PptMasterJobError("INVALID_STATE", "只有新建作业可以锁定报告快照。")
    return _updated_job(job, state="snapshot_locked", updated_at=_aware(now))


def begin_stage(job: PptMasterJob, *, stage_id: str, now: datetime) -> PptMasterJob:
    if job.state not in {"snapshot_locked", "paused", "failed"}:
        raise PptMasterJobError("INVALID_STATE", "当前作业状态不能开始新阶段。")
    if stage_id != job.next_stage:
        raise PptMasterJobError("RECEIPT_OUT_OF_ORDER", "请从上次保存位置继续，不能跳过阶段。")
    return _updated_job(
        job, state="running", active_stage=stage_id, updated_at=_aware(now)
    )


def commit_receipt(job: PptMasterJob, receipt: StageReceipt) -> PptMasterJob:
    if job.state != "running" or job.active_stage != receipt.stage_id:
        raise PptMasterJobError("RECEIPT_OUT_OF_ORDER", "阶段收据与当前运行阶段不一致。")
    if receipt.status == "committed" and receipt.stage_id != job.next_stage:
        raise PptMasterJobError("RECEIPT_OUT_OF_ORDER", "阶段收据没有连接到当前恢复位置。")
    receipts = (*job.receipts, receipt)
    if receipt.status == "failed":
        state: JobState = "failed"
        next_stage = job.next_stage
    else:
        committed_count = sum(item.status == "committed" for item in receipts)
        next_stage = None if committed_count == len(STAGES) else STAGE_IDS[committed_count]
        state = "ready_for_acceptance" if next_stage is None else "snapshot_locked"
    return PptMasterJob.model_validate(
        {
            **job.model_dump(mode="json"),
            "state": state,
            "active_stage": None,
            "next_stage": next_stage,
            "receipts": [item.model_dump(mode="json") for item in receipts],
            "updated_at": receipt.committed_at.isoformat(),
        }
    )


def pause_job(job: PptMasterJob, *, now: datetime) -> PptMasterJob:
    if job.state != "snapshot_locked":
        raise PptMasterJobError("INVALID_STATE", "只能在阶段收据已经保存的边界暂停。")
    return _updated_job(job, state="paused", updated_at=_aware(now))


def resume_job(
    job: PptMasterJob,
    *,
    now: datetime,
    project_id: str,
    report: ReportKind,
    snapshot_id: str,
    snapshot_sha256: str,
    artifact_root: Path,
) -> PptMasterJob:
    _aware(now)
    if job.state not in {"paused", "failed"}:
        raise PptMasterJobError("INVALID_STATE", "当前作业不是可恢复状态。")
    if now > job.expires_at:
        raise PptMasterJobError("RECEIPT_EXPIRED", "本次恢复凭据已过期，需要重新建立作业。")
    if project_id != job.snapshot.project_id or report != job.snapshot.report:
        raise PptMasterJobError("REPORT_MISMATCH", "请求的项目或报告与锁定快照不一致。")
    if snapshot_id != job.snapshot.snapshot_id or snapshot_sha256 != job.snapshot.snapshot_sha256:
        raise PptMasterJobError("SNAPSHOT_MISMATCH", "报告快照已经变化，不能沿用原作业。")
    for receipt in job.receipts:
        if receipt.status != "committed":
            continue
        for artifact in receipt.artifacts:
            path = artifact_root / artifact.relative_path
            if not path.is_file():
                raise PptMasterJobError(
                    "ARTIFACT_MISSING", f"前置产物缺失：{artifact.relative_path}"
                )
            if hashlib.sha256(path.read_bytes()).hexdigest() != artifact.sha256:
                raise PptMasterJobError(
                    "ARTIFACT_DIGEST_MISMATCH",
                    f"前置产物已经变化：{artifact.relative_path}",
                )
            if path.stat().st_size != artifact.byte_size:
                raise PptMasterJobError(
                    "ARTIFACT_DIGEST_MISMATCH",
                    f"前置产物大小已经变化：{artifact.relative_path}",
                )
    return _updated_job(job, state="snapshot_locked", updated_at=now)


class PptMasterJobStore:
    """以原子替换保存作业清单；恢复不依赖目录时间。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, job: PptMasterJob) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = _canonical_json(job.model_dump(mode="json"))
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    def load(self) -> PptMasterJob:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PptMasterJobError(
                "JOB_NOT_FOUND", "找不到可恢复的 PPT Master 作业记录。"
            ) from error
        return PptMasterJob.model_validate(payload)


class PptMasterLeaseStore:
    """跨 A/B/C 共用一个原子执行锁，防止并行调用 PPT Master。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def acquire(self, lease: ExecutionLease, *, now: datetime) -> None:
        _aware(now)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = _canonical_json(lease.model_dump(mode="json"))
        for _ in range(2):
            try:
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                current = self.read()
                same_job = (
                    current.job_id == lease.job_id
                    and current.project_id == lease.project_id
                    and current.report == lease.report
                    and current.snapshot_id == lease.snapshot_id
                )
                if now <= current.expires_at or not same_job:
                    raise PptMasterJobError(
                        "ACTIVE_LOCK_CONFLICT",
                        "另一个 PPT Master 作业仍在运行，请等待其在阶段边界释放。",
                    ) from None
                self.path.unlink(missing_ok=True)
                continue
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            return
        raise PptMasterJobError("ACTIVE_LOCK_CONFLICT", "PPT Master 全局执行锁获取失败。")

    def read(self) -> ExecutionLease:
        try:
            return ExecutionLease.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise PptMasterJobError(
                "ACTIVE_LOCK_CONFLICT", "PPT Master 全局执行锁不可读取。"
            ) from error

    def release(self, *, job_id: str, owner_id: str) -> None:
        current = self.read()
        if current.job_id != job_id or current.owner_id != owner_id:
            raise PptMasterJobError("ACTIVE_LOCK_CONFLICT", "不能释放其他作业持有的执行锁。")
        self.path.unlink()
