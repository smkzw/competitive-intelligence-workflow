"""One append-only registration of exact A/B consumers; no rendering/current.

Preserve all report observations, including unknown arm relationships. Reuse
only previously source-bound clinical questions, not inferred numeric equality.
Exclusive outputs make partial registration recoverable without blind replay.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.b_efficacy_source_views import project_b_efficacy_source_views
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.portal_consumer_registry import (
    SourceRowContext,
    project_b_safety_source_views,
    register_a_source_consumers,
    register_b_shared_source_consumers,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
PREP = ROOT / ".artifacts/1007-scoped-consumer-preparation-v2"
ADOPT = ROOT / ".artifacts/1007-scoped-source-union-adoption-v2"
OUT = PROJECT / "evidence/library/scoped-ab-consumers-v2"
CURRENT_SHA = "7336654514605085b9ee86e3fedaa664e83406f0c358125fa653683767374d24"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def tables() -> dict[str, Counter[str]]:
    with sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {
            n: Counter(
                json.dumps(tuple(r), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for r in db.execute('SELECT * FROM "' + n.replace('"', '""') + '"')
            )
            for n in names
        }


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing registration: reopen stage returns; never blindly replay")
    adopted = json.loads((ADOPT / "verified.json").read_bytes())
    assert adopted["status"] == "NORMAL_SOURCE_ADOPTION_ONLY_NOT_CURRENT_NOT_REPORT_ACCEPTANCE"
    assert adopted["accepted_facts"] == 3989
    assert sha(PROJECT / "reports/current.json") == CURRENT_SHA
    prepared = json.loads((PREP / "proof.json").read_bytes())
    assert sha(PREP / "a-preliminary.json") == prepared["a_sha256"]
    assert sha(PREP / "direct-consumer-candidates.json") == prepared["direct_candidates_sha256"]
    mapping = json.loads((PREP / "direct-consumer-candidates.json").read_bytes())
    versions: dict[str, str] = mapping["row_versions"]
    assert len(versions) == 886
    preliminary = ReportAPortalData.model_validate_json((PREP / "a-preliminary.json").read_bytes())
    returned = json.loads(
        (
            ROOT / ".artifacts/1007-scoped-source-union-ingestion-v2/ingestion-return.json"
        ).read_bytes()
    )
    locked = LockedSnapshot.model_validate(returned["evidence_snapshot"])
    assert locked.snapshot_id == mapping["source_evidence_snapshot_id"]
    snapshot = SnapshotStore(PROJECT).read(locked)
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 11
    original: dict[str, Any] = {}
    for delivery in current.reports:
        if delivery.report in {"A", "B"}:
            assert delivery.builder_input_relative_path is not None
            path = PROJECT / delivery.builder_input_relative_path
            assert sha(path) == delivery.builder_input_sha256
            original[delivery.report] = json.loads(path.read_bytes())
    protected = {
        p: sha(p)
        for directory in ("reports", "snapshots", "receipts", "state/user-fact-builder-inputs")
        for p in (PROJECT / directory).rglob("*")
        if p.is_file()
    }
    old_tables = tables()
    OUT.mkdir()
    with (
        sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True) as db,
        sqlite3.connect(OUT / "database-before.sqlite") as backup,
    ):
        db.backup(backup)
    now = datetime.now(UTC)
    write(
        "prewrite.json",
        {
            "state": "ADOPTED_SOURCE_REGISTERING_NOT_CURRENT",
            "created_at": now.isoformat(),
            "current_sha256": CURRENT_SHA,
            "snapshot": locked.model_dump(mode="json"),
            "adoption_decision_digest": adopted["decision_digest"],
            "backup_sha256": sha(OUT / "database-before.sqlite"),
            "input_hashes": prepared,
            "protected_files": {p.relative_to(PROJECT).as_posix(): h for p, h in protected.items()},
            "tables_before": {n: dict(rows) for n, rows in old_tables.items()},
        },
    )
    try:
        contexts = {
            ref: SourceRowContext(**value) for ref, value in mapping["source_row_contexts"].items()
        }
        a_bindings = register_a_source_consumers(
            PROJECT,
            locked,
            preliminary,
            versions,
            registered_at=now,
            source_row_contexts=contexts,
        )
        write("a-registration-return.json", [b.model_dump(mode="json") for b in a_bindings])
        efficacy = tuple(
            {**v, "source_fact_version_id": versions[f"efficacy:{v['row_id']}"]}
            for v in project_b_efficacy_source_views(
                PROJECT,
                locked,
                preliminary,
                {ref: version for ref, version in versions.items() if ref.startswith("efficacy:")},
            )
        )
        safety = project_b_safety_source_views(
            PROJECT,
            locked,
            preliminary,
            {ref: version for ref, version in versions.items() if ref.startswith("safety:")},
        )
        measures = {(v["source_version_id"], v["source_measure_path"]): v for v in efficacy}
        questions = original["A"]["efficacy_views"]["clinical_questions"]
        for question in questions:
            view = measures[(question["source_version_id"], question["source_measure_path"])]
            refs = {r["reference_id"] for r in view["source_clause_context"]["continuations"]}
            assert set(question["basis_reference_ids"]) <= refs
        assert len(questions) == 35
        old_safety = {v["row_id"]: v for v in original["B"]["safety_views"]["facts"]}
        old_safety.update({v["row_id"]: v for v in safety})
        views = {"coverage_mode": "partial", "facts": efficacy, "clinical_questions": questions}
        safety_views = {"coverage_mode": "partial", "facts": tuple(old_safety.values())}
        a = ReportAPortalData.model_validate(
            {
                **preliminary.model_dump(mode="json"),
                "efficacy_views": views,
                "safety_views": safety_views,
                "report_version": "v1-1007-scoped-source-v2",
            }
        )
        b = ReportBPortalData.model_validate(
            {
                **original["B"],
                "trials": a.model_dump(mode="json")["trials"],
                "efficacy": a.model_dump(mode="json")["efficacy"],
                "safety": a.model_dump(mode="json")["safety"],
                "additional_observations": a.model_dump(mode="json")["additional_observations"],
                "source_evidence_snapshot_id": locked.snapshot_id,
                "efficacy_views": views,
                "safety_views": safety_views,
                "report_version": "v1-1007-scoped-source-v2",
            }
        )
        b_bindings = register_b_shared_source_consumers(
            PROJECT,
            locked,
            b,
            versions,
            registered_at=now,
        )
        write(
            "b-registration-return.json",
            [binding.model_dump(mode="json") for binding in b_bindings],
        )
        write("a-input.json", a.model_dump(mode="json"))
        write("b-input.json", b.model_dump(mode="json"))
        after = tables()
        assert set(after) == set(old_tables)
        for name, rows in old_tables.items():
            assert not (rows - after[name]), name
            if name != "source_portal_consumer_bindings":
                assert rows == after[name], name
        assert all(sha(p) == h for p, h in protected.items())
        assert sha(PROJECT / "reports/current.json") == CURRENT_SHA
        assert len(a_bindings) == len(b_bindings) == 886
        write(
            "verified.json",
            {
                "state": "LEGAL_AB_REGISTERED_ORDINARY_INPUTS_READY_NOT_CURRENT",
                "snapshot": locked.model_dump(mode="json"),
                "a_bindings": len(a_bindings),
                "b_bindings": len(b_bindings),
                "efficacy_source_views": len(efficacy),
                "direct_safety_source_views": len(safety),
                "descriptive_question_mappings_reused_exact": len(questions),
                "a_rows": len(a.efficacy) + len(a.safety),
                "trials": len(a.trials),
                "input_hashes": {kind: sha(OUT / f"{kind}-input.json") for kind in ("a", "b")},
                "old_scientific_rows_and_current_preserved": True,
                "limits": (
                    "No render/current/edit/share/universe/clinical-equivalence/RC acceptance"
                ),
                "locked_source_fact_count": len(snapshot["fact_version_ids"]),
            },
        )
    except Exception as error:
        write(
            "failure.json",
            {
                "state": "FAILED_REOPEN_STAGE_RETURNS_BEFORE_RETRY",
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
        raise
    print(
        json.dumps({"state": "REGISTERED_NOT_CURRENT", "a": len(a_bindings), "b": len(b_bindings)})
    )


if __name__ == "__main__":
    main()
