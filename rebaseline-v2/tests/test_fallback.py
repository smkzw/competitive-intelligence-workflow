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
    assert result.raw['_ciw_route'] == {'index': 1, 'model': 'deepseek', 'previous_failures': ['glm-5.3-flash']}
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
