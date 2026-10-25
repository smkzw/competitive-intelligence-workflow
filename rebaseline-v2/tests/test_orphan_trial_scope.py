import pytest

from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.harness.cancellation import RunCancelled, RunControl
from ciw2.harness.llm import LLMError, ScriptedLLM
from ciw2.pipeline.scope import review_orphan_trials, review_scope
from ciw2.service import Service

DEVICE = {
    'title': '设备可行性研究', 'phase': 'phase4', 'conditions': ['特应性皮炎'],
    'interventions': [{'type': 'DEVICE', 'name': '激光设备', 'other_names': ['Laser']}],
    'url': 'https://clinicaltrials.gov/study/NCT00000010', 'registry': 'ctgov',
    'enrollment': None, 'countries': ['United States'], 'healthy_volunteers': True,
}
CHINA = {
    'title': '诊断器械观察', 'phase': 'unknown', 'conditions': ['其他适应症'],
    'interventions': [{'type': 'DIAGNOSTIC_TEST', 'name': '检测盒', 'other_names': []}],
    'url': 'http://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml',
    'registry': 'chinadrugtrials',
}
CANDIDATE_KEYS = {'name', 'name_zh', 'aliases', 'attrs', 'found_by', 'entity_id'}


def opened(settings):
    service = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = service.create_project('适应症', ['C'], focus='仅复核未挂药物的试验')
    rc = service.context(pid, service.db.create_run(pid))
    rc.stage = 'coverage_review'
    return service, rc


def trial(rc, name, **kwargs):
    eid, _ = rc.db.upsert_entity(rc.project_id, 'trial', name, **kwargs)
    return eid


def attrs_for(name):
    return {'title': name, 'phase': 'phase2', 'conditions': ['适应症'],
            'interventions': [{'type': 'DEVICE', 'name': '设备', 'other_names': ['别名不提升']}],
            'url': f'https://example.test/{name}'}


def accept(task, state=True, reason='符合本次研究范围'):
    return ScopeResult(decisions=[
        ScopeDecision(entity_id=item['entity_id'], drug=item['name'], in_scope=state, reason=reason)
        for item in task['candidates']])


def add_fact(rc, entity_id, source_id, quote):
    rc.db.add_fact({'project_id': rc.project_id, 'entity_id': entity_id, 'field': 'design.phase',
                    'value': 'phase2', 'tier': 'standard', 'status': 'verified', 'source_id': source_id,
                    'quote': quote, 'extracted_by': 'code:test'})


def records(db, pid):
    entities = [(row['id'], row['type'], row['name'], row['aliases'], row['attrs'], row['found_by'])
                for row in db.entities(pid)]
    sources = db.query('SELECT id,kind,url,digest FROM sources WHERE project_id=? ORDER BY id', (pid,))
    facts = db.query(
        'SELECT id,entity_id,field,value,status,quote,source_id FROM facts WHERE project_id=? ORDER BY id', (pid,))
    links = db.query('SELECT src,rel,dst,attrs FROM links WHERE project_id=? ORDER BY src,rel,dst', (pid,))
    return entities, sources, facts, links


def test_orphan_request_contains_only_unlinked_trials_and_full_attrs(settings, monkeypatch):
    _, rc = opened(settings)
    db, pid = rc.db, rc.project_id
    included, _ = db.upsert_entity(pid, 'drug', '在研药物')
    unknown, _ = db.upsert_entity(pid, 'drug', '未知药物')
    excluded, _ = db.upsert_entity(pid, 'drug', '排除药物')
    db.set_scope(included, True, '纳入')
    db.set_scope(excluded, False, '排除')
    parents = {'NCT-LINK-IN': included, 'NCT-LINK-UNK': unknown, 'NCT-LINK-OUT': excluded}
    for name, drug_id in parents.items():
        db.link(pid, drug_id, 'drug-trial', trial(rc, name, attrs=attrs_for(name)))
    device = trial(rc, 'NCT00000010', attrs=DEVICE, route_id='ctgov')
    china = trial(rc, 'CTR20260001', attrs=CHINA, route_id='chinadrugtrials')
    source = db.add_source(pid, 'ctgov', DEVICE['url'], 'digest-device')
    db.link(pid, device, 'ctgov-current', source)
    seen = []

    def review(name, task):
        assert task['candidate_kind'] == 'trial' and task['indication'] == '适应症'
        assert task['focus'] == '仅复核未挂药物的试验' and task['ambiguous_names'] == []
        assert 'coverage' in task
        seen.extend(task['candidates'])
        return accept(task, None, '信息不足')

    monkeypatch.setattr(rc, 'skill', review)
    result = review_orphan_trials(rc, '适应症')
    by_name = {item['name']: item for item in seen}
    assert set(by_name) == {'NCT00000010', 'CTR20260001'}
    assert by_name['NCT00000010']['entity_id'] == device and by_name['NCT00000010']['attrs'] == DEVICE
    assert by_name['CTR20260001']['entity_id'] == china and by_name['CTR20260001']['attrs'] == CHINA
    assert by_name['NCT00000010']['aliases'] == [] and by_name['NCT00000010']['found_by'] == ['ctgov']
    assert set(by_name['NCT00000010']) == CANDIDATE_KEYS and '激光设备' not in by_name['NCT00000010']['aliases']
    scopes = {row['name']: row['in_scope'] for row in db.entities(pid)}
    assert scopes['在研药物'] == 1 and scopes['未知药物'] is None and scopes['排除药物'] == 0
    assert scopes['NCT-LINK-IN'] is scopes['NCT-LINK-UNK'] is scopes['NCT-LINK-OUT'] is None
    assert scopes['NCT00000010'] is None and result['pending'] == 2 and result['excluded'] == 0
    assert result['decisions'] == 2 and result['candidate_kind'] == 'trial'
    assert db.one("SELECT dst FROM links WHERE project_id=? AND rel='ctgov-current'", (pid,))['dst'] == source


def test_identity_bound_decisions_do_not_cross_entities(settings, monkeypatch):
    service, rc = opened(settings)
    db, pid = rc.db, rc.project_id
    drug, _ = db.upsert_entity(pid, 'drug', '兄弟药物', aliases=['NCT-TRUE'])
    db.set_scope(drug, True, '药物已纳入')
    linked = trial(rc, 'NCT-LINKED', attrs=attrs_for('NCT-LINKED'))
    db.link(pid, drug, 'drug-trial', linked)
    names = ('NCT-TRUE', 'NCT-FALSE', 'NCT-NULL', 'NCT-MISS', 'NCT-DUP', 'NCT-FOREIGN', 'NCT-CONFLICT', 'NCT-SIB')
    ids = {name: trial(rc, name, attrs=attrs_for(name)) for name in names}
    other = service.create_project('其他适应症', ['C'])
    foreign, _ = db.upsert_entity(other, 'trial', 'NCT-FOREIGN', attrs=attrs_for('foreign'))
    twin, _ = db.upsert_entity(other, 'trial', 'NCT-SIB', attrs=attrs_for('twin'))
    source = db.add_source(pid, 'ctgov', 'https://clinicaltrials.gov/study/NCT-TRUE', 'digest-true')
    db.link(pid, ids['NCT-TRUE'], 'ctgov-current', source)
    add_fact(rc, ids['NCT-TRUE'], source, 'Phase 2')
    before, before_other = records(db, pid), records(db, other)

    def review(name, task):
        rows = {item['name']: item['entity_id'] for item in task['candidates']}
        assert 'NCT-LINKED' not in rows and rows['NCT-TRUE'] == ids['NCT-TRUE']
        return ScopeResult(decisions=[
            ScopeDecision(entity_id=rows['NCT-TRUE'], drug='NCT-TRUE', in_scope=True, reason='纳入该试验'),
            ScopeDecision(entity_id=rows['NCT-FALSE'], drug='NCT-FALSE', in_scope=False, reason='明确非本研究'),
            ScopeDecision(entity_id=rows['NCT-NULL'], drug='NCT-NULL', in_scope=None, reason='材料不足'),
            ScopeDecision(drug='NCT-DUP', in_scope=True, reason='一次纳入'),
            ScopeDecision(drug='NCT-DUP', in_scope=False, reason='一次排除'),
            ScopeDecision(entity_id=foreign, drug='NCT-FOREIGN', in_scope=False, reason='外部项目'),
            ScopeDecision(entity_id=rows['NCT-CONFLICT'], drug='NCT-TRUE', in_scope=False, reason='身份冲突'),
            ScopeDecision(entity_id=drug, drug='兄弟药物', in_scope=False, reason='不得改药物'),
            ScopeDecision(drug='NCT-SIB', in_scope=True, reason='唯一原名'),
        ])

    monkeypatch.setattr(rc, 'skill', review)
    result = review_orphan_trials(rc, '适应症')
    scopes = {row['name']: row['in_scope'] for row in db.entities(pid, 'trial')}
    assert scopes == {'NCT-LINKED': None, 'NCT-TRUE': 1, 'NCT-FALSE': 0, 'NCT-NULL': None, 'NCT-MISS': None,
                      'NCT-DUP': None, 'NCT-FOREIGN': None, 'NCT-CONFLICT': None, 'NCT-SIB': 1}
    drug_row = db.entities(pid, 'drug')[0]
    assert drug_row['in_scope'] == 1 and drug_row['scope_reason'] == '药物已纳入' and drug_row['aliases'] == ['NCT-TRUE']
    assert {row['id']: row['in_scope'] for row in db.entities(other, 'trial')} == {foreign: None, twin: None}
    assert {'duplicate_decision', 'invalid_binding', 'missing_decision'} <= {item['kind'] for item in result['issues']}
    assert result['in_scope'] == 2 and result['excluded'] == 1 and result['pending'] == 5 and result['decisions'] == 4
    assert records(db, pid) == before and records(db, other) == before_other
    assert db.one('SELECT scope_reason FROM entities WHERE id=?', (ids['NCT-FALSE'],))['scope_reason'] == '明确非本研究'
    assert db.one('SELECT scope_reason,in_scope FROM entities WHERE id=?', (ids['NCT-NULL'],)) == {
        'scope_reason': '材料不足', 'in_scope': None}
    assert db.one('SELECT in_scope FROM entities WHERE id=?', (linked,))['in_scope'] is None


def test_shared_alias_without_exact_id_stays_pending(settings, monkeypatch):
    _, rc = opened(settings)
    for name in ('NCT-A', 'NCT-B'):
        trial(rc, name, aliases=['共享登记名'], attrs=attrs_for(name))

    def review(name, task):
        assert task['ambiguous_names'] == ['共享登记名'] and task['candidate_kind'] == 'trial'
        return ScopeResult(decisions=[ScopeDecision(drug='共享登记名', in_scope=False, reason='无法区分')])

    monkeypatch.setattr(rc, 'skill', review)
    result = review_orphan_trials(rc, '适应症')
    assert result['pending'] == 2 and result['excluded'] == 0 and result['decisions'] == 0
    assert {row['in_scope'] for row in rc.db.entities(rc.project_id, 'trial')} == {None}
    assert any(item['kind'] == 'ambiguous_name' for item in result['issues'])


def test_conflicting_duplicate_is_not_reused(settings, monkeypatch):
    _, rc = opened(settings)
    trial(rc, 'NCT-DUP', attrs=attrs_for('NCT-DUP'))
    calls = []

    def review(name, task):
        calls.append(task['candidate_kind'])
        item = task['candidates'][0]
        return ScopeResult(decisions=[
            ScopeDecision(entity_id=item['entity_id'], drug='NCT-DUP', in_scope=True, reason='纳入'),
            ScopeDecision(entity_id=item['entity_id'], drug='NCT-DUP', in_scope=False, reason='排除')])

    monkeypatch.setattr(rc, 'skill', review)
    assert review_orphan_trials(rc, '适应症')['pending'] == 1
    assert review_orphan_trials(rc, '适应症')['pending'] == 1
    assert calls == ['trial', 'trial']
    assert rc.db.entities(rc.project_id, 'trial')[0]['in_scope'] is None


def test_partial_failure_resumes_and_source_change_recalls(settings, monkeypatch):
    _, rc = opened(settings)
    names = [f'NCT{i:08d}' for i in range(31)]
    ids = [trial(rc, name, attrs=attrs_for(name)) for name in names]
    source = rc.db.add_source(rc.project_id, 'ctgov', 'https://clinicaltrials.gov/study/NCT00000000', 'digest-0')
    add_fact(rc, ids[0], source, 'completed batch')
    add_fact(rc, ids[-1], source, 'pending batch')
    facts = rc.db.query('SELECT id,entity_id,value,quote FROM facts WHERE project_id=? ORDER BY id', (rc.project_id,))
    links = rc.db.query('SELECT src,rel,dst FROM links WHERE project_id=? ORDER BY src,rel,dst', (rc.project_id,))
    calls, fail = [], {'armed': True}

    def review(name, task):
        calls.append([item['name'] for item in task['candidates']])
        if len(calls) == 2 and fail['armed']:
            fail['armed'] = False
            raise LLMError('later batch unavailable')
        return accept(task)

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(LLMError):
        review_orphan_trials(rc, '适应症')
    state = {row['name']: row['in_scope'] for row in rc.db.entities(rc.project_id, 'trial')}
    assert [state[name] for name in names[:30]] == [1] * 30 and state[names[30]] is None
    result = review_orphan_trials(rc, '适应症')
    assert [len(batch) for batch in calls] == [30, 1, 1] and calls[1] == calls[2] == [names[30]]
    assert result['in_scope'] == 31 and result['pending'] == 0
    # Only the batch that cites this URL (NCT00000030's task attrs) depends on it.
    # The retired whole-pool key re-ran all 30 earlier trials for any new source.
    rc.db.add_source(rc.project_id, 'ctgov', 'https://example.test/NCT00000030', 'digest-30')
    review_orphan_trials(rc, '适应症')
    assert [len(batch) for batch in calls] == [30, 1, 1, 1] and calls[3] == calls[2]
    assert rc.db.one("SELECT COUNT(*) n FROM agent_steps WHERE role='cache'")['n'] == 2
    assert rc.db.query('SELECT id,entity_id,value,quote FROM facts WHERE project_id=? ORDER BY id',
                       (rc.project_id,)) == facts
    assert rc.db.query('SELECT src,rel,dst FROM links WHERE project_id=? ORDER BY src,rel,dst',
                       (rc.project_id,)) == links


def test_cancellation_does_not_call_the_next_batch(settings, monkeypatch):
    _, rc = opened(settings)
    rc.control = RunControl()
    names = [f'NCT{i:08d}' for i in range(31)]
    ids = [trial(rc, name, attrs=attrs_for(name)) for name in names]
    source = rc.db.add_source(rc.project_id, 'ctgov', 'https://clinicaltrials.gov/study/NCT00000030', 'digest-last')
    add_fact(rc, ids[-1], source, 'not yet reviewed')
    calls = []

    def review(name, task):
        calls.append(task['candidates'][0]['name'])
        if len(calls) == 1:
            rc.control.request_stop()
        return accept(task)

    monkeypatch.setattr(rc, 'skill', review)
    with pytest.raises(RunCancelled):
        review_orphan_trials(rc, '适应症')
    state = {row['name']: row['in_scope'] for row in rc.db.entities(rc.project_id, 'trial')}
    assert calls == [names[0]] and state[names[0]] == 1 and state[names[30]] is None
    assert rc.db.one('SELECT COUNT(*) n FROM facts WHERE entity_id=?', (ids[-1],))['n'] == 1
    rc.control = RunControl()
    assert review_orphan_trials(rc, '适应症')['in_scope'] == 31
    assert calls == [names[0], names[30]]


def test_drug_review_leaves_orphan_trials_untouched(settings, monkeypatch):
    _, rc = opened(settings)
    rc.db.upsert_entity(rc.project_id, 'drug', 'DrugA')
    trial(rc, 'NCT-ORPHAN', attrs=attrs_for('NCT-ORPHAN'))
    seen = []

    def review(name, task):
        seen.append(task)
        return accept(task)

    monkeypatch.setattr(rc, 'skill', review)
    result = review_scope(rc, '适应症')
    assert [item['name'] for item in seen[0]['candidates']] == ['DrugA']
    assert 'candidate_kind' not in seen[0] and 'candidate_kind' not in result and result['in_scope'] == 1
    assert rc.db.entities(rc.project_id, 'trial')[0]['in_scope'] is None
    monkeypatch.setattr(rc, 'skill', lambda *args: pytest.fail('cached drug batch was sent again'))
    assert review_scope(rc, '适应症')['in_scope'] == 1


def test_linked_trials_are_not_sent_when_every_parent_is_excluded(settings, monkeypatch):
    _, rc = opened(settings)
    drug, _ = rc.db.upsert_entity(rc.project_id, 'drug', 'DrugA')
    rc.db.set_scope(drug, False, '已排除药物')
    linked = trial(rc, 'NCT-LINKED', attrs=attrs_for('NCT-LINKED'))
    rc.db.link(rc.project_id, drug, 'drug-trial', linked)
    monkeypatch.setattr(rc, 'skill', lambda *args: pytest.fail('linked trial is not an orphan'))
    result = review_orphan_trials(rc, '适应症')
    assert result['input_empty'] is True and result['decisions'] == 0 and result['candidate_kind'] == 'trial'
    assert rc.db.one('SELECT in_scope FROM entities WHERE id=?', (linked,))['in_scope'] is None
