"""Task 6.3 B 类安全性可比语境与多维热图合同。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.b.safety import (
    DEFAULT_SAFETY_DIMENSIONS,
    SafetyArmRole,
    SafetyComparableContext,
    SafetyEventSelection,
    SafetyFactRow,
    SafetyFamily,
    SafetyViewError,
    build_safety_views,
    default_safety_dimensions,
    expand_safety_events,
    search_safety_events,
    select_default_safety_events,
    validate_safety_view_set,
)

_LOCATOR = EvidenceLocator(
    document_role="trial-results",
    table="Table 14.3.1",
    row="headache",
    column="value",
)


def _fact(
    row_id: str,
    *,
    trial_id: str = "NCT00000001",
    product_id: str = "product-a",
    term_id: str = "headache",
    source_term: str = "头痛",
    family: SafetyFamily = SafetyFamily.COMMON_AE,
    arm_role: SafetyArmRole = SafetyArmRole.TREATMENT,
    arm_id: str = "arm-treatment",
    arm_label: str = "治疗组",
    value: float | None = 12.0,
    state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    raw_value: str | None = "12%",
    time_window_zh: str = "治疗期间",
    analysis_population_zh: str = "安全性分析集",
    unit: str = "%",
    denominator: int | None = 100,
    denominator_semantics_zh: str | None = None,
) -> SafetyFactRow:
    return SafetyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=f"observation-{row_id}",
        product_id=product_id,
        trial_id=trial_id,
        family=family,
        term_id=term_id,
        source_term=source_term,
        event_definition_zh="治疗期间出现的不良事件",
        time_window_zh=time_window_zh,
        analysis_population_zh=analysis_population_zh,
        arm_role=arm_role,
        arm_id=arm_id,
        arm_label=arm_label,
        value=value,
        raw_value=raw_value,
        unit=unit,
        denominator=denominator,
        denominator_semantics_zh=denominator_semantics_zh,
        disclosure_state=state,
        source_version_id="source-version-1",
        source_locator=_LOCATOR,
    )


def test_context_key_only_compares_same_event_and_measurement_semantics() -> None:
    rows = (
        _fact("treatment"),
        _fact(
            "control",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="arm-control",
            arm_label="安慰剂",
            value=8.0,
            raw_value="8%",
        ),
        _fact("follow-up", time_window_zh="随访期"),
        _fact("count", unit="例", value=12, raw_value="12例"),
        _fact("other-denominator", denominator_semantics_zh="暴露患者年"),
    )

    views = build_safety_views(rows)

    assert len(views.heatmap_views) == 4
    treatment_control = next(
        view
        for view in views.heatmap_views
        if {cell.fact_version_id for cell in view.cells} == {"treatment", "control"}
    )
    assert treatment_control.context.event_identity == "头痛"
    assert treatment_control.context.time_window_zh == "治疗期间"
    assert treatment_control.context.unit == "%"
    assert treatment_control.context.denominator_semantics == "受试者分母"
    assert treatment_control.context.identity_key == treatment_control.context.key


def test_materially_different_event_definitions_never_share_a_colour_scale() -> None:
    rows = (
        _fact("standard-definition"),
        _fact("narrow-definition").model_copy(
            update={"event_definition_zh": "仅计入研究者判断与治疗相关的事件"}
        ),
    )

    views = build_safety_views(rows)

    assert len(views.heatmap_views) == 2
    assert {view.context.event_definition_zh for view in views.heatmap_views} == {
        "治疗期间出现的不良事件",
        "仅计入研究者判断与治疗相关的事件",
    }


def test_heatmap_keeps_treatment_control_parallel_and_separates_trials() -> None:
    rows = (
        _fact("treatment-1", value=24.0, raw_value="24%"),
        _fact(
            "control-1",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="arm-control",
            arm_label="安慰剂",
            value=10.0,
            raw_value="10%",
        ),
        _fact("treatment-2", trial_id="NCT00000002", value=40.0, raw_value="40%"),
        _fact(
            "control-2",
            trial_id="NCT00000002",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="arm-control",
            arm_label="安慰剂",
            value=20.0,
            raw_value="20%",
        ),
    )

    views = build_safety_views(rows)

    assert len(views.heatmap_views) == 1
    view = views.heatmap_views[0]
    assert view.trial_ids == ("NCT00000001", "NCT00000002")
    assert {(column.product_id, column.trial_id) for column in view.trial_columns} == {
        ("product-a", "NCT00000001"),
        ("product-a", "NCT00000002"),
    }
    assert all(column.has_both_arms for column in view.trial_columns)
    assert [cell.arm_role for cell in view.trial_columns[0].rows] == [
        SafetyArmRole.TREATMENT,
        SafetyArmRole.CONTROL,
    ]
    assert {cell.fact_version_id for cell in view.cells} == {
        "treatment-1",
        "control-1",
        "treatment-2",
        "control-2",
    }
    assert all("排名" not in cell.display_value for cell in view.cells)


def test_values_are_printed_and_non_numeric_states_never_enter_colour_scale() -> None:
    rows = (
        _fact("reported", value=20.0, raw_value="20%"),
        _fact(
            "zero",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="arm-control",
            arm_label="安慰剂",
            value=0.0,
            raw_value="0%",
            state=FactDisclosureState.REPORTED_ZERO,
        ),
        _fact(
            "not-reported",
            product_id="product-b",
            value=None,
            raw_value="原文未报告",
            state=FactDisclosureState.NOT_REPORTED,
        ),
        _fact(
            "threshold",
            product_id="product-c",
            value=None,
            raw_value="<5%",
            state=FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        ),
    )

    views = build_safety_views(rows)
    cells = {cell.fact_version_id: cell for cell in views.all_cells}

    assert cells["reported"].display_value_zh == "20%"
    assert cells["zero"].display_value_zh == "0%"
    assert cells["reported"].relative_intensity == 1.0
    assert cells["zero"].relative_intensity == 0.0
    assert cells["not-reported"].display_value_zh == "原文未报告"
    assert cells["threshold"].display_value_zh == "<5%"
    assert not cells["not-reported"].is_colorable
    assert not cells["threshold"].is_colorable
    assert cells["not-reported"].relative_intensity is None
    assert cells["threshold"].relative_intensity is None


def test_participant_counts_use_rates_for_colour_but_keep_source_values() -> None:
    rows = (
        _fact("count-a", unit="例", value=10, raw_value="10例", denominator=100),
        _fact(
            "count-b",
            product_id="product-b",
            unit="例",
            value=20,
            raw_value="20例",
            denominator=100,
        ),
    )

    view = build_safety_views(rows).heatmap_views[0]
    cells = {cell.fact_version_id: cell for cell in view.cells}

    assert cells["count-a"].numeric_value == 10
    assert cells["count-a"].display_value_zh == "10例"
    assert cells["count-a"].comparison_rate_percent == 10.0
    assert cells["count-b"].comparison_rate_percent == 20.0
    assert cells["count-a"].relative_intensity == 0.5
    assert cells["count-b"].relative_intensity == 1.0


def test_tampered_cell_or_missing_context_fails_closed_without_losing_rows() -> None:
    fact = _fact("row-1")
    forged = fact.model_copy(
        update={"value": None, "disclosure_state": FactDisclosureState.REPORTED_VALUE}
    )
    with pytest.raises(SafetyViewError, match="重新校验"):
        build_safety_views((forged,))

    with pytest.raises(SafetyViewError, match="可比语境"):
        build_safety_views((_fact("missing", time_window_zh=None),))  # type: ignore[arg-type]

    context = SafetyComparableContext(
        event_identity="头痛",
        event_family=SafetyFamily.COMMON_AE,
        time_window_zh="治疗期间",
        analysis_population_zh="安全性分析集",
        denominator_semantics_zh="受试者分母",
        unit="%",
    )
    with pytest.raises(SafetyViewError, match="筛选参数互相冲突"):
        build_safety_views((fact,), context=context, context_key=("other", "x", "y", "%", "z"))

    valid = build_safety_views((fact,))
    assert validate_safety_view_set(valid).all_cells[0].fact_version_id == "row-1"


def test_missing_trial_or_product_filter_returns_an_empty_closed_view() -> None:
    view_set = build_safety_views((_fact("row-1"),), trial_id="NCT99999999")

    assert view_set.fact_rows == ()
    assert view_set.heatmap_views == ()


def test_manual_heatmap_context_cannot_cross_event_identity() -> None:
    fact = _fact("row-1")
    with pytest.raises(ValidationError, match="可比语境"):
        # The mismatched context is rejected by the cell contract before any
        # view can be assembled.
        from ci_workflow.reports.b.safety import SafetyHeatmapCell

        SafetyHeatmapCell(
            fact_row=fact,
            context=SafetyComparableContext(
                event_identity="皮疹",
                event_family=SafetyFamily.COMMON_AE,
                time_window_zh="治疗期间",
                analysis_population_zh="安全性分析集",
                denominator_semantics_zh="受试者分母",
                unit="%",
            ),
        )


def test_default_dimensions_keep_fixed_order_and_add_available_optional_families() -> None:
    rows = (
        _fact("teae", family=SafetyFamily.TEAE),
        _fact("death", family=SafetyFamily.DEATH),
        _fact("grade", family=SafetyFamily.GRADE_3_OR_HIGHER),
    )

    expected = (
        *DEFAULT_SAFETY_DIMENSIONS,
        SafetyFamily.DEATH,
        SafetyFamily.GRADE_3_OR_HIGHER,
    )
    assert default_safety_dimensions(rows) == expected
    view_set = build_safety_views(rows)
    assert view_set.default_dimensions == expected
    assert view_set.is_ranked is False


def test_common_ae_default_selection_is_deterministic_and_keeps_complete_rows() -> None:
    rows: list[SafetyFactRow] = []
    for index in range(16):
        term_id = f"ae-{index:02d}"
        rows.extend(
            (
                _fact(
                    f"treatment-{index:02d}",
                    term_id=term_id,
                    source_term=f"事件{index:02d}",
                    value=50 - index,
                    raw_value=f"{50 - index}%",
                ),
                _fact(
                    f"control-{index:02d}",
                    term_id=term_id,
                    source_term=f"事件{index:02d}",
                    arm_role=SafetyArmRole.CONTROL,
                    arm_id=f"arm-control-{index:02d}",
                    arm_label="安慰剂",
                    value=10 + index,
                    raw_value=f"{10 + index}%",
                ),
            )
        )

    selected = select_default_safety_events(rows)
    view_set = build_safety_views(rows)
    assert isinstance(selected, SafetyEventSelection)
    assert len(selected.selected_event_keys) == 12
    assert len(selected.selected_rows) == 24
    assert len(selected.complete_rows) == 32
    assert len(view_set.default_event_keys) == 12
    assert len(view_set.default_common_ae_rows) == 24
    assert len(view_set.complete_event_rows) == 32
    assert set(view_set.complete_event_rows) == set(rows)
    assert selected.is_ranked is False
    assert view_set.is_ranked is False

    changed_values = tuple(
        row.model_copy(
            update={
                "value": 99 if row.arm_role is SafetyArmRole.TREATMENT else 1,
                "raw_value": "99%" if row.arm_role is SafetyArmRole.TREATMENT else "1%",
            }
        )
        for row in rows
    )
    changed = select_default_safety_events(changed_values)
    assert changed.selected_event_keys == selected.selected_event_keys


def test_complete_event_search_and_expand_preserve_non_default_rows() -> None:
    rows = (
        _fact(
            "rash-treatment",
            term_id="rash",
            source_term="皮疹",
            value=18,
            raw_value="18%",
        ),
        _fact(
            "rash-control",
            term_id="rash",
            source_term="皮疹",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="arm-control",
            arm_label="安慰剂",
            value=8,
            raw_value="8%",
        ),
        _fact(
            "rare-unreported",
            term_id="rare-event",
            source_term="罕见事件",
            value=None,
            raw_value="原文未报告",
            state=FactDisclosureState.NOT_REPORTED,
        ),
    )
    view_set = build_safety_views(rows)

    searched = search_safety_events(view_set, "皮疹")
    assert [row.row_id for row in searched] == ["rash-treatment", "rash-control"]
    assert [row.row_id for row in view_set.search_events("rare-event")] == ["rare-unreported"]
    expanded = expand_safety_events(view_set)
    assert [row.row_id for row in expanded] == [
        "rash-treatment",
        "rash-control",
        "rare-unreported",
    ]
    assert [row.row_id for row in view_set.expand_events()] == [
        "rash-treatment",
        "rash-control",
        "rare-unreported",
    ]
    assert {row.row_id for row in view_set.default_rows} == {
        "rash-treatment",
        "rash-control",
    }
    assert {row.row_id for row in view_set.complete_event_rows} == {
        "rash-treatment",
        "rash-control",
        "rare-unreported",
    }


def test_common_ae_selection_uses_union_of_explicit_criteria() -> None:
    rows = (
        _fact(
            "frequency-treatment-1",
            trial_id="NCT00000001",
            term_id="frequency-event",
            source_term="高频事件",
            value=1,
            raw_value="1%",
        ),
        _fact(
            "frequency-control-1",
            trial_id="NCT00000001",
            term_id="frequency-event",
            source_term="高频事件",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="control-frequency-1",
            arm_label="安慰剂",
            value=1,
            raw_value="1%",
        ),
        _fact(
            "frequency-treatment-2",
            trial_id="NCT00000002",
            term_id="frequency-event",
            source_term="高频事件",
            value=1,
            raw_value="1%",
        ),
        _fact(
            "frequency-control-2",
            trial_id="NCT00000002",
            term_id="frequency-event",
            source_term="高频事件",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="control-frequency-2",
            arm_label="安慰剂",
            value=1,
            raw_value="1%",
        ),
        _fact(
            "difference-treatment",
            term_id="difference-event",
            source_term="差异事件",
            value=4,
            raw_value="4%",
        ),
        _fact(
            "difference-control",
            term_id="difference-event",
            source_term="差异事件",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="control-difference",
            arm_label="安慰剂",
            value=10,
            raw_value="10%",
        ),
        _fact(
            "important-treatment",
            term_id="important-event",
            source_term="重要事件",
            value=1,
            raw_value="1%",
        ),
        _fact(
            "important-control",
            term_id="important-event",
            source_term="重要事件",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="control-important",
            arm_label="安慰剂",
            value=1,
            raw_value="1%",
        ),
        _fact(
            "not-candidate-treatment",
            term_id="not-candidate",
            source_term="未入选事件",
            value=1,
            raw_value="1%",
        ),
        _fact(
            "not-candidate-control",
            term_id="not-candidate",
            source_term="未入选事件",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="control-not-candidate",
            arm_label="安慰剂",
            value=1,
            raw_value="1%",
        ),
    )

    selection = select_default_safety_events(
        rows,
        clinically_important_terms={"important-event"},
        high_frequency_terms={"frequency-event"},
    )
    built = build_safety_views(
        rows,
        clinically_important_terms={"important-event"},
        high_frequency_terms={"frequency-event"},
    )

    assert "common_ae:important-event" in built.default_event_keys

    assert set(selection.common_ae_event_keys) == {
        "common_ae:frequency-event",
        "common_ae:difference-event",
        "common_ae:important-event",
    }
    assert "common_ae:not-candidate" not in selection.common_ae_event_keys
    reasons = dict(selection.eligibility_reasons_by_event)
    assert "来源高频" in reasons["common_ae:frequency-event"]
    assert "治疗—对照绝对差≥5个百分点" in reasons["common_ae:difference-event"]
    assert "项目适配器标记临床重要" in reasons["common_ae:important-event"]


def test_repeated_low_rate_disclosure_is_not_relabelled_as_source_high_frequency() -> None:
    rows = tuple(
        _fact(
            f"low-rate-{trial_id}",
            trial_id=trial_id,
            term_id="low-rate-event",
            source_term="低发生率事件",
            value=1,
            raw_value="1%",
        )
        for trial_id in ("NCT00000001", "NCT00000002")
    )

    selection = select_default_safety_events(rows)

    assert selection.common_ae_event_keys == ()

    explicitly_frequent = select_default_safety_events(
        rows,
        source_frequency_by_event={"low-rate-event": 2},
    )
    assert explicitly_frequent.common_ae_event_keys == ("common_ae:low-rate-event",)


def test_common_ae_difference_never_pairs_treatment_and_control_across_trials() -> None:
    rows = (
        _fact(
            "treatment-trial-1",
            trial_id="NCT00000001",
            term_id="cross-trial-event",
            source_term="跨试验事件",
            value=4,
            raw_value="4%",
        ),
        _fact(
            "control-trial-2",
            trial_id="NCT00000002",
            term_id="cross-trial-event",
            source_term="跨试验事件",
            arm_role=SafetyArmRole.CONTROL,
            arm_id="control-cross-trial",
            arm_label="安慰剂",
            value=10,
            raw_value="10%",
        ),
    )

    selection = select_default_safety_events(rows, source_frequency_threshold=99)

    assert selection.common_ae_event_keys == ()
