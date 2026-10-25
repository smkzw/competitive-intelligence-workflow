"""Registered isotope labels must remain data, not Essie query operators."""
import json
from contextlib import contextmanager

import httpx
import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.stages import trial_evidence
from ciw2.service import Service
from ciw2.sources import ctgov, http


@contextmanager
def offline(monkeypatch, respond):
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(ctgov, "fetch", lambda c, u, **kw: http.fetch(c, u, client=client, **kw))
        yield


def context(settings, name):
    service = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = service.create_project('Paroxysmal Nocturnal Hemoglobinuria', ['C'])
    drug, _ = service.db.upsert_entity(pid, 'drug', name)
    rc = service.context(pid, service.db.create_run(pid))
    rc.stage = 'trial_evidence'
    return rc, drug


@pytest.mark.parametrize('name', ['[14C]HS-10542', '[14C] HSK39297'])
def test_registered_bracketed_name_is_sent_as_a_literal_phrase(settings, monkeypatch, name):
    rc, drug = context(settings, name)
    requests = []
    tid, _ = rc.db.upsert_entity(rc.project_id, 'trial', 'NCT00000001', attrs={
        'interventions': [{'name': name}], 'phase': 'phase1'})
    rc.db.link(rc.project_id, drug, 'drug-trial', tid)
    monkeypatch.setattr('ciw2.sources.ctgov.ingest_trial', lambda *a, **kw: {
        'entity_id': tid, 'facts_added': 0})

    def respond(request):
        requests.append(dict(request.url.params))
        if request.url.params['query.intr'] != json.dumps(name, ensure_ascii=False):
            return httpx.Response(400, text="Error parsing query: extraneous input '['")
        return httpx.Response(200, json={'totalCount': 0, 'studies': []})

    with offline(monkeypatch, respond):
        result = trial_evidence(rc)
    assert len(requests) == 1
    assert requests[0]['query.intr'] == json.dumps(name, ensure_ascii=False)
    assert requests[0]['query.cond'] == 'Paroxysmal Nocturnal Hemoglobinuria'
    assert requests[0]['pageSize'] == '100' and requests[0]['countTotal'] == 'true'
    assert result['pending_trials'] == [] and result['linked'] == 1
    assert rc.db.entities(rc.project_id, 'drug')[0]['name'] == name
    assert rc.db.one("SELECT 1 FROM links WHERE src=? AND dst=? AND rel='drug-trial'", (drug, tid))


@pytest.mark.parametrize('name', ['eculizumab', 'HS-10542', 'Drug multi word'])
def test_ordinary_intervention_queries_keep_existing_search_semantics(settings, monkeypatch, name):
    rc, _ = context(settings, name)
    queries = []

    def respond(request):
        queries.append(request.url.params['query.intr'])
        return httpx.Response(200, json={'totalCount': 0, 'studies': []})

    with offline(monkeypatch, respond):
        assert trial_evidence(rc)['pending_trials'] == []
    assert queries == [name]


@pytest.mark.parametrize('status', [400, 403])
def test_a_literal_search_failure_stays_pending_not_real_zero(settings, monkeypatch, status):
    name = '[14C]HS-10542'
    rc, _ = context(settings, name)
    with offline(monkeypatch, lambda request: httpx.Response(status, text='source request failed')), \
            pytest.raises(IncompleteWork) as failed:
        trial_evidence(rc)
    assert failed.value.output['pending_trials'][0]['reason'] == 'source_search_failed'
    assert len(failed.value.output['errors']) == 1
    assert rc.db.entities(rc.project_id, 'drug')[0]['name'] == name
