#!/usr/bin/env python3
"""Independently recompute every W04 v4 evidence binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageStat


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _db_summary(database_path: Path) -> dict[str, Any]:
    database = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        queries = {
            "fact_versions": (
                "SELECT fact_version_id,fact_id,raw_value,normalized_value,review_state,"
                "supersedes_fact_version_id,primary_fragment_id FROM fact_versions "
                "WHERE fact_id LIKE 'fact-%' ORDER BY fact_id,created_at,fact_version_id"
            ),
            "requests": (
                "SELECT request_id,request_digest,status,result_fact_version_id,result_revision,"
                "result_json FROM user_fact_edit_requests ORDER BY request_id"
            ),
            "derivations": (
                "SELECT derivation_id,revision,derivation_kind,input_fact_version_ids_json,"
                "output_json,formula FROM user_fact_derivations ORDER BY derivation_id"
            ),
            "refresh": (
                "SELECT conflict_id,fact_id,base_fact_version_id,user_fact_version_id,"
                "source_version_id,comparison_json,requires_explicit_resolution,"
                "resolution_json FROM user_refresh_conflicts "
                "ORDER BY conflict_id"
            ),
        }
        return {
            name: [list(row) for row in database.execute(sql).fetchall()]
            for name, sql in queries.items()
        }
    finally:
        database.close()


def verify(repo: Path, manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec = manifest.get("dirty_source_digest_spec", {})
    expected_spec = {
        "algorithm": "sha256",
        "encoding": "utf-8",
        "ordering": "unicode-codepoint-path-order",
        "record_format": "path + NUL + sha256(raw bytes) + LF",
    }
    for key, value in expected_spec.items():
        if spec.get(key) != value:
            errors.append(f"dirty digest spec mismatch: {key}")
    material = bytearray()
    inputs = spec.get("inputs", [])
    paths = [entry.get("path") for entry in inputs]
    if paths != sorted(paths):
        errors.append("dirty digest inputs are not sorted")
    for entry in inputs:
        path = repo / str(entry.get("path"))
        if not path.is_file():
            errors.append(f"missing dirty source: {entry.get('path')}")
            continue
        data = path.read_bytes()
        digest = _sha(data)
        if digest != entry.get("sha256") or len(data) != entry.get("size"):
            errors.append(f"dirty source mismatch: {entry.get('path')}")
        material.extend(
            str(entry["path"]).encode("utf-8")
            + b"\0"
            + digest.encode("ascii")
            + b"\n"
        )
    if _sha(bytes(material)) != manifest.get("dirty_source_digest"):
        errors.append("dirty source digest mismatch")

    artifact_paths: set[str] = set()
    for entry in manifest.get("artifacts", []):
        relative = str(entry.get("path"))
        artifact_paths.add(relative)
        path = repo / relative
        if not path.is_file():
            errors.append(f"missing artifact: {relative}")
            continue
        data = path.read_bytes()
        if _sha(data) != entry.get("sha256") or len(data) != entry.get("size"):
            errors.append(f"artifact mismatch: {relative}")

    project = repo / manifest["project_relative_path"]
    current_path = project / "reports/current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    if current.get("revision") != 3 or manifest.get("final_revision") != 3:
        errors.append("final raw current is not revision 3")
    current_relative = current_path.relative_to(repo).as_posix()
    if current_relative not in artifact_paths:
        errors.append("final raw current is not bound")

    event_path = project / "events/events.jsonl"
    try:
        events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
        if [event["sequence"] for event in events] != list(range(1, len(events) + 1)):
            errors.append("event sequence is not contiguous")
        if any(not event.get("event_digest") for event in events):
            errors.append("event digest missing")
    except (json.JSONDecodeError, KeyError) as error:
        errors.append(f"event stream invalid: {error}")

    actual_journals = sorted(
        path.relative_to(repo).as_posix()
        for path in (project / "state/user-fact-transactions").glob("*.json")
    )
    if actual_journals != manifest.get("journal_paths"):
        errors.append("journal set mismatch")
    for relative in actual_journals:
        journal = json.loads((repo / relative).read_text(encoding="utf-8"))
        if journal.get("phase") != "ready":
            errors.append(f"journal not ready: {relative}")

    summary_path = manifest_path.parent / "readonly-db-summary.json"
    expected_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if _db_summary(project / "state/project.sqlite") != expected_summary:
        errors.append("readonly DB summary mismatch")

    for delivery in current.get("reports", []):
        transaction_path = project / delivery["transaction_manifest_relative_path"]
        transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
        receipt_path = project / delivery["site_relative_path"] / "data/consumer-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if transaction.get("revision") != 3 or receipt.get("revision") != 3:
            errors.append(f"revision 3 receipt mismatch: {delivery.get('report')}")
        if transaction.get("portal_integration") != receipt:
            errors.append(f"transaction receipt mismatch: {delivery.get('report')}")
        if '"user_fact_revision"' in (
            project / delivery["site_relative_path"] / "data/report.js"
        ).read_text(encoding="utf-8"):
            errors.append(f"overlay metadata remains: {delivery.get('report')}")

    browser_journey = json.loads(
        (manifest_path.parent / "runtime-journey-browser.json").read_text(encoding="utf-8")
    )
    if browser_journey.get("console", {}).get("errors") != 0:
        errors.append("browser console errors are not zero")
    if browser_journey.get("console", {}).get("warnings") != 0:
        errors.append("browser console warnings are not zero")
    for assertion, passed in browser_journey.get("dom_assertions", {}).items():
        if passed is not True:
            errors.append(f"DOM assertion failed: {assertion}")
    for relative in browser_journey.get("screenshots", []):
        path = repo / relative
        try:
            with Image.open(path).convert("RGB") as image:
                stat = ImageStat.Stat(image)
                extrema = cast(tuple[tuple[int, int], ...], image.getextrema())
                if all(low == high == 255 for low, high in extrema):
                    errors.append(f"blank screenshot: {relative}")
                if not all(0 < mean < 255 for mean in stat.mean):
                    errors.append(f"degenerate screenshot pixels: {relative}")
        except OSError as error:
            errors.append(f"invalid screenshot {relative}: {error}")

    return {
        "schema_version": manifest.get("schema_version"),
        "checked_artifacts": len(manifest.get("artifacts", [])),
        "checked_sources": len(inputs),
        "errors": errors,
        "error_count": len(errors),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.repo.resolve(), args.manifest.resolve())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 1 if result["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
