"""Task 6.2 B 类疗效事实和三类视图合同。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import (
    EfficacyArmRole,
    EfficacyFactRow,
    EfficacyViewError,
    build_efficacy_views,
)


def _fact(
    row_id: str,
    *,
    arm_role: str,
    arm_id: str,
    timepoint: int,
    value: float | None,
    effect_value: float | None = None,
) -> EfficacyFactRow:
    return EfficacyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=f"obs-{row_id}",
        product_id="product-a",
        trial_id="NCT00000001",
        endpoint_family_id="endpoint-easi75-response-v1",
        endpoint_family_label_zh="EASI-75",
        compatibility_key=(
            "endpoint-easi75-response-v1",
            "timepoint-week-12-v1" if timepoint <= 14 else "timepoint-week-24-v1",
        ),
        original_endpoint="easi75",
        original_definition="EASI-75 应答者比例",
        endpoint_role="primary",
        direction=EndpointDirection.HIGHER_IS_BETTER,
        unit="%",
        analysis_form="response_rate",
        actual_timepoint=timepoint,
        actual_timepoint_unit="week",
        analysis_population="全分析集",
        arm_role=EfficacyArmRole(arm_role),
        arm_id=arm_id,
        arm_label="治疗组" if arm_role == "treatment" else "安慰剂",
        value=value,
        denominator=100,
        source_version_id="source-version-1",
        source_locator=EvidenceLocator(
            document_role="trial-results",
            table="Table 1",
            row=f"row-{row_id}",
            column="value",
        ),
        effect_measure="risk_difference" if effect_value is not None else None,
        effect_value=effect_value,
        effect_lower=(effect_value - 0.1) if effect_value is not None else None,
        effect_upper=(effect_value + 0.1) if effect_value is not None else None,
        comparison_id="comparison-a",
    )


def test_three_views_share_immutable_fact_rows_and_parallel_arms() -> None:
    treatment_12 = _fact(
        "t-12",
        arm_role="treatment",
        arm_id="arm-t",
        timepoint=12,
        value=61.0,
        effect_value=0.3,
    )
    control_12 = _fact("c-12", arm_role="control", arm_id="arm-c", timepoint=12, value=31.0)
    treatment_24 = _fact(
        "t-24",
        arm_role="treatment",
        arm_id="arm-t",
        timepoint=24,
        value=68.0,
        effect_value=0.4,
    )
    control_24 = _fact("c-24", arm_role="control", arm_id="arm-c", timepoint=24, value=35.0)

    views = build_efficacy_views((control_24, treatment_24, control_12, treatment_12))

    assert len(views.single_timepoint_views) == 2
    assert len(views.longitudinal_views) == 1
    assert len(views.source_effect_size_views) == 2
    assert all(comparison.has_both_arms for comparison in views.longitudinal_views[0].comparisons)
    assert views.longitudinal_views[0].compatibility_key is None
    assert views.longitudinal_views[0].compatibility_keys == (
        ("endpoint-easi75-response-v1", "timepoint-week-12-v1"),
        ("endpoint-easi75-response-v1", "timepoint-week-24-v1"),
    )
    assert views.single_timepoint_views[0].rows[0].row_id == "t-12"
    assert {row.source_row_id for row in views.longitudinal_views[0].rows} == {
        "source-t-12",
        "source-c-12",
        "source-t-24",
        "source-c-24",
    }
    assert {row.row_id for view in views.source_effect_size_views for row in view.rows} == {
        "t-12",
        "c-12",
        "t-24",
        "c-24",
    }
    assert {
        row.row_id for view in views.source_effect_size_views for row in view.effect_rows
    } == {"t-12", "t-24"}
    assert all(
        comparison.has_both_arms
        for view in views.source_effect_size_views
        for comparison in view.comparisons
    )


def test_raw_observation_compatibility_bucket_and_source_line_survive_projection() -> None:
    fact = _fact("t-12", arm_role="treatment", arm_id="arm-t", timepoint=12, value=61.0)
    views = build_efficacy_views((fact,))
    projected = views.single_timepoint_views[0].rows[0]

    assert projected.raw_endpoint == "easi75"
    assert projected.raw_definition == "EASI-75 应答者比例"
    assert projected.actual_timepoint == 12
    assert projected.compatibility_key == (
        "endpoint-easi75-response-v1",
        "timepoint-week-12-v1",
    )
    assert projected.compatibility_bucket_id == (
        "endpoint-easi75-response-v1::timepoint-week-12-v1"
    )
    assert projected.source_row_id == "source-t-12"
    assert projected.source_locator.row == "row-t-12"


def test_forest_view_never_derives_effect_size_from_arm_values() -> None:
    rows = (
        _fact("t-12", arm_role="treatment", arm_id="arm-t", timepoint=12, value=61.0),
        _fact("c-12", arm_role="control", arm_id="arm-c", timepoint=12, value=31.0),
    )

    views = build_efficacy_views(rows)

    assert views.source_effect_size_views == ()


def test_tampered_nested_observation_and_duplicate_rows_fail_closed() -> None:
    fact = _fact("t-12", arm_role="treatment", arm_id="arm-t", timepoint=12, value=61.0)
    forged = fact.model_copy(update={"original_definition": "伪造定义"})
    with pytest.raises((EfficacyViewError, ValidationError), match="原始观察|重新校验"):
        build_efficacy_views((forged,))

    with pytest.raises(EfficacyViewError, match="重复 row_id"):
        build_efficacy_views((fact, fact))


def test_only_requested_compatibility_bucket_is_selected() -> None:
    fact = _fact("t-12", arm_role="treatment", arm_id="arm-t", timepoint=12, value=61.0)
    other = _fact("t-other", arm_role="treatment", arm_id="arm-t", timepoint=24, value=65.0)
    all_views = build_efficacy_views((fact, other))
    assert {row.row_id for row in all_views.fact_rows} == {"t-12", "t-other"}
    selected = build_efficacy_views(
        (fact, other),
        compatibility_key=("endpoint-easi75-response-v1", "timepoint-week-12-v1"),
    )
    assert [row.row_id for row in selected.fact_rows] == ["t-12"]


def test_missing_values_remain_in_facts_but_do_not_create_empty_axes() -> None:
    rows = (
        _fact("t-missing", arm_role="treatment", arm_id="arm-t", timepoint=12, value=None),
        _fact("c-missing", arm_role="control", arm_id="arm-c", timepoint=12, value=None),
    )

    views = build_efficacy_views(rows)

    assert len(views.fact_rows) == 2
    assert views.single_timepoint_views == ()
    assert views.longitudinal_views == ()
    assert views.source_effect_size_views == ()
