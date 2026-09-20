"""B-class native PDF projection (PDF03–PDF05)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import KeepTogether, Paragraph, Spacer  # type: ignore[import-untyped]

from ci_workflow.renderers.pdf_native.projections._layout import (
    UNPUBLISHED,
    bookmark,
    bubble_matrix_chart,
    continuation_table_blocks,
    cover_block,
    cutoff_zh,
    disclosure_zh,
    display_value,
    efficacy_forest_chart,
    efficacy_grouped_bar_chart,
    executive_summary_page,
    longitudinal_line_chart,
    make_doc,
    make_styles,
    product_map,
    safety_heatmap_chart,
    section_break,
    section_heading,
    styled_table,
    toc_page,
    trial_map,
)

_FORBIDDEN = ("html", "chromium", "playwright", "browser", "screenshot")

_NATIVE_LABELS = {
    "baseline_sample_size": "样本量",
    "age": "年龄",
    "sex": "性别",
    "baseline_easi": "基线EASI",
    "baseline_hemoglobin": "基线血红蛋白",
    "demographics": "人口学",
    "baseline_severity": "基线疾病严重程度",
    "disease_context": "疾病语境",
    "screened": "已筛选",
    "screen_failure": "筛败",
    "randomized": "已随机",
    "received_treatment": "已接受治疗",
    "completed_treatment": "完成治疗",
    "completed_study": "完成研究",
    "treatment_discontinued": "停止治疗",
    "study_withdrawal": "退出研究",
    "lost_to_follow_up": "失访",
    "adherence": "依从性",
    "rescue_treatment": "补救治疗",
    "prohibited_medication": "禁用药",
    "protocol_deviation": "方案偏离",
    "major_protocol_deviation": "重要方案偏离",
    "protocol_deviation_leading_to_exclusion": "导致排除的方案偏离",
    "participant_flow": "受试者流转",
    "reason": "原因",
    "screen_failure_reason": "筛败原因",
    "treatment_discontinuation_reason": "停止治疗原因",
    "study_withdrawal_reason": "退出研究原因",
    "treatment": "治疗组",
    "control": "对照组",
    "placebo": "对照组",
    "sample_size": "例数",
    "mean": "均值",
    "proportion": "构成比",
    "source_other": "其他来源",
}

_DISEASE_CONTEXT_VARS = (
    ("disease_duration", "病程"),
    ("prior_systemic_therapy", "既往系统治疗"),
    ("phenotype", "表型"),
    ("comorbidity", "相关合并症"),
)

_B_TOC: list[tuple[str, str]] = [
    ("总览", "封面"),
    ("总览", "目录"),
    ("总览", "首页摘要"),
    ("疗效与安全性", "疗效"),
    ("疗效与安全性", "纵向结果"),
    ("疗效与安全性", "安全性"),
    ("疗效与安全性", "疗效与安全性矩阵"),
    ("基线与人群", "基线与人群总览"),
    ("基线与人群", "人口学"),
    ("基线与人群", "疾病语境"),
    ("基线与人群", "基线疾病严重程度"),
    ("试验完成情况", "试验完成情况"),
    ("试验完成情况", "受试者流转"),
    ("试验完成情况", "依从性"),
    ("试验完成情况", "失访与退出"),
    ("试验完成情况", "筛败与原因"),
    ("试验完成情况", "补救治疗"),
    ("试验完成情况", "禁用药使用"),
    ("试验完成情况", "方案偏离"),
    ("试验与证据", "试验与暴露语境"),
    ("试验与证据", "亚组与支持证据"),
    ("试验与证据", "产品与试验档案"),
    ("试验与证据", "研究依据与局限"),
]


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("report-b-data root must be object")
    return payload


def _label(value: Any) -> str:
    text = "" if value is None else str(value)
    return _NATIVE_LABELS.get(text, text or UNPUBLISHED)


def _name(products: dict[str, dict[str, Any]], product_id: str | None) -> str:
    if not product_id:
        return UNPUBLISHED
    return str(products.get(product_id, {}).get("name") or product_id)


def _trial_name(trials: dict[str, dict[str, Any]], trial_id: str | None) -> str:
    if not trial_id:
        return UNPUBLISHED
    return str(trials.get(trial_id, {}).get("name") or trial_id)


def _arm_zh(value: Any, group_id: Any = None) -> str:
    raw = str(value or group_id or "")
    lowered = raw.lower()
    if "treatment" in lowered or raw == "治疗组":
        return "治疗组"
    if "control" in lowered or "placebo" in lowered or raw in {"对照组", "安慰剂组"}:
        return "对照组"
    return _label(raw)


def _usable_width(*, landscape: bool = False) -> float:
    from ci_workflow.renderers.pdf_native import tokens

    size = tokens.A4_LANDSCAPE if landscape else tokens.A4_PORTRAIT
    return float(size[0]) - 2 * float(tokens.MARGIN_X)


def _facts(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    block = data.get(key) or {}
    if isinstance(block, dict):
        return list(block.get("facts") or [])
    return []


def build_report_b_native_pdf(*, report_data_path: Path | str, output_path: Path | str) -> Path:
    """Build complete B-class native PDF from locked report-data JSON."""
    for name in ("report_data_path", "output_path"):
        if any(marker in name for marker in _FORBIDDEN):
            raise ValueError(f"forbidden parameter name: {name}")

    source = Path(report_data_path)
    output = Path(output_path)
    data = _load(source)
    products = product_map(list(data.get("products") or []))
    trials = trial_map(list(data.get("trials") or []))
    styles = make_styles()
    output.parent.mkdir(parents=True, exist_ok=True)

    title = f"{data.get('indication', '适应症')}临床试验结果比较"
    doc = make_doc(
        str(output),
        title=title,
        indication=str(data.get("indication") or ""),
        footer_label=title,
    )
    story: list[Any] = []

    bookmark(story, "cover", "封面")
    cover_block(
        story,
        styles=styles,
        title=title,
        subtitle="疗效纵向 · 安全性矩阵 · 基线完成 · 试验档案",
        indication=str(data.get("indication") or UNPUBLISHED),
        cutoff=cutoff_zh(data.get("data_cutoff")),
    )

    section_break(story)
    bookmark(story, "toc", "目录")
    toc_page(story, styles=styles, entries=_B_TOC)

    section_break(story)
    bookmark(story, "summary", "首页摘要")
    summary_bullets = [
        f"范围内产品 {len(products)} 个、试验 {len(trials)} 项；治疗组与对照组并列比较。",
        "疗效/纵向/安全性先图后表；分母、时间点、人群与披露状态在完整表中保留。",
        "基线与完成字段按试验×组别展开；未公开数值准确写“未公开”，不作零填充。",
    ]
    highlight_rows = []
    for row in data.get("efficacy") or []:
        if row.get("arm") != "治疗组" or row.get("value") is None:
            continue
        control = next(
            (
                item
                for item in data.get("efficacy") or []
                if item.get("product_id") == row.get("product_id")
                and item.get("trial_id") == row.get("trial_id")
                and item.get("arm") in {"对照组", "安慰剂组"}
                and item.get("value") is not None
            ),
            None,
        )
        delta = float(row["value"]) - float(control["value"]) if control is not None else None
        highlight_rows.append(
            [
                _name(products, str(row.get("product_id"))),
                _trial_name(trials, row.get("trial_id")),
                str(row.get("endpoint") or UNPUBLISHED),
                display_value(row.get("value"), unit="%"),
                display_value(None if control is None else control.get("value"), unit="%"),
                "—" if delta is None else f"{delta:+.1f} 百分点",
            ]
        )
    executive_summary_page(
        story,
        styles=styles,
        bullets=summary_bullets,
        highlight_rows=highlight_rows,
        highlight_headers=["产品", "试验", "终点", "治疗组", "对照组", "组间差值"],
        highlight_widths=[28 * mm, 24 * mm, 36 * mm, 22 * mm, 22 * mm, 28 * mm],
    )

    # ---- PDF03 efficacy / longitudinal / safety / matrix ----
    efficacy_rows = list(data.get("efficacy") or [])
    efficacy_points = [
            {
                "product_zh": _name(products, row.get("product_id")),
                "trial_id": row.get("trial_id"),
                "trial_zh": _trial_name(trials, row.get("trial_id")),
            "arm_zh": _arm_zh(row.get("arm")),
            "endpoint_zh": str(row.get("endpoint") or UNPUBLISHED),
            "timepoint_zh": str(row.get("timepoint") or UNPUBLISHED),
            "population_zh": str(row.get("population") or UNPUBLISHED),
            "value": row.get("value"),
            "unit": str(row.get("unit") or "%"),
            "numerator": row.get("numerator"),
            "denominator": row.get("denominator"),
        }
        for row in efficacy_rows
    ]
    forest_rows: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for point in efficacy_points:
        if point.get("value") is None:
            continue
        by_key[(point["product_zh"], point["trial_zh"])][point["arm_zh"]] = float(point["value"])
    for (product, trial), arms in by_key.items():
        if "治疗组" in arms and "对照组" in arms:
            forest_rows.append(
                {"label_zh": f"{product}/{trial}", "difference": arms["治疗组"] - arms["对照组"]}
            )

    section_break(story, landscape=True)
    bookmark(story, "efficacy", "疗效")
    section_heading(
        story,
        styles,
        "疗效",
        caption="展示全部已抽取终点；治疗组与对照组并列。含柱状图、不合并森林图与完整数据表。",
    )
    story.append(Paragraph("疗效比较柱状图", styles["caption"]))
    story.append(
        efficacy_grouped_bar_chart(
            efficacy_points,
            width=_usable_width(landscape=True),
            height=110,
            title="疗效比较柱状图 · 治疗组与对照组",
        )
    )
    story.append(Spacer(1, 2))
    story.append(Paragraph("疗效森林图", styles["caption"]))
    story.append(
        efficacy_forest_chart(
            forest_rows,
            width=_usable_width(landscape=True),
            height=90,
            title="疗效森林图 · 治疗—对照差值",
        )
    )
    story.append(Spacer(1, 3))
    story.append(Paragraph("疗效完整数据表", styles["caption"]))
    story.append(
        styled_table(
            ["产品", "试验", "组别", "终点", "时间点", "数值", "例数", "人群"],
            [
                [
                    pt["product_zh"],
                    pt["trial_zh"],
                    pt["arm_zh"],
                    pt["endpoint_zh"],
                    pt["timepoint_zh"],
                    display_value(pt["value"], unit=pt["unit"]),
                    (
                        f"{pt['numerator']}/{pt['denominator']}"
                        if pt.get("numerator") is not None and pt.get("denominator") is not None
                        else UNPUBLISHED
                    ),
                    pt["population_zh"],
                ]
                for pt in efficacy_points
            ],
            styles,
            [24 * mm, 24 * mm, 16 * mm, 32 * mm, 18 * mm, 18 * mm, 20 * mm, 22 * mm],
        )
    )

    # The compact efficacy rows are the report-level source of truth. Detailed
    # views are a fallback only; mixing both can put contradictory values for
    # the same product/trial/arm on adjacent pages.
    view_facts = [] if efficacy_points else _facts(data, "efficacy_views")
    series_map: dict[str, dict[str, Any]] = {}
    long_table_rows: list[list[Any]] = []
    if view_facts:
        for fact in view_facts:
            arm = _arm_zh(fact.get("arm_role"), fact.get("arm_label") or fact.get("arm_id"))
            label = (
                f"{_name(products, fact.get('product_id'))}/"
                f"{_trial_name(trials, fact.get('trial_id'))}/{arm}"
            )
            bucket = series_map.setdefault(label, {"label_zh": label, "points": []})
            week = fact.get("actual_timepoint")
            value = fact.get("value")
            if week is not None and value is not None:
                bucket["points"].append({"x": float(week), "y": float(value)})
            long_table_rows.append(
                [
                    _name(products, fact.get("product_id")),
                    _trial_name(trials, fact.get("trial_id")),
                    arm,
                    fact.get("endpoint_family_label_zh")
                    or fact.get("original_endpoint")
                    or UNPUBLISHED,
                    display_value(week, unit=str(fact.get("actual_timepoint_unit") or "")),
                    display_value(value, unit=str(fact.get("unit") or "%")),
                    fact.get("analysis_population") or UNPUBLISHED,
                    disclosure_zh(fact.get("disclosure_state")),
                ]
            )
    else:
        for pt in efficacy_points:
            label = f"{pt['product_zh']}/{pt['trial_zh']}/{pt['arm_zh']}"
            bucket = series_map.setdefault(label, {"label_zh": label, "points": []})
            # Parse rough week number when possible.
            week = None
            text = str(pt["timepoint_zh"])
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                week = float(digits)
            if week is not None and pt.get("value") is not None:
                bucket["points"].append({"x": week, "y": float(pt["value"])})
            long_table_rows.append(
                [
                    pt["product_zh"],
                    pt["trial_zh"],
                    pt["arm_zh"],
                    pt["endpoint_zh"],
                    pt["timepoint_zh"],
                    display_value(pt["value"], unit=pt["unit"]),
                    pt["population_zh"],
                    "已公开" if pt.get("value") is not None else UNPUBLISHED,
                ]
            )

    section_break(story, landscape=True)
    bookmark(story, "longitudinal-results", "纵向结果")
    story.append(Paragraph("纵向结果", styles["section"]))
    story.append(
        Paragraph(
            "按产品、试验、终点和时间点展示纵向序列；时间点不足时仍保留已披露点，不编造中间值。",
            styles["caption"],
        )
    )
    story.append(Paragraph("纵向结果折线图", styles["caption"]))
    story.append(
        longitudinal_line_chart(
            list(series_map.values()),
            width=_usable_width(landscape=True),
            height=150,
            title="纵向结果折线图",
        )
    )
    if series_map and all(len(item.get("points") or []) <= 1 for item in series_map.values()):
        story.append(
            Paragraph(
                "当前各序列仅公开一个评估时间点，因此仅绘制离散点，不连接为变化趋势；"
                "同一时间点的圆点横向微调以便辨认，准确时间点与数值见下表。",
                styles["caption"],
            )
        )
    story.append(Spacer(1, 3))
    story.extend(
        continuation_table_blocks(
            title="纵向结果完整数据表",
            headers=["产品", "试验", "组别", "终点", "时间点", "数值", "人群", "披露"],
            rows=long_table_rows,
            styles=styles,
            col_widths=[22 * mm, 22 * mm, 16 * mm, 34 * mm, 18 * mm, 18 * mm, 22 * mm, 18 * mm],
        )
    )

    safety_compact = list(data.get("safety") or [])
    # Prefer indication-locked compact rows. Detailed view fixtures may come
    # from another vertical slice and must not contaminate the report.
    safety_facts = [] if safety_compact else _facts(data, "safety_views")
    heatmap_cells: list[dict[str, Any]] = []
    safety_table_rows: list[list[Any]] = []
    if safety_facts:
        family_zh = {
            "teae": "治疗期间不良事件",
            "sae": "严重不良事件",
            "aesi": "特别关注不良事件",
            "common_ae": "常见不良事件",
        }
        for fact in safety_facts:
            product = _name(products, fact.get("product_id"))
            category = family_zh.get(
                str(fact.get("family")), str(fact.get("family") or UNPUBLISHED)
            )
            heatmap_cells.append(
                {
                    "product_zh": product,
                    "category_zh": category,
                    "value": fact.get("value"),
                }
            )
            safety_table_rows.append(
                [
                    product,
                    _trial_name(trials, fact.get("trial_id")),
                    category,
                    fact.get("source_term") or fact.get("term_id") or UNPUBLISHED,
                    _arm_zh(fact.get("arm_role"), fact.get("arm_label")),
                    fact.get("time_window_zh") or UNPUBLISHED,
                    display_value(fact.get("value"), unit="%"),
                    (
                        f"{fact.get('numerator')}/{fact.get('denominator')}"
                        if fact.get("numerator") is not None and fact.get("denominator") is not None
                        else UNPUBLISHED
                    ),
                    disclosure_zh(fact.get("disclosure_state")),
                ]
            )
    else:
        for row in safety_compact:
            heatmap_cells.append(
                {
                    "product_zh": _name(products, row.get("product_id")),
                    "category_zh": str(row.get("category") or UNPUBLISHED),
                    "value": row.get("value"),
                }
            )
            safety_table_rows.append(
                [
                    _name(products, row.get("product_id")),
                    _trial_name(trials, row.get("trial_id")),
                    row.get("category"),
                    row.get("term"),
                    _arm_zh(row.get("arm")),
                    row.get("time_window") or UNPUBLISHED,
                    display_value(row.get("value"), unit=str(row.get("unit") or "%")),
                    UNPUBLISHED,
                    disclosure_zh(row.get("disclosure_state")),
                ]
            )

    section_break(story, landscape=True)
    bookmark(story, "safety", "安全性")
    story.append(Paragraph("安全性", styles["section"]))
    story.append(Paragraph("含热图与完整表；数值印在单元格并区分披露状态。", styles["caption"]))
    story.append(Paragraph("安全性热图", styles["caption"]))
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for cell in heatmap_cells:
        dedup.setdefault((cell["product_zh"], cell["category_zh"]), cell)
    story.append(
        safety_heatmap_chart(
            list(dedup.values()),
            width=_usable_width(landscape=True),
            height=140,
            title="安全性热图",
        )
    )
    story.append(Spacer(1, 3))
    story.extend(
        continuation_table_blocks(
            title="安全性完整数据表",
            headers=["产品", "试验", "类别", "术语", "组别", "观察窗", "发生率", "例数", "披露"],
            rows=safety_table_rows,
            styles=styles,
            col_widths=[
                20 * mm,
                24 * mm,
                24 * mm,
                22 * mm,
                14 * mm,
                22 * mm,
                16 * mm,
                16 * mm,
                16 * mm,
            ],
            rows_per_page=12,
        )
    )

    matrix_rows_raw: list[dict[str, Any]] = []
    bubble_points: list[dict[str, Any]] = []
    matrix_table: list[list[Any]] = []
    for row in matrix_rows_raw:
        point = row.get("point") or {}
        bubble_points.append(
            {
                "label_zh": _name(products, row.get("product_id")),
                "x": None if point is None else point.get("x_value"),
                "y": None if point is None else point.get("y_value"),
                "size": None if point is None else point.get("size"),
            }
        )
        matrix_table.append(
            [
                _name(products, row.get("product_id")),
                _trial_name(trials, row.get("trial_id")),
                row.get("display_label_zh") or UNPUBLISHED,
                display_value(None if point is None else point.get("x_value"), unit="%"),
                display_value(None if point is None else point.get("y_value"), unit="%"),
                display_value(None if point is None else point.get("size"), unit="例"),
                disclosure_zh(row.get("status")) if row.get("status") != "comparable" else "可比",
            ]
        )
    if not matrix_table:
        # Derive from the same compact efficacy/safety rows used by the pages
        # above, so the matrix cannot silently introduce a third value set.
        for pt in efficacy_points:
            if pt["arm_zh"] != "治疗组":
                continue
            teae = next(
                (
                    cell["value"]
                    for cell in heatmap_cells
                    if cell["product_zh"] == pt["product_zh"]
                    and "治疗期间" in str(cell["category_zh"])
                ),
                None,
            )
            trial_record = trials.get(str(pt.get("trial_id"))) or {}
            treatment_n = trial_record.get("treatment_sample_size")
            bubble_points.append(
                {
                    "label_zh": pt["product_zh"],
                    "x": pt.get("value"),
                    "y": teae,
                    "size": treatment_n,
                }
            )
            matrix_table.append(
                [
                    pt["product_zh"],
                    pt["trial_zh"],
                    f"{pt['endpoint_zh']}与治疗期间不良事件",
                    display_value(pt.get("value"), unit="%"),
                    display_value(teae, unit="%"),
                    display_value(treatment_n, unit="例"),
                    "可比" if pt.get("value") is not None and teae is not None else UNPUBLISHED,
                ]
            )

    section_break(story, landscape=True)
    bookmark(story, "efficacy-safety-matrix", "疗效与安全性矩阵")
    story.append(
        KeepTogether(
            [
                Paragraph("疗效与安全性矩阵", styles["section"]),
                Paragraph(
                    "气泡面积反映治疗组样本量；当前映射旁注：X=疗效观察信号，Y=治疗期间不良事件（倒序）。",
                    styles["caption"],
                ),
                Paragraph("疗效与安全性气泡图", styles["caption"]),
                bubble_matrix_chart(
                    [
                        pt
                        for pt in bubble_points
                        if pt.get("x") is not None and pt.get("y") is not None
                    ],
                    width=_usable_width(landscape=True),
                    height=210,
                    title="疗效与安全性气泡图",
                    mapping_note="气泡面积反映治疗组样本量；不生成综合分数。",
                ),
            ]
        )
    )
    story.append(Spacer(1, 3))
    story.append(Paragraph("疗效与安全性矩阵完整数据表", styles["caption"]))
    story.append(
        styled_table(
            ["产品", "试验", "映射说明", "疗效X", "安全性Y", "计划治疗N", "状态"],
            matrix_table,
            styles,
            [22 * mm, 22 * mm, 48 * mm, 18 * mm, 20 * mm, 16 * mm, 16 * mm],
        )
    )

    # ---- PDF04 baseline ----
    baseline_facts = _facts(data, "baseline_views")
    section_break(story, landscape=True)
    bookmark(story, "baseline-overview", "基线与人群总览")
    story.append(Paragraph("基线与人群总览", styles["section"]))
    story.append(
        Paragraph(
            "样本量口径：试验档案列示计划样本量；本节仅列来源已披露的基线分析人数，"
            "两者不可直接互换。",
            styles["caption"],
        )
    )
    overview_rows = []
    for fact in baseline_facts:
        overview_rows.append(
            [
                _name(products, fact.get("product_id")),
                _trial_name(trials, fact.get("trial_id")),
                _arm_zh(fact.get("arm_role"), fact.get("group_id")),
                _label(fact.get("variable_domain")),
                _label(fact.get("standardized_concept") or fact.get("source_name")),
                display_value(fact.get("value"), unit=str(fact.get("unit") or "")),
                _label(fact.get("statistic_form")),
                disclosure_zh(fact.get("disclosure_state")),
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="基线与人群总览完整表",
            headers=["产品", "试验", "组别", "域", "变量", "数值", "统计形式", "披露"],
            rows=overview_rows,
            styles=styles,
            col_widths=[20 * mm, 22 * mm, 16 * mm, 22 * mm, 28 * mm, 18 * mm, 20 * mm, 16 * mm],
        )
    )

    def _baseline_section(
        page_key: str,
        title_zh: str,
        domain: str,
        concepts: set[str] | None = None,
        *,
        landscape: bool = False,
        skip_break: bool = False,
    ) -> None:
        if not skip_break:
            section_break(story, landscape=landscape)
        bookmark(story, page_key, title_zh)
        story.append(Paragraph(title_zh, styles["section"]))
        rows: list[list[Any]] = []
        for fact in baseline_facts:
            if str(fact.get("variable_domain")) != domain:
                continue
            concept = str(fact.get("standardized_concept") or fact.get("source_name") or "")
            if concepts is not None and concept not in concepts:
                continue
            rows.append(
                [
                    _name(products, fact.get("product_id")),
                    _trial_name(trials, fact.get("trial_id")),
                    _arm_zh(fact.get("arm_role"), fact.get("group_id")),
                    _label(concept),
                    display_value(fact.get("value"), unit=str(fact.get("unit") or "")),
                    _label(fact.get("statistic_form")),
                    fact.get("analysis_population") or UNPUBLISHED,
                    disclosure_zh(fact.get("disclosure_state")),
                ]
            )
        if not rows and domain == "disease_context":
            # Dense disclosure matrix: preserve truthful 未公开 without sparse long-row sprawl.
            arms = sorted(
                {
                    (
                        str(fact.get("product_id")),
                        str(fact.get("trial_id")),
                        _arm_zh(fact.get("arm_role"), fact.get("group_id")),
                    )
                    for fact in baseline_facts
                }
            )
            matrix_rows = [
                [
                    _name(products, product_id),
                    _trial_name(trials, trial_id),
                    arm,
                    *[UNPUBLISHED for _key, _label in _DISEASE_CONTEXT_VARS],
                    UNPUBLISHED,
                ]
                for product_id, trial_id, arm in arms
            ]
            story.append(
                Paragraph(
                    "本锁定快照未公开病程、既往系统治疗、表型与相关合并症数值；"
                    "下表按试验×组别完整保留未公开状态，不作零填充。",
                    styles["caption"],
                )
            )
            story.extend(
                continuation_table_blocks(
                    title=f"{title_zh}完整表",
                    headers=[
                        "产品",
                        "试验",
                        "组别",
                        *[label for _key, label in _DISEASE_CONTEXT_VARS],
                        "披露",
                    ],
                    rows=matrix_rows,
                    styles=styles,
                    col_widths=[
                        22 * mm,
                        24 * mm,
                        16 * mm,
                        22 * mm,
                        28 * mm,
                        18 * mm,
                        28 * mm,
                        16 * mm,
                    ],
                    first_page_rows=2,
                    rows_per_page=16,
                )
            )
            return
        story.extend(
            continuation_table_blocks(
                title=f"{title_zh}完整表",
                headers=["产品", "试验", "组别", "变量", "数值", "统计形式", "人群", "披露"],
                rows=rows,
                styles=styles,
                col_widths=[22 * mm, 24 * mm, 16 * mm, 28 * mm, 20 * mm, 20 * mm, 22 * mm, 16 * mm],
            )
        )

    # Demographics + disease-context(未公开矩阵) + severity share consecutive pages by sequence.
    _baseline_section(
        "baseline-demographics",
        "人口学",
        "demographics",
        {"baseline_sample_size", "age", "sex"},
        landscape=True,
    )
    _baseline_section(
        "baseline-disease-context",
        "疾病语境",
        "disease_context",
        skip_break=True,
    )
    _baseline_section(
        "baseline-severity",
        "基线疾病严重程度",
        "baseline_severity",
        {"baseline_easi", "baseline_hemoglobin"},
        skip_break=True,
    )

    # ---- PDF05 disposition + profiles ----
    disposition_facts = _facts(data, "disposition_views")
    section_break(story, landscape=True)
    bookmark(story, "disposition-overview", "试验完成情况")
    story.append(Paragraph("试验完成情况总览", styles["section"]))
    story.append(
        Paragraph(
            "筛选、随机、治疗、完成、停止、退出、失访及实施字段；未公开数值不作零处理。"
            "本节人数为来源披露的受试者流转口径，不等同于试验档案中的计划样本量。",
            styles["caption"],
        )
    )
    disp_rows = []
    for fact in disposition_facts:
        value_text = display_value(fact.get("value"), unit=str(fact.get("unit") or ""))
        if fact.get("value") is None:
            value_text = UNPUBLISHED
        denom = fact.get("denominator")
        disp_rows.append(
            [
                _name(products, fact.get("product_id")),
                _trial_name(trials, fact.get("trial_id")),
                _arm_zh(fact.get("arm_role"), fact.get("group_id")),
                _label(fact.get("field_family")),
                _label(fact.get("field")),
                value_text,
                display_value(denom),
                _label(fact.get("denominator_role")),
                disclosure_zh(fact.get("disclosure_state")),
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="试验完成情况完整表",
            headers=[
                "产品",
                "试验",
                "组别",
                "观察类别",
                "指标",
                "数值",
                "分母",
                "分母口径",
                "披露",
            ],
            rows=disp_rows,
            styles=styles,
            col_widths=[
                18 * mm,
                25 * mm,
                14 * mm,
                18 * mm,
                25 * mm,
                16 * mm,
                14 * mm,
                20 * mm,
                16 * mm,
            ],
            rows_per_page=18,
            context="含受试者流转、依从性、失访与退出、筛败、补救治疗、禁用药与方案偏离。",
        )
    )

    def _disp_rows_for(key: str, families: set[str]) -> list[list[Any]]:
        rows: list[list[Any]] = []
        for fact in disposition_facts:
            family = str(fact.get("field_family") or "")
            field = str(fact.get("field") or "")
            if family not in families:
                continue
            if key == "loss-exit" and field not in {
                "lost_to_follow_up",
                "treatment_discontinued",
                "study_withdrawal",
                "treatment_discontinuation_reason",
                "study_withdrawal_reason",
            }:
                continue
            if key == "screen-failure" and "screen" not in field:
                continue
            rows.append(
                [
                    _name(products, fact.get("product_id")),
                    _trial_name(trials, fact.get("trial_id")),
                    _arm_zh(fact.get("arm_role"), fact.get("group_id")),
                    _label(field),
                    display_value(fact.get("value"))
                    if fact.get("value") is not None
                    else UNPUBLISHED,
                    _label(fact.get("denominator_role")),
                    disclosure_zh(fact.get("disclosure_state")),
                ]
            )
        return rows or [
            [UNPUBLISHED, UNPUBLISHED, UNPUBLISHED, key, UNPUBLISHED, "分母", UNPUBLISHED]
        ]

    def _emit_disp_section(
        key: str,
        title_zh: str,
        families: set[str],
        *,
        break_before: bool = False,
        landscape: bool = False,
        rows_per_page: int = 16,
    ) -> None:
        if break_before:
            section_break(story, landscape=landscape)
        bookmark(story, key, title_zh)
        section_heading(story, styles, title_zh)
        story.extend(
            continuation_table_blocks(
                title=f"{title_zh}完整表",
                headers=["产品", "试验", "组别", "指标", "数值", "分母口径", "披露"],
                rows=_disp_rows_for(key, families),
                styles=styles,
                col_widths=[24 * mm, 26 * mm, 18 * mm, 34 * mm, 22 * mm, 24 * mm, 20 * mm],
                rows_per_page=rows_per_page,
            )
        )

    # Longer flow alone; short 未公开-heavy sections share pages by clinical sequence.
    _emit_disp_section(
        "participant-flow",
        "受试者流转",
        {"participant_flow"},
        break_before=True,
        landscape=True,
        rows_per_page=16,
    )
    _emit_disp_section(
        "loss-exit",
        "失访与退出",
        {"reason", "participant_flow"},
        break_before=True,
        rows_per_page=14,
    )
    _emit_disp_section(
        "adherence",
        "依从性",
        {"adherence"},
        break_before=True,
        rows_per_page=12,
    )
    _emit_disp_section(
        "screen-failure",
        "筛败与原因",
        {"participant_flow", "reason"},
        break_before=False,
        rows_per_page=12,
    )
    _emit_disp_section(
        "rescue-treatment",
        "补救治疗",
        {"rescue_treatment"},
        break_before=False,
        rows_per_page=12,
    )
    _emit_disp_section(
        "prohibited-medication",
        "禁用药使用",
        {"prohibited_medication"},
        break_before=False,
        rows_per_page=12,
    )
    _emit_disp_section(
        "plan-deviation",
        "方案偏离",
        {"protocol_deviation"},
        break_before=True,
        landscape=True,
        rows_per_page=14,
    )

    section_break(story, landscape=True)
    bookmark(story, "trial-exposure-context", "试验与暴露语境")
    section_heading(
        story,
        styles,
        "试验与暴露语境",
        caption="呈现试验角色、计划组别规模、地域与暴露相关字段；未公开暴露时长如实标记，不推断。",
    )
    exposure_rows = []
    for trial in data.get("trials") or []:
        pid = str(trial.get("product_id"))
        exposure_rows.append(
            [
                _name(products, pid),
                trial.get("name"),
                trial.get("role") or UNPUBLISHED,
                trial.get("phase") or UNPUBLISHED,
                trial.get("region") or UNPUBLISHED,
                trial.get("status") or UNPUBLISHED,
                display_value(trial.get("sample_size"), unit="例"),
                display_value(trial.get("treatment_sample_size"), unit="例"),
                UNPUBLISHED,  # 暴露时长未在本快照公开
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="试验与暴露语境完整表",
            headers=[
                "产品",
                "试验",
                "角色",
                "阶段",
                "地域",
                "状态",
                "总N",
                "治疗N",
                "暴露时长",
            ],
            rows=exposure_rows,
            styles=styles,
            col_widths=[
                20 * mm,
                22 * mm,
                28 * mm,
                14 * mm,
                14 * mm,
                16 * mm,
                14 * mm,
                16 * mm,
                20 * mm,
            ],
        )
    )

    bookmark(story, "subgroups-supporting-evidence", "亚组与支持证据")
    section_heading(
        story,
        styles,
        "亚组与支持证据",
        caption=(
            "早期、延伸、亚组、事后和真实世界结果放在支持层并明确角色，不与核心比较等权。"
            "本锁定快照未公开独立亚组数值时，保留支持层空位与未公开状态。"
        ),
    )
    support_rows = []
    for trial in data.get("trials") or []:
        support_rows.append(
            [
                _name(products, str(trial.get("product_id"))),
                trial.get("name"),
                "核心比较",
                "主要疗效/安全性",
                "已纳入核心章节",
                "已公开"
                if any(
                    row.get("trial_id") == trial.get("id") for row in (data.get("efficacy") or [])
                )
                else UNPUBLISHED,
            ]
        )
        support_rows.append(
            [
                _name(products, str(trial.get("product_id"))),
                trial.get("name"),
                "支持层",
                "亚组/延伸/真实世界",
                "不与核心等权",
                UNPUBLISHED,
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="亚组与支持证据完整表",
            headers=["产品", "试验", "证据角色", "内容", "解释约束", "披露"],
            rows=support_rows,
            styles=styles,
            col_widths=[24 * mm, 26 * mm, 22 * mm, 40 * mm, 36 * mm, 20 * mm],
        )
    )

    section_break(story, landscape=True)
    bookmark(story, "product-trial-profiles", "产品与试验档案")
    story.append(Paragraph("产品与试验档案", styles["section"]))
    profile_rows = []
    for trial in data.get("trials") or []:
        pid = str(trial.get("product_id"))
        profile_rows.append(
            [
                _name(products, pid),
                trial.get("name"),
                trial.get("display_id") or UNPUBLISHED,
                trial.get("phase"),
                trial.get("region"),
                trial.get("status"),
                trial.get("role") or UNPUBLISHED,
                display_value(trial.get("sample_size"), unit="例"),
                display_value(trial.get("treatment_sample_size"), unit="例"),
            ]
        )
    story.extend(
        continuation_table_blocks(
            title="产品与试验档案完整表",
            headers=[
                "产品",
                "试验",
                "登记号",
                "阶段",
                "地域",
                "状态",
                "角色",
                "总N",
                "治疗N",
            ],
            rows=profile_rows,
            styles=styles,
            col_widths=[
                24 * mm,
                24 * mm,
                28 * mm,
                14 * mm,
                14 * mm,
                16 * mm,
                28 * mm,
                14 * mm,
                16 * mm,
            ],
        )
    )
    # Attach compact endpoint/safety coverage for archive completeness.
    archive_cov = []
    for pt in efficacy_points:
        archive_cov.append(
            [
                pt["product_zh"],
                pt["trial_zh"],
                "疗效",
                pt["arm_zh"],
                pt["endpoint_zh"],
                pt["timepoint_zh"],
                display_value(pt["value"], unit=pt["unit"]),
            ]
        )
    for row in safety_table_rows[:20]:
        archive_cov.append([row[0], row[1], "安全性", row[4], row[3], row[5], row[6]])
    story.extend(
        continuation_table_blocks(
            title="逐试验终点与安全性覆盖",
            headers=["产品", "试验", "域", "组别", "项目", "时间/窗", "数值"],
            rows=archive_cov,
            styles=styles,
            col_widths=[22 * mm, 22 * mm, 16 * mm, 18 * mm, 44 * mm, 26 * mm, 22 * mm],
        )
    )

    bookmark(story, "evidence-limitations", "研究依据与局限")
    section_heading(
        story,
        styles,
        "研究依据与局限",
        caption="呈现影响比较解释的来源成熟度、可比性差异和局限，完整检索过程留在项目记录。",
    )
    source_rows = [
        [
            item.get("source") or UNPUBLISHED,
            item.get("scope") or UNPUBLISHED,
            item.get("maturity") or UNPUBLISHED,
            item.get("limitation") or UNPUBLISHED,
        ]
        for item in data.get("sources") or []
    ]
    if not source_rows:
        source_rows = [[UNPUBLISHED, UNPUBLISHED, UNPUBLISHED, UNPUBLISHED]]
    story.extend(
        continuation_table_blocks(
            title="研究依据与局限完整表",
            headers=["来源", "范围", "成熟度", "局限"],
            rows=source_rows,
            styles=styles,
            col_widths=[36 * mm, 42 * mm, 36 * mm, 54 * mm],
        )
    )

    doc.build(story)
    if not output.is_file() or output.stat().st_size < 2000:
        raise RuntimeError(f"B PDF 生成失败或过小：{output}")
    return output


__all__ = ["build_report_b_native_pdf"]
