"""The native study API and fetch_url must share one current source identity."""
from __future__ import annotations

import json

import httpx
import pytest
from test_ctgov_document_fetch import API, JSON_TYPE, NCT, SHELL, offline, raw, study_document

from ciw2.domain.models import ScopeDecision, ScopeResult
from ciw2.pipeline import scope
from ciw2.service import Service
from ciw2.sources import http, websearch


def registered_pair(ctx, body):
    rows = []
    for kind in ('web', 'ctgov'):
        sid = http.register_text(ctx, kind=kind, url=API, text=body.decode(),
                                 meta={'content_type': 'application/json'})
        rows.append(ctx.db.one('SELECT * FROM sources WHERE id=?', (sid,)))
    return rows


def test_current_api_fetch_keeps_native_identity_and_legacy_web_record(settings, monkeypatch):
    from test_source_representations import context
    ctx = context(settings)
    body = raw(study_document())
    legacy, native = registered_pair(ctx, body)
    with offline(monkeypatch, lambda request: httpx.Response(200, content=body, headers=JSON_TYPE)) as calls:
        result = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=API))
    assert calls == [API]
    assert result['source_id'] == native['id']
    assert http.source_by_url(ctx, API)['id'] == native['id']
    assert ctx.db.one('SELECT * FROM sources WHERE id=?', (legacy['id'],)) == legacy
    assert len(ctx.db.query('SELECT * FROM sources')) == 2


@pytest.mark.parametrize(('body', 'ctype'), [
    (SHELL.encode(), 'text/html'),
    (raw(study_document('NCT00000001')), 'application/json'),
    (b'[]', 'application/json'),
], ids=['html-shell', 'wrong-study', 'array'])
def test_current_api_requires_the_matching_study_not_an_opaque_web_body(settings, monkeypatch, body, ctype):
    from test_source_representations import context
    ctx = context(settings)
    with offline(monkeypatch, lambda request: httpx.Response(
            200, content=body, headers={'content-type': ctype})), pytest.raises(ValueError):
        websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=API))
    rows = ctx.db.query('SELECT * FROM sources')
    assert len(rows) == 1 and rows[0]['kind'] == 'ctgov'
    assert ctx.cas.get(rows[0]['digest']) == body
    assert not ctx.extra.get('source_ids_read')


def test_scope_projection_and_actual_fetch_share_a_reusable_receipt(settings, monkeypatch):
    service = Service(settings)
    pid = service.create_project('Target disease', ['C'])
    rc = service.context(pid, service.db.create_run(pid))
    rc.stage = 'candidate_triage'
    drug, _ = rc.db.upsert_entity(pid, 'drug', 'Candidate')
    trial, _ = rc.db.upsert_entity(pid, 'trial', NCT)
    rc.db.link(pid, drug, 'drug-trial', trial)
    document = study_document()
    document['protocolSection']['conditionsModule'] = {'conditions': ['Target disease']}
    body = raw(document)
    ctx = rc.tool_ctx()
    legacy, native = registered_pair(ctx, body)
    tasks = []

    def skill(name, task):
        tasks.append(task)
        tool_ctx = rc.tool_ctx()
        result = websearch._fetch_url(tool_ctx, websearch.FetchUrlArgs(url=API))
        rc.cache['last_skill_source_ids'] = sorted(tool_ctx.extra['source_ids_read'])
        assert result['source_url'] == API
        return ScopeResult(decisions=[
            ScopeDecision(entity_id=drug, drug='Candidate', in_scope=True, reason='Offline target membership')])

    monkeypatch.setattr(rc, 'skill', skill)
    with offline(monkeypatch, lambda request: httpx.Response(200, content=body, headers=JSON_TYPE)) as calls:
        first = scope.review_scope(rc, 'Target disease')
        second = scope.review_scope(rc, 'Target disease')
    assert first == second
    assert len(tasks) == 1 and calls == [API]
    envelope = rc.db.stage_output(rc.run_id, scope._batch_key(rc, tasks[0]))
    cited = [s for s in envelope['sources'] if s['url'] == API]
    assert [s['id'] for s in cited] == [native['id']]
    assert ctx.db.one('SELECT * FROM sources WHERE id=?', (legacy['id'],)) == legacy
    assert ctx.db.current_facts(pid) == []
    assert json.loads(native['meta']) == {'content_type': 'application/json'}

