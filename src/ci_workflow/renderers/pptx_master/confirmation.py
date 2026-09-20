"""PPT Master 八项中文确认、结果覆盖和一次性会话合同。

本模块只负责确认输入的确定性合同，不启动确认页面、不创建 PPTX，也不持有
常驻工作台。推荐值绑定一个已经锁定的 source pack；用户结果必须回带同一个
会话、来源包和快照身份，随后才能覆盖推荐值。会话关闭是一次性的，重复提交
同一结果安全地返回已关闭会话，提交不同结果则失败关闭。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.domain.ids import stable_id

ConfirmationKey = Literal[
    "canvas_format",
    "page_range",
    "target_audience",
    "style_goal",
    "color_scheme",
    "icon_strategy",
    "font_formula_strategy",
    "image_strategy",
]
ReportKey = Literal["A", "B", "C"]
JsonObject = dict[str, Any]

SCHEMA_VERSION: Literal["1.0"] = "1.0"
CONTRACT_VERSION: Literal["8.7"] = "8.7"
SCHEMA_FILENAME = "pptx-confirmation.schema.json"
RECOMMENDATION_PATH = "confirm_ui/recommendations.json"
RESULT_PATH = "confirm_ui/result.json"
SESSION_PATH = "confirm_ui/session.json"

CONFIRMATION_KEYS: tuple[ConfirmationKey, ...] = (
    "canvas_format",
    "page_range",
    "target_audience",
    "style_goal",
    "color_scheme",
    "icon_strategy",
    "font_formula_strategy",
    "image_strategy",
)
# Friendly aliases used by callers that describe the data as items or fields.
RECOMMENDATION_KEYS = CONFIRMATION_KEYS
CONFIRMATION_ITEM_KEYS = CONFIRMATION_KEYS
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_ZERO_DIGEST = "0" * 64


class PptxConfirmationError(ValueError):
    """确认推荐、用户结果或会话状态不符合合同。"""

    def __init__(self, message: str, code: str = "INVALID_CONFIRMATION") -> None:
        super().__init__(message)
        self.code = code


# Short aliases make the error usable without coupling adapters to the module name.
ConfirmationError = PptxConfirmationError
ConfirmationContractError = PptxConfirmationError


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
        raise PptxConfirmationError(
            "确认合同必须是有限、可序列化的 JSON", "SERIALIZATION_ERROR"
        ) from error


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _not_blank(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}必须是文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field}不能为空")
    return normalized


def _digest(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field}必须是 64 位小写 SHA-256")
    return value


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field}必须包含明确时区")
    return value


def _relative_path(value: str, field: str) -> str:
    normalized = _not_blank(value, field)
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or "\\" in normalized:
        raise ValueError(f"{field}必须是项目内 POSIX 相对路径")
    return normalized


def _report(value: str) -> ReportKey:
    normalized = _not_blank(value, "报告类型")
    if normalized not in {"A", "B", "C"}:
        raise ValueError("报告类型必须是 A、B 或 C")
    return cast(ReportKey, normalized)


def _cjk_text(value: str, field: str) -> str:
    normalized = _not_blank(value, field)
    if _CJK_RE.search(normalized) is None:
        raise ValueError(f"{field}必须包含中文")
    return normalized


def _payload(value: Any, field: str) -> JsonObject:
    if isinstance(value, BaseModel):
        raw = value.model_dump(mode="json")
    elif isinstance(value, Mapping):
        raw = dict(value)
    elif hasattr(value, "summary"):
        return _payload(value.summary, field)
    elif hasattr(value, "manifest"):
        return _payload(value.manifest, field)
    else:
        raise PptxConfirmationError(f"{field}必须是对象或映射", "INVALID_INPUT")
    if not isinstance(raw, dict):
        raise PptxConfirmationError(f"{field}顶层必须是对象", "INVALID_INPUT")
    return raw


def _read_required_text(data: Mapping[str, Any], key: str, field: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PptxConfirmationError(f"{field}缺少{key}", "BINDING_MISSING")
    return _not_blank(value, f"{field}.{key}")


def _read_optional_text(data: Mapping[str, Any], key: str, fallback: str) -> str:
    value = data.get(key)
    if value is None:
        return fallback
    if not isinstance(value, str) or not value.strip():
        raise PptxConfirmationError(f"确认绑定字段 {key} 无效", "BINDING_INVALID")
    return _not_blank(value, key)


def _source_pack_binding(source_pack: Any) -> JsonObject:
    """Extract and validate the immutable identity carried by a source pack summary."""

    data = _payload(source_pack, "来源包摘要")
    report = _report(_read_required_text(data, "report", "来源包摘要"))
    project_id = _read_required_text(data, "project_id", "来源包摘要")
    report_version = _read_required_text(data, "report_version", "来源包摘要")
    snapshot_id = _read_required_text(data, "snapshot_id", "来源包摘要")
    snapshot_sha256 = _read_required_text(data, "snapshot_sha256", "来源包摘要")
    _digest(snapshot_sha256, "来源包摘要.snapshot_sha256")
    coverage_set_id = _read_required_text(data, "coverage_set_id", "来源包摘要")
    source_pack_id = _read_optional_text(
        data,
        "source_pack_id",
        stable_id("pptx-source-pack", project_id, report, report_version, snapshot_id),
    )
    source_pack_sha256 = data.get("source_pack_sha256")
    if source_pack_sha256 is None:
        # A raw binding is accepted for adapters, but it still receives a stable
        # digest so a later result cannot silently move to a different binding.
        source_pack_sha256 = _sha256(data)
    _digest(str(source_pack_sha256), "来源包摘要.source_pack_sha256")
    claim_snapshot_id = _read_optional_text(
        data,
        "claim_snapshot_id",
        stable_id("claim-snapshot", project_id, snapshot_id),
    )
    evidence_snapshot_id = _read_optional_text(
        data,
        "evidence_snapshot_id",
        stable_id("evidence-snapshot", project_id, snapshot_id),
    )
    data_cutoff = _read_optional_text(data, "data_cutoff", "未公开")
    return {
        "project_id": project_id,
        "report": report,
        "report_version": report_version,
        "source_pack_id": source_pack_id,
        "source_pack_sha256": str(source_pack_sha256),
        "snapshot_id": snapshot_id,
        "snapshot_sha256": snapshot_sha256,
        "claim_snapshot_id": claim_snapshot_id,
        "evidence_snapshot_id": evidence_snapshot_id,
        "coverage_set_id": coverage_set_id,
        "data_cutoff": data_cutoff,
        "page_count": data.get("page_count"),
    }


class ConfirmationRecommendation(BaseModel):
    """单项中文推荐及其可选值。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: ConfirmationKey
    label_zh: str = Field(min_length=1)
    recommended_value_zh: str = Field(min_length=1)
    options_zh: tuple[str, ...] = Field(min_length=1)
    rationale_zh: str = Field(min_length=1)

    @field_validator("label_zh", "recommended_value_zh", "rationale_zh")
    @classmethod
    def _chinese_text(cls, value: str, info: Any) -> str:
        field = getattr(info, "field_name", "确认文本")
        return _cjk_text(value, field)

    @field_validator("options_zh")
    @classmethod
    def _options_are_valid(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value, "确认选项") for value in values)
        if len(normalized) != len(set(normalized)):
            raise ValueError("确认选项不得重复")
        return normalized

    @model_validator(mode="after")
    def _recommended_value_is_an_option(self) -> ConfirmationRecommendation:
        if self.recommended_value_zh not in self.options_zh:
            raise ValueError("推荐值必须出现在确认选项中")
        return self

    @property
    def key(self) -> ConfirmationKey:
        return self.item_id

    @property
    def recommendation(self) -> str:
        return self.recommended_value_zh

    @property
    def recommended_value(self) -> str:
        return self.recommended_value_zh

    @property
    def options(self) -> tuple[str, ...]:
        return self.options_zh


class ConfirmationRecommendations(BaseModel):
    """八项推荐，带 source pack/锁定快照身份和自洽摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    contract_version: Literal["8.7"] = CONTRACT_VERSION
    session_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report: ReportKey
    report_version: str = Field(min_length=1)
    source_pack_id: str = Field(min_length=1)
    source_pack_sha256: str
    snapshot_id: str = Field(min_length=1)
    snapshot_sha256: str
    claim_snapshot_id: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    coverage_set_id: str = Field(min_length=1)
    data_cutoff: str = Field(min_length=1)
    generated_at: datetime
    recommendations_path: str = RECOMMENDATION_PATH
    items: tuple[ConfirmationRecommendation, ...] = Field(min_length=8, max_length=8)
    recommendations_sha256: str
    @model_validator(mode="before")
    @classmethod
    def _accept_recommendations_alias(cls, value: Any) -> Any:
        if isinstance(value, Mapping) and "items" not in value and "recommendations" in value:
            raw = dict(value)
            raw["items"] = raw.pop("recommendations")
            return raw
        return value

    @field_validator(
        "project_id",
        "session_id",
        "report_version",
        "source_pack_id",
        "snapshot_id",
        "claim_snapshot_id",
        "evidence_snapshot_id",
        "coverage_set_id",
        "data_cutoff",
    )
    @classmethod
    def _identity_text(cls, value: str) -> str:
        return _not_blank(value, "确认身份")

    @field_validator("source_pack_sha256", "snapshot_sha256", "recommendations_sha256")
    @classmethod
    def _identity_digest(cls, value: str) -> str:
        return _digest(value, "确认摘要")

    _generated_time = field_validator("generated_at")(
        lambda value: _aware(value, "推荐生成时间")
    )
    _path = field_validator("recommendations_path")(
        lambda value: _relative_path(value, "推荐清单路径")
    )

    @model_validator(mode="after")
    def _eight_unique_and_digest_valid(self) -> ConfirmationRecommendations:
        keys = tuple(item.item_id for item in self.items)
        if keys != CONFIRMATION_KEYS:
            if len(set(keys)) != len(keys):
                raise ValueError("八项确认标识不得重复")
            raise ValueError("八项确认必须按固定顺序完整提供")
        expected = _recommendations_digest(self)
        if expected != self.recommendations_sha256:
            raise ValueError("推荐清单摘要不一致")
        return self

    @property
    def recommendations(self) -> tuple[ConfirmationRecommendation, ...]:
        return self.items

    @property
    def binding(self) -> ConfirmationBinding:
        return ConfirmationBinding.from_recommendations(self)

    def item(self, item_id: ConfirmationKey) -> ConfirmationRecommendation:
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise KeyError(item_id)


class ConfirmationBinding(BaseModel):
    """确认结果必须继承的报告、来源包和锁定快照身份。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str = Field(min_length=1)
    report: ReportKey
    report_version: str = Field(min_length=1)
    source_pack_id: str = Field(min_length=1)
    source_pack_sha256: str
    snapshot_id: str = Field(min_length=1)
    snapshot_sha256: str
    claim_snapshot_id: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    coverage_set_id: str = Field(min_length=1)

    @field_validator(
        "project_id",
        "report_version",
        "source_pack_id",
        "snapshot_id",
        "claim_snapshot_id",
        "evidence_snapshot_id",
        "coverage_set_id",
    )
    @classmethod
    def _text_fields(cls, value: str) -> str:
        return _not_blank(value, "确认绑定")

    @field_validator("source_pack_sha256", "snapshot_sha256")
    @classmethod
    def _digest_fields(cls, value: str) -> str:
        return _digest(value, "确认绑定摘要")

    @classmethod
    def from_recommendations(
        cls, recommendations: ConfirmationRecommendations
    ) -> ConfirmationBinding:
        return cls(
            project_id=recommendations.project_id,
            report=recommendations.report,
            report_version=recommendations.report_version,
            source_pack_id=recommendations.source_pack_id,
            source_pack_sha256=recommendations.source_pack_sha256,
            snapshot_id=recommendations.snapshot_id,
            snapshot_sha256=recommendations.snapshot_sha256,
            claim_snapshot_id=recommendations.claim_snapshot_id,
            evidence_snapshot_id=recommendations.evidence_snapshot_id,
            coverage_set_id=recommendations.coverage_set_id,
        )

    def matches(self, other: ConfirmationBinding) -> bool:
        return self == other


class ConfirmationResult(BaseModel):
    """用户对八项确认的结果；confirmed_values 覆盖推荐值。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    contract_version: Literal["8.7"] = CONTRACT_VERSION
    session_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report: ReportKey
    report_version: str = Field(min_length=1)
    source_pack_id: str = Field(min_length=1)
    source_pack_sha256: str
    snapshot_id: str = Field(min_length=1)
    snapshot_sha256: str
    claim_snapshot_id: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    coverage_set_id: str = Field(min_length=1)
    recommendations_sha256: str
    confirmed_values: dict[str, str]
    confirmed_by: str = Field(min_length=1)
    confirmed_at: datetime
    result_sha256: str

    @model_validator(mode="before")
    @classmethod
    def _accept_values_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        raw = dict(value)
        if "confirmed_values" not in raw and "values" in raw:
            raw["confirmed_values"] = raw.pop("values")
        if "confirmed_values" not in raw and "answers" in raw:
            answers = raw.pop("answers")
            if isinstance(answers, Mapping):
                raw["confirmed_values"] = dict(answers)
            elif isinstance(answers, list):
                converted: dict[str, str] = {}
                for answer in answers:
                    if not isinstance(answer, Mapping):
                        return raw
                    item_id = answer.get("item_id", answer.get("key"))
                    answer_value = answer.get("value_zh", answer.get("value"))
                    if not isinstance(item_id, str) or not isinstance(answer_value, str):
                        return raw
                    converted[item_id] = answer_value
                raw["confirmed_values"] = converted
        return raw

    @field_validator(
        "session_id",
        "project_id",
        "report_version",
        "source_pack_id",
        "confirmed_by",
        "snapshot_id",
        "claim_snapshot_id",
        "evidence_snapshot_id",
        "coverage_set_id",
    )
    @classmethod
    def _text_fields(cls, value: str) -> str:
        return _not_blank(value, "确认结果")

    @field_validator(
        "source_pack_sha256",
        "snapshot_sha256",
        "recommendations_sha256",
        "result_sha256",
    )
    @classmethod
    def _digest_fields(cls, value: str) -> str:
        return _digest(value, "确认结果摘要")

    @field_validator("confirmed_at")
    @classmethod
    def _confirmed_time(cls, value: datetime) -> datetime:
        return _aware(value, "确认时间")

    @field_validator("confirmed_values")
    @classmethod
    def _values_are_nonblank(cls, values: MutableMapping[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in values.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("确认结果字段标识不能为空")
            normalized[key] = _not_blank(value, f"确认结果.{key}")
        return normalized

    @model_validator(mode="after")
    def _keys_and_digest_are_valid(self) -> ConfirmationResult:
        keys = tuple(self.confirmed_values)
        if set(keys) != set(CONFIRMATION_KEYS) or len(keys) != len(CONFIRMATION_KEYS):
            missing = sorted(set(CONFIRMATION_KEYS) - set(keys))
            unknown = sorted(set(keys) - set(CONFIRMATION_KEYS))
            detail = []
            if missing:
                detail.append(f"缺少 {','.join(missing)}")
            if unknown:
                detail.append(f"未知 {','.join(unknown)}")
            raise ValueError("确认结果必须恰好覆盖八项：" + "；".join(detail))
        expected = _result_digest(self)
        if expected != self.result_sha256:
            raise ValueError("确认结果摘要不一致")
        return self

    @property
    def values(self) -> dict[str, str]:
        return dict(self.confirmed_values)

    @property
    def answers(self) -> tuple[tuple[ConfirmationKey, str], ...]:
        return tuple((key, self.confirmed_values[key]) for key in CONFIRMATION_KEYS)

    @property
    def binding(self) -> ConfirmationBinding:
        return ConfirmationBinding.model_validate(
            {
                "project_id": self.project_id,
                "report": self.report,
                "report_version": self.report_version,
                "source_pack_id": self.source_pack_id,
                "source_pack_sha256": self.source_pack_sha256,
                "snapshot_id": self.snapshot_id,
                "snapshot_sha256": self.snapshot_sha256,
                "claim_snapshot_id": self.claim_snapshot_id,
                "evidence_snapshot_id": self.evidence_snapshot_id,
                "coverage_set_id": self.coverage_set_id,
            }
        )


class ConfirmationSession(BaseModel):
    """一次性确认会话状态；关闭后不可接受不同结果。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    contract_version: Literal["8.7"] = CONTRACT_VERSION
    session_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report: ReportKey
    report_version: str = Field(min_length=1)
    source_pack_id: str = Field(min_length=1)
    source_pack_sha256: str
    snapshot_id: str = Field(min_length=1)
    snapshot_sha256: str
    claim_snapshot_id: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    coverage_set_id: str = Field(min_length=1)
    recommendations_sha256: str
    recommendations_path: str = RECOMMENDATION_PATH
    result_path: str = RESULT_PATH
    state: Literal["open", "closed"] = "open"
    opened_at: datetime
    closed_at: datetime | None = None
    result_sha256: str | None = None
    session_sha256: str

    @field_validator(
        "session_id",
        "project_id",
        "report_version",
        "source_pack_id",
        "snapshot_id",
        "claim_snapshot_id",
        "evidence_snapshot_id",
        "coverage_set_id",
    )
    @classmethod
    def _text_fields(cls, value: str) -> str:
        return _not_blank(value, "确认会话")

    @field_validator(
        "source_pack_sha256", "snapshot_sha256", "recommendations_sha256", "session_sha256"
    )
    @classmethod
    def _digest_fields(cls, value: str) -> str:
        return _digest(value, "确认会话摘要")

    @field_validator("recommendations_path", "result_path")
    @classmethod
    def _paths(cls, value: str) -> str:
        return _relative_path(value, "确认会话路径")

    @field_validator("opened_at", "closed_at")
    @classmethod
    def _times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _aware(value, "确认会话时间")

    @model_validator(mode="after")
    def _state_and_digest_are_valid(self) -> ConfirmationSession:
        if self.state == "open" and (self.closed_at is not None or self.result_sha256 is not None):
            raise ValueError("打开的确认会话不能携带关闭结果")
        if self.state == "closed" and (self.closed_at is None or self.result_sha256 is None):
            raise ValueError("已关闭确认会话必须携带关闭时间和结果摘要")
        expected = _session_digest(self)
        if expected != self.session_sha256:
            raise ValueError("确认会话摘要不一致")
        return self

    @property
    def closed(self) -> bool:
        return self.state == "closed"

    @property
    def binding(self) -> ConfirmationBinding:
        return ConfirmationBinding.model_validate(
            {
                "project_id": self.project_id,
                "report": self.report,
                "report_version": self.report_version,
                "source_pack_id": self.source_pack_id,
                "source_pack_sha256": self.source_pack_sha256,
                "snapshot_id": self.snapshot_id,
                "snapshot_sha256": self.snapshot_sha256,
                "claim_snapshot_id": self.claim_snapshot_id,
                "evidence_snapshot_id": self.evidence_snapshot_id,
                "coverage_set_id": self.coverage_set_id,
            }
        )


@dataclass(frozen=True)
class EffectiveConfirmation:
    """结果覆盖推荐后的只读视图。"""

    session_id: str
    report: ReportKey
    snapshot_id: str
    recommendations_sha256: str
    result_sha256: str
    effective_values: Mapping[str, str]
    source: Literal["user_confirmed"] = "user_confirmed"

    @property
    def values(self) -> dict[str, str]:
        return dict(self.effective_values)

    @property
    def confirmed_values(self) -> dict[str, str]:
        return dict(self.effective_values)

    def __getitem__(self, item_id: str) -> str:
        return self.effective_values[item_id]

    def get(self, item_id: str, default: str | None = None) -> str | None:
        return self.effective_values.get(item_id, default)


# ─── deterministic digest helpers ──────────────────────────────────────────


def _recommendations_digest(recommendations: ConfirmationRecommendations) -> str:
    payload = recommendations.model_dump(mode="json")
    payload["recommendations_sha256"] = _ZERO_DIGEST
    return _sha256(payload)


def _result_digest(result: ConfirmationResult) -> str:
    payload = result.model_dump(mode="json")
    payload["result_sha256"] = _ZERO_DIGEST
    return _sha256(payload)


def _session_digest(session: ConfirmationSession) -> str:
    payload = session.model_dump(mode="json")
    payload["session_sha256"] = _ZERO_DIGEST
    return _sha256(payload)


def _finalize_model(model: BaseModel, field: str, digest_fn: Any, cls: type[BaseModel]) -> Any:
    # Keep typed values while computing the digest; serializing a provisional
    # model to JSON first makes Pydantic emit warnings for nested models.
    provisional = model.model_copy(update={field: _ZERO_DIGEST})
    digest = digest_fn(provisional)
    payload = model.model_dump(mode="python")
    payload[field] = digest
    return cls.model_validate(payload)


# ─── recommendation generation ─────────────────────────────────────────────


def _recommendation_items(page_count: int | None) -> tuple[ConfirmationRecommendation, ...]:
    page_text = (
        f"覆盖来源包全部 {page_count} 页（第 1 页至第 {page_count} 页）"
        if isinstance(page_count, int) and page_count > 0
        else "覆盖来源包全部页面，按来源包页序生成"
    )
    specs: tuple[tuple[ConfirmationKey, str, str, tuple[str, ...], str], ...] = (
        (
            "canvas_format",
            "画布格式",
            "16:9 宽屏（1920×1080）",
            ("16:9 宽屏（1920×1080）", "4:3 标准（1024×768）"),
            "适合临床汇报屏幕，并为表格和证据依据保留横向空间。",
        ),
        (
            "page_range",
            "页数范围",
            page_text,
            (page_text, "仅生成摘要页和结论页"),
            "页序必须覆盖来源包已锁定的页面责任，不得因排版省略事实页面。",
        ),
        (
            "target_audience",
            "目标受众",
            "临床、医学事务与注册团队",
            ("临床、医学事务与注册团队", "临床研究项目团队"),
            "受众决定术语密度；数值仍以锁定快照和来源包为准。",
        ),
        (
            "style_goal",
            "风格目标",
            "证据优先、层级清晰、克制留白",
            ("证据优先、层级清晰、克制留白", "管理层摘要、结论优先"),
            "重点是可追溯地阅读事实，不以装饰或综合评分替代证据。",
        ),
        (
            "color_scheme",
            "配色方案",
            "深海军蓝、青绿色与中性灰；状态色仅作语义标记",
            (
                "深海军蓝、青绿色与中性灰；状态色仅作语义标记",
                "项目既有康哲配色；状态色仅作语义标记",
            ),
            "配色保持正文、表格和状态标签的对比度，不把颜色当成疗效或风险排名。",
        ),
        (
            "icon_strategy",
            "图标策略",
            "仅使用项目内许可图标；缺失时使用中文文字标签",
            (
                "仅使用项目内许可图标；缺失时使用中文文字标签",
                "不使用图标，全部使用中文文字标签",
            ),
            "图标只承担导航和状态提示，不引入未在来源包中披露的临床含义。",
        ),
        (
            "font_formula_strategy",
            "字体与公式策略",
            "中文优先字体；公式使用可编辑文本并保留原始符号",
            (
                "中文优先字体；公式使用可编辑文本并保留原始符号",
                "中文优先字体；公式转为清晰图片并绑定来源说明",
            ),
            "中文字体保证可读性；公式策略必须保持单位、分母和比较符号可核查。",
        ),
        (
            "image_strategy",
            "图片策略",
            "仅使用来源包或项目内许可图片；缺失时显示未公开",
            (
                "仅使用来源包或项目内许可图片；缺失时显示未公开",
                "不使用图片，改用中文结构化事实卡片",
            ),
            "图片不能替代结构化事实，也不能用占位图暗示未披露的临床结果。",
        ),
    )
    return tuple(
        ConfirmationRecommendation(
            item_id=item_id,
            label_zh=label,
            recommended_value_zh=recommended,
            options_zh=options,
            rationale_zh=rationale,
        )
        for item_id, label, recommended, options, rationale in specs
    )


def build_recommendations(
    source_pack: Any,
    *,
    session_id: str | None = None,
    generated_at: datetime | None = None,
    recommendations_path: str = RECOMMENDATION_PATH,
) -> ConfirmationRecommendations:
    """为一个锁定 source pack 生成确定性的八项中文推荐。"""

    binding = _source_pack_binding(source_pack)
    if generated_at is None:
        generated_at = datetime.now(UTC)
    _aware(generated_at, "推荐生成时间")
    if session_id is None:
        session_id = stable_id(
            "pptx-confirmation-session",
            binding["project_id"],
            binding["report"],
            binding["report_version"],
            binding["source_pack_id"],
            binding["snapshot_id"],
            binding["snapshot_sha256"],
        )
    base = ConfirmationRecommendations.model_construct(
        schema_version=SCHEMA_VERSION,
        contract_version=CONTRACT_VERSION,
        session_id=_not_blank(session_id, "确认会话标识"),
        project_id=binding["project_id"],
        report=binding["report"],
        report_version=binding["report_version"],
        source_pack_id=binding["source_pack_id"],
        source_pack_sha256=binding["source_pack_sha256"],
        snapshot_id=binding["snapshot_id"],
        snapshot_sha256=binding["snapshot_sha256"],
        claim_snapshot_id=binding["claim_snapshot_id"],
        evidence_snapshot_id=binding["evidence_snapshot_id"],
        coverage_set_id=binding["coverage_set_id"],
        data_cutoff=binding["data_cutoff"],
        generated_at=generated_at,
        recommendations_path=recommendations_path,
        items=_recommendation_items(binding.get("page_count")),
        recommendations_sha256=_ZERO_DIGEST,
    )
    return cast(
        ConfirmationRecommendations,
        _finalize_model(
            base,
            "recommendations_sha256",
            _recommendations_digest,
            ConfirmationRecommendations,
        ),
    )


def build_confirmation_recommendations(*args: Any, **kwargs: Any) -> ConfirmationRecommendations:
    """明确命名的推荐构建别名。"""

    return build_recommendations(*args, **kwargs)


# ─── result validation and override ─────────────────────────────────────────


def _recommendation_model(value: Any) -> ConfirmationRecommendations:
    if isinstance(value, ConfirmationRecommendations):
        return value
    try:
        return ConfirmationRecommendations.model_validate(_payload(value, "推荐清单"))
    except (PydanticValidationError, PptxConfirmationError) as error:
        raise PptxConfirmationError("推荐清单不符合类型合同", "RECOMMENDATIONS_INVALID") from error


def _result_model(value: Any) -> ConfirmationResult:
    if isinstance(value, ConfirmationResult):
        return value
    try:
        raw = _payload(value, "确认结果")
        # Adapters may receive the natural ``values`` spelling; canonical output
        # remains ``confirmed_values`` so the JSON contract is unambiguous.
        if "confirmed_values" not in raw and "values" in raw:
            raw["confirmed_values"] = raw.pop("values")
        return ConfirmationResult.model_validate(raw)
    except (PydanticValidationError, PptxConfirmationError) as error:
        raise PptxConfirmationError("确认结果不符合类型合同", "RESULT_INVALID") from error


def _same_binding(left: ConfirmationBinding, right: ConfirmationBinding) -> None:
    if left.project_id != right.project_id or left.report != right.report:
        raise PptxConfirmationError("确认结果跨项目或跨报告复用", "REPORT_MISMATCH")
    if left.snapshot_id != right.snapshot_id or left.snapshot_sha256 != right.snapshot_sha256:
        raise PptxConfirmationError("确认结果绑定的锁定快照已经变化", "SNAPSHOT_MISMATCH")
    if (
        left.source_pack_id != right.source_pack_id
        or left.source_pack_sha256 != right.source_pack_sha256
    ):
        raise PptxConfirmationError("确认结果绑定的来源包已经变化", "SOURCE_PACK_MISMATCH")
    if left != right:
        raise PptxConfirmationError(
            "确认结果绑定的版本、覆盖集合或证据快照已经变化", "BINDING_MISMATCH"
        )


def _is_recommendations_input(value: Any) -> bool:
    if isinstance(value, ConfirmationRecommendations):
        return True
    if isinstance(value, Mapping):
        return "items" in value or "recommendations" in value
    return hasattr(value, "summary") or hasattr(value, "manifest")


def validate_confirmation_result(
    result: Any,
    recommendations: Any | None = None,
) -> ConfirmationResult:
    """验证八项结果、自摘要和全部来源/快照身份绑定。

    主调用顺序是 ``(result, recommendations)``；为兼容 adapter 的自然写法，
    也接受 ``(recommendations, result)``，并依据类型自动交换。
    """

    if _is_recommendations_input(result) and recommendations is not None:
        result, recommendations = recommendations, result
    if recommendations is None:
        raise PptxConfirmationError("验证确认结果需要推荐清单", "RECOMMENDATIONS_MISSING")
    recs = _recommendation_model(recommendations)
    submitted = _result_model(result)
    if submitted.session_id != recs.session_id:
        raise PptxConfirmationError("确认结果未绑定当前一次性会话", "SESSION_MISMATCH")
    if submitted.recommendations_sha256 != recs.recommendations_sha256:
        raise PptxConfirmationError("确认结果对应的推荐值已经漂移", "RECOMMENDATIONS_DRIFT")
    _same_binding(submitted.binding, recs.binding)
    if set(submitted.confirmed_values) != set(CONFIRMATION_KEYS):
        raise PptxConfirmationError("确认结果必须恰好覆盖八项", "INCOMPLETE_RESULT")
    return submitted


def validate_confirmation(*args: Any, **kwargs: Any) -> ConfirmationResult:
    """确认结果验证别名。"""

    return validate_confirmation_result(*args, **kwargs)


def build_confirmation_result(
    recommendations: Any,
    confirmed_values: Mapping[str, str] | None = None,
    *,
    confirmed_by: str = "user",
    confirmed_at: datetime | None = None,
    values: Mapping[str, str] | None = None,
) -> ConfirmationResult:
    """从八项用户值构建与推荐清单同绑定的确认结果。"""

    recs = _recommendation_model(recommendations)
    if confirmed_values is None:
        confirmed_values = values
    if confirmed_values is None:
        confirmed_values = {
            item.item_id: item.recommended_value_zh for item in recs.items
        }
    if confirmed_at is None:
        confirmed_at = datetime.now(UTC)
    _aware(confirmed_at, "确认时间")
    base = ConfirmationResult.model_construct(
        schema_version=SCHEMA_VERSION,
        contract_version=CONTRACT_VERSION,
        session_id=recs.session_id,
        project_id=recs.project_id,
        report=recs.report,
        report_version=recs.report_version,
        source_pack_id=recs.source_pack_id,
        source_pack_sha256=recs.source_pack_sha256,
        snapshot_id=recs.snapshot_id,
        snapshot_sha256=recs.snapshot_sha256,
        claim_snapshot_id=recs.claim_snapshot_id,
        evidence_snapshot_id=recs.evidence_snapshot_id,
        coverage_set_id=recs.coverage_set_id,
        recommendations_sha256=recs.recommendations_sha256,
        confirmed_values=dict(confirmed_values),
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
        result_sha256=_ZERO_DIGEST,
    )
    try:
        finalized = _finalize_model(base, "result_sha256", _result_digest, ConfirmationResult)
    except (PydanticValidationError, ValueError) as error:
        raise PptxConfirmationError("确认结果缺字段或包含未知字段", "INCOMPLETE_RESULT") from error
    return validate_confirmation_result(finalized, recs)


def apply_confirmation_result(
    recommendations: Any,
    result: Any,
) -> EffectiveConfirmation:
    """返回用户结果覆盖推荐值后的只读确认视图。"""

    recs = _recommendation_model(recommendations)
    submitted = validate_confirmation_result(result, recs)
    # Keep the mapping detached from the Pydantic model so a caller cannot
    # mutate the persisted confirmation result through the effective view.
    return EffectiveConfirmation(
        session_id=recs.session_id,
        report=recs.report,
        snapshot_id=recs.snapshot_id,
        recommendations_sha256=recs.recommendations_sha256,
        result_sha256=submitted.result_sha256,
        effective_values=dict(submitted.confirmed_values),
    )


def effective_confirmation(*args: Any, **kwargs: Any) -> EffectiveConfirmation:
    """结果覆盖别名。"""

    return apply_confirmation_result(*args, **kwargs)


# ─── one-time session lifecycle ─────────────────────────────────────────────


def open_confirmation_session(
    recommendations: Any,
    *,
    opened_at: datetime | None = None,
    recommendations_path: str | None = None,
    result_path: str = RESULT_PATH,
) -> ConfirmationSession:
    """建立一次性确认会话；相同推荐清单每次得到相同 session_id。"""

    recs = _recommendation_model(recommendations)
    if opened_at is None:
        opened_at = recs.generated_at
    _aware(opened_at, "确认会话打开时间")
    base = ConfirmationSession.model_construct(
        schema_version=SCHEMA_VERSION,
        contract_version=CONTRACT_VERSION,
        session_id=recs.session_id,
        project_id=recs.project_id,
        report=recs.report,
        report_version=recs.report_version,
        source_pack_id=recs.source_pack_id,
        source_pack_sha256=recs.source_pack_sha256,
        snapshot_id=recs.snapshot_id,
        snapshot_sha256=recs.snapshot_sha256,
        claim_snapshot_id=recs.claim_snapshot_id,
        evidence_snapshot_id=recs.evidence_snapshot_id,
        coverage_set_id=recs.coverage_set_id,
        recommendations_sha256=recs.recommendations_sha256,
        recommendations_path=recommendations_path or recs.recommendations_path,
        result_path=result_path,
        state="open",
        opened_at=opened_at,
        closed_at=None,
        result_sha256=None,
        session_sha256=_ZERO_DIGEST,
    )
    return cast(
        ConfirmationSession,
        _finalize_model(base, "session_sha256", _session_digest, ConfirmationSession),
    )


def _validate_result_against_session(
    session: ConfirmationSession,
    result: Any,
) -> ConfirmationResult:
    submitted = _result_model(result)
    if submitted.session_id != session.session_id:
        raise PptxConfirmationError("确认结果未绑定当前会话", "SESSION_MISMATCH")
    if submitted.recommendations_sha256 != session.recommendations_sha256:
        raise PptxConfirmationError("确认结果对应的推荐值已经漂移", "RECOMMENDATIONS_DRIFT")
    _same_binding(submitted.binding, session.binding)
    return submitted


def close_confirmation_session(
    session: ConfirmationSession | Mapping[str, Any],
    result: Any,
    *,
    closed_at: datetime | None = None,
) -> ConfirmationSession:
    """关闭一次性会话；相同结果重放返回原会话，不产生第二次关闭副作用。"""

    if not isinstance(session, ConfirmationSession):
        try:
            session = ConfirmationSession.model_validate(_payload(session, "确认会话"))
        except (PydanticValidationError, PptxConfirmationError) as error:
            raise PptxConfirmationError("确认会话不符合类型合同", "SESSION_INVALID") from error
    submitted = _validate_result_against_session(session, result)
    if session.state == "closed":
        if session.result_sha256 == submitted.result_sha256:
            return session
        raise PptxConfirmationError("确认会话已经关闭，不能重放不同结果", "SESSION_CLOSED")
    if closed_at is None:
        closed_at = submitted.confirmed_at
    _aware(closed_at, "确认会话关闭时间")
    if closed_at < session.opened_at:
        raise PptxConfirmationError("确认会话关闭时间早于打开时间", "SESSION_TIME_INVALID")
    base = session.model_copy(
        update={
            "state": "closed",
            "closed_at": closed_at,
            "result_sha256": submitted.result_sha256,
            "session_sha256": _ZERO_DIGEST,
        }
    )
    return cast(
        ConfirmationSession,
        _finalize_model(base, "session_sha256", _session_digest, ConfirmationSession),
    )


def shutdown_confirmation_session(*args: Any, **kwargs: Any) -> ConfirmationSession:
    """一次性确认页关闭别名；重复同结果调用保持幂等。"""

    return close_confirmation_session(*args, **kwargs)


# ─── JSON persistence ───────────────────────────────────────────────────────


def _canonical_model_bytes(model: BaseModel) -> bytes:
    return _canonical_json(model.model_dump(mode="json"))


def _write_model(
    path: Path,
    model: BaseModel,
    *,
    label: str,
    allow_replace: bool = False,
) -> Path:
    path = Path(path)
    encoded = _canonical_model_bytes(model)
    if path.exists():
        try:
            existing = path.read_bytes()
        except OSError as error:
            raise PptxConfirmationError(f"{label}读取失败：{path}", "IO_ERROR") from error
        if existing == encoded:
            return path
        if not allow_replace:
            raise PptxConfirmationError(f"拒绝覆盖不同的{label}：{path}", "WRITE_CONFLICT")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise PptxConfirmationError(f"{label}写入失败：{path}", "IO_ERROR") from error
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _load_model(path: Path, model_type: type[BaseModel], *, label: str) -> Any:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PptxConfirmationError(f"{label}读取失败：{path}", "READ_ERROR") from error
    try:
        return model_type.model_validate(payload)
    except PydanticValidationError as error:
        raise PptxConfirmationError(f"{label}不符合类型合同：{path}", "INVALID_ARTIFACT") from error


def write_recommendations(
    recommendations: Any,
    path: Path | None = None,
) -> Path:
    recs = _recommendation_model(recommendations)
    target = Path(path or recs.recommendations_path)
    return _write_model(target, recs, label="推荐清单")


def write_confirmation_recommendations(*args: Any, **kwargs: Any) -> Path:
    """推荐清单写入别名。"""

    return write_recommendations(*args, **kwargs)


def load_recommendations(path: Path) -> ConfirmationRecommendations:
    return cast(
        ConfirmationRecommendations,
        _load_model(path, ConfirmationRecommendations, label="推荐清单"),
    )


def load_confirmation_recommendations(path: Path) -> ConfirmationRecommendations:
    return load_recommendations(path)


def write_confirmation_result(result: Any, path: Path = Path(RESULT_PATH)) -> Path:
    submitted = _result_model(result)
    return _write_model(Path(path), submitted, label="确认结果")


def load_confirmation_result(path: Path) -> ConfirmationResult:
    return cast(ConfirmationResult, _load_model(path, ConfirmationResult, label="确认结果"))


def write_confirmation_session(session: Any, path: Path = Path(SESSION_PATH)) -> Path:
    if not isinstance(session, ConfirmationSession):
        try:
            session = ConfirmationSession.model_validate(_payload(session, "确认会话"))
        except (PydanticValidationError, PptxConfirmationError) as error:
            raise PptxConfirmationError("确认会话不符合类型合同", "SESSION_INVALID") from error
    return _write_model(Path(path), session, label="确认会话")


def load_confirmation_session(path: Path) -> ConfirmationSession:
    return cast(ConfirmationSession, _load_model(path, ConfirmationSession, label="确认会话"))


class ConfirmationSessionStore:
    """原子保存、加载和幂等关闭一次性确认会话。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def save(self, session: ConfirmationSession) -> Path:
        return write_confirmation_session(session, self.path)

    def load(self) -> ConfirmationSession:
        return load_confirmation_session(self.path)

    def close(
        self,
        recommendations: Any,
        result: Any,
        *,
        closed_at: datetime | None = None,
    ) -> ConfirmationSession:
        recs = _recommendation_model(recommendations)
        current = self.load()
        if current.session_id != recs.session_id:
            raise PptxConfirmationError("持久化会话与当前推荐清单不一致", "SESSION_MISMATCH")
        # Validate against recommendations before touching the session file.
        submitted = validate_confirmation_result(result, recs)
        closed = close_confirmation_session(current, submitted, closed_at=closed_at)
        if closed is current:
            return current
        _write_model(self.path, closed, label="确认会话", allow_replace=True)
        return closed


# ─── schema validation ───────────────────────────────────────────────────────


def _load_schema() -> JsonObject:
    module_path = Path(__file__).resolve()
    candidates = (
        module_path.parents[4] / "schemas" / SCHEMA_FILENAME,
        module_path.parents[2] / "schemas" / SCHEMA_FILENAME,
    )
    for candidate in candidates:
        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError) as error:
            raise PptxConfirmationError(
                f"确认 Schema 损坏：{candidate}", "SCHEMA_INVALID"
            ) from error
        if not isinstance(raw, dict):
            raise PptxConfirmationError("确认 Schema 顶层必须是对象", "SCHEMA_INVALID")
        return cast(JsonObject, raw)
    raise PptxConfirmationError("无法定位 PPTX 确认 Schema", "SCHEMA_MISSING")


def validate_confirmation_artifact(value: Any) -> BaseModel:
    """按其形态验证推荐、结果或会话，并运行同一 JSON Schema。"""

    from jsonschema import Draft202012Validator, FormatChecker

    raw = _payload(value, "确认产物")
    if "items" in raw:
        model: BaseModel = _recommendation_model(raw)
    elif "confirmed_values" in raw or "values" in raw:
        model = _result_model(raw)
    elif "state" in raw:
        try:
            model = ConfirmationSession.model_validate(raw)
        except PydanticValidationError as error:
            raise PptxConfirmationError("确认会话不符合类型合同", "SESSION_INVALID") from error
    else:
        raise PptxConfirmationError("无法识别确认产物类型", "INVALID_ARTIFACT")
    schema = _load_schema()
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
                model.model_dump(mode="json")
            ),
            key=lambda error: list(error.path),
        )
    except Exception as error:
        raise PptxConfirmationError("确认 Schema 校验失败", "SCHEMA_INVALID") from error
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise PptxConfirmationError(f"确认产物不符合 Schema：{detail}", "SCHEMA_MISMATCH")
    return model


# Explicit names used by adapters/tests.
validate_confirmation_schema = validate_confirmation_artifact


__all__ = [
    "CONFIRMATION_KEYS",
    "CONFIRMATION_ITEM_KEYS",
    "CONTRACT_VERSION",
    "ConfirmationBinding",
    "ConfirmationContractError",
    "ConfirmationError",
    "ConfirmationKey",
    "ConfirmationRecommendation",
    "ConfirmationRecommendations",
    "ConfirmationResult",
    "ConfirmationSession",
    "ConfirmationSessionStore",
    "EffectiveConfirmation",
    "PptxConfirmationError",
    "RECOMMENDATION_KEYS",
    "RECOMMENDATION_PATH",
    "RESULT_PATH",
    "SCHEMA_FILENAME",
    "SCHEMA_VERSION",
    "SESSION_PATH",
    "apply_confirmation_result",
    "build_confirmation_recommendations",
    "build_confirmation_result",
    "build_recommendations",
    "close_confirmation_session",
    "effective_confirmation",
    "load_confirmation_recommendations",
    "load_confirmation_result",
    "load_confirmation_session",
    "load_recommendations",
    "open_confirmation_session",
    "shutdown_confirmation_session",
    "validate_confirmation",
    "validate_confirmation_artifact",
    "validate_confirmation_result",
    "validate_confirmation_schema",
    "write_confirmation_recommendations",
    "write_confirmation_result",
    "write_confirmation_session",
    "write_recommendations",
]
