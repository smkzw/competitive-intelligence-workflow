#!/usr/bin/env python3
"""Task 10.6 recovery-package-v1 生产者、严格校验与恢复演练支撑工具。

恢复包只允许绑定本 RC、批准迁移资料和本次验收记录；payload 采用显式
allowlist，结构上排除可运行旧流水线。工具没有默认输入或输出路径，
验证失败的包一律拒绝出具回执。Task 10.6A 的测试只对临时 fixture
输入调用本模块；真实旧根永远不会成为输入。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Never

SCHEMA_VERSION = "1.0"
MANIFEST_KIND = "recovery-package-manifest-v1"
RECEIPT_KIND = "recovery-package-v1"
PACKAGE_PREFIX = "recovery-package-v1"
MANIFEST_MEMBER = f"{PACKAGE_PREFIX}/recovery-manifest.json"
PAYLOAD_PREFIX = f"{PACKAGE_PREFIX}/payload/"
PAYLOAD_KINDS = {"approved_material": "materials", "acceptance_record": "acceptance"}
RECEIPT_FIELDS = {
    "schema_version",
    "receipt_kind",
    "status",
    "recovery_package_sha256",
    "issued_at",
}
MANIFEST_FIELDS = {
    "schema_version",
    "package_kind",
    "source_commit",
    "bundle",
    "bundle_manifest",
    "payload",
    "created_at",
    "manifest_sha256",
}
_HEX = set("0123456789abcdef")


class RecoveryPackageError(ValueError):
    """输入、包字节或回执不满足 recovery-package-v1 合同。"""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_digest(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_lower_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _require_tz_iso(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise RecoveryPackageError(f"{label}必须是带时区 ISO 8601 字符串")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RecoveryPackageError(f"{label}时间格式无效：{value!r}") from error
    if parsed.utcoffset() is None:
        raise RecoveryPackageError(f"{label}必须带时区")
    return parsed


def _require_source_commit(value: object) -> str:
    if not isinstance(value, str) or not 7 <= len(value) <= 64 or set(value) - _HEX:
        raise RecoveryPackageError("source_commit 必须是 7-64 位小写十六进制")
    return value


def _require_keys(
    payload: dict[str, Any],
    required: set[str],
    label: str,
) -> None:
    missing = required - payload.keys()
    unknown = payload.keys() - required
    if missing:
        raise RecoveryPackageError(f"{label}缺少字段：{sorted(missing)}")
    if unknown:
        raise RecoveryPackageError(f"{label}含未知字段：{sorted(unknown)}")


def _require_relative(value: object, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise RecoveryPackageError(f"{label}必须是相对路径字符串")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "\\" in value:
        raise RecoveryPackageError(f"{label}必须是安全相对路径：{value!r}")


@dataclass(frozen=True)
class _PayloadEntry:
    kind: str
    origin: str
    source: Path
    member: str


def _collect_kind(kind: str, roots: Sequence[Path]) -> list[_PayloadEntry]:
    if kind not in PAYLOAD_KINDS:
        raise RecoveryPackageError(f"payload kind 未登记：{kind!r}")
    entries: list[_PayloadEntry] = []
    for root in roots:
        if root.is_symlink() or not root.exists():
            raise RecoveryPackageError(f"{kind} 输入必须是存在的普通路径：{root}")
        if root.is_file():
            origin = root.name
            entries.append(
                _PayloadEntry(
                    kind=kind,
                    origin=origin,
                    source=root,
                    member=f"{PAYLOAD_PREFIX}{PAYLOAD_KINDS[kind]}/{origin}",
                )
            )
            continue
        for current, dirnames, filenames in os.walk(root):
            current_path = Path(current)
            for name in dirnames:
                if (current_path / name).is_symlink():
                    raise RecoveryPackageError(
                        f"{kind} 输入不得包含符号链接：{current_path / name}"
                    )
            for name in sorted(filenames):
                child = current_path / name
                if child.is_symlink():
                    raise RecoveryPackageError(f"{kind} 输入不得包含符号链接：{child}")
                origin = child.relative_to(root).as_posix()
                entries.append(
                    _PayloadEntry(
                        kind=kind,
                        origin=origin,
                        source=child,
                        member=f"{PAYLOAD_PREFIX}{PAYLOAD_KINDS[kind]}/{origin}",
                    )
                )
    return entries


def _binding(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RecoveryPackageError(f"{label}必须是存在的普通文件：{path}")
    data = path.read_bytes()
    return {"name": path.name, "sha256": _sha256_bytes(data), "bytes": len(data)}


def _require_binding(value: object, label: str) -> None:
    if not isinstance(value, dict):
        raise RecoveryPackageError(f"{label}必须是对象")
    _require_keys(value, {"name", "sha256", "bytes"}, label)
    if not isinstance(value["name"], str) or not value["name"]:
        raise RecoveryPackageError(f"{label}.name 必须是非空字符串")
    if not _is_lower_sha256(value["sha256"]):
        raise RecoveryPackageError(f"{label}.sha256 必须是小写 SHA-256")
    raw_bytes = value["bytes"]
    if not isinstance(raw_bytes, int) or isinstance(raw_bytes, bool) or raw_bytes < 0:
        raise RecoveryPackageError(f"{label}.bytes 必须是非负整数")


def _require_payload_item(item: object, index: int) -> None:
    label = f"payload #{index}"
    if not isinstance(item, dict):
        raise RecoveryPackageError(f"{label}必须是对象")
    _require_keys(item, {"member", "kind", "origin", "sha256", "bytes"}, label)
    if item["kind"] not in PAYLOAD_KINDS:
        raise RecoveryPackageError(f"{label} kind 未登记：{item['kind']!r}")
    member = item["member"]
    if not isinstance(member, str) or not member.startswith(PAYLOAD_PREFIX):
        raise RecoveryPackageError(f"{label} member 必须位于 {PAYLOAD_PREFIX} 之下")
    _require_relative(member, f"{label} member")
    bucket = member.removeprefix(PAYLOAD_PREFIX).split("/", 1)[0]
    if bucket != PAYLOAD_KINDS[item["kind"]]:
        raise RecoveryPackageError(f"{label} kind 与成员目录不匹配")
    _require_relative(item["origin"], f"{label} origin")
    if not _is_lower_sha256(item["sha256"]):
        raise RecoveryPackageError(f"{label} sha256 必须是小写 SHA-256")
    raw_bytes = item["bytes"]
    if not isinstance(raw_bytes, int) or isinstance(raw_bytes, bool) or raw_bytes < 0:
        raise RecoveryPackageError(f"{label} bytes 必须是非负整数")


def _tar_bytes(
    manifest: dict[str, Any],
    entries: Sequence[tuple[_PayloadEntry, bytes]],
) -> bytes:
    buffer = io.BytesIO()
    members: list[tuple[str, bytes]] = [(MANIFEST_MEMBER, canonical_json_bytes(manifest))]
    members.extend((entry.member, data) for entry, data in entries)
    with (
        gzip.GzipFile(filename="", fileobj=buffer, mode="wb", mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar,
    ):
        for name, data in sorted(members):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def build_recovery_package(
    *,
    source_commit: str,
    bundle: Path,
    bundle_manifest: Path,
    materials: Sequence[Path],
    records: Sequence[Path],
    created_at: str | None = None,
) -> tuple[dict[str, Any], bytes]:
    """构建确定性恢复包：同一输入与 created_at 产出逐字节相同结果。"""

    _require_source_commit(source_commit)
    created = created_at if created_at is not None else _now_iso()
    _require_tz_iso(created, "created_at")
    bundle_binding = _binding(bundle, "bundle")
    manifest_binding = _binding(bundle_manifest, "bundle_manifest")

    raw_entries = [
        *[
            (entry, entry.source.read_bytes())
            for entry in _collect_kind("approved_material", materials)
        ],
        *[
            (entry, entry.source.read_bytes())
            for entry in _collect_kind("acceptance_record", records)
        ],
    ]
    entries = sorted(raw_entries, key=lambda pair: pair[0].member)
    if len({entry.member for entry, _ in entries}) != len(entries):
        raise RecoveryPackageError("payload 成员路径不得重复")
    if not any(entry.kind == "approved_material" for entry, _ in entries):
        raise RecoveryPackageError("恢复包必须至少包含一份批准迁移资料")
    if not any(entry.kind == "acceptance_record" for entry, _ in entries):
        raise RecoveryPackageError("恢复包必须至少包含一份本次验收记录")

    payload = [
        {
            "member": entry.member,
            "kind": entry.kind,
            "origin": entry.origin,
            "sha256": _sha256_bytes(data),
            "bytes": len(data),
        }
        for entry, data in entries
    ]
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "package_kind": MANIFEST_KIND,
        "source_commit": source_commit,
        "bundle": bundle_binding,
        "bundle_manifest": manifest_binding,
        "payload": payload,
        "created_at": created,
    }
    manifest = {**body, "manifest_sha256": canonical_digest(body)}
    return manifest, _tar_bytes(manifest, entries)


def _read_package(package_path: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        raw = package_path.read_bytes()
    except OSError as error:
        raise RecoveryPackageError(f"无法读取恢复包：{package_path}") from error
    blobs: dict[str, bytes] = {}
    try:
        with (
            gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as gz,
            tarfile.open(fileobj=gz, mode="r:") as tar,
        ):
            for member in tar.getmembers():
                if member.type != tarfile.REGTYPE:
                    raise RecoveryPackageError(f"恢复包成员不得是非普通文件：{member.name}")
                stream = tar.extractfile(member)
                if stream is None:
                    raise RecoveryPackageError(f"恢复包成员不可读：{member.name}")
                blobs[member.name] = stream.read()
    except RecoveryPackageError:
        raise
    except (OSError, EOFError, tarfile.TarError) as error:
        raise RecoveryPackageError(f"恢复包不可读或已损坏：{error}") from error
    if MANIFEST_MEMBER not in blobs:
        raise RecoveryPackageError(f"恢复包缺少 {MANIFEST_MEMBER}")
    try:
        manifest = json.loads(blobs[MANIFEST_MEMBER].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RecoveryPackageError(f"恢复包清单不可解析：{error}") from error
    if not isinstance(manifest, dict):
        raise RecoveryPackageError("恢复包清单顶层必须是对象")
    return manifest, blobs


def _verified_blobs(
    package_path: Path,
    *,
    expect_source_commit: str | None = None,
    expect_bundle_sha256: str | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    manifest, blobs = _read_package(package_path)
    _require_keys(manifest, MANIFEST_FIELDS, "恢复包清单")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise RecoveryPackageError("恢复包清单 schema_version 必须为 1.0")
    if manifest["package_kind"] != MANIFEST_KIND:
        raise RecoveryPackageError("恢复包清单 package_kind 不匹配")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest["manifest_sha256"] != canonical_digest(body):
        raise RecoveryPackageError("manifest_sha256 不匹配")
    if blobs[MANIFEST_MEMBER] != canonical_json_bytes(manifest):
        raise RecoveryPackageError("清单字节必须是规范 JSON 编码")
    _require_source_commit(manifest["source_commit"])
    _require_tz_iso(manifest["created_at"], "created_at")
    _require_binding(manifest["bundle"], "bundle")
    _require_binding(manifest["bundle_manifest"], "bundle_manifest")

    payload = manifest["payload"]
    if not isinstance(payload, list) or not payload:
        raise RecoveryPackageError("payload 必须是非空列表")
    expected_members = {MANIFEST_MEMBER}
    for index, item in enumerate(payload):
        _require_payload_item(item, index)
        member = item["member"]
        if member in expected_members:
            raise RecoveryPackageError(f"payload 成员路径重复：{member}")
        expected_members.add(member)
        data = blobs.get(member)
        if data is None:
            raise RecoveryPackageError(f"恢复包缺少登记成员：{member}")
        if _sha256_bytes(data) != item["sha256"] or len(data) != item["bytes"]:
            raise RecoveryPackageError(f"恢复包成员摘要不匹配：{member}")
    if set(blobs) != expected_members:
        extra = sorted(set(blobs) - expected_members)
        raise RecoveryPackageError(f"恢复包含未登记成员：{extra}")
    if expect_source_commit is not None and manifest["source_commit"] != expect_source_commit:
        raise RecoveryPackageError("source_commit 与期望绑定不匹配")
    if expect_bundle_sha256 is not None and manifest["bundle"]["sha256"] != expect_bundle_sha256:
        raise RecoveryPackageError("bundle sha256 与期望绑定不匹配")
    return manifest, blobs


def verify_recovery_package(
    package_path: Path,
    *,
    expect_source_commit: str | None = None,
    expect_bundle_sha256: str | None = None,
) -> dict[str, Any]:
    """逐成员核验恢复包；任何漂移、未知成员或绑定不匹配都失败关闭。"""

    manifest, _ = _verified_blobs(
        package_path,
        expect_source_commit=expect_source_commit,
        expect_bundle_sha256=expect_bundle_sha256,
    )
    return manifest


def extract_payload(package_path: Path, destination: Path) -> list[dict[str, Any]]:
    """在一次性空隔离根中恢复 payload，并回读核验逐字节一致。"""

    manifest, blobs = _verified_blobs(package_path)
    if destination.is_symlink() or not destination.is_dir():
        raise RecoveryPackageError(f"恢复目标必须是存在的普通目录：{destination}")
    if any(destination.iterdir()):
        raise RecoveryPackageError("恢复目标目录必须为空（一次性隔离根）")
    base = destination.resolve()
    restored: list[dict[str, Any]] = []
    for item in manifest["payload"]:
        relative = str(item["member"]).removeprefix(PAYLOAD_PREFIX)
        target = destination / relative
        if not target.resolve().is_relative_to(base):
            raise RecoveryPackageError(f"恢复目标逃逸隔离根：{relative}")
        if target.exists() or target.is_symlink():
            raise RecoveryPackageError(f"恢复目标已存在：{relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to(base):
            raise RecoveryPackageError(f"恢复父目录逃逸隔离根：{relative}")
        target.write_bytes(blobs[str(item["member"])])
        if _sha256_bytes(target.read_bytes()) != item["sha256"]:
            raise RecoveryPackageError(f"恢复字节摘要漂移：{relative}")
        restored.append(
            {
                "member": item["member"],
                "sha256": item["sha256"],
                "bytes": item["bytes"],
            }
        )
    return sorted(restored, key=lambda record: record["member"])


def validate_receipt(receipt: dict[str, Any]) -> None:
    """生产者侧严格回执形状检查，与 legacy_cutover 消费端合同一致。"""

    _require_keys(receipt, RECEIPT_FIELDS, "恢复包回执")
    if receipt["schema_version"] != SCHEMA_VERSION:
        raise RecoveryPackageError("恢复包回执 schema_version 必须为 1.0")
    if receipt["receipt_kind"] != RECEIPT_KIND or receipt["status"] != "passed":
        raise RecoveryPackageError("恢复包回执尚未通过")
    if not _is_lower_sha256(receipt["recovery_package_sha256"]):
        raise RecoveryPackageError("恢复包摘要必须是小写 SHA-256")
    _require_tz_iso(receipt["issued_at"], "恢复包回执时间")


def issue_receipt(package_path: Path, *, issued_at: str | None = None) -> dict[str, Any]:
    """仅在整包验证通过后出具恰好五个字段的严格回执。"""

    verify_recovery_package(package_path)
    return {
        "schema_version": SCHEMA_VERSION,
        "receipt_kind": RECEIPT_KIND,
        "status": "passed",
        "recovery_package_sha256": file_digest(package_path),
        "issued_at": issued_at if issued_at is not None else _now_iso(),
    }


def confirm_receipt(package_path: Path, receipt: dict[str, Any]) -> None:
    """恢复演练收口：回执摘要必须绑定当前实际包字节。"""

    validate_receipt(receipt)
    verify_recovery_package(package_path)
    actual = file_digest(package_path)
    if receipt["recovery_package_sha256"] != actual:
        raise RecoveryPackageError("恢复包回执摘要与实际包字节不匹配")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="recovery-package-v1 构建与严格校验（无默认路径）")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--source-commit", required=True)
    build.add_argument("--bundle", type=Path, required=True)
    build.add_argument("--bundle-manifest", type=Path, required=True)
    build.add_argument("--material", type=Path, action="append", default=[])
    build.add_argument("--record", type=Path, action="append", default=[])
    build.add_argument("--created-at")
    build.add_argument("--manifest-out", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("--package", type=Path, required=True)
    verify.add_argument("--expect-source-commit")
    verify.add_argument("--expect-bundle-sha256")
    restore = commands.add_parser("restore")
    restore.add_argument("--package", type=Path, required=True)
    restore.add_argument("--destination", type=Path, required=True)
    receipt = commands.add_parser("receipt")
    receipt.add_argument("--package", type=Path, required=True)
    receipt.add_argument("--output", type=Path, required=True)
    return parser


def _write_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _success_signal(command: str, package_sha256: str, count: int) -> str:
    if command == "build":
        return f"RECOVERY_PACKAGE_OK package_sha256={package_sha256} payload={count}"
    if command == "verify":
        return f"RECOVERY_VERIFY_OK package_sha256={package_sha256} payload={count}"
    if command == "restore":
        return f"RECOVERY_RESTORE_OK files={count}"
    return f"RECOVERY_RECEIPT_OK package_sha256={package_sha256}"


def main(argv: list[str] | None = None) -> Never:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            manifest, package = build_recovery_package(
                source_commit=args.source_commit,
                bundle=args.bundle,
                bundle_manifest=args.bundle_manifest,
                materials=list(args.material),
                records=list(args.record),
                created_at=args.created_at,
            )
            try:
                args.output.write_bytes(package)
            except OSError as error:
                raise RecoveryPackageError(f"无法写出恢复包：{args.output}") from error
            if args.manifest_out is not None:
                _write_object(args.manifest_out, manifest)
            signal = _success_signal("build", _sha256_bytes(package), len(manifest["payload"]))
        elif args.command == "verify":
            manifest = verify_recovery_package(
                args.package,
                expect_source_commit=args.expect_source_commit,
                expect_bundle_sha256=args.expect_bundle_sha256,
            )
            signal = _success_signal("verify", file_digest(args.package), len(manifest["payload"]))
        elif args.command == "restore":
            restored = extract_payload(args.package, args.destination)
            signal = _success_signal("restore", file_digest(args.package), len(restored))
        else:
            receipt = issue_receipt(args.package)
            _write_object(args.output, receipt)
            signal = _success_signal("receipt", receipt["recovery_package_sha256"], 0)
        print(signal)
    except RecoveryPackageError as error:
        print(f"RECOVERY_PACKAGE_FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error
    raise SystemExit(0)


if __name__ == "__main__":
    main()
