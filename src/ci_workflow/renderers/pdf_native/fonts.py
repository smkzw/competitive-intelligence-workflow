"""Resolve an embeddable CJK-capable TrueType font for searchable Chinese text."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]

FONT_FAMILY = "CIWorkflowCJK"
FONT_FAMILY_BOLD = "CIWorkflowCJK-Bold"

_FONT_CANDIDATES: tuple[Path, ...] = (
    Path.home() / "Library/Fonts/NotoSansSC-Regular.ttf",
    Path.home() / "Library/Fonts/NotoSansSC-Bold.ttf",
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
)


class MissingCJKFontError(RuntimeError):
    """No embeddable Chinese font is available on this host."""


def _existing_candidates() -> list[Path]:
    found: list[Path] = []
    for path in _FONT_CANDIDATES:
        if path.is_file():
            found.append(path)
    override = os.environ.get("CI_WORKFLOW_PDF_CJK_FONT")
    if override:
        override_path = Path(override)
        if override_path.is_file():
            found.insert(0, override_path)
    return found


@lru_cache(maxsize=1)
def register_cjk_fonts() -> tuple[str, str]:
    """Register regular/bold CJK faces and return ReportLab font names."""
    candidates = _existing_candidates()
    if not candidates:
        raise MissingCJKFontError(
            "未找到可嵌入的中文字体。请安装 Noto Sans SC / Arial Unicode，"
            "或设置 CI_WORKFLOW_PDF_CJK_FONT 指向 .ttf/.otf 文件。"
        )

    regular_path = next(
        (path for path in candidates if "bold" not in path.name.lower()),
        candidates[0],
    )
    bold_path = next(
        (path for path in candidates if "bold" in path.name.lower()),
        regular_path,
    )

    if FONT_FAMILY not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_FAMILY, str(regular_path)))
    if FONT_FAMILY_BOLD not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_FAMILY_BOLD, str(bold_path)))
    return FONT_FAMILY, FONT_FAMILY_BOLD
