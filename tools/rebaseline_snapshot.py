#!/usr/bin/env python3
"""Build and verify a full, content-addressed repository recovery snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast

SNAPSHOT_KIND = "ci-rebaseline-recovery-snapshot"
SCHEMA_VERSION = "1.0"
_CACHE_PARTS = frozenset(
    {
        ".cache",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "node_modules",
    }
)
_RAW_ROOTS = frozenset(
    {
        ".artifacts",
        ".playwright-cli",
        "archives",
        "conference",
        "logs",
        "output",
        "runs",
        "tmp",
    }
)
_NORMATIVE_ROOTS = frozenset(
    {
        ".trellis",
        "context",
        "docs",
        "metrics",
        "plans",
        "prompts",
        "reviews",
    }
)
_SOURCE_ROOTS = frozenset(
    {
        "assets",
        "contracts",
        "fixtures",
        "migrations",
        "policies",
        "schemas",
        "skills",
        "src",
        "tests",
        "tools",
    }
)
_SOURCE_FILES = frozenset(
    {"package-manifest.json", "pyproject.toml", "uv.lock"}
)


class SnapshotError(ValueError):
    """The requested snapshot or manifest is invalid."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(root: Path, *args: str) -> bytes:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *args],
            check=True,
            capture_output=True,
            timeout=120,
            env=environment,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SnapshotError(f"git command failed: {' '.join(args)}") from exc
    return completed.stdout


def _repository_root(path: Path) -> Path:
    candidate = path.expanduser().absolute()
    if candidate.is_symlink() or not candidate.is_dir():
        raise SnapshotError(f"snapshot root must be a real directory: {candidate}")
    reported = Path(os.fsdecode(_git(candidate, "rev-parse", "--show-toplevel")).strip())
    if reported.resolve() != candidate.resolve():
        raise SnapshotError("snapshot root must be the Git repository root")
    return candidate


def _paths(value: bytes) -> set[str]:
    return {os.fsdecode(item) for item in value.split(b"\0") if item}


def _git_sets(root: Path) -> tuple[set[str], set[str], set[str]]:
    tracked = _paths(_git(root, "ls-files", "-z"))
    modified = _paths(_git(root, "diff", "--name-only", "-z"))
    modified.update(_paths(_git(root, "diff", "--cached", "--name-only", "-z")))
    ignored = _paths(_git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"))
    return tracked, modified, ignored


def _walk_nodes(root: Path) -> Iterator[Path]:
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        symlink_dirs: list[str] = []
        for dirname in dirnames:
            if (current_path / dirname).is_symlink():
                symlink_dirs.append(dirname)
        dirnames[:] = sorted(name for name in dirnames if name not in symlink_dirs)
        for name in sorted([*symlink_dirs, *filenames]):
            yield current_path / name


def _content_class(relative: str) -> str:
    path = PurePosixPath(relative)
    if path.parts[0] == ".git":
        return "git_metadata"
    if any(part in _CACHE_PARTS for part in path.parts):
        return "cache"
    if path.parts[0] in _RAW_ROOTS:
        return "raw_run_artifact"
    if path.parts[0] in _NORMATIVE_ROOTS or relative == "AGENTS.md":
        return "normative_evidence"
    if path.parts[0] in _SOURCE_ROOTS or relative in _SOURCE_FILES:
        return "source"
    return "other"


def _hash_node(path: Path) -> tuple[str, int, str]:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        value = os.fsencode(os.readlink(path))
        return _sha256_bytes(value), len(value), "symlink"
    if not stat.S_ISREG(metadata.st_mode):
        raise SnapshotError(f"unsupported filesystem node: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size, "regular"


def build_snapshot_manifest(
    root: Path,
    *,
    snapshot_name: str,
    reference_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Hash every file and symlink, including Git metadata and ignored files."""

    if reference_manifest is None:
        repository = _repository_root(root)
        tracked, modified, ignored = _git_sets(repository)
        status = _git(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        git_record = {
            "branch": os.fsdecode(_git(repository, "branch", "--show-current")).strip(),
            "head": os.fsdecode(_git(repository, "rev-parse", "HEAD")).strip(),
            "status_sha256": _sha256_bytes(status),
        }
        reference_files: dict[str, dict[str, Any]] = {}
    else:
        repository = root.expanduser().absolute()
        if repository.is_symlink() or not repository.is_dir():
            raise SnapshotError(f"snapshot root must be a real directory: {repository}")
        tracked = modified = ignored = set()
        reference_files = {
            cast(str, record["path"]): record
            for record in cast(list[dict[str, Any]], reference_manifest.get("files"))
        }
        git_record = cast(dict[str, Any], reference_manifest.get("git"))
    files: list[dict[str, object]] = []
    for path in _walk_nodes(repository):
        relative = path.relative_to(repository).as_posix()
        digest, size, node_type = _hash_node(path)
        reference = reference_files.get(relative)
        if reference is not None:
            git_state = cast(str, reference["git_state"])
            content_class = cast(str, reference["content_class"])
        elif relative.startswith(".git/"):
            git_state = "git_metadata"
            content_class = "git_metadata"
        elif relative in tracked:
            git_state = "tracked_modified" if relative in modified else "tracked_unchanged"
            content_class = _content_class(relative)
        elif relative in ignored:
            git_state = "ignored"
            content_class = _content_class(relative)
        else:
            git_state = "untracked"
            content_class = _content_class(relative)
        files.append(
            {
                "bytes": size,
                "content_class": content_class,
                "git_state": git_state,
                "mode": f"{stat.S_IMODE(path.lstat().st_mode):04o}",
                "node_type": node_type,
                "path": relative,
                "sha256": digest,
            }
        )
    files.sort(key=lambda record: cast(str, record["path"]))
    content_counts = Counter(cast(str, record["content_class"]) for record in files)
    state_counts = Counter(cast(str, record["git_state"]) for record in files)
    node_counts = Counter(cast(str, record["node_type"]) for record in files)
    body: dict[str, Any] = {
        "captured_at": datetime.now(UTC).isoformat(),
        "counts": {
            "bytes": sum(cast(int, record["bytes"]) for record in files),
            "content_class": dict(sorted(content_counts.items())),
            "files": len(files),
            "git_state": dict(sorted(state_counts.items())),
            "node_type": dict(sorted(node_counts.items())),
        },
        "files": files,
        "git": git_record,
        "manifest_kind": SNAPSHOT_KIND,
        "repository_root": ".",
        "schema_version": SCHEMA_VERSION,
        "snapshot_name": snapshot_name,
    }
    body["manifest_sha256"] = _sha256_bytes(_canonical_json(body))
    return body


def assert_same_snapshot(source: Mapping[str, Any], backup: Mapping[str, Any]) -> None:
    """Fail unless source and backup contain identical nodes, bytes, mode, and Git state."""

    source_files = {
        record["path"]: record for record in cast(list[dict[str, Any]], source.get("files"))
    }
    backup_files = {
        record["path"]: record for record in cast(list[dict[str, Any]], backup.get("files"))
    }
    if source_files.keys() != backup_files.keys():
        missing = sorted(source_files.keys() - backup_files.keys())[:3]
        extra = sorted(backup_files.keys() - source_files.keys())[:3]
        raise SnapshotError(f"source/backup path mismatch: missing={missing} extra={extra}")
    for path in source_files:
        if source_files[path] != backup_files[path]:
            raise SnapshotError(
                f"source/backup node mismatch: {path} "
                f"source={source_files[path]} backup={backup_files[path]}"
            )
    for key in ("counts", "git"):
        if source.get(key) != backup.get(key):
            raise SnapshotError(f"source/backup snapshot mismatch: {key}")


def write_snapshot_manifest(manifest: Mapping[str, Any], path: Path) -> None:
    """Atomically write a validated manifest outside the snapshotted tree."""

    destination = path.expanduser().absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    finally:
        if temporary_name and Path(temporary_name).exists():
            Path(temporary_name).unlink()


def validate_snapshot_manifest(path: Path) -> dict[str, Any]:
    """Validate the manifest envelope and its canonical digest."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"invalid snapshot manifest: {path}") from exc
    if not isinstance(value, dict):
        raise SnapshotError("snapshot manifest root must be an object")
    manifest = cast(dict[str, Any], value)
    if manifest.get("manifest_kind") != SNAPSHOT_KIND:
        raise SnapshotError("snapshot manifest kind mismatch")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotError("snapshot schema version mismatch")
    supplied = manifest.get("manifest_sha256")
    if not isinstance(supplied, str):
        raise SnapshotError("snapshot manifest SHA-256 is missing")
    body = {key: item for key, item in manifest.items() if key != "manifest_sha256"}
    if supplied != _sha256_bytes(_canonical_json(body)):
        raise SnapshotError("snapshot manifest SHA-256 mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise SnapshotError("snapshot manifest has no files")
    if not all(isinstance(record, dict) for record in files):
        raise SnapshotError("snapshot file records must be objects")
    records = cast(list[dict[str, Any]], files)
    paths = [record.get("path") for record in records]
    if not all(isinstance(path, str) for path in paths):
        raise SnapshotError("snapshot file paths must be strings")
    typed_paths = cast(list[str], paths)
    if typed_paths != sorted(set(typed_paths)):
        raise SnapshotError("snapshot file paths must be unique and sorted")
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="backup Git repository root")
    parser.add_argument("--manifest", required=True, type=Path, help="external manifest path")
    parser.add_argument("--snapshot-name", required=True)
    parser.add_argument(
        "--reference-manifest",
        type=Path,
        help="source manifest captured before copying; compare all copied nodes against it",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest_path = args.manifest.expanduser().absolute()
        root = args.root.expanduser().absolute()
        if manifest_path == root or root in manifest_path.parents:
            raise SnapshotError("manifest must be outside the snapshotted tree")
        reference = (
            validate_snapshot_manifest(args.reference_manifest)
            if args.reference_manifest is not None
            else None
        )
        manifest = build_snapshot_manifest(
            root,
            snapshot_name=args.snapshot_name,
            reference_manifest=reference,
        )
        if reference is not None:
            assert_same_snapshot(reference, manifest)
        write_snapshot_manifest(manifest, manifest_path)
        validate_snapshot_manifest(manifest_path)
    except SnapshotError as exc:
        print(f"REBASELINE_SNAPSHOT_FAIL {exc}", file=sys.stderr)
        return 1
    counts = cast(dict[str, Any], manifest["counts"])
    print(
        "REBASELINE_SNAPSHOT_OK "
        f"files={counts['files']} bytes={counts['bytes']} "
        f"manifest_sha256={manifest['manifest_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
