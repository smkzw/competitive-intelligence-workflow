"""Terminal-scale scope metadata must stay complete inside one bounded task.

The production failure kept 243 drug candidates and 3068 route rows but built a
352856-character base, so no task could ever be sent.  Route rows are global
retrieval statistics: their exact table stays in the database, while the review
input only needs a bounded, exact-total statistic per route family.  Registry
observations are different: every selected raw field, NCT, source version, JSON
locator and URL association must survive verbatim, so repeated provenance is
factored through an explicit source dictionary instead of truncated.

This family is portable: all sources, CAS bytes and coverage rows are generated
inline; no private workspace data is read.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import scope
from ciw2.service import Service
from ciw2.sources.http import register_text

API = 'https://clinicaltrials.gov/api/v2/studies'
SEARCH = (API + '?pageSize=100&query.cond=Paroxysmal+Nocturnal+Hemoglobinuria'
          '&countTotal=true')
STATUSES = ('ok', 'failed', 'blocked')
CREATED = '2026-01-01T00:00:00+00:00'


def opened(settings, names=(), *, focus='补体通路'):
    service = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = service.create_project('阵发性睡眠性血红蛋白尿症', ['C'], focus=focus)
    rid = service.db.create_run(pid)
    for name in names:
        service.db.upsert_entity(pid, 'drug', name)
    rc = service.context(pid, rid)
    rc.stage = 'coverage_review'
    return service, rc


def add_terminal_routes(rc, count=3068):
    """One row per unique expansion-route hash, plus stable non-expansion anchors."""
    rows = []
    for index in range(count):
        digest = hashlib.sha256(f'expansion-route-{index}'.encode()).hexdigest()[:16]
        transport = ('browser', 'site', '')[index % 3]
        route = f'china:expand:alias:{digest}' + (f':{transport}' if transport else '')
        rows.append((rc.run_id, route, 'china', f'term-{index}',
                     STATUSES[(index // 3) % 3], index % 7, 0, CREATED))
    rows.append((rc.run_id, 'china:cde:indication', 'china', 'indication', 'blocked', 0, 0, CREATED))
    rows.append((rc.run_id, 'global:ctgov:condition', 'global', 'condition', 'ok', 12, 3, CREATED))
    with rc.db.tx() as conn:
        conn.executemany(
            'INSERT INTO coverage (run_id, route_id, region, query, status, hits, new_entities, created_at) '
            'VALUES (?,?,?,?,?,?,?,?)', rows)
    return len(rows)


def study(nct, conditions, *, study_type='INTERVENTIONAL', purpose='TREATMENT',
          healthy=False, include_healthy=True):
    module = {
        'identificationModule': {'nctId': nct, 'briefTitle': f'{nct} title'},
        'conditionsModule': {'conditions': list(conditions)},
        'designModule': {'studyType': study_type, 'designInfo': {'primaryPurpose': purpose}},
    }
    if include_healthy:
        module['eligibilityModule'] = {'healthyVolunteers': healthy}
    return {'protocolSection': module,
            'resultsSection': {'outcomeMeasuresModule': {'outcomeMeasures': [{'title': 'not forwarded'}]}}}


def published(rc, url, payload):
    return register_text(rc.tool_ctx(), kind='ctgov', url=url,
                         text=json.dumps(payload, ensure_ascii=False))


def patched(monkeypatch, rc):
    tasks = []

    def skill(name, task):
        tasks.append(task)
        return ScopeResult(decisions=[
            ScopeDecision(entity_id=item['entity_id'], drug=item['name'], in_scope=True,
                          reason='测试用范围结论') for item in task['candidates']])

    monkeypatch.setattr(rc, 'skill', skill)
    return tasks


@pytest.mark.parametrize(('route', 'group'), [
    ('custom:0123456789abcdef:source', 'custom:0123456789abcdef:source'),
    ('china:cde:0123456789abcdef', 'china:cde:0123456789abcdef'),
    ('global:expand:alias:0123456789abcdef:unexpected',
     'global:expand:alias:0123456789abcdef:unexpected'),
    ('china:expand:alias:0123456789abcdef', 'china:expand:alias'),
    ('china:expand:company:0123456789abcdef:browser', 'china:expand:company:browser'),
    ('global:expand:target:0123456789abcdef:site', 'global:expand:target:site'),
])
def test_route_folding_preserves_every_unrecognized_route_identity(route, group):
    assert scope._route_group(route) == group


def test_terminal_route_volume_becomes_exact_bounded_statistics(settings, monkeypatch):
    _, rc = opened(settings, [f'Drug{index:03}' for index in range(31)])
    inserted = add_terminal_routes(rc)
    exact = rc.db.query(
        'SELECT route_id, region, status, SUM(hits) hits, COUNT(*) n FROM coverage '
        'WHERE run_id=? GROUP BY route_id, region, status', (rc.run_id,))

    stats = scope._coverage(rc)

    assert stats['layout'] == 'route-groups-v1'
    assert stats['route_rows'] == len(exact) == inserted
    assert stats['rows'] == sum(row['n'] for row in exact)
    assert stats['hits'] == sum(row['hits'] for row in exact)
    assert sum(group['routes'] for group in stats['groups']) == stats['route_rows']
    assert sum(group['rows'] for group in stats['groups']) == stats['rows']
    assert sum(group['hits'] for group in stats['groups']) == stats['hits']
    groups = {(group['group'], group['region'], group['status']) for group in stats['groups']}
    assert {('china:cde:indication', 'china', 'blocked'),
            ('global:ctgov:condition', 'global', 'ok'),
            ('china:expand:alias', 'china', 'ok'),
            ('china:expand:alias:browser', 'china', 'failed'),
            ('china:expand:alias:site', 'china', 'blocked')} <= groups
    assert len(scope._json(stats)) < scope.TASK_CHARS // 10
    # The compact projection is a statistic; the exact coverage table is untouched.
    assert rc.db.one('SELECT COUNT(*) n FROM coverage WHERE run_id=?', (rc.run_id,))['n'] == inserted

    tasks = patched(monkeypatch, rc)
    result = scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')

    assert result['in_scope'] == 31
    assert len(tasks) >= 2
    assert sum(len(task['candidates']) for task in tasks) == 31
    assert {item['name'] for task in tasks for item in task['candidates']} == {
        f'Drug{index:03}' for index in range(31)}
    assert all(len(task['candidates']) <= scope.BATCH_SIZE for task in tasks)
    assert all(len(scope._json(task)) <= scope.TASK_CHARS for task in tasks)


def test_repeated_registry_provenance_is_lossless_inside_one_task(settings, monkeypatch):
    _, rc = opened(settings)
    drug, _ = rc.db.upsert_entity(rc.project_id, 'drug', 'eculizumab',
                                  aliases=['C5 inhibitor', 'Soliris'])
    ncts = [f'NCT{index:08d}' for index in range(320)]
    studies = []
    for index, nct in enumerate(ncts):
        trial, _ = rc.db.upsert_entity(rc.project_id, 'trial', nct)
        rc.db.link(rc.project_id, drug, 'drug-trial', trial)
        if index == 0:
            studies.append(study(nct, ['Unrelated disease'], study_type='OBSERVATIONAL',
                                 purpose='SUPPORTIVE_CARE', include_healthy=False))
        elif index == 1:
            studies.append(study(nct, ['Paroxysmal Nocturnal Hemoglobinuria (PNH)', 'PNH'],
                                 healthy=True))
        elif index == 2:
            studies.append(study(nct, ['Paroxysmal Nocturnal Hemoglobinuria'],
                                 include_healthy=False))
        else:
            studies.append(study(nct, ['Paroxysmal Nocturnal Hemoglobinuria']))
    search = published(rc, SEARCH, {'studies': studies})
    per_nct_url = f'{API}/NCT00000000'
    conflicting = published(rc, per_nct_url, study('NCT00000000', ['Conflicting condition']))
    tasks = patched(monkeypatch, rc)

    assert scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')['in_scope'] == 1

    task = tasks[0]
    assert len(task['candidates']) == 1 and len(scope._json(task)) <= scope.TASK_CHARS
    projection = task['candidates'][0]['attrs']['registry_observations']
    assert projection['registry'] == 'ctgov'
    assert projection['sources'] == {search: SEARCH, conflicting: per_nct_url}

    refs = [(ref['nct'], ref['source_id'], ref['json'], projection['sources'][ref['source_id']])
            for group in projection['groups'] for ref in group['studies']]
    expected = [(nct, search, f'studies[{index}].protocolSection', SEARCH)
                for index, nct in enumerate(ncts)]
    expected.append(('NCT00000000', conflicting, 'protocolSection', per_nct_url))
    assert sorted(refs) == sorted(expected)
    assert len(refs) == len(expected) == len(ncts) + 1
    # Locator, NCT and payload index still agree after factoring.
    for nct, sid, locator, _url in refs:
        if sid != search:
            continue
        index = int(locator.split('[')[1].split(']')[0])
        assert studies[index]['protocolSection']['identificationModule']['nctId'] == nct

    unrelated = next(group for group in projection['groups']
                     if group['conditions'] == ['Unrelated disease'])
    assert unrelated['studyType'] == 'OBSERVATIONAL'
    assert unrelated['primaryPurpose'] == 'SUPPORTIVE_CARE'
    assert 'healthyVolunteers' not in unrelated
    assert any(group.get('healthyVolunteers') is True for group in projection['groups'])
    assert any(group.get('healthyVolunteers') is False for group in projection['groups'])
    conflicting_group = next(group for group in projection['groups']
                             if group['conditions'] == ['Conflicting condition'])
    assert conflicting_group['studies'][0]['source_id'] == conflicting
    assert 'not forwarded' not in scope._json(task)


def test_shared_alias_across_batches_survives_route_compaction(settings, monkeypatch):
    _, rc = opened(settings, [f'Drug{index:03}' for index in range(35)])
    add_terminal_routes(rc)
    for name in ('Drug000', 'Drug034'):
        rc.db.upsert_entity(rc.project_id, 'drug', name, aliases=['shared'])

    def review(name, task):
        return ScopeResult(decisions=[
            ScopeDecision(drug='shared' if 'shared' in item['aliases'] else item['name'],
                          in_scope=True, reason='跨批共享别名') for item in task['candidates']])

    monkeypatch.setattr(rc, 'skill', review)
    result = scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')

    scopes = {row['name']: row['in_scope'] for row in rc.db.entities(rc.project_id, 'drug')}
    assert scopes['Drug000'] is scopes['Drug034'] is None
    assert result['in_scope'] == 33 and result['pending'] == 2
    ambiguous = [issue for issue in result['issues'] if issue['kind'] == 'ambiguous_name']
    assert len(ambiguous) == 2


def test_terminal_route_volume_keeps_source_version_reuse_scoped(settings, monkeypatch):
    _, rc = opened(settings, ['DrugA'])
    add_terminal_routes(rc)
    cited = 'https://clinicaltrials.gov/study/NCT00000001'
    rc.db.upsert_entity(rc.project_id, 'drug', 'DrugA', attrs={'evidence_urls': [cited]})
    calls = []

    def review(name, task):
        calls.append(task)
        return ScopeResult(decisions=[ScopeDecision(entity_id=item['entity_id'], drug=item['name'],
                                                    in_scope=True, reason='纳入') for item in task['candidates']])

    monkeypatch.setattr(rc, 'skill', review)
    coverage_before = rc.db.query('SELECT * FROM coverage ORDER BY id')
    scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    assert len(calls) == 1
    sid = register_text(rc.tool_ctx(), kind='ctgov', url=cited, text='current registered text')
    scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    assert len(calls) == 2
    scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    assert len(calls) == 2
    rc.db.execute('UPDATE sources SET digest=? WHERE id=?', (rc.cas.put(b'changed source raw bytes'), sid))
    scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    assert len(calls) == 3
    scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    assert len(calls) == 3
    assert rc.db.query('SELECT * FROM coverage ORDER BY id') == coverage_before


def test_irreducible_focus_still_fails_before_any_model_call(settings, monkeypatch):
    _, rc = opened(settings, ['DrugA'])
    add_terminal_routes(rc)
    rc.db.execute('UPDATE projects SET focus=? WHERE id=?', ('临床关注' * 20000, rc.project_id))
    assert scope._coverage(rc)['rows'] >= 3068
    calls = []

    def review(name, task):
        calls.append(task)
        return ScopeResult(decisions=[])

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(ValueError, match='复核输入'):
        scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    assert calls == []


def test_irreducible_single_candidate_fails_before_any_batch_is_sent(settings, monkeypatch):
    _, rc = opened(settings, [f'Drug{index:03}' for index in range(31)])
    add_terminal_routes(rc)
    rc.db.upsert_entity(rc.project_id, 'drug', 'Drug030', attrs={'clinical_definition': '完整定义' * 20000})
    calls = []

    def review(name, task):
        calls.append(task)
        return ScopeResult(decisions=[])

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(ValueError, match='复核输入'):
        scope.review_scope(rc, '阵发性睡眠性血红蛋白尿症')
    assert calls == []
    assert rc.db.one("SELECT COUNT(*) n FROM stages WHERE run_id=? AND name LIKE 'scope_batch:%'",
                     (rc.run_id,))['n'] == 0
    assert {row['in_scope'] for row in rc.db.entities(rc.project_id, 'drug')} == {None}
