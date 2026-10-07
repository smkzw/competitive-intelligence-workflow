"""Ordinary A controls stay reachable without opening configuration by default."""

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site

ROOT = Path(__file__).resolve().parents[2]


class _ViewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.workspace = None
        self.rows: dict[str, list[str]] = {}
        self.active = None

    def handle_starttag(self, tag, attrs) -> None:
        fields = dict(attrs)
        if tag == "details" and "kz-a-workspace-bar" in fields.get("class", ""):
            self.workspace = fields
        if tag == "tr" and "data-row-id" in fields:
            self.active = fields["data-row-id"]
            self.rows[self.active] = []

    def handle_data(self, data: str) -> None:
        if self.active:
            self.rows[self.active].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr":
            self.active = None


@pytest.fixture
def rendered(tmp_path: Path):
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text()
    )
    payload["safety"][0].update(
        value=None, numerator=None, denominator=None,
        disclosure_state="用户清除，待重新核实",
    )
    payload["safety"][1].update(value=0.0, unit="人", numerator=0, denominator=60)
    payload["efficacy"][0].update(
        value=None, numerator=None, denominator=None, disclosure_state="user_cleared",
    )
    payload["efficacy"][1].update(
        value=None, numerator=None, denominator=None, disclosure_state="not_reported",
    )
    data = ReportAPortalData.model_validate(payload)
    render_report_a_site(data, tmp_path)
    html = (tmp_path / "safety.html").read_text()
    parser = _ViewParser()
    parser.feed(html)
    return data, html, parser


def test_workspace_configuration_is_collapsed_and_not_viewport_forced(rendered) -> None:
    _, html, parser = rendered
    assert parser.workspace is not None
    assert "open" not in parser.workspace
    assert "data-responsive-workspace" not in parser.workspace
    for hook in ("data-a-save-view", "data-a-clear-view", "data-a-view-status"):
        assert hook in html
    assert "视图与修订配置" in html


def test_clear_is_not_presented_as_source_non_disclosure(rendered) -> None:
    data, _, parser = rendered
    texts = parser.rows[data.safety[0].row_id]
    assert "用户清除，待重新核实" in " ".join(texts)
    assert "未公开" not in texts


def test_whole_number_display_preserves_explicit_zero_and_original_float(rendered) -> None:
    data, _, parser = rendered
    texts = parser.rows[data.safety[1].row_id]
    assert "0人" in texts
    assert "0.0人" not in texts
    assert data.safety[1].value == 0.0
    assert isinstance(data.safety[1].value, float)
    assert "0/60人" in texts


@pytest.mark.parametrize("collection,page", [
    ("safety", "safety.html"), ("efficacy", "efficacy.html"),
    ("safety", "product"), ("efficacy", "product"),
])
def test_cleared_current_value_is_consistent_in_summary_and_product_detail(
    rendered, tmp_path: Path, collection: str, page: str,
) -> None:
    data, _, _ = rendered
    row = getattr(data, collection)[0]
    relative = f"products/{row.product_id}.html" if page == "product" else page
    parser = _ViewParser()
    parser.feed((tmp_path / relative).read_text())
    assert row.row_id in parser.rows
    text = " ".join(parser.rows[row.row_id])
    assert "用户清除，待重新核实" in text
    assert "None" not in text and "未公开" not in text


def test_unknown_source_value_is_not_user_clear_and_keeps_its_source_state(
    rendered, tmp_path: Path,
) -> None:
    data, _, _ = rendered
    row = data.efficacy[1]
    for relative in ("efficacy.html", f"products/{row.product_id}.html"):
        parser = _ViewParser()
        parser.feed((tmp_path / relative).read_text())
        text = " ".join(parser.rows[row.row_id])
        assert "来源未列示" in text
        assert "None" not in text and "用户清除" not in text
