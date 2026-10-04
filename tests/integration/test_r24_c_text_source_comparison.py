"""Long C design clauses use the existing source-comparison DOM, not text heatmaps.

Calls the ordinary production projection and complete report-c.js startup in the
existing small Node DOM harness. Synthetic data is not clinical acceptance or
browser geometry evidence; actual Ego captures are required separately.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.renderers.portal import report_c
from tests.integration.test_r24_c_precedent_table import HARNESS_JS, ROOT

PAGES = ("endpoint-timepoint-matrix", "population-disease-definition", "treatment-arms")


@pytest.fixture(params=PAGES)
def comparison(request: pytest.FixtureRequest, tmp_path: Path) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node DOM behavior unavailable; not a browser/clinical PASS")
    data = report_c.ReportCPortalData.model_validate_json(
        (ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_bytes()
    )
    page_id = str(request.param)
    observations = report_c._page_observations(data, page_id)
    groups = json.loads(report_c._json(report_c._chart_groups(
        data, observations, page_id=page_id, title="开发条款"
    )))
    rows = [row for group in groups for row in group["rows"]]
    assert len(rows) >= 2
    rows[0]["source_location_zh"] = "研究方案与统计分析计划 · 开发来源定位"
    rows[0]["value"] = "不得混淆分析人群、访视或终点定义；" * 15
    rows[0]["review_state"] = "user_modified"
    rows[1]["value"] = None
    rows[1]["review_state"] = "user_modified"
    rows[1]["disclosure_state"] = "user_cleared"
    _, dimensions = report_c._filter_dimensions_for_rows(data, observations)
    payload = {
        "asset_path": str(ROOT / "src/ci_workflow/renderers/portal/assets/report-c.js"),
        "page_id": page_id,
        "chart_groups": groups,
        "table_rows": json.loads(report_c._json(report_c._table_rows(
            data, observations, page_id=page_id
        ))),
        "row_dimensions": dimensions,
        "filter_dimensions": tuple(report_c._FILTER_DIMENSION_LABELS),
        "first_trial": rows[0]["trial_display_id"],
        "search_query": rows[0]["trial_display_id"],
        "ordinal_query": "no-source-clause-matches-this-development-control",
    }
    payload_path = tmp_path / "input.json"
    original_bytes = json.dumps(payload, ensure_ascii=False).encode()
    payload_path.write_bytes(original_bytes)
    harness_path = tmp_path / "driver.cjs"
    harness_path.write_text(HARNESS_JS.replace(
        'win.__C_PAGE_ID__ = "inclusion-criteria";',
        "win.__C_PAGE_ID__ = page.page_id;",
    ))
    result = subprocess.run(
        [node, str(harness_path), str(payload_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)
    assert actual["ok"], actual.get("error")
    assert payload_path.read_bytes() == original_bytes
    return {"rows": rows, "snapshots": actual["snapshots"]}


def test_long_design_content_preserves_each_source_and_current_value(
    comparison: dict[str, Any],
) -> None:
    rows = comparison["rows"]
    initial = comparison["snapshots"]["initial"]
    assert initial["table_present"]
    definitions = {row["row_id"]: row for row in initial["defs"]}
    assert set(definitions) == {row["row_id"] for row in rows}
    assert set(initial["visible_table_rows"]) == set(definitions)
    for row in rows:
        definition = definitions[row["row_id"]]
        assert definition["original_text"] == row["source_text"].strip()
        assert definition["evidence_row_id"] == row["row_id"]
        assert definition["evidence_count"] == 1
    edited = definitions[rows[0]["row_id"]]
    assert rows[0]["value"] in edited["text"]
    assert "研究方案与统计分析计划" in edited["text"]
    assert "登记记录：研究方案" not in edited["text"]
    cleared = definitions[rows[1]["row_id"]]
    assert cleared["current_state"] == "user_cleared"
    assert "用户清除，待重新核实" in cleared["text"]


def test_search_study_choice_and_empty_state_do_not_shrink_input_universe(
    comparison: dict[str, Any],
) -> None:
    snapshots = comparison["snapshots"]
    rows = comparison["rows"]
    all_ids = {row["row_id"] for row in rows}
    first_trial = rows[0]["trial_display_id"]
    first_ids = {row["row_id"] for row in rows if row["trial_display_id"] == first_trial}
    for stage in ("initial", "clear", "ordinal_clear", "rechecked"):
        assert {row["row_id"] for row in snapshots[stage]["defs"]} == all_ids
    assert {row["row_id"] for row in snapshots["search"]["defs"]} == first_ids
    assert snapshots["ordinal"]["defs"] == []
    assert snapshots["ordinal"]["visible_table_rows"] == []
    assert {row["row_id"] for row in snapshots["unchecked"]["defs"]} == all_ids - first_ids
    assert snapshots["restore"]["defs"] == []
    assert "0" in snapshots["restore"]["status_text"]
