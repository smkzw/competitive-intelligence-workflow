"""Production CDE adapters recover only unchanged run-bound page collections."""
import json
from copy import deepcopy
from dataclasses import replace

import pytest
from test_cde_browser import capture
from test_cde_review_capture import page, row

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import cde_browser, cde_review_browser, china_browser


@pytest.fixture
def ctx(settings):
    svc=Service(replace(settings,china_ego_space_id=63),llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('恢复来源',['A'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def source_pages(section):
    if section=='new_review_task':
        return [page([row(1),row(2)],1,5),page([row(3),row(4)],2,5),page([row(5)],3,5)]
    output=[]
    for number,ordinals in enumerate(((1,2),(3,4),(5,)),1):
        p=capture(total=5,rows=[[str(i),f'CXSL260000{i}','原药','化药','新药','','企业','2026-01-01'] for i in ordinals])
        p['pagination'].update(current=number,page_size=2)
        output.append(p)
    return output


def stream(pages,status='ok',**end):
    return '\n'.join([*('CIW_CHINA_PAGE:'+json.dumps(p,ensure_ascii=False) for p in pages),
        'CIW_CHINA_END:'+json.dumps({'status':status,**end})]),status=='ok'


def search(ctx,section):
    if section=='new_review_task':
        return cde_review_browser.browser_search(ctx,'CYHL2600085','acceptance_number')
    return cde_browser.browser_search(ctx,'原药','drug_name')


@pytest.mark.parametrize('section',['acceptance','new_review_task'])
def test_partial_recovery_rechecks_first_page_skips_old_page_two_and_keeps_lineage(ctx,monkeypatch,section):
    pages=source_pages(section)
    calls=[]
    def captured(*args,**kw):
        calls.append(kw.get('options',{}))
        if len(calls)==1:
            return stream(pages[:2],'failed')
        resume=kw['options']['resume']
        assert resume['pages_read']==[1,2] and resume['total_records']==5 and resume['page_size']==2
        assert len(resume['first_page_sha256'])==64
        return stream([pages[0],pages[2]],resume_used=True,reused_pages=[2],new_pages_checked=[1,3])
    monkeypatch.setattr(china_browser,'_invoke',captured)
    with pytest.raises(china_browser.BrowserFailed):search(ctx,section)
    first=ctx.db.one('SELECT * FROM sources ORDER BY rowid LIMIT 1')
    raw=ctx.cas.get(first['digest'])
    result=search(ctx,section)
    assert result['complete'] and result['total_records']==5 and len(result['results'])==5
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(result['source_id'],))
    meta=json.loads(source['meta'])
    assert meta['reused_source_ids']==[first['id']] and meta['reused_pages']==[2]
    assert meta['new_pages_checked']==[1,3]
    assert ctx.cas.get(first['digest'])==raw
    assert ctx.db.current_facts(ctx.project_id)==[]


@pytest.mark.parametrize('section',['acceptance','new_review_task'])
def test_changed_first_page_forces_complete_new_capture_not_old_page_union(ctx,monkeypatch,section):
    old=source_pages(section)
    fresh=deepcopy(old)
    if section=='acceptance':fresh[0]['rows'][0][2]='修订原药'
    else:fresh[0]['rows'][0][2]['text']='修订原药'
    calls=[]
    def captured(*args,**kw):
        calls.append(kw)
        return stream(old[:2],'failed') if len(calls)==1 else stream(
            fresh,resume_used=False,reused_pages=[],new_pages_checked=[1,2,3])
    monkeypatch.setattr(china_browser,'_invoke',captured)
    with pytest.raises(china_browser.BrowserFailed):search(ctx,section)
    result=search(ctx,section)
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(result['source_id'],))
    meta=json.loads(source['meta'])
    assert meta['reused_pages']==[] and meta['reused_source_ids']==[]
    assert meta['new_pages_checked']==[1,2,3] and result['results'][0]['drug_name']=='修订原药'


@pytest.mark.parametrize('section',['acceptance','new_review_task'])
def test_claimed_reuse_with_changed_anchor_fails_in_host_even_if_browser_says_ok(ctx,monkeypatch,section):
    pages=source_pages(section)
    calls=[]
    def captured(*args,**kw):
        calls.append(kw)
        if len(calls)==1:return stream(pages[:2],'failed')
        fresh=deepcopy(pages[0])
        if section=='acceptance':fresh['rows'][0][2]='变更药'
        else:fresh['rows'][0][2]['text']='变更药'
        return stream([fresh,pages[2]],resume_used=True,reused_pages=[2],new_pages_checked=[1,3])
    monkeypatch.setattr(china_browser,'_invoke',captured)
    with pytest.raises(china_browser.BrowserFailed):search(ctx,section)
    with pytest.raises(china_browser.BrowserFailed):search(ctx,section)
    assert ctx.db.current_facts(ctx.project_id)==[]
