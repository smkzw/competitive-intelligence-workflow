"""Read-only, fail-closed candidate bridge for an old A row and refreshed source.

This tool does not migrate a fact, rebuild a report, or change the current
generation. An exact JSON path is only a candidate when its scientific atom is
unchanged; user edits still need an explicit three-way source comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from tools import audit_a_payload_drift

SOURCE_DOMAIN_BY_COLLECTION = {
    "efficacy": "efficacy",
    "safety": "safety",
    "observations": "additional_observations",
}


class BridgeAuditError(ValueError):
    """Inputs cannot support a safe, read-only candidate assessment."""


def _source_rows(sidecar: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    rows = sidecar.get("row_source_map")
    if not isinstance(rows, list):
        raise BridgeAuditError(f"{label} missing row_source_map")
    by_id: dict[str, dict[str, Any]] = {}
    known_fields = set(audit_a_payload_drift.ATOM_FIELDS) | {
        "trial_id", "value_path", "source_page_sha256", "source_url", "row_id",
    }
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("row_id"), str):
            raise BridgeAuditError(f"{label} source row missing row_id")
        extra = set(row) - known_fields
        if extra:
            raise BridgeAuditError(
                f"{label} unknown source atom field: {','.join(sorted(extra))}"
            )
        row_id = row["row_id"]
        if not row_id:
            raise BridgeAuditError(f"{label} source row missing row_id")
        if row_id in by_id:
            raise BridgeAuditError(f"duplicate {label} row_id: {row_id}")
        by_id[row_id] = row
    return by_id


def read_current_bindings(
    database_path: Path,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    """Read the selected generation and verified consumers without SQLite writes."""
    path = database_path.resolve(strict=True)
    if path.with_name(path.name + "-wal").exists():
        raise BridgeAuditError("active SQLite WAL: immutable read might omit current state")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as database:
        database.row_factory = sqlite3.Row
        selected = database.execute(
            "SELECT revision,generation_sha256 FROM current_delivery_state"
        ).fetchall()
        if len(selected) != 1:
            raise BridgeAuditError("expected exactly one current generation")
        current = {"revision": int(selected[0]["revision"]),
                   "generation_sha256": str(selected[0]["generation_sha256"])}
        generation_rows = database.execute(
            "SELECT bundle_json FROM current_delivery_generations WHERE generation_sha256=?",
            (current["generation_sha256"],),
        ).fetchall()
        if len(generation_rows) != 1:
            raise BridgeAuditError("selected generation payload is missing or ambiguous")
        generation_text = str(generation_rows[0]["bundle_json"])
        if hashlib.sha256(generation_text.encode()).hexdigest() != current["generation_sha256"]:
            raise BridgeAuditError("selected generation digest mismatch")
        try:
            generation = json.loads(generation_text)
        except json.JSONDecodeError as error:
            raise BridgeAuditError("selected generation is not JSON") from error
        if not isinstance(generation, dict) or not isinstance(
            generation.get("active_fact_version_ids"), list
        ) or not all(isinstance(item, str) for item in generation["active_fact_version_ids"]):
            raise BridgeAuditError("selected generation has no typed active fact set")
        active_versions = set(generation["active_fact_version_ids"])
        all_bindings = [
            {key: str(row[key]) for key in (
                "source_fact_version_id", "evidence_snapshot_id", "report", "collection",
                "row_id",
            )}
            for row in database.execute(
                "SELECT source_fact_version_id,evidence_snapshot_id,report,collection,row_id "
                "FROM source_portal_consumer_bindings "
                "ORDER BY report,collection,row_id,source_fact_version_id"
            )
        ]
        all_edits = [
            {key: str(row[key]) for key in (
                "target_fact_version_id", "result_fact_version_id"
            )}
            for row in database.execute(
                "SELECT target_fact_version_id,result_fact_version_id "
                "FROM user_fact_edit_requests WHERE status='complete' "
                "ORDER BY target_fact_version_id,result_fact_version_id"
            )
        ]
        descendants: dict[str, set[str]] = {}
        for edit in all_edits:
            descendants.setdefault(edit["target_fact_version_id"], set()).add(
                edit["result_fact_version_id"]
            )

        def is_active_lineage(version_id: str) -> bool:
            pending = [version_id]
            visited: set[str] = set()
            while pending:
                candidate = pending.pop()
                if candidate in active_versions:
                    return True
                if candidate in visited:
                    continue
                visited.add(candidate)
                pending.extend(descendants.get(candidate, ()))
            return False

        bindings = [binding for binding in all_bindings
                    if is_active_lineage(binding["source_fact_version_id"])]
        supersedes_children: dict[str, set[str]] = {}
        for row in database.execute(
            "SELECT fact_version_id,supersedes_fact_version_id FROM fact_versions "
            "WHERE supersedes_fact_version_id IS NOT NULL"
        ):
            supersedes_children.setdefault(str(row["supersedes_fact_version_id"]), set()).add(
                str(row["fact_version_id"])
            )
        for binding in all_bindings:
            source_version = binding["source_fact_version_id"]
            if is_active_lineage(source_version):
                continue
            pending_versions = [source_version]
            visited_versions: set[str] = set()
            while pending_versions:
                version = pending_versions.pop()
                if version in active_versions:
                    raise BridgeAuditError(
                        "non-edit supersedes reaches an active bound fact; "
                        "three-way source lineage needs explicit review"
                    )
                if version in visited_versions:
                    continue
                visited_versions.add(version)
                pending_versions.extend(descendants.get(version, ()))
                pending_versions.extend(supersedes_children.get(version, ()))
        bound_sources = {binding["source_fact_version_id"] for binding in bindings}
        linked_versions = set(bound_sources)
        pending = list(bound_sources)
        while pending:
            for child in descendants.get(pending.pop(), ()):
                if child not in linked_versions:
                    linked_versions.add(child)
                    pending.append(child)
        edits = [edit for edit in all_edits
                 if edit["target_fact_version_id"] in linked_versions
                 and is_active_lineage(edit["result_fact_version_id"])]
    if path.with_name(path.name + "-wal").exists():
        raise BridgeAuditError("active SQLite WAL appeared during immutable read")
    return current, bindings, edits


def assess_refresh_bridge(
    old_sidecar: dict[str, Any],
    new_sidecar: dict[str, Any],
    bindings: list[dict[str, str]],
    edits: list[dict[str, str]],
    current: dict[str, Any],
    *,
    expected_generation_sha256: str,
) -> dict[str, Any]:
    """Assess only bound rows; never infer source identity from titles or order."""
    if current.get("generation_sha256") != expected_generation_sha256:
        raise BridgeAuditError("current generation changed; re-open the project")
    before = _source_rows(old_sidecar, "old")
    _source_rows(new_sidecar, "new")
    try:
        delta = audit_a_payload_drift.audit_row_source_maps(old_sidecar, new_sidecar)
    except ValueError as error:
        raise BridgeAuditError(str(error)) from error
    pairs = {str(item["old_row_id"]): item for item in delta["pairs"]}
    assessment: list[dict[str, Any]] = []
    counts = {"a_exact_path_candidates": 0, "a_source_changed_review": 0,
              "a_unresolved": 0, "other_reports_rebuild_required": 0,
              "user_edits_requiring_three_way_merge": 0}
    for binding in bindings:
        report = binding["report"]
        expected_domain = SOURCE_DOMAIN_BY_COLLECTION.get(binding["collection"])
        if expected_domain is None:
            raise BridgeAuditError(f"unknown consumer collection: {binding['collection']}")
        item: dict[str, Any] = {**binding, "new_row_id": None,
                                "source_page_changed": None}
        if report != "A":
            item["status"] = "report_rebuild_required"
            counts["other_reports_rebuild_required"] += 1
        elif (binding["row_id"] not in before or
              before[binding["row_id"]].get("domain") != expected_domain):
            item["status"] = "old_source_row_unresolved"
            counts["a_unresolved"] += 1
        else:
            pair = pairs.get(binding["row_id"])
            if pair is None:
                item["status"] = "source_withdrawn_or_path_changed_review"
                counts["a_unresolved"] += 1
            elif pair["changed_fields"]:
                item["status"] = "source_changed_review"
                item["changed_fields"] = pair["changed_fields"]
                counts["a_source_changed_review"] += 1
            else:
                item["status"] = "exact_path_candidate_not_accepted"
                item["new_row_id"] = pair["new_row_id"]
                item["source_page_changed"] = pair["source_page_changed"]
                counts["a_exact_path_candidates"] += 1
        assessment.append(item)
    edited: list[dict[str, Any]] = []
    edit_parents: dict[str, set[str]] = {}
    for edit in edits:
        edit_parents.setdefault(edit["result_fact_version_id"], set()).add(
            edit["target_fact_version_id"]
        )
    for edit in edits:
        target = edit["target_fact_version_id"]
        ancestors = {target}
        pending = [target]
        while pending:
            for parent in edit_parents.get(pending.pop(), ()):
                if parent not in ancestors:
                    ancestors.add(parent)
                    pending.append(parent)
        bound_reports = sorted({item["report"] for item in bindings
                                if item["source_fact_version_id"] in ancestors})
        edited.append({**edit, "bound_reports": bound_reports,
                       "status": "three_way_merge_required"})
    counts["user_edits_requiring_three_way_merge"] = len(edited)
    return {
        "status": "read_only_candidate_no_current_switch",
        "safe_to_switch_current": False,
        "current": current,
        "source_delta_counts": delta["counts"],
        "counts": counts,
        "bindings": assessment,
        "user_edits": edited,
        "limitations": [
            "Exact source path and unchanged atom are candidates, not accepted fact identity.",
            "A consumers need re-registration; B/C require their own source-bound rebuild.",
            "Any user edit needs source/base/user three-way comparison before propagation.",
        ],
    }


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pinned_input_digests(
    paths: dict[str, Path], expected: dict[str, str],
) -> dict[str, str]:
    observed = {name: _digest(path) for name, path in paths.items()}
    for name, digest in observed.items():
        if expected.get(name) != digest:
            raise BridgeAuditError(f"{name} digest mismatch against frozen pin")
    return observed


def _tool_identity() -> dict[str, str]:
    return {
        "audit_tool_sha256": _digest(Path(__file__)),
        "delta_tool_sha256": _digest(Path(audit_a_payload_drift.__file__)),
    }


def _verified_source_epoch(
    receipt_path: Path,
    expected_receipt_sha256: str,
    database_path: Path,
    old_sidecar_sha256: str,
    bindings: list[dict[str, str]],
) -> dict[str, str]:
    """Bind the old derivation and selected consumers to one pinned source snapshot."""
    if _digest(receipt_path) != expected_receipt_sha256:
        raise BridgeAuditError("source epoch receipt digest mismatch")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BridgeAuditError("source epoch receipt cannot be read") from error
    source = receipt.get("source") if isinstance(receipt, dict) else None
    if not isinstance(source, dict):
        raise BridgeAuditError("source epoch receipt has no source block")
    if source.get("sidecar_sha256") != old_sidecar_sha256:
        raise BridgeAuditError("old sidecar does not match source epoch receipt")
    snapshot_id = source.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not re.fullmatch(
        r"evidence-snapshot_[0-9a-f]{24}", snapshot_id
    ):
        raise BridgeAuditError("source epoch receipt has invalid snapshot id")
    if not bindings or any(
        binding.get("evidence_snapshot_id") != snapshot_id for binding in bindings
    ):
        raise BridgeAuditError("binding snapshot differs from pinned source epoch")
    snapshot_path = (
        database_path.parent.parent / "snapshots" / "evidence" / f"{snapshot_id}.json"
    )
    if not snapshot_path.is_file() or _digest(snapshot_path) != source.get("snapshot_sha256"):
        raise BridgeAuditError("source snapshot digest mismatch against epoch receipt")
    return {
        "source_epoch_receipt_sha256": expected_receipt_sha256,
        "evidence_snapshot_id": snapshot_id,
        "snapshot_sha256": str(source["snapshot_sha256"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-sidecar", required=True, type=Path)
    parser.add_argument("--new-sidecar", required=True, type=Path)
    parser.add_argument("--project-db", required=True, type=Path)
    parser.add_argument("--expected-generation-sha256", required=True)
    parser.add_argument("--expected-old-sidecar-sha256", required=True)
    parser.add_argument("--expected-new-sidecar-sha256", required=True)
    parser.add_argument("--expected-project-db-sha256", required=True)
    parser.add_argument("--expected-delta-tool-sha256", required=True)
    parser.add_argument("--source-epoch-receipt", required=True, type=Path)
    parser.add_argument("--expected-source-epoch-receipt-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {"old_sidecar": args.old_sidecar, "new_sidecar": args.new_sidecar,
             "project_db": args.project_db,
             "source_epoch_receipt": args.source_epoch_receipt}
    expected = {
        "old_sidecar": args.expected_old_sidecar_sha256,
        "new_sidecar": args.expected_new_sidecar_sha256,
        "project_db": args.expected_project_db_sha256,
        "source_epoch_receipt": args.expected_source_epoch_receipt_sha256,
    }
    initial_digests = _pinned_input_digests(paths, expected)
    tool_identity = _tool_identity()
    if tool_identity["delta_tool_sha256"] != args.expected_delta_tool_sha256:
        raise BridgeAuditError("delta tool digest mismatch against frozen pin")
    old = json.loads(args.old_sidecar.read_text(encoding="utf-8"))
    new = json.loads(args.new_sidecar.read_text(encoding="utf-8"))
    current, bindings, edits = read_current_bindings(args.project_db)
    source_epoch = _verified_source_epoch(
        args.source_epoch_receipt, args.expected_source_epoch_receipt_sha256,
        args.project_db, initial_digests["old_sidecar"], bindings,
    )
    result = assess_refresh_bridge(
        old, new, bindings, edits, current,
        expected_generation_sha256=args.expected_generation_sha256,
    )
    if initial_digests != _pinned_input_digests(paths, expected):
        raise BridgeAuditError("an input changed during read-only assessment")
    if source_epoch != _verified_source_epoch(
        args.source_epoch_receipt, args.expected_source_epoch_receipt_sha256,
        args.project_db, initial_digests["old_sidecar"], bindings,
    ):
        raise BridgeAuditError("source epoch changed during read-only assessment")
    if tool_identity != _tool_identity():
        raise BridgeAuditError("audit code changed during read-only assessment")
    result["input_sha256"] = initial_digests
    result["source_epoch"] = source_epoch
    result.update(tool_identity)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps(result["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
