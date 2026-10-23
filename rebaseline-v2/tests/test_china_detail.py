"""Actual source-reader contracts, synthetic small public UI captures only."""
import json
from copy import deepcopy
from dataclasses import replace

import pytest
from test_china_browser import page as list_page
from test_china_browser import stream

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import china, china_browser, china_detail
from ciw2.sources.http import register_text

CTR='CTR20260001'
DETAIL='1'*32
URL='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml'


def capture():
    return {'url':URL,'title':CTR+'详细信息','section':'trial_detail','registry_id':CTR,'detail_id':DETAIL,
        'observed_at':'2026-10-24T00:00:00Z',
        'basic':[['登记号',CTR],['试验状态','进行中'],['首次公示信息日期','2026-01-01'],['申请人名称','原申请人公司']],
        'tables':[{'rows':[['登记号',CTR],['药物名称','原药（联合方案）'],['适应症','登记适应症'],['试验专业题目','健康人研究']], 'nested':[]},
            {'rows':[['试验分类','药代动力学','试验分期','I期','设计类型','平行分组']], 'nested':[]},
            {'rows':[['入选标准','1\t评分≥12且≤24；并且筛选期与基线均满足。'],['排除标准','1\tALT > 3×ULN；或既往感染。']],
             'nested':[{'row':0,'column':1,'rows':[['1','评分≥12且≤24；并且筛选期与基线均满足。']]},
                       {'row':1,'column':1,'rows':[['1','ALT > 3×ULN；或既往感染。']]}]},
            {'rows':[['目标入组人数','国内: 登记人暂未填写该信息；'],['实际入组总人数','国内: 0；']], 'nested':[]}]}


@pytest.fixture
def ctx(settings):
    svc=Service(replace(settings,china_ego_space_id=63),llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('登记适应症',['C'])
    context=svc.context(pid,svc.db.create_run(pid)).tool_ctx()
    p=list_page('登记适应症')
    p['rows'][0]={'cells':['1',CTR,'进行中','原药（联合方案）','登记适应症','健康人研究'],'detail_id':DETAIL}
    raw=json.dumps({'query':'登记适应症','pages':[p]},ensure_ascii=False)
    sid=register_text(context,kind='chinadrugtrials',url=p['url'],text=raw,meta={'complete':True})
    parsed=china_browser.parse_capture([p],query='登记适应症')
    china._persist_browser_candidates(context,{**parsed,'source_id':sid},'china:list')
    return context


def test_parse_keeps_full_clauses_nested_rows_and_literal_roles():
    raw=capture()
    out=china_detail.parse_capture(raw,ctr=CTR,detail_id=DETAIL)
    assert out['applicant']=='原申请人公司' and out['registered_drug_name']=='原药（联合方案）'
    assert out['tables']==raw['tables'] and '评分≥12且≤24' in out['source_text']
    assert '登记人暂未填写' in out['source_text'] and '国内: 0' in out['source_text']
    assert not {'mah','sponsor','approved','enrollment','phase'} & out.keys()


@pytest.mark.parametrize('change',['ctr','detail_id','url','credentials','title','basic_ctr','missing_block','duplicate','nested_mismatch','bad_cells'])
def test_changed_or_malformed_capture_is_not_a_valid_trial(change):
    raw=capture()
    if change=='ctr':raw['registry_id']='CTR99999999'
    elif change=='detail_id':raw['detail_id']='2'*32
    elif change=='url':raw['url']='https://unrelated.example/clinicaltrials.searchlistdetail.dhtml'
    elif change=='credentials':raw['url']=URL+'?session_token=private'
    elif change=='title':raw['title']='CTR99999999详细信息'
    elif change=='basic_ctr':raw['basic'][0][1]='CTR99999999'
    elif change=='missing_block':raw['tables']=[]
    elif change=='duplicate':raw['basic'].append(['申请人名称','另一公司'])
    elif change=='nested_mismatch':raw['tables'][2]['nested'][0]['rows'][0][1]='替换成未出现的阈值'
    else:raw['tables'][0]['rows'][0][1]=None
    with pytest.raises(ValueError):china_detail.parse_capture(raw,ctr=CTR,detail_id=DETAIL)


def test_browser_reader_uses_bound_list_id_and_registers_exact_bytes_no_facts(ctx,monkeypatch):
    raw=capture()
    calls=[]
    def invoke(context,query,**kw):
        calls.append((query,kw))
        return stream([raw]),True
    monkeypatch.setattr(china_browser,'_invoke',invoke)
    out=china_detail.browser_detail(ctx,CTR)
    assert calls[0][0]==CTR and calls[0][1]['options']['detail_id']==DETAIL
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(out['source_id'],))
    assert json.loads(ctx.cas.get(source['digest']))==raw
    assert ctx.cas.get_text(source['text_digest'])==out['source_text']
    assert json.loads(source['meta'])['request_context']['registry_id']==CTR
    assert out['source_id'] in ctx.extra['source_ids_read'] and ctx.db.current_facts(ctx.project_id)==[]
    assert len(ctx.db.entities(ctx.project_id,'trial'))==1
    assert source['published_date'] is None  # First public record date does not date every later fact version.


@pytest.mark.parametrize('change',['unconfigured','unknown','cross_project','corrupt_source','list_mismatch'])
def test_unbound_request_does_not_open_browser(ctx,monkeypatch,change):
    if change=='unconfigured':ctx.settings=replace(ctx.settings,china_ego_space_id=None)
    elif change=='unknown':
        with pytest.raises(ValueError):china_detail.browser_detail(ctx,'CTR99999999')
        return
    elif change=='cross_project':ctx.project_id=ctx.db.create_project('别的项目',['C'])
    elif change=='corrupt_source':
        sid=ctx.db.entities(ctx.project_id,'trial')[0]['attrs']['registry_source_id']
        ctx.db.execute('UPDATE sources SET digest=? WHERE id=?',('0'*64,sid))
    else:
        ctx.db.upsert_entity(ctx.project_id,'trial',CTR,attrs={'registry_detail_id':'2'*32})
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:pytest.fail('unbound request must not browse'))
    with pytest.raises((ValueError,RuntimeError)):china_detail.browser_detail(ctx,CTR)


def test_failed_browser_preserves_old_sources_and_facts(ctx,monkeypatch):
    before=ctx.db.query('SELECT * FROM sources')
    bad=deepcopy(capture())
    bad['registry_id']='CTR99999999'
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:(stream([bad]),True))
    with pytest.raises(ValueError):china_detail.browser_detail(ctx,CTR)
    assert ctx.db.query('SELECT * FROM sources')==before and ctx.db.current_facts(ctx.project_id)==[]


def test_same_run_reuse_is_logged_but_new_run_rechecks_browser(ctx,monkeypatch):
    calls=[]
    def invoke(*a,**kw):
        calls.append(kw)
        return stream([capture()]),True
    monkeypatch.setattr(china_browser,'_invoke',invoke)
    first=china_detail.browser_detail(ctx,CTR)
    assert china_detail.browser_detail(ctx,CTR)['observation_mode']=='cache_reused'
    assert len(calls)==1
    ctx.run_id=ctx.db.create_run(ctx.project_id)
    new=china_detail.browser_detail(ctx,CTR)
    assert len(calls)==2 and new['observation_mode']=='browser_checked'
    assert new['source_id']==first['source_id']  # Same content, separate actual check receipt.


def test_tampered_cached_text_cannot_be_used_for_later_fact_verification(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:(stream([capture()]),True))
    first=china_detail.browser_detail(ctx,CTR)
    other=ctx.cas.put(b'valid hash but wrong source text')
    ctx.db.execute('UPDATE sources SET text_digest=? WHERE id=?',(other,first['source_id']))
    with pytest.raises(ValueError,match='原文'):china_detail.browser_detail(ctx,CTR)


def test_model_payload_leads_with_exact_source_and_full_plaintext_not_duplicate_json_tables(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:(stream([capture()]),True))
    result=china_detail._detail(ctx,china_detail.DetailArgs(ctr=CTR))
    assert list(result)[:3]==['source_id','source_url','registry_id']
    assert 'tables' not in result and 'detail_id' not in result
    assert result['source_text']==china_detail.parse_capture(capture(),ctr=CTR,detail_id=DETAIL)['source_text']
    assert '评分≥12且≤24' in result['source_text'] and 'ALT > 3×ULN' in result['source_text']
