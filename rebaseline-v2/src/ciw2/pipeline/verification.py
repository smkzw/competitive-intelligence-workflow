"""Atomic, replay-safe adoption of source-bound extraction proposals.

核验结果同时写入一条 ``fact_verdict`` 回执（绑定不可变事实与固定来源），
使同 run 恢复和离线复核都能判断“当前规则是否已经复核过”。回执与事实同一
事务写入：回执失败时新事实/实体一起回滚。
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from ciw2.domain.tiers import tier_of
from ciw2.pipeline.context import RunContext
from ciw2.pipeline.profile import FIELDS, SOURCE_CONTEXT, anchored, context_of
from ciw2.sources import ctgov
from ciw2.sources.http import source_by_url
from ciw2.verify import assessment

CONTEXT_KEYS = ('endpoint', 'unit', 'stat_type', 'arm', 'timepoint', 'population', 'denominator', 'enrollment_type',
                *SOURCE_CONTEXT)
SOURCE_UNREAD = '来源版本未在本项目中读取，无法核验'
RETRYABLE = frozenset({'source_unavailable','source_unreadable','source_digest_mismatch'})


def compatible(old: dict[str, Any], context: dict[str, Any]) -> bool:
    # Missing context is not evidence of equality to a specified scientific context.
    return all(old['context'].get(key) == context.get(key) for key in CONTEXT_KEYS)


def _stored(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, 'value': json.loads(row['value']), 'context': json.loads(row['context'])}


def prepare(rc: RunContext, cross_check: Callable[..., Any]) -> list[dict[str, Any]]:
    ctx, prepared = rc.tool_ctx(), []
    rule = assessment.rule_identity()
    receipts = rc.db.latest_verdicts(rc.project_id, rule)
    for stage in ('enrich_drugs', 'extract_results', 'extract_design'):
        for raw in _proposals(rc,stage):
            fid=_proposal_id(rc,stage,raw)
            existing=_existing_proposal(rc,stage,raw,fid)
            proposal=raw if existing else anchored(rc,raw)
            if existing:fid=existing['id']
            if existing:
                row = _stored(existing)
                receipt = receipts.get(fid)
                if (receipt is not None and assessment.receipt_matches(receipt, row,db=rc.db)
                        and receipt['verdict'] not in RETRYABLE):
                    prepared.append({'id': fid, 'replay': True, 'status': receipt['status'], 'rule': rule})
                    continue
                if row['status'] != 'verified' or not row['extracted_by'].startswith('llm:'):
                    prepared.append({'id': fid, 'replay': True, 'status': row['status'], 'rule': rule})
                    continue
                # Rule changed or no valid receipt: recheck the pinned source, adopt no fact.
                result = assessment.inspect_fact(rc.db,rc.cas,row)
                receipt = assessment.make_receipt(row, rule=rule, stored_status='verified', result=result)
                prepared.append({'id': fid, 'replay': True, 'reassessed': True, 'rule': rule,
                                 'status': receipt['status'], 'receipt': receipt})
                continue
            if 'source_id' in proposal:
                src = rc.db.one('SELECT * FROM sources WHERE project_id=? AND id=? AND url=?',
                               (rc.project_id, proposal['source_id'], proposal['source_url']))
            else:  # Read-only compatibility for extraction receipts made before source pinning.
                src = source_by_url(ctx, proposal['source_url'])
            item: dict[str, Any] = {'id': fid, 'proposal': proposal, 'rule': rule,
                                    'source_id': src['id'] if src else None, 'status': 'unverified',
                                    'quote_start': None, 'quote_end': None, 'reason': ''}
            if proposal['field'] in FIELDS:
                try:item['entity_id']=_profile_entity(rc,proposal)
                except ValueError as exc:
                    item['identity_error']=str(exc);prepared.append(item);continue
            if proposal.get('value') is None:
                item.update(status='unknown', reason='来源未给出')
            elif src is None:
                item['reason'] = SOURCE_UNREAD
            else:
                result = assessment.inspect_fact(rc.db,rc.cas,{'project_id':rc.project_id,
                    'entity_id':item.get('entity_id'),'source_id':src['id'],'field':proposal['field'],
                    'quote':proposal.get('quote'),'value':proposal['value'],'context':context_of(proposal)})
                status = 'verified' if result['verdict'] == 'confirmed' else 'unverified'
                item.update(status=status, reason=result['reason'], assessment=result,
                            quote_start=result['quote_start'], quote_end=result['quote_end'])
                if (item['status'] == 'verified' and tier_of(proposal['field']) == 'critical' and rc.check_llm is not None
                        and cross_check(rc.check_llm, proposal) is False):
                    item.update(status='conflict', reason='二次核对模型不同意')
            prepared.append(item)
    return prepared


def _proposal_id(rc: RunContext,stage: str,proposal: dict[str,Any]) -> str:
    digest=hashlib.sha256(json.dumps([rc.project_id,rc.run_id,stage,proposal],
        sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return f'fct_{digest}'


def _existing_proposal(rc: RunContext,stage: str,raw: dict[str,Any],fid: str) -> dict[str,Any] | None:
    existing=rc.db.one('SELECT * FROM facts WHERE project_id=? AND id=?',(rc.project_id,fid))
    if existing or raw['field'] not in FIELDS:return existing
    # Read-only compatibility: old IDs hashed the expanded quote. Reconstruct that
    # exact historical ID from stored quotes, not from current CAS availability.
    matches=[]
    for row in rc.db.query('SELECT * FROM facts WHERE project_id=? AND field=? AND source_id IS ?',
                            (rc.project_id,raw['field'],raw.get('source_id'))):
        legacy={**raw,'quote':row['quote']}
        if _proposal_id(rc,stage,legacy)==row['id']:matches.append(row)
    if len(matches)>1:raise ValueError('原始提案存在多个历史采用身份，保留现场不猜选')
    return matches[0] if matches else None


def _proposals(rc: RunContext,stage: str) -> list[dict[str,Any]]:
    row=rc.db.one("SELECT status,output_json FROM stages WHERE run_id=? AND name=?",(rc.run_id,stage))
    if not row or not row['output_json'] or row['status'] not in {'succeeded','failed'}:return []
    output=json.loads(row['output_json'])
    if row['status']=='failed' and (stage!='enrich_drugs'
            or not (output.get('pending_units') or output.get('pending_drug_ids'))):return []
    return output.get('facts',[])


def _profile_entity(rc: RunContext,proposal: dict[str,Any]) -> str:
    from ciw2.domain.identity import name_key
    from ciw2.domain.profile_evidence import drug_names
    drugs=rc.db.entities(rc.project_id,'drug')
    expected={d['id'] for d in drugs if name_key(d['name'])==name_key(proposal['drug'])}
    actual={d['id'] for d in drugs if name_key(d['name'])==name_key(proposal['entity'])}
    if not actual:
        actual={d['id'] for d in drugs if any(name_key(n)==name_key(proposal['entity'])
                for n in drug_names(rc.db,rc.project_id,d['id']))}
    if len(expected)!=1 or actual!=expected:raise ValueError('档案返回实体不等于宿主输入药物实体')
    return next(iter(expected))


def _append(rc: RunContext, receipt: dict[str, Any], rule: str,
            latest: dict[str, dict[str, Any]]) -> bool:
    if receipt.get('rule') != rule or assessment.same_receipt(latest.get(receipt['fact_id']), receipt):
        return False
    row=rc.db.one('SELECT * FROM facts WHERE id=? AND project_id=?',(receipt['fact_id'],rc.project_id))
    if row is None or not assessment.receipt_matches(receipt,_stored(row),db=rc.db):return False
    rc.db.log_step(rc.run_id, rc.stage or 'verify', 'verify', 0, assessment.ROLE, receipt)
    latest[receipt['fact_id']] = receipt
    return True


def _replayed(row: dict[str, Any], receipts: dict[str, dict[str, Any]],db: Any) -> str:
    """并发/竞态兜底：已有事实只读，不能凭本轮提案回执认证。"""
    receipt = receipts.get(row['id'])
    if receipt is not None and assessment.receipt_matches(receipt, row,db=db):
        return receipt['status']
    return 'unverified' if row['status'] == 'verified' else row['status']


def adopt(rc: RunContext, entity_for: Callable[..., str], cross_check: Callable[..., Any]) -> dict[str, Any]:
    # Source/CAS reads happen before the DB write lock. A failed write adopts nothing.
    prepared = prepare(rc, cross_check)
    stats = dict.fromkeys(('verified', 'unverified', 'conflict', 'unknown'), 0)
    reasons: dict[str, int] = {}
    issues, replayed, reassessed = [], 0, 0
    with rc.db.tx(immediate=True):
        rule = assessment.rule_identity()
        receipts = rc.db.latest_verdicts(rc.project_id, rule)
        for item in prepared:
            if item.get('identity_error'):
                fact=item['proposal']
                issues.append({**{k:fact[k] for k in ('entity','drug','field')},'reason':item['identity_error']})
                continue
            if item.get('replay'):
                if item.get('receipt') and _append(rc, item['receipt'], rule, receipts):
                    reassessed += 1
                replayed += 1
                row=rc.db.one('SELECT * FROM facts WHERE id=?',(item['id'],))
                stats[_replayed(_stored(row),receipts,rc.db)] += 1
                continue
            existing = rc.db.one('SELECT * FROM facts WHERE id=?', (item['id'],))
            if existing:
                replayed += 1
                stats[_replayed(_stored(existing), receipts,rc.db)] += 1
                continue
            fact = item['proposal']
            try:
                entity = item['entity_id'] if 'entity_id' in item else entity_for(rc, fact['entity'], fact['drug'])
                if (fact['field'].startswith(('design.', 'trial.', 'status.trial'))
                        and not any(e['id'] == entity for e in rc.db.entities(rc.project_id, 'trial'))):
                    raise ValueError('试验设计事实需要明确的研究实体')
            except ValueError as exc:
                issues.append({**{k: fact[k] for k in ('entity', 'drug', 'field')}, 'reason': str(exc)})
                continue
            context = {**context_of(fact),**{key:fact[key] for key in CONTEXT_KEYS if fact.get(key) is not None}}
            if fact['field'].startswith('result.'):
                context['endpoint_key'] = ctgov.endpoint_key(context.get('endpoint') or fact['field'])
            status, reason, supersedes = item['status'], item['reason'], fact.get('supersedes')
            if supersedes:
                old = next((f for f in rc.db.current_facts(rc.project_id, entity)
                            if f['id'] == supersedes and f['field'] == fact['field']), None)
                if old is None:
                    status, reason = 'conflict', '修订对象不属于同项目、同实体、同字段的当前事实'
                elif status == 'verified' and not compatible(old, context):
                    reason, supersedes = 'revision_context_mismatch', None
                if status != 'verified':
                    supersedes = None
            if status=='verified' and fact['field'] in {'identity.target','identity.modality'}:
                from ciw2.domain.profile_evidence import brand_basis
                if (item.get('assessment') or {}).get('identity_basis')!=brand_basis(rc.db,rc.project_id,entity):
                    status,reason,supersedes='unverified','身份来源已变化，待重新核验',None
            stats[status] += 1
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
            record = {'id': item['id'], 'project_id': rc.project_id, 'entity_id': entity,
                'field': fact['field'], 'value': fact['value'], 'tier': tier_of(fact['field']), 'status': status,
                'source_id': item['source_id'], 'quote': fact.get('quote'),
                'quote_start': item['quote_start'], 'quote_end': item['quote_end'],
                'context': {**context, 'source_url': fact['source_url'], 'verify_note': reason,
                            'proposed_supersedes': fact.get('supersedes')},
                'extracted_by': f"llm:{fact.get('extraction_model', getattr(rc.llm, 'model', 'llm'))}",
                'supersedes': supersedes}
            rc.db.add_fact(record)
            if status == 'verified' and item.get('assessment'):
                rc.db.log_step(rc.run_id, rc.stage or 'verify', 'verify', 0, assessment.ROLE,
                               assessment.make_receipt(record, rule=rule, stored_status='verified',
                                                       result=item['assessment']))
    return {'stats': stats, 'reasons': reasons, 'identity_issues': issues,
            'unresolved_entities': len(issues), 'replayed': replayed, 'reassessed': reassessed}
