#!/usr/bin/env python3
"""验证 required-v12 发布案例是否在声明 owner 阶段真实闭合。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Never, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from ci_workflow.application.acceptance_catalog import (
    compute_case_digest,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "release-case-receipt.schema.json"
CATALOG_SCHEMA = ROOT / "schemas" / "acceptance-catalog.schema.json"
PRE_RC_RECEIPT_SCHEMA = "schemas/host-receipt.schema.json"


class ReceiptClosureError(ValueError):
    """回执缺失、漂移或未在 owner 阶段闭合。"""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def receipt_digest(receipt: dict[str, Any]) -> str:
    body = {key: value for key, value in receipt.items() if key != "receipt_digest"}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def case_input_digest(case: dict[str, Any]) -> str:
    raw_inputs = case.get("inputs")
    if not isinstance(raw_inputs, list):
        raise ReceiptClosureError(f"catalog 案例 inputs 无效：{case.get('id')}")
    inputs = sorted(raw_inputs, key=lambda item: str(item.get("path", "")))
    return hashlib.sha256(canonical_json_bytes(inputs)).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReceiptClosureError(f"无法读取{label}：{path}") from error
    if not isinstance(payload, dict):
        raise ReceiptClosureError(f"{label}顶层必须是对象：{path}")
    return payload


def _load_catalog(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ReceiptClosureError(f"无法读取验收 catalog：{path}") from error
    if not isinstance(payload, dict):
        raise ReceiptClosureError("验收 catalog 顶层必须是对象")
    return cast(dict[str, Any], payload)


def _safe_receipt_path(root: Path, relative: str, case_id: str) -> Path:
    if root.is_symlink():
        raise ReceiptClosureError("receipts root 不得是符号链接")
    try:
        root_real = root.resolve(strict=True)
    except FileNotFoundError as error:
        raise ReceiptClosureError("receipts root 不存在") from error
    candidate = root / relative
    if candidate.is_symlink():
        raise ReceiptClosureError(f"release receipt 不得是符号链接：{case_id}")
    try:
        candidate.resolve(strict=True).relative_to(root_real)
    except (FileNotFoundError, ValueError) as error:
        raise ReceiptClosureError(f"release receipt 越出证据根或不存在：{case_id}") from error
    current = root
    for part in Path(relative).parts[:-1]:
        current /= part
        if current.is_symlink():
            raise ReceiptClosureError(f"release receipt 祖先不得是符号链接：{case_id}")
    return candidate


def verify_required_receipts(
    *,
    catalog_path: Path,
    receipts_root: Path,
    package_manifest_path: Path,
    release_candidate_sha256: str,
    project_contract_path: Path,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    if len(release_candidate_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in release_candidate_sha256
    ):
        raise ReceiptClosureError("release candidate 摘要必须是小写 SHA-256")
    catalog = _load_catalog(catalog_path)
    schema = _load_json(schema_path, "release receipt schema")
    catalog_schema = _load_json(CATALOG_SCHEMA, "acceptance catalog schema")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator.check_schema(catalog_schema)
    catalog_errors = sorted(
        Draft202012Validator(
            catalog_schema, format_checker=FormatChecker()
        ).iter_errors(catalog),
        key=lambda error: list(error.path),
    )
    if catalog_errors:
        raise ReceiptClosureError(f"acceptance catalog schema 失败：{catalog_errors[0].message}")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    catalog_sha256 = sha256_file(catalog_path)
    package_sha256 = sha256_file(package_manifest_path)
    project_contract_sha256 = sha256_file(project_contract_path)
    release_scope = catalog.get("release_scope")
    raw_cases = catalog.get("cases")
    if release_scope != "site_html_v1" or not isinstance(raw_cases, list):
        raise ReceiptClosureError("catalog release_scope/cases 合同无效")

    required_cases = [
        case
        for case in raw_cases
        if isinstance(case, dict) and case.get("family") == "required-v12"
    ]
    if not required_cases:
        raise ReceiptClosureError("catalog 没有 required-v12 案例")
    case_ids = [case.get("id") for case in required_cases]
    if len(case_ids) != len(set(case_ids)):
        raise ReceiptClosureError("required-v12 case id 重复")

    closed: list[str] = []
    not_applicable: list[str] = []
    for case in required_cases:
        case_id = case.get("id")
        owner_task = case.get("owner_task")
        declared_digest = case.get("case_digest")
        receipt_contract = case.get("receipt")
        if not isinstance(case_id, str) or not isinstance(owner_task, str):
            raise ReceiptClosureError("required-v12 案例缺少 id/owner_task")
        if declared_digest != compute_case_digest(case):
            raise ReceiptClosureError(f"catalog case_digest 漂移：{case_id}")
        if not isinstance(receipt_contract, dict):
            raise ReceiptClosureError(f"catalog 案例缺少 receipt：{case_id}")
        if receipt_contract.get("schema") != PRE_RC_RECEIPT_SCHEMA:
            raise ReceiptClosureError(f"catalog pre-RC receipt schema 漂移：{case_id}")
        receipt_path = _safe_receipt_path(receipts_root, f"{case_id}.json", case_id)
        receipt = _load_json(receipt_path, f"release receipt {case_id}")
        errors = sorted(validator.iter_errors(receipt), key=lambda error: list(error.path))
        if errors:
            raise ReceiptClosureError(f"release receipt schema 失败 {case_id}：{errors[0].message}")
        if receipt["receipt_digest"] != receipt_digest(receipt):
            raise ReceiptClosureError(f"release receipt 摘要不匹配：{case_id}")
        bindings = {
            "case_id": case_id,
            "release_scope": release_scope,
            "owner_task": owner_task,
            "catalog_sha256": catalog_sha256,
            "case_digest": declared_digest,
            "package_manifest_sha256": package_sha256,
            "release_candidate_sha256": release_candidate_sha256,
        }
        for field, expected in bindings.items():
            if receipt[field] != expected:
                raise ReceiptClosureError(f"release receipt {field} 漂移：{case_id}")
        if receipt["input_sha256"] != case_input_digest(case):
            raise ReceiptClosureError(f"release receipt input_sha256 漂移：{case_id}")

        optional = case.get("execution_scope") == "conditional-extension" and isinstance(
            case.get("not_applicable"), str
        )
        catalog_owner_status = receipt_contract.get("owner_status")
        if receipt["status"] == "not_applicable":
            if not optional:
                raise ReceiptClosureError(f"只有可选适配器可 not_applicable：{case_id}")
            if catalog_owner_status != "not_applicable":
                raise ReceiptClosureError(f"catalog 未声明 not_applicable：{case_id}")
            if receipt["project_contract_sha256"] != project_contract_sha256:
                raise ReceiptClosureError(f"not_applicable 未绑定项目合同：{case_id}")
            if receipt["not_applicable_reason_zh"] != case["not_applicable"]:
                raise ReceiptClosureError(f"not_applicable 原因与 catalog 不一致：{case_id}")
            not_applicable.append(case_id)
            continue
        if catalog_owner_status not in {"pending_future_owner", "current_owner", "verified"}:
            raise ReceiptClosureError(f"catalog owner_status 不允许 owner-stage 闭合：{case_id}")
        if receipt["status"] != "accepted":
            raise ReceiptClosureError(
                f"required-v12 案例未在 owner 阶段 accepted：{case_id}={receipt['status']}"
            )
        closed.append(case_id)

    return {
        "status": "closed",
        "release_scope": release_scope,
        "catalog_sha256": catalog_sha256,
        "package_manifest_sha256": package_sha256,
        "release_candidate_sha256": release_candidate_sha256,
        "accepted_case_ids": sorted(closed),
        "not_applicable_case_ids": sorted(not_applicable),
        "required_case_count": len(required_cases),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="required-v12 发布回执闭环验证")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--receipts-root", type=Path, required=True)
    parser.add_argument("--package-manifest", type=Path, required=True)
    parser.add_argument("--release-candidate-sha256", required=True)
    parser.add_argument("--project-contract", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    return parser


def main(argv: list[str] | None = None) -> Never:
    args = _parser().parse_args(argv)
    try:
        result = verify_required_receipts(
            catalog_path=args.catalog,
            receipts_root=args.receipts_root,
            package_manifest_path=args.package_manifest,
            release_candidate_sha256=args.release_candidate_sha256,
            project_contract_path=args.project_contract,
            schema_path=args.schema,
        )
    except (ReceiptClosureError, OSError) as error:
        print(f"RELEASE_RECEIPTS_FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
