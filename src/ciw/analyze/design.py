"""C 设计先例：试验 × 设计维度矩阵；保留完整入排原文与计划终点。"""

from __future__ import annotations

from collections import Counter
from typing import Any

from ciw.analyze.common import product_label, role_label
from ciw.analyze.landscape import REGISTRY_ZH, STATUS_ZH
from ciw.config import IndicationConfig
from ciw.models import Product, Trial

ALLOCATION_ZH = {"RANDOMIZED": "随机", "NON_RANDOMIZED": "非随机", "NA": "不适用"}
MASKING_ZH = {"NONE": "开放", "SINGLE": "单盲", "DOUBLE": "双盲", "TRIPLE": "三盲", "QUADRUPLE": "四盲"}
MODEL_ZH = {"PARALLEL": "平行", "CROSSOVER": "交叉", "SINGLE_GROUP": "单组", "FACTORIAL": "析因", "SEQUENTIAL": "序贯"}


def _registration(t: Trial) -> dict[str, Any]:
    return {"trial_id": t.trial_id, "title": t.title, "registry": REGISTRY_ZH.get(t.registry, t.registry),
            "url": t.url, "phase": t.phase, "status": STATUS_ZH.get(t.status, t.status),
            "sponsor": t.sponsor, "enrollment": t.design.enrollment,
            "enrollment_text": t.design.enrollment_text,
            "enrollment_type": {"ACTUAL": "实际", "ESTIMATED": "计划"}.get(
                t.design.enrollment_type, t.design.enrollment_type),
            "eligibility": t.design.eligibility_text,
            "arms": [{"label": a.label, "role_label": role_label(a.role),
                      "interventions": a.interventions, "description": a.description} for a in t.arms],
            "primary": [o.model_dump() for o in t.outcomes_planned if o.kind == "primary"],
            "secondary": [o.model_dump() for o in t.outcomes_planned if o.kind == "secondary"],
            "source_id": t.locator.source_id}


def build_design(cfg: IndicationConfig, trials: list[Trial], products: dict[str, Product]) -> dict[str, Any]:
    labels = {c.id: c.label for c in cfg.concepts}
    rows = []
    for t in trials:
        if t.relevance != "core":
            continue
        prim = [o for o in t.outcomes_planned if o.kind == "primary"]
        sec = [o for o in t.outcomes_planned if o.kind == "secondary"]
        rows.append(
            {
                "trial_id": t.trial_id,
                "ids": t.ids,
                "registration_ids": list(dict.fromkeys(
                    [t.trial_id] + [r.trial_id for r in t.registrations])),
                "registrations": [_registration(r) for r in t.registrations],
                "registry": REGISTRY_ZH.get(t.registry, t.registry),
                "acronym": t.acronym,
                "title": t.title,
                "official_title": t.official_title,
                "url": t.url,
                "products": [
                    {
                        "product_id": pid,
                        "label": product_label(products.get(pid)),
                        "is_own": bool(products.get(pid) and products[pid].is_own),
                    }
                    for pid in t.product_ids
                ],
                "is_own": any(products.get(pid) and products[pid].is_own for pid in t.product_ids),
                "sponsor": t.sponsor,
                "phase": t.phase,
                "phase_rank": t.phase_rank,
                "status": STATUS_ZH.get(t.status, t.status),
                "start": t.dates.start,
                "primary_completion": t.dates.primary_completion,
                "results_posted": t.dates.results_first_posted,
                "china": t.china,
                "country_count": len(t.countries),
                "countries": t.countries,
                "allocation": ALLOCATION_ZH.get(t.design.allocation, t.design.allocation),
                "masking": MASKING_ZH.get(t.design.masking, t.design.masking),
                "model": MODEL_ZH.get(t.design.model, t.design.model),
                "enrollment": t.design.enrollment,
                "enrollment_text": t.design.enrollment_text,
                "enrollment_type": {"ACTUAL": "实际", "ESTIMATED": "计划"}.get(
                    t.design.enrollment_type, t.design.enrollment_type
                ),
                "arm_count": len(t.arms),
                "arms": [
                    {
                        "label": a.label,
                        "role_label": role_label(a.role),
                        "description": a.description,
                        "interventions": a.interventions,
                    }
                    for a in t.arms
                ],
                "background_therapy": t.design.background_therapy,
                "primary": [
                    {"title": o.title, "timeframe": o.timeframe, "concept": labels.get(o.concept_id or "", "")}
                    for o in prim
                ],
                "secondary": [
                    {"title": o.title, "timeframe": o.timeframe, "concept": labels.get(o.concept_id or "", "")}
                    for o in sec
                ],
                "primary_concepts": sorted({labels[o.concept_id] for o in prim if o.concept_id}),
                "min_age": t.design.min_age,
                "max_age": t.design.max_age,
                "sex": t.design.sex,
                "eligibility": t.design.eligibility_text,
                "has_results": t.has_results,
            }
        )
    # 设计参考价值：III（含 II/III）> IV > II > I > 未知；同期别按首例入组时间倒序
    priority = {4: 0, 5: 1, 3: 2, 2: 3, 1: 4, 0: 5}
    rows.sort(key=lambda r: r["start"] or "", reverse=True)
    rows.sort(key=lambda r: (not r["is_own"], priority.get(r["phase_rank"], 9)))
    facets = {
        "phase": Counter(r["phase"] for r in rows),
        "masking": Counter(r["masking"] for r in rows),
        "primary_concepts": Counter(c for r in rows for c in r["primary_concepts"]),
    }
    return {"rows": rows, "facets": {k: dict(v.most_common()) for k, v in facets.items()}}
