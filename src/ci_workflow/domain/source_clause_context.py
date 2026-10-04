"""Source-scoped clause context, separate from report/page/consumer identity."""

import re

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from ci_workflow.domain.evidence import EvidenceLocator


class SourceClauseReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    label_zh: str = Field(min_length=1)
    locator: EvidenceLocator
    original_text: str = Field(min_length=1)

    @field_validator("original_text")
    @classmethod
    def _raw_quote(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Context quote cannot be blank")
        return value


class SourceClauseRelation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relation_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    description: str = Field(min_length=1)
    references: tuple[SourceClauseReference, ...] = Field(min_length=1)


class SourceClauseContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label_zh: str = Field(min_length=1)
    scope_note_zh: str = Field(min_length=1)
    scientific_scope: dict[str, JsonValue]
    continuations: tuple[SourceClauseReference, ...] = ()
    relations: tuple[SourceClauseRelation, ...] = ()

    @field_validator("label_zh", "scope_note_zh")
    @classmethod
    def _chinese_note(cls, value: str) -> str:
        if not re.search(r"[\u4e00-\u9fff]", value):
            raise ValueError("Clause explanation must contain Chinese")
        return value
