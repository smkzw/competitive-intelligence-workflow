"""One recoverable, real newly adopted TESAE A+B UI chain; no replay or edit."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-current23-tesae-ui-v1"
FACT = "ctgov-atomic-fact_35c576f0fcfbdfad41e5b900"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Reopen pending/current/return; do not repeat writes"
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 23
    assert current_bundle_sha256(current) == (
        "345d5b21c76de3f9383a54b80c1705bf0c8febaf042e2d6b0a5ee530b8179e98"
    )
    facts = UserFactEditService(PROJECT).current_facts()
    fact = facts[FACT]
    assert len(facts) == 1505 and fact["normalized_value"] == "2"
    assert fact["registry_id"] == "NCT04202679" and not fact.get("user_edit")
    assert fact["review_state"] == "accepted"
    assert {b["report"] for b in fact["consumer_bindings"]} == {"A", "B"}
    assert all(b["row_id"] == "safe-e5e0b4524553ae12affb" for b in fact["consumer_bindings"])
    protected = {p.relative_to(PROJECT).as_posix(): sha(p)
                 for directory in ("reports", "snapshots", "receipts", "evidence/library")
                 for p in (PROJECT / directory).rglob("*") if p.is_file()
                 and p != PROJECT / "reports/current.json"}
    OUT.mkdir()
    with (sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro",
                         uri=True) as db, sqlite3.connect(OUT / "database-before.sqlite") as old):
        db.backup(old)
    with (OUT / "prewrite.json").open("x") as stream:
        json.dump({"state": "PREPARED_READONLY_NOT_UI_ACCEPTED", "current":
                   current.model_dump(mode="json"), "selected_fact": fact,
                   "all_public_facts_before": facts, "protected_files": protected,
                   "backup_sha256": sha(OUT / "database-before.sqlite"),
                   "recipe_sha256": sha(Path(__file__)),
                   "plan": "Normal editor2→3,undo2,clear,undo2. Temporary user-layer only.",
                   "limits": "No source correction, scientific acceptance, coaxis or release"},
                  stream, ensure_ascii=False, sort_keys=True, indent=1)
    print(json.dumps({"state": "READONLY_PREPARED", "fact": FACT, "facts": len(facts)}))


if __name__ == "__main__":
    main()
