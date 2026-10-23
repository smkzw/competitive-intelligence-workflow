"""Atomically activate one literal Chinese registry design using existing sources/facts/links."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ciw2.harness.tools import ToolContext
from ciw2.sources import china_design, china_detail
from ciw2.sources.http import public_url

EXTRACTOR_VERSION=hashlib.sha256(b''.join(p.read_bytes() for p in (
    Path(__file__),Path(china_design.__file__),Path(china_detail.__file__),
    Path(__file__).parents[1]/'domain/tiers.py'))).hexdigest()


def _source(ctx: ToolContext, ctr: str, raw: dict, sid: str) -> dict:
    if not ctx.db.one('SELECT id FROM runs WHERE id=? AND project_id=?',(ctx.run_id,ctx.project_id)):
        raise ValueError('中国登记设计运行不属于当前项目')
    china_detail.parse_capture(raw,ctr=ctr,detail_id=raw['detail_id'])
    source=ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                     (sid,ctx.project_id,'chinadrugtrials'))
    scope={'registry':'chinadrugtrials','section':'trial_detail','registry_id':ctr,'detail_id':raw['detail_id']}
    try:
        original=ctx.cas.get(source['digest']) if source else None
        text=ctx.cas.get(source['text_digest']) if source else None
        valid=(source is not None and source['url']==public_url(raw['url'])
            and json.loads(source['meta']).get('request_context')==scope
            and hashlib.sha256(original).hexdigest()==source['digest'] and json.loads(original)==raw
            and hashlib.sha256(text).hexdigest()==source['text_digest']
            and text.decode()==china_detail.parse_capture(raw,ctr=ctr,detail_id=raw['detail_id'])['source_text'])
    except (OSError,KeyError,TypeError,ValueError,UnicodeError):
        valid=False
    if not valid:
        raise ValueError('中国登记设计来源版本、字节、身份或原文未通过核对')
    return source


def _activate_design(ctx: ToolContext, ctr: str, raw: dict, sid: str, route: str) -> dict:
    source=_source(ctx,ctr,raw,sid)
    bundle=china_design.parse_design(raw)
    snapshot=hashlib.sha256(f'{sid}:{EXTRACTOR_VERSION}'.encode()).hexdigest()
    added=0
    with ctx.db.tx():
        eid,_=ctx.db.upsert_entity(ctx.project_id,'trial',ctr,attrs=bundle['attrs'],route_id=route)
        prior=ctx.db.one("SELECT dst,attrs FROM links WHERE project_id=? AND src=? AND rel='chinadrugtrials-current'",
                         (ctx.project_id,eid))
        previous=json.loads(prior['attrs']) if prior else None
        for fact in bundle['facts']:
            key=json.dumps([ctx.project_id,eid,snapshot,fact],sort_keys=True,ensure_ascii=False)
            fid='fct_'+hashlib.sha256(key.encode()).hexdigest()
            if not ctx.db.one('SELECT id FROM facts WHERE id=?',(fid,)):
                ctx.db.add_fact({**fact,'id':fid,'project_id':ctx.project_id,'entity_id':eid,'source_id':sid,
                                'context':{**fact['context'],'source_snapshot':snapshot}})
                added+=1
        if previous is None or previous.get('snapshot')!=snapshot:
            current={'snapshot':snapshot,'source_id':sid,'source_digest':source['digest'],
                'extractor_version':EXTRACTOR_VERSION,'fact_count':len(bundle['facts']),'gaps':bundle['gaps'],
                'registry_id':ctr,'scientific_retraction':False}
            ctx.db.execute("DELETE FROM links WHERE project_id=? AND src=? AND rel='chinadrugtrials-current'",
                           (ctx.project_id,eid))  # Only the mutable current pointer; historical facts/sources stay intact.
            ctx.db.link(ctx.project_id,eid,'chinadrugtrials-current',sid,attrs=current)
            ctx.db.log_step(ctx.run_id,ctx.stage,'chinadrugtrials',0,'source_activation',
                            {'entity_id':eid,'previous':previous,'current':current,'reason':'registry_snapshot'})
    return {'entity_id':eid,'source_id':sid,'snapshot':snapshot,'facts_added':added,
            'fact_count':len(bundle['facts']),'gaps':bundle['gaps']}


def ingest_trial(ctx: ToolContext, ctr: str, route_id: str='china:detail') -> dict:
    result=china_detail.browser_detail(ctx,ctr)
    source=ctx.db.one('SELECT digest FROM sources WHERE project_id=? AND id=?',(ctx.project_id,result['source_id']))
    raw=json.loads(ctx.cas.get(source['digest']))
    return _activate_design(ctx,ctr,raw,result['source_id'],route_id)
