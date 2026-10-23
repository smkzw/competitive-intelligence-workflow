"""本地数据备份/恢复：只读 SQLite 快照 + 仅被 sources 引用的 CAS 字节。

备份产物是普通目录（manifest.json + 数据文件），不是归档包：只包含
ciw2.sqlite3 与 cas/XX/DIGEST，不复制 portals、导出、凭据、日志或缓存，
也不改动源库、WAL 与 CAS。恢复只还原数据文件，不启动任务、模型或渲染。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

SCHEMA_VERSION = "ciw2-backup-v1"
_DATABASE = "ciw2.sqlite3"
_MANIFEST = "manifest.json"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_CHUNK = 1 << 20
_TIMEOUT = 30.0


class BackupError(ValueError):
    """备份或恢复请求无法安全完成。"""


def _digest_value(value: object) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise BackupError("sources table contains a malformed CAS digest")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK):
                digest.update(chunk)
    except OSError as exc:
        raise BackupError(f"cannot read backup file: {path.name}") from exc
    return digest.hexdigest()


def _copy_verified(source: Path, target: Path) -> str:
    digest = hashlib.sha256()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, target.open("xb") as writer:
            while chunk := reader.read(_CHUNK):
                digest.update(chunk)
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
    except OSError as exc:
        raise BackupError(f"cannot copy backup file: {source.name}") from exc
    return digest.hexdigest()


def _connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{quote(path.as_posix(), safe='/')}?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True, timeout=_TIMEOUT)
    except sqlite3.Error as exc:
        raise BackupError(f"cannot open database read-only: {path.name}") from exc


def _check_integrity(conn: sqlite3.Connection, label: str) -> None:
    if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise BackupError(f"database integrity check failed: {label}")


def _database_digests(path: Path) -> set[str]:
    """Read the exact non-null digest/text_digest set from a database file."""
    conn = _connect_readonly(path)
    try:
        _check_integrity(conn, path.name)
        try:
            rows = conn.execute("SELECT digest, text_digest FROM sources").fetchall()
        except sqlite3.Error as exc:
            raise BackupError("database has no readable sources table") from exc
    finally:
        conn.close()
    digests: set[str] = set()
    for raw, text in rows:
        digests.add(_digest_value(raw))
        if text is not None:
            digests.add(_digest_value(text))
    return digests


def _snapshot_database(source: Path, target: Path) -> None:
    """Copy committed source pages (including WAL) through SQLite's backup API."""
    reader = _connect_readonly(source)
    try:
        try:
            writer = sqlite3.connect(target, timeout=_TIMEOUT)
        except sqlite3.Error as exc:
            raise BackupError("cannot create the database snapshot") from exc
        try:
            last_progress = time.monotonic()

            def progress(status: int, remaining: int, total: int) -> None:
                nonlocal last_progress
                if status in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                    if time.monotonic() - last_progress >= _TIMEOUT:
                        raise BackupError("source database remains locked; no backup published")
                else:
                    last_progress = time.monotonic()

            reader.backup(writer, pages=128, progress=progress, sleep=min(0.1, _TIMEOUT))
            # A WAL-mode file grows empty -wal/-shm sidecars whenever it is opened,
            # even read-only; the published backup must stay one self-contained file.
            writer.execute("PRAGMA journal_mode=DELETE")
        finally:
            writer.close()
    finally:
        reader.close()


def _reject_symlink_components(path: Path, label: str) -> None:
    absolute = Path(path)
    if not absolute.is_absolute():
        absolute = Path.cwd() / absolute
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        if part in {"", "."}:
            continue
        current /= part
        if current.is_symlink():
            raise BackupError(f"{label} must not contain symbolic links")


def _existing_directory(path: Path, label: str) -> Path:
    root = Path(path)
    _reject_symlink_components(root, label)
    if not root.is_dir():
        raise BackupError(f"{label} is missing")
    return root.resolve()


def _new_target(path: Path) -> Path:
    target = Path(path)
    if os.path.lexists(target):
        raise BackupError("destination already exists")
    _reject_symlink_components(target.parent, "destination path")
    if not target.parent.is_dir():
        raise BackupError("destination parent directory is missing")
    return target.resolve()


def _require_disjoint(source: Path, target: Path) -> None:
    source_path, target_path = source.resolve(), target.resolve()
    if (
        source_path == target_path
        or source_path.is_relative_to(target_path)
        or target_path.is_relative_to(source_path)
    ):
        raise BackupError("source and destination must not overlap")


def _require_regular(path: Path, label: str) -> None:
    if path.is_symlink():
        raise BackupError(f"{label} must not be a symbolic link")
    if not path.is_file():
        raise BackupError(f"{label} is missing")


def _new_staging(target: Path) -> Path:
    return Path(tempfile.mkdtemp(prefix=f".{target.name}.", suffix=".staging", dir=target.parent))


def _publish(staging: Path, destination: Path) -> None:
    """Reserve the new destination exclusively, then rename the validated tree in."""
    try:
        os.mkdir(destination)
    except FileExistsError as exc:
        raise BackupError("destination already exists") from exc
    try:
        os.rename(staging, destination)
    except BaseException:
        try:
            os.rmdir(destination)
        except OSError:
            pass
        raise


def _source_blob(data_root: Path, digest: str) -> Path:
    cas_root = data_root / "cas"
    if cas_root.is_symlink():
        raise BackupError("CAS directory must not be a symbolic link")
    shard = cas_root / digest[:2]
    if shard.is_symlink():
        raise BackupError("CAS shard directory must not be a symbolic link")
    blob = shard / digest
    if blob.is_symlink():
        raise BackupError("CAS blob must not be a symbolic link")
    if not blob.is_file():
        raise BackupError(f"referenced CAS blob is missing: {digest}")
    return blob


def _tree_files(root: Path) -> set[str]:
    found: set[str] = set()
    pending = [(root, "")]
    while pending:
        directory, prefix = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_symlink():
                    raise BackupError(f"backup tree must not contain symbolic links: {prefix}{entry.name}")
                if entry.is_dir(follow_symlinks=False):
                    pending.append((Path(entry.path), f"{prefix}{entry.name}/"))
                elif entry.is_file(follow_symlinks=False):
                    found.add(f"{prefix}{entry.name}")
                else:
                    raise BackupError(f"unsupported file in backup tree: {prefix}{entry.name}")
    return found


def _parse_manifest(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "files"}:
        raise BackupError("manifest must contain exactly schema_version and files")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise BackupError("unsupported backup manifest schema")
    files = raw["files"]
    if not isinstance(files, dict) or not files:
        raise BackupError("manifest files must be a non-empty object")
    canonical: dict[str, str] = {}
    for key, value in files.items():
        if not isinstance(key, str) or not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            raise BackupError("manifest entries must map relative paths to lowercase sha256 digests")
        if key != _DATABASE:
            parts = key.split("/")
            if len(parts) != 3 or parts[0] != "cas" or parts[1] != value[:2] or parts[2] != value:
                raise BackupError(f"manifest path is not a canonical backup path: {key}")
        canonical[key] = value
    if _DATABASE not in canonical:
        raise BackupError("manifest does not declare ciw2.sqlite3")
    return {"schema_version": SCHEMA_VERSION, "files": dict(sorted(canonical.items()))}


def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BackupError("manifest contains a duplicate key")
        result[key] = value
    return result


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError("backup manifest is not readable JSON") from exc
    return _parse_manifest(raw)


def _manifest_cas_digests(manifest: dict[str, Any]) -> set[str]:
    return {key.split("/")[2] for key in manifest["files"] if key != _DATABASE}


def _verify_tree(root: Path, manifest: dict[str, Any], extra: frozenset[str] = frozenset()) -> None:
    """Prove the directory holds exactly the declared files, with matching bytes and CAS closure."""
    if root.is_symlink():
        raise BackupError("backup directory must not be a symbolic link")
    actual = _tree_files(root)
    expected = set(manifest["files"]) | set(extra)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise BackupError(f"backup file set does not match manifest: missing={missing} unexpected={unexpected}")
    for relative, expected_digest in manifest["files"].items():
        if _sha256_file(root / relative) != expected_digest:
            raise BackupError(f"backup file content does not match manifest: {relative}")
    if _database_digests(root / _DATABASE) != _manifest_cas_digests(manifest):
        raise BackupError("database CAS references do not match manifest")


def create_backup(data_dir: Path, destination: Path) -> dict[str, Any]:
    """Write a validated snapshot backup of one data directory to a new destination."""
    staging: Path | None = None
    try:
        data_root = _existing_directory(data_dir, "data directory")
        target = _new_target(destination)
        _require_disjoint(data_root, target)
        database = data_root / _DATABASE
        _require_regular(database, "source database")
        for suffix in ("-wal", "-shm"):
            if database.with_name(database.name + suffix).is_symlink():
                raise BackupError("source database sidecars must not be symbolic links")
        if (data_root / "cas").is_symlink():
            raise BackupError("CAS directory must not be a symbolic link")
        staging = _new_staging(target)
        snapshot = staging / _DATABASE
        _snapshot_database(database, snapshot)
        files = {_DATABASE: _sha256_file(snapshot)}
        for digest in sorted(_database_digests(snapshot)):
            relative = f"cas/{digest[:2]}/{digest}"
            copied = _copy_verified(_source_blob(data_root, digest), staging / relative)
            if copied != digest:
                raise BackupError(f"CAS blob content does not match its digest: {relative}")
            files[relative] = copied
        manifest = _parse_manifest({"schema_version": SCHEMA_VERSION, "files": files})
        (staging / _MANIFEST).write_bytes(_manifest_bytes(manifest))
        _verify_tree(staging, manifest, frozenset({_MANIFEST}))
        _publish(staging, target)
        staging = None
        return manifest
    except BackupError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise BackupError(f"backup failed: {exc}") from exc
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


def restore_backup(backup_dir: Path, destination: Path) -> dict[str, Any]:
    """Restore one validated backup into a new data directory; history stays data only."""
    staging: Path | None = None
    try:
        source = _existing_directory(backup_dir, "backup directory")
        target = _new_target(destination)
        _require_disjoint(source, target)
        _require_regular(source / _MANIFEST, "backup manifest")
        manifest = _load_manifest(source / _MANIFEST)
        _verify_tree(source, manifest, frozenset({_MANIFEST}))
        staging = _new_staging(target)
        for relative, expected in manifest["files"].items():
            copied = _copy_verified(source / relative, staging / relative)
            if copied != expected:
                raise BackupError(f"backup file content does not match manifest: {relative}")
        _verify_tree(staging, manifest)
        _publish(staging, target)
        staging = None
        return manifest
    except BackupError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise BackupError(f"restore failed: {exc}") from exc
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
