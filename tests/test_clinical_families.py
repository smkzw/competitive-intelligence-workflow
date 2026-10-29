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


def test_added_source_only_classifies_new_members_without_rearranging_verified_family(cfg, ws):
    cfg, rows, trials = inputs(cfg)
    roles, _ = models([group_for(rows)])
    original, _ = enrich_endpoint_families(ws, cfg, rows, roles)
    new = rows[0].model_copy(deep=True, update={"result_id": "new", "trial_id": "T2", "concept_id": "source-2"})
    new.title = "Proportion of Individuals Achieving Clinical Remission at Week 24"
    cfg.concepts.append(ConceptCfg(id=new.concept_id, label="临床缓解", patterns=[re.escape(new.title)],
        source_definition=new.description, origin="source_index", direction="higher_better"))
    additions, calls = models([group_for([new])])
    current, issues = enrich_endpoint_families(ws, cfg, [*rows, new], additions)
    assert not issues and len(calls) == 2
    group, = current["groups"]
    assert set(group["member_ids"]) == {"source-0", "source-1", "source-2"}
    assert {cid:group["member_quotes"][cid] for cid in original["groups"][0]["member_ids"]} == (
        original["groups"][0]["member_quotes"])
    assert "Concept:source-2" in calls[0][1] and "Concept:source-0" not in calls[0][1].split("<<<", 1)[1]


def test_new_model_cannot_reassign_or_split_retained_members_when_new_sources_arrive(cfg, ws):
    cfg, rows, _ = inputs(cfg)
    roles, _ = models([group_for(rows)])
    original, _ = enrich_endpoint_families(ws, cfg, rows, roles)
    new = rows[0].model_copy(deep=True, update={"result_id": "new", "concept_id": "source-2"})
    cfg.concepts.append(ConceptCfg(id=new.concept_id, label="临床缓解", patterns=[re.escape(new.title)],
        source_definition=new.description, origin="source_index"))
    reassign, _ = models([group_for([rows[0]])])
    current, issues = enrich_endpoint_families(ws, cfg, [*rows, new], reassign)
    assert issues and current["groups"] == original["groups"]


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


def test_failed_review_batch_reuses_completed_extraction_and_other_batches(cfg, ws):
    from ciw.config import ConceptCfg
    from ciw.verify.llm import CachedBackend

    cfg, seed, _ = inputs(cfg)
    rows = []
    for i in range(24):
        row = seed[i % 2].model_copy(deep=True)
        row.result_id, row.concept_id = f"r{i}", f"source-{i:02}"
        rows.append(row)
    cfg.concepts = [ConceptCfg(id=r.concept_id, label="临床缓解", patterns=[re.escape(r.title)],
                              source_definition=r.description, origin="source_index") for r in rows]
    groups = [group_for(rows[i:i + 2]) for i in range(0, len(rows), 2)]
    calls = {"extract": 0, "review": 0}
    seen = []

    def extract(*_):
        calls["extract"] += 1
        return json.dumps({"items": groups})

    def review(system, user):
        calls["review"] += 1
        source = user.split("原文：\n<<<\n", 1)[1].split("\n>>>", 1)[0]
        seen.append(source)
        assert source.count("Concept:") <= 10
        if calls["review"] == 2:
            raise TimeoutError("synthetic upstream timeout")
        candidates = json.JSONDecoder().raw_decode(user.split("待核候选（仅供查错，不是来源）：\n", 1)[1])[0]
        return json.dumps({"items": candidates})

    roles = {"extractor_a": CachedBackend(FakeBackend("deepseek", "a", extract), ws),
             "verifier": CachedBackend(FakeBackend("glm", "b", review), ws)}
    partial, issues = enrich_endpoint_families(ws, cfg, rows, roles)
    assert len(partial["groups"]) == 7 and partial["status"] == "partial"
    assert partial["checked_catalog"] is None
    assert any(i["kind"] == "endpoint_family_batch_failed" for i in issues)
    complete, issues = enrich_endpoint_families(ws, cfg, rows, roles)
    assert not issues and len(complete["groups"]) == 12
    assert calls == {"extract": 1, "review": 4}
    assert {cid for text in seen for cid in re.findall(r"Concept:(\S+)", text)} == {r.concept_id for r in rows}


def test_review_batches_keep_whole_proposed_groups_and_cover_primary_omissions(cfg):
    from ciw.verify.crosscheck import ExtractionTask
    from ciw.verify.endpoint_families import ClinicalFamilyItem, _review_batches

    catalog = {str(i): dict(title=f"Endpoint {i}", definition="Source") for i in range(25)}
    task = ExtractionTask("t", "s", "full", "group", ClinicalFamilyItem, (), ())
    candidate = dict(member_ids=[str(i) for i in range(12)])
    batches = list(_review_batches(task, [candidate], catalog))
    assert batches[0][1] == [candidate]  # a proposed family is never silently split
    texts = [batch.source_text for batch, _ in batches]
    assert {cid for text in texts for cid in re.findall(r"Concept:(\S+)", text)} == set(catalog)
    assert sum(text.count("Concept:") for text in texts) == 25


@pytest.mark.parametrize("case,adopt", [("guard", True), ("unconfirmed", False), ("stale", False),
                                        ("conflict", False), ("no_receipt", False)])
def test_retained_family_guard_recheck_requires_current_confirmed_item(cfg, ws, case, adopt):
    cfg, rows, _ = inputs(cfg)
    snapshot, _ = enrich_endpoint_families(ws, cfg, rows)
    item = group_for(rows)
    note = "核对结果未通过来源校验：旧比较符规则"
    if case == "unconfirmed":
        note = "主抽取条目未被核对者确认"
    calls = [dict(role="extract", family="deepseek"),
             dict(role="verify", family="glm", model="checker",
                  response_id=None if case == "no_receipt" else "fake-response")]
    ws.save_verification("family:retained", "needs_review", dict(item=item, calls=calls, review_note=note))
    if case == "stale":
        rows[0].description = "New scientific definition"
    if case == "conflict":
        ws.save_verification("family:conflict", "needs_review", dict(
            item={**item, "family_label": "另一个问题"}, calls=calls, review_note=note))
    payload = [item] if case != "conflict" else [item, {**item, "family_label": "另一个问题"}]
    with ws.db() as con:
        con.execute("INSERT INTO llm_cache(cache_key,model,family,prompt_sha,response,created_at,metadata) "
                    "VALUES(?,?,?,?,?,?,?)", ("fake", "checker", "glm", "prompt", json.dumps({"items": payload}),
                    "test", json.dumps({"response_id": "fake-response"})))
    recovered, issues = enrich_endpoint_families(ws, cfg, rows, previous=snapshot)
    assert bool(recovered["groups"]) is adopt
    assert (ws.verifications()["family:retained"]["status"] == "verified") is adopt
    if adopt:
        assert not issues
        assert ws.verifications()["family:retained"]["deterministic_recheck"]["review_binding"] == dict(
            method="cached_verifier_item", response_id="fake-response")
    else:
        assert any(i["kind"] == "endpoint_family_missing" for i in issues)
