"""Adopt one already-captured public NMPA certificate; literal, versioned, no fetch.

Activation never browses, never creates or renames entities and never merges a
holder with its manufacturer or domestic responsible person. It re-reads the
registered public capture, resolves exactly one existing drug by literal name,
and atomically appends deterministic facts plus one per-certificate current
pointer. Historical facts and other certificates keep their bytes.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ciw2.domain import identity, tiers
from ciw2.domain.identity import name_key
from ciw2.domain.tiers import tier_of
from ciw2.harness.tools import ToolContext
from ciw2.sources import nmpa_capture, nmpa_detail
from ciw2.verify import quote
from ciw2.verify.quote import check_quote

EXTRACTOR_VERSION=hashlib.sha256(b''.join(Path(module.__file__).read_bytes() for module in
    (identity,tiers,quote,nmpa_capture,nmpa_detail))+Path(__file__).read_bytes()).hexdigest()

CURRENT='nmpa-current'
ROLES=(('identity.name_zh','drug_name','registered_product_name_zh'),
       ('identity.name_en','drug_name_en','registered_product_name_en'))


def _require(ctx: ToolContext) -> None:
    if ctx.db is None or ctx.cas is None or not ctx.project_id or not ctx.run_id:
        raise ValueError('NMPA许可采用缺少当前项目或运行')
    if ctx.db.one('SELECT id FROM runs WHERE id=? AND project_id=?',
                  (ctx.run_id,ctx.project_id)) is None:
        raise ValueError('NMPA许可采用运行不属于当前项目')


def _run_belongs(ctx: ToolContext, run_id: Any) -> None:
    if not isinstance(run_id,str) or not run_id:
        raise ValueError('NMPA许可来源缺少原始运行绑定')
    if ctx.db.one('SELECT id FROM runs WHERE id=? AND project_id=?',(run_id,ctx.project_id)) is None:
        raise ValueError('NMPA许可来源原始运行不属于当前项目')


def _source(ctx: ToolContext, source_id: Any) -> tuple[dict[str,Any],str,str]:
    if not isinstance(source_id,str) or not source_id.strip():
        raise ValueError('NMPA许可来源标识缺失')
    source=ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                      (source_id,ctx.project_id,nmpa_detail.KIND))
    if source is None:
        raise ValueError('NMPA许可来源不属于当前项目')
    if not source['text_digest']:
        raise ValueError('NMPA许可来源缺少字面原文')
    try:
        meta=json.loads(source['meta'])
    except (TypeError,ValueError):
        raise ValueError('NMPA许可来源元数据不可读') from None
    if not isinstance(meta,dict) or not meta:
        raise ValueError('NMPA许可来源元数据不可读')
    if meta.get('extractor_version')!=nmpa_detail.code_hash():
        raise ValueError('NMPA许可抽取版本与当前代码不符')
    scope=meta.get('request_context')
    if not isinstance(scope,dict) or not scope:
        raise ValueError('NMPA许可来源缺少请求范围')
    if scope.get('tool')!='nmpa_product_detail':
        raise ValueError('NMPA许可来源工具范围不符')
    if scope.get('project_id')!=ctx.project_id:
        raise ValueError('NMPA许可来源请求范围不属于当前项目')
    _run_belongs(ctx,scope.get('run_id'))
    number=scope.get('registration_number')
    category=scope.get('category')
    if not isinstance(number,str) or re.fullmatch(nmpa_detail.NUMBER,number) is None:
        raise ValueError('NMPA许可来源请求范围缺少有效注册证号')
    if category not in nmpa_capture.FIELDS:
        raise ValueError('NMPA许可来源请求范围类别不符')
    url=scope.get('url')
    if not isinstance(url,str) or not url:
        raise ValueError('NMPA许可来源请求范围缺少公开记录地址')
    try:
        same_record=nmpa_detail._record(url)==nmpa_detail._record(source['url'])
    except ValueError:
        raise ValueError('NMPA许可来源请求范围地址与登记来源不符') from None
    if not same_record:
        raise ValueError('NMPA许可来源请求范围地址与登记来源不符')
    return source,number,category


def _capture(ctx: ToolContext, source: dict[str,Any], number: str, category: str) -> dict[str,Any]:
    try:
        raw=ctx.cas.get(source['digest'])
        text=ctx.cas.get(source['text_digest'])
    except (OSError,KeyError,TypeError,ValueError):
        raise ValueError('NMPA许可来源字节不可读') from None
    if (hashlib.sha256(raw).hexdigest()!=source['digest']
            or hashlib.sha256(text).hexdigest()!=source['text_digest']):
        raise ValueError('NMPA许可来源字节与登记摘要不符')
    try:
        captured=json.loads(raw)
    except (TypeError,ValueError):
        raise ValueError('NMPA许可捕获格式不符') from None
    try:
        parsed=nmpa_detail.parse_capture(captured,url=source['url'],
            registration_number=number,category=category)
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise ValueError('NMPA许可捕获与登记来源、证号或类别不符') from None
    try:
        literal=text.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError('NMPA许可原文不是UTF-8') from None
    if literal!=parsed['source_text']:
        raise ValueError('NMPA许可登记原文与捕获原文不一致')
    return parsed


def _target(ctx: ToolContext, keys: set[str]) -> dict[str,Any]:
    drugs=ctx.db.entities(ctx.project_id,'drug')
    # Discovery labels are search hints, not evidence that two products are one.
    index: dict[str,set[str]]={}
    for drug in drugs:
        index.setdefault(name_key(drug['name']),set()).add(drug['id'])
    sources={s['id'] for s in ctx.db.query('SELECT id FROM sources WHERE project_id=?',(ctx.project_id,))}
    for fact in ctx.db.current_facts(ctx.project_id):
        if (fact['field'] in {'identity.name_zh','identity.name_en'} and fact['status']=='verified'
                and fact['source_id'] in sources and isinstance(fact['value'],str) and name_key(fact['value'])):
            index.setdefault(name_key(fact['value']),set()).add(fact['entity_id'])
    owners=sorted(set().union(*(index.get(key,set()) for key in keys)))
    if not owners:
        return {'status':'unresolved','reason':'no_literal_match','candidate_ids':[]}
    if len(owners)>1:
        return {'status':'unresolved','reason':'ambiguous_literal_name','candidate_ids':owners}
    drug=next(item for item in drugs if item['id']==owners[0])
    if drug['in_scope']==0:
        return {'status':'unresolved','reason':'excluded_target','entity_id':drug['id'],
                'candidate_ids':[drug['id']]}
    return {'status':'ok','entity_id':drug['id']}


def _time(value: Any) -> datetime | None:
    if not isinstance(value,str):
        return None
    try:
        stamp=datetime.fromisoformat(value)
    except ValueError:
        return None
    return stamp if stamp.tzinfo is not None else None


def _context(parsed: dict[str,Any], snapshot: str, role: str, path: str) -> dict[str,Any]:
    return {'source_snapshot':snapshot,'registration_number':parsed['registration_number'],
        'category':parsed['category'],'jurisdiction':'CN','role':role,'json_path':path,
        'product_name_zh':parsed['drug_name'],'product_name_en':parsed['drug_name_en'],
        'strength':parsed['strength'],'observed_at':parsed['observed_at'],
        'issue_date':parsed['issue_date'],'approval_date':parsed['approval_date'],
        'valid_until':parsed['valid_until']}


def _fact(parsed: dict[str,Any], snapshot: str, field: str, value: str, role: str,
          key: str) -> dict[str,Any]:
    labels=nmpa_capture.FIELDS[parsed['category']]
    label=labels[key]
    raw=parsed['raw_fields'].get(label)
    path=parsed['field_locators'].get(key)
    if not isinstance(raw,str) or not raw or not isinstance(path,str) or not path:
        raise ValueError('NMPA许可字段缺少原值或定位')
    quote=label+'\t'+raw
    checked=check_quote(parsed['source_text'],quote,value)
    if not checked.ok:
        raise ValueError('NMPA许可字段引文未通过原文核验：'+checked.reason)
    return {'field':field,'value':value,'tier':tier_of(field),'status':'verified',
        'quote':quote,'quote_start':checked.start,'quote_end':checked.end,
        'context':_context(parsed,snapshot,role,path)}


def _facts(parsed: dict[str,Any], snapshot: str) -> list[dict[str,Any]]:
    facts=[]
    for field,key,role in ROLES:
        value=parsed.get(key)
        if value:
            facts.append(_fact(parsed,snapshot,field,value,role,key))
    if parsed['holder_name_zh'] is not None:
        holder='holder_name_zh'
    elif parsed['holder_name_en'] is not None:
        holder='holder_name_en'
    else:
        holder=None
    if holder:
        facts.append(_fact(parsed,snapshot,'status.china_mah',parsed['holder_name'],
                           'marketing_authorization_holder',holder))
    return facts


def _fact_rows(ctx: ToolContext, entity_id: str, source_id: str, parsed: dict[str,Any],
               snapshot: str) -> list[dict[str,Any]]:
    out=[]
    for item in _facts(parsed,snapshot):
        key=json.dumps([ctx.project_id,entity_id,snapshot,item['field'],item['context']],
                       sort_keys=True,ensure_ascii=False)
        out.append({**item,'id':'fct_'+hashlib.sha256(key.encode()).hexdigest(),
            'project_id':ctx.project_id,'entity_id':entity_id,'source_id':source_id,
            'extracted_by':'code:nmpa'})
    return out


def _pointers(ctx: ToolContext, number: str, category: str) -> list[dict[str,Any]]:
    matched=[]
    for row in ctx.db.query("SELECT src,dst,attrs FROM links WHERE project_id=? AND rel=?",
                            (ctx.project_id,CURRENT)):
        try:
            attrs=json.loads(row['attrs'])
        except (TypeError,ValueError):
            raise ValueError('NMPA当前许可指针损坏') from None
        if not isinstance(attrs,dict) or not attrs:
            raise ValueError('NMPA当前许可指针损坏')
        if attrs.get('registration_number')!=number or attrs.get('category')!=category:
            continue
        if _time(attrs.get('observed_at')) is None:
            raise ValueError('NMPA当前许可指针缺少有效实际获取时间')
        matched.append({**attrs,'entity_id':row['src'],'source_id':row['dst']})
    return matched


def _decide(matched: list[dict[str,Any]], source_id: str, snapshot: str,
            observed: datetime) -> tuple[str,dict[str,Any]|None,str|None]:
    if not matched:
        return 'adopt',None,None
    current=max(matched,key=lambda item:_time(item['observed_at']))
    current_at=_time(current['observed_at'])
    if observed<current_at:
        return 'stale',current,'older_observation'
    if observed==current_at:
        if len(matched)==1 and current['source_id']==source_id:
            if current.get('snapshot')==snapshot and current.get('extractor_version')==EXTRACTOR_VERSION:
                return 'already_current',current,'already_current_certificate'
            return 'adopt',current,'adoption_rule_changed'
        return 'stale',current,'same_observation_not_current_source'
    return 'adopt',current,None


def _attrs(parsed: dict[str,Any], snapshot: str, source_id: str) -> dict[str,Any]:
    return {'snapshot':snapshot,'source_id':source_id,
        'registration_number':parsed['registration_number'],'category':parsed['category'],
        'observed_at':parsed['observed_at'],'extractor_version':EXTRACTOR_VERSION}


def _write(ctx: ToolContext, entity_id: str, source_id: str, parsed: dict[str,Any], snapshot: str,
           matched: list[dict[str,Any]], facts: list[dict[str,Any]]) -> int:
    added=0
    for fact in facts:
        if ctx.db.one('SELECT id FROM facts WHERE id=?',(fact['id'],)) is None:
            ctx.db.add_fact(fact)
            added+=1
    for pointer in matched:
        ctx.db.execute("DELETE FROM links WHERE project_id=? AND src=? AND rel=? AND dst=? "
                       "AND json_extract(attrs,'$.registration_number')=? "
                       "AND json_extract(attrs,'$.category')=?",
                       (ctx.project_id,entity_id,CURRENT,pointer['source_id'],
                        parsed['registration_number'],parsed['category']))
    ctx.db.link(ctx.project_id,entity_id,CURRENT,source_id,attrs=_attrs(parsed,snapshot,source_id))
    ctx.db.log_step(ctx.run_id,ctx.stage,'nmpa',0,'source_activation',{
        'project_id':ctx.project_id,'source_id':source_id,'entity_id':entity_id,
        'snapshot':snapshot,'registration_number':parsed['registration_number'],
        'category':parsed['category'],'observed_at':parsed['observed_at'],
        'extractor_version':EXTRACTOR_VERSION,'facts_added':added,
        'replaced_source_ids':sorted(item['source_id'] for item in matched)})
    return added


def _result(status: str, entity_id: str, source_id: str, snapshot: str, facts_added: int,
            current: dict[str,Any]|None, reason: str|None=None) -> dict[str,Any]:
    out={'status':status,'entity_id':entity_id,'source_id':source_id,'snapshot':snapshot,
         'facts_added':facts_added,'reason':reason,'candidate_ids':[entity_id]}
    if current is not None:
        out['current']={'source_id':current['source_id'],'snapshot':current.get('snapshot'),
                        'observed_at':current.get('observed_at')}
    return out


def _unresolved(source_id: str, snapshot: str, target: dict[str,Any]) -> dict[str,Any]:
    return {'status':'unresolved','entity_id':target.get('entity_id'),'source_id':source_id,
        'snapshot':snapshot,'facts_added':0,'reason':target['reason'],
        'candidate_ids':target['candidate_ids']}


def activate_source(ctx: ToolContext, source_id: str) -> dict[str,Any]:
    """Adopt one registered certificate; no browser, model, entity creation or history rewrite."""
    _require(ctx)
    source,number,category=_source(ctx,source_id)
    parsed=_capture(ctx,source,number,category)
    keys={name_key(name) for name in (parsed['drug_name'],parsed['drug_name_en']) if name_key(name)}
    snapshot=hashlib.sha256(f'{source_id}:{EXTRACTOR_VERSION}'.encode()).hexdigest()
    observed=_time(parsed['observed_at'])
    if observed is None:
        raise ValueError('NMPA许可捕获缺少有效实际获取时间')
    target=_target(ctx,keys)
    if target['status']!='ok':
        return _unresolved(source_id,snapshot,target)
    facts=_fact_rows(ctx,target['entity_id'],source_id,parsed,snapshot)
    with ctx.db.tx(immediate=True):
        checked=_target(ctx,keys)
        if checked['status']!='ok' or checked['entity_id']!=target['entity_id']:
            return _unresolved(source_id,snapshot,checked)
        entity_id=checked['entity_id']
        matched=_pointers(ctx,number,category)
        status,current,reason=_decide(matched,source_id,snapshot,observed)
        if status!='stale' and any(item['entity_id']!=entity_id for item in matched):
            return _unresolved(source_id,snapshot,{'reason':'certificate_entity_conflict',
                'candidate_ids':sorted({entity_id,*[item['entity_id'] for item in matched]})})
        if status!='adopt':
            return _result(status,entity_id,source_id,snapshot,0,current,reason)
        added=_write(ctx,entity_id,source_id,parsed,snapshot,matched,facts)
    return _result('adopted',entity_id,source_id,snapshot,added,None)
