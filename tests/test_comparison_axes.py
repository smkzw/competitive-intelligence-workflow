"""Synthetic shared-axis contracts, not real clinical acceptance."""
import json
import re
from copy import deepcopy

import pytest

from ciw.analyze.clinical_families import project_clinical_families
from ciw.analyze.comparison_axes import project_comparison_axes
from ciw.analyze.results import build_results
from ciw.config import ConceptCfg
from ciw.models import GroupValue, Locator, OutcomeResult, TimePoint, Trial
from ciw.normalize.comparison_axes import context_catalog, context_id
from ciw.verify.comparison_axes import check_axis, enrich_comparison_axes
from ciw.verify.llm import FakeBackend


def inputs(cfg):
    cfg = cfg.model_copy(deep=True)
    results, trials = [], {}
    for i in range(2):
        title = "Part B: Change From Baseline in Hemoglobin Level at Each Specified Time Point"
        definition = ("Mean hemoglobin change from Week 0. Baseline is the last non-missing value before first dose."
                      if i == 0 else "Hemoglobin change from Week 0; baseline was last non-missing value "
                      "before first dose.")
        population = "Part B-FAS: participants with available data after at least one dose."
        trial = Trial(trial_id=f"T{i}", registry="ctgov", phase="III", acronym=f"Trial{i}",
            title="Without recent transfusion." if i == 0 else "With recent transfusion.",
            locator=Locator(source_id=f"S{i}"))
        trials[trial.trial_id] = trial
        for week in (27, 28):
            results.append(OutcomeResult(result_id=f"r{i}-{week}", trial_id=trial.trial_id, outcome_index=0,
                type="PRIMARY", title=title, description=definition, population=population,
                domain="efficacy", concept_id=f"source-{i}", measure_kind="mean",
                unit="grams per deciliter" if i == 0 else "g/dL",
                time=TimePoint(raw=f"Week {week}", key=f"W{week}", label=f"第{week}周", weeks=week),
                groups=[GroupValue(group_id="drug", title="Drug", role="experimental", value=i + week / 10, n=20+i)],
                locator=Locator(source_id=f"S{i}")))
    cfg.concepts = [ConceptCfg(id=f"source-{i}", label="血红蛋白", patterns=[re.escape(results[0].title)],
        source_definition=results[2*i].description, origin="source_index", direction="higher_better") for i in range(2)]
    family = dict(family_id="family", family_label="血红蛋白变化", member_ids=["source-0", "source-1"])
    return cfg, results, trials, [family]


def item_for(results, trials):
    unique = {context_id(r): r for r in results}
    return dict(axis_anchor=min(unique), axis_label="B期血红蛋白较基线变化", member_ids=sorted(unique),
        member_quotes={cid:r.description for cid,r in unique.items()}, analysis_set="FAS",
        analysis_quotes={cid:r.population for cid,r in unique.items()},
        baseline_quotes={cid:r.description for cid,r in unique.items()},
        stratum_labels={cid:"无近期输血" if r.trial_id == "T0" else "近期输血" for cid,r in unique.items()},
        stratum_quotes={cid:trials[r.trial_id].title for cid,r in unique.items()}, quote=results[0].description)


def roles_for(items):
    calls = []
    def answer(*args):
        calls.append(True)
        return json.dumps(dict(items=items), ensure_ascii=False)
    return {"extractor_a":FakeBackend("deepseek", "a", answer),
            "verifier":FakeBackend("glm", "b", answer)}, calls


def test_two_role_axis_joins_same_time_rows_and_longitudinal_preserving_strata_and_original_units(cfg, ws):
    cfg, results, trials, families = inputs(cfg)
    before = [r.model_dump() for r in results]
    roles, calls = roles_for([item_for(results, trials)])
    snapshot, issues = enrich_comparison_axes(ws, cfg, results, trials, families, roles)
    assert not issues and len(calls) == 2 and len(snapshot["groups"]) == 1
    body = project_clinical_families(build_results(cfg, trials, {}, results, None), families)
    previous = deepcopy(body)
    projected = project_comparison_axes(body, snapshot["groups"], results)
    q, = projected["questions"]
    assert len(q["frames"]) == 2 and all(f["trial_ids"] == ["T0", "T1"] for f in q["frames"])
    assert {f["time_key"] for f in q["frames"]} == {"W27", "W28"}
    assert all(f["units"] == ["g/dL"] for f in q["frames"])
    rows = [r for f in q["frames"] for r in f["rows"]]
    assert {r["unit"] for r in rows} == {"grams per deciliter", "g/dL"}
    assert {r["stratum_label"] for r in rows} == {"无近期输血", "近期输血"}
    assert sorted(r["value"] for r in rows) == [2.7, 2.8, 3.7, 3.8]
    chart, = projected["longitudinal"]
    assert chart["unit"] == "g/dL" and len(chart["lines"]) == 2
    assert {line["trial_id"] for line in chart["lines"]} == {"T0", "T1"}
    assert all(len(line["points"]) == 2 for line in chart["lines"])
    assert [r.model_dump() for r in results] == before and body == previous
    assert enrich_comparison_axes(ws, cfg, results, trials, families, roles)[0]["groups"] == snapshot["groups"]
    assert len(calls) == 2


@pytest.mark.parametrize("defect", ["quote", "analysis", "baseline", "stratum", "foreign", "overlap"])
def test_bad_axes_never_replace_source_frames(cfg, ws, defect):
    cfg, results, trials, families = inputs(cfg)
    item = item_for(results, trials)
    cid = item["member_ids"][0]
    if defect == "quote":
        item["member_quotes"][cid] = "Invented measurement"
    elif defect == "analysis":
        item["analysis_set"] = "ITT"
    elif defect == "baseline":
        item["baseline_quotes"][cid] = ""
    elif defect == "stratum":
        item["stratum_quotes"][cid] = "Invented population"
    elif defect == "foreign":
        item["member_ids"][0] = "foreign"
    items = [item, {**item, "axis_label": "B期血红蛋白测量"}] if defect == "overlap" else [item]
    roles, _ = roles_for(items)
    snapshot, issues = enrich_comparison_axes(ws, cfg, results, trials, families, roles)
    assert issues and not snapshot["groups"]
    retained, retained_issues = enrich_comparison_axes(ws, cfg, results, trials, families)
    assert retained_issues == issues and not retained["groups"]
    body = project_clinical_families(build_results(cfg, trials, {}, results, None), families)
    assert project_comparison_axes(body, snapshot["groups"], results) == body


@pytest.mark.parametrize("difference", ["unit", "statistic", "direction", "threshold", "period", "missing_population",
                                        "missing_analysis"])
def test_deterministic_guards_keep_known_conflicts_or_missing_context_separate(cfg, difference):
    cfg, results, trials, families = inputs(cfg)
    if difference == "unit":
        results[2].unit = "g/L"
    elif difference == "statistic":
        results[2].measure_kind = "ls_mean"
    elif difference == "direction":
        cfg.concepts[1].direction = "lower_better"
    elif difference == "threshold":
        results[2].title += " >2"
    elif difference == "period":
        results[2].title = results[2].title.replace("Part B", "Part A")
    elif difference == "missing_analysis":
        results[2].population = "Participants with available data."
    else:
        results[2].population = ""
    item = item_for([results[0], results[2]], trials)
    assert not check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]


def test_changed_material_cannot_reuse_old_axis_and_release_snapshot_can_restore_stage(cfg, ws):
    cfg, results, trials, families = inputs(cfg)
    roles, calls = roles_for([item_for(results, trials)])
    snapshot, _ = enrich_comparison_axes(ws, cfg, results, trials, families, roles)
    (ws.root / "stages/research-comparison-axes.json").unlink()
    restored, _ = enrich_comparison_axes(ws, cfg, results, trials, families, previous=snapshot)
    assert restored["groups"] == snapshot["groups"] and len(calls) == 2
    for row in results[2:]:
        row.description += " A changed baseline or estimation strategy."
    changed, _ = enrich_comparison_axes(ws, cfg, results, trials, families, previous=snapshot)
    assert not changed["groups"] and len(calls) == 2


def test_exact_time_and_interval_never_collapse_even_with_same_verified_axis(cfg, ws):
    cfg, results, trials, families = inputs(cfg)
    roles, _ = roles_for([item_for(results, trials)])
    snapshot, _ = enrich_comparison_axes(ws, cfg, results, trials, families, roles)
    results[2].time = TimePoint(raw="Through Week 27", key="W27_window*", label="至第27周", weeks=27)
    body = project_clinical_families(build_results(cfg, trials, {}, results, None), families)
    q, = project_comparison_axes(body, snapshot["groups"], results)["questions"]
    assert len(q["frames"]) == 3
    assert all(f["trial_ids"] != ["T0", "T1"] for f in q["frames"] if f["time_key"] != "W28")


def test_source_context_transport_failure_remains_pending_and_recovers_without_empty_success(cfg, ws):
    cfg, results, trials, families = inputs(cfg)
    def fail(*args):
        raise TimeoutError("synthetic source normalization timeout")
    roles, calls = roles_for([item_for(results, trials)])
    failed, issues = enrich_comparison_axes(ws, cfg, results, trials, families,
        {**roles, "extractor_a": FakeBackend("deepseek", "a", fail)})
    assert issues and failed["status"] == "partial" and not failed["groups"]
    assert len(failed["unmatched_ids"]) == 2
    restored, issues = enrich_comparison_axes(ws, cfg, results, trials, families, roles)
    assert not issues and len(restored["groups"]) == 1 and len(calls) == 2


@pytest.mark.parametrize("label", ["available data", "Participants with available data at each time point", "FAS"])
def test_availability_phrase_cannot_hide_missing_analysis_set(cfg, label):
    cfg, results, trials, families = inputs(cfg)
    results[0].population = "Participants with available data at each time point."
    results[2].population = "Full analysis set participants with available data at each time point."
    item = item_for([results[0], results[2]], trials)
    item["analysis_set"] = label
    assert not check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]


def test_named_analysis_aliases_match_without_turning_modified_itt_or_pp_into_itt(cfg):
    cfg, results, trials, families = inputs(cfg)
    results[0].population = "Part B full analysis set participants with available data."
    item = item_for([results[0], results[2]], trials)
    assert check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]
    results[0].population = "Modified intention to treat population."
    results[2].population = "Intention to treat population."
    item = item_for([results[0], results[2]], trials)
    item["analysis_set"] = "ITT"
    assert not check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]

    results[0].population = "Modified ITT population."
    item = item_for([results[0], results[2]], trials)
    item["analysis_set"] = "ITT"
    assert not check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]
    results[0].population = "Per protocol population."
    item = item_for([results[0], results[2]], trials)
    item["analysis_set"] = "ITT"
    assert not check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]


@pytest.mark.parametrize("alias", ["mITT", "m-ITT", "m ITT", "m–ITT", "modified-ITT", "modified (ITT)",
                                    "modified intention-to-treat", "modified-intention-to-treat"])
def test_modified_analysis_grammar_keeps_separator_variants_distinct_from_plain_itt(cfg, alias):
    cfg, results, trials, families = inputs(cfg)
    results[0].population = alias + " population."
    results[2].population = "ITT population."
    item = item_for([results[0], results[2]], trials)
    item["analysis_set"] = "ITT"
    assert not check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]
    results[2].population = "modified intention to treat population."
    item = item_for([results[0], results[2]], trials)
    item["analysis_set"] = "mITT"
    assert check_axis(item, context_catalog(results, trials, families, cfg.concepts))[0]

