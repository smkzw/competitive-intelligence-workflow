"""One real normal source refresh after adopted-source consumer registration.

Persist the exact command and API return before postconditions. Never rerun an
existing attempt blindly; current, user clears, C and all historical files are
checked independently from candidate counts or model confidence.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.source_current_refresh import (
    SourceCurrentRefreshCommand,
    SourceCurrentRefreshService,
    SourceFactAddition,
    SourceReportBuilderInput,
)
from ci_workflow.application.user_fact_edit import UserFactEditService
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
REGISTER = PROJECT / "evidence/library/scoped-ab-consumers-v2"
PREP = ROOT / ".artifacts/1007-scoped-consumer-preparation-v2"
OUT = ROOT / ".artifacts/1007-scoped-ab-current-refresh-v2"
CURRENT_SHA = "7336654514605085b9ee86e3fedaa664e83406f0c358125fa653683767374d24"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing refresh: reopen command/API return/current; never blind replay")
    registration = json.loads((REGISTER / "verified.json").read_bytes())
    assert registration["state"] == "LEGAL_AB_REGISTERED_ORDINARY_INPUTS_READY_NOT_CURRENT"
    assert sha(PROJECT / "reports/current.json") == CURRENT_SHA
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 11
    public = UserFactEditService(PROJECT).current_facts()
    assert len(public) == 349
    locked = LockedSnapshot.model_validate(registration["snapshot"])
    snapshot = SnapshotStore(PROJECT).read(locked)
    facts = {r["fact_version_id"]: r for r in snapshot["closure"]["facts"]}
    source_ids = {
        r["capture"]["source_id"]: r["source_version_id"] for r in snapshot["closure"]["sources"]
    }
    mapping = json.loads((PREP / "direct-consumer-candidates.json").read_bytes())["row_versions"]
    additions = tuple(
        SourceFactAddition(
            fact_id=facts[v]["fact"]["fact_id"],
            fact_version_id=v,
            source_version_id=source_ids[facts[v]["fact"]["source_id"]],
            rationale_zh="固定登记版本的精确原子已正式复核采用，A/B合法消费者均已登记。",
        )
        for v in sorted(mapping.values())
        if facts[v]["fact"]["fact_id"] not in public
    )
    assert len(additions) == 795
    pins = tuple(
        SourceReportBuilderInput(
            report=kind,
            input_relative_path=(REGISTER / f"{kind.lower()}-input.json")
            .relative_to(PROJECT)
            .as_posix(),
            input_sha256=registration["input_hashes"][kind.lower()],
        )
        for kind in ("A", "B")
    )
    for pin in pins:
        assert sha(PROJECT / pin.input_relative_path) == pin.input_sha256
    now = datetime.now(UTC)
    command = SourceCurrentRefreshCommand(
        request_id="owner-1007-scoped-ab-current-v2",
        project_id=current.project_id,
        expected_revision=11,
        requested_by="owner-1007-scoped-source-v2",
        requested_at=now,
        additions=additions,
        builder_inputs=pins,
    )
    protected = {
        p: sha(p)
        for directory in (
            "reports",
            "snapshots",
            "receipts",
            "evidence/library",
            "state/user-fact-builder-inputs",
        )
        for p in (PROJECT / directory).rglob("*")
        if p.is_file() and p != PROJECT / "reports/current.json"
    }
    with sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        original_facts = {row[0]: tuple(row) for row in db.execute("SELECT * FROM fact_versions")}
    OUT.mkdir()
    with (
        sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True) as db,
        sqlite3.connect(OUT / "database-before.sqlite") as backup,
    ):
        db.backup(backup)
    write("command.json", command.model_dump(mode="json"))
    write(
        "prewrite.json",
        {
            "state": "SOURCE_REFRESH_READY_NOT_CURRENT",
            "created_at": now.isoformat(),
            "old_current": current.model_dump(mode="json"),
            "old_public_facts": public,
            "current_sha256": CURRENT_SHA,
            "backup_sha256": sha(OUT / "database-before.sqlite"),
            "protected_files": {p.relative_to(PROJECT).as_posix(): h for p, h in protected.items()},
            "command_sha256": sha(OUT / "command.json"),
        },
    )
    try:
        result = SourceCurrentRefreshService(PROJECT).refresh(command)
        write("refresh-return.json", result.model_dump(mode="json"))
        after = read_current_delivery(PROJECT)
        assert after is not None and after.revision == 12
        assert result.rebuilt_reports == ("A", "B")
        assert after.project_id == current.project_id
        assert next(r for r in after.reports if r.report == "C") == next(
            r for r in current.reports if r.report == "C"
        )
        assert set(current.active_fact_version_ids) <= set(after.active_fact_version_ids)
        assert len(after.active_fact_version_ids) == 1144
        latest_public = UserFactEditService(PROJECT).current_facts()
        assert len(latest_public) == 1144
        for fact_id, original in public.items():
            assert latest_public[fact_id] == original, fact_id
        with sqlite3.connect(
            (PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True
        ) as db:
            latest_facts = {row[0]: tuple(row) for row in db.execute("SELECT * FROM fact_versions")}
        assert original_facts == latest_facts
        assert all(sha(p) == h for p, h in protected.items())
        write(
            "verified.json",
            {
                "state": "REAL_SOURCE_REFRESH_COMMITTED_BROWSER_ACCEPTANCE_PENDING",
                "current_revision": 12,
                "reports": "A12/B12/C9",
                "active_facts": len(after.active_fact_version_ids),
                "new_source_facts": len(additions),
                "old_user_and_source_facts_preserved": len(public),
                "unchanged_original_files": len(protected),
                "current_sha256": sha(PROJECT / "reports/current.json"),
                "generation_sha256": result.current_generation_sha256,
                "limits": (
                    "Not browser/visual/config/share/full-universe/freshness/MAH/"
                    "clinical-equivalence/install/three-host/24-portal/RC acceptance"
                ),
            },
        )
    except Exception as error:
        write(
            "failure.json",
            {
                "state": "FAILED_REOPEN_RETURN_AND_CURRENT_BEFORE_RETRY",
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
        raise
    print(
        json.dumps({"revision": after.revision, "active_facts": len(after.active_fact_version_ids)})
    )


if __name__ == "__main__":
    main()
