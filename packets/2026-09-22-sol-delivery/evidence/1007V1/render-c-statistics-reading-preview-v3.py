"""Normal C9 preview after separating field collections from drawer row grids."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).with_name("render-c-statistics-reading-preview-v1.py")
SPEC = importlib.util.spec_from_file_location("normal_c_reading_preview", BASE)
assert SPEC is not None and SPEC.loader is not None
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)
producer.OUT = producer.ROOT / ".artifacts/1007-c-statistics-reading-preview-v3"
producer.main()
with (producer.OUT / "producer-binding.json").open("x") as stream:
    json.dump({
        "base_recipe_sha256": producer.base.sha(BASE),
        "wrapper_sha256": producer.base.sha(Path(__file__)),
        "override": "OUT only; ordinary C9/current21 renderer and exact durable pins",
        "purpose": "Reading folds and evidence summary with independent field-collection layout",
    }, stream, ensure_ascii=False, indent=1)
