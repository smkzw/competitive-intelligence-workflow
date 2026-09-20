from __future__ import annotations

import copy
import gzip
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

from tools.build_recovery_package import (
    MANIFEST_MEMBER,
    PAYLOAD_PREFIX,
    RecoveryPackageError,
    build_recovery_package,
    canonical_digest,
    canonical_json_bytes,
    confirm_receipt,
    extract_payload,
    file_digest,
    issue_receipt,
    validate_receipt,
    verify_recovery_package,
)
from tools.legacy_cutover import (
    CutoverError,
    build_inventory,
    registry_for_legacy_root,
    validate_inventory,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "tools" / "build_recovery_package.py"
MANIFEST_SCHEMA = ROOT / "migration" / "recovery_package.schema.json"
RECEIPT_SCHEMA = ROOT / "migration" / "recovery_package_receipt.schema.json"

CREATED_AT = "2026-09-02T12:00:00+08:00"
SOURCE_COMMIT = "9f2c1a7b" * 5
RECEIPT_FIELDS = {
    "schema_version",
    "receipt_kind",
    "status",
    "recovery_package_sha256",
    "issued_at",
}


def _schema(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _collect_source_bytes(kind: str, roots: list[Path]) -> dict[str, bytes]:
    bucket = "materials" if kind == "approved_material" else "acceptance"
    result: dict[str, bytes] = {}
    for root in roots:
        if root.is_file():
            result[f"{PAYLOAD_PREFIX}{bucket}/{root.name}"] = root.read_bytes()
            continue
        for child in sorted(root.rglob("*")):
            if child.is_file() and not child.is_symlink():
                relative = child.relative_to(root).as_posix()
                result[f"{PAYLOAD_PREFIX}{bucket}/{relative}"] = child.read_bytes()
    return result


def _rc_inputs(tmp_path: Path) -> dict[str, Any]:
    run_dir = tmp_path / "rc-run"
    materials_dir = run_dir / "approved-materials"
    (materials_dir / "policies").mkdir(parents=True)
    (materials_dir / "design-contract.md").write_text("批准设计合同 v1.2\n", encoding="utf-8")
    (materials_dir / "policies" / "gate.yaml").write_text("gate: v1\n", encoding="utf-8")
    records_dir = run_dir / "acceptance-records"
    records_dir.mkdir(parents=True)
    (records_dir / "acceptance.json").write_text('{"run": "rc-final"}\n', encoding="utf-8")
    bundle = run_dir / "final.tar.zst"
    bundle.write_bytes(b"FINAL-BUNDLE-BYTES")
    bundle_manifest = run_dir / "bundle-manifest.json"
    bundle_manifest.write_text('{"files": 3}\n', encoding="utf-8")
    materials = [materials_dir]
    records = [records_dir]
    return {
        "source_commit": SOURCE_COMMIT,
        "bundle": bundle,
        "bundle_manifest": bundle_manifest,
        "materials": materials,
        "records": records,
        "sources": {
            **_collect_source_bytes("approved_material", materials),
            **_collect_source_bytes("acceptance_record", records),
        },
    }


def _build_kwargs(inputs: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "source_commit": inputs["source_commit"],
        "bundle": inputs["bundle"],
        "bundle_manifest": inputs["bundle_manifest"],
        "materials": inputs["materials"],
        "records": inputs["records"],
        "created_at": CREATED_AT,
    }
    kwargs.update(overrides)
    return kwargs


def _build(
    inputs: dict[str, Any],
    tmp_path: Path,
    name: str = "recovery-package.tar.gz",
) -> tuple[Path, dict[str, Any]]:
    manifest, package = build_recovery_package(**_build_kwargs(inputs))
    out = tmp_path / name
    out.write_bytes(package)
    return out, manifest


def _legacy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "consumer.txt").write_text("consumer=fixture\n", encoding="utf-8")
    return root


def _rewrite_package(source: Path, target: Path, mutate: Any) -> None:
    raw = io.BytesIO(source.read_bytes())
    with (
        gzip.GzipFile(filename="", fileobj=raw, mode="rb") as gz,
        tarfile.open(fileobj=gz, mode="r:") as tar,
    ):
        blobs: dict[str, bytes] = {}
        for member in tar.getmembers():
            stream = tar.extractfile(member)
            assert stream is not None
            blobs[member.name] = stream.read()
    blobs = mutate(blobs)
    out = io.BytesIO()
    with (
        gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w") as tar,
    ):
        for name, data in sorted(blobs.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    target.write_bytes(out.getvalue())


def test_build_is_deterministic_and_receipt_binds_into_cutover_chain(
    tmp_path: Path,
) -> None:
    inputs = _rc_inputs(tmp_path)
    first_package, first_manifest = _build(inputs, tmp_path, "first.tar.gz")
    second_package, second_manifest = _build(inputs, tmp_path, "second.tar.gz")
    assert first_package.read_bytes() == second_package.read_bytes()
    assert first_manifest == second_manifest

    Draft202012Validator.check_schema(_schema(MANIFEST_SCHEMA))
    Draft202012Validator.check_schema(_schema(RECEIPT_SCHEMA))
    Draft202012Validator(_schema(MANIFEST_SCHEMA)).validate(first_manifest)
    manifest = verify_recovery_package(first_package)
    assert manifest == first_manifest

    receipt = issue_receipt(first_package)
    Draft202012Validator(_schema(RECEIPT_SCHEMA)).validate(receipt)
    validate_receipt(receipt)
    confirm_receipt(first_package, receipt)

    inventory = build_inventory(registry_for_legacy_root(_legacy_fixture(tmp_path)))
    assert validate_inventory(inventory, receipt)["status"] == "validated"

    with pytest.raises(CutoverError, match="未知字段"):
        validate_inventory(inventory, {**receipt, "note": "extra"})
    with pytest.raises(RecoveryPackageError, match="未知字段"):
        validate_receipt({**receipt, "note": "extra"})


def test_isolated_restore_rehearsal_is_byte_identical(tmp_path: Path) -> None:
    inputs = _rc_inputs(tmp_path)
    package, _ = _build(inputs, tmp_path)
    restore_root = tmp_path / "isolated-restore"
    restore_root.mkdir()

    restored = extract_payload(package, restore_root)
    assert {record["member"] for record in restored} == set(inputs["sources"])
    for member, data in inputs["sources"].items():
        relative = member.removeprefix(PAYLOAD_PREFIX)
        assert (restore_root / relative).read_bytes() == data

    with pytest.raises(RecoveryPackageError, match="必须为空"):
        extract_payload(package, restore_root)

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "stale.txt").write_text("stale\n", encoding="utf-8")
    with pytest.raises(RecoveryPackageError, match="必须为空"):
        extract_payload(package, occupied)


def test_drift_and_binding_negatives_fail_closed(tmp_path: Path) -> None:
    inputs = _rc_inputs(tmp_path)
    package, manifest = _build(inputs, tmp_path)
    receipt = issue_receipt(package)
    member = manifest["payload"][0]["member"]

    appended = tmp_path / "appended.tar.gz"
    appended.write_bytes(package.read_bytes() + b"\x00")
    # 成员级校验只覆盖归档逻辑内容；归档结束后的杂散字节由回执的
    # 整包字节摘要绑定捕获，两层组合保证任何漂移都不被静默接受。
    assert verify_recovery_package(appended) == manifest
    with pytest.raises(RecoveryPackageError, match="与实际包字节不匹配"):
        confirm_receipt(appended, receipt)

    variant_bundle = inputs["bundle"].with_name("final-v2.tar.zst")
    variant_bundle.write_bytes(b"FINAL-BUNDLE-BYTES-V2")
    variant, _ = _build({**inputs, "bundle": variant_bundle}, tmp_path, "variant.tar.gz")
    with pytest.raises(RecoveryPackageError, match="与实际包字节不匹配"):
        confirm_receipt(variant, receipt)

    def flip_byte(blobs: dict[str, bytes]) -> dict[str, bytes]:
        return {name: (b"X" + data[1:] if name == member else data) for name, data in blobs.items()}

    tampered = tmp_path / "tampered.tar.gz"
    _rewrite_package(package, tampered, flip_byte)
    with pytest.raises(RecoveryPackageError, match="摘要不匹配"):
        verify_recovery_package(tampered)

    def inject_member(blobs: dict[str, bytes]) -> dict[str, bytes]:
        mutated = dict(blobs)
        mutated[f"{PAYLOAD_PREFIX}materials/injected.txt"] = b"evil"
        return mutated

    injected = tmp_path / "injected.tar.gz"
    _rewrite_package(package, injected, inject_member)
    with pytest.raises(RecoveryPackageError, match="未登记成员"):
        verify_recovery_package(injected)

    def drop_member(blobs: dict[str, bytes]) -> dict[str, bytes]:
        return {name: data for name, data in blobs.items() if name != member}

    dropped = tmp_path / "dropped.tar.gz"
    _rewrite_package(package, dropped, drop_member)
    with pytest.raises(RecoveryPackageError, match="缺少登记成员"):
        verify_recovery_package(dropped)

    def swap_kind(blobs: dict[str, bytes]) -> dict[str, bytes]:
        loaded = json.loads(blobs[MANIFEST_MEMBER].decode("utf-8"))
        loaded["payload"][0]["kind"] = "runtime_script"
        body = {key: value for key, value in loaded.items() if key != "manifest_sha256"}
        loaded["manifest_sha256"] = canonical_digest(body)
        mutated = dict(blobs)
        mutated[MANIFEST_MEMBER] = canonical_json_bytes(loaded)
        return mutated

    swapped = tmp_path / "swapped.tar.gz"
    _rewrite_package(package, swapped, swap_kind)
    with pytest.raises(RecoveryPackageError, match="kind 未登记"):
        verify_recovery_package(swapped)

    with pytest.raises(RecoveryPackageError, match="source_commit 与期望绑定不匹配"):
        verify_recovery_package(package, expect_source_commit="b" * 40)
    with pytest.raises(RecoveryPackageError, match="bundle sha256 与期望绑定不匹配"):
        verify_recovery_package(package, expect_bundle_sha256="0" * 64)


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"source_commit": "NOT-HEX"}, "十六进制"),
        ({"records": []}, "本次验收记录"),
        ({"materials": []}, "批准迁移资料"),
        ({"created_at": "2026-09-02T12:00:00"}, "必须带时区"),
    ],
)
def test_builder_inputs_fail_closed(tmp_path: Path, override: dict[str, Any], match: str) -> None:
    inputs = _rc_inputs(tmp_path)
    with pytest.raises(RecoveryPackageError, match=match):
        build_recovery_package(**_build_kwargs(inputs, **override))


def test_builder_rejects_missing_or_symlink_inputs(tmp_path: Path) -> None:
    inputs = _rc_inputs(tmp_path)
    with pytest.raises(RecoveryPackageError, match="普通文件"):
        build_recovery_package(**_build_kwargs(inputs, bundle=tmp_path / "absent.tar.zst"))

    real = tmp_path / "real-bundle.tar.zst"
    real.write_bytes(b"x")
    link = tmp_path / "link-bundle.tar.zst"
    link.symlink_to(real)
    with pytest.raises(RecoveryPackageError, match="普通文件"):
        build_recovery_package(**_build_kwargs(inputs, bundle=link))

    materials_dir = tmp_path / "materials-with-link"
    materials_dir.mkdir()
    (materials_dir / "ok.txt").write_text("ok", encoding="utf-8")
    (materials_dir / "bad-link").symlink_to(real)
    with pytest.raises(RecoveryPackageError, match="符号链接"):
        build_recovery_package(**_build_kwargs(inputs, materials=[materials_dir]))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row.update({"unexpected": True}),
        lambda row: row["payload"][0].update({"kind": "runtime_script"}),
        lambda row: row.update(
            {"payload": [item for item in row["payload"] if item["kind"] != "approved_material"]}
        ),
        lambda row: row.update({"source_commit": "9F2C1A7B" * 5}),
    ],
)
def test_manifest_schema_rejects_drift(tmp_path: Path, mutation: Any) -> None:
    _, manifest = _build(_rc_inputs(tmp_path), tmp_path)
    mutated = copy.deepcopy(manifest)
    mutation(mutated)
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema(MANIFEST_SCHEMA)).validate(mutated)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row.update({"unexpected": True}),
        lambda row: row.update({"status": "failed"}),
        lambda row: row.update({"recovery_package_sha256": "A" * 64}),
        lambda row: row.update({"issued_at": "2026-09-02T12:00:00"}),
    ],
)
def test_receipt_schema_rejects_drift(tmp_path: Path, mutation: Any) -> None:
    package, _ = _build(_rc_inputs(tmp_path), tmp_path)
    receipt = issue_receipt(package)
    mutated = copy.deepcopy(receipt)
    mutation(mutated)
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema(RECEIPT_SCHEMA)).validate(mutated)


def test_cli_matches_frozen_argument_contract(tmp_path: Path) -> None:
    inputs = _rc_inputs(tmp_path)
    package = tmp_path / "cli.tar.gz"
    receipt_path = tmp_path / "receipt.json"
    manifest_out = tmp_path / "manifest.json"
    restore_root = tmp_path / "cli-restore"
    restore_root.mkdir()

    build_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "build",
            "--output",
            str(package),
            "--source-commit",
            inputs["source_commit"],
            "--bundle",
            str(inputs["bundle"]),
            "--bundle-manifest",
            str(inputs["bundle_manifest"]),
            "--material",
            str(inputs["materials"][0]),
            "--record",
            str(inputs["records"][0]),
            "--created-at",
            CREATED_AT,
            "--manifest-out",
            str(manifest_out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_run.returncode == 0, build_run.stderr
    assert "RECOVERY_PACKAGE_OK" in build_run.stdout

    verify_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "verify",
            "--package",
            str(package),
            "--expect-source-commit",
            inputs["source_commit"],
            "--expect-bundle-sha256",
            file_digest(inputs["bundle"]),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify_run.returncode == 0, verify_run.stderr
    assert "RECOVERY_VERIFY_OK" in verify_run.stdout

    receipt_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "receipt",
            "--package",
            str(package),
            "--output",
            str(receipt_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert receipt_run.returncode == 0, receipt_run.stderr
    assert "RECOVERY_RECEIPT_OK" in receipt_run.stdout
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert set(receipt) == RECEIPT_FIELDS
    Draft202012Validator(_schema(RECEIPT_SCHEMA)).validate(receipt)

    restore_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "restore",
            "--package",
            str(package),
            "--destination",
            str(restore_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert restore_run.returncode == 0, restore_run.stderr
    assert "RECOVERY_RESTORE_OK" in restore_run.stdout

    failed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "verify",
            "--package",
            str(package),
            "--expect-source-commit",
            "b" * 40,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 1
    assert "RECOVERY_PACKAGE_FAIL" in failed.stderr
    assert "source_commit 与期望绑定不匹配" in failed.stderr
