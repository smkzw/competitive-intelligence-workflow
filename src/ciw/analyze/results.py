"""B 临床结果：按临床问题（概念 × 时间点 × 统计形式）组织跨试验比较；历时折线；安全概况。

组间差只来自来源 analyses；没有时仅对同一试验内明确安慰剂臂计算差值（标“计算值”，无 CI）。
不同试验之间不计算任何差值，只并列。
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

from ciw.analyze.common import pct, product_label, role_label
from ciw.analyze.shared_cohort import collapse_shared
from ciw.config import IndicationConfig, normalize_name
from ciw.models import OutcomeResult, Product, SafetySummary, Trial
from ciw.normalize.comparison_context import context_display_label, endpoint_context
from ciw.normalize.semantics import MEASURE_LABEL_ZH

_CFB = re.compile(
    r"change from baseline|change in|percent(age)? change|reduction from baseline|improvement from baseline", re.I
)
_COMPUTABLE = {"ls_mean", "mean", "proportion"}
_RATIO = re.compile(r"ratio", re.I)
TYPE_ZH = {
    "PRIMARY": "主要终点",
    "SECONDARY": "次要终点",
    "OTHER_PRE_SPECIFIED": "其他预设终点",
    "POST_HOC": "事后分析",
}


_PCT_CHANGE = re.compile(r"percent(age)? change|% change|percent reduction", re.I)


def _cfb(r: OutcomeResult) -> bool:
    return bool(_CFB.search(r.title + (" " + r.description if r.kind == "publication" else "")))


def _pct(r: OutcomeResult) -> bool:
    """较基线百分比变化与绝对变化是不同估计量，不能同轴。"""
    return bool(_PCT_CHANGE.search(r.title + " " + r.unit + (" " + r.description if r.kind == "publication" else "")))


def _unit_key(unit: str) -> str:
    text = " ".join(unit.split())
    # Case of physical symbols can change the unit (M versus m); only prose labels fold case.
    return text.casefold() if text.casefold() in {"score on a scale", "score", "points", "point", "percent"} else text


def _label(base: str, cfb: bool, pct: bool, kind: str) -> str:
    if pct:
        return base + "较基线百分比变化"
    return base + ("较基线变化" if cfb and kind != "proportion" else "")


def build_results(
    cfg: IndicationConfig,
    trials: dict[str, Trial],
    products: dict[str, Product],
    results: list[OutcomeResult],
    own_id: str | None,
) -> dict[str, Any]:
    concepts = {c.id: c for c in cfg.concepts}
    buckets: dict[tuple, list[OutcomeResult]] = defaultdict(list)
    for r in results:
        t = trials.get(r.trial_id)
        if (not t or t.relevance != "core" or r.domain != "efficacy" or not r.concept_id
                or r.time is None or r.time.key == "BASELINE"):
            continue
        buckets[
            (
                r.concept_id,
                r.time.key,
                r.measure_kind,
                _cfb(r),
                _pct(r),
                r.subgroup,
                r.category_title,
                _unit_key(r.unit),
            )
        ].append(r)

    questions = []
    for (cid, tkey, kind, cfb, pctc, sub, cat, unit), rs in buckets.items():
        c = concepts[cid]
        rows, comps = [], []
        for r in rs:
            t = trials[r.trial_id]
            for g in r.groups:
                if g.value is None or g.period != "treatment" or g.role in ("other",):
                    continue
                rows.append(_group_row(r, t, g, products))
            comps.extend(_comparisons(r, t, products))
        if not rows and not comps and not any(r.analyses for r in rs):
            continue
        trial_ids = sorted({r.trial_id for r in rs})
        rows.sort(key=lambda x: (not x["is_own"], x["acronym"], x["role"] != "placebo", x["group_title"]))
        comps.sort(key=lambda x: (not x["is_own"], x["product_label"], x["acronym"]))
        has_primary = any(r.type == "PRIMARY" for r in rs)
        questions.append(
            {
                "question_id": "q_"
                + hashlib.sha256(repr((cid, tkey, kind, cfb, pctc, sub, cat, unit)).encode()).hexdigest()[:12],
                "concept_id": cid,
                "label": _label(c.label, cfb, pctc, kind),
                "subgroup": sub,
                "category": cat,
                "time_label": rs[0].time.label,
                "time_key": tkey,
                "weeks": rs[0].time.weeks,
                "measure_kind": kind,
                "change_from_baseline": cfb,
                "percent_change": pctc,
                "measure_label": MEASURE_LABEL_ZH.get(kind, kind),
                "direction": c.direction,
                "units": sorted({r.unit for r in rs if r.unit}),
                "has_primary": has_primary,
                "trial_ids": trial_ids,
                "rows": rows,
                "comparisons": comps,
                "frames": _context_frames(rs, c, trials, products),
            }
        )
    questions.sort(
        key=lambda q: (bool(q["subgroup"]), not q["has_primary"], -len(q["trial_ids"]), q["label"], q["weeks"] or 999)
    )
    return {"questions": questions, "longitudinal": _longitudinal(cfg, trials, products, results),
            "observations": _observations(trials, products, results)}


def _context_frames(results, concept, trials, products):
    contexts = defaultdict(list)
    for result in results:
        contexts[endpoint_context(result, concept)].append(result)
    frames = []
    for context, rs in sorted(contexts.items()):
        rows, comps = [], []
        for r in rs:
            trial = trials[r.trial_id]
            rows.extend(_group_row(r, trial, g, products) for g in r.groups
                        if g.value is not None and g.period == "treatment" and g.role != "other")
            comps.extend(_comparisons(r, trial, products))
        frames.append(dict(frame_id="frame_" + hashlib.sha256(repr(context).encode()).hexdigest()[:12],
                           context_label=context_display_label(rs[0]), title=rs[0].title, description=rs[0].description,
                           population=rs[0].population, trial_ids=sorted({r.trial_id for r in rs}),
                           result_ids=[r.result_id for r in rs], rows=collapse_shared(rows, rs, trials),
                           comparisons=collapse_shared(comps, rs, trials),
                           source_statistics=collapse_shared(_source_statistics(rs, trials, comps), rs, trials)))
    return sorted(frames, key=lambda f: (-len(f["trial_ids"]), f["frame_id"]))


def _source_statistics(results, trials, comparisons):
    projected = {(r["result_id"], r["path"]) for r in comparisons if r["kind"] == "reported"}
    rows = []
    for result in results:
        trial = trials[result.trial_id]
        groups = {g.group_id: g for g in result.groups}
        for analysis in result.analyses:
            if (result.result_id, analysis.path) in projected:
                continue
            rows.append(dict(result_id=result.result_id, trial_id=trial.trial_id,
                acronym=trial.acronym or trial.trial_id, phase=trial.phase,
                source_id=result.locator.source_id, path=analysis.path, url=result.source_url or trial.url,
                status=result.status, group_labels=[groups[g].title if g in groups else g for g in analysis.group_ids],
                param_type=analysis.param_type, value=analysis.value, value_raw=analysis.value_raw,
                ci_lower=analysis.ci_lower, ci_upper=analysis.ci_upper, ci_pct=analysis.ci_pct,
                p_value=analysis.p_value, method=analysis.method))
    return rows


def _observations(trials, products, results):
    domains = {"efficacy": "疗效", "safety": "安全性", "pk": "药代动力学", "pd": "药效学",
               "immunogenicity": "免疫原性", "other": "其他观测"}
    return [
        {
            "result_id": r.result_id, "trial_id": t.trial_id, "acronym": t.acronym or t.trial_id,
            "products": [product_label(products.get(pid)) for pid in t.product_ids],
            "phase": t.phase, "domain": r.domain, "domain_label": domains[r.domain],
            "title": r.title, "timeframe": r.timeframe, "class_title": r.class_title,
            "time_label": r.time.label if r.time else "", "time_key": r.time.key if r.time else "",
            "category_title": r.category_title, "population": r.population,
            "unit": r.unit, "param_type": r.param_type, "dispersion_type": r.dispersion_type,
            "status": r.status, "source_kind": r.kind, "url": r.source_url or t.url, "source_id": r.locator.source_id,
            "groups": [{**g.model_dump(), "role_label": role_label(g.role, t, g.arm_id)} for g in r.groups],
            "analyses": [a.model_dump() for a in r.analyses],
        }
        for r in results if (t := trials.get(r.trial_id)) and t.relevance == "core"
    ]


def _orient(a_val: float, g1, g2) -> tuple | None:
    """由两组数值确定来源差值方向：返回 (被减组, 减数组)；对不上返回 None。"""
    if g1.value is None or g2.value is None:
        return None
    tol = max(0.005, abs(a_val) * 0.03)
    fwd = abs((g1.value - g2.value) - a_val) <= tol
    rev = abs((g2.value - g1.value) - a_val) <= tol
    if fwd and not rev:
        return g1, g2
    if rev and not fwd:
        return g2, g1
    return None  # 对不上，或差值太小两种方向都成立


def _comparisons(r: OutcomeResult, t: Trial, products: dict[str, Product]) -> list[dict[str, Any]]:
    groups = {g.group_id: g for g in r.groups if g.period == "treatment"}
    placebo = [g for g in groups.values() if g.role == "placebo"]
    out, covered = [], set()
    ctrl_roles = ("placebo", "active_comparator", "no_intervention")
    for a in r.analyses:
        if len(a.group_ids) != 2 or a.value is None:
            continue
        g1, g2 = (groups.get(x) for x in a.group_ids)
        if not g1 or not g2:
            continue
        ratio = bool(_RATIO.search(a.param_type))
        orient = None if ratio else _orient(a.value, g1, g2)
        if not ratio and {a.minuend_group_id, a.subtrahend_group_id} == {g1.group_id, g2.group_id}:
            orient = groups[a.minuend_group_id], groups[a.subtrahend_group_id]
        ctrl = next((g for g in (g1, g2) if g.role in ctrl_roles), None)
        exp = next((g for g in (g1, g2) if g is not ctrl and g.role == "experimental"), None)
        h2h = ctrl is None and g1.role == g2.role == "experimental"
        if h2h:
            exp, ctrl = orient if orient else (g1, g2)
        if not ctrl or not exp:
            continue
        covered.add(exp.group_id)
        plot = (a.value, a.ci_lower, a.ci_upper)
        if ratio:
            note = "比值，方向以来源统计量名称为准"
        elif orient is None:
            note = "差值方向无法由组均值确定，不入图"
            plot = (None, None, None)
        elif orient[0] is exp:
            note = ""
        else:
            note = "来源差值为对照组−试验组，图中已换算为试验组−对照组"
            plot = (-a.value, _neg(a.ci_upper), _neg(a.ci_lower))
        out.append(
            _comp_row(
                r,
                t,
                products,
                exp,
                ctrl,
                kind="reported",
                value=a.value,
                ci_lower=a.ci_lower,
                ci_upper=a.ci_upper,
                ci_pct=a.ci_pct,
                p_value=a.p_value,
                method=a.method,
                param_type=a.param_type,
                path=a.path,
                note=note,
                h2h=h2h,
                family="ratio" if ratio else "difference",
                plot_value=plot[0],
                plot_lower=plot[1],
                plot_upper=plot[2],
            )
        )
    out.extend(_computed_comparisons(r, t, products, groups, placebo, covered))
    return out


def _neg(x: float | None) -> float | None:
    return None if x is None else -x


def _comp_row(r, t, products, exp, ctrl, **kw) -> dict[str, Any]:
    pid = exp.product_id
    return {
        "result_id": r.result_id,
        "trial_id": t.trial_id,
        "acronym": t.acronym or t.trial_id,
        "phase": t.phase,
        "product_id": pid,
        "product_label": product_label(products.get(pid)) if pid else exp.title,
        "is_own": bool(pid and products.get(pid) and products[pid].is_own),
        "exp_group": exp.title,
        "ctrl_group": ctrl.title,
        "ctrl_role_label": "头对头（另一试验组）" if kw.get("h2h") else role_label(ctrl.role),
        "n_exp": exp.n,
        "n_ctrl": ctrl.n,
        "source_id": r.locator.source_id,
        "source_kind": r.kind,
        "status": r.status,
        "url": r.source_url or t.url,
        "kind_label": "来源报告" if kw["kind"] == "reported" else "计算值",
        "group_basis": "论文分组"
        if r.kind == "publication" and (exp.arm_id is None or ctrl.arm_id is None) else "登记臂",
        **kw,
    }


def _longitudinal(
    cfg: IndicationConfig, trials: dict[str, Trial], products: dict[str, Product], results: list[OutcomeResult]
) -> list[dict[str, Any]]:
    labels = {c.id: c.label for c in cfg.concepts}
    charts: dict[tuple, dict[tuple, list]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        t = trials.get(r.trial_id)
        if (
            not t
            or t.relevance != "core"
            or r.domain != "efficacy"
            or not r.concept_id
            or r.time is None
            or r.time.key == "BASELINE"
            or r.time.weeks is None
            or "*" in r.time.key  # 多时间点汇总的单值，不是某一周的观察
            or "-" in r.time.key  # 区间（如第 49–52 周）不是单一时点
            or r.subgroup
            or r.category_title
        ):
            continue
        for g in r.groups:
            if g.value is None or g.period != "treatment":
                continue
            series_key = (t.trial_id, normalize_name(g.title))
            context = endpoint_context(r, next(c for c in cfg.concepts if c.id == r.concept_id))
            charts[(r.concept_id, r.measure_kind, _cfb(r), _pct(r), _unit_key(r.unit), context)][series_key].append(
                {
                    "weeks": r.time.weeks,
                    "label": r.time.label,
                    "value": g.value,
                    "lower": g.lower,
                    "upper": g.upper,
                    "n": g.n,
                    "group_title": g.title,
                    "role": g.role,
                    "product_id": g.product_id,
                    "acronym": t.acronym or t.trial_id,
                    "path": g.path,
                    "source_id": r.locator.source_id,
                }
            )
    out = []
    for (cid, kind, cfb, pctc, unit, context), series in charts.items():
        lines = []
        for (tid, _), pts in series.items():
            by_week: dict[float, list] = defaultdict(list)
            for pt in pts:
                by_week[pt["weeks"]].append(pt)
            # 同一周出现不同数值（主分析与敏感性分析等）时整周剔除，不静默取其一
            uniq = {w: v[0] for w, v in sorted(by_week.items()) if len({x["value"] for x in v}) == 1}
            if len(uniq) < 2:
                continue
            first = next(iter(uniq.values()))
            pid = first["product_id"]
            lines.append(
                {
                    "trial_id": tid,
                    "acronym": first["acronym"],
                    "group_title": first["group_title"],
                    "role": first["role"],
                    "role_label": first.get("role_label") or role_label(first["role"]),
                    "product_label": product_label(products.get(pid)) if pid else "",
                    "is_own": bool(pid and products.get(pid) and products[pid].is_own),
                    "points": list(uniq.values()),
                }
            )
        if lines:
            out.append(
                {
                    "chart_id": f"l_{cid}_{kind}_{int(cfb)}{int(pctc)}_"
                    + hashlib.sha256(repr((unit, context)).encode()).hexdigest()[:10],
                    "concept_id": cid,
                    "label": _label(labels[cid], cfb, pctc, kind),
                    "measure_label": MEASURE_LABEL_ZH.get(kind, kind),
                    "unit": unit,
                    "lines": lines,
                }
            )
    out.sort(key=lambda c: -len(c["lines"]))
    return out


def build_safety(
    trials: dict[str, Trial], products: dict[str, Product], safety: list[SafetySummary]
) -> list[dict[str, Any]]:
    rows = []
    for s in safety:
        t = trials.get(s.trial_id)
        if not t or t.relevance != "core":
            continue
        disc = {normalize_name(d.title): d for d in s.discontinuations}
        for g in s.groups:
            if g.period != "treatment" or g.role in ("other",):
                continue
            d = disc.get(normalize_name(g.title))
            if d is None:
                same = [x for x in s.discontinuations if x.role == g.role and x.product_id == g.product_id]
                d = same[0] if len(same) == 1 else None
            top = _top_terms(s, g.group_id)
            pid = g.product_id if g.role != "placebo" else None
            rows.append(
                {
                    "trial_id": t.trial_id,
                    "acronym": t.acronym or t.trial_id,
                    "phase": t.phase,
                    "product_id": pid,
                    "product_label": product_label(products.get(pid)) if pid else "",
                    "is_own": bool(pid and products.get(pid) and products[pid].is_own),
                    "group_title": g.title,
                    "role": g.role,
                    "role_label": role_label(g.role, t, g.arm_id),
                    "N": g.serious.N or g.other.N,
                    "sae_n": g.serious.n,
                    "sae_pct": pct(g.serious.n, g.serious.N),
                    "other_n": g.other.n,
                    "other_pct": pct(g.other.n, g.other.N),
                    "other_threshold": s.other_threshold,
                    "death_n": g.deaths.n,
                    "death_N": g.deaths.N,
                    "disc_n": d.n if d else None,
                    "disc_N": d.N if d else None,
                    "disc_pct": pct(d.n, d.N) if d else None,
                    "timeframe": s.timeframe,
                    "top_terms": top,
                    "source_id": s.locator.source_id,
                    "url": t.url,
                }
            )
    rows.sort(key=lambda r: (not r["is_own"], r["acronym"], r["role"] != "placebo"))
    return rows


def _top_terms(s: SafetySummary, group_id: str, k: int = 6) -> list[dict[str, Any]]:
    scored = []
    for term in s.terms:
        st = next((x for x in term.stats if x.group_id == group_id), None)
        p = pct(st.n, st.N) if st else None
        if p is not None and p > 0:
            scored.append({"term": term.term, "serious": term.serious, "n": st.n, "N": st.N, "pct": p})
    scored.sort(key=lambda x: -x["pct"])
    return scored[:k]


def _group_row(r, t, g, products) -> dict[str, Any]:
    pid = g.product_id if g.role != "placebo" else None
    return {
        "result_id": r.result_id,
        "trial_id": t.trial_id,
        "acronym": t.acronym or t.trial_id,
        "phase": t.phase,
        "outcome_type": TYPE_ZH.get(r.type, r.type),
        "product_id": pid,
        "product_label": product_label(products.get(pid)) if pid else "",
        "is_own": bool(pid and products.get(pid) and products[pid].is_own),
        "group_title": g.title,
        "role": g.role,
        "role_label": role_label(g.role, t, g.arm_id),
        "n": g.n,
        "value": g.value,
        "spread": g.spread,
        "lower": g.lower,
        "upper": g.upper,
        "dispersion_type": r.dispersion_type,
        "unit": r.unit,
        "timeframe": r.timeframe,
        "title": r.title,
        "class_title": r.class_title,
        "category_title": r.category_title,
        "population": r.population,
        "source_kind": r.kind,
        "status": r.status,
        "source_id": r.locator.source_id,
        "path": g.path,
        "url": r.source_url or t.url,
    }


def _computed_comparisons(r, t, products, groups, placebo, covered):
    out = []
    if r.measure_kind in _COMPUTABLE and len(placebo) == 1 and placebo[0].value is not None:
        ctrl = placebo[0]
        for g in groups.values():
            if g.role == "experimental" and g.group_id not in covered and g.value is not None:
                out.append(
                    _comp_row(
                        r,
                        t,
                        products,
                        g,
                        ctrl,
                        kind="computed",
                        value=round(g.value - ctrl.value, 4),
                        ci_lower=None,
                        ci_upper=None,
                        ci_pct=None,
                        p_value="",
                        method="",
                        param_type="组均值之差（计算值）"
                        if r.measure_kind != "proportion"
                        else "比例之差（百分点，计算值）"
                        if re.search(r"percent|%", r.unit, re.I)
                        else "比例之差（计算值）",
                        path=g.path,
                        note="",
                        h2h=False,
                        family="difference",
                        plot_value=round(g.value - ctrl.value, 4),
                        plot_lower=None,
                        plot_upper=None,
                    )
                )
    return out
