"""P3.7 生产者合同：语义复核工作项的发射与提交验证（Reviewer-E 修订版）。

对选择与消费端分桶语义一致：初始分桶（与渲染端相同的 science/文本桶）
作为输入；同域才可成对；同桶且守卫可比才跳过；跨桶近窗对与措辞差异对
都是待裁决对。提交验证绑定任务摘要与当前观察、复验候选资格、执行消费
端同等的最终时间窗守卫。
"""
from __future__ import annotations

import pytest

from ci_workflow.application.semantic_review_task import (
    build_semantic_review_task,
    validate_semantic_review_submission,
)
from tests.reports.b.test_semantic_grouping_proposals import _approved, _rows


def _pool(*rows: dict, domain: str = "efficacy") -> list[tuple[dict, object]]:
    return [(dict(row, _domain=domain), None) for row in rows]


def _buckets(records):
    return (tuple(records),)


def _enriched_rows() -> tuple[dict, ...]:
    first, second = _rows()
    # 真实流程由 _records_with_semantics 从原始定义补全语义定义；此处对齐。
    first = dict(first, semantic_definition="EASI-75应答者比例")
    _, second_base = _rows()
    third = dict(second_base, row_id="third", trial_id="trial-c", actual_timepoint=52,
                 semantic_definition="第三种措辞", original_definition="第三种措辞")
    return first, second, third


def test_task_lists_wording_and_cross_bucket_near_window_pairs() -> None:
    first, second, third = _enriched_rows()
    records = _pool(first, second, third)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    # (first,second) 措辞差异同窗；(second,third) 措辞差异且 50↔52 同窗；
    # (first,third) 48↔52 超窗属硬冲突（模型不可覆盖）→ 不进入。
    pairs = {frozenset(item.row_ids) for item in task.pairs}
    assert pairs == {frozenset(("first", "second")),
                     frozenset(("second", "third"))}
    for item in task.pairs:
        assert len(item.row_digests) == 2
        assert all(len(digest) == 64 for digest in item.row_digests)
        assert item.guard_verdict == "undecided"
    assert task.policy_version


def test_task_skips_deterministically_mergeable_same_bucket_pair() -> None:
    first, _ = _rows()
    first = dict(first, semantic_definition="EASI-75应答者比例")
    twin = dict(first, row_id="twin", trial_id="trial-b", value=61)
    records = _pool(first, twin)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    # 同桶 + 守卫完全可比（含同实际时间点）→ 确定性合并，无需模型裁决。
    assert task.pairs == ()


def test_task_emits_cross_bucket_guard_compatible_pair() -> None:
    """同语义不同实际时间点（近窗）跨桶对：守卫可比但不同桶 → 必须裁决。"""
    first, _ = _rows()
    first = dict(first, semantic_definition="EASI-75应答者比例")
    near = dict(first, row_id="near", trial_id="trial-b", actual_timepoint=50)
    records = _pool(first, near)
    one_bucket_each = (tuple(records[:1]), tuple(records[1:]))
    task = build_semantic_review_task("project-x", records, buckets=one_bucket_each)
    assert {frozenset(p.row_ids) for p in task.pairs} == {frozenset(("first", "near"))}


def test_task_excludes_same_trial_and_unknown_product_pairs() -> None:
    first, _ = _rows()
    first = dict(first, semantic_definition="EASI-75应答者比例")
    same_trial = dict(first, row_id="st", value=61)
    unknown_product = dict(first, row_id="up", trial_id="trial-b", product_id="")
    records = _pool(first, same_trial, unknown_product)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    assert task.pairs == (), "同试验对与产品未知对都不得进入工作项"


def test_task_never_pairs_across_domains() -> None:
    first, second = _rows()
    first = dict(first, semantic_definition="EASI-75应答者比例")
    safety_row = dict(second, row_id="saf", _domain="safety")
    records = [(dict(r, _domain="efficacy"), None) for r in (first, second)]
    records.append((safety_row, None))
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    assert all("saf" not in pair.row_ids for pair in task.pairs)


def test_valid_submission_round_trips() -> None:
    first, second, _ = _enriched_rows()
    records = _pool(first, second)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    validated = validate_semantic_review_submission(
        [_approved(first, second).model_dump(mode="json")], task,
        records=records, buckets=_buckets(records),
    )
    assert len(validated) == 1


def test_stale_task_digest_mismatch_is_rejected() -> None:
    """提交摘要与任务签发摘要不一致（任务过期），即使当前观察未漂移。"""
    first, second, _ = _enriched_rows()
    records = _pool(first, second)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    drifted_submission = _approved(first, dict(second, value=99))
    with pytest.raises(ValueError, match="任务摘要"):
        validate_semantic_review_submission(
            [drifted_submission.model_dump(mode="json")], task,
            records=records, buckets=_buckets(records),
        )


def test_submission_losing_candidate_status_is_rejected() -> None:
    """任务签发后分桶上下文变化使对成为确定性可比：候选资格复验拒绝。

    签发时两行分属不同桶（跨桶可比对=候选）；提交时同桶且守卫可比 →
    消费端会自动合并，批准失去对象。
    """
    first, _ = _rows()
    first = dict(first, semantic_definition="EASI-75应答者比例")
    near = dict(first, row_id="near", trial_id="trial-b", actual_timepoint=50)
    records = _pool(first, near)
    split = (tuple(records[:1]), tuple(records[1:]))
    task = build_semantic_review_task("project-x", records, buckets=split)
    assert len(task.pairs) == 1
    with pytest.raises(ValueError, match="候选资格"):
        validate_semantic_review_submission(
            [_approved(first, near).model_dump(mode="json")], task,
            records=records, buckets=_buckets(records),
        )


def test_time_window_vetoed_submission_is_rejected() -> None:
    """时间窗不兼容的正向提交必然被消费端拒绝，验证器须前置拒绝。"""
    first, second, _ = _enriched_rows()
    records = _pool(first, second)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    base = _approved(first, second)
    vetoed = base.model_copy(
        update={"proposal": base.proposal.model_copy(
            update={"time_window_compatible": False})},
    )
    with pytest.raises(ValueError, match="时间窗"):
        validate_semantic_review_submission(
            [vetoed.model_dump(mode="json")], task,
            records=records, buckets=_buckets(records),
        )


def test_pair_outside_task_is_rejected() -> None:
    first, second, third = _enriched_rows()
    records = _pool(first, second)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    with pytest.raises(ValueError, match="任务之外"):
        validate_semantic_review_submission(
            [_approved(first, third).model_dump(mode="json")], task,
            records=_pool(first, second, third),
            buckets=_buckets(_pool(first, second, third)),
        )


def test_forged_outer_binding_is_revalidated() -> None:
    first, second, _ = _enriched_rows()
    records = _pool(first, second)
    task = build_semantic_review_task("project-x", records, buckets=_buckets(records))
    payload = _approved(first, second).model_dump(mode="json")
    payload["receipt"]["decision"] = "incompatible"
    with pytest.raises(ValueError, match="一致"):
        validate_semantic_review_submission(
            [payload], task, records=records, buckets=_buckets(records),
        )
