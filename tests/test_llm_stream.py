"""Verifier SSE transport. Synthetic payloads only; no live endpoints or saved sources."""
import hashlib
import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from ciw.verify.crosscheck import _FORMAT_ERRORS
from ciw.verify.llm import CachedBackend, OpenAICompatBackend, load_roles

_SECRET = "synthetic-private-stream-marker"


def _backend(**kwargs):
    values = dict(timeout=30, stream=True, response_format=None)
    values.update(kwargs)
    return OpenAICompatBackend("glm", "glm-5.3-flash", "https://example.com/v1", None, **values)


def _install(monkeypatch, opener):
    monkeypatch.setattr("urllib.request.build_opener", lambda *_: opener)


def _cache_count(ws):
    with ws.db() as con:
        return con.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]


class _Chunks:
    def __init__(self, chunks, content_type="text/event-stream", clock=None, step=0):
        self.chunks = list(chunks)
        self.headers = {"Content-Type": content_type}
        self.timeouts = []
        self.clock = clock
        self.step = step

    def settimeout(self, value):
        self.timeouts.append(value)

    def read(self, _n=-1):
        if self.clock is not None:
            self.clock[0] += self.step
        if not self.chunks:
            return b""
        return self.chunks.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def _event(payload):
    return ("data: " + json.dumps(payload) + "\n\n").encode()


def _happy_chunks():
    role = _event({
        "id": "msg_stream", "model": "glm-observed",
        "choices": [{"index": 0, "delta": {"role": "assistant", "reasoning_content": "do-not-keep"},
                     "finish_reason": None}],
    })
    marker = "甲".encode()
    first_obj = {"id": "msg_stream", "model": "glm-observed", "choices": [
        {"index": 0, "delta": {"content": marker.decode()}}]}
    first = ("data: " + json.dumps(first_obj, ensure_ascii=False) + "\n\n").encode()
    left = (
        '{"id":"msg_stream","model":"glm-observed","choices":'
        '[{"index":0,"delta":{"content":"乙\\n丙"},"finish_reason":null}'
    )
    multiline = ("data: " + left + "\ndata: ]}\n\n").encode()
    finish = _event({
        "id": "msg_stream", "model": "glm-observed",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    })
    usage = _event({
        "id": "msg_stream", "model": "glm-observed", "choices": [],
        "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
    })
    done = b": keep-alive\n\ndata: [DONE]\n\n"
    wire = b": keep-alive\n\n" + role + first + multiline + finish + usage + done
    mark = "\u7532".encode()
    at = wire.find(mark)
    return [wire[:at + 1], wire[at + 1:]]


def _opener(calls, response):
    class Opener:
        def open(self, req, timeout=None):
            calls.append((json.loads(req.data), timeout, req))
            return response
    return Opener()


def test_only_the_verifier_role_streams():
    roles = load_roles()
    assert roles["verifier"].stream is True
    assert roles["extractor_a"].stream is False
    assert roles["verifier"].timeout == roles["extractor_a"].timeout == 7200
    assert roles["verifier"].max_tokens == roles["extractor_a"].max_tokens == 65536
    assert roles["verifier"].reasoning_effort is None


def test_sse_keeps_content_metadata_and_exact_cache_key(monkeypatch, ws):
    clock = [0.0]
    response = _Chunks(_happy_chunks(), clock=clock, step=1)
    calls = []
    _install(monkeypatch, _opener(calls, response))
    monkeypatch.setattr("ciw.verify.transport.monotonic", lambda: clock[0])
    backend = CachedBackend(_backend(), ws)
    text = backend.chat("system", "synthetic-user")
    assert text == "\u7532\u4e59\n\u4e19" and "keep-alive" not in text and "assistant" not in text
    body = calls[0][0]
    assert body["stream"] is True and body["stream_options"] == {"include_usage": True}
    assert set(body) == {"model", "temperature", "max_tokens", "messages", "stream", "stream_options"}
    assert len(calls) == 1 and response.timeouts == [30, 29, 28]
    receipt = backend.receipt
    assert receipt["cached"] is False and receipt["response_transport"] == "sse"
    assert receipt["response_id"] == "msg_stream" and receipt["response_model"] == "glm-observed"
    assert receipt["finish_reason"] == "stop" and receipt["usage"]["total_tokens"] == 5
    assert "do-not-keep" not in text and "do-not-keep" not in json.dumps(receipt)
    prompt_sha = hashlib.sha256(b"system\x00synthetic-user").hexdigest()
    key = hashlib.sha256(f"glm|glm-5.3-flash|{prompt_sha}".encode()).hexdigest()
    with ws.db() as con:
        row = con.execute("SELECT cache_key, response, metadata FROM llm_cache").fetchone()
    assert row[0] == key and row[1] == "\u7532\u4e59\n\u4e19" and "do-not-keep" not in row[2]

    def fail(*_args, **_kwargs):
        raise AssertionError("cached stream output must not open another request")

    _install(monkeypatch, type("Closed", (), {"open": staticmethod(fail)}))
    replay = CachedBackend(_backend(stream=False), ws)
    assert replay.chat("system", "synthetic-user") == "\u7532\u4e59\n\u4e19"
    assert replay.receipt["cached"] is True


def test_old_nonstream_cache_hits_without_http_when_stream_turns_on(monkeypatch, ws):
    calls = []

    class Response:
        def read(self):
            return json.dumps({"id": "old", "model": "plain", "choices": [
                {"finish_reason": "stop", "message": {"content": "cached-bytes"}}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    class Opener:
        def open(self, req, timeout=None):
            calls.append(json.loads(req.data))
            return Response()

    _install(monkeypatch, Opener())
    assert CachedBackend(_backend(stream=False), ws).chat("system", "synthetic-user") == "cached-bytes"
    assert "stream" not in calls[0]

    def fail(*_args, **_kwargs):
        raise AssertionError("stream toggle must reuse the non-stream cache key")

    _install(monkeypatch, type("Closed", (), {"open": staticmethod(fail)}))
    again = CachedBackend(_backend(stream=True), ws)
    assert again.chat("system", "synthetic-user") == "cached-bytes" and again.receipt["cached"] is True
    assert len(calls) == 1


def test_length_finish_with_done_keeps_truncation_metadata(monkeypatch, ws):
    chunks = [
        _event({"id": "msg_len", "model": "glm-observed", "choices": [
            {"index": 0, "delta": {"content": "partial-token"}, "finish_reason": "length"}]}),
        b"data: [DONE]\n\n",
    ]
    calls = []
    _install(monkeypatch, _opener(calls, _Chunks(chunks)))
    backend = CachedBackend(_backend(), ws)
    assert backend.chat("system", "synthetic-user") == "partial-token"
    assert backend.receipt["finish_reason"] == "length" and backend.receipt["response_transport"] == "sse"
    assert len(calls) == 1 and _cache_count(ws) == 1


def test_explicit_json_completion_does_not_send_a_second_request(monkeypatch, ws):
    raw = json.dumps({"id": "json-1", "model": "glm-json", "usage": {"total_tokens": 9}, "choices": [
        {"finish_reason": "stop", "message": {"content": "full-json"}}]}).encode()
    calls = []
    _install(monkeypatch, _opener(calls, _Chunks([raw], content_type="application/json; charset=utf-8")))
    backend = CachedBackend(_backend(), ws)
    assert backend.chat("system", "synthetic-user") == "full-json"
    assert len(calls) == 1 and calls[0][0]["stream"] is True
    assert backend.receipt["response_transport"] == "json" and backend.receipt["response_id"] == "json-1"


@pytest.mark.parametrize("chunks", [
    [b'data: {"choices":[{"index":0,"delta":{"content":"cut"},"finish_reason":"stop"}]}\n\n'],
    [b'data: {"choices":[{"index":0,"delta":{"content":"cut"}}]}\n\ndata: [DONE]\n\n'],
    [b"data: {not-json}\n\n"],
    ["\u7532".encode()[:2]],
])
def test_incomplete_stream_is_operational_and_not_cached(monkeypatch, ws, chunks):
    calls = []
    _install(monkeypatch, _opener(calls, _Chunks(chunks)))
    backend = CachedBackend(_backend(), ws)
    with pytest.raises(OSError) as caught:
        backend.chat("system", "synthetic-user")
    assert type(caught.value) is OSError and type(caught.value).__name__ not in _FORMAT_ERRORS
    assert len(calls) == 1 and _cache_count(ws) == 0
    assert backend.receipt.get("cached") is not True


def test_error_event_keeps_only_the_operational_category(monkeypatch, ws):
    payload = _event({"error": {"message": "overload " + _SECRET}})
    calls = []
    _install(monkeypatch, _opener(calls, _Chunks([payload])))
    backend = CachedBackend(_backend(), ws)
    with pytest.raises(OSError) as caught:
        backend.chat("system", "synthetic-user")
    assert type(caught.value) is OSError and caught.value.rejection_kind == "service_busy"
    assert len(calls) == 1 and _cache_count(ws) == 0
    assert _SECRET not in str(caught.value) and _SECRET not in json.dumps(backend.receipt)


def test_json_error_body_is_not_cached_or_retried(monkeypatch, ws):
    raw = json.dumps({"error": {"message": "overload " + _SECRET}}).encode()
    calls = []
    _install(monkeypatch, _opener(calls, _Chunks([raw], content_type="application/json")))
    backend = CachedBackend(_backend(), ws)
    with pytest.raises(OSError) as caught:
        backend.chat("system", "synthetic-user")
    assert type(caught.value) is OSError and backend.receipt["rejection_kind"] == "service_busy"
    assert len(calls) == 1 and _cache_count(ws) == 0 and _SECRET not in json.dumps(backend.receipt)


def test_unexpected_content_type_is_not_read_or_cached(monkeypatch, ws):
    calls = []

    class Response:
        headers = {"Content-Type": "text/html"}

        def read(self, _n=-1):
            raise AssertionError("unexpected body must not be consumed")

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    class Opener:
        def open(self, req, timeout=None):
            calls.append(json.loads(req.data))
            return Response()

    _install(monkeypatch, Opener())
    backend = CachedBackend(_backend(), ws)
    with pytest.raises(OSError) as caught:
        backend.chat("system", "synthetic-user")
    assert type(caught.value) is OSError and len(calls) == 1 and _cache_count(ws) == 0
    assert "text/html" not in str(caught.value)


def test_gateway_504_is_not_retried_or_cached(monkeypatch, ws):
    calls = []

    class Opener:
        def open(self, req, timeout=None):
            calls.append(json.loads(req.data))
            raise HTTPError(req.full_url, 504, "gateway", {}, BytesIO(f'{{"error":"{_SECRET}"}}'.encode()))

    _install(monkeypatch, Opener())
    backend = CachedBackend(_backend(), ws)
    with pytest.raises(HTTPError):
        backend.chat("system", "synthetic-user")
    assert len(calls) == 1 and calls[0]["stream"] is True
    assert backend.receipt["http_status"] == 504 and _cache_count(ws) == 0
    assert _SECRET not in json.dumps(backend.receipt) and "HTTPError" not in _FORMAT_ERRORS


def test_deadline_includes_429_wait_and_does_not_reset_for_chunks(monkeypatch, ws):
    clock = [0.0]
    reads = []

    class Response:
        headers = {"Content-Type": "text/event-stream"}

        def settimeout(self, value):
            self.armed = value

        def read(self, _n=-1):
            reads.append(self.armed)
            clock[0] += self.armed
            return b": ping\n\n"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    opens = []

    class Opener:
        def open(self, req, timeout=None):
            opens.append((req, timeout))
            if len(opens) == 1:
                raise HTTPError(req.full_url, 429, "rejected", {"Retry-After": "1"},
                                BytesIO(b'{"detail":"maximum concurrent requests"}'))
            return Response()

    _install(monkeypatch, Opener())
    monkeypatch.setattr("ciw.verify.transport.monotonic", lambda: clock[0])
    monkeypatch.setattr("ciw.verify.transport.sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    backend = CachedBackend(_backend(timeout=12), ws)
    with pytest.raises(TimeoutError):
        backend.chat("system", "synthetic-user")
    assert [item[1] for item in opens] == [12, 7] and reads == [7]
    assert opens[0][0] is opens[1][0] and _cache_count(ws) == 0


@pytest.mark.parametrize("event", [
    {"choices": [{"message": {"content": '{"items":[]}'}}]},
    {"choices": [{"finish_reason": "", "message": {"content": '{"items":[]}'}}]},
    {"choices": [{"finish_reason": "network_error", "message": {"content": '{"items":[]}'}}]},
    {"choices": [{"finish_reason": {}, "message": {"content": '{"items":[]}'}}]},
    {"error": {"message": _SECRET}, "choices": [
        {"finish_reason": "stop", "message": {"content": '{"items":[]}'}}]},
    {"choices": [{"index": 1, "finish_reason": "stop", "message": {"content": '{"items":[]}'}}]},
])
def test_json_fallback_requires_one_finished_nonerror_completion(monkeypatch, ws, event):
    calls = []
    _install(monkeypatch, _opener(calls, _Chunks([json.dumps(event).encode()], "application/json")))
    with pytest.raises(OSError):
        CachedBackend(_backend(), ws).chat("system", "source")
    assert len(calls) == 1 and _cache_count(ws) == 0


@pytest.mark.parametrize("events", [
    [{"error": {"message": _SECRET}, "choices": [
        {"index": 0, "delta": {"content": "bad"}, "finish_reason": "stop"}]}],
    [{"choices": [{"index": 0, "delta": {"content": "bad"}, "finish_reason": "network_error"}]}],
    [{"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
     {"choices": [{"index": 0, "delta": {"content": "late"}}]}],
    [{"id": "one", "choices": [{"delta": {}, "finish_reason": "stop"}]},
     {"id": "two", "choices": [], "usage": {}}],
])
def test_sse_error_or_changed_completion_cannot_be_cached(monkeypatch, ws, events):
    calls = []
    wire = [_event(e) for e in events] + [b"data: [DONE]\n\n"]
    _install(monkeypatch, _opener(calls, _Chunks(wire)))
    with pytest.raises(OSError):
        CachedBackend(_backend(), ws).chat("system", "source")
    assert len(calls) == 1 and _cache_count(ws) == 0


def test_unicode_line_separator_is_content_not_an_sse_frame_boundary(monkeypatch, ws):
    calls = []
    payload = {"choices": [{"index": 0, "delta": {"content": "甲\u2028乙"}, "finish_reason": "stop"}]}
    wire = ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\ndata: [DONE]\n\n").encode()
    _install(monkeypatch, _opener(calls, _Chunks([wire])))
    assert CachedBackend(_backend(), ws).chat("system", "source") == "甲\u2028乙"


def test_incomplete_http_chunk_stays_operational_and_does_not_retry(monkeypatch, ws):
    from http.client import IncompleteRead
    calls = []

    class Broken(_Chunks):
        def read(self, _n=-1):
            raise IncompleteRead(b"private-partial-stream", 10)

    _install(monkeypatch, _opener(calls, Broken([])))
    with pytest.raises(OSError):
        CachedBackend(_backend(), ws).chat("system", "source")
    assert len(calls) == 1 and _cache_count(ws) == 0



def test_stream_uses_a_single_read_per_deadline_and_never_requests_format_repair(monkeypatch, ws):
    from pydantic import BaseModel

    from ciw.verify.crosscheck import CrosscheckFailed, ExtractionTask, crosscheck
    from ciw.verify.llm import FakeBackend

    calls = []

    class Broken(_Chunks):
        def read(self, _n=-1):
            raise AssertionError("SSE must not block collecting a full read buffer")

        def read1(self, _n=-1):
            return super().read(_n)

    _install(monkeypatch, _opener(calls, Broken([b'data: {"choices":[]}\n\n'])))

    class Item(BaseModel):
        name: str
        quote: str

    task = ExtractionTask("synthetic", "source", "alpha", "Read alpha", Item, ("name",), ("name",))
    a = FakeBackend("deepseek", "fake", lambda *_: '{"items":[{"name":"alpha","quote":"alpha"}]}')
    with pytest.raises(CrosscheckFailed) as caught:
        crosscheck(task, {"extractor_a": a, "verifier": CachedBackend(_backend(), ws)})
    assert [c["role"] for c in caught.value.calls] == ["extract", "verify"]
    assert caught.value.calls[-1]["error"] == "OSError"
    assert len(calls) == 1 and _cache_count(ws) == 0
