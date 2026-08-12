"""Task 3.4 应用持有的类型化控制图：迁移注册表、规范状态、归约器与本地执行器。

默认执行器只编排应用能力；事实、声明、快照继续由既有数据层持有。
"""

from __future__ import annotations

from ci_workflow.graph.definitions import NEW_REPORT_NODES, node_contract
from ci_workflow.graph.executor import (
    GraphExecutor,
    IdempotentSideEffects,
    SideEffectConflictError,
    SideEffectError,
)
from ci_workflow.graph.reducer import graph_reducer
from ci_workflow.graph.registry import TRANSITION_REGISTRY, TransitionRegistry
from ci_workflow.graph.state import initial_state
from ci_workflow.graph.types import (
    DeclaredEdge,
    GuardResult,
    NodeContract,
    RetryPolicy,
    TransitionRequest,
    TypedField,
)

__all__ = [
    "DeclaredEdge",
    "GraphExecutor",
    "GuardResult",
    "IdempotentSideEffects",
    "NEW_REPORT_NODES",
    "NodeContract",
    "RetryPolicy",
    "SideEffectConflictError",
    "SideEffectError",
    "TRANSITION_REGISTRY",
    "TransitionRegistry",
    "TransitionRequest",
    "TypedField",
    "graph_reducer",
    "initial_state",
    "node_contract",
]
