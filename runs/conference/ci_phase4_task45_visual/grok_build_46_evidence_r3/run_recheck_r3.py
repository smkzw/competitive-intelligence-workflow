#!/usr/bin/env python3
"""Round-3 focused recheck against http://127.0.0.1:8767. Writes only to this dir."""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8767"
TRACE: list[dict] = []


def log(step: str, **extra) -> None:
    rec = {"t": time.strftime("%H:%M:%S"), "step": step, **extra}
    TRACE.append(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def dump(name: str, data) -> None:
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def shot(page, name: str) -> None:
    page.screenshot(path=str(ROOT / name), full_page=False, animations="disabled")
    log("screenshot", path=name, url=page.url, vw=page.viewport_size)


def chart_probe(page) -> dict:
    return page.evaluate(
        """() => {
          const groups = Array.from(document.querySelectorAll('.kz-chart-module__group')).map(g => {
            const style = getComputedStyle(g);
            const texts = Array.from(g.querySelectorAll('text, tspan')).map(t => (t.textContent||'').trim()).filter(Boolean);
            const rows = Array.from(g.querySelectorAll('tbody tr')).map(tr => ({
              hidden: tr.hidden || getComputedStyle(tr).display === 'none',
              text: tr.innerText.replace(/\\s+/g,' ').trim()
            }));
            return {
              title: (g.querySelector('h3,.kz-chart-group__title')?.textContent||'').trim(),
              display: style.display,
              h: Math.round(g.getBoundingClientRect().height),
              svgTexts: texts,
              hasJia: texts.some(t => t.includes('试验一') || t === '-18.4' || t === '-8.6' || t.includes('产品甲')),
              hasYi79: texts.some(t => t.includes('-7.9')),
              hasShiEr: texts.some(t => t.includes('试验二')),
              hasJinxing: texts.some(t => t.includes('进行中')),
              hasYiwancheng: texts.some(t => t.includes('已完成')),
              rows
            };
          });
          const body = document.body.innerText;
          return {
            url: location.href,
            rowCount: document.getElementById('kz-filter-row-count')?.textContent || '',
            groups,
            bodyHasJia: /产品甲|试验一/.test(body),
            visibleJiaInCharts: groups.some(g => g.display !== 'none' && g.h > 0 && g.hasJia)
          };
        }"""
    )


def drawer_probe(page) -> dict:
    return page.evaluate(
        """() => {
          const drawer = document.getElementById('kz-evidence-drawer');
          const header = document.querySelector('.site-header, header.site-header');
          const box = drawer ? drawer.getBoundingClientRect() : null;
          const hb = header ? header.getBoundingClientRect().bottom : null;
          const texts = (drawer && drawer.innerText) || '';
          return {
            url: location.href,
            hidden: drawer ? drawer.hidden : null,
            top: box ? Math.round(box.top) : null,
            headerBottom: hb != null ? Math.round(hb) : null,
            belowHeader: (box && hb != null) ? box.top >= hb - 1 : null,
            heading: document.querySelector('#kz-evidence-view-subject')?.textContent || '',
            status: document.getElementById('kz-evidence-drawer-status')?.innerText || '',
            hint: document.getElementById('kz-evidence-pinned-hint')?.innerText || '',
            compare: document.getElementById('kz-evidence-compare')?.innerText || '',
            drawerText: texts.slice(0, 2500),
            mismatchHits: (texts.match(/口径[^\\n]{0,50}|不可直接比较|终点不同|组别不同|时间点不同|差异/g) || []),
            pageHits: (document.body.innerText.match(/已移出|不再固定|超出当前筛选|已从固定对照移除|固定数据|已移除固定/g) || [])
          };
        }"""
    )


def click_chart_center(page, group_index: int) -> dict:
    info = page.evaluate(
        """(i) => {
          const g = document.querySelectorAll('.kz-chart-module__group')[i];
          if (!g || getComputedStyle(g).display === 'none') return {ok:false, reason:'hidden'};
          const host = g.querySelector('svg, canvas, .kz-chart-group__chart') || g;
          const r = host.getBoundingClientRect();
          const marks = Array.from(g.querySelectorAll('path[fill]:not([fill="none"]), rect[fill]:not([fill="none"])'))
            .map(el => { const b=el.getBoundingClientRect(); return {x:b.x+b.width/2,y:b.y+b.height/2,w:b.width,h:b.height}; })
            .filter(m => m.w>8 && m.h>8);
          return {ok:true, cx: r.x+r.width/2, cy: r.y+r.height/2, w:r.width, h:r.height, nMarks: marks.length, mark: marks[0]||null};
        }""",
        group_index,
    )
    if info.get("ok"):
        page.mouse.click(info["cx"], info["cy"])
        page.wait_for_timeout(350)
        top = page.evaluate(
            """(pt) => {
              const el = document.elementFromPoint(pt.x, pt.y);
              return el ? {tag:el.tagName, id:el.id, cls:(el.className||'').toString().slice(0,120), text:(el.textContent||'').trim().slice(0,80)} : null;
            }""",
            {"x": info["cx"], "y": info["cy"]},
        )
        info["elementFromPoint"] = top
        info["afterUrl"] = page.url
        info["drawerHidden"] = page.evaluate("() => document.getElementById('kz-evidence-drawer')?.hidden")
        info["heading"] = page.evaluate("() => document.querySelector('#kz-evidence-view-subject')?.textContent || ''")
    return info


def main() -> None:
    console = []
    remote = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="zh-CN", device_scale_factor=1)
        page.on("console", lambda m: console.append({"type": m.type, "text": m.text}))
        page.on(
            "response",
            lambda r: remote.append(r.url) if not r.url.startswith(BASE) else None,
        )

        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(700)
        shot(page, "r3_01_efficacy_1280_landing.png")
        dump("state_landing.json", {"charts": chart_probe(page), "easiInTitle": "EASI" in (page.title() + (page.locator("h1").inner_text() if page.locator("h1").count() else ""))})

        # regression: heatmap + status semantics
        page.evaluate("window.scrollTo(0, 900)")
        page.wait_for_timeout(200)
        shot(page, "r3_02_efficacy_1280_heatmap.png")
        page.evaluate("window.scrollTo(0, 1600)")
        page.wait_for_timeout(200)
        shot(page, "r3_03_efficacy_1280_status.png")
        dump("state_unfiltered_charts.json", chart_probe(page))

        # item 2: pin 甲 EASI then open 丙 疾病活动度
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(150)
        page.locator('[data-evidence-field="label"]', has_text="产品甲 · 治疗组 · EASI").first.click()
        page.wait_for_timeout(250)
        page.locator("#kz-evidence-pin-btn").click()
        page.wait_for_timeout(200)
        page.locator('[data-evidence-field="label"]', has_text="产品丙 · 治疗组 · 疾病活动").first.click()
        page.wait_for_timeout(350)
        page.evaluate("document.getElementById('kz-evidence-pinned')?.scrollIntoView({block:'start'})")
        shot(page, "r3_04_efficacy_1280_mismatch_hint.png")
        dump("state_mismatch.json", drawer_probe(page))

        # item 1 + 3: reset, pin 甲, filter 乙
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.locator('[data-evidence-field="label"]', has_text="产品甲 · 治疗组 · EASI").first.click()
        page.wait_for_timeout(200)
        page.locator("#kz-evidence-pin-btn").click()
        page.wait_for_timeout(200)
        page.locator("#kz-filter-entry").click()
        page.wait_for_timeout(150)
        page.locator(".kz-filter-item", has_text="产品乙").first.click()
        page.wait_for_timeout(400)
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        shot(page, "r3_05_efficacy_1280_filter_beta_page.png")
        dump("state_filter_evict.json", drawer_probe(page))
        page.evaluate("window.scrollTo(0, 720)")
        page.wait_for_timeout(250)
        shot(page, "r3_06_efficacy_1280_filter_beta_bar.png")
        page.evaluate("window.scrollTo(0, 1400)")
        page.wait_for_timeout(250)
        shot(page, "r3_07_efficacy_1280_filter_beta_status.png")
        dump("state_filter_charts.json", chart_probe(page))

        # baseline EASI no Age regression
        page.goto(f"{BASE}/baseline.html", wait_until="networkidle")
        page.wait_for_timeout(450)
        el = page.locator('[data-evidence-field="label"]', has_text="湿疹")
        if el.count() == 0:
            el = page.locator('[data-evidence-field="label"]').nth(1)
        el.first.click()
        page.wait_for_timeout(250)
        shot(page, "r3_08_baseline_1280_easi.png")
        dump("state_baseline_easi.json", drawer_probe(page))

        # item 4: 1024 drawer then click chart center
        page.set_viewport_size({"width": 1024, "height": 768})
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        shot(page, "r3_09_efficacy_1024_landing.png")
        page.locator('[data-evidence-field="label"]', has_text="产品乙 · 治疗组 · EASI").first.click()
        page.wait_for_timeout(300)
        shot(page, "r3_10_efficacy_1024_drawer_open.png")
        dump("state_1024_drawer.json", drawer_probe(page))

        # find a visible bar/status chart and click its center
        # bar group is typically index 1 (disclosed EASI)
        bar_click = click_chart_center(page, 1)
        log("click_bar_center_1024", **{k: v for k, v in bar_click.items() if k != "mark"})
        shot(page, "r3_11_efficacy_1024_after_bar_click.png")
        dump("state_1024_after_bar_click.json", {"click": bar_click, "drawer": drawer_probe(page)})

        # reopen drawer then click status matrix center (last visible group)
        page.locator('[data-evidence-field="label"]', has_text="产品乙 · 治疗组 · EASI").first.click()
        page.wait_for_timeout(250)
        n = page.evaluate("() => document.querySelectorAll('.kz-chart-module__group').length")
        status_idx = n - 1
        status_click = click_chart_center(page, status_idx)
        log("click_status_center_1024", **{k: v for k, v in status_click.items() if k != "mark"})
        shot(page, "r3_12_efficacy_1024_after_status_click.png")
        dump("state_1024_after_status_click.json", {"click": status_click, "drawer": drawer_probe(page)})

        browser.close()

    dump("trace_r3.json", {"steps": TRACE, "console": console, "remote": remote})
    (ROOT / "TRAIL.md").write_text(
        "\n".join(
            f"- {s['t']} {s['step']} {json.dumps({k:v for k,v in s.items() if k not in {'t','step'}}, ensure_ascii=False)}"
            for s in TRACE
        ),
        encoding="utf-8",
    )
    print("DONE r3")


if __name__ == "__main__":
    main()
