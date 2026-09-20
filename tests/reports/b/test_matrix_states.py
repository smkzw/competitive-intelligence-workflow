"""Task 6.4 B 类比较矩阵状态和不可绘制组合合同。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import EfficacyArmRole, EfficacyFactRow
from ci_workflow.reports.b.pages import (
    MatrixComparisonRow,
    MatrixComparisonStatus,
    MatrixSelectionState,
    apply_matrix_selection,
    build_bubble_matrix,
    build_matrix_comparison_rows,
    build_matrix_view_state,
    reset_matrix_selection,
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
    value: float | None = 60.0,
    direction: EndpointDirection = EndpointDirection.HIGHER_IS_BETTER,
    disclosure_state: FactDisclosureState | None = None,
) -> EfficacyFactRow:
    is_lower = direction is EndpointDirection.LOWER_IS_BETTER
    endpoint_family_id = "endpoint-nps-change-v1" if is_lower else "endpoint-easi75-response-v1"
    state = disclosure_state or (
        FactDisclosureState.REPORTED_VALUE
        if value is not None
        else FactDisclosureState.NOT_REPORTED
    )
    return EfficacyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=f"observation-{row_id}",
        product_id="product-a",
        trial_id="NCT00000001",
        endpoint_family_id=endpoint_family_id,
        endpoint_family_label_zh="鼻息肉评分变化" if is_lower else "EASI-75 应答率",
        compatibility_key=(endpoint_family_id, "timepoint-week-12-v1"),
        original_endpoint="nps" if is_lower else "easi75",
        original_definition="鼻息肉评分较基线变化" if is_lower else "EASI-75 应答者比例",
        endpoint_role="primary",
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
        disclosure_state=state,
        source_version_id="source-version-1",
        source_locator=_LOCATOR,
    )


def _safety(
    row_id: str,
    *,
    arm_role: SafetyArmRole,
    arm_id: str,
    value: float | None = 20.0,
    state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    time_window_zh: str = "治疗期间",
    applicability_predicate_id: str | None = None,
    family: SafetyFamily = SafetyFamily.TEAE,
    term_id: str = "teae-any",
    source_term: str = "任何治疗期间不良事件",
    event_definition_zh: str = "治疗期间出现的不良事件",
) -> SafetyFactRow:
    return SafetyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=f"observation-{row_id}",
        product_id="product-a",
        trial_id="NCT00000001",
        family=family,
        term_id=term_id,
        source_term=source_term,
        event_definition_zh=event_definition_zh,
        time_window_zh=time_window_zh,
        analysis_population_zh="安全性分析集",
        arm_role=arm_role,
        arm_id=arm_id,
        arm_label="治疗组" if arm_role is SafetyArmRole.TREATMENT else "安慰剂",
        value=value,
        raw_value=f"{value:g}%" if value is not None else "该维度不适用",
        unit="%",
        denominator=100 if value is not None else None,
        disclosure_state=state,
        applicability_predicate_id=applicability_predicate_id,
        source_version_id="source-version-1",
        source_locator=_LOCATOR,
    )


def _facts() -> tuple[tuple[EfficacyFactRow, ...], tuple[SafetyFactRow, ...]]:
    return (
        _efficacy(
            "eff-treatment",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-treatment",
            value=60.0,
        ),
        _efficacy(
            "eff-control",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-control",
            value=30.0,
        ),
    ), (
        _safety(
            "safe-treatment",
            arm_role=SafetyArmRole.TREATMENT,
            arm_id="arm-treatment",
            value=20.0,
        ),
        _safety(
            "safe-control",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="arm-control",
            value=10.0,
        ),
    )


_SAMPLE_SIZES = {
    ("product-a", "NCT00000001", "arm-treatment"): 100,
}


def _assert_unplottable(view: Any, status: MatrixComparisonStatus) -> None:
    row = view.comparison_rows[0]
    assert row.status is status
    assert row.status_label_zh in {"不兼容", "未报告", "不适用", "待核实"}
    assert view.points == ()
    assert len(view.unplottable_rows) == 1
    assert not hasattr(view.unplottable_rows[0], "x_value")
    assert not hasattr(view.unplottable_rows[0], "y_value")


def test_comparable_row_is_the_only_state_that_generates_a_bubble() -> None:
    efficacy, safety = _facts()

    view = build_bubble_matrix(
        efficacy, safety, treatment_sample_sizes=_SAMPLE_SIZES
    )

    assert view.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE
    assert view.comparison_rows[0].status_label_zh == "可比"
    assert len(view.points) == 1
    assert view.unplottable_rows == ()


def test_incompatible_efficacy_context_is_retained_without_a_zero_coordinate() -> None:
    efficacy, safety = _facts()
    incompatible_control = _efficacy(
        "eff-control-incompatible",
        arm_role=EfficacyArmRole.CONTROL,
        arm_id="arm-control",
        value=30.0,
        direction=EndpointDirection.LOWER_IS_BETTER,
    )
    row = MatrixComparisonRow(
        comparison_row_id="incompatible-row",
        product_id="product-a",
        trial_id="NCT00000001",
        efficacy_treatment=efficacy[0],
        efficacy_control=incompatible_control,
        safety_treatment=safety[0],
        safety_control=safety[1],
        treatment_sample_size=100,
    )

    view = build_bubble_matrix((row,))

    _assert_unplottable(view, MatrixComparisonStatus.INCOMPATIBLE)
    assert view.comparison_rows[0].efficacy_treatment is not None
    assert view.comparison_rows[0].efficacy_treatment.row_id == efficacy[0].row_id
    assert view.comparison_rows[0].efficacy_control is not None
    assert view.comparison_rows[0].efficacy_control.row_id == incompatible_control.row_id
    assert view.comparison_rows[0].x_value is None
    assert "兼容" in view.unplottable_rows[0].reason_zh


def test_unreported_efficacy_is_an_explicit_state_not_a_zero_coordinate() -> None:
    efficacy, safety = _facts()
    missing_treatment = _efficacy(
        "eff-treatment-missing",
        arm_role=EfficacyArmRole.TREATMENT,
        arm_id="arm-treatment",
        value=None,
        disclosure_state=FactDisclosureState.NOT_REPORTED,
    )

    view = build_bubble_matrix((missing_treatment, efficacy[1]), safety)

    _assert_unplottable(view, MatrixComparisonStatus.NOT_REPORTED)
    assert view.comparison_rows[0].efficacy_treatment is not None
    assert view.comparison_rows[0].efficacy_treatment.value is None
    assert view.comparison_rows[0].x_value is None
    assert "未报告" in view.unplottable_rows[0].reason_zh


def test_not_applicable_safety_is_preserved_as_a_matrix_state() -> None:
    efficacy, safety = _facts()
    not_applicable_treatment = _safety(
        "safe-treatment-na",
        arm_role=SafetyArmRole.TREATMENT,
        arm_id="arm-treatment",
        value=None,
        state=FactDisclosureState.NOT_APPLICABLE,
        applicability_predicate_id="teae-applicability-v1",
    )

    view = build_bubble_matrix(efficacy, (not_applicable_treatment, safety[1]))

    _assert_unplottable(view, MatrixComparisonStatus.NOT_APPLICABLE)
    assert view.comparison_rows[0].safety_treatment is not None
    assert view.comparison_rows[0].safety_treatment.value is None
    assert "不适用" in view.unplottable_rows[0].reason_zh


def test_unknown_sample_size_is_pending_verification_not_zero() -> None:
    efficacy, safety = _facts()

    view = build_bubble_matrix(
        efficacy,
        safety,
        treatment_sample_sizes={("product-a", "NCT00000001", "arm-treatment"): None},
    )

    _assert_unplottable(view, MatrixComparisonStatus.PENDING_VERIFICATION)
    assert view.comparison_rows[0].treatment_sample_size is None
    assert "未知" in view.unplottable_rows[0].reason_zh


def test_safety_event_denominator_is_not_silently_used_as_treatment_group_n() -> None:
    efficacy, safety = _facts()

    view = build_bubble_matrix(efficacy, safety)

    _assert_unplottable(view, MatrixComparisonStatus.PENDING_VERIFICATION)
    assert view.comparison_rows[0].treatment_sample_size is None
    assert safety[0].denominator == 100


@pytest.mark.parametrize(
    "broad_key",
    ("product-a", "NCT00000001", "arm-treatment", ("product-a", "NCT00000001")),
)
def test_broad_sample_size_keys_cannot_lend_n_to_a_trial_arm(broad_key: object) -> None:
    efficacy, safety = _facts()

    view = build_bubble_matrix(
        efficacy,
        safety,
        treatment_sample_sizes={broad_key: 999},
    )

    _assert_unplottable(view, MatrixComparisonStatus.PENDING_VERIFICATION)
    assert view.comparison_rows[0].treatment_sample_size is None


def test_scoped_nested_sample_size_must_name_the_treatment_arm() -> None:
    efficacy, safety = _facts()

    view = build_bubble_matrix(
        efficacy,
        safety,
        treatment_sample_sizes={
            ("product-a", "NCT00000001"): {"arm-treatment": 123}
        },
    )

    assert view.comparison_rows[0].treatment_sample_size == 123
    assert view.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE


def test_multiple_safety_contexts_require_selection_instead_of_claiming_unreported() -> None:
    efficacy, safety = _facts()
    later_treatment = _safety(
        "safe-treatment-later",
        arm_role=SafetyArmRole.TREATMENT,
        arm_id="arm-treatment",
        value=35.0,
        time_window_zh="整个研究期",
    )
    later_control = _safety(
        "safe-control-later",
        arm_role=SafetyArmRole.CONTROL,
        arm_id="arm-control",
        value=25.0,
        time_window_zh="整个研究期",
    )

    state = build_matrix_view_state(
        efficacy,
        (*safety, later_treatment, later_control),
        treatment_sample_sizes={
            ("product-a", "NCT00000001", "arm-treatment"): 100
        },
    )

    assert state.selection.safety_time_window_zh is None
    assert state.comparison_rows[0].status is MatrixComparisonStatus.PENDING_VERIFICATION
    assert "存在多个安全性统计口径" in state.complete_table[0].reason_zh
    assert state.chart.points == ()


def test_existing_safety_dimension_with_unmatched_filter_is_not_called_unreported() -> None:
    efficacy, safety = _facts()

    rows = build_matrix_comparison_rows(
        efficacy,
        safety,
        safety_time_window_zh="整个研究期",
        treatment_sample_sizes={
            ("product-a", "NCT00000001", "arm-treatment"): 100
        },
    )

    assert rows[0].status is MatrixComparisonStatus.PENDING_VERIFICATION
    assert "已有该安全性维度数据" in (rows[0].status_reason_zh or "")


def test_effect_measure_buckets_keep_unique_row_ids_and_never_subtract() -> None:
    efficacy, safety = _facts()
    treatment = efficacy[0].model_copy(update={"effect_measure": "risk_difference"})
    control = efficacy[1].model_copy(update={"effect_measure": "odds_ratio"})

    view = build_bubble_matrix(
        (treatment, control),
        safety,
        treatment_sample_sizes={
            ("product-a", "NCT00000001", "arm-treatment"): 100
        },
    )

    assert len(view.comparison_rows) == 2
    assert len({row.comparison_row_id for row in view.comparison_rows}) == 2
    assert all(row.efficacy_signal is None for row in view.comparison_rows)
    assert view.points == ()


def test_switching_safety_family_drops_previous_family_dependent_filters() -> None:
    efficacy, safety = _facts()
    sae_treatment = _safety(
        "safe-treatment-sae",
        arm_role=SafetyArmRole.TREATMENT,
        arm_id="arm-treatment",
        value=3.0,
        time_window_zh="研究期间",
        family=SafetyFamily.SAE,
        term_id="sae-any",
        source_term="任何严重不良事件",
        event_definition_zh="研究期间出现的严重不良事件",
    )
    sae_control = _safety(
        "safe-control-sae",
        arm_role=SafetyArmRole.CONTROL,
        arm_id="arm-control",
        value=2.0,
        time_window_zh="研究期间",
        family=SafetyFamily.SAE,
        term_id="sae-any",
        source_term="任何严重不良事件",
        event_definition_zh="研究期间出现的严重不良事件",
    )
    initial = build_matrix_view_state(
        efficacy,
        (*safety, sae_treatment, sae_control),
        treatment_sample_sizes={
            ("product-a", "NCT00000001", "arm-treatment"): 100
        },
    )

    switched = apply_matrix_selection(initial, {"safety_family": SafetyFamily.SAE})

    assert switched.selection.safety_family is SafetyFamily.SAE
    assert switched.selection.safety_term_id is None
    assert switched.selection.safety_time_window_zh is None
    assert switched.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE
    assert switched.chart.points[0].y_value == pytest.approx(3.0)


def test_all_five_matrix_states_have_distinct_chinese_labels() -> None:
    assert {
        state.value: state_label
        for state, state_label in zip(
            MatrixComparisonStatus,
            ("可比", "不兼容", "未报告", "不适用", "待核实"),
            strict=True,
        )
    } == {
        "comparable": "可比",
        "incompatible": "不兼容",
        "not_reported": "未报告",
        "not_applicable": "不适用",
        "pending_verification": "待核实",
    }


def test_conflicting_matrix_status_aliases_fail_closed() -> None:
    efficacy, safety = _facts()
    row = build_bubble_matrix(efficacy, safety).comparison_rows[0]
    payload = row.model_dump(mode="python")
    payload["comparison_status"] = MatrixComparisonStatus.INCOMPATIBLE

    with pytest.raises(ValidationError, match="状态"):
        MatrixComparisonRow.model_validate(payload)


def _two_product_facts() -> tuple[tuple[EfficacyFactRow, ...], tuple[SafetyFactRow, ...]]:
    efficacy, safety = _facts()
    second_efficacy = tuple(
        row.model_copy(
            update={
                "row_id": f"{row.row_id}-product-b",
                "product_id": "product-b",
            }
        )
        for row in efficacy
    )
    second_safety = tuple(
        row.model_copy(
            update={
                "row_id": f"{row.row_id}-product-b",
                "product_id": "product-b",
            }
        )
        for row in safety
    )
    return efficacy + second_efficacy, safety + second_safety


def test_matrix_selection_defaults_to_snapshot_and_reset_is_reversible() -> None:
    efficacy, safety = _two_product_facts()

    initial = build_matrix_view_state(
        efficacy,
        safety,
        locked_snapshot_id="snapshot-6-4",
    )
    selected = initial.selection.model_copy(update={"product_ids": ("product-b",)})
    filtered = apply_matrix_selection(initial, selected)
    reset = reset_matrix_selection(filtered)

    assert initial.selection.snapshot_id == "snapshot-6-4"
    assert initial.selection.product_ids == ("product-a", "product-b")
    assert len(initial.comparison_rows) == 2
    assert len(filtered.comparison_rows) == 1
    assert filtered.comparison_rows[0].product_id == "product-b"
    assert filtered.efficacy_facts == initial.efficacy_facts
    assert reset.selection == initial.selection
    assert reset.url == initial.url
    assert reset.comparison_row_ids == initial.comparison_row_ids


def test_matrix_selection_url_round_trip_is_stable_for_all_dimensions() -> None:
    efficacy, safety = _facts()
    initial = build_matrix_view_state(efficacy, safety, locked_snapshot_id="snapshot-6-4")
    selected = initial.selection.model_copy(
        update={
            "efficacy_effect_form": "response_rate",
            "efficacy_analysis_form": "response_rate",
            "safety_family": SafetyFamily.TEAE,
            "safety_term_id": "teae-any",
            "safety_event_definition_zh": "治疗期间出现的不良事件",
            "safety_time_window_zh": "治疗期间",
            "safety_analysis_population_zh": "安全性分析集",
            "safety_denominator_semantics_zh": None,
            "bubble_size": "样本量",
            "product_ids": ("product-a",),
            "trial_ids": ("NCT00000001",),
            "target_ids": ("target-a",),
        }
    )
    normalized = MatrixSelectionState.model_validate(
        selected.model_dump(mode="python", warnings=False)
    )
    restored = MatrixSelectionState.from_url(normalized.to_url())

    assert restored == normalized
    assert list(normalized.to_url_params()) == sorted(normalized.to_url_params())
    assert "bubble_size=treatment_sample_size" in normalized.to_url()
    assert "%E6%B2%BB%E7%96%97%E6%9C%9F%E9%97%B4" in normalized.to_url()


def test_matrix_surfaces_share_rows_facts_and_never_rank() -> None:
    efficacy, safety = _facts()

    state = build_matrix_view_state(efficacy, safety)

    assert state.comparison_row_ids == tuple(
        cell.comparison_row_id for cell in state.complete_table
    )
    assert state.comparison_row_ids == tuple(
        prompt.comparison_row_id for prompt in state.prompts
    )
    assert set(state.comparison_row_ids) == {
        link.comparison_row_id for link in state.evidence_links
    }
    assert set(state.fact_row_ids) == {link.fact_row_id for link in state.evidence_links}
    assert set(state.fact_row_ids) == {
        fact_id for cell in state.complete_table for fact_id in cell.fact_row_ids
    }
    assert tuple(row.comparison_row_id for row in state.chart.comparison_rows) == (
        state.comparison_row_ids
    )
    assert state.is_ranked is False
    assert state.chart.is_ranked is False
    assert all(cell.is_ranked is False for cell in state.complete_table)
    assert all(prompt.is_ranked is False for prompt in state.prompts)


def test_partial_selection_inherits_snapshot_dimensions() -> None:
    efficacy, safety = _two_product_facts()

    initial = build_matrix_view_state(efficacy, safety, locked_snapshot_id="snapshot-6-4")
    filtered = initial.with_selection({"products": ["product-b"]})

    assert filtered.selection.endpoint_family_id == initial.selection.endpoint_family_id
    assert filtered.selection.safety_event_id == initial.selection.safety_event_id
    assert filtered.selection.snapshot_id == "snapshot-6-4"
    assert filtered.comparison_rows[0].product_id == "product-b"


def test_complete_table_keeps_the_original_comparison_row() -> None:
    efficacy, safety = _facts()

    state = build_matrix_view_state(efficacy, safety)
    cell = state.complete_table[0]

    assert cell.comparison_row == state.comparison_rows[0]
    assert cell.raw_treatment_efficacy_value == 60.0
    assert cell.raw_control_efficacy_value == 30.0
    assert cell.raw_safety_rate == 20.0
