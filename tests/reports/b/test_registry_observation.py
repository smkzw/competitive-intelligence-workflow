"""G20-2 路径①合同：登记终点分类器与区间时间窗语义（v2 含安全性域拒判）。"""

from __future__ import annotations

from ci_workflow.reports.b.registry_observation import (
    CLASSIFIER_VERSION,
    classify_registry_endpoint,
    is_safety_domain_endpoint,
)


def test_classifier_maps_real_registry_sentences_to_families() -> None:
    assert (
        classify_registry_endpoint(
            "Percent Change From Baseline in Lactate Dehydrogenase (LDH) Level at Day 92"
        )
        == "endpoint-pnh-ldh-change-v2"
    )
    # 绝对值测量不得落入"变化"族（第二十二轮 veto：Coversin LDH 绝对值误标）
    assert (
        classify_registry_endpoint(
            "Measurement of Lactate Dehydrogenase (LDH) at Baseline, Day 90 and Day 180"
        )
        == "endpoint-pnh-ldh-levels-v1"
    )
    assert (
        classify_registry_endpoint("Change From Baseline in Hgb at Week 12")
        == "endpoint-pnh-hemoglobin-v1"
    )
    assert (
        classify_registry_endpoint("Part 1: Number of Participants Who Were Transfusion-free")
        == "endpoint-pnh-transfusion-avoidance-v2"
    )
    # 输血例次 MEAN 行必须落入独立例次族（第二十轮 veto：不得标 Participants）
    assert (
        classify_registry_endpoint("Number of Transfusion Instances During 12 Weeks of Treatment")
        == "endpoint-pnh-transfusion-instances-v2"
    )
    assert (
        classify_registry_endpoint("Number of RBC Transfusion Instances")
        == "endpoint-pnh-transfusion-instances-v2"
    )
    assert (
        classify_registry_endpoint("Percentage of Participants With Breakthrough Hemolysis (BTH)")
        == "endpoint-pnh-breakthrough-hemolysis-v1"
    )
    assert classify_registry_endpoint("Two-year Overall Survival") == "endpoint-pnh-survival-v1"
    assert (
        classify_registry_endpoint(
            "Pharmacodynamic (PD) Effect of ALN-CC5: Percentage Reduction From Baseline"
        )
        == "endpoint-pnh-complement-inhibition-v1"
    )
    assert (
        classify_registry_endpoint("Measurement of Ratio of LDH to the Upper Limit of Normal (ULN)")
        == "endpoint-pnh-ldh-ratio-v1"
    )


def test_safety_domain_endpoints_never_enter_efficacy_families() -> None:
    """AE/TEAE/SAE 计数属安全性口径：拒绝进入任何疗效族（v2 veto 修复）。"""
    for text in (
        "Percentage of Participants With Treatment Emergent Adverse Events (TEAEs)",
        "Number and Type of Adverse Events",
        "Number of Participants With Serious Adverse Events (SAEs)",
    ):
        assert is_safety_domain_endpoint(text) is True
        assert classify_registry_endpoint(text) is None


def test_free_hemoglobin_and_transfusion_burden_are_distinct_families() -> None:
    """游离 Hgb 与输血次数负担不得并入血红蛋白浓度/输血回避族（v3）。"""
    assert (
        classify_registry_endpoint("Change From Baseline in Free Hgb at Week 25")
        == "endpoint-pnh-free-hemoglobin-v1"
    )
    result = classify_registry_endpoint("Number of RBC Transfusion Instances During 12 Weeks")
    assert result is not None and "transfusion" in result


def test_percent_change_free_hgb_and_burden_change_are_distinct() -> None:
    """百分比变化游离 Hgb 与变化型输血次数独立成族（v4）。"""
    assert (
        classify_registry_endpoint("Percent Change In Free Hemoglobin Levels From Baseline")
        == "endpoint-pnh-free-hemoglobin-pct-v1"
    )
    assert (
        classify_registry_endpoint("Change in Number of Transfusion Instances From 24 Weeks Prior")
        == "endpoint-pnh-transfusion-burden-change-v1"
    )


def test_pnh_clone_size_endpoints_are_distinct_family() -> None:
    """克隆大小终点（含 Hemoglobinuria 字样）独立成族（v6）。"""
    assert (
        classify_registry_endpoint(
            "Percent Change In PNH RBC Types II And III Clone Size From Baseline"
        )
        == "endpoint-pnh-clone-pct-v1"
    )
    assert (
        classify_registry_endpoint(
            "Change From Baseline in Paroxysmal Nocturnal Hemoglobinuria (PNH) Clone Size"
        )
        == "endpoint-pnh-clone-pct-v1"
    )


def test_classifier_returns_none_for_unclassifiable_text() -> None:
    """兜底族捕获所有非安全域文本；只有空文本和安全域返回 None。"""
    assert (
        classify_registry_endpoint("Quality of Life Questionnaire Score")
        == "endpoint-generic-unclassified-v1"
    )
    assert classify_registry_endpoint("") is None
    assert is_safety_domain_endpoint("Serious Adverse Events") is True


def test_classifier_version_is_explicit() -> None:
    assert CLASSIFIER_VERSION.startswith("registry-endpoint-family-")
