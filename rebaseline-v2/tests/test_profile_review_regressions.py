"""Reproduce frozen01 independent-review counterexamples against production."""
import pytest
from test_drug_enrichment import setup

from ciw2.pipeline.requalify import requalify_project
from ciw2.pipeline.stages import verify
from ciw2.render.drug_profile import drug_profiles
from ciw2.render.portal import render_report
from ciw2.sources.http import register_text
from ciw2.verify.quote import check_quote


def stage(rc,did,text,field,value,context=None,entity='ExampleDrug'):
    url='https://example.org/frozen-review-source'
    sid=register_text(rc.tool_ctx(),kind='company',url=url,text=text)
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':[{
        'entity':entity,'drug':'ExampleDrug','field':field,'value':value,'source_id':sid,
        'source_url':url,'quote':text,'source_context':context or {}}]})
    return sid


def holder(rc,did,sid,context=None):
    rc.db.add_fact({'project_id':rc.project_id,'entity_id':did,'field':'status.china_mah',
        'value':'ExampleHolder','status':'verified','tier':'critical','quote':'ExampleHolder',
        'source_id':sid,'context':{'jurisdiction':'CN',**(context or {})},'extracted_by':'code:synthetic'})


def test_profile_cannot_write_other_drug_despite_correct_parent_quote(settings):
    svc,rc,did=setup(settings)
    other,_=svc.db.upsert_entity(rc.project_id,'drug','OtherDrug')
    stage(rc,did,'ExampleDrug targets IL-31RA.','identity.target','IL-31RA',entity='OtherDrug')
    result=verify(rc)
    assert not drug_profiles(svc.db,rc.project_id)[other]['targets']
    assert result['unresolved_entities']==1


@pytest.mark.parametrize('text,field,value,context',[
    ('ExampleGroup and ExampleHolder are distribution partners, not subsidiaries of each other. 2025-01-02.',
     'status.china_mah_group','ExampleGroup',{'legal_entity':'ExampleHolder','relationship':'wholly_owned',
       'jurisdiction':'CN','as_of':'2025-01-02'}),
    ('ExampleDrug 特应性皮炎 III期 is in the United States, not China. 2025-01-02.',
     'status.china.development','III期',{'indication':'特应性皮炎','jurisdiction':'CN','as_of':'2025-01-02'}),
    ('ExampleDrug 中国 特应性皮炎 III期 as of 2024-01-02. The unrelated annual meeting is 2025-01-02.',
     'status.china.development','III期',{'indication':'特应性皮炎','jurisdiction':'CN','as_of':'2025-01-02'}),
    ('ExampleDrug 中国 特应性皮炎 III期 as of 2024-01-02, and the unrelated annual meeting is 2025-01-02.',
     'status.china.development','III期',{'indication':'特应性皮炎','jurisdiction':'CN','as_of':'2025-01-02'}),
    ('ExampleDrug 特应性皮炎 III期 in the United States, while China has a separate filing as of 2025-01-02.',
     'status.china.development','III期',{'indication':'特应性皮炎','jurisdiction':'CN','as_of':'2025-01-02'}),
    ("ExampleGroup owns ExampleHolder's distributor as its wholly owned subsidiary as of 2025-01-02.",
     'status.china_mah_group','ExampleGroup',{'legal_entity':'ExampleHolder','relationship':'wholly_owned',
       'jurisdiction':'CN','as_of':'2025-01-02'}),
])
def test_context_cooccurrence_does_not_certify_opposite_or_unrelated_statement(settings,text,field,value,context):
    svc,rc,did=setup(settings)
    sid=stage(rc,did,text,field,value,context)
    if field=='status.china_mah_group':holder(rc,did,sid)
    verify(rc)
    assert not any(f['field']==field and f['status']=='verified' for f in svc.db.current_facts(rc.project_id,did))


@pytest.mark.parametrize('label,number',[('5-HT2A',5),('2F8',2)])
def test_digit_starting_identifiers_do_not_certify_clinical_counts(label,number):
    text=f'The scientific label is {label}.'
    assert not check_quote(text,text,number).ok
    assert check_quote(text,text,label).ok


@pytest.mark.parametrize('label',['5‑HT2A','5‐HT2A','5‒HT2A'])
def test_unicode_identifiers_do_not_supply_clinical_numbers(label):
    source=f'The target is {label}.'
    assert not check_quote(source,source,5).ok
    assert check_quote(source,source,label).ok


@pytest.mark.parametrize('unit',['µg','μg','µg/kg'])
def test_microgram_units_use_the_same_unicode_normalization_as_source(unit):
    text=f'The dose was 10{unit}.'
    assert check_quote(text,text,10).ok


@pytest.mark.parametrize('quote',[
    'ExampleDrug is compared with OtherDrug, which targets IL-31RA.',
    'ExampleDrug is the source full name. ComparatorDrug targets IL-31RA.',
    'ExampleDrug is the source full name.\n\nComparatorDrug targets IL-31RA.',
])
def test_unknown_or_other_named_subject_cannot_borrow_target(settings,quote):
    svc,rc,did=setup(settings)
    stage(rc,did,quote,'identity.target','IL-31RA')
    verify(rc)
    assert drug_profiles(svc.db,rc.project_id)[did]['targets']==[]


@pytest.mark.parametrize('legacy',[False,True])
def test_quote_expansion_idempotence_does_not_depend_on_cas_availability(settings,legacy):
    svc,rc,did=setup(settings)
    text='ExampleDrug is the source full name. Its target is IL-31RA.'
    sid=stage(rc,did,text,'identity.target','IL-31RA')
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':[{
        'entity':'ExampleDrug','drug':'ExampleDrug','field':'identity.target','value':'IL-31RA',
        'source_id':sid,'source_url':'https://example.org/frozen-review-source','quote':'Its target is IL-31RA.'}]})
    if legacy:
        from ciw2.pipeline.verification import _proposal_id
        raw=svc.db.stage_output(rc.run_id,'enrich_drugs')['facts'][0]
        fid=_proposal_id(rc,'enrich_drugs',{**raw,'quote':text})
        svc.db.add_fact({'id':fid,'project_id':rc.project_id,'entity_id':did,'field':'identity.target',
            'value':'IL-31RA','status':'verified','tier':'standard','quote':text,'source_id':sid,
            'extracted_by':'llm:legacy'})
    verify(rc)
    before=svc.db.query('SELECT * FROM facts')
    source=svc.db.one('SELECT text_digest FROM sources WHERE id=?',(sid,))
    path=svc.cas._path(source['text_digest']);raw=path.read_bytes()
    path.unlink()
    try:
        assert verify(rc)['replayed']==1
        assert svc.db.query('SELECT * FROM facts')==before
    finally:
        path.write_bytes(raw)
    assert verify(rc)['replayed']==1 and svc.db.query('SELECT * FROM facts')==before


@pytest.mark.parametrize('source,value',[('The dose was 10mg/kg.',10),('The level was 1e-3mg/mL.',0.001),
    ('The pressure was 120mmHg.',120),('The level was 3ULN.',3)])
def test_attached_units_and_exponents_remain_numeric_evidence(source,value):
    assert check_quote(source,source,value).ok


def test_offline_requalification_applies_actual_entity_guard(settings):
    svc,rc,did=setup(settings)
    text='OtherDrug targets IL-31RA.'
    sid=register_text(rc.tool_ctx(),kind='company',url='https://example.org/legacy',text=text)
    fid=svc.db.add_fact({'project_id':rc.project_id,'entity_id':did,'field':'identity.target','value':'IL-31RA',
        'status':'verified','tier':'standard','quote':text,'source_id':sid,'extracted_by':'llm:legacy'})
    before=svc.db.one('SELECT * FROM facts WHERE id=?',(fid,))
    result=requalify_project(svc.db,svc.cas,rc.project_id)
    assert result['counts']['invalidated']==1
    assert drug_profiles(svc.db,rc.project_id)[did]['targets']==[]
    assert svc.db.one('SELECT * FROM facts WHERE id=?',(fid,))==before


def test_expired_holder_does_not_regain_current_mah_group_role(settings):
    svc,rc,did=setup(settings)
    text='ExampleGroup owns ExampleHolder as its wholly owned subsidiary as of 2025-01-02.'
    context={'legal_entity':'ExampleHolder','relationship':'wholly_owned','jurisdiction':'CN','as_of':'2025-01-02'}
    sid=stage(rc,did,text,'status.china_mah_group','ExampleGroup',context)
    holder(rc,did,sid,{'valid_until':'2024-01-01','observed_at':'2025-01-02T00:00:00+00:00'})
    verify(rc)
    groups=drug_profiles(svc.db,rc.project_id)[did]['group_refs']
    assert len(groups)==1 and groups[0]['role']=='许可记录持有人所属集团'
    assert '中国MAH所属集团' not in render_report(svc.db,rc.project_id,'A')


@pytest.mark.parametrize('date_text',['January 2, 2025','2 January 2025','2025年01月02日'])
def test_explicit_claim_date_spelling_is_not_a_false_gap(settings,date_text):
    svc,rc,did=setup(settings)
    stage(rc,did,f'ExampleDrug 中国 特应性皮炎 III期 as of {date_text}.','status.china.development','III期',
          {'indication':'特应性皮炎','jurisdiction':'CN','as_of':'2025-01-02'})
    verify(rc)
    assert drug_profiles(svc.db,rc.project_id)[did]['phase_china']=='phase3'
