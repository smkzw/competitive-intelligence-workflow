"""B portal page payloads: external matrix/evidence script, compact share inventory."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ci_workflow.application.share_export import (
    ShareViewSelection,
    _FilterInventory,
    _validate_view_selection,
)
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json"

_LARGE_INLINE = (
    "window.__FILTER_ROWS__ = [",
    "window.__CHART_GROUPS__ = [",
    "window.__B_COMPARISON_WORKSPACE__ = {",
    "window.__EVIDENCE_VIEWS__ = [",
)


def _payload_paths(page: Path) -> list[Path]:
    return [(page.parent / reference).resolve() for reference in re.findall(
        r'<script src="([^"]*data/shared-payloads/[^"]+\.js)"></script>',
        page.read_text(encoding="utf-8"),
    )]


def test_identical_payload_components_are_stored_once_across_physical_pages(tmp_path):
    site = tmp_path / "B"
    render_report_b_site(ReportBPortalData.model_validate_json(FIXTURE.read_bytes()), site)
    references = [_payload_paths(page) for page in site.rglob("*.html")]
    assert all(len(paths) == 4 for paths in references)
    all_paths = [path for paths in references for path in paths]
    unique_paths = set(all_paths)
    assert len(unique_paths) < len(all_paths)
    assert all(path.is_file() and path.is_relative_to(site) for path in unique_paths)
    assert sum(path.stat().st_size for path in unique_paths) < sum(
        path.stat().st_size for path in all_paths)


def _assignment(source: str, name: str) -> object:
    marker = f"window.{name} = "
    pos = source.find(marker)
    assert pos >= 0, name
    value, _end = json.JSONDecoder().raw_decode(source[pos + len(marker) :])
    return value


def test_b_page_payload_externalizes_matrix_evidence_and_keeps_share_inventory(
    tmp_path: Path,
) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    site = tmp_path / "B"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)

    overview = site / "overview.html"
    overview_html = overview.read_text(encoding="utf-8")
    for fragment in _LARGE_INLINE:
        assert fragment not in overview_html

    assert "window.__B_COMPARISON_QUERY_INVENTORY__ = " in overview_html
    inventory = _assignment(overview_html, "__B_COMPARISON_QUERY_INVENTORY__")
    assert isinstance(inventory, dict) and inventory

    paths = _payload_paths(overview)
    assert len(paths) == 4
    page_js = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    filter_rows = _assignment(page_js, "__FILTER_ROWS__")
    chart_groups = _assignment(page_js, "__CHART_GROUPS__")
    workspace = _assignment(page_js, "__B_COMPARISON_WORKSPACE__")
    evidence = _assignment(page_js, "__EVIDENCE_VIEWS__")
    assert isinstance(filter_rows, list) and filter_rows
    assert isinstance(chart_groups, list) and chart_groups
    assert isinstance(workspace, dict) and workspace.get("columns")
    assert isinstance(evidence, list) and evidence

    chart_ids = {
        row["row_id"]
        for group in chart_groups
        for row in group.get("rows", [])
        if isinstance(row, dict) and row.get("row_id")
    }
    evidence_ids = {
        view["row"]["row_id"]
        for view in evidence
        if isinstance(view, dict)
        and isinstance(view.get("row"), dict)
        and view["row"].get("row_id")
    }
    filter_ids = {row["id"] for row in filter_rows if isinstance(row, dict) and "id" in row}
    member_ids = set(workspace["membership"]["row_ids"])
    assert chart_ids
    assert chart_ids <= evidence_ids
    assert member_ids <= filter_ids
    assert member_ids <= evidence_ids

    expected_inventory: dict[str, int] = {}
    for column in workspace["columns"]:
        question = column["question_id"]
        expected_inventory[question] = expected_inventory.get(question, 0) + 1
    assert inventory == expected_inventory

    parser = _FilterInventory()
    parser.feed(overview_html)
    assert parser.comparison is True
    assert parser.comparison_questions("B") == expected_inventory

    question = sorted(expected_inventory)[0]
    columns = expected_inventory[question]
    last_page = str(max(1, (columns + 3) // 4))
    _validate_view_selection(
        ShareViewSelection(
            report="B",
            revision=0,
            entry_page="overview.html",
            query={
                "view": ("comparison",),
                "cmp": (question,),
                "cmp_page": (last_page,),
            },
        ),
        overview.read_bytes(),
    )

    product = payload["products"][0]["id"]
    nested = site / "products" / f"{product}.html"
    nested_html = nested.read_text(encoding="utf-8")
    for fragment in _LARGE_INLINE:
        assert fragment not in nested_html
    nested_paths = _payload_paths(nested)
    assert len(nested_paths) == 4
    assert all(path.is_file() and path.is_relative_to(site) for path in nested_paths)

    html_bytes = sum(path.stat().st_size for path in site.rglob("*.html"))
    payload_bytes = sum(
        path.stat().st_size for path in (site / "data/shared-payloads").rglob("*.js")
    )
    assert payload_bytes > 0
    # Comparable input: large row/evidence JSON lives once in page scripts, not HTML.
    assert html_bytes < payload_bytes or all(
        fragment not in path.read_text(encoding="utf-8")
        for path in site.rglob("*.html")
        for fragment in _LARGE_INLINE
    )


@pytest.mark.parametrize(
    "query",
    [
        {"view": ("unknown",)},
        {"cmp": ("missing-question",)},
        {"cmp_page": ("999",)},
    ],
)
def test_b_share_inventory_rejects_unknown_comparison_query(
    tmp_path: Path, query: dict[str, tuple[str, ...]]
) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    site = tmp_path / "B"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    page = (site / "overview.html").read_bytes()
    with pytest.raises(ValueError):
        _validate_view_selection(
            ShareViewSelection(report="B", revision=0, query=query),
            page,
        )
