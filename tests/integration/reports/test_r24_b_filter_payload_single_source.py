"""B filter lookup is derived from one offline literal, with all dimensions intact."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site


@pytest.mark.parametrize("row_id", ("ordinary", "__proto__", "constructor", "fact:中文-2"))
def test_filter_lookup_preserves_dimensions_without_a_duplicate_literal(
    tmp_path: Path, row_id: str,
) -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["efficacy"][0]["row_id"] = row_id
    site = tmp_path / "site"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    html = (site / "efficacy.html").read_text(encoding="utf-8")
    match = re.search(r"<script>(window\.__SNAPSHOT_ID__.*?)</script>", html, re.S)
    assert match is not None
    script = match.group(1)
    result = subprocess.run(
        ["node", "-e", (
            "var window={};" + script
            + ";console.log(JSON.stringify({rows:window.__FILTER_ROWS__,"
            "lookup:window.__B_ROW_DIMENSIONS__,"
            "nullPrototype:Object.getPrototypeOf(window.__B_ROW_DIMENSIONS__)===null}));"
        )],
        check=True, capture_output=True, text=True,
    )
    actual = json.loads(result.stdout)
    expected = {
        row["id"]: {key: value for key, value in row.items() if key != "id"}
        for row in actual["rows"]
    }
    assert actual["lookup"] == expected
    assert row_id in actual["lookup"]
    assert actual["nullPrototype"] is True
    assert "window.__B_ROW_DIMENSIONS__ = {" not in script
    # The full query remains present. Reduction must not truncate rows or fields.
    assert len(actual["rows"]) == len(payload["efficacy"])
