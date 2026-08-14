#!/usr/bin/env python3
"""Continue remaining visual checks after drawer intercepted header nav."""
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
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def shot(page, name: str) -> None:
    dest = ROOT / name
    page.screenshot(path=str(dest), full_page=False, animations="disabled")
    log("screenshot", path=dest.name, url=page.url, vw=page.viewport_size)


def collect(page) -> dict:
    return page.evaluate(
        """() => {
          const drawer = document.getElementById('kz-evidence-drawer');
          const focus = document.activeElement;
          const texts = Array.from(document.querySelectorAll('body *')).slice(0, 0);
          const scan = document.body.innerText;
          const hits = {};
          ['未公开','尚未公开','不适用','技术暂不可用','来源未列示','未提供','原文未提供'].forEach(k => { hits[k] = scan.includes(k); });
          const charts = Array.from(document.querySelectorAll('.kz-chart-module__group, .kz-chart-undisclosed')).map((g,i)=>({
            i, cls:g.className,
            title:g.querySelector('h3,.kz-chart-group__title,.kz-chart-undisclosed__title')?.textContent?.trim()||'',
            undisclosed: (g.querySelector('.kz-chart-undisclosed')||g.classList.contains('kz-chart-undisclosed')) ? (g.innerText||'').slice(0,240) : null,
            emptyValues: Array.from(g.querySelectorAll('[data-evidence-field="value"]')).map(el=>({text:(el.textContent||'').trim(), empty:!(el.textContent||'').trim()}))
          }));
          const header = document.querySelector('header.site-header, .site-header');
          const nav = document.querySelector('.site-header__nav, nav[aria-label="主导航"]');
          const drawerBox = drawer ? drawer.getBoundingClientRect() : null;
          const navItems = Array.from(document.querySelectorAll('a.site-header__nav-item')).map(a=>{
            const r=a.getBoundingClientRect();
            const cx=r.x+r.width/2, cy=r.y+r.height/2;
            const top = document.elementFromPoint(cx, cy);
            return {text:a.textContent.trim(), x:Math.round(r.x), w:Math.round(r.width), coveredBy: top ? (top.id||top.className||top.tagName).toString().slice(0,80) : null};
          });
          return {
            url: location.href, vw: innerWidth, vh: innerHeight,
            title: document.title,
            drawerHidden: drawer ? drawer.hidden : null,
            drawerW: drawerBox ? Math.round(drawerBox.width) : null,
            drawerX: drawerBox ? Math.round(drawerBox.x) : null,
            pinText: document.getElementById('kz-evidence-pin-btn')?.textContent || '',
            compareText: document.getElementById('kz-evidence-compare')?.innerText?.slice(0,2000) || '',
            heading: document.querySelector('#kz-evidence-drawer h3')?.textContent || '',
            status: document.getElementById('kz-evidence-drawer-status')?.textContent || '',
            focus: focus ? {tag:focus.tagName,id:focus.id,text:(focus.textContent||'').trim().slice(0,80),aria:focus.getAttribute('aria-label')} : null,
            rowCount: document.getElementById('kz-filter-row-count')?.textContent || '',
            filterSummary: document.getElementById('kz-filter-summary')?.textContent || '',
            emptyVisible: document.getElementById('kz-filter-empty')?.style.display !== 'none',
            emptyText: document.getElementById('kz-filter-empty')?.innerText || '',
            hits, charts, navItems,
            overflowX: document.documentElement.scrollWidth > innerWidth + 2,
            scrollW: document.documentElement.scrollWidth,
            visibleRowLabels: Array.from(document.querySelectorAll('[data-filter-row-id]:not([hidden]) .kz-fixture-cell--label, [data-filter-row-id]')).filter(el=>el.offsetParent).slice(0,20).map(el=>(el.textContent||'').trim().slice(0,60))
          };
        }"""
    )


def close_drawer(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    page.evaluate(
        """() => {
          const d=document.getElementById('kz-evidence-drawer');
          if(d && !d.hidden){
            const btn=document.getElementById('kz-evidence-drawer-close');
            if(btn) btn.click();
          }
        }"""
    )
    page.wait_for_timeout(200)


def click_svg_mark(page, idx: int = 0) -> dict:
    info = page.evaluate(
        """(i) => {
          const groups=document.querySelectorAll('.kz-chart-module__group');
          const g=groups[i];
          if(!g) return {ok:false,reason:'no-group',n:groups.length};
          const rects=Array.from(g.querySelectorAll('path[fill]:not([fill="none"]), rect[fill]:not([fill="none"])'))
            .map(el=>{const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height,fill:el.getAttribute('fill')};})
            .filter(r=>r.w>6 && r.h>6);
          return {ok:true, n:rects.length, series:rects.slice(0,6)};
        }""",
        idx,
    )
    if info.get("series"):
        s = info["series"][0]
        page.mouse.click(s["x"], s["y"])
        page.wait_for_timeout(300)
        info["clicked"] = s
    return info


def main() -> None:
    console_all: list[dict] = []
    remote: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="zh-CN", device_scale_factor=1)
        page.on("console", lambda m: console_all.append({"type": m.type, "text": m.text}))
        page.on(
            "response",
            lambda r: remote.append({"url": r.url, "status": r.status})
            if not r.url.startswith("http://127.0.0.1:8765")
            else None,
        )

        # Disposition 1280
        page.goto("http://127.0.0.1:8765/disposition.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "16_disposition_1280x900_landing.png")
        (ROOT / "state_disposition_landing.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")
        marks = click_svg_mark(page, 0)
        log("disp_chart", marks=marks)
        if not marks.get("clicked"):
            page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(250)
        if page.locator("#kz-evidence-pin-btn").is_visible():
            page.locator("#kz-evidence-pin-btn").click()
        labels = page.locator('[data-evidence-field="label"]')
        if labels.count() > 1:
            labels.nth(1).click()
            page.wait_for_timeout(250)
            btn = page.locator("#kz-evidence-pin-btn")
            if btn.is_visible() and "固定此条" in btn.inner_text():
                btn.click()
        page.wait_for_timeout(250)
        page.evaluate("document.getElementById('kz-evidence-pinned')?.scrollIntoView({block:'center'})")
        shot(page, "17_disposition_1280x900_two_pinned.png")
        (ROOT / "state_disposition_two_pinned.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")
        page.evaluate("window.scrollTo(0, 680)")
        page.wait_for_timeout(200)
        shot(page, "18_disposition_1280x900_charts.png")
        if page.locator('.kz-chart-module__group').count() > 1:
            click_svg_mark(page, 1)
            shot(page, "18b_disposition_1280x900_heatmap_click.png")
        close_drawer(page)
        after_esc = collect(page)
        log("disp_esc", hidden=after_esc.get("drawerHidden"), focus=after_esc.get("focus"))
        shot(page, "19_disposition_1280x900_after_esc.png")
        (ROOT / "state_disposition_after_esc.json").write_text(json.dumps(after_esc, ensure_ascii=False, indent=2), encoding="utf-8")

        # Baseline undisclosed + charts more carefully
        page.goto("http://127.0.0.1:8765/baseline.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        page.evaluate("window.scrollTo(0, 500)")
        page.wait_for_timeout(200)
        shot(page, "15b_baseline_1280x900_chart_area.png")
        bmarks = click_svg_mark(page, 0)
        log("base_chart", marks=bmarks)
        if page.locator('.kz-chart-module__group').count() > 1:
            click_svg_mark(page, 1)
        page.wait_for_timeout(200)
        shot(page, "15c_baseline_1280x900_after_chart_click.png")
        (ROOT / "state_baseline_charts.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")

        # Look for undisclosed by opening several rows
        ids = page.eval_on_selector_all("[data-evidence-open]", "els => [...new Set(els.map(e=>e.getAttribute('data-evidence-open')))]")
        found_states = []
        for rid in ids[:8]:
            page.locator(f'[data-evidence-open="{rid}"][data-evidence-field="label"]').first.click()
            page.wait_for_timeout(180)
            text = page.locator("#kz-evidence-drawer").inner_text()
            found_states.append({"id": rid, "has_undisclosed": any(k in text for k in ["尚未公开", "未公开", "技术暂不可用", "来源未列示", "不适用", "原文未提供"])})
        (ROOT / "state_baseline_disclosure_scan.json").write_text(json.dumps(found_states, ensure_ascii=False, indent=2), encoding="utf-8")
        log("baseline_disclosure_scan", found_states=found_states)

        # Efficacy 1024
        page.set_viewport_size({"width": 1024, "height": 768})
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "20_efficacy_1024x768_landing.png")
        (ROOT / "state_efficacy_1024_landing.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")
        click_svg_mark(page, 0)
        page.wait_for_timeout(250)
        shot(page, "21_efficacy_1024x768_drawer.png")
        nav_cover = collect(page)
        (ROOT / "state_efficacy_1024_drawer_navcover.json").write_text(json.dumps(nav_cover, ensure_ascii=False, indent=2), encoding="utf-8")
        close_drawer(page)
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(200)
        page.locator('.kz-filter-item[data-val="product-beta"]').click()
        page.wait_for_timeout(250)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        shot(page, "22_efficacy_1024x768_filter_beta.png")
        (ROOT / "state_efficacy_1024_filter.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")

        # Focus/Esc on 1024
        cell = page.locator('[data-evidence-field="label"]').first
        cell.focus()
        before = collect(page)
        cell.press("Enter")
        page.wait_for_timeout(250)
        opened = collect(page)
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        after = collect(page)
        (ROOT / "state_focus_esc.json").write_text(json.dumps({"before": before, "opened": opened, "after": after}, ensure_ascii=False, indent=2), encoding="utf-8")
        shot(page, "28_efficacy_1024x768_after_esc_focus.png")
        log("focus_esc", before=before.get("focus"), opened=opened.get("drawerHidden"), after=after.get("focus"), afterHidden=after.get("drawerHidden"))

        # Baseline 1024
        page.goto("http://127.0.0.1:8765/baseline.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "23_baseline_1024x768_landing.png")
        page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(250)
        shot(page, "24_baseline_1024x768_drawer.png")
        (ROOT / "state_baseline_1024.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")
        close_drawer(page)

        # Disposition 1024
        page.goto("http://127.0.0.1:8765/disposition.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "25_disposition_1024x768_landing.png")
        click_svg_mark(page, 0)
        if page.locator("#kz-evidence-drawer").is_visible() is False:
            page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(250)
        shot(page, "26_disposition_1024x768_drawer.png")
        page.evaluate("window.scrollTo(0, 560)")
        page.wait_for_timeout(200)
        shot(page, "27_disposition_1024x768_charts.png")
        (ROOT / "state_disposition_1024.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")

        # Efficacy filter empty + no expand
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(200)
        # select only product that exists, then also check chips
        page.locator('.kz-filter-item[data-val="product-alpha"]').click()
        page.wait_for_timeout(200)
        filtered = collect(page)
        (ROOT / "state_filter_narrow.json").write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
        shot(page, "29_efficacy_1280x900_filter_narrow_panel.png")
        close_drawer(page)

        # Open heatmap cell then inspect empty value semantics
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.evaluate("window.scrollTo(0, 980)")
        page.wait_for_timeout(200)
        shot(page, "30_efficacy_1280x900_heatmap_full.png")
        page.locator('.kz-chart-module__group').nth(1).locator('[data-evidence-field="value"]').nth(1).click()
        page.wait_for_timeout(250)
        shot(page, "31_efficacy_1280x900_heatmap_empty_cell.png")
        (ROOT / "state_heatmap_empty_cell.json").write_text(json.dumps(collect(page), ensure_ascii=False, indent=2), encoding="utf-8")

        # Status matrix visual
        page.evaluate("window.scrollTo(0, 1600)")
        page.wait_for_timeout(200)
        shot(page, "32_efficacy_1280x900_status_matrix_full.png")

        browser.close()

    (ROOT / "trace_continue.json").write_text(
        json.dumps({"steps": TRACE, "console": console_all, "remote": remote}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    existing = ROOT / "TRAIL.md"
    extra = "\n".join(
        f"- {s['t']} {s['step']} {json.dumps({k:v for k,v in s.items() if k not in {'t','step'}}, ensure_ascii=False)}"
        for s in TRACE
    )
    prev = existing.read_text(encoding="utf-8") if existing.exists() else ""
    existing.write_text(prev + "\n\n## continue\n" + extra + "\n", encoding="utf-8")
    print("DONE continue")


if __name__ == "__main__":
    main()
