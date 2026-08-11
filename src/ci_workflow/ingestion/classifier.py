from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

DocumentRole = Literal[
    "registry_record",
    "web_page",
    "publication_pdf",
    "supplementary_material",
    "conference_slides",
    "company_release",
    "user_provided_file",
    "review_pending",
]
SourceFamily = Literal[
    "clinical_trial_registry",
    "general_web",
    "publication",
    "conference",
    "company_disclosure",
    "unknown",
]
IngestionChannel = Literal["automatic", "manual_inbox"]

_ROLE_LABELS: dict[DocumentRole, str] = {
    "registry_record": "临床试验登记记录",
    "web_page": "网页资料",
    "publication_pdf": "论文全文",
    "supplementary_material": "论文补充材料",
    "conference_slides": "学术会议演示材料",
    "company_release": "企业正式披露",
    "user_provided_file": "用户补充文件",
    "review_pending": "资料类型待确认",
}
_PRESENTATION_MEDIA_TYPES = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
}


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("来源文档字段不能为空")
    return normalized


class SourceDocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str
    media_type: str
    source_family: SourceFamily
    ingestion_channel: IngestionChannel
    relationship_role: Literal["supplementary_material"] | None = None
    parent_document_id: str | None = None

    @field_validator("filename", "media_type")
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("parent_document_id")
    @classmethod
    def _parent_id_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @model_validator(mode="after")
    def _supplement_has_parent(self) -> SourceDocumentInput:
        if self.relationship_role == "supplementary_material" and not self.parent_document_id:
            raise ValueError("补充材料必须关联主文档")
        return self


class SourceClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_role: DocumentRole
    document_role_label_zh: str
    original_filename: str
    media_type: str
    classification_state: Literal["classified", "review_pending"]
    parent_document_id: str | None = None

    @model_validator(mode="after")
    def _label_and_state_match_role(self) -> SourceClassification:
        if self.document_role_label_zh != _ROLE_LABELS[self.document_role]:
            raise ValueError("文档角色与中文名称不一致")
        expected_state = (
            "review_pending" if self.document_role == "review_pending" else "classified"
        )
        if self.classification_state != expected_state:
            raise ValueError("文档分类状态与角色不一致")
        return self


def classify_source(source: SourceDocumentInput) -> SourceClassification:
    if source.ingestion_channel == "manual_inbox":
        role: DocumentRole = "user_provided_file"
    elif source.relationship_role == "supplementary_material":
        role = "supplementary_material"
    elif (
        source.source_family == "clinical_trial_registry"
        and source.media_type == "application/json"
    ):
        role = "registry_record"
    elif source.source_family == "company_disclosure":
        role = "company_release"
    elif (
        source.source_family == "conference"
        and source.media_type in _PRESENTATION_MEDIA_TYPES
    ):
        role = "conference_slides"
    elif source.source_family == "publication" and source.media_type == "application/pdf":
        role = "publication_pdf"
    elif source.media_type == "text/html":
        role = "web_page"
    else:
        role = "review_pending"
    return SourceClassification(
        document_role=role,
        document_role_label_zh=_ROLE_LABELS[role],
        original_filename=source.filename,
        media_type=source.media_type,
        classification_state=(
            "review_pending" if role == "review_pending" else "classified"
        ),
        parent_document_id=source.parent_document_id,
    )
