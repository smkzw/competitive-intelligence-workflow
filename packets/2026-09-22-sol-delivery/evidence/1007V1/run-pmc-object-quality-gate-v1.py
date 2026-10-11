"""One source/UI milestone quality gate after all writers are terminal and frozen."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RECIPE = Path(__file__).with_name("run-abc-fact-version-quality-gate-v1.py")
assert hashlib.sha256(RECIPE.read_bytes()).hexdigest() == (
    "23d0e7ecf859a827525517fb628f878b8ef87884c992e20debe003db5222153c"
)
spec = importlib.util.spec_from_file_location("bounded_quality_recipe", RECIPE)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.OUT = ROOT / ".artifacts/1007-pmc-object-quality-gate-v1"
module.main()
