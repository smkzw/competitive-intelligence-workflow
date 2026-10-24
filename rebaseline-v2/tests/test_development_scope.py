"""Explicit dated approval statements retain their literal population qualification."""
import pytest
from test_drug_enrichment import setup
from test_profile_review_regressions import stage

from ciw2.pipeline.stages import verify
from ciw2.render.drug_profile import drug_profiles
from ciw2.render.portal import render_report

DATE='2024-09-12'
SCOPE='成人中重度特应性皮炎'
QUOTE=('2024年9月12日，示例公司宣布，公司自主研发的ExampleDrug正式获得'
       '国家药品监督管理局批准上市，用于治疗成人中重度特应性皮炎。')


def adopt(settings,text=QUOTE,scope=SCOPE,as_of=DATE,region='CN',field='status.china.development'):
    svc,rc,did=setup(settings)
    stage(rc,did,text,field,'批准上市',{'indication':scope,'jurisdiction':region,'as_of':as_of})
    verify(rc)
    fact=next(f for f in svc.db.current_facts(rc.project_id,did) if f['field']==field)
    return svc,rc,did,fact


def test_explicit_dated_nmpa_approval_with_population_is_verified_without_broadening(settings):
    svc,rc,did,fact=adopt(settings)
    assert fact['status']=='verified'
    assert fact['context']['indication']==SCOPE and fact['context']['as_of']==DATE
    row=drug_profiles(svc.db,rc.project_id)[did]
    assert row['phase_china']=='approved' and row['phase_global']=='unknown'
    assert row['phase_china_refs'][0]['context']['indication']==SCOPE
    html=render_report(svc.db,rc.project_id,'A')
    assert f'<div class="stage-scope">{SCOPE} · 截至 {DATE}</div>' in html
    assert QUOTE in html and f'data-fact-id="{fact["id"]}"' in html
    assert verify(rc)['replayed']==1


@pytest.mark.parametrize('scope',['成人特应性皮炎','儿童中重度特应性皮炎','青少年重度特应性皮炎'])
def test_same_disease_qualified_populations_are_kept_verbatim(settings,scope):
    svc,rc,did,fact=adopt(settings,QUOTE.replace(SCOPE,scope),scope)
    assert fact['status']=='verified'
    assert drug_profiles(svc.db,rc.project_id)[did]['phase_china_refs'][0]['context']['indication']==scope


@pytest.mark.parametrize('text,scope,as_of,region,field',[
    (QUOTE,'特应性皮炎',DATE,'CN','status.china.development'),
    (QUOTE,'儿童中重度特应性皮炎',DATE,'CN','status.china.development'),
    (QUOTE,SCOPE,'2024-09-10','CN','status.china.development'),
    (QUOTE.replace('国家药品监督管理局','美国食品药品监督管理局'),SCOPE,DATE,'CN','status.china.development'),
    (QUOTE.replace('批准上市','尚未批准上市'),SCOPE,DATE,'CN','status.china.development'),
    (QUOTE.replace('ExampleDrug正式','预计ExampleDrug正式'),SCOPE,DATE,'CN','status.china.development'),
    (QUOTE.replace('ExampleDrug正式','是否ExampleDrug正式'),SCOPE,DATE,'CN','status.china.development'),
    (QUOTE.replace('ExampleDrug正式获得','OtherDrug正式获得')+'ExampleDrug处于研发中。',SCOPE,DATE,'CN','status.china.development'),
    (QUOTE,SCOPE,DATE,'global','status.global.development'),
    (QUOTE.replace(SCOPE,'非特应性皮炎'),'非特应性皮炎',DATE,'CN','status.china.development'),
    (QUOTE.replace(SCOPE,'疑似特应性皮炎'),'疑似特应性皮炎',DATE,'CN','status.china.development'),
    (QUOTE.replace(SCOPE,'特应性皮炎样疾病'),'特应性皮炎样疾病',DATE,'CN','status.china.development'),
    (QUOTE.replace(SCOPE,'成人中重度银屑病'),'成人中重度银屑病',DATE,'CN','status.china.development'),
])
def test_missing_or_other_population_date_territory_or_disease_cannot_borrow_approval(
        settings,text,scope,as_of,region,field):
    svc,rc,did,fact=adopt(settings,text,scope,as_of,region,field)
    assert fact['status']=='unverified'
    assert drug_profiles(svc.db,rc.project_id)[did]['phase_china']=='unknown'


def test_multiple_qualified_stage_scopes_stay_visible_not_max_or_latest(settings):
    svc,rc,did,fact=adopt(settings)
    child='2025年1月2日，ExampleDrug 中国 儿童特应性皮炎 III期。'
    stage(rc,did,child,'status.china.development','III期',
          {'indication':'儿童特应性皮炎','jurisdiction':'CN','as_of':'2025-01-02'})
    verify(rc)
    row=drug_profiles(svc.db,rc.project_id)[did]
    assert row['phase_china']=='unknown'
    assert {r['context']['indication'] for r in row['phase_china_refs']}=={SCOPE,'儿童特应性皮炎'}
    html=render_report(svc.db,rc.project_id,'A')
    assert SCOPE in html and '儿童特应性皮炎' in html
    assert fact['quote']==QUOTE
