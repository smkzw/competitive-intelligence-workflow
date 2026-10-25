"""Scope-batch receipts bind this batch's own read/cited sources, not the whole pool.

The historical key hashed every project source. That made an unrelated source registered
by a later batch invalidate every earlier batch. These tests keep the raw/text/failure
protections and replace only that implementation-specific whole-pool assertion with
explicit used-versus-unrelated behavior.
"""

import pytest

from ciw2.domain.identity import name_owners
from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.harness.llm import LLMError, ScriptedLLM
from ciw2.pipeline import scope
from ciw2.pipeline.queries import intake_data
from ciw2.pipeline.stages import coverage_review
from ciw2.service import Service

URL = 'https://clinicaltrials.gov/study/NCT00000001'


def setup_scope(settings, names):
    scripted = ScriptedLLM([])
    service = Service(settings, llm_factory=lambda s: (scripted, None))
    pid = service.create_project('适应症', ['C'])
    rid = service.db.create_run(pid)
    for name in names:
        service.db.upsert_entity(pid, 'drug', name)
    rc = service.context(pid, rid)
    rc.stage = 'coverage_review'
    return rc, scripted


def decisions(task):
    return ScopeResult(decisions=[
        ScopeDecision(drug=item['name'], in_scope=True, reason='符合本次研究范围') for item in task['candidates']])


def succeeded_batches(rc):
    return rc.db.one(
        "SELECT COUNT(*) n FROM stages WHERE run_id=? AND name LIKE 'scope_batch:%' AND status='succeeded'",
        (rc.run_id,))['n']


def batch_key(rc, task):
    return scope._batch_key(rc, task)


def planned_tasks(rc):
    entities = rc.db.entities(rc.project_id, 'drug')
    owners = name_owners(entities)
    base = {'indication': intake_data(rc)['indication'], 'focus': rc.project['focus'],
            'ambiguous_names': sorted(name for name, ids in owners.items() if len(ids) > 1),
            'coverage': scope._coverage(rc)}
    return scope._tasks(base, entities)


def fetch(rc, digest, url=URL, text='text-1'):
    return rc.db.add_source(rc.project_id, 'ctgov', url, digest, text_digest=text)


def receipt_sources(rc, task):
    cached = rc.db.stage_output(rc.run_id, batch_key(rc, task))
    assert cached is not None
    return cached['sources']


def stored_batches(rc):
    return {row['name'] for row in rc.db.query(
        "SELECT name FROM stages WHERE run_id=? AND status='succeeded' AND name LIKE 'scope_batch:%'",
        (rc.run_id,))}


def test_same_run_reuses_scope_batch_after_it_reads_a_source(settings, monkeypatch):
    rc, scripted = setup_scope(settings, ['DrugA'])
    calls = []

    def review(name, task):
        calls.append(task)
        if len(calls) == 1:
            sid = fetch(rc, 'fetched-digest', text='fetched-text')
            rc.cache['last_skill_source_ids'] = [sid]
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    assert coverage_review(rc)['in_scope'] == 1
    assert coverage_review(rc)['in_scope'] == 1
    assert len(calls) == 1 and scripted.calls == []
    assert [source['url'] for source in receipt_sources(rc, calls[0])] == [URL]
    assert batch_key(rc, calls[0]) in stored_batches(rc)
    assert rc.db.one("SELECT COUNT(*) n FROM agent_steps WHERE role='cache'")['n'] == 1
    # Retired assertion: this batch used to miss because the whole project source pool
    # was part of the key. A source it did not read must not force another model call.
    fetch(rc, 'unrelated-digest', 'https://clinicaltrials.gov/study/NCT00000002', 'unrelated-text')
    assert coverage_review(rc)['in_scope'] == 1
    assert len(calls) == 1


def test_unrelated_source_does_not_invalidate_but_used_source_changes_do(settings, monkeypatch):
    rc, scripted = setup_scope(settings, ['DrugA'])
    calls, used = [], {}

    def review(name, task):
        calls.append(task)
        if 'sid' not in used:
            used['sid'] = fetch(rc, 'digest-a', text='text-a')
        rc.cache['last_skill_source_ids'] = [used['sid']]
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(calls) == 1
    fetch(rc, 'digest-b', 'https://clinicaltrials.gov/study/NCT00000002', 'text-b')
    coverage_review(rc)
    assert len(calls) == 1  # retired: an unrelated source used to invalidate every batch
    count = rc.db.one('SELECT COUNT(*) n FROM sources WHERE project_id=?', (rc.project_id,))['n']
    rc.db.execute('UPDATE sources SET digest=? WHERE project_id=? AND digest=?',
                  ('digest-a-changed', rc.project_id, 'digest-a'))
    assert rc.db.one('SELECT COUNT(*) n FROM sources WHERE project_id=?', (rc.project_id,))['n'] == count
    coverage_review(rc)
    assert len(calls) == 2
    rc.db.execute('UPDATE sources SET text_digest=? WHERE project_id=? AND digest=?',
                  ('text-a-changed', rc.project_id, 'digest-a-changed'))
    coverage_review(rc)
    assert len(calls) == 3 and scripted.calls == []


def test_same_run_reuses_both_batches_after_first_batch_reads_its_own_source(settings, monkeypatch):
    rc, scripted = setup_scope(settings, [f'Drug{i:03}' for i in range(31)])
    calls = []

    def review(name, task):
        calls.append(task)
        if len(calls) == 1:
            sid = fetch(rc, 'fetched-31', 'https://clinicaltrials.gov/study/NCT00000031', 'text-31')
            rc.cache['last_skill_source_ids'] = [sid]
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    assert coverage_review(rc)['in_scope'] == 31
    assert coverage_review(rc)['in_scope'] == 31
    assert [len(task['candidates']) for task in calls] == [30, 1]
    assert len(receipt_sources(rc, calls[0])) == 1
    assert receipt_sources(rc, calls[1]) == []
    assert rc.db.one("SELECT COUNT(*) n FROM agent_steps WHERE role='cache'")['n'] == 2
    assert scripted.calls == []


def test_later_batch_reads_the_source_registered_by_the_previous_batch(settings, monkeypatch):
    rc, scripted = setup_scope(settings, [f'Drug{i:03}' for i in range(31)])
    calls = []

    def review(name, task):
        calls.append(task)
        if task['candidates'][0]['name'] == 'Drug000':
            sid = fetch(rc, 'fetched-31', 'https://clinicaltrials.gov/study/NCT00000031', 'text-31')
        else:
            row = rc.db.one('SELECT id FROM sources WHERE project_id=? AND url=?',
                            (rc.project_id, 'https://clinicaltrials.gov/study/NCT00000031'))
            assert row is not None
            sid = row['id']
        rc.cache['last_skill_source_ids'] = [sid]
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    assert coverage_review(rc)['in_scope'] == 31
    assert len(calls) == 2
    assert receipt_sources(rc, calls[0]) == receipt_sources(rc, calls[1])
    coverage_review(rc)
    assert len(calls) == 2
    assert rc.db.one("SELECT COUNT(*) n FROM agent_steps WHERE role='cache'")['n'] == 2
    assert scripted.calls == []


def test_resume_reuses_batch_cached_with_the_source_it_read(settings, monkeypatch):
    rc, scripted = setup_scope(settings, [f'Drug{i:03}' for i in range(31)])
    calls = []
    fail = {'armed': True}

    def review(name, task):
        calls.append(task['candidates'][0]['name'])
        if calls[-1] == 'Drug000' and len(calls) == 1:
            sid = fetch(rc, 'fetched-partial', 'https://clinicaltrials.gov/study/NCT00000031', 'text-partial')
            rc.cache['last_skill_source_ids'] = [sid]
        if calls[-1] == 'Drug030' and fail['armed']:
            fail['armed'] = False
            raise LLMError('later batch unavailable')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(LLMError):
        coverage_review(rc)
    assert succeeded_batches(rc) == 1
    assert rc.db.one('SELECT in_scope FROM entities WHERE project_id=? AND name=?',
                     (rc.project_id, 'Drug000'))['in_scope'] == 1
    assert rc.db.one('SELECT in_scope FROM entities WHERE project_id=? AND name=?',
                     (rc.project_id, 'Drug030'))['in_scope'] is None
    assert coverage_review(rc)['in_scope'] == 31
    coverage_review(rc)
    assert calls == ['Drug000', 'Drug030', 'Drug030'] and scripted.calls == []


def test_later_batch_unrelated_source_does_not_refresh_earlier_batch(settings, monkeypatch):
    rc, scripted = setup_scope(settings, [f'Drug{i:03}' for i in range(31)])
    calls = []

    def review(name, task):
        calls.append(task['candidates'][0]['name'])
        if calls[-1] == 'Drug030':
            fetch(rc, 'later-30', 'https://clinicaltrials.gov/study/NCT00000030', 'text-30')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    coverage_review(rc)
    # Retired assertion: this used to be ['Drug000', 'Drug030', 'Drug000'] because the
    # whole project pool was hashed. Drug000 never read the source fetched by Drug030.
    assert calls == ['Drug000', 'Drug030'] and scripted.calls == []


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'wrong_identity'])
def test_invalid_scope_result_is_not_cached_after_source_fetch(settings, monkeypatch, kind):
    rc, scripted = setup_scope(settings, ['DrugA', 'DrugB'])
    calls = []

    def review(name, task):
        calls.append(task)
        if len(calls) == 1:
            fetch(rc, f'fetched-{kind}')
        if kind == 'missing':
            return ScopeResult(decisions=[])
        if kind == 'duplicate':
            return ScopeResult(decisions=[
                ScopeDecision(drug='DrugA', in_scope=True, reason='纳入'),
                ScopeDecision(drug='DrugA', in_scope=False, reason='排除'),
                ScopeDecision(drug='DrugB', in_scope=True, reason='纳入')])
        return ScopeResult(decisions=[
            ScopeDecision(entity_id=task['candidates'][0]['entity_id'], drug='DrugB', in_scope=False, reason='错误关联')])

    monkeypatch.setattr(rc, 'skill', review)
    first = coverage_review(rc)
    second = coverage_review(rc)
    assert first['issues'] and first['decisions'] == second['decisions']
    assert len(calls) == 2 and succeeded_batches(rc) == 0 and scripted.calls == []


def test_failed_scope_call_does_not_fabricate_successful_cache(settings, monkeypatch):
    rc, scripted = setup_scope(settings, ['DrugA'])
    calls = []

    def review(name, task):
        calls.append(task)
        if len(calls) == 1:
            fetch(rc, 'fetched-fail', text='text-fail')
            raise LLMError('scope unavailable')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(LLMError):
        coverage_review(rc)
    assert succeeded_batches(rc) == 0
    assert coverage_review(rc)['in_scope'] == 1
    coverage_review(rc)
    assert len(calls) == 2 and succeeded_batches(rc) == 1 and scripted.calls == []
