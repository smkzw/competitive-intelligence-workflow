"""The normal DAG scopes trials after source collection, without erasing evidence."""
from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.stages import STAGES
from ciw2.render.portal import report_data
from ciw2.service import Service


def test_normal_stage_reviews_new_orphans_before_analysis(settings, monkeypatch):
    names = [stage.name for stage in STAGES]
    assert names.index('trial_evidence') < names.index('trial_scope_review') < names.index('verify')
    svc = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = svc.create_project('适应症', ['A', 'B', 'C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    rc.stage = 'trial_scope_review'
    db = svc.db
    ids = {}
    for name, kind in [('NCT-DEVICE', 'DEVICE'), ('NCT-DRUG', 'DRUG'), ('NCT-UNKNOWN', 'OTHER')]:
        tid, _ = db.upsert_entity(pid, 'trial', name, attrs={'interventions': [{'name': name, 'type': kind}]})
        ids[name] = tid
        db.add_fact({'project_id': pid, 'entity_id': tid, 'field': 'design.sample_size', 'value': 40,
                     'tier': 'standard', 'status': 'verified', 'quote': '40', 'extracted_by': 'code:test'})
    before = db.current_facts(pid)
    seen = []

    def review(skill, task):
        seen.append(task)
        return ScopeResult(decisions=[ScopeDecision(entity_id=item['entity_id'], drug=item['name'],
            in_scope={'NCT-DEVICE': False, 'NCT-DRUG': True, 'NCT-UNKNOWN': None}[item['name']],
            reason='测试用有界范围决定') for item in task['candidates']])

    monkeypatch.setattr(rc, 'skill', review)
    stage = next(stage for stage in STAGES if stage.name == 'trial_scope_review')
    result = stage.fn(rc)
    assert seen[0]['candidate_kind'] == 'trial' and len(seen[0]['candidates']) == 3
    assert (result['excluded'], result['in_scope'], result['pending']) == (1, 1, 1)
    assert {row['trial'] for row in report_data(db, pid, 'C')['rows']} == {'NCT-DRUG', 'NCT-UNKNOWN'}
    assert db.current_facts(pid) == before
    assert {row['id'] for row in db.entities(pid, 'trial')} == set(ids.values())
    monkeypatch.setattr(rc, 'skill', lambda *args: (_ for _ in ()).throw(AssertionError('cache missed')))
    assert stage.fn(rc) == result
