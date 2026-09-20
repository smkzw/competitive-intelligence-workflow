"""Native PDF projections for complete A/B/C reports."""

from ci_workflow.renderers.pdf_native.projections.a import build_report_a_native_pdf
from ci_workflow.renderers.pdf_native.projections.b import build_report_b_native_pdf
from ci_workflow.renderers.pdf_native.projections.c import build_report_c_native_pdf

__all__ = [
    "build_report_a_native_pdf",
    "build_report_b_native_pdf",
    "build_report_c_native_pdf",
]
