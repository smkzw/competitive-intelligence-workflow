"""Collect completed isolated A/B registrations after the original pin failure.

No registration/replay/ingestion/adoption/render/save. Preserve the original
FAIL. Compare durable files and all database rows; WAL/SHM are SQLite connection
coordination files, not scientific state. The initial transient cause was not
captured and remains an inference, never retroactively a PASS.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-arm-consumers-isolated-v1"
COORDINATION = {"state/project.sqlite-wal", "state/project.sqlite-shm"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tables(path: Path) -> dict[str, Counter[str]]:
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as database:
        names = [r[0] for r in database.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        return {name: Counter(json.dumps(tuple(row), ensure_ascii=False) for row in
                             database.execute('SELECT * FROM "'
                                              + name.replace('"', '""') + '"'))
                for name in names}


def main() -> None:
    destination = OUT / "recovery-verified.json"
    assert not destination.exists(), "Completed collection must not be replayed"
    original = json.loads((OUT / "prewrite.json").read_bytes())
    failure = json.loads((OUT / "failure.json").read_bytes())
    assert failure["type"] == "AssertionError" and failure["live_project_unchanged"] is True
    current = read_current_delivery(PROJECT)
    assert current is not None and current_bundle_sha256(current) == original["generation"]
    expected = {k: v for k, v in original["live_pins"].items() if k not in COORDINATION}
    actual = {p.relative_to(PROJECT).as_posix(): sha(p) for p in PROJECT.rglob("*")
              if p.is_file() and p.name != "user-fact-edit.lock"
              and p.relative_to(PROJECT).as_posix() not in COORDINATION}
    assert actual == expected, "A durable source/current/user/history file differs"
    live = tables(PROJECT / "state/project.sqlite")
    copied = tables(OUT / "project/state/project.sqlite")
    assert copied.keys() == live.keys()
    added_count = 0
    for name, rows in live.items():
        if name == "source_portal_consumer_bindings":
            assert not rows - copied[name], "Original bindings lost in copy"
            added_count = sum((copied[name] - rows).values())
            assert added_count == 698
        else:
            assert copied[name] == rows, ("Scientific/user/current table differs", name)
    mapping = json.loads((OUT / "new-row-versions.json").read_bytes())["row_versions"]
    assert len(mapping) == len(set(mapping.values())) == 349
    for report in ("a", "b"):
        returned = json.loads((OUT / f"{report}-registration-return.json").read_bytes())
        assert len(returned) == 349
        with sqlite3.connect((OUT / "project/state/project.sqlite").resolve().as_uri()
                             + "?mode=ro", uri=True) as database:
            for item in returned:
                binding = ActiveFactBinding.model_validate(item)
                ref = f"{binding.collection}:{binding.row_id}"
                stored = database.execute(
                    "SELECT binding_json,binding_sha256 FROM source_portal_consumer_bindings "
                    "WHERE evidence_snapshot_id=? AND report=? AND source_fact_version_id=?",
                    (original["source_snapshot"]["snapshot_id"], report.upper(), mapping[ref]),
                ).fetchone()
                assert stored is not None and json.loads(stored[0]) == item
                assert hashlib.sha256(stored[0].encode()).hexdigest() == stored[1]
    result = {
        "state": "READ_ONLY_RECOVERY_ISOLATED_AB_BINDINGS_VERIFIED_ORIGINAL_FAIL_RETAINED",
        "generation": original["generation"], "script_sha256": sha(Path(__file__)),
        "prewrite_sha256": sha(OUT / "prewrite.json"),
        "original_failure_sha256": sha(OUT / "failure.json"),
        "a_return_sha256": sha(OUT / "a-registration-return.json"),
        "b_return_sha256": sha(OUT / "b-registration-return.json"),
        "mapping_sha256": sha(OUT / "new-row-versions.json"),
        "new_atoms": 349, "copy_added_bindings": added_count,
        "unchanged_live_durable_files": len(expected), "exact_database_tables": len(live),
        "same_user_current_scientific_rows": True, "replayed_registrations": 0,
        "live_registrations": 0, "adoptions": 0, "renders": 0, "saves": 0,
        "cause": "Original mismatch not captured; concurrent WAL/SHM plausible only. "
                 "Read-only copy probe actually produced SQLite WAL/SHM in WAL mode. "
                 "Durable byte and all-table equality verified after original completion.",
        "limits": "Copy-only guard result, not live current/clinical coaxis/visual/RC",
    }
    with destination.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=1)
    print(json.dumps({"state": result["state"], "new_AB_atoms": 349}))


if __name__ == "__main__":
    main()
