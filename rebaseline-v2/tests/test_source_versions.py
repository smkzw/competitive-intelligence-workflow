"""Current source-version defects. Offline counterexamples; no historical rewrites."""
import copy
import json

import httpx
import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import ctgov
from ciw2.sources.http import fetch, register_text, source_by_url


def context(settings):
    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = svc.create_project('适应症', ['C'])
    return svc.context(pid, svc.db.create_run(pid)).tool_ctx()


def versions(monkeypatch, first, second=None):
    queue = [copy.deepcopy(first), copy.deepcopy(second if second is not None else first)]

    def get(ctx, nct):
        study = queue.pop(0)
        sid = register_text(ctx, kind='ctgov', url=f'{ctgov.API}/{nct}', text=json.dumps(study))
        return study, sid

    monkeypatch.setattr(ctgov, 'get_study', get)


def test_changed_current_source_value_is_not_silently_ignored(settings, study, monkeypatch):
    ctx = context(settings)
    second = copy.deepcopy(study)
    second['protocolSection']['designModule']['enrollmentInfo']['count'] = 1000
    versions(monkeypatch, study, second)
    nct = study['protocolSection']['identificationModule']['nctId']
    ctgov.ingest_trial(ctx, nct)
    old = ctx.db.one("SELECT * FROM facts WHERE project_id=? AND field='design.sample_size'", (ctx.project_id,))
    ctgov.ingest_trial(ctx, nct)
    current = [f for f in ctx.db.current_facts(ctx.project_id) if f['field'] == 'design.sample_size']
    assert [f['value'] for f in current] == [1000]
    assert current[0]['source_id'] != old['source_id']
    assert ctx.db.one('SELECT * FROM facts WHERE id=?', (old['id'],)) == old


def test_requested_study_identity_mismatch_cannot_create_adopted_facts(settings, study, monkeypatch):
    ctx = context(settings)
    versions(monkeypatch, study)
    requested = 'NCT00000001'
    assert study['protocolSection']['identificationModule']['nctId'] != requested
    with pytest.raises((ValueError, RuntimeError), match='登记号|NCT'):
        ctgov.ingest_trial(ctx, requested)
    assert ctx.db.current_facts(ctx.project_id) == []


def test_failed_source_bundle_preserves_previous_facts_and_trial_metadata(settings, study, monkeypatch):
    ctx = context(settings)
    second = copy.deepcopy(study)
    second['protocolSection']['designModule']['enrollmentInfo']['count'] = 1000
    endpoints = second['protocolSection']['outcomesModule']['primaryOutcomes']
    endpoints.extend({'measure': f'Additional endpoint {i}', 'timeFrame': 'Week 24'} for i in range(3))
    versions(monkeypatch, study, second)
    nct = study['protocolSection']['identificationModule']['nctId']
    ctgov.ingest_trial(ctx, nct)
    before = ctx.db.current_facts(ctx.project_id)
    before_entity = ctx.db.entities(ctx.project_id, 'trial')
    original = ctx.db.add_fact
    calls = []

    def fail_third(fact):
        calls.append(fact)
        if len(calls) == 3:
            raise RuntimeError('simulated atomic insertion failure')
        return original(fact)

    monkeypatch.setattr(ctx.db, 'add_fact', fail_third)
    with pytest.raises(RuntimeError, match='atomic insertion'):
        ctgov.ingest_trial(ctx, nct)
    assert ctx.db.current_facts(ctx.project_id) == before
    assert ctx.db.entities(ctx.project_id, 'trial') == before_entity
    rejected = ctx.db.query("SELECT content FROM agent_steps WHERE role='source_rejection'")
    assert len(rejected) == 1 and json.loads(rejected[0]['content'])['reason_type'] == 'RuntimeError'


def test_identical_network_recheck_and_cache_reuse_have_distinct_receipts(settings):
    ctx = context(settings)
    ctx.extra = {'fetch_cache': {}}
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, text='Identical source bytes.')

    url = 'https://example.org/source?api_key=synthetic-secret'
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        a = fetch(ctx, url, kind='web', client=client)
        cached = fetch(ctx, url, kind='web', client=client)
        ctx.extra = {'fetch_cache': {}}
        b = fetch(ctx, url, kind='web', client=client)
    assert a.source_id == b.source_id and len(calls) == 2
    assert a.mode == b.mode == 'network_checked' and a.status == b.status == 200
    assert cached.mode == 'cache_reused' and cached.status is None and cached.network_checked_at is None
    records = [json.loads(row['content']) for row in ctx.db.query(
        "SELECT content FROM agent_steps WHERE run_id=? AND role='source_observation' ORDER BY id", (ctx.run_id,))]
    assert [record['mode'] for record in records] == ['network_checked', 'cache_reused', 'network_checked']
    assert records[1]['network_checked_at'] is None
    assert records[0]['network_checked_at'] and records[2]['network_checked_at']
    assert 'synthetic-secret' not in json.dumps(records)


def test_unchanged_registry_source_is_idempotent(settings, study, monkeypatch):
    ctx = context(settings)
    versions(monkeypatch, study)
    nct = study['protocolSection']['identificationModule']['nctId']
    first = ctgov.ingest_trial(ctx, nct)
    facts = ctx.db.query('SELECT * FROM facts ORDER BY rowid')
    second = ctgov.ingest_trial(ctx, nct)
    assert first['facts_added'] and second['facts_added'] == 0
    assert ctx.db.query('SELECT * FROM facts ORDER BY rowid') == facts


def test_new_registry_snapshot_preserves_independent_publication_and_history(settings, study, monkeypatch):
    ctx = context(settings)
    second = copy.deepcopy(study)
    second['protocolSection']['designModule']['enrollmentInfo']['type'] = 'ESTIMATED'
    second['protocolSection']['outcomesModule']['primaryOutcomes'] = []
    versions(monkeypatch, study, second)
    nct = study['protocolSection']['identificationModule']['nctId']
    first = ctgov.ingest_trial(ctx, nct)
    old = ctx.db.query('SELECT * FROM facts ORDER BY rowid')
    pub = register_text(ctx, kind='pubmed', url='https://pubmed.ncbi.nlm.nih.gov/123/', text='Independent paper')
    fid = ctx.db.add_fact({'project_id': ctx.project_id, 'entity_id': first['entity_id'],
        'field': 'result.primary.value', 'value': 0, 'status': 'verified', 'tier': 'critical',
        'source_id': pub, 'extracted_by': 'llm:test'})
    ctgov.ingest_trial(ctx, nct)
    current = ctx.db.current_facts(ctx.project_id)
    assert fid in {fact['id'] for fact in current}
    assert not [fact for fact in current if fact['field'] == 'design.primary_endpoint']
    size = [fact for fact in current if fact['field'] == 'design.sample_size']
    assert len(size) == 1 and size[0]['context']['enrollment_type'] == 'ESTIMATED'
    assert all(ctx.db.one('SELECT * FROM facts WHERE id=?', (fact['id'],)) == fact for fact in old)
    assert all(fact['supersedes'] is None for fact in ctx.db.query('SELECT * FROM facts'))


def test_reordered_outcomes_have_one_current_document_without_positional_merge(settings, study, monkeypatch):
    ctx = context(settings)
    first = copy.deepcopy(study)
    outcomes = first['protocolSection']['outcomesModule']['primaryOutcomes']
    outcomes.append({'measure': 'Additional distinct outcome', 'timeFrame': 'Week 52'})
    second = copy.deepcopy(first)
    second['protocolSection']['outcomesModule']['primaryOutcomes'].reverse()
    versions(monkeypatch, first, second)
    nct = first['protocolSection']['identificationModule']['nctId']
    ctgov.ingest_trial(ctx, nct)
    ctgov.ingest_trial(ctx, nct)
    current = [fact for fact in ctx.db.current_facts(ctx.project_id) if fact['field'] == 'design.primary_endpoint']
    assert len(current) == len(outcomes)
    assert sorted((f['value']['measure'], f['value']['time_frame']) for f in current) == sorted(
        (o['measure'], o['timeFrame']) for o in outcomes)


def test_reobserved_existing_content_is_current_without_rewriting_first_seen(settings):
    ctx = context(settings)
    url = 'https://example.org/versions'
    a = register_text(ctx, kind='web', url=url, text='Version A')
    first = ctx.db.one('SELECT * FROM sources WHERE id=?', (a,))
    b = register_text(ctx, kind='web', url=url, text='Version B')
    assert source_by_url(ctx, url)['id'] == b
    assert register_text(ctx, kind='web', url=url, text='Version A') == a
    assert source_by_url(ctx, url)['id'] == a
    assert ctx.db.one('SELECT * FROM sources WHERE id=?', (a,)) == first


def test_same_bytes_new_parser_builds_new_snapshot_and_preserves_legacy(settings, study, monkeypatch):
    ctx = context(settings)
    versions(monkeypatch, study)
    nct = study['protocolSection']['identificationModule']['nctId']
    first = ctgov.ingest_trial(ctx, nct)
    old_ids = {f['id'] for f in ctx.db.current_facts(ctx.project_id)}
    monkeypatch.setattr(ctgov, 'EXTRACTOR_VERSION', 'changed-parser-version')
    second = ctgov.ingest_trial(ctx, nct)
    current = ctx.db.current_facts(ctx.project_id)
    assert second['facts_added'] == first['facts_added'] == len(current)
    assert old_ids.isdisjoint(f['id'] for f in current)
    assert len(ctx.db.query('SELECT * FROM facts')) == first['facts_added'] * 2
    assert len(ctx.db.query('SELECT * FROM sources')) == 1


def test_old_project_without_snapshot_pointer_keeps_current_behavior(settings):
    ctx = context(settings)
    eid, _ = ctx.db.upsert_entity(ctx.project_id, 'trial', 'NCT00000001')
    fid = ctx.db.add_fact({'project_id': ctx.project_id, 'entity_id': eid, 'field': 'design.sample_size',
        'value': 0, 'tier': 'critical', 'status': 'verified', 'extracted_by': 'code:ctgov'})
    assert [f['id'] for f in ctx.db.current_facts(ctx.project_id)] == [fid]
