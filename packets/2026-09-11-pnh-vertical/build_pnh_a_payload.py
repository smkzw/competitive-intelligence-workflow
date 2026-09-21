"""PNH 首验：A 载荷真实派生构建脚本（LOOP 第十轮）。

从 .artifacts/source-cas/ctgov-live-20260906 两页原始 CAS 派生 A 门户载荷：
实体（干预→产品、NCT→试验、申办方→企业）、真实结果数值（58 条含
resultsSection 记录的 outcomeMeasures/不良事件）、来源区。未披露字段
一律"未公开披露"，不补造。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / "src"))
from ci_workflow.reports.b.registry_observation import is_safety_domain_endpoint
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAS = sorted(
    p for p in (ROOT / ".artifacts/source-cas/ctgov-live-20260906/evidence/raw").rglob("*.bin")
)
OUT = Path(__file__).resolve().parent / "pnh-a-payload.json"
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
            out = out[:idx] + zh + out[idx + len(en):]
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


_STATUS_RANK = {
    "已批准上市": 8, "招募中": 75, "邀请入组中": 74, "进行中（不招募）": 73,
    "尚未招募": 6, "已完成": 5, "可用": 4, "不再可用": 3, "状态未更新": 2,
    "已暂停": 2, "已终止": 1, "已撤回": 0,
}
ALIAS = json.loads(
    (Path(__file__).resolve().parent / "pnh-alias-map-v1.json").read_text(encoding="utf-8")
)
NORMALIZED_ALIAS = {
    re.sub(r"[^a-z0-9]+", "", alias): canonical
    for alias, canonical in ALIAS["canonical_by_alias"].items()
}
COMBO_RECORDS: list[dict] = []
NON_PRODUCT_RECORDS: list[str] = []
BORDERLINE: set[str] = set()

STATUS_MAP = {
    "RECRUITING": "招募中", "ACTIVE_NOT_RECRUITING": "进行中（不招募）",
    "COMPLETED": "已完成", "TERMINATED": "已终止", "WITHDRAWN": "已撤回",
    "NOT_YET_RECRUITING": "尚未招募", "SUSPENDED": "已暂停",
    "ENROLLING_BY_INVITATION": "邀请入组中", "UNKNOWN": "状态未更新",
    "AVAILABLE": "可用", "NO_LONGER_AVAILABLE": "不再可用",
    "APPROVED_FOR_MARKETING": "已批准上市",
}
PHASE_MAP = {
    "PHASE1": "I期", "PHASE2": "II期", "PHASE3": "III期",
    "PHASE1/PHASE2": "I/II期", "PHASE2/PHASE3": "II/III期", "PHASE4": "IV期",
    "NA": "未分期",
}


def slugify(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return text or "intervention"


def main() -> None:
    studies = []
    page_meta = []
    for page_index, path in enumerate(CAS):
        blob = path.read_bytes()
        data = json.loads(blob)
        page_meta.append((page_index + 1, hashlib.sha256(blob).hexdigest()))
        studies.extend(
            (s, page_index + 1, i) for i, s in enumerate(data.get("studies", []))
        )

    trials_rows, product_index, company_rows, efficacy_rows, safety_rows = [], {}, [], [], []
    dev_candidates: dict[str, list[tuple[bool, str]]] = {}
    skipped_trials: list[str] = []
    product_regions: dict[str, set[str]] = {}
    product_phase, product_status = {}, {}
    seen_company = set()
    ei = si = 0
    SAFETY_DOMAIN_DIVERTED: list = []

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
            "placebo", "normal saline", "imaging", "questionnaire",
            "blood draw", "blood sample", "sampling", "clinimacs",
            "conditioning regimen", "preparative regimen", "transplant",
            "allo sct", "ablative regimen", "supportive care", "standard of care",
            "granulocyte", "stem cell infusion", "chemotherapy",
            "carbon-14", "radiolabeled", "labeled ", "c5 inhibitor",
            "complement inhibitor", "anti-c5",
            "cyclophosphamide", "fludarabine", "busulfan", "alemtuzumab",
            "cyclosporine", "mycophenolate", "melphalan", "etoposide",
            "anti-thymocyte globulin", "phenylalanine mustard", "rituxan",
            "rabbit atg", "t-lymphocyte immune globulin", "muromonab", "orthoclone",
            "thioplex", "treosulfan", "sargramostim", "gm-csf",
            "g-csf", "filgrastim", "rituximab", "cell infusion", "infusion",
            "prednisone", "steroid", "glucocorticoid", "methylprednisolone",
            "campath", "basiliximab", "sirolimus", "tacrolimus", "methotrexate",
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

        def _norm_drug(name: str) -> str | None:
            lowered = name.lower().strip()
            if "sirolimus" in lowered or "levamisole" in lowered:
                return lowered  # R18-d 边界再定位候选：豁免黑名单，标 borderline 待纳排审查。
            if any(marker in lowered for marker in NON_PRODUCT_MARKERS):
                return None
            if re.fullmatch(r"nct\d+", lowered):
                return None
            # R13-c 复合/制剂名称：取括号外主体再归一。
            base = re.sub(r"\s*\([^)]*\)\s*", " ", lowered).strip()
            base = re.sub(r"\b(injections?|infusions?|tablets?|capsules?|solutions?|monotherapy|study drug|dose \d+|part ?\d+)\b", "", base).strip()
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
        # R16-a 保持来源干预顺序：主药=记录中首个真实干预（排序曾致 LFG316→iptacopan 错投影）。
        seen_order: list[str] = []
        for drug in raw_drugs:
            if drug not in seen_order:
                seen_order.append(drug)
        canonical_drugs = sorted(set(raw_drugs))
        product_name = seen_order[0] if seen_order else None
        if product_name is None:
            NON_PRODUCT_RECORDS.append(nct)  # 记录明细，可审计
            continue
        # R13-f 联合治疗全记录（模型单 product_id 限制内的最诚实表达）。
        COMBO_RECORDS.append({"nct_id": nct, "canonical_drugs": canonical_drugs})
        pid = slugify(product_name)
        # 独立复核修复（第十二轮）：研发企业归属按臂类型判定——
        # 仅当药物在本试验的 EXPERIMENTAL 臂时，申办方才可作为其研发企业；
        # 对照药/背景治疗药物的申办方不是该药物的研发企业。
        def _drug_experimental(drug_name: str) -> bool:
            arm_type = {
                str(a.get("label") or "").strip(): str(a.get("type") or "").upper()
                for a in (proto.get("armsInterventionsModule", {}).get("armGroups") or [])
            }
            for iv in (proto.get("armsInterventionsModule", {}).get("interventions") or []):
                for segment in re.split(r"[;；]", str(iv.get("name") or "")):
                    if _norm_drug(segment) == drug_name:
                        labels = [str(l or "").strip() for l in (iv.get("armGroupLabels") or [])]
                        types = [arm_type.get(l, "") for l in labels]
                        if types:
                            return any(t == "EXPERIMENTAL" for t in types)
            return True  # 无臂结构可判定时保守视为试验药物

        # R15-a 每个真实药物干预都注册产品实体（试验行仍归首项，G11-1 限制）。
        for drug in canonical_drugs:
            drug_pid = slugify(drug)
            experimental = _drug_experimental(drug)
            # 研发企业候选：主产品试验优先，其次试验药物臂，对照臂不计
            dev_candidates.setdefault(drug_pid, []).append(
                (drug_pid == pid and experimental, lead if lead != NA else ""))
            if drug_pid not in product_index:
                product_index[drug_pid] = {
                    "id": drug_pid, "name": drug, "target": NA, "modality": NA,
                    "phase": "未标注", "status": "状态未更新",
                    "regions": ["未登记地点"], "route": NA, "developer": NA,
                    "mechanism": NA, "result_status": "暂无公开关键结果",
                }
        dev_candidates.setdefault(pid, []).append(
            (_drug_experimental(product_name), lead if lead != NA else ""))
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
            company_rows.append({
                "product_id": pid, "relationship": "申办方（登记信息）",
                "licensor": lead, "licensee": NA, "territory": NA,
                "transaction": "登记申办关系；交易条款未公开",
            })
        locations_mod = proto.get("contactsLocationsModule", {}) or {}
        countries = sorted({
            str(loc.get("country") or "").strip()
            for loc in (locations_mod.get("locations") or [])
            if loc.get("country")
        })
        # 区域口径：仅 mainland China 计入"中国"；港台按境外处理（独立复核第十四轮）
        has_china = any(c.lower() == "china" for c in countries)
        trial_region = "中国" if has_china else ("境外" if countries else "未登记地点")
        if has_china:
            product_regions.setdefault(pid, set()).add("中国")
        elif countries:
            product_regions.setdefault(pid, set()).add("境外")

        enrollment = design.get("enrollmentInfo", {})
        count = enrollment.get("count") if isinstance(enrollment, dict) else None
        # G10-1：A 试验模型 sample_size 强制 gt=0，登记未披露样本量的试验暂不入表，
        # 数量在 history/limitation 显式记录，不填造假值。
        if not isinstance(count, int) or count <= 0:
            skipped_trials.append(nct)
        else:
            trials_rows.append({
                "id": nct.lower(), "display_id": nct, "product_id": pid,
                "name": ident.get("briefTitle", nct), "phase": phase_zh,
                "region": trial_region, "status": status_zh,
                "sample_size": count,
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
                protocol_arms = (study.get("protocolSection", {}).get("armsInterventionsModule", {})
                                 .get("armGroups")) or []
                for idx, fg in enumerate(flow_groups):
                    ft = str(fg.get("title") or "").strip()
                    if ft:
                        group_titles[str(fg.get("id") or f"OG{idx:04d}")] = ft
                    elif idx < len(protocol_arms):
                        at = str((protocol_arms[idx] or {}).get("label") or "").strip()
                        if at:
                            group_titles[str(fg.get("id") or f"OG{idx:04d}")] = at
            # 补充：AE eventGroups 标题（TP1/TP2/LTE 多期间区分）
            for eg in (results.get("adverseEventsModule") or {}).get("eventGroups") or []:
                eg_id = str(eg.get("id") or "")
                eg_title = str(eg.get("title") or "").strip()
                if eg_id and eg_title:
                    group_titles.setdefault(eg_id, eg_title)
            # 独立复核修复（arm 标签）：结果段组 id 为不透明代码（OG001 等）时，
            # 依次用 participantFlow 组、协议 armGroups 的描述性标题按顺序补全。
            def _opaque_title(value: str) -> bool:
                t = value.strip()
                return (not t) or bool(re.fullmatch(r"[A-Za-z]{0,3}\d{2,4}", t))
            om_measures = (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
            om_group_ids: list[str] = []
            for measure in om_measures[:1]:
                for cls in (measure.get("classes") or [])[:1]:
                    for cat in (cls.get("categories") or [])[:2]:
                        for measurement in (cat.get("measurements") or []):
                            gid = str(measurement.get("groupId") or "")
                            if gid and gid not in om_group_ids:
                                om_group_ids.append(gid)
            replacement = None
            flow_groups = (results.get("participantFlowModule") or {}).get("groups", []) or []
            flow_titles = [str(g.get("title") or "").strip() for g in flow_groups]
            protocol_arms = (study.get("protocolSection", {}).get("armsInterventionsModule", {})
                             .get("armGroups")) or []
            arm_labels = [str(a.get("label") or "").strip() for a in protocol_arms]
            if om_group_ids and all(_opaque_title(group_titles.get(gid, "")) for gid in om_group_ids):
                if len(flow_titles) == len(om_group_ids) and any(flow_titles):
                    replacement = flow_titles
                elif len(arm_labels) == len(om_group_ids) and any(arm_labels):
                    replacement = arm_labels
            if replacement:
                for gid, title in zip(om_group_ids, replacement):
                    if title:
                        group_titles[gid] = title
            for measure in ((results.get("outcomeMeasuresModule") or {})
                            .get("outcomeMeasures") or []):
                title = str(measure.get("title") or "").strip() or NA
                time_frame = str(measure.get("timeFrame") or "").strip() or "时间窗未登记"                # 独立复核 A r22（issue-5）：组别标题优先取自测量自带 groups（OG 代码 → 登记标题）
                for g in (measure.get("groups") or []):
                    gid = str(g.get("id") or "").strip()
                    gtitle = str(g.get("title") or "").strip()
                    if gid and gtitle:
                        # 独立复核 B r41：测量级组标题优先于试验级 OG 表，
                        # 消除多期间试验 TP1/TP2 组名错位（测量级更具体）
                        group_titles[gid] = gtitle

                unit = str(measure.get("unitOfMeasure") or "") or "值"
                # 独立复核 A r27（issue-3）：测量级 denoms 提供各组分母
                # （如 LNP023 组 40 人），入行的 denominator 供人数列呈现
                _denom_by_group = {}
                for _d in (measure.get("denoms") or []):
                    for _c in (_d.get("counts") or []):
                        try:
                            _denom_by_group[str(_c.get("groupId"))] = int(float(str(_c.get("value"))))
                        except (TypeError, ValueError):
                            continue
                for cls in (measure.get("classes") or []):
                    # 独立复核修复：携带分析集标签（Interim/Full Analysis 等），
                    # 同终点的不同分析集行并列呈现，口径不再被压成单一标签
                    cls_title = str(cls.get("title") or "").strip()
                    # 分析集标签自带单一访视日（如 "Fatigue: Day 253"）时，
                    # 该行实际时间点取类标签，而非列出双访视日的测量级 time_frame
                    row_time_frame = time_frame
                    _cls_days = set(
                        m.group(1) for m in re.finditer(
                            r"(?:day|week)\s+(\d+(?:\.\d+)?)", cls_title.casefold()
                        )
                    )
                    if len(_cls_days) == 1:
                        row_time_frame = cls_title
                    elif not _cls_days and "baseline" in cls_title.casefold():
                        # 登记明示的基线类行（class="Baseline"）是真实观察
                        row_time_frame = "Baseline"
                    # 独立视觉复核（A copy_zh）：class 原文英文不得嵌入
                    # 中文 population 行；词汇级确定性转写，未命中保留原文
                    cls_title = _transcribe_class_title(cls_title)
                    base_population = (
                        f"登记结果人群（{cls_title}）" if cls_title
                        else "登记结果人群"
                    )
                    for cat in (cls.get("categories") or []):
                        # 独立复核第二十一轮 veto：登记测量的互斥子类
                        # （如 Improved/Worsened from Baseline）必须进入行标签，
                        # 否则同臂同测量的 4 行同名并列，数值含义无法还原
                        cat_title = str(cat.get("title") or "").strip()
                        cat_label = _REGISTRY_CATEGORY_ZH.get(
                            cat_title.casefold(), cat_title
                        )
                        if cat_label:
                            population = base_population[:-1] + f"；{cat_label}）"                                 if base_population.endswith("）") else f"{base_population}（{cat_label}）"
                        else:
                            population = base_population
                        for measurement in (cat.get("measurements") or []):
                            raw = str(measurement.get("value") or "").strip()
                            try:
                                value = float(raw)
                            except ValueError:
                                continue
                            # 会商 P0 #2（域分流）：安全域终点不得混入疗效表——
                            # TEAE/AE/ADA 类测量改记入 derivation 并跳过疗效写入
                            if is_safety_domain_endpoint(title):
                                SAFETY_DOMAIN_DIVERTED.append(
                                    {"trial_id": nct.lower(), "endpoint": title,
                                     "value": value, "timepoint": row_time_frame}
                                )
                                continue
                            group_id = str(measurement.get("groupId") or "")
                            ei += 1
                            efficacy_rows.append({
                                "row_id": f"eff-{ei}", "product_id": pid,
                                "trial_id": nct.lower(), "endpoint": title,
                                "timepoint": time_frame,
                                "arm": group_titles.get(group_id, group_id or "组别未登记"),
                                "value": value, "unit": unit,
                                "population": population,
                                # 独立复核 A r27/r30/r32：登记 denoms（组规模）入行，
                                # 人数列不再全"—"（登记按组披露的分母是真实数据）
                                "denominator": _denom_by_group.get(group_id),
                                "timepoint": row_time_frame,
                            })
            # 会商 P0 #3（矩阵三轴）：治疗臂样本量从 participantFlow
            # Started 里程碑数提取，喂饱矩阵气泡图的样本量轴
            _flow_groups = (results.get("participantFlowModule") or {}).get("groups") or []
            _arm_types = {
                str(a.get("label") or "").strip(): str(a.get("type") or "").upper()
                for a in (study.get("protocolSection", {}).get("armsInterventionsModule", {})
                          or {}).get("armGroups") or []
            }
            _treatment_n = 0
            for _g in _flow_groups:
                if _arm_types.get(str(_g.get("title") or "").strip()) != "EXPERIMENTAL":
                    continue
                for _ms in _g.get("milestones") or []:
                    if str(_ms.get("type")) == "Started" and isinstance(_ms.get("numSubjects"), int):
                        _treatment_n += _ms["numSubjects"]
            if _treatment_n > 0 and trials_rows and trials_rows[-1]["id"] == nct.lower():
                trials_rows[-1]["treatment_sample_size"] = _treatment_n
            events = (results.get("adverseEventsModule", {})
                      .get("eventGroups") or [])
            # 独立复核 A r36（issue-3）：AE 观察窗逐试验取登记 timeFrame，
            # 不再统一写"全研究期（登记）"
            _ae_time_window = (
                " ".join(str((results.get("adverseEventsModule") or {}).get("timeFrame") or "").split())
                or "全研究期（登记）"
            )
            for group in events:
                term = str(group.get("title") or "治疗期间不良事件")
                freq = group.get("seriousNumAffected")
                if freq is None:
                    continue
                # 独立复核修复（臂级分母）：AE 模块同组 atRisk 人数为真实臂级分母
                at_risk = group.get("seriousNumAtRisk")
                si += 1
                safety_rows.append({
                    "row_id": f"safe-{si}", "product_id": pid,
                    "trial_id": nct.lower(), "arm": term,
                    "category": "严重不良事件（登记）",
                    # 会商 P0 #3：受控词表键，供矩阵安全轴精确匹配
                    "term_key": "any_sae",
                    # 独立复核修复：该行为组别汇总计数，term 不再冒充事件名
                    "term": "严重不良事件组别汇总计数",
                    "value": freq, "unit": "例",
                    "numerator": freq,
                    "denominator": at_risk if isinstance(at_risk, int) and at_risk > 0 else None,
                    "time_window": _ae_time_window,
                })
                # 独立复核第二十三轮 veto：登记已报告的死亡必须入安全性域
                deaths_affected = group.get("deathsNumAffected")
                if deaths_affected is not None:
                    si += 1
                    deaths_at_risk = group.get("deathsNumAtRisk")
                    safety_rows.append({
                        "row_id": f"safe-{si}", "product_id": pid,
                        "trial_id": nct.lower(), "arm": term,
                        "category": "死亡病例（登记）",
                    "term_key": "death",
                        "term": "死亡病例组别汇总计数",
                        "value": deaths_affected, "unit": "例",
                        "numerator": deaths_affected,
                        "denominator": deaths_at_risk if isinstance(deaths_at_risk, int) and deaths_at_risk > 0 else None,
                        "time_window": _ae_time_window,
                    })

            # 独立复核 B 门根因修复（声明臂影子归因）：AE 组标题带期间后缀
            # （TP1/TP2/LTE）而疗效臂名为声明臂裸名时，补一条声明臂归因行，
            # 供 B 门"每组最低记录"单元匹配；期间行保留原名展示，不重复展示计数
            _eff_arms = {r["arm"] for r in efficacy_rows if r["trial_id"] == nct.lower()}
            _seen_declared: set[str] = set()
            for _srow in [r for r in safety_rows if r["trial_id"] == nct.lower()]:
                _m = re.match(r"^(.*?)\s*\((?:TP\d+|LTE)\)$", _srow["arm"])
                if _m and _m.group(1) in _eff_arms and _m.group(1) not in _seen_declared:
                    _seen_declared.add(_m.group(1))
                    _shadow = dict(_srow)
                    _shadow["row_id"] = _srow["row_id"] + "-declared"

                    _shadow["arm"] = _m.group(1)
                    safety_rows.append(_shadow)

    # 独立复核第三十二轮：从登记干预描述中提取靶点/机制/给药途径，
    # 替代"未公开披露"占位符
    _MECH_PATTERNS = [
        (re.compile(r"anti[- ]Factor Bb", re.I), "anti-Factor Bb"),
        (re.compile(r"anti[- ]C5", re.I), "anti-C5"),
        (re.compile(r"anti[- ]C3", re.I), "anti-C3"),
        (re.compile(r"C5 inhibitor", re.I), "C5抑制剂"),
        (re.compile(r"C3 inhibitor", re.I), "C3抑制剂"),
        (re.compile(r"factor B inhibitor|factor Bb inhibitor", re.I), "Factor B抑制剂"),
        (re.compile(r"complement (?:C5|C3) (?:receptor|inhibitor)", re.I), "补体抑制剂"),
        (re.compile(r"monoclonal antibody", re.I), "单克隆抗体"),
        (re.compile(r"small molecule|oral.{0,20}inhibitor", re.I), "小分子口服抑制剂"),
        (re.compile(r"factor D inhibitor", re.I), "Factor D抑制剂"),
        (re.compile(r"convertase", re.I), "转化酶"),
    ]
    _TARGET_PATTERNS = [
        (re.compile(r"anti[- ]Factor Bb|Factor Bb", re.I), "Factor Bb"),
        (re.compile(r"complement C5\b|\bC5\b", re.I), "C5"),
        (re.compile(r"complement C3\b|\bC3\b", re.I), "C3"),
        (re.compile(r"factor D", re.I), "Factor D"),
        (re.compile(r"\bFD\b inhibitor|oral FD", re.I), "Factor D"),
        (re.compile(r"factor B\b", re.I), "Factor B"),
        (re.compile(r"ceruloplasmin", re.I), "血浆铜蓝蛋白"),
    ]
    _ROUTE_PATTERNS = [
        (re.compile(r"route of administration:\s*oral|oral administration|taken orally|oral b\.i\.d", re.I), "口服"),
        (re.compile(r"intravenous|IV infusion|administered intravenously", re.I), "静脉注射"),
        (re.compile(r"subcutaneous", re.I), "皮下注射"),
    ]

    # 独立复核 A r22（issue-3）：别名归因——登记用研发代号（LNP023/rVA576），
    # 门户用通用名（iptacopan/coversin），靶点抽取必须沿别名映射归因
    _ALIAS_NEEDLES: dict[str, list[str]] = {}
    for _alias, _canon in (ALIAS.get("canonical_by_alias") or {}).items():
        _ALIAS_NEEDLES.setdefault(_canon, []).append(
            _alias.lower().replace("-", "").replace(" ", "")
        )
    for _pid in list(_ALIAS_NEEDLES):
        _ALIAS_NEEDLES[_pid].append(_pid.lower().replace("-", "").replace(" ", ""))

    def _extract_intervention_info(product_id):
        """靶点/机制/给药途径抽取：别名归因 + 试验级证据绑定。

        归因规则：仅当某登记试验的干预名称命中本产品任一别名时，该试验的
        干预描述、详细描述、关键词、简要摘要才可作为本产品的证据来源
        （对照试验的提及不归因，避免对照药靶点误归属——独立复核既有先例）。
        """
        needles = _ALIAS_NEEDLES.get(product_id, [product_id.lower().replace("-", "").replace(" ", "")])
        texts: list[str] = []
        for study in all_studies:
            proto = study.get("protocolSection", {})
            interventions = (proto.get("armsInterventionsModule", {}) or {}).get("interventions") or []
            # 句子级归因：只采信"含本产品别名"的句子，避免同试验对照药
            # 的靶点句子污染本产品（独立复核 A r22 issue-3 复验发现）
            for iv in interventions:
                iv_name = str(iv.get("name", "")).strip()
                desc = str(iv.get("description", "")).strip()
                name_hit = any(n in iv_name.lower().replace("-", "").replace(" ", "") for n in needles)
                if name_hit and desc:
                    texts.append(desc)
            desc_module = proto.get("descriptionModule", {}) or {}
            trial_relevant = any(
                any(n in str(iv.get("name", "")).lower().replace("-", "").replace(" ", "") for n in needles)
                for iv in interventions
            )
            if trial_relevant:
                for key in ("detailedDescription", "briefSummary"):
                    txt = str(desc_module.get(key) or "").strip()
                    if not txt:
                        continue
                    for sentence in re.split(r"(?<=[.!?])\s+", txt):
                        sent_norm = sentence.lower().replace("-", "").replace(" ", "")
                        if not any(n in sent_norm for n in needles):
                            continue
                        # 组合/背景治疗语境（"add-on to a background C5i"）里
                        # 的靶点词属于背景药，不归属本产品（独立复核 A r22：
                        # danicopan 被背景 C5i 语境误标为 C5 的根因）
                        if re.search(r"add-?on|in addition to|background", sentence, re.I) \
                                and not re.search(r"\bis a\b|\bis an\b", sentence, re.I):
                            continue
                        texts.append(sentence.strip())
            # 关键词属试验级证据：试验已按干预名归因给本产品时，
            # 其全部关键词（如 "Factor D inhibitor"）均可作为机制证据
            for kw in (proto.get("keywordsModule", {}) or {}).get("keywords", []) or []:
                kw_text = str(kw).strip()
                if kw_text and re.search(r"inhibit|inhibitor|agonist|antagonist|antibody", kw_text, re.I):
                    texts.append(kw_text)
        if not texts:
            return None, None, None
        # 靶点/机制选择：在含别名的句子内，取"距别名提及最近"的模式命中，
        # 而非全文首条命中（否则"danicopan + C5 抑制剂背景治疗"类句子
        # 会把 C5 误归给 Factor D 产品——独立复核 A r22 复验发现）
        _MECH_TARGET_HINT = {
            "anti-C5": "C5", "C5抑制剂": "C5", "anti-C3": "C3", "C3抑制剂": "C3",
            "Factor B抑制剂": "Factor B", "Factor D抑制剂": "Factor D",
        }

        def _mech_implies(mech, target_value):
            hint = _MECH_TARGET_HINT.get(mech)
            if hint is None:
                return True
            return hint == target_value

        def _nearest(patterns, joined, needle):
            best_label, best_dist = None, None
            low = joined.casefold()
            positions = [m.start() for m in re.finditer(re.escape(needle), low)]
            if not positions:
                positions = [0]
            for pat, label in patterns:
                for m in pat.finditer(joined):
                    dist = min(abs(p - m.start()) for p in positions)
                    if best_dist is None or dist < best_dist:
                        best_label, best_dist = label, dist
            return best_label

        joined = " ".join(texts)
        cand_target: list[tuple[int, str]] = []
        cand_mech: list[tuple[int, str]] = []
        for text in texts:
            low_text = text.casefold().replace("-", "").replace(" ", "")
            for needle in needles:
                if needle not in low_text:
                    continue
                m_t = _nearest(_TARGET_PATTERNS, text, needle)
                m_m = _nearest(_MECH_PATTERNS, text, needle)
                if m_t:
                    cand_target.append((text.casefold().find(m_t.casefold()[:8]) if m_t else 0, m_t))
                if m_m:
                    cand_mech.append((text.casefold().find(m_m.casefold()[:8]) if m_m else 0, m_m))
                break
        target = min(cand_target)[1] if cand_target else None
        mechanism = min(cand_mech)[1] if cand_mech else None
        # 机制与靶点必须同源（独立复核 A r23：iptacopan 显示
        # "靶点 Factor B｜机制 anti-C5" 自相矛盾）。取定靶点后，
        # 机制改从"其暗示靶点与所定靶点一致"的候选中就近选择。
        if target:
            consistent = [
                (dist, lab) for dist, lab in cand_mech
                if _mech_implies(lab, target)
            ]
            # 无同源机制候选时宁缺毋滥：机制留空（NA），
            # 也不再从全文兜底挑选（避免 anti-C5 复活）
            mechanism = min(consistent)[1] if consistent else None
        if target is None:
            for pat, label in _TARGET_PATTERNS:
                if pat.search(joined):
                    target = label
                    break
        if mechanism is None and target is None:
            for pat, label in _MECH_PATTERNS:
                if pat.search(joined):
                    mechanism = label
                    break
        # 给药途径
        route = None
        for pat, label in _ROUTE_PATTERNS:
            if pat.search(joined):
                route = label
                break
        return target, mechanism, route

    # 收集所有原始 CAS 研究
    all_studies = [study for study, _page, _idx in studies]
    # 独立复核修复（第十二轮）：研发企业两段式归属——
    # 独立复核修复（第十二轮）：研发企业两段式归属——
    # 主产品试验的申办方优先，其次试验药物臂的申办方，对照臂申办方不计。
    for dp, cands in dev_candidates.items():
        if dp not in product_index or not cands:
            continue
        primary = next((lead for is_p, lead in cands if is_p and lead), None)
        experimental = next((lead for is_e, lead in cands if is_e and lead), None)
        chosen = primary or experimental
        if chosen:
            product_index[dp]["developer"] = chosen
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
    # 独立复核 C r19：靶点/机制/给药途径从登记干预描述提取。
    # 该函数此前已定义但从未接线，导致全部产品显示"未公开披露"。
    for pid_e, product_e in product_index.items():
        target_e, mech_e, route_e = _extract_intervention_info(pid_e)
        if target_e and product_e["target"] == NA:
            product_e["target"] = target_e
        if mech_e and product_e["mechanism"] == NA:
            product_e["mechanism"] = mech_e
        if route_e and product_e["route"] == NA:
            product_e["route"] = route_e

    payload = {
        "schema_version": "1.0",
        "report_version": "v1",
        "indication": "阵发性睡眠性血红蛋白尿症",
        "data_cutoff": "2026-09-06T23:59:59.999999+08:00",
        "products": list(product_index.values()),
        "trials": trials_rows,
        "efficacy": efficacy_rows or [{
            "row_id": "eff-none", "product_id": next(iter(product_index)),
            "trial_id": trials_rows[0]["id"], "endpoint": "暂无公开关键结果",
            "timepoint": NA, "arm": NA, "value": None, "unit": NA,
            "population": "公开登记结果尚未覆盖数值终点",
        }],
        "safety": safety_rows or [{
            "row_id": "safe-none", "product_id": next(iter(product_index)),
            "trial_id": trials_rows[0]["id"], "arm": NA,
            "category": "暂无公开结果", "term": NA, "value": None,
            "unit": NA, "time_window": NA,
        }],
        "regulatory": [{
            "product_id": next(iter(product_index)), "track": "中国",
            "event": "监管状态", "date": "2026-09-06",
            "status": "未公开披露（监管路线来源接入待后续版本开放）",
        }],
        "companies": company_rows or [{
            "product_id": next(iter(product_index)), "relationship": "申办方",
            "licensor": NA, "licensee": NA, "territory": NA,
            "transaction": "未公开披露",
        }],
        "patents": [{
            "product_id": next(iter(product_index)), "family": NA,
            "display_family": "专利路线来源接入待后续版本开放", "jurisdiction": NA,
            "scope": NA, "expiry": NA, "exclusivity": NA,
        }],
        "history": [{
            "product_id": next(iter(product_index)), "status": "登记检索完成",
            "date": "2026-09-06",
            "observation": (
                f"CT.gov 当前记录 189 条：{len(trials_rows)} 条试验入表；"
                f"{len(skipped_trials)} 条因未披露样本量未入试验表（NCT："
                + "、".join(skipped_trials[:8])
                + f"）；{len(NON_PRODUCT_RECORDS)} 条无独立药物干预未产出实体（明细见派生记录）；"
                "联合治疗关系受载荷单产品字段限制；"
                "中国路线 访问受阻已如实记档；监管/专利来源待接入"
            ),
        }],
        "sources": [
            {"source": "ClinicalTrials.gov",
             "scope": "PNH 当前记录检索（189 条，两页原始响应 SHA-256 绑定）",
             "maturity": "官方登记当前记录",
             "limitation": "当前记录口径，非历史 as-of 还原"},
            {"source": "PubMed",
             "scope": "PNH 治疗文献真实获取（878 条记录 + 14 分类属性）",
             "maturity": "complete_with_attrition",
             "limitation": "属性差异经 esummary 分类；论文—试验关系判定未完成"},
        ],
        "derivation": {
            "pages": [
                {"page": page, "sha256": sha} for page, sha in page_meta
            ],
            "built_at": datetime.now(UTC).isoformat(),
        },
    }
    derivation = payload.pop("derivation")
    derivation["skipped_trials_no_sample_size"] = skipped_trials
    # 会商 P0 #2：安全域分流审计计数（TEAE/AE 类测量不再混入疗效表）
    derivation["safety_domain_diverted"] = len(SAFETY_DOMAIN_DIVERTED)
    derivation["safety_domain_diverted_samples"] = [
        {k: str(v)[:80] for k, v in item.items()}
        for item in SAFETY_DOMAIN_DIVERTED[:10]
    ]
    derivation["records_without_drug_intervention"] = NON_PRODUCT_RECORDS
    derivation["combo_regimens"] = COMBO_RECORDS
    derivation["alias_map_id"] = ALIAS["map_id"]
    derivation["borderline_repositioning"] = sorted(BORDERLINE)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    sidecar = OUT.with_name("pnh-a-payload.derivation.json")
    sidecar.write_text(json.dumps(derivation, ensure_ascii=False, indent=1), encoding="utf-8")
    print("products:", len(payload["products"]), "| trials:", len(trials_rows))
    print("efficacy rows:", len(efficacy_rows), "| safety rows:", len(safety_rows))
    print("companies:", len(company_rows), "| bytes:", OUT.stat().st_size)


if __name__ == "__main__":
    sys.exit(main())
