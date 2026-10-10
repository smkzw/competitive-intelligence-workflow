"""Validate only newly source-declared arm consumers in a minimal project copy.

The live project, its current reports and user edits are pinned and read-only.
Normal production A/B registration and source projection run on the copy; no
source ingestion, adoption, rendering or live current transaction occurs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.b_efficacy_source_views import project_b_efficacy_source_views
from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.portal_consumer_registry import (
    SourceRowContext,
    project_b_safety_source_views,
    register_a_source_consumers,
    register_b_shared_source_consumers,
)
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
ATTEMPT = ROOT / ".artifacts/1007-arm-relations-owner-v2"
PREP = ROOT / ".artifacts/1007-scoped-consumer-preparation-v2"
OUT = ROOT / ".artifacts/1007-arm-consumers-isolated-v1"
GENERATION = "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*")
            if p.is_file() and p.name != "user-fact-edit.lock"}


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Existing attempt: collect its original returns; do not replay"
    assert sha(ATTEMPT / "actual.json") == (
        "44ae4b8aac24228ac34586a34daa59372cd2e05f3c828de79dfa4820c87c9927")
    proof = json.loads((ATTEMPT / "actual.json").read_bytes())
    assert sha(ATTEMPT / "a-candidate.json") == proof["payload_sha256"]
    assert sha(ROOT / "tools/build_a_payload.py") == proof["code_sha256"]
    before = pins(PROJECT)
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 21
    assert current_bundle_sha256(current) == GENERATION
    original = json.loads((PREP / "a-preliminary.json").read_bytes())
    old_proof = json.loads((PREP / "proof.json").read_bytes())
    assert sha(PREP / "a-preliminary.json") == old_proof["a_sha256"]
    candidate = json.loads((ATTEMPT / "a-candidate.json").read_bytes())
    changed = {f"{r['collection']}:{r['row_id']}" for r in proof["arm_changes"]}
    assert len(changed) == 349
    # Keep the already source-bound values, N, original quotes and locators.
    # Only new declared titles and states are imported from the new builder.
    original["trials"] = candidate["trials"]
    for collection in ("efficacy", "safety"):
        for row in original[collection]:
            if f"{collection}:{row['row_id']}" in changed:
                assert row["group_assignment_state"] == "unknown"
                row["group_assignment_state"] = "declared"
    a = ReportAPortalData.model_validate(original)
    returned = json.loads((ROOT / ".artifacts/1007-scoped-source-union-ingestion-v2"
                           / "ingestion-return.json").read_bytes())
    locked = LockedSnapshot.model_validate(returned["evidence_snapshot"])
    assert locked.sha256 == (
        "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237")
    # Read the pinned bytes, not a verifier which might apply migrations live.
    snapshot_path = PROJECT / locked.relative_path
    assert sha(snapshot_path) == locked.sha256
    snapshot = json.loads(snapshot_path.read_bytes())
    primaries = {r["consumer_binding"]["row_ref"]: r for r in snapshot["closure"]["facts"]
                 if r["fact"].get("result_context", {}).get("value_role") != "denominator"}
    assert changed <= primaries.keys()
    versions = {ref: primaries[ref]["fact_version_id"] for ref in sorted(changed)}
    assert len(set(versions.values())) == len(versions)
    context: dict[str, SourceRowContext] = {}
    for row in a.efficacy:
        ref = f"efficacy:{row.row_id}"
        if ref in versions:
            fact = primaries[ref]["fact"]
            observation = fact["result_context"]
            context[ref] = SourceRowContext(
                endpoint=observation["endpoint"], timepoint=row.timepoint,
                group_title=observation["group_title"],
                value_path=fact["locator"]["field_path"],
            )
    OUT.mkdir()
    replica = OUT / "project"
    document = json.loads((PROJECT / "project.yaml").read_bytes())
    contract = next(v for v in document["project_contract_versions"]
                    if v["contract_version"] == document["active_contract_version"])
    create_project_workspace(replica, ProjectContract.model_validate(contract))
    with (sqlite3.connect((PROJECT / "state/project.sqlite").resolve().as_uri()
                         + "?mode=ro", uri=True) as source,
          sqlite3.connect(replica / "state/project.sqlite") as copied):
        for version in versions.values():
            accepted = source.execute("SELECT review_state FROM fact_versions "
                                      "WHERE fact_version_id=?", (version,)).fetchone()
            assert accepted == ("accepted",), (version, accepted)
            assert version not in current.active_fact_version_ids
        source.backup(copied)
    shutil.copyfile(snapshot_path, replica / locked.relative_path)
    assert sha(replica / locked.relative_path) == locked.sha256
    assert SnapshotStore(replica).read(locked) == snapshot
    write("prewrite.json", {"state": "ISOLATED_REGISTRATION_ONLY_NOT_LIVE",
                            "generation": GENERATION, "live_pins": before,
                            "source_snapshot": locked.model_dump(mode="json"),
                            "candidate_proof_sha256": sha(ATTEMPT / "actual.json")})
    try:
        now = datetime.now(UTC)
        ab = register_a_source_consumers(replica, locked, a, versions,
                                         registered_at=now, source_row_contexts=context)
        write("a-registration-return.json", [v.model_dump(mode="json") for v in ab])
        efficacy = project_b_efficacy_source_views(replica, locked, a, {
            ref: version for ref, version in versions.items() if ref.startswith("efficacy:")})
        safety = project_b_safety_source_views(replica, locked, a, {
            ref: version for ref, version in versions.items() if ref.startswith("safety:")})
        current_b = next(v for v in current.reports if v.report == "B")
        assert current_b.builder_input_relative_path is not None
        b_path = PROJECT / current_b.builder_input_relative_path
        assert sha(b_path) == current_b.builder_input_sha256
        b_dict: dict[str, Any] = json.loads(b_path.read_bytes())
        b_dict.update({k: original[k] for k in ("trials", "efficacy", "safety")})
        b_dict["source_evidence_snapshot_id"] = locked.snapshot_id
        b_dict["efficacy_views"] = {"coverage_mode": "partial", "facts": efficacy,
                                     "clinical_questions": ()}
        b_dict["safety_views"] = {"coverage_mode": "partial", "facts": safety}
        b = ReportBPortalData.model_validate(b_dict)
        bb = register_b_shared_source_consumers(replica, locked, b, versions, registered_at=now)
        write("b-registration-return.json", [v.model_dump(mode="json") for v in bb])
        write("new-row-versions.json", {"row_versions": versions,
                                        "source_row_contexts": {
                                            k: vars(v) for k, v in context.items()}})
        assert len(ab) == len(bb) == len(versions)
        assert pins(PROJECT) == before and read_current_delivery(PROJECT) == current
        write("verified.json", {
            "state": "ISOLATED_PRODUCTION_AB_REGISTRATION_PASSED_NOT_LIVE_OR_CURRENT",
            "generation": GENERATION, "source_snapshot": locked.model_dump(mode="json"),
            "source_commit": "3069e00187f7ac24a0b2bad68010a69f5e5d6e67",
            "script_sha256": sha(Path(__file__)), "new_direct_consumers_per_report": len(ab),
            "by_collection": dict(Counter(ref.split(":")[0] for ref in versions)),
            "accepted_source_atoms_reused": len(versions),
            "live_project_files_unchanged": len(before),
            "live_registrations": 0, "adoptions": 0, "renders": 0, "saves": 0,
            "current_mutations": 0, "clinical_comparability": "NOT_ACCEPTED",
            "limits": "Copy-only guard proof; no live current/visual/share/universe/freshness/RC",
        })
    except Exception as error:
        write("failure.json", {"state": "FAILED_COLLECT_ORIGINAL_NO_BLIND_REPLAY",
                               "type": type(error).__name__, "reason": str(error),
                               "live_project_unchanged": pins(PROJECT) == before})
        raise
    print(json.dumps({"state": "ISOLATED_ONLY", "new_AB": len(ab)}))


if __name__ == "__main__":
    main()
