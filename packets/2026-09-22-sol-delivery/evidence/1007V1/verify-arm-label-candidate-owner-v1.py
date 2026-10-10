"""Replay frozen original pages once into a NEW arm-link candidate, never current.

This is a production builder/differential proof, not clinical adoption or freshness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
POOL = ROOT / ".artifacts/1007-scoped-source-pool-reconcile-v2"
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
GENERATION = "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*")
            if p.is_file() and p.name != "user-fact-edit.lock"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    out = ROOT / f".artifacts/1007-arm-relations-owner-{args.attempt}"
    assert not out.exists(), "Existing attempt: do not replay or overwrite"
    assert sha(POOL / "candidate.json") == (
        "9aae15b65841b35910c51469ac0db875729d17fa47454e71e6cc281aa8f22587"
    )
    original = json.loads((POOL / "a-scoped.json").read_bytes())
    candidate = json.loads((POOL / "candidate.json").read_bytes())
    raw = ROOT / candidate["source_captures"]["ctgov-nct03816891"][
        "text_derivation"]["raw_asset"]["relative_path"]
    # Its content-addressed bytes belong to the original source root, not this repo root.
    raw = ROOT / ".artifacts/1007-pn-current-source-v1" / raw.relative_to(ROOT)
    assert sha(raw) == "82b4ed9ab0c63e227a2c4c34b85727dd988e55062850d42b41517f0749168edf"
    generation_path = PROJECT / "reports/generations" / f"{GENERATION}.json"
    assert sha(generation_path) == GENERATION
    before = pins(PROJECT)
    command = list(candidate["command"])
    command[0] = sys.executable
    command[command.index("--output") + 1] = str(out / "a-candidate.json")
    out.mkdir()
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result: dict[str, Any] = {
        "state": "BUILDER_OR_DIFFERENTIAL_NOT_ACCEPTED", "command": command,
        "exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
        "code_sha256": sha(ROOT / "tools/build_a_payload.py"),
        "input_sha256": sha(POOL / "candidate.json"), "raw_sha256": sha(raw),
        "current_generation": GENERATION, "source_writes": 0, "adoptions": 0,
        "registrations": 0, "renders": 0, "saves": 0,
        "science": "NOT_ACCEPTED", "freshness": "NOT_RUN", "browser": "NOT_RUN",
    }
    try:
        assert run.returncode == 0, run.stderr
        new = json.loads((out / "a-candidate.json").read_bytes())
        sidecar = json.loads((out / "a-candidate.derivation.json").read_bytes())
        row_changes, other_changes = [], []
        for collection in ("efficacy", "safety"):
            old_rows = {r["row_id"]: r for r in original[collection]}
            new_rows = {r["row_id"]: r for r in new[collection]}
            assert set(old_rows) == set(new_rows), "Observation coverage changed"
            for row_id, old in old_rows.items():
                fresh = new_rows[row_id]
                diff = {k: {"old": old.get(k), "new": fresh.get(k)}
                        for k in set(old) | set(fresh) if old.get(k) != fresh.get(k)}
                if diff:
                    record = {"collection": collection, "row_id": row_id,
                              "trial_id": old["trial_id"], "arm": old["arm"], "diff": diff}
                    if set(diff) <= {"product_id", "group_assignment_state"}:
                        row_changes.append(record)
                    else:
                        other_changes.append(record)
        assert {t["id"] for t in new["trials"]} == {t["id"] for t in original["trials"]}
        old_support = {r["row_id"]: r for r in original["additional_observations"]}
        new_support = {r["row_id"]: r for r in new["additional_observations"]}
        assert set(old_support) == set(new_support), "Supporting observation coverage changed"
        supporting_changes = []
        for row_id, old in old_support.items():
            fresh = new_support[row_id]
            diff = {k: {"old": old.get(k), "new": fresh.get(k)}
                    for k in set(old) | set(fresh) if old.get(k) != fresh.get(k)}
            if diff:
                supporting_changes.append({"row_id": row_id, "domain": old.get("domain"),
                                           "trial_id": old["trial_id"], "diff": diff})
                assert set(diff) <= {"product_id", "group_assignment_state"}, (
                    "Supporting scientific value/context/domain changed"
                )
        result.update({
            "trials": len(new["trials"]),
            "rows": sum(len(new[k]) for k in ("efficacy", "safety")),
            "arm_changes": row_changes, "other_observation_changes": other_changes,
            "supporting_observations": len(new_support),
            "supporting_arm_changes": supporting_changes,
            "by_trial": dict(Counter(r["trial_id"] for r in row_changes)),
            "arm_label_derivations": sidecar["arm_label_derivations"],
            "payload_sha256": sha(out / "a-candidate.json"),
            "derivation_sha256": sha(out / "a-candidate.derivation.json"),
        })
        assert not other_changes, "Unexpected scientific observation changes retained"
        assert all(r["diff"].get("group_assignment_state") == {
            "old": "unknown", "new": "declared",
        } for r in row_changes)
        result["state"] = "NORMAL_FROZEN_SOURCE_REPLAY_ARM_ONLY_DIFF_PASSED_NOT_ADOPTED"
    finally:
        result["project_files_unchanged"] = pins(PROJECT) == before
        result["project_files"] = len(before)
        assert result["project_files_unchanged"], "Actual current project changed"
        with (out / "actual.json").open("x") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=1)
    print(json.dumps({k: result[k] for k in ("state", "exit_code", "project_files_unchanged")}))


if __name__ == "__main__":
    main()
