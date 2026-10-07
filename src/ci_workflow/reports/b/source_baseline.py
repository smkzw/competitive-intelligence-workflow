"""Source-only baseline observations for the existing B view contract.

Descriptive columns are not canonical population identities or efficacy
equivalence. Every consumed scalar keeps its own exact source and version;
mean, spread and limits are separate observations, never fabricated error bars.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ci_workflow.application.source_research_service import ResearchFact

_DESCRIPTIVE_POPULATION = "随机入组基线（仅描述性对照）"
# Bounded source wording checked against original modules. This does not rewrite
# analysis_population, accept ITT/FAS equivalence, or authorize a numeric effect.
_RANDOMIZED_WORDINGS = frozenset({
    "all randomized participants.",
    "analysis was performed on randomized population.",
    "analysis was performed on intent-to-treat population (itt) population which "
    "consisted of all randomized participants.",
    "intent-to-treat (itt) population included all randomized participants.",
})


def build_source_baseline_view(
    facts: Sequence[ResearchFact], *, source_versions: Mapping[str, str],
    fact_versions: Mapping[str, str],
) -> dict[str, Any]:
    """Project real numeric atoms; no arm, product, denominator or rate guess."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fact in facts:
        context = fact.result_context
        if context is None or context.category != "baseline":
            continue
        if fact.fact_id in seen:
            raise ValueError("基线事实身份重复，不能first-wins")
        seen.add(fact.fact_id)
        if not source_versions.get(fact.source_id) or not fact_versions.get(fact.fact_id):
            raise ValueError("基线来源或事实版本未闭合")
        population = context.analysis_population or ""
        shared = population.strip().casefold() in _RANDOMIZED_WORDINGS
        aggregate = (context.group_description or "").strip().casefold() == (
            "total of all reporting groups"
        )
        suffix = (fact.locator.field_path or "").rsplit(".", 1)[-1]
        stat = context.source_param_type or "未注明"
        if context.value_role == "dispersion":
            stat = context.source_dispersion_type or "未注明离散度"
        elif suffix in {"lowerLimit", "upperLimit"}:
            stat = "下限" if suffix == "lowerLimit" else "上限"
        elif context.value_role in {"denominator", "participant_count"}:
            stat = "count"
        stat_label = {"MEAN": "均值", "MEDIAN": "中位数",
                      "STANDARD_DEVIATION": "标准差", "count": "人数"}.get(stat, stat)
        labels = tuple(label for label in (
            context.term, context.class_title, context.category_title,
        ) if label)
        label = "｜".join(labels)
        if context.value_role == "dispersion" or suffix in {"lowerLimit", "upperLimit"}:
            label += "｜" + stat_label
        number = None if fact.normalized_value is None else float(fact.normalized_value)
        if context.value_role in {"denominator", "participant_count"} and number is not None:
            number = int(number)
        note = (
            "仅描述性对照，入排、背景治疗、设盲和给药方案仍需分别查看；"
            "不代表人群或疗效等价。原始分析人群：" + (population or "未明确")
        )
        note += (
            "；来源Total为研究汇总，不是治疗组。" if aggregate else
            "；结果组与产品关系待核，不按名称或顺序分配治疗角色。"
        )
        rows.append({
            "row_id": fact.fact_id, "source_row_id": fact.fact_id,
            "source_fact_version_id": fact_versions[fact.fact_id],
            "trial_id": context.trial_id.casefold(), "product_id": None,
            "group_id": context.group_id, "arm_role": "unknown",
            "group_assignment_state": "unknown", "is_source_aggregate": aggregate,
            "group_label_zh": "来源组：" + (context.group_title or context.group_id),
            "source_group_title": context.group_title,
            "source_group_description": context.group_description,
            "variable_label_zh": label, "source_name": context.term,
            "source_definition": "；".join((label, "原始分析人群：" + population,
                "原始组别：" + context.group_title,
                "原始统计形式：" + (context.source_param_type or "未注明"))),
            "clinical_concept": label,
            "field_family": "基线来源统计", "statistic_form": stat,
            "statistic_label_zh": stat_label,
            "source_param_type": context.source_param_type,
            "source_dispersion_type": context.source_dispersion_type,
            "source_value_role": context.value_role, "unit": context.source_unit,
            "value": number, "raw_value": fact.raw_value,
            "analysis_population": population,
            "population_context": (_DESCRIPTIVE_POPULATION if shared else
                                   population or "人群待核：" + context.trial_id),
            "baseline_timepoint": "登记基线（具体访视未注明）",
            "baseline_definition": "来源基线模块，不推断首次给药前访视",
            "source_measure_path": context.source_measure_path,
            "source_domain": "baseline", "source_metric": context.metric,
            "source_version_id": source_versions[fact.source_id],
            "source_locator": fact.locator.model_dump(mode="json"),
            "source_text": fact.original_text,
            "source_clause_context": (fact.source_clause_context.model_dump(mode="json")
                                      if fact.source_clause_context else None),
            "review_state": "candidate", "disclosure_state": (
                fact.disclosure_state if number is not None else "unresolved_due_to_route"
            ),
            "difference_labels_zh": (note,),
        })
    return {"facts": tuple(rows)}
