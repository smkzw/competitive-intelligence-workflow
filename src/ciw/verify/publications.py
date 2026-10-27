"""Primary-publication numbers, explicit trial/arm binding, and shared result projection."""

from __future__ import annotations

import json
import re

from ciw.config import normalize_name
from ciw.models import Analysis, GroupValue, Locator, OutcomeResult, Trial, stable_id
from ciw.normalize.products import ProductResolver
from ciw.normalize.semantics import classify, parse_timepoint
from ciw.verify.crosscheck import CrosscheckFailed, ExtractionTask, crosscheck, task_id_for
from ciw.verify.quote import normalize
from ciw.verify.schemas import PublicationResultItem

INSTRUCTION = (
    "抽取本摘要明确报告的主要终点数值（单组统计量和来源报告的组间差均可）。"
    "不要从组均值重算调整差，不要按值正负号猜差值方向，不推断单位、组别或分析N。"
    "registry_id必须在摘要中明确出现，且本条明确属于该研究；多研究合报而数值未分配时不抽。"
    "arm_label/comparator_label用原文药名，单组数值comparator_label留空。"
    "overall/亚组人群分别保留在population，不从受试者总数或安全集推断分析N。"
    "difference的base_stat_type只按原文说明填写；contrast_direction只有原文明示药物减对照时才填写。"
    "quote必须是涵盖本条数值及人群、终点、时点的连续原文，可包含相邻方法句，不拼接。"
)
_FIELDS = tuple(PublicationResultItem.model_fields)
_NUMBERS = ("value", "ci_lower", "ci_upper", "ci_pct", "n")


def _task(paper: dict) -> ExtractionTask:
    instruction = INSTRUCTION + "本篇关联登记：" + ", ".join(paper["registry_ids"])
    return ExtractionTask(
        task_id_for(
            paper["source_sha"], json.dumps(PublicationResultItem.model_json_schema(), sort_keys=True), instruction
        ),
        paper["source_id"],
        paper["text"],
        instruction,
        PublicationResultItem,
        ("registry_id", "endpoint", "timepoint", "population", "stat_type", "arm_label", "comparator_label"),
        tuple(f for f in _FIELDS if f != "quote"),
        numeric_fields=_NUMBERS,
    )


def extract_publications(ws, cfg, papers, trials, resolver, roles) -> tuple[list[OutcomeResult], list[dict]]:
    results, issues, source_conflicts = [], [], set()
    for paper in papers:
        if paper["excluded_type"]:
            continue
        if roles is None:
            issues.append(dict(kind="publication_not_extracted", ref=paper["paper_id"], note="未启用异构模型核对"))
            continue
        task = _task(paper)
        try:
            checked = crosscheck(task, roles)
        except CrosscheckFailed as exc:
            issues.append(dict(kind="publication_extract_failed", ref=paper["paper_id"], note=str(exc)))
            continue
        for chk in checked:
            item = chk.item
            result, reason = _project(cfg, paper, trials, resolver, item, chk.status)
            key = stable_id("pub", paper["paper_id"], chk.key)
            ws.save_verification(
                key,
                chk.status,
                dict(
                    source_id=paper["source_id"],
                    task=task.task_id,
                    item=item,
                    calls=chk.calls,
                    note=chk.note or reason,
                ),
            )
            if chk.status == "needs_review" or reason:
                issues.append(
                    dict(
                        kind="publication_unbound" if reason else "publication_needs_review",
                        ref=key,
                        note=reason or chk.note,
                    )
                )
            elif result is not None:
                results.append(result)
                trial = trials[result.trial_id]
                if trial.trial_id not in source_conflicts and _registry_conflict(trial, resolver):
                    source_conflicts.add(trial.trial_id)
                    issues.append(
                        dict(
                            kind="registry_arm_relationship_conflict",
                            ref=trial.trial_id,
                            note="登记组名/角色与干预关联冲突；原文保留，论文按明确名称和角色绑定",
                        )
                    )
    return results, issues


def _match_arm(trial: Trial, label: str, resolver: ProductResolver):
    exact = [a for a in trial.arms if normalize_name(a.label) == normalize_name(label)]
    if len(exact) == 1:
        return exact[0]
    pid = resolver.resolve_intervention(label)
    # Explicit arm labels/verified aliases beat a contradictory intervention link.
    matches = (
        [
            a
            for a in trial.arms
            if resolver.resolve_intervention(a.label) == pid and a.role in {"experimental", "active_comparator"}
        ]
        if pid
        else []
    )
    if len(matches) == 1:
        return matches[0]
    matches = (
        [
            a
            for a in trial.arms
            if pid in a.product_ids
            and a.role in {"experimental", "active_comparator"}
            and resolver.resolve_intervention(a.label) in {None, pid}
        ]
        if pid
        else []
    )
    if len(matches) == 1:
        return matches[0]
    # A literal placebo label plus one explicitly registered placebo arm, never array order.
    if normalize_name(label) in {"placebo", "安慰剂"}:
        matches = [a for a in trial.arms if a.role == "placebo"]
        if len(matches) == 1:
            return matches[0]
    return None


def _group(arm, label: str, path: str, resolver, **values) -> GroupValue:
    pid = resolver.resolve_intervention(label) if arm.role != "placebo" else None
    if pid is None and arm.role in {"experimental", "active_comparator"} and len(arm.product_ids) == 1:
        pid = arm.product_ids[0]
    return GroupValue(
        group_id=arm.arm_id,
        arm_id=arm.arm_id,
        title=label,
        role=arm.role,
        product_id=pid,
        path=path,
        **values,
    )


def _project(cfg, paper, trials, resolver, item, status):
    if any(
        item[field] and normalize(item[field]) not in normalize(item["quote"])
        for field in ("unit", "population", "arm_label", "comparator_label")
    ):
        return None, "论文科学上下文未在引用中保留原文"
    tid = item["registry_id"].upper()
    matches = [
        t
        for t in trials.values()
        if tid in {t.trial_id, *(i.upper() for k, v in t.ids.items() if k in {"nct", "ctr"} for i in v.split(";"))}
    ]
    trial = matches[0] if len(matches) == 1 else None
    if tid not in paper["registry_ids"] or trial is None or trial.relevance != "core":
        return None, "论文数值未明确关联当前核心研究"
    arm = _match_arm(trial, item["arm_label"], resolver)
    if arm is None or arm.role == "unknown":
        return None, "论文组别未唯一匹配登记臂"
    contrast = item["stat_type"] in {"difference", "hazard_ratio", "odds_ratio"}
    ctrl = _match_arm(trial, item["comparator_label"], resolver) if contrast else None
    if contrast and (ctrl is None or ctrl.arm_id == arm.arm_id or ctrl.role == "unknown"):
        return None, "论文对照组未唯一匹配登记臂"
    groups = [
        _group(
            arm,
            item["arm_label"],
            paper["path"],
            resolver,
            value=None if contrast else item["value"],
            n=item.get("n"),
            lower=None if contrast else item.get("ci_lower"),
            upper=None if contrast else item.get("ci_upper"),
        )
    ]
    analyses = []
    if contrast:
        groups.append(_group(ctrl, item["comparator_label"], paper["path"], resolver))
        analyses = [_analysis(item, arm.arm_id, ctrl.arm_id, paper["path"])]
    domain, concept = classify(item["endpoint"], cfg)
    return OutcomeResult(
        result_id=stable_id("pubresult", paper["paper_id"], item),
        trial_id=trial.trial_id,
        outcome_index=-1,
        type=item["outcome_type"],
        title=item["endpoint"],
        description=_measurement_context(item),
        timeframe=item["timepoint"],
        time=parse_timepoint(item["timepoint"]),
        subgroup=item["population"],
        population=item["population"],
        concept_id=concept,
        domain=domain,
        measure_kind=item["base_stat_type"] if contrast else item["stat_type"],
        unit=item["unit"],
        groups=groups,
        analyses=analyses,
        status=status,
        kind="publication",
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{paper['paper_id']}/",
        locator=Locator(source_id=paper["source_id"], path=paper["path"], quote=item["quote"]),
    ), ""


def _measurement_context(item):
    endpoint = re.escape(item["endpoint"])
    match = re.search(
        r"(?:percent(?:age)?\s+)?change\s+(?:from baseline\s+(?:in|of)\s+"
        + endpoint
        + r"|in\s+"
        + endpoint
        + r"\s+from baseline)",
        item["quote"],
        re.I,
    )
    return match[0] if match else ""


def _registry_conflict(trial, resolver):
    for arm in trial.arms:
        label_pid = resolver.resolve_intervention(arm.label)
        if arm.role == "placebo" and arm.product_ids:
            return True
        if label_pid and arm.product_ids and label_pid not in arm.product_ids:
            return True
        if label_pid and arm.interventions and any(re.search(r"placebo|安慰剂", i, re.I) for i in arm.interventions):
            return True
    return False


def _analysis(item, arm, ctrl, path):
    direction = item["stat_type"] == "difference" and item["contrast_direction"] == "arm_minus_comparator"
    ordered, evidence = _reported_order(item) if not direction else (1, "")
    return Analysis(
        group_ids=[arm, ctrl],
        param_type=item["stat_type"],
        value=item["value"],
        value_raw=str(item["value"]),
        ci_lower=item.get("ci_lower"),
        ci_upper=item.get("ci_upper"),
        ci_pct=item.get("ci_pct"),
        path=path,
        minuend_group_id=arm if ordered == 1 else ctrl if ordered == -1 else None,
        subtrahend_group_id=ctrl if ordered == 1 else arm if ordered == -1 else None,
        direction_evidence=evidence,
    )


def _reported_order(item):
    if item["stat_type"] != "difference" or item["base_stat_type"] not in {"ls_mean", "mean"}:
        return 0, ""

    def match(a, b):
        return re.search(
            r"(?<!\w)"
            + re.escape(a)
            + r"\s+(?:vs\.?|versus)\s+"
            + re.escape(b)
            + r"\s+groups?\b(?:[^.;]|\.(?=\d)){0,180}?(?:LS mean difference|"
            r"least[- ]squares mean difference|mean difference)",
            item["quote"],
            re.I,
        )

    forward = match(item["arm_label"], item["comparator_label"])
    reverse = match(item["comparator_label"], item["arm_label"])
    if bool(forward) == bool(reverse):
        return 0, ""
    return (1, forward[0]) if forward else (-1, reverse[0])
