"""Task 8.5：A/B/C HTML-PPT file:// Chromium/WebKit 基础合同。"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import BrowserType, sync_playwright

from ci_workflow.renderers.html_ppt.projections.a import build_report_a_html_ppt
from ci_workflow.renderers.html_ppt.projections.b import build_report_b_html_ppt
from ci_workflow.renderers.html_ppt.projections.c import build_report_c_html_ppt

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
BROWSERS = ("chromium", "webkit")
REMOTE_SCHEMES = ("http://", "https://", "ws://", "wss://")
BUILDERS = {
    "A": build_report_a_html_ppt,
    "B": build_report_b_html_ppt,
    "C": build_report_c_html_ppt,
}
TITLES = {
    "A": "特应性皮炎竞品全景",
    "B": "阵发性睡眠性血红蛋白尿临床试验结果比较",
    "C": "中重度特应性皮炎临床试验设计比较",
}


@pytest.fixture(scope="module")
def decks(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    folder = tmp_path_factory.mktemp("html-ppt-85")
    out: dict[str, Path] = {}
    for report, builder in BUILDERS.items():
        out[report] = builder(output_path=folder / f"report-{report.lower()}.html", root=ROOT)
    return out


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("report", ["A", "B", "C"])
def test_html_ppt_file_url_runtime_in_real_browsers(
    browser_name: str, report: str, decks: dict[str, Path]
) -> None:
    path = decks[report]
    remote: list[str] = []
    page_errors: list[str] = []
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser_type: BrowserType = getattr(playwright, browser_name)
        browser = browser_type.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.on(
            "request",
            lambda request: remote.append(request.url)
            if request.url.startswith(REMOTE_SCHEMES)
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.goto(path.as_uri())
        page.locator(".slide.is-active").wait_for()
        assert page.evaluate("location.protocol") == "file:"
        assert page.evaluate("document.querySelector('.deck').offsetWidth") == 1280
        assert page.evaluate("document.querySelector('.slide.is-active').offsetHeight") == 720
        title = page.locator(".slide.is-active h1").inner_text()
        assert TITLES[report] in title or title in {TITLES[report], "谢谢", "目录"}
        page.keyboard.press("ArrowRight")
        page.locator(".slide.is-active").wait_for()
        page.wait_for_timeout(900)
        page_number = page.locator(".slide.is-active .slide-number")
        if page_number.count():
            assert page_number.inner_text() == f"2 / {len(page.locator('.slide'))}"
            assert page_number.evaluate(
                "el => getComputedStyle(el, '::before').content === 'none'"
            )
            assert page_number.evaluate(
                "el => getComputedStyle(el, '::after').content === 'none'"
            )
        page.keyboard.press("n")
        drawer = page.locator(".deck-notes-drawer")
        drawer.wait_for()
        assert "is-open" in (drawer.get_attribute("class") or "")
        assert page.evaluate("location.hash") in {"#/2", "#/1"}
        assert remote == []
        assert page_errors == []
        assert console_errors == []
        browser.close()


OVERFLOW_JS = """() => {
  const slide = document.querySelector('.slide.is-active');
  const box = slide.getBoundingClientRect();
  const issues = [];
  const sel = 'h1,h3,p,.disclosure-row,.kz-card,.stat-strip,.content-conclusion';
  const nodes = slide.querySelectorAll(sel);
  for (const el of nodes) {
    if (el.closest('aside.notes')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    if (r.right > box.right + 2.5 || r.bottom > box.bottom + 2.5) {
      issues.push(slide.dataset.slideId + ':' + (el.className || el.tagName) + ':overflow');
    }
    if (el.scrollWidth > el.clientWidth + 4 && !el.closest('svg')) {
      issues.push(slide.dataset.slideId + ':' + (el.className || el.tagName) + ':clip');
    }
  }
  return issues;
}"""


@pytest.mark.parametrize('report', ['A', 'B', 'C'])
def test_html_ppt_active_slide_geometry(report: str, decks: dict[str, Path]) -> None:
    path = decks[report]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.goto(path.as_uri())
        page.locator('.slide.is-active').wait_for()
        seen: list[str] = []
        issues: list[str] = []
        while True:
            slide_id = page.evaluate("document.querySelector('.slide.is-active').dataset.slideId")
            if slide_id in seen:
                break
            seen.append(slide_id)
            page.wait_for_timeout(900)
            issues.extend(page.evaluate(OVERFLOW_JS))
            page.keyboard.press('ArrowRight')
            page.locator('.slide.is-active').wait_for()
        browser.close()
    assert issues == [], issues
    assert len(seen) >= 15
