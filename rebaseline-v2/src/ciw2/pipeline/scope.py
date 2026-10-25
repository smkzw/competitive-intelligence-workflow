"""Complete, bounded scope review with literal candidate identity and same-run recovery.

Drug review stays on drug entities. Trials with no drug parent are a separate candidate_kind='trial' pass.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ciw2.domain.identity import CODE_HASH as IDENTITY_CODE_HASH
from ciw2.domain.identity import literal_names, name_key, name_owners
from ciw2.domain.models import ScopeResult
from ciw2.harness.agent import HARNESS_RULES
from ciw2.pipeline.context import RunContext

CODE_HASH = hashlib.sha256(Path(__file__).read_bytes() + IDENTITY_CODE_HASH.encode()).hexdigest()
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


def _resolve(result: ScopeResult, candidates: list[dict[str, Any]], ambiguous_names: set[str]) -> dict[str, Any]:
    by_id = {item['entity_id']: item for item in candidates}
    matched: dict[str, list[Any]] = {eid: [] for eid in by_id}
    invalid, issues = set(), []
    for decision in result.decisions:
        name = name_key(decision.drug)
        ids = [eid for eid, item in by_id.items() if name in literal_names(item)]
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


def _batch_key(rc: RunContext, task: dict[str, Any], sources: list[dict[str, Any]]) -> str:
    skill = rc.skills['coverage-review']
    signature = {'task': task, 'sources': sources, 'code': CODE_HASH, 'rules': HARNESS_RULES,
                 'skill': skill.body, 'schema': ScopeResult.model_json_schema(), 'model': rc.settings.llm_model}
    return 'scope_batch:' + hashlib.sha256(_json(signature).encode()).hexdigest()


def _review_batch(rc: RunContext, task: dict[str, Any]) -> dict[str, Any]:
    skill = rc.skills['coverage-review']
    cached_key = _batch_key(rc, task, _sources(rc))
    cached = rc.db.stage_output(rc.run_id, cached_key)
    if cached is not None:
        rc.db.log_step(rc.run_id, rc.stage, skill.name, 0, 'cache', {'reused_stage': cached_key})
        return cached
    result = ScopeResult.model_validate(rc.skill(skill.name, task))
    normalized = _resolve(result, task['candidates'], set(task['ambiguous_names']))
    if not normalized['issues']:
        # The call may register sources. Bind the receipt to the set present after it returns.
        rc.db.set_stage(rc.run_id, _batch_key(rc, task, _sources(rc)), 'succeeded', output=normalized)
    return normalized


def _coverage(rc: RunContext) -> list[dict[str, Any]]:
    return rc.db.query(
        'SELECT route_id, region, status, SUM(hits) hits, COUNT(*) n FROM coverage '
        'WHERE run_id=? GROUP BY route_id, region, status ORDER BY route_id, region, status', (rc.run_id,))


def _sources(rc: RunContext) -> list[dict[str, Any]]:
    return rc.db.query('SELECT id, digest, text_digest FROM sources WHERE project_id=? ORDER BY id', (rc.project_id,))


def _orphan_trials(rc: RunContext) -> list[dict[str, Any]]:
    """Trials with zero project drug parents. An excluded drug parent is still a parent."""
    drugs = {row['id'] for row in rc.db.entities(rc.project_id, 'drug')}
    linked = {edge['dst'] for edge in rc.db.query(
        "SELECT src,dst FROM links WHERE project_id=? AND rel='drug-trial'", (rc.project_id,))
        if edge['src'] in drugs}
    return [trial for trial in rc.db.entities(rc.project_id, 'trial') if trial['id'] not in linked]


def _apply(rc: RunContext, tasks: list[dict[str, Any]], *,
           empty: bool, bounded: bool) -> dict[str, Any]:
    output = {'decisions': 0, 'in_scope': 0, 'excluded': 0, 'pending': 0,
              'issues': [], 'batches': len(tasks), 'input_empty': empty}
    for task in tasks:
        if bounded:
            rc.check_cancelled()  # Stop before the next model call; completed batches stay committed.
        result = _review_batch(rc, task)
        output['decisions'] += result['applied']
        output['issues'].extend(result['issues'])
        with rc.db.tx():
            for decision in result['decisions']:
                rc.db.set_scope(decision['entity_id'], decision['in_scope'], decision['reason'])
                key = 'pending' if decision['in_scope'] is None else 'in_scope' if decision['in_scope'] else 'excluded'
                output[key] += 1
    return output


def _review(rc: RunContext, indication: str, entities: list[dict[str, Any]], *,
            candidate_kind: str | None) -> dict[str, Any]:
    owners = name_owners(entities)
    base = {'indication': indication, 'focus': rc.project['focus'],
            'ambiguous_names': sorted(name for name, ids in owners.items() if len(ids) > 1),
            'coverage': _coverage(rc)}
    if candidate_kind:
        base['candidate_kind'] = candidate_kind
    tasks = _tasks(base, entities)  # Validate every complete input before the first model call.
    output = _apply(rc, tasks, empty=not entities, bounded=candidate_kind is not None)
    if candidate_kind:
        output['candidate_kind'] = candidate_kind
    return output


def review_scope(rc: RunContext, indication: str) -> dict[str, Any]:
    return _review(rc, indication, rc.db.entities(rc.project_id, 'drug'), candidate_kind=None)


def review_orphan_trials(rc: RunContext, indication: str) -> dict[str, Any]:
    """Scope-review trials that have no project drug-trial parent. Counts stay separate from drug review."""
    return _review(rc, indication, _orphan_trials(rc), candidate_kind='trial')
