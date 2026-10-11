"""New read-only candidate after actual A graph-below-table geometry failure."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-ab-shared-question-preview-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "202bcbb56625d775c6c70ef37cbd757a1c33dc88c5f883df72f4f6e54ded7bf6"
)
source = raw.decode().replace(".artifacts/1007-ab-shared-question-preview-v1",
                             ".artifacts/1007-ab-shared-question-preview-v2")
assert "Never overwrite an original candidate or receipt" in source
exec(compile(source, str(Path(__file__)), "exec"))
