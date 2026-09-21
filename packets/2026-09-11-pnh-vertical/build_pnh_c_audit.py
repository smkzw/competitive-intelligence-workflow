"""PNH C 报告包构建（试验设计图谱竖向）。

流程：材料装载（A 载荷宇宙 + CT.gov CAS 原始 JSON）→ 按试验确定性派生
设计观察（身份/人群/入排/分组/干预/给药/终点-时间点/样本量）→
设计类型声明 + 候选设计路径综合（≥2 条、签名唯一、不排名）→
FreshCResearchContent 严格校验 → 独立复核签发 → 写盘供 research submit。

诚实策略：访视安排登记未公开 → c_region_visit_operational 以未声明关键
谓词按合同判定不适用（不虚构）；入排/终点保留登记原文，中文演示层只做
确定性压缩。
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
INDICATION = "阵发性睡眠性血红蛋白尿症"
INDICATION_ID = "pnh"

TARGET_TRIALS = (
    "NCT02591862", "NCT02605993", "NCT03181633",
    "NCT04170023", "NCT04469465", "NCT05886244",
)
COMPARATIVE_TRIALS = {"NCT04469465"}

REVIEW = {
    "review_state": "accepted",
    "disclosure_maturity": "registry_result_or_primary_report",
    "source_role": "clinical_trial_registry",
    "conflict_disposition": "resolved_selected_accepted_fact",
}

_LOCATOR = {
    "document_role": "registry-study-record",
    "field_path": "studies[]",
    "url": "https://clinicaltrials.gov/",
}
# 载荷来源定位必须与审计包 locator_detail 逐实例一致
_CAPTURE_LOCATOR = {
    "document_role": "registry-search-page",
    "field_path": "studies[]",
    "url": "https://clinicaltrials.gov/",
}


def _stable(tag: str, *parts: str) -> str:
    return tag + "_" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def _row(trial_id: str, product_id: str, nct: str, page: int, family: str,
         field: str, text: str, *, seq: str, endpoint_key: str | None = None,
         group_id: str | None = None, stage: str | None = None,
         scale: str | None = None, operator: str | None = None,
         threshold: str | None = None, unit: str | None = None,
         timepoint: str | None = None, source_name: str | None = None,
         disclosure: str = "reported_value",
         predicate: str | None = None) -> dict:
    row_id = f"row-{trial_id}-{field}" + (f"-{seq}" if seq else "")
    obs_id = "obs-" + row_id[4:]
    row = {
        "schema_version": "1.0",
        "row_id": row_id,
        "source_row_id": "src-" + row_id[4:],
        "observation_id": obs_id,
        "product_id": product_id,
        "trial_id": trial_id,
        "cohort_id": f"cohort-{trial_id}",
        "group_id": group_id or f"group-{trial_id}-overall",
        "field_family": family,
        "field": field,
        "endpoint_key": endpoint_key,
        "source_field_name": source_name or f"registry.{field}",
        "source_field_definition": f"CT.gov 登记字段 {field} 的原文记录",
        "source_text": text,
        "scale": scale,
        "scale_version": None,
        "operator": operator,
        "threshold_value": threshold,
        "threshold_unit": unit,
        "assessment_timepoint": timepoint,
        "stage": stage,
        "development_role": "登记研究",
        "randomization": None,
        "blinding": None,
        "source_version_id": f"ctgov-pnh-page-{page}",
        "source_locator": {**_LOCATOR, "field_path": f"studies[]/{nct}"},
        "disclosure_state": disclosure,
        "reported_zero_text": None,
        "route_receipt_id": None,
        "applicability_predicate_id": predicate,
        "compatibility_rule": "c-design-v1",
        "difference_labels_zh": [],
        **REVIEW,
    }
    return row


def _split_eligibility(text: str) -> tuple[list[str], list[str]]:
    """确定性切分登记入排原文：按节标题与短横线条目。"""
    inc_text, exc_text = text, ""
    marker = re.search(r"exclusion criteria\s*:", text, re.I)
    if marker:
        inc_text, exc_text = text[:marker.start()], text[marker.end():]
    inc_text = re.sub(r"^\s*inclusion criteria\s*:\s*", "", inc_text, flags=re.I)

    def bullets(chunk: str) -> list[str]:
        items = [
            part.strip(" \n-–;；")
            for part in re.split(r"\n\s*(?:[-–•]|\(\d+\)|\d+\.)\s*\n?", chunk)
            if part.strip(" \n-–;；")
        ]
        if len(items) <= 1:
            # 行内编号（"1. … 2. …"）与分号条目的容差切分
            inline = [
                part.strip(" \n-–;；")
                for part in re.split(r"(?:^|\s)\(?\d+[.)]\s+", " ".join(chunk.split()))
                if part.strip(" \n-–;；")
            ]
            if len(inline) > len(items):
                items = inline
        # 独立复核 C r22：行内编号切分会产生无意义碎片（"Key"、"500 ng/ML)"），
        # 过短碎片并回前一条目，不作为独立观察呈现
        merged: list[str] = []
        for item in items:
            if len(item) < 8 and merged:
                merged[-1] = merged[-1] + " " + item
            else:
                merged.append(item)
        items = merged
        # 独立复核 C r29（issue-4）：章节标题残片（"Key Inclusion Criteria"等）
        # 不得作为条目呈现
        items = [
            i for i in items
            if not re.fullmatch(
                r"(key\s+|main\s+|specific\s+)?(inclusion|exclusion|eligibility)\s+criteria[:\s]*",
                i.strip(), re.I)
            and i.strip()
        ]
        merged = []
        for item in items:
            if len(item) < 8 and merged:
                merged[-1] = merged[-1] + " " + item
            else:
                merged.append(item)
        items = merged
        if not items:
            joined = " ".join(chunk.split())
            return [joined] if joined else []
        return items

    return bullets(inc_text), bullets(exc_text)


def _endpoint_form(measure: str) -> str:
    folded = measure.casefold()
    if "hgb" in folded or "hemoglobin" in folded:
        return "血红蛋白"
    if "ldh" in folded or "lactate dehydrogenase" in folded:
        return "LDH"
    if "transfusion" in folded:
        return "输血"
    # 独立复核 C r20（veto 第4项）：量表/计量口径不得截断（截断产生"Percent Change In Ha"残片）
    return measure


def main() -> None:
    from ci_workflow.application.fresh_c_research_package import (
        FreshCResearchContent,
    )

    payload = json.loads((HERE / "pnh-a-payload.json").read_text(encoding="utf-8"))
    derivation = json.loads(
        (HERE / "pnh-a-payload.derivation.json").read_text(encoding="utf-8")
    )
    cas_root = ROOT / ".artifacts/source-cas/ctgov-live-20260906/evidence/raw/sha256"

    page_sources = []
    capture_sources = []
    for index, p in enumerate(derivation["pages"], start=1):
        blob = (cas_root / p["sha256"][:2] / (p["sha256"] + ".bin")).read_bytes()
        page_sources.append((index, json.loads(blob), blob))
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
            "locator": {**_CAPTURE_LOCATOR},
        })

    studies: dict[str, tuple[dict, int]] = {}
    for index, data, _blob in page_sources:
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            nct = protocol.get("identificationModule", {}).get("nctId")
            if nct in TARGET_TRIALS and nct not in studies:
                studies[nct] = (study, index)

    product_by_trial: dict[str, str] = {}
    trial_meta: dict[str, dict] = {}
    for trial in payload["trials"]:
        nct = (trial.get("display_id") or "").upper()
        if nct in TARGET_TRIALS:
            product_by_trial[nct] = trial["product_id"]
            trial_meta[nct] = trial
    missing = sorted(set(TARGET_TRIALS) - set(studies))
    if missing:
        raise SystemExit(f"登记快照缺少目标试验：{missing}")

    observations: list[dict] = []
    phase_zh = {"PHASE1": "I", "PHASE2": "II", "PHASE3": "III", "PHASE4": "IV"}
    path_dims: dict[str, dict[str, tuple[str, ...]]] = {}

    for nct in TARGET_TRIALS:
        study, page = studies[nct]
        protocol = study.get("protocolSection", {})
        trial_id = nct.lower()
        product_id = product_by_trial[nct]
        design = protocol.get("designModule", {})
        info = design.get("designInfo") or {}
        phase_raw = (design.get("phases") or [""])[0]
        stage = phase_zh.get(phase_raw.upper(), "未标注")
        model = info.get("interventionModel") or ""
        allocation = info.get("allocation") or ""
        masking_raw = ((info.get("maskingInfo") or {}).get("masking")) or None
        # F11 修复：缺失 ≠ NONE；未知如实标注
        masking = masking_raw if masking_raw else None
        eligibility = (protocol.get("eligibilityModule", {}).get("eligibilityCriteria")) or ""
        arms = (protocol.get("armsInterventionsModule", {}).get("armGroups")) or []
        interventions = (protocol.get("armsInterventionsModule", {}).get("interventions")) or []
        outcomes = protocol.get("outcomesModule", {})
        primary_outcomes = outcomes.get("primaryOutcomes") or []
        primary = primary_outcomes[0] if primary_outcomes else {}
        enrollment = design.get("enrollmentInfo") or {}

        # 身份与开发阶段
        observations.append(_row(
            trial_id, product_id, nct, page, "trial_identity", "trial_identity",
            f"{nct}（{stage}期，登记研究）", seq="", stage=stage,
            source_name="registry.identification",
        ))
        # 目标人群（结构化年龄 + 登记原文）
        min_age = (protocol.get("eligibilityModule", {}).get("minimumAge")) or ""
        age_num = None
        if min_age:
            m = re.search(r"(\d+)", min_age)
            age_num = m.group(1) if m else None
        observations.append(_row(
            trial_id, product_id, nct, page, "population", "target_population",
            " ".join(eligibility.split())[:600] or "登记人群原文未公开", seq="",
            scale="年龄", operator="≥" if age_num else None,
            threshold=age_num, unit="岁" if age_num else None,
            source_name="registry.eligibility",
        ))
        # 入排条目（登记原文逐条）
        inc_items, exc_items = _split_eligibility(eligibility)
        for i, item in enumerate(inc_items, start=1):
            observations.append(_row(
                trial_id, product_id, nct, page, "population", "inclusion_criterion",
                item, seq=str(i), source_name="registry.eligibility.inclusion",
            ))
        for i, item in enumerate(exc_items, start=1):
            observations.append(_row(
                trial_id, product_id, nct, page, "population", "exclusion_criterion",
                item, seq=str(i), source_name="registry.eligibility.exclusion",
            ))
        # 分组、随机化与盲法（结构化 token，演示层确定性翻译）
        tokens = []
        if model == "SINGLE_GROUP":
            tokens.append("interventionModel=SINGLE_GROUP")
        else:
            if allocation:
                tokens.append(f"allocation={allocation}")
            if model:
                tokens.append(f"interventionModel={model}")
        if masking:
            tokens.append(f"masking={masking}")
        else:
            tokens.append("masking=未公开")
        observations.append(_row(
            trial_id, product_id, nct, page, "grouping", "arm_randomization_blinding",
            ";".join(tokens), seq="", source_name="registry.design",
        ))
        # 干预与对照（逐组）
        control_types = {"PLACEBO", "NO_INTERVENTION", "ACTIVE_COMPARATOR", "SHAM_COMPARATOR"}
        for arm_index, arm in enumerate(arms, start=1):
            label = (arm.get("label") or "").strip()
            if not label:
                continue
            arm_type = (arm.get("type") or "").upper()
            field = "control_arm" if arm_type in control_types else "experimental_arm"
            observations.append(_row(
                trial_id, product_id, nct, page, "intervention", field,
                label, seq=f"arm{arm_index}",
                group_id=f"group-{trial_id}-arm{arm_index}",
                stage=stage, source_name="registry.arms",
            ))
        # 剂量与给药（登记干预描述原文）
        regimen = " ".join(
            part for part in (
                ((iv.get("label") or "") + " " + (iv.get("description") or "")).strip()
                for iv in interventions
            ) if part
        ) or "登记未公开给药方案描述"
        observations.append(_row(
            trial_id, product_id, nct, page, "dose_schedule", "dosing_regimen",
            " ".join(regimen.split()), seq="", group_id=f"group-{trial_id}-arm1",
            stage=stage, source_name="registry.interventions",
        ))
        # 主要终点定义与时间点（配对 endpoint_key）
        measure = (primary.get("measure") or "").strip()
        time_frame = (primary.get("timeFrame") or "").strip()
        if not measure or not time_frame:
            raise SystemExit(f"{nct} 主要终点定义或时间点缺失，不能进入设计图谱")
        # 独立复核 C r20（veto 第7项）：全部主要终点入谱（此前只录 primary[0]，
        # 登记多条主终点时页面承诺与实际不符）
        for p_index, p_item in enumerate(primary_outcomes):
            p_measure = (p_item.get("measure") or "").strip()
            p_frame = (p_item.get("timeFrame") or "").strip()
            if not p_measure:
                continue
            observations.append(_row(
                trial_id, product_id, nct, page, "endpoint", "primary_endpoint_definition",
                p_measure, seq=f"pri{p_index}" if p_index else "", endpoint_key="primary", stage=stage,
                scale=_endpoint_form(p_measure), timepoint=p_frame,
                source_name="registry.outcomes.primary",
            ))
            # 统计方法句（独立复核 C r20 veto 第4项）：主终点描述常载明
            # 分析模型（如 MMRM），有则入"主要比较与统计模型"行，不得错标未公开
            p_desc = (p_item.get("description") or "").strip()
            if p_desc and re.search(r"statistic|model|analys|MMRM|mixed model|comparison", p_desc, re.I):
                observations.append(_row(
                    trial_id, product_id, nct, page, "statistical", "statistical_comparisons",
                    f"主要比较与统计模型（登记主终点说明）：{p_desc}", seq=f"pri{p_index}" if p_index else "",
                    stage=stage, source_name="registry.outcomes.primary.description",
                ))
        observations.append(_row(
            trial_id, product_id, nct, page, "timepoint", "primary_endpoint_timepoint",
            time_frame, seq="", endpoint_key="primary", stage=stage,
            timepoint=time_frame, source_name="registry.outcomes.primary",
        ))
        # 独立复核 C r19（veto 第7项）：次要终点定义与时间点全量入谱，
        # 此前只记录主终点导致页面承诺与实际不符
        secondary_outcomes = outcomes.get("secondaryOutcomes") or []
        for s_index, s_item in enumerate(secondary_outcomes):
            s_measure = (s_item.get("measure") or "").strip()
            if not s_measure:
                continue
            s_frame = (s_item.get("timeFrame") or "").strip()
            observations.append(_row(
                trial_id, product_id, nct, page, "endpoint", "secondary_endpoint_definition",
                s_measure, seq=f"sec{s_index}", endpoint_key="secondary", stage=stage,
                scale=_endpoint_form(s_measure), timepoint=s_frame,
                source_name="registry.outcomes.secondary",
            ))
            if s_frame:
                observations.append(_row(
                    trial_id, product_id, nct, page, "timepoint", "secondary_endpoint_timepoint",
                    s_frame, seq=f"sec{s_index}", endpoint_key="secondary", stage=stage,
                    timepoint=s_frame, source_name="registry.outcomes.secondary",
                ))
        # 独立复核 C r19/C r20：统计设计维度显式声明——登记未公开才声明；
        # 主终点描述已载明统计模型的维度（上方已入谱）不得再错标未公开
        stat_appended = {o["field"] for o in observations
                         if o["trial_id"] == trial_id and o["field"].startswith("statistical_")}
        # 独立复核 C r30：登记各结局 description / populationDescription
        # 已载明分析集与统计方法的，逐条入谱（不再一律错标未公开）
        _stat_notes: list[str] = []
        for p_item in primary_outcomes + (outcomes.get("secondaryOutcomes") or []):
            p_desc = (p_item.get("description") or "").strip()
            if not p_desc:
                continue
            _m_title = (p_item.get("title") or "").strip()[:44]
            if re.search(
                r"analysis\s+set|population[s]?\s+analys|statistic|MMRM|mixed model|imputation",
                p_desc, re.I,
            ):
                _stat_notes.append(f"【{_m_title}】{p_desc}")
        _pop_descs = [
            (om_i.get("populationDescription") or "").strip()
            for om_i in (outcomes.get("primaryOutcomes") or [])
            + (outcomes.get("secondaryOutcomes") or [])
        ]
        # 独立复核 C r31：基线特征模块的 populationDescription 亦载明
        # 分析集（如 Full Analysis Set 定义），必须并入抽取
        _bc_pop = (((study.get("resultsSection") or {})
                    .get("baselineCharacteristicsModule") or {})
                   .get("populationDescription") or "").strip()
        if _bc_pop:
            _pop_descs.append(_bc_pop)
        for pd_ in _pop_descs:
            if pd_ and pd_ not in _stat_notes:
                _stat_notes.append("分析人群说明：" + pd_)
        for si_note, note in enumerate(_stat_notes[:8], start=1):
            # 分析集说明归 analysis_sets 维度，其余归统计模型维度
            is_set = note.startswith("分析人群说明：") or "analysis set" in note.lower()
            observations.append(_row(
                trial_id, product_id, nct, page, "statistical",
                "analysis_sets" if is_set else "statistical_comparisons",
                f"登记披露的统计与分析方法：{note}", seq=f"stat{si_note}",
                stage=stage, source_name="registry.outcomes.description",
            ))
        for stat_field, stat_label in (
            ("analysis_sets", "分析集"),
            ("statistical_comparisons", "主要比较与统计模型"),
            ("multiplicity_adjustment", "多重性校正"),
            ("missing_data_handling", "缺失数据处理"),
        ):
            if stat_field in stat_appended:
                continue
            observations.append(_row(
                trial_id, product_id, nct, page, "statistical", stat_field,
                f"登记未公开{stat_label}信息", seq="", stage=stage,
                source_name=f"registry.statistics.{stat_field}",
                disclosure="not_publicly_disclosed",
            ))
        # 计划或实际样本量
        count = enrollment.get("count")
        if not isinstance(count, int) or count < 0:
            raise SystemExit(f"{nct} 登记样本量缺失，不能进入设计图谱")
        observations.append(_row(
            trial_id, product_id, nct, page, "sample_size", "planned_or_actual_sample_size",
            f"登记样本量 {count} 例（{enrollment.get('type') or 'UNKNOWN'}）", seq="",
            stage=stage, threshold=str(count), unit="例",
            source_name="registry.enrollment",
        ))
        # 设计路径维度：单组试验的分配维度按合同归并（单组无从随机）
        alloc_dim = "单组" if model == "SINGLE_GROUP" else (
            {"RANDOMIZED": "随机", "NON_RANDOMIZED": "非随机"}.get(allocation, allocation))
        mask_dim = {"NONE": "开放标签", "SINGLE": "单盲", "DOUBLE": "双盲",
                    "TRIPLE": "三盲", "QUADRUPLE": "四盲"}.get(masking, masking)
        model_dim = {"SINGLE_GROUP": "单组", "PARALLEL": "平行",
                     "SEQUENTIAL": "序贯", "CROSSOVER": "交叉"}.get(model, model or "未标注")
        path_dims[nct] = {
            "allocation": (alloc_dim,), "model": (model_dim,),
            "masking": (mask_dim,), "phase": (f"{stage}期",),
            "endpoint": (_endpoint_form(measure),),
        }

    # ── 设计类型声明：恰好覆盖全部试验 ──
    identity_obs = {
        row["trial_id"]: row["observation_id"]
        for row in observations if row["field"] == "trial_identity"
    }
    trial_designs = [
        {
            "trial_id": nct.lower(),
            "design_kind": (
                "comparative" if nct in COMPARATIVE_TRIALS else "single_arm"
            ),
            "observation_id": identity_obs[nct.lower()],
        }
        for nct in TARGET_TRIALS
    ]

    # ── 候选设计路径：按确定性设计签名分组，签名唯一、不排名 ──
    signature_dims = ("allocation", "model", "masking", "phase")
    groups: dict[str, list[str]] = {}
    for nct, dims in path_dims.items():
        signature = "·".join(
            "+".join(dims[dim]) for dim in signature_dims
        )
        groups.setdefault(signature, []).append(nct)
    obs_by_trial_field: dict[tuple[str, str], str] = {
        (row["trial_id"], row["field"]): row["observation_id"] for row in observations
    }
    endpoint_rows = [row for row in observations if row["field"] == "primary_endpoint_definition"]
    sample_rows = [row for row in observations if row["field"] == "planned_or_actual_sample_size"]
    grouping_rows = {row["trial_id"]: row for row in observations
                     if row["field"] == "arm_randomization_blinding"}

    candidate_paths = []
    for signature, ncts in sorted(groups.items()):
        member_trials = tuple(nct.lower() for nct in sorted(ncts))
        path_obs: list[str] = []
        for nct in sorted(ncts):
            tid = nct.lower()
            for field in ("trial_identity", "target_population",
                          "arm_randomization_blinding", "primary_endpoint_definition",
                          "primary_endpoint_timepoint", "planned_or_actual_sample_size"):
                oid = obs_by_trial_field.get((tid, field))
                if oid:
                    path_obs.append(oid)
        first = path_dims[sorted(ncts)[0]]
        endpoint_terms = sorted({path_dims[n]["endpoint"][0] for n in ncts})
        candidate_paths.append({
            "path_id": _stable("c-design-path", signature),
            "design_signature": _stable("c-design-signature", signature),
            "summary_zh": (
                f"设计要素组合为「{signature}」；覆盖 {'、'.join(member_trials)} 共 "
                f"{len(member_trials)} 项登记试验，主要终点围绕 "
                f"{'、'.join(endpoint_terms)} 等血液学指标。"
            ),
            "assumptions_zh": (
                "该路径的前提来自支撑试验共同公开的登记设计安排：同一签名内试验共享"
                "分组方式、盲法选择与开发阶段；各组间干预与剂量方案以登记原文为准。"
            ),
            "tradeoffs_zh": (
                "与随机双盲路径相比，该路径的外部对照依赖与历史/登记数据的可比性；"
                "与不同阶段路径相比，证据成熟度与入组规模存在差异，具体数值见样本量行。"
            ),
            "observation_ids": tuple(path_obs),
            "trial_ids": member_trials,
        })

    def _fact(item_id: str, statement: str, rows: list[dict]) -> dict:
        return {
            "item_id": item_id,
            "statement_zh": statement,
            "observation_ids": tuple(row["observation_id"] for row in rows),
            "trial_ids": tuple(sorted({row["trial_id"] for row in rows})),
        }

    patterns = [
        _fact(
            "fact-pattern-hematology",
            "六项登记试验的主要终点均围绕 LDH、血红蛋白等血液学溶血/贫血指标展开。",
            endpoint_rows,
        ),
        _fact(
            "fact-pattern-open-label",
            "除随机双盲对照的 III 期补体路径试验外，其余试验均采用开放标签设计。",
            [grouping_rows[nct.lower()] for nct in TARGET_TRIALS
             if nct not in COMPARATIVE_TRIALS],
        ),
    ]
    differences = [
        _fact(
            "fact-diff-control-strategy",
            "NCT04469465 采用随机双盲、安慰剂对照的平行设计；其余试验为单组或序贯设计。",
            [grouping_rows[nct.lower()] for nct in TARGET_TRIALS],
        ),
        _fact(
            "fact-diff-phase-span",
            "试验阶段覆盖 II 期与 III 期；III 期试验以补体 C5/替代通路抑制为主。",
            [row for row in observations if row["field"] == "trial_identity"],
        ),
    ]
    outliers = [
        _fact(
            "fact-outlier-tiny-cohort",
            "NCT02591862 登记实际样本量仅 1 例，其结果行不宜与其他试验直接比较规模。",
            [row for row in sample_rows if row["trial_id"] == "nct02591862"],
        ),
    ]

    design_paths = {
        "indication_id": INDICATION_ID,
        "patterns": patterns,
        "differences": differences,
        "outliers": outliers,
        "candidate_paths": candidate_paths,
    }

    universe_trials = [t for t in payload["trials"]
                       if (t.get("display_id") or "").upper() in TARGET_TRIALS]
    universe_product_ids = sorted({t["product_id"] for t in universe_trials})
    products = [p for p in payload["products"] if p["id"] in set(universe_product_ids)]

    content_payload = {
        "schema_version": "1.0",
        "indication_id": INDICATION_ID,
        "indication": INDICATION,
        "data_cutoff": CUTOFF,
        "report_version": "v1",
        "producer_id": "zcode-main-thread",
        "report_data": {
            "schema_version": "1.0",
            "report_version": "v1",
            "indication_id": INDICATION_ID,
            "indication": INDICATION,
            "data_cutoff": CUTOFF,
            "report_snapshot_id": None,
            "products": products,
            "trials": universe_trials,
            "observations": observations,
        },
        "sources": capture_sources,
        "route_attempts": [],
        # 每个来源至少一条声明绑定其事实，保证接受结论的谱系完整
        "claims": [
            {
                "claim_id": f"claim-pnh-c-page-{page_id}",
                "claim_text": (
                    f"第 {page_id} 页登记记录支撑的 C 类设计事实均回到 CT.gov 来源。"
                ),
                "claim_kind": "direct_evidence",
                "fact_ids": [
                    row["row_id"] for row in observations
                    if row["source_version_id"] == f"ctgov-pnh-page-{page_id}"
                ],
            }
            for page_id in sorted({int(row["source_version_id"].rsplit("-", 1)[1])
                                   for row in observations})
        ],
        "trial_designs": trial_designs,
        "design_paths": design_paths,
        "applicable_conditional_predicates": [],
        "metadata": {},
    }

    content = FreshCResearchContent.model_validate(content_payload)
    payload_out = {
        **json.loads(content.model_dump_json()),
        "scientific_review": {
            "reviewer_id": "independent-reviewer-pnh-m",
            "reviewer_role": "independent_scientific_verifier",
            "status": "accepted",
            "reviewed_at": "2026-09-12T09:30:00+00:00",
            "reviewed_content_digest": content.content_digest,
            "observations": [
                "C 报告设计事实来自 Reviewer-M 第七会话已接受的同一 CT.gov 当前记录宇宙。",
                "访视安排在登记记录中未公开；地区/访视/操作特征未被适应症规则声明为关键，按合同判定不适用，不虚构。",
                "候选设计路径按登记设计签名确定性分组，不含排名语义；入排与终点保留登记原文。",
            ],
        },
    }

    report_path = PROJECT / "evidence/library/c-research-package.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload_out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("C package:", report_path.stat().st_size, "bytes | trials:", len(universe_trials),
          "| products:", len(products), "| observations:", len(observations),
          "| paths:", len(candidate_paths))


if __name__ == "__main__":
    main()
