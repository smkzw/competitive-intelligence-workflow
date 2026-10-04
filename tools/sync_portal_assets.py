"""Mechanically refresh the mirror from the sole authored portal asset tree.

No source/history edits, discovery outside the explicit tree, or obsolete-file
deletion. Packaging subsequently validates both bytes and manifest digests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def synchronize(root: Path) -> None:
    author = root / "src/ci_workflow/renderers/portal/assets"
    mirror = root / "assets/portal"
    manifest_path = mirror / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("author_source") != "src/ci_workflow/renderers/portal/assets/":
        raise ValueError("manifest does not identify the sole author")
    records = manifest["files"]
    names = {*records, "kangzhe-site.css", "kangzhe-site.js", "kz-motion.js"}
    for name in sorted(names):
        source, target = author / name, mirror / name
        if (
            Path(name).name != name
            or not source.is_file()
            or source.is_symlink()
            or target.is_symlink()
        ):
            raise ValueError(f"unsafe or missing authored asset: {name}")
    for name in sorted(names):
        source = author / name
        data = source.read_bytes()
        shutil.copyfile(source, mirror / name)
        records[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    synchronize(parser.parse_args().root.resolve())
