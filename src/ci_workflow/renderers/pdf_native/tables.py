"""Shared native ReportLab table helpers for Task 8.2 PDFs (PDF09)."""

from __future__ import annotations

import math
import re
import xml.sax.saxutils
from collections.abc import Sequence
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase.pdfmetrics import stringWidth  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ci_workflow.renderers.pdf_native import tokens
from ci_workflow.renderers.pdf_native.flowables import AccentRule


def esc(value: Any) -> str:
    return xml.sax.saxutils.escape("" if value is None else str(value))


_CLINICAL_TIME_TOKEN = re.compile(
    r"(?:(?:诱导|维持|治疗)期|(?:基线|治疗)至)?(?:第)?\d+(?:\.\d+)?(?:周|年|月|天)"
)
_LATIN_ID = r"(?:NCT\d+|[A-Za-z][A-Za-z0-9+./-]*)"
_LATIN_PARENS = rf"[（(]{_LATIN_ID}[）)]"
_TABLE_UNIT = re.compile(
    rf"("
    rf"{_CLINICAL_TIME_TOKEN.pattern}|"
    rf"[^\s、；;，,]{{1,12}}{_LATIN_PARENS}|"
    rf"{_LATIN_ID}{_LATIN_PARENS}?|"
    rf"{_LATIN_PARENS}|"
    rf"\s+|"
    rf".)",
    re.DOTALL,
)
_LEAD_PUNCT = re.compile(r"^[）)\]】。．.，,、；;：:]+")
_LATIN_ID_PARENS = re.compile(rf"^({_LATIN_ID})({_LATIN_PARENS})$")
_CJK_LATIN_PARENS = re.compile(rf"^(.+?)({_LATIN_PARENS})$")


def _split_overwide_unit(unit: str, style: ParagraphStyle, max_width: float) -> list[str]:
    """Keep identifiers intact; split only between a label and its latin parenthetical."""
    if stringWidth(unit, style.fontName, style.fontSize) <= max_width:
        return [unit]
    for pattern in (_LATIN_ID_PARENS, _CJK_LATIN_PARENS):
        matched = pattern.match(unit)
        if matched and stringWidth(matched.group(1), style.fontName, style.fontSize) <= max_width:
            return [matched.group(1), matched.group(2)]
    return [unit]


def _safe_clinical_lines(text: str, style: ParagraphStyle, max_width: float) -> list[str]:
    """Wrap table text without splitting time units, NCT IDs, or latin trial/endpoint names."""
    lines: list[str] = []
    for source_line in text.splitlines() or [""]:
        current = ""
        for match in _TABLE_UNIT.finditer(source_line):
            for unit in _split_overwide_unit(match.group(0), style, max_width):
                candidate = current + unit
                if current and stringWidth(candidate, style.fontName, style.fontSize) > max_width:
                    lines.append(current.rstrip())
                    current = unit.lstrip()
                else:
                    current = candidate
        lines.append(current.rstrip())
    merged: list[str] = []
    for line in lines:
        stripped = line.strip()
        if merged and stripped and _LEAD_PUNCT.match(stripped):
            merged[-1] = f"{merged[-1]}{stripped}"
        else:
            merged.append(line)
    return merged


def _table_markup(
    value: Any,
    style: ParagraphStyle,
    max_width: float | None = None,
) -> str:
    """Escape table text and keep clinical identities readable across wrapped columns."""
    text = "" if value is None else str(value)
    if max_width:
        return "<br/>".join(esc(line) for line in _safe_clinical_lines(text, style, max_width))
    return esc(text).replace("\n", "<br/>")


def p(
    text: Any,
    style: ParagraphStyle,
    *,
    max_width: float | None = None,
) -> Paragraph:
    return Paragraph(_table_markup(text, style, max_width), style)


def styled_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    styles: dict[str, ParagraphStyle],
    col_widths: Sequence[float],
) -> Table:
    data: list[list[Any]] = [
        [
            p(header, styles["table_header"], max_width=float(col_widths[index]) - 6)
            for index, header in enumerate(headers)
        ]
    ]
    for row in rows:
        data.append(
            [
                p(cell, styles["table_cell"], max_width=float(col_widths[index]) - 6)
                for index, cell in enumerate(row)
            ]
        )
    table = Table(data, colWidths=list(col_widths), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), tokens.KZ_MEDICAL_TINT),
                ("GRID", (0, 0), (-1, -1), 0.4, tokens.TABLE_GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, 0), 1.0, tokens.KZ_ORANGE),
            ]
        )
    )
    return table


def _balanced_chunks(
    rows: Sequence[Sequence[Any]], rows_per_page: int
) -> list[list[Sequence[Any]]]:
    """Split rows evenly so the final page is not a tiny leftover tail."""
    total = len(rows)
    if total == 0:
        return [[]]
    if total <= rows_per_page:
        return [list(rows)]
    page_count = max(1, math.ceil(total / rows_per_page))
    # Prefer fewer pages when the last page would be tiny.
    while page_count > 1 and total / page_count < max(4, rows_per_page * 0.45):
        page_count -= 1
    base = total // page_count
    rem = total % page_count
    chunks: list[list[Sequence[Any]]] = []
    cursor = 0
    for index in range(page_count):
        size = base + (1 if index < rem else 0)
        chunks.append(list(rows[cursor : cursor + size]))
        cursor += size
    return chunks


def continuation_table_blocks(
    *,
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    styles: dict[str, ParagraphStyle],
    col_widths: Sequence[float],
    rows_per_page: int = 14,
    first_page_rows: int | None = None,
    context: str | None = None,
    force_break_before: bool = False,
) -> list[Flowable]:
    """Emit a long table with repeated headers and explicit ``续表`` labels."""
    blocks: list[Flowable] = []
    if first_page_rows is not None and len(rows) > first_page_rows:
        chunks = [list(rows[:first_page_rows])]
        chunks.extend(_balanced_chunks(rows[first_page_rows:], rows_per_page))
    else:
        chunks = _balanced_chunks(rows, rows_per_page)
    for index, chunk in enumerate(chunks):
        if index > 0 or force_break_before:
            blocks.append(PageBreak())
        label = title if index == 0 else f"续表 · {title}"
        header_bits = [Paragraph(esc(label), styles["context"])]
        if context and index == 0:
            header_bits.append(Paragraph(esc(context), styles["caption"]))
        header_bits.extend([AccentRule(), Spacer(1, 1 * mm)])
        blocks.append(KeepTogether(header_bits))
        blocks.append(styled_table(headers, chunk, styles, col_widths))
    return blocks


__all__ = [
    "continuation_table_blocks",
    "esc",
    "p",
    "styled_table",
]
