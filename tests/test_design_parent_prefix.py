"""A source's list marker is layout, while all words in its clinical parent remain binding."""

import json

import pytest
from test_retained_source_facts import cached_roles

from ciw.analyze.design import build_design
from ciw.config import DesignTopicCfg
from ciw.models import Design, Locator, Trial
from ciw.normalize.design import design_passages
from ciw.verify.design_clauses import DesignTopicReview, _check, _parent_offset, _source_context, enrich_design_clauses


def example(cfg, marker="* ", parent="Meets one of the following:"):
    cfg = cfg.model_copy(deep=True)
    cfg.design_topics = [DesignTopicCfg(label="eGFR入排阈值", patterns=["eGFR"], kind="eligibility_threshold")]
    child = "Relapsed disease, defined as documented remission after treatment followed by eGFR ≥40 mL/min."
    source = "Inclusion criteria:\n" + marker + parent + "\n  1. New disease.\n  2. " + child
    trial = Trial(
        trial_id="synthetic", registry="ctgov", locator=Locator(source_id="s"), design=Design(eligibility_text=source)
    )
    item = DesignTopicReview(
        topic_id="design-topic-0",
        quote=child,
        clauses=[dict(field="eligibility", text=child, quote=child, condition=parent, criterion_role="inclusion")],
    ).model_dump()
    return cfg, trial, item


@pytest.mark.parametrize("marker", ["* ", "- ", "+ ", "• ", "   "])
def test_markerless_parent_keeps_exact_source_binding_and_all_branches(cfg, marker):
    cfg, trial, item = example(cfg, marker)
    assert _check(item, {"design-topic-0": dict(kind="eligibility_threshold")}, design_passages(trial))[0]
    bound = _source_context(item["clauses"][0], trial.design.eligibility_text)
    locator = bound["condition_source"]
    assert trial.design.eligibility_text[locator["start"] : locator["end"]] == item["clauses"][0]["condition"]
    assert "New disease" in bound["context"] and "Relapsed disease" in bound["context"]


@pytest.mark.parametrize("condition", ["one of the following:", "the following:", "Meets all of the following:"])
def test_format_equivalence_cannot_remove_or_change_parent_words(cfg, condition):
    cfg, trial, item = example(cfg)
    item["clauses"][0]["condition"] = condition
    assert not _check(item, {"design-topic-0": dict(kind="eligibility_threshold")}, design_passages(trial))[0]


@pytest.mark.parametrize("prefix", ["1. ", "A. ", "Cohort A ", "Meets ", "one "])
def test_numbered_or_clinical_prefixes_are_not_assumed_decorative(prefix):
    assert _parent_offset("the following:", prefix + "the following:") is None


@pytest.mark.parametrize(
    "proof",
    [
        "valid",
        "no_b_cache",
        "a_only",
        "changed_source",
        "wrong_note",
        "changed_task",
        "changed_source_id",
        "changed_b_item",
    ],
)
def test_original_complete_verifier_item_can_be_rechecked_after_marker_binding_repair(cfg, ws, monkeypatch, proof):
    import ciw.verify.design_clauses as clauses

    cfg, trial, item = example(cfg)
    roles = cached_roles(ws, [item])
    current = clauses._source_context
    monkeypatch.setattr(
        clauses, "_source_context", lambda c, s: None if not c["condition"].startswith("*") else current(c, s)
    )
    assert enrich_design_clauses(ws, cfg, [trial], build_design(cfg, [trial], {}), roles)
    original = next(v for v in ws.verifications().values() if v.get("item", {}).get("topic_id") == "design-topic-0")
    assert original["status"] == "needs_review"
    with ws.db() as con:
        if proof == "no_b_cache":
            con.execute("DELETE FROM llm_cache WHERE family='glm'")
        if proof == "changed_b_item":
            con.execute("UPDATE llm_cache SET response=? WHERE family='glm'", ('{"items":[]}',))
        if proof in {"wrong_note", "changed_task", "changed_source_id"}:
            field = {"wrong_note": "note", "changed_task": "task", "changed_source_id": "source_id"}[proof]
            for key, data in con.execute("SELECT fact_key,payload FROM verifications").fetchall():
                record = json.loads(data)
                record[field] = "not-the-original"
                con.execute("UPDATE verifications SET payload=? WHERE fact_key=?", (json.dumps(record), key))
        if proof == "a_only":
            for key, data in con.execute("SELECT fact_key,payload FROM verifications").fetchall():
                record = json.loads(data)
                record["calls"] = [c for c in record["calls"] if c["role"] == "extract"]
                con.execute("UPDATE verifications SET payload=? WHERE fact_key=?", (json.dumps(record), key))
        cache_before = con.execute("SELECT cache_key FROM llm_cache ORDER BY cache_key").fetchall()
    if proof == "changed_source":
        trial.design.eligibility_text = trial.design.eligibility_text.replace("≥40", "≥45")
    monkeypatch.setattr(clauses, "_source_context", current)
    view = build_design(cfg, [trial], {})
    issues = enrich_design_clauses(ws, cfg, [trial], view, None)
    assert bool(issues) == (proof != "valid")
    assert bool(view["rows"][0]["design_excerpts"]) == (proof == "valid")
    with ws.db() as con:
        assert con.execute("SELECT cache_key FROM llm_cache ORDER BY cache_key").fetchall() == cache_before
    if proof == "valid":
        updated = next(v for v in ws.verifications().values() if v.get("item", {}).get("topic_id") == "design-topic-0")
        assert updated["status"] == "verified" and updated["calls"] == original["calls"]
        assert updated["deterministic_recheck"]["previous_status"] == "needs_review"
