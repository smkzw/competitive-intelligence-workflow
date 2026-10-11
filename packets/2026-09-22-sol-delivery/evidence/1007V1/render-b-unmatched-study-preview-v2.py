"""A second, immutable normal B preview after the filter-scroll family fix."""

from __future__ import annotations

import importlib.util
from pathlib import Path

RECIPE = Path(__file__).with_name("render-b-unmatched-study-preview-v1.py")
SPEC = importlib.util.spec_from_file_location("normal_b_preview_v1", RECIPE)
assert SPEC is not None and SPEC.loader is not None
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
preview.OUT = preview.ROOT / ".artifacts/1007-b-unmatched-study-preview-v2"

if __name__ == "__main__":
    # The delegated helper records its own digest. Retain this wrapper separately.
    preview.main()
