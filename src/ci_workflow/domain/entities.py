from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

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

    @classmethod
    def create(
        cls,
        entity_type: EntityType,
        canonical_name: str,
        identity_basis: str,
        aliases: tuple[str, ...] = (),
        external_identifiers: tuple[ExternalIdentifier, ...] = (),
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
        )


class EntityRelation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relation_id: str
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    evidence_fragment_id: str

    @classmethod
    def create(
        cls,
        subject: EntityIdentity,
        predicate: str,
        object_: EntityIdentity,
        evidence_fragment_id: str,
    ) -> EntityRelation:
        predicate = _text(predicate)
        evidence_fragment_id = _text(evidence_fragment_id)
        return cls(
            relation_id=stable_id(
                "entity-relation",
                subject.entity_id,
                predicate,
                object_.entity_id,
                evidence_fragment_id,
            ),
            subject_entity_id=subject.entity_id,
            predicate=predicate,
            object_entity_id=object_.entity_id,
            evidence_fragment_id=evidence_fragment_id,
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
