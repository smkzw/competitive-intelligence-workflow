"""Synthetic field-level regressions for actual publication scope and evidence selection defects."""

import pytest
from test_publications import roles, setup

from ciw.analyze.results import build_results
from ciw.pipeline import build_products
from ciw.verify.publications import _reported_order, extract_publications


@pytest.mark.parametrize("population", ["overall population", "population with eosinophilia"])
def test_polyposis_condition_keeps_all_ncs_observations_in_report_questions(cfg, resolver, ws, population):
    paper, trial, item = setup(ws)
    trial.conditions = ["Chronic Rhinosinusitis With Nasal Polyposis"]
    quote = (
        "NCT12345678: In the " + population + ", the LS mean change in nasal congestion score "
        "from baseline to Week 24 was -1.4 for stapokibart and -0.3 for placebo; "
        "stapokibart minus placebo difference -1.0 (95% CI -1.4 to -0.6)."
    )
    paper["text"] = quote
    item.update(
        endpoint="nasal congestion score", population=population, quote=quote, value=-1.0, ci_lower=-1.4, ci_upper=-0.6
    )
    values = [
        dict(
            item,
            stat_type="ls_mean",
            value=value,
            comparator_label="",
            ci_lower=None,
            ci_upper=None,
            contrast_direction="unknown",
            arm_label=label,
        )
        for label, value in [("stapokibart", -1.4), ("placebo", -0.3)]
    ]
    results, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([*values, item]))
    assert not issues and len(results) == 3
    b = build_results(cfg, {trial.trial_id: trial}, build_products(cfg), results, None)
    assert len(b["observations"]) == 3
    assert sum(len(q["rows"]) for q in b["questions"]) == 2
    assert [c["value"] for q in b["questions"] for c in q["comparisons"]] == [-1.0]


QUOTE = (
    "In the overall population, the LS mean change in score at week 16 in the Drug-X vs placebo groups "
    "was -1.8 vs -0.2 points (LS mean difference, -1.6; 95% CI -1.9 to -1.3); "
    "in the population with marker positivity, the change was -2.0 vs -0.2 points "
    "(LS mean difference, -1.9; 95% CI -2.3 to -1.4)."
)


@pytest.mark.parametrize(
    "population,value", [("overall population", -1.6), ("population with marker positivity", -1.9)]
)
def test_direction_evidence_includes_this_population_and_its_reported_estimate(population, value):
    item = dict(
        stat_type="difference",
        base_stat_type="ls_mean",
        arm_label="Drug-X",
        comparator_label="placebo",
        quote=QUOTE,
        population=population,
        value=value,
    )
    direction, evidence = _reported_order(item)
    assert direction == 1
    assert population in evidence and str(value) in evidence
    assert evidence in QUOTE
    if population != "overall population":
        assert "-1.6" not in evidence


@pytest.mark.parametrize(
    "change",
    [
        {"population": "overall population", "value": -1.9},
        {"population": "population with marker positivity", "value": -1.6},
        {"population": "unreported population", "value": -1.6},
        {"population": "population with marker positivity", "value": -9.9},
        {
            "quote": QUOTE.replace("; in the population", ". In the population"),
            "population": "population with marker positivity",
            "value": -1.9,
        },
    ],
)
def test_direction_does_not_borrow_another_analysis_or_unstated_order(change):
    item = dict(
        stat_type="difference",
        base_stat_type="ls_mean",
        arm_label="Drug-X",
        comparator_label="placebo",
        quote=QUOTE,
        population="overall population",
        value=-1.6,
    )
    item.update(change)
    assert _reported_order(item) == (0, "")


def test_confidence_annotation_before_estimate_keeps_supported_direction(cfg, resolver, ws):
    paper, trial, item = setup(ws)
    quote = (
        "NCT12345678: stapokibart improves nasal polyp score in the overall population "
        "compared with placebo at Week 16 (mean difference [95% CI], -1.2 [-2.3 to -0.1], P = 0.04)."
    )
    paper["text"] = quote
    item.update(
        quote=quote,
        endpoint="nasal polyp score",
        timepoint="Week 16",
        value=-1.2,
        ci_lower=-2.3,
        ci_upper=-0.1,
        p_value="= 0.04",
        contrast_direction="unknown",
        base_stat_type="mean",
    )
    results, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([item]))
    assert not issues and len(results) == 1
    b = build_results(cfg, {trial.trial_id: trial}, build_products(cfg), results, None)
    assert b["questions"][0]["comparisons"][0]["plot_value"] == -1.2
    a = results[0].analyses[0]
    assert "-1.2" in a.direction_evidence and "compared with placebo" in a.direction_order_evidence


def test_subgroup_evidence_and_shared_order_have_separate_literal_anchors(cfg, resolver, ws):
    paper, trial, item = setup(ws)
    quote = QUOTE.replace("Drug-X", "stapokibart")
    paper["text"] = quote
    item.update(
        quote=quote,
        endpoint="score",
        timepoint="Week 16",
        population="population with marker positivity",
        value=-1.9,
        ci_lower=-2.3,
        ci_upper=-1.4,
        contrast_direction="unknown",
    )
    results, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([item]))
    assert not issues and len(results) == 1
    a = results[0].analyses[0]
    assert "-1.9" in a.direction_evidence and "-1.6" not in a.direction_evidence
    assert "population with marker positivity" in a.direction_evidence
    assert "stapokibart vs placebo groups" in a.direction_order_evidence
    assert a.direction_evidence in quote and a.direction_order_evidence in quote


def test_a_later_sentence_with_its_own_explicit_order_can_supply_its_own_direction():
    quote = QUOTE.replace("; in the population", ". In the population").replace(
        "the change was -2.0", "the Drug-X vs placebo groups showed a change of -2.0"
    )
    item = dict(
        stat_type="difference",
        base_stat_type="ls_mean",
        arm_label="Drug-X",
        comparator_label="placebo",
        quote=quote,
        population="population with marker positivity",
        value=-1.9,
    )
    direction, evidence = _reported_order(item)
    assert direction == 1 and "-1.9" in evidence and "-1.6" not in evidence
