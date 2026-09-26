"""Task 6.9：真实 Chromium/WebKit 浏览器下的 B 类门户 RED 验收。"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_REPORT_DATA = ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json"
PNH_REPORT_DATA = ROOT / "fixtures/positive/b-pnh/inputs/report-data.json"
BROWSERS = ("chromium", "webkit")
RESPONSIVE_WIDTHS = (768, 1024, 1280, 1440)
RESPONSIVE_PAGES = (
    "overview.html",
    "efficacy.html",
    "safety.html",
    "baseline-overview.html",
    "disposition-overview.html",
    "efficacy-safety-matrix.html",
)


def _load_portal_payload() -> dict[str, object]:
    payload = json.loads(SYNTHETIC_REPORT_DATA.read_text(encoding="utf-8"))
    safety = [dict(row) for row in payload["safety"]]  # type: ignore[index]
    safety[0].update(value=0, disclosure_state="已公开")
    safety[1].update(value=None, disclosure_state="未公开")
    payload["safety"] = safety
    return payload


@pytest.fixture(scope="module")
def b_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("b-browser") / "html"
    data = ReportBPortalData.model_validate(_load_portal_payload())
    render_report_b_site(data, root)
    return root


@pytest.fixture(scope="module")
def b_pnh_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("b-pnh-browser") / "html"
    data = ReportBPortalData.model_validate(
        json.loads(PNH_REPORT_DATA.read_text(encoding="utf-8"))
    )
    render_report_b_site(data, root)
    return root


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("width", (1920, 2560))
def test_sparse_safety_heatmaps_use_compact_parallel_desktop_cards(
    b_pnh_site: Path, browser_name: str, width: int
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": width, "height": 1080})
        _open(page, b_pnh_site, "safety.html")
        cards = page.locator(".kz-chart-module__group[data-grid-span='6']")
        assert cards.count() >= 2
        first = cards.nth(0).bounding_box()
        second = cards.nth(1).bounding_box()
        assert first is not None and second is not None
        assert first["width"] < width / 2
        assert second["x"] > first["x"] + first["width"]
        assert abs(second["y"] - first["y"]) < 3
        heights = cards.locator("[data-chart-type='heatmap']").evaluate_all(
            "nodes => nodes.map(node => node.getBoundingClientRect().height)"
        )
        assert heights and all(height <= 190 for height in heights)
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_single_efficacy_observation_is_compact_fact_with_source(
    b_pnh_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        _open(page, b_pnh_site, "efficacy.html")
        single = page.locator(
            '.kz-chart-module__group[data-observation-count="1"]:has([data-chart-type="single-fact"])'
        ).first
        assert single.count() == 1
        fact = single.locator(".kz-chart-group__chart--single-fact")
        assert fact.locator("svg, canvas").count() == 0
        assert fact.bounding_box()["height"] <= 90  # type: ignore[index]
        button = fact.locator("[data-chart-evidence-open]")
        assert button.count() == 1
        button.click()
        panel = page.locator("#kz-evidence-drawer-panel")
        assert panel.is_visible()
        page.keyboard.press("Escape")
        assert not panel.is_visible()
        assert page.evaluate(
            "document.activeElement?.getAttribute('data-chart-evidence-open')"
        ) == button.get_attribute("data-chart-evidence-open")
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_desktop_evidence_drawer_reflows_charts_without_covering_facts(
    b_pnh_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        _open(page, b_pnh_site, "safety.html")
        _expand_complete_tables(page)
        trigger = page.locator("#kz-chart-module [data-evidence-open]").first
        trigger.click()
        drawer = page.locator(".kz-evidence-drawer:not([hidden])")
        assert drawer.count() == 1
        page.wait_for_timeout(200)
        main_box = page.locator(".portal-main").bounding_box()
        drawer_box = drawer.bounding_box()
        assert main_box is not None and drawer_box is not None
        assert main_box["x"] + main_box["width"] <= drawer_box["x"] + 1
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
        assert page.locator(
            "[data-chart-type='heatmap'] svg, [data-chart-type='heatmap'] canvas"
        ).count() > 0
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("width", (1440, 1600, 1920, 2560))
def test_b_pnh_names_timepoint_and_matrix_are_user_visible(
    b_pnh_site: Path, browser_name: str, width: int
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": width, "height": 900})
        _open(page, b_pnh_site, "overview.html")
        text = page.locator("body").inner_text()
        assert "APPLY-PNH" in text
        assert "APPOINT-PNH" in text
        assert "第24周" in text
        assert "24week" not in text
        assert "图形定位" not in text
        assert "先看图形，再核对完整数据表" not in text
        for internal_label in (
            "baseline_sample_size",
            "screen_failure",
            "protocol_deviation",
            "not_reported",
            "factor-b",
            "apply-cohort",
        ):
            assert internal_label not in text

        _open(page, b_pnh_site, "efficacy-safety-matrix.html")
        chart = _chart(page)
        box = chart.bounding_box()
        assert box is not None
        assert box["x"] >= 0
        assert box["x"] + box["width"] <= width + 1
        assert page.locator('[data-chart-type="bubble"]').count() == 1
        assert "80.5" in page.locator("#kz-chart-module").inner_text()
        matrix_axes = page.evaluate(
            """() => {
              const node = document.querySelector('[data-chart-type="bubble"]');
              const model = window.echarts.getInstanceByDom(node).getModel();
              return {
                xName: model.getComponent('xAxis').option.name,
                yName: model.getComponent('yAxis').option.name,
                yInverse: model.getComponent('yAxis').option.inverse
              };
            }"""
        )
        assert matrix_axes == {
            "xName": "试验内疗效差（百分点）",
            "yName": "治疗组安全性观察值（%）",
            "yInverse": True,
        }
        matrix_text = page.locator("#kz-chart-module").inner_text()
        assert "气泡大小：治疗组安全性分析人数" in matrix_text
        missing = page.locator(".kz-b-matrix-gaps")
        assert missing.count() == 1
        missing.locator("summary").click()
        assert "不能当作零差值" in missing.inner_text()
        assert "APPOINT-PNH" in missing.inner_text()
        assert missing.locator('a[href="efficacy.html"]').count() == 1
        assert "comparable" not in matrix_text
        assert "可比较" in matrix_text

        _open(page, b_pnh_site, "safety.html")
        safety_box = _chart(page).bounding_box()
        assert safety_box is not None
        assert safety_box["x"] >= 0
        assert safety_box["x"] + safety_box["width"] <= width + 1
        safety_axes = page.evaluate(
            """() => {
              const node = Array.from(document.querySelectorAll('[data-chart-type="heatmap"]'))
                .find(candidate => window.echarts.getInstanceByDom(candidate));
              if (!node) return null;
              const model = window.echarts.getInstanceByDom(node).getModel();
              return {
                arms: model.getComponent('xAxis').option.data,
                trials: model.getComponent('yAxis').option.data
              };
            }"""
        )
        assert safety_axes is not None
        assert safety_axes["arms"] == ["治疗组", "对照组"]
        assert len(safety_axes["trials"]) == 1
        assert "APPLY-PNH" in safety_axes["trials"][0]
        trial_groups = page.evaluate(
            """() => Array.from(document.querySelectorAll('[data-chart-type="heatmap"]'))
              .map(node => window.echarts.getInstanceByDom(node))
              .filter(Boolean)
              .map(chart => chart.getModel().getComponent('yAxis').option.data)"""
        )
        assert all(len(trials) == 1 for trials in trial_groups)
        assert {trial for trials in trial_groups for trial in trials} == {
            "伊普可泮 · APPLY-PNH", "伊普可泮 · APPOINT-PNH",
        }
        assert "APPOINT-PNH：单臂设计，无同期对照组" in page.locator(
            "#kz-chart-module"
        ).inner_text()
        assert "不适用" in page.locator("#kz-chart-module").inner_text()
        safety_options = page.evaluate(
            """() => Array.from(document.querySelectorAll('[data-chart-type="heatmap"]'))
              .map(node => {
                const chart = window.echarts.getInstanceByDom(node);
                return chart ? chart.getOption() : null;
              })
              .filter(Boolean)"""
        )
        assert any(
            item.get("status") == "not_applicable"
            for option in safety_options
            for series in option.get("series", [])
            for item in series.get("data", [])
        )
        table_font_size = page.locator(".kz-chart-table__cell").first.evaluate(
            "node => getComputedStyle(node).fontSize"
        )
        assert table_font_size == "16px"

        browser.close()


def test_b_pnh_drawer_and_design_axes_use_the_same_native_facts(
    b_pnh_site: Path,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        _open(page, b_pnh_site, "efficacy.html")
        _expand_complete_tables(page)
        page.locator(
            '[data-row-id="eff-row-nct04558918-apply-treatment"] [data-evidence-open]'
        ).first.click()
        drawer_text = page.locator(
            "#kz-evidence-drawer-panel, #data-basis-panel"
        ).first.inner_text()
        assert "分子\n来源未列示" in drawer_text
        assert "分子\n51" not in drawer_text
        assert "分母\n60" in drawer_text
        assert "数据说明" in drawer_text
        assert "规范化说明" not in drawer_text
        assert "apply-treatment" not in drawer_text
        assert "nct04558918/efficacy" not in drawer_text

        _open(page, b_pnh_site, "baseline-overview.html")
        baseline_labels = page.evaluate(
            """() => {
              const node = Array.from(document.querySelectorAll('[data-chart-type="bar"]'))
                .find(candidate => window.echarts.getInstanceByDom(candidate));
              return window.echarts.getInstanceByDom(node).getModel()
                .getComponent('xAxis').option.data;
            }"""
        )
        assert baseline_labels
        assert all("｜" in label for label in baseline_labels)
        assert all("baseline_" not in label for label in baseline_labels)
        assert "基线样本量" in page.locator("#kz-chart-module").inner_text()

        _open(page, b_pnh_site, "disposition-overview.html")
        disposition_labels = page.evaluate(
            """() => {
              const node = Array.from(document.querySelectorAll('[data-chart-type="bar"]'))
                .find(candidate => window.echarts.getInstanceByDom(candidate));
              return window.echarts.getInstanceByDom(node).getModel()
                .getComponent('xAxis').option.data;
            }"""
        )
        assert disposition_labels
        assert all("｜" in label for label in disposition_labels)
        assert "已筛选" in page.locator("#kz-chart-module").inner_text()
        browser.close()


def test_b_pnh_chart_values_groups_and_filters_are_clinically_direct(
    b_pnh_site: Path,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1024, "height": 900})

        _open(page, b_pnh_site, "efficacy.html")
        efficacy_groups = page.evaluate(
            """() => window.__CHART_GROUPS__.map(group => ({
              title: group.title_zh,
              crossTrial: group.cross_trial,
              identities: [...new Set(group.rows.map(row => row._chart_identity_label))],
              armRoles: [...new Set(group.rows.map(row => row.arm_role))]
            }))"""
        )
        assert len(efficacy_groups) == 2
        assert all(group["crossTrial"] is False for group in efficacy_groups)
        assert all(len(group["identities"]) == 1 for group in efficacy_groups)
        assert set(efficacy_groups[0]["armRoles"]) == {"treatment", "control"}
        assert set(efficacy_groups[1]["armRoles"]) == {"treatment"}
        expected_headers = [
            "产品",
            "试验",
            "组别",
            "疗效指标",
            "统计形式",
            "分析人群",
            "评价时间",
            "比较值",
            "数值依据",
            "原始应答人数",
            "分析人数",
            "单位",
            "口径提示",
            "披露状态",
        ]
        tables = page.locator("#kz-chart-module table")
        assert tables.count() == 2
        for index in range(tables.count()):
            assert (
                tables.nth(index).locator(".kz-chart-table__th").all_text_contents()
                == expected_headers
            )
        headers = expected_headers
        assert "原始终点" not in headers
        assert "标准分析人群" not in headers
        hit = page.locator(
            '[data-chart-evidence-open="eff-row-nct04558918-apply-treatment"]'
        )
        assert hit.count() == 1
        box = hit.bounding_box()
        assert box is not None and box["width"] >= 24 and box["height"] >= 24
        hit.click()
        drawer_text = page.locator(
            "#kz-evidence-drawer-panel, #data-basis-panel"
        ).first.inner_text()
        assert "分子\n来源未列示" in drawer_text
        assert "分子\n51" not in drawer_text
        assert "分母\n60" in drawer_text

        _open(page, b_pnh_site, "baseline-overview.html")
        baseline_rows = page.locator(".kz-chart-table__row").filter(
            has_text="基线样本量"
        )
        baseline_texts = baseline_rows.all_text_contents()
        assert baseline_texts
        assert any("治疗组" in text for text in baseline_texts)
        assert any("对照组" in text for text in baseline_texts)
        assert all("组别未列示" not in text for text in baseline_texts)
        unit_sets = page.evaluate(
            """() => window.__CHART_GROUPS__.map(group =>
              [...new Set(group.rows.map(row => row.unit).filter(Boolean))]
            )"""
        )
        assert unit_sets == [["人"], ["岁"], ["%"], ["g/dL"]]
        assert page.locator(".kz-b-page-meta").evaluate(
            "el => parseFloat(getComputedStyle(el).fontSize)"
        ) >= 16
        svg_sizes = page.locator(".kz-chart-group__chart svg text").evaluate_all(
            "els => els.map(el => parseFloat(getComputedStyle(el).fontSize))"
        )
        assert svg_sizes and min(svg_sizes) >= 16
        _open(page, b_pnh_site, "disposition-overview.html")
        disposition_groups = page.evaluate(
            """() => window.__CHART_GROUPS__.map(group => ({
              title: group.title_zh,
              crossTrial: group.cross_trial,
              trials: [...new Set(group.rows.map(row => row.trial_zh))]
            }))"""
        )
        assert len(disposition_groups) >= 4
        assert all(group["crossTrial"] for group in disposition_groups)
        assert all(
            "APPLY-PNH" in group["trials"] and "APPOINT-PNH" in group["trials"]
            for group in disposition_groups
        )
        assert any("完成研究" in group["title"] for group in disposition_groups)
        apply_values = page.evaluate(
            """() => Object.fromEntries(window.__CHART_GROUPS__
              .flatMap(group => group.rows)
              .filter(row => row.trial_id === 'nct04558918')
              .map(row => [row.row_id, row.numeric_value]))"""
        )
        assert apply_values["trial-disposition-row_983d452b94d70c4a5ccea9ab"] == 62
        assert apply_values["trial-disposition-row_8b8342b9666d71ad12652c60"] == 35
        assert apply_values["trial-disposition-row_19455d9d5a4fddbe4ce2446d"] == 61
        assert apply_values["trial-disposition-row_cb4282ed9a30a404d400f406"] == 35
        chart_axes = page.evaluate(
            """() => [...document.querySelectorAll('[data-chart-type="bar"]')].map(node =>
              window.echarts.getInstanceByDom(node).getModel().getComponent('xAxis').option.data
            )"""
        )
        assert all(len(labels) <= 9 for labels in chart_axes)

        _open(page, b_pnh_site, "overview.html")
        page.locator("#kz-filter-panel > summary").click()
        assert page.locator(
            '.kz-b-filter-more .kz-b-filter-group[data-filter-dimension="element"]'
        ).count() == 1
        direct_groups = page.locator(
            ".kz-b-filters > .kz-b-filter-group"
        ).evaluate_all("els => els.map(el => el.dataset.filterDimension)")
        assert "element" not in direct_groups
        group_text = page.locator(
            '.kz-b-filter-group[data-filter-dimension="group"]'
        ).first.inner_text()
        assert "组别未列示" not in group_text
        assert "不适用" not in group_text

        browser.close()


def _launch(playwright: Playwright, browser_name: str) -> Browser:
    return getattr(playwright, browser_name).launch()


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("width", (320, 390))
def test_pnh_narrow_heatmap_keeps_readable_cells_after_resize(
    b_pnh_site: Path, browser_name: str, width: int
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(page, b_pnh_site, "safety.html")
        page.set_viewport_size({"width": width, "height": 844})
        page.wait_for_timeout(300)
        grids = page.evaluate(
            """() => [...document.querySelectorAll('[data-chart-type="heatmap"]')]
              .map(node => {
                const chart = window.echarts.getInstanceByDom(node);
                const model = chart.getModel();
                const rect = model.getComponent('grid').coordinateSystem.getRect();
                return {width: rect.width, right: rect.x + rect.width,
                  chartWidth: chart.getWidth(),
                  arms: model.getComponent('xAxis').option.data.length};
              })"""
        )
        assert grids
        assert all(grid["width"] >= 90 for grid in grids)
        assert all(grid["width"] / grid["arms"] >= 40 for grid in grids)
        assert all(grid["right"] <= grid["chartWidth"] for grid in grids)
        labels = page.locator('[data-chart-type="heatmap"]').first.locator(
            "svg text"
        ).all_text_contents()
        assert "治疗组" in labels and "对照组" in labels
        label_boxes = page.locator('[data-chart-type="heatmap"]').first.evaluate(
            """node => Object.fromEntries([...node.querySelectorAll('svg text')]
              .filter(text => ['治疗组', '对照组'].includes(text.textContent))
              .map(text => [text.textContent, {
                left: text.getBoundingClientRect().left,
                right: text.getBoundingClientRect().right}]))"""
        )
        assert label_boxes["治疗组"]["right"] + 2 <= label_boxes["对照组"]["left"]
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()


def _open(page: Page, site: Path, relative: str) -> None:
    page.goto((site / relative).as_uri(), wait_until="domcontentloaded")
    page.wait_for_timeout(250)


def _expand_complete_tables(page: Page) -> None:
    """完整折叠表默认收起；验证表格内交互前先展开。"""
    summaries = page.locator("#kz-chart-module .kz-complete-table > summary")
    for index in range(summaries.count()):
        summaries.nth(index).click()
    page.wait_for_timeout(100)


def _sitemap(site: Path) -> list[dict[str, object]]:
    payload = json.loads((site / "data/sitemap.json").read_text(encoding="utf-8"))
    routes = payload["routes"]
    assert isinstance(routes, list)
    return routes


def _route_path(entry: dict[str, object]) -> str:
    path = entry.get("path")
    assert isinstance(path, str)
    return path


def _chart(page: Page):
    chart = page.locator("#kz-chart-module .kz-chart-group__chart").first
    assert chart.count() == 1
    return chart


def test_b_home_default_main_chart_is_visible_with_real_geometry(b_site: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, b_site, "overview.html")
        chart = _chart(page)
        assert chart.is_visible()
        box = chart.bounding_box()
        assert box is not None
        assert box["width"] >= 320
        assert box["height"] >= 160
        assert box["x"] >= 0
        assert box["x"] + box["width"] <= 1280 + 1
        assert page.evaluate("() => document.documentElement.scrollWidth") <= 1281
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_longitudinal_small_multiples_share_axes_and_keep_labels_readable(
    b_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, b_site, "longitudinal-results.html")
        axes = page.evaluate(
            """() => Array.from(document.querySelectorAll('.kz-chart-group__chart'))
              .map(node => {
                if (node.dataset.chartType === 'single-fact') {
                  return {kind: 'fact', value: node.querySelector('strong')?.textContent,
                    hasSvg: !!node.querySelector('svg, canvas')};
                }
                const chart = window.echarts.getInstanceByDom(node);
                if (!chart) return {kind: 'missing'};
                const model = chart.getModel();
                return {
                  kind: 'chart',
                  extent: model.getComponent('yAxis').axis.scale.getExtent(),
                  xFont: model.getComponent('xAxis').option.axisLabel.fontSize,
                  yFont: model.getComponent('yAxis').option.axisLabel.fontSize
                };
              })"""
        )
        assert axes
        assert all(axis["kind"] != "missing" for axis in axes)
        assert all(
            axis["xFont"] >= 14 and axis["yFont"] >= 16
            for axis in axes if axis["kind"] == "chart"
        )
        assert all(
            axis["value"] and not axis["hasSvg"]
            for axis in axes if axis["kind"] == "fact"
        )
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_core_chart_and_complete_table_share_stable_fact_rows(
    b_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, b_site, "efficacy.html")
        _expand_complete_tables(page)
        group = page.locator("#kz-chart-module .kz-chart-module__group").first
        chart = group.locator(".kz-chart-group__chart")
        table = group.locator("table")
        chart_box = chart.bounding_box()
        table_box = table.bounding_box()
        assert chart_box is not None and table_box is not None
        assert chart_box["y"] < table_box["y"]
        assert table.locator("caption").count() == 1
        assert table.locator("thead th[scope]").count() >= 3

        chart_ids = page.evaluate(
            """() => window.__CHART_SYNC__.getChartRowIds()"""
        )
        table_ids = page.locator("#kz-chart-module .kz-chart-table__row").evaluate_all(
            "nodes => nodes.map(node => node.getAttribute('data-row-id'))"
        )
        assert chart_ids
        assert set(chart_ids) == set(table_ids)
        assert all(
            page.evaluate(
                "rowId => window.__EVIDENCE_DRAWER__.hasView(rowId)",
                row_id,
            )
            for row_id in table_ids
        )
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_product_filter_uses_repeated_params_and_restores_after_reload(
    b_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, b_site, "efficacy.html")
        buttons = page.locator('[data-filter-dimension="product"] button')
        assert buttons.count() >= 2
        values: list[str] = []
        for index in range(2):
            button = buttons.nth(index)
            value = button.get_attribute("data-filter-value") or button.get_attribute("data-val")
            assert value
            values.append(value)
            button.click()
        query = parse_qs(urlsplit(page.url).query, keep_blank_values=True)
        assert query.get("product") == values
        assert page.locator(".kz-chart-table__row:not([hidden])").count() > 0

        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        restored = page.locator(
            '[data-filter-dimension="product"] button[aria-pressed="true"], '
            '[data-filter-dimension="product"] button[aria-checked="true"]'
        )
        restored_values = [
            restored.nth(index).get_attribute("data-filter-value")
            or restored.nth(index).get_attribute("data-val")
            for index in range(restored.count())
        ]
        assert set(restored_values) == set(values)
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_row_opens_data_basis_and_restores_focus_in_url(
    b_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, b_site, "efficacy.html")
        _expand_complete_tables(page)
        trigger = page.locator("#kz-chart-module [data-evidence-open]").first
        assert trigger.count() == 1
        row_id = trigger.get_attribute("data-evidence-open")
        assert row_id
        trigger.click()

        panel = page.locator("#kz-evidence-drawer-panel, #data-basis-panel").first
        assert panel.is_visible()
        assert "数据依据" in panel.inner_text()
        assert "来源待核" in panel.inner_text()
        assert "原文未提供" in panel.inner_text()
        assert "ClinicalTrials.gov" not in panel.inner_text()
        assert "focus=" in page.url
        assert row_id in panel.inner_text() or page.locator(
            f'[data-row-id="{row_id}"]'
        ).count() >= 1

        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        assert panel.is_visible()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("key", ("Enter", " "))
def test_b_evidence_cell_enter_and_space_open_drawer_without_pageerror(
    b_pnh_site: Path, browser_name: str, key: str
) -> None:
    """RED: B 表证据单元格 Enter/Space 不得触发未定义 activateRow 运行错误。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        _open(page, b_pnh_site, "efficacy.html")
        _expand_complete_tables(page)

        cell = page.locator(
            '[data-row-id="eff-row-nct04558918-apply-treatment"] '
            "td[data-evidence-open]:not(:has(a))"
        ).first
        assert cell.count() == 1
        cell.scroll_into_view_if_needed()
        cell.focus()
        page.keyboard.press(key)

        panel = page.locator("#kz-evidence-drawer-panel, #data-basis-panel").first
        assert panel.is_visible()
        assert page.evaluate("() => window.__EVIDENCE_DRAWER__.isOpen()") is True
        assert (
            page.evaluate("() => window.__EVIDENCE_DRAWER__.getOpenRowId()")
            == "eff-row-nct04558918-apply-treatment"
        )
        assert page_errors == [], f"pageerror during {key!r}: {page_errors}"
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_desktop_search_escape_keeps_results_closed(
    b_pnh_site: Path, browser_name: str
) -> None:
    """RED: 桌面全局搜索 Esc 关闭后，不得被 input[type=search] 原生清空重开。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(page, b_pnh_site, "overview.html")

        search = page.locator("#global-search-input")
        assert search.is_visible()
        search.click()
        page.keyboard.type("疗效")
        page.wait_for_timeout(150)
        results = page.locator("#global-search-results")
        assert results.get_attribute("hidden") is None
        assert page.locator(".site-header__search-result").count() > 0

        page.keyboard.press("Escape")
        # Chromium may clear the query after the portal handler hides results;
        # give the native input event a beat to reopen if the bug is present.
        page.wait_for_timeout(250)
        assert search.input_value() == "疗效"
        assert results.is_hidden() or results.get_attribute("hidden") is not None
        assert page.locator(".site-header__search-result:visible").count() == 0

        # A prior outside click hides results while the query remains. Escape
        # must still preserve that query instead of reopening all results.
        page.locator("main").click(position={"x": 8, "y": 8})
        assert results.is_hidden()
        search.focus()
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        assert search.input_value() == "疗效"
        assert results.is_hidden() or results.get_attribute("hidden") is not None
        assert page.locator(".site-header__search-result:visible").count() == 0
        browser.close()

@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_mobile_menu_open_focuses_search_input(
    b_pnh_site: Path, browser_name: str
) -> None:
    """RED: 768 菜单展开后，全局搜索必须自动获得焦点。"""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 768, "height": 900})
        _open(page, b_pnh_site, "overview.html")

        toggle = page.locator("#menu-toggle")
        search = page.locator("#global-search-input")
        assert toggle.is_visible()
        assert not search.is_visible()

        toggle.click()

        assert page.locator(".site-header__nav.is-open").count() == 1
        assert search.is_visible()
        assert search.evaluate("node => node === document.activeElement")
        browser.close()

@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("relative", RESPONSIVE_PAGES)
@pytest.mark.parametrize("width", (1440, 2560))
def test_b_desktop_tables_keep_all_columns_reachable(
    b_pnh_site: Path, browser_name: str, relative: str, width: int
) -> None:
    """0923V1: internal scrolling is allowed; the last fact must remain reachable."""
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": width, "height": 900})
        _open(page, b_pnh_site, relative)

        containers = page.locator(".kz-b-table-scroll")
        assert containers.count() > 0, relative
        metrics = containers.evaluate_all(
            """nodes => nodes.map(node => {
              const row = node.querySelector("tbody tr");
              const cells = row ? Array.from(row.children) : [];
              node.scrollLeft = node.scrollWidth;
              const containerBox = node.getBoundingClientRect();
              const lastBox = cells.at(-1)?.getBoundingClientRect();
              return {
                cellCount: cells.length,
                lastCellReachable: !!lastBox && lastBox.width > 0 &&
                  lastBox.left >= containerBox.left - 1 &&
                  lastBox.right <= containerBox.right + 1
              };
            })"""
        )
        assert all(item["cellCount"] > 0 for item in metrics), metrics
        assert all(item["lastCellReachable"] for item in metrics), metrics
        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_safety_table_keeps_explicit_zero_distinct_from_missing(
    b_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, b_site, "safety.html")
        _expand_complete_tables(page)
        zero_row = page.locator('[data-row-id="safe-fixture-teae"]').first
        missing_row = page.locator('[data-row-id="safe-fixture-sae"]').first
        assert zero_row.count() == 1 and missing_row.count() == 1
        assert "0" in zero_row.inner_text()
        assert any(state in missing_row.inner_text() for state in ("未公开", "未报告"))
        assert zero_row.inner_text() != missing_row.inner_text()
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_all_routes_load_without_console_errors_or_remote_requests(
    b_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors: list[str] = []
        console_errors: list[str] = []
        remote_requests: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "request",
            lambda request: remote_requests.append(request.url)
            if request.url.startswith(("http:", "https:"))
            else None,
        )
        for entry in _sitemap(b_site):
            relative = _route_path(entry)
            _open(page, b_site, relative)
            assert page.locator("main h1").count() == 1, relative
            assert page.locator(".site-footer").count() == 1, relative
            assert page.locator("html[lang='zh-CN']").count() == 1, relative
        assert page_errors == []
        assert console_errors == []
        assert remote_requests == []
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
@pytest.mark.parametrize("width", RESPONSIVE_WIDTHS)
@pytest.mark.parametrize("relative", RESPONSIVE_PAGES)
def test_b_core_pages_fit_viewport_without_page_horizontal_overflow(
    b_site: Path, browser_name: str, width: int, relative: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": width, "height": 900})
        _open(page, b_site, relative)
        chart = _chart(page)
        chart.scroll_into_view_if_needed()
        metrics = page.evaluate(
            """() => {
              const charts = [...document.querySelectorAll(
                '#kz-chart-module .kz-chart-group__chart'
              )];
              const rects = charts.map(node => {
                const box = node.getBoundingClientRect();
                return {
                  left: box.left,
                  right: box.right,
                  width: box.width,
                  height: box.height,
                  scrollWidth: node.scrollWidth,
                  clientWidth: node.clientWidth
                };
              });
              return {
                viewport: innerWidth,
                documentWidth: document.documentElement.scrollWidth,
                bodyWidth: document.body.scrollWidth,
                rects
              };
            }"""
        )
        assert metrics["viewport"] == width
        assert max(metrics["documentWidth"], metrics["bodyWidth"]) <= width + 1
        assert metrics["rects"]
        for rect in metrics["rects"]:
            assert rect["width"] > 0
            assert rect["height"] > 0
            assert rect["left"] >= -1
            assert rect["right"] <= width + 1
            assert rect["scrollWidth"] <= rect["clientWidth"] + 1
        browser.close()


@pytest.mark.parametrize("browser_name", BROWSERS)
def test_b_product_and_trial_dossiers_are_reachable_from_profile_page(
    b_site: Path, browser_name: str
) -> None:
    with sync_playwright() as playwright:
        browser = _launch(playwright, browser_name)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open(page, b_site, "product-trial-profiles.html")
        product_link = page.locator('a[href^="products/"]').first
        trial_link = page.locator('a[href^="trials/"]').first
        assert product_link.count() == 1 and trial_link.count() == 1
        product_href = product_link.get_attribute("href")
        trial_href = trial_link.get_attribute("href")
        assert product_href and trial_href

        _open(page, b_site, product_href)
        assert page.locator("[data-product-id]").count() == 1
        assert page.locator("#kz-chart-module").count() == 1
        assert page.locator("table").count() >= 1
        product_chart = _chart(page).bounding_box()
        product_table = page.locator("#kz-chart-module table").first.bounding_box()
        assert product_chart is not None and product_table is not None
        assert product_chart["y"] < product_table["y"]

        _open(page, b_site, trial_href)
        assert page.locator("[data-trial-id]").count() == 1
        assert page.locator("#kz-chart-module").count() == 1
        assert page.locator("table").count() >= 1
        trial_chart = _chart(page).bounding_box()
        trial_table = page.locator("#kz-chart-module table").first.bounding_box()
        assert trial_chart is not None and trial_table is not None
        assert trial_chart["y"] < trial_table["y"]

        browser.close()
