"""Relevant summary/search dependencies, rather than sibling safety extraction."""
from __future__ import annotations

import importlib
import re

import pytest
from runtime_resume_helpers import service

from ciw2.pipeline import expansion, stage_versions, tool_versions
from ciw2.pipeline.runner import stages_for
from ciw2.sources import ctgov, http


def context(settings):
    svc=service(settings);pid=svc.create_project('来源依赖范围',['A','B','C'])
    return svc.context(pid,svc.db.create_run(pid))


def binding(rc,name):
    plan=stages_for(['A','B','C']);index=next(i for i,s in enumerate(plan) if s.name==name)
    return stage_versions.stage_binding(rc,plan[index],[s.name for s in plan[:index]])


def changed(fn):
    namespace={'__name__':fn.__module__}
    exec(compile(f'def {fn.__name__}(*args, **kwargs):\n return {{"changed":True}}\n',fn.__code__.co_filename,'exec'),namespace)  # noqa: S102 - compiled offline fixture
    return namespace[fn.__name__]


def test_safety_parser_change_keeps_search_and_summary_but_invalidates_ingestion(settings,monkeypatch):
    rc=context(settings);before={n:binding(rc,n) for n in ['universe_china','extract_design','trial_evidence']}
    monkeypatch.setattr(ctgov,'ae_facts',changed(ctgov.ae_facts))
    monkeypatch.setattr(ctgov,'EXTRACTOR_VERSION',ctgov.EXTRACTOR_VERSION+'-safety-upgrade')
    assert binding(rc,'universe_china')==before['universe_china']
    assert binding(rc,'extract_design')==before['extract_design']
    assert binding(rc,'trial_evidence')!=before['trial_evidence']


@pytest.mark.parametrize('helper',['parse_study','_aliases','map_phase','_g','search'])
def test_used_summary_helper_invalidates_search(settings,monkeypatch,helper):
    rc=context(settings);before=binding(rc,'universe_china')
    monkeypatch.setattr(ctgov,helper,changed(getattr(ctgov,helper)))
    assert binding(rc,'universe_china')!=before


def test_source_http_policy_is_a_real_search_dependency(settings,monkeypatch):
    rc=context(settings);before=tool_versions.tool_binding(rc,'ctgov_search')
    monkeypatch.setattr(http,'fetch',changed(http.fetch))
    assert tool_versions.tool_binding(rc,'ctgov_search')!=before


def test_identifier_validation_is_still_bound(settings,monkeypatch):
    rc=context(settings);before=binding(rc,'universe_china')
    monkeypatch.setattr(ctgov,'NCT_RE',re.compile(r'^NCT\d{8,9}$'))
    assert binding(rc,'universe_china')!=before


def test_summary_helper_binding_does_not_depend_on_whole_file_extractor_version(settings,monkeypatch):
    rc=context(settings);before=tool_versions.tool_binding(rc,'ctgov_search')
    monkeypatch.setattr(ctgov,'EXTRACTOR_VERSION','f'*64)
    assert tool_versions.tool_binding(rc,'ctgov_search')==before


def test_expansion_search_contract_ignores_sibling_ae_only_upgrade(settings,monkeypatch):
    before=expansion.CODE_HASH
    try:
        with monkeypatch.context() as patch:
            patch.setattr(ctgov,'EXTRACTOR_VERSION',ctgov.EXTRACTOR_VERSION+'-safety-only')
            importlib.reload(expansion)
            assert expansion.CODE_HASH==before
    finally:
        importlib.reload(expansion)


def test_actual_imported_helper_alias_is_bound_not_only_its_module_name(settings,monkeypatch):
    rc=context(settings);before=tool_versions.tool_binding(rc,'ctgov_search')
    monkeypatch.setattr(ctgov,'fetch',changed(http.fetch))
    assert tool_versions.tool_binding(rc,'ctgov_search')!=before


def test_expansion_source_cache_uses_current_tool_and_real_source_bytes(settings,monkeypatch):
    from ciw2.sources.http import Fetched, register_text
    rc=context(settings);rc.stage='universe_expand';calls=[]

    def fetch(ctx,url,**kwargs):
        calls.append(url);text='{"studies":[]}'
        sid=register_text(ctx,kind='ctgov',url=url,text=text)
        return Fetched(sid,url,200,text.encode(),text,'application/json')

    monkeypatch.setattr(ctgov,'fetch',fetch)
    query={'tool':'ctgov_search','id':'global:test','region':'global','term':'condition','registry':None,
           'arguments':{'condition':'condition','route_id':'global:test','region':'global'}}
    first,status=expansion._source(rc,query,True)
    assert status=='fetched' and len(calls)==1 and first['source_ids']
    assert expansion._source(rc,query,True)[1]=='cached' and len(calls)==1
    with monkeypatch.context() as patch:
        patch.setattr(ctgov,'ae_facts',changed(ctgov.ae_facts))
        patch.setattr(ctgov,'EXTRACTOR_VERSION','new-safety-parser')
        assert expansion._source(rc,query,True)[1]=='cached' and len(calls)==1
    monkeypatch.setattr(ctgov,'map_phase',changed(ctgov.map_phase))
    assert expansion._source(rc,query,True)[1]=='fetched' and len(calls)==2
    assert rc.db.stage_output(rc.run_id,next(row['name'] for row in rc.db.query(
        "SELECT name FROM stages WHERE run_id=? AND name LIKE 'expansion_source:%'",(rc.run_id,))))['sources']


@pytest.mark.parametrize('name',['ctgov_search','ctgov_get'])
def test_reachable_tuple_key_phase_map_changes_summary_tool_binding(settings,monkeypatch,name):
    rc=context(settings);before=tool_versions.tool_binding(rc,name)
    monkeypatch.setitem(ctgov._PHASE,('PHASE3',),'phase3-changed')
    assert tool_versions.tool_binding(rc,name)!=before


def test_tuple_key_map_is_stable_but_key_order_and_values_are_meaningful():
    payload=stage_versions._constant_payload
    left={('A','B'):'ab',('C',):'c'}
    assert payload(left) is not None
    assert payload(left)==payload(dict(reversed(list(left.items()))))
    assert payload(left)!=payload({('B','A'):'ab',('C',):'c'})
    assert payload(left)!=payload({('A','B'):'changed',('C',):'c'})


def test_real_expansion_source_cache_refetches_when_phase_map_changes(settings,monkeypatch):
    from ciw2.sources.http import Fetched, register_text
    rc=context(settings);rc.stage='universe_expand';calls=[]
    def fetch(ctx,url,**kwargs):
        calls.append(url);text='{"studies":[]}'
        sid=register_text(ctx,kind='ctgov',url=url,text=text)
        return Fetched(sid,url,200,text.encode(),text,'application/json')
    monkeypatch.setattr(ctgov,'fetch',fetch)
    query={'tool':'ctgov_search','id':'global:test','region':'global','term':'condition','registry':None,
           'arguments':{'condition':'condition','route_id':'global:test','region':'global'}}
    assert expansion._source(rc,query,True)[1]=='fetched'
    assert expansion._source(rc,query,True)[1]=='cached'
    monkeypatch.setitem(ctgov._PHASE,('PHASE3',),'phase3-changed')
    assert expansion._source(rc,query,True)[1]=='fetched' and len(calls)==2
