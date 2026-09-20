#!/usr/bin/env python3
"""Render locked A/B/C HTML-PPT decks as single offline files.

Usage::

    uv run python tools/render_html_ppt.py --report A --output output/html-ppt/report-a.html
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ci_workflow.renderers.html_ppt.assets import REPO_ROOT
from ci_workflow.renderers.html_ppt.projections.a import build_report_a_html_ppt
from ci_workflow.renderers.html_ppt.projections.b import build_report_b_html_ppt
from ci_workflow.renderers.html_ppt.projections.c import build_report_c_html_ppt

BUILDERS = {
    "A": build_report_a_html_ppt,
    "B": build_report_b_html_ppt,
    "C": build_report_c_html_ppt,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成康哲单文件 HTML-PPT")
    parser.add_argument("--report", required=True, choices=["A", "B", "C"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    path = BUILDERS[args.report](output_path=Path(args.output), root=REPO_ROOT)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
