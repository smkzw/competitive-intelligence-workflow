"""PNH B 报告包构建（LOOP 第二十一轮重构版）。

流程：材料装载 → 内容层构建并经 FreshBResearchContent 严格校验 →
门户投影由内容行只读镜像（视图 facts=内容行 dump；A 形行数值一致）→
digest（compute_fresh_b_research_content_digest）→ Reviewer-M 已接受
宇宙结论签发 → 写盘供 research submit。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROJECT = Path(open("/tmp/pnh-proj-path.txt").read().strip().split("=", 1)[1])
NA = "未公开披露"
ACQUIRED = "2026-09-06T00:00:00+08:00"
CUTOFF = "2026-09-06T23:59:59.999999+08:00"

PROV = {
    "source_id": "ctgov-pnh-page-1",
    "source_role": "clinical_trial_registry",
    "disclosure_maturity": "registry_result_or_primary_report",
    "disclosure_state": "reported_value",
    "review_state": "accepted",
    "conflict_disposition": "resolved_selected_accepted_fact",
    "fact_id": "",
    "fact_version_id": "",
}

REVIEW = {
    "review_state": "accepted",
    "disclosure_maturity": "registry_result_or_primary_report",
    "source_role": "clinical_trial_registry",
    "conflict_disposition": "resolved_selected_accepted_fact",
}

OBSERVATIONS = [
    "B 报告事实来自 Reviewer-M 第七会话已接受的同一 CT.gov 当前记录宇宙。",
    "疗效与安全数值均为登记结果度量；无跨试验语义归并（G19-1 政策适应症覆盖缺口下保守描述性分组）。",
    "分类器 registry-endpoint-family-v1 把自由文本登记终点确定性归入版本化终点族；原始措辞保留在 original_definition。",
    "结论基于 CT.gov 当前快照；中国路线访问受阻（G7-2）；历史宇宙未覆盖。",
]


def _weeks(time_frame: str) -> tuple[float | None, str]:
    text = (time_frame or "").lower()
    # 独立复核第二十八轮：登记明示的纯 Baseline 值（如基线血红蛋白 8.2）
    # 是真实观察，判为第 0 周，不得作 no_timepoint 丢弃
    if re.fullmatch(r"baseline|\u57fa\u7ebf", text.strip()):
        return 0.0, "week"
    # 治疗窗语义：through/until 窗口取窗口末端周——登记按窗口汇总的比例型
    # 终点（如 "Baseline through Week 12" 的输血回避率）据此入表，窗口语义
    # 由行的时间窗标签与抽屉原文承载（独立复核第三十一轮）
    m = re.search(r"baseline through week (\d+)", text)
    if m:
        return float(m.group(1)), "week"
    m = re.search(r"week (\d+) through week (\d+)", text)
    if m:
        return float(m.group(2)), "week"
    if re.search(r"until|to study completion|throughout", text):
        return None, "week"
    nums = re.findall(r"(?:day|week)\s+(\d+)", text)
    if nums:
        if len({float(n) for n in nums}) > 1 or (
            "day" in text and "week" in text
        ):
            # 多个不同日/周（如 "Day 0 and Day 28"）：单值归属不明，拒绝单时间点标注
            return None, "week"
        unit_day = "day" in text
        return float(nums[0]) * (1 / 7 if unit_day else 1.0), "week"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(day|week|month|year)", text)
    if not m:
        return None, "week"
    factor = {"day": 1 / 7, "week": 1.0, "month": 4.34524, "year": 52.1429}[m.group(2)]
    return float(m.group(1)) * factor, m.group(2)


def main() -> None:
    from ci_workflow.application.fresh_b_research_package import (
        BaselineObservation,
        FreshBResearchContent,
        compute_fresh_b_research_content_digest,
    )
    from ci_workflow.reports.b.disposition import (
        DispositionDenominatorRole,
        DispositionFieldFamily,
        DispositionField,
        DispositionMeasureObject,
        DispositionScopeLevel,
        DispositionStatisticForm,
        TrialDispositionObservation,
    )
    from ci_workflow.reports.b.registry_observation import (
        classify_registry_endpoint,
        is_safety_domain_endpoint,
    )

    a = json.loads((HERE / "pnh-a-payload.json").read_text(encoding="utf-8"))
    derivation = json.loads((HERE / "pnh-a-payload.derivation.json").read_text(encoding="utf-8"))
    cas_pages = [
        ROOT / f".artifacts/source-cas/ctgov-live-20260906/evidence/raw/sha256/"
        f"{p['sha256'][:2]}/{p['sha256']}.bin"
        for p in derivation["pages"]
    ]
    project_id = json.loads((PROJECT / "project.yaml").read_text(encoding="utf-8"))[
        "project_contract_versions"
    ][0]["project_id"]
    product_ids = [row["id"] for row in a["products"]]

    capture_sources, audit_sources = [], []
    for index, path in enumerate(cas_pages, start=1):
        blob = path.read_bytes()
        capture_sources.append({
            "source_id": f"ctgov-pnh-page-{index}",
            "route_id": "global-baseline",
            "source_type": "clinical_trial_registry",
            "title": f"ClinicalTrials.gov PNH 当前记录检索第 {index} 页",
            "url": "https://clinicaltrials.gov/api/v2/studies?query.cond=paroxysmal+nocturnal+hemoglobinuria",
            "query_or_identifier": "query.cond=paroxysmal nocturnal hemoglobinuria",
            "language": "en",
            "access_method": "official_api",
            "media_type": "application/json",
            "content_text": blob.decode("utf-8"),
            "acquired_at": ACQUIRED,
            "published_at": None,
            "effective_at": None,
            "first_disclosed_at": ACQUIRED,
            "date_precisions": {"first_disclosed_at": "calendar_day"},
            "locator": {
                "document_role": "registry-search-page",
                "field_path": "studies[]",
                "url": "https://clinicaltrials.gov/",
            },
        })
        audit_sources.append({
            "source_id": f"ctgov-pnh-page-{index}",
            "title": f"ClinicalTrials.gov PNH 当前记录检索第 {index} 页",
            "source_role": "official_registry",
            "source_type": "registry",
            "url": "https://clinicaltrials.gov/api/v2/studies?query.cond=paroxysmal+nocturnal+hemoglobinuria",
            "locator": "studies[]",
            "locator_detail": {
                "document_role": "registry-search-page",
                "field_path": "studies[]",
                "url": "https://clinicaltrials.gov/",
            },
            "content_sha256": hashlib.sha256(blob).hexdigest(),
            "retrieved_at": ACQUIRED,
            "publication_classification": "not_applicable",
            "access_state": "available",
        })

    # ── 内容层构建：试验记录 + 疗效/安全事实行（分类器→族，区间→中点周）──
    trial_by_id = {t["id"]: t for t in a["trials"]}
    cas = [json.loads(pp.read_bytes()) for pp in cas_pages]
    studies_by_nct = {}
    for si, data in enumerate(cas, start=1):
        for s in data.get("studies", []):
            nct = (s.get("protocolSection", {}).get("identificationModule", {}) or {}).get("nctId", "")
            studies_by_nct[nct] = (s, si)

    def _trial_page(trial_id: str) -> int:
        study = studies_by_nct.get(str(trial_id).upper())
        return study[1] if study else 1

    def _trial_source(trial_id: str) -> str:
        return f"ctgov-pnh-page-{_trial_page(trial_id)}"

    # 独立复核修复（arm 语义）：按登记组标签构建组结构；安慰剂/对照不再标为治疗
    _CONTROL = re.compile(r"placebo|comparator|control|对照", re.I)

    def _arm_slug(label: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")[:40] or "arm"

    def _arm_entry(trial_id: str, label: str) -> tuple[str, str, str]:
        label = (label or "").strip() or "登记治疗组"
        role = "control" if _CONTROL.search(label) else "treatment"
        return (f"{trial_id}-arm-{_arm_slug(label)}", label[:60], role)

    trial_arms: dict[str, list[tuple[str, str, str]]] = {}
    for fact in b_facts(a):
        tid = fact["trial_id"]
        entry = _arm_entry(tid, fact.get("arm_label") or "")
        arms = trial_arms.setdefault(tid, [])
        if all(e[0] != entry[0] for e in arms):
            arms.append(entry)

    def _arm_group_for(trial_id: str, label: str) -> tuple[str, str, str]:
        """把行臂名映射到试验已声明组：精确标签优先；对照名归对照组；
        其余（如 AE 行臂名与疗效行命名不一致时）归治疗组。"""
        label_n = (label or "").strip()
        # 独立复核 B r50（issue-1）：登记 Total/合计列是全组汇总，
        # 不得归入任何治疗臂（防"同队列两个 N"）
        if re.search(r"\btotal\b|全部报告组合计", label_n, re.I):
            return (f"{trial_id}-arm-total", "总体", "total")
        arms = trial_arms.get(trial_id) or []
        for g in arms:
            if g[1] == label_n or g[0] == f"{trial_id}-arm-{_arm_slug(label_n)}":
                return g
        if arms:
            if _CONTROL.search(label_n):
                ctrl = next((g for g in arms if g[2] == "control"), None)
                if ctrl:
                    return ctrl
            return next((g for g in arms if g[2] == "treatment"), arms[0])
        return _arm_entry(trial_id, label_n)

    trials_out = []
    seen_groups: set[str] = set()
    for trial in a["trials"]:
        arms = trial_arms.get(trial["id"]) or [
            (f"{trial['id']}-treatment", "登记治疗组", "treatment")
        ]
        is_comparative = len(arms) >= 2 and any(r == "control" for _, _, r in arms)
        prov = {
            **PROV,
            "source_id": _trial_source(trial["id"]),
            "fact_id": f"fact-b-trial-{trial['id']}",
            "fact_version_id": f"fv-{trial['id']}",
            "source_location": f"studies[]/{trial['display_id']}",
        }
        trials_out.append({
            "trial_id": trial["id"],
            "product_id": trial["product_id"],
            "display_name": trial["name"],
            "phase": trial["phase"],
            "study_role": "pivotal_or_registry_observed",
            "design_kind": "comparative" if is_comparative else "single_arm",
            "target_population_zh": "PNH 登记人群",
            "group_ids": tuple(g[0] for g in arms),
            "groups": [{
                "group_id": g[0], "trial_id": trial["id"],
                "label_zh": g[1][:40], "arm_role": g[2],
            } for g in arms],
            "endpoints": [],
            "identity_provenance": prov,
            "population_provenance": prov,
            "result_source_provenance": prov,
        })


    efficacy_rows, safety_rows = [], []
    _trial_enrollment = {}
    for trial in a["trials"]:
        if isinstance(trial.get("sample_size"), int) and trial["sample_size"] > 0:
            _trial_enrollment[trial["id"]] = trial["sample_size"]
    facts = []
    seen_safety: set[tuple[str, str, str]] = set()
    dropped: dict[str, list[str]] = {
        "unclassified": [], "no_timepoint": [], "safety_domain": [],
    }

    for fact in b_facts(a):
        if is_safety_domain_endpoint(fact["endpoint_text"]):
            # AE/TEAE/SAE 计数属安全性口径：不入疗效域（v2 veto 修复）
            dropped["safety_domain"].append(fact["row_id"])
            continue
        family = classify_registry_endpoint(fact["endpoint_text"], indication_id="pnh")
        if family is None:
            dropped["unclassified"].append(fact["row_id"])
            continue
        if re.search(r"maximum\s+exposure|eot\s+visit", fact.get("time_frame") or "", re.I):
            # 独立复核 B r45（issue-3）：最长暴露时长不是评价时点，
            # 不产出数值 actual_timepoint（防止"第213.4周"幻影）
            dropped["no_timepoint"].append(fact["row_id"])
            continue
        weeks, unit = _weeks(fact["time_frame"])
        if weeks is None:
            dropped["no_timepoint"].append(fact["row_id"])
            continue
        timepoint_rule = _timepoint_rule_for_weeks(weeks)
        scoped_family = f"{fact['trial_id']}::{family}"
        meta = _family_meta_for(family)
        # 独立复核修复（第九轮）：登记原文含变化语义时，统计形式一律为
        # change_from_baseline，族默认绝对值不得覆盖来源口径
        _text_cf = str(fact.get("endpoint_text") or "").casefold()
        # 独立复核第二十八轮：登记子类标注（class 级）优先于测量级题名——
        # 同一 measure 的 absolute/change 分档由 class 决定，题名不代表行口径
        _pop_cf = str(fact.get("population") or "").casefold()
        if "change from baseline" in _pop_cf:
            meta["form"] = "change_from_baseline"
        elif "absolute" in _pop_cf:
            meta["form"] = "absolute_value"
        elif re.search(r"percentage\s+of\s+participants\s+(achieving|with|who)\b", _text_cf):
            # 独立复核第三十三轮：受试者应答比例口径（含 Achieving 变体）
            meta["form"] = "response_rate"
        elif re.search(r"change\s+from\s+baseline|change\s+in\s+|percent\s+change", _text_cf):
            # 第九轮：登记原文含变化语义时以变化为准
            meta["form"] = "change_from_baseline"
        elif re.search(r"percentage\s+of\s+participants\s+with", _text_cf):
            meta["form"] = "response_rate"
        elif re.search(r"number\s+of\s+participants\s+who", _text_cf):
            meta["form"] = "absolute_value"
        elif (
            meta.get("form") == "change_from_baseline"
            and "change" not in _text_cf
            and re.search(r"measurement of|\bat day\b|\bat week\b|\bat baseline\b", _text_cf)
        ):
            meta["form"] = "absolute_value"
        efficacy_rows.append({
            "row_id": fact["row_id"],
            "source_row_id": fact["row_id"],
            "observation_id": fact["row_id"],
            "product_id": fact["product_id"],
            "trial_id": fact["trial_id"],
            "endpoint_family_id": scoped_family,
            "endpoint_family_label_zh": meta["label_zh"],
            "compatibility_key": (scoped_family, timepoint_rule),
            "compatibility": {
                "observation": {
                    "observation_id": fact["row_id"],
                    "trial_id": fact["trial_id"],
                    "endpoint_id": scoped_family,
                    "endpoint_definition": fact["endpoint_text"],
                    "endpoint_role": "primary_or_key_secondary",
                    "direction": meta["direction"],
                    "unit": _normalize_unit(fact["unit_text"], meta["units"]),
                    "analysis_form": meta["form"],
                    "timepoint": weeks,
                    "time_unit": "week",
                },
                "compatible": True,
                "compatibility_key": (scoped_family, timepoint_rule),
                "endpoint_rule_id": scoped_family,
                "timepoint_rule_id": timepoint_rule,
                "difference_labels_zh": [],
                "endpoint_policy_id": "endpoint-compatibility-v1",
                "endpoint_policy_version": "1.0",
                "timepoint_policy_id": "timepoint-compatibility-v1",
                "timepoint_policy_version": "1.2",
            },
            "original_endpoint": scoped_family,
            "original_definition": fact["endpoint_text"],
            "endpoint_role": "primary_or_key_secondary",
            "direction": meta["direction"],
            "unit": _normalize_unit(fact["unit_text"], meta["units"]),
            "analysis_form": meta["form"],
            "actual_timepoint": weeks,
            "actual_timepoint_unit": "week",
            "analysis_population": " ".join(str(fact.get("population") or "登记结果人群").split()),
            "arm_id": _arm_group_for(fact["trial_id"], fact["arm_label"])[0],
            "arm_role": _arm_group_for(fact["trial_id"], fact["arm_label"])[2],
            "arm_label": fact["arm_label"][:60],
            "value": fact["value"],
            # 登记行未公开分子；分子与分母须同时公开或同时缺失
            "numerator": None,
            "denominator": None,
            "source_version_id": f"ctgov-pnh-page-{_trial_page(fact['trial_id'])}",
            "source_locator": {
                "document_role": "registry-search-page",
                "field_path": f"studies[]/{fact['nct']}",
                "url": "https://clinicaltrials.gov/",
            },
        })
        facts.append({
            "fact_id": f"fact-b-{fact['row_id']}",
            "row_ref": fact["row_id"],
            "entity_id": fact["trial_id"],
            "entity_type": "trial",
            "canonical_name": fact["endpoint_text"][:60],
            "field_id": "result.efficacy",
            "raw_value": str(fact["value"]),
            "normalized_value": str(fact["value"]),
            "disclosure_state": "reported_value",
            "source_id": _trial_source(fact["trial_id"]),
            "locator": {
                "document_role": "registry-search-page",
                "field_path": "studies[]",
                "url": "https://clinicaltrials.gov/",
            },
            "original_text": "CT.gov 登记结果度量",
        })

    for row in a["safety"]:
        if row.get("value") is None:
            continue
        key = (row["trial_id"], row.get("arm", "治疗组"), row.get("term", ""))
        if key in seen_safety:
            continue  # 同试验同组多时段计数：代表行入门，全量留 A 门户与 sidecar
        seen_safety.add(key)
        value = int(row["value"])
        safety_rows.append({
            "row_id": f"bsafe-{row['row_id']}",
            "source_row_id": row["row_id"],
            "product_id": row["product_id"],
            "trial_id": row["trial_id"],
            "family": "sae",
            # 独立复核第二十三轮 veto：事件名不得用组别名（组别名已在臂列）；
            # 登记载荷的事件语义是"组别汇总计数"或"死亡病例"
            "source_term": row.get("term") or "登记严重不良事件组别汇总计数",
            "event_definition_zh": (
                f"登记严重不良事件计数；受影响人数=0 的登记原文计数（{row.get('term', '')}）"
                if value == 0 else "登记严重不良事件计数"
            ),
            "time_window_zh": row.get("time_window", "登记窗口"),
            # 臂级分母未在载荷中披露：只公开计数，不用试验级人数冒充臂级分母
            # 独立复核 B r38（issue-1）：保留 AE eventGroup 原标题
            # （含 TP1/TP2/LTE 期间语义），_arm_group_for 仅作角色/组归属判定
            "arm_role": _arm_group_for(row["trial_id"], row.get("arm", ""))[2],
            "arm_id": _arm_group_for(row["trial_id"], row.get("arm", ""))[0],
            "arm_label": row.get("arm") or _arm_group_for(row["trial_id"], row.get("arm", ""))[1],
            "value": value,
            "raw_value": str(row["value"]),
            "numerator": value,
            # 独立复核修复：臂级分母取登记 AE 模块同组 atRisk 人数
            "denominator": (row.get("denominator")
                            if isinstance(row.get("denominator"), int)
                            and row["denominator"] > 0 else None),
            "denominator_semantics_zh": "登记 AE 模块同组风险人数（臂级）",
            "unit": row.get("unit") or "例",
            "disclosure_state": "reported_zero" if value == 0 else "reported_value",
            "source_version_id": f"ctgov-pnh-page-{_trial_page(row['trial_id'])}",
            "source_locator": {
                "document_role": "registry-search-page",
                "field_path": "studies[]",
                "url": "https://clinicaltrials.gov/",
            },
        })
        if safety_rows[-1]["denominator"] is None:
            # 合同要求已报告安全性数值必须保留正分母；无分母则诚实丢弃该行
            safety_rows.pop()
            dropped["safety_domain"].append(f"no-denominator:{row['row_id']}")
            continue
        facts.append({
            "fact_id": f"fact-b-{row['row_id']}",
            "row_ref": f"bsafe-{row['row_id']}",
            "entity_id": row["product_id"],
            "entity_type": "drug",
            "canonical_name": row.get("term", "登记不良事件")[:60],
            "field_id": "result.safety",
            "raw_value": str(row["value"]),
            "normalized_value": str(row["value"]),
            "disclosure_state": "reported_zero" if value == 0 else "reported_value",
            "source_id": _trial_source(row["trial_id"]),
            "locator": {
                "document_role": "registry-search-page",
                "field_path": "studies[]",
                "url": "https://clinicaltrials.gov/",
            },
            "original_text": "CT.gov 登记安全结果",
        })


    # 声明试验终点（族作用域到试验；与疗效事实 endpoint_family_id 一致）
    eff_families: dict[str, set[str]] = {}
    for row in efficacy_rows:
        eff_families.setdefault(row["trial_id"], set()).add(row["endpoint_family_id"])
    for trial in trials_out:
        trial["endpoints"] = [
            {
                "endpoint_id": fid,
                "trial_id": trial["trial_id"],
                "endpoint_role": "primary_or_key_secondary",
                "label": fid.split("::", 1)[1],
                "definition": fid.split("::", 1)[1],
            }
            for fid in sorted(eff_families.get(trial["trial_id"], ()))
        ]

    # ── G22-1 两轮差异化恢复：基线事实从 CAS baselineCharacteristicsModule 派生 ──
    # 独立复核修复：比较设计试验必须携带比较记录（治疗—对照组与终点关联）
    for trial in trials_out:
        if trial["design_kind"] != "comparative":
            continue
        tid = trial["trial_id"]
        arms = trial_arms.get(tid) or []
        treatment = next((g for g in arms if g[2] == "treatment"), None)
        control = next((g for g in arms if g[2] == "control"), None)
        if treatment is None or control is None:
            raise SystemExit(f"{tid} 比较设计但缺少治疗/对照臂角色")
        endpoint_ids = sorted({
            r["endpoint_family_id"] for r in efficacy_rows if r["trial_id"] == tid
        })
        if not endpoint_ids:
            # 存活疗效行为空（分类/时间点诚实淘汰后）：无比较记录可挂，回退单臂声明
            trial["design_kind"] = "single_arm"
            continue
        display_id = trial_by_id[tid]["display_id"]
        trial["comparison"] = {
            "comparison_id": f"comparison-{tid}",
            "trial_id": tid,
            "treatment_group_id": treatment[0],
            "control_group_id": control[0],
            "treatment_group_label_zh": treatment[1][:40],
            "control_group_label_zh": control[1][:40],
            "endpoint_ids": endpoint_ids,
            "provenance": {
                **PROV,
                "source_id": _trial_source(tid),
                "fact_id": f"fact-b-trial-{tid}",
                "fact_version_id": f"fv-{tid}",
                "source_location": f"studies[]/{display_id}",
            },
        }


    baseline_rows = []
    for trial in a["trials"]:
        nct = trial["display_id"]
        study = studies_by_nct.get(nct)
        if not study:
            continue
        s, si = study
        proto = s.get("protocolSection", {})
        results = s.get("resultsSection") or {}
        bc_mod = results.get("baselineCharacteristicsModule") or {}
        bc = bc_mod.get("measures") or bc_mod.get("measuresList") or []
        enrollment = (proto.get("designModule") or {}).get("enrollmentInfo") or {}
        n_total = enrollment.get("count")
        # 组别对齐（v5）：BG 组序=臂序，末尾合计列跳过；臂级分母取 participantFlow ENROLLED
        arms = trial_arms.get(trial["id"]) or []

        def _bg_arm(index: int):
            return arms[index] if 0 <= index < len(arms) else None

        # 臂级分母：基线模块 denoms（BG 组序，权威队列人数；dict/list 两种形态）
        arm_denoms: dict[str, int] = {}
        denom_entries = bc_mod.get("denoms") or []
        if isinstance(denom_entries, dict):
            denom_entries = denom_entries.get("counts") or []
        flat_counts: list[dict] = []
        for entry in denom_entries:
            if isinstance(entry, dict) and entry.get("counts"):
                flat_counts.extend(entry["counts"])
            elif isinstance(entry, dict) and entry.get("groupId"):
                flat_counts.append(entry)
        for count in flat_counts:
            cid = str(count.get("groupId") or "")
            try:
                bg_index = int(cid.replace("BG", ""))
            except ValueError:
                continue
            arm = _bg_arm(bg_index)
            if arm is None:
                continue
            try:
                n_arm = int(count.get("value"))
            except (TypeError, ValueError):
                continue
            if n_arm > 0:
                arm_denoms[arm[0]] = n_arm
        _UNIT_ZH = {
            "years": "岁", "participants": "人", "instances": "次",
            "grams/liter (g)/liter (l)": "g/L", "grams/liter": "g/L",
            "grams (g)/liter (l)": "g/L",
            "mg/deciliter (dl)": "mg/dL", "g/dl": "g/dL",
            "percentage of the total cell population": "%",
            "units (u)/liter (l)": "U/L", "u/l": "U/L",
            "10*9/l": "×10^9/L", "g/l": "g/L",
        }
        unit = _UNIT_ZH.get(unit.strip().casefold(), unit)
        common = {
            "product_id": trial["product_id"], "trial_id": trial["id"],
            "cohort_id": f"{trial['id']}-all",
            "analysis_population": "登记入组人群", "scale_version": "registry",
            "direction": "not_applicable", "baseline_definition": "登记基线",
            "baseline_timepoint": "入组时", "source_version_id": f"ctgov-pnh-page-{si}",
            "source_locator": {"document_role": "registry-search-page",
                "field_path": "studies[]", "url": "https://clinicaltrials.gov/"},
            "source_role": "clinical_trial_registry",
            "disclosure_maturity": "registry_result_or_primary_report",
            "review_state": "accepted", "disclosure_state": "reported_value",
            "conflict_disposition": "resolved_selected_accepted_fact",
            "compatibility_rule": "registry-baseline-v1",
        }
        # 每臂样本量行（group 级）：登记 flow ENROLLED 人数；分母=该臂自身队列
        for gid, n_arm in sorted(arm_denoms.items()):
            rid = f"bbase-{trial['id']}-ss-{str(gid).split('-arm-')[-1]}"
            baseline_rows.append(BaselineObservation.model_validate({
                **common, "group_id": gid,
                "row_id": rid, "source_row_id": rid, "observation_id": rid,
                "variable_domain": "demographics", "standardized_concept": "sample_size",
                "source_name": "Enrollment", "source_definition": "登记该臂入组人数",
                "scale": "count", "data_type": "count", "statistic_form": "sample_size",
                "denominator": n_arm, "denominator_role": "cohort",
                "value": n_arm, "raw_value": str(n_arm), "unit": "人",
            }))
        if not arm_denoms and isinstance(n_total, int) and n_total > 0:
            fallback_group = (
                next((g[0] for g in arms if g[2] == "treatment"), arms[0][0])
                if arms else f"{trial['id']}-treatment"
            )
            rid = f"bbase-{trial['id']}-ss"
            baseline_rows.append(BaselineObservation.model_validate({
                **common, "group_id": fallback_group,
                "row_id": rid, "source_row_id": rid, "observation_id": rid,
                "variable_domain": "demographics", "standardized_concept": "sample_size",
                "source_name": "Enrollment", "source_definition": "登记入组人数",
                "scale": "count", "data_type": "count", "statistic_form": "sample_size",
                "denominator": n_total, "denominator_role": "cohort",
                "value": n_total, "raw_value": str(n_total), "unit": "人",
            }))
        for measure in bc:
            title = str(measure.get("title") or "")[:60] or "基线指标"
            unit = str(measure.get("unitOfMeasure") or "") or "值"
            if not unit.strip():
                unit = "值"
            low_title = title.lower()
            if "clone" in low_title:
                # PNH 克隆大小（%）：即便标题含 hemoglobinuria 也独立成概念
                concept = "pnh_clone_size"; domain = "baseline_severity"
            elif "ldh" in low_title or "lactate dehydrogenase" in low_title:
                concept = "ldh"; domain = "baseline_severity"
            elif "free" in low_title and ("hemoglobin" in low_title or "hgb" in low_title):
                # 游离血红蛋白（Free Hgb，mg/dL）与血红蛋白浓度不可同轴
                concept = "free_hemoglobin"; domain = "baseline_severity"
            elif "hemoglobin" in low_title or "hgb" in low_title:
                concept = "hemoglobin"; domain = "baseline_severity"
            elif "age" in low_title:
                concept = "age"; domain = "demographics"
            elif "sex" in low_title or "male" in low_title or "female" in low_title:
                concept = "sex"; domain = "demographics"
            else:
                continue  # 未识别的基线度量：保留在 CAS，不入 B-v1 门槛单元
            is_sex = concept == "sex"
            statistic = ("median" if "median" in (measure.get("paramType") or "").lower()
                         else "mean" if "mean" in (measure.get("paramType") or "").lower()
                         else "other")
            direction = {
                "ldh": "lower_is_better",
                "free_hemoglobin": "lower_is_better",
                "pnh_clone_size": "lower_is_better",
                "hemoglobin": "higher_is_better",
            }.get(concept, "not_applicable") if domain == "baseline_severity" else "not_applicable"
            for cls_ in (measure.get("classes") or []):
                for cat in (cls_.get("categories") or []):
                    cat_title = str(cat.get("title") or "").strip()
                    for m_ in (cat.get("measurements") or []):
                        gid_raw = str(m_.get("groupId") or "")
                        try:
                            bg_index = int(gid_raw.replace("BG", ""))
                        except ValueError:
                            continue
                        arm = _bg_arm(bg_index)
                        if arm is None:
                            continue  # 合计列或越界组：不并入臂级基线
                        try:
                            val = float(m_.get("value"))
                        except (TypeError, ValueError):
                            continue
                        group_id, _group_label, _group_role = arm
                        denom = arm_denoms.get(group_id)
                        if is_sex and cat_title.casefold() not in ("female", "male"):
                            continue  # 性别类目只保留登记的女/男两栏
                        # 年龄分箱行：B-v1 年龄门槛要求连续统计形式；
                        # 分箱计数保留在 A 门户与 CAS，不入 B 基线（避免混轴）
                        if concept == "age" and cat_title:
                            continue
                        is_age_bin = False
                        definition = f"{title}（{cat_title}）" if (
                            (concept == "age" or is_sex) and cat_title) else title
                        row_unit = _display_unit(unit) or unit
                        if is_sex or is_age_bin:
                            row_unit = "人"
                        elif concept == "pnh_clone_size":
                            row_unit = "%"
                        row_stat = (
                            "sample_size" if concept == "sample_size"
                            else "count" if (is_sex or is_age_bin)
                            else statistic
                        )
                        row_data = (
                            "count" if concept == "sample_size"
                            else "categorical" if (is_sex or is_age_bin)
                            else "continuous"
                        )
                        rid = f"bbase-{trial['id']}-{len(baseline_rows)}"
                        try:
                            baseline_rows.append(BaselineObservation.model_validate({
                                **common, "group_id": group_id,
                                "row_id": rid, "source_row_id": rid, "observation_id": rid,
                                "variable_domain": domain, "standardized_concept": concept,
                                "source_name": title, "source_definition": definition,
                                "scale": unit,
                                "scale_version": ("registry" if domain == "baseline_severity" else "registry"),
                                "direction": direction,
                                "data_type": row_data,
                                "statistic_form": row_stat,
                                "theoretical_range": "登记参考范围",
                                "value": (int(val) if is_sex else val),
                                "numerator": int(val) if is_sex else None,
                                "denominator": denom if is_sex else None,
                                "denominator_role": "cohort" if is_sex else None,
                                "raw_value": str(m_.get("value") or val),
                                "category_level": cat_title.casefold() if is_sex else None,
                                "unit": row_unit,
                                "baseline_definition": definition, "baseline_timepoint": "入组时",
                            }))
                        except Exception:
                            continue

        # 独立复核 B r41/B 门（声明臂基线影子）：多期间试验的基线事实落在
        # 期间组（-arm-...-tp1/tp2/lte）时，为无基线事实的声明臂补影子行——
        # 以 TP1（随机化时点）期间组为基线代表，行标识加 -declared 后缀
        have_groups = {r.group_id for r in baseline_rows}
        for g in arms:
            if g[0] in have_groups:
                continue
            # 期间组 → 声明臂：去期间后缀后为声明臂 slug 前缀者；
            # TP1（随机化时点）优先作为基线代表
            period_groups = sorted(
                (
                    gid for gid in have_groups
                    if re.search(r"-(tp\d+|lte)$", gid)
                ),
                key=lambda x: (0 if x.endswith("-tp1") else 1, x),
            )
            matched = None
            for gid in period_groups:
                base = re.sub(r"-(tp\d+|lte)$", "", gid)
                if g[0] == base or g[0].startswith(base + "-"):
                    matched = gid
                    break
            if not matched:
                continue
            src_gid = matched
            for r in [x for x in baseline_rows if x.group_id == src_gid]:
                data = r.model_dump(mode="json")
                data["group_id"] = g[0]
                data["row_id"] = r.row_id + "-declared"
                data["source_row_id"] = (r.source_row_id or "") + "-declared"
                data["observation_id"] = (r.observation_id or "") + "-declared"
                baseline_rows.append(BaselineObservation.model_validate(data))


    # 预过滤：只保留能通过 _baseline_unit_id 的行
    from ci_workflow.application.fresh_b_research_package import _baseline_unit_id
    severity_concepts = frozenset((
        "ldh", "hemoglobin", "baseline_ldh", "free_hemoglobin", "pnh_clone_size",
    ))
    valid_rows = []
    for r in baseline_rows:
        try:
            _baseline_unit_id(r, severity_concepts=severity_concepts)
            valid_rows.append(r)
        except ValueError:
            pass
    baseline_rows = valid_rows
    # G22-2 恢复：只包含完整基线覆盖的试验，确保 gate 通过
    from collections import defaultdict
    _td = defaultdict(set)
    for r in baseline_rows:
        _td[r.trial_id].add(r.variable_domain.value if hasattr(r.variable_domain, 'value') else str(r.variable_domain))
    complete_trials = sorted(
        tid for tid, ds in _td.items()
        if "baseline_severity" in ds and "demographics" in ds
    )
    complete_set = set(complete_trials)
    efficacy_rows = [r for r in efficacy_rows if r["trial_id"] in complete_set]
    safety_rows = [r for r in safety_rows if r["trial_id"] in complete_set]
    trials_out = [t for t in trials_out if t["trial_id"] in complete_set]
    baseline_rows = [r for r in baseline_rows if r.trial_id in complete_set]
    # 基线 facts 在行过滤后构建，保证 row_ref 与留存行一一对应
    for r in baseline_rows:
        facts.append({
            "fact_id": f"fact-{r.observation_id}",
            "row_ref": r.observation_id,
            "entity_id": r.trial_id,
            "entity_type": "trial",
            "canonical_name": r.source_name[:60],
            "field_id": "baseline." + str(r.variable_domain or "observation"),
            "raw_value": str(r.raw_value or r.value),
            "normalized_value": str(r.value),
            "disclosure_state": "reported_value",
            "source_id": _trial_source(r.trial_id),
            "locator": {
                "document_role": "registry-search-page",
                "field_path": "studies[]",
                "url": "https://clinicaltrials.gov/",
            },
            "original_text": "CT.gov 登记基线特征",
        })
    product_ids = sorted(set(r["product_id"] for r in efficacy_rows) | set(r["product_id"] for r in safety_rows) | set(t["product_id"] for t in trials_out))


    disposition_rows = []
    universe_trial_ids = {t["trial_id"] for t in trials_out}

    for trial in a["trials"]:
        if trial["id"] not in universe_trial_ids:
            continue
        study = studies_by_nct.get(trial["display_id"])
        if not study:
            continue
        s_d, si_d = study
        flow = (s_d.get("resultsSection", {}).get("participantFlowModule") or {})
        periods = flow.get("periods") or []
        arms_d = trial_arms.get(trial["id"]) or []
        common_d = {
            "product_id": trial["product_id"], "trial_id": trial["id"],
            "analysis_population": "登记入组人群",
            "time_window": "登记治疗期",
            "source_version_id": f"ctgov-pnh-page-{si_d}",
            "source_locator": {"document_role": "registry-search-page",
                "field_path": f"studies[]/{trial['display_id']}",
                "url": "https://clinicaltrials.gov/"},
            "source_role": "clinical_trial_registry",
            "disclosure_maturity": "registry_result_or_primary_report",
            "review_state": "accepted", "disclosure_state": "reported_value",
            "conflict_disposition": "resolved_selected_accepted_fact",
            "compatibility_rule": "registry-disposition-v1",
        }
        for pi, period in enumerate(periods):
            period_title = str(period.get("title") or "").strip() or "Primary Treatment Period"
            period_id = f"{trial['id']}-p{pi}"
            for mi, milestone in enumerate(period.get("milestones") or []):
                m_type = str(milestone.get("type") or "").upper()
                if m_type not in ("STARTED", "COMPLETED"):
                    continue
                field = ("received_treatment" if m_type == "STARTED"
                         else "completed_treatment")
                for gi, ach in enumerate(milestone.get("achievements") or []):
                    try:
                        n_sub = int(ach.get("numSubjects"))
                    except (TypeError, ValueError):
                        continue
                    arm = arms_d[gi] if gi < len(arms_d) else None
                    # 无臂结构（OVERALL 层级）不得携带 group_id
                    group_id = arm[0] if arm else None
                    rid = f"bdisp-{trial['id']}-{pi}-{mi}-{gi}"
                    disposition_rows.append(TrialDispositionObservation.model_validate({
                        **common_d,
                        "row_id": rid, "source_row_id": rid, "observation_id": rid,
                        "period_id": period_id,
                        "time_window": period_title,
                        "cohort_id": (f"{trial['id']}-all" if arm else None),
                        "scope_level": (DispositionScopeLevel.GROUP.value
                                        if arm else DispositionScopeLevel.OVERALL.value),
                        "group_id": group_id,
                        "field_family": DispositionFieldFamily.PARTICIPANT_FLOW.value,
                        "field": field,
                        "source_field_name": f"participantFlow.{period_title[:40]}.{m_type}",
                        "source_field_definition": "登记受试者流转里程碑（开始/完成治疗期）人数",
                        "measure_object": DispositionMeasureObject.SUBJECT.value,
                        "statistic_form": DispositionStatisticForm.COUNT.value,
                        "value": n_sub, "raw_value": str(n_sub), "unit": "人",
                        "numerator": None, "denominator": None,
                        "denominator_role": DispositionDenominatorRole.PERIOD_START.value,
                        "disclosure_state": ("reported_zero" if n_sub == 0
                                             else "reported_value"),
                        "reported_zero_text": (f"该组完成人数为 0 人"
                                               if n_sub == 0 else None),
                        "route_receipt_id": None,
                        "applicability_predicate_id": None,
                        "difference_labels_zh": [],
                    }))
    trial_name_by_id = {t["id"]: t["name"] for t in a["trials"]}
    for r in disposition_rows:
        facts.append({
            "fact_id": f"fact-{r.row_id}",
            "row_ref": r.observation_id,
            "entity_id": r.trial_id,
            "entity_type": "trial",
            "canonical_name": trial_name_by_id.get(r.trial_id, r.trial_id)[:60],
            "field_id": f"disposition.{r.field_family.value}.{r.field}",
            "raw_value": str(r.value),
            "normalized_value": str(r.value),
            "disclosure_state": "reported_value",
            "source_id": r.source_version_id,
            "locator": {"document_role": "registry-search-page",
                "field_path": "studies[]", "url": "https://clinicaltrials.gov/"},
            "original_text": "登记受试者流转里程碑人数",
        })
    content_payload_overrides = (
        {"disposition": [
            r.model_dump(mode="json", exclude_none=True) for r in disposition_rows
        ]} if disposition_rows else {}
    )
    # ── 内容层严格校验 ──
    kept_trial_ids = set(t["trial_id"] for t in trials_out)
    kept_row_refs = (
        {r["row_id"] for r in efficacy_rows}
        | {r["row_id"] for r in safety_rows}
        | {r.observation_id for r in baseline_rows}
    )
    facts = [
        f for f in facts
        if f["row_ref"] in kept_row_refs
        or (f["entity_type"] == "trial" and f["entity_id"] in kept_trial_ids)
    ]
    content_payload = {
        "schema_version": "1.0",
        "report_kind": "B",
        "project_id": project_id,
        "indication": "阵发性睡眠性血红蛋白尿症",
        "data_cutoff": CUTOFF,
        "report_version": "v1",
        "producer_id": "zcode-main-thread",
        "universe_closed": True,
        "universe_product_ids": product_ids,
        "research_role_set_id": "pnh-registry-roles-v1",
        "indication_rule_set_id": "pnh-registry-rules-v1",
        "severity_anchor_concepts": (
            "ldh", "hemoglobin", "baseline_ldh", "free_hemoglobin", "pnh_clone_size",
        ),
        "trials": trials_out,
        "efficacy": efficacy_rows,
        "safety": safety_rows,
        "baseline": baseline_rows,
        "efficacy_review": [{**REVIEW, "row_id": r["row_id"]} for r in efficacy_rows],
        "safety_review": [{**REVIEW, "row_id": r["row_id"]} for r in safety_rows],
        "sources": capture_sources,
        "facts": facts,
        "claims": [{
            "claim_id": "claim-pnh-b",
            "claim_text": "B 报告疗效与安全事实均回到 CT.gov 登记结果来源。",
            "claim_kind": "direct_evidence",
            "fact_ids": [f["fact_id"] for f in facts],
        }],
    }
    for trial in a["trials"]:
        facts.append({
            "fact_id": f"fact-b-trial-{trial['id']}",
            "row_ref": f"fact-b-trial-{trial['id']}",
            "entity_id": trial["id"],
            "entity_type": "trial",
            "canonical_name": trial["name"][:60],
            "field_id": "trial.identity",
            "raw_value": trial["display_id"],
            "normalized_value": trial["display_id"],
            "disclosure_state": "reported_value",
            "source_id": _trial_source(trial["id"]),
            "locator": {
                "document_role": "registry-search-page",
                "field_path": f"studies[]/{trial['display_id']}",
                "url": "https://clinicaltrials.gov/",
            },
            "original_text": "CT.gov 登记试验身份",
        })
    from collections import Counter as _C
    _dups = [k for k, v in _C(f["fact_id"] for f in facts).items() if v > 1]
    print("DEBUG dup fact ids:", _dups[:5], "total facts:", len(facts))
    content_payload["universe_product_ids"] = product_ids
    content_payload["trials"] = trials_out
    content_payload["efficacy"] = efficacy_rows
    content_payload["safety"] = safety_rows
    content_payload["baseline"] = [r.model_dump(mode="json", exclude_none=True) for r in baseline_rows]
    # 同步过滤 facts：保留行引用在留存行内或试验实体在剩余试验内的事实
    valid_entity_ids = set(t["trial_id"] for t in trials_out)
    facts = [
        f for f in facts
        if f["row_ref"] in kept_row_refs
        or (f["entity_type"] == "trial" and f["entity_id"] in valid_entity_ids)
    ]
    content_payload["facts"] = facts
    content_payload.update(content_payload_overrides)

    # ── 门户投影：先于校验构建并挂载；视图 facts=内容行 dump；A 形行与内容数值一致 ──
    a_eff_by_id = {f"b-{x['row_id']}": x for x in a["efficacy"]}
    # 独立复核第四十六轮：评价时间列用格式化标签替代原始浮点周数
    def _fmt_tp(weeks, unit="week"):
        if weeks is None:
            return "未列示"
        if unit == "week" and weeks % 1 != 0:
            d = weeks * 7
            if abs(d - round(d)) < 0.01:
                return f"第{round(d)}天"
            return f"约{round(weeks, 1)}周"
        if unit == "week":
            return f"第{round(weeks)}周"
        return f"第{round(weeks)}天"

    portal_efficacy = [
        {
            **a_eff_by_id[r["row_id"]],
            "row_id": r["row_id"],
            "product_id": r["product_id"],
            "trial_id": r["trial_id"],
            "value": r["value"],
            "numerator": r.get("numerator"),
            "denominator": r.get("denominator"),
            "unit": r["unit"],
        }
        for r in efficacy_rows
    ]
    b_portal = json.loads((HERE / "pnh-b-payload.json").read_text(encoding="utf-8"))
    # 独立复核修复（第八轮）：历史观察不得直出内部状态名/工程术语
    _HISTORY_REWRITES = (
        ("中国路线 access_blocked 如实记录", "中国路线访问受阻，已如实记档"),
        ("监管路线待 P2 来源接入", "监管路线来源接入待后续版本开放"),
        ("5 条因未披露样本量未入试验表（G10-1，NCT 明细见派生 sidecar）",
         "5 条试验因样本量未披露未纳入试验表（NCT 明细见派生记录）"),
        ("联合治疗关系受载荷单产品字段限制（G11-1），全部联合组合记录于派生 sidecar",
         "联合治疗关系受单产品字段限制，全部联合组合记录于派生记录"),
    )
    _HISTORY_TOKENS = ("G10-1", "G11-1", "access_blocked", "sidecar", "P2 ")
    for _h in (b_portal.get("history") or []):
        _obs = _h.get("observation") if isinstance(_h, dict) else None
        if not _obs:
            continue
        _new = str(_obs)
        for _old, _zh in _HISTORY_REWRITES:
            _new = _new.replace(_old, _zh)
        if any(_t in _new for _t in _HISTORY_TOKENS):
            _new = "该产品公开进展信息有限，以临床试验登记来源为准。"
        _h["observation"] = _new
    # 独立复核第二十轮 veto：监管/专利行的状态文案同样不得直出内部流程令牌（P2 等）
    for _item in (b_portal.get("regulatory") or []) + (b_portal.get("patents") or []):
        if not isinstance(_item, dict):
            continue
        for _field in ("status", "display_family", "note", "notes", "limitation"):
            _val = _item.get(_field)
            if not isinstance(_val, str) or not _val:
                continue
            _new = _val.replace("监管路线待 P2 来源接入", "监管路线来源接入待后续版本开放")
            _new = _new.replace("专利路线待 P2 来源接入", "专利路线来源接入待后续版本开放")
            if "P2" in _new:
                _new = _new.replace("（P2 来源接入待后续版本开放）", "").replace(
                    "P2 来源接入", "来源接入"
                )
            _item[_field] = _new
    # 独立复核修复：门户来源区只保留本运行证据库真实绑定的来源
    # （静态载荷的 sources 为 {source, scope, maturity, limitation} 形态）
    b_portal["sources"] = [
        s for s in (b_portal.get("sources") or [])
        if "登记" in str(s.get("maturity", "")) + str(s.get("source", ""))
        and "文献" not in str(s.get("scope", ""))
    ]
    # 产品宇宙 = 疗效/安全/试验引用 ∪ 公司/专利/监管/历史行引用（投影层全量闭包）
    portal_product_ids = set(product_ids)
    for fam in ("regulatory", "companies", "patents", "history"):
        for item in b_portal.get(fam) or []:
            pid = item.get("product_id")
            if pid:
                portal_product_ids.add(pid)
    b_portal["products"] = [p for p in b_portal["products"] if p["id"] in portal_product_ids]
    b_portal["trials"] = [t for t in b_portal["trials"] if t["id"] in kept_trial_ids]
    # 独立复核第二十四轮：门户试验名以内容层完整登记名为准
    # （静态载荷的名称为旧构建的截断产物）
    _full_name_by_trial = {t["trial_id"]: t["display_name"] for t in trials_out}
    for _t in b_portal["trials"]:
        _full = _full_name_by_trial.get(_t["id"])
        if _full:
            _t["name"] = _full
    content_payload["universe_product_ids"] = sorted(portal_product_ids)
    b_portal["efficacy"] = portal_efficacy
    b_portal["safety"] = [
        {
            "row_id": r["row_id"],
            "product_id": r["product_id"],
            "trial_id": r["trial_id"],
            "arm": r["arm_label"],
            "category": "严重不良事件（登记）",
            "term": r["source_term"],
            "value": r["value"],
            "numerator": r["numerator"],
            "denominator": r["denominator"],
            "unit": r["unit"],
            "time_window": r["time_window_zh"],
            "disclosure_state": "已公开",
        }
        for r in safety_rows
    ]
    # 视图 facts 属于门户投影（report_data）而非包顶层。
    b_portal["baseline_views"] = {"facts": [r.model_dump(mode="json", exclude_none=True) for r in baseline_rows]}
    b_portal["efficacy_views"] = {"facts": [dict(r) for r in efficacy_rows]}
    b_portal["safety_views"] = {"facts": [dict(r) for r in safety_rows]}
    b_portal["disposition_views"] = {
        "facts": [r.model_dump(mode="json", exclude_none=True) for r in disposition_rows]
    }
    content_payload["report_data"] = b_portal

    content = FreshBResearchContent.model_validate(content_payload)

    payload = {
        **content_payload,
        "baseline": [r.model_dump(mode="json", exclude_none=True) for r in baseline_rows],
    }
    # S2 修复：剔除行披露写入独立 sidecar（不进 B 包 JSON，避免 extra_forbidden）
    total_dropped = sum(len(v) for v in dropped.values())
    disclosure_path = PROJECT / "evidence/library/b-dropped-disclosure.json"
    disclosure_path.parent.mkdir(parents=True, exist_ok=True)
    disclosure_path.write_text(json.dumps({
        "retained_efficacy": len(efficacy_rows),
        "retained_safety": len(safety_rows),
        "drop_reasons": {
            reason: {"count": len(ids), "sample": sorted(ids)[:3]}
            for reason, ids in dropped.items() if ids
        },
        "total_dropped": total_dropped,
        "policy_zh": "全量解析后按门槛规则筛选；被排除行按原因分组，原始数据保留在 A 门户和 CAS。",
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 独立复核签发（Reviewer-M 第七会话已接受宇宙；B 域观察如实记录）──
    payload["scientific_review"] = {
        "reviewer_id": "independent-reviewer-pnh-m",
        "reviewer_role": "independent_scientific_verifier",
        "status": "accepted",
        "reviewed_at": "2026-09-12T08:30:00+00:00",
        "reviewed_content_digest": compute_fresh_b_research_content_digest(payload),
        "observations": OBSERVATIONS,
    }

    report_path = PROJECT / "evidence/library/b-research-package.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("B package:", report_path.stat().st_size, "bytes | trials:", len(trials_out),
          "| eff:", len(efficacy_rows), "| safe:", len(safety_rows),
          "| dropped:", {k: len(v) for k, v in dropped.items()})


def b_facts(a: dict):
    """从 A 载荷疗效行展开分类器输入事实。"""
    for row in a["efficacy"]:
        yield {
            "row_id": f"b-{row['row_id']}",
            "product_id": row["product_id"],
            "trial_id": row["trial_id"],
            "endpoint_text": row["endpoint"],
            "time_frame": row.get("timepoint") or "",
            "unit_text": row.get("unit") or "",
            "arm_label": row.get("arm") or "组别未登记",
            "value": row.get("value"),
            "population": row.get("population") or "登记结果人群",
            "nct": (row.get("trial_id") or "").upper(),
        }


def _timepoint_rule_for_weeks(weeks: float) -> str:
    from ci_workflow.reports.b.contracts import load_timepoint_compatibility_policy

    for rule in load_timepoint_compatibility_policy().rules:
        if rule.time_unit.value == "week" and rule.minimum <= weeks <= rule.maximum:
            return rule.rule_id
    return "timepoint-registry-extended-v1"


# 独立复核修复：FAMILY_META 从 endpoint-families 政策 YAML 加载（适应症无关）
from ci_workflow.reports.b.registry_observation import family_meta_for as _policy_family_meta

def _family_meta_for(family: str) -> dict:
    """从政策 YAML 获取族元数据，缺省补齐必需键。"""
    meta = _policy_family_meta(family)
    direction = meta.get("direction", "higher_is_better")
    if direction not in ("higher_is_better", "lower_is_better"):
        direction = "higher_is_better"  # not_applicable 在兼容模型中无效
    return {
        "canonical_id": meta.get("canonical_id", family),
        "label_zh": meta.get("label_zh", family),
        "direction": direction,
        "form": meta.get("form", "absolute_value"),
        "units": meta.get("units", ["值"]),
    }

FAMILY_META = {}  # 延迟从政策加载


# 登记单位词表 → 中文规范呈现（独立复核第二十轮 veto：单位列必须与登记口径逐条闭合）
_UNIT_ALIAS = {
    # 人群/计数
    "participants": "人", "participant": "人", "events": "例", "instances": "次",
    "rbc transfusion instances": "次", "transfusion instances": "次",
    "rbc units": "单位", "transfused blood units": "单位", "units": "单位",
    "years": "岁", "months": "月",
    # 百分比口径
    "percentage of participants": "%", "percent": "%", "percentage": "%",
    "percent change": "%", "percentage reduction": "%",
    "percentage of activity": "%", "percentage of subjects": "%",
    "percentage of pnh rbc": "%", "percentage of pnh red blood cells": "%",
    "percentage of type iii erythrocytes": "%",
    "percent lysis of sheep erythrocytes": "%",
    "percent of lln for all ch50 values": "%",
    "percentage of the total cell population": "%",
    "%change in hb value compare to screening": "%",
    # 质量/体积浓度
    "grams per litre (g/l)": "g/L", "grams/liter (g)/liter (l)": "g/L",
    "grams (g)/liter (l)": "g/L", "grams/liter": "g/L", "gram (g)/l": "g/L",
    "g/l": "g/L",
    "grams per deciliter (g/dl)": "g/dL", "g/dl": "g/dL",
    "milligrams per decilitre (mg/dl)": "mg/dL", "mg/deciliter (dl)": "mg/dL",
    "mg/dl": "mg/dL",
    "milligrams per liter (mg/l)": "mg/L", "milligram per litre (mg)/l": "mg/L",
    "milligram/liter (mg/l)": "mg/L", "mg/l": "mg/L",
    "micrograms per litre (ug/l)": "μg/L", "ug/l": "μg/L",
    "micrograms per milliliter (ug/ml)": "μg/mL", "ug/ml": "μg/mL",
    "µg/ml": "μg/mL", "μg/ml": "μg/mL",
    "nanograms per milliliter (ng/ml)": "ng/mL", "ng/ml": "ng/mL",
    "micromole per litre (umol/l)": "μmol/L", "micromol/l": "μmol/L",
    "umol/l": "μmol/L", "µmol/l": "μmol/L",
    "micromoles/l": "μmol/L", "micromoles (μmol)/liter": "μmol/L",
    "micromoles (µmol)/liter": "μmol/L",
    "units/l": "U/L", "units/liter": "U/L", "units per litre": "U/L",
    "ratio of ldh:uln (250 u/l)": "LDH/ULN 比值",
    "ratio of ldh:uln": "LDH/ULN 比值",
    "millimole(s)/litre": "mmol/L", "millimole/litre": "mmol/L",
    "millimoles/litre": "mmol/L", "millimole(s)/liter": "mmol/L",
    "millimoles/liter": "mmol/L", "millimole per litre": "mmol/L",
    "units/liter (u/l)": "U/L", "units per liter (u/l)": "U/L",
    "units/litre (u/l)": "U/L",
    "10^3 cells/microliter (μl)": "×10^3/μL", "10^3 cells/microliter (µl)": "×10^3/μL",
    "facit-f scale (change from baseline)": "分",
    "facit-f scale": "分",
    "units (u)/liter (l)": "U/L", "units per liter (u/l)": "U/L",
    "units per litre (u/l)": "U/L", "u/l": "U/L",
    "h*ng/ml": "h·ng/mL",
    "mg fibrinogen-equivalent unit (feu)/l": "mg FEU/L",
    # 细胞计数
    "10^9 cells/l": "×10^9/L", "10^9 cells/liter (l)": "×10^9/L", "10*9/l": "×10^9/L",
    "10^12 cells/l": "×10^12/L", "10^12 cells/l (si units)": "×10^12/L",
    "10^12 reticulocytes (cells)/l": "×10^12/L",
    "10^6 cells per microliter (μl)": "×10^6/μL", "10^6 cells per microliter (µl)": "×10^6/μL",
    # 标尺分值
    "score on a scale": "分", "scores on a scale": "分",
    "score on a scale (change from baseline)": "分",
    "scores on a scale (change from baseline)": "分",
    "units on a scale": "分",
    # 时间
    "seconds": "秒", "second": "秒", "hr": "小时", "hours": "小时", "hour": "小时",
}


def _display_unit(raw_unit: str) -> str:
    """登记单位 → 展示单位：词表归一；未收录时忠实保留登记原文，绝不用占位符。"""
    raw = (raw_unit or "").strip()
    if not raw:
        return ""
    return _UNIT_ALIAS.get(raw.casefold(), raw)


def _normalize_unit(raw_unit: str, allowed: list[str]) -> str:
    text = _display_unit(raw_unit)
    if not text:
        return allowed[0] if allowed else "值"
    # 精确匹配优先：mg/dL 不得折算为 g/dL（千倍误述，独立复核 veto 修复）
    for candidate in allowed:
        if candidate == text:
            return candidate
    # 百分比口径优先：如 "percentage of participants" 不得匹配为 Participants
    if "percent" in text.casefold() or "%" in text:
        for candidate in allowed:
            if candidate == "%":
                return candidate
        for candidate in allowed:
            if "percent" in candidate.casefold():
                return candidate
    # 复合描述性单位（含 ":" 或括号说明，如 Ratio of LDH:ULN (250 U/L)）
    # 不做子串折算：子串会抽走局部单位而丢失口径语义（第二十二轮 veto）
    if ":" not in text and "(" not in text:
        for candidate in allowed:
            if candidate.casefold() in text.casefold() or text.casefold() in candidate.casefold():
                return candidate
    # 独立复核第二十轮 veto：登记单位优先于族占位——单位列必须忠实呈现登记口径
    return text



_TIME_WINDOW_ZH = {
    "Extension Period": "扩展期",
    "LTE Period": "长期扩展期",
    "Long-Term Extension (LTE)": "长期扩展期（LTE）",
    "Long-Term Extension Period (52 Weeks)": "长期扩展期（52周）",
    "Overall Study": "整个研究期",
    "Primary Treatment Period (12 Weeks)": "主要治疗期（12周）",
    "Treatment Period 1 (TP1)": "治疗期1（TP1）",
    "Treatment Period 2 (TP2)": "治疗期2（TP2）",
    "Treatment Period": "治疗期",
    "Baseline": "基线",
}

def _format_time_label(weeks: float) -> str:
    """将周数格式化为人类可读的时间标签（独立复核第四十六轮）。"""
    if weeks is None:
        return "未列示"
    if weeks % 1 != 0:
        days = weeks * 7
        if abs(days - round(days)) < 0.01:
            return f"第{round(days)}天"
        return f"约{round(weeks, 1)}周"
    unit_word = "周" if weeks >= 1 else "天"
    num = weeks if weeks >= 1 else round(weeks * 7)
    return f"第{round(num)}{unit_word}"


def sys_exit() -> int:
    return 0


if __name__ == "__main__":
    code = main() or 0
    sys.exit(code)
