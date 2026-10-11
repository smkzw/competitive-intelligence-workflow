"""Normal readonly three-report candidate; existing shared query and source contracts."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-abc-question-heading-v1"
recipe = Path(__file__).with_name("render-abc-source-disclosure-v1.py")
raw = recipe.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "5b10558370c92d79e9197ede41c61cab7bd62d37db44b35e98002bc33199c6df"
)
paths = ("src/ci_workflow/reports/common/page-catalogs/C.yaml",
         "docs/architecture/page-catalogs/C.yaml")
catalogs = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}
source = raw.decode().replace(".artifacts/1007-abc-source-disclosure-v1",
                             ".artifacts/1007-abc-question-heading-v1")
exec(compile(source, str(Path(__file__)), "exec"))
assert catalogs == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                    for name in paths}
with (OUT / "catalog-bindings.json").open("x") as stream:
    json.dump(catalogs, stream, sort_keys=True, indent=1)
