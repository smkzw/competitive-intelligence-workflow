"""A source search hit is not itself a structured trial-design feature."""
from test_design_source_clauses import models

from ciw.analyze.design import build_design
from ciw.analyze.design_excerpts import design_excerpts
from ciw.config import DesignTopicCfg
from ciw.models import Design, Locator, Trial
from ciw.verify.design_clauses import _check, enrich_design_clauses


def context(cfg, text):
    cfg = cfg.model_copy(deep=True)
    cfg.design_topics = [DesignTopicCfg(label="活检要求", kind="lookup", patterns=["biopsy"])]
    t = Trial(trial_id="synthetic", registry="ctgov", conditions=[cfg.name_en],
              locator=Locator(source_id="synthetic"), design=Design(detailed_description=text))
    return cfg, t


def test_background_lookup_is_source_checked_not_promoted_to_a_trial_requirement(cfg, ws):
    text = "Previous studies suggest that kidney biopsy is useful for this disease."
    cfg, trial = context(cfg, text)
    c = build_design(cfg, [trial], {})
    answer = [dict(topic_id="design-topic-0", quote=text, clauses=[])]
    roles = models(answer)
    assert not enrich_design_clauses(ws, cfg, [trial], c, roles)
    assert roles["extractor_a"].responder.call_count == 2
    assert not c["rows"][0]["design_excerpts"]
    assert c["rows"][0]["study_narrative"][0]["text"] == text
    # A model cannot relabel the same general background as this study's operation.
    item = dict(topic_id="design-topic-0", quote=text, clauses=[dict(field="detailed_description",
        text=text, quote=text, condition="", cohort_quote="", protocol_quote=text, criterion_role="unspecified")])
    assert not _check(item, {"design-topic-0": dict(kind="lookup")}, [("研究描述", text, "detailed_description")])[0]


def test_explicit_trial_biopsy_plan_remains_a_lookup_design_feature(cfg, ws):
    text = "In this study, patients will undergo a kidney biopsy at Week 12."
    cfg, trial = context(cfg, text)
    c = build_design(cfg, [trial], {})
    item = dict(topic_id="design-topic-0", quote=text, clauses=[dict(field="detailed_description",
        text=text, quote=text, condition="", cohort_quote="", protocol_quote=text, criterion_role="unspecified")])
    assert not enrich_design_clauses(ws, cfg, [trial], c, models([item]))
    assert c["rows"][0]["design_excerpts"][0]["snippets"][0]["text"] == text


def test_heading_only_hits_do_not_become_criteria_but_full_original_remains(cfg):
    cfg, trial = context(cfg, "")
    cfg.design_topics[0].patterns = ["Inclusion Criteria", "Exclusion Criteria"]
    trial.design.eligibility_text = "Inclusion Criteria:\nAge ≥18 years.\nExclusion Criteria:\nPrior cancer."
    assert not design_excerpts(trial, cfg.design_topics)
    trial.design.eligibility_text = "Inclusion Criteria: Age ≥18 years."
    assert design_excerpts(trial, cfg.design_topics)[0]["snippets"][0]["text"] == trial.design.eligibility_text
