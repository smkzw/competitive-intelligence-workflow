"""Complete-record extraction batches and recoverable explicit work budgets."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ciw2.domain.models import ExtractionResult
from ciw2.harness.agent import HARNESS_RULES
from ciw2.harness.tools import REGISTRY
from ciw2.pipeline.context import IncompleteWork, RunContext, work_limit
from ciw2.pipeline.queries import drug_trials, intake_data, scoped_drugs
from ciw2.pipeline.recovery import fingerprint, get_unit, put_unit
from ciw2.sources import china_detail
from ciw2.sources.http import source_by_url

CODE_HASH = hashlib.sha256(b''.join(Path(path).read_bytes() for path in (
    __file__, RunContext.skill.__code__.co_filename, put_unit.__code__.co_filename,
    source_by_url.__code__.co_filename))).hexdigest()
TASK_CHARS = 60000


def _tasks(rc: RunContext, skill: str, drug: dict[str, Any], extra: dict[str, Any]) -> list[dict[str, Any]]:
    it = intake_data(rc)
    base = {'indication': it['indication'], 'indication_en': it.get('indication_en'), 'focus': rc.project['focus'],
            'drug': {key: drug[key] for key in ('name', 'name_zh', 'aliases')}}
    refs: dict[str, list[dict[str, Any]]] = {}
    if skill == 'extract-design':
        for fact in rc.db.current_facts(rc.project_id):
            if fact['field'].startswith('design.'):
                refs.setdefault(fact['entity_id'], []).append({
                    **{key: fact[key] for key in ('id', 'entity_id', 'field', 'source_id', 'status')},
                    'read_tool': 'read_project_fact'})

    def task(trials: list[dict[str, Any]]) -> dict[str, Any]:
        ncts = {trial['name'] for trial in trials}
        out = {**base, **{key: [item for item in value if item in ncts]
                         if key in {'trials_with_registry_design', 'trials_with_registry_results'} else value
                         for key, value in extra.items()},
               'known_trials': [{'nct': t['name'], 'entity_id': t['id'],
                                 'title':t['attrs'].get('title') or t['attrs'].get('registry_title'),
                                 **{key:t['attrs'].get(key) for key in ('phase','has_results')},
                                 'detail_tool':'china_trial_detail' if t['attrs'].get('registry_detail_id') else None}
                                for t in trials]}
        if skill == 'extract-design':
            out['existing_design_facts'] = [ref for trial in trials for ref in refs.get(trial['id'], [])]
        return out

    def check(payload: dict[str, Any]) -> None:
        if len(json.dumps(payload, ensure_ascii=False)) > TASK_CHARS:
            raise ValueError('抽取输入超过整包预算；保留完整试验记录和事实，不截断临床定义')

    check(task([]))
    batches, pending = [], []
    for trial in drug_trials(rc, drug['id']):
        proposed = task([*pending, trial])
        if len(json.dumps(proposed, ensure_ascii=False)) > TASK_CHARS and pending:
            batches.append(task(pending))
            pending = []
        pending.append(trial)
        check(task(pending))
    if pending or not batches:
        batches.append(task(pending))
    return batches


def _key(rc: RunContext, skill: str, task: dict[str, Any]) -> str:
    spec = rc.skills[skill]
    signature = {'task': task, 'code': CODE_HASH, 'rules': HARNESS_RULES, 'skill': spec.body,
                 'schema': ExtractionResult.model_json_schema(), 'model': rc.settings.llm_model,
                 'china_detail_version':china_detail.code_hash() if 'china_trial_detail' in spec.tools else None,
                 'tools': [{'schema': REGISTRY.get(name).schema(), 'code': hashlib.sha256(
                     Path(REGISTRY.get(name).fn.__code__.co_filename).read_bytes()).hexdigest()}
                     for name in spec.tools]}
    return f'extraction:{skill}:{fingerprint(signature)}'


def _call(rc: RunContext, skill: str, task: dict[str, Any], key: str) -> dict[str, Any]:
    rc.cache.pop('last_skill_source_ids', None)
    result = ExtractionResult.model_validate(rc.skill(skill, task))
    output = result.model_dump()
    read_ids = set(rc.cache.get('last_skill_source_ids', []))
    read_sources = rc.db.query('SELECT id,url,meta FROM sources WHERE project_id=?', (rc.project_id,))
    for fact in output['facts']:
        candidates=set()
        for source in read_sources:
            if source['id'] not in read_ids or source['url']!=fact['source_url']:
                continue
            scope=json.loads(source['meta']).get('request_context',{})
            if (scope.get('registry')=='chinadrugtrials' and scope.get('section')=='trial_detail'
                    and fact['field'].startswith(('design.','trial.','status.trial'))
                    and scope.get('registry_id')!=fact['entity'].strip().upper()):
                continue
            candidates.add(source['id'])
        supplied=fact.get('source_id')
        fact['source_id'] = (supplied if supplied in candidates else None) if supplied is not None else (
            next(iter(candidates)) if len(candidates) == 1 else None)
    output['extraction_model'] = rc.llm.model
    put_unit(rc, key, output, source_ids=rc.cache.get('last_skill_source_ids', []),
             urls=[fact.source_url for fact in result.facts])
    return output


def extract_drugs(rc: RunContext, skill: str,
                  extra: Callable[[RunContext, dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    limit = work_limit(rc.cache.get('max_drugs'))
    planned = [(drug, _tasks(rc, skill, drug, extra(rc, drug))) for drug in scoped_drugs(rc)]
    output = {'facts': [], 'gaps': [], 'errors': [], 'pending_drug_ids': [], 'pending_units': []}
    started = set()
    for drug, tasks in planned:
        for task in tasks:
            key = _key(rc, skill, task)
            result = get_unit(rc, key)
            if result is None and limit is not None and len(started) >= limit and drug['id'] not in started:
                output['pending_units'].append({'drug_id': drug['id'], 'key': key, 'reason': 'execution_budget'})
                continue
            if result is None:
                started.add(drug['id'])
                try:
                    result = _call(rc, skill, task, key)
                except Exception as exc:  # noqa: BLE001 - isolate a failed batch, retain healthy neighbors
                    output['errors'].append(f"{drug['name']}: {type(exc).__name__}: {exc}")
                    output['pending_units'].append({'drug_id': drug['id'], 'key': key, 'reason': 'unit_failed'})
                    continue
            typed = ExtractionResult.model_validate({'facts': [
                {k: v for k, v in f.items() if k != 'source_id'} for f in result['facts']], 'gaps': result['gaps']})
            output['facts'].extend({**fact.model_dump(), 'drug': drug['name'],
                **({'source_id': raw['source_id']} if 'source_id' in raw else {}),
                'extraction_model': result['extraction_model']} for fact, raw in zip(typed.facts, result['facts'], strict=True))
            output['gaps'].extend(f"{drug['name']}: {gap}" for gap in typed.gaps)
    output['pending_drug_ids'] = sorted({item['drug_id'] for item in output['pending_units']})
    if output['pending_units']:
        raise IncompleteWork(f"药物抽取未完成：{len(output['pending_drug_ids'])}个药物仍有待处理批次", output)
    return output
