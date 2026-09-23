"""Task 9.2 影响传播图：来源 → 事实 → 声明 → 报告页面 → 选定格式的确定性反向闭包。

图只由稳定对象标识与显式依赖边构成；影响闭包、复用集合与计划摘要完全由
图结构推导。调用方只能声明变化种子（或来自 ``gates.coverage`` 计算的受影响
报告类型），不能自行扩大或缩小结果集合。输出恒为排序稳定、去重的冻结序列；
计划摘要绑定图内容、种子、影响与复用集合，可直接用作刷新计划与重建动作的
稳定幂等键。

门槛收紧的报告级影响以 ``gates.coverage`` 的变更单元 → 受影响报告计算为
唯一真源：本模块不复制任何 GateSpec 规则，只在页面节点声明报告类型后把
报告级影响接入同一闭包——受影响报告回到覆盖/科学质控，其余对象按摘要复用。
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.state import REPORT_KINDS

__all__ = [
    "ImpactEdge",
    "ImpactGraph",
    "ImpactGraphError",
    "ImpactLayer",
    "ImpactNode",
    "ImpactPlan",
]


class ImpactGraphError(RuntimeError):
    """影响图构造或求值违反确定性合同。"""


class ImpactLayer(StrEnum):
    """影响传播的封闭层词表；变化只能沿声明顺序向前传播。"""

    SOURCE = "source"
    FACT = "fact"
    CLAIM = "claim"
    DERIVATION = "derivation"
    MEDICAL_SEMANTIC = "medical_semantic"
    FACET = "facet"
    NARRATIVE = "narrative"
    CHART = "chart"
    TABLE = "table"
    INDEX = "index"
    SOURCE_POINTER = "source_pointer"
    PAGE = "page"
    FORMAT = "format"


_LAYER_ORDER: dict[ImpactLayer, int] = {layer: order for order, layer in enumerate(ImpactLayer)}

_REPORT_KIND_SET = frozenset(REPORT_KINDS)


def _sort_key(node: ImpactNode) -> tuple[int, str]:
    return (_LAYER_ORDER[node.layer], node.object_id)


def _token(node: ImpactNode) -> str:
    return f"{node.layer.value}:{node.object_id}"


@dataclass(frozen=True)
class ImpactNode:
    """影响图节点：层 + 稳定对象标识；仅页面层可声明所属报告类型集合。"""

    layer: ImpactLayer
    object_id: str
    report_kinds: frozenset[str] = frozenset()
    revision: int | None = None

    def __post_init__(self) -> None:
        try:
            layer = ImpactLayer(self.layer)
        except ValueError as error:
            raise ImpactGraphError(f"未知影响层: {self.layer!r}") from error
        object.__setattr__(self, "layer", layer)
        if not self.object_id or self.object_id.split() != [self.object_id]:
            raise ImpactGraphError("影响对象标识必须是非空且不含空白字符的稳定标识")
        kinds = frozenset(self.report_kinds)
        unknown = sorted(kinds - _REPORT_KIND_SET)
        if unknown:
            raise ImpactGraphError(f"报告类型超出封闭词表: {unknown}")
        if kinds and layer is not ImpactLayer.PAGE:
            raise ImpactGraphError(f"仅页面层可声明报告类型: {layer.value}:{self.object_id}")
        if self.revision is not None and self.revision < 0:
            raise ImpactGraphError("影响对象revision不得为负数")
        object.__setattr__(self, "report_kinds", kinds)


@dataclass(frozen=True)
class ImpactEdge:
    """一条依赖边：downstream 依赖 upstream；变化沿 upstream → downstream 传播。"""

    upstream: ImpactNode
    downstream: ImpactNode

    def __post_init__(self) -> None:
        if (
            self.upstream.revision is not None
            and self.downstream.revision is not None
            and self.upstream.revision != self.downstream.revision
        ):
            raise ImpactGraphError(
                "影响边不得跨revision: "
                f"{_token(self.upstream)}@{self.upstream.revision} -> "
                f"{_token(self.downstream)}@{self.downstream.revision}"
            )
        allowed: dict[ImpactLayer, frozenset[ImpactLayer]] = {
            ImpactLayer.SOURCE: frozenset({ImpactLayer.FACT}),
            ImpactLayer.FACT: frozenset(
                {
                    ImpactLayer.CLAIM,
                    ImpactLayer.DERIVATION,
                    ImpactLayer.MEDICAL_SEMANTIC,
                    ImpactLayer.FACET,
                    ImpactLayer.NARRATIVE,
                    ImpactLayer.CHART,
                    ImpactLayer.TABLE,
                    ImpactLayer.INDEX,
                    ImpactLayer.SOURCE_POINTER,
                }
            ),
            ImpactLayer.CLAIM: frozenset({ImpactLayer.PAGE}),
            ImpactLayer.DERIVATION: frozenset(
                {
                    ImpactLayer.DERIVATION,
                    ImpactLayer.FACET,
                    ImpactLayer.NARRATIVE,
                    ImpactLayer.CHART,
                    ImpactLayer.TABLE,
                    ImpactLayer.INDEX,
                }
            ),
            ImpactLayer.MEDICAL_SEMANTIC: frozenset(
                {
                    ImpactLayer.MEDICAL_SEMANTIC,
                    ImpactLayer.FACET,
                    ImpactLayer.NARRATIVE,
                    ImpactLayer.CHART,
                    ImpactLayer.TABLE,
                    ImpactLayer.INDEX,
                }
            ),
            ImpactLayer.FACET: frozenset(
                {
                    ImpactLayer.FACET,
                    ImpactLayer.NARRATIVE,
                    ImpactLayer.CHART,
                    ImpactLayer.TABLE,
                    ImpactLayer.INDEX,
                }
            ),
            ImpactLayer.NARRATIVE: frozenset({ImpactLayer.NARRATIVE, ImpactLayer.PAGE}),
            ImpactLayer.CHART: frozenset({ImpactLayer.PAGE}),
            ImpactLayer.TABLE: frozenset({ImpactLayer.PAGE}),
            ImpactLayer.INDEX: frozenset({ImpactLayer.PAGE}),
            ImpactLayer.SOURCE_POINTER: frozenset({ImpactLayer.PAGE}),
            ImpactLayer.PAGE: frozenset({ImpactLayer.FORMAT}),
            ImpactLayer.FORMAT: frozenset(),
        }
        if self.downstream.layer not in allowed[self.upstream.layer]:
            raise ImpactGraphError(
                "影响边不符合声明的派生方向或跳过必要相邻层: "
                f"{_token(self.upstream)} -> {_token(self.downstream)}"
            )


@dataclass(frozen=True)
class ImpactPlan:
    """一次影响传播的冻结结果：影响集合包含全部种子及其下游，其余对象复用。"""

    graph_digest: str
    seeds: tuple[ImpactNode, ...]
    affected: tuple[ImpactNode, ...]
    reused: tuple[ImpactNode, ...]

    def __post_init__(self) -> None:
        seed_set = frozenset(self.seeds)
        affected_set = frozenset(self.affected)
        reused_set = frozenset(self.reused)
        if not seed_set <= affected_set:
            raise ImpactGraphError("影响集合必须包含全部变化种子")
        if affected_set & reused_set:
            raise ImpactGraphError("影响集合与复用集合不得相交")
        if len(affected_set) != len(self.affected) or len(reused_set) != len(self.reused):
            raise ImpactGraphError("影响集合与复用集合必须去重")

    @property
    def plan_digest(self) -> str:
        """计划稳定摘要：绑定图内容、种子、影响与复用集合；用作幂等键。"""
        return stable_id(
            "impact-plan",
            self.graph_digest,
            *("seed:" + _token(node) for node in self.seeds),
            *("affected:" + _token(node) for node in self.affected),
            *("reused:" + _token(node) for node in self.reused),
        )

    def affected_ids(self, layer: ImpactLayer) -> tuple[str, ...]:
        """按层取受影响对象稳定标识；排序稳定、去重。"""
        return tuple(node.object_id for node in self.affected if node.layer is layer)

    def reused_ids(self, layer: ImpactLayer) -> tuple[str, ...]:
        """按层取按摘要复用对象稳定标识；排序稳定、去重。"""
        return tuple(node.object_id for node in self.reused if node.layer is layer)


@dataclass(frozen=True)
class ImpactGraph:
    """不可变影响图：父版本登记对象的完整集合 + 依赖边；构造期失败关闭。"""

    nodes: tuple[ImpactNode, ...]
    edges: tuple[ImpactEdge, ...] = ()

    def __post_init__(self) -> None:
        canonical_nodes = tuple(sorted(set(self.nodes), key=_sort_key))
        seen_owners: dict[str, ImpactLayer] = {}
        for node in canonical_nodes:
            existing = seen_owners.get(node.object_id)
            if existing is not None:
                raise ImpactGraphError(
                    f"对象标识不得跨层重复: {node.object_id}（{existing.value}/{node.layer.value}）"
                )
            seen_owners[node.object_id] = node.layer
        node_set = frozenset(canonical_nodes)
        canonical_edges = tuple(
            sorted(
                set(self.edges),
                key=lambda edge: (_sort_key(edge.upstream), _sort_key(edge.downstream)),
            )
        )
        for edge in canonical_edges:
            unregistered = [
                endpoint
                for endpoint in (edge.upstream, edge.downstream)
                if endpoint not in node_set
            ]
            if unregistered:
                raise ImpactGraphError(
                    f"影响边端点未登记: {_token(edge.upstream)} -> {_token(edge.downstream)}"
                )
        adjacency: dict[ImpactNode, tuple[ImpactNode, ...]] = {}
        for node in canonical_nodes:
            adjacency[node] = tuple(
                edge.downstream for edge in canonical_edges if edge.upstream == node
            )
        visiting: set[ImpactNode] = set()
        visited: set[ImpactNode] = set()

        def visit(node: ImpactNode) -> None:
            if node in visiting:
                raise ImpactGraphError(f"影响图存在环：{_token(node)}")
            if node in visited:
                return
            visiting.add(node)
            for downstream in adjacency[node]:
                visit(downstream)
            visiting.remove(node)
            visited.add(node)

        for node in canonical_nodes:
            visit(node)
        projected_pages = {
            edge.upstream
            for edge in canonical_edges
            if edge.upstream.layer is ImpactLayer.PAGE
            and edge.downstream.layer is ImpactLayer.FORMAT
        }
        unprojected_pages = [
            node.object_id
            for node in canonical_nodes
            if node.layer is ImpactLayer.PAGE and node not in projected_pages
        ]
        if unprojected_pages:
            raise ImpactGraphError(
                "每个报告页面都必须显式投影到交付格式: " + "、".join(unprojected_pages)
            )
        object.__setattr__(self, "nodes", canonical_nodes)
        object.__setattr__(self, "edges", canonical_edges)

    @functools.cached_property
    def _node_set(self) -> frozenset[ImpactNode]:
        return frozenset(self.nodes)

    @functools.cached_property
    def _dependents(self) -> dict[ImpactNode, tuple[ImpactNode, ...]]:
        """反向依赖索引：对象 → 直接依赖它的对象（排序稳定）。"""
        index: dict[ImpactNode, set[ImpactNode]] = {}
        for edge in self.edges:
            index.setdefault(edge.upstream, set()).add(edge.downstream)
        return {
            node: tuple(sorted(dependents, key=_sort_key)) for node, dependents in index.items()
        }

    @functools.cached_property
    def graph_digest(self) -> str:
        """图内容摘要：登记对象与依赖边共同决定；内容相同则摘要相同。"""
        node_parts = tuple(
            f"node:{node.layer.value}:{node.object_id}:{','.join(sorted(node.report_kinds))}:"
            f"{node.revision if node.revision is not None else '-'}"
            for node in self.nodes
        )
        edge_parts = tuple(
            f"edge:{edge.upstream.object_id}:{edge.downstream.object_id}" for edge in self.edges
        )
        return stable_id("impact-graph", *node_parts, *edge_parts)

    def impact_closure(self, seeds: Sequence[ImpactNode]) -> ImpactPlan:
        """由变化种子推导影响闭包；种子未登记失败关闭，调用方不能改写结果。"""
        seed_tuple = tuple(sorted(set(seeds), key=_sort_key))
        if not seed_tuple:
            raise ImpactGraphError("变化种子不能为空")
        for seed in seed_tuple:
            if seed not in self._node_set:
                raise ImpactGraphError(f"变化种子未在影响图登记: {_token(seed)}")
        affected: set[ImpactNode] = set(seed_tuple)
        frontier = list(seed_tuple)
        while frontier:
            for dependent in self._dependents.get(frontier.pop(), ()):
                if dependent not in affected:
                    affected.add(dependent)
                    frontier.append(dependent)
        return ImpactPlan(
            graph_digest=self.graph_digest,
            seeds=seed_tuple,
            affected=tuple(sorted(affected, key=_sort_key)),
            reused=tuple(sorted(self._node_set - affected, key=_sort_key)),
        )

    def impact_for_report_kinds(self, report_kinds: Sequence[str]) -> ImpactPlan:
        """门槛收紧的报告级影响：受影响报告的页面进入同一闭包。

        调用方声明的受影响报告集合必须来自 ``gates.coverage`` 的确定性计算；
        声明的报告类型没有登记页面时失败关闭，不允许静默缩小影响范围。
        报告回覆盖/科学质控；事实与声明内容未变化，按摘要复用。
        """
        requested = frozenset(report_kinds)
        if not requested:
            raise ImpactGraphError("受影响报告类型集合不能为空")
        unknown = sorted(requested - _REPORT_KIND_SET)
        if unknown:
            raise ImpactGraphError(f"受影响报告类型超出封闭词表: {unknown}")
        affected_pages = frozenset(
            node
            for node in self.nodes
            if node.layer is ImpactLayer.PAGE and node.report_kinds & requested
        )
        covered: set[str] = set()
        for page in affected_pages:
            covered |= page.report_kinds
        missing = sorted(requested - covered)
        if missing:
            raise ImpactGraphError(f"声明的受影响报告类型在影响图中没有页面: {missing}")
        return self.impact_closure(tuple(affected_pages))
