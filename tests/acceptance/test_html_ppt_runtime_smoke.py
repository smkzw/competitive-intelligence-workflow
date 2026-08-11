from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import BrowserType, Page, ViewportSize, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_URL = (ROOT / "tests" / "fixtures" / "html-ppt-runtime" / "index.html").as_uri()
ECHARTS_URL = (ROOT / "tests" / "fixtures" / "offline-echarts" / "index.html").as_uri()


def _assert_main_view(page: Page, *, expected_scale: str) -> None:
    page.goto(FIXTURE_URL)
    page.locator(".slide.is-active").wait_for()
    assert page.locator(".slide.is-active").count() == 1
    assert page.locator(".slide.is-active h1").inner_text() == "竞品格局"
    assert page.locator(".slide.is-active .slide-number").inner_text() == "1 / 3"
    actual_scale = page.evaluate(
        "document.querySelector('.deck').style.getPropertyValue('--deck-scale')"
    )
    assert actual_scale == expected_scale

    page.keyboard.press("ArrowRight")
    assert page.locator(".slide.is-active h1").inner_text() == "主要疗效"
    assert page.locator(".slide.is-active .slide-number").inner_text() == "2 / 3"
    assert page.evaluate("location.hash") == "#/2"

    page.keyboard.press("n")
    drawer = page.locator(".deck-notes-drawer")
    assert "is-open" in (drawer.get_attribute("class") or "")
    assert "主要终点及对照组效应" in drawer.inner_text()

    page.keyboard.press("Escape")
    assert "is-open" not in (drawer.get_attribute("class") or "")
    for removed_control in ("t", "a", "o"):
        page.keyboard.press(removed_control)
        assert page.locator(".slide.is-active h1").inner_text() == "主要疗效"

    page.keyboard.press("End")
    assert page.locator(".slide.is-active h1").inner_text() == "安全性概览"
    page.keyboard.press("Home")
    assert page.locator(".slide.is-active h1").inner_text() == "竞品格局"


def _assert_presenter_view(page: Page) -> None:
    page.goto(FIXTURE_URL)
    page.locator(".slide.is-active").wait_for()
    with page.expect_popup() as popup_info:
        page.keyboard.press("s")
    presenter = popup_info.value
    presenter.wait_for_load_state("domcontentloaded")
    presenter.locator("#current-title").wait_for()
    assert presenter.title() == "演讲者视图"
    assert presenter.locator("#current-title").inner_text() == "竞品格局"
    assert presenter.locator("#next-title").inner_text() == "主要疗效"
    assert "本页说明竞品格局" in presenter.locator("#script").inner_text()
    assert presenter.locator("#page-detail").inner_text() == "第1页，共3页"
    assert presenter.locator("#timer").inner_text() == "00:00"
    assert presenter.get_by_role("button", name="上一页").count() == 1
    assert presenter.get_by_role("button", name="下一页").count() == 1
    assert presenter.get_by_role("button", name="重新计时").count() == 1
    presenter.get_by_role("button", name="下一页").click()
    assert presenter.locator("#current-title").inner_text() == "主要疗效"
    assert presenter.locator("#page-detail").inner_text() == "第2页，共3页"
    presenter.close()


@pytest.mark.parametrize(
    ("browser_name", "viewport", "expected_scale"),
    [
        ("chromium", {"width": 1600, "height": 900}, "1.25"),
        ("webkit", {"width": 2048, "height": 1024}, "1.4222222222222223"),
    ],
)
def test_offline_runtime_navigation_and_presenter_view_in_real_browsers(
    browser_name: str,
    viewport: ViewportSize,
    expected_scale: str,
) -> None:
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        browser = browser_type.launch()
        page = browser.new_page(viewport=viewport)
        remote_requests: list[str] = []
        page.on(
            "request",
            lambda request: remote_requests.append(request.url)
            if request.url.startswith(("http://", "https://"))
            else None,
        )
        try:
            _assert_main_view(page, expected_scale=expected_scale)
            _assert_presenter_view(page)
            assert remote_requests == []
        finally:
            browser.close()


def test_single_slide_preview_mode_hides_navigation_surfaces() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        try:
            page.goto(f"{FIXTURE_URL}?preview=3")
            page.locator(".slide.is-active").wait_for()
            assert page.locator(".slide.is-active h1").inner_text() == "安全性概览"
            assert page.evaluate("document.documentElement.dataset.preview") == "true"
            progress_display = page.locator(".deck-progress").evaluate(
                "el => getComputedStyle(el).display"
            )
            assert progress_display == "none"
            page.keyboard.press("ArrowLeft")
            assert page.locator(".slide.is-active h1").inner_text() == "安全性概览"
        finally:
            browser.close()


@pytest.mark.parametrize("browser_name", ["chromium", "webkit"])
def test_echarts_bundle_renders_real_offline_svg_chart(browser_name: str) -> None:
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        browser = browser_type.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        remote_requests: list[str] = []
        page.on(
            "request",
            lambda request: remote_requests.append(request.url)
            if request.url.startswith(("http://", "https://"))
            else None,
        )
        try:
            page.goto(ECHARTS_URL)
            page.wait_for_function("window.__chart_ready__ === true")
            assert page.locator("#chart svg").count() == 1
            assert page.locator("#chart canvas").count() == 0
            svg_text = page.locator("#chart svg").text_content() or ""
            assert "竞品甲" in svg_text
            assert "主要终点变化值" in svg_text
            assert remote_requests == []
        finally:
            browser.close()
