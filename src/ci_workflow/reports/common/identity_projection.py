"""A/B/C common presentation of source-bound entities and explicit role edges.

This reads the existing graph/lineage registry; it never infers a holder from a
sponsor, corporate spelling or commercial partnership, and never signs review.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from jinja2 import Environment, StrictUndefined
from markupsafe import Markup
from pydantic import TypeAdapter

from ci_workflow.capabilities.extraction_normalization import verify_reopened_fragment
from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType
from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.public_pdf_availability import (
    PublicPdfAvailabilityWitness,
    verify_public_pdf_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.source_derivation import source_json_decoder


def project_product_identity(
    entity_id: str, graph: EntityGraph, evidence: ScientificLineageRegistry, *, cutoff: datetime,
    public_pdf_availability: dict[str, PublicPdfAvailabilityWitness] | None = None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("身份投影截止时点必须包含时区")
    product = EntityIdentity.model_validate(graph.entities[entity_id].model_dump())
    if product.entity_type not in {EntityType.PRODUCT, EntityType.DRUG_PROJECT, EntityType.REGIMEN}:
        raise ValueError("身份头必须引用药物、研发项目或方案")
    by_fragment = {item.fragment.fragment_id: item for item in evidence.verified_fragments}
    name_refs: set[str] = set()
    witnesses = public_pdf_availability or {}
    publicly_available: dict[str, bool] = {}

    def known(fragment_id: str) -> bool:
        item = by_fragment.get(fragment_id)
        if item is None:
            return False
        if fragment_id not in publicly_available:
            witness = witnesses.get(fragment_id)
            if witness is not None:
                derivation = item.source_version.text_derivation
                if evidence_root is None or derivation is None or not item.fragment.locator.url:
                    raise ValueError("身份公开获取凭证缺少原始来源绑定")
                # Always verify the receipt, even when a separate publication date exists.
                # A past cutoff simply cannot use this later observation.
                verify_public_pdf_availability(evidence_root, witness,
                    item.fragment.locator.url, derivation.raw_asset, datetime.now(UTC))
            publicly_available[fragment_id] = (
                item.source_version.published_at.is_known_by(cutoff)
                or item.source_version.first_disclosed_at.is_known_by(cutoff)
                or (witness is not None and witness.observed_available_at <= cutoff)
            )
        return publicly_available[fragment_id]

    def display(entity: EntityIdentity) -> str:
        if (entity.official_chinese_name and entity.name_evidence_fragment_id
                and known(entity.name_evidence_fragment_id)
                and re.search(r"(?<!\w)" + r"\s*".join(
                    re.escape(char) for char in entity.official_chinese_name if not char.isspace()
                ) + r"(?!\w)",
                    by_fragment[entity.name_evidence_fragment_id].reopened_original_text)):
            name_refs.add(entity.name_evidence_fragment_id)
            return entity.official_chinese_name
        return entity.canonical_name

    def reason(edge: EntityRelation) -> str | None:
        if edge.evidence_fragment_id not in by_fragment:
            return "source_not_verified"
        if not known(edge.evidence_fragment_id):
            return "not_known_at_cutoff"
        if edge.observed_at is None:
            return "observation_date_unknown"
        if edge.observed_at > cutoff:
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

    def group_chain(holder: EntityIdentity) -> tuple[
        EntityIdentity | None, list[str], list[EntityRelation],
    ]:
        """Only traverse explicit, verified control; ambiguity invalidates attribution."""
        current = holder
        chain = [holder.entity_id]
        used: list[EntityRelation] = []
        while True:
            candidates = [item for item in edges if item.subject_entity_id == current.entity_id
                          and item.predicate == "controlled_by"]
            if not candidates:
                return (current if used else None), chain, used
            invalid = [(item, reason(item)) for item in candidates if reason(item) is not None]
            if invalid:
                unresolved.extend({"relation_id": item.relation_id, "reason": str(problem)}
                                  for item, problem in invalid)
                return None, chain, used
            parents = {item.object_entity_id for item in candidates}
            if len(parents) != 1:
                unresolved.extend({"relation_id": item.relation_id,
                                   "reason": "group_control_conflict"} for item in candidates)
                return None, chain, used
            parent_id = next(iter(parents))
            parent = EntityIdentity.model_validate(graph.entities[parent_id].model_dump())
            if parent.entity_type is not EntityType.ORGANIZATION:
                raise ValueError("集团关系必须引用组织实体")
            used.extend(candidates)
            if parent_id == current.entity_id:
                return current, chain, used
            if parent_id in chain:
                unresolved.extend({"relation_id": item.relation_id,
                                   "reason": "group_control_cycle"} for item in candidates)
                return None, chain, used
            chain.append(parent_id)
            current = parent

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
        other = EntityIdentity.model_validate(graph.entities[edge.object_entity_id].model_dump())
        if edge.predicate == "has_target":
            if other.entity_type is not EntityType.TARGET:
                raise ValueError("靶点关系不得引用公司或药物实体")
            targets.append({"entity_id": other.entity_id, "name": display(other),
                            "evidence_fragment_id": edge.evidence_fragment_id})
            continue
        if other.entity_type is not EntityType.ORGANIZATION:
            raise ValueError("持有人关系必须引用组织实体")
        parent, chain, parents = group_chain(other)
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
            "group_chain_entity_ids": chain,
            "group_relations": [item.model_dump(mode="json") for item in parents],
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
    display_name = display(product)
    refs = (name_refs | {item["evidence_fragment_id"] for item in targets}
            | {ref for item in companies for ref in item["evidence_fragment_ids"]})
    sources = []
    for ref in sorted(refs):
        item = by_fragment[ref]
        url = item.fragment.locator.url or ""
        parsed = urlsplit(url)
        safe_url = url if (parsed.scheme == "https" and parsed.netloc
                           and not parsed.username and not parsed.password) else None
        sources.append({
            "fragment_id": ref, "source_version_id": item.source_version.source_version_id,
            "source_sha256": item.source_version.content_sha256,
            "raw_sha256": (item.source_version.text_derivation.raw_asset.sha256
                           if item.source_version.text_derivation else None),
            "url": safe_url, "page": item.fragment.locator.page,
            "original_text": item.reopened_original_text,
            "acquired_at": item.source_version.acquired_at,
            "observed_publicly_available_at": (
                witnesses[ref].observed_available_at if ref in witnesses else None),
        })
    return {
        "entity_id": entity_id, "display_name": display_name,
        "original_name": product.canonical_name, "aliases": list(product.aliases),
        "targets": targets, "companies": companies, "unresolved_relations": unresolved,
        "sources": sources,
        "company_label": "公司：" + "；".join(dict.fromkeys(row["label"] for row in preferred))
            if preferred else "公司归属待核",
    }


@dataclass(frozen=True)
class PortalIdentityContext:
    """Renderer arguments referencing existing entities, not another identity store."""

    graph: EntityGraph
    evidence: ScientificLineageRegistry
    product_entity_ids: dict[str, str]
    graph_asset: ContentBlob | None = None
    context_digest: str | None = None
    public_pdf_availability: dict[str, PublicPdfAvailabilityWitness] = field(default_factory=dict)
    evidence_root: Path | None = None

    def _digest(self) -> str:
        payload = {
            "entities": [value.model_dump(mode="json")
                         for _, value in sorted(self.graph.entities.items())],
            "relations": [value.model_dump(mode="json")
                          for _, value in sorted(self.graph.relations.items())],
            "evidence": self.evidence.model_dump(mode="json"),
            "product_entity_ids": self.product_entity_ids,
            "public_pdf_availability": {key: value.model_dump(mode="json")
                for key, value in sorted(self.public_pdf_availability.items())},
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False,
                                        sort_keys=True).encode()).hexdigest()

    def _verify_pinned_context(self) -> None:
        if self.graph_asset is not None and self.context_digest != self._digest():
            raise ValueError("已绑定的身份内容在内存中改变，必须重新从来源加载")

    def render_binding(self) -> dict[str, Any]:
        """Portable source pointer, not a new scientific identity or approval."""
        self._verify_pinned_context()
        return {"schema_version": "portal-identity-context-1",
                "graph_asset": (self.graph_asset.model_dump(mode="json")
                                if self.graph_asset else None),
                "product_ids": sorted(self.product_entity_ids)}

    def for_products(self, product_ids: tuple[str, ...]) -> PortalIdentityContext:
        """Scope a project graph to actual report consumers without remapping identities."""
        self._verify_pinned_context()
        scoped = replace(self, product_entity_ids={key: value
            for key, value in self.product_entity_ids.items() if key in product_ids})
        return replace(scoped, context_digest=scoped._digest())

    def project(self, product_ids: tuple[str, ...], *, cutoff: datetime) -> dict[str, Any]:
        self._verify_pinned_context()
        if set(self.product_entity_ids) - set(product_ids):
            raise ValueError("共同身份映射引用了报告外产品")
        headers = {product_id: project_product_identity(
            entity_id, self.graph, self.evidence, cutoff=cutoff,
            public_pdf_availability=self.public_pdf_availability, evidence_root=self.evidence_root,
        ) for product_id, entity_id in self.product_entity_ids.items()}
        return cast(dict[str, Any], TypeAdapter(dict[str, Any]).dump_python(headers, mode="json"))


def load_identity_context(root: Path, graph_asset: dict[str, Any]) -> PortalIdentityContext:
    """Reopen the existing pinned entity CAS and original sources at rebuild."""
    asset = ContentBlob.model_validate(graph_asset)
    payload = source_json_decoder().decode(ContentAddressedStore(root).read_bytes(asset).decode())
    graph = EntityGraph()
    for item in payload["entities"]:
        graph.add_entity(EntityIdentity.model_validate(item))
    for item in payload["relations"]:
        graph.add_relation(EntityRelation.model_validate(item))
    repository = EvidenceRepository(root / "state/project.sqlite", ContentAddressedStore(root))
    fragments = []
    for fragment_id in payload["source_fragment_ids"]:
        fragment = repository.read_fragment(fragment_id)
        fragments.append(verify_reopened_fragment(
            fragment, reopened_original_text=fragment.original_text,
            source_version_id=fragment.source_version_id, repository=repository,
        ))
    witnesses = {key: PublicPdfAvailabilityWitness.model_validate(value)
                 for key, value in payload.get("public_pdf_availability", {}).items()}
    by_fragment = {item.fragment.fragment_id: item for item in fragments}
    for key, witness in witnesses.items():
        item = by_fragment.get(key)
        if (item is None or item.source_version.text_derivation is None
                or not item.fragment.locator.url):
            raise ValueError("身份公开获取凭证引用未知或无原始材料的片段")
        verify_public_pdf_availability(root, witness, item.fragment.locator.url,
            item.source_version.text_derivation.raw_asset, datetime.now(UTC))
    context = PortalIdentityContext(graph, ScientificLineageRegistry.from_verified_fragments(
        tuple(fragments),
    ), payload["product_entity_ids"], asset, public_pdf_availability=witnesses, evidence_root=root)
    return replace(context, context_digest=context._digest())


IDENTITY_INPUT_PATH = "evidence/library/portal-identity-context.json"


def load_identity_binding(root: Path, payload: dict[str, Any]) -> PortalIdentityContext:
    """Existing portable graph pointer, with only a validated consumer subset allowed."""
    if (payload.get("schema_version") != "portal-identity-context-1"
            or set(payload) - {"schema_version", "graph_asset", "product_ids"}
            or not isinstance(payload.get("graph_asset"), dict)):
        raise ValueError("身份来源绑定合同不合法")
    context = load_identity_context(root, payload["graph_asset"])
    if "product_ids" in payload:
        ids = payload["product_ids"]
        if (not isinstance(ids, list) or any(not isinstance(item, str) for item in ids)
                or len(ids) != len(set(ids)) or set(ids) - set(context.product_entity_ids)):
            raise ValueError("身份来源绑定包含未知或重复消费者")
        context = context.for_products(tuple(ids))
    return context


def load_project_identity_context(root: Path) -> PortalIdentityContext | None:
    """Normal project input discovery; original CAS/PDF verification is never bypassed."""
    path = ContentAddressedStore(root).resolve_relative(IDENTITY_INPUT_PATH)
    if not path.exists():
        return None
    payload = source_json_decoder().decode(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("身份来源绑定必须是对象")
    return load_identity_binding(root, payload)


def render_identity_headers(headers: dict[str, Any]) -> Markup:
    """Safe, compact identity/source details shared by independent portals."""
    if not headers:
        return Markup("")
    template = Environment(autoescape=True, undefined=StrictUndefined).from_string("""
<section class="portal-identity" aria-label="药物身份与公司来源">
{% for product_id, item in headers.items() %}
<details data-identity-product="{{ product_id }}">
<summary>{{ item.display_name }} · {{ item.company_label }}</summary>
<dl><div><dt>原名 / INN / 研发代号</dt><dd>{{ item.original_name }}</dd></div>
{% if item.targets %}<div><dt>靶点</dt><dd>{% for target in item.targets %}
{{ target.name }}{% if not loop.last %}；{% endif %}{% endfor %}</dd></div>{% endif %}
{% for company in item.companies %}
<div><dt>{{ company.role }} · 持有人法律实体</dt><dd>{{ company.legal_entity_name }}</dd></div>
<div><dt>许可/权益范围</dt><dd>{{ company.authorization_scope or '来源未注明' }}
 · {{ company.jurisdiction or '辖区待核' }} · 观察于 {{ company.observed_at }}</dd></div>
{% if company.effective_from or company.effective_until %}<div><dt>关系有效期</dt>
<dd>{{ company.effective_from or '起点未注明' }} —
{{ company.effective_until or '终点未注明' }}</dd>
</div>{% endif %}
{% for relation in company.group_relations %}<div><dt>集团关系范围</dt>
<dd>{{ relation.get('authorization_scope', '明确控股关系') }}
 · 观察于 {{ relation.get('observed_at', '待核') }}</dd></div>{% endfor %}
{% endfor %}</dl>
<details><summary>身份来源（{{ item.sources|length }}）</summary><ul>
{% for source in item.sources %}<li>{% if source.url %}
<a href="{{ source.url }}" target="_blank" rel="noopener noreferrer">原始来源</a>
{% else %}原始来源{% endif %}{% if source.page %} · 第{{ source.page }}页{% endif %}
<blockquote>{{ source.original_text }}</blockquote></li>{% endfor %}
</ul></details></details>{% endfor %}</section>
""")
    return Markup(template.render(headers=headers))
