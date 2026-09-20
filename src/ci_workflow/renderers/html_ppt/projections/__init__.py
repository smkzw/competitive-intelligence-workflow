"""HTML-PPT report projections."""

from ci_workflow.renderers.html_ppt.projections.a import build_report_a_html_ppt
from ci_workflow.renderers.html_ppt.projections.b import build_report_b_html_ppt
from ci_workflow.renderers.html_ppt.projections.c import build_report_c_html_ppt

__all__ = [
    "build_report_a_html_ppt",
    "build_report_b_html_ppt",
    "build_report_c_html_ppt",
]
