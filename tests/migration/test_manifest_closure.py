from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "migration" / "legacy_manifest.jsonl"
SCHEMA = ROOT / "migration" / "legacy_manifest.schema.json"

APPROVED_MIGRATED_ITEMS = {
    "approved-design-spec-v1-2",
    "decision-ledger-d01-d70",
    "kangzhe-core-design-contract",
    "kangzhe-site-design-contract",
    "kangzhe-verified-logo",
    "legacy-fixture-five-products-zero-trials",
    "legacy-fixture-style-collapse",
    "legacy-fixture-false-green-qc",
    "legacy-fixture-unanchored-ad-shell",
    "legacy-negative-regression-assertions",
}
REQUIRED_EXCLUSION_CATEGORIES = {
    "legacy_code",
    "legacy_schema",
    "legacy_template",
    "legacy_qc",
    "legacy_document",
    "global_fact_base",
    "session_state",
    "cache_state",
    "plaintext_credentials",
    "absolute_path_dependency",
    "compatibility_wrapper",
}
SENSITIVE_CATEGORIES = {"session_state", "cache_state", "plaintext_credentials"}
SENSITIVE_SENTINEL_MARKERS = {
    "session_state": "legacy-sensitive-session-and-cache-content-not-read-v1",
    "cache_state": "legacy-sensitive-session-and-cache-content-not-read-v1",
    "plaintext_credentials": "legacy-sensitive-config-content-not-read-v1",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema() -> dict[str, Any]:
    value = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return value


def _records() -> list[dict[str, Any]]:
    lines = [line for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line]
    assert lines, "迁移清单不得为空"
    return [json.loads(line) for line in lines]


def _repository_target(relative: str) -> Path:
    target = (ROOT / relative).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError as error:
        raise AssertionError(f"迁移目标逃逸仓库：{relative}") from error
    return target


def test_manifest_schema_ids_and_approved_migration_set_are_closed() -> None:
    validator = Draft202012Validator(_schema())
    records = _records()
    for record in records:
        validator.validate(record)
        assert Path(record["old_path"]).is_absolute()
        assert Path(record["old_realpath"]).is_absolute()

    item_ids = [record["item_id"] for record in records]
    assert len(item_ids) == len(set(item_ids)), "迁移登记项标识不得重复"
    migrated = {
        record["item_id"]
        for record in records
        if record["final_disposition"] == "migrated"
    }
    assert migrated == APPROVED_MIGRATED_ITEMS
    assert all(record["runtime_dependency"] is False for record in records)


def test_migrated_targets_are_inside_repository_and_match_recorded_digest() -> None:
    targets: list[Path] = []
    for record in _records():
        if record["final_disposition"] != "migrated":
            continue
        target = _repository_target(record["new_path"])
        assert target.is_file(), f"已迁移目标不存在：{record['new_path']}"
        assert not target.is_symlink(), f"已迁移目标不得是符号链接：{record['new_path']}"
        assert _sha256(target) == record["target_sha256"], record["item_id"]
        targets.append(target)
    assert len(targets) == len(set(targets)), "多个迁移项不得覆盖同一目标"


def test_required_exclusion_categories_are_closed() -> None:
    excluded = [
        record
        for record in _records()
        if record["final_disposition"] == "not_migrated"
    ]
    assert {record["category"] for record in excluded} >= REQUIRED_EXCLUSION_CATEGORIES
    for record in excluded:
        assert record["new_path"] is None
        assert record["target_sha256"] is None
        assert record["transformation"] == "none"


def test_sensitive_classes_use_only_redacted_sentinel_digests() -> None:
    sensitive = [
        record for record in _records() if record["category"] in SENSITIVE_CATEGORIES
    ]
    assert {record["category"] for record in sensitive} == SENSITIVE_CATEGORIES
    for record in sensitive:
        assert record["item_type"] == "sensitive_class"
        assert record["hash_basis"] == "redacted_sentinel"
        assert record["final_disposition"] == "not_migrated"
        marker = SENSITIVE_SENTINEL_MARKERS[record["category"]]
        assert record["source_sha256"] == hashlib.sha256(marker.encode()).hexdigest()
        assert "未读取" in record["redaction"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row.update({"unexpected": True}),
        lambda row: row.update({"runtime_dependency": True}),
        lambda row: row.update({"new_path": None, "target_sha256": None}),
    ],
)
def test_schema_rejects_unknown_runtime_or_incomplete_migrated_records(
    mutation: Any,
) -> None:
    record = copy.deepcopy(_records()[0])
    mutation(record)
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(record)


def test_schema_rejects_target_on_excluded_item_and_sensitive_file_digest() -> None:
    validator = Draft202012Validator(_schema())
    excluded = next(
        record
        for record in _records()
        if record["final_disposition"] == "not_migrated"
    )
    excluded["new_path"] = "src/forbidden.py"
    excluded["target_sha256"] = "0" * 64
    with pytest.raises(ValidationError):
        validator.validate(excluded)

    sensitive = next(
        record for record in _records() if record["category"] == "plaintext_credentials"
    )
    sensitive["hash_basis"] = "file_bytes"
    with pytest.raises(ValidationError):
        validator.validate(sensitive)


def test_repository_target_rejects_escape() -> None:
    with pytest.raises(AssertionError, match="逃逸仓库"):
        _repository_target("../legacy.py")
