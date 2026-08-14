#!/usr/bin/env python3
"""Read-only visual pass for Task 4.5 review site. Writes only to this evidence dir."""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
TRACE: list[dict] = []


def log(step: str, **extra) -> None:
    rec = {"t": time.strftime("%H:%M:%S"), "step": step, **extra}
    TRACE.append(rec)
    print(json.dumps(rec, ensure_ascii=False))


def shot(page, name: str, full: bool = False) -> str:
    dest = ROOT / name
    page.screenshot(path=str(dest), full_page=full, animations="disabled")
    log("screenshot", path=str(dest.name), url=page.url, vw=page.viewport_size)
    return dest.name


def collect_runtime(page) -> dict:
    return page.evaluate(
        """() => {
          const drawer = document.getElementById('kz-evidence-drawer');
          const pinBtn = document.getElementById('kz-evidence-pin-btn');
          const pinned = document.getElementById('kz-evidence-pinned');
          const compare = document.getElementById('kz-evidence-compare');
          const status = document.getElementById('kz-evidence-drawer-status');
          const focus = document.activeElement;
          const charts = Array.from(document.querySelectorAll('.kz-chart-module__group')).map((g, i) => {
            const title = g.querySelector('.kz-chart-group__title, h3')?.textContent?.trim() || '';
            const svg = g.querySelector('svg');
            const canvas = g.querySelector('canvas');
            const undisclosed = g.querySelector('.kz-chart-undisclosed');
            const valueCells = Array.from(g.querySelectorAll('[data-evidence-field="value"]')).map(el => ({
              text: (el.textContent || '').trim(),
              row: el.getAttribute('data-evidence-open'),
              empty: !(el.textContent || '').trim(),
              cls: el.className
            }));
            return {
              i, title,
              hasSvg: !!svg, hasCanvas: !!canvas,
              undisclosed: undisclosed ? undisclosed.textContent.trim().slice(0, 200) : null,
              valueCells
            };
          });
          const search = document.querySelector('input[type="search"], [role="searchbox"], .site-search input');
          const searchBox = search ? {
            placeholder: search.getAttribute('placeholder'),
            w: Math.round(search.getBoundingClientRect().width),
            overflow: getComputedStyle(search).textOverflow
          } : null;
          const headerSearch = document.querySelector('.site-header input, header input');
          const headerSearchRect = headerSearch ? headerSearch.getBoundingClientRect() : null;
          return {
            url: location.href,
            title: document.title,
            vw: window.innerWidth,
            vh: window.innerHeight,
            drawerHidden: drawer ? drawer.hasAttribute('hidden') || drawer.hidden : null,
            drawerTitle: document.querySelector('#kz-evidence-drawer h3, .kz-evidence-current h3')?.textContent || '',
            status: status ? status.textContent : '',
            pinText: pinBtn ? pinBtn.textContent : '',
            pinnedHidden: pinned ? pinned.hidden : null,
            pinnedHint: document.getElementById('kz-evidence-pinned-hint')?.textContent || '',
            compareText: compare ? compare.innerText.slice(0, 2500) : '',
            focus: focus ? {
              tag: focus.tagName,
              id: focus.id,
              role: focus.getAttribute('role'),
              text: (focus.textContent || '').trim().slice(0, 80),
              aria: focus.getAttribute('aria-label')
            } : null,
            rowCount: document.getElementById('kz-filter-row-count')?.textContent || '',
            filterSummary: document.getElementById('kz-filter-summary')?.textContent || '',
            emptyVisible: document.getElementById('kz-filter-empty')?.style.display !== 'none',
            searchBox,
            headerSearchW: headerSearchRect ? Math.round(headerSearchRect.width) : null,
            charts,
            visibleFacts: Array.from(document.querySelectorAll('[data-filter-row-id]')).filter(el => el.offsetParent !== null).map(el => el.getAttribute('data-filter-row-id')),
            bodyOverflowX: document.documentElement.scrollWidth > window.innerWidth + 2
          };
        }"""
    )


def click_chart_mark(page, group_index: int = 0) -> dict:
    return page.evaluate(
        """(idx) => {
          const groups = document.querySelectorAll('.kz-chart-module__group');
          const g = groups[idx];
          if (!g) return {ok:false, reason:'no-group'};
          const chart = g.querySelector('.kz-chart-group__chart, [id*="chart"], canvas, svg');
          const rectHost = chart || g;
          const r = rectHost.getBoundingClientRect();
          const candidates = [];
          g.querySelectorAll('path, rect, [ecseries], .echarts-for-react').forEach(() => {});
          const series = Array.from(g.querySelectorAll('path[fill]:not([fill="none"]), rect[fill]:not([fill="none"])'))
            .filter(el => {
              const br = el.getBoundingClientRect();
              return br.width > 8 && br.height > 8 && br.y > r.y;
            })
            .slice(0, 8)
            .map(el => {
              const br = el.getBoundingClientRect();
              return {x: br.x + br.width/2, y: br.y + br.height/2, w: br.width, h: br.height, tag: el.tagName, fill: el.getAttribute('fill')};
            });
          return {ok:true, host:{x:r.x,y:r.y,w:r.width,h:r.height}, series};
        }""",
        group_index,
    )


def main() -> None:
    console_all: list[dict] = []
    requests_all: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="zh-CN", device_scale_factor=1)
        page = context.new_page()
        page.on("console", lambda msg: console_all.append({"type": msg.type, "text": msg.text, "url": page.url}))
        page.on(
            "request",
            lambda req: requests_all.append({"method": req.method, "url": req.url, "res": None}),
        )
        page.on(
            "response",
            lambda res: requests_all.append({"method": res.request.method, "url": res.url, "status": res.status}),
        )

        # ---- 1280x900 efficacy ----
        page.set_viewport_size({"width": 1280, "height": 900})
        log("goto", url="http://127.0.0.1:8765/efficacy.html", viewport="1280x900")
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(800)
        shot(page, "01_efficacy_1280x900_landing.png")
        page.evaluate("window.scrollTo(0, 520)")
        page.wait_for_timeout(300)
        shot(page, "02_efficacy_1280x900_charts.png")
        state = collect_runtime(page)
        (ROOT / "state_efficacy_landing.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        log("state_landing", charts=len(state.get("charts") or []), search=state.get("searchBox"))

        # Click first chart mark if possible
        marks = click_chart_mark(page, 0)
        log("chart0_marks", marks=marks)
        clicked_bar = False
        if marks.get("series"):
            s = marks["series"][0]
            page.mouse.click(s["x"], s["y"])
            page.wait_for_timeout(400)
            clicked_bar = True
            log("clicked_bar", x=s["x"], y=s["y"], fill=s.get("fill"))
        else:
            # fallback: click first numeric table cell
            page.locator('[data-evidence-field="value"]').first.click()
            page.wait_for_timeout(400)
            log("clicked_value_cell_fallback")
        shot(page, "03_efficacy_1280x900_bar_or_cell.png")
        after_bar = collect_runtime(page)
        (ROOT / "state_efficacy_after_bar.json").write_text(json.dumps(after_bar, ensure_ascii=False, indent=2), encoding="utf-8")

        # Pin first
        pin = page.locator("#kz-evidence-pin-btn")
        if pin.count() and pin.is_visible():
            pin.click()
            page.wait_for_timeout(250)
            log("pinned_first", url=page.url)
        shot(page, "04_efficacy_1280x900_pinned_one.png")

        # Heatmap / second group value cell
        heat_cells = page.locator('.kz-chart-module__group').nth(1).locator('[data-evidence-field="value"]')
        if heat_cells.count():
            heat_cells.first.click()
            page.wait_for_timeout(350)
            log("clicked_heatmap_value", count=heat_cells.count(), url=page.url)
        else:
            page.locator('[aria-label*="疾病活动度变化值"]').first.click()
            page.wait_for_timeout(350)
            log("clicked_heatmap_label_fallback", url=page.url)
        pin2 = page.locator("#kz-evidence-pin-btn")
        if pin2.count() and pin2.is_visible() and "固定此条" in (pin2.inner_text() or ""):
            pin2.click()
            page.wait_for_timeout(250)
            log("pinned_second", url=page.url)
        page.evaluate("document.getElementById('kz-evidence-pinned')?.scrollIntoView({block:'center'})")
        page.wait_for_timeout(200)
        shot(page, "05_efficacy_1280x900_two_pinned.png")
        compare_state = collect_runtime(page)
        (ROOT / "state_efficacy_two_pinned.json").write_text(json.dumps(compare_state, ensure_ascii=False, indent=2), encoding="utf-8")

        # Status matrix third group
        page.locator('.kz-chart-module__group').nth(2).locator('[data-evidence-field="value"]').first.click()
        page.wait_for_timeout(300)
        log("clicked_status_matrix", url=page.url)
        shot(page, "06_efficacy_1280x900_status_matrix.png")

        # Full table data unit from fixture table
        page.locator('[data-evidence-open="report-row_d94d011208fe8bf89b6bf983"][data-evidence-field="label"]').click()
        page.wait_for_timeout(300)
        log("clicked_safety_row", url=page.url)
        shot(page, "07_efficacy_1280x900_table_row_safety.png")

        # Filter narrow
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(250)
        shot(page, "08_efficacy_1280x900_filter_open.png")
        page.locator('.kz-filter-item[data-val="product-alpha"]').click()
        page.wait_for_timeout(300)
        log("filter_product_alpha", url=page.url)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        shot(page, "09_efficacy_1280x900_filter_alpha.png")
        filtered = collect_runtime(page)
        (ROOT / "state_efficacy_filter_alpha.json").write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")

        # URL copy/refresh
        filtered_url = page.url
        log("before_reload", url=filtered_url)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(600)
        log("after_reload", url=page.url)
        shot(page, "10_efficacy_1280x900_after_reload.png")
        after_reload = collect_runtime(page)
        (ROOT / "state_efficacy_after_reload.json").write_text(json.dumps(after_reload, ensure_ascii=False, indent=2), encoding="utf-8")

        # Navigate to baseline then back/forward
        page.locator('a[href="baseline.html"]').click()
        page.wait_for_timeout(700)
        log("nav_baseline", url=page.url)
        shot(page, "11_baseline_1280x900_landing.png")
        page.go_back()
        page.wait_for_timeout(500)
        log("back_to_efficacy", url=page.url)
        shot(page, "12_efficacy_1280x900_after_back.png")
        page.go_forward()
        page.wait_for_timeout(600)
        log("forward_to_baseline", url=page.url)
        shot(page, "13_baseline_1280x900_after_forward.png")

        # Baseline: table, pin two, undisclosed
        page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(300)
        if page.locator("#kz-evidence-pin-btn").is_visible():
            page.locator("#kz-evidence-pin-btn").click()
        labels = page.locator('[data-evidence-field="label"]')
        if labels.count() > 1:
            labels.nth(1).click()
            page.wait_for_timeout(250)
            if page.locator("#kz-evidence-pin-btn").is_visible() and "固定此条" in page.locator("#kz-evidence-pin-btn").inner_text():
                page.locator("#kz-evidence-pin-btn").click()
        page.wait_for_timeout(250)
        shot(page, "14_baseline_1280x900_two_pinned.png")
        base_state = collect_runtime(page)
        (ROOT / "state_baseline_two_pinned.json").write_text(json.dumps(base_state, ensure_ascii=False, indent=2), encoding="utf-8")

        # Click chart/heatmap on baseline if present
        bmarks = click_chart_mark(page, 0)
        log("baseline_chart_marks", marks=bmarks)
        if bmarks.get("series"):
            s = bmarks["series"][0]
            page.mouse.click(s["x"], s["y"])
            page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 700)")
        page.wait_for_timeout(200)
        shot(page, "15_baseline_1280x900_charts.png")

        # Disposition
        page.locator('a[href="disposition.html"]').click()
        page.wait_for_timeout(700)
        log("nav_disposition", url=page.url)
        shot(page, "16_disposition_1280x900_landing.png")
        page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(300)
        if page.locator("#kz-evidence-pin-btn").is_visible():
            page.locator("#kz-evidence-pin-btn").click()
        if page.locator('[data-evidence-field="label"]').count() > 1:
            page.locator('[data-evidence-field="label"]').nth(1).click()
            page.wait_for_timeout(250)
            if page.locator("#kz-evidence-pin-btn").is_visible() and "固定此条" in page.locator("#kz-evidence-pin-btn").inner_text():
                page.locator("#kz-evidence-pin-btn").click()
        page.wait_for_timeout(250)
        shot(page, "17_disposition_1280x900_two_pinned.png")
        disp_state = collect_runtime(page)
        (ROOT / "state_disposition_two_pinned.json").write_text(json.dumps(disp_state, ensure_ascii=False, indent=2), encoding="utf-8")
        dmarks = click_chart_mark(page, 0)
        log("disposition_chart_marks", marks=dmarks)
        if dmarks.get("series"):
            s = dmarks["series"][0]
            page.mouse.click(s["x"], s["y"])
            page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 720)")
        page.wait_for_timeout(200)
        shot(page, "18_disposition_1280x900_charts.png")

        # Esc and focus return
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        esc1 = collect_runtime(page)
        log("esc_disposition", drawerHidden=esc1.get("drawerHidden"), focus=esc1.get("focus"))
        shot(page, "19_disposition_1280x900_after_esc.png")

        # ---- 1024x768 pass on all three ----
        page.set_viewport_size({"width": 1024, "height": 768})
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "20_efficacy_1024x768_landing.png")
        page.locator('[data-evidence-field="value"]').first.click()
        page.wait_for_timeout(300)
        shot(page, "21_efficacy_1024x768_drawer.png")
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(200)
        page.locator('.kz-filter-item[data-val="product-beta"]').click()
        page.wait_for_timeout(250)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        shot(page, "22_efficacy_1024x768_filter_beta.png")
        e1024 = collect_runtime(page)
        (ROOT / "state_efficacy_1024.json").write_text(json.dumps(e1024, ensure_ascii=False, indent=2), encoding="utf-8")

        page.goto("http://127.0.0.1:8765/baseline.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "23_baseline_1024x768_landing.png")
        page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(250)
        shot(page, "24_baseline_1024x768_drawer.png")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        b1024 = collect_runtime(page)
        (ROOT / "state_baseline_1024.json").write_text(json.dumps(b1024, ensure_ascii=False, indent=2), encoding="utf-8")

        page.goto("http://127.0.0.1:8765/disposition.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "25_disposition_1024x768_landing.png")
        page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(250)
        shot(page, "26_disposition_1024x768_drawer.png")
        # click heatmap/status if present
        if page.locator('.kz-chart-module__group').count() > 1:
            page.locator('.kz-chart-module__group').nth(1).locator('[data-evidence-field="value"]').first.click()
            page.wait_for_timeout(250)
        page.evaluate("window.scrollTo(0, 640)")
        page.wait_for_timeout(200)
        shot(page, "27_disposition_1024x768_charts.png")
        d1024 = collect_runtime(page)
        (ROOT / "state_disposition_1024.json").write_text(json.dumps(d1024, ensure_ascii=False, indent=2), encoding="utf-8")

        # Focus return: tab to a cell, open, Esc
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        cell = page.locator('[data-evidence-field="label"]').first
        cell.focus()
        before = collect_runtime(page)
        cell.press("Enter")
        page.wait_for_timeout(250)
        opened = collect_runtime(page)
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        after_esc = collect_runtime(page)
        (ROOT / "state_focus_esc.json").write_text(
            json.dumps({"before": before, "opened": opened, "after_esc": after_esc}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        shot(page, "28_efficacy_1024x768_after_esc_focus.png")
        log("focus_esc", before=before.get("focus"), opened_hidden=opened.get("drawerHidden"), after=after_esc.get("focus"), after_hidden=after_esc.get("drawerHidden"))

        browser.close()

    remote = [r for r in requests_all if r.get("url") and not r["url"].startswith("http://127.0.0.1:8765")]
    errors = [c for c in console_all if c.get("type") in {"error", "warning"}]
    summary = {
        "steps": TRACE,
        "console": console_all,
        "console_errors_warnings": errors,
        "request_count": len(requests_all),
        "remote_requests": remote,
        "local_hosts": sorted({r.get("url", "").split("/")[2] for r in requests_all if "://" in r.get("url", "")}),
    }
    (ROOT / "trace.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "TRAIL.md").write_text(
        "\n".join(f"- {s['t']} {s['step']} {json.dumps({k:v for k,v in s.items() if k not in {'t','step'}}, ensure_ascii=False)}" for s in TRACE),
        encoding="utf-8",
    )
    print("DONE", ROOT)


if __name__ == "__main__":
    main()
