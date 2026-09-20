#!/usr/bin/env python3
"""Validate or compare a historical, content-addressed dirty-tree baseline.

The filename and kind retain the worker's original ``release-source-set`` label
for evidentiary continuity. The payload includes deferred formats and records a
dirty tree, so it is not a v1 HTML-only release source set and cannot establish
release readiness. A new clean-commit source set is created only after the
R2-R4 implementation and bundle boundary are complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:  # pragma: no cover - only direct CLI calls
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.bundle_contract import BundleError, expand_allowlist, validate_relative_path

SOURCE_SET_KIND = "rebaseline-release-source-set-v1"
SCHEMA_VERSION = "1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_TOP_LEVEL = frozenset(
    {
        "source_set_kind",
        "schema_version",
        "captured_at",
        "release_scope",
        "provenance",
        "basis",
        "roots",
        "files",
        "excluded_classes",
        "source_set_sha256",
    }
)
_ALLOWED_PROVENANCE = frozenset(
    {"state", "head", "branch", "status_sha256", "requires_clean_commit_for_release"}
)
_ALLOWED_BASIS = frozenset(
    {"allowlist_module", "allowlist_symbol", "root_count", "file_count"}
)
_ALLOWED_FILE = frozenset({"path", "sha256", "bytes"})


class SourceSetError(ValueError):
    """Source-set input or current repository content is invalid."""


@dataclass(frozen=True)
class SourceSetResult:
    """Compact successful verification evidence."""

    source_set_path: Path
    root: Path
    file_count: int
    source_set_sha256: str
    current_head: str
    current_status_sha256: str
    release_ready: bool


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise SourceSetError(f"无法读取来源文件：{path}") from exc
    return digest.hexdigest(), size


def _reject_unknown(raw: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = sorted(str(key) for key in raw if key not in allowed)
    if unknown:
        raise SourceSetError(f"{label} 包含未知字段：{', '.join(unknown)}")


def _require_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise SourceSetError(f"{label} 必须是小写 SHA-256")
    return value

def _require_relative_path(value: object, label: str) -> str:
    try:
        return validate_relative_path(value, label=label)
    except BundleError as exc:
        raise SourceSetError(str(exc)) from exc


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceSetError(f"来源集合 JSON 无法读取：{path}") from exc
    if not isinstance(value, dict):
        raise SourceSetError("来源集合顶层必须是对象")
    raw = cast(dict[str, Any], value)
    _reject_unknown(raw, _ALLOWED_TOP_LEVEL, "来源集合")
    required = _ALLOWED_TOP_LEVEL
    missing = sorted(required - set(raw))
    if missing:
        raise SourceSetError(f"来源集合缺少字段：{', '.join(missing)}")
    if raw["source_set_kind"] != SOURCE_SET_KIND:
        raise SourceSetError("来源集合 kind 不符合 rebaseline 合同")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise SourceSetError("来源集合 schema_version 必须为 1.0")
    if not isinstance(raw["captured_at"], str) or not raw["captured_at"].strip():
        raise SourceSetError("来源集合 captured_at 无效")
    if not isinstance(raw["release_scope"], str) or not raw["release_scope"].strip():
        raise SourceSetError("来源集合 release_scope 无效")

    provenance = raw["provenance"]
    if not isinstance(provenance, dict):
        raise SourceSetError("来源集合 provenance 必须是对象")
    _reject_unknown(provenance, _ALLOWED_PROVENANCE, "provenance")
    if set(provenance) != _ALLOWED_PROVENANCE:
        raise SourceSetError("来源集合 provenance 字段不完整")
    if provenance["state"] != "dirty-baseline":
        raise SourceSetError("当前 verifier 只接受 dirty-baseline rebaseline 快照")
    _require_sha(provenance["status_sha256"], "provenance.status_sha256")
    if not isinstance(provenance["head"], str) or not provenance["head"].strip():
        raise SourceSetError("provenance.head 无效")
    if not isinstance(provenance["branch"], str):
        raise SourceSetError("provenance.branch 无效")
    if provenance["requires_clean_commit_for_release"] is not True:
        raise SourceSetError("来源集合必须要求 clean commit 才可发布")

    basis = raw["basis"]
    if not isinstance(basis, dict):
        raise SourceSetError("来源集合 basis 必须是对象")
    _reject_unknown(basis, _ALLOWED_BASIS, "basis")
    if set(basis) != _ALLOWED_BASIS:
        raise SourceSetError("来源集合 basis 字段不完整")
    if basis["allowlist_module"] != "tools/bundle_contract.py":
        raise SourceSetError("来源集合必须绑定 bundle_contract allowlist 模块")
    if basis["allowlist_symbol"] != "DEFAULT_ALLOWLIST":
        raise SourceSetError("来源集合必须绑定 DEFAULT_ALLOWLIST")
    if not isinstance(basis["root_count"], int) or basis["root_count"] <= 0:
        raise SourceSetError("basis.root_count 无效")
    if not isinstance(basis["file_count"], int) or basis["file_count"] <= 0:
        raise SourceSetError("basis.file_count 无效")

    roots = raw["roots"]
    if (
        not isinstance(roots, list)
        or not roots
        or not all(isinstance(item, str) for item in roots)
    ):
        raise SourceSetError("来源集合 roots 必须是非空字符串列表")
    normalised_roots = [
        _require_relative_path(item, label="来源集合 root") for item in roots
    ]
    if normalised_roots != sorted(set(normalised_roots)):
        raise SourceSetError("来源集合 roots 必须唯一并按 POSIX 路径排序")
    if len(normalised_roots) != basis["root_count"]:
        raise SourceSetError("来源集合 root_count 与 roots 不一致")

    files = raw["files"]
    if (
        not isinstance(files, list)
        or not files
        or not all(isinstance(item, dict) for item in files)
    ):
        raise SourceSetError("来源集合 files 必须是非空对象列表")
    file_paths: list[str] = []
    for index, item in enumerate(files):
        record = cast(dict[str, Any], item)
        _reject_unknown(record, _ALLOWED_FILE, f"files[{index}]")
        if set(record) != _ALLOWED_FILE:
            raise SourceSetError(f"files[{index}] 字段不完整")
        file_paths.append(
            _require_relative_path(record["path"], label=f"files[{index}].path")
        )
        _require_sha(record["sha256"], f"files[{index}].sha256")
        if not isinstance(record["bytes"], int) or record["bytes"] < 0:
            raise SourceSetError(f"files[{index}].bytes 无效")
    if file_paths != sorted(set(file_paths)):
        raise SourceSetError("来源集合 files 必须唯一并按 POSIX 路径排序")
    if len(file_paths) != basis["file_count"]:
        raise SourceSetError("来源集合 file_count 与 files 不一致")

    excluded = raw["excluded_classes"]
    if not isinstance(excluded, list) or not excluded or not all(
        isinstance(item, str) and item.strip() for item in excluded
    ):
        raise SourceSetError("来源集合 excluded_classes 必须是非空字符串列表")

    supplied_digest = _require_sha(raw["source_set_sha256"], "source_set_sha256")
    body = {key: value for key, value in raw.items() if key != "source_set_sha256"}
    if _sha256_bytes(_canonical_json(body)) != supplied_digest:
        raise SourceSetError("source_set_sha256 不匹配")
    return raw


def validate_source_set_document(path: Path) -> dict[str, Any]:
    """Validate the frozen historical document without comparing workspace bytes."""

    return _load(path.expanduser().resolve())


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=text,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise SourceSetError(f"git 命令超时：{' '.join(args)}") from exc
    except OSError as exc:
        raise SourceSetError(f"git 命令无法启动：{' '.join(args)}") from exc
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
        raise SourceSetError(f"git 命令失败（{' '.join(args)}）：{detail}") from exc
    return cast(str | bytes, completed.stdout)

def _repo_root(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.is_dir():
        raise SourceSetError(f"验证根必须是存在的目录：{candidate}")
    value = _git(candidate, "rev-parse", "--show-toplevel")
    if not isinstance(value, str) or not value.strip():
        raise SourceSetError("Git 未返回仓库根目录")
    root = Path(value.strip()).resolve()
    if root != candidate:
        raise SourceSetError("验证根必须是 Git 仓库根目录本身")
    return root


def verify_source_set(
    source_set_path: Path,
    *,
    root: Path,
    require_clean: bool = False,
) -> SourceSetResult:
    """Compare current bytes with a historical baseline; never approve a release."""

    source_path = source_set_path.expanduser().resolve()
    payload = validate_source_set_document(source_path)
    if require_clean:
        raise SourceSetError(
            "历史脏树基线不能证明发布就绪；R2-R4 后须生成新的 HTML-only clean-commit 来源集"
        )
    repo = _repo_root(root)
    try:
        roots = cast(list[str], payload["roots"])
        expected_files = cast(list[dict[str, Any]], payload["files"])
        expanded = expand_allowlist(repo, roots)
    except BundleError as exc:
        raise SourceSetError(f"来源集合 roots 无法展开：{exc}") from exc
    expected_paths = tuple(record["path"] for record in expected_files)
    if expanded != expected_paths:
        missing = sorted(set(expected_paths) - set(expanded))
        extra = sorted(set(expanded) - set(expected_paths))
        details: list[str] = []
        if missing:
            details.append(f"missing={','.join(missing[:5])}")
        if extra:
            details.append(f"extra={','.join(extra[:5])}")
        raise SourceSetError("来源集合文件集合漂移：" + "; ".join(details))

    for record in expected_files:
        relative = record["path"]
        path = repo / relative
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise SourceSetError(f"来源文件不存在：{relative}") from exc
        if resolved != path or path.is_symlink() or not path.is_file():
            raise SourceSetError(f"来源文件必须是仓库内普通文件：{relative}")
        digest, size = _sha256_file(path)
        if digest != record["sha256"] or size != record["bytes"]:
            raise SourceSetError(
                f"来源文件摘要漂移：{relative} actual={digest}/{size} "
                f"expected={record['sha256']}/{record['bytes']}"
            )

    head = _git(repo, "rev-parse", "HEAD")
    status = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", text=False)
    if not isinstance(head, str) or not head.strip() or not isinstance(status, bytes):
        raise SourceSetError("Git provenance 输出无效")
    current_status_sha256 = _sha256_bytes(status)
    return SourceSetResult(
        source_set_path=source_path,
        root=repo,
        file_count=len(expected_files),
        source_set_sha256=cast(str, payload["source_set_sha256"]),
        current_head=head.strip(),
        current_status_sha256=current_status_sha256,
        release_ready=False,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_set", type=Path, help="来源集合 JSON")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Git 仓库根目录（必须是仓库根本身）",
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="保留的拒绝式兼容参数；历史脏树基线永远不能证明发布就绪",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_source_set(
            args.source_set,
            root=args.root,
            require_clean=args.require_clean,
        )
    except SourceSetError as exc:
        print(f"SOURCE_SET_FAIL {exc}", file=sys.stderr)
        return 1
    print(
        f"SOURCE_SET_OK files={result.file_count} state=historical_baseline_only "
        f"head={result.current_head} source_set_sha256={result.source_set_sha256} "
        f"status_sha256={result.current_status_sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
