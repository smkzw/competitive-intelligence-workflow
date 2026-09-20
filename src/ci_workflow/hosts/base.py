"""Task 9.4 宿主适配器共享合同与薄基类。

依据设计合同（Task 9.4 design.md「单一语义合同」）：

- ``HostAdapter`` 接收规范化最小输入和既有项目路径，只返回宿主调用计划、
  中文状态消息、中断/恢复映射和产物定位。
- ``HostSemanticReceipt`` 是三宿主一致性的比较面：最小输入、能力选择、
  规范状态、阻断/恢复、部分交付和产物摘要。
- 宿主名称、可执行文件、真实路径、进程和会话属于 ``HostRunIdentity``
  运行身份，不参与科学语义摘要。

权能边界（验收标准 1）：本层只复用公共 capability preflight、规范事件流
与检查点存储和公共 CLI 入口；不得导入门槛评估器、来源策略写入、事实/
声明存储、快照锁定、修订批准或报告渲染内部实现，也不复制业务逻辑。
关键证据不足时的 no-draft、事件与检查点写入均由公共执行器负责，适配器
只把规范状态翻译成中文宿主消息。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.application.capability_preflight import (
    CAPABILITY_ACTIONS,
    CAPABILITY_LABELS,
    CapabilityMatrix,
    CapabilityProbe,
    CapabilitySelection,
    HostName,
    MatrixState,
    plan_environment_recovery,
    run_capability_preflight,
    selection_from_project,
)
from ci_workflow.application.delivered_artifacts import read_accepted_html_artifacts
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.storage.event_store import EventStore, StoredWorkflowEvent

ReportName = Literal["A", "B", "C"]
OutputName = Literal["html"]
CanonicalProjectState = Literal[
    "not_started",
    "running",
    "awaiting_user",
    "partially_delivered",
    "blocked",
    "complete",
]
FailureClass = Literal[
    "none",
    "awaiting_user_materials",
    "insufficient_key_evidence",
    "capability_blocked",
]

# 主对话只报告已启动、重要里程碑、需要用户资料、部分完成、阻断和全部完成
# （prd.md 用户体验）；此处是三宿主共享的规范状态中文映射。
CANONICAL_STATE_MESSAGES_ZH: dict[CanonicalProjectState, str] = {
    "not_started": "项目已创建，尚未开始调研。",
    "running": "调研正在进行，完成后会通知您。",
    "awaiting_user": "需要您补充关键资料后才能继续。",
    "partially_delivered": "部分报告已交付，其余部分待恢复后继续。",
    "blocked": "关键证据不足，按规则不生成草稿报告。",
    "complete": "全部报告已完成交付。",
}

# 手工收件箱请求状态的用户可见中文名（不暴露后端状态词）。
DOWNLOAD_STATE_LABELS_ZH: dict[str, str] = {
    "awaiting_user": "等待您放入文件",
    "file_detected": "已发现文件，正在核对",
    "matched": "已核对匹配，正在接受",
    "needs_re_download": "需要重新下载后放入",
    "accepted": "已接受",
    "not_required": "不再需要",
}

# 手工收件箱中需要用户动作的活跃状态。
_ACTIVE_DOWNLOAD_STATES = frozenset(
    {"awaiting_user", "file_detected", "matched", "needs_re_download"}
)


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("宿主合同字段不能为空")
    return normalized


class MinimalUserInput(BaseModel):
    """规范化最小用户输入：报告类型、适应症与输出选择（首版站点式 HTML）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    reports: tuple[ReportName, ...] = Field(min_length=1)
    indication: str
    outputs: tuple[OutputName, ...] = Field(min_length=1)

    @field_validator("indication")
    @classmethod
    def _indication_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("reports", "outputs")
    @classmethod
    def _values_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("最小输入选择项不能重复")
        return values

    @model_validator(mode="after")
    def _html_is_first_output(self) -> MinimalUserInput:
        if self.outputs[0] != "html":
            raise ValueError("首版真实交付必须是站点式 HTML")
        return self


class CapabilityStateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability_id: str
    state: Literal["ready", "blocked", "not_applicable"]


class ResearchReadinessRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportName
    state: Literal["ready", "blocked"]
    blocked_by: tuple[str, ...]


class DeliveryReadinessRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportName
    output: OutputName
    state: Literal["ready", "blocked"]
    blocked_by: tuple[str, ...]


class CapabilitySelectionSummary(BaseModel):
    """能力选择摘要：三宿主共享 capability preflight 的矩阵投影。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    overall_state: MatrixState
    capability_states: tuple[CapabilityStateRecord, ...]
    research_states: tuple[ResearchReadinessRecord, ...]
    delivery_states: tuple[DeliveryReadinessRecord, ...]
    user_messages_zh: tuple[str, ...]


class ManualInboxPendingItem(BaseModel):
    """手工收件箱活跃请求的用户可见摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    title: str
    reason_zh: str
    inbox_directory: str
    state_zh: str


class BlockingAndRecovery(BaseModel):
    """阻断/恢复映射：失败分类、中文原因、用户行动与恢复重排计划。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_class: FailureClass
    reasons_zh: tuple[str, ...]
    user_actions_zh: tuple[str, ...]
    manual_inbox_pending: tuple[ManualInboxPendingItem, ...]
    recovery_requeue_node_ids: tuple[str, ...]


class DeliveredArtifact(BaseModel):
    """已交付产物摘要：项目相对入口路径与内容摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportName
    output: OutputName
    entry_relative_path: str
    entry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PendingReportOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportName
    output: OutputName


class PartialDeliverySummary(BaseModel):
    """部分交付摘要：已交付产物与选择中尚未交付的报告/格式。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    delivered: tuple[DeliveredArtifact, ...]
    pending: tuple[PendingReportOutput, ...]


class HostSemanticReceipt(BaseModel):
    """三宿主一致性比较面；不包含宿主运行身份字段。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    minimal_input: MinimalUserInput
    capability_selection: CapabilitySelectionSummary
    canonical_state: CanonicalProjectState
    blocking_and_recovery: BlockingAndRecovery
    partial_delivery: PartialDeliverySummary | None
    artifacts: tuple[DeliveredArtifact, ...]
    primary_status_zh: str


class HostRunIdentity(BaseModel):
    """宿主运行身份：宿主、安装入口、可执行文件与会话通道。

    运行身份不参与 ``HostSemanticReceipt`` 语义比较；真实安装入口、外部
    进程与版本验证属于 host-smoke 真实入口 runner（HA09），本结构只承载
    源码级可确定的定位结果。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: HostName
    host_label_zh: str
    session_channel: str
    executable: str | None
    install_entry: str | None


class HostInvocationPlan(BaseModel):
    """宿主内启动/恢复工作流的公共 CLI 调用计划（运行身份层面）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: HostName
    create_command: tuple[str, ...] | None = None
    preflight_command: tuple[str, ...]
    run_command: tuple[str, ...]
    resume_command: tuple[str, ...]


def _canonical_project_state(
    events: tuple[StoredWorkflowEvent, ...],
) -> CanonicalProjectState:
    """从规范事件流机械推导项目最后状态（family=project，last-wins）。"""
    state: str | None = None
    for event in events:
        if (
            event.event_type == "graph.transition.accepted"
            and event.payload.get("family") == "project"
        ):
            state = str(event.payload["to_state"])
    if state is None:
        return "not_started"
    allowed: tuple[CanonicalProjectState, ...] = (
        "running",
        "awaiting_user",
        "partially_delivered",
        "blocked",
        "complete",
    )
    if state not in allowed:
        raise ValueError(f"未声明的项目规范状态：{state}")
    return state  # pyright: ignore[reportReturnType]


def _manual_inbox_pending(project_root: Path) -> tuple[ManualInboxPendingItem, ...]:
    """读取项目手工收件箱中的活跃请求（复用 receipts 真源，不重复状态机）。"""
    requests_path = project_root / "receipts" / "download_requests.jsonl"
    if not requests_path.is_file():
        return ()
    items: list[ManualInboxPendingItem] = []
    for line in requests_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            state_value = str(record.get("state", ""))
            if state_value not in _ACTIVE_DOWNLOAD_STATES:
                continue
            items.append(
                ManualInboxPendingItem(
                    request_id=str(record["request_id"]),
                    title=str(record["title"]),
                    reason_zh=str(record["reason_zh"]),
                    inbox_directory=str(record["inbox_directory"]),
                    state_zh=DOWNLOAD_STATE_LABELS_ZH[state_value],
                )
            )
        except (json.JSONDecodeError, KeyError) as error:
            raise ValueError("待补充资料记录无效，无法向宿主呈现收件箱状态") from error
    return tuple(items)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _delivered_artifacts(
    project_root: Path, selection: CapabilitySelection
) -> tuple[DeliveredArtifact, ...]:
    """按项目相对约定定位站点式 HTML 产物入口并绑定内容摘要。

    首版真实输出只有站点式 HTML（格式裁决），因此产物摘要只覆盖 html。
    """
    artifacts: list[DeliveredArtifact] = []
    for manifest in read_accepted_html_artifacts(project_root):
        if "html" not in selection.outputs or manifest.report not in selection.reports:
            continue
        entry = project_root / manifest.artifact.relative_path / "index.html"
        artifacts.append(
            DeliveredArtifact(
                report=manifest.report,
                output="html",
                entry_relative_path=entry.relative_to(project_root).as_posix(),
                entry_sha256=_sha256_file(entry),
            )
        )
    return tuple(artifacts)


def _capability_selection_summary(
    matrix: CapabilityMatrix,
) -> CapabilitySelectionSummary:
    return CapabilitySelectionSummary(
        overall_state=matrix.overall_state,
        capability_states=tuple(
            CapabilityStateRecord(capability_id=item.capability_id, state=item.state)
            for item in matrix.capabilities
        ),
        research_states=tuple(
            ResearchReadinessRecord(
                report=item.report, state=item.state, blocked_by=item.blocked_by
            )
            for item in matrix.research
        ),
        delivery_states=tuple(
            DeliveryReadinessRecord(
                report=item.report,
                output=item.output,
                state=item.state,
                blocked_by=item.blocked_by,
            )
            for item in matrix.deliveries
        ),
        user_messages_zh=matrix.user_messages,
    )


def _blocking_and_recovery(
    *,
    canonical_state: CanonicalProjectState,
    matrix: CapabilityMatrix,
    manual_inbox_pending: tuple[ManualInboxPendingItem, ...],
    previous_matrix: CapabilityMatrix | None,
) -> BlockingAndRecovery:
    """把规范阻断状态与能力矩阵翻译为共享失败分类、原因与用户行动。

    分类优先级以规范事件流（项目真源）为先：关键证据阻断与等待用户材料
    来自公共执行器写入的项目状态；能力缺失只在项目未因证据阻断时呈现，
    且只阻断依赖该能力的报告/格式（选择性阻断）。
    """
    reasons: list[str] = []
    actions: list[str] = []
    if canonical_state == "awaiting_user":
        failure_class: FailureClass = "awaiting_user_materials"
        reasons.append("自动检索穷尽后仍有少量关键原文无法公开获取。")
        actions.append("请按待补充资料清单把原文文件放入对应收件目录，无需重命名。")
    elif canonical_state == "blocked":
        failure_class = "insufficient_key_evidence"
        reasons.append("关键证据不足，按证据门槛不生成草稿报告。")
        actions.append("请补充可公开核对的原始文献或登记材料，之后从同一项目恢复。")
    elif matrix.overall_state != "ready":
        failure_class = "capability_blocked"
    else:
        failure_class = "none"

    if failure_class in ("capability_blocked", "none"):
        for item in matrix.capabilities:
            if item.state != "blocked":
                continue
            reasons.append(
                f"{CAPABILITY_LABELS[item.capability_id]}暂时不可用：{item.detail}"
            )
            actions.append(CAPABILITY_ACTIONS[item.capability_id])
        if failure_class == "capability_blocked" and not reasons:
            reasons.append("所选交付格式所需能力暂不可用。")

    recovery_nodes: tuple[str, ...] = ()
    if previous_matrix is not None:
        recovery_nodes = plan_environment_recovery(previous_matrix, matrix).requeue_node_ids

    return BlockingAndRecovery(
        failure_class=failure_class,
        reasons_zh=tuple(dict.fromkeys(reasons)),
        user_actions_zh=tuple(dict.fromkeys(actions)),
        manual_inbox_pending=manual_inbox_pending,
        recovery_requeue_node_ids=recovery_nodes,
    )


def _partial_delivery_summary(
    *,
    canonical_state: CanonicalProjectState,
    artifacts: tuple[DeliveredArtifact, ...],
    selection: CapabilitySelection,
) -> PartialDeliverySummary | None:
    """仅部分交付状态需要摘要；已交付与待恢复都按同一选择推导。"""
    if canonical_state != "partially_delivered":
        return None
    delivered_keys = {(item.report, item.output) for item in artifacts}
    pending = tuple(
        PendingReportOutput(report=report, output=output)
        for report in selection.reports
        for output in selection.outputs
        if (report, output) not in delivered_keys
    )
    return PartialDeliverySummary(
        delivered=tuple(
            item for item in artifacts if (item.report, item.output) in delivered_keys
        ),
        pending=pending,
    )


class HostBoundaryError(RuntimeError):
    """宿主适配器越权：新增公共成员、覆写共享语义面或声明非法宿主名。"""


# 三宿主真实名（HA02–HA04 适配器必须且只能声明其中之一）。
HOST_ADAPTER_NAMES: tuple[str, ...] = ("codex", "hermes", "omp")

# 设计合同 §6.3 明令禁止的科学越权操作：适配器以此命名任何公共成员都会
# 在类定义时失败关闭，错误信息直接引用被违反的合同句。
FORBIDDEN_HOST_OPERATIONS: Mapping[str, str] = {
    "set_source_weight": "宿主适配器不得改变来源权重",
    "override_evidence_threshold": "宿主适配器不得改变证据门槛",
    "reclassify_failure": "宿主适配器不得改变错误分类",
    "rewrite_snapshot": "宿主适配器不得改变快照内容",
    "override_acceptance": "宿主适配器不得改变验收标准",
}

# 共享语义面与调用计划方法：三宿主一致的六类薄操作全部由基类承担，
# 子类不得覆写（prd 验收 1；宿主差异只允许留在运行身份）。
HOST_SHARED_SEMANTIC_SURFACE: frozenset[str] = frozenset(
    {
        "resolve_minimal_input",
        "capability_matrix",
        "build_semantic_receipt",
        "resolve_executable",
        "resolve_install_entry",
        "run_identity",
        "invocation_plan",
    }
)

# 子类必须实现的运行身份钩子（宿主差异的唯一合法落点）。
HOST_RUN_IDENTITY_HOOKS: frozenset[str] = frozenset(
    {"executable_candidates", "install_entry_candidates", "session_channel"}
)

# 基类冻结公共面：共享语义方法 + 运行身份钩子 + 身份 ClassVar。
HOST_ADAPTER_PUBLIC_API: frozenset[str] = (
    HOST_SHARED_SEMANTIC_SURFACE | HOST_RUN_IDENTITY_HOOKS | {"host", "host_label_zh"}
)

# 这些特殊方法可截获基类的属性读取、能力探针注入或对象序列化，等同于
# 绕过薄适配器权能边界。普通私有数据/辅助函数仍可保留。
HOST_ADAPTER_FORBIDDEN_SPECIAL_METHODS: frozenset[str] = frozenset(
    {
        "__setattr__",
        "__getattribute__",
        "__getattr__",
        "__delattr__",
        "__getstate__",
        "__setstate__",
        "__reduce__",
        "__reduce_ex__",
    }
)


class HostAdapter(ABC):
    """三宿主共享的薄适配器基类。

    语义面（最小输入解析、能力选择、规范状态、中断/恢复映射、产物定位）
    全部由本类基于公共设施组装，子类不得覆写，保证三宿主语义一致；子类
    只提供运行身份（可执行文件、安装入口、会话通道）。

    越权在类定义与实例化时失败关闭（``__init_subclass__`` / ``__init__``）：
    适配器新增公共成员、覆写共享语义面、覆写构造函数或声明
    ``codex/hermes/omp`` 之外的宿主名都会立即报 ``HostBoundaryError``。
    """

    host: ClassVar[HostName]
    host_label_zh: ClassVar[str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        """薄适配器合同是结构约束而非文档约定：越权子类无法完成类定义。"""
        super().__init_subclass__(**kwargs)
        if "__init__" in cls.__dict__:
            raise HostBoundaryError("宿主适配器不得覆写构造函数；初始化只属于共享基类")
        for name, value in cls.__dict__.items():
            if name in HOST_ADAPTER_FORBIDDEN_SPECIAL_METHODS:
                raise HostBoundaryError(
                    f"宿主适配器不得覆写可截获共享状态的特殊方法：{name}"
                )
            if name.startswith("_"):
                continue
            if name == "host":
                if value not in HOST_ADAPTER_NAMES:
                    raise HostBoundaryError(
                        f"宿主名只能是 {HOST_ADAPTER_NAMES} 之一：{value!r}"
                    )
                continue
            if name in ("host_label_zh",) or name in HOST_RUN_IDENTITY_HOOKS:
                continue
            if name in HOST_SHARED_SEMANTIC_SURFACE:
                raise HostBoundaryError(f"宿主适配器不得覆写共享语义面方法：{name}")
            forbidden = FORBIDDEN_HOST_OPERATIONS.get(name)
            if forbidden is not None:
                raise HostBoundaryError(
                    f"适配器公共成员 {name} 越权：{forbidden}（设计合同 §6.3）"
                )
            raise HostBoundaryError(
                f"宿主适配器不得新增公共成员 {name}；适配器只能实现运行身份钩子，"
                "语义一律来自共享基类（prd 验收 1）"
            )
        for name in cls.__dict__.get("__annotations__", {}):
            if not name.startswith("_") and name not in HOST_ADAPTER_PUBLIC_API:
                raise HostBoundaryError(
                    f"宿主适配器不得新增公共属性声明 {name}；宿主差异只允许是运行身份"
                )

    def __init__(self, *, probe: CapabilityProbe | None = None) -> None:
        host = getattr(self, "host", None)
        if host not in HOST_ADAPTER_NAMES:
            raise HostBoundaryError(
                f"宿主适配器必须声明 {HOST_ADAPTER_NAMES} 之一作为宿主名"
            )
        label = getattr(self, "host_label_zh", None)
        if not isinstance(label, str) or not label.strip():
            raise HostBoundaryError("宿主适配器必须提供非空中文宿主显示名")
        if probe is None:
            from ci_workflow.application.capability_preflight import (
                RuntimeCapabilityProbe,
            )

            probe = RuntimeCapabilityProbe()
        self.probe = probe

    # ── 共享语义面（三宿主一致；子类不得覆写） ──────────────────────────────

    def resolve_minimal_input(self, project_root: Path) -> MinimalUserInput:
        """从既有项目合同解析规范化最小输入（项目合同是冻结真源）。"""
        contract = verify_project_workspace(project_root).contract
        return MinimalUserInput(
            schema_version="1.0",
            reports=tuple(report.value for report in contract.reports),
            indication=contract.indication,
            outputs=tuple(output.value for output in contract.outputs),
        )

    def capability_matrix(
        self, *, project_root: Path, selection: CapabilitySelection
    ) -> CapabilityMatrix:
        """复用公共 capability preflight；宿主名是唯一差异输入。"""
        return run_capability_preflight(
            selection,
            host=self.host,
            probe=self.probe,
            project_root=project_root,
        )

    def build_semantic_receipt(
        self,
        *,
        project_root: Path,
        selection: CapabilitySelection | None = None,
        previous_matrix: CapabilityMatrix | None = None,
    ) -> HostSemanticReceipt:
        """组装三宿主一致的语义回执（比较面）。"""
        effective_selection = selection or selection_from_project(project_root)
        minimal = self.resolve_minimal_input(project_root)
        matrix = self.capability_matrix(
            project_root=project_root, selection=effective_selection
        )
        events = EventStore(project_root).read_all()
        canonical_state = _canonical_project_state(events)
        artifacts = _delivered_artifacts(project_root, effective_selection)
        delivered_reports = {artifact.report for artifact in artifacts}
        all_delivered = set(effective_selection.reports) <= delivered_reports
        if canonical_state == "complete" and not all_delivered:
            canonical_state = "partially_delivered" if artifacts else "running"
        elif canonical_state == "partially_delivered" and not artifacts:
            canonical_state = "running"
        manual_inbox = _manual_inbox_pending(project_root)
        blocking = _blocking_and_recovery(
            canonical_state=canonical_state,
            matrix=matrix,
            manual_inbox_pending=manual_inbox,
            previous_matrix=previous_matrix,
        )
        partial = _partial_delivery_summary(
            canonical_state=canonical_state,
            artifacts=artifacts,
            selection=effective_selection,
        )
        return HostSemanticReceipt(
            schema_version="1.0",
            minimal_input=minimal,
            capability_selection=_capability_selection_summary(matrix),
            canonical_state=canonical_state,
            blocking_and_recovery=blocking,
            partial_delivery=partial,
            artifacts=artifacts,
            primary_status_zh=CANONICAL_STATE_MESSAGES_ZH[canonical_state],
        )

    # ── 运行身份（子类提供候选；本类解析与组装） ───────────────────────────

    @abstractmethod
    def executable_candidates(self) -> tuple[Path, ...]:
        """宿主可执行文件的候选绝对路径（按优先级）。"""

    @abstractmethod
    def install_entry_candidates(self) -> tuple[Path, ...]:
        """宿主安装入口的候选目录（按优先级）。"""

    @abstractmethod
    def session_channel(self) -> str:
        """宿主会话通道标识（运行身份，不进入语义回执）。"""

    def resolve_executable(self) -> str | None:
        """解析宿主可执行文件：先 PATH，再约定候选。"""
        which = shutil.which(self.host)
        if which:
            return which
        for candidate in self.executable_candidates():
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None

    def resolve_install_entry(self) -> str | None:
        """解析宿主安装入口 realpath。"""
        for candidate in self.install_entry_candidates():
            if candidate.is_dir():
                return str(candidate.resolve())
        return None

    def run_identity(self) -> HostRunIdentity:
        """组装宿主运行身份（HA09 真实入口 runner 复用）。"""
        return HostRunIdentity(
            host=self.host,
            host_label_zh=self.host_label_zh,
            session_channel=self.session_channel(),
            executable=self.resolve_executable(),
            install_entry=self.resolve_install_entry(),
        )

    def invocation_plan(
        self, project_root: Path, *, minimal_input: MinimalUserInput | None = None
    ) -> HostInvocationPlan:
        """宿主内启动/恢复工作流的公共 CLI 调用计划。

        三宿主调用同一公共入口；恢复绑定同一项目（公共检查点真源），
        不依赖宿主私有会话。提供 ``minimal_input`` 时（首次运行、尚无项目）
        额外给出与最小输入一一对应的项目创建命令。
        """
        root = str(project_root)
        create_command: tuple[str, ...] | None = None
        if minimal_input is not None:
            create_command = (
                "ci-workflow",
                "project",
                "create",
                "--root",
                root,
                "--indication",
                minimal_input.indication,
                "--reports",
                ",".join(minimal_input.reports),
                "--outputs",
                ",".join(minimal_input.outputs),
            )
        return HostInvocationPlan(
            host=self.host,
            create_command=create_command,
            preflight_command=(
                "ci-workflow",
                "capability",
                "preflight",
                "--host",
                self.host,
                "--project",
                root,
            ),
            run_command=("ci-workflow", "project", "run", "--root", root),
            resume_command=(
                "ci-workflow",
                "project",
                "run",
                "--root",
                root,
                "--resume",
            ),
        )
