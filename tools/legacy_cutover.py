#!/usr/bin/env python3
"""Task 10.5 精准旧工程切换工具。

所有目标必须来自显式 registry，并位于显式批准根内。工具没有默认旧根；
``inventory``/``validate`` 只读，``apply`` 只执行已授权的逐项动作且不跟随
符号链接。Task 10.5 的测试只对临时 fixture 根调用本模块。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Never

SCHEMA_VERSION = "1.0"
ENTRY_KINDS = {
    "legacy_root",
    "legacy_skill",
    "archive_copy",
    "symlink",
    "launcher",
    "consumer_reference",
    "cache",
    "backup",
}
ACTIONS = {"delete", "retain"}
HASH_MODES = {"content", "metadata"}


class CutoverError(ValueError):
    """输入或当前文件系统状态不满足精准切换合同。"""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CutoverError(f"无法读取{label}：{path}") from error
    if not isinstance(payload, dict):
        raise CutoverError(f"{label}顶层必须是对象")
    return payload


def _write_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_keys(
    payload: dict[str, Any],
    required: set[str],
    label: str,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - payload.keys()
    unknown = payload.keys() - required - optional
    if missing:
        raise CutoverError(f"{label}缺少字段：{sorted(missing)}")
    if unknown:
        raise CutoverError(f"{label}含未知字段：{sorted(unknown)}")


def _absolute_clean_path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise CutoverError(f"{label}必须是非空绝对路径")
    path = Path(raw)
    if not path.is_absolute() or ".." in path.parts:
        raise CutoverError(f"{label}必须是无逃逸的绝对路径：{raw}")
    return path


def _containing_root(path: Path, roots: tuple[Path, ...]) -> Path:
    matches: list[Path] = []
    for root in roots:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        matches.append(root)
    if not matches:
        raise CutoverError(f"登记路径越出批准根：{path}")
    return max(matches, key=lambda item: len(item.parts))


def _reject_symlink_ancestors(path: Path, root: Path) -> None:
    try:
        if stat.S_ISLNK(root.lstat().st_mode):
            raise CutoverError(f"批准根不得是符号链接：{root}")
    except FileNotFoundError:
        pass
    current = root
    relative = path.relative_to(root)
    ancestors = relative.parts[:-1] if relative.parts else ()
    for part in ancestors:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise CutoverError(f"登记路径祖先不得是符号链接：{current}")


def _node_type(mode: int) -> str:
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "directory"
    return "other"


def _metadata_digest(path: Path, observed: os.stat_result) -> str:
    payload = {
        "mode": stat.S_IMODE(observed.st_mode),
        "size": observed.st_size,
        "type": _node_type(observed.st_mode),
    }
    if stat.S_ISLNK(observed.st_mode):
        payload["link_target"] = os.readlink(path)
    return canonical_digest(payload)


def _directory_digest(path: Path) -> str:
    records: list[dict[str, Any]] = []

    def visit(directory: Path, prefix: Path) -> None:
        with os.scandir(directory) as stream:
            entries = sorted(stream, key=lambda item: item.name)
        for entry in entries:
            child = directory / entry.name
            relative = (prefix / entry.name).as_posix()
            observed = child.lstat()
            kind = _node_type(observed.st_mode)
            record: dict[str, Any] = {"path": relative, "type": kind}
            if kind == "file":
                record["sha256"] = file_digest(child)
            elif kind == "symlink":
                record["sha256"] = hashlib.sha256(os.readlink(child).encode()).hexdigest()
            else:
                record["sha256"] = _metadata_digest(child, observed)
            records.append(record)
            if kind == "directory":
                visit(child, prefix / entry.name)

    visit(path, Path())
    return canonical_digest(records)


def _content_digest(path: Path, observed: os.stat_result) -> str:
    kind = _node_type(observed.st_mode)
    if kind == "file":
        return file_digest(path)
    if kind == "symlink":
        return hashlib.sha256(os.readlink(path).encode()).hexdigest()
    if kind == "directory":
        return _directory_digest(path)
    return _metadata_digest(path, observed)


def _observe_entry(entry: dict[str, Any], roots: tuple[Path, ...]) -> dict[str, Any]:
    path = _absolute_clean_path(entry["path"], f"{entry['entry_id']} path")
    root = _containing_root(path, roots)
    _reject_symlink_ancestors(path, root)
    base = {
        "entry_id": entry["entry_id"],
        "kind": entry["kind"],
        "path": str(path),
        "approved_root": str(root),
        "action": entry["action"],
        "hash_mode": entry["hash_mode"],
    }
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return {
            **base,
            "exists": False,
            "realpath": os.path.realpath(path),
            "device": None,
            "inode": None,
            "node_type": "absent",
            "sha256": None,
        }
    digest = (
        _content_digest(path, observed)
        if entry["hash_mode"] == "content"
        else _metadata_digest(path, observed)
    )
    return {
        **base,
        "exists": True,
        "realpath": os.path.realpath(path),
        "device": observed.st_dev,
        "inode": observed.st_ino,
        "node_type": _node_type(observed.st_mode),
        "sha256": digest,
    }


def _parse_registry(payload: dict[str, Any]) -> tuple[tuple[Path, ...], list[dict[str, Any]]]:
    _require_keys(payload, {"schema_version", "approved_roots", "entries"}, "registry")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise CutoverError("registry schema_version 必须为 1.0")
    raw_roots = payload["approved_roots"]
    raw_entries = payload["entries"]
    if not isinstance(raw_roots, list) or not raw_roots:
        raise CutoverError("registry approved_roots 必须是非空列表")
    roots = tuple(_absolute_clean_path(value, "approved_root") for value in raw_roots)
    if len(set(roots)) != len(roots):
        raise CutoverError("registry approved_roots 不得重复")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise CutoverError("registry entries 必须是非空列表")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            raise CutoverError(f"registry entry #{index} 必须是对象")
        _require_keys(
            raw_entry,
            {"entry_id", "kind", "path", "action", "hash_mode"},
            f"registry entry #{index}",
        )
        entry_id = raw_entry["entry_id"]
        if not isinstance(entry_id, str) or not entry_id or entry_id in seen:
            raise CutoverError(f"registry entry_id 无效或重复：{entry_id!r}")
        if raw_entry["kind"] not in ENTRY_KINDS:
            raise CutoverError(f"registry kind 未登记：{raw_entry['kind']!r}")
        if raw_entry["action"] not in ACTIONS:
            raise CutoverError(f"registry action 未登记：{raw_entry['action']!r}")
        if raw_entry["hash_mode"] not in HASH_MODES:
            raise CutoverError(f"registry hash_mode 未登记：{raw_entry['hash_mode']!r}")
        path = _absolute_clean_path(raw_entry["path"], f"{entry_id} path")
        root = _containing_root(path, roots)
        _reject_symlink_ancestors(path, root)
        seen.add(entry_id)
        entries.append(dict(raw_entry))
    paths = [entry["path"] for entry in entries]
    if len(paths) != len(set(paths)):
        raise CutoverError("registry path 不得重复")
    for parent in entries:
        if parent["action"] != "delete":
            continue
        parent_path = Path(parent["path"])
        for child in entries:
            if child["action"] != "retain" or child is parent:
                continue
            try:
                Path(child["path"]).relative_to(parent_path)
            except ValueError:
                continue
            raise CutoverError(
                f"不得删除父路径同时保留子项：{parent['entry_id']} -> {child['entry_id']}"
            )
    return roots, sorted(entries, key=lambda item: item["entry_id"])


def build_inventory(registry: dict[str, Any]) -> dict[str, Any]:
    roots, entries = _parse_registry(registry)
    observed = [_observe_entry(entry, roots) for entry in entries]
    if not any(entry["exists"] for entry in observed):
        raise CutoverError("inventory 至少必须观察到一个存在的登记项")
    for entry in observed:
        if (entry["kind"] == "symlink") != (entry["node_type"] == "symlink"):
            raise CutoverError(f"登记 kind 与符号链接观测不一致：{entry['entry_id']}")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "inventory_kind": "exact-legacy-cutover-v1",
        "registry_sha256": canonical_digest(registry),
        "approved_roots": [str(root) for root in roots],
        "entries": observed,
    }
    payload["inventory_sha256"] = canonical_digest(payload)
    return payload


def registry_for_legacy_root(root: Path) -> dict[str, Any]:
    """Build the exact, non-symlink-following registry used by the frozen CLI."""

    root = _absolute_clean_path(str(root), "legacy_root")
    if not root.exists() or root.is_symlink() or not root.is_dir():
        raise CutoverError("legacy_root 必须是存在的普通目录且不得是符号链接")
    entries: list[dict[str, str]] = []

    def add(path: Path, kind: str, hash_mode: str) -> None:
        relative = path.relative_to(root)
        suffix = "root" if not relative.parts else relative.as_posix()
        entry_id = "legacy-" + hashlib.sha256(suffix.encode()).hexdigest()[:20]
        entries.append(
            {
                "entry_id": entry_id,
                "kind": kind,
                "path": str(path),
                "action": "delete",
                "hash_mode": hash_mode,
            }
        )

    add(root, "legacy_root", "metadata")

    def visit(directory: Path) -> None:
        with os.scandir(directory) as stream:
            children = sorted(stream, key=lambda item: item.name)
        for child in children:
            path = directory / child.name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                add(path, "symlink", "metadata")
            elif stat.S_ISDIR(mode):
                add(path, "archive_copy", "metadata")
                visit(path)
            else:
                # The shorthand must be safe for credential/session carriers whose
                # names are not predictable. Exact content hashing is opt-in via
                # an explicit reviewed registry.
                add(path, "consumer_reference", "metadata")

    visit(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "approved_roots": [str(root)],
        "entries": entries,
    }


def _verify_inventory(payload: dict[str, Any]) -> None:
    _require_keys(
        payload,
        {
            "schema_version",
            "inventory_kind",
            "registry_sha256",
            "approved_roots",
            "entries",
            "inventory_sha256",
        },
        "inventory",
    )
    digest = payload["inventory_sha256"]
    body = {key: value for key, value in payload.items() if key != "inventory_sha256"}
    if digest != canonical_digest(body):
        raise CutoverError("inventory_sha256 不匹配")


def authorization_digest(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "authorization_sha256"}
    return canonical_digest(body)


def _verify_authorization(payload: dict[str, Any], inventory: dict[str, Any]) -> None:
    _require_keys(
        payload,
        {
            "schema_version",
            "authorization_kind",
            "inventory_sha256",
            "registry_sha256",
            "recovery_receipt_sha256",
            "preauthorization_validation_sha256",
            "actions",
            "authorization_sha256",
        },
        "authorization",
    )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise CutoverError("authorization schema_version 必须为 1.0")
    if payload["authorization_kind"] != "exact-legacy-cutover-authorization-v1":
        raise CutoverError("authorization_kind 不匹配")
    if payload["authorization_sha256"] != authorization_digest(payload):
        raise CutoverError("authorization_sha256 不匹配")
    if payload["inventory_sha256"] != inventory["inventory_sha256"]:
        raise CutoverError("授权清单摘要与 inventory 不匹配")
    if payload["registry_sha256"] != inventory["registry_sha256"]:
        raise CutoverError("授权 registry 摘要与 inventory 不匹配")
    validation_digest = payload["preauthorization_validation_sha256"]
    if not isinstance(validation_digest, str) or len(validation_digest) != 64 or any(
        character not in "0123456789abcdef" for character in validation_digest
    ):
        raise CutoverError("授权预验证摘要必须是小写 SHA-256")
    expected_actions = [
        {"entry_id": entry["entry_id"], "action": entry["action"]}
        for entry in inventory["entries"]
    ]
    if payload["actions"] != expected_actions:
        raise CutoverError("授权动作与 inventory 不完全一致")


def _recovery_digest(payload: dict[str, Any]) -> str:
    return canonical_digest(payload)


def _verify_recovery(recovery: dict[str, Any]) -> None:
    _require_keys(
        recovery,
        {
            "schema_version",
            "receipt_kind",
            "status",
            "recovery_package_sha256",
            "issued_at",
        },
        "recovery receipt",
    )
    if recovery["schema_version"] != SCHEMA_VERSION:
        raise CutoverError("恢复包回执 schema_version 必须为 1.0")
    if recovery["receipt_kind"] != "recovery-package-v1" or recovery["status"] != "passed":
        raise CutoverError("恢复包回执尚未通过")
    digest = recovery["recovery_package_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise CutoverError("恢复包摘要必须是小写 SHA-256")
    issued_at = recovery["issued_at"]
    if not isinstance(issued_at, str):
        raise CutoverError("恢复包回执时间必须是带时区 ISO 8601 字符串")
    try:
        parsed = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise CutoverError("恢复包回执时间格式无效") from error
    if parsed.utcoffset() is None:
        raise CutoverError("恢复包回执时间必须带时区")


def validate_cutover(
    inventory: dict[str, Any], authorization: dict[str, Any], recovery: dict[str, Any]
) -> dict[str, Any]:
    preauthorization = validate_inventory(inventory, recovery)
    _verify_authorization(authorization, inventory)
    if authorization["recovery_receipt_sha256"] != _recovery_digest(recovery):
        raise CutoverError("恢复包回执摘要与授权不匹配")
    if (
        authorization["preauthorization_validation_sha256"]
        != preauthorization["validation_sha256"]
    ):
        raise CutoverError("授权未绑定当前预验证回执")
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "receipt_kind": "legacy-cutover-validation-v1",
        "status": "validated",
        "inventory_sha256": inventory["inventory_sha256"],
        "authorization_sha256": authorization["authorization_sha256"],
        "recovery_receipt_sha256": authorization["recovery_receipt_sha256"],
        "content_mode": preauthorization["content_mode"],
    }
    receipt["validation_sha256"] = canonical_digest(receipt)
    return receipt


def validate_inventory(
    inventory: dict[str, Any], recovery: dict[str, Any], legacy_root: Path | None = None
) -> dict[str, Any]:
    """Task 10.7 pre-authorization validation used by the frozen CLI."""

    _verify_inventory(inventory)
    _verify_recovery(recovery)
    if legacy_root is not None:
        expected = str(_absolute_clean_path(str(legacy_root), "legacy_root"))
        if expected not in inventory["approved_roots"]:
            raise CutoverError("legacy_root 与 inventory 批准根不匹配")
    roots = tuple(
        _absolute_clean_path(value, "inventory approved_root")
        for value in inventory["approved_roots"]
    )
    current = [_observe_entry(entry, roots) for entry in inventory["entries"]]
    if current != inventory["entries"]:
        raise CutoverError("inventory 后文件系统状态发生 device/inode/type/摘要漂移")
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "receipt_kind": "legacy-cutover-preauthorization-validation-v1",
        "status": "validated",
        "inventory_sha256": inventory["inventory_sha256"],
        "recovery_receipt_sha256": _recovery_digest(recovery),
        "content_mode": (
            "explicit_content"
            if any(entry["hash_mode"] == "content" for entry in inventory["entries"])
            else "metadata_only"
        ),
    }
    receipt["validation_sha256"] = canonical_digest(receipt)
    return receipt


def _verify_validation(
    receipt: dict[str, Any], inventory: dict[str, Any], authorization: dict[str, Any]
) -> None:
    _require_keys(
        receipt,
        {
            "schema_version",
            "receipt_kind",
            "status",
            "inventory_sha256",
            "authorization_sha256",
            "recovery_receipt_sha256",
            "content_mode",
            "validation_sha256",
        },
        "validation receipt",
    )
    body = {key: value for key, value in receipt.items() if key != "validation_sha256"}
    if receipt["validation_sha256"] != canonical_digest(body):
        raise CutoverError("validation_sha256 不匹配")
    expected = (
        "legacy-cutover-validation-v1",
        "validated",
        inventory["inventory_sha256"],
        authorization["authorization_sha256"],
        authorization["recovery_receipt_sha256"],
        receipt["content_mode"],
    )
    actual = (
        receipt["receipt_kind"],
        receipt["status"],
        receipt["inventory_sha256"],
        receipt["authorization_sha256"],
        receipt["recovery_receipt_sha256"],
        receipt["content_mode"],
    )
    if actual != expected:
        raise CutoverError("validation receipt 未绑定当前授权链")


def _matches_original(current: dict[str, Any], original: dict[str, Any]) -> bool:
    return current == original


def _matches_directory_after_child_deletes(
    current: dict[str, Any], original: dict[str, Any]
) -> bool:
    keys = (
        "entry_id",
        "kind",
        "path",
        "approved_root",
        "action",
        "hash_mode",
        "exists",
        "realpath",
        "device",
        "inode",
        "node_type",
    )
    return original["node_type"] == "directory" and all(
        current[key] == original[key] for key in keys
    )


def apply_cutover(
    inventory: dict[str, Any],
    authorization: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _verify_inventory(inventory)
    _verify_authorization(authorization, inventory)
    if validation is not None:
        _verify_validation(validation, inventory, authorization)
    roots = tuple(
        _absolute_clean_path(value, "inventory approved_root")
        for value in inventory["approved_roots"]
    )
    current = [_observe_entry(entry, roots) for entry in inventory["entries"]]
    for observed, original in zip(current, inventory["entries"], strict=True):
        if original["action"] == "delete" and not observed["exists"]:
            continue
        unchanged = _matches_original(observed, original)
        resumable_directory = _matches_directory_after_child_deletes(observed, original)
        if not unchanged and not resumable_directory:
            raise CutoverError(f"apply 前登记项发生漂移：{original['entry_id']}")

    outcomes: list[dict[str, str]] = []
    ordered = sorted(
        inventory["entries"],
        key=lambda item: len(Path(item["path"]).parts),
        reverse=True,
    )
    for original in ordered:
        if original["action"] == "retain":
            outcomes.append({"entry_id": original["entry_id"], "result": "retained"})
            continue
        current_entry = _observe_entry(original, roots)
        if not current_entry["exists"]:
            outcomes.append({"entry_id": original["entry_id"], "result": "already_absent"})
            continue
        unchanged = _matches_original(current_entry, original)
        safe_directory = _matches_directory_after_child_deletes(current_entry, original)
        if not unchanged and not safe_directory:
            raise CutoverError(f"处置瞬间登记项发生漂移：{original['entry_id']}")
        path = Path(original["path"])
        try:
            if current_entry["node_type"] == "directory":
                path.rmdir()
            else:
                path.unlink()
        except OSError as error:
            raise CutoverError(
                f"登记项处置失败，可修复后用同一授权幂等重放：{original['entry_id']}"
            ) from error
        if path.exists() or path.is_symlink():
            raise CutoverError(f"登记项处置后仍存在：{original['entry_id']}")
        outcomes.append({"entry_id": original["entry_id"], "result": "deleted"})

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "receipt_kind": "legacy-cutover-apply-v1",
        "status": "applied",
        "inventory_sha256": inventory["inventory_sha256"],
        "authorization_sha256": authorization["authorization_sha256"],
        "validation_sha256": (
            validation["validation_sha256"]
            if validation
            else authorization["preauthorization_validation_sha256"]
        ),
        "outcomes": sorted(outcomes, key=lambda item: item["entry_id"]),
    }
    receipt["apply_sha256"] = canonical_digest(receipt)
    return receipt


def absence_check(
    inventory: dict[str, Any], scan_roots: tuple[Path, ...] = ()
) -> dict[str, Any]:
    _verify_inventory(inventory)
    roots = tuple(
        _absolute_clean_path(value, "inventory approved_root")
        for value in inventory["approved_roots"]
    )
    checked_scan_roots = tuple(
        _absolute_clean_path(str(root), "scan_root") for root in scan_roots
    )
    if checked_scan_roots:
        for entry in inventory["entries"]:
            _containing_root(Path(entry["path"]), checked_scan_roots)
    remaining = [
        entry["entry_id"]
        for entry in inventory["entries"]
        if _observe_entry(entry, roots)["exists"]
    ]
    if remaining:
        raise CutoverError(f"仍存在已登记旧运行时或引用：{remaining}")
    result = {
        "schema_version": SCHEMA_VERSION,
        "receipt_kind": "legacy-absence-check-v1",
        "status": "absent",
        "inventory_sha256": inventory["inventory_sha256"],
    }
    result["absence_sha256"] = canonical_digest(result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="精准旧工程切换工具（无默认目标）")
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("inventory")
    source = inventory.add_mutually_exclusive_group(required=True)
    source.add_argument("--registry", type=Path)
    source.add_argument("--legacy-root", type=Path)
    inventory.add_argument("--output", "--manifest", dest="output", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--inventory", "--manifest", dest="inventory", type=Path, required=True)
    validate.add_argument("--authorization", type=Path)
    validate.add_argument("--legacy-root", type=Path)
    validate.add_argument("--recovery-receipt", type=Path, required=True)
    validate.add_argument("--output", type=Path)
    apply = commands.add_parser("apply")
    apply.add_argument("--inventory", "--manifest", dest="inventory", type=Path, required=True)
    apply.add_argument("--authorization", type=Path, required=True)
    apply.add_argument("--validation-receipt", type=Path)
    apply.add_argument("--output", "--receipt", dest="output", type=Path, required=True)
    absence = commands.add_parser("absence-check")
    absence.add_argument("--inventory", "--manifest", dest="inventory", type=Path, required=True)
    absence.add_argument("--scan-root", action="append", type=Path, default=[])
    absence.add_argument("--output", type=Path)
    return parser


def _success_signal(command: str, result: dict[str, Any]) -> str:
    if command == "inventory":
        return (
            "CUTOVER_INVENTORY_OK mutated=0 "
            f"inventory_sha256={result['inventory_sha256']}"
        )
    if command == "validate":
        return (
            "CUTOVER_VALIDATE_OK escapes=0 recovery=passed "
            f"content_mode={result['content_mode']} "
            f"inventory_sha256={result['inventory_sha256']}"
        )
    if command == "apply":
        return f"CUTOVER_APPLY_OK apply_sha256={result['apply_sha256']}"
    return f"LEGACY_ABSENCE_OK absence_sha256={result['absence_sha256']}"


def main(argv: list[str] | None = None) -> Never:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inventory":
            registry = (
                _load_object(args.registry, "registry")
                if args.registry
                else registry_for_legacy_root(args.legacy_root)
            )
            result = build_inventory(registry)
        elif args.command == "validate":
            inventory = _load_object(args.inventory, "inventory")
            recovery = _load_object(args.recovery_receipt, "recovery receipt")
            result = (
                validate_cutover(
                    inventory,
                    _load_object(args.authorization, "authorization"),
                    recovery,
                )
                if args.authorization
                else validate_inventory(inventory, recovery, args.legacy_root)
            )
        elif args.command == "apply":
            result = apply_cutover(
                _load_object(args.inventory, "inventory"),
                _load_object(args.authorization, "authorization"),
                _load_object(args.validation_receipt, "validation receipt")
                if args.validation_receipt
                else None,
            )
        else:
            result = absence_check(
                _load_object(args.inventory, "inventory"), tuple(args.scan_root)
            )
        if getattr(args, "output", None):
            _write_object(args.output, result)
        print(_success_signal(args.command, result))
    except CutoverError as error:
        print(f"LEGACY_CUTOVER_FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error
    raise SystemExit(0)


if __name__ == "__main__":
    main()
