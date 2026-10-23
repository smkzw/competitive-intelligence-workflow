"""Opt-in exact official certificate smoke; separate data directory, no model or fact adoption."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ciw2.config import Settings
from ciw2.harness.tools import REGISTRY, RESULT_PAGE_TOOL, ToolContext
from ciw2.service import Service
from ciw2.sources.nmpa_detail import code_hash


def complete(ctx: ToolContext, arguments: dict) -> dict:
    payload=json.loads(REGISTRY.get('nmpa_product_detail').run(ctx,arguments))
    if payload.get('status')=='paged':
        chunks=[]
        while True:
            chunks.append(payload['text'])
            if payload['next_offset'] is None:break
            payload=json.loads(RESULT_PAGE_TOOL.run(ctx,{
                'result_id':payload['result_id'],'offset':payload['next_offset']}))
            if payload.get('status')!='paged':raise RuntimeError('来源结果分页未闭合')
        payload=json.loads(''.join(chunks))
    if payload.get('error') or payload.get('status')=='tool_failed':
        raise RuntimeError(payload.get('error') or '来源读取失败')
    return payload


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--registration-number',required=True)
    parser.add_argument('--category',choices=['境内生产药品','境外生产药品'],required=True)
    parser.add_argument('--space',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True,help='明确的新证据目录，不覆盖旧资料')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)

    def no_models(_):
        raise AssertionError('Exact public-source smoke must not initialize models')

    svc=Service(Settings(data_dir=args.output/'data',china_ego_space_id=args.space),llm_factory=no_models)
    pid=svc.create_project('官方药品许可资料核查',['A'])
    rid=svc.db.create_run(pid)
    ctx=ToolContext(db=svc.db,cas=svc.cas,settings=svc.settings,project_id=pid,run_id=rid,
                    stage='universe_china',extra={})
    arguments={'url':args.url,'registration_number':args.registration_number,'category':args.category}
    before=code_hash()
    result={'scope':'EXACT_PUBLIC_NMPA_SOURCE_TOOL_NOT_INDICATION_APPROVAL_OR_M2',
        'project_id':pid,'run_id':rid,'code_hash':before,'model_calls':0,'state':'STARTED'}
    (args.output/'started.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    try:
        first=complete(ctx,arguments)
        cached=complete(ctx,arguments)
        assert first['observation_mode']=='browser_checked' and cached['observation_mode']=='cache_reused'
        assert first['source_id']==cached['source_id']
        ctx.run_id=svc.db.create_run(pid)
        fresh=complete(ctx,arguments)
        assert fresh['observation_mode']=='browser_checked'
        assert svc.db.current_facts(pid)==[] and svc.db.entities(pid)==[]
        assert before==code_hash()
        for source in svc.db.query('SELECT * FROM sources WHERE project_id=?',(pid,)):
            assert source['published_date'] is None
            for key in ('digest','text_digest'):
                assert hashlib.sha256(svc.cas.get(source[key])).hexdigest()==source[key]
        result.update(state='RETURNED',results=[first,cached,fresh],source_ids_read=sorted(ctx.extra['source_ids_read']),
            source_count=len(svc.db.query('SELECT id FROM sources WHERE project_id=?',(pid,))),
            observations=svc.db.query("SELECT content FROM agent_steps WHERE role='source_observation' ORDER BY id"),
            scientific_facts_added=0,entities_added=0,M2='NOT_RUN',M3='NOT_RUN')
    except Exception as exc:  # noqa: BLE001 - preserve failed smoke evidence without claiming empty success
        result.update(state='FAILED',error_type=type(exc).__name__,error=str(exc))
    (args.output/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'results','observations'}},ensure_ascii=False))
    return 0 if result['state']=='RETURNED' else 1


if __name__=='__main__':raise SystemExit(main())
