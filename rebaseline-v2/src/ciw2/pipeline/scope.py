"""Complete, bounded scope review with literal candidate identity and same-run recovery."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ciw2.domain.models import ScopeResult
from ciw2.harness.agent import HARNESS_RULES
from ciw2.pipeline.context import RunContext

CODE_HASH = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
TASK_CHARS = 60000
BATCH_SIZE = 30


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _tasks(base: dict[str, Any], drugs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def task(items: list[dict[str, Any]]) -> dict[str, Any]:
        return {**base, 'candidates': items}

    def check(value: dict[str, Any]) -> None:
        if len(_json(value)) > TASK_CHARS:
            raise ValueError('复核输入超过整包预算；保留完整候选及上下文，不截断或丢弃候选')

    check(task([]))
    batches, pending = [], []
    for drug in drugs:
        candidate = {key: drug[key] for key in ('name', 'name_zh', 'aliases', 'attrs', 'found_by')}
        candidate['entity_id'] = drug['id']
        proposed = [*pending, candidate]
        if len(proposed) > BATCH_SIZE or len(_json(task(proposed))) > TASK_CHARS:
            if pending:
                batches.append(task(pending))
            proposed = [candidate]
        check(task(proposed))
        pending = proposed
    if pending:
        batches.append(task(pending))
    return batches


def _names(candidate: dict[str, Any]) -> set[str]:
    return {name.strip().casefold() for name in
            [candidate['name'], candidate['name_zh'], *candidate['aliases']] if name and name.strip()}


def _resolve(result: ScopeResult, candidates: list[dict[str, Any]], ambiguous_names: set[str]) -> dict[str, Any]:
    by_id = {item['entity_id']: item for item in candidates}
    matched: dict[str, list[Any]] = {eid: [] for eid in by_id}
    invalid, issues = set(), []
    for decision in result.decisions:
        name = decision.drug.strip().casefold()
        ids = [eid for eid, item in by_id.items() if name in _names(item)]
        if decision.entity_id is not None:
            eid = decision.entity_id
            if eid not in by_id or eid not in ids:
                issues.append({'kind': 'invalid_binding', 'entity_id': eid, 'drug': decision.drug})
                if eid in by_id:
                    invalid.add(eid)
                continue
        elif len(ids) == 1 and name not in ambiguous_names:
            eid = ids[0]
        else:
            issues.append({'kind': 'ambiguous_name' if ids else 'unknown_name', 'drug': decision.drug})
            invalid.update(ids)
            continue
        matched[eid].append(decision)
    normalized, applied = [], 0
    for eid, responses in matched.items():
        reason = '复核未返回该候选结论'
        state = None
        if len(responses) > 1:
            issues.append({'kind': 'duplicate_decision', 'entity_id': eid})
            reason = '同一候选返回多条结论，待重新核实'
        elif eid in invalid:
            reason = '候选身份关联不一致，待重新核实'
        elif len(responses) == 1:
            state, reason = responses[0].in_scope, responses[0].reason
            applied += 1
        else:
            issues.append({'kind': 'missing_decision', 'entity_id': eid})
        normalized.append({'entity_id': eid, 'in_scope': state, 'reason': reason})
    return {'decisions': normalized, 'applied': applied, 'issues': issues}


def _review_batch(rc: RunContext, task: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    skill = rc.skills['coverage-review']
    signature = {'task': task, 'sources': sources, 'code': CODE_HASH, 'rules': HARNESS_RULES,
                 'skill': skill.body, 'schema': ScopeResult.model_json_schema(), 'model': rc.settings.llm_model}
    digest = hashlib.sha256(_json(signature).encode()).hexdigest()
    key = f'scope_batch:{digest}'
    cached = rc.db.stage_output(rc.run_id, key)
    if cached is not None:
        rc.db.log_step(rc.run_id, rc.stage, skill.name, 0, 'cache', {'reused_stage': key})
        return cached
    result = ScopeResult.model_validate(rc.skill(skill.name, task))
    normalized = _resolve(result, task['candidates'], set(task['ambiguous_names']))
    if not normalized['issues']:
        rc.db.set_stage(rc.run_id, key, 'succeeded', output=normalized)
    return normalized


def review_scope(rc: RunContext, indication: str) -> dict[str, Any]:
    drugs = rc.db.entities(rc.project_id, 'drug')
    owners: dict[str, set[str]] = {}
    for drug in drugs:
        for name in _names(drug):
            owners.setdefault(name, set()).add(drug['id'])
    base = {'indication': indication, 'focus': rc.project['focus'],
            'ambiguous_names': sorted(name for name, ids in owners.items() if len(ids) > 1), 'coverage': rc.db.query(
        'SELECT route_id, region, status, SUM(hits) hits, COUNT(*) n FROM coverage '
        'WHERE run_id=? GROUP BY route_id, region, status ORDER BY route_id, region, status', (rc.run_id,))}
    tasks = _tasks(base, drugs)  # Validate every complete input before the first model call.
    sources = rc.db.query('SELECT id, digest, text_digest FROM sources WHERE project_id=? ORDER BY id',
                          (rc.project_id,))
    output = {'decisions': 0, 'in_scope': 0, 'excluded': 0, 'pending': 0,
              'issues': [], 'batches': len(tasks), 'input_empty': not drugs}
    for task in tasks:
        result = _review_batch(rc, task, sources)
        output['decisions'] += result['applied']
        output['issues'].extend(result['issues'])
        with rc.db.tx():
            for decision in result['decisions']:
                rc.db.set_scope(decision['entity_id'], decision['in_scope'], decision['reason'])
                key = 'pending' if decision['in_scope'] is None else 'in_scope' if decision['in_scope'] else 'excluded'
                output[key] += 1
    return output
