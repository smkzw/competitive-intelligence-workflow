from __future__ import annotations

import pytest

from ci_workflow.reports.b.semantic_contract import (
    BUBBLE_PRESETS,
    ClinicalConstructObservation,
    ClinicalSemanticError,
    SemanticAdjudicationReceipt,
    assert_clinical_construct_compatible,
    build_bubble_point,
    compare_clinical_constructs,
)


def _observation(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "observation_id": "obs-1",
        "clinical_construct": "easi75_response",
        "definition": "EASI-75应答者比例",
        "direction": "higher_is_better",
        "unit": "%",
        "estimand": "treatment_policy",
        "denominator": "full_analysis_set",
        "analysis_set": "full_analysis_set",
        "analysis_form": "response_rate",
        "instrument_or_scale": "EASI v1.0",
        "actual_timepoint": 48,
        "actual_timepoint_unit": "week",
    }
    value.update(overrides)
    return value


def test_48_and_50_week_observations_share_only_compatible_construct_frame() -> None:
    result = compare_clinical_constructs(
        _observation(observation_id="obs-48", actual_timepoint=48),
        _observation(observation_id="obs-50", actual_timepoint=50),
    )
    assert result.compatible is True
    assert result.time_window_note_zh

    with pytest.raises(ClinicalSemanticError):
        assert_clinical_construct_compatible(
            (
                _observation(observation_id="obs-48"),
                _observation(observation_id="obs-50", instrument_or_scale="EASI v2.0"),
            )
        )


def test_semantic_conflicts_are_not_pooled() -> None:
    for field, value in (
        ("direction", "lower_is_better"),
        ("estimand", "hypothetical"),
        ("denominator", "randomized_population"),
        ("analysis_set", "per_protocol"),
        ("analysis_form", "mean_difference"),
    ):
        result = compare_clinical_constructs(_observation(), _observation(**{field: value}))
        assert result.compatible is False
        assert result.reasons


@pytest.mark.parametrize(
    "field",
    ["clinical_construct", "definition", "direction", "unit", "estimand",
     "denominator", "analysis_set", "analysis_form", "instrument_or_scale"],
)
@pytest.mark.parametrize("unknown", ["not_reported", "UNKNOWN", "未报告"])
def test_matching_unknown_semantics_do_not_prove_compatibility(field: str, unknown: str) -> None:
    result = compare_clinical_constructs(
        _observation(observation_id="left", **{field: unknown}),
        _observation(observation_id="right", **{field: unknown}),
    )
    assert result.compatible is False
    assert any("未明确" in reason for reason in result.reasons)


def test_missing_semantics_cannot_be_overridden_by_wording_adjudication() -> None:
    receipt = SemanticAdjudicationReceipt(
        adjudication_id="adj-unknown",
        observation_ids=("left", "right"),
        decision="compatible",
        model_id="medical-semantic-review-v1",
        independent_review_id="review-1",
        independent_context="clean-context-1",
        rationale_zh="表述相同，但不能据此补造未知的分析集。",
    )
    result = compare_clinical_constructs(
        _observation(observation_id="left", analysis_set="analysis-set-not-reported"),
        _observation(observation_id="right", analysis_set="analysis-set-not-reported"),
        adjudication=receipt,
    )
    assert result.compatible is False


def test_model_adjudication_can_merge_wording_but_not_hard_semantic_conflicts() -> None:
    left = ClinicalConstructObservation.model_validate(
        _observation(observation_id="left")
    )
    right = ClinicalConstructObservation.model_validate(
        _observation(
            observation_id="right",
            clinical_construct="EASI 75 responder rate",
            definition="达到基线 EASI 改善不少于 75% 的受试者比例",
            actual_timepoint=50,
        )
    )
    receipt = SemanticAdjudicationReceipt(
        adjudication_id="adj-1",
        observation_ids=("left", "right"),
        decision="compatible",
        model_id="medical-semantic-review-v1",
        independent_review_id="review-1",
        independent_context="clean-context-1",
        rationale_zh="两种表述指向同一 EASI-75 应答构念，时间窗临床接近。",
    )
    result = compare_clinical_constructs(left, right, adjudication=receipt)
    assert result.compatible is True
    assert result.time_window_note_zh is not None

    conflicting = right.model_copy(update={"analysis_set": "per_protocol"})
    result = compare_clinical_constructs(left, conflicting, adjudication=receipt)
    assert result.compatible is False
    assert "分析集不一致" in result.reasons


def test_semantic_adjudication_must_bind_the_exact_observation_pair() -> None:
    left = ClinicalConstructObservation.model_validate(
        _observation(observation_id="left")
    )
    right = ClinicalConstructObservation.model_validate(
        _observation(observation_id="right", clinical_construct="EASI 75 responder rate")
    )
    receipt = SemanticAdjudicationReceipt(
        adjudication_id="adj-1",
        observation_ids=("left", "other"),
        decision="compatible",
        model_id="medical-semantic-review-v1",
        independent_review_id="review-1",
        independent_context="clean-context-1",
        rationale_zh="独立复核认为构念一致。",
    )
    with pytest.raises(ClinicalSemanticError, match="绑定"):
        compare_clinical_constructs(left, right, adjudication=receipt)


def test_b_has_exactly_three_neutral_non_ranked_presets() -> None:
    assert len(BUBBLE_PRESETS) == 3
    assert [preset.preset_id for preset in BUBBLE_PRESETS] == [
        "efficacy_overall_safety",
        "efficacy_serious_risk",
        "durability_discontinuation_risk",
    ]
    assert all(
        preset.neutral and not preset.ranking and not preset.composite_score
        for preset in BUBBLE_PRESETS
    )
    assert build_bubble_point(
        BUBBLE_PRESETS[0], x_value=1, y_value=2, size_value=3
    )["rank"] is None
    assert build_bubble_point(
        BUBBLE_PRESETS[0],
        x_value=1,
        y_value=2,
        size_value=3,
        size_state="not_publicly_disclosed",
    ) is None


def test_portal_grouping_splits_semantic_axes_before_cross_trial_charting() -> None:
    from ci_workflow.renderers.portal.report_b import _groups_for_page

    base = {
        "row_id": "row-1",
        "product_id": "product-a",
        "trial_id": "trial-a",
        "display_label_zh": "EASI-75",
        "clinical_concept": "easi75_response",
        "statistical_form_family": "response_rate",
        "statistic_form": "response_rate",
        "unit": "%",
        "population_context": "full_analysis_set",
        "time_window_band": "around_year_1",
        "_domain": "efficacy",
        "renderable": True,
        "numeric_value": 50,
        "semantic_definition": "EASI-75应答者比例",
        "semantic_direction": "higher_is_better",
        "semantic_estimand": "treatment_policy",
        "semantic_denominator": "full_analysis_set",
        "semantic_analysis_set": "full_analysis_set",
        "semantic_analysis_form": "response_rate",
        "semantic_instrument_or_scale": "EASI v1.0",
    }
    second = dict(base, row_id="row-2", trial_id="trial-b", semantic_estimand="hypothetical")

    groups = _groups_for_page("efficacy", [(base, None), (second, None)])

    assert len(groups) == 2
