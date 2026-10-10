"""One normal frozen-source replay proving domain moves, not source acceptance.

Old candidates, scientific snapshots, current report and user edits stay intact.
Compare source atoms by exact path, not changing report row identifiers.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
POOL = ROOT / ".artifacts/1007-scoped-source-pool-reconcile-v2"
OLD = ROOT / ".artifacts/1007-arm-relations-owner-v2"
OUT = ROOT / ".artifacts/1007-half-life-candidate-owner-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins() -> dict[str, str]:
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in PROJECT.rglob("*")
            if p.is_file() and p.name != "user-fact-edit.lock"
            and p.name not in {"project.sqlite-wal", "project.sqlite-shm"}}


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Existing frozen replay: collect originals, never overwrite"
    assert sha(POOL / "candidate.json") == (
        "9aae15b65841b35910c51469ac0db875729d17fa47454e71e6cc281aa8f22587")
    assert sha(OLD / "a-candidate.json") == (
        "767733753e3536c45b2c5016918fd1d7d870a35ad34d5ce46dd99aace8716dd8")
    assert sha(OLD / "a-candidate.derivation.json") == (
        "4898289654273b9a6b91ab3d23322737d20a24614fbeeb1998cf92f7ec68f22b")
    pool = json.loads((POOL / "candidate.json").read_bytes())
    old = json.loads((OLD / "a-candidate.json").read_bytes())
    old_sidecar = json.loads((OLD / "a-candidate.derivation.json").read_bytes())
    before = pins()
    OUT.mkdir()
    command = list(pool["command"])
    command[0] = sys.executable
    command[command.index("--output") + 1] = str(OUT / "a-candidate.json")
    write("prewrite.json", {"durable_project_pins": before, "command": command,
                            "source_classifier_sha256": sha(ROOT /
                                "src/ci_workflow/application/source_research_service.py")})
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    write("builder-return.json", {"exit_code": run.returncode, "stdout": run.stdout,
                                  "stderr": run.stderr})
    try:
        assert run.returncode == 0, run.stderr
        new = json.loads((OUT / "a-candidate.json").read_bytes())
        new_sidecar = json.loads((OUT / "a-candidate.derivation.json").read_bytes())
        assert {t["id"] for t in old["trials"]} == {t["id"] for t in new["trials"]}
        assert old["trials"] == new["trials"]
        migrations = []
        for group in ("efficacy", "safety", "additional_observations"):
            previous = {r["row_id"]: r for r in old[group]}
            current = {r["row_id"]: r for r in new[group]}
            for identity in previous.keys() & current.keys():
                assert previous[identity] == current[identity], (group, identity)
            if group == "efficacy":
                assert not current.keys() - previous.keys()
                migrated = [previous[k] for k in previous.keys() - current.keys()]
                assert len(migrated) == 2
                assert {r["endpoint"] for r in migrated} == {"Half-life (t1/2) of Nemolizumab"}
                assert {r["trial_id"] for r in migrated} == {"nct05405985"}
                migrations = migrated
            elif group == "safety":
                assert previous == current
            else:
                assert not previous.keys() - current.keys()
                added = [current[k] for k in current.keys() - previous.keys()]
                assert len(added) == 2 and {r["domain"] for r in added} == {"pk_pd"}
                assert {(float(r["raw_value"]), r["raw_unit"], r["group_id"], r["time_window"])
                        for r in added} == {
                            (r["value"], r["unit"], r["group_id"], r["timepoint"])
                            for r in migrations}
        def atoms(sidecar: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
            values = {(r["trial_id"], r["value_path"]): r for r in sidecar["row_source_map"]}
            assert len(values) == len(sidecar["row_source_map"])
            return values

        previous_atoms, current_atoms = atoms(old_sidecar), atoms(new_sidecar)
        assert previous_atoms.keys() == current_atoms.keys()
        changed = []
        for key, previous in previous_atoms.items():
            current = current_atoms[key]
            delta = {k: {"old": previous.get(k), "new": current.get(k)}
                     for k in previous.keys() | current.keys() if previous.get(k) != current.get(k)}
            if delta:
                assert set(delta) == {"domain", "row_id"}, (key, delta)
                changed.append({"source_atom": key, "diff": delta})
        assert len(changed) == 2
        assert pins() == before, "Source/current/user/history durable bytes differ"
        write("actual.json", {
            "state": "NORMAL_FROZEN_PK_DOMAIN_MOVE_PASSED_NOT_ADOPTED_OR_CURRENT",
            "source_commit": "e616f415eb61ba91a8d32cdcebb2460da31bff53",
            "classifier_sha256": sha(ROOT /
                "src/ci_workflow/application/source_research_service.py"),
            "script_sha256": sha(Path(__file__)),
            "source_pool_sha256": sha(POOL / "candidate.json"),
            "payload_sha256": sha(OUT / "a-candidate.json"),
            "derivation_sha256": sha(OUT / "a-candidate.derivation.json"),
            "all_exact_source_atoms": len(previous_atoms), "changed_source_atoms": changed,
            "efficacy": len(new["efficacy"]), "safety": len(new["safety"]),
            "additional": len(new["additional_observations"]), "trials": len(new["trials"]),
            "durable_project_files_unchanged": len(before),
            "source_writes": 0, "adoptions": 0, "registrations": 0, "renders": 0, "saves": 0,
            "limits": "Original source/history/current untouched; new scientific source versions "
                      "and independent review still required; not clinical coaxis/universe/RC",
        })
    except Exception as error:
        write("failure.json", {"state": "FAILED_COLLECT_ORIGINAL_BEFORE_RETRY",
                               "type": type(error).__name__, "reason": str(error)})
        raise
    print(json.dumps({"state": "PK_DOMAIN_MOVE_ONLY_NOT_CURRENT", "moved": 2,
                      "all_source_atoms": len(previous_atoms)}))


if __name__ == "__main__":
    main()
