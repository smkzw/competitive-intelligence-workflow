"""C homepage source-bound design findings (2026-10-11 expert-reading contract).

Root-family RED for the C overview summary:

- the homepage opens with concise design findings grouped from actual usable
  observations (randomisation/blinding architecture, primary endpoint
  assessment windows), not a generic collection count under 核心结论
- cleared, zero and unknown records never contribute a finding
- finding row IDs, source values and the summary/comparison navigation stay
  intact; long English definitions stay in the reachable detail views

Runs the ordinary production renderer end to end. Cleared-fact variants use
the real review-candidate entry because the current-delivery design gate
intentionally blocks pages whose core design facts are cleared.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.renderers.portal import report_c

ROOT = Path(__file__).resolve().parents[2]
REPORT_DATA = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
BLINDING_FIELD = "arm_randomization_blinding"
TIMEPOINT_FIELD = "primary_endpoint_timepoint"
BLINDING_ROW_IDS = (
    "c-nct02260986-grouping",
    "c-nct04178967-grouping",
    "c-nct03985943-grouping",
    "c-nct05149313-grouping",
)
TIMEPOINT_ROW_IDS = (
    "c-nct02260986-timepoint",
    "c-nct04178967-timepoint",
    "c-nct03985943-timepoint",
    "c-nct05149313-timepoint",
)

BLINDING_TEXT_FULL = (
    "各试验均为随机分配、平行分组；"
    "其中：三盲（NCT02260986）、"
    "四盲（NCT04178967、NCT03985943、NCT05149313）。"
)
BLINDING_TEXT_PARTIAL = (
    "NCT04178967、NCT03985943、NCT05149313：均为随机分配、平行分组、四盲。"
)
WINDOW_TEXT_UNIFORM = "各项试验的主要终点评估时间均为第16周。"
WINDOW_TEXT_GROUPED = (
    "主要终点评估时间：基线至第24周（NCT02260986）、"
    "第16周（NCT04178967、NCT03985943、NCT05149313）。"
)


def _load_data() -> report_c.ReportCPortalData:
    return report_c.ReportCPortalData.model_validate_json(REPORT_DATA.read_bytes())


def _with_row(
    data: report_c.ReportCPortalData, row_id: str, **updates: Any
) -> report_c.ReportCPortalData:
    observations = tuple(
        observation.model_copy(update=updates)
        if observation.row_id == row_id
        else observation
        for observation in data.observations
    )
    return data.model_copy(update={"observations": observations})


def _findings_section(html: str) -> str:
    match = re.search(r'<section[^>]*aria-label="设计概要"[^>]*>.*?</section>', html, re.S)
    assert match is not None, "homepage must render the 设计概要 design findings section"
    return match.group(0)


def _finding_items(section: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in re.findall(r"<li[^>]*>.*?</li>", section, re.S):
        label = re.search(r"<strong>(.*?)</strong>", block, re.S)
        text = re.search(r"<span>(.*?)</span>", block, re.S)
        items.append(
            {
                "label": label.group(1) if label else "",
                "text": text.group(1) if text else "",
                "row_ids": re.findall(r'data-evidence-open="([^"]+)"', block),
            }
        )
    return items


def _findings_by_label(section: str) -> dict[str, dict[str, Any]]:
    return {item["label"]: item for item in _finding_items(section)}


def _report_payload_observations(site: Path) -> dict[str, dict[str, Any]]:
    content = (site / "data/report.js").read_text(encoding="utf-8").strip()
    assert content.startswith("window.REPORT_C=")
    payload = json.loads(content[len("window.REPORT_C=") : -1])
    return {row["row_id"]: row for row in payload["observations"]}


def test_home_design_findings_are_source_bound_grouped_and_compact(tmp_path: Path) -> None:
    data = _load_data()
    site = tmp_path / "site"
    report_c.render_report_c_site(data, site)
    html = (site / "overview.html").read_text(encoding="utf-8")

    section = _findings_section(html)
    items = _finding_items(section)
    # Compact grouped findings, not one verbose row/card per observation.
    assert len(items) == 2

    blinding = _findings_by_label(section)["随机与盲法"]
    assert blinding["text"] == BLINDING_TEXT_FULL
    assert sorted(blinding["row_ids"]) == sorted(BLINDING_ROW_IDS)

    windows = _findings_by_label(section)["主要终点时间点"]
    assert windows["text"] == WINDOW_TEXT_UNIFORM
    assert sorted(windows["row_ids"]) == sorted(TIMEPOINT_ROW_IDS)

    # Long English definitions stay in reachable detail, not on the homepage.
    assert "allocation=" not in section
    assert "masking=" not in section

    # The old generic collection count must not survive anywhere on the page.
    assert "核心结论" not in html
    assert "比较范围" not in html
    assert "项注册试验" not in html

    # Finding row IDs are real observations, source values stay unmodified.
    payload = _report_payload_observations(site)
    fixture_rows = {
        row["row_id"]: row
        for row in json.loads(REPORT_DATA.read_text(encoding="utf-8"))["observations"]
    }
    for row_id in (*BLINDING_ROW_IDS, *TIMEPOINT_ROW_IDS):
        assert row_id in payload
        assert payload[row_id]["source_text"] == fixture_rows[row_id]["source_text"]
        assert (
            payload[row_id]["source_version_id"]
            == fixture_rows[row_id]["source_version_id"]
        )

    # Summary navigation and the first-level comparison entry stay intact.
    assert 'data-c-summary-only' in section
    assert re.search(r'href="[^"]*overview\.html\?view=comparison"', html)
    assert "data-c-enter-comparison" in html
    assert "打开全研究横比" in html


def test_home_design_findings_keep_distinct_assessment_windows(tmp_path: Path) -> None:
    data = _with_row(
        _load_data(),
        "c-nct02260986-timepoint",
        assessment_timepoint="Baseline, Week 24",
        source_text="Baseline, Week 24",
    )
    site = tmp_path / "site"
    report_c.render_report_c_site(data, site)
    section = _findings_section((site / "overview.html").read_text(encoding="utf-8"))

    windows = _findings_by_label(section)["主要终点时间点"]
    assert windows["text"] == WINDOW_TEXT_GROUPED

    blinding = _findings_by_label(section)["随机与盲法"]
    assert blinding["text"] == BLINDING_TEXT_FULL


def test_cleared_zero_and_unknown_records_never_become_findings(tmp_path: Path) -> None:
    data = _with_row(
        _load_data(),
        "c-nct02260986-grouping",
        disclosure_state=FactDisclosureState.USER_CLEARED,
    )
    data = _with_row(
        data,
        "c-nct04178967-timepoint",
        disclosure_state=FactDisclosureState.REPORTED_ZERO,
        reported_zero_text="0",
    )
    data = _with_row(
        data,
        "c-nct03985943-timepoint",
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
    )

    # Cleared core design facts intentionally block current delivery; the
    # review-candidate entry is the real production path that still renders.
    with pytest.raises(report_c.ReportCPortalError):
        report_c.render_report_c_site(data, tmp_path / "blocked")

    site = tmp_path / "candidate"
    report_c.render_report_c_site(data, site, review_candidate=True)
    section = _findings_section((site / "overview.html").read_text(encoding="utf-8"))
    by_label = _findings_by_label(section)

    blinding = by_label["随机与盲法"]
    assert blinding["text"] == BLINDING_TEXT_PARTIAL
    assert "c-nct02260986-grouping" not in blinding["row_ids"]
    assert sorted(blinding["row_ids"]) == sorted(set(BLINDING_ROW_IDS) - {
        "c-nct02260986-grouping",
    })

    windows = by_label["主要终点时间点"]
    assert windows["text"] == "主要终点评估时间：第16周（NCT02260986、NCT05149313）。"
    assert sorted(windows["row_ids"]) == sorted(set(TIMEPOINT_ROW_IDS) - {
        "c-nct04178967-timepoint",
        "c-nct03985943-timepoint",
    })

    # Placeholder states must not leak into the findings as pseudo facts.
    assert "已报告零值" not in section
    assert "用户清除" not in section
    assert "未公开" not in section


def test_no_usable_summary_records_renders_no_findings_and_no_fallback(tmp_path: Path) -> None:
    data = _load_data()
    for row_id in (*BLINDING_ROW_IDS, *TIMEPOINT_ROW_IDS):
        data = _with_row(
            data, row_id, disclosure_state=FactDisclosureState.USER_CLEARED
        )
    site = tmp_path / "candidate"
    report_c.render_report_c_site(data, site, review_candidate=True)
    html = (site / "overview.html").read_text(encoding="utf-8")

    assert 'aria-label="设计概要"' not in html
    # Without usable records the page must not fall back to the old count.
    assert "项注册试验" not in html
    assert "比较范围" not in html
    assert "核心结论" not in html

    # The rest of the homepage, including the comparison entry, stays intact.
    assert "打开全研究横比" in html
    assert "data-c-enter-comparison" in html


def test_home_current_user_edits_do_not_disappear_or_fall_back_to_source(tmp_path: Path) -> None:
    data = _with_row(_load_data(), "c-nct02260986-grouping",
                     review_state=FactReviewState.USER_MODIFIED,
                     display_text="allocation=RANDOMIZED; interventionModel=PARALLEL; masking=NONE")
    data = _with_row(data, "c-nct02260986-timepoint",
                     review_state=FactReviewState.USER_MODIFIED, display_text="Week 24")
    site = tmp_path / "current-edit"
    report_c.render_report_c_site(data, site, review_candidate=True)
    section = _findings_section((site / "overview.html").read_text())
    items = _findings_by_label(section)
    assert "开放标签（NCT02260986）" in items["随机与盲法"]["text"]
    assert "三盲" not in items["随机与盲法"]["text"]
    assert "第24周（NCT02260986）" in items["主要终点时间点"]["text"]
    assert "c-nct02260986-timepoint" in items["主要终点时间点"]["row_ids"]
    assert "用户修订" in section
    assert "<details" in section and "研究与依据" in section


def test_home_unknown_design_tokens_stay_in_original_detail_not_summary(tmp_path: Path) -> None:
    data = _with_row(_load_data(), "c-nct02260986-grouping",
                     display_text="allocation=RANDOMIZED; interventionModel=PARALLEL; "
                     "masking=UNKNOWN; " + "Original unreviewed English clause ".strip() * 8)
    site = tmp_path / "unknown-design"
    report_c.render_report_c_site(data, site, review_candidate=True)
    section = _findings_section((site / "overview.html").read_text())
    assert "Original unreviewed" not in section and "masking=UNKNOWN" not in section
    assert "随机分配" in section and "平行分组" in section
    payload = _report_payload_observations(site)
    assert "masking=UNKNOWN" in payload["c-nct02260986-grouping"]["display_text"]
