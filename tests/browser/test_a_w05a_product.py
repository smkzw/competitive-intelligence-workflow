"""W05A product, responsive-space, and end-to-end navigation contracts."""
# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from tests.integration.test_fresh_a_research_package import _package_payload


def _stage_payload() -> dict[str, object]:
    payload = _package_payload()["report_data"]
    phases = ("I期", "I/II期", "II期", "III期")
    for product, phase in zip(payload["products"], phases, strict=True):
        product["phase"] = phase
        product["status"] = "开展中"
    seed = payload["products"][0]
    payload["products"].extend(
        [
            {
                **seed,
                "id": "phase-iv-product",
                "name": "IV期产品",
                "phase": "IV期",
                "result_status": "暂无公开关键结果",
            },
            {
                **seed,
                "id": "preclinical-product",
                "name": "临床前产品",
                "phase": "临床前",
                "result_status": "临床前",
            },
            {
                **seed,
                "id": "unknown-phase-product",
                "name": "阶段未知产品",
                "phase": "未标注",
                "result_status": "暂无公开关键结果",
            },
        ]
    )
    return payload


def _high_load_payload() -> dict[str, object]:
    """Equivalent 45-product load with long labels and six clinical stage sets."""
    payload = _package_payload()["report_data"]
    products = payload["products"]
    assert isinstance(products, list)
    phases = ("I期", "I/II期", "II期", "III期", "IV期", "未标注")
    for index, product in enumerate(products):
        product["phase"] = phases[index % len(phases)]
        product["status"] = "开展中"
    seed = products[0]
    targets = ("C5", "C3", "补体旁路", "IL-4Rα", "TSLP", "JAK1")
    while len(products) < 45:
        index = len(products) + 1
        products.append(
            {
                **seed,
                "id": f"high-load-product-{index:02d}",
                "name": f"长名称创新治疗候选项目{index:02d}",
                "target": targets[index % len(targets)],
                "phase": phases[index % len(phases)],
                "status": "开展中",
                "result_status": "暂无公开关键结果",
            }
        )
    assert len(products) == 45
    return payload


@pytest.fixture(scope="module")
def w05a_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("w05a-a-site")
    render_report_a_site(ReportAPortalData.model_validate(_stage_payload()), site)
    return site


@pytest.fixture(scope="module")
def w05a_high_load_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("w05a-a-high-load-site")
    render_report_a_site(ReportAPortalData.model_validate(_high_load_payload()), site)
    return site


def _open(page: Page, site: Path, relative: str) -> None:
    page.goto((site / relative).as_uri(), wait_until="domcontentloaded")
    page.wait_for_timeout(150)


def test_landscape_chart_and_table_conserve_every_stage_and_product(
    w05a_site: Path,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(page, w05a_site, "landscape.html")
        expected = {product["id"] for product in _stage_payload()["products"]}
        plotted = set(
            page.locator('[data-chart-id="landscape-full"] [data-product-id]').evaluate_all(
                "nodes => nodes.map(node => node.dataset.productId)"
            )
        )
        table = set(
            page.locator("tbody tr[data-product-id]").evaluate_all(
                "nodes => nodes.map(node => node.dataset.productId)"
            )
        )
        assert plotted == table == expected
        assert set(
            page.locator("[data-landscape-stage]").evaluate_all(
                "nodes => nodes.map(node => node.dataset.landscapeStage)"
            )
        ) >= {"I期", "I/II期", "II期", "III期", "IV期", "临床前", "未知"}
        assert "Top-N" not in page.locator("body").inner_text()
        browser.close()


def test_user_edit_with_missing_source_fields_never_renders_literal_none(
    tmp_path: Path,
) -> None:
    payload = _package_payload()["report_data"]
    row = payload["safety"][0]
    row["source_text"] = None
    row["source_field_path"] = None
    payload["user_edits"] = {
        row["row_id"]: {
            "fact_id": "fact-source-empty",
            "fact_version_id": "fact-source-empty-v2",
            "request_id": "request-source-empty",
            "revision": 2,
            "primary_fragment_id": "fragment-source-empty",
            "source_version_id": "source-version-empty",
            "source_locator": {"field_path": "registry.results.safety[0]"},
            "current_value": "30%",
            "original_value": "原文未列示数值",
            "basis": "用户核对后修订",
            "saved_by": "测试用户",
            "saved_at": "2026-09-23T08:00:00+08:00",
            "operation": "save",
        }
    }
    render_report_a_site(ReportAPortalData.model_validate(payload), tmp_path)
    html = (tmp_path / "safety.html").read_text(encoding="utf-8")
    assert "原来源原文：None" not in html
    assert "原定位：None" not in html
    assert "原文未提供" in html
    assert "定位见证据链" in html


@pytest.mark.parametrize(
    ("width", "height", "minimum_main_ratio", "maximum_padding"),
    (
        (1920, 1080, 0.88, 24),
        (1440, 900, 0.94, 24),
        (1024, 1366, 0.98, 20),
        (390, 844, 0.98, 14),
        (320, 568, 0.98, 12),
    ),
)
def test_a_responsive_space_uses_canvas_and_keeps_a_complete_first_reading_unit(
    w05a_site: Path,
    width: int,
    height: int,
    minimum_main_ratio: float,
    maximum_padding: float,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        _open(page, w05a_site, "landscape.html")
        metrics = page.evaluate(
            """() => {
              const main = document.querySelector('.portal-main').getBoundingClientRect();
              const panel = document.querySelector('.kz-a-panel');
              const head = document.querySelector('.portal-page-head');
              const firstBand = document.querySelector('.kz-a-landscape-band');
              const chart = document.querySelector('[data-chart-id="landscape-full"]');
              const px = value => Number.parseFloat(value) || 0;
              const controls = [...document.querySelectorAll(
                '.kz-a-panel button, .kz-a-panel summary, .kz-a-workspace-bar button')]
                .filter(node => node.getBoundingClientRect().width > 0);
              return {
                ratio: main.width / innerWidth,
                padding: px(getComputedStyle(panel).paddingLeft),
                headMargin: px(getComputedStyle(head).marginBottom),
                chartHeight: chart.getBoundingClientRect().height,
                firstBandBottom: firstBand.getBoundingClientRect().bottom,
                overflow: document.documentElement.scrollWidth - innerWidth,
                minControlHeight: Math.min(...controls.map(node => node.getBoundingClientRect().height)),
                hasTitle: Boolean(document.querySelector('h1')),
                hasCoreFilters: document.querySelectorAll('[data-filter-dimension]').length >= 2
              };
            }"""
        )
        assert metrics["ratio"] >= minimum_main_ratio
        assert metrics["padding"] <= maximum_padding
        assert metrics["overflow"] <= 1
        assert metrics["minControlHeight"] >= 40
        assert metrics["hasTitle"] and metrics["hasCoreFilters"]
        if width <= 1024:
            assert metrics["headMargin"] <= 18
        if width <= 390:
            assert metrics["chartHeight"] <= 520, metrics
            assert metrics["firstBandBottom"] <= height, metrics
        browser.close()


@pytest.mark.parametrize(
    ("width", "height", "expected_mode"),
    (
        (1920, 1080, "matrix"),
        (1440, 900, "matrix"),
        (1024, 1366, "compact"),
        (390, 844, "compact"),
        (320, 568, "compact"),
        (305, 568, "compact"),
    ),
)
def test_high_load_landscape_exposes_complete_core_unit_without_clipping(
    w05a_high_load_site: Path,
    width: int,
    height: int,
    expected_mode: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        _open(page, w05a_high_load_site, "landscape.html")
        metrics = page.evaluate(
            """() => {
              const host = document.querySelector('[data-chart-id="landscape-full"]');
              const core = host.querySelector('.kz-a-landscape-core');
              const coreBox = core.getBoundingClientRect();
              const items = [...core.querySelectorAll('[data-landscape-stage-summary]')];
              const controls = [...document.querySelectorAll(
                '.kz-a-panel button, .kz-a-panel summary, .kz-a-workspace-bar summary')]
                .filter(node => node.getBoundingClientRect().width > 0);
              const bodyFont = Number.parseFloat(getComputedStyle(document.body).fontSize);
              const leadFonts = [...document.querySelectorAll('.portal-lead, .kz-a-section-head p')]
                .map(node => Number.parseFloat(getComputedStyle(node).fontSize));
              const stageFonts = items.flatMap(node => [...node.querySelectorAll('strong, span')]
                .map(label => Number.parseFloat(getComputedStyle(label).fontSize)));
              return {
                mode: host.dataset.landscapeMode,
                core: {top: coreBox.top, bottom: coreBox.bottom, width: coreBox.width,
                       height: coreBox.height, visible: coreBox.width > 0 && coreBox.height > 0},
                coreCount: items.reduce((sum, node) => sum + Number(node.dataset.count), 0),
                labelsFit: items.every(node => node.scrollWidth <= node.clientWidth + 1 &&
                  node.scrollHeight <= node.clientHeight + 1),
                productCount: new Set([...host.querySelectorAll('[data-product-id]')]
                  .map(node => node.dataset.productId)).size,
                stageSet: [...new Set([...host.querySelectorAll('[data-landscape-stage]')]
                  .map(node => node.dataset.landscapeStage))].sort(),
                overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth,
                minTouch: Math.min(...controls.map(node => node.getBoundingClientRect().height)),
                bodyFont,
                minLeadFont: Math.min(...leadFonts),
                minStageFont: Math.min(...stageFonts),
                chartHeight: host.getBoundingClientRect().height
              };
            }"""
        )
        expected_stages = {"I期", "I/II期", "II期", "III期", "IV期", "未知"}
        assert metrics["mode"] == expected_mode
        assert metrics["core"]["visible"]
        assert metrics["core"]["bottom"] <= height, metrics
        assert metrics["coreCount"] == 45
        assert metrics["productCount"] == 45
        assert set(metrics["stageSet"]) == expected_stages
        assert metrics["labelsFit"]
        assert metrics["overflow"] <= 1
        assert metrics["minTouch"] >= 40
        assert metrics["bodyFont"] >= 16
        assert metrics["minLeadFont"] >= 16
        assert metrics["minStageFont"] >= 14
        assert metrics["chartHeight"] > metrics["core"]["height"]
        browser.close()


@pytest.mark.parametrize("width,height", ((390, 844), (320, 568), (305, 568)))
def test_high_load_landscape_mobile_detail_and_complete_table_do_not_scroll_sideways(
    w05a_high_load_site: Path,
    width: int,
    height: int,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        _open(page, w05a_high_load_site, "landscape.html")

        first_target = page.locator("details.kz-a-landscape-target-band").first
        first_target.locator("summary").click()
        stage_groups = first_target.locator(".kz-a-landscape-cell")
        assert stage_groups.count() >= 1
        detail_layout = first_target.evaluate(
            """node => ({
              width: node.clientWidth,
              scrollWidth: node.scrollWidth,
              stages: [...node.querySelectorAll('.kz-a-landscape-cell')]
                .filter(item => item.getBoundingClientRect().height > 0)
                .map(item => ({width: item.getBoundingClientRect().width,
                  scrollWidth: item.scrollWidth, clientWidth: item.clientWidth})),
              productButtons: [...node.querySelectorAll('.kz-a-landscape-product')]
                .filter(item => item.getBoundingClientRect().height > 0)
                .map(item => ({height: item.getBoundingClientRect().height,
                  fits: item.scrollWidth <= item.clientWidth + 1 &&
                    item.scrollHeight <= item.clientHeight + 1}))
            })"""
        )
        assert detail_layout["scrollWidth"] <= detail_layout["width"] + 1
        assert all(item["width"] >= detail_layout["width"] - 16 for item in detail_layout["stages"])
        assert all(item["height"] >= 40 and item["fits"] for item in detail_layout["productButtons"])

        complete = page.locator("details.kz-complete-table")
        complete.locator("summary").click()
        cards = complete.locator(".kz-a-landscape-records")
        assert cards.is_visible()
        card_metrics = cards.evaluate(
            """node => ({
              clientWidth: node.clientWidth,
              scrollWidth: node.scrollWidth,
              records: node.querySelectorAll('[data-landscape-record]').length,
              fieldCounts: [...node.querySelectorAll('[data-landscape-record]')]
                .map(record => record.querySelectorAll('dt').length)
            })"""
        )
        assert card_metrics["records"] == 45
        assert card_metrics["scrollWidth"] <= card_metrics["clientWidth"] + 1
        assert set(card_metrics["fieldCounts"]) == {6}
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        browser.close()


def test_same_query_drives_chart_and_folded_table_and_saved_view_restores(
    w05a_site: Path,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1024, "height": 1366})
        page = context.new_page()
        _open(page, w05a_site, "landscape.html")
        complete_table = page.locator("details.kz-complete-table")
        assert complete_table.count() == 1
        assert complete_table.get_attribute("open") is None
        phase_group = page.locator('[data-filter-dimension="phase"]')
        if phase_group.evaluate("node => node.tagName === 'DETAILS' && !node.open"):
            phase_group.locator("summary").click()
        phase = phase_group.locator("button").filter(has_text="IV期")
        phase.click()
        chart_ids = set(
            page.locator('[data-chart-id="landscape-full"] [data-product-id]').evaluate_all(
                "nodes => nodes.map(node => node.dataset.productId)"
            )
        )
        complete_table.locator("summary").click()
        table_ids = set(
            page.locator("tbody tr[data-product-id]:not([hidden])").evaluate_all(
                "nodes => nodes.map(node => node.dataset.productId)"
            )
        )
        assert chart_ids == table_ids == {"phase-iv-product"}
        page.get_by_role("button", name="保存当前视图").click()
        page.goto((w05a_site / "landscape.html").as_uri())
        page.wait_for_timeout(150)
        restored_phase = page.locator(
            '[data-filter-dimension="phase"] button[aria-pressed="true"]'
        ).text_content()
        diagnostic = page.evaluate(
            """() => ({
              status: document.querySelector('[data-a-view-status]').textContent,
              storage: {...localStorage},
              pressed: [...document.querySelectorAll('[aria-pressed="true"]')]
                .map(node => node.textContent)
            })"""
        )
        assert restored_phase == "IV期", diagnostic
        assert "已恢复本机保存的视图" in page.locator("[data-a-view-status]").inner_text()
        context.close()
        browser.close()


def test_universe_to_product_evidence_and_return_journey(w05a_site: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(page, w05a_site, "landscape.html")
        product = page.locator('[data-chart-id="landscape-full"] [data-product-id]').first
        product_id = product.get_attribute("data-product-id")
        product.click()
        drawer = page.locator("#a-product-insight-drawer")
        assert drawer.is_visible()
        drawer.get_by_role("tab", name="产品档案").click()
        profile = drawer.locator('[data-product-panel="profile"]')
        assert "作用机制" in profile.inner_text()
        profile.get_by_role("link", name="查看完整产品档案").click()
        page.wait_for_timeout(100)
        assert f"/products/{product_id}.html" in page.url
        for anchor in ("mechanism", "regions", "trials", "results", "evidence"):
            assert page.locator(f"#{anchor}").count() == 1
        page.locator("#evidence").click()
        assert page.locator("#data-basis-panel").is_visible()
        page.locator("[data-close-evidence]").click()
        page.get_by_role("link", name="返回上一步").click()
        page.wait_for_timeout(100)
        assert page.url.endswith("landscape.html") or "landscape.html?" in page.url
        assert drawer.is_visible()
        browser.close()
