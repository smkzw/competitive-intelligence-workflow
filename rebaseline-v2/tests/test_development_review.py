"""Owner reproductions of frozen review: no live source/model or medical approval."""
import pytest
from test_development_scope import DATE, QUOTE, SCOPE, adopt
from test_drug_enrichment import setup
from test_profile_review_regressions import stage

from ciw2.pipeline.requalify import requalify_project
from ciw2.pipeline.stages import verify
from ciw2.render.drug_profile import drug_profiles
from ciw2.render.portal import report_data
from ciw2.sources.http import register_text


@pytest.mark.parametrize('tail',['申请被拒绝','申请获受理','许可申请','计划启动'])
def test_application_or_plan_does_not_become_an_approval(settings,tail):
    text='2024年9月12日，ExampleDrug中国特应性皮炎批准上市'+tail+'。'
    _,_,_,fact=adopt(settings,text,'特应性皮炎')
    assert fact['status']=='unverified'


@pytest.mark.parametrize('mode',['current','replay','offline'])
def test_status_depends_on_the_current_formal_name_not_only_its_own_receipt(settings,mode):
    svc,rc,did=setup(settings)
    name='Formal Drug Injection'
    sid=register_text(rc.tool_ctx(),kind='regulator',url='https://example.org/names',text=name+' / Other Injection')
    base={'project_id':rc.project_id,'entity_id':did,'field':'identity.name_en','source_id':sid,
          'quote':name,'tier':'critical','status':'verified','extracted_by':'code:synthetic'}
    fid=svc.db.add_fact({**base,'value':name})
    stage(rc,did,QUOTE.replace('ExampleDrug',name),'status.china.development','批准上市',
          {'indication':SCOPE,'jurisdiction':'CN','as_of':DATE})
    verify(rc)
    assert drug_profiles(svc.db,rc.project_id)[did]['phase_china']=='approved'
    before=svc.db.query("SELECT * FROM facts WHERE field='status.china.development'")
    svc.db.add_fact({**base,'value':'Other Injection','quote':'Other Injection','supersedes':fid})
    if mode=='replay':verify(rc)
    if mode=='offline':requalify_project(svc.db,svc.cas,rc.project_id)
    assert drug_profiles(svc.db,rc.project_id)[did]['phase_china']=='unknown'
    assert svc.db.query("SELECT * FROM facts WHERE field='status.china.development'")==before


def test_actual_company_excerpt_uses_formal_identity_and_not_regulator_update_date(settings):
    svc,rc,did=setup(settings)
    name='司普奇拜单抗注射液'
    svc.db.execute('UPDATE entities SET name=? WHERE id=?',(name,did))
    # Byte-identical short excerpt from company CAS 8793a35c..., not an entire article.
    quote=('2024年9月12日，康诺亚宣布，公司自主研发的1类新药康悦达®（司普奇拜单抗注射液）'
           '正式获得国家药品监督管理局批准上市，用于治疗成人中重度特应性皮炎。')
    url='https://www.keymedbio.com/cn/newsd.html?id=22&type=2'
    sid=register_text(rc.tool_ctx(),kind='company',url=url,text=quote)
    proposal={'entity':name,'drug':name,'field':'status.china.development','value':'批准上市',
              'source_id':sid,'source_url':url,'quote':quote,'source_context':{
                  'indication':SCOPE,'jurisdiction':'CN','as_of':DATE}}
    svc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':[proposal]})
    verify(rc)
    row=report_data(svc.db,rc.project_id,'A')['rows'][0]
    assert row['phase_china']=='approved' and row['phase_china_refs'][0]['quote']==quote
    assert row['phase_china_refs'][0]['source_kind']=='company'


def test_chart_payload_retains_all_qualified_observations_and_ids(settings):
    svc,rc,did,_=adopt(settings)
    second='2025年1月2日，ExampleDrug中国儿童特应性皮炎 III期。'
    stage(rc,did,second,'status.china.development','III期',
          {'indication':'儿童特应性皮炎','jurisdiction':'CN','as_of':'2025-01-02'})
    verify(rc)
    data=report_data(svc.db,rc.project_id,'A')
    row=data['rows'][0];chart=data['charts']['landscape']['rows'][0]
    assert row['id']==chart['id']==did and row['phase_china']=='unknown'
    assert row['has_china_stage'] is True
    observations=chart['phase_observations']
    assert {(o['indication'],o['as_of'],o['phase']) for o in observations}=={
        (SCOPE,DATE,'approved'),('儿童特应性皮炎','2025-01-02','phase3')}
    assert {o['fact_id'] for o in observations}=={r['fact_id'] for r in row['phase_china_refs']}
    assert all(o['source_kind']=='company' and o['region']=='china' for o in observations)


def test_actual_english_regulator_excerpt_does_not_borrow_its_page_update_as_status_date(settings):
    svc,rc,did=setup(settings)
    name='Stapokibart Injection'
    svc.db.execute('UPDATE entities SET name=? WHERE id=?',(name,did))
    quote=('Recently, the Stapokibart Injection (trade name: 康悦达) of Chengdu Kangnuoxing Biopharma, Inc. '
           'is approved by China NMPA. It is indicated for the treatment of adult patients with '
           'moderate-to-severe atopic dermatitis in adults who are inadequately controlled by topical '
           'medications or for whom topical medications are not indicated.')
    url='https://english.nmpa.gov.cn/2025-02/19/c_1073594.htm'
    sid=register_text(rc.tool_ctx(),kind='regulator',url=url,text='Updated: 2025-02-19\n\n'+quote)
    proposal={'entity':name,'drug':name,'field':'status.china.development','value':'approved',
        'source_id':sid,'source_url':url,'quote':quote,'source_context':{
            'indication':'特应性皮炎','jurisdiction':'CN','as_of':'2025-02-19'}}
    svc.db.set_stage(rc.run_id,'enrich_drugs','succeeded',output={'facts':[proposal]})
    verify(rc)
    fact=next(f for f in svc.db.current_facts(rc.project_id) if f['field']=='status.china.development')
    assert fact['status']=='unverified' and fact['quote']==quote
    assert drug_profiles(svc.db,rc.project_id)[did]['phase_china']=='unknown'
