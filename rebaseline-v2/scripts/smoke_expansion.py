"""One real, explicitly budgeted source query; never a full-universe/model acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from ciw2.config import Settings
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.expansion import expand_universe, query_plan
from ciw2.service import Service


def smoke(settings: Settings, output: Path, condition: str, intervention: str) -> dict:
    if output.exists():
        raise FileExistsError('Existing evidence is immutable; choose a new smoke output')
    output.mkdir(parents=True)
    cfg = replace(settings, data_dir=output / 'data')
    service = Service(cfg, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = service.create_project(condition, ['C'])
    run_id = service.db.create_run(pid)
    service.db.upsert_entity(pid, 'drug', intervention)
    rc = service.context(pid, run_id)
    rc.stage = 'universe_expand'
    rc.cache.update(max_expansion_queries=1, max_expansion_rounds=1)
    plan = query_plan(rc)
    assert plan and plan[0]['tool'] == 'ctgov_search'
    assert plan[0]['region'] == 'china' and plan[0]['arguments']['location'] == 'China'
    try:
        result = expand_universe(rc, lambda _: 0)
    except IncompleteWork as exc:
        result = exc.output
    sources = service.db.query('SELECT id,digest,url FROM sources WHERE project_id=?', (pid,))
    for source in sources:
        assert hashlib.sha256(service.cas.get(source['digest'])).hexdigest() == source['digest']
    succeeded = len(result['completed_queries']) == 1 and not result['source_issues']
    receipt = {'scope': 'ONE_CHINA_CT_GOV_SOURCE_QUERY', 'project_id': pid, 'run_id': run_id,
        'status': 'SOURCE_QUERY_COMPLETED_FRONTIER_PENDING' if succeeded else 'SOURCE_QUERY_FAILED',
        'pipeline_acceptance': 'NOT_RUN', 'medical_acceptance': 'NOT_RUN', 'model_calls': len(rc.llm.calls),
        'planned_query': plan[0], 'result': result, 'sources': sources,
        'candidate_names_and_literal_aliases': [{key: d[key] for key in ('name', 'aliases')}
                                               for d in service.db.entities(pid, 'drug')],
        'trials': len(service.db.entities(pid, 'trial')),
        'source_files': {str(p.relative_to(Path(__file__).resolve().parents[1])): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((Path(__file__).resolve().parents[1] / 'src/ciw2').rglob('*.py'))}}
    assert receipt['model_calls'] == 0
    assert not result['expansion_complete'] and result['source_attempts'] == 1
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--condition', required=True, help='Literal condition query, usually English')
    parser.add_argument('--intervention', required=True)
    args = parser.parse_args()
    receipt = smoke(Settings(), args.output.resolve(), args.condition, args.intervention)
    print(json.dumps({key: receipt[key] for key in ('scope', 'status', 'model_calls', 'trials')}, ensure_ascii=False))
    raise SystemExit(0 if receipt['status'] == 'SOURCE_QUERY_COMPLETED_FRONTIER_PENDING' else 2)
