"""release → 三个门户目录 site/{A,B,C}/。只做投影：所有标签、角色、比较都已在 release 里。"""

from __future__ import annotations

import hashlib
import json
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
    "pubmed": "PubMed",
    "publications": "论文结果",
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
        "links": {k: f"../{k}/index.html" for k in rel.get("rendered_reports", REPORTS)},
    }
    if report == "A":
        sources = {x["source_id"]: {"url": x["url"], "title": x["title"], "kind": x["kind"]} for x in rel["sources"]}
        return {
            **head,
            "a": rel["a"],
            "trials": _trial_index(rel),
            "stats": rel["stats"],
            "events": [e for e in rel["events"] if e["status"] in
                       {"registry", "verified", "dual_agreed", "arbitrated"}],
            "sources": sources,
        }
    if report == "B":
        return {**head, "b": rel["b"], "trials": _trial_index(rel)}
    return {**head, "c": rel["c"]}


def presentation_digest():
    root = resources.files("ciw.render")
    digest = hashlib.sha256()
    paths = [root.joinpath("site.py")]
    paths += [p for folder in ("templates", "static") for p in root.joinpath(folder).iterdir() if p.is_file()]
    for item in sorted(paths, key=lambda p: str(p)):
        digest.update(item.name.encode())
        digest.update(item.read_bytes())
    return digest.hexdigest()


def _write_immutable(path, data, recover=False):
    if path.exists():
        if path.read_bytes() == data:
            return
        if not recover:
            raise ValueError("已存在的不可变报告文件冲突，原文件已保留")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def _render_attempt(base, site, rel, selected):
    """Only an explicitly unfinished, never-published attempt may repair partial bytes."""
    marker = site.parent / f".{site.name}.pending.json"
    expected = dict(release_id=rel["release_id"], presentation_digest=rel.get("presentation_digest"), reports=selected)
    if not site.exists() and not marker.exists():
        _write_immutable(marker, json.dumps(expected, sort_keys=True).encode())
    if not marker.exists():
        return marker, False
    if json.loads(marker.read_text()) != expected:
        raise ValueError("未完成报告版本冲突，原文件已保留")
    pointer = base.parent / "current.json"
    if pointer.exists() and json.loads(pointer.read_text()).get("release_id") == rel["release_id"]:
        raise ValueError("已提交报告仍有未完成标记，原文件已保留")
    return marker, True


def rerender_current(ws):
    with ws.writer():
        return _rerender_current(ws)


def _rerender_current(ws):
    from ciw.release import write_release
    doc = load_release(ws.current_release_dir())
    body = {k: v for k, v in doc.items()
            if k not in {"schema_version", "release_id", "generated_at", "code_version"}}
    body["presentation_digest"] = presentation_digest()
    release_id, path = write_release(ws, body)
    site = render_release(path)
    ws.set_current(release_id)
    return site


def render_release(release_path: str | Path, out_dir: str | Path | None = None, reports=None) -> Path:
    rel = load_release(release_path)
    if not out_dir and rel.get("presentation_digest") != presentation_digest():
        raise ValueError("呈现版本已变化，请运行ciw render生成新版本，保留旧快照")
    base = Path(release_path)
    base = base if base.is_dir() else base.parent
    site = Path(out_dir) if out_dir else base / "site"
    env = Environment(loader=PackageLoader("ciw.render", "templates"), autoescape=select_autoescape())
    static = resources.files("ciw.render").joinpath("static")
    selected = reports if reports is not None else rel.get("rendered_reports", list(REPORTS))
    marker, recovering = _render_attempt(base, site, rel, selected)
    for report in selected:
        if report not in REPORTS:
            raise ValueError("未知报告类型")
        d = site / report
        d.mkdir(parents=True, exist_ok=True)
        for name in (*STATIC, f"{report.lower()}.js"):
            _write_immutable(d / name, static.joinpath(name).read_bytes(), recover=recovering)
        data = json.dumps(_payload(rel, report), ensure_ascii=False, separators=(",", ":"))
        _write_immutable(d / "data.js", ("window.CIW=" + data.replace("</", "<\\/") + ";\n").encode(),
                         recover=recovering)
        html = env.get_template(f"{report.lower()}.html").render(
            report=report, title=REPORTS[report], indication=rel["indication"], cutoff=rel["cutoff"],
            reports={r: REPORTS[r] for r in selected}
        )
        _write_immutable(d / "index.html", html.encode(), recover=recovering)
    if recovering:
        marker.unlink()
    return site
