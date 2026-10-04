"""科学复核 epoch 指针存储（R24 版本化复核纪元）。

epoch 0 是既有单例布局的隐式纪元（不落任何指针文件，路径与历史行为逐字节
兼容）；epoch ≥ 1 的生产上下文/复核请求/签发记录位于
``state/scientific_review/<kind>/epochs/e<n>/``，回执位于
``receipts/scientific_review/<kind>/epochs/e<n>/receipt.json``。指针文件
（``state/scientific_review/<kind>/epoch.json``）只追加纪元链：条目一经
写入不再改写，链上每个纪元绑定其前驱上下文摘要，指针自摘要在模型层校验。

分层边界：本模块只提供确定性路径推导、指针模型与原子读写；epoch 推进
决策、前驱/项目/门户字节绑定与失败关闭语义留在 application 层
（``application.scientific_review_transition``）。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

EPOCH_RECORD_KIND: Final = "scientific-review-epoch-v1"


class ScientificReviewEpochStateError(ValueError):
    """epoch 指针文件损坏、链断裂、绑定缺失或摘要漂移：失败关闭。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("epoch 指针字段不能为空")
    return normalized


def _sha256_field(value: str) -> str:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("epoch 指针摘要必须是小写 SHA-256")
    return value


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("epoch 指针时间必须包含明确时区偏移")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    # 与 hosts.receipt / qc.review_receipt / review_issuer 同一规范化：
    # 排序键、紧凑分隔符、无结尾换行。
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _validated_kind(report_kind: str) -> Literal["A", "B", "C"]:
    if report_kind not in ("A", "B", "C"):
        raise ScientificReviewEpochStateError(
            f"科学复核 epoch 只适用于 A/B/C 类报告：{report_kind!r}"
        )
    return report_kind  # type: ignore[return-value]


def _validated_epoch(epoch: int) -> int:
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise ScientificReviewEpochStateError("epoch 序号必须是从 1 开始的整数")
    return epoch


class ScientificReviewEpochEntry(BaseModel):
    """一条已激活纪元：绑定新上下文摘要与其前驱上下文摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    epoch: int
    context_digest: str
    predecessor_context_digest: str
    advanced_at: datetime

    @field_validator("epoch")
    @classmethod
    def _epoch_is_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("epoch 序号必须从 1 开始")
        return value

    @field_validator("context_digest", "predecessor_context_digest")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @field_validator("advanced_at")
    @classmethod
    def _advanced_at_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class ScientificReviewEpochPointer(BaseModel):
    """epoch 指针：只追加纪元链与当前活跃纪元；自摘要构造即校验。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_kind: Literal["scientific-review-epoch-v1"]
    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    report_kind: Literal["A", "B", "C"]
    active_epoch: int
    epochs: tuple[ScientificReviewEpochEntry, ...]
    pointer_digest: str

    @field_validator("project_id")
    @classmethod
    def _project_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("pointer_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @model_validator(mode="after")
    def _chain_is_consistent(self) -> ScientificReviewEpochPointer:
        if not self.epochs:
            raise ValueError("epoch 指针必须至少记录一个已激活纪元")
        if self.epochs[-1].epoch != self.active_epoch:
            raise ValueError("epoch 指针活跃纪元必须等于最后一个纪元条目")
        previous_digest: str | None = None
        expected_epoch = 0
        for entry in self.epochs:
            if entry.epoch != expected_epoch + 1:
                raise ValueError("epoch 链必须从 1 开始连续递增")
            if (
                previous_digest is not None
                and entry.predecessor_context_digest != previous_digest
            ):
                raise ValueError("epoch 链前驱绑定断裂：历史纪元不可改写")
            previous_digest = entry.context_digest
            expected_epoch = entry.epoch
        if self.pointer_digest != compute_epoch_pointer_digest(self):
            raise ValueError("epoch 指针摘要与内容不一致：指针被篡改或损坏")
        return self

    @staticmethod
    def compute_pointer_digest(pointer: ScientificReviewEpochPointer) -> str:
        """按除 ``pointer_digest`` 外全部字段的规范 JSON 计算 SHA-256。"""
        material = pointer.model_dump(mode="json", exclude={"pointer_digest"})
        return hashlib.sha256(_canonical_json_bytes(material)).hexdigest()


def compute_epoch_pointer_digest(pointer: ScientificReviewEpochPointer) -> str:
    """模块级摘要计算（与模型静态方法同一算法）。"""
    return ScientificReviewEpochPointer.compute_pointer_digest(pointer)


def build_scientific_review_epoch_pointer(
    *,
    project_id: str,
    report_kind: str,
    epochs: tuple[ScientificReviewEpochEntry, ...],
    active_epoch: int,
) -> ScientificReviewEpochPointer:
    """以完整绑定材料构造指针并派生自摘要（唯一受支持构造路径）。"""
    kind = _validated_kind(report_kind)
    _validated_epoch(active_epoch)
    draft = ScientificReviewEpochPointer.model_construct(
        record_kind=EPOCH_RECORD_KIND,
        schema_version="1.0",
        project_id=project_id,
        report_kind=kind,
        active_epoch=active_epoch,
        epochs=tuple(epochs),
        pointer_digest="0" * 64,
    )
    return ScientificReviewEpochPointer.model_validate(
        draft.model_dump(mode="json", exclude={"pointer_digest"})
        | {"pointer_digest": ScientificReviewEpochPointer.compute_pointer_digest(draft)}
    )


# ── 确定性路径推导 ─────────────────────────────────────────────────────────────


def epoch_pointer_path(report_kind: str) -> PurePosixPath:
    """epoch 指针文件的项目相对路径（epoch 0 隐式，无此文件）。"""
    kind = _validated_kind(report_kind)
    return PurePosixPath("state") / "scientific_review" / kind / "epoch.json"


def epoch_scope_dir(report_kind: str, epoch: int) -> PurePosixPath:
    """epoch ≥ 1 版本化材料目录的项目相对路径。"""
    kind = _validated_kind(report_kind)
    _validated_epoch(epoch)
    return PurePosixPath("state") / "scientific_review" / kind / "epochs" / f"e{epoch}"


def epoch_production_context_path(report_kind: str, epoch: int) -> PurePosixPath:
    return epoch_scope_dir(report_kind, epoch) / "production_context.json"


def epoch_review_request_path(report_kind: str, epoch: int) -> PurePosixPath:
    return epoch_scope_dir(report_kind, epoch) / "review_request.json"


def epoch_issuance_record_path(report_kind: str, epoch: int) -> PurePosixPath:
    return epoch_scope_dir(report_kind, epoch) / "issuance.json"


def epoch_receipt_path(report_kind: str, epoch: int) -> PurePosixPath:
    kind = _validated_kind(report_kind)
    _validated_epoch(epoch)
    return (
        PurePosixPath("receipts") / "scientific_review" / kind / "epochs" / f"e{epoch}"
        / "receipt.json"
    )


# ── 指针原子读写 ───────────────────────────────────────────────────────────────


def read_epoch_pointer(
    project_root: Path, report_kind: str
) -> ScientificReviewEpochPointer | None:
    """读取 epoch 指针；epoch 0（无文件）返回 None，损坏/漂移失败关闭。"""
    kind = _validated_kind(report_kind)
    path = project_root / epoch_pointer_path(kind)
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise ScientificReviewEpochStateError("epoch 指针必须是项目内普通文件")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScientificReviewEpochStateError(
            "epoch 指针不可读或不是有效 JSON"
        ) from error
    if not isinstance(raw, dict) or raw.get("record_kind") != EPOCH_RECORD_KIND:
        raise ScientificReviewEpochStateError("epoch 指针记录类别无效")
    try:
        pointer = ScientificReviewEpochPointer.model_validate(raw)
        if pointer.report_kind != kind:
            raise ScientificReviewEpochStateError("epoch 指针报告类型与所在作用域不一致")
        return pointer
    except PydanticValidationError as error:
        raise ScientificReviewEpochStateError(f"epoch 指针验证失败：{error}") from error


def write_epoch_pointer(
    project_root: Path, report_kind: str, pointer: ScientificReviewEpochPointer
) -> Path:
    """原子写入 epoch 指针（临时文件 + fsync + 原子替换）；激活即生效。"""
    kind = _validated_kind(report_kind)
    path = project_root / epoch_pointer_path(kind)
    payload = _canonical_json_bytes(pointer.model_dump(mode="json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".epoch-pointer-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def load_epoch_entry(pointer: ScientificReviewEpochPointer, epoch: int) -> Any:
    """按序号取已激活纪元条目；未知序号失败关闭。"""
    _validated_epoch(epoch)
    for entry in pointer.epochs:
        if entry.epoch == epoch:
            return entry
    raise ScientificReviewEpochStateError(f"epoch 指针没有记录纪元 {epoch}")


__all__ = [
    "EPOCH_RECORD_KIND",
    "ScientificReviewEpochEntry",
    "ScientificReviewEpochPointer",
    "ScientificReviewEpochStateError",
    "build_scientific_review_epoch_pointer",
    "compute_epoch_pointer_digest",
    "epoch_issuance_record_path",
    "epoch_pointer_path",
    "epoch_production_context_path",
    "epoch_receipt_path",
    "epoch_review_request_path",
    "epoch_scope_dir",
    "load_epoch_entry",
    "read_epoch_pointer",
    "write_epoch_pointer",
]
