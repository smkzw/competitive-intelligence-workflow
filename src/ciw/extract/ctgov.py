"""CT.gov v2 记录 → Trial / OutcomeResult / SafetySummary（确定性抽取，状态 registry）。

硬规则（见 PRD §3）：缺失不是 0；人数与比例分开；统计形式取 paramType；
组别角色只来自 armGroups.type 与显式匹配；组间差只取 analyses。
"""

from __future__ import annotations

import re
from typing import Any

from ciw.config import IndicationConfig
from ciw.models import (
    AETerm,
    AETermStat,
    Analysis,
    Arm,
    CountN,
    Design,
    Discontinuation,
    GroupValue,
    Locator,
    OutcomeResult,
    PlannedOutcome,
    SafetyGroup,
    SafetySummary,
    Source,
    Trial,
    TrialDates,
    stable_id,
)
from ciw.normalize.arms import ROLE_BY_TYPE, match_group, period_of
from ciw.normalize.products import ProductResolver
from ciw.normalize.semantics import classify, concept_of, measure_kind, parse_timepoint, subgroup_of
from ciw.normalize.trials import registry_ids

PHASE_LABEL = {"EARLY_PHASE1": "早期I", "PHASE1": "I", "PHASE2": "II", "PHASE3": "III", "PHASE4": "IV", "NA": "不适用"}
PHASE_RANK = {"NA": 0, "EARLY_PHASE1": 1, "PHASE1": 2, "PHASE2": 3, "PHASE3": 4, "PHASE4": 5}
CHINA_COUNTRIES = {"China"}


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def _int(v: Any) -> int | None:
    x = _num(v)
    return int(x) if x is not None and float(x).is_integer() else None


def _date(struct: dict[str, Any] | None) -> str | None:
    return (struct or {}).get("date")


def phase_of(phases: list[str]) -> tuple[str, int]:
    if not phases:
        return "", 0
    labels = [PHASE_LABEL.get(p, p) for p in phases]
    return "/".join(labels), max(PHASE_RANK.get(p, 0) for p in phases)


# ---------------------------------------------------------------- 方案
def _secondary_ids(ident: dict[str, Any]) -> dict[str, str]:
    secondary = [entry.get("id", "") for entry in ident.get("secondaryIdInfos", [])]
    ctr = registry_ids(";".join(secondary), "cde")
    return {"ctr": ";".join(ctr)} if ctr else {}


def extract_trial(study: dict[str, Any], source: Source, cfg: IndicationConfig, resolver: ProductResolver) -> Trial:
    p = study["protocolSection"]
    ident = p["identificationModule"]
    nct = ident["nctId"]
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    arms_mod = p.get("armsInterventionsModule", {})
    elig = p.get("eligibilityModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {})
    locations = p.get("contactsLocationsModule", {}).get("locations", [])
    cond_mod = p.get("conditionsModule", {})

    phase, rank = phase_of(design.get("phases", []))
    interventions = arms_mod.get("interventions", [])
    iv_product = {iv["name"]: resolver.resolve_intervention(iv["name"]) for iv in interventions}

    arms: list[Arm] = []
    for i, ag in enumerate(arms_mod.get("armGroups", [])):
        names = [re.sub(r"^[A-Za-z ]+:\s*", "", n) for n in ag.get("interventionNames", [])]
        pids = sorted({pid for n in names if (pid := iv_product.get(n) or resolver.resolve_intervention(n))})
        arms.append(
            Arm(
                arm_id=f"A{i}",
                label=ag.get("label", ""),
                type=ag.get("type", ""),
                role=ROLE_BY_TYPE.get(ag.get("type", ""), "unknown"),
                description=ag.get("description", ""),
                interventions=names,
                product_ids=pids,
            )
        )

    product_ids = sorted({pid for pid in iv_product.values() if pid})
    background = sorted(
        {
            n
            for n, pid in iv_product.items()
            if pid is None and cfg.is_background(n) and not re.search(r"placebo|matching", n, re.I)
        }
    )

    text = " ".join(
        [
            ident.get("briefTitle", ""),
            ident.get("officialTitle", ""),
            *cond_mod.get("conditions", []),
            *cond_mod.get("keywords", []),
        ]
    )
    relevant = cfg.is_relevant_text(text)
    if relevant and product_ids:
        relevance, reason = "core", "适应症匹配且含竞品干预"
    elif relevant:
        relevance, reason = "background", "适应症匹配，但干预均为背景/传统治疗或未归类"
    else:
        relevance, reason = "background", "检索命中但条件/标题未明确为本适应症"

    countries = sorted({loc.get("country", "") for loc in locations if loc.get("country")})
    enroll = design.get("enrollmentInfo", {})
    masking = design.get("designInfo", {}).get("maskingInfo", {})
    outcomes: list[PlannedOutcome] = []
    out_mod = p.get("outcomesModule", {})
    for kind, key in (("primary", "primaryOutcomes"), ("secondary", "secondaryOutcomes"), ("other", "otherOutcomes")):
        for o in out_mod.get(key, []):
            outcomes.append(
                PlannedOutcome(
                    kind=kind,
                    title=o.get("measure", ""),
                    timeframe=o.get("timeFrame", ""),
                    description=o.get("description", ""),
                    concept_id=concept_of(o.get("measure", ""), cfg),
                )
            )
    return Trial(
        trial_id=nct,
        registry="ctgov",
        ids={"nct": nct, **({"org": ident["orgStudyIdInfo"]["id"]} if ident.get("orgStudyIdInfo") else {}),
             **_secondary_ids(ident)},
        acronym=ident.get("acronym", ""),
        title=ident.get("briefTitle", ""),
        official_title=ident.get("officialTitle", ""),
        phase=phase,
        phase_rank=rank,
        status=status.get("overallStatus", ""),
        dates=TrialDates(
            start=_date(status.get("startDateStruct")),
            primary_completion=_date(status.get("primaryCompletionDateStruct")),
            completion=_date(status.get("completionDateStruct")),
            first_posted=_date(status.get("studyFirstPostDateStruct")),
            results_first_posted=_date(status.get("resultsFirstPostDateStruct")),
            last_update=_date(status.get("lastUpdatePostDateStruct")),
        ),
        sponsor=sponsor.get("leadSponsor", {}).get("name", ""),
        sponsor_class=sponsor.get("leadSponsor", {}).get("class", ""),
        collaborators=[c.get("name", "") for c in sponsor.get("collaborators", [])],
        countries=countries,
        china=bool(CHINA_COUNTRIES & set(countries)),
        conditions=cond_mod.get("conditions", []),
        design=Design(
            allocation=design.get("designInfo", {}).get("allocation", ""),
            model=design.get("designInfo", {}).get("interventionModel", ""),
            masking=masking.get("masking", ""),
            masked_roles=masking.get("whoMasked", []),
            purpose=design.get("designInfo", {}).get("primaryPurpose", ""),
            enrollment=_int(enroll.get("count")),
            enrollment_type=enroll.get("type", ""),
            eligibility_text=elig.get("eligibilityCriteria", ""),
            min_age=elig.get("minimumAge", ""),
            max_age=elig.get("maximumAge", ""),
            sex=elig.get("sex", ""),
            healthy_volunteers=elig.get("healthyVolunteers"),
            arm_count=len(arms),
            background_therapy=background,
        ),
        arms=arms,
        outcomes_planned=outcomes,
        product_ids=product_ids,
        has_results=bool(study.get("hasResults")),
        relevance=relevance,
        relevance_reason=reason,
        url=source.url,
        locator=Locator(source_id=source.source_id, path="protocolSection"),
    )


# ---------------------------------------------------------------- 结果
def _denoms(denoms: list[dict[str, Any]] | None) -> dict[str, int | None]:
    for d in denoms or []:
        if str(d.get("units", "")).strip().lower() == "participants":
            return {c["groupId"]: _int(c.get("value")) for c in d.get("counts", [])}
    return {}


def extract_results(
    study: dict[str, Any], trial: Trial, source: Source, cfg: IndicationConfig, resolver: ProductResolver
) -> tuple[list[OutcomeResult], dict[str, int]]:
    results: list[OutcomeResult] = []
    stats = {"outcomes": 0, "analyses_unassigned": 0}
    measures = study.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    for oi, om in enumerate(measures):
        stats["outcomes"] += 1
        title = om.get("title", "")
        domain, concept = classify(title, cfg)
        kind = measure_kind(om.get("paramType", ""), om.get("unitOfMeasure", ""))
        group_meta = {}
        for g in om.get("groups", []):
            arm_id, role, pid = match_group(g.get("title", ""), trial.arms, resolver)
            group_meta[g["id"]] = (g.get("title", ""), arm_id, role, pid, period_of(g.get("title", "")))
        outcome_n = _denoms(om.get("denoms"))
        combos = [
            (ci, c, ki, cat)
            for ci, c in enumerate(om.get("classes", []))
            for ki, cat in enumerate(c.get("categories", []))
        ]
        analyses = [
            _analysis(a, f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{oi}].analyses[{ai}]")
            for ai, a in enumerate(om.get("analyses", []))
        ]
        if len(combos) != 1 and analyses:
            stats["analyses_unassigned"] += len(analyses)
        for ci, cls, ki, cat in combos:
            class_n = _denoms(cls.get("denoms")) or outcome_n
            class_title = cls.get("title", "") or ""
            if _BASELINE_CLASS.fullmatch(class_title):
                continue  # 基线值不是该终点的结果，不进入比较
            class_time, class_rest = _split_class(class_title)
            tp = parse_timepoint(class_time, title, om.get("timeFrame", ""))
            subgroup = "；".join(x for x in (subgroup_of(title), class_rest) if x)
            groups: list[GroupValue] = []
            for mi, m in enumerate(cat.get("measurements", [])):
                gid = m["groupId"]
                gtitle, arm_id, role, pid, period = group_meta.get(gid, (gid, None, "unknown", None, "treatment"))
                groups.append(
                    GroupValue(
                        group_id=gid,
                        title=gtitle,
                        arm_id=arm_id,
                        role=role,
                        period=period,
                        product_id=pid,
                        n=class_n.get(gid),
                        value=_num(m.get("value")),
                        value_raw=str(m.get("value", "")),
                        spread=_num(m.get("spread")),
                        lower=_num(m.get("lowerLimit")),
                        upper=_num(m.get("upperLimit")),
                        path=(
                            f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{oi}].classes[{ci}]"
                            f".categories[{ki}].measurements[{mi}]"
                        ),
                    )
                )
            results.append(
                OutcomeResult(
                    result_id=stable_id("res", trial.trial_id, oi, ci, ki),
                    trial_id=trial.trial_id,
                    outcome_index=oi,
                    type=om.get("type", ""),
                    title=title,
                    description=om.get("description", ""),
                    timeframe=om.get("timeFrame", ""),
                    time=tp,
                    class_title=class_title,
                    category_title=cat.get("title", "") or "",
                    subgroup=subgroup,
                    concept_id=concept,
                    domain=domain,
                    measure_kind=kind,
                    param_type=om.get("paramType", ""),
                    dispersion_type=om.get("dispersionType", ""),
                    unit=om.get("unitOfMeasure", ""),
                    population=om.get("populationDescription", ""),
                    groups=groups,
                    analyses=analyses if len(combos) == 1 else [],
                    locator=Locator(
                        source_id=source.source_id, path=f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{oi}]"
                    ),
                )
            )
    return results, stats


_TIME_CLASS = re.compile(
    r"\s*(?:at\s+)?(?:weeks?|days?|months?|visit)\s*\d+(?:\.\d+)?(?:\s*(?:to|-|–|through)\s*(?:weeks?|days?|months?)?\s*\d+)?"
    r"\s*(?:\([^)]*\))?\s*",
    re.I,
)
_BASELINE_CLASS = re.compile(r"\s*(?:at\s+)?baseline\s*(?:\((?:day|week)\s*[01]\)|\(.{0,20}\))?\s*", re.I)


_TIME_TOKEN = re.compile(r"\b(?:at\s+)?(?:weeks?|days?|months?)\s*\d+(?:\.\d+)?\b", re.I)
_NOISE = re.compile(r"\bn\s*=\s*[\d,\s]+|[,;:：\-–—()（）\s]+$|^[,;:：\-–—()（）\s]+", re.I)


def _split_class(text: str) -> tuple[str, str]:
    """class 标题 → (时间部分, 其余文字)。

    “Week 21, n=42, 32” → ("Week 21", "")；“Change in PM Score - Week 12” → ("Week 12", "Change in PM Score")。
    """
    t = text or ""
    if _looks_like_time(t):
        return t, ""
    hits = _TIME_TOKEN.findall(t)
    if len(hits) != 1:
        return "", t.strip()
    rest = _TIME_TOKEN.sub(" ", t)
    for _ in range(3):
        rest = _NOISE.sub("", rest).strip()
    return hits[0], rest


def _looks_like_time(text: str) -> bool:
    """class 标题整体是时间点（“Week 24”“Day 169 (EOT)”）才算；“≥2 prior surgeries in 12 months”是亚组。"""
    return bool(_TIME_CLASS.fullmatch(text or ""))


def _analysis(a: dict[str, Any], path: str) -> Analysis:
    return Analysis(
        group_ids=list(a.get("groupIds", [])),
        param_type=a.get("paramType", "") or "",
        value=_num(a.get("paramValue")),
        value_raw=str(a.get("paramValue", "") or ""),
        ci_pct=_num(a.get("ciPctValue")),
        ci_lower=_num(a.get("ciLowerLimit")),
        ci_upper=_num(a.get("ciUpperLimit")),
        p_value=str(a.get("pValue", "") or ""),
        method=a.get("statisticalMethod", "") or "",
        test_type=a.get("nonInferiorityType", "") or "",
        path=path,
    )


def _discontinuations(study: dict[str, Any], trial: Trial, resolver: ProductResolver) -> list[Discontinuation]:
    flow = study.get("resultsSection", {}).get("participantFlowModule", {})
    periods = flow.get("periods", [])
    if not periods:
        return []
    started: dict[str, int | None] = {}
    for m in periods[0].get("milestones", []):
        if m.get("type") == "STARTED":
            started = {a["groupId"]: _int(a.get("numSubjects")) for a in m.get("achievements", [])}
    totals: dict[str, int] = {}
    reported = False
    for per in periods[:1]:  # 只计首个（随机治疗）时期；随访/延长期退出不归入该组
        for w in per.get("dropWithdraws", []):
            if "adverse event" not in str(w.get("type", "")).lower():
                continue
            reported = True
            for r in w.get("reasons", []):
                n = _int(r.get("numSubjects"))
                if n is not None:
                    totals[r["groupId"]] = totals.get(r["groupId"], 0) + n
    out = []
    for g in flow.get("groups", []):
        arm_id, role, pid = match_group(g.get("title", ""), trial.arms, resolver)
        out.append(
            Discontinuation(
                group_id=g["id"],
                title=g.get("title", ""),
                role=role,
                product_id=pid,
                n=totals.get(g["id"]) if reported else None,
                N=started.get(g["id"]),
            )
        )
    return out


def extract_safety(
    study: dict[str, Any], trial: Trial, source: Source, resolver: ProductResolver
) -> SafetySummary | None:
    ae = study.get("resultsSection", {}).get("adverseEventsModule")
    if not ae:
        return None
    groups = []
    for g in ae.get("eventGroups", []):
        arm_id, role, pid = match_group(g.get("title", ""), trial.arms, resolver)
        groups.append(
            SafetyGroup(
                group_id=g["id"],
                title=g.get("title", ""),
                arm_id=arm_id,
                role=role,
                period=period_of(g.get("title", "")),
                product_id=pid,
                serious=CountN(n=_int(g.get("seriousNumAffected")), N=_int(g.get("seriousNumAtRisk"))),
                other=CountN(n=_int(g.get("otherNumAffected")), N=_int(g.get("otherNumAtRisk"))),
                deaths=CountN(n=_int(g.get("deathsNumAffected")), N=_int(g.get("deathsNumAtRisk"))),
            )
        )
    terms = []
    for serious, key in ((True, "seriousEvents"), (False, "otherEvents")):
        for e in ae.get(key, []):
            terms.append(
                AETerm(
                    term=e.get("term", ""),
                    organ_system=e.get("organSystem", ""),
                    serious=serious,
                    stats=[
                        AETermStat(
                            group_id=s["groupId"],
                            n=_int(s.get("numAffected")),
                            N=_int(s.get("numAtRisk")),
                            events=_int(s.get("numEvents")),
                        )
                        for s in e.get("stats", [])
                    ],
                )
            )
    return SafetySummary(
        trial_id=trial.trial_id,
        timeframe=ae.get("timeFrame", ""),
        description=ae.get("description", ""),
        other_threshold=_num(ae.get("frequencyThreshold")),
        groups=groups,
        terms=terms,
        discontinuations=_discontinuations(study, trial, resolver),
        locator=Locator(source_id=source.source_id, path="resultsSection.adverseEventsModule"),
    )
