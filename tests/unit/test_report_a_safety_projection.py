"""A 类安全性展示投影的定向回归测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal import report_a
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    _display_safety_rows,
    _safety_event_filters,
    render_report_a_site,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/positive/a-atopic-dermatitis/research-content.json"


def _report() -> ReportAPortalData:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return ReportAPortalData.model_validate(payload["report_data"])


def test_controlled_safety_aliases_merge_without_rewriting_raw_terms() -> None:
    rows = _display_safety_rows(_report())
    aliases = [
        row
        for row in rows
        if row["term"] in {"Headache", "HEADACHE", "头痛"}
    ]

    assert aliases
    assert {row["term_key"] for row in aliases} == {"headache"}
    assert {row["term_label"] for row in aliases} == {"头痛"}
    assert {row["original_term"] for row in aliases} >= {"Headache", "HEADACHE"}
    assert all(row["term"] == row["original_term"] for row in aliases)

    nasopharyngitis = [
        row
        for row in rows
        if row["term"] in {"Nasopharyngitis", "NASOPHARYNGITIS", "鼻咽炎"}
    ]
    assert {row["term_key"] for row in nasopharyngitis} == {"nasopharyngitis"}
    assert {row["term_label"] for row in nasopharyngitis} == {"鼻咽炎"}

    assert {
        row["term_key"]
        for row in rows
        if row["term"] in {"Tension Headache", "TENSION HEADACHE"}
    }.isdisjoint({"headache"})


def test_event_filter_projection_has_one_choice_per_controlled_dimension() -> None:
    rows = _display_safety_rows(_report())
    filters = _safety_event_filters(rows)

    assert sum(item["key"] == "headache" for item in filters) == 1
    assert sum(item["key"] == "nasopharyngitis" for item in filters) == 1
    assert next(item for item in filters if item["key"] == "headache")["label"] == "头痛"
    assert next(item for item in filters if item["key"] == "nasopharyngitis")["label"] == "鼻咽炎"


def test_rendered_safety_payload_keeps_unpublished_state_and_raw_term(tmp_path: Path) -> None:
    report = _report()
    rows = _display_safety_rows(report)
    unpublished = next(row for row in rows if row["disclosure_state"] == "未公开")
    render_report_a_site(report, tmp_path)

    report_js = (tmp_path / "data/report.js").read_text(encoding="utf-8")
    safety_html = (tmp_path / "safety.html").read_text(encoding="utf-8")
    assert f'"original_term":"{unpublished["original_term"]}"' in report_js
    assert '"disclosure_state":"未公开"' in report_js
    assert 'data-event-key="headache"' in safety_html
    assert 'data-normalized-term="头痛"' in safety_html
    assert 'data-disclosure-state="未公开"' in safety_html


def test_report_a_projects_each_row_collection_once_per_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counts = {"efficacy": 0, "safety": 0}
    original_efficacy = report_a._display_efficacy_rows
    original_safety = report_a._display_safety_rows

    def counted_efficacy(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
        counts["efficacy"] += 1
        return original_efficacy(data)

    def counted_safety(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
        counts["safety"] += 1
        return original_safety(data)

    monkeypatch.setattr(report_a, "_display_efficacy_rows", counted_efficacy)
    monkeypatch.setattr(report_a, "_display_safety_rows", counted_safety)
    render_report_a_site(_report(), tmp_path)

    assert counts == {"efficacy": 1, "safety": 1}
    assert (tmp_path / "data/report.js").is_file()
    assert (tmp_path / "products").is_dir()
