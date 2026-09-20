from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "docs" / "architecture" / "format-contracts" / "pptx-master-job.yaml"
VECTORS_PATH = ROOT / "tests" / "fixtures" / "pptx-master-job" / "contract-vectors.json"


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    payload = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def vectors() -> dict[str, Any]:
    payload = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _stages(contract: dict[str, Any]) -> list[dict[str, Any]]:
    stages = contract["stages"]["order"]
    assert isinstance(stages, list)
    return stages


def _case_map(vectors: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = vectors["cases"]
    assert isinstance(cases, list)
    return {case["id"]: case for case in cases}


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_contract_freezes_single_serial_stage_order(contract: dict[str, Any]) -> None:
    stages = _stages(contract)

    assert [stage["order"] for stage in stages] == list(range(1, 10))
    assert [stage["id"] for stage in stages] == [
        "initialize",
        "content_design_lock",
        "page_svg",
        "quality_check",
        "speaker_notes",
        "closeout",
        "native_export",
        "editability_check",
        "visual_check",
    ]
    assert contract["serial_execution"]["maximum_active_jobs"] == 1
    assert contract["serial_execution"]["maximum_active_stage_attempts"] == 1
    assert contract["serial_execution"]["parallel_master_invocation"] is False
    assert contract["stages"]["receipt_required_for_every_committed_stage"] is True


def test_contract_freezes_snapshot_identity_and_recovery_preflight(
    contract: dict[str, Any],
) -> None:
    identity = contract["identity"]
    assert identity["job_key"] == ["project_id", "report", "snapshot_id"]
    assert set(identity["immutable_after_lock"]) >= {
        "report",
        "report_version",
        "snapshot_id",
        "snapshot_sha256",
        "claim_snapshot_id",
        "evidence_snapshot_id",
        "coverage_set_id",
        "contract_version",
    }

    preflight = set(contract["recovery"]["resume_preflight"])
    assert {
        "job_identity_matches_request",
        "snapshot_id_matches_locked_snapshot",
        "snapshot_sha256_matches_locked_snapshot",
        "latest_receipt_identity_matches_pointer",
        "all_predecessor_receipts_are_committed",
        "all_predecessor_artifact_digests_match_receipts",
        "recovery_authorization_is_not_expired",
        "global_execution_lock_is_acquired_before_the_next_stage",
    } <= preflight
    assert (
        contract["recovery"]["recovery_pointer"][
            "pointer_must_not_be_inferred_from_filesystem_mtime"
        ]
        is True
    )


def test_positive_vectors_cover_a_b_c_and_resume_boundaries(
    contract: dict[str, Any], vectors: dict[str, Any]
) -> None:
    stages = _stages(contract)
    stage_ids = [stage["id"] for stage in stages]
    positives = [case for case in vectors["cases"] if case["kind"] == "positive"]

    assert {case["job"]["report"] for case in positives} == {"A", "B", "C"}
    for case in positives:
        job = case["job"]
        assert case["expected"]["decision"] == "accept"
        assert job["contract_version"] == contract["contract_version"]
        assert job["state"] in {"paused", "snapshot_locked", "ready_for_acceptance"}
        if job["state"] == "ready_for_acceptance":
            assert job["next_stage"] is None
            assert len(case["receipts"]) == len(stage_ids)
            assert case["expected"]["requires_independent_acceptance"] is True
        else:
            expected_next = case["expected"]["next_stage"]
            assert job["next_stage"] == expected_next
            assert expected_next in stage_ids
            assert len(case["receipts"]) == stage_ids.index(expected_next)


def test_positive_receipts_form_an_identity_stable_chain(vectors: dict[str, Any]) -> None:
    positives = [case for case in vectors["cases"] if case["kind"] == "positive"]
    for case in positives:
        job = case["job"]
        receipts = case["receipts"]
        previous: dict[str, Any] | None = None
        for expected_order, receipt in enumerate(receipts, start=1):
            assert receipt["job_id"] == job["job_id"]
            assert receipt["project_id"] == job["project_id"]
            assert receipt["report"] == job["report"]
            assert receipt["snapshot_id"] == job["snapshot_id"]
            assert receipt["snapshot_sha256"] == job["snapshot_sha256"]
            assert receipt["stage_order"] == expected_order
            assert receipt["status"] == "committed"
            if previous is None:
                assert receipt["predecessor_receipt_id"] is None
            else:
                assert receipt["predecessor_receipt_id"] == previous["receipt_id"]
                assert receipt["input_digest"] == previous["output_digest"]
            previous = receipt


def test_negative_vectors_cover_required_rejection_classes(
    contract: dict[str, Any], vectors: dict[str, Any]
) -> None:
    negative = [case for case in vectors["cases"] if case["kind"] == "negative"]
    expected_codes = {case["expected"]["code"] for case in negative}
    declared_codes = set(contract["recovery"]["rejection_codes"])

    assert {
        "RECEIPT_EXPIRED",
        "RECEIPT_OUT_OF_ORDER",
        "REPORT_MISMATCH",
        "ARTIFACT_DIGEST_MISMATCH",
    } <= expected_codes
    assert expected_codes <= declared_codes


def test_expired_vector_is_unambiguously_expired(vectors: dict[str, Any]) -> None:
    case = _case_map(vectors)["negative-expired-resume"]
    assert _parse_utc(case["job"]["expires_at"]) < _parse_utc(vectors["evaluated_at"])
    assert case["expected"] == {"decision": "reject", "code": "RECEIPT_EXPIRED"}


def test_out_of_order_vector_skips_the_next_stage(
    contract: dict[str, Any], vectors: dict[str, Any]
) -> None:
    case = _case_map(vectors)["negative-out-of-order-stage"]
    stage_ids = [stage["id"] for stage in _stages(contract)]
    assert stage_ids.index(case["job"]["next_stage"]) > len(case["receipts"])
    assert case["expected"]["code"] == "RECEIPT_OUT_OF_ORDER"


def test_cross_report_vector_cannot_reuse_snapshot_identity(vectors: dict[str, Any]) -> None:
    case = _case_map(vectors)["negative-cross-report-contamination"]
    job = case["job"]
    assert job["report"] == "B"
    assert job["snapshot_id"].startswith("snapshot-c-")
    assert case["expected"]["code"] == "REPORT_MISMATCH"


def test_digest_drift_vector_has_distinct_actual_and_recorded_digests(
    vectors: dict[str, Any]
) -> None:
    case = _case_map(vectors)["negative-predecessor-digest-drift"]
    recorded = case["receipts"][0]["output_digest"]
    actual = case["actual_predecessor_output_digest"]
    assert recorded != actual
    assert case["expected"]["code"] == "ARTIFACT_DIGEST_MISMATCH"
