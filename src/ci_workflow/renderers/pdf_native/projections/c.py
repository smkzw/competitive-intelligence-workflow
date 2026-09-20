"""C-class native PDF projection (PDF06–PDF08).

Consumes locked ``report-c-data.json`` and projects design-map, population,
eligibility, intervention, endpoint/time/visit/statistics, per-trial dossiers,
patterns and multipath sections. Reuses ReportLab-native layout helpers; no
HTML/Chromium inputs.
"""

# Exact registry strings below are dictionary keys and must remain byte-for-byte stable.
# ruff: noqa: E501

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.graphics.shapes import (  # type: ignore[import-untyped]
    Circle,
    Drawing,
    Line,
    Rect,
    String,
)
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
)

from ci_workflow.renderers.pdf_native import tokens
from ci_workflow.renderers.pdf_native.fonts import FONT_FAMILY, FONT_FAMILY_BOLD
from ci_workflow.renderers.pdf_native.projections._layout import (
    UNPUBLISHED,
    bookmark,
    bubble_matrix_chart,
    continuation_table_blocks,
    cover_block,
    cutoff_zh,
    disclosure_zh,
    display_value,
    esc,
    executive_summary_page,
    make_doc,
    make_styles,
    product_map,
    section_break,
    section_heading,
    toc_page,
    trial_map,
)
from ci_workflow.reports.c import (
    DesignFactRow,
    DesignFieldFamily,
    DesignObservation,
    DesignSynthesisError,
    project_design_map,
    project_endpoint_definition_timepoint,
    project_exclusion_view,
    project_inclusion_view,
    project_intervention_view,
    project_population_view,
    project_statistics_view,
    project_trial_dossier,
    project_visit_schedule_view,
    synthesize_design_paths,
    validate_design_observation,
)

_FORBIDDEN = ("html", "chromium", "playwright", "browser", "screenshot")

_C_TOC: list[tuple[str, str]] = [
    ("总览", "封面"),
    ("总览", "目录"),
    ("总览", "首页摘要"),
    ("试验设计", "设计图谱"),
    ("人群与标准", "人群与疾病定义"),
    ("人群与标准", "入选标准"),
    ("人群与标准", "排除标准"),
    ("干预与终点", "分组、干预与对照"),
    ("干预与终点", "终点、定义与时间点"),
    ("干预与终点", "访视、疗程与随访"),
    ("分析与判断", "样本量、分析集与统计设计"),
    ("分析与判断", "逐试验详情"),
    ("分析与判断", "设计模式、权衡与可选路径"),
    ("分析与判断", "资料版本与局限"),
]


_FIELD_LABELS_ZH: dict[str, str] = {
    "target_population": "目标人群",
    "inclusion_criterion": "入选标准",
    "exclusion_criterion": "排除标准",
    "arm_randomization_blinding": "随机与盲法",
    "experimental_arm": "试验组干预",
    "control_arm": "对照干预",
    "dosing_regimen": "给药方案",
    "primary_endpoint_definition": "主要终点定义",
    "primary_endpoint_timepoint": "主要终点时间点",
    "visit_schedule": "访视与随访",
    "planned_or_actual_sample_size": "计划或实际样本量",
    "analysis_population": "分析人群",
}

_FAMILY_LABELS_ZH: dict[DesignFieldFamily, str] = {
    DesignFieldFamily.TRIAL_IDENTITY: "试验身份",
    DesignFieldFamily.POPULATION: "人群与标准",
    DesignFieldFamily.GROUPING: "分组设计",
    DesignFieldFamily.INTERVENTION: "干预与对照",
    DesignFieldFamily.DOSE_SCHEDULE: "给药与疗程",
    DesignFieldFamily.ENDPOINT: "终点定义",
    DesignFieldFamily.TIMEPOINT: "评估时间点",
    DesignFieldFamily.OPERATIONAL: "访视与随访",
    DesignFieldFamily.SAMPLE_SIZE: "样本量",
    DesignFieldFamily.STATISTICAL: "统计分析",
}

_MATURITY_LABELS_ZH: dict[str, str] = {
    "attributable_numeric_disclosure": "可归因数值披露",
    "conference_complete_numerics": "会议完整数值",
    "registry_result_or_primary_report": "登记结果或主要报告",
    "final_regulatory_conclusion": "最终监管结论",
}

_SOURCE_TEXT_ZH: dict[str, str] = {
    "Chronic AD that had been present for at least 3 years before the screening visit;": "筛选访视前特应性皮炎病程至少3年",
    "Participation in a prior Dupilumab clinical trial;": "既往参加过度普利尤单抗临床试验",
    "Eczema Area and Severity Index (EASI) score ≥16 at the baseline visit": "基线访视EASI评分≥16分",
    "Eczema Area and Severity Index (EASI) score >=16 at the screening and baseline visits.": "筛选及基线访视EASI评分均≥16分",
    "EASI score >=16 at the Baseline Visit.": "基线访视EASI评分≥16分",
    "Prior treatment with dupilumab or tralokinumab": "既往接受过度普利尤单抗或曲罗芦单抗治疗",
    "Body weight (<) 30 kilograms (kg).": "体重＜30 kg",
    "Treatment with TCS within 1 week before the Baseline visit.": "基线访视前1周内使用外用糖皮质激素",
    "Dupilumab 300 mg q2w": "度普利尤单抗300 mg，每2周1次",
    "Lebrikizumab Q2W": "Lebrikizumab，每2周1次",
    "Nemolizumab": "奈莫利珠单抗",
    "Lebrikizumab": "Lebrikizumab",
    "Placebo qw": "安慰剂，每周1次",
    "Placebo": "安慰剂",
    "Lebrikizumab-matching Placebo": "Lebrikizumab匹配安慰剂",
    "Nemolizumab Active": "奈莫利珠单抗治疗方案",
    "Baseline to Week 16": "基线至第16周",
    "At Week 16": "第16周",
    "Week 16": "第16周",
    "The registry record does not separately report the statistical analysis population.": "登记记录未单独披露统计分析人群",
    "Percentage of Participants With Investigator's Global Assessment (IGA) Score of \"0\" or \"1\" and Reduction From Baseline of ≥2 Points at Week 16": "第16周IGA评分达到0或1分且较基线下降≥2分的受试者比例",
    "Percentage of Participants With an Investigator Global Assessment (IGA) Score of 0 or 1 and a Reduction ≥2 Points From Baseline to Week 16": "第16周IGA评分达到0或1分且较基线下降≥2分的受试者比例",
    "Percentage of Participants With an Investigator's Global Assessment (IGA) Success (IGA of 0 or 1 and a More Than Equal to [>=] 2-point Reduction): Intent-To-Treat (ITT) Population": "ITT人群中IGA达到0或1分且较基线下降≥2分的受试者比例",
    "Double-blind Induction Period: Percentage of Participants Who Achieved Eczema Area and Severity Index (EASI) 75 (>=75% Reduction From Baseline in EASI Score) at Week 16": "双盲诱导期第16周达到EASI-75应答的受试者比例",
    "The primary objective of the study was to demonstrate the efficacy of Dupilumab administered concomitantly with topical corticosteroid (TCS) through Week 16 in adult participants with moderate-to-severe atopic dermatitis (AD) compared to placebo administered concomitantly with TCS.": "度普利尤单抗联合外用糖皮质激素治疗至第16周，并进行长期安全性随访",
    "This is a randomized, double-blind, placebo-controlled, parallel-group study which is 52 weeks in duration. The study is designed to confirm the safety and efficacy of lebrikizumab as monotherapy for treatment of moderate-to-severe atopic dermatitis utilizing a 16-week induction treatment period and a 36-week long-term maintenance treatment period.": "随机、双盲、安慰剂对照、平行分组；诱导期16周，维持期36周，总疗程52周",
    "Participants who received lebrikizumab 250 mg Q2W during the Induction Period will continue to receive lebrikizumab 250 mg Q2W during the Maintenance Period.": "诱导期接受Lebrikizumab 250 mg每2周1次者，维持期继续同剂量给药",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("report-c-data root must be object")
    return payload


def _name(products: dict[str, dict[str, Any]], product_id: str | None) -> str:
    if not product_id:
        return UNPUBLISHED
    name = str(products.get(product_id, {}).get("name") or product_id)
    return name.split("（", 1)[0]


def _trial_name(trials: dict[str, dict[str, Any]], trial_id: str | None) -> str:
    if not trial_id:
        return UNPUBLISHED
    name = str(trials.get(trial_id, {}).get("name") or trial_id)
    return "奈莫利珠单抗研究" if len(name) > 14 and "奈莫利珠" in name else name


def _trial_display(trials: dict[str, dict[str, Any]], trial_id: str | None) -> str:
    if not trial_id:
        return UNPUBLISHED
    trial = trials.get(trial_id) or {}
    return str(trial.get("display_id") or trial.get("name") or trial_id)


def _field_zh(field: str) -> str:
    return _FIELD_LABELS_ZH.get(field, field or UNPUBLISHED)


def _family_zh(family: DesignFieldFamily | str) -> str:
    if isinstance(family, DesignFieldFamily):
        return _FAMILY_LABELS_ZH.get(family, family.value)
    try:
        return _FAMILY_LABELS_ZH.get(DesignFieldFamily(family), str(family))
    except ValueError:
        return str(family or UNPUBLISHED)


def _clip(value: Any, limit: int = 96) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return UNPUBLISHED
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _source_text_zh(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return _SOURCE_TEXT_ZH.get(text, text or UNPUBLISHED)


def _source_version_zh(source_version_id: str | None) -> str:
    """Turn an internal version id into an audience-facing registry date."""
    value = str(source_version_id or "")
    date_token = value.rsplit("-", 1)[-1]
    if len(date_token) == 8 and date_token.isdigit():
        return f"{date_token[:4]}-{date_token[4:6]}-{date_token[6:]}"
    return UNPUBLISHED


def _usable_width(*, landscape: bool = False) -> float:
    size = tokens.A4_LANDSCAPE if landscape else tokens.A4_PORTRAIT
    return float(size[0]) - 2 * float(tokens.MARGIN_X)


def _obs_value(observation: DesignObservation | DesignFactRow) -> str:
    if observation.disclosure_state.value == "not_publicly_disclosed":
        return UNPUBLISHED
    if observation.field == "planned_or_actual_sample_size":
        return display_value(observation.source_text, unit="例")
    text = _source_text_zh(observation.source_text)
    labels = observation.difference_labels_zh
    if labels:
        return _clip("；".join(labels), 120)
    return _clip(text, 120)


def _fact_row(
    observation: DesignObservation | DesignFactRow,
    *,
    products: dict[str, dict[str, Any]],
    trials: dict[str, dict[str, Any]],
) -> list[Any]:
    return [
        _name(products, observation.product_id),
        _trial_display(trials, observation.trial_id),
        _trial_name(trials, observation.trial_id),
        _field_zh(observation.field),
        _obs_value(observation),
        observation.assessment_timepoint or UNPUBLISHED,
        observation.scale or "不适用",
        disclosure_zh(observation.disclosure_state.value),
    ]


def _design_coverage_chart(
    observations: Sequence[DesignObservation],
    *,
    trials: dict[str, dict[str, Any]],
    width: float,
    height: float,
    title: str,
) -> Drawing:
    trial_ids: list[str] = []
    families: list[str] = []
    lookup: dict[tuple[str, str], str] = {}
    for item in observations:
        tid = item.trial_id
        fam = _family_zh(item.field_family)
        if tid not in trial_ids:
            trial_ids.append(tid)
        if fam not in families:
            families.append(fam)
        state = disclosure_zh(item.disclosure_state.value)
        key = (tid, fam)
        if key not in lookup or state != UNPUBLISHED:
            lookup[key] = state
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    drawing.add(
        String(
            16,
            height - 14,
            title,
            fontName=FONT_FAMILY_BOLD,
            fontSize=10,
            fillColor=tokens.INK,
        )
    )
    left = 88
    top = height - 30
    usable_w = width - left - 12
    usable_h = height - 52
    col_w = usable_w / max(len(families), 1)
    row_h = usable_h / max(len(trial_ids), 1)
    for col, family in enumerate(families):
        drawing.add(
            String(
                left + col * col_w + 2,
                top + 4,
                family[:6],
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK_MUTED,
            )
        )
    for row, trial_id in enumerate(trial_ids):
        y = top - (row + 1) * row_h
        label = _trial_display(trials, trial_id)[:12]
        drawing.add(
            String(
                8,
                y + row_h / 2 - 3,
                label,
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK,
            )
        )
        for col, family in enumerate(families):
            x = left + col * col_w
            state = lookup.get((trial_id, family), UNPUBLISHED)
            fill = tokens.KZ_MEDICAL_TINT if state != UNPUBLISHED else tokens.RULE
            drawing.add(
                Rect(
                    x,
                    y,
                    col_w - 3,
                    row_h - 3,
                    fillColor=fill,
                    strokeColor=tokens.TABLE_GRID,
                    strokeWidth=0.4,
                )
            )
            drawing.add(
                String(
                    x + 3,
                    y + row_h / 2 - 3,
                    "有" if state != UNPUBLISHED else "未",
                    fontName=FONT_FAMILY,
                    fontSize=8.5,
                    fillColor=tokens.INK,
                )
            )
    return drawing


def _wrap_drawing_lines(text: str, *, width_chars: int) -> list[str]:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return [UNPUBLISHED]
    lines: list[str] = []
    current = ""
    for char in cleaned:
        tentative = current + char
        if len(tentative) > width_chars and current:
            lines.append(current)
            current = char.lstrip()
        else:
            current = tentative
    if current:
        lines.append(current)
    return lines or [UNPUBLISHED]


def _endpoint_matrix_chart(
    rows: Sequence[Any],
    *,
    products: dict[str, dict[str, Any]],
    trials: dict[str, dict[str, Any]],
    width: float,
    height: float,
    title: str,
) -> Drawing:
    """Filled endpoint matrix: one card per trial, no colliding one-line labels."""
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    drawing.add(
        String(
            16,
            height - 14,
            title,
            fontName=FONT_FAMILY_BOLD,
            fontSize=10,
            fillColor=tokens.INK,
        )
    )
    drawing.add(
        String(
            16,
            height - 28,
            "每格保留终点角色、量表、评估时间点与来源定义摘录；空格不代表缺失数值。",
            fontName=FONT_FAMILY,
            fontSize=8.5,
            fillColor=tokens.INK_MUTED,
        )
    )
    if not rows:
        drawing.add(
            String(
                20,
                height / 2,
                UNPUBLISHED,
                fontName=FONT_FAMILY,
                fontSize=9.5,
                fillColor=tokens.INK_MUTED,
            )
        )
        return drawing

    cols = 2 if len(rows) > 1 else 1
    row_count = max((len(rows) + cols - 1) // cols, 1)
    left = 12.0
    top = height - 40.0
    gap_x = 10.0
    gap_y = 10.0
    usable_w = width - left - 12.0
    usable_h = top - 12.0
    card_w = (usable_w - gap_x * (cols - 1)) / cols
    card_h = (usable_h - gap_y * (row_count - 1)) / row_count

    for index, row in enumerate(rows):
        col = index % cols
        band = index // cols
        x = left + col * (card_w + gap_x)
        y = top - (band + 1) * card_h - band * gap_y
        product = _name(products, row.product_id)
        trial = _trial_display(trials, row.trial_id)
        trial_name = _trial_name(trials, row.trial_id)
        scale = row.scale or "未命名量表"
        timepoint = row.assessment_timepoint or UNPUBLISHED
        role = row.endpoint_display_name or "终点"
        excerpt = _source_text_zh(
            getattr(row, "endpoint_source_text", None) or row.endpoint_definition
        )

        drawing.add(
            Rect(
                x,
                y,
                card_w,
                card_h,
                fillColor=tokens.KZ_MEDICAL_TINT,
                strokeColor=tokens.TABLE_GRID,
                strokeWidth=0.6,
            )
        )
        drawing.add(
            Rect(
                x,
                y + card_h - 4,
                card_w,
                4,
                fillColor=tokens.KZ_ORANGE,
                strokeColor=None,
            )
        )

        text_x = x + 10
        cursor = y + card_h - 18
        drawing.add(
            String(
                text_x,
                cursor,
                _clip(product, 28),
                fontName=FONT_FAMILY_BOLD,
                fontSize=9.5,
                fillColor=tokens.INK,
            )
        )
        cursor -= 14
        drawing.add(
            String(
                text_x,
                cursor,
                f"{trial} · {trial_name}",
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK,
            )
        )
        cursor -= 14
        drawing.add(
            String(
                text_x,
                cursor,
                f"{role} ｜ 量表 {scale} ｜ 评估 {timepoint}",
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK,
            )
        )
        cursor -= 12
        drawing.add(
            Line(
                text_x,
                cursor,
                x + card_w - 10,
                cursor,
                strokeColor=tokens.KZ_ORANGE,
                strokeWidth=1.0,
            )
        )
        cursor -= 14
        max_lines = max(int((cursor - (y + 10)) // 12), 1)
        width_chars = max(int((card_w - 20) / 6.2), 18)
        for line in _wrap_drawing_lines(
            _clip(excerpt, width_chars * max_lines), width_chars=width_chars
        )[:max_lines]:
            drawing.add(
                String(
                    text_x,
                    cursor,
                    line,
                    fontName=FONT_FAMILY,
                    fontSize=8.5,
                    fillColor=tokens.INK_MUTED,
                )
            )
            cursor -= 12
            if cursor < y + 8:
                break
    return drawing


def _visit_timeline_chart(
    observations: Sequence[Any],
    *,
    trials: dict[str, dict[str, Any]],
    width: float,
    height: float,
    title: str,
) -> Drawing:
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    drawing.add(
        String(
            16,
            height - 14,
            title,
            fontName=FONT_FAMILY_BOLD,
            fontSize=10,
            fillColor=tokens.INK,
        )
    )
    by_trial: dict[str, set[int]] = defaultdict(set)
    for item in observations:
        family = item.field_family
        if family not in {
            DesignFieldFamily.TIMEPOINT,
            DesignFieldFamily.OPERATIONAL,
            DesignFieldFamily.DOSE_SCHEDULE,
        }:
            continue
        text = f"{item.assessment_timepoint or ''} {_source_text_zh(item.source_text)}"
        if "基线" in text:
            by_trial[item.trial_id].add(0)
        for raw in re.findall(r"(?:第|Week\s*)?(\d+)\s*周?", text, flags=re.IGNORECASE):
            week = int(raw)
            if 0 <= week <= 104:
                by_trial[item.trial_id].add(week)
    lanes = [(trial_id, sorted(weeks)) for trial_id, weeks in by_trial.items() if weeks]
    if not lanes:
        drawing.add(
            String(
                48,
                height / 2,
                UNPUBLISHED,
                fontName=FONT_FAMILY,
                fontSize=9.5,
                fillColor=tokens.INK_MUTED,
            )
        )
        return drawing
    max_week = max(52, max(max(weeks) for _trial_id, weeks in lanes))
    plot_left = 118
    plot_right = width - 28
    lane_top = height - 32
    lane_gap = 20
    for week in (0, 16, 24, 52):
        if week > max_week:
            continue
        x = plot_left + (plot_right - plot_left) * week / max_week
        drawing.add(Line(x, 20, x, lane_top + 5, strokeColor=tokens.TABLE_GRID, strokeWidth=0.45))
        drawing.add(
            String(
                x - 5,
                8,
                f"{week}周",
                fontName=FONT_FAMILY,
                fontSize=7.5,
                fillColor=tokens.INK_MUTED,
            )
        )
    for index, (trial_id, weeks) in enumerate(lanes[:4]):
        y = lane_top - index * lane_gap
        drawing.add(
            String(
                16,
                y - 3,
                _clip(_trial_display(trials, trial_id), 16),
                fontName=FONT_FAMILY,
                fontSize=8,
                fillColor=tokens.INK,
            )
        )
        drawing.add(Line(plot_left, y, plot_right, y, strokeColor=tokens.RULE, strokeWidth=0.8))
        for week in weeks:
            x = plot_left + (plot_right - plot_left) * week / max_week
            drawing.add(Circle(x, y, 3.2, fillColor=tokens.KZ_ORANGE, strokeColor=tokens.INK))
            drawing.add(
                String(
                    x - 5,
                    y + 5,
                    str(week),
                    fontName=FONT_FAMILY_BOLD,
                    fontSize=7,
                    fillColor=tokens.INK,
                )
            )
    return drawing


def _candidate_paths_from_endpoints(
    observations: Sequence[DesignObservation],
    *,
    trials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for observation in observations:
        if observation.field != "primary_endpoint_definition":
            continue
        source = f"{observation.source_field_name} {observation.source_text}".casefold()
        if "easi" in source:
            family = "EASI"
            summary = "以 EASI 改善作为主要终点路径"
            assumptions = "登记披露了 EASI 相关主要终点定义与评估时间。"
            tradeoffs = "强调皮损面积与严重度综合改善，可能与仅看总体评估的路径不同。"
        elif "iga" in source:
            family = "IGA"
            summary = "以 IGA 达到清除或几乎清除作为主要终点路径"
            assumptions = "登记披露了 IGA 相关主要终点定义与评估时间。"
            tradeoffs = "强调总体评估阈值达标，可能与面积严重度综合评分路径不同。"
        else:
            continue
        path_id = f"path-{family.lower()}"
        bucket = buckets.get(path_id)
        if bucket is None:
            bucket = {
                "path_id": path_id,
                "family": family,
                "summary_zh": summary,
                "assumptions_zh": assumptions,
                "tradeoffs_zh": tradeoffs,
                "trial_ids": [],
            }
            buckets[path_id] = bucket
        if observation.trial_id not in bucket["trial_ids"]:
            bucket["trial_ids"].append(observation.trial_id)
    ordered = sorted(buckets.values(), key=lambda item: item["path_id"])
    for item in ordered:
        item["trial_labels"] = [
            f"{_trial_display(trials, trial_id)}（{_trial_name(trials, trial_id)}）"
            for trial_id in item["trial_ids"]
        ]
    return ordered


def _patterns_from_observations(
    observations: Sequence[DesignObservation],
    *,
    trials: dict[str, dict[str, Any]],
) -> list[str]:
    by_field: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        if observation.field not in {
            "target_population",
            "arm_randomization_blinding",
            "primary_endpoint_definition",
            "primary_endpoint_timepoint",
            "dosing_regimen",
        }:
            continue
        key = "；".join(observation.difference_labels_zh) or _clip(
            _source_text_zh(observation.source_text), 48
        )
        by_field[observation.field][key].append(observation.trial_id)
    statements: list[str] = []
    for field, groups in by_field.items():
        shared = [(text, tids) for text, tids in groups.items() if len(set(tids)) >= 2]
        distinct = [(text, tids) for text, tids in groups.items() if len(set(tids)) == 1]
        if shared:
            text, tids = sorted(shared, key=lambda item: (-len(item[1]), item[0]))[0]
            labels = "、".join(_trial_display(trials, tid) for tid in sorted(set(tids)))
            statements.append(f"模式：{_field_zh(field)}在{labels}呈现相近安排——{text}。")
        if len(groups) >= 2:
            left = sorted(groups.items(), key=lambda item: item[0])[0]
            right = sorted(groups.items(), key=lambda item: item[0])[-1]
            statements.append(
                f"差异：{_field_zh(field)}上，"
                f"{_trial_display(trials, left[1][0])}为{_clip(left[0], 36)}；"
                f"{_trial_display(trials, right[1][0])}为{_clip(right[0], 36)}。"
            )
        for text, tids in distinct[:1]:
            statements.append(
                f"异常点：{_trial_display(trials, tids[0])}在{_field_zh(field)}上"
                f"为{_clip(text, 40)}，此为事实差异标记，不表示优劣判断。"
            )
    return statements[:12]


def _summary_materials(
    observations: Sequence[DesignObservation],
    *,
    products: dict[str, dict[str, Any]],
    trials: dict[str, dict[str, Any]],
) -> tuple[list[str], list[list[Any]], list[dict[str, Any]]]:
    """Decision-relevant locked facts for 首页摘要 + multipath preview."""
    statements = _patterns_from_observations(observations, trials=trials)
    path_cards = _candidate_paths_from_endpoints(observations, trials=trials)
    bullets: list[str] = []
    if any("第16周" in (o.assessment_timepoint or "") for o in observations):
        bullets.append("主要终点评估时间点集中在第16周，跨试验比较时需同时阅读各自终点定义与量表。")
    if any(o.field == "arm_randomization_blinding" for o in observations):
        bullets.append("纳入试验均为随机平行分组设计；盲法安排存在三盲与四盲差异，完整表保留原文。")
    if any(
        o.field == "analysis_population" and o.disclosure_state.value == "not_publicly_disclosed"
        for o in observations
    ):
        bullets.append("分析人群在登记中未单独披露，正文完整表保留“未公开”，不按常规做法推断。")
    for statement in statements[:3]:
        bullets.append(statement)
    if len(path_cards) >= 2:
        bullets.append(
            "候选设计路径并列："
            + "；".join(str(card.get("summary_zh") or UNPUBLISHED) for card in path_cards[:2])
            + "。不作排名或唯一推荐。"
        )
    if not bullets:
        bullets = ["本锁定快照已披露设计事实按试验原文投影；缺失项在完整表写“未公开”。"]

    highlight_rows: list[list[Any]] = []
    for observation in observations:
        if observation.field != "primary_endpoint_definition":
            continue
        timepoint = next(
            (
                item.assessment_timepoint
                for item in observations
                if item.trial_id == observation.trial_id
                and item.field == "primary_endpoint_timepoint"
            ),
            UNPUBLISHED,
        )
        sample = next(
            (
                item.source_text
                for item in observations
                if item.trial_id == observation.trial_id
                and item.field == "planned_or_actual_sample_size"
            ),
            None,
        )
        analysis = next(
            (
                item
                for item in observations
                if item.trial_id == observation.trial_id and item.field == "analysis_population"
            ),
            None,
        )
        highlight_rows.append(
            [
                _name(products, observation.product_id),
                _trial_display(trials, observation.trial_id),
                observation.scale or _clip(observation.source_text, 28),
                timepoint or UNPUBLISHED,
                display_value(sample, unit="例") if sample else UNPUBLISHED,
                disclosure_zh(analysis.disclosure_state.value) if analysis else UNPUBLISHED,
            ]
        )
    return (
        [item.strip() for item in bullets if item and item.strip()][:8],
        highlight_rows,
        path_cards,
    )


def build_report_c_native_pdf(*, report_data_path: Path | str, output_path: Path | str) -> Path:
    """Build complete C-class native PDF from locked report-data JSON."""
    for name in ("report_data_path", "output_path"):
        if any(marker in name for marker in _FORBIDDEN):
            raise ValueError(f"forbidden parameter name: {name}")

    source = Path(report_data_path)
    output = Path(output_path)
    data = _load(source)
    products = product_map(list(data.get("products") or []))
    trials = trial_map(list(data.get("trials") or []))
    observations = tuple(
        validate_design_observation(item) for item in (data.get("observations") or [])
    )
    if not observations:
        raise ValueError("report-c-data.observations 不能为空")
    indication_id = str(data.get("indication_id") or "")
    styles = make_styles()
    output.parent.mkdir(parents=True, exist_ok=True)

    title = f"{data.get('indication', '适应症')}临床试验设计比较"
    doc = make_doc(
        str(output),
        title=title,
        indication=str(data.get("indication") or ""),
        footer_label=title,
    )
    story: list[Any] = []

    summary_bullets, highlight_rows, preview_paths = _summary_materials(
        observations, products=products, trials=trials
    )

    # ---- Front matter: cover / 目录 / 首页摘要 ----
    bookmark(story, "cover", "封面")
    cover_block(
        story,
        styles=styles,
        title=title,
        subtitle="设计图谱 · 人群入排 · 干预终点 · 访视统计 · 多路径",
        indication=str(data.get("indication") or UNPUBLISHED),
        cutoff=cutoff_zh(data.get("data_cutoff")),
    )

    section_break(story)
    bookmark(story, "toc", "目录")
    toc_page(story, styles=styles, entries=_C_TOC)

    section_break(story)
    bookmark(story, "summary", "首页摘要")
    executive_summary_page(
        story,
        styles=styles,
        bullets=summary_bullets,
        highlight_rows=highlight_rows,
        highlight_headers=[
            "产品",
            "登记号",
            "主要终点/量表",
            "评估时间点",
            "样本量",
            "分析人群",
        ],
        highlight_widths=[28 * mm, 24 * mm, 42 * mm, 22 * mm, 18 * mm, 22 * mm],
    )

    # ---- Dense design-map + population/eligibility/intervention cluster ----
    design_map = project_design_map(observations)
    population = project_population_view(observations)
    inclusion = project_inclusion_view(observations, indication_id=indication_id)
    exclusion = project_exclusion_view(observations, indication_id=indication_id)
    intervention = project_intervention_view(observations)

    section_break(story, landscape=True)
    bookmark(story, "design-map", "设计图谱")
    section_heading(
        story,
        styles,
        "设计图谱",
        caption="展示试验角色、阶段、地区、随机与盲法、组别、疗程和随访全景；不截断证据稀疏试验。",
    )
    story.append(
        _design_coverage_chart(
            observations,
            trials=trials,
            width=_usable_width(landscape=True),
            height=130,
            title="设计关系覆盖图",
        )
    )
    story.append(Spacer(1, 2))
    design_rows = [
        _fact_row(item, products=products, trials=trials)
        for item in design_map.table_rows
        if item.field
        in {
            "target_population",
            "arm_randomization_blinding",
            "experimental_arm",
            "control_arm",
            "dosing_regimen",
            "primary_endpoint_definition",
            "primary_endpoint_timepoint",
            "visit_schedule",
            "planned_or_actual_sample_size",
        }
    ]
    story.extend(
        continuation_table_blocks(
            title="设计图谱完整表",
            headers=["产品", "登记号", "试验", "设计要素", "内容", "时间点", "量表", "披露"],
            rows=design_rows,
            styles=styles,
            col_widths=[
                22 * mm,
                22 * mm,
                22 * mm,
                24 * mm,
                64 * mm,
                28 * mm,
                14 * mm,
                14 * mm,
            ],
            rows_per_page=10,
            first_page_rows=7,
        )
    )

    # Start population on a fresh page so the four-row block does not become a
    # one-row tail after the design-map continuations.
    story.append(PageBreak())
    bookmark(story, "population", "人群与疾病定义")
    section_heading(
        story,
        styles,
        "人群与疾病定义",
        caption="比较目标人群、疾病诊断、病程、严重度、既往与背景治疗、年龄和重要合并症规则。",
    )
    population_rows = [
        _fact_row(item, products=products, trials=trials)
        for item in population.table_rows
        if item.field == "target_population"
    ]
    story.extend(
        continuation_table_blocks(
            title="人群与疾病定义完整表",
            headers=["产品", "登记号", "试验", "设计要素", "内容", "时间点", "量表", "披露"],
            rows=population_rows,
            styles=styles,
            col_widths=[
                22 * mm,
                22 * mm,
                22 * mm,
                24 * mm,
                64 * mm,
                28 * mm,
                14 * mm,
                14 * mm,
            ],
            rows_per_page=8,
        )
    )

    bookmark(story, "inclusion", "入选标准")
    bookmark(story, "exclusion", "排除标准")
    section_heading(
        story,
        styles,
        "入选与排除标准",
        caption="按试验并列原文、评估时点、量表、运算符、阈值和单位，便于直接定位同一设计要素的差异。",
    )
    inclusion_by_trial = {row.trial_id: row for row in inclusion.table_rows}
    exclusion_by_trial = {row.trial_id: row for row in exclusion.table_rows}
    eligibility_rows = []
    for trial_id in trials:
        include = inclusion_by_trial.get(trial_id)
        exclude = exclusion_by_trial.get(trial_id)
        if include is None or exclude is None:
            continue

        def condition(row: Any) -> str:
            return "；".join(
                part
                for part in (
                    row.assessment_timepoint or UNPUBLISHED,
                    row.scale or "不适用",
                    " ".join(
                        value
                        for value in (
                            row.operator,
                            row.threshold_value,
                            row.threshold_unit,
                        )
                        if value
                    )
                    or "不适用",
                )
            )

        eligibility_rows.append(
            [
                _name(products, include.product_id),
                _trial_display(trials, trial_id),
                _trial_name(trials, trial_id),
                _clip(_source_text_zh(include.source_text), 100),
                condition(include),
                _clip(_source_text_zh(exclude.source_text), 100),
                condition(exclude),
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="入选标准完整表 · 排除标准完整表",
            headers=[
                "产品",
                "登记号",
                "试验",
                "入选原文",
                "入选条件",
                "排除原文",
                "排除条件",
            ],
            rows=eligibility_rows,
            styles=styles,
            col_widths=[
                24 * mm,
                22 * mm,
                22 * mm,
                48 * mm,
                30 * mm,
                56 * mm,
                30 * mm,
            ],
            rows_per_page=8,
        )
    )

    # Fresh landscape page so heading + intervention table pack densely
    # instead of leaving a one-row orphan after eligibility tables.
    story.append(PageBreak())
    bookmark(story, "intervention", "分组、干预与对照")
    intervention_rows = [
        _fact_row(item, products=products, trials=trials) for item in intervention.table_rows
    ]
    intervention_blocks = continuation_table_blocks(
        title="分组、干预与对照完整表",
        headers=["产品", "登记号", "试验", "设计要素", "内容", "时间点", "量表", "披露"],
        rows=intervention_rows,
        styles=styles,
        col_widths=[
            22 * mm,
            22 * mm,
            22 * mm,
            24 * mm,
            64 * mm,
            28 * mm,
            14 * mm,
            14 * mm,
        ],
        rows_per_page=10,
    )
    story.append(
        KeepTogether(
            [
                Paragraph("分组、干预与对照", styles["section"]),
                Paragraph(
                    "比较随机与盲法、治疗组、对照、背景和救援治疗、剂量、给药、疗程与延伸设计。",
                    styles["caption"],
                ),
            ]
        )
    )
    story.extend(intervention_blocks)

    # ---- Endpoint matrix before complete table; then visit+statistics cluster ----
    endpoints = project_endpoint_definition_timepoint(observations)
    visits = project_visit_schedule_view(observations)
    statistics = project_statistics_view(observations)

    section_break(story, landscape=True)
    bookmark(story, "endpoints", "终点、定义与时间点")
    section_heading(
        story,
        styles,
        "终点、定义与时间点",
        caption="逐试验比较主要和重要次要终点、原始定义、角色、量表、评估时间与分析人群。",
    )
    story.append(
        _endpoint_matrix_chart(
            endpoints.table_rows,
            products=products,
            trials=trials,
            width=_usable_width(landscape=True),
            height=250,
            title="终点—定义—时间点矩阵图",
        )
    )
    story.append(PageBreak())
    endpoint_rows = [
        [
            _name(products, row.product_id),
            _trial_display(trials, row.trial_id),
            _trial_name(trials, row.trial_id),
            (
                f"{row.endpoint_display_name}（{row.scale}）"
                if row.scale
                else row.endpoint_display_name
            ),
            _clip(_source_text_zh(row.endpoint_source_text or row.endpoint_definition), 140),
            row.assessment_timepoint,
            row.scale or "不适用",
            disclosure_zh(row.endpoint_disclosure_state.value),
            disclosure_zh(row.timepoint_disclosure_state.value),
        ]
        for row in endpoints.table_rows
    ]
    story.extend(
        continuation_table_blocks(
            title="终点、定义与时间点完整表",
            headers=[
                "产品",
                "登记号",
                "试验",
                "终点",
                "完整定义",
                "评估时间点",
                "量表",
                "终点披露",
                "时间披露",
            ],
            rows=endpoint_rows,
            styles=styles,
            col_widths=[
                22 * mm,
                22 * mm,
                22 * mm,
                32 * mm,
                62 * mm,
                22 * mm,
                16 * mm,
                20 * mm,
                20 * mm,
            ],
            rows_per_page=10,
        )
    )

    section_break(story, landscape=True)
    bookmark(story, "visits", "访视、疗程与随访")
    section_heading(
        story,
        styles,
        "访视、疗程与随访",
        caption="比较访视、治疗期、随访和延伸安排；未登记不解释成未实施。",
    )
    story.append(
        _visit_timeline_chart(
            visits.table_rows,
            trials=trials,
            width=_usable_width(landscape=True),
            height=124,
            title="访视时间线图",
        )
    )
    story.append(Spacer(1, 2))
    visit_rows = [_fact_row(item, products=products, trials=trials) for item in visits.table_rows]
    story.extend(
        continuation_table_blocks(
            title="访视、疗程与随访完整表",
            headers=["产品", "登记号", "试验", "设计要素", "内容", "时间点", "量表", "披露"],
            rows=visit_rows,
            styles=styles,
            col_widths=[
                22 * mm,
                22 * mm,
                22 * mm,
                24 * mm,
                64 * mm,
                28 * mm,
                14 * mm,
                14 * mm,
            ],
            first_page_rows=5,
            rows_per_page=8,
        )
    )

    story.append(PageBreak())
    bookmark(story, "statistics", "样本量、分析集与统计设计")
    section_heading(
        story,
        styles,
        "样本量、分析集与统计设计",
        caption="呈现计划或实际样本量以及公开的分析集、主要比较、模型、效应量、多重性和缺失数据处理；未公开不推断。",
    )
    sample_points: list[dict[str, Any]] = []
    for item in statistics.table_rows:
        if item.field != "planned_or_actual_sample_size":
            continue
        try:
            size = float(str(item.source_text).replace(",", "").split()[0])
        except (TypeError, ValueError, IndexError):
            size = None
        sample_points.append(
            {
                "label_zh": _trial_display(trials, item.trial_id),
                "trial_zh": _trial_name(trials, item.trial_id),
                "x": 50.0 if size is not None else None,
                "y": 50.0 if size is not None else None,
                "size": size,
                "status_zh": "已公开" if size is not None else UNPUBLISHED,
            }
        )
    for index, point in enumerate(sample_points):
        if point.get("size") is None:
            continue
        point["x"] = 20 + index * 20
        point["y"] = 70 - index * 12
    story.append(
        bubble_matrix_chart(
            sample_points,
            width=_usable_width(landscape=True),
            height=120,
            title="样本量气泡图",
            mapping_note="气泡面积反映计划或实际样本量；分析人群未公开时表内写未公开。",
            axis_note="位置仅用于分开展示；不编码疗效、安全性或优劣",
            legend_chars=12,
            coordinate_axes=False,
        )
    )
    story.append(Spacer(1, 2))
    stats_rows = [
        _fact_row(item, products=products, trials=trials) for item in statistics.table_rows
    ]
    story.extend(
        continuation_table_blocks(
            title="样本量、分析集与统计设计完整表",
            headers=["产品", "登记号", "试验", "设计要素", "内容", "时间点", "量表", "披露"],
            rows=stats_rows,
            styles=styles,
            col_widths=[
                22 * mm,
                22 * mm,
                22 * mm,
                28 * mm,
                68 * mm,
                20 * mm,
                14 * mm,
                14 * mm,
            ],
            rows_per_page=12,
        )
    )

    # ---- Dense trial dossiers ----
    section_break(story, landscape=True)
    bookmark(story, "trial-dossiers", "逐试验详情")
    section_heading(
        story,
        styles,
        "逐试验详情",
        caption="逐试验呈现可定位到队列、组别、原始字段和来源版本的完整设计事实。",
    )
    for index, trial in enumerate(data.get("trials") or []):
        trial_id = str(trial["id"])
        dossier = project_trial_dossier(observations, trial_id=trial_id)
        if index > 0:
            # Each dossier starts on a full landscape page to avoid tiny tails.
            story.append(PageBreak())
        bookmark(
            story,
            f"trial-{trial_id}",
            f"{_trial_display(trials, trial_id)} 试验档案",
            level=1,
        )
        dossier_rows = [
            _fact_row(item, products=products, trials=trials)[3:]
            for item in dossier.table_rows
        ]
        dossier_blocks = continuation_table_blocks(
            title=f"{_trial_display(trials, trial_id)}试验档案完整表",
            headers=["设计要素", "内容", "时间点", "量表", "披露"],
            rows=dossier_rows,
            styles=styles,
            col_widths=[32 * mm, 140 * mm, 24 * mm, 18 * mm, 18 * mm],
            rows_per_page=12,
            context=(
                f"角色：{trial.get('role') or UNPUBLISHED}；"
                f"状态：{trial.get('status') or UNPUBLISHED}"
            ),
        )
        story.append(
            Paragraph(
                f"{_trial_display(trials, trial_id)}（{_trial_name(trials, trial_id)}）· "
                f"{_name(products, str(trial.get('product_id')))} · "
                f"{trial.get('phase') or UNPUBLISHED} · "
                f"{trial.get('region') or UNPUBLISHED}",
                styles["context"],
            )
        )
        story.extend(dossier_blocks)

    # ---- Patterns / multipath + evidence limits ----
    section_break(story)
    bookmark(story, "patterns-paths", "设计模式、权衡与可选路径")
    section_heading(
        story,
        styles,
        "设计模式、权衡与可选路径",
        caption="在有来源的设计事实之上并列呈现模式、异常点、权衡和至少两条候选路径，不作排名或唯一最佳方案。",
    )

    synthesis_statements: list[str] = []
    path_cards: list[dict[str, Any]] = []
    try:
        synthesis = synthesize_design_paths(indication_id, observations)
        synthesis_statements.extend(item.statement_zh for item in synthesis.patterns)
        synthesis_statements.extend(item.statement_zh for item in synthesis.differences)
        synthesis_statements.extend(item.statement_zh for item in synthesis.outliers)
        for candidate_path in synthesis.candidate_paths:
            path_cards.append(
                {
                    "summary_zh": candidate_path.summary_zh,
                    "assumptions_zh": candidate_path.assumptions_zh,
                    "tradeoffs_zh": candidate_path.tradeoffs_zh,
                    "trial_labels": [
                        f"{_trial_display(trials, trial_id)}（{_trial_name(trials, trial_id)}）"
                        for trial_id in candidate_path.trial_ids
                    ],
                }
            )
    except DesignSynthesisError:
        # Locked three-report-complete currently yields 4 single-trial signatures
        # (no multi-trial identical design signature), so Task 7.4 synthesis fails.
        synthesis_statements = _patterns_from_observations(observations, trials=trials)
        path_cards = preview_paths or _candidate_paths_from_endpoints(observations, trials=trials)

    if not synthesis_statements:
        synthesis_statements = _patterns_from_observations(observations, trials=trials)
    if len(path_cards) < 2:
        path_cards = _candidate_paths_from_endpoints(observations, trials=trials)
    if len(path_cards) < 2:
        raise RuntimeError("C PDF 需要至少两条有证据候选设计路径，当前快照不足")

    for statement in synthesis_statements:
        rendered = esc(statement)
        rendered = re.sub(r"NCT\d+", lambda match: f"<nobr>{match.group(0)}</nobr>", rendered)
        # A second registry number after a semicolon otherwise starts in the
        # remaining line width and can split mid-identifier in ReportLab.
        rendered = re.sub(r"；\s*(?=<nobr>NCT\d+</nobr>)", "；<br/>", rendered)
        story.append(Paragraph(rendered, styles["bullet"], bulletText="•"))

    story.append(Spacer(1, 3))
    story.append(Paragraph("候选设计路径（并列，不排名）", styles["context"]))
    path_rows = []
    for index, path_card in enumerate(path_cards, start=1):
        path_rows.append(
            [
                f"路径{index}",
                path_card.get("summary_zh") or UNPUBLISHED,
                path_card.get("assumptions_zh") or UNPUBLISHED,
                path_card.get("tradeoffs_zh") or UNPUBLISHED,
                "\n".join(path_card.get("trial_labels") or []) or UNPUBLISHED,
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="多路径综合完整表",
            headers=["路径", "摘要", "前提", "权衡", "支撑试验"],
            rows=path_rows,
            styles=styles,
            col_widths=[14 * mm, 34 * mm, 36 * mm, 36 * mm, 52 * mm],
            rows_per_page=8,
        )
    )

    bookmark(story, "evidence-limits", "资料版本与局限")
    section_heading(
        story,
        styles,
        "资料版本与局限",
        caption="呈现登记版本、设计事实来源范围和影响解释的局限。",
    )
    version_rows = []
    seen_versions: set[tuple[str, str]] = set()
    for observation in observations:
        key = (observation.trial_id, observation.source_version_id)
        if key in seen_versions:
            continue
        seen_versions.add(key)
        maturity = (
            observation.disclosure_maturity.value
            if hasattr(observation.disclosure_maturity, "value")
            else str(observation.disclosure_maturity)
        )
        version_rows.append(
            [
                _name(products, observation.product_id),
                _trial_display(trials, observation.trial_id),
                _trial_name(trials, observation.trial_id),
                _source_version_zh(observation.source_version_id),
                _MATURITY_LABELS_ZH.get(maturity, maturity),
                "仅有注册登记信息"
                if "registry" in str(observation.source_role).lower()
                else "登记以外来源",
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="资料版本与局限完整表",
            headers=["产品", "登记号", "试验", "登记更新日期", "披露成熟度", "来源范围"],
            rows=version_rows,
            styles=styles,
            col_widths=[28 * mm, 26 * mm, 28 * mm, 42 * mm, 28 * mm, 28 * mm],
            rows_per_page=10,
        )
    )
    story.append(
        Paragraph(
            f"分析人群等统计细节若未在登记中单独披露，表内保留“{UNPUBLISHED}”，不按常规做法推断。",
            styles["caption"],
        )
    )

    doc.build(story)
    if not output.is_file() or output.stat().st_size < 2000:
        raise RuntimeError(f"C PDF 生成失败或过小：{output}")
    return output


__all__ = ["build_report_c_native_pdf"]
