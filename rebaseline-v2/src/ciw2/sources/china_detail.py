"""Read an explicitly list-bound Chinese trial detail; source data, not MAH/facts."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources import china_browser
from ciw2.sources.china_capture import parse_capture as parse_list
from ciw2.sources.http import register_text

SCRIPT=Path(__file__).with_suffix('.mjs')
URL='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml'
BASIC={'登记号','试验状态','首次公示信息日期','申请人名称'}


def code_hash() -> str:
    return hashlib.sha256(b''.join(p.read_bytes() for p in (
        Path(__file__),SCRIPT,Path(china_browser.__file__),
        Path(__file__).with_name('china_capture.py')))).hexdigest()


def _rows(value: Any) -> list[list[str]]:
    if (not isinstance(value,list) or not value or any(not isinstance(r,list) or not r
            or any(not isinstance(c,str) for c in r) for r in value)):
        raise ValueError('登记详情缺少有效原始单元格')
    return value


def _fields(rows: list[list[str]], labels: set[str]) -> dict[str,str]:
    found={}
    for row in rows:
        if len(row)%2:
            raise ValueError('登记详情标签与值不是配对单元格')
        for label,value in zip(row[::2],row[1::2],strict=True):
            key=label.strip()
            if key in labels:
                if key in found:
                    raise ValueError('登记详情身份字段重复，不能任取一项')
                found[key]=value
    return found


def _tables(value: Any) -> list[dict[str,Any]]:
    if not isinstance(value,list) or not value:
        raise ValueError('登记详情无临床信息表')
    for table in value:
        if not isinstance(table,dict) or set(table)!={'rows','nested'} or not isinstance(table['nested'],list):
            raise ValueError('登记详情表结构不符')
        rows=_rows(table['rows'])
        seen=set()
        for nested in table['nested']:
            if not isinstance(nested,dict) or set(nested)!={'row','column','rows'}:
                raise ValueError('登记详情内表结构不符')
            r,c=nested['row'],nested['column']
            if type(r) is not int or type(c) is not int or not 0<=r<len(rows) or not 0<=c<len(rows[r]) or (r,c) in seen:
                raise ValueError('登记详情内表定位不符')
            seen.add((r,c))
            content='\n'.join('\t'.join(row) for row in _rows(nested['rows']))
            if ' '.join(content.split())!=' '.join(rows[r][c].split()):
                raise ValueError('登记详情内表与原始单元格不一致')
    return value


def parse_capture(raw: dict, *, ctr: str, detail_id: str) -> dict[str,Any]:
    expected={'url','title','section','registry_id','detail_id','basic','tables','observed_at'}
    if not isinstance(raw,dict) or set(raw)!=expected:
        raise ValueError('登记详情捕获结构不符')
    if not re.fullmatch(r'CTR[0-9]{8}',ctr) or not re.fullmatch(r'[0-9a-f]{32}',detail_id):
        raise ValueError('登记详情请求标识不合法')
    u=urlsplit(raw['url'])
    if (u.scheme!='https' or u.hostname not in {'www.chinadrugtrials.org.cn','chinadrugtrials.org.cn'}
            or u.port not in {None,443} or u.username or u.password or u.query or u.fragment
            or u.path!='/clinicaltrials.searchlistdetail.dhtml'):
        raise ValueError('登记详情不是无会话参数的官方页面')
    if (raw['section']!='trial_detail' or raw['registry_id']!=ctr or raw['detail_id']!=detail_id
            or raw['title']!=ctr+'详细信息'):
        raise ValueError('登记详情与所请求试验不符')
    if not isinstance(raw['observed_at'],str) or datetime.fromisoformat(raw['observed_at']).tzinfo is None:
        raise ValueError('登记详情无有效实际获取时间')
    basic=_fields(_rows(raw['basic']),BASIC)
    tables=_tables(raw['tables'])
    fields=_fields([r for t in tables for r in t['rows']],{'登记号','药物名称','适应症','试验专业题目','试验分期'})
    labels={r[0].strip() for t in tables for r in t['rows']}
    if (set(basic)!=BASIC or basic['登记号']!=ctr or fields.get('登记号')!=ctr
            or not fields.get('药物名称') or not fields.get('适应症') or '试验分期' not in fields
            or not {'入选标准','排除标准'}<=labels):
        raise ValueError('登记详情缺少完整身份/设计/入排原文块')
    text='\n'.join('\t'.join(row) for row in [*raw['basic'],*(r for t in tables for r in t['rows'])])
    return {'registry_id':ctr,'detail_id':detail_id,'applicant':basic['申请人名称'],
            'registered_drug_name':fields['药物名称'],'indication':fields['适应症'],
            'title':fields.get('试验专业题目'),'basic':raw['basic'],'tables':tables,'source_text':text}


def _bound_trial(ctx: ToolContext, ctr: str) -> dict[str,Any]:
    if ctx.settings.china_ego_space_id is None:
        raise china_browser.BrowserBlocked('未配置专用Ego浏览器空间')
    if not ctx.db.one('SELECT id FROM runs WHERE id=? AND project_id=?',(ctx.run_id,ctx.project_id)):
        raise ValueError('详情请求运行不属于当前项目')
    trials=[t for t in ctx.db.entities(ctx.project_id,'trial') if t['name']==ctr]
    if len(trials)!=1:
        raise ValueError('详情请求不是当前项目已发现的明确试验')
    attrs=trials[0]['attrs']
    source=ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                     (attrs.get('registry_source_id'),ctx.project_id,'chinadrugtrials'))
    if source is None:
        raise ValueError('登记详情缺少本项目列表来源')
    try:
        raw=ctx.cas.get(source['digest'])
        if hashlib.sha256(raw).hexdigest()!=source['digest']:
            raise ValueError('列表来源字节不符')
        payload=json.loads(raw)
        listing=parse_list(payload['pages'],query=payload['query'])
    except (OSError,KeyError,TypeError,ValueError):
        raise ValueError('登记详情列表来源无法核验') from None
    matches=[r for r in listing['results'] if r['ctr']==ctr and r['detail_id']==attrs.get('registry_detail_id')]
    if len(matches)!=1:
        raise ValueError('登记详情标识与原列表不符')
    return {**matches[0],'list_source_id':source['id']}


def browser_detail(ctx: ToolContext, ctr: str) -> dict[str,Any]:
    bound=_bound_trial(ctx,ctr)
    scope={'registry':'chinadrugtrials','section':'trial_detail','registry_id':ctr,'detail_id':bound['detail_id']}
    if ctx.extra is None:
        ctx.extra={}
    ctx.extra.setdefault('source_ids_read',set()).add(bound['list_source_id'])
    cache=ctx.extra.setdefault('fetch_cache',{})
    key=('china_detail',ctx.project_id,ctx.run_id,ctr,bound['detail_id'],code_hash())
    mode='browser_checked'
    if key in cache:
        source=ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                         (cache[key],ctx.project_id,'chinadrugtrials'))
        if source is None or json.loads(source['meta']).get('request_context')!=scope:
            raise ValueError('登记详情缓存来源范围不符')
        raw=ctx.cas.get(source['digest'])
        if hashlib.sha256(raw).hexdigest()!=source['digest']:
            raise ValueError('登记详情缓存字节不符')
        captured=json.loads(raw)
        expected_text=parse_capture(captured,ctr=ctr,detail_id=bound['detail_id'])['source_text'].encode()
        stored_text=ctx.cas.get(source['text_digest'])
        if hashlib.sha256(stored_text).hexdigest()!=source['text_digest'] or stored_text!=expected_text:
            raise ValueError('登记详情缓存原文与原始字节不符')
        sid=source['id']
        mode='cache_reused'
    else:
        stdout,ok=china_browser._invoke(ctx,ctr,script_path=SCRIPT,options={'detail_id':bound['detail_id']})
        pages,end=china_browser._read_output(stdout)
        if not ok or end.get('status')!='ok' or len(pages)!=1:
            if end.get('status')=='user_control':
                raise china_browser.BrowserBlocked('登记详情浏览器控制已交接')
            raise china_browser.BrowserFailed('登记详情未完成，不能作为空资料')
        captured=pages[0]
        parsed=parse_capture(captured,ctr=ctr,detail_id=bound['detail_id'])
        sid=register_text(ctx,kind='chinadrugtrials',url=captured['url'],text=parsed['source_text'],
            raw=json.dumps(captured,ensure_ascii=False).encode(),title=captured['title'],
            meta={'method':'ego_public_ui','request_context':scope,'extractor_version':code_hash()})
        cache[key]=sid
    parsed=parse_capture(captured,ctr=ctr,detail_id=bound['detail_id'])
    ctx.extra.setdefault('source_ids_read',set()).add(sid)
    ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_observation',{
        'project_id':ctx.project_id,'source_id':sid,'mode':mode,
        'browser_checked_at' if mode=='browser_checked' else 'cache_reused_at':datetime.now(UTC).isoformat()})
    return {**parsed,'source_id':sid,'source_url':captured['url'],'observation_mode':mode}


class DetailArgs(BaseModel):
    ctr: str = Field(pattern=r'^CTR[0-9]{8}$',description='本项目已登记列表来源中的CTR号；不猜详情URL或法律角色')


@REGISTRY.register('china_trial_detail','读取本项目明确CTR的中文登记详情，完整保留入排、组别、终点及原文来源版本。',DetailArgs)
def _detail(ctx: ToolContext, a: DetailArgs) -> dict[str,Any]:
    result=browser_detail(ctx,a.ctr)
    # One complete readable source, not a duplicated JSON-table wall. Raw nested
    # cells remain in the immutable source capture for deterministic consumers.
    keys=('source_id','source_url','registry_id','applicant','registered_drug_name',
          'indication','title','observation_mode','source_text')
    return {key:result[key] for key in keys}
