"""One explicit public review scope; exact lookup is host-side after closure."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ciw2.harness.tools import ToolContext
from ciw2.sources import china_browser
from ciw2.sources.cde_review_capture import SCOPE, CaptureError, parse_review_capture
from ciw2.sources.http import register_text

SCRIPT=Path(__file__).with_suffix('.mjs')


def _code_hash() -> str:
    return hashlib.sha256(b''.join(path.read_bytes() for path in (
        Path(__file__),SCRIPT,Path(__file__).with_name('cde_review_capture.py'),
        Path(__file__).with_name('cde_capture.py'),Path(china_browser.__file__)))).hexdigest()


def _observe(ctx: ToolContext, source: str, mode: str, complete: bool) -> None:
    event={'project_id':ctx.project_id,'source_id':source,'mode':mode,'complete':complete,'http_status':None}
    event['browser_checked_at' if mode=='browser_checked' else 'cache_reused_at']=datetime.now(UTC).isoformat()
    ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_observation',event)


def _save(ctx: ToolContext, pages: list[dict[str,Any]], complete: bool) -> str:
    sid=register_text(ctx,kind='cde',url=pages[0]['url'],
        text=json.dumps({'section':'new_review_task','filters':SCOPE,'pages':pages},ensure_ascii=False),
        title='CDE化药IND新报审评任务完整序列',meta={'method':'ego_public_ui','complete':complete,
            'request_context':{'registry':'cde','section':'new_review_task','filters':SCOPE}})
    _observe(ctx,sid,'browser_checked',complete)
    return sid


def _scope(ctx: ToolContext) -> tuple[list[dict[str,Any]],str]:
    if ctx.extra is None:
        ctx.extra={}
    cache=ctx.extra.setdefault('fetch_cache',{})
    key=f'cde_review:{ctx.project_id}:{ctx.run_id}:{ctx.settings.china_ego_space_id}:{_code_hash()}'
    if key in cache:
        source=ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=?',(cache[key],ctx.project_id))
        if not source or source['kind']!='cde':
            raise china_browser.BrowserFailed('审评缓存来源不属于当前项目')
        raw=ctx.cas.get(source['digest'])
        if hashlib.sha256(raw).hexdigest()!=source['digest']:
            raise china_browser.BrowserFailed('审评缓存来源字节不一致')
        payload=json.loads(raw)
        if payload.get('section')!='new_review_task' or payload.get('filters')!=SCOPE:
            raise china_browser.BrowserFailed('审评缓存范围不符')
        parse_review_capture(payload['pages'],filters=SCOPE)
        ctx.extra.setdefault('source_ids_read',set()).add(source['id'])
        _observe(ctx,source['id'],'cache_reused',True)
        return payload['pages'],source['id']
    stdout,ok=china_browser._invoke(ctx,'',script_path=SCRIPT)
    pages,end=china_browser._read_output(stdout)
    if not pages:
        if end.get('status') in {'blocked','user_control'}:
            raise china_browser.BrowserBlocked('审评浏览器空间不可用或需要用户交接')
        raise china_browser.BrowserFailed('未取得公开审评来源')
    try:
        parsed=parse_review_capture(pages,filters=SCOPE,allow_partial=True)
    except CaptureError:
        valid=[]
        for page in pages:
            try:
                parse_review_capture([page],filters=SCOPE,allow_partial=True)
            except CaptureError:
                continue
            valid.append(page)
        if valid:
            _save(ctx,valid,False)
        raise china_browser.BrowserFailed('审评来源校验失败，未闭合查询') from None
    complete=ok and end.get('status')=='ok' and parsed['complete']
    source=_save(ctx,pages,complete)
    if not complete:
        raise china_browser.BrowserFailed('审评序列未完成，已保存有效页但未缓存为成功')
    cache[key]=source
    return pages,source


def browser_search(ctx: ToolContext, query: str, query_kind: str) -> dict[str,Any]:
    import re
    if query_kind!='acceptance_number':
        raise china_browser.BrowserBlocked('当前审评适配只支持明确受理号与化药IND新报范围')
    if not isinstance(query,str) or not re.fullmatch('[A-Z]+[0-9]+',query.strip()):
        raise china_browser.BrowserBlocked('审评查询需完整受理号')
    pages,source=_scope(ctx)
    parsed=parse_review_capture(pages,filters=SCOPE,acceptance_number=query)
    return {**parsed,'source_id':source,'query_kind':query_kind,
        'results':[{**row,'source_id':source} for row in parsed['results']]}


def persist_refs(ctx: ToolContext, result: dict[str,Any], route: str) -> int:
    if not result.get('complete') or not ctx.db.one('SELECT id FROM sources WHERE id=? AND project_id=?',
                                                 (result['source_id'],ctx.project_id)):
        raise china_browser.BrowserFailed('不完整或跨项目审评来源不可关联')
    count=0
    with ctx.db.tx():
        for drug in ctx.db.entities(ctx.project_id,'drug'):
            applications=set()
            for ref in drug['attrs'].get('cde_acceptance_refs',[]):
                source=ctx.db.one('SELECT kind,meta FROM sources WHERE id=? AND project_id=?',
                                 (ref.get('source_id'),ctx.project_id))
                if source and source['kind']=='cde' and json.loads(source['meta']).get('request_context',{}).get('section')=='acceptance':
                    applications.add(ref['acceptance_number'])
            refs=list(drug['attrs'].get('cde_review_refs',[]))
            before=len(refs)
            for row in result['results']:
                if row['acceptance_number'] in applications and row not in refs:
                    refs.append(row)
            if len(refs)>before:
                ctx.db.upsert_entity(ctx.project_id,'drug',drug['name'],attrs={'cde_review_refs':refs},route_id=route)
                count+=len(refs)-before
    return count
