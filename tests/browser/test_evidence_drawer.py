"""Task 4.5 数据依据面板与固定对照浏览器验收测试（Chromium + WebKit）。

合同要点（§15.5 + 验收合同）：
- 右侧同页「数据依据」面板：不整页跳转、打开/关闭不改变滚动与筛选。
- 通用观察完整渲染产品、试验、组别、终点/事件/设计要素、量表、时间点、
  值、阈值、单位、分子、分母、披露状态、来源版本与原文定位；空字段以
  互斥中文状态呈现（不适用/尚未公开/来源未列示/技术暂不可用），不得留白，
  已报告零值必须渲染为 0 而不是缺失。
- 基线/完成情况观察额外渲染完整扩展字段族；简短原文与原因原文逐字保留。
- 原文定位无有效 http(s) 链接时不生成伪链接；非法协议一律不渲染链接。
- 固定多条后以并列对照表核对定义、时间点、分母与冲突；重复固定去重。
- 未知/过期行失败关闭并给出中文提示；筛选可见性变化移除打开项与固定项，
  不得扩大筛选。
- 关闭按钮键盘可操作并返回触发点焦点；减少动态效果生效。
- 无 console/page 错误、无远程请求、无禁用工程词汇。
- 1280 与 1024 原分辨率截图存档供 Codex 复核。
"""

from __future__ import annotations

import hashlib
import http.server
import json
import re
import socket
import threading
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PKG = ROOT / "tests" / "fixtures" / "task45-evidence-drawer"
SCREENSHOT_DIR = ROOT / ".artifacts" / "task45-evidence-drawer" / "current" / "screenshots"

BROWSERS: tuple[str, ...] = ("chromium", "webkit")
DESKTOP_WIDTHS: tuple[int, ...] = (1280, 1024)

FORBIDDEN_VOCAB = re.compile(
    r"证据抽屉|抽屉|事实行|row[_-]?id|gate|signal|prompt|"
    r"\b(not_applicable|not_yet_disclosed|source_not_listed|"
    r"technically_unavailable|reported_value|reported_zero|"
    r"below_reporting_threshold|unresolved_due_to_route|"
    r"not_publicly_disclosed|not_reported|conflicting|evidence_drawer)\b"
)

LABEL_TREAT = "疗效 · 产品甲 · 治疗组 · EASI评分变化值"
LABEL_CTRL = "疗效 · 产品甲 · 对照组 · EASI评分变化值"
LABEL_UNDISCLOSED = "疗效 · 产品乙 · 治疗组 · EASI评分变化值"
LABEL_BETA_CTRL = "疗效 · 产品乙 · 对照组 · EASI评分变化值"
LABEL_ZERO = "安全 · 产品乙 · 治疗组 · 治疗期不良事件"
LABEL_NO_LINK = "疗效 · 产品丙 · 治疗组 · 疾病活动度变化值"
LABEL_INVALID_URL = "疗效 · 产品丙 · 对照组 · 疾病活动度变化值"
LABEL_BASELINE = "基线 · 产品甲 · 治疗组 · 年龄"
LABEL_BASELINE_EASI = "基线 · 产品乙 · 治疗组 · 湿疹面积与严重程度指数"
LABEL_DISPOSITION = "完成情况 · 产品甲 · 治疗组 · 停止治疗（不良事件）"


def _load_render_mod() -> Any:
    import importlib.util

    path = FIXTURE_PKG / "render_fixture.py"
    spec = importlib.util.spec_from_file_location("task45_render_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载夹具构建器：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_render = _load_render_mod()
ROW = _render.fixture_row_ids()


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


def _launch(playwright: Playwright, browser_name: str) -> Browser:
    return cast(Browser, getattr(playwright, browser_name).launch())


def _open_compact_header(page: Page) -> None:
    toggle = page.locator("#menu-toggle")
    nav = page.locator(".site-header__nav")
    if toggle.is_visible() and not nav.is_visible():
        toggle.click()
        page.wait_for_timeout(100)
    assert nav.is_visible()


def _attach_collectors(page: Page) -> tuple[list[str], list[str], list[str]]:
    page_errors: list[str] = []
    console_errors: list[str] = []
    requests: list[str] = []

    def on_page_error(e: Any) -> None:
        page_errors.append(str(e))

    def on_console(msg: Any) -> None:
        if msg.type == "error":
            console_errors.append(msg.text)

    def on_request(req: Any) -> None:
        requests.append(req.url)

    page.on("pageerror", on_page_error)
    page.on("console", on_console)
    page.on("request", on_request)
    return page_errors, console_errors, requests


def _assert_local_only(requests: list[str], port: int) -> None:
    local = f"http://127.0.0.1:{port}/"
    for url in requests:
        assert url.startswith(local), f"夹具页面不得发起非本地请求：{url}"


def _trigger(page: Page, label: str) -> Any:
    return page.locator(
        f'td.kz-fixture-cell--label[data-evidence-open="{ROW[label]}"]'
    )


def _product_cell(page: Page, label: str) -> Any:
    return page.locator(
        f'td.kz-fixture-cell--product[data-evidence-open="{ROW[label]}"]'
    )


def _scroll_trigger_into_view(page: Page, label: str) -> None:
    _trigger(page, label).evaluate(
        "el => el.scrollIntoView({ block: 'center', inline: 'nearest' })"
    )


def _open_view(page: Page, label: str) -> None:
    _trigger(page, label).click()
    page.locator("#kz-evidence-drawer").wait_for(state="visible")


def _field_texts(page: Page) -> dict[str, str]:
    entries = page.evaluate(
        """() => {
        const out = {};
        const rows = document.querySelectorAll("#kz-evidence-view-fields > div");
        for (const row of rows) {
          const dt = row.querySelector("dt");
          const dd = row.querySelector("dd");
          if (dt && dd) out[dt.textContent.trim()] = dd.textContent.trim();
        }
        return out;
        }"""
    )
    return dict(entries)


@pytest.fixture(scope="module")
def fixture_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("task45-evidence-drawer-site")
    _render.write_fixture_site(site, repo_root=ROOT)
    return site


# ─── 资产与嵌入合同（无浏览器） ───────────────────────────────────────────────


def test_packaged_drawer_assets_mirrored_and_manifested() -> None:
    """包内资产与仓库镜像逐字节一致，manifest 摘要与字节数锁定。"""
    manifest = json.loads(
        (ROOT / "assets" / "portal" / "manifest.json").read_text(encoding="utf-8")
    )
    for name in ("evidence-drawer.js", "evidence-drawer.css"):
        packaged = ROOT / "src" / "ci_workflow" / "renderers" / "portal" / "assets" / name
        mirrored = ROOT / "assets" / "portal" / name
        assert packaged.is_file(), f"包内缺少 {name}"
        assert mirrored.read_bytes() == packaged.read_bytes(), f"镜像与包内 {name} 不一致"
        entry = manifest["files"][name]
        digest = hashlib.sha256(packaged.read_bytes()).hexdigest()
        assert entry["sha256"] == digest, f"manifest 摘要不一致：{name}"
        assert entry["bytes"] == packaged.stat().st_size, f"manifest 字节数不一致：{name}"


def test_build_portal_copies_drawer_assets(tmp_path: Path) -> None:
    from ci_workflow.renderers.portal.builder import NavEntry, PageSpec, PortalSpec, build_portal

    spec = PortalSpec(
        title="数据依据资产测试",
        pages=[PageSpec(slug="only", title="唯一页", nav_label="唯一页")],
        nav=[NavEntry(slug="only", label="唯一页")],
    )
    out = tmp_path / "portal"
    build_portal(spec, out)
    for name in ("evidence-drawer.js", "evidence-drawer.css"):
        assert (out / "assets" / name).is_file(), f"build_portal 必须复制 {name}"


def test_embed_carries_views_and_chinese_state_labels(fixture_site: Path) -> None:
    """页面嵌入全部证据视图与中文状态标签；宿主不含禁用工程词汇。"""
    html = (fixture_site / "efficacy.html").read_text(encoding="utf-8")
    assert "window.__EVIDENCE_VIEWS__" in html
    for label in (LABEL_TREAT, LABEL_CTRL, LABEL_UNDISCLOSED, LABEL_ZERO):
        assert ROW[label] in html, f"嵌入必须包含 {label} 的行"
    assert 'id="kz-evidence-drawer"' in html
    assert ">未公开<" in html
    assert ">已报告零值<" in html
    host_markup = html[html.index("<aside") : html.index("</aside>") + len("</aside>")]
    assert not FORBIDDEN_VOCAB.search(host_markup), (
        "静态宿主不得出现禁用工程词汇（数据嵌入中的键名不算用户可见文本）"
    )


# ─── 同页打开：不导航、不改变滚动与筛选 ──────────────────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_open_same_page_no_navigation_scroll_filter_change(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            errs, cerrs, reqs = _attach_collectors(page)
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            page.evaluate("window.scrollTo(0, 420)")
            _scroll_trigger_into_view(page, LABEL_TREAT)
            page.wait_for_timeout(50)
            before_url = page.url
            before_scroll = int(page.evaluate("window.scrollY"))
            assert before_scroll > 0, "前置滚动必须生效"

            _open_view(page, LABEL_TREAT)

            after_url = page.url
            assert after_url.split("#")[0] == before_url.split("#")[0], (
                "打开数据依据不得离开当前页或改写查询串"
            )
            assert int(page.evaluate("window.scrollY")) == before_scroll, "打开不得改变滚动"
            assert not page.evaluate("document.getElementById('kz-evidence-drawer').hidden"), (
                "数据依据面板必须可见"
            )
            hash_after = page.evaluate("() => location.hash")
            assert "eo=" in hash_after, "打开条目必须写入版本化网址"
            chips = page.locator("#kz-filter-chips").inner_text()
            assert "产品甲" not in chips, "打开不得改变筛选状态"

            page.locator("#kz-evidence-drawer-close").click()
            assert int(page.evaluate("window.scrollY")) == before_scroll, "关闭不得改变滚动"
            assert page.evaluate("document.getElementById('kz-evidence-drawer').hidden")
            assert not errs, f"pageerror: {errs}"
            assert not cerrs, f"console error: {cerrs}"
            _assert_local_only(reqs, port)
            browser.close()
    finally:
        server.shutdown()


# ─── 通用观察字段渲染：完整、无空白、零值不是缺失 ─────────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_general_view_renders_all_fields_no_blanks(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)

            fields = _field_texts(page)
            required = (
                "产品",
                "试验",
                "组别",
                "终点/事件/设计要素",
                "量表",
                "时间点",
                "值",
                "阈值",
                "单位",
                "分子",
                "分母",
                "披露状态",
                "数据说明",
                "来源版本",
                "原文定位",
                "简短原文",
            )
            for label in required:
                assert label in fields, f"缺少字段行：{label}"
                assert fields[label].strip(), f"字段不得留白：{label}"
            assert fields["产品"] == "产品甲"
            assert fields["值"] == "-18.4"
            assert fields["单位"] == "分"
            assert fields["分母"] == "120"
            assert "ClinicalTrials.gov 登记结果（2026年5月1日）" in fields["来源版本"]
            assert fields["披露状态"] == "已报告值"
            assert "-16.9 分" in page.locator("#kz-evidence-view-conflicts").inner_text()
            assert "At week 16" in fields["简短原文"]
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_field_states_semantic_chinese_and_zero_not_missing(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")

            _open_view(page, LABEL_UNDISCLOSED)
            fields = _field_texts(page)
            assert fields["值"] == "尚未公开", "未公开值必须呈现语义状态而非空白或 0"
            assert fields["量表"] == "来源未列示"
            assert fields["单位"] == "技术暂不可用"
            assert fields["阈值"] == "不适用"
            assert fields["披露状态"] == "未公开"
            for label in fields.values():
                assert label.strip(), "任何字段都不得留白"

            _open_view(page, LABEL_ZERO)
            fields = _field_texts(page)
            assert fields["值"] == "0", "已报告零值必须渲染为 0，不是缺失"
            assert fields["分子"] == "0"
            assert fields["披露状态"] == "已报告零值"
            assert "早期登记版本报告 1 例" in page.locator("#kz-evidence-view-history").inner_text()
            browser.close()
    finally:
        server.shutdown()


# ─── 基线/处置扩展字段族 ─────────────────────────────────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_baseline_extension_fields_complete(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/baseline.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_BASELINE)

            fields = _field_texts(page)
            required = (
                "规范变量族",
                "来源字段原名",
                "来源字段定义",
                "统计形式/计量对象",
                "量表版本与方向",
                "分母角色",
                "时间窗/基线定义",
                "原因原文",
                "规范原因",
                "互斥与穷尽",
                "兼容规则",
                "差异标签",
            )
            for label in required:
                assert label in fields, f"基线观察缺少扩展字段：{label}"
                assert fields[label].strip(), f"扩展字段不得留白：{label}"
            assert fields["规范变量族"] == "人口学特征"
            assert fields["来源字段原名"] == "Age"
            assert fields["互斥与穷尽"] == "不适用"
            assert fields["原因原文"] == "Age at enrollment"
            assert fields["值"] == "42.3"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_baseline_severity_evidence_never_inherits_age_metadata(
    browser_name: str, fixture_site: Path
) -> None:
    """EASI 记录的变量族、来源字段和原因必须属于 EASI 本身，不能串入年龄。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/baseline.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_BASELINE_EASI)
            fields = _field_texts(page)
            assert fields["规范变量族"] == "疾病严重程度"
            assert fields["来源字段原名"] == "EASI total score"
            assert "湿疹面积与严重程度指数" in fields["来源字段定义"]
            assert fields["量表版本与方向"] == "EASI；0–72分；分数越高表示病情越重"
            assert fields["原因原文"] == "EASI total score at baseline"
            assert "年龄" not in " ".join(fields.values())
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_disposition_extension_fields_complete(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/disposition.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_DISPOSITION)

            fields = _field_texts(page)
            assert fields["规范变量族"] == "停止治疗原因"
            assert fields["原因原文"] == "Adverse event"
            assert fields["互斥与穷尽"] == "互斥但未穷尽"
            assert fields["分母"] == "118"
            assert fields["分子"] == "3"
            assert "2 例" in page.locator("#kz-evidence-view-conflicts").inner_text()
            browser.close()
    finally:
        server.shutdown()


# ─── 原文定位：无伪链接 ──────────────────────────────────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_locator_links_only_when_url_valid(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")

            _open_view(page, LABEL_TREAT)
            locator_row = page.locator(
                "#kz-evidence-view-fields dd.kz-evidence-locator"
            ).first
            links = locator_row.locator("a.kz-evidence-locator__link")
            assert links.count() == 1, "有效 https 链接必须渲染"
            href = links.first.get_attribute("href") or ""
            assert href.startswith("https://clinicaltrials.gov/")

            _open_view(page, LABEL_NO_LINK)
            no_link_row = page.locator(
                "#kz-evidence-view-fields dd.kz-evidence-locator"
            ).first
            assert no_link_row.locator("a.kz-evidence-locator__link").count() == 0, (
                "无链接定位不得生成伪链接"
            )
            assert "表 2" in no_link_row.inner_text()

            _open_view(page, LABEL_INVALID_URL)
            invalid_row = page.locator(
                "#kz-evidence-view-fields dd.kz-evidence-locator"
            ).first
            assert invalid_row.locator("a.kz-evidence-locator__link").count() == 0, (
                "javascript: 协议不得生成链接"
            )
            browser.close()
    finally:
        server.shutdown()


# ─── 固定对照：并列核对、去重、取消固定 ──────────────────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_pin_compare_side_by_side_and_dedupe(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")

            _open_view(page, LABEL_TREAT)
            pin = page.locator("#kz-evidence-pin-btn")
            pin.click()
            assert pin.get_attribute("aria-pressed") == "true"

            _open_view(page, LABEL_CTRL)
            pin.click()

            cols = page.locator(".kz-evidence-compare__table thead th.kz-evidence-compare__col")
            assert cols.count() == 2, "固定两条必须并列两列"
            rows = page.locator(".kz-evidence-compare__table tbody tr")
            row_labels = [
                (r.locator("th[scope='row']").inner_text() or "").strip() for r in rows.all()
            ]
            for expected in ("定义", "时间点", "分母", "冲突", "值", "来源版本"):
                assert expected in row_labels, f"对照表缺少行：{expected}"
            for r in rows.all():
                for td in r.locator("td").all():
                    assert td.inner_text().strip(), "对照表单元格不得留白"

            # 重复固定去重：对同一行再次固定必须不产生新列
            page.evaluate(
                "(rowId) => window.__EVIDENCE_DRAWER__.pin(rowId)", ROW[LABEL_TREAT]
            )
            assert cols.count() == 2, "重复固定同一行必须去重"

            # 取消固定一条
            page.locator(".kz-evidence-compare__col-remove").first.click()
            assert cols.count() == 1

            # 全部取消后对照表隐藏
            page.locator(".kz-evidence-compare__col-remove").first.click()
            assert not page.locator("#kz-evidence-compare").is_visible()
            browser.close()
    finally:
        server.shutdown()


# ─── 未知/过期行失败关闭；筛选变化移除打开项与固定项 ─────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_unknown_row_fails_closed_with_chinese_status(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")

            ok = page.evaluate("window.__EVIDENCE_DRAWER__.openByRowId('report-row_not-exist')")
            assert ok is False, "未知行必须失败关闭"
            assert page.evaluate("document.getElementById('kz-evidence-drawer').hidden") is False, (
                "失败提示必须可见"
            )
            status = page.locator("#kz-evidence-drawer-status").inner_text()
            assert "不存在或已失效" in status, "失败提示必须为自然中文"
            assert not page.locator("#kz-evidence-view").is_visible(), "未知行不得渲染任何依据内容"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_filter_change_removes_open_and_pinned_without_widening(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")

            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            assert page.locator("#kz-evidence-compare").is_visible()

            # 选择「产品乙」→ 产品甲行被筛选隐藏 → 打开项与固定项必须移除
            entry = page.locator("#kz-filter-entry")
            entry.click()
            item = page.locator('.kz-filter-item[data-val="product-beta"]')
            item.click()
            page.wait_for_timeout(100)

            assert page.evaluate("document.getElementById('kz-evidence-drawer').hidden"), (
                "打开项已不在当前事实行集时必须移除"
            )
            assert not page.locator("#kz-evidence-compare").is_visible(), (
                "固定项已不在当前事实行集时必须移除"
            )
            chips = page.locator("#kz-filter-chips").inner_text()
            assert "产品乙" in chips and "产品甲" not in chips, "不得扩大或改写筛选"


            # 关闭筛选面板后，当前事实行集内的行仍可正常打开
            page.locator("#kz-filter-close").click()
            _open_view(page, LABEL_UNDISCLOSED)
            assert "产品乙" in _field_texts(page)["产品"]
            browser.close()
    finally:
        server.shutdown()


# ─── 键盘与减少动态效果 ──────────────────────────────────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_close_button_keyboard_returns_focus_to_trigger(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")

            row_id = ROW[LABEL_TREAT]
            trigger = _trigger(page, LABEL_TREAT)
            trigger.click()
            page.locator("#kz-evidence-drawer").wait_for(state="visible")

            page.locator("#kz-evidence-drawer-close").focus()
            page.keyboard.press("Enter")
            assert page.evaluate("document.getElementById('kz-evidence-drawer').hidden")
            focused = page.evaluate(
                "(rowId) => document.activeElement && "
                "document.activeElement.getAttribute('data-evidence-open') === rowId",
                row_id,
            )
            assert focused, "键盘关闭必须把焦点返回触发点"
            # 固定按钮键盘可操作
            trigger.click()
            page.locator("#kz-evidence-pin-btn").focus()
            page.keyboard.press(" ")
            assert page.locator("#kz-evidence-pin-btn").get_attribute("aria-pressed") == "true"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_reduced_motion_disables_drawer_transition(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.emulate_media(reduced_motion="reduce")
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            duration = page.evaluate(
                """() => {
                const el = document.getElementById("kz-evidence-drawer-panel");
                return parseFloat(getComputedStyle(el).transitionDuration) || 0;
                }"""
            )
            assert duration <= 0.001, f"减少动态效果下过渡时长必须为 0：{duration}"
            browser.close()
    finally:
        server.shutdown()


# ─── 禁用词汇、错误与离线检查 ────────────────────────────────────────────────


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_no_forbidden_vocabulary_in_drawer(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            for label in (LABEL_TREAT, LABEL_UNDISCLOSED, LABEL_ZERO):
                _open_view(page, label)
                text = page.locator("#kz-evidence-drawer").inner_text()
                match = FORBIDDEN_VOCAB.search(text)
                assert match is None, f"面板出现禁用词汇：{match.group(0)}（{label}）"
            page.locator("#kz-evidence-pin-btn").click()
            compare_text = page.locator("#kz-evidence-compare").inner_text()
            assert FORBIDDEN_VOCAB.search(compare_text) is None, "对照表出现禁用词汇"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_no_console_page_errors_and_local_only(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            errs, cerrs, reqs = _attach_collectors(page)
            for page_name in ("efficacy.html", "baseline.html", "disposition.html"):
                page.goto(f"http://127.0.0.1:{port}/{page_name}")
                page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_DISPOSITION)
            page.locator("#kz-evidence-pin-btn").click()
            assert not errs, f"pageerror: {errs}"
            assert not cerrs, f"console error: {cerrs}"
            _assert_local_only(reqs, port)
            browser.close()
    finally:
        server.shutdown()


# ─── 1280 / 1024 原分辨率截图 ────────────────────────────────────────────────


@pytest.mark.parametrize("browser_name,width", [(b, w) for b in BROWSERS for w in DESKTOP_WIDTHS])
def test_drawer_fits_viewport_and_screenshots(
    browser_name: str, width: int, fixture_site: Path
) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")

            _open_view(page, LABEL_TREAT)
            box = page.locator("#kz-evidence-drawer").bounding_box()
            assert box is not None and box["x"] >= 0 and box["x"] + box["width"] <= width, (
                f"面板必须完整落在视口内（{width}px）"
            )
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            assert no_overflow, f"页面不得出现水平溢出（{width}px）"
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"drawer-open-{browser_name}-{width}.png"),
                full_page=False,
            )

            page.locator("#kz-evidence-pin-btn").click()
            _open_view(page, LABEL_CTRL)
            page.locator("#kz-evidence-pin-btn").click()
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"drawer-compare-{browser_name}-{width}.png"),
                full_page=False,
            )
            browser.close()
    finally:
        server.shutdown()

    for name in (
        f"drawer-open-{browser_name}-{width}.png",
        f"drawer-compare-{browser_name}-{width}.png",
    ):
        shot = SCREENSHOT_DIR / name
        assert shot.is_file(), f"截图必须保存：{name}"
        assert shot.stat().st_size > 4000, f"截图异常小：{name}"


def _assert_drawer_matches_hit(page: Page, hit: dict[str, Any]) -> None:
    open_id = page.evaluate("() => window.__EVIDENCE_DRAWER__.getOpenRowId()")
    assert open_id == hit["row_id"], f"打开行必须与命中行相同：{open_id} vs {hit['row_id']}"
    fields = _field_texts(page)
    assert fields["产品"] == hit["product_zh"]
    assert fields["试验"] == hit["trial_zh"]
    assert fields["组别"] == hit["group_zh"]
    subject = page.locator("#kz-evidence-view-subject").inner_text()
    assert hit["product_zh"] in subject
    selected = page.evaluate(
        "() => window.__CHART_SYNC__ && window.__CHART_SYNC__.getSelectedRowId()"
    )
    if selected is not None:
        assert selected == hit["row_id"] or page.locator(
            f'.kz-chart-table__row[data-row-id="{hit["row_id"]}"]'
        ).count() == 0


def _wait_charts(page: Page) -> None:
    page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
    page.wait_for_timeout(700)


def _expand_complete_tables(page: Page) -> None:
    """完整表默认折叠；单元格级交互前显式展开。"""
    page.evaluate(
        """() => {
          document.querySelectorAll('details.kz-complete-table').forEach(node => {
            node.open = true;
          });
        }"""
    )
    page.wait_for_timeout(50)


def _pointer_meta_bar(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const chartEl = Array.from(
            document.querySelectorAll('[data-chart-type="bar"]')
          ).find((el) => window.echarts.getInstanceByDom(el));
          if (!chartEl) return { ok: false, reason: 'no-bar' };
          const inst = window.echarts.getInstanceByDom(chartEl);
          if (!inst) return { ok: false, reason: 'no-instance' };
          const groupIndex = Number(String(chartEl.id || '').replace('kz-chart-', ''));
          const group = (window.__CHART_GROUPS__ || [])[groupIndex];
          if (!group) return { ok: false, reason: 'no-group' };
          const expected = group.rows[0];
          const paths = Array.from(chartEl.querySelectorAll('path'))
            .map((p) => {
              const b = p.getBoundingClientRect();
              return { x: b.left, y: b.top, w: b.width, h: b.height };
            })
            .filter((b) => b.w >= 20 && b.h >= 10)
            .sort((a, b) => a.x - b.x);
          if (!paths.length) return { ok: false, reason: 'no-bar-path' };
          const target = paths[0];
          return {
            ok: true,
            clientX: target.x + target.w / 2,
            clientY: target.y + target.h / 2,
            hit: expected
          };
        }"""
    )


def _pointer_meta_matrix(page: Page, chart_type: str) -> dict[str, Any]:
    return page.evaluate(
        """(chartType) => {
          const chartEl = document.querySelector('[data-chart-type="' + chartType + '"]');
          if (!chartEl) return { ok: false, reason: 'no-chart' };
          const inst = window.echarts.getInstanceByDom(chartEl);
          if (!inst) return { ok: false, reason: 'no-instance' };
          const group = (window.__CHART_GROUPS__ || []).find(
            (g) => g.rows && g.rows[0] && g.rows[0]._chart_type === chartType
          );
          if (!group) return { ok: false, reason: 'no-group' };
          const expected = group.rows[0];
          let pixel = null;
          try {
            pixel = inst.convertToPixel({ seriesIndex: 0 }, [0, 0]);
          } catch (err) {
            pixel = null;
          }
          if (Array.isArray(pixel) && pixel.length >= 2) {
            const box = chartEl.getBoundingClientRect();
            return {
              ok: true,
              clientX: box.left + pixel[0],
              clientY: box.top + pixel[1],
              hit: expected
            };
          }
          const rects = Array.from(chartEl.querySelectorAll('rect'))
            .map((r) => {
              const b = r.getBoundingClientRect();
              return { x: b.left, y: b.top, w: b.width, h: b.height };
            })
            .filter((b) => b.w >= 16 && b.h >= 12 && b.w < 420)
            .sort((a, b) => a.y - b.y || a.x - b.x);
          if (!rects.length) return { ok: false, reason: 'no-cell' };
          const target = rects[0];
          return {
            ok: true,
            clientX: target.x + target.w / 2,
            clientY: target.y + target.h / 2,
            hit: expected
          };
        }""",
        chart_type,
    )


def test_fixture_copy_uses_natural_chinese_not_engineering_row(fixture_site: Path) -> None:
    html = (fixture_site / "efficacy.html").read_text(encoding="utf-8")
    assert "点击任一数据项" in html
    assert "事实行" not in html
    assert "kz-fixture-cell--product" in html
    assert "查看数据依据" in html


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_fixture_global_search_finds_products_and_explains_no_match(
    browser_name: str, fixture_site: Path
) -> None:
    """全局搜索必须找到产品实体；无匹配时给出中文反馈，不能像失灵。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_compact_header(page)
            search = page.locator("#global-search-input")
            search.fill("产品乙")
            results = page.locator("#global-search-results")
            assert results.is_visible()
            assert "产品乙" in results.inner_text()
            search.fill("不存在的产品")
            assert results.is_visible()
            assert "未找到匹配页面或数据" in results.inner_text()
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_pointer_bar_opens_same_row_evidence(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errs, cerrs, reqs = _attach_collectors(page)
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _wait_charts(page)
            page.evaluate(
                """() => {
                  const el = document.querySelector('[data-chart-type="bar"]');
                  if (el) el.scrollIntoView({ block: "center", inline: "nearest" });
                }"""
            )
            page.wait_for_timeout(200)
            meta = _pointer_meta_bar(page)
            assert meta.get("ok"), f"无法定位柱几何: {meta}"
            page.mouse.click(meta["clientX"], meta["clientY"])
            page.locator("#kz-evidence-drawer").wait_for(state="visible")
            _assert_drawer_matches_hit(page, meta["hit"])
            selected = page.evaluate("() => window.__CHART_SYNC__.getSelectedRowId()")
            assert selected == meta["hit"]["row_id"], "必须保留图表选择高亮"
            assert not errs, f"pageerror: {errs}"
            assert not cerrs, f"console error: {cerrs}"
            _assert_local_only(reqs, port)
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_pointer_bar_escape_returns_focus_to_exact_svg_mark(
    browser_name: str, fixture_site: Path
) -> None:
    """图点触发也必须回到同一个真实 SVG 标记，不只覆盖表格触发器。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _wait_charts(page)
            page.evaluate(
                """() => {
                  const el = document.querySelector('[data-chart-type="bar"]');
                  if (el) el.scrollIntoView({ block: "center", inline: "nearest" });
                }"""
            )
            page.wait_for_timeout(200)
            meta = _pointer_meta_bar(page)
            assert meta.get("ok"), f"无法定位柱几何: {meta}"
            page.evaluate(
                """(point) => {
                  window.__TASK45_POINTER_TRIGGER__ = document.elementFromPoint(
                    point.clientX, point.clientY
                  );
                }""",
                meta,
            )
            page.mouse.click(meta["clientX"], meta["clientY"])
            page.locator("#kz-evidence-drawer").wait_for(state="visible")
            page.keyboard.press("Escape")
            assert page.evaluate(
                "() => document.activeElement === window.__TASK45_POINTER_TRIGGER__"
            ), "Esc 必须把焦点返回刚才点击的图形标记"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("chart_type", ["heatmap", "status_matrix"])
def test_pointer_matrix_cell_opens_same_row_evidence(
    browser_name: str, chart_type: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _wait_charts(page)
            page.evaluate(
                """(chartType) => {
                  const el = document.querySelector('[data-chart-type="' + chartType + '"]');
                  if (el) el.scrollIntoView({ block: "center", inline: "nearest" });
                }""",
                chart_type,
            )
            page.wait_for_timeout(200)
            meta = _pointer_meta_matrix(page, chart_type)
            assert meta.get("ok"), f"无法定位{chart_type}单元: {meta}"
            page.mouse.click(meta["clientX"], meta["clientY"])
            page.locator("#kz-evidence-drawer").wait_for(state="visible")
            _assert_drawer_matches_hit(page, meta["hit"])
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_matrix_tables_preserve_heatmap_values_and_status_semantics(
    browser_name: str, fixture_site: Path
) -> None:
    """热图下表必须有同值；状态矩阵必须使用试验状态标题且不挂疗效单位。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _wait_charts(page)
            _expand_complete_tables(page)
            heatmap = page.locator('[data-chart-type="heatmap"]').locator("xpath=..")
            assert heatmap.locator("td.kz-chart-table__cell--value").all_inner_texts() == [
                "-12.1",
                "-9.4",
            ]
            status = page.locator('[data-chart-type="status_matrix"]').locator("xpath=..")
            assert "试验完成状态" in status.locator("h3").inner_text()
            assert status.locator("thead th").nth(0).inner_text() == "试验"
            assert status.locator("thead th").nth(2).inner_text() == "试验状态"
            assert status.locator("td.kz-chart-table__cell--label").all_inner_texts() == [
                "试验一",
                "试验二",
            ]
            assert status.locator("td.kz-chart-table__cell--value").all_inner_texts() == [
                "已完成",
                "进行中",
            ]
            assert status.locator("td.kz-chart-table__cell--unit").all_inner_texts() == ["", ""]
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_opening_drawer_closes_responsive_navigation(
    browser_name: str, fixture_site: Path
) -> None:
    """窄屏打开依据时先收起菜单，不能让菜单和依据面板叠压。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1024, "height": 768})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            page.locator("#menu-toggle").click()
            assert page.locator(".site-header__nav").evaluate(
                "el => el.classList.contains('is-open')"
            )
            _open_view(page, LABEL_TREAT)
            assert not page.locator(".site-header__nav").evaluate(
                "el => el.classList.contains('is-open')"
            )
            assert page.locator("#menu-toggle").get_attribute("aria-expanded") == "false"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_drawer_starts_below_sticky_header_and_keeps_navigation_available(
    browser_name: str, fixture_site: Path
) -> None:
    """依据面板不得盖住站点导航；打开依据后仍能直接切换页面。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            drawer_top = page.locator("#kz-evidence-drawer").bounding_box()["y"]
            header_bottom = page.locator(".site-header").bounding_box()["height"]
            assert drawer_top >= header_bottom
            _open_compact_header(page)
            page.get_by_role("link", name="基线与人群", exact=True).click()
            page.wait_for_url("**/baseline.html")
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_1024_drawer_leaves_chart_center_available_for_continuous_review(
    browser_name: str, fixture_site: Path
) -> None:
    """1024 宽度下右侧依据面板不能盖住图表中心点击区。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1024, "height": 768})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _wait_charts(page)
            _open_view(page, LABEL_TREAT)
            chart = page.locator('[data-chart-type="status_matrix"]')
            chart.scroll_into_view_if_needed()
            drawer_box = page.locator("#kz-evidence-drawer").bounding_box()
            chart_box = chart.bounding_box()
            assert chart_box["x"] + chart_box["width"] / 2 < drawer_box["x"]
            chart.click(timeout=5000)
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_filter_pruning_explains_removed_pinned_items(
    browser_name: str, fixture_site: Path
) -> None:
    """筛选收窄必须移除越界固定项，同时用中文说明发生了什么。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_NO_LINK)
            page.locator("#kz-evidence-pin-btn").click()
            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            page.locator("#kz-filter-entry").click()
            page.locator('.kz-filter-item[data-val="product-alpha"]').click()
            assert page.evaluate("() => window.__EVIDENCE_DRAWER__.getPinnedRowIds()") == [
                ROW[LABEL_TREAT]
            ]
            notice = page.locator("#kz-evidence-drawer-status")
            assert notice.is_visible()
            assert "已移除 1 条不在当前筛选范围内的固定数据" in notice.inner_text()
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_pinned_compare_flags_material_definition_differences(
    browser_name: str, fixture_site: Path
) -> None:
    """不同指标、组别、时间点或单位并列时，先给出自然中文可比性提示。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            _open_view(page, LABEL_INVALID_URL)
            page.locator("#kz-evidence-pin-btn").click()
            warning = page.locator(".kz-evidence-compare__warning")
            assert warning.is_visible()
            warning_text = warning.inner_text()
            assert "指标定义" in warning_text
            assert "组别" in warning_text
            assert "并列用于核对口径，不代表可以直接比较数值" in warning_text
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_open_item_is_compared_with_existing_pin_for_definition_warning(
    browser_name: str, fixture_site: Path
) -> None:
    """只固定一条时，当前查看项与固定项口径不同也必须立即提示。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            _open_view(page, LABEL_INVALID_URL)
            warning = page.locator(".kz-evidence-compare__warning")
            assert warning.is_visible()
            assert "指标定义" in warning.inner_text()
            assert "不代表可以直接比较数值" in warning.inner_text()
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_filter_pruning_notice_remains_visible_when_open_item_is_removed(
    browser_name: str, fixture_site: Path
) -> None:
    """筛选同时关闭越界当前项时，移除固定项说明仍留在主页面。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            page.locator("#kz-filter-entry").click()
            page.locator('.kz-filter-item[data-val="product-beta"]').click()
            notice = page.locator("#kz-evidence-filter-notice")
            assert notice.is_visible()
            assert "已移除 1 条不在当前筛选范围内的固定数据" in notice.inner_text()
            assert not page.locator("#kz-evidence-drawer").is_visible()
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_table_data_cell_pointer_opens_same_row(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            cell = _product_cell(page, LABEL_TREAT)
            cell.click()
            page.locator("#kz-evidence-drawer").wait_for(state="visible")
            fields = _field_texts(page)
            assert fields["产品"] == "产品甲"
            assert fields["试验"] == "试验一"
            assert fields["组别"] == "治疗组"
            assert page.evaluate(
                "() => window.__EVIDENCE_DRAWER__.getOpenRowId()"
            ) == ROW[LABEL_TREAT]
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_chart_table_cell_keyboard_and_pointer(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _wait_charts(page)
            _expand_complete_tables(page)
            value_cell = page.locator(
                f'td.kz-chart-table__cell--value[data-evidence-open="{ROW[LABEL_TREAT]}"]'
            ).first
            value_cell.click()
            page.locator("#kz-evidence-drawer").wait_for(state="visible")
            assert page.evaluate("() => window.__EVIDENCE_DRAWER__.getOpenRowId()") == ROW[
                LABEL_TREAT
            ]
            page.locator("#kz-evidence-drawer-close").click()
            arm_cell = page.locator(
                f'td.kz-chart-table__cell--arm[data-evidence-open="{ROW[LABEL_CTRL]}"]'
            ).first
            arm_cell.focus()
            page.keyboard.press("Enter")
            page.locator("#kz-evidence-drawer").wait_for(state="visible")
            assert page.evaluate(
                "() => window.__EVIDENCE_DRAWER__.getOpenRowId()"
            ) == ROW[LABEL_CTRL]
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_escape_returns_focus_and_preserves_scroll(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            page.evaluate("window.scrollTo(0, 360)")
            _scroll_trigger_into_view(page, LABEL_TREAT)
            page.wait_for_timeout(50)
            before = int(page.evaluate("window.scrollY"))
            trigger = _trigger(page, LABEL_TREAT)
            trigger.click()
            page.locator("#kz-evidence-drawer").wait_for(state="visible")
            assert int(page.evaluate("window.scrollY")) == before
            page.keyboard.press("Escape")
            assert page.evaluate("document.getElementById('kz-evidence-drawer').hidden")
            focused = page.evaluate(
                "(rowId) => document.activeElement && "
                "document.activeElement.getAttribute('data-evidence-open') === rowId",
                ROW[LABEL_TREAT],
            )
            assert focused, "Esc 必须把焦点返回精确触发点"
            assert int(page.evaluate("window.scrollY")) == before, "Esc 关闭不得改变滚动"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_url_restore_refresh_and_unknown_id_normalized(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            _open_view(page, LABEL_CTRL)
            page.locator("#kz-evidence-pin-btn").click()
            hash_before = page.evaluate("() => location.hash")
            assert "eo=" in hash_before
            assert "e=" in hash_before

            page.reload()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_function(
                "() => window.__EVIDENCE_DRAWER__ && window.__EVIDENCE_DRAWER__.isOpen()",
                timeout=10000,
            )
            assert page.evaluate("() => window.__EVIDENCE_DRAWER__.getOpenRowId()") == ROW[
                LABEL_CTRL
            ]
            pinned = page.evaluate("() => window.__EVIDENCE_DRAWER__.getPinnedRowIds()")
            assert ROW[LABEL_TREAT] in pinned and ROW[LABEL_CTRL] in pinned

            page.evaluate(
                """() => {
                  const panel = document.getElementById("kz-filter-panel");
                  const pid = panel
                    ? panel.getAttribute("data-page-id")
                    : "/efficacy";
                  location.hash =
                    "v1~pid=" +
                    encodeURIComponent(pid) +
                    "~eo=report-row_not-exist~e=also-gone";
                }"""
            )
            page.wait_for_function(
                """() => {
                  const hash = location.hash || "";
                  return hash.indexOf("report-row_not-exist") === -1
                    && hash.indexOf("also-gone") === -1;
                }""",
                timeout=10000,
            )
            hash_after = page.evaluate("() => location.hash")
            assert "report-row_not-exist" not in hash_after
            assert "also-gone" not in hash_after
            assert page.evaluate("() => window.__EVIDENCE_DRAWER__.getOpenRowId()") in (
                None,
                False,
            )
            chips = page.locator("#kz-filter-chips").inner_text()
            assert "产品乙" not in chips, "未知标识规范化不得放宽筛选"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_url_back_forward_restores_open_and_pins(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            _open_view(page, LABEL_CTRL)
            page.evaluate("() => history.back()")
            page.wait_for_function(
                "(id) => window.__EVIDENCE_DRAWER__ && "
                "window.__EVIDENCE_DRAWER__.getOpenRowId() === id",
                arg=ROW[LABEL_TREAT],
                timeout=10000,
            )
            assert page.evaluate("() => window.__EVIDENCE_DRAWER__.getOpenRowId()") == ROW[
                LABEL_TREAT
            ]
            page.evaluate("() => history.forward()")
            page.wait_for_function(
                "(id) => window.__EVIDENCE_DRAWER__ && "
                "window.__EVIDENCE_DRAWER__.getOpenRowId() === id",
                arg=ROW[LABEL_CTRL],
                timeout=10000,
            )
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_filter_removes_ids_and_normalizes_url_without_widening(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _open_view(page, LABEL_TREAT)
            page.locator("#kz-evidence-pin-btn").click()
            assert "eo=" in page.evaluate("() => location.hash")
            page.locator("#kz-filter-entry").click()
            page.locator('.kz-filter-item[data-val="product-beta"]').click()
            page.wait_for_timeout(150)
            hash_now = page.evaluate("() => location.hash")
            assert ROW[LABEL_TREAT] not in hash_now
            assert page.evaluate("document.getElementById('kz-evidence-drawer').hidden")
            chips = page.locator("#kz-filter-chips").inner_text()
            assert "产品乙" in chips and "产品甲" not in chips
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_product_filter_keeps_compatible_charts_for_selected_product(
    browser_name: str, fixture_site: Path
) -> None:
    """筛选产品乙后仍显示其疗效图和试验状态，不能塌成只有表格的空页面。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/efficacy.html")
            page.wait_for_load_state("domcontentloaded")
            _wait_charts(page)
            page.locator("#kz-filter-entry").click()
            page.locator('.kz-filter-item[data-val="product-beta"]').click()
            page.wait_for_timeout(250)
            _expand_complete_tables(page)
            bar_state = page.evaluate(
                """() => {
                  const visible = (el) => !!(el && el.offsetParent !== null);
                  const groups = Array.from(
                    document.querySelectorAll('[data-chart-type="bar"]')
                  ).map(chart => chart.parentElement).filter(visible);
                  return {
                    groupCount: groups.length,
                    rowIds: groups.flatMap(group => Array.from(
                      group.querySelectorAll('.kz-chart-table__row')
                    ).filter(visible).map(row => row.getAttribute('data-row-id'))),
                    liveChartCount: groups.filter(group => {
                      const chart = group.querySelector('[data-chart-type="bar"]');
                      return chart && window.echarts.getInstanceByDom(chart);
                    }).length
                  };
                }"""
            )
            assert bar_state["groupCount"] >= 1
            assert bar_state["rowIds"] == [ROW[LABEL_UNDISCLOSED], ROW[LABEL_BETA_CTRL]]
            assert bar_state["liveChartCount"] >= 1
            chart_options = page.evaluate(
                """() => Array.from(document.querySelectorAll('[data-chart-type]'))
                  .filter(el => el.offsetParent !== null)
                  .map(el => window.echarts.getInstanceByDom(el))
                  .filter(Boolean)
                  .map(inst => JSON.stringify(inst.getOption()))"""
            )
            rendered_options = "\n".join(chart_options)
            assert "产品甲" not in rendered_options
            assert "试验一" not in rendered_options
            assert "试验二" in rendered_options
            assert ROW[LABEL_TREAT] not in rendered_options
            assert ROW[LABEL_CTRL] not in rendered_options
            assert ROW[LABEL_BETA_CTRL] in rendered_options
            status_group = page.locator('[data-chart-type="status_matrix"]').locator("xpath=..")
            assert status_group.is_visible()
            assert status_group.locator(
                ".kz-chart-table__row:visible td.kz-chart-table__cell--value"
            ).all_inner_texts() == ["进行中"]
            browser.close()
    finally:
        server.shutdown()
