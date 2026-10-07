"""A/B/C common presentation of source-bound entities and explicit role edges.

This reads the existing graph/lineage registry; it never infers a holder from a
sponsor, corporate spelling or commercial partnership, and never signs review.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType


def project_product_identity(
    entity_id: str, graph: EntityGraph, evidence: ScientificLineageRegistry, *, cutoff: datetime,
) -> dict[str, Any]:
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("身份投影截止时点必须包含时区")
    product = EntityIdentity.model_validate(graph.entities[entity_id].model_dump())
    if product.entity_type not in {EntityType.PRODUCT, EntityType.DRUG_PROJECT, EntityType.REGIMEN}:
        raise ValueError("身份头必须引用药物、研发项目或方案")
    by_fragment = {item.fragment.fragment_id: item for item in evidence.verified_fragments}

    def known(fragment_id: str) -> bool:
        item = by_fragment.get(fragment_id)
        return item is not None and (
            item.source_version.acquired_at <= cutoff
            or item.source_version.published_at.is_known_by(cutoff)
            or item.source_version.first_disclosed_at.is_known_by(cutoff)
        )

    def display(entity: EntityIdentity) -> str:
        return (entity.official_chinese_name
                if entity.official_chinese_name and entity.name_evidence_fragment_id
                and known(entity.name_evidence_fragment_id) else entity.canonical_name)

    def reason(edge: EntityRelation) -> str | None:
        if edge.evidence_fragment_id not in by_fragment:
            return "source_not_verified"
        if not known(edge.evidence_fragment_id):
            return "not_known_at_cutoff"
        if edge.observed_at is None:
            return "observation_date_unknown"
        if edge.observed_at > cutoff and (
            edge.effective_from is None or edge.effective_from > cutoff
        ):
            return "not_known_at_cutoff"
        if edge.effective_from is not None and edge.effective_from > cutoff:
            return "not_yet_effective"
        if edge.effective_until is not None and cutoff >= edge.effective_until:
            return "expired"
        if edge.predicate == "has_mah" and (
            not edge.jurisdiction or not edge.authorization_scope
        ):
            return "authorization_scope_unknown"
        return None

    edges = sorted((EntityRelation.model_validate(item.model_dump())
                    for item in graph.relations.values()), key=lambda item: item.relation_id)
    unresolved: list[dict[str, str]] = []
    companies: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    for edge in edges:
        if edge.subject_entity_id != entity_id or edge.predicate not in {
            "has_mah", "has_development_rights_holder", "has_target",
        }:
            continue
        problem = reason(edge)
        if problem is not None:
            unresolved.append({"relation_id": edge.relation_id, "reason": problem})
            continue
        other = graph.entities[edge.object_entity_id]
        if edge.predicate == "has_target":
            if other.entity_type is not EntityType.TARGET:
                raise ValueError("靶点关系不得引用公司或药物实体")
            targets.append({"entity_id": other.entity_id, "name": display(other),
                            "evidence_fragment_id": edge.evidence_fragment_id})
            continue
        if other.entity_type is not EntityType.ORGANIZATION:
            raise ValueError("持有人关系必须引用组织实体")
        parents = [item for item in edges if item.subject_entity_id == other.entity_id
                   and item.predicate == "controlled_by" and reason(item) is None]
        parent_ids = {item.object_entity_id for item in parents}
        parent = graph.entities[next(iter(parent_ids))] if len(parent_ids) == 1 else None
        if parent is not None and parent.entity_type is not EntityType.ORGANIZATION:
            raise ValueError("集团关系必须引用组织实体")
        china = edge.predicate == "has_mah" and edge.jurisdiction == "CN"
        role = ("中国MAH" if china else f"境外MAH（{edge.jurisdiction}）"
                if edge.predicate == "has_mah" else "研发权益方")
        if china and parent is not None:
            label = (f"{display(parent)}｜中国MAH" if parent.entity_id == other.entity_id
                     else f"{display(parent)}｜中国MAH所属集团")
        elif china:
            label = f"{display(other)}｜集团归属待核"
        else:
            label = f"{display(other)}｜{role}"
        companies.append({
            "legal_entity_id": other.entity_id, "legal_entity_name": other.canonical_name,
            "group_entity_id": parent.entity_id if parent is not None else None,
            "role": role, "jurisdiction": edge.jurisdiction,
            "authorization_scope": edge.authorization_scope,
            "effective_from": edge.effective_from, "effective_until": edge.effective_until,
            "observed_at": edge.observed_at, "label": label,
            "evidence_fragment_ids": [edge.evidence_fragment_id,
                *sorted({item.evidence_fragment_id for item in parents})],
        })
    companies.sort(key=lambda row: (row["role"] != "中国MAH",
                                   row["role"] == "研发权益方", row["legal_entity_id"]))
    preferred = ([row for row in companies if row["role"] == companies[0]["role"]]
                 if companies else [])
    return {
        "entity_id": entity_id, "display_name": display(product),
        "original_name": product.canonical_name, "aliases": list(product.aliases),
        "targets": targets, "companies": companies, "unresolved_relations": unresolved,
        "company_label": "公司：" + "；".join(dict.fromkeys(row["label"] for row in preferred))
            if preferred else "公司归属待核",
    }
