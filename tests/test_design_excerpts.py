"""Verbatim design clauses, not inferred eligibility or clinical equivalence."""

import json
import subprocess
from pathlib import Path

import pytest
from lxml import html

from ciw.analyze.design import build_design
from ciw.analyze.design_excerpts import design_excerpts, threshold_spans
from ciw.config import DesignTopicCfg
from ciw.models import Arm, Design, Locator, Trial


def trial(text):
    return Trial(
        trial_id="synthetic",
        registry="ctgov",
        locator=Locator(source_id="source"),
        design=Design(eligibility_text=text),
    )


def test_matching_clause_and_source_are_retained_without_numeric_assignment(cfg):
    text = (
        "Inclusion criteria:\nNPS ≥5 and NCS at least 2; asthma must be controlled.\n"
        "Exclusion criteria:\nSurgery <6 months."
    )
    t = trial(text)
    result = design_excerpts(t, cfg.design_topics)
    nps = next(r for r in result if r["label"] == "鼻息肉评分")["snippets"][0]
    assert nps["text"] == text.splitlines()[1] and nps["source_id"] == "source"
    assert [nps["text"][s["start"] : s["end"]] for s in nps["marks"]] == ["≥5", "at least 2"]
    assert "value" not in nps  # Multiple thresholds in one clause are not assigned to a guessed metric.
    assert t.design.eligibility_text == text
    assert next(r for r in result if r["label"] == "既往手术")["snippets"][0]["text"] == "Surgery <6 months."


def test_empty_topics_do_not_invent_design_features_and_arm_text_is_searchable():
    t = trial("No thresholds specified.")
    assert design_excerpts(t, []) == [] and threshold_spans(t.design.eligibility_text) == []
    t.arms = [Arm(arm_id="a", label="Trial arm", description="Dose 300 mg every 2 weeks.")]
    found = design_excerpts(t, [DesignTopicCfg(label="给药", patterns=[r"\bmg\b"])])
    assert found[0]["snippets"][0]["field"] == "arm:a"
    assert found[0]["snippets"][0]["text"] == t.arms[0].description


def test_randomization_and_rescue_are_indexed_from_design_narrative_without_guessing(cfg):
    t = trial("Eligibility is defined separately.")
    t.design.detailed_description = "Patients are randomized in a 2:1 ratio. Rescue therapy is permitted after Week 12."
    found = design_excerpts(t, cfg.design_topics)
    assert {r["label"] for r in found} >= {"随机比例", "背景治疗与救援"}
    assert all(s["text"] == t.design.detailed_description for r in found for s in r["snippets"])


def test_config_rejects_invalid_expressions():
    with pytest.raises(ValueError):
        DesignTopicCfg(label="invalid", patterns=["["])


def test_design_projection_uses_same_original_text_for_marks_and_topics(cfg):
    t = trial("鼻息肉评分≥5分；鼻塞评分不低于2分")
    row = build_design(cfg, [t], {})["rows"][0]
    assert row["eligibility"] == t.design.eligibility_text and len(row["design_excerpts"]) == 2
    assert [row["eligibility"][s["start"] : s["end"]] for s in row["eligibility_marks"]] == ["≥5分", "不低于2分"]


def test_annotation_preserves_unicode_original_and_escapes_markup_with_overlapping_search():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    text = "🧬 NPS <5 & <script>alert(1)</script>"
    script = r"""
const fs=require('fs'),vm=require('vm');
const window={CIW:{},addEventListener(){}};
const document={getElementById(){return null},addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});
const d=JSON.parse(process.argv[2]);
process.stdout.write(window.U.annotate(d.text,d.marks,'NPS <5'));
"""
    data = json.dumps({"text": text, "marks": threshold_spans(text)})
    result = subprocess.run(["node", "-e", script, str(asset), data], capture_output=True, text=True, check=True)
    fragment = html.fragment_fromstring(result.stdout, create_parent="div")
    assert fragment.text_content() == text and not fragment.xpath(".//script")
    assert fragment.xpath(".//strong")[0].text_content() == "<5"
    assert "".join(fragment.xpath(".//mark/text()")) == "NPS <5"


def test_treatment_duration_is_not_postdose_contraception_or_endpoint_followup():
    t = trial("Women use contraception for 18 months after the last dose of study treatment.")
    t.design.detailed_description = "Study treatment will be administered for 52 weeks."
    t.arms = [Arm(arm_id="a", label="Drug", description="Drug is administered every 2 weeks.")]
    topic = DesignTopicCfg(label="治疗时长", patterns=["treatment", "last dose"])
    found = design_excerpts(t, [topic])
    assert [s["text"] for s in found[0]["snippets"]] == [t.design.detailed_description]


def test_design_projection_keeps_complete_endpoint_definition_and_source_conditions(cfg):
    from ciw.models import PlannedOutcome
    t = trial("Study cohort criteria")
    t.conditions = ["Disease A", "Disease B"]
    t.outcomes_planned = [PlannedOutcome(kind="primary", title="Response", timeframe="Week 104",
                                        description="UPCR ≤0.7, eGFR ≥60 and no treatment failure.")]
    row = build_design(cfg, [t], {})["rows"][0]
    assert row["primary"][0]["description"] == t.outcomes_planned[0].description
    assert row["primary"][0]["description_marks"]
    assert row["conditions"] == t.conditions


def test_eligibility_threshold_topics_do_not_collect_outcome_measurements():
    from ciw.models import PlannedOutcome
    t = trial("anti-PLA2R antibody ≥50 RU/mL and eGFR ≥50 mL/min.")
    t.outcomes_planned = [PlannedOutcome(kind="primary", title="anti-PLA2R change",
                                        description="anti-PLA2R antibody change.")]
    topic = DesignTopicCfg(label="抗PLA2R抗体入排阈值", patterns=["anti-PLA2R"])
    found = design_excerpts(t, [topic])
    assert topic.kind == "eligibility_threshold"
    assert {s["field"] for s in found[0]["snippets"]} == {"eligibility"}
    assert found[0]["snippets"][0]["marks"]


def test_remission_definition_topics_do_not_collect_prior_response_eligibility():
    from ciw.models import PlannedOutcome
    t = trial("Exclude patients who previously achieved complete remission.")
    t.outcomes_planned = [PlannedOutcome(kind="primary", title="Complete remission",
                                        description="Complete remission: protein <0.3 g/day.")]
    topic = DesignTopicCfg(label="完全缓解定义", patterns=["complete remission"])
    found = design_excerpts(t, [topic])
    assert topic.kind == "endpoint_definition"
    assert {s["field"] for s in found[0]["snippets"]} == {"outcome:0"}


def test_conditional_retreatment_and_followup_are_separate_verbatim_clauses():
    t = trial("")
    text = ("After treatment, subjects enter a repeat treatment period (3 months) if necessary; "
            "and a final follow-up period of 15 to 18 months.")
    t.design.detailed_description = text
    topic = DesignTopicCfg(label="实际给药暴露/治疗时长", patterns=["treatment"], kind="treatment_duration")
    snippets = design_excerpts(t, [topic])[0]["snippets"]
    assert len(snippets) == 1
    assert "3 months" in snippets[0]["text"] and "if necessary" in snippets[0]["text"]
    assert "15" not in snippets[0]["text"] and "follow-up" not in snippets[0]["text"]
    assert snippets[0]["context"] == text and t.design.detailed_description == text


def test_followup_cannot_supply_a_treatment_duration_and_real_preposed_duration_is_kept():
    t = trial("")
    t.design.detailed_description = "Participants will be treated, then followed for 18 months."
    topic = DesignTopicCfg(label="治疗时长", patterns=["treatment"])
    assert design_excerpts(t, [topic]) == []
    t.design.brief_summary = "A randomized study with a 100 week treatment period."
    snippets = design_excerpts(t, [topic])[0]["snippets"]
    assert [s["text"] for s in snippets] == [t.design.brief_summary]


def test_eligibility_ranges_are_highlighted_without_turning_a_date_into_a_threshold():
    text = "eGFR 30–60 mL/min, age between 18 and 65; record date 2026-10-28."
    marked = [text[s["start"]:s["end"]] for s in threshold_spans(text)]
    assert marked == ["30–60 mL/min", "between 18 and 65"]
