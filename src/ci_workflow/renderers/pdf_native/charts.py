"""Shared native ReportLab charts for Task 8.2 A/B/C PDF projections (PDF09)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.graphics.charts.barcharts import (  # type: ignore[import-untyped]
    HorizontalBarChart,
    VerticalBarChart,
)
from reportlab.graphics.charts.legends import Legend  # type: ignore[import-untyped]
from reportlab.graphics.charts.lineplots import LinePlot  # type: ignore[import-untyped]
from reportlab.graphics.shapes import (  # type: ignore[import-untyped]
    Circle,
    Drawing,
    Line,
    Rect,
    String,
)
from reportlab.graphics.widgets.markers import makeMarker  # type: ignore[import-untyped]

from ci_workflow.renderers.pdf_native import tokens
from ci_workflow.renderers.pdf_native.fonts import FONT_FAMILY, FONT_FAMILY_BOLD

UNPUBLISHED = "未公开"


def efficacy_grouped_bar_chart(
    points: Sequence[dict[str, Any]],
    *,
    width: float,
    height: float,
    title: str,
) -> Drawing:
    products: list[str] = []
    by_product: dict[str, dict[str, float]] = {}
    for point in points:
        product = str(point["product_zh"])
        arm = str(point["arm_zh"])
        if product not in products:
            products.append(product)
        if point.get("value") is None:
            continue
        by_product.setdefault(product, {})[arm] = float(point["value"])
    treatment = [by_product.get(product, {}).get("治疗组", 0.0) for product in products]
    control = [
        by_product.get(product, {}).get("对照组", by_product.get(product, {}).get("安慰剂组", 0.0))
        for product in products
    ]
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    chart = VerticalBarChart()
    chart.x = 55
    chart.y = 36
    chart.height = height - 78
    chart.width = width - 95
    chart.data = [treatment, control]
    chart.categoryAxis.categoryNames = products or ["—"]
    chart.categoryAxis.labels.fontName = FONT_FAMILY
    chart.categoryAxis.labels.fontSize = 8.5
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontName = FONT_FAMILY
    chart.valueAxis.labels.fontSize = 8.5
    chart.bars[0].fillColor = tokens.TREATMENT_FILL
    chart.bars[1].fillColor = tokens.PLACEBO_FILL
    chart.bars.strokeColor = None
    chart.barWidth = 10
    chart.groupSpacing = 14
    chart.barLabelFormat = "%0.1f"
    chart.barLabels.fontName = FONT_FAMILY
    chart.barLabels.fontSize = 8.5
    drawing.add(chart)
    drawing.add(
        String(40, height - 16, title, fontName=FONT_FAMILY_BOLD, fontSize=10, fillColor=tokens.INK)
    )
    legend = Legend()
    legend.x = width - 140
    legend.y = height - 14
    legend.fontName = FONT_FAMILY
    legend.fontSize = 8.5
    legend.colorNamePairs = [
        (tokens.TREATMENT_FILL, "治疗组"),
        (tokens.PLACEBO_FILL, "对照组"),
    ]
    drawing.add(legend)
    return drawing


def efficacy_forest_chart(
    rows: Sequence[dict[str, Any]],
    *,
    width: float,
    height: float,
    title: str,
) -> Drawing:
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    drawing.add(
        String(24, height - 14, title, fontName=FONT_FAMILY_BOLD, fontSize=10, fillColor=tokens.INK)
    )
    chart = HorizontalBarChart()
    labels = [str(row["label_zh"]) for row in rows] or ["—"]
    values = [float(row.get("difference") or 0.0) for row in rows] or [0.0]
    chart.x = 150
    # Keep value-axis tick labels clear of the clinical interpretation note.
    chart.y = 38
    chart.height = max(18, height - 68)
    chart.width = width - 190
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = FONT_FAMILY
    chart.categoryAxis.labels.fontSize = 8.5
    chart.valueAxis.labels.fontName = FONT_FAMILY
    chart.valueAxis.labels.fontSize = 8.5
    lo = min(0.0, min(values) - 5)
    hi = max(0.0, max(values) + 5)
    chart.valueAxis.valueMin = lo
    chart.valueAxis.valueMax = hi
    chart.bars[0].fillColor = tokens.KZ_ORANGE_MID
    chart.bars.strokeColor = None
    chart.barLabelFormat = "%0.1f"
    chart.barLabels.fontName = FONT_FAMILY
    chart.barLabels.fontSize = 8.5
    drawing.add(chart)
    zero_x = chart.x + (0 - lo) / (hi - lo) * chart.width if hi != lo else chart.x
    drawing.add(
        Line(
            zero_x,
            chart.y,
            zero_x,
            chart.y + chart.height,
            strokeColor=tokens.RULE,
            strokeWidth=0.8,
        )
    )
    drawing.add(
        String(
            24,
            6,
            "组间差值（百分点）；正值表示治疗组观察信号更强，不进行跨试验合并。",
            fontName=FONT_FAMILY,
            fontSize=8.5,
            fillColor=tokens.INK_MUTED,
        )
    )
    return drawing


def longitudinal_line_chart(
    series: Sequence[dict[str, Any]],
    *,
    width: float,
    height: float,
    title: str,
) -> Drawing:
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    plot = LinePlot()
    plot.x = 50
    plot.y = 30
    plot.height = height - 70
    plot.width = width - 90
    data = []
    legend_labels: list[str] = []
    colors = [tokens.TREATMENT_FILL, tokens.PLACEBO_FILL, tokens.KZ_ORANGE_MID, tokens.INK_MUTED]
    for index, item in enumerate(series):
        points = [
            (float(pt["x"]), float(pt["y"]))
            for pt in item.get("points") or []
            if pt.get("y") is not None
        ]
        if not points:
            points = [(0.0, 0.0)]
        data.append(points)
        raw_label = str(item.get("label_zh") or f"序列{index + 1}")
        label_parts = [part for part in raw_label.split("/") if part]
        # Trial names make the legend wider than the chart. Product + arm keeps
        # the audience-facing distinction while the complete trial identity
        # remains immediately below in the data table.
        legend_labels.append(
            "·".join((label_parts[0], label_parts[-1])) if len(label_parts) >= 2 else raw_label
        )
        plot.lines[index].strokeColor = colors[index % len(colors)]
        plot.lines[index].symbol = makeMarker("FilledCircle")
    single_timepoint_only = bool(data) and all(len(points) <= 1 for points in data)
    if single_timepoint_only and len(data) > 1:
        # All observations remain anchored to the same labelled week. A small,
        # symmetric visual offset prevents close values from becoming one dot;
        # the exact timepoint stays authoritative in the table below.
        center = (len(data) - 1) / 2.0
        for index, points in enumerate(data):
            if points:
                week, value = points[0]
                points[0] = (week + (index - center) * 0.16, value)
    display_title = "单一时间点结果（不连线）" if single_timepoint_only else title
    drawing.add(
        String(
            24,
            height - 14,
            display_title,
            fontName=FONT_FAMILY_BOLD,
            fontSize=10,
            fillColor=tokens.INK,
        )
    )
    plot.data = data or [[(0.0, 0.0)]]
    plot.xValueAxis.labels.fontName = FONT_FAMILY
    plot.xValueAxis.labels.fontSize = 8.5
    plot.yValueAxis.labels.fontName = FONT_FAMILY
    plot.yValueAxis.labels.fontSize = 8.5
    plot.yValueAxis.valueMin = 0
    plot.yValueAxis.valueMax = 100
    plot.xValueAxis.valueMin = 0
    plot.xValueAxis.valueMax = max(
        20.0,
        max((point[0] for points in data for point in points), default=16.0) + 2.0,
    )
    drawing.add(plot)
    legend = Legend()
    legend.x = width - 300
    legend.y = height - 12
    legend.fontName = FONT_FAMILY
    legend.fontSize = 8
    legend.alignment = "left"
    legend.columnMaximum = 2
    legend.deltax = 145
    legend.dxTextSpace = 5
    legend.colorNamePairs = [
        (colors[index % len(colors)], label[:16]) for index, label in enumerate(legend_labels)
    ] or [(tokens.TREATMENT_FILL, "无纵向点")]
    drawing.add(legend)
    return drawing


def safety_heatmap_chart(
    cells: Sequence[dict[str, Any]],
    *,
    width: float,
    height: float,
    title: str,
) -> Drawing:
    products: list[str] = []
    categories: list[str] = []
    lookup: dict[tuple[str, str], Any] = {}
    for cell in cells:
        product = str(cell["product_zh"])
        category = str(cell["category_zh"])
        if product not in products:
            products.append(product)
        if category not in categories:
            categories.append(category)
        lookup[(product, category)] = cell.get("value")

    # Short stable abbreviations keep Chinese headers from colliding in narrow cells.
    abbrev_map = {
        "治疗期间不良事件": "TEAE",
        "严重不良事件": "SAE",
        "特别关注不良事件": "AESI",
        "常见不良事件": "常见AE",
    }
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    drawing.add(
        String(16, height - 14, title, fontName=FONT_FAMILY_BOLD, fontSize=10, fillColor=tokens.INK)
    )
    left = 78
    top = height - 42
    usable_w = width - left - 12
    usable_h = height - 70
    col_w = usable_w / max(len(categories), 1)
    row_h = usable_h / max(len(products), 1)
    category_max = {
        category: max(
            (
                float(value)
                for (product_key, category_key), value in lookup.items()
                if category_key == category and value is not None
            ),
            default=0.0,
        )
        for category in categories
    }
    for col, category in enumerate(categories):
        label = abbrev_map.get(category, category[:6])
        drawing.add(
            String(
                left + col * col_w + max((col_w - 3 - 8.5 * len(label)) / 2.0, 2),
                top + 8,
                label,
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK_MUTED,
            )
        )
    for row, product in enumerate(products):
        y = top - (row + 1) * row_h
        product_label = product if len(product) <= 6 else product[:5] + "…"
        drawing.add(
            String(
                6,
                y + row_h / 2 - 3,
                product_label,
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK,
            )
        )
        for col, category in enumerate(categories):
            x = left + col * col_w
            value = lookup.get((product, category))
            if value is None:
                fill = tokens.RULE
                label = "—"
            else:
                denominator = category_max.get(category) or 1.0
                intensity = max(0.0, min(float(value) / denominator, 1.0))
                fill = tokens.tint(tokens.KZ_RISK, 1.0 - intensity * 0.75)
                label = f"{float(value):.1f}"
            drawing.add(
                Rect(
                    x,
                    y,
                    col_w - 4,
                    row_h - 4,
                    fillColor=fill,
                    strokeColor=tokens.TABLE_GRID,
                    strokeWidth=0.4,
                )
            )
            drawing.add(
                String(
                    x + max((col_w - 4 - 8.5 * len(label)) / 2.0, 2),
                    y + row_h / 2 - 4,
                    label,
                    fontName=FONT_FAMILY,
                    fontSize=8.5,
                    fillColor=tokens.INK,
                )
            )
    legend = "颜色越深表示同一指标在当前竞品中相对更高；数值为准。"
    if categories:
        legend += " " + "；".join(
            f"{abbrev_map.get(cat, cat[:6])}={cat}" for cat in categories
        )
    drawing.add(
        String(
            16,
            10,
            legend[:78],
            fontName=FONT_FAMILY,
            fontSize=8.5,
            fillColor=tokens.INK_MUTED,
        )
    )
    return drawing


def _fmt_tick(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return f"{value:.1f}"


def bubble_matrix_chart(
    points: Sequence[dict[str, Any]],
    *,
    width: float,
    height: float,
    title: str,
    mapping_note: str,
    axis_note: str = "向上 = 发生率更低；向右 = 疗效观察信号更强",
    legend_chars: int = 10,
    coordinate_axes: bool = True,
) -> Drawing:
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))
    drawing.add(
        String(16, height - 14, title, fontName=FONT_FAMILY_BOLD, fontSize=10, fillColor=tokens.INK)
    )
    # Leave a right legend rail and bottom note band so labels never collide with axes.
    legend_w = 118
    plot_x, plot_y = (58, 50) if coordinate_axes else (48, 42)
    plot_w = max(width - plot_x - legend_w - 12, 120)
    plot_h = height - (96 if coordinate_axes else 86)
    drawing.add(
        Rect(
            plot_x, plot_y, plot_w, plot_h, fillColor=None, strokeColor=tokens.RULE, strokeWidth=0.8
        )
    )
    drawing.add(
        String(
            plot_x,
            14,
            mapping_note[:72],
            fontName=FONT_FAMILY,
            fontSize=8.5,
            fillColor=tokens.INK_MUTED,
        )
    )
    drawing.add(
        String(
            plot_x,
            plot_y + plot_h + 6,
            axis_note,
            fontName=FONT_FAMILY,
            fontSize=8.5,
            fillColor=tokens.INK_MUTED,
        )
    )

    plottable = [pt for pt in points if pt.get("x") is not None and pt.get("y") is not None]
    sizes = [max(float(pt.get("size") or 1.0), 1.0) for pt in plottable] or [1.0]
    max_size = max(sizes)
    xs = [float(pt["x"]) for pt in plottable] or [0.0, 100.0]
    ys = [float(pt["y"]) for pt in plottable] or [0.0, 100.0]
    x_min, x_max = min(xs) - 8, max(xs) + 8
    y_min, y_max = max(min(ys) - 8, 0.0), min(max(ys) + 8, 100.0)
    if x_max <= x_min:
        x_min, x_max = 0.0, 100.0
    if y_max <= y_min:
        y_min, y_max = 0.0, 100.0

    if coordinate_axes:
        for fraction in (0.0, 0.5, 1.0):
            tx = plot_x + fraction * plot_w
            ty = plot_y + fraction * plot_h
            drawing.add(
                Line(tx, plot_y, tx, plot_y + plot_h, strokeColor=tokens.RULE, strokeWidth=0.35)
            )
            drawing.add(
                Line(plot_x, ty, plot_x + plot_w, ty, strokeColor=tokens.RULE, strokeWidth=0.35)
            )
            x_value = x_min + fraction * (x_max - x_min)
            drawing.add(
                Line(tx, plot_y - 1, tx, plot_y - 5, strokeColor=tokens.INK, strokeWidth=0.7)
            )
            drawing.add(
                String(
                    tx - 8,
                    plot_y - 16,
                    _fmt_tick(x_value),
                    fontName=FONT_FAMILY,
                    fontSize=7.5,
                    fillColor=tokens.INK,
                )
            )
            y_value = y_max - fraction * (y_max - y_min)
            drawing.add(
                Line(plot_x - 1, ty, plot_x - 5, ty, strokeColor=tokens.INK, strokeWidth=0.7)
            )
            drawing.add(
                String(
                    8,
                    ty - 3,
                    _fmt_tick(y_value),
                    fontName=FONT_FAMILY,
                    fontSize=7.5,
                    fillColor=tokens.INK,
                )
            )
        drawing.add(
            Line(
                plot_x,
                plot_y,
                plot_x + plot_w + 6,
                plot_y,
                strokeColor=tokens.INK,
                strokeWidth=0.8,
            )
        )
        drawing.add(
            Line(
                plot_x + plot_w + 1,
                plot_y - 3,
                plot_x + plot_w + 6,
                plot_y,
                strokeColor=tokens.INK,
                strokeWidth=0.8,
            )
        )
        drawing.add(
            Line(
                plot_x + plot_w + 1,
                plot_y + 3,
                plot_x + plot_w + 6,
                plot_y,
                strokeColor=tokens.INK,
                strokeWidth=0.8,
            )
        )
        drawing.add(
            Line(
                plot_x,
                plot_y,
                plot_x,
                plot_y + plot_h + 6,
                strokeColor=tokens.INK,
                strokeWidth=0.8,
            )
        )
        drawing.add(
            Line(
                plot_x - 3,
                plot_y + plot_h + 1,
                plot_x,
                plot_y + plot_h + 6,
                strokeColor=tokens.INK,
                strokeWidth=0.8,
            )
        )
        drawing.add(
            Line(
                plot_x + 3,
                plot_y + plot_h + 1,
                plot_x,
                plot_y + plot_h + 6,
                strokeColor=tokens.INK,
                strokeWidth=0.8,
            )
        )
        drawing.add(
            String(
                plot_x + plot_w - 52,
                plot_y - 26,
                "疗效观察 →",
                fontName=FONT_FAMILY,
                fontSize=7.5,
                fillColor=tokens.INK_MUTED,
            )
        )

    legend_y = height - 34
    drawing.add(
        String(
            plot_x + plot_w + 10,
            legend_y,
            "图例",
            fontName=FONT_FAMILY_BOLD,
            fontSize=8.5,
            fillColor=tokens.INK,
        )
    )
    legend_y -= 14
    for index, pt in enumerate(plottable):
        radius = 6 + 12 * math.sqrt(float(pt.get("size") or 1.0) / max_size)
        x = plot_x + (float(pt["x"]) - x_min) / (x_max - x_min) * plot_w
        y = plot_y + (1.0 - (float(pt["y"]) - y_min) / (y_max - y_min)) * plot_h
        x = max(plot_x + radius + 2, min(x, plot_x + plot_w - radius - 2))
        y = max(plot_y + radius + 2, min(y, plot_y + plot_h - radius - 2))
        drawing.add(
            Circle(
                x,
                y,
                radius,
                fillColor=tokens.TREATMENT_FILL,
                strokeColor=tokens.INK,
                strokeWidth=0.5,
            )
        )
        marker = chr(ord("A") + index)
        drawing.add(
            String(
                x - 2.5,
                y - 3,
                marker,
                fontName=FONT_FAMILY_BOLD,
                fontSize=8.5,
                fillColor=tokens.INK,
            )
        )
        label = str(pt.get("label_zh") or f"点{index + 1}")
        drawing.add(
            String(
                plot_x + plot_w + 10,
                legend_y,
                f"{marker} {label[:legend_chars]}",
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK,
            )
        )
        legend_y -= 12
    if not plottable:
        drawing.add(
            String(
                plot_x + 12,
                plot_y + plot_h / 2,
                "无可绘制坐标（缺失记为未公开，不按零绘制）",
                fontName=FONT_FAMILY,
                fontSize=8.5,
                fillColor=tokens.INK_MUTED,
            )
        )
    return drawing


__all__ = [
    "bubble_matrix_chart",
    "efficacy_forest_chart",
    "efficacy_grouped_bar_chart",
    "longitudinal_line_chart",
    "safety_heatmap_chart",
]
