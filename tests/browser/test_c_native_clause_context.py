"""Actual ordinary C source panel displays native continuation and scoped differences."""

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.integration.test_r24_c_clause_context import build_candidate


@pytest.fixture(scope="module")
def candidate(tmp_path_factory):
    return build_candidate(tmp_path_factory.mktemp("native-context-browser"))


@pytest.mark.parametrize("browser_name", ["chromium", "webkit"])
def test_native_statistical_panel_keeps_scope_and_separate_page_quotes(candidate, browser_name):
    output, manifest, data = candidate
    site = output / manifest["site_relative_path"]
    with sync_playwright() as playwright:
        browser = getattr(playwright, browser_name).launch()
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.goto((site / "sample-analysis-statistics.html").as_uri())
        target = next(r for r in data.observations if r.source_row_id.endswith(
            "prot-p62-efficacy-analysis-part2"
        ))
        fragment = next(r for r in data.observations if r.source_row_id.endswith(
            "sap-p24-concomitant-conservative-lead-in"
        ))
        item = page.locator(f'[data-criterion-row-id="{fragment.row_id}"]')
        current = item.locator(".kz-c-design-source-value")
        expect(current).to_have_text("来源条款：" + fragment.source_clause_context.label_zh)
        expect(item.locator(".kz-c-criteria-source")).to_have_text("查看来源与跨页前后文")
        item.locator(".kz-c-criteria-def-fold > summary").click()
        expect(item.locator(".kz-c-criteria-original")).to_have_text(fragment.source_text)
        expect(item).to_contain_text("跨页条款，前后文各页分别定位")
        from ci_workflow.renderers.portal.report_c import _page_observations

        expected_ids = {r.row_id for r in _page_observations(data, "sample-analysis-statistics")}
        assert set(page.evaluate("window.__C_VISIBLE_CHART_ROW_IDS__")) == expected_ids
        search = page.locator("#kz-c-criteria-search")
        search.fill("合并用药日期缺失")
        expect(item).to_be_visible()
        assert fragment.row_id in page.evaluate("window.__C_VISIBLE_CHART_ROW_IDS__")
        search.fill("")
        assert set(page.evaluate("window.__C_VISIBLE_CHART_ROW_IDS__")) == expected_ids
        trigger = page.locator(f'button[data-evidence-open][data-row-id="{target.row_id}"]').first
        trigger.click()
        panel = page.locator("#kz-evidence-drawer")
        expect(panel).to_be_visible()
        expect(panel).to_contain_text("不适用于§12.5安全性")
        expect(panel).to_contain_text("跨页前后文（各页分别定位）")
        quotes = panel.locator(".kz-evidence-quote")
        assert target.source_text in quotes.all_text_contents()
        continuation = target.source_clause_context.continuations[0]
        assert continuation.original_text in quotes.all_text_contents()
        assert panel.locator('a[href="' + continuation.locator.url + '"]').count() > 0
        page.keyboard.press("Escape")
        expect(trigger).to_be_focused()
        conflict_row = next(r for r in data.observations if r.source_row_id.endswith(
            "sap-p26-facit-cohort4-ttest"
        ))
        page.locator(f'button[data-evidence-open][data-row-id="{conflict_row.row_id}"]').first.click()
        expect(panel.locator("#kz-evidence-view-conflicts")).to_be_visible()
        expect(panel).to_contain_text("no formal statistical testing")
        assert panel.locator(".kz-evidence-conflict").count() > 0
        browser.close()
