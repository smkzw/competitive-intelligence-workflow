"""R13 B 类跨产品/试验语义归一化与图表分组合同。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    _display_locator,
    _efficacy_records,
    _filter_dimensions,
    _group,
    _groups_for_page,
    _matrix_records,
    _page_records,
    _project_record,
    _safety_records,
    _synthetic_status_records,
    load_report_b_data,
    render_report_b_site,
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


def test_safety_view_declared_shadow_never_reaches_display_records() -> None:
    payload = json.loads(PNH_DATA.read_text(encoding="utf-8"))
    source_row = payload["safety"][0]
    payload["safety_views"] = {
        "facts": [source_row, {**source_row, "row_id": source_row["row_id"] + "-declared"}]
    }
    data = ReportBPortalData.model_validate(payload)
    names = {row.id: row.name for row in data.products}
    trial_names = {row.id: row.display_id for row in data.trials}

    records = _safety_records(data, names, trial_names)

    visible_ids = {row["row_id"] for row, _source in records}
    assert source_row["row_id"] in visible_ids
    assert source_row["row_id"] + "-declared" not in visible_ids


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
        "EASI-75应答 · 应答率 · 约6个月 · 全分析集",
        "EASI-75应答 · 均值 · 约6个月 · 全分析集",
        "EASI-75应答 · 应答率 · 约第12周 · 全分析集",
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


def test_chart_comparison_context_pairs_only_same_exact_period() -> None:
    treatment_1 = _project_efficacy("treatment-1", "EASI-75")
    treatment_2 = dict(treatment_1, row_id="treatment-2")
    control_1 = dict(treatment_1, row_id="control-1", arm_role="control", arm="对照组")
    control_2 = dict(control_1, row_id="control-2")
    for row, period in (
        (treatment_1, "Treatment Period 1"),
        (treatment_2, "Treatment Period 2"),
        (control_1, "Treatment Period 1"),
        (control_2, "Treatment Period 2"),
    ):
        row["time"] = period
    group = _group(
        "分期结果", tuple((row, None) for row in (
            treatment_1, treatment_2, control_2, control_1,
        )), chart_type="bar", identity_series=True,
    )
    contexts = {row["row_id"]: row["_chart_comparison_context_key"] for row in group["rows"]}
    assert contexts["treatment-1"] == contexts["control-1"]
    assert contexts["treatment-2"] == contexts["control-2"]
    assert contexts["treatment-1"] != contexts["treatment-2"]


def test_chart_context_keeps_raw_window_and_cohort_separate() -> None:
    for field in ("time_window", "cohort"):
        treatment_1 = _project_efficacy("treatment-1", "EASI-75")
        treatment_2 = dict(treatment_1, row_id="treatment-2")
        control_1 = dict(treatment_1, row_id="control-1", arm_role="control", arm="对照组")
        control_2 = dict(control_1, row_id="control-2")
        for row, period in (
            (treatment_1, "Treatment Period 1"),
            (treatment_2, "Treatment Period 2"),
            (control_1, "Treatment Period 1"),
            (control_2, "Treatment Period 2"),
        ):
            row["time"] = "第24周"
            row[field] = period
        projected = tuple(
            _project_record(
                row, domain="efficacy", names={"product-a": "产品甲"},
                trial_names={"trial-a": "试验甲"}, fallback=str(row["row_id"]),
            ) for row in (treatment_1, treatment_2, control_2, control_1)
        )
        group = _group(
            "分期结果", tuple((row, None) for row in projected),
            chart_type="bar", identity_series=True,
        )
        contexts = {
            row["row_id"]: row["_chart_comparison_context_key"] for row in group["rows"]
        }
        assert contexts["treatment-1"] == contexts["control-1"]
        assert contexts["treatment-2"] == contexts["control-2"]
        assert contexts["treatment-1"] != contexts["treatment-2"], field


def test_chart_context_label_uses_compact_source_period_not_registry_key() -> None:
    row = _project_efficacy("treatment-1", "EASI-75")
    row.update(
        time="Treatment Period 1 (TP1)",
        time_window="给药 第1周期（TP1）",
        period="nct04469465-p0",
        cohort="nct04469465-全部",
    )
    group = _group("分期结果", ((row, None),), chart_type="bar", identity_series=True)
    label = group["rows"][0]["_chart_comparison_context_label"]
    assert "TP1" in label and "p0" in label
    assert "nct04469465" not in label.casefold()
    assert len(label) < 50


def test_matrix_percentage_difference_is_labeled_percentage_points() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trials = {row.id: row.display_id for row in data.trials}
    groups = _groups_for_page(
        "efficacy-safety-matrix", _matrix_records(data, names, trials)
    )
    assert len(groups) == 1
    assert groups[0]["rows"][0]["x_value"] == 80.5
    assert groups[0]["x_unit"] == "百分点"
    assert groups[0]["x_axis_label_zh"] == "试验内疗效差（百分点）"


def test_unformed_matrix_is_not_called_unpublished_source_result() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trials = {row.id: row.display_id for row in data.trials}
    records = _synthetic_status_records(
        data, page_id="efficacy-safety-matrix", names=names,
        trial_names=trials, domain="matrix",
    )
    assert records
    assert all(row["disclosure_state"] == "not_applicable" for row, _ in records)
    assert all("不等于研究未公开结果" in row["reason"] for row, _ in records)
    groups = _groups_for_page("efficacy-safety-matrix", records)
    assert groups[0]["empty_message"] == "当前未形成可绘制的试验内比较"


def test_empty_typed_matrix_retains_efficacy_view_studies(tmp_path: Path) -> None:
    payload = json.loads(PNH_DATA.read_text(encoding="utf-8"))
    payload["efficacy_views"] = {"facts": payload["efficacy"]}
    payload["efficacy"] = []
    payload["matrix_view"] = {"rows": []}
    data = ReportBPortalData.model_validate(payload)
    names = {row.id: row.name for row in data.products}
    trials = {row.id: row.display_id for row in data.trials}
    view_trial_ids = {
        row["trial_id"] for row, _ in _efficacy_records(data, names, trials)
    }
    assert len(view_trial_ids) == 2
    records = _page_records(
        data, page_id="efficacy-safety-matrix", names=names, trial_names=trials,
        efficacy=_efficacy_records(data, names, trials),
        safety=_safety_records(data, names, trials),
    )
    assert {row["trial_id"] for row, _ in records} == view_trial_ids
    assert all(row["renderable"] is False for row, _ in records)
    render_report_b_site(data, tmp_path / "b")
    html = (tmp_path / "b" / "efficacy-safety-matrix.html").read_text(encoding="utf-8")
    assert "未进入气泡坐标的相关研究（2）" in html


def test_partial_precise_views_preserve_other_efficacy_and_safety_studies() -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text(
            encoding="utf-8"
        )
    )
    first_efficacy = payload["efficacy"][0]
    first_safety = payload["safety"][0]
    first_safety["value"] = 0.0
    payload["efficacy_views"] = {"coverage_mode": "partial", "facts": [{
        **first_efficacy,
        "source_version_id": "source-version-verified-efficacy",
        "source_text": "68.4",
    }]}
    payload["safety_views"] = {"coverage_mode": "partial", "facts": [{
        **first_safety,
        "source_version_id": "source-version-verified-safety",
        "source_text": "0",
        "disclosure_state": "reported_zero",
    }]}
    data = ReportBPortalData.model_validate(payload)
    names = {product.id: product.name for product in data.products}
    trials = {trial.id: trial.display_id for trial in data.trials}
    efficacy = _efficacy_records(data, names, trials)
    safety = _safety_records(data, names, trials)

    assert {row["row_id"] for row, _ in efficacy} == {
        row["row_id"] for row in payload["efficacy"]
    }
    assert {row["row_id"] for row, _ in safety} == {
        row["row_id"] for row in payload["safety"]
    }
    assert len(efficacy) == len(payload["efficacy"])
    assert len(safety) == len(payload["safety"])
    assert efficacy[0][0]["source_version_id"] == "source-version-verified-efficacy"
    assert safety[0][0]["source_version_id"] == "source-version-verified-safety"


def test_explicit_view_link_replaces_one_legacy_row_without_losing_others() -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text(
            encoding="utf-8"
        )
    )
    original = payload["efficacy"][0]
    original["source_view_row_id"] = "verified-observation-1"
    payload["efficacy_views"] = {"coverage_mode": "partial", "facts": [{
        **original,
        "row_id": "verified-observation-1",
        "source_version_id": "source-version-verified",
    }]}
    data = ReportBPortalData.model_validate(payload)
    names = {product.id: product.name for product in data.products}
    trials = {trial.id: trial.display_id for trial in data.trials}
    rows = _efficacy_records(data, names, trials)

    assert len(rows) == len(payload["efficacy"])
    assert {row["row_id"] for row, _ in rows} == {
        "verified-observation-1",
        *(item["row_id"] for item in payload["efficacy"][1:]),
    }


def test_partial_precise_view_rejects_conflicting_overlap() -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text(
            encoding="utf-8"
        )
    )
    payload["efficacy_views"] = {"coverage_mode": "partial", "facts": [{
        **payload["efficacy"][0],
        "value": 99.0,
    }]}
    data = ReportBPortalData.model_validate(payload)
    names = {product.id: product.name for product in data.products}
    trials = {trial.id: trial.display_id for trial in data.trials}
    with pytest.raises(ValueError, match="来源视图.*领域行.*冲突"):
        _efficacy_records(data, names, trials)


def test_publication_locator_is_not_replaced_by_registry_trial_link() -> None:
    locator = _display_locator({
        "trial_id": "NCT04820530",
        "source_locator": {
            "document_role": "publication",
            "table": "Table 2",
            "url": "https://example.org/article/123",
        },
    }, "eff-publication")
    assert locator.url == "https://example.org/article/123"
    assert locator.table == "Table 2"


def test_registered_json_field_anchor_is_visible_in_b_evidence() -> None:
    locator = _display_locator({
        "source_locator": {
            "document_role": "registry",
            "field_path": "$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0]",
            "url": "https://clinicaltrials.gov/study/NCT04820530",
        },
    }, "eff-source-row")
    assert locator.field_path == (
        "$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0]"
    )


@pytest.mark.parametrize("locator_form", ["source_field_path", "source_locator"])
def test_untrusted_local_path_cannot_be_promoted_to_source_field(
    locator_form: str,
) -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text(
            encoding="utf-8"
        )
    )
    payload["efficacy_views"] = {"coverage_mode": "partial", "facts": []}
    data = ReportBPortalData.model_validate(payload)
    names = {item.id: item.name for item in data.products}
    trials = {item.id: item.name for item in data.trials}
    row, _source = _efficacy_records(data, names, trials)[0]
    source = {
        "source_version_id": "claimed-version",
        locator_form: (
            "/Users/example/internal.json"
            if locator_form == "source_field_path"
            else {"document_role": "registry", "field_path": "/Users/example/internal.json"}
        ),
        "source_text": "68.4",
    }
    from ci_workflow.renderers.portal.report_b import _evidence_view
    from ci_workflow.reports.common.evidence_view import EvidenceObservationKind
    view = _evidence_view(
        data, row=row, source=source, page_id="efficacy",
        observation_kind=EvidenceObservationKind.GENERAL,
        names=names, trial_names=trials,
    )
    assert view.source_trace_state == "unverified"
    assert view.locator is None


def test_explicit_complete_view_must_cover_every_domain_row() -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text(
            encoding="utf-8"
        )
    )
    names = {row["id"]: row["name"] for row in payload["products"]}
    trials = {row["id"]: row["display_id"] for row in payload["trials"]}
    payload["efficacy_views"] = {
        "coverage_mode": "complete", "facts": [payload["efficacy"][0]],
    }
    with pytest.raises(ValueError, match="完整.*遗漏"):
        _efficacy_records(ReportBPortalData.model_validate(payload), names, trials)

    payload["efficacy_views"] = {"coverage_mode": "complete", "facts": []}
    with pytest.raises(ValueError, match="完整.*遗漏"):
        _efficacy_records(ReportBPortalData.model_validate(payload), names, trials)

    payload["efficacy_views"]["facts"] = payload["efficacy"]
    complete = _efficacy_records(ReportBPortalData.model_validate(payload), names, trials)
    assert len(complete) == len(payload["efficacy"])


def test_b_view_only_efficacy_does_not_relax_a_completeness() -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text(
            encoding="utf-8"
        )
    )
    payload["efficacy"] = []
    with pytest.raises(ValueError, match="疗效比较缺少治疗组或对照组"):
        ReportAPortalData.model_validate(payload)


def test_unknown_semantics_keep_trials_in_adjacent_descriptive_groups() -> None:
    first = _project_efficacy("first", "EASI-75")
    second = dict(first, row_id="second", trial_id="trial-b")
    groups = _groups_for_page("efficacy", [(first, None), (second, None)])
    assert len(groups) == 2
    assert all(group["cross_trial"] is False for group in groups)
    assert all("登记分组信息不全" not in group["title_zh"] for group in groups)
    assert {row["row_id"] for group in groups for row in group["rows"]} == {
        "first", "second",
    }


def test_missing_registered_arm_is_disclosed_without_cross_trial_merge() -> None:
    first = _project_efficacy("first", "EASI-75")
    second = dict(first, row_id="second", trial_id="trial-b")
    for row in (first, second):
        row["arm"] = ""
        row["arm_role"] = "unknown"
        row["group_id"] = ""

    groups = _groups_for_page("efficacy", [(first, None), (second, None)])

    assert len(groups) == 2
    assert all(group["cross_trial"] is False for group in groups)
    assert all("登记分组信息不全" in group["title_zh"] for group in groups)


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
