"""Observed biological UI uses LCSYSQ, not the hidden chemical IND selector."""
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from test_cde_review_browser import invoke
from test_cde_review_capture import FILTERS, pages

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import cde_review_browser, china, china_browser
from ciw2.sources.cde_review_capture import CaptureError, parse_review_capture

BIO = {'sequence':'生物','task_type':'LCSYSQ','ui_acceptance_number':''}
SECTION = 'new_review_task_biological_trial'


@pytest.fixture
def ctx(settings):
    service=Service(replace(settings,china_ego_space_id=80),llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=service.create_project('审评范围组件测试',['A'])
    return service.context(pid,service.db.create_run(pid)).tool_ctx()


def biological_pages():
    captured=json.loads((Path(__file__).parent/'fixtures/cde-biological-review.json').read_text())
    first={**captured,'rows':deepcopy(captured['rows'][:2]),
           'pagination':{'current':1,'page_size':2,'text':'共 3 条'}}
    last={**captured,'rows':deepcopy(captured['rows'][2:]),
          'pagination':{'current':2,'page_size':2,'text':'共 3 条'}}
    return [first,last]


def test_observed_biological_scope_keeps_original_values_and_missing_pages():
    source=biological_pages()
    partial=parse_review_capture(source[:1],filters=BIO,allow_partial=True)
    assert partial['pending_pages']==[2] and not partial['complete']
    out=parse_review_capture(source,filters=BIO,acceptance_number='JXSL2600209')
    assert out['complete'] and out['matched_count']==1
    row=out['results'][0]
    assert row['drug_name']=='艰难梭菌佐剂疫苗'
    assert row['scope_filters']==BIO and row['raw_cells']==source[0]['rows'][0]
    assert not {'approved','target_indication','mah'} & row.keys()


@pytest.mark.parametrize('filters', [FILTERS, {**BIO,'task_type':'IND'}, {**BIO,'task_type':''}])
def test_wrong_or_hidden_filter_never_qualifies_biological_page(filters):
    with pytest.raises(CaptureError):
        parse_review_capture(biological_pages(),filters=filters)


def test_browser_cache_is_separate_for_each_observed_sequence(ctx,monkeypatch):
    calls=[]
    def capture(*args,**kwargs):
        filters=kwargs.get('options',{}).get('filters',FILTERS)
        calls.append(filters)
        return invoke(biological_pages() if filters==BIO else pages())
    monkeypatch.setattr(china_browser,'_invoke',capture)
    chemical=cde_review_browser.browser_search(ctx,'CYHL2600085','acceptance_number')
    biological=cde_review_browser.browser_search(ctx,'JXSL2600209','acceptance_number',section=SECTION)
    repeated=cde_review_browser.browser_search(ctx,'JXSL2600209','acceptance_number',section=SECTION)
    assert len(calls)==2 and calls==[FILTERS,BIO]
    assert chemical['source_id']!=biological['source_id']==repeated['source_id']
    for result,filters in ((chemical,FILTERS),(biological,BIO)):
        source=ctx.db.one('SELECT meta,digest FROM sources WHERE id=?',(result['source_id'],))
        assert json.loads(source['meta'])['request_context']['filters']==filters
        assert json.loads(ctx.cas.get(source['digest']))['filters']==filters
    assert not ctx.db.current_facts(ctx.project_id)


def test_public_tool_accepts_explicit_biological_trial_section(ctx,monkeypatch):
    def blocked(*args,**kwargs):
        raise china.RegistryBlocked('No direct interface')
    monkeypatch.setattr(china,'direct_search',blocked)
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:invoke(biological_pages()))
    result=china._china(ctx,china.ChinaArgs(registry='cde',query='JXSL2600209',
        query_kind='acceptance_number',cde_section=SECTION,route_id='china:cde:biological'))
    assert result['mode']=='browser' and result['complete'] and result['count']==1
    assert result['filters']==BIO and result['linked_refs']==0 and not result['persisted']
    assert not ctx.db.entities(ctx.project_id,'drug') and not ctx.db.current_facts(ctx.project_id)
