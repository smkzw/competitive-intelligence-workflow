"""Normal current21 preview with shared categorical identity styles; no current/save."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).with_name("render-baseline-landscape-preview-v3.py")
SPEC = importlib.util.spec_from_file_location("normal_ab_identity_preview", BASE)
assert SPEC is not None and SPEC.loader is not None
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)
producer.OUT = producer.ROOT / ".artifacts/1007-identity-palette-preview-v5"
producer.main()
with (producer.OUT / "producer-binding.json").open("x") as stream:
    json.dump({
        "base_recipe_sha256": producer.sha(BASE),
        "wrapper_sha256": producer.sha(Path(__file__)),
        "override": "OUT only; ordinary A/B producer; exact current21 values/identity and project pins",
        "purpose": "Source-group categorical palette, compact label spacing, filter stability",
    }, stream, ensure_ascii=False, indent=1)
