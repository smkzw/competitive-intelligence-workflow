"""Prepare recoverable evidence for one new real A+B consumer, before UI writes.

No adoption, edit or source/current write. A browser operation must follow the
normal editor; test values are explicitly user-layer checks, never source facts.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-current14-real-ab-edit-v1"
FACT = "ctgov-atomic-fact_6ac934e661c1a374ea7e55f0"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing preparation: reopen original evidence, never replay UI writes")
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 14
    assert current_bundle_sha256(current) == (
        "7bdaf9709abacfabbfe248e93cfa511c160503d874c59a1290fde5cb731575d0"
    )
    facts = UserFactEditService(PROJECT).current_facts()
    fact = facts[FACT]
    old = json.loads(
        (ROOT / ".artifacts/1007-scoped-ab-current-refresh-v2/prewrite.json").read_bytes()
    )
    assert FACT not in old["old_public_facts"], "Must exercise a newly registered real consumer"
    assert {binding["report"] for binding in fact["consumer_bindings"]} == {"A", "B"}
    assert fact["review_state"] == "accepted" and str(fact["normalized_value"]) == "-67.5"
    assert fact["registry_id"] == "NCT03816891" and fact["period"] == "Week 30"
    assert fact["unit"] == "percentage change" and fact["statistical_form"] == "estimate"
    assert not fact.get("user_edit"), "Do not overwrite an existing user adjustment"
    protected = {p.relative_to(PROJECT).as_posix(): sha(p)
                 for directory in ("reports", "snapshots", "receipts", "evidence/library")
                 for p in (PROJECT / directory).rglob("*") if p.is_file()}
    OUT.mkdir()
    with (sqlite3.connect((PROJECT / "state/project.sqlite").as_uri()+"?mode=ro", uri=True) as db,
          sqlite3.connect(OUT / "database-before.sqlite") as backup):
        db.backup(backup)
    with (OUT / "prewrite.json").open("x") as stream:
        json.dump({
            "state": "PREPARED_READONLY_NO_UI_SAVE_OR_FACT_CHANGE",
            "current": current.model_dump(mode="json"), "selected_fact": fact,
            "all_public_facts_before": facts, "protected_files": protected,
            "backup_sha256": sha(OUT / "database-before.sqlite"),
            "scope": (
                "New normal A+B Vixarelimab source binding,-67.5 percent change; no C dependency"
            ),
            "plan": (
                "Normal UI set-67.4/undo to-67.5/clear/undo to-67.5; "
                "source and other facts preserved"
            ),
            "limits": (
                "Temporary user-layer validation only, not revised clinical source or acceptance"
            ),
        }, stream, ensure_ascii=False, sort_keys=True, indent=1)
    print(json.dumps({"state":"PREPARED_READONLY", "fact":FACT, "source_value":"-67.5"}))


if __name__ == "__main__":
    main()
