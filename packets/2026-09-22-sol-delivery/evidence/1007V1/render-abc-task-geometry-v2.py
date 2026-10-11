"""Normal readonly current32 render after shared geometry and C summary integration."""

import hashlib
from pathlib import Path

recipe = Path(__file__).with_name("render-abc-question-heading-v1.py")
raw = recipe.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "329903b1078d7fb2beaea7eafd01c36a6412eb39a70504f089a5369b960c3925"
)
source = raw.decode().replace(".artifacts/1007-abc-question-heading-v1",
                            ".artifacts/1007-abc-task-geometry-v2")
exec(compile(source, str(Path(__file__)), "exec"))
