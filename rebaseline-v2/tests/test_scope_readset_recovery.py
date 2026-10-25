"""Scope batch reuse binds this batch's own input and source read set.

The historical key hashed every project source, so a source registered by a later
batch made all earlier batches miss. Reuse is now same-run and identity-correct and
only invalidates for sources this batch actually used or cited.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from ciw2.domain.identity import name_owners
from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.harness.agent import HARNESS_RULES
from ciw2.harness.llm import LLMError, ScriptedLLM
from ciw2.pipeline import scope
from ciw2.pipeline.stages import coverage_review
from ciw2.service import Service
from ciw2.sources.http import register_text

URL = 'https://clinicaltrials.gov/study/NCT00000001'


def setup(settings, names, attrs=None):
    scripted = ScriptedLLM([])
    service = Service(settings, llm_factory=lambda _: (scripted, None))
    pid = service.create_project('适应症', ['C'])
    rid = service.db.create_run(pid)
    for name in names:
        service.db.upsert_entity(pid, 'drug', name, attrs=(attrs or {}).get(name))
    rc = service.context(pid, rid)
    rc.stage = 'coverage_review'
    return service, rc, scripted


def decisions(task):
    return ScopeResult(decisions=[
        ScopeDecision(drug=item['name'], in_scope=True, reason='符合本次研究范围')
        for item in task['candidates']])


def add_only(rc, url, text):
    return register_text(rc.tool_ctx(), kind='ctgov', url=url, text=text)


def read_source(rc, url, text):
    """Register/observe a source and record what the current Skill call read."""
    ctx = rc.tool_ctx()
    sid = register_text(ctx, kind='ctgov', url=url, text=text)
    rc.cache['last_skill_source_ids'] = sorted(ctx.extra['source_ids_read'])
    return sid


def read_current(rc, url, text):
    """Read the current version at a URL, like a source tool that stays offline."""
    row = rc.db.one('SELECT id FROM sources WHERE project_id=? AND url=? ORDER BY rowid DESC LIMIT 1',
                    (rc.project_id, url))
    if row:
        rc.cache['last_skill_source_ids'] = [row['id']]
        return row['id']
    return read_source(rc, url, text)


def source_url(index):
    return f'https://clinicaltrials.gov/study/NCT{index:08d}'


def names(tasks):
    return [task['candidates'][0]['name'] for task in tasks]


def planned_task(rc):
    entities = rc.db.entities(rc.project_id, 'drug')
    owners = name_owners(entities)
    base = {'indication': rc.project['indication'], 'focus': rc.project['focus'],
            'ambiguous_names': sorted(name for name, ids in owners.items() if len(ids) > 1),
            'coverage': scope._coverage(rc)}
    return scope._tasks(base, entities)[0]


def receipt(rc, task):
    cached = rc.db.stage_output(rc.run_id, scope._batch_key(rc, task))
    assert cached is not None
    return cached['sources']


def test_unrelated_source_does_not_force_a_completed_batch_to_repeat(settings, monkeypatch):
    _, rc, scripted = setup(settings, ['DrugA'])
    tasks = []

    def review(name, task):
        tasks.append(task)
        read_source(rc, URL, 'used text')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 1
    add_only(rc, 'https://clinicaltrials.gov/study/NCT00000099', 'unrelated text')
    coverage_review(rc)
    assert len(tasks) == 1 and scripted.calls == []


def test_same_call_read_is_bound_and_only_its_version_invalidates(settings, monkeypatch):
    _, rc, scripted = setup(settings, ['DrugA'])
    tasks = []

    def review(name, task):
        tasks.append(task)
        read_current(rc, URL, 'used text')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 1
    assert [source['url'] for source in receipt(rc, tasks[0])] == [URL]
    add_only(rc, 'https://clinicaltrials.gov/study/NCT00000099', 'unrelated text')
    coverage_review(rc)
    assert len(tasks) == 1
    used = receipt(rc, tasks[0])[0]
    rc.db.execute('UPDATE sources SET digest=? WHERE id=?', ('changed-digest', used['id']))
    coverage_review(rc)
    assert len(tasks) == 2
    rc.db.execute('UPDATE sources SET text_digest=? WHERE id=?', ('changed-text', used['id']))
    coverage_review(rc)
    assert len(tasks) == 3 and scripted.calls == []


def test_resume_reuses_two_completed_batches_after_a_later_failure(settings, monkeypatch):
    _, rc, scripted = setup(settings, [f'Drug{i:03}' for i in range(61)])
    tasks, fail = [], {'armed': True}

    def review(name, task):
        tasks.append(task)
        first = task['candidates'][0]['name']
        read_source(rc, source_url(int(first[4:])), f'text-{first}')
        if first == 'Drug060' and fail['armed']:
            fail['armed'] = False
            raise LLMError('third batch unavailable')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(LLMError):
        coverage_review(rc)
    assert names(tasks) == ['Drug000', 'Drug030', 'Drug060']
    coverage_review(rc)
    assert names(tasks) == ['Drug000', 'Drug030', 'Drug060', 'Drug060']
    coverage_review(rc)
    assert names(tasks) == ['Drug000', 'Drug030', 'Drug060', 'Drug060']
    assert [source['url'] for source in receipt(rc, tasks[0])] == [source_url(0)]
    assert [source['url'] for source in receipt(rc, tasks[1])] == [source_url(30)]
    assert [source['url'] for source in receipt(rc, tasks[-1])] == [source_url(60)]
    assert scripted.calls == []


def test_cited_but_unread_url_is_a_null_dependency_until_the_source_appears(settings, monkeypatch):
    _, rc, scripted = setup(settings, ['DrugA'], {'DrugA': {'evidence_urls': [URL]}})
    tasks = []

    def review(name, task):
        tasks.append(task)
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    assert [(source['url'], source['id']) for source in receipt(rc, tasks[0])] == [(URL, None)]
    coverage_review(rc)
    assert len(tasks) == 1
    sid = add_only(rc, URL, 'appeared text')
    coverage_review(rc)
    assert len(tasks) == 2
    assert [source['id'] for source in receipt(rc, tasks[-1])] == [sid]
    coverage_review(rc)
    assert len(tasks) == 2
    rc.db.execute('UPDATE sources SET digest=? WHERE id=?', ('appeared-changed', sid))
    coverage_review(rc)
    assert len(tasks) == 3 and scripted.calls == []


def test_later_batch_fetch_of_a_cited_url_invalidates_the_earlier_batch(settings, monkeypatch):
    _, rc, scripted = setup(settings, [f'Drug{i:03}' for i in range(31)],
                            {'Drug000': {'evidence_urls': [URL]}})
    tasks = []

    def review(name, task):
        tasks.append(task)
        if task['candidates'][0]['name'] == 'Drug030':
            read_source(rc, URL, 'later batch text')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    assert names(tasks) == ['Drug000', 'Drug030']
    coverage_review(rc)
    assert names(tasks) == ['Drug000', 'Drug030', 'Drug000']
    coverage_review(rc)
    assert names(tasks) == ['Drug000', 'Drug030', 'Drug000']
    assert scripted.calls == []


def test_used_source_change_invalidates_only_the_batch_that_used_it(settings, monkeypatch):
    _, rc, scripted = setup(settings, [f'Drug{i:03}' for i in range(31)])
    tasks, used = [], {}

    def review(name, task):
        first = task['candidates'][0]['name']
        tasks.append(task)
        used[first] = read_current(rc, source_url(int(first[4:])), f'text-{first}')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 2
    rc.db.execute('UPDATE sources SET text_digest=? WHERE id=?', ('changed', used['Drug000']))
    coverage_review(rc)
    assert names(tasks) == ['Drug000', 'Drug030', 'Drug000']
    assert scripted.calls == []


def test_missing_used_source_invalidates_the_batch(settings, monkeypatch):
    _, rc, scripted = setup(settings, ['DrugA'])
    tasks, holder = [], {}

    def review(name, task):
        tasks.append(task)
        holder.setdefault('sid', read_current(rc, URL, 'text'))
        rc.cache['last_skill_source_ids'] = [holder['sid']]
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 1
    rc.db.execute('DELETE FROM sources WHERE id=?', (holder['sid'],))
    coverage_review(rc)
    assert len(tasks) == 2
    # Retain the historical envelope, but never reuse or replace it with a dropped pointer.
    assert holder['sid'] in [source['id'] for source in receipt(rc, tasks[0])]
    assert scope.get_unit(rc, scope._batch_key(rc, tasks[0])) is None
    coverage_review(rc)
    assert len(tasks) == 3 and scripted.calls == []


def test_failed_call_is_not_cached_and_does_not_lend_its_read_set(settings, monkeypatch):
    _, rc, scripted = setup(settings, [f'Drug{i:03}' for i in range(31)])
    tasks, failed, fail = [], {}, {'armed': True}

    def review(name, task):
        first = task['candidates'][0]['name']
        tasks.append(task)
        if first == 'Drug030' and fail['armed']:
            fail['armed'] = False
            failed['sid'] = read_current(rc, URL, 'failed read')
            raise LLMError('second batch unavailable')
        if first == 'Drug030':
            assert 'last_skill_source_ids' not in rc.cache
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(LLMError):
        coverage_review(rc)
    assert rc.db.stage_output(rc.run_id, scope._batch_key(rc, tasks[1])) is None
    coverage_review(rc)
    assert [source['id'] for source in receipt(rc, tasks[1])] == []
    assert failed['sid'] not in [source['id'] for source in receipt(rc, tasks[1])]
    assert scripted.calls == []


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'wrong_binding'])
def test_unresolved_decisions_are_never_cached(settings, monkeypatch, kind):
    _, rc, scripted = setup(settings, ['DrugA', 'DrugB'])
    tasks = []

    def review(name, task):
        tasks.append(task)
        read_current(rc, URL, 'text')
        if kind == 'missing':
            return ScopeResult(decisions=[])
        if kind == 'duplicate':
            return ScopeResult(decisions=[
                ScopeDecision(drug='DrugA', in_scope=True, reason='纳入'),
                ScopeDecision(drug='DrugA', in_scope=False, reason='排除'),
                ScopeDecision(drug='DrugB', in_scope=True, reason='纳入')])
        return ScopeResult(decisions=[
            ScopeDecision(entity_id=task['candidates'][0]['entity_id'], drug='DrugB',
                          in_scope=False, reason='错误关联'),
            ScopeDecision(drug='DrugA', in_scope=True, reason='纳入')])

    monkeypatch.setattr(rc, 'skill', review)
    first, second = coverage_review(rc), coverage_review(rc)
    assert first['issues'] and second['decisions'] == first['decisions']
    assert len(tasks) == 2 and scripted.calls == []
    assert rc.db.stage_output(rc.run_id, scope._batch_key(rc, tasks[0])) is None


def test_task_skill_model_run_and_project_identity_prevent_reuse(settings, monkeypatch):
    service, rc, scripted = setup(settings, ['DrugA'])
    tasks = []

    def review(name, task):
        tasks.append(task)
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 1
    rc.db.upsert_entity(rc.project_id, 'drug', 'DrugA', attrs={'clinical_definition': 'changed'})
    coverage_review(rc)
    assert len(tasks) == 2
    monkeypatch.setattr(rc.skills['coverage-review'], 'body', rc.skills['coverage-review'].body + ' changed')
    coverage_review(rc)
    assert len(tasks) == 3
    rc.settings = replace(rc.settings, llm_model='another-model')
    coverage_review(rc)
    assert len(tasks) == 4
    rc.run_id = rc.db.create_run(rc.project_id)
    coverage_review(rc)
    assert len(tasks) == 5
    other = service.create_project('适应症', ['C'])
    service.db.upsert_entity(other, 'drug', 'DrugA')
    rc.project_id, rc.run_id = other, service.db.create_run(other)
    coverage_review(rc)
    assert len(tasks) == 6 and scripted.calls == []


def test_batch_key_binds_code_rules_and_output_schema(settings, monkeypatch):
    _, rc, _ = setup(settings, ['DrugA'])
    task = planned_task(rc)
    base = scope._batch_key(rc, task)
    monkeypatch.setattr(scope, 'CODE_HASH', 'changed-code')
    assert scope._batch_key(rc, task) != base
    monkeypatch.undo()
    monkeypatch.setattr(scope, 'HARNESS_RULES', 'changed rules')
    assert scope._batch_key(rc, task) != base
    monkeypatch.undo()

    class ChangedScopeResult(ScopeResult):
        changed: str = ''

    monkeypatch.setattr(scope, 'ScopeResult', ChangedScopeResult)
    assert scope._batch_key(rc, task) != base


def test_batch_key_separates_run_and_project(settings):
    service, rc, _ = setup(settings, ['DrugA'])
    task = planned_task(rc)
    original, before = rc.project_id, scope._batch_key(rc, task)
    other = service.create_project('适应症', ['C'])
    rc.project_id = other
    assert scope._batch_key(rc, task) != before
    rc.project_id, rc.run_id = original, service.db.create_run(original)
    assert scope._batch_key(rc, task) != before


def test_explicit_candidate_source_id_is_a_dependency(settings, monkeypatch):
    _, rc, scripted = setup(settings, ['DrugA'])
    sid = add_only(rc, 'https://example.org/registry', 'registry text')
    rc.db.upsert_entity(rc.project_id, 'drug', 'DrugA', attrs={'registry_source_id': sid})
    tasks = []

    def review(name, task):
        tasks.append(task)
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 1
    add_only(rc, 'https://example.org/unrelated', 'unrelated text')
    coverage_review(rc)
    assert len(tasks) == 1
    rc.db.execute('UPDATE sources SET text_digest=? WHERE id=?', ('changed', sid))
    coverage_review(rc)
    assert len(tasks) == 2 and scripted.calls == []


def test_legacy_full_pool_receipt_is_not_reused_or_rewritten(settings, monkeypatch):
    _, rc, scripted = setup(settings, ['DrugA'])
    entities = rc.db.entities(rc.project_id, 'drug')
    task = planned_task(rc)
    signature = {'task': task, 'sources': [], 'code': scope.CODE_HASH, 'rules': HARNESS_RULES,
                 'skill': rc.skills['coverage-review'].body, 'schema': ScopeResult.model_json_schema(),
                 'model': rc.settings.llm_model}
    legacy_key = 'scope_batch:' + hashlib.sha256(scope._json(signature).encode()).hexdigest()
    legacy_output = {'decisions': [{'entity_id': entities[0]['id'], 'in_scope': True, 'reason': '旧缓存'}],
                     'applied': 1, 'issues': []}
    rc.db.set_stage(rc.run_id, legacy_key, 'succeeded', output=legacy_output)
    tasks = []

    def review(name, task):
        tasks.append(task)
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    assert len(tasks) == 1
    assert scope._batch_key(rc, task) != legacy_key
    assert rc.db.stage_output(rc.run_id, legacy_key) == legacy_output
    assert scripted.calls == []


@pytest.mark.parametrize('kind', ['missing', 'foreign'])
def test_explicit_unavailable_source_id_cannot_be_silently_dropped_from_receipt(settings, monkeypatch, kind):
    service, rc, scripted = setup(settings, ['DrugA'])
    sid = 'src_missing00000'
    if kind == 'foreign':
        other = service.create_project('other', ['C'])
        sid = service.db.add_source(other, 'web', 'https://example.org/other', 'other-digest')
    service.db.upsert_entity(rc.project_id, 'drug', 'DrugA', attrs={'registry_source_id': sid})
    tasks = []

    def review(name, task):
        tasks.append(task)
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 2 and scripted.calls == []
    assert rc.db.stage_output(rc.run_id, scope._batch_key(rc, tasks[0])) is None


@pytest.mark.parametrize('surface', ['allowed_tool', 'shared_execution', 'source_recovery_policy'])
def test_scope_receipt_does_not_survive_a_used_execution_or_source_rule_change(settings, monkeypatch, surface):
    from ciw2.harness import agent
    from ciw2.harness.tools import REGISTRY
    from ciw2.pipeline import recovery
    _, rc, scripted = setup(settings, ['DrugA'])
    tasks = []

    def review(name, task):
        tasks.append(task)
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(tasks) == 1
    if surface == 'allowed_tool':
        def changed_fetch(*args, **kwargs):
            return {'changed-source-read-contract': True}
        monkeypatch.setattr(REGISTRY.get('fetch_url'), 'fn', changed_fetch)
    elif surface == 'shared_execution':
        monkeypatch.setattr(agent, '_dispatch', lambda *args, **kwargs: 'changed-execution')
    else:
        monkeypatch.setattr(recovery, '_representation_current', lambda *args: False)
    coverage_review(rc)
    assert len(tasks) == 2 and scripted.calls == []
