"""New read-only candidate; retain every previous render and browser attempt."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-b-question-reading-preview-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "bf81aff069036b8defe1998f9f5b84a71dff2456f79ad1e81dc25e50a466fa76"
)
source = raw.decode().replace(
    'OUT = ROOT / ".artifacts/1007-b-question-reading-preview-v1"',
    'OUT = ROOT / ".artifacts/1007-b-compact-shared-reading-v1"',
).replace('"assets/portal.js", "assets/kangzhe-site.css")',
          '"assets/portal.js", "assets/kangzhe-site.css", "assets/kangzhe-site.js")')
exec(compile(source, str(Path(__file__)), "exec"))
