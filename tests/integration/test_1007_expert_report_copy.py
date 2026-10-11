"""Expert reports expose data, not repeated defensive instruction paragraphs."""

from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

ROOT = Path(__file__).resolve().parents[2]
BOILERPLATE = (
    "阅读边界", "证据限制", "条件与限制", "不等于", "不代表临床",
    "不代表数值可以共轴", "不构成完整", "不能作为已验科学结论",
    "描述性对照不等于头对头", "数值共轴资格另判",
)


@pytest.mark.parametrize("kind", ["a", "b", "c"])
def test_normal_renderer_does_not_publish_defensive_copy(kind, tmp_path):
    folder = {"a": "synthetic/a-complete", "b": "positive/b-pnh",
              "c": "positive/c-atopic-dermatitis"}[kind]
    fixture = ROOT / f"fixtures/{folder}/inputs/report-data.json"
    model, renderer = {
        "a": (ReportAPortalData, render_report_a_site),
        "b": (ReportBPortalData, render_report_b_site),
        "c": (ReportCPortalData, render_report_c_site),
    }[kind]
    data = model.model_validate_json(fixture.read_bytes())
    before = data.model_dump_json()
    site = tmp_path / kind
    options = {"review_candidate": True} if kind == "c" else {}
    renderer(data, site, **options)
    pages = list(site.rglob("*.html"))
    assert pages
    for page in pages:
        html = page.read_text()
        for phrase in BOILERPLATE:
            assert phrase not in html, (page.name, phrase)
        assert "external-sources" in html
    assert data.model_dump_json() == before


@pytest.mark.parametrize("asset", [
    "portal.js", "report-a.js", "report-b.js", "report-c.js", "evidence-drawer.js",
])
def test_shared_asset_copy_has_no_defensive_boilerplate(asset):
    source = (ROOT / "src/ci_workflow/renderers/portal/assets" / asset).read_text()
    # Source comments are implementation records, not report copy.
    quoted = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("//"))
    for phrase in BOILERPLATE:
        assert phrase not in quoted, (asset, phrase)
