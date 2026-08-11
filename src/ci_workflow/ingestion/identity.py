from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
from ci_workflow.capabilities.ontology_universe import ComponentEligibility
from ci_workflow.domain.entities import EntityIdentity, EntityType, ExternalIdentifier


def _alias(value: str) -> str:
    return " ".join(value.split()).casefold()


class AliasResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["not_found", "resolved", "conflicting"]
    candidate_entity_ids: tuple[str, ...]
    selected_entity_id: str | None
    evidence_fragment_ids: tuple[str, ...]


class EntityIdentityIndex:
    def __init__(self) -> None:
        self.entities: dict[str, EntityIdentity] = {}
        self.aliases: dict[tuple[EntityType, str], list[tuple[str, str]]] = {}
        self.external_identifiers: dict[
            tuple[str, str], list[tuple[str, str]]
        ] = {}

    def add(self, entity: EntityIdentity, *, evidence_fragment_id: str) -> None:
        existing = self.entities.get(entity.entity_id)
        if existing is not None and existing != entity:
            raise ValueError("同一实体身份对应了不同内容")
        self.entities[entity.entity_id] = entity
        for alias in (entity.canonical_name, *entity.aliases):
            key = (entity.entity_type, _alias(alias))
            pair = (entity.entity_id, evidence_fragment_id)
            if pair not in self.aliases.setdefault(key, []):
                self.aliases[key].append(pair)
        for identifier in entity.external_identifiers:
            pair = (entity.entity_id, evidence_fragment_id)
            if pair not in self.external_identifiers.setdefault(
                identifier.match_key, []
            ):
                self.external_identifiers[identifier.match_key].append(pair)

    def resolve_alias(self, alias: str, *, entity_type: EntityType) -> AliasResolution:
        matches = self.aliases.get((entity_type, _alias(alias)), [])
        entity_ids = tuple(dict.fromkeys(item[0] for item in matches))
        evidence_ids = tuple(dict.fromkeys(item[1] for item in matches))
        if not entity_ids:
            state: Literal["not_found", "resolved", "conflicting"] = "not_found"
            selected = None
        elif len(entity_ids) == 1:
            state = "resolved"
            selected = entity_ids[0]
        else:
            state = "conflicting"
            selected = None
        return AliasResolution(
            state=state,
            candidate_entity_ids=entity_ids,
            selected_entity_id=selected,
            evidence_fragment_ids=evidence_ids,
        )

    def resolve_external_identifier(
        self, identifier: ExternalIdentifier
    ) -> AliasResolution:
        matches = self.external_identifiers.get(identifier.match_key, [])
        entity_ids = tuple(dict.fromkeys(item[0] for item in matches))
        evidence_ids = tuple(dict.fromkeys(item[1] for item in matches))
        if not entity_ids:
            state: Literal["not_found", "resolved", "conflicting"] = "not_found"
            selected = None
        elif len(entity_ids) == 1:
            state = "resolved"
            selected = entity_ids[0]
        else:
            state = "conflicting"
            selected = None
        return AliasResolution(
            state=state,
            candidate_entity_ids=entity_ids,
            selected_entity_id=selected,
            evidence_fragment_ids=evidence_ids,
        )

class CompetitorUniverseMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity: EntityIdentity
    eligibility: ComponentEligibility


class CompetitorUniverse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    universe_closed: bool
    members: tuple[CompetitorUniverseMember, ...]
    eligibility_audit: tuple[ComponentEligibility, ...]

    @classmethod
    def build(
        cls,
        *,
        entities: tuple[EntityIdentity, ...],
        eligibility: tuple[ComponentEligibility, ...],
        evidence_registry: ScientificLineageRegistry,
    ) -> CompetitorUniverse:
        by_id = {entity.entity_id: entity for entity in entities}
        if len(by_id) != len(entities):
            raise ValueError("竞品宇宙实体身份不得重复")
        eligibility_ids = tuple(item.component_id for item in eligibility)
        eligibility_id_set = set(eligibility_ids)
        if len(eligibility_id_set) != len(eligibility_ids):
            raise ValueError("每个实体必须且只能有一条适格记录")
        unknown = eligibility_id_set - set(by_id)
        if unknown:
            raise ValueError("适格记录引用了未登记实体")
        if set(by_id) - eligibility_id_set:
            raise ValueError("每个实体必须且只能有一条适格记录")
        verified_fragment_ids = evidence_registry.verified_fragment_ids
        referenced_fragments = {
            fragment_id
            for item in eligibility
            for fragment_id in item.evidence_fragment_ids
        }
        if not referenced_fragments <= verified_fragment_ids:
            raise ValueError("竞品宇宙引用了尚未登记并重开的证据片段")
        review_fragments = {
            fragment_id
            for item in eligibility
            if item.review_receipt is not None
            for fragment_id in item.review_receipt.evidence_fragment_ids
        }
        if not review_fragments <= verified_fragment_ids:
            raise ValueError("边界审查引用了尚未登记并重开的证据片段")
        pending = any(item.decision == "review_pending" for item in eligibility)
        members = tuple(
            CompetitorUniverseMember(entity=by_id[item.component_id], eligibility=item)
            for item in eligibility
            if item.decision == "included"
        )
        return cls(
            universe_closed=not pending,
            members=members,
            eligibility_audit=eligibility,
        )
