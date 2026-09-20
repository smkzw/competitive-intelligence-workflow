"""Browser source links on a synthetic but genuinely bound FreshA run."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.integration.test_fresh_a_scientific_review import _run_ready_project, _write_a_project


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [1440, 768, 390, 320])
def test_drawer_uses_bound_public_sources_not_source_categories(
    tmp_path: Path, engine: str, width: int,
) -> None:
    project = _write_a_project(tmp_path)
    _run_ready_project(project)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto((project / "reports/A/v1/html/efficacy.html").as_uri())
        page.locator('[data-chart-id="efficacy-full"] [data-a-product-focus]').first.click()
        drawer = page.locator("#a-product-insight-drawer")
        drawer.get_by_role("tab", name="数据依据", exact=True).click()
        panel = drawer.locator('[data-product-panel="evidence"]')
        link = panel.locator('a[href="https://clinicaltrials.gov/study/NCT00000001"]')
        assert link.count() == 1
        assert "已存测试记录" in link.inner_text()
        assert "报告级" in panel.inner_text()
        assert "发布日期：2026-07-01" in panel.inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        link.scroll_into_view_if_needed()
        link.evaluate("node => node.scrollIntoView({block: 'center', inline: 'nearest'})")
        bounds = link.bounding_box()
        assert bounds is not None and bounds["y"] >= 0
        assert bounds["y"] + bounds["height"] <= 900
        assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
        page.screenshot(path=str(tmp_path / f"source-drawer-{engine}-{width}.png"))
        browser.close()
