"""P3.3 合同：时间窗可比性由版本化政策决定，废除全局 ±2 周硬编码。

两套机制统一：观察按 policies/timepoints 规则归类（双侧命中且同规则），
数值邻近性由该规则的版本化容差（comparison_tolerance_weeks，默认 2.0）
判定；未命中规则或分属不同规则 = 不可比，不再被全局阈值放行。
"""
from __future__ import annotations

from pathlib import Path

from ci_workflow.reports.b.contracts import load_timepoint_compatibility_policy
from ci_workflow.reports.b.semantic_contract import (
    ClinicalConstructObservation,
    compare_clinical_constructs,
)

ROOT = Path(__file__).resolve().parents[3]


def _obs(row_id: str, timepoint: float, unit: str = "week") -> ClinicalConstructObservation:
    return ClinicalConstructObservation.model_validate({
        "observation_id": row_id,
        "clinical_construct": "easi75_response",
        "definition": "EASI-75 应答者比例",
        "direction": "higher_is_better",
        "unit": "%",
        "estimand": "treatment_policy",
        "denominator": "full_analysis_set",
        "analysis_set": "full_analysis_set",
        "analysis_form": "response_rate",
        "instrument_or_scale": "EASI v1.0",
        "actual_timepoint": timepoint,
        "actual_timepoint_unit": unit,
    })


def test_unmatched_window_rejected_instead_of_delta_bypass() -> None:
    """15 周未命中任何版本化窗口：旧 ±2 会放行 13↔15，新合同拒绝。"""
    result = compare_clinical_constructs(_obs("a", 13), _obs("b", 15))
    assert not result.compatible
    assert any("版本化时间窗" in reason for reason in result.reasons)


def test_off_window_pair_rejected() -> None:
    """8 周未命中窗口：不得因 |8-10|≤2 放行。"""
    result = compare_clinical_constructs(_obs("a", 8), _obs("b", 10))
    assert not result.compatible


def test_same_window_within_tolerance_remains_compatible() -> None:
    """48↔50 同属 week-52 窗且在默认容差内：保持可比（钉住旧行为）。"""
    result = compare_clinical_constructs(_obs("a", 48), _obs("b", 50))
    assert result.compatible
    assert result.time_window_note_zh is not None


def test_same_window_beyond_tolerance_remains_incompatible() -> None:
    """48↔56 同窗但差 8 周 > 默认容差 2：保持不可比（钉住旧行为）。"""
    result = compare_clinical_constructs(_obs("a", 48), _obs("b", 56))
    assert not result.compatible
    assert any("容差" in reason for reason in result.reasons)


def test_tolerance_comes_from_versioned_policy() -> None:
    """容差属于政策：week-52 容差调至 4 周时 48↔52 变为可比。"""
    policy_path = ROOT / "policies/timepoints/compatibility-v1.yaml"
    policy = load_timepoint_compatibility_policy(policy_path)
    adjusted = policy.model_copy(update={
        "rules": tuple(
            rule.model_copy(update={"comparison_tolerance_weeks": 4.0})
            if rule.rule_id == "timepoint-week-52-v1" else rule
            for rule in policy.rules
        ),
    })
    result = compare_clinical_constructs(
        _obs("a", 48), _obs("b", 52), timepoint_policy=adjusted,
    )
    assert result.compatible
    strict = compare_clinical_constructs(
        _obs("a", 48), _obs("b", 52),
    )
    assert not strict.compatible, "默认政策下 48↔52 仍不可比（容差 2 周）"


def test_different_windows_rejected() -> None:
    """12 周与 48 周分属不同版本化窗口：不可比。"""
    result = compare_clinical_constructs(_obs("a", 12), _obs("b", 48))
    assert not result.compatible
    assert any("不同版本化时间窗" in reason for reason in result.reasons)


def test_policy_file_declares_per_rule_tolerance() -> None:
    """发货政策必须显式声明每规则容差并升级版本。"""
    policy = load_timepoint_compatibility_policy()
    assert policy.version == "1.2"
    for rule in policy.rules:
        assert rule.comparison_tolerance_weeks > 0
