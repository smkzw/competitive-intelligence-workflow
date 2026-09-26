"""Persist an exact CT.gov A source candidate without accepting or publishing it.

The input is a fixed, previously built A payload plus its row-source sidecar.
Offline CAS replay is explicitly not a live source check or an as-of history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import (
    CtgovARowSourceRef,
    CtgovAtomicResult,
    ResearchClaim,
    ResearchFact,
    SourceCapture,
    build_ctgov_a_outcome_candidate_batch,
    build_ctgov_a_safety_candidate_batch,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.public_provenance import PublicProvenance, PublicSource
from ci_workflow.qc.browser import site_directory_digest
from ci_workflow.renderers.portal.report_a import (
    AdditionalObservationRow,
    ReportAPortalData,
    render_report_a_site,
)
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.snapshot_store import SnapshotStore
from tools.audit_ctgov_a_source_map import audit


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _extra_facts(
    rows: tuple[AdditionalObservationRow, ...],
    sources: dict[str, SourceCapture],
    page_hashes: dict[str, str],
) -> tuple[tuple[ResearchFact, ...], tuple[ResearchClaim, ...]]:
    """Keep other-domain source atoms; do not invent an A/B/C numeric consumer."""
    atoms_by_trial_path: dict[tuple[str, str | None], CtgovAtomicResult] = {}
    for trial_id in {row.trial_id for row in rows}:
        source = sources[trial_id]
        atoms, _issues = extract_ctgov_atomic_results(source)
        for atom in atoms:
            key = (trial_id, atom.value_locator.field_path)
            if key in atoms_by_trial_path:
                raise ValueError(f"{trial_id}: duplicate source atom path")
            atoms_by_trial_path[key] = atom
    facts: list[ResearchFact] = []
    claims: list[ResearchClaim] = []
    for row in rows:
        source = sources[row.trial_id]
        matched_atom = atoms_by_trial_path.get((row.trial_id, row.source_path))
        if matched_atom is None or not (
            page_hashes[row.trial_id] == row.source_page_sha256
            and row.source_url == source.url
            and row.domain == matched_atom.domain
            and row.group_id == matched_atom.group_id
            and row.group_title == matched_atom.group_title
            and row.endpoint == matched_atom.endpoint
            and row.class_title == matched_atom.class_title
            and row.category_title == matched_atom.category_title
            and row.time_window in {matched_atom.timepoint, matched_atom.observation_timepoint}
            and row.raw_value == matched_atom.value_quote
            and row.raw_value_type == matched_atom.raw_value_type
            and row.raw_unit == matched_atom.raw_unit
        ):
            raise ValueError(f"{row.row_id}: other-domain observation/source identity conflict")
        source_facts = research_facts_from_ctgov_atom(matched_atom)
        facts.extend(source_facts)
        claims.append(ResearchClaim(
            claim_id=stable_id("ctgov-other-domain-claim", row.row_id,
                               *(fact.fact_id for fact in source_facts)),
            claim_text="登记原始其他领域观察；未纳入疗效或安全性数值共轴",
            claim_kind="direct_evidence",
            fact_ids=tuple(fact.fact_id for fact in source_facts),
        ))
    return tuple(facts), tuple(claims)


def materialize(
    *, project_root: Path, cas_dir: Path, payload_path: Path,
    sidecar_path: Path, observed_at: datetime,
    selected_trials: set[str] | None = None,
    preview_site: Path | None = None,
) -> dict[str, Any]:
    """Recheck row bytes, ingest only exact candidates, retain unresolved counts."""
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("offline replay observation time requires an explicit offset")
    if preview_site is not None:
        destination = preview_site.resolve()
        if not destination.is_relative_to(project_root.resolve()) or destination.exists():
            raise ValueError("preview site must be a new directory inside the project")
    workspace = verify_project_workspace(project_root)
    if "A" not in {kind.value for kind in workspace.contract.reports}:
        raise ValueError("project contract does not include report A")
    payload_bytes = payload_path.read_bytes()
    sidecar_bytes = sidecar_path.read_bytes()
    report = ReportAPortalData.model_validate_json(payload_bytes)
    if (
        report.indication != workspace.contract.indication
        or report.data_cutoff > workspace.contract.data_cutoff
    ):
        raise ValueError("candidate indication or data cutoff conflicts with project")
    sidecar = json.loads(sidecar_bytes)
    rows_by_trial: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in sidecar["row_source_map"]:
        rows_by_trial[str(entry["trial_id"])].append(entry)
    selected = set(rows_by_trial) if selected_trials is None else selected_trials
    if not selected or selected - rows_by_trial.keys():
        raise ValueError("selected trials must occur in the source sidecar")

    # The diagnostic validates the entire payload/sidecar row set, then reopens
    # every selected raw path and requires exact original JSON value and type.
    diagnostic = audit(cas_dir, payload_path, sidecar_path, selected_trials=selected)
    store = ContentAddressedStore(project_root)
    sources: dict[str, SourceCapture] = {}
    page_hashes: dict[str, str] = {}
    refs: dict[str, CtgovARowSourceRef] = {}
    for trial_id in sorted(selected):
        entries = rows_by_trial[trial_id]
        hashes = {str(entry["source_page_sha256"]) for entry in entries}
        if len(hashes) != 1:
            raise ValueError(f"{trial_id}: source page ambiguity")
        page_hash = next(iter(hashes))
        page = (cas_dir / "evidence/raw/sha256" / page_hash[:2]
                / f"{page_hash}.bin")
        page_bytes = page.read_bytes()
        if _sha256(page_bytes) != page_hash:
            raise ValueError(f"{trial_id}: raw page digest mismatch")
        raw_asset = store.put_bytes(page_bytes, media_type="application/json")
        study = derive_saved_ctgov_record(
            project_root, raw_asset, trial_id.upper(), replayed_at=observed_at,
        )
        sources[trial_id] = source_capture_from_ctgov_study(project_root, study)
        page_hashes[trial_id] = page_hash
        for entry in entries:
            if entry["domain"] not in {"efficacy", "safety"}:
                continue
            ref = CtgovARowSourceRef(
                row_id=entry["row_id"], trial_id=trial_id,
                source_page_sha256=page_hash, value_path=entry["value_path"],
                raw_class_title=entry.get("class_title"),
                raw_category_title=entry.get("category_title"),
                display_population=entry.get("display_population"),
            )
            if ref.row_id in refs:
                raise ValueError(f"duplicate candidate row reference: {ref.row_id}")
            refs[ref.row_id] = ref

    efficacy = tuple(row for row in report.efficacy if row.trial_id in selected)
    safety = tuple(row for row in report.safety if row.trial_id in selected)
    other = tuple(row for row in report.additional_observations if row.trial_id in selected)
    captures = tuple(sources[trial_id] for trial_id in sorted(selected))
    outcomes = build_ctgov_a_outcome_candidate_batch(
        captures, efficacy, row_source_refs=tuple(refs[row.row_id] for row in efficacy),
    )
    safety_batch = build_ctgov_a_safety_candidate_batch(
        captures, safety, row_source_refs=tuple(refs[row.row_id] for row in safety),
    )
    extra_facts, extra_claims = _extra_facts(other, sources, page_hashes)
    facts = (*outcomes.facts, *safety_batch.facts, *extra_facts)
    claims = (*outcomes.claims, *safety_batch.claims, *extra_claims)
    if len({fact.fact_id for fact in facts}) != len(facts):
        raise ValueError("one source atom was reused across candidate display rows")
    if len({claim.claim_id for claim in claims}) != len(claims):
        raise ValueError("candidate claim identities collide")
    if not facts or not claims:
        raise ValueError("selected sources have no verifiable candidate facts")
    unresolved = [
        {"row_id": gap.row_id, "reason": gap.reason} for gap in outcomes.gaps
    ] + [
        {"row_id": gap.row_id, "reason": gap.reason} for gap in safety_batch.gaps
    ]
    content_digest = _sha256(json.dumps({
        "payload": _sha256(payload_bytes), "sidecar": _sha256(sidecar_bytes),
        "trials": sorted(selected), "fact_ids": sorted(fact.fact_id for fact in facts),
        "claim_ids": sorted(claim.claim_id for claim in claims),
    }, sort_keys=True, separators=(",", ":")).encode())
    lineage = ingest_research_evidence(
        project_root=project_root, project_id=workspace.contract.project_id,
        contract_version=workspace.contract.contract_version, report_kind="A",
        data_cutoff=report.data_cutoff, scientific_content_digest=content_digest,
        created_at=observed_at, sources=captures, route_attempts=(),
        facts=facts, claims=claims,
        request_id=stable_id("r24-fixed-cas-candidate", workspace.contract.project_id,
                             content_digest),
    )
    locked_content = SnapshotStore(project_root).read(lineage.evidence_snapshot)
    source_version_by_id = {
        entry["capture"]["source_id"]: entry["source_version_id"]
        for entry in locked_content["closure"]["sources"]
    }
    preview: dict[str, object] | None = None
    if preview_site is not None:
        destination = preview_site.resolve()
        if not destination.is_relative_to(project_root.resolve()) or destination.exists():
            raise ValueError("preview site must be a new directory inside the project")
        bound_efficacy = {row.row_id: row for row in outcomes.bound_rows}
        bound_safety = {row.row_id: row for row in safety_batch.bound_rows}
        bound_report = ReportAPortalData.model_validate({
            **report.model_dump(mode="json"),
            "efficacy": [
                bound_efficacy.get(row.row_id, row).model_dump(mode="json")
                for row in report.efficacy
            ],
            "safety": [
                bound_safety.get(row.row_id, row).model_dump(mode="json")
                for row in report.safety
            ],
        })
        provenance = PublicProvenance(
            evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
            report_data_digest=_sha256(bound_report.model_dump_json().encode()),
            sources=tuple(
                PublicSource(
                    source_version_id=source_version_by_id[source.source_id],
                    label=source.title, url=source.url, source_type="临床试验登记",
                    published_at=(source.published_at.date().isoformat()
                                  if source.published_at else "未知（来源未明确公开）"),
                    data_cutoff=report.data_cutoff.date().isoformat(),
                    limitation="离线固定来源开发候选；此处不是独立医学复核或发布依据。",
                ) for source in captures
            ),
        )
        pages = render_report_a_site(
            bound_report, destination,
            public_provenance=provenance,
            publication_limitation_zh=(
                "开发候选：固定登记页离线重放；尚未完成动态状态核查、中国来源、"
                "关键论文、组别产品归属和独立医学复核，不可作为正式结论。"
            ),
        )
        site_digest, site_bytes = site_directory_digest(destination)
        preview = {
            "relative_path": destination.relative_to(project_root.resolve()).as_posix(),
            "sha256": site_digest, "bytes": site_bytes, "pages": len(pages),
            "bound_report_data_sha256": provenance.report_data_digest,
        }
    issues = {
        (issue.source_id, issue.result_key, issue.category, issue.status,
         issue.source_path): issue
        for issue in (*outcomes.source_issues, *safety_batch.source_issues)
    }
    return {
        "schema_version": "r24-21-candidate-1",
        "status": "ingested_candidate_not_reviewed_or_current",
        "project_id": workspace.contract.project_id,
        "source_access_method": "offline_cas_replay",
        "observed_at": observed_at.isoformat(),
        "payload_sha256": _sha256(payload_bytes),
        "sidecar_sha256": _sha256(sidecar_bytes),
        "source_pages": page_hashes,
        "source_version_by_source_id": source_version_by_id,
        "selected_trials": sorted(selected),
        "raw_paths_verified": diagnostic["raw_paths_verified_in_selected_trials"],
        "bound_efficacy_rows": [row.row_id for row in outcomes.bound_rows],
        "bound_safety_rows": [row.row_id for row in safety_batch.bound_rows],
        "other_domain_source_rows_without_portal_binding": [row.row_id for row in other],
        "binding_gaps": unresolved,
        "fact_bindings": [
            {"row_ref": fact.row_ref, "fact_version_id":
             lineage.fact_version_by_ref[fact.fact_id]}
            for fact in facts
        ],
        "source_issues": [
            {"source_id": item.source_id, "trial_id": item.trial_id,
             "result_key": item.result_key,
             "category": item.category, "status": item.status,
             "source_path": item.source_path, "reason_zh": item.reason_zh}
            for item in sorted(issues.values(), key=lambda issue: issue.source_path)
        ],
        "source_issue_statuses": dict(Counter(item.status for item in issues.values())),
        "source_version_ids": list(lineage.source_version_ids),
        "fact_version_ids": list(lineage.fact_version_ids),
        "claim_version_ids": list(lineage.claim_version_ids),
        "snapshot_id": lineage.evidence_snapshot.snapshot_id,
        "snapshot_sha256": lineage.evidence_snapshot.sha256,
        "snapshot_relative_path": lineage.evidence_snapshot.relative_path,
        "preview_site": preview,
        "counts": {
            "sources": len(captures), "facts": len(lineage.fact_version_ids),
            "claims": len(lineage.claim_version_ids), "other_rows": len(other),
            "binding_gaps": len(unresolved), "source_issues": len(issues),
        },
        "limits": [
            "No independent scientific review, current delivery switch, or release gate was run.",
            "Offline replay is not a new live status check or historical-as-of reconstruction.",
            "Other-domain source facts have no A/B/C portal consumer binding yet.",
            "Unknown arm-product relations, China sources and required publications remain open.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--cas-dir", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--sidecar", required=True, type=Path)
    parser.add_argument("--observed-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--trial", action="append", default=[])
    parser.add_argument("--preview-site", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output exists; choose a new versioned receipt path")
    result = materialize(
        project_root=args.project, cas_dir=args.cas_dir,
        payload_path=args.payload, sidecar_path=args.sidecar,
        observed_at=args.observed_at,
        selected_trials={value.casefold() for value in args.trial} if args.trial else None,
        preview_site=args.preview_site,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print(json.dumps({"status": result["status"], **result["counts"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
