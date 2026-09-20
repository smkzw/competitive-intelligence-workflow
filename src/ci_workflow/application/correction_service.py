"""Task 9.1 来源关联修订服务：追加式建议、验证处置、所有者决定与幂等发布。

边界（design.md）：本服务位于应用层，复用既有 SQLite 项目库、规范事件流、
内容寻址快照与 ``revision_approval`` 迁移族声明（``graph/transitions.py`` +
``graph/guards.py``），不另造状态机，也不直接修改事实表、声明表或报告文件；
发布只登记新的不可变版本及其前后关系。

- 全部状态迁移经 :class:`~ci_workflow.graph.executor.GraphExecutor` 走规范
  ``graph.transition.accepted/rejected`` 事件，归约/重放时按声明边与结构化
  守卫重求值，伪造或漂移的迁移失败关闭。
- ``correction_proposals`` 表只保存当前投影；完整操作历史保存在追加事件里。
  投影与规范状态不一致时以事件流为准自愈（崩溃恢复路径）。
- 每个操作以确定性幂等键写入 ``idempotency_keys``（追加式账本）：精确重放
  返回既有结果，同一键不同载荷失败关闭，重复提交/批准/发布不重复创建版本。
- 发布核验：显式批准 ID、新快照（内容寻址锁定且实质内容变化）、受影响内容
  重建、独立质控缺一失败关闭；失败保留批准状态并追加失败原因事件，不回写
  旧快照；发布中断后同一批准可恢复，不重复登记版本。
- 面向用户的表述只有自然中文；机器状态只保存在合同字段中。
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.domain.enums import RevisionApprovalState
from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.definitions.correction import binding_for_transition
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.storage.event_store import EventConflictError, EventStore, WorkflowEvent
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import (
    LockedSnapshot,
    ReportSnapshotManifest,
    SnapshotIntegrityError,
    SnapshotStore,
    compute_locked_snapshot,
)
from ci_workflow.storage.sqlite import open_database

_RUN_ID = "corrections"
_REPORT = Literal["A", "B", "C"]
_TARGET_TYPE = Literal["fact", "chart_point", "matrix_cell", "claim"]
_OUTCOME = Literal["needs_evidence", "rejected", "passed"]
_DECISION = Literal["approve", "reject", "needs_evidence"]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z][a-z0-9-]*_[0-9a-f]{24}$")
_VERSION = re.compile(r"^v(?P<number>[0-9]+)$")


class CorrectionServiceError(RuntimeError):
    """修订建议服务合同失败；消息中文陈述事实。"""


class CorrectionNotFoundError(CorrectionServiceError):
    """修订建议不存在。"""


class CorrectionBindingError(CorrectionServiceError):
    """修订建议与项目或当前快照的绑定核验失败。"""


class CorrectionStateError(CorrectionServiceError):
    """当前修订状态不允许该操作。"""


class CorrectionOwnerError(CorrectionServiceError):
    """修订决定不是来自报告所有者本人。"""


class CorrectionConflictError(CorrectionServiceError):
    """同一幂等键被另一份业务载荷复用。"""


class CorrectionPublishError(CorrectionServiceError):
    """发布前置条件不满足；批准状态与失败原因保留，等待恢复。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("修订建议字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("修订建议时间必须包含明确时区偏移")
    return value


def _canonical_json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_digest(value: object) -> str:
    return hashlib.sha256(_canonical_json_text(value).encode("utf-8")).hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _is_nonblank_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


# ── 机器合同 ─────────────────────────────────────────────────────────────────


class CorrectionAttachment(BaseModel):
    """建议附带的一条来源附件或链接。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    url: str

    @field_validator("label", "url")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CorrectionSourceRecord(BaseModel):
    """追加到同一建议的一条来源记录；原提交历史不覆盖。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str
    source_refs: tuple[CorrectionAttachment, ...] = ()
    note_zh: str
    recorded_by: str
    recorded_at: datetime

    @field_validator("evidence_id", "note_zh", "recorded_by")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("recorded_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class CorrectionValidationRecord(BaseModel):
    """一次验证处置：身份/上下文/定位/冲突/影响核验与处置理由。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    validation_id: str
    outcome: _OUTCOME
    disposition_reason_zh: str
    identity_verified: bool
    context_located: bool
    locator_verified: bool
    conflicts_checked: bool
    impact_checked: bool
    conflicts: tuple[str, ...] = ()
    impact_set: tuple[str, ...] = ()
    validated_by: str
    validated_at: datetime

    @field_validator("validation_id", "disposition_reason_zh", "validated_by")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("validated_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class CorrectionOwnerDecision(BaseModel):
    """报告所有者的显式决定；验证本身不能产生该记录。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: _DECISION
    approval_id: str | None = None
    decided_by: str
    decided_at: datetime
    reason_zh: str

    @field_validator("decided_by", "reason_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("decided_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _approval_id_present_only_for_approve(self) -> CorrectionOwnerDecision:
        if self.decision == "approve":
            if not _is_nonblank_str(self.approval_id):
                raise ValueError("批准决定必须携带批准标识")
        elif self.approval_id is not None:
            raise ValueError("只有批准决定才携带批准标识")
        return self


class CorrectionPublishedVersion(BaseModel):
    """发布登记产生的新版本及前后版本关系。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_version: str
    snapshot_id: str
    snapshot_sha256: str
    supersedes_snapshot_id: str
    published_at: datetime

    @field_validator("report_version", "snapshot_id", "supersedes_snapshot_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("snapshot_sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if not _is_sha256(value):
            raise ValueError("快照摘要必须是小写 SHA-256")
        return value

    @field_validator("published_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class CorrectionProposal(BaseModel):
    """修订建议机器合同（§17.1 最低字段集）；机器状态保存在合同字段中。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str
    project_id: str
    report: _REPORT
    report_version: str
    snapshot_id: str
    snapshot_sha256: str
    target_type: _TARGET_TYPE
    target_id: str
    current_visible_value: str
    proposed_value: str | None = None
    proposed_explanation: str | None = None
    rationale_zh: str
    submitted_at: datetime
    submitted_by: str
    report_owner_id: str
    attachments: tuple[CorrectionAttachment, ...] = ()
    source_records: tuple[CorrectionSourceRecord, ...] = ()
    validations: tuple[CorrectionValidationRecord, ...] = ()
    owner_decision: CorrectionOwnerDecision | None = None
    conflicts: tuple[str, ...] = ()
    impact_set: tuple[str, ...] = ()
    publish_idempotency_key: str | None = None
    published_version: CorrectionPublishedVersion | None = None
    state: str

    @field_validator(
        "proposal_id",
        "project_id",
        "report_version",
        "snapshot_id",
        "target_id",
        "current_visible_value",
        "rationale_zh",
        "submitted_by",
        "report_owner_id",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("snapshot_sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if not _is_sha256(value):
            raise ValueError("快照摘要必须是小写 SHA-256")
        return value

    @field_validator("target_id")
    @classmethod
    def _target_is_stable_id(cls, value: str) -> str:
        if _STABLE_ID.fullmatch(value) is None:
            raise ValueError("修订目标必须使用项目稳定标识")
        return value

    @field_validator("submitted_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("state")
    @classmethod
    def _state_is_declared(cls, value: str) -> str:
        declared = {member.value for member in RevisionApprovalState}
        if value not in declared:
            raise ValueError("修订状态不在已声明的六态之内")
        return value

    @model_validator(mode="after")
    def _proposal_changes_present(self) -> CorrectionProposal:
        has_value = _is_nonblank_str(self.proposed_value)
        has_explanation = _is_nonblank_str(self.proposed_explanation)
        if not (has_value or has_explanation):
            raise ValueError("建议值与建议解释至少要有一项")
        return self


def state_progress_zh(state: str) -> str:
    """把机器状态转译为自然中文进度；内部状态词不出现在结果里。"""

    mapping: dict[str, str] = {
        RevisionApprovalState.SUBMITTED.value: "已收到修订建议，正在核验来源与影响范围。",
        RevisionApprovalState.NEEDS_EVIDENCE.value: (
            "还需要补充证据：请提供与建议相关的来源材料后再提交。"
        ),
        RevisionApprovalState.REJECTED.value: (
            "该修订建议未通过核验，已保留完整记录，现行报告未改动。"
        ),
        RevisionApprovalState.VALIDATED_PENDING_USER_APPROVAL.value: (
            "核验已完成，等待报告负责人明确决定是否采纳。"
        ),
        RevisionApprovalState.APPROVED.value: (
            "报告负责人已批准，正在重建受影响内容并安排独立质控。"
        ),
        RevisionApprovalState.PUBLISHED.value: "修订已作为新版本发布，历史版本保持可追溯。",
    }
    return mapping.get(state, "修订建议正在处理中。")


# ── 服务 ─────────────────────────────────────────────────────────────────────


class CorrectionService:
    """追加式修订服务：submit / add_evidence / validate / 决定 / publish。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.event_store = EventStore(self.project_root)
        self.database_path = self.project_root / "state" / "project.sqlite"
        apply_migrations(self.database_path)
        self.snapshot_store = SnapshotStore(self.project_root)
        self.executor = GraphExecutor(self.project_root, run_id=_RUN_ID)

    # ── 读取与投影 ─────────────────────────────────────────────────────────

    def load(self, proposal_id: str) -> CorrectionProposal:
        """读取建议：以规范事件流重建真源，投影漂移或滞后时自愈。"""
        canonical = self._canonical_state(proposal_id)
        rebuilt = self._rebuild_from_events(proposal_id, canonical)
        if rebuilt is not None:
            stored = self._read_projection(proposal_id)
            if stored is None or stored != rebuilt:
                self._save(rebuilt)
            return rebuilt
        proposal = self._read_projection(proposal_id)
        if proposal is None:
            raise CorrectionNotFoundError(f"修订建议不存在：{proposal_id}")
        if proposal.state != canonical:
            repaired = proposal.model_copy(update={"state": canonical})
            self._save(repaired)
            return repaired
        return proposal

    def _read_projection(self, proposal_id: str) -> CorrectionProposal | None:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT proposal_json FROM correction_proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        if row is None:
            return None
        return CorrectionProposal.model_validate(json.loads(str(row[0])))

    def _rebuild_from_events(
        self, proposal_id: str, canonical_state: str
    ) -> CorrectionProposal | None:
        """从追加事件重建建议合同：事件是真源，投影只是当前快照。"""
        base: dict[str, Any] | None = None
        source_records: list[CorrectionSourceRecord] = []
        validations: list[CorrectionValidationRecord] = []
        owner_decision: CorrectionOwnerDecision | None = None
        publish_key: str | None = None
        published_version: CorrectionPublishedVersion | None = None
        conflicts: tuple[str, ...] = ()
        impact_set: tuple[str, ...] = ()
        for event in self.event_store.read_all():
            payload = event.payload
            if event.event_type == "correction.proposal.submitted":
                candidate = payload.get("proposal")
                if isinstance(candidate, dict) and candidate.get("proposal_id") == proposal_id:
                    base = candidate
            elif event.event_type == "correction.evidence.appended":
                if payload.get("proposal_id") != proposal_id:
                    continue
                record = payload.get("evidence_record")
                if isinstance(record, dict):
                    source_records.append(CorrectionSourceRecord.model_validate(record))
            elif event.event_type == "graph.transition.accepted":
                if (
                    payload.get("family") != "revision_approval"
                    or payload.get("object_id") != proposal_id
                ):
                    continue
                guard_evidence = payload.get("guard_evidence")
                if not isinstance(guard_evidence, dict):
                    continue
                validation = guard_evidence.get("validation_record")
                if isinstance(validation, dict):
                    record = CorrectionValidationRecord.model_validate(validation)
                    validations = [
                        item for item in validations if item.validation_id != record.validation_id
                    ] + [record]
                    conflicts = tuple(record.conflicts) or conflicts
                    impact_set = tuple(record.impact_set) or impact_set
                decision = guard_evidence.get("decision_record")
                if isinstance(decision, dict):
                    owner_decision = CorrectionOwnerDecision.model_validate(decision)
                    if owner_decision.decision == "approve" and owner_decision.approval_id:
                        publish_key = f"correction.publish:{owner_decision.approval_id}"
            elif event.event_type == "correction.revision.published":
                if payload.get("proposal_id") != proposal_id:
                    continue
                version = payload.get("published_version")
                if isinstance(version, dict):
                    published_version = CorrectionPublishedVersion.model_validate(version)
        if base is None:
            return None
        fields = dict(base)
        fields.update(
            {
                "source_records": tuple(source_records),
                "validations": tuple(validations),
                "owner_decision": owner_decision,
                "conflicts": conflicts,
                "impact_set": impact_set,
                "publish_idempotency_key": publish_key,
                "published_version": published_version,
                "state": canonical_state,
            }
        )
        return CorrectionProposal.model_validate(fields)

    def _canonical_state(self, proposal_id: str) -> str:
        state = self.executor.state()
        current = state.get("revision_approval", {}).get(proposal_id)
        if current is None:
            return RevisionApprovalState.SUBMITTED.value
        return str(current)

    def _save(self, proposal: CorrectionProposal) -> None:
        payload = proposal.model_dump(mode="json")
        with open_database(self.database_path) as database:
            database.execute(
                """
                INSERT INTO correction_proposals (
                    proposal_id, project_id, state, proposal_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(proposal_id) DO UPDATE
                SET state = excluded.state, proposal_json = excluded.proposal_json
                """,
                (
                    proposal.proposal_id,
                    proposal.project_id,
                    proposal.state,
                    _canonical_json_text(payload),
                    proposal.submitted_at.isoformat(),
                ),
            )

    def _load_or_none(self, proposal_id: str) -> CorrectionProposal | None:
        canonical = self._canonical_state(proposal_id)
        rebuilt = self._rebuild_from_events(proposal_id, canonical)
        if rebuilt is not None:
            return rebuilt
        return self._read_projection(proposal_id)

    # ── 幂等账本 ───────────────────────────────────────────────────────────

    def _claim(self, *, key: str, operation: str, result: dict[str, Any]) -> bool:
        """登记操作结果；返回 True 表示首次登记。同键同结果视为重放。"""
        result_digest = _payload_digest(result)
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT operation, result_digest FROM idempotency_keys WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                if str(row[0]) != operation or str(row[1]) != result_digest:
                    raise CorrectionConflictError(f"同一幂等键对应了不同操作或结果：{key}")
                return False
            database.execute(
                """
                INSERT INTO idempotency_keys (
                    idempotency_key, operation, result_digest, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (key, operation, result_digest, datetime.now().astimezone().isoformat()),
            )
        return True

    def _recorded_result_digest(self, key: str) -> str | None:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT result_digest FROM idempotency_keys WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
        return None if row is None else str(row[0])

    # ── 事件与迁移 ─────────────────────────────────────────────────────────

    def _append_business_event(
        self,
        *,
        event_type: str,
        event_kind: str,
        proposal_id: str,
        project_id: str,
        actor_id: str,
        occurred_at: datetime,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> None:
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(
                event_kind, project_id, _RUN_ID, proposal_id, _payload_digest(payload)
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

    def _transition(
        self,
        *,
        proposal: CorrectionProposal,
        to_state: RevisionApprovalState,
        request_id: str,
        evidence: dict[str, Any],
        actor_id: str,
        occurred_at: datetime,
    ) -> None:
        try:
            edge = binding_for_transition(proposal.state, to_state.value)
        except ValueError as error:
            raise CorrectionStateError(str(error)) from error
        request = TransitionRequest(
            schema_version="1.0",
            request_id=request_id,
            project_id=proposal.project_id,
            run_id=_RUN_ID,
            family="revision_approval",
            object_id=proposal.proposal_id,
            from_state=proposal.state,
            to_state=to_state.value,
            trigger=edge.trigger,
            evidence={"target_object_id": proposal.proposal_id, **evidence},
            actor_id=actor_id,
            occurred_at=occurred_at,
        )
        try:
            stored = self.executor.submit(request)
        except EventConflictError as error:
            raise CorrectionConflictError(str(error)) from error
        if stored.event_type == "graph.transition.rejected":
            reason = str(stored.payload.get("reason", "unknown"))
            guard_reason = stored.payload.get("guard_reason")
            detail = f"{reason}:{guard_reason}" if guard_reason else reason
            raise CorrectionStateError(f"修订状态迁移被拒绝：{detail}")

    # ── 快照绑定核验 ───────────────────────────────────────────────────────

    def _snapshot_path(self, report: str, snapshot_id: str) -> Path:
        return self.project_root / "snapshots" / "reports" / report / f"{snapshot_id}.json"

    def _verify_target_snapshot(
        self,
        *,
        project_id: str,
        report: _REPORT,
        snapshot_id: str,
        snapshot_sha256: str,
    ) -> ReportSnapshotManifest:
        path = self._snapshot_path(report, snapshot_id)
        if not path.is_file():
            raise CorrectionBindingError(
                "修订包绑定的报告快照在项目中不存在，请基于最新报告重新导出修订包。"
            )
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != snapshot_sha256:
            raise CorrectionBindingError("修订包绑定的快照摘要与项目快照不一致，快照可能已被取代。")
        try:
            manifest = ReportSnapshotManifest.model_validate(json.loads(raw))
            recomputed = compute_locked_snapshot(
                kind="report", report=report, manifest=manifest.model_dump(mode="json")
            )
        except (json.JSONDecodeError, SnapshotIntegrityError, ValueError) as error:
            raise CorrectionBindingError("修订绑定的快照不是有效的报告快照。") from error
        if manifest.project_id != project_id:
            raise CorrectionBindingError("修订包与当前项目不匹配。")
        if manifest.report != report:
            raise CorrectionBindingError("修订包声明的报告类型与快照不一致。")
        if recomputed.snapshot_id != snapshot_id:
            raise CorrectionBindingError("修订绑定的快照标识与内容身份不一致。")
        latest_snapshot_id = self._latest_snapshot_id(project_id=project_id, report=report)
        if latest_snapshot_id is not None and snapshot_id != latest_snapshot_id:
            raise CorrectionBindingError(
                "该报告已存在更新的版本，请基于最新报告重新导出修订包后再提交。"
            )
        return manifest

    def _latest_snapshot_id(self, *, project_id: str, report: str) -> str | None:
        """按已登记清单时间判断当前快照，避免发布时间或时区文本干扰。"""
        with open_database(self.database_path) as database:
            rows = database.execute(
                """
                SELECT snapshot_id, manifest_json
                FROM report_snapshots
                WHERE project_id = ? AND report_kind = ?
                """,
                (project_id, report),
            ).fetchall()
        if not rows:
            return None
        candidates: list[tuple[datetime, str]] = []
        for snapshot_id, manifest_json in rows:
            try:
                manifest = ReportSnapshotManifest.model_validate(json.loads(str(manifest_json)))
            except (json.JSONDecodeError, ValueError) as error:
                raise CorrectionBindingError(
                    "已登记报告版本的快照清单无效，暂不能提交修订。"
                ) from error
            candidates.append((manifest.created_at, str(snapshot_id)))
        return max(candidates, key=lambda item: item[0])[1]

    # ── 操作 1：submit ─────────────────────────────────────────────────────

    def submit(
        self,
        *,
        project_id: str,
        report: _REPORT,
        snapshot_id: str,
        snapshot_sha256: str,
        target_type: _TARGET_TYPE,
        target_id: str,
        current_visible_value: str,
        rationale_zh: str,
        submitted_by: str,
        report_owner_id: str,
        proposed_value: str | None = None,
        proposed_explanation: str | None = None,
        attachments: tuple[CorrectionAttachment, ...] = (),
        occurred_at: datetime,
    ) -> CorrectionProposal:
        """校验项目与当前快照绑定，保存首次建议与事件；重复提交返回既有建议。"""
        proposal_id = stable_id(
            "correction-proposal",
            project_id,
            report,
            snapshot_id,
            snapshot_sha256,
            target_type,
            target_id,
            _payload_digest(
                {
                    "current_visible_value": current_visible_value,
                    "proposed_value": proposed_value,
                    "proposed_explanation": proposed_explanation,
                    "rationale_zh": rationale_zh,
                }
            ),
        )
        existing = self._load_or_none(proposal_id)
        if existing is not None:
            return existing
        if _STABLE_ID.fullmatch(target_id) is None:
            raise CorrectionBindingError("修订目标必须使用项目稳定标识。")
        projects = {event.project_id for event in self.event_store.read_all()}
        if projects and projects != {project_id}:
            raise CorrectionBindingError("修订包与当前项目的项目身份不一致。")
        manifest = self._verify_target_snapshot(
            project_id=project_id,
            report=report,
            snapshot_id=snapshot_id,
            snapshot_sha256=snapshot_sha256,
        )
        if target_type == "claim" and target_id not in manifest.claim_ids:
            raise CorrectionBindingError("修订目标不在当前报告快照中，请从最新报告重新发起修订。")
        proposal = CorrectionProposal(
            proposal_id=proposal_id,
            project_id=project_id,
            report=report,
            report_version=manifest.report_version,
            snapshot_id=snapshot_id,
            snapshot_sha256=snapshot_sha256,
            target_type=target_type,
            target_id=target_id,
            current_visible_value=current_visible_value,
            proposed_value=proposed_value,
            proposed_explanation=proposed_explanation,
            rationale_zh=rationale_zh,
            submitted_at=occurred_at,
            submitted_by=submitted_by,
            report_owner_id=report_owner_id,
            attachments=attachments,
            state=RevisionApprovalState.SUBMITTED.value,
        )
        self._append_business_event(
            event_type="correction.proposal.submitted",
            event_kind="correction-submitted",
            proposal_id=proposal_id,
            project_id=project_id,
            actor_id=submitted_by,
            occurred_at=occurred_at,
            payload={"proposal": proposal.model_dump(mode="json")},
            idempotency_key=(
                f"correction.submit:{proposal_id}:"
                f"{_payload_digest(proposal.model_dump(mode='json'))}"
            ),
        )
        self._save(proposal)
        return proposal

    # ── 操作 2：add_evidence ───────────────────────────────────────────────

    def add_evidence(
        self,
        proposal_id: str,
        *,
        note_zh: str,
        recorded_by: str,
        occurred_at: datetime,
        source_refs: tuple[CorrectionAttachment, ...] = (),
    ) -> CorrectionProposal:
        """向同一建议追加来源；不覆盖原提交，需补证据的建议回到已提交。"""
        proposal = self.load(proposal_id)
        if proposal.state not in (
            RevisionApprovalState.SUBMITTED.value,
            RevisionApprovalState.NEEDS_EVIDENCE.value,
        ):
            raise CorrectionStateError("当前修订状态不允许追加来源材料。")
        evidence_id = stable_id(
            "correction-evidence",
            proposal_id,
            _payload_digest(
                {
                    "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
                    "note_zh": note_zh,
                    "recorded_by": recorded_by,
                }
            ),
        )
        existing_record = next(
            (record for record in proposal.source_records if record.evidence_id == evidence_id),
            None,
        )
        if existing_record is not None:
            if proposal.state == RevisionApprovalState.NEEDS_EVIDENCE.value:
                self._transition(
                    proposal=proposal,
                    to_state=RevisionApprovalState.SUBMITTED,
                    request_id=stable_id("correction-evidence-submit", proposal_id, evidence_id),
                    evidence={"new_evidence_appended": True, "evidence_id": evidence_id},
                    actor_id=recorded_by,
                    occurred_at=occurred_at,
                )
                proposal = proposal.model_copy(
                    update={"state": RevisionApprovalState.SUBMITTED.value}
                )
                self._save(proposal)
            return proposal
        record = CorrectionSourceRecord(
            evidence_id=evidence_id,
            source_refs=source_refs,
            note_zh=note_zh,
            recorded_by=recorded_by,
            recorded_at=occurred_at,
        )
        self._append_business_event(
            event_type="correction.evidence.appended",
            event_kind="correction-evidence",
            proposal_id=proposal_id,
            project_id=proposal.project_id,
            actor_id=recorded_by,
            occurred_at=occurred_at,
            payload={"proposal_id": proposal_id, "evidence_record": record.model_dump(mode="json")},
            idempotency_key=f"correction.evidence:{proposal_id}:{evidence_id}",
        )
        updated = proposal.model_copy(update={"source_records": (*proposal.source_records, record)})
        if proposal.state == RevisionApprovalState.NEEDS_EVIDENCE.value:
            self._transition(
                proposal=updated,
                to_state=RevisionApprovalState.SUBMITTED,
                request_id=stable_id("correction-evidence-submit", proposal_id, evidence_id),
                evidence={"new_evidence_appended": True, "evidence_id": evidence_id},
                actor_id=recorded_by,
                occurred_at=occurred_at,
            )
            updated = updated.model_copy(update={"state": RevisionApprovalState.SUBMITTED.value})
        self._save(updated)
        return updated

    # ── 操作 3：validate ───────────────────────────────────────────────────

    def validate(
        self,
        proposal_id: str,
        *,
        outcome: _OUTCOME,
        disposition_reason_zh: str,
        validated_by: str,
        occurred_at: datetime,
        identity_verified: bool = True,
        context_located: bool = True,
        locator_verified: bool = True,
        conflicts_checked: bool = True,
        impact_checked: bool = True,
        conflicts: tuple[str, ...] = (),
        impact_set: tuple[str, ...] = (),
    ) -> CorrectionProposal:
        """记录验证处置；结果只能是需补证据、拒绝或等待用户批准，绝不能批准。"""
        proposal = self.load(proposal_id)
        validation_id = stable_id(
            "correction-validation",
            proposal_id,
            _payload_digest(
                {
                    "outcome": outcome,
                    "disposition_reason_zh": disposition_reason_zh,
                    "identity_verified": identity_verified,
                    "context_located": context_located,
                    "locator_verified": locator_verified,
                    "conflicts_checked": conflicts_checked,
                    "impact_checked": impact_checked,
                    "conflicts": list(conflicts),
                    "impact_set": list(impact_set),
                    "validated_by": validated_by,
                }
            ),
        )
        if any(item.validation_id == validation_id for item in proposal.validations):
            return proposal
        if proposal.state != RevisionApprovalState.SUBMITTED.value:
            raise CorrectionStateError("只有已提交状态的修订建议可以进入验证处置。")
        if outcome == "passed" and not all(
            (
                identity_verified,
                context_located,
                locator_verified,
                conflicts_checked,
                impact_checked,
                bool(impact_set),
            )
        ):
            raise CorrectionStateError(
                "来源身份、上下文、证据定位、冲突和影响范围未全部核验，不能提交批准。"
            )
        record = CorrectionValidationRecord(
            validation_id=validation_id,
            outcome=outcome,
            disposition_reason_zh=disposition_reason_zh,
            identity_verified=identity_verified,
            context_located=context_located,
            locator_verified=locator_verified,
            conflicts_checked=conflicts_checked,
            impact_checked=impact_checked,
            conflicts=conflicts,
            impact_set=impact_set,
            validated_by=validated_by,
            validated_at=occurred_at,
        )
        outcome_state = {
            "needs_evidence": RevisionApprovalState.NEEDS_EVIDENCE,
            "rejected": RevisionApprovalState.REJECTED,
            "passed": RevisionApprovalState.VALIDATED_PENDING_USER_APPROVAL,
        }[outcome]
        outcome_flag = {
            "needs_evidence": "needs_more_evidence",
            "rejected": "validation_rejected",
            "passed": "validation_passed",
        }[outcome]
        self._transition(
            proposal=proposal,
            to_state=outcome_state,
            request_id=stable_id("correction-validation", proposal_id, validation_id),
            evidence={
                "validation_complete": True,
                outcome_flag: True,
                "disposition_reason_saved": True,
                "validation_record": record.model_dump(mode="json"),
            },
            actor_id=validated_by,
            occurred_at=occurred_at,
        )
        updated = proposal.model_copy(
            update={
                "state": outcome_state.value,
                "validations": (*proposal.validations, record),
                "conflicts": conflicts or proposal.conflicts,
                "impact_set": impact_set or proposal.impact_set,
            }
        )
        self._save(updated)
        return updated

    # ── 操作 4：record_owner_decision ──────────────────────────────────────

    def record_owner_decision(
        self,
        proposal_id: str,
        *,
        decision: _DECISION,
        decided_by: str,
        reason_zh: str,
        occurred_at: datetime,
    ) -> CorrectionProposal:
        """只接受报告所有者的明确批准、拒绝或要求补证据；验证本身不能批准。"""
        proposal = self.load(proposal_id)
        approval_id = stable_id(
            "revision-approval",
            proposal_id,
            decision,
            decided_by,
            _payload_digest({"reason_zh": reason_zh}),
        )
        recorded = proposal.owner_decision
        if (
            recorded is not None
            and recorded.decision == decision
            and recorded.approval_id == approval_id
        ):
            # 同一决定的精确重放（含发布中断恢复）：幂等返回，并补齐可能
            # 因中断缺失的批准副作用（事件与账本均幂等去重）。
            if decision == "approve":
                self._record_approval_side_effect(
                    approval_id=approval_id,
                    decided_by=decided_by,
                    occurred_at=occurred_at,
                    project_id=proposal.project_id,
                )
            return proposal
        if proposal.state != RevisionApprovalState.VALIDATED_PENDING_USER_APPROVAL.value:
            raise CorrectionStateError("修订建议尚未完成核验，只有核验通过后报告负责人才能决定。")
        if decided_by != proposal.report_owner_id:
            raise CorrectionOwnerError("只有报告负责人本人可以批准、拒绝或要求补充证据。")
        decision_record = CorrectionOwnerDecision(
            decision=decision,
            approval_id=approval_id if decision == "approve" else None,
            decided_by=decided_by,
            decided_at=occurred_at,
            reason_zh=reason_zh,
        )
        decision_flag = {
            "approve": "decision_approve",
            "reject": "decision_reject",
            "needs_evidence": "decision_needs_evidence",
        }[decision]
        outcome_state = {
            "approve": RevisionApprovalState.APPROVED,
            "reject": RevisionApprovalState.REJECTED,
            "needs_evidence": RevisionApprovalState.NEEDS_EVIDENCE,
        }[decision]
        self._transition(
            proposal=proposal,
            to_state=outcome_state,
            request_id=stable_id("correction-decision", proposal_id, approval_id),
            evidence={
                "owner_explicit_decision": True,
                decision_flag: True,
                "approval_id": approval_id,
                "decision_record": decision_record.model_dump(mode="json"),
            },
            actor_id=decided_by,
            occurred_at=occurred_at,
        )
        updated = proposal.model_copy(
            update={
                "state": outcome_state.value,
                "owner_decision": decision_record,
                "publish_idempotency_key": (
                    f"correction.publish:{approval_id}"
                    if decision == "approve"
                    else proposal.publish_idempotency_key
                ),
            }
        )
        self._save(updated)
        if decision == "approve":
            self._record_approval_side_effect(
                approval_id=approval_id,
                decided_by=decided_by,
                occurred_at=occurred_at,
                project_id=proposal.project_id,
            )
        return updated

    def _record_approval_side_effect(
        self,
        *,
        approval_id: str,
        decided_by: str,
        occurred_at: datetime,
        project_id: str,
    ) -> None:
        """批准以 ``revision.approve`` 副作用事件进入既有审批账本（幂等）。"""
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id("correction-approve", project_id, _RUN_ID, approval_id),
            project_id=project_id,
            run_id=_RUN_ID,
            event_type="revision.approve",
            occurred_at=occurred_at,
            actor_id=decided_by,
            idempotency_key=f"correction.approve:{approval_id}",
            payload={
                "approval_id": approval_id,
                "decision": "approve",
                "approver": decided_by,
            },
        )
        stored = self.event_store.append(event)
        self.executor.side_effects(stored)

    # ── 操作 5：publish ────────────────────────────────────────────────────

    def publish(
        self,
        proposal_id: str,
        *,
        new_snapshot_manifest: dict[str, Any],
        rebuilt_artifacts: tuple[dict[str, Any], ...],
        independent_qc: dict[str, Any],
        occurred_at: datetime,
    ) -> CorrectionProposal:
        """核验批准与发布前置条件后幂等登记新版本；不修改任何旧版本。

        失败关闭顺序：已登记结果短路 → 批准材料 → 状态 → 前置条件 →
        迁移 → 登记。任何前置失败保留批准状态并追加失败原因事件；发布中断
        后同一批准重入可恢复，不重复登记版本。
        """
        proposal = self.load(proposal_id)
        publish_key = proposal.publish_idempotency_key
        if publish_key is None or proposal.owner_decision is None:
            raise CorrectionStateError("修订建议还没有报告负责人的批准，不能发布。")
        claim_key = f"correction.publish:{proposal_id}:{publish_key}"
        existing_digest = self._recorded_result_digest(claim_key)
        if existing_digest is not None:
            return self._verify_recorded_publish(proposal, existing_digest)
        if proposal.state not in (
            RevisionApprovalState.APPROVED.value,
            RevisionApprovalState.PUBLISHED.value,
        ):
            raise CorrectionStateError("只有已批准状态的修订建议可以发布；请先完成批准。")
        approval_id = proposal.owner_decision.approval_id or ""
        if not approval_id.strip():
            raise CorrectionStateError("批准记录缺少批准标识，不能发布。")
        new_version = self._next_report_version(proposal.report_version)
        try:
            locked_new = self._verify_publish_materials(
                proposal=proposal,
                new_snapshot_manifest=new_snapshot_manifest,
                rebuilt_artifacts=rebuilt_artifacts,
                independent_qc=independent_qc,
            )
            if proposal.state == RevisionApprovalState.APPROVED.value:
                self._transition(
                    proposal=proposal,
                    to_state=RevisionApprovalState.PUBLISHED,
                    request_id=stable_id(
                        "correction-publish",
                        proposal_id,
                        approval_id,
                        _payload_digest(
                            {
                                "new_snapshot_id": locked_new.snapshot_id,
                                "rebuilt_artifacts": rebuilt_artifacts,
                                "independent_qc": independent_qc,
                            }
                        ),
                    ),
                    evidence={
                        "new_snapshot_built": True,
                        "affected_artifacts_rebuilt": True,
                        "independent_qc_passed": True,
                        "approval_id": approval_id,
                        "new_snapshot_id": locked_new.snapshot_id,
                        "new_snapshot_sha256": locked_new.sha256,
                        "new_report_version": new_version,
                    },
                    actor_id=proposal.report_owner_id,
                    occurred_at=occurred_at,
                )
        except (CorrectionPublishError, CorrectionStateError) as error:
            self._record_publish_failure(
                proposal=proposal,
                approval_id=approval_id,
                reason=str(error),
                occurred_at=occurred_at,
            )
            raise
        return self._register_new_version(
            proposal=proposal,
            locked_new=locked_new,
            new_version=new_version,
            publish_key=publish_key,
            approval_id=approval_id,
            occurred_at=occurred_at,
        )

    def _verify_recorded_publish(
        self,
        proposal: CorrectionProposal,
        existing_digest: str,
    ) -> CorrectionProposal:
        """已登记的发布：同一结果视为重放返回；不同结果失败关闭。"""
        current = proposal.published_version
        result_digest = (
            _payload_digest({"published_version": current.model_dump(mode="json")})
            if current is not None
            else ""
        )
        if result_digest != existing_digest:
            raise CorrectionConflictError("同一批准标识对应的发布结果与登记记录不一致。")
        return proposal

    def _record_publish_failure(
        self,
        *,
        proposal: CorrectionProposal,
        approval_id: str,
        reason: str,
        occurred_at: datetime,
    ) -> None:
        """发布失败：批准状态保留，追加失败原因事件，等待相同建议恢复。"""
        payload = {
            "proposal_id": proposal.proposal_id,
            "approval_id": approval_id,
            "failure_reason_zh": reason,
        }
        self._append_business_event(
            event_type="correction.publish.failed",
            event_kind="correction-publish-failed",
            proposal_id=proposal.proposal_id,
            project_id=proposal.project_id,
            actor_id=proposal.report_owner_id,
            occurred_at=occurred_at,
            payload=payload,
            idempotency_key=(
                f"correction.publish.failed:{proposal.proposal_id}:{approval_id}:"
                f"{_payload_digest(payload)}"
            ),
        )

    def _verify_publish_materials(
        self,
        *,
        proposal: CorrectionProposal,
        new_snapshot_manifest: dict[str, Any],
        rebuilt_artifacts: tuple[dict[str, Any], ...],
        independent_qc: dict[str, Any],
    ) -> LockedSnapshot:
        """发布前置核验：新快照实质变化、重建材料与独立质控缺一失败关闭。"""
        if not rebuilt_artifacts:
            raise CorrectionPublishError("发布缺少受影响内容的重建记录，已保留批准状态。")
        for artifact in rebuilt_artifacts:
            if not _is_nonblank_str(artifact.get("artifact_id")) or not _is_sha256(
                artifact.get("sha256")
            ):
                raise CorrectionPublishError("受影响内容的重建记录不完整，已保留批准状态。")
        if (
            not _is_nonblank_str(independent_qc.get("qc_verdict_id"))
            or independent_qc.get("qc_result") != "accepted"
            or not _is_nonblank_str(independent_qc.get("reviewer_id"))
            or not _is_nonblank_str(independent_qc.get("qc_checked_at"))
            or not _is_nonblank_str(independent_qc.get("reviewed_snapshot_id"))
            or not _is_sha256(independent_qc.get("reviewed_snapshot_content_digest"))
        ):
            raise CorrectionPublishError("发布缺少独立质控结论，已保留批准状态。")
        if independent_qc["reviewer_id"] == proposal.report_owner_id:
            raise CorrectionPublishError("独立质控不能由本次修订的报告负责人本人完成。")
        try:
            _offset_datetime(datetime.fromisoformat(str(independent_qc["qc_checked_at"])))
        except (TypeError, ValueError) as error:
            raise CorrectionPublishError("独立质控时间必须包含明确时区。") from error
        try:
            new_manifest = ReportSnapshotManifest.model_validate(new_snapshot_manifest)
            candidate = compute_locked_snapshot(
                kind="report",
                report=proposal.report,
                manifest=new_manifest.model_dump(mode="json"),
            )
        except (SnapshotIntegrityError, ValueError) as error:
            raise CorrectionPublishError(f"新快照不符合报告快照合同：{error}") from error
        if new_manifest.project_id != proposal.project_id:
            raise CorrectionPublishError("新快照与本次修订所属项目不一致。")
        if new_manifest.report != proposal.report:
            raise CorrectionPublishError("新快照与本次修订的报告类型不一致。")
        expected_version = self._next_report_version(proposal.report_version)
        if new_manifest.report_version != expected_version:
            raise CorrectionPublishError(f"新快照必须登记为紧邻的下一版本 {expected_version}。")
        if (
            independent_qc["reviewed_snapshot_id"] != candidate.snapshot_id
            or independent_qc["reviewed_snapshot_content_digest"] != candidate.sha256
        ):
            raise CorrectionPublishError("独立质控结论未绑定本次待发布的新快照。")
        if (
            proposal.published_version is not None
            and proposal.published_version.snapshot_id != candidate.snapshot_id
        ):
            raise CorrectionPublishError("同一批准记录已绑定另一份发布结果，不能改用不同材料重试。")
        if candidate.snapshot_id == proposal.snapshot_id:
            raise CorrectionPublishError("新快照与修订目标快照相同，发布必须建立新快照。")
        try:
            old_manifest = ReportSnapshotManifest.model_validate(
                json.loads(
                    self._snapshot_path(proposal.report, proposal.snapshot_id).read_text(
                        encoding="utf-8"
                    )
                )
            )
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as error:
            raise CorrectionPublishError("当前版本快照无法核验，已保留批准状态。") from error
        if self._material_view(old_manifest) == self._material_view(new_manifest):
            raise CorrectionPublishError("新快照的实质内容与当前版本一致，没有需要发布的变化。")
        try:
            return self.snapshot_store.lock_report_snapshot(
                report=proposal.report,
                manifest=new_manifest.model_dump(mode="json"),
            )
        except (SnapshotIntegrityError, ValueError) as error:
            raise CorrectionPublishError(f"新快照无法按内容寻址合同锁定：{error}") from error

    @staticmethod
    def _material_view(manifest: ReportSnapshotManifest) -> dict[str, Any]:
        """快照实质内容视图：排除版本号与时间戳后的可比字段。"""
        return {
            "claim_ids": list(manifest.claim_ids),
            "evidence_snapshot_id": manifest.evidence_snapshot_id,
            "claim_snapshot_id": manifest.claim_snapshot_id,
            "coverage_set_id": manifest.coverage_set_id,
            "data_cutoff": manifest.data_cutoff.isoformat(),
        }

    @staticmethod
    def _version_rank(version: str) -> int | None:
        match = _VERSION.fullmatch(version.strip())
        return int(match.group("number")) if match is not None else None

    @classmethod
    def _next_report_version(cls, current_version: str) -> str:
        rank = cls._version_rank(current_version)
        if rank is None:
            raise CorrectionPublishError("当前报告版本无法递增，发布终止。")
        return f"v{rank + 1}"

    def _register_new_version(
        self,
        *,
        proposal: CorrectionProposal,
        locked_new: LockedSnapshot,
        new_version: str,
        publish_key: str,
        approval_id: str,
        occurred_at: datetime,
    ) -> CorrectionProposal:
        """幂等登记新版本：INSERT 按主键去重；旧版本行与旧快照不改动。"""
        manifest_path = self.project_root.joinpath(*PurePosixPath(locked_new.relative_path).parts)
        manifest = ReportSnapshotManifest.model_validate(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        manifest_json = _canonical_json_text(manifest.model_dump(mode="json"))
        with open_database(self.database_path) as database:
            existing = database.execute(
                "SELECT report_version FROM report_snapshots WHERE snapshot_id = ?",
                (locked_new.snapshot_id,),
            ).fetchone()
            if existing is None:
                try:
                    database.execute(
                        """
                        INSERT INTO report_snapshots (
                            snapshot_id, project_id, report_kind, report_version,
                            evidence_state, manifest_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            locked_new.snapshot_id,
                            proposal.project_id,
                            proposal.report,
                            new_version,
                            "snapshot_locked",
                            manifest_json,
                            manifest.created_at.isoformat(),
                        ),
                    )
                except sqlite3.IntegrityError as error:
                    raise CorrectionPublishError(
                        "新版本登记与既有版本冲突，发布失败关闭。"
                    ) from error
            elif str(existing[0]) != new_version:
                raise CorrectionPublishError("同一快照身份已登记为其他版本，发布失败关闭。")
        published_version = CorrectionPublishedVersion(
            report_version=new_version,
            snapshot_id=locked_new.snapshot_id,
            snapshot_sha256=locked_new.sha256,
            supersedes_snapshot_id=proposal.snapshot_id,
            published_at=occurred_at,
        )
        updated = proposal.model_copy(
            update={
                "state": RevisionApprovalState.PUBLISHED.value,
                "published_version": published_version,
            }
        )
        result = {"published_version": published_version.model_dump(mode="json")}
        self._append_business_event(
            event_type="correction.revision.published",
            event_kind="correction-published",
            proposal_id=proposal.proposal_id,
            project_id=proposal.project_id,
            actor_id=proposal.report_owner_id,
            occurred_at=occurred_at,
            payload={
                "proposal_id": proposal.proposal_id,
                "approval_id": approval_id,
                "publish_idempotency_key": publish_key,
                **result,
            },
            idempotency_key=(f"correction.publish.recorded:{proposal.proposal_id}:{approval_id}"),
        )
        self._save(updated)
        self._claim(
            key=f"correction.publish:{proposal.proposal_id}:{publish_key}",
            operation="correction.publish",
            result=result,
        )
        return updated
