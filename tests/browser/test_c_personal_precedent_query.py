"""C precedent keyword/column configuration is portable, not local-storage-only."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from ci_workflow.application.share_export import ShareViewSelection, _validate_view_selection
from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site
from tests.browser.test_personal_view_transfer import _open_personal_controls

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def c_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    data = ReportCPortalData.model_validate_json(
        (ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_bytes()
    )
    site = tmp_path_factory.mktemp("c-personal-precedent") / "html"
    render_report_c_site(data, site)
    return site


@pytest.mark.parametrize("browser_name", ["chromium", "webkit"])
def test_c_keyword_and_study_columns_export_import_and_reuse(
    tmp_path: Path, c_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = getattr(playwright, browser_name).launch()
        page = browser.new_page(accept_downloads=True, viewport={"width": 1600, "height": 900})
        page.goto((c_site / "inclusion-criteria.html").as_uri()
                  + "?criteria_q=EASI&criteria_hide=NCT02260986")
        assert page.locator("#kz-c-criteria-search").input_value() == "EASI"
        _open_personal_controls(page)
        with page.expect_download() as download:
            page.get_by_role("button", name="导出配置", exact=True).click()
        saved = tmp_path / "precedent.json"
        download.value.save_as(saved)
        config = json.loads(saved.read_bytes())
        assert config["selections"][0]["query"] == {
            "criteria_q": ["EASI"], "criteria_hide": ["NCT02260986"],
        }
        _validate_view_selection(
            ShareViewSelection.model_validate(config["selections"][0]),
            (c_site / "inclusion-criteria.html").read_bytes(),
        )
        fresh = browser.new_context(viewport={"width": 1600, "height": 900})
        target = fresh.new_page()
        target.goto((c_site / "inclusion-criteria.html").as_uri())
        assert target.evaluate("() => localStorage.length") == 0
        _open_personal_controls(target)
        target.locator('input[aria-label="选择个人视图 JSON 文件"]').set_input_files(saved)
        target.wait_for_url("**/inclusion-criteria.html?**criteria_q=EASI**", timeout=5000)
        assert target.locator("#kz-c-criteria-search").input_value() == "EASI"
        assert not target.locator('input[value="NCT02260986"]').is_checked()
        target.goto((c_site / "exclusion-criteria.html").as_uri())
        assert target.locator("#kz-c-criteria-search").input_value() == "EASI"
        assert "criteria_hide=NCT02260986" in target.url
        assert not target.locator('input[value="NCT02260986"]').is_checked()
        fresh.close()
        browser.close()


@pytest.mark.parametrize("browser_name", ["chromium", "webkit"])
def test_c_statistical_text_is_source_comparison_not_sample_size_axis(
    c_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = getattr(playwright, browser_name).launch()
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.goto((c_site / "sample-analysis-statistics.html").as_uri())
        module = page.locator("#kz-chart-module")
        assert module.locator("#kz-c-criteria-search").count() == 1
        rows = module.locator("[data-criterion-row-id]")
        assert rows.count() == 8
        assert module.locator(".kz-c-chart-canvas svg").count() == 0
        assert "740" in module.inner_text()
        assert "样本量与统计分析原文对照" in module.inner_text()
        assert len(set(rows.evaluate_all("nodes => nodes.map(n => n.dataset.criterionRowId)"))) == 8
        browser.close()
