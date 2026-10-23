import json
import subprocess
from dataclasses import replace
from types import SimpleNamespace

import pytest

from ciw2.service import Service
from ciw2.sources import china_browser


def page(query='适应症', *, number=1, pages=1, total=1):
    return {'url':'https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml','query':query,
        'headers':['序号','登记号','试验状态','药物名称','适应症','试验通俗题目'],
        'rows':[{'cells':[str(number),f'CTR{20260000+number}','进行中 招募中','原始复合药物','适应症','完整研究题目'],
                 'detail_id':f'{number:032x}'}],
        'pagination_text':f'当前第 {number} 页，共 {pages} 页，共 {total} 条记录'}


def stream(pages, status='ok'):
    return '\n'.join(['[ego-browser:notice] no source payload here',
        *('CIW_CHINA_PAGE:'+json.dumps(p,ensure_ascii=False) for p in pages),
        'CIW_CHINA_END:'+json.dumps({'status':status})])


@pytest.fixture
def ctx(settings):
    svc=Service(replace(settings,china_ego_space_id=59))
    pid=svc.create_project('适应症',['A'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def test_requires_explicit_space_and_does_not_create_or_claim_browser_context(settings,monkeypatch):
    svc=Service(settings)
    pid=svc.create_project('适应症',['A'])
    context=svc.context(pid,svc.db.create_run(pid)).tool_ctx()
    monkeypatch.setattr(china_browser.subprocess,'run',lambda *a,**k:pytest.fail('unconfigured browser must not run'))
    with pytest.raises(china_browser.BrowserBlocked):
        china_browser.browser_search(context,'适应症')


def test_valid_capture_becomes_real_source_not_http_or_empty_claim(ctx,monkeypatch):
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    calls=[]
    def run(args,**kw):
        calls.append((args,kw))
        return SimpleNamespace(returncode=0,stdout=stream([page()]),stderr='private runtime error text')
    monkeypatch.setattr(china_browser.subprocess,'run',run)
    output=china_browser.browser_search(ctx,'适应症')
    assert output['complete'] is True and len(output['results'])==1
    assert output['results'][0]['source_id']==output['source_id']
    sources=ctx.db.query('SELECT * FROM sources WHERE project_id=?',(ctx.project_id,))
    assert len(sources)==1 and sources[0]['id']==output['source_id']
    events=ctx.db.query("SELECT content FROM agent_steps WHERE role='source_observation'")
    assert any(json.loads(e['content'])['mode']=='browser_checked' for e in events)
    assert all(json.loads(e['content']).get('http_status') is None for e in events)
    assert calls[0][0][:3]==['/usr/bin/ego-browser','nodejs','-e']
    script=calls[0][0][3]
    assert 'taskSpace(config.space)' in script and 'claimTaskSpace' not in script and 'newPage' not in script
    assert calls[0][1].get('shell',False) is False
    assert 'private runtime error text' not in json.dumps(output)


def test_query_string_is_data_not_a_shell_or_script_fragment(ctx,monkeypatch):
    query='药物"; throw new Error("not code"); //'
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    def run(args,**kw):
        first=args[3].split('\n',1)[0]
        config=json.loads(first.removeprefix('const config = ').removesuffix(';'))
        assert config['query']==query and config['space']==59
        return SimpleNamespace(returncode=0,stdout=stream([page(query)]),stderr='')
    monkeypatch.setattr(china_browser.subprocess,'run',run)
    assert china_browser.browser_search(ctx,query)['complete']


@pytest.mark.parametrize('timeout',[False,True])
def test_ego_console_markers_on_stderr_are_read_without_retaining_other_diagnostics(ctx,monkeypatch,timeout):
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    payload=stream([page(pages=2,total=2)] if timeout else [page()],'failed' if timeout else 'ok')
    def run(*args,**kw):
        stderr='private-runtime-diagnostic\n'+payload
        if timeout:
            raise subprocess.TimeoutExpired('ego-browser',5,output=b'',stderr=stderr.encode())
        return SimpleNamespace(returncode=0,stdout='',stderr=stderr)
    monkeypatch.setattr(china_browser.subprocess,'run',run)
    if timeout:
        with pytest.raises(china_browser.BrowserFailed):
            china_browser.browser_search(ctx,'适应症')
    else:
        assert china_browser.browser_search(ctx,'适应症')['complete']
    source=ctx.db.one('SELECT * FROM sources')
    assert source is not None
    assert 'private-runtime-diagnostic' not in ctx.cas.get_text(source['text_digest'])


@pytest.mark.parametrize('status',['failed','user_control','blocked'])
def test_browser_error_is_not_zero_results_or_captured_secret(ctx,monkeypatch,status):
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    monkeypatch.setattr(china_browser.subprocess,'run',lambda *a,**k:SimpleNamespace(
        returncode=1,stdout=stream([],status),stderr='api_key=do-not-persist'))
    with pytest.raises((china_browser.BrowserBlocked,china_browser.BrowserFailed)) as error:
        china_browser.browser_search(ctx,'适应症')
    assert 'do-not-persist' not in str(error.value)
    assert ctx.db.query('SELECT * FROM sources')==[]


def test_timeout_preserves_valid_partial_capture_but_never_accepts_it(ctx,monkeypatch):
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    def run(*args,**kw):
        raise subprocess.TimeoutExpired('ego-browser',5,output=stream([page(pages=2,total=2)],'failed').encode())
    monkeypatch.setattr(china_browser.subprocess,'run',run)
    with pytest.raises(china_browser.BrowserFailed):
        china_browser.browser_search(ctx,'适应症')
    source=ctx.db.one('SELECT * FROM sources')
    assert source is not None
    assert json.loads(source['meta'])['complete'] is False
    assert json.loads(source['meta'])['pending_pages']==[2]


def test_malformed_capture_cannot_register_cross_query_data(ctx,monkeypatch):
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    monkeypatch.setattr(china_browser.subprocess,'run',lambda *a,**k:SimpleNamespace(
        returncode=0,stdout=stream([page('另一适应症')]),stderr=''))
    with pytest.raises(china_browser.BrowserFailed):
        china_browser.browser_search(ctx,'适应症')
    assert ctx.db.query('SELECT * FROM sources')==[]


def test_batch_conflict_keeps_validated_public_pages_for_offline_repair_not_acceptance(ctx,monkeypatch):
    captured=[page(number=1,pages=2,total=2),page(number=2,pages=2,total=2)]
    captured[1]['rows'][0]['cells'][1]=captured[0]['rows'][0]['cells'][1]
    monkeypatch.setattr(china_browser,'_invoke',lambda *a:(stream(captured),True))
    with pytest.raises(china_browser.BrowserFailed):
        china_browser.browser_search(ctx,'适应症')
    source=ctx.db.one('SELECT * FROM sources')
    assert source is not None
    assert json.loads(source['meta'])['validation_failed'] is True
    assert json.loads(source['meta'])['complete'] is False
    assert len(json.loads(ctx.cas.get_text(source['text_digest']))['pages'])==2


def test_same_run_retry_only_requests_missing_pages_and_retains_reuse_provenance(ctx,monkeypatch):
    first=page(number=1,pages=2,total=2)
    second=page(number=2,pages=2,total=2)
    calls=[]
    def invoke(context,query,resume=None):
        calls.append(resume)
        if len(calls)==1:
            return stream([first],'failed'),False
        assert [p['pagination_text'] for p in resume['pages']]==[first['pagination_text']]
        return stream([second]),True
    monkeypatch.setattr(china_browser,'_invoke',invoke)
    with pytest.raises(china_browser.BrowserFailed):
        china_browser.browser_search(ctx,'适应症')
    result=china_browser.browser_search(ctx,'适应症')
    assert result['complete'] and result['pages_read']==[1,2]
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(result['source_id'],))
    assert json.loads(source['meta'])['reused_pages']==[1]
    assert json.loads(source['meta'])['new_pages_checked']==[2]


def test_partial_from_another_run_is_not_silently_reused(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a:(stream([page(pages=2,total=2)],'failed'),False))
    with pytest.raises(china_browser.BrowserFailed):
        china_browser.browser_search(ctx,'适应症')
    ctx.run_id=ctx.db.create_run(ctx.project_id)
    def fresh(context,query,resume=None):
        assert resume is None
        return stream([page()]),True
    monkeypatch.setattr(china_browser,'_invoke',fresh)
    assert china_browser.browser_search(ctx,'适应症')['complete']


def test_registered_china_tool_prefers_configured_browser_over_site_leads(ctx,monkeypatch):
    from ciw2.sources import china

    def blocked(*args,**kw):
        raise china.RegistryBlocked('HTTP blocked fixture')
    monkeypatch.setattr(china,'direct_search',blocked)
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    monkeypatch.setattr(china_browser.subprocess,'run',lambda *a,**k:SimpleNamespace(
        returncode=0,stdout=stream([page()]),stderr=''))
    monkeypatch.setattr(china,'web_search',lambda *args:pytest.fail('browser success must not become site leads'))
    result=china._china(ctx,china.ChinaArgs(registry='chinadrugtrials',query='适应症',route_id='china:ctr:condition'))
    assert result['mode']=='browser' and result['complete'] and result['count']==1
    rows=ctx.db.query('SELECT route_id,status,hits FROM coverage ORDER BY id')
    assert rows==[{'route_id':'china:ctr:condition','status':'blocked','hits':0},
                  {'route_id':'china:ctr:condition:browser','status':'ok','hits':1}]
    drugs=ctx.db.entities(ctx.project_id,'drug')
    trials=ctx.db.entities(ctx.project_id,'trial')
    assert len(drugs)==len(trials)==1 and drugs[0]['name']=='原始复合药物'
    assert trials[0]['name']=='CTR20260001' and trials[0]['attrs']['registry_status_text']=='进行中 招募中'
    assert drugs[0]['in_scope'] is None and 'china_mah' not in drugs[0]['attrs']
    assert ctx.db.current_facts(ctx.project_id)==[]


@pytest.mark.parametrize('parameter',['token=secret','api_key=secret','password=secret'])
def test_public_capture_url_cannot_persist_query_credentials(ctx,monkeypatch,parameter):
    captured=page()
    captured['url']+='?'+parameter
    monkeypatch.setattr(china_browser.shutil,'which',lambda _: '/usr/bin/ego-browser')
    monkeypatch.setattr(china_browser.subprocess,'run',lambda *a,**k:SimpleNamespace(
        returncode=0,stdout=stream([captured]),stderr=''))
    with pytest.raises(china_browser.BrowserFailed):
        china_browser.browser_search(ctx,'适应症')
    assert ctx.db.query('SELECT * FROM sources')==[]
