"""Reopen ordinary source-backed A/B artifacts; not Ego/clinical release QA."""

import json
import re
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.renderers.portal import report_a
from ci_workflow.reports.b.semantic_grouping import semantic_row_digest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / ".artifacts/1007-source-questions-current-v2"


def _assignment(text, name):
    return json.JSONDecoder().raw_decode(text.split(f"window.{name} = ", 1)[1])[0]


def _read():
    if not (CANDIDATE / "checkpoint.json").is_file():
        pytest.skip("private real source replay absent; no source/visual acceptance implied")
    checkpoint = json.loads((CANDIDATE / "checkpoint.json").read_bytes())
    for path, expected in checkpoint["input_bindings"].items():
        assert sha256((ROOT / path).read_bytes()).hexdigest() == expected
    return checkpoint


def test_real_same_source_question_in_ordinary_a_and_b_keeps_science_and_all_instances():
    checkpoint = _read()
    original = report_a.ReportAPortalData.model_validate_json((ROOT /
        ".artifacts/1007-ab-context-current-v2/project/inputs/a-bound.json").read_bytes())
    projected = report_a.ReportAPortalData.model_validate_json(
        (CANDIDATE / "a-input.json").read_bytes())
    assert projected.efficacy_views["facts"] == original.efficacy_views["facts"]
    old_workspace, old_groups, old_rows = report_a._a_comparison_workspace(original)
    workspace, groups, rows = report_a._a_comparison_workspace(projected)
    assert groups == old_groups and rows == old_rows
    assert {key: semantic_row_digest(row) for key, row in rows.items()} == {
        key: semantic_row_digest(row) for key, row in old_rows.items()}
    for key in ("membership", "facets", "numeric_eligibility"):
        assert workspace[key] == old_workspace[key]
    actual_a = _assignment((CANDIDATE / "A/clinical-portfolio.html").read_text(),
                           "__A_COMPARISON_WORKSPACE__")
    assert actual_a == json.loads(json.dumps(workspace))
    # Follow the actual overview's relative scripts, not arbitrary filesystem
    # order that might select a valid single-study dossier workspace instead.
    overview = (CANDIDATE / "B/overview.html").read_text()
    scripts = re.findall(r'<script src="([^"]+)">', overview)
    payloads = [(CANDIDATE / "B" / path).read_text() for path in scripts
                if path.startswith("data/shared-payloads/")]
    actual_b = next(_assignment(text, "__B_COMPARISON_WORKSPACE__") for text in payloads
                    if text.startswith("window.__B_COMPARISON_WORKSPACE__ = "))
    question = "efficacy::q-pruritus-nrs-ge4-improvement"
    a_column = next(c for c in actual_a["columns"] if c["question_id"] == question)
    b_column = next(c for c in actual_b["columns"] if c["question_id"] == question)
    assert a_column["cells"] == b_column["cells"]
    assert len(a_column["cells"]) == 3 and len(a_column["row_ids"]) == 32
    assert len({rows[row]["product_id"] for row in a_column["row_ids"]}) == 2
    assert len(a_column["scientific_facets"]) == 32
    assert all(rows[row]["semantic_estimand"] == "estimand-not-reported"
               for row in a_column["row_ids"])
    assert len(projected.efficacy) == checkpoint["full_efficacy_pool"] == 3544
    assert len(rows) == checkpoint["full_members"] == 3733
    assert checkpoint["current_promoted"] is False and checkpoint["browser_inspected"] is False


def test_real_scalar_metric_differences_onset_and_truncation_reach_cell_labels():
    _read()
    data = report_a.ReportAPortalData.model_validate_json((CANDIDATE / "a-input.json").read_bytes())
    workspace, _groups, _rows = report_a._a_comparison_workspace(data)
    proposal = json.loads((ROOT /
        ".artifacts/1007-source-question-proposals-v1/proposal.json").read_bytes())
    source = json.loads((ROOT /
        ".artifacts/1007-source-question-proposals-v1/source-contexts.json").read_bytes())
    originals = {(c["source_version_id"], c["source_measure_path"]): c["source_measure"]
                 for c in source["contexts"]}
    columns = {c["question_id"]: c for c in workspace["columns"]}
    for context in proposal["contexts"]:
        raw = originals[(context["source_version_id"], context["source_measure_path"])]
        ice = context["facet_dimensions"]["ice"]
        for field in ("rescue_source_phrase", "missing_source_phrase"):
            quote = ice[field]
            if quote is not None:
                assert quote in raw["description"]
        column = columns["efficacy::" + context["question_id"]]
        assert set(context["row_ids"]) <= set(column["row_ids"])
        labels = [column["facet_label_by_row"][row] for row in context["row_ids"]]
        if context["facet_dimensions"]["statistic"]["kind"] == "kaplan_meier_probability":
            assert all("Kaplan–Meier 概率" in label for label in labels)
            assert all("非原报告百分比" in label for label in labels)
        if context["question_id"] == "q-wi-nrs-onset-of-action":
            assert all("不证明第4周就是首次起效周" in label for label in labels)
        if ice["missing_status"] == "source_text_truncated":
            assert raw["description"].endswith("non-responde")
            assert all("原文截断，完整规则待核" in label for label in labels)
    assert "efficacy::q-iga-pn-s-score-0-or-1" in columns
    assert "efficacy::q-iga-success-0-or-1-and-ge2-reduction" in columns
    assert "efficacy::q-wi-nrs-ge4-and-iga-pn-s-0-or-1" in columns
    assert "efficacy::q-sd-nrs-ge4-improvement" in columns
    assert "efficacy::q-sleep-nrs-quality-change" in columns
