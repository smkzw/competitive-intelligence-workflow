"""Normal default CLI shares for one committed current; no configuration claim.

Each archive is independently moved and every report member verified. Original
attempts are exclusive. Browser/offline/fresh-profile acceptance remains separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.cli import main as cli_main

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-scoped-current12-shares-v2"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", type=int, default=12)
    parser.add_argument("--config-dir", type=Path)
    args = parser.parse_args()
    revision = args.expected_revision
    if revision < 12:
        raise SystemExit("Explicit new current revision required")
    OUT = ROOT / f".artifacts/1007-scoped-current{revision}-shares-v2"
    if OUT.exists():
        raise SystemExit(
            "Existing share attempt: reopen completed archives/returns, do not overwrite"
        )
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == revision
    generation = current_bundle_sha256(current)
    expected_revisions: dict[str, int] = {r.report: r.revision for r in current.reports}
    assert expected_revisions == {"A": revision, "B": revision, "C": 9}
    selections = {}
    if args.config_dir:
        config_root = args.config_dir.resolve(strict=True)
        assert config_root.is_relative_to(ROOT / ".artifacts")
        for kind in "ABC":
            config = json.loads((config_root / f"personal-view-{kind}.json").read_bytes())
            assert config["schema_version"] == "1.0" and len(config["selections"]) == 1
            selection = config["selections"][0]
            assert selection["report"] == kind
            assert selection["revision"] == expected_revisions[kind]
            selections[kind] = selection
    OUT.mkdir()
    records = []
    for kinds in (("A",), ("B",), ("C",), ("A", "B", "C")):
        tag = "".join(kinds)
        destination = OUT / f"current{revision}-{tag}.zip"
        view_args = []
        if selections:
            config_path = OUT / f"{tag}-view-config.json"
            with config_path.open("x") as stream:
                json.dump({"schema_version": "1.0", "selections": [selections[k] for k in kinds]},
                          stream, ensure_ascii=False)
            view_args = ["--view-config", str(config_path)]
        assert (
            cli_main(
                [
                    "project",
                    "share",
                    "--root",
                    str(PROJECT),
                    "--reports",
                    ",".join(kinds),
                    "--output",
                    str(destination),
                    *view_args,
                ]
            )
            == 0
        )
        # Persist the successful API/CLI export before archive postconditions.
        with (OUT / f"{tag}-export-return.json").open("x") as stream:
            json.dump({"archive": destination.name, "sha256": sha(destination)}, stream)
        staging = OUT / f"stage-{tag}"
        moved = OUT / f"moved-{tag}"
        with ZipFile(destination) as archive:
            manifest = json.loads(archive.read("share-manifest.json"))
            assert manifest["current_revision"] == revision
            assert manifest["current_generation_sha256"] == generation
            assert set(manifest["reports"]) == set(kinds)
            for info in archive.infolist():
                name = PurePosixPath(info.filename)
                assert (
                    not name.is_absolute() and ".." not in name.parts and "\\" not in info.filename
                )
                assert ((info.external_attr >> 16) & 0o170000) != 0o120000
            archive.extractall(staging)
            members = len(archive.infolist())
        staging.rename(moved)
        for kind in kinds:
            report = manifest["reports"][kind]
            assert report["report_revision"] == expected_revisions[kind]
            for name, digest in report["file_sha256"].items():
                assert sha(moved / kind / name) == digest
        records.append(
            {
                "reports": list(kinds),
                "archive": destination.name,
                "archive_sha256": sha(destination),
                "members": members,
                "moved_root": moved.name,
                "generation_sha256": generation,
                "manifest_sha256": sha(moved / "share-manifest.json"),
            }
        )
        with (OUT / f"{tag}-verified.json").open("x") as stream:
            json.dump(records[-1], stream, indent=1)
        print(json.dumps({"reports": kinds, "members": members}), flush=True)
    assert read_current_delivery(PROJECT) == current
    with (OUT / "verified.json").open("x") as stream:
        json.dump(
            {
                "state": "FOUR_NORMAL_CURRENT_SHARES_MOVED_HASH_VERIFIED_NOT_BROWSER_ACCEPTED",
                "current_revision": revision,
                "report_revisions": expected_revisions,
                "exports": records,
                "current_unchanged": True,
                "saved_config": "ACTUAL_DOWNLOADED_CONFIGS_BOUND" if selections else "NOT_RUN",
                "fresh_browser": "NOT_RUN",
                "offline_browser": "NOT_RUN",
                "limits": "Share is not Skill installation or scientific/RC acceptance",
            },
            stream,
            indent=1,
        )


if __name__ == "__main__":
    main()
