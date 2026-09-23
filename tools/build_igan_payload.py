"""IgAN A 载荷构建器（从通用构建器参数化派生）。"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
args = [
    sys.executable,
    str(ROOT / "tools" / "build_a_payload.py"),
    "--cas-dir",
    str(ROOT / ".artifacts/source-cas/ctgov-igan-20260920"),
    "--alias-map",
    str(ROOT / "packets/2026-09-20-test-round-2/igan-alias-map.json"),
    "--indication",
    "IgA肾病",
    "--indication-id",
    "igan",
    "--output",
    str(ROOT / "packets/2026-09-20-test-round-2/igan-a-payload.json"),
    "--cutoff",
    "2026-09-20",
]
# 创建最小别名表（如果不存在）
alias_path = ROOT / "packets/2026-09-20-test-round-2/igan-alias-map.json"
if not alias_path.exists():
    # 从 CT.gov 数据自动提取药物名
    with (ROOT / "packets/2026-09-20-test-round-2/igan-page-1.json").open() as handle:
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
        "map_id": "igan-alias-auto",
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
