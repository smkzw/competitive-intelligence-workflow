"""Scope review receives exact selected CT.gov observations from local CAS.

The projection is read-only: it forwards original registry fields for linked trials,
never decides medical relevance, never rewrites entity attrs or the database, and
never cites a stale version of a URL. The family builds every registered document
inline, so it runs from a clean checkout without private workspace data.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ciw2.domain.identity import CODE_HASH as IDENTITY_CODE_HASH
from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import scope, scope_context
from ciw2.service import Service
from ciw2.sources.http import register_text

API = 'https://clinicaltrials.gov/api/v2/studies'
SEARCH = API + '?pageSize=100&query.cond=Pain'
TABLES = ('projects', 'runs', 'stages', 'agent_steps', 'sources', 'entities', 'links', 'facts', 'coverage')


def nct_url(nct):
    return f'{API}/{nct}'


def opened(settings, names=(), *, focus=''):
    service = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = service.create_project('适应症', ['C'], focus=focus)
    rid = service.db.create_run(pid)
    for name in names:
        service.db.upsert_entity(pid, 'drug', name)
    rc = service.context(pid, rid)
    rc.stage = 'coverage_review'
    return service, rc


def study(nct, conditions=('Pain',), *, study_type='INTERVENTIONAL', purpose='TREATMENT',
          healthy=False, include_healthy=True):
    """Minimal representative registered study; the noise proves only selected fields travel."""
    module = {
        'identificationModule': {'nctId': nct, 'briefTitle': f'{nct} synthetic title'},
        'conditionsModule': {'conditions': list(conditions)},
        'designModule': {'studyType': study_type, 'designInfo': {'primaryPurpose': purpose}},
    }
    if include_healthy:
        module['eligibilityModule'] = {'healthyVolunteers': healthy}
    noise = {'outcomeMeasuresModule': {'outcomeMeasures': [{'title': 'not forwarded outcome'}]}}
    return {'protocolSection': module, 'resultsSection': noise}


def published(rc, url, payload=None, *, raw=None):
    body = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode()
    return register_text(rc.tool_ctx(), kind='ctgov', url=url, text=body.decode('utf-8'))


def linked(rc, drug_name, nct, *, attrs=None):
    drug, _ = rc.db.upsert_entity(rc.project_id, 'drug', drug_name)
    trial, _ = rc.db.upsert_entity(rc.project_id, 'trial', nct,
                                   attrs=attrs if attrs is not None else {'conditions': ['lead only']})
    rc.db.link(rc.project_id, drug, 'drug-trial', trial)
    return drug, trial


def patched(monkeypatch, rc):
    tasks = []

    def skill(name, task):
        tasks.append(copy.deepcopy(task))
        return ScopeResult(decisions=[
            ScopeDecision(entity_id=item['entity_id'], drug=item['name'], in_scope=True,
                          reason='测试用范围结论') for item in task['candidates']])

    monkeypatch.setattr(rc, 'skill', skill)
    return tasks


def snapshot(db):
    return {table: db.query(f'SELECT * FROM {table} ORDER BY rowid') for table in TABLES}


def observations(candidate):
    return candidate['attrs'].get('registry_observations')


def test_linked_drug_candidate_receives_only_the_exact_registered_fields(settings, monkeypatch):
    _, rc = opened(settings)
    drug, _ = linked(rc, 'Capsaicin 8%', 'NCT01533428')
    sid = published(rc, nct_url('NCT01533428'), study(
        'NCT01533428', ['Diabetic Peripheral Neuropathy', 'Pain'], healthy=False))
    tasks = patched(monkeypatch, rc)

    result = scope.review_scope(rc, '适应症')

    candidate = tasks[0]['candidates'][0]
    projection = observations(candidate)
    group = projection['groups'][0]
    assert projection['registry'] == 'ctgov' and len(projection['groups']) == 1
    assert set(group) == {'conditions', 'studyType', 'primaryPurpose', 'healthyVolunteers', 'studies'}
    assert group['conditions'] == ['Diabetic Peripheral Neuropathy', 'Pain']
    assert group['studyType'] == 'INTERVENTIONAL' and group['primaryPurpose'] == 'TREATMENT'
    assert group['healthyVolunteers'] is False
    assert group['studies'] == [{'nct': 'NCT01533428', 'source_id': sid, 'json': 'protocolSection',
                                 'url': nct_url('NCT01533428')}]
    assert candidate['entity_id'] == drug and result['in_scope'] == 1
    assert 'not forwarded outcome' not in scope._json(tasks[0])


def test_search_endpoint_snapshot_alone_produces_source_bound_context(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    sid = published(rc, SEARCH, {'studies': [
        study('NCT00000009', ['Other disease']),
        study('NCT00000001', ['Search-only condition']),
    ]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    group = observations(tasks[0]['candidates'][0])['groups'][0]
    assert group['conditions'] == ['Search-only condition']
    assert group['studies'] == [{'nct': 'NCT00000001', 'source_id': sid,
                                 'json': 'studies[1].protocolSection', 'url': SEARCH}]


def test_conflicting_current_sources_are_both_kept_without_ranking(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    per_nct = published(rc, nct_url('NCT00000001'), study('NCT00000001', ['Per-NCT condition']))
    search = published(rc, SEARCH, {'studies': [study('NCT00000001', ['Search-page condition'])]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    groups = observations(tasks[0]['candidates'][0])['groups']
    by_condition = {tuple(group['conditions']): group for group in groups}
    assert set(by_condition) == {('Per-NCT condition',), ('Search-page condition',)}
    assert by_condition[('Per-NCT condition',)]['studies'][0]['source_id'] == per_nct
    assert by_condition[('Search-page condition',)]['studies'][0]['source_id'] == search


def test_a_stale_same_url_version_is_never_cited(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    stale = published(rc, SEARCH, {'studies': [study('NCT00000001', ['Stale condition'])]})
    current = published(rc, SEARCH, {'studies': [study('NCT00000001', ['Current condition'])]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    group = observations(tasks[0]['candidates'][0])['groups'][0]
    assert group['conditions'] == ['Current condition']
    assert group['studies'][0]['source_id'] == current
    assert group['studies'][0]['source_id'] != stale


@pytest.mark.parametrize('kind', ['foreign', 'nonofficial_host', 'http_scheme', 'wrong_path', 'study_query'])
def test_foreign_or_nonofficial_sources_cannot_supply_context(settings, monkeypatch, kind):
    service, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    if kind == 'foreign':
        other = service.create_project('其他适应症', ['C'])
        published(service.context(other, service.db.create_run(other)), SEARCH,
                  {'studies': [study('NCT00000001', ['Foreign condition'])]})
    elif kind == 'nonofficial_host':
        published(rc, 'https://example.org/api/v2/studies?pageSize=100',
                  {'studies': [study('NCT00000001', ['Unofficial condition'])]})
    elif kind == 'http_scheme':
        published(rc, 'http://clinicaltrials.gov/api/v2/studies?pageSize=100',
                  {'studies': [study('NCT00000001', ['Plain HTTP condition'])]})
    elif kind == 'wrong_path':
        published(rc, 'https://clinicaltrials.gov/api/v2/other',
                  {'studies': [study('NCT00000001', ['Wrong path condition'])]})
    else:
        published(rc, nct_url('NCT00000001') + '?pageSize=100', study('NCT00000001', ['Queried study']))
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    assert 'registry_observations' not in tasks[0]['candidates'][0]['attrs']


@pytest.mark.parametrize('mode', ['not_json', 'missing_cas', 'digest_mismatch'])
def test_malformed_or_unverifiable_search_payloads_are_ignored(settings, monkeypatch, mode):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    if mode == 'not_json':
        published(rc, SEARCH, raw=b'not json at all')
    elif mode == 'missing_cas':
        rc.db.add_source(rc.project_id, 'ctgov', SEARCH, 'b' * 64)
    else:
        sid = published(rc, SEARCH, {'studies': [study('NCT00000001', ['Tampered condition'])]})
        digest = rc.db.one('SELECT digest FROM sources WHERE id=?', (sid,))['digest']
        real = rc.cas.get
        monkeypatch.setattr(rc.cas, 'get', lambda value: b'{}' if value == digest else real(value))
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    assert 'registry_observations' not in tasks[0]['candidates'][0]['attrs']


def test_identical_observations_keep_every_study_and_every_source(settings, monkeypatch):
    _, rc = opened(settings)
    names = ['NCT00000001', 'NCT00000002', 'NCT00000003']
    for nct in names:
        linked(rc, 'DrugA', nct)
    search = published(rc, SEARCH, {'studies': [study(nct, ['Shared condition']) for nct in names]})
    per_nct = published(rc, nct_url('NCT00000002'), study('NCT00000002', ['Shared condition']))
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    task = tasks[0]
    groups = observations(task['candidates'][0])['groups']
    assert len(groups) == 1
    entries = groups[0]['studies']
    assert sorted(item['nct'] for item in entries) == sorted([*names, 'NCT00000002'])
    assert {item['source_id'] for item in entries} == {search, per_nct}
    assert len({(item['nct'], item['source_id'], item['json']) for item in entries}) == 4
    assert entries == sorted(entries, key=lambda item: (item['nct'], item['url'], item['source_id'], item['json']))
    assert len(scope._json(task)) <= scope.TASK_CHARS


def test_projection_is_deterministic_and_mutates_neither_inputs_nor_the_database(settings):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000002')
    linked(rc, 'DrugA', 'NCT00000001')
    published(rc, SEARCH, {'studies': [study('NCT00000001', ['Pain']), study('NCT00000002', ['Pain'])]})
    published(rc, nct_url('NCT00000001'), study('NCT00000001', ['Pain']))
    candidates = rc.db.entities(rc.project_id, 'drug')
    before, rows = copy.deepcopy(candidates), snapshot(rc.db)

    first = scope_context.attach(rc, candidates)
    second = scope_context.attach(rc, candidates)

    assert first == second and candidates == before and snapshot(rc.db) == rows
    assert first[0]['attrs'] is not candidates[0]['attrs']
    assert 'registry_observations' in first[0]['attrs'] and 'registry_observations' not in candidates[0]['attrs']


def test_false_healthy_volunteers_differs_from_an_absent_field(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    linked(rc, 'DrugA', 'NCT00000002')
    published(rc, SEARCH, {'studies': [
        study('NCT00000001', ['Pain'], healthy=False),
        study('NCT00000002', ['Pain'], include_healthy=False),
    ]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    groups = observations(tasks[0]['candidates'][0])['groups']
    assert len(groups) == 2
    present = next(item for item in groups if 'healthyVolunteers' in item)
    absent = next(item for item in groups if 'healthyVolunteers' not in item)
    assert present['healthyVolunteers'] is False and present['studies'][0]['nct'] == 'NCT00000001'
    assert absent['studies'][0]['nct'] == 'NCT00000002'


def test_literal_conditions_keep_commas_and_source_order(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    published(rc, SEARCH, {'studies': [study('NCT00000001', ['Pain, neuropathic', 'Diabetic neuropathy'])]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    assert observations(tasks[0]['candidates'][0])['groups'][0]['conditions'] == [
        'Pain, neuropathic', 'Diabetic neuropathy']


def test_orphan_trial_candidate_uses_its_own_exact_nct_not_entity_leads(settings, monkeypatch):
    _, rc = opened(settings, focus='仅复核未挂药物的试验')
    rc.db.upsert_entity(rc.project_id, 'trial', 'NCT00000001', attrs={'conditions': ['Lead only']})
    rc.db.upsert_entity(rc.project_id, 'trial', 'NCT-DEVICE', attrs={'conditions': ['Device lead']})
    sid = published(rc, SEARCH, {'studies': [study('NCT00000001', ['Registered condition'])]})
    tasks = patched(monkeypatch, rc)

    result = scope.review_orphan_trials(rc, '适应症')

    by_name = {item['name']: item for item in tasks[0]['candidates']}
    group = observations(by_name['NCT00000001'])['groups'][0]
    assert group['conditions'] == ['Registered condition'] and group['studies'][0]['source_id'] == sid
    assert 'registry_observations' not in by_name['NCT-DEVICE']['attrs']
    assert result['in_scope'] == 2


def test_only_project_linked_trials_with_registered_bytes_are_forwarded(settings, monkeypatch):
    service, rc = opened(settings, ['Linked', 'Unregistered', 'Foreign', 'Unlinked'])
    linked(rc, 'Linked', 'NCT00000001')
    published(rc, SEARCH, {'studies': [study('NCT00000001', ['Forwarded condition'])]})
    linked(rc, 'Unregistered', 'NCT00000002', attrs={'conditions': ['Lead must not become fact']})
    foreign_drug, _ = rc.db.upsert_entity(rc.project_id, 'drug', 'Foreign')
    foreign = service.create_project('其他适应症', ['C'])
    foreign_trial, _ = service.db.upsert_entity(foreign, 'trial', 'NCT00000003')
    service.db.add_source(foreign, 'ctgov', SEARCH, 'a' * 64)
    rc.db.link(rc.project_id, foreign_drug, 'drug-trial', foreign_trial)
    service.db.upsert_entity(rc.project_id, 'trial', 'NCT00000004')
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    by_name = {item['name']: item for item in tasks[0]['candidates']}
    assert set(by_name) == {'Linked', 'Unregistered', 'Foreign', 'Unlinked'}
    assert observations(by_name['Linked'])['groups'][0]['conditions'] == ['Forwarded condition']
    for name in ('Unregistered', 'Foreign', 'Unlinked'):
        assert 'registry_observations' not in by_name[name]['attrs']


def test_registry_observations_are_forwarded_without_medical_filtering(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    published(rc, SEARCH, {'studies': [study(
        'NCT00000001', ['Unrelated disease'], study_type='OBSERVATIONAL',
        purpose='SUPPORTIVE_CARE', healthy=True)]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    group = observations(tasks[0]['candidates'][0])['groups'][0]
    assert group['conditions'] == ['Unrelated disease'] and group['studyType'] == 'OBSERVATIONAL'
    assert group['primaryPurpose'] == 'SUPPORTIVE_CARE' and group['healthyVolunteers'] is True


def test_a_new_version_reviews_again_but_an_unrelated_official_source_does_not(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    published(rc, SEARCH, {'studies': [study('NCT00000001', ['First condition'])]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')
    scope.review_scope(rc, '适应症')
    assert len(tasks) == 1
    published(rc, API + '?pageSize=100&query.cond=Other',
              {'studies': [study('NCT00000009', ['Unrelated condition'])]})
    scope.review_scope(rc, '适应症')
    assert len(tasks) == 1

    sid = published(rc, SEARCH, {'studies': [study('NCT00000001', ['Second condition'])]})

    scope.review_scope(rc, '适应症')

    assert len(tasks) == 2
    group = observations(tasks[-1]['candidates'][0])['groups'][0]
    assert group['conditions'] == ['Second condition'] and group['studies'][0]['source_id'] == sid


def test_projection_sources_become_this_batch_dependencies(settings, monkeypatch):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    per_nct = published(rc, nct_url('NCT00000001'), study('NCT00000001', ['Pain']))
    search = published(rc, SEARCH, {'studies': [study('NCT00000001', ['Pain'])]})
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    ids, urls = scope._dependencies(tasks[0])
    assert set(ids) == {per_nct, search} and set(urls) == {nct_url('NCT00000001'), SEARCH}


def test_a_source_registered_without_an_observation_step_is_still_read(settings):
    _, rc = opened(settings)
    linked(rc, 'DrugA', 'NCT00000001')
    body = json.dumps({'studies': [study('NCT00000001', ['Legacy registered condition'])]}).encode()
    digest = rc.cas.put(body)
    sid = rc.db.add_source(rc.project_id, 'ctgov', SEARCH, digest, text_digest=digest)
    candidates = rc.db.entities(rc.project_id, 'drug')

    projected = scope_context.attach(rc, candidates)

    group = observations(projected[0])['groups'][0]
    assert group['conditions'] == ['Legacy registered condition']
    assert group['studies'][0]['source_id'] == sid


def test_candidates_without_context_keep_the_existing_shape(settings, monkeypatch):
    _, rc = opened(settings, ['DrugA'])
    tasks = patched(monkeypatch, rc)

    scope.review_scope(rc, '适应症')

    candidate = tasks[0]['candidates'][0]
    assert set(candidate) == {'name', 'name_zh', 'aliases', 'attrs', 'found_by', 'entity_id'}
    assert candidate['attrs'] == {}


def test_overflow_remains_an_explicit_error_and_is_not_truncated(settings, monkeypatch):
    _, rc = opened(settings)
    studies = []
    for index in range(40):
        nct = f'NCT{index:08d}'
        linked(rc, 'DrugA', nct)
        studies.append(study(nct, [f'Long registered condition {index} ' * 60]))
    published(rc, SEARCH, {'studies': studies})
    tasks = patched(monkeypatch, rc)

    with pytest.raises(ValueError, match='复核输入'):
        scope.review_scope(rc, '适应症')
    assert tasks == []


def test_scope_code_hash_binds_the_projection_helper_bytes():
    expected = hashlib.sha256(
        Path(scope.__file__).read_bytes() + Path(scope_context.__file__).read_bytes()
        + IDENTITY_CODE_HASH.encode()).hexdigest()
    assert scope.CODE_HASH == expected
