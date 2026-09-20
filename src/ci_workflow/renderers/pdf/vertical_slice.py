"""Task 8.1 RED-compatible entrypoint.

``tests/acceptance/test_native_pdf_slice.py`` imports
``ci_workflow.renderers.pdf.vertical_slice.build_native_pdf_vertical_slice``.
Implementation is owned by ``pdf_native``.
"""

from __future__ import annotations

from pathlib import Path

from ci_workflow.renderers.pdf_native.builder import build_native_pdf_vertical_slice as _build

__all__ = ["build_native_pdf_vertical_slice"]


def build_native_pdf_vertical_slice(*, package_dir: Path | str, output_path: Path | str) -> Path:
    """Delegate to the pdf_native builder without exposing HTML/Chromium parameters."""
    return _build(package_dir=package_dir, output_path=output_path)
