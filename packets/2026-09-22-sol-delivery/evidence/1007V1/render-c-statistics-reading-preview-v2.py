"""Normal C reading preview after owner density/duplicate/marker root repair."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).with_name("render-c-statistics-reading-preview-v1.py")
SPEC = importlib.util.spec_from_file_location("normal_c_reading_preview", BASE)
assert SPEC is not None and SPEC.loader is not None
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)
producer.OUT = producer.ROOT / ".artifacts/1007-c-statistics-reading-preview-v2"
producer.main()
with (producer.OUT / "producer-binding.json").open("x") as stream:
    json.dump({
        "base_recipe_sha256": producer.base.sha(BASE),
        "wrapper_sha256": producer.base.sha(Path(__file__)),
        "override": "OUT only; ordinary C9/current21 renderer and exact durable pins",
        "purpose": "Concise visible warning, nonduplicate complete source/gap details, native arrow",
    }, stream, ensure_ascii=False, indent=1)
