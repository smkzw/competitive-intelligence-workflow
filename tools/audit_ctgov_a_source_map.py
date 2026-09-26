"""Replay an A candidate's row locators against captured CT.gov pages.

The result is a development diagnostic. It never accepts a report, ingests a
fact version, refreshes a live source, or changes the current generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.source_research_service import (
    CtgovARowSourceRef,
    build_ctgov_a_outcome_candidate_batch,
    build_ctgov_a_safety_candidate_batch,
    source_capture_from_ctgov_study,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import source_json_decoder


def _raw_at_path(record: dict[str, Any], path: str) -> object:
    if not path.startswith("$.resultsSection.") or "*" in path:
        raise ValueError("non-exact registry result path")
    value: object = record
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path[2:]):
        if part.startswith("["):
            if not isinstance(value, list):
                raise ValueError("path array mismatch")
            value = value[int(part[1:-1])]
        else:
            if not isinstance(value, dict):
                raise ValueError("path object mismatch")
            value = value[part]
    return value


def audit(
    cas_dir: Path, payload_path: Path, sidecar_path: Path,
    *, selected_trials: set[str] | None = None,
) -> dict[str, Any]:
    payload_bytes = payload_path.read_bytes()
    sidecar_bytes = sidecar_path.read_bytes()
    payload = json.loads(payload_bytes)
    sidecar = json.loads(sidecar_bytes)
    report = ReportAPortalData.model_validate(payload)
    entries = sidecar["row_source_map"]
    by_trial: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mapped_keys: set[tuple[str, str]] = set()
    for entry in entries:
        key = (entry["domain"], entry["row_id"])
        if key in mapped_keys:
            raise ValueError(f"duplicate row source reference: {key}")
        mapped_keys.add(key)
        by_trial[entry["trial_id"]].append(entry)
    displayed_keys = {
        *(('efficacy', row.row_id) for row in report.efficacy),
        *(('safety', row.row_id) for row in report.safety),
        *(('additional_observations', row['row_id'])
          for row in payload.get('additional_observations', [])),
    }
    if mapped_keys != displayed_keys:
        raise ValueError(
            f"row source map coverage differs: missing={len(displayed_keys - mapped_keys)}, "
            f"extra={len(mapped_keys - displayed_keys)}"
        )
    if selected_trials is not None and selected_trials - by_trial.keys():
        raise ValueError("requested trial has no mapped row")

    by_domain = Counter(entry["domain"] for entry in entries)
    per_trial: list[dict[str, Any]] = []
    raw_verified = 0
    bound_efficacy = bound_safety = 0
    gap_reasons: Counter[str] = Counter()
    source_issue_statuses: Counter[str] = Counter()
    source_issue_count = 0
    trials = sorted(selected_trials if selected_trials is not None else by_trial)
    with tempfile.TemporaryDirectory(prefix="r24-source-audit-", dir=payload_path.parent) as temp:
        temp_root = Path(temp)
        store = ContentAddressedStore(temp_root)
        for trial_id in trials:
            trial_entries = by_trial[trial_id]
            page_digests = {entry["source_page_sha256"] for entry in trial_entries}
            if len(page_digests) != 1:
                raise ValueError(f"{trial_id}: source page ambiguity")
            page_digest = next(iter(page_digests))
            page = (cas_dir / "evidence/raw/sha256" / page_digest[:2]
                    / f"{page_digest}.bin")
            page_bytes = page.read_bytes()
            if hashlib.sha256(page_bytes).hexdigest() != page_digest:
                raise ValueError(f"{trial_id}: source page bytes drifted")
            blob = store.put_bytes(page_bytes, media_type="application/json")
            replayed = derive_saved_ctgov_record(
                temp_root, blob, trial_id.upper(), replayed_at=datetime.now(UTC),
            )
            source = source_capture_from_ctgov_study(temp_root, replayed)
            record = source_json_decoder().decode(source.content_text)
            if not isinstance(record, dict):
                raise ValueError(f"{trial_id}: source record not an object")
            refs: dict[str, CtgovARowSourceRef] = {}
            for entry in trial_entries:
                raw = _raw_at_path(record, entry["value_path"])
                if raw != entry["raw_value"] or type(raw).__name__ != entry["raw_value_type"]:
                    raise ValueError(f"{trial_id}:{entry['row_id']}: raw source mismatch")
                raw_verified += 1
                refs[entry["row_id"]] = CtgovARowSourceRef(
                    row_id=entry["row_id"], trial_id=trial_id,
                    source_page_sha256=page_digest, value_path=entry["value_path"],
                    raw_class_title=entry.get("class_title"),
                    raw_category_title=entry.get("category_title"),
                    display_population=entry.get("display_population"),
                )
            efficacy = tuple(row for row in report.efficacy if row.trial_id == trial_id)
            safety = tuple(row for row in report.safety if row.trial_id == trial_id)
            outcome = build_ctgov_a_outcome_candidate_batch(
                (source,), efficacy, row_source_refs=tuple(refs[row.row_id] for row in efficacy),
            )
            safety_batch = build_ctgov_a_safety_candidate_batch(
                (source,), safety, row_source_refs=tuple(refs[row.row_id] for row in safety),
            )
            bound_efficacy += len(outcome.bound_rows)
            bound_safety += len(safety_batch.bound_rows)
            gap_reasons.update(gap.reason for gap in outcome.gaps)
            gap_reasons.update(gap.reason for gap in safety_batch.gaps)
            source_issue_count += len(outcome.source_issues)
            source_issue_statuses.update(issue.status for issue in outcome.source_issues)
            per_trial.append({
                "trial_id": trial_id,
                "source_page_sha256": page_digest,
                "efficacy_rows": len(efficacy),
                "efficacy_bound_candidates": len(outcome.bound_rows),
                "safety_rows": len(safety),
                "safety_bound_candidates": len(safety_batch.bound_rows),
                "additional_observations_paths_only": sum(
                    entry["domain"] == "additional_observations" for entry in trial_entries
                ),
                "binding_gaps": [
                    {"row_id": gap.row_id, "reason": gap.reason}
                    for gap in outcome.gaps
                ] + [
                    {"row_id": gap.row_id, "reason": gap.reason}
                    for gap in safety_batch.gaps
                ],
                "source_coverage_issues": len(outcome.source_issues),
                "source_issue_details": [
                    {"category": issue.category, "status": issue.status,
                     "source_path": issue.source_path, "reason_zh": issue.reason_zh}
                    for issue in outcome.source_issues
                ],
            })
    return {
        "status": "development_candidate_not_source_closure",
        "source_access_method": "offline_cas_replay",
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "sidecar_sha256": hashlib.sha256(sidecar_bytes).hexdigest(),
        "selected_trials": trials,
        "mapped_total_rows": len(entries),
        "mapped_by_domain": dict(by_domain),
        "raw_paths_verified_in_selected_trials": raw_verified,
        "efficacy_bound_candidates": bound_efficacy,
        "safety_bound_candidates": bound_safety,
        "binding_gap_reasons": dict(gap_reasons),
        "source_coverage_issues": source_issue_count,
        "source_issue_statuses": dict(source_issue_statuses),
        "per_trial": per_trial,
        "limits": [
            "A candidate binding is not an ingested or independently accepted fact version.",
            "Additional observations have raw paths but no A/B/C consumer binding in this audit.",
            "Product/arm unknown relationships and parser issues remain separate blockers.",
            "Offline replay is neither a live status check nor historical-as-of reconstruction.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cas-dir", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--sidecar", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--trial", action="append", default=[])
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new versioned receipt path")
    result = audit(
        args.cas_dir, args.payload, args.sidecar,
        selected_trials={item.casefold() for item in args.trial} if args.trial else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        key: result[key] for key in (
            "mapped_total_rows", "raw_paths_verified_in_selected_trials",
            "efficacy_bound_candidates", "safety_bound_candidates",
            "binding_gap_reasons", "source_coverage_issues",
        )
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
