"""Persist native PDF clauses as unreviewed evidence, not approved C observations.

Consumes a pinned proposal and an existing acquisition manifest. Local acquisition
timestamps stay local observations: replay never fabricates a new network fetch,
public date, numerical endpoint/timepoint pair, or accepted consumer binding.
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

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.fresh_research_primitives import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.domain.evidence import ContentBlob, EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.sources.connectors.public_pdf_availability import (
    PublicPdfAvailabilityCapture,
    PublicPdfAvailabilityWitness,
    verify_public_pdf_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.source_derivation import capture_pdf_page_text, extract_locator_quote
from ci_workflow.storage.sqlite import open_database


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def materialize(
    *, source_root: Path, proposal_path: Path, proposal_sha256: str,
    acquisition_asset: ContentBlob, output: Path, observed_at: datetime,
    availability_root: Path | None = None, availability_manifest: Path | None = None,
    availability_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate all source/page/quote identities before creating a fresh candidate."""
    if output.exists() or output.is_symlink():
        raise ValueError("PDF candidate output requires a fresh directory")
    if output.resolve().is_relative_to(source_root.resolve()):
        raise ValueError("Candidate cannot be created inside the historical source root")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("Candidate observation requires a timezone")
    if observed_at > datetime.now(UTC):
        raise ValueError("Candidate observation cannot be in the future")
    proposal_raw = proposal_path.read_bytes()
    if _digest(proposal_raw) != proposal_sha256:
        raise ValueError("Frozen proposal changed")
    proposal = json.loads(proposal_raw)
    if proposal.get("accepted") is not False or proposal.get("status") != "proposal_only":
        raise ValueError("This adapter only materializes unreviewed native-clause proposals")
    atoms = proposal["atoms"]
    if not atoms or len({a["proposal_id"] for a in atoms}) != len(atoms):
        raise ValueError("Clause identities must be nonempty and unique")

    store = ContentAddressedStore(source_root)
    acquisition_raw = store.read_bytes(acquisition_asset)
    acquisition = json.loads(acquisition_raw)
    acquired_by_name = {d["name"]: d for d in acquisition["documents"]}
    documents = {d["filename"]: d for d in proposal["documents"]}
    if len(acquired_by_name) != len(acquisition["documents"]) or len(documents) != len(
        proposal["documents"]
    ):
        raise ValueError("Document acquisition identities must be unique")
    raw_documents: dict[str, bytes] = {}
    local_acquired_at: dict[str, datetime] = {}
    pages: dict[tuple[str, int], str] = {}
    replayed_quotes: dict[str, str] = {}
    for name, document in documents.items():
        acquired = acquired_by_name[name]
        raw_blob = ContentBlob.model_validate(acquired["raw_asset"])
        if (
            raw_blob.media_type != "application/pdf"
            or raw_blob.sha256 != document["raw_sha256"]
            or acquired["registered_url"] != document["url"]
            or acquired["timestamp_kind"] != "local_file_mtime_not_http_publication_date"
        ):
            raise ValueError("Document acquisition does not prove the pinned PDF identity")
        moment = datetime.fromisoformat(acquired["local_download_completed_at"])
        if moment.tzinfo is None or moment.utcoffset() is None or moment > observed_at:
            raise ValueError("Original local acquisition timestamp is invalid")
        raw_documents[name] = store.read_bytes(raw_blob)
        local_acquired_at[name] = moment
        reader = PdfReader(io.BytesIO(raw_documents[name]))
        for atom in (a for a in atoms if a["document_filename"] == name):
            page = atom["physical_page"]
            if (
                type(page) is not int or page < 1 or page > len(reader.pages)
                or atom["document_raw_sha256"] != raw_blob.sha256
                or atom["trial_id"] != document["trial_id"]
            ):
                raise ValueError("Clause PDF/page/trial identity conflicts with its source")
            page_text = pages.setdefault((name, page), (
                reader.pages[page - 1].extract_text() or ""
            ).strip())
            locator = EvidenceLocator(document_role="protocol_sap", page=page,
                                      paragraph=atom["original_quote"])
            quote = extract_locator_quote(page_text, media_type="application/pdf", locator=locator)
            if quote != atom["original_quote"].strip():
                raise ValueError("Clause original quote does not match its exact native page")
            # Keep the pinned proposal bytes as provenance, but persist exactly
            # the source span already proved by the production extractor. The
            # locator normalizes boundary whitespace; ingestion must not revert
            # to an untrimmed proposal string after successful prevalidation.
            replayed_quotes[atom["proposal_id"]] = quote
            expected = atom.get("canonical_page_text_sha256")
            if expected is not None and _digest(page_text.encode()) != expected:
                raise ValueError("Native page extractor bytes differ from the pinned proposal")
    if any(a["document_filename"] not in documents for a in atoms):
        raise ValueError("Clause references a document outside the pinned source set")

    availability_raw = b""
    witnesses: dict[str, PublicPdfAvailabilityWitness] = {}
    receipt_bytes: dict[str, bytes] = {}
    if any(x is not None for x in (availability_root, availability_manifest, availability_sha256)):
        if (availability_root is None or availability_manifest is None
                or availability_sha256 is None):
            raise ValueError("Current availability requires root, manifest and pinned digest")
        availability_raw = availability_manifest.read_bytes()
        if _digest(availability_raw) != availability_sha256:
            raise ValueError("Official availability manifest digest changed")
        availability = json.loads(availability_raw)
        if availability.get("proposal_sha256") != proposal_sha256:
            raise ValueError("Official availability manifest references another proposal")
        records = availability["records"]
        names = [record["filename"] for record in records]
        if len(set(names)) != len(names) or set(names) != set(documents):
            raise ValueError("Official availability documents differ from the pinned source set")
        availability_store = ContentAddressedStore(availability_root)
        for record in records:
            name = record["filename"]
            result = PublicPdfAvailabilityCapture.model_validate(record["capture"])
            proof = result.witness
            if proof is None or proof.receipt_asset is None:
                raise ValueError("Official acquisition did not produce a reusable receipt")
            raw_blob = ContentBlob.model_validate(acquired_by_name[name]["raw_asset"])
            reopened = verify_public_pdf_availability(
                availability_root, proof, documents[name]["url"], raw_blob, observed_at,
            )
            if reopened != raw_documents[name]:
                raise ValueError("Official bytes differ from the pinned native source")
            witnesses[name] = proof
            receipt_bytes[name] = availability_store.read_bytes(proof.receipt_asset)

    # From here failures leave a recoverable candidate directory, never current.
    output.mkdir(parents=True, exist_ok=False)
    apply_migrations(output / "state/project.sqlite")
    candidate_store = ContentAddressedStore(output)
    proposal_blob = candidate_store.put_bytes(proposal_raw, media_type="application/json")
    acquisition_copy = candidate_store.put_bytes(acquisition_raw, media_type="application/json")
    availability_copy = None
    if availability_raw:
        availability_copy = candidate_store.put_bytes(
            availability_raw, media_type="application/json",
        )
        for name, raw_receipt in receipt_bytes.items():
            copied = candidate_store.put_bytes(raw_receipt, media_type="application/json")
            if copied != witnesses[name].receipt_asset:
                raise ValueError("Copied official receipt changed")
    captures: dict[tuple[str, int], SourceCapture] = {}
    for (name, page), expected_text in sorted(pages.items()):
        text, derivation = capture_pdf_page_text(output, raw_documents[name], page=page)
        if text != expected_text:
            raise ValueError("Prevalidation and production page extraction disagree")
        document = documents[name]
        captures[name, page] = SourceCapture(
            source_id=stable_id("pdf-page-source", document["raw_sha256"], str(page)),
            route_id="saved-public-protocol-sap", source_type="protocol_sap",
            title=f"{document['trial_id']} {name} physical page {page}",
            url=document["url"], query_or_identifier=document["trial_id"], language="en",
            access_method=("official_public_get_receipt_replay" if witnesses else
                           "saved_public_pdf_local_acquisition_replay"),
            media_type="application/pdf", content_text=text, text_derivation=derivation,
            acquired_at=(witnesses[name].observed_available_at if witnesses
                         else local_acquired_at[name]), published_at=None, effective_at=None,
            first_disclosed_at=None,
            public_pdf_availability=witnesses.get(name),
            locator=EvidenceLocator(document_role="protocol_sap", page=page,
                                    url=document["url"]),
        )
    facts = tuple(ResearchFact(
        fact_id=atom["proposal_id"], row_ref="source-clause:" + atom["proposal_id"],
        entity_id=atom["trial_id"].casefold(), entity_type="trial",
        canonical_name=atom["trial_id"], field_id="source_clause",
        raw_value=replayed_quotes[atom["proposal_id"]], normalized_value=None,
        disclosure_state="reported_value",
        source_id=captures[atom["document_filename"], atom["physical_page"]].source_id,
        locator=EvidenceLocator(document_role="protocol_sap", page=atom["physical_page"],
                                paragraph=atom["original_quote"]),
        original_text=replayed_quotes[atom["proposal_id"]],
    ) for atom in atoms)
    # Verbatim clauses, not model interpretations, estimated values or synthesized claims.
    claims = tuple(ResearchClaim(
        claim_id=stable_id("source-clause-claim", fact.fact_id),
        claim_text=fact.original_text, claim_kind="direct_evidence", fact_ids=(fact.fact_id,),
    ) for fact in facts)
    scientific_digest = _digest(proposal_raw + b"\n" + acquisition_raw
                                + (b"\n" + availability_raw if availability_raw else b""))
    lineage = ingest_research_evidence(
        project_root=output, project_id=stable_id("pdf-clause-candidate", scientific_digest),
        contract_version=1, report_kind="C", data_cutoff=observed_at,
        scientific_content_digest=scientific_digest, created_at=observed_at,
        sources=tuple(captures.values()), route_attempts=(), facts=facts, claims=claims,
    )
    repository = EvidenceRepository(output / "state/project.sqlite", candidate_store)
    for fact in facts:
        fragment = repository.read_fragment(lineage.fragment_by_fact_id[fact.fact_id])
        repository.verify_reopened_fragment_record(
            fragment, reopened_original_text=fragment.original_text,
            source_version_id=fragment.source_version_id,
        )
    SnapshotStore(output).read(lineage.evidence_snapshot)
    with open_database(output / "state/project.sqlite") as database:
        accepted = database.execute(
            "SELECT COUNT(*) FROM fact_versions WHERE review_state='accepted'",
        ).fetchone()[0]
        bindings = database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings",
        ).fetchone()[0]
    manifest: dict[str, Any] = {
        "schema_version": "pdf-native-clause-candidate-v1",
        "accepted": False, "status": "candidate_unreviewed",
        "scientific_content_digest": scientific_digest,
        "proposal_asset": proposal_blob.model_dump(mode="json"),
        "acquisition_asset": acquisition_copy.model_dump(mode="json"),
        "evidence_snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
        "counts": {"clauses": len(facts), "native_pages": len(captures),
                   "raw_documents": len(documents), "reopened_clauses": len(facts),
                   "accepted_facts": int(accepted), "consumer_bindings": int(bindings)},
        "fact_version_by_ref": dict(lineage.fact_version_by_ref),
        "source_version_ids": list(lineage.source_version_ids),
        "historical_cutoff_eligible": False,
        "limitations": [
            "Local acquisition timestamps are not independently re-proved CDN transfers",
            "Printed/version/upload date roles remain in the pinned proposal, "
            "not promoted to first disclosure",
            "Source clauses are not accepted C endpoint/timepoint observations "
            "or legal report bindings",
            "Scientific scopes, conflicts, gaps and old quote identities remain "
            "in the pinned proposal asset",
        ],
    }
    if availability_copy is not None:
        manifest["availability_asset"] = availability_copy.model_dump(mode="json")
        manifest["current_availability_eligible"] = True
        manifest["limitations"][0] = (
            "Exact official GET receipt and raw bytes reopened; current availability only"
        )
    with (output / "candidate-manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--proposal-sha256", required=True)
    parser.add_argument("--acquisition-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--availability-root", type=Path)
    parser.add_argument("--availability-manifest", type=Path)
    parser.add_argument("--availability-sha256")
    args = parser.parse_args()
    relative = f"evidence/raw/sha256/{args.acquisition_sha256[:2]}/{args.acquisition_sha256}.bin"
    acquisition_path = args.source_root / relative
    manifest = materialize(
        source_root=args.source_root, proposal_path=args.proposal,
        proposal_sha256=args.proposal_sha256,
        acquisition_asset=ContentBlob(
            sha256=args.acquisition_sha256, relative_path=relative,
            byte_size=acquisition_path.stat().st_size, media_type="application/json",
        ),
        output=args.output, observed_at=datetime.now(UTC),
        availability_root=args.availability_root, availability_manifest=args.availability_manifest,
        availability_sha256=args.availability_sha256,
    )
    print(json.dumps({"status": manifest["status"], "counts": manifest["counts"]}))


if __name__ == "__main__":
    main()
