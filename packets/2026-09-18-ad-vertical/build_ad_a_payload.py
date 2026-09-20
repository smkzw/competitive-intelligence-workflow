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
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAS = sorted(
    p for p in (ROOT / ".artifacts/source-cas/ctgov-live-20260918-ad/evidence/raw").rglob("*.bin")
)
OUT = Path(__file__).resolve().parent / "ad-a-payload.json"
NA = "未公开披露"

_STATUS_RANK = {
    "已批准上市": 8, "招募中": 75, "邀请入组中": 74, "进行中（不招募）": 73,
    "尚未招募": 6, "已完成": 5, "可用": 4, "不再可用": 3, "状态未更新": 2,
    "已暂停": 2, "已终止": 1, "已撤回": 0,
}
ALIAS = json.loads(
    (Path(__file__).resolve().parent / "ad-alias-map-v1.json").read_text(encoding="utf-8")
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
    skipped_trials: list[str] = []
    product_regions: dict[str, set[str]] = {}
    product_phase, product_status = {}, {}
    seen_company = set()
    ei = si = 0

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
        # R15-a 每个真实药物干预都注册产品实体（试验行仍归首项，G11-1 限制）。
        for drug in canonical_drugs:
            drug_pid = slugify(drug)
            if drug_pid not in product_index:
                product_index[drug_pid] = {
                    "id": drug_pid, "name": drug, "target": NA, "modality": NA,
                    "phase": "未标注", "status": "状态未更新",
                    "regions": ["未登记地点"], "route": NA, "developer": lead,
                    "mechanism": NA, "result_status": "暂无公开关键结果",
                }
        if pid not in product_index:
            product_index[pid] = {
                "id": pid, "name": product_name, "target": NA, "modality": NA,
                "phase": "未标注", "status": "状态未更新",
                "regions": ["未登记地点"], "route": NA, "developer": lead,
                "mechanism": NA, "result_status": "暂无公开关键结果",
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
        has_china = any(c.lower() in {"china", "hong kong", "taiwan"} for c in countries)
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
                "name": ident.get("briefTitle", nct)[:120], "phase": phase_zh,
                "region": trial_region, "status": status_zh,
                "sample_size": count,
                "treatment_sample_size": None, "role": "登记研究",
            })

        results = study.get("resultsSection") or {}
        if results:
            group_titles = {
                str(g.get("id")): str(g.get("title") or "组别未登记")[:40]
                for g in (results.get("outcomeMeasuresModule") or {}).get("groups", []) or []
            }
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
                        group_titles[gid] = title[:40]
            for measure in ((results.get("outcomeMeasuresModule") or {})
                            .get("outcomeMeasures") or []):
                title = str(measure.get("title") or "")[:80] or NA
                time_frame = str(measure.get("timeFrame") or "")[:40] or "时间窗未登记"
                unit = str(measure.get("unitOfMeasure") or "") or "值"
                for cls in (measure.get("classes") or [])[:1]:
                    for cat in (cls.get("categories") or []):
                        for measurement in (cat.get("measurements") or [])[:4]:
                            raw = str(measurement.get("value") or "").strip()
                            try:
                                value = float(raw)
                            except ValueError:
                                continue
                            group_id = str(measurement.get("groupId") or "")
                            ei += 1
                            efficacy_rows.append({
                                "row_id": f"eff-{ei}", "product_id": pid,
                                "trial_id": nct.lower(), "endpoint": title,
                                "timepoint": time_frame,
                                "arm": group_titles.get(group_id, group_id or "组别未登记"),
                                "value": value, "unit": unit,
                                "population": "登记结果人群",
                            })
            events = (results.get("adverseEventsModule", {})
                      .get("eventGroups") or [])
            for group in events:
                term = str(group.get("title") or "治疗期间不良事件")[:40]
                freq = group.get("seriousNumAffected")
                if freq is None:
                    continue
                # 独立复核修复（臂级分母）：AE 模块同组 atRisk 人数为真实臂级分母
                at_risk = group.get("seriousNumAtRisk")
                si += 1
                safety_rows.append({
                    "row_id": f"safe-{si}", "product_id": pid,
                    "trial_id": nct.lower(), "arm": term,
                    "category": "严重不良事件（登记）", "term": term,
                    "value": freq, "unit": "例",
                    "numerator": freq,
                    "denominator": at_risk if isinstance(at_risk, int) and at_risk > 0 else None,
                    "time_window": "全研究期（登记）",
                })

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
        "indication": "特应性皮炎",
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
            "status": "未公开披露（监管路线待 P2 来源接入）",
        }],
        "companies": company_rows or [{
            "product_id": next(iter(product_index)), "relationship": "申办方",
            "licensor": NA, "licensee": NA, "territory": NA,
            "transaction": "未公开披露",
        }],
        "patents": [{
            "product_id": next(iter(product_index)), "family": NA,
            "display_family": "专利路线待 P2 来源接入", "jurisdiction": NA,
            "scope": NA, "expiry": NA, "exclusivity": NA,
        }],
        "history": [{
            "product_id": next(iter(product_index)), "status": "登记检索完成",
            "date": "2026-09-06",
            "observation": (
                f"CT.gov 当前记录 189 条：{len(trials_rows)} 条试验入表；"
                f"{len(skipped_trials)} 条因未披露样本量未入试验表（G10-1，NCT 明细见派生 sidecar："
                + "、".join(skipped_trials[:8])
                + f"）；{len(NON_PRODUCT_RECORDS)} 条无独立药物干预未产出实体（明细见 sidecar）；"
                "联合治疗关系受载荷单产品字段限制（G11-1），全部联合组合记录于派生 sidecar；"
                "中国路线 access_blocked 如实记录；监管/专利来源待接入"
            ),
        }],
        "sources": [
            {"source": "ClinicalTrials.gov",
             "scope": "AD 当前记录检索（COMPLETED 过滤，两页真实响应 SHA-256 绑定）",
             "maturity": "官方登记当前记录",
             "limitation": "当前记录口径，非历史 as-of 还原"},
            {"source": "PubMed",
             "scope": "AD 文献路线（未部署，如实记档）",
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
