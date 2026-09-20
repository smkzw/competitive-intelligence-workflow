"""Task 7.5：真实 Chromium/WebKit 下 C 类站点门户 RED 验收。"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
REPORT_DATA = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
BROWSERS = ("chromium", "webkit")
RESPONSIVE_WIDTHS = (1024, 1280, 1440, 1920)
STATIC_PAGES = (
    "overview",
    "design-map",
    "trial-profile",
    "population-disease-definition",
    "inclusion-criteria",
    "exclusion-criteria",
    "treatment-arms",
    "endpoint-timepoint-matrix",
    "visit-duration-followup",
    "sample-analysis-statistics",
    "design-patterns",
)
_INTERNAL_LEAKS = (
    "field_family",
    "source_role",
    "not_publicly_disclosed",
    "registry_result_or_primary_report",
    "c_missing_",
    "candidate_paths",
    "工作流",
    "后端",
    "提示词",
)


def _load_payload() -> dict[str, Any]:
    value = json.loads(REPORT_DATA.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _renderer() -> ModuleType:
    """延迟导入 C 渲染器，使 RED 在实现缺失时精确失败。"""
    try:
        module = importlib.import_module("ci_workflow.renderers.portal.report_c")
    except ModuleNotFoundError as exc:
        if exc.name != "ci_workflow.renderers.portal.report_c":
            raise
        pytest.fail(f"C 类门户渲染器尚未实现：{exc}", pytrace=False)
    return module


@pytest.fixture(scope="module")
def c_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    module = _renderer()
    data_type = getattr(module, "ReportCPortalData", None)
    render = getattr(module, "render_report_c_site", None)
    if data_type is None or not callable(render):
        pytest.fail("C 类门户必须公开 ReportCPortalData 与 render_report_c_site", pytrace=False)
    root = tmp_path_factory.mktemp("c-browser") / "html"
    data = data_type.model_validate(_load_payload())
    render(data, root)
    return root




def _open(page: Page, site: Path, relative: str, *, width: int, height: int = 900) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.goto((site / relative).as_uri(), wait_until="load")
    page.wait_for_function("document.readyState === 'complete'")
    page.wait_for_timeout(100)


def _launch(playwright: Playwright, browser_name: str) -> Browser:
    return getattr(playwright, browser_name).launch()


def _visible_row_ids(page: Page) -> list[str]:
    return page.locator(".kz-chart-table__row[data-row-id]").evaluate_all(
        """nodes => nodes.filter(node => node.style.display !== 'none')
          .map(node => node.getAttribute('data-row-id')).filter(Boolean)"""
    )


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("width", RESPONSIVE_WIDTHS)
def test_c_all_eleven_pages_render_without_horizontal_dragging(
    c_site: Path,
    browser_name: str,
    width: int,
) -> None:
    """四个内容列宽度下，批准的十一页均有默认核心图和可读完整表。"""
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.on(
            "console",
            lambda message: errors.append(
                f"console:{message.type}:{message.text}"
            )
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: errors.append(f"page:{error}"))
        for page_id in STATIC_PAGES:
            _open(page, c_site, f"{page_id}.html", width=width)
            assert page.locator("html").get_attribute("lang") == "zh-CN"
            assert "康哲药业" in page.locator("body").inner_text()
            assert page.locator("#kz-chart-module").count() == 1, page_id
            assert page.locator(".kz-chart-table__row[data-row-id]").count() > 0, page_id
            assert page.locator("[data-chart-type]").count() > 0, page_id
            if page_id == "design-patterns":
                assert page.locator("[data-path-id]").count() >= 2
                assert "唯一最佳" not in page.locator("body").inner_text()
            overflow = page.evaluate(
                """() => ({
                  document: document.documentElement.scrollWidth,
                  viewport: window.innerWidth,
                  body: document.body.scrollWidth
                })"""
            )
            assert overflow["document"] <= width + 1, (page_id, overflow)
            assert overflow["body"] <= width + 1, (page_id, overflow)
            chart_box = page.locator("#kz-chart-module").bounding_box()
            assert chart_box is not None, page_id
            assert chart_box["x"] >= 0 and chart_box["x"] + chart_box["width"] <= width + 1
            visible = page.locator("#kz-chart-module").inner_text()
            assert visible.strip(), page_id
            for token in _INTERNAL_LEAKS:
                assert token not in page.locator("body").inner_text(), (page_id, token)
        assert not errors
        page.close()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_trial_details_are_physical_and_keep_trial_scoped_facts(
    c_site: Path,
    browser_name: str,
) -> None:
    payload = _load_payload()
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        for trial in payload["trials"]:
            trial_id = trial["id"]
            _open(page, c_site, f"trials/{trial_id}.html", width=1280)
            assert page.locator(f'[data-trial-id="{trial_id}"]').count() == 1
            assert trial["display_id"] in page.locator("body").inner_text()
            assert page.locator("h1").inner_text() == f'{trial["display_id"]} 试验档案'
            assert "模块级" not in page.locator("body").inner_text()
            rows = page.locator(".kz-chart-table__row[data-row-id]")
            assert rows.count() == 12
            assert page.locator("#kz-chart-module [data-chart-type]").count() > 0
            assert page.locator("[data-evidence-open]").count() >= 1
            assert "United States" not in page.locator("body").inner_text()
            assert "Australia" not in page.locator("body").inner_text()
            for token in _INTERNAL_LEAKS:
                assert token not in page.locator("body").inner_text(), (trial_id, token)
        assert not errors
        page.close()
        browser.close()


def test_c_product_filters_use_native_chinese_names(c_site: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(page, c_site, "treatment-arms.html", width=1440)
        visible = page.locator("body").inner_text()
        assert "来布利珠单抗（Lebrikizumab）" in visible
        assert "Lebrikizumab 匹配安慰剂" not in visible
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_filters_restore_url_and_keep_chart_table_drawer_in_sync(
    c_site: Path,
    browser_name: str,
) -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: errors.append(message.text)
            if message.type == "error"
            else None,
        )
        _open(page, c_site, "overview.html", width=1280)
        page.locator("#kz-filter-panel > summary").click()
        trial_buttons = page.locator('button[data-filter-dimension="trial"][data-filter-value]')
        assert trial_buttons.count() >= 2
        trial_value = trial_buttons.first.get_attribute("data-filter-value")
        assert trial_value
        before = set(_visible_row_ids(page))
        assert len(before) >= 2
        trial_buttons.first.click()
        page.wait_for_timeout(50)
        after = set(_visible_row_ids(page))
        assert after
        assert after < before
        assert trial_value in page.url
        assert page.locator('[data-filter-dimension="trial"][aria-pressed="true"]').count() >= 1
        selected_rows = page.locator(".kz-chart-table__row[data-row-id]").evaluate_all(
            """nodes => nodes.filter(node => node.style.display !== 'none')
              .map(node => node.getAttribute('data-trial-id')).filter(Boolean)"""
        )
        assert selected_rows and all(value == trial_value for value in selected_rows)

        page.reload(wait_until="load")
        page.wait_for_timeout(100)
        panel = page.locator("#kz-filter-panel")
        if panel.count() and not panel.evaluate("node => node.open"):
            page.locator("#kz-filter-panel > summary").click()
        module_buttons = page.locator(
            'button[data-filter-scope="module"][data-filter-dimension][data-filter-value]'
        )
        assert module_buttons.count() >= 1
        module_url_before = page.url
        module_buttons.first.click()
        page.wait_for_timeout(50)
        assert set(_visible_row_ids(page))
        assert page.url != module_url_before
        assert trial_value in page.url
        assert "?" in page.url or "#" in page.url
        assert not errors
        page.close()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_evidence_drawer_supports_keyboard_close_and_focus_return(
    c_site: Path,
    browser_name: str,
) -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.emulate_media(reduced_motion="reduce")
        _open(page, c_site, "inclusion-criteria.html", width=1280)
        assert page.evaluate("window.matchMedia('(prefers-reduced-motion: reduce)').matches")
        summary = page.locator("#kz-chart-module .kz-complete-table > summary")
        if summary.count():
            summary.first.click()
            page.wait_for_timeout(50)
        trigger = page.locator("[data-evidence-open]").first
        assert trigger.count() == 1
        trigger_id = (
            trigger.get_attribute("data-row-id")
            or trigger.get_attribute("data-evidence-open")
        )
        trigger.focus()
        trigger.click()
        panel = page.locator("#kz-evidence-drawer-panel")
        assert panel.count() == 1
        assert panel.is_visible()
        drawer_text = panel.inner_text()
        assert "来源" in drawer_text
        assert "来源类型" in drawer_text
        assert "登记记录" in drawer_text
        assert "原文" in drawer_text
        assert "source_role" not in drawer_text
        assert "field_family" not in drawer_text
        page.keyboard.press("Escape")
        assert not panel.is_visible()
        active = page.evaluate(
            """() => ({
              id: document.activeElement && document.activeElement.getAttribute('data-row-id'),
              evidence: document.activeElement
                && document.activeElement.hasAttribute('data-evidence-open')
            })"""
        )
        assert active["evidence"] is True
        if trigger_id:
            assert active["id"] == trigger_id or active["id"] is None
        assert not errors
        page.close()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_pages_make_no_remote_runtime_requests(c_site: Path, browser_name: str) -> None:
    requests: list[str] = []
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("request", lambda request: requests.append(request.url))
        _open(page, c_site, "overview.html", width=1280)
        assert not [url for url in requests if url.startswith(("http://", "https://"))]
        page.close()
        browser.close()


def _core_chart_visibility(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const chart = document.querySelector('#kz-chart-module [data-chart-type]')
            || document.querySelector('[data-chart-type]');
          if (!chart) return {ok: false, reason: 'missing-chart'};
          const box = chart.getBoundingClientRect();
          const vh = window.innerHeight;
          const visibleHeight = Math.min(box.bottom, vh) - Math.max(box.top, 0);
          return {
            ok: box.top < vh && visibleHeight > 40,
            top: box.top,
            visibleHeight,
            vh,
            filterOpen: !!(document.querySelector('#kz-filter-panel')
              && document.querySelector('#kz-filter-panel').open)
          };
        }"""
    )


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("width", RESPONSIVE_WIDTHS)
@pytest.mark.parametrize(
    "page_id",
    (
        "overview",
        "inclusion-criteria",
        "endpoint-timepoint-matrix",
        "design-patterns",
        "sample-analysis-statistics",
    ),
)
def test_c_adversarial_core_chart_is_default_visible_without_scrolling(
    c_site: Path,
    browser_name: str,
    width: int,
    page_id: str,
) -> None:
    """医学经理打开页面后，核心图应在首屏默认可读，无需先收起筛选或向下拖动。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": width, "height": 900})
        _open(page, c_site, f"{page_id}.html", width=width)
        visibility = _core_chart_visibility(page)
        assert visibility["ok"], (page_id, browser_name, width, visibility)
        page.close()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_adversarial_design_paths_are_near_chart_not_after_giant_table(
    c_site: Path,
    browser_name: str,
) -> None:
    """设计综合路径应贴近核心图，不能被完整表推到数千像素之外。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, c_site, "design-patterns.html", width=1280)
        geometry = page.evaluate(
            """() => {
              const chart = document.querySelector('[data-chart-type]');
              const table = document.querySelector('.kz-chart-table');
              const path = document.querySelector('[data-path-id]');
              if (!chart || !table || !path) {
                return {ok: false, reason: 'missing-nodes'};
              }
              const chartTop = chart.getBoundingClientRect().top + window.scrollY;
              const tableTop = table.getBoundingClientRect().top + window.scrollY;
              const pathTop = path.getBoundingClientRect().top + window.scrollY;
              return {
                ok: pathTop < tableTop || pathTop - chartTop < 900,
                chartTop,
                tableTop,
                pathTop,
                pathText: (path.innerText || '').slice(0, 160)
              };
            }"""
        )
        assert geometry["ok"], geometry
        body = page.locator("body").inner_text()
        assert "前提：前提：" not in body
        assert "权衡：权衡：" not in body
        page.close()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_adversarial_treatment_arms_avoid_raw_registry_enums(
    c_site: Path,
    browser_name: str,
) -> None:
    """分组页用户可见文本应是中文临床试验表达，不能直接甩出登记枚举拼串。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, c_site, "treatment-arms.html", width=1280)
        body = page.locator(".kz-chart-table").inner_text()
        for token in (
            "allocation=",
            "interventionModel=",
            "masking=",
            "RANDOMIZED",
            "PARALLEL",
            "TRIPLE",
            "QUADRUPLE",
        ):
            assert token not in body, token
        assert "设计事实" not in body or "随机" in body
        page.close()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_adversarial_filter_panel_does_not_consume_first_screen(
    c_site: Path,
    browser_name: str,
) -> None:
    """默认展开的筛选面板不得独占首屏并挤走核心图。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        _open(page, c_site, "overview.html", width=1024)
        metrics = page.evaluate(
            """() => {
              const panel = document.querySelector('#kz-filter-panel');
              const chart = document.querySelector('[data-chart-type]');
              const panelHeight = panel
                ? panel.getBoundingClientRect().height
                : 0;
              const chartTop = chart
                ? chart.getBoundingClientRect().top
                : null;
              return {
                open: !!(panel && panel.open),
                panelHeight,
                chartTop,
                ok: chart
                  && chart.getBoundingClientRect().top < window.innerHeight - 40
              };
            }"""
        )
        assert metrics["ok"], metrics
        # If the panel starts open, it still must leave room for the chart.
        if metrics["open"]:
            assert metrics["panelHeight"] < 360, metrics
        page.close()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_overview_chart_shows_real_design_facts_not_coverage_dots(
    c_site: Path,
    browser_name: str,
) -> None:
    """首页首图要直接呈现可比较事实，不能退化成几乎相同的覆盖圆点。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        _open(page, c_site, "overview.html", width=1024)
        chart = page.locator('[data-chart-type="core-design-matrix"]')
        chart.wait_for(state="visible")
        text = chart.text_content() or ""
        assert "核心设计差异" not in text  # 标题在图外，避免把标题误当数据。
        assert "740" in text
        assert "445" in text
        assert "主要终点定义" in text
        assert "●" not in text
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_design_patterns_chart_compares_choices_instead_of_overlapping_radar(
    c_site: Path,
    browser_name: str,
) -> None:
    """设计模式页要展示具体选择，不能用四条完全重叠的覆盖雷达线。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        _open(page, c_site, "design-patterns.html", width=1024)
        chart = page.locator('[data-chart-type="design-choice-matrix"]')
        chart.wait_for(state="visible")
        text = chart.text_content() or ""
        assert "主要终点定义" in text
        assert "IGA达到0或1分" in text
        assert page.locator('[data-chart-type="design-pattern-radar"]').count() == 0
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_endpoint_chart_keeps_clinically_decisive_threshold_and_timepoint(
    c_site: Path,
    browser_name: str,
) -> None:
    """终点图不能把 IGA 阈值或第16周截掉。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        _open(page, c_site, "endpoint-timepoint-matrix.html", width=1024)
        text = page.locator('[data-chart-type="endpoint-timepoint-matrix"]').text_content() or ""
        assert "IGA达到0或1分" in text
        assert "较基线降低≥2分" in text
        assert "第16周" in text
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_trial_index_uses_multi_trial_summary_and_overview_keeps_full_regimen(
    c_site: Path,
    browser_name: str,
) -> None:
    """试验入口页不能误称单试验；首页给药方案不能在关键疗程前截断。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        _open(page, c_site, "trial-profile.html", width=1024)
        assert page.locator('[data-chart-type="core-design-matrix"]').count() == 1
        assert "本试验核心设计" not in page.locator("#kz-c-chart-visuals").inner_text()
        _open(page, c_site, "overview.html", width=1024)
        chart_text = page.locator('[data-chart-type="core-design-matrix"]').text_content() or ""
        assert "第1周至第51周" in chart_text
        assert "基线至第52周" in chart_text
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_c_treatment_chart_keeps_frequency_loading_dose_and_treatment_period(
    c_site: Path,
    browser_name: str,
) -> None:
    """分组页核心图应完整保留给药频次、负荷剂量和疗程。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1024, "height": 900})
        _open(page, c_site, "treatment-arms.html", width=1024)
        text = page.locator('[data-chart-type="treatment-structure-matrix"]').text_content() or ""
        assert "每2周1次" in text
        assert "含负荷剂量" in text
        assert "第1周至第51周" in text
        assert "基线至第52周" in text
        assert "度普利尤单抗" in text
        assert "奈莫利珠单抗" in text
        assert "Dupilumab" not in text
        assert "Nemolizumab" not in text
        assert "来布利珠单抗匹配安慰剂" in text
        assert "Lebrikizumab" not in text
        assert "奈莫利珠单抗研究" in text
        assert "奈莫利珠单抗疗效与安全…" not in text
        svg_lines = page.locator(
            '[data-chart-type="treatment-structure-matrix"] tspan'
        ).all_text_contents()
        assert "300 m" not in svg_lines
        assert "0 mg" not in svg_lines
        assert "25" not in svg_lines
        assert "0 mg；每2周1次；含" not in svg_lines
        browser.close()
