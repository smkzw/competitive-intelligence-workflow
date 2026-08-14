#!/usr/bin/env python3
from __future__ import annotations
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
TRACE = []

def log(step, **extra):
    rec = {"t": time.strftime("%H:%M:%S"), "step": step, **extra}
    TRACE.append(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)

def shot(page, name):
    page.screenshot(path=str(ROOT / name), full_page=False, animations="disabled")
    log("screenshot", path=name, url=page.url, vw=page.viewport_size)

def main():
    console = []
    reqs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 768}, locale="zh-CN")
        page.on("console", lambda m: console.append({"type": m.type, "text": m.text, "loc": m.location}))
        page.on("request", lambda r: reqs.append(r.url))
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        # open hamburger
        menu = page.locator("button", has_text="菜单")
        log("menu_count", n=menu.count())
        if menu.count():
            menu.first.click()
            page.wait_for_timeout(250)
            shot(page, "33_efficacy_1024x768_menu_open.png")
            nav_state = page.evaluate(
                """() => ({
                  menuExpanded: document.querySelector('[aria-expanded="true"]')?.textContent?.trim(),
                  visibleNav: Array.from(document.querySelectorAll('a.site-header__nav-item')).map(a=>({
                    text:a.textContent.trim(),
                    visible: !!(a.offsetWidth||a.offsetHeight),
                    r: Object.fromEntries(['x','y','width','height'].map(k=>[k,Math.round(a.getBoundingClientRect()[k])]))
                  })),
                  searchVisible: !!(document.querySelector('input[type="search"], [role="searchbox"]')?.offsetWidth)
                })"""
            )
            (ROOT / "state_1024_menu.json").write_text(json.dumps(nav_state, ensure_ascii=False, indent=2), encoding="utf-8")
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)

        # open drawer via table cell
        page.locator('[data-evidence-field="value"]').first.click()
        page.wait_for_timeout(300)
        shot(page, "34_efficacy_1024x768_table_drawer.png")
        d = page.evaluate(
            """() => ({
              url: location.href,
              hidden: document.getElementById('kz-evidence-drawer')?.hidden,
              heading: document.querySelector('#kz-evidence-drawer h3')?.textContent,
              drawerW: Math.round(document.getElementById('kz-evidence-drawer')?.getBoundingClientRect().width||0),
              mainW: Math.round(document.getElementById('main')?.getBoundingClientRect().width||0),
              overflowX: document.documentElement.scrollWidth > innerWidth+2,
              navCovered: Array.from(document.querySelectorAll('a.site-header__nav-item, button')).filter(el=>/菜单|试验完成|基线/.test(el.textContent||'')).map(el=>{
                const r=el.getBoundingClientRect();
                const top=document.elementFromPoint(r.x+r.width/2, r.y+r.height/2);
                return {text:(el.textContent||'').trim().slice(0,20), coveredBy: top && (top.className||top.id||top.tagName).toString().slice(0,80)};
              })
            })"""
        )
        (ROOT / "state_1024_table_drawer.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # filter alpha then inspect remaining visible chart titles
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(150)
        page.locator('.kz-filter-item[data-val="product-alpha"]').click()
        page.wait_for_timeout(250)
        page.keyboard.press("Escape")
        vis = page.evaluate(
            """() => {
              const groups = Array.from(document.querySelectorAll('.kz-chart-module__group')).map(g=>{
                const r=g.getBoundingClientRect();
                const style=getComputedStyle(g);
                return {
                  title:g.querySelector('h3,.kz-chart-group__title')?.textContent?.trim(),
                  display:style.display, visibility:style.visibility,
                  h:Math.round(r.height), w:Math.round(r.width),
                  hiddenAttr:g.hidden,
                  textPreview:(g.innerText||'').slice(0,80)
                };
              });
              const facts=Array.from(document.querySelectorAll('.kz-fixture-facts [data-filter-row-id]')).map(tr=>({
                id:tr.getAttribute('data-filter-row-id'),
                hidden:tr.hidden || getComputedStyle(tr).display==='none',
                text:tr.querySelector('[data-evidence-field="label"]')?.textContent?.trim()
              }));
              return {url:location.href, groups, facts, rowCount:document.getElementById('kz-filter-row-count')?.textContent};
            }"""
        )
        (ROOT / "state_filter_chart_visibility.json").write_text(json.dumps(vis, ensure_ascii=False, indent=2), encoding="utf-8")
        page.evaluate("window.scrollTo(0, 900)")
        page.wait_for_timeout(200)
        shot(page, "35_efficacy_1280x900_filter_alpha_scrolled.png")

        # EASI vs age field mix on baseline
        page.goto("http://127.0.0.1:8765/baseline.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.locator('[data-evidence-open="report-row_8e2a17032e949e11c8777470"][data-evidence-field="label"]').click()
        page.wait_for_timeout(250)
        easi = page.evaluate(
            """() => ({
              url:location.href,
              heading:document.querySelector('#kz-evidence-drawer h3')?.textContent,
              text:document.getElementById('kz-evidence-drawer')?.innerText || ''
            })"""
        )
        (ROOT / "state_baseline_easi_drawer.json").write_text(json.dumps(easi, ensure_ascii=False, indent=2), encoding="utf-8")
        shot(page, "36_baseline_1280x900_easi_drawer.png")
        page.locator("#kz-evidence-pin-btn").click()
        page.wait_for_timeout(150)
        page.locator('[data-evidence-open="report-row_697a9c6b3a5289cf7f663372"][data-evidence-field="label"]').click()
        page.wait_for_timeout(250)
        page.locator("#kz-evidence-pin-btn").click()
        page.wait_for_timeout(200)
        page.evaluate("document.getElementById('kz-evidence-pinned')?.scrollIntoView({block:'start'})")
        shot(page, "37_baseline_1280x900_age_vs_easi_compare.png")
        both = page.evaluate(
            """() => ({
              url:location.href,
              heading:document.querySelector('#kz-evidence-drawer h3')?.textContent,
              compare:document.getElementById('kz-evidence-compare')?.innerText || '',
              current:document.getElementById('kz-evidence-drawer')?.innerText?.slice(0,2500)
            })"""
        )
        (ROOT / "state_baseline_compare.json").write_text(json.dumps(both, ensure_ascii=False, indent=2), encoding="utf-8")

        # copy URL restore
        url = page.url
        page.goto("http://127.0.0.1:8765/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(300)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(500)
        restored = page.evaluate(
            """() => ({
              url:location.href,
              hidden:document.getElementById('kz-evidence-drawer')?.hidden,
              heading:document.querySelector('#kz-evidence-drawer h3')?.textContent,
              pinCount:(document.getElementById('kz-evidence-compare')?.innerText||'').includes('湿疹') && (document.getElementById('kz-evidence-compare')?.innerText||'').includes('年龄')
            })"""
        )
        (ROOT / "state_url_restore_baseline.json").write_text(json.dumps({"saved": url, "restored": restored}, ensure_ascii=False, indent=2), encoding="utf-8")
        shot(page, "38_baseline_1280x900_url_restore.png")

        # scan all three pages for missing-status words after opening drawers
        scan = {}
        for name, u in [("efficacy","http://127.0.0.1:8765/efficacy.html"),("baseline","http://127.0.0.1:8765/baseline.html"),("disposition","http://127.0.0.1:8765/disposition.html")]:
            page.goto(u, wait_until="networkidle")
            page.wait_for_timeout(400)
            ids = page.eval_on_selector_all("[data-evidence-open]", "els => [...new Set(els.map(e=>e.getAttribute('data-evidence-open')))]")
            page_hits = []
            for rid in ids:
                page.locator(f'[data-evidence-open="{rid}"][data-evidence-field="label"]').first.click()
                page.wait_for_timeout(120)
                text = page.locator("#kz-evidence-drawer").inner_text()
                page_hits.append({
                    "id": rid,
                    "heading": page.locator("#kz-evidence-drawer h3").inner_text() if page.locator("#kz-evidence-drawer h3").count() else "",
                    "未公开": "未公开" in text,
                    "尚未公开": "尚未公开" in text,
                    "不适用": "不适用" in text,
                    "技术暂不可用": "技术暂不可用" in text,
                    "来源未列示": "来源未列示" in text,
                    "原文未提供": "原文未提供" in text,
                })
            scan[name] = page_hits
        (ROOT / "state_missing_semantics_scan.json").write_text(json.dumps(scan, ensure_ascii=False, indent=2), encoding="utf-8")

        browser.close()
    (ROOT / "trace_final.json").write_text(json.dumps({"steps": TRACE, "console": console, "unique_hosts": sorted({u.split('/')[2] for u in reqs if '://' in u}), "remote": [u for u in reqs if not u.startswith('http://127.0.0.1:8765')]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE final")

if __name__ == "__main__":
    main()
