"""Task 9.3 可选监测的变更候选机器合同与稳定去重摘要。

边界（design.md / v1.2 §17.3）：监测是可选叶子能力，只产出去重、可追溯、
可恢复的变更候选；本模块只定义合同字段、状态词表、去重摘要与候选/交接单
标识推导，不接触事实表、声明表、快照或报告发布。核心项目服务与刷新服务
不得导入本模块，删除监测能力不影响项目生命周期。

- ``dedupe_digest`` 由项目、来源稳定身份/版本/可复现定位、实体、声明域、
  变化类型、当前值与候选值的规范 JSON 计算；原始链接不参与摘要，同一业务
  变化只有一个候选身份。候选 ID 由该摘要稳定派生，调用方不能自带标识。
- 构造边界重算摘要并比对缓存字段；``model_copy(update=...)`` 绕过校验，
  因此所有公开聚合边界必须调用 :func:`verify_candidate_dedupe_identity` /
  :func:`verify_refresh_handoff_addressing` 从当前序列化内容重推导，复用
  ``model_copy`` 的漂移候选在聚合前失败关闭。
- 交接单只绑定候选、项目、当前项目合同版本、来源身份与建议复核范围；
  它是一份刷新输入，不是刷新动作，不调用刷新接受、快照锁定或报告发布。
- 观察结果词表区分“发现变化 / 无变化 / 未公开 / 可自动恢复的技术失败 /
  需要用户协助”五类；机器状态只保存在合同字段中，用户可见文案由
  :func:`outcome_guidance_zh` 等转译为自然中文。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from ci_workflow.domain.ids import stable_id

# ── 冻结词表 ─────────────────────────────────────────────────────────────────

#: 监测能力合同版本（区别于项目合同版本；随 Task 9.3 合同冻结）。
MONITORING_CONTRACT_VERSION: Final = "1.0"

#: 来源观察的五种结果：发现变化 / 完成但无变化 / 来源确认未公开 /
#: 技术获取失败仍可自动恢复 / 多轮恢复后仍失败需要用户协助。
ObservationOutcome = Literal[
    "change_found",
    "no_change",
    "confirmed_not_public",
    "technical_failure_recoverable",
    "needs_user_assistance",
]

#: 变化类型：数值更新 / 新增披露 / 状态变化 / 数值勘误 / 信息撤回。
ChangeType = Literal[
    "value_updated",
    "newly_disclosed",
    "status_changed",
    "value_corrected",
    "value_withdrawn",
]

#: 候选值获取方式：公开直接获取 / 经用户协助获取（§18.3：用户辅助获取
#: 改变访问来源，不改变科学权威）。
AcquisitionStatus = Literal["acquired", "acquired_with_user_assistance"]

#: 候选当前技术诊断状态：无未决问题 / 技术失败自动恢复中 / 需要用户协助。
DiagnosticStatus = Literal[
    "healthy",
    "technical_failure_recoverable",
    "needs_user_assistance",
]

#: 用户处置：待处理 / 启动正常刷新 / 暂不处理。
UserDisposition = Literal["pending", "start_normal_refresh", "deferred"]

#: 技术失败类别（§19.2：网络、限流、验证码或登录、页面变更、解析失败、
#: 工具能力缺失，以及无法归类的未知）。
FailureCategory = Literal[
    "network",
    "rate_limit",
    "captcha_or_login",
    "page_structure_changed",
    "parse_failure",
    "tool_capability_missing",
    "unknown",
]

#: 稳定追加事件类型（历史真源 events/events.jsonl 的冻结词表）。
MONITORING_CANDIDATE_DISCOVERED_EVENT = "monitoring.candidate.discovered"
MONITORING_CANDIDATE_REDISCOVERED_EVENT = "monitoring.candidate.rediscovered"
MONITORING_CANDIDATE_DIAGNOSTIC_EVENT = "monitoring.candidate.diagnostic_updated"
MONITORING_CANDIDATE_DISPOSITION_EVENT = "monitoring.candidate.disposition_recorded"
MONITORING_REFRESH_HANDOFF_EVENT = "monitoring.refresh_handoff.created"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z][a-z0-9-]*_[0-9a-f]{24}$")
_CJK_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF))


class MonitoringContractError(RuntimeError):
    """监测变更候选合同失败；消息中文陈述事实。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("监测合同字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("监测合同时间必须包含明确时区偏移")
    return value


def _prose_zh(value: str) -> str:
    """用户可见说明必须是中文原生短句，而不是机器标签。"""

    normalized = _not_blank(value)
    if not any(
        any(low <= ord(char) <= high for low, high in _CJK_RANGES)
        for char in normalized
    ):
        raise ValueError("用户可见说明必须包含中文")
    return normalized


def _canonical_json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


# ── 机器合同 ─────────────────────────────────────────────────────────────────


class MonitoringSourceIdentity(BaseModel):
    """来源身份：稳定来源 ID、来源版本、可复现定位与原始链接。

    摘要只取稳定 ID、版本与定位；原始链接是呈现辅助，同一来源的不同链接
    形态不产生新候选。``source_version_id`` 必须表示不可变的来源内容版本，
    不能使用每次抓取时间、运行编号或临时快照标签；相同内容被再次获取时应
    复用同一版本标识。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_stable_id: str
    source_version_id: str
    locator: str
    source_url: str

    @field_validator("source_stable_id", "source_version_id", "locator", "source_url")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("source_stable_id")
    @classmethod
    def _source_is_stable_id(cls, value: str) -> str:
        if _STABLE_ID.fullmatch(value) is None:
            raise ValueError("来源必须使用项目稳定标识")
        return value


class MonitoringDiscoveryRecord(BaseModel):
    """一次发现记录：候选内的 discoveries 只登记实际看到该变化的观察，
    无变化、未公开与技术失败结果由事件流承载，不写入候选发现列表。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observed_at: datetime
    observer: str
    outcome: Literal["change_found"]
    note_zh: str

    @field_validator("observer", "note_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("note_zh")
    @classmethod
    def _note_is_chinese_prose(cls, value: str) -> str:
        return _prose_zh(value)

    @field_validator("observed_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class MonitoringDiagnosticRecord(BaseModel):
    """一条追加式技术诊断：失败类别、尝试轮次、已尝试方法与下一步。

    标为“需要用户协助”时必须提供至少一个已尝试方法；恢复轮次阈值由
    服务层按恢复策略配置判定，合同不固化数字。``recovered`` 是恢复记录：
    技术问题解决后追加，使候选诊断状态回到健康；历史失败记录不删除。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    diagnostic_id: str
    status: Literal[
        "technical_failure_recoverable", "needs_user_assistance", "recovered"
    ]
    failure_category: FailureCategory
    attempts: int
    methods_tried_zh: tuple[str, ...]
    next_step_zh: str
    user_guidance_zh: str
    recorded_at: datetime

    @field_validator("diagnostic_id", "next_step_zh", "user_guidance_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("next_step_zh", "user_guidance_zh")
    @classmethod
    def _visible_text_is_chinese_prose(cls, value: str) -> str:
        return _prose_zh(value)

    @field_validator("methods_tried_zh")
    @classmethod
    def _methods_are_chinese_prose(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_prose_zh(item) for item in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError("已尝试的恢复方法不得重复")
        return normalized

    @field_validator("attempts")
    @classmethod
    def _attempts_are_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("恢复尝试轮次至少为 1")
        return value

    @field_validator("recorded_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _assistance_requires_methods(self) -> Self:
        if self.status == "needs_user_assistance" and not self.methods_tried_zh:
            raise ValueError("需要用户协助的诊断必须提供已尝试的恢复方法")
        return self


class MonitoringUserDispositionRecord(BaseModel):
    """一次用户处置决定：启动正常刷新或暂不处理；只追加不覆盖。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition: Literal["start_normal_refresh", "deferred"]
    decided_by: str
    decided_at: datetime
    reason_zh: str

    @field_validator("decided_by", "reason_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("reason_zh")
    @classmethod
    def _reason_is_chinese_prose(cls, value: str) -> str:
        return _prose_zh(value)

    @field_validator("decided_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


def _handoff_binding_digest(
    *,
    candidate_id: str,
    dedupe_digest: str,
    project_id: str,
    project_contract_version: int,
    source_stable_id: str,
    source_version_id: str,
    locator: str,
    source_url: str,
    suggested_review_scope_zh: str,
) -> str:
    payload = {
        "candidate_id": candidate_id,
        "dedupe_digest": dedupe_digest,
        "project_id": project_id,
        "project_contract_version": project_contract_version,
        "source_identity": {
            "source_stable_id": source_stable_id,
            "source_version_id": source_version_id,
            "locator": locator,
            "source_url": source_url,
        },
        "suggested_review_scope_zh": suggested_review_scope_zh,
    }
    return hashlib.sha256(_canonical_json_text(payload).encode("utf-8")).hexdigest()


class MonitoringRefreshHandoff(BaseModel):
    """只读刷新交接单：绑定候选、项目与当前项目合同版本。

    ``handoff_id`` 由绑定内容（候选 ID、去重摘要、项目、项目合同版本、
    来源身份、建议复核范围）内容寻址派生；``created_at`` 记录首次生成
    时间但不参与寻址，同一决定的幂等重放得到同一交接单。交接单只是
    Task 9.2 正常刷新的输入，不触发刷新接受、快照或发布。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    handoff_id: str
    candidate_id: str
    dedupe_digest: str
    project_id: str
    project_contract_version: int
    source_identity: MonitoringSourceIdentity
    suggested_review_scope_zh: str
    created_at: datetime

    @field_validator("handoff_id", "candidate_id", "project_id", "suggested_review_scope_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("suggested_review_scope_zh")
    @classmethod
    def _scope_is_chinese_prose(cls, value: str) -> str:
        return _prose_zh(value)

    @field_validator("handoff_id", "candidate_id")
    @classmethod
    def _ids_follow_stable_convention(cls, value: str) -> str:
        if _STABLE_ID.fullmatch(value) is None:
            raise ValueError("交接单标识必须使用项目稳定标识")
        return value

    @field_validator("dedupe_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if not _is_sha256(value):
            raise ValueError("去重摘要必须是小写 SHA-256")
        return value

    @field_validator("project_contract_version")
    @classmethod
    def _contract_version_is_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("项目合同版本至少为 1")
        return value

    @field_validator("created_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _addressing_is_consistent(self) -> Self:
        expected = _handoff_binding_digest(
            candidate_id=self.candidate_id,
            dedupe_digest=self.dedupe_digest,
            project_id=self.project_id,
            project_contract_version=self.project_contract_version,
            source_stable_id=self.source_identity.source_stable_id,
            source_version_id=self.source_identity.source_version_id,
            locator=self.source_identity.locator,
            source_url=self.source_identity.source_url,
            suggested_review_scope_zh=self.suggested_review_scope_zh,
        )
        if stable_id("monitoring-refresh", expected) != self.handoff_id:
            raise ValueError("交接单标识与绑定内容不一致")
        return self


class MonitoringChangeCandidate(BaseModel):
    """监测变更候选机器合同（§17.3 最低字段集）。

    候选不能直接成为事实：本模型不携带任何写入事实、声明、快照或报告的
    能力；唯一出口是用户处置后生成的只读刷新交接单。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["1.0"] = MONITORING_CONTRACT_VERSION
    candidate_id: str
    project_id: str
    source_identity: MonitoringSourceIdentity
    discovered_at: datetime
    discoveries: tuple[MonitoringDiscoveryRecord, ...]
    entity_id: str
    claim_domain: str
    change_type: ChangeType
    current_value: str
    candidate_value: str
    dedupe_digest: str
    possibly_affected_reports: tuple[str, ...]
    possibly_affected_page_ids: tuple[str, ...]
    acquisition_status: AcquisitionStatus
    diagnostic_status: DiagnosticStatus
    diagnostics: tuple[MonitoringDiagnosticRecord, ...] = ()
    user_disposition: UserDisposition = "pending"
    disposition_records: tuple[MonitoringUserDispositionRecord, ...] = ()
    refresh_handoff: MonitoringRefreshHandoff | None = None

    @field_validator("candidate_id", "project_id", "entity_id", "claim_domain")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("candidate_id", "entity_id")
    @classmethod
    def _ids_follow_stable_convention(cls, value: str) -> str:
        if _STABLE_ID.fullmatch(value) is None:
            raise ValueError("候选与实体必须使用项目稳定标识")
        return value

    @field_validator("dedupe_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if not _is_sha256(value):
            raise ValueError("去重摘要必须是小写 SHA-256")
        return value

    @field_validator("discovered_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("possibly_affected_reports")
    @classmethod
    def _reports_are_declared(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {"A", "B", "C"}
        if not value or set(value) - allowed:
            raise ValueError("可能影响的报告只能是 A、B、C 的非空子集")
        return value

    @field_validator("discoveries")
    @classmethod
    def _discoveries_present(
        cls, value: tuple[MonitoringDiscoveryRecord, ...]
    ) -> tuple[MonitoringDiscoveryRecord, ...]:
        if not value:
            raise ValueError("候选至少保留一条发现记录")
        return value

    @model_validator(mode="after")
    def _dedupe_identity_is_consistent(self) -> Self:
        recomputed = monitoring_dedupe_digest(
            project_id=self.project_id,
            source_identity=self.source_identity,
            entity_id=self.entity_id,
            claim_domain=self.claim_domain,
            change_type=self.change_type,
            current_value=self.current_value,
            candidate_value=self.candidate_value,
        )
        if recomputed != self.dedupe_digest:
            raise ValueError("去重摘要与候选当前内容不一致")
        if candidate_id_from_digest(recomputed) != self.candidate_id:
            raise ValueError("候选标识与去重摘要不一致")
        return self

    @model_validator(mode="after")
    def _state_bindings_are_consistent(self) -> Self:
        if self.user_disposition == "pending":
            if self.refresh_handoff is not None:
                raise ValueError("待处理候选不能携带刷新交接单")
        elif not [
            record
            for record in self.disposition_records
            if record.disposition == self.user_disposition
        ]:
            raise ValueError("当前处置必须有对应的用户决定记录")
        if self.refresh_handoff is not None:
            handoff = self.refresh_handoff
            if self.user_disposition != "start_normal_refresh":
                raise ValueError("刷新交接单只能来自启动正常刷新的决定")
            if handoff.candidate_id != self.candidate_id:
                raise ValueError("交接单绑定的候选与当前候选不一致")
            if handoff.dedupe_digest != self.dedupe_digest:
                raise ValueError("交接单绑定的去重摘要与当前候选不一致")
            if handoff.project_id != self.project_id:
                raise ValueError("交接单绑定的项目与当前候选不一致")
        if self.diagnostics:
            latest = self.diagnostics[-1].status
            expected = "healthy" if latest == "recovered" else latest
            if self.diagnostic_status != expected:
                raise ValueError("诊断状态必须与最新诊断记录一致")
        elif self.diagnostic_status != "healthy":
            raise ValueError("技术失败状态必须由诊断记录支撑")
        return self


# ── 稳定去重摘要与标识推导 ───────────────────────────────────────────────────


def monitoring_dedupe_digest(
    *,
    project_id: str,
    source_identity: MonitoringSourceIdentity,
    entity_id: str,
    claim_domain: str,
    change_type: str,
    current_value: str,
    candidate_value: str,
) -> str:
    """从合同字段计算稳定去重摘要：规范 JSON 的 SHA-256。

    参与字段：项目、来源稳定 ID、来源版本、可复现定位、实体、声明域、
    变化类型、当前值、候选值。原始链接、发现时间与追加历史不参与摘要，
    同一业务变化重复发现保持同一身份。
    """

    payload = {
        "project_id": _not_blank(project_id),
        "source_stable_id": source_identity.source_stable_id,
        "source_version_id": source_identity.source_version_id,
        "locator": source_identity.locator,
        "entity_id": _not_blank(entity_id),
        "claim_domain": _not_blank(claim_domain),
        "change_type": _not_blank(change_type),
        "current_value": _not_blank(current_value),
        "candidate_value": _not_blank(candidate_value),
    }
    return hashlib.sha256(_canonical_json_text(payload).encode("utf-8")).hexdigest()


def candidate_id_from_digest(dedupe_digest: str) -> str:
    """候选 ID 由去重摘要稳定派生；调用方不能自带候选标识。"""

    if not _is_sha256(dedupe_digest):
        raise MonitoringContractError("去重摘要必须是小写 SHA-256 才能派生候选标识")
    return stable_id("monitoring-candidate", dedupe_digest)


def verify_candidate_dedupe_identity(candidate: MonitoringChangeCandidate) -> None:
    """聚合边界重推导全部候选语义，再核对摘要与候选 ID。

    ``model_copy(update=...)`` 绕过构造校验；任何把候选交给持久化、合并、
    交接或呈现的边界都必须先调用本函数。这里从当前序列化内容重新构造，
    因而处置—交接、诊断状态、中文说明和交接跨对象绑定也会重新校验。
    """

    recomputed = monitoring_dedupe_digest(
        project_id=candidate.project_id,
        source_identity=candidate.source_identity,
        entity_id=candidate.entity_id,
        claim_domain=candidate.claim_domain,
        change_type=candidate.change_type,
        current_value=candidate.current_value,
        candidate_value=candidate.candidate_value,
    )
    if recomputed != candidate.dedupe_digest:
        raise MonitoringContractError(
            f"候选去重摘要与当前内容不一致：{candidate.candidate_id}"
        )
    if candidate_id_from_digest(recomputed) != candidate.candidate_id:
        raise MonitoringContractError(f"候选标识与去重摘要不一致：{candidate.candidate_id}")
    try:
        MonitoringChangeCandidate.model_validate(candidate.model_dump(mode="python"))
    except ValidationError as error:
        raise MonitoringContractError(
            f"候选当前投影不满足完整合同：{candidate.candidate_id}"
        ) from error


def verify_refresh_handoff_addressing(handoff: MonitoringRefreshHandoff) -> None:
    """聚合边界重推导交接单的内容寻址标识，漂移交接单失败关闭。"""

    expected = _handoff_binding_digest(
        candidate_id=handoff.candidate_id,
        dedupe_digest=handoff.dedupe_digest,
        project_id=handoff.project_id,
        project_contract_version=handoff.project_contract_version,
        source_stable_id=handoff.source_identity.source_stable_id,
        source_version_id=handoff.source_identity.source_version_id,
        locator=handoff.source_identity.locator,
        source_url=handoff.source_identity.source_url,
        suggested_review_scope_zh=handoff.suggested_review_scope_zh,
    )
    if stable_id("monitoring-refresh", expected) != handoff.handoff_id:
        raise MonitoringContractError(
            f"交接单标识与绑定内容不一致：{handoff.handoff_id}"
        )


def build_refresh_handoff(
    *,
    candidate: MonitoringChangeCandidate,
    project_contract_version: int,
    suggested_review_scope_zh: str,
    created_at: datetime,
) -> MonitoringRefreshHandoff:
    """由候选内容寻址生成只读刷新交接单；同一绑定内容幂等。"""

    digest = _handoff_binding_digest(
        candidate_id=candidate.candidate_id,
        dedupe_digest=candidate.dedupe_digest,
        project_id=candidate.project_id,
        project_contract_version=project_contract_version,
        source_stable_id=candidate.source_identity.source_stable_id,
        source_version_id=candidate.source_identity.source_version_id,
        locator=candidate.source_identity.locator,
        source_url=candidate.source_identity.source_url,
        suggested_review_scope_zh=suggested_review_scope_zh,
    )
    return MonitoringRefreshHandoff(
        handoff_id=stable_id("monitoring-refresh", digest),
        candidate_id=candidate.candidate_id,
        dedupe_digest=candidate.dedupe_digest,
        project_id=candidate.project_id,
        project_contract_version=project_contract_version,
        source_identity=candidate.source_identity,
        suggested_review_scope_zh=suggested_review_scope_zh,
        created_at=created_at,
    )


def build_change_candidate(
    *,
    project_id: str,
    source_identity: MonitoringSourceIdentity,
    discovered_at: datetime,
    observer: str,
    discovery_note_zh: str,
    entity_id: str,
    claim_domain: str,
    change_type: ChangeType,
    current_value: str,
    candidate_value: str,
    possibly_affected_reports: tuple[str, ...],
    possibly_affected_page_ids: tuple[str, ...],
    acquisition_status: AcquisitionStatus = "acquired",
) -> MonitoringChangeCandidate:
    """规范构造入口：先验证来源身份，再派生摘要与候选 ID。

    调用方不能提供候选 ID 或去重摘要；身份由当前合同字段推导。
    """

    digest = monitoring_dedupe_digest(
        project_id=project_id,
        source_identity=source_identity,
        entity_id=entity_id,
        claim_domain=claim_domain,
        change_type=change_type,
        current_value=current_value,
        candidate_value=candidate_value,
    )
    return MonitoringChangeCandidate(
        candidate_id=candidate_id_from_digest(digest),
        project_id=project_id,
        source_identity=source_identity,
        discovered_at=discovered_at,
        discoveries=(
            MonitoringDiscoveryRecord(
                observed_at=discovered_at,
                observer=observer,
                outcome="change_found",
                note_zh=discovery_note_zh,
            ),
        ),
        entity_id=entity_id,
        claim_domain=claim_domain,
        change_type=change_type,
        current_value=current_value,
        candidate_value=candidate_value,
        dedupe_digest=digest,
        possibly_affected_reports=possibly_affected_reports,
        possibly_affected_page_ids=possibly_affected_page_ids,
        acquisition_status=acquisition_status,
        diagnostic_status="healthy",
    )


# ── 中文转译 ─────────────────────────────────────────────────────────────────

_OUTCOME_GUIDANCE_ZH: dict[str, str] = {
    "change_found": (
        "已完成检索并发现可能的变化；变化已登记为候选，等待您决定是否启动正常刷新。"
    ),
    "no_change": "已完成检索，该来源范围内的公开信息没有变化，无需处理。",
    "confirmed_not_public": (
        "来源已确认尚未公开目标信息；这不是获取故障，无需处理，后续监测会继续跟进。"
    ),
    "technical_failure_recoverable": (
        "来源获取遇到技术问题，正在按恢复策略自动重试；暂时不需要您处理。"
    ),
    "needs_user_assistance": (
        "已按恢复策略完成多轮重试仍无法获取该来源；"
        "需要您在浏览器中协助完成访问，再继续监测。"
    ),
}

_CHANGE_TYPE_ZH: dict[str, str] = {
    "value_updated": "数值更新",
    "newly_disclosed": "新增披露",
    "status_changed": "状态变化",
    "value_corrected": "数值勘误",
    "value_withdrawn": "信息撤回",
}

_DISPOSITION_ZH: dict[str, str] = {
    "pending": "待处理",
    "start_normal_refresh": "已启动正常刷新",
    "deferred": "暂不处理",
}

_ACQUISITION_ZH: dict[str, str] = {
    "acquired": "已从公开渠道直接获取",
    "acquired_with_user_assistance": "经用户协助访问后获取",
}

_DIAGNOSTIC_ZH: dict[str, str] = {
    "healthy": "获取正常",
    "technical_failure_recoverable": "获取遇到技术问题，自动恢复中",
    "needs_user_assistance": "多轮恢复后仍失败，需要用户协助",
}

_FAILURE_CATEGORY_ZH: dict[str, str] = {
    "network": "网络访问失败",
    "rate_limit": "来源限流",
    "captcha_or_login": "需要验证码或登录",
    "page_structure_changed": "页面结构变化",
    "parse_failure": "内容解析失败",
    "tool_capability_missing": "工具能力缺失",
    "unknown": "未能归类的获取失败",
}


def outcome_guidance_zh(outcome: str) -> str:
    """把观察结果转译为面向用户的中文提示；未知结果失败关闭。"""

    text = _OUTCOME_GUIDANCE_ZH.get(outcome)
    if text is None:
        raise MonitoringContractError(f"未声明的观察结果：{outcome}")
    return text


def change_type_zh(change_type: str) -> str:
    text = _CHANGE_TYPE_ZH.get(change_type)
    if text is None:
        raise MonitoringContractError(f"未声明的变化类型：{change_type}")
    return text


def disposition_zh(disposition: str) -> str:
    text = _DISPOSITION_ZH.get(disposition)
    if text is None:
        raise MonitoringContractError(f"未声明的用户处置：{disposition}")
    return text


def acquisition_status_zh(status: str) -> str:
    text = _ACQUISITION_ZH.get(status)
    if text is None:
        raise MonitoringContractError(f"未声明的获取状态：{status}")
    return text


def diagnostic_status_zh(status: str) -> str:
    text = _DIAGNOSTIC_ZH.get(status)
    if text is None:
        raise MonitoringContractError(f"未声明的诊断状态：{status}")
    return text


def failure_category_zh(category: str) -> str:
    text = _FAILURE_CATEGORY_ZH.get(category)
    if text is None:
        raise MonitoringContractError(f"未声明的失败类别：{category}")
    return text
