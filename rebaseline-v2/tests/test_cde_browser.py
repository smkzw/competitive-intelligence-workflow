import json
from dataclasses import replace

import pytest

from ciw2.service import Service
from ciw2.sources import cde_browser, china, china_browser

FILTERS={'year':'','drug_name':'原药','applicant':'','acceptance_number':'','drug_type':'','application_type':''}


def capture(*,filters=None,rows=None,total=1):
    return {'url':'https://www.cde.org.cn/main/xxgk/listpage/'+'a'*32,'section':'acceptance',
        'filters':dict(filters or FILTERS),
        'headers':['序号','受理号','药品名称','药品类型','申请类型','注册分类','企业名称','承办日期'],
        'rows':rows if rows is not None else [['1','CXSL2600001','原药联合片','生物制品','补充申请','','企业一;企业二;','2026-01-01']],
        'pagination':{'current':1,'page_size':50,'total_records':total,'text':f'共 {total} 条'}}


def stream(pages,status='ok'):
    return '\n'.join([*('CIW_CHINA_PAGE:'+json.dumps(p,ensure_ascii=False) for p in pages),
                      'CIW_CHINA_END:'+json.dumps({'status':status})])


@pytest.fixture
def ctx(settings):
    service=Service(replace(settings,china_ego_space_id=59))
    pid=service.create_project('适应症',['A'])
    return service.context(pid,service.db.create_run(pid)).tool_ctx()


@pytest.mark.parametrize('kind',['keyword','indication','target'])
def test_untyped_disease_or_target_is_not_queried_as_a_drug_name(ctx,monkeypatch,kind):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:pytest.fail('no such native CDE query field'))
    with pytest.raises(china_browser.BrowserBlocked):
        cde_browser.browser_search(ctx,'原药',kind)


@pytest.mark.parametrize('kind,field',[('drug_name','drug_name'),('company','applicant'),('acceptance_number','acceptance_number')])
def test_source_preserves_enterprise_text_without_assigning_a_legal_role(ctx,monkeypatch,kind,field):
    filters={**dict.fromkeys(FILTERS,''),field:'原药'}
    def invoke(*a,**kw):
        assert kw['options']['filters']==filters
        assert kw['script_path']==cde_browser.SCRIPT
        return stream([capture(filters=filters)]),True
    monkeypatch.setattr(china_browser,'_invoke',invoke)
    result=cde_browser.browser_search(ctx,'原药',kind)
    assert result['complete'] and result['results'][0]['company_text']=='企业一;企业二;'
    assert 'applicant_text' not in result['results'][0]
    assert result['results'][0]['handled_date_text']=='2026-01-01'
    assert 'acceptance_date_text' not in result['results'][0]
    assert not any(k in result['results'][0] for k in ('mah','china_mah','target_indication','phase','review_status'))
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(result['source_id'],))
    metadata=json.loads(source['meta'])
    assert metadata['request_context']['filters']==filters
    assert metadata['request_context']['section']=='acceptance'
    assert metadata['request_context']['registry']=='cde'


def test_default_year_or_filter_drift_is_not_accepted_as_all_years(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:(stream([capture(filters={**FILTERS,'year':'2026'})]),True))
    with pytest.raises(china_browser.BrowserFailed):
        cde_browser.browser_search(ctx,'原药','drug_name')
    assert ctx.db.query('SELECT * FROM sources')==[]


def test_cde_explicit_empty_ui_without_pagination_is_not_a_fabricated_zero_footer(ctx,monkeypatch):
    page=capture(rows=[],total=0)
    page['pagination']={'current':0,'page_size':None,'total_records':0,'text':'暂无内容'}
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:(stream([page]),True))
    result=cde_browser.browser_search(ctx,'原药','drug_name')
    assert result['complete'] and result['total_records']==0 and result['results']==[]
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(result['source_id'],))
    assert '暂无内容' in ctx.cas.get_text(source['text_digest'])
    assert '共 0 条' not in ctx.cas.get_text(source['text_digest'])


def test_failed_query_reports_safe_phase_without_claiming_zero(ctx,monkeypatch):
    marker={'status':'failed','phase':'query','error_type':'ElementResolutionError'}
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:(
        'CIW_CHINA_END:'+json.dumps(marker),True))
    with pytest.raises(china_browser.BrowserFailed,match='query.*ElementResolutionError'):
        cde_browser.browser_search(ctx,'原药','drug_name')
    assert ctx.db.query('SELECT * FROM sources')==[]


def test_generic_production_tool_adopts_only_provisional_drug_labels(ctx,monkeypatch):
    def blocked(*a,**k):
        raise china.RegistryBlocked('public direct interface unavailable')
    monkeypatch.setattr(china,'direct_search',blocked)
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:(stream([capture()]),True))
    monkeypatch.setattr(china,'web_search',lambda *a:pytest.fail('valid browser source must not become site leads'))
    result=china._china(ctx,china.ChinaArgs(registry='cde',query='原药',query_kind='drug_name',route_id='cde:drug'))
    assert result['mode']=='browser' and result['persisted'] and result['count']==1
    drugs=ctx.db.entities(ctx.project_id,'drug')
    assert len(drugs)==1 and drugs[0]['name']=='原药联合片' and drugs[0]['in_scope'] is None
    assert drugs[0]['attrs']['cde_acceptance_refs'][0]['company_text']=='企业一;企业二;'
    assert 'china_mah' not in drugs[0]['attrs']
    assert ctx.db.entities(ctx.project_id,'trial')==[] and ctx.db.current_facts(ctx.project_id)==[]
