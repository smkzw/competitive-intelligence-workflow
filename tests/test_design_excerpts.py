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
