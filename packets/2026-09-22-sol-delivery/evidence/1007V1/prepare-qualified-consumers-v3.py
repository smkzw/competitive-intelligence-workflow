"""Exact newly declared arm consumers; no adoption, registration or report switch."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.portal_consumer_registry import _safety_source_context_matches
from ci_workflow.renderers.portal.report_a import ReportAPortalData, SafetyRow
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
NEW = ROOT / ".artifacts/1007-source-definition-candidate-v4"
ARM = ROOT / ".artifacts/1007-arm-relations-owner-v2"
OLD = ROOT / ".artifacts/1007-scoped-consumer-preparation-v2"
OUT = ROOT / ".artifacts/1007-qualified-consumer-preparation-v3"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Existing preparation: reopen original, never overwrite"
    proof = json.loads((NEW / "actual.json").read_bytes())
    assert sha(NEW / "a-candidate.json") == proof["payload_sha256"]
    assert sha(ROOT / "tools/build_a_payload.py") == proof["builder_sha256"]
    assert sha(ARM / "actual.json") == (
        "44ae4b8aac24228ac34586a34daa59372cd2e05f3c828de79dfa4820c87c9927")
    old_proof = json.loads((OLD / "proof.json").read_bytes())
    assert sha(OLD / "a-preliminary.json") == old_proof["a_sha256"]
    before = {name: sha(PROJECT / name)
              for name in ("state/project.sqlite", "reports/current.json")}
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 21
    assert current_bundle_sha256(current) == (
        "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310")
    a_delivery = next(report for report in current.reports if report.report == "A")
    assert a_delivery.builder_input_relative_path is not None
    a_path = PROJECT / a_delivery.builder_input_relative_path
    assert sha(a_path) == a_delivery.builder_input_sha256
    payload = json.loads(a_path.read_bytes())
    raw = json.loads((NEW / "a-candidate.json").read_bytes())
    original = json.loads((OLD / "a-preliminary.json").read_bytes())
    changes = json.loads((ARM / "actual.json").read_bytes())["arm_changes"]
    changed = {f"{row['collection']}:{row['row_id']}" for row in changes}
    assert len(changed) == 349
    present = {f"{collection}:{row['row_id']}" for collection in ("efficacy", "safety")
               for row in raw[collection]}
    selected = changed & present
    excluded = changed - present
    assert len(selected) == 347 and len(excluded) == 2
    old_rows = {f"{collection}:{row['row_id']}": row
                for collection in ("efficacy", "safety") for row in original[collection]}
    payload["trials"] = raw["trials"]
    payload["additional_observations"] = raw["additional_observations"]
    for collection in ("efficacy", "safety"):
        payload[collection] = [row for row in payload[collection]
                               if f"{collection}:{row['row_id']}" not in excluded]
        for row in payload[collection]:
            ref = f"{collection}:{row['row_id']}"
            if ref in selected:
                source_row = dict(old_rows[ref])
                assert source_row["group_assignment_state"] == "unknown"
                source_row["group_assignment_state"] = "declared"
                row.clear()
                row.update(source_row)
    returned = json.loads((ROOT / ".artifacts/1007-scoped-source-union-ingestion-v2"
                           / "ingestion-return.json").read_bytes())
    locked = LockedSnapshot.model_validate(returned["evidence_snapshot"])
    assert locked.sha256 == "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237"
    snapshot = SnapshotStore(PROJECT).read(locked)
    primaries = {item["consumer_binding"]["row_ref"]: item
                 for item in snapshot["closure"]["facts"]
                 if item["fact"].get("result_context", {}).get("value_role") != "denominator"}
    assert selected <= primaries.keys()
    versions = {ref: primaries[ref]["fact_version_id"] for ref in sorted(selected)}
    assert len(set(versions.values())) == 347
    payload["source_evidence_snapshot_id"] = locked.snapshot_id
    payload["report_version"] = "v1-1007-qualified-consumer-v3-prepared"
    report = ReportAPortalData.model_validate(payload)
    contexts = {}
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        for version in versions.values():
            assert db.execute("SELECT review_state FROM fact_versions WHERE fact_version_id=?",
                              (version,)).fetchone() == ("accepted",)
            assert version not in current.active_fact_version_ids
            assert db.execute("SELECT count(*) FROM source_portal_consumer_bindings WHERE "
                              "source_fact_version_id=? AND report IN ('A','B') AND "
                              "evidence_snapshot_id=?", (version, locked.snapshot_id)
                              ).fetchone() == (0,)
        for row in report.efficacy:
            ref = f"efficacy:{row.row_id}"
            if ref in versions:
                fact = primaries[ref]["fact"]
                context = fact["result_context"]
                contexts[ref] = {"endpoint": context["endpoint"], "timepoint": row.timepoint,
                                 "group_title": context["group_title"],
                                 "value_path": fact["locator"]["field_path"]}
        for row in report.safety:
            ref = f"safety:{row.row_id}"
            if ref in versions:
                assert isinstance(row, SafetyRow)
                fact = primaries[ref]["fact"]
                assert _safety_source_context_matches(
                    fact["result_context"], row, float(fact["raw_value"]))
    assert all(sha(PROJECT / name) == digest for name, digest in before.items())
    OUT.mkdir()
    write("a-input.json", report.model_dump(mode="json"))
    write("new-row-versions.json", {"row_versions": versions, "source_row_contexts": contexts,
                                   "evidence_snapshot": locked.model_dump(mode="json")})
    write("actual.json", {
        "state": "PREPARED_ONLY_NOT_REGISTERED_OR_CURRENT", "new_direct_candidates": 347,
        "by_collection": dict(Counter(ref.split(":")[0] for ref in versions)),
        "excluded_reclassified_pk_rows": sorted(excluded), "additional_observations": 50,
        "all_observations_retained": True, "current_revision": 21,
        "old_current_and_db_hashes": before, "recipe_sha256": sha(Path(__file__)),
        "source_evidence_snapshot": locked.model_dump(mode="json"),
        "a_input_sha256": sha(OUT / "a-input.json"),
        "mapping_sha256": sha(OUT / "new-row-versions.json"),
        "limits": "No source adoption/replay/consumer registration/current/co-axis/visual/RC claim",
    })
    print(json.dumps({"state": "PREPARED_ONLY", "A_B_potential": 347, "excluded_pk": 2}))


if __name__ == "__main__":
    main()
