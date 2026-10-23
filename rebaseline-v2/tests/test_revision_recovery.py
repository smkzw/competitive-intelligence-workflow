import pytest

from ciw2.domain.models import ExtractedFact, ExtractionResult
from ciw2.harness.llm import LLMError, ScriptedLLM
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.stages import _design_extra, _extract, cross_check, verify
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service
from ciw2.sources.http import register_text


def project(settings):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('设计',['C'])
    rid=svc.db.create_run(pid)
    rc=svc.context(pid,rid)
    trial,_=svc.db.upsert_entity(pid,'trial','NCT00000001')
    old_source=register_text(rc.tool_ctx(),kind='ctgov',url='https://example.org/registry',text='Planned size 941.')
    old=svc.db.add_fact({'project_id':pid,'entity_id':trial,'field':'design.sample_size','value':941,
        'tier':'critical','status':'verified','extracted_by':'code:ctgov','source_id':old_source,
        'quote':'Planned size 941.','context':{'enrollment_type':'ESTIMATED'}})
    url='https://example.org/amendment'
    register_text(rc.tool_ctx(),kind='web',url=url,text='The amended planned sample size is 1000. Allocation RANDOMIZED.')
    return svc,rc,old,url


def proposal(old,url,*,value=1000,quote='The amended planned sample size is 1000.'):
    return {**ExtractedFact(entity='NCT00000001',field='design.sample_size',value=value,
        source_url=url,quote=quote,supersedes=old).model_dump(),'drug':'Study drug','enrollment_type':'ESTIMATED'}


def stage(rc,facts,status='succeeded'):
    rc.db.set_stage(rc.run_id,'extract_design',status,output={'facts':facts})
    rc.stage='verify'


@pytest.mark.parametrize('revision',[True,False])
def test_exact_verification_replay_preserves_all_fact_bytes_and_status(settings,revision):
    _,rc,old,url=project(settings)
    fact=proposal(old if revision else None,url)
    stage(rc,[fact])
    verify(rc)
    rows=rc.db.query('SELECT * FROM facts WHERE project_id=? ORDER BY rowid',(rc.project_id,))
    verify(rc)
    assert rc.db.query('SELECT * FROM facts WHERE project_id=? ORDER BY rowid',(rc.project_id,))==rows


def test_rejected_revision_does_not_mask_current_verified_value_in_portal(settings):
    svc,rc,old,url=project(settings)
    stage(rc,[proposal(old,url,value=999,quote='Not present in the source.')])
    verify(rc)
    data=report_data(svc.db,rc.project_id,'C')
    assert data['rows'][0]['sample_size']==941
    assert data['charts']['size']['values']==[941]
    assert len(data['rows'][0]['sources']['sample_size'])==2


def test_verify_write_failure_rolls_back_whole_adoption_but_not_sources(settings,monkeypatch):
    _,rc,old,url=project(settings)
    second={**proposal(None,url), 'field':'design.allocation','value':'RANDOMIZED','quote':'Allocation RANDOMIZED.'}
    stage(rc,[proposal(old,url),second])
    before=rc.db.query('SELECT * FROM facts WHERE project_id=? ORDER BY rowid',(rc.project_id,))
    entities=rc.db.entities(rc.project_id)
    sources=rc.db.query('SELECT * FROM sources WHERE project_id=? ORDER BY rowid',(rc.project_id,))
    original=rc.db.add_fact
    calls=[]
    def failing(fact):
        calls.append(fact)
        if len(calls)==2:
            raise RuntimeError('synthetic second-write failure')
        return original(fact)
    monkeypatch.setattr(rc.db,'add_fact',failing)
    with pytest.raises(RuntimeError,match='second-write'):
        verify(rc)
    assert rc.db.query('SELECT * FROM facts WHERE project_id=? ORDER BY rowid',(rc.project_id,))==before
    assert rc.db.entities(rc.project_id)==entities
    assert rc.db.query('SELECT * FROM sources WHERE project_id=? ORDER BY rowid',(rc.project_id,))==sources
    monkeypatch.setattr(rc.db,'add_fact',original)
    verify(rc)
    current=rc.db.current_facts(rc.project_id)
    assert [f['value'] for f in current if f['field']=='design.sample_size']==[1000]


def test_adopted_revision_exposes_immutable_prior_value_and_source(settings):
    svc,rc,old,url=project(settings)
    old_bytes=rc.db.one('SELECT * FROM facts WHERE id=?',(old,))
    stage(rc,[proposal(old,url)])
    verify(rc)
    data=report_data(svc.db,rc.project_id,'C')
    ref=data['rows'][0]['sources']['sample_size'][0]
    assert ref['supersedes']['fact_id']==old
    assert ref['supersedes']['value']==941
    assert ref['supersedes']['url']=='https://example.org/registry'
    assert rc.db.one('SELECT * FROM facts WHERE id=?',(old,))==old_bytes
    html=render_report(svc.db,rc.project_id,'C')
    assert '修订前记录' in html and '941' in html and '1000' in html
    assert f'data-fact-id="{old}"' in html and 'https://example.org/registry' in html


def test_partial_extraction_retry_does_not_reexecute_healthy_drug_after_verification(settings,monkeypatch):
    _,rc,old,url=project(settings)
    for name in ('Alpha','Beta'):
        drug,_=rc.db.upsert_entity(rc.project_id,'drug',name)
        trial=rc.db.entities(rc.project_id,'trial')[0]['id']
        rc.db.link(rc.project_id,drug,'drug-trial',trial)
    calls=[]
    def extract(name,task):
        drug=task['drug']['name']
        calls.append(drug)
        if drug=='Beta' and calls.count('Beta')==1:
            raise LLMError('one missing unit')
        return ExtractionResult(facts=[ExtractedFact.model_validate({k:v for k,v in proposal(old,url).items() if k!='drug'})]
                                if drug=='Alpha' else [],gaps=[])
    monkeypatch.setattr(rc,'skill',extract)
    work=_extract('extract-design',_design_extra)
    with pytest.raises(IncompleteWork) as caught:
        work(rc)
    rc.db.set_stage(rc.run_id,'extract_design','failed',output=caught.value.output)
    verify(rc)
    work(rc)
    assert calls.count('Alpha')==1 and calls.count('Beta')==2


@pytest.mark.parametrize('context',[{'enrollment_type':'ACTUAL'}, {'enrollment_type':None},
                                  {'arm':'Treatment A'}, {'timepoint':'Week 24'},
                                  {'population':'Treated patients'}, {'unit':'per arm'}])
def test_cross_context_revision_retains_both_verified_observations(settings,context):
    svc,rc,old,url=project(settings)
    stage(rc,[{**proposal(old,url),**context}])
    verify(rc)
    current=rc.db.current_facts(rc.project_id)
    assert {f['value'] for f in current}=={941,1000}
    assert all(f['status']=='verified' for f in current)
    assert all(not f['supersedes'] for f in current)
    row=report_data(svc.db,rc.project_id,'C')['rows'][0]
    assert row.get('sample_size') is None
    assert len(row['observations']['sample_size'])==2
    assert report_data(svc.db,rc.project_id,'C')['charts']['size']['values']==[]


def test_competing_verified_scalars_are_order_independent_and_all_reachable(settings):
    svc,rc,old,url=project(settings)
    stage(rc,[proposal(None,url)])
    verify(rc)
    facts=rc.db.current_facts(rc.project_id)
    data=report_data(svc.db,rc.project_id,'C')
    assert data['rows'][0].get('sample_size') is None
    assert {ref['value'] for ref in data['rows'][0]['observations']['sample_size']}=={941,1000}
    assert data['charts']['size']['values']==[]
    assert old in {ref['fact_id'] for ref in data['rows'][0]['observations']['sample_size']}
    from ciw2.render.design import design_data
    original=svc.db.current_facts
    svc.db.current_facts=lambda *_:list(reversed(facts))
    assert design_data(svc.db,rc.project_id,{})==data
    svc.db.current_facts=original


def test_pinned_extraction_source_is_not_rebound_to_later_bytes(settings):
    _,rc,old,url=project(settings)
    source=rc.db.one('SELECT * FROM sources WHERE project_id=? AND url=?',(rc.project_id,url))
    f={**proposal(old,url),'source_id':source['id']}
    newer=register_text(rc.tool_ctx(),kind='web',url=url,text='The revised planned sample size is 1100.')
    assert newer!=source['id']
    stage(rc,[f])
    verify(rc)
    current=rc.db.current_facts(rc.project_id)
    assert len(current)==1 and current[0]['source_id']==source['id'] and current[0]['status']=='verified'


def test_foreign_source_id_cannot_verify_a_project_fact(settings):
    svc,rc,old,url=project(settings)
    other=svc.create_project('Other',['C'])
    other_rc=svc.context(other,svc.db.create_run(other))
    sid=register_text(other_rc.tool_ctx(),kind='web',url=url,text='The amended planned sample size is 1000.')
    stage(rc,[{**proposal(old,url),'source_id':sid}])
    verify(rc)
    latest=rc.db.current_facts(rc.project_id)
    assert any(f['id']==old for f in latest)
    assert all(f['source_id']!=sid for f in latest)
    assert next(f for f in latest if f['id']!=old)['status']=='unverified'


@pytest.mark.parametrize('read_versions',['old_only','ambiguous'])
def test_extraction_metadata_uses_read_version_not_latest_observation(settings,monkeypatch,read_versions):
    from ciw2.pipeline.extraction import _call
    _,rc,old,url=project(settings)
    prior=rc.db.one('SELECT id FROM sources WHERE project_id=? AND url=?',(rc.project_id,url))['id']
    newer=register_text(rc.tool_ctx(),kind='web',url=url,text='The revised planned sample size is 1100.')
    def skill(*args):
        rc.cache['last_skill_source_ids']=[prior] if read_versions=='old_only' else [prior,newer]
        return ExtractionResult(facts=[ExtractedFact.model_validate(
            {k:v for k,v in proposal(old,url).items() if k!='drug'})])
    monkeypatch.setattr(rc,'skill',skill)
    out=_call(rc,'extract-design',{},f'probe:{read_versions}')
    assert out['facts'][0]['source_id']==(prior if read_versions=='old_only' else None)


def test_optional_cross_check_receives_enrollment_type():
    import json

    from ciw2.harness.llm import LLMReply

    def respond(messages):
        payload=json.loads(messages[0]['content'].split('\n',1)[1])
        assert payload['enrollment_type']=='ACTUAL'
        return LLMReply(content='YES')
    assert cross_check(ScriptedLLM(respond),{'field':'design.sample_size','value':299,
        'enrollment_type':'ACTUAL','quote':'299 patients had been enrolled'}) is True
