"""Reuse the read-only normal renderer recipe for the expert-reading revision."""

import importlib.util
from pathlib import Path

ROOT = Path("/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow")
RECIPE = Path(__file__).with_name("render-b-reading-hierarchy-preview-v1.py")
SPEC = importlib.util.spec_from_file_location("readonly_reading_preview", RECIPE)
assert SPEC and SPEC.loader
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
preview.OUT = ROOT / ".artifacts/1007-b-expert-reading-preview-v1"
preview.main()
