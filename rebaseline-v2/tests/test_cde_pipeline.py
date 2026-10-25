"""The ordinary evidence stage must schedule proven CDE directories without an LLM."""
from dataclasses import replace

import pytest
from test_cde_biological_review import biological_pages
from test_cde_browser import capture
from test_cde_priority import captures
from test_cde_review_browser import invoke
from test_cde_review_capture import pages

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.stages import trial_evidence
from ciw2.service import Service
from ciw2.sources import cde_browser, china_browser


def workspace(settings,monkeypatch):
    svc=Service(replace(settings,china_ego_space_id=84),llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('登记来源流程',['A']);rc=svc.context(pid,svc.db.create_run(pid));rc.stage='trial_evidence'
    calls=[];fail={'priority':False};searches=[]
    def source(*a,**kw):
        script=kw['script_path'].name;calls.append(script)
        if script=='cde_browser.mjs':
            raw=capture(filters=kw['options']['filters'],total=2,rows=[
                ['1','CYHL2600085','原药A','化药','IND','','原企业','2026-01-01'],
                ['2','JXHS2600124','原药B','生物制品','NDA','','原企业','2026-01-01']])
            return invoke([raw])
        if script=='cde_priority.mjs':
            if fail['priority']:raise china_browser.BrowserFailed('source unavailable')
            return invoke(captures())
        return invoke(biological_pages() if kw['options']['filters']['sequence']=='生物' else pages())
    monkeypatch.setattr(china_browser,'_invoke',source)
    ctx=rc.tool_ctx();found=cde_browser.browser_search(ctx,'原企业','company');cde_browser.persist_candidates(ctx,found,'seed')
    calls.clear()
    def ctgov(ctx,**kw):searches.append(kw['intervention']);return []
    monkeypatch.setattr('ciw2.sources.ctgov.search',ctgov)
    return rc,calls,fail,searches


def test_normal_stage_schedules_three_directories_for_all_proven_applications_and_reuses_same_run(settings,monkeypatch):
    rc,calls,_,_=workspace(settings,monkeypatch)
    trial_evidence(rc)
    assert sorted(calls)==['cde_priority.mjs','cde_review_browser.mjs','cde_review_browser.mjs']
    drugs=rc.db.entities(rc.project_id,'drug')
    assert any(d['attrs'].get('cde_review_refs') for d in drugs)
    assert any(d['attrs'].get('cde_priority_refs') for d in drugs)
    assert not rc.llm.calls and not rc.db.current_facts(rc.project_id)
    trial_evidence(rc);assert len(calls)==3
    rc.run_id=rc.db.create_run(rc.project_id);trial_evidence(rc)
    assert len(calls)==6


def test_one_unavailable_directory_keeps_completed_neighbors_and_global_research(settings,monkeypatch):
    rc,calls,fail,searches=workspace(settings,monkeypatch);fail['priority']=True
    with pytest.raises(IncompleteWork) as caught:trial_evidence(rc)
    pending=caught.value.output['pending_trials']
    assert len(pending)==1 and pending[0]['kind']=='cde_directory'
    assert pending[0]['section']=='priority_included'
    assert set(pending[0]['acceptance_numbers'])=={'CYHL2600085','JXHS2600124'}
    assert set(searches)=={'原药A','原药B'}
    fail['priority']=False;trial_evidence(rc)
    assert calls.count('cde_review_browser.mjs')==2 and calls.count('cde_priority.mjs')==2


def test_forged_reference_does_not_trigger_remote_queries_or_link_another_product(settings,monkeypatch):
    rc,calls,_,_=workspace(settings,monkeypatch)
    rc.db.execute("UPDATE entities SET in_scope=0 WHERE project_id=?",(rc.project_id,))
    source=rc.db.entities(rc.project_id,'drug')[0]['attrs']['cde_acceptance_refs'][0]
    rc.db.upsert_entity(rc.project_id,'drug','另一个产品',attrs={'cde_acceptance_refs':[source]})
    with pytest.raises(IncompleteWork) as caught:trial_evidence(rc)
    assert calls==[] and caught.value.output['pending_trials'][0]['reason']=='unproven_application_binding'
    assert not rc.db.current_facts(rc.project_id)
