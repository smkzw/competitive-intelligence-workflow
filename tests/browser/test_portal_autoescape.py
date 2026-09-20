"""Real-render Chromium regression for A/B/C HTML template escaping."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

ROOT = Path(__file__).resolve().parents[2]
TEXT = '审查文本<script>window.__AUTOESCAPE_TEXT__=1</script> & "原文"'
ATTRIBUTE = '靶点" onpointerenter="window.__AUTOESCAPE_ATTRIBUTE__=1" data-probe=" & < > \'原文\''
SNAPSHOT = "版本-\"单引号'与<&>"


@pytest.fixture(scope="module", params=("A", "B", "C"))
def escaped_site(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> tuple[str, Path]:
    kind = str(request.param)
    fixture = (
        "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
        if kind == "C"
        else "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    payload = json.loads((ROOT / fixture).read_text(encoding="utf-8"))
    payload["indication"] = TEXT
    payload["products"][0]["target"] = ATTRIBUTE
    site = tmp_path_factory.mktemp(f"autoescape-{kind}")
    if kind == "A":
        render_report_a_site(ReportAPortalData.model_validate(payload), site)
    elif kind == "B":
        payload["report_snapshot_id"] = SNAPSHOT
        render_report_b_site(ReportBPortalData.model_validate(payload), site)
    else:
        payload["report_snapshot_id"] = SNAPSHOT
        render_report_c_site(ReportCPortalData.model_validate(payload), site)
    return kind, site


@pytest.fixture
def portal_page(escaped_site: tuple[str, Path]) -> Iterator[Page]:
    kind, site = escaped_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # No authenticated profile or external requests are used by this regression.
        page.route("https://**/*", lambda route: route.abort())
        page.route("http://**/*", lambda route: route.abort())
        relative = "landscape.html" if kind == "A" else "overview.html"
        try:
            page.goto((site / relative).as_uri(), wait_until="load")
            yield page
            assert not errors, errors
        finally:
            browser.close()


def test_text_is_literal_and_cannot_execute_script(
    escaped_site: tuple[str, Path], portal_page: Page
) -> None:
    kind, _ = escaped_site
    assert portal_page.evaluate("window.__AUTOESCAPE_TEXT__ === undefined")
    selector = ".site-header__title" if kind == "A" else f".kz-{kind.lower()}-page-meta"
    assert TEXT in portal_page.locator(selector).inner_text()
    assert portal_page.locator(selector).locator("script").count() == 0


def test_filter_attribute_preserves_quotes_and_cannot_add_event_handler(
    portal_page: Page,
) -> None:
    button = (
        portal_page.locator('[data-filter-dimension="target"] button').filter(has_text="靶点").first
    )
    panel = portal_page.locator("details#kz-filter-panel")
    if panel.count():
        panel.locator("summary").first.click()
    button.dispatch_event("pointerenter")
    assert portal_page.evaluate("window.__AUTOESCAPE_ATTRIBUTE__ === undefined")
    assert button.get_attribute("onpointerenter") is None
    assert button.get_attribute("data-probe") is None
    assert button.get_attribute("data-filter-value") == ATTRIBUTE
    assert button.inner_text() == ATTRIBUTE


def test_json_and_explicit_safe_html_remain_functional(
    escaped_site: tuple[str, Path], portal_page: Page
) -> None:
    kind, _ = escaped_site
    assert portal_page.locator(".site-header nav a").count() > 0
    if kind == "A":
        # A's trusted Jinja macros must remain actual elements, not escaped markup.
        assert portal_page.evaluate("window.REPORT_A.indication") == TEXT
        assert portal_page.evaluate("window.REPORT_A.products[0].target") == ATTRIBUTE
        assert portal_page.locator(".kz-a-section-head button[data-open-evidence]").count() > 0
        assert portal_page.locator('[data-chart-id="landscape-full"] [data-product-id]').count() > 0
        return

    # Quotes, ampersands and angle brackets must survive the real |tojson slot.
    assert portal_page.evaluate("window.__SNAPSHOT_ID__") == SNAPSHOT
    assert portal_page.evaluate(f"window.__{kind}_PAGE_ID__") == "overview"
    assert portal_page.evaluate("Array.isArray(window.__CHART_GROUPS__)")
    assert portal_page.evaluate("window.__CHART_GROUPS__.length") > 0
    assert portal_page.locator("#kz-evidence-drawer").count() == 1
    assert portal_page.locator("#kz-chart-module canvas, #kz-chart-module svg").count() > 0
    # |safe evidence host/embed must still bind an operational drawer to a real row.
    portal_page.evaluate(
        """() => window.__EVIDENCE_DRAWER__.openByRowId(
            window.__EVIDENCE_VIEWS__[0].row.row_id, null
        )"""
    )
    assert portal_page.locator("#kz-evidence-drawer").is_visible()
