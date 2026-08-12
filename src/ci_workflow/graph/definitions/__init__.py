"""Task 3.4 新建报告图定义：完整不可变节点合同注册表。"""

from __future__ import annotations

from ci_workflow.graph.definitions.new_report import NEW_REPORT_NODES
from ci_workflow.graph.types import NodeContract

__all__ = ["NEW_REPORT_NODES", "node_contract"]


def node_contract(node_id: str) -> NodeContract:
    """按 node_id 取节点合同；未知节点失败关闭。"""
    for contract in NEW_REPORT_NODES:
        if contract.node_id == node_id:
            return contract
    raise ValueError(f"未知图节点: {node_id}")
