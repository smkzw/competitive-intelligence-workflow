"""Task 6.2 B 类疗效默认顺序与用户可逆排序合同。"""

from __future__ import annotations

import pytest

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import (
    EfficacyArmRole,
    EfficacyFactRow,
    EfficacySignalState,
    EfficacySortKey,
    EfficacyViewError,
    reset_efficacy_sort,
    sort_efficacy_rows,
)

BUCKET = ("endpoint-easi75-response-v1", "timepoint-week-12-v1")
WEEK24_BUCKET = ("endpoint-easi75-response-v1", "timepoint-week-24-v1")
NPS_BUCKET = ("endpoint-nps-change-v1", "timepoint-week-12-v1")


def _fact(
    row_id: str,
    *,
    product_id: str,
    trial_id: str,
    comparison_id: str,
    arm_role: EfficacyArmRole,
    value: float | None,
    direction: EndpointDirection = EndpointDirection.HIGHER_IS_BETTER,
    compatibility_key: tuple[str, str] = BUCKET,
) -> EfficacyFactRow:
    endpoint_family_id = compatibility_key[0]
    is_nps = endpoint_family_id == "endpoint-nps-change-v1"
    return EfficacyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=f"observation-{row_id}",
        product_id=product_id,
        trial_id=trial_id,
        endpoint_family_id=endpoint_family_id,
        endpoint_family_label_zh="鼻息肉评分变化" if is_nps else "EASI-75",
        compatibility_key=compatibility_key,
        original_endpoint="nps" if is_nps else "easi75",
        original_definition="鼻息肉评分较基线变化" if is_nps else "EASI-75 应答者比例",
        endpoint_role="primary",
        direction=direction,
        unit="points" if is_nps else "%",
        analysis_form="change_from_baseline" if is_nps else "response_rate",
        actual_timepoint=24 if compatibility_key[1] == "timepoint-week-24-v1" else 12,
        actual_timepoint_unit="week",
        analysis_population="全分析集",
        arm_role=arm_role,
        arm_id=f"{comparison_id}-{arm_role.value}",
        arm_label="治疗组" if arm_role is EfficacyArmRole.TREATMENT else "安慰剂",
        value=value,
        denominator=100,
        disclosure_state=(
            FactDisclosureState.REPORTED_VALUE
            if value is not None
            else FactDisclosureState.NOT_REPORTED
        ),
        comparison_id=comparison_id,
        source_version_id="source-version-1",
        source_locator=EvidenceLocator(
            document_role="trial-results",
            table="Table 1",
            row=f"row-{row_id}",
            column="value",
        ),
    )


def test_default_order_is_stable_and_does_not_rank_by_values() -> None:
    rows = (
        _fact(
            "b-control",
            product_id="product-b",
            trial_id="NCT00000002",
            comparison_id="comparison-b",
            arm_role=EfficacyArmRole.CONTROL,
            value=5,
        ),
        _fact(
            "b-treatment",
            product_id="product-b",
            trial_id="NCT00000002",
            comparison_id="comparison-b",
            arm_role=EfficacyArmRole.TREATMENT,
            value=10,
        ),
        _fact(
            "a-control",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-a",
            arm_role=EfficacyArmRole.CONTROL,
            value=5,
        ),
        _fact(
            "a-treatment",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-a",
            arm_role=EfficacyArmRole.TREATMENT,
            value=10,
        ),
    )

    default = sort_efficacy_rows(rows, BUCKET)
    changed_values = tuple(
        _fact(
            row.row_id,
            product_id=row.product_id,
            trial_id=row.trial_id,
            comparison_id=row.comparison_id or row.row_id,
            arm_role=row.arm_role,
            value=95 if row.arm_role is EfficacyArmRole.TREATMENT else 1,
        )
        for row in rows
    )
    changed = sort_efficacy_rows(changed_values, BUCKET)

    assert default.sort_key is EfficacySortKey.DEFAULT
    assert default.is_default
    assert [row.row_id for row in default.rows] == [
        "a-treatment",
        "a-control",
        "b-treatment",
        "b-control",
    ]
    assert tuple(row.row_id for row in default.rows) == tuple(
        row.row_id for row in changed.rows
    )


def test_signal_sort_is_direction_correct_and_keeps_unknown_rows_explicit() -> None:
    rows = (
        _fact(
            "unknown-control",
            product_id="product-0",
            trial_id="NCT00000000",
            comparison_id="comparison-unknown",
            arm_role=EfficacyArmRole.CONTROL,
            value=3,
        ),
        _fact(
            "unknown-treatment",
            product_id="product-0",
            trial_id="NCT00000000",
            comparison_id="comparison-unknown",
            arm_role=EfficacyArmRole.TREATMENT,
            value=None,
        ),
        _fact(
            "zero-control",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-zero",
            arm_role=EfficacyArmRole.CONTROL,
            value=10,
        ),
        _fact(
            "zero-treatment",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-zero",
            arm_role=EfficacyArmRole.TREATMENT,
            value=10,
        ),
        _fact(
            "high-control",
            product_id="product-b",
            trial_id="NCT00000002",
            comparison_id="comparison-high",
            arm_role=EfficacyArmRole.CONTROL,
            value=10,
        ),
        _fact(
            "high-treatment",
            product_id="product-b",
            trial_id="NCT00000002",
            comparison_id="comparison-high",
            arm_role=EfficacyArmRole.TREATMENT,
            value=80,
        ),
    )

    ranked = sort_efficacy_rows(rows, BUCKET, sort_mode=EfficacySortKey.SIGNAL)

    assert ranked.is_user_sorted
    assert [row.row_id for row in ranked.rows] == [
        "high-treatment",
        "high-control",
        "zero-treatment",
        "zero-control",
        "unknown-treatment",
        "unknown-control",
    ]
    assert ranked.signal_by_row_id == (
        ("high-treatment", 70.0),
        ("high-control", 70.0),
        ("zero-treatment", 0.0),
        ("zero-control", 0.0),
    )
    assert set(ranked.unknown_row_ids) == {"unknown-treatment", "unknown-control"}
    assert all(
        state is EfficacySignalState.UNKNOWN
        for row_id, state in ranked.signal_states
        if row_id in ranked.unknown_row_ids
    )
    assert set(dict(ranked.unknown_reason_by_row_id)) == set(ranked.unknown_row_ids)


def test_signal_sort_corrects_lower_is_better_direction() -> None:
    rows = (
        _fact(
            "lower-a-control",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-lower-a",
            arm_role=EfficacyArmRole.CONTROL,
            value=5,
            direction=EndpointDirection.LOWER_IS_BETTER,
            compatibility_key=NPS_BUCKET,
        ),
        _fact(
            "lower-a-treatment",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-lower-a",
            arm_role=EfficacyArmRole.TREATMENT,
            value=2,
            direction=EndpointDirection.LOWER_IS_BETTER,
            compatibility_key=NPS_BUCKET,
        ),
        _fact(
            "lower-b-control",
            product_id="product-b",
            trial_id="NCT00000002",
            comparison_id="comparison-lower-b",
            arm_role=EfficacyArmRole.CONTROL,
            value=7,
            direction=EndpointDirection.LOWER_IS_BETTER,
            compatibility_key=NPS_BUCKET,
        ),
        _fact(
            "lower-b-treatment",
            product_id="product-b",
            trial_id="NCT00000002",
            comparison_id="comparison-lower-b",
            arm_role=EfficacyArmRole.TREATMENT,
            value=8,
            direction=EndpointDirection.LOWER_IS_BETTER,
            compatibility_key=NPS_BUCKET,
        ),
    )

    ranked = sort_efficacy_rows(rows, NPS_BUCKET, sort_mode="signal")

    assert [row.row_id for row in ranked.rows] == [
        "lower-a-treatment",
        "lower-a-control",
        "lower-b-treatment",
        "lower-b-control",
    ]
    assert dict(ranked.signal_by_row_id)["lower-a-treatment"] == 3.0
    assert dict(ranked.signal_by_row_id)["lower-b-treatment"] == -1.0


def test_sort_rejects_cross_bucket_input_and_reset_reproduces_default() -> None:
    rows = (
        _fact(
            "treatment",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-a",
            arm_role=EfficacyArmRole.TREATMENT,
            value=60,
        ),
        _fact(
            "control",
            product_id="product-a",
            trial_id="NCT00000001",
            comparison_id="comparison-a",
            arm_role=EfficacyArmRole.CONTROL,
            value=20,
        ),
    )
    other_bucket = _fact(
        "other",
        product_id="product-b",
        trial_id="NCT00000002",
        comparison_id="comparison-b",
        arm_role=EfficacyArmRole.TREATMENT,
        value=50,
        compatibility_key=WEEK24_BUCKET,
    )

    with pytest.raises(EfficacyViewError, match="跨桶"):
        sort_efficacy_rows((*rows, other_bucket), BUCKET, sort_mode="signal")

    default = sort_efficacy_rows(rows, BUCKET)
    ranked = sort_efficacy_rows(rows, BUCKET, sort_key="signal")
    assert ranked.reset().rows == default.rows
    assert reset_efficacy_sort(ranked).rows == default.rows
    assert reset_efficacy_sort(rows, BUCKET).rows == default.rows
