"""Resume after old revision assertion: reuse terminal B ZIP, export only missing ABC."""
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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, payload: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    before = json.loads((OUT / "prewrite.json").read_bytes())
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == before["revision"] == 31
    generation = current_bundle_sha256(current)
    assert generation == before["generation"]
    assert current.model_dump(mode="json") == before["current"]
    assert not (OUT / "verified.json").exists()
    revisions = {r.report: r.revision for r in current.reports}
    b_return = json.loads((OUT / "B-export-return.json").read_bytes())
    assert sha(OUT / b_return["archive"]) == b_return["sha256"]
    assert not (OUT / "current31-ABC.zip").exists()
    selections = {}
    for kind in "ABC":
        folder = ROOT / (
            ".artifacts/1007-b-current31-native-qa-v1" if kind == "B"
            else ".artifacts/1007-current30-config-v1"
        )
        config = json.loads((folder / f"personal-view-{kind}.json").read_bytes())
        selection = config["selections"][0]
        assert selection["report"] == kind and selection["revision"] == revisions[kind]
        selections[kind] = selection
    write("recovery-prewrite.json", {
        "recipe_sha256": sha(Path(__file__)), "current_generation": generation,
        "preserved_failure": "v1 terminal B export succeeded; old manifest revision assertion",
        "reused_B_archive_sha256": b_return["sha256"], "B_export_replayed": False,
    })
    write("ABC-view-config.json", {
        "schema_version": "1.0", "selections": [selections[k] for k in "ABC"],
    })
    destination = OUT / "current31-ABC.zip"
    assert cli_main([
        "project", "share", "--root", str(PROJECT), "--reports", "A,B,C",
        "--output", str(destination), "--view-config", str(OUT / "ABC-view-config.json"),
    ]) == 0
    write("ABC-export-return.json", {"archive": destination.name, "sha256": sha(destination)})
    records = []
    for kinds in (("B",), ("A", "B", "C")):
        tag = "".join(kinds)
        destination = OUT / f"current31-{tag}.zip"
        staging, moved = OUT / f"stage-{tag}", OUT / f"moved-{tag}"
        assert not staging.exists() and not moved.exists()
        with ZipFile(destination) as archive:
            manifest = json.loads(archive.read("share-manifest.json"))
            assert manifest["current_revision"] == 31
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
        record = {
            "reports": list(kinds), "archive": destination.name,
            "archive_sha256": sha(destination), "members": members,
            "moved_root": moved.name, "generation_sha256": generation,
            "manifest_sha256": sha(moved / "share-manifest.json"),
        }
        records.append(record)
        write(f"{tag}-verified.json", record)
    assert read_current_delivery(PROJECT) == current
    write("verified.json", {
        "state": "CHANGED_B_AND_JOINT_CURRENT_SHARES_MOVED_HASH_VERIFIED_NOT_BROWSER_ACCEPTED",
        "current_revision": 31, "report_revisions": revisions, "exports": records,
        "current_unchanged": True, "saved_config": "ACTUAL_DOWNLOADED_CONFIGS_BOUND",
        "fresh_browser": "NOT_RUN", "offline_browser": "NOT_RUN", "B_export_replayed": False,
        "limits": "Changed B and joint exports only; unchanged A/C standalone at current30. "
                  "Not Skill installation/scientific/RC acceptance.",
    })
    print("RECOVERED_B_AND_ABC_SHARES_VERIFIED_NOT_BROWSER_ACCEPTED", flush=True)


if __name__ == "__main__":
    main()
