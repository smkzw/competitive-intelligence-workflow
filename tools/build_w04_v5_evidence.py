#!/usr/bin/env python3
"""Build and finalize W04 v5 evidence from scientifically matching portal rows."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

from ci_workflow.application import latest_delivery as latest_delivery_module
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
)

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / (
    "packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v5-final"
)
PROJECT = EVIDENCE / "w04-project"
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)

SOURCE_INPUTS = (
    "migrations/0014_current_generation_protocol.sql",
    "src/ci_workflow/application/latest_delivery.py",
    "src/ci_workflow/application/user_fact_edit.py",
    "src/ci_workflow/application/user_fact_edit_server.py",
    "src/ci_workflow/renderers/portal/active_fact_projection.py",
    "src/ci_workflow/renderers/portal/report_a.py",
    "src/ci_workflow/renderers/portal/report_b.py",
    "src/ci_workflow/renderers/portal/report_c.py",
    "src/ci_workflow/storage/event_store.py",
    "tests/integration/test_w04_user_fact_edit.py",
    "tests/integration/test_sqlite_migrations.py",
    "tools/build_w04_v5_evidence.py",
    "tools/verify_w04_v5_evidence.py",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_test_support() -> ModuleType:
    path = REPO / "tests/integration/test_w04_user_fact_edit.py"
    spec = importlib.util.spec_from_file_location("w04_v5_test_support", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法载入W04集成测试支持")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _selector() -> dict[str, Any]:
    database = sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True)
    try:
        row = database.execute(
            "SELECT project_id,revision,request_id,generation_sha256,"
            "generation_relative_path,committed_at FROM current_delivery_state WHERE singleton=1"
        ).fetchone()
    finally:
        database.close()
    if row is None:
        raise RuntimeError("current selector缺失")
    names = (
        "project_id",
        "revision",
        "request_id",
        "generation_sha256",
        "generation_relative_path",
        "committed_at",
    )
    return dict(zip(names, row, strict=True))


def setup() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    support = _load_test_support()
    root, _fragments = support._project(EVIDENCE)
    if root != PROJECT:
        raise RuntimeError("证据项目路径漂移")
    service = UserFactEditService(PROJECT)
    descriptor = PROJECT / "reports/current.json"
    descriptor_before = descriptor.read_bytes()
    baseline = service.read_current_delivery()

    a_result = service.save(
        UserFactSaveCommand(
            request_id="v5-a-save",
            project_id=baseline.project_id,
            expected_revision=0,
            target=FactTargetIdentity(
                fact_id="fact-a-safety",
                fact_version_id="fact-a-safety-v1",
                entity_id="entity-arm",
                field_id="safety.any_teae",
            ),
            edits=FactEdit(raw_value="67.0%", normalized_value=67.0),
            user_basis="核对同一A门户原始安全性行后修订为67.0%。",
            saved_by="medical-user",
            saved_at=NOW,
        )
    )
    if a_result.rebuilt_reports != ("A",):
        raise RuntimeError("A事实不得重建B/C")

    b_command = UserFactSaveCommand(
        request_id="v5-b-fault-retry",
        project_id=baseline.project_id,
        expected_revision=1,
        target=FactTargetIdentity(
            fact_id="fact-crude-rate",
            fact_version_id="fact-crude-rate-v1",
            entity_id="entity-arm",
            field_id="safety.crude_rate",
        ),
        edits=FactEdit(numerator=24, denominator=80),
        user_basis="核对同一B门户原始34/62行后修订为24/80。",
        saved_by="medical-user",
        saved_at=NOW + timedelta(minutes=1),
    )
    original_fsync = latest_delivery_module._fsync_directory
    injected = False

    def fail_generation_fsync(path: Path) -> None:
        nonlocal injected
        if path.name == "generations" and not injected:
            injected = True
            raise OSError("v5 injected generation directory fsync failure")
        original_fsync(path)

    latest_delivery_module._fsync_directory = fail_generation_fsync
    failure_text = ""
    try:
        service.save(b_command)
    except OSError as error:
        failure_text = str(error)
    finally:
        latest_delivery_module._fsync_directory = original_fsync
    if not injected or "generation directory fsync" not in failure_text:
        raise RuntimeError("generation故障未按预期触发")
    after_failure = UserFactEditService(PROJECT).read_current_delivery()
    if after_failure.revision != 1 or descriptor.read_bytes() != descriptor_before:
        raise RuntimeError("generation故障后公开current不应前移")

    restarted = UserFactEditService(PROJECT)
    b_result = restarted.save(b_command)
    if b_result.revision != 2 or b_result.rebuilt_reports != ("B",):
        raise RuntimeError("重启精确重试未只提交B revision 2")
    if descriptor.read_bytes() != descriptor_before:
        raise RuntimeError("稳定current协议描述符不应随revision变化")
    _write_json(
        EVIDENCE / "runtime-journey-setup.json",
        {
            "schema_version": "5.0",
            "baseline_revision": baseline.revision,
            "a_result": a_result.model_dump(mode="json"),
            "fault": {
                "injected": failure_text,
                "visible_revision_after_failure": after_failure.revision,
                "raw_current_bytes_unchanged": True,
            },
            "restart_retry_result": b_result.model_dump(mode="json"),
            "selector_after_restart_retry": _selector(),
            "raw_current_sha256": _sha(descriptor_before),
        },
    )


def _db_summary() -> dict[str, Any]:
    database = sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True)
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


def _artifact_entry(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(REPO).as_posix(),
        "sha256": _sha(data),
        "size": len(data),
    }


def finalize() -> None:
    browser_path = EVIDENCE / "runtime-journey-browser.json"
    if not browser_path.is_file():
        raise RuntimeError("浏览器旅程记录尚未写入")
    service = UserFactEditService(PROJECT)
    current = service.read_current_delivery()
    if current.revision != 3:
        raise RuntimeError("v5最终current必须为revision 3")
    facts = service.current_facts()
    c_fact = facts["fact-c-threshold"]
    comparison = service.compare_refresh(
        fact_id="fact-c-threshold",
        base_fact_version_id="fact-c-threshold-v1",
        user_fact_version_id=str(c_fact["fact_version_id"]),
        source_fields={"threshold_operator": ">", "threshold_value": 17.0},
        source_version_id="source-v5-refresh",
        request_id="v5-refresh-compare",
        compared_at=NOW + timedelta(minutes=3),
    )
    _write_json(EVIDENCE / "refresh-comparison.json", comparison.model_dump(mode="json"))
    _write_json(EVIDENCE / "readonly-db-summary.json", _db_summary())
    selector = _selector()
    generation_path = PROJECT / str(selector["generation_relative_path"])
    _write_json(
        EVIDENCE / "current-protocol-summary.json",
        {
            "raw_contract": json.loads((PROJECT / "reports/current.json").read_text()),
            "raw_contract_sha256": _sha((PROJECT / "reports/current.json").read_bytes()),
            "selector": selector,
            "selected_generation_sha256": _sha(generation_path.read_bytes()),
            "generation_files": [
                _artifact_entry(path)
                for path in sorted((PROJECT / "reports/generations").glob("*.json"))
            ],
        },
    )

    source_entries = []
    digest_material = bytearray()
    for relative in sorted(SOURCE_INPUTS):
        path = REPO / relative
        data = path.read_bytes()
        digest = _sha(data)
        source_entries.append({"path": relative, "sha256": digest, "size": len(data)})
        digest_material.extend(relative.encode() + b"\0" + digest.encode("ascii") + b"\n")

    artifact_paths = {
        EVIDENCE / "runtime-journey-setup.json",
        browser_path,
        EVIDENCE / "refresh-comparison.json",
        EVIDENCE / "readonly-db-summary.json",
        EVIDENCE / "current-protocol-summary.json",
        EVIDENCE / "verification-result.json",
        EVIDENCE / "tamper-verification-result.json",
        PROJECT / "reports/current.json",
        PROJECT / "events/events.jsonl",
    }
    artifact_paths.update((PROJECT / "reports/generations").glob("*.json"))
    artifact_paths.update((PROJECT / "state/user-fact-transactions").glob("*.json"))
    for delivery in current.reports:
        if delivery.transaction_manifest_relative_path is None:
            raise RuntimeError("最终报告缺少事务清单")
        site = PROJECT / delivery.site_relative_path
        artifact_paths.update(
            {
                PROJECT / delivery.transaction_manifest_relative_path,
                site / "data/consumer-receipt.json",
                site / "data/report.js",
                site / "data/search-index.js",
            }
        )
        receipt = json.loads((site / "data/consumer-receipt.json").read_text())
        artifact_paths.update(site / path for path in receipt["html_sha256"])
    browser = json.loads(browser_path.read_text())
    artifact_paths.update(REPO / relative for relative in browser["screenshots"])
    artifact_paths.update(REPO / relative for relative in browser["browser_logs"])
    artifacts = [_artifact_entry(path) for path in sorted(artifact_paths)]
    _write_json(
        EVIDENCE / "evidence-manifest.json",
        {
            "schema_version": "5.0",
            "formal_verdict": "FAIL_PENDING_FOURTH_INDEPENDENT_REVIEW",
            "project_relative_path": PROJECT.relative_to(REPO).as_posix(),
            "final_revision": current.revision,
            "report_revisions": {
                delivery.report: delivery.revision for delivery in current.reports
            },
            "dirty_source_digest_spec": {
                "algorithm": "sha256",
                "encoding": "utf-8",
                "ordering": "unicode-codepoint-path-order",
                "record_format": "path + NUL + sha256(raw bytes) + LF",
                "inputs": source_entries,
            },
            "dirty_source_digest": _sha(bytes(digest_material)),
            "raw_current_contract_sha256": _sha(
                (PROJECT / "reports/current.json").read_bytes()
            ),
            "selected_generation_sha256": selector["generation_sha256"],
            "journal_paths": sorted(
                path.relative_to(REPO).as_posix()
                for path in (PROJECT / "state/user-fact-transactions").glob("*.json")
            ),
            "artifacts": artifacts,
        },
    )


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
