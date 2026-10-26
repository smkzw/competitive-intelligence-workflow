"""Failure evidence is local to one actual chat, not replayed at every later task."""
import pytest
from test_fallback import route

from ciw2.harness.fallback import FallbackLLM
from ciw2.harness.llm import LLMError, LLMReply, ScriptedLLM


def test_later_failed_chat_does_not_rebill_the_initial_fallback_chain():
    routes = [route(name, LLMError('unavailable')) for name in ('glm-5.3-flash', 'deepseek', 'qwen')]
    client = FallbackLLM(routes)
    with pytest.raises(LLMError): client.chat([])
    first = list(client.failure_details)
    assert [item['requested_model'] for item in first] == ['glm-5.3-flash', 'deepseek', 'qwen']
    with pytest.raises(LLMError): client.chat([])
    assert [item['requested_model'] for item in client.failure_details] == ['qwen']
    assert [item['requested_model'] for item in first] == ['glm-5.3-flash', 'deepseek', 'qwen']
    assert client.failures == ['glm-5.3-flash', 'deepseek', 'qwen']
    assert [len(llm.calls) for llm in routes] == [1, 1, 2]
    assert all(item['call_scope'] == 'current_chat' for item in client.failure_details)


def test_recovered_backup_reply_does_not_claim_an_old_failure_occurred_again():
    attempts = 0
    def transient(messages):
        nonlocal attempts
        attempts += 1
        if attempts <= 4: raise LLMError('temporarily unavailable')
        return LLMReply(content='recovered', raw={'model': 'actual-qwen'})
    qwen = ScriptedLLM(transient)
    qwen.model = 'qwen'
    primary = route('glm-5.3-flash', LLMError('unavailable'))
    client = FallbackLLM([primary, qwen])
    for _ in range(4):
        with pytest.raises(LLMError): client.chat([])
    result = client.chat([])
    assert result.content == 'recovered' and result.raw['model'] == 'actual-qwen'
    assert result.raw['_ciw_route']['failure_details'] == []
    assert client.failure_details == []
    assert client.failures == ['glm-5.3-flash', 'qwen']
    assert len(primary.calls) == 1 and len(qwen.calls) == 5


def test_many_last_route_failures_keep_evidence_bounded_without_changing_attempts():
    last = route('qwen', LLMError('limited'))
    client = FallbackLLM([last])
    for _ in range(135):
        with pytest.raises(LLMError): client.chat([])
        assert len(client.failure_details) == 1
        assert client.failures == ['qwen']
    assert len(last.calls) == 135
