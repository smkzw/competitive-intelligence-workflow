"""PNH 首验：A 载荷真实派生构建脚本（LOOP 第十轮）。

从 .artifacts/source-cas/ctgov-live-20260906 两页原始 CAS 派生 A 门户载荷：
实体（干预→产品、NCT→试验、申办方→企业）、真实结果数值（58 条含
resultsSection 记录的 outcomeMeasures/不良事件）、来源区。未披露字段
一律"未公开披露"，不补造。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ci_workflow.application.source_research_service import (  # noqa: E402
    classify_source_outcome,
    ctgov_class_observation_timepoint,
)
from ci_workflow.reports.b.safety_concepts import (  # noqa: E402
    describe_safety_concept,
    safety_category_zh,
)

ROOT = Path(__file__).resolve().parents[2]
NA = "未公开披露"


_CLASS_TITLE_TOKENS = (
    ("proportion of subjects with", "受试者"),
    ("haemolytic event free status", "无溶血事件"),
    ("thrombotic event free status", "无血栓事件"),
    ("absence of transfusions", "无输血"),
    ("hemoglobin between", "血红蛋白"),
    ("neutralizing antibody positive postbaseline", "基线后中和抗体阳性"),
    ("binding antibody positive postbaseline", "基线后结合抗体阳性"),
    ("with negative/no result at baseline", "且基线阴性/无结果"),
    ("fatigue", "疲乏"),
    ("abdominal pain", "腹痛"),
    ("dyspnea", "呼吸困难"),
    ("dysphagia", "吞咽困难"),
    ("chest pain", "胸痛"),
    ("erectile dysfunction", "勃起功能障碍"),
    ("erectile", "勃起功能"),
    ("transfusion avoidance", "输血回避"),
    ("dysfunction", "障碍"),
    ("symptom scales", "症状量表"),
    ("total score", "总分"),
    ("at the eot", "治疗结束访视"),
    ("eot visit", "治疗结束访视"),
    ("maximum exposure", "最长暴露"),
    ("quality of life", "生活质量"),
    ("final study visit", "末次研究访视"),
    ("interim efficacy analysis", "期中疗效分析"),
    ("full analysis", "全分析集"),
    ("free complement 5", "游离补体C5"),
    ("total complement 5", "总补体C5"),
    ("serum free c5", "血清游离C5"),
    ("serum total c5", "血清总C5"),
    ("change at week", "第X周变化占位"),
    ("end of treatment", "治疗结束"),
    ("baseline", "基线"),
    ("moderate", "中度"),
    ("severe", "重度"),
    ("mild", "轻度"),
    ("none", "无"),
    ("change at", "变化"),
)


def _transcribe_class_title(title: str) -> str:
    """登记 class 标题的确定性中文转写：词汇级替换 + 时间归一。

    未命中词汇的保留登记原文（不做机器翻译式臆造）。
    """
    text = " ".join(str(title or "").split())
    if not text:
        return text
    # 时间归一无条件执行：Day/Week/Month N → 第N天/周/个月
    out = re.sub(r"[Dd]ay\s+(\d+)", r"第\1天", text)
    out = re.sub(r"[Ww]eek\s+(\d+)", r"第\1周", out)
    out = re.sub(r"[Mm]onth\s+(\d+)", r"第\1个月", out)
    out = re.sub(r"(\d+)\s*[Mm]onths?", r"\1个月", out)
    out = re.sub(r"[Cc]hange at\s+", "", out)
    low = out.casefold()
    changed = out != text
    for en, zh in _CLASS_TITLE_TOKENS:
        if en in low:
            changed = True
            idx = low.find(en)
            out = out[:idx] + zh + out[idx + len(en) :]
            low = out.casefold()
    if not changed:
        return text
    out = out.replace(" between ", "").replace("、", "、")
    out = re.sub(r"\s+at\s+", "（", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    if out.count("（") > out.count("）"):
        out += "）"
    # 归一后剩余裸英文词 ≥3 个则视为未转写成功，保留原文
    if len(re.findall(r"[A-Za-z]{4,}", out)) >= 3:
        return text
    return out


# 登记结果测量的互斥子类 → 中文行标签（独立复核第二十一轮 veto）
_REGISTRY_CATEGORY_ZH = {
    "improved from baseline": "较基线改善",
    "worsened from baseline": "较基线恶化",
    "no change from baseline": "较基线无变化",
    "no change": "较基线无变化",
    "not applicable": "不适用",
    "na": "不适用",
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="通用 A 载荷构建器")
    p.add_argument("--cas-dir", required=True, help="CAS 原始数据根目录")
    p.add_argument("--alias-map", required=True, help="别名映射 JSON")
    p.add_argument("--indication", required=True, help="适应症中文名")
    p.add_argument("--indication-id", required=True, help="适应症英文标识")
    p.add_argument("--output", required=True, help="输出 JSON 路径")
    p.add_argument("--cutoff", default="2026-09-06", help="数据截止日")
    return p.parse_args()


_args = _parse_args()
CAS = sorted(p for p in (Path(_args.cas_dir) / "evidence" / "raw").rglob("*.bin"))
OUT = Path(_args.output)
INDICATION = _args.indication
INDICATION_ID = _args.indication_id
CUTOFF_DATE = _args.cutoff

_STATUS_RANK = {
    "已批准上市": 8,
    "招募中": 75,
    "邀请入组中": 74,
    "进行中（不招募）": 73,
    "尚未招募": 6,
    "已完成": 5,
    "可用": 4,
    "不再可用": 3,
    "状态未更新": 2,
    "已暂停": 2,
    "已终止": 1,
    "已撤回": 0,
}
ALIAS = json.loads(Path(_args.alias_map).read_text(encoding="utf-8"))
NORMALIZED_ALIAS: dict[str, str] = {
    re.sub(r"[^a-z0-9]+", "", alias.lower()): str(canonical)
    for alias, canonical in ALIAS["canonical_by_alias"].items()
}
COMBO_RECORDS: list[dict[str, Any]] = []
NON_PRODUCT_RECORDS: list[str] = []
BORDERLINE: set[str] = set()

STATUS_MAP = {
    "RECRUITING": "招募中",
    "ACTIVE_NOT_RECRUITING": "进行中（不招募）",
    "COMPLETED": "已完成",
    "TERMINATED": "已终止",
    "WITHDRAWN": "已撤回",
    "NOT_YET_RECRUITING": "尚未招募",
    "SUSPENDED": "已暂停",
    "ENROLLING_BY_INVITATION": "邀请入组中",
    "UNKNOWN": "状态未更新",
    "AVAILABLE": "可用",
    "NO_LONGER_AVAILABLE": "不再可用",
    "APPROVED_FOR_MARKETING": "已批准上市",
}
PHASE_MAP = {
    "PHASE1": "I期",
    "PHASE2": "II期",
    "PHASE3": "III期",
    "PHASE1/PHASE2": "I/II期",
    "PHASE2/PHASE3": "II/III期",
    "PHASE4": "IV期",
    "NA": "未分期",
}


def slugify(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return text or "intervention"


def _linked_product_for_group(
    group_title: str, product_links: list[dict[str, Any]], focus_product_id: str,
) -> tuple[str, str]:
    declared = {
        str(link["product_id"])
        for link in product_links
        if group_title.strip().casefold() in {
            str(label).strip().casefold() for label in link["arm_labels"]
        }
    }
    if len(declared) == 1:
        return next(iter(declared)), "declared"
    return focus_product_id, "unknown"


def main() -> None:
    studies: list[tuple[dict[str, Any], int, int]] = []
    page_meta: list[tuple[int, str]] = []
    for page_index, path in enumerate(CAS):
        blob = path.read_bytes()
        data = json.loads(blob)
        page_meta.append((page_index + 1, hashlib.sha256(blob).hexdigest()))
        studies.extend((s, page_index + 1, i) for i, s in enumerate(data.get("studies", [])))

    trials_rows: list[dict[str, Any]] = []
    product_index: dict[str, dict[str, Any]] = {}
    company_rows: list[dict[str, Any]] = []
    efficacy_rows: list[dict[str, Any]] = []
    safety_rows: list[dict[str, Any]] = []
    dev_candidates: dict[str, list[tuple[bool, str]]] = {}
    enrollment_issues: list[dict[str, str]] = []
    denominator_conflicts: list[dict[str, str]] = []
    product_regions: dict[str, set[str]] = {}
    product_phase: dict[str, str] = {}
    product_status: dict[str, str] = {}
    seen_company = set()
    ei = si = 0
    SAFETY_DOMAIN_DIVERTED: list[dict[str, Any]] = []
    NON_EFFICACY_OBSERVATIONS: list[dict[str, Any]] = []
    ROW_SOURCE_MAP: list[dict[str, Any]] = []

    for study, page_no, array_index in studies:
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        nct = ident.get("nctId") or f"record-{page_no}-{array_index}"
        design = proto.get("designModule", {})
        status_mod = proto.get("statusModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
        arms_mod = proto.get("armsInterventionsModule", {})
        lead = (sponsor_mod.get("leadSponsor") or {}).get("name") or NA

        # R13-①过滤扩充：移植预处理/系统化疗/同位素标记/通用类/非独立方案。
        NON_PRODUCT_MARKERS = (
            "placebo",
            "normal saline",
            "imaging",
            "questionnaire",
            "blood draw",
            "blood sample",
            "sampling",
            "clinimacs",
            "conditioning regimen",
            "preparative regimen",
            "transplant",
            "allo sct",
            "ablative regimen",
            "supportive care",
            "standard of care",
            "granulocyte",
            "stem cell infusion",
            "chemotherapy",
            "carbon-14",
            "radiolabeled",
            "labeled ",
            "c5 inhibitor",
            "complement inhibitor",
            "anti-c5",
            "cyclophosphamide",
            "fludarabine",
            "busulfan",
            "alemtuzumab",
            "cyclosporine",
            "mycophenolate",
            "melphalan",
            "etoposide",
            "anti-thymocyte globulin",
            "phenylalanine mustard",
            "rituxan",
            "rabbit atg",
            "t-lymphocyte immune globulin",
            "muromonab",
            "orthoclone",
            "thioplex",
            "treosulfan",
            "sargramostim",
            "gm-csf",
            "g-csf",
            "filgrastim",
            "rituximab",
            "cell infusion",
            "infusion",
            "prednisone",
            "steroid",
            "glucocorticoid",
            "methylprednisolone",
            "campath",
            "basiliximab",
            "sirolimus",
            "tacrolimus",
            "methotrexate",
        )

        def _split_brand_combo(normalized_base: str) -> str | None:
            # R16-c 窄规则：连字符各段均为已知别名时归并为映射序首（如 soliris-ultomiris）。
            parts = [seg for seg in re.split(r"[-/]", normalized_base) if seg.strip()]
            if len(parts) >= 2 and all(
                re.sub(r"[^a-z0-9]+", "", seg) in NORMALIZED_ALIAS for seg in parts
            ):
                first_known = next(
                    NORMALIZED_ALIAS[re.sub(r"[^a-z0-9]+", "", seg)] for seg in parts
                )
                return first_known
            return None

        def _norm_drug(name: str, markers: tuple[str, ...] = NON_PRODUCT_MARKERS) -> str | None:
            lowered = name.lower().strip()
            if "sirolimus" in lowered or "levamisole" in lowered:
                return lowered  # R18-d 边界再定位候选：豁免黑名单，标 borderline 待纳排审查。
            if any(marker in lowered for marker in markers):
                return None
            if re.fullmatch(r"nct\d+", lowered):
                return None
            # R13-c 复合/制剂名称：取括号外主体再归一。
            base = re.sub(r"\s*\([^)]*\)\s*", " ", lowered).strip()
            base = re.sub(
                r"\b(injections?|infusions?|tablets?|capsules?|solutions?|"
                r"monotherapy|study drug|dose \d+|part ?\d+)\b",
                "",
                base,
            ).strip()
            # R17-c 剂量/频次尾部剔除（如 ntq5082 100mg qd）。
            base = re.sub(r"\b\d+\s*(mg|mcg|g|iu)\b.*$", "", base).strip()
            base = re.sub(r"\b(qd|bid|tid|q24h|q12h|q2w|q4w|q8w)\b", "", base).strip()
            # R17-e 冒号/Part 前缀残留清理。
            base = re.sub(r"^[\s:;,-]+", "", base).strip()
            base = re.sub(r"[\s:;,-]+$", "", base).strip()
            normalized = re.sub(r"[^a-z0-9]+", "", base)
            if not normalized:
                return None
            combo = _split_brand_combo(base)
            if combo is not None:
                return combo
            # R13-a 映射表键做同样归一，双侧一致。
            return NORMALIZED_ALIAS.get(normalized, base)

        raw_drugs = []
        for item in arms_mod.get("interventions", []) or []:
            name = str(item.get("name") or "").strip()
            itype = str(item.get("type") or "").upper()
            if not name or not ({"DRUG", "BIOLOGICAL"} & set(itype.split())):
                continue
            # R18-d 边界再定位方案不静默丢弃：恢复入宇宙并标 borderline 待纳排审查。
            if "sirolimus" in name.lower() or "levamisole" in name.lower():
                BORDERLINE.add(name.strip())
            # R15-b 中文分号/英文分号复合名切分为独立干预段。
            for segment in re.split(r"[;；]", name):
                normalized = _norm_drug(segment)
                if normalized:
                    raw_drugs.append(normalized)
        canonical_drugs = sorted(set(raw_drugs))
        arm_types = {
            str(arm.get("label") or "").strip(): str(arm.get("type") or "").upper()
            for arm in (arms_mod.get("armGroups") or [])
        }
        role_names = {
            "EXPERIMENTAL": "experimental",
            "ACTIVE_COMPARATOR": "active_comparator",
            "PLACEBO_COMPARATOR": "other_comparator",
            "SHAM_COMPARATOR": "other_comparator",
            "NO_INTERVENTION": "other",
            "OTHER": "other",
        }
        product_links: list[dict[str, Any]] = []
        for drug in canonical_drugs:
            by_role: dict[str, set[str]] = {}
            for intervention in arms_mod.get("interventions", []) or []:
                if not any(
                    _norm_drug(segment) == drug
                    for segment in re.split(r"[;；]", str(intervention.get("name") or ""))
                ):
                    continue
                for label in intervention.get("armGroupLabels") or []:
                    arm_label = str(label or "").strip()
                    role = role_names.get(arm_types.get(arm_label, ""), "unknown")
                    by_role.setdefault(role, set()).add(arm_label)
            if not by_role:
                by_role["unknown"] = set()
            for role in sorted(by_role):
                product_links.append({
                    "product_id": slugify(drug), "arm_role": role,
                    "arm_labels": sorted(by_role[role]),
                })

        experimental_drugs = sorted(
            drug for drug in canonical_drugs
            if any(link["product_id"] == slugify(drug)
                   and link["arm_role"] == "experimental" for link in product_links)
        )
        # The legacy single product_id is only a deterministic display focus;
        # product_links is the complete trial relationship, independent of
        # source intervention array order.
        if not canonical_drugs:
            NON_PRODUCT_RECORDS.append(nct)  # 记录明细，可审计
            continue
        product_name = (experimental_drugs or canonical_drugs)[0]
        # R13-f 联合治疗全记录（模型单 product_id 限制内的最诚实表达）。
        COMBO_RECORDS.append({"nct_id": nct, "canonical_drugs": canonical_drugs})
        pid = slugify(product_name)

        # Sponsor is not a developer of an active comparator or an intervention
        # with no source-declared arm relationship.
        for drug in canonical_drugs:
            drug_pid = slugify(drug)
            experimental = drug in experimental_drugs
            dev_candidates.setdefault(drug_pid, []).append(
                (drug_pid == pid and experimental, lead if lead != NA else "")
            )
            if drug_pid not in product_index:
                product_index[drug_pid] = {
                    "id": drug_pid,
                    "name": drug,
                    "target": NA,
                    "modality": NA,
                    "phase": "未标注",
                    "status": "状态未更新",
                    "regions": ["未登记地点"],
                    "route": NA,
                    "developer": NA,
                    "mechanism": NA,
                    "result_status": "暂无公开关键结果",
                }
        phases = design.get("phases") or []
        phase_zh = PHASE_MAP.get("/".join(phases), "未标注") if phases else "未标注"
        current = product_phase.get(pid)
        order = ["未标注", "未分期", "I期", "I/II期", "II期", "II/III期", "III期", "IV期"]
        if current is None or order.index(phase_zh) > order.index(current):
            product_phase[pid] = phase_zh
        status_zh = STATUS_MAP.get(status_mod.get("overallStatus", ""), "状态未更新")
        # R12-③状态优先级聚合：高等级胜，替代顺序覆盖。
        rank = _STATUS_RANK.get(status_zh, 0)
        prev = product_status.get(pid)
        if prev is None or rank > _STATUS_RANK.get(prev, 0):
            product_status[pid] = status_zh
        company_key = (pid, lead)
        if lead != NA and company_key not in seen_company:
            seen_company.add(company_key)
            company_rows.append(
                {
                    "product_id": pid,
                    "relationship": "申办方（登记信息）",
                    "licensor": lead,
                    "licensee": NA,
                    "territory": NA,
                    "transaction": "登记申办关系；交易条款未公开",
                }
            )
        locations_mod = proto.get("contactsLocationsModule", {}) or {}
        countries = sorted(
            {
                str(loc.get("country") or "").strip()
                for loc in (locations_mod.get("locations") or [])
                if loc.get("country")
            }
        )
        # 区域口径：仅 mainland China 计入"中国"；港台按境外处理（独立复核第十四轮）
        has_china = any(c.lower() == "china" for c in countries)
        trial_region = "中国" if has_china else ("境外" if countries else "未登记地点")
        if has_china:
            product_regions.setdefault(pid, set()).add("中国")
        elif countries:
            product_regions.setdefault(pid, set()).add("境外")

        enrollment = design.get("enrollmentInfo", {})
        count = enrollment.get("count") if isinstance(enrollment, dict) else None
        enrollment_type = (
            str(enrollment.get("type") or "").upper()
            if isinstance(enrollment, dict) else ""
        )
        if enrollment_type not in {"ACTUAL", "ESTIMATED"}:
            enrollment_type = "UNKNOWN"
        if type(count) is not int or count < 0:
            if count is not None:
                enrollment_issues.append({
                    "trial_id": nct, "reason": "invalid_enrollment_count",
                })
            count = None
        trials_rows.append({
            "id": nct.lower(), "display_id": nct, "product_id": pid,
            "product_links": product_links,
            "name": ident.get("briefTitle", nct)[:120],
            "phase": phase_zh, "region": trial_region, "status": status_zh,
            "sample_size": count if enrollment_type == "ACTUAL" else None,
            "planned_sample_size": count if enrollment_type == "ESTIMATED" else None,
            "reported_sample_size": count if enrollment_type == "UNKNOWN" else None,
            "enrollment_type": enrollment_type,
            "treatment_sample_size": None, "role": "登记研究",
        })

        results = study.get("resultsSection") or {}
        if results:
            # 独立复核修复：OG id 标题按 measure 级 groups 精确映射
            _om = results.get("outcomeMeasuresModule") or {}
            group_titles = {
                str(g.get("id")): str(g.get("title") or "组别未登记")
                for g in (_om.get("groups") or [])
            }
            # 多期间试验：OG 标题可能是不透明代码，用 flow 标题按序补全
            if not group_titles:
                flow_groups = (results.get("participantFlowModule") or {}).get("groups") or []
                for fg in flow_groups:
                    group_id = str(fg.get("id") or "").strip()
                    ft = str(fg.get("title") or "").strip()
                    if group_id and ft:
                        group_titles[group_id] = ft
            # 补充：AE eventGroups 标题（TP1/TP2/LTE 多期间区分）
            for eg in (results.get("adverseEventsModule") or {}).get("eventGroups") or []:
                eg_id = str(eg.get("id") or "")
                eg_title = str(eg.get("title") or "").strip()
                if eg_id and eg_title:
                    group_titles.setdefault(eg_id, eg_title)

            # Never pair opaque outcome-group IDs with protocol arms by array position.
            outcome_measures = (
                (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
            )
            for measure_index, measure in enumerate(outcome_measures):
                # 独立测试第二轮（UC）：不得截断登记终点标题——截断会
                # 摧毁 Mayo/时间窗等尾部语义并造成分类漏检
                title = str(measure.get("title") or "").strip() or NA
                time_frame = str(measure.get("timeFrame") or "").strip() or "时间窗未登记"
                # 独立复核 A r22（issue-5）：组别标题优先取自测量自带 groups
                for g in measure.get("groups") or []:
                    gid = str(g.get("id") or "").strip()
                    gtitle = str(g.get("title") or "").strip()
                    if gid and gtitle:
                        # The measure's group title is more specific than the
                        # trial-level title for multi-period observations.
                        group_titles[gid] = gtitle

                unit = str(measure.get("unitOfMeasure") or "") or "值"
                denominator_by_group: dict[str, int] = {}
                conflicting_denominator_groups: set[str] = set()
                denominator_candidates: dict[str, list[dict[str, Any]]] = {}
                for denom_index, denom in enumerate(measure.get("denoms") or []):
                    for count_index, count in enumerate(denom.get("counts") or []):
                        group_id = str(count.get("groupId") or "").strip()
                        raw_count = count.get("value")
                        if group_id:
                            denominator_candidates.setdefault(group_id, []).append({
                                "value_path": (
                                    "$.resultsSection.outcomeMeasuresModule.outcomeMeasures"
                                    f"[{measure_index}].denoms[{denom_index}]"
                                    f".counts[{count_index}].value"
                                ),
                                "raw_value": raw_count,
                                "raw_value_type": type(raw_count).__name__,
                                "param_type": denom.get("paramType"),
                                "unit": denom.get("unitOfMeasure"),
                            })
                        if not group_id or isinstance(raw_count, bool):
                            continue
                        try:
                            count_value = int(str(raw_count))
                        except (TypeError, ValueError):
                            continue
                        if count_value > 0 and group_id not in conflicting_denominator_groups:
                            if group_id in denominator_by_group and (
                                denominator_by_group[group_id] != count_value
                            ):
                                conflicting_denominator_groups.add(group_id)
                                denominator_by_group.pop(group_id)
                                denominator_conflicts.append({
                                    "trial_id": nct.lower(), "endpoint": title,
                                    "group_id": group_id,
                                })
                                continue
                            denominator_by_group[group_id] = count_value
                for class_index, cls in enumerate(measure.get("classes") or []):
                    # 独立复核修复：携带分析集标签（Interim/Full Analysis 等），
                    # 同终点的不同分析集行并列呈现，口径不再被压成单一标签
                    cls_title = str(cls.get("title") or "").strip()
                    source_class_title = cls_title
                    # 仅明确单一访视覆盖测量时间窗；"from baseline" 是
                    # 比较基准，不是 Baseline 访视。
                    row_time_frame = ctgov_class_observation_timepoint(cls_title) or time_frame
                    # 独立视觉复核（A copy_zh）：class 原文英文不得嵌入
                    # 中文 population 行；词汇级确定性转写，未命中保留原文
                    cls_title = _transcribe_class_title(cls_title)
                    base_population = (
                        f"登记结果人群（{cls_title}）" if cls_title else "登记结果人群"
                    )
                    for category_index, cat in enumerate(cls.get("categories") or []):
                        # 独立复核第二十一轮 veto：登记测量的互斥子类
                        # （如 Improved/Worsened from Baseline）必须进入行标签，
                        # 否则同臂同测量的 4 行同名并列，数值含义无法还原
                        cat_title = str(cat.get("title") or "").strip()
                        cat_label = _REGISTRY_CATEGORY_ZH.get(cat_title.casefold(), cat_title)
                        if cat_label:
                            population = (
                                base_population[:-1] + f"；{cat_label}）"
                                if base_population.endswith("）")
                                else f"{base_population}（{cat_label}）"
                            )
                        else:
                            population = base_population
                        for measurement_index, measurement in enumerate(
                            cat.get("measurements") or []
                        ):
                            raw_source_value = measurement.get("value")
                            raw = (
                                str(raw_source_value).strip()
                                if raw_source_value is not None else ""
                            )
                            try:
                                value = float(raw)
                            except ValueError:
                                continue
                            group_id = str(measurement.get("groupId") or "")
                            group_title = group_titles.get(group_id, group_id or "组别未登记")
                            row_product_id, assignment_state = _linked_product_for_group(
                                group_title, product_links, pid,
                            )
                            source_path = (
                                "$.resultsSection.outcomeMeasuresModule.outcomeMeasures"
                                f"[{measure_index}].classes[{class_index}].categories"
                                f"[{category_index}].measurements[{measurement_index}].value"
                            )
                            source_atom = {
                                "trial_id": nct.lower(),
                                "source_page_sha256": page_meta[page_no - 1][1],
                                "source_url": f"https://clinicaltrials.gov/study/{nct}",
                                "value_path": source_path,
                                "raw_value": raw_source_value,
                                "raw_value_type": type(raw_source_value).__name__,
                                "raw_unit": unit,
                                "outcome_title": title,
                                "class_title": source_class_title,
                                "category_title": cat_title,
                                "group_id": group_id,
                                "group_title": group_title,
                                "timepoint": row_time_frame,
                                "denominator_candidates": denominator_candidates.get(
                                    group_id, [],
                                ),
                            }
                            domain = classify_source_outcome(
                                title, source_class_title, cat_title,
                            )
                            if domain not in {"efficacy", "adverse_events"}:
                                other_row_id = "other-" + hashlib.sha256(
                                    f"{nct}|{source_path}".encode()
                                ).hexdigest()[:16]
                                NON_EFFICACY_OBSERVATIONS.append({
                                    "row_id": other_row_id,
                                    "trial_id": nct.lower(), "product_id": row_product_id,
                                    "group_id": group_id, "group_title": group_title,
                                    "group_assignment_state": assignment_state,
                                    "endpoint": title, "class_title": source_class_title,
                                    "category_title": cat_title, "time_window": row_time_frame,
                                    "domain": domain, "raw_value": raw,
                                    "raw_value_type": type(raw_source_value).__name__,
                                    "raw_unit": unit,
                                    "source_url": f"https://clinicaltrials.gov/study/{nct}",
                                    "source_page_sha256": page_meta[page_no - 1][1],
                                    "source_path": source_path,
                                })
                                ROW_SOURCE_MAP.append({
                                    "domain": "additional_observations",
                                    "row_id": other_row_id, **source_atom,
                                })
                                continue
                            # 会商 P0 #2（域分流）：安全域终点不得混入疗效表——
                            # TEAE/AE 类测量在安全域保留独立统计对象和来源语境。
                            if domain == "adverse_events":
                                semantic = describe_safety_concept(title)
                                unit_lower = unit.strip().casefold()
                                if unit_lower in {"participants", "participant"}:
                                    display_unit, measure_object = "人", "participant_count"
                                elif unit_lower in {"events", "event"}:
                                    display_unit, measure_object = "次", "event_count"
                                elif "percentage" in unit_lower and "participant" in unit_lower:
                                    display_unit, measure_object = "%", "participant_proportion"
                                else:
                                    display_unit, measure_object = unit, "adjusted_estimate"
                                safety_count: int | None = (
                                    int(value) if measure_object == "participant_count"
                                    and value.is_integer() else None
                                )
                                safety_denominator: int | None = denominator_by_group.get(group_id)
                                if (
                                    semantic.count_basis == "mixed"
                                    or safety_count is None or safety_denominator is None
                                    or not 0 <= safety_count <= safety_denominator
                                ):
                                    safety_count = safety_denominator = None
                                si += 1
                                safety_rows.append({
                                    "row_id": f"safe-{si}", "product_id": row_product_id,
                                    "trial_id": nct.lower(),
                                    "arm": group_title,
                                    "group_assignment_state": assignment_state,
                                    "group_id": group_id or None,
                                    "category": safety_category_zh(semantic.key),
                                    "term": title,
                                    "term_key": semantic.key,
                                    "polarity": semantic.polarity,
                                    "grade_set": list(semantic.grade_set),
                                    "seriousness": semantic.seriousness,
                                    "teae": semantic.teae,
                                    "relatedness": semantic.relatedness,
                                    "parent": semantic.parent,
                                    "children": list(semantic.children),
                                    "count_basis": semantic.count_basis,
                                    "at_risk_stat": semantic.at_risk_stat,
                                    "measure_context": "；".join(
                                        part for part in (cls_title, cat_label) if part
                                    ) or None,
                                    "source_class_title": source_class_title or None,
                                    "source_category_title": cat_title or None,
                                    "value": value,
                                    "unit": display_unit,
                                    "measure_object": measure_object,
                                    "numerator": safety_count,
                                    "denominator": safety_denominator,
                                    "time_window": row_time_frame,
                                })
                                ROW_SOURCE_MAP.append({
                                    "domain": "safety", "row_id": f"safe-{si}",
                                    **source_atom,
                                })
                                SAFETY_DOMAIN_DIVERTED.append(
                                    {
                                        "trial_id": nct.lower(),
                                        "endpoint": title,
                                        "value": value,
                                        "timepoint": row_time_frame,
                                        "safety_row_id": f"safe-{si}",
                                    }
                                )
                                continue
                            ei += 1
                            efficacy_rows.append(
                                {
                                    "row_id": f"eff-{ei}",
                                    "product_id": row_product_id,
                                    "trial_id": nct.lower(),
                                    "endpoint": title,
                                    "arm": group_title,
                                    "group_assignment_state": assignment_state,
                                    "group_id": group_id or None,
                                    "value": value,
                                    "unit": unit,
                                    "population": population,
                                    "timepoint": row_time_frame,
                                    "denominator": denominator_by_group.get(group_id),
                                }
                            )
                            ROW_SOURCE_MAP.append({
                                "domain": "efficacy", "row_id": f"eff-{ei}",
                                **source_atom,
                            })
            # 会商 P0 #3（矩阵三轴）：治疗臂样本量从 participantFlow
            # Started 里程碑数提取，喂饱矩阵气泡图的样本量轴
            _flow_groups = (results.get("participantFlowModule") or {}).get("groups") or []
            _arm_types = {
                str(a.get("label") or "").strip(): str(a.get("type") or "").upper()
                for a in (
                    study.get("protocolSection", {}).get("armsInterventionsModule", {}) or {}
                ).get("armGroups")
                or []
            }
            _treatment_n = 0
            for _g in _flow_groups:
                if _arm_types.get(str(_g.get("title") or "").strip()) != "EXPERIMENTAL":
                    continue
                for _ms in _g.get("milestones") or []:
                    if str(_ms.get("type")) == "Started" and isinstance(
                        _ms.get("numSubjects"), int
                    ):
                        _treatment_n += _ms["numSubjects"]
            if _treatment_n > 0 and trials_rows[-1]["id"] == nct.lower():
                actual_n = trials_rows[-1]["sample_size"]
                if actual_n is None or _treatment_n <= actual_n:
                    trials_rows[-1]["treatment_sample_size"] = _treatment_n
                else:
                    enrollment_issues.append({
                        "trial_id": nct, "reason": "arm_n_exceeds_actual_enrollment",
                    })
            ae_module = results.get("adverseEventsModule") or {}
            events = ae_module.get("eventGroups") or []
            ae_time_window = str(ae_module.get("timeFrame") or "收集时间窗未登记").strip()
            for group_index, group in enumerate(events):
                arm_title = str(group.get("title") or "登记组别未提供")
                row_product_id, assignment_state = _linked_product_for_group(
                    arm_title, product_links, pid,
                )
                for affected_field, at_risk_field, category, concept, term, seriousness in (
                    (
                        "seriousNumAffected", "seriousNumAtRisk", "严重不良事件（登记）",
                        "any_sae", "严重不良事件组别汇总计数", "serious",
                    ),
                    (
                        "deathsNumAffected", "deathsNumAtRisk", "死亡病例（登记）",
                        "death", "死亡病例组别汇总计数", "unspecified",
                    ),
                ):
                    affected = group.get(affected_field)
                    if type(affected) is not int or affected < 0:
                        continue  # 缺失不是零，死亡字段也不依赖 SAE 字段存在。
                    at_risk = group.get(at_risk_field)
                    valid_denominator = (
                        type(at_risk) is int and at_risk > 0 and affected <= at_risk
                    )
                    si += 1
                    safety_rows.append(
                        {
                            "row_id": f"safe-{si}",
                            "product_id": row_product_id,
                            "trial_id": nct.lower(),
                            "arm": arm_title,
                            "group_assignment_state": assignment_state,
                            "group_id": str(group.get("id") or "") or None,
                            "category": category,
                            "term_key": concept,
                            "term": term,
                            "polarity": "affirmed",
                            "seriousness": seriousness,
                            "count_basis": "participants",
                            "at_risk_stat": "serious" if concept == "any_sae" else "deaths",
                            "value": affected,
                            "unit": "人",
                            "measure_object": "participant_count",
                            "numerator": affected if valid_denominator else None,
                            "denominator": at_risk if valid_denominator else None,
                            "time_window": ae_time_window,
                        }
                    )
                    at_risk_candidate = ([{
                        "value_path": (
                            "$.resultsSection.adverseEventsModule.eventGroups"
                            f"[{group_index}].{at_risk_field}"
                        ),
                        "raw_value": at_risk,
                        "raw_value_type": type(at_risk).__name__,
                    }] if at_risk is not None else [])
                    ROW_SOURCE_MAP.append({
                        "domain": "safety", "row_id": f"safe-{si}",
                        "trial_id": nct.lower(),
                        "source_page_sha256": page_meta[page_no - 1][1],
                        "source_url": f"https://clinicaltrials.gov/study/{nct}",
                        "value_path": (
                            "$.resultsSection.adverseEventsModule.eventGroups"
                            f"[{group_index}].{affected_field}"
                        ),
                        "raw_value": affected,
                        "raw_value_type": type(affected).__name__,
                        "raw_unit": "participants",
                        "outcome_title": term,
                        "class_title": None,
                        "category_title": None,
                        "group_id": str(group.get("id") or ""),
                        "group_title": arm_title,
                        "timepoint": ae_time_window,
                        "denominator_candidates": at_risk_candidate,
                    })

    # 独立复核修复（第十二轮）：研发企业两段式归属——
    # 主产品试验的申办方优先，其次试验药物臂的申办方，对照臂申办方不计。
    for dp, cands in dev_candidates.items():
        if dp not in product_index or not cands:
            continue
        primary_lead = next((lead for is_p, lead in cands if is_p and lead), None)
        experimental_lead = next((lead for is_e, lead in cands if is_e and lead), None)
        chosen_lead = primary_lead or experimental_lead
        if chosen_lead:
            product_index[dp]["developer"] = chosen_lead
    for pid, phase in product_phase.items():
        product_index[pid]["phase"] = phase
    for pid, status in product_status.items():
        product_index[pid]["status"] = status
    # R12-④产品区域=其试验地点并集（真实派生）。
    for pid, regions in product_regions.items():
        if pid in product_index:
            product_index[pid]["regions"] = sorted(regions)
    # R16-d 仅对确有结果行的产品设置结果状态。
    products_with_results = {row["product_id"] for row in efficacy_rows} | {
        row["product_id"] for row in safety_rows
    }
    for pid in products_with_results:
        if pid in product_index:
            product_index[pid]["result_status"] = "已有部分公开结果"

    payload = {
        "schema_version": "1.0",
        "report_version": "v1",
        "indication": INDICATION,
        "data_cutoff": f"{CUTOFF_DATE}T23:59:59.999999+08:00",
        "products": list(product_index.values()),
        "trials": trials_rows,
        "efficacy": efficacy_rows,
        "safety": safety_rows,
        "additional_observations": NON_EFFICACY_OBSERVATIONS,
        "regulatory": [
            {
                "product_id": next(iter(product_index)),
                "track": "中国",
                "event": "监管状态",
                "date": "2026-09-06",
                "status": "未公开披露（监管路线来源接入待后续版本开放）",
            }
        ],
        "companies": company_rows
        or [
            {
                "product_id": next(iter(product_index)),
                "relationship": "申办方",
                "licensor": NA,
                "licensee": NA,
                "territory": NA,
                "transaction": "未公开披露",
            }
        ],
        "patents": [
            {
                "product_id": next(iter(product_index)),
                "family": NA,
                "display_family": "专利路线来源接入待后续版本开放",
                "jurisdiction": NA,
                "scope": NA,
                "expiry": NA,
                "exclusivity": NA,
            }
        ],
        "history": [
            {
                "product_id": next(iter(product_index)),
                "status": "登记检索完成",
                "date": CUTOFF_DATE,
                # 独立测试第二轮（UC）：检索统计与排除明细从本运行真实派生，
                # 不得携带 PNH 轮次的固定数字与内部流程代号
                "observation": (
                    f"CT.gov 当前记录检索共 {sum(1 for _ in CAS)} 页原始响应："
                    f"{len(trials_rows)} 条研究入表（含样本量未知或明确零值）；"
                    f"{len(enrollment_issues)} 条样本量来源问题留待核查；"
                    f"{len(NON_PRODUCT_RECORDS)} 条无独立药物干预未产出实体"
                    "（明细见派生记录）；"
                    "联合治疗组合完整记录于派生记录；中国路线访问受阻已如实记档；"
                    "监管/专利来源接入待后续版本开放"
                ),
            }
        ],
        "sources": [
            {
                "source": "ClinicalTrials.gov",
                "scope": f"{INDICATION}当前记录检索（{len(page_meta)} 页原始响应 SHA-256 绑定）",
                "maturity": "官方登记当前记录",
                "limitation": "当前记录口径，非历史 as-of 还原",
            },
            {
                "source": "PubMed",
                "scope": (
                    f"{INDICATION}治疗文献检索回执未纳入当前工作区绑定"
                    "（计数与分类属性以检索回执为准，不在载荷中虚构）"
                ),
                "maturity": "not_bound",
                "limitation": "文献层证据未接入当前载荷，相关叙事仅来自登记来源",
            },
        ],
        "derivation": {
            "pages": [{"page": page, "sha256": sha} for page, sha in page_meta],
            "built_at": datetime.now(UTC).isoformat(),
        },
    }
    derivation = payload.pop("derivation")
    derivation["enrollment_issues"] = enrollment_issues
    derivation["denominator_conflicts"] = denominator_conflicts
    # 会商 P0 #2：安全域分流审计计数（TEAE/AE 类测量不再混入疗效表）
    derivation["safety_domain_diverted"] = len(SAFETY_DOMAIN_DIVERTED)
    derivation["non_efficacy_observations"] = NON_EFFICACY_OBSERVATIONS
    derivation["row_source_map"] = ROW_SOURCE_MAP
    derivation["safety_domain_diverted_samples"] = [
        {k: str(v)[:80] for k, v in item.items()} for item in SAFETY_DOMAIN_DIVERTED[:10]
    ]
    derivation["records_without_drug_intervention"] = NON_PRODUCT_RECORDS
    derivation["combo_regimens"] = COMBO_RECORDS
    derivation["alias_map_id"] = ALIAS["map_id"]
    derivation["borderline_repositioning"] = sorted(BORDERLINE)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    sidecar = OUT.with_name(OUT.stem + ".derivation.json")
    sidecar.write_text(json.dumps(derivation, ensure_ascii=False, indent=1), encoding="utf-8")
    print("products:", len(payload["products"]), "| trials:", len(trials_rows))
    print("efficacy rows:", len(efficacy_rows), "| safety rows:", len(safety_rows))
    print("companies:", len(company_rows), "| bytes:", OUT.stat().st_size)


if __name__ == "__main__":
    main()
