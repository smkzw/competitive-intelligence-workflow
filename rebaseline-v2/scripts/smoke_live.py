"""真实网络冒烟（不调用 LLM）：CT.gov / openFDA / PubMed / 中国来源 / 全网搜索 的可达性与覆盖台账。
用法：python scripts/smoke_live.py "paroxysmal nocturnal hemoglobinuria" iptacopan
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import ciw2.sources  # noqa: F401
from ciw2.config import Settings
from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources import ctgov
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


def _pagination_receipt(db: DB, cas: CAS, rows: list[dict]) -> dict:
    sources = db.query('SELECT id,url,digest,text_digest FROM sources ORDER BY rowid')
    raw_ids, totals = set(), set()
    for source in sources:
        raw = cas.get(source['digest'])
        if hashlib.sha256(raw).hexdigest() != source['digest']:
            raise ValueError('来源字节校验不一致')
        page = json.loads(raw)
        if page.get('totalCount') is not None:
            totals.add(page['totalCount'])
        raw_ids.update(item['protocolSection']['identificationModule']['nctId'] for item in page.get('studies', []))
    ids = [row['nct'] for row in rows]
    if len(totals) != 1 or totals != {len(ids)} or set(ids) != raw_ids or len(ids) != len(set(ids)):
        raise ValueError('完整来源页、唯一研究集合与官方totalCount不一致或未提供总数')
    return {'status': 'PASSED_SOURCE_PAGINATION_ONLY', 'source_versions': sources, 'page_count': len(sources),
            'unique_study_count': len(ids), 'official_total_counts': sorted(totals), 'study_ids': ids,
            'model_calls': 0, 'scientific_or_visual_acceptance': 'NOT_RUN'}


def complete_ctgov(condition: str, output_dir: Path) -> dict:
    """One isolated full-source probe; never mutates a running report or old receipt."""
    output_dir.mkdir(parents=True, exist_ok=False)
    settings = Settings(data_dir=output_dir / 'data')
    settings.ensure_dirs()
    db, cas = DB(settings.db_path), CAS(settings.cas_dir)
    pid = db.create_project(condition, [], request_text='Source pagination capability check; not a report')
    ctx = ToolContext(db=db, cas=cas, settings=settings, project_id=pid, stage='source_smoke',
                      extra={'fetch_cache': {}})
    try:
        result = _pagination_receipt(db, cas, ctgov.search(ctx, condition=condition, max_results=None))
    except Exception as exc:  # noqa: BLE001 - preserve source evidence on a failed capability probe
        result = {'status': 'FAILED_SOURCE_PAGINATION', 'error': f'{type(exc).__name__}: {exc}',
                  'model_calls': 0, 'source_versions': db.query('SELECT id,url,digest,text_digest FROM sources')}
    result.update({'condition': condition, 'project_id': pid, 'code_hashes': {
        'scripts/smoke_live.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'src/ciw2/sources/ctgov.py': hashlib.sha256(Path(ctgov.__file__).read_bytes()).hexdigest()}})
    with (output_dir / 'receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--complete-ctgov':
        if len(sys.argv) != 4:
            raise SystemExit('usage: smoke_live.py --complete-ctgov CONDITION NEW_OUTPUT_DIR')
        result = complete_ctgov(sys.argv[2], Path(sys.argv[3]))
        print(json.dumps({key: value for key, value in result.items() if key not in {'source_versions', 'study_ids'}},
                         ensure_ascii=False))
        raise SystemExit(0 if result['status'] == 'PASSED_SOURCE_PAGINATION_ONLY' else 1)
    else:
        main(*(sys.argv[1:3] if len(sys.argv) >= 3 else ("paroxysmal nocturnal hemoglobinuria", "iptacopan")))
