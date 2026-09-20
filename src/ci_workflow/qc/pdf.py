"""Task 8.3 read-only native-PDF acceptance contracts.

The verifier owns extraction and rendering.  This module owns the immutable
shape and the fail-closed checks over the evidence it produces.  It never
opens a write handle and never changes a PDF, an image, or an evidence file.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import ReportKind

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_A4_PORTRAIT = (595.27, 841.89)
_A4_LANDSCAPE = (841.89, 595.27)
_PT_TOLERANCE = 2.0

# Task 8.2's accepted files.  These values are defaults, not a mechanism for
# discovering or replacing an artifact: a caller may provide a different
# explicit expected digest when validating an isolated fixture.
LOCKED_PDF_SHA256: dict[str, str] = {
    "A": "b5e224cf2a558154a024c8b43e5211353abd5dead77455c541a4e84d20f53bf7",
    "B": "83bec909d39a8bfe22a1c35ee42072ac9d9cdfac7b4908d16c14d5876276d716",
    "C": "9cfa1a6323fcddac0a3d83df32ab351ebab03c12e84f0984f59d746a87628a68",
}
LOCKED_PDF_PAGE_COUNTS: dict[str, int] = {"A": 10, "B": 24, "C": 20}


class PdfAcceptanceError(ValueError):
    """PDF 验收输入或绑定证据不完整；失败关闭且不产生写入。"""


class PdfOrientation(StrEnum):
    """Native PDF page orientation."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PdfAcceptanceViolationCode(StrEnum):
    """Machine-readable fail-closed PDF acceptance violation."""

    REPORT_MISMATCH = "report_mismatch"
    PDF_MISSING = "pdf_missing"
    PDF_HASH_MISMATCH = "pdf_hash_mismatch"
    EXPECTED_HASH_DRIFT = "expected_hash_drift"
    PAGE_COUNT_MISMATCH = "page_count_mismatch"
    PAGE_SEQUENCE_MISMATCH = "page_sequence_mismatch"
    PAGE_TEXT_MISSING = "page_text_missing"
    PAGE_TEXT_MISSING_FILE = "page_text_missing_file"
    PAGE_TEXT_HASH_MISMATCH = "page_text_hash_mismatch"
    ORIENTATION_MISMATCH = "orientation_mismatch"
    NON_A4_PAGE = "non_a4_page"
    HEADER_MISSING = "header_missing"
    FOOTER_MISSING = "footer_missing"
    PAGE_NUMBER_MISSING = "page_number_missing"
    PAGE_NUMBER_MISMATCH = "page_number_mismatch"
    CONTINUATION_MISSING = "continuation_missing"
    CONTINUATION_MARKER_MISSING = "continuation_marker_missing"
    PAGE_IMAGE_MISSING = "page_image_missing"
    PAGE_IMAGE_MISSING_FILE = "page_image_missing_file"
    PAGE_IMAGE_HASH_MISMATCH = "page_image_hash_mismatch"
    CONTACT_SHEET_MISSING = "contact_sheet_missing"
    CONTACT_SHEET_MISSING_FILE = "contact_sheet_missing_file"
    CONTACT_SHEET_HASH_MISMATCH = "contact_sheet_hash_mismatch"
    COVERAGE_MISSING = "coverage_missing"
    COVERAGE_FAILED = "coverage_failed"
    REPORTED_DEFECT = "reported_defect"
    RENDER_COUNT_MISMATCH = "render_count_mismatch"


def _not_blank(value: str, *, label: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label}不能为空")
    return normalized


def _optional_text(value: str | None, *, label: str) -> str | None:
    if value is None:
        return None
    return _not_blank(value, label=label)


def _digest(value: str, *, label: str) -> str:
    normalized = _not_blank(value, label=label)
    if _SHA256_RE.fullmatch(normalized) is None:
        raise ValueError(f"{label}必须是小写 SHA-256（64 位十六进制）")
    return normalized


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalise_orientation(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip().casefold()
    return {
        "portrait": PdfOrientation.PORTRAIT,
        "vertical": PdfOrientation.PORTRAIT,
        "纵向": PdfOrientation.PORTRAIT,
        "a4-portrait": PdfOrientation.PORTRAIT,
        "landscape": PdfOrientation.LANDSCAPE,
        "horizontal": PdfOrientation.LANDSCAPE,
        "横向": PdfOrientation.LANDSCAPE,
        "a4-landscape": PdfOrientation.LANDSCAPE,
    }.get(normalized, value)


def _normalise_page_size(value: object) -> object:
    if isinstance(value, Mapping):
        raw = dict(value)
        if "width_pt" not in raw and "width" in raw:
            raw["width_pt"] = raw.pop("width")
        if "height_pt" not in raw and "height" in raw:
            raw["height_pt"] = raw.pop("height")
        return raw
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values = list(value)
        if len(values) == 2:
            return {"width_pt": values[0], "height_pt": values[1]}
    return value


def _normalise_image(value: object) -> object:
    if isinstance(value, PdfImageEvidence):
        return value
    if not isinstance(value, Mapping):
        return value
    raw = dict(value)
    for source, target in (
        ("image_path", "path"),
        ("original_image_path", "path"),
        ("render_path", "path"),
        ("image_sha256", "sha256"),
        ("original_image_sha256", "sha256"),
        ("render_sha256", "sha256"),
    ):
        if target not in raw and source in raw:
            raw[target] = raw[source]
        raw.pop(source, None)
    if "byte_size" not in raw and "bytes" in raw:
        raw["byte_size"] = raw.pop("bytes")
    return raw


class PdfPageSize(BaseModel):
    """One page's media-box dimensions in points."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width_pt: float
    height_pt: float

    @model_validator(mode="before")
    @classmethod
    def _normalise_shape(cls, value: Any) -> Any:
        return _normalise_page_size(value)

    @model_validator(mode="after")
    def _finite_positive(self) -> Self:
        if not math.isfinite(self.width_pt) or not math.isfinite(self.height_pt):
            raise ValueError("页面尺寸必须是有限数")
        if self.width_pt <= 0 or self.height_pt <= 0:
            raise ValueError("页面尺寸必须为正数")
        return self

    @property
    def orientation(self) -> PdfOrientation:
        if self.width_pt > self.height_pt:
            return PdfOrientation.LANDSCAPE
        return PdfOrientation.PORTRAIT

    @property
    def is_a4(self) -> bool:
        return (
            abs(self.width_pt - _A4_PORTRAIT[0]) <= _PT_TOLERANCE
            and abs(self.height_pt - _A4_PORTRAIT[1]) <= _PT_TOLERANCE
        ) or (
            abs(self.width_pt - _A4_LANDSCAPE[0]) <= _PT_TOLERANCE
            and abs(self.height_pt - _A4_LANDSCAPE[1]) <= _PT_TOLERANCE
        )


class PdfImageEvidence(BaseModel):
    """One current original page image or contact-sheet file binding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    byte_size: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def _normalise_shape(cls, value: Any) -> Any:
        return _normalise_image(value)

    @field_validator("path")
    @classmethod
    def _path_not_blank(cls, value: str) -> str:
        return _not_blank(value, label="图像证据路径")

    @field_validator("sha256")
    @classmethod
    def _sha256_valid(cls, value: str) -> str:
        return _digest(value, label="图像证据摘要")


class PdfPageEvidence(BaseModel):
    """Immutable evidence for one PDF page.

    ``text`` may be carried inline or by ``text_path``.  Presence flags are
    deliberately explicit: a missing observation is not silently treated as a
    passed header, footer, page number, or continuation check.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_number: int = Field(ge=1)
    text: str = ""
    text_path: str | None = None
    text_sha256: str | None = None
    orientation: PdfOrientation
    page_size: PdfPageSize | None = None
    header: str | None = None
    footer: str | None = None
    page_number_text: str | None = None
    header_present: bool | None = None
    footer_present: bool | None = None
    page_number_present: bool | None = None
    continuation: bool | None = None
    continuation_marker: str | None = None
    image: PdfImageEvidence | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalise_shape(cls, value: Any) -> Any:
        if isinstance(value, PdfPageEvidence) or not isinstance(value, Mapping):
            return value
        raw = dict(value)

        aliases = (
            ("page", "page_number"),
            ("index", "page_number"),
            ("page_text", "text"),
            ("text_file", "text_path"),
            ("text_file_path", "text_path"),
            ("header_text", "header"),
            ("footer_text", "footer"),
            ("page_label", "page_number_text"),
            ("page_number_label", "page_number_text"),
            ("has_header", "header_present"),
            ("has_footer", "footer_present"),
            ("has_page_number", "page_number_present"),
            ("page_number_found", "page_number_present"),
            ("is_continuation", "continuation"),
            ("continuation_page", "continuation"),
            ("continuation_text", "continuation_marker"),
            ("size", "page_size"),
        )
        for source, target in aliases:
            if target not in raw and source in raw:
                raw[target] = raw[source]
            raw.pop(source, None)

        if "header_footer_present" in raw:
            present = raw.pop("header_footer_present")
            raw.setdefault("header_present", present)
            raw.setdefault("footer_present", present)
        if "header" in raw and isinstance(raw["header"], bool):
            raw.setdefault("header_present", raw.pop("header"))
        if "footer" in raw and isinstance(raw["footer"], bool):
            raw.setdefault("footer_present", raw.pop("footer"))
        if "page_number_text" in raw and isinstance(raw["page_number_text"], bool):
            raw.setdefault("page_number_present", raw.pop("page_number_text"))

        if "page_size" in raw:
            raw["page_size"] = _normalise_page_size(raw["page_size"])
        elif "width_pt" in raw or "height_pt" in raw:
            raw["page_size"] = {
                "width_pt": raw.pop("width_pt", None),
                "height_pt": raw.pop("height_pt", None),
            }

        image_value = raw.pop("image", None)
        if image_value is None:
            for key in ("original_image", "page_image", "render", "render_evidence"):
                if key in raw:
                    image_value = raw.pop(key)
                    break
        image_path = None
        image_sha256 = None
        for key in ("image_path", "original_image_path", "render_path"):
            if key in raw:
                image_path = raw.pop(key)
                break
        for key in ("image_sha256", "original_image_sha256", "render_sha256"):
            if key in raw:
                image_sha256 = raw.pop(key)
                break
        if image_value is not None:
            image_value = _normalise_image(image_value)
        elif image_path is not None or image_sha256 is not None:
            image_value = {"path": image_path, "sha256": image_sha256}
        if image_value is not None:
            raw["image"] = image_value

        # Some extractors use the visible footer label as ``page_number`` and
        # carry the ordinal under ``page``/``index``.  Preserve both facts.
        raw_page_number = raw.get("page_number")
        if isinstance(raw_page_number, str):
            match = re.search(r"(?<!\d)(\d+)(?!\d)", raw_page_number)
            ordinal = raw.get("page") or raw.get("index")
            if ordinal is not None:
                raw["page_number_text"] = raw_page_number
                raw["page_number"] = ordinal
            elif match:
                raw["page_number_text"] = raw_page_number
                raw["page_number"] = int(match.group(1))

        return raw

    @field_validator("text")
    @classmethod
    def _text_is_string(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("逐页文本必须是字符串")
        return value

    @field_validator("text_path")
    @classmethod
    def _text_path_valid(cls, value: str | None) -> str | None:
        return _optional_text(value, label="逐页文本路径")

    @field_validator("text_sha256")
    @classmethod
    def _text_sha_valid(cls, value: str | None) -> str | None:
        return None if value is None else _digest(value, label="逐页文本摘要")

    @field_validator("orientation", mode="before")
    @classmethod
    def _orientation_valid(cls, value: object) -> object:
        return _normalise_orientation(value)

    @field_validator("header", "footer", "page_number_text", "continuation_marker")
    @classmethod
    def _labels_valid(cls, value: str | None, info: Any) -> str | None:
        return _optional_text(value, label=str(info.field_name))

    @model_validator(mode="after")
    def _text_binding_is_present(self) -> Self:
        if not self.text.strip() and self.text_path is None:
            raise ValueError("逐页证据必须包含文本或逐页文本路径")
        if self.text_sha256 is not None and self.text:
            actual = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
            if actual != self.text_sha256:
                raise ValueError("逐页文本摘要与内嵌文本不一致")
        # Text labels are sufficient evidence for the corresponding presence
        # flags when a producer does not duplicate the same fact as a boolean.
        if self.header_present is None and self.header is not None:
            object.__setattr__(self, "header_present", True)
        if self.footer_present is None and self.footer is not None:
            object.__setattr__(self, "footer_present", True)
        if self.page_number_present is None and self.page_number_text is not None:
            object.__setattr__(self, "page_number_present", True)
        return self

    @property
    def image_path(self) -> str | None:
        return None if self.image is None else self.image.path

    @property
    def image_sha256(self) -> str | None:
        return None if self.image is None else self.image.sha256

    @property
    def header_text(self) -> str | None:
        return self.header

    @property
    def footer_text(self) -> str | None:
        return self.footer

    @property
    def is_continuation(self) -> bool | None:
        return self.continuation


class PdfContactSheetEvidence(PdfImageEvidence):
    """Current contact-sheet image binding for one report."""


class PdfAcceptanceEvidence(BaseModel):
    """Immutable report-level PDF evidence consumed by the verifier."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    report: ReportKind
    pdf: str
    sha256: str
    page_count: int = Field(ge=1)
    pages: tuple[PdfPageEvidence, ...] = Field(min_length=1)
    contact_sheet: PdfContactSheetEvidence | None = None
    contact_sheets: tuple[PdfContactSheetEvidence, ...] = ()
    expected_sha256: str | None = None
    expected_page_count: int | None = Field(default=None, ge=1)
    bookmarks: tuple[str, ...] = ()
    page_sizes: tuple[PdfPageSize, ...] = ()
    renders: tuple[str, ...] = ()
    coverage: dict[str, Any] | None = None
    coverage_ok: bool | None = None
    defects: tuple[dict[str, Any], ...] = ()
    text_engine: str | None = None
    byte_size: int | None = Field(default=None, ge=1, validation_alias="bytes")
    reported_ok: bool | None = Field(default=None, validation_alias="ok")

    @model_validator(mode="before")
    @classmethod
    def _normalise_shape(cls, value: Any) -> Any:
        if isinstance(value, PdfAcceptanceEvidence) or not isinstance(value, Mapping):
            return value
        raw = dict(value)

        for source, target in (
            ("report_kind", "report"),
            ("pdf_path", "pdf"),
            ("artifact_path", "pdf"),
            ("pdf_sha256", "sha256"),
            ("artifact_sha256", "sha256"),
            ("final_sha256", "sha256"),
            ("page_evidence", "pages"),
            ("page_observations", "pages"),
            ("per_page", "pages"),
            ("render_paths", "renders"),
            ("original_page_images", "renders"),
        ):
            if target not in raw and source in raw:
                raw[target] = raw[source]
            raw.pop(source, None)

        if "page_sizes" in raw:
            raw["page_sizes"] = tuple(_normalise_page_size(item) for item in raw["page_sizes"])
        if "renders" in raw and isinstance(raw["renders"], Sequence) and not isinstance(
            raw["renders"], (str, bytes, bytearray)
        ):
            renders = []
            for item in raw["renders"]:
                if isinstance(item, Mapping):
                    renders.append(str(item.get("path") or item.get("image_path") or ""))
                else:
                    renders.append(item)
            raw["renders"] = tuple(renders)

        if "pages" not in raw:
            raw_pages = raw.get("page_texts")
            if isinstance(raw_pages, Sequence) and not isinstance(
                raw_pages, (str, bytes, bytearray)
            ):
                raw["pages"] = [
                    {"page_number": index, "text": text}
                    for index, text in enumerate(raw_pages, start=1)
                ]

        image_paths = raw.pop("original_page_image_paths", None)
        image_hashes = raw.pop("original_page_image_sha256", None)
        if isinstance(raw.get("pages"), Sequence) and not isinstance(
            raw["pages"], (str, bytes, bytearray)
        ) and (image_paths is not None or image_hashes is not None):
            page_values = list(raw["pages"])
            image_paths = list(image_paths or ())
            image_hashes = list(image_hashes or ())
            for index, page in enumerate(page_values):
                if not isinstance(page, Mapping) or "image" in page:
                    continue
                page_copy = dict(page)
                if index < len(image_paths):
                    page_copy["image_path"] = image_paths[index]
                if index < len(image_hashes):
                    page_copy["image_sha256"] = image_hashes[index]
                page_values[index] = page_copy
            raw["pages"] = page_values

        if "contact_sheet" in raw and isinstance(raw["contact_sheet"], Sequence) and not isinstance(
            raw["contact_sheet"], (str, bytes, bytearray, Mapping)
        ):
            raw["contact_sheets"] = raw.pop("contact_sheet")
        if "contact_sheet" not in raw:
            contact_path = raw.pop("contact_sheet_path", None)
            contact_sha = raw.pop("contact_sheet_sha256", None)
            if contact_path is not None or contact_sha is not None:
                raw["contact_sheet"] = {"path": contact_path, "sha256": contact_sha}

        if "coverage_ok" not in raw and isinstance(raw.get("coverage"), Mapping):
            coverage_ok = raw["coverage"].get("ok")
            if isinstance(coverage_ok, bool):
                raw["coverage_ok"] = coverage_ok

        return raw

    @field_validator("pdf")
    @classmethod
    def _pdf_path_valid(cls, value: str) -> str:
        normalized = _not_blank(value, label="PDF 路径")
        if Path(normalized).suffix.casefold() != ".pdf":
            raise ValueError("PDF 产物路径必须以 .pdf 结尾")
        return normalized

    @field_validator("sha256", "expected_sha256")
    @classmethod
    def _sha256_valid(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _digest(value, label=str(info.field_name))

    @field_validator("bookmarks", "renders")
    @classmethod
    def _list_text_valid(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value, label=str(info.field_name)) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError(f"{info.field_name}不得重复")
        return normalized

    @field_validator("text_engine")
    @classmethod
    def _engine_valid(cls, value: str | None) -> str | None:
        return _optional_text(value, label="文本抽取引擎")

    @model_validator(mode="after")
    def _report_contract_is_sane(self) -> Self:
        page_numbers = tuple(page.page_number for page in self.pages)
        if len(set(page_numbers)) != len(page_numbers):
            raise ValueError("逐页证据页码不得重复")
        if self.page_sizes and len(self.page_sizes) != self.page_count:
            raise ValueError("全局页面尺寸证据必须覆盖每一页")
        if self.contact_sheet is not None and self.contact_sheets:
            raise ValueError("contact_sheet 与 contact_sheets 不得同时提供")
        if len(self.contact_sheets) > 1:
            paths = [item.path for item in self.contact_sheets]
            if len(set(paths)) != len(paths):
                raise ValueError("contact sheet 路径不得重复")
        return self

    @property
    def report_value(self) -> str:
        return self.report.value

    @property
    def pdf_path(self) -> str:
        return self.pdf

    @property
    def final_sha256(self) -> str:
        return self.sha256

    @property
    def artifact_sha256(self) -> str:
        return self.sha256

    @property
    def page_evidence(self) -> tuple[PdfPageEvidence, ...]:
        return self.pages

    @property
    def accepted_contact_sheets(self) -> tuple[PdfContactSheetEvidence, ...]:
        if self.contact_sheet is not None:
            return (self.contact_sheet,)
        return self.contact_sheets


class PdfAcceptanceViolation(BaseModel):
    """One reportable PDF acceptance violation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PdfAcceptanceViolationCode
    message_zh: str
    page_number: int | None = Field(default=None, ge=1)

    @field_validator("message_zh")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        return _not_blank(value, label="验收问题")


class PdfAcceptanceResult(BaseModel):
    """Read-only acceptance outcome; ``ok`` is false for any missing proof."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence: PdfAcceptanceEvidence
    expected_sha256: str
    expected_page_count: int = Field(ge=1)
    actual_sha256: str | None = None
    violations: tuple[PdfAcceptanceViolation, ...] = ()
    ok: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def report(self) -> ReportKind:
        return self.evidence.report

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pdf(self) -> str:
        return self.evidence.pdf

    @computed_field  # type: ignore[prop-decorator]
    @property
    def page_count(self) -> int:
        return self.evidence.page_count

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sha256(self) -> str:
        return self.evidence.sha256

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> tuple[PdfPageEvidence, ...]:
        return self.evidence.pages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def accepted(self) -> bool:
        return self.ok

    @computed_field  # type: ignore[prop-decorator]
    @property
    def message_zh(self) -> str:
        if self.ok:
            return (
                f"{self.evidence.report.value} 类 PDF 只读验收通过："
                f"已绑定最终摘要、{self.evidence.page_count} 页逐页文本、方向、"
                "页眉页脚、页码、续表与当前原图证据。"
            )
        listed = "；".join(item.message_zh for item in self.violations[:5])
        if len(self.violations) > 5:
            listed = f"{listed} 等 {len(self.violations)} 项"
        return f"{self.evidence.report.value} 类 PDF 只读验收失败：{listed}"


def _resolved_path(raw: str, project_root: Path | None) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute() and project_root is not None:
        path = project_root / path
    return path


def _violation(
    code: PdfAcceptanceViolationCode,
    message: str,
    *,
    page_number: int | None = None,
) -> PdfAcceptanceViolation:
    return PdfAcceptanceViolation(code=code, message_zh=message, page_number=page_number)


def _read_page_text(
    page: PdfPageEvidence,
    *,
    project_root: Path | None,
    verify_files: bool,
    violations: list[PdfAcceptanceViolation],
) -> str:
    text = page.text
    if page.text_path is None:
        return text
    path = _resolved_path(page.text_path, project_root)
    if not verify_files:
        return text
    if not path.is_file():
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.PAGE_TEXT_MISSING_FILE,
                f"第 {page.page_number} 页逐页文本文件不存在：{page.text_path}",
                page_number=page.page_number,
            )
        )
        return text
    try:
        current = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.PAGE_TEXT_MISSING_FILE,
                f"第 {page.page_number} 页逐页文本无法读取：{page.text_path}（{error}）",
                page_number=page.page_number,
            )
        )
        return text
    if text and current != text:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.PAGE_TEXT_HASH_MISMATCH,
                f"第 {page.page_number} 页内嵌文本与当前逐页文本文件不一致",
                page_number=page.page_number,
            )
        )
    text = current
    if page.text_sha256 is not None:
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual != page.text_sha256:
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.PAGE_TEXT_HASH_MISMATCH,
                    f"第 {page.page_number} 页逐页文本摘要与当前文件不一致",
                    page_number=page.page_number,
                )
            )
    return text


def _check_image_file(
    image: PdfImageEvidence | None,
    *,
    label: str,
    page_number: int | None,
    project_root: Path | None,
    verify_files: bool,
    missing_code: PdfAcceptanceViolationCode,
    hash_code: PdfAcceptanceViolationCode,
    violations: list[PdfAcceptanceViolation],
) -> None:
    if image is None:
        violations.append(
            _violation(
                missing_code,
                f"{label}缺少当前原图路径与摘要证据",
                page_number=page_number,
            )
        )
        return
    if not verify_files:
        return
    path = _resolved_path(image.path, project_root)
    if not path.is_file():
        violations.append(
            _violation(
                missing_code,
                f"{label}文件不存在：{image.path}",
                page_number=page_number,
            )
        )
        return
    try:
        actual = _file_sha256(path)
    except OSError as error:
        violations.append(
            _violation(
                missing_code,
                f"{label}文件无法读取：{image.path}（{error}）",
                page_number=page_number,
            )
        )
        return
    if actual != image.sha256:
        violations.append(
            _violation(
                hash_code,
                f"{label}摘要与当前文件不一致：{image.path}",
                page_number=page_number,
            )
        )


def verify_pdf_acceptance(
    evidence: PdfAcceptanceEvidence | Mapping[str, Any],
    *,
    expected_report: ReportKind | str | None = None,
    expected_sha256: str | None = None,
    expected_page_count: int | None = None,
    project_root: Path | str | None = None,
    verify_files: bool = True,
    require_contact_sheet: bool = True,
    require_coverage: bool = True,
    require_continuation: bool = True,
) -> PdfAcceptanceResult:
    """Verify immutable PDF evidence without modifying any input.

    The default expectation is the locked Task 8.2 A10/B24/C20 set.  A custom
    expected digest/count is allowed only when explicitly supplied by a caller;
    omitting either falls back to the locked report contract.  ``verify_files``
    additionally re-hashes the PDF, text files, page images, and contact sheet
    from their current paths, so evidence from an earlier render cannot pass.
    """
    try:
        parsed = (
            evidence
            if isinstance(evidence, PdfAcceptanceEvidence)
            else PdfAcceptanceEvidence.model_validate(evidence)
        )
    except ValidationError as error:
        raise PdfAcceptanceError(f"PDF 验收证据结构无效，失败关闭：{error}") from error

    report_value = parsed.report.value
    expected_report_value: str | None = None
    if expected_report is not None:
        try:
            expected_report_value = ReportKind(expected_report).value
        except ValueError as error:
            raise PdfAcceptanceError(f"未知报告类型，失败关闭：{expected_report}") from error

    default_sha = LOCKED_PDF_SHA256[report_value]
    selected_sha = (
        expected_sha256
        if expected_sha256 is not None
        else parsed.expected_sha256
        if parsed.expected_sha256 is not None
        else default_sha
    )
    try:
        selected_sha = _digest(selected_sha, label="预期 PDF 摘要")
    except ValueError as error:
        raise PdfAcceptanceError(str(error)) from error
    if expected_sha256 is not None and parsed.expected_sha256 is not None:
        try:
            supplied_sha = _digest(expected_sha256, label="预期 PDF 摘要")
        except ValueError as error:
            raise PdfAcceptanceError(str(error)) from error
        expected_hash_drift = supplied_sha != parsed.expected_sha256
    else:
        expected_hash_drift = False

    default_count = LOCKED_PDF_PAGE_COUNTS[report_value]
    selected_count = (
        expected_page_count
        if expected_page_count is not None
        else parsed.expected_page_count
        if parsed.expected_page_count is not None
        else default_count
    )
    if (
        not isinstance(selected_count, int)
        or isinstance(selected_count, bool)
        or selected_count < 1
    ):
        raise PdfAcceptanceError("预期 PDF 页数必须是正整数")
    if expected_page_count is not None and parsed.expected_page_count is not None:
        expected_count_drift = expected_page_count != parsed.expected_page_count
    else:
        expected_count_drift = False

    root = None if project_root is None else Path(project_root).expanduser().resolve()
    violations: list[PdfAcceptanceViolation] = []

    if expected_report_value is not None and report_value != expected_report_value:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.REPORT_MISMATCH,
                f"验收报告绑定不一致：证据为 {report_value}，预期为 {expected_report_value}",
            )
        )
    if expected_hash_drift:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.EXPECTED_HASH_DRIFT,
                "调用方预期摘要与证据声明摘要不一致，不能确定权威 PDF",
            )
        )
    if expected_count_drift:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.PAGE_COUNT_MISMATCH,
                "调用方预期页数与证据声明页数不一致，不能确定权威 PDF",
            )
        )

    actual_sha: str | None = None
    pdf_path = _resolved_path(parsed.pdf, root)
    if verify_files:
        if not pdf_path.is_file():
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.PDF_MISSING,
                    f"当前 PDF 文件不存在：{parsed.pdf}",
                )
            )
        else:
            try:
                actual_sha = _file_sha256(pdf_path)
            except OSError as error:
                violations.append(
                    _violation(
                        PdfAcceptanceViolationCode.PDF_MISSING,
                        f"当前 PDF 文件无法读取：{parsed.pdf}（{error}）",
                    )
                )
            else:
                if actual_sha != parsed.sha256 or actual_sha != selected_sha:
                    violations.append(
                        _violation(
                            PdfAcceptanceViolationCode.PDF_HASH_MISMATCH,
                            "当前 PDF 文件摘要与锁定最终摘要不一致，旧验收结论失效",
                        )
                    )
    if parsed.sha256 != selected_sha:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.PDF_HASH_MISMATCH,
                "证据声明的 PDF 摘要与锁定最终摘要不一致",
            )
        )

    if parsed.page_count != selected_count:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.PAGE_COUNT_MISMATCH,
                f"PDF 页数不一致：证据为 {parsed.page_count} 页，预期为 {selected_count} 页",
            )
        )

    expected_pages = tuple(range(1, parsed.page_count + 1))
    actual_pages = tuple(page.page_number for page in parsed.pages)
    if actual_pages != expected_pages:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.PAGE_SEQUENCE_MISMATCH,
                f"逐页证据必须完整覆盖 1–{parsed.page_count} 页，当前顺序为 {actual_pages}",
            )
        )

    if not parsed.bookmarks:
        violations.append(
            _violation(PdfAcceptanceViolationCode.COVERAGE_MISSING, "PDF 未提供可导航书签证据")
        )
    if parsed.renders and len(parsed.renders) != parsed.page_count:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.RENDER_COUNT_MISMATCH,
                f"原始页图数量不一致：{len(parsed.renders)} 张对应 {parsed.page_count} 页",
            )
        )

    global_sizes = parsed.page_sizes
    continuation_pages = 0
    page_texts: dict[int, str] = {}
    for index, page in enumerate(parsed.pages):
        text = _read_page_text(
            page,
            project_root=root,
            verify_files=verify_files,
            violations=violations,
        )
        page_texts[page.page_number] = text
        if not text.strip():
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.PAGE_TEXT_MISSING,
                    f"第 {page.page_number} 页缺少可选择、可检索的逐页文本",
                    page_number=page.page_number,
                )
            )
        if page.text_sha256 is not None and page.text:
            actual_text_sha = hashlib.sha256(page.text.encode("utf-8")).hexdigest()
            if actual_text_sha != page.text_sha256:
                violations.append(
                    _violation(
                        PdfAcceptanceViolationCode.PAGE_TEXT_HASH_MISMATCH,
                        f"第 {page.page_number} 页内嵌文本摘要不一致",
                        page_number=page.page_number,
                    )
                )

        size = page.page_size
        if size is None and index < len(global_sizes):
            size = global_sizes[index]
        if size is not None:
            if size.orientation is not page.orientation:
                violations.append(
                    _violation(
                        PdfAcceptanceViolationCode.ORIENTATION_MISMATCH,
                        f"第 {page.page_number} 页方向声明与页面尺寸不一致",
                        page_number=page.page_number,
                    )
                )
            if not size.is_a4:
                violations.append(
                    _violation(
                        PdfAcceptanceViolationCode.NON_A4_PAGE,
                        (
                            f"第 {page.page_number} 页不是 A4 尺寸："
                            f"{size.width_pt}×{size.height_pt} pt"
                        ),
                        page_number=page.page_number,
                    )
                )

        if page.header_present is not True:
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.HEADER_MISSING,
                    f"第 {page.page_number} 页缺少页眉证据",
                    page_number=page.page_number,
                )
            )
        if page.footer_present is not True:
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.FOOTER_MISSING,
                    f"第 {page.page_number} 页缺少页脚证据",
                    page_number=page.page_number,
                )
            )
        if page.page_number_present is not True:
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.PAGE_NUMBER_MISSING,
                    f"第 {page.page_number} 页缺少页码证据",
                    page_number=page.page_number,
                )
            )
        if page.page_number_text is not None:
            match = re.search(r"(?<!\d)(\d+)(?!\d)", page.page_number_text)
            if match is None or int(match.group(1)) != page.page_number:
                violations.append(
                    _violation(
                        PdfAcceptanceViolationCode.PAGE_NUMBER_MISMATCH,
                        f"第 {page.page_number} 页可见页码与逐页序号不一致",
                        page_number=page.page_number,
                    )
                )

        if page.continuation is None:
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.CONTINUATION_MISSING,
                    f"第 {page.page_number} 页缺少续表状态证据",
                    page_number=page.page_number,
                )
            )
        elif page.continuation:
            continuation_pages += 1
            if "续表" not in text and not (page.continuation_marker or "").strip():
                violations.append(
                    _violation(
                        PdfAcceptanceViolationCode.CONTINUATION_MARKER_MISSING,
                        f"第 {page.page_number} 页声明为续表但缺少可检索“续表”标记",
                        page_number=page.page_number,
                    )
                )
        elif "续表" in text:
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.CONTINUATION_MARKER_MISSING,
                    f"第 {page.page_number} 页含有“续表”但续表状态声明为否",
                    page_number=page.page_number,
                )
            )

        _check_image_file(
            page.image,
            label=f"第 {page.page_number} 页原始页图",
            page_number=page.page_number,
            project_root=root,
            verify_files=verify_files,
            missing_code=PdfAcceptanceViolationCode.PAGE_IMAGE_MISSING_FILE,
            hash_code=PdfAcceptanceViolationCode.PAGE_IMAGE_HASH_MISMATCH,
            violations=violations,
        )

    if require_continuation and continuation_pages == 0:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.CONTINUATION_MISSING,
                "全部逐页证据中未发现任何续表页及其可检索标记",
            )
        )

    contact_sheets = parsed.accepted_contact_sheets
    if require_contact_sheet and not contact_sheets:
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.CONTACT_SHEET_MISSING,
                "缺少当前 PDF 重新生成的 contact sheet 证据",
            )
        )
    for index, contact_sheet in enumerate(contact_sheets, start=1):
        _check_image_file(
            contact_sheet,
            label=f"contact sheet {index}",
            page_number=None,
            project_root=root,
            verify_files=verify_files,
            missing_code=PdfAcceptanceViolationCode.CONTACT_SHEET_MISSING_FILE,
            hash_code=PdfAcceptanceViolationCode.CONTACT_SHEET_HASH_MISMATCH,
            violations=violations,
        )

    if require_coverage:
        if parsed.coverage is None and parsed.coverage_ok is None:
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.COVERAGE_MISSING,
                    "缺少现有 coverage projection 验收证据",
                )
            )
        elif parsed.coverage_ok is not True and not (
            isinstance(parsed.coverage, Mapping) and parsed.coverage.get("ok") is True
        ):
            violations.append(
                _violation(
                    PdfAcceptanceViolationCode.COVERAGE_FAILED,
                    "coverage projection 未通过或缺少完整责任页覆盖",
                )
            )
    for defect in parsed.defects:
        detail = defect.get("message") or defect.get("description") or defect.get("kind")
        violations.append(
            _violation(
                PdfAcceptanceViolationCode.REPORTED_DEFECT,
                f"结构化证据仍记录缺陷：{detail or '未命名缺陷'}",
            )
        )

    # Keep the local extraction variable as an explicit proof boundary: if a
    # producer supplied text paths, continuation checks above always consume
    # the current bytes rather than an old in-memory claim.
    del page_texts
    return PdfAcceptanceResult(
        evidence=parsed,
        expected_sha256=selected_sha,
        expected_page_count=selected_count,
        actual_sha256=actual_sha,
        violations=tuple(violations),
        ok=not violations,
    )


def validate_pdf_acceptance(
    evidence: PdfAcceptanceEvidence | Mapping[str, Any],
    **kwargs: Any,
) -> PdfAcceptanceResult:
    """Strict validation wrapper: return a result or raise on any defect."""
    result = verify_pdf_acceptance(evidence, **kwargs)
    if not result.ok:
        raise PdfAcceptanceError(result.message_zh)
    return result


def verify_bound_pdf_hash(
    evidence: PdfAcceptanceEvidence | Mapping[str, Any],
    *,
    project_root: Path | str | None = None,
) -> str:
    """Re-hash the currently bound PDF and fail closed on any drift."""
    try:
        parsed = (
            evidence
            if isinstance(evidence, PdfAcceptanceEvidence)
            else PdfAcceptanceEvidence.model_validate(evidence)
        )
    except ValidationError as error:
        raise PdfAcceptanceError(f"PDF 绑定证据结构无效：{error}") from error
    root = None if project_root is None else Path(project_root).expanduser().resolve()
    path = _resolved_path(parsed.pdf, root)
    if not path.is_file():
        raise PdfAcceptanceError(f"当前 PDF 文件不存在：{parsed.pdf}")
    try:
        actual = _file_sha256(path)
    except OSError as error:
        raise PdfAcceptanceError(f"当前 PDF 文件无法读取：{parsed.pdf}（{error}）") from error
    if actual != parsed.sha256:
        raise PdfAcceptanceError("当前 PDF 摘要与证据声明不一致，旧验收结论失效")
    return actual


# Descriptive aliases keep the contract discoverable to callers that use
# "observation"/"verification" terminology, while all behavior remains in
# the single model and verifier above.
PdfPageObservation = PdfPageEvidence
PdfAcceptanceContract = PdfAcceptanceEvidence
PdfVerification = PdfAcceptanceResult


__all__ = [
    "LOCKED_PDF_PAGE_COUNTS",
    "LOCKED_PDF_SHA256",
    "PdfAcceptanceContract",
    "PdfAcceptanceError",
    "PdfAcceptanceEvidence",
    "PdfAcceptanceResult",
    "PdfAcceptanceViolation",
    "PdfAcceptanceViolationCode",
    "PdfContactSheetEvidence",
    "PdfImageEvidence",
    "PdfOrientation",
    "PdfPageEvidence",
    "PdfPageObservation",
    "PdfPageSize",
    "PdfVerification",
    "validate_pdf_acceptance",
    "verify_bound_pdf_hash",
    "verify_pdf_acceptance",
]
