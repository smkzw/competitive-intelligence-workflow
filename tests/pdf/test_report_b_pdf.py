"""Task 8.2 PDF03–PDF05：B 类完整原生 PDF 投影精确合同。"""

from __future__ import annotations

import importlib
import inspect
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pypdf import PdfReader

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "fixtures/synthetic/three-report-complete"
REPORT_B = CASE / "inputs" / "report-b-data.json"

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
        module = importlib.import_module("ci_workflow.renderers.pdf_native.projections.b")
    except ImportError as error:
        pytest.fail(f"RED: 缺少 B 类 PDF 投影模块（{error}）")
    builder = getattr(module, "build_report_b_native_pdf", None)
    if builder is None or not callable(builder):
        pytest.fail("RED: projections.b 必须导出 build_report_b_native_pdf(...)")
    for name in inspect.signature(builder).parameters:
        if name in FORBIDDEN_BUILDER_PARAMS or any(
            marker in name.lower()
            for marker in ("html", "chromium", "playwright", "browser", "screenshot")
        ):
            pytest.fail(f"RED: B PDF 构建入口不得接受 HTML/Chromium 参数：{name}")
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
    output = tmp_path / "reports" / "B" / "v-fixture-001" / "report.pdf"
    result = builder(report_data_path=REPORT_B, output_path=output)
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


def test_b_pdf_contains_efficacy_safety_and_matrix_sections(tmp_path: Path) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)
    for needle in (
        "特应性皮炎",
        "疗效",
        "纵向结果",
        "安全性",
        "疗效与安全性矩阵",
        "治疗组",
        "对照组",
        "EASI-75",
        "柱状图",
        "折线图",
        "森林图",
        "热图",
        "气泡图",
        "完整数据表",
    ):
        assert needle in text, f"缺少疗效/安全/矩阵责任：{needle}"

    assert text.find("疗效比较柱状图") < text.find("疗效完整数据表")
    assert text.find("纵向结果折线图") < text.find("纵向结果完整数据表")
    assert text.find("安全性热图") < text.find("安全性完整数据表")
    assert text.find("疗效与安全性气泡图") < text.find("疗效与安全性矩阵完整数据表")


def test_b_pdf_uses_one_result_source_and_no_backend_labels(tmp_path: Path) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)

    # The efficacy, longitudinal and matrix pages must project the same locked
    # compact result set instead of mixing stale detailed-view fixture values.
    for value in ("68.4", "31.2", "64.1", "28.9"):
        assert text.count(value) >= 3, f"跨页面疗效值未保持一致：{value}"
    for stale in ("82.3", "80.5", "突破性溶血"):
        assert stale not in text, f"出现跨适应症或旧视图污染：{stale}"
    for backend_label in ("sample_size", "source_other"):
        assert backend_label not in text, f"用户页面残留后端标签：{backend_label}"


def test_b_fixture_has_no_cross_indication_detail_view_contamination() -> None:
    payload = json.loads(REPORT_B.read_text(encoding="utf-8"))
    raw = REPORT_B.read_text(encoding="utf-8")
    for stale in ("nct04558918", "血红蛋白较基线", "突破性溶血"):
        assert stale not in raw, f"B 类特应性皮炎基准残留跨适应症数据：{stale}"
    for view in ("baseline_views", "disposition_views"):
        facts = payload[view]["facts"]
        assert facts
        assert all(row["disclosure_state"] == "not_publicly_disclosed" for row in facts)
        assert all(row["value"] is None and row["raw_value"] == "未公开" for row in facts)
        assert all(row["source_role"] == "clinical_trial_registry" for row in facts)
    assert payload["efficacy_views"]["facts"] == []
    assert payload["safety_views"]["facts"] == []


def test_b_pdf_contains_arm_level_baseline_sections(tmp_path: Path) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)
    for needle in (
        "基线与人群总览",
        "人口学",
        "疾病语境",
        "基线疾病严重程度",
        "澄明-3",
        "HORIZON-AD",
        "治疗组",
        "对照组",
        "样本量",
        "年龄",
        "性别",
        "EASI",
        "未公开",
    ):
        assert needle in text, f"缺少基线责任：{needle}"

    titles = _outline_titles(PdfReader(str(output)))
    for bookmark in ("人口学", "疾病语境", "基线疾病严重程度"):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"
    assert "试验档案列示计划样本量" in text
    assert "两者不可直接互换" in text


def test_b_pdf_contains_disposition_denominators_reasons_and_missing_states(
    tmp_path: Path,
) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)
    for needle in (
        "试验完成情况",
        "受试者流转",
        "依从性",
        "失访与退出",
        "筛败",
        "补救治疗",
        "禁用药",
        "方案偏离",
        "产品与试验档案",
        "分母",
        "未公开",
        "澄明-3",
        "HORIZON-AD",
    ):
        assert needle in text, f"缺少完成/处置责任：{needle}"

    titles = _outline_titles(PdfReader(str(output)))
    for bookmark in ("试验完成情况", "产品与试验档案"):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"


def test_b_pdf_archive_coverage_keeps_arm_context(tmp_path: Path) -> None:
    output = _build(tmp_path)
    text = _extract_text(output)
    section = text[text.find("逐试验终点与安全性覆盖") :]
    assert "组别" in section
    assert "治疗组" in section
    assert "对照组" in section


def test_b_pdf_has_cover_toc_summary_and_dense_short_sections(tmp_path: Path) -> None:
    output = _build(tmp_path)
    reader = PdfReader(str(output))
    text = _extract_text(output)
    for needle in ("封面", "目录", "首页摘要", "关键已披露结果一览"):
        assert needle in text, f"缺少首页结构：{needle}"
    titles = _outline_titles(reader)
    for bookmark in ("封面", "目录", "首页摘要", "试验与暴露语境", "亚组与支持证据"):
        assert any(bookmark in title for title in titles), f"缺少书签：{bookmark}"

    # Short 未公开-heavy sections must not occupy solitary near-empty pages.
    sparse = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        chars = len("".join(page_text.split()))
        if index <= 3:
            continue
        solo = [
            name
            for name in ("依从性完整表", "补救治疗完整表", "禁用药使用完整表", "筛败与原因完整表")
            if name in page_text
        ]
        if len(solo) == 1 and chars < 220 and "续表" not in page_text:
            companions = sum(
                1
                for title in (
                    "依从性",
                    "筛败与原因",
                    "补救治疗",
                    "禁用药使用",
                    "方案偏离",
                    "失访与退出",
                )
                if title in page_text
            )
            if companions <= 1:
                sparse.append((index, solo[0], chars))
    assert not sparse, f"发现稀疏短节页：{sparse}"


def test_b_pdf_disposition_headers_are_clinician_readable(tmp_path: Path) -> None:
    module = importlib.import_module("ci_workflow.renderers.pdf_native.projections.b")
    source = inspect.getsource(module.build_report_b_native_pdf)
    for label in ("观察类别", "指标", "分母口径"):
        assert f'"{label}"' in source
    for leaked in ("字段族", "分母角色"):
        assert leaked not in source, f"完成情况投影仍含工程表头：{leaked}"

    text = _extract_text(_build(tmp_path))
    for needle in ("观察类别", "指标", "分母口径"):
        assert needle in text, f"完成情况表缺少临床医学可读表头：{needle}"
    for leaked in ("字段族", "分母角色"):
        assert leaked not in text, f"完成情况页残留工程表头：{leaked}"
    assert "按阅读顺序列出本报告各章节。" in text
    for leaked in ("责任章节", "书签与下表标题"):
        assert leaked not in text, f"B 类目录残留内部过程措辞：{leaked}"
