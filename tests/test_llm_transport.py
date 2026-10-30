import json

import pytest

from ciw.verify.llm import (
    CachedBackend,
    FakeBackend,
    OpenAICompatBackend,
    _read_key,
    load_roles,
    require_model_credentials,
)


def test_role_contract_uses_only_explicit_authorized_credentials(monkeypatch, tmp_path):
    path = tmp_path / "key"
    path.write_text("test-only-key")
    monkeypatch.setenv("CIW_DGX_KEY_FILE", str(path))
    monkeypatch.setenv("CMS_SMK_API_KEY", "test-only-cms-key")
    roles = load_roles()
    assert roles["extractor_a"].api_key == "test-only-key"
    assert roles["verifier"].api_key == "test-only-cms-key"
    assert {r.family for r in roles.values()} == {"deepseek", "glm"}
    assert roles["verifier"].response_format is None
    assert roles["verifier"].model == "glm-5.3-flash"
    assert roles["verifier"].base_url == "https://new-api.mediportal.com.cn/v1"
    assert roles["verifier"].no_proxy is False
    assert roles["verifier"].timeout == 7200
    assert roles["verifier"].max_tokens == 65536
    assert roles["extractor_a"].response_format is None
    assert roles["extractor_a"].max_tokens == 65536
    for spec in ({"key_env": ["MW_DGX_API_KEY"]}, {"default_key_file": str(path)}):
        with pytest.raises(ValueError):
            _read_key(spec)


def test_transport_preserves_actual_response_metadata_and_explicit_json_mode(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(
                {
                    "model": "qwen-served",
                    "id": "request-test",
                    "choices": [{"finish_reason": "stop", "message": {"content": '{"items":[]}'}}],
                }
            )

    class Opener:
        def open(self, req, **kwargs):
            requests.append(json.loads(req.data))
            return Response()

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    b = OpenAICompatBackend("qwen", "qwen", "https://example.com/v1", None, response_format=None)
    assert b.chat("system", "input") == '{"items":[]}'
    assert "response_format" not in requests[0]
    assert b.receipt["response_model"] == "qwen-served"


@pytest.mark.parametrize("status,wait,expected", [(429, "2", 2), (401, "2", 1),
                                                (503, "2", 1), (429, "9999", 1)])
def test_only_rejected_429_waits_within_budget_and_reuses_the_exact_request(monkeypatch, status, wait, expected):
    from io import BytesIO
    from urllib.error import HTTPError
    calls, pauses = [], []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self):
            return json.dumps(dict(model="served", choices=[dict(finish_reason="stop",
                message=dict(content='{"items":[]}'))])).encode()
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            if len(calls) == 1:
                raise HTTPError(req.full_url, status, "synthetic rejection", {"Retry-After":wait},
                                BytesIO(b'{"error":{"message":"synthetic"}}'))
            return Response()
    monkeypatch.setattr("urllib.request.build_opener", lambda *_: Opener())
    monkeypatch.setattr("ciw.verify.transport.sleep", pauses.append)
    b = OpenAICompatBackend("deepseek", "deepseek", "https://example.com/v1", None, timeout=600)
    if expected == 2:
        assert b.chat("s", "source") == '{"items":[]}'
        assert pauses == [5] and calls[0] is calls[1]
        assert b.receipt["admission_retries"] == [dict(http_status=429, wait_seconds=5)]
    else:
        with pytest.raises(HTTPError):
            b.chat("s", "source")
        assert not pauses
    assert len(calls) == expected


def test_repeated_429_has_finite_retries_without_success_or_cache(monkeypatch, ws):
    from io import BytesIO
    from urllib.error import HTTPError
    calls, pauses = [], []
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            raise HTTPError(req.full_url, 429, "synthetic rejection", {}, BytesIO(b'{}'))
    monkeypatch.setattr("urllib.request.build_opener", lambda *_: Opener())
    monkeypatch.setattr("ciw.verify.transport.sleep", pauses.append)
    backend = CachedBackend(OpenAICompatBackend("deepseek", "deepseek", "https://example.com/v1", None), ws)
    with pytest.raises(HTTPError):
        backend.chat("s", "source")
    assert len(calls) == 6 and pauses == [5, 10, 20, 40, 60]
    with ws.db() as con:
        assert con.execute("SELECT count(*) FROM llm_cache").fetchone()[0] == 0


def test_one_second_retry_hint_cannot_create_a_busy_retry_loop(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    calls, pauses = [], []
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            raise HTTPError(req.full_url,429,"synthetic rejection",{"Retry-After":"1"},BytesIO(b'{}'))
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    monkeypatch.setattr("ciw.verify.transport.sleep",pauses.append)
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None)
    with pytest.raises(HTTPError):
        b.chat("s","source")
    assert pauses == [5,10,20,40,60] and len(calls) == 6


@pytest.mark.parametrize("kind,message,limit", [
    ("concurrency", "maximum concurrent requests", None),
    ("model_transition", "model is loading", None),
    ("context_capacity", "KV cache pool full", None),
    ("context_capacity", "insufficient KV cache capacity", None),
    ("request_rate", "rate limit exceeded", 6), ("quota", "insufficient balance", 1)])
def test_only_confirmed_temporary_admission_limits_get_longer_bounded_wait(monkeypatch, kind, message, limit):
    from io import BytesIO
    from urllib.error import HTTPError
    calls, pauses, clock = [], [], [0.0]
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            raise HTTPError(req.full_url,429,"rejected",{"Retry-After":"1"},
                            BytesIO(json.dumps(dict(detail=message)).encode()))
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    monkeypatch.setattr("ciw.verify.transport.monotonic",lambda:clock[0])
    def wait(seconds):
        pauses.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr("ciw.verify.transport.sleep",wait)
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None,timeout=7200)
    with pytest.raises(HTTPError):
        b.chat("s","source")
    assert len(calls) == len(pauses)+1
    if limit is None:
        assert 900 < sum(pauses) < 7200 <= sum(pauses)+60
    else:
        assert len(calls) == limit and sum(pauses) <= 180
    assert b.receipt["rejection_kind"] == kind
    assert all(req is calls[0] for req in calls)


def test_busy_admission_can_recover_after_old_retry_window_without_retrying_accepted_requests(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    calls, clock = [], [0.0]
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self):
            return json.dumps(dict(model="served", choices=[dict(finish_reason="stop",
                message=dict(content='{"items":[]}'))])).encode()
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            if len(calls) <= 7:
                raise HTTPError(req.full_url,429,"rejected",{},BytesIO(b'{"detail":"maximum concurrent requests"}'))
            return Response()
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    monkeypatch.setattr("ciw.verify.transport.monotonic",lambda:clock[0])
    monkeypatch.setattr("ciw.verify.transport.sleep",lambda seconds:clock.__setitem__(0,clock[0]+seconds))
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None)
    assert b.chat("s","source") == '{"items":[]}' and len(calls) == 8
    assert clock[0] == 255 and b.receipt["response_model"] == "served"


def test_quota_vetoes_temporary_signals_and_final_error_stream_is_closed(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    body = BytesIO(json.dumps(dict(detail="maximum concurrent requests; insufficient quota")).encode())
    calls = []
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            raise HTTPError(req.full_url,429,"rejected",{},body)
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    monkeypatch.setattr("ciw.verify.transport.sleep",lambda *_:pytest.fail("quota must not retry"))
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None)
    with pytest.raises(HTTPError):
        b.chat("s","source")
    assert b.receipt["rejection_kind"] == "quota" and len(calls) == 1 and body.closed


@pytest.mark.parametrize("timeout", [.01, 0])
def test_exact_total_timeout_is_not_raised_to_one_tenth_of_a_second(monkeypatch, timeout):
    calls=[]
    class Opener:
        def open(self, req, **kwargs):
            calls.append(kwargs["timeout"])
            raise TimeoutError("synthetic timeout")
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    monkeypatch.setattr("ciw.verify.transport.monotonic",lambda:0)
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None,timeout=timeout)
    with pytest.raises(TimeoutError):
        b.chat("s","source")
    assert calls == ([timeout] if timeout else [])


def test_oversize_private_error_body_is_closed_even_if_it_cannot_be_classified(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    body=BytesIO(json.dumps(dict(detail="private-marker"*1000)).encode())
    class Opener:
        def open(self, req, **kwargs):
            raise HTTPError(req.full_url,401,"rejected",{},body)
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None)
    with pytest.raises(HTTPError):
        b.chat("s","source")
    assert body.closed and "private-marker" not in json.dumps(b.receipt)


@pytest.mark.parametrize("message,kind", [("maximum concurrent requests", "concurrency"),
    ("rate limit exceeded", "request_rate"), ("insufficient balance", "quota"),
    ("KV cache pool full", "context_capacity"), ("model is loading", "model_transition")])
def test_error_receipts_classify_rejections_without_retaining_upstream_private_text(monkeypatch, message, kind):
    from io import BytesIO
    from urllib.error import HTTPError
    secret = "synthetic-private-marker-do-not-retain"
    class Opener:
        def open(self, req, **kwargs):
            raise HTTPError(req.full_url,429,"rejected",{"Retry-After":"9999"},
                BytesIO(json.dumps(dict(error=dict(message=message + " " + secret))).encode()))
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None)
    with pytest.raises(HTTPError):
        b.chat("s","source")
    assert b.receipt["rejection_kind"] == kind
    assert secret not in json.dumps(b.receipt)


@pytest.mark.parametrize("detail", ["maximum concurrent requests: synthetic-private-marker",
                                    {"reason":"maximum concurrent requests: synthetic-private-marker"}])
def test_gateway_detail_error_shapes_preserve_only_the_operational_category(monkeypatch, detail):
    from io import BytesIO
    from urllib.error import HTTPError
    class Opener:
        def open(self, req, **kwargs):
            raise HTTPError(req.full_url,429,"rejected",{"Retry-After":"9999"},
                            BytesIO(json.dumps(dict(detail=detail)).encode()))
    monkeypatch.setattr("urllib.request.build_opener",lambda *_:Opener())
    b=OpenAICompatBackend("deepseek","deepseek","https://example.com/v1",None)
    with pytest.raises(HTTPError):
        b.chat("s","source")
    assert b.receipt["rejection_kind"] == "concurrency"
    assert "synthetic-private-marker" not in json.dumps(b.receipt)


def test_content_cache_keeps_original_receipt_without_another_model_call(ws):
    calls = []
    b = FakeBackend("qwen", "qwen", lambda *args: calls.append(args) or '{"items":[]}')
    b.receipt = {"response_model": "served-model", "response_id": "original-call"}
    a = CachedBackend(b, ws)
    assert a.chat("s", "original source") == '{"items":[]}'
    c = CachedBackend(b, ws)
    assert c.chat("s", "original source") == '{"items":[]}'
    assert len(calls) == 1 and c.receipt["cached"]
    assert c.receipt["response_id"] == "original-call"


@pytest.mark.parametrize('text', [
    '{"items": []}\n说明：原文只有剂量，没有靶点。',
    '核对说明：没有靶点。\n\n{"items": []}',
    '核对说明：无遗漏。\n\n```json\n{"items": []}\n```',
    '```json\n{"items": []}\n```\n核对说明：未报告。',
    '{"items": [{"quote": "literal {braces}"}]}\n说明：保留原文。',
])
def test_one_json_document_can_have_trailing_explanation(text):
    from ciw.verify.llm import parse_json
    assert isinstance(parse_json(text)["items"], list)


@pytest.mark.parametrize('text', [
    '{"items": []}\n{"items": [{"value": 9}]}',
    '```json\n{"items": []}\n```\n```json\n{"items": [1]}\n```',
    '{"items": [], "items": [1]}',
])
def test_multiple_documents_and_duplicate_keys_are_not_first_or_last_wins(text):
    from ciw.verify.llm import parse_json
    with pytest.raises(ValueError):
        parse_json(text)


def test_attribute_effort_is_scoped_and_does_not_relabel_the_clinical_extractor(ws):
    roles = load_roles()
    original = CachedBackend(roles["extractor_a"], ws)
    attributes = original.for_attributes()
    assert original.inner.reasoning_effort is None
    assert attributes.inner.reasoning_effort == "low"
    assert attributes.model == original.model == "deepseek"
    assert roles["verifier"].reasoning_effort is None


def test_missing_live_credentials_fail_before_network_while_inspection_and_stubs_remain_usable(monkeypatch):
    for name in ("CIW_DGX_API_KEY", "CIW_DGX_KEY_FILE", "CMS_SMK_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    roles = load_roles()  # configuration inspection alone does not call services
    assert roles["extractor_a"].api_key is None
    with pytest.raises(ValueError, match="模型凭据未配置"):
        require_model_credentials(roles)
    stub = {"extractor_a": FakeBackend("deepseek", "a", lambda *_: "{}"),
            "verifier": FakeBackend("glm", "b", lambda *_: "{}")}
    assert require_model_credentials(stub) is stub


def test_effort_variants_do_not_reuse_a_different_request_receipt(ws):
    calls = []
    backend = FakeBackend("test-family", "same-model", lambda *args: calls.append(args) or '{"items":[]}')
    base = CachedBackend(backend, ws)
    base.chat("schema", "source")
    backend.reasoning_effort = "low"
    fast = CachedBackend(backend, ws)
    fast.chat("schema", "source")
    fast.chat("schema", "source")
    assert len(calls) == 2 and fast.receipt["cached"]


def test_temporary_model_transition_keeps_both_models_cache_records(ws):
    calls = []
    original = CachedBackend(FakeBackend("glm", "glm-5.3-flash", lambda *_: calls.append("cms") or "old"), ws)
    temporary = CachedBackend(FakeBackend("glm", "glm", lambda *_: calls.append("dgx") or "new"), ws)
    assert original.chat("same schema", "same source") == "old"
    assert temporary.chat("same schema", "same source") == "new"
    assert original.chat("same schema", "same source") == "old"
    assert temporary.chat("same schema", "same source") == "new"
    assert calls == ["cms", "dgx"]


@pytest.mark.parametrize("exists,content", [(False, ""), (True, ""), (True, "   ")])
def test_explicit_missing_or_empty_key_file_fails_before_any_request(monkeypatch, tmp_path, exists, content):
    path = tmp_path / "key"
    if exists:
        path.write_text(content)
    monkeypatch.delenv("CIW_DGX_API_KEY", raising=False)
    monkeypatch.setenv("CIW_DGX_KEY_FILE", str(path))
    with pytest.raises(ValueError, match="CIW_DGX_KEY_FILE") as error:
        load_roles()
    assert str(path) not in str(error.value)


@pytest.mark.parametrize('rejections,retry_after', [(20, '1'), (1, '3600')])
def test_confirmed_busy_uses_existing_whole_request_deadline_not_a_hidden_shorter_window(
        monkeypatch, rejections, retry_after):
    from io import BytesIO
    from urllib.error import HTTPError
    calls, remaining, clock = [], [], [0.0]
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self):
            return json.dumps(dict(model='served', choices=[dict(finish_reason='stop',
                message=dict(content='{"items":[]}'))])).encode()
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            remaining.append(kwargs['timeout'])
            if len(calls) <= rejections:
                raise HTTPError(req.full_url,429,'rejected',{'Retry-After':retry_after},
                                BytesIO(b'{"detail":"maximum concurrent requests"}'))
            return Response()
    monkeypatch.setattr('urllib.request.build_opener',lambda *_:Opener())
    monkeypatch.setattr('ciw.verify.transport.monotonic',lambda:clock[0])
    monkeypatch.setattr('ciw.verify.transport.sleep',lambda seconds:clock.__setitem__(0,clock[0]+seconds))
    b=OpenAICompatBackend('deepseek','deepseek','https://example.com/v1',None,timeout=7200)
    assert b.chat('s','source') == '{"items":[]}'
    assert len(calls) == rejections+1 and clock[0] > 900
    assert remaining[-1] == 7200-clock[0]
    assert all(req is calls[0] for req in calls)


def test_admission_latency_consumes_original_timeout_without_restarting_accepted_inference(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    calls, remaining, clock = [], [], [0.0]
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self):
            raise TimeoutError('accepted model response did not complete')
    class Opener:
        def open(self, req, **kwargs):
            calls.append(req)
            remaining.append(kwargs['timeout'])
            if len(calls) == 1:
                clock[0] += 20
                raise HTTPError(req.full_url,429,'rejected',{},BytesIO(b'{"detail":"model is loading"}'))
            return Response()
    monkeypatch.setattr('urllib.request.build_opener',lambda *_:Opener())
    monkeypatch.setattr('ciw.verify.transport.monotonic',lambda:clock[0])
    monkeypatch.setattr('ciw.verify.transport.sleep',lambda seconds:clock.__setitem__(0,clock[0]+seconds))
    b=OpenAICompatBackend('deepseek','deepseek','https://example.com/v1',None,timeout=100)
    with pytest.raises(TimeoutError):
        b.chat('s','source')
    assert len(calls) == 2 and remaining == [100, 75]
    assert calls[0] is calls[1] and clock[0] == 25
