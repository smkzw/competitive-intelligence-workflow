"""Task 8.3 visual repair: keep C12/C20 identity tokens readable when wrapping."""

from __future__ import annotations

import pytest
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm

from ci_workflow.renderers.pdf_native.fonts import FONT_FAMILY, register_cjk_fonts
from ci_workflow.renderers.pdf_native.tables import _safe_clinical_lines

pytestmark = [pytest.mark.retained_legacy_format]


def _style() -> ParagraphStyle:
    register_cjk_fonts()
    return ParagraphStyle("table_cell", fontName=FONT_FAMILY, fontSize=8.5, leading=11)


def test_supporting_trial_column_does_not_split_latin_trial_names() -> None:
    style = _style()
    lines = _safe_clinical_lines(
        "NCT04178967（ADvocate2）\nNCT05149313（ADvantage）\nNCT02260986（CHRONOS）",
        style,
        52 * mm - 6,
    )
    for token in ("ADvocate2", "ADvantage", "CHRONOS"):
        assert any(token in line for line in lines), token
        assert not any(
            line.strip() and line.strip() != token and token.startswith(line.strip())
            for line in lines
        )
    assert all(not line.startswith("）") for line in lines)


def test_endpoint_column_keeps_scale_parenthetical_with_role() -> None:
    style = _style()
    assert _safe_clinical_lines("主要终点（IGA）", style, 32 * mm - 6) == ["主要终点（IGA）"]
    assert _safe_clinical_lines("终点披露", style, 20 * mm - 6) == ["终点披露"]
    assert _safe_clinical_lines("时间披露", style, 20 * mm - 6) == ["时间披露"]
