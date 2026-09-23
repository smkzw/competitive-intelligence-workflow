"""Task 9.2 增量刷新与影响传播服务：父版本绑定、截止日扩展、候选晋级、
GateSpec 收紧、局部重建回执、不可变历史与幂等恢复。

边界（design.md）：本服务位于应用层，只读取已登记项目合同版本、已锁定快照、
来源版本/回执、缺口与候选记录。扩大截止日与门槛收紧都通过追加新的项目合同
版本表达；父合同行、父快照和父报告字节不变且保持可读。影响传播不在这里复制
任何规则：门槛收紧复用 :mod:`ci_workflow.gates.coverage` 的只收紧偏序、变化
单元与受影响报告计算；影响闭包复用 :mod:`ci_workflow.graph.impact`（Task 9.2
图定义工作项）的确定性反向依赖；候选晋级复用
:func:`ci_workflow.sources.planner.assess_historical_source` 的历史截止日语义。

- 刷新计划与每个重建动作使用稳定幂等键：精确重放返回同一计划、同一子版本
  与同一回执；同一键对应不同输入失败关闭。
- 未完成的局部重建不能把子版本登记为已接受：受影响对象没有完整重建回执、
  受影响报告缺少通过的门槛决定或新报告快照时，接受操作失败关闭。
- 重大 Schema/本体/证据合同变化不做局部刷新，明确要求重新建立基线；
  放宽型门槛覆盖被拒绝，不伪装成局部刷新。
- 首版只处理站点式 HTML（决策 0013）：格式级受影响对象只允许 ``html``。
- 面向用户的表述只有自然中文；机器状态只保存在合同字段中。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.domain.contracts import ProjectContract, refresh_project_contract
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator, SourceVersionRecord
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.coverage import (
    compute_affected_report_kinds,
    compute_changed_unit_ids,
    validate_override_declaration,
    validate_spec_override,
)
from ci_workflow.gates.models import (
    GateOverride,
    GateSpec,
    ReportDecision,
    ReportGateResult,
)
from ci_workflow.graph.definitions.refresh import (
    REBASELINE_REQUIRED_MESSAGE_ZH,
    RefreshBaselineIdentity,
    classify_refresh_branch,
)
from ci_workflow.graph.impact import (
    ImpactEdge,
    ImpactGraph,
    ImpactLayer,
    ImpactNode,
)
from ci_workflow.qc.scientific import (
    ScientificQcReviewBundle,
    ScientificQcVerdict,
    check_scientific_qc_review_bundle_semantics,
    check_scientific_qc_verdict_semantics,
)
from ci_workflow.sources.planner import (
    HistoricalCutoffState,
    assess_historical_source,
)
from ci_workflow.storage.event_store import EventStore, WorkflowEvent
from ci_workflow.storage.migrations import (
    MigrationError,
    apply_migrations,
    persist_project_contract,
)
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    ReportSnapshotManifest,
    SnapshotIntegrityError,
    SnapshotStore,
    compute_locked_snapshot,
)
from ci_workflow.storage.sqlite import open_database

if TYPE_CHECKING:
    from ci_workflow.application.user_fact_edit import RefreshConflictComparison

_RUN_ID = "refresh"
_PLAN_EVENT = "refresh.plan.created"
_PROMOTION_EVENT = "refresh.candidates.promoted"
_REBUILD_EVENT = "refresh.rebuild.recorded"
_GATE_DECISION_EVENT = "refresh.gate.decision.recorded"
_SNAPSHOT_EVENT = "refresh.report.snapshot.registered"
_QC_EVENT = "refresh.scientific_qc.recorded"
_ACCEPTED_EVENT = "refresh.version.accepted"
_USER_FACT_COMPARISON_EVENT = "refresh.user_fact.compared"

# 首版唯一必选交付格式（决策 0013）
_SUPPORTED_FORMATS: tuple[str, ...] = ("html",)

_OBJECT_KINDS = tuple(layer.value for layer in ImpactLayer)
_PARENT_BASELINE_ONTOLOGY_VERSION = "1.0"
_EVIDENCE_CONTRACT_VERSION = "1.0"
_DATE_ROLES = ("acquired_at", "published_at", "effective_at", "first_disclosed_at")


class RefreshServiceError(RuntimeError):
    """增量刷新服务合同失败；消息中文陈述事实。"""


class RefreshRebaselineRequired(RefreshServiceError):
    """重大 Schema/本体/证据合同变化：不做局部刷新，需要重新建立基线。"""


class RefreshConflictError(RefreshServiceError):
    """同一幂等键被另一份刷新输入复用。"""


class RefreshStateError(RefreshServiceError):
    """当前项目或刷新状态不允许该操作。"""


class RefreshIncompleteError(RefreshServiceError):
    """局部重建未完成：子版本不能登记为已接受。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("刷新字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("刷新时间必须包含明确时区偏移")
    return value


def _canonical_json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_digest(value: object) -> str:
    return hashlib.sha256(_canonical_json_text(value).encode("utf-8")).hexdigest()


# ── 机器合同 ─────────────────────────────────────────────────────────────────


class ImpactedObject(BaseModel):
    """影响集合或复用集合中的一个稳定对象。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    object_kind: str
    object_id: str

    @field_validator("object_kind")
    @classmethod
    def _kind_is_closed(cls, value: str) -> str:
        normalized = _not_blank(value)
        if normalized not in _OBJECT_KINDS:
            raise ValueError("影响对象种类必须是来源、事实、声明、页面或格式")
        return normalized

    @field_validator("object_id")
    @classmethod
    def _id_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def _format_is_site_html_first(self) -> ImpactedObject:
        if self.object_kind == "format" and self.object_id not in _SUPPORTED_FORMATS:
            raise ValueError("首版只处理站点式 HTML，其他格式不做局部重建")
        return self


class CandidatePromotion(BaseModel):
    """因截止日扩大而新适格、进入本轮重评的候选来源。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    source_id: str
    first_disclosed_at: datetime
    rationale_zh: str

    @field_validator("source_version_id", "source_id", "rationale_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("first_disclosed_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class BlockedCandidate(BaseModel):
    """仍未适格或披露时间未解决的候选来源；继续阻断，不进入重评。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    source_id: str
    reason_code: str
    rationale_zh: str

    @field_validator("source_version_id", "source_id", "rationale_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("reason_code")
    @classmethod
    def _reason_is_declared(cls, value: str) -> str:
        normalized = _not_blank(value)
        declared = {member.value for member in HistoricalCutoffState}
        if normalized not in declared:
            raise ValueError("候选阻断原因不在已声明的截止日评估状态之内")
        return normalized


class GateSpecBinding(BaseModel):
    """本轮报告必须使用的子规则版本与内容指纹。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_kind: ReportKind
    spec_version: str
    spec_fingerprint: str

    @field_validator("spec_version")
    @classmethod
    def _version_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("spec_fingerprint")
    @classmethod
    def _fingerprint_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class ObjectChangeRecord(BaseModel):
    """本轮影响范围内对象的可审计变化分类。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    object_kind: str
    object_id: str
    change_kind: Literal["new", "changed", "withdrawn", "revised", "superseded", "unchanged"]
    basis_digest: str
    related_object_id: str | None = None
    rationale_zh: str

    @field_validator("object_kind")
    @classmethod
    def _kind_is_closed(cls, value: str) -> str:
        normalized = _not_blank(value)
        if normalized not in _OBJECT_KINDS:
            raise ValueError("变化对象种类必须是来源、事实、声明、页面或格式")
        return normalized

    @field_validator("object_id", "rationale_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("basis_digest")
    @classmethod
    def _basis_is_sha256(cls, value: str) -> str:
        normalized = _not_blank(value)
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("变化依据摘要必须是小写 SHA-256")
        return normalized

    @field_validator("related_object_id")
    @classmethod
    def _related_is_not_blank(cls, value: str | None) -> str | None:
        return _not_blank(value) if value is not None else None

    @model_validator(mode="after")
    def _superseded_has_successor(self) -> ObjectChangeRecord:
        if self.change_kind == "superseded" and self.related_object_id is None:
            raise ValueError("被取代对象必须指向接替对象")
        return self


class RefreshPlan(BaseModel):
    """确定性、可重放的增量刷新计划。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    refresh_id: str
    project_id: str
    parent_contract: ProjectContract
    child_contract: ProjectContract
    change_kinds: tuple[Literal["cutoff_expansion", "gate_tightening"], ...]
    requested_cutoff: datetime
    promoted: tuple[CandidatePromotion, ...] = ()
    blocked: tuple[BlockedCandidate, ...] = ()
    gate_override: GateOverride | None = None
    gate_spec_bindings: tuple[GateSpecBinding, ...] = ()
    affected_report_kinds: tuple[ReportKind, ...] = ()
    rebuild_report_kinds: tuple[ReportKind, ...] = ()
    reuse_report_kinds: tuple[ReportKind, ...] = ()
    affected_objects: tuple[ImpactedObject, ...] = ()
    reuse_objects: tuple[ImpactedObject, ...] = ()
    change_records: tuple[ObjectChangeRecord, ...] = ()
    impact_plan_digest: str | None = None
    plan_digest: str
    created_at: datetime

    @field_validator("refresh_id", "project_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("requested_cutoff", "created_at")
    @classmethod
    def _times_have_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("change_kinds")
    @classmethod
    def _change_kinds_are_unique_and_nonempty(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values:
            raise ValueError("刷新计划必须至少声明一种增量变化")
        if len(set(values)) != len(values):
            raise ValueError("增量变化种类不得重复")
        return values

    @model_validator(mode="after")
    def _plan_is_internally_consistent(self) -> RefreshPlan:
        if self.child_contract.project_id != self.parent_contract.project_id:
            raise ValueError("子合同与父合同的项目身份不一致")
        if self.child_contract.contract_version != self.parent_contract.contract_version + 1:
            raise ValueError("子合同版本必须是父合同版本的紧邻下一版")
        if self.child_contract.data_cutoff < self.parent_contract.data_cutoff:
            raise ValueError("子合同截止日不得早于父合同")
        if self.project_id != self.parent_contract.project_id:
            raise ValueError("计划项目身份与父合同不一致")
        promoted_ids = [item.source_version_id for item in self.promoted]
        if len(set(promoted_ids)) != len(promoted_ids):
            raise ValueError("晋级候选不得重复")
        affected_pairs = [(item.object_kind, item.object_id) for item in self.affected_objects]
        reuse_pairs = [(item.object_kind, item.object_id) for item in self.reuse_objects]
        if len(set(affected_pairs)) != len(affected_pairs):
            raise ValueError("影响对象集合不得重复")
        if len(set(reuse_pairs)) != len(reuse_pairs):
            raise ValueError("复用对象集合不得重复")
        if set(affected_pairs) & set(reuse_pairs):
            raise ValueError("同一对象不能同时出现在影响集合与复用集合")
        change_pairs = [(item.object_kind, item.object_id) for item in self.change_records]
        if len(set(change_pairs)) != len(change_pairs):
            raise ValueError("同一对象只能登记一种本轮变化")
        if set(change_pairs) != set(affected_pairs) | set(reuse_pairs):
            raise ValueError("变化台账必须完整覆盖影响对象与复用对象")
        change_by_pair = {
            (item.object_kind, item.object_id): item.change_kind for item in self.change_records
        }
        if any(change_by_pair[pair] != "unchanged" for pair in reuse_pairs):
            raise ValueError("复用对象只能登记为未变化")
        if any(change_by_pair[pair] == "unchanged" for pair in affected_pairs):
            raise ValueError("受影响对象不得登记为未变化")
        for promotion in self.promoted:
            if ("source", promotion.source_version_id) not in set(affected_pairs):
                raise ValueError("晋级候选必须出现在影响集合中等待重评")
            if change_by_pair[("source", promotion.source_version_id)] != "new":
                raise ValueError("晋级候选必须登记为新增对象")
        if self.affected_objects and not any(
            item.object_kind in ("claim", "page", "format") for item in self.affected_objects
        ):
            # 影响至少要能落到事实、声明、页面和格式层级（由影响闭包传播）；
            # 只停留在来源层级说明依赖边缺失，失败关闭。
            raise ValueError("影响集合只停留在来源层级：缺少事实/声明/页面/格式依赖边")
        if self.affected_report_kinds and self.gate_override is None:
            raise ValueError("门槛受影响报告集合只能来自门槛收紧覆盖")
        if not set(self.affected_report_kinds) <= set(self.rebuild_report_kinds):
            raise ValueError("门槛受影响报告必须纳入实际重建报告集合")
        if self.promoted and not self.rebuild_report_kinds:
            raise ValueError("晋级候选必须通过影响闭包定位到至少一类报告")
        if set(self.rebuild_report_kinds) & set(self.reuse_report_kinds):
            raise ValueError("同一报告不能同时受影响又按摘要复用")
        if self.gate_override is not None and not self.affected_report_kinds:
            raise ValueError("门槛收紧必须声明受影响报告集合")
        binding_kinds = [item.report_kind for item in self.gate_spec_bindings]
        if len(set(binding_kinds)) != len(binding_kinds):
            raise ValueError("同一报告只能绑定一份本轮门槛规则")
        if set(binding_kinds) != set(self.affected_report_kinds):
            raise ValueError("本轮门槛规则绑定必须完整覆盖门槛受影响报告")
        if self.gate_override is not None and "gate_tightening" not in self.change_kinds:
            raise ValueError("携带门槛覆盖的计划必须声明门槛收紧变化")
        if (
            "cutoff_expansion" in self.change_kinds
            and self.child_contract.data_cutoff == self.parent_contract.data_cutoff
        ):
            raise ValueError("截止日扩展必须实际扩大数据截止日")
        expected_digest = _payload_digest(self._digest_body())
        if self.plan_digest != expected_digest:
            raise ValueError("计划摘要与计划内容不一致")
        return self

    def _digest_body(self) -> dict[str, Any]:
        return {
            "refresh_id": self.refresh_id,
            "project_id": self.project_id,
            "parent_contract": self.parent_contract.model_dump(mode="json"),
            "child_contract": self.child_contract.model_dump(mode="json"),
            "change_kinds": list(self.change_kinds),
            "requested_cutoff": self.requested_cutoff.isoformat(),
            "promoted": [item.model_dump(mode="json") for item in self.promoted],
            "blocked": [item.model_dump(mode="json") for item in self.blocked],
            "gate_override": (
                self.gate_override.model_dump(mode="json")
                if self.gate_override is not None
                else None
            ),
            "gate_spec_bindings": [
                item.model_dump(mode="json") for item in self.gate_spec_bindings
            ],
            "affected_report_kinds": [kind.value for kind in self.affected_report_kinds],
            "rebuild_report_kinds": [kind.value for kind in self.rebuild_report_kinds],
            "reuse_report_kinds": [kind.value for kind in self.reuse_report_kinds],
            "affected_objects": [item.model_dump(mode="json") for item in self.affected_objects],
            "reuse_objects": [item.model_dump(mode="json") for item in self.reuse_objects],
            "change_records": [item.model_dump(mode="json") for item in self.change_records],
            "impact_plan_digest": self.impact_plan_digest,
        }


class RebuildAction(BaseModel):
    """一个受影响或复用对象的追加式重建回执。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    refresh_id: str
    action_id: str
    object_kind: str
    object_id: str
    disposition: Literal["rebuilt", "reuse"]
    basis_digest: str
    recorded_at: datetime
    actor_id: str

    @field_validator("refresh_id", "action_id", "object_id", "actor_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("object_kind")
    @classmethod
    def _kind_is_closed(cls, value: str) -> str:
        normalized = _not_blank(value)
        if normalized not in _OBJECT_KINDS:
            raise ValueError("重建对象种类必须是来源、事实、声明、页面或格式")
        return normalized

    @field_validator("basis_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        normalized = _not_blank(value)
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("重建依据摘要必须是小写 SHA-256")
        return normalized

    @field_validator("recorded_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class GateDecisionRecord(BaseModel):
    """受影响报告在本轮刷新中的门槛决定；阻断即失败关闭，不生成草稿。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    refresh_id: str
    report_kind: ReportKind
    decision: Literal["passed", "blocked"]
    result_key: str
    gate_result: ReportGateResult
    recorded_at: datetime
    actor_id: str

    @field_validator("refresh_id", "result_key", "actor_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("recorded_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _decision_matches_result(self) -> GateDecisionRecord:
        expected = "passed" if self.gate_result.decision is ReportDecision.PASSED else "blocked"
        if self.decision != expected or self.result_key != self.gate_result.result_key:
            raise ValueError("门槛登记必须完全来自已校验的报告级门槛结果")
        if self.report_kind is not self.gate_result.report_kind:
            raise ValueError("门槛登记的报告类型与报告级门槛结果不一致")
        return self


class RefreshQcRecord(BaseModel):
    """独立科学质控登记；结论绑定本轮报告快照与真实门槛结果。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    refresh_id: str
    report_kind: ReportKind
    report_snapshot_id: str
    review_bundle: ScientificQcReviewBundle
    verdict: ScientificQcVerdict

    @field_validator("refresh_id", "report_snapshot_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def _reviewer_is_independent(self) -> RefreshQcRecord:
        if self.verdict.reviewer_id == self.review_bundle.producer_id:
            raise ValueError("科学质控必须由不同于报告构建者的人员独立完成")
        if self.verdict.review_input_digest != self.review_bundle.input_digest:
            raise ValueError("科学质控结论必须绑定实际审查输入包")
        return self


class RefreshCompletion(BaseModel):
    """刷新接受登记：子版本已接受，父版本保持可读。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    refresh_id: str
    project_id: str
    child_contract_version: int
    evidence_snapshot_id: str | None
    report_snapshot_ids: tuple[str, ...] = ()
    accepted_at: datetime

    @field_validator("refresh_id", "project_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("accepted_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


# ── 服务 ─────────────────────────────────────────────────────────────────────


class RefreshService:
    """从最近已接受版本继续的增量刷新服务：plan / record / accept / resume。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.database_path = self.project_root / "state" / "project.sqlite"
        try:
            apply_migrations(self.database_path)
        except MigrationError as error:
            raise RefreshServiceError(f"项目数据库迁移无法执行：{error}") from error
        self.event_store = EventStore(self.project_root)
        self.snapshot_store = SnapshotStore(self.project_root)

    # ── 读取与恢复视图 ─────────────────────────────────────────────────────

    def _load_project_document(self) -> dict[str, Any]:
        path = self.project_root / "project.yaml"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise RefreshStateError("项目文件缺失或不是有效 JSON，无法确定已接受版本") from error
        if not isinstance(document, dict) or "active_contract_version" not in document:
            raise RefreshStateError("项目文件缺少当前合同版本，无法确定已接受版本")
        return document

    def parent_contract(self) -> ProjectContract:
        """最近已接受的合同版本；项目文件中的历史版本保持只读。"""
        document = self._load_project_document()
        versions = document.get("project_contract_versions")
        if not isinstance(versions, list) or not versions:
            raise RefreshStateError("项目文件没有可读取的合同版本")
        active = document["active_contract_version"]
        for payload in versions:
            if not isinstance(payload, dict):
                continue
            if payload.get("contract_version") != active:
                continue
            try:
                return ProjectContract.model_validate(payload)
            except ValueError as error:
                raise RefreshStateError(f"当前合同版本无法读取：{error}") from error
        raise RefreshStateError("项目指定的当前合同版本不存在")

    def load_plan(self, refresh_id: str) -> RefreshPlan:
        """从规范事件流重建刷新计划；事件是真源，可安全跨中断调用。"""
        for event in self.event_store.read_all():
            if event.event_type != _PLAN_EVENT or event.payload.get("refresh_id") != refresh_id:
                continue
            plan = RefreshPlan.model_validate(event.payload["plan"])
            if plan.refresh_id != refresh_id:
                raise RefreshStateError("刷新计划标识与事件内容不一致")
            return plan
        raise RefreshStateError(f"刷新计划不存在：{refresh_id}")

    def resume_status(self, refresh_id: str) -> dict[str, Any]:
        """中断恢复视图：计划、已记录动作、缺口与接受状态。"""
        plan = self.load_plan(refresh_id)
        actions = self._rebuild_actions(refresh_id)
        decisions = self._gate_decisions(refresh_id)
        snapshots = self._registered_snapshot_ids(refresh_id)
        qc_records = self._qc_records(refresh_id)
        required = {(item.object_kind, item.object_id) for item in plan.affected_objects}
        recorded = {(item.object_kind, item.object_id) for item in actions}
        return {
            "plan": plan,
            "recorded_actions": actions,
            "gate_decisions": decisions,
            "registered_report_snapshot_ids": snapshots,
            "scientific_qc_records": qc_records,
            "completion": self._accepted_completion(refresh_id),
            "missing_rebuild_objects": tuple(
                ImpactedObject(object_kind=kind, object_id=object_id)
                for kind, object_id in sorted(required - recorded)
            ),
            "pending_gate_report_kinds": tuple(
                sorted(
                    (kind for kind in plan.rebuild_report_kinds if kind not in decisions),
                    key=lambda kind: kind.value,
                )
            ),
            "pending_snapshot_report_kinds": tuple(
                sorted(
                    (kind for kind in plan.rebuild_report_kinds if kind not in snapshots),
                    key=lambda kind: kind.value,
                )
            ),
            "pending_scientific_qc_report_kinds": tuple(
                sorted(
                    (kind for kind in plan.rebuild_report_kinds if kind not in qc_records),
                    key=lambda kind: kind.value,
                )
            ),
        }

    def _user_fact_row(self, fact_version_id: str) -> dict[str, Any]:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT fact_version_id,fact_id,entity_id,field_id,raw_value,normalized_value,"
                "primary_fragment_id,supersedes_fact_version_id,scientific_context_json "
                "FROM fact_versions WHERE fact_version_id=?",
                (fact_version_id,),
            ).fetchone()
        if row is None:
            raise RefreshStateError("三方比较事实版本不存在")
        names = (
            "fact_version_id",
            "fact_id",
            "entity_id",
            "field_id",
            "raw_value",
            "normalized_value",
            "primary_fragment_id",
            "supersedes_fact_version_id",
            "scientific_context_json",
        )
        result = dict(zip(names, row, strict=True))
        try:
            context = json.loads(str(result["scientific_context_json"] or "{}"))
        except json.JSONDecodeError as error:
            raise RefreshStateError("三方比较事实语义无法读取") from error
        if not isinstance(context, dict):
            raise RefreshStateError("三方比较事实语义不是对象")
        context.pop("user_edit", None)
        context.update(
            {
                "raw_value": result["raw_value"],
                "normalized_value": result["normalized_value"],
                "entity_id": result["entity_id"],
                "field_id": result["field_id"],
                "primary_fragment_id": result["primary_fragment_id"],
            }
        )
        result["fields"] = context
        return result

    def _user_lineage(
        self,
        *,
        fact_id: str,
        base_fact_version_id: str,
        user_fact_version_id: str,
    ) -> tuple[str, ...]:
        lineage: list[str] = []
        current_id: str | None = user_fact_version_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id in visited:
                raise RefreshStateError("用户事实版本谱系存在环")
            visited.add(current_id)
            row = self._user_fact_row(current_id)
            if row["fact_id"] != fact_id:
                raise RefreshStateError("用户事实版本谱系跨越了事实身份")
            lineage.append(current_id)
            if current_id == base_fact_version_id:
                return tuple(lineage)
            parent = row["supersedes_fact_version_id"]
            current_id = None if parent is None else str(parent)
        raise RefreshStateError("用户事实版本不是指定base的后代")

    def _declared_user_fields(self, lineage: tuple[str, ...]) -> set[str]:
        user_versions = lineage[:-1]
        if not user_versions:
            return set()
        placeholders = ",".join("?" for _ in user_versions)
        with open_database(self.database_path) as database:
            rows = database.execute(
                "SELECT result_fact_version_id,command_json FROM user_fact_edit_requests "
                f"WHERE result_fact_version_id IN ({placeholders})",
                user_versions,
            ).fetchall()
        commands = {
            str(version_id): json.loads(str(command_json))
            for version_id, command_json in rows
        }
        if set(commands) != set(user_versions):
            raise RefreshStateError("用户事实谱系缺少对应的typed保存命令")
        declared: set[str] = set()
        for version_id in user_versions:
            command = commands[version_id]
            edits = command.get("edits")
            if not isinstance(edits, dict):
                raise RefreshStateError("用户事实谱系保存命令缺少typed edits")
            declared.update(key for key, value in edits.items() if value is not None)
        if declared & {"numerator", "denominator", "threshold_operator", "threshold_value"}:
            declared.update({"raw_value", "normalized_value"})
        return declared

    def compare_user_fact_refresh(
        self,
        *,
        fact_id: str,
        base_fact_version_id: str,
        user_fact_version_id: str,
        source_version_id: str,
        source_fields: dict[str, object],
        source_withdrawn: bool,
        request_id: str,
        compared_at: datetime,
        actor_id: str,
    ) -> RefreshConflictComparison:
        """Persist a complete typed base/user/new-source comparison for W07."""
        from ci_workflow.application.user_fact_edit import (
            RefreshConflictComparison,
            RefreshFieldComparison,
            RefreshFieldState,
        )

        occurred_at = _offset_datetime(compared_at)
        base = self._user_fact_row(base_fact_version_id)
        user = self._user_fact_row(user_fact_version_id)
        if base["fact_id"] != fact_id or user["fact_id"] != fact_id:
            raise RefreshStateError("三方比较事实身份不一致")
        lineage = self._user_lineage(
            fact_id=fact_id,
            base_fact_version_id=base_fact_version_id,
            user_fact_version_id=user_fact_version_id,
        )
        base_fields = dict(base["fields"])
        user_fields = dict(user["fields"])
        missing_user = sorted(set(base_fields) - set(user_fields))
        if missing_user:
            raise RefreshStateError(f"用户事实没有完整继承base字段：{missing_user}")
        declared_user_fields = self._declared_user_fields(lineage)
        undeclared_changes = sorted(
            field
            for field in set(base_fields) | set(user_fields)
            if base_fields.get(field) != user_fields.get(field)
            and field not in declared_user_fields
        )
        if undeclared_changes:
            raise RefreshStateError(
                f"用户事实存在未由typed命令声明的字段变化：{undeclared_changes}"
            )
        comparisons: dict[str, RefreshFieldComparison] = {}
        field_names = sorted(set(base_fields) | set(user_fields) | set(source_fields))
        for field in field_names:
            base_present = field in base_fields
            user_present = field in user_fields
            source_present = field in source_fields
            base_value = base_fields.get(field)
            user_value = user_fields.get(field)
            source_value = source_fields.get(field, base_value)
            user_changed = user_present != base_present or user_value != base_value
            source_changed = source_present and source_value != base_value
            if source_withdrawn:
                state = RefreshFieldState.SOURCE_WITHDRAWN
            elif user_changed and source_changed:
                state = (
                    RefreshFieldState.CONVERGED
                    if user_value == source_value
                    else RefreshFieldState.CONFLICT
                )
            elif user_changed:
                state = RefreshFieldState.USER_MODIFIED
            elif source_changed:
                state = RefreshFieldState.SOURCE_CHANGED
            else:
                state = RefreshFieldState.UNCHANGED
            requires = state in {
                RefreshFieldState.CONFLICT,
                RefreshFieldState.SOURCE_WITHDRAWN,
            }
            comparisons[field] = RefreshFieldComparison(
                field=field,
                base_value=base_value,
                user_value=user_value,
                source_value=None if source_withdrawn else source_value,
                base_present=base_present,
                user_present=user_present,
                source_present=source_present,
                source_inherited_from_base=not source_withdrawn and not source_present,
                state=state,
                source_version_id=source_version_id,
                resolution_required=requires,
                resolution_options=("keep_user", "accept_source", "manual") if requires else (),
            )
        states = {field: item.state for field, item in comparisons.items()}
        requires_explicit_resolution = any(
            item.resolution_required for item in comparisons.values()
        )
        conflict_id = stable_id(
            "user-refresh-conflict",
            request_id,
            fact_id,
            base_fact_version_id,
            user_fact_version_id,
            source_version_id,
            _payload_digest(source_fields),
            str(source_withdrawn),
        )
        comparison = RefreshConflictComparison(
            conflict_id=conflict_id,
            fact_id=fact_id,
            base_fact_version_id=base_fact_version_id,
            user_fact_version_id=user_fact_version_id,
            source_version_id=source_version_id,
            user_lineage=lineage,
            field_states=states,
            field_comparisons=comparisons,
            requires_explicit_resolution=requires_explicit_resolution,
        )
        comparison_json = comparison.model_dump_json()
        with open_database(self.database_path) as database:
            request_row = database.execute(
                "SELECT conflict_id,comparison_json FROM user_refresh_conflicts WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if request_row is not None and (
                str(request_row[0]) != conflict_id or str(request_row[1]) != comparison_json
            ):
                raise RefreshConflictError("同一刷新比较请求标识对应了不同内容")
            existing = database.execute(
                "SELECT comparison_json FROM user_refresh_conflicts WHERE conflict_id=?",
                (conflict_id,),
            ).fetchone()
            if existing is not None:
                if str(existing[0]) != comparison_json:
                    raise RefreshConflictError("同一三方比较身份对应了不同内容")
            else:
                database.execute(
                    "INSERT INTO user_refresh_conflicts (conflict_id,request_id,fact_id,"
                    "base_fact_version_id,user_fact_version_id,source_fields_json,field_states_json,"
                    "requires_explicit_resolution,created_at,source_version_id,base_fields_json,"
                    "user_fields_json,comparison_json,resolution_json) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        conflict_id,
                        request_id,
                        fact_id,
                        base_fact_version_id,
                        user_fact_version_id,
                        _canonical_json_text(source_fields),
                        _canonical_json_text({key: value.value for key, value in states.items()}),
                        int(requires_explicit_resolution),
                        occurred_at.isoformat(),
                        source_version_id,
                        _canonical_json_text(base_fields),
                        _canonical_json_text(user_fields),
                        comparison_json,
                        _canonical_json_text(
                            {
                                key: list(value.resolution_options)
                                for key, value in comparisons.items()
                                if value.resolution_required
                            }
                        ),
                    ),
                )
            project = database.execute(
                "SELECT project_id FROM project_contract_versions "
                "ORDER BY contract_version DESC LIMIT 1"
            ).fetchone()
        if project is None:
            raise RefreshStateError("项目合同不存在，无法持久化刷新比较事件")
        self._append_event(
            event_type=_USER_FACT_COMPARISON_EVENT,
            event_kind="user-fact-refresh-comparison",
            project_id=str(project[0]),
            actor_id=actor_id,
            occurred_at=occurred_at,
            payload={"comparison": comparison.model_dump(mode="json")},
            idempotency_key=f"refresh.user_fact.compare:{request_id}",
        )
        return comparison

    # ── 幂等账本 ───────────────────────────────────────────────────────────

    def _claim(self, *, key: str, operation: str, result: dict[str, Any]) -> bool:
        """登记操作结果；返回 True 表示首次登记，False 表示精确重放。"""
        result_digest = _payload_digest(result)
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT operation, result_digest FROM idempotency_keys WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                if str(row[0]) != operation or str(row[1]) != result_digest:
                    raise RefreshConflictError(f"同一幂等键对应了不同刷新输入：{key}")
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

    def _recorded_digest(self, key: str) -> str | None:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT result_digest FROM idempotency_keys WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
        return None if row is None else str(row[0])

    # ── 事件 ───────────────────────────────────────────────────────────────

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
    ) -> None:
        event_identity = str(payload.get("refresh_id") or "")
        if not event_identity:
            comparison = payload.get("comparison")
            if isinstance(comparison, dict):
                event_identity = str(comparison.get("conflict_id") or "")
        if not event_identity:
            event_identity = idempotency_key
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(
                event_kind,
                project_id,
                _RUN_ID,
                event_identity,
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

    # ── 操作 1：plan_refresh ───────────────────────────────────────────────

    def plan_refresh(
        self,
        *,
        requested_cutoff: str | datetime | None = None,
        requested_at: datetime,
        actor_id: str,
        requested_contract: ProjectContract | None = None,
        evidence_contract_version: str = _EVIDENCE_CONTRACT_VERSION,
        gate_specs: dict[ReportKind, tuple[GateSpec, GateSpec]] | None = None,
        declared_affected_report_kinds: tuple[ReportKind, ...] | None = None,
        child_baseline: RefreshBaselineIdentity | None = None,
        impact_edges: tuple[ImpactEdge, ...] = (),
        impact_nodes: tuple[ImpactNode, ...] = (),
        sources: tuple[SourceVersionRecord, ...] = (),
        declared_change_records: tuple[ObjectChangeRecord, ...] = (),
    ) -> RefreshPlan:
        """制定增量刷新计划：父版本绑定、截止日扩展、候选晋级、门槛收紧。

        同一输入精确重放返回同一计划与同一子合同版本；同一计划标识对应不同
        输入失败关闭。重大合同变化不做局部刷新，明确要求重新建立基线。
        """
        occurred_at = _offset_datetime(requested_at)
        parent = self.parent_contract()

        # 1. 重大合同变化分类：基线身份三维任一变化必须再基线（图定义分支）。
        self._assert_incremental_scope(
            parent,
            evidence_contract_version=evidence_contract_version,
            child_baseline=child_baseline,
            requested_contract=requested_contract,
        )

        # 2. 父版本绑定：追加紧邻子合同版本；父行不改写。
        cutoff_expansion = requested_cutoff is not None
        child = self._derive_child_contract(
            parent,
            requested_cutoff=requested_cutoff,
            occurred_at=occurred_at,
        )

        # 3. 候选晋级：仅截止日扩展时按 first_disclosed_at 重新评估候选。
        promoted: tuple[CandidatePromotion, ...] = ()
        blocked: tuple[BlockedCandidate, ...] = ()
        if cutoff_expansion:
            promoted, blocked = self._evaluate_candidates(
                parent=parent, child=child, sources=sources
            )

        # 4. 门槛收紧：复用 gates.coverage 的只收紧偏序与受影响报告计算。
        gate_override, gate_spec_bindings, affected_kinds, reuse_kinds = self._tighten_gates(
            parent=parent,
            child=child,
            gate_specs=gate_specs,
            declared_affected_report_kinds=declared_affected_report_kinds,
            occurred_at=occurred_at,
        )

        change_kinds: list[str] = []
        if cutoff_expansion:
            change_kinds.append("cutoff_expansion")
        if gate_override is not None:
            change_kinds.append("gate_tightening")
        if not change_kinds:
            raise RefreshStateError("刷新请求没有可执行的增量变化：截止日未扩大，门槛也未收紧")

        # 5. 影响闭包：截止日扩展以晋级候选为种子；门槛收紧以受影响报告页面
        #    为种子；传播与复用集合全部由影响图推导，本服务不复制传播规则。
        (
            affected_objects,
            reuse_objects,
            impact_report_kinds,
            impact_plan_digest,
        ) = self._impact_sets(
            promoted_seed_ids=[item.source_version_id for item in promoted],
            affected_report_kinds=affected_kinds,
            impact_edges=impact_edges,
            impact_nodes=impact_nodes,
        )

        plan = self._build_plan(
            parent=parent,
            child=child,
            change_kinds=tuple(change_kinds),
            requested_cutoff=child.data_cutoff,
            occurred_at=occurred_at,
            promoted=promoted,
            blocked=blocked,
            gate_override=gate_override,
            affected_kinds=affected_kinds,
            reuse_kinds=reuse_kinds,
            affected_objects=affected_objects,
            reuse_objects=reuse_objects,
            declared_change_records=declared_change_records,
            gate_spec_bindings=gate_spec_bindings,
            impact_report_kinds=impact_report_kinds,
            impact_plan_digest=impact_plan_digest,
        )

        # 6. 幂等登记：同键同结果视为重放；同键不同输入失败关闭。
        claim_key = f"refresh.plan:{plan.refresh_id}"
        result = {"plan_digest": plan.plan_digest}
        existing = self._recorded_digest(claim_key)
        if existing is not None:
            if existing != _payload_digest(result):
                raise RefreshConflictError("同一刷新计划对应了不同输入，必须失败关闭")
            return plan
        self._assert_no_parallel_plan(plan)
        self._append_child_contract(child)
        self._record_candidates(plan, occurred_at=occurred_at, actor_id=actor_id)
        self._append_event(
            event_type=_PLAN_EVENT,
            event_kind="refresh-plan",
            project_id=plan.project_id,
            actor_id=actor_id,
            occurred_at=occurred_at,
            payload={"refresh_id": plan.refresh_id, "plan": plan.model_dump(mode="json")},
            idempotency_key=f"refresh.plan.created:{plan.refresh_id}",
        )
        self._claim(key=claim_key, operation="refresh.plan", result=result)
        return plan

    def _assert_no_parallel_plan(self, plan: RefreshPlan) -> None:
        """同一父版本只允许一个未完成计划占用紧邻子版本。"""
        for event in self.event_store.read_all():
            if event.event_type != _PLAN_EVENT:
                continue
            other = RefreshPlan.model_validate(event.payload["plan"])
            if other.refresh_id == plan.refresh_id:
                continue
            same_version_edge = (
                other.project_id == plan.project_id
                and other.parent_contract.contract_version == plan.parent_contract.contract_version
                and other.child_contract.contract_version == plan.child_contract.contract_version
            )
            if same_version_edge and self._accepted_completion(other.refresh_id) is None:
                raise RefreshConflictError("同一父版本已有未完成刷新计划，请先恢复或结束该计划")

    def _assert_incremental_scope(
        self,
        parent: ProjectContract,
        *,
        evidence_contract_version: str,
        child_baseline: RefreshBaselineIdentity | None,
        requested_contract: ProjectContract | None,
    ) -> None:
        """重大合同变化只识别、明确要求再基线；分支裁定复用图定义合同。"""
        parent_baseline = RefreshBaselineIdentity(
            contract_schema_version=parent.schema_version,
            ontology_version=_PARENT_BASELINE_ONTOLOGY_VERSION,
            evidence_contract_version=evidence_contract_version,
        )
        decision = classify_refresh_branch(parent_baseline, child_baseline or parent_baseline)
        if decision.branch == "rebaseline_required":
            dimensions = "、".join(decision.changed_dimensions)
            raise RefreshRebaselineRequired(
                f"{REBASELINE_REQUIRED_MESSAGE_ZH}（变化维度：{dimensions}）"
            )
        if requested_contract is None:
            return
        if requested_contract.project_id != parent.project_id:
            raise RefreshRebaselineRequired("刷新请求属于其他项目身份，需要重新建立基线。")
        drifted = [
            field
            for field in ("indication", "reports", "outputs", "timezone")
            if getattr(requested_contract, field) != getattr(parent, field)
        ]
        if drifted:
            names = "、".join(drifted)
            raise RefreshRebaselineRequired(
                f"项目合同字段 {names} 发生重大变化，增量刷新不适用，需要重新建立基线。"
            )

    def _derive_child_contract(
        self,
        parent: ProjectContract,
        *,
        requested_cutoff: str | datetime | None,
        occurred_at: datetime,
    ) -> ProjectContract:
        if requested_cutoff is None:
            try:
                return ProjectContract(
                    schema_version=parent.schema_version,
                    contract_version=parent.contract_version + 1,
                    project_id=parent.project_id,
                    indication=parent.indication,
                    reports=parent.reports,
                    outputs=parent.outputs,
                    timezone=parent.timezone,
                    data_cutoff=parent.data_cutoff,
                    cutoff_was_user_supplied=parent.cutoff_was_user_supplied,
                    created_at=occurred_at.astimezone(ZoneInfo(parent.timezone)),
                )
            except ValueError as error:
                raise RefreshStateError(f"门槛收紧子合同无法生成：{error}") from error
        try:
            return refresh_project_contract(parent, cutoff=requested_cutoff, created_at=occurred_at)
        except ValueError as error:
            raise RefreshStateError(str(error)) from error

    def _append_child_contract(self, child: ProjectContract) -> None:
        """追加子合同版本行；同一版本同一内容幂等，不同内容失败关闭。"""
        try:
            persist_project_contract(self.database_path, child)
        except MigrationError as error:
            raise RefreshStateError(
                "子合同版本无法追加（可能存在未完成的其他刷新，请先恢复该刷新"
                "或重新建立基线）：" + str(error)
            ) from error

    # ── 候选晋级 ───────────────────────────────────────────────────────────

    def _evaluate_candidates(
        self,
        *,
        parent: ProjectContract,
        child: ProjectContract,
        sources: tuple[SourceVersionRecord, ...],
    ) -> tuple[tuple[CandidatePromotion, ...], tuple[BlockedCandidate, ...]]:
        """按 first_disclosed_at（而非获取时间）重新评估候选；只晋级新适格者。"""
        promoted: list[CandidatePromotion] = []
        blocked: list[BlockedCandidate] = []
        seen: set[str] = set()
        for source in self._iter_candidates(sources):
            if source.source_version_id in seen:
                raise RefreshStateError(f"候选来源重复：{source.source_version_id}")
            seen.add(source.source_version_id)
            parent_state = assess_historical_source(
                source, cutoff=parent.data_cutoff, key_evidence=True
            )
            if parent_state.can_enter_snapshot:
                # 父截止日下已适格且未变化的来源已在父快照中，不重评。
                continue
            new_state = assess_historical_source(
                source, cutoff=child.data_cutoff, key_evidence=True
            )
            if new_state.can_enter_snapshot:
                disclosed = source.first_disclosed_at.value
                if disclosed is None:
                    raise RefreshStateError("适格候选缺少首次披露时间，必须失败关闭")
                promoted.append(
                    CandidatePromotion(
                        source_version_id=source.source_version_id,
                        source_id=source.source_id,
                        first_disclosed_at=disclosed,
                        rationale_zh=new_state.rationale_zh,
                    )
                )
            else:
                blocked.append(
                    BlockedCandidate(
                        source_version_id=source.source_version_id,
                        source_id=source.source_id,
                        reason_code=new_state.state.value,
                        rationale_zh=new_state.rationale_zh,
                    )
                )
        return (
            tuple(sorted(promoted, key=lambda item: item.source_version_id)),
            tuple(sorted(blocked, key=lambda item: item.source_version_id)),
        )

    def _iter_candidates(
        self, sources: tuple[SourceVersionRecord, ...]
    ) -> tuple[SourceVersionRecord, ...]:
        """合并调用方来源与项目库中已登记来源；数据库行重建为不可变记录。"""
        merged = {record.source_version_id: record for record in sources}
        with open_database(self.database_path) as database:
            rows = database.execute(
                """
                SELECT sv.source_version_id, sv.source_id, sv.content_sha256,
                       cb.relative_path, cb.media_type, sv.acquired_at, sv.created_at
                FROM source_versions sv
                LEFT JOIN content_blobs cb ON cb.content_sha256 = sv.content_sha256
                """
            ).fetchall()
            assertions: dict[str, dict[str, dict[str, Any]]] = {}
            for row in database.execute(
                """
                SELECT source_version_id, date_role, disclosure_state, observed_at,
                       date_precision, locator_json
                FROM source_date_assertions
                """
            ).fetchall():
                assertions.setdefault(str(row[0]), {})[str(row[1])] = {
                    "disclosure_state": str(row[2]),
                    "observed_at": row[3],
                    "date_precision": str(row[4]),
                    "locator_json": str(row[5]),
                }
        for row in rows:
            (
                source_version_id,
                source_id,
                content_sha256,
                relative_path,
                media_type,
                acquired_at,
                created_at,
            ) = row
            source_version_id = str(source_version_id)
            if source_version_id in merged:
                continue
            if relative_path is None or media_type is None:
                raise RefreshStateError(
                    f"来源版本缺少已登记正文对象，无法评估刷新候选：{source_version_id}"
                )
            roles = assertions.get(source_version_id, {})
            missing = [role for role in _DATE_ROLES if role not in roles]
            if missing:
                raise RefreshStateError(
                    f"来源版本缺少日期断言，无法评估刷新候选：{source_version_id}"
                )
            try:
                record = SourceVersionRecord(
                    schema_version="1.0",
                    source_version_id=source_version_id,
                    source_id=str(source_id),
                    content_sha256=str(content_sha256),
                    content_relative_path=str(relative_path),
                    media_type=str(media_type),
                    acquired_at=datetime.fromisoformat(str(acquired_at)),
                    acquired_locator=self._date_evidence(roles["acquired_at"]).locator,
                    published_at=self._date_evidence(roles["published_at"]),
                    effective_at=self._date_evidence(roles["effective_at"]),
                    first_disclosed_at=self._date_evidence(roles["first_disclosed_at"]),
                    created_at=datetime.fromisoformat(str(created_at)),
                )
            except ValueError as error:
                raise RefreshStateError(
                    f"来源版本无法重建为不可变记录：{source_version_id}：{error}"
                ) from error
            merged[source_version_id] = record
        return tuple(merged.values())

    @staticmethod
    def _date_evidence(assertion: dict[str, Any]) -> DateEvidence:
        observed = assertion["observed_at"]
        return DateEvidence(
            state=assertion["disclosure_state"],
            value=datetime.fromisoformat(observed) if observed else None,
            precision=assertion["date_precision"],
            locator=EvidenceLocator.model_validate_json(assertion["locator_json"]),
        )

    def _record_candidates(
        self, plan: RefreshPlan, *, occurred_at: datetime, actor_id: str
    ) -> None:
        """把晋级与阻断候选追加登记到 refresh_candidates 审计表（幂等）。"""
        rows: list[tuple[str, str, str, str | None, str]] = []
        for promotion in plan.promoted:
            rows.append(
                (
                    stable_id("refresh-candidate", plan.refresh_id, promotion.source_version_id),
                    promotion.source_id,
                    _canonical_json_text({"source_version_id": promotion.source_version_id}),
                    promotion.first_disclosed_at.isoformat(),
                    f"promoted:{promotion.rationale_zh}",
                )
            )
        for candidate in plan.blocked:
            rows.append(
                (
                    stable_id("refresh-candidate", plan.refresh_id, candidate.source_version_id),
                    candidate.source_id,
                    _canonical_json_text({"source_version_id": candidate.source_version_id}),
                    None,
                    f"blocked:{candidate.reason_code}:{candidate.rationale_zh}",
                )
            )
        if not rows:
            return
        with open_database(self.database_path) as database:
            for candidate_id, source_id, locator, disclosed, reason in rows:
                database.execute(
                    """
                    INSERT OR IGNORE INTO refresh_candidates (
                        candidate_id, source_id, candidate_locator,
                        first_disclosed_at, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candidate_id,
                        source_id,
                        locator,
                        disclosed,
                        reason,
                        occurred_at.isoformat(),
                    ),
                )
        if plan.promoted:
            self._append_event(
                event_type=_PROMOTION_EVENT,
                event_kind="refresh-promotion",
                project_id=plan.project_id,
                actor_id=actor_id,
                occurred_at=occurred_at,
                payload={
                    "refresh_id": plan.refresh_id,
                    "promoted": [item.model_dump(mode="json") for item in plan.promoted],
                    "blocked": [item.model_dump(mode="json") for item in plan.blocked],
                },
                idempotency_key=f"refresh.candidates:{plan.refresh_id}",
            )

    # ── 门槛收紧 ───────────────────────────────────────────────────────────

    def _tighten_gates(
        self,
        *,
        parent: ProjectContract,
        child: ProjectContract,
        gate_specs: dict[ReportKind, tuple[GateSpec, GateSpec]] | None,
        declared_affected_report_kinds: tuple[ReportKind, ...] | None,
        occurred_at: datetime,
    ) -> tuple[
        GateOverride | None,
        tuple[GateSpecBinding, ...],
        tuple[ReportKind, ...],
        tuple[ReportKind, ...],
    ]:
        """复用 gates.coverage：只收紧偏序、变化单元与受影响报告全部由其计算。"""
        if gate_specs is None:
            if declared_affected_report_kinds:
                raise RefreshStateError("声明了受影响报告但没有提供门槛覆盖材料")
            return None, (), (), ()
        for kind, (parent_spec, child_spec) in gate_specs.items():
            if parent_spec.report_kind is not kind or child_spec.report_kind is not kind:
                raise RefreshStateError(f"门槛规格的报告类型与映射键不一致：{kind.value}")
        versions = {parent_spec.version for parent_spec, _ in gate_specs.values()}
        if len(versions) != 1:
            raise RefreshStateError("全部报告的父规格必须共享同一基础规则版本")
        for parent_spec, child_spec in gate_specs.values():
            if child_spec.version != parent_spec.version:
                raise RefreshStateError("子规格必须保持基础规则版本，覆盖只改变项目合同版本")
            violations = validate_spec_override(parent_spec, child_spec)
            if violations:
                raise RefreshStateError(
                    "门槛覆盖只能收紧，未通过只收紧校验：" + "；".join(violations)
                )
        changed_units: list[str] = []
        affected_kinds: set[ReportKind] = set()
        for kind, (parent_spec, child_spec) in gate_specs.items():
            kind_changed = compute_changed_unit_ids(parent_spec, child_spec)
            changed_units.extend(kind_changed)
            if kind_changed:
                affected_kinds.add(kind)
        computed_affected = compute_affected_report_kinds(
            changed_units, {kind: child for kind, (_, child) in gate_specs.items()}
        )
        if set(computed_affected) != affected_kinds:
            raise RefreshStateError("受影响报告的反向依赖计算与变化单元归属不一致")
        if declared_affected_report_kinds is not None and set(
            declared_affected_report_kinds
        ) != set(computed_affected):
            raise RefreshStateError("调用方声明的受影响报告集合与确定性计算不一致，必须失败关闭")
        if not changed_units:
            raise RefreshStateError("门槛覆盖没有任何单元变化，不构成增量刷新")
        override = GateOverride(
            schema_version="1.0",
            override_id=stable_id(
                "gate-override",
                parent.project_id,
                str(child.contract_version),
                _payload_digest(
                    {
                        kind.value: {
                            "parent": parent_spec.spec_fingerprint,
                            "child": child_spec.spec_fingerprint,
                        }
                        for kind, (parent_spec, child_spec) in sorted(
                            gate_specs.items(), key=lambda item: item[0].value
                        )
                    }
                ),
            ),
            base_spec_version=next(iter(gate_specs.values()))[0].version,
            parent_contract_version=str(parent.contract_version),
            child_contract_version=str(child.contract_version),
            change_summary_zh="项目证据门槛收紧：只重算受影响报告，其他报告按摘要复用。",
            changed_unit_ids=tuple(sorted(set(changed_units))),
            affected_report_kinds=computed_affected,
            created_at=occurred_at,
        )
        residual = validate_override_declaration(override, specs_by_report_kind=gate_specs)
        if residual:
            raise RefreshStateError("门槛收紧声明与计算不一致：" + "；".join(residual))
        reuse_kinds = tuple(
            sorted(set(parent.reports) - set(computed_affected), key=lambda kind: kind.value)
        )
        bindings = tuple(
            GateSpecBinding(
                report_kind=kind,
                spec_version=gate_specs[kind][1].version,
                spec_fingerprint=gate_specs[kind][1].spec_fingerprint,
            )
            for kind in sorted(computed_affected, key=lambda item: item.value)
        )
        return override, bindings, computed_affected, reuse_kinds

    # ── 影响闭包 ───────────────────────────────────────────────────────────

    def _impact_sets(
        self,
        *,
        promoted_seed_ids: Sequence[str],
        affected_report_kinds: tuple[ReportKind, ...],
        impact_edges: tuple[ImpactEdge, ...],
        impact_nodes: tuple[ImpactNode, ...],
    ) -> tuple[
        tuple[ImpactedObject, ...],
        tuple[ImpactedObject, ...],
        tuple[ReportKind, ...],
        str | None,
    ]:
        """调用影响图得到受影响集合、复用集合与计划摘要；不复制传播规则。

        截止日扩展以晋级候选（来源层）为种子；门槛收紧以受影响报告登记的
        页面为种子（``impact_for_report_kinds``，报告集合来自 gates.coverage
        的确定性计算）。两类种子同时存在时合并进同一闭包。
        """
        seed_nodes = [
            ImpactNode(layer=ImpactLayer.SOURCE, object_id=object_id)
            for object_id in promoted_seed_ids
        ]
        if not seed_nodes and not affected_report_kinds:
            return (), (), (), None
        registered: dict[tuple[str, str], ImpactNode] = {
            (node.layer.value, node.object_id): node for node in impact_nodes
        }
        for node in (*seed_nodes, *_edge_endpoints(impact_edges)):
            registered.setdefault((node.layer.value, node.object_id), node)
        graph = ImpactGraph(nodes=tuple(registered.values()), edges=impact_edges)
        page_seeds: tuple[ImpactNode, ...] = ()
        if affected_report_kinds:
            page_plan = graph.impact_for_report_kinds(
                tuple(kind.value for kind in affected_report_kinds)
            )
            page_seeds = page_plan.seeds
        closure = graph.impact_closure((*seed_nodes, *page_seeds))
        report_kinds = tuple(
            sorted(
                {
                    ReportKind(kind)
                    for node in closure.affected
                    if node.layer is ImpactLayer.PAGE
                    for kind in node.report_kinds
                },
                key=lambda kind: kind.value,
            )
        )
        return (
            self._project_nodes(closure.affected),
            self._project_nodes(closure.reused),
            report_kinds,
            closure.plan_digest,
        )

    @staticmethod
    def _project_nodes(nodes: tuple[ImpactNode, ...]) -> tuple[ImpactedObject, ...]:
        projected: list[ImpactedObject] = []
        for node in nodes:
            try:
                projected.append(
                    ImpactedObject(object_kind=node.layer.value, object_id=node.object_id)
                )
            except ValueError as error:
                raise RefreshStateError(
                    "影响对象不符合首版站点式 HTML 合同："
                    f"{node.layer.value}/{node.object_id}：{error}"
                ) from error
        return tuple(projected)

    # ── 操作 2：record_rebuild_action ──────────────────────────────────────

    def record_rebuild_action(
        self,
        refresh_id: str,
        *,
        object_kind: str,
        object_id: str,
        disposition: Literal["rebuilt", "reuse"],
        basis_digest: str,
        recorded_at: datetime,
        actor_id: str,
    ) -> RebuildAction:
        """记录一个对象的重建或复用回执；追加式，跨中断幂等。"""
        plan = self.load_plan(refresh_id)
        object_kind = _not_blank(object_kind)
        if object_kind not in _OBJECT_KINDS:
            raise RefreshStateError("重建对象种类必须是来源、事实、声明、页面或格式")
        if object_kind == "format" and object_id not in _SUPPORTED_FORMATS:
            raise RefreshStateError("首版只处理站点式 HTML，其他格式不做局部重建")
        object_id = _not_blank(object_id)
        pair = (object_kind, object_id)
        declared_affected = {(item.object_kind, item.object_id) for item in plan.affected_objects}
        declared_reuse = {(item.object_kind, item.object_id) for item in plan.reuse_objects}
        if pair in declared_affected and disposition != "rebuilt":
            raise RefreshStateError("受影响对象必须重建，不能按摘要复用")
        if pair in declared_reuse and disposition != "reuse":
            raise RefreshStateError("复用对象不允许重建，按父版本摘要复用")
        if pair not in declared_affected and pair not in declared_reuse:
            raise RefreshStateError("重建对象不在刷新计划的影响或复用集合内")
        occurred_at = _offset_datetime(recorded_at)
        action = RebuildAction(
            schema_version="1.0",
            refresh_id=refresh_id,
            action_id=stable_id(
                "refresh-rebuild",
                refresh_id,
                object_kind,
                object_id,
                disposition,
                _not_blank(basis_digest),
            ),
            object_kind=object_kind,
            object_id=object_id,
            disposition=disposition,
            basis_digest=_not_blank(basis_digest),
            recorded_at=occurred_at,
            actor_id=_not_blank(actor_id),
        )
        existing = {item.action_id: item for item in self._rebuild_actions(refresh_id)}
        previous = existing.get(action.action_id)
        if previous is not None:
            if previous != action:
                raise RefreshConflictError("同一重建动作标识对应了不同内容")
            return previous
        self._append_event(
            event_type=_REBUILD_EVENT,
            event_kind="refresh-rebuild",
            project_id=plan.project_id,
            actor_id=action.actor_id,
            occurred_at=occurred_at,
            payload={"refresh_id": refresh_id, "action": action.model_dump(mode="json")},
            idempotency_key=f"refresh.rebuild:{action.action_id}",
        )
        self._append_receipt(action)
        return action

    def _receipt_path(self) -> Path:
        return self.project_root / "receipts" / "refresh_receipts.jsonl"

    def _append_receipt(self, action: RebuildAction) -> None:
        """追加重建回执 JSONL（投影）；事件流是真源，缺失行可由事件重放补齐。"""
        path = self._receipt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_ids: set[str] = set()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    existing_ids.add(str(json.loads(line).get("action_id")))
        if action.action_id in existing_ids:
            return
        encoded = _canonical_json_text(action.model_dump(mode="json")) + "\n"
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        try:
            os.write(descriptor, encoded.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _rebuild_actions(self, refresh_id: str) -> tuple[RebuildAction, ...]:
        """从事件流重建全部重建回执，并自愈缺失的 JSONL 投影行。"""
        actions: dict[str, RebuildAction] = {}
        for event in self.event_store.read_all():
            if event.event_type != _REBUILD_EVENT:
                continue
            if event.payload.get("refresh_id") != refresh_id:
                continue
            action = RebuildAction.model_validate(event.payload["action"])
            existing = actions.get(action.action_id)
            if existing is not None and existing != action:
                raise RefreshConflictError("同一重建动作标识对应了不同内容")
            actions[action.action_id] = action
        ordered = tuple(sorted(actions.values(), key=lambda item: item.action_id))
        recorded_ids: set[str] = set()
        path = self._receipt_path()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    recorded_ids.add(str(json.loads(line).get("action_id")))
        for action in ordered:
            if action.action_id not in recorded_ids:
                self._append_receipt(action)
        return ordered

    # ── 操作 3：record_gate_decision ───────────────────────────────────────

    def record_gate_decision(
        self,
        refresh_id: str,
        *,
        gate_result: ReportGateResult,
        recorded_at: datetime,
        actor_id: str,
    ) -> GateDecisionRecord:
        """登记真实报告级门槛结果；调用方不能用字符串自行宣称通过。"""
        plan = self.load_plan(refresh_id)
        validated = ReportGateResult.model_validate(gate_result.model_dump(mode="json"))
        report_kind = validated.report_kind
        if report_kind not in plan.rebuild_report_kinds:
            raise RefreshStateError("只有影响闭包确定需要重建的报告才能登记门槛结果")
        if validated.contract_version != str(plan.child_contract.contract_version):
            raise RefreshStateError("门槛结果必须绑定本轮刷新子合同版本")
        binding = next(
            (item for item in plan.gate_spec_bindings if item.report_kind is report_kind),
            None,
        )
        if binding is not None and (
            validated.spec_version != binding.spec_version
            or validated.spec_fingerprint != binding.spec_fingerprint
        ):
            raise RefreshStateError("门槛结果没有使用本轮收紧后的规则版本与内容指纹")
        record = GateDecisionRecord(
            refresh_id=refresh_id,
            report_kind=report_kind,
            decision=("passed" if validated.decision is ReportDecision.PASSED else "blocked"),
            result_key=validated.result_key,
            gate_result=validated,
            recorded_at=_offset_datetime(recorded_at),
            actor_id=_not_blank(actor_id),
        )
        previous = self._gate_decisions(refresh_id).get(report_kind)
        if previous is not None:
            if previous != record:
                raise RefreshConflictError("同一受影响报告登记了不同门槛决定")
            return previous
        self._append_event(
            event_type=_GATE_DECISION_EVENT,
            event_kind="refresh-gate-decision",
            project_id=plan.project_id,
            actor_id=record.actor_id,
            occurred_at=record.recorded_at,
            payload={
                "refresh_id": refresh_id,
                "decision": record.model_dump(mode="json"),
            },
            idempotency_key=f"refresh.gate.decision:{refresh_id}:{report_kind.value}",
        )
        return record

    def _gate_decisions(self, refresh_id: str) -> dict[ReportKind, GateDecisionRecord]:
        decisions: dict[ReportKind, GateDecisionRecord] = {}
        for event in self.event_store.read_all():
            if event.event_type != _GATE_DECISION_EVENT:
                continue
            if event.payload.get("refresh_id") != refresh_id:
                continue
            record = GateDecisionRecord.model_validate(event.payload["decision"])
            existing = decisions.get(record.report_kind)
            if existing is not None and existing != record:
                raise RefreshConflictError("同一受影响报告登记了不同门槛决定")
            decisions[record.report_kind] = record
        return decisions

    # ── 操作 4：record_scientific_qc ─────────────────────────────────────

    def record_scientific_qc(
        self,
        refresh_id: str,
        *,
        verdict: ScientificQcVerdict,
        review_bundle: ScientificQcReviewBundle,
    ) -> RefreshQcRecord:
        """登记独立科学质控结论，并绑定当前报告快照、门槛结果与构建者身份。"""
        plan = self.load_plan(refresh_id)
        validated = ScientificQcVerdict.model_validate(
            verdict.model_dump(mode="json", exclude={"verdict_digest"})
        )
        violations = check_scientific_qc_verdict_semantics(
            validated.model_dump(mode="json", exclude={"verdict_digest"})
        )
        if violations:
            raise RefreshStateError("科学质控结论语义不完整：" + "；".join(violations))
        bundle = ScientificQcReviewBundle.model_validate(
            review_bundle.model_dump(mode="json", exclude={"input_digest"})
        )
        bundle_violations = check_scientific_qc_review_bundle_semantics(
            bundle.model_dump(mode="json", exclude={"input_digest"})
        )
        if bundle_violations:
            raise RefreshStateError("科学质控审查输入不完整：" + "；".join(bundle_violations))
        report_kind = validated.report_kind
        if report_kind not in plan.rebuild_report_kinds:
            raise RefreshStateError("未受影响报告不得登记本轮科学质控结论")
        if validated.project_id != plan.project_id:
            raise RefreshStateError("科学质控结论与刷新项目不一致")
        if validated.contract_version != str(plan.child_contract.contract_version):
            raise RefreshStateError("科学质控结论必须绑定本轮刷新子合同版本")
        registered = self._registered_snapshot_ids(refresh_id)
        snapshot_id = registered.get(report_kind)
        if snapshot_id is None:
            raise RefreshStateError("报告快照尚未登记，不能接受科学质控结论")
        manifest = self._registered_report_manifest(snapshot_id)
        if validated.candidate_snapshot_id != snapshot_id:
            raise RefreshStateError("科学质控结论未绑定本轮登记的报告快照")
        if validated.report_version != str(manifest["report_version"]):
            raise RefreshStateError("科学质控结论与报告版本不一致")
        if validated.report_object_id != snapshot_id:
            raise RefreshStateError("科学质控报告对象必须绑定本轮报告快照标识")
        if validated.candidate_content_digest != _payload_digest(manifest):
            raise RefreshStateError("科学质控结论与报告快照内容摘要不一致")
        decision = self._gate_decisions(refresh_id).get(report_kind)
        if decision is None or validated.gate_result_key != decision.result_key:
            raise RefreshStateError("科学质控结论未绑定本轮真实门槛结果")
        if str(manifest["evidence_snapshot_id"]) != decision.gate_result.evidence_snapshot_id:
            raise RefreshStateError("报告快照与门槛结果没有绑定同一份证据快照")
        evidence_manifest = self._locked_evidence_manifest(
            decision.gate_result.evidence_snapshot_id
        )
        allowed_sources = set(evidence_manifest["source_version_ids"])
        allowed_fragments = set(evidence_manifest["fragment_ids"])
        allowed_facts = set(evidence_manifest["fact_version_ids"])
        allowed_claims = set(manifest["claim_ids"])
        for source_ref in bundle.source_refs:
            if source_ref.source_version_id not in allowed_sources:
                raise RefreshStateError("科学质控引用了本轮证据快照之外的来源")
            if not set(source_ref.fragment_ids) <= allowed_fragments:
                raise RefreshStateError("科学质控引用了本轮证据快照之外的证据片段")
            if not set(source_ref.fact_version_ids) <= allowed_facts:
                raise RefreshStateError("科学质控引用了本轮证据快照之外的事实")
            if not set(source_ref.claim_ids) <= allowed_claims:
                raise RefreshStateError("科学质控引用了本轮报告快照之外的声明")
        bundle_pairs = (
            (bundle.project_id, validated.project_id),
            (bundle.report_kind, validated.report_kind),
            (bundle.report_version, validated.report_version),
            (bundle.report_object_id, validated.report_object_id),
            (bundle.candidate_snapshot_id, validated.candidate_snapshot_id),
            (bundle.candidate_content_digest, validated.candidate_content_digest),
            (bundle.criteria_version, validated.criteria_version),
            (bundle.gate_result_key, validated.gate_result_key),
            (bundle.coverage_set_id, validated.coverage_set_id),
            (bundle.coverage_digest, validated.coverage_digest),
            (bundle.source_refs, validated.source_refs),
            (bundle.locators, validated.locators),
        )
        if any(left != right for left, right in bundle_pairs):
            raise RefreshStateError("科学质控结论与实际审查输入包不一致")
        if validated.review_input_digest != bundle.input_digest:
            raise RefreshStateError("科学质控结论没有绑定实际审查输入包摘要")
        record = RefreshQcRecord(
            refresh_id=refresh_id,
            report_kind=report_kind,
            report_snapshot_id=snapshot_id,
            review_bundle=bundle,
            verdict=validated,
        )
        previous = self._qc_records(refresh_id).get(report_kind)
        if previous is not None:
            if previous != record:
                raise RefreshConflictError("同一报告登记了不同科学质控结论")
            return previous
        self._append_event(
            event_type=_QC_EVENT,
            event_kind="refresh-scientific-qc",
            project_id=plan.project_id,
            actor_id=validated.reviewer_id,
            occurred_at=validated.reviewed_at,
            payload={
                "refresh_id": refresh_id,
                "qc": record.model_dump(
                    mode="json",
                    exclude={
                        "review_bundle": {"input_digest"},
                        "verdict": {"verdict_digest"},
                    },
                ),
            },
            idempotency_key=f"refresh.qc:{refresh_id}:{report_kind.value}",
        )
        return record

    def _locked_evidence_manifest(self, snapshot_id: str) -> dict[str, Any]:
        path = self.project_root / "snapshots" / "evidence" / f"{snapshot_id}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validated = EvidenceSnapshotManifest.model_validate(payload)
            locked = compute_locked_snapshot(
                kind="evidence",
                report=None,
                manifest=validated.model_dump(mode="json"),
            )
        except (OSError, json.JSONDecodeError, SnapshotIntegrityError, ValueError) as error:
            raise RefreshStateError("科学质控引用的证据快照尚未锁定或无法校验") from error
        if locked.snapshot_id != snapshot_id:
            raise RefreshStateError("科学质控引用的证据快照身份与内容不一致")
        return validated.model_dump(mode="json")

    def _qc_records(self, refresh_id: str) -> dict[ReportKind, RefreshQcRecord]:
        records: dict[ReportKind, RefreshQcRecord] = {}
        for event in self.event_store.read_all():
            if event.event_type != _QC_EVENT or event.payload.get("refresh_id") != refresh_id:
                continue
            record = RefreshQcRecord.model_validate(event.payload["qc"])
            existing = records.get(record.report_kind)
            if existing is not None and existing != record:
                raise RefreshConflictError("同一报告登记了不同科学质控结论")
            records[record.report_kind] = record
        return records

    # ── 操作 4：register_report_snapshot ───────────────────────────────────

    def register_report_snapshot(
        self,
        refresh_id: str,
        *,
        report_kind: ReportKind,
        manifest: dict[str, Any],
    ) -> str:
        """锁定并登记受影响报告的新快照；父快照与父版本字节不变。"""
        plan = self.load_plan(refresh_id)
        allowed_kinds = self._snapshot_allowed_kinds(plan)
        if report_kind not in allowed_kinds:
            raise RefreshStateError(
                "只有受影响或因候选晋级而重建的报告登记新快照，其他报告按父版本复用"
            )
        try:
            validated = ReportSnapshotManifest.model_validate(manifest)
            locked = compute_locked_snapshot(
                kind="report",
                report=report_kind.value,
                manifest=validated.model_dump(mode="json"),
            )
        except (SnapshotIntegrityError, ValueError) as error:
            raise RefreshStateError(f"报告快照不符合快照合同：{error}") from error
        if validated.project_id != plan.project_id:
            raise RefreshStateError("新报告快照与刷新项目不一致")
        if validated.contract_version != plan.child_contract.contract_version:
            raise RefreshStateError("新报告快照必须绑定刷新子合同版本")
        if validated.data_cutoff != plan.child_contract.data_cutoff:
            raise RefreshStateError("新报告快照必须绑定刷新后的数据截止日")
        registered = self._registered_snapshot_ids(refresh_id)
        if report_kind in registered:
            if registered[report_kind] != locked.snapshot_id:
                raise RefreshConflictError("同一受影响报告已登记另一份新快照")
            return locked.snapshot_id
        self.snapshot_store.lock_report_snapshot(
            report=report_kind.value, manifest=validated.model_dump(mode="json")
        )
        manifest_text = _canonical_json_text(validated.model_dump(mode="json"))
        with open_database(self.database_path) as database:
            rows = database.execute(
                """
                SELECT snapshot_id, manifest_json FROM report_snapshots
                WHERE snapshot_id = ? OR (
                    project_id = ? AND report_kind = ? AND report_version = ?
                )
                """,
                (
                    locked.snapshot_id,
                    plan.project_id,
                    report_kind.value,
                    validated.report_version,
                ),
            ).fetchall()
        if rows:
            exact_match = (
                len(rows) == 1
                and str(rows[0][0]) == locked.snapshot_id
                and str(rows[0][1]) == manifest_text
            )
            if not exact_match:
                raise RefreshStateError("新报告快照登记与既有版本冲突")
            self._append_snapshot_event(
                refresh_id=refresh_id,
                plan=plan,
                report_kind=report_kind,
                snapshot_id=locked.snapshot_id,
                report_version=validated.report_version,
                occurred_at=validated.created_at,
            )
            return locked.snapshot_id
        expected_version = self._next_report_version(report_kind)
        if validated.report_version != expected_version:
            raise RefreshStateError(f"新报告快照必须登记为紧邻的下一版本 {expected_version}")
        with open_database(self.database_path) as database:
            try:
                database.execute(
                    """
                    INSERT INTO report_snapshots (
                        snapshot_id, project_id, report_kind, report_version,
                        evidence_state, manifest_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        locked.snapshot_id,
                        plan.project_id,
                        report_kind.value,
                        validated.report_version,
                        "snapshot_locked",
                        manifest_text,
                        validated.created_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise RefreshStateError(f"新报告快照登记与既有版本冲突：{error}") from error
        self._append_snapshot_event(
            refresh_id=refresh_id,
            plan=plan,
            report_kind=report_kind,
            snapshot_id=locked.snapshot_id,
            report_version=validated.report_version,
            occurred_at=validated.created_at,
        )
        return locked.snapshot_id

    def _append_snapshot_event(
        self,
        *,
        refresh_id: str,
        plan: RefreshPlan,
        report_kind: ReportKind,
        snapshot_id: str,
        report_version: str,
        occurred_at: datetime,
    ) -> None:
        self._append_event(
            event_type=_SNAPSHOT_EVENT,
            event_kind="refresh-report-snapshot",
            project_id=plan.project_id,
            actor_id="refresh-service",
            occurred_at=occurred_at,
            payload={
                "refresh_id": refresh_id,
                "report_kind": report_kind.value,
                "snapshot_id": snapshot_id,
                "report_version": report_version,
            },
            idempotency_key=f"refresh.snapshot:{refresh_id}:{report_kind.value}",
        )

    def _registered_report_manifest(self, snapshot_id: str) -> dict[str, Any]:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT manifest_json FROM report_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
        if row is None:
            raise RefreshStateError("本轮报告快照登记缺失，不能继续质控或接受")
        payload = json.loads(str(row[0]))
        if not isinstance(payload, dict):
            raise RefreshStateError("本轮报告快照清单无法读取")
        return payload

    def _snapshot_allowed_kinds(self, plan: RefreshPlan) -> frozenset[ReportKind]:
        """允许登记新快照的报告：门槛受影响报告，加上候选晋级涉及的报告。

        门槛收紧只重算受影响报告；截止日扩展的晋级候选可能影响任何报告，
        由重建层选择实际重建的报告并在此登记。
        """
        return frozenset(plan.rebuild_report_kinds)

    def _registered_snapshot_ids(self, refresh_id: str) -> dict[ReportKind, str]:
        """本轮刷新已登记的报告快照：以追加事件为准。"""
        registered: dict[ReportKind, str] = {}
        for event in self.event_store.read_all():
            if event.event_type != _SNAPSHOT_EVENT:
                continue
            if event.payload.get("refresh_id") != refresh_id:
                continue
            kind = ReportKind(str(event.payload["report_kind"]))
            snapshot_id = str(event.payload["snapshot_id"])
            existing = registered.get(kind)
            if existing is not None and existing != snapshot_id:
                raise RefreshConflictError("同一受影响报告登记了不同新快照")
            registered[kind] = snapshot_id
        return registered

    def _next_report_version(self, report_kind: ReportKind) -> str:
        project_id = self.parent_contract().project_id
        with open_database(self.database_path) as database:
            rows = database.execute(
                """
                SELECT report_version FROM report_snapshots
                WHERE project_id = ? AND report_kind = ?
                """,
                (project_id, report_kind.value),
            ).fetchall()
        latest_rank = 0
        for row in rows:
            match = re.fullmatch(r"v([0-9]+)", str(row[0]))
            if match is None:
                raise RefreshStateError("已登记报告版本无法读取，暂不能登记新版本")
            latest_rank = max(latest_rank, int(match.group(1)))
        return f"v{latest_rank + 1}"

    # ── 操作 5：accept_refresh ─────────────────────────────────────────────

    def accept_refresh(
        self,
        refresh_id: str,
        *,
        occurred_at: datetime,
        actor_id: str,
        evidence_snapshot_manifest: dict[str, Any] | None = None,
    ) -> RefreshCompletion:
        """把子版本登记为已接受；局部重建未完成时失败关闭，不产生草稿接受。

        失败关闭顺序：全部受影响对象有重建回执 → 受影响报告门槛全部通过 →
        受影响报告新快照已登记（晋级候选必须建立新证据快照且至少重建一份
        报告）→ 项目文件当前版本翻转到子版本（幂等）→ 接受事件与账本登记。
        """
        plan = self.load_plan(refresh_id)
        accepted_at = _offset_datetime(occurred_at)
        claim_key = f"refresh.accept:{refresh_id}"

        actions = self._rebuild_actions(refresh_id)
        done = {
            (item.object_kind, item.object_id) for item in actions if item.disposition == "rebuilt"
        }
        required = {(item.object_kind, item.object_id) for item in plan.affected_objects}
        missing = sorted(required - done)
        if missing:
            names = "、".join(f"{kind}/{object_id}" for kind, object_id in missing[:5])
            raise RefreshIncompleteError(
                f"局部重建未完成，子版本不能登记为已接受：缺少重建回执 {names}"
            )
        decisions = self._gate_decisions(refresh_id)
        blocked_kinds = sorted(
            (kind for kind, record in decisions.items() if record.decision != "passed"),
            key=lambda kind: kind.value,
        )
        if blocked_kinds:
            names = "、".join(kind.value for kind in blocked_kinds)
            raise RefreshIncompleteError(f"{names} 类报告关键证据仍未达门槛，继续阻断，不生成草稿")
        missing_decisions = [kind for kind in plan.rebuild_report_kinds if kind not in decisions]
        if missing_decisions:
            names = "、".join(kind.value for kind in missing_decisions)
            raise RefreshIncompleteError(
                f"{names} 类报告尚未登记重算门槛决定，子版本不能登记为已接受"
            )
        registered = self._registered_snapshot_ids(refresh_id)
        pending_kinds = [kind for kind in plan.rebuild_report_kinds if kind not in registered]
        if pending_kinds:
            names = "、".join(kind.value for kind in pending_kinds)
            raise RefreshIncompleteError(f"受影响报告缺少新快照登记：{names}")
        if plan.promoted and evidence_snapshot_manifest is None:
            raise RefreshIncompleteError("晋级候选必须建立新的不可变证据快照后才能接受本轮刷新")
        expected_evidence_snapshot_id = self._expected_evidence_snapshot_id(
            plan, evidence_snapshot_manifest
        )
        for kind in plan.rebuild_report_kinds:
            decision = decisions[kind]
            manifest = self._registered_report_manifest(registered[kind])
            report_evidence_id = str(manifest["evidence_snapshot_id"])
            if decision.gate_result.evidence_snapshot_id != report_evidence_id:
                raise RefreshIncompleteError(
                    f"{kind.value} 类报告的门槛结果与报告快照未绑定同一份证据快照"
                )
            if (
                expected_evidence_snapshot_id is not None
                and report_evidence_id != expected_evidence_snapshot_id
            ):
                raise RefreshIncompleteError(f"{kind.value} 类报告未绑定本轮即将接受的证据快照")
        qc_records = self._qc_records(refresh_id)
        vetoed = sorted(
            (kind for kind, record in qc_records.items() if record.verdict.verdict != "accepted"),
            key=lambda kind: kind.value,
        )
        if vetoed:
            names = "、".join(kind.value for kind in vetoed)
            raise RefreshIncompleteError(f"{names} 类报告未通过独立科学质控，继续阻断，不生成草稿")
        expired_qc = sorted(
            (
                kind
                for kind, record in qc_records.items()
                if not (record.verdict.reviewed_at <= accepted_at <= record.verdict.valid_until)
            ),
            key=lambda kind: kind.value,
        )
        if expired_qc:
            names = "、".join(kind.value for kind in expired_qc)
            raise RefreshIncompleteError(f"{names} 类报告的科学质控结论已过期或晚于接受时间")
        missing_qc = [kind for kind in plan.rebuild_report_kinds if kind not in qc_records]
        if missing_qc:
            names = "、".join(kind.value for kind in missing_qc)
            raise RefreshIncompleteError(
                f"{names} 类报告尚未完成独立科学质控，子版本不能登记为已接受"
            )
        evidence_snapshot_id = self._lock_evidence_snapshot(plan, evidence_snapshot_manifest)

        completion = RefreshCompletion(
            schema_version="1.0",
            refresh_id=refresh_id,
            project_id=plan.project_id,
            child_contract_version=plan.child_contract.contract_version,
            evidence_snapshot_id=evidence_snapshot_id,
            report_snapshot_ids=tuple(
                registered[kind] for kind in sorted(registered, key=lambda kind: kind.value)
            ),
            accepted_at=accepted_at,
        )
        result = {"completion": completion.model_dump(mode="json")}
        existing_digest = self._recorded_digest(claim_key)
        if existing_digest is not None:
            if existing_digest != _payload_digest(result):
                raise RefreshConflictError("同一刷新的接受登记与既有记录不一致")
            return completion
        self._flip_active_contract(plan)
        self._append_event(
            event_type=_ACCEPTED_EVENT,
            event_kind="refresh-accepted",
            project_id=plan.project_id,
            actor_id=_not_blank(actor_id),
            occurred_at=accepted_at,
            payload={
                "refresh_id": refresh_id,
                "child_contract_version": plan.child_contract.contract_version,
                "report_snapshot_ids": {
                    kind.value: snapshot_id
                    for kind, snapshot_id in sorted(
                        registered.items(), key=lambda item: item[0].value
                    )
                },
                "evidence_snapshot_id": evidence_snapshot_id,
                "completion": completion.model_dump(mode="json"),
            },
            idempotency_key=f"refresh.accepted:{refresh_id}",
        )
        self._claim(key=claim_key, operation="refresh.accept", result=result)
        return completion

    def _lock_evidence_snapshot(
        self, plan: RefreshPlan, manifest: dict[str, Any] | None
    ) -> str | None:
        """锁定新证据快照并核验其绑定子合同版本与刷新后截止日。"""
        if manifest is None:
            return None
        expected = self._expected_evidence_snapshot_id(plan, manifest)
        try:
            validated = EvidenceSnapshotManifest.model_validate(manifest)
            locked = self.snapshot_store.lock_evidence_snapshot(validated.model_dump(mode="json"))
        except (SnapshotIntegrityError, ValueError) as error:
            raise RefreshStateError(f"新证据快照不符合快照合同：{error}") from error
        if validated.project_id != plan.project_id:
            raise RefreshStateError("新证据快照与刷新项目不一致")
        if validated.contract_version != plan.child_contract.contract_version:
            raise RefreshStateError("新证据快照必须绑定刷新子合同版本")
        if validated.data_cutoff != plan.child_contract.data_cutoff:
            raise RefreshStateError("新证据快照必须绑定刷新后的数据截止日")
        if locked.snapshot_id != expected:
            raise RefreshStateError("新证据快照锁定结果与预计算身份不一致")
        return locked.snapshot_id

    @staticmethod
    def _expected_evidence_snapshot_id(
        plan: RefreshPlan, manifest: dict[str, Any] | None
    ) -> str | None:
        if manifest is None:
            return None
        try:
            validated = EvidenceSnapshotManifest.model_validate(manifest)
            locked = compute_locked_snapshot(
                kind="evidence", report=None, manifest=validated.model_dump(mode="json")
            )
        except (SnapshotIntegrityError, ValueError) as error:
            raise RefreshStateError(f"新证据快照不符合快照合同：{error}") from error
        if validated.project_id != plan.project_id:
            raise RefreshStateError("新证据快照与刷新项目不一致")
        if validated.contract_version != plan.child_contract.contract_version:
            raise RefreshStateError("新证据快照必须绑定刷新子合同版本")
        if validated.data_cutoff != plan.child_contract.data_cutoff:
            raise RefreshStateError("新证据快照必须绑定刷新后的数据截止日")
        return locked.snapshot_id

    def _flip_active_contract(self, plan: RefreshPlan) -> None:
        """把项目文件当前版本翻转到子版本；父版本条目原样保留、字节不变。"""
        document = self._load_project_document()
        active = document.get("active_contract_version")
        if active == plan.child_contract.contract_version:
            return
        if active != plan.parent_contract.contract_version:
            raise RefreshStateError("项目当前合同版本已被其他刷新翻转，拒绝覆盖登记")
        versions = document.get("project_contract_versions")
        if not isinstance(versions, list):
            raise RefreshStateError("项目合同版本列表无法读取")
        already_listed = any(
            isinstance(item, dict)
            and item.get("contract_version") == plan.child_contract.contract_version
            for item in versions
        )
        if not already_listed:
            versions.append(plan.child_contract.model_dump(mode="json"))
        document["active_contract_version"] = plan.child_contract.contract_version
        self._atomic_json_write(self.project_root / "project.yaml", document)

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

    def _accepted_completion(self, refresh_id: str) -> RefreshCompletion | None:
        for event in self.event_store.read_all():
            if event.event_type != _ACCEPTED_EVENT:
                continue
            if event.payload.get("refresh_id") != refresh_id:
                continue
            return RefreshCompletion.model_validate(event.payload["completion"])
        return None

    # ── 计划构建 ───────────────────────────────────────────────────────────

    def _build_plan(
        self,
        *,
        parent: ProjectContract,
        child: ProjectContract,
        change_kinds: tuple[str, ...],
        requested_cutoff: datetime,
        occurred_at: datetime,
        promoted: tuple[CandidatePromotion, ...],
        blocked: tuple[BlockedCandidate, ...],
        gate_override: GateOverride | None,
        gate_spec_bindings: tuple[GateSpecBinding, ...],
        affected_kinds: tuple[ReportKind, ...],
        reuse_kinds: tuple[ReportKind, ...],
        affected_objects: tuple[ImpactedObject, ...],
        reuse_objects: tuple[ImpactedObject, ...],
        declared_change_records: tuple[ObjectChangeRecord, ...],
        impact_report_kinds: tuple[ReportKind, ...],
        impact_plan_digest: str | None,
    ) -> RefreshPlan:
        rebuild_kinds = tuple(
            sorted(
                set(affected_kinds) | set(impact_report_kinds),
                key=lambda kind: kind.value,
            )
        )
        reuse_kinds = tuple(
            sorted(
                set(parent.reports) - set(rebuild_kinds),
                key=lambda kind: kind.value,
            )
        )
        change_records = self._build_change_records(
            promoted=promoted,
            affected_objects=affected_objects,
            reuse_objects=reuse_objects,
            declared=declared_change_records,
        )
        refresh_id = stable_id(
            "refresh-plan",
            parent.project_id,
            str(parent.contract_version),
            str(child.contract_version),
            child.data_cutoff.isoformat(),
            _payload_digest(
                {
                    "change_kinds": list(change_kinds),
                    "promoted": [item.source_version_id for item in promoted],
                    "gate_override": (
                        gate_override.model_dump(mode="json") if gate_override else None
                    ),
                    "gate_spec_bindings": [
                        item.model_dump(mode="json") for item in gate_spec_bindings
                    ],
                    "affected_objects": [item.model_dump(mode="json") for item in affected_objects],
                    "rebuild_report_kinds": [kind.value for kind in rebuild_kinds],
                    "reuse_objects": [item.model_dump(mode="json") for item in reuse_objects],
                    "change_records": [item.model_dump(mode="json") for item in change_records],
                }
            ),
        )
        fields: dict[str, Any] = {
            "schema_version": "1.0",
            "refresh_id": refresh_id,
            "project_id": parent.project_id,
            "parent_contract": parent,
            "child_contract": child,
            "change_kinds": change_kinds,
            "requested_cutoff": requested_cutoff,
            "promoted": promoted,
            "blocked": blocked,
            "gate_override": gate_override,
            "gate_spec_bindings": gate_spec_bindings,
            "affected_report_kinds": affected_kinds,
            "rebuild_report_kinds": rebuild_kinds,
            "reuse_report_kinds": reuse_kinds,
            "affected_objects": affected_objects,
            "reuse_objects": reuse_objects,
            "change_records": change_records,
            "impact_plan_digest": impact_plan_digest,
            "plan_digest": "pending",
            "created_at": occurred_at,
        }
        # 摘要先于构造计算：构造期校验会按同一 _digest_body 算法重算并比对。
        probe = RefreshPlan.model_construct(**fields)
        fields["plan_digest"] = _payload_digest(probe._digest_body())
        return RefreshPlan(**fields)

    @staticmethod
    def _build_change_records(
        *,
        promoted: tuple[CandidatePromotion, ...],
        affected_objects: tuple[ImpactedObject, ...],
        reuse_objects: tuple[ImpactedObject, ...],
        declared: tuple[ObjectChangeRecord, ...],
    ) -> tuple[ObjectChangeRecord, ...]:
        affected = {(item.object_kind, item.object_id) for item in affected_objects}
        reused = {(item.object_kind, item.object_id) for item in reuse_objects}
        known = affected | reused
        promoted_pairs = {("source", item.source_version_id) for item in promoted}
        declared_by_pair: dict[tuple[str, str], ObjectChangeRecord] = {}
        for record in declared:
            pair = (record.object_kind, record.object_id)
            if pair not in known:
                raise RefreshStateError("变化台账包含影响图之外的对象")
            if pair in declared_by_pair:
                raise RefreshStateError("变化台账对同一对象重复分类")
            if pair in reused and record.change_kind != "unchanged":
                raise RefreshStateError("按摘要复用的对象只能登记为未变化")
            if pair in promoted_pairs and record.change_kind != "new":
                raise RefreshStateError("本轮晋级候选只能登记为新增对象")
            declared_by_pair[pair] = record

        records: list[ObjectChangeRecord] = []
        for pair in sorted(known):
            if pair in declared_by_pair:
                records.append(declared_by_pair[pair])
                continue
            if pair in promoted_pairs:
                change_kind: Literal[
                    "new", "changed", "withdrawn", "revised", "superseded", "unchanged"
                ] = "new"
                rationale = "本轮截止日扩展后首次进入适格证据范围。"
            elif pair in reused:
                change_kind = "unchanged"
                rationale = "依赖内容摘要未变化，本轮沿用已接受版本。"
            else:
                change_kind = "changed"
                rationale = "受新增证据或门槛收紧影响，本轮需要重新生成。"
            records.append(
                ObjectChangeRecord(
                    object_kind=pair[0],
                    object_id=pair[1],
                    change_kind=change_kind,
                    basis_digest=hashlib.sha256(
                        f"{pair[0]}:{pair[1]}:{change_kind}".encode()
                    ).hexdigest(),
                    rationale_zh=rationale,
                )
            )
        return tuple(records)


# ── 模块级辅助 ───────────────────────────────────────────────────────────────


def _edge_endpoints(edges: tuple[ImpactEdge, ...]) -> list[ImpactNode]:
    endpoints: dict[tuple[str, str], ImpactNode] = {}
    for edge in edges:
        for node in (edge.upstream, edge.downstream):
            endpoints.setdefault((node.layer.value, node.object_id), node)
    return list(endpoints.values())
