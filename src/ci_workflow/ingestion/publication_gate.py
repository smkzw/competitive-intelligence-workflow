"""Versioned publication classification and snapshot-level manual supply gate.

The scientific engine receives typed publication decisions.  This module does
not fetch files; it records why a publication is required or excluded and
models the one allowed user interruption when a required item is unavailable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.publication import (
    EXCLUDED_PUBLICATION_CLASSES,
    REQUIRED_PUBLICATION_CLASSES,
    ClassificationReviewState,
    PublicationClass,
    PublicationContractError,
    PublicationFetchAttempt,
    PublicationRecord,
    classify_publication,
    compute_publication_review_digest,
)

ManualGateState = Literal["awaiting_user", "accepted", "unavailable"]
ManualResponseOutcome = Literal["file_received", "file_unavailable"]


class PublicationGateError(ValueError):
    """Publication classification or manual-gate transition is invalid."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=False,
    )


def _text(value: str, label: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label}不能为空")
    return normalized


def _items(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, label) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label}不能重复")
    return normalized


def _offset(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含明确时区")
    return value


def _external_url(value: str, label: str) -> str:
    normalized = _text(value, label)
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{label}必须是外部 http(s) 地址")
    return normalized


def _relative_path(value: str, label: str) -> str:
    normalized = _text(value, label).replace("\\", "/")
    if normalized.startswith(("/", "~/")) or "://" in normalized:
        raise ValueError(f"{label}必须是项目相对路径")
    if any(part == ".." for part in normalized.split("/")):
        raise ValueError(f"{label}不得越过项目目录")
    return normalized


class ManualSupplyRequest(_StrictModel):
    """One missing publication/attachment listed by the consolidated gate."""

    request_id: str
    product_id: str
    trial_id: str
    registry_identifiers: tuple[str, ...] = Field(min_length=1)
    doi: str | None = None
    pmid: str | None = None
    exact_title: str
    blocking_fields: tuple[str, ...] = Field(min_length=1)
    attempted_paths: tuple[str, ...] = Field(min_length=1)
    source_links: tuple[str, ...] = Field(min_length=1)
    delivery_directory: str
    minimum_user_action: str
    affected_reports: tuple[Literal["A", "B", "C"], ...] = Field(min_length=1)

    @field_validator("request_id", "product_id", "trial_id", "exact_title", "minimum_user_action")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, str(info.field_name))

    @field_validator("registry_identifiers", "blocking_fields", "attempted_paths")
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, str(info.field_name))

    @field_validator("source_links")
    @classmethod
    def _links(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            _external_url(value, "source_link") for value in _items(values, "source_links")
        )

    @field_validator("delivery_directory")
    @classmethod
    def _delivery_directory(cls, value: str) -> str:
        return _relative_path(value, "delivery_directory")

    @field_validator("doi", "pmid")
    @classmethod
    def _optional_identifiers(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, "publication identifier")


class ManualSupplyResponse(_StrictModel):
    response_id: str
    outcome: ManualResponseOutcome
    responded_at: datetime
    original_filenames: tuple[str, ...] = ()
    validation_receipts: tuple[ManualFileValidationReceipt, ...] = ()
    notes: str | None = None

    @field_validator("response_id")
    @classmethod
    def _response_id(cls, value: str) -> str:
        return _text(value, "response_id")

    @field_validator("responded_at")
    @classmethod
    def _responded_at(cls, value: datetime) -> datetime:
        return _offset(value)

    @field_validator("original_filenames")
    @classmethod
    def _filenames(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _items(values, "original_filenames")

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, "response notes")


class ManualFileValidationReceipt(_StrictModel):
    request_id: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_relative_path: str
    source_version_id: str

    @field_validator("request_id", "source_version_id")
    @classmethod
    def _ids(cls, value: str, info: Any) -> str:
        return _text(value, str(info.field_name))

    @field_validator("canonical_relative_path")
    @classmethod
    def _path(cls, value: str) -> str:
        return _relative_path(value, "canonical_relative_path")


class ManualSupplyGate(_StrictModel):
    """Exactly one user interruption for one evidence snapshot."""

    schema_version: Literal["1.3"] = "1.3"
    gate_id: str
    snapshot_id: str
    requests: tuple[ManualSupplyRequest, ...] = Field(min_length=1)
    affected_reports: tuple[Literal["A", "B", "C"], ...] = Field(min_length=1)
    state: ManualGateState = "awaiting_user"
    user_response_count: Literal[0, 1] = 0
    response: ManualSupplyResponse | None = None
    limitation_zh: str | None = None
    evidence_insufficiency_page: bool = False

    @field_validator("gate_id", "snapshot_id")
    @classmethod
    def _ids(cls, value: str, info: Any) -> str:
        return _text(value, str(info.field_name))

    @field_validator("affected_reports")
    @classmethod
    def _reports(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _items(values, "affected_reports")

    @field_validator("limitation_zh")
    @classmethod
    def _limitation(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, "limitation_zh")

    @model_validator(mode="after")
    def _response_state_is_coherent(self) -> Self:
        if self.user_response_count == 0:
            if self.response is not None or self.state != "awaiting_user":
                raise PublicationGateError("未响应的 manual gate 必须保持 awaiting_user")
            if self.limitation_zh or self.evidence_insufficiency_page:
                raise PublicationGateError("用户响应前不能发布限制或证据不足页")
            return self
        if self.response is None or self.state == "awaiting_user":
            raise PublicationGateError("manual gate 的一次用户响应必须有终态回执")
        if self.response.outcome == "file_received" and self.state != "accepted":
            raise PublicationGateError("收到补件后 manual gate 必须为 accepted")
        if self.state == "accepted":
            receipt_ids = {receipt.request_id for receipt in self.response.validation_receipts}
            request_ids = {request.request_id for request in self.requests}
            if receipt_ids != request_ids:
                raise PublicationGateError("accepted gate 必须绑定全部补件请求的核验回执")
        if self.response.outcome == "file_unavailable" and self.state != "unavailable":
            raise PublicationGateError("补件不可用后 manual gate 必须为 unavailable")
        if self.state == "accepted" and self.evidence_insufficiency_page:
            raise PublicationGateError("accepted gate 不能同时交付证据不足页")
        if self.state == "unavailable" and not (
            self.limitation_zh or self.evidence_insufficiency_page
        ):
            raise PublicationGateError("不可用补件必须给出限制或证据不足页")
        return self

    def record_user_response(
        self,
        response: ManualSupplyResponse,
        *,
        official_evidence_sufficient: bool,
        limitation_zh: str | None = None,
    ) -> ManualSupplyGate:
        """Apply the sole response; replay or a second prompt is rejected."""

        if self.user_response_count != 0:
            raise PublicationGateError("同一快照的 manual gate 不能重复询问用户")
        if response.outcome == "file_received":
            receipt_ids = {receipt.request_id for receipt in response.validation_receipts}
            request_ids = {request.request_id for request in self.requests}
            if receipt_ids != request_ids:
                raise PublicationGateError("收到补件后必须先绑定全部文件核验回执")
            return self.model_copy(
                update={
                    "state": "accepted",
                    "user_response_count": 1,
                    "response": response,
                    "limitation_zh": None,
                    "evidence_insufficiency_page": False,
                }
            )
        if official_evidence_sufficient:
            if not limitation_zh:
                raise PublicationGateError("官方证据足够继续时必须记录明确限制")
            return self.model_copy(
                update={
                    "state": "unavailable",
                    "user_response_count": 1,
                    "response": response,
                    "limitation_zh": _text(limitation_zh, "limitation_zh"),
                    "evidence_insufficiency_page": False,
                }
            )
        return self.model_copy(
            update={
                "state": "unavailable",
                "user_response_count": 1,
                "response": response,
                "limitation_zh": None,
                "evidence_insufficiency_page": True,
            }
        )

    def to_markdown(self) -> str:
        """Render the user-facing gate without internal locators or secrets."""

        if self.state == "accepted":
            return "\n".join(
                (
                    "# 公开资料补件状态",
                    "",
                    "补件已核验通过；本次研究不再重复请求这些文件。",
                )
            )
        if self.state == "unavailable" and self.evidence_insufficiency_page:
            return "\n".join(
                (
                    "# 公开资料补件状态",
                    "",
                    "您已确认无法取得必需全文。现有官方证据不足以回答受影响报告的核心问题，系统将仅生成简洁的证据不足页。",
                )
            )
        if self.state == "unavailable":
            return "\n".join(
                (
                    "# 公开资料补件状态",
                    "",
                    "您已确认无法取得必需全文。本次研究将基于现有官方证据继续，并在受影响报告中持续显示以下限制：",
                    "",
                    self.limitation_zh or "存在未取得的必需全文。",
                )
            )
        lines = [
            "# 需要补充的公开资料",
            "",
            "- 请将下列资料一次性放入指定投递目录。",
            "",
        ]
        for item in self.requests:
            identifiers = "、".join(item.registry_identifiers)
            if item.doi:
                identifiers += f"；DOI：{item.doi}"
            if item.pmid:
                identifiers += f"；PMID：{item.pmid}"
            lines.extend(
                [
                    f"## {item.exact_title}",
                    f"- 产品/试验：{item.product_id} / {item.trial_id}",
                    f"- 登记与论文标识：{identifiers}",
                    f"- 阻断字段：{'、'.join(item.blocking_fields)}",
                    f"- 已尝试路径：{'、'.join(item.attempted_paths)}",
                    f"- 原文/附件链接：{'、'.join(item.source_links)}",
                    f"- 投递目录：{item.delivery_directory}",
                    f"- 最小动作：{item.minimum_user_action}",
                    "",
                ]
            )
        return "\n".join(lines)


class ManualSupplyLedger(_StrictModel):
    """Snapshot index preventing two gates for the same snapshot."""

    gates: tuple[ManualSupplyGate, ...] = ()

    @model_validator(mode="after")
    def _unique_snapshots(self) -> Self:
        snapshot_ids = [gate.snapshot_id for gate in self.gates]
        if len(snapshot_ids) != len(set(snapshot_ids)):
            raise PublicationGateError("同一快照只能建立一个 manual-supply gate")
        return self

    def add(self, gate: ManualSupplyGate) -> ManualSupplyLedger:
        if any(existing.snapshot_id == gate.snapshot_id for existing in self.gates):
            raise PublicationGateError("同一快照只能建立一个 manual-supply gate")
        return self.model_copy(update={"gates": (*self.gates, gate)})


__all__ = [
    "ClassificationReviewState",
    "EXCLUDED_PUBLICATION_CLASSES",
    "ManualGateState",
    "ManualResponseOutcome",
    "ManualSupplyGate",
    "ManualSupplyLedger",
    "ManualSupplyRequest",
    "ManualSupplyResponse",
    "PublicationClass",
    "PublicationContractError",
    "PublicationFetchAttempt",
    "PublicationGateError",
    "PublicationRecord",
    "REQUIRED_PUBLICATION_CLASSES",
    "classify_publication",
    "compute_publication_review_digest",
]
