"""Observed included/proposed priority directories; their roles and dates stay distinct."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ciw2.harness.tools import ToolContext
from ciw2.sources import china_browser
from ciw2.sources.cde_browser import merge_capture, resume_capture, resume_options
from ciw2.sources.cde_capture import CaptureError, _check_url, _expected_rows, _parse_pagination
from ciw2.sources.http import register_text

SECTION='priority_included'
FILTERS={'acceptance_number':'','drug_name':'','applicant':''}
COLUMNS=('序号','受理号','药品名称','注册申请人','承办日期','申请日期','公示日期','状态','是否为罕见病药物')
FIELDS=('row_number_text','acceptance_number','drug_name','registration_applicant_text','handled_date_text',
        'application_date_text','publicity_date_text','directory_status_text','rare_disease_text')
PROPOSED_COLUMNS=('序号','受理号','药品名称','注册申请人','申请日期','公示日期','公示截止日期','是否为罕见病药物','提出异议')
PROPOSED_FIELDS=('row_number_text','acceptance_number','drug_name','registration_applicant_text',
                 'application_date_text','publicity_date_text','publicity_end_date_text','rare_disease_text','objection_text')
SECTIONS=(SECTION,'priority_proposed')
SCRIPT=Path(__file__).with_suffix('.mjs')


def _page(page: Any, index: int, section: str=SECTION) -> dict[str,Any]:
    if not isinstance(page,dict) or page.get('section')!=section or page.get('filters')!=FILTERS:
        raise CaptureError('优先审评栏目或完整序列筛选不符')
    url=_check_url(page.get('url'))
    if page.get('headers')!=list(COLUMNS if section==SECTION else PROPOSED_COLUMNS):raise CaptureError('优先审评九列表头不符')
    pager=page.get('pagination')
    if not isinstance(pager,dict) or not isinstance(pager.get('text'),str):raise CaptureError('优先审评分页结构不符')
    totals=set(re.findall(r'共\s*([0-9]+)\s*条',pager.get('text','')))
    if len(totals)!=1:raise CaptureError('优先审评分页总数缺失或冲突')
    current,size,total,count=_parse_pagination({**pager,'total_records':int(totals.pop())})
    if not total or size is None:raise CaptureError('优先审评空序列尚无真实来源验证')
    rows=page.get('rows')
    if not isinstance(rows,list) or len(rows)!=_expected_rows(current,size,count,total):
        raise CaptureError('优先审评页行数不完整')
    result=[]
    for i,cells in enumerate(rows):
        if not isinstance(cells,list) or len(cells)!=9 or any(not isinstance(c,str) for c in cells):
            raise CaptureError('优先审评行必须为九列原始文本')
        if cells[0].strip()!=str((current-1)*size+i+1) or not cells[2].strip():
            raise CaptureError('优先审评来源行号/受理号/药名不符')
        number=cells[1].strip();known=bool(re.fullmatch('[A-Z]+[0-9]+',number))
        result.append({**dict(zip(FIELDS if section==SECTION else PROPOSED_FIELDS,cells,strict=True)),'acceptance_number_text':cells[1],
            'acceptance_number':number if known else None,'raw_cells':list(cells),'page':current,
            'issues':[] if known else [{'reason':'acceptance_not_reported' if number in {'','无'} else 'unparsed_acceptance_number'}],
            'locator':f'$.pages[{index}].rows[{i}]','source_url':url,'observed_at':page.get('observed_at')})
    return {'url':url,'page':current,'page_size':size,'total_records':total,'total_pages':count,'rows':result}


def parse_capture(pages: list[dict], *, query: str | None = None, allow_partial: bool = False, section: str=SECTION) -> dict:
    if section not in SECTIONS:raise CaptureError('未经验证的优先审评栏目')
    if type(allow_partial) is not bool or not isinstance(pages,list) or not pages:raise CaptureError('优先审评缺少有效分页')
    parsed=[_page(p,i,section) for i,p in enumerate(pages)]
    identity={(p['url'],p['page_size'],p['total_records'],p['total_pages']) for p in parsed}
    if len(identity)!=1:raise CaptureError('优先审评范围/总数跨页变化')
    first=parsed[0];read=[p['page'] for p in parsed]
    if len(set(read))!=len(read):raise CaptureError('优先审评来源重复页')
    pending=sorted(set(range(1,first['total_pages']+1))-set(read))
    if pending and not allow_partial:raise CaptureError('优先审评序列未闭合')
    rows=[r for p in sorted(parsed,key=lambda p:p['page']) for r in p['rows']]
    matches=[r for r in rows if query is None or r['acceptance_number']==query]
    return {'section':section,'filters':dict(FILTERS),'complete':not pending,'total_records':first['total_records'],
        'total_pages':first['total_pages'],'pages_read':sorted(read),'pending_pages':pending,
        'matched_count':len(matches),'unresolved_acceptance_count':sum(r['acceptance_number'] is None for r in rows),'results':matches}


def _code_hash() -> str:
    return hashlib.sha256(b''.join(p.read_bytes() for p in (Path(__file__),SCRIPT,
        Path(__file__).with_name('cde_capture.py'),Path(__file__).with_name('cde_browser.py'),
        Path(__file__).with_name('cde_resume.py'),Path(china_browser.__file__),Path(__file__).with_name('http.py')))).hexdigest()


def _observe(ctx: ToolContext, source: str, mode: str, complete: bool) -> None:
    ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_observation',{'project_id':ctx.project_id,
        'source_id':source,'mode':mode,'complete':complete,'http_status':None,
        'browser_checked_at' if mode=='browser_checked' else 'cache_reused_at':datetime.now(UTC).isoformat()})


def _save(ctx: ToolContext, pages: list[dict], complete: bool, *, section: str=SECTION, **metadata: Any) -> str:
    sid=register_text(ctx,kind='cde',url=pages[0]['url'],title='CDE'+('纳入优先审评品种名单' if section==SECTION else '拟优先审评品种公示')+'完整目录',
        text=json.dumps({'section':section,'filters':FILTERS,'pages':pages},ensure_ascii=False),
        meta={'method':'ego_public_ui','complete':complete,**metadata,
            'request_context':{'registry':'cde','section':section,'filters':FILTERS}})
    _observe(ctx,sid,'browser_checked',complete);return sid


def _retain_rejected(ctx: ToolContext, pages: list[dict], section: str=SECTION) -> None:
    # Keep failed public captures for diagnosis, never as qualified source/cache.
    try:
        for page in pages:_check_url(page.get('url'))
    except (CaptureError,AttributeError):
        return
    digest=ctx.cas.put(json.dumps({'section':section,'pages':pages},ensure_ascii=False).encode())
    ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_capture_rejected',
                    {'digest':digest,'pages':len(pages),'accepted':False})


def _scope(ctx: ToolContext, *, section: str=SECTION) -> tuple[list[dict],str]:
    if section not in SECTIONS:raise china_browser.BrowserBlocked('未经验证的优先审评栏目')
    if ctx.extra is None:ctx.extra={}
    cache=ctx.extra.setdefault('fetch_cache',{})
    key=f'cde_priority:{section}:{ctx.project_id}:{ctx.run_id}:{ctx.settings.china_ego_space_id}:{_code_hash()}'
    if key in cache:
        source=ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',(cache[key],ctx.project_id,'cde'))
        if not source:raise china_browser.BrowserFailed('优先审评缓存不属于本项目')
        raw=ctx.cas.get(source['digest'])
        if hashlib.sha256(raw).hexdigest()!=source['digest']:raise china_browser.BrowserFailed('优先审评缓存字节不符')
        payload=json.loads(raw)
        if payload.get('section')!=section or payload.get('filters')!=FILTERS:raise china_browser.BrowserFailed('优先审评缓存范围不符')
        parse_capture(payload['pages'],section=section);ctx.extra.setdefault('source_ids_read',set()).add(source['id'])
        _observe(ctx,source['id'],'cache_reused',True);return payload['pages'],source['id']
    prior=resume_capture(ctx,section,FILTERS,lambda pages:parse_capture(pages,allow_partial=True,section=section))
    stdout,ok=china_browser._invoke(ctx,'',script_path=SCRIPT,options={'resume':resume_options(prior),'section':section})
    pages,end=china_browser._read_output(stdout);new_pages=pages
    if not pages:
        error=china_browser.BrowserBlocked if end.get('status') in {'blocked','user_control'} else china_browser.BrowserFailed
        raise error('未取得所选优先审评完整目录')
    try:
        parse_capture(pages,allow_partial=True,section=section);pages,recovery=merge_capture(prior,pages,end)
        parsed=parse_capture(pages,allow_partial=True,section=section)
    except (CaptureError,china_browser.BrowserFailed):
        _retain_rejected(ctx,new_pages,section)
        valid=[]
        for page in new_pages:
            try:_page(page,0,section)
            except CaptureError:continue
            valid.append(page)
        if valid:_save(ctx,valid,False,section=section)
        raise china_browser.BrowserFailed('优先审评来源校验失败，未闭合查询') from None
    complete=ok and end.get('status')=='ok' and parsed['complete'];sid=_save(ctx,pages,complete,section=section,**recovery)
    if not complete:raise china_browser.BrowserFailed('优先审评序列未完成，已保全有效来源')
    cache[key]=sid;return pages,sid


def browser_search(ctx: ToolContext, query: str, query_kind: str, *, section: str=SECTION) -> dict:
    if query_kind!='acceptance_number' or not isinstance(query,str) or not re.fullmatch('[A-Z]+[0-9]+',query.strip()):
        raise china_browser.BrowserBlocked('优先审评适配只支持明确完整受理号')
    pages,sid=_scope(ctx,section=section);parsed=parse_capture(pages,query=query.strip(),section=section)
    return {**parsed,'source_id':sid,'query_kind':query_kind,'results':[{**r,'source_id':sid} for r in parsed['results']]}
