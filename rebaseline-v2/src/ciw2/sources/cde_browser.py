"""Public acceptance observations only; enterprise labels are not verified applicant/MAH roles."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ciw2.harness.tools import ToolContext
from ciw2.sources import china_browser
from ciw2.sources.cde_capture import CaptureError, parse_capture, parse_page
from ciw2.sources.http import register_text

SCRIPT = Path(__file__).with_suffix('.mjs')
QUERY_FIELDS = {'drug_name':'drug_name','company':'applicant','acceptance_number':'acceptance_number'}


def code_hash() -> str:
    return hashlib.sha256(b''.join(path.read_bytes() for path in (
        Path(__file__),SCRIPT,Path(__file__).with_name('cde_capture.py'),
        Path(china_browser.__file__),Path(__file__).with_name('http.py')))).hexdigest()


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
    stdout,process_ok = china_browser._invoke(ctx,query,script_path=SCRIPT,options={'filters':filters})
    pages,end = china_browser._read_output(stdout)
    if not pages:
        if end.get('status') in {'blocked','user_control'}:
            raise china_browser.BrowserBlocked('CDE浏览器空间不可用或需要用户交接')
        raise china_browser.BrowserFailed('CDE浏览器未取得可核验的公开目录')
    try:
        result = parse_capture(pages,filters=filters,allow_partial=True)
    except CaptureError:
        valid = []
        for page in pages:
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
                     pending_pages=result['pending_pages'],total_records=result['total_records'])
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
            reference = {key:row[key] for key in ('acceptance_number','company_text','application_type',
                'handled_date_text','source_id','page','row_number')}
            refs = list(existing.get(name,{}).get('attrs',{}).get('cde_acceptance_refs',[]))
            if reference not in refs:
                refs.append(reference)
            ctx.db.upsert_entity(ctx.project_id,'drug',name,route_id=route,attrs={'cde_acceptance_refs':refs})
            existing.setdefault(name,{'attrs':{}})['attrs']['cde_acceptance_refs'] = refs
