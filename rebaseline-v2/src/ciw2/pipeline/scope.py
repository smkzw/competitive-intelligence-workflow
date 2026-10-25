"""Complete, bounded scope review with literal candidate identity and same-run recovery.

Drug review stays on drug entities. Trials with no drug parent are a separate candidate_kind='trial' pass.
Each candidate carries only exact source-bound registry observations read from this project's CAS.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ciw2.domain.identity import CODE_HASH as IDENTITY_CODE_HASH
from ciw2.domain.identity import literal_names, name_key, name_owners
from ciw2.domain.models import ScopeResult
from ciw2.harness.agent import HARNESS_RULES
from ciw2.pipeline import scope_context, stage_versions, tool_versions
from ciw2.pipeline.context import RunContext
from ciw2.pipeline.recovery import get_unit, put_unit

CODE_HASH = hashlib.sha256(Path(__file__).read_bytes() + Path(scope_context.__file__).read_bytes()
                           + IDENTITY_CODE_HASH.encode()).hexdigest()
TASK_CHARS = 60000
BATCH_SIZE = 30
RECEIPT_LAYOUT = 'scope-batch-dependencies-v1'
_SOURCE_ID_KEYS = frozenset({'source_id', 'source_ids', 'registry_source_id', 'registry_source_ids'})
_EXPANSION_ROUTE = re.compile(
    r'((?:china|global):expand:(?:alias|target|company)):[0-9a-f]{16}((?::(?:browser|site))?)')


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


def _dependencies(task: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Explicit candidate evidence URLs and source ids carried by this exact task."""
    urls: set[str] = set()
    source_ids: set[str] = set()

    def walk(value: Any, key: str = '') -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, str(child_key))
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str):
            text = value.strip()
            if text.startswith(('http://', 'https://')):
                urls.add(text)
            elif key in _SOURCE_ID_KEYS and text:
                source_ids.add(text)

    for candidate in task.get('candidates', []):
        walk(candidate.get('attrs') or {})
    return sorted(source_ids), sorted(urls)


def _batch_key(rc: RunContext, task: dict[str, Any]) -> str:
    """Same-run identity only. Source versions are checked by the receipt, not the key."""
    skill = rc.skills['coverage-review']
    signature = {'layout': RECEIPT_LAYOUT, 'run': rc.run_id, 'project': rc.project_id, 'task': task,
                 'code': CODE_HASH, 'rules': HARNESS_RULES, 'skill': skill.body,
                 'schema': ScopeResult.model_json_schema(), 'model': rc.settings.llm_model,
                 'execution': tool_versions.shared_execution_digest(),
                 'tools': [tool_versions.tool_binding(rc, name) for name in skill.tools],
                 'source_policy': stage_versions.module_digest('ciw2.pipeline.recovery')}
    return 'scope_batch:' + hashlib.sha256(_json(signature).encode()).hexdigest()


def _review_batch(rc: RunContext, task: dict[str, Any]) -> dict[str, Any]:
    skill = rc.skills['coverage-review']
    key = _batch_key(rc, task)
    cached = get_unit(rc, key)
    if cached is not None:
        return cached
    # A failed or mocked call must not lend its read set to the next batch.
    rc.cache.pop('last_skill_source_ids', None)
    result = ScopeResult.model_validate(rc.skill(skill.name, task))
    normalized = _resolve(result, task['candidates'], set(task['ambiguous_names']))
    if normalized['issues']:
        return normalized
    cited_ids, cited_urls = _dependencies(task)
    read_ids = sorted(set(cited_ids) | set(rc.cache.get('last_skill_source_ids', [])))
    if any(rc.db.one('SELECT id FROM sources WHERE project_id=? AND id=?',
                     (rc.project_id, sid)) is None for sid in read_ids):
        return normalized  # Missing/foreign pointers must not disappear into an empty reusable receipt.
    put_unit(rc, key, normalized, source_ids=read_ids, urls=cited_urls)
    return normalized


def _route_group(route_id: str) -> str:
    """Fold only the per-query expansion digest; keep region, tool and transport exact."""
    match = _EXPANSION_ROUTE.fullmatch(route_id)
    return ''.join(match.groups()) if match else route_id


def _coverage(rc: RunContext) -> dict[str, Any]:
    """Bounded route statistics for the review input; the exact coverage table stays intact.

    A terminal run records one row per expanded query, so the literal rows outgrow every
    task by themselves.  The Skill only needs to know which route families ran, with what
    status, and how many queries/hits they produced; every exact row remains queryable in
    this run's coverage table.  Totals and per-group counts are exact, not sampled.
    """
    rows = rc.db.query(
        'SELECT route_id, region, status, SUM(hits) hits, COUNT(*) n FROM coverage '
        'WHERE run_id=? GROUP BY route_id, region, status ORDER BY route_id, region, status', (rc.run_id,))
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (_route_group(row['route_id']), row['region'], row['status'])
        group = groups.setdefault(key, {'group': key[0], 'region': key[1], 'status': key[2],
                                        'routes': 0, 'rows': 0, 'hits': 0})
        group['routes'] += 1
        group['rows'] += row['n']
        group['hits'] += row['hits']
    return {'layout': 'route-groups-v1', 'route_rows': len(rows),
            'rows': sum(row['n'] for row in rows), 'hits': sum(row['hits'] for row in rows),
            'groups': [groups[key] for key in sorted(groups)]}


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
    # Validate every complete input before the first model call.
    tasks = _tasks(base, scope_context.attach(rc, entities))
    output = _apply(rc, tasks, empty=not entities, bounded=candidate_kind is not None)
    if candidate_kind:
        output['candidate_kind'] = candidate_kind
    return output


def review_scope(rc: RunContext, indication: str) -> dict[str, Any]:
    return _review(rc, indication, rc.db.entities(rc.project_id, 'drug'), candidate_kind=None)


def review_orphan_trials(rc: RunContext, indication: str) -> dict[str, Any]:
    """Scope-review trials that have no project drug-trial parent. Counts stay separate from drug review."""
    return _review(rc, indication, _orphan_trials(rc), candidate_kind='trial')
