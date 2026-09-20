"""Task 6.4 B 类疗效—安全性气泡图的面积和原始事实合同。"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import EfficacyArmRole, EfficacyFactRow
from ci_workflow.reports.b.pages import (
    BubblePoint,
    MatrixComparisonStatus,
    MatrixViewError,
    SampleSizeState,
    bubble_area,
    bubble_radius,
    build_bubble_matrix,
    build_matrix_comparison_rows,
)
from ci_workflow.reports.b.safety import SafetyArmRole, SafetyFactRow, SafetyFamily

_LOCATOR = EvidenceLocator(
    document_role="trial-results",
    table="Table 14.3.1",
    row="row",
    column="value",
)


def _efficacy(
    row_id: str,
    *,
    arm_role: EfficacyArmRole,
    arm_id: str,
    trial_id: str = "NCT00000001",
    product_id: str = "product-a",
    value: float | None = 60.0,
    direction: EndpointDirection = EndpointDirection.HIGHER_IS_BETTER,
    endpoint_family_id: str = "endpoint-easi75-response-v1",
    endpoint_role: str = "primary",
) -> EfficacyFactRow:
    is_lower = direction is EndpointDirection.LOWER_IS_BETTER
    endpoint_family_id = "endpoint-nps-change-v1" if is_lower else endpoint_family_id
    return EfficacyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=f"observation-{row_id}",
        product_id=product_id,
        trial_id=trial_id,
        endpoint_family_id=endpoint_family_id,
        endpoint_family_label_zh="鼻息肉评分变化" if is_lower else "EASI-75 应答率",
        compatibility_key=(endpoint_family_id, "timepoint-week-12-v1"),
        original_endpoint="nps" if is_lower else "easi75",
        original_definition="鼻息肉评分较基线变化" if is_lower else "EASI-75 应答者比例",
        endpoint_role=endpoint_role,
        direction=direction,
        unit="points" if is_lower else "%",
        analysis_form="change_from_baseline" if is_lower else "response_rate",
        actual_timepoint=12,
        actual_timepoint_unit="week",
        analysis_population="全分析集",
        arm_role=arm_role,
        arm_id=arm_id,
        arm_label="治疗组" if arm_role is EfficacyArmRole.TREATMENT else "安慰剂",
        value=value,
        denominator=100,
        disclosure_state=(
            FactDisclosureState.REPORTED_VALUE
            if value is not None
            else FactDisclosureState.NOT_REPORTED
        ),
        source_version_id="source-version-1",
        source_locator=_LOCATOR,
    )


def _safety(
    row_id: str,
    *,
    arm_role: SafetyArmRole,
    arm_id: str,
    trial_id: str = "NCT00000001",
    product_id: str = "product-a",
    value: float | None = 20.0,
    state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    family: SafetyFamily = SafetyFamily.TEAE,
    term_id: str = "teae-any",
    time_window_zh: str | None = "治疗期间",
    analysis_population_zh: str | None = "安全性分析集",
    denominator: int | None = 100,
) -> SafetyFactRow:
    return SafetyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=f"observation-{row_id}",
        product_id=product_id,
        trial_id=trial_id,
        family=family,
        term_id=term_id,
        source_term="任何治疗期间不良事件",
        event_definition_zh="治疗期间出现的不良事件",
        time_window_zh=time_window_zh,
        analysis_population_zh=analysis_population_zh,
        arm_role=arm_role,
        arm_id=arm_id,
        arm_label="治疗组" if arm_role is SafetyArmRole.TREATMENT else "安慰剂",
        value=value,
        raw_value=(f"{value:g}%" if value is not None else "原文未报告"),
        unit="%",
        denominator=denominator,
        disclosure_state=state,
        source_version_id="source-version-1",
        source_locator=_LOCATOR,
    )


def _facts(
    *, direction: EndpointDirection = EndpointDirection.HIGHER_IS_BETTER
) -> tuple[tuple[EfficacyFactRow, ...], tuple[SafetyFactRow, ...]]:
    return (
        _efficacy(
            "eff-treatment",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-treatment",
            value=60.0,
            direction=direction,
        ),
        _efficacy(
            "eff-control",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-control",
            value=30.0,
            direction=direction,
        ),
    ), (
        _safety(
            "safe-treatment", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment", value=20.0
        ),
        _safety("safe-control", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control", value=10.0),
    )


_SAMPLE_SIZES = {
    ("product-a", "NCT00000001", "arm-treatment"): 100,
}


def test_bubble_area_and_radius_preserve_the_declared_formula() -> None:
    radius = bubble_radius(100, radius_scale=2.0)
    area = bubble_area(100, radius_scale=2.0)
    assert radius is not None

    assert radius == pytest.approx(2.0 * math.sqrt(100 / math.pi))
    assert area == pytest.approx(math.pi * radius**2)
    assert math.pi * radius**2 / 2.0**2 == pytest.approx(100)
    assert area == pytest.approx(4.0 * 100)


def test_default_axes_use_direction_corrected_efficacy_and_raw_teae_with_reversed_axis() -> None:
    efficacy, safety = _facts()
    view = build_bubble_matrix(
        efficacy,
        safety,
        treatment_sample_sizes=_SAMPLE_SIZES,
        radius_scale=2.0,
    )

    assert len(view.points) == 1
    point = view.points[0]
    assert point.x_value == pytest.approx(30.0)
    assert point.raw_treatment_efficacy_value == 60.0
    assert point.raw_control_efficacy_value == 30.0
    assert point.y_value == pytest.approx(20.0)
    assert point.raw_safety_value == 20.0
    assert point.safety_axis_reversed is True
    assert point.radius == pytest.approx(2.0 * math.sqrt(100 / math.pi))
    assert point.area == pytest.approx(4.0 * 100)
    assert view.y_axis_note_zh == "向上 = 发生率更低 = 观察到的安全性位置更有利"
    assert view.is_ranked is False
    assert "score" not in str(view.model_dump()).lower()
    assert "rank" not in str(view.model_dump()).lower()


def test_lower_is_better_direction_is_corrected_without_rewriting_raw_values() -> None:
    efficacy, safety = _facts(direction=EndpointDirection.LOWER_IS_BETTER)
    efficacy = tuple(
        row.model_copy(
            update={"value": 20.0 if row.arm_role is EfficacyArmRole.TREATMENT else 30.0}
        )
        for row in efficacy
    )
    # Reconstruct through the public model to avoid accepting model_copy as a
    # source fact if a future validator changes its semantics.
    efficacy = tuple(
        EfficacyFactRow.model_validate(row.model_dump(mode="python")) for row in efficacy
    )

    point = build_bubble_matrix(
        efficacy, safety, treatment_sample_sizes=_SAMPLE_SIZES
    ).points[0]

    assert point.x_value == pytest.approx(10.0)
    assert point.raw_treatment_efficacy_value == 20.0
    assert point.raw_control_efficacy_value == 30.0


def test_comparison_rows_keep_trial_and_fact_identity_without_cross_trial_pooling() -> None:
    efficacy, safety = _facts()
    second_efficacy = (
        _efficacy(
            "eff-treatment-second",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-treatment",
            trial_id="NCT00000002",
            value=60.0,
        ),
        _efficacy(
            "eff-control-second",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-control",
            trial_id="NCT00000002",
            value=30.0,
        ),
    )
    second_safety = (
        _safety(
            "safe-treatment-second",
            arm_role=SafetyArmRole.TREATMENT,
            arm_id="arm-treatment",
            trial_id="NCT00000002",
            value=20.0,
        ),
        _safety(
            "safe-control-second",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="arm-control",
            trial_id="NCT00000002",
            value=10.0,
        ),
    )
    efficacy = (*efficacy, *second_efficacy)
    safety = (*safety, *second_safety)

    rows = build_matrix_comparison_rows(
        efficacy,
        safety,
        treatment_sample_sizes={
            ("product-a", "NCT00000001", "arm-treatment"): 100,
            ("product-a", "NCT00000002", "arm-treatment"): 100,
        },
    )
    view = build_bubble_matrix(rows)

    assert len(rows) == 2
    assert {row.trial_id for row in rows} == {"NCT00000001", "NCT00000002"}
    assert all(len(row.fact_row_ids) == 4 for row in rows)
    assert {point.trial_id for point in view.points} == {"NCT00000001", "NCT00000002"}
    assert {point.efficacy_fact_row_id for point in view.points} == {
        "eff-treatment",
        "eff-treatment-second",
    }
    assert {point.safety_fact_row_id for point in view.points} == {
        "safe-treatment",
        "safe-treatment-second",
    }


def test_unknown_treatment_sample_size_is_not_zero_and_does_not_create_a_point() -> None:
    efficacy, safety = _facts()
    view = build_bubble_matrix(
        efficacy,
        safety,
        treatment_sample_sizes={
            ("product-a", "NCT00000001", "arm-treatment"): None,
        },
    )
    row = view.comparison_rows[0]

    assert row.treatment_sample_size is None
    assert row.sample_size_state is SampleSizeState.UNKNOWN
    assert row.status is MatrixComparisonStatus.PENDING_VERIFICATION
    assert view.points == ()
    assert len(view.unplottable_rows) == 1
    assert "未知" in view.unplottable_rows[0].reason_zh


def test_unreported_efficacy_or_safety_remains_a_state_not_a_zero_coordinate() -> None:
    efficacy, safety = _facts()
    missing_efficacy = tuple(
        row.model_copy(update={"value": None, "disclosure_state": FactDisclosureState.NOT_REPORTED})
        for row in efficacy
    )
    missing_efficacy = tuple(
        EfficacyFactRow.model_validate(row.model_dump(mode="python")) for row in missing_efficacy
    )
    view = build_bubble_matrix(missing_efficacy, safety)

    assert view.points == ()
    assert view.comparison_rows[0].status is MatrixComparisonStatus.NOT_REPORTED
    assert view.comparison_rows[0].x_value is None
    assert "未报告" in view.unplottable_rows[0].reason_zh


def test_invalid_radius_and_unknown_sample_boundaries_fail_closed() -> None:
    with pytest.raises(MatrixViewError, match="半径系数"):
        bubble_radius(10, radius_scale=0)
    with pytest.raises(MatrixViewError, match="正整数"):
        bubble_radius(0)
    with pytest.raises(MatrixViewError, match="正整数"):
        bubble_area(-1)
    with pytest.raises((ValidationError, ValueError)):
        # A point cannot be made with the unknown sample-size boundary.

        BubblePoint(
            comparison_row_id="row",
            product_id="product-a",
            trial_id="NCT00000001",
            treatment_arm_id="arm-treatment",
            treatment_arm_label="治疗组",
            endpoint_family_id="easi75-response",
            efficacy_direction=EndpointDirection.HIGHER_IS_BETTER,
            x_value=1.0,
            y_value=20.0,
            safety_term_id="teae-any",
            safety_time_window_zh="治疗期间",
            safety_analysis_population_zh="安全性分析集",
            safety_unit="%",
            treatment_sample_size=0,
            efficacy_fact_row_id="eff-treatment",
            safety_fact_row_id="safe-treatment",
        )
