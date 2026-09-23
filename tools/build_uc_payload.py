"""UC A 载荷构建器。"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
args = [
    sys.executable,
    str(ROOT / "tools" / "build_a_payload.py"),
    "--cas-dir",
    str(ROOT / ".artifacts/source-cas/ctgov-uc-20260920"),
    "--alias-map",
    str(ROOT / "packets/2026-09-20-test-round-2/uc-alias-map.json"),
    "--indication",
    "溃疡性结肠炎",
    "--indication-id",
    "uc",
    "--output",
    str(ROOT / "packets/2026-09-20-test-round-2/uc-a-payload.json"),
    "--cutoff",
    "2026-09-20",
]
alias_path = ROOT / "packets/2026-09-20-test-round-2/uc-alias-map.json"
if not alias_path.exists():
    with (ROOT / "packets/2026-09-20-test-round-2/uc-page-1.json").open() as handle:
        data = json.load(handle)
    drugs = set()
    for s in data.get("studies", []):
        for iv in (
            s.get("protocolSection", {}).get("armsInterventionsModule", {}).get("interventions")
            or []
        ):
            if (iv.get("type") or "").upper() in ("DRUG", "BIOLOGICAL"):
                name = (iv.get("name") or "").strip()
                if name and name.lower() not in ("placebo", "matching placebo"):
                    drugs.add(name)
    alias = {
        "schema_version": "1.0",
        "map_id": "uc-alias-auto",
        "canonical_by_alias": {d: d for d in sorted(drugs)},
        "excluded_interventions": ["Placebo", "Matching Placebo"],
        "notes": ["auto-generated from CT.gov page 1"],
    }
    alias_path.write_text(json.dumps(alias, ensure_ascii=False, indent=1))
    print(f"auto alias map: {len(drugs)} drugs")

result = subprocess.run(args, capture_output=True, text=True)
print(result.stdout[-500:] if result.stdout else "")
if result.returncode != 0:
    print("STDERR:", result.stderr[-500:])
    sys.exit(1)
