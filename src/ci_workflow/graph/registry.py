"""Task 3.4 迁移注册表：九族注册、声明边查询与结构化守卫求值。

构造时校验全部不变量：边族已注册、守卫存在、无重复边、证据状态族零迁移边、
无孤立守卫。Guard ID 与测试字面 fixture 逐边一致。
"""

from __future__ import annotations

from ci_workflow.graph.guards import GUARD_SPECS, GuardSpec, evaluate_spec
from ci_workflow.graph.state import ALL_STATE_FAMILIES, EVIDENCE_STATE_FAMILIES
from ci_workflow.graph.transitions import (
    ALL_DECLARED_TRANSITIONS,
    FAMILY_STATE_ENUMS,
)
from ci_workflow.graph.types import DeclaredEdge, GuardResult


class TransitionRegistry:
    """应用持有的类型化迁移注册表。"""

    def __init__(
        self,
        edges: frozenset[DeclaredEdge],
        guard_specs: dict[str, GuardSpec],
    ) -> None:
        self._edges = frozenset(edges)
        self._guard_specs = dict(guard_specs)
        self._by_family: dict[str, frozenset[DeclaredEdge]] = {
            family: frozenset(edge for edge in self._edges if edge.family == family)
            for family in ALL_STATE_FAMILIES
        }
        self._validate()

    def _validate(self) -> None:
        seen: set[tuple[str, str | None, str]] = set()
        referenced_guards: set[str] = set()
        for edge in self._edges:
            if edge.family not in ALL_STATE_FAMILIES:
                raise ValueError(f"未注册状态族: {edge.family}")
            if edge.guard_id not in self._guard_specs:
                raise ValueError(f"声明边缺少守卫: {edge.guard_id}")
            key = (edge.family, edge.from_state, edge.to_state)
            if key in seen:
                raise ValueError(f"重复声明边: {key}")
            seen.add(key)
            referenced_guards.add(edge.guard_id)
        # 前四组证据状态族不由运行图改写：不得声明任何迁移边
        for family in EVIDENCE_STATE_FAMILIES:
            if self._by_family[family]:
                raise ValueError(f"证据状态族不得声明迁移边: {family}")
        for guard_id, spec in self._guard_specs.items():
            if guard_id not in referenced_guards:
                raise ValueError(f"孤立守卫: {guard_id}")
            if spec.guard_id != guard_id:
                raise ValueError(f"守卫标识不一致: {guard_id}")

    def families(self) -> tuple[str, ...]:
        return ALL_STATE_FAMILIES

    def runtime_families(self) -> tuple[str, ...]:
        return tuple(
            family for family in ALL_STATE_FAMILIES if family not in EVIDENCE_STATE_FAMILIES
        )

    def evidence_families(self) -> tuple[str, ...]:
        return EVIDENCE_STATE_FAMILIES

    def state_values(self, family: str) -> tuple[str, ...]:
        if family not in FAMILY_STATE_ENUMS:
            raise ValueError(f"未注册状态族: {family}")
        return tuple(str(member.value) for member in FAMILY_STATE_ENUMS[family])

    def declared(
        self,
        family: str,
        from_state: str | None,
        to_state: str,
    ) -> DeclaredEdge | None:
        """声明边查询：未声明（含同状态、跨族、缺失边）一律返回 None。"""
        for edge in self._by_family.get(family, frozenset()):
            if edge.from_state == from_state and edge.to_state == to_state:
                return edge
        return None

    def declared_edges(self, family: str) -> tuple[DeclaredEdge, ...]:
        return tuple(
            sorted(
                self._by_family.get(family, frozenset()),
                key=lambda edge: (edge.from_state or "", edge.to_state),
            )
        )

    def guard_ids(self) -> frozenset[str]:
        return frozenset(self._guard_specs)

    def guard_spec(self, guard_id: str) -> GuardSpec:
        return self._guard_specs[guard_id]

    def evaluate_guard(
        self,
        guard_id: str,
        evidence: dict[str, object],
        *,
        target_family: str,
        target_object_id: str,
    ) -> GuardResult:
        return evaluate_spec(
            self._guard_specs[guard_id],
            evidence,
            target_family=target_family,
            target_object_id=target_object_id,
        )


TRANSITION_REGISTRY = TransitionRegistry(ALL_DECLARED_TRANSITIONS, GUARD_SPECS)
