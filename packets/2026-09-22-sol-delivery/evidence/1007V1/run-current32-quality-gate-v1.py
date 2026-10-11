"""One immutable milestone development gate, not product release acceptance."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-current32-quality-gate-v1"


def source_set() -> dict[str, str]:
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ("src", "tests", "tools") for p in (ROOT / directory).rglob("*")
            if p.is_file() and p.suffix in {".py", ".js", ".css", ".j2", ".sh"}}


def main() -> None:
    OUT.mkdir()  # Exclusive: reopen an existing terminal result; do not replay.
    frozen = source_set()
    command = ["bash", "tools/gate.sh"]
    (OUT / "prewrite.json").write_text(json.dumps({
        "command": command, "source_set": frozen,
        "scope": "Six-step quality-only, not integration/browser/clinical/hosts/install/RC",
    }, sort_keys=True))
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    log = result.stdout.encode()
    (OUT / "terminal.txt").write_bytes(log)
    unchanged = frozen == source_set()
    (OUT / "result.json").write_text(json.dumps({
        "returncode": result.returncode, "source_set_unchanged": unchanged,
        "log_sha256": hashlib.sha256(log).hexdigest(),
        "state": "QUALITY_ONLY_PASSED" if result.returncode == 0 and unchanged
                 else "FAILED_OR_SOURCE_CHANGED_NOT_ACCEPTED",
    }, sort_keys=True))
    print(result.stdout, end="")
    if result.returncode or not unchanged:
        raise SystemExit(result.returncode or 1)


if __name__ == "__main__":
    main()
