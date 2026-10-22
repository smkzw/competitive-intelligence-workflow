"""真实网络冒烟（不调用 LLM）：CT.gov / openFDA / PubMed / 中国来源 / 全网搜索 的可达性与覆盖台账。
用法：python scripts/smoke_live.py "paroxysmal nocturnal hemoglobinuria" iptacopan
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import ciw2.sources  # noqa: F401
from ciw2.config import Settings
from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.store.cas import CAS
from ciw2.store.db import DB


def main(condition: str, drug: str) -> None:
    s = Settings(data_dir=Path(tempfile.mkdtemp()))
    s.ensure_dirs()
    db, cas = DB(s.db_path), CAS(s.cas_dir)
    pid = db.create_project(condition, ["A", "B", "C"])
    ctx = ToolContext(db=db, cas=cas, settings=s, project_id=pid, run_id=db.create_run(pid), stage="smoke")
    calls = [
        ("ctgov_search", {"condition": condition, "location": "China", "route_id": "china:ctgov:location",
                          "region": "china", "max_results": 200}),
        ("ctgov_search", {"condition": condition, "intervention": drug, "route_id": "global:ctgov:intervention"}),
        ("fda_drugsfda", {"name": drug}),
        ("pubmed_search", {"query": f"{drug} AND {condition}", "max_results": 5}),
        ("china_registry_search", {"registry": "chinadrugtrials", "query": condition, "route_id": "china:cdt"}),
        ("web_search", {"query": f"{drug} {condition} phase 3", "route_id": "global:web"}),
    ]
    for name, args in calls:
        out = json.loads(REGISTRY.get(name).run(ctx, args))
        print(f"{name:22s} → " + json.dumps({k: out[k] for k in ("count", "mode", "status", "error") if k in out},
                                            ensure_ascii=False))
    for r in db.query("SELECT route_id, status, hits, note FROM coverage"):
        print("coverage", r)


if __name__ == "__main__":
    main(*(sys.argv[1:3] if len(sys.argv) >= 3 else ("paroxysmal nocturnal hemoglobinuria", "iptacopan")))
