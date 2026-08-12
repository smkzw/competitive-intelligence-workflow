"""Task 3.5 部分交付协调器：从规范状态机械派生聚合条件并经 GraphExecutor 迁移。

本模块只编排规范状态，不持有科学事实，也不生成用户报告：

- 不可变的 :class:`DeliveryContract`（输出选择：报告类型 + 可选格式）与
  :class:`ReportTarget`（版本化运行目标）分离：改变报告类型/可选格式必须
  使用更高的正整数合同版本；版本化运行目标经显式重绑操作推进；
- 选择绑定：首次公开协调动作即使不发生项目迁移，也把不可变输出选择以
  ``coordinator.selection_bound`` 业务事件持久化到既有 EventStore（归约器
  安全 no-op）；同一合同身份下选择漂移失败关闭，旧版本不能在更高版本之后
  出现，放弃格式不能从集合中删除后计算 complete；
- 目标重绑：显式重开后的阻断报告经 ``coordinator.report_target_bound``
  业务事件绑定到新对象身份。每个重绑必须锚定一个具体的、被接受的显式项目
  重开事件：该重开必须发生在旧报告当前阻断进入事件之后、原因必须与重绑
  原因一致、且不得已被同类型的其他阻断代次消费；重放幂等、同身份载荷漂移
  失败关闭，旧对象保持不可变；
- 协调器自有业务事件读路径统一校验：任何伪造/错配/漂移的
  ``coordinator.selection_bound`` / ``coordinator.report_target_bound`` 事件
  在影响状态、选择或目标解析之前，以 :class:`CoordinatorEventContractError`
  失败关闭（载荷键集/类型、选择摘要、事件 ID/幂等键、版本序、目标链连续性、
  阻断代次、重开回执全部重算比对）；外来非协调器业务事件保持忽略；
- :class:`PartialDeliveryCoordinator` 从 ``executor.state()`` 归约出的规范
  状态逐对象分类（已交付 / 终态阻断 / 可继续），再机械计算 v1.2 §10.2
  聚合守卫所需的全部布尔键；项目/格式迁移全部经 ``GraphExecutor.submit()``
  发出，绝不直接改写 state dict，也不伪造 ``graph.transition.accepted``；
  同一协调动作的请求身份由合同身份 + 动作 + 阻断进入代次确定性派生，重放
  同一动作不追加事件，身份相同但载荷漂移由 EventStore 失败关闭；
- 调用者不得传入 ``selected_objects_continuable`` / ``all_selected_*`` 等
  结论布尔值——聚合证据完全由规范状态计算。

副作用边界：本模块不生产 artifact.publish/move、revision.approve、
artifact.delete 任何副作用事件，因此不触及 Task 3.4 验收锚点的副作用
生产入口校验边界。选择绑定与目标重绑是非图业务事件，写入前由本模块完成
领域校验，读路径由本模块的统一校验器重算身份与摘要；归约器对两类事件
安全 no-op，不改写图状态。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.registry import TRANSITION_REGISTRY
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.storage.event_store import (
    EventConflictError,
    StoredWorkflowEvent,
    WorkflowEvent,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_REPORT_KINDS: frozenset[str] = frozenset({"A", "B", "C"})
_OPTIONAL_FORMATS: frozenset[str] = frozenset({"pdf", "html-ppt", "pptx"})
MANDATORY_HTML: str = "html"

# 各运行族的终态阻断状态：进入后只能由显式 reopen 退出
_TERMINAL_BLOCKED: dict[str, frozenset[str]] = {
    "project": frozenset({"blocked", "partial_delivery_blocked"}),
    "report_evidence": frozenset({"evidence_blocked"}),
    "format_artifact": frozenset({"blocked"}),
}

# v1.2 §10.2 字面状态族分类（与 transitions/guards 冻结表一致）
_REPORT_KNOWN_STATES: frozenset[str] = frozenset(
    {
        "queued",
        "collecting",
        "recovering",
        "awaiting_user",
        "scientific_qc",
        "snapshot_locked",
        "evidence_blocked",
        "superseded",
    }
)
_FORMAT_KNOWN_STATES: frozenset[str] = frozenset(
    {
        "queued",
        "generating",
        "quality_check",
        "passed",
        "delivery_ready",
        "blocked",
        "superseded",
    }
)
_FORMAT_CONTINUABLE_STATES: frozenset[str] = frozenset(
    {"queued", "generating", "quality_check", "passed"}
)

# 项目显式重新打开（v1.2 §10.2 / g_project_blocked_running）
PROJECT_REOPEN_REASONS: tuple[str, ...] = (
    "user_material_accepted",
    "environment_fix_confirmed",
    "new_contract_version_reopens",
)
# 格式重新打开（v1.2 §10.2 / g_format_blocked_queued）：用户材料不能重开格式
FORMAT_REOPEN_REASONS: tuple[str, ...] = (
    "environment_fixed",
    "generator_fixed",
    "new_contract_version_reopens",
)

# 本模块持久化的非图业务事件类型：归约器安全 no-op
SELECTION_BOUND_EVENT: str = "coordinator.selection_bound"
REBIND_EVENT: str = "coordinator.report_target_bound"

# 协调器业务事件载荷的封闭键集
_SELECTION_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "contract_id",
        "contract_version",
        "reports",
        "mandatory_html",
        "optional_formats",
        "selection_digest",
    }
)
_REBIND_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "kind",
        "old_object_id",
        "new_object_id",
        "reason",
        "contract_id",
        "contract_version",
        "selection_digest",
        "reports",
        "optional_formats",
        "blocked_occurrence",
        "reopen_event_id",
        "reopen_event_digest",
    }
)

# 项目族聚合守卫：其必需键全部由协调器从规范状态机械计算
_AGGREGATE_GUARD_IDS: tuple[str, ...] = (
    "g_project_running_partially_delivered",
    "g_project_partially_delivered_partial_delivery_blocked",
    "g_project_any_incomplete_blocked",
    "g_project_any_incomplete_complete",
)


class CoordinationError(ValueError):
    """协调器领域错误：合同、选择、状态或身份不合法；失败关闭。"""


class ContractDriftError(CoordinationError):
    """同一合同身份下选择/载荷漂移：改变选择或放弃格式必须使用更高的新合同版本。"""


class InconsistentStateError(CoordinationError):
    """规范状态与选择矩阵矛盾：阻断/取代/交付状态不可并存。"""


class CoordinatorEventContractError(CoordinationError):
    """协调器自有业务事件契约校验失败：伪造、错配或漂移；失败关闭且不改写状态。"""


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


def _selection_digest_of(
    contract_id: str,
    contract_version: int,
    reports: list[str] | tuple[str, ...],
    optional_formats: list[str] | tuple[str, ...],
) -> str:
    """选择摘要：与协调器写路径完全一致的规范 JSON 摘要算法。"""
    return hashlib.sha256(
        _canonical_json(
            {
                "contract_id": contract_id,
                "contract_version": contract_version,
                "reports": list(reports),
                "optional_formats": list(optional_formats),
            }
        )
    ).hexdigest()


@dataclass(frozen=True)
class ReportTarget:
    """选定报告的稳定对象身份：报告类型 + 规范 report_evidence 对象 ID。"""

    kind: str
    object_id: str

    def __post_init__(self) -> None:
        if self.kind not in _REPORT_KINDS:
            raise ValueError(f"非法报告类型: {self.kind}")
        if not isinstance(self.object_id, str) or not self.object_id.strip():
            raise ValueError("报告对象身份不能为空")


@dataclass(frozen=True)
class DeliveryContract:
    """不可变输出选择合同：报告类型 + 可选格式；改变选择必须用更高的新合同版本。

    ``contract_version`` 与规范项目合同一致：正整数。``reports`` 是用户输出
    选择的报告类型（A/B/C 排序且不重复），格式亦排序且不重复——重复输入
    直接失败关闭。版本化运行目标（对象 ID）不在此处表达，由显式重绑操作
    持久化并解析。
    """

    contract_id: str
    contract_version: int
    reports: tuple[str, ...]
    optional_formats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.contract_id, str) or not self.contract_id.strip():
            raise ValueError("合同标识不能为空")
        if (
            not isinstance(self.contract_version, int)
            or isinstance(self.contract_version, bool)
            or self.contract_version < 1
        ):
            raise ValueError(
                f"合同版本必须是正整数，收到: {self.contract_version!r}"
            )
        if not isinstance(self.reports, tuple) or not self.reports:
            raise ValueError("合同必须至少选择一个报告")
        if any(kind not in _REPORT_KINDS for kind in self.reports):
            raise ValueError(f"非法报告类型: {self.reports}")
        if len(set(self.reports)) != len(self.reports):
            raise ValueError("合同报告类型重复")
        if self.reports != tuple(sorted(self.reports)):
            raise ValueError("合同报告必须按 A/B/C 排序")
        if not isinstance(self.optional_formats, tuple):
            raise ValueError("可选格式必须是元组")
        if any(fmt not in _OPTIONAL_FORMATS for fmt in self.optional_formats):
            raise ValueError(f"非法可选格式: {self.optional_formats}")
        if len(set(self.optional_formats)) != len(self.optional_formats):
            raise ValueError("可选格式重复")
        if self.optional_formats != tuple(sorted(self.optional_formats)):
            raise ValueError("可选格式必须排序")


def report_target(kind: str) -> ReportTarget:
    """默认版本报告目标：稳定对象身份 ``report_{kind}``。"""
    return ReportTarget(kind=kind, object_id=f"report_{kind}")


def report_version_target(kind: str, version: str) -> ReportTarget:
    """恢复阻断报告的新版本目标：新对象身份 ``report_{kind}_v{version}``。

    旧 ``evidence_blocked`` 报告版本保持不可变；恢复必须使用新对象身份，
    迁移表也没有把旧阻断对象原地改回 queued 的声明边。
    """
    if not isinstance(version, str) or not version.strip():
        raise ValueError("报告版本不能为空")
    return ReportTarget(kind=kind, object_id=f"report_{kind}_v{' '.join(version.split())}")


def format_object_id(report_object_id: str, fmt: str) -> str:
    """格式对象稳定身份：绑定报告对象身份 + 格式名。"""
    return f"{report_object_id}:{fmt}"


def matrix_targets(contract: DeliveryContract) -> tuple[tuple[str, str], ...]:
    """完整选择矩阵：每个选定报告 ×（强制 HTML + 每个选定可选格式）。"""
    return tuple(
        (kind, fmt)
        for kind in contract.reports
        for fmt in (MANDATORY_HTML, *contract.optional_formats)
    )


@dataclass(frozen=True)
class DeliveryTarget:
    """选择矩阵中的单一交付目标：报告类型 + 报告对象身份 + 格式。"""

    kind: str
    report_object_id: str
    fmt: str

    @property
    def object_id(self) -> str:
        return format_object_id(self.report_object_id, self.fmt)


@dataclass(frozen=True)
class DeliveryConditions:
    """从规范状态机械计算的聚合条件（v1.2 §10.2 聚合守卫的九个布尔键）。"""

    target_matrix: tuple[DeliveryTarget, ...]
    report_states: tuple[tuple[str, str | None], ...]
    format_states: tuple[tuple[str, str | None], ...]
    delivered_targets: tuple[DeliveryTarget, ...]
    terminal_blocked_targets: tuple[DeliveryTarget, ...]
    continuable_targets: tuple[DeliveryTarget, ...]
    at_least_one_artifact_delivery_ready: bool
    selected_objects_continuable: bool
    at_least_one_artifact_delivered: bool
    remaining_selected_exhausted_blocked: bool
    no_running_selected_object: bool
    no_deliverable_artifact: bool
    at_least_one_terminal_blocked: bool
    all_selected_html_delivery_ready: bool
    all_selected_optional_formats_delivery_ready: bool


@dataclass(frozen=True)
class CoordinationResult:
    """一次协调动作的结果：动作类型、提交事件（无则不提交）与聚合条件。"""

    action: str
    submitted: StoredWorkflowEvent | None
    conditions: DeliveryConditions
    note: str


@dataclass(frozen=True)
class _CoordinatorView:
    """协调器业务事件校验后的只读视图：选择绑定、重绑链与阻断/重开账本。"""

    selection_bindings: tuple[dict[str, Any], ...]
    rebind_payloads: tuple[dict[str, Any], ...]
    rebind_events: dict[str, StoredWorkflowEvent]
    rebind_by_identity: dict[tuple[str, str, str, int], StoredWorkflowEvent]
    current_targets: dict[str, str]
    bound_targets: frozenset[str]
    consumed_reopens: dict[str, frozenset[str]]
    project_reopens: tuple[StoredWorkflowEvent, ...]
    reopen_by_id: dict[str, StoredWorkflowEvent]
    blocked_entry_sequences: dict[tuple[str, str], tuple[tuple[int, int | None], ...]]
    binding_sequences: dict[tuple[str, int], int]


def _classify_target(
    report_state: str | None,
    fmt_state: str | None,
    target: DeliveryTarget,
) -> str:
    """单个矩阵目标的机械分类：delivered / terminal_blocked / continuable。

    报告终态阻断（evidence_blocked）时其全部格式目标一律终态阻断；
    未见格式对象按类型化起始状态 queued 处理；取代与矛盾状态失败关闭。
    """
    if report_state is not None and report_state not in _REPORT_KNOWN_STATES:
        raise InconsistentStateError(f"无法分类的报告状态: {report_state}")
    if fmt_state is not None and fmt_state not in _FORMAT_KNOWN_STATES:
        raise InconsistentStateError(f"无法分类的格式状态: {fmt_state}")
    if report_state == "evidence_blocked":
        if fmt_state in ("delivery_ready", "superseded"):
            raise InconsistentStateError(
                f"阻断报告 {target.report_object_id} 的格式对象状态矛盾: {fmt_state}"
            )
        return "terminal_blocked"
    if report_state == "superseded":
        raise InconsistentStateError(
            f"选定报告 {target.report_object_id} 已被取代，需要新合同版本重新绑定"
        )
    if fmt_state == "delivery_ready":
        if report_state != "snapshot_locked":
            raise InconsistentStateError(
                f"{target.object_id} 已交付但报告不在 snapshot_locked: {report_state}"
            )
        return "delivered"
    if fmt_state == "blocked":
        return "terminal_blocked"
    if fmt_state == "superseded":
        raise InconsistentStateError(f"选定格式 {target.object_id} 已被取代，需要新合同版本")
    if fmt_state is None or fmt_state in _FORMAT_CONTINUABLE_STATES:
        return "continuable"
    raise InconsistentStateError(f"无法分类的格式状态: {fmt_state}")


def _reopen_matches_reason(event: StoredWorkflowEvent, reason: str) -> bool:
    """接受的项目重开事件是否以该原因放行（守卫证据中对应真键）。"""
    evidence = event.payload.get("guard_evidence")
    return isinstance(evidence, dict) and evidence.get(reason) is True


class PartialDeliveryCoordinator:
    """报告/格式独立的渐进交付协调器。

    只读规范状态（``executor.state()``）并只经 ``executor.submit()`` 发出
    迁移；调用者不得传入 ``selected_objects_continuable``、
    ``all_selected_*`` 等结论布尔值。协调动作的请求身份由合同身份 + 动作 +
    阻断进入代次确定性派生：同合同同动作同代次重放不追加事件；身份相同但
    载荷漂移由 EventStore 失败关闭。所有读路径先经协调器业务事件统一校验
    （伪造/错配/漂移以 :class:`CoordinatorEventContractError` 失败关闭）。
    """

    def __init__(self, executor: GraphExecutor) -> None:
        self.executor = executor
        self.run_id = executor.run_id
        self._project_id: str | None = None

    # ── 公开 API ──────────────────────────────────────────────────────────

    def conditions(self, contract: DeliveryContract) -> DeliveryConditions:
        """从规范状态机械计算当前聚合条件（只读，不写事件）。

        只返回权威聚合条件：合同必须已绑定、必须是该合同当前绑定版本、且
        选择与绑定一致；未绑定版本、过期版本与同版本选择漂移一律失败关闭
        （非权威版本不允许直接读取聚合条件）。
        """
        view, state = self._validate_coordinator_events()
        self._require_authoritative(contract, view)
        return self._compute_conditions(contract, state, view)

    def reconcile(
        self,
        contract: DeliveryContract,
        *,
        actor_id: str,
        occurred_at: datetime,
    ) -> CoordinationResult:
        """静默推进项目在 running / awaiting_user / partially_delivered 内的合法迁移。

        即使本次没有候选迁移，也先持久化不可变选择绑定（若未绑定）——
        选择从首次公开动作起就不可在相同合同身份下漂移。两个阻断终态与
        complete 只能由显式 reopen 退出；静默 reconcile 绝不离开它们。
        """
        view, state = self._validate_coordinator_events()
        self._ensure_selection_bound(
            contract, actor_id=actor_id, occurred_at=occurred_at, view=view
        )
        project_object_id, current = self._single_project(state)
        conditions = self._compute_conditions(contract, state, view)
        if current in ("blocked", "partial_delivery_blocked"):
            return CoordinationResult(
                action="reconcile",
                submitted=None,
                conditions=conditions,
                note="terminal_blocked_requires_explicit_reopen",
            )
        if current == "complete":
            return CoordinationResult(
                action="reconcile",
                submitted=None,
                conditions=conditions,
                note="already_complete",
            )
        if current not in ("running", "awaiting_user", "partially_delivered"):
            raise CoordinationError(f"项目状态 {current} 无法协调")
        order: dict[str, tuple[str, ...]] = {
            "running": ("complete", "blocked", "partial_delivery_blocked", "partially_delivered"),
            "awaiting_user": ("complete", "blocked", "partial_delivery_blocked"),
            "partially_delivered": ("complete", "partial_delivery_blocked", "blocked"),
        }
        for to_state in order[current]:
            submitted = self._try_project_transition(
                contract,
                project_object_id,
                current,
                to_state,
                conditions,
                actor_id,
                occurred_at,
                view,
            )
            if submitted is not None:
                return CoordinationResult(
                    action="reconcile",
                    submitted=submitted,
                    conditions=conditions,
                    note=f"project:{current}->{to_state}",
                )
        return CoordinationResult(
            action="reconcile",
            submitted=None,
            conditions=conditions,
            note="no_candidate",
        )

    def reopen_project(
        self,
        contract: DeliveryContract,
        *,
        reason: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> CoordinationResult:
        """显式重新打开阻断项目：blocked / partial_delivery_blocked -> running。

        只接受用户材料、环境修复或新合同版本三种显式原因。新合同版本重开
        必须证明传入版本高于进入当前阻断态时的合同版本；请求身份携带阻断
        进入代次，同一阻断代次重放不追加事件、原因漂移失败关闭。
        """
        view, state = self._validate_coordinator_events()
        self._ensure_selection_bound(
            contract, actor_id=actor_id, occurred_at=occurred_at, view=view
        )
        if reason not in PROJECT_REOPEN_REASONS:
            raise CoordinationError(f"项目重新打开原因非法: {reason}")
        project_object_id, current = self._single_project(state)
        _, version_at_blocked = self._blocked_entry_info(view, "project", project_object_id)
        if (
            current is not None
            and current in ("blocked", "partial_delivery_blocked", "awaiting_user")
        ):
            source_state = current
            generation = self._entry_generation(source_state)
        else:
            # 重放：项目已在 running，重建最近一次被接受重开的 (源状态, 代次)
            last = self._last_accepted_reopen()
            if last is None:
                raise CoordinationError(f"项目当前状态 {current} 不可重新打开")
            source_state, generation = last
        identity_parts = ("project", "running", source_state, f"entry:{generation}")
        request_id = self._request_id(contract, identity_parts)
        existing = self._existing_transition_event(
            request_id, family="project", object_id=project_object_id
        )
        if existing is not None:
            # 同一阻断代次的同一重开动作重放：证据一致返回原事件，漂移失败关闭
            evidence = self._reopen_evidence(contract, "project", project_object_id, reason, view)
            if existing.payload.get("guard_evidence") != evidence:
                raise EventConflictError(
                    f"同一重开请求身份对应了不同证据: {request_id}"
                )
            return CoordinationResult(
                action="reopen_project",
                submitted=existing,
                conditions=self._compute_conditions(contract, state, view),
                note="replay_noop",
            )
        edge = TRANSITION_REGISTRY.declared("project", current, "running")
        if current is None or edge is None:
            raise CoordinationError(f"项目当前状态 {current} 不可重新打开")
        if (
            reason == "new_contract_version_reopens"
            and (
                version_at_blocked is None
                or contract.contract_version <= version_at_blocked
            )
        ):
            raise CoordinationError(
                f"新合同版本重开需要高于进入阻断时的版本 "
                f"v{version_at_blocked}，当前 v{contract.contract_version} 不是更新的版本"
            )
        conditions = self._compute_conditions(contract, state, view)
        evidence = self._reopen_evidence(contract, "project", project_object_id, reason, view)
        guard = TRANSITION_REGISTRY.evaluate_guard(
            edge.guard_id,
            evidence,
            target_family="project",
            target_object_id=project_object_id,
        )
        if not guard.allowed:
            raise CoordinationError(f"项目重新打开守卫拒绝: {guard.reason}")
        request = self._request(
            contract,
            family="project",
            object_id=project_object_id,
            from_state=current,
            to_state="running",
            trigger=edge.trigger,
            evidence=evidence,
            actor_id=actor_id,
            occurred_at=occurred_at,
            identity_parts=identity_parts,
        )
        return CoordinationResult(
            action="reopen_project",
            submitted=self.executor.submit(request),
            conditions=conditions,
            note=f"project:{current}->running",
        )

    def reopen_format(
        self,
        contract: DeliveryContract,
        *,
        report_kind: str,
        fmt: str,
        reason: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> CoordinationResult:
        """显式重新打开阻断格式：blocked -> queued。

        只接受环境/生成器修复或新合同版本；用户材料不能重开格式。请求身份
        携带该格式对象的阻断进入代次。
        """
        view, state = self._validate_coordinator_events()
        self._ensure_selection_bound(
            contract, actor_id=actor_id, occurred_at=occurred_at, view=view
        )
        if reason not in FORMAT_REOPEN_REASONS:
            raise CoordinationError(
                f"格式重新打开原因非法: {reason}（只允许环境/生成器修复或新合同版本）"
            )
        if report_kind not in contract.reports:
            raise CoordinationError(f"报告 {report_kind} 不在合同选择中")
        if fmt not in (MANDATORY_HTML, *contract.optional_formats):
            raise CoordinationError(f"{fmt} 不在合同选择矩阵中")
        report_object_id = view.current_targets[report_kind]
        object_id = format_object_id(report_object_id, fmt)
        epoch = self._blocked_epoch(view, "format_artifact", object_id)
        version_at_blocked = self._version_at_blocked(
            view, "format_artifact", object_id, contract.contract_id
        )
        identity_parts = ("format", object_id, f"entry:{epoch}")
        request_id = self._request_id(contract, identity_parts)
        existing = self._existing_transition_event(
            request_id, family="format_artifact", object_id=object_id
        )
        if existing is not None:
            # 同一阻断代次的同一重开动作重放：证据一致返回原事件，漂移失败关闭
            evidence = self._reopen_evidence(contract, "format_artifact", object_id, reason, view)
            if existing.payload.get("guard_evidence") != evidence:
                raise EventConflictError(
                    f"同一重开请求身份对应了不同证据: {request_id}"
                )
            return CoordinationResult(
                action="reopen_format",
                submitted=existing,
                conditions=self._compute_conditions(contract, state, view),
                note="replay_noop",
            )
        edge = TRANSITION_REGISTRY.declared("format_artifact", "blocked", "queued")
        if edge is None:
            raise CoordinationError("格式 blocked->queued 迁移未声明")
        if (
            reason == "new_contract_version_reopens"
            and (
                version_at_blocked is None
                or contract.contract_version <= version_at_blocked
            )
        ):
            raise CoordinationError(
                f"新合同版本重开需要高于进入阻断时的版本 "
                f"v{version_at_blocked}，当前 v{contract.contract_version} 不是更新的版本"
            )
        conditions = self._compute_conditions(contract, state, view)
        evidence = self._reopen_evidence(contract, "format_artifact", object_id, reason, view)
        guard = TRANSITION_REGISTRY.evaluate_guard(
            edge.guard_id,
            evidence,
            target_family="format_artifact",
            target_object_id=object_id,
        )
        if not guard.allowed:
            raise CoordinationError(f"格式重新打开守卫拒绝: {guard.reason}")
        request = self._request(
            contract,
            family="format_artifact",
            object_id=object_id,
            from_state="blocked",
            to_state="queued",
            trigger=edge.trigger,
            evidence=evidence,
            actor_id=actor_id,
            occurred_at=occurred_at,
            identity_parts=identity_parts,
        )
        return CoordinationResult(
            action="reopen_format",
            submitted=self.executor.submit(request),
            conditions=conditions,
            note=f"format:{object_id}:blocked->queued",
        )

    def rebind_report(
        self,
        contract: DeliveryContract,
        *,
        kind: str,
        old_object_id: str,
        new_object_id: str,
        reason: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> CoordinationResult:
        """显式重绑报告运行目标：kind 从旧对象推进到新对象身份。

        重绑必须锚定一个具体的、被接受的显式项目重开事件：

        - 该重开必须发生在旧报告当前阻断进入事件之后（陈旧重开失败关闭）；
        - 重开事件记录的原因必须与本次重绑原因一致（原因不匹配失败关闭）；
        - 该重开不得已被同一类型的其他阻断代次消费（重放幂等、代次唯一）；
        - 重开事件 ID/摘要持久化在重绑载荷与幂等身份中。

        其余前提（任一不满足即失败关闭）：kind 必须在合同输出选择中；重绑
        不改变选择；old_object_id 必须是该 kind 当前记录目标（错误类型重绑
        失败关闭）；旧报告必须处于终态 evidence_blocked；新对象身份不得已
        存在于规范状态或已被其他目标使用（复用/重定向失败关闭）；reason
        必须是显式重开原因之一。
        """
        view, state = self._validate_coordinator_events()
        self._ensure_selection_bound(
            contract, actor_id=actor_id, occurred_at=occurred_at, view=view
        )
        if kind not in _REPORT_KINDS:
            raise CoordinationError(f"非法报告类型: {kind}")
        if kind not in contract.reports:
            raise CoordinationError(f"报告 {kind} 不在合同选择中")
        if reason not in PROJECT_REOPEN_REASONS:
            raise CoordinationError(
                f"报告目标重绑原因非法: {reason}（必须是显式重开原因之一）"
            )
        old_object_id = " ".join(old_object_id.split())
        new_object_id = " ".join(new_object_id.split())
        if not old_object_id or not new_object_id:
            raise CoordinationError("报告目标身份不能为空")
        entries = view.blocked_entry_sequences.get(("report_evidence", old_object_id), ())
        if not entries:
            raise CoordinationError(f"旧报告 {old_object_id} 没有阻断进入事件，不可重绑")
        epoch = len(entries)
        # 同一 (kind, old, new, 阻断代次) 已记录：重放或原因漂移
        stored_event = view.rebind_by_identity.get(
            (kind, old_object_id, new_object_id, epoch)
        )
        if stored_event is not None:
            stored_reason = str(stored_event.payload["reason"])
            if stored_reason != reason:
                raise ContractDriftError(
                    f"同一报告重绑（{kind} {old_object_id} → {new_object_id}，"
                    f"阻断代次 {epoch}）被记录为 {stored_reason}，不能用 {reason} 漂移"
                )
            return CoordinationResult(
                action="rebind_report",
                submitted=None,
                conditions=self._compute_conditions(contract, state, view),
                note="replay_noop",
            )
        blocked_seq = entries[-1][0]
        reopen = self._find_qualifying_reopen(view, kind, blocked_seq, reason)
        if reopen is None:
            raise CoordinationError(
                f"报告 {kind} 在阻断之后没有匹配原因 {reason} 且未被消费的"
                "显式项目重开事件"
            )
        project_id = self._resolve_project_id()
        event_id = stable_id(
            "coordinator-rebind",
            project_id,
            self.run_id,
            contract.contract_id,
            str(contract.contract_version),
            kind,
            old_object_id,
            new_object_id,
            f"blocked:{epoch}",
            reopen.event_id,
        )
        payload: dict[str, object] = {
            "kind": kind,
            "old_object_id": old_object_id,
            "new_object_id": new_object_id,
            "reason": reason,
            "contract_id": contract.contract_id,
            "contract_version": contract.contract_version,
            "selection_digest": self._selection_digest(contract),
            "reports": list(contract.reports),
            "optional_formats": list(contract.optional_formats),
            "blocked_occurrence": epoch,
            "reopen_event_id": reopen.event_id,
            "reopen_event_digest": reopen.event_digest,
        }
        existing = view.rebind_events.get(event_id)
        if existing is not None:
            if existing.payload != payload:
                raise ContractDriftError(
                    f"同一报告重绑身份对应了不同载荷: {event_id}"
                )
            return CoordinationResult(
                action="rebind_report",
                submitted=None,
                conditions=self._compute_conditions(contract, state, view),
                note="replay_noop",
            )
        # 写路径状态前提
        if view.current_targets.get(kind) != old_object_id:
            raise CoordinationError(
                f"重绑类型错误：{kind} 的当前目标是 {view.current_targets.get(kind)}，"
                f"不是 {old_object_id}"
            )
        if state.get("report_evidence", {}).get(old_object_id) != "evidence_blocked":
            raise CoordinationError(
                f"旧报告 {old_object_id} 未处于 evidence_blocked，不可重绑"
            )
        if new_object_id in state.get("report_evidence", {}):
            raise CoordinationError(f"新对象 {new_object_id} 已存在于规范状态，不可复用")
        if new_object_id in view.bound_targets:
            raise CoordinationError(f"新对象 {new_object_id} 已被其他目标使用")
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=event_id,
            project_id=project_id,
            run_id=self.run_id,
            event_type=REBIND_EVENT,
            occurred_at=occurred_at,
            actor_id=actor_id,
            idempotency_key=(
                f"coordinator.rebind:{self.run_id}:{contract.contract_id}:"
                f"{contract.contract_version}:{kind}:{old_object_id}:{new_object_id}:"
                f"blocked:{epoch}:{reopen.event_id}"
            ),
            payload=payload,
        )
        stored = self.executor.store.append(event)
        # 追加后重新校验并重建视图：返回的条件必须已解析新目标，无需二次读取
        fresh_view, fresh_state = self._validate_coordinator_events()
        return CoordinationResult(
            action="rebind_report",
            submitted=stored,
            conditions=self._compute_conditions(contract, fresh_state, fresh_view),
            note=f"report:{kind}:{old_object_id}->{new_object_id}",
        )

    # ── 协调器业务事件统一校验 ────────────────────────────────────────────

    def _validate_coordinator_events(self) -> tuple[_CoordinatorView, dict[str, Any]]:
        """读路径统一校验：先归约（伪造图事件在归约时失败关闭），再逐条校验
        协调器业务事件；任何伪造/错配/漂移在选择、目标或阻断账本被读取前以
        :class:`CoordinatorEventContractError` 失败关闭。外来非协调器业务事件
        保持忽略。
        """
        state = self.executor.state()
        events = self._run_events()
        project_id = self._resolve_project_id()
        selection_bindings: list[dict[str, Any]] = []
        rebind_payloads: list[dict[str, Any]] = []
        rebind_events: dict[str, StoredWorkflowEvent] = {}
        rebind_by_identity: dict[tuple[str, str, str, int], StoredWorkflowEvent] = {}
        current_targets: dict[str, str] = {kind: f"report_{kind}" for kind in _REPORT_KINDS}
        bound_targets: set[str] = {f"report_{kind}" for kind in _REPORT_KINDS}
        seen_report_objects: set[str] = set()
        consumed_reopens: dict[str, set[str]] = {kind: set() for kind in _REPORT_KINDS}
        project_reopens: list[StoredWorkflowEvent] = []
        reopen_by_id: dict[str, StoredWorkflowEvent] = {}
        blocked_entries: dict[tuple[str, str], list[tuple[int, int | None]]] = {}
        seen_contracts: dict[str, tuple[int, tuple[str, ...], tuple[str, ...]]] = {}
        binding_sequences: dict[tuple[str, int], int] = {}
        for event in events:
            if event.event_type == SELECTION_BOUND_EVENT:
                payload = self._validate_selection_event(event, project_id, seen_contracts)
                selection_bindings.append(payload)
                binding_sequences[
                    (str(payload["contract_id"]), int(payload["contract_version"]))
                ] = event.sequence
            elif event.event_type == REBIND_EVENT:
                payload = self._validate_rebind_event(
                    event,
                    project_id,
                    current_targets,
                    bound_targets,
                    seen_report_objects,
                    consumed_reopens,
                    reopen_by_id,
                    blocked_entries,
                    selection_bindings,
                )
                rebind_payloads.append(payload)
                rebind_events[event.event_id] = event
                identity = (
                    str(payload["kind"]),
                    str(payload["old_object_id"]),
                    str(payload["new_object_id"]),
                    int(payload["blocked_occurrence"]),
                )
                rebind_by_identity[identity] = event
                current_targets[str(payload["kind"])] = str(payload["new_object_id"])
                bound_targets.add(str(payload["new_object_id"]))
                consumed_reopens[str(payload["kind"])].add(str(payload["reopen_event_id"]))
            elif event.event_type == "graph.transition.accepted":
                payload = event.payload
                family = payload.get("family")
                if (
                    family == "project"
                    and payload.get("to_state") == "running"
                    and payload.get("from_state") in ("blocked", "partial_delivery_blocked")
                ):
                    project_reopens.append(event)
                    reopen_by_id[event.event_id] = event
                if (
                    family in _TERMINAL_BLOCKED
                    and payload.get("to_state") in _TERMINAL_BLOCKED[family]
                ):
                    object_id = str(payload["object_id"])
                    version: int | None = None
                    guard_evidence = payload.get("guard_evidence")
                    if isinstance(guard_evidence, dict) and isinstance(
                        guard_evidence.get("contract_version"), int
                    ):
                        version = guard_evidence["contract_version"]
                    blocked_entries.setdefault((str(family), object_id), []).append(
                        (event.sequence, version)
                    )
                if family == "report_evidence":
                    seen_report_objects.add(str(payload["object_id"]))
        view = _CoordinatorView(
            selection_bindings=tuple(selection_bindings),
            rebind_payloads=tuple(rebind_payloads),
            rebind_events=rebind_events,
            rebind_by_identity=rebind_by_identity,
            current_targets=current_targets,
            bound_targets=frozenset(bound_targets),
            consumed_reopens={kind: frozenset(ids) for kind, ids in consumed_reopens.items()},
            project_reopens=tuple(project_reopens),
            reopen_by_id=reopen_by_id,
            blocked_entry_sequences={key: tuple(value) for key, value in blocked_entries.items()},
            binding_sequences=binding_sequences,
        )
        return view, state

    def _validate_selection_event(
        self,
        event: StoredWorkflowEvent,
        project_id: str,
        seen_contracts: dict[str, tuple[int, tuple[str, ...], tuple[str, ...]]],
    ) -> dict[str, Any]:
        """selection_bound 契约校验：键集/类型、版本序、选择摘要与事件身份重算。"""
        payload = event.payload
        if set(payload) != _SELECTION_PAYLOAD_KEYS:
            raise CoordinatorEventContractError(
                f"selection_bound 载荷键集不合法: {event.event_id}"
            )
        contract_id = payload["contract_id"]
        if not isinstance(contract_id, str) or not contract_id.strip():
            raise CoordinatorEventContractError(
                f"selection_bound 合同标识不合法: {event.event_id}"
            )
        version = payload["contract_version"]
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise CoordinatorEventContractError(
                f"selection_bound 合同版本不是正整数: {event.event_id}"
            )
        reports = payload["reports"]
        if (
            not isinstance(reports, list)
            or not reports
            or any(
                not isinstance(kind, str) or kind not in _REPORT_KINDS
                for kind in reports
            )
        ):
            raise CoordinatorEventContractError(
                f"selection_bound 报告类型不合法: {event.event_id}"
            )
        if len(set(reports)) != len(reports):
            raise CoordinatorEventContractError(
                f"selection_bound 报告类型重复: {event.event_id}"
            )
        if reports != sorted(reports):
            raise CoordinatorEventContractError(
                f"selection_bound 报告类型未排序: {event.event_id}"
            )
        if payload["mandatory_html"] != MANDATORY_HTML:
            raise CoordinatorEventContractError(
                f"selection_bound mandatory_html 漂移: {event.event_id}"
            )
        formats = payload["optional_formats"]
        if not isinstance(formats, list) or any(
            fmt not in _OPTIONAL_FORMATS for fmt in formats
        ):
            raise CoordinatorEventContractError(
                f"selection_bound 可选格式不合法: {event.event_id}"
            )
        if len(set(formats)) != len(formats):
            raise CoordinatorEventContractError(
                f"selection_bound 可选格式重复: {event.event_id}"
            )
        if formats != sorted(formats):
            raise CoordinatorEventContractError(
                f"selection_bound 可选格式未排序: {event.event_id}"
            )
        expected_digest = _selection_digest_of(contract_id, version, reports, formats)
        if payload["selection_digest"] != expected_digest:
            raise CoordinatorEventContractError(
                f"selection_bound 选择摘要漂移: {event.event_id}"
            )
        if event.project_id != project_id:
            raise CoordinatorEventContractError(
                f"selection_bound 项目身份不匹配: {event.event_id}"
            )
        expected_event_id = stable_id(
            "coordinator-selection", project_id, event.run_id, contract_id, str(version)
        )
        if event.event_id != expected_event_id:
            raise CoordinatorEventContractError(
                f"selection_bound 事件标识漂移: {event.event_id}"
            )
        expected_key = f"coordinator.selection:{event.run_id}:{contract_id}:{version}"
        if event.idempotency_key != expected_key:
            raise CoordinatorEventContractError(
                f"selection_bound 幂等键漂移: {event.event_id}"
            )
        selection = (tuple(reports), tuple(formats))
        prior = seen_contracts.get(contract_id)
        if prior is not None:
            prior_version, prior_reports, prior_formats = prior
            if version < prior_version:
                raise CoordinatorEventContractError(
                    f"合同 {contract_id} 旧版本 v{version} 出现在 v{prior_version} 之后"
                )
            if version == prior_version and selection != (prior_reports, prior_formats):
                raise CoordinatorEventContractError(
                    f"合同 {contract_id} v{version} 同版本不同选择"
                )
        seen_contracts[contract_id] = (version, selection[0], selection[1])
        return payload

    def _validate_rebind_event(
        self,
        event: StoredWorkflowEvent,
        project_id: str,
        current_targets: dict[str, str],
        bound_targets: set[str],
        seen_report_objects: set[str],
        consumed_reopens: dict[str, set[str]],
        reopen_by_id: dict[str, StoredWorkflowEvent],
        blocked_entries: dict[tuple[str, str], list[tuple[int, int | None]]],
        selection_bindings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """report_target_bound 契约校验：键集/类型、选择绑定、链连续性、
        新目标复用、阻断代次、重开回执与事件身份重算。"""
        payload = event.payload
        if set(payload) != _REBIND_PAYLOAD_KEYS:
            raise CoordinatorEventContractError(
                f"report_target_bound 载荷键集不合法: {event.event_id}"
            )
        kind = payload["kind"]
        if not isinstance(kind, str) or kind not in _REPORT_KINDS:
            raise CoordinatorEventContractError(
                f"report_target_bound 报告类型不合法: {event.event_id}"
            )
        old_object_id = payload["old_object_id"]
        new_object_id = payload["new_object_id"]
        if not isinstance(old_object_id, str) or not old_object_id.strip():
            raise CoordinatorEventContractError(
                f"report_target_bound 旧目标不合法: {event.event_id}"
            )
        if not isinstance(new_object_id, str) or not new_object_id.strip():
            raise CoordinatorEventContractError(
                f"report_target_bound 新目标不合法: {event.event_id}"
            )
        # 旧/新目标必须是规范空白形式：伪造的尾随/内部重复空白不能消费重开
        # 或重定向目标解析
        if old_object_id != " ".join(old_object_id.split()):
            raise CoordinatorEventContractError(
                f"report_target_bound 旧目标未规范化: {event.event_id}"
            )
        if new_object_id != " ".join(new_object_id.split()):
            raise CoordinatorEventContractError(
                f"report_target_bound 新目标未规范化: {event.event_id}"
            )
        reason = payload["reason"]
        if not isinstance(reason, str) or reason not in PROJECT_REOPEN_REASONS:
            raise CoordinatorEventContractError(
                f"report_target_bound 原因不合法: {event.event_id}"
            )
        contract_id = payload["contract_id"]
        if not isinstance(contract_id, str) or not contract_id.strip():
            raise CoordinatorEventContractError(
                f"report_target_bound 合同标识不合法: {event.event_id}"
            )
        version = payload["contract_version"]
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise CoordinatorEventContractError(
                f"report_target_bound 合同版本不是正整数: {event.event_id}"
            )
        reports = payload["reports"]
        if (
            not isinstance(reports, list)
            or not reports
            or any(report not in _REPORT_KINDS for report in reports)
        ):
            raise CoordinatorEventContractError(
                f"report_target_bound 报告选择不合法: {event.event_id}"
            )
        if len(set(reports)) != len(reports) or reports != sorted(reports):
            raise CoordinatorEventContractError(
                f"report_target_bound 报告选择未排序或不重复: {event.event_id}"
            )
        if kind not in reports:
            raise CoordinatorEventContractError(
                f"report_target_bound 重绑类型不在选择中: {event.event_id}"
            )
        formats = payload["optional_formats"]
        if (
            not isinstance(formats, list)
            or any(fmt not in _OPTIONAL_FORMATS for fmt in formats)
        ):
            raise CoordinatorEventContractError(
                f"report_target_bound 可选格式不合法: {event.event_id}"
            )
        if len(set(formats)) != len(formats) or formats != sorted(formats):
            raise CoordinatorEventContractError(
                f"report_target_bound 可选格式未排序或不重复: {event.event_id}"
            )
        expected_digest = _selection_digest_of(contract_id, version, reports, formats)
        if payload["selection_digest"] != expected_digest:
            raise CoordinatorEventContractError(
                f"report_target_bound 选择摘要漂移: {event.event_id}"
            )
        binding = next(
            (
                candidate
                for candidate in reversed(selection_bindings)
                if candidate["contract_id"] == contract_id
                and candidate["contract_version"] == version
            ),
            None,
        )
        if binding is None or (
            tuple(binding["reports"]),
            tuple(binding["optional_formats"]),
        ) != (tuple(reports), tuple(formats)):
            raise CoordinatorEventContractError(
                f"report_target_bound 选择未绑定: {event.event_id}"
            )
        occurrence = payload["blocked_occurrence"]
        if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
            raise CoordinatorEventContractError(
                f"report_target_bound 阻断代次不合法: {event.event_id}"
            )
        reopen_event_id = payload["reopen_event_id"]
        reopen_digest = payload["reopen_event_digest"]
        if not isinstance(reopen_event_id, str) or not reopen_event_id.strip():
            raise CoordinatorEventContractError(
                f"report_target_bound 重开事件标识不合法: {event.event_id}"
            )
        if not isinstance(reopen_digest, str) or _SHA256_RE.fullmatch(reopen_digest) is None:
            raise CoordinatorEventContractError(
                f"report_target_bound 重开摘要不合法: {event.event_id}"
            )
        if event.project_id != project_id:
            raise CoordinatorEventContractError(
                f"report_target_bound 项目身份不匹配: {event.event_id}"
            )
        expected_event_id = stable_id(
            "coordinator-rebind",
            project_id,
            event.run_id,
            contract_id,
            str(version),
            kind,
            old_object_id,
            new_object_id,
            f"blocked:{occurrence}",
            reopen_event_id,
        )
        if event.event_id != expected_event_id:
            raise CoordinatorEventContractError(
                f"report_target_bound 事件标识漂移: {event.event_id}"
            )
        expected_key = (
            f"coordinator.rebind:{event.run_id}:{contract_id}:{version}:{kind}:"
            f"{old_object_id}:{new_object_id}:blocked:{occurrence}:{reopen_event_id}"
        )
        if event.idempotency_key != expected_key:
            raise CoordinatorEventContractError(
                f"report_target_bound 幂等键漂移: {event.event_id}"
            )
        if current_targets.get(kind) != old_object_id:
            raise CoordinatorEventContractError(
                f"report_target_bound 目标链断裂: {event.event_id}"
            )
        # 新目标不得复用：不得是任何当前/默认目标、已绑定目标，或在该重绑
        # 事件之前已进入规范状态的报告对象（按事件位置判定，重放稳定）
        if new_object_id in bound_targets or new_object_id in seen_report_objects:
            raise CoordinatorEventContractError(
                f"report_target_bound 新目标复用: {event.event_id}"
            )
        entries = blocked_entries.get(("report_evidence", old_object_id), [])
        if len(entries) < occurrence:
            raise CoordinatorEventContractError(
                f"report_target_bound 阻断进入事件缺失: {event.event_id}"
            )
        blocked_seq = entries[occurrence - 1][0]
        reopen = reopen_by_id.get(reopen_event_id)
        if reopen is None:
            raise CoordinatorEventContractError(
                f"report_target_bound 重开回执不存在: {event.event_id}"
            )
        if reopen.sequence <= blocked_seq:
            raise CoordinatorEventContractError(
                f"report_target_bound 重开早于阻断进入: {event.event_id}"
            )
        if reopen.event_digest != reopen_digest:
            raise CoordinatorEventContractError(
                f"report_target_bound 重开摘要不匹配: {event.event_id}"
            )
        if not _reopen_matches_reason(reopen, reason):
            raise CoordinatorEventContractError(
                f"report_target_bound 重开原因不匹配: {event.event_id}"
            )
        if reopen_event_id in consumed_reopens.get(kind, set()):
            raise CoordinatorEventContractError(
                f"report_target_bound 重开已被消费: {event.event_id}"
            )
        return payload

    def _find_qualifying_reopen(
        self,
        view: _CoordinatorView,
        kind: str,
        after_sequence: int,
        reason: str,
    ) -> StoredWorkflowEvent | None:
        """阻断进入之后、原因匹配且未被同类型消费的最近一次项目重开事件。"""
        consumed = view.consumed_reopens.get(kind, frozenset())
        candidates = [
            event
            for event in view.project_reopens
            if event.sequence > after_sequence
            and event.event_id not in consumed
            and _reopen_matches_reason(event, reason)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda event: event.sequence)

    # ── 选择绑定与目标解析 ────────────────────────────────────────────────

    def _ensure_selection_bound(
        self,
        contract: DeliveryContract,
        *,
        actor_id: str,
        occurred_at: datetime,
        view: _CoordinatorView,
    ) -> None:
        """首次公开动作持久化不可变选择绑定；此后漂移/降级一律失败关闭。

        同 (contract_id, version) 已绑定且选择一致 → no-op；选择不一致 →
        :class:`ContractDriftError`；已绑定更高版本时旧版本（无论是否曾绑定）
        一律拒绝 → :class:`ContractDriftError`；未绑定且高于全部已绑定版本
        才写入新绑定事件。
        """
        project_id = self._resolve_project_id()
        versions = [
            binding["contract_version"]
            for binding in view.selection_bindings
            if binding["contract_id"] == contract.contract_id
        ]
        if versions and contract.contract_version < max(versions):
            raise ContractDriftError(
                f"合同 {contract.contract_id} 已绑定更高版本 v{max(versions)}，"
                f"v{contract.contract_version} 已过期；过期版本不能读取或推进任何协调动作"
            )
        recorded = self._binding_from_view(view, contract.contract_id, contract.contract_version)
        if recorded is not None:
            recorded_selection = (
                tuple(recorded["reports"]),
                tuple(recorded["optional_formats"]),
            )
            current_selection = (contract.reports, contract.optional_formats)
            if recorded_selection != current_selection:
                raise ContractDriftError(
                    f"合同 {contract.contract_id} v{contract.contract_version} 的选择"
                    "发生漂移；改变选择或放弃格式必须使用更高的新合同版本"
                )
            return
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(
                "coordinator-selection",
                project_id,
                self.run_id,
                contract.contract_id,
                str(contract.contract_version),
            ),
            project_id=project_id,
            run_id=self.run_id,
            event_type=SELECTION_BOUND_EVENT,
            occurred_at=occurred_at,
            actor_id=actor_id,
            idempotency_key=(
                f"coordinator.selection:{self.run_id}:{contract.contract_id}:"
                f"{contract.contract_version}"
            ),
            payload={
                "contract_id": contract.contract_id,
                "contract_version": contract.contract_version,
                "reports": list(contract.reports),
                "mandatory_html": MANDATORY_HTML,
                "optional_formats": list(contract.optional_formats),
                "selection_digest": self._selection_digest(contract),
            },
        )
        self.executor.store.append(event)

    @staticmethod
    def _binding_from_view(
        view: _CoordinatorView,
        contract_id: str,
        contract_version: int,
    ) -> dict[str, Any] | None:
        for binding in reversed(view.selection_bindings):
            if (
                binding["contract_id"] == contract_id
                and binding["contract_version"] == contract_version
            ):
                return binding
        return None

    def _run_events(self) -> tuple[StoredWorkflowEvent, ...]:
        return tuple(
            event
            for event in self.executor.store.read_all()
            if event.run_id == self.run_id
        )

    def _request_id(
        self,
        contract: DeliveryContract,
        identity_parts: tuple[str, ...],
    ) -> str:
        """协调请求的稳定身份：合同身份 + 动作 + 阻断进入代次。"""
        project_id = self._resolve_project_id()
        return stable_id(
            "coord",
            project_id,
            self.run_id,
            contract.contract_id,
            str(contract.contract_version),
            *identity_parts,
        )

    def _existing_transition_event(
        self,
        request_id: str,
        *,
        family: str,
        object_id: str,
    ) -> StoredWorkflowEvent | None:
        """按协调请求身份找回已接受的迁移事件（与 executor.submit 事件身份一致）。

        已接受事件存在且证据一致 → 同一动作重放，返回原事件不追加；
        证据漂移由调用方失败关闭。
        """
        event_id = stable_id(
            "graph-transition",
            self._resolve_project_id(),
            self.run_id,
            family,
            object_id,
            request_id,
        )
        for event in self._run_events():
            if (
                event.event_type == "graph.transition.accepted"
                and event.event_id == event_id
            ):
                return event
        return None

    # ── 内部实现 ──────────────────────────────────────────────────────────

    def _resolve_project_id(self) -> str:
        if self._project_id is None:
            projects = {event.project_id for event in self.executor.store.read_all()}
            if not projects:
                raise CoordinationError("事件流中没有项目事件，无法确定项目身份")
            if len(projects) > 1:
                raise CoordinationError("事件流混入了多个项目身份")
            self._project_id = next(iter(projects))
        return self._project_id

    def _single_project(self, state: dict[str, Any]) -> tuple[str, str | None]:
        projects = state.get("project", {})
        if len(projects) != 1:
            raise CoordinationError(f"项目对象必须恰好一个，实际 {len(projects)}")
        object_id = next(iter(projects))
        return object_id, projects[object_id]

    def _compute_conditions(
        self,
        contract: DeliveryContract,
        state: dict[str, Any],
        view: _CoordinatorView,
    ) -> DeliveryConditions:
        report_evidence = state.get("report_evidence", {})
        format_artifact = state.get("format_artifact", {})
        report_states: list[tuple[str, str | None]] = []
        format_states: list[tuple[str, str | None]] = []
        targets: list[DeliveryTarget] = []
        for kind in contract.reports:
            report_object_id = view.current_targets[kind]
            report_state = report_evidence.get(report_object_id)
            report_states.append((report_object_id, report_state))
            for fmt in (MANDATORY_HTML, *contract.optional_formats):
                target = DeliveryTarget(
                    kind=kind,
                    report_object_id=report_object_id,
                    fmt=fmt,
                )
                format_states.append((target.object_id, format_artifact.get(target.object_id)))
                targets.append(target)
        delivered: list[DeliveryTarget] = []
        terminal: list[DeliveryTarget] = []
        continuable: list[DeliveryTarget] = []
        for target in targets:
            classification = _classify_target(
                report_evidence.get(target.report_object_id),
                format_artifact.get(target.object_id),
                target,
            )
            if classification == "delivered":
                delivered.append(target)
            elif classification == "terminal_blocked":
                terminal.append(target)
            else:
                continuable.append(target)
        delivered_ids = {target.object_id for target in delivered}
        html_targets = [target for target in targets if target.fmt == MANDATORY_HTML]
        optional_targets = [target for target in targets if target.fmt != MANDATORY_HTML]
        no_running = not continuable
        return DeliveryConditions(
            target_matrix=tuple(targets),
            report_states=tuple(report_states),
            format_states=tuple(format_states),
            delivered_targets=tuple(delivered),
            terminal_blocked_targets=tuple(terminal),
            continuable_targets=tuple(continuable),
            at_least_one_artifact_delivery_ready=bool(delivered),
            selected_objects_continuable=bool(continuable),
            at_least_one_artifact_delivered=bool(delivered),
            remaining_selected_exhausted_blocked=no_running,
            no_running_selected_object=no_running,
            no_deliverable_artifact=not delivered,
            at_least_one_terminal_blocked=bool(terminal),
            all_selected_html_delivery_ready=all(
                target.object_id in delivered_ids for target in html_targets
            ),
            all_selected_optional_formats_delivery_ready=all(
                target.object_id in delivered_ids for target in optional_targets
            ),
        )

    def _try_project_transition(
        self,
        contract: DeliveryContract,
        project_object_id: str,
        from_state: str,
        to_state: str,
        conditions: DeliveryConditions,
        actor_id: str,
        occurred_at: datetime,
        view: _CoordinatorView,
    ) -> StoredWorkflowEvent | None:
        edge = TRANSITION_REGISTRY.declared("project", from_state, to_state)
        if edge is None:
            return None
        evidence = self._project_evidence(contract, project_object_id, conditions, view)
        guard = TRANSITION_REGISTRY.evaluate_guard(
            edge.guard_id,
            evidence,
            target_family="project",
            target_object_id=project_object_id,
        )
        if not guard.allowed:
            return None
        entry = self._running_entry_count()
        request = self._request(
            contract,
            family="project",
            object_id=project_object_id,
            from_state=from_state,
            to_state=to_state,
            trigger=edge.trigger,
            evidence=evidence,
            actor_id=actor_id,
            occurred_at=occurred_at,
            identity_parts=("project", to_state, f"entry:{entry}"),
        )
        return self.executor.submit(request)

    def _running_entry_count(self) -> int:
        """规范事件流中该项目进入 running 的次数（含新建与显式重开）。"""
        count = 0
        for event in self._run_events():
            if event.event_type != "graph.transition.accepted":
                continue
            payload = event.payload
            if payload.get("family") == "project" and payload.get("to_state") == "running":
                count += 1
        return count

    def _require_authoritative(self, contract: DeliveryContract, view: _CoordinatorView) -> None:
        """权威聚合条件门槛：合同必须已绑定、必须是当前绑定版本、选择一致。

        未绑定版本（非权威）、已过期版本（更高版本已绑定）与同版本选择漂移
        一律失败关闭——过期合同不能读取或推进任何协调动作。
        """
        bindings = [
            binding
            for binding in view.selection_bindings
            if binding["contract_id"] == contract.contract_id
        ]
        if not bindings:
            raise CoordinationError(
                f"合同 {contract.contract_id} 尚未绑定；非权威版本不能读取"
                "聚合条件（先 reconcile 绑定）"
            )
        latest = max(bindings, key=lambda binding: binding["contract_version"])
        if latest["contract_version"] != contract.contract_version:
            raise ContractDriftError(
                f"合同 {contract.contract_id} 当前绑定版本为 "
                f"v{latest['contract_version']}，v{contract.contract_version} 已过期；"
                "过期版本不能读取或推进任何协调动作"
            )
        selection = (
            tuple(latest["reports"]),
            tuple(latest["optional_formats"]),
        )
        if selection != (contract.reports, contract.optional_formats):
            raise ContractDriftError(
                f"合同 {contract.contract_id} v{contract.contract_version} 的选择"
                "与绑定不一致；同版本选择漂移失败关闭"
            )

    def _entry_generation(self, source_state: str) -> int:
        """项目进入该源状态的次数（重开代次的确定性生成，重放稳定）。"""
        count = 0
        for event in self._run_events():
            if event.event_type != "graph.transition.accepted":
                continue
            payload = event.payload
            if (
                payload.get("family") == "project"
                and payload.get("to_state") == source_state
            ):
                count += 1
        return count

    def _last_accepted_reopen(self) -> tuple[str, int] | None:
        """最近一次被接受的项目重开：(源状态, 该源状态进入代次)；事件流重建。"""
        entry_counts: dict[str, int] = {}
        last: tuple[str, int] | None = None
        for event in self._run_events():
            if event.event_type != "graph.transition.accepted":
                continue
            payload = event.payload
            if payload.get("family") != "project":
                continue
            to_state = payload.get("to_state")
            from_state = payload.get("from_state")
            if to_state in ("blocked", "partial_delivery_blocked", "awaiting_user"):
                key = str(to_state)
                entry_counts[key] = entry_counts.get(key, 0) + 1
            if (
                to_state == "running"
                and from_state in ("blocked", "partial_delivery_blocked", "awaiting_user")
            ):
                key = str(from_state)
                last = (key, entry_counts.get(key, 0))
        return last

    @staticmethod
    def _blocked_epoch(
        view: _CoordinatorView,
        family: str,
        object_id: str,
    ) -> int:
        return len(view.blocked_entry_sequences.get((family, object_id), ()))

    def _version_at_blocked(
        self,
        view: _CoordinatorView,
        family: str,
        object_id: str,
        contract_id: str,
    ) -> int | None:
        """进入阻断态时生效的合同版本。

        优先取阻断事件守卫证据中的 contract_version；缺失时按事件位置取该
        合同在阻断事件之前最近的已绑定版本（选择绑定事件序号 <= 阻断事件
        序号）；仍无则 None（新合同版本重开无法证明 → 失败关闭）。
        """
        entries = view.blocked_entry_sequences.get((family, object_id), ())
        if not entries:
            return None
        blocked_seq, version = entries[-1]
        if version is not None:
            return version
        latest: int | None = None
        for (contract, bound_version), bound_seq in view.binding_sequences.items():
            if (
                contract == contract_id
                and bound_seq <= blocked_seq
                and (latest is None or bound_version > latest)
            ):
                latest = bound_version
        return latest

    def _blocked_entry_info(
        self,
        view: _CoordinatorView,
        family: str,
        object_id: str,
    ) -> tuple[int, int | None]:
        """(阻断进入代次, 进入当前阻断态时的合同版本) 由校验后的视图确定性派生。"""
        entries = view.blocked_entry_sequences.get((family, object_id), ())
        epoch = len(entries)
        version = entries[-1][1] if entries else None
        return epoch, version

    def _project_evidence(
        self,
        contract: DeliveryContract,
        project_object_id: str,
        conditions: DeliveryConditions,
        view: _CoordinatorView,
    ) -> dict[str, object]:
        evidence = self._contract_evidence(contract, "project", project_object_id, view)
        evidence["target_status"] = self._target_status(conditions)
        for key in self._aggregate_guard_keys():
            if not hasattr(conditions, key):
                raise CoordinationError(f"聚合守卫键 {key} 无法从规范状态计算")
            evidence[key] = getattr(conditions, key)
        return evidence

    def _reopen_evidence(
        self,
        contract: DeliveryContract,
        target_family: str,
        target_object_id: str,
        reason: str,
        view: _CoordinatorView,
    ) -> dict[str, object]:
        evidence = self._contract_evidence(contract, target_family, target_object_id, view)
        evidence[reason] = True
        return evidence

    def _contract_evidence(
        self,
        contract: DeliveryContract,
        target_family: str,
        target_object_id: str,
        view: _CoordinatorView,
    ) -> dict[str, object]:
        return {
            "contract_id": contract.contract_id,
            "contract_version": contract.contract_version,
            "selection_digest": self._selection_digest(contract),
            "reports": list(contract.reports),
            "mandatory_html": MANDATORY_HTML,
            "optional_formats": list(contract.optional_formats),
            "targets": {
                kind: view.current_targets[kind] for kind in contract.reports
            },
            "target_family": target_family,
            "target_object_id": target_object_id,
        }

    @staticmethod
    def _target_status(conditions: DeliveryConditions) -> dict[str, str]:
        status = {
            object_id: state or "unseen" for object_id, state in conditions.report_states
        }
        status.update(
            {object_id: state or "unseen" for object_id, state in conditions.format_states}
        )
        return status

    @staticmethod
    def _aggregate_guard_keys() -> tuple[str, ...]:
        keys: list[str] = []
        seen: set[str] = set()
        for guard_id in _AGGREGATE_GUARD_IDS:
            spec = TRANSITION_REGISTRY.guard_spec(guard_id)
            for group in spec.required_any:
                for key in group:
                    if key not in seen:
                        seen.add(key)
                        keys.append(key)
            for key in spec.required_true:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        return tuple(keys)

    def _request(
        self,
        contract: DeliveryContract,
        *,
        family: str,
        object_id: str,
        from_state: str,
        to_state: str,
        trigger: str,
        evidence: dict[str, object],
        actor_id: str,
        occurred_at: datetime,
        identity_parts: tuple[str, ...],
    ) -> TransitionRequest:
        project_id = self._resolve_project_id()
        return TransitionRequest(
            schema_version="1.0",
            request_id=self._request_id(contract, identity_parts),
            project_id=project_id,
            run_id=self.run_id,
            family=family,
            object_id=object_id,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            evidence=evidence,
            actor_id=actor_id,
            occurred_at=occurred_at,
        )

    def _selection_digest(self, contract: DeliveryContract) -> str:
        return _selection_digest_of(
            contract.contract_id,
            contract.contract_version,
            contract.reports,
            contract.optional_formats,
        )


__all__ = [
    "CoordinationError",
    "ContractDriftError",
    "CoordinationResult",
    "CoordinatorEventContractError",
    "DeliveryConditions",
    "DeliveryContract",
    "DeliveryTarget",
    "FORMAT_REOPEN_REASONS",
    "InconsistentStateError",
    "MANDATORY_HTML",
    "PROJECT_REOPEN_REASONS",
    "PartialDeliveryCoordinator",
    "REBIND_EVENT",
    "ReportTarget",
    "SELECTION_BOUND_EVENT",
    "format_object_id",
    "matrix_targets",
    "report_target",
    "report_version_target",
]
