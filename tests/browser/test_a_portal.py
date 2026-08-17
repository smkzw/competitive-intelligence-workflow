"""Task 5.4：用真实浏览器操作 A 类门户，而非只扫描 HTML。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from ci_workflow.application.fixture_runner import run_fixture_case


@pytest.fixture(scope="module")
def a_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    project = tmp_path_factory.mktemp("a-browser")
    result = run_fixture_case(
        "a-complete", project_root=project, reports=["A"], outputs=["html"]
    )
    assert result.run_result.outcome == "completed"
    return project / "reports/A/v-fixture-001/html"


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


def test_a_safety_page_shows_multidimensional_heatmap_before_table(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "safety.html")
    chart = page.locator('[data-module="safety"] .kz-chart')
    table = page.locator('[data-module="safety"] table')
    assert chart.bounding_box() and table.bounding_box()
    assert chart.bounding_box()["y"] < table.bounding_box()["y"]  # type: ignore[index]
    for term in ("严重不良事件", "特别关注不良事件", "治疗期间不良事件", "常见不良事件"):
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


def test_a_evidence_page_is_professional_chinese_not_pipeline_log(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "evidence-limitations.html")
    visible = page.locator("body").inner_text()
    assert "研究依据与局限" in visible
    for forbidden in ("prompt", "route", "pipeline", "gate", "signal", "accepted", "pending"):
        assert forbidden not in visible.lower()


def test_a_sitemap_matches_every_static_page_and_every_product_in_snapshot(
    page: Page, a_site: Path
) -> None:
    manifest = json.loads(
        (a_site.parent / "html.manifest.json").read_text(encoding="utf-8")
    )
    expected = 12 + len(manifest["product_ids"])
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


def test_a_evidence_page_has_an_informative_visual_instead_of_an_empty_frame(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "evidence-limitations.html")
    chart = page.locator('[data-a-chart="evidence"]')
    assert chart.locator('[data-visual-node="source"]').count() == 4
    assert "主要论文与监管公开材料" in chart.inner_text()


def test_a_product_dossier_charts_only_show_the_current_product(
    page: Page, a_site: Path
) -> None:
    _open(page, a_site, "products/fixture-product.html")
    efficacy_chart = page.locator('[data-chart-id="product-efficacy"]')
    assert efficacy_chart.locator(".kz-a-bar-row").count() == 1
    assert "安澜双抗" not in efficacy_chart.inner_text()
    safety_chart = page.locator('[data-chart-id="product-safety"]')
    assert safety_chart.locator(".kz-a-heat-label").nth(1).inner_text() == "泰瑞奇单抗"
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
    cells = page.locator('[data-a-chart="safety"] .kz-a-heatmap > div')
    teae_backgrounds = [
        cells.nth(index).evaluate("node => node.style.background")
        for index in range(6, 10)
    ]
    assert len(set(teae_backgrounds)) == 4
    assert "颜色深浅仅在同一事件内比较" in page.locator('[data-a-chart="safety"]').inner_text()


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
    last_cell = chart.locator(".kz-a-heatmap > div").last
    chart_box = chart.bounding_box()
    cell_box = last_cell.bounding_box()
    assert chart_box is not None and cell_box is not None
    assert cell_box["x"] + cell_box["width"] <= chart_box["x"] + chart_box["width"]
    assert "诺维单抗" in chart.inner_text()


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
