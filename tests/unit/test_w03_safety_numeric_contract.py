from __future__ import annotations

import json

import pytest

from ci_workflow.renderers.portal.report_a import SafetyRow
from ci_workflow.renderers.portal.report_b import ReportBPortalError, _project_record
from ci_workflow.reports.b.safety_concepts import (
    classify_safety_concept,
    describe_safety_concept,
)
from ci_workflow.reports.b.safety_denominator_crosswalk import build_atrisk_crosswalk
from ci_workflow.reports.common.numeric_projection import (
    NumericMeasureKind,
    infer_numeric_kind,
    project_numeric,
)


def test_denominator_requires_identity_or_explicit_relationship_and_keeps_integer() -> None:
    rows = json.loads(json.dumps([
        {
            "study_id": "S1", "module": "adverseEventsModule", "group_id": "EG1",
            "title": "Drug X", "period": "Period 1", "stat": "other",
            "measure_object": "participants_at_risk", "analysis_population": "SAF",
            "window": "TP1", "source_version_id": "sv1", "num_at_risk": 10,
            "relationships": [{
                "target_module": "outcomeMeasuresModule",
                "target_group_id": "OG1",
                "relationship_kind": "audited_mapping",
                "mapping_id": "audit-s1-eg1-og1",
            }],
        },
        {
            "study_id": "S1", "module": "adverseEventsModule", "group_id": "EG2",
            "title": "Placebo", "period": "Period 1", "stat": "other",
            "measure_object": "participants_at_risk", "analysis_population": "SAF",
            "window": "TP1", "source_version_id": "sv1", "num_at_risk": 10,
            "relationships": [{
                "target_module": "outcomeMeasuresModule",
                "target_group_id": "OG2",
                "relationship_kind": "source_declared",
                "mapping_id": "ctgov-edge-s1-eg2-og2",
            }],
        },
    ]))
    walk = build_atrisk_crosswalk(rows)
    common = dict(
        study_id="S1", module="outcomeMeasuresModule", stat="other", period="TP1",
        measure_object="participants_at_risk", analysis_population="SAF",
        window="TP1", source_version_id="sv1",
    )
    assert walk.lookup(title="Drug X", group_id="OG1", **common) == 10
    assert isinstance(walk.lookup(title="Drug X", group_id="OG1", **common), int)
    assert walk.lookup(title="Drug X", group_id="OG2", **common) is None
    assert walk.lookup(title="Placebo", group_id="OG1", **common) is None


def test_production_denominator_lookup_fails_closed_without_complete_identity() -> None:
    walk = build_atrisk_crosswalk([{
        "study_id": "S1", "module": "adverseEventsModule", "group_id": "EG1",
        "title": "Drug X", "period": "TP1", "stat": "other",
        "measure_object": "participants_at_risk", "analysis_population": "SAF",
        "window": "TP1", "source_version_id": "sv1", "num_at_risk": 10,
    }])
    assert walk.lookup(stat="other", period="TP1", title="Drug X") is None
    assert walk.lookup(
        stat="other", period="TP1", title="Drug X", study_id="S1",
        module="adverseEventsModule", group_id="EG1",
    ) is None


def test_denominator_does_not_use_equal_n_or_cross_period_as_identity() -> None:
    walk = build_atrisk_crosswalk([
        {"study_id": "S1", "module": "ae", "group_id": "G1", "title": "Drug X",
         "period": "TP1", "stat": "serious", "measure_object": "participants_at_risk",
         "analysis_population": "SAF", "window": "TP1", "source_version_id": "sv1",
         "num_at_risk": 24},
        {"study_id": "S1", "module": "ae", "group_id": "G2", "title": "Placebo",
         "period": "TP2", "stat": "serious", "measure_object": "participants_at_risk",
         "analysis_population": "SAF", "window": "TP2", "source_version_id": "sv1",
         "num_at_risk": 24},
    ])
    assert walk.lookup(
        study_id="S1", module="outcomes", group_id="UNKNOWN", title="Drug X",
        stat="serious", period="TP1", measure_object="participants_at_risk",
        analysis_population="SAF", window="TP1", source_version_id="sv1",
    ) is None


@pytest.mark.parametrize(
    ("title", "key", "polarity", "grades"),
    [
        ("Non-serious TEAEs", "non_serious_teae", "negative_seriousness", ()),
        ("Participants without SAEs", "absence_sae", "negative_presence", ()),
        ("Grade 4 adverse events", "grade_specific", "affirmed", (4,)),
        ("Grade 1 or 3 adverse events", "grade_specific", "affirmed", (1, 3)),
    ],
)
def test_safety_concept_preserves_negation_and_grade_sets(title, key, polarity, grades) -> None:
    concept = describe_safety_concept(title)
    assert classify_safety_concept(title) == key
    assert concept.polarity == polarity
    assert concept.grade_set == grades


def test_composite_concept_has_no_automatic_other_denominator() -> None:
    concept = describe_safety_concept("TEAEs, SAEs and events leading to discontinuation")
    assert concept.key == "composite_ae"
    assert concept.at_risk_stat is None
    assert concept.children == ("any_teae", "any_sae", "discontinuation_ae")


def test_a_safety_row_roundtrips_complete_concept_semantics() -> None:
    row = SafetyRow(
        row_id="semantic", product_id="p1", category="安全性", term="Participants without SAEs",
        term_key="absence_sae", polarity="negative_presence", grade_set=(),
        seriousness="serious", teae=False, relatedness="unspecified",
        parent=None, children=(), count_basis="participants", at_risk_stat="serious",
        value=0, numerator=0, denominator=40, unit="人", time_window="TP1",
    )
    payload = json.loads(row.model_dump_json())
    assert payload["polarity"] == "negative_presence"
    assert payload["seriousness"] == "serious"
    assert payload["teae"] is False
    assert payload["count_basis"] == "participants"


def test_typed_numeric_projection_separates_people_events_rates_and_estimates() -> None:
    people = project_numeric(
        value=12, unit="人", kind=NumericMeasureKind.PARTICIPANT_PROPORTION,
        numerator=12, denominator=40, window="TP1", estimand="SAF",
    )
    assert people.renderable and people.plot_value == 30 and people.plot_unit == "%"
    assert not project_numeric(
        value=12, unit="人", kind=NumericMeasureKind.PARTICIPANT_PROPORTION,
        window="TP1", estimand="SAF",
    ).renderable
    events = project_numeric(
        value=70, unit="次", kind=NumericMeasureKind.EVENT_COUNT,
        numerator=70, denominator=40, window="TP1", estimand="SAF",
    )
    assert events.renderable and events.plot_value == 70 and events.plot_unit == "次"
    assert project_numeric(
        value=1.8, unit="次/100人年", kind=NumericMeasureKind.PERSON_TIME_RATE,
        window="随访期", estimand="暴露调整率",
    ).facet_key != events.facet_key
    estimate = project_numeric(
        value=-3.2, unit="分", kind=NumericMeasureKind.ADJUSTED_ESTIMATE,
        direction="越低越好", window="第12周", estimand="LS mean difference",
    )
    assert estimate.plot_value == -3.2


def test_nonpercent_efficacy_is_not_forced_into_participant_proportion() -> None:
    score_kind = infer_numeric_kind(unit="分", domain="efficacy")
    assert score_kind is NumericMeasureKind.CONTINUOUS_MEASURE
    score = project_numeric(
        value=-4, unit="分", kind=score_kind, window="第24周", estimand="评分变化"
    )
    assert score.renderable and score.plot_value == -4 and score.plot_unit == "分"
    assert (
        infer_numeric_kind(unit="%", domain="efficacy")
        is NumericMeasureKind.PARTICIPANT_PROPORTION
    )
    assert (
        infer_numeric_kind(unit="", domain="efficacy")
        is NumericMeasureKind.PARTICIPANT_PROPORTION
    )


def test_n_le_n_applies_only_to_participant_proportion() -> None:
    with pytest.raises(ValueError):
        project_numeric(
            value=50, unit="人", kind=NumericMeasureKind.PARTICIPANT_PROPORTION,
            numerator=50, denominator=40,
        )
    row = SafetyRow(
        row_id="events", product_id="p1", category="不良事件（登记）", term="Events",
        value=70, numerator=70, denominator=40, unit="次", time_window="TP1",
        measure_object="event_count",
    )
    assert row.numerator == 70


def test_b_matrix_rejects_arbitrary_single_arm_absolute_mapping() -> None:
    with pytest.raises(ReportBPortalError, match="TypedMatrixView"):
        _project_record(
            {"row_id": "fake", "point": {"x_value": 42, "y_value": 7, "size": 30}},
            domain="matrix", names={}, trial_names={}, fallback="fake",
        )
