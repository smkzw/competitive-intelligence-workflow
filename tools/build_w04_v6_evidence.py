#!/usr/bin/env python3
"""Build W04 v6 evidence with source-safe projections and frozen builder inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ci_workflow.application.user_fact_edit import UserFactEditService
from tools import build_w04_v5_evidence as legacy
from tools.verify_w04_v6_evidence import verify

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / (
    "packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v6-final-3"
)
PROJECT = EVIDENCE / "w04-project"
SOURCE_INPUTS = (
    "migrations/0014_current_generation_protocol.sql",
    "assets/portal/evidence-drawer.js",
    "assets/portal/report-a.js",
    "assets/portal/report-b.js",
    "src/ci_workflow/application/latest_delivery.py",
    "src/ci_workflow/application/user_fact_edit.py",
    "src/ci_workflow/application/user_fact_edit_server.py",
    "src/ci_workflow/renderers/portal/active_fact_projection.py",
    "src/ci_workflow/renderers/portal/assets/evidence-drawer.js",
    "src/ci_workflow/renderers/portal/assets/report-a.js",
    "src/ci_workflow/renderers/portal/assets/report-b.js",
    "src/ci_workflow/renderers/portal/report_a.py",
    "src/ci_workflow/renderers/portal/report_b.py",
    "src/ci_workflow/renderers/portal/report_c.py",
    "src/ci_workflow/renderers/portal/templates/a/safety.html.j2",
    "src/ci_workflow/reports/common/evidence_view.py",
    "src/ci_workflow/storage/event_store.py",
    "tests/integration/test_w04_user_fact_edit.py",
    "tests/integration/test_sqlite_migrations.py",
    "tools/build_w04_v5_evidence.py",
    "tools/build_w04_v6_evidence.py",
    "tools/verify_w04_v5_evidence.py",
    "tools/verify_w04_v6_evidence.py",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _configure_legacy() -> None:
    legacy.EVIDENCE = EVIDENCE
    legacy.PROJECT = PROJECT
    legacy.SOURCE_INPUTS = SOURCE_INPUTS  # type: ignore[assignment]


def setup() -> None:
    _configure_legacy()
    legacy.setup()
    setup_path = EVIDENCE / "runtime-journey-setup.json"
    payload = json.loads(setup_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "6.0"
    _write(setup_path, payload)


def finalize() -> None:
    _configure_legacy()
    _write(EVIDENCE / "verification-result.json", {"pending": True})
    _write(EVIDENCE / "tamper-verification-result.json", {"pending": True})
    legacy.finalize()
    manifest_path = EVIDENCE / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "6.0"
    manifest["formal_verdict"] = "FAIL_PENDING_FIFTH_INDEPENDENT_REVIEW"
    excluded = {
        (EVIDENCE / "verification-result.json").relative_to(REPO).as_posix(),
        (EVIDENCE / "tamper-verification-result.json").relative_to(REPO).as_posix(),
    }
    artifacts = [
        item for item in manifest["artifacts"] if str(item["path"]) not in excluded
    ]
    service = UserFactEditService(PROJECT)
    current = service.read_current_delivery()
    for delivery in current.reports:
        if delivery.builder_input_relative_path is None:
            raise RuntimeError(f"{delivery.report} missing builder input")
        path = PROJECT / delivery.builder_input_relative_path
        relative = path.relative_to(REPO).as_posix()
        data = path.read_bytes()
        artifacts.append({"path": relative, "sha256": _sha(data), "size": len(data)})
    manifest["artifacts"] = sorted(
        {item["path"]: item for item in artifacts}.values(),
        key=lambda item: str(item["path"]),
    )
    manifest["builder_input_contract"] = {
        "path_basis": "project-relative delivery.builder_input_relative_path",
        "path_boundary": "resolved ordinary file inside project root; no symlink",
        "byte_algorithm": "sha256(raw bytes)",
        "manifest_membership": "exactly one artifact entry per A/B/C builder input",
        "binding_recomputation": "parse frozen bytes and recompute every receipt consumer identity",
    }
    _write(manifest_path, manifest)
    result = verify(REPO, manifest_path)
    _write(EVIDENCE / "verification-result.json", result)
    if result["error_count"]:
        raise RuntimeError(f"v6 verifier failed: {result['errors']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("setup", "finalize"))
    args = parser.parse_args()
    if args.mode == "setup":
        setup()
    else:
        finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
