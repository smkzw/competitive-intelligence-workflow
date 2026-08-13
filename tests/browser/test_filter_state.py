"""Task 4.3 筛选面板与 URL 状态浏览器验收测试。

覆盖：
- 筛选面板渲染、键盘可达、中文标签、全页/本模块分区
- URL hash 同步（encode → decode → refresh → back/forward）
- 页面重置与模块重置互不污染
- 空结果状态、限制回显、重置按钮
- Chromium + WebKit × 1280/1440/1920 × file:// + static server；1024 代表路径
- 无 console/page 错误、无远程请求、reduced-motion、焦点返回
"""

from __future__ import annotations

import http.server
import re
import socket
import sys
import threading
from pathlib import Path
from typing import Any, cast
from urllib.request import pathname2url

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = ROOT / ".artifacts" / "task43-portal" / "current" / "screenshots"

SYNTHETIC_ROWS: list[dict[str, str]] = [
    {
        "id": "row-001",
        "module_id": "b-efficacy",
        "product": "product-alpha",
        "indication": "ind-sle",
        "target_or_mechanism": "target-baff",
        "trial": "trial-001",
        "product_label": "产品甲",
        "trial_label": "NCT00000001",
        "endpoint": "ep-pri",
        "label": "疗效 · 产品甲 · 主要终点",
    },
    {
        "id": "row-002",
        "module_id": "b-efficacy",
        "product": "product-beta",
        "indication": "ind-sle",
        "target_or_mechanism": "target-cd20",
        "trial": "trial-002",
        "product_label": "产品乙",
        "trial_label": "NCT00000002",
        "endpoint": "ep-pri",
        "label": "疗效 · 产品乙 · 主要终点",
    },
    {
        "id": "row-003",
        "module_id": "b-efficacy",
        "product": "product-alpha",
        "indication": "ind-ra",
        "target_or_mechanism": "target-baff",
        "trial": "trial-003",
        "product_label": "产品甲",
        "trial_label": "NCT00000003",
        "endpoint": "ep-sec",
        "label": "疗效 · 产品甲 · 次要终点",
    },
    {
        "id": "row-004",
        "module_id": "b-safety",
        "product": "product-gamma",
        "indication": "ind-sle",
        "target_or_mechanism": "target-jak",
        "trial": "trial-004",
        "product_label": "产品丙",
        "trial_label": "NCT00000004",
        "ae_term": "ae-teae",
        "label": "安全 · 产品丙 · 治疗期不良事件",
    },
    {
        "id": "row-005",
        "module_id": "b-safety",
        "product": "product-beta",
        "indication": "ind-ra",
        "target_or_mechanism": "target-cd20",
        "trial": "trial-005",
        "product_label": "产品乙",
        "trial_label": "NCT00000005",
        "ae_term": "ae-sae",
        "label": "安全 · 产品乙 · 严重不良事件",
    },
]

FILTER_GROUPS: list[dict[str, Any]] = [
    {
        "title": "适应症",
        "scope": "page",
        "items": [
            {"id": "ind-sle", "label": "系统性红斑狼疮", "dim": "indication"},
            {"id": "ind-ra", "label": "类风湿关节炎", "dim": "indication"},
        ],
    },
    {
        "title": "产品",
        "scope": "page",
        "items": [
            {"id": "product-alpha", "label": "产品甲", "dim": "product"},
            {"id": "product-beta", "label": "产品乙", "dim": "product"},
            {"id": "product-gamma", "label": "产品丙", "dim": "product"},
            {
                "id": "x" * 2500,
                "label": "超长标识测试项",
                "dim": "product",
                "test_only": True,
            },
        ],
    },
    {
        "title": "靶点或机制",
        "scope": "page",
        "items": [
            {"id": "target-baff", "label": "BAFF", "dim": "target_or_mechanism"},
            {"id": "target-cd20", "label": "CD20", "dim": "target_or_mechanism"},
            {"id": "target-jak", "label": "JAK", "dim": "target_or_mechanism"},
        ],
    },
    {
        "title": "终点",
        "scope": "module",
        "module_id": "b-efficacy",
        "module_label": "疗效数据",
        "items": [
            {"id": "ep-pri", "label": "主要终点", "dim": "endpoint"},
            {"id": "ep-sec", "label": "次要终点", "dim": "endpoint"},
        ],
    },
    {
        "title": "不良事件术语",
        "scope": "module",
        "module_id": "b-safety",
        "module_label": "安全性数据",
        "items": [
            {"id": "ae-teae", "label": "治疗期不良事件", "dim": "ae_term"},
            {"id": "ae-sae", "label": "严重不良事件", "dim": "ae_term"},
        ],
    },
    {
        "title": "分母角色",
        "scope": "module",
        "module_id": "b-efficacy",
        "module_label": "疗效数据",
        "advanced": True,
        "items": [
            {"id": "den-safety", "label": "安全性人群", "dim": "denominator_role"},
            {"id": "den-itt", "label": "意向性治疗人群", "dim": "denominator_role"},
        ],
    },
]

BROWSERS = ["chromium", "webkit"]
DESKTOP_WIDTHS = [1280, 1440, 1920]
DESKTOP_PARAMS = [(browser, width) for browser in BROWSERS for width in DESKTOP_WIDTHS]

FORBIDDEN_VOCAB = re.compile(
    r"query[_-]?builder|backend|schema|SQL|api[_-]?call|fetch|async|debug|trace",
    re.IGNORECASE,
)


def _build_portal_with_filters(tmp_path: Path) -> Path:
    """Build a minimal portal page with filter panel and synthetic rows."""
    from ci_workflow.renderers.portal.builder import (
        NavEntry,
        PageSpec,
        PortalSpec,
        build_portal,
    )
    from ci_workflow.renderers.portal.page_shell import render_page_html

    row_rows: list[str] = []
    for row in SYNTHETIC_ROWS:
        row_rows.append(
            f'        <tr id="filter-row-{row["id"]}" '
            f'data-filter-row-id="{row["id"]}" '
            f'data-module-id="{row["module_id"]}">'
            f'<td>{row["label"]}</td>'
            f'<td>{row.get("product_label", row["product"])}</td>'
            f'<td>{row.get("trial_label", row["trial"])}</td>'
            f"</tr>"
        )
    row_table = (
        '    <div id="kz-filter-row-table">\n'
        "      <table><thead><tr><th>名称</th><th>产品</th><th>试验</th></tr></thead>\n"
        "      <tbody>\n"
        + "\n".join(row_rows)
        + "\n      </tbody></table>\n    </div>"
    )

    body_text = (
        "选择适应症、产品和终点，快速查看对应的竞品临床试验数据。"
    )

    spec = PortalSpec(
        title="系统性红斑狼疮竞品研究",
        footer_text="竞品临床试验数据",
        pages=[
            PageSpec(
                slug="filter-test",
                title="竞品数据筛选",
                nav_label="竞品数据",
                nav_group="总览",
                sections=["疗效数据", "安全性数据"],
                body_text=body_text,
            ),
        ],
        nav=[
            NavEntry(slug="filter-test", label="竞品数据", group="总览"),
        ],
    )

    out = tmp_path / "portal"
    build_portal(spec, out)

    page = spec.pages[0]
    html = render_page_html(
        page=page,
        spec=spec,
        assets_rel="assets",
        filter_groups=FILTER_GROUPS,
        synthetic_rows=SYNTHETIC_ROWS,
    )
    # Insert row table after filter empty block
    marker = '<script>window.__FILTER_ROWS__'
    idx = html.find(marker)
    if idx > 0:
        html = html[:idx] + row_table + "\n\n    " + html[idx:]
    page_path = out / "filter-test.html"
    # 测试页使用冻结目录路由，便于与产品 URL 权威对齐
    html = html.replace('data-page-id="/filter-test"', 'data-page-id="/b/overview"')
    page_path.write_text(html, encoding="utf-8")
    return out


def _attach_error_collectors(page: Page) -> tuple[list[str], list[str], list[str]]:
    page_errors: list[str] = []
    console_errors: list[str] = []
    remote_requests: list[str] = []

    def on_page_error(e: Any) -> None:
        page_errors.append(str(e))

    def on_console(msg: Any) -> None:
        if msg.type == "error":
            console_errors.append(msg.text)

    def on_request(req: Any) -> None:
        skip = ("document", "script", "stylesheet", "image", "font")
        if req.resource_type not in skip:
            remote_requests.append(req.url)

    page.on("pageerror", on_page_error)
    page.on("console", on_console)
    page.on("request", on_request)
    return page_errors, console_errors, remote_requests


def _launch(playwright: Playwright, browser_name: str) -> Browser:
    browser_type = getattr(playwright, browser_name)
    return cast(Browser, browser_type.launch())


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str = "", **kwargs: Any) -> None:
        self._directory = directory
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(directory: Path) -> tuple[http.server.HTTPServer, int]:
    port = _free_port()

    def handler(*a: Any) -> _QuietHandler:
        return _QuietHandler(*a, directory=str(directory))

    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _file_url(path: Path) -> str:
    return "file://" + pathname2url(str(path.resolve()))


class TestFilterState:
    """筛选面板浏览器验收矩阵。"""

    @pytest.mark.parametrize("browser_name,width", DESKTOP_PARAMS)
    def test_filter_panel_renders_and_is_accessible(
        self, tmp_path: Path, browser_name: str, width: int
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": width, "height": 800})
                errs, cerrs, reqs = _attach_error_collectors(page)

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")

                entry = page.locator("#kz-filter-entry")
                assert entry.is_visible(), "筛选入口按钮必须可见"
                assert "筛选" in entry.inner_text(), "筛选入口必须含中文"

                entry.click()
                panel = page.locator("#kz-filter-panel")
                assert panel.is_visible(), "筛选面板必须展开"

                assert page.locator('.kz-filter-scope[data-scope="page"]').count() == 1
                assert page.locator('.kz-filter-scope[data-scope="module"]').count() == 2
                assert "整份报告条件" in panel.inner_text()
                assert "疗效数据" in panel.inner_text()
                assert "安全性数据" in panel.inner_text()
                assert "清除疗效条件" in panel.inner_text()
                assert "清除安全性条件" in panel.inner_text()
                assert page.locator(".kz-filter-advanced").count() == 1
                assert not page.locator('[data-test-only="true"]').is_visible()

                items = page.locator(".kz-filter-item")
                assert items.count() > 0, "必须存在筛选项"

                for i in range(items.count()):
                    text = items.nth(i).evaluate(
                        """(el) => {
                          const clone = el.cloneNode(true);
                          const check = clone.querySelector('.kz-filter-item__check');
                          if (check) check.remove();
                          return (clone.textContent || '').trim();
                        }"""
                    )
                    assert text, f"筛选项标签不能为空（index={i}）"
                    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
                    has_abbrev = bool(re.match(r"^[A-Z0-9/\-]+$", text))
                    assert has_chinese or has_abbrev, (
                        f"筛选项必须含中文或标准缩写：{text!r}"
                    )
                    assert not FORBIDDEN_VOCAB.search(text), f"筛选项含禁止词：{text}"

                close_btn = page.locator("#kz-filter-close")
                close_btn.click()
                assert not panel.is_visible(), "面板必须关闭"

                assert errs == [], f"页面错误：{errs}"
                assert cerrs == [], f"控制台错误：{cerrs}"
                assert len(reqs) == 0, f"不应有远程请求：{reqs}"

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name,width", DESKTOP_PARAMS)
    def test_filter_selection_updates_rows_and_url(
        self, tmp_path: Path, browser_name: str, width: int
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": width, "height": 800})
                errs, cerrs, _reqs = _attach_error_collectors(page)

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")

                page.click("#kz-filter-entry")
                page.wait_for_selector("#kz-filter-panel[open]")

                sle_btn = page.locator('.kz-filter-item[data-val="ind-sle"]')
                sle_btn.click()

                row_count = page.locator("#kz-filter-row-count")
                assert "3" in row_count.inner_text(), (
                    f"选 SLE 应有 3 行：{row_count.inner_text()}"
                )

                url = page.url
                assert "ind-sle" in url or "ps=" in url, f"URL 应含筛选状态：{url}"

                chips = page.locator("#kz-filter-chips .kz-filter-chip")
                assert chips.count() >= 1, "应显示筛选标签"

                assert errs == [], f"页面错误：{errs}"
                assert cerrs == [], f"控制台错误：{cerrs}"

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_page_and_module_resets_do_not_pollute(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")

                page.click("#kz-filter-entry")
                page.wait_for_selector("#kz-filter-panel[open]")
                page.click('.kz-filter-item[data-val="ind-sle"]')
                page.click('.kz-filter-item[data-val="ep-pri"]')
                page.click('.kz-filter-item[data-val="ae-teae"]')

                assert "ps=" in page.url
                assert "ms=" in page.url or "m=" in page.url

                page.click("#kz-filter-reset-page")
                assert "ind-sle" not in page.url
                assert page.locator(
                    '.kz-filter-item[data-val="ep-pri"]'
                ).get_attribute("aria-checked") == "true"
                # 疗效主要终点保留 2 行；安全性 TEAE 保留 1 行。
                assert "3" in page.locator("#kz-filter-row-count").inner_text()

                page.click("#kz-filter-reset-module")
                assert page.locator(
                    '.kz-filter-item[data-val="ep-pri"]'
                ).get_attribute("aria-checked") == "false"
                assert page.locator(
                    '.kz-filter-item[data-val="ae-teae"]'
                ).get_attribute("aria-checked") == "true"
                assert "4" in page.locator("#kz-filter-row-count").inner_text()

                page.click("#kz-filter-reset-module-2")
                assert page.locator(
                    '.kz-filter-item[data-val="ae-teae"]'
                ).get_attribute("aria-checked") == "false"
                assert "5" in page.locator("#kz-filter-row-count").inner_text()

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_back_forward_and_refresh_restore_state(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")

                page.click("#kz-filter-entry")
                page.wait_for_selector("#kz-filter-panel[open]")
                page.click('.kz-filter-item[data-val="ind-sle"]')

                url_filtered = page.url
                assert "ind-sle" in url_filtered

                page.reload()
                page.wait_for_load_state("domcontentloaded")
                assert "ind-sle" in page.url
                assert "3" in page.locator("#kz-filter-row-count").inner_text()

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")
                page.go_back()
                page.wait_for_load_state("domcontentloaded")
                assert "ind-sle" in page.url

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_empty_state_shows_message_restrictions_and_reset(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")

                page.click("#kz-filter-entry")
                page.wait_for_selector("#kz-filter-panel[open]")
                page.click('.kz-filter-item[data-val="ind-ra"]')
                page.click('.kz-filter-item[data-val="product-gamma"]')

                empty = page.locator("#kz-filter-empty")
                assert empty.is_visible(), "空结果时应显示空状态"
                assert "暂无可比较数据" in empty.inner_text()
                restrictions = page.locator("#kz-filter-empty-restrictions")
                assert "整份报告" in restrictions.inner_text()
                restriction_text = restrictions.inner_text()
                assert "类风湿" in restriction_text or "产品丙" in restriction_text

                # Must not auto-clear URL
                assert "ps=" in page.url

                reset_page = page.locator("#kz-filter-empty-reset-page")
                assert reset_page.is_visible()
                reset_page.click()
                assert "5" in page.locator("#kz-filter-row-count").inner_text()

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_keyboard_navigation_and_focus_return(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")

                entry = page.locator("#kz-filter-entry")
                entry.focus()
                page.keyboard.press("Enter")
                page.wait_for_selector("#kz-filter-panel[open]")

                first_item = page.locator(".kz-filter-item").first
                first_item.focus()
                page.keyboard.press("Space")
                assert first_item.get_attribute("aria-checked") == "true"

                page.keyboard.press("Escape")
                assert not page.locator("#kz-filter-panel").is_visible()
                focused = page.evaluate("() => document.activeElement && document.activeElement.id")
                assert focused == "kz-filter-entry"

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_file_protocol_works(self, tmp_path: Path, browser_name: str) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            errs, cerrs, reqs = _attach_error_collectors(page)

            page.goto(_file_url(portal_dir / "filter-test.html"))
            page.wait_for_load_state("domcontentloaded")
            page.click("#kz-filter-entry")
            page.wait_for_selector("#kz-filter-panel[open]")
            page.click('.kz-filter-item[data-val="ind-sle"]')
            assert "3" in page.locator("#kz-filter-row-count").inner_text()
            assert errs == [], f"file:// 页面错误：{errs}"
            assert cerrs == [], f"file:// 控制台错误：{cerrs}"
            assert len(reqs) == 0, f"file:// 不应有远程请求：{reqs}"
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_width_1024_representative(self, tmp_path: Path, browser_name: str) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1024, "height": 800})
                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")
                assert page.locator("#kz-filter-entry").is_visible()
                page.click("#kz-filter-entry")
                assert page.locator("#kz-filter-panel").is_visible()
                # No horizontal clip on entry text
                overflow = page.evaluate(
                    """() => {
                      const el = document.querySelector('#kz-filter-entry');
                      return el.scrollWidth <= el.clientWidth + 1;
                    }"""
                )
                assert overflow, "1024 宽度下筛选入口文本不应裁切"
                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_chinese_labels_only_no_english_jargon(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")
                page.click("#kz-filter-entry")

                visible_text = page.evaluate(
                    """() => {
                    const bar = document.querySelector('.kz-filter-bar');
                    const panel = document.querySelector('.kz-filter-panel');
                    return (bar ? bar.innerText : '') + '\\n' + (panel ? panel.innerText : '');
                }"""
                )

                match = FORBIDDEN_VOCAB.search(visible_text)
                assert not match, f"筛选区域含软件术语：{match.group()}"
                assert "筛选" in visible_text
                assert "清除" in visible_text
                assert "整份报告条件" in visible_text
                assert "疗效数据" in visible_text
                assert "安全性数据" in visible_text
                assert "Details" not in visible_text
                assert "product-alpha" not in visible_text
                assert "trial-001" not in visible_text
                page_text = page.locator("body").inner_text()
                assert "合成数据" not in page_text
                assert "筛选验证" not in page_text
                assert "测试用途" not in page_text

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_reduced_motion_preference(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    reduced_motion="reduce",
                )
                page = context.new_page()

                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")

                has_rm_rules = page.evaluate(
                    """() => {
                    for (let i = 0; i < document.styleSheets.length; i++) {
                        try {
                            const rules = document.styleSheets[i].cssRules;
                            for (let j = 0; j < rules.length; j++) {
                                if (rules[j] instanceof CSSMediaRule &&
                                    rules[j].conditionText &&
                                    rules[j].conditionText.includes('prefers-reduced-motion')) {
                                    return true;
                                }
                            }
                        } catch (e) { /* cross-origin */ }
                    }
                    return false;
                }"""
                )
                assert has_rm_rules, "CSS 必须包含 prefers-reduced-motion 规则"

                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_module_filters_do_not_cross_contaminate(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")
                page.click("#kz-filter-entry")
                page.wait_for_selector("#kz-filter-panel[open]")
                page.click('.kz-filter-item[data-val="ep-pri"]')
                # Efficacy filtered to 2; safety rows untouched → 4
                assert "4" in page.locator("#kz-filter-row-count").inner_text()
                assert page.locator("#filter-row-row-004").is_visible()
                assert page.locator("#filter-row-row-001").is_visible()
                assert not page.locator("#filter-row-row-003").is_visible()

                page.click('.kz-filter-item[data-val="ae-teae"]')
                # Safety now only teae (row-004); efficacy still ep-pri → 3
                assert "3" in page.locator("#kz-filter-row-count").inner_text()
                assert page.locator("#filter-row-row-004").is_visible()
                assert not page.locator("#filter-row-row-005").is_visible()
                assert page.locator("#filter-row-row-001").is_visible()
                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_bad_hash_shows_restore_error_keeps_hash(
        self, tmp_path: Path, browser_name: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                bad = (
                    f"http://127.0.0.1:{port}/filter-test.html"
                    "#v1~pid=%2Fb%2Foverview~ps=totally_unknown:a"
                )
                page.goto(bad)
                page.wait_for_load_state("domcontentloaded")
                err = page.locator("#kz-filter-restore-error")
                assert err.is_visible()
                assert "无法恢复此筛选网址" in err.inner_text()
                assert "totally_unknown" in page.url
                # Must not rewrite to empty hash or apply filters
                assert "5" in page.locator("#kz-filter-row-count").inner_text() or (
                    page.locator("#kz-filter-row-count").inner_text() == ""
                    or "5" in page.locator("#kz-filter-row-count").inner_text()
                )
                # Ensure chips not applied from bad state
                assert page.locator("#kz-filter-chips .kz-filter-chip").count() == 0
                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize(
        "bad_hash",
        [
            "v1~pid=%2Fb%2Foverview~ps=indication:ind-sle|indication:ind-ra",
            "v1~pid=%2Fb%2Foverview~m=b-efficacy~ms=endpoint:ep-pri~m=b-efficacy",
            "v1~pid=%2Fb%2Foverview~ps=indication:ind-sle,ind-sle",
            "v1~pid=%2Fb%2Foverview~pid=%2Fother",
            "v2~pid=%2Fb%2Foverview",
            "v1~pid=%2Fa%2Foverview",
            "v1~pid=%2Fb%2Foverview~s=field:sideways",
            "v1~pid=%2Fb%2Foverview~pg=0",
            "v1~pid=%2Fb%2Foverview~e=frag-1,frag-1",
            "v1~pid=%2Fb%2Foverview~a=NCT1~a=NCT2",
        ],
    )
    def test_duplicate_or_invalid_hash_variants(
        self, tmp_path: Path, bad_hash: str
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, "chromium")
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(f"http://127.0.0.1:{port}/filter-test.html#{bad_hash}")
                page.wait_for_load_state("domcontentloaded")
                assert page.locator("#kz-filter-restore-error").is_visible()
                assert page.locator("#kz-filter-chips .kz-filter-chip").count() == 0
                browser.close()
        finally:
            server.shutdown()

    def test_utf8_byte_limit_via_real_filter_click(self, tmp_path: Path) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, "chromium")
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")
                page.click("#kz-filter-entry")
                page.click('.kz-filter-item[data-val="ind-sle"]')
                prior_hash = page.evaluate("() => location.hash")
                assert "ind-sle" in prior_hash
                long_btn = page.locator('.kz-filter-item[data-val="' + ("x" * 2500) + '"]')
                assert long_btn.count() == 1
                long_btn.dispatch_event("click")
                # Product path: keep prior hash, keep selections, show hint
                assert page.evaluate("() => location.hash") == prior_hash
                assert long_btn.get_attribute("aria-checked") == "true"
                assert page.locator(
                    '.kz-filter-item[data-val="ind-sle"]'
                ).get_attribute("aria-checked") == "true"
                hint = page.locator("#kz-filter-local-hint")
                assert hint.is_visible()
                assert "保存为本地视图" in hint.inner_text()
                browser.close()
        finally:
            server.shutdown()

    def test_global_state_survives_filter_ops_and_navigation(
        self, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, "chromium")
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                base = f"http://127.0.0.1:{port}/filter-test.html"
                loaded = (
                    base
                    + "#v1~pid=%2Fb%2Foverview"
                    + "~s=efficacy:desc~a=NCT0099~e=frag-a,frag-b~pg=3"
                )
                page.goto(loaded)
                page.wait_for_load_state("domcontentloaded")
                assert not page.locator("#kz-filter-restore-error").is_visible()
                page.click("#kz-filter-entry")
                page.click('.kz-filter-item[data-val="ind-sle"]')
                url_after = page.url
                assert "ind-sle" in url_after
                assert "s=efficacy" in url_after or "efficacy" in url_after
                assert "NCT0099" in url_after
                assert "frag-a" in url_after and "frag-b" in url_after
                assert "pg=3" in url_after

                page.reload()
                page.wait_for_load_state("domcontentloaded")
                assert "ind-sle" in page.url
                assert "NCT0099" in page.url
                assert "pg=3" in page.url
                assert page.locator(
                    '.kz-filter-item[data-val="ind-sle"]'
                ).get_attribute("aria-checked") == "true"

                page.goto(base)
                page.wait_for_load_state("domcontentloaded")
                page.go_back()
                page.wait_for_load_state("domcontentloaded")
                assert "ind-sle" in page.url
                assert "NCT0099" in page.url
                browser.close()
        finally:
            server.shutdown()

    def test_bad_hash_preserves_existing_ui_state(self, tmp_path: Path) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, "chromium")
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                page.wait_for_load_state("domcontentloaded")
                page.click("#kz-filter-entry")
                page.click('.kz-filter-item[data-val="ind-sle"]')
                assert page.locator("#kz-filter-chips .kz-filter-chip").count() >= 1
                page.evaluate(
                    """() => {
                      history.pushState({}, '', '#v1~pid=%2Fb%2Foverview~s=field:sideways');
                      window.dispatchEvent(new PopStateEvent('popstate'));
                    }"""
                )
                assert page.locator("#kz-filter-restore-error").is_visible()
                assert "无法恢复此筛选网址" in page.locator(
                    "#kz-filter-restore-error"
                ).inner_text()
                # Prior UI not cleared
                assert page.locator("#kz-filter-chips .kz-filter-chip").count() >= 1
                assert page.locator(
                    '.kz-filter-item[data-val="ind-sle"]'
                ).get_attribute("aria-checked") == "true"
                browser.close()
        finally:
            server.shutdown()

    def test_real_screenshots_chromium(self, tmp_path: Path) -> None:
        portal_dir = _build_portal_with_filters(tmp_path)
        server, port = _start_server(portal_dir)
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as pw:
                browser = _launch(pw, "chromium")
                for width, name in ((1280, "filter-1280.png"), (1024, "filter-1024.png")):
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    page.goto(f"http://127.0.0.1:{port}/filter-test.html")
                    page.wait_for_load_state("domcontentloaded")
                    page.click("#kz-filter-entry")
                    page.wait_for_selector("#kz-filter-panel[open]")
                    page.click('.kz-filter-item[data-val="ind-sle"]')
                    out = SCREENSHOT_DIR / name
                    page.screenshot(path=str(out), full_page=True)
                    assert out.is_file() and out.stat().st_size > 1000
                browser.close()
        finally:
            server.shutdown()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
