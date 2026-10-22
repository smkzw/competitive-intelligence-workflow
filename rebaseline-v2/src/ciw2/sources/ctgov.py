"""ClinicalTrials.gov v2：确定性解析（设计、结果、不良事件），不经 LLM。
从 v1 connectors/clinicaltrials_gov.py + ctgov_fetch.py 的经验移植，但只保留 v2 JSON API 路径。
关键规则：
- 组/臂原名原样保存（CT.gov 组标题常含期别，如 "Initial Treatment Period (...): Placebo"），不改写。
- numAffected 缺失 → value=None, status=unknown（不补 0）。
- 受试者比例只在 count_participants + 同组 numAtRisk 时派生。
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from ciw2.domain.semantics import derive_proportion, parse_number
from ciw2.domain.tiers import tier_of
from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import fetch

API = "https://clinicaltrials.gov/api/v2/studies"
STUDY_URL = "https://clinicaltrials.gov/study/{nct}"
NCT_RE = re.compile(r"^NCT\d{8}$")

_PHASE = {
    ("EARLY_PHASE1",): "phase1", ("PHASE1",): "phase1", ("PHASE1", "PHASE2"): "phase1_2",
    ("PHASE2",): "phase2", ("PHASE2", "PHASE3"): "phase2_3", ("PHASE3",): "phase3",
    ("PHASE4",): "phase4",
}


def map_phase(phases: list[str] | None) -> str:
    return _PHASE.get(tuple(sorted(phases or [])), "unknown")


def _g(d: Any, *path: str, default: Any = None) -> Any:
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
    return default if d is None else d


# ------------------------------------------------------------------ 解析
def parse_study(study: dict[str, Any]) -> dict[str, Any]:
    ps = study.get("protocolSection", {})
    ident, status = ps.get("identificationModule", {}), ps.get("statusModule", {})
    design, arms_mod = ps.get("designModule", {}), ps.get("armsInterventionsModule", {})
    locs = _g(ps, "contactsLocationsModule", "locations", default=[])
    countries = sorted({loc.get("country") for loc in locs if loc.get("country")})
    elig = ps.get("eligibilityModule", {})
    return {
        "nct": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "acronym": ident.get("acronym"),
        "sponsor": _g(ps, "sponsorCollaboratorsModule", "leadSponsor", "name"),
        "collaborators": [c.get("name") for c in _g(ps, "sponsorCollaboratorsModule", "collaborators", default=[])],
        "overall_status": status.get("overallStatus"),
        "start_date": _g(status, "startDateStruct", "date"),
        "primary_completion_date": _g(status, "primaryCompletionDateStruct", "date"),
        "phases": design.get("phases") or [],
        "phase": map_phase(design.get("phases")),
        "study_type": design.get("studyType"),
        "allocation": _g(design, "designInfo", "allocation"),
        "masking": _g(design, "designInfo", "maskingInfo", "masking"),
        "enrollment": _g(design, "enrollmentInfo", "count"),
        "enrollment_type": _g(design, "enrollmentInfo", "type"),
        "conditions": _g(ps, "conditionsModule", "conditions", default=[]),
        "interventions": [
            {"type": i.get("type"), "name": i.get("name"), "other_names": i.get("otherNames") or []}
            for i in arms_mod.get("interventions", [])
        ],
        "arms": [
            {"label": a.get("label"), "type": a.get("type"), "description": a.get("description"),
             "interventions": a.get("interventionNames") or []}
            for a in arms_mod.get("armGroups", [])
        ],
        "countries": countries,
        "china_site": any(c in {"China", "Hong Kong", "Taiwan", "Macao", "Macau"} for c in countries),
        "primary_outcomes": _g(ps, "outcomesModule", "primaryOutcomes", default=[]),
        "secondary_outcomes": _g(ps, "outcomesModule", "secondaryOutcomes", default=[]),
        "eligibility": {"min_age": elig.get("minimumAge"), "max_age": elig.get("maximumAge"),
                        "sex": elig.get("sex"), "criteria": elig.get("eligibilityCriteria")},
        "has_results": bool(study.get("hasResults")),
    }


def _fact(field: str, value: Any, *, quote: str | None = None, path: str = "", **context: Any) -> dict[str, Any]:
    status = "unknown" if value is None else "verified"
    return {"field": field, "value": value, "tier": tier_of(field), "status": status,
            "quote": quote, "context": {"json_path": path, **{k: v for k, v in context.items() if v is not None}},
            "extracted_by": "code:ctgov"}


def design_facts(s: dict[str, Any]) -> list[dict[str, Any]]:
    out = [
        _fact("design.sample_size", s["enrollment"], quote=None if s["enrollment"] is None else str(s["enrollment"]),
              path="designModule.enrollmentInfo.count", enrollment_type=s["enrollment_type"]),
        _fact("design.phase", s["phase"], path="designModule.phases", raw=s["phases"]),
        _fact("design.allocation", s["allocation"], path="designModule.designInfo.allocation"),
        _fact("design.masking", s["masking"], path="designModule.designInfo.maskingInfo.masking"),
        _fact("design.arms", s["arms"], path="armsInterventionsModule.armGroups"),
        _fact("design.eligibility.age", {"min": s["eligibility"]["min_age"], "max": s["eligibility"]["max_age"]},
              path="eligibilityModule"),
        _fact("design.eligibility.criteria", s["eligibility"]["criteria"],
              quote=s["eligibility"]["criteria"], path="eligibilityModule.eligibilityCriteria"),
        _fact("status.trial", s["overall_status"], path="statusModule.overallStatus"),
        _fact("trial.countries", s["countries"], path="contactsLocationsModule.locations[].country"),
        _fact("trial.china_site", s["china_site"], path="contactsLocationsModule.locations[].country"),
        _fact("trial.start_date", s["start_date"], path="statusModule.startDateStruct.date"),
    ]
    for i, o in enumerate(s["primary_outcomes"]):
        out.append(_fact("design.primary_endpoint", {"measure": o.get("measure"), "time_frame": o.get("timeFrame"),
                                                     "description": o.get("description")},
                         quote=o.get("measure"), path=f"outcomesModule.primaryOutcomes[{i}]",
                         timepoint=o.get("timeFrame")))
    for i, o in enumerate(s["secondary_outcomes"]):
        out.append(_fact("design.secondary_endpoint", {"measure": o.get("measure"), "time_frame": o.get("timeFrame")},
                         quote=o.get("measure"), path=f"outcomesModule.secondaryOutcomes[{i}]",
                         timepoint=o.get("timeFrame")))
    return out


def stat_type_of(param_type: str | None, unit: str | None) -> str:
    u = (unit or "").lower()
    p = (param_type or "").upper()
    if "percent" in u and "participant" in u or u.strip() in {"%", "percentage"}:
        return "proportion"
    return {
        "COUNT_OF_PARTICIPANTS": "count_participants", "COUNT_OF_UNITS": "count_events",
        "MEAN": "mean", "MEDIAN": "median", "LEAST_SQUARES_MEAN": "ls_mean",
        "GEOMETRIC_MEAN": "mean", "NUMBER": "number",
    }.get(p, "number")


def endpoint_key(title: str | None) -> str:
    return re.sub(r"[^a-z0-9>=<%]+", " ", (title or "").lower()).strip()


def result_facts(study: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    oms = _g(study, "resultsSection", "outcomeMeasuresModule", "outcomeMeasures", default=[])
    for mi, om in enumerate(oms):
        kind = {"PRIMARY": "result.primary", "SECONDARY": "result.secondary"}.get(om.get("type", ""),
                                                                                  "result.other")
        groups = {g["id"]: g.get("title") for g in om.get("groups", [])}
        denoms: dict[str, Any] = {}
        for d in om.get("denoms", []):
            if (d.get("units") or "").lower() == "participants":
                denoms = {c["groupId"]: parse_number(c.get("value")) for c in d.get("counts", [])}
        st = stat_type_of(om.get("paramType"), om.get("unitOfMeasure"))
        base = {"endpoint": om.get("title"), "endpoint_key": endpoint_key(om.get("title")),
                "timepoint": om.get("timeFrame"), "population": om.get("populationDescription"),
                "unit": om.get("unitOfMeasure"), "stat_type": st, "param_type": om.get("paramType"),
                "dispersion_type": om.get("dispersionType")}
        for ci, cls in enumerate(om.get("classes", [])):
            for ki, cat in enumerate(cls.get("categories", [])):
                for m in cat.get("measurements", []):
                    gid = m.get("groupId")
                    val = parse_number(m.get("value"))
                    out.append(_fact(
                        f"{kind}.value", val, quote=m.get("value"),
                        path=f"outcomeMeasures[{mi}].classes[{ci}].categories[{ki}]",
                        arm=groups.get(gid), group_id=gid, denominator=denoms.get(gid),
                        class_title=cls.get("title"), category=cat.get("title"),
                        spread=m.get("spread"), lower=m.get("lowerLimit"), upper=m.get("upperLimit"),
                        raw_value=m.get("value"), **base))
        for ai, an in enumerate(om.get("analyses", [])):
            out.append(_fact(
                f"{kind}.analysis", {k: an.get(k) for k in ("paramType", "paramValue", "ciPctValue",
                                                            "ciLowerLimit", "ciUpperLimit", "pValue",
                                                            "statisticalMethod")},
                quote=an.get("paramValue"), path=f"outcomeMeasures[{mi}].analyses[{ai}]",
                arms=[groups.get(g) for g in an.get("groupIds", [])], **base))
    return out


def ae_facts(study: dict[str, Any]) -> list[dict[str, Any]]:
    ae = _g(study, "resultsSection", "adverseEventsModule", default={})
    if not ae:
        return []
    out: list[dict[str, Any]] = []
    groups = {g["id"]: g for g in ae.get("eventGroups", [])}
    common = {"timepoint": ae.get("timeFrame"), "population": ae.get("description"),
              "stat_type": "count_participants"}
    for gid, g in groups.items():
        for field, key in (("safety.sae.any", "serious"), ("safety.death.all_cause", "deaths"),
                           ("safety.other_ae.above_threshold", "other")):
            n, d = g.get(f"{key}NumAffected"), g.get(f"{key}NumAtRisk")
            extra = {"threshold_pct": ae.get("frequencyThreshold")} if key == "other" else {}
            out.append(_fact(field, n, quote=None if n is None else str(n),
                             path=f"adverseEventsModule.eventGroups[{gid}].{key}NumAffected",
                             arm=g.get("title"), group_id=gid, denominator=d,
                             proportion=derive_proportion(n, d, "count_participants"), **common, **extra))
    for bucket, field in (("seriousEvents", "safety.sae.term"), ("otherEvents", "safety.ae.term")):
        for ei, ev in enumerate(ae.get(bucket, [])):
            for st in ev.get("stats", []):
                n, d = st.get("numAffected"), st.get("numAtRisk")
                out.append(_fact(field, n, quote=None if n is None else str(n),
                                 path=f"adverseEventsModule.{bucket}[{ei}]",
                                 term=ev.get("term"), organ_system=ev.get("organSystem"),
                                 arm=groups.get(st.get("groupId"), {}).get("title"),
                                 group_id=st.get("groupId"), denominator=d, num_events=st.get("numEvents"),
                                 proportion=derive_proportion(n, d, "count_participants"), **common))
    return out


def all_facts(study: dict[str, Any]) -> list[dict[str, Any]]:
    return design_facts(parse_study(study)) + result_facts(study) + ae_facts(study)


# ------------------------------------------------------------------ 抓取与入库
def get_study(ctx: ToolContext | None, nct: str) -> tuple[dict[str, Any], str | None]:
    if not NCT_RE.match(nct):
        raise ValueError(f"不是合法 NCT 号：{nct}")
    f = fetch(ctx, f"{API}/{nct}", kind="ctgov", title=nct)
    return f.json(), f.source_id


def ingest_trial(ctx: ToolContext, nct: str, route_id: str = "ctgov:get") -> dict[str, Any]:
    """抓取单个试验并写入实体 + 事实（代码抽取）。返回解析摘要。"""
    study, sid = get_study(ctx, nct)
    s = parse_study(study)
    eid, _ = ctx.db.upsert_entity(ctx.project_id, "trial", s["nct"], attrs=_trial_attrs(s), route_id=route_id)
    existing = {(f["field"], json.dumps(f["context"].get("json_path")), json.dumps(f["context"].get("group_id")))
                for f in ctx.db.current_facts(ctx.project_id, eid) if f["extracted_by"] == "code:ctgov"}
    n = 0
    for fact in all_facts(study):
        key = (fact["field"], json.dumps(fact["context"].get("json_path")),
               json.dumps(fact["context"].get("group_id")))
        if key in existing:
            continue
        ctx.db.add_fact({**fact, "project_id": ctx.project_id, "entity_id": eid, "source_id": sid})
        n += 1
    return {**_trial_attrs(s), "entity_id": eid, "facts_added": n}


def _trial_attrs(s: dict[str, Any]) -> dict[str, Any]:
    return {k: s[k] for k in ("title", "sponsor", "overall_status", "phase", "enrollment", "countries",
                              "china_site", "interventions", "conditions", "has_results", "start_date")} | {
        "url": STUDY_URL.format(nct=s["nct"]), "registry": "ctgov"}


def search(ctx: ToolContext | None, *, condition: str = "", term: str = "", intervention: str = "",
           location: str = "", max_results: int = 100) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"pageSize": min(max_results, 100), "countTotal": "true"}
    if condition:
        params["query.cond"] = condition
    if term:
        params["query.term"] = term
    if intervention:
        params["query.intr"] = intervention
    if location:
        params["query.locn"] = location
    out: list[dict[str, Any]] = []
    token = None
    while len(out) < max_results:
        if token:
            params["pageToken"] = token
        f = fetch(ctx, API, kind="ctgov", params=params, title=f"search {params}")
        data = f.json()
        out += [parse_study(s) for s in data.get("studies", [])]
        token = data.get("nextPageToken")
        if not token:
            break
    return out[:max_results]


# ------------------------------------------------------------------ 工具
class SearchArgs(BaseModel):
    condition: str = Field(default="", description="适应症（英文），对应 query.cond")
    term: str = Field(default="", description="其他关键词，如靶点、药物代号")
    intervention: str = Field(default="", description="干预措施/药物名，对应 query.intr")
    location: str = Field(default="", description="地点，如 China")
    max_results: int = Field(default=100, ge=1, le=500)
    route_id: str = Field(description="检索路线 ID，如 global:ctgov:condition")
    region: str = Field(default="global", description="china | global")


@REGISTRY.register("ctgov_search", "检索 ClinicalTrials.gov，返回试验摘要（NCT、期别、状态、申办方、干预、是否有中国站点）。"
                   "结果自动登记为试验实体并记入覆盖率。", SearchArgs)
def _ctgov_search(ctx: ToolContext, a: SearchArgs) -> Any:
    q = json.dumps({k: v for k, v in a.model_dump().items() if v and k not in {"route_id", "region"}},
                   ensure_ascii=False)
    try:
        rows = search(ctx, condition=a.condition, term=a.term, intervention=a.intervention,
                      location=a.location, max_results=a.max_results)
    except Exception as exc:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, a.region, q, "failed", note=str(exc)[:500])
        raise
    new = 0
    if ctx.db:
        for s in rows:
            trial_id, is_new = ctx.db.upsert_entity(ctx.project_id, "trial", s["nct"], attrs=_trial_attrs(s),
                                                    route_id=a.route_id)
            new += int(is_new)
            if ctx.stage in {'universe_china', 'universe_global'}:
                for intervention in s['interventions']:
                    raw = (intervention.get('name') or '').strip()
                    if intervention.get('type') not in {'DRUG', 'BIOLOGICAL'} or not raw or raw.casefold() in {'placebo', '安慰剂'}:
                        continue
                    # Registry occurrence is a provisional candidate, not a claim
                    # of innovation, approval, MAH, target or group assignment.
                    name = raw.casefold() if raw.isalpha() and raw.isascii() else raw
                    drug_id, drug_new = ctx.db.upsert_entity(ctx.project_id, 'drug', name,
                        aliases=[raw] if raw != name else [], route_id=a.route_id,
                        attrs={'discovery_method': 'registry_intervention',
                               'evidence_urls': [STUDY_URL.format(nct=s['nct'])]})
                    ctx.db.link(ctx.project_id, drug_id, 'drug-trial', trial_id)
                    new += int(drug_new)
        if ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, a.region, q, "ok", hits=len(rows), new_entities=new)
    interventions: dict[tuple[str, str], dict[str, Any]] = {}
    for study in rows:
        for item in study['interventions']:
            key = (item.get('name') or '', item.get('type') or '')
            entry = interventions.setdefault(key, {'name': key[0], 'type': key[1],
                                                   'other_names': [], 'trials': []})
            entry['other_names'] = sorted(set(entry['other_names']) | set(item.get('other_names') or []))
            if study['nct'] not in entry['trials']:
                entry['trials'].append(study['nct'])
    return {'count': len(rows), 'interventions': list(interventions.values()),
            'sponsors': sorted({s['sponsor'] for s in rows if s.get('sponsor')}),
            'studies': [{'nct': s['nct'], 'phase': s['phase'], 'china_site': s['china_site']}
                        for s in rows],
            'details_tool': 'ctgov_get', 'source_url_template': STUDY_URL}


class GetArgs(BaseModel):
    nct: str = Field(description="NCT 号，如 NCT01234567")


@REGISTRY.register("ctgov_get", "获取单个 CT.gov 试验的设计摘要（臂、终点、样本量、入排年龄、国家）。", GetArgs)
def _ctgov_get(ctx: ToolContext, a: GetArgs) -> Any:
    study, _ = get_study(ctx, a.nct)
    return parse_study(study)
