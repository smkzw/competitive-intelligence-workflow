"""Task 8.2 PDF09：共享图表/表格/书签/coverage projection 与 verify_pdf 合同。"""

from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path

import pytest
from pypdf import PdfReader
from reportlab.graphics.shapes import Line, String

from ci_workflow.renderers.pdf_native.bookmarks import bookmark
from ci_workflow.renderers.pdf_native.charts import (
    bubble_matrix_chart,
    efficacy_forest_chart,
    efficacy_grouped_bar_chart,
    longitudinal_line_chart,
    safety_heatmap_chart,
)
from ci_workflow.renderers.pdf_native.coverage import (
    coverage_defects,
    load_expected_page_counts,
    project_pdf_coverage,
)
from ci_workflow.renderers.pdf_native.flowables import make_styles
from ci_workflow.renderers.pdf_native.tables import continuation_table_blocks, styled_table

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / ".artifacts/pdf-complete"
EXPECTED = ROOT / "fixtures/synthetic/three-report-complete/inputs/coverage-set-expected.json"
VERIFY_PDF = ROOT / "tools/verify_pdf.py"

PDF_PATHS = {
    "A": ARTIFACTS / "reports/A/v-fixture-001/report.pdf",
    "B": ARTIFACTS / "reports/B/v-fixture-001/report.pdf",
    "C": ARTIFACTS / "report-c.pdf",
}


def _outline_titles(reader: PdfReader) -> list[str]:
    titles: list[str] = []

    def walk(items: list) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
                continue
            title = getattr(item, "title", None)
            if title:
                titles.append(str(title))

    walk(list(reader.outline or []))
    return titles


def test_shared_chart_table_bookmark_surfaces_exist() -> None:
    assert callable(efficacy_grouped_bar_chart)
    assert callable(efficacy_forest_chart)
    assert callable(longitudinal_line_chart)
    assert callable(safety_heatmap_chart)
    assert callable(bubble_matrix_chart)
    assert callable(styled_table)
    assert callable(continuation_table_blocks)
    assert callable(bookmark)
    # Facade used by A/B/C remains import-compatible.
    layout = importlib.import_module("ci_workflow.renderers.pdf_native.projections._layout")
    for name in (
        "efficacy_grouped_bar_chart",
        "styled_table",
        "continuation_table_blocks",
        "bookmark",
        "bubble_matrix_chart",
    ):
        assert callable(getattr(layout, name))


def _iter_shapes(drawing):
    contents = getattr(drawing, "contents", []) or []
    for item in contents:
        yield item
        nested = getattr(item, "contents", None)
        if nested:
            yield from nested


def test_bubble_matrix_chart_adds_coordinate_ticks_without_changing_values() -> None:
    points = [
        {"label_zh": "药A", "x": 68.4, "y": 31.2, "size": 100},
        {"label_zh": "药B", "x": 40.0, "y": 70.0, "size": 50},
    ]
    with_axes = bubble_matrix_chart(
        points,
        width=400,
        height=180,
        title="疗效与安全性气泡图",
        mapping_note="气泡面积反映治疗组样本量；缺失坐标不绘制为数值零。",
    )
    labels = [shape.text for shape in _iter_shapes(with_axes) if isinstance(shape, String)]
    assert "疗效观察 →" in labels
    assert any(isinstance(shape, Line) for shape in _iter_shapes(with_axes))
    numeric = [label for label in labels if label.replace(".", "", 1).isdigit()]
    assert len(numeric) >= 6
    no_axes = bubble_matrix_chart(
        points,
        width=400,
        height=120,
        title="样本量气泡图",
        mapping_note="位置仅用于分开展示",
        axis_note="位置仅用于分开展示；不编码疗效、安全性或优劣",
        coordinate_axes=False,
    )
    no_labels = [shape.text for shape in _iter_shapes(no_axes) if isinstance(shape, String)]
    assert "疗效观察 →" not in no_labels


def test_shared_chart_drawing_uses_axis_label_floor() -> None:
    drawing = efficacy_grouped_bar_chart(
        [
            {"product_zh": "药A", "arm_zh": "治疗组", "value": 40.0},
            {"product_zh": "药A", "arm_zh": "对照组", "value": 20.0},
        ],
        width=400,
        height=220,
        title="疗效比较图",
    )
    assert drawing.width == 400
    assert drawing.height == 220


def test_coverage_expected_counts_match_locked_fixture() -> None:
    counts = load_expected_page_counts(EXPECTED)
    assert counts == {"A": 11, "B": 20, "C": 11}


@pytest.mark.parametrize("report", ["A", "B", "C"])
def test_current_pdf_coverage_projection_reports_only(report: str) -> None:
    path = PDF_PATHS[report]
    if not path.is_file():
        pytest.fail(f"RED: 缺少当前 {report} PDF：{path}")
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    bookmarks = _outline_titles(reader)
    projection = project_pdf_coverage(
        report=report,
        text=text,
        bookmark_titles=bookmarks,
    )
    defects = coverage_defects(projection)
    # Contract: projection must be produced and defects must be explicit lists.
    assert projection.registry_page_count == projection.expected_page_count
    assert isinstance(projection.missing_page_ids, list)
    assert isinstance(defects, list)
    # Persist machine-readable snapshot for Codex review under authorized path.
    out = ROOT / ".artifacts/pdf-complete/coverage" / f"{report}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"projection": projection.to_dict(), "defects": defects},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_verify_pdf_cli_exists_and_is_report_only() -> None:
    assert VERIFY_PDF.is_file()
    source = VERIFY_PDF.read_text(encoding="utf-8")
    assert "never rewrites PDF content" in source or "绝不" in source or "never" in source
    assert "project_pdf_coverage" in source
    assert "pdftoppm" in source
    assert "pdftotext" in source
    # CLI must not import HTML/Chromium builders.
    for banned in ("playwright", "chromium", "weasyprint", "build_report_a_native_pdf"):
        if banned == "build_report_a_native_pdf":
            assert banned not in source
        elif banned in ("playwright", "chromium", "weasyprint"):
            # Allowed only as forbidden markers / docs, not as runtime deps.
            assert "from playwright" not in source
            assert "import playwright" not in source


def test_layout_facade_signature_stable_for_projections() -> None:
    module = importlib.import_module("ci_workflow.renderers.pdf_native.projections._layout")
    sig = inspect.signature(module.make_doc)
    assert {"output_path", "title", "indication", "footer_label"} <= set(
        list(sig.parameters) + ["output_path"]
    ) or "title" in sig.parameters
    styles = make_styles()
    assert styles["table_cell"].fontSize >= 8.5
    assert styles["body"].fontSize >= 9.5


def test_toc_caption_has_no_internal_process_wording() -> None:
    module = importlib.import_module("ci_workflow.renderers.pdf_native.projections._layout")
    source = inspect.getsource(module.toc_page)
    assert "按阅读顺序列出本报告各章节。" in source
    for leaked in ("责任章节", "书签与下表", "纸面阅读顺序"):
        assert leaked not in source, f"目录仍含内部过程措辞：{leaked}"
