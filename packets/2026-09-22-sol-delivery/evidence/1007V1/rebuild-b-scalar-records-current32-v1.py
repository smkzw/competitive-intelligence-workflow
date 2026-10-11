"""Commit only B presentation after the exact normal preview passes real Ego QA.

The existing journal recovers the immutable previous current; no duplicate SQL
backup or replay of clinical saves/source adoption is needed for presentation.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import (
    CurrentPresentationRebuildCommand,
    UserFactEditService,
)

BASE = Path(__file__).with_name("rebuild-compact-provenance-current13-v1.py")
SPEC = importlib.util.spec_from_file_location("existing_presentation_protection", BASE)
assert SPEC is not None and SPEC.loader is not None
util = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(util)
ROOT, PROJECT = util.ROOT, util.PROJECT
OUT = ROOT / ".artifacts/1007-b-scalar-records-current32-v1"
PREVIEW = ROOT / ".artifacts/1007-b-scalar-records-preview-v2"
GENERATION = "16a5fbb6c99e36b7578ad51280e2fb4b7da23c64cfed27eb73c846974d968dfa"


def main() -> None:
    assert not OUT.exists(), "Reopen saved return/current/journal; do not blindly replay"
    preview = json.loads((PREVIEW / "actual.json").read_bytes())
    qa = json.loads((PREVIEW / "qa/actual.json").read_bytes())
    assert qa["state"] == "SCOPED_REAL_B_SCALAR_RECORDS_PASSED_OWNER_PIXELS_PENDING"
    assert not qa["failures"] and len(qa["states"]) == 24
    assert qa["render_proof_sha256"] == util.sha(PREVIEW / "actual.json")
    assert preview["source_generation"] == GENERATION and preview["facts"] == 1505
    for name, digest in preview["author_sha256"].items():
        assert util.sha(ROOT / "src/ci_workflow/renderers/portal" / name) == digest
    for name in ("report-b.js", "report-b.css"):
        assert util.sha(ROOT / "assets/portal" / name) == preview["author_sha256"][
            "assets/" + name
        ]
    before = read_current_delivery(PROJECT)
    assert before is not None and before.revision == 31
    assert current_bundle_sha256(before) == GENERATION
    service = UserFactEditService(PROJECT)
    public, frozen = service.current_facts(), util.tables()
    assert len(public) == 1505
    protected = {
        p.relative_to(PROJECT).as_posix(): util.sha(p)
        for directory in ("reports", "snapshots", "receipts", "evidence/library")
        for p in (PROJECT / directory).rglob("*")
        if p.is_file() and p != PROJECT / "reports/current.json"
    }
    command = CurrentPresentationRebuildCommand(
        request_id="owner-1007-b-scalar-records-current32-v1", project_id=before.project_id,
        expected_revision=31, reports=("B",), requested_by="owner-1007-presentation",
        requested_at=datetime.now(UTC),
    )
    OUT.mkdir()
    util.OUT = OUT
    util.write("command.json", command.model_dump(mode="json"))
    util.write("prewrite.json", {
        "current": before.model_dump(mode="json"), "recipe_sha256": util.sha(Path(__file__)),
        "helper_sha256": util.sha(BASE), "protected_files": protected,
        "preview_sha256": util.sha(PREVIEW / "actual.json"),
        "qa_sha256": util.sha(PREVIEW / "qa/actual.json"),
        "assets": preview["author_sha256"],
        "recovery": "Existing immutable current reports plus presentation transaction journal",
    })
    try:
        after = service.rebuild_current_presentation(command)
        util.write("rebuild-return.json", after.model_dump(mode="json"))
        assert read_current_delivery(PROJECT) == after and after.revision == 32
        assert after.active_fact_version_ids == before.active_fact_version_ids
        assert service.current_facts() == public and util.tables() == frozen
        for kind in ("A", "C"):
            assert next(r for r in after.reports if r.report == kind) == next(
                r for r in before.reports if r.report == kind
            )
        assert all(util.sha(PROJECT / name) == digest for name, digest in protected.items())
        util.write("verified.json", {
            "state": "CURRENT32_B_ONLY_COMMITTED_NOT_PRODUCT_OR_SCIENCE_ACCEPTANCE",
            "revision": 32, "generation": current_bundle_sha256(after),
            "facts_unchanged": 1505, "frozen_tables_unchanged": list(util.FROZEN_TABLES),
            "old_files_unchanged": len(protected),
            "reports": {r.report: r.revision for r in after.reports},
            "current": after.model_dump(mode="json"), "assets": preview["author_sha256"],
            "limits": "No clinical save/source adoption/refresh; new-current pixels/share pending",
        })
    except Exception as error:
        util.write("failure.json", {"state": "REOPEN_RETURN_CURRENT_AND_JOURNAL_NO_REPLAY",
                                    "reason": str(error)})
        raise
    print(json.dumps({"revision": after.revision, "generation": current_bundle_sha256(after)}))


if __name__ == "__main__":
    main()
