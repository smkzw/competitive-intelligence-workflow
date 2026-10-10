"""Reuse the exact normal-entry producer for the next bounded presentation revision."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).with_name("render-baseline-landscape-preview-v3.py")
SPEC = importlib.util.spec_from_file_location("normal_ab_preview", BASE)
assert SPEC is not None and SPEC.loader is not None
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)
producer.OUT = producer.ROOT / ".artifacts/1007-plotted-label-preview-v4"
producer.main()  # Ordinary A/B renderers, current values, unchanged project pins; no save.
with (producer.OUT / "producer-binding.json").open("x") as stream:
    json.dump({
        "base_recipe_sha256": producer.sha(BASE),
        "wrapper_sha256": producer.sha(Path(__file__)),
        "override": "OUT only; normal A/B producer, source/current/identity preconditions intact",
        "purpose": "Visible grouped axes/legend density and truthful source-group labels",
    }, stream, ensure_ascii=False, indent=1)
