import pytest

from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.harness.llm import LLMError, ScriptedLLM
from ciw2.pipeline.stages import coverage_review
from ciw2.service import Service


def setup_scope(settings, names):
    service = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = service.create_project('适应症', ['C'])
    rid = service.db.create_run(pid)
    for name in names:
        service.db.upsert_entity(pid, 'drug', name)
    rc = service.context(pid, rid)
    rc.stage = 'coverage_review'
    return rc


def decisions(task):
    return ScopeResult(decisions=[ScopeDecision(drug=d['name'], in_scope=True, reason='符合本次研究范围')
                                  for d in task['candidates']])


def scopes(rc):
    return {d['name']: d['in_scope'] for d in rc.db.entities(rc.project_id, 'drug')}


def test_all_candidates_reviewed_in_small_complete_batches(settings, monkeypatch):
    rc = setup_scope(settings, [f'Drug{i:03}' for i in range(67)])
    seen = []

    def review(name, task):
        assert len(task['candidates']) <= 30
        seen.extend(d['name'] for d in task['candidates'])
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    result = coverage_review(rc)
    assert seen == sorted(scopes(rc)) and len(seen) == len(set(seen)) == 67
    assert result['in_scope'] == 67 and result['pending'] == 0


def test_literal_names_are_not_merged_by_removing_punctuation(settings, monkeypatch):
    rc = setup_scope(settings, ['A-B', 'AB'])
    monkeypatch.setattr(rc, 'skill', lambda *args: ScopeResult(decisions=[
        ScopeDecision(drug='A-B', in_scope=False, reason='本次排除A-B')]))
    result = coverage_review(rc)
    assert scopes(rc) == {'A-B': 0, 'AB': None}
    assert result['excluded'] == 1 and result['pending'] == 1


def test_conflicting_duplicate_decisions_remain_pending_not_last_wins(settings, monkeypatch):
    rc = setup_scope(settings, ['DrugA'])
    monkeypatch.setattr(rc, 'skill', lambda *args: ScopeResult(decisions=[
        ScopeDecision(drug='DrugA', in_scope=True, reason='纳入'),
        ScopeDecision(drug='DrugA', in_scope=False, reason='排除')]))
    result = coverage_review(rc)
    assert scopes(rc)['DrugA'] is None
    assert result['in_scope'] == result['excluded'] == 0 and result['pending'] == 1
    assert any(issue['kind'] == 'duplicate_decision' for issue in result['issues'])


def test_later_scope_failure_reuses_unchanged_earlier_batch(settings, monkeypatch):
    rc = setup_scope(settings, [f'Drug{i:03}' for i in range(35)])
    seen = []
    fail = {'once': True}

    def review(name, task):
        first = task['candidates'][0]['name']
        seen.append(first)
        if len(seen) == 2 and fail['once']:
            fail['once'] = False
            raise LLMError('later batch unavailable')
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(LLMError):
        coverage_review(rc)
    result = coverage_review(rc)
    assert seen.count('Drug000') == 1 and result['in_scope'] == 35


def test_no_candidates_does_not_ask_model_to_invent_review(settings, monkeypatch):
    rc = setup_scope(settings, [])
    monkeypatch.setattr(rc, 'skill', lambda *args: pytest.fail('No candidates to review'))
    result = coverage_review(rc)
    assert result['decisions'] == 0 and result['input_empty'] is True


def test_scope_metadata_budget_checked_before_any_model_call(settings, monkeypatch):
    rc = setup_scope(settings, ['DrugA'])
    rc.db.execute('UPDATE projects SET focus=? WHERE id=?', ('临床关注' * 20000, rc.project_id))
    monkeypatch.setattr(rc, 'skill', lambda *args: pytest.fail('Oversize task sent to model'))
    with pytest.raises(ValueError, match='复核输入'):
        coverage_review(rc)


def test_explicit_ids_do_not_accept_wrong_name_or_other_project(settings, monkeypatch):
    rc = setup_scope(settings, ['DrugA', 'DrugB'])
    rows = rc.db.entities(rc.project_id, 'drug')
    monkeypatch.setattr(rc, 'skill', lambda *args: ScopeResult(decisions=[
        ScopeDecision(entity_id=rows[0]['id'], drug='DrugB', in_scope=False, reason='错误关联'),
        ScopeDecision(entity_id='outside-project', drug='DrugB', in_scope=True, reason='外部ID')]))
    result = coverage_review(rc)
    assert scopes(rc) == {'DrugA': None, 'DrugB': None}
    assert result['decisions'] == 0 and result['pending'] == 2
    assert sum(issue['kind'] == 'invalid_binding' for issue in result['issues']) == 2


def test_shared_alias_needs_explicit_candidate_id(settings, monkeypatch):
    rc = setup_scope(settings, ['DrugA', 'DrugB'])
    for name in scopes(rc):
        rc.db.upsert_entity(rc.project_id, 'drug', name, aliases=['shared'])
    monkeypatch.setattr(rc, 'skill', lambda *args: ScopeResult(decisions=[
        ScopeDecision(drug='shared', in_scope=True, reason='别名无法区分')]))
    result = coverage_review(rc)
    assert result['pending'] == 2 and result['decisions'] == 0
    assert any(issue['kind'] == 'ambiguous_name' for issue in result['issues'])

    def exact(name, task):
        return ScopeResult(decisions=[ScopeDecision(entity_id=d['entity_id'], drug='shared',
                                                   in_scope=True, reason='明确ID') for d in task['candidates']])

    monkeypatch.setattr(rc, 'skill', exact)
    # New run never borrows the previous run's model decisions.
    rc.run_id = rc.db.create_run(rc.project_id)
    assert coverage_review(rc)['in_scope'] == 2


def test_source_change_invalidates_scope_cache(settings, monkeypatch):
    rc = setup_scope(settings, ['DrugA'])
    # A source at a URL this exact task cites is a real dependency. The retired
    # whole-pool key also invalidated for unrelated sources; that is no longer reused.
    rc.db.upsert_entity(rc.project_id, 'drug', 'DrugA', attrs={
        'evidence_urls': ['https://clinicaltrials.gov/study/NCT00000001']})
    seen = []

    def review(name, task):
        seen.append(name)
        return decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    coverage_review(rc)
    coverage_review(rc)
    assert len(seen) == 1
    rc.db.add_source(rc.project_id, 'ctgov', 'https://clinicaltrials.gov/study/NCT00000001', 'new-digest')
    coverage_review(rc)
    assert len(seen) == 2
    assert rc.db.one("SELECT COUNT(*) n FROM agent_steps WHERE role='cache'")['n'] == 1


def test_oversized_last_candidate_fails_before_any_batch(settings, monkeypatch):
    rc = setup_scope(settings, [f'Drug{i:03}' for i in range(35)])
    rc.db.upsert_entity(rc.project_id, 'drug', 'Drug034', attrs={'clinical_definition': '完整定义' * 20000})
    monkeypatch.setattr(rc, 'skill', lambda *args: pytest.fail('Input planning must finish before calling model'))
    with pytest.raises(ValueError, match='复核输入'):
        coverage_review(rc)


def test_alias_ambiguity_across_batches_does_not_depend_on_partition(settings, monkeypatch):
    rc = setup_scope(settings, [f'Drug{i:03}' for i in range(35)])
    for name in ('Drug000', 'Drug034'):
        rc.db.upsert_entity(rc.project_id, 'drug', name, aliases=['shared'])

    def review(name, task):
        return ScopeResult(decisions=[ScopeDecision(drug='shared' if 'shared' in d['aliases'] else d['name'],
                                                   in_scope=True, reason='测试跨批同名') for d in task['candidates']])

    monkeypatch.setattr(rc, 'skill', review)
    result = coverage_review(rc)
    assert scopes(rc)['Drug000'] is scopes(rc)['Drug034'] is None
    assert result['in_scope'] == 33 and result['pending'] == 2


def test_incomplete_batch_is_not_frozen_as_reusable_model_result(settings, monkeypatch):
    rc = setup_scope(settings, ['DrugA'])
    calls = []

    def review(name, task):
        calls.append(name)
        return ScopeResult(decisions=[]) if len(calls) == 1 else decisions(task)

    monkeypatch.setattr(rc, 'skill', review)
    assert coverage_review(rc)['pending'] == 1
    assert coverage_review(rc)['in_scope'] == 1
    assert len(calls) == 2
