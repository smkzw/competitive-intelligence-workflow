"""Task 8.2 PDF01–PDF02：A 类完整原生 PDF 投影精确合同。"""

from __future__ import annotations

import importlib
import inspect
import shutil
import subprocess
from pathlib import Path

import pytest
from pypdf import PdfReader

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "fixtures/synthetic/three-report-complete"
REPORT_A = CASE / "inputs" / "report-a-data.json"

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


def _import_builder():
    try:
        module = importlib.import_module("ci_workflow.renderers.pdf_native.projections.a")
    except ImportError as error:
        pytest.fail(f"RED: 缺少 A 类 PDF 投影模块（{error}）")
    builder = getattr(module, "build_report_a_native_pdf", None)
    if builder is None or not callable(builder):
        pytest.fail("RED: projections.a 必须导出 build_report_a_native_pdf(...)")
    for name in inspect.signature(builder).parameters:
        if name in FORBIDDEN_BUILDER_PARAMS or any(
            marker in name.lower()
            for marker in ("html", "chromium", "playwright", "browser", "screenshot")
        ):
            pytest.fail(f"RED: A PDF 构建入口不得接受 HTML/Chromium 参数：{name}")
    return builder


def _extract_text(path: Path) -> str:
    binary = shutil.which("pdftotext")
    if binary is not None:
        completed = subprocess.run(
            [binary, "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _build(tmp_path: Path) -> Path:
    builder = _import_builder()
    output = tmp_path / "reports" / "A" / "v-fixture-001" / "report.pdf"
    result = builder(report_data_path=REPORT_A, output_path=output)
    assert Path(result) == output
    assert output.is_file() and output.stat().st_size > 2000
    return output


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

    walk(reader.outline or [])
    return titles


def test_a_pdf_contains_complete_profile_and_landscape_sections(tmp_path: Path) -> None:
    output = _build(tmp_path)
    reader = PdfReader(str(output))
    assert len(reader.pages) >= 4
    text = _extract_text(output)
    assert "数据截止：2026年7月31日" in text
    assert "2026-07-31T23:59:59+08:00" not in text
    for needle in (
        "特应性皮炎",
        "竞争格局",
        "产品总览",
        "临床开发组合",
        "中国与全球监管",
        "企业与交易",
        "专利与保护",
        "泰瑞奇单抗",
        "安澜双抗",
        "瑞格替尼",
        "诺维单抗",
        "未公开",
    ):
        assert needle in text, f"缺少可检索内容：{needle}"

    titles = _outline_titles(reader)
    for bookmark in (
        "竞争格局",
        "产品总览",
        "临床开发组合",
        "中国与全球监管",
        "企业与交易",
        "专利与保护",
    ):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"


def test_a_pdf_contains_comparison_charts_followed_by_complete_tables(
    tmp_path: Path,
) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)
    for needle in (
        "疗效",
        "安全性",
        "疗效与安全性矩阵",
        "治疗组",
        "对照组",
        "EASI-75",
        "治疗期间不良事件",
        "严重不良事件",
        "特别关注不良事件",
        "常见不良事件",
        "气泡面积反映治疗组样本量",
    ):
        assert needle in text, f"缺少比较责任：{needle}"

    efficacy_chart = text.find("疗效比较图")
    efficacy_table = text.find("疗效完整数据表")
    safety_chart = text.find("安全性热图")
    safety_table = text.find("安全性完整数据表")
    matrix_chart = text.find("疗效与安全性气泡图")
    matrix_table = text.find("疗效与安全性矩阵完整数据表")
    assert 0 <= efficacy_chart < efficacy_table
    assert 0 <= safety_chart < safety_table
    assert 0 <= matrix_chart < matrix_table
    assert "组间差值" in text or "治疗—对照" in text


def test_a_pdf_has_cover_toc_summary_and_no_sparse_profile_pages(tmp_path: Path) -> None:
    output = _build(tmp_path)
    reader = PdfReader(str(output))
    text = _extract_text(output)
    for needle in ("封面", "目录", "首页摘要", "关键已披露结果一览"):
        assert needle in text, f"缺少首页结构：{needle}"
    titles = _outline_titles(reader)
    for bookmark in ("封面", "目录", "首页摘要"):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"

    # Known sparse one-section anti-pattern: a content page that is only one short
    # profile/regulatory table after front matter.
    sparse = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        chars = len("".join(page_text.split()))
        if index <= 3:
            continue  # cover/目录/首页摘要 may be intentionally lighter
        solo_markers = (
            "企业与交易完整表",
            "专利与保护完整表",
            "监管事件完整表",
            "历史与边缘观察完整表",
            "研究依据与局限完整表",
        )
        # A sparse solo page contains exactly one of these titles and little else.
        hits = [marker for marker in solo_markers if marker in page_text]
        if len(hits) == 1 and chars < 240 and "续表" not in page_text:
            # Allow if another major section title coexists.
            companions = sum(
                1
                for title in (
                    "竞争格局",
                    "产品总览",
                    "临床开发组合",
                    "中国与全球监管",
                    "企业与交易",
                    "专利与保护",
                    "历史与边缘观察",
                    "研究依据与局限",
                    "疗效",
                    "安全性",
                )
                if title in page_text
            )
            if companions <= 1:
                sparse.append((index, hits[0], chars))
    assert not sparse, f"发现稀疏单节页：{sparse}"


def test_a_pdf_toc_copy_is_audience_facing(tmp_path: Path) -> None:
    text = _extract_text(_build(tmp_path))
    assert "按阅读顺序列出本报告各章节。" in text
    for leaked in ("责任章节", "书签与下表标题", "纸面阅读顺序"):
        assert leaked not in text, f"A 类目录残留内部过程措辞：{leaked}"
