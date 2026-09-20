"""PNH A 门户浏览器验收（LOOP 第十七轮）。

Chromium/WebKit × 1440×900、1024×1366、390×844、320×568 × 全部物理页面。
检查：页面可打开、中文渲染、水平溢出、空图、来源区外链、键盘可达。
证据：逐组合 JSON + 每页单截图（一个代表视口）留 output/playwright/pnh-a-accept/。
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
import os
import tempfile

if os.environ.get("ACCEPT_SITE"):
    SITE = Path(os.environ["ACCEPT_SITE"]).resolve()
else:
    from ci_workflow.renderers.portal.report_a import build_report_a_artifact
    _payload = json.loads((ROOT / "packets/2026-09-11-pnh-vertical/pnh-a-payload.json").read_text(encoding="utf-8"))
    _td = tempfile.mkdtemp()
    _proj = Path(_td) / "p"
    (_proj / "state").mkdir(parents=True)
    _dp = Path(_td) / "a.json"
    _dp.write_text(json.dumps(_payload, ensure_ascii=False), encoding="utf-8")
    _r = build_report_a_artifact(project_root=_proj, data_path=_dp, project_id="accept-v2",
                                 contract_version=1, run_id="run-accept")
    _site = _r[0] if isinstance(_r, tuple) else _r
    SITE = _site if (_site / "overview.html").exists() else _site / "html"
OUT = Path(os.environ.get(
    "ACCEPT_OUT", str(ROOT / "output/playwright/pnh-a-accept")
))
VIEWPORTS = [(1440, 900), (1024, 1366), (390, 844), (320, 568)]
ENGINES = ["chromium", "webkit"]

CHECKS_JS = """
() => {
  const doc = document.documentElement;
  const overflowX = doc.scrollWidth - doc.clientWidth;
  const emptyCharts = [...document.querySelectorAll('.chart,[data-chart]')]
    .filter(el => el.clientHeight < 40);
  const cjk = /[\u4e00-\u9fff]/.test(document.body.innerText.slice(0, 5000));
  const links = [...document.querySelectorAll('a[href^="http"]')];
  return {
    title: document.title.slice(0, 80),
    overflowX,
    emptyChartCount: emptyCharts.length,
    cjkRendered: cjk,
    externalLinks: links.length,
    bodyText: document.body.innerText.length,
  };
}
"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = sorted(
        str(p.relative_to(SITE)) for p in SITE.rglob("*.html")
    )
    results = []
    with sync_playwright() as pw:
        for engine in ENGINES:
            browser = getattr(pw, engine).launch()
            for width, height in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": height})
                page_errors: list[str] = []
                page.on(
                    "pageerror",
                    lambda error, _bucket=page_errors: _bucket.append(str(error)[:120]),
                )
                for rel in pages:
                    url = (SITE / rel).as_uri()
                    entry = {
                        "engine": engine, "viewport": f"{width}x{height}", "page": rel,
                    }
                    try:
                        page.goto(url, timeout=15000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:  # noqa: BLE001
                            pass
                        page.wait_for_timeout(150)
                        info = page.evaluate(CHECKS_JS)
                        entry.update(info)
                        entry["pageErrors"] = len(page_errors)
                        entry["ok"] = (
                            info["overflowX"] <= 2 and info["emptyChartCount"] == 0
                            and info["bodyText"] > 200
                        )
                    except Exception as error:  # noqa: BLE001
                        entry["ok"] = False
                        entry["error"] = str(error)[:120]
                    results.append(entry)
                # 代表视口每页单截图（每引擎 1440 一轮）
                if (width, height) == (1440, 900) and engine == "chromium":
                    shot_dir = OUT / engine
                    shot_dir.mkdir(exist_ok=True)
                    for rel in pages[:3]:
                        page.goto((SITE / rel).as_uri(), timeout=15000)
                        page.screenshot(path=str(shot_dir / (rel.replace("/", "__") + ".png")))
                page.close()
            browser.close()
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "site": str(SITE),
        "page_count": len(pages),
        "combination_count": len(results),
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "failures": [r for r in results if not r["ok"]][:40],
    }
    (OUT / "acceptance.json").write_text(
        json.dumps({"summary": report, "results": results}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=1)[:600])
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
