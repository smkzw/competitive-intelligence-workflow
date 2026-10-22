import json

import httpx
import pytest

from ciw2.harness.fallback import FallbackLLM
from ciw2.harness.llm import LLMError, LLMReply, OpenAICompatLLM, ScriptedLLM


@pytest.mark.parametrize(('message', 'usage'), [
    ({'content': '', 'reasoning_content': 'internal reasoning'}, {'completion_tokens': 10}),
    ({'content': '', 'reasoning_content': 'internal reasoning'}, ['malformed usage']),
    ({'content': 'OK but no required tool'}, {}),
    ({'tool_calls': [{'id': 'x', 'function': {'name': 'submit_result', 'arguments': '{bad'}}]}, {}),
])
def test_incomplete_required_function_response_fails_once(message, usage):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={'model': 'test', 'choices': [{'message': message, 'finish_reason': 'stop'}],
                                         'usage': usage})

    client = OpenAICompatLLM('http://localhost:1/v1', 'synthetic', 'test')
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(respond))
    try:
        with pytest.raises(LLMError):
            client.chat([], [{'type': 'function', 'function': {'name': 'submit_result', 'parameters': {}}}])
        assert len(calls) == 1
    finally:
        client._client.close()


def test_provider_protocol_failure_reaches_only_configured_next_route():
    primary = OpenAICompatLLM('http://localhost:1/v1', 'synthetic', 'deepseek', max_retries=1)
    primary._client.close()
    primary._client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
        'model': 'DeepSeek-V4.1-Flash-TF', 'choices': [{'message': {'reasoning_content': 'reasoning only'}}],
        'usage': {'completion_tokens': 10}})))
    backup = ScriptedLLM([LLMReply(content='ready', raw={'model': 'Qwen3.8'})])
    backup.model = 'qwen'
    try:
        result = FallbackLLM([primary, backup]).chat([])
        assert result.content == 'ready'
        assert result.raw['_ciw_route']['previous_failures'] == ['deepseek']
        detail = result.raw['_ciw_route']['failure_details'][0]
        assert detail['requested_model'] == 'deepseek' and detail['actual_model'] == 'DeepSeek-V4.1-Flash-TF'
        assert detail['usage']['completion_tokens'] == 10
    finally:
        primary._client.close()


def test_malformed_provider_response_is_not_a_programming_error():
    client = OpenAICompatLLM('http://localhost:1/v1', 'synthetic', 'test', max_retries=1)
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'choices': []})))
    try:
        with pytest.raises(LLMError):
            client.chat([])
    finally:
        client._client.close()


def test_http_failure_keeps_status_but_not_provider_body_or_credentials(monkeypatch):
    waits = []
    monkeypatch.setattr('ciw2.harness.llm.time.sleep', waits.append)
    client = OpenAICompatLLM('http://localhost:1/v1', 'synthetic-private-key', 'test', max_retries=1)
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        401, text='provider echoed synthetic-private-key')))
    try:
        with pytest.raises(LLMError) as caught:
            client.chat([])
        assert '401' in str(caught.value) and 'synthetic-private-key' not in str(caught.value)
        assert waits == []
    finally:
        client._client.close()
