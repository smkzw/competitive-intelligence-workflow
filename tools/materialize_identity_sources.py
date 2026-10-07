"""Materialize source-bound entity projections, not scientific approval/current.

Uses the existing entity graph, PDF-page derivation, CAS and evidence repository.
The explicit source-set is a replay input, never an executable agent instruction.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType
from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
from ci_workflow.reports.common.identity_projection import load_identity_context
from ci_workflow.sources.connectors.public_pdf_availability import (
    PublicPdfAvailabilityWitness,
    verify_public_pdf_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.source_derivation import (
    capture_pdf_page_text,
    extract_locator_quote,
    source_json_decoder,
)


def _graph(spec: dict[str, Any], refs: dict[str, str]) -> tuple[EntityGraph, dict[str, str]]:
    graph = EntityGraph()
    entities = {}
    for item in spec["entities"]:
        key = item["key"]
        if key in entities:
            raise ValueError("Duplicate identity entity key")
        entity = EntityIdentity.create(
            EntityType(item["entity_type"]), item["canonical_name"], item["identity_basis"],
            aliases=tuple(item.get("aliases", ())),
            official_chinese_name=item.get("official_chinese_name"),
            name_evidence_fragment_id=refs[item["name_source_key"]]
                if item.get("name_source_key") else None,
        )
        entities[key] = entity
        graph.add_entity(entity)
    for item in spec["relations"]:
        dates = {key: datetime.fromisoformat(item[key]) for key in (
            "effective_from", "effective_until", "observed_at",
        ) if item.get(key) is not None}
        graph.add_relation(EntityRelation.create(
            entities[item["subject"]], item["predicate"], entities[item["object"]],
            refs[item["source_key"]], jurisdiction=item.get("jurisdiction"),
            authorization_scope=item.get("authorization_scope"),
            effective_from=dates.get("effective_from"),
            effective_until=dates.get("effective_until"),
            observed_at=dates.get("observed_at"),
        ))
    return graph, {key: entities[value].entity_id
                   for key, value in spec["product_entity_ids"].items()}


def materialize(
    source_root: Path, source_set: Path, expected_sha: str, output: Path,
    *, project_workspace: bool = False,
) -> dict[str, Any]:
    raw_spec = source_set.read_bytes()
    if (output.is_symlink() or (output.exists() and not project_workspace)
            or hashlib.sha256(raw_spec).hexdigest() != expected_sha):
        raise ValueError("Requires pinned source-set and fresh candidate output")
    canonical = None
    if project_workspace:
        store = ContentAddressedStore(output)
        canonical = store.resolve_relative("evidence/library/portal-identity-context.json")
        checkpoint = store.resolve_relative("identity-checkpoint.json")
        if canonical.exists() or checkpoint.exists():
            raise ValueError("已有身份绑定或检查点；初次摄取不得覆盖，请使用版本化更新流程")
        verify_project_workspace(output)
    spec = source_json_decoder().decode(raw_spec.decode("utf-8"))
    if spec.get("candidate_only") is not True:
        raise ValueError("Identity source replay cannot claim scientific acceptance")
    planned = []
    keys: set[str] = set()
    for item in spec["sources"]:
        if item["key"] in keys:
            raise ValueError("Duplicate identity source key")
        keys.add(item["key"])
        path = ContentAddressedStore(source_root).resolve_relative(item["filename"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"] or not raw.startswith(b"%PDF-"):
            raise ValueError("Source PDF bytes do not match pinned identity")
        reader = PdfReader(io.BytesIO(raw))
        page = item["page"]
        if type(page) is not int or page < 1 or page > len(reader.pages):
            raise ValueError("Identity source page is outside the pinned PDF")
        text = (reader.pages[page - 1].extract_text() or "").strip()
        locator = EvidenceLocator(document_role="identity_source", page=page,
                                  paragraph=item["paragraph"], url=item["url"])
        quote = extract_locator_quote(text, media_type="application/pdf", locator=locator)
        acquired = datetime.now(UTC)
        witness = (PublicPdfAvailabilityWitness.model_validate(item["public_pdf_availability"])
                   if item.get("public_pdf_availability") is not None else None)
        if witness is not None:
            witnessed_raw = verify_public_pdf_availability(source_root, witness, item["url"],
                witness.expected_raw_asset, acquired)
            if witnessed_raw != raw:
                raise ValueError("Identity public availability does not match the pinned PDF")
        planned.append((item, raw, locator, quote, acquired, witness))
    _graph(spec, {key: key for key in keys})  # Validate all relationships before writing.
    apply_migrations(output / "state/project.sqlite")
    store = ContentAddressedStore(output)
    repository = EvidenceRepository(output / "state/project.sqlite", store)
    refs = {}
    witnesses = {}
    for item, raw, locator, quote, acquired, witness in planned:
        text, derivation = capture_pdf_page_text(output, raw, page=item["page"])
        unknown_date = DateEvidence(state="not_publicly_disclosed", value=None, locator=locator)
        source = repository.add_source_version(
            source_id=item["key"], content=text.encode(), media_type="text/plain",
            acquired_at=acquired, published_at=unknown_date, effective_at=unknown_date,
            first_disclosed_at=unknown_date, text_derivation=derivation,
        )
        fragment = repository.add_fragment(source_version_id=source.source_version_id,
            locator=locator, original_text=quote, created_at=datetime.now(UTC))
        refs[item["key"]] = fragment.fragment_id
        if witness is not None:
            assert witness.receipt_asset is not None  # Already reopened and verified above.
            copied = store.put_bytes(ContentAddressedStore(source_root).read_bytes(
                witness.receipt_asset), media_type="application/json")
            if copied != witness.receipt_asset or derivation.raw_asset != witness.raw_asset:
                raise ValueError("Portable identity evidence changed during materialization")
            witnesses[fragment.fragment_id] = witness.model_dump(mode="json")
    graph, product_ids = _graph(spec, refs)
    payload = {"entities": [e.model_dump(mode="json") for e in graph.entities.values()],
               "relations": [e.model_dump(mode="json") for e in graph.relations.values()],
               "source_fragment_ids": sorted(refs.values()), "product_entity_ids": product_ids,
               "public_pdf_availability": witnesses}
    asset = store.put_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode(),
                            media_type="application/json")
    load_identity_context(output, asset.model_dump(mode="json"))  # Actual repository reopen.
    receipt = {"source_set_sha256": expected_sha, "graph_asset": asset.model_dump(mode="json"),
               "source_raw_sha256": sorted({item[0]["sha256"] for item in planned}),
               "source_fragments": len(refs), "science_accepted": False, "current_promoted": False,
               "public_availability_witnesses": len(witnesses),
               "acquisition_timestamp_kind": "source_import_clock_not_publication"}
    with (output / "identity-checkpoint.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
    if canonical is not None:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        with canonical.open("x", encoding="utf-8") as stream:
            json.dump({"schema_version": "portal-identity-context-1",
                       "graph_asset": asset.model_dump(mode="json")}, stream,
                      ensure_ascii=False, indent=2)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--source-set", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project-workspace", action="store_true",
                        help="Initial identity install into a verified project; no overwrite")
    args = parser.parse_args()
    print(json.dumps(materialize(args.source_root, args.source_set, args.sha256, args.output,
                                project_workspace=args.project_workspace),
                     ensure_ascii=False))
