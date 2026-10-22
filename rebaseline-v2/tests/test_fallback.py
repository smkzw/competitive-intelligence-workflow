import json
from dataclasses import replace

import httpx
import pytest

from ciw2.harness.fallback import FallbackLLM
from ciw2.harness.llm import LLMError, LLMReply, OpenAICompatLLM, ScriptedLLM


def route(model, outcome):
    def reply(messages):
        if isinstance(outcome, Exception):
            raise outcome
        return LLMReply(content=outcome, raw={'model': model})
    llm = ScriptedLLM(reply)
    llm.model = model
    return llm


def test_backup_order_is_explicit_and_switch_is_recorded():
    primary = route('glm-5.3-flash', LLMError('unavailable'))
    deepseek = route('deepseek', 'ok')
    qwen = route('qwen', 'last')
    client = FallbackLLM([primary, deepseek, qwen])
    result = client.chat([{'role': 'user', 'content': 'test'}])
    assert client.model == 'deepseek'
    assert result.raw['_ciw_route'] == {'index': 1, 'model': 'deepseek', 'previous_failures': ['glm-5.3-flash'],
        'failure_details': [{'requested_model': 'glm-5.3-flash', 'error_type': 'LLMError'}]}
    assert len(primary.calls) == len(deepseek.calls) == 1 and not qwen.calls
    client.chat([{'role': 'user', 'content': 'continue'}])
    assert len(primary.calls) == 1 and len(deepseek.calls) == 2


def test_qwen_is_only_used_after_deepseek_failure():
    client = FallbackLLM([route('glm-5.3-flash', LLMError('1')), route('deepseek', LLMError('2')),
                          route('qwen', 'ok')])
    assert client.chat([]).content == 'ok' and client.model == 'qwen'


def test_unknown_programming_error_does_not_trigger_a_model_switch():
    broken = route('glm-5.3-flash', ValueError('defect'))
    backup = route('deepseek', 'ok')
    client = FallbackLLM([broken, backup])
    with pytest.raises(ValueError):
        client.chat([])
    assert not backup.calls


def test_service_uses_only_explicit_ordered_fallback_environment(settings, monkeypatch):
    from ciw2.service import default_llms
    monkeypatch.setenv('TEST_MODEL_URL', 'http://localhost:1/v1')
    monkeypatch.setenv('TEST_MODEL_KEY', 'synthetic-test-key')
    config = json.dumps([{'model': name, 'base_url_env': 'TEST_MODEL_URL',
                          'api_key_env': 'TEST_MODEL_KEY'} for name in ('deepseek', 'qwen')])
    main, check = default_llms(replace(settings, llm_model='glm-5.3-flash', llm_fallbacks=config))
    assert [r.model for r in main.routes] == ['glm-5.3-flash', 'deepseek', 'qwen']
    assert check is None
    assert main.routes[0]._client.timeout.read == 300
    assert main.routes[0].max_retries == 1
    for route_client in main.routes:
        route_client._client.close()


def test_service_rejects_missing_backup_configuration(settings):
    from ciw2.service import default_llms
    with pytest.raises(LLMError, match='备用模型配置'):
        default_llms(replace(settings, llm_fallbacks='[{"model":"backup"}]'))


def test_llm_output_is_bounded_and_actual_model_is_retained():
    seen = []
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={'model': 'test-model', 'choices': [{'message': {'content': 'ok'}}]})
    llm = OpenAICompatLLM('http://localhost:1/v1', 'synthetic', 'test-model', max_retries=1)
    llm._client.close()
    llm._client = httpx.Client(transport=httpx.MockTransport(respond))
    reply = llm.chat([{'role': 'user', 'content': 'test'}])
    llm._client.close()
    assert reply.raw['model'] == 'test-model'
    assert 0 < seen[0]['max_tokens'] <= 8192


def test_default_primary_matches_current_user_choice(monkeypatch, tmp_path):
    from ciw2.config import Settings
    monkeypatch.delenv('CIW_LLM_BASE_URL', raising=False)
    monkeypatch.delenv('CIW_LLM_MODEL', raising=False)
    settings = Settings(data_dir=tmp_path)
    assert settings.llm_model == 'glm-5.3-flash'
    assert settings.llm_base_url == 'http://127.0.0.1:20128/v1'


@pytest.mark.parametrize(('requested', 'actual', 'ok'), [
    ('glm-5.3-flash', 'unrequested-model', False),
    ('glm-5.3-flash', None, False),
    ('deepseek', 'DeepSeek-V4.1-Flash-TF', True),
    ('qwen', 'Qwen3.8-27B', True),
])
def test_response_model_identity_cannot_silently_change(requested, actual, ok):
    def respond(request):
        return httpx.Response(200, json={'model': actual, 'choices': [{'message': {'content': 'ok'}}]})
    client = OpenAICompatLLM('http://localhost:1/v1', 'synthetic', requested, max_retries=1)
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(respond))
    try:
        if ok:
            assert client.chat([]).raw['model'] == actual
        else:
            with pytest.raises(LLMError, match='模型身份'):
                client.chat([])
    finally:
        client._client.close()


def test_submit_only_interaction_requests_required_function():
    seen = []

    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={'model': 'test', 'choices': [{'message': {
            'tool_calls': [{'id': 'finish', 'function': {'name': 'submit_result', 'arguments': '{}'}}]}}]})

    client = OpenAICompatLLM('http://localhost:1/v1', 'synthetic', 'test', max_retries=1)
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(respond))
    try:
        client.chat([], [{'type': 'function', 'function': {'name': 'submit_result', 'parameters': {}}}])
        assert seen[0]['tool_choice'] == {'type': 'function', 'function': {'name': 'submit_result'}}
    finally:
        client._client.close()
