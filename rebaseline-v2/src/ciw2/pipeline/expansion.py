"""Code-planned source expansion; existing tools, Skills, CAS and stages only."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from ciw2.domain.identity import CODE_HASH as IDENTITY_HASH
from ciw2.domain.identity import name_key, research_aliases
from ciw2.domain.models import UniverseResult
from ciw2.harness.agent import HARNESS_RULES
from ciw2.pipeline.context import IncompleteWork, RunContext, work_limit
from ciw2.pipeline.queries import intake_data
from ciw2.pipeline.recovery import fingerprint, get_unit, put_unit
from ciw2.sources import cde_browser, china, ctgov, websearch
from ciw2.sources.china_browser import CODE_HASH as CHINA_BROWSER_HASH
from ciw2.sources.http import FetchError

CODE_HASH = hashlib.sha256(Path(__file__).read_bytes() + IDENTITY_HASH.encode() +
    ctgov.EXTRACTOR_VERSION.encode() + Path(china.__file__).read_bytes() +
    Path(websearch.__file__).read_bytes() + CHINA_BROWSER_HASH.encode() + cde_browser.code_hash().encode()).hexdigest()


def _seeds(rc: RunContext) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for drug in rc.db.entities(rc.project_id, 'drug'):
        if drug['in_scope'] == 0:
            continue
        fields = {'alias': research_aliases([drug['name'], drug['name_zh'], *drug['aliases']]),
                  'target': drug['attrs'].get('targets') or [], 'company': drug['attrs'].get('companies') or []}
        for kind, terms in fields.items():
            for term in terms:
                if not isinstance(term, str) or not name_key(term):
                    continue
                term = term.strip()
                seed = grouped.setdefault((kind, name_key(term)), {'kind': kind, 'term': term, 'owners': []})
                seed['term'] = min(seed['term'], term)
                if drug['id'] not in seed['owners']:
                    seed['owners'].append(drug['id'])
    return sorted(grouped.values(), key=lambda item: (item['kind'], name_key(item['term']), item['term']))


def query_plan(rc: RunContext) -> list[dict[str, Any]]:
    intake = intake_data(rc)
    condition = intake.get('indication_en') or intake['indication']
    plan = []
    for seed in _seeds(rc):
        for region in ('china', 'global'):
            args = {'condition': condition, 'region': region, 'max_results': None,
                    'location': 'China' if region == 'china' else '',
                    'intervention' if seed['kind'] == 'alias' else 'term': seed['term']}
            routes = [('ctgov_search', args)]
            if region == 'china':
                for registry in ('chinadrugtrials','cde','nmpa'):
                    parameters = {'registry':registry,'query':seed['term'] if registry != 'nmpa'
                                  else f"{intake['indication']} {seed['term']}"}
                    if registry == 'cde':
                        parameters['query_kind'] = {'alias':'drug_name','company':'company','target':'target'}[seed['kind']]
                    routes.append(('china_registry_search',parameters))
            else:
                routes.append(('web_search', {'query': f"{condition} {seed['term']}", 'region': region}))
            for tool, arguments in routes:
                digest = fingerprint({'region': region, 'kind': seed['kind'], 'tool': tool, 'arguments': arguments})
                qid = f"{region}:expand:{seed['kind']}:{digest[:16]}"
                plan.append({**seed, 'owners': sorted(seed['owners']), 'region': region, 'tool': tool,
                             'registry': arguments.get('registry'), 'id': qid,
                             'arguments': {**arguments, 'route_id': qid}})
    return plan


def _read_result(rc: RunContext, digest: str) -> Any:
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('扩展检索回执的内容地址无效')
    raw = rc.cas.get(digest)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('扩展检索结果字节不符合回执')
    return json.loads(raw)


def _source_shape(query: dict[str, Any], result: dict[str, Any]) -> bool:
    rows = result.get('studies' if query['tool'] == 'ctgov_search' else 'results')
    count = result.get('count')
    if type(count) is not int or count < 0 or not isinstance(rows, list) or count != len(rows):
        return False
    if any(not isinstance(row, dict) for row in rows):
        return False
    if query['tool'] == 'ctgov_search':
        return isinstance(result.get('interventions'), list)
    return True


def _source(rc: RunContext, query: dict[str, Any], admitted: bool) -> tuple[dict[str, Any], str]:
    key = 'expansion_source:' + fingerprint({'arguments': query['arguments'], 'tool': query['tool'],
        'code': CODE_HASH, 'search_provider': rc.settings.websearch_provider,
        'china_browser_space':rc.settings.china_ego_space_id if query.get('registry') in {'chinadrugtrials','cde'} else None})
    cached = get_unit(rc, key)
    if cached is not None:
        return {**cached, 'payload': _read_result(rc, cached['digest'])}, 'cached'
    if not admitted:
        return {}, 'budget'
    ctx = rc.tool_ctx()
    tool = rc.registry.get(query['tool'])
    try:
        result = tool.fn(ctx, tool.args_model.model_validate(query['arguments']))
    except (FetchError, httpx.HTTPError, china.RegistryBlocked, websearch.SearchBlocked,
            websearch.SearchFailed, ValueError, RuntimeError) as exc:
        rc.db.log_coverage(rc.run_id, query['id'], query['region'], query['term'], 'failed',
                           note=f'扩展来源失败：{type(exc).__name__}')
        return {'error_type': type(exc).__name__}, 'failed'
    if not isinstance(result, dict):
        return {'error_type': 'InvalidSourceShape'}, 'failed'
    status = result.get('status', result.get('mode'))
    if status is not None and not isinstance(status, str):
        return {'error_type': 'InvalidSourceShape'}, 'failed'
    if status in {'blocked', 'failed', 'tool_failed', 'unsupported'}:
        return {}, 'blocked' if status in {'blocked', 'unsupported'} else 'failed'
    if status == 'browser' and result.get('complete') is not True:
        return {'error_type':'IncompleteBrowserCapture'},'failed'
    if status not in {None, 'ok', 'success', 'direct', 'site_search', 'browser'} or not _source_shape(query, result):
        return {'error_type': 'InvalidSourceShape'}, 'failed'
    digest = rc.cas.put(json.dumps(result, ensure_ascii=False).encode())
    sources = sorted((ctx.extra or {}).get('source_ids_read', set()))
    output = {'digest': digest, 'source_ids': sources}
    put_unit(rc, key, output, source_ids=sources)
    return {**output, 'payload': result}, 'fetched'


def _interpret(rc: RunContext, query: dict[str, Any], source: dict[str, Any],
               persist: Callable[[UniverseResult], int]) -> None:
    if query['tool'] == 'ctgov_search':
        return  # The production source tool already persists every provisional intervention and literal alias.
    payload = source['payload']
    if query['tool'] == 'china_registry_search' and payload.get('mode') == 'browser' and payload.get('persisted') is True:
        return  # Structured labels/relations already adopted; scope review still decides scientific inclusion.
    if not payload.get('results'):
        return
    skill = rc.skills[f"universe-{query['region']}"]
    task = {**intake_data(rc), 'mode': 'expansion_results', 'region': query['region'],
            'focus': rc.project['focus'], 'query': query, 'source_hits': payload['results']}
    if len(json.dumps(task, ensure_ascii=False)) > 60000:
        raise ValueError('完整扩展线索包超预算，保留原文及待处理查询，不截断')
    key = 'expansion_interpret:' + fingerprint({'task': task, 'digest': source['digest'], 'code': CODE_HASH,
        'skill': skill.body, 'rules': HARNESS_RULES, 'schema': UniverseResult.model_json_schema(),
        'model': rc.settings.llm_model})
    if get_unit(rc, key) is not None:
        return
    result = rc.skill(skill.name, task)
    if result.region != query['region']:
        raise ValueError('扩展候选返回区域与实际任务不一致')
    sources = set(source['source_ids']) | set(rc.cache.get('last_skill_source_ids', []))
    with rc.db.tx():
        new = persist(result)
        put_unit(rc, key, {'candidates': len(result.candidates), 'new': new}, source_ids=sources,
                 urls=[url for c in result.candidates for url in c.evidence_urls])


def expand_universe(rc: RunContext, persist: Callable[[UniverseResult], int]) -> dict[str, Any]:
    limit = work_limit(rc.cache.get('max_expansion_queries'))
    rounds = work_limit(rc.cache.get('max_expansion_rounds', 3)) or 3
    if rounds > 3:
        raise ValueError('扩展轮次不能超过既定三轮预算')
    seen = set()
    out = {'rounds': 0, 'queries': 0, 'source_attempts': 0, 'reused_queries': 0,
           'completed_queries': [], 'source_issues': [], 'pending_queries': [],
           'expansion_complete': False, 'clinical_universe_accepted': False}

    def pending() -> list[dict[str, Any]]:
        return [q for q in query_plan(rc) if q['id'] not in seen]

    for round_index in range(rounds):
        planned = pending()
        if not planned:
            break
        out['rounds'] = round_index + 1
        for query in planned:
            rc.check_cancelled()
            try:
                source, status = _source(rc, query, limit is None or out['source_attempts'] < limit)
                if status == 'budget':
                    raise ValueError('扩展检索执行预算耗尽')
                out['source_attempts'] += status != 'cached'
                out['reused_queries'] += status == 'cached'
                out['queries'] += 1
                if status in {'blocked', 'failed'}:
                    out['source_issues'].append({'id': query['id'], 'status': status,
                                                'error_type': source.get('error_type')})
                else:
                    _interpret(rc, query, source, persist)
                    out['completed_queries'].append(query['id'])
                seen.add(query['id'])
            except Exception as exc:
                out['pending_queries'] = pending()
                out['error_type'] = type(exc).__name__
                raise IncompleteWork('扩展检索或线索整理未完成；保留已完单元及待处理查询', out) from exc
    out['pending_queries'] = pending()
    if out['pending_queries']:
        raise IncompleteWork('扩展轮次预算已用完，尚有新增线索未查', out)
    out['expansion_complete'] = bool(seen) and not out['source_issues']
    return out
