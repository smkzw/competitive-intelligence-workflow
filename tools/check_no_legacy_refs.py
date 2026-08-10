#!/usr/bin/env python3
"""Reject runtime dependencies on the superseded competitive-research workspace."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LEGACY_ROOT = Path(
    "/Users/smkzw/Documents/AI Products/" + "竞品调研" + "工作流"
)
SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".trellis",
    ".venv",
    "__pycache__",
    "node_modules",
}
SKIPPED_FILES = {Path("migration/legacy_manifest.jsonl")}
HISTORICAL_ROOTS = {"docs", "fixtures"}
NON_RUNTIME_TOP_LEVELS = {
    "archives",
    "context",
    "logs",
    "metrics",
    "plans",
    "prompts",
    "reviews",
    "runs",
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class Finding:
    code: str
    path: Path
    detail: str


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _iter_paths(root: Path) -> Iterator[Path]:
    for directory, names, filenames in os.walk(root, followlinks=False):
        names[:] = sorted(name for name in names if name not in SKIPPED_DIRECTORY_NAMES)
        current = Path(directory)
        for name in names:
            path = current / name
            if path.is_symlink():
                yield path
        for name in sorted(filenames):
            yield current / name


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        content = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan(root: Path, legacy_root: Path) -> list[Finding]:
    root = root.resolve()
    legacy_text = str(legacy_root.resolve())
    legacy_name = legacy_root.name
    legacy_markers = (
        legacy_text,
        f"../{legacy_name}",
        f"..\\{legacy_name}",
        f"{legacy_name}/",
        f"{legacy_name}\\",
    )
    findings: list[Finding] = []

    for path in _iter_paths(root):
        relative = path.relative_to(root)
        if relative in SKIPPED_FILES:
            continue
        if relative.parts[0] in NON_RUNTIME_TOP_LEVELS:
            continue

        if path.is_symlink():
            target = path.resolve(strict=False)
            if not _is_within(target, root):
                findings.append(
                    Finding("EXTERNAL_RUNTIME_SYMLINK", relative, f"target={target}")
                )
            continue

        text = _read_text(path)
        if text is None:
            continue

        is_historical_surface = relative.parts[0] in HISTORICAL_ROOTS
        for line_number, line in enumerate(text.splitlines(), start=1):
            marker = next((item for item in legacy_markers if item in line), None)
            if marker is None:
                continue
            if is_historical_surface:
                if "historical:" not in line.casefold():
                    findings.append(
                        Finding(
                            "UNMARKED_HISTORICAL_REFERENCE",
                            relative,
                            f"line={line_number}",
                        )
                    )
                continue
            findings.append(
                Finding(
                    "LEGACY_RUNTIME_REFERENCE",
                    relative,
                    f"line={line_number} marker={marker!r}",
                )
            )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"SCAN_ROOT_MISSING path={root}")
        return 2

    legacy_root = Path(os.environ.get("CI_WORKFLOW_LEGACY_ROOT", DEFAULT_LEGACY_ROOT))
    findings = scan(root, legacy_root)
    if findings:
        for finding in findings:
            print(f"{finding.code} path={finding.path} {finding.detail}")
        print(f"LEGACY_REF_FAILED findings={len(findings)}")
        return 1

    print(f"LEGACY_REF_OK root={root} scanned_without_runtime_dependency=true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
