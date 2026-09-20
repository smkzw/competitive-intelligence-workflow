from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ci_workflow.application.ppt_master_job import (
    STAGE_IDS,
    ExecutionLease,
    LockedReportSnapshot,
    PptMasterJobError,
    PptMasterJobStore,
    PptMasterLeaseStore,
    StageArtifact,
    begin_stage,
    build_receipt,
    commit_receipt,
    create_job,
    lock_snapshot,
    pause_job,
    resume_job,
)

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 31, 12, tzinfo=UTC)
DIGEST = "a" * 64


def _snapshot(report: str = "A") -> LockedReportSnapshot:
    return LockedReportSnapshot(
        project_id="project-demo",
        report=report,
        report_version=f"{report.lower()}-v1",
        snapshot_id=f"snapshot-{report.lower()}-001",
        snapshot_sha256=DIGEST,
        claim_snapshot_id=f"claims-{report.lower()}-001",
        evidence_snapshot_id=f"evidence-{report.lower()}-001",
        coverage_set_id=f"coverage-{report.lower()}-001",
        locked_at=NOW,
    )


def _artifact(root: Path, name: str, content: bytes) -> StageArtifact:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return StageArtifact(
        relative_path=name,
        sha256=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
    )


def _commit(job, *, stage_id: str, artifact: StageArtifact, minute: int):
    running = begin_stage(job, stage_id=stage_id, now=NOW + timedelta(minutes=minute))
    receipt = build_receipt(
        job=running,
        receipt_id=f"receipt-{minute:02d}",
        stage_id=stage_id,
        attempt=1,
        input_digest="b" * 64,
        artifacts=(artifact,),
        status="committed",
        committed_at=NOW + timedelta(minutes=minute + 1),
    )
    return commit_receipt(running, receipt)


def test_json_schema_and_pydantic_accept_same_new_job() -> None:
    job = create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=2))
    payload = job.model_dump(mode="json")
    schema = json.loads((ROOT / "schemas/ppt-master-job.schema.json").read_text())

    Draft202012Validator(schema).validate(payload)
    assert payload["next_stage"] == "initialize"


def test_stage_receipts_advance_exactly_once_and_finish_at_independent_acceptance(
    tmp_path: Path,
) -> None:
    artifact = _artifact(tmp_path, "work/stage.txt", b"complete")
    job = lock_snapshot(
        create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=3)),
        now=NOW,
    )
    for index, stage_id in enumerate(STAGE_IDS):
        job = _commit(job, stage_id=stage_id, artifact=artifact, minute=index * 2 + 1)

    assert job.state == "ready_for_acceptance"
    assert job.next_stage is None
    assert len(job.receipts) == 9


def test_out_of_order_stage_is_rejected_before_receipt(tmp_path: Path) -> None:
    job = lock_snapshot(
        create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=2)),
        now=NOW,
    )

    with pytest.raises(PptMasterJobError, match="不能跳过") as caught:
        begin_stage(job, stage_id="page_svg", now=NOW)
    assert caught.value.code == "RECEIPT_OUT_OF_ORDER"
    assert not (tmp_path / "work").exists()


def test_pause_and_resume_checks_predecessor_artifacts(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path, "work/init.json", b"locked")
    job = lock_snapshot(
        create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=2)),
        now=NOW,
    )
    job = pause_job(
        _commit(job, stage_id="initialize", artifact=artifact, minute=1),
        now=NOW + timedelta(minutes=3),
    )
    resumed = resume_job(
        job,
        now=NOW + timedelta(minutes=10),
        project_id="project-demo",
        report="A",
        snapshot_id="snapshot-a-001",
        snapshot_sha256=DIGEST,
        artifact_root=tmp_path,
    )

    assert resumed.state == "snapshot_locked"
    assert resumed.next_stage == "content_design_lock"


def test_expired_resume_is_rejected_without_mutation(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path, "work/init.json", b"locked")
    job = lock_snapshot(
        create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(minutes=5)),
        now=NOW,
    )
    job = pause_job(
        _commit(job, stage_id="initialize", artifact=artifact, minute=1),
        now=NOW + timedelta(minutes=3),
    )
    before = job.model_dump_json()

    with pytest.raises(PptMasterJobError) as caught:
        resume_job(
            job,
            now=NOW + timedelta(minutes=6),
            project_id="project-demo",
            report="A",
            snapshot_id="snapshot-a-001",
            snapshot_sha256=DIGEST,
            artifact_root=tmp_path,
        )
    assert caught.value.code == "RECEIPT_EXPIRED"
    assert job.model_dump_json() == before


@pytest.mark.parametrize(
    ("report", "snapshot_id", "code"),
    [("B", "snapshot-a-001", "REPORT_MISMATCH"), ("A", "snapshot-c-001", "SNAPSHOT_MISMATCH")],
)
def test_cross_report_or_snapshot_reuse_is_rejected(
    tmp_path: Path, report: str, snapshot_id: str, code: str
) -> None:
    artifact = _artifact(tmp_path, "work/init.json", b"locked")
    job = lock_snapshot(
        create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=2)),
        now=NOW,
    )
    job = pause_job(
        _commit(job, stage_id="initialize", artifact=artifact, minute=1),
        now=NOW + timedelta(minutes=3),
    )

    with pytest.raises(PptMasterJobError) as caught:
        resume_job(
            job,
            now=NOW + timedelta(minutes=10),
            project_id="project-demo",
            report=report,
            snapshot_id=snapshot_id,
            snapshot_sha256=DIGEST,
            artifact_root=tmp_path,
        )
    assert caught.value.code == code


def test_changed_predecessor_artifact_is_rejected(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path, "work/init.json", b"locked")
    job = lock_snapshot(
        create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=2)),
        now=NOW,
    )
    job = pause_job(
        _commit(job, stage_id="initialize", artifact=artifact, minute=1),
        now=NOW + timedelta(minutes=3),
    )
    (tmp_path / artifact.relative_path).write_bytes(b"changed")

    with pytest.raises(PptMasterJobError) as caught:
        resume_job(
            job,
            now=NOW + timedelta(minutes=10),
            project_id="project-demo",
            report="A",
            snapshot_id="snapshot-a-001",
            snapshot_sha256=DIGEST,
            artifact_root=tmp_path,
        )
    assert caught.value.code == "ARTIFACT_DIGEST_MISMATCH"


def test_job_store_round_trips_and_rejects_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "jobs" / "job-a.json"
    store = PptMasterJobStore(path)
    job = create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=2))
    store.save(job)
    assert store.load() == job

    path.write_text("not json", encoding="utf-8")
    with pytest.raises(PptMasterJobError) as caught:
        store.load()
    assert caught.value.code == "JOB_NOT_FOUND"


def test_global_lease_serializes_different_reports(tmp_path: Path) -> None:
    store = PptMasterLeaseStore(tmp_path / "runtime" / "ppt-master-global-lock.json")
    lease_a = ExecutionLease(
        schema_version="1.0",
        lock_name="ppt_master_global",
        job_id="job-a",
        project_id="project-demo",
        report="A",
        snapshot_id="snapshot-a-001",
        owner_id="owner-a",
        acquired_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    lease_b = lease_a.model_copy(
        update={
            "job_id": "job-b",
            "report": "B",
            "snapshot_id": "snapshot-b-001",
            "owner_id": "owner-b",
        }
    )
    store.acquire(lease_a, now=NOW)

    with pytest.raises(PptMasterJobError) as caught:
        store.acquire(lease_b, now=NOW + timedelta(minutes=1))
    assert caught.value.code == "ACTIVE_LOCK_CONFLICT"
    store.release(job_id="job-a", owner_id="owner-a")
    store.acquire(lease_b, now=NOW + timedelta(minutes=1))


def test_receipt_tampering_is_rejected(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path, "work/init.json", b"locked")
    job = begin_stage(
        lock_snapshot(
            create_job(job_id="job-a", snapshot=_snapshot(), now=NOW, ttl=timedelta(hours=2)),
            now=NOW,
        ),
        stage_id="initialize",
        now=NOW,
    )
    receipt = build_receipt(
        job=job,
        receipt_id="receipt-1",
        stage_id="initialize",
        attempt=1,
        input_digest="b" * 64,
        artifacts=(artifact,),
        status="committed",
        committed_at=NOW,
    )
    payload = receipt.model_dump(mode="json")
    payload["receipt_sha256"] = "0" * 64

    with pytest.raises(ValidationError, match="收据摘要"):
        type(receipt).model_validate(payload)
