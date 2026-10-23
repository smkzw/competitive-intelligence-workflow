"""Synthetic production-contract checks; not real clinical/group evidence."""
import pytest

from ciw2.domain.models import ExtractedFact, ExtractionResult
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import extraction, stages
from ciw2.pipeline.context import IncompleteWork
from ciw2.service import Service
from ciw2.sources.http import register_text


def setup(settings):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('特应性皮炎',['A'])
    rc=svc.context(pid,svc.db.create_run(pid))
    did,_=svc.db.upsert_entity(pid,'drug','ExampleDrug',attrs={'targets':['FAKE-TARGET']})
    return svc,rc,did


def test_a_only_enrichment_is_normal_stage_and_uses_existing_nine_skills(settings,monkeypatch):
    from ciw2.pipeline.runner import stages_for
    svc,rc,did=setup(settings)
    plan=[s.name for s in stages_for(['A'])]
    assert 'enrich_drugs' in plan and 'verify' in plan
    assert plan.index('trial_evidence')<plan.index('enrich_drugs')<plan.index('verify')<plan.index('analysis_A')
    assert len(rc.skills)==9
    url='https://example.org/official'
    text='ExampleDrug targets IL-31RA.'
    sid=register_text(rc.tool_ctx(),kind='web',url=url,text=text)
    calls=[]
    def skill(name,task):
        calls.append((name,task))
        assert task['mode']=='identity_enrichment' and task['drug']['name']=='ExampleDrug'
        assert 'known_trials' not in task
        rc.cache['last_skill_source_ids']=[sid]
        return ExtractionResult(facts=[ExtractedFact(entity='ExampleDrug',field='identity.target',value='IL-31RA',
            source_url=url,source_id=sid,quote=text)])
    monkeypatch.setattr(rc,'skill',skill)
    work=next(s for s in stages.STAGES if s.name=='enrich_drugs')
    output=work.fn(rc)
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output=output)
    stages.verify(rc)
    facts=svc.db.current_facts(rc.project_id,did)
    assert [(f['value'],f['status']) for f in facts]==[('IL-31RA','verified')]
    assert work.fn(rc)==output and len(calls)==1


def test_group_context_survives_source_adoption_and_idempotent_replay(settings):
    svc,rc,did=setup(settings)
    text='ExampleGroup owns ExampleHolder as its wholly owned subsidiary as of 2025-12-31.'
    url='https://example.org/annual-report'
    sid=register_text(rc.tool_ctx(),kind='web',url=url,text=text)
    proposal=ExtractedFact(entity='ExampleDrug',field='status.china_mah_group',value='ExampleGroup',
        source_url=url,source_id=sid,quote=text,source_context={
            'legal_entity':'ExampleHolder','relationship':'wholly_owned','as_of':'2025-12-31','jurisdiction':'CN'})
    fact={**proposal.model_dump(),'drug':'ExampleDrug'}
    svc.db.add_fact({'project_id':rc.project_id,'entity_id':did,'field':'status.china_mah',
        'value':'ExampleHolder','status':'verified','tier':'critical','source_id':sid,
        'quote':text,'context':{'jurisdiction':'CN'},'extracted_by':'code:synthetic'})
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':[fact]})
    stages.verify(rc)
    row=next(f for f in svc.db.current_facts(rc.project_id,did) if f['field']=='status.china_mah_group')
    assert row['status']=='verified' and row['context']['legal_entity']=='ExampleHolder'
    assert row['context']['relationship']=='wholly_owned' and row['context']['as_of']=='2025-12-31'
    assert stages.verify(rc)['replayed']==1
    assert len(svc.db.query('SELECT * FROM facts'))==2


@pytest.mark.parametrize('field,value,quote,context',[
    ('identity.target','IL-31RA','OtherDrug targets IL-31RA.',{}),
    ('status.china_mah_group','ExampleGroup','ExampleGroup owns OtherHolder.',
     {'legal_entity':'ExampleHolder','relationship':'wholly_owned','as_of':'2025-12-31','jurisdiction':'CN'}),
    ('status.china.development','III期','ExampleDrug III期，重度哮喘，2025-12-31。',
     {'indication':'特应性皮炎','as_of':'2025-12-31','jurisdiction':'CN'}),
])
def test_source_value_alone_does_not_certify_wrong_product_or_scope(settings,field,value,quote,context):
    svc,rc,did=setup(settings)
    url='https://example.org/source'
    sid=register_text(rc.tool_ctx(),kind='web',url=url,text=quote)
    proposal=ExtractedFact(entity='ExampleDrug',field=field,value=value,source_url=url,source_id=sid,
                           quote=quote,source_context=context)
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={
        'facts':[{**proposal.model_dump(),'drug':'ExampleDrug'}]})
    stages.verify(rc)
    assert all(f['status']!='verified' for f in svc.db.current_facts(rc.project_id,did))


def test_enrichment_failure_only_retries_missing_drug(settings,monkeypatch):
    _,rc,_=setup(settings)
    rc.db.upsert_entity(rc.project_id,'drug','SecondDrug')
    calls=[]
    def skill(name,task):
        drug=task['drug']['name']
        calls.append(drug)
        if drug=='SecondDrug' and calls.count(drug)==1:raise RuntimeError('one source unit failed')
        return ExtractionResult(facts=[],gaps=['No directly sourced profile in this unit'])
    monkeypatch.setattr(rc,'skill',skill)
    work=next(s for s in stages.STAGES if s.name=='enrich_drugs')
    with pytest.raises(IncompleteWork):work.fn(rc)
    work.fn(rc)
    assert calls.count('ExampleDrug')==1 and calls.count('SecondDrug')==2


def test_identity_task_is_one_complete_drug_not_split_by_large_trial_lists(settings):
    _,rc,did=setup(settings)
    for i in range(6):
        tid,_=rc.db.upsert_entity(rc.project_id,'trial',f'NCT{i:08d}',attrs={'title':'long title '*3000})
        rc.db.link(rc.project_id,did,'drug-trial',tid)
    tasks=extraction._tasks(rc,'extract-results',rc.db.entities(rc.project_id,'drug')[0],
                            {'mode':'identity_enrichment'})
    assert len(tasks)==1 and 'known_trials' not in tasks[0]


def test_completed_source_unit_remains_usable_when_other_drugs_are_pending(settings):
    svc,rc,did=setup(settings)
    text='ExampleDrug targets IL-31RA.'
    url='https://example.org/profile'
    sid=register_text(rc.tool_ctx(),kind='company',url=url,text=text)
    proposal=ExtractedFact(entity='ExampleDrug',field='identity.target',value='IL-31RA',
                           source_url=url,source_id=sid,quote=text)
    rc.db.set_stage(rc.run_id,'enrich_drugs','failed',output={'facts':[
        {**proposal.model_dump(),'drug':'ExampleDrug'}],'pending_drug_ids':['another-drug'],
        'pending_units':[{'drug_id':'another-drug','reason':'unit_failed'}]})
    stages.verify(rc)
    assert [(f['value'],f['status']) for f in svc.db.current_facts(rc.project_id,did)]==[('IL-31RA','verified')]
    assert stages.verify(rc)['replayed']==1


def test_source_paragraph_can_supply_literal_full_name_without_guessing_short_alias(settings):
    svc,rc,did=setup(settings)
    text='ExampleDrug Injection is the source full name. Its target is IL-31RA.\n\nOtherDrug targets IL-4Rα.'
    svc.db.execute('UPDATE entities SET name=? WHERE id=?',('ExampleDrug Injection',did))
    url='https://example.org/product'
    sid=register_text(rc.tool_ctx(),kind='company',url=url,text=text)
    proposals=[{'entity':'ExampleDrug Injection','field':'identity.target','value':value,
        'quote':quote,'source_url':url,'source_id':sid,'drug':'ExampleDrug Injection'}
        for value,quote in [('IL-31RA','Its target is IL-31RA.'),('IL-4Rα','OtherDrug targets IL-4Rα.')]]
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':proposals})
    stages.verify(rc)
    facts=svc.db.current_facts(rc.project_id,did)
    supported=next(f for f in facts if f['value']=='IL-31RA')
    assert supported['status']=='verified' and supported['quote']==text.split('\n\n')[0]
    assert next(f for f in facts if f['value']=='IL-4Rα')['status']=='unverified'


def test_self_development_does_not_prove_licensing_or_rights(settings):
    svc,rc,did=setup(settings)
    text='ExampleCompany independently developed ExampleDrug.'
    url='https://example.org/developer'
    sid=register_text(rc.tool_ctx(),kind='company',url=url,text=text)
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':[{
        'entity':'ExampleDrug','field':'identity.rights_holder','value':'ExampleCompany',
        'quote':text,'source_url':url,'source_id':sid,'drug':'ExampleDrug'}]})
    stages.verify(rc)
    assert svc.db.current_facts(rc.project_id,did)[0]['status']=='unverified'
