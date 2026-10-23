"""Cancellation at completed source-unit boundaries preserves same-run reuse."""
import pytest
from test_china_design_pipeline import setup
from test_expansion import setup_expansion
from test_workset_completion import context

from ciw2.domain.models import ExtractionResult
from ciw2.harness.cancellation import RunCancelled, RunControl
from ciw2.pipeline import china_evidence, expansion, stages


def test_china_stops_between_records_and_resume_reuses_completed_record(settings, monkeypatch):
    rc, _, calls=setup(settings,monkeypatch,count=3)
    rc.control=RunControl()
    original=china_evidence.china_ingest.ingest_trial

    def ingest(*args,**kwargs):
        result=original(*args,**kwargs)
        rc.control.request_stop()
        return result

    monkeypatch.setattr(china_evidence.china_ingest,'ingest_trial',ingest)
    with pytest.raises(RunCancelled):china_evidence.collect(rc)
    assert len(calls)==1 and rc.db.current_facts(rc.project_id)
    monkeypatch.setattr(china_evidence.china_ingest,'ingest_trial',original)
    rc.control=RunControl()
    assert china_evidence.collect(rc)['pending_trials']==[]
    assert len(calls)==3


def test_expansion_stops_before_next_source_without_rewriting_as_failure(settings,monkeypatch):
    _,rc,_,calls=setup_expansion(settings)
    rc.control=RunControl()
    original=expansion._source

    def read(*args,**kwargs):
        result=original(*args,**kwargs)
        rc.control.request_stop()
        return result

    monkeypatch.setattr(expansion,'_source',read)
    with pytest.raises(RunCancelled):expansion.expand_universe(rc,lambda result:0)
    assert len(calls)==1
    monkeypatch.setattr(expansion,'_source',original)
    rc.control=RunControl()
    result=expansion.expand_universe(rc,lambda result:0)
    assert result['reused_queries']==1 and result['expansion_complete']


def test_extraction_stops_between_batches_and_completed_cache_is_reused(settings,monkeypatch):
    rc=context(settings,count=3)
    rc.control=RunControl()
    calls=[]

    def extract(name,task):
        calls.append(task['drug']['name'])
        if len(calls)==1:rc.control.request_stop()
        return ExtractionResult(facts=[],gaps=[])

    monkeypatch.setattr(rc,'skill',extract)
    work=stages._extract('extract-design',stages._design_extra)
    with pytest.raises(RunCancelled):work(rc)
    assert len(calls)==1
    rc.control=RunControl()
    assert work(rc)['pending_units']==[]
    assert len(calls)==len(set(calls))==3


def test_ctgov_stops_between_trials_without_repeating_completed_trial(settings,monkeypatch):
    rc=context(settings)
    rc.control=RunControl()
    calls=[]
    drug=rc.db.entities(rc.project_id,'drug')[0]
    rows=[{'nct':f'NCT{i:08}','interventions':[{'name':drug['name']}]} for i in (1,2,3)]
    monkeypatch.setattr(stages.ctgov,'search',lambda *a,**kw:rows)

    def ingest(ctx,nct,**kwargs):
        calls.append(nct)
        tid,_=rc.db.upsert_entity(rc.project_id,'trial',nct)
        if len(calls)==1:rc.control.request_stop()
        return {'entity_id':tid,'facts_added':0}

    monkeypatch.setattr(stages.ctgov,'ingest_trial',ingest)
    with pytest.raises(RunCancelled):stages.trial_evidence(rc)
    assert len(calls)==1
    rc.control=RunControl()
    assert stages.trial_evidence(rc)['pending_trials']==[]
    assert len(calls)==len(set(calls))==3
