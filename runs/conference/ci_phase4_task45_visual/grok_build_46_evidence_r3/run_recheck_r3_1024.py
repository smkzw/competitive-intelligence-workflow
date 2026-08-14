#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8767"


def dump(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 768}, locale="zh-CN")
        page.goto(f"{BASE}/efficacy.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        page.locator('[data-evidence-field="label"]', has_text="产品乙 · 治疗组 · EASI").first.click()
        page.wait_for_timeout(300)

        def visible_mark(idx):
            return page.evaluate(
                """(i) => {
                  const g = document.querySelectorAll('.kz-chart-module__group')[i];
                  const drawer = document.getElementById('kz-evidence-drawer');
                  const dbox = drawer && !drawer.hidden ? drawer.getBoundingClientRect() : null;
                  if (!g) return {ok:false};
                  g.scrollIntoView({block:'center'});
                  const marks = Array.from(g.querySelectorAll('path[fill]:not([fill="none"]), rect[fill]:not([fill="none"])'))
                    .map(el => {
                      const b = el.getBoundingClientRect();
                      return {x:b.x+b.width/2, y:b.y+b.height/2, w:b.width, h:b.height, left:b.x, right:b.right};
                    })
                    .filter(m => m.w>8 && m.h>8 && m.y>80 && m.y<760);
                  const free = marks.filter(m => !dbox || m.right < dbox.left - 4);
                  const pick = (free[0] || marks[0] || null);
                  let hit = null;
                  if (pick) {
                    const el = document.elementFromPoint(pick.x, pick.y);
                    hit = el ? {tag:el.tagName, id:el.id, cls:(el.className||'').toString().slice(0,140)} : null;
                  }
                  return {
                    ok: !!pick,
                    title: g.querySelector('h3,.kz-chart-group__title')?.textContent?.trim(),
                    drawerLeft: dbox ? Math.round(dbox.left) : null,
                    drawerTop: dbox ? Math.round(dbox.top) : null,
                    nMarks: marks.length,
                    nFree: free.length,
                    pick,
                    hit
                  };
                }""",
                idx,
            )

        # disclosed EASI bar group index 1
        page.evaluate("document.querySelectorAll('.kz-chart-module__group')[1]?.scrollIntoView({block:'center'})")
        page.wait_for_timeout(250)
        bar = visible_mark(1)
        if bar.get("ok") and bar.get("pick"):
            page.mouse.click(bar["pick"]["x"], bar["pick"]["y"])
            page.wait_for_timeout(400)
        page.screenshot(path=str(ROOT / "r3_13_efficacy_1024_bar_click_visible.png"), animations="disabled")
        after_bar = {
            "before": bar,
            "url": page.url,
            "hidden": page.evaluate("() => document.getElementById('kz-evidence-drawer')?.hidden"),
            "heading": page.evaluate("() => document.querySelector('#kz-evidence-view-subject')?.textContent || ''"),
            "top": page.evaluate("() => Math.round(document.getElementById('kz-evidence-drawer')?.getBoundingClientRect().top||0)"),
        }
        dump("state_1024_visible_bar_click.json", after_bar)

        # reopen drawer if closed, then status
        if page.evaluate("() => document.getElementById('kz-evidence-drawer')?.hidden"):
            page.locator('[data-evidence-field="label"]', has_text="产品乙 · 治疗组 · EASI").first.click()
            page.wait_for_timeout(250)
        page.evaluate("document.querySelectorAll('.kz-chart-module__group')[3]?.scrollIntoView({block:'center'})")
        page.wait_for_timeout(250)
        st = visible_mark(3)
        if st.get("ok") and st.get("pick"):
            page.mouse.click(st["pick"]["x"], st["pick"]["y"])
            page.wait_for_timeout(400)
        page.screenshot(path=str(ROOT / "r3_14_efficacy_1024_status_click_visible.png"), animations="disabled")
        after_st = {
            "before": st,
            "url": page.url,
            "hidden": page.evaluate("() => document.getElementById('kz-evidence-drawer')?.hidden"),
            "heading": page.evaluate("() => document.querySelector('#kz-evidence-view-subject')?.textContent || ''"),
            "top": page.evaluate("() => Math.round(document.getElementById('kz-evidence-drawer')?.getBoundingClientRect().top||0)"),
        }
        dump("state_1024_visible_status_click.json", after_st)
        browser.close()
    print("DONE 1024 visible clicks")


if __name__ == "__main__":
    main()
