#!/usr/bin/env python3
"""Task 8.3 PDF reader verifier: pypdf + pdftotext + pdftoppm + coverage projection.

Usage::

    uv run python tools/verify_pdf.py \\
        --artifacts .artifacts/pdf-complete \\
        --output-dir docs/acceptance/runs/8.3/verification

The verifier only reports defects and writes derived acceptance evidence. It
never rewrites PDF content, fixtures, or projection builders to force a green
result. Every evidence file is bound to the current locked PDF SHA-256.

Exit codes:
  0 = no defects
  1 = verification defects found
  2 = input / environment error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Never

from pypdf import PdfReader

from ci_workflow.renderers.pdf_native.coverage import (
    coverage_defects,
    load_expected_page_counts,
    project_pdf_coverage,
)

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

_A4_PORTRAIT = (595.27, 841.89)
_A4_LANDSCAPE = (841.89, 595.27)
_PT_TOLERANCE = 2.0

_FORBIDDEN_MARKERS = (
    "<html",
    "chromium",
    "playwright",
    "weasyprint",
    "wkhtmltopdf",
)

# Task 8.2 accepted these exact immutable PDF inputs.  Keeping the lock here
# makes a regenerated acceptance package fail closed when an input changes.
_LOCKED_PDFS: dict[str, dict[str, int | str]] = {
    "A": {
        "sha256": "b5e224cf2a558154a024c8b43e5211353abd5dead77455c541a4e84d20f53bf7",
        "page_count": 10,
    },
    "B": {
        "sha256": "83bec909d39a8bfe22a1c35ee42072ac9d9cdfac7b4908d16c14d5876276d716",
        "page_count": 24,
    },
    "C": {
        "sha256": "9cfa1a6323fcddac0a3d83df32ab351ebab03c12e84f0984f59d746a87628a68",
        "page_count": 20,
    },
}

_PAGE_NUMBER_RE = re.compile(r"第\s*(?P<number>\d+)\s*页")
_PAGE_FOOTER_RE = re.compile(r"(?P<title>[^\n·]{2,80})\s*·\s*第\s*(?P<number>\d+)\s*页")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")

_DEFAULT_PDFS = {
    "A": Path(".artifacts/pdf-complete/reports/A/v-fixture-001/report.pdf"),
    "B": Path(".artifacts/pdf-complete/reports/B/v-fixture-001/report.pdf"),
    "C": Path(".artifacts/pdf-complete/report-c.pdf"),
}


class ChineseArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self.add_argument("-h", "--help", action="help", help="显示帮助并退出")

    def error(self, message: str) -> Never:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}：参数错误：{message}\n")


def _resolve_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    # Codex runtime ships Poppler under native/ without every override shim.
    runtime_root = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
    candidates = [
        runtime_root / "bin/override" / name,
        runtime_root / "native/poppler/poppler/bin" / name,
        runtime_root / "native/poppler/bin" / name,
    ]
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _page_size(page: Any) -> tuple[float, float]:
    box = page.mediabox
    return (float(box.width), float(box.height))


def _is_a4(size: tuple[float, float]) -> bool:
    return (
        abs(size[0] - _A4_PORTRAIT[0]) <= _PT_TOLERANCE
        and abs(size[1] - _A4_PORTRAIT[1]) <= _PT_TOLERANCE
    ) or (
        abs(size[0] - _A4_LANDSCAPE[0]) <= _PT_TOLERANCE
        and abs(size[1] - _A4_LANDSCAPE[1]) <= _PT_TOLERANCE
    )


def _extract_text(path: Path, *, pdftotext_bin: str | None) -> tuple[str, str]:
    if pdftotext_bin:
        completed = subprocess.run(
            [pdftotext_bin, "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout, "pdftotext"
        raise RuntimeError(
            f"pdftotext failed for {path}: {completed.stderr.strip() or completed.returncode}"
        )
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text, "pypdf"


def _extract_page_texts(
    path: Path,
    *,
    page_count: int,
    reader: PdfReader,
    pdftotext_bin: str | None,
) -> tuple[list[str], str]:
    """Extract one text payload per page with the selected deterministic engine."""
    if pdftotext_bin:
        texts: list[str] = []
        for page_number in range(1, page_count + 1):
            completed = subprocess.run(
                [
                    pdftotext_bin,
                    "-layout",
                    "-f",
                    str(page_number),
                    "-l",
                    str(page_number),
                    str(path),
                    "-",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"pdftotext failed for {path} page {page_number}: "
                    f"{completed.stderr.strip() or completed.returncode}"
                )
            texts.append(completed.stdout.rstrip("\f"))
        return texts, "pdftotext"
    return [page.extract_text() or "" for page in reader.pages], "pypdf"


def _write_page_texts(
    page_texts: list[str],
    out_dir: Path,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence: list[dict[str, Any]] = []
    for page_number, text in enumerate(page_texts, start=1):
        path = out_dir / f"page-{page_number:02d}.txt"
        path.write_text(text, encoding="utf-8")
        evidence.append(
            {
                "page": page_number,
                "path": str(path),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return evidence


def _clear_generated_files(directory: Path, pattern: str) -> None:
    """Remove only files owned by this verifier, never the source PDF."""
    if not directory.is_dir():
        return
    for path in directory.glob(pattern):
        if path.is_file() or path.is_symlink():
            path.unlink()


def _png_rgb(path: Path) -> tuple[int, int, bytes]:
    """Decode the 8-bit PNG forms emitted by pdftoppm into RGB bytes."""
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"unsupported PNG signature: {path}")
    position = 8
    width = height = bit_depth = color_type = interlace = 0
    palette = b""
    alpha_palette = b""
    image_data = bytearray()
    while position < len(payload):
        if position + 12 > len(payload):
            raise ValueError(f"truncated PNG chunk: {path}")
        length = struct.unpack(">I", payload[position : position + 4])[0]
        chunk_type = payload[position + 4 : position + 8]
        chunk_start = position + 8
        chunk_end = chunk_start + length
        if chunk_end + 4 > len(payload):
            raise ValueError(f"truncated PNG payload: {path}")
        chunk = payload[chunk_start:chunk_end]
        position = chunk_end + 4
        if chunk_type == b"IHDR":
            if len(chunk) != 13:
                raise ValueError(f"invalid PNG IHDR: {path}")
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
        elif chunk_type == b"PLTE":
            palette = chunk
        elif chunk_type == b"tRNS":
            alpha_palette = chunk
        elif chunk_type == b"IDAT":
            image_data.extend(chunk)
        elif chunk_type == b"IEND":
            break
    if not width or not height or bit_depth != 8 or interlace != 0:
        raise ValueError(f"unsupported PNG format: {path}")
    channels_by_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channels_by_type.get(color_type)
    if channels is None:
        raise ValueError(f"unsupported PNG color type {color_type}: {path}")
    if color_type == 3 and not palette:
        raise ValueError(f"indexed PNG has no palette: {path}")
    decoded = zlib.decompress(bytes(image_data))
    row_size = width * channels
    expected_size = height * (row_size + 1)
    if len(decoded) != expected_size:
        raise ValueError(f"unexpected PNG data size for {path}")

    rows: list[bytes] = []
    previous = bytearray(row_size)
    offset = 0
    for _ in range(height):
        filter_type = decoded[offset]
        offset += 1
        filtered = decoded[offset : offset + row_size]
        offset += row_size
        row = bytearray(row_size)
        for index, value in enumerate(filtered):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                reconstructed = value
            elif filter_type == 1:
                reconstructed = (value + left) & 0xFF
            elif filter_type == 2:
                reconstructed = (value + up) & 0xFF
            elif filter_type == 3:
                reconstructed = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                predictor = left + up - upper_left
                distances = (
                    abs(predictor - left),
                    abs(predictor - up),
                    abs(predictor - upper_left),
                )
                reconstructed = (
                    value + (left, up, upper_left)[distances.index(min(distances))]
                ) & 0xFF
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}: {path}")
            row[index] = reconstructed
        rows.append(bytes(row))
        previous = row

    rgb = bytearray(width * height * 3)
    destination = 0
    for raw_row in rows:
        if color_type == 2:
            rgb[destination : destination + len(raw_row)] = raw_row
            destination += len(raw_row)
            continue
        for index in range(width):
            if color_type == 0:
                red = green = blue = raw_row[index]
                alpha = 255
            elif color_type == 3:
                palette_index = raw_row[index] * 3
                red, green, blue = palette[palette_index : palette_index + 3]
                alpha = (
                    alpha_palette[raw_row[index]]
                    if raw_row[index] < len(alpha_palette)
                    else 255
                )
            elif color_type == 4:
                red = green = blue = raw_row[index * 2]
                alpha = raw_row[index * 2 + 1]
            else:
                red, green, blue, alpha = raw_row[index * 4 : index * 4 + 4]
            rgb[destination : destination + 3] = bytes(
                (
                    (red * alpha + 255 * (255 - alpha)) // 255,
                    (green * alpha + 255 * (255 - alpha)) // 255,
                    (blue * alpha + 255 * (255 - alpha)) // 255,
                )
            )
            destination += 3
    return width, height, bytes(rgb)


def _resize_rgb(
    width: int,
    height: int,
    rgb: bytes,
    *,
    max_width: int,
    max_height: int,
) -> tuple[int, int, bytes]:
    scale = min(max_width / width, max_height / height)
    target_width = max(1, round(width * scale))
    target_height = max(1, round(height * scale))
    if target_width == width and target_height == height:
        return width, height, rgb
    resized = bytearray(target_width * target_height * 3)
    for y in range(target_height):
        source_y = min(height - 1, (y * height) // target_height)
        for x in range(target_width):
            source_x = min(width - 1, (x * width) // target_width)
            source = (source_y * width + source_x) * 3
            destination = (y * target_width + x) * 3
            resized[destination : destination + 3] = rgb[source : source + 3]
    return target_width, target_height, bytes(resized)


def _write_png_rgb(path: Path, width: int, height: int, rgb: bytes) -> None:
    if len(rgb) != width * height * 3:
        raise ValueError("RGB payload does not match PNG dimensions")
    raw = b"".join(b"\x00" + rgb[row * width * 3 : (row + 1) * width * 3] for row in range(height))

    def chunk(kind: bytes, value: bytes) -> bytes:
        return (
            struct.pack(">I", len(value))
            + kind
            + value
            + struct.pack(">I", zlib.crc32(kind + value) & 0xFFFFFFFF)
        )

    encoded = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(encoded)


_DIGIT_BITMAPS: dict[str, tuple[str, ...]] = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}


def _draw_page_label(
    canvas: bytearray,
    canvas_width: int,
    canvas_height: int,
    *,
    x: int,
    y: int,
    label: str,
) -> None:
    scale = 3
    padding = 4
    label_width = len(label) * (3 * scale + scale) - scale
    label_height = 5 * scale
    box_width = label_width + padding * 2
    box_height = label_height + padding * 2
    for row in range(max(0, y - padding), min(canvas_height, y + box_height)):
        start = max(0, x - padding)
        end = min(canvas_width, x + box_width)
        for column in range(start, end):
            offset = (row * canvas_width + column) * 3
            canvas[offset : offset + 3] = b"\xff\xff\xff"
    cursor_x = x
    for digit in label:
        bitmap = _DIGIT_BITMAPS[digit]
        for bitmap_y, bitmap_row in enumerate(bitmap):
            for bitmap_x, bit in enumerate(bitmap_row):
                if bit != "1":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        pixel_x = cursor_x + bitmap_x * scale + dx
                        pixel_y = y + bitmap_y * scale + dy
                        if 0 <= pixel_x < canvas_width and 0 <= pixel_y < canvas_height:
                            offset = (pixel_y * canvas_width + pixel_x) * 3
                            canvas[offset : offset + 3] = b"\x20\x20\x20"
        cursor_x += 4 * scale


def _build_contact_sheet(
    rendered: list[Path],
    output_path: Path,
) -> dict[str, Any]:
    """Build a dependency-free PNG overview from the current page renders."""
    if not rendered:
        raise ValueError("cannot build a contact sheet without rendered pages")
    tile_width, tile_height = 320, 420
    margin, gap = 16, 12
    columns = min(4, len(rendered))
    rows = (len(rendered) + columns - 1) // columns
    canvas_width = margin * 2 + columns * tile_width + (columns - 1) * gap
    canvas_height = margin * 2 + rows * tile_height + (rows - 1) * gap
    canvas = bytearray(b"\xff" * (canvas_width * canvas_height * 3))
    for page_number, path in enumerate(rendered, start=1):
        width, height, rgb = _png_rgb(path)
        image_width, image_height, resized = _resize_rgb(
            width,
            height,
            rgb,
            max_width=tile_width - 16,
            max_height=tile_height - 16,
        )
        column = (page_number - 1) % columns
        row = (page_number - 1) // columns
        tile_x = margin + column * (tile_width + gap)
        tile_y = margin + row * (tile_height + gap)
        image_x = tile_x + (tile_width - image_width) // 2
        image_y = tile_y + (tile_height - image_height) // 2
        for image_row in range(image_height):
            destination = ((image_y + image_row) * canvas_width + image_x) * 3
            source = image_row * image_width * 3
            canvas[destination : destination + image_width * 3] = resized[
                source : source + image_width * 3
            ]
        for border_x in range(tile_x, tile_x + tile_width):
            for border_y in (tile_y, tile_y + tile_height - 1):
                offset = (border_y * canvas_width + border_x) * 3
                canvas[offset : offset + 3] = b"\x88\x88\x88"
        for border_y in range(tile_y, tile_y + tile_height):
            for border_x in (tile_x, tile_x + tile_width - 1):
                offset = (border_y * canvas_width + border_x) * 3
                canvas[offset : offset + 3] = b"\x88\x88\x88"
        _draw_page_label(
            canvas,
            canvas_width,
            canvas_height,
            x=tile_x + 8,
            y=tile_y + 8,
            label=f"{page_number:02d}",
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_png_rgb(output_path, canvas_width, canvas_height, bytes(canvas))
    return {
        "path": str(output_path),
        "sha256": _sha256(output_path),
        "bytes": output_path.stat().st_size,
        "page_count": len(rendered),
        "columns": columns,
        "rows": rows,
        "tile_size": [tile_width, tile_height],
    }


def _page_status(
    *,
    page_number: int,
    text: str,
    size: tuple[float, float],
    text_evidence: dict[str, Any],
) -> dict[str, Any]:
    footer_matches = list(_PAGE_FOOTER_RE.finditer(text))
    page_markers = [int(match.group("number")) for match in _PAGE_NUMBER_RE.finditer(text)]
    footer = footer_matches[-1] if footer_matches else None
    marked_page = (
        int(footer.group("number")) if footer else (page_markers[-1] if page_markers else None)
    )
    orientation = "landscape" if size[0] > size[1] else "portrait"
    return {
        "page": page_number,
        "page_number": marked_page,
        "page_number_marker": marked_page,
        "expected_page_number": page_number,
        "page_number_ok": marked_page == page_number,
        "page_markers": page_markers,
        "header_footer": {
            "present": footer is not None,
            "text": footer.group(0).strip() if footer else None,
            "title": footer.group("title").strip() if footer else None,
            "page_number": marked_page,
        },
        "has_header_footer": footer is not None,
        "header_footer_ok": footer is not None and marked_page == page_number,
        "size_points": [size[0], size[1]],
        "is_a4": _is_a4(size),
        "orientation": orientation,
        "continued_table": "续表" in text,
        "is_continued_table": "续表" in text,
        "has_chinese_text": bool(_CJK_RE.search(text)),
        "text_chars": len(text),
        "text": text_evidence,
    }


def _render_pages(path: Path, out_dir: Path, *, pdftoppm_bin: str, dpi: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"
    completed = subprocess.run(
        [pdftoppm_bin, "-png", "-r", str(dpi), str(path), str(prefix)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"pdftoppm failed for {path}: {completed.stderr.strip() or completed.returncode}"
        )
    return sorted(out_dir.glob("page-*.png"))


@dataclass
class ReportInput:
    report: str
    path: Path


def _build_parser() -> ChineseArgumentParser:
    parser = ChineseArgumentParser(prog="verify_pdf.py", description=__doc__)
    parser.add_argument("--report", choices=("A", "B", "C"), action="append", dest="reports")
    parser.add_argument("--pdf", action="append", default=[], help="report=path 形式，可重复")
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path(".artifacts/pdf-complete"),
        help="默认 artifact 根目录",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/acceptance/runs/8.3/verification"),
        help="验证产物输出目录",
    )
    parser.add_argument("--dpi", type=int, default=120, help="pdftoppm 渲染 DPI")
    parser.add_argument(
        "--allow-missing-pdftotext",
        action="store_true",
        help="缺少 pdftotext 时回退 pypdf（默认失败关闭）",
    )
    return parser


def _resolve_inputs(args: argparse.Namespace) -> list[ReportInput]:
    mapping: dict[str, Path] = {}
    for item in args.pdf:
        if "=" not in item:
            raise ValueError(f"--pdf 必须是 report=path 形式：{item}")
        report, raw = item.split("=", 1)
        mapping[report.upper()] = Path(raw)
    artifacts = Path(args.artifacts)
    defaults = {
        "A": artifacts / "reports/A/v-fixture-001/report.pdf",
        "B": artifacts / "reports/B/v-fixture-001/report.pdf",
        "C": artifacts / "report-c.pdf",
    }
    selected = [r.upper() for r in (args.reports or ["A", "B", "C"])]
    inputs: list[ReportInput] = []
    for report in selected:
        path = mapping.get(report) or defaults.get(report)
        if path is None:
            raise ValueError(f"未配置报告 {report} 的 PDF 路径")
        if not path.is_file():
            raise FileNotFoundError(f"缺少 PDF：{path}")
        inputs.append(ReportInput(report=report, path=path))
    return inputs


def verify_one(
    item: ReportInput,
    *,
    output_dir: Path,
    dpi: int,
    pdftotext_bin: str | None,
    pdftoppm_bin: str | None,
    expected_counts: dict[str, int],
) -> dict[str, Any]:
    report_dir = output_dir / item.report
    page_text_dir = report_dir / "page-text"
    renders_dir = report_dir / "renders"
    contact_sheet_path = report_dir / "contact-sheet.png"
    evidence_path = report_dir / "evidence.json"
    report_dir.mkdir(parents=True, exist_ok=True)
    for generated_path in (
        report_dir / "pdftotext_full.txt",
        report_dir / "structure_report.json",
        report_dir / "defects.json",
        report_dir / "coverage_projection.json",
    ):
        generated_path.unlink(missing_ok=True)
    _clear_generated_files(page_text_dir, "page-*.txt")
    _clear_generated_files(renders_dir, "page-*.png")
    contact_sheet_path.unlink(missing_ok=True)
    evidence_path.unlink(missing_ok=True)

    reader = PdfReader(str(item.path))
    page_count = len(reader.pages)
    pdf_sha256 = _sha256(item.path)
    pdf_bytes = item.path.stat().st_size
    bookmarks = _outline_titles(reader)
    sizes = [_page_size(page) for page in reader.pages]
    text, text_engine = _extract_text(item.path, pdftotext_bin=pdftotext_bin)
    full_text_path = report_dir / "pdftotext_full.txt"
    full_text_path.write_text(text, encoding="utf-8")
    page_texts, page_text_engine = _extract_page_texts(
        item.path,
        page_count=page_count,
        reader=reader,
        pdftotext_bin=pdftotext_bin,
    )
    text_evidence = _write_page_texts(page_texts, page_text_dir)

    defects: list[dict[str, Any]] = []

    def add_defect(
        defect_id: str,
        *,
        severity: str,
        kind: str,
        message: str,
        page: int | None = None,
    ) -> None:
        defect: dict[str, Any] = {
            "id": defect_id,
            "severity": severity,
            "kind": kind,
            "message": message,
        }
        if page is not None:
            defect["page"] = page
        defects.append(defect)

    locked = _LOCKED_PDFS[item.report]
    locked_sha256 = str(locked["sha256"])
    locked_page_count = int(locked["page_count"])
    if pdf_sha256 != locked_sha256:
        add_defect(
            f"LOCK-{item.report}-SHA256",
            severity="high",
            kind="locked_pdf_hash_mismatch",
            message=(f"当前 PDF SHA-256 {pdf_sha256} 与 Task 8.2 锁定值 {locked_sha256} 不一致"),
        )
    if page_count != locked_page_count:
        add_defect(
            f"LOCK-{item.report}-PAGES",
            severity="high",
            kind="locked_pdf_page_count_mismatch",
            message=(f"当前 PDF 页数 {page_count} 与锁定值 {locked_page_count} 不一致"),
        )
    if page_count < 3:
        add_defect(
            f"STRUCT-{item.report}-PAGES",
            severity="high",
            kind="too_few_pages",
            message=f"page count {page_count} < 3",
        )
    if len(page_texts) != page_count:
        add_defect(
            f"STRUCT-{item.report}-TEXT-COUNT",
            severity="high",
            kind="page_text_count_mismatch",
            message=f"extracted {len(page_texts)} page texts for {page_count} pages",
        )
    for index, size in enumerate(sizes, start=1):
        if not _is_a4(size):
            add_defect(
                f"STRUCT-{item.report}-A4-{index}",
                severity="high",
                kind="non_a4_page",
                message=f"page {index} size {size} is not A4",
                page=index,
            )
    if not bookmarks:
        add_defect(
            f"STRUCT-{item.report}-BOOKMARKS",
            severity="high",
            kind="missing_bookmarks",
            message="PDF outline/bookmarks empty",
        )
    if "第" not in text or "页" not in text:
        add_defect(
            f"STRUCT-{item.report}-PAGENUM",
            severity="medium",
            kind="missing_page_numbers",
            message="searchable page-number footer markers not found",
        )
    lowered = text.lower()
    for marker in _FORBIDDEN_MARKERS:
        if marker in lowered:
            add_defect(
                f"STRUCT-{item.report}-PIPELINE",
                severity="high",
                kind="html_pipeline_marker",
                message=f"found forbidden marker `{marker}`",
            )

    page_evidence: list[dict[str, Any]] = []
    for index, size in enumerate(sizes, start=1):
        page_text = page_texts[index - 1] if index <= len(page_texts) else ""
        status = _page_status(
            page_number=index,
            text=page_text,
            size=size,
            text_evidence=text_evidence[index - 1]
            if index <= len(text_evidence)
            else {
                "page": index,
                "path": None,
                "sha256": None,
                "bytes": 0,
            },
        )
        if not status["page_number_ok"]:
            add_defect(
                f"STRUCT-{item.report}-PAGENUM-{index}",
                severity="high",
                kind="page_number_mismatch",
                message=(
                    f"page {index} marker is {status['page_number']!r}, "
                    "expected the physical page number"
                ),
                page=index,
            )
        if not status["header_footer_ok"]:
            add_defect(
                f"STRUCT-{item.report}-HEADER-FOOTER-{index}",
                severity="high",
                kind="missing_header_footer",
                message=f"page {index} has no matching Chinese header/footer marker",
                page=index,
            )
        status["source_pdf_sha256"] = pdf_sha256
        page_evidence.append(status)

    rendered: list[Path] = []
    if pdftoppm_bin is None:
        add_defect(
            f"ENV-{item.report}-PDFTOPPM",
            severity="high",
            kind="missing_tool",
            message="pdftoppm unavailable; cannot render pages for visual evidence",
        )
    else:
        try:
            rendered = _render_pages(
                item.path,
                renders_dir,
                pdftoppm_bin=pdftoppm_bin,
                dpi=dpi,
            )
        except (OSError, RuntimeError) as error:
            add_defect(
                f"ENV-{item.report}-PDFTOPPM-RUN",
                severity="high",
                kind="render_failed",
                message=str(error),
            )
        if len(rendered) != page_count:
            add_defect(
                f"STRUCT-{item.report}-RENDER-COUNT",
                severity="high",
                kind="render_count_mismatch",
                message=f"rendered {len(rendered)} pngs for {page_count} pages",
            )

    render_paths = [str(path) for path in rendered]
    render_evidence: list[dict[str, Any]] = []
    if len(rendered) == page_count:
        for index, path in enumerate(rendered, start=1):
            render_evidence.append(
                {
                    "page": index,
                    "path": str(path),
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                    "source_pdf_sha256": pdf_sha256,
                }
            )
        try:
            contact_sheet = _build_contact_sheet(rendered, contact_sheet_path)
            contact_sheet["source_pdf_sha256"] = pdf_sha256
        except (OSError, ValueError, zlib.error) as error:
            contact_sheet = None
            add_defect(
                f"ENV-{item.report}-CONTACT-SHEET",
                severity="high",
                kind="contact_sheet_failed",
                message=str(error),
            )
    else:
        contact_sheet = None
        contact_sheet_path.unlink(missing_ok=True)
    for index, status in enumerate(page_evidence):
        status["render"] = render_evidence[index] if index < len(render_evidence) else None
        status["raw_page_image"] = status["render"]
        text_meta = status["text"]
        status["text_path"] = text_meta["path"]
        status["text_sha256"] = text_meta["sha256"]
        status["text_bytes"] = text_meta["bytes"]
        if status["render"] is not None:
            render_meta = status["render"]
            status["render_path"] = render_meta["path"]
            status["render_sha256"] = render_meta["sha256"]
            status["image_path"] = render_meta["path"]
            status["image_sha256"] = render_meta["sha256"]
            status["image_bytes"] = render_meta["bytes"]
        else:
            status["render_path"] = None
            status["render_sha256"] = None
            status["image_path"] = None
            status["image_sha256"] = None
            status["image_bytes"] = 0
            add_defect(
                f"STRUCT-{item.report}-IMAGE-{index + 1}",
                severity="high",
                kind="missing_page_image",
                message=f"page {index + 1} has no current raw page image",
                page=index + 1,
            )

    projection = project_pdf_coverage(
        report=item.report,
        text=text,
        bookmark_titles=bookmarks,
        expected_counts=expected_counts,
    )
    defects.extend(coverage_defects(projection))

    source_evidence = {
        "path": str(item.path),
        "sha256": pdf_sha256,
        "bytes": pdf_bytes,
        "locked_sha256": locked_sha256,
        "locked_page_count": locked_page_count,
    }
    binding = {
        "source_pdf": source_evidence,
        "page_count": page_count,
        "full_text": {
            "path": str(full_text_path),
            "sha256": _sha256(full_text_path),
            "bytes": full_text_path.stat().st_size,
        },
        "pages": [
            {
                "page": status["page"],
                "text_path": status["text_path"],
                "text_sha256": status["text_sha256"],
                "render_path": status["render_path"],
                "render_sha256": status["render_sha256"],
                "page_number": status["page_number"],
                "page_number_ok": status["page_number_ok"],
                "header_footer_ok": status["header_footer_ok"],
                "orientation": status["orientation"],
                "is_a4": status["is_a4"],
                "continued_table": status["continued_table"],
            }
            for status in page_evidence
        ],
        "contact_sheet_sha256": (contact_sheet or {}).get("sha256"),
    }
    binding_digest = hashlib.sha256(
        json.dumps(
            binding,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    for status in page_evidence:
        status["binding_digest"] = binding_digest
    if contact_sheet is not None:
        contact_sheet["binding_digest"] = binding_digest
    binding["digest"] = binding_digest

    page_checks = {
        "all_page_numbers": all(status["page_number_ok"] for status in page_evidence),
        "all_header_footer": all(status["header_footer_ok"] for status in page_evidence),
        "all_a4": all(status["is_a4"] for status in page_evidence),
        "continued_table_pages": [
            status["page"] for status in page_evidence if status["continued_table"]
        ],
    }
    evidence = {
        "schema_version": "1.0",
        "report": item.report,
        "pdf": str(item.path),
        "pdf_sha256": pdf_sha256,
        "source_pdf_sha256": pdf_sha256,
        "expected_sha256": locked_sha256,
        "page_count": page_count,
        "expected_page_count": locked_page_count,
        "source_pdf": source_evidence,
        "binding": binding,
        "text_engine": text_engine,
        "page_text_engine": page_text_engine,
        "full_text": {
            "path": str(full_text_path),
            "sha256": _sha256(full_text_path),
            "bytes": full_text_path.stat().st_size,
        },
        "render": {
            "engine": "pdftoppm",
            "dpi": dpi,
            "pages": render_evidence,
        },
        "bookmarks": bookmarks,
        "pages": page_evidence,
        "page_checks": page_checks,
        "contact_sheet": contact_sheet,
        "coverage": projection.to_dict(),
        "defects": defects,
        "ok": not defects,
    }
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    evidence_file = {
        "path": str(evidence_path),
        "sha256": _sha256(evidence_path),
        "bytes": evidence_path.stat().st_size,
    }
    result = {
        "report": item.report,
        "pdf": str(item.path),
        "sha256": pdf_sha256,
        "pdf_sha256": pdf_sha256,
        "bytes": pdf_bytes,
        "source": source_evidence,
        "locked_input": {
            "sha256": locked_sha256,
            "page_count": locked_page_count,
            "hash_ok": pdf_sha256 == locked_sha256,
            "page_count_ok": page_count == locked_page_count,
        },
        "page_count": page_count,
        "bookmarks": bookmarks,
        "page_sizes": sizes,
        "text_engine": text_engine,
        "page_text_engine": page_text_engine,
        "page_checks": page_checks,
        "full_text": {
            "path": str(full_text_path),
            "sha256": _sha256(full_text_path),
            "bytes": full_text_path.stat().st_size,
        },
        "render_dpi": dpi,
        "render_engine": "pdftoppm",
        "coverage": projection.to_dict(),
        "renders": render_paths,
        "render_evidence": render_evidence,
        "raw_page_images": render_evidence,
        "page_evidence": page_evidence,
        "pages": page_evidence,
        "page_text_count": len(text_evidence),
        "raw_page_image_count": len(render_evidence),
        "page_texts": text_evidence,
        "contact_sheet": contact_sheet,
        "contact_sheet_path": (contact_sheet or {}).get("path"),
        "contact_sheet_sha256": (contact_sheet or {}).get("sha256"),
        "evidence": evidence_file,
        "hash_binding": binding,
        "defects": defects,
        "ok": not defects,
    }
    (report_dir / "structure_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (report_dir / "defects.json").write_text(
        json.dumps(defects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (report_dir / "coverage_projection.json").write_text(
        json.dumps(projection.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        inputs = _resolve_inputs(args)
    except (OSError, ValueError) as error:
        print(f"verify_pdf.py：输入错误：{error}", file=sys.stderr)
        return EXIT_USAGE

    pdftotext_bin = _resolve_tool("pdftotext")
    pdftoppm_bin = _resolve_tool("pdftoppm")
    if pdftotext_bin is None and not args.allow_missing_pdftotext:
        print(
            "verify_pdf.py：环境错误：缺少 pdftotext。"
            "最小修复：确保 Poppler pdftotext 在 PATH，或使用已有 runtime "
            "`~/.cache/codex-runtimes/.../native/poppler/poppler/bin/pdftotext`；"
            "临时排查可加 --allow-missing-pdftotext。",
            file=sys.stderr,
        )
        return EXIT_USAGE

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_counts = load_expected_page_counts()

    reports: list[dict[str, Any]] = []
    all_defects: list[dict[str, Any]] = []
    for item in inputs:
        result = verify_one(
            item,
            output_dir=output_dir,
            dpi=args.dpi,
            pdftotext_bin=pdftotext_bin,
            pdftoppm_bin=pdftoppm_bin,
            expected_counts=expected_counts,
        )
        reports.append(result)
        all_defects.extend({**defect, "report": item.report} for defect in result["defects"])

    summary = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "tools": {
            "pdftotext": pdftotext_bin,
            "pdftoppm": pdftoppm_bin,
            "pypdf": True,
        },
        "hash_lock": "task-8.2-final-pdfs",
        "total_pages": sum(int(item["page_count"]) for item in reports),
        "expected_total_pages": sum(
            int(_LOCKED_PDFS[item["report"]]["page_count"]) for item in reports
        ),
        "reports": [
            {
                "report": item["report"],
                "pdf": item["pdf"],
                "sha256": item["sha256"],
                "pdf_sha256": item["pdf_sha256"],
                "locked_sha256": item["locked_input"]["sha256"],
                "hash_ok": item["locked_input"]["hash_ok"],
                "page_count": item["page_count"],
                "expected_page_count": item["locked_input"]["page_count"],
                "page_count_ok": item["locked_input"]["page_count_ok"],
                "bookmark_count": len(item["bookmarks"]),
                "coverage_ok": item["coverage"]["ok"],
                "missing_page_ids": item["coverage"]["missing_page_ids"],
                "page_checks": item["page_checks"],
                "page_evidence_count": len(item["page_evidence"]),
                "page_text_count": len(item["page_texts"]),
                "render_count": len(item["render_evidence"]),
                "render_dpi": item["render_dpi"],
                "contact_sheet": item["contact_sheet"],
                "contact_sheet_path": item["contact_sheet_path"],
                "contact_sheet_sha256": item["contact_sheet_sha256"],
                "evidence": item["evidence"],
                "binding_digest": item["hash_binding"]["digest"],
                "defect_count": len(item["defects"]),
                "ok": item["ok"],
            }
            for item in reports
        ],
        "defects": all_defects,
        "ok": not all_defects,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "defects.json").write_text(
        json.dumps(all_defects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return EXIT_OK if not all_defects else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
