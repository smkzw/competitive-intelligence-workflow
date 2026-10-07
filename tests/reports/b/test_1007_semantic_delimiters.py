"""Root-cause family for unknown/nonclinical delimiter handling on shared predicates."""

from __future__ import annotations

import pytest

from ci_workflow.reports.b.semantic_contract import (
    semantic_value_is_unknown,
    source_domain_conflicts,
)


@pytest.mark.parametrize(
    ("value", "expected_unknown"),
    [
        # RED root causes: ASCII/Chinese commas and qualifier-before-real-tail lists.
        ("未知,未报告", True),
        ("未知，未报告", True),
        ("未知（待核）、EASI改善", False),
        ("EASI改善, not reported", False),
        ("EASI改善、result-not-reported", False),
        # Preserved adjacent positives/negatives.
        ("未知、EASI改善", False),
        ("（未知）EASI改善", True),
        ("EASI改善（FAS）", False),
        ("未知、待核", True),
        ("未知（待核）", True),
        ("用户清除，待重新核实", True),
        ("EASI改善不少于75%（FAS）", False),
    ],
)
def test_unknown_list_and_qualifier_delimiters(value: str, expected_unknown: bool) -> None:
    assert semantic_value_is_unknown(value) is expected_unknown


@pytest.mark.parametrize(
    ("metric", "expected_conflict"),
    [
        # RED root causes: retain known nonclinical tokens through lists/qualifiers.
        ("Cmax、Tmax", True),
        ("Cmax, Tmax", True),
        ("Cmax（几何均值）", True),
        ("Cmax（未报告）", True),
        ("PK、PD", True),
        # Preserved closed-token and clinical-boundary behavior.
        ("Cmax", True),
        ("Cmax_geometric_mean", True),
        ("tmax", True),
        ("adaptive_response", False),
        ("easi75_response", False),
        ("EASI-75", False),
    ],
)
def test_nonclinical_metric_list_and_qualifier_delimiters(
    metric: str, expected_conflict: bool,
) -> None:
    assert source_domain_conflicts({"source_metric": metric}, "efficacy") is expected_conflict


def test_source_domain_null_and_explicit_semantics_remain_closed() -> None:
    assert source_domain_conflicts({"source_domain": "unknown"}, "efficacy") is True
    assert source_domain_conflicts({"source_domain": "efficacy"}, "efficacy") is False
    assert source_domain_conflicts({"source_metric": "未报告"}, "efficacy") is True
    assert source_domain_conflicts({}, "efficacy") is False
