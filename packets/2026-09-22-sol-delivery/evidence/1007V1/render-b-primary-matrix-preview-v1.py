"""New ordinary readonly current32 candidate, not a committed delivery."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-b-question-reading-preview-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "bf81aff069036b8defe1998f9f5b84a71dff2456f79ad1e81dc25e50a466fa76"
)
source = raw.decode().replace(
    ".artifacts/1007-b-question-reading-preview-v1",
    ".artifacts/1007-b-primary-matrix-preview-v1",
)
exec(compile(source, str(Path(__file__)), "exec"))
