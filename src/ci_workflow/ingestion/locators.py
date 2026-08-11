from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id

_FIELD_TOKEN = re.compile(r"(?P<key>[^.\[\]]+)|\[(?P<index>[0-9]+)\]")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("证据定位字段不能为空")
    return normalized


def _canonical_json(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise ValueError("登记记录必须是可序列化的 JSON 对象") from error


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _evidence_locator_json(locator: EvidenceLocator) -> str:
    return json.dumps(
        locator.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class RegistryJsonSnapshot(BaseModel):
    """与来源版本绑定的不可变登记 JSON 快照。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    source_url: str
    document_role_label_zh: str
    canonical_json: str
    content_sha256: str

    @field_validator(
        "source_version_id", "source_url", "document_role_label_zh", "canonical_json"
    )
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("登记快照摘要必须是小写 SHA-256")
        return value

    @property
    def payload(self) -> dict[str, Any]:
        parsed = json.loads(self.canonical_json)
        if not isinstance(parsed, dict):
            raise ValueError("登记快照不是 JSON 对象")
        return parsed

    @classmethod
    def create(
        cls,
        *,
        source_version_id: str,
        payload: Mapping[str, Any],
        source_url: str,
        document_role_label_zh: str,
    ) -> RegistryJsonSnapshot:
        canonical = _canonical_json(payload)
        return cls(
            source_version_id=source_version_id,
            source_url=source_url,
            document_role_label_zh=document_role_label_zh,
            canonical_json=canonical,
            content_sha256=_content_sha256(canonical),
        )


class RegistryJsonLocator(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    locator_id: str
    anchor_kind: Literal["registry_json_field"] = "registry_json_field"
    source_version_id: str
    source_content_sha256: str
    evidence_locator: EvidenceLocator

    @field_validator("locator_id", "source_version_id")
    @classmethod
    def _locator_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("source_content_sha256")
    @classmethod
    def _locator_digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("定位摘要必须是小写 SHA-256")
        return value


def _parse_field_path(field_path: str) -> tuple[str | int, ...]:
    field_path = _text(field_path)
    tokens: list[str | int] = []
    position = 0
    for match in _FIELD_TOKEN.finditer(field_path):
        if match.start() != position and not (
            field_path[position : match.start()] == "."
        ):
            raise ValueError("登记字段路径格式不正确")
        key = match.group("key")
        index = match.group("index")
        tokens.append(int(index) if index is not None else str(key))
        position = match.end()
    if position != len(field_path) or not tokens:
        raise ValueError("登记字段路径格式不正确")
    return tuple(tokens)


def _resolve_json_field(payload: Any, field_path: str) -> Any:
    current = payload
    for token in _parse_field_path(field_path):
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                raise ValueError("登记字段路径未定位到现有数组元素")
            current = current[token]
        else:
            if not isinstance(current, dict) or token not in current:
                raise ValueError("登记字段路径未定位到现有字段")
            current = current[token]
    return current


def create_registry_json_locator(
    snapshot: RegistryJsonSnapshot, *, field_path: str
) -> RegistryJsonLocator:
    normalized_path = _text(field_path)
    _resolve_json_field(snapshot.payload, normalized_path)
    evidence_locator = EvidenceLocator(
        document_role=snapshot.document_role_label_zh,
        field_path=normalized_path,
        url=snapshot.source_url,
    )
    return RegistryJsonLocator(
        locator_id=stable_id(
            "registry-json-locator",
            snapshot.source_version_id,
            snapshot.content_sha256,
            _evidence_locator_json(evidence_locator),
        ),
        source_version_id=snapshot.source_version_id,
        source_content_sha256=snapshot.content_sha256,
        evidence_locator=evidence_locator,
    )


def reopen_registry_json_locator(
    snapshot: RegistryJsonSnapshot, locator: RegistryJsonLocator
) -> Any:
    if (
        snapshot.source_version_id != locator.source_version_id
        or snapshot.content_sha256 != locator.source_content_sha256
    ):
        raise ValueError("定位器与来源版本或内容摘要不一致")
    expected_locator_id = stable_id(
        "registry-json-locator",
        locator.source_version_id,
        locator.source_content_sha256,
        _evidence_locator_json(locator.evidence_locator),
    )
    if locator.locator_id != expected_locator_id:
        raise ValueError("登记定位器身份校验失败")
    field_path = locator.evidence_locator.field_path
    if field_path is None:
        raise ValueError("登记字段定位器缺少字段路径")
    return _resolve_json_field(snapshot.payload, field_path)


class WebSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    heading: str
    paragraphs: tuple[str, ...] = Field(min_length=1)

    @field_validator("heading")
    @classmethod
    def _heading_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("paragraphs")
    @classmethod
    def _paragraphs_are_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_text(value) for value in values)


class WebPageSnapshot(BaseModel):
    """按标题和段落顺序保存的不可变网页快照。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    source_url: str
    document_role_label_zh: str
    sections: tuple[WebSection, ...] = Field(min_length=1)
    content_sha256: str

    @field_validator("source_version_id", "source_url", "document_role_label_zh")
    @classmethod
    def _web_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _web_digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("网页快照摘要必须是小写 SHA-256")
        return value

    @classmethod
    def create(
        cls,
        *,
        source_version_id: str,
        source_url: str,
        document_role_label_zh: str,
        sections: Sequence[Mapping[str, Any]],
    ) -> WebPageSnapshot:
        parsed_sections = tuple(WebSection.model_validate(item) for item in sections)
        canonical = json.dumps(
            [item.model_dump(mode="json") for item in parsed_sections],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return cls(
            source_version_id=source_version_id,
            source_url=source_url,
            document_role_label_zh=document_role_label_zh,
            sections=parsed_sections,
            content_sha256=_content_sha256(canonical),
        )


class WebParagraphLocator(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    locator_id: str
    anchor_kind: Literal["web_heading_paragraph"] = "web_heading_paragraph"
    source_version_id: str
    source_content_sha256: str
    heading_occurrence: int = Field(ge=1)
    paragraph_number: int = Field(ge=1)
    evidence_locator: EvidenceLocator

    @field_validator("locator_id", "source_version_id")
    @classmethod
    def _web_locator_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("source_content_sha256")
    @classmethod
    def _web_locator_digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("网页定位摘要必须是小写 SHA-256")
        return value


def _web_section(
    snapshot: WebPageSnapshot, *, heading: str, heading_occurrence: int
) -> WebSection:
    normalized_heading = _text(heading)
    matches = tuple(
        section for section in snapshot.sections if section.heading == normalized_heading
    )
    if heading_occurrence < 1 or heading_occurrence > len(matches):
        raise ValueError("网页定位器未找到指定标题及出现次序")
    return matches[heading_occurrence - 1]


def create_web_paragraph_locator(
    snapshot: WebPageSnapshot,
    *,
    heading: str,
    heading_occurrence: int,
    paragraph_number: int,
) -> WebParagraphLocator:
    section = _web_section(
        snapshot, heading=heading, heading_occurrence=heading_occurrence
    )
    if paragraph_number < 1 or paragraph_number > len(section.paragraphs):
        raise ValueError("网页定位器未找到指定段落")
    evidence_locator = EvidenceLocator(
        document_role=snapshot.document_role_label_zh,
        field_path=(f"heading[{heading_occurrence}].paragraph[{paragraph_number}]"),
        heading=section.heading,
        paragraph=f"第 {paragraph_number} 段",
        url=snapshot.source_url,
    )
    return WebParagraphLocator(
        locator_id=stable_id(
            "web-paragraph-locator",
            snapshot.source_version_id,
            snapshot.content_sha256,
            str(heading_occurrence),
            str(paragraph_number),
            _evidence_locator_json(evidence_locator),
        ),
        source_version_id=snapshot.source_version_id,
        source_content_sha256=snapshot.content_sha256,
        heading_occurrence=heading_occurrence,
        paragraph_number=paragraph_number,
        evidence_locator=evidence_locator,
    )


def reopen_web_paragraph_locator(
    snapshot: WebPageSnapshot, locator: WebParagraphLocator
) -> str:
    if (
        snapshot.source_version_id != locator.source_version_id
        or snapshot.content_sha256 != locator.source_content_sha256
    ):
        raise ValueError("定位器与来源版本或内容摘要不一致")
    expected_locator_id = stable_id(
        "web-paragraph-locator",
        locator.source_version_id,
        locator.source_content_sha256,
        str(locator.heading_occurrence),
        str(locator.paragraph_number),
        _evidence_locator_json(locator.evidence_locator),
    )
    if locator.locator_id != expected_locator_id:
        raise ValueError("网页定位器身份校验失败")
    heading = locator.evidence_locator.heading
    if heading is None:
        raise ValueError("网页定位器缺少标题")
    section = _web_section(
        snapshot,
        heading=heading,
        heading_occurrence=locator.heading_occurrence,
    )
    if locator.paragraph_number > len(section.paragraphs):
        raise ValueError("网页定位器未找到指定段落")
    return section.paragraphs[locator.paragraph_number - 1]


class PdfTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    table_name: str
    columns: tuple[str, ...] = Field(min_length=1)
    rows: tuple[tuple[str, ...], ...] = Field(min_length=1)

    @field_validator("table_name")
    @classmethod
    def _table_name_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("columns")
    @classmethod
    def _columns_are_valid(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("PDF 表格列名不得重复")
        return normalized

    @field_validator("rows")
    @classmethod
    def _rows_are_not_blank(cls, rows: tuple[tuple[str, ...], ...]) -> tuple[tuple[str, ...], ...]:
        return tuple(tuple(_text(cell) for cell in row) for row in rows)

    @model_validator(mode="after")
    def _row_width_matches_columns(self) -> PdfTable:
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("PDF 表格行列数量不一致")
        return self


class PdfPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    page_number: int = Field(ge=1)
    tables: tuple[PdfTable, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _table_names_are_unique(self) -> PdfPage:
        table_names = tuple(table.table_name for table in self.tables)
        if len(set(table_names)) != len(table_names):
            raise ValueError("PDF 同一页内表名不得重复")
        return self


class PdfDocumentSnapshot(BaseModel):
    """保存页码与表格结构的不可变 PDF 抽取快照。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    source_url: str
    document_role_label_zh: str
    pages: tuple[PdfPage, ...] = Field(min_length=1)
    content_sha256: str

    @field_validator("source_version_id", "source_url", "document_role_label_zh")
    @classmethod
    def _pdf_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _pdf_digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("PDF 快照摘要必须是小写 SHA-256")
        return value

    @model_validator(mode="after")
    def _page_numbers_are_unique(self) -> PdfDocumentSnapshot:
        page_numbers = tuple(page.page_number for page in self.pages)
        if len(set(page_numbers)) != len(page_numbers):
            raise ValueError("PDF 快照页码不得重复")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_version_id: str,
        source_url: str,
        document_role_label_zh: str,
        pages: Sequence[Mapping[str, Any]],
    ) -> PdfDocumentSnapshot:
        parsed_pages = tuple(PdfPage.model_validate(item) for item in pages)
        canonical = json.dumps(
            [page.model_dump(mode="json") for page in parsed_pages],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return cls(
            source_version_id=source_version_id,
            source_url=source_url,
            document_role_label_zh=document_role_label_zh,
            pages=parsed_pages,
            content_sha256=_content_sha256(canonical),
        )


class PdfTableCellLocator(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    locator_id: str
    anchor_kind: Literal["pdf_table_cell"] = "pdf_table_cell"
    source_version_id: str
    source_content_sha256: str
    page_number: int = Field(ge=1)
    table_name: str
    row_number: int = Field(ge=1)
    column_name: str
    evidence_locator: EvidenceLocator

    @field_validator("locator_id", "source_version_id", "table_name", "column_name")
    @classmethod
    def _pdf_locator_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("source_content_sha256")
    @classmethod
    def _pdf_locator_digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("PDF 定位摘要必须是小写 SHA-256")
        return value


def _pdf_table(
    snapshot: PdfDocumentSnapshot, *, page_number: int, table_name: str
) -> PdfTable:
    pages = tuple(page for page in snapshot.pages if page.page_number == page_number)
    if len(pages) != 1:
        raise ValueError("PDF 定位器未找到指定页")
    normalized_table_name = _text(table_name)
    tables = tuple(
        table for table in pages[0].tables if table.table_name == normalized_table_name
    )
    if len(tables) != 1:
        raise ValueError("PDF 定位器未找到唯一指定表格")
    return tables[0]


def create_pdf_table_cell_locator(
    snapshot: PdfDocumentSnapshot,
    *,
    page_number: int,
    table_name: str,
    row_number: int,
    column_name: str,
) -> PdfTableCellLocator:
    table = _pdf_table(snapshot, page_number=page_number, table_name=table_name)
    if row_number < 1 or row_number > len(table.rows):
        raise ValueError("PDF 定位器未找到指定行")
    normalized_column = _text(column_name)
    if normalized_column not in table.columns:
        raise ValueError("PDF 定位器未找到指定列")
    row_label = table.rows[row_number - 1][0]
    evidence_locator = EvidenceLocator(
        document_role=snapshot.document_role_label_zh,
        field_path=(
            f"page[{page_number}].table[{table.table_name}].row[{row_number}]"
            f".column[{normalized_column}]"
        ),
        page=page_number,
        table=table.table_name,
        row=f"第 {row_number} 行：{row_label}",
        column=normalized_column,
        url=snapshot.source_url,
    )
    return PdfTableCellLocator(
        locator_id=stable_id(
            "pdf-table-cell-locator",
            snapshot.source_version_id,
            snapshot.content_sha256,
            str(page_number),
            table.table_name,
            str(row_number),
            normalized_column,
            _evidence_locator_json(evidence_locator),
        ),
        source_version_id=snapshot.source_version_id,
        source_content_sha256=snapshot.content_sha256,
        page_number=page_number,
        table_name=table.table_name,
        row_number=row_number,
        column_name=normalized_column,
        evidence_locator=evidence_locator,
    )


def reopen_pdf_table_cell_locator(
    snapshot: PdfDocumentSnapshot, locator: PdfTableCellLocator
) -> str:
    if (
        snapshot.source_version_id != locator.source_version_id
        or snapshot.content_sha256 != locator.source_content_sha256
    ):
        raise ValueError("定位器与来源版本或内容摘要不一致")
    expected_locator_id = stable_id(
        "pdf-table-cell-locator",
        locator.source_version_id,
        locator.source_content_sha256,
        str(locator.page_number),
        locator.table_name,
        str(locator.row_number),
        locator.column_name,
        _evidence_locator_json(locator.evidence_locator),
    )
    if locator.locator_id != expected_locator_id:
        raise ValueError("PDF 定位器身份校验失败")
    table = _pdf_table(
        snapshot,
        page_number=locator.page_number,
        table_name=locator.table_name,
    )
    if locator.row_number > len(table.rows):
        raise ValueError("PDF 定位器未找到指定行")
    if locator.column_name not in table.columns:
        raise ValueError("PDF 定位器未找到指定列")
    column_index = table.columns.index(locator.column_name)
    return table.rows[locator.row_number - 1][column_index]
