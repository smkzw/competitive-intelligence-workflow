#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8766"


def dump(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def shot(page, name):
    page.screenshot(path=str(ROOT / name), full_page=False, animations="disabled")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(600)

        # Pin EASI 产品甲治疗组, then 疾病活动度 产品丙
        page.locator('[data-evidence-field="label"]', has_text="产品甲 · 治疗组 · EASI").first.click()
        page.wait_for_timeout(250)
        page.locator("#kz-evidence-pin-btn").click()
        page.locator('[data-evidence-field="label"]', has_text="产品丙 · 治疗组 · 疾病活动").first.click()
        page.wait_for_timeout(250)
        if "固定此条" in page.locator("#kz-evidence-pin-btn").inner_text():
            page.locator("#kz-evidence-pin-btn").click()
        page.wait_for_timeout(250)
        page.evaluate("document.getElementById('kz-evidence-pinned')?.scrollIntoView({block:'start'})")
        shot(page, "r2_16_efficacy_1280x900_cross_endpoint_pin.png")
        cross = page.evaluate(
            """() => ({
              url: location.href,
              status: document.getElementById('kz-evidence-drawer-status')?.innerText || '',
              hint: document.getElementById('kz-evidence-pinned-hint')?.innerText || '',
              compare: document.getElementById('kz-evidence-compare')?.innerText || '',
              alerts: Array.from(document.querySelectorAll('[role="status"], [role="alert"], .kz-evidence-mismatch, .kz-pin-warning, .kz-compare-warning')).map(el => ({
                cls: el.className, text: el.innerText.trim().slice(0,400)
              })),
              bodyHits: (document.body.innerText.match(/口径[^\\n]{0,40}|不可直接比较|时间点不同|定义不同|差异提示/g) || [])
            })"""
        )
        dump("state_cross_endpoint_pin.json", cross)

        # Filter 产品乙 while 产品甲+丙 pinned; capture eviction copy
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(150)
        page.locator(".kz-filter-item", has_text="产品乙").first.click()
        page.wait_for_timeout(400)
        shot(page, "r2_17_efficacy_1280x900_filter_evict.png")
        evict = page.evaluate(
            """() => ({
              url: location.href,
              status: document.getElementById('kz-evidence-drawer-status')?.innerText || '',
              hint: document.getElementById('kz-evidence-pinned-hint')?.innerText || '',
              drawerText: document.getElementById('kz-evidence-drawer')?.innerText?.slice(0,2000) || '',
              alerts: Array.from(document.querySelectorAll('[role="status"], [role="alert"], .kz-filter-restore-error, .kz-filter-local-hint, .kz-evidence-status')).map(el => ({
                id: el.id, hidden: el.hidden, cls: el.className, text: (el.innerText||'').trim()
              })),
              bodyHits: (document.body.innerText.match(/固定[^\\n]{0,30}|已移出|不再显示|超出当前筛选|当前筛选下[^\\n]{0,30}/g) || [])
            })"""
        )
        dump("state_filter_evict.json", evict)

        # After 产品乙 filter, which chart marks remain and product ids
        vis = page.evaluate(
            """() => {
              const groups = Array.from(document.querySelectorAll('.kz-chart-module__group')).map(g => {
                const style = getComputedStyle(g);
                const rows = Array.from(g.querySelectorAll('tbody tr')).map(tr => ({
                  hidden: tr.hidden || getComputedStyle(tr).display === 'none',
                  text: tr.innerText.replace(/\\s+/g,' ').trim(),
                  row: tr.getAttribute('data-filter-row-id') || tr.querySelector('[data-evidence-open]')?.getAttribute('data-evidence-open')
                }));
                const labels = Array.from(g.querySelectorAll('text')).map(t => t.textContent.trim()).filter(Boolean);
                return {
                  title: g.querySelector('h3,.kz-chart-group__title')?.textContent?.trim(),
                  display: style.display,
                  h: Math.round(g.getBoundingClientRect().height),
                  rows, labels: labels.slice(0, 20)
                };
              });
              return groups;
            }"""
        )
        dump("state_filter_beta_chart_rows.json", vis)
        page.evaluate("window.scrollTo(0, 820)")
        page.wait_for_timeout(200)
        shot(page, "r2_18_efficacy_1280x900_filter_beta_bars.png")

        # Search UI visible
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        box = page.locator('input[type="search"], [role="searchbox"], header input').first
        box.click()
        box.fill("产品乙")
        page.wait_for_timeout(400)
        shot(page, "r2_19_efficacy_1280x900_search_beta_panel.png")
        box.fill("没有这个产品XYZQ")
        page.wait_for_timeout(400)
        shot(page, "r2_20_efficacy_1280x900_search_empty_panel.png")

        # 1024 search + drawer below header confirm
        page.set_viewport_size({"width": 1024, "height": 768})
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.locator("button", has_text="菜单").first.click()
        page.wait_for_timeout(200)
        page.locator('[data-evidence-field="label"]', has_text="产品乙 · 治疗组 · EASI").first.click()
        page.wait_for_timeout(300)
        shot(page, "r2_21_efficacy_1024x768_drawer_after_menu.png")
        dump(
            "state_1024_after_menu_drawer.json",
            page.evaluate(
                """() => ({
                  menu: Array.from(document.querySelectorAll('button')).find(b=>/菜单/.test(b.textContent||''))?.getAttribute('aria-expanded'),
                  navVisible: Array.from(document.querySelectorAll('a.site-header__nav-item')).some(a => a.offsetHeight>0),
                  drawerTop: Math.round(document.getElementById('kz-evidence-drawer')?.getBoundingClientRect().top||0),
                  headerBottom: Math.round(document.querySelector('.site-header')?.getBoundingClientRect().bottom||0),
                  heading: document.querySelector('#kz-evidence-view-subject')?.textContent
                })"""
            ),
        )
        browser.close()
    print("DONE extra")


if __name__ == "__main__":
    main()
