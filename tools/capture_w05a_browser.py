"""Capture reproducible W05A responsive and journey evidence from a rendered A portal."""
# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from playwright.sync_api import ConsoleMessage, Page, sync_playwright

VIEWPORTS = ((1920, 1080), (1440, 900), (1024, 1366), (390, 844), (320, 568), (305, 568))


def _console_recorder(errors: list[str]) -> Callable[[ConsoleMessage], None]:
    def record(message: ConsoleMessage) -> None:
        if message.type == "error":
            errors.append(message.text)

    return record


def _metrics(page: Page) -> dict[str, object]:
    return cast(
        dict[str, object],
        page.evaluate(
            """() => {
          const box = selector => document.querySelector(selector)?.getBoundingClientRect().toJSON();
          const px = value => Number.parseFloat(value) || 0;
          const main = document.querySelector('.portal-main');
          const panel = document.querySelector('.kz-a-panel');
          const chart = document.querySelector('[data-chart-id="landscape-full"]');
          const core = document.querySelector('.kz-a-landscape-core');
          const compact = document.querySelector('.kz-a-landscape-grid');
          const controls = [...document.querySelectorAll(
            '.kz-a-panel button,.kz-a-panel summary,.kz-a-workspace-bar button,.kz-a-workspace-bar summary')]
            .filter(node => node.getBoundingClientRect().width > 0);
          const bodyFonts = [...document.querySelectorAll('.portal-lead,.kz-a-section-head p')]
            .map(node => Number.parseFloat(getComputedStyle(node).fontSize));
          const stageFonts = [...core.querySelectorAll('[data-landscape-stage-summary] strong,[data-landscape-stage-summary] span')]
            .map(node => Number.parseFloat(getComputedStyle(node).fontSize));
          return {
            viewport: {width: innerWidth, height: innerHeight},
            main: box('.portal-main'),
            main_width_ratio: main.getBoundingClientRect().width / innerWidth,
            panel: box('.kz-a-panel'),
            panel_padding: px(getComputedStyle(panel).paddingLeft),
            card_gap: px(getComputedStyle(document.documentElement).getPropertyValue('--portal-card-gap')),
            page_head: box('.portal-page-head'),
            page_head_margin_bottom: px(getComputedStyle(document.querySelector('.portal-page-head')).marginBottom),
            workspace: box('.kz-a-workspace-bar'),
            core_filters: [...document.querySelectorAll('[data-responsive-filter]')].map(node => node.getBoundingClientRect().toJSON()),
            landscape_mode: chart.dataset.landscapeMode,
            first_reading_unit: core.getBoundingClientRect().toJSON(),
            core_unit: {
              box: core.getBoundingClientRect().toJSON(),
              visible: core.getBoundingClientRect().width > 0 && core.getBoundingClientRect().height > 0,
              fully_visible: core.getBoundingClientRect().top >= 0 && core.getBoundingClientRect().bottom <= innerHeight,
              visible_height: Math.max(0, Math.min(innerHeight, core.getBoundingClientRect().bottom) - Math.max(0, core.getBoundingClientRect().top)),
              project_count: [...core.querySelectorAll('[data-landscape-stage-summary]')]
                .reduce((sum, node) => sum + Number(node.dataset.count), 0),
              stage_count: core.querySelectorAll('[data-landscape-stage-summary]').length
            },
            compact_unit: {
              box: compact.getBoundingClientRect().toJSON(),
              visible: compact.getBoundingClientRect().width > 0 && compact.getBoundingClientRect().height > 0,
              visible_height: Math.max(0, Math.min(innerHeight, compact.getBoundingClientRect().bottom) - Math.max(0, compact.getBoundingClientRect().top))
            },
            chart: chart.getBoundingClientRect().toJSON(),
            chart_height: chart.getBoundingClientRect().height,
            document_width: document.documentElement.scrollWidth,
            horizontal_overflow: document.documentElement.scrollWidth - innerWidth,
            minimum_visible_control_height: Math.min(...controls.map(node => node.getBoundingClientRect().height)),
            minimum_body_font_size: Math.min(...bodyFonts),
            minimum_stage_font_size: Math.min(...stageFonts),
            first_screen: {
              title: box('h1'),
              core_filter_count: document.querySelectorAll('[data-filter-dimension]').length,
              complete_reading_unit_visible: core.getBoundingClientRect().bottom <= innerHeight
            }
          };
        }"""
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    viewport_receipts: list[dict[str, object]] = []
    receipt: dict[str, Any] = {
        "source_site": str(args.site.resolve()),
        "viewports": viewport_receipts,
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width, height in VIEWPORTS:
            page = browser.new_page(viewport={"width": width, "height": height})
            console_errors: list[str] = []
            page.on("console", _console_recorder(console_errors))
            page.goto(
                (args.site / "landscape.html").resolve().as_uri(),
                wait_until="domcontentloaded",
            )
            page.wait_for_timeout(250)
            item = _metrics(page)
            item["console_errors"] = console_errors
            item["screenshot"] = f"landscape-{width}x{height}.png"
            page.screenshot(path=args.output / item["screenshot"], full_page=False)
            viewport_receipts.append(item)
            page.close()

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((args.site / "landscape.html").resolve().as_uri(), wait_until="domcontentloaded")
        product = page.locator('[data-chart-id="landscape-full"] [data-product-id]').first
        product_id = product.get_attribute("data-product-id")
        product.click()
        drawer = page.locator("#a-product-insight-drawer")
        drawer.get_by_role("tab", name="产品档案").click()
        dossier = drawer.get_by_role("link", name="查看完整产品档案")
        dossier.click()
        page.wait_for_timeout(150)
        anchors = {
            anchor: page.locator(f"#{anchor}").count() == 1
            for anchor in ("mechanism", "regions", "trials", "results", "evidence")
        }
        page.locator("#evidence").click()
        evidence_visible = page.locator("#data-basis-panel").is_visible()
        page.locator("[data-close-evidence]").click()
        page.get_by_role("link", name="返回上一步").click()
        page.wait_for_timeout(150)
        return_drawer_visible = page.locator("#a-product-insight-drawer").is_visible()
        chart_ids = page.locator('[data-chart-id="landscape-full"] [data-product-id]').evaluate_all(
            "nodes => nodes.map(node => node.dataset.productId)"
        )
        table_ids = page.locator("tbody tr[data-product-id]:not([hidden])").evaluate_all(
            "nodes => nodes.map(node => node.dataset.productId)"
        )
        receipt["journey"] = {
            "product_id": product_id,
            "steps": ["宇宙", "机制", "产品", "地域", "试验", "结果", "证据", "返回"],
            "anchors": anchors,
            "evidence_drawer_visible": evidence_visible,
            "return_drawer_visible": return_drawer_visible,
            "chart_table_same_query": sorted(chart_ids) == sorted(table_ids),
            "chart_product_count": len(chart_ids),
            "table_product_count": len(table_ids),
            "final_url": page.url,
        }
        page.screenshot(path=args.output / "journey-return-1440x900.png", full_page=False)
        browser.close()
    (args.output / "browser-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
