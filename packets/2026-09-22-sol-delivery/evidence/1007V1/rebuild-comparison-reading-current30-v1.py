"""One presentation-only ABC generation after terminal worker integration.

Keep current29 facts/source/user history exact; never replay prior transactions.
The exclusive attempt stores command/backup/return before postcondition checks.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import (
    CurrentPresentationRebuildCommand,
    UserFactEditService,
)

BASE = Path(__file__).with_name("rebuild-compact-provenance-current13-v1.py")
SPEC = importlib.util.spec_from_file_location("protected_presentation_helpers", BASE)
assert SPEC is not None and SPEC.loader is not None
util = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(util)
ROOT, PROJECT = util.ROOT, util.PROJECT
OUT = ROOT / ".artifacts/1007-comparison-reading-current30-v1"
GENERATION = "d257be432fe94b31f6bc047d77162aa64aa59cd24f3b6f4cea56446d7124492b"


def main() -> None:
    assert not OUT.exists(), "Read existing return/current; never blindly replay"
    restored = json.loads((ROOT / ".artifacts/1007-comparison-reading-current29-v1"
                           / "verified.json").read_bytes())
    offline = json.loads((ROOT / ".artifacts/1007-current28-shares-v1"
                          / "offline-actual-v1.json").read_bytes())
    assert offline["revision"] == 28 and len(offline["pages"]) == 6
    assert not offline["failures"] and offline["network_restored"]
    before = read_current_delivery(PROJECT)
    assert before is not None and before.revision == restored["revision"] == 29
    assert current_bundle_sha256(before) == restored["generation"] == GENERATION
    assert len(before.active_fact_version_ids) == 1505
    assets = {}
    for name in ("portal.css", "report-b.css", "report-b.js"):
        author = ROOT / "src/ci_workflow/renderers/portal/assets" / name
        assert util.sha(author) == util.sha(ROOT / "assets/portal" / name)
        assets[name] = util.sha(author)
    source_set = {
        path.relative_to(ROOT).as_posix(): util.sha(path)
        for path in (ROOT / "src/ci_workflow/renderers/portal").rglob("*")
        if path.is_file() and path.suffix in (".py", ".js", ".css", ".j2")
    }
    service = UserFactEditService(PROJECT)
    public_before, frozen = service.current_facts(), util.tables()
    protected = {
        path.relative_to(PROJECT).as_posix(): util.sha(path)
        for directory in ("reports", "snapshots", "receipts", "evidence/library")
        for path in (PROJECT / directory).rglob("*")
        if path.is_file() and path != PROJECT / "reports/current.json"
    }
    command = CurrentPresentationRebuildCommand(
        request_id="owner-1007-comparison-reading-current30-v1", project_id=before.project_id,
        expected_revision=29, reports=("A", "B", "C"), requested_by="owner-1007-presentation",
        requested_at=datetime.now(UTC),
    )
    OUT.mkdir()
    util.OUT = OUT
    with (sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro",
                         uri=True) as db,
          sqlite3.connect(OUT / "database-before.sqlite") as backup):
        db.backup(backup)
    util.write("command.json", command.model_dump(mode="json"))
    util.write("prewrite.json", {
        "state": "ABC_PRESENTATION_READY_NOT_CLINICAL_ACCEPTANCE", "current":
        before.model_dump(mode="json"), "recipe_sha256": util.sha(Path(__file__)),
        "helper_sha256": util.sha(BASE), "assets": assets, "source_set": source_set,
        "protected_files": protected, "backup_sha256": util.sha(OUT / "database-before.sqlite"),
    })
    try:
        result = service.rebuild_current_presentation(command)
        util.write("rebuild-return.json", result.model_dump(mode="json"))
        after = read_current_delivery(PROJECT)
        assert after == result and after.revision == 30
        assert after.active_fact_version_ids == before.active_fact_version_ids
        assert service.current_facts() == public_before and util.tables() == frozen
        assert all(util.sha(PROJECT / path) == digest for path, digest in protected.items())
        assert all(util.sha(ROOT / path) == digest for path, digest in source_set.items())
        assert {report.report: report.revision for report in after.reports} == {
            "A": 30, "B": 30, "C": 30,
        }
        util.write("verified.json", {
            "state": "CURRENT30_ABC_PRESENTATION_COMMITTED_NOT_PRODUCT_ACCEPTANCE",
            "revision": after.revision, "generation": current_bundle_sha256(after),
            "facts_unchanged": len(public_before), "science_user_tables_unchanged":
            list(util.FROZEN_TABLES), "old_files_unchanged": len(protected),
            "assets": assets, "current": after.model_dump(mode="json"),
            "limits": "No new source acceptance/equivalence/universe/pixels/share/hosts/24/RC",
        })
    except Exception as error:
        util.write("failure.json", {"state": "REOPEN_RETURN_CURRENT_BEFORE_RECOVERY",
                                    "type": type(error).__name__, "reason": str(error)})
        raise
    print(json.dumps({"revision": after.revision, "generation": current_bundle_sha256(after)}))


if __name__ == "__main__":
    main()


