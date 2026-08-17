"""Task 5.3 A 类疗效—安全性气泡矩阵合同。"""

from __future__ import annotations

import math

import pytest

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.gates.models import GateEvaluationError
from ci_workflow.reports.a.analysis import (
    ArmRole,
    SafetyFamily,
    SafetyMeasureRecord,
    build_bubble_matrix,
    build_efficacy_safety_summary,
)
from tests.reports.a.test_efficacy_safety_summary import _case, _scoped
from tests.reports.a.test_result_bearing_gate import _safety


def _summary():
    args = _case()
    return build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=args[2],
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )


def test_bubble_uses_direction_corrected_efficacy_inverted_raw_teae_and_sample_size() -> None:
    summary = _summary()
    view = build_bubble_matrix(
        summary,
        current_universe_summary=summary.identity.universe_summary,
        radius_scale=2.0,
    )
    point = view.points[0]
    assert point.arm_role is ArmRole.TREATMENT
    assert point.efficacy_position == 51.2
    assert point.raw_safety_rate == 78.0
    assert point.safety_position == 22.0
    assert point.sample_size == 224
    assert point.radius == pytest.approx(2.0 * math.sqrt(224 / math.pi))
    assert view.safety_term_id == "teae-any"
    assert view.safety_event_definition_zh == "治疗期间不良事件"
    assert view.safety_time_window_zh == "治疗期间"
    assert view.safety_analysis_population_zh == "意向治疗集"
    assert view.y_axis_note_zh == "向上 = 发生率更低 = 观察到的安全性位置更有利"
    dumped = view.model_dump()
    assert "score" not in str(dumped).lower()
    assert "rank" not in str(dumped).lower()


def test_default_bubble_uses_teae_and_never_substitutes_sae() -> None:
    summary = _summary()
    without_teae = summary.model_copy(
        update={
            "safety_cells": tuple(
                cell.model_copy(update={"family": SafetyFamily.SAE})
                for cell in summary.safety_cells
            )
        }
    )
    with pytest.raises(GateEvaluationError, match="摘要"):
        build_bubble_matrix(
            without_teae,
            current_universe_summary=summary.identity.universe_summary,
        )


def test_unknown_endpoint_selection_is_rejected() -> None:
    summary = _summary()
    with pytest.raises(GateEvaluationError, match="疗效指标"):
        build_bubble_matrix(
            summary,
            current_universe_summary=summary.identity.universe_summary,
            endpoint_family_id="unknown",
        )


def test_nonpositive_radius_scale_is_rejected() -> None:
    summary = _summary()
    with pytest.raises(ValueError):
        build_bubble_matrix(
            summary,
            current_universe_summary=summary.identity.universe_summary,
            radius_scale=0,
        )


def test_old_universe_summary_is_rejected() -> None:
    summary = _summary()
    with pytest.raises(GateEvaluationError, match="当前竞品宇宙"):
        build_bubble_matrix(summary, current_universe_summary="old-universe-summary")


def test_participant_count_uses_derived_rate_and_still_plots() -> None:
    args = _case()
    bindings = tuple(
        binding.model_copy(update={"numeric_value": 39, "denominator": 50, "unit": "例"})
        if binding.fact_version_id == "teae-active"
        else binding
        for binding in args[2]
    )
    summary = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=bindings,
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=args[6],
    )
    view = build_bubble_matrix(
        summary,
        current_universe_summary=summary.identity.universe_summary,
    )
    assert view.points[0].raw_safety_rate == 78.0
    assert view.points[0].sample_size == 50


def test_default_bubble_uses_explicit_overall_teae_not_first_sorted_term() -> None:
    args = _case()
    other_base = _safety(event_definition="其他治疗期间不良事件", numeric_value=5.0)
    other_active = _scoped(
        other_base,
        fact="other-teae-active",
        group="grp-active",
        value=5.0,
    )
    other_control = _scoped(
        other_base,
        fact="other-teae-control",
        group="grp-control",
        value=4.0,
    )
    safety_records = (
        *args[6],
        SafetyMeasureRecord(
            fact_version_id="other-teae-active",
            family=SafetyFamily.TEAE,
            term_id="aaa-other",
            arm_role=ArmRole.TREATMENT,
        ),
        SafetyMeasureRecord(
            fact_version_id="other-teae-control",
            family=SafetyFamily.TEAE,
            term_id="aaa-other",
            arm_role=ArmRole.CONTROL,
        ),
    )
    summary = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=(*args[2], other_active, other_control),
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=safety_records,
    )
    view = build_bubble_matrix(
        summary,
        current_universe_summary=summary.identity.universe_summary,
    )
    assert view.points[0].raw_safety_rate == 78.0
    assert view.points[0].safety_term_id == "teae-any"
    assert view.points[0].safety_time_window_zh == "治疗期间"
    assert view.points[0].safety_fact_version_id == "teae-active"


def test_explicit_safety_term_with_multiple_windows_requires_window_selection() -> None:
    args = _case()
    followup_base = _safety(time_window="随访期", numeric_value=10.0)
    followup_active = _scoped(
        followup_base,
        fact="teae-followup-active",
        group="grp-active",
        value=10.0,
    )
    followup_control = _scoped(
        followup_base,
        fact="teae-followup-control",
        group="grp-control",
        value=8.0,
    )
    safety_records = (
        *args[6],
        SafetyMeasureRecord(
            fact_version_id="teae-followup-active",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.TREATMENT,
        ),
        SafetyMeasureRecord(
            fact_version_id="teae-followup-control",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.CONTROL,
        ),
    )
    summary = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=(*args[2], followup_active, followup_control),
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=safety_records,
    )
    with pytest.raises(GateEvaluationError, match="存在多个时间窗"):
        build_bubble_matrix(
            summary,
            current_universe_summary=summary.identity.universe_summary,
            safety_term_id="teae-any",
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"safety_term_id": "不存在的安全性事件"}, "安全性事件不属于"),
        ({"safety_time_window_zh": "不存在的时间窗"}, "安全性时间窗不属于"),
    ],
)
def test_unknown_safety_selection_is_rejected(
    kwargs: dict[str, str],
    message: str,
) -> None:
    summary = _summary()
    with pytest.raises(GateEvaluationError, match=message):
        build_bubble_matrix(
            summary,
            current_universe_summary=summary.identity.universe_summary,
            **kwargs,
        )


def test_multiple_complete_safety_contexts_require_context_selection() -> None:
    args = _case()
    second_base = _safety(numeric_value=60.0).model_copy(
        update={"analysis_population": "安全性分析集"}
    )
    second_active = _scoped(
        second_base,
        fact="teae-itt-active",
        group="grp-active",
        value=60.0,
    )
    second_control = _scoped(
        second_base,
        fact="teae-itt-control",
        group="grp-control",
        value=55.0,
    )
    safety_records = (
        *args[6],
        SafetyMeasureRecord(
            fact_version_id="teae-itt-active",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.TREATMENT,
        ),
        SafetyMeasureRecord(
            fact_version_id="teae-itt-control",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.CONTROL,
        ),
    )
    summary = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=(*args[2], second_active, second_control),
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=safety_records,
    )
    with pytest.raises(GateEvaluationError, match="多个安全性完整语境"):
        build_bubble_matrix(
            summary,
            current_universe_summary=summary.identity.universe_summary,
            safety_term_id="teae-any",
            safety_time_window_zh="治疗期间",
        )
    selected = build_bubble_matrix(
        summary,
        current_universe_summary=summary.identity.universe_summary,
        safety_term_id="teae-any",
        safety_time_window_zh="治疗期间",
        safety_analysis_population_zh="安全性分析集",
    )
    assert selected.points[0].raw_safety_rate == 60.0
    assert selected.points[0].safety_analysis_population_zh == "安全性分析集"


def test_unquantified_context_still_participates_in_ambiguity_detection() -> None:
    args = _case()
    missing_base = _safety(
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        numeric_value=None,
        denominator=None,
        source_location=None,
    ).model_copy(update={"analysis_population": "安全性分析集"})
    missing_active = _scoped(
        missing_base,
        fact="teae-missing-active",
        group="grp-active",
        value=None,
    )
    missing_control = _scoped(
        missing_base,
        fact="teae-missing-control",
        group="grp-control",
        value=None,
    )
    safety_records = (
        *args[6],
        SafetyMeasureRecord(
            fact_version_id="teae-missing-active",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.TREATMENT,
        ),
        SafetyMeasureRecord(
            fact_version_id="teae-missing-control",
            family=SafetyFamily.TEAE,
            term_id="teae-any",
            arm_role=ArmRole.CONTROL,
        ),
    )
    summary = build_efficacy_safety_summary(
        projects=(args[0],),
        snapshot=args[1],
        bindings=(*args[2], missing_active, missing_control),
        trial_selection=args[3],
        group_roles=args[7],
        endpoint_families=args[4],
        efficacy_records=args[5],
        safety_records=safety_records,
    )
    with pytest.raises(GateEvaluationError, match="多个安全性完整语境"):
        build_bubble_matrix(
            summary,
            current_universe_summary=summary.identity.universe_summary,
            safety_term_id="teae-any",
            safety_time_window_zh="治疗期间",
        )
