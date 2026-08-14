#!/usr/bin/env python3
"""Focused r2 recheck against http://127.0.0.1:8766. Writes only to this dir."""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8766"
TRACE: list[dict] = []


def log(step: str, **extra) -> None:
    rec = {"t": time.strftime("%H:%M:%S"), "step": step, **extra}
    TRACE.append(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def shot(page, name: str) -> None:
    dest = ROOT / name
    page.screenshot(path=str(dest), full_page=False, animations="disabled")
    log("screenshot", path=name, url=page.url, vw=page.viewport_size)


def dump(name: str, data) -> None:
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(page) -> dict:
    return page.evaluate(
        """() => {
          const drawer = document.getElementById('kz-evidence-drawer');
          const header = document.querySelector('header.site-header, .site-header');
          const menuBtn = Array.from(document.querySelectorAll('button')).find(b => /菜单|关闭菜单/.test((b.textContent||'').trim()));
          const search = document.querySelector('input[type="search"], [role="searchbox"], .site-search input, header input');
          const spacer = document.querySelector('.kz-fixture-spacer');
          const headerBottom = header ? header.getBoundingClientRect().bottom : null;
          const drawerBox = drawer ? drawer.getBoundingClientRect() : null;
          const groups = Array.from(document.querySelectorAll('.kz-chart-module__group')).map(g => {
            const style = getComputedStyle(g);
            return {
              title: g.querySelector('h3, .kz-chart-group__title')?.textContent?.trim() || '',
              display: style.display,
              h: Math.round(g.getBoundingClientRect().height),
              values: Array.from(g.querySelectorAll('[data-evidence-field="value"], .kz-chart-table__cell--value')).map(el => ({
                text: (el.textContent||'').trim(),
                field: el.getAttribute('data-evidence-field'),
                empty: !(el.textContent||'').trim()
              })),
              headers: Array.from(g.querySelectorAll('th')).map(th => th.textContent.trim()),
              preview: (g.innerText||'').slice(0, 280)
            };
          });
          return {
            url: location.href,
            vw: innerWidth, vh: innerHeight,
            title: document.title,
            h1: document.querySelector('h1')?.textContent?.trim() || '',
            drawerHidden: drawer ? drawer.hidden : null,
            drawerTop: drawerBox ? Math.round(drawerBox.top) : null,
            headerBottom: headerBottom != null ? Math.round(headerBottom) : null,
            drawerBelowHeader: (drawerBox && headerBottom != null) ? drawerBox.top >= headerBottom - 1 : null,
            heading: document.querySelector('#kz-evidence-view-subject, #kz-evidence-drawer h3')?.textContent || '',
            drawerText: drawer ? (drawer.innerText||'').slice(0, 3500) : '',
            pinText: document.getElementById('kz-evidence-pin-btn')?.textContent || '',
            pinnedHint: document.getElementById('kz-evidence-pinned-hint')?.textContent || '',
            compareText: document.getElementById('kz-evidence-compare')?.innerText?.slice(0, 2500) || '',
            status: document.getElementById('kz-evidence-drawer-status')?.textContent || '',
            rowCount: document.getElementById('kz-filter-row-count')?.textContent || '',
            filterSummary: document.getElementById('kz-filter-summary')?.textContent || '',
            menuText: menuBtn ? menuBtn.textContent.trim() : null,
            menuExpanded: menuBtn ? menuBtn.getAttribute('aria-expanded') : null,
            searchW: search ? Math.round(search.getBoundingClientRect().width) : 0,
            searchPlaceholder: search ? search.getAttribute('placeholder') : null,
            spacerH: spacer ? spacer.getBoundingClientRect().height : 0,
            bodyTextHas2400: /2400/.test(document.body.innerText||''),
            groups
          };
        }"""
    )


def main() -> None:
    console = []
    remote = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="zh-CN", device_scale_factor=1)
        page.on("console", lambda m: console.append({"type": m.type, "text": m.text}))
        page.on(
            "response",
            lambda r: remote.append({"url": r.url, "status": r.status})
            if not r.url.startswith(BASE)
            else None,
        )

        # ---- 1280 efficacy landing / EASI endpoint ----
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        landing = collect(page)
        dump("state_efficacy_1280_landing.json", landing)
        shot(page, "r2_01_efficacy_1280x900_landing.png")
        page.evaluate("window.scrollTo(0, 520)")
        page.wait_for_timeout(250)
        shot(page, "r2_02_efficacy_1280x900_charts.png")
        charts_mid = collect(page)
        dump("state_efficacy_1280_charts.json", charts_mid)

        # heatmap + status matrix area
        page.evaluate("window.scrollTo(0, 980)")
        page.wait_for_timeout(250)
        shot(page, "r2_03_efficacy_1280x900_heatmap.png")
        page.evaluate("window.scrollTo(0, 1650)")
        page.wait_for_timeout(250)
        shot(page, "r2_04_efficacy_1280x900_status.png")

        # pin two different endpoints for口径差异
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(150)
        # open first numeric cell then pin
        if page.locator('[data-evidence-field="value"]').count():
            page.locator('[data-evidence-field="value"]').first.click()
        else:
            page.locator('[data-evidence-field="label"]').first.click()
        page.wait_for_timeout(300)
        if page.locator("#kz-evidence-pin-btn").is_visible():
            page.locator("#kz-evidence-pin-btn").click()
        # second: try a different product/endpoint label
        labels = page.locator('[data-evidence-field="label"]')
        target = None
        for i in range(labels.count()):
            t = labels.nth(i).inner_text()
            if "疾病活动" in t or "EASI" in t or "产品乙" in t or "产品丙" in t:
                target = labels.nth(i)
                break
        if target is None and labels.count() > 2:
            target = labels.nth(2)
        if target:
            target.click()
            page.wait_for_timeout(300)
            btn = page.locator("#kz-evidence-pin-btn")
            if btn.is_visible() and "固定此条" in btn.inner_text():
                btn.click()
        page.wait_for_timeout(250)
        page.evaluate("document.getElementById('kz-evidence-pinned')?.scrollIntoView({block:'center'})")
        shot(page, "r2_05_efficacy_1280x900_two_pinned.png")
        pinned = collect(page)
        dump("state_efficacy_1280_two_pinned.json", pinned)

        # filter product-beta, check charts remain + pin eviction notice
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(200)
        beta = page.locator('.kz-filter-item[data-val="product-beta"]')
        if beta.count() == 0:
            # try visible text
            page.locator(".kz-filter-item", has_text="产品乙").first.click()
        else:
            beta.click()
        page.wait_for_timeout(350)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        shot(page, "r2_06_efficacy_1280x900_filter_beta.png")
        filtered = collect(page)
        dump("state_efficacy_1280_filter_beta.json", filtered)
        page.evaluate("window.scrollTo(0, 700)")
        page.wait_for_timeout(200)
        shot(page, "r2_07_efficacy_1280x900_filter_beta_charts.png")
        filtered_charts = collect(page)
        dump("state_efficacy_1280_filter_beta_charts.json", filtered_charts)

        # search 产品乙
        page.evaluate("window.scrollTo(0, 0)")
        search = page.locator('input[type="search"], [role="searchbox"], header input').first
        search.click()
        search.fill("产品乙")
        page.wait_for_timeout(400)
        shot(page, "r2_08_efficacy_1280x900_search_beta.png")
        search_state = page.evaluate(
            """() => {
              const panel = document.querySelector('[role="listbox"], .kz-search-results, .site-search__results, #kz-search-results');
              return {
                url: location.href,
                value: document.querySelector('input[type="search"], [role="searchbox"], header input')?.value,
                panelText: panel ? panel.innerText.slice(0, 800) : (document.body.innerText.match(/产品乙[\\s\\S]{0,200}/)||[''])[0],
                visibleHits: Array.from(document.querySelectorAll('a, li, button')).filter(el => /产品乙/.test(el.textContent||'') && el.offsetParent).slice(0,8).map(el => el.textContent.trim().slice(0,80))
              };
            }"""
        )
        dump("state_search_beta.json", search_state)

        # no match
        search.fill("没有这个产品XYZQ")
        page.wait_for_timeout(400)
        shot(page, "r2_09_efficacy_1280x900_search_empty.png")
        empty_search = page.evaluate(
            """() => {
              const panel = document.querySelector('[role="listbox"], .kz-search-results, .site-search__results, #kz-search-results');
              const body = document.body.innerText;
              return {
                panelText: panel ? panel.innerText.slice(0, 500) : '',
                hasNoMatch: /无匹配|没有找到|未找到|无结果|没有符合/.test((panel && panel.innerText) || body)
              };
            }"""
        )
        dump("state_search_empty.json", empty_search)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)

        # ---- baseline EASI not mixed with Age ----
        page.goto(f"{BASE}/baseline.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        shot(page, "r2_10_baseline_1280x900_landing.png")
        base_land = collect(page)
        dump("state_baseline_1280_landing.json", base_land)
        easi = page.locator('[data-evidence-field="label"]', has_text="湿疹")
        if easi.count() == 0:
            easi = page.locator('[data-evidence-field="label"]', has_text="EASI")
        if easi.count() == 0:
            # any second row
            easi = page.locator('[data-evidence-field="label"]').nth(1)
        easi.first.click()
        page.wait_for_timeout(350)
        shot(page, "r2_11_baseline_1280x900_easi_drawer.png")
        easi_state = collect(page)
        dump("state_baseline_easi_drawer.json", easi_state)

        # spacer check on all three
        spacers = {}
        for name in ("efficacy", "baseline", "disposition"):
            page.goto(f"{BASE}/{name}.html", wait_until="networkidle")
            page.wait_for_timeout(350)
            spacers[name] = page.evaluate(
                """() => {
                  const s = document.querySelector('.kz-fixture-spacer');
                  return {
                    exists: !!s,
                    h: s ? Math.round(s.getBoundingClientRect().height) : 0,
                    inline: s ? s.getAttribute('style') : null,
                    scrollH: document.documentElement.scrollHeight,
                    innerH: innerHeight
                  };
                }"""
            )
        dump("state_spacers.json", spacers)

        # ---- 1024: menu collapse + drawer below header ----
        page.set_viewport_size({"width": 1024, "height": 768})
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        shot(page, "r2_12_efficacy_1024x768_landing.png")
        menu = page.locator("button", has_text="菜单")
        if menu.count():
            menu.first.click()
            page.wait_for_timeout(250)
            shot(page, "r2_13_efficacy_1024x768_menu_open.png")
        page.locator('[data-evidence-field="value"]').first.click()
        page.wait_for_timeout(350)
        shot(page, "r2_14_efficacy_1024x768_drawer.png")
        d1024 = collect(page)
        dump("state_efficacy_1024_drawer.json", d1024)
        menu_after = page.evaluate(
            """() => {
              const btn = Array.from(document.querySelectorAll('button')).find(b => /菜单|关闭菜单/.test((b.textContent||'').trim()));
              const navItems = Array.from(document.querySelectorAll('a.site-header__nav-item')).map(a => ({
                text: a.textContent.trim(),
                visible: !!(a.offsetWidth && a.offsetHeight),
                h: Math.round(a.getBoundingClientRect().height)
              }));
              return {
                menuText: btn && btn.textContent.trim(),
                expanded: btn && btn.getAttribute('aria-expanded'),
                navItems,
                drawerTop: Math.round(document.getElementById('kz-evidence-drawer')?.getBoundingClientRect().top || 0),
                headerBottom: Math.round(document.querySelector('.site-header, header.site-header')?.getBoundingClientRect().bottom || 0)
              };
            }"""
        )
        dump("state_1024_menu_after_drawer.json", menu_after)

        # 1024 baseline EASI
        page.goto(f"{BASE}/baseline.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        el = page.locator('[data-evidence-field="label"]', has_text="湿疹")
        if el.count() == 0:
            el = page.locator('[data-evidence-field="label"]').nth(1)
        el.first.click()
        page.wait_for_timeout(300)
        shot(page, "r2_15_baseline_1024x768_easi_drawer.png")
        dump("state_baseline_1024_easi.json", collect(page))

        browser.close()

    dump(
        "trace_r2.json",
        {
            "steps": TRACE,
            "console": console,
            "console_err": [c for c in console if c.get("type") in {"error", "warning"}],
            "remote": remote,
        },
    )
    (ROOT / "TRAIL.md").write_text(
        "\n".join(
            f"- {s['t']} {s['step']} {json.dumps({k:v for k,v in s.items() if k not in {'t','step'}}, ensure_ascii=False)}"
            for s in TRACE
        ),
        encoding="utf-8",
    )
    print("DONE r2")


if __name__ == "__main__":
    main()
