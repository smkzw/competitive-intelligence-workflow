"""Ordinary new candidate after source-caption reading failure; no history rewrite."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-b-sparse-visible-preview-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "4eb9f909ab40730bfcb95c4cfa65e62d70a11efbf6c012e04240e8d3079dc09c"
)
source = raw.decode().replace(
    ".artifacts/1007-b-sparse-visible-preview-v1",
    ".artifacts/1007-b-sparse-visible-preview-v2",
)
exec(compile(source, str(Path(__file__)), "exec"))
