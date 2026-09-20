"""Task 8.2 PDF06–PDF08：C 类完整原生 PDF 投影精确合同。"""

from __future__ import annotations

import importlib
import inspect
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from pypdf import PdfReader

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "fixtures/synthetic/three-report-complete"
REPORT_C = CASE / "inputs" / "report-c-data.json"

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
        module = importlib.import_module("ci_workflow.renderers.pdf_native.projections.c")
    except ImportError as error:
        pytest.fail(f"RED: 缺少 C 类 PDF 投影模块（{error}）")
    builder = getattr(module, "build_report_c_native_pdf", None)
    if builder is None or not callable(builder):
        pytest.fail("RED: projections.c 必须导出 build_report_c_native_pdf(...)")
    for name in inspect.signature(builder).parameters:
        if name in FORBIDDEN_BUILDER_PARAMS or any(
            marker in name.lower()
            for marker in ("html", "chromium", "playwright", "browser", "screenshot")
        ):
            pytest.fail(f"RED: C PDF 构建入口不得接受 HTML/Chromium 参数：{name}")
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
    output = tmp_path / "reports" / "C" / "v-fixture-001" / "report.pdf"
    result = builder(report_data_path=REPORT_C, output_path=output)
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


def test_c_pdf_contains_design_map_population_eligibility_and_intervention(
    tmp_path: Path,
) -> None:
    output = _build(tmp_path)
    reader = PdfReader(str(output))
    assert len(reader.pages) >= 6
    text = _extract_text(output)
    for needle in (
        "特应性皮炎",
        "设计图谱",
        "人群与疾病定义",
        "入选标准",
        "排除标准",
        "分组、干预与对照",
        "度普利尤单抗",
        "Lebrikizumab",
        "奈莫利珠单抗",
        "CHRONOS",
        "ADvocate2",
        "未公开",
    ):
        assert needle in text, f"缺少可检索内容：{needle}"

    titles = _outline_titles(reader)
    for bookmark in (
        "设计图谱",
        "人群与疾病定义",
        "入选标准",
        "排除标准",
        "分组、干预与对照",
    ):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"


def test_c_pdf_contains_endpoint_visit_and_statistics_with_chart_before_table(
    tmp_path: Path,
) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)
    for needle in (
        "终点、定义与时间点",
        "访视、疗程与随访",
        "样本量、分析集与统计设计",
        "分析人群",
        "未公开",
        "终点—定义—时间点矩阵图",
        "访视时间线图",
        "样本量气泡图",
        "完整表",
    ):
        assert needle in text, f"缺少终点/访视/统计责任：{needle}"

    assert text.find("终点—定义—时间点矩阵图") < text.find("终点、定义与时间点完整表")
    assert text.find("访视时间线图") < text.find("访视、疗程与随访完整表")
    assert text.find("样本量气泡图") < text.find("样本量、分析集与统计设计完整表")

    titles = _outline_titles(PdfReader(str(output)))
    for bookmark in ("终点、定义与时间点", "访视、疗程与随访", "样本量、分析集与统计设计"):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"

    # Clinical time units must remain readable in every table column, not only
    # in the dedicated timepoint column. These exact regressions previously
    # rendered as “诱导期1 / 6周” and “第16 / 周”.
    for broken in (
        r"诱导期1\s*\n\s*6周",
        r"治疗至第16\s*\n\s*周",
        r"第5\s*\n\s*2周",
    ):
        assert re.search(broken, text) is None, f"临床时间单位被拆行：{broken}"
    for week in ("0周", "16周", "24周", "52周"):
        assert week in text, f"访视时间线缺少真实周数刻度：{week}"
    assert "A–H" not in text
    assert "位置不表示时间顺序" not in text


def test_c_pdf_contains_trial_dossiers_patterns_and_multipath(tmp_path: Path) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)
    for needle in (
        "逐试验详情",
        "试验档案",
        "设计模式、权衡与可选路径",
        "候选设计路径",
        "前提",
        "权衡",
        "路径1",
        "路径2",
        "NCT02260986",
        "NCT04178967",
        "NCT03985943",
        "NCT05149313",
        "资料版本与局限",
    ):
        assert needle in text, f"缺少逐试验/多路径责任：{needle}"

    titles = _outline_titles(PdfReader(str(output)))
    for bookmark in (
        "逐试验详情",
        "设计模式、权衡与可选路径",
        "资料版本与局限",
        "NCT02260986",
        "NCT05149313",
    ):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"


def test_c_pdf_has_cover_toc_summary_and_dense_short_sections(tmp_path: Path) -> None:
    output = _build(tmp_path)
    reader = PdfReader(str(output))
    text = _extract_text(output)
    for needle in ("封面", "目录", "首页摘要", "关键已披露结果一览"):
        assert needle in text, f"缺少首页结构：{needle}"
    titles = _outline_titles(reader)
    for bookmark in ("封面", "目录", "首页摘要"):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"

    # Short known sections must not occupy solitary near-empty pages after front matter.
    sparse = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        chars = len("".join(page_text.split()))
        if index <= 3:
            continue
        solo = [
            name
            for name in (
                "人群与疾病定义完整表",
                "入选标准完整表",
                "排除标准完整表",
                "访视、疗程与随访完整表",
                "样本量、分析集与统计设计完整表",
                "资料版本与局限完整表",
            )
            if name in page_text
        ]
        if len(solo) == 1 and chars < 240 and "续表" not in page_text:
            companions = sum(
                1
                for title in (
                    "设计图谱",
                    "人群与疾病定义",
                    "入选标准",
                    "排除标准",
                    "分组、干预与对照",
                    "终点、定义与时间点",
                    "访视、疗程与随访",
                    "样本量、分析集与统计设计",
                    "设计模式",
                    "资料版本与局限",
                )
                if title in page_text
            )
            if companions <= 1:
                sparse.append((index, solo[0], chars))
    assert not sparse, f"发现稀疏短节页：{sparse}"


def test_c_pdf_limits_and_toc_copy_is_audience_facing(tmp_path: Path) -> None:
    module = importlib.import_module("ci_workflow.renderers.pdf_native.projections.c")
    source = inspect.getsource(module.build_report_c_native_pdf)
    assert "呈现登记版本、设计事实来源范围和影响解释的局限。" in source
    for leaked in ("技术过程不进入受众页", "技术过程", "受众页"):
        assert leaked not in source, f"C20 投影仍含内部过程措辞：{leaked}"

    text = _extract_text(_build(tmp_path))
    assert "呈现登记版本、设计事实来源范围和影响解释的局限。" in text
    assert "按阅读顺序列出本报告各章节。" in text
    for leaked in ("技术过程不进入受众页", "技术过程", "受众页", "责任章节", "书签与下表标题"):
        assert leaked not in text, f"C 类用户页残留内部过程措辞：{leaked}"


def test_c_pdf_keeps_endpoint_and_supporting_trial_identities_readable(
    tmp_path: Path,
) -> None:
    text = _extract_text(_build(tmp_path))
    for broken in (
        r"ADvoc\s*\n\s*ate2",
        r"ADvantage\s*\n\s*[）)]",
        r"CHRONOS\s*\n\s*[）)]",
        r"主要终点（IGA\s*\n\s*）",
        r"主要终点（EASI\s*\n\s*）",
        r"终点披\s*\n\s*露",
        r"时间披\s*\n\s*露",
    ):
        assert re.search(broken, text) is None, f"身份列硬折行：{broken}"
    compact = re.sub(r"\s+", "", text)
    for needle in (
        "ADvocate2",
        "ADvantage",
        "CHRONOS",
        "主要终点（IGA）",
        "终点披露",
        "时间披露",
        "支撑试验",
    ):
        assert needle in compact, f"缺少可检索身份：{needle}"
