"""Ordinary A safety rendering keeps complete controls in compact disclosures.

HTML structure is a development check, not rendered visual acceptance.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site

ROOT = Path(__file__).resolve().parents[2]


class _FilterParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.groups: dict[str, dict[str, object]] = {}
        self.active: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        if "data-filter-dimension" in fields:
            self.active = str(fields["data-filter-dimension"])
            self.groups[self.active] = {"tag": tag, "attrs": fields, "values": []}
        if tag == "button" and self.active and "data-filter-value" in fields:
            values = self.groups[self.active]["values"]
            assert isinstance(values, list)
            values.append(fields["data-filter-value"])

    def handle_endtag(self, tag: str) -> None:
        if self.active and tag == self.groups[self.active]["tag"]:
            self.active = None


@pytest.mark.parametrize("count", [2, 8, 9])
def test_safety_filters_remain_compact_without_losing_options(
    tmp_path: Path, count: int,
) -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text()
    )
    seed = payload["safety"][0]
    payload["safety"] += [
        {**seed, "row_id": f"density-{index}", "category": f"安全维度{index}",
         "term": f"特定事件{index}", "term_key": None}
        for index in range(count)
    ]
    render_report_a_site(ReportAPortalData.model_validate(payload), tmp_path)
    parser = _FilterParser()
    html = (tmp_path / "safety.html").read_text()
    parser.feed(html)
    assert set(parser.groups) == {"product", "arm", "category", "event", "semantic"}
    for dimension, group in parser.groups.items():
        assert group["tag"] == "details", dimension
        attrs = group["attrs"]
        assert isinstance(attrs, dict)
        assert "open" not in attrs, dimension
        # Responsive legacy controls auto-open above 1100px; desktop compact does not.
        assert "data-responsive-filter" not in attrs, dimension
        assert int(str(attrs["data-filter-total"])) == len(group["values"])  # type: ignore[arg-type]
        assert f'data-filter-selection-count="{dimension}"' in html
    assert len(parser.groups["category"]["values"]) == count + 4  # type: ignore[arg-type]
    assert set(parser.groups["event"]["values"]) >= {  # type: ignore[arg-type]
        f"raw:特定事件{index}" for index in range(count)
    }
    assert html.count('data-row-id="density-') == count


def test_invented_typed_safety_key_is_rejected_not_silently_normalized(tmp_path: Path) -> None:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text()
    )
    payload["safety"].append({
        **payload["safety"][0], "row_id": "invalid-key", "term_key": "specific_event_0",
    })
    with pytest.raises(ValueError, match="term_key 不在受控 catalog"):
        render_report_a_site(ReportAPortalData.model_validate(payload), tmp_path)
