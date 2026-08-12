"""Task 3.4 控制图核心类型：声明边、守卫结果、迁移请求与不可变节点合同。"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# 封闭输出类型词表用到的序列化枚举值
_REPORT_KIND_VALUES = frozenset({"A", "B", "C"})
_OUTPUT_FORMAT_VALUES = frozenset({"html", "pdf", "html-ppt", "pptx"})


@dataclass(frozen=True)
class DeclaredEdge:
    """一条已声明的合法迁移边：family / from / to / trigger / guard_id。"""

    family: str
    from_state: str | None
    to_state: str
    trigger: str
    guard_id: str


@dataclass(frozen=True)
class GuardResult:
    """结构化守卫求值结果：放行与否 + 确定性理由。"""

    allowed: bool
    reason: str


class TransitionRequest(BaseModel):
    """一次状态迁移尝试；request_id 是该次尝试的稳定幂等身份。

    同一 request_id 重放同一载荷是 no-op；同一 request_id 复用不同载荷
    会通过 EventStore 失败关闭（EventConflictError）。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    request_id: str
    project_id: str
    run_id: str
    family: str
    object_id: str
    from_state: str | None
    to_state: str
    trigger: str
    evidence: dict[str, Any]
    actor_id: str
    occurred_at: datetime

    @field_validator(
        "request_id",
        "project_id",
        "run_id",
        "family",
        "object_id",
        "to_state",
        "trigger",
        "actor_id",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("迁移请求文本字段不能为空")
        return normalized

    @field_validator("occurred_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("迁移请求时间必须包含明确时区偏移")
        return value


@dataclass(frozen=True)
class TypedField:
    """类型化输入/输出字段：name / 类型声明 / 描述。"""

    name: str
    type: str
    description: str


@dataclass(frozen=True)
class RetryPolicy:
    """节点重试策略：最大次数、退避秒数、可重试错误类别。"""

    max_attempts: int
    backoff_seconds: float
    retryable_errors: tuple[str, ...]


@dataclass(frozen=True)
class NodeContract:
    """新建报告图节点合同：完整、版本化、不可变。

    声明版本化类型化输入/输出、完成谓词、读写集、重试策略、声明错误、
    幂等材料、副作用类与 shared/report/artifact 作用域。
    """

    node_id: str
    version: str
    typed_inputs: tuple[TypedField, ...]
    typed_outputs: tuple[TypedField, ...]
    completion_predicate: Callable[[dict[str, Any]], bool]
    completion_summary: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    retry_policy: RetryPolicy
    declared_errors: tuple[str, ...]
    idempotency_material: tuple[str, ...]
    side_effect_class: str
    scope: str


def _is_nonblank_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_output_value(type_decl: str, value: Any) -> bool:
    """封闭类型词表：非空 str / 严格 bool / 非空字符串列表 / 证据引用列表 /
    字典 / ReportKind、OutputFormat 序列化枚举值及其列表形式。"""
    normalized = type_decl.strip().lower()
    if normalized == "str":
        return _is_nonblank_str(value)
    if normalized == "bool":
        return isinstance(value, bool)
    if normalized in ("tuple[str]", "list[str]"):
        return isinstance(value, (list, tuple)) and all(
            _is_nonblank_str(item) for item in value
        )
    if normalized == "reportkind":
        return value in _REPORT_KIND_VALUES
    if normalized in ("tuple[reportkind]", "list[reportkind]"):
        return isinstance(value, (list, tuple)) and all(
            item in _REPORT_KIND_VALUES for item in value
        )
    if normalized == "outputformat":
        return value in _OUTPUT_FORMAT_VALUES
    if normalized in ("tuple[outputformat]", "list[outputformat]"):
        return isinstance(value, (list, tuple)) and all(
            item in _OUTPUT_FORMAT_VALUES for item in value
        )
    if normalized in ("evidencereference", "tuple[evidencereference]", "list[evidencereference]"):
        refs = value if normalized != "evidencereference" else [value]
        if not isinstance(refs, (list, tuple)):
            return False
        for ref in refs:
            if not isinstance(ref, dict):
                return False
            fragment_id = ref.get("fragment_id")
            sha256 = ref.get("sha256")
            if not _is_nonblank_str(fragment_id):
                return False
            if not isinstance(sha256, str) or _SHA256_RE.fullmatch(sha256) is None:
                return False
        return True
    if normalized in ("dict[str, object]", "dict"):
        return isinstance(value, dict)
    raise ValueError(f"未知输出类型声明: {type_decl}")


def validate_typed_outputs(contract: NodeContract, outputs: dict[str, Any]) -> None:
    """按合同声明的封闭类型词表校验输出；任一字段类型不合法即失败关闭。"""
    for field in contract.typed_outputs:
        value = outputs.get(field.name)
        if not _check_output_value(field.type, value):
            raise ValueError(
                f"{contract.node_id}.{field.name} 输出类型不合法: {value!r}"
            )
