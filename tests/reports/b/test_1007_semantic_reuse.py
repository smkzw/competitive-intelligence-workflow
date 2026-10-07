"""1007：单次调用内的确定性语义复用，不得改变完整链接成员资格与来源守卫。

家庭内的调用计数用例在旧实现上是 RED：重复的相同临床上下文会对每一对
观察重复做 Pydantic 校验与确定性比较。修复后，相同上下文的每行只校验
一次、相同上下文对只比较一次；所有成员资格、顺序、守卫负例与配对
提案/回执行为保持不变，且缓存绝不跨调用泄漏。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

import ci_workflow.reports.b.semantic_grouping as semantic_grouping
from ci_workflow.reports.b.semantic_contract import SemanticAdjudicationReceipt
from ci_workflow.reports.b.semantic_grouping import (
    ApprovedSemanticMerge,
    SemanticGroupingProposal,
    proposed_semantic_buckets,
    semantic_row_digest,
)


def _row(
    row_id: str,
    *,
    trial_id: str = "trial-a",
    timepoint: float = 48,
    definition: str = "EASI改善不少于75%",
    domain: str = "efficacy",
) -> dict[str, Any]:
    """完整已知语义的单行观察；除显式变化外所有硬轴一致。"""
    return {
        "row_id": row_id,
        "trial_id": trial_id,
        "product_id": "product-a",
        "clinical_concept": "easi75_response",
        "semantic_definition": definition,
        "semantic_direction": "higher_is_better",
        "unit": "%",
        "semantic_estimand": "treatment_policy",
        "semantic_denominator": "full_analysis_set",
        "semantic_analysis_set": "FAS",
        "semantic_analysis_form": "response_rate",
        "semantic_instrument_or_scale": "EASI v1.0",
        "actual_timepoint": timepoint,
        "actual_timepoint_unit": "week",
        "_domain": domain,
    }


def _proposal(first: dict[str, Any], second: dict[str, Any]) -> SemanticGroupingProposal:
    return SemanticGroupingProposal(
        proposal_id=f"proposal-{first['row_id']}-{second['row_id']}",
        row_ids=(str(first["row_id"]), str(second["row_id"])),
        row_digests=(semantic_row_digest(first), semantic_row_digest(second)),
        compatible=True,
        time_window_compatible=True,
        producer_id="synthetic-model",
        rationale_zh="两种措辞指向同一临床构念，时间窗经复核确认。",
    )


def _veto(first: dict[str, Any], second: dict[str, Any]) -> SemanticGroupingProposal:
    return _proposal(first, second).model_copy(update={"compatible": False})


def _approved(first: dict[str, Any], second: dict[str, Any]) -> ApprovedSemanticMerge:
    return ApprovedSemanticMerge(
        merge_id=f"merge-{first['row_id']}-{second['row_id']}",
        proposal=_proposal(first, second),
        receipt=SemanticAdjudicationReceipt(
            adjudication_id=f"adjudication-{first['row_id']}-{second['row_id']}",
            observation_ids=(str(first["row_id"]), str(second["row_id"])),
            decision="compatible",
            model_id="model-a",
            independent_review_id="reviewer-x",
            independent_context="clean-context-1",
            rationale_zh="两种措辞指向同一临床构念，已经独立上下文复核。",
        ),
    )


def _ordered_membership(
    groups: tuple[tuple[tuple[dict[str, Any], Any], ...], ...],
) -> list[list[str]]:
    return [[row["row_id"] for row, _ in group] for group in groups]


def _membership(
    groups: tuple[tuple[tuple[dict[str, Any], Any], ...], ...],
) -> set[frozenset[str]]:
    return {frozenset(row["row_id"] for row, _ in group) for group in groups}


def _counting(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Count production guard calls without changing behavior."""
    counts = {"observations": 0, "comparisons": 0}
    real_observation = semantic_grouping._observation
    real_compare = semantic_grouping.compare_clinical_constructs

    def counted_observation(row: dict[str, Any]) -> Any:
        counts["observations"] += 1
        return real_observation(row)

    def counted_compare(left: Any, right: Any) -> Any:
        counts["comparisons"] += 1
        return real_compare(left, right)

    monkeypatch.setattr(semantic_grouping, "_observation", counted_observation)
    monkeypatch.setattr(semantic_grouping, "compare_clinical_constructs", counted_compare)
    return counts


def test_repeated_valid_contexts_are_validated_and_compared_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """8 个相同上下文行：旧实现 8+2*28 次校验、28 次比较；修复后各 8/1 次。"""
    counters = _counting(monkeypatch)
    rows = tuple((_row(f"row-{index:02d}"), None) for index in range(8))
    snapshot = deepcopy(rows)

    groups = proposed_semantic_buckets((rows,), ())

    assert counters == {"observations": 8, "comparisons": 1}
    assert len(groups) == 1
    assert _ordered_membership(groups) == [[f"row-{index:02d}" for index in range(8)]]
    assert sum(len(group) for group in groups) == 8
    assert rows == snapshot, "复用不得改动输入行"


def test_distinct_origins_with_identical_contexts_still_reuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """每个观察各自成桶（不同 origin、相同上下文）：非描述域仍应复用。"""
    counters = _counting(monkeypatch)
    rows = tuple(_row(f"row-{index:02d}", trial_id=f"trial-{index:02d}") for index in range(8))

    groups = proposed_semantic_buckets(tuple(((row, None),) for row in rows), ())

    assert counters == {"observations": 8, "comparisons": 1}
    assert _membership(groups) == {frozenset(row["row_id"] for row in rows)}


def test_mixed_domains_never_reuse_across_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    """混合域：每行仍只校验一次，但不同域的同上下文对绝不共享裁决。"""
    counters = _counting(monkeypatch)
    efficacy = [_row("eff-01"), _row("eff-02")]
    safety = [_row("safe-01", domain="safety"), _row("safe-02", domain="safety")]

    groups = proposed_semantic_buckets(
        (tuple((row, None) for row in efficacy + safety),), (),
    )

    assert counters["observations"] == 4
    assert _membership(groups) == {
        frozenset({"eff-01", "eff-02"}), frozenset({"safe-01", "safe-02"}),
    }


def test_reuse_never_leaks_across_invocations(monkeypatch: pytest.MonkeyPatch) -> None:
    """两次独立调用各自重新校验与比较：本地缓存不得变成跨调用缓存。"""
    counters = _counting(monkeypatch)
    rows = tuple((_row(f"row-{index:02d}"), None) for index in range(4))

    for _ in range(2):
        assert len(proposed_semantic_buckets((rows,), ())) == 1

    assert counters == {"observations": 8, "comparisons": 2}


def test_second_invocation_revalidates_mutated_rows() -> None:
    """调用之间修改行：成员资格与摘要绑定必须反映新内容，而不是旧缓存。"""
    first = _row("row-first")
    second = _row("row-second", trial_id="trial-b")
    stale_proposal = _proposal(first, second)
    buckets = (((first, None),), ((second, None),))

    assert _membership(proposed_semantic_buckets(buckets, ())) == {
        frozenset({"row-first", "row-second"}),
    }
    first["semantic_analysis_set"] = "per_protocol"
    assert _membership(proposed_semantic_buckets(buckets, ())) == {
        frozenset({"row-first"}), frozenset({"row-second"}),
    }
    with pytest.raises(ValueError, match="摘要"):
        proposed_semantic_buckets(buckets, (stale_proposal,))


def test_membership_and_order_are_stable_across_input_orders() -> None:
    """相同输入的不同排列必须给出完全相同的成员与组内顺序。"""
    shared = [_row(f"a-{index:02d}") for index in range(4)]
    other = [_row(f"b-{index:02d}", definition="另一种措辞") for index in range(2)]
    rows = shared + other
    canonical = proposed_semantic_buckets(tuple(((row, None),) for row in rows), ())
    shuffled = proposed_semantic_buckets(
        tuple(((row, None),) for row in reversed(rows)), (),
    )

    assert _ordered_membership(canonical) == _ordered_membership(shuffled)
    assert _ordered_membership(canonical) == [["a-00", "a-01", "a-02", "a-03"], ["b-00", "b-01"]]
    assert sum(len(group) for group in canonical) == 6


def test_native_48_50_52_approximation_stays_non_transitive() -> None:
    """原生近窗（容差 2 周）：48↔50、50↔52 可比，48↔52 不可比，不得传递合并。"""
    rows = (
        _row("row-48", timepoint=48),
        _row("row-50", trial_id="trial-b", timepoint=50),
        _row("row-52", trial_id="trial-c", timepoint=52),
    )

    groups = proposed_semantic_buckets((tuple((row, None) for row in rows),), ())

    assert _membership(groups) == {frozenset({"row-50", "row-52"}), frozenset({"row-48"})}
    assert sum(len(group) for group in groups) == 3


def test_approved_wording_merges_stay_non_transitive() -> None:
    """已批准措辞归并 48↔50 与 50↔52：不得让 48 与 52 传递同组。"""
    first = _row("row-48", timepoint=48)
    second = _row("row-50", trial_id="trial-b", timepoint=50, definition="第二种措辞")
    third = _row("row-52", trial_id="trial-c", timepoint=52, definition="第三种措辞")
    merges = (_approved(first, second), _approved(second, third))

    groups = proposed_semantic_buckets(
        (tuple((row, None) for row in (first, second, third)),),
        (_proposal(first, second), _proposal(second, third)),
        approved_merges=merges,
    )

    assert _membership(groups) == {frozenset({"row-50", "row-52"}), frozenset({"row-48"})}
    assert sum(len(group) for group in groups) == 3


def test_unknown_definition_negative_survives_approved_wording_reuse() -> None:
    """缺定义不是等价类：即使持有已批准措辞归并也不得并组。"""
    reported = _row("row-reported")
    unknown = _row("row-unknown", trial_id="trial-b", definition="未知")

    groups = proposed_semantic_buckets(
        (((reported, None),), ((unknown, None),)),
        (_proposal(reported, unknown),),
        approved_merges=(_approved(reported, unknown),),
    )

    assert len(groups) == 2
    assert sum(len(group) for group in groups) == 2


def test_identical_unknown_values_are_not_an_equivalence_class() -> None:
    first = _row("row-a", definition="未报告")
    second = _row("row-b", trial_id="trial-b", definition="未报告")

    groups = proposed_semantic_buckets((((first, None),), ((second, None),)), ())

    assert len(groups) == 2


def test_source_conflict_negative_survives_approved_wording_reuse() -> None:
    """显式非临床来源（PK/免疫原性）不得借措辞归并或复用跨过守卫。"""
    clinical = _row("row-clinical")
    stamped = dict(
        _row("row-stamped", trial_id="trial-b"),
        **{"source_metric": "PK/PD"},
    )
    clean = _row("row-clean", trial_id="trial-b")

    control = proposed_semantic_buckets((((clinical, None),), ((clean, None),)), ())
    assert len(control) == 1, "对照：无来源冲突时同上下文必须并组"

    conflicted = proposed_semantic_buckets(
        (((clinical, None),), ((stamped, None),)),
        (_proposal(clinical, stamped),),
        approved_merges=(_approved(clinical, stamped),),
    )
    assert len(conflicted) == 2
    assert sum(len(group) for group in conflicted) == 2


def test_explicit_source_domain_conflict_is_not_reused_away() -> None:
    clinical = _row("row-clinical")
    stamped = dict(
        _row("row-stamped", trial_id="trial-b"),
        source_domain="immunogenicity",
    )

    groups = proposed_semantic_buckets(
        (((clinical, None),), ((stamped, None),)),
        (_proposal(clinical, stamped),),
        approved_merges=(_approved(clinical, stamped),),
    )

    assert len(groups) == 2


def test_pair_specific_approval_is_never_generic_reuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同一上下文的两对观察：克隆对不得复用已批准对的肯定裁决。

    已批准对是 (row-a48, row-b50)；克隆对 (row-z48, row-z50) 内容相同但没有
    自己的回执。完整链接下正确分区为 {b50,z50}+{a48,z48}；若把已批准对的
    决定当成通用接受，z48 会被拉进 {b50,z50} 组。
    """
    counters = _counting(monkeypatch)
    first = _row("row-a48", timepoint=48)
    second = _row("row-b50", trial_id="trial-b", timepoint=50, definition="第二种措辞")
    first_clone = _row("row-z48", timepoint=48)
    second_clone = _row("row-z50", trial_id="trial-d", timepoint=50, definition="第二种措辞")
    rows = (first, second, first_clone, second_clone)

    groups = proposed_semantic_buckets(
        (tuple((row, None) for row in rows),),
        (_proposal(first, second),),
        approved_merges=(_approved(first, second),),
    )

    assert _membership(groups) == {
        frozenset({"row-b50", "row-z50"}), frozenset({"row-a48", "row-z48"}),
    }
    assert sum(len(group) for group in groups) == 4
    assert counters == {"observations": 4, "comparisons": 4}


def test_pair_specific_veto_applies_only_to_its_own_pair() -> None:
    first = _row("row-a48", timepoint=48)
    second = _row("row-b50", trial_id="trial-b", timepoint=50, definition="第二种措辞")
    second_clone = _row("row-z50", trial_id="trial-d", timepoint=50, definition="第二种措辞")

    vetoed = proposed_semantic_buckets(
        (tuple((row, None) for row in (first, second, second_clone)),),
        (_veto(first, second),),
    )
    approved = proposed_semantic_buckets(
        (tuple((row, None) for row in (first, second)),),
        (_proposal(first, second),),
        approved_merges=(_approved(first, second),),
    )

    assert _membership(vetoed) == {
        frozenset({"row-b50", "row-z50"}), frozenset({"row-a48"}),
    }
    assert _membership(approved) == {frozenset({"row-a48", "row-b50"})}


@pytest.mark.parametrize("later_has_domain_stamp,expected_groups", ((True, 1), (False, 2)))
def test_descriptive_missing_and_null_domain_keep_pair_specific_source_guard(
    later_has_domain_stamp: bool, expected_groups: int,
) -> None:
    """旧路径右行的来源守卫使用左行域串；缺键与null不能缓存成同一输入。"""
    first = _row("row-a")
    second = _row("row-b")
    for row in (first, second):
        row.pop("_domain")
        row["source_domain"] = "immunogenicity"
    (second if later_has_domain_stamp else first)["_domain"] = None
    groups = proposed_semantic_buckets(
        (tuple((row, None) for row in (first, second)),), (), descriptive_only=True,
    )
    assert len(groups) == expected_groups
    assert {row["row_id"] for group in groups for row, _ in group} == {"row-a", "row-b"}
