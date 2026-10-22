"""搜索提供方错误的安全边界：失败≠被拦≠空结果，且失败信息不落凭据。

全部离线：只替换 websearch 模块创建的 HTTP 客户端为 MockTransport，不访问真实服务，不使用真实密钥。
"""
from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources import websearch
from ciw2.sources.websearch import SearchBlocked, SearchFailed, web_search
from ciw2.store.db import DB

SECRET = "synthetic-search-key-7f3c9a"
ROUTE = "global:web:test"


def _search_settings(settings, provider: str = "serpapi", key: str = SECRET):
    return replace(settings, websearch_provider=provider, websearch_api_key=key)


@pytest.fixture
def serve_search(monkeypatch: pytest.MonkeyPatch):
    """把 websearch 内部创建的客户端换成离线 MockTransport。"""
    real_client = httpx.Client

    def install(handler) -> None:
        def factory(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_client(*args, **kwargs)

        monkeypatch.setattr(websearch.httpx, "Client", factory)

    return install


@pytest.fixture
def coverage_db(settings):
    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project("搜索错误", ["A"])
    return db, db.create_run(pid)


def _run_tool(ctx: ToolContext, query: str = "ipilimumab melanoma") -> dict:
    return json.loads(REGISTRY.get("web_search").run(ctx, {"query": query, "route_id": ROUTE, "max_results": 5}))


def _last_coverage(db: DB) -> dict:
    return db.one("SELECT * FROM coverage ORDER BY id DESC LIMIT 1")


def test_successful_search_returns_rows_and_logs_ok_hits(settings, coverage_db, serve_search):
    db, rid = coverage_db

    def respond(request):
        assert request.url.params["api_key"] == SECRET  # 凭据只出现在真实请求里
        return httpx.Response(200, json={"organic_results": [
            {"title": "CheckMate 067", "link": "https://example.org/checkmate", "snippet": "ipilimumab",
             "date": "2015"}]})

    serve_search(respond)
    ctx = ToolContext(db=db, settings=_search_settings(settings), run_id=rid)
    payload = _run_tool(ctx)

    assert payload["count"] == 1 and payload["results"][0]["url"] == "https://example.org/checkmate"
    assert _last_coverage(db)["status"] == "ok" and _last_coverage(db)["hits"] == 1


def test_empty_results_remain_empty_success_not_failed_or_blocked(settings, coverage_db, serve_search):
    db, rid = coverage_db
    serve_search(lambda request: httpx.Response(200, json={"organic_results": []}))
    ctx = ToolContext(db=db, settings=_search_settings(settings), run_id=rid)

    payload = _run_tool(ctx, "unfindable query")

    assert payload == {"count": 0, "results": []}
    assert _last_coverage(db)["status"] == "ok" and _last_coverage(db)["hits"] == 0


def test_provider_http_error_never_persists_query_key_url_or_provider_body(settings, coverage_db, serve_search):
    db, rid = coverage_db

    def respond(request):
        assert request.url.params["api_key"] == SECRET  # Serpapi 把密钥放在查询参数
        return httpx.Response(401, json={"error": f"Invalid API key: {SECRET}"})

    serve_search(respond)
    ctx = ToolContext(db=db, settings=_search_settings(settings), run_id=rid)
    payload = _run_tool(ctx)
    note = _last_coverage(db)["note"] or ""

    assert payload["status"] == "tool_failed"  # 不是 blocked，也不是空结果
    assert "count" not in payload and "results" not in payload
    for leak in (SECRET, "api_key", "serpapi.com", "Invalid API key"):
        assert leak not in json.dumps(payload, ensure_ascii=False)
        assert leak not in note
    assert "401" in payload["error"] and "HTTPStatusError" in payload["error"]
    assert _last_coverage(db)["status"] == "failed"


def test_transport_error_reports_type_without_raw_exception_text(settings, coverage_db, serve_search):
    db, rid = coverage_db

    def refuse(request):
        raise httpx.ConnectError(f"connection failed for {request.url}")

    serve_search(refuse)
    ctx = ToolContext(db=db, settings=_search_settings(settings), run_id=rid)
    payload = _run_tool(ctx)

    assert payload["status"] == "tool_failed"
    assert "ConnectError" in payload["error"]
    assert SECRET not in json.dumps(payload, ensure_ascii=False)
    assert "serpapi.com" not in payload["error"] and "api_key" not in payload["error"]
    assert _last_coverage(db)["status"] == "failed"


def test_invalid_provider_json_is_failed_without_echoing_body(settings, serve_search):
    body = f"<html><body>maintenance window (api_key={SECRET})</body></html>"
    serve_search(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text=body))

    with pytest.raises(SearchFailed) as caught:
        web_search(_search_settings(settings), "ipilimumab melanoma", 5)

    message = str(caught.value)
    assert "JSONDecodeError" in message
    assert SECRET not in message and "maintenance window" not in message


def test_unknown_and_missing_provider_stay_blocked(settings, coverage_db):
    db, rid = coverage_db
    with pytest.raises(SearchBlocked):
        web_search(_search_settings(settings, provider="none", key=""), "q", 1)
    with pytest.raises(SearchBlocked):
        web_search(_search_settings(settings, provider="acme-search"), "q", 1)

    ctx = ToolContext(db=db, settings=_search_settings(settings, provider="none", key=""), run_id=rid)
    payload = _run_tool(ctx, "unconfigured query")

    assert payload["status"] == "blocked"
    assert _last_coverage(db)["status"] == "blocked" and _last_coverage(db)["hits"] == 0


def test_malformed_provider_payload_is_not_silently_empty(settings, serve_search):
    serve_search(lambda request: httpx.Response(200, json={"results": {"unexpected": "shape"}}))

    with pytest.raises(SearchFailed):  # 外部数据形状必须在解析边界校验，不冒充内部程序错误或0结果
        web_search(_search_settings(settings, provider="tavily"), "q", 1)


@pytest.mark.parametrize('provider', ['tavily', 'bing', 'serpapi'])
def test_http_200_error_is_failed_not_empty(settings, coverage_db, serve_search, provider):
    db, rid = coverage_db
    serve_search(lambda request: httpx.Response(200, json={'error': f'account failure {SECRET}'}))
    result = _run_tool(ToolContext(db=db, settings=_search_settings(settings, provider), run_id=rid))
    assert result['status'] == 'tool_failed' and _last_coverage(db)['status'] == 'failed'
    assert SECRET not in json.dumps(result) and SECRET not in _last_coverage(db)['note']


def test_documented_serpapi_success_fully_empty_is_not_a_provider_failure(settings, coverage_db, serve_search):
    db, rid = coverage_db
    # https://serpapi.com/api-status-and-error-codes: success may carry error for genuine empty results.
    serve_search(lambda request: httpx.Response(200, json={
        'search_metadata': {'status': 'Success'}, 'search_information': {'organic_results_state': 'Fully empty'},
        'error': "Google hasn't returned any results for this query."}))
    result = _run_tool(ToolContext(db=db, settings=_search_settings(settings), run_id=rid))
    assert result == {'count': 0, 'results': []} and _last_coverage(db)['status'] == 'ok'


@pytest.mark.parametrize('payload', [{}, [], {'results': None}, {'results': [SECRET]}])
def test_malformed_response_shape_is_safe_failure(settings, serve_search, payload):
    serve_search(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(SearchFailed) as caught:
        web_search(_search_settings(settings, provider='tavily'), 'q', 1)
    assert SECRET not in str(caught.value)


@pytest.mark.parametrize('configured', [True, False])
def test_china_site_fallback_records_own_failed_or_blocked_route(settings, coverage_db, serve_search, monkeypatch, configured):
    from ciw2.sources import china

    def blocked(*args):
        raise china.RegistryBlocked('Synthetic direct challenge')

    monkeypatch.setattr(china, 'direct_search', blocked)
    db, rid = coverage_db
    serve_search(lambda request: httpx.Response(401, text=SECRET))
    s = _search_settings(settings) if configured else _search_settings(settings, provider='none', key='')
    result = json.loads(REGISTRY.get('china_registry_search').run(ToolContext(db=db, settings=s, run_id=rid),
        {'registry': 'chinadrugtrials', 'query': '适应症', 'route_id': 'china:test'}))
    assert result['status' if configured else 'mode'] == ('tool_failed' if configured else 'blocked')
    routes = db.query('SELECT route_id,status,note FROM coverage ORDER BY id')
    assert [(row['route_id'], row['status']) for row in routes] == [
        ('china:test', 'blocked'), ('china:test:site', 'failed' if configured else 'blocked')]
    assert SECRET not in json.dumps(routes)
