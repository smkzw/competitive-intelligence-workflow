"""One normal presentation rebuild, after owner accepts the bounded asset diff.

No fact edit/source acceptance/refresh. A/B advance together; C and all source,
fact, user-clear and historical bytes are retained. Exclusive evidence prevents
blind replay; the API return is durable before postcondition checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import (
    CurrentPresentationRebuildCommand,
    UserFactEditService,
)

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-compact-provenance-current13-v1"
FROZEN_TABLES = (
    "fact_versions", "fact_evidence", "evidence_fragments", "source_versions",
    "source_portal_consumer_bindings", "user_fact_derivations", "user_fact_edit_requests",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, payload: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=1)


def tables() -> dict[str, tuple[tuple[object, ...], ...]]:
    with sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        return {name: tuple(db.execute(f"SELECT * FROM {name} ORDER BY 1"))
                for name in FROZEN_TABLES}


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", type=int, default=12)
    parser.add_argument("--expected-generation", default=(
        "4cdbfeb77e4e4cbffb9eb4ac3318e118cc04951bb3d8c985eda47aacf3d9b284"
    ))
    parser.add_argument("--attempt-id", default="1007-compact-provenance-current13-v1")
    args = parser.parse_args()
    if not re.fullmatch(r"1007-[a-z0-9-]+", args.attempt_id):
        raise SystemExit("Attempt must be an explicit exclusive1007 evidence directory")
    OUT = ROOT / ".artifacts" / args.attempt_id
    target_revision = args.expected_revision + 1
    if OUT.exists():
        raise SystemExit(
            "Existing attempt: reopen original command/return/current, never blind retry"
        )
    before = read_current_delivery(PROJECT)
    assert before is not None and before.revision == args.expected_revision
    assert current_bundle_sha256(before) == args.expected_generation
    assert len(before.active_fact_version_ids) == 1144
    asset_hashes = {}
    for name in ("portal.js", "report-a.js", "report-b.js", "kangzhe-site.css"):
        author = ROOT / "src/ci_workflow/renderers/portal/assets" / name
        assert sha(author) == sha(ROOT / "assets/portal" / name), "Mirror must be synchronized"
        asset_hashes[name] = sha(author)
    service = UserFactEditService(PROJECT)
    public_before = service.current_facts()
    frozen = tables()
    protected = {p.relative_to(PROJECT).as_posix(): sha(p)
                 for directory in ("reports", "snapshots", "receipts", "evidence/library")
                 for p in (PROJECT / directory).rglob("*") if p.is_file()}
    command = CurrentPresentationRebuildCommand(
        request_id="owner-" + args.attempt_id,
        project_id=before.project_id, expected_revision=args.expected_revision, reports=("A", "B"),
        requested_by="owner-1007-presentation", requested_at=datetime.now(UTC),
    )
    OUT.mkdir()
    with (sqlite3.connect((PROJECT / "state/project.sqlite").as_uri()+"?mode=ro", uri=True) as db,
          sqlite3.connect(OUT / "database-before.sqlite") as backup):
        db.backup(backup)
    write("command.json", command.model_dump(mode="json"))
    write("prewrite.json", {
        "state": "NORMAL_PRESENTATION_READY_NOT_REBUILT", "current": before.model_dump(mode="json"),
        "asset_hashes": asset_hashes, "backup_sha256": sha(OUT / "database-before.sqlite"),
        "protected_files": protected, "command_sha256": sha(OUT / "command.json"),
    })
    try:
        result = service.rebuild_current_presentation(command)
        write("rebuild-return.json", result.model_dump(mode="json"))
        after = read_current_delivery(PROJECT)
        assert after == result and result.revision == target_revision
        assert after.active_fact_version_ids == before.active_fact_version_ids
        assert service.current_facts() == public_before
        assert tables() == frozen
        assert next(r for r in after.reports if r.report == "C") == next(
            r for r in before.reports if r.report == "C"
        )
        assert all(sha(PROJECT / path) == digest for path, digest in protected.items())
        a = next(r for r in after.reports if r.report == "A")
        public = json.loads((PROJECT/a.site_relative_path/"data/render-context.json").read_bytes())[
            "public_provenance"
        ]
        assert public is not None and len(public["sources"]) == 20
        write("verified.json", {
            "state": (
                f"CURRENT{target_revision}_PRESENTATION_COMMITTED_NOT_BROWSER_OR_RELEASE_ACCEPTED"
            ),
            "revision": target_revision, "reports": {r.report: r.revision for r in after.reports},
            "generation": current_bundle_sha256(after), "facts_unchanged": len(public_before),
            "frozen_tables_unchanged": list(FROZEN_TABLES), "old_files_unchanged": len(protected),
            "public_sources": len(public["sources"]), "asset_hashes": asset_hashes,
            "limits": (
                "No new source, clinical equivalence, universe, visual, edit, config, "
                "share, host or RC acceptance"
            ),
        })
    except Exception as error:
        write("failure.json", {"state":"FAILED_REOPEN_RETURN_AND_CURRENT", "error":str(error)})
        raise
    print(json.dumps({"revision": after.revision, "generation":current_bundle_sha256(after)}))


if __name__ == "__main__":
    main()
