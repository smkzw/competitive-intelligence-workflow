"""New preview after actual1440 density FAIL; preserve all v1 output."""

from __future__ import annotations

import importlib.util
from pathlib import Path

RECIPE = Path(__file__).with_name("render-b-scalar-records-preview-v1.py")
SPEC = importlib.util.spec_from_file_location("b_scalar_preview_original_helper", RECIPE)
assert SPEC is not None and SPEC.loader is not None
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
preview.OUT = preview.ROOT / ".artifacts/1007-b-scalar-records-preview-v2"

if __name__ == "__main__":
    preview.main()
