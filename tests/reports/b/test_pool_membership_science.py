"""P3.5-3 合同：跨试验可比性成员裁决与池级校验的唯一真源在科学层。

渲染器（_cross_trial_groups/_adjudicate_full_pool）只消费科学层输出做
展示组装；候选提案不授权合并、批准归并跨桶生效、否决生效、池级
孤儿/跨域/摘要/外层重验全部由 reports/b 承担。
"""
from __future__ import annotations

import pytest

from ci_workflow.renderers.portal import report_b as rb
from ci_workflow.reports.b.portal_science import (
    adjudicate_comparable_membership,
    validate_full_pool_inputs,
)
from tests.reports.b.test_semantic_grouping_proposals import _approved, _rows


def _pool(*rows: dict, domain: str = "efficacy") -> list[tuple[dict, object]]:
    return [(dict(row, _domain=domain), None) for row in rows]


def _key(row: dict) -> tuple[str, str]:
    return (
        str(row.get("semantic_definition") or row.get("original_definition") or ""),
        str(row.get("trial_id") or ""),
    )


def test_candidate_alone_never_merges_in_membership() -> None:
    first, second = _rows()
    first = dict(first, semantic_definition="EASI-75应答者比例")
    members = adjudicate_comparable_membership(
        "efficacy", _pool(first, second),
        bucket_key_fn=_key, semantic_proposals=(), semantic_adjudications=(),
    )
    assert [tuple(row["row_id"] for row, _ in group) for group in members] == [
        ("first",), ("second",),
    ]


def test_approved_merge_unifies_membership() -> None:
    first, second = _rows()
    from tests.reports.b.test_semantic_grouping_proposals import _proposal

    members = adjudicate_comparable_membership(
        "efficacy", _pool(first, second),
        bucket_key_fn=_key, semantic_proposals=(_proposal(first, second),),
        semantic_adjudications=(_approved(first, second),),
    )
    assert [tuple(row["row_id"] for row, _ in group) for group in members] == [
        ("first", "second"),
    ]


def test_veto_splits_membership() -> None:
    first, second = _rows()
    veto = _approved(first, second).proposal.model_copy(update={"compatible": False})
    members = adjudicate_comparable_membership(
        "efficacy", _pool(first, second),
        bucket_key_fn=_key, semantic_proposals=(veto,), semantic_adjudications=(),
    )
    assert len(members) == 2


def test_membership_rejects_unknown_domain() -> None:
    first, _ = _rows()
    with pytest.raises(ValueError, match="不支持"):
        adjudicate_comparable_membership(
            "mystery", _pool(first),
            bucket_key_fn=_key, semantic_proposals=(), semantic_adjudications=(),
        )


def test_pool_validation_rejects_orphans_and_cross_domain() -> None:
    first, second = _rows()
    pool = _pool(first, second)
    with pytest.raises(ValueError, match="池之外"):
        validate_full_pool_inputs(
            pool, semantic_proposals=(_proposal_for(first, "ghost"),),
            semantic_adjudications=(),
        )
    safety_row = dict(first, row_id="saf", _domain="safety")
    from tests.reports.b.test_semantic_grouping_proposals import _proposal

    cross = _proposal(first, safety_row)
    with pytest.raises(ValueError, match="跨域"):
        validate_full_pool_inputs(
            [*pool, (safety_row, None)],
            semantic_proposals=(cross,), semantic_adjudications=(),
        )


def test_pool_validation_rejects_stale_adjudication_digest() -> None:
    first, second = _rows()
    stale = _approved(first, dict(second, value=99))
    with pytest.raises(ValueError, match="摘要"):
        validate_full_pool_inputs(
            _pool(first, second), semantic_proposals=(),
            semantic_adjudications=(stale,),
        )


def test_renderer_cross_trial_groups_consume_science_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """渲染器 efficacy/safety 分组必须消费科学层成员（不得本地重裁决）。"""
    first, second = _rows()
    records = _pool(first, second)
    calls: list[str] = []
    real = adjudicate_comparable_membership

    def counting(domain, recs, **kwargs):
        calls.append(domain)
        return real(domain, recs, **kwargs)

    monkeypatch.setattr(rb, "adjudicate_comparable_membership", counting)
    rb._groups_for_page(
        "efficacy", records,
        semantic_proposals=(),
        semantic_adjudications=(_approved(first, second),),
    )
    assert calls == ["efficacy"]
    rb._groups_for_page(
        "safety", [(dict(r, _domain="safety"), None) for r in _rows()],
        semantic_proposals=(), semantic_adjudications=(),
    )
    assert calls[-1] == "safety"


def _proposal_for(first: dict, other_id: str):
    from tests.reports.b.test_semantic_grouping_proposals import _proposal

    ghost = dict(first, row_id=other_id, trial_id=f"trial-{other_id}")
    return _proposal(first, ghost)
