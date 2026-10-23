"""Atomic, replay-safe adoption of source-bound extraction proposals."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from ciw2.domain.tiers import tier_of
from ciw2.pipeline.context import RunContext
from ciw2.sources import ctgov
from ciw2.sources.http import source_by_url, source_text
from ciw2.verify.quote import check_quote

CONTEXT_KEYS = ('endpoint', 'unit', 'stat_type', 'arm', 'timepoint', 'population', 'denominator', 'enrollment_type')


def compatible(old: dict[str, Any], context: dict[str, Any]) -> bool:
    # Missing context is not evidence of equality to a specified scientific context.
    return all(old['context'].get(key) == context.get(key) for key in CONTEXT_KEYS)


def prepare(rc: RunContext, cross_check: Callable[..., Any]) -> list[dict[str, Any]]:
    ctx, prepared = rc.tool_ctx(), []
    for stage in ('extract_results', 'extract_design'):
        for proposal in (rc.db.stage_output(rc.run_id, stage) or {}).get('facts', []):
            digest = hashlib.sha256(json.dumps([rc.project_id, rc.run_id, stage, proposal],
                sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            fid = f'fct_{digest}'
            existing = rc.db.one('SELECT * FROM facts WHERE project_id=? AND id=?', (rc.project_id, fid))
            if existing:
                prepared.append({'id': fid, 'replay': True, 'status': existing['status']})
                continue
            if 'source_id' in proposal:
                src = rc.db.one('SELECT * FROM sources WHERE project_id=? AND id=? AND url=?',
                               (rc.project_id, proposal['source_id'], proposal['source_url']))
            else:  # Read-only compatibility for extraction receipts made before source pinning.
                src = source_by_url(ctx, proposal['source_url'])
            status, start, end, reason = 'unverified', None, None, ''
            if proposal.get('value') is None:
                status, reason = 'unknown', '来源未给出'
            elif src is None:
                reason = '来源版本未在本项目中读取，无法核验'
            else:
                check = check_quote(source_text(ctx, src['id']) or '', proposal.get('quote'), proposal['value'])
                start, end, reason = check.start, check.end, check.reason
                status = 'verified' if check.ok else 'unverified'
                if (check.ok and tier_of(proposal['field']) == 'critical' and rc.check_llm is not None
                        and cross_check(rc.check_llm, proposal) is False):
                    status, reason = 'conflict', '二次核对模型不同意'
            prepared.append({'id': fid, 'proposal': proposal, 'source_id': src['id'] if src else None,
                             'status': status, 'quote_start': start, 'quote_end': end, 'reason': reason})
    return prepared


def adopt(rc: RunContext, entity_for: Callable[..., str], cross_check: Callable[..., Any]) -> dict[str, Any]:
    # Source/model reads happen before the DB write lock. A failed write adopts nothing.
    prepared = prepare(rc, cross_check)
    stats = dict.fromkeys(('verified', 'unverified', 'conflict', 'unknown'), 0)
    reasons: dict[str, int] = {}
    issues, replayed = [], 0
    with rc.db.tx():
        for item in prepared:
            if item.get('replay') or rc.db.one('SELECT id FROM facts WHERE id=?', (item['id'],)):
                replayed += 1
                stats[item['status']] += 1
                continue
            fact = item['proposal']
            try:
                entity = entity_for(rc, fact['entity'], fact['drug'])
                if (fact['field'].startswith(('design.', 'trial.', 'status.trial'))
                        and not any(e['id'] == entity for e in rc.db.entities(rc.project_id, 'trial'))):
                    raise ValueError('试验设计事实需要明确的研究实体')
            except ValueError as exc:
                issues.append({**{k: fact[k] for k in ('entity', 'drug', 'field')}, 'reason': str(exc)})
                continue
            context = {key: fact[key] for key in CONTEXT_KEYS if fact.get(key) is not None}
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
            stats[status] += 1
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
            rc.db.add_fact({'id': item['id'], 'project_id': rc.project_id, 'entity_id': entity,
                'field': fact['field'], 'value': fact['value'], 'tier': tier_of(fact['field']), 'status': status,
                'source_id': item['source_id'], 'quote': fact.get('quote'),
                'quote_start': item['quote_start'], 'quote_end': item['quote_end'],
                'context': {**context, 'source_url': fact['source_url'], 'verify_note': reason,
                            'proposed_supersedes': fact.get('supersedes')},
                'extracted_by': f"llm:{fact.get('extraction_model', getattr(rc.llm, 'model', 'llm'))}",
                'supersedes': supersedes})
    return {'stats': stats, 'reasons': reasons, 'identity_issues': issues,
            'unresolved_entities': len(issues), 'replayed': replayed}
