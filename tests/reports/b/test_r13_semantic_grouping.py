"""R13 B 类跨产品/试验语义归一化与图表分组合同。"""

from __future__ import annotations

from pathlib import Path

from ci_workflow.renderers.portal.report_b import (
    _efficacy_records,
    _filter_dimensions,
    _groups_for_page,
    _page_records,
    _project_record,
    _safety_records,
    load_report_b_data,
)

ROOT = Path(__file__).resolve().parents[3]
PNH_DATA = ROOT / "fixtures/positive/b-pnh/inputs/report-data.json"


def _project_efficacy(
    row_id: str,
    endpoint: str,
    *,
    statistic: str = "response_rate",
    timepoint: int | float | str = 24,
    time_unit: str = "week",
) -> dict[str, object]:
    return _project_record(
        {
            "row_id": row_id,
            "product_id": "product-a",
            "trial_id": "trial-a",
            "endpoint_family_label_zh": endpoint,
            "original_endpoint": endpoint,
            "original_definition": f"原始定义：{endpoint}",
            "actual_timepoint": timepoint,
            "actual_timepoint_unit": time_unit,
            "analysis_form": statistic,
            "analysis_population": "FAS",
            "arm_label": "active",
            "unit": "%",
            "value": 50,
            "numerator": 5,
            "denominator": 10,
        },
        domain="efficacy",
        names={"product-a": "产品甲"},
        trial_names={"trial-a": "试验甲"},
        fallback=row_id,
    )


def _project_baseline(
    row_id: str,
    *,
    product_id: str,
    trial_id: str,
    population: str,
    variable: str = "age",
    value: float = 50,
) -> dict[str, object]:
    return _project_record(
        {
            "row_id": row_id,
            "product_id": product_id,
            "trial_id": trial_id,
            "variable": variable,
            "source_name": variable,
            "baseline_timepoint": "基线",
            "statistic_form": "mean",
            "analysis_population": population,
            "arm_label": "active",
            "unit": "岁" if variable == "age" else "g/dL",
            "value": value,
        },
        domain="baseline",
        names={product_id: f"产品{product_id[-1].upper()}"},
        trial_names={trial_id: f"试验{trial_id[-1].upper()}"},
        fallback=row_id,
    )


def test_controlled_semantics_normalize_aliases_and_preserve_raw_identity() -> None:
    row = _project_efficacy("row-easi", "EASI-75 responder proportion")

    assert row["clinical_concept"] == "easi75_response"
    assert row["clinical_concept_label_zh"] == "EASI-75应答"
    assert row["time_window_band"] == "around_month_6"
    assert row["statistical_form_family"] == "response_rate"
    assert row["population_context"] == "full_analysis_set"
    assert row["arm_role"] == "treatment"
    assert row["arm"] == "治疗组"
    assert row["original_endpoint"] == "EASI-75 responder proportion"
    assert row["original_definition"] == "原始定义：EASI-75 responder proportion"
    assert row["actual_timepoint"] == 24
    assert row["actual_timepoint_unit"] == "week"


def test_time_units_convert_to_controlled_clinical_bands() -> None:
    day_28 = _project_efficacy("row-day28", "EASI-75", timepoint=28, time_unit="day")
    week_12 = _project_efficacy("row-week12", "EASI-75", timepoint=12)
    month_6 = _project_efficacy("row-month6", "EASI-75", timepoint=6, time_unit="month")
    week_prefix = _project_efficacy("row-week24-prefix", "EASI-75", timepoint="week 24")
    around_week = _project_efficacy("row-around-week12", "EASI-75", timepoint="around 12 weeks")

    assert day_28["time_window_band"] == "around_day_28"
    assert week_12["time_window_band"] == "around_week_12"
    assert month_6["time_window_band"] == "around_month_6"
    assert week_prefix["time_window_band"] == "around_month_6"
    assert around_week["time_window_band"] == "around_week_12"


def test_safety_keeps_original_event_identity() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trial_names = {row.id: row.display_id for row in data.trials}
    safety = _safety_records(data, names, trial_names)

    assert any(
        row["original_endpoint"] == "任何TEAE"
        for row, _source in safety
    )


def test_controlled_semantics_do_not_fuzzy_merge_distinct_concepts() -> None:
    rows = [
        (_project_efficacy("row-easi75", "EASI-75"), None),
        (_project_efficacy("row-easi90", "EASI-90"), None),
        (_project_efficacy("row-unknown", "EASI-76"), None),
    ]

    groups = _groups_for_page("efficacy", rows)

    assert len(groups) == 3
    assert {row["clinical_concept"] for row, _source in rows} == {
        "easi75_response",
        "easi90_response",
        "efficacy:easi76",
    }


def test_statistical_form_and_time_band_remain_separate_axes() -> None:
    rows = [
        (_project_efficacy("row-rate", "EASI-75", statistic="response_rate", timepoint=24), None),
        (_project_efficacy("row-mean", "EASI-75", statistic="mean", timepoint=24), None),
        (_project_efficacy("row-week12", "EASI-75", statistic="response_rate", timepoint=12), None),
    ]

    groups = _groups_for_page("efficacy", rows)

    assert len(groups) == 3
    assert {group["title_zh"] for group in groups} == {
        "EASI-75应答 · 应答率 · 约6个月 · 全分析集 · 该组部分观察的登记分组信息不全，已按试验合并展示",
        "EASI-75应答 · 均值 · 约6个月 · 全分析集 · 该组部分观察的登记分组信息不全，已按试验合并展示",
        "EASI-75应答 · 应答率 · 约第12周 · 全分析集 · 该组部分观察的登记分组信息不全，已按试验合并展示",
    }


def test_breakthrough_hemolysis_is_an_adverse_direction_event_rate() -> None:
    row = _project_efficacy(
        "row-breakthrough",
        "breakthrough_hemolysis",
        statistic="response_rate",
        timepoint=24,
    )

    assert row["clinical_concept"] == "breakthrough_hemolysis_rate"
    assert row["clinical_concept_label_zh"] == "突破性溶血"
    assert row["statistical_form_family"] == "event_rate"
    assert row["statistical_form_family_label_zh"] == "事件发生率（越低越好）"


def test_incomplete_fixture_semantics_preserve_trials_and_both_arm_roles_without_merging() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trial_names = {row.id: row.display_id for row in data.trials}
    efficacy = _efficacy_records(data, names, trial_names)

    groups = _groups_for_page("efficacy", efficacy)
    # 此历史fixture缺关键比较语义；不向真实输入补造参数来保留旧的跨试验预期。
    assert len(groups) == 2
    assert all(group["cross_trial"] is False for group in groups)
    assert all(group["x_axis_label_zh"] == "产品｜试验" for group in groups)
    assert {row["trial_id"] for row, _source in efficacy} == {
        "nct04558918",
        "nct04820530",
    }
    assert {row["arm_role"] for row, _source in efficacy} == {"treatment", "control"}
    assert {row["clinical_concept"] for row, _source in efficacy} == {
        "hemoglobin_response_without_transfusion"
    }
    assert {row["_chart_identity_key"] for group in groups for row in group["rows"]} == {
        "iptacopan::nct04558918",
        "iptacopan::nct04820530",
    }
    assert {row["_chart_series_key"] for group in groups for row in group["rows"]} == {
        "treatment",
        "control",
    }


def test_duplicate_same_role_arms_keep_distinct_human_labels() -> None:
    high = _project_efficacy("row-high", "EASI-75")
    low = _project_efficacy("row-low", "EASI-75")
    high["group_id"] = "treatment-high"
    high["arm_detail"] = "高剂量"
    low["group_id"] = "treatment-low"
    low["arm_detail"] = "低剂量"

    groups = _groups_for_page(
        "efficacy",
        [(high, None), (low, None)],
    )

    assert len(groups) == 1
    assert {row["_chart_series_key"] for row in groups[0]["rows"]} == {
        "treatment:treatmenthigh",
        "treatment:treatmentlow",
    }
    assert {row["_chart_series_label"] for row in groups[0]["rows"]} == {
        "治疗组（高剂量）",
        "治疗组（低剂量）",
    }


def test_unknown_semantics_keep_trials_in_adjacent_descriptive_groups() -> None:
    first = _project_efficacy("first", "EASI-75")
    second = dict(first, row_id="second", trial_id="trial-b")
    groups = _groups_for_page("efficacy", [(first, None), (second, None)])
    assert len(groups) == 2
    assert all(group["cross_trial"] is False for group in groups)
    assert all("登记分组信息不全" in group["title_zh"] for group in groups)
    assert {row["row_id"] for group in groups for row in group["rows"]} == {
        "first", "second",
    }


def test_complete_known_semantics_still_allow_cross_trial_group() -> None:
    first = _project_efficacy("first", "EASI-75")
    first.update(
        semantic_direction="higher_is_better",
        semantic_estimand="treatment_policy",
        semantic_denominator="full_analysis_set",
        semantic_instrument_or_scale="EASI v1.0",
    )
    second = dict(first, row_id="second", trial_id="trial-b")
    groups = _groups_for_page("efficacy", [(first, None), (second, None)])
    assert len(groups) == 1
    assert groups[0]["cross_trial"] is True


def test_longitudinal_group_uses_one_series_across_time_bands() -> None:
    first = _project_efficacy("row-week24", "EASI-75", timepoint=24)
    second = _project_efficacy("row-week12", "EASI-75", timepoint=12)
    first["group_id"] = "treatment-arm"
    second["group_id"] = "treatment-arm"

    groups = _groups_for_page(
        "longitudinal-results",
        [(first, None), (second, None)],
    )

    assert len(groups) == 1
    assert {row["_chart_type"] for row in groups[0]["rows"]} == {"line"}
    assert {row["_chart_series_key"] for row in groups[0]["rows"]} == {"treatment"}
    assert {row["_chart_time_key"] for row in groups[0]["rows"]} == {
        "around_month_6",
        "around_week_12",
    }


def test_baseline_and_disposition_groups_are_identity_aware() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trial_names = {row.id: row.display_id for row in data.trials}
    efficacy = _efficacy_records(data, names, trial_names)
    safety = ()

    baseline = _page_records(
        data,
        page_id="baseline-overview",
        names=names,
        trial_names=trial_names,
        efficacy=efficacy,
        safety=safety,
    )
    assert any(row["original_variable"] == "baseline_sample_size" for row, _source in baseline)
    assert any(
        row["original_variable_label_zh"] == "基线样本量"
        for row, _source in baseline
    )
    assert any(
        row["original_definition"] == "基线时点按随机化组列示"
        for row, _source in baseline
    )
    disposition = _page_records(
        data,
        page_id="disposition-overview",
        names=names,
        trial_names=trial_names,
        efficacy=efficacy,
        safety=safety,
    )

    baseline_groups = _groups_for_page("baseline-overview", baseline)
    disposition_groups = _groups_for_page("disposition-overview", disposition)

    assert baseline_groups
    assert disposition_groups
    for group in (*baseline_groups, *disposition_groups):
        assert group["x_axis_label_zh"] == "产品｜试验"
        if group["cross_trial"]:
            assert all(row["_chart_identity_key"] for row in group["rows"])
        assert all(row["clinical_concept"] for row in group["rows"])


def test_baseline_comparison_splits_unknown_population_from_fas() -> None:
    fas = _project_baseline(
        "baseline-age-fas",
        product_id="product-a",
        trial_id="trial-a",
        population="全分析集",
    )
    source_population = _project_baseline(
        "baseline-age-source",
        product_id="product-b",
        trial_id="trial-b",
        population="来源报告基线/相应分析人群",
        value=47,
    )

    groups = _groups_for_page(
        "baseline-overview",
        [(fas, None), (source_population, None)],
    )

    assert len(groups) == 2
    assert {group["title_zh"] for group in groups} == {
        "基线 · 年龄 · 均值 · 全分析集",
        "基线 · 年龄 · 均值 · 来源报告基线/相应分析人群",
    }


def test_baseline_internal_hgb_alias_is_never_exposed_as_visible_concept() -> None:
    row = _project_baseline(
        "baseline-hgb",
        product_id="product-a",
        trial_id="trial-a",
        population="全分析集",
        variable="baseline_hgb_actual",
        value=8.8,
    )

    assert row["clinical_concept"] == "baseline_hemoglobin"
    assert row["clinical_concept_label_zh"] == "基线血红蛋白"
    filters = _filter_dimensions([(row, None)])
    assert filters[0]["element"] == "基线血红蛋白"


def test_baseline_age_mean_and_median_share_one_comparison_with_difference_note() -> None:
    mean = _project_baseline(
        "baseline-age-mean",
        product_id="product-a",
        trial_id="trial-a",
        population="全分析集",
    )
    median = _project_baseline(
        "baseline-age-median",
        product_id="product-b",
        trial_id="trial-b",
        population="全分析集",
        value=47,
    )
    median["statistic_form"] = "中位数"
    median["statistical_form_family"] = "median"
    median["statistical_form_family_label_zh"] = "中位数"

    groups = _groups_for_page(
        "baseline-overview",
        [(mean, None), (median, None)],
    )

    assert len(groups) == 1
    assert groups[0]["title_zh"] == "基线 · 年龄 · 全分析集 · 统计形式：均值/中位数"
    assert groups[0]["title_complete"] is True


def test_baseline_missing_unit_stays_with_same_measure_and_is_marked() -> None:
    reported = _project_baseline(
        "baseline-hgb-reported",
        product_id="product-a",
        trial_id="trial-a",
        population="全分析集",
        variable="baseline_hgb_actual",
        value=8.8,
    )
    undisclosed = _project_baseline(
        "baseline-hgb-undisclosed",
        product_id="product-b",
        trial_id="trial-b",
        population="全分析集",
        variable="baseline_hgb_actual",
        value=0,
    )
    undisclosed["unit"] = ""
    undisclosed["renderable"] = False
    undisclosed["disclosure_state"] = "not_publicly_disclosed"

    groups = _groups_for_page(
        "baseline-overview",
        [(reported, None), (undisclosed, None)],
    )

    assert len(groups) == 1
    assert (
        groups[0]["title_zh"]
        == "基线 · 基线血红蛋白 · 均值 · 全分析集 · 单位：g/dL/单位未列示"
    )


def test_disposition_group_title_is_complete_without_duplicate_indicator_prefix() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trial_names = {row.id: row.display_id for row in data.trials}
    records = _page_records(
        data,
        page_id="participant-flow",
        names=names,
        trial_names=trial_names,
        efficacy=(),
        safety=(),
    )

    groups = _groups_for_page("participant-flow", records)

    assert groups
    assert all(group["title_complete"] is True for group in groups)
    assert all(group["title_zh"].startswith("完成情况 · ") for group in groups)
