import json
from dataclasses import replace

import pytest
from test_cde_browser import capture as acceptance_capture
from test_cde_review_capture import pages

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import cde_review_browser, china, china_browser


@pytest.fixture
def ctx(settings):
    svc=Service(replace(settings,china_ego_space_id=63),llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('来源适配测试',['A'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def invoke(pages,status='ok'):
    return '\n'.join([*('CIW_CHINA_PAGE:'+json.dumps(p,ensure_ascii=False) for p in pages),
        'CIW_CHINA_END:'+json.dumps({'status':status})]),status=='ok'


def test_shared_full_scope_is_reused_as_cache_not_fresh_browser_check(ctx,monkeypatch):
    calls=[]
    def capture(*a,**kw):
        calls.append(kw['script_path'])
        return invoke(pages())
    monkeypatch.setattr(china_browser,'_invoke',capture)
    first=cde_review_browser.browser_search(ctx,'CYHL2600085','acceptance_number')
    ctx.extra['source_ids_read']=set()
    second=cde_review_browser.browser_search(ctx,'CXHL2600990','acceptance_number')
    assert first['matched_count']==second['matched_count']==1 and len(calls)==1
    assert first['source_id']==second['source_id']
    assert first['source_id'] in ctx.extra['source_ids_read']
    assert second['results'][0]['acceptance_number']=='CXHL2600990'
    modes=[json.loads(row['content'])['mode'] for row in ctx.db.query("SELECT content FROM agent_steps WHERE role='source_observation'")]
    assert modes==['imported','browser_checked','cache_reused']


def test_partial_found_target_is_retained_but_not_success_or_cached(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke(pages()[:1],status='failed'))
    with pytest.raises(china_browser.BrowserFailed):
        cde_review_browser.browser_search(ctx,'CYHL2600085','acceptance_number')
    source=ctx.db.one('SELECT * FROM sources')
    assert json.loads(source['meta'])['complete'] is False
    assert ctx.db.current_facts(ctx.project_id)==[]


def test_only_explicit_acceptance_lookup_is_supported(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:pytest.fail('unsupported query must not access browser'))
    with pytest.raises(china_browser.BrowserBlocked):
        cde_review_browser.browser_search(ctx,'皮炎','indication')


def test_new_run_requires_fresh_scope_and_corrupt_cache_never_supplies_values(ctx,monkeypatch):
    calls=[]
    def captured(*a,**kw):
        calls.append(True)
        return invoke(pages())
    monkeypatch.setattr(china_browser,'_invoke',captured)
    first=cde_review_browser.browser_search(ctx,'CYHL2600085','acceptance_number')
    fresh=replace(ctx,run_id=ctx.db.create_run(ctx.project_id))
    cde_review_browser.browser_search(fresh,'CYHL2600085','acceptance_number')
    assert len(calls)==2
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(first['source_id'],))
    ctx.cas._path(source['digest']).write_bytes(b'corrupt owned test CAS')
    with pytest.raises(china_browser.BrowserFailed,match='字节'):
        cde_review_browser.browser_search(ctx,'CYHL2600085','acceptance_number')


def test_public_tool_links_only_existing_application_binding_not_whole_page(ctx,monkeypatch):
    def blocked(*a,**kw):
        raise china.RegistryBlocked('no direct public interface')
    monkeypatch.setattr(china,'direct_search',blocked)
    acceptance=acceptance_capture()
    acceptance['rows'][0][1]='CYHL2600085'
    def captured(*a,**kw):
        return invoke([acceptance]) if kw['script_path'].name=='cde_browser.mjs' else invoke(pages())
    monkeypatch.setattr(china_browser,'_invoke',captured)
    china._china(ctx,china.ChinaArgs(registry='cde',query='原药',query_kind='drug_name',route_id='cde:acceptance:drug'))
    drug=ctx.db.entities(ctx.project_id,'drug')[0]['id']
    out=china._china(ctx,china.ChinaArgs(registry='cde',query='CYHL2600085',query_kind='acceptance_number',
        cde_section='new_review_task_chemical_ind',route_id='cde:review:application'))
    assert out['mode']=='browser' and out['count']==1
    assert len(ctx.db.entities(ctx.project_id,'drug'))==1
    attrs=ctx.db.entities(ctx.project_id,'drug')[0]['attrs']
    assert attrs['cde_review_refs'][0]['acceptance_number']=='CYHL2600085'
    assert not {'china_mah','approved','target_indication'} & attrs.keys()
    assert ctx.db.entities(ctx.project_id,'trial')==[] and ctx.db.current_facts(ctx.project_id)==[]
    assert ctx.db.entities(ctx.project_id,'drug')[0]['id']==drug


def test_unproven_application_attr_does_not_create_review_binding(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke(pages()))
    drug,_=ctx.db.upsert_entity(ctx.project_id,'drug','未经来源绑定的药',attrs={
        'cde_acceptance_refs':[{'acceptance_number':'CYHL2600085','source_id':'not-a-source'}]})
    result=cde_review_browser.browser_search(ctx,'CYHL2600085','acceptance_number')
    assert cde_review_browser.persist_refs(ctx,result,'cde:review')==0
    assert 'cde_review_refs' not in ctx.db.entities(ctx.project_id,'drug')[0]['attrs']
    assert ctx.db.entities(ctx.project_id,'drug')[0]['id']==drug


def test_source_cli_separates_whole_scope_count_and_exact_match(tmp_path,monkeypatch):
    import runpy
    import sys
    from pathlib import Path
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke(pages()))
    output=tmp_path/'smoke'
    script=Path(__file__).parents[1]/'scripts/smoke_china_browser.py'
    monkeypatch.setattr(sys,'argv',[str(script),'--space','63','--registry','cde','--query','CYHL2600085',
        '--query-kind','acceptance_number','--cde-section','new_review_task_chemical_ind','--output',str(output)])
    assert runpy.run_path(str(script))['main']()==0
    receipt=json.loads((output/'receipt.json').read_text())
    assert receipt['rows']==1 and receipt['source_total_records']==3
    assert receipt['code_unchanged_during_run'] and receipt['model_calls']==0
