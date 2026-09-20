"""Task 8.1 原生 PDF 设计 token：对齐康哲 core / track_pdf，不引入新依赖。"""

from __future__ import annotations

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.lib.colors import Color, HexColor  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4, landscape  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]

# Brand emphasis (core §0.8.1) — MUST keep HEX.
KZ_ORANGE = HexColor("#FF9900")
KZ_YELLOW = HexColor("#FFCC00")
KZ_ORANGE_MID = HexColor("#F5A000")
KZ_RISK = HexColor("#C00000")
KZ_TABLE_HEADER = HexColor("#F79646")
KZ_MEDICAL_TINT = HexColor("#FBE3D6")

# Neutral reading surface (track_pdf / core).
PAGE_BG = HexColor("#FFFEFB")  # warm white
INK = HexColor("#1A1A1A")
INK_MUTED = HexColor("#404040")
RULE = HexColor("#D9D2C5")
TABLE_GRID = HexColor("#C9C1B4")
PLACEBO_FILL = HexColor("#8A8580")
TREATMENT_FILL = KZ_ORANGE

A4_PORTRAIT = A4
A4_LANDSCAPE = landscape(A4)

MARGIN_X = 16 * mm
MARGIN_Y = 14 * mm
HEADER_BAND = 10 * mm
FOOTER_BAND = 10 * mm

BODY_PT = 10.0
TITLE_PT = 18.0
SECTION_PT = 13.0
TABLE_PT = 8.5
CAPTION_PT = 9.5
FOOTER_PT = 8.5


def tint(color: Color, factor: float = 0.18) -> Color:
    """Lighten a solid color toward white for soft fills."""
    return Color(
        color.red + (1.0 - color.red) * factor,
        color.green + (1.0 - color.green) * factor,
        color.blue + (1.0 - color.blue) * factor,
    )
