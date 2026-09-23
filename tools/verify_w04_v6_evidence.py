#!/usr/bin/env python3
"""Verify W04 v6 evidence, including every frozen portal builder input byte."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, cast

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
from tools import verify_w04_v5_evidence as legacy


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _artifact_for_builder(
    artifacts: Sequence[Mapping[str, Any]],
    *,
    project_relative_path: str,
    builder_relative_path: str,
) -> Mapping[str, Any] | None:
    accepted = {
        builder_relative_path,
        f"{project_relative_path.rstrip('/')}/{builder_relative_path}",
    }
    matches = [entry for entry in artifacts if str(entry.get("path")) in accepted]
    return matches[0] if len(matches) == 1 else None


def _binding_from_bytes(
    report: str,
    data: bytes,
    consumer: Mapping[str, Any],
) -> dict[str, Any]:
    collection = str(consumer["collection"])
    row_id = str(consumer["row_id"])
    if report == "A":
        if collection not in ("safety", "efficacy"):
            raise ValueError(f"invalid A consumer collection: {collection}")
        binding = active_fact_binding_for_a(
            ReportAPortalData.model_validate_json(data),
            cast(Literal["safety", "efficacy"], collection),
            row_id,
        )
    elif report == "B":
        if collection not in ("safety", "efficacy"):
            raise ValueError(f"invalid B consumer collection: {collection}")
        binding = active_fact_binding_for_b(
            ReportBPortalData.model_validate_json(data),
            cast(Literal["safety", "efficacy"], collection),
            row_id,
        )
    elif report == "C":
        binding = active_fact_binding_for_c(ReportCPortalData.model_validate_json(data), row_id)
    else:
        raise ValueError(f"unknown report: {report}")
    return binding.model_dump(mode="json")


def verify_builder_inputs(
    project: Path,
    deliveries: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
    *,
    project_relative_path: str = "",
    byte_overrides: Mapping[str, bytes] | None = None,
    require_receipts: bool = False,
) -> list[str]:
    """Verify path, bytes, delivery digest, manifest membership and row identity."""
    errors: list[str] = []
    root = project.resolve()
    overrides = byte_overrides or {}
    for delivery in deliveries:
        report = str(delivery.get("report"))
        relative = delivery.get("builder_input_relative_path")
        expected_sha = delivery.get("builder_input_sha256")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            errors.append(f"builder input path invalid: {report}")
            continue
        path = (root / relative).resolve(strict=False)
        if not _inside(root, path) or path.is_symlink():
            errors.append(f"builder input path escapes project: {report}")
            continue
        if relative in overrides:
            data = overrides[relative]
        elif path.is_file():
            data = path.read_bytes()
        else:
            errors.append(f"builder input missing: {report}/{relative}")
            continue
        digest = _sha(data)
        if digest != expected_sha:
            errors.append(f"builder input delivery digest mismatch: {report}/{relative}")
        artifact = _artifact_for_builder(
            artifacts,
            project_relative_path=project_relative_path,
            builder_relative_path=relative,
        )
        if artifact is None:
            errors.append(f"builder input absent or duplicated in manifest: {report}/{relative}")
        elif digest != artifact.get("sha256") or len(data) != artifact.get("size"):
            errors.append(f"builder input manifest bytes mismatch: {report}/{relative}")

        receipt_path = root / str(delivery.get("site_relative_path")) / "data/consumer-receipt.json"
        if not receipt_path.is_file():
            if require_receipts:
                errors.append(f"builder input receipt missing: {report}")
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            consumers = receipt["consumers"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            errors.append(f"builder input receipt unreadable: {report}: {error}")
            continue
        for consumer in consumers:
            try:
                actual = _binding_from_bytes(report, data, consumer)
            except Exception as error:
                errors.append(f"builder input cannot recompute binding: {report}: {error}")
                continue
            if actual != consumer.get("binding_identity"):
                errors.append(
                    f"builder input scientific binding mismatch: {report}/{consumer.get('row_id')}"
                )
    return errors


def verify(
    repo: Path,
    manifest_path: Path,
    *,
    manifest_override: dict[str, Any] | None = None,
    builder_overrides: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    manifest = manifest_override or json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if manifest.get("schema_version") != "6.0":
        errors.append("manifest schema is not v6")
    if manifest.get("formal_verdict") != "FAIL_PENDING_FIFTH_INDEPENDENT_REVIEW":
        errors.append("formal W04 verdict is not pending fifth review")

    compatibility = copy.deepcopy(manifest)
    compatibility["schema_version"] = "5.0"
    compatibility["formal_verdict"] = "FAIL_PENDING_FOURTH_INDEPENDENT_REVIEW"
    legacy_result = legacy.verify(repo, manifest_path, manifest_override=compatibility)
    errors.extend(str(error) for error in legacy_result["errors"])

    project_relative = str(manifest.get("project_relative_path") or "")
    project = (repo / project_relative).resolve(strict=False)
    current: dict[str, Any] = {}
    try:
        selector = sqlite3.connect(f"file:{project / 'state/project.sqlite'}?mode=ro", uri=True)
        try:
            row = selector.execute(
                "SELECT generation_relative_path FROM current_delivery_state WHERE singleton=1"
            ).fetchone()
        finally:
            selector.close()
        if row is None:
            errors.append("committed selector missing for builder verification")
        else:
            current = json.loads((project / str(row[0])).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, sqlite3.Error) as error:
        errors.append(f"cannot read current deliveries for builder verification: {error}")
    if current:
        errors.extend(
            verify_builder_inputs(
                project,
                current.get("reports", []),
                manifest.get("artifacts", []),
                project_relative_path=project_relative,
                byte_overrides=builder_overrides,
                require_receipts=True,
            )
        )
    return {
        "schema_version": manifest.get("schema_version"),
        "checked_sources": legacy_result["checked_sources"],
        "checked_artifacts": legacy_result["checked_artifacts"],
        "checked_builder_inputs": len(current.get("reports", [])),
        "error_count": len(errors),
        "errors": errors,
    }


def _builder_override(
    repo: Path,
    manifest: Mapping[str, Any],
    mode: str,
) -> tuple[str, bytes]:
    project = repo / str(manifest["project_relative_path"])
    database = sqlite3.connect(f"file:{project / 'state/project.sqlite'}?mode=ro", uri=True)
    try:
        row = database.execute(
            "SELECT generation_relative_path FROM current_delivery_state WHERE singleton=1"
        ).fetchone()
    finally:
        database.close()
    if row is None:
        raise RuntimeError("selector missing")
    current = json.loads((project / str(row[0])).read_text(encoding="utf-8"))
    delivery = next(item for item in current["reports"] if item["report"] == "A")
    relative = str(delivery["builder_input_relative_path"])
    original = (project / relative).read_bytes()
    if mode == "byte":
        return relative, original + b"\n"
    payload = json.loads(original)
    if mode == "target":
        receipt = json.loads(
            (
                project / str(delivery["site_relative_path"]) / "data/consumer-receipt.json"
            ).read_text()
        )
        row_id = receipt["consumers"][0]["row_id"]
        target = next(item for item in payload["safety"] if item["row_id"] == row_id)
        target["value"] = 999
    else:
        payload["indication"] = "TAMPERED-NON-TARGET"
    return relative, json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--tamper-check",
        choices=("artifact", "builder-target", "builder-nontarget", "builder-byte"),
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    builder_overrides: dict[str, bytes] | None = None
    if args.tamper_check == "artifact":
        manifest = copy.deepcopy(manifest)
        manifest["artifacts"][0]["sha256"] = "0" * 64
    elif args.tamper_check:
        mode = args.tamper_check.removeprefix("builder-")
        relative, data = _builder_override(repo, manifest, mode)
        builder_overrides = {relative: data}
    result = verify(
        repo,
        manifest_path,
        manifest_override=manifest,
        builder_overrides=builder_overrides,
    )
    if args.tamper_check:
        result["tamper_probe"] = args.tamper_check
        result["tamper_rejected"] = result["error_count"] > 0
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    if args.tamper_check:
        return 0 if result["tamper_rejected"] else 1
    return 1 if result["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
