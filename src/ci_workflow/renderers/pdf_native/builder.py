"""Minimal ReportLab builder for Task 8.1 native PDF vertical slice.

Consumes a Chinese ReportViewModel package directory and writes a native PDF.
No HTML, Chromium, or print-pipeline inputs are accepted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

from ci_workflow.renderers.pdf_native import tokens
from ci_workflow.renderers.pdf_native.flowables import (
    AccentRule,
    BookmarkFlowable,
    build_efficacy_chart,
    efficacy_snapshot_table,
    efficacy_table,
    logo_image,
    make_styles,
    safety_continuation_blocks,
)
from ci_workflow.renderers.pdf_native.fonts import register_cjk_fonts
from ci_workflow.reports.common.view_state import validate_report_view_model_payload

_FORBIDDEN_PARAM_MARKERS = (
    "html",
    "chromium",
    "playwright",
    "browser",
    "screenshot",
    "weasy",
    "wkhtml",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def _package_inputs(
    package_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    inputs = package_dir / "inputs"
    document = _load_json(inputs / "document.json")
    efficacy_view = _load_json(inputs / document["views"]["efficacy"])
    safety_view = _load_json(inputs / document["views"]["safety_long"])
    projection = _load_json(inputs / document["display_projection"])
    validate_report_view_model_payload(efficacy_view)
    validate_report_view_model_payload(safety_view)
    return document, efficacy_view, safety_view, projection


def _index_projection(
    projection: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    efficacy_points = list(projection.get("efficacy_points") or [])
    safety_points = list(projection.get("safety_points") or [])
    if not efficacy_points:
        raise ValueError("display_projection.efficacy_points 不能为空")
    if len(safety_points) < 2:
        raise ValueError("display_projection.safety_points 需要足够行数以验证跨页续表")
    return efficacy_points, safety_points


def _page_decorations(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    page_width, page_height = doc.pagesize
    canvas.setFillColor(tokens.PAGE_BG)
    canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # Top brand accent rule.
    canvas.setStrokeColor(tokens.KZ_ORANGE)
    canvas.setLineWidth(2.0)
    canvas.line(tokens.MARGIN_X, page_height - 8, page_width - tokens.MARGIN_X, page_height - 8)

    canvas.setFillColor(tokens.INK_MUTED)
    canvas.setFont(doc.cjk_font, tokens.FOOTER_PT)
    footer = f"{doc.footer_label}  ·  第 {doc.page} 页"
    canvas.drawCentredString(page_width / 2.0, 10, footer)
    canvas.restoreState()


def build_native_pdf_vertical_slice(*, package_dir: Path | str, output_path: Path | str) -> Path:
    """Build the Task 8.1 vertical-slice PDF from a ReportViewModel package.

    Parameters are intentionally limited to package_dir/output_path so callers
    cannot inject HTML/Chromium print inputs.
    """
    # Defensive: reject unexpected kwargs smuggled via partials in future wrappers.
    for name in ("package_dir", "output_path"):
        if any(marker in name for marker in _FORBIDDEN_PARAM_MARKERS):
            raise ValueError(f"forbidden parameter name: {name}")

    package = Path(package_dir)
    output = Path(output_path)
    if not package.is_dir():
        raise FileNotFoundError(f"package_dir 不存在：{package}")
    output.parent.mkdir(parents=True, exist_ok=True)

    document, _efficacy_view, _safety_view, projection = _package_inputs(package)
    efficacy_points, safety_points = _index_projection(projection)
    regular_font, _bold_font = register_cjk_fonts()
    styles = make_styles()

    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=tokens.MARGIN_X,
        rightMargin=tokens.MARGIN_X,
        topMargin=tokens.MARGIN_Y + 4,
        bottomMargin=tokens.MARGIN_Y,
        title=str(document["title_zh"]),
        author="康哲药业",
        subject=str(document["indication_zh"]),
        creator="ci_workflow.renderers.pdf_native",
    )
    doc.cjk_font = regular_font
    doc.footer_label = str(document["title_zh"])

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
                onPage=_page_decorations,
            ),
            PageTemplate(
                id="landscape",
                frames=[landscape_frame],
                pagesize=tokens.A4_LANDSCAPE,
                onPage=_page_decorations,
            ),
        ]
    )

    bookmark_titles = {
        item["target_id"]: item["title_zh"] for item in document.get("bookmarks", [])
    }
    story: list[Any] = []

    # 1) Portrait cover + summary
    story.append(
        BookmarkFlowable(
            "cover-summary",
            str(bookmark_titles.get("cover-summary", "封面与摘要")),
        )
    )
    story.append(logo_image())
    story.append(Spacer(1, 6))
    story.append(AccentRule())
    story.append(Spacer(1, 8))
    story.append(Paragraph(str(document["title_zh"]), styles["cover_title"]))
    story.append(Paragraph(str(document["cover_subtitle_zh"]), styles["subtitle"]))
    story.append(
        Paragraph(
            f"适应症：{document['indication_zh']}　｜　{document['data_cutoff_zh']}",
            styles["meta"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("摘要", styles["section"]))
    for bullet in document.get("summary_bullets_zh", []):
        story.append(Paragraph(f"• {bullet}", styles["bullet"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("第16周疗效概览", styles["section"]))
    story.append(
        Paragraph(
            "EASI-75 应答率；组间差值仅用于直观阅读，不进行跨试验合并。",
            styles["caption"],
        )
    )
    story.append(efficacy_snapshot_table(efficacy_points, styles))

    # 2) Landscape efficacy comparison: chart then complete table
    story.append(NextPageTemplate("landscape"))
    story.append(PageBreak())
    story.append(
        BookmarkFlowable(
            "efficacy-comparison",
            str(bookmark_titles.get("efficacy-comparison", "疗效比较")),
        )
    )
    story.append(Paragraph("疗效比较", styles["section"]))
    story.append(
        Paragraph(
            "各产品治疗组与相应安慰剂组按原研究结果并列，未进行跨试验合并。",
            styles["caption"],
        )
    )
    usable_landscape_width = tokens.A4_LANDSCAPE[0] - 2 * tokens.MARGIN_X
    chart = build_efficacy_chart(
        efficacy_points,
        width=usable_landscape_width,
        height=150,
    )
    story.append(chart)
    story.append(Spacer(1, 4))
    story.append(Paragraph("第16周 EASI-75 完整数据表", styles["caption"]))
    story.append(efficacy_table(efficacy_points, styles))

    # 3) Portrait long safety table with continuation headers
    story.append(NextPageTemplate("portrait"))
    story.append(PageBreak())
    story.append(
        BookmarkFlowable(
            "safety-detail-table",
            str(bookmark_titles.get("safety-detail-table", "安全性明细表")),
        )
    )
    story.append(Paragraph("安全性明细表", styles["section"]))
    story.append(
        Paragraph(
            "按发生率由高到低列示；治疗组、观察时间窗及分析人群在表题中标明。",
            styles["caption"],
        )
    )
    story.extend(
        safety_continuation_blocks(
            safety_points,
            styles,
            rows_per_page=16,
        )
    )

    doc.build(story)
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"PDF 生成失败或文件过小：{output}")
    return output
