"""Public acceptance observations only; enterprise labels are not verified applicant/MAH roles."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ciw2.harness.tools import ToolContext
from ciw2.sources import china_browser
from ciw2.sources.cde_capture import CaptureError, parse_capture, parse_page
from ciw2.sources.cde_resume import load_partial
from ciw2.sources.http import register_text

SCRIPT = Path(__file__).with_suffix('.mjs')
QUERY_FIELDS = {'drug_name':'drug_name','company':'applicant','acceptance_number':'acceptance_number'}


def code_hash() -> str:
    return hashlib.sha256(b''.join(path.read_bytes() for path in (
        Path(__file__),SCRIPT,Path(__file__).with_name('cde_capture.py'),
        Path(china_browser.__file__),Path(__file__).with_name('http.py'),
        Path(__file__).with_name('cde_resume.py')))).hexdigest()


def page_anchor(page: dict[str, Any]) -> str:
    cells = [[cell if isinstance(cell, str) else [cell['text'], cell['images']] for cell in row]
             for row in page['rows']]
    legend = [[entry['text'], entry['images']] for entry in page.get('legend', [])]
    total = page['pagination'].get('total_records')
    if total is None:
        total = int(re.search(r'共\s*(\d+)\s*条', page['pagination']['text'])[1])
    identity = [page['section'], sorted(page['filters'].items()), page['headers'], cells, legend,
                page['pagination']['page_size'], total]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def resume_capture(ctx: ToolContext, section: str, filters: dict, validate: Any) -> dict | None:
    prior = load_partial(ctx, section=section, filters=filters, validate=validate)
    if prior:
        if ctx.extra is None:
            ctx.extra = {}
        ctx.extra.setdefault('source_ids_read', set()).add(prior['source_id'])
        ctx.db.log_step(ctx.run_id, ctx.stage, 'source', 0, 'source_observation', {
            'project_id':ctx.project_id, 'source_id':prior['source_id'], 'mode':'cache_read',
            'cache_read_at':datetime.now(UTC).isoformat(), 'complete':False})
        if 1 in prior['pages_read'] and any(n > 1 for n in prior['pages_read']):
            return prior
    return None


def resume_options(prior: dict | None) -> dict | None:
    if not prior:
        return None
    first = next(p for p in prior['pages'] if p['pagination']['current'] == 1)
    return {'pages_read':prior['pages_read'], 'page_size':first['pagination']['page_size'],
            'total_records':prior['total_records'], 'first_page_sha256':page_anchor(first)}


def merge_capture(prior: dict | None, pages: list[dict], end: dict) -> tuple[list[dict], dict]:
    numbers = [page['pagination']['current'] for page in pages]
    used = end.get('resume_used', False)
    if type(used) is not bool:
        raise china_browser.BrowserFailed('CDE恢复标记不合法')
    for key in ('reused_pages', 'new_pages_checked'):
        if key in end and (not isinstance(end[key], list) or any(type(n) is not int for n in end[key])):
            raise china_browser.BrowserFailed('CDE恢复页号不合法')
    if end.get('new_pages_checked', numbers) != numbers or not used and end.get('reused_pages', []):
        raise china_browser.BrowserFailed('CDE恢复读取记录与实际分页不符')
    reused: list[int] = []
    if used:
        first = [page for page in pages if page['pagination']['current'] == 1]
        old_first = [page for page in (prior or {}).get('pages', []) if page['pagination']['current'] == 1]
        if not prior or len(first) != 1 or len(old_first) != 1 or page_anchor(first[0]) != page_anchor(old_first[0]):
            raise china_browser.BrowserFailed('CDE恢复首个新鲜页与来源锚点不符')
        reused = sorted(n for n in prior['pages_read'] if n != 1)
        if end.get('reused_pages') != reused or end.get('new_pages_checked') != numbers or set(reused) & set(numbers):
            raise china_browser.BrowserFailed('CDE恢复页集合与实际读取不符')
        pages = [*(page for page in prior['pages'] if page['pagination']['current'] in reused), *pages]
    return pages, {'reused_source_ids':[prior['source_id']] if reused else [],
                   'reused_pages':reused, 'new_pages_checked':numbers}


def _save(ctx: ToolContext, pages: list[dict[str, Any]], filters: dict[str, str], *,
          complete: bool, **metadata: Any) -> str:
    query = next(value for key,value in filters.items() if key in QUERY_FIELDS.values() and value)
    source_id = register_text(ctx,kind='cde',url=pages[0]['url'],
        text=json.dumps({'section':'acceptance','filters':filters,'pages':pages},ensure_ascii=False),
        title=f'CDE受理品种检索：{query}',meta={'method':'ego_public_ui','complete':complete,**metadata,
          'request_context':{'method':'browser_form','registry':'cde','section':'acceptance','filters':filters}})
    ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_observation',{
        'project_id':ctx.project_id,'source_id':source_id,'mode':'browser_checked','url':pages[0]['url'],
        'http_status':None,'browser_checked_at':datetime.now(UTC).isoformat(),'complete':complete})
    return source_id


def browser_search(ctx: ToolContext, query: str, query_kind: str) -> dict[str, Any]:
    if query_kind not in QUERY_FIELDS:
        raise china_browser.BrowserBlocked('CDE公开目录需明确药名、企业名称或受理号查询；不将适应症/靶点当作药名')
    if not query.strip():
        raise china_browser.BrowserFailed('CDE检索词为空')
    filters = dict.fromkeys(('year','drug_name','applicant','acceptance_number','drug_type','application_type'),'')
    filters[QUERY_FIELDS[query_kind]] = query
    prior = resume_capture(ctx, 'acceptance', filters,
                           lambda pages: parse_capture(pages, filters=filters, allow_partial=True))
    stdout,process_ok = china_browser._invoke(ctx,query,script_path=SCRIPT,
                                            options={'filters':filters, 'resume':resume_options(prior)})
    pages,end = china_browser._read_output(stdout)
    new_pages = pages
    if not pages:
        if end.get('status') in {'blocked','user_control'}:
            raise china_browser.BrowserBlocked('CDE浏览器空间不可用或需要用户交接')
        phase = end.get('phase')
        if phase not in {'start','navigate','filters','query','page_size','pages'}:
            phase = 'unknown'
        error_type = end.get('error_type')
        if error_type not in {'Error','ElementResolutionError','TimeoutError','PageNavigationTimeoutError',
                              'ElementNotFoundError'}:
            error_type = 'Error'
        raise china_browser.BrowserFailed(f'CDE浏览器未取得可核验的公开目录（{phase}: {error_type}）')
    try:
        parse_capture(pages,filters=filters,allow_partial=True)
        pages, recovery = merge_capture(prior, pages, end)
        result = parse_capture(pages,filters=filters,allow_partial=True)
    except (CaptureError, china_browser.BrowserFailed):
        valid = []
        for page in new_pages:
            try:
                parse_page(page,filters=filters)
            except CaptureError:
                continue
            valid.append(page)
        if valid:
            _save(ctx,valid,filters,complete=False,validation_failed=True)
        raise china_browser.BrowserFailed('CDE公开目录校验失败，未采用为完整检索') from None
    complete = process_ok and end.get('status') == 'ok' and result['complete']
    source_id = _save(ctx,pages,filters,complete=complete,pages_read=result['pages_read'],
                     pending_pages=result['pending_pages'],total_records=result['total_records'],**recovery)
    if not complete:
        raise china_browser.BrowserFailed('CDE检索未完成，已保存有效公开页')
    return {**result,'source_id':source_id,'query_kind':query_kind,
            'results':[{**row,'source_id':source_id} for row in result['results']]}


def persist_candidates(ctx: ToolContext, result: dict[str, Any], route: str) -> None:
    """A regulatory application is not a clinical trial or a confirmed indication/MAH."""
    source_id = result['source_id']
    if not ctx.db.one('SELECT id FROM sources WHERE id=? AND project_id=?',(source_id,ctx.project_id)):
        raise china_browser.BrowserFailed('CDE来源不属于当前项目')
    existing = {drug['name']:drug for drug in ctx.db.entities(ctx.project_id,'drug')}
    with ctx.db.tx():
        for row in result['results']:
            name = row['drug_name']
            reference = {key:row[key] for key in ('acceptance_number','company_text','application_type','drug_type','registration_class',
                'handled_date_text','source_id','page','row_number')}
            refs = list(existing.get(name,{}).get('attrs',{}).get('cde_acceptance_refs',[]))
            prior = next((ref for ref in refs if isinstance(ref, dict) and
                          ref.get('source_id') == source_id and
                          ref.get('acceptance_number') == row['acceptance_number']), None)
            if prior is None:
                refs.append(reference)
            else:
                prior.update(reference)  # Enrich one provisional source observation, retaining unrelated metadata.
            ctx.db.upsert_entity(ctx.project_id,'drug',name,route_id=route,attrs={'cde_acceptance_refs':refs})
            existing.setdefault(name,{'attrs':{}})['attrs']['cde_acceptance_refs'] = refs
