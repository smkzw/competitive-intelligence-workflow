"""Ordinary pipeline must activate native CTR designs, not require model rephrasing."""
from copy import deepcopy

import pytest
from test_china_design import design_capture
from test_china_design_adoption import registered

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.stages import _design_extra, trial_evidence
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service
from ciw2.sources import china_detail


def setup(settings,monkeypatch,count=1):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('登记适应症',['C'])
    rc=svc.context(pid,svc.db.create_run(pid))
    rc.stage='trial_evidence'
    drug,_=svc.db.upsert_entity(pid,'drug','原药软膏')
    monkeypatch.setattr('ciw2.sources.ctgov.search',lambda *a,**kw:[])
    payloads={}
    for i in range(count):
        raw=design_capture()
        raw['registry_id']=f'CTR{i:08}'
        raw['title']=raw['registry_id']+'详细信息'
        raw['basic'][0][1]=raw['registry_id']
        raw['tables'][0]['rows'][0][1]=raw['registry_id']
        raw['tables'].append({'rows':[['年龄','18岁(最小年龄)至45岁(最大年龄)']],'nested':[]})
        tid,_=svc.db.upsert_entity(pid,'trial',raw['registry_id'],attrs={
            'registry':'chinadrugtrials','registry_detail_id':raw['detail_id']})
        svc.db.link(pid,drug,'drug-trial',tid)
        payloads[raw['registry_id']]=(raw,registered(rc.tool_ctx(),raw))
    calls=[]
    def detail(ctx,ctr):
        calls.append((ctx.run_id,ctr))
        return {'source_id':payloads[ctr][1]}
    monkeypatch.setattr(china_detail,'browser_detail',detail)
    return rc,payloads,calls


def test_normal_stage_adopts_full_design_and_resumes_without_reopening_same_run(settings,monkeypatch):
    rc,_payloads,calls=setup(settings,monkeypatch)
    trial_evidence(rc)
    assert len(rc.db.current_facts(rc.project_id))>10
    assert len(calls)==1
    trial_evidence(rc)
    assert len(calls)==1
    row=report_data(rc.db,rc.project_id,'C')['rows'][0]
    assert len(row['primary_endpoints'])==2 and len(row['arms'])==3
    assert row['identity']['companies'][0]['role']=='登记申请人'
    assert row['identity']['companies'][0]['name']=='原申请人公司'
    assert row['identity']['drug_label']=='原药软膏'
    assert row['identity']['phase_label']=='I 期'
    assert report_data(rc.db,rc.project_id,'C')['charts']['phase']==[{'name':'I 期','value':1}]
    assert _design_extra(rc,rc.db.entities(rc.project_id,'drug')[0])['trials_with_registry_design']==['CTR00000000']
    html=render_report(rc.db,rc.project_id,'C')
    assert '18岁' in html and '国内试验' in html and '原申请人公司' in html
    assert '中国站点 —' not in html and 'COMPARATOR' not in html.split('data-original-value="COMPARATOR">')[1].split('</div>')[0]


def test_changed_source_invalidates_receipt_and_new_run_checks_again(settings,monkeypatch):
    rc,payloads,calls=setup(settings,monkeypatch)
    trial_evidence(rc)
    raw=deepcopy(payloads['CTR00000000'][0])
    raw['basic'][1][1]='已完成'
    payloads['CTR00000000']=(raw,registered(rc.tool_ctx(),raw))
    trial_evidence(rc)
    assert len(calls)==2
    status=[f['value'] for f in rc.db.current_facts(rc.project_id) if f['field']=='status.trial']
    assert status==['已完成']
    rc.run_id=rc.db.create_run(rc.project_id)
    trial_evidence(rc)
    assert len(calls)==3


def test_budget_and_individual_failure_keep_complete_neighbors_and_explicit_pending(settings,monkeypatch):
    rc,_payloads,calls=setup(settings,monkeypatch,count=3)
    rc.cache['max_china_trials']=1
    with pytest.raises(IncompleteWork) as err:trial_evidence(rc)
    assert len(err.value.output['pending_trials'])==2 and len(calls)==1
    rc.cache['max_china_trials']=None
    good=china_detail.browser_detail
    def fail(ctx,ctr):
        if ctr=='CTR00000001':raise RuntimeError('source unavailable')
        return good(ctx,ctr)
    monkeypatch.setattr(china_detail,'browser_detail',fail)
    with pytest.raises(IncompleteWork) as err:trial_evidence(rc)
    assert len(err.value.output['pending_trials'])==1
    assert {f['entity_id'] for f in rc.db.current_facts(rc.project_id)}=={
        t['id'] for t in rc.db.entities(rc.project_id,'trial') if t['name']!='CTR00000001'}
    assert any('source unavailable' in e for e in err.value.output['errors'])
    monkeypatch.setattr(china_detail,'browser_detail',good)
    assert trial_evidence(rc)['pending_trials']==[]


def test_native_source_only_identity_uses_registered_drug_without_inventing_mah(settings,monkeypatch):
    from ciw2.render.trial_identity import trial_identities
    from ciw2.sources.china_ingest import _activate_design
    rc,payloads,_=setup(settings,monkeypatch)
    raw,sid=payloads['CTR00000000']
    tid=_activate_design(rc.tool_ctx(),raw['registry_id'],raw,sid,'china:detail')['entity_id']
    rc.db.execute("DELETE FROM links WHERE rel='drug-trial'")
    identity=trial_identities(rc.db,rc.project_id)[tid]
    assert identity['drug_label']==raw['tables'][0]['rows'][1][1]
    assert [c['role'] for c in identity['companies']]==['登记申请人']
    rc.db.execute("DELETE FROM links WHERE rel='chinadrugtrials-current'")
    assert not trial_identities(rc.db,rc.project_id)[tid]['companies']
