"""Extend a pinned registry C candidate with exact Protocol/SAP statistics.

Uses the existing C observations, evidence ingestion, consumer registry and
ordinary review renderer. No new acceptance, current-generation or ontology.
Mapped statistics and qualified planned sample-size terms are projected;
other clauses remain explicitly deferred in the pinned source proposal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.c_portal_consumer_registry import register_c_source_consumers
from ci_workflow.application.fresh_c_research_package import research_facts_from_c_observations
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.source_research_service import ResearchClaim, SourceCapture
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import ContentBlob, EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.source_clause_context import (
    SourceClauseContext,
    SourceClauseReference,
    SourceClauseRelation,
)
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    render_report_c_review_candidate,
)
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation
from ci_workflow.sources.connectors.public_pdf_availability import verify_public_pdf_availability
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.source_derivation import (
    extract_locator_quote,
    verify_source_text_derivation,
)

_STATISTICAL_FIELDS = frozenset(
    {
        "analysis_population",
        "comparison_logic",
        "statistical_model",
        "missing_data_sensitivity",
        "sample_size_assumptions",
    }
)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_pinned(path: Path, sha256: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("Pinned candidate files cannot be symlinks")
    raw = path.read_bytes()
    if _digest(raw) != sha256:
        raise ValueError("Pinned candidate file changed")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Candidate document must be an object")
    return value


def _write_readable_review(
    output: Path, captures: dict[str, SourceCapture], observations: list[DesignObservation],
) -> dict[str, str]:
    """A readable copy of already raw-replayed pages, not a new source authority."""
    review = output / "readable-review"
    (review / "pages").mkdir(parents=True)
    (review / "clauses").mkdir()
    page_entries = []
    for source in captures.values():
        derivation = source.text_derivation
        if source.source_type != "protocol_sap" or derivation is None:
            continue
        path = review / "pages" / (source.source_id + ".txt")
        raw = source.content_text.encode("utf-8")
        path.write_bytes(raw)
        page_entries.append({
            "source_id": source.source_id, "url": source.url,
            "physical_page": derivation.page,
            "raw_pdf_sha256": derivation.raw_asset.sha256,
            "native_page_sha256": _digest(raw),
            "extractor": derivation.extractor_version,
            "path": path.relative_to(review).as_posix(),
        })
    clause_entries = []
    for row in observations:
        context = row.source_clause_context
        if context is None:
            continue
        path = review / "clauses" / (row.source_row_id + ".md")
        lines = [
            "# " + context.label_zh,
            "", "Scientific acceptance: NOT_ACCEPTED", "",
            f"Physical page: {row.source_locator.page}",
            "Source URL: " + str(row.source_locator.url),
            "Complete native page: pages/" + row.source_version_id + ".txt",
            "", "## Verbatim clause (internal line breaks preserved)", "",
            row.source_text, "", "## Source-scoped explanation (proposal, not adjudication)",
            "", context.scope_note_zh, "",
            json.dumps(context.scientific_scope, ensure_ascii=False, indent=2),
            "", "## Separately located cross-page context", "",
        ]
        for ref in context.continuations:
            lines.extend([
                ref.label_zh, f"Physical page: {ref.locator.page}",
                "Complete native page: pages/" + ref.source_id + ".txt", "",
                ref.original_text, "",
            ])
        lines.extend(["## Source relationships (no automatic winner)", ""])
        for relation in context.relations:
            lines.extend([relation.relation_id + " / " + relation.status,
                          relation.description, ""])
            for ref in relation.references:
                lines.extend([ref.reference_id + " — " + ref.label_zh,
                              "Complete native page: pages/" + ref.source_id + ".txt",
                              f"Physical page: {ref.locator.page}", ""])
        path.write_text("\n".join(lines) + "\n")
        clause_entries.append({"clause_id": row.source_row_id,
                               "path": path.relative_to(review).as_posix(),
                               "sha256": _digest(path.read_bytes())})
    (review / "index.json").write_text(json.dumps({
        "status": "readable_copy_of_raw_replayed_sources_not_independent_extraction",
        "pages": page_entries, "clauses": clause_entries,
    }, ensure_ascii=False, indent=2) + "\n")
    return {
        path.relative_to(output).as_posix(): _digest(path.read_bytes())
        for path in sorted(review.rglob("*")) if path.is_file()
    }


def extend_candidate(
    *,
    registry_root: Path,
    pdf_root: Path,
    registry_sha256: str,
    pdf_sha256: str,
    output: Path,
    observed_at: datetime,
) -> dict[str, Any]:
    """Preserve every baseline row; exact new clauses are candidates, not winners."""
    if output.exists() or output.is_symlink():
        raise ValueError("Combined C candidate needs a fresh output")
    if registry_root.is_symlink() or pdf_root.is_symlink():
        raise ValueError("Historical input roots cannot be symlinks")
    if any(output.resolve().is_relative_to(root.resolve()) for root in (registry_root, pdf_root)):
        raise ValueError("Combined output cannot be inside a historical input")
    if (
        observed_at.tzinfo is None
        or observed_at.utcoffset() is None
        or observed_at > datetime.now(UTC)
    ):
        raise ValueError("Candidate observation requires a real, timezone-aware time")
    registry = _read_pinned(registry_root / "candidate-manifest.json", registry_sha256)
    pdf = _read_pinned(pdf_root / "candidate-manifest.json", pdf_sha256)
    if (
        registry.get("schema_version") != "ctgov-c-source-candidate-1"
        or registry.get("scientific_acceptance") != "not_accepted"
        or pdf.get("schema_version") != "pdf-native-clause-candidate-v1"
        or pdf.get("accepted") is not False
    ):
        raise ValueError("Only unreviewed native candidates can be extended here")
    inputs = _read_pinned(registry_root / "inputs.json", registry["file_sha256"]["inputs.json"])
    projection = _read_pinned(
        registry_root / "projection.json",
        registry["file_sha256"]["projection.json"],
    )
    preview = json.loads((registry_root / "review-preview-manifest.json").read_bytes())
    if preview["source_manifest_sha256"] != registry_sha256:
        raise ValueError("Registry preview references another candidate")
    base = ReportCPortalData.model_validate(
        _read_pinned(
            registry_root / "review-portal-data.json",
            preview["report_data_sha256"],
        )
    )
    if [row.model_dump(mode="json") for row in base.observations] != projection["observations"]:
        raise ValueError("Registry preview observations differ from its pinned projection")
    if any(row.review_state is not FactReviewState.CANDIDATE for row in base.observations):
        raise ValueError("Do not inherit accepted observation states")
    trial_products = {row.id.casefold(): row.product_id for row in base.trials}
    if trial_products != {
        row["trial_id"].casefold(): row["product_id"] for row in inputs["bindings"]
    }:
        raise ValueError("Registry report and explicit trial/product proposals differ")
    contract = create_project_contract(
        indication=base.indication,
        reports=["C"],
        outputs=["html"],
        created_at=observed_at,
    )
    captures: dict[str, SourceCapture] = {}
    source_roots: dict[str, Path] = {}
    for source_root, descriptor in (
        (registry_root / "project", registry["snapshot"]),
        (pdf_root, pdf["evidence_snapshot"]),
    ):
        closure = SnapshotStore(source_root).read(LockedSnapshot.model_validate(descriptor))[
            "closure"
        ]
        for entry in closure["sources"]:
            source = SourceCapture.model_validate(entry["capture"])
            if source.source_id in captures:
                raise ValueError("Duplicate source identities cannot be merged by order")
            if source.acquired_at > observed_at or not source.is_available_by(contract.data_cutoff):
                raise ValueError("Source is not available by the new candidate time")
            derivation = source.text_derivation
            if derivation is None:
                raise ValueError("Every extension source requires a raw-asset proof")
            verify_source_text_derivation(source_root, derivation, source.content_text)
            if source.source_type == "protocol_sap":
                proof = source.public_pdf_availability
                if proof is None:
                    raise ValueError(
                        "Unknown first-date PDF needs real current-availability evidence"
                    )
                verify_public_pdf_availability(
                    source_root,
                    proof,
                    source.url,
                    derivation.raw_asset,
                    observed_at,
                )
            captures[source.source_id] = source
            source_roots[source.source_id] = source_root

    proposal_asset = ContentBlob.model_validate(pdf["proposal_asset"])
    proposal_raw = ContentAddressedStore(pdf_root).read_bytes(proposal_asset)
    proposal = json.loads(proposal_raw)
    if proposal.get("accepted") is not False or proposal.get("status") != "proposal_only":
        raise ValueError("Native proposal is not an unreviewed input")
    ids = [atom["proposal_id"] for atom in proposal["atoms"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate clauses cannot be merged by order")
    documents = {item["filename"]: item for item in proposal["documents"]}
    pdf_sources = {
        (source.text_derivation.raw_asset.sha256, source.text_derivation.page): source
        for source in captures.values()
        if source.source_type == "protocol_sap" and source.text_derivation is not None
    }
    observations: list[DesignObservation] = list(base.observations)
    atoms_by_id = {atom["proposal_id"]: atom for atom in proposal["atoms"]}
    relations_by_id = {item["conflict_id"]: item for item in proposal["conflicts"]}
    if len(relations_by_id) != len(proposal["conflicts"]):
        raise ValueError("Duplicate source relation identities")

    def reference(proposal_id: str) -> SourceClauseReference:
        related = atoms_by_id[proposal_id]
        source = pdf_sources[(related["document_raw_sha256"], related["physical_page"])]
        if source.query_or_identifier.casefold() != related["trial_id"].casefold():
            raise ValueError("Context clause belongs to another trial")
        related_locator = EvidenceLocator(
            document_role="protocol_sap", page=related["physical_page"],
            paragraph=related["original_quote"], url=source.url,
        )
        text = extract_locator_quote(
            source.content_text, media_type="application/pdf", locator=related_locator,
        )
        if text != related["original_quote"].strip():
            raise ValueError("Related native clause changed")
        return SourceClauseReference(
            reference_id=proposal_id, source_id=source.source_id,
            label_zh=related["provisional_chinese_label"],
            locator=related_locator, original_text=text,
        )
    deferred = []
    mapped = []
    for atom in proposal["atoms"]:
        document = documents[atom["document_filename"]]
        trial = atom["trial_id"].casefold()
        clause_source = pdf_sources.get((atom["document_raw_sha256"], atom["physical_page"]))
        if (
            clause_source is None
            or trial not in trial_products
            or clause_source.query_or_identifier.casefold() != trial
            or document["trial_id"].casefold() != trial
            or document["url"] != clause_source.url
        ):
            raise ValueError("PDF clause does not match its native page, trial and source")
        locator = EvidenceLocator(
            document_role="protocol_sap",
            page=atom["physical_page"],
            paragraph=atom["original_quote"],
            url=clause_source.url,
        )
        quote = extract_locator_quote(
            clause_source.content_text, media_type="application/pdf", locator=locator
        )
        # Match the existing ResearchFact/native-materializer outer-whitespace
        # boundary; internal source line breaks must remain byte-exact.
        if quote != atom["original_quote"].strip():
            raise ValueError("Native clause quote changed")
        field = atom["c_field_mapping"]["field_id"]
        is_statistical = (
            atom["design_field_family"] == "statistical" and field in _STATISTICAL_FIELDS
        )
        # A prose plan is not an exact enrolled N. Keep cohort/completer/repeat
        # conditions together with their source scope, without number extraction
        # or changing the separately registered ACTUAL count.
        is_sample_terms = (
            atom["design_field_family"] == "sample_size" and field == "sample_size"
        )
        if not (is_statistical or is_sample_terms):
            deferred.append(
                {
                    "proposal_id": atom["proposal_id"],
                    "reason": "not_in_this_statistics_and_sample_terms_extension",
                    "source_id": clause_source.source_id,
                    "locator": locator.model_dump(mode="json"),
                }
            )
            continue
        anchor = atom["anchor"]
        related_context = []
        for relation_id in atom["conflict_links"]:
            relation = relations_by_id[relation_id]
            if (relation["trial_id"].casefold() != trial
                    or atom["proposal_id"] not in relation["linked_atoms"]):
                raise ValueError("Source relation does not explicitly bind this clause")
            related_ids = tuple(dict.fromkeys(
                relation["linked_atoms"] + relation.get("related_context_atoms", [])
            ))
            related_context.append(SourceClauseRelation(
                relation_id=relation_id, status=relation["status"],
                description=relation["description"],
                references=tuple(reference(item) for item in related_ids),
            ))
        continuation = atom.get("multi_page_link")
        scope_note = "仅适用于本条原文指明的人群、指标及章节；不能扩为全研究统一规则。"
        if atom["proposal_id"].endswith("prot-p62-efficacy-analysis-part2"):
            scope_note = (
                "无填补约定仅限方案§12.4的FACIT/PD探索性疗效段落；"
                "不适用于§12.5安全性、PK/PD定量限、AE日期或合并用药日期规则。"
                "探索性分析输出是同段另一项说明，不构成填补或检验结论。"
            )
        clause_context = SourceClauseContext(
            label_zh=atom["provisional_chinese_label"], scope_note_zh=scope_note,
            scientific_scope=atom.get("scientific_scope", {}),
            continuations=(reference(continuation),) if continuation else (),
            relations=tuple(related_context),
        )
        observations.append(
            DesignObservation(
                row_id="c-pdf-" + atom["proposal_id"],
                source_row_id=atom["proposal_id"],
                observation_id="c-pdf-observation-" + atom["proposal_id"],
                product_id=trial_products[trial],
                trial_id=trial,
                cohort_id=f"cohort-{trial}-source-clause",
                group_id=f"group-{trial}-source-clause",
                field_family=(DesignFieldFamily.SAMPLE_SIZE if is_sample_terms
                              else DesignFieldFamily.STATISTICAL),
                field="planned_sample_size_terms" if is_sample_terms else field,
                source_field_name=anchor,
                source_field_definition=anchor,
                source_text=quote,
                source_clause_context=clause_context,
                source_version_id=clause_source.source_id,
                source_locator=locator,
                source_role=SourceRole.PROTOCOL_SAP,
                disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
                review_state=FactReviewState.CANDIDATE,
                disclosure_state=FactDisclosureState.REPORTED_VALUE,
                conflict_disposition=(
                    ConflictDisposition.OPEN_CONFLICT_PRESERVED
                    if atom["conflict_links"]
                    else ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
                ),
                compatibility_rule=(
                    "native-pdf-planned-sample-terms-v1+scope-as-printed"
                    if is_sample_terms else "native-pdf-statistical-clause-v1+scope-as-printed"
                ),
                difference_labels_zh=(("来源表述存在未决差异",) if atom["conflict_links"] else ()),
            )
        )
        mapped.append(atom["proposal_id"])
    if not mapped:
        raise ValueError("No supported statistical clauses were present")
    report = ReportCPortalData.model_validate(
        {
            **base.model_dump(mode="json"),
            "report_version": "native-pdf-statistics-and-sample-terms-v2",
            "data_cutoff": contract.data_cutoff,
            "observations": observations,
        }
    )
    facts = research_facts_from_c_observations(
        report.observations,
        sources=tuple(captures.values()),
        trial_names={row.id: row.name for row in report.trials},
    )
    claims = tuple(
        ResearchClaim(
            claim_id=stable_id("c-native-extension-claim", fact.fact_id),
            claim_text=fact.original_text,
            claim_kind="direct_evidence",
            fact_ids=(fact.fact_id,),
        )
        for fact in facts
    )
    report_raw = report.model_dump_json().encode()
    content_digest = _digest(report_raw + b"\n" + proposal_raw)
    output.mkdir(parents=True, exist_ok=False)
    root = output / "project"
    create_project_workspace(root, contract)
    store = ContentAddressedStore(root)
    store.put_bytes(proposal_raw, media_type="application/json")
    for source_id, source in captures.items():
        origin = ContentAddressedStore(source_roots[source_id])
        if source.text_derivation is None:  # preflight guarantees this
            raise ValueError("Source lost its raw proof")
        assets = [source.text_derivation.raw_asset]
        if source.public_pdf_availability is not None:
            receipt = source.public_pdf_availability.receipt_asset
            if receipt is None:
                raise ValueError("Source lost its persisted current-GET receipt")
            assets.append(receipt)
        for asset in assets:
            if store.put_bytes(origin.read_bytes(asset), media_type=asset.media_type) != asset:
                raise ValueError("Copied source asset differs from its pinned identity")
    lineage = ingest_research_evidence(
        project_root=root,
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        report_kind="C",
        data_cutoff=contract.data_cutoff,
        scientific_content_digest=content_digest,
        created_at=observed_at,
        sources=tuple(captures.values()),
        route_attempts=(),
        facts=facts,
        claims=claims,
    )
    registered = register_c_source_consumers(
        root,
        lineage.evidence_snapshot,
        report,
        dict(lineage.fact_version_by_ref),
        captures,
        registered_at=observed_at,
    )
    site = root / "reports/C/review-candidate/html"
    pages = render_report_c_review_candidate(
        report,
        site,
        publication_limitation_zh=(
            "仅为两项研究的待复核设计先例，不代表完整竞品宇宙；产品对应关系待审。"
            "方案/SAP原文已逐页定位，首次公开日期未知，仅证明本次官网可得，不能倒推历史。"
            "统计条款按原文范围并列；未决差异不自动选赢家，其他条款及来源缺口仍待接入。"
        ),
    )
    (output / "review-portal-data.json").write_bytes(report_raw)
    readable_review_sha256 = _write_readable_review(output, captures, observations)
    result: dict[str, Any] = {
        "schema_version": "c-native-pdf-statistics-and-sample-terms-v2",
        "scientific_acceptance": False,
        "current_generation_switched": False,
        "registry_manifest_sha256": registry_sha256,
        "pdf_manifest_sha256": pdf_sha256,
        "observed_at": observed_at.isoformat(),
        "data_cutoff": contract.data_cutoff.isoformat(),
        "observations": len(observations),
        "registered_consumers": len(registered),
        "original_clause_count": len(ids),
        "mapped_clause_ids": mapped,
        "deferred_clauses": deferred,
        "source_proposal_asset": proposal_asset.model_dump(mode="json"),
        "snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
        "fact_version_by_ref": dict(lineage.fact_version_by_ref),
        "scientific_content_digest": content_digest,
        "report_data_sha256": _digest(report_raw),
        "readable_review_sha256": readable_review_sha256,
        "site_relative_path": site.relative_to(output).as_posix(),
        "html_sha256": {
            page.relative_to(site).as_posix(): _digest(page.read_bytes()) for page in pages
        },
        "site_file_sha256": {
            path.relative_to(site).as_posix(): _digest(path.read_bytes())
            for path in sorted(site.rglob("*")) if path.is_file()
        },
        "code_sha256": _digest(Path(__file__).read_bytes()),
        "limitations": [
            "Mapped statistics and planned terms are not independent scientific acceptance",
            "Qualified plans do not supply exact scalar N or replace ACTUAL registry counts",
            "No critical endpoint/timepoint slots filled by these PDF clauses",
            "Native source scope, all conflicts/gaps, and deferred clauses remain in proposal",
        ],
    }
    (output / "candidate-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-root", type=Path, required=True)
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--registry-sha256", required=True)
    parser.add_argument("--pdf-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = extend_candidate(**vars(args), observed_at=datetime.now(UTC))
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "observations",
                    "registered_consumers",
                    "scientific_acceptance",
                    "current_generation_switched",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
