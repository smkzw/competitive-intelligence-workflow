"""Priority directory is its own observed source, not an approval or MAH fact."""
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from test_cde_review_browser import invoke

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import china, china_browser


def captures():
    source=json.loads((Path(__file__).parent/'fixtures/cde-priority.json').read_text())
    first=deepcopy(source);first['rows']=source['rows'][:2]
    first['pagination']={'current':1,'page_size':2,'text':'共 3 条'}
    last=deepcopy(source);last['rows']=source['rows'][2:3]
    last['pagination']={'current':2,'page_size':2,'text':'共 3 条'}
    return [first,last]


@pytest.fixture
def ctx(settings):
    svc=Service(replace(settings,china_ego_space_id=84),llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('公开目录测试',['A']);return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def test_explicit_priority_public_contract():
    assert china.ChinaArgs(registry='cde',query='JXHS2600124',query_kind='acceptance_number',
        cde_section='priority_included',route_id='priority').cde_section=='priority_included'


def test_priority_source_preserves_nine_columns_and_distinct_dates():
    from ciw2.sources.cde_priority import parse_capture
    pages=captures();parsed=parse_capture(pages,query='JXHS2600124')
    assert parsed['complete'] and parsed['matched_count']==1
    row=parsed['results'][0]
    assert row['raw_cells']==pages[0]['rows'][0]
    assert row['registration_applicant_text']=='百时美施贵宝（中国）投资有限公司'
    assert row['handled_date_text']=='2026-10-10' and row['application_date_text']=='2026-09-18'
    assert row['publicity_date_text']=='2026-10-12' and row['directory_status_text']=='已纳入'
    assert not {'approved','mah','trial_id','target_indication'} & row.keys()


@pytest.mark.parametrize('mutation',['section','headers','filters','ordinal','partial'])
def test_unclosed_or_wrong_priority_scope_cannot_supply_a_result(mutation):
    from ciw2.sources.cde_capture import CaptureError
    from ciw2.sources.cde_priority import parse_capture
    pages=captures()
    if mutation=='section':pages[0]['section']='priority_proposed'
    if mutation=='headers':pages[0]['headers'][3]='上市许可持有人'
    if mutation=='filters':pages[0]['filters']['acceptance_number']='JXHS2600124'
    if mutation=='ordinal':pages[1]['rows'][0][0]='2'
    if mutation=='partial':pages=pages[:1]
    with pytest.raises(CaptureError):parse_capture(pages,query='JXHS2600124')


def test_priority_one_scope_cache_retains_partial_and_requires_new_run_recheck(ctx,monkeypatch):
    from ciw2.sources import cde_priority
    calls=[]
    def captured(*a,**kw):calls.append(kw);return invoke(captures())
    monkeypatch.setattr(china_browser,'_invoke',captured)
    first=cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number')
    second=cde_priority.browser_search(ctx,'JXHS2600125','acceptance_number')
    assert len(calls)==1 and first['source_id']==second['source_id'] and second['matched_count']==1
    fresh=replace(ctx,run_id=ctx.db.create_run(ctx.project_id));cde_priority.browser_search(fresh,'JXHS2600124','acceptance_number')
    assert len(calls)==2 and not ctx.db.current_facts(ctx.project_id)
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(first['source_id'],))
    assert json.loads(source['meta'])['request_context']['section']=='priority_included'
    ctx.cas._path(source['digest']).write_bytes(b'owned corrupt fixture')
    with pytest.raises(china_browser.BrowserFailed):cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number')


def test_incomplete_priority_pages_retained_without_success(ctx,monkeypatch):
    from ciw2.sources import cde_priority
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke(captures()[:1],status='failed'))
    with pytest.raises(china_browser.BrowserFailed):cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number')
    assert json.loads(ctx.db.one('SELECT meta FROM sources')['meta'])['complete'] is False


def test_priority_tool_does_not_create_a_trial_or_approval(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke(captures()))
    result=china._china(ctx,china.ChinaArgs(registry='cde',query='JXHS2600124',query_kind='acceptance_number',
        cde_section='priority_included',route_id='cde:priority'))
    assert result['mode']=='browser' and result['count']==1 and result['linked_refs']==0
    assert not result['persisted'] and not ctx.db.entities(ctx.project_id,'drug')
    assert not ctx.db.entities(ctx.project_id,'trial') and not ctx.db.current_facts(ctx.project_id)


@pytest.mark.parametrize('kind',['indication','drug_name','company'])
def test_unobserved_priority_query_kind_is_rejected_before_browser(ctx,monkeypatch,kind):
    from ciw2.sources import cde_priority
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:pytest.fail('must not access browser'))
    with pytest.raises(china_browser.BrowserBlocked):cde_priority.browser_search(ctx,'皮炎',kind)


def test_priority_partial_resume_rechecks_first_page_and_reuses_only_verified_page(ctx,monkeypatch):
    from ciw2.sources import cde_priority
    source=captures();raw=source[0]['rows']+source[1]['rows']
    pages=[{**deepcopy(source[0]),'rows':[row],
            'pagination':{'current':i+1,'page_size':1,'text':'共 3 条'}} for i,row in enumerate(raw)]
    calls=[]
    def capture(*a,**kw):
        calls.append(kw['options']['resume'])
        if len(calls)==1:return invoke(pages[:2],status='failed')
        assert kw['options']['resume']['pages_read']==[1,2]
        return '\n'.join([*('CIW_CHINA_PAGE:'+json.dumps(p) for p in [pages[0],pages[2]]),
            'CIW_CHINA_END:'+json.dumps({'status':'ok','resume_used':True,'reused_pages':[2],'new_pages_checked':[1,3]})]),True
    monkeypatch.setattr(china_browser,'_invoke',capture)
    with pytest.raises(china_browser.BrowserFailed):cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number')
    old=ctx.db.one('SELECT * FROM sources')
    result=cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number')
    assert result['complete'] and result['total_records']==3 and len(calls)==2
    assert ctx.db.one('SELECT * FROM sources WHERE id=?',(old['id'],))==old
    source=ctx.db.one('SELECT meta FROM sources WHERE id=?',(result['source_id'],))
    assert json.loads(source['meta'])['reused_pages']==[2]


@pytest.mark.parametrize('pager',[None,[], 'not a pager'])
def test_priority_malformed_pagination_is_a_source_validation_failure(pager):
    from ciw2.sources.cde_capture import CaptureError
    from ciw2.sources.cde_priority import parse_capture
    pages=captures();pages[0]['pagination']=pager
    with pytest.raises(CaptureError):parse_capture(pages)


def test_legitimate_acceptance_binding_receives_only_priority_reference(ctx,monkeypatch):
    from test_cde_browser import capture
    acceptance=capture();acceptance['filters']['drug_name']='玛伐凯泰胶囊'
    acceptance['rows'][0][1]='JXHS2600124';acceptance['rows'][0][2]='玛伐凯泰胶囊'
    def fetch(*a,**kw):
        return invoke([acceptance]) if kw['script_path'].name=='cde_browser.mjs' else invoke(captures())
    monkeypatch.setattr(china_browser,'_invoke',fetch)
    china._china(ctx,china.ChinaArgs(registry='cde',query='玛伐凯泰胶囊',query_kind='drug_name',route_id='acceptance'))
    result=china._china(ctx,china.ChinaArgs(registry='cde',query='JXHS2600124',query_kind='acceptance_number',
        cde_section='priority_included',route_id='priority'))
    attrs=ctx.db.entities(ctx.project_id,'drug')[0]['attrs']
    assert result['linked_refs']==1 and result['persisted']
    assert attrs['cde_priority_refs'][0]['directory_status_text']=='已纳入'
    assert 'cde_review_refs' not in attrs and not {'china_mah','approved','target_indication'} & attrs.keys()
    assert not ctx.db.entities(ctx.project_id,'trial') and not ctx.db.current_facts(ctx.project_id)


def test_genuine_priority_rows_without_an_acceptance_number_are_preserved():
    from ciw2.sources.cde_priority import parse_capture
    page=json.loads((Path(__file__).parent/'fixtures/cde-priority-missing-id.json').read_text())
    result=parse_capture([page],allow_partial=True)
    assert len(result['results'])==50 and result['unresolved_acceptance_count']==11
    missing=[r for r in result['results'] if r['acceptance_number'] is None]
    assert all(r['acceptance_number_text']=='无' for r in missing)
    assert [r['raw_cells'] for r in result['results']]==page['rows']
    exact=parse_capture([page],allow_partial=True,query='JXHS2600124')
    assert exact['matched_count']==1 and exact['unresolved_acceptance_count']==11


def test_rejected_raw_pages_are_retained_as_unaccepted_evidence(ctx,monkeypatch):
    from ciw2.sources import cde_priority
    pages=captures();pages[-1]['rows'][0][0]='wrong ordinal'
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke(pages))
    with pytest.raises(china_browser.BrowserFailed):cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number')
    event=json.loads(ctx.db.one("SELECT content FROM agent_steps WHERE role='source_capture_rejected'")['content'])
    assert json.loads(ctx.cas.get(event['digest']))['pages']==pages and event['accepted'] is False
    assert not ctx.db.current_facts(ctx.project_id)


def test_another_product_cannot_borrow_a_real_source_application_reference(ctx,monkeypatch):
    from test_cde_browser import capture
    acceptance=capture();acceptance['filters']['drug_name']='玛伐凯泰胶囊'
    acceptance['rows'][0][1]='JXHS2600124';acceptance['rows'][0][2]='玛伐凯泰胶囊'
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke([acceptance]) if kw['script_path'].name=='cde_browser.mjs' else invoke(captures()))
    china._china(ctx,china.ChinaArgs(registry='cde',query='玛伐凯泰胶囊',query_kind='drug_name',route_id='acceptance'))
    original=ctx.db.entities(ctx.project_id,'drug')[0]
    forged,_=ctx.db.upsert_entity(ctx.project_id,'drug','另一个无关产品',attrs={
        'cde_acceptance_refs':deepcopy(original['attrs']['cde_acceptance_refs'])})
    out=china._china(ctx,china.ChinaArgs(registry='cde',query='JXHS2600124',query_kind='acceptance_number',
        cde_section='priority_included',route_id='priority'))
    assert out['linked_refs']==1
    other=next(d for d in ctx.db.entities(ctx.project_id,'drug') if d['id']==forged)
    assert 'cde_priority_refs' not in other['attrs']


@pytest.mark.parametrize('fault',['wrong_row','wrong_company','corrupt_cas','partial_source'])
def test_application_proof_requires_original_row_and_qualified_bytes(ctx,monkeypatch,fault):
    from test_cde_browser import capture

    from ciw2.sources import cde_browser, cde_review_browser
    acceptance=capture()
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke([acceptance]))
    found=cde_browser.browser_search(ctx,'原药','drug_name');cde_browser.persist_candidates(ctx,found,'acceptance')
    drug=ctx.db.entities(ctx.project_id,'drug')[0]
    assert len(cde_review_browser.proven_acceptance_refs(ctx,drug))==1
    ref=drug['attrs']['cde_acceptance_refs'][0]
    if fault=='wrong_row':ref['row_number']=999
    if fault=='wrong_company':ref['company_text']='不同企业'
    if fault=='corrupt_cas':
        source=ctx.db.one('SELECT digest FROM sources WHERE id=?',(ref['source_id'],))
        ctx.cas._path(source['digest']).write_bytes(b'corrupt owned test data')
    if fault=='partial_source':
        # A partial capture is a different source, never a successful previous proof.
        from ciw2.sources.http import register_text
        sid=register_text(ctx,kind='cde',url=acceptance['url'],title='partial',
            text=json.dumps({'section':'acceptance','filters':acceptance['filters'],'pages':[acceptance]}),
            meta={'complete':False,'request_context':{'section':'acceptance','filters':acceptance['filters']}})
        ref['source_id']=sid
    assert cde_review_browser.proven_acceptance_refs(ctx,drug)==[]
