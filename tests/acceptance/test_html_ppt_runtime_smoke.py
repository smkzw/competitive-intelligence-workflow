from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import BrowserType, Page, ViewportSize, sync_playwright

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "html-ppt-runtime" / "index.html"
ECHARTS_PATH = ROOT / "tests" / "fixtures" / "offline-echarts" / "index.html"
FIXTURE_URL = FIXTURE_PATH.as_uri()
ECHARTS_URL = ECHARTS_PATH.as_uri()
EVIDENCE_ROOT = ROOT / "docs" / "acceptance" / "runs" / "8.4"
SCREENSHOT_DIR = EVIDENCE_ROOT / "screenshots"
LEDGER_PATH = EVIDENCE_ROOT / "browser-contract-ledger.json"
EVIDENCE_MD = EVIDENCE_ROOT / "browser-contract-evidence.md"

REMOTE_SCHEMES = ("http://", "https://", "ws://", "wss://")
REMOTE_ATTR = re.compile(r"""(?:src|href)\s*=\s*['"]https?://""", re.IGNORECASE)
BROWSERS = ("chromium", "webkit")
CANVAS_MATRIX: list[tuple[str, ViewportSize, str]] = [
    ("1280x720", {"width": 1280, "height": 720}, "1"),
    ("1600x900", {"width": 1600, "height": 900}, "1.25"),
    ("1920x1080", {"width": 1920, "height": 1080}, "1.5"),
    ("2048x1024", {"width": 2048, "height": 1024}, "1.4222222222222223"),
]


class PageAudit:
    def __init__(self, page: Page) -> None:
        self.remote: list[str] = []
        self.page_errors: list[str] = []
        self.console_errors: list[str] = []
        page.on(
            "request",
            lambda request: self.remote.append(request.url)
            if request.url.startswith(REMOTE_SCHEMES)
            else None,
        )
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: self.console_errors.append(message.text)
            if message.type == "error"
            else None,
        )


def _assert_file_url(page: Page) -> None:
    href = page.evaluate("location.href")
    assert href.startswith("file:"), href
    assert page.evaluate("location.protocol") == "file:"


def _assert_clean_audit(audit: PageAudit) -> None:
    assert audit.remote == []
    assert audit.page_errors == []
    assert audit.console_errors == []


def _assert_main_view(page: Page, *, expected_scale: str) -> None:
    page.goto(f"{FIXTURE_URL}#/2")
    page.locator(".slide.is-active").wait_for()
    _assert_file_url(page)
    assert page.locator(".slide.is-active").count() == 1
    assert page.locator(".slide.is-active h1").inner_text() == "主要疗效"
    assert page.locator(".slide.is-active .slide-number").inner_text() == "2 / 3"
    assert page.evaluate("location.hash") == "#/2"
    assert page.evaluate("document.querySelector('.deck').offsetWidth") == 1280
    assert page.evaluate("document.querySelector('.slide.is-active').offsetHeight") == 720
    actual_scale = page.evaluate(
        "document.documentElement.style.getPropertyValue('--deck-scale')"
    )
    assert actual_scale == expected_scale
    root_scale = page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--deck-scale').trim()"
    )
    assert root_scale == expected_scale
    formula_scale = page.evaluate(
        "String(Math.min(document.documentElement.clientWidth / 1280,"
        " document.documentElement.clientHeight / 720))"
    )
    assert actual_scale == formula_scale
    transform = page.evaluate(
        """() => {
          const deck = document.querySelector('.deck');
          const matrix = new DOMMatrixReadOnly(getComputedStyle(deck).transform);
          const rect = deck.getBoundingClientRect();
          return {
            a: matrix.a,
            b: matrix.b,
            c: matrix.c,
            d: matrix.d,
            centerErrorX: Math.abs(rect.left + rect.width / 2 - innerWidth / 2),
            centerErrorY: Math.abs(rect.top + rect.height / 2 - innerHeight / 2)
          };
        }"""
    )
    scale = float(expected_scale)
    assert abs(transform["a"] - scale) < 1e-5
    assert abs(transform["d"] - scale) < 1e-5
    assert abs(transform["b"]) < 1e-9
    assert abs(transform["c"]) < 1e-9
    assert transform["centerErrorX"] <= 0.5
    assert transform["centerErrorY"] <= 0.5
    progress_width = page.evaluate(
        "document.querySelector('.deck-progress span').style.width"
    )
    assert progress_width.startswith("66.")

    page.wait_for_function("window.__deck_chart_ready__ === true")
    assert page.locator("#efficacy-chart svg").count() == 1
    assert page.locator("#efficacy-chart canvas").count() == 0
    chart_text = page.locator("#efficacy-chart svg").text_content() or ""
    assert "竞品甲" in chart_text

    page.keyboard.press("Home")
    assert page.locator(".slide.is-active h1").inner_text() == "竞品格局"
    assert page.locator(".slide.is-active .slide-number").inner_text() == "1 / 3"
    assert page.evaluate("location.hash") == "#/1"

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


def _assert_presenter_view(page: Page) -> dict[str, str]:
    page.goto(FIXTURE_URL)
    page.locator(".slide.is-active").wait_for()
    with page.expect_popup() as popup_info:
        page.keyboard.press("s")
    presenter = popup_info.value
    presenter_audit = PageAudit(presenter)
    presenter.wait_for_load_state("domcontentloaded")
    presenter.locator("#current-title").wait_for()
    current_preview = presenter.frame_locator("#current-preview")
    next_preview = presenter.frame_locator("#next-preview")
    current_preview.locator(".slide.is-active h1").wait_for()
    next_preview.locator("#efficacy-chart svg").wait_for()
    assert current_preview.locator(".slide.is-active h1").inner_text() == "竞品格局"
    assert next_preview.locator(".slide.is-active h1").inner_text() == "主要疗效"
    assert presenter.title() == "演讲者视图"
    assert presenter.locator("#current-title").inner_text() == "竞品格局"
    assert presenter.locator("#next-title").inner_text() == "主要疗效"
    assert presenter.locator("#next-end").is_hidden()
    assert "本页说明竞品格局" in presenter.locator("#script").inner_text()
    assert presenter.locator("#page-detail").inner_text() == "第1页，共3页"
    assert presenter.locator("#timer").inner_text() == "00:00"
    assert presenter.get_by_role("button", name="上一页").count() == 1
    assert presenter.get_by_role("button", name="下一页").count() == 1
    assert presenter.get_by_role("button", name="重新计时").count() == 1
    presenter.get_by_role("button", name="下一页").click()
    assert presenter.locator("#current-title").inner_text() == "主要疗效"
    assert presenter.locator("#page-detail").inner_text() == "第2页，共3页"
    page.wait_for_function("() => location.hash === '#/2'")
    assert page.locator(".slide.is-active h1").inner_text() == "主要疗效"

    page.keyboard.press("ArrowRight")
    presenter.wait_for_function(
        "() => document.querySelector('#current-title')?.textContent === '安全性概览'"
    )
    assert page.evaluate("location.hash") == "#/3"
    assert presenter.locator("#page-detail").inner_text() == "第3页，共3页"
    assert presenter.locator("#next-title").inner_text() == ""
    assert presenter.locator("#next-end").is_visible()

    presenter.wait_for_timeout(1100)
    elapsed = presenter.locator("#timer").inner_text()
    assert elapsed != "00:00"
    page.keyboard.press("r")
    presenter.wait_for_function(
        "() => document.querySelector('#timer')?.textContent === '00:00'"
    )
    presenter.get_by_role("button", name="重新计时").click()
    assert presenter.locator("#timer").inner_text() == "00:00"
    snapshot = {
        "audience_hash": page.evaluate("location.hash"),
        "presenter_title": presenter.locator("#current-title").inner_text(),
        "presenter_page": presenter.locator("#page-detail").inner_text(),
    }
    _assert_clean_audit(presenter_audit)
    presenter.close()
    return snapshot


def _assert_preview(page: Page) -> None:
    page.goto(f"{FIXTURE_URL}?preview=3")
    page.locator(".slide.is-active").wait_for()
    _assert_file_url(page)
    assert page.locator(".slide.is-active h1").inner_text() == "安全性概览"
    assert page.evaluate("document.documentElement.dataset.preview") == "true"
    progress_display = page.locator(".deck-progress").evaluate(
        "el => getComputedStyle(el).display"
    )
    assert progress_display == "none"
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("n")
    page.keyboard.press("s")
    assert page.locator(".slide.is-active h1").inner_text() == "安全性概览"
    assert page.locator(".slide.is-active .slide-number").inner_text() == "3 / 3"
    assert page.evaluate("location.hash") in ("", "#/3")


def _assert_echarts(page: Page, url: str) -> None:
    page.goto(url)
    _assert_file_url(page)
    page.wait_for_function("window.__chart_ready__ === true")
    assert page.locator("#chart svg").count() == 1
    assert page.locator("#chart canvas").count() == 0
    svg_text = page.locator("#chart svg").text_content() or ""
    assert "竞品甲" in svg_text
    assert "主要终点变化值" in svg_text


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_runtime_sources_have_no_remote_asset_attributes() -> None:
    local_files = [
        ROOT / "assets" / "html-ppt" / "runtime.js",
        ROOT / "assets" / "html-ppt" / "runtime.css",
        FIXTURE_PATH,
        ECHARTS_PATH,
    ]
    for path in local_files:
        text = path.read_text(encoding="utf-8")
        assert REMOTE_ATTR.search(text) is None, path


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("viewport_name,viewport,expected_scale", CANVAS_MATRIX)
def test_offline_runtime_canvas_matrix_in_real_browsers(
    browser_name: str,
    viewport_name: str,
    viewport: ViewportSize,
    expected_scale: str,
) -> None:
    del viewport_name
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        browser = browser_type.launch()
        page = browser.new_page(viewport=viewport)
        audit = PageAudit(page)
        try:
            _assert_main_view(page, expected_scale=expected_scale)
            _assert_clean_audit(audit)
        finally:
            browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_offline_runtime_presenter_sync_in_real_browsers(browser_name: str) -> None:
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        browser = browser_type.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        audit = PageAudit(page)
        try:
            snapshot = _assert_presenter_view(page)
            assert snapshot["audience_hash"] == "#/3"
            assert snapshot["presenter_title"] == "安全性概览"
            _assert_clean_audit(audit)
        finally:
            browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_single_slide_preview_mode_hides_navigation_surfaces(browser_name: str) -> None:
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        browser = browser_type.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        audit = PageAudit(page)
        try:
            _assert_preview(page)
            _assert_clean_audit(audit)
        finally:
            browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_echarts_bundle_renders_real_offline_svg_chart(browser_name: str) -> None:
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        browser = browser_type.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        audit = PageAudit(page)
        try:
            _assert_echarts(page, ECHARTS_URL)
            _assert_clean_audit(audit)
        finally:
            browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_maximized_viewport_scale_follows_client_box(browser_name: str) -> None:
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        launch_args = ["--window-size=1920,1080"] if browser_name == "chromium" else []
        browser = browser_type.launch(args=launch_args)
        page = browser.new_page(viewport=None)
        audit = PageAudit(page)
        try:
            page.goto(f"{FIXTURE_URL}#/1")
            page.locator(".slide.is-active").wait_for()
            measured = page.evaluate(
                """() => {
                  const width = document.documentElement.clientWidth;
                  const height = document.documentElement.clientHeight;
                  return {
                    width,
                    height,
                    expected: String(Math.min(width / 1280, height / 720)),
                    actual: document.documentElement.style.getPropertyValue('--deck-scale'),
                    logicalWidth: document.querySelector('.deck').offsetWidth,
                    logicalHeight: document.querySelector('.slide.is-active').offsetHeight
                  };
                }"""
            )
            assert measured["logicalWidth"] == 1280
            assert measured["logicalHeight"] == 720
            assert measured["width"] > 0
            assert measured["height"] > 0
            assert measured["actual"] == measured["expected"]
            _assert_file_url(page)
            _assert_clean_audit(audit)
        finally:
            browser.close()


def test_browser_contract_writes_auditable_evidence_pack() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    shots: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []

    def capture(page: Page, name: str) -> str:
        path = SCREENSHOT_DIR / f"{name}.png"
        page.screenshot(path=str(path), full_page=False)
        digest = _sha256(path)
        shots.append(
            {
                "name": name,
                "path": str(path.relative_to(ROOT)),
                "sha256": digest,
                "bytes": path.stat().st_size,
            }
        )
        return digest

    with sync_playwright() as playwright:
        for browser_name in BROWSERS:
            browser_type: BrowserType = getattr(playwright, browser_name)
            browser = browser_type.launch()
            try:
                audience = browser.new_page(viewport={"width": 1280, "height": 720})
                audit = PageAudit(audience)
                audience.goto(f"{FIXTURE_URL}#/2")
                audience.locator(".slide.is-active").wait_for()
                audience.wait_for_function("window.__deck_chart_ready__ === true")
                capture(audience, f"{browser_name}-1280x720-slide-2")
                audience.keyboard.press("n")
                audience.locator(".deck-notes-drawer.is-open").wait_for()
                audience.wait_for_timeout(250)
                assert audience.locator(".slide.is-active h1").is_visible()
                assert audience.locator(".deck-notes-drawer__body").is_visible()
                capture(audience, f"{browser_name}-1280x720-notes")
                audience.keyboard.press("Escape")

                wide = browser.new_page(viewport={"width": 1920, "height": 1080})
                wide_audit = PageAudit(wide)
                wide.goto(FIXTURE_URL)
                wide.locator(".slide.is-active").wait_for()
                with wide.expect_popup() as popup_info:
                    wide.keyboard.press("s")
                presenter = popup_info.value
                presenter_audit = PageAudit(presenter)
                presenter.wait_for_load_state("domcontentloaded")
                presenter.locator("#current-title").wait_for()
                presenter.frame_locator("#current-preview").locator(
                    ".slide.is-active h1"
                ).wait_for()
                presenter.frame_locator("#next-preview").locator(
                    "#efficacy-chart svg"
                ).wait_for()
                popup_size = presenter.evaluate("() => [innerWidth, innerHeight]")
                assert popup_size == [1440, 900]
                capture(presenter, f"{browser_name}-1440x900-presenter")
                presenter.close()
                wide.close()

                echarts_page = browser.new_page(viewport={"width": 1280, "height": 720})
                echarts_audit = PageAudit(echarts_page)
                _assert_echarts(echarts_page, ECHARTS_URL)
                capture(echarts_page, f"{browser_name}-echarts-svg")
                echarts_page.close()

                _assert_clean_audit(audit)
                _assert_clean_audit(wide_audit)
                _assert_clean_audit(presenter_audit)
                _assert_clean_audit(echarts_audit)
                cases.append(
                    {
                        "browser": browser_name,
                        "fixture_href": audience.evaluate("location.href"),
                        "protocol": audience.evaluate("location.protocol"),
                        "remote_requests": (
                            audit.remote
                            + wide_audit.remote
                            + presenter_audit.remote
                            + echarts_audit.remote
                        ),
                        "page_errors": (
                            audit.page_errors
                            + wide_audit.page_errors
                            + presenter_audit.page_errors
                            + echarts_audit.page_errors
                        ),
                        "console_errors": (
                            audit.console_errors
                            + wide_audit.console_errors
                            + presenter_audit.console_errors
                            + echarts_audit.console_errors
                        ),
                    }
                )
                audience.close()
            finally:
                browser.close()

    ledger = {
        "task": "8.4",
        "worker": "worker_03",
        "not_acceptance": True,
        "recorded_at": datetime.now(UTC).isoformat(),
        "fixture_url": FIXTURE_URL,
        "echarts_url": ECHARTS_URL,
        "runtime_js_sha256": _sha256(ROOT / "assets" / "html-ppt" / "runtime.js"),
        "runtime_css_sha256": _sha256(ROOT / "assets" / "html-ppt" / "runtime.css"),
        "echarts_bundle_sha256": _sha256(
            ROOT / "assets" / "third-party" / "echarts" / "echarts.min.js"
        ),
        "viewports": [name for name, _viewport, _scale in CANVAS_MATRIX],
        "browsers": list(BROWSERS),
        "cases": cases,
        "screenshots": shots,
    }
    LEDGER_PATH.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    screenshot_lines = "\n".join(
        f"- `{item['path']}` `{item['sha256'][:12]}` ({item['bytes']} bytes)"
        for item in shots
    )
    evidence_body = "\n".join(
        [
            "# Task 8.4 HTML-PPT browser contract evidence",
            "",
            "Date: 2026-08-31",
            "Worker: `worker_03` (cursor / grok-4.6 fallback of grok-build)",
            (
                "Status: **not acceptance**. Codex remains the final authority "
                "for visual, PPT, clinical, and regulatory decisions."
            ),
            "",
            "## Contract covered",
            "",
            (
                "- Chromium and WebKit against 1280×720, 1600×900, "
                "1920×1080, 2048×1024."
            ),
            (
                "- Maximized-window *semantics*: `--deck-scale` equals unrounded "
                "`min(clientWidth/1280, clientHeight/720)` with logical canvas "
                "1280×720. Task 8.6 still owns native maximized-window visual "
                "acceptance."
            ),
            (
                "- `file://` protocol, zero `http(s)/ws(s)` requests, "
                "no page or console errors."
            ),
            (
                "- Audience ↔ presenter two-way sync, notes drawer, "
                "timer reset, `?preview=` freeze."
            ),
            (
                "- Offline ECharts SVG renderer (no canvas) in the runtime "
                "fixture and the standalone chart fixture."
            ),
            "",
            "## Recorded hashes",
            "",
            f"- `assets/html-ppt/runtime.js` `{ledger['runtime_js_sha256']}`",
            f"- `assets/html-ppt/runtime.css` `{ledger['runtime_css_sha256']}`",
            (
                "- `assets/third-party/echarts/echarts.min.js` "
                f"`{ledger['echarts_bundle_sha256']}`"
            ),
            f"- Ledger `{LEDGER_PATH.relative_to(ROOT)}`",
            "",
            "## Screenshots",
            "",
            screenshot_lines,
            "",
            "## Residual",
            "",
            "- Kangzhe visual master / FX injection is Task 8.5.",
            "- Native maximized-window visual pass is Task 8.6.",
            "",
        ]
    )
    EVIDENCE_MD.write_text(evidence_body + "\n", encoding="utf-8")
    assert LEDGER_PATH.is_file()
    assert EVIDENCE_MD.is_file()
    assert len(shots) >= 6
    for case in cases:
        assert case["protocol"] == "file:"
        assert case["remote_requests"] == []
        assert case["page_errors"] == []
        assert case["console_errors"] == []
