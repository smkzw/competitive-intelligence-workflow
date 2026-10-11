"""Normal presentation-only ABC current transaction; preserve all scientific atoms."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import (
    CurrentPresentationRebuildCommand,
    UserFactEditService,
)
from tools.bundle_contract import validate_portal_asset_mirror

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
PREVIEW = ROOT / ".artifacts/1007-abc-axis-reading-v1"
OUT = ROOT / ".artifacts/1007-abc-reading-current33-v1"
GENERATION = "ae95ab2d09b15076b59b4ab594b476dd0da1df8e177bc573eae8c6e51eb97fb4"
FROZEN = ("fact_versions", "claim_versions", "fact_evidence", "evidence_fragments",
          "source_versions", "source_portal_consumer_bindings", "user_fact_derivations",
          "user_fact_edit_requests")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, data: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=1)


def frozen_tables() -> dict[str, str]:
    with sqlite3.connect((PROJECT / "state/project.sqlite").as_uri()+"?mode=ro", uri=True) as db:
        result = {}
        for name in FROZEN:
            digest = hashlib.sha256()
            for row in db.execute(f"SELECT * FROM {name} ORDER BY 1"):
                digest.update(repr(tuple(row)).encode("utf-8"))
                digest.update(b"\n")
            result[name] = digest.hexdigest()
        return result


def main() -> None:
    assert not OUT.exists(), "Reopen command/return/current/journal, never blind replay"
    validate_portal_asset_mirror(ROOT)
    preview = json.loads((PREVIEW / "actual.json").read_bytes())
    for folder, expected in (("a-qa", 12), ("b-qa", 12)):
        qa = json.loads((PREVIEW / folder / "actual.json").read_bytes())
        assert not qa["failures"] and len(qa["states"]) == expected
    axes = json.loads((PREVIEW / "axis-options.json").read_bytes())
    assert axes["state"] == "BOUNDED_NUMERIC_TICKS_PASS" and len(axes["states"]) == 16
    assert not axes["failures"]
    assert preview["source_generation"] == GENERATION and preview["facts"] == 1505
    for name, digest in preview["author_sha256"].items():
        assert sha(ROOT / "src/ci_workflow/renderers/portal" / name) == digest
    before = read_current_delivery(PROJECT)
    assert before and before.revision == 32 and current_bundle_sha256(before) == GENERATION
    service = UserFactEditService(PROJECT)
    public = service.current_facts()
    assert len(public) == 1505
    frozen = frozen_tables()
    protected = {p.relative_to(PROJECT).as_posix(): sha(p)
        for directory in ("reports", "snapshots") for p in (PROJECT / directory).rglob("*")
        if p.is_file()}
    command = CurrentPresentationRebuildCommand(
        request_id="owner-1007-abc-reading-current33-v1", project_id=before.project_id,
        expected_revision=32, reports=("A", "B", "C"), requested_by="owner-1007-presentation",
        requested_at=datetime.now(UTC),
    )
    OUT.mkdir()
    write("command.json", command.model_dump(mode="json"))
    write("prewrite.json", {"current": before.model_dump(mode="json"),
        "recipe_sha256": sha(Path(__file__)), "protected_files": protected,
        "protected_scope": ["reports", "snapshots"], "frozen_tables": frozen,
        "preview_sha256": sha(PREVIEW / "actual.json"), "author_sha256": preview["author_sha256"],
        "recovery": "Original immutable reports and existing presentation transaction journal",
        "source_only_review": "Separate frozen request/snapshot, no candidate adoption or writes"})
    try:
        after = service.rebuild_current_presentation(command)
        write("rebuild-return.json", after.model_dump(mode="json"))
        assert read_current_delivery(PROJECT) == after and after.revision == 33
        assert after.active_fact_version_ids == before.active_fact_version_ids
        assert service.current_facts() == public and frozen_tables() == frozen
        assert all(sha(PROJECT / name) == digest for name, digest in protected.items())
        for old in before.reports:
            new = next(item for item in after.reports if item.report == old.report)
            assert new.revision == 33
            assert new.builder_input_sha256 == old.builder_input_sha256
            assert new.fact_version_ids == old.fact_version_ids
        write("verified.json", {
            "state": "CURRENT33_ABC_PRESENTATION_COMMITTED_NOT_RELEASE_ACCEPTED",
            "revision": 33, "generation": current_bundle_sha256(after),
            "active_facts_unchanged": 1505, "frozen_tables_unchanged": list(FROZEN),
            "old_files_unchanged": len(protected),
            "reports": {r.report:r.revision for r in after.reports},
            "source_adoptions": 0, "clinical_edits": 0,
            "current": after.model_dump(mode="json"), "author_sha256": preview["author_sha256"],
            "new_current_browser_config_share": "NOT_RUN", "product_state": "REVISE"})
    except Exception as error:
        write("failure.json", {"state": "REOPEN_RETURN_CURRENT_JOURNAL_NO_REPLAY",
                               "error": str(error)})
        raise
    print(json.dumps({"revision": 33, "generation": current_bundle_sha256(after)}), flush=True)


if __name__ == "__main__":
    main()
