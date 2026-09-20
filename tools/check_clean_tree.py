#!/usr/bin/env python3
"""Fail-closed Git work-tree checker for release and task-finalization hooks.

The checker never stages, commits, resets, cleans, or writes repository files.  A
caller may explicitly allow exact paths or path prefixes for known run-time
outputs; every other staged, unstaged, or untracked entry remains a failure.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast


class CleanTreeError(ValueError):
    """Input or repository state cannot be evaluated safely."""


@dataclass(frozen=True)
class StatusEntry:
    """One porcelain status record."""

    code: str
    path: str


@dataclass(frozen=True)
class CleanTreeResult:
    """Observed status and the entries not covered by an explicit allowlist."""

    root: Path
    head: str
    status_sha256: str
    entries: tuple[StatusEntry, ...]
    unexpected: tuple[StatusEntry, ...]

    @property
    def ok(self) -> bool:
        return not self.unexpected


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    executable = "git"
    try:
        completed = subprocess.run(
            [executable, "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=text,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise CleanTreeError(f"git 命令超时：{' '.join(args)}") from exc
    except OSError as exc:
        raise CleanTreeError(f"git 命令无法启动：{' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        detail = (
            stderr.strip().splitlines()[-1]
            if stderr.strip()
            else f"退出码 {exc.returncode}"
        )
        raise CleanTreeError(f"git 命令失败（{' '.join(args)}）：{detail}") from exc
    return cast(str | bytes, completed.stdout)


def _repo_root(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.exists() or not candidate.is_dir():
        raise CleanTreeError(f"检查根必须是存在的普通目录：{candidate}")
    raw = _git(candidate, "rev-parse", "--show-toplevel")
    if not isinstance(raw, str) or not raw.strip():
        raise CleanTreeError("Git 未返回仓库根目录")
    root = Path(raw.strip()).resolve()
    if root != candidate:
        raise CleanTreeError(
            f"检查根不是 Git 仓库根目录（toplevel={root}）；必须从仓库根目录检查"
        )
    return root


def _parse_status(raw: bytes) -> tuple[StatusEntry, ...]:
    """Parse ``git status --porcelain=v1 -z`` without path quoting."""

    fields = raw.split(b"\0")
    entries: list[StatusEntry] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 3 or field[2:3] != b" ":
            raise CleanTreeError("Git status 返回无法解析的 porcelain 记录")
        code = field[:2].decode("ascii", errors="strict")
        path = os.fsdecode(field[3:])
        entries.append(StatusEntry(code=code, path=path))
        # With -z, rename/copy records carry the second path as a separate
        # NUL field.  The first path is the destination in Git's v1 format;
        # retain it as the actionable path and consume the source path.
        if code[0] in {"R", "C"} and index < len(fields):
            index += 1
    return tuple(entries)


def _normalise_allow(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CleanTreeError(f"{label} 不能为空")
    if "\\" in value or value.startswith("/") or value.startswith("~"):
        raise CleanTreeError(f"{label} 必须是相对 POSIX 路径：{value!r}")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise CleanTreeError(f"{label} 不得包含绝对路径或 . / ..：{value!r}")
    return pure.as_posix()


def _is_allowed(path: str, exact: frozenset[str], prefixes: tuple[str, ...]) -> bool:
    if path in exact:
        return True
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


def check_clean_tree(
    root: Path,
    *,
    allow_paths: Sequence[str] = (),
    allow_prefixes: Sequence[str] = (),
) -> CleanTreeResult:
    """Observe the repository and fail closed for every non-allowlisted path."""

    repo = _repo_root(root)
    exact = frozenset(_normalise_allow(value, label="allow-path") for value in allow_paths)
    prefixes = tuple(
        sorted({_normalise_allow(value, label="allow-prefix") for value in allow_prefixes})
    )
    raw = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", text=False)
    if not isinstance(raw, bytes):
        raise CleanTreeError("Git status 未返回字节流")
    entries = _parse_status(raw)
    unexpected = tuple(
        entry for entry in entries if not _is_allowed(entry.path, exact, prefixes)
    )
    head_raw = _git(repo, "rev-parse", "HEAD")
    if not isinstance(head_raw, str) or not head_raw.strip():
        raise CleanTreeError("Git 未返回 HEAD")
    return CleanTreeResult(
        root=repo,
        head=head_raw.strip(),
        status_sha256=hashlib.sha256(raw).hexdigest(),
        entries=entries,
        unexpected=unexpected,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Git 仓库根目录（必须是仓库根本身）",
    )
    parser.add_argument(
        "--allow-path",
        action="append",
        default=[],
        help="显式允许一个相对路径；可重复",
    )
    parser.add_argument(
        "--allow-prefix",
        action="append",
        default=[],
        help="显式允许一个相对路径前缀；可重复",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = check_clean_tree(
            args.root,
            allow_paths=args.allow_path,
            allow_prefixes=args.allow_prefix,
        )
    except CleanTreeError as exc:
        print(f"CLEAN_TREE_ENV_ERROR {exc}", file=sys.stderr)
        return 2
    if result.unexpected:
        print(
            f"CLEAN_TREE_FAIL entries={len(result.unexpected)} "
            f"observed={len(result.entries)} status_sha256={result.status_sha256}",
            file=sys.stderr,
        )
        for entry in result.unexpected:
            print(f"{entry.code} {entry.path}", file=sys.stderr)
        return 1
    print(
        f"CLEAN_TREE_OK head={result.head} entries={len(result.entries)} "
        f"status_sha256={result.status_sha256} allowlisted={len(result.entries)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
