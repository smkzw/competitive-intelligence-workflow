"""Task 8.3：最终 A10/B24/C20 原生 PDF 的只读验收合同。

这些测试只读取已锁定的交付 PDF，并在 pytest 临时目录中运行 verifier，避免
验收过程改写 PDF、fixture 或仓库中的验收产物。逐页文本和原始页图必须来自
本次 verifier 运行；contact sheet 只能作为总览，不能替代逐页证据。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "tools/verify_pdf.py"

PDFS = {
    "A": ROOT / "output/pdf/A类-特应性皮炎竞品全景.pdf",
    "B": ROOT / "output/pdf/B类-特应性皮炎临床试验结果比较.pdf",
    "C": ROOT / "output/pdf/C类-特应性皮炎临床试验设计比较.pdf",
}

# Task 8.2 已接受的最终文件摘要；任何字节变化都必须使本合同失败。
LOCKED_SHA256 = {
    "A": "b5e224cf2a558154a024c8b43e5211353abd5dead77455c541a4e84d20f53bf7",
    "B": "83bec909d39a8bfe22a1c35ee42072ac9d9cdfac7b4908d16c14d5876276d716",
    "C": "9cfa1a6323fcddac0a3d83df32ab351ebab03c12e84f0984f59d746a87628a68",
}

EXPECTED_PAGE_COUNTS = {"A": 10, "B": 24, "C": 20}
EXPECTED_LANDSCAPE_PAGES = {
    "A": (4, 6, 7, 8, 9),
    "B": (4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 22, 23, 24),
    "C": (4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19),
}
EXPECTED_CONTINUATION_PAGES = {
    "A": (8,),
    "B": (9, 11, 13, 14, 15, 17, 18, 20),
    "C": (5, 6, 7, 10, 14),
}
EXPECTED_BOOKMARKS = {
    "A": (
        "封面",
        "目录",
        "首页摘要",
        "竞争格局",
        "产品总览",
        "临床开发组合",
        "中国与全球监管",
        "企业与交易",
        "专利与保护",
        "疗效",
        "安全性",
        "疗效与安全性矩阵",
        "历史与边缘观察",
        "研究依据与局限",
    ),
    "B": (
        "封面",
        "目录",
        "首页摘要",
        "疗效",
        "纵向结果",
        "安全性",
        "疗效与安全性矩阵",
        "基线与人群总览",
        "人口学",
        "疾病语境",
        "基线疾病严重程度",
        "试验完成情况",
        "受试者流转",
        "失访与退出",
        "依从性",
        "筛败与原因",
        "补救治疗",
        "禁用药使用",
        "方案偏离",
        "试验与暴露语境",
        "亚组与支持证据",
        "产品与试验档案",
        "研究依据与局限",
    ),
    "C": (
        "封面",
        "目录",
        "首页摘要",
        "设计图谱",
        "人群与疾病定义",
        "入选标准",
        "排除标准",
        "分组、干预与对照",
        "终点、定义与时间点",
        "访视、疗程与随访",
        "样本量、分析集与统计设计",
        "逐试验详情",
        "NCT02260986 试验档案",
        "NCT04178967 试验档案",
        "NCT03985943 试验档案",
        "NCT05149313 试验档案",
        "设计模式、权衡与可选路径",
        "资料版本与局限",
    ),
}
EXPECTED_SEARCH_PHRASES = {
    "A": ("特应性皮炎", "竞争格局", "疗效与安全性矩阵", "研究依据与局限"),
    "B": ("特应性皮炎", "纵向结果", "试验完成情况", "受试者流转", "未公开"),
    "C": (
        "特应性皮炎",
        "设计图谱",
        "入选标准",
        "终点、定义与时间点",
        "NCT02260986",
        "设计模式、权衡与可选路径",
    ),
}

_A4_PORTRAIT = (595.27, 841.89)
_A4_LANDSCAPE = (841.89, 595.27)
_PT_TOLERANCE = 2.0
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_FORBIDDEN_TEXT_MARKERS = ("<html", "chromium", "playwright", "weasyprint", "wkhtmltopdf")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"JSON 对象应为字典：{path}"
    return payload


def _resolve_poppler_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    runtime_root = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
    for candidate in (
        runtime_root / "bin/override" / name,
        runtime_root / "native/poppler/poppler/bin" / name,
        runtime_root / "native/poppler/bin" / name,
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _pdftotext(path: Path, *, first: int | None = None, last: int | None = None) -> str:
    binary = _resolve_poppler_tool("pdftotext")
    if binary is None:
        pytest.fail("环境缺少 pdftotext；中文检索和逐页文本验收必须失败关闭")
    command = [binary]
    if first is not None:
        assert last is not None
        command.extend(["-f", str(first), "-l", str(last)])
    command.extend(["-layout", str(path), "-"])
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        pytest.fail(f"pdftotext 失败（{path}）：{completed.stderr.strip()}")
    return completed.stdout


def _page_texts(path: Path, page_count: int) -> tuple[str, ...]:
    text = _pdftotext(path)
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    assert len(pages) == page_count, (
        f"逐页文本页数不一致：{path}，PDF={page_count}，pdftotext={len(pages)}"
    )
    return tuple(pages)


def _outline_titles(reader: PdfReader) -> list[str]:
    titles: list[str] = []

    def walk(items: list[Any]) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
                continue
            title = getattr(item, "title", None)
            if title:
                titles.append(str(title))

    walk(list(reader.outline or []))
    return titles


def _matches_a4(size: tuple[float, float], expected: tuple[float, float]) -> bool:
    return (
        abs(size[0] - expected[0]) <= _PT_TOLERANCE
        and abs(size[1] - expected[1]) <= _PT_TOLERANCE
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload.startswith(_PNG_SIGNATURE), f"不是 PNG 原始页图：{path}"
    assert payload[12:16] == b"IHDR", f"PNG 缺少 IHDR：{path}"
    width, height = struct.unpack(">II", payload[16:24])
    assert width > 0 and height > 0, f"PNG 尺寸无效：{path}"
    return width, height


def _resolve_evidence_path(raw: str, *, root: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    for base in (ROOT, root):
        resolved = base / candidate
        if resolved.is_file():
            return resolved
    return root / candidate


def _numbered_files(directory: Path, suffix: str) -> dict[int, Path]:
    files: dict[int, Path] = {}
    pattern = re.compile(r"^page-(\d+)" + re.escape(suffix) + r"$")
    for path in directory.rglob(f"page-*{suffix}"):
        match = pattern.match(path.name)
        if match is None:
            continue
        page_number = int(match.group(1))
        assert page_number not in files, f"逐页证据存在重复页号：{path}"
        files[page_number] = path
    return files


def _verifier_output(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("pdf-verification")
    command = [
        sys.executable,
        str(VERIFIER),
        "--dpi",
        "120",
        "--output-dir",
        str(output_dir),
    ]
    for report, path in PDFS.items():
        command.extend(["--pdf", f"{report}={path}"])
    environment = os.environ.copy()
    current_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        str(ROOT)
        if not current_pythonpath
        else os.pathsep.join((str(ROOT), current_pythonpath))
    )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )
    assert completed.returncode == 0, (
        "最终 PDF verifier 必须无缺陷退出；"
        f"\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    summary_path = output_dir / "summary.json"
    assert summary_path.is_file(), "verifier 必须生成 summary.json"
    return output_dir


@pytest.fixture(scope="session")
def verification_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """在隔离临时目录中生成本次 PDF 的机器验收证据。"""

    return _verifier_output(tmp_path_factory)


def _summary_record(verification_dir: Path, report: str) -> dict[str, Any]:
    summary = _load_json(verification_dir / "summary.json")
    records = [item for item in summary.get("reports", []) if item.get("report") == report]
    assert len(records) == 1, f"summary 缺少唯一报告记录：{report}"
    record = records[0]
    assert summary.get("ok") is True, f"summary 存在验收缺陷：{report}"
    assert record.get("ok") is True, f"报告验收未通过：{report}"
    assert record.get("defect_count") == 0, f"报告仍有结构缺陷：{report}"
    return record


def test_final_pdfs_open_and_match_immutable_a10_b24_c20_hashes(
    verification_dir: Path,
) -> None:
    """三份最终交付 PDF 必须可由普通 PDF 解析器打开且摘要不可漂移。"""

    total_pages = 0
    for report, path in PDFS.items():
        assert path.is_file(), f"缺少最终 {report} PDF：{path}"
        reader = PdfReader(str(path))
        assert not reader.is_encrypted, f"最终 {report} PDF 不得要求密码打开"
        page_count = len(reader.pages)
        assert page_count == EXPECTED_PAGE_COUNTS[report]
        digest = _sha256(path)
        assert digest == LOCKED_SHA256[report]

        record = _summary_record(verification_dir, report)
        assert record["sha256"] == digest
        assert record["page_count"] == page_count
        assert Path(str(record["pdf"])).resolve() == path.resolve()
        total_pages += page_count

    assert total_pages == 54, "A10/B24/C20 必须合计验收 54 页"


def test_final_pdfs_have_selectable_searchable_chinese_text(
    verification_dir: Path,
) -> None:
    """pdftotext 必须从最终 PDF 读出关键中文，而非只得到栅格页面。"""

    for report, path in PDFS.items():
        reader = PdfReader(str(path))
        pages = _page_texts(path, EXPECTED_PAGE_COUNTS[report])
        full_text = "\n".join(pages)
        assert full_text.strip(), f"{report} PDF 不得整页栅格化"
        assert any("\u4e00" <= char <= "\u9fff" for char in full_text)
        for phrase in EXPECTED_SEARCH_PHRASES[report]:
            assert phrase in full_text, f"{report} PDF 中文检索缺少：{phrase}"
        lowered = full_text.lower()
        for marker in _FORBIDDEN_TEXT_MARKERS:
            assert marker not in lowered, f"{report} PDF 残留 HTML/Chromium 标记：{marker}"

        report_dir = verification_dir / report
        extracted = (report_dir / "pdftotext_full.txt").read_text(encoding="utf-8")
        assert extracted.strip() == _pdftotext(path).strip()
        assert len(reader.pages) == len(pages)


def test_final_pdfs_have_exact_chinese_bookmarks_and_page_headers_footers(
    verification_dir: Path,
) -> None:
    """书签顺序、每页标题和页码页脚必须覆盖整份报告。"""

    del verification_dir  # 证据生成由本测试模块 fixture 统一执行
    for report, path in PDFS.items():
        reader = PdfReader(str(path))
        assert _outline_titles(reader) == list(EXPECTED_BOOKMARKS[report])
        pages = _page_texts(path, EXPECTED_PAGE_COUNTS[report])
        footer_label = {
            "A": "特应性皮炎竞品全景",
            "B": "特应性皮炎临床试验结果比较",
            "C": "特应性皮炎临床试验设计比较",
        }[report]
        for page_number, page_text in enumerate(pages, start=1):
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            assert lines, f"{report} 第 {page_number} 页缺少可读页眉/正文"
            assert re.search(
                rf"{re.escape(footer_label)}\s+·\s+第\s+{page_number}\s+页",
                page_text,
            ), f"{report} 第 {page_number} 页缺少页码页脚"
            assert lines[0] != f"{footer_label} · 第 {page_number} 页"
            assert any("\u4e00" <= char <= "\u9fff" for char in lines[0])


def test_final_pdfs_are_a4_with_locked_orientation_sequences(
    verification_dir: Path,
) -> None:
    """所有物理页面必须是 A4，横向页序列必须与锁定交付一致。"""

    del verification_dir
    for report, path in PDFS.items():
        reader = PdfReader(str(path))
        landscape_pages: list[int] = []
        for page_number, page in enumerate(reader.pages, start=1):
            size = (float(page.mediabox.width), float(page.mediabox.height))
            assert _matches_a4(size, _A4_PORTRAIT) or _matches_a4(size, _A4_LANDSCAPE)
            if size[0] > size[1]:
                landscape_pages.append(page_number)
        assert tuple(landscape_pages) == EXPECTED_LANDSCAPE_PAGES[report]


def test_continuation_pages_repeat_explicit_table_context(
    verification_dir: Path,
) -> None:
    """每个续表页都必须重复续表标记、表头和披露语境。"""

    del verification_dir
    for report, path in PDFS.items():
        pages = _page_texts(path, EXPECTED_PAGE_COUNTS[report])
        continuation_pages = EXPECTED_CONTINUATION_PAGES[report]
        assert tuple(
            index for index, page_text in enumerate(pages, start=1) if "续表" in page_text
        ) == continuation_pages
        for page_number in continuation_pages:
            page_text = pages[page_number - 1]
            assert "续表" in page_text
            assert "产品" in page_text, f"{report} 第 {page_number} 页缺少重复表头"
            assert "披露" in page_text, f"{report} 第 {page_number} 页缺少披露语境"


def test_verifier_emits_current_page_text_raw_images_contact_sheet_and_structured_evidence(
    verification_dir: Path,
) -> None:
    """逐页文本、原始页图和 contact sheet 必须由本次 PDF 验证生成并绑定摘要。"""

    for report, path in PDFS.items():
        report_dir = verification_dir / report
        structure_path = report_dir / "structure_report.json"
        assert structure_path.is_file(), f"{report} 缺少结构化验收报告"
        structure = _load_json(structure_path)
        page_count = EXPECTED_PAGE_COUNTS[report]
        assert structure["report"] == report
        assert structure["sha256"] == LOCKED_SHA256[report]
        assert structure["page_count"] == page_count
        assert structure["ok"] is True
        assert structure["coverage"]["ok"] is True
        assert structure["coverage"]["missing_page_ids"] == []

        page_evidence = structure.get("page_evidence")
        assert isinstance(page_evidence, list), f"{report} 缺少逐页结构化证据"
        assert len(page_evidence) == page_count
        for page_number, evidence in enumerate(page_evidence, start=1):
            assert isinstance(evidence, dict)
            assert evidence.get("page") == page_number
            assert evidence.get("expected_page_number") == page_number
            assert evidence.get("page_number") == page_number
            assert evidence.get("page_number_ok") is True
            assert evidence.get("orientation") in {"portrait", "landscape"}
            header_footer = evidence.get("header_footer")
            assert isinstance(header_footer, dict)
            assert header_footer.get("present") is True
            assert header_footer.get("page_number") == page_number
            assert evidence.get("header_footer_ok") is True
            assert evidence.get("is_a4") is True
            assert evidence.get("source_pdf_sha256") == LOCKED_SHA256[report]
            assert isinstance(evidence.get("text"), dict)
            assert isinstance(evidence.get("render"), dict)
            assert evidence.get("raw_page_image") == evidence.get("render")
            assert evidence.get("binding_digest")

        text_files = _numbered_files(report_dir, ".txt")
        image_files = _numbered_files(report_dir, ".png")
        assert len(text_files) == page_count, f"{report} 逐页文本不完整"
        assert len(image_files) == page_count, f"{report} 原始页图不完整"
        assert set(text_files) == set(range(1, page_count + 1))
        assert set(image_files) == set(range(1, page_count + 1))

        pages = _page_texts(path, page_count)
        for page_number in range(1, page_count + 1):
            stored_text = text_files[page_number].read_text(encoding="utf-8")
            assert stored_text.strip() == pages[page_number - 1].strip()
            width, height = _png_dimensions(image_files[page_number])
            expected_size = (
                (1404, 993)
                if page_number in EXPECTED_LANDSCAPE_PAGES[report]
                else (993, 1404)
            )
            assert (width, height) == expected_size

        contact_sheet = structure.get("contact_sheet")
        assert isinstance(contact_sheet, dict), f"{report} 缺少 contact sheet 绑定"
        assert contact_sheet.get("page_count") == page_count
        assert contact_sheet.get("source_pdf_sha256") == LOCKED_SHA256[report]
        assert contact_sheet.get("binding_digest")
        contact_path = _resolve_evidence_path(
            str(contact_sheet["path"]),
            root=verification_dir,
        )
        assert contact_path.is_file()
        assert "contact" in contact_path.stem.lower()
        contact_width, contact_height = _png_dimensions(contact_path)
        assert contact_width > 0 and contact_height > 0
        assert contact_path.resolve().is_relative_to(report_dir.resolve())
        assert contact_sheet["sha256"] == _sha256(contact_path)
        assert contact_path.stat().st_mtime_ns >= max(
            image.stat().st_mtime_ns for image in image_files.values()
        )

        binding = structure.get("hash_binding")
        assert isinstance(binding, dict)
        assert binding["source_pdf"]["sha256"] == LOCKED_SHA256[report]
        assert binding["source_pdf"]["locked_sha256"] == LOCKED_SHA256[report]
        assert binding["page_count"] == page_count
        assert binding["contact_sheet_sha256"] == contact_sheet["sha256"]
        assert binding["digest"]
        assert len(binding["pages"]) == page_count
        assert structure["evidence"]["sha256"] == _sha256(
            _resolve_evidence_path(str(structure["evidence"]["path"]), root=verification_dir)
        )

        for evidence in page_evidence:
            text_evidence = evidence["text"]
            render_evidence = evidence["render"]
            text_path = _resolve_evidence_path(
                str(text_evidence["path"]),
                root=verification_dir,
            )
            render_path = _resolve_evidence_path(
                str(render_evidence["path"]),
                root=verification_dir,
            )
            assert text_path.is_file()
            assert render_path.is_file()
            assert text_path.resolve().is_relative_to(report_dir.resolve())
            assert render_path.resolve().is_relative_to(report_dir.resolve())
            assert text_evidence["page"] == evidence["page"]
            assert render_evidence["page"] == evidence["page"]
            assert text_evidence["sha256"] == _sha256(text_path)
            assert render_evidence["sha256"] == _sha256(render_path)
            assert text_evidence["bytes"] == text_path.stat().st_size
            assert render_evidence["bytes"] == render_path.stat().st_size
            assert render_evidence["source_pdf_sha256"] == LOCKED_SHA256[report]
            assert evidence["binding_digest"] == binding["digest"]
