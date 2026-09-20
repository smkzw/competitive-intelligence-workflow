"""Raw-asset/text derivation storage, independent of PDF report output."""

from __future__ import annotations

import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from typing import Literal, NoReturn

from ci_workflow.domain.evidence import CtgovRecordSelector, SourceTextDerivation
from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError


class SourceDerivationError(ValueError):
    """Raw asset or extraction cannot substantiate the submitted source text."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SourceDerivationError("JSON对象含重复字段，不能确定原始记录")
        result[key] = value
    return result


def _invalid_constant(value: str) -> NoReturn:
    raise SourceDerivationError("JSON来源含非有限数值")


def source_json_decoder() -> json.JSONDecoder:
    """One strict interpretation for acquisition and raw-record derivation."""
    return json.JSONDecoder(object_pairs_hook=_unique_object, parse_constant=_invalid_constant)


def _extract_ctgov_record(content: bytes, selector: CtgovRecordSelector) -> str:
    """Return the exact JSON object slice, without rounding numeric tokens."""
    decoder = source_json_decoder()
    try:
        text = content.decode("utf-8")
        payload = decoder.decode(text)
        if not isinstance(payload, dict) or not isinstance(payload.get("studies"), list):
            raise ValueError("missing studies")
        record = payload["studies"][selector.study_index]
        if record["protocolSection"]["identificationModule"]["nctId"] != selector.nct_id:
            raise ValueError("record identity mismatch")

        def whitespace(position: int) -> int:
            while position < len(text) and text[position] in " \r\n\t":
                position += 1
            return position

        position = whitespace(0) + 1  # Validated top-level object opening brace.
        while True:
            key, position = decoder.raw_decode(text, whitespace(position))
            position = whitespace(whitespace(position) + 1)  # Colon.
            if key == "studies":
                position = whitespace(position + 1)  # Array opening bracket.
                for index in range(selector.study_index + 1):
                    start = position
                    _, position = decoder.raw_decode(text, position)
                    if index == selector.study_index:
                        return text[start:position]
                    position = whitespace(whitespace(position) + 1)  # Array comma.
            _, position = decoder.raw_decode(text, position)
            position = whitespace(whitespace(position) + 1)  # Object comma.
    except (ValueError, UnicodeError, IndexError, KeyError, TypeError, RecursionError) as error:
        raise SourceDerivationError("原始JSON无法支持指定登记记录的身份与位置") from error
    raise SourceDerivationError("原始JSON未找到指定登记记录")


def _extract(
    content: bytes, media_type: str, record_selector: CtgovRecordSelector | None = None,
) -> tuple[str, Literal["utf8-strip-v1", "pypdf-text-v1", "ctgov-study-json-v1"], str]:
    if record_selector is not None:
        if media_type != "application/json":
            raise SourceDerivationError("登记记录选择器仅适用于JSON响应")
        return (
            _extract_ctgov_record(content, record_selector), "ctgov-study-json-v1",
            "stdlib-json-object-slice-v1",
        )
    if media_type == "application/pdf":
        from ci_workflow.ingestion.manual_inbox import _pdf_text_and_metadata

        if not content.startswith(b"%PDF-"):
            raise SourceDerivationError("来源资产不是有效PDF，不得把文本冒充原始文件")
        text, parseable, text_layer = _pdf_text_and_metadata(content)
        if not parseable or not text_layer:
            raise SourceDerivationError("PDF无法提取可靠文本层；需解析恢复或受控OCR并重新复核")
        return text.strip(), "pypdf-text-v1", version("pypdf")
    if not (
        media_type.startswith("text/") or media_type in {"application/json", "application/xml"}
    ):
        raise SourceDerivationError("来源媒体类型没有已实现的可验证文本提取方法")
    try:
        text = content.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise SourceDerivationError("来源文本不是UTF8，需显式转换和复核") from error
    if not text:
        raise SourceDerivationError("来源正文为空，不能生成提取回执")
    return text, "utf8-strip-v1", "unicode-strip-v1"


def capture_source_text(
    project_root: Path, content: bytes, *, media_type: str,
    record_selector: CtgovRecordSelector | None = None,
) -> tuple[str, SourceTextDerivation]:
    """Preserve exact public-source bytes only after successful extraction."""
    text, method, extractor_version = _extract(content, media_type, record_selector)
    blob = ContentAddressedStore(project_root).put_bytes(content, media_type=media_type)
    return text, SourceTextDerivation(
        raw_asset=blob, text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        method=method, extractor_version=extractor_version, record_selector=record_selector,
    )


def verify_source_text_derivation(
    project_root: Path, receipt: SourceTextDerivation, text: str,
) -> None:
    """Reopen and re-extract the actual raw asset; a receipt alone is insufficient."""
    store = ContentAddressedStore(project_root)
    try:
        content = store.read_bytes(receipt.raw_asset)
    except (OSError, ContentIntegrityError) as error:
        raise SourceDerivationError("原始资产缺失或摘要漂移") from error
    extracted, method, extractor_version = _extract(
        content, receipt.raw_asset.media_type, receipt.record_selector,
    )
    if method != receipt.method or extractor_version != receipt.extractor_version:
        raise SourceDerivationError("提取方法或版本变化，需重新提取和独立复核")
    if extracted != text or hashlib.sha256(text.encode("utf-8")).hexdigest() != receipt.text_sha256:
        raise SourceDerivationError("规范文本与原始资产实际提取结果不一致")
