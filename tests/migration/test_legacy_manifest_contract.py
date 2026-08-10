from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "migration" / "legacy_manifest.jsonl"
SCHEMA = ROOT / "migration" / "legacy_manifest.schema.json"
INITIAL_ITEM_IDS = {
    "approved-design-spec-v1-2",
    "decision-ledger-d01-d70",
    "kangzhe-share-contract-candidate",
    "kangzhe-presentation-contract-candidate",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_legacy_manifest_schema_and_copied_targets_are_current() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    records = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    item_ids = [record["item_id"] for record in records]
    assert len(item_ids) == len(set(item_ids)), "迁移登记项标识不得重复"
    assert set(item_ids) >= INITIAL_ITEM_IDS

    for record in records:
        validator.validate(record)
        assert record["runtime_dependency"] is False
        if record["status"] != "copied_verified":
            continue
        assert record["target_path"], "已复制项必须指向新仓内的相对路径"
        target = ROOT / record["target_path"]
        assert target.is_file(), f"已复制项不存在：{record['target_path']}"
        assert _sha256(target) == record["source_sha256"]
