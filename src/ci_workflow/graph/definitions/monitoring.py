"""Task 9.3 可选监测控制图定义：六个监测节点合同与可卸载边界。

监测是可选叶子能力：本模块只声明合同——读取监测范围、执行来源观察、
归一化与去重、记录候选/诊断、等待用户处置、生成刷新交接。节点执行、
候选投影、追加事件与幂等恢复由 ``application/monitoring_service.py``
持有；宿主调度属于 Task 9.4，这里不实现。

节点输出不含事实、声明、快照、报告或发布能力：全部节点副作用类为
``none``，只写 ``monitoring.*`` 状态键，绝不写证据、门槛、快照、质控、
分析或产物键，也不读写修订审批族——候选必须经用户"启动正常刷新"进入
Task 9.2 刷新流程重新核验，不得直接进入修订批准流。

本模块不得被核心项目服务、刷新服务、修订服务或 ``graph/__init__``
反向导入；删除监测模块或监测 Skill 不影响新建、打开、恢复与手动刷新
（可卸载性由 ``tests/graph/test_monitoring_uninstallable.py`` 钉死）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, get_args

from ci_workflow.domain.monitoring import ObservationOutcome, UserDisposition
from ci_workflow.graph.definitions.new_report import NEW_REPORT_NODES
from ci_workflow.graph.definitions.refresh import REFRESH_NODES
from ci_workflow.graph.types import NodeContract, RetryPolicy, TypedField

__all__ = [
    "DISPOSITION_DEFER",
    "DISPOSITION_START_REFRESH",
    "HANDOFF_TARGET_NORMAL_REFRESH",
    "MONITORING_DISPOSITIONS",
    "MONITORING_NODE_IDS",
    "MONITORING_NODES",
    "MONITORING_OUTCOMES",
    "MONITORING_STATE_PREFIX",
    "OUTCOME_CHANGED",
    "OUTCOME_NEEDS_USER",
    "OUTCOME_NO_CHANGE",
    "OUTCOME_NOT_PUBLIC",
    "OUTCOME_TECHNICAL_FAILURE",
    "monitoring_node_contract",
]

# ── 状态键前缀与封闭词表 ─────────────────────────────────────────────────

# 监测节点只写 monitoring.* 键；核心真源键（证据/门槛/快照/质控/分析/
# 产物）与运行状态族一律不写，"project" 仅作为只读项目合同身份。
MONITORING_STATE_PREFIX = "monitoring."

# 观察结果封闭词表：与域合同 ``domain/monitoring.py`` 的
# ``ObservationOutcome`` 逐字对齐（导入期核对漂移）。技术获取失败与
# "已检索但未发现变化/未公开"严格区分；恢复尝试未穷尽时不得标为
# 需要用户协助（由监测服务在记录时失败关闭）。
OUTCOME_CHANGED = "change_found"
OUTCOME_NO_CHANGE = "no_change"
OUTCOME_NOT_PUBLIC = "confirmed_not_public"
OUTCOME_TECHNICAL_FAILURE = "technical_failure_recoverable"
OUTCOME_NEEDS_USER = "needs_user_assistance"
MONITORING_OUTCOMES: tuple[str, ...] = (
    OUTCOME_CHANGED,
    OUTCOME_NO_CHANGE,
    OUTCOME_NOT_PUBLIC,
    OUTCOME_TECHNICAL_FAILURE,
    OUTCOME_NEEDS_USER,
)

# 用户处置封闭词表：与域合同 ``UserDisposition`` 对齐（"pending" 是初始
# 状态而非用户决定，不在本词表）；处置是追加事件，只有启动正常刷新
# 与暂不处理两种用户决定。
DISPOSITION_START_REFRESH = "start_normal_refresh"
DISPOSITION_DEFER = "deferred"
MONITORING_DISPOSITIONS: tuple[str, ...] = (DISPOSITION_START_REFRESH, DISPOSITION_DEFER)

# 刷新交接唯一去向：Task 9.2 正常刷新输入合同；不是修订批准流。
HANDOFF_TARGET_NORMAL_REFRESH = "normal_refresh"

# 监测节点输出不得携带的能力词：任何命中即说明节点获得了接纳事实、
# 建立快照或发布报告的能力，导入期失败关闭。
_FORBIDDEN_OUTPUT_NAME_FRAGMENTS: tuple[str, ...] = (
    "publish",
    "approv",
    "accept",
    "snapshot",
    "fact",
    "claim",
    "revision",
)
_FORBIDDEN_OUTPUT_TYPES: frozenset[str] = frozenset(
    {"evidencereference", "qcverificationreference"}
)

_IDEMPOTENCY_MATERIAL: tuple[str, ...] = (
    "project_id",
    "run_id",
    "node_id",
    "input_digest",
)


def _field(name: str, type_: str, description: str) -> TypedField:
    return TypedField(name=name, type=type_, description=description)


def _completion_requires(*fields: str) -> Callable[[dict[str, Any]], bool]:
    """完成谓词：全部声明输出存在且非 None 才视为完成。"""

    def predicate(outputs: dict[str, Any]) -> bool:
        return all(outputs.get(field) is not None for field in fields) and bool(fields)

    return predicate


MONITORING_NODES: tuple[NodeContract, ...] = (
    # ── 读取监测范围：既有项目合同 + 可变来源清单（只读） ─────────────────
    NodeContract(
        node_id="monitor_scope",
        version="1.0",
        typed_inputs=(
            _field("project_id", "str", "既有项目稳定标识（只读绑定）"),
            _field(
                "monitoring_scope",
                "dict[str, object]",
                "监测范围：可变来源清单、实体范围、上次数据截止时间与监测频率",
            ),
        ),
        typed_outputs=(
            _field("scope_receipt_id", "str", "监测范围回执标识（追加保存）"),
            _field("observable_source_ids", "tuple[str]", "本次待观察的可变来源稳定标识"),
            _field("last_cutoff", "str", "上次数据截止时间，观察不得早于该时间"),
        ),
        completion_predicate=_completion_requires(
            "scope_receipt_id", "observable_source_ids", "last_cutoff"
        ),
        completion_summary="读取既有项目合同与监测范围；项目合同只读，不改变项目状态",
        reads=("project",),
        writes=(f"{MONITORING_STATE_PREFIX}scope",),
        retry_policy=RetryPolicy(1, 0.0, ("ValueError",)),
        declared_errors=("MonitoringScopeError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 执行来源观察：接收调用方已完成的观察，四类结果可区分 ──────────────
    NodeContract(
        node_id="monitor_observe",
        version="1.0",
        typed_inputs=(
            _field("scope_receipt_id", "str", "监测范围回执标识"),
            _field(
                "source_observations",
                "dict[str, object]",
                "调用方已完成的来源观察结果；本节点不执行网络抓取",
            ),
        ),
        typed_outputs=(
            _field("observation_receipt_id", "str", "来源观察回执标识（追加保存）"),
            _field("changed_source_ids", "tuple[str]", "已完成并发现变化的来源标识"),
            _field("unchanged_source_ids", "tuple[str]", "已完成但无变化的来源标识；空候选不创建"),
            _field("not_public_source_ids", "tuple[str]", "来源确认未公开目标信息的来源标识"),
            _field(
                "failed_source_ids", "tuple[str]", "技术获取失败的来源标识；与未发现变化严格区分"
            ),
        ),
        completion_predicate=_completion_requires(
            "observation_receipt_id",
            "changed_source_ids",
            "unchanged_source_ids",
            "not_public_source_ids",
            "failed_source_ids",
        ),
        completion_summary="登记来源观察回执；技术失败与已检索未发现/未公开严格区分，不混报",
        reads=(f"{MONITORING_STATE_PREFIX}scope",),
        writes=(f"{MONITORING_STATE_PREFIX}observations",),
        retry_policy=RetryPolicy(3, 2.0, ("TransientError", "RateLimitError")),
        declared_errors=("SourceObservationError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 归一化与去重：稳定摘要派生候选身份，重复发现合并 ──────────────────
    NodeContract(
        node_id="monitor_dedupe",
        version="1.0",
        typed_inputs=(
            _field("project_id", "str", "既有项目稳定标识"),
            _field(
                "normalized_observations",
                "dict[str, object]",
                "归一化后的变化观察：来源身份/版本/定位、实体、声明域、变化类型、当前值与候选值",
            ),
            _field("existing_candidate_ids", "tuple[str]", "既有候选标识，用于重复发现合并"),
        ),
        typed_outputs=(
            _field("dedupe_receipt_id", "str", "去重回执标识（追加保存）"),
            _field("new_candidate_ids", "tuple[str]", "新业务变化形成的候选标识"),
            _field(
                "merged_candidate_ids",
                "tuple[str]",
                "重复发现映射到的既有候选标识；同一变化不重复建候选、不重复提醒",
            ),
        ),
        completion_predicate=_completion_requires(
            "dedupe_receipt_id", "new_candidate_ids", "merged_candidate_ids"
        ),
        completion_summary="按稳定去重摘要归并重复发现；同一业务变化只保留一个候选身份",
        reads=(f"{MONITORING_STATE_PREFIX}observations", f"{MONITORING_STATE_PREFIX}candidates"),
        writes=(f"{MONITORING_STATE_PREFIX}candidates",),
        retry_policy=RetryPolicy(1, 0.0, ("DedupeDigestError",)),
        declared_errors=("DedupeDigestError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 记录候选/诊断：追加事件与候选投影；输出中文用户指引 ────────────────
    NodeContract(
        node_id="monitor_record",
        version="1.0",
        typed_inputs=(
            _field("project_id", "str", "既有项目稳定标识"),
            _field(
                "candidate_payloads",
                "dict[str, object]",
                "候选材料：来源/版本/定位、发现时间、实体与声明域、变化类型、当前值与候选值、获取/诊断状态",
            ),
            _field("observation_receipt_id", "str", "来源观察回执标识"),
        ),
        typed_outputs=(
            _field(
                "recorded_candidate_ids",
                "tuple[str]",
                "已记录候选标识；投影不可覆盖、可由事件流恢复",
            ),
            _field(
                "diagnosis_categories",
                "tuple[str]",
                "按封闭词表归类的诊断类别；技术失败不得记为未发现变化",
            ),
            _field(
                "user_guidance_zh",
                "str",
                "中文用户指引：说明发现了什么变化、可能影响哪里、当前能否核验、下一步可做什么",
            ),
            _field(
                "possibly_affected_reports",
                "tuple[ReportKind]",
                "可能受影响的报告引用集合（仅提示，不代表任何报告被改动）",
            ),
            _field(
                "possibly_affected_page_ids",
                "tuple[str]",
                "可能受影响的页面引用集合（仅提示，不代表任何页面被改动）",
            ),
        ),
        completion_predicate=_completion_requires(
            "recorded_candidate_ids",
            "diagnosis_categories",
            "user_guidance_zh",
            "possibly_affected_reports",
            "possibly_affected_page_ids",
        ),
        completion_summary="追加记录候选与诊断并生成中文用户指引；不写事实、声明、快照或报告",
        reads=(f"{MONITORING_STATE_PREFIX}candidates",),
        writes=(
            f"{MONITORING_STATE_PREFIX}candidates",
            f"{MONITORING_STATE_PREFIX}diagnostics",
        ),
        retry_policy=RetryPolicy(1, 0.0, ("CandidateRecordingError",)),
        declared_errors=("CandidateRecordingError", "DiagnosisClassificationError"),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 等待用户处置：只有启动正常刷新与暂不处理，追加且幂等 ───────────────
    NodeContract(
        node_id="monitor_await_disposition",
        version="1.0",
        typed_inputs=(
            _field("candidate_ids", "tuple[str]", "待处置候选标识"),
            _field("requested_disposition", "str", "用户显式处置：启动正常刷新或暂不处理"),
            _field("requested_by", "str", "处置用户标识"),
        ),
        typed_outputs=(
            _field("disposition", "str", "按封闭词表落账的用户处置"),
            _field(
                "disposition_receipt_id", "str", "处置回执标识；重放幂等，不删除候选、不改写历史"
            ),
        ),
        completion_predicate=_completion_requires("disposition", "disposition_receipt_id"),
        completion_summary="等待并登记用户处置；处置追加保存，候选与历史保留",
        reads=(f"{MONITORING_STATE_PREFIX}candidates", f"{MONITORING_STATE_PREFIX}diagnostics"),
        writes=(f"{MONITORING_STATE_PREFIX}dispositions",),
        retry_policy=RetryPolicy(1, 0.0, ("DispositionError",)),
        declared_errors=("DispositionError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 生成刷新交接：只读交接单进入 Task 9.2 正常刷新，不是修订流 ─────────
    NodeContract(
        node_id="monitor_handoff",
        version="1.0",
        typed_inputs=(
            _field("candidate_id", "str", "用户选择启动正常刷新的候选标识"),
            _field("project_id", "str", "既有项目稳定标识"),
            _field("contract_version", "str", "交接绑定的当前合同版本"),
            _field("source_identity", "dict[str, object]", "候选绑定的来源稳定身份/版本/定位"),
            _field(
                "suggested_review_scope", "tuple[str]", "建议复核范围（仅建议，刷新时仍需重新核验）"
            ),
        ),
        typed_outputs=(
            _field("handoff_id", "str", "内容寻址的只读刷新交接单标识"),
            _field("handoff_digest", "str", "交接单内容摘要；重放同载荷返回同一交接单"),
            _field("bound_contract_version", "str", "交接单绑定的当前合同版本"),
        ),
        completion_predicate=_completion_requires(
            "handoff_id", "handoff_digest", "bound_contract_version"
        ),
        completion_summary="生成绑定项目、候选与合同版本的只读刷新交接单；不接纳事实、不建快照、不发布报告",
        reads=(
            f"{MONITORING_STATE_PREFIX}candidates",
            f"{MONITORING_STATE_PREFIX}dispositions",
        ),
        writes=(f"{MONITORING_STATE_PREFIX}handoffs",),
        retry_policy=RetryPolicy(1, 0.0, ("RefreshHandoffError",)),
        declared_errors=("RefreshHandoffError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
)


def _validate_monitoring_graph_contract() -> None:
    """导入期核对：节点唯一、不与核心图冲突、无越权读写或输出能力。"""
    node_ids = tuple(contract.node_id for contract in MONITORING_NODES)
    if len(set(node_ids)) != len(node_ids):
        raise ValueError("监测节点标识不得重复")
    core_ids = {contract.node_id for contract in (*NEW_REPORT_NODES, *REFRESH_NODES)}
    conflict = core_ids & set(node_ids)
    if conflict:
        raise ValueError(f"监测节点标识与核心图冲突: {sorted(conflict)}")

    allowed_reads = {"project", f"{MONITORING_STATE_PREFIX}scope"}
    for contract in MONITORING_NODES:
        for key in contract.writes:
            if not key.startswith(MONITORING_STATE_PREFIX):
                raise ValueError(f"{contract.node_id} 试图写监测以外的状态键: {key}")
        for key in contract.reads:
            if not key.startswith(MONITORING_STATE_PREFIX) and key not in allowed_reads:
                raise ValueError(f"{contract.node_id} 读取了监测边界外的状态键: {key}")
        if contract.side_effect_class != "none":
            raise ValueError(
                f"{contract.node_id} 监测节点不得声明副作用: {contract.side_effect_class}"
            )
        if contract.scope != "shared":
            raise ValueError(f"{contract.node_id} 监测节点必须是项目级共享作用域")
        for field in contract.typed_outputs:
            lowered = field.name.lower()
            if any(fragment in lowered for fragment in _FORBIDDEN_OUTPUT_NAME_FRAGMENTS):
                raise ValueError(f"{contract.node_id} 输出携带越权能力词: {field.name}")
            if field.type.strip().lower() in _FORBIDDEN_OUTPUT_TYPES:
                raise ValueError(f"{contract.node_id} 输出使用越权类型: {field.name}")


def _validate_vocabulary_alignment() -> None:
    """导入期核对：图词表必须是域合同 ``domain/monitoring.py`` 词表的子集。

    图节点合同与域机器合同由不同工件承载，此处逐字核对防止两条词表
    漂移；域合同新增取值不强制图立刻跟随，但图声明的每个取值必须在
    域合同中存在。
    """
    domain_outcomes = set(get_args(ObservationOutcome))
    graph_outcomes = set(MONITORING_OUTCOMES)
    if not graph_outcomes <= domain_outcomes:
        raise ValueError(f"图观察结果词表漂移于域合同: {sorted(graph_outcomes - domain_outcomes)}")
    domain_dispositions = set(get_args(UserDisposition))
    graph_dispositions = set(MONITORING_DISPOSITIONS)
    if not graph_dispositions <= domain_dispositions:
        raise ValueError(
            f"图用户处置词表漂移于域合同: {sorted(graph_dispositions - domain_dispositions)}"
        )


_validate_vocabulary_alignment()
_validate_monitoring_graph_contract()

MONITORING_NODE_IDS: tuple[str, ...] = tuple(contract.node_id for contract in MONITORING_NODES)


def monitoring_node_contract(node_id: str) -> NodeContract:
    """按 node_id 取监测节点合同；未知节点失败关闭。"""
    for contract in MONITORING_NODES:
        if contract.node_id == node_id:
            return contract
    raise ValueError(f"未知监测图节点: {node_id}")
