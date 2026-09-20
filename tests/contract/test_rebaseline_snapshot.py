from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from tools.rebaseline_snapshot import (
    assert_same_snapshot,
    build_snapshot_manifest,
    validate_snapshot_manifest,
    write_snapshot_manifest,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_snapshot_manifest_hashes_and_classifies_full_git_tree(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "--quiet")
    _git(source, "config", "user.email", "tests@example.invalid")
    _git(source, "config", "user.name", "Snapshot Tests")
    (source / ".gitignore").write_text(".cache/\n", encoding="utf-8")
    (source / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    _git(source, "add", ".gitignore", "tracked.txt")
    _git(source, "commit", "--quiet", "-m", "baseline")

    (source / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (source / "src").mkdir()
    (source / "src" / "new.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "docs" / "specs").mkdir(parents=True)
    (source / "docs" / "specs" / "rule.md").write_text("rule\n", encoding="utf-8")
    (source / "runs").mkdir()
    (source / "runs" / "raw.json").write_text("{}\n", encoding="utf-8")
    (source / ".cache").mkdir()
    (source / ".cache" / "ignored.bin").write_bytes(b"cache")
    (source / "source-link").symlink_to("src/new.py")

    manifest = build_snapshot_manifest(source, snapshot_name="test-source")
    records = {record["path"]: record for record in manifest["files"]}

    assert records["tracked.txt"]["git_state"] == "tracked_modified"
    assert records["src/new.py"]["git_state"] == "untracked"
    assert records["src/new.py"]["content_class"] == "source"
    assert records["docs/specs/rule.md"]["content_class"] == "normative_evidence"
    assert records["runs/raw.json"]["content_class"] == "raw_run_artifact"
    assert records[".cache/ignored.bin"]["content_class"] == "cache"
    assert records["source-link"]["node_type"] == "symlink"
    assert records["source-link"]["sha256"]
    assert any(path.startswith(".git/") for path in records)

    destination = tmp_path / "backup"
    shutil.copytree(source, destination, symlinks=True)
    copied = build_snapshot_manifest(
        destination,
        snapshot_name="test-backup",
        reference_manifest=manifest,
    )
    assert_same_snapshot(manifest, copied)

    manifest_path = tmp_path / "snapshot-manifest.json"
    write_snapshot_manifest(copied, manifest_path)
    validated = validate_snapshot_manifest(manifest_path)
    assert validated["manifest_sha256"] == copied["manifest_sha256"]
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["files"] == copied["files"]
