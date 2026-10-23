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

from ciw2.domain.availability import require_supported_cutoff
from ciw2.domain.outcomes import DOMAIN_LABELS, classify_outcome_domain
from ciw2.render.labels import PHASE_ZH, age_label, phase_label, registry_label
from ciw2.render.result_identity import bind_result_drugs
from ciw2.render.results import result_groups
from ciw2.render.trial_identity import trial_identities, verified_holders
from ciw2.store.db import DB

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
PHASE_ORDER = ["preclinical", "phase1", "phase1_2", "phase2", "phase2_3", "phase3", "nda_bla", "approved",
               "phase4", "unknown"]
STATUS_ZH = {"verified": "已核实", "unverified": "未核实", "conflict": "冲突", "unknown": "未报告"}
REPORT_ZH = {"A": "A · 竞争格局", "B": "B · 疗效与安全性", "C": "C · 试验设计先例"}

_env = Environment(loader=FileSystemLoader(str(HERE / "templates")), autoescape=select_autoescape(["html"]))
_env.filters["phase"] = phase_label
_env.filters["status"] = lambda s: STATUS_ZH.get(s, s)
_env.filters['registry_label'] = registry_label
_env.filters['age_label'] = age_label


def _trial_drugs(db: DB, pid: str) -> dict[str, list[str]]:
    names = {e["id"]: e["name"] for e in db.entities(pid, "drug")}
    out: dict[str, list[str]] = defaultdict(list)
    for r in db.query("SELECT src, dst FROM links WHERE project_id=? AND rel='drug-trial'", (pid,)):
        if r["src"] in names:
            out[r["dst"]].append(names[r["src"]])
    return out


def data_a(db: DB, pid: str) -> dict[str, Any]:
    drugs = db.entities(pid, "drug")
    identities = trial_identities(db, pid)
    holder_map = verified_holders(db.current_facts(pid), {s['id']: s for s in db.query(
        'SELECT id,url FROM sources WHERE project_id=?', (pid,))})
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
            "id": d['id'], "name": d["name"], "name_zh": d["name_zh"], "targets": a.get("targets", []),
            "modality": a.get("modality"), "companies": a.get("companies", []),
            "china_mah": ' / '.join(dict.fromkeys(c['name'] for c in holder_map[d['id']])),
            'mah_refs': holder_map[d['id']],
            "phase_global": a.get("highest_phase_global", "unknown"),
            "phase_china": a.get("highest_phase_china", "unknown"), "innovative": a.get("innovative"),
            "n_trials": len(ts), "n_china_trials": sum(1 for t in ts if t["attrs"].get("china_site")),
            "found_by": d["found_by"], "in_scope": d["in_scope"], "scope_reason": d["scope_reason"],
            "evidence_urls": a.get("evidence_urls", []),
            "trials": [identities[t['id']] for t in ts if t['id'] in identities],
        })
    included = [r for r in rows if r["in_scope"] != 0]
    charts = {'landscape': {
        'rows': [{key: r[key] for key in ('id', 'targets', 'phase_global', 'phase_china')} for r in included],
        'phase_labels': {p: PHASE_ZH[p] for p in PHASE_ORDER if p != 'unknown'},
    }}
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
            "entity_id": f["entity_id"], "entity_type": e.get("type"), "source_id": f["source_id"],
            "source_snapshot": c.get("source_snapshot"),
            "drugs": tmap.get(f["entity_id"], [e.get("name")] if e.get("type") == "drug" else []),
            "endpoint": c.get("endpoint") or c.get("term") or f["field"], "endpoint_key": c.get("endpoint_key"),
            "timepoint": c.get("timepoint"), "arm": c.get("arm"), "value": f["value"], "unit": c.get("unit"),
            "stat_type": c.get("stat_type"), "denominator": c.get("denominator"),
            "proportion": c.get("proportion"), "population": c.get("population"),
            "status": f["status"], "tier": f["tier"], "extracted_by": f["extracted_by"],
            "source_url": c.get("source_url") or srcs.get(f["source_id"] or ""), "quote": f["quote"],
            "verify_note": c.get("verify_note"),
            **{key: c.get(key) for key in ('class_title', 'category', 'param_type', 'dispersion_type',
                                          'group_id', 'raw_value', 'spread', 'lower', 'upper', 'json_path')},
        })
    return rows


def data_b(db: DB, pid: str) -> dict[str, Any]:
    rows = _result_rows(db, pid)
    bind_result_drugs(db, pid, rows)
    identities = trial_identities(db, pid)
    drug_names = {d['name']: d['name_zh'] or d['name'] for d in db.entities(pid, 'drug')}
    for row in rows:
        row['identity'] = identities.get(row['entity_id'])
        row['display_drugs'] = [drug_names.get(name, name) for name in row['drugs']]
        row['arm_drug_label'] = ' / '.join(drug_names.get(name, name) + (f'（{name}）' if drug_names.get(name, name) != name else '')
                                         for name in row['drugs'])
        row['domain'] = ('safety' if row['field'].startswith('safety.') else
                         classify_outcome_domain(row['endpoint'], drug_names=row['drugs']))
    results = [r for r in rows if r["field"].startswith("result.") and not r["field"].endswith(".analysis")]
    analyses = [r for r in rows if r["field"].endswith(".analysis")]
    safety = [r for r in rows if r["field"] in ("safety.sae.any", "safety.death.all_cause")]
    charts, exclusions = result_groups(results)
    counts = {label: sum(r['domain'] == label for r in results) for label in DOMAIN_LABELS}
    counts = {label: count for label, count in counts.items() if count}
    unverified_critical = sum(1 for r in rows if r["tier"] == "critical" and r["status"] != "verified")
    return {"results": results, "analyses": analyses, "safety": safety, "charts": {"groups": charts},
            "unverified_critical": unverified_critical, "plot_exclusions": exclusions,
            'domain_counts': counts, 'domain_labels': DOMAIN_LABELS,
            'default_domain': 'clinical' if counts.get('clinical') else 'all'}


def data_c(db: DB, pid: str) -> dict[str, Any]:
    from ciw2.render.design import design_data
    return design_data(db, pid, PHASE_ZH)


BUILDERS = {"A": data_a, "B": data_b, "C": data_c}


def report_data(db: DB, pid: str, report: str) -> dict[str, Any]:
    project = db.project(pid)
    if project is None:
        raise KeyError(pid)
    require_supported_cutoff(project['cutoff_date'])
    return BUILDERS[report](db, pid)


def render_report(db: DB, pid: str, report: str, *, findings: dict[str, Any] | None = None,
                  static_prefix: str = "/static", inline: bool = False) -> str:
    project = db.project(pid)
    if project is None:
        raise KeyError(pid)
    data = report_data(db, pid, report)
    has_data = any(data.get(key) for key in ('rows', 'results', 'safety', 'analyses'))
    verified = {fact['id']: fact for fact in db.current_facts(pid) if fact['status'] == 'verified'}
    identities = trial_identities(db, pid)
    summaries = []
    for finding in (findings or {}).get('findings', []):
        if has_data and finding.get('fact_refs') and set(finding['fact_refs']) <= verified.keys():
            tids = dict.fromkeys(verified[fid]['entity_id'] for fid in finding['fact_refs'])
            summaries.append({**finding, 'trial_context': [identities[tid] for tid in tids if tid in identities]})
    assets = None
    if inline:
        assets = {"css": (STATIC / "kangzhe.css").read_text(encoding="utf-8"),
                  "js": (STATIC / "portal.js").read_text(encoding="utf-8"),
                  "echarts": (STATIC / "echarts.min.js").read_text(encoding="utf-8")
                  if (STATIC / "echarts.min.js").exists() else ""}
    tpl = _env.get_template(f"{report.lower()}.html")
    return tpl.render(project=project, report=report, report_title=REPORT_ZH[report], data=data,
                      findings=summaries,
                      charts_json=data.get("charts", {}),
                      static=static_prefix, assets=assets, reports=project["reports"], phase_zh=PHASE_ZH)
