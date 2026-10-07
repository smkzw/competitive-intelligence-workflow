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

from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType
from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
from ci_workflow.reports.common.identity_projection import load_identity_context
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
) -> dict[str, Any]:
    raw_spec = source_set.read_bytes()
    if (output.exists() or output.is_symlink()
            or hashlib.sha256(raw_spec).hexdigest() != expected_sha):
        raise ValueError("Requires pinned source-set and fresh candidate output")
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
        acquired = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if acquired > datetime.now(UTC):
            raise ValueError("Source local acquisition is in the future")
        planned.append((item, raw, locator, quote, acquired))
    _graph(spec, {key: key for key in keys})  # Validate all relationships before writing.
    apply_migrations(output / "state/project.sqlite")
    store = ContentAddressedStore(output)
    repository = EvidenceRepository(output / "state/project.sqlite", store)
    refs = {}
    for item, raw, locator, quote, acquired in planned:
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
    graph, product_ids = _graph(spec, refs)
    payload = {"entities": [e.model_dump(mode="json") for e in graph.entities.values()],
               "relations": [e.model_dump(mode="json") for e in graph.relations.values()],
               "source_fragment_ids": sorted(refs.values()), "product_entity_ids": product_ids}
    asset = store.put_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode(),
                            media_type="application/json")
    load_identity_context(output, asset.model_dump(mode="json"))  # Actual repository reopen.
    receipt = {"source_set_sha256": expected_sha, "graph_asset": asset.model_dump(mode="json"),
               "source_raw_sha256": sorted({item[0]["sha256"] for item in planned}),
               "source_fragments": len(refs), "science_accepted": False, "current_promoted": False,
               "acquisition_timestamp_kind": "local_download_file_mtime_not_first_publication"}
    (output / "identity-checkpoint.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
    )
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--source-set", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(materialize(args.source_root, args.source_set, args.sha256, args.output),
                     ensure_ascii=False))
