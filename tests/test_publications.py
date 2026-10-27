"""Synthetic publication cases exercise production functions; not clinical evidence."""

import json

from ciw.analyze.results import build_results
from ciw.models import Arm, Locator, Trial
from ciw.pipeline import build_products
from ciw.verify.llm import FakeBackend
from ciw.verify.publications import extract_publications

TEXT = (
    "NCT12345678: In the overall population at Week 24, least squares mean change in nasal polyp score "
    "was -2.6 with stapokibart and -0.4 with placebo; stapokibart minus placebo difference -2.5 "
    "(95% CI -2.9 to -2.1). The same contrast was reported for the eosinophilic population."
)


def setup(ws):
    source = ws.record_source(
        kind="europepmc",
        url="https://example.com/paper",
        ext="json",
        data=json.dumps({"resultList": {"result": [{"abstractText": TEXT}]}}).encode(),
    )
    trial = Trial(
        trial_id="NCT12345678",
        registry="ctgov",
        phase="III",
        phase_rank=4,
        product_ids=["stapokibart"],
        locator=Locator(source_id=source.source_id),
        arms=[
            Arm(arm_id="A", label="CM310", role="experimental", product_ids=["stapokibart"]),
            Arm(arm_id="B", label="Placebo", role="placebo"),
        ],
    )
    paper = dict(
        source_id=source.source_id,
        source_sha=source.sha256,
        registry_ids=[trial.trial_id],
        paper_id="123",
        path="$.resultList.result[0].abstractText",
        text=TEXT,
        excluded_type=False,
    )
    item = dict(
        registry_id=trial.trial_id,
        arm_label="stapokibart",
        comparator_label="placebo",
        endpoint="least squares mean change in nasal polyp score",
        timepoint="Week 24",
        population="overall population",
        stat_type="difference",
        base_stat_type="ls_mean",
        contrast_direction="arm_minus_comparator",
        value=-2.5,
        ci_lower=-2.9,
        ci_upper=-2.1,
        outcome_type="PRIMARY",
        quote=TEXT,
    )
    return paper, trial, item


def roles(items):
    return {
        k: FakeBackend(f, f, lambda *a: json.dumps({"items": items}))
        for k, f in (("extractor_a", "deepseek"), ("extractor_b", "qwen"), ("arbiter", "glm"))
    }


def test_adjusted_contrast_with_no_arm_values_is_plotted_without_fabricated_zero(cfg, resolver, ws):
    paper, trial, item = setup(ws)
    results, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([item]))
    assert not issues and len(results) == 1
    assert all(g.value is None and g.n is None for g in results[0].groups)
    b = build_results(cfg, {trial.trial_id: trial}, build_products(cfg), results, None)
    q = b["questions"][0]
    c = q["comparisons"][0]
    assert q["rows"] == [] and q["trial_ids"] == [trial.trial_id]
    assert (c["value"], c["plot_value"], c["plot_lower"], c["plot_upper"]) == (-2.5, -2.5, -2.9, -2.1)
    assert c["source_kind"] == "publication" and c["status"] == "dual_agreed" and c["url"].endswith("/123/")


def test_population_statistic_and_registry_values_remain_distinct(cfg, resolver, ws):
    paper, trial, item = setup(ws)
    items = [
        dict(
            item,
            stat_type="ls_mean",
            value=-2.6,
            ci_lower=None,
            ci_upper=None,
            comparator_label="",
            contrast_direction="unknown",
        ),
        dict(item, population="eosinophilic population"),
    ]
    results, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles(items))
    assert not issues and len(results) == 2
    assert {r.subgroup for r in results} == {"overall population", "eosinophilic population"}
    b = build_results(cfg, {trial.trial_id: trial}, build_products(cfg), results, None)
    assert len(b["questions"]) == 2 and sum(len(q["rows"]) for q in b["questions"]) == 1


def test_unlinked_trial_ambiguous_arm_and_unknown_direction_do_not_create_plotted_comparison(cfg, resolver, ws):
    paper, trial, item = setup(ws)
    bad = dict(item, arm_label="unmapped treatment")
    results, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([bad]))
    assert results == [] and issues[0]["kind"] == "publication_unbound"
    results, issues = extract_publications(
        ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([dict(item, contrast_direction="unknown")])
    )
    b = build_results(cfg, {trial.trial_id: trial}, build_products(cfg), results, None)
    assert b["questions"][0]["comparisons"][0]["plot_value"] is None
    results, issues = extract_publications(
        ws, cfg, [dict(paper, registry_ids=["NCT99999999"])], {trial.trial_id: trial}, resolver, roles([item])
    )
    assert results == []


def test_model_disabled_and_excluded_papers_are_not_treated_as_extracted(cfg, resolver, ws):
    paper, trial, item = setup(ws)
    results, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, None)
    assert not results and issues[0]["kind"] == "publication_not_extracted"
    results, issues = extract_publications(
        ws, cfg, [dict(paper, excluded_type=True)], {trial.trial_id: trial}, resolver, roles([item])
    )
    assert results == issues == []


def test_publication_audit_reads_original_abstract_and_detects_numeric_tampering(cfg, resolver, ws):
    from ciw.audit import _publication

    paper, trial, item = setup(ws)
    results, _ = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([item]))
    original = json.loads(ws.read_source(paper["source_id"]))
    sample = dict(
        kind="analysis",
        result_id=results[0].result_id,
        source_id=paper["source_id"],
        path=paper["path"],
        value=-2.5,
        ci=(-2.9, -2.1),
    )
    assert _publication(sample, original, [r.model_dump() for r in results])[0]
    assert not _publication(dict(sample, value=-2.6), original, [r.model_dump() for r in results])[0]


def test_different_physical_units_never_share_one_numeric_axis(cfg, resolver, ws):
    paper, trial, item = setup(ws)
    item["quote"] += " Units in separate analyses: g/dL and g/L."
    paper["text"] = item["quote"]
    items = [dict(item, unit="g/dL"), dict(item, unit="g/L")]
    results, _ = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([items[0]]))
    other, _ = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, roles([items[1]]))
    b = build_results(cfg, {trial.trial_id: trial}, build_products(cfg), results + other, None)
    assert len(b["questions"]) == 2
    assert {tuple(q["units"]) for q in b["questions"]} == {("g/dL",), ("g/L",)}
