"""One frozen shared A/B-query milestone, not a product or clinical release gate."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("run-abc-fact-version-quality-gate-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "23d0e7ecf859a827525517fb628f878b8ef87884c992e20debe003db5222153c"
)
source = raw.decode().replace(".artifacts/1007-abc-fact-version-quality-gate-v1",
                             ".artifacts/1007-ab-shared-query-quality-gate-v1")
exec(compile(source, str(Path(__file__)), "exec"))
