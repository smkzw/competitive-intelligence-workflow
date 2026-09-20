"""ReportLab flowables for Task 8.1 native PDF vertical slice."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.graphics.charts.barcharts import VerticalBarChart  # type: ignore[import-untyped]
from reportlab.graphics.charts.legends import Legend  # type: ignore[import-untyped]
from reportlab.graphics.shapes import Drawing, Line, Rect, String  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ci_workflow.renderers.pdf_native import tokens
from ci_workflow.renderers.pdf_native.fonts import FONT_FAMILY, FONT_FAMILY_BOLD

_LOGO_PNG = Path(__file__).resolve().parent / "assets" / "cms-logo.png"


class BookmarkFlowable(Flowable):  # type: ignore[misc]  # ReportLab 5.0.0 has no installed stubs
    """Zero-height outline/bookmark anchor."""

    def __init__(self, key: str, title: str, level: int = 0) -> None:
        super().__init__()
        self.key = key
        self.title = title
        self.level = level
        self.width = 0
        self.height = 0

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:  # noqa: N803
        return (0, 0)

    def draw(self) -> None:
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, level=self.level, closed=0)


class AccentRule(Flowable):  # type: ignore[misc]  # ReportLab 5.0.0 has no installed stubs
    """Thin Kangzhe orange identification line."""

    def __init__(self, width: float | None = None, thickness: float = 2.0) -> None:
        super().__init__()
        self._width = width
        self.thickness = thickness
        self.height = thickness + 2

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:  # noqa: N803
        self.width = self._width or availWidth
        return (self.width, self.height)

    def draw(self) -> None:
        self.canv.setStrokeColor(tokens.KZ_ORANGE)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 1, self.width, 1)


def make_styles() -> dict[str, ParagraphStyle]:
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName=FONT_FAMILY_BOLD,
            fontSize=tokens.TITLE_PT,
            leading=tokens.TITLE_PT + 6,
            textColor=tokens.INK,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName=FONT_FAMILY,
            fontSize=11,
            leading=16,
            textColor=tokens.INK_MUTED,
            spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "meta",
            fontName=FONT_FAMILY,
            fontSize=tokens.CAPTION_PT,
            leading=13,
            textColor=tokens.INK_MUTED,
            spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "section",
            fontName=FONT_FAMILY_BOLD,
            fontSize=tokens.SECTION_PT,
            leading=tokens.SECTION_PT + 4,
            textColor=tokens.INK,
            spaceBefore=2,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            fontName=FONT_FAMILY,
            fontSize=tokens.BODY_PT,
            leading=tokens.BODY_PT + 4,
            textColor=tokens.INK,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName=FONT_FAMILY,
            fontSize=tokens.BODY_PT,
            leading=tokens.BODY_PT + 5,
            textColor=tokens.INK,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=3,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName=FONT_FAMILY_BOLD,
            fontSize=tokens.TABLE_PT,
            leading=tokens.TABLE_PT + 2,
            textColor=tokens.INK,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName=FONT_FAMILY,
            fontSize=tokens.TABLE_PT,
            leading=tokens.TABLE_PT + 2,
            textColor=tokens.INK,
        ),
        "context": ParagraphStyle(
            "context",
            fontName=FONT_FAMILY,
            fontSize=tokens.CAPTION_PT,
            leading=12,
            textColor=tokens.INK_MUTED,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName=FONT_FAMILY,
            fontSize=tokens.CAPTION_PT,
            leading=12,
            textColor=tokens.INK_MUTED,
            spaceBefore=2,
            spaceAfter=4,
        ),
    }


def logo_image(max_width: float = 55 * mm) -> Flowable:
    """Embed the official Kangzhe logo (rasterized from assets/brand/cms-logo.svg)."""
    if not _LOGO_PNG.is_file():
        raise FileNotFoundError(f"缺少正式 Logo 位图：{_LOGO_PNG}")
    # Official viewBox 121x25 → keep aspect, no stretch.
    height = max_width * (25.0 / 121.0)
    return Image(str(_LOGO_PNG), width=max_width, height=height, kind="proportional")


def build_efficacy_chart(points: Sequence[dict[str, Any]], width: float, height: float) -> Drawing:
    """Native ReportLab vector grouped bar chart: treatment vs placebo by product."""
    products: list[str] = []
    treatment: list[float] = []
    placebo: list[float] = []
    by_product: dict[str, dict[str, float]] = {}
    for point in points:
        product = str(point["product_zh"])
        group = str(point["group_zh"])
        value = float(point["value_pct"])
        bucket = by_product.setdefault(product, {})
        bucket[group] = value
        if product not in products:
            products.append(product)
    for product in products:
        treatment.append(by_product[product].get("治疗组", 0.0))
        placebo.append(by_product[product].get("安慰剂组", 0.0))

    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=tokens.PAGE_BG, strokeColor=None))

    chart = VerticalBarChart()
    chart.x = 72
    chart.y = 42
    chart.height = height - 88
    chart.width = width - 112
    chart.data = [treatment, placebo]
    chart.categoryAxis.categoryNames = products
    chart.categoryAxis.labels.fontName = FONT_FAMILY
    chart.categoryAxis.labels.fontSize = 8.5
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.categoryAxis.labels.dy = -8
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontName = FONT_FAMILY
    chart.valueAxis.labels.fontSize = 8.5
    chart.valueAxis.labels.fillColor = tokens.INK_MUTED
    chart.valueAxis.labels.dx = -5
    chart.categoryAxis.strokeColor = tokens.RULE
    chart.valueAxis.strokeColor = tokens.RULE
    chart.bars[0].fillColor = tokens.TREATMENT_FILL
    chart.bars[1].fillColor = tokens.PLACEBO_FILL
    chart.barWidth = 12
    chart.groupSpacing = 18
    chart.barSpacing = 2
    chart.bars.strokeColor = None
    chart.barLabelFormat = "%0.1f"
    chart.barLabels.fontName = FONT_FAMILY
    chart.barLabels.fontSize = 8.5
    chart.barLabels.fillColor = tokens.INK
    chart.barLabels.nudge = 5
    drawing.add(chart)

    drawing.add(
        String(
            55,
            height - 18,
            "第16周 EASI-75 应答率（%）· 治疗组与安慰剂组同屏对照",
            fontName=FONT_FAMILY_BOLD,
            fontSize=10,
            fillColor=tokens.INK,
        )
    )

    legend = Legend()
    legend.alignment = "right"
    legend.x = width - 152
    legend.y = height - 16
    legend.fontName = FONT_FAMILY
    legend.fontSize = 8.5
    legend.colorNamePairs = [
        (tokens.TREATMENT_FILL, "治疗组"),
        (tokens.PLACEBO_FILL, "安慰剂组"),
    ]
    legend.dx = 8
    legend.dy = 8
    legend.dxTextSpace = 6
    legend.deltay = 12
    drawing.add(legend)

    # Explicit vector emphasis mark (ensures path operators even if chart style changes).
    drawing.add(Line(72, 34, width - 20, 34, strokeColor=tokens.KZ_ORANGE, strokeWidth=1.2))
    return drawing


def efficacy_snapshot_table(
    points: Sequence[dict[str, Any]], styles: dict[str, ParagraphStyle]
) -> Table:
    """Compact cover-page summary using the same locked efficacy points."""
    by_product: dict[str, dict[str, dict[str, Any]]] = {}
    for point in points:
        by_product.setdefault(str(point["product_zh"]), {})[str(point["group_zh"])] = dict(point)

    rows: list[list[Any]] = [
        [
            _p("产品", styles["table_header"]),
            _p("治疗组", styles["table_header"]),
            _p("安慰剂组", styles["table_header"]),
            _p("组间差值", styles["table_header"]),
        ]
    ]
    for product, values in by_product.items():
        treatment = values.get("治疗组")
        placebo = values.get("安慰剂组")
        treatment_value = float(treatment["value_pct"]) if treatment else None
        placebo_value = float(placebo["value_pct"]) if placebo else None
        difference = (
            treatment_value - placebo_value
            if treatment_value is not None and placebo_value is not None
            else None
        )

        def value_and_count(point: dict[str, Any] | None) -> str:
            if point is None:
                return "—"
            return (
                f"{float(point['value_pct']):.1f}%（{point['numerator']}/{point['denominator']}）"
            )

        rows.append(
            [
                _p(product, styles["table_cell"]),
                _p(value_and_count(treatment), styles["table_cell"]),
                _p(value_and_count(placebo), styles["table_cell"]),
                _p(
                    "—" if difference is None else f"{difference:+.1f} 个百分点",
                    styles["table_cell"],
                ),
            ]
        )
    table = Table(rows, colWidths=[35 * mm, 37 * mm, 37 * mm, 38 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), tokens.KZ_MEDICAL_TINT),
                ("GRID", (0, 0), (-1, -1), 0.4, tokens.TABLE_GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 1.0, tokens.KZ_ORANGE),
            ]
        )
    )
    return table


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def efficacy_table(points: Sequence[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    header = [
        _p("产品", styles["table_header"]),
        _p("试验", styles["table_header"]),
        _p("治疗组别", styles["table_header"]),
        _p("终点", styles["table_header"]),
        _p("时间点", styles["table_header"]),
        _p("应答率", styles["table_header"]),
        _p("例数", styles["table_header"]),
        _p("分析人群", styles["table_header"]),
    ]
    rows: list[list[Any]] = [header]
    for point in points:
        rows.append(
            [
                _p(str(point["product_zh"]), styles["table_cell"]),
                _p(str(point["trial_zh"]), styles["table_cell"]),
                _p(str(point["group_zh"]), styles["table_cell"]),
                _p(str(point["endpoint_zh"]), styles["table_cell"]),
                _p(str(point["timepoint_zh"]), styles["table_cell"]),
                _p(f"{float(point['value_pct']):.1f}{point['unit_zh']}", styles["table_cell"]),
                _p(f"{point['numerator']}/{point['denominator']}", styles["table_cell"]),
                _p(str(point["population_zh"]), styles["table_cell"]),
            ]
        )
    table = Table(
        rows,
        colWidths=[28 * mm, 24 * mm, 18 * mm, 28 * mm, 16 * mm, 16 * mm, 18 * mm, 24 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), tokens.KZ_MEDICAL_TINT),
                ("TEXTCOLOR", (0, 0), (-1, -1), tokens.INK),
                ("FONTNAME", (0, 0), (-1, -1), FONT_FAMILY),
                ("FONTSIZE", (0, 0), (-1, -1), tokens.TABLE_PT),
                ("ALIGN", (5, 1), (6, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, tokens.TABLE_GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, 0), 1.0, tokens.KZ_ORANGE),
            ]
        )
    )
    return table


def safety_continuation_blocks(
    points: Sequence[dict[str, Any]],
    styles: dict[str, ParagraphStyle],
    *,
    rows_per_page: int = 12,
) -> list[Flowable]:
    """Portrait long table split across pages with repeated clinical context and 续表."""
    if rows_per_page < 1:
        raise ValueError("rows_per_page must be >= 1")

    flowables: list[Flowable] = []
    chunks = [
        list(points[index : index + rows_per_page])
        for index in range(0, len(points), rows_per_page)
    ]
    if not chunks:
        return flowables

    for page_index, chunk in enumerate(chunks):
        if page_index > 0:
            flowables.append(PageBreak())

        trial = str(chunk[0]["trial_zh"])
        group = str(chunk[0]["group_zh"])
        window = str(chunk[0]["time_window_zh"])
        product = str(chunk[0]["product_zh"])
        population = str(chunk[0]["population_zh"])
        if page_index == 0:
            context = f"安全性明细 · {product} · 试验 {trial} · {group} · {window} · {population}"
        else:
            context = (
                f"续表 · 安全性明细 · {product} · 试验 {trial} · {group} · {window} · {population}"
            )
        header_line = KeepTogether(
            [
                Paragraph(context, styles["context"]),
                AccentRule(),
                Spacer(1, 2 * mm),
            ]
        )
        flowables.append(header_line)

        table_header = [
            _p("不良事件", styles["table_header"]),
            _p("发生率", styles["table_header"]),
            _p("例数", styles["table_header"]),
        ]
        data: list[list[Any]] = [table_header]
        for point in chunk:
            data.append(
                [
                    _p(str(point["term_zh"]), styles["table_cell"]),
                    _p(f"{float(point['value_pct']):.1f}{point['unit_zh']}", styles["table_cell"]),
                    _p(f"{point['numerator']}/{point['denominator']}", styles["table_cell"]),
                ]
            )
        table = Table(
            data,
            colWidths=[86 * mm, 34 * mm, 34 * mm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), tokens.KZ_MEDICAL_TINT),
                    ("GRID", (0, 0), (-1, -1), 0.4, tokens.TABLE_GRID),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 1), (2, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, 0), 1.0, tokens.KZ_TABLE_HEADER),
                ]
            )
        )
        flowables.append(table)
    return flowables
