"""Task 6.8 B 类试验完成情况视图的科学资格与同源投影 RED 测试。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.b.disposition import (
    DispositionDenominatorRole,
    DispositionField,
    DispositionFieldFamily,
    DispositionMeasureObject,
    DispositionScopeLevel,
    DispositionStatisticForm,
    TrialDispositionObservation,
)
from ci_workflow.reports.b.disposition_views import (
    DispositionChartType,
    DispositionViewError,
    build_disposition_view_state,
)

_LOCATOR = EvidenceLocator(
    document_role="primary-trial-report",
    field_path="Table 14.1.1 participant disposition",
    table="受试者处置表",
    row="Treatment group",
    column="n (%)",
    page=19,
)


_MISSING_STATES = {
    FactDisclosureState.NOT_REPORTED,
    FactDisclosureState.BELOW_REPORTING_THRESHOLD,
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
    FactDisclosureState.NOT_APPLICABLE,
    FactDisclosureState.CONFLICTING,
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
}


def _observation(
    token: str,
    *,
    product_id: str = "product-a",
    trial_id: str = "trial-1",
    period_id: str = "period-1",
    cohort_id: str | None = "cohort-1",
    scope_level: DispositionScopeLevel = DispositionScopeLevel.COHORT,
    group_id: str | None = None,
    analysis_population: str = "随机化人群",
    field_family: DispositionFieldFamily = DispositionFieldFamily.PARTICIPANT_FLOW,
    field: DispositionField = DispositionField.RECEIVED_TREATMENT,
    source_field_name: str = "Received treatment",
    source_field_definition: str = "接受至少一次研究治疗的受试者",
    measure_object: DispositionMeasureObject = DispositionMeasureObject.SUBJECT,
    statistic_form: DispositionStatisticForm = DispositionStatisticForm.COUNT,
    value: int | float | None = 100,
    raw_value: str | int | float | None = "100例",
    unit: str | None = "例",
    numerator: int | None = 100,
    denominator: int | None = 118,
    denominator_role: DispositionDenominatorRole = DispositionDenominatorRole.RANDOMIZED,
    time_window: str = "治疗期（第1天至第12周）",
    reason_original_text: str | None = None,
    canonical_reason: str | None = None,
    reason_is_mutually_exclusive: bool | None = None,
    reason_is_exhaustive: bool | None = None,
    adherence_definition: str | None = None,
    adherence_threshold: str | None = None,
    protocol_deviation_level: str | None = None,
    source_version_id: str = "source-version-1",
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    reported_zero_text: str | None = None,
    route_receipt_id: str | None = None,
    applicability_predicate_id: str | None = None,
    conflict_disposition: ConflictDisposition = (
        ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
    ),
    difference_labels_zh: tuple[str, ...] = (),
    **overrides: Any,
) -> TrialDispositionObservation:
    """构造一条有效处置事实，显式保留来源和统计语境。"""

    if scope_level is DispositionScopeLevel.OVERALL:
        cohort_id = None
        group_id = None
    elif scope_level is DispositionScopeLevel.COHORT:
        group_id = None
        cohort_id = cohort_id or f"cohort-{token}"
    else:
        cohort_id = cohort_id or f"cohort-{token}"
        group_id = group_id or f"group-{token}"

    if field in {
        DispositionField.SCREENED,
        DispositionField.SCREEN_FAILURE,
        DispositionField.SCREEN_FAILURE_REASON,
    }:
        denominator_role = DispositionDenominatorRole.SCREENED

    if disclosure_state in _MISSING_STATES:
        value = None
        numerator = None
        denominator = None
        reported_zero_text = None
        if disclosure_state is FactDisclosureState.NOT_REPORTED:
            raw_value = None
        elif disclosure_state is FactDisclosureState.BELOW_REPORTING_THRESHOLD:
            raw_value = "<5例"
        elif disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED:
            raw_value = "来源未公开"
        elif disclosure_state is FactDisclosureState.NOT_APPLICABLE:
            raw_value = "不适用"
            applicability_predicate_id = applicability_predicate_id or "predicate-disposition-v1"
        elif disclosure_state is FactDisclosureState.CONFLICTING:
            raw_value = "来源存在冲突"
            conflict_disposition = ConflictDisposition.OPEN_CONFLICT_PRESERVED
        else:
            raw_value = "当前技术路径未解决"
            route_receipt_id = route_receipt_id or "receipt-disposition-1"
    elif disclosure_state is FactDisclosureState.REPORTED_ZERO:
        value = 0
        raw_value = raw_value or "0例"
        reported_zero_text = reported_zero_text or "原文报告 0例"
        numerator = 0 if numerator is None else numerator
    if field_family is DispositionFieldFamily.REASON:
        reason_original_text = reason_original_text or "来源原因原文"
        canonical_reason = canonical_reason or f"规范原因-{token}"
    if field_family is DispositionFieldFamily.ADHERENCE:
        adherence_definition = adherence_definition or "按来源定义计算依从性"
        adherence_threshold = adherence_threshold or "达到规定治疗暴露"
    if field in {
        DispositionField.PROTOCOL_DEVIATION,
        DispositionField.MAJOR_PROTOCOL_DEVIATION,
        DispositionField.PROTOCOL_DEVIATION_LEADING_TO_EXCLUSION,
    }:
        protocol_deviation_level = protocol_deviation_level or "overall"

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": f"disposition-row-{token}",
        "source_row_id": f"source-row-{token}",
        "observation_id": f"disposition-observation-{token}",
        "product_id": product_id,
        "trial_id": trial_id,
        "period_id": period_id,
        "cohort_id": cohort_id,
        "scope_level": scope_level,
        "group_id": group_id,
        "analysis_population": analysis_population,
        "field_family": field_family,
        "field": field,
        "source_field_name": source_field_name,
        "source_field_definition": source_field_definition,
        "measure_object": measure_object,
        "statistic_form": statistic_form,
        "value": value,
        "raw_value": raw_value,
        "unit": unit,
        "numerator": numerator,
        "denominator": denominator,
        "denominator_role": denominator_role,
        "time_window": time_window,
        "reason_original_text": reason_original_text,
        "canonical_reason": canonical_reason,
        "reason_is_mutually_exclusive": reason_is_mutually_exclusive,
        "reason_is_exhaustive": reason_is_exhaustive,
        "adherence_definition": adherence_definition,
        "adherence_threshold": adherence_threshold,
        "protocol_deviation_level": protocol_deviation_level,
        "source_version_id": source_version_id,
        "source_locator": _LOCATOR,
        "source_role": SourceRole.PRIMARY_TRIAL_REPORT,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": disclosure_state,
        "conflict_disposition": conflict_disposition,
        "reported_zero_text": reported_zero_text,
        "route_receipt_id": route_receipt_id,
        "applicability_predicate_id": applicability_predicate_id,
        "compatibility_rule": "trial-disposition-view-v1",
        "difference_labels_zh": difference_labels_zh,
    }
    payload.update(overrides)
    return TrialDispositionObservation.model_validate(payload)


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _row_by_id(rows: Iterable[Any]) -> dict[str, Any]:
    return {row.row_id: row for row in rows}


def test_single_trial_flow_keeps_completion_and_exit_nodes_distinct() -> None:
    flow = (
        _observation(
            "screened",
            field=DispositionField.SCREENED,
            source_field_name="Screened",
            source_field_definition="接受筛选评估的受试者",
            value=150,
            raw_value="150例",
            numerator=150,
            denominator=150,
            denominator_role=DispositionDenominatorRole.SCREENED,
        ),
        _observation(
            "screen-failure",
            field=DispositionField.SCREEN_FAILURE,
            source_field_name="Screen failure",
            source_field_definition="筛选失败的受试者",
            value=32,
            raw_value="32例",
            numerator=32,
            denominator=150,
            denominator_role=DispositionDenominatorRole.SCREENED,
        ),
        _observation(
            "randomized",
            field=DispositionField.RANDOMIZED,
            source_field_name="Randomized",
            source_field_definition="随机分组的受试者",
            value=118,
            raw_value="118例",
            numerator=118,
            denominator=118,
        ),
        _observation(
            "received-treatment",
            field=DispositionField.RECEIVED_TREATMENT,
            value=116,
            raw_value="116例",
            numerator=116,
            denominator=118,
        ),
        _observation(
            "completed-treatment",
            field=DispositionField.COMPLETED_TREATMENT,
            source_field_name="Completed treatment",
            source_field_definition="完成研究治疗的受试者",
            value=106,
            raw_value="106例",
            numerator=106,
            denominator=116,
        ),
        _observation(
            "completed-study",
            field=DispositionField.COMPLETED_STUDY,
            source_field_name="Completed study",
            source_field_definition="完成研究的受试者",
            value=104,
            raw_value="104例",
            numerator=104,
            denominator=118,
        ),
        _observation(
            "treatment-discontinued",
            field=DispositionField.TREATMENT_DISCONTINUED,
            source_field_name="Treatment discontinued",
            source_field_definition="停止研究治疗的受试者",
            value=10,
            raw_value="10例",
            numerator=10,
            denominator=116,
        ),
        _observation(
            "study-withdrawal",
            field=DispositionField.STUDY_WITHDRAWAL,
            source_field_name="Study withdrawal",
            source_field_definition="退出研究的受试者",
            value=12,
            raw_value="12例",
            numerator=12,
            denominator=118,
        ),
        _observation(
            "lost-to-follow-up",
            field=DispositionField.LOST_TO_FOLLOW_UP,
            source_field_name="Lost to follow-up",
            source_field_definition="失访的受试者",
            value=4,
            raw_value="4例",
            numerator=4,
            denominator=118,
        ),
    )

    state = build_disposition_view_state(flow)

    assert len(state.selected_facts) == len(flow)
    assert len(state.chart_panels) == 1
    panel = state.chart_panels[0]
    assert _enum_value(panel.chart_type) == DispositionChartType.CONSORT_FLOW.value
    assert {row.field for row in panel.rows} == {row.field for row in flow}
    assert [row.field for row in panel.rows] == [fact.field for fact in flow]
    assert {
        row.field
        for row in panel.rows
        if row.field in {
            DispositionField.COMPLETED_TREATMENT,
            DispositionField.COMPLETED_STUDY,
            DispositionField.TREATMENT_DISCONTINUED,
            DispositionField.STUDY_WITHDRAWAL,
        }
    } == {
        DispositionField.COMPLETED_TREATMENT,
        DispositionField.COMPLETED_STUDY,
        DispositionField.TREATMENT_DISCONTINUED,
        DispositionField.STUDY_WITHDRAWAL,
    }
    assert set(row.row_id for row in panel.rows) == set(state.table_row_ids)
    assert tuple(row.row_id for row in state.complete_table) == state.table_row_ids


def test_cross_trial_panels_split_denominator_roles_and_never_merge_trials() -> None:
    rows = (
        _observation(
            "trial-a-completed",
            trial_id="trial-a",
            cohort_id="cohort-a",
            field=DispositionField.COMPLETED_STUDY,
            source_field_name="Completed study",
            source_field_definition="完成研究的受试者比例",
            statistic_form=DispositionStatisticForm.PROPORTION,
            value=80.0,
            raw_value="80%",
            unit="%",
            numerator=80,
            denominator=100,
            denominator_role=DispositionDenominatorRole.RANDOMIZED,
        ),
        _observation(
            "trial-b-completed",
            trial_id="trial-b",
            cohort_id="cohort-b",
            field=DispositionField.COMPLETED_STUDY,
            source_field_name="Completed study",
            source_field_definition="完成研究的受试者比例",
            statistic_form=DispositionStatisticForm.PROPORTION,
            value=75.0,
            raw_value="75%",
            unit="%",
            numerator=75,
            denominator=100,
            denominator_role=DispositionDenominatorRole.RANDOMIZED,
        ),
        _observation(
            "trial-c-completed",
            trial_id="trial-c",
            cohort_id="cohort-c",
            field=DispositionField.COMPLETED_STUDY,
            source_field_name="Completed study",
            source_field_definition="完成研究的受试者比例",
            statistic_form=DispositionStatisticForm.PROPORTION,
            value=72.0,
            raw_value="72%",
            unit="%",
            numerator=72,
            denominator=100,
            denominator_role=DispositionDenominatorRole.TREATED,
        ),
    )

    state = build_disposition_view_state(rows)

    assert len(state.chart_panels) == 2
    assert all(
        _enum_value(panel.chart_type)
        in {
            DispositionChartType.PROPORTION_BAR.value,
            DispositionChartType.POINT.value,
        }
        for panel in state.chart_panels
    )
    assert all(
        _enum_value(panel.chart_type) != DispositionChartType.CONSORT_FLOW.value
        for panel in state.chart_panels
    )
    assert {
        _enum_value(panel.denominator_role) for panel in state.chart_panels
    } == {
        DispositionDenominatorRole.RANDOMIZED.value,
        DispositionDenominatorRole.TREATED.value,
    }
    panel_trial_sets = {
        frozenset(row.trial_id for row in panel.rows) for panel in state.chart_panels
    }
    assert panel_trial_sets == {frozenset({"trial-a", "trial-b"}), frozenset({"trial-c"})}
    for panel in state.chart_panels:
        assert all(row.measure_object is DispositionMeasureObject.SUBJECT for row in panel.rows)


def test_counts_and_events_keep_measurement_object_and_user_labels_separate() -> None:
    subject_count = _observation(
        "subject-pd",
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION,
        source_field_name="Protocol deviation subjects",
        source_field_definition="发生方案偏离的受试者",
        measure_object=DispositionMeasureObject.SUBJECT,
        statistic_form=DispositionStatisticForm.COUNT,
        value=7,
        raw_value="7例",
        unit="例",
        numerator=7,
        denominator=100,
        denominator_role=DispositionDenominatorRole.ANALYSIS,
        protocol_deviation_level="any",
    )
    event_count = _observation(
        "event-pd",
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION,
        source_field_name="Protocol deviation events",
        source_field_definition="方案偏离事件次数",
        measure_object=DispositionMeasureObject.EVENT,
        statistic_form=DispositionStatisticForm.EVENT_COUNT,
        value=9,
        raw_value="9件",
        unit="件",
        numerator=None,
        denominator=None,
        denominator_role=DispositionDenominatorRole.ANALYSIS,
        protocol_deviation_level="any",
    )

    state = build_disposition_view_state((subject_count, event_count))

    assert len(state.chart_panels) == 2
    event_panels = [
        panel
        for panel in state.chart_panels
        if panel.rows and panel.rows[0].measure_object is DispositionMeasureObject.EVENT
    ]
    subject_panels = [
        panel
        for panel in state.chart_panels
        if panel.rows and panel.rows[0].measure_object is DispositionMeasureObject.SUBJECT
    ]
    assert len(event_panels) == len(subject_panels) == 1
    event_panel = event_panels[0]
    assert all(
        row.statistic_form is DispositionStatisticForm.EVENT_COUNT
        for row in event_panel.rows
    )
    assert "比例" not in event_panel.title_zh
    assert "受试者比例" not in event_panel.description_zh


def test_only_qualified_reason_sets_may_use_100_percent_stacked_graph() -> None:
    qualified = (
        _observation(
            "qualified-reason-consent",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            source_field_name="Reason for treatment discontinuation",
            source_field_definition="停止治疗原因",
            value=30,
            raw_value="30例",
            numerator=30,
            denominator=100,
            denominator_role=DispositionDenominatorRole.TREATED,
            reason_original_text="受试者撤回同意",
            canonical_reason="撤回同意",
            reason_is_mutually_exclusive=True,
            reason_is_exhaustive=True,
        ),
        _observation(
            "qualified-reason-adverse-event",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            source_field_name="Reason for treatment discontinuation",
            source_field_definition="停止治疗原因",
            value=70,
            raw_value="70例",
            numerator=70,
            denominator=100,
            denominator_role=DispositionDenominatorRole.TREATED,
            reason_original_text="不良事件",
            canonical_reason="不良事件",
            reason_is_mutually_exclusive=True,
            reason_is_exhaustive=True,
        ),
        _observation(
            "qualified-reason-other",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            source_field_name="Reason for treatment discontinuation",
            source_field_definition="停止治疗原因",
            value=0,
            raw_value="0例",
            numerator=0,
            denominator=100,
            denominator_role=DispositionDenominatorRole.TREATED,
            reason_original_text="其他原因",
            canonical_reason="其他",
            reason_is_mutually_exclusive=True,
            reason_is_exhaustive=True,
            disclosure_state=FactDisclosureState.REPORTED_ZERO,
            reported_zero_text="原文报告 0例",
        ),
    )
    unqualified = (
        _observation(
            "unqualified-reason-consent",
            trial_id="trial-2",
            cohort_id="cohort-2",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            source_field_name="Reason for treatment discontinuation",
            source_field_definition="停止治疗原因",
            value=20,
            raw_value="20例",
            numerator=20,
            denominator=100,
            denominator_role=DispositionDenominatorRole.TREATED,
            reason_original_text="受试者撤回同意",
            canonical_reason="撤回同意",
            reason_is_mutually_exclusive=False,
            reason_is_exhaustive=True,
        ),
        _observation(
            "unqualified-reason-adverse-event",
            trial_id="trial-2",
            cohort_id="cohort-2",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            source_field_name="Reason for treatment discontinuation",
            source_field_definition="停止治疗原因",
            value=30,
            raw_value="30例",
            numerator=30,
            denominator=100,
            denominator_role=DispositionDenominatorRole.TREATED,
            reason_original_text="不良事件",
            canonical_reason="不良事件",
            reason_is_mutually_exclusive=False,
            reason_is_exhaustive=True,
        ),
    )

    state = build_disposition_view_state((*qualified, *unqualified))

    stacked = [
        panel
        for panel in state.chart_panels
        if _enum_value(panel.chart_type) == DispositionChartType.REASON_STACKED_100.value
    ]
    independent = [
        panel
        for panel in state.chart_panels
        if _enum_value(panel.chart_type) == DispositionChartType.REASON_INDEPENDENT_BAR.value
    ]
    assert len(stacked) == 1
    assert len(independent) == 1
    assert stacked[0].is_stacked is True
    assert independent[0].is_stacked is False
    assert len(stacked[0].rows) == 3
    assert all(
        row.measure_object is DispositionMeasureObject.SUBJECT
        for row in independent[0].rows
    )


def test_reason_stack_requires_complete_selection_and_one_explicit_denominator() -> None:
    reasons = (
        _observation(
            "reason-consent",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.STUDY_WITHDRAWAL_REASON,
            source_field_name="Reason for withdrawal",
            source_field_definition="退出研究原因",
            value=30,
            raw_value="30例",
            numerator=30,
            denominator=100,
            canonical_reason="撤回同意",
            reason_original_text="受试者撤回同意",
            reason_is_mutually_exclusive=True,
            reason_is_exhaustive=True,
        ),
        _observation(
            "reason-ae",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.STUDY_WITHDRAWAL_REASON,
            source_field_name="Reason for withdrawal",
            source_field_definition="退出研究原因",
            value=50,
            raw_value="50例",
            numerator=50,
            denominator=100,
            canonical_reason="不良事件",
            reason_original_text="不良事件",
            reason_is_mutually_exclusive=True,
            reason_is_exhaustive=True,
        ),
    )
    full = build_disposition_view_state(reasons)
    filtered = full.with_selection({"canonical_reason": ("撤回同意",)})
    mismatched_denominator = build_disposition_view_state(
        (reasons[0], reasons[1].model_copy(update={"denominator": 80}))
    )

    assert full.chart_panels[0].chart_type is DispositionChartType.REASON_STACKED_100
    assert filtered.chart_panels[0].chart_type is DispositionChartType.REASON_INDEPENDENT_BAR
    assert (
        mismatched_denominator.chart_panels[0].chart_type
        is DispositionChartType.REASON_INDEPENDENT_BAR
    )


def test_incompatible_units_scope_and_definitions_split_panels() -> None:
    percent = _observation(
        "percent",
        trial_id="trial-a",
        field=DispositionField.COMPLETED_STUDY,
        statistic_form=DispositionStatisticForm.PROPORTION,
        value=80.0,
        raw_value="80%",
        unit="%",
        numerator=80,
        denominator=100,
        source_field_definition="完成研究的受试者比例",
    )
    fraction = _observation(
        "fraction",
        trial_id="trial-b",
        field=DispositionField.COMPLETED_STUDY,
        statistic_form=DispositionStatisticForm.PROPORTION,
        value=0.8,
        raw_value="0.8",
        unit="ratio",
        numerator=80,
        denominator=100,
        source_field_definition="完成研究的受试者比例",
    )
    overall = _observation(
        "overall",
        trial_id="trial-c",
        scope_level=DispositionScopeLevel.OVERALL,
        field=DispositionField.COMPLETED_STUDY,
        source_field_definition="完成整个研究随访的受试者",
    )

    state = build_disposition_view_state((percent, fraction, overall))

    assert len(state.chart_panels) == 3
    assert percent.row_id != fraction.row_id


def test_subject_count_units_do_not_merge_or_qualify_reason_stack() -> None:
    counts = (
        _observation("subjects", unit="例"),
        _observation("visits", trial_id="trial-2", unit="人次"),
    )
    reasons = (
        _observation(
            "reason-subjects",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.STUDY_WITHDRAWAL_REASON,
            unit="例",
            reason_is_mutually_exclusive=True,
            reason_is_exhaustive=True,
        ),
        _observation(
            "reason-visits",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.STUDY_WITHDRAWAL_REASON,
            unit="人次",
            reason_is_mutually_exclusive=True,
            reason_is_exhaustive=True,
        ),
    )

    count_state = build_disposition_view_state(counts)
    reason_state = build_disposition_view_state(reasons)

    assert len(count_state.chart_panels) == 2
    assert all(
        panel.chart_type is DispositionChartType.REASON_INDEPENDENT_BAR
        for panel in reason_state.chart_panels
    )


def test_single_trial_flow_does_not_mix_count_and_proportion() -> None:
    count = _observation("flow-count", field=DispositionField.RECEIVED_TREATMENT)
    proportion = _observation(
        "flow-rate",
        field=DispositionField.COMPLETED_STUDY,
        statistic_form=DispositionStatisticForm.PROPORTION,
        value=80.0,
        raw_value="80%",
        unit="%",
        numerator=80,
        denominator=100,
    )

    state = build_disposition_view_state((count, proportion))

    assert len(state.chart_panels) == 2
    assert {panel.chart_type for panel in state.chart_panels} == {
        DispositionChartType.CONSORT_FLOW,
        DispositionChartType.PROPORTION_BAR,
    }


def test_event_proportion_uses_event_proportion_chinese_description() -> None:
    event_rate = _observation(
        "event-rate",
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION,
        measure_object=DispositionMeasureObject.EVENT,
        statistic_form=DispositionStatisticForm.PROPORTION,
        value=10.0,
        raw_value="10%",
        unit="%",
        numerator=10,
        denominator=100,
        protocol_deviation_level="all",
    )

    panel = build_disposition_view_state((event_rate,)).chart_panels[0]

    assert "事件比例" in panel.description_zh
    assert "事件数" not in panel.description_zh


def test_missing_states_form_a_status_matrix_and_never_become_zero() -> None:
    rows = (
        _observation(
            "not-reported",
            field=DispositionField.COMPLETED_STUDY,
            disclosure_state=FactDisclosureState.NOT_REPORTED,
        ),
        _observation(
            "below-threshold",
            field=DispositionField.TREATMENT_DISCONTINUED,
            disclosure_state=FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        ),
        _observation(
            "not-public",
            field=DispositionField.STUDY_WITHDRAWAL,
            disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        ),
        _observation(
            "not-applicable",
            field=DispositionField.LOST_TO_FOLLOW_UP,
            disclosure_state=FactDisclosureState.NOT_APPLICABLE,
        ),
        _observation(
            "conflicting",
            field=DispositionField.RECEIVED_TREATMENT,
            disclosure_state=FactDisclosureState.CONFLICTING,
        ),
        _observation(
            "route-unresolved",
            field=DispositionField.RANDOMIZED,
            disclosure_state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
        ),
    )

    state = build_disposition_view_state(rows)
    table = _row_by_id(state.complete_table)

    assert state.status_matrix is not None
    assert _enum_value(state.status_matrix.chart_type) == DispositionChartType.STATUS_MATRIX.value
    assert {row.row_id for row in state.status_matrix.rows} == set(state.table_row_ids)
    assert not any(panel.has_axes for panel in state.chart_panels)
    assert {row.disclosure_state for row in table.values()} == _MISSING_STATES
    assert all(row.value is None for row in table.values())
    assert all(row.is_chart_drawable is False for row in table.values())
    assert {
        row.disclosure_label_zh for row in table.values()
    } == {
        "原文未报告",
        "低于来源列示阈值",
        "未公开",
        "不适用",
        "来源存在冲突",
        "技术路径未解决",
    }
    assert all(
        enum_token not in row.display_value_zh
        for row in table.values()
        for enum_token in ("not_reported", "not_publicly_disclosed", "unresolved_due_to_route")
    )


def test_reported_zero_is_drawable_zero_and_is_not_missing() -> None:
    row = _observation(
        "reported-zero",
        field=DispositionField.LOST_TO_FOLLOW_UP,
        value=0,
        raw_value="0例",
        numerator=0,
        denominator=118,
        disclosure_state=FactDisclosureState.REPORTED_ZERO,
        reported_zero_text="原文报告 0例",
    )

    state = build_disposition_view_state((row,))
    projected = state.complete_table[0]

    assert projected.value == 0
    assert projected.display_value_zh == "0例"
    assert projected.is_chart_drawable is True
    assert projected.disclosure_label_zh == "已报告为零"
    assert state.chart_panels[0].drawable_rows[0].row_id == projected.row_id


def test_complete_table_panels_and_evidence_preserve_one_fact_identity() -> None:
    rows = (
        _observation("age-like-a", field=DispositionField.RECEIVED_TREATMENT),
        _observation(
            "age-like-b",
            field=DispositionField.COMPLETED_STUDY,
            source_field_name="Completed study",
            source_field_definition="完成研究的受试者",
            value=90,
            raw_value="90例",
            numerator=90,
            denominator=100,
        ),
    )

    state = build_disposition_view_state(rows)
    table = _row_by_id(state.complete_table)
    original = {fact.row_id: fact for fact in rows}

    assert set(table) == set(original)
    assert tuple(row.row_id for row in state.complete_table) == state.table_row_ids
    assert {
        row.row_id for panel in state.chart_panels for row in panel.rows
    } == set(state.table_row_ids)
    assert tuple(link.row_id for link in state.evidence_links) == state.table_row_ids
    assert tuple(state.evidence_links_by_row_id) == state.table_row_ids
    for row_id, projected in table.items():
        fact = original[row_id]
        assert projected.fact == fact
        assert projected.source_row_id == fact.source_row_id
        assert projected.observation_id == fact.observation_id
        assert projected.source_field_name == fact.source_field_name
        assert projected.source_field_definition == fact.source_field_definition
        assert projected.measure_object is fact.measure_object
        assert projected.statistic_form is fact.statistic_form
        assert projected.period_id == fact.period_id
        assert projected.scope_level is fact.scope_level
        assert projected.field_family is fact.field_family
        assert projected.field is fact.field
        assert projected.denominator_role is fact.denominator_role
        assert projected.time_window == fact.time_window
        assert projected.numerator == fact.numerator
        assert projected.denominator == fact.denominator
        assert projected.raw_value == fact.raw_value
        assert projected.source_locator == fact.source_locator
        assert projected.fact_version_id == fact.fact_version_id
        assert projected.difference_labels_zh == fact.difference_labels_zh
        evidence = state.evidence_links_by_row_id[row_id]
        assert evidence.row_id == row_id
        assert evidence.fact_row_id == row_id
        assert evidence.observation == fact


def test_model_copy_fact_tampering_is_revalidated_at_view_boundary() -> None:
    row = _observation("tampered-fact")
    forged = row.model_copy(update={"field": DispositionField.COMPLETED_STUDY})

    with pytest.raises(DispositionViewError, match="重新校验|原始观察|不可变"):
        build_disposition_view_state((forged,))
    with pytest.raises(DispositionViewError, match="重复 row_id|重复事实"):
        build_disposition_view_state((row, row))


def test_empty_input_is_a_real_chinese_empty_state() -> None:
    state = build_disposition_view_state(())

    assert state.complete_table == ()
    assert state.chart_panels == ()
    assert state.status_matrix is None
    assert state.empty_state.is_empty is True
    assert state.empty_state.message_zh == "当前筛选范围暂无处置事实"
    assert "disposition" not in state.empty_state.message_zh.casefold()
    assert "pending" not in state.empty_state.message_zh.casefold()
