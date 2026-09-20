"""Task 9.3 可选监测服务：去重变更候选、追加事件、技术诊断、用户处置与只读刷新交接。

边界（design.md）：监测是可选叶子能力，本服务只依赖
:mod:`ci_workflow.domain.monitoring` 的机器合同与既有事件库；不调用
:class:`~ci_workflow.application.refresh_service.RefreshService` 的任何接受、
快照或发布动作，不新增数据库表和迁移，不修改事实表、声明表、正式快照
或报告目录。用户明确选择"启动正常刷新"后，本服务只生成绑定候选与当前
合同版本的只读刷新交接单；Task 9.2 正常刷新仍需重新核验来源、证据门槛、
影响图和科学质控。

- 候选身份由去重摘要稳定派生（:func:`ci_workflow.domain.monitoring.\
monitoring_dedupe_digest`）：相同业务变化的重复发现返回同一候选并追加
  发现历史，不重复提醒；同一来源但不同定位、版本或候选值形成不同候选。
  归约结束的聚合边界调用 ``verify_candidate_dedupe_identity`` 重推导，
  不信任 ``model_copy(update=...)`` 后的缓存字段。
- 事件流（``events/events.jsonl``）是真源：首次发现、重复发现、诊断更新、
  用户处置、刷新交接与观察回执分别有稳定事件与幂等键；``monitoring/inbox``
  中的候选 JSON 只是当前投影（§17.3 schema），缺失或漂移时由事件归约自愈
  重建。同一幂等键不同载荷由 :class:`~ci_workflow.storage.event_store.\
EventStore` 失败关闭。
- "启动正常刷新"的处置与只读交接单在同一操作内落账：§17.3 schema 要求
  该处置状态下投影必须携带交接单，因此不持久化中间状态；中断后重放同一
  操作幂等补齐。
- 技术获取失败与"已完成但没有变化""来源确认未公开目标信息"严格分开建模；
  未达到恢复次数或未提供已尝试方法时，不得标为"需要用户协助"（失败关闭）。
- 用户处置只有待处理、启动正常刷新、暂不处理三种；处置是追加事件，不删除
  候选、不改写历史；精确重放幂等。
- 面向用户的表述只有自然中文；机器状态只保存在合同字段中。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.monitoring import (
    MONITORING_CANDIDATE_DIAGNOSTIC_EVENT,
    MONITORING_CANDIDATE_DISCOVERED_EVENT,
    MONITORING_CANDIDATE_DISPOSITION_EVENT,
    MONITORING_CANDIDATE_REDISCOVERED_EVENT,
    MONITORING_REFRESH_HANDOFF_EVENT,
    ChangeType,
    DiagnosticStatus,
    FailureCategory,
    MonitoringChangeCandidate,
    MonitoringContractError,
    MonitoringDiagnosticRecord,
    MonitoringDiscoveryRecord,
    MonitoringRefreshHandoff,
    MonitoringSourceIdentity,
    MonitoringUserDispositionRecord,
    ObservationOutcome,
    UserDisposition,
    build_change_candidate,
    build_refresh_handoff,
    candidate_id_from_digest,
    failure_category_zh,
    monitoring_dedupe_digest,
    outcome_guidance_zh,
    verify_candidate_dedupe_identity,
    verify_refresh_handoff_addressing,
)
from ci_workflow.storage.event_store import EventStore, WorkflowEvent

_RUN_ID = "monitoring"
_DEFAULT_RECOVERY_ATTEMPT_LIMIT = 3

# 观察回执事件：无变化、确认未公开与技术失败不创建候选，只写事件与回执。
_OBSERVATION_EVENT = "monitoring.observation.recorded"

_RECEIPT_OUTCOMES: tuple[str, ...] = (
    "no_change",
    "confirmed_not_public",
    "technical_failure_recoverable",
    "needs_user_assistance",
)

_CJK_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF))


class MonitoringServiceError(RuntimeError):
    """监测服务合同失败；消息中文陈述事实。"""


class MonitoringObservationError(MonitoringServiceError):
    """来源观察不符合机器合同。"""


class MonitoringAssistanceError(MonitoringServiceError):
    """未达到恢复合同就要求用户协助，或已达上限仍标为可自动恢复；失败关闭。"""


class MonitoringNotFoundError(MonitoringServiceError):
    """变更候选或刷新交接单不存在。"""


class MonitoringStateError(MonitoringServiceError):
    """当前监测状态不允许该操作。"""


class MonitoringConflictError(MonitoringServiceError):
    """同一候选或幂等键对应了不同业务载荷。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("监测字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("监测时间必须包含明确时区偏移")
    return value


def _require_prose_zh(value: str, field_name: str) -> str:
    """用户可见文本必须包含汉字且不是内部工程化标签（§17.3 schema 口径）。

    返回 ValueError 供模型校验器转为 ValidationError；服务操作边界请改用
    :func:`_require_prose_zh_or_fail` 以中文服务错误失败关闭。
    """

    normalized = _not_blank(value)
    has_cjk = any(any(low <= ord(char) <= high for low, high in _CJK_RANGES) for char in normalized)
    if not has_cjk:
        raise ValueError(f"{field_name}必须是面向用户的中文说明")
    return normalized


def _require_prose_zh_or_fail(value: str, field_name: str) -> str:
    """服务操作边界的中文说明校验；不合规输入以中文服务错误失败关闭。"""

    try:
        return _require_prose_zh(value, field_name)
    except ValueError as error:
        raise MonitoringServiceError(str(error)) from error


def _canonical_json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_digest(value: object) -> str:
    return hashlib.sha256(_canonical_json_text(value).encode("utf-8")).hexdigest()


# ── 服务层输入与回执合同 ─────────────────────────────────────────────────────


class MonitoringObservation(BaseModel):
    """调用方已完成的来源观察；监测服务不复制网络抓取逻辑。

    结果词表与 :data:`ci_workflow.domain.monitoring.ObservationOutcome` 一致：
    发现变化 / 完成但无变化 / 来源确认未公开 / 技术获取失败仍可自动恢复 /
    多轮恢复后仍失败需要用户协助。载荷必须与结果匹配，混装失败关闭。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    source_identity: MonitoringSourceIdentity
    outcome: ObservationOutcome
    observed_at: datetime
    observer: str
    # 发现变化的载荷（其余结果不得携带）
    discovery_note_zh: str | None = None
    entity_id: str | None = None
    claim_domain: str | None = None
    change_type: ChangeType | None = None
    current_value: str | None = None
    candidate_value: str | None = None
    possibly_affected_reports: tuple[str, ...] = ()
    possibly_affected_page_ids: tuple[str, ...] = ()
    acquired_with_user_assistance: bool = False
    # 技术失败载荷（其余结果不得携带）
    failure_category: FailureCategory | None = None
    attempts: int | None = Field(default=None, ge=1)
    methods_tried_zh: tuple[str, ...] = ()
    next_step_zh: str | None = None
    note_zh: str | None = None

    @field_validator("project_id", "observer")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("discovery_note_zh", "next_step_zh")
    @classmethod
    def _visible_prose_is_chinese(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        if value is None:
            return None
        field_name = "发现说明" if info.field_name == "discovery_note_zh" else "下一步"
        return _require_prose_zh(value, field_name)

    @field_validator("methods_tried_zh")
    @classmethod
    def _recovery_methods_are_chinese_and_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        methods = tuple(_require_prose_zh(item, "已尝试方法") for item in value)
        if len(methods) != len(set(methods)):
            raise ValueError("已尝试方法不得重复")
        return methods

    @field_validator("observed_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _payload_matches_outcome(self) -> MonitoringObservation:
        change_fields = (
            self.discovery_note_zh,
            self.entity_id,
            self.claim_domain,
            self.change_type,
            self.current_value,
            self.candidate_value,
        )
        if self.outcome == "change_found":
            if any(field is None for field in change_fields):
                raise ValueError(
                    "发现变化的观察必须同时携带发现说明、实体、声明域、变化类型与当前/候选值"
                )
            if not self.possibly_affected_reports:
                raise ValueError("发现变化的观察必须声明至少一类可能受影响的报告")
            for item in self.possibly_affected_reports:
                if item not in ("A", "B", "C"):
                    raise ValueError("可能受影响报告只能是 A、B 或 C")
        elif any(field is not None for field in change_fields):
            raise ValueError("未发现变化的观察不得携带变更候选材料")
        if self.outcome in ("technical_failure_recoverable", "needs_user_assistance"):
            diagnostic_fields = (self.failure_category, self.attempts, self.next_step_zh)
            if any(field is None for field in diagnostic_fields):
                raise ValueError("技术失败观察必须同时记录失败类别、尝试轮次与下一步")
            if not self.methods_tried_zh:
                raise ValueError("技术失败观察必须记录已尝试方法")
        elif (
            self.failure_category is not None
            or self.attempts is not None
            or self.next_step_zh is not None
            or self.methods_tried_zh
        ):
            raise ValueError("非技术失败观察不得携带诊断材料")
        return self


class MonitoringObservationReceipt(BaseModel):
    """一次监测观察的回执；无变化与技术失败只写事件与回执，不创建空候选。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    receipt_id: str
    project_id: str
    source_identity: MonitoringSourceIdentity
    outcome: ObservationOutcome
    observed_at: datetime
    observer: str
    guidance_zh: str
    candidate_id: str | None = None
    rediscovered: bool = False
    failure_category: FailureCategory | None = None
    attempts: int | None = None
    methods_tried_zh: tuple[str, ...] = ()
    next_step_zh: str | None = None
    note_zh: str | None = None

    @field_validator("receipt_id", "project_id", "observer", "guidance_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("guidance_zh")
    @classmethod
    def _guidance_is_prose(cls, value: str) -> str:
        return _require_prose_zh(value, "回执用户提示")

    @field_validator("observed_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


# ── 服务 ─────────────────────────────────────────────────────────────────────


class MonitoringService:
    """可选监测服务：submit_observation / record_diagnosis / apply_disposition /
    create_refresh_handoff / load / load_handoff / list_candidates。"""

    def __init__(
        self,
        project_root: Path,
        *,
        recovery_attempt_limit: int = _DEFAULT_RECOVERY_ATTEMPT_LIMIT,
    ) -> None:
        if recovery_attempt_limit < 1:
            raise MonitoringServiceError("恢复尝试上限必须至少为 1")
        self.project_root = project_root.resolve()
        self.recovery_attempt_limit = recovery_attempt_limit
        self.event_store = EventStore(self.project_root)

    # ── 路径 ───────────────────────────────────────────────────────────────

    def _inbox_dir(self) -> Path:
        return self.project_root / "monitoring" / "inbox"

    def _handoff_dir(self) -> Path:
        return self.project_root / "monitoring" / "handoffs"

    def _receipt_path(self) -> Path:
        return self.project_root / "receipts" / "monitoring_observations.jsonl"

    # ── 事件与投影 ─────────────────────────────────────────────────────────

    def _append_event(
        self,
        *,
        event_type: str,
        event_kind: str,
        project_id: str,
        actor_id: str,
        occurred_at: datetime,
        payload: dict[str, Any],
        idempotency_key: str,
        identity: str,
    ) -> None:
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(
                event_kind,
                project_id,
                _RUN_ID,
                identity,
                _payload_digest(payload),
            ),
            project_id=project_id,
            run_id=_RUN_ID,
            event_type=event_type,
            occurred_at=occurred_at,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            payload=payload,
        )
        self.event_store.append(event)

    @staticmethod
    def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temp_name, path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise

    # ── 操作 1：submit_observation ────────────────────────────────────────

    def submit_observation(
        self, observation: MonitoringObservation
    ) -> MonitoringObservationReceipt:
        """提交一次已完成的来源观察。

        发现变化时按去重摘要登记或合并候选；无变化、确认未公开与技术失败
        只写事件与回执，不创建空候选。技术失败未达恢复合同不得要求用户协助。
        """

        _, active_project_id = self._active_contract_identity()
        if observation.project_id != active_project_id:
            raise MonitoringObservationError(
                "来源观察所属项目与当前项目不一致，未写入任何监测记录。"
            )
        observed_at = _offset_datetime(observation.observed_at)
        if observation.outcome == "change_found":
            return self._submit_change(observation, observed_at)
        return self._submit_non_change(observation, observed_at)

    def _submit_change(
        self, observation: MonitoringObservation, observed_at: datetime
    ) -> MonitoringObservationReceipt:
        if (
            observation.entity_id is None
            or observation.claim_domain is None
            or observation.change_type is None
            or observation.current_value is None
            or observation.candidate_value is None
            or observation.discovery_note_zh is None
        ):
            # 模型合同已在构造边界校验；此处兜底失败关闭。
            raise MonitoringObservationError("发现变化的观察缺少变更候选材料")
        # 聚合边界重新计算摘要；候选 ID 由摘要派生，不信任调用方缓存。
        dedupe_digest = monitoring_dedupe_digest(
            project_id=observation.project_id,
            source_identity=observation.source_identity,
            entity_id=observation.entity_id,
            claim_domain=observation.claim_domain,
            change_type=observation.change_type,
            current_value=observation.current_value,
            candidate_value=observation.candidate_value,
        )
        candidate_id = candidate_id_from_digest(dedupe_digest)
        normalized_note = _require_prose_zh_or_fail(observation.discovery_note_zh, "发现说明")
        discovery = MonitoringDiscoveryRecord(
            observed_at=observed_at,
            observer=observation.observer,
            outcome="change_found",
            note_zh=normalized_note,
        )
        existing = self._reduce_candidate(candidate_id)
        if existing is None:
            try:
                candidate = build_change_candidate(
                    project_id=observation.project_id,
                    source_identity=observation.source_identity,
                    discovered_at=observed_at,
                    observer=observation.observer,
                    discovery_note_zh=normalized_note,
                    entity_id=observation.entity_id,
                    claim_domain=observation.claim_domain,
                    change_type=observation.change_type,
                    current_value=observation.current_value,
                    candidate_value=observation.candidate_value,
                    possibly_affected_reports=tuple(sorted(observation.possibly_affected_reports)),
                    possibly_affected_page_ids=tuple(observation.possibly_affected_page_ids),
                    acquisition_status=(
                        "acquired_with_user_assistance"
                        if observation.acquired_with_user_assistance
                        else "acquired"
                    ),
                )
            except ValueError as error:
                raise MonitoringObservationError(f"变更候选无法按合同构造：{error}") from error
            self._append_event(
                event_type=MONITORING_CANDIDATE_DISCOVERED_EVENT,
                event_kind="monitoring-discovery",
                project_id=candidate.project_id,
                actor_id=observation.observer,
                occurred_at=observed_at,
                payload={"candidate": candidate.model_dump(mode="json")},
                idempotency_key=f"monitoring.candidate.discovered:{candidate_id}",
                identity=candidate_id,
            )
            rediscovered = False
            guidance = outcome_guidance_zh("change_found")
        else:
            if existing.project_id != observation.project_id:
                raise MonitoringConflictError("同一候选身份对应了不同项目，必须失败关闭")
            verify_candidate_dedupe_identity(existing)
            if existing.dedupe_digest != dedupe_digest:
                raise MonitoringConflictError("同一候选身份对应了不同业务载荷，必须失败关闭")
            was_known = discovery in existing.discoveries
            if not was_known:
                self._append_event(
                    event_type=MONITORING_CANDIDATE_REDISCOVERED_EVENT,
                    event_kind="monitoring-rediscovery",
                    project_id=existing.project_id,
                    actor_id=observation.observer,
                    occurred_at=observed_at,
                    payload={
                        "candidate_id": candidate_id,
                        "discovery": discovery.model_dump(mode="json"),
                    },
                    idempotency_key=(
                        "monitoring.candidate.rediscovered:"
                        + stable_id(
                            "monitoring-discovery", candidate_id, discovery.model_dump_json()
                        )
                    ),
                    identity=candidate_id,
                )
            # 首次发现的精确重放按首次登记回执返回；其余都是并入既有历史。
            rediscovered = not (was_known and len(existing.discoveries) == 1)
            if rediscovered:
                guidance = (
                    "同一变化此前已登记，本次发现已并入该候选的发现历史，不会重复提醒；"
                    "是否启动正常刷新仍由您决定。"
                )
            else:
                guidance = outcome_guidance_zh("change_found")
        # 归约并自愈投影后返回回执
        self.load(candidate_id)
        return MonitoringObservationReceipt(
            receipt_id=stable_id(
                "monitoring-receipt",
                observation.project_id,
                candidate_id,
                observed_at.isoformat(),
                _payload_digest(
                    {
                        "outcome": "change_found",
                        "observer": observation.observer,
                        "note_zh": observation.note_zh,
                    }
                ),
            ),
            project_id=observation.project_id,
            source_identity=observation.source_identity,
            outcome="change_found",
            observed_at=observed_at,
            observer=observation.observer,
            guidance_zh=guidance,
            candidate_id=candidate_id,
            rediscovered=rediscovered,
            note_zh=observation.note_zh,
        )

    def _submit_non_change(
        self, observation: MonitoringObservation, observed_at: datetime
    ) -> MonitoringObservationReceipt:
        outcome = observation.outcome
        if outcome not in _RECEIPT_OUTCOMES:
            raise MonitoringObservationError(f"未知观察结果：{outcome}")
        if outcome == "technical_failure_recoverable":
            attempts = int(observation.attempts or 0)
            if attempts >= self.recovery_attempt_limit:
                raise MonitoringAssistanceError(
                    f"恢复尝试已达到上限（{self.recovery_attempt_limit} 轮），"
                    "必须按需要用户协助上报，不能继续标为可自动恢复"
                )
        if outcome == "needs_user_assistance":
            attempts = int(observation.attempts or 0)
            if attempts < self.recovery_attempt_limit:
                raise MonitoringAssistanceError(
                    f"恢复尝试尚未达到上限（{attempts}/{self.recovery_attempt_limit} 轮），"
                    "不得要求用户协助，请先按恢复策略自动重试"
                )
            if not observation.methods_tried_zh:
                raise MonitoringAssistanceError("要求用户协助前必须记录已尝试的恢复方法")
        receipt = MonitoringObservationReceipt(
            receipt_id=stable_id(
                "monitoring-receipt",
                observation.project_id,
                observation.source_identity.source_stable_id,
                observed_at.isoformat(),
                _payload_digest(
                    {
                        "outcome": outcome,
                        "observer": observation.observer,
                        "note_zh": observation.note_zh,
                    }
                ),
            ),
            project_id=observation.project_id,
            source_identity=observation.source_identity,
            outcome=outcome,
            observed_at=observed_at,
            observer=observation.observer,
            guidance_zh=self._observation_guidance(observation),
            failure_category=observation.failure_category,
            attempts=observation.attempts,
            methods_tried_zh=tuple(observation.methods_tried_zh),
            next_step_zh=observation.next_step_zh,
            note_zh=observation.note_zh,
        )
        self._append_event(
            event_type=_OBSERVATION_EVENT,
            event_kind="monitoring-observation",
            project_id=observation.project_id,
            actor_id=observation.observer,
            occurred_at=observed_at,
            payload={"receipt": receipt.model_dump(mode="json")},
            idempotency_key=f"monitoring.observation.recorded:{receipt.receipt_id}",
            identity=receipt.receipt_id,
        )
        self._append_receipt(receipt)
        return receipt

    def _observation_guidance(self, observation: MonitoringObservation) -> str:
        """组合回执级中文提示：说明阻断原因（含失败类别与轮次）与用户要做什么。"""

        if observation.outcome == "technical_failure_recoverable":
            category = failure_category_zh(str(observation.failure_category))
            attempts = int(observation.attempts or 0)
            return (
                f"来源获取遇到{category}，正在按恢复策略自动重试（已尝试 {attempts} 轮），"
                "暂时不需要您处理。"
            )
        if observation.outcome == "needs_user_assistance":
            category = failure_category_zh(str(observation.failure_category))
            attempts = int(observation.attempts or 0)
            step = str(observation.next_step_zh)
            return (
                f"已按恢复策略完成 {attempts} 轮重试仍无法获取该来源（{category}）；"
                f"请您{step}，完成后监测将继续。"
            )
        return outcome_guidance_zh(str(observation.outcome))

    # ── 操作 2：record_diagnosis ──────────────────────────────────────────

    def record_diagnosis(
        self,
        candidate_id: str,
        *,
        status: Literal["technical_failure_recoverable", "needs_user_assistance", "recovered"],
        failure_category: FailureCategory,
        attempts: int,
        methods_tried_zh: tuple[str, ...],
        next_step_zh: str,
        recorded_at: datetime,
        recorded_by: str,
    ) -> MonitoringChangeCandidate:
        """对既有候选追加一次技术诊断；只有达到恢复合同才能要求用户协助。

        ``recovered`` 是恢复记录：此前必须存在未解决的技术失败记录，追加后
        候选诊断状态回到健康，历史失败记录不删除。
        """

        candidate = self._require_candidate(candidate_id)
        occurred_at = _offset_datetime(recorded_at)
        if status == "needs_user_assistance":
            if attempts < self.recovery_attempt_limit:
                raise MonitoringAssistanceError(
                    f"恢复尝试尚未达到上限（{attempts}/{self.recovery_attempt_limit} 轮），"
                    "不得把该候选标为需要用户协助"
                )
            if not methods_tried_zh:
                raise MonitoringAssistanceError("要求用户协助前必须记录已尝试的恢复方法")
        elif status == "technical_failure_recoverable":
            if attempts >= self.recovery_attempt_limit:
                raise MonitoringAssistanceError(
                    f"恢复尝试已达到上限（{self.recovery_attempt_limit} 轮），"
                    "诊断必须上报为需要用户协助，不能继续标为可自动恢复"
                )
        else:
            if not any(
                item.status in ("technical_failure_recoverable", "needs_user_assistance")
                for item in candidate.diagnostics
            ):
                raise MonitoringStateError("候选没有未解决的技术失败记录，不能登记恢复")
        category_zh = failure_category_zh(failure_category)
        if status == "technical_failure_recoverable":
            guidance = (
                f"来源获取遇到{category_zh}，正在按恢复策略自动重试（已尝试 {attempts} 轮），"
                "暂时不需要您处理。"
            )
        elif status == "needs_user_assistance":
            guidance = (
                f"已按恢复策略完成 {attempts} 轮重试仍无法获取该来源（{category_zh}）；"
                f"请您{next_step_zh}，完成后监测将继续。"
            )
        else:
            guidance = f"此前阻断该来源的技术问题（{category_zh}）已解决，监测恢复正常。"
        methods = tuple(_require_prose_zh_or_fail(item, "已尝试方法") for item in methods_tried_zh)
        normalized_step = _require_prose_zh_or_fail(next_step_zh, "下一步")
        diagnostic_id = stable_id(
            "monitoring-diagnostic",
            candidate_id,
            _payload_digest(
                {
                    "status": status,
                    "failure_category": failure_category,
                    "attempts": attempts,
                    "methods_tried_zh": list(methods),
                    "next_step_zh": normalized_step,
                    "user_guidance_zh": guidance,
                }
            ),
        )
        diagnostic = MonitoringDiagnosticRecord(
            diagnostic_id=diagnostic_id,
            status=status,
            failure_category=failure_category,
            attempts=attempts,
            methods_tried_zh=methods,
            next_step_zh=normalized_step,
            user_guidance_zh=guidance,
            recorded_at=occurred_at,
        )
        known_ids = {item.diagnostic_id for item in candidate.diagnostics}
        if diagnostic.diagnostic_id not in known_ids:
            self._append_event(
                event_type=MONITORING_CANDIDATE_DIAGNOSTIC_EVENT,
                event_kind="monitoring-diagnostic",
                project_id=candidate.project_id,
                actor_id=recorded_by,
                occurred_at=occurred_at,
                payload={
                    "candidate_id": candidate_id,
                    "diagnostic": diagnostic.model_dump(mode="json"),
                },
                idempotency_key=(
                    f"monitoring.candidate.diagnostic_updated:{diagnostic.diagnostic_id}"
                ),
                identity=diagnostic.diagnostic_id,
            )
        return self.load(candidate_id)

    # ── 操作 3：apply_disposition ─────────────────────────────────────────

    def apply_disposition(
        self,
        candidate_id: str,
        *,
        disposition: Literal["start_normal_refresh", "deferred"],
        decided_by: str,
        decided_at: datetime,
        reason_zh: str,
    ) -> MonitoringChangeCandidate:
        """记录用户处置；"启动正常刷新"在同一操作内生成只读刷新交接单。

        §17.3 schema 要求启动正常刷新的投影必须携带交接单，因此处置事件与
        交接事件连续落账后才写投影；中断后重放同一操作幂等补齐。处置是追加
        事件，不删除候选、不改写历史。
        """

        candidate = self._require_candidate(candidate_id)
        occurred_at = _offset_datetime(decided_at)
        record = MonitoringUserDispositionRecord(
            disposition=disposition,
            decided_by=decided_by,
            decided_at=occurred_at,
            reason_zh=_require_prose_zh_or_fail(reason_zh, "处置理由"),
        )
        disposition_id = stable_id(
            "monitoring-disposition",
            candidate_id,
            record.model_dump_json(),
        )
        known_ids = {
            stable_id("monitoring-disposition", candidate_id, item.model_dump_json())
            for item in candidate.disposition_records
        }
        if candidate.refresh_handoff is not None and disposition_id not in known_ids:
            raise MonitoringStateError(
                "该候选已交给正常刷新，不能再改变处置；如需停止，请在刷新任务中处理。"
            )
        if disposition_id not in known_ids:
            self._append_event(
                event_type=MONITORING_CANDIDATE_DISPOSITION_EVENT,
                event_kind="monitoring-disposition",
                project_id=candidate.project_id,
                actor_id=decided_by,
                occurred_at=occurred_at,
                payload={
                    "candidate_id": candidate_id,
                    "disposition": record.model_dump(mode="json"),
                },
                idempotency_key=f"monitoring.candidate.disposition_recorded:{disposition_id}",
                identity=disposition_id,
            )
        if disposition == "start_normal_refresh":
            self.create_refresh_handoff(candidate_id, occurred_at=occurred_at, actor_id=decided_by)
        return self.load(candidate_id)

    # ── 操作 4：create_refresh_handoff ────────────────────────────────────

    def create_refresh_handoff(
        self,
        candidate_id: str,
        *,
        occurred_at: datetime,
        actor_id: str,
    ) -> MonitoringRefreshHandoff:
        """生成只读刷新交接单；用户已选择"启动正常刷新"是唯一入口。

        交接单绑定候选 ID/摘要、项目 ID、当前项目合同版本、来源身份与建议
        复核范围；不调用刷新接受、不创建锁定快照、不写报告目录、不改事实或
        声明。同一绑定内容幂等重放返回同一交接单。
        """

        candidate = self._require_candidate(candidate_id, heal_projection=False)
        if candidate.user_disposition != "start_normal_refresh":
            raise MonitoringStateError("只有用户明确选择启动正常刷新后，才能生成刷新交接单")
        active_version, active_project_id = self._active_contract_identity()
        if active_project_id != candidate.project_id:
            raise MonitoringStateError("候选所属项目与当前项目文件不一致，必须失败关闭")
        occurred_at = _offset_datetime(occurred_at)
        handoff = build_refresh_handoff(
            candidate=candidate,
            project_contract_version=active_version,
            suggested_review_scope_zh=self._suggested_review_scope_zh(candidate),
            created_at=occurred_at,
        )
        verify_refresh_handoff_addressing(handoff)
        existing = candidate.refresh_handoff
        if existing is not None:
            if existing.handoff_id != handoff.handoff_id:
                raise MonitoringConflictError("同一候选已绑定另一份刷新交接单，必须失败关闭")
            self._atomic_json_write(
                self._handoff_dir() / f"{existing.handoff_id}.json",
                existing.model_dump(mode="json"),
            )
            self.load(candidate_id)
            return existing
        self._append_event(
            event_type=MONITORING_REFRESH_HANDOFF_EVENT,
            event_kind="monitoring-handoff",
            project_id=candidate.project_id,
            actor_id=actor_id,
            occurred_at=occurred_at,
            payload={
                "candidate_id": candidate.candidate_id,
                "handoff": handoff.model_dump(mode="json"),
            },
            idempotency_key=f"monitoring.refresh_handoff.created:{handoff.handoff_id}",
            identity=handoff.handoff_id,
        )
        self._atomic_json_write(
            self._handoff_dir() / f"{handoff.handoff_id}.json",
            handoff.model_dump(mode="json"),
        )
        self.load(candidate_id)
        return handoff

    @staticmethod
    def _suggested_review_scope_zh(candidate: MonitoringChangeCandidate) -> str:
        """由候选的可能影响集合组合建议复核范围的中文说明（只是建议）。"""

        reports = "、".join(candidate.possibly_affected_reports)
        if candidate.possibly_affected_page_ids:
            return (
                f"建议复核 {reports} 报告中的相关页面；刷新时仍需按现行证据门槛重新核验。"
            )
        return f"建议复核 {reports} 报告；刷新时仍需按现行证据门槛重新核验。"

    def _active_contract_identity(self) -> tuple[int, str]:
        """只读读取项目文件当前合同版本与项目身份；不执行任何迁移或写入。"""

        path = self.project_root / "project.yaml"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise MonitoringStateError(
                "项目文件缺失或不是有效 JSON，无法确定当前合同版本"
            ) from error
        if not isinstance(document, dict) or "active_contract_version" not in document:
            raise MonitoringStateError("项目文件缺少当前合同版本，无法生成交接单")
        active = document["active_contract_version"]
        versions = document.get("project_contract_versions")
        if not isinstance(versions, list):
            raise MonitoringStateError("项目文件没有可读取的合同版本")
        for payload in versions:
            if not isinstance(payload, dict) or payload.get("contract_version") != active:
                continue
            project_id = payload.get("project_id")
            if not isinstance(project_id, str) or not project_id.strip():
                raise MonitoringStateError("当前合同版本缺少项目身份")
            return int(active), project_id
        raise MonitoringStateError("项目指定的当前合同版本不存在")

    # ── 读取与投影恢复 ────────────────────────────────────────────────────

    def load(self, candidate_id: str) -> MonitoringChangeCandidate:
        """读取候选：先按事件归约规范投影，文件缺失或漂移时自愈重建。"""

        candidate = self._reduce_candidate(candidate_id)
        if candidate is None:
            raise MonitoringNotFoundError(f"变更候选不存在于规范事件流：{candidate_id}")
        path = self._inbox_dir() / f"{candidate_id}.json"
        stored: MonitoringChangeCandidate | None = None
        if path.is_file():
            try:
                stored = MonitoringChangeCandidate.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, ValueError):
                stored = None
        if stored != candidate:
            self._atomic_json_write(path, candidate.model_dump(mode="json"))
        return candidate

    def load_handoff(self, handoff_id: str) -> MonitoringRefreshHandoff:
        """读取刷新交接单：事件是真源，文件缺失或漂移时自愈重建。"""

        for event in self.event_store.read_all():
            if event.event_type != MONITORING_REFRESH_HANDOFF_EVENT:
                continue
            handoff = MonitoringRefreshHandoff.model_validate(event.payload["handoff"])
            if handoff.handoff_id != handoff_id:
                continue
            if event.payload.get("candidate_id") != handoff.candidate_id:
                raise MonitoringConflictError("交接单事件与载荷候选不一致，必须失败关闭")
            path = self._handoff_dir() / f"{handoff_id}.json"
            stored: MonitoringRefreshHandoff | None = None
            if path.is_file():
                try:
                    stored = MonitoringRefreshHandoff.model_validate(
                        json.loads(path.read_text(encoding="utf-8"))
                    )
                except (OSError, json.JSONDecodeError, ValueError):
                    stored = None
            if stored != handoff:
                self._atomic_json_write(path, handoff.model_dump(mode="json"))
            return handoff
        raise MonitoringNotFoundError(f"刷新交接单不存在：{handoff_id}")

    def list_candidates(
        self, *, source_stable_id: str | None = None
    ) -> tuple[MonitoringChangeCandidate, ...]:
        """按事件归约全部候选（可按来源过滤），并自愈各自的投影文件。"""

        ids: list[str] = []
        for event in self.event_store.read_all():
            if event.event_type == MONITORING_CANDIDATE_DISCOVERED_EVENT:
                candidate_id = str(event.payload["candidate"]["candidate_id"])
                if candidate_id not in ids:
                    ids.append(candidate_id)
        candidates = [self.load(candidate_id) for candidate_id in sorted(ids)]
        if source_stable_id is None:
            return tuple(candidates)
        return tuple(
            item for item in candidates if item.source_identity.source_stable_id == source_stable_id
        )

    def observation_receipts(self) -> tuple[MonitoringObservationReceipt, ...]:
        """从事件流归约全部观察回执，并自愈缺失的 JSONL 回执行。"""

        receipts: dict[str, MonitoringObservationReceipt] = {}
        for event in self.event_store.read_all():
            if event.event_type != _OBSERVATION_EVENT:
                continue
            receipt = MonitoringObservationReceipt.model_validate(event.payload["receipt"])
            existing = receipts.get(receipt.receipt_id)
            if existing is not None and existing != receipt:
                raise MonitoringConflictError("同一观察回执标识对应了不同内容")
            receipts[receipt.receipt_id] = receipt
        ordered = tuple(
            sorted(receipts.values(), key=lambda item: (item.observed_at, item.receipt_id))
        )
        recorded_ids: set[str] = set()
        path = self._receipt_path()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    recorded_ids.add(str(json.loads(line).get("receipt_id")))
        for receipt in ordered:
            if receipt.receipt_id not in recorded_ids:
                self._append_receipt(receipt)
        return ordered

    def _append_receipt(self, receipt: MonitoringObservationReceipt) -> None:
        """追加观察回执 JSONL（投影）；事件流是真源，缺失行可由事件重放补齐。"""

        path = self._receipt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_ids: set[str] = set()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    existing_ids.add(str(json.loads(line).get("receipt_id")))
        if receipt.receipt_id in existing_ids:
            return
        encoded = _canonical_json_text(receipt.model_dump(mode="json")) + "\n"
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        try:
            os.write(descriptor, encoded.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _require_candidate(
        self, candidate_id: str, *, heal_projection: bool = True
    ) -> MonitoringChangeCandidate:
        candidate = self._reduce_candidate(candidate_id)
        if candidate is None:
            raise MonitoringNotFoundError(f"变更候选不存在于规范事件流：{candidate_id}")
        if heal_projection:
            self.load(candidate_id)
        return candidate

    # ── 事件归约 ──────────────────────────────────────────────────────────

    def _reduce_candidate(self, candidate_id: str) -> MonitoringChangeCandidate | None:
        """从规范事件流归约候选当前投影；事件是真源，文件只是快照。"""

        candidate: MonitoringChangeCandidate | None = None
        for event in self.event_store.read_all():
            if event.event_type == MONITORING_CANDIDATE_DISCOVERED_EVENT:
                discovered = MonitoringChangeCandidate.model_validate(event.payload["candidate"])
                if discovered.candidate_id != candidate_id:
                    continue
                if candidate is not None:
                    raise MonitoringConflictError("同一候选出现了两次首次发现事件")
                candidate = discovered
            elif event.event_type == MONITORING_CANDIDATE_REDISCOVERED_EVENT:
                if event.payload.get("candidate_id") != candidate_id:
                    continue
                if candidate is None:
                    raise MonitoringConflictError("重复发现事件早于首次发现事件")
                discovery = MonitoringDiscoveryRecord.model_validate(event.payload["discovery"])
                if discovery not in candidate.discoveries:
                    # 追加式历史：发现顺序与事件流一致，发现时间只保留在记录内。
                    candidate = candidate.model_copy(
                        update={"discoveries": (*candidate.discoveries, discovery)}
                    )
            elif event.event_type == MONITORING_CANDIDATE_DIAGNOSTIC_EVENT:
                if event.payload.get("candidate_id") != candidate_id:
                    continue
                if candidate is None:
                    raise MonitoringConflictError("诊断事件早于首次发现事件")
                diagnostic = MonitoringDiagnosticRecord.model_validate(event.payload["diagnostic"])
                if diagnostic.diagnostic_id in {
                    item.diagnostic_id for item in candidate.diagnostics
                }:
                    continue
                latest_status: DiagnosticStatus = (
                    "healthy" if diagnostic.status == "recovered" else diagnostic.status
                )
                candidate = candidate.model_copy(
                    update={
                        "diagnostics": (*candidate.diagnostics, diagnostic),
                        "diagnostic_status": latest_status,
                    }
                )
            elif event.event_type == MONITORING_CANDIDATE_DISPOSITION_EVENT:
                if event.payload.get("candidate_id") != candidate_id:
                    continue
                if candidate is None:
                    raise MonitoringConflictError("处置事件早于首次发现事件")
                record = MonitoringUserDispositionRecord.model_validate(
                    event.payload["disposition"]
                )
                state: UserDisposition = record.disposition
                candidate = candidate.model_copy(
                    update={
                        "disposition_records": (*candidate.disposition_records, record),
                        "user_disposition": state,
                    }
                )
            elif event.event_type == MONITORING_REFRESH_HANDOFF_EVENT:
                if event.payload.get("candidate_id") != candidate_id:
                    continue
                if candidate is None:
                    raise MonitoringConflictError("交接事件早于首次发现事件")
                handoff = MonitoringRefreshHandoff.model_validate(event.payload["handoff"])
                if candidate.user_disposition != "start_normal_refresh":
                    raise MonitoringConflictError("交接事件先于启动正常刷新的处置事件")
                if candidate.refresh_handoff is not None:
                    if candidate.refresh_handoff != handoff:
                        raise MonitoringConflictError("同一候选绑定了不同刷新交接单")
                else:
                    candidate = candidate.model_copy(update={"refresh_handoff": handoff})
        if candidate is not None:
            # 聚合边界从当前序列化内容重跑完整合同；不信任 model_copy
            # 绕过的摘要、处置、诊断或交接跨对象绑定。
            try:
                verify_candidate_dedupe_identity(candidate)
            except MonitoringContractError as error:
                raise MonitoringConflictError(
                    "监测事件归约后的候选不满足完整绑定合同"
                ) from error
        return candidate
