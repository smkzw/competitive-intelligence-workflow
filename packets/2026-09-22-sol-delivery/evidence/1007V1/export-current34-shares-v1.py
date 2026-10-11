"""Frozen native-view/normal share instrument replay for one new current generation."""
from __future__ import annotations

import hashlib
from pathlib import Path

RECIPE = Path(__file__).with_name("export-current33-shares-v1.py")
raw = RECIPE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "c68e57b4536f68756861394b07cc41de9ede6ed5be63bc8d51674139eccf89b0"
)
source = raw.decode().replace("1007-abc-reading-current33-v1", "1007-b-opener-current34-v1")
source = source.replace("1007-current33-config-v2", "1007-current34-config-v1")
source = source.replace("current33", "current34").replace(" == 33", " == 34")
source = source.replace('"revision": 33', '"revision": 34')
source = source.replace('"current_revision": 33', '"current_revision": 34')
source = source.replace("CURRENT33_", "CURRENT34_")
namespace = {"__file__": str(Path(__file__)), "__name__": "frozen_current34_share_instrument"}
exec(compile(source, str(RECIPE), "exec"), namespace)
namespace["main"]()
