import json

import pytest

from ciw.verify.llm import CachedBackend, FakeBackend, OpenAICompatBackend, _read_key, load_roles


def test_role_contract_uses_only_explicit_dgx_credentials(monkeypatch, tmp_path):
    path = tmp_path / "key"
    path.write_text("test-only-key")
    monkeypatch.setenv("CIW_DGX_KEY_FILE", str(path))
    roles = load_roles()
    assert {r.family for r in roles.values()} == {"deepseek", "qwen", "glm"}
    assert roles["extractor_b"].response_format is None
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
