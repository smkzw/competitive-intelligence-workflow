"""Source-backed trade names bridge profile wording, not discovery guesses (synthetic)."""
import json

import pytest
from test_nmpa_ingest import certificate, drug, registered

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import stages
from ciw2.service import Service
from ciw2.sources import nmpa_ingest
from ciw2.sources.http import register_text


def setup(settings):
    svc=Service(settings,llm_factory=lambda _:(ScriptedLLM([]),None))
    pid=svc.create_project('特应性皮炎',['A'])
    rc=svc.context(pid,svc.db.create_run(pid));ctx=rc.tool_ctx()
    did=drug(ctx,'Drug A Injection')
    raw=certificate()
    raw['rows'].extend([['商品名（中文）','商品甲'],['商品名（英文）','BrandA']])
    sid=registered(ctx,raw)
    before=svc.db.one('SELECT * FROM sources WHERE id=?',(sid,))
    nmpa_ingest.activate_source(ctx,sid)
    assert svc.db.one('SELECT * FROM sources WHERE id=?',(sid,))==before
    return svc,rc,ctx,did,sid


def propose(rc,field,value,text):
    url='https://example.org/company-product'
    sid=register_text(rc.tool_ctx(),kind='company',url=url,text=text)
    raw={'entity':'Drug A Injection','drug':'Drug A Injection','field':field,'value':value,
         'source_id':sid,'source_url':url,'quote':text,'extraction_model':'synthetic-model'}
    rc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':[raw]})
    stages.verify(rc)
    return next(f for f in rc.db.current_facts(rc.project_id) if f['field']==field)


def test_literal_registered_trade_names_are_additive_current_facts_with_locators(settings):
    svc,rc,ctx,did,sid=setup(settings)
    brands=[f for f in svc.db.current_facts(rc.project_id,did) if f['field'].startswith('identity.trade_name')]
    assert {f['field']:f['value'] for f in brands}=={
        'identity.trade_name_zh':'商品甲','identity.trade_name_en':'BrandA'}
    assert all(f['source_id']==sid and f['extracted_by']=='code:nmpa' and f['status']=='verified' for f in brands)
    assert all(f['context']['json_path'].startswith('$.rows[') and f['quote'].startswith('商品名') for f in brands)
    assert nmpa_ingest.activate_source(ctx,sid)['facts_added']==0
    assert not [f for f in brands if f['supersedes']]


@pytest.mark.parametrize('field,value,text',[
    ('identity.target','IL-31RA','国内自主研发IL-31RA抗体药物商品甲®获批。'),
    ('identity.modality','IL-31RA抗体','国内自主研发IL-31RA抗体药物商品甲®获批。'),
    ('identity.target','IL-31RA','作为国内首个申报的IL-31RA抗体药物，商品甲®的上市。'),
    ('identity.modality','IL-31RA抗体','作为国内首个申报的IL-31RA抗体药物，商品甲®的上市。'),
])
def test_registered_product_class_apposition_is_a_bound_positive_not_cooccurrence(settings,field,value,text):
    _,rc,_,_,_=setup(settings)
    assert propose(rc,field,value,text)['status']=='verified'


@pytest.mark.parametrize('text',[
    'IL-31RA抗体药物其他商品获批，商品甲®只作为对照。',
    '商品甲®与IL-31RA抗体药物OtherDrug比较。',
    '非IL-31RA抗体药物商品甲®。',
    '商品甲®不是IL-31RA抗体药物。',
    '作为另一药物的IL-31RA抗体药物，OtherDrug获批。商品甲®属于其他类型。',
    'IL-31RA抗体药物商品甲Plus获批。',
    '非 IL-31RA抗体药物商品甲®。',
    '作为非 IL-31RA抗体药物，商品甲®的上市。',
    'IL-4Rα/IL-31RA抗体药物商品甲®获批。',
])
def test_registered_brand_does_not_borrow_other_class_or_negation(settings,text):
    _,rc,_,_,_=setup(settings)
    assert propose(rc,'identity.target','IL-31RA',text)['status']=='unverified'


def test_discovery_brand_never_certifies_scientific_identity(settings):
    _,rc,_,did,_=setup(settings)
    rc.db.execute('UPDATE entities SET aliases=? WHERE id=?',(json.dumps(['DiscoveryBrand']),did))
    fact=propose(rc,'identity.target','IL-31RA','国内自主研发IL-31RA抗体药物DiscoveryBrand获批。')
    assert fact['status']=='unverified'


def test_same_brand_on_two_registered_products_is_not_an_identity_shortcut(settings):
    _,rc,ctx,_,_=setup(settings)
    drug(ctx,'Other Injection')
    other=certificate(seed='b',number='国药准字SJ20240002',name='其他药注射液',name_en='Other Injection')
    other['rows'].append(['商品名（中文）','商品甲'])
    nmpa_ingest.activate_source(ctx,registered(ctx,other))
    fact=propose(rc,'identity.target','IL-31RA','国内自主研发IL-31RA抗体药物商品甲®获批。')
    assert fact['status']=='unverified'


@pytest.mark.parametrize('change',('withdrawn','ambiguous'))
def test_saved_verdict_cannot_outlive_its_current_registered_brand_basis(settings,change):
    svc,rc,ctx,_,_=setup(settings)
    fact=propose(rc,'identity.target','IL-31RA','国内自主研发IL-31RA抗体药物商品甲®获批。')
    assert fact['status']=='verified'
    original=svc.db.one('SELECT * FROM facts WHERE id=?',(fact['id'],))
    if change=='withdrawn':
        raw=certificate(observed='2026-10-24T01:00:00Z')
    else:
        drug(ctx,'Other Injection')
        raw=certificate(seed='b',number='国药准字SJ20240002',name='其他药注射液',name_en='Other Injection')
        raw['rows'].append(['商品名（中文）','商品甲'])
    nmpa_ingest.activate_source(ctx,registered(ctx,raw))
    current=next(f for f in svc.db.current_facts(rc.project_id) if f['id']==fact['id'])
    assert current['status']=='unverified'
    assert svc.db.one('SELECT * FROM facts WHERE id=?',(fact['id'],))==original
    result=stages.verify(rc)
    assert result['reassessed']==1
    current=next(f for f in svc.db.current_facts(rc.project_id) if f['id']==fact['id'])
    assert current['status']=='unverified' and current['verdict']=='invalidated'


def test_identity_change_between_prepare_and_commit_cannot_report_acceptance(settings,monkeypatch):
    from ciw2.pipeline import verification
    _,rc,ctx,_,_=setup(settings)
    prepare=verification.prepare
    def revoke(*args,**kwargs):
        result=prepare(*args,**kwargs)
        nmpa_ingest.activate_source(ctx,registered(ctx,certificate(observed='2026-10-24T01:00:00Z')))
        return result
    monkeypatch.setattr(verification,'prepare',revoke)
    row=propose(rc,'identity.target','IL-31RA','国内自主研发IL-31RA抗体药物商品甲®获批。')
    assert row['stored_status']=='unverified'


def test_reassessment_commit_rechecks_identity_basis_without_false_verified_stats(settings,monkeypatch):
    from ciw2.pipeline import verification
    from ciw2.verify import assessment
    _,rc,ctx,_,_=setup(settings)
    assert propose(rc,'identity.target','IL-31RA','国内自主研发IL-31RA抗体药物商品甲®获批。')['status']=='verified'
    monkeypatch.setattr(assessment,'rule_identity',lambda:'synthetic-new-rule')
    prepare=verification.prepare
    def revoke(*args,**kwargs):
        result=prepare(*args,**kwargs)
        nmpa_ingest.activate_source(ctx,registered(ctx,certificate(observed='2026-10-24T01:00:00Z')))
        return result
    monkeypatch.setattr(verification,'prepare',revoke)
    result=stages.verify(rc)
    assert result['stats']['verified']==0 and result['stats']['unverified']==1


def test_official_name_withdrawal_invalidates_a_name_supported_target(settings):
    svc,rc,ctx,_,_=setup(settings)
    nmpa_ingest.activate_source(ctx,registered(ctx,certificate(observed='2026-10-24T01:00:00Z')))
    row=propose(rc,'identity.target','IL-31RA','药物甲注射液 targets IL-31RA.')
    assert row['status']=='verified'
    original=svc.db.one('SELECT * FROM facts WHERE id=?',(row['id'],))
    nmpa_ingest.activate_source(ctx,registered(ctx,certificate(name='药物乙注射液',observed='2026-10-24T02:00:00Z')))
    assert next(f for f in svc.db.current_facts(rc.project_id) if f['id']==row['id'])['status']=='unverified'
    assert svc.db.one('SELECT * FROM facts WHERE id=?',(row['id'],))==original


@pytest.mark.parametrize('prefix',('尚无证据表明','目前无','没有','未见','未发现','無'))
def test_negative_existence_is_not_a_supported_drug_class(settings,prefix):
    _,rc,_,_,_=setup(settings)
    assert propose(rc,'identity.target','IL-31RA',prefix+'IL-31RA抗体药物商品甲获批。')['status']=='unverified'


def test_registered_short_brand_does_not_steal_a_longer_chinese_brand(settings):
    _,rc,ctx,_,_=setup(settings)
    drug(ctx,'Other Injection')
    raw=certificate(seed='b',number='国药准字SJ20240002',name='其他药注射液',name_en='Other Injection')
    raw['rows'].append(['商品名（中文）','商品甲乙'])
    nmpa_ingest.activate_source(ctx,registered(ctx,raw))
    assert propose(rc,'identity.target','IL-31RA','IL-31RA抗体药物商品甲乙获批。')['status']=='unverified'


@pytest.mark.parametrize('dry_run',(False,True))
def test_offline_receipt_append_rechecks_its_current_identity_basis(settings,monkeypatch,dry_run):
    from ciw2.pipeline.requalify import requalify_project
    from ciw2.verify import assessment
    svc,rc,ctx,_,_=setup(settings)
    row=propose(rc,'identity.target','IL-31RA','国内自主研发IL-31RA抗体药物商品甲获批。')
    assert row['status']=='verified'
    monkeypatch.setattr(assessment,'rule_identity',lambda:'synthetic-offline-new-rule')
    inspect=assessment.inspect_fact
    def revoke(*args,**kwargs):
        result=inspect(*args,**kwargs)
        nmpa_ingest.activate_source(ctx,registered(ctx,certificate(observed='2026-10-24T01:00:00Z')))
        return result
    monkeypatch.setattr(assessment,'inspect_fact',revoke)
    result=requalify_project(svc.db,svc.cas,rc.project_id,dry_run=dry_run)
    assert result['counts']['confirmed']==0 and result['counts']['errors']==1
    assert row['id'] not in svc.db.latest_verdicts(rc.project_id)


def test_later_longer_brand_invalidates_previous_prefix_acceptance(settings):
    svc,rc,ctx,_,_=setup(settings)
    row=propose(rc,'identity.target','IL-31RA','IL-31RA抗体药物商品甲注射液获批。')
    assert row['status']=='verified'
    drug(ctx,'Other Injection')
    raw=certificate(seed='b',number='国药准字SJ20240002',name='其他药注射液',name_en='Other Injection')
    raw['rows'].append(['商品名（中文）','商品甲注射液'])
    nmpa_ingest.activate_source(ctx,registered(ctx,raw))
    assert next(f for f in svc.db.current_facts(rc.project_id) if f['id']==row['id'])['status']=='unverified'


@pytest.mark.parametrize('text',('IL-31RA抗体药物商品甲获批。','IL-31RA抗体药物商品甲注射液。',
    'IL-31RA抗体药物商品甲用于无进展生存期评估。'))
def test_chinese_suffix_and_non_negated_clinical_term_are_not_blanket_rejected(settings,text):
    _,rc,_,_,_=setup(settings)
    assert propose(rc,'identity.target','IL-31RA',text)['status']=='verified'


@pytest.mark.parametrize('text,expected',(
    ('目前无IL-31RA抗体药物商品甲。','unverified'),
    ('IL-31RA抗体药物商品甲的无进展生存期显著延长且获批。','verified'),
))
def test_existence_negation_is_local_not_an_arbitrary_outcome_window(settings,text,expected):
    _,rc,_,_,_=setup(settings)
    assert propose(rc,'identity.target','IL-31RA',text)['status']==expected


@pytest.mark.parametrize('introduce_first',(True,False))
def test_competing_shorter_brand_makes_dosage_suffix_interpretation_ambiguous(settings,introduce_first):
    svc,rc,ctx,did,_=setup(settings)
    raw=certificate(observed='2026-10-24T01:00:00Z')
    raw['rows'].append(['商品名（中文）','独立品牌注射液'])
    nmpa_ingest.activate_source(ctx,registered(ctx,raw))
    def shorter():
        drug(ctx,'Other Injection')
        other=certificate(seed='b',number='国药准字SJ20240002',name='其他药注射液',name_en='Other Injection')
        other['rows'].append(['商品名（中文）','独立品牌'])
        nmpa_ingest.activate_source(ctx,registered(ctx,other))
    if introduce_first:shorter()
    row=propose(rc,'identity.target','IL-31RA','IL-31RA抗体药物独立品牌注射液获批。')
    if not introduce_first:
        assert row['status']=='verified'
        shorter()
    assert next(f for f in svc.db.current_facts(rc.project_id,did) if f['id']==row['id'])['status']=='unverified'
