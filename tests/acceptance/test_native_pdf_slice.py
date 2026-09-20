"""Task 8.1：中文 ReportViewModel 原生 PDF 垂直样例精确 RED。

本文件只定义垂直样例合同：fixture 必须是可校验的中文 ``ReportViewModel``，
构建输入不得含 HTML/Chromium；生成 PDF 后用结构断言覆盖页数、方向、书签、
可检索中文、续表重复表头与矢量比较图。实现由
``ci_workflow.renderers.pdf.vertical_slice`` 提供；本 RED 在实现前必须失败。
"""

from __future__ import annotations

import importlib
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from ci_workflow.reports.common.view_state import validate_report_view_model_payload

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "fixtures/synthetic/pdf-native-slice"
INPUTS = FIXTURE_ROOT / "inputs"
DOCUMENT_PATH = INPUTS / "document.json"
EFFICACY_VIEW_PATH = INPUTS / "efficacy_view.json"
SAFETY_VIEW_PATH = INPUTS / "safety_long_view.json"
DISPLAY_PROJECTION_PATH = INPUTS / "display_projection.json"

FORBIDDEN_INPUT_MARKERS = (
    "<html",
    "<!doctype html",
    "chromium",
    "playwright",
    "puppeteer",
    "chrome-headless",
    "weasyprint",
    "wkhtmltopdf",
)
FORBIDDEN_BUILDER_PARAMS = {
    "html",
    "html_path",
    "html_dir",
    "page_url",
    "chromium",
    "playwright",
    "browser",
    "browser_type",
    "screenshot",
    "print_url",
}

_A4_PORTRAIT = (595.27, 841.89)
_A4_LANDSCAPE = (841.89, 595.27)
_PT_TOLERANCE = 2.0


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _package_text_blob() -> str:
    parts: list[str] = []
    for path in sorted(INPUTS.glob("*.json")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts).lower()


def _import_builder():
    try:
        module = importlib.import_module("ci_workflow.renderers.pdf.vertical_slice")
    except ImportError as error:
        pytest.fail(
            "RED: 缺少原生 PDF 垂直样例构建模块 "
            f"ci_workflow.renderers.pdf.vertical_slice（{error}）"
        )
    builder = getattr(module, "build_native_pdf_vertical_slice", None)
    if builder is None or not callable(builder):
        pytest.fail(
            "RED: ci_workflow.renderers.pdf.vertical_slice 必须导出 "
            "build_native_pdf_vertical_slice(...)"
        )
    return builder


def _build_candidate(tmp_path: Path) -> Path:
    builder = _import_builder()
    signature = inspect.signature(builder)
    for name in signature.parameters:
        if name in FORBIDDEN_BUILDER_PARAMS or any(
            marker in name.lower()
            for marker in ("html", "chromium", "playwright", "browser", "screenshot")
        ):
            pytest.fail(
                f"RED: 构建入口不得接受 HTML/Chromium 相关参数：{name}"
            )

    output_path = tmp_path / "pdfs" / "native-pdf-vertical-slice.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = builder(package_dir=FIXTURE_ROOT, output_path=output_path)
    assert Path(result) == output_path
    assert output_path.is_file()
    assert output_path.stat().st_size > 1000
    return output_path


def _page_size(page: Any) -> tuple[float, float]:
    box = page.mediabox
    return (float(box.width), float(box.height))


def _is_portrait(size: tuple[float, float]) -> bool:
    width, height = size
    return height - width > _PT_TOLERANCE


def _is_landscape(size: tuple[float, float]) -> bool:
    width, height = size
    return width - height > _PT_TOLERANCE


def _matches_a4(size: tuple[float, float], expected: tuple[float, float]) -> bool:
    return (
        abs(size[0] - expected[0]) <= _PT_TOLERANCE
        and abs(size[1] - expected[1]) <= _PT_TOLERANCE
    )


def _pdftotext(path: Path) -> str:
    binary = shutil.which("pdftotext")
    if binary is None:
        pytest.fail("RED 环境缺少 pdftotext，无法验证可检索中文")
    completed = subprocess.run(
        [binary, "-layout", str(path), "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.fail(f"pdftotext 失败：{completed.stderr.strip()}")
    return completed.stdout


def _page_texts(path: Path) -> list[str]:
    binary = shutil.which("pdftotext")
    if binary is None:
        pytest.fail("RED 环境缺少 pdftotext，无法逐页抽取文本")
    reader = PdfReader(str(path))
    texts: list[str] = []
    for index in range(len(reader.pages)):
        completed = subprocess.run(
            [
                binary,
                "-f",
                str(index + 1),
                "-l",
                str(index + 1),
                "-layout",
                str(path),
                "-",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            pytest.fail(
                f"pdftotext 第 {index + 1} 页失败：{completed.stderr.strip()}"
            )
        texts.append(completed.stdout)
    return texts


def _content_has_vector_drawing(page: Any) -> bool:
    contents = page.get_contents()
    if contents is None:
        return False
    if isinstance(contents, list):
        raw = b"".join(item.get_data() for item in contents)
    else:
        raw = contents.get_data()
    text = raw.decode("latin-1", errors="ignore")
    operators = (" re", " m", " l", " c", " S", " s", " f", " F", " B", " b")
    return any(token in text for token in operators)


def test_chinese_report_view_models_validate_against_production_contract() -> None:
    document = _load(DOCUMENT_PATH)
    efficacy = validate_report_view_model_payload(_load(EFFICACY_VIEW_PATH))
    safety = validate_report_view_model_payload(_load(SAFETY_VIEW_PATH))
    projection = _load(DISPLAY_PROJECTION_PATH)

    assert (
        document["report_snapshot_id"]
        == efficacy.report_snapshot_id
        == safety.report_snapshot_id
    )
    assert efficacy.page_responsibility_id == "efficacy"
    assert safety.page_responsibility_id == "safety"
    assert len(efficacy.rows) == 6
    assert len(safety.rows) >= 30
    assert all(
        re.search(r"[\u4e00-\u9fff]", row.display_label_zh) for row in efficacy.rows
    )
    assert all(
        re.search(r"[\u4e00-\u9fff]", row.display_label_zh) for row in safety.rows
    )

    efficacy_ids = {row.row_id for row in efficacy.rows}
    safety_ids = {row.row_id for row in safety.rows}
    assert {point["row_id"] for point in projection["efficacy_points"]} == efficacy_ids
    assert {point["row_id"] for point in projection["safety_points"]} == safety_ids
    assert projection["report_snapshot_id"] == document["report_snapshot_id"]


def test_fixture_inputs_contain_no_html_or_chromium_markers() -> None:
    document = _load(DOCUMENT_PATH)
    constraints = json.dumps(
        document.get("build_constraints", {}), ensure_ascii=False
    ).lower()
    blob = _package_text_blob().replace(constraints, "")
    for marker in FORBIDDEN_INPUT_MARKERS:
        assert marker not in blob, f"fixture 输入不得包含 {marker!r}"
    for path in INPUTS.glob("*"):
        assert path.suffix.lower() != ".html"
        assert "chromium" not in path.name.lower()


def test_builder_entry_rejects_html_chromium_parameters_and_consumes_package(
    tmp_path: Path,
) -> None:
    output_path = _build_candidate(tmp_path)
    assert list(output_path.parent.glob("*.html")) == []
    assert list(tmp_path.rglob("*.html")) == []


def test_native_pdf_has_expected_pages_orientations_and_chinese_bookmarks(
    tmp_path: Path,
) -> None:
    document = _load(DOCUMENT_PATH)
    output_path = _build_candidate(tmp_path)
    reader = PdfReader(str(output_path))

    assert len(reader.pages) >= int(document["expected_structure"]["min_pages"])

    sizes = [_page_size(page) for page in reader.pages]
    assert _is_portrait(sizes[0]), "首页必须纵向"
    assert _matches_a4(sizes[0], _A4_PORTRAIT) or (
        abs(sizes[0][0] - _A4_PORTRAIT[0]) <= 4
        and abs(sizes[0][1] - _A4_PORTRAIT[1]) <= 4
    )
    assert any(_is_landscape(size) for size in sizes), "文档必须包含横向比较页"
    landscape_indexes = [
        index for index, size in enumerate(sizes) if _is_landscape(size)
    ]
    assert landscape_indexes, "缺少横向页"
    assert _matches_a4(sizes[landscape_indexes[0]], _A4_LANDSCAPE) or (
        abs(sizes[landscape_indexes[0]][0] - _A4_LANDSCAPE[0]) <= 4
        and abs(sizes[landscape_indexes[0]][1] - _A4_LANDSCAPE[1]) <= 4
    )
    assert any(
        index > landscape_indexes[0] and _is_portrait(size)
        for index, size in enumerate(sizes)
    ), "横向比较页之后必须回到纵向长表"

    outlines = getattr(reader, "outline", None) or getattr(reader, "outlines", None)
    assert outlines, "必须生成目录书签"
    flat_titles: list[str] = []

    def _walk(items: Any) -> None:
        for item in items:
            if isinstance(item, list):
                _walk(item)
                continue
            title = getattr(item, "title", None)
            if title is None and isinstance(item, dict):
                title = item.get("/Title")
            if title is not None:
                flat_titles.append(str(title))

    _walk(outlines)
    expected_bookmarks = [item["title_zh"] for item in document["bookmarks"]]
    for title in expected_bookmarks:
        assert title in flat_titles, f"缺少中文书签：{title}"


def test_native_pdf_chinese_text_is_selectable_and_searchable(tmp_path: Path) -> None:
    document = _load(DOCUMENT_PATH)
    output_path = _build_candidate(tmp_path)
    text = _pdftotext(output_path)
    assert text.strip(), "PDF 必须包含可抽取文本，不得整页栅格化"
    for phrase in document["expected_structure"]["searchable_chinese_phrases"]:
        assert phrase in text, f"关键中文不可检索：{phrase}"
    for banned in ("Traceback", "DEBUG", "TODO", "chromium", "playwright", "<html"):
        assert banned not in text


def test_long_table_continuation_repeats_header_and_clinical_context(
    tmp_path: Path,
) -> None:
    output_path = _build_candidate(tmp_path)
    page_texts = _page_texts(output_path)
    reader = PdfReader(str(output_path))
    sizes = [_page_size(page) for page in reader.pages]
    landscape_indexes = [
        index for index, size in enumerate(sizes) if _is_landscape(size)
    ]
    assert landscape_indexes
    long_table_start = landscape_indexes[0] + 1
    assert long_table_start < len(page_texts), "缺少纵向长表页"
    long_table_pages = page_texts[long_table_start:]
    assert len(long_table_pages) >= 2, "长表必须跨页以验证续表"

    header_tokens = ("不良事件", "发生率", "治疗组", "示例试验 01", "至第52周")
    first_long = long_table_pages[0]
    for token in header_tokens:
        assert token in first_long, f"长表首页缺少语境/表头：{token}"

    for index, page_text in enumerate(long_table_pages[1:], start=2):
        assert "续表" in page_text, f"长表第 {index} 页必须标明续表"
        for token in header_tokens:
            assert token in page_text, f"长表第 {index} 页必须重复表头/语境：{token}"


def test_comparison_chart_page_contains_vector_drawing_not_only_raster(
    tmp_path: Path,
) -> None:
    output_path = _build_candidate(tmp_path)
    reader = PdfReader(str(output_path))
    sizes = [_page_size(page) for page in reader.pages]
    landscape_indexes = [
        index for index, size in enumerate(sizes) if _is_landscape(size)
    ]
    assert landscape_indexes, "缺少横向比较页"
    chart_page = reader.pages[landscape_indexes[0]]
    assert _content_has_vector_drawing(chart_page), (
        "横向比较页必须包含原生矢量绘制内容（ReportLab Graphics），"
        "不得仅嵌入栅格图冒充比较图"
    )
    page_text = _page_texts(output_path)[landscape_indexes[0]]
    for token in ("EASI-75", "治疗组", "安慰剂组", "泰瑞奇单抗"):
        assert token in page_text
