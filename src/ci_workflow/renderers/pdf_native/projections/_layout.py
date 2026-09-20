"""Shared native-PDF layout helpers for Task 8.2 A/B/C projections.

PDF09 shared surfaces live in ``charts`` / ``tables`` / ``bookmarks`` /
``coverage``. This module keeps the document shell and a stable import facade
used by A/B/C projections.
"""

from __future__ import annotations

import xml.sax.saxutils
from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

from ci_workflow.renderers.pdf_native import tokens
from ci_workflow.renderers.pdf_native.bookmarks import bookmark
from ci_workflow.renderers.pdf_native.charts import (
    bubble_matrix_chart,
    efficacy_forest_chart,
    efficacy_grouped_bar_chart,
    longitudinal_line_chart,
    safety_heatmap_chart,
)
from ci_workflow.renderers.pdf_native.flowables import AccentRule, logo_image, make_styles
from ci_workflow.renderers.pdf_native.fonts import register_cjk_fonts
from ci_workflow.renderers.pdf_native.tables import continuation_table_blocks, esc, p, styled_table

UNPUBLISHED = "未公开"


def display_value(value: Any, *, unit: str | None = None, missing: str = UNPUBLISHED) -> str:
    if value is None or value == "":
        return missing
    text = str(value)
    if unit:
        text = f"{text} {unit}".strip()
    return text


def disclosure_zh(state: Any) -> str:
    if state is None or state == "" or str(state) == "None":
        return "已公开"
    mapping = {
        "reported_value": "已报告数值",
        "reported_zero": "已报告为零",
        "not_publicly_disclosed": UNPUBLISHED,
        "not_reported": "未报告",
        "not_applicable": "不适用",
        "below_reporting_threshold": "低于报告阈值",
        "unresolved_due_to_route": "路径未解析",
        "conflicting": "来源冲突",
        "comparable": "可比",
        "incompatible": "不兼容",
        "pending_verification": "待核实",
        "已公开": "已公开",
        UNPUBLISHED: UNPUBLISHED,
        "disclosed": "已披露",
        "partial": "部分披露",
        "undisclosed": UNPUBLISHED,
        "not_disclosed": UNPUBLISHED,
        "unpublished": UNPUBLISHED,
        "unknown": UNPUBLISHED,
    }
    return mapping.get(str(state), str(state))


def cutoff_zh(value: Any) -> str:
    text = str(value or "")
    if not text:
        return UNPUBLISHED
    if text.startswith("数据截止"):
        return text
    try:
        day = date.fromisoformat(text[:10])
    except ValueError:
        pass
    else:
        return f"数据截止：{day.year}年{day.month}月{day.day}日"
    return f"数据截止 {text}"


def product_map(products: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in products}


def trial_map(trials: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in trials}


def page_decorations(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    page_width, page_height = doc.pagesize
    canvas.setFillColor(tokens.PAGE_BG)
    canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    canvas.setStrokeColor(tokens.KZ_ORANGE)
    canvas.setLineWidth(2.0)
    canvas.line(tokens.MARGIN_X, page_height - 8, page_width - tokens.MARGIN_X, page_height - 8)
    canvas.setFillColor(tokens.INK_MUTED)
    canvas.setFont(doc.cjk_font, tokens.FOOTER_PT)
    footer = f"{doc.footer_label}  ·  第 {doc.page} 页"
    canvas.drawCentredString(page_width / 2.0, 10, footer)
    canvas.restoreState()


def make_doc(
    output_path: str, *, title: str, indication: str, footer_label: str
) -> BaseDocTemplate:
    register_cjk_fonts()
    regular_font, _bold_font = register_cjk_fonts()
    doc = BaseDocTemplate(
        str(output_path),
        pagesize=tokens.A4_PORTRAIT,
        leftMargin=tokens.MARGIN_X,
        rightMargin=tokens.MARGIN_X,
        topMargin=tokens.MARGIN_Y + 4,
        bottomMargin=tokens.MARGIN_Y,
        title=title,
        author="康哲药业",
        subject=indication,
        creator="ci_workflow.renderers.pdf_native",
    )
    doc.cjk_font = regular_font
    doc.footer_label = footer_label
    portrait_frame = Frame(
        tokens.MARGIN_X,
        tokens.MARGIN_Y,
        tokens.A4_PORTRAIT[0] - 2 * tokens.MARGIN_X,
        tokens.A4_PORTRAIT[1] - 2 * tokens.MARGIN_Y,
        id="portrait_frame",
    )
    landscape_frame = Frame(
        tokens.MARGIN_X,
        tokens.MARGIN_Y,
        tokens.A4_LANDSCAPE[0] - 2 * tokens.MARGIN_X,
        tokens.A4_LANDSCAPE[1] - 2 * tokens.MARGIN_Y,
        id="landscape_frame",
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="portrait",
                frames=[portrait_frame],
                pagesize=tokens.A4_PORTRAIT,
                onPage=page_decorations,
            ),
            PageTemplate(
                id="landscape",
                frames=[landscape_frame],
                pagesize=tokens.A4_LANDSCAPE,
                onPage=page_decorations,
            ),
        ]
    )
    return doc


def section_break(story: list[Any], *, landscape: bool = False) -> None:
    story.append(NextPageTemplate("landscape" if landscape else "portrait"))
    story.append(PageBreak())


def ensure_template(story: list[Any], *, landscape: bool = False) -> None:
    """Switch page template without forcing an immediate blank page when unused."""
    story.append(NextPageTemplate("landscape" if landscape else "portrait"))


def section_heading(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    title: str,
    *,
    caption: str | None = None,
) -> None:
    heading = [Paragraph(esc(title), styles["section"])]
    if caption:
        heading.append(Paragraph(esc(caption), styles["caption"]))
    story.append(KeepTogether(heading))


def cover_block(
    story: list[Any],
    *,
    styles: dict[str, ParagraphStyle],
    title: str,
    subtitle: str,
    indication: str,
    cutoff: str,
    bullets: Sequence[str] | None = None,
) -> None:
    """Polished cover. Summary bullets are optional for backward compatibility."""
    story.append(logo_image())
    story.append(Spacer(1, 8))
    story.append(AccentRule())
    story.append(Spacer(1, 10))
    story.append(Paragraph(esc(title), styles["cover_title"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(esc(subtitle), styles["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(esc(f"适应症：{indication}"), styles["body"]))
    story.append(Paragraph(esc(cutoff), styles["meta"]))
    story.append(Spacer(1, 10))
    story.append(AccentRule())
    if bullets:
        story.append(Spacer(1, 8))
        story.append(Paragraph("摘要", styles["section"]))
        for bullet in bullets:
            story.append(Paragraph(esc(bullet), styles["bullet"], bulletText="•"))


def toc_page(
    story: list[Any],
    *,
    styles: dict[str, ParagraphStyle],
    entries: Sequence[tuple[str, str]],
) -> None:
    """Distinct 目录 page. entries = [(group_zh, title_zh), ...]."""
    story.append(Paragraph("目录", styles["section"]))
    story.append(
        Paragraph(
            "按阅读顺序列出本报告各章节。",
            styles["caption"],
        )
    )
    story.append(AccentRule())
    story.append(Spacer(1, 4))
    current_group = None
    for group, title in entries:
        if group != current_group:
            current_group = group
            story.append(Spacer(1, 3))
            story.append(Paragraph(esc(group), styles["context"]))
        story.append(Paragraph(f"　• {esc(title)}", styles["body"]))


def executive_summary_page(
    story: list[Any],
    *,
    styles: dict[str, ParagraphStyle],
    bullets: Sequence[str],
    highlight_rows: Sequence[Sequence[Any]] | None = None,
    highlight_headers: Sequence[str] | None = None,
    highlight_widths: Sequence[float] | None = None,
) -> None:
    """Distinct 首页摘要 with decision-relevant disclosed facts only."""
    story.append(Paragraph("首页摘要", styles["section"]))
    story.append(
        Paragraph(
            "以下仅汇总本锁定快照中已披露、对比较解读最关键的观察；缺失项在正文完整保留为“未公开”。",
            styles["caption"],
        )
    )
    for bullet in bullets:
        story.append(Paragraph(esc(bullet), styles["bullet"], bulletText="•"))
    if highlight_rows and highlight_headers and highlight_widths:
        story.append(Spacer(1, 4))
        story.append(Paragraph("关键已披露结果一览", styles["caption"]))
        story.append(styled_table(highlight_headers, highlight_rows, styles, highlight_widths))


def iter_pairs(items: Iterable[Any]) -> list[Any]:
    return list(items)


# Re-export xml escape used by older call sites that imported esc/p from _layout.
_ = xml.sax.saxutils

__all__ = [
    "UNPUBLISHED",
    "AccentRule",
    "KeepTogether",
    "NextPageTemplate",
    "PageBreak",
    "Spacer",
    "bookmark",
    "bubble_matrix_chart",
    "continuation_table_blocks",
    "cover_block",
    "cutoff_zh",
    "disclosure_zh",
    "display_value",
    "efficacy_forest_chart",
    "efficacy_grouped_bar_chart",
    "ensure_template",
    "esc",
    "executive_summary_page",
    "iter_pairs",
    "longitudinal_line_chart",
    "make_doc",
    "make_styles",
    "p",
    "product_map",
    "safety_heatmap_chart",
    "section_break",
    "section_heading",
    "styled_table",
    "toc_page",
    "trial_map",
]
