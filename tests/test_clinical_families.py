"""Clinical family is not numeric eligibility; stub-source contracts, no live model acceptance."""
import json
import re
from copy import deepcopy

import pytest

from ciw.analyze.clinical_families import project_clinical_families
from ciw.analyze.results import build_results
from ciw.config import ConceptCfg
from ciw.models import GroupValue, Locator, OutcomeResult, TimePoint, Trial
from ciw.verify.endpoint_families import enrich_endpoint_families
from ciw.verify.llm import FakeBackend


def inputs(cfg):
    cfg = cfg.model_copy(deep=True)
    titles = ["Percentage of Participants With Clinical Remission at Week 24",
              "Proportion of Patients Achieving Clinical Remission at Week 24"]
    rows = [OutcomeResult(result_id="r" + str(i), trial_id="T" + str(i), outcome_index=0, type="PRIMARY",
        title=title, description="Clinical remission definition.", population="All randomized participants",
        concept_id="source-" + str(i), domain="efficacy", measure_kind="proportion", unit="Percent",
        time=TimePoint(raw="Week 24", key="W24", label="第24周", weeks=24),
        groups=[GroupValue(group_id="g", title="Drug " + str(i), role="experimental", value=20 + i, n=10)],
        locator=Locator(source_id="S" + str(i))) for i, title in enumerate(titles)]
    cfg.concepts = [ConceptCfg(id=r.concept_id, label="来源应答", patterns=[re.escape(r.title)],
        source_definition=r.description, origin="source_index", direction="higher_better") for r in rows]
    trials = {r.trial_id: Trial(trial_id=r.trial_id, registry="ctgov", relevance="core",
                               locator=Locator(source_id=r.locator.source_id)) for r in rows}
    return cfg, rows, trials


def group_for(rows):
    quotes = {r.concept_id: r.title for r in rows}
    return dict(family_anchor=min(quotes), family_label="临床缓解", member_ids=list(quotes),
                member_quotes=quotes, quote=rows[0].title)


def models(groups):
    calls = []
    def response(system, user):
        calls.append((system, user))
        return json.dumps(dict(items=groups))
    return {"extractor_a": FakeBackend("deepseek", "primary", response),
            "verifier": FakeBackend("glm", "checker", response)}, calls


def test_quoted_aliases_form_one_question_with_two_studies_without_altering_facts(cfg, ws):
    cfg, rows, trials = inputs(cfg)
    before = [r.model_dump() for r in rows]
    roles, calls = models([group_for(rows)])
    snapshot, issues = enrich_endpoint_families(ws, cfg, rows, roles)
    assert not issues and len(calls) == 2
    old = build_results(cfg, trials, {}, rows, None)
    assert len(old["questions"]) == 2
    joined = project_clinical_families(old, snapshot["groups"])
    q, = joined["questions"]
    assert q["trial_ids"] == ["T0", "T1"] and len(q["frames"]) == 1
    assert [r["value"] for r in q["frames"][0]["rows"]] == [20, 21]
    assert {r["result_id"] for r in q["frames"][0]["rows"]} == {"r0", "r1"}
    assert [r.model_dump() for r in rows] == before
    assert len(old["questions"]) == 2
    second, issues = enrich_endpoint_families(ws, cfg, rows, roles)
    assert not issues and second["groups"] == snapshot["groups"] and len(calls) == 2
    assert enrich_endpoint_families(ws, cfg, rows, roles=None)[0]["groups"] == snapshot["groups"]


@pytest.mark.parametrize("difference", ["time", "unit", "population", "definition", "measure", "category", "change",
                                       "unknown_population", "unknown_definition", "upper_window"])
def test_related_question_does_not_merge_incompatible_numeric_frames(cfg, ws, difference):
    cfg, rows, trials = inputs(cfg)
    if difference == "time":
        rows[1].time = TimePoint(raw="Week 12", key="W12", label="第12周", weeks=12)
    elif difference == "unit":
        rows[1].unit = "Proportion of participants"
    elif difference == "population":
        rows[1].population = "Induction responders with nonresponder imputation"
    elif difference == "definition":
        rows[1].description = "Other clinical remission definition requiring afebrile status."
    elif difference == "measure":
        rows[1].measure_kind = "mean"
    elif difference == "category":
        rows[1].category_title = "Sensitivity population"
    elif difference == "unknown_population":
        rows[0].population = rows[1].population = ""
    elif difference == "unknown_definition":
        rows[0].description = rows[1].description = ""
    elif difference == "upper_window":
        rows[1].time = TimePoint(raw="Up to Week 24", key="W24_window*", label="至第24周", weeks=24)
    else:
        rows[1].title = "Percent Change From Baseline in Clinical Remission at Week 24"
    roles, _ = models([group_for(rows)])
    snapshot, issues = enrich_endpoint_families(ws, cfg, rows, roles)
    assert not issues
    joined = project_clinical_families(build_results(cfg, trials, {}, rows, None), snapshot["groups"])
    q, = joined["questions"]
    assert q["trial_ids"] == ["T0", "T1"] and len(q["frames"]) == 2
    assert sorted(r["value"] for frame in q["frames"] for r in frame["rows"]) == [20, 21]


@pytest.mark.parametrize("bad", ["quote", "foreign", "duplicate", "overlap"])
def test_unconfirmed_or_overlapping_memberships_do_not_hide_original_questions(cfg, ws, bad):
    cfg, rows, trials = inputs(cfg)
    group = group_for(rows)
    if bad == "quote":
        group["member_quotes"][rows[1].concept_id] = "Invented source sentence"
    elif bad == "foreign":
        group["member_ids"].append("foreign")
        group["member_quotes"]["foreign"] = group["quote"]
    elif bad == "duplicate":
        group["member_ids"].append(rows[0].concept_id)
    groups = [group]
    if bad == "overlap":
        groups.append({**group, "family_label": "临床缓解研究"})
    roles, _ = models(groups)
    snapshot, issues = enrich_endpoint_families(ws, cfg, rows, roles)
    assert issues and snapshot["groups"] == []
    old = build_results(cfg, trials, {}, rows, None)
    assert project_clinical_families(old, snapshot["groups"])["questions"] == old["questions"]


def test_changed_source_definition_cannot_reuse_old_membership_without_review(cfg, ws):
    cfg, rows, trials = inputs(cfg)
    roles, _ = models([group_for(rows)])
    enrich_endpoint_families(ws, cfg, rows, roles)
    rows[1].description = "The source definition has changed."
    snapshot, _ = enrich_endpoint_families(ws, cfg, rows, roles=None)
    assert snapshot["groups"] == []


def test_old_source_index_stage_is_not_rewritten_by_question_grouping(cfg, ws):
    cfg, rows, trials = inputs(cfg)
    source_index = dict(items={"existing-descriptor": dict(label="已有指标")})
    ws.write_stage("research-endpoint-index", source_index)
    original = deepcopy(ws.read_stage("research-endpoint-index"))
    roles, _ = models([group_for(rows)])
    enrich_endpoint_families(ws, cfg, rows, roles)
    assert ws.read_stage("research-endpoint-index") == original


def test_report_supplement_can_reuse_release_membership_after_stage_loss(cfg, ws):
    cfg, rows, trials = inputs(cfg)
    roles, calls = models([group_for(rows)])
    previous, _ = enrich_endpoint_families(ws, cfg, rows, roles)
    (ws.root / "stages/research-endpoint-families.json").unlink()
    recovered, issues = enrich_endpoint_families(ws, cfg, rows, roles=None, previous=previous)
    assert not issues and recovered["groups"] == previous["groups"] and len(calls) == 2


@pytest.mark.parametrize("left,right", [
    ("Assessment (GPPGA) Total Score of 0 or 1", "Assessment (GPPGA) Pustulation Subscore of 0"),
    ("Assessment (GPPGA) Pustulation Subscore", "Assessment (GPPGA) Erythema Subscore"),
    ("Participants Achieving Clinical Remission", "Occurrence of at Least One GPP Flare"),
    ("Dermatology Life Quality Index (DLQI)", "Short Form Health Survey (SF-36)"),
    ("Short Form Health Survey (SF-36) Mental health subscore",
     "Short Form Health Survey (SF-36) Physical health subscore"),
    ("Short Form Health Survey (SF-36) Version 1 score", "Short Form Health Survey (SF-36) Version 2 score"),
    ("Dermatology Life Quality Index (DLQI)", "Short Form Health Status Survey Version 2 (SF-36 V2) Score"),
])
def test_two_models_agreeing_does_not_override_structural_endpoint_differences(cfg, ws, left, right):
    cfg, rows, trials = inputs(cfg)
    for row, concept, title in zip(rows, cfg.concepts, [left, right], strict=True):
        row.title, row.description = title, "Source endpoint definition."
        concept.patterns, concept.source_definition = [re.escape(title)], row.description
    group = {**group_for(rows), "family_label": "临床结果"}
    roles, _ = models([group])
    snapshot, issues = enrich_endpoint_families(ws, cfg, rows, roles)
    assert issues and snapshot["groups"] == []
    original = build_results(cfg, trials, {}, rows, None)
    assert len(project_clinical_families(original, snapshot["groups"])["questions"]) == 2


def test_structural_identity_keeps_punctuation_and_explicit_version_aliases():
    from ciw.verify.endpoint_families import _structural_compatibility
    for titles in [
        ["Assessment (GPPGA) Pustulation Sub-score", "Assessment (GPPGA) Pustulation Subscore"],
        ["Short Form Health Survey Version 2 (SF-36) Score", "Short Form Health Survey (SF-36 V2) Score"],
    ]:
        assert _structural_compatibility([{"title": title} for title in titles]) == (True, "")
