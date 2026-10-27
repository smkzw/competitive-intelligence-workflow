"""A 竞品全景：产品 × 最高阶段（全球/中国）、状态、时间线、未归类干预。"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ciw.analyze.common import product_label
from ciw.models import Event, Product, Trial

PHASE_COLUMNS = [(1, "早期I"), (2, "I"), (3, "II"), (4, "III"), (5, "IV（上市后）")]
ACTIVE = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}
STATUS_ZH = {
    "RECRUITING": "招募中",
    "NOT_YET_RECRUITING": "尚未招募",
    "ACTIVE_NOT_RECRUITING": "进行中（不再招募）",
    "ENROLLING_BY_INVITATION": "邀请入组",
    "COMPLETED": "已完成",
    "TERMINATED": "已终止",
    "WITHDRAWN": "已撤回",
    "SUSPENDED": "暂停",
    "UNKNOWN": "状态未知",
}
REGISTRY_ZH = {"ctgov": "ClinicalTrials.gov", "cde": "药物临床试验登记与信息公示平台"}


def build_landscape(
    products: list[Product],
    trials: list[Trial],
    events: list[Event],
    unclassified: list[dict[str, Any]],
    own_id: str | None,
) -> dict[str, Any]:
    core = [t for t in trials if t.relevance == "core" and t.status != "WITHDRAWN"]  # 撤回的试验从未入组
    by_product: dict[str, list[Trial]] = defaultdict(list)
    for t in core:
        for pid in t.product_ids:
            by_product[pid].append(t)
    ev_by: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if e.product_id:
            ev_by[e.product_id].append(e)

    rows = []
    for p in products:
        ts = by_product.get(p.product_id, [])
        if not ts and not ev_by.get(p.product_id) and not p.is_own:
            continue
        rows.append(_product_row(p, ts, ev_by.get(p.product_id, [])))
    own_other = [
        {
            "trial_id": t.trial_id,
            "indication": "、".join(t.conditions),
            "status": STATUS_ZH.get(t.status, t.status),
            "title": t.title,
            "url": t.url,
        }
        for t in trials
        if own_id
        and t.relevance == "background"
        and t.relevance_reason == "本品其他适应症登记"
        and own_id in t.product_ids
    ]
    for r in rows:
        r["innovative"] = next(p.innovative for p in products if p.product_id == r["product_id"])
        r["other_indications"] = own_other if r["is_own"] else []
    non_innovative = [r for r in rows if not r["innovative"]]
    rows = [r for r in rows if r["innovative"]]
    rows.sort(key=lambda r: (not r["is_own"], -r["global_rank"], -r["china_rank"], r["label"].casefold()))

    timeline = []
    for t in core:
        if t.phase_rank < 3 or not t.dates.start:
            continue
        for pid in t.product_ids:
            timeline.append(
                {
                    "product_id": pid,
                    "trial_id": t.trial_id,
                    "acronym": t.acronym,
                    "phase": t.phase,
                    "start": t.dates.start,
                    "primary_completion": t.dates.primary_completion,
                    "status": STATUS_ZH.get(t.status, t.status),
                    "china": t.china,
                }
            )
    return {
        "phase_columns": [{"rank": r, "label": lbl} for r, lbl in PHASE_COLUMNS],
        "products": rows,
        "non_innovative": non_innovative,
        "timeline": timeline,
        "unclassified": unclassified,
        "own_product_id": own_id,
    }


def _rank_label(rank: int) -> str:
    return dict(PHASE_COLUMNS).get(rank, "未知")


def _product_row(p, ts, product_events) -> dict[str, Any]:
    registered = [record for t in ts for record in [t, *t.registrations]]
    g = max((t.phase_rank for t in registered), default=0)
    cn = max((t.phase_rank for t in registered if t.china or t.registry == "cde"), default=0)
    statuses = Counter(t.status for t in ts)
    approvals = [
        e
        for e in product_events
        if e.event_type == "approval" and e.status in ("registry", "dual_agreed", "arbitrated")
    ]
    starts = sorted(t.dates.start for t in ts if t.dates.start)
    return {
        "product_id": p.product_id,
        "label": product_label(p),
        "name_en": p.name_en,
        "name_zh": p.name_zh,
        "codes": p.codes,
        "target": p.target,
        "modality": p.modality,
        "route": p.route,
        "company": p.company,
        "china_partner": p.china_partner,
        "is_own": p.is_own,
        "attribute_status": p.attribute_status,
        "global_rank": g,
        "china_rank": cn,
        "global_phase": _rank_label(g),
        "china_phase": _rank_label(cn) if cn else "—",
        "approvals": [
            {
                "region": e.region,
                "date": e.date,
                "status": e.status,
                "source_id": e.source_id,
                "detail": e.detail,
                "scope_label": e.indication or "药品许可",
            }
            for e in approvals
        ],
        "trial_count": len(ts),
        "active_trials": sum(statuses[s] for s in ACTIVE),
        "status_counts": {STATUS_ZH.get(k, k): v for k, v in statuses.items()},
        "first_start": starts[0] if starts else None,
        "key_trials": [
            t.trial_id for t in sorted(ts, key=lambda t: (-t.phase_rank, t.dates.start or "")) if t.phase_rank >= 3
        ][:12],
    }
