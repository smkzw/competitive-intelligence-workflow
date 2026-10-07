from __future__ import annotations

import json
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.ids import stable_id


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("实体身份字段不能为空")
    return normalized


class EntityType(Enum):
    PRODUCT = "product"
    DRUG_PROJECT = "drug_project"
    REGIMEN = "regimen"
    ORGANIZATION = "organization"
    TRIAL = "trial"
    COHORT = "cohort"
    ARM = "arm"
    TARGET = "target"


class ExternalIdentifier(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    namespace: str
    value: str

    @field_validator("namespace", "value")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        return _text(value)

    @property
    def match_key(self) -> tuple[str, str]:
        """Return a comparison key without changing the source-facing identifier."""
        return (self.namespace.casefold(), self.value.casefold())

class EntityIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_id: str
    entity_type: EntityType
    canonical_name: str
    identity_basis: str
    aliases: tuple[str, ...]
    external_identifiers: tuple[ExternalIdentifier, ...]
    official_chinese_name: str | None = Field(default=None, exclude_if=lambda value: value is None)
    name_evidence_fragment_id: str | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )

    @field_validator("official_chinese_name", "name_evidence_fragment_id")
    @classmethod
    def _optional_name_has_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @model_validator(mode="after")
    def _official_name_has_evidence(self) -> EntityIdentity:
        if bool(self.official_chinese_name) != bool(self.name_evidence_fragment_id):
            raise ValueError("正式中文名须同时提供来源片段")
        return self

    @classmethod
    def create(
        cls,
        entity_type: EntityType,
        canonical_name: str,
        identity_basis: str,
        aliases: tuple[str, ...] = (),
        external_identifiers: tuple[ExternalIdentifier, ...] = (),
        official_chinese_name: str | None = None,
        name_evidence_fragment_id: str | None = None,
    ) -> EntityIdentity:
        canonical = _text(canonical_name)
        basis = _text(identity_basis)
        normalized_aliases = tuple(dict.fromkeys(_text(item) for item in aliases))
        normalized_identifiers = tuple(dict.fromkeys(external_identifiers))
        prohibited_basis_values = {
            canonical.casefold(),
            *(item.casefold() for item in normalized_aliases),
            *(item.value.casefold() for item in normalized_identifiers),
        }
        if basis.casefold() in prohibited_basis_values:
            raise ValueError("身份依据不能直接使用名称、别名或外部登记号")
        return cls(
            entity_id=stable_id("entity", entity_type.value, basis),
            entity_type=entity_type,
            canonical_name=canonical,
            identity_basis=basis,
            aliases=normalized_aliases,
            external_identifiers=normalized_identifiers,
            official_chinese_name=(
                _text(official_chinese_name) if official_chinese_name is not None else None
            ),
            name_evidence_fragment_id=(
                _text(name_evidence_fragment_id) if name_evidence_fragment_id is not None else None
            ),
        )


class EntityRelation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relation_id: str
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    evidence_fragment_id: str
    jurisdiction: str | None = Field(default=None, exclude_if=lambda value: value is None)
    authorization_scope: str | None = Field(default=None, exclude_if=lambda value: value is None)
    effective_from: datetime | None = Field(default=None, exclude_if=lambda value: value is None)
    effective_until: datetime | None = Field(default=None, exclude_if=lambda value: value is None)
    observed_at: datetime | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("jurisdiction", "authorization_scope")
    @classmethod
    def _optional_scope_is_nonblank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("effective_from", "effective_until", "observed_at")
    @classmethod
    def _date_has_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("关系日期必须包含时区")
        return value

    @model_validator(mode="after")
    def _scope_interval_is_ordered(self) -> EntityRelation:
        if (self.effective_from is not None and self.effective_until is not None
                and self.effective_until <= self.effective_from):
            raise ValueError("关系有效区间必须递增")
        return self

    @classmethod
    def create(
        cls,
        subject: EntityIdentity,
        predicate: str,
        object_: EntityIdentity,
        evidence_fragment_id: str,
        *,
        jurisdiction: str | None = None,
        authorization_scope: str | None = None,
        effective_from: datetime | None = None,
        effective_until: datetime | None = None,
        observed_at: datetime | None = None,
    ) -> EntityRelation:
        predicate = _text(predicate)
        evidence_fragment_id = _text(evidence_fragment_id)
        metadata = {
            "jurisdiction": jurisdiction, "authorization_scope": authorization_scope,
            "effective_from": effective_from, "effective_until": effective_until,
            "observed_at": observed_at,
        }
        scope = {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in metadata.items() if value is not None
        }
        scope_key = (json.dumps(scope, sort_keys=True, ensure_ascii=False),) if scope else ()
        return cls(
            relation_id=stable_id(
                "entity-relation",
                subject.entity_id,
                predicate,
                object_.entity_id,
                evidence_fragment_id,
                *scope_key,
            ),
            subject_entity_id=subject.entity_id,
            predicate=predicate,
            object_entity_id=object_.entity_id,
            evidence_fragment_id=evidence_fragment_id,
            jurisdiction=jurisdiction,
            authorization_scope=authorization_scope,
            effective_from=effective_from,
            effective_until=effective_until,
            observed_at=observed_at,
        )


class EntityGraph:
    def __init__(self) -> None:
        self.entities: dict[str, EntityIdentity] = {}
        self.relations: dict[str, EntityRelation] = {}

    def add_entity(self, entity: EntityIdentity) -> None:
        existing = self.entities.get(entity.entity_id)
        if existing is not None and existing != entity:
            raise ValueError("同一实体身份对应了不同内容")
        self.entities[entity.entity_id] = entity

    def add_relation(self, relation: EntityRelation) -> None:
        if relation.subject_entity_id not in self.entities:
            raise ValueError("关系主体尚未登记")
        if relation.object_entity_id not in self.entities:
            raise ValueError("关系客体尚未登记")
        self.relations[relation.relation_id] = relation

    def related(self, entity_id: str, predicate: str) -> tuple[str, ...]:
        return tuple(
            item.object_entity_id
            for item in self.relations.values()
            if item.subject_entity_id == entity_id and item.predicate == predicate
        )
