"""Normal default CLI shares for one committed current; no configuration claim.

Each archive is independently moved and every report member verified. Original
attempts are exclusive. Browser/offline/fresh-profile acceptance remains separate.
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
OUT = ROOT / ".artifacts/1007-scoped-current12-shares-v2"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise SystemExit(
            "Existing share attempt: reopen completed archives/returns, do not overwrite"
        )
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 12
    generation = current_bundle_sha256(current)
    expected_revisions: dict[str, int] = {r.report: r.revision for r in current.reports}
    assert expected_revisions == {"A": 12, "B": 12, "C": 9}
    OUT.mkdir()
    records = []
    for kinds in (("A",), ("B",), ("C",), ("A", "B", "C")):
        tag = "".join(kinds)
        destination = OUT / f"current12-{tag}.zip"
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
            assert manifest["current_revision"] == 12
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
                "current_revision": 12,
                "report_revisions": expected_revisions,
                "exports": records,
                "current_unchanged": True,
                "saved_config": "NOT_RUN",
                "fresh_browser": "NOT_RUN",
                "offline_browser": "NOT_RUN",
                "limits": "Share is not Skill installation or scientific/RC acceptance",
            },
            stream,
            indent=1,
        )


if __name__ == "__main__":
    main()
