from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator

from ci_workflow.application.acceptance_catalog import (  # type: ignore[import-untyped]
    compute_case_digest,
)
from tools.verify_release_receipts import (
    ReceiptClosureError,
    case_input_digest,
    receipt_digest,
    sha256_file,
    verify_required_receipts,
)

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "fixtures" / "acceptance" / "catalog.yaml"
SCHEMA = ROOT / "schemas" / "release-case-receipt.schema.json"
RC_SHA256 = "c" * 64


def _load_catalog() -> dict[str, Any]:
    payload = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def _sha(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _setup_receipts(tmp_path: Path) -> tuple[dict[str, Any], Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    catalog = _load_catalog()
    package_manifest = tmp_path / "package-manifest.json"
    package_manifest.write_text('{"package":"fixture"}\n', encoding="utf-8")
    project_contract = tmp_path / "project-contract.json"
    project_contract.write_text('{"optional_adapters":[]}\n', encoding="utf-8")
    catalog_sha = sha256_file(CATALOG)
    package_sha = sha256_file(package_manifest)
    contract_sha = sha256_file(project_contract)

    for raw_case in catalog["cases"]:
        if not isinstance(raw_case, dict) or raw_case.get("family") != "required-v12":
            continue
        case = cast(dict[str, Any], raw_case)
        optional = case.get("execution_scope") == "conditional-extension"
        status = "not_applicable" if optional else "accepted"
        receipt: dict[str, Any] = {
            "schema_version": "1.0",
            "receipt_kind": "release-case-v1",
            "case_id": case["id"],
            "release_scope": catalog["release_scope"],
            "status": status,
            "owner_task": case["owner_task"],
            "catalog_sha256": catalog_sha,
            "case_digest": case["case_digest"],
            "package_manifest_sha256": package_sha,
            "release_candidate_sha256": RC_SHA256,
            "run_id": f"run-{case['id']}",
            "session_id": f"session-{case['id']}",
            "input_sha256": case_input_digest(case),
            "artifact_sha256": None if optional else _sha({"artifact": case["id"]}),
            "verdict_sha256": _sha({"status": status, "case": case["id"]}),
            "project_contract_sha256": contract_sha if optional else None,
            "not_applicable_reason_zh": case.get("not_applicable") if optional else None,
            "issued_at": "2026-09-02T10:00:00+08:00",
        }
        receipt["receipt_digest"] = receipt_digest(receipt)
        path = tmp_path / f"{case['id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return catalog, package_manifest, project_contract, tmp_path


def _verify(tmp_path: Path) -> dict[str, Any]:
    _, package, contract, receipts_root = _setup_receipts(tmp_path)
    return verify_required_receipts(
        catalog_path=CATALOG,
        receipts_root=receipts_root,
        package_manifest_path=package,
        release_candidate_sha256=RC_SHA256,
        project_contract_path=contract,
    )


def _receipt_path(root: Path, catalog: dict[str, Any], case_id: str) -> Path:
    assert any(case["id"] == case_id for case in catalog["cases"])
    return root / f"{case_id}.json"


def _mutate_receipt(path: Path, mutate: Any) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    payload["receipt_digest"] = receipt_digest(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _catalog_with_owner_status(
    tmp_path: Path,
    catalog: dict[str, Any],
    receipts_root: Path,
    case_id: str,
    owner_status: str,
) -> Path:
    target = next(case for case in catalog["cases"] if case["id"] == case_id)
    target["receipt"]["owner_status"] = owner_status
    target["case_digest"] = compute_case_digest(target)
    catalog_path = tmp_path / "catalog-owner-status.yaml"
    catalog_path.write_text(
        yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    catalog_sha = sha256_file(catalog_path)
    for case in catalog["cases"]:
        if case.get("family") != "required-v12":
            continue
        path = receipts_root / f"{case['id']}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["catalog_sha256"] = catalog_sha
        payload["case_digest"] = case["case_digest"]
        payload["receipt_digest"] = receipt_digest(payload)
        path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return catalog_path


def test_release_case_receipt_schema_is_strict_and_status_sensitive() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    base = {
        "schema_version": "1.0",
        "receipt_kind": "release-case-v1",
        "case_id": "case-a",
        "release_scope": "site_html_v1",
        "status": "accepted",
        "owner_task": "phase-10-task-106-rc-freeze",
        "catalog_sha256": "a" * 64,
        "case_digest": "b" * 64,
        "package_manifest_sha256": "c" * 64,
        "release_candidate_sha256": "d" * 64,
        "run_id": "run-a",
        "session_id": "session-a",
        "input_sha256": "e" * 64,
        "artifact_sha256": "f" * 64,
        "verdict_sha256": "1" * 64,
        "project_contract_sha256": None,
        "not_applicable_reason_zh": None,
        "issued_at": "2026-09-02T10:00:00+08:00",
        "receipt_digest": "2" * 64,
    }
    validator.validate(base)
    extra = {**base, "unexpected": True}
    assert list(validator.iter_errors(extra))
    missing_artifact = {**base, "artifact_sha256": None}
    assert list(validator.iter_errors(missing_artifact))


def test_every_applicable_required_v12_case_closes_at_declared_owner_stage(
    tmp_path: Path,
) -> None:
    result = _verify(tmp_path)
    catalog = _load_catalog()
    required = [case for case in catalog["cases"] if case["family"] == "required-v12"]
    assert result["status"] == "closed"
    assert result["required_case_count"] == len(required)
    assert result["not_applicable_case_ids"] == ["optional-adapter-recovery"]
    assert "legacy-absence" in result["accepted_case_ids"]


def test_pending_future_owner_never_counts_as_accepted(tmp_path: Path) -> None:
    catalog, package, contract, root = _setup_receipts(tmp_path)
    path = _receipt_path(root, catalog, "legacy-absence")
    _mutate_receipt(path, lambda receipt: receipt.update(status="pending_future_owner"))
    with pytest.raises(ReceiptClosureError, match="未在 owner 阶段 accepted"):
        verify_required_receipts(
            catalog_path=CATALOG,
            receipts_root=root,
            package_manifest_path=package,
            release_candidate_sha256=RC_SHA256,
            project_contract_path=contract,
        )


@pytest.mark.parametrize(
    ("case_id", "owner_status", "match"),
    [
        ("legacy-absence", "not_applicable", "不允许 owner-stage 闭合"),
        ("optional-adapter-recovery", "current_owner", "未声明 not_applicable"),
    ],
)
def test_catalog_owner_status_gate_rejects_incompatible_release_receipt(
    tmp_path: Path, case_id: str, owner_status: str, match: str
) -> None:
    catalog, package, contract, root = _setup_receipts(tmp_path)
    catalog_path = _catalog_with_owner_status(
        tmp_path, catalog, root, case_id, owner_status
    )
    with pytest.raises(ReceiptClosureError, match=match):
        verify_required_receipts(
            catalog_path=catalog_path,
            receipts_root=root,
            package_manifest_path=package,
            release_candidate_sha256=RC_SHA256,
            project_contract_path=contract,
        )


@pytest.mark.parametrize(
    ("case_id", "mutation", "match"),
    [
        ("legacy-absence", lambda row: row.update(owner_task="wrong-owner"), "owner_task 漂移"),
        (
            "legacy-absence",
            lambda row: row.update(input_sha256="0" * 64),
            "input_sha256 漂移",
        ),
        (
            "legacy-absence",
            lambda row: row.update(
                status="not_applicable",
                artifact_sha256=None,
                project_contract_sha256="a" * 64,
                not_applicable_reason_zh="不适用",
            ),
            "只有可选适配器",
        ),
        (
            "optional-adapter-recovery",
            lambda row: row.update(project_contract_sha256="0" * 64),
            "未绑定项目合同",
        ),
        (
            "optional-adapter-recovery",
            lambda row: row.update(not_applicable_reason_zh="任意理由"),
            "原因与 catalog 不一致",
        ),
    ],
)
def test_closure_rejects_owner_drift_or_invalid_not_applicable(
    tmp_path: Path, case_id: str, mutation: Any, match: str
) -> None:
    catalog, package, contract, root = _setup_receipts(tmp_path)
    path = _receipt_path(root, catalog, case_id)
    _mutate_receipt(path, mutation)
    with pytest.raises(ReceiptClosureError, match=match):
        verify_required_receipts(
            catalog_path=CATALOG,
            receipts_root=root,
            package_manifest_path=package,
            release_candidate_sha256=RC_SHA256,
            project_contract_path=contract,
        )


def test_closure_rejects_package_or_receipt_digest_drift(tmp_path: Path) -> None:
    catalog, package, contract, root = _setup_receipts(tmp_path)
    package.write_text('{"package":"drifted"}\n', encoding="utf-8")
    with pytest.raises(ReceiptClosureError, match="package_manifest_sha256 漂移"):
        verify_required_receipts(
            catalog_path=CATALOG,
            receipts_root=root,
            package_manifest_path=package,
            release_candidate_sha256=RC_SHA256,
            project_contract_path=contract,
        )

    _, package, contract, root = _setup_receipts(tmp_path / "digest")
    path = _receipt_path(root, catalog, "legacy-absence")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["receipt_digest"] = "0" * 64
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ReceiptClosureError, match="摘要不匹配"):
        verify_required_receipts(
            catalog_path=CATALOG,
            receipts_root=root,
            package_manifest_path=package,
            release_candidate_sha256=RC_SHA256,
            project_contract_path=contract,
        )


def test_closure_never_follows_receipt_symlink(tmp_path: Path) -> None:
    catalog, package, contract, root = _setup_receipts(tmp_path)
    path = _receipt_path(root, catalog, "legacy-absence")
    outside = tmp_path / "outside-receipt.json"
    path.replace(outside)
    path.symlink_to(outside)
    with pytest.raises(ReceiptClosureError, match="不得是符号链接"):
        verify_required_receipts(
            catalog_path=CATALOG,
            receipts_root=root,
            package_manifest_path=package,
            release_candidate_sha256=RC_SHA256,
            project_contract_path=contract,
        )
