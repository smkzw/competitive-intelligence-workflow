import json

import httpx
import pytest

from ciw2.harness.llm import LLMProtocolError, OpenAICompatLLM

TOOLS = [{'type': 'function', 'function': {'name': 'submit_result', 'parameters': {
    'type': 'object', 'required': ['report', 'findings']}}}]


def response(finish, args=None):
    message = {'reasoning_content': 'synthetic-private-reasoning'}
    if args is not None:
        message['tool_calls'] = [{'id': 'done', 'function': {
            'name': 'submit_result', 'arguments': json.dumps(args)}}]
    return {'model': 'glm-5.3-flash', 'choices': [{'finish_reason': finish, 'message': message}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 8192 if finish == 'length' else 200}}


def client_for(outcomes, calls, **kwargs):
    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=outcomes.pop(0))

    client = OpenAICompatLLM('http://localhost:1', 'synthetic', 'glm-5.3-flash', max_retries=1, **kwargs)
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(respond))
    return client


@pytest.mark.parametrize('initial_args', [None, {}, {'report': 'C', 'findings': []}])
def test_length_recovery_is_same_input_same_model_once_and_keeps_safe_usage(initial_args):
    calls = []
    client = client_for([response('length', initial_args), response('tool_calls', {'report': 'C', 'findings': []})], calls)
    messages = [{'role': 'user', 'content': 'Full clinical definition'}]
    try:
        result = client.chat(messages, TOOLS)
        assert [c['max_tokens'] for c in calls] == [8192, 16384]
        assert all(c['model'] == 'glm-5.3-flash' and c['messages'] == messages and c['tools'] == TOOLS for c in calls)
        assert not any('thinking' in c or 'reasoning_effort' in c for c in calls)
        assert client.max_output_tokens == 8192
        recovery = result.raw['_ciw_output_recovery']
        assert recovery['from_tokens'] == 8192 and recovery['to_tokens'] == 16384
        assert recovery['previous_error']['usage']['completion_tokens'] == 8192
        assert 'synthetic-private-reasoning' not in json.dumps(recovery)
    finally:
        client._client.close()


def test_second_length_failure_is_terminal_with_both_attempts_metadata():
    calls = []
    client = client_for([response('length'), response('length')], calls)
    try:
        with pytest.raises(LLMProtocolError) as caught:
            client.chat([], TOOLS)
        assert len(calls) == 2
        assert caught.value.metadata['output_recovery']['previous_error']['usage']['completion_tokens'] == 8192
        assert caught.value.metadata['max_output_tokens'] == 16384
        assert 'synthetic-private-reasoning' not in json.dumps(caught.value.metadata)
    finally:
        client._client.close()


def test_explicit_output_ceiling_does_not_expand_again():
    calls = []
    client = client_for([response('length')], calls, max_output_tokens=16384)
    try:
        with pytest.raises(LLMProtocolError):
            client.chat([], TOOLS)
        assert [c['max_tokens'] for c in calls] == [16384]
    finally:
        client._client.close()


def test_recovered_request_logs_failed_budget_usage_but_not_private_reasoning(settings):
    from ciw2.harness.agent import run_skill
    from ciw2.harness.skills import parse_skill
    from ciw2.harness.tools import ToolContext, ToolRegistry
    from ciw2.store.db import DB

    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project('输出恢复', ['C'])
    rid = db.create_run(pid)
    skill = parse_skill('---\nname: recover\ndescription: d\ntools: []\noutput: AnalysisResult\nmax_steps: 4\n---\n正文')
    calls = []
    client = client_for([response('length'), response('tool_calls', {'report': 'C', 'findings': []})], calls)
    try:
        result = run_skill(skill, {}, client, ToolRegistry(), ToolContext(db=db, run_id=rid))
        assert result.report == 'C'
        log = db.one("SELECT content FROM agent_steps WHERE run_id=? AND role='model'", (rid,))
        event = json.loads(log['content'])
        assert event['usage']['completion_tokens'] == 200
        assert event['output_recovery']['previous_error']['usage']['completion_tokens'] == 8192
        assert all('synthetic-private-reasoning' not in row['content']
                   for row in db.query('SELECT content FROM agent_steps WHERE run_id=?', (rid,)))
    finally:
        client._client.close()
