from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "migration" / "legacy_manifest.jsonl"
SCHEMA = ROOT / "migration" / "legacy_manifest.schema.json"
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
    assert item_ids

    for record in records:
        validator.validate(record)
        assert record["runtime_dependency"] is False
        if record["final_disposition"] != "migrated":
            continue
        assert record["new_path"], "已迁移项必须指向新仓内的相对路径"
        target = ROOT / record["new_path"]
        assert target.is_file(), f"已迁移项不存在：{record['new_path']}"
        assert _sha256(target) == record["target_sha256"]
