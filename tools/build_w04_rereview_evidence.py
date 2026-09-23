#!/usr/bin/env python3
"""Build the reproducible W04 rereview project and v4 evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ci_workflow.application.refresh_service import RefreshService
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
)
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import OutputFormat, ReportKind
from ci_workflow.storage.event_store import EventStoreError, WorkflowEvent
from ci_workflow.storage.migrations import persist_project_contract
from ci_workflow.storage.sqlite import open_database

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v4"
PROJECT = EVIDENCE / "w04-project"
SOURCE_RUN = REPO / "runs/pnh-vertical/abc-v106"
PROJECT_ID = "project-w04-rereview-v4"
NOW = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)

SOURCE_INPUTS = (
    "src/ci_workflow/application/latest_delivery.py",
    "src/ci_workflow/application/user_fact_edit.py",
    "src/ci_workflow/application/user_fact_edit_server.py",
    "src/ci_workflow/renderers/portal/active_fact_projection.py",
    "src/ci_workflow/renderers/portal/fact_revision.py",
    "src/ci_workflow/renderers/portal/report_a.py",
    "src/ci_workflow/renderers/portal/report_b.py",
    "src/ci_workflow/renderers/portal/report_c.py",
    "src/ci_workflow/renderers/portal/templates/a/safety.html.j2",
    "src/ci_workflow/storage/event_store.py",
    "tests/integration/test_w04_user_fact_edit.py",
    "tools/build_w04_rereview_evidence.py",
    "tools/verify_w04_evidence.py",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _seed_fact(
    database: sqlite3.Connection,
    *,
    fact_id: str,
    version_id: str,
    field_id: str,
    raw_value: str,
    normalized_value: str,
    fragment_id: str,
    quote: str,
    locator: str,
    context: dict[str, Any],
) -> None:
    database.execute(
        "INSERT OR IGNORE INTO evidence_fragments "
        "(fragment_id,source_version_id,locator,content_text,content_sha256,created_at) "
        "VALUES (?,?,?,?,?,?)",
        (fragment_id, "source-v1", locator, quote, _sha(quote.encode()), NOW.isoformat()),
    )
    context_json = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    database.execute(
        "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,raw_value,"
        "normalized_value,disclosure_state,review_state,primary_fragment_id,created_at,"
        "content_sha256,scientific_context_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            version_id,
            fact_id,
            "entity-arm",
            field_id,
            raw_value,
            normalized_value,
            "reported_value",
            "accepted",
            fragment_id,
            NOW.isoformat(),
            _sha(context_json.encode()),
            context_json,
        ),
    )
    database.execute(
        "INSERT INTO fact_evidence (fact_version_id,fragment_id,evidence_role,created_at) "
        "VALUES (?,?,?,?)",
        (version_id, fragment_id, "primary", NOW.isoformat()),
    )


def setup() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    PROJECT.mkdir()
    persist_project_contract(
        PROJECT / "state/project.sqlite",
        ProjectContract(
            contract_version=1,
            project_id=PROJECT_ID,
            indication="阵发性睡眠性血红蛋白尿症",
            reports=(ReportKind.A, ReportKind.B, ReportKind.C),
            outputs=(OutputFormat.HTML,),
            timezone="Asia/Shanghai",
            data_cutoff=datetime(2026, 9, 20, tzinfo=UTC),
            cutoff_was_user_supplied=True,
            created_at=NOW,
        ),
    )
    with open_database(PROJECT / "state/project.sqlite") as database:
        database.execute(
            "INSERT INTO entities (entity_id,entity_type,canonical_name,created_at) "
            "VALUES ('entity-arm','trial_arm','治疗组',?)",
            (NOW.isoformat(),),
        )
        database.execute(
            "INSERT INTO source_versions (source_version_id,source_id,content_sha256,"
            "acquired_at,created_at) VALUES ('source-v1','source-1',?,?,?)",
            (_sha(b"w04-v4-source"), NOW.isoformat(), NOW.isoformat()),
        )
        common = {
            "entity_id": "entity-arm",
            "arm_id": "arm-treatment",
            "cohort_id": "cohort-main",
            "population": "ITT人群",
            "timepoint": "第24周",
            "unit": "%",
            "normalized_unit": "%",
            "endpoint_definition": "发生至少一次目标事件的受试者比例",
            "analysis_set": "ITT",
            "measure_object": "participants",
        }
        _seed_fact(
            database,
            fact_id="fact-crude-rate",
            version_id="fact-crude-rate-v1",
            field_id="safety.crude_rate",
            raw_value="25% (20/80)",
            normalized_value="25",
            fragment_id="fragment-count",
            quote="20/80例受试者发生事件（25%）。",
            locator="registry.results.safety[0]",
            context={
                **common,
                "numerator": 20,
                "denominator": 80,
                "statistical_form": "crude_rate",
                "consumer_bindings": [
                    {"report": "A", "collection": "safety", "row_id": "safe-1"},
                    {"report": "B", "collection": "safety", "row_id": "bsafe-safe-298"},
                ],
            },
        )
        _seed_fact(
            database,
            fact_id="fact-c-threshold",
            version_id="fact-c-threshold-v1",
            field_id="eligibility.hemoglobin_threshold",
            raw_value="<10 g/dL",
            normalized_value="10",
            fragment_id="fragment-threshold",
            quote="Anemia (Hgb <10 g/dL)",
            locator="protocolSection.eligibilityModule.eligibilityCriteria",
            context={
                **common,
                "unit": "g/dL",
                "normalized_unit": "g/dL",
                "statistical_form": "threshold",
                "threshold_operator": "<",
                "threshold_value": 10.0,
                "threshold_unit": "g/dL",
                "endpoint_definition": "筛选期血红蛋白浓度",
                "consumer_bindings": [
                    {
                        "report": "C",
                        "collection": "observations",
                        "row_id": "row-nct04469465-inclusion_criterion-1",
                    }
                ],
            },
        )
        _seed_fact(
            database,
            fact_id="fact-unrelated-20",
            version_id="fact-unrelated-20-v1",
            field_id="baseline.sample_size",
            raw_value="20",
            normalized_value="20",
            fragment_id="fragment-unrelated",
            quote="另一研究共有20例受试者。",
            locator="registry.study.other.enrollment",
            context={**common, "unit": "人", "normalized_unit": "人", "statistical_form": "count"},
        )
    sites: dict[str, Path] = {}
    data_paths: dict[str, Path] = {}
    for report in ("A", "B", "C"):
        site = PROJECT / f"reports/{report}/v1/html"
        shutil.copytree(SOURCE_RUN / f"reports/{report}/v1/html", site)
        sites[report] = site
        data_paths[report] = SOURCE_RUN / f"state/derived/report-{report.lower()}-data.json"
    service = UserFactEditService(PROJECT)
    service.initialize_current_delivery(
        project_id=PROJECT_ID,
        report_sites=sites,
        report_data_paths=data_paths,
        fact_version_ids=("fact-crude-rate-v1", "fact-c-threshold-v1", "fact-unrelated-20-v1"),
        created_at=NOW,
    )
    seed_event = service.event_store.append(
        WorkflowEvent(
            schema_version="1.0",
            event_id="event-before-partial",
            project_id=PROJECT_ID,
            run_id="w04-rereview",
            event_type="test.before.partial",
            occurred_at=NOW,
            actor_id="w04-evidence",
            idempotency_key="w04.before.partial",
            payload={"preserve": True},
        )
    )
    command = UserFactSaveCommand(
        request_id="v4-rate-save",
        project_id=PROJECT_ID,
        expected_revision=0,
        target=FactTargetIdentity(
            fact_id="fact-crude-rate",
            fact_version_id="fact-crude-rate-v1",
            entity_id="entity-arm",
            field_id="safety.crude_rate",
        ),
        edits=FactEdit(numerator=24, denominator=80),
        user_basis="核对病例汇总表后将事件人数修订为24/80。",
        saved_by="medical-user",
        saved_at=NOW + timedelta(minutes=1),
    )
    pointer = PROJECT / "reports/current.json"
    before = pointer.read_bytes()
    original = service.event_store._replace_stream
    injected = False

    def partial_failure(payload: bytes) -> None:
        nonlocal injected
        if injected:
            raise AssertionError("partial failure must occur once")
        injected = True
        current_size = service.event_store.path.stat().st_size
        with service.event_store.path.open("ab") as stream:
            stream.write(payload[current_size : current_size + 41])
            stream.flush()
        raise OSError("injected partial event stream failure")

    service.event_store._replace_stream = partial_failure  # type: ignore[method-assign]
    failure = ""
    try:
        service.save(command)
    except EventStoreError as error:
        failure = str(error)
    finally:
        service.event_store._replace_stream = original  # type: ignore[method-assign]
    if not failure or pointer.read_bytes() != before:
        raise RuntimeError("partial event failure did not preserve raw current")
    result = service.save(command)
    if service.save(command) != result:
        raise RuntimeError("idempotent retry changed the result")
    events = service.event_store.read_all()
    if events[0] != seed_event or len(events) != 2:
        raise RuntimeError("event tail recovery did not preserve history exactly")
    _write_json(
        EVIDENCE / "runtime-journey-fault-retry.json",
        {
            "failure": failure,
            "raw_current_unchanged_on_failure": True,
            "recovered_revision": result.revision,
            "idempotent_retry_equal": True,
            "events": [event.model_dump(mode="json") for event in events],
        },
    )


def _db_summary() -> dict[str, Any]:
    uri = f"file:{PROJECT / 'state/project.sqlite'}?mode=ro"
    database = sqlite3.connect(uri, uri=True)
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


def _dirty_digest() -> tuple[str, list[dict[str, Any]]]:
    entries = []
    material = bytearray()
    for relative in sorted(SOURCE_INPUTS):
        data = (REPO / relative).read_bytes()
        digest = _sha(data)
        entries.append({"path": relative, "sha256": digest, "size": len(data)})
        material.extend(relative.encode("utf-8") + b"\0" + digest.encode("ascii") + b"\n")
    return _sha(bytes(material)), entries


def finalize() -> None:
    service = UserFactEditService(PROJECT)
    current = service.read_current_delivery()
    final_path = EVIDENCE / "runtime-journey-final.json"
    if current.revision == 2:
        facts = service.current_facts()
        threshold = facts["fact-c-threshold"]
        undo = service.save(
            UserFactSaveCommand(
                request_id="v4-threshold-undo",
                project_id=PROJECT_ID,
                expected_revision=2,
                operation="undo",
                target=FactTargetIdentity(
                    fact_id="fact-c-threshold",
                    fact_version_id=str(threshold["fact_version_id"]),
                    entity_id="entity-arm",
                    field_id="eligibility.hemoglobin_threshold",
                ),
                edits=FactEdit(),
                user_basis="撤销浏览器阈值修订，追加恢复原始阈值的新版本。",
                saved_by="medical-user",
                saved_at=NOW + timedelta(minutes=3),
            )
        )
        with open_database(PROJECT / "state/project.sqlite") as database:
            row = database.execute(
                "SELECT fact_version_id FROM fact_versions WHERE fact_id='fact-c-threshold' "
                "AND supersedes_fact_version_id='fact-c-threshold-v1' "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
        if row is None:
            raise RuntimeError("browser threshold fact version not found")
        comparison = RefreshService(PROJECT).compare_user_fact_refresh(
            fact_id="fact-c-threshold",
            base_fact_version_id="fact-c-threshold-v1",
            user_fact_version_id=str(row[0]),
            source_version_id="source-v2",
            source_fields={"threshold_value": 9.0, "threshold_operator": ">"},
            source_withdrawn=False,
            request_id="v4-refresh-conflict",
            compared_at=NOW + timedelta(minutes=4),
            actor_id="refresh-worker",
        )
        final_current = service.read_current_delivery()
        _write_json(
            final_path,
            {
                "undo": undo.model_dump(mode="json"),
                "refresh": comparison.model_dump(mode="json"),
                "final_current": final_current.model_dump(mode="json"),
            },
        )
    elif current.revision == 3 and final_path.is_file():
        final_current = current
    else:
        raise RuntimeError(
            "finalize requires browser revision 2 or a recorded revision 3 recovery"
        )
    _write_json(EVIDENCE / "readonly-db-summary.json", _db_summary())
    dirty_digest, source_entries = _dirty_digest()
    required: list[Path] = [
        EVIDENCE / "runtime-journey-fault-retry.json",
        EVIDENCE / "runtime-journey-browser.json",
        EVIDENCE / "runtime-journey-final.json",
        EVIDENCE / "readonly-db-summary.json",
        PROJECT / "reports/current.json",
        PROJECT / "events/events.jsonl",
    ]
    required.extend(sorted((PROJECT / "state/user-fact-transactions").glob("*.json")))
    for delivery in final_current.reports:
        if delivery.transaction_manifest_relative_path is None:
            raise RuntimeError("revision 3 delivery is missing transaction manifest")
        transaction = PROJECT / delivery.transaction_manifest_relative_path
        required.extend(
            [transaction, PROJECT / delivery.site_relative_path / "data/consumer-receipt.json"]
        )
    browser_dir = EVIDENCE / "browser"
    required.extend(sorted(browser_dir.glob("*")))
    if not all(path.is_file() for path in required):
        missing = [str(path) for path in required if not path.is_file()]
        raise RuntimeError(f"evidence files missing: {missing}")
    artifacts = []
    for path in sorted(set(required)):
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(REPO).as_posix(),
                "sha256": _sha(data),
                "size": len(data),
            }
        )
    manifest = {
        "schema_version": "4.0",
        "formal_w04_verdict": "FAIL_PENDING_THIRD_INDEPENDENT_REVIEW",
        "model_effort": "UNVERIFIED",
        "dirty_source_digest": dirty_digest,
        "dirty_source_digest_spec": {
            "algorithm": "sha256",
            "encoding": "utf-8",
            "ordering": "unicode-codepoint-path-order",
            "record_format": "path + NUL + sha256(raw bytes) + LF",
            "inputs": source_entries,
        },
        "project_relative_path": PROJECT.relative_to(REPO).as_posix(),
        "final_revision": final_current.revision,
        "artifacts": artifacts,
        "journal_paths": [
            path.relative_to(REPO).as_posix()
            for path in sorted((PROJECT / "state/user-fact-transactions").glob("*.json"))
        ],
    }
    _write_json(EVIDENCE / "evidence-manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("setup", "finalize"))
    args = parser.parse_args()
    setup() if args.phase == "setup" else finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
