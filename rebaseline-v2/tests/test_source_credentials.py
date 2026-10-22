import json

import httpx
import pytest

from ciw2.harness.tools import ToolContext
from ciw2.sources.http import FetchError, fetch, public_url
from ciw2.store.cas import CAS
from ciw2.store.db import DB


def test_fetch_never_persists_request_query_credentials(settings):
    settings.ensure_dirs()
    db, cas = DB(settings.db_path), CAS(settings.cas_dir)
    pid = db.create_project('来源', ['C'])
    ctx = ToolContext(db=db, cas=cas, settings=settings, project_id=pid)
    secret = 'synthetic-private-source-key'
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'value': 100}))) as client:
        result = fetch(ctx, 'https://example.org/data', kind='web',
                       params={'id': 'study', 'api_key': secret}, client=client)
    row = db.one('SELECT * FROM sources WHERE id=?', (result.source_id,))
    assert secret not in json.dumps(row) and secret not in result.url
    assert 'id=study' in result.url


def test_http_error_never_exposes_query_credentials():
    secret = 'synthetic-private-source-key'
    with (httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401))) as client,
          pytest.raises(FetchError) as caught):
        fetch(None, 'https://example.org/data', kind='web', params={'api_key': secret}, client=client)
    assert secret not in str(caught.value)


def test_official_ctgov_public_pagination_is_not_an_auth_token():
    result = public_url('https://clinicaltrials.gov/api/v2/studies?pageToken=public-cursor&api_key=secret')
    assert 'pageToken=public-cursor' in result and 'secret' not in result
    assert 'secret' not in public_url('https://example.org/api?pageToken=secret')
    assert 'secret' not in public_url('https://clinicaltrials.gov/auth?pageToken=secret')


def test_same_run_fetch_reuses_captured_bytes_but_new_run_checks_again(settings):
    settings.ensure_dirs()
    db, cas = DB(settings.db_path), CAS(settings.cas_dir)
    pid = db.create_project('同运行资料复用', ['C'])
    shared = {}
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={'version': len(calls)})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        def read(cache, cursor='one'):
            ctx = ToolContext(db=db, cas=cas, project_id=pid, extra={'fetch_cache': cache})
            return fetch(ctx, 'https://example.org/data', params={'cursor': cursor}, kind='web', client=client)

        first, again = read(shared), read(shared)
        assert len(calls) == 1 and first.content == again.content and first.source_id == again.source_id
        assert read(shared, 'two').json()['version'] == 2
        assert read({}).json()['version'] == 3


def test_fetch_cache_keeps_existing_query_and_project_identity(settings):
    settings.ensure_dirs()
    db, cas, cache = DB(settings.db_path), CAS(settings.cas_dir), {}
    one, two = db.create_project('一', ['C']), db.create_project('二', ['C'])
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={'request_url': str(request.url)})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        def read(project, query):
            ctx = ToolContext(db=db, cas=cas, project_id=project, extra={'fetch_cache': cache})
            return fetch(ctx, f'https://example.org/data?paper={query}', kind='web', client=client)

        first = read(one, 'one')
        second = read(one, 'two')
        assert second.json()['request_url'].endswith('paper=two')
        assert first.source_id != second.source_id
        copied = read(two, 'one')
        assert db.one('SELECT project_id FROM sources WHERE id=?', (copied.source_id,))['project_id'] == two
        assert len(calls) == 3
