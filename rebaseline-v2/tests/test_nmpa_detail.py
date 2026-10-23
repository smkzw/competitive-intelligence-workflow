"""Exact public NMPA certificate retrieval: source only, verified cache, offline."""
import base64
import json
from copy import deepcopy
from dataclasses import replace

import pytest
from pydantic import ValidationError

from ciw2.harness.cancellation import RunCancelled
from ciw2.service import Service
from ciw2.sources import china_browser, nmpa_detail

FOREIGN='境外生产药品'
DOMESTIC='境内生产药品'
NUMBER='国药准字SJ20240001'
DOMESTIC_NUMBER='国药准字S20240040'
URL='https://datasearch.nmpa.gov.cn/datasearch/search-info.html?nmpa='+base64.b64encode(
    b'id='+b'a'*32+b'&itemId='+b'b'*32).decode()
DOMESTIC_URL='https://datasearch.nmpa.gov.cn/datasearch/search-info.html?nmpa='+base64.b64encode(
    b'id='+b'c'*32+b'&itemId='+b'd'*32).decode()


def foreign():
    return {'url':URL,'category':FOREIGN,'registration_number':NUMBER,
        'heading':FOREIGN+' ——“'+NUMBER+'”基本信息','observed_at':'2026-10-24T00:00:00Z',
        'rows':[['注册证号',NUMBER],['上市许可持有人中文名称','————'],
            ['上市许可持有人英文名称','Holder Legal Entity'],['产品名称（中文）','药物甲注射液'],
            ['产品名称（英文）','Drug A Injection'],['生产厂商（英文）','Factory Company'],
            ['规格（中文）','300mg（2.0mL）/支'],['发证日期','2025-02-18'],
            ['有效期截止日','2030-01-23'],['境内责任人名称','境内责任人甲公司'],['注','详情']]}


def domestic():
    return {'url':DOMESTIC_URL,'category':DOMESTIC,'registration_number':DOMESTIC_NUMBER,
        'heading':DOMESTIC+' ——“'+DOMESTIC_NUMBER+'”基本信息','observed_at':'2026-10-24T00:00:00Z',
        'rows':[['批准文号',DOMESTIC_NUMBER],['产品名称','司普奇拜单抗注射液'],
            ['英文名称','Stapokibart Injection'],['规格','300mg（2ml）/瓶'],
            ['上市许可持有人','持有人甲法律实体'],['生产单位','  生产企业乙'],
            ['批准日期','2024-09-10'],['注','详情']]}


def stream(pages,status='ok'):
    return '\n'.join(['[ego-browser:notice] no source payload here',
        *('CIW_CHINA_PAGE:'+json.dumps(page,ensure_ascii=False) for page in pages),
        'CIW_CHINA_END:'+json.dumps({'status':status})])


def install(monkeypatch,raw,status='ok',calls=None):
    def invoke(context,query,**kw):
        if calls is not None:
            calls.append((query,kw))
        return stream([raw] if raw is not None else [],status),status=='ok'
    monkeypatch.setattr(china_browser,'_invoke',invoke)


@pytest.fixture
def ctx(settings):
    svc=Service(replace(settings,china_ego_space_id=71))
    pid=svc.create_project('适应症',['A'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def test_foreign_certificate_registers_exact_raw_and_literal_text_without_writes(ctx,monkeypatch):
    raw=foreign(); calls=[]; install(monkeypatch,raw,calls=calls)
    out=nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert calls==[(NUMBER,{'script_path':nmpa_detail.SCRIPT,'options':{'url':URL,'category':FOREIGN}})]
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(out['source_id'],))
    assert json.loads(ctx.cas.get(source['digest']))==raw
    assert ctx.cas.get_text(source['text_digest'])==out['source_text']
    assert out['source_text'].splitlines()[:3]==[raw['heading'],
        '注册证号\t'+NUMBER,'上市许可持有人中文名称\t————']
    assert out['observation_mode']=='browser_checked' and out['published_date'] is None
    assert source['published_date'] is None
    assert out['source_id'] in ctx.extra['source_ids_read']
    assert ctx.db.current_facts(ctx.project_id)==[] and ctx.db.entities(ctx.project_id,'drug')==[]


def test_foreign_roles_are_literal_and_do_not_merge_holder_factory_or_agent(ctx,monkeypatch):
    install(monkeypatch,foreign())
    out=nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert out['holder_name']=='Holder Legal Entity' and out['holder_name_zh'] is None
    assert out['manufacturer_name']=='Factory Company'
    assert out['domestic_responsible_person']=='境内责任人甲公司'
    assert out['drug_name']=='药物甲注射液' and out['strength']=='300mg（2.0mL）/支'
    assert out['issue_date']=='2025-02-18' and out['valid_until']=='2030-01-23'
    assert out['approval_date'] is None
    assert not {'indication','approved','group','first_public_date'} & out.keys()


def test_domestic_certificate_keeps_approval_date_and_explicit_manufacturer(ctx,monkeypatch):
    install(monkeypatch,domestic())
    out=nmpa_detail.browser_detail(ctx,DOMESTIC_URL,DOMESTIC_NUMBER,DOMESTIC)
    assert out['approval_date']=='2024-09-10'
    assert out['issue_date'] is None and out['valid_until'] is None
    assert out['holder_name']=='持有人甲法律实体' and out['manufacturer_name']=='生产企业乙'
    assert out['domestic_responsible_person'] is None and out['published_date'] is None
    assert out['field_locators']['holder_name_zh']=='$.rows[4][1]'


@pytest.mark.parametrize('change',['heading','number','category','url','extra','observed','row_shape','duplicate'])
def test_unbound_or_malformed_capture_is_never_an_empty_certificate(ctx,monkeypatch,change):
    raw=foreign()
    if change=='heading':raw['heading']=raw['heading'].replace('SJ20240001','SJ20240002')
    elif change=='number':raw['rows'][0][1]='国药准字SJ20240002'
    elif change=='category':raw['category']=DOMESTIC
    elif change=='url':raw['url']=URL.replace('datasearch.nmpa.gov.cn','example.org')
    elif change=='extra':raw['note']='page instructed this'
    elif change=='observed':raw['observed_at']='2026-10-24T00:00:00'
    elif change=='row_shape':raw['rows'].append(['坏行'])
    else:raw['rows'].append(['注册证号',NUMBER])
    install(monkeypatch,raw)
    before=ctx.db.query('SELECT * FROM sources')
    with pytest.raises(ValueError):
        nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert ctx.db.query('SELECT * FROM sources')==before and ctx.db.current_facts(ctx.project_id)==[]


@pytest.mark.parametrize('bad',['space','run','cross_project','url','number','category'])
def test_unbound_request_does_not_launch_browser(ctx,monkeypatch,bad):
    url,number,category=URL,NUMBER,FOREIGN
    if bad=='space':ctx.settings=replace(ctx.settings,china_ego_space_id=None)
    elif bad=='run':ctx.run_id=None
    elif bad=='cross_project':ctx.project_id=ctx.db.create_project('别的项目',['A'])
    elif bad=='url':url=URL.replace('https://','http://')
    elif bad=='number':number='SJ20240001'
    else:category='生物制品'
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:pytest.fail('unbound request must not browse'))
    with pytest.raises((ValueError,RuntimeError)):
        nmpa_detail.browser_detail(ctx,url,number,category)
    assert ctx.db.query('SELECT * FROM sources')==[] and ctx.db.current_facts(ctx.project_id)==[]


def test_same_run_replay_verifies_cache_and_new_run_checks_the_source_again(ctx,monkeypatch):
    calls=[]; install(monkeypatch,foreign(),calls=calls)
    first=nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    second=nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert second['observation_mode']=='cache_reused' and second['source_id']==first['source_id']
    assert len(calls)==1
    modes=[json.loads(row['content'])['mode'] for row in ctx.db.query(
        "SELECT content FROM agent_steps WHERE role='source_observation' ORDER BY id")]
    assert modes.count('browser_checked')==1 and modes.count('cache_reused')==1
    cache_key=next(iter(ctx.extra['fetch_cache']))
    assert first['source_id']==ctx.extra['fetch_cache'][cache_key]
    ctx.run_id=ctx.db.create_run(ctx.project_id)
    third=nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert len(calls)==2 and third['observation_mode']=='browser_checked'
    assert third['source_id']==first['source_id']


def test_cache_reuse_requires_same_run_url_category_number_and_space(ctx,monkeypatch):
    calls=[]
    raws={NUMBER:foreign(),DOMESTIC_NUMBER:domestic()}
    def invoke(context,query,**kw):
        calls.append(query)
        return stream([raws[query]]),True
    monkeypatch.setattr(china_browser,'_invoke',invoke)
    nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    nmpa_detail.browser_detail(ctx,DOMESTIC_URL,DOMESTIC_NUMBER,DOMESTIC)
    assert len(calls)==2
    nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert len(calls)==2
    ctx.settings=replace(ctx.settings,china_ego_space_id=72)
    nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert len(calls)==3


@pytest.mark.parametrize('tamper',['text','digest','scope','version'])
def test_tampered_or_stale_cache_evidence_fails_closed_without_new_browser_claim(ctx,monkeypatch,tamper):
    calls=[]; install(monkeypatch,foreign(),calls=calls)
    first=nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    if tamper=='text':
        other=ctx.cas.put('有效哈希但非该证书原文'.encode())
        ctx.db.execute('UPDATE sources SET text_digest=? WHERE id=?',(other,first['source_id']))
    elif tamper=='digest':
        ctx.db.execute('UPDATE sources SET digest=? WHERE id=?',('0'*64,first['source_id']))
    elif tamper=='scope':
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.registration_number',?) WHERE id=?",
            ('国药准字SJ20249999',first['source_id']))
    else:
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.extractor_version','old') WHERE id=?",
            (first['source_id'],))
    before=ctx.db.query('SELECT * FROM sources')
    with pytest.raises(ValueError):
        nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert len(calls)==1 and ctx.db.query('SELECT * FROM sources')==before


@pytest.mark.parametrize(('status','error'),[
    pytest.param('ok',china_browser.BrowserFailed,id='no-page'),
    pytest.param('failed',china_browser.BrowserFailed,id='failed'),
    pytest.param('blocked',china_browser.BrowserBlocked,id='blocked'),
    pytest.param('user_control',china_browser.BrowserBlocked,id='user-control')])
def test_incomplete_control_or_handed_off_capture_is_not_success(ctx,monkeypatch,status,error):
    install(monkeypatch,None,status)
    before=ctx.db.query('SELECT * FROM sources')
    with pytest.raises(error) as raised:
        nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert 'no source payload' not in str(raised.value) and 'nmpa=' not in str(raised.value)
    assert ctx.db.query('SELECT * FROM sources')==before and ctx.db.current_facts(ctx.project_id)==[]


def test_duplicate_pages_are_not_merged_into_one_certificate(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',
        lambda *a,**k:(stream([foreign(),foreign()]),True))
    with pytest.raises(china_browser.BrowserFailed):
        nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert ctx.db.query('SELECT * FROM sources')==[] and ctx.db.current_facts(ctx.project_id)==[]


def test_user_cancel_is_not_rewritten_as_a_tool_failure(ctx,monkeypatch):
    def cancel(*args,**kwargs):
        raise RunCancelled('用户请求停止')
    monkeypatch.setattr(china_browser,'_invoke',cancel)
    with pytest.raises(RunCancelled):
        nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert ctx.db.query('SELECT * FROM sources')==[] and ctx.db.current_facts(ctx.project_id)==[]


def test_failed_capture_keeps_previous_certificate_evidence(ctx,monkeypatch):
    install(monkeypatch,foreign())
    first=nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    before=ctx.db.query('SELECT * FROM sources')
    ctx.extra['fetch_cache'].clear()
    bad=deepcopy(foreign()); bad['heading']=bad['heading'].replace(NUMBER,'国药准字SJ20240002')
    install(monkeypatch,bad)
    with pytest.raises(ValueError):
        nmpa_detail.browser_detail(ctx,URL,NUMBER,FOREIGN)
    assert ctx.db.query('SELECT * FROM sources')==before
    assert ctx.db.one('SELECT id FROM sources WHERE id=?',(first['source_id'],)) is not None


def test_tool_payload_has_exact_locators_and_no_adopted_fact_or_entity(ctx,monkeypatch):
    install(monkeypatch,foreign())
    out=nmpa_detail._detail(ctx,nmpa_detail.DetailArgs(url=URL,registration_number=NUMBER,category=FOREIGN))
    assert out['field_locators']['registration_number']=='$.rows[0][1]'
    assert out['field_locators']['drug_name']=='$.rows[3][1]'
    assert out['source_text'].splitlines()[0]==foreign()['heading']
    assert not {'indication','approved','group','first_public_date'} & out.keys()
    assert ctx.db.current_facts(ctx.project_id)==[] and ctx.db.entities(ctx.project_id,'drug')==[]
    assert ctx.db.entities(ctx.project_id,'trial')==[]


@pytest.mark.parametrize('number',['SJ20240001','国药准字sj20240001','国药准字SJ2024001'])
def test_tool_arguments_reject_unofficial_number_shapes(number):
    with pytest.raises(ValidationError):
        nmpa_detail.DetailArgs(url=URL,registration_number=number,category=FOREIGN)


def test_tool_registration_is_typed_and_documented_for_model_use():
    tool=nmpa_detail.REGISTRY.get('nmpa_product_detail')
    assert set(tool.args_model.model_fields)=={'url','registration_number','category'}
    assert tool.args_model.model_fields['category'].annotation==nmpa_detail.CATEGORY_TYPE
