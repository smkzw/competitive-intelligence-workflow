"""原生 PDF 渲染包（Task 8.1 垂直样例 + Task 8.2 A/B/C 投影）。"""

from ci_workflow.renderers.pdf_native.builder import build_native_pdf_vertical_slice
from ci_workflow.renderers.pdf_native.coverage import (
    coverage_defects,
    project_pdf_coverage,
)
from ci_workflow.renderers.pdf_native.projections.a import build_report_a_native_pdf
from ci_workflow.renderers.pdf_native.projections.b import build_report_b_native_pdf
from ci_workflow.renderers.pdf_native.projections.c import build_report_c_native_pdf

__all__ = [
    "build_native_pdf_vertical_slice",
    "build_report_a_native_pdf",
    "build_report_b_native_pdf",
    "build_report_c_native_pdf",
    "coverage_defects",
    "project_pdf_coverage",
]
