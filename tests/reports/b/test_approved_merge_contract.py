"""P3.7 核心合同：正向语义归并必须持有已获独立复核签发的裁决。

候选 SemanticGroupingProposal 只贡献否决与守卫输入；它自身不再授权
跨试验合并（"提案身份和来源声明摘要只是候选完整性机制，不是实际
独立复核者签发 accepted 的替代"）。确定性路径（同桶+守卫通过）不
受影响；否决方向永远生效。
"""
from __future__ import annotations

import pytest

from ci_workflow.renderers.portal.report_b import _groups_for_page
from ci_workflow.reports.b.semantic_contract import SemanticAdjudicationReceipt
from ci_workflow.reports.b.semantic_grouping import (
    ApprovedSemanticMerge,
    proposed_semantic_buckets,
)
from tests.reports.b.test_semantic_grouping_proposals import _proposal, _rows


def _receipt(first: dict, second: dict) -> SemanticAdjudicationReceipt:
    return SemanticAdjudicationReceipt(
        adjudication_id="adj-1",
        observation_ids=(str(first["row_id"]), str(second["row_id"])),
        decision="compatible",
        model_id="model-a",
        independent_review_id="reviewer-x",
        independent_context="clean-context-1",
        rationale_zh="两种措辞指向同一临床构念，已经独立上下文复核。",
    )


def _approved(first: dict, second: dict) -> ApprovedSemanticMerge:
    return ApprovedSemanticMerge(
        merge_id="merge-1",
        proposal=_proposal(first, second),
        receipt=_receipt(first, second),
    )


def _pool(*rows: dict) -> tuple[tuple[tuple[dict, None], ...], ...]:
    return (tuple((dict(row, _domain="efficacy"), None) for row in rows),)


def test_candidate_positive_proposal_alone_cannot_merge() -> None:
    first, second = _rows()
    groups = proposed_semantic_buckets(
        _pool(first, second), (_proposal(first, second),),
    )
    assert len(groups) == 2, "候选提案未经独立复核签发，不得授权合并"


def test_approved_merge_licenses_wording_equivalence() -> None:
    first, second = _rows()
    groups = proposed_semantic_buckets(
        _pool(first, second),
        (_proposal(first, second),),
        approved_merges=(_approved(first, second),),
    )
    assert len(groups) == 1
    assert {row["row_id"] for row, _ in groups[0]} == {"first", "second"}


def test_candidate_veto_applies_without_approval() -> None:
    first, second = _rows()
    veto = _proposal(first, second).model_copy(update={"compatible": False})
    groups = proposed_semantic_buckets(_pool(first, second), (veto,))
    assert len(groups) == 2


def test_approved_merge_with_stale_digest_is_rejected() -> None:
    first, second = _rows()
    approved = _approved(first, second)
    mutated = dict(second, value=99)
    with pytest.raises(ValueError, match="摘要"):
        proposed_semantic_buckets(
            _pool(first, mutated),
            (_proposal(first, mutated),),
            approved_merges=(approved,),
        )


def test_merge_model_binds_receipt_to_proposal() -> None:
    first, second = _rows()
    incompatible_receipt = _receipt(first, second).model_copy(
        update={"decision": "incompatible"}
    )
    with pytest.raises(ValueError, match="一致"):
        ApprovedSemanticMerge(
            merge_id="m",
            proposal=_proposal(first, second),
            receipt=incompatible_receipt,
        )
    foreign_ids = _receipt(first, dict(second, row_id="other"))
    with pytest.raises(ValueError, match="观察"):
        ApprovedSemanticMerge(
            merge_id="m",
            proposal=_proposal(first, second),
            receipt=foreign_ids,
        )


def test_renderer_page_consumes_approved_merges_only() -> None:
    first, second = _rows()
    rows = [(dict(row, _domain="efficacy"), None) for row in (first, second)]
    candidate_only = _groups_for_page(
        "efficacy", rows, semantic_proposals=(_proposal(first, second),),
    )
    assert len(candidate_only) == 2
    approved = _groups_for_page(
        "efficacy", rows,
        semantic_proposals=(_proposal(first, second),),
        semantic_adjudications=(_approved(first, second),),
    )
    assert len(approved) == 1


def test_forged_outer_merge_is_revalidated_at_pool_boundary() -> None:
    """P3（Reviewer-D）：外层 model_copy 伪造不得经池级边界。"""
    from ci_workflow.renderers.portal.report_b import _adjudicate_full_pool
    from tests.reports.b.test_r13_semantic_grouping import _project_efficacy

    left = _project_efficacy("pool-a", "easi75", timepoint=48)
    right = _project_efficacy("pool-b", "easi75", timepoint=50)
    right.update(trial_id="trial-b", semantic_definition="另一种措辞",
                 original_definition="另一种措辞")
    pool = [(dict(r, _domain="efficacy"), None) for r in (left, right)]
    forged = _approved(left, right).model_copy(
        update={"receipt": _receipt(left, right).model_copy(
            update={"decision": "incompatible"})}
    )
    with pytest.raises(ValueError, match="一致"):
        _adjudicate_full_pool(
            pool,
            semantic_proposals=(_proposal(left, right),),
            semantic_adjudications=(forged,),
        )


def test_descriptive_domains_reject_approved_merge_instead_of_igning() -> None:
    """描述性域收到已批准归并必须拒绝，不得静默忽略。"""
    from tests.reports.b.test_r13_semantic_grouping import _project_baseline

    a = _project_baseline("da", product_id="product-a", trial_id="trial-a", population="FAS")
    b = _project_baseline("db", product_id="product-b", trial_id="trial-b", population="FAS")
    forged = _approved(
        {**a, "row_id": "da"}, {**b, "row_id": "db"},
    )
    with pytest.raises(ValueError, match="描述性"):
        _groups_for_page(
            "baseline-overview",
            [({k: v for k, v in a.items() if k != "_domain"}, None),
             ({k: v for k, v in b.items() if k != "_domain"}, None)],
            semantic_proposals=(_proposal({**a, "row_id": "da"}, {**b, "row_id": "db"}),),
            semantic_adjudications=(forged,),
        )


def test_safety_page_consumes_approved_merges() -> None:
    """Reviewer-D P2-b 回归：安全性分支的已批准归并必须可达。"""
    first, second = _rows()  # 完整语义字段；未知轴会触发保守否决
    rows = [(dict(first, _domain="safety"), None), (dict(second, _domain="safety"), None)]
    merged = _groups_for_page(
        "safety", rows,
        semantic_proposals=(_proposal(first, second),),
        semantic_adjudications=(_approved(first, second),),
    )
    assert len(merged) == 1
