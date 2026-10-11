"""New ordinary candidate for sparse visibility; preserve the prior frozen render."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-b-compact-shared-reading-v2.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "e2e5a3af4128fc59ef0f9cafa52691ffafb619211013bdf34a377c4e35ab1da4"
)
source = raw.decode().replace(
    ".artifacts/1007-b-compact-shared-reading-v2",
    ".artifacts/1007-b-sparse-visible-preview-v1",
)
exec(compile(source, str(Path(__file__)), "exec"))
