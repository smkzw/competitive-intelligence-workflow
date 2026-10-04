"""C reading chrome is compact while full data and personal configuration stay reachable."""

from pathlib import Path

from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

ROOT = Path(__file__).resolve().parents[2]


def test_personal_configuration_uses_existing_collapsed_filter_mount(tmp_path: Path) -> None:
    data = ReportCPortalData.model_validate_json(
        (ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_bytes()
    )
    render_report_c_site(data, tmp_path)
    for page_path in tmp_path.rglob("*.html"):
        page = page_path.read_text()
        panel = page.index('id="kz-filter-panel"')
        disclosure = page.index('<details class="kz-c-personal">')
        seam = page.index("kz-a-workspace-bar__actions")
        assert panel < disclosure < seam
        assert " open" not in page[disclosure:page.index(">", disclosure)]
        assert page.count("kz-a-workspace-bar__actions") == 1
        assert "data-filter-summary" in page[:disclosure]
        assert "data-filter-reset" in page and "global-search-input" in page
