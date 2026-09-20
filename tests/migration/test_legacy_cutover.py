from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.legacy_cutover import (
    CutoverError,
    absence_check,
    apply_cutover,
    authorization_digest,
    build_inventory,
    canonical_digest,
    registry_for_legacy_root,
    validate_cutover,
    validate_inventory,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "tools" / "legacy_cutover.py"


def _registry(root: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "approved_roots": [str(root)],
        "entries": [
            {
                "entry_id": "consumer-ref",
                "kind": "consumer_reference",
                "path": str(root / "consumer.txt"),
                "action": "delete",
                "hash_mode": "content",
            },
            {
                "entry_id": "legacy-link",
                "kind": "symlink",
                "path": str(root / "legacy-link"),
                "action": "delete",
                "hash_mode": "metadata",
            },
            {
                "entry_id": "legacy-root",
                "kind": "legacy_root",
                "path": str(root),
                "action": "delete",
                "hash_mode": "content",
            },
            {
                "entry_id": "runtime-file",
                "kind": "launcher",
                "path": str(root / "launcher.sh"),
                "action": "delete",
                "hash_mode": "content",
            },
        ],
    }


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "consumer.txt").write_text("consumer=legacy\n", encoding="utf-8")
    (root / "launcher.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (root / "legacy-link").symlink_to(tmp_path / "outside")
    return root, _registry(root)


def _tree_state(root: Path) -> list[tuple[str, str, bytes | str]]:
    state: list[tuple[str, str, bytes | str]] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.is_symlink():
            state.append((path.name, "symlink", path.readlink().as_posix()))
        else:
            state.append((path.name, "file", path.read_bytes()))
    return state


def _authorization(
    inventory: dict[str, Any], recovery: dict[str, Any]
) -> dict[str, Any]:
    preauthorization = validate_inventory(inventory, recovery)
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "authorization_kind": "exact-legacy-cutover-authorization-v1",
        "inventory_sha256": inventory["inventory_sha256"],
        "registry_sha256": inventory["registry_sha256"],
        "recovery_receipt_sha256": canonical_digest(recovery),
        "preauthorization_validation_sha256": preauthorization["validation_sha256"],
        "actions": [
            {"entry_id": entry["entry_id"], "action": entry["action"]}
            for entry in inventory["entries"]
        ],
    }
    payload["authorization_sha256"] = authorization_digest(payload)
    return payload


def _recovery() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "receipt_kind": "recovery-package-v1",
        "status": "passed",
        "recovery_package_sha256": "a" * 64,
        "issued_at": "2026-09-02T10:00:00+08:00",
    }


def test_inventory_is_exact_and_dry_run_is_non_mutating(tmp_path: Path) -> None:
    root, registry = _fixture(tmp_path)
    before = _tree_state(root)

    first = build_inventory(registry)
    second = build_inventory(registry)

    assert first == second
    assert _tree_state(root) == before
    assert [entry["entry_id"] for entry in first["entries"]] == sorted(
        entry["entry_id"] for entry in registry["entries"]
    )
    assert all(
        {
            "path",
            "realpath",
            "device",
            "inode",
            "node_type",
            "sha256",
            "action",
        }
        <= entry.keys()
        for entry in first["entries"]
    )


def test_legacy_root_shortcut_never_reads_unknown_file_content(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path)
    registry = registry_for_legacy_root(root)
    assert {entry["hash_mode"] for entry in registry["entries"]} == {"metadata"}


def test_validate_rejects_path_escape_symlink_follow_and_inode_drift(
    tmp_path: Path,
) -> None:
    root, registry = _fixture(tmp_path)
    escaped = copy.deepcopy(registry)
    escaped["entries"][0]["path"] = str(tmp_path / "outside.txt")
    with pytest.raises(CutoverError, match="越出批准根"):
        build_inventory(escaped)

    real_root = tmp_path / "real-root"
    real_root.mkdir()
    (real_root / "item").write_text("x", encoding="utf-8")
    alias = tmp_path / "alias-root"
    alias.symlink_to(real_root, target_is_directory=True)
    through_link = {
        "schema_version": "1.0",
        "approved_roots": [str(alias)],
        "entries": [
            {
                "entry_id": "linked-root-item",
                "kind": "legacy_root",
                "path": str(alias / "item"),
                "action": "delete",
                "hash_mode": "content",
            }
        ],
    }
    with pytest.raises(CutoverError, match="批准根不得是符号链接"):
        build_inventory(through_link)

    inventory = build_inventory(registry)
    recovery = _recovery()
    authorization = _authorization(inventory, recovery)
    launcher = root / "launcher.sh"
    launcher.unlink()
    launcher.write_text("replacement\n", encoding="utf-8")
    with pytest.raises(CutoverError, match="漂移"):
        validate_cutover(inventory, authorization, recovery)


def test_apply_requires_matching_authorization_manifest_hash_and_is_idempotent(
    tmp_path: Path,
) -> None:
    root, registry = _fixture(tmp_path)
    inventory = build_inventory(registry)
    recovery = _recovery()
    authorization = _authorization(inventory, recovery)
    validation = validate_cutover(inventory, authorization, recovery)

    wrong = copy.deepcopy(authorization)
    wrong["inventory_sha256"] = "0" * 64
    with pytest.raises(CutoverError, match="authorization_sha256"):
        apply_cutover(inventory, wrong, validation)

    first = apply_cutover(inventory, authorization, validation)
    second = apply_cutover(inventory, authorization, validation)
    assert first["status"] == second["status"] == "applied"
    assert not root.exists()
    assert {item["result"] for item in second["outcomes"]} == {"already_absent"}


def test_absence_check_fails_on_any_registered_legacy_runtime_or_reference(
    tmp_path: Path,
) -> None:
    _, registry = _fixture(tmp_path)
    inventory = build_inventory(registry)
    recovery = _recovery()
    authorization = _authorization(inventory, recovery)
    validation = validate_cutover(inventory, authorization, recovery)

    with pytest.raises(CutoverError, match="仍存在"):
        absence_check(inventory)
    apply_cutover(inventory, authorization, validation)
    assert absence_check(inventory)["status"] == "absent"


def test_absence_check_does_not_treat_retain_as_absent(tmp_path: Path) -> None:
    _, registry = _fixture(tmp_path)
    for entry in registry["entries"]:
        entry["action"] = "retain"
    inventory = build_inventory(registry)
    with pytest.raises(CutoverError, match="consumer-ref"):
        absence_check(inventory)


def test_cli_matches_frozen_task_107_and_108_argument_contract(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path)
    manifest = tmp_path / "cutover-dry-run.json"
    recovery_path = tmp_path / "recovery.json"
    authorization_path = tmp_path / "authorization.json"
    apply_receipt = tmp_path / "apply-receipt.json"
    recovery = _recovery()
    recovery_path.write_text(json.dumps(recovery), encoding="utf-8")

    inventory_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "inventory",
            "--legacy-root",
            str(root),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert inventory_run.returncode == 0, inventory_run.stderr
    assert "CUTOVER_INVENTORY_OK mutated=0" in inventory_run.stdout
    inventory = json.loads(manifest.read_text(encoding="utf-8"))

    validate_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "validate",
            "--manifest",
            str(manifest),
            "--legacy-root",
            str(root),
            "--recovery-receipt",
            str(recovery_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate_run.returncode == 0, validate_run.stderr
    assert "CUTOVER_VALIDATE_OK escapes=0 recovery=passed" in validate_run.stdout
    assert "content_mode=metadata_only" in validate_run.stdout

    authorization = _authorization(inventory, recovery)
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    apply_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "apply",
            "--manifest",
            str(manifest),
            "--authorization",
            str(authorization_path),
            "--receipt",
            str(apply_receipt),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert apply_run.returncode == 0, apply_run.stderr
    assert "CUTOVER_APPLY_OK" in apply_run.stdout
    assert not root.exists()

    absence_run = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "absence-check",
            "--manifest",
            str(manifest),
            "--scan-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert absence_run.returncode == 0, absence_run.stderr
    assert "LEGACY_ABSENCE_OK" in absence_run.stdout


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda row: row.update(status="failed"), "尚未通过"),
        (lambda row: row.update(recovery_package_sha256="not-a-digest"), "小写 SHA-256"),
        (lambda row: row.update(issued_at="2026-09-02T10:00:00"), "必须带时区"),
        (lambda row: row.update(unexpected=True), "未知字段"),
    ],
)
def test_recovery_receipt_gate_fails_closed(
    tmp_path: Path, mutation: Any, match: str
) -> None:
    _, registry = _fixture(tmp_path)
    inventory = build_inventory(registry)
    recovery = _recovery()
    mutation(recovery)
    with pytest.raises(CutoverError, match=match):
        validate_inventory(inventory, recovery)


def test_registry_rejects_empty_observation_kind_drift_and_delete_parent_retain_child(
    tmp_path: Path,
) -> None:
    absent_root = tmp_path / "absent"
    absent = {
        "schema_version": "1.0",
        "approved_roots": [str(absent_root)],
        "entries": [
            {
                "entry_id": "absent-item",
                "kind": "consumer_reference",
                "path": str(absent_root / "missing"),
                "action": "delete",
                "hash_mode": "content",
            }
        ],
    }
    with pytest.raises(CutoverError, match="至少必须观察到一个"):
        build_inventory(absent)

    root, registry = _fixture(tmp_path)
    wrong_kind = copy.deepcopy(registry)
    link = next(entry for entry in wrong_kind["entries"] if entry["kind"] == "symlink")
    link["kind"] = "consumer_reference"
    with pytest.raises(CutoverError, match="kind 与符号链接观测不一致"):
        build_inventory(wrong_kind)

    conflict = copy.deepcopy(registry)
    child = next(entry for entry in conflict["entries"] if entry["entry_id"] == "consumer-ref")
    child["action"] = "retain"
    with pytest.raises(CutoverError, match="删除父路径同时保留子项"):
        build_inventory(conflict)


def test_partial_apply_is_fail_closed_and_same_authorization_resumes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "partial"
    root.mkdir()
    registered = root / "registered.txt"
    registered.write_text("registered\n", encoding="utf-8")
    blocker = root / "unregistered.txt"
    blocker.write_text("blocker\n", encoding="utf-8")
    registry = {
        "schema_version": "1.0",
        "approved_roots": [str(root)],
        "entries": [
            {
                "entry_id": "partial-root",
                "kind": "legacy_root",
                "path": str(root),
                "action": "delete",
                "hash_mode": "metadata",
            },
            {
                "entry_id": "registered-file",
                "kind": "consumer_reference",
                "path": str(registered),
                "action": "delete",
                "hash_mode": "content",
            },
        ],
    }
    inventory = build_inventory(registry)
    recovery = _recovery()
    authorization = _authorization(inventory, recovery)
    validation = validate_cutover(inventory, authorization, recovery)

    with pytest.raises(CutoverError, match="幂等重放"):
        apply_cutover(inventory, authorization, validation)
    assert not registered.exists()
    assert blocker.exists()
    blocker.unlink()
    resumed = apply_cutover(inventory, authorization, validation)
    assert not root.exists()
    assert {item["result"] for item in resumed["outcomes"]} == {
        "already_absent",
        "deleted",
    }
