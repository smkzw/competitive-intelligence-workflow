"""Personal controls remain keyboard-reachable without occupying the first screen."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("report", ["A", "B", "C"])
def test_collapsed_personal_controls_export_through_keyboard(tmp_path: Path, report: str) -> None:
    site = tmp_path / report
    if report == "A":
        project = tmp_path / "a-project"
        result = run_fixture_case(
            "a-complete", project_root=project, reports=["A"], outputs=["html"]
        )
        assert result.run_result.outcome == "completed"
        site = project / "reports/A/v-fixture-001/html"
    elif report == "B":
        data = ReportBPortalData.model_validate_json(
            (ROOT / "fixtures/positive/b-pnh/inputs/report-data.json").read_bytes()
        )
        render_report_b_site(data, site)
    else:
        c_data = ReportCPortalData.model_validate_json(
            (ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_bytes()
        )
        render_report_c_site(c_data, site)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=True, viewport={"width": 1600, "height": 900})
        page.goto((site / "overview.html").as_uri())
        outer = page.locator(
            "details.kz-a-workspace-bar" if report == "A" else "details#kz-filter-panel"
        )
        assert outer.get_attribute("open") is None
        outer.locator(":scope > summary").focus()
        page.keyboard.press("Enter")
        assert outer.get_attribute("open") is not None
        if report != "A":
            personal = page.locator(f"details.kz-{report.lower()}-personal")
            assert personal.get_attribute("open") is None
            personal.locator(":scope > summary").focus()
            page.keyboard.press("Enter")
            assert personal.get_attribute("open") is not None
        export = page.get_by_role("button", name="导出配置", exact=True)
        expect(export).to_be_visible()
        expect(page.get_by_role("button", name="导入配置", exact=True)).to_be_visible()
        export.focus()
        with page.expect_download() as downloaded:
            page.keyboard.press("Enter")
        saved = tmp_path / "personal.json"
        downloaded.value.save_as(saved)
        config = json.loads(saved.read_bytes())
        assert config["selections"][0]["report"] == report
        assert config["selections"][0]["revision"] == 0
        assert config["selections"][0]["entry_page"] == "overview.html"
        browser.close()
