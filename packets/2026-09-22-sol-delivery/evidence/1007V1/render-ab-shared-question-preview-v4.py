"""Normal A/B current32 candidate after shared chart reading fixes, no save."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-ab-shared-question-preview-v3.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "52c8e0b46a7e76082d982c971ca1e169912ab49bc78cdbe5ea78e12ade99350e"
)
source = raw.decode().replace(".artifacts/1007-ab-shared-question-preview-v3",
                             ".artifacts/1007-ab-shared-question-preview-v4")
exec(compile(source, str(Path(__file__)), "exec"))
