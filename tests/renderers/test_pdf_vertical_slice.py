"""Renderer-level smoke for Task 8.1 native PDF vertical slice builder."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from ci_workflow.renderers.pdf_native import build_native_pdf_vertical_slice

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "fixtures/synthetic/pdf-native-slice"


def test_pdf_native_builder_writes_portrait_landscape_portrait(tmp_path: Path) -> None:
    output = tmp_path / "slice.pdf"
    result = build_native_pdf_vertical_slice(package_dir=PACKAGE, output_path=output)
    assert result == output
    reader = PdfReader(str(output))
    assert len(reader.pages) == 4
    widths = [float(page.mediabox.width) for page in reader.pages]
    heights = [float(page.mediabox.height) for page in reader.pages]
    assert heights[0] > widths[0]
    assert any(width > height for width, height in zip(widths, heights, strict=True))
    assert any(
        index > 0 and heights[index] > widths[index] and widths[index - 1] > heights[index - 1]
        for index in range(1, len(reader.pages))
    )
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "特应性皮炎" in text
    assert "续表" in text
    assert "EASI-75" in text
    assert "组间差值" in text
