from __future__ import annotations

import hashlib
import re
from pathlib import PurePath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.ids import stable_id
from ci_workflow.ingestion.classifier import SourceClassification

_SHA256 = re.compile(r"[0-9a-f]{64}")
_SAFE_FILENAME_COMPONENT = re.compile(r"[^0-9A-Za-z_.\-\u3400-\u9fff]+")


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("摄取文档字段不能为空")
    return normalized


def _filename_component(value: str) -> str:
    normalized = _SAFE_FILENAME_COMPONENT.sub("-", _text(value)).strip("-._")
    if not normalized:
        raise ValueError("无法生成规范文件名")
    return normalized


class IngestedDocumentVersion(BaseModel):
    """自动或用户补充文档的稳定身份、内容版本和父文档关系。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    document_identity: str
    source_version_id: str
    document_role: str
    document_role_label_zh: str
    parent_document_id: str | None
    original_filename: str
    canonical_filename: str
    media_type: str
    version_label: str
    content_sha256: str
    byte_size: int = Field(gt=0)

    @field_validator(
        "document_id",
        "document_identity",
        "source_version_id",
        "document_role",
        "document_role_label_zh",
        "original_filename",
        "canonical_filename",
        "media_type",
        "version_label",
    )
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("parent_document_id")
    @classmethod
    def _parent_document_id_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _content_digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("摄取文档摘要必须是小写 SHA-256")
        return value

    @model_validator(mode="after")
    def _supplement_keeps_parent(self) -> IngestedDocumentVersion:
        if self.document_role == "supplementary_material" and not self.parent_document_id:
            raise ValueError("论文补充材料必须保留父文档身份")
        return self


def create_document_version(
    *,
    document_identity: str,
    classification: SourceClassification,
    content: bytes,
    version_label: str,
) -> IngestedDocumentVersion:
    document_identity = _text(document_identity)
    version_label = _text(version_label)
    if not content:
        raise ValueError("摄取文档不能为空")
    original_filename = _text(classification.original_filename)
    if PurePath(original_filename).name != original_filename:
        raise ValueError("摄取文档必须保留不含目录的原文件名")
    suffix = PurePath(original_filename).suffix.lower()
    digest = hashlib.sha256(content).hexdigest()
    document_id = stable_id("document", document_identity)
    canonical_filename = (
        f"{_filename_component(document_identity)}_"
        f"{_filename_component(classification.document_role_label_zh)}_"
        f"{_filename_component(version_label)}_{digest[:12]}{suffix}"
    )
    return IngestedDocumentVersion(
        document_id=document_id,
        document_identity=document_identity,
        source_version_id=stable_id("source-version", document_id, digest),
        document_role=classification.document_role,
        document_role_label_zh=classification.document_role_label_zh,
        parent_document_id=classification.parent_document_id,
        original_filename=original_filename,
        canonical_filename=canonical_filename,
        media_type=classification.media_type,
        version_label=version_label,
        content_sha256=digest,
        byte_size=len(content),
    )
