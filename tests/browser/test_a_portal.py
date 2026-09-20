"""Task 5.4：用真实浏览器操作 A 类门户，而非只扫描 HTML。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site

ROOT = Path(__file__).resolve().parents[2]
FRESH_A_CONTENT = ROOT / "fixtures/positive/a-atopic-dermatitis/research-content.json"


@pytest.fixture(scope="module")
def a_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    project = tmp_path_factory.mktemp("a-browser")
    result = run_fixture_case(
        "a-complete", project_root=project, reports=["A"], outputs=["html"]
    )
    assert result.run_result.outcome == "completed"
    return project / "reports/A/v-fixture-001/html"


@pytest.fixture(scope="module")
def full_a_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    project = tmp_path_factory.mktemp("a-browser-full")
    payload = json.loads(FRESH_A_CONTENT.read_text(encoding="utf-8"))
    data = ReportAPortalData.model_validate(payload["report_data"])
    render_report_a_site(data, project)
    return project


@pytest.fixture()
def page() -> Page:
    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        current = context.new_page()
        yield current
        context.close()
        browser.close()


def _open(page: Page, site: Path, relative: str) -> None:
    page.goto((site / relative).as_uri(), wait_until="domcontentloaded")
    page.wait_for_timeout(250)


def test_a_home_has_landscape_efficacy_safety_and_matrix_summaries(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "overview.html")
    for module in ("landscape", "efficacy", "safety", "matrix"):
        block = page.locator(f'[data-summary-module="{module}"]')
        assert block.count() == 1
        assert block.locator(".kz-chart").count() == 1
        assert block.locator("a").count() >= 1
    assert page.locator('[data-target-group]').count() >= 2
    ambient = page.locator(".kz-a-page-ambient")
    assert ambient.get_attribute("aria-hidden") == "true"
    assert ambient.bounding_box() is not None


def test_a_home_efficacy_preserves_all_endpoints_and_timepoints(
    page: Page, full_a_site: Path
) -> None:
    """首页不再挑选单一终点或最近时间点替代其他观察。"""
    _open(page, full_a_site, "overview.html")
    labels = page.locator(
        '[data-chart-id="home-efficacy"] .kz-a-bar-label small'
    ).all_inner_texts()

    assert len(labels) >= 28
    payload = json.loads(FRESH_A_CONTENT.read_text(encoding="utf-8"))
    expected = {row["row_id"] for row in payload["report_data"]["efficacy"]}
    assert set(page.locator('[data-chart-id="home-efficacy"] [data-row-id]').evaluate_all(
        "nodes => nodes.map(node => node.dataset.rowId)"
    )) == expected


def test_a_header_keeps_logo_primary_navigation_and_more_menu(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "companies-transactions.html")
    logo = page.locator(".site-header__logo img")
    assert logo.is_visible()
    assert logo.evaluate("node => node.naturalWidth") > 0
    more = page.locator(".kz-a-more-nav")
    assert more.is_visible()
    assert more.get_attribute("open") is None
    more.locator("summary").click()
    assert more.get_by_role("link", name="企业与交易", exact=True).get_attribute(
        "aria-current"
    ) == "page"


def test_a_product_dossier_for_fixture_slug_preserves_all_sections(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "products/fixture-product.html")
    for section in (
        "基本信息",
        "作用机制与给药",
        "临床开发组合",
        "关键疗效",
        "关键安全性",
        "中国与全球监管",
        "企业与交易",
        "专利与保护",
    ):
        assert page.get_by_role("heading", name=section, exact=True).count() == 1


def test_a_clinical_portfolio_filters_product_target_phase_and_region(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "clinical-portfolio.html")
    for dim in ("product", "target", "phase", "region"):
        assert page.locator(f'[data-filter-dimension="{dim}"]').count() == 1
    page.locator('[data-filter-dimension="target"] button').first.click()
    visible_rows = page.locator("tbody tr:not([hidden])")
    assert 0 < visible_rows.count() < page.locator("tbody tr").count()
    assert "target=" in page.url


def test_a_efficacy_page_shows_chart_before_complete_table_and_controls(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "efficacy.html")
    chart = page.locator('[data-module="efficacy"] .kz-chart')
    table = page.locator('[data-module="efficacy"] table')
    assert chart.bounding_box() and table.bounding_box()
    assert chart.bounding_box()["y"] < table.bounding_box()["y"]  # type: ignore[index]
    assert page.get_by_text("治疗组", exact=True).count() >= 1
    assert page.get_by_text("对照组", exact=True).count() >= 1
    assert page.locator('[data-filter-dimension="endpoint"]').count() == 1
    rows = page.locator(".kz-a-bar-row")
    assert rows.count() >= 4
    for index in range(rows.count()):
        assert rows.nth(index).locator(".kz-a-bar-lane").count() == 2


def test_a_efficacy_endpoint_and_timepoint_are_single_select_and_drive_title(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "efficacy.html")
    endpoint = page.locator('[data-filter-dimension="endpoint"] button').first
    timepoint = page.locator('[data-filter-dimension="timepoint"] button').first
    endpoint.click()
    timepoint.click()

    assert (
        page.locator('[data-filter-dimension="endpoint"] button[aria-pressed="true"]').count()
        == 1
    )
    assert (
        page.locator('[data-filter-dimension="timepoint"] button[aria-pressed="true"]').count()
        == 1
    )
    title = timepoint.inner_text() + endpoint.inner_text()
    assert title in page.locator("[data-efficacy-heading] h2").inner_text()
    assert title in page.locator('[data-chart-id="efficacy-full"]').get_attribute("aria-label")

def test_a_safety_page_shows_multidimensional_heatmap_before_table(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "safety.html")
    chart = page.locator('[data-module="safety"] .kz-chart')
    table = page.locator('[data-module="safety"] table')
    assert chart.bounding_box() and table.bounding_box()
    assert chart.bounding_box()["y"] < table.bounding_box()["y"]  # type: ignore[index]
    for term in ("严重不良事件", "治疗期间不良事件", "常见不良事件"):
        assert page.get_by_text(term, exact=True).count() >= 1


def test_a_matrix_page_updates_bubble_axes_size_filters_and_table(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "matrix.html")
    chart = page.locator('[data-module="matrix"] .kz-chart')
    before = chart.get_attribute("data-view-digest")
    coverage = page.locator("[data-matrix-coverage]")
    assert coverage.is_visible()
    assert "绘入" in coverage.inner_text()
    page.locator('[data-matrix-control="safety-axis"]').select_option(index=1)
    after = chart.get_attribute("data-view-digest")
    assert before != after
    assert page.get_by_text("气泡大小：治疗组样本量", exact=True).count() == 1
    assert chart.locator(".kz-a-axis-tick--x").count() == 5
    assert chart.locator(".kz-a-axis-tick--y").count() == 5
    initial_values = chart.locator(".kz-a-bubble").evaluate_all(
        "nodes => nodes.map(node => node.dataset.efficacyValue)"
    )
    page.locator('[data-matrix-control="efficacy-axis"]').select_option(index=1)
    changed_values = chart.locator(".kz-a-bubble").evaluate_all(
        "nodes => nodes.map(node => node.dataset.efficacyValue)"
    )
    assert changed_values != initial_values
    page.locator('[data-matrix-control="bubble-size"]').select_option(index=1)
    assert page.get_by_text("气泡大小：全部随机样本量", exact=True).count() == 1

    assert page.locator('[data-module="matrix"] table tbody tr:not([hidden])').count() >= 3

def test_a_matrix_bubble_and_legend_open_accessible_product_insight_drawer(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "matrix.html")
    bubble = page.locator('[data-chart-id="matrix-full"] .kz-a-bubble').first
    product_id = bubble.get_attribute("data-product-id")
    assert product_id
    assert bubble.get_attribute("data-a-product-focus") == product_id
    assert bubble.get_attribute("type") == "button"

    bubble.focus()
    bubble.press("Enter")
    drawer = page.locator("#a-product-insight-drawer")
    assert drawer.is_visible()
    assert drawer.get_attribute("role") == "dialog"
    assert drawer.get_attribute("aria-modal") == "true"
    assert drawer.get_attribute("data-product-id") == product_id
    assert page.locator("#a-product-insight-close").evaluate(
        "node => document.activeElement === node"
    )
    for tab in ("疗效", "安全性", "产品档案", "数据依据"):
        assert drawer.get_by_role("tab", name=tab, exact=True).count() == 1
    assert "疗效治疗组/对照组" in drawer.inner_text()
    assert "治疗组样本量" in drawer.inner_text()
    assert "总样本量" in drawer.inner_text()
    assert f"focus={product_id}" in page.url

    drawer.get_by_role("tab", name="产品档案", exact=True).click()
    dossier = drawer.get_by_role("link", name="查看完整产品档案", exact=True)
    assert dossier.get_attribute("href") == f"products/{product_id}.html"
    page.keyboard.press("Escape")
    assert not drawer.is_visible()
    assert page.url.find("focus=") == -1
    assert bubble.evaluate("node => document.activeElement === node")

    legend = page.locator('[data-chart-id="matrix-full"] .kz-a-bubble-key button').first
    legend.click()
    assert drawer.is_visible()
    assert drawer.get_attribute("data-product-id") == legend.get_attribute("data-product-id")
    drawer.get_by_role("button", name="关闭产品洞察", exact=True).click()


def test_a_matrix_product_insight_focus_restores_from_shared_url(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "matrix.html")
    product_id = page.locator('[data-chart-id="matrix-full"] .kz-a-bubble').first.get_attribute(
        "data-product-id"
    )
    assert product_id
    url = (a_site / "matrix.html").as_uri() + f"?focus={product_id}"
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(250)
    drawer = page.locator("#a-product-insight-drawer")
    assert drawer.is_visible()
    assert drawer.get_attribute("data-product-id") == product_id
    assert page.locator("#a-product-insight-close").evaluate(
        "node => document.activeElement === node"
    )

def test_a_all_empty_aesi_is_removed_from_page_chart_legend_and_table(
    page: Page, full_a_site: Path
) -> None:
    for relative in ("overview.html", "safety.html", "matrix.html", "products/amlitelimab.html"):
        _open(page, full_a_site, relative)
        main = page.locator("main")
        assert "特别关注不良事件" not in main.inner_text()
        assert "AESI" not in main.inner_text()
        assert page.locator(
            '[data-filter-dimension] [data-filter-value*="AESI"]'
        ).count() == 0
        assert page.locator(
            'tbody tr[data-category="特别关注不良事件"], '
            '[data-heat-label="event"][data-heat-event="预先界定AESI"]'
        ).count() == 0


def test_a_matrix_keeps_amlitelimab_on_one_trial_and_excludes_ak120_pooled_safety(
    page: Page, full_a_site: Path
) -> None:
    _open(page, full_a_site, "matrix.html")
    amlitelimab = page.locator('.kz-a-bubble[aria-label^="阿姆特利单抗（Amlitelimab）："]')
    assert amlitelimab.count() == 1
    assert amlitelimab.get_attribute("data-trial-id") == "nct05131477"
    assert amlitelimab.get_attribute("data-arm-detail")
    assert "NCT05131477" in amlitelimab.get_attribute("title")
    assert page.locator('.kz-a-bubble[aria-label^="AK120："]').count() == 0


def test_a_legacy_pages_do_not_promote_source_categories_to_citations(
    page: Page, a_site: Path
) -> None:
    """旧证据第 12 页已并入每页的外部来源与数据依据，逐页核对其专业中文表达。"""
    for relative in (
        "overview.html",
        "landscape.html",
        "product-overview.html",
        "clinical-portfolio.html",
        "efficacy.html",
        "safety.html",
        "matrix.html",
        "regulatory.html",
        "companies-transactions.html",
        "patents-protection.html",
        "historical-edge.html",
    ):
        _open(page, a_site, relative)
        sources = page.locator("#external-sources")
        assert sources.locator("li").count() == 0
        assert "未绑定可核验的公共来源谱系" in sources.inner_text()
        assert "来源类别说明不代表具体出处" in sources.inner_text()
        assert page.locator("#data-basis-panel").count() == 1
        visible = page.locator("body").inner_text()
        for forbidden in ("prompt", "route", "pipeline", "gate", "signal", "accepted", "pending"):
            assert forbidden not in visible.lower()


def test_a_sitemap_matches_every_static_page_and_every_product_in_snapshot(
    page: Page, a_site: Path
) -> None:
    manifest = json.loads(
        (a_site.parent / "html.manifest.json").read_text(encoding="utf-8")
    )
    static_pages = manifest["pages_or_sections"]
    assert len(static_pages) == 11
    expected = len(static_pages) + len(manifest["product_ids"])
    sitemap = json.loads((a_site / "data/sitemap.json").read_text(encoding="utf-8"))
    assert len(sitemap["routes"]) == expected
    for item in sitemap["routes"]:
        target = a_site / item["path"]
        assert target.is_file()
        _open(page, a_site, item["path"])
        assert page.locator("main h1").count() == 1
        assert page.locator(".site-footer").count() == 1


@pytest.mark.parametrize(
    ("relative", "chart_type"),
    [
        ("landscape.html", "landscape"),
        ("clinical-portfolio.html", "portfolio"),
        ("regulatory.html", "timeline"),
        ("companies-transactions.html", "network"),
        ("patents-protection.html", "timeline"),
        ("historical-edge.html", "timeline"),
    ],
)
def test_a_structural_charts_have_real_information_nodes_not_empty_frames(
    page: Page, a_site: Path, relative: str, chart_type: str
) -> None:
    _open(page, a_site, relative)
    chart = page.locator(f'[data-a-chart="{chart_type}"]').first
    assert chart.is_visible()
    assert chart.locator('[data-visual-node]').count() >= 4
    text = chart.inner_text().strip()
    assert len(text) >= 24


def test_a_regulatory_timeline_uses_chronological_reading_order(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "regulatory.html")
    dates = page.locator('[data-a-chart="timeline"] [data-visual-node] small').all_inner_texts()
    assert dates == sorted(dates)


def test_a_structural_chart_captions_describe_the_visual_that_is_rendered(
    page: Page, a_site: Path
) -> None:
    for relative in ("landscape.html", "clinical-portfolio.html"):
        _open(page, a_site, relative)
        assert "圆点" not in page.locator("main").inner_text()


def test_a_every_page_explains_sources_with_coverage_and_limits_not_an_empty_frame(
    page: Page, a_site: Path
) -> None:
    """旧证据页的信息图职责由每页外部来源清单承接，不得是空框架。"""
    for relative in ("overview.html", "efficacy.html", "matrix.html"):
        _open(page, a_site, relative)
        sources = page.locator("#external-sources")
        assert sources.is_visible()
        assert "外部来源" in sources.inner_text()
        for source in sources.locator("li").all():
            entry = source.inner_text()
            assert "覆盖：" in entry
            assert "限制：" in entry
            assert len(entry.strip()) >= 12


def test_a_product_dossier_charts_only_show_the_current_product(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "products/fixture-product.html")
    efficacy_chart = page.locator('[data-chart-id="product-efficacy"]')
    assert efficacy_chart.locator(".kz-a-bar-row").count() == 1
    assert "安澜双抗" not in efficacy_chart.inner_text()
    safety_chart = page.locator('[data-chart-id="product-safety"]')
    assert set(
        safety_chart.locator("[data-heat-label='product']").all_inner_texts()
    ) == {"泰瑞奇单抗"}
    assert "安澜双抗" not in safety_chart.inner_text()


def test_a_user_visible_fixture_uses_medical_demo_labels_not_backend_tokens(
    page: Page, a_site: Path
) -> None:
    for relative in (
        "clinical-portfolio.html",
        "patents-protection.html",
        "products/fixture-product.html",
    ):
        _open(page, a_site, relative)
        visible = page.locator("main").inner_text().lower()
        assert "fixture" not in visible
        assert "wo-comp" not in visible


def test_a_matrix_explains_safety_direction_without_conflicting_arrow_shorthand(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "matrix.html")
    chart = page.locator('[data-a-chart="matrix"]')
    assert "发生率（越低越靠上）" in chart.inner_text()
    assert "任何TEAE↓" not in chart.inner_text()
    assert "不作为头对头结论" in page.locator('[data-module="matrix"]').inner_text()


def test_a_matrix_uses_stable_medical_scales_and_restorable_url_settings(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "matrix.html")
    chart = page.locator('[data-a-chart="matrix"]')
    assert {"0.0%", "25.0%", "50.0%", "75.0%", "100.0%"} <= set(
        chart.locator(".kz-a-axis-tick").all_inner_texts()
    )
    page.locator('[data-matrix-control="efficacy-axis"]').select_option(index=1)
    page.locator('[data-matrix-control="safety-axis"]').select_option(index=1)
    page.locator('[data-matrix-control="bubble-size"]').select_option(index=1)
    assert "matrix_x=difference" in page.url
    assert "matrix_y=sae" in page.url
    assert "matrix_size=total" in page.url
    page.reload()
    assert (
        page.locator('[data-matrix-control="efficacy-axis"]').input_value()
        == "治疗组与对照组差值"
    )
    assert page.locator('[data-matrix-control="safety-axis"]').input_value() == "任何SAE发生率"
    assert page.locator('[data-matrix-control="bubble-size"]').input_value() == "全部随机样本量"
    assert "10.0%" in chart.locator(".kz-a-axis-tick").all_inner_texts()


def test_a_safety_heatmap_uses_distinct_continuous_colors_within_each_event(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "safety.html")
    cells = page.locator(
        '[data-a-chart="safety"] .kz-a-safety-observation[data-heat-event="任何TEAE"] strong'
    )
    teae_backgrounds = cells.evaluate_all("nodes => nodes.map(node => node.style.background)")
    assert len(set(teae_backgrounds)) == 4
    assert "固定0至100%刻度" in page.locator('[data-a-chart="safety"]').inner_text()


def test_a_evidence_panel_lists_specific_trials_sources_and_cutoff(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "efficacy.html")
    page.get_by_role("button", name="查看数据依据").click()
    panel = page.locator("#data-basis-panel")
    visible = panel.inner_text()
    assert "示例登记号301" in visible
    assert "治疗组样本量：210" in visible
    assert "ClinicalTrials.gov" in visible
    assert "2026年07月31日" in visible


def test_a_history_distinguishes_past_events_from_current_product_status(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "historical-edge.html")
    visible = page.locator("main").inner_text()
    assert "曾暂停（已恢复）" in visible
    assert "早期方案撤回" in visible


def test_a_home_safety_heatmap_keeps_the_last_product_fully_inside_its_card(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "overview.html")
    chart = page.locator('[data-chart-id="home-safety"]')
    last_product = chart.locator("[data-heat-label='product']").last
    chart_box = chart.bounding_box()
    product_box = last_product.bounding_box()
    assert chart_box is not None and product_box is not None
    assert product_box["x"] + product_box["width"] <= chart_box["x"] + chart_box["width"]
    assert chart.evaluate("node => node.scrollWidth <= node.clientWidth")
    labels = chart.locator("[data-heat-label='product']").all_inner_texts()
    assert len(set(labels)) == 4
    assert all(
        grid.locator("[data-heat-label='product']").count() == 1
        for grid in chart.locator(".kz-a-safety-observation-group").all()
    )
    assert "诺维单抗" in chart.inner_text()


def test_a_safety_heatmap_keeps_numeric_results_from_each_published_window(
    page: Page, full_a_site: Path
) -> None:
    """默认热图不得用一个精确观察窗遮掉其他产品已公开的同维度数值。"""
    _open(page, full_a_site, "safety.html")

    coverage = page.evaluate(
        """() => {
            const expected = new Set(window.REPORT_A.safety
                .filter(row => row.term_key === 'any_teae'
                    && row.category === '治疗期间不良事件'
                    && (row.arm || '治疗组') === '治疗组'
                    && typeof row.value === 'number')
                .map(row => row.product_id));
            const shown = new Set([...document.querySelectorAll(
                '[data-chart-id="safety-full"] .kz-a-safety-observation[data-heat-key="any_teae"]'
            )].filter(cell => cell.querySelector('.kz-a-heat-value').textContent.includes('%'))
                .map(cell => cell.getAttribute('data-heat-product')));
            const expectedNames = new Set([...expected].map(id =>
                window.REPORT_A.products.find(product => product.id === id).name));
            const windows = new Set([...document.querySelectorAll(
                '[data-chart-id="safety-full"] '
                + '.kz-a-safety-observation[data-heat-key="any_teae"][data-time-window]'
            )].map(cell => cell.getAttribute('data-time-window')).filter(Boolean));
            return {
                expected: [...expectedNames].sort(),
                shown: [...shown].sort(),
                windows: [...windows]
            };
        }"""
    )

    assert coverage["expected"]
    assert coverage["shown"] == coverage["expected"]
    assert coverage["windows"]


def test_a_safety_product_filter_uses_the_selected_product_name(
    page: Page, full_a_site: Path
) -> None:
    _open(page, full_a_site, "safety.html")
    product_name = page.evaluate("window.REPORT_A.products[0].name")
    product_button = page.locator(
        f'[data-filter-dimension="product"] [data-filter-value="{product_name}"]'
    )
    product_button.evaluate("node => { node.closest('details').open = true; }")
    product_button.click()

    labels = page.locator(
        '[data-chart-id="safety-full"] [data-heat-label="product"]'
    ).all_inner_texts()
    assert labels
    assert set(labels) == {product_name}
    assert page.locator(
        '[data-chart-id="safety-full"] .kz-a-heat-value'
    ).filter(has_text="%").count() > 0


@pytest.mark.parametrize("viewport_width", (1024, 1280, 1440, 1920))
@pytest.mark.parametrize(
    ("relative", "chart_id"),
    (("overview.html", "home-safety"), ("safety.html", "safety-full")),
)
def test_a_safety_heatmap_does_not_horizontal_drag_at_default_desktop_widths(
    page: Page,
    full_a_site: Path,
    viewport_width: int,
    relative: str,
    chart_id: str,
) -> None:
    page.set_viewport_size({"width": viewport_width, "height": 900})
    _open(page, full_a_site, relative)
    chart = page.locator(f"[data-chart-id='{chart_id}']")
    chart.scroll_into_view_if_needed()
    chart_box = chart.bounding_box()
    assert chart_box is not None and chart_box["width"] > 0

    layout = page.evaluate(
        f"""() => ({{
            viewport: window.innerWidth,
            document: document.documentElement.scrollWidth,
            body: document.body.scrollWidth,
            pageX: window.scrollX,
            chart: document.querySelector('[data-chart-id="{chart_id}"]').scrollWidth,
            chartClient: document.querySelector('[data-chart-id="{chart_id}"]').clientWidth
        }})"""
    )
    assert max(layout["document"], layout["body"]) <= layout["viewport"]
    assert layout["chart"] <= layout["chartClient"]

    start_x = chart_box["x"] + chart_box["width"] - 12
    end_x = max(chart_box["x"] + 8, start_x - min(240, chart_box["width"] - 24))
    y = chart_box["y"] + min(24, chart_box["height"] / 2)
    page.mouse.move(start_x, y)
    page.mouse.down()
    page.mouse.move(end_x, y, steps=4)
    page.mouse.up()
    page.mouse.wheel(480, 0)
    page.wait_for_timeout(50)

    after = page.evaluate(
        f"""() => ({{
            pageX: window.scrollX,
            chart: document.querySelector('[data-chart-id="{chart_id}"]').scrollLeft
        }})"""
    )
    assert after == {"pageX": layout["pageX"], "chart": 0}


def test_a_safety_heatmap_keeps_dimension_headers_below_the_site_header(
    page: Page, full_a_site: Path
) -> None:
    page.set_viewport_size({"width": 1024, "height": 900})
    _open(page, full_a_site, "safety.html")
    chart = page.locator('[data-chart-id="safety-full"]')
    chart.scroll_into_view_if_needed()
    page.wait_for_timeout(100)

    header_top = chart.locator('[data-heat-label="event"]').first.evaluate(
        "node => node.getBoundingClientRect().top"
    )
    site_header_bottom = page.locator(".site-header").evaluate(
        "node => node.getBoundingClientRect().bottom"
    )
    assert header_top >= site_header_bottom

    page.mouse.wheel(0, 600)
    page.wait_for_timeout(100)
    visible_headers = chart.locator('[data-heat-label="event"]').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect())"
        ".filter(box => box.bottom > 64 && box.top < innerHeight)"
    )
    assert visible_headers
    assert min(box["top"] for box in visible_headers) >= site_header_bottom - 1


@pytest.mark.parametrize("viewport_width", (1024, 1280, 1440, 1920))
@pytest.mark.parametrize(
    ("relative", "chart_id"),
    (("overview.html", "home-safety"), ("safety.html", "safety-full")),
)
def test_a_shared_safety_matrix_remains_readable_at_common_viewports(
    page: Page,
    full_a_site: Path,
    viewport_width: int,
    relative: str,
    chart_id: str,
) -> None:
    """首页和安全性详情共用的热图必须在默认视野内完整、可读。"""
    page.set_viewport_size({"width": viewport_width, "height": 900})
    _open(page, full_a_site, relative)

    metrics = page.evaluate(
        f"""() => {{
            const chart = document.querySelector('[data-chart-id="{chart_id}"]');
            const chartBox = chart.getBoundingClientRect();
            const grids = [...chart.querySelectorAll(
                '.kz-a-safety-observation-group:not([hidden])')];
            const boxes = selector => grids.flatMap(grid =>
                [...grid.querySelectorAll(selector)]
                .filter(node => node.getBoundingClientRect().height > 0).map(node => {{
                    const box = node.getBoundingClientRect();
                    const style = getComputedStyle(node);
                    return {{
                        width: box.width,
                        height: box.height,
                        left: box.left,
                        right: box.right,
                        scrollWidth: node.scrollWidth,
                        clientWidth: node.clientWidth,
                        scrollHeight: node.scrollHeight,
                        clientHeight: node.clientHeight,
                        fontSize: parseFloat(style.fontSize),
                        lineHeight: parseFloat(style.lineHeight) || 0
                    }};
                }}));
            const products = boxes('[data-heat-label="product"]');
            const events = boxes('[data-heat-label="event"]');
            return {{
                viewport: window.innerWidth,
                documentWidth: document.documentElement.scrollWidth,
                bodyWidth: document.body.scrollWidth,
                chart: {{
                    left: chartBox.left,
                    right: chartBox.right,
                    width: chartBox.width,
                    clientWidth: chart.clientWidth,
                    scrollWidth: chart.scrollWidth
                }},
                grids: grids.map(grid => ({{
                    clientWidth: grid.clientWidth,
                    scrollWidth: grid.scrollWidth,
                    productCount: grid.querySelectorAll('[data-heat-label="product"]').length,
                    eventCount: grid.querySelectorAll('[data-heat-label="event"]').length
                }})),
                products,
                events
            }};
        }}"""
    )

    assert metrics["viewport"] == viewport_width
    assert max(metrics["documentWidth"], metrics["bodyWidth"]) <= viewport_width
    assert metrics["chart"]["scrollWidth"] <= metrics["chart"]["clientWidth"]
    assert metrics["chart"]["width"] > 0
    assert metrics["grids"]
    assert all(grid["scrollWidth"] <= grid["clientWidth"] for grid in metrics["grids"])
    assert all(grid["productCount"] == 1 for grid in metrics["grids"])
    assert all(grid["eventCount"] >= 1 for grid in metrics["grids"])

    for cell in metrics["products"]:
        assert cell["width"] >= 100
        assert cell["height"] >= 20
        assert cell["fontSize"] >= 16
        assert cell["lineHeight"] >= cell["fontSize"]
        assert cell["left"] >= metrics["chart"]["left"] - 1
        assert cell["right"] <= metrics["chart"]["right"] + 1
        assert cell["scrollWidth"] <= cell["clientWidth"] + 1
        assert cell["scrollHeight"] <= cell["clientHeight"] + 1

    for cell in metrics["events"]:
        assert cell["width"] >= 64
        assert cell["height"] >= 20
        assert cell["fontSize"] >= 16
        assert cell["lineHeight"] >= cell["fontSize"]
        assert cell["left"] >= metrics["chart"]["left"] - 1
        assert cell["right"] <= metrics["chart"]["right"] + 1
        assert cell["scrollWidth"] <= cell["clientWidth"] + 1
        assert cell["scrollHeight"] <= cell["clientHeight"] + 1


def test_a_safety_details_are_paginated_and_fit_at_1024(
    page: Page, full_a_site: Path
) -> None:
    page.set_viewport_size({"width": 1024, "height": 900})
    _open(page, full_a_site, "safety.html")

    table_wrap = page.locator("[data-paged-table]")
    complete_table = table_wrap.locator("details.kz-complete-table")
    assert complete_table.count() == 1
    assert complete_table.get_attribute("open") is None
    assert "第 1/" in page.locator("[data-page-status]").inner_text()
    complete_table.locator("summary").click()
    page.wait_for_timeout(100)
    assert complete_table.get_attribute("open") is not None

    rows = table_wrap.locator("tbody tr")
    visible_rows = table_wrap.locator("tbody tr:not([hidden])")
    assert rows.count() > 100
    assert visible_rows.count() == 50
    assert "第 1/" in page.locator("[data-page-status]").inner_text()
    assert "每页 50 条" in page.locator("[data-page-status]").inner_text()

    first_row = visible_rows.first.inner_text()
    page.locator('[data-page-action="next"]').click()
    page.wait_for_timeout(250)
    assert "第 2/" in page.locator("[data-page-status]").inner_text()
    assert visible_rows.count() == 50
    assert visible_rows.first.inner_text() != first_row

    layout = table_wrap.evaluate(
        "node => ({scrollWidth: node.scrollWidth, clientWidth: node.clientWidth})"
    )
    assert layout["scrollWidth"] <= layout["clientWidth"]
    dimension_box = visible_rows.first.locator("td").nth(3).bounding_box()
    row_box = visible_rows.first.bounding_box()
    assert dimension_box is not None and dimension_box["width"] >= 100
    assert row_box is not None and row_box["height"] < 120
    assert page.evaluate("document.documentElement.scrollHeight") < 100_000

    assert page.get_by_role(
        "heading", name="发生率与观察窗明细", exact=True
    ).count() == 1


def test_a_product_dossier_evidence_buttons_limit_trials_to_current_product(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "products/fixture-product.html")
    buttons = page.locator("[data-open-evidence]")
    assert buttons.count() >= 3
    buttons.nth(1).click()
    panel = page.locator("#data-basis-panel")
    assert "示例登记号301" in panel.inner_text()
    assert "示例登记号201" not in panel.inner_text()


def test_a_history_filter_labels_use_resolved_event_meaning(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "historical-edge.html")
    filter_group = page.locator('[data-filter-dimension="status"]')
    assert filter_group.get_by_role("button", name="曾暂停（已恢复）").count() == 1
    assert filter_group.get_by_role("button", name="早期方案撤回").count() == 1
