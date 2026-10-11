"""New candidate after actual pixel rejection; never overwrite the first attempt."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-b-compact-shared-reading-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "21ed53e8399b77345a69203e8c589dd302897a8022eb733dd5d6b8753be1b4dc"
)
source = raw.decode().replace(
    ".artifacts/1007-b-compact-shared-reading-v1",
    ".artifacts/1007-b-compact-shared-reading-v2",
).replace(
    "source = raw.decode().replace(",
    "source = raw.decode().replace('\"templates/b/page.html.j2\",', "
    "'\"templates/b/page.html.j2\", \"templates/b/base.html.j2\",').replace(",
)
exec(compile(source, str(Path(__file__)), "exec"))
