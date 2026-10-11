"""Recoverably archive one explicitly retired candidate, never project or history roots."""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

from tools.build_recovery_package import file_digest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / ".artifacts/1007-ab-shared-question-preview-v4"
OUT = ROOT / ".artifacts/recovery-archives/1007-frontend-v4-20261011"


def inventory() -> dict[str, str]:
    result = {}
    for path in SOURCE.rglob("*"):
        assert not path.is_symlink(), "No symlink traversal or removal"
        if path.is_file():
            result[path.relative_to(ROOT / ".artifacts").as_posix()] = file_digest(path)
        else:
            assert path.is_dir(), "No special files"
    return result


def main() -> None:
    assert SOURCE.parent == ROOT / ".artifacts" and not SOURCE.is_symlink()
    assert not (ROOT / ".artifacts").is_symlink()
    assert SOURCE.is_dir() and not OUT.exists(), "Never overwrite a recovery checkpoint"
    assert file_digest(SOURCE / "actual.json") == (
        "7e982d1f696a2751d3f4dc776637a12cd9b2802b47f62ec20c08e14b96c4c613"
    )
    actual = json.loads((SOURCE / "actual.json").read_bytes())
    assert actual["current_writes"] == 0 and actual["source_writes"] == 0
    assert actual["facts"] == 1505 and actual["reports"]["A"]["pages"] == 49
    before = inventory()
    assert before and SOURCE.name + "/actual.json" in before
    original_bytes = sum((ROOT / ".artifacts" / name).stat().st_size for name in before)
    OUT.mkdir(parents=True)
    archive = OUT / (SOURCE.name + ".tar.gz")
    with tarfile.open(archive, "x:gz") as store:
        for name in sorted(before):
            store.add(ROOT / ".artifacts" / name, arcname=name, recursive=False)
    recovered = {}
    with tarfile.open(archive, "r:gz") as store:
        for member in store:
            assert member.isfile() and member.name in before and member.name not in recovered
            stream = store.extractfile(member)
            assert stream is not None
            recovered[member.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    assert recovered == before and inventory() == before, "All files must be recoverable unchanged"
    receipt = {"state": "ARCHIVE_VERIFIED_BEFORE_REMOVAL", "source": SOURCE.name,
               "archive": archive.relative_to(ROOT).as_posix(), "sha256": file_digest(archive),
               "files": before, "original_bytes": original_bytes,
               "archive_bytes": archive.stat().st_size,
               "restore": "tar -xzf " + archive.relative_to(ROOT).as_posix() + " -C .artifacts"}
    with (OUT / "verified-before-removal.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=1)
    # Exact validated owned terminal candidate only; all original bytes are in the verified archive.
    shutil.rmtree(SOURCE)
    assert not SOURCE.exists()
    receipt["state"] = "TERMINAL_CANDIDATE_RECOVERABLY_ARCHIVED"
    with (OUT / "actual.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=1)
    print(json.dumps({"state": receipt["state"], "files": len(before),
                      "net_logical_bytes_reclaimed": original_bytes - archive.stat().st_size,
                      "archive_sha256": receipt["sha256"]}))


if __name__ == "__main__":
    main()
