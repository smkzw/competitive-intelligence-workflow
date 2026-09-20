"""Project-level persistence for the once-per-project Yaozh access answer.

v1.3 §1.2/§5.3：每个新项目只询问一次药智网访问条件。本模块把该回答绑定到
已验证的项目工作区并持久化；持久记录是封闭对象，不含用户名、密码、
Cookie、会话令牌、授权头、浏览器存储或任意元数据。相同回答幂等重放，
不同回答失败关闭，被改写或身份不一致的记录同样失败关闭。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Self, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ci_workflow.application.intake import (
    YaozhAccessRecord,
    YaozhAnswer,
    YaozhRouteDecision,
    record_yaozh_answer,
    yaozh_route_decision,
)
from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    verify_project_workspace,
)

YAOZH_ACCESS_RECORD_PATH = "state/yaozh-access.json"
YAOZH_ROUTE_RECEIPT_DIRECTORY = "state/yaozh-route-access"
INITIAL_ANSWERS: frozenset[str] = frozenset({"available", "unavailable", "skipped"})
YAOZH_REUSE_WINDOW = timedelta(minutes=5)


class YaozhAccessError(ValueError):
    """药智访问回答无法记录、读取或与项目绑定。"""


@dataclass(frozen=True)
class YaozhAccessOutcome:
    record: YaozhAccessRecord
    record_path: Path
    replayed: bool
    decision: YaozhRouteDecision


@dataclass(frozen=True)
class YaozhRouteAccessOutcome:
    receipt: YaozhRouteAccessReceipt
    receipt_path: Path
    replayed: bool


class YaozhRouteAccessReceipt(BaseModel):
    """Credential-free runtime status for the optional browser route."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    run_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.:-]{1,160}$", exclude_if=lambda value: value is None,
    )
    route_id: Literal["yaozh-optional-browser"] = "yaozh-optional-browser"
    answer_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    host: Literal["local", "codex", "hermes", "omp"]
    technical_state: Literal[
        "ready",
        "session_expired",
        "captcha_required",
        "permission_denied",
        "tool_unavailable",
        "parser_error",
    ]
    result_class: Literal["ready", "access_blocked", "parser_error"]
    user_action_zh: str
    blocks_core_research: Literal[False] = False
    credential_fields_allowed: Literal[False] = False

    @model_validator(mode="after")
    def _state_and_result_match(self) -> Self:
        if self.observed_at.utcoffset() is None:
            raise ValueError("药智会话回执时间必须包含时区")
        expected = {
            "ready": "ready",
            "session_expired": "access_blocked",
            "captcha_required": "access_blocked",
            "permission_denied": "access_blocked",
            "tool_unavailable": "access_blocked",
            "parser_error": "parser_error",
        }[self.technical_state]
        if self.result_class != expected:
            raise ValueError("药智技术访问状态与结果分类不一致")
        if not self.user_action_zh.strip():
            raise ValueError("药智技术访问指引不能为空")
        return self


class YaozhSessionObservation(BaseModel):
    """Host observation of Yaozh access; deliberately excludes session material."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    run_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.:-]{1,160}$", exclude_if=lambda value: value is None,
    )
    answer_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    host: Literal["local", "codex", "hermes", "omp"]
    observer_id: str
    origin: str
    technical_state: Literal[
        "ready",
        "session_expired",
        "captcha_required",
        "permission_denied",
        "tool_unavailable",
        "parser_error",
    ]
    page_marker_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _safe_observation(self) -> Self:
        if self.observed_at.utcoffset() is None:
            raise ValueError("药智会话观察时间必须包含时区")
        if self.observed_at > datetime.now(self.observed_at.tzinfo) + timedelta(minutes=1):
            raise ValueError("药智会话观察时间不得来自未来")
        parsed = urlsplit(self.origin)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "vip.yaozh.com"
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("药智会话观察只能绑定规范企业版来源 origin")
        for label, value in (("project_id", self.project_id), ("observer_id", self.observer_id)):
            normalized = " ".join(value.split())
            if not normalized or "/" in normalized or "\\" in normalized:
                raise ValueError(f"{label} 不能为空或包含本机路径")
            lowered = normalized.casefold()
            if any(
                token in lowered
                for token in (
                    "password", "passwd", "username", "cookie", "sessionid",
                    "token", "authorization", "secret", "credentials", "api-key",
                    "api_key", "bearer ",
                )
            ):
                raise ValueError(f"{label} 不得包含会话或凭据内容")
        return self


def _observation_digest(observation: YaozhSessionObservation) -> str:
    encoded = json.dumps(
        observation.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _receipt_bytes(receipt: YaozhRouteAccessReceipt) -> bytes:
    serialized = json.dumps(
        receipt.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True
    )
    return f"{serialized}\n".encode()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _record_bytes(record: YaozhAccessRecord) -> bytes:
    serialized = json.dumps(
        record.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True
    )
    return f"{serialized}\n".encode()


def _read_validated_record(path: Path, *, project_id: str) -> YaozhAccessRecord:
    if path.is_symlink() or not path.is_file():
        raise YaozhAccessError("药智访问回答记录必须是普通文件；失败关闭，不重复询问")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise YaozhAccessError("药智访问回答记录无法读取；失败关闭，不重复询问") from exc
    if not isinstance(payload, dict):
        raise YaozhAccessError("药智访问回答记录顶层必须是对象；失败关闭，不重复询问")
    try:
        record = YaozhAccessRecord.model_validate(payload)
    except ValueError as exc:
        # 校验诊断可能回显被改写的值；只给出封闭的中文结论。
        raise YaozhAccessError(
            "药智访问回答记录不符合合同（含多余字段或被改动）；失败关闭，不重复询问"
        ) from exc
    if record.project_id != project_id:
        raise YaozhAccessError("药智访问回答记录与当前项目身份不一致；失败关闭")
    return record


def _project_binding(project_root: Path) -> tuple[Path, str]:
    try:
        contract = verify_project_workspace(project_root).contract
    except ProjectWorkspaceError as exc:
        raise YaozhAccessError(f"项目目录无法通过验证：{exc}") from exc
    root = project_root.expanduser().resolve()
    return root / YAOZH_ACCESS_RECORD_PATH, contract.project_id


def answer_yaozh_access(
    project_root: Path,
    answer: str,
    *,
    asked_at: datetime | None = None,
) -> YaozhAccessOutcome:
    """Record the one project answer; identical replay is idempotent."""

    if answer not in INITIAL_ANSWERS:
        raise YaozhAccessError(
            "药智访问回答只能是 available、unavailable 或 skipped（无账号可跳过）"
        )
    record_path, project_id = _project_binding(project_root)
    if record_path.is_symlink() or record_path.exists():
        existing = _read_validated_record(record_path, project_id=project_id)
        if existing.answer != answer:
            raise YaozhAccessError(
                "同一项目的药智网访问条件只能回答一次；"
                f"已记录回答为 {existing.answer}，拒绝改写为 {answer}"
            )
        return YaozhAccessOutcome(
            record=existing,
            record_path=record_path,
            replayed=True,
            decision=yaozh_route_decision(existing),
        )
    # INITIAL_ANSWERS 是 YaozhAnswer 初始询问取值的子集，上面的成员检查已收窄类型。
    record = record_yaozh_answer(
        project_id, cast(YaozhAnswer, answer), asked_at=asked_at
    )
    _atomic_write(record_path, _record_bytes(record))
    return YaozhAccessOutcome(
        record=record,
        record_path=record_path,
        replayed=False,
        decision=yaozh_route_decision(record),
    )


def load_yaozh_access_record(project_root: Path) -> YaozhAccessRecord | None:
    """Read the persisted answer for downstream routing; None when not yet asked."""

    record_path, project_id = _project_binding(project_root)
    if record_path.is_symlink():
        return _read_validated_record(record_path, project_id=project_id)
    if not record_path.exists():
        return None
    return _read_validated_record(record_path, project_id=project_id)


def build_yaozh_route_access_receipt(
    record: YaozhAccessRecord,
    observation: YaozhSessionObservation,
) -> YaozhRouteAccessReceipt:
    """Describe runtime access without mutating the once-only project answer."""

    if not record.route_enabled:
        raise YaozhAccessError("未启用药智可选路线时不得生成运行期访问回执")
    answer_digest = hashlib.sha256(_record_bytes(record)).hexdigest()
    if observation.project_id != record.project_id:
        raise YaozhAccessError("药智会话观察与当前项目身份不一致")
    if observation.answer_digest != answer_digest:
        raise YaozhAccessError("药智会话观察未绑定当前项目回答字节")
    actions = {
        "ready": "无需处理；药智仍只用于线索与交叉核验。",
        "session_expired": "请在浏览器中自行登录药智网后继续该辅助路线。",
        "captcha_required": "请在浏览器中自行完成药智网验证后继续；系统不会绕过验证码。",
        "permission_denied": "请核对药智企业版访问权限；其他适格来源将继续研究。",
        "tool_unavailable": "请启用可操作已登录浏览器的宿主能力后继续该辅助路线。",
        "parser_error": "药智页面已访问但未能安全解析；请更换解析策略后重试该辅助路线。",
    }
    return YaozhRouteAccessReceipt(
        project_id=record.project_id,
        run_id=observation.run_id,
        answer_digest=answer_digest,
        observation_digest=_observation_digest(observation),
        observed_at=observation.observed_at,
        host=observation.host,
        technical_state=observation.technical_state,
        result_class=(
            "ready"
            if observation.technical_state == "ready"
            else "parser_error"
            if observation.technical_state == "parser_error"
            else "access_blocked"
        ),
        user_action_zh=actions[observation.technical_state],
    )


def persist_yaozh_route_access_receipt(
    project_root: Path,
    observation: YaozhSessionObservation,
) -> YaozhRouteAccessOutcome:
    """Persist one immutable, content-addressed, credential-free route receipt."""

    record_path, project_id = _project_binding(project_root)
    root = record_path.parent.parent
    record = load_yaozh_access_record(root)
    if record is None:
        raise YaozhAccessError("药智访问条件尚未回答，不得提交会话观察")
    if observation.project_id != project_id:
        raise YaozhAccessError("药智会话观察与当前项目身份不一致")
    receipt = build_yaozh_route_access_receipt(record, observation)
    directory = root / YAOZH_ROUTE_RECEIPT_DIRECTORY
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise YaozhAccessError("药智运行期回执目录必须是项目内普通目录")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{receipt.observation_digest}.json"
    encoded = _receipt_bytes(receipt)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise YaozhAccessError("药智运行期回执目标必须是普通文件")
    if path.exists():
        if path.read_bytes() != encoded:
            raise YaozhAccessError("药智运行期回执摘要冲突，拒绝覆盖")
        return YaozhRouteAccessOutcome(receipt=receipt, receipt_path=path, replayed=True)
    _atomic_write(path, encoded)
    return YaozhRouteAccessOutcome(receipt=receipt, receipt_path=path, replayed=False)


class YaozhRuntimeAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["recheck_required", "reuse_available", "access_blocked", "not_applicable"]
    reuse_allowed: bool = False
    blocks_core_research: Literal[False] = False
    run_id: str | None = None
    instruction_zh: str


def check_yaozh_runtime_access(
    project_root: Path, *, host: str, now: datetime | None = None,
) -> YaozhRuntimeAccess:
    """Consume current-run observations; availability is not scientific acceptance."""
    from ci_workflow.application.run_service import RunError, validate_run_manifest

    now = now or datetime.now(UTC)
    if now.utcoffset() is None:
        raise YaozhAccessError("访问检查时间必须包含时区")
    record = load_yaozh_access_record(project_root)
    if record is not None and not record.route_enabled:
        return YaozhRuntimeAccess(
            state="not_applicable", instruction_zh="本项目未启用药智路线，继续其他适格来源。",
        )
    instruction = "请在当前运行实际检查浏览器访问；历史回答不是登录证明。"
    if record is None:
        return YaozhRuntimeAccess(state="recheck_required", instruction_zh=instruction)
    try:
        manifest = validate_run_manifest(project_root)
        run_id = str(manifest["run_id"])
        started_at = datetime.fromisoformat(manifest["started_at"])
    except (RunError, OSError, ValueError, KeyError, TypeError) as error:
        raise YaozhAccessError("当前运行身份无法验证；不得复用药智会话观察") from error
    directory = project_root / YAOZH_ROUTE_RECEIPT_DIRECTORY
    if directory.is_symlink():
        raise YaozhAccessError("药智回执目录不得是符号链接")
    matching = []
    for path in directory.glob("*.json"):
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("receipt path")
            receipt = YaozhRouteAccessReceipt.model_validate_json(path.read_bytes())
            if path.stem != receipt.observation_digest or receipt.project_id != record.project_id:
                raise ValueError("receipt identity")
        except (OSError, ValueError) as error:
            raise YaozhAccessError("药智回执损坏，必须重新核验，不得沿用历史成功") from error
        if (
            receipt.run_id == run_id and receipt.host == host
            and receipt.answer_digest == hashlib.sha256(_record_bytes(record)).hexdigest()
            and started_at <= receipt.observed_at <= now
        ):
            matching.append(receipt)
    if not matching:
        return YaozhRuntimeAccess(
            state="recheck_required", run_id=run_id, instruction_zh=instruction,
        )
    # At equal timestamps a failure takes precedence over a success.
    latest = max(matching, key=lambda item: (item.observed_at, item.technical_state != "ready"))
    if latest.technical_state != "ready":
        return YaozhRuntimeAccess(
            state="access_blocked", run_id=run_id, instruction_zh=latest.user_action_zh,
        )
    if now - latest.observed_at >= YAOZH_REUSE_WINDOW:
        return YaozhRuntimeAccess(
            state="recheck_required", run_id=run_id, instruction_zh=instruction,
        )
    return YaozhRuntimeAccess(
        state="reuse_available", reuse_allowed=True, run_id=run_id,
        instruction_zh="仅本运行本宿主短期复用；任何访问失败必须立即记录并重检。",
    )


__all__ = [
    "INITIAL_ANSWERS",
    "YAOZH_ACCESS_RECORD_PATH",
    "YAOZH_ROUTE_RECEIPT_DIRECTORY",
    "YaozhAccessError",
    "YaozhAccessOutcome",
    "YaozhRouteAccessReceipt",
    "YaozhRouteAccessOutcome",
    "YaozhSessionObservation",
    "answer_yaozh_access",
    "build_yaozh_route_access_receipt",
    "load_yaozh_access_record",
    "persist_yaozh_route_access_receipt",
    "check_yaozh_runtime_access",
]
