"""Changed B and joint normal current CLI exports with actual downloaded view configs.

Not Skill distribution or browser acceptance. Existing outputs are never overwritten.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.cli import main as cli_main

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-current31-shares-v1"
CONFIGS = ROOT / ".artifacts/1007-current30-config-v1"
B_CONFIGS = ROOT / ".artifacts/1007-b-current31-native-qa-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, payload: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Inspect existing exports/returns; no overwrite or blind replay"
    proof = json.loads((ROOT / ".artifacts/1007-b-disclosure-current31-v1"
                        / "verified.json").read_bytes())
    config_proof = json.loads((B_CONFIGS / "actual.json").read_bytes())
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == proof["revision"] == 31
    generation = current_bundle_sha256(current)
    assert generation == proof["generation"] == config_proof["generation"]
    assert config_proof["state"] == (
        "ACTUAL_CURRENT31_B_READING_AND_NATIVE_CONFIG_PASSED_OWNER_PIXELS_PENDING"
    )
    revisions = {report.report: report.revision for report in current.reports}
    selections = {}
    for kind in "ABC":
        folder = B_CONFIGS if kind == "B" else CONFIGS
        config = json.loads((folder / f"personal-view-{kind}.json").read_bytes())
        assert config["schema_version"] == "1.0" and len(config["selections"]) == 1
        selection = config["selections"][0]
        assert selection["report"] == kind and selection["revision"] == revisions[kind]
        selections[kind] = selection
    OUT.mkdir()
    write("prewrite.json", {"revision": current.revision, "generation": generation,
                           "recipe_sha256": sha(Path(__file__)),
                           "config_proof_sha256": sha(B_CONFIGS / "actual.json"),
                           "current": current.model_dump(mode="json")})
    records = []
    for kinds in (("B",), ("A", "B", "C")):
        tag = "".join(kinds)
        view = OUT / f"{tag}-view-config.json"
        write(view.name, {"schema_version": "1.0", "selections": [selections[k] for k in kinds]})
        destination = OUT / f"current31-{tag}.zip"
        assert cli_main(["project", "share", "--root", str(PROJECT), "--reports", ",".join(kinds),
                         "--output", str(destination), "--view-config", str(view)]) == 0
        write(f"{tag}-export-return.json", {"archive": destination.name,
                                           "sha256": sha(destination)})
        staging, moved = OUT / f"stage-{tag}", OUT / f"moved-{tag}"
        with ZipFile(destination) as archive:
            manifest = json.loads(archive.read("share-manifest.json"))
            assert manifest["current_revision"] == 30
            assert manifest["current_generation_sha256"] == generation
            assert set(manifest["reports"]) == set(kinds)
            for info in archive.infolist():
                name = PurePosixPath(info.filename)
                assert not name.is_absolute() and ".." not in name.parts
                assert "\\" not in info.filename
                assert ((info.external_attr >> 16) & 0o170000) != 0o120000
                assert name.suffix.lower() not in {".pdf", ".sqlite", ".log", ".pptx"}
            members = len(archive.infolist())
            archive.extractall(staging)
        staging.rename(moved)
        for kind in kinds:
            report = manifest["reports"][kind]
            assert report["report_revision"] == revisions[kind]
            assert report["view_config"] == selections[kind]
            for relative, digest in report["file_sha256"].items():
                assert sha(moved / kind / relative) == digest
        record = {"reports": list(kinds), "archive": destination.name,
                  "archive_sha256": sha(destination), "members": members,
                  "moved_root": moved.name, "generation_sha256": generation,
                  "manifest_sha256": sha(moved / "share-manifest.json")}
        records.append(record)
        write(f"{tag}-verified.json", record)
        print(json.dumps({"reports": kinds, "members": members}), flush=True)
    assert read_current_delivery(PROJECT) == current
    write("verified.json", {
        "state": "CHANGED_B_AND_JOINT_CURRENT_SHARES_MOVED_HASH_VERIFIED_NOT_BROWSER_ACCEPTED",
        "current_revision": current.revision, "report_revisions": revisions, "exports": records,
        "current_unchanged": True, "saved_config": "ACTUAL_DOWNLOADED_CONFIGS_BOUND",
        "fresh_browser": "NOT_RUN", "offline_browser": "NOT_RUN",
        "limits": "No commercial PDF/DB/log/PPT files; production privacy/resource gates apply. "
                  "Not Skill installation/scientific/RC acceptance.",
    })


if __name__ == "__main__":
    main()
