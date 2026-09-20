"""Task 9.1 修订控制图定义：五类服务操作 → 已冻结修订迁移边的唯一绑定。

本模块不声明任何新状态规则：六种状态、八条迁移边与结构化守卫全部来自
既有 ``graph/transitions.py`` / ``graph/guards.py`` 冻结注册表。这里只把
修订服务操作（提交、补证、验证处置、报告所有者决定、发布）绑定到已声明
边，并在导入时与冻结迁移表逐边核对；缺边、漂移或重复绑定一律失败关闭，
修订服务因此不可能绕开或曲解 v1.2 字面迁移表。

提交不是迁移边：修订建议建立即处于类型化起始状态 ``submitted``
（复用 ``FAMILY_DEFAULT_STATES``，本模块不重新声明起始状态）。验证处置
与报告所有者决定各绑定不同守卫——验证本身不能批准；发布绑定唯一
``approved -> published`` 边，其守卫声明新快照、受影响产物重建与独立
质控三项前置条件，发布以批准 ID 幂等。
"""

from __future__ import annotations

from dataclasses import dataclass

from ci_workflow.graph.guards import GuardSpec
from ci_workflow.graph.registry import TRANSITION_REGISTRY
from ci_workflow.graph.state import FAMILY_DEFAULT_STATES

REVISION_FAMILY = "revision_approval"

# 五类修订服务操作（Task 9.1 设计 §服务操作）
OPERATION_SUBMIT = "submit"
OPERATION_ADD_EVIDENCE = "add_evidence"
OPERATION_VALIDATE = "validate"
OPERATION_RECORD_OWNER_DECISION = "record_owner_decision"
OPERATION_PUBLISH = "publish"

# 建议建立时的类型化起始状态：复用冻结注册表；缺失在导入时失败关闭
_raw_initial_state = FAMILY_DEFAULT_STATES[REVISION_FAMILY]
if not isinstance(_raw_initial_state, str):
    raise ValueError("修订状态族必须声明类型化起始状态")
INITIAL_STATE: str = _raw_initial_state

# 只建立起始状态、不绑定迁移边的操作
INITIAL_STATE_OPERATIONS: frozenset[str] = frozenset({OPERATION_SUBMIT})


@dataclass(frozen=True)
class CorrectionTransitionBinding:
    """修订服务操作到一条已冻结迁移边的绑定；字段与声明边逐字对应。

    ``disposition`` 是同一操作内的确定性分支标识（验证处置结果、所有者
    决定类别或发布），供服务按业务结果选择唯一迁移边。
    """

    operation: str
    disposition: str
    from_state: str
    to_state: str
    trigger: str
    guard_id: str


CORRECTION_TRANSITION_BINDINGS: tuple[CorrectionTransitionBinding, ...] = (
    # 验证处置：Agent 完成来源身份、上下文、冲突和影响核验，三种结果之一
    CorrectionTransitionBinding(
        operation=OPERATION_VALIDATE,
        disposition="needs_more_evidence",
        from_state="submitted",
        to_state="needs_evidence",
        trigger="validation_needs_evidence",
        guard_id="g_revision_submitted_needs_evidence",
    ),
    CorrectionTransitionBinding(
        operation=OPERATION_VALIDATE,
        disposition="validation_rejected",
        from_state="submitted",
        to_state="rejected",
        trigger="validation_rejected",
        guard_id="g_revision_submitted_rejected",
    ),
    CorrectionTransitionBinding(
        operation=OPERATION_VALIDATE,
        disposition="validation_passed",
        from_state="submitted",
        to_state="validated_pending_user_approval",
        trigger="validation_passed",
        guard_id="g_revision_submitted_validated_pending_user_approval",
    ),
    # 补证：新证据作为同一建议的新事件附加，原提交历史不覆盖
    CorrectionTransitionBinding(
        operation=OPERATION_ADD_EVIDENCE,
        disposition="evidence_appended",
        from_state="needs_evidence",
        to_state="submitted",
        trigger="new_evidence_appended",
        guard_id="g_revision_needs_evidence_submitted",
    ),
    # 报告所有者显式决定：验证本身不能批准
    CorrectionTransitionBinding(
        operation=OPERATION_RECORD_OWNER_DECISION,
        disposition="decision_approve",
        from_state="validated_pending_user_approval",
        to_state="approved",
        trigger="owner_explicit_approval",
        guard_id="g_revision_validated_approved",
    ),
    CorrectionTransitionBinding(
        operation=OPERATION_RECORD_OWNER_DECISION,
        disposition="decision_reject",
        from_state="validated_pending_user_approval",
        to_state="rejected",
        trigger="owner_explicit_rejection",
        guard_id="g_revision_validated_rejected",
    ),
    CorrectionTransitionBinding(
        operation=OPERATION_RECORD_OWNER_DECISION,
        disposition="decision_needs_evidence",
        from_state="validated_pending_user_approval",
        to_state="needs_evidence",
        trigger="owner_requests_evidence",
        guard_id="g_revision_validated_needs_evidence",
    ),
    # 发布：新快照、受影响产物重建与独立质控全部通过；以批准 ID 幂等
    CorrectionTransitionBinding(
        operation=OPERATION_PUBLISH,
        disposition="publish",
        from_state="approved",
        to_state="published",
        trigger="publish_after_rebuild_qc",
        guard_id="g_revision_approved_published",
    ),
)

_BINDINGS_BY_OPERATION: dict[str, tuple[CorrectionTransitionBinding, ...]] = {
    operation: tuple(
        binding for binding in CORRECTION_TRANSITION_BINDINGS if binding.operation == operation
    )
    for operation in (
        OPERATION_SUBMIT,
        OPERATION_ADD_EVIDENCE,
        OPERATION_VALIDATE,
        OPERATION_RECORD_OWNER_DECISION,
        OPERATION_PUBLISH,
    )
}
_BINDING_BY_PAIR: dict[tuple[str, str], CorrectionTransitionBinding] = {
    (binding.from_state, binding.to_state): binding
    for binding in CORRECTION_TRANSITION_BINDINGS
}


def _validate_bindings_against_frozen_registry() -> None:
    """导入期核对：绑定与冻结声明边逐字段一致，且恰好完整覆盖、不重不漏。"""
    declared_by_pair = {
        (edge.from_state, edge.to_state): edge
        for edge in TRANSITION_REGISTRY.declared_edges(REVISION_FAMILY)
    }
    seen_pairs: set[tuple[str | None, str]] = set()
    for binding in CORRECTION_TRANSITION_BINDINGS:
        pair = (binding.from_state, binding.to_state)
        edge = declared_by_pair.get(pair)
        if edge is None:
            raise ValueError(
                f"修订操作绑定引用了未声明迁移: {binding.operation}:{pair[0]} -> {pair[1]}"
            )
        if binding.trigger != edge.trigger or binding.guard_id != edge.guard_id:
            raise ValueError(
                f"修订操作绑定与冻结迁移表漂移: {binding.operation}:{pair[0]} -> {pair[1]}"
            )
        if pair in seen_pairs:
            raise ValueError(f"修订迁移被重复绑定: {pair[0]} -> {pair[1]}")
        seen_pairs.add(pair)
    missing = set(declared_by_pair) - seen_pairs
    if missing:
        raise ValueError(f"冻结修订迁移缺少操作绑定: {sorted(missing)}")
    for operation, bound in _BINDINGS_BY_OPERATION.items():
        if operation in INITIAL_STATE_OPERATIONS:
            if bound:
                raise ValueError(f"起始状态操作不得绑定迁移边: {operation}")
        elif not bound:
            raise ValueError(f"修订操作缺少迁移绑定: {operation}")


_validate_bindings_against_frozen_registry()


def bindings_for_operation(operation: str) -> tuple[CorrectionTransitionBinding, ...]:
    """按服务操作取全部绑定；未知操作失败关闭。"""
    if operation not in _BINDINGS_BY_OPERATION:
        raise ValueError(f"未知修订服务操作: {operation}")
    return _BINDINGS_BY_OPERATION[operation]


def binding_for(operation: str, disposition: str) -> CorrectionTransitionBinding:
    """按操作与处置分支取唯一绑定；未知组合失败关闭。"""
    for binding in bindings_for_operation(operation):
        if binding.disposition == disposition:
            return binding
    raise ValueError(f"修订操作无此处置分支: {operation}:{disposition}")


def binding_for_transition(from_state: str, to_state: str) -> CorrectionTransitionBinding:
    """按状态对取唯一服务绑定；未声明状态对失败关闭。"""
    try:
        return _BINDING_BY_PAIR[(from_state, to_state)]
    except KeyError as error:
        raise ValueError(f"修订审批族未声明迁移: {from_state} -> {to_state}") from error


def guard_spec_for(binding: CorrectionTransitionBinding) -> GuardSpec:
    """取绑定迁移边的结构化守卫声明；守卫规则仍由冻结注册表持有。"""
    return TRANSITION_REGISTRY.guard_spec(binding.guard_id)
