"""Compound criteria and narrative claims need source-bound clauses, never guessed values."""
import json
from copy import deepcopy
from unittest.mock import Mock

import pytest

from ciw.analyze.design import build_design
from ciw.config import DesignTopicCfg
from ciw.models import Design, Locator, Trial
from ciw.verify.design_clauses import enrich_design_clauses
from ciw.verify.llm import FakeBackend


def example(cfg):
    cfg = cfg.model_copy(deep=True)
    cfg.design_topics = [DesignTopicCfg(label="eGFR入排阈值", patterns=["eGFR"]),
                         DesignTopicCfg(label="给药方案", patterns=["Regimen"], kind="dosing_regimen")]
    criteria = ("Inclusion criteria:\nBiopsy may be omitted if all of the following apply: "
                "proteinuria >5 g/day; eGFR ≥40 mL/min; albumin <30 g/L.")
    narrative = "Regimen A is a recommended treatment for this disease with a long follow-up period."
    t = Trial(trial_id="synthetic", registry="ctgov", conditions=[cfg.name_en],
              locator=Locator(source_id="source"),
              design=Design(eligibility_text=criteria, detailed_description=narrative))
    review = [dict(topic_id="design-topic-0", quote=criteria.splitlines()[1], clauses=[
        dict(field="eligibility", text="eGFR ≥40 mL/min", quote=criteria.splitlines()[1],
             condition="Biopsy may be omitted if all of the following apply:",
             cohort_quote="", criterion_role="inclusion")]),
        dict(topic_id="design-topic-1", quote=narrative, clauses=[])]
    return cfg, t, review


def models(items):
    answer = Mock(return_value=json.dumps(dict(items=items)))
    return {"extractor_a": FakeBackend("deepseek", "a", answer),
            "verifier": FakeBackend("glm", "b", answer)}


def test_compact_clause_keeps_parent_condition_and_background_is_not_regimen(cfg, ws):
    cfg, t, items = example(cfg)
    raw = t.model_dump()
    c = build_design(cfg, [t], {})
    roles = models(items)
    assert enrich_design_clauses(ws, cfg, [t], c, roles) == []
    snippets = c["rows"][0]["design_excerpts"]
    assert len(snippets) == 1 and snippets[0]["topic_id"] == "design-topic-0"
    clause = snippets[0]["snippets"][0]
    assert clause["text"] == "eGFR ≥40 mL/min" and clause["condition"].endswith("apply:")
    assert clause["context"] == items[0]["quote"] and clause["criterion_role"] == "inclusion"
    assert clause["source_id"] == "source" and clause["marks"]
    assert t.model_dump() == raw
    # Saved content/rule reuse, even when later report generation has no C model budget.
    later = build_design(cfg, [t], {})
    cfg.design_topics[0].aliases = ["搜索词变动不重抽原文"]
    # Use the original projection's search data here: the source clauses themselves must stay identical.
    assert enrich_design_clauses(ws, cfg, [t], later, None) == []
    assert later == c and roles["extractor_a"].responder.call_count == 2


@pytest.mark.parametrize("field,value", [("text", "eGFR ≥50 mL/min"),
    ("field", "outcome:999"), ("condition", ""), ("criterion_role", "exclusion"),
    ("cohort_quote", "PMN cohort")])
def test_invented_or_decontextualized_clauses_cannot_enter_current_projection(cfg, ws, field, value):
    cfg, t, items = example(cfg)
    items = deepcopy(items)
    items[0]["clauses"][0][field] = value
    c = build_design(cfg, [t], {})
    issues = enrich_design_clauses(ws, cfg, [t], c, models(items))
    assert issues and not c["rows"][0]["design_excerpts"]
    assert c["rows"][0]["eligibility"] == t.design.eligibility_text


def test_changed_source_or_topic_does_not_reuse_previous_acceptance(cfg, ws):
    cfg, t, items = example(cfg)
    c = build_design(cfg, [t], {})
    enrich_design_clauses(ws, cfg, [t], c, models(items))
    t.design.eligibility_text = t.design.eligibility_text.replace("≥40", "≥45")
    later = build_design(cfg, [t], {})
    issues = enrich_design_clauses(ws, cfg, [t], later, None)
    assert issues and not later["rows"][0]["design_excerpts"]
    assert "≥45" in later["rows"][0]["eligibility"]


def test_short_unambiguous_registry_criterion_needs_no_model(cfg, ws):
    cfg, t, _ = example(cfg)
    t.design = Design(eligibility_text="Inclusion criteria:\neGFR ≥40 mL/min.")
    c = build_design(cfg, [t], {})
    assert enrich_design_clauses(ws, cfg, [t], c, None) == []
    assert c["rows"][0]["design_excerpts"][0]["snippets"][0]["text"] == "eGFR ≥40 mL/min."


def test_non_numeric_source_mentions_are_searchable_without_inventing_criteria(cfg):
    cfg, t, _ = example(cfg)
    cfg.design_topics[0].aliases = ["肾功能"]
    t.design = Design(eligibility_text="eGFR is recorded without a numeric eligibility cutoff.")
    c = build_design(cfg, [t], {})
    assert c["topic_catalog"][0]["topic_id"] == "design-topic-0"
    assert "肾功能" in c["rows"][0]["search_text"]
    assert c["rows"][0]["design_excerpts"] == []


def test_required_call_failure_keeps_previous_current(cfg, seeded_ws, monkeypatch):
    from ciw.pipeline import run
    from ciw.verify.crosscheck import CrosscheckFailed
    original = run(cfg, seeded_ws, offline=True, report_scope="C", render=False, log=lambda *_: None)
    before = original.release_path.read_bytes()
    custom, t, _ = example(cfg)
    monkeypatch.setattr("ciw.pipeline._extract_studies", lambda *_: ({t.trial_id: t}, [], [], {}, {}))
    def fail(*_):
        raise CrosscheckFailed("synthetic network failure", calls=[dict(family="deepseek", error="OSError")])
    monkeypatch.setattr("ciw.verify.design_clauses.crosscheck", fail)
    with pytest.raises(CrosscheckFailed):
        run(custom, seeded_ws, offline=True, report_scope="C", roles=models([]), render=False, log=lambda *_: None)
    assert seeded_ws.current_release_dir() == original.release_path.parent
    assert original.release_path.read_bytes() == before


def test_multiline_parent_is_visible_and_cannot_be_removed_by_a_model(cfg, ws):
    cfg, t, _ = example(cfg)
    t.design = Design(eligibility_text="Inclusion criteria:\nBiopsy may be omitted if all of the following apply:\n"
                      "- anti-PLA2R positive;\n- eGFR ≥40 mL/min.")
    c = build_design(cfg, [t], {})
    assert "all of the following" in c["rows"][0]["design_excerpts"][0]["snippets"][0]["condition"]
    item = dict(topic_id="design-topic-0", quote=t.design.eligibility_text,
                clauses=[dict(field="eligibility", text="eGFR ≥40 mL/min", quote="- eGFR ≥40 mL/min.",
                              criterion_role="inclusion")])
    assert enrich_design_clauses(ws, cfg, [t], c, models([item]))
    assert c["rows"][0]["design_excerpts"] == []


def test_key_headings_and_new_peer_bullet_end_the_previous_list():
    from ciw.normalize.design import logical_contexts
    text = ("Key Inclusion Criteria:\n* Meets one of the following:\n"
            "  1. New disease, proteinuria ≥5 g/day.\n  2. Relapsed disease, proteinuria ≥4 g/day.\n"
            "* UPCR ≥3 g/g.\nKey Exclusion Criteria:\n* eGFR ≤30 mL/min.")
    assert logical_contexts(text, "proteinuria ≥4 g/day")[0]["condition"] == "* Meets one of the following:"
    assert logical_contexts(text, "UPCR ≥3 g/g") == []
    assert logical_contexts(text, "eGFR ≤30 mL/min") == []


def test_prompt_field_labels_are_not_quotes_and_repair_names_the_exact_problem(cfg):
    from ciw.models import Arm
    from ciw.normalize.design import design_passages
    from ciw.verify.design_clauses import DesignTopicReview, _check
    cfg, t, _ = example(cfg)
    t.arms = [Arm(arm_id="a", label="Combination", description="Drug A 10 mg weekly")]
    item = DesignTopicReview(topic_id="design-topic-1", quote="FIELD arm:a (Combination)", clauses=[]).model_dump()
    okay, reason = _check(item, {t["topic_id"]:t for t in build_design(cfg, [], {})["topic_catalog"]},
                          design_passages(t))
    assert not okay and "FIELD" in reason and "quote" in reason


@pytest.mark.parametrize("mode", ["valid", "duplicate", "peer", "exclusion", "paraphrased"])
def test_unique_list_parent_has_its_own_source_locator_without_rewriting_child_quote(cfg, ws, mode):
    cfg, t, _ = example(cfg)
    parent = "* Meets one of the following:"
    child = "Relapsed disease, eGFR ≥40 mL/min."
    prefix = "Key Inclusion Criteria:\n" + parent + "\n  1. Newly diagnosed disease.\n"
    if mode == "peer":
        prefix += "* Separate criterion:\n"
    if mode == "exclusion":
        prefix += "Key Exclusion Criteria:\n"
    t.design = Design(eligibility_text=prefix + "  2. " + child + ("\n  3. " + child if mode=="duplicate" else ""))
    condition = parent if mode != "paraphrased" else "Either new or relapsed disease"
    role = "exclusion" if mode == "exclusion" else "inclusion"
    item = dict(topic_id="design-topic-0", quote=child, clauses=[dict(field="eligibility", text=child,
                quote=child, condition=condition, cohort_quote="", criterion_role=role)])
    c = build_design(cfg, [t], {})
    # Peer/exclusion cases need the same source guard even though their baseline short clause is not pending.
    from ciw.normalize.design import design_passages
    from ciw.verify.design_clauses import DesignTopicReview, _check
    valid = _check(DesignTopicReview.model_validate(item).model_dump(),
                   {x["topic_id"]:x for x in c["topic_catalog"]}, design_passages(t))[0]
    assert valid == (mode == "valid")
    if mode == "valid":
        assert not enrich_design_clauses(ws, cfg, [t], c, models([item]))
        snippet = c["rows"][0]["design_excerpts"][0]["snippets"][0]
        locator = snippet["condition_source"]
        assert t.design.eligibility_text[locator["start"]:locator["end"]] == parent
        assert snippet["text"] == child and "Newly diagnosed" in snippet["context"]
        assert snippet["source_quote"] == child  # The verifier's original child quote stays intact.


def test_exact_recommendation_is_not_proof_of_actual_regimen(cfg, ws):
    cfg, t, items = example(cfg)
    items[1]["clauses"] = [dict(field="detailed_description", text=t.design.detailed_description,
        quote=t.design.detailed_description, protocol_quote=t.design.detailed_description)]
    c = build_design(cfg, [t], {})
    assert enrich_design_clauses(ws, cfg, [t], c, models(items))
    assert [t["topic_id"] for t in c["rows"][0]["design_excerpts"]] == ["design-topic-0"]


def test_trial_operation_cannot_lend_its_anchor_to_adjacent_general_recommendation(cfg, ws):
    cfg, t, _ = example(cfg)
    actual = "In this study participants will receive Drug A 10 mg weekly."
    generic = "Drug B is a recommended treatment Regimen."
    t.design = Design(detailed_description=actual + " " + generic)
    item = dict(topic_id="design-topic-1", quote=t.design.detailed_description,
                clauses=[dict(field="detailed_description", text=generic, quote=t.design.detailed_description,
                              protocol_quote=t.design.detailed_description)])
    c = build_design(cfg, [t], {})
    assert enrich_design_clauses(ws, cfg, [t], c, models([item]))
    item["clauses"][0]["text"] = actual
    item["clauses"][0]["protocol_quote"] = actual
    # A changed source/rule task is not needed to construct the positive producer check.
    from ciw.normalize.design import design_passages
    from ciw.verify.design_clauses import DesignTopicReview, _check
    assert _check(DesignTopicReview.model_validate(item).model_dump(),
                  {x["topic_id"]:x for x in c["topic_catalog"]}, design_passages(t))[0]


def test_partial_topup_preserves_prior_source_checked_topics(cfg, ws, monkeypatch):
    from ciw.verify.crosscheck import CheckedItem
    from ciw.verify.design_clauses import _review, _task
    cfg, t, items = example(cfg)
    selected = build_design(cfg, [t], {})["topic_catalog"]
    task, passages = _task(t, selected)
    responses = iter([[CheckedItem(items[0], "verified", ("design-topic-0",))],
                      [CheckedItem(items[1], "verified", ("design-topic-1",))]])
    monkeypatch.setattr("ciw.verify.design_clauses.crosscheck", lambda *_: next(responses))
    saved = {"tasks": {}}
    assert set(_review(ws, task, passages, selected, saved, models([]))) == {"design-topic-0"}
    assert set(_review(ws, task, passages, selected, saved, models([]))) == {"design-topic-0", "design-topic-1"}


def test_structured_background_and_titled_endpoint_definition_keep_timeframe(cfg):
    from ciw.models import PlannedOutcome
    cfg = cfg.model_copy(deep=True)
    cfg.design_topics = [DesignTopicCfg(label="背景治疗", patterns=["Methotrexate"], kind="background_therapy"),
        DesignTopicCfg(label="完全缓解定义", patterns=["Complete remission"], kind="endpoint_definition")]
    t = Trial(trial_id="synthetic", registry="ctgov", locator=Locator(source_id="s"),
        design=Design(background_therapy=["Methotrexate 10 mg weekly"]),
        outcomes_planned=[PlannedOutcome(title="Complete remission", kind="primary", timeframe="Week 24",
                                         description="Proteinuria <0.3 g/day")])
    row = build_design(cfg, [t], {})["rows"][0]
    snippets = {x["topic_id"]: x["snippets"] for x in row["design_excerpts"]}
    assert snippets["design-topic-0"][0]["text"] == "Methotrexate 10 mg weekly"
    assert snippets["design-topic-1"][0]["text"] == "Proteinuria <0.3 g/day"
    assert snippets["design-topic-1"][0]["timeframe"] == "Week 24"
    assert snippets["design-topic-1"][0]["timeframe_field"] == "outcome:0:timeframe"
