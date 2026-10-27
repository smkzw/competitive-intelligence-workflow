"""release → 三个门户目录 site/{A,B,C}/。只做投影：所有标签、角色、比较都已在 release 里。"""

from __future__ import annotations

import json
import shutil
from importlib import resources
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from ciw.release import load_release

REPORTS = {"A": "竞品全景", "B": "临床结果", "C": "设计先例"}
COVERAGE_ZH = {
    "ctgov": "ClinicalTrials.gov",
    "cde": "CDE 登记平台",
    "docs": "公告/公众号/NMPA",
    "company": "药企公告",
    "wechat": "公众号",
    "nmpa": "NMPA",
    "europepmc": "文献",
}
STATUS_ZH = {"ok": "已覆盖", "partial": "部分覆盖", "not_captured": "未采集", "failed": "失败", "skipped": "未抽取"}
STATIC = ("style.css", "common.js", "echarts.min.js", "LICENSE")


def _trial_index(rel: dict[str, Any]) -> dict[str, Any]:
    return {
        t["trial_id"]: {
            "acronym": t["acronym"],
            "title": t["title"],
            "phase": t["phase"],
            "status": t["status"],
            "url": t["url"],
            "registry": t["registry"],
            "relevance": t["relevance"],
        }
        for t in rel["trials"]
    }


def _payload(rel: dict[str, Any], report: str) -> dict[str, Any]:
    head = {
        "report": report,
        "report_label": REPORTS[report],
        "indication": rel["indication"],
        "cutoff": rel["cutoff"],
        "release_id": rel["release_id"],
        "generated_at": rel["generated_at"],
        "own_product_id": rel["own_product_id"],
        "coverage": [
            {
                **c,
                "label": COVERAGE_ZH.get(c["source"], c["source"]),
                "status_label": STATUS_ZH.get(c["status"], c["status"]),
            }
            for c in rel["coverage"]
        ],
        "links": {k: f"../{k}/index.html" for k in REPORTS},
    }
    if report == "A":
        sources = {x["source_id"]: {"url": x["url"], "title": x["title"], "kind": x["kind"]} for x in rel["sources"]}
        return {
            **head,
            "a": rel["a"],
            "trials": _trial_index(rel),
            "stats": rel["stats"],
            "events": rel["events"],
            "sources": sources,
        }
    if report == "B":
        return {**head, "b": rel["b"], "trials": _trial_index(rel)}
    return {**head, "c": rel["c"]}


def render_release(release_path: str | Path, out_dir: str | Path | None = None) -> Path:
    rel = load_release(release_path)
    base = Path(release_path)
    base = base if base.is_dir() else base.parent
    site = Path(out_dir) if out_dir else base / "site"
    env = Environment(loader=PackageLoader("ciw.render", "templates"), autoescape=select_autoescape())
    static = resources.files("ciw.render").joinpath("static")
    for report in REPORTS:
        d = site / report
        d.mkdir(parents=True, exist_ok=True)
        for name in (*STATIC, f"{report.lower()}.js"):
            with resources.as_file(static.joinpath(name)) as src:
                shutil.copyfile(src, d / name)
        data = json.dumps(_payload(rel, report), ensure_ascii=False, separators=(",", ":"))
        (d / "data.js").write_text("window.CIW=" + data.replace("</", "<\\/") + ";\n", encoding="utf-8")
        html = env.get_template(f"{report.lower()}.html").render(
            report=report, title=REPORTS[report], indication=rel["indication"], cutoff=rel["cutoff"], reports=REPORTS
        )
        (d / "index.html").write_text(html, encoding="utf-8")
    return site
