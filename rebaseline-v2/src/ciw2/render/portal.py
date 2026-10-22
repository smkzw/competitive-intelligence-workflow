"""门户渲染：数据（DB）→ 报告数据 → Jinja2 模板 → HTML（平台内直接展示）。
规则：
- 图表数值轴只放 verified 事实（代码解析或原文核验通过）；critical 未核实的只进表格并标「未核实」。
- 不可比的结果不强行同轴：按 (终点, 时间点, 统计形式, 单位) 分组，各组单独小图。
- 不写任何适应症/药物/NCT 专用逻辑（v1 的 PNH 硬编码教训）。
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ciw2.domain.semantics import parse_timepoint
from ciw2.store.db import DB

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
PHASE_ORDER = ["preclinical", "phase1", "phase1_2", "phase2", "phase2_3", "phase3", "nda_bla", "approved",
               "phase4", "unknown"]
PHASE_ZH = {"preclinical": "临床前", "phase1": "I 期", "phase1_2": "I/II 期", "phase2": "II 期",
            "phase2_3": "II/III 期", "phase3": "III 期", "nda_bla": "上市申请", "approved": "已上市",
            "phase4": "IV 期", "unknown": "未知"}
STATUS_ZH = {"verified": "已核实", "unverified": "未核实", "conflict": "冲突", "unknown": "未报告"}
REPORT_ZH = {"A": "A · 竞争格局", "B": "B · 疗效与安全性", "C": "C · 试验设计先例"}

_env = Environment(loader=FileSystemLoader(str(HERE / "templates")), autoescape=select_autoescape(["html"]))
_env.filters["phase"] = lambda p: PHASE_ZH.get(p or "unknown", p)
_env.filters["status"] = lambda s: STATUS_ZH.get(s, s)


def _trial_drugs(db: DB, pid: str) -> dict[str, list[str]]:
    names = {e["id"]: e["name"] for e in db.entities(pid, "drug")}
    out: dict[str, list[str]] = defaultdict(list)
    for r in db.query("SELECT src, dst FROM links WHERE project_id=? AND rel='drug-trial'", (pid,)):
        if r["src"] in names:
            out[r["dst"]].append(names[r["src"]])
    return out


def _coverage(db: DB, pid: str) -> dict[str, Any]:
    run = db.one("SELECT id FROM runs WHERE project_id=? ORDER BY created_at DESC LIMIT 1", (pid,))
    if not run:
        return {"regions": {}, "routes": []}
    rows = db.query("SELECT route_id, region, status, COUNT(*) n, SUM(hits) hits, SUM(new_entities) new "
                    "FROM coverage WHERE run_id=? GROUP BY route_id, region, status ORDER BY region, route_id",
                    (run["id"],))
    regions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        regions[r["region"]][r["status"]] += r["n"]
    return {"regions": {k: dict(v) for k, v in regions.items()}, "routes": rows}


def data_a(db: DB, pid: str) -> dict[str, Any]:
    drugs = db.entities(pid, "drug")
    tmap = _trial_drugs(db, pid)
    trials = {t["id"]: t for t in db.entities(pid, "trial")}
    per_drug: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tid, dnames in tmap.items():
        for n in dnames:
            if tid in trials:
                per_drug[n].append(trials[tid])
    rows = []
    for d in drugs:
        a = d["attrs"]
        ts = per_drug.get(d["name"], [])
        rows.append({
            "name": d["name"], "name_zh": d["name_zh"], "targets": a.get("targets", []),
            "modality": a.get("modality"), "companies": a.get("companies", []), "china_mah": a.get("china_mah"),
            "phase_global": a.get("highest_phase_global", "unknown"),
            "phase_china": a.get("highest_phase_china", "unknown"), "innovative": a.get("innovative"),
            "n_trials": len(ts), "n_china_trials": sum(1 for t in ts if t["attrs"].get("china_site")),
            "found_by": d["found_by"], "in_scope": d["in_scope"], "scope_reason": d["scope_reason"],
            "evidence_urls": a.get("evidence_urls", []),
        })
    included = [r for r in rows if r["in_scope"] != 0]
    targets = sorted({t for r in included for t in (r["targets"] or ["未知靶点"])})
    phases = [p for p in PHASE_ORDER if any(r["phase_global"] == p or r["phase_china"] == p for r in included)]
    heat = []
    for r in included:
        for t in r["targets"] or ["未知靶点"]:
            if r["phase_global"] in phases:
                heat.append([phases.index(r["phase_global"]), targets.index(t)])
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for x, y in heat:
        counts[(x, y)] += 1
    bar_g = [sum(1 for r in included if r["phase_global"] == p) for p in phases]
    bar_c = [sum(1 for r in included if r["phase_china"] == p) for p in phases]
    charts = {
        "heat": {"x": [PHASE_ZH[p] for p in phases], "y": targets,
                 "data": [[x, y, n] for (x, y), n in counts.items()]},
        "phase_bar": {"x": [PHASE_ZH[p] for p in phases], "series": [
            {"name": "全球最高阶段", "data": bar_g}, {"name": "中国最高阶段", "data": bar_c}]},
    }
    return {"rows": sorted(included, key=lambda r: PHASE_ORDER.index(r["phase_china"]))
            , "excluded": [r for r in rows if r["in_scope"] == 0], "charts": charts}


def _result_rows(db: DB, pid: str) -> list[dict[str, Any]]:
    tmap = _trial_drugs(db, pid)
    ents = {e["id"]: e for e in db.query("SELECT id, name, type FROM entities WHERE project_id=?", (pid,))}
    srcs = {s["id"]: s["url"] for s in db.query("SELECT id, url FROM sources WHERE project_id=?", (pid,))}
    rows = []
    for f in db.current_facts(pid):
        if not f["field"].startswith(("result.", "safety.")):
            continue
        e = ents.get(f["entity_id"], {})
        c = f["context"]
        rows.append({
            "id": f["id"], "field": f["field"], "entity": e.get("name"),
            "drugs": tmap.get(f["entity_id"], [e.get("name")] if e.get("type") == "drug" else []),
            "endpoint": c.get("endpoint") or c.get("term") or f["field"], "endpoint_key": c.get("endpoint_key"),
            "timepoint": c.get("timepoint"), "arm": c.get("arm"), "value": f["value"], "unit": c.get("unit"),
            "stat_type": c.get("stat_type"), "denominator": c.get("denominator"),
            "proportion": c.get("proportion"), "population": c.get("population"),
            "status": f["status"], "tier": f["tier"], "extracted_by": f["extracted_by"],
            "source_url": c.get("source_url") or srcs.get(f["source_id"] or ""), "quote": f["quote"],
            "verify_note": c.get("verify_note"),
        })
    return rows


def _norm(s: str | None) -> str:
    import re
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (s or "").lower())


def _arm_drug(db: DB, pid: str) -> Any:
    """组别 → 药物：只有组名里出现药物名/别名才归属该药，其余（安慰剂、对照药）不冒用试验药名。"""
    keys = [(_norm(k), d["name"]) for d in db.entities(pid, "drug") for k in [d["name"], *d["aliases"]]
            if len(_norm(k)) >= 4]
    return lambda arm: next((name for k, name in keys if k in _norm(arm)), None)


def data_b(db: DB, pid: str) -> dict[str, Any]:
    rows = _result_rows(db, pid)
    arm_drug = _arm_drug(db, pid)
    for r in rows:
        r["arm_drug"] = arm_drug(r["arm"]) if r["arm"] else None
    results = [r for r in rows if r["field"].startswith("result.") and not r["field"].endswith(".analysis")]
    analyses = [r for r in rows if r["field"].endswith(".analysis")]
    safety = [r for r in rows if r["field"] in ("safety.sae.any", "safety.death.all_cause")]
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in results:
        if r["status"] != "verified" or not isinstance(r["value"], (int, float)):
            continue
        tp = parse_timepoint(r["timepoint"] or "")
        key = (r["endpoint_key"] or r["endpoint"], tp.days if tp.days is not None else (tp.months, "m"),
               r["stat_type"], (r["unit"] or "").lower())
        groups[key].append(r)
    charts = []
    for key, items in sorted(groups.items(), key=lambda kv: (-len({i["entity"] for i in kv[1]}),
                                                               not kv[1][0]["field"].startswith("result.primary")))[:12]:
        charts.append({
            "title": items[0]["endpoint"][:90], "subtitle": f"{items[0]['timepoint'] or '时间点未报告'} · "
                                                            f"{items[0]['unit'] or items[0]['stat_type'] or ''}",
            "labels": [" · ".join(x for x in (i["arm_drug"], i["entity"], i["arm"] or "组别未报告") if x)
                       for i in items],
            "primary": items[0]["field"].startswith("result.primary"),
            "values": [i["value"] for i in items], "trials": len({i["entity"] for i in items})})
    unverified_critical = sum(1 for r in rows if r["tier"] == "critical" and r["status"] != "verified")
    return {"results": results, "analyses": analyses, "safety": safety, "charts": {"groups": charts},
            "unverified_critical": unverified_critical}


def data_c(db: DB, pid: str) -> dict[str, Any]:
    from ciw2.render.design import design_data
    return design_data(db, pid, PHASE_ZH)


BUILDERS = {"A": data_a, "B": data_b, "C": data_c}


def report_data(db: DB, pid: str, report: str) -> dict[str, Any]:
    return BUILDERS[report](db, pid)


def render_report(db: DB, pid: str, report: str, *, findings: dict[str, Any] | None = None,
                  static_prefix: str = "/static", inline: bool = False) -> str:
    project = db.project(pid)
    if project is None:
        raise KeyError(pid)
    data = report_data(db, pid, report)
    has_data = any(data.get(key) for key in ('rows', 'results', 'safety', 'analyses'))
    verified_ids = {fact['id'] for fact in db.current_facts(pid) if fact['status'] == 'verified'}
    summaries = [finding for finding in (findings or {}).get('findings', [])
                 if has_data and finding.get('fact_refs') and set(finding['fact_refs']) <= verified_ids]
    assets = None
    if inline:
        assets = {"css": (STATIC / "kangzhe.css").read_text(encoding="utf-8"),
                  "js": (STATIC / "portal.js").read_text(encoding="utf-8"),
                  "echarts": (STATIC / "echarts.min.js").read_text(encoding="utf-8")
                  if (STATIC / "echarts.min.js").exists() else ""}
    tpl = _env.get_template(f"{report.lower()}.html")
    return tpl.render(project=project, report=report, report_title=REPORT_ZH[report], data=data,
                      findings=summaries, coverage=_coverage(db, pid),
                      charts_json=data.get("charts", {}),
                      static=static_prefix, assets=assets, reports=project["reports"], phase_zh=PHASE_ZH)
