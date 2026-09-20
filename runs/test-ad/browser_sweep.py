import json
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path("/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow")
OUT = ROOT / "output/playwright/test-ad"
OUT.mkdir(parents=True, exist_ok=True)

SITES = {
    "A": ROOT / "runs/test-ad/reports/A/v1/html",
    "B": ROOT / "runs/test-ad/reports/B/v1/html",
    "C": ROOT / "runs/test-ad/reports/C/v1/html",
}

VIEWPORTS = [
    {"name": "desktop", "width": 1440, "height": 900},
    {"name": "tablet", "width": 1024, "height": 1366},
    {"name": "mobile", "width": 390, "height": 844},
    {"name": "small_mobile", "width": 320, "height": 568},
]

ENGINES = ["chromium", "webkit"]

def run_sweep():
    summary = {
        "reports": {},
        "interaction": {},
        "console_errors": [],
        "page_errors": [],
        "total_combinations": 0,
        "passed_combinations": 0,
        "failed_combinations": 0,
    }

    with sync_playwright() as pw:
        for r_name, site in SITES.items():
            html_files = sorted(str(p.relative_to(site)) for p in site.rglob("*.html"))
            r_summary = {
                "pages_count": len(html_files),
                "combinations": 0,
                "passed": 0,
                "failed": 0,
                "overflow_issues": [],
                "empty_charts": [],
            }
            print(f"=== Sweeping Report {r_name} ({len(html_files)} pages) ===")

            for engine_name in ENGINES:
                browser_type = getattr(pw, engine_name)
                try:
                    browser = browser_type.launch()
                except Exception as e:
                    print(f"Could not launch {engine_name}: {e}")
                    continue

                for vp in VIEWPORTS:
                    page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
                    page.on("console", lambda m: summary["console_errors"].append(f"[{r_name}][{engine_name}][{vp['name']}] console.{m.type}: {m.text[:120]}") if m.type == "error" else None)
                    page.on("pageerror", lambda e: summary["page_errors"].append(f"[{r_name}][{engine_name}][{vp['name']}] pageerror: {str(e)[:120]}"))

                    for rel_p in html_files:
                        url = f"file://{site / rel_p}"
                        r_summary["combinations"] += 1
                        summary["total_combinations"] += 1
                        try:
                            page.goto(url, wait_until="load")
                            # Evaluate checks
                            res = page.evaluate('''() => {
                                const doc = document.documentElement;
                                const overflowX = doc.scrollWidth - doc.clientWidth;
                                const emptyCharts = [...document.querySelectorAll('.chart,[data-chart],[data-a-chart]')]
                                  .filter(el => el.clientHeight < 30);
                                const hasCjk = /[\u4e00-\u9fff]/.test(document.body.innerText.slice(0, 5000));
                                return {
                                    overflowX,
                                    emptyChartsCount: emptyCharts.length,
                                    hasCjk,
                                    title: document.title,
                                    bodyLen: document.body.innerText.length
                                };
                            }''')

                            if res["overflowX"] > 2 and vp["name"] in ("desktop", "tablet"):
                                r_summary["failed"] += 1
                                summary["failed_combinations"] += 1
                                r_summary["overflow_issues"].append(f"{rel_p} ({engine_name}, {vp['name']}): overflow {res['overflowX']}px")
                            else:
                                r_summary["passed"] += 1
                                summary["passed_combinations"] += 1

                        except Exception as e:
                            r_summary["failed"] += 1
                            summary["failed_combinations"] += 1
                            print(f"Error on {rel_p}: {e}")

                    page.close()
                browser.close()

            summary["reports"][r_name] = r_summary

        # === Interaction Tests ===
        print("=== Running Detailed Interactive Probes ===")
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        interaction_log = {}

        # 1. Test Report A matrix.html 3D controls
        page.goto(f"file://{SITES['A'] / 'matrix.html'}")
        matrix_status = page.evaluate('''() => {
            const chart = document.querySelector('[data-a-chart="matrix"], .kz-chart');
            const emptyText = chart ? (chart.innerText || '') : '';
            const coverage = document.querySelector('[data-matrix-coverage]');
            const coverageText = coverage ? (coverage.innerText || '') : '';
            const points = document.querySelectorAll('.kz-bubble-point, svg circle');
            return {
                chartText: emptyText.slice(0, 200),
                coverageText: coverageText.slice(0, 200),
                pointsCount: points.length,
                hasPoints: points.length > 0
            };
        }''')
        interaction_log["A_matrix_initial"] = matrix_status

        # Try clicking matrix control selectors
        selects = page.locator("select")
        select_count = selects.count()
        interaction_log["A_matrix_select_count"] = select_count
        if select_count > 0:
            try:
                selects.nth(0).select_option(index=1)
                page.wait_for_timeout(300)
                after_select = page.evaluate('''() => {
                    const points = document.querySelectorAll('.kz-bubble-point, svg circle');
                    return { pointsCount: points.length };
                }''')
                interaction_log["A_matrix_after_select"] = after_select
            except Exception as e:
                interaction_log["A_matrix_select_error"] = str(e)

        # 2. Test Report A evidence drawer
        page.goto(f"file://{SITES['A'] / 'efficacy.html'}")
        btn = page.locator('[data-open-evidence], .kz-a-evidence-button').first
        if btn.count() > 0:
            btn.click()
            page.wait_for_timeout(300)
            drawer = page.evaluate('''() => {
                const el = document.querySelector('#data-basis-panel, .kz-evidence-panel');
                return {
                    visible: el ? !el.hidden : false,
                    content: el ? el.innerText.slice(0, 300) : ''
                };
            }''')
            interaction_log["A_evidence_drawer"] = drawer

        # 3. Test Report B quick filters and table
        page.goto(f"file://{SITES['B'] / 'efficacy.html'}")
        page.wait_for_timeout(500)
        b_eff_state = page.evaluate('''() => {
            const btns = document.querySelectorAll('.kz-b-filter-quick__button');
            const rows = document.querySelectorAll('table tbody tr');
            return {
                filterButtonsCount: btns.length,
                tableRowsCount: rows.length,
                firstRowText: rows.length > 0 ? rows[0].innerText.slice(0, 150) : ''
            };
        }''')
        interaction_log["B_efficacy_initial"] = b_eff_state

        # Click a filter button in B
        filter_btn = page.locator('.kz-b-filter-quick__button').first
        if filter_btn.count() > 0:
            btn_text = filter_btn.inner_text()
            filter_btn.click()
            page.wait_for_timeout(300)
            after_filter = page.evaluate('''() => {
                const rows = document.querySelectorAll('table tbody tr');
                return { tableRowsCount: rows.length };
            }''')
            interaction_log[f"B_efficacy_after_filter_{btn_text}"] = after_filter

        # 4. Test Report C design map and pattern filters
        page.goto(f"file://{SITES['C'] / 'overview.html'}")
        c_state = page.evaluate('''() => {
            const cards = document.querySelectorAll('.kz-c-card, .kz-c-trial-card, article');
            return {
                title: document.title,
                cardsCount: cards.length,
                bodySnippet: document.body.innerText.slice(0, 400)
            };
        }''')
        interaction_log["C_overview"] = c_state

        page.goto(f"file://{SITES['C'] / 'design-map.html'}")
        c_map = page.evaluate('''() => {
            const items = document.querySelectorAll('.kz-c-map-item, table tbody tr, .kz-c-pattern');
            return {
                title: document.title,
                itemsCount: items.length,
                textSnippet: document.body.innerText.slice(0, 400)
            };
        }''')
        interaction_log["C_design_map"] = c_map

        summary["interaction"] = interaction_log
        browser.close()

    out_file = OUT / "sweep_results.json"
    out_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sweep complete! Results written to {out_file}")
    print(f"Total combinations: {summary['total_combinations']}, Passed: {summary['passed_combinations']}, Failed: {summary['failed_combinations']}")
    print(f"Console errors: {len(summary['console_errors'])}, Page errors: {len(summary['page_errors'])}")
    return summary

if __name__ == '__main__':
    run_sweep()
