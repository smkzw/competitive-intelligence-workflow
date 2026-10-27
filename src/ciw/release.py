"""release：一次运行的唯一发布物。内容哈希即 release_id；写入后设置 current 指针。"""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any

import jsonschema

from ciw import __version__
from ciw.store import Workspace, now_iso

SCHEMA_VERSION = "ciw-release-1"


def _schema() -> dict[str, Any]:
    return json.loads(resources.files("ciw").joinpath("data/release.schema.json").read_text(encoding="utf-8"))


def write_release(ws: Workspace, body: dict[str, Any]) -> tuple[str, Path]:
    content = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
    release_id = "rel_" + hashlib.sha256(content.encode()).hexdigest()[:16]
    doc = {
        "schema_version": SCHEMA_VERSION,
        "release_id": release_id,
        "generated_at": now_iso(),
        "code_version": __version__,
        **body,
    }
    jsonschema.validate(doc, _schema())
    out_dir = ws.releases_dir / release_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "release.json"
    if path.exists():
        existing = load_release(path)
        previous = {k: v for k, v in existing.items()
                    if k not in {"schema_version", "release_id", "generated_at", "code_version"}}
        if json.dumps(previous, ensure_ascii=False, sort_keys=True, default=str) != content:
            raise ValueError("不可变发布版本内容冲突")
        return release_id, path
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    tmp.replace(path)
    return release_id, path


def load_release(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if p.is_dir():
        p = p / "release.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    jsonschema.validate(doc, _schema())
    return doc
