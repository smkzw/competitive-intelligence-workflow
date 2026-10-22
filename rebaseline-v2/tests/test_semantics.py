from ciw2.domain.semantics import (
    classify_safety,
    comparable_on_axis,
    derive_proportion,
    parse_number,
    same_safety_category,
    same_timepoint,
)
from ciw2.domain.tiers import tier_of


def test_unknown_is_not_zero():
    assert parse_number(None) is None
    assert parse_number("NA") is None
    assert parse_number("") is None
    assert parse_number("0") == 0.0
    assert parse_number("1,234") == 1234.0


def test_proportion_only_from_participant_counts():
    assert derive_proportion(4, 321, "count_participants") == 1.2
    assert derive_proportion(12, 100, "count_events") is None      # 事件次数不能当受试者比例
    assert derive_proportion(4, None, "count_participants") is None
    assert derive_proportion(5, 4, "count_participants") is None   # 分母小于分子：拒绝


def test_safety_semantics_v1_bugs():
    # v1 F06：Non-serious TEAE 曾被归为 any_teae
    assert classify_safety("Non-serious TEAEs").seriousness == "non_serious"
    assert not same_safety_category("Non-serious TEAEs", "TEAEs")
    # Grade 4 / Grade 1 or 3 / Grade >=3 不同
    assert not same_safety_category("Grade 4 TEAEs", "Grade >=3 TEAEs")
    assert classify_safety("Grade 1 or 3 AEs").grades == frozenset({1, 3})
    assert classify_safety("TEAEs without SAEs").excludes_serious
    assert classify_safety("SAE or AE leading to discontinuation").composite


def test_timepoints():
    assert same_timepoint("Week 16", "Day 112") is True
    assert same_timepoint("Week 16", "Week 24") is False
    assert same_timepoint("Month 6", "Week 24") is None   # 月不换算


def test_comparability():
    a = {"stat_type": "proportion", "unit": "%", "timepoint": "Week 16"}
    assert comparable_on_axis(a, dict(a)) == (True, "")
    assert comparable_on_axis(a, {**a, "timepoint": "Week 24"})[0] is False
    assert comparable_on_axis(a, {**a, "stat_type": "mean"})[0] is False


def test_tiers():
    assert tier_of("result.primary.value") == "critical"
    assert tier_of("safety.sae.any") == "critical"
    assert tier_of("design.masking") == "standard"
