"""阶段定义。确定性工作（抓取、解析、核验、渲染）用代码；判断类工作交给 Skill。

DAG（按报告类型裁剪）：
intake → universe_china → universe_global → coverage_review(scope) → trial_evidence(code)
       → extract_results(B) → extract_design(C) → verify(code) → analysis_A/B/C → render(code)
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ciw2.domain.models import AnalysisResult, ExtractionResult, IntakeResult, ScopeResult, UniverseResult
from ciw2.domain.tiers import tier_of
from ciw2.pipeline.context import RunContext
from ciw2.sources import ctgov
from ciw2.sources.http import source_by_url, source_text
from ciw2.verify.quote import check_quote


@dataclass(frozen=True)
class Stage:
    name: str
    fn: Callable[[RunContext], dict[str, Any]]
    reports: frozenset[str] = frozenset({"A", "B", "C"})  # 哪些报告需要本阶段
    blocking: bool = True    # 失败是否终止运行（非阻断阶段失败会记录并继续）


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (s or "").lower())


# ------------------------------------------------------------------ intake
def intake(rc: RunContext) -> dict[str, Any]:
    p = rc.project
    res: IntakeResult = rc.skill("intake", {
        "request_text": p["request_text"], "indication": p["indication"], "reports": p["reports"],
        "focus": p["focus"], "cutoff_date": p["cutoff_date"]})
    aliases = sorted(set(p["indication_aliases"]) | set(res.aliases) | {res.indication_en})
    rc.db.execute("UPDATE projects SET indication_aliases=?, focus=? WHERE id=?",
                  (json.dumps(aliases, ensure_ascii=False), p["focus"] or res.focus, rc.project_id))
    return res.model_dump()


def _intake(rc: RunContext) -> dict[str, Any]:
    return rc.db.stage_output(rc.run_id, "intake") or {"indication": rc.project["indication"],
                                                       "indication_en": "", "aliases": []}


# ------------------------------------------------------------------ universe
def _persist_universe(rc: RunContext, res: UniverseResult) -> int:
    new = 0
    for c in res.candidates:
        attrs = {k: v for k, v in c.model_dump().items()
                 if k not in {"name", "name_zh", "aliases", "route_id"} and v not in (None, [], "unknown")}
        attrs[f"found_in_{res.region}"] = True
        eid, is_new = rc.db.upsert_entity(rc.project_id, "drug", c.name, name_zh=c.name_zh,
                                          aliases=c.aliases, attrs=attrs, route_id=c.route_id)
        new += int(is_new)
        for comp in c.companies:
            cid, _ = rc.db.upsert_entity(rc.project_id, "company", comp, route_id=c.route_id)
            rc.db.link(rc.project_id, eid, "drug-company", cid)
        for t in c.targets:
            tid, _ = rc.db.upsert_entity(rc.project_id, "target", t, route_id=c.route_id)
            rc.db.link(rc.project_id, eid, "drug-target", tid)
        # 中国状态/MAH 属于 critical：只有给出证据 URL 时才写入事实（核验阶段再查原文）
        if c.highest_phase_china != "unknown":
            rc.db.add_fact({"project_id": rc.project_id, "entity_id": eid, "field": "status.china.highest_phase",
                            "value": c.highest_phase_china, "tier": tier_of("status.china"),
                            "status": "unverified", "context": {"evidence_urls": c.evidence_urls},
                            "extracted_by": f"llm:{getattr(rc.llm, 'model', 'llm')}"})
    return new


def _universe(region: str) -> Callable[[RunContext], dict[str, Any]]:
    def run(rc: RunContext) -> dict[str, Any]:
        it = _intake(rc)
        known = [e["name"] for e in rc.db.entities(rc.project_id, "drug")]
        res: UniverseResult = rc.skill(f"universe-{region}", {
            "indication": it["indication"], "indication_en": it.get("indication_en"),
            "aliases": it.get("aliases", []), "focus": rc.project["focus"], "already_known": known})
        if res.region != region:
            res = res.model_copy(update={"region": region})
        new = _persist_universe(rc, res)
        return {"candidates": len(res.candidates), "new": new, "routes_run": res.routes_run,
                "routes_failed": res.routes_failed, "notes": res.notes}
    return run


# ------------------------------------------------------------------ scope / coverage review
def coverage_review(rc: RunContext) -> dict[str, Any]:
    drugs = rc.db.entities(rc.project_id, "drug")
    cov = rc.db.query("SELECT route_id, region, status, SUM(hits) hits, COUNT(*) n FROM coverage "
                      "WHERE run_id=? GROUP BY route_id, region, status", (rc.run_id,))
    res: ScopeResult = rc.skill("coverage-review", {
        "indication": _intake(rc)["indication"], "focus": rc.project["focus"],
        "candidates": [{"name": d["name"], "name_zh": d["name_zh"], "aliases": d["aliases"],
                        "attrs": d["attrs"], "found_by": d["found_by"]} for d in drugs],
        "coverage": cov})
    by_name = {_norm(d["name"]): d for d in drugs}
    for d in drugs:
        for a in d["aliases"]:
            by_name.setdefault(_norm(a), d)
    applied = 0
    for dec in res.decisions:
        d = by_name.get(_norm(dec.drug))
        if d:
            rc.db.set_scope(d["id"], dec.in_scope, dec.reason)
            applied += 1
    return {"decisions": applied, "in_scope": sum(1 for x in res.decisions if x.in_scope),
            "excluded": sum(1 for x in res.decisions if x.in_scope is False),
            "pending": sum(1 for x in res.decisions if x.in_scope is None)}


def scoped_drugs(rc: RunContext) -> list[dict[str, Any]]:
    """纳入 + 待定（待定在平台上标注，不静默丢弃）。"""
    return [d for d in rc.db.entities(rc.project_id, "drug") if d["in_scope"] != 0]


# ------------------------------------------------------------------ trial evidence (code)
def _matches(drug: dict[str, Any], interventions: list[dict[str, Any]]) -> bool:
    keys = {_norm(x) for x in [drug["name"], *drug["aliases"]] if len(_norm(x)) >= 4}
    for iv in interventions:
        names = [iv.get("name"), *(iv.get("other_names") or [])]
        if any(k in _norm(n) for n in names for k in keys):
            return True
    return False


def trial_evidence(rc: RunContext) -> dict[str, Any]:
    it = _intake(rc)
    ctx = rc.tool_ctx()
    cond = it.get("indication_en") or rc.project["indication"]
    max_trials = int(rc.cache.get("max_trials_per_drug", 15))
    linked, ingested, errors = 0, 0, []
    for d in scoped_drugs(rc):
        try:
            rows = ctgov.search(ctx, condition=cond, intervention=d["name"], max_results=50)
            rc.db.log_coverage(rc.run_id, "trial:ctgov:intervention", "global", f"{cond} × {d['name']}",
                               "ok", hits=len(rows))
        except Exception as exc:  # noqa: BLE001 - 独立来源边界记录失败并继续其他路线
            rc.db.log_coverage(rc.run_id, "trial:ctgov:intervention", "global", f"{cond} × {d['name']}",
                               "failed", note=str(exc)[:300])
            errors.append(f"{d['name']}: {exc}")
            continue
        known = {t["name"]: t for t in rc.db.entities(rc.project_id, "trial")}
        candidates = {r["nct"]: r for r in rows}
        for t in known.values():
            candidates.setdefault(t["name"], {"nct": t["name"], **t["attrs"]})
        hits = [r for r in candidates.values() if _matches(d, r.get("interventions") or [])]
        hits.sort(key=lambda r: (r.get("phase") or "", r.get("start_date") or ""), reverse=True)
        for r in hits[:max_trials]:
            try:
                info = ctgov.ingest_trial(ctx, r["nct"], route_id="trial:ctgov:intervention")
            except Exception as exc:  # noqa: BLE001 - 单个试验失败不丢其他试验
                errors.append(f"{r['nct']}: {exc}")
                continue
            rc.db.link(rc.project_id, d["id"], "drug-trial", info["entity_id"])
            linked += 1
            ingested += int(info["facts_added"] > 0)
    return {"linked": linked, "ingested": ingested, "errors": errors}


def drug_trials(rc: RunContext, drug_id: str) -> list[dict[str, Any]]:
    ids = {r["dst"] for r in rc.db.query(
        "SELECT dst FROM links WHERE project_id=? AND src=? AND rel='drug-trial'", (rc.project_id, drug_id))}
    return [t for t in rc.db.entities(rc.project_id, "trial") if t["id"] in ids]


# ------------------------------------------------------------------ LLM extraction
def _extract(skill: str, extra: Callable[[RunContext, dict[str, Any]], dict[str, Any]]) -> Callable[
        [RunContext], dict[str, Any]]:
    def run(rc: RunContext) -> dict[str, Any]:
        it = _intake(rc)
        facts, gaps, errors = [], [], []
        limit = int(rc.cache.get("max_drugs", 30))
        for d in scoped_drugs(rc)[:limit]:
            trials = drug_trials(rc, d["id"])
            task = {"indication": it["indication"], "indication_en": it.get("indication_en"),
                    "focus": rc.project["focus"],
                    "drug": {"name": d["name"], "name_zh": d["name_zh"], "aliases": d["aliases"]},
                    "known_trials": [{"nct": t["name"], "title": t["attrs"].get("title"),
                                      "phase": t["attrs"].get("phase"),
                                      "has_results": t["attrs"].get("has_results")} for t in trials],
                    **extra(rc, d)}
            try:
                res: ExtractionResult = rc.skill(skill, task)
            except Exception as exc:  # noqa: BLE001 - 保留单药错误供恢复
                errors.append(f"{d['name']}: {type(exc).__name__}: {exc}")
                continue
            facts += [{**f.model_dump(), "drug": d["name"]} for f in res.facts]
            gaps += [f"{d['name']}: {g}" for g in res.gaps]
        if errors and not facts:
            raise RuntimeError("全部药物抽取失败：" + "; ".join(errors[:5]))
        return {"facts": facts, "gaps": gaps, "errors": errors}
    return run


def _results_extra(rc: RunContext, d: dict[str, Any]) -> dict[str, Any]:
    have = {(f["entity_id"]) for f in rc.db.current_facts(rc.project_id) if f["field"].startswith("result.")}
    return {"trials_with_registry_results": [t["name"] for t in drug_trials(rc, d["id"]) if t["id"] in have]}


def _design_extra(rc: RunContext, d: dict[str, Any]) -> dict[str, Any]:
    with_design = {f["entity_id"] for f in rc.db.current_facts(rc.project_id)
                   if f["field"] == "design.sample_size" and f["extracted_by"] == "code:ctgov"}
    return {"trials_with_registry_design": [t["name"] for t in drug_trials(rc, d["id"]) if t["id"] in with_design]}


# ------------------------------------------------------------------ verify (code)
def _entity_for(rc: RunContext, name: str, drug: str) -> str:
    n = name.strip()
    if re.fullmatch(r"NCT\d{8}", n.upper()):
        return rc.db.upsert_entity(rc.project_id, "trial", n.upper(), route_id="extract")[0]
    if re.fullmatch(r"CTR\d{8}", n.upper()):
        return rc.db.upsert_entity(rc.project_id, "trial", n.upper(), attrs={"registry": "chinadrugtrials"},
                                   route_id="extract")[0]
    for d in rc.db.entities(rc.project_id, "drug"):
        if _norm(n) in {_norm(d["name"]), *map(_norm, d["aliases"])}:
            return d["id"]
    return rc.db.upsert_entity(rc.project_id, "drug", drug, route_id="extract")[0]


def cross_check(llm: Any, fact: dict[str, Any]) -> bool | None:
    """可选：第二个模型只回答「原文片段是否支持该值及其语义（组/时间点/人群/统计对象）」。"""
    from ciw2.harness.llm import LLMError
    prompt = ("只回答 YES 或 NO：下面的原文片段是否明确支持该事实（数值、组别、时间点、人群、统计对象全部一致）？\n"
              + json.dumps({k: fact.get(k) for k in ("field", "value", "unit", "stat_type", "arm", "timepoint",
                                                      "population", "denominator", "quote")}, ensure_ascii=False))
    try:
        reply = llm.chat([{"role": "user", "content": prompt}])
    except LLMError:
        return None
    text = (reply.content or "").strip().upper()
    return True if text.startswith("YES") else False if text.startswith("NO") else None


def verify(rc: RunContext) -> dict[str, Any]:
    ctx = rc.tool_ctx()
    model = getattr(rc.llm, "model", "llm")
    stats = {"verified": 0, "unverified": 0, "conflict": 0, "unknown": 0}
    reasons: dict[str, int] = {}
    for stage in ("extract_results", "extract_design"):
        out = rc.db.stage_output(rc.run_id, stage) or {}
        for f in out.get("facts", []):
            tier = tier_of(f["field"])
            src = source_by_url(ctx, f["source_url"])
            status, start, end, reason = "unverified", None, None, ""
            if f.get("value") is None:
                status, reason = "unknown", "来源未给出"
            elif src is None:
                reason = "来源未在本项目中读取，无法核验"
            else:
                text = source_text(ctx, src["id"]) or ""
                chk = check_quote(text, f.get("quote"), f.get("value"))
                start, end, reason = chk.start, chk.end, chk.reason
                status = "verified" if chk.ok else "unverified"
                if chk.ok and tier == "critical" and rc.check_llm is not None:
                    agree = cross_check(rc.check_llm, f)
                    if agree is False:
                        status, reason = "conflict", "二次核对模型不同意"
            stats[status] += 1
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
            ctxt = {k: f.get(k) for k in ("endpoint", "unit", "stat_type", "arm", "timepoint", "population", "denominator")
                    if f.get(k) is not None}
            if f["field"].startswith("result."):
                ctxt["endpoint_key"] = ctgov.endpoint_key(ctxt.get("endpoint") or f["field"])
            rc.db.add_fact({"project_id": rc.project_id, "entity_id": _entity_for(rc, f["entity"], f["drug"]),
                            "field": f["field"], "value": f["value"], "tier": tier, "status": status,
                            "source_id": src["id"] if src else None, "quote": f.get("quote"),
                            "quote_start": start, "quote_end": end,
                            "context": {**ctxt, "source_url": f["source_url"], "verify_note": reason},
                            "extracted_by": f"llm:{model}"})
    return {"stats": stats, "reasons": reasons}


# ------------------------------------------------------------------ analysis + render
def _analysis(report: str) -> Callable[[RunContext], dict[str, Any]]:
    def run(rc: RunContext) -> dict[str, Any]:
        from ciw2.render.portal import report_data
        data = report_data(rc.db, rc.project_id, report)
        res: AnalysisResult = rc.skill(f"analysis-{report.lower()}", {
            "indication": _intake(rc)["indication"], "focus": rc.project["focus"],
            "data": _compact(data)})
        return res.model_dump()
    return run


def _compact(data: dict[str, Any], limit: int = 60000) -> dict[str, Any]:
    """给分析 Skill 的数据：去掉图表配置，限制体积。"""
    slim = {k: v for k, v in data.items() if k not in {"charts"}}
    text = json.dumps(slim, ensure_ascii=False, default=str)
    if len(text) > limit:
        slim = {**slim, "_truncated": True}
        for k in ("rows", "safety", "results"):
            if isinstance(slim.get(k), list):
                slim[k] = slim[k][:150]
    return slim


def render(rc: RunContext) -> dict[str, Any]:
    from ciw2.render.portal import render_report
    out_dir = rc.settings.portals_dir / rc.project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for rep in rc.project["reports"]:
        findings = rc.db.stage_output(rc.run_id, f"analysis_{rep}")
        html = render_report(rc.db, rc.project_id, rep, findings=findings, inline=True)
        path = out_dir / f"{rep}.html"
        path.write_text(html, encoding="utf-8")
        written.append(str(path.name))
    return {"files": written}


STAGES: list[Stage] = [
    Stage("intake", intake),
    Stage("universe_china", _universe("china"), blocking=False),
    Stage("universe_global", _universe("global"), blocking=False),
    Stage("coverage_review", coverage_review),
    Stage("trial_evidence", trial_evidence),
    Stage("extract_results", _extract("extract-results", _results_extra), frozenset({"B"}), blocking=False),
    Stage("extract_design", _extract("extract-design", _design_extra), frozenset({"C"}), blocking=False),
    Stage("verify", verify, frozenset({"B", "C"})),
    Stage("analysis_A", _analysis("A"), frozenset({"A"}), blocking=False),
    Stage("analysis_B", _analysis("B"), frozenset({"B"}), blocking=False),
    Stage("analysis_C", _analysis("C"), frozenset({"C"}), blocking=False),
    Stage("render", render),
]
