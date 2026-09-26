"""Task 4.4 浏览器验收：Python 权威分组、离线 ECharts 八类、真实 pointer 联动。"""

from __future__ import annotations

import hashlib
import http.server
import importlib.util
import json
import re
import shutil
import socket
import sys
import threading
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from ci_workflow.renderers.portal import (
    NavEntry,
    PageSpec,
    PortalSpec,
    build_portal,
    resolve_echarts_bundle,
)
from ci_workflow.reports.common.chart_specs import ChartType, resolve_chart_type

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PKG = ROOT / "tests" / "fixtures" / "task44-chart-table-sync"
SCREENSHOT_DIR = ROOT / ".artifacts" / "task44-chart" / "current"


def _load_render_mod() -> Any:
    path = FIXTURE_PKG / "render_fixture.py"
    spec = importlib.util.spec_from_file_location("task44_render_fixture", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_render = _load_render_mod()
build_chart_payload = _render.build_chart_payload
write_fixture_site = _render.write_fixture_site

ALL_ROW_IDS: tuple[str, ...] = (
    "row-treat-endpoint-a",
    "row-ctrl-endpoint-a",
    "row-treat-endpoint-b",
    "row-ctrl-endpoint-b",
    "row-unique-endpoint-c",
    "row-not-disclosed",
)
NOT_RENDERABLE_ROW_ID = "row-not-disclosed"
BROWSERS: tuple[str, ...] = ("chromium", "webkit")
DESKTOP_WIDTHS: tuple[int, ...] = (1280, 1024)

FORBIDDEN_VOCAB = re.compile(
    r"row_id|renderable|_chart_type|snapshot|gate|signal|\btest\b|\blog\b|debug|fixture|"
    r"\bhash\b|backend|未满足展示条件|"
    r"higher_better|lower_better|\bbar\b|\bline\b|\bforest\b|\bheatmap\b|\bbubble\b|"
    r"scatter_interval|\btimeline\b|\bradar\b|status_matrix",
    re.IGNORECASE,
)

ECHARTS_SHA256 = "b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0"
CHART_TYPES: tuple[str, ...] = (
    "bar",
    "line",
    "forest",
    "heatmap",
    "bubble",
    "scatter_interval",
    "timeline",
    "status_matrix",
)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str = "", **kwargs: Any) -> None:
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(directory: Path) -> tuple[http.server.HTTPServer, int]:
    port = _free_port()

    def handler(*a: Any, **kw: Any) -> _QuietHandler:
        return _QuietHandler(*a, directory=str(directory), **kw)

    server = http.server.HTTPServer(("127.0.0.1", port), cast(Any, handler))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def _launch(playwright: Playwright, browser_name: str) -> Browser:
    return cast(Browser, getattr(playwright, browser_name).launch())


def _expand_complete_tables(page: Page) -> None:
    """完整表默认折叠；行级交互前显式展开。"""
    page.evaluate(
        """() => {
          document.querySelectorAll('details.kz-complete-table').forEach(node => {
            node.open = true;
          });
        }"""
    )
    page.wait_for_timeout(50)


def _attach_collectors(page: Page) -> tuple[list[str], list[str], list[str]]:
    page_errors: list[str] = []
    console_errors: list[str] = []
    requests: list[str] = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("request", lambda req: requests.append(req.url))
    return page_errors, console_errors, requests


def _assert_offline(requests: list[str], port: int) -> None:
    local = f"http://127.0.0.1:{port}/"
    external = [
        u
        for u in requests
        if (u.startswith("http://") or u.startswith("https://")) and not u.startswith(local)
    ]
    assert not external, f"发现远程请求: {external}"
    assert any("echarts.min.js" in u for u in requests), "必须加载本地 echarts.min.js"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_grouped_bar_repeated_observations_keep_both_glyphs(tmp_path: Path) -> None:
    site = tmp_path / "site"
    write_fixture_site(site, repo_root=ROOT)
    page_file = site / "index.html"
    html = page_file.read_text(encoding="utf-8")
    marker = '<script src="assets/charts.js"></script>'
    assert marker in html
    injection = """<script>
      var group = window.__CHART_GROUPS__[0];
      group.identity_series = true;
      var repeated = Object.assign({}, group.rows[0], {row_id: 'repeat-observation'});
      group.rows.push(repeated);
      window.__PORTAL_FILTER__ = null;
      window.__FILTER_ROWS__ = [];
    </script>
    """
    page_file.write_text(html.replace(marker, injection + marker), encoding="utf-8")
    server, port = _start_server(site)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined")
            result = page.evaluate(
                """() => {
                  const chartNode = document.getElementById('kz-chart-0');
                  const instance = window.echarts.getInstanceByDom(chartNode);
                  const option = instance.getOption();
                  return {
                    categories: option.xAxis[0].data,
                    ids: option.series.flatMap(series =>
                      series.data.map(point => point._row_id).filter(Boolean))
                  };
                }"""
            )
            assert "repeat-observation" in result["ids"]
            assert len(result["categories"]) >= 2
            assert not errors
            browser.close()
    finally:
        server.shutdown()


def test_empty_comparison_does_not_repeat_every_row_reason(tmp_path: Path) -> None:
    site = tmp_path / "site"
    write_fixture_site(site, repo_root=ROOT)
    page_file = site / "index.html"
    html = page_file.read_text(encoding="utf-8")
    marker = '<script src="assets/charts.js"></script>'
    assert marker in html
    injection = """<script>
      var group = window.__CHART_GROUPS__[0];
      group.empty_message = '当前未形成可绘制的试验内比较';
      group.rows = group.rows.slice(0, 2).map(function (row) {
        return Object.assign({}, row, {
          renderable: false, disclosure_state: 'not_applicable',
          reason: '需核对对照、人群与来源，不等于未公开'
        });
      });
    </script>
    """
    page_file.write_text(html.replace(marker, injection + marker), encoding="utf-8")
    server, port = _start_server(site)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined")
            card = page.locator('.kz-chart-module__group[data-group-index="0"]')
            assert card.locator(".kz-chart-group__status-note").count() == 0
            assert card.locator(".kz-chart-undisclosed__title").inner_text() == (
                "当前未形成可绘制的试验内比较"
            )
            assert card.locator(".kz-chart-undisclosed__hint").inner_text().count(
                "需核对对照、人群与来源"
            ) == 1
            assert card.locator(".kz-chart-table__row").count() == 2
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("case", ("swapped_periods", "duplicate_cell", "unknown_context"))
def test_grouped_bar_never_pairs_observations_by_array_occurrence(
    tmp_path: Path, case: str
) -> None:
    site = tmp_path / "site"
    write_fixture_site(site, repo_root=ROOT)
    page_file = site / "index.html"
    html = page_file.read_text(encoding="utf-8")
    marker = '<script src="assets/charts.js"></script>'
    injection = """<script>
      var group = window.__CHART_GROUPS__[0];
      var seed = group.rows[0];
      function item(id, series, context, value) {
        return Object.assign({}, seed, {
          row_id: id, value: value, numeric_value: value,
          _chart_identity_key: 'drug::trial', _chart_identity_label: '药物｜研究',
          _chart_series_key: series, _chart_series_label: series,
          _chart_comparison_context_key: context,
          _chart_comparison_context_label: context
        });
      }
      group.identity_series = true;
      group.rows = __CASE__ === 'swapped_periods'
        ? [item('t1', 'treatment', 'period-1', 11),
           item('t2', 'treatment', 'period-2', 22),
           item('c2', 'control', 'period-2', 33),
           item('c1', 'control', 'period-1', 44)]
        : __CASE__ === 'duplicate_cell'
        ? [item('t1', 'treatment', 'period-1', 11),
           item('t2', 'treatment', 'period-1', 22),
           item('c1', 'control', 'period-1', 44)]
        : [item('t1', 'treatment', '', 11),
           item('c1', 'control', '', 44)];
      window.__PORTAL_FILTER__ = null;
      window.__FILTER_ROWS__ = [];
    </script>
    """.replace("__CASE__", json.dumps(case))
    page_file.write_text(html.replace(marker, injection + marker), encoding="utf-8")
    server, port = _start_server(site)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined")
            cells = page.evaluate(
                """() => {
                  const chart = document.getElementById('kz-chart-0');
                  const option = window.echarts.getInstanceByDom(chart).getOption();
                  return {
                    labels: option.xAxis[0].data,
                    cells: option.xAxis[0].data.map((_, index) => option.series
                      .map(series => series.data[index]?._row_id)
                      .filter(Boolean).sort())
                  };
                }"""
            )
            if case == "swapped_periods":
                assert sorted(cells["cells"]) == [["c1", "t1"], ["c2", "t2"]]
                assert "period-1" in cells["labels"][0]
                assert "period-2" in cells["labels"][1]
            elif case == "duplicate_cell":
                assert sorted(cells["cells"]) == [["c1"], ["t1"], ["t2"]]
            else:
                assert sorted(cells["cells"]) == [["c1"], ["t1"]]
            assert not errors
            browser.close()
    finally:
        server.shutdown()


@pytest.fixture(scope="module")
def fixture_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("task44-fixture-site")
    write_fixture_site(site, repo_root=ROOT)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return site


def test_fixture_payload_matches_python_split_exactly() -> None:
    """静态构建器输出必须与实时 resolve+split 逐字段相等。"""
    payload = build_chart_payload()
    groups = payload["chart_groups"]
    assert len(groups) == 4
    titles = [g["title_zh"] for g in groups]
    assert all("越高越有利" in t or "越低越有利" in t or "nmol" in t for t in titles)
    assert not any("higher_better" in t or "lower_better" in t for t in titles)
    assert not any("_" in t for t in titles)

    # 未公开行独立成组
    alone = [g for g in groups if any(r["row_id"] == NOT_RENDERABLE_ROW_ID for r in g["rows"])]
    assert len(alone) == 1
    assert len(alone[0]["rows"]) == 1

    # 再跑一次权威 API，逐字段相等
    payload2 = build_chart_payload()
    assert payload["chart_groups"] == payload2["chart_groups"]
    assert payload["snapshot_id"] == payload2["snapshot_id"]
    assert {r["row_id"] for r in payload["chart_rows"]} == set(ALL_ROW_IDS)


def test_packaged_echarts_contract_fail_closed() -> None:
    """包内 ECharts 必须存在且摘要匹配；不得静默依赖仓库绝对路径。"""
    bundled = ROOT / "src/ci_workflow/renderers/portal/assets/echarts.min.js"
    assert bundled.is_file(), "包内缺少 echarts.min.js（资源合同失败关闭）"
    assert _sha(bundled) == ECHARTS_SHA256
    resolved = resolve_echarts_bundle()
    assert resolved.resolve() == bundled.resolve()
    assert _sha(resolved) == ECHARTS_SHA256

    manifest = json.loads((ROOT / "assets/portal/manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["echarts.min.js"]["sha256"] == ECHARTS_SHA256
    charts_repo = ROOT / "assets/portal/charts.js"
    charts_pkg = ROOT / "src/ci_workflow/renderers/portal/assets/charts.js"
    assert charts_repo.read_bytes() == charts_pkg.read_bytes()
    assert _sha(charts_repo) == manifest["files"]["charts.js"]["sha256"]


@pytest.mark.parametrize("browser_name,width", [(b, w) for b in BROWSERS for w in DESKTOP_WIDTHS])
def test_chart_before_table_python_groups(
    browser_name: str, width: int, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": width, "height": 900})
            page_errors, console_errors, requests = _attach_collectors(page)
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.wait_for_timeout(400)

            groups = page.locator(".kz-chart-module__group")
            assert groups.count() == 4
            chart_box = groups.nth(0).locator(".kz-chart-group__chart").bounding_box()
            table_box = groups.nth(0).locator(".kz-chart-table").bounding_box()
            assert chart_box and table_box and chart_box["y"] < table_box["y"]

            assert page.locator(".kz-chart-table__row").count() == 6
            assert (
                page.locator(f'.kz-chart-table__row[data-row-id="{NOT_RENDERABLE_ROW_ID}"]').count()
                == 1
            )

            titles = page.locator(".kz-chart-group__title").all_inner_texts()
            assert len(titles) == 4
            assert "主要终点 HbA1c 变化值" in titles[0]
            assert "探索终点 IL-6 变化值" in titles[1]
            assert "次要终点 LDL-C 变化值" in titles[2]
            assert "探索终点 25-OH-VD 变化值" in titles[3]
            for title in titles:
                assert not FORBIDDEN_VOCAB.search(title), title
                assert "higher_better" not in title

            assert page.locator(".kz-chart-table__th", has_text="组别").count() >= 1
            undisclosed = page.locator(
                f'.kz-chart-module__group:has(.kz-chart-table__row[data-row-id="{NOT_RENDERABLE_ROW_ID}"])'
            )
            status = undisclosed.locator(".kz-chart-undisclosed")
            assert status.count() == 1
            assert "该指标结果尚未公开" in status.inner_text()
            chart_region = undisclosed.locator(".kz-chart-group__chart")
            table_region = undisclosed.locator(".kz-chart-table")
            status_box = chart_region.bounding_box()
            table_box_u = table_region.bounding_box()
            assert status_box and table_box_u and status_box["y"] < table_box_u["y"]
            assert status_box["height"] < 160
            assert chart_region.locator("canvas, svg").count() == 0

            path = SCREENSHOT_DIR / f"state-initial-{browser_name}-{width}.png"
            page.screenshot(path=str(path), full_page=True)
            _assert_offline(requests, port)
            assert not page_errors and not console_errors
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_pointer_click_highlights_table_row(browser_name: str, fixture_site: Path) -> None:
    """真实 pointer click 必须单独通过；禁止 API 回退掩盖失败。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page_errors, _, requests = _attach_collectors(page)
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.wait_for_timeout(800)

            meta = page.evaluate(
                """() => {
                  const chartEl = document.getElementById('kz-chart-0');
                  const inst = window.echarts.getInstanceByDom(chartEl);
                  if (!inst) return { ok: false, reason: 'no-instance' };
                  const expected = window.__CHART_GROUPS__[0].rows[0].row_id;
                  // 真实 SVG 柱路径：取宽高足够的 path，按 x 排序后点第一根
                  const selector = 'path[fill]:not([fill="none"])';
                  const paths = Array.from(chartEl.querySelectorAll(selector))
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
                    expected
                  };
                }"""
            )
            assert meta.get("ok"), f"无法定位柱几何: {meta}"
            page.mouse.click(meta["clientX"], meta["clientY"])
            page.wait_for_timeout(350)
            clicked = page.evaluate("window.__CHART_SYNC__.getSelectedRowId()")
            assert clicked == meta["expected"], (
                f"真实 pointer 未选中期望行：got={clicked} expected={meta['expected']}"
            )
            cls = page.locator(f'.kz-chart-table__row[data-row-id="{clicked}"]').get_attribute(
                "class"
            )
            assert cls and "kz-chart-table__row--selected" in cls

            page.screenshot(
                path=str(SCREENSHOT_DIR / f"state-selection-{browser_name}-1280.png"),
                full_page=True,
            )
            _assert_offline(requests, port)
            assert not page_errors
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_programmatic_select_by_row_id_separate(browser_name: str, fixture_site: Path) -> None:
    """程序化 selectByRowId 另测，不掩盖 pointer 失败。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            target = ALL_ROW_IDS[2]
            page.evaluate("(id) => window.__CHART_SYNC__.selectByRowId(id)", target)
            assert page.evaluate("window.__CHART_SYNC__.getSelectedRowId()") == target
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_table_keyboard_selects_chart(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            _expand_complete_tables(page)
            row = page.locator(f'.kz-chart-table__row[data-row-id="{ALL_ROW_IDS[0]}"]')
            row.click()
            assert page.evaluate("window.__CHART_SYNC__.getSelectedRowId()") == ALL_ROW_IDS[0]
            assert "kz-chart-table__row--selected" in (row.get_attribute("class") or "")
            assert (
                page.locator(".kz-chart-group__chart").first.get_attribute("data-selected-row-id")
                == ALL_ROW_IDS[0]
            )
            second = page.locator(f'.kz-chart-table__row[data-row-id="{ALL_ROW_IDS[2]}"]')
            second.press("Enter")
            assert page.evaluate("window.__CHART_SYNC__.getSelectedRowId()") == ALL_ROW_IDS[2]
            ctrl = page.locator(f'.kz-chart-table__row[data-row-id="{ALL_ROW_IDS[1]}"]')
            treat = page.locator(f'.kz-chart-table__row[data-row-id="{ALL_ROW_IDS[0]}"]')
            ctrl.click()
            ctrl.press("ArrowDown")
            assert page.evaluate("window.__CHART_SYNC__.getSelectedRowId()") == ALL_ROW_IDS[0]
            treat.press("ArrowUp")
            assert page.evaluate("window.__CHART_SYNC__.getSelectedRowId()") == ALL_ROW_IDS[1]
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_row_id_equality_and_null_series(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            _expand_complete_tables(page)

            chart_ids = page.evaluate("() => window.__CHART_SYNC__.getChartRowIds().slice().sort()")
            table_ids = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .map(el => el.getAttribute('data-row-id')).sort()"""
            )
            assert chart_ids == table_ids
            assert set(chart_ids) == set(ALL_ROW_IDS)

            series = page.evaluate(
                """() => {
                  const groups = window.__CHART_GROUPS__;
                  let gIdx = -1;
                  for (let i = 0; i < groups.length; i++) {
                    if (groups[i].rows.some(r => r.row_id === 'row-not-disclosed')) gIdx = i;
                  }
                  const local = groups[gIdx].rows.map(r => r.row_id);
                  const values = window.__CHART_SYNC__.getSeriesValues(gIdx);
                  const idx = local.indexOf('row-not-disclosed');
                  return { gIdx, idx, value: values[idx], title: groups[gIdx].title_zh };
                }"""
            )
            assert series["idx"] == 0
            assert series["value"] is None
            assert "越低越有利" in series["title"]

            page.locator(f'.kz-chart-table__row[data-row-id="{NOT_RENDERABLE_ROW_ID}"]').click()
            page.wait_for_timeout(300)
            selected = page.evaluate("window.__CHART_SYNC__.getSelectedRowId()")
            assert selected == NOT_RENDERABLE_ROW_ID
            page.screenshot(
                path=str(
                    SCREENSHOT_DIR / f"state-small-multiples-undisclosed-{browser_name}-1280.png"
                ),
                full_page=True,
            )
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_filter_and_empty_do_not_widen(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.locator("#kz-filter-entry").click()
            page.locator('.kz-filter-item[data-val="nmol/L"]').click()
            page.wait_for_timeout(300)
            visible = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .filter(el => el.style.display !== 'none').length"""
            )
            assert visible == 1
            hidden_groups = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-module__group'))
                  .filter(el => getComputedStyle(el).display === 'none').length"""
            )
            assert hidden_groups == 3
            page.locator('.kz-filter-item[data-val="nmol/L"]').click()
            page.wait_for_timeout(300)
            restored = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .filter(el => el.style.display !== 'none').length"""
            )
            assert restored == 6
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name,width", [(b, w) for b in BROWSERS for w in DESKTOP_WIDTHS])
def test_dom_overflow_no_duplicate_screenshot_names(
    browser_name: str, width: int, fixture_site: Path
) -> None:
    """DOM 溢出断言；不另存与 initial 同内容的 overflow 重复文件名。"""
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            overflow = page.evaluate(
                """() => {
                  const bad = [];
                  const root = document.documentElement;
                  if (root.scrollWidth > root.clientWidth + 1) {
                    bad.push('document');
                  }
                  const sel = [
                    '.kz-chart-group__title',
                    '.kz-chart-table__th',
                    '.kz-chart-table__cell',
                    '.kz-filter-bar',
                    '.portal-page-title'
                  ].join(',');
                  document.querySelectorAll(sel).forEach(el => {
                    if (el.scrollWidth > el.clientWidth + 2) bad.push(el.className);
                  });
                  return bad;
                }"""
            )
            assert not overflow, overflow
            # 证据态文件应已由其它用例写出且互不相同
            initial = SCREENSHOT_DIR / f"state-initial-{browser_name}-{width}.png"
            if width == 1280:
                undisclosed = (
                    SCREENSHOT_DIR / f"state-small-multiples-undisclosed-{browser_name}-1280.png"
                )
                selection = SCREENSHOT_DIR / f"state-selection-{browser_name}-1280.png"
                for path in (initial, undisclosed, selection):
                    if path.is_file():
                        assert path.stat().st_size > 1000
                existing = [p for p in (initial, undisclosed, selection) if p.is_file()]
                digests = {_sha(p) for p in existing}
                assert len(digests) == len(existing), "截图状态文件内容不得重复"
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_no_forbidden_visible_vocabulary(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            visible = page.evaluate(
                """() => Array.from(document.querySelectorAll('h1,h3,td,th,p,button,span'))
                  .filter(el => !el.closest('.kz-meta'))
                  .filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                  })
                  .map(el => el.textContent.trim()).filter(Boolean)"""
            )
            for text in visible:
                assert not FORBIDDEN_VOCAB.search(text), text
            body = page.locator("body").inner_text()
            assert "未满足展示条件" not in body
            assert "snapshot" not in body.lower()
            assert "fixture" not in body.lower()
            assert "backend" not in body.lower()
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name,width", [(b, w) for b in BROWSERS for w in DESKTOP_WIDTHS])
def test_filter_panel_adjacent_overlay_not_body_end(
    browser_name: str, width: int, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.locator("#kz-filter-entry").click()
            page.wait_for_selector("#kz-filter-panel[open]")
            geo = page.evaluate(
                """() => {
                  const btn = document.getElementById('kz-filter-entry');
                  const panel = document.getElementById('kz-filter-panel');
                  const last = document.body.lastElementChild;
                  const br = btn.getBoundingClientRect();
                  const pr = panel.getBoundingClientRect();
                  const cs = getComputedStyle(panel);
                  return {
                    btnBottom: br.bottom,
                    panelTop: pr.top,
                    panelBottom: pr.bottom,
                    panelHeight: pr.height,
                    viewport: window.innerHeight,
                    position: cs.position,
                    lastIsPanel: last === panel,
                    parentIsHost: panel.parentElement.classList.contains('kz-filter-host')
                  };
                }"""
            )
            assert geo["parentIsHost"]
            assert not geo["lastIsPanel"]
            assert geo["position"] == "absolute"
            assert geo["panelTop"] >= geo["btnBottom"] - 1
            assert geo["panelTop"] <= geo["btnBottom"] + 80
            assert geo["panelTop"] < geo["viewport"]
            assert geo["panelHeight"] > 80
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"state-filter-open-{browser_name}-{width}.png"),
                full_page=False,
            )
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_filter_url_hash_chips_empty_reload_history(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.locator("#kz-filter-entry").click()
            page.locator('.kz-filter-item[data-val="nmol/L"]').click()
            page.wait_for_timeout(250)
            chip_text = page.locator("#kz-filter-chips").inner_text()
            assert "nmol/L" in chip_text
            assert "已选" not in chip_text
            hash_after = page.evaluate("() => location.hash")
            assert hash_after.startswith("#v1")
            assert "pid=" in hash_after
            assert "ps=" in hash_after
            assert "unit" in hash_after
            assert "nmol" in hash_after
            visible = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .filter(el => el.style.display !== 'none').length"""
            )
            assert visible == 1
            match_text = page.locator("#kz-filter-row-count").inner_text()
            assert "匹配 1 项" in match_text
            hidden = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-module__group'))
                  .filter(el => getComputedStyle(el).display === 'none').length"""
            )
            assert hidden == 3
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"state-filter-nmol-{browser_name}-1280.png"),
                full_page=True,
            )

            page.reload()
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.wait_for_timeout(300)
            assert "nmol/L" in page.locator("#kz-filter-chips").inner_text()
            assert page.evaluate("() => location.hash").startswith("#v1")
            visible_reload = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .filter(el => el.style.display !== 'none').length"""
            )
            assert visible_reload == 1

            page.go_back()
            page.wait_for_timeout(400)
            visible_back = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .filter(el => el.style.display !== 'none').length"""
            )
            assert visible_back == 6
            page.go_forward()
            page.wait_for_timeout(400)
            visible_fwd = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .filter(el => el.style.display !== 'none').length"""
            )
            assert visible_fwd == 1

            page.locator("#kz-filter-entry").click()
            page.locator('.kz-filter-item[data-val="24周"]').click()
            page.wait_for_timeout(300)
            page.locator("#kz-filter-close").click()
            page.wait_for_timeout(200)
            empty = page.locator("#kz-filter-empty")
            assert empty.is_visible()
            assert "当前选择下暂无可比较数据" in empty.inner_text()
            assert page.locator("#kz-filter-empty-reset-page").is_visible()
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"state-filter-empty-{browser_name}-1280.png"),
                full_page=True,
            )
            page.locator("#kz-filter-empty-reset-page").click()
            page.wait_for_timeout(300)
            assert not empty.is_visible()
            restored = page.evaluate(
                """() => Array.from(document.querySelectorAll('.kz-chart-table__row'))
                  .filter(el => el.style.display !== 'none').length"""
            )
            assert restored == 6
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_negative_bars_zero_baseline_value_labels(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.wait_for_timeout(600)
            proof = page.evaluate(
                """() => {
                  const groups = window.__CHART_GROUPS__;
                  let gIdx = -1;
                  for (let i = 0; i < groups.length; i++) {
                    if (groups[i].rows.some(r => r.row_id === 'row-treat-endpoint-b')) gIdx = i;
                  }
                  const el = document.getElementById('kz-chart-' + gIdx);
                  const inst = window.echarts.getInstanceByDom(el);
                  const opt = inst.getOption();
                  const y = Array.isArray(opt.yAxis) ? opt.yAxis[0] : opt.yAxis;
                  const paths = Array.from(el.querySelectorAll('path'))
                    .map(p => p.getBoundingClientRect())
                    .filter(b => b.width >= 12 && b.height >= 8)
                    .sort((a, b) => a.x - b.x);
                  const texts = Array.from(el.querySelectorAll('text')).map(
                    (t) => t.textContent || ''
                  );
                  const joined = texts.join('|');
                  return {
                    gIdx,
                    min: typeof y.min === 'function' ? 'fn' : y.min,
                    max: typeof y.max === 'function' ? 'fn' : y.max,
                    scale: y.scale === false ? false : y.scale,
                    barHeights: paths.map(b => Math.round(b.height)),
                    hasTreat: joined.indexOf('治疗组') !== -1,
                    hasCtrl: joined.indexOf('对照组') !== -1,
                    hasTreatVal: joined.includes('-2.1') || joined.includes('−2.1'),
                    hasCtrlVal: joined.includes('-1.5') || joined.includes('−1.5'),
                    zeroY: inst.convertToPixel({ yAxisIndex: 0 }, 0),
                    negY: inst.convertToPixel({ yAxisIndex: 0 }, -2.1)
                  };
                }"""
            )
            assert proof["gIdx"] >= 0
            assert proof["scale"] is False
            if proof["min"] not in ("fn", None):
                assert float(proof["min"]) <= 0
            if proof["max"] not in ("fn", None):
                assert float(proof["max"]) >= 0
            assert proof["zeroY"] is not None and proof["negY"] is not None
            assert proof["negY"] > proof["zeroY"]
            assert len(proof["barHeights"]) >= 2
            assert proof["barHeights"][0] >= 8 and proof["barHeights"][1] >= 8
            assert proof["hasTreat"] and proof["hasCtrl"]
            assert proof["hasTreatVal"] and proof["hasCtrlVal"]
            page.locator(
                f'.kz-chart-table__row[data-row-id="{ALL_ROW_IDS[2]}"]'
            ).scroll_into_view_if_needed()
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"state-negative-bars-{browser_name}-1280.png"),
                full_page=False,
            )
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_undisclosed_group_no_empty_axes(browser_name: str, fixture_site: Path) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            proof = page.evaluate(
                """() => {
                  const groups = window.__CHART_GROUPS__;
                  let gIdx = -1;
                  for (let i = 0; i < groups.length; i++) {
                    if (groups[i].rows.some(r => r.row_id === 'row-not-disclosed')) gIdx = i;
                  }
                  const el = document.getElementById('kz-chart-' + gIdx);
                  const box = el.getBoundingClientRect();
                  const values = window.__CHART_SYNC__.getSeriesValues(gIdx);
                  return {
                    gIdx,
                    hasCanvas: !!el.querySelector('canvas'),
                    hasSvg: !!el.querySelector('svg'),
                    height: box.height,
                    text: el.innerText,
                    values,
                    table: !!document.querySelector(
                      '.kz-chart-table__row[data-row-id="row-not-disclosed"]'
                    )
                  };
                }"""
            )
            assert not proof["hasCanvas"] and not proof["hasSvg"]
            assert proof["height"] < 160
            assert "该指标结果尚未公开" in proof["text"]
            assert proof["values"] == [None]
            assert proof["table"]
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_published_but_unplotted_is_not_called_unpublished(
    browser_name: str, fixture_site: Path
) -> None:
    server, port = _start_server(fixture_site)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.evaluate(
                """() => {
                  const group = window.__CHART_GROUPS__.find(g =>
                    g.rows.some(r => r.row_id === 'row-not-disclosed'));
                  const row = group.rows.find(r => r.row_id === 'row-not-disclosed');
                  row.disclosure_state = 'reported_value';
                  row.renderable = false;
                  row.numeric_value = 7.5;
                  row.value = 7.5;
                  row.reason = '分析集不同，未纳入此图';
                }"""
            )
            page.add_script_tag(url=f"http://127.0.0.1:{port}/assets/charts.js")
            page.wait_for_function(
                "document.querySelectorAll('.kz-chart-undisclosed').length > 0"
            )
            status = page.locator(".kz-chart-undisclosed").filter(
                has_text="有公开记录，但当前口径不适合绘图"
            )
            assert status.count() == 1
            assert "分析集不同，未纳入此图" in status.inner_text()
            assert status.locator("svg, canvas").count() == 0
            row = page.locator('.kz-chart-table__row[data-row-id="row-not-disclosed"]')
            assert row.locator(".kz-chart-table__cell--value").text_content() == "7.5"
            disclosure = row.locator(".kz-chart-table__cell--disclosure").text_content() or ""
            assert "已披露；未绘制" in disclosure
            assert "分析集不同，未纳入此图" in disclosure
            assert "未公开" not in disclosure
            browser.close()
    finally:
        server.shutdown()


def _chart_type_rows(chart_type: str) -> list[dict[str, Any]]:
    base = {
        "unit": "mg/dL",
        "scale": "原始",
        "statistical_form": "均值差",
        "direction": "higher_better",
        "time_window": "12周",
        "analysis_population": "ITT",
        "control_role": "安慰剂",
        "denominator": 100,
        "report_snapshot_id": "snap-nine",
        "display_label_zh": "示例指标",
    }
    disclosed = {
        **base,
        "row_id": f"row-{chart_type}-ok",
        "disclosure_state": "reported_value",
    }
    missing = {
        **base,
        "row_id": f"row-{chart_type}-miss",
        "disclosure_state": "not_publicly_disclosed",
        "display_label_zh": "未公开指标",
        "value": None,
        "numeric_value": None,
    }
    if chart_type == "bar":
        disclosed.update({"category": "治疗组", "value": 1.2, "numeric_value": 1.2})
        missing.update({"category": "治疗组"})
    elif chart_type == "line":
        disclosed.update({"time": "第1周", "value": 2.0, "numeric_value": 2.0})
        missing.update({"time": "第2周"})
    elif chart_type == "forest":
        disclosed.update({"effect": 0.8, "ci_lower": 0.5, "ci_upper": 1.1, "numeric_value": 0.8})
        missing.update({"effect": None, "ci_lower": None, "ci_upper": None})
    elif chart_type == "heatmap":
        disclosed.update({"event": "事件甲", "value_matrix": [0.4]})
        missing.update({"event": "事件乙", "value_matrix": None})
    elif chart_type == "bubble":
        disclosed.update({"x_value": 1.0, "y_value": 2.0, "size": 12})
        missing.update({"x_value": None, "y_value": None, "size": None})
    elif chart_type == "scatter_interval":
        disclosed.update({"center": 1.5, "ci_lower": 0.3, "ci_upper": 1.8})
        missing.update({"center": None, "ci_lower": None, "ci_upper": None})
    elif chart_type == "timeline":
        disclosed.update({"time": "2024-01", "status": "进行中"})
        missing.update({"time": "2024-02", "status": None})
    elif chart_type == "status_matrix":
        disclosed.update({"status": "已完成", "coverage": 0.9})
        missing.update({"status": None, "coverage": None})
    else:
        raise AssertionError(chart_type)
    return [disclosed, missing]


def _write_chart_type_page(site: Path, chart_type: str) -> Path:
    rows = resolve_chart_type(_chart_type_rows(chart_type), ChartType(chart_type))
    payload = {
        "snapshot_id": "snap-nine",
        "row_set_digest": "digest-nine",
        "chart_rows": rows,
        "chart_groups": [
            {
                "title_zh": "全部指标",
                "split_dims": [],
                "rows": rows,
            }
        ],
    }
    assets = site / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    echarts_src = ROOT / "src/ci_workflow/renderers/portal/assets/echarts.min.js"
    shutil.copy2(echarts_src, assets / "echarts.min.js")
    shutil.copy2(ROOT / "assets/portal/charts.js", assets / "charts.js")
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
    <title>图形类型验收</title>
    <style>.kz-chart-group__chart{{width:100%;height:320px}}</style></head><body>
    <section id="kz-chart-module" class="kz-chart-module"></section>
    <script src="assets/echarts.min.js"></script>
    <script>
    window.__SNAPSHOT_ID__ = {json.dumps(payload["snapshot_id"])};
    window.__ROW_SET_DIGEST__ = {json.dumps(payload["row_set_digest"])};
    window.__CHART_ROWS__ = {json.dumps(payload["chart_rows"], ensure_ascii=False)};
    window.__CHART_GROUPS__ = {json.dumps(payload["chart_groups"], ensure_ascii=False)};
    window.__FILTER_ROWS__ = [];
    </script>
    <script src="assets/charts.js"></script>
    </body></html>"""
    path = site / f"{chart_type}.html"
    path.write_text(html, encoding="utf-8")
    return path


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("chart_type", CHART_TYPES)
def test_chart_types_real_echarts_smoke(
    browser_name: str, chart_type: str, tmp_path: Path
) -> None:
    page_path = _write_chart_type_page(tmp_path, chart_type)
    server, port = _start_server(tmp_path)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1100, "height": 800})
            page_errors, _, requests = _attach_collectors(page)
            page.goto(f"http://127.0.0.1:{port}/{page_path.name}")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.wait_for_timeout(400)
            ok = page.evaluate(
                """() => {
                  const el = document.getElementById('kz-chart-0');
                  if (!el) return false;
                  const hasSvg = !!el.querySelector('svg');
                  const ver = window.echarts && window.echarts.version;
                  const ids = window.__CHART_SYNC__.getChartRowIds();
                  const values = window.__CHART_SYNC__.getSeriesValues(0);
                  const missIdx = ids.indexOf(ids.find(id => id.includes('-miss')));
                  return {
                    hasSvg,
                    ver,
                    ids,
                    missValue: values[missIdx],
                    types: window.__CHART_SYNC__.supportedChartTypes()
                  };
                }"""
            )
            assert ok["hasSvg"], f"{chart_type} 未渲染 SVG"
            assert ok["ver"] == "6.1.0"
            assert len(ok["ids"]) == 2
            assert ok["missValue"] is None
            assert chart_type in ok["types"]
            assert set(ok["types"]) == set(CHART_TYPES)
            _assert_offline(requests, port)
            assert not page_errors, page_errors
            browser.close()
    finally:
        server.shutdown()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_build_portal_serves_packaged_echarts(browser_name: str, tmp_path: Path) -> None:
    """正式 build_portal 复制/加载包内 ECharts；生成站点双引擎确认。"""
    out = tmp_path / "portal-site"
    spec = PortalSpec(
        title="特应性皮炎竞品全景",
        pages=[
            PageSpec(
                slug="overview",
                title="竞品全景",
                nav_label="竞品全景",
                sections=["靶点分布"],
                body_text="展示竞品格局要点。",
            ),
            PageSpec(
                slug="efficacy",
                title="疗效比较",
                nav_label="疗效比较",
                sections=["主要终点"],
                body_text="终点比较展示。",
            ),
        ],
        nav=[
            NavEntry(label="竞品全景", slug="overview"),
            NavEntry(label="疗效比较", slug="efficacy"),
        ],
    )
    paths = build_portal(spec, out)
    assert paths
    assets = out / "assets"
    assert (assets / "echarts.min.js").is_file()
    assert _sha(assets / "echarts.min.js") == ECHARTS_SHA256
    assert (assets / "charts.js").is_file()
    html = (out / "overview.html").read_text(encoding="utf-8")
    assert 'src="assets/echarts.min.js"' in html
    echarts_pos = html.find("echarts.min.js")
    charts_pos = html.find("charts.js")
    assert 0 <= echarts_pos < charts_pos

    payload = build_chart_payload()
    # inject chart payload before charts.js so init sees #kz-chart-module
    injected = html.replace(
        '<script src="assets/echarts.min.js"></script>\n  <script src="assets/charts.js"></script>',
        f"""<script src="assets/echarts.min.js"></script>
<section id="kz-chart-module" class="kz-chart-module" aria-label="图表与数据表"></section>
<script>
window.__SNAPSHOT_ID__ = {json.dumps(payload["snapshot_id"])};
window.__ROW_SET_DIGEST__ = {json.dumps(payload["row_set_digest"])};
window.__CHART_ROWS__ = {json.dumps(payload["chart_rows"], ensure_ascii=False)};
window.__CHART_GROUPS__ = {json.dumps(payload["chart_groups"], ensure_ascii=False)};
window.__FILTER_ROWS__ = [];
</script>
<script src="assets/charts.js"></script>""",
    )
    assert injected != html, "未能注入图表载荷到 build_portal 页面"
    (out / "overview.html").write_text(injected, encoding="utf-8")

    server, port = _start_server(out)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page_errors, _, requests = _attach_collectors(page)
            page.goto(f"http://127.0.0.1:{port}/overview.html")
            page.wait_for_function("window.__CHART_SYNC__ !== undefined", timeout=15000)
            page.wait_for_timeout(500)
            proof = page.evaluate(
                """() => ({
                  ver: window.echarts.version,
                  svg: !!document.querySelector('#kz-chart-0 svg'),
                  groups: document.querySelectorAll('.kz-chart-module__group').length,
                  ids: window.__CHART_SYNC__.getChartRowIds().length
                })"""
            )
            assert proof["ver"] == "6.1.0"
            assert proof["svg"]
            assert proof["groups"] == 4
            assert proof["ids"] == 6
            _assert_offline(requests, port)
            assert not page_errors
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
