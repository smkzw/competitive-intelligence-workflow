"""PNH 测试轮交互检查：真实点击筛选、下钻、搜索，并记录可见内容问题。

与 accept_a_portal.py 的静态矩阵互补——本脚本只做交互与内容抽查，
输出 output/playwright/test-round-1/interaction.json。
"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/playwright/test-round-1"
SITES = {
    "A": ROOT / "runs/test-pnh/reports/A/v1/html",
    "B": ROOT / "runs/test-pnh/reports/B/v1/html",
    "C": ROOT / "runs/test-pnh/reports/C/v1/html",
}

PROBE = """
() => {
  const q = (s) => document.querySelector(s);
  const all = (s) => [...document.querySelectorAll(s)];
  const charts = all('.chart,[data-chart]');
  const drawnSvg = charts.filter(c => c.querySelector('svg,canvas')).length;
  return {
    title: document.title,
    chartCount: charts.length,
    chartWithGraphic: drawnSvg,
    tableCount: all('table').length,
    tableRows: all('table tbody tr').length,
    buttons: all('button,[role=tab],select').length,
    filterControls: all('select,[type=search],input[type=text]').map(el => ({
      tag: el.tagName, type: el.type || '', name: el.name || el.id || '',
      options: el.tagName === 'SELECT' ? el.options.length : null,
    })),
    links: all('a[href]').length,
    emptyState: all('.kz-chart-module').filter(el => (el.innerText || '').includes('暂无')).length,
    text: document.body.innerText.slice(0, 4000),
  };
}
"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        console: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}:{m.text[:100]}") if m.type == "error" else None)
        page.on("pageerror", lambda e: console.append(f"pageerror:{str(e)[:100]}"))

        for name, site in SITES.items():
            entry: dict[str, object] = {"site": str(site), "pages": {}}
            targets = {
                "A": ["overview.html", "landscape.html", "efficacy.html", "safety.html",
                      "matrix.html", "regulatory.html", "patents-protection.html",
                      "historical-edge.html", "companies-transactions.html",
                      "clinical-portfolio.html", "product-overview.html"],
                "B": ["overview.html", "efficacy.html", "safety.html", "baseline-overview.html",
                      "baseline-severity.html", "disposition-overview.html",
                      "longitudinal-results.html", "efficacy-safety-matrix.html",
                      "participant-flow.html", "product-trial-profiles.html"],
                "C": ["overview.html", "design-map.html", "design-patterns.html",
                      "inclusion-criteria.html", "exclusion-criteria.html",
                      "endpoint-timepoint-matrix.html", "treatment-arms.html",
                      "sample-analysis-statistics.html", "trial-profile.html"],
            }[name]
            for rel in targets:
                path = site / rel
                if not path.is_file():
                    entry["pages"][rel] = {"error": "missing"}
                    continue
                console.clear()
                page.goto(path.as_uri(), timeout=20000)
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_timeout(250)
                info = page.evaluate(PROBE)
                info["consoleErrors"] = list(console)
                info.pop("text", None)
                entry["pages"][rel] = info

            # 交互：首位筛选控件改变后抽样比较可见文本长度与图表图形数
            entry["interaction"] = []
            for rel, selector in (
                ("efficacy.html", "select"),
                ("landscape.html", "select"),
                ("overview.html", "input"),
            ):
                path = site / rel
                if not path.is_file():
                    continue
                page.goto(path.as_uri(), timeout=20000)
                page.wait_for_timeout(400)
                try:
                    handle = page.query_selector(selector)
                    if handle is None:
                        entry["interaction"].append({"page": rel, "control": selector, "result": "no-control"})
                        continue
                    before = page.evaluate("() => document.body.innerText.length")
                    if selector == "select":
                        options = page.eval_on_selector_all(
                            f"{selector} option", "els => els.map(e => e.value)"
                        )
                        if len(options) > 1:
                            page.select_option(selector, options[1])
                        else:
                            handle.click()
                    else:
                        handle.fill("")
                        handle.type("dan")
                    page.wait_for_timeout(600)
                    after = page.evaluate(
                        "() => ({len: document.body.innerText.length,"
                        " rows: document.querySelectorAll('table tbody tr').length,"
                        " links: document.querySelectorAll('a[href]').length})"
                    )
                    entry["interaction"].append({
                        "page": rel, "control": selector, "beforeLen": before, "after": after,
                        "result": "changed" if after["len"] != before else "no-visible-change",
                    })
                except Exception as error:  # noqa: BLE001
                    entry["interaction"].append({"page": rel, "control": selector, "error": str(error)[:160]})

            # 下钻：从概览进入首个产品/试验档案
            drill = None
            for rel in ("landscape.html", "product-overview.html", "products", "trials", "design-map.html"):
                candidate = site / rel
                if candidate.is_dir() or candidate.suffix != ".html" or not candidate.is_file():
                    continue
                try:
                    page.goto(candidate.as_uri(), timeout=20000)
                except Exception as error:  # noqa: BLE001
                    entry.setdefault("drillErrors", []).append(f"{rel}: {str(error)[:80]}")
                    continue
                page.wait_for_timeout(300)
                href = page.evaluate(
                    "() => { const a = [...document.querySelectorAll('a[href]')]"
                    ".find(x => x.getAttribute('href').includes('products/')"
                    " || x.getAttribute('href').includes('trials/'));"
                    " return a ? a.getAttribute('href') : null; }"
                )
                if href:
                    page.goto((candidate.parent / href).as_uri(), timeout=20000)
                    page.wait_for_timeout(400)
                    drill = {
                        "from": rel, "href": href,
                        "title": page.title(),
                        "len": page.evaluate("() => document.body.innerText.length"),
                        "rows": page.evaluate("() => document.querySelectorAll('table tbody tr').length"),
                        "url": page.url,
                    }
                    break
            entry["drilldown"] = drill
            report[name] = entry

        # 搜索：A 门户顶部搜索
        search = None
        site = SITES["A"]
        page.goto((site / "overview.html").as_uri(), timeout=20000)
        page.wait_for_timeout(400)
        box = page.query_selector("input[type=search], input[type=text], #search, [role=search] input")
        if box is not None:
            box.click()
            box.type("iptacopan")
            page.wait_for_timeout(900)
            search = page.evaluate(
                "() => ({results: document.querySelectorAll('[role=listbox] li, .kz-search-result,"
                " .search-result').length, text: document.body.innerText.slice(0, 600),"
                " url: location.href})"
            )
        else:
            search = {"error": "no-search-box"}
        report["A_search"] = search
        page.close()
        browser.close()
    (OUT / "interaction.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("interaction written:", OUT / "interaction.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
