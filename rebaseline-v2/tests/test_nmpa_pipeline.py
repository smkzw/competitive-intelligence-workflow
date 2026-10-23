"""Normal research-stage adoption, refresh and isolated source failures."""
from dataclasses import replace

import pytest
from test_nmpa_detail import FOREIGN, NUMBER, URL, foreign, install

from ciw2.harness.cancellation import RunCancelled
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.stages import trial_evidence
from ciw2.service import Service
from ciw2.sources import ctgov, nmpa_detail


@pytest.fixture
def workspace(settings,monkeypatch):
    svc=Service(replace(settings,china_ego_space_id=71))
    pid=svc.create_project('研究适应症',['A','B','C'])
    svc.db.upsert_entity(pid,'drug','Drug A Injection')
    rc=svc.context(pid,svc.db.create_run(pid))
    calls=[]
    install(monkeypatch,foreign(),calls=calls)
    source=nmpa_detail.browser_detail(rc.tool_ctx(),URL,NUMBER,FOREIGN)
    monkeypatch.setattr(ctgov,'search',lambda *a,**k:[])
    return rc,source,calls


def test_normal_trial_evidence_adopts_name_holder_and_retries_without_duplicate_facts(workspace):
    rc,_,calls=workspace
    first=trial_evidence(rc)
    assert first['nmpa']['adopted']==1 and len(calls)==1
    rows=rc.db.current_facts(rc.project_id)
    assert {f['field'] for f in rows}=={'identity.name_zh','identity.name_en','status.china_mah'}
    assert first['nmpa']['pending_records']==[] and first['nmpa']['unresolved']==[]
    assert trial_evidence(rc)['nmpa']['adopted']==0 and len(calls)==1
    assert rc.db.current_facts(rc.project_id)==rows


def test_new_run_rechecks_source_even_when_previous_adoption_was_complete(workspace):
    rc,_,calls=workspace
    trial_evidence(rc)
    rc.run_id=rc.db.create_run(rc.project_id)
    trial_evidence(rc)
    assert len(calls)==2
    assert len(rc.db.current_facts(rc.project_id))==3


def test_failed_refresh_keeps_old_facts_but_cannot_claim_complete_research(workspace,monkeypatch):
    rc,_,_=workspace
    trial_evidence(rc)
    before=rc.db.current_facts(rc.project_id)
    rc.run_id=rc.db.create_run(rc.project_id)
    def failed(*a,**k):
        raise RuntimeError('source transport failed')
    monkeypatch.setattr(nmpa_detail,'browser_detail',failed)
    with pytest.raises(IncompleteWork) as error:
        trial_evidence(rc)
    assert error.value.output['nmpa']['pending_records']==[
        {'registration_number':NUMBER,'reason':'source_identity_failed'}]
    assert rc.db.current_facts(rc.project_id)==before


def test_unresolved_formulation_is_visible_not_a_network_failure(workspace):
    rc,_,_=workspace
    rc.db.execute("UPDATE entities SET name='Drug A' WHERE project_id=? AND type='drug'",(rc.project_id,))
    out=trial_evidence(rc)
    assert out['nmpa']['adopted']==0 and len(out['nmpa']['unresolved'])==1
    assert out['nmpa']['pending_records']==[] and rc.db.current_facts(rc.project_id)==[]


def test_cancel_checked_before_a_certificate_unit(workspace,monkeypatch):
    from ciw2.pipeline.nmpa_evidence import collect
    rc,_,_=workspace
    def cancelled():
        raise RunCancelled('stopped')
    monkeypatch.setattr(rc,'check_cancelled',cancelled)
    with pytest.raises(RunCancelled):
        collect(rc)
    assert rc.db.current_facts(rc.project_id)==[]


@pytest.mark.parametrize('meta',['null','[]','{}','{"request_context":[]}','invalid'])
def test_invalid_source_request_is_isolated_and_not_an_empty_success(workspace,meta):
    from ciw2.pipeline.nmpa_evidence import collect
    rc,source,_=workspace
    rc.db.execute('UPDATE sources SET meta=? WHERE id=?',(meta,source['source_id']))
    out=collect(rc)
    assert out['pending_records']==[{'source_id':source['source_id'],'reason':'source_request_invalid'}]
    assert out['adopted']==0 and out['errors'] and rc.db.current_facts(rc.project_id)==[]


@pytest.mark.parametrize('repair_root',[False,True])
def test_source_proof_chain_closes_in_one_run_even_when_dependent_url_sorts_first(workspace,monkeypatch,repair_root):
    from test_nmpa_ingest import certificate, registered

    from ciw2.pipeline.nmpa_evidence import collect
    rc,primary,_=workspace
    if repair_root:
        from ciw2.sources import nmpa_ingest
        nmpa_ingest.activate_source(rc.tool_ctx(),primary['source_id'])
        rc.db.execute("UPDATE links SET attrs=json_remove(attrs,'$.extractor_version') WHERE rel='nmpa-current'")
        assert rc.db.current_facts(rc.project_id)==[]
    raw=certificate('0','国药准字SJ20240002',name_en='Other official name')
    assert raw['url']<URL
    sid=registered(rc.tool_ctx(),raw)
    original=nmpa_detail.browser_detail
    calls=[]
    def read(ctx,url,number,category):
        calls.append(url)
        return {'source_id':sid} if url==raw['url'] else original(ctx,url,number,category)
    monkeypatch.setattr(nmpa_detail,'browser_detail',read)
    out=collect(rc)
    assert out['adopted']==(1 if repair_root else 2) and out['unresolved']==[]
    assert len(rc.db.current_facts(rc.project_id))==6
    assert calls==[raw['url'],URL]  # Retrying identity never refetches source bytes.
