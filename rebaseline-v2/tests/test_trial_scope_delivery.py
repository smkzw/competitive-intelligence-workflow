"""Explicit candidate scope and failed source routes must not falsify report completeness."""
import pytest
from test_china_design_pipeline import setup

from ciw2.pipeline import runner
from ciw2.pipeline.stages import STAGES, Stage, trial_evidence
from ciw2.render.portal import report_data
from ciw2.sources import china_detail


@pytest.mark.parametrize('mode',['excluded','unknown','mixed','orphan','trial_excluded'])
def test_native_work_respects_explicit_parent_scope_without_discarding_unknowns(settings,monkeypatch,mode):
    rc,_,calls=setup(settings,monkeypatch)
    db,pid=rc.db,rc.project_id
    drug=db.entities(pid,'drug')[0]
    trial=db.entities(pid,'trial')[0]
    if mode in {'excluded','mixed'}:db.set_scope(drug['id'],False,'本项目明确排除')
    if mode=='mixed':
        included,_=db.upsert_entity(pid,'drug','另一明确方案')
        db.link(pid,included,'drug-trial',trial['id'])
    if mode=='orphan':db.execute("DELETE FROM links WHERE project_id=? AND rel='drug-trial'",(pid,))
    if mode=='trial_excluded':db.set_scope(trial['id'],False,'本项目明确排除研究')
    trial_evidence(rc)
    assert len(calls)==(0 if mode in {'excluded','trial_excluded'} else 1)


def test_scope_change_updates_a_b_c_queries_without_deleting_adopted_history(settings,monkeypatch):
    rc,_,_=setup(settings,monkeypatch)
    trial_evidence(rc)
    db,pid=rc.db,rc.project_id
    trial=db.entities(pid,'trial')[0]
    drug=db.entities(pid,'drug')[0]
    db.add_fact({'project_id':pid,'entity_id':trial['id'],'field':'result.primary.value','value':12,
        'status':'verified','tier':'critical','source_id':None,'quote':'12',
        'context':{'endpoint':'EASI','arm':'原药软膏','timepoint':'Week 8','stat_type':'mean','unit':'score'},
        'extracted_by':'code:test'})
    before=db.current_facts(pid)
    assert report_data(db,pid,'C')['rows'] and report_data(db,pid,'B')['results']
    db.set_scope(drug['id'],False,'本项目明确排除')
    assert not report_data(db,pid,'A')['rows']
    assert not report_data(db,pid,'B')['results']
    assert not report_data(db,pid,'C')['rows']
    assert db.current_facts(pid)==before
    db.set_scope(drug['id'],None,'待核不删')
    assert report_data(db,pid,'C')['rows'] and report_data(db,pid,'B')['results']


def test_explicitly_excluded_ctgov_trial_is_not_reingested_from_a_new_search_hit(settings,monkeypatch):
    from ciw2.harness.llm import ScriptedLLM
    from ciw2.service import Service
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('适应症',['C'])
    rc=svc.context(pid,svc.db.create_run(pid))
    svc.db.upsert_entity(pid,'drug','药物')
    tid,_=svc.db.upsert_entity(pid,'trial','NCT00000001')
    svc.db.set_scope(tid,False,'明确排除')
    monkeypatch.setattr('ciw2.sources.ctgov.search',lambda *a,**kw:[{'nct':'NCT00000001','interventions':[{'name':'药物'}]}])
    def unexpected(*args,**kwargs):pytest.fail('Explicitly excluded study re-ingested')
    monkeypatch.setattr('ciw2.sources.ctgov.ingest_trial',unexpected)
    assert trial_evidence(rc)['ingested']==0


def test_real_trial_stage_source_failure_keeps_report_available_failed_run_and_resumable_units(settings,monkeypatch):
    rc,_,calls=setup(settings,monkeypatch,count=3)
    original=china_detail.browser_detail
    def fail(ctx,ctr):
        if ctr=='CTR00000001':raise RuntimeError('source temporarily blocked')
        return original(ctx,ctr)
    monkeypatch.setattr(china_detail,'browser_detail',fail)
    rendered=[]
    def render(context):
        rows=report_data(context.db,context.project_id,'C')['rows']
        rendered.append(len(rows))
        return {'rows':len(rows)}
    monkeypatch.setattr(runner,'STAGES',[next(s for s in STAGES if s.name=='trial_evidence'),Stage('render',render)])
    assert runner.execute(rc)=='failed'
    assert rendered==[2]
    stage=rc.db.one("SELECT * FROM stages WHERE run_id=? AND name='trial_evidence'",(rc.run_id,))
    assert stage['status']=='failed' and 'CTR00000001' in stage['output_json']
    assert rc.db.stage_output(rc.run_id,'render')=={'rows':2}
    monkeypatch.setattr(china_detail,'browser_detail',original)
    assert runner.execute(rc)=='succeeded' and rendered==[2,3]
    assert len(calls)==3  # Completed neighbors were not fetched again; downstream was rebuilt.
