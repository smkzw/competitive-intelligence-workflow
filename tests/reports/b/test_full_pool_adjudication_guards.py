"""P3.0 护栏：完整观察池一次裁决，页面只投影，子集不得重新裁决。

来源：2026-09-11 Reviewer-A 终审四项 P2（packets/2026-09-11-takeover-review/）。
第一轮反例 test_product_page_is_projection_of_global_groups 的不变量由
tests/browser/test_b_semantic_proposals.py::test_dossier_uses_global_scientific_partition
在真实渲染路径上验证；本文件固化裁决入口护栏本身。
"""
from __future__ import annotations

import pytest

from ci_workflow.renderers.portal.report_b import (
    _adjudicate_full_pool,
    _assert_page_fallback_only_uncovered,
    _groups_for_page,
)
from tests.reports.b.test_semantic_grouping_proposals import _proposal, _rows


def _pool_rows(*rows: dict) -> list[tuple[dict, None]]:
    return [(dict(row, _domain="efficacy"), None) for row in rows]


def test_page_groups_reject_real_domain_subset() -> None:
    """产品/试验档案分组不得接受真实域子集：那是全池裁决入口的职责。"""
    a, b = _rows()
    a = dict(a, product_id="product-a")
    b = dict(b, product_id="product-b")
    c = dict(
        b, row_id="third", trial_id="trial-c", actual_timepoint=52,
        semantic_definition="第三种措辞", original_definition="第三种措辞",
    )
    rows = _pool_rows(a, b, c)
    selected = [item for item in rows if item[0]["product_id"] == "product-b"]
    with pytest.raises(ValueError, match="完整观察池"):
        _groups_for_page(
            "product-trial-profiles", selected,
            semantic_proposals=(_proposal(a, b), _proposal(b, c)),
        )


def test_full_pool_rejects_orphan_proposal() -> None:
    """全池裁决中引用不存在观察的提案必须拒绝，不得静默忽略。"""
    a, b = _rows()
    orphan = _proposal(a, dict(b, row_id="missing-row"))
    with pytest.raises(ValueError, match="完整观察池之外的观察"):
        _adjudicate_full_pool(_pool_rows(a, b), semantic_proposals=(orphan,))


def test_full_pool_rejects_unknown_domain() -> None:
    """完整观察池只接受已知域；未知域记录必须失败关闭。"""
    a, _ = _rows()
    with pytest.raises(ValueError, match="未支持域"):
        _adjudicate_full_pool(
            [(dict(a, _domain="mystery"), None)], semantic_proposals=(),
        )


def test_full_pool_adjudicates_and_merges_via_approved_merge() -> None:
    from tests.reports.b.test_semantic_grouping_proposals import _approved

    a, b = _rows()
    merged = _adjudicate_full_pool(
        _pool_rows(a, b), semantic_proposals=(_proposal(a, b),),
        semantic_adjudications=(_approved(a, b),),
    )
    assert [tuple(row["row_id"] for row in group["rows"]) for group in merged] == [
        ("first", "second"),
    ]
    # 候选提案单独存在时不再授权合并（P3.7 合同）。
    separated = _adjudicate_full_pool(
        _pool_rows(a, b), semantic_proposals=(_proposal(a, b),),
    )
    assert len(separated) == 2


def test_page_cannot_retag_existing_domain() -> None:
    """页面不得静默改写已有域标签；域冲突必须失败关闭。"""
    a, _ = _rows()
    with pytest.raises(ValueError, match="域"):
        _groups_for_page("efficacy", [(dict(a, _domain="safety"), None)])


def test_uncovered_real_domain_record_rejected() -> None:
    """未经全池裁决的真实域观察不得走页面回退分组；显式合成/空态记录可以。"""
    a, _ = _rows()
    real = (dict(a, _domain="efficacy"), None)
    with pytest.raises(ValueError, match="未经完整观察池裁决"):
        _assert_page_fallback_only_uncovered((real,))
    synthetic = (dict(a, _domain="matrix", _synthetic=True), None)
    empty_state = (dict(a, _domain="baseline", _empty_state=True), None)
    _assert_page_fallback_only_uncovered((synthetic, empty_state))


def test_profile_page_synthetic_fallback_preserved() -> None:
    """钉住既有行为：generic 合成记录不产生分组；profile 记录保持状态矩阵。"""
    generic = ({"row_id": "g1", "_domain": "generic"}, None)
    assert _groups_for_page("product-trial-profiles", (generic,)) == ()
    profile = ({"row_id": "p1", "_domain": "profile"}, None)
    groups = _groups_for_page("product-trial-profiles", (profile,))
    assert len(groups) == 1
    assert groups[0]["rows"][0]["_chart_type"] == "status_matrix"
