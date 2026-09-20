"""Task 6.8 B 类处置视图筛选、网址、焦点、重置和失败关闭 RED 测试。"""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from ci_workflow.domain.enums import FactDisclosureState
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
    DispositionSelectionState,
    DispositionViewError,
    apply_disposition_selection,
    build_disposition_view_state,
    reset_disposition_selection,
    selection_from_url,
    selection_to_url,
)
from tests.reports.b.test_disposition_views import _observation


def _facts() -> tuple[TrialDispositionObservation, ...]:
    return (
        _observation(
            "a-received",
            product_id="product-a",
            trial_id="trial-a",
            period_id="period-a",
            cohort_id="cohort-a",
            scope_level=DispositionScopeLevel.GROUP,
            group_id="group-a",
            field=DispositionField.RECEIVED_TREATMENT,
            value=100,
            raw_value="100例",
            numerator=100,
            denominator=120,
            time_window="整个研究期",
        ),
        _observation(
            "a-completed",
            product_id="product-a",
            trial_id="trial-a",
            period_id="period-a",
            cohort_id="cohort-a",
            scope_level=DispositionScopeLevel.GROUP,
            group_id="group-a",
            field=DispositionField.COMPLETED_STUDY,
            source_field_name="Completed study",
            source_field_definition="完成研究的受试者",
            value=92,
            raw_value="92例",
            numerator=92,
            denominator=100,
            time_window="整个研究期",
        ),
        _observation(
            "b-completed",
            product_id="product-b",
            trial_id="trial-b",
            period_id="period-b",
            cohort_id="cohort-b",
            scope_level=DispositionScopeLevel.GROUP,
            group_id="group-b",
            field=DispositionField.COMPLETED_STUDY,
            source_field_name="Completed study",
            source_field_definition="完成研究的受试者",
            value=84,
            raw_value="84例",
            numerator=84,
            denominator=100,
            time_window="整个研究期",
        ),
        _observation(
            "b-discontinuation-reason",
            product_id="product-b",
            trial_id="trial-b",
            period_id="period-b",
            cohort_id="cohort-b",
            scope_level=DispositionScopeLevel.GROUP,
            group_id="group-b",
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            source_field_name="Reason for treatment discontinuation",
            source_field_definition="停止治疗原因",
            value=16,
            raw_value="16例",
            numerator=16,
            denominator=100,
            denominator_role=DispositionDenominatorRole.TREATED,
            time_window="整个研究期",
            reason_original_text="不良事件",
            canonical_reason="不良事件",
            reason_is_mutually_exclusive=False,
            reason_is_exhaustive=False,
        ),
        _observation(
            "b-protocol-event",
            product_id="product-b",
            trial_id="trial-b",
            period_id="period-b",
            cohort_id="cohort-b",
            scope_level=DispositionScopeLevel.GROUP,
            group_id="group-b",
            field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
            field=DispositionField.PROTOCOL_DEVIATION,
            source_field_name="Protocol deviation events",
            source_field_definition="方案偏离事件次数",
            measure_object=DispositionMeasureObject.EVENT,
            statistic_form=DispositionStatisticForm.EVENT_COUNT,
            value=4,
            raw_value="4件",
            unit="件",
            numerator=None,
            denominator=None,
            denominator_role=DispositionDenominatorRole.ANALYSIS,
            time_window="整个研究期",
            protocol_deviation_level="any",
        ),
    )


def test_multi_select_filters_rebuild_all_views_from_one_fact_subset() -> None:
    state = apply_disposition_selection(
        build_disposition_view_state(_facts()),
        {
            "product_ids": ("product-b",),
            "trial_ids": ("trial-b",),
            "period_ids": ("period-b",),
            "cohort_ids": ("cohort-b",),
            "group_ids": ("group-b",),
            "analysis_populations": ("随机化人群",),
            "field_families": (DispositionFieldFamily.PARTICIPANT_FLOW,),
            "fields": (DispositionField.COMPLETED_STUDY,),
            "denominator_roles": (DispositionDenominatorRole.RANDOMIZED,),
            "time_windows": ("整个研究期",),
            "measure_objects": (DispositionMeasureObject.SUBJECT,),
            "statistic_forms": (DispositionStatisticForm.COUNT,),
            "disclosure_states": (FactDisclosureState.REPORTED_VALUE,),
        },
    )

    assert tuple(fact.trial_id for fact in state.selected_facts) == ("trial-b",)
    assert {row.product_id for row in state.complete_table} == {"product-b"}
    assert {row.trial_id for row in state.complete_table} == {"trial-b"}
    assert {row.period_id for row in state.complete_table} == {"period-b"}
    assert {row.cohort_id for row in state.complete_table} == {"cohort-b"}
    assert {row.group_id for row in state.complete_table} == {"group-b"}
    assert {row.field for row in state.complete_table} == {DispositionField.COMPLETED_STUDY}
    assert tuple(row.row_id for row in state.complete_table) == state.table_row_ids
    assert {
        row.row_id for panel in state.chart_panels for row in panel.rows
    } == set(state.table_row_ids)
    assert tuple(link.row_id for link in state.evidence_links) == state.table_row_ids
    assert tuple(state.evidence_links_by_row_id) == state.table_row_ids


def test_supported_and_non_applicable_filters_are_explicit() -> None:
    state = build_disposition_view_state(_facts())

    for dimension in (
        "product",
        "trial",
        "period",
        "cohort",
        "group",
        "analysis_population",
        "field_family",
        "field",
        "denominator_role",
        "time_window",
        "measure_object",
        "statistic_form",
        "disclosure_state",
    ):
        assert state.filter_applicability[dimension].enabled is True
    assert state.filter_applicability["target"].enabled is False
    assert "不适用" in (state.filter_applicability["target"].reason_zh or "")
    assert all("target" not in option.label_zh.casefold() for option in state.filter_options)
    target_selected = state.with_selection({"target_ids": ("target-1",)})
    assert target_selected.selection.target_ids == ("target-1",)
    assert target_selected.complete_table == ()


def test_page_module_and_full_reset_are_separate_and_reversible() -> None:
    initial = build_disposition_view_state(_facts())
    focus_id = next(
        row.row_id
        for row in initial.complete_table
        if row.field is DispositionField.PROTOCOL_DEVIATION
    )
    selected = initial.with_selection(
        {
            "product_ids": ("product-b",),
            "trial_ids": ("trial-b",),
            "period_ids": ("period-b",),
            "field_families": (DispositionFieldFamily.PROTOCOL_DEVIATION,),
            "fields": (DispositionField.PROTOCOL_DEVIATION,),
            "measure_objects": (DispositionMeasureObject.EVENT,),
            "statistic_forms": (DispositionStatisticForm.EVENT_COUNT,),
            "evidence_focus_id": focus_id,
        }
    )

    module_reset = reset_disposition_selection(selected, scope="module")
    page_reset = reset_disposition_selection(selected, scope="page")
    full_reset = reset_disposition_selection(selected)

    assert module_reset.selection.product_ids == ("product-b",)
    assert module_reset.selection.trial_ids == ("trial-b",)
    assert module_reset.selection.period_ids == ("period-b",)
    assert module_reset.selection.field_families == ()
    assert module_reset.selection.fields == ()
    assert module_reset.selection.measure_objects == ()
    assert module_reset.selection.statistic_forms == ()
    assert module_reset.selection.evidence_focus_id is None
    assert page_reset.selection.product_ids == ()
    assert page_reset.selection.trial_ids == ()
    assert page_reset.selection.period_ids == ()
    assert page_reset.selection.field_families == (
        DispositionFieldFamily.PROTOCOL_DEVIATION,
    )
    assert page_reset.selection.fields == (DispositionField.PROTOCOL_DEVIATION,)
    assert page_reset.selection.evidence_focus_id == focus_id
    assert full_reset.selection == initial.selection
    assert full_reset.complete_table == initial.complete_table
    assert full_reset.url == initial.url


def test_repeated_url_parameters_round_trip_every_disposition_dimension() -> None:
    selection = DispositionSelectionState(
        product_ids=("product-b", "product-a"),
        target_ids=("target-2", "target-1"),
        trial_ids=("trial-b",),
        period_ids=("period-b",),
        cohort_ids=("cohort-b",),
        group_ids=("group-b",),
        analysis_populations=("随机化人群", "安全性人群"),
        field_families=(
            DispositionFieldFamily.PROTOCOL_DEVIATION,
            DispositionFieldFamily.PARTICIPANT_FLOW,
        ),
        fields=(DispositionField.COMPLETED_STUDY, DispositionField.RECEIVED_TREATMENT),
        canonical_reasons=("不良事件", "撤回同意"),
        denominator_roles=(
            DispositionDenominatorRole.RANDOMIZED,
            DispositionDenominatorRole.TREATED,
        ),
        time_windows=("整个研究期", "治疗期"),
        measure_objects=(DispositionMeasureObject.SUBJECT, DispositionMeasureObject.EVENT),
        statistic_forms=(
            DispositionStatisticForm.COUNT,
            DispositionStatisticForm.EVENT_COUNT,
        ),
        disclosure_states=(
            FactDisclosureState.REPORTED_VALUE,
            FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        ),
        evidence_focus_id="disposition-row-focus",
    )

    url = selection_to_url(selection, route="/b/disposition-overview")
    restored = selection_from_url(url)
    query = parse_qs(urlsplit(url).query, keep_blank_values=True)

    assert restored == selection
    assert url.startswith("/b/disposition-overview?")
    assert query["product"] == ["product-a", "product-b"]
    assert query["target"] == ["target-1", "target-2"]
    assert query["trial"] == ["trial-b"]
    assert query["period"] == ["period-b"]
    assert query["cohort"] == ["cohort-b"]
    assert query["group"] == ["group-b"]
    assert query["population"] == ["安全性人群", "随机化人群"]
    assert query["family"] == ["participant_flow", "protocol_deviation"]
    assert query["field"] == ["completed_study", "received_treatment"]
    assert query["reason"] == ["不良事件", "撤回同意"]
    assert query["denominator"] == ["randomized", "treated"]
    assert query["window"] == ["整个研究期", "治疗期"]
    assert query["measure"] == ["event", "subject"]
    assert query["statistic"] == ["count", "event_count"]
    assert query["disclosure"] == ["not_publicly_disclosed", "reported_value"]
    assert query["focus"] == ["disposition-row-focus"]
    assert "%E9%9A%8F%E6%9C%BA%E5%8C%96%E4%BA%BA%E7%BE%A4" in url


def test_url_unknown_fields_and_duplicate_scalar_focus_fail_closed() -> None:
    with pytest.raises(DispositionViewError, match="未知字段"):
        selection_from_url("/b/disposition-overview?unexpected=value")
    with pytest.raises(DispositionViewError, match="重复|focus"):
        selection_from_url("/b/disposition-overview?focus=row-a&focus=row-b")
    with pytest.raises(DispositionViewError, match="路由|页面"):
        selection_from_url("/a/other?trial=trial-a")
    with pytest.raises(DispositionViewError, match="相对地址|路由|页面"):
        selection_from_url("https://example.org/b/disposition?trial=trial-a")


@pytest.mark.parametrize(
    "route",
    (
        "/b/disposition",
        "/b/disposition-overview",
        "/b/participant-flow",
        "/b/adherence",
        "/b/loss-exit",
        "/b/screen-failure",
        "/b/rescue-treatment",
        "/b/prohibited-medication",
        "/b/plan-deviation",
    ),
)
def test_disposition_page_routes_share_one_url_contract(route: str) -> None:
    selection = DispositionSelectionState(trial_ids=("trial-a",))

    url = selection_to_url(selection, route=route)

    assert url.startswith(f"{route}?")
    assert selection_from_url(url) == selection
    assert build_disposition_view_state(_facts(), selection, route=route).route == route


def test_mapping_aliases_are_normalized_before_validation() -> None:
    state = build_disposition_view_state(_facts())

    selected = state.with_selection(
        {
            "period_id": ("period-b",),
            "field_family": (DispositionFieldFamily.PARTICIPANT_FLOW,),
        }
    )

    assert selected.selection.period_ids == ("period-b",)
    assert selected.selection.field_families == (
        DispositionFieldFamily.PARTICIPANT_FLOW,
    )

    built = build_disposition_view_state(
        _facts(),
        {
            "period_id": ("period-b",),
            "canonical_reason": ("撤回同意",),
        },
    )
    url = selection_to_url(
        {
            "period_id": ("period-b",),
            "field_family": (DispositionFieldFamily.PARTICIPANT_FLOW,),
        }
    )

    assert built.selection.period_ids == ("period-b",)
    assert built.selection.canonical_reasons == ("撤回同意",)
    assert selection_from_url(url).period_ids == ("period-b",)
    assert selection_from_url(url).field_families == (
        DispositionFieldFamily.PARTICIPANT_FLOW,
    )


def test_engineering_tokens_do_not_leak_into_filter_labels() -> None:
    fact = _observation(
        "engineering-label",
        analysis_population="randomized_population",
        time_window="treatment_window_v1",
    )
    state = build_disposition_view_state((fact,))
    labels = tuple(option.label_zh for option in state.filter_options)

    assert all("randomized_population" not in label for label in labels)
    assert all("treatment_window_v1" not in label for label in labels)
    assert any("其他分析人群" in label for label in labels)
    assert any("其他观察时间范围" in label for label in labels)


def test_evidence_focus_keeps_filters_and_points_to_the_same_fact_row() -> None:
    initial = build_disposition_view_state(_facts())
    focus_id = next(
        row.row_id
        for row in initial.complete_table
        if row.field is DispositionField.COMPLETED_STUDY
    )

    focused = initial.with_evidence_focus(focus_id)

    assert focused.selection.evidence_focus_id == focus_id
    assert focused.evidence_focus_row_id == focus_id
    assert focused.evidence_focus is not None
    assert focused.evidence_focus.row_id == focus_id
    assert focused.evidence_focus.fact.row_id == focus_id
    assert focused.complete_table == initial.complete_table
    assert focused.chart_panels == initial.chart_panels
    assert focused.evidence_links_by_row_id[focus_id].row_id == focus_id
    assert selection_from_url(focused.url) == focused.selection


def test_expired_focus_is_cleared_and_url_is_normalized_to_current_facts() -> None:
    expired = selection_from_url(
        "/b/disposition-overview?trial=trial-a&focus=expired-row"
    )
    state = build_disposition_view_state(_facts(), expired)

    assert state.selection.trial_ids == ("trial-a",)
    assert state.selection.evidence_focus_id is None
    assert state.evidence_focus is None
    assert state.evidence_focus_row_id is None
    assert "focus" not in parse_qs(urlsplit(state.url).query, keep_blank_values=True)
    assert selection_from_url(state.url) == state.selection


def test_unavailable_filter_does_not_auto_widen_a_no_result_view() -> None:
    initial = build_disposition_view_state(_facts())
    selected = initial.with_selection(
        {
            "product_ids": ("product-a",),
            "group_ids": ("group-that-does-not-exist",),
            "fields": (DispositionField.COMPLETED_STUDY,),
            "disclosure_states": (FactDisclosureState.REPORTED_VALUE,),
        }
    )

    assert selected.complete_table == ()
    assert selected.chart_panels == ()
    assert selected.status_matrix is None
    assert selected.selection.product_ids == ("product-a",)
    assert selected.selection.group_ids == ("group-that-does-not-exist",)
    assert selected.selection.fields == (DispositionField.COMPLETED_STUDY,)
    assert selected.empty_state.is_empty is True
    assert selected.empty_state.message_zh == "当前筛选范围暂无处置事实"
    assert "放宽" not in selected.empty_state.message_zh
    assert selected.url != initial.url


def test_selection_model_copy_tampering_is_rejected_before_filtering() -> None:
    initial = build_disposition_view_state(_facts())
    forged = initial.selection.model_copy(update={"trial_ids": ("trial-a", 42)})

    with pytest.raises(DispositionViewError, match="重新校验|选择状态"):
        initial.with_selection(forged)


def test_forged_view_state_fails_closed_before_public_rebuild() -> None:
    state = build_disposition_view_state(_facts())
    forged = state.model_copy(update={"complete_table": ()})

    with pytest.raises(DispositionViewError, match="重新计算|同步|一致"):
        forged.assert_synchronized()
    with pytest.raises(DispositionViewError, match="重新计算|同步|一致"):
        forged.with_selection({})
    with pytest.raises(TypeError):
        state.url_state["product"] = "forged"  # type: ignore[index]
    with pytest.raises(TypeError):
        state.evidence_links_by_row_id["forged"] = state.evidence_links[0]  # type: ignore[index]

    forged_default = state.model_copy(
        update={"default_selection": DispositionSelectionState(trial_ids=("trial-a",))}
    )
    with pytest.raises(DispositionViewError, match="默认选择|重新校验|同步"):
        forged_default.assert_synchronized()
