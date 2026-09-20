"""Task 6.6 B 类基线视图筛选、网址、焦点和空状态合同。"""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.reports.b.baseline import (
    BaselineObservation,
    BaselineStatisticForm,
    BaselineVariableDomain,
)
from ci_workflow.reports.b.baseline_views import (
    BaselineSelectionState,
    BaselineViewError,
    apply_baseline_selection,
    build_baseline_view_state,
    reset_baseline_selection,
    selection_from_url,
    selection_to_url,
)
from tests.reports.b.test_baseline_views import _observation, _proportion, _severity


def _facts() -> tuple[BaselineObservation, ...]:
    return (
        _observation(
            "a-age",
            product_id="product-a",
            trial_id="trial-a",
            cohort_id="cohort-a",
            group_id="group-a",
        ),
        _proportion(
            "a-sex",
            product_id="product-a",
            trial_id="trial-a",
            cohort_id="cohort-a",
            category="女性",
            numerator=45,
            value=45.0,
            group_id="group-a",
        ),
        _severity(
            "a-severity",
            product_id="product-a",
            trial_id="trial-a",
            cohort_id="cohort-a",
            group_id="group-a",
        ),
        _observation(
            "b-age",
            product_id="product-b",
            trial_id="trial-b",
            cohort_id="cohort-b",
            group_id="group-b",
            value=42.0,
            raw_value="42.0（10.2）",
        ),
        _observation(
            "b-duration",
            product_id="product-b",
            trial_id="trial-b",
            cohort_id="cohort-b",
            group_id="group-b",
            variable_domain=BaselineVariableDomain.DISEASE_CONTEXT,
            source_name="Disease duration",
            source_definition="Disease duration at baseline",
            standardized_concept="disease_duration",
            value=6.0,
            raw_value="6.0",
            unit="年",
            dispersion=None,
            denominator=None,
        ),
    )


def test_page_and_module_filters_rebuild_chart_and_table_from_one_fact_subset() -> None:
    state = apply_baseline_selection(
        # The initial state proves that page and module dimensions have defaults.
        build_baseline_view_state(_facts()),
        {
            "product_ids": ("product-b",),
            "trial_ids": ("trial-b",),
            "cohort_ids": ("cohort-b",),
            "group_ids": ("group-b",),
            "variable_domains": (BaselineVariableDomain.DISEASE_CONTEXT,),
            "standardized_concepts": ("disease_duration",),
            "analysis_populations": ("全分析集",),
            "statistic_forms": (BaselineStatisticForm.MEAN,),
        },
    )

    assert {row.product_id for row in state.complete_table} == {"product-b"}
    assert {row.trial_id for row in state.complete_table} == {"trial-b"}
    assert {row.cohort_id for row in state.complete_table} == {"cohort-b"}
    assert {row.group_id for row in state.complete_table} == {"group-b"}
    assert {row.standardized_concept for row in state.complete_table} == {"disease_duration"}
    assert tuple(row.row_id for row in state.complete_table) == state.table_row_ids
    assert {
        row.row_id for panel in state.chart_panels for row in panel.drawable_rows
    } <= set(state.table_row_ids)
    assert set(state.evidence_links_by_row_id) == set(state.table_row_ids)


def test_supported_and_non_applicable_filter_dimensions_are_explicit() -> None:

    state = build_baseline_view_state(_facts())
    applicability = state.filter_applicability

    assert applicability["product"].enabled is True
    assert applicability["trial"].enabled is True
    assert applicability["cohort"].enabled is True
    assert applicability["group"].enabled is True
    assert applicability["analysis_population"].enabled is True
    assert applicability["variable_domain"].enabled is True
    assert applicability["standardized_concept"].enabled is True
    assert applicability["statistic_form"].enabled is True
    assert applicability["target"].enabled is False
    assert applicability["region"].enabled is False
    assert "不适用" in (applicability["target"].reason_zh or "")
    assert "不适用" in (applicability["region"].reason_zh or "")
    assert all("target" not in option.label_zh.casefold() for option in state.filter_options)


def test_page_and_module_reset_are_separate_and_reversible() -> None:

    initial = build_baseline_view_state(_facts())
    selected = initial.with_selection(
        {
            "product_ids": ("product-b",),
            "trial_ids": ("trial-b",),
            "standardized_concepts": ("disease_duration",),
            "variable_domains": (BaselineVariableDomain.DISEASE_CONTEXT,),
            "evidence_focus_id": initial.table_row_ids[-1],
        }
    )

    module_reset = reset_baseline_selection(selected, scope="module")
    page_reset = reset_baseline_selection(selected, scope="page")
    full_reset = reset_baseline_selection(selected)

    assert module_reset.selection.product_ids == ("product-b",)
    assert module_reset.selection.trial_ids == ("trial-b",)
    assert module_reset.selection.standardized_concepts == ()
    assert module_reset.selection.variable_domains == ()
    assert module_reset.selection.evidence_focus_id is None
    assert page_reset.selection.product_ids == ()
    assert page_reset.selection.trial_ids == ()
    assert page_reset.selection.standardized_concepts == ("disease_duration",)
    assert page_reset.selection.variable_domains == (BaselineVariableDomain.DISEASE_CONTEXT,)
    assert page_reset.selection.evidence_focus_id == selected.selection.evidence_focus_id
    assert full_reset.selection == initial.selection
    assert full_reset.complete_table == initial.complete_table
    assert full_reset.url == initial.url


def test_all_required_selection_dimensions_round_trip_through_standard_library_url() -> None:
    selection = BaselineSelectionState(
        product_ids=("product-b", "product-a"),
        target_ids=("target-2", "target-1"),
        trial_ids=("trial-b",),
        cohort_ids=("cohort-b",),
        group_ids=("group-b",),
        region_ids=("中国", "境外"),
        analysis_populations=("全分析集", "符合方案集"),
        variable_domains=(
            BaselineVariableDomain.BASELINE_SEVERITY,
            BaselineVariableDomain.DISEASE_CONTEXT,
        ),
        standardized_concepts=("easi_total_score", "disease_duration"),
        statistic_forms=(BaselineStatisticForm.MEAN, BaselineStatisticForm.QUARTILES),
        scales=("EASI", "NRS"),
        units=("分", "年"),
        disclosure_states=(
            FactDisclosureState.REPORTED_VALUE,
            FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        ),
        evidence_focus_id="baseline-row-focus",
    )

    url = selection_to_url(selection, route="/b/baseline-severity")
    restored = selection_from_url(url)
    query = parse_qs(urlsplit(url).query, keep_blank_values=True)

    assert restored == selection
    assert url.startswith("/b/baseline-severity?")
    assert query["product"] == ["product-a", "product-b"]
    assert query["target"] == ["target-1", "target-2"]
    assert query["trial"] == ["trial-b"]
    assert query["cohort"] == ["cohort-b"]
    assert query["group"] == ["group-b"]
    assert query["region"] == ["中国", "境外"]
    assert query["population"] == ["全分析集", "符合方案集"]
    assert query["domain"] == ["baseline_severity", "disease_context"]
    assert query["concept"] == ["disease_duration", "easi_total_score"]
    assert query["statistic"] == ["mean", "quartiles"]
    assert query["scale"] == ["EASI", "NRS"]
    assert query["unit"] == ["分", "年"]
    assert query["disclosure"] == ["not_publicly_disclosed", "reported_value"]
    assert query["focus"] == ["baseline-row-focus"]
    assert "%E4%B8%AD%E5%9B%BD" in url


def test_url_unknown_fields_and_duplicate_scalar_focus_fail_closed() -> None:
    with pytest.raises(BaselineViewError, match="未知字段"):
        selection_from_url("/b/baseline?unexpected=value")
    with pytest.raises(BaselineViewError, match="重复|focus"):
        selection_from_url("/b/baseline?focus=row-a&focus=row-b")


def test_evidence_focus_keeps_filter_range_and_exposes_the_same_table_row() -> None:

    initial = build_baseline_view_state(_facts())
    focus_id = next(
        row.row_id for row in initial.complete_table if row.standardized_concept == "age"
    )
    focused = initial.with_evidence_focus(focus_id)

    assert focused.selection.evidence_focus_id == focus_id
    assert focused.evidence_focus_row_id == focus_id
    assert focused.evidence_focus is not None
    assert focused.evidence_focus.row_id == focus_id
    assert focused.evidence_focus.source_row_id == next(
        row.source_row_id for row in focused.complete_table if row.row_id == focus_id
    )
    assert focused.complete_table == initial.complete_table
    assert focused.chart_panels == initial.chart_panels
    assert selection_from_url(focused.url) == focused.selection


def test_no_result_preserves_every_filter_and_does_not_auto_widen_scope() -> None:

    initial = build_baseline_view_state(_facts())
    selected = initial.with_selection(
        {
            "product_ids": ("product-a",),
            "group_ids": ("group-that-does-not-exist",),
            "standardized_concepts": ("age",),
            "disclosure_states": (FactDisclosureState.REPORTED_VALUE,),
        }
    )

    assert selected.complete_table == ()
    assert selected.chart_panels == ()
    assert selected.selection.product_ids == ("product-a",)
    assert selected.selection.group_ids == ("group-that-does-not-exist",)
    assert selected.selection.standardized_concepts == ("age",)
    assert selected.selection.disclosure_states == (FactDisclosureState.REPORTED_VALUE,)
    assert selected.empty_state.is_empty is True
    assert selected.empty_state.message_zh == "当前筛选范围暂无基线事实"
    assert selected.url != initial.url
    assert "放宽" not in selected.empty_state.message_zh


def test_selection_boundary_rejects_model_copy_tampering_before_filtering() -> None:

    initial = build_baseline_view_state(_facts())
    forged = initial.selection.model_copy(update={"product_ids": ("product-a", 42)})
    with pytest.raises(BaselineViewError, match="重新校验|选择状态"):
        initial.with_selection(forged)


def test_view_state_rejects_forged_fact_and_exposes_read_only_indexes() -> None:
    state = build_baseline_view_state(_facts())
    forged_fact = state.facts[0].model_copy(update={"value": 999})
    forged_state = state.model_copy(update={"facts": (forged_fact, *state.facts[1:])})

    with pytest.raises(BaselineViewError, match="重新计算|重新校验"):
        forged_state.with_selection({})
    with pytest.raises(TypeError):
        state.url_state["product"] = "forged"  # type: ignore[index]


def test_unknown_internal_concept_does_not_leak_into_chinese_filter_label() -> None:
    payload = _facts()[0].model_dump(mode="python")
    payload.update(
        {"standardized_concept": "pending_status", "source_name": "pending_status"}
    )
    unknown = BaselineObservation.model_validate(payload)
    state = build_baseline_view_state((unknown,))
    labels = tuple(option.label_zh for option in state.filter_options)

    assert all("pending_status" not in label for label in labels)
    assert any("其他基线变量" in label for label in labels)
