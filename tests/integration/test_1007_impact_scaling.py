"""Saving a large project must not compare every registered node to every edge."""

import pytest

from ci_workflow.graph.impact import ImpactEdge, ImpactGraph, ImpactLayer, ImpactNode


@pytest.mark.parametrize("size", [64, 512])
def test_impact_index_build_is_linear_and_preserves_exact_closure(
    monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    facts = tuple(ImpactNode(ImpactLayer.FACT, f"fact-{i:04d}") for i in range(size))
    charts = tuple(ImpactNode(ImpactLayer.CHART, f"chart-{i:04d}") for i in range(size))
    nodes = facts + charts
    edges = tuple(ImpactEdge(fact, chart) for fact, chart in zip(facts, charts, strict=True))
    comparisons = 0
    original_eq = ImpactNode.__eq__

    def count_eq(left: ImpactNode, right: object) -> bool:
        nonlocal comparisons
        comparisons += 1
        return original_eq(left, right)

    monkeypatch.setattr(ImpactNode, "__eq__", count_eq)
    graph = ImpactGraph(nodes=nodes, edges=edges)
    # Count work, not elapsed time: independent of machine load and CI speed.
    assert comparisons <= 12 * (len(nodes) + len(edges))
    plan = graph.impact_closure((facts[-1],))
    assert plan.affected == (facts[-1], charts[-1])
    assert set(plan.reused) == set(nodes) - {facts[-1], charts[-1]}
    reordered = ImpactGraph(nodes=nodes[::-1], edges=edges[::-1] + edges[:2])
    assert reordered.graph_digest == graph.graph_digest
    assert reordered.impact_closure((facts[-1],)) == plan
