#!/usr/bin/env python3
"""Independently recompute W04 v5 scientific bindings and durable current state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageStat

from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    active_fact_binding_for_a,
)
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    active_fact_binding_for_b,
)
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
)

_IDENTITY_KEYS = {
    "report",
    "collection",
    "row_id",
    "product_id",
    "drug_name",
    "trial_id",
    "registry_id",
    "group_id",
    "arm",
    "cohort_id",
    "period",
    "endpoint_definition",
    "event_definition",
    "statistical_form",
    "measure_object",
    "unit",
    "normalized_unit",
    "source_version_id",
    "source_pointer",
    "original_row_sha256",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _db_summary(database_path: Path) -> dict[str, Any]:
    database = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        queries = {
            "current_selector": (
                "SELECT singleton,project_id,revision,request_id,generation_sha256,"
                "generation_relative_path,committed_at FROM current_delivery_state"
            ),
            "current_generations": (
                "SELECT generation_sha256,project_id,revision,request_id,"
                "generation_relative_path,created_at FROM current_delivery_generations "
                "ORDER BY revision,generation_sha256"
            ),
            "fact_versions": (
                "SELECT fact_version_id,fact_id,raw_value,normalized_value,review_state,"
                "supersedes_fact_version_id,primary_fragment_id,scientific_context_json "
                "FROM fact_versions WHERE fact_id LIKE 'fact-%' "
                "ORDER BY fact_id,created_at,fact_version_id"
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
                "source_version_id,comparison_json,requires_explicit_resolution,resolution_json "
                "FROM user_refresh_conflicts ORDER BY conflict_id"
            ),
        }
        return {
            name: [list(row) for row in database.execute(sql).fetchall()]
            for name, sql in queries.items()
        }
    finally:
        database.close()


def _actual_binding(
    project: Path, delivery: dict[str, Any], consumer: dict[str, Any]
) -> dict[str, Any]:
    builder = project / delivery["builder_input_relative_path"]
    report = delivery["report"]
    if report == "A":
        data_a = ReportAPortalData.model_validate_json(builder.read_bytes())
        binding = active_fact_binding_for_a(
            data_a, consumer["collection"], consumer["row_id"]
        )
    elif report == "B":
        data_b = ReportBPortalData.model_validate_json(builder.read_bytes())
        binding = active_fact_binding_for_b(
            data_b, consumer["collection"], consumer["row_id"]
        )
    else:
        data_c = ReportCPortalData.model_validate_json(builder.read_bytes())
        binding = active_fact_binding_for_c(data_c, consumer["row_id"])
    return binding.model_dump(mode="json")


def verify(
    repo: Path,
    manifest_path: Path,
    *,
    manifest_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    manifest = manifest_override or json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "5.0":
        errors.append("manifest schema is not v5")
    if manifest.get("formal_verdict") != "FAIL_PENDING_FOURTH_INDEPENDENT_REVIEW":
        errors.append("formal W04 verdict is not pending fourth review")

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
        material.extend(str(entry["path"]).encode() + b"\0" + digest.encode() + b"\n")
    if _sha(bytes(material)) != manifest.get("dirty_source_digest"):
        errors.append("dirty source digest mismatch")

    artifacts = manifest.get("artifacts", [])
    for entry in artifacts:
        path = repo / str(entry.get("path"))
        if not path.is_file():
            errors.append(f"missing artifact: {entry.get('path')}")
            continue
        data = path.read_bytes()
        if _sha(data) != entry.get("sha256") or len(data) != entry.get("size"):
            errors.append(f"artifact mismatch: {entry.get('path')}")

    project = repo / manifest["project_relative_path"]
    descriptor_path = project / "reports/current.json"
    expected_descriptor = {
        "schema_version": "2.0",
        "protocol": "sqlite-committed-generation",
        "database_relative_path": "state/project.sqlite",
        "selector_table": "current_delivery_state",
        "generations_relative_path": "reports/generations",
    }
    try:
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"raw current contract unreadable: {error}")
        descriptor = {}
    if descriptor != expected_descriptor:
        errors.append("raw current contract mismatch")
    if _sha(descriptor_path.read_bytes()) != manifest.get("raw_current_contract_sha256"):
        errors.append("raw current contract digest mismatch")

    database_path = project / "state/project.sqlite"
    database = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        selector = database.execute(
            "SELECT revision,generation_sha256,generation_relative_path "
            "FROM current_delivery_state WHERE singleton=1"
        ).fetchone()
    finally:
        database.close()
    if selector is None:
        errors.append("committed selector missing")
        current: dict[str, Any] = {}
    else:
        revision, generation_sha256, generation_relative_path = selector
        generation = project / str(generation_relative_path)
        if not generation.is_file() or _sha(generation.read_bytes()) != generation_sha256:
            errors.append("selected immutable generation mismatch")
            current = {}
        else:
            current = json.loads(generation.read_text(encoding="utf-8"))
        if revision != manifest.get("final_revision") or generation_sha256 != manifest.get(
            "selected_generation_sha256"
        ):
            errors.append("selector identity mismatch")

    expected_summary = json.loads(
        (manifest_path.parent / "readonly-db-summary.json").read_text(encoding="utf-8")
    )
    if _db_summary(database_path) != expected_summary:
        errors.append("readonly DB summary mismatch")

    expected_revisions = manifest.get("report_revisions", {})
    if expected_revisions != {"A": 1, "B": 2, "C": 3}:
        errors.append("report revisions do not prove report-scoped rebuilds")
    for delivery in current.get("reports", []):
        report = delivery.get("report")
        if delivery.get("revision") != expected_revisions.get(report):
            errors.append(f"report revision mismatch: {report}")
        transaction_path = project / str(delivery.get("transaction_manifest_relative_path"))
        site = project / str(delivery.get("site_relative_path"))
        try:
            transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
            receipt = json.loads(
                (site / "data/consumer-receipt.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"transaction or receipt unreadable for {report}: {error}")
            continue
        if transaction.get("portal_integration") != receipt:
            errors.append(f"transaction receipt mismatch: {report}")
        impact_bindings = transaction.get("impact_bindings")
        if not isinstance(impact_bindings, list):
            errors.append(f"impact identities missing: {report}")
            impact_bindings = []
        for consumer in receipt.get("consumers", []):
            binding = consumer.get("binding_identity", {})
            if set(binding) != _IDENTITY_KEYS:
                errors.append(f"incomplete binding identity: {report}")
                continue
            try:
                actual = _actual_binding(project, delivery, consumer)
            except Exception as error:  # verifier must convert malformed evidence to FAIL
                errors.append(f"cannot recompute original binding {report}: {error}")
                continue
            if actual != binding:
                errors.append(f"scientific binding mismatch: {report}/{consumer.get('row_id')}")
            expected_impact = {
                "fact_id": consumer.get("fact_id"),
                "fact_version_id": consumer.get("fact_version_id"),
                "binding_identity": binding,
                "original_row_sha256": consumer.get("original_row_sha256"),
            }
            if expected_impact not in impact_bindings:
                errors.append(f"impact binding mismatch: {report}")
        payload = (site / "data/report.js").read_text(encoding="utf-8")
        if '"user_fact_revision"' in payload:
            errors.append(f"overlay metadata remains: {report}")

    event_path = project / "events/events.jsonl"
    try:
        events = [json.loads(line) for line in event_path.read_text().splitlines()]
        if [event["sequence"] for event in events] != list(range(1, len(events) + 1)):
            errors.append("event sequence is not contiguous")
    except (OSError, json.JSONDecodeError, KeyError) as error:
        errors.append(f"event stream invalid: {error}")
    actual_journals = sorted(
        path.relative_to(repo).as_posix()
        for path in (project / "state/user-fact-transactions").glob("*.json")
    )
    if actual_journals != manifest.get("journal_paths"):
        errors.append("journal set mismatch")
    for relative in actual_journals:
        if json.loads((repo / relative).read_text()).get("phase") != "ready":
            errors.append(f"journal not ready: {relative}")

    browser = json.loads(
        (manifest_path.parent / "runtime-journey-browser.json").read_text(encoding="utf-8")
    )
    if browser.get("console") != {"errors": 0, "warnings": 0}:
        errors.append("browser console is not zero-error/zero-warning")
    for assertion, passed in browser.get("dom_assertions", {}).items():
        if passed is not True:
            errors.append(f"DOM assertion failed: {assertion}")
    for relative in browser.get("screenshots", []):
        path = repo / relative
        try:
            with Image.open(path).convert("RGB") as image:
                stat = ImageStat.Stat(image)
                extrema = cast(tuple[tuple[int, int], ...], image.getextrema())
                if all(low == high == 255 for low, high in extrema):
                    errors.append(f"blank screenshot: {relative}")
                if not all(0 < mean < 255 for mean in stat.mean):
                    errors.append(f"degenerate screenshot: {relative}")
        except OSError as error:
            errors.append(f"invalid screenshot {relative}: {error}")

    return {
        "schema_version": manifest.get("schema_version"),
        "checked_sources": len(inputs),
        "checked_artifacts": len(artifacts),
        "error_count": len(errors),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--tamper-check", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    manifest_path = args.manifest.resolve()
    if args.tamper_check:
        tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
        tampered["artifacts"][0]["sha256"] = "0" * 64
        result = verify(repo, manifest_path, manifest_override=tampered)
        result["tamper_probe"] = "first artifact sha256 replaced with 64 zeroes"
        result["tamper_rejected"] = result["error_count"] > 0
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if result["tamper_rejected"] else 1
    result = verify(repo, manifest_path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 1 if result["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
