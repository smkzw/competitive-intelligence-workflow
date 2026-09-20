"""Task 6.6 B 类基线三页面视图的科学资格与同源投影合同。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.b.baseline import (
    BaselineDataType,
    BaselineObservation,
    BaselineStatisticForm,
    BaselineVariableDomain,
)
from ci_workflow.reports.b.baseline_views import (
    BaselineChartType,
    BaselineViewError,
    build_baseline_view_state,
)

_LOCATOR = EvidenceLocator(
    document_role="primary-trial-report",
    field_path="Table 1.baseline",
    table="Table 1",
    row="Treatment group",
    column="Value",
    page=12,
)


def _observation(
    token: str,
    *,
    product_id: str = "product-a",
    trial_id: str = "trial-1",
    cohort_id: str = "cohort-1",
    group_id: str | None = None,
    analysis_population: str = "全分析集",
    variable_domain: BaselineVariableDomain = BaselineVariableDomain.DEMOGRAPHICS,
    source_name: str = "Age",
    source_definition: str = "Age at baseline",
    standardized_concept: str = "age",
    scale: str | None = None,
    scale_version: str | None = None,
    direction: str | None = None,
    theoretical_range: str | None = None,
    data_type: BaselineDataType = BaselineDataType.CONTINUOUS,
    statistic_form: BaselineStatisticForm = BaselineStatisticForm.MEAN,
    value: int | float | None = 54.3,
    raw_value: str | None = "54.3 (12.1)",
    unit: str | None = "岁",
    dispersion: int | float | None = 12.1,
    range_lower: int | float | None = None,
    range_upper: int | float | None = None,
    category_level: str | None = None,
    bin_label: str | None = None,
    bin_lower: int | float | None = None,
    bin_upper: int | float | None = None,
    numerator: int | None = None,
    denominator: int | None = 100,
    denominator_role: str | None = "随机化人群",
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    reported_zero_text: str | None = None,
    route_receipt_id: str | None = None,
    applicability_predicate_id: str | None = None,
    conflict_disposition: ConflictDisposition = (
        ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
    ),
    difference_labels_zh: tuple[str, ...] = (),
    **overrides: Any,
) -> BaselineObservation:
    """Build one valid Task 6.5 observation while keeping source identity explicit."""

    effective_group_id = group_id or f"group-{token}"
    if disclosure_state in {
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    }:
        value = None
        raw_value = None
        dispersion = None
        range_lower = None
        range_upper = None
        bin_lower = None
        bin_upper = None
        numerator = None
        denominator = None
    if disclosure_state is FactDisclosureState.NOT_APPLICABLE:
        value = None
        raw_value = None
        dispersion = None
        range_lower = None
        range_upper = None
        bin_lower = None
        bin_upper = None
        numerator = None
        denominator = None
        applicability_predicate_id = applicability_predicate_id or "predicate-baseline-v1"
    if disclosure_state is FactDisclosureState.REPORTED_ZERO:
        value = 0
        raw_value = raw_value or "0"
        reported_zero_text = reported_zero_text or "原文报告为 0"
        dispersion = None

    payload: dict[str, object] = {
        "row_id": f"baseline-row-{token}",
        "source_row_id": f"source-row-{token}",
        "observation_id": f"baseline-observation-{token}",
        "product_id": product_id,
        "trial_id": trial_id,
        "cohort_id": cohort_id,
        "group_id": effective_group_id,
        "analysis_population": analysis_population,
        "variable_domain": variable_domain,
        "source_name": source_name,
        "source_definition": source_definition,
        "standardized_concept": standardized_concept,
        "scale": scale,
        "scale_version": scale_version,
        "direction": direction,
        "theoretical_range": theoretical_range,
        "data_type": data_type,
        "statistic_form": statistic_form,
        "value": value,
        "raw_value": raw_value,
        "unit": unit,
        "dispersion": dispersion,
        "range_lower": range_lower,
        "range_upper": range_upper,
        "category_level": category_level,
        "bin_label": bin_label,
        "bin_lower": bin_lower,
        "bin_upper": bin_upper,
        "numerator": numerator,
        "denominator": denominator,
        "denominator_role": denominator_role,
        "baseline_definition": "首次给药前最近一次评估",
        "baseline_timepoint": "基线",
        "source_version_id": "source-version-1",
        "source_locator": _LOCATOR,
        "source_role": SourceRole.PRIMARY_TRIAL_REPORT,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": disclosure_state,
        "conflict_disposition": conflict_disposition,
        "reported_zero_text": reported_zero_text,
        "route_receipt_id": route_receipt_id,
        "applicability_predicate_id": applicability_predicate_id,
        "compatibility_rule": "baseline-view-compatibility-v1",
        "difference_labels_zh": difference_labels_zh,
    }
    payload.update(overrides)
    return BaselineObservation.model_validate(payload)


def _proportion(
    token: str,
    *,
    concept: str = "sex",
    category: str = "女性",
    numerator: int | None = 45,
    denominator: int | None = 100,
    value: float | None = 45.0,
    **overrides: Any,
) -> BaselineObservation:
    return _observation(
        token,
        source_name="Sex",
        source_definition="Sex at baseline",
        standardized_concept=concept,
        data_type=BaselineDataType.CATEGORICAL,
        statistic_form=BaselineStatisticForm.PROPORTION,
        value=value,
        raw_value=f"{numerator}/{denominator}（{value}%）" if value is not None else None,
        unit="%",
        dispersion=None,
        category_level=category,
        numerator=numerator,
        denominator=denominator,
        **overrides,
    )


def _severity(
    token: str,
    *,
    concept: str = "easi_total_score",
    scale: str = "EASI",
    scale_version: str = "v1",
    direction: str = "higher_is_more_severe",
    statistic_form: BaselineStatisticForm = BaselineStatisticForm.MEAN,
    value: int | float | None = 24.5,
    dispersion: int | float | None = 8.1,
    range_lower: int | float | None = None,
    range_upper: int | float | None = None,
    unit: str = "分",
    difference_labels_zh: tuple[str, ...] = (),
    **overrides: object,
) -> BaselineObservation:
    is_interval = statistic_form in {
        BaselineStatisticForm.QUARTILES,
        BaselineStatisticForm.RANGE,
    }
    payload: dict[str, Any] = {
        "variable_domain": BaselineVariableDomain.BASELINE_SEVERITY,
        "source_name": "EASI total score",
        "source_definition": "EASI total score at baseline",
        "standardized_concept": concept,
        "scale": scale,
        "scale_version": scale_version,
        "direction": direction,
        "theoretical_range": "0–72",
        "statistic_form": statistic_form,
        "value": None if is_interval else value,
        "raw_value": "24.5（8.1）" if not is_interval else "18–32",
        "unit": unit,
        "dispersion": None if is_interval else dispersion,
        "range_lower": range_lower if is_interval else None,
        "range_upper": range_upper if is_interval else None,
        "difference_labels_zh": difference_labels_zh,
    }
    payload.update(overrides)
    return _observation(token, **payload)


def _panel_for(state: Any, concept: str, statistic_form: BaselineStatisticForm) -> Any:
    panels = [
        panel
        for panel in state.chart_panels
        if panel.standardized_concept == concept
        and panel.statistic_form is statistic_form
    ]
    assert len(panels) == 1
    return panels[0]


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _row_by_fact_id(rows: Iterable[Any]) -> dict[str, Any]:
    return {row.row_id: row for row in rows}


def test_continuous_forms_are_split_and_only_source_intervals_draw_ranges() -> None:
    rows = (
        _observation("age-mean", statistic_form=BaselineStatisticForm.MEAN),
        _observation(
            "age-median",
            group_id="group-age-median",
            statistic_form=BaselineStatisticForm.MEDIAN,
            value=52.0,
            raw_value="52（四分位距 44–60）",
            dispersion=None,
        ),
        _observation(
            "age-quartiles",
            group_id="group-age-quartiles",
            statistic_form=BaselineStatisticForm.QUARTILES,
            value=None,
            raw_value="四分位数 44–60",
            dispersion=None,
            range_lower=44.0,
            range_upper=60.0,
        ),
        _observation(
            "age-range",
            group_id="group-age-range",
            statistic_form=BaselineStatisticForm.RANGE,
            value=None,
            raw_value="范围 18–81",
            dispersion=None,
            range_lower=18.0,
            range_upper=81.0,
        ),
    )

    state = build_baseline_view_state(rows)

    assert len(state.chart_panels) == 4
    mean_panel = _panel_for(state, "age", BaselineStatisticForm.MEAN)
    median_panel = _panel_for(state, "age", BaselineStatisticForm.MEDIAN)
    quartiles_panel = _panel_for(state, "age", BaselineStatisticForm.QUARTILES)
    range_panel = _panel_for(state, "age", BaselineStatisticForm.RANGE)
    assert _enum_value(mean_panel.chart_type) == BaselineChartType.POINT.value
    assert _enum_value(median_panel.chart_type) == BaselineChartType.POINT.value
    assert _enum_value(quartiles_panel.chart_type) == BaselineChartType.INTERVAL.value
    assert _enum_value(range_panel.chart_type) == BaselineChartType.INTERVAL.value
    assert mean_panel.drawable_rows[0].value == 54.3
    assert mean_panel.drawable_rows[0].dispersion == 12.1
    assert median_panel.drawable_rows[0].value == 52.0
    assert median_panel.drawable_rows[0].dispersion is None
    assert quartiles_panel.drawable_rows[0].value is None
    assert quartiles_panel.drawable_rows[0].range_lower == 44.0
    assert quartiles_panel.drawable_rows[0].range_upper == 60.0
    assert range_panel.drawable_rows[0].range_lower == 18.0
    assert range_panel.drawable_rows[0].range_upper == 81.0
    assert {
        row.row_id
        for panel in state.chart_panels
        for row in panel.drawable_rows
    } == {row.row_id for row in rows}


def test_center_only_continuous_fact_gets_labeled_point_without_synthetic_error_bar() -> None:
    row = _observation(
        "bmi-center-only",
        source_name="BMI",
        source_definition="Body mass index at baseline",
        standardized_concept="bmi",
        unit="kg/m²",
        value=25.6,
        raw_value="25.6",
        dispersion=None,
        denominator=None,
    )

    state = build_baseline_view_state((row,))
    panel = _panel_for(state, "bmi", BaselineStatisticForm.MEAN)

    assert _enum_value(panel.chart_type) == BaselineChartType.POINT.value
    assert panel.drawable_rows[0].value == 25.6
    assert panel.drawable_rows[0].dispersion is None
    assert panel.drawable_rows[0].range_lower is None
    assert panel.drawable_rows[0].range_upper is None
    assert panel.drawable_rows[0].value_label == "25.6 kg/m²"


def test_categorical_proportions_need_denominator_and_never_become_100_percent_stack() -> None:
    female = _proportion("sex-female", category="女性")
    male = _proportion("sex-male", category="男性", numerator=55, value=55.0)
    incomplete = _proportion(
        "ethnicity-han",
        concept="ethnicity",
        category="汉族",
        numerator=70,
        value=70.0,
    )

    state = build_baseline_view_state((male, incomplete, female))
    sex_panel = _panel_for(state, "sex", BaselineStatisticForm.PROPORTION)
    ethnicity_panel = _panel_for(state, "ethnicity", BaselineStatisticForm.PROPORTION)

    assert _enum_value(sex_panel.chart_type) == BaselineChartType.PROPORTION_BAR.value
    assert _enum_value(ethnicity_panel.chart_type) == BaselineChartType.PROPORTION_BAR.value
    assert sex_panel.is_stacked is False
    assert ethnicity_panel.is_stacked is False
    assert {row.category_level for row in sex_panel.drawable_rows} == {"女性", "男性"}
    assert ethnicity_panel.drawable_rows[0].denominator == 100

    no_denominator = _proportion(
        "sex-no-denominator",
        category="未知",
        numerator=None,
        denominator=None,
        value=None,
        disclosure_state=FactDisclosureState.NOT_REPORTED,
    )
    no_denominator_state = build_baseline_view_state((no_denominator,))
    no_denominator_panel = _panel_for(
        no_denominator_state, "sex", BaselineStatisticForm.PROPORTION
    )
    assert no_denominator_panel.drawable_rows == ()
    assert no_denominator_panel.status_rows[0].disclosure_state is FactDisclosureState.NOT_REPORTED
    assert _enum_value(no_denominator_panel.chart_type) == BaselineChartType.DISCLOSURE.value


def test_incompatible_severity_scales_and_statistics_form_separate_small_multiples() -> None:
    easi_v1 = _severity("severity-easi-v1", value=24.5)
    easi_v2 = _severity(
        "severity-easi-v2",
        group_id="group-severity-v2",
        scale_version="v2",
        value=25.2,
        difference_labels_zh=("量表版本不同，拆分小多图",),
    )
    itch = _severity(
        "severity-itch",
        group_id="group-severity-itch",
        concept="pruritus_nrs",
        scale="NRS",
        scale_version="v1",
        theoretical_range="0–10",
        value=6.0,
        unit="分",
        source_name="Pruritus NRS",
        source_definition="Pruritus numerical rating scale at baseline",
    )
    median = _severity(
        "severity-easi-median",
        group_id="group-severity-median",
        statistic_form=BaselineStatisticForm.MEDIAN,
        value=23.0,
        dispersion=None,
    )

    state = build_baseline_view_state((itch, median, easi_v2, easi_v1))

    easi_panels = [
        panel
        for panel in state.chart_panels
        if panel.standardized_concept == "easi_total_score"
    ]
    assert len(easi_panels) == 3
    assert len({panel.compatibility_bucket_id for panel in easi_panels}) == 3
    assert all(
        _enum_value(panel.chart_type) == BaselineChartType.SMALL_MULTIPLE.value
        for panel in easi_panels
    )
    assert all(panel.is_mixed_compatibility is False for panel in easi_panels)
    assert any("量表版本不同" in "；".join(panel.difference_labels_zh) for panel in easi_panels)
    assert all(
        "理论范围不同，拆分小多图" not in panel.difference_labels_zh
        for panel in easi_panels
    ), "EASI 面板不得混入 NRS 的理论范围差异"
    assert any(panel.standardized_concept == "pruritus_nrs" for panel in state.chart_panels)
    assert all(
        len({row.compatibility_bucket_id for row in panel.drawable_rows}) <= 1
        for panel in state.chart_panels
    )


def test_default_variable_order_is_stable_identity_order_not_numeric_merit_order() -> None:
    rows = (
        _severity("severity-itch", concept="pruritus_nrs", group_id="group-itch", value=99.0),
        _observation(
            "demographics-bmi",
            group_id="group-bmi",
            source_name="BMI",
            source_definition="Body mass index at baseline",
            standardized_concept="bmi",
            value=18.2,
            raw_value="18.2",
            dispersion=None,
            unit="kg/m²",
            denominator=None,
        ),
        _severity("severity-easi", group_id="group-easi", value=10.0),
        _proportion("demographics-sex", category="女性", numerator=45, value=45.0),
        _observation(
            "demographics-age",
            group_id="group-age",
            standardized_concept="age",
            value=90.0,
            raw_value="90.0",
            dispersion=None,
        ),
        _observation(
            "sample-size",
            group_id="group-sample-size",
            source_name="Randomized population",
            source_definition="Randomized population at baseline",
            standardized_concept="baseline_sample_size",
            data_type=BaselineDataType.COUNT,
            statistic_form=BaselineStatisticForm.SAMPLE_SIZE,
            value=12,
            raw_value="12",
            unit="例",
            dispersion=None,
            denominator=None,
        ),
        _observation(
            "disease-duration",
            group_id="group-duration",
            variable_domain=BaselineVariableDomain.DISEASE_CONTEXT,
            source_name="Disease duration",
            source_definition="Disease duration at baseline",
            standardized_concept="disease_duration",
            value=7.5,
            raw_value="7.5",
            unit="年",
            dispersion=None,
            denominator=None,
        ),
    )

    first = build_baseline_view_state(rows)
    second = build_baseline_view_state(tuple(reversed(rows)))
    first_order = [panel.standardized_concept for panel in first.chart_panels]
    second_order = [panel.standardized_concept for panel in second.chart_panels]

    assert first_order == second_order
    assert first_order[:4] == [
        "baseline_sample_size",
        "age",
        "sex",
        "easi_total_score",
    ]
    assert first_order.index("disease_duration") < first_order.index("pruritus_nrs")
    assert first_order.index("age") < first_order.index("bmi")
    assert first_order.index("easi_total_score") < first_order.index("pruritus_nrs")
    assert first_order != sorted(first_order)


def test_complete_table_is_lossless_and_chart_rows_are_a_subset_of_same_fact_identity() -> None:
    rows = (
        _observation("age", value=54.3, raw_value="54.3（12.1）"),
        _proportion("sex", category="女性", numerator=45, value=45.0),
        _observation(
            "not-public",
            group_id="group-not-public",
            standardized_concept="body_surface_area",
            source_name="BSA",
            source_definition="Body surface area at baseline",
            disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        ),
    )

    state = build_baseline_view_state(rows)
    table = _row_by_fact_id(state.complete_table)
    assert set(table) == {row.row_id for row in rows}
    assert tuple(row.row_id for row in state.complete_table) == state.table_row_ids
    assert {row.row_id for panel in state.chart_panels for row in panel.drawable_rows} <= set(table)
    assert set(state.evidence_links_by_row_id) == set(table)

    original_by_id = {row.row_id: row for row in rows}
    for row_id, projected in table.items():
        original = original_by_id[row_id]
        assert projected.source_row_id == original.source_row_id
        assert projected.observation_id == original.observation_id
        assert projected.raw_value == original.raw_value
        assert projected.value == original.value
        assert projected.statistic_form is original.statistic_form
        assert projected.denominator == original.denominator
        assert projected.disclosure_state is original.disclosure_state
        assert projected.compatibility_bucket_id == original.compatibility_bucket_id
        assert projected.source_locator == original.source_locator
        assert projected.difference_labels_zh == original.difference_labels_zh


def test_all_missing_states_remain_distinct_chinese_table_states_without_coordinates() -> None:
    missing_rows = (
        _observation(
            "not-reported",
            standardized_concept="x-not-reported",
            disclosure_state=FactDisclosureState.NOT_REPORTED,
        ),
        _observation(
            "below-threshold",
            group_id="group-below-threshold",
            standardized_concept="x-below-threshold",
            disclosure_state=FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        ),
        _observation(
            "not-publicly-disclosed",
            group_id="group-not-publicly-disclosed",
            standardized_concept="x-not-publicly-disclosed",
            disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        ),
        _observation(
            "route-unresolved",
            group_id="group-route-unresolved",
            standardized_concept="x-route-unresolved",
            disclosure_state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
            route_receipt_id="route-v1",
        ),
        _observation(
            "not-applicable",
            group_id="group-not-applicable",
            standardized_concept="x-not-applicable",
            disclosure_state=FactDisclosureState.NOT_APPLICABLE,
        ),
        _observation(
            "conflicting",
            group_id="group-conflicting",
            standardized_concept="x-conflicting",
            disclosure_state=FactDisclosureState.CONFLICTING,
            conflict_disposition=ConflictDisposition.OPEN_CONFLICT_PRESERVED,
        ),
        _observation(
            "reported-zero",
            group_id="group-reported-zero",
            standardized_concept="x-reported-zero",
            value=0,
            raw_value="0",
            dispersion=None,
            disclosure_state=FactDisclosureState.REPORTED_ZERO,
            reported_zero_text="原文报告为 0",
        ),
    )

    state = build_baseline_view_state(missing_rows)
    table = _row_by_fact_id(state.complete_table)
    labels = {row.disclosure_state: row.disclosure_label_zh for row in table.values()}
    assert labels == {
        FactDisclosureState.NOT_REPORTED: "原文未报告",
        FactDisclosureState.BELOW_REPORTING_THRESHOLD: "低于来源列示阈值",
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED: "未公开",
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE: "技术路径未解决",
        FactDisclosureState.NOT_APPLICABLE: "不适用",
        FactDisclosureState.CONFLICTING: "来源存在冲突",
        FactDisclosureState.REPORTED_ZERO: "已报告为零",
    }
    assert all(
        row.row_id
        not in {
            point.row_id
            for panel in state.chart_panels
            for point in panel.drawable_rows
        }
        for row in state.complete_table
        if row.disclosure_state is not FactDisclosureState.REPORTED_ZERO
    )
    assert all(
        panel.has_axes is False
        for panel in state.chart_panels
        if panel.status_rows and not panel.drawable_rows
    )
    assert all("pending" not in row.disclosure_label_zh.casefold() for row in state.complete_table)


def test_model_copy_tampering_is_revalidated_and_duplicate_facts_fail_closed() -> None:
    row = _observation("tamper")
    forged = row.model_copy(update={"standardized_concept": "forged-age"})
    with pytest.raises(BaselineViewError, match="重新校验|原始观察"):
        build_baseline_view_state((forged,))

    with pytest.raises(BaselineViewError, match="重复 row_id|重复事实"):
        build_baseline_view_state((row, row))


def test_empty_input_is_a_real_chinese_empty_state_not_an_unbounded_default() -> None:
    state = build_baseline_view_state(())

    assert state.complete_table == ()
    assert state.chart_panels == ()
    assert state.empty_state.is_empty is True
    assert state.empty_state.message_zh == "当前筛选范围暂无基线事实"
    assert "baseline" not in state.empty_state.message_zh.casefold()
    assert "pending" not in state.empty_state.message_zh.casefold()
