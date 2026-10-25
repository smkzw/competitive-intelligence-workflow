import json
import runpy
from pathlib import Path

import httpx
import pytest

from ciw2.harness.llm import OpenAICompatLLM


@pytest.fixture
def smoke():
    return runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/smoke_model.py'))


@pytest.mark.parametrize('status', [200, 429])
def test_model_probe_uses_mock_transport_and_safe_isolated_receipt(settings, tmp_path, smoke, monkeypatch, status):
    client = OpenAICompatLLM('http://localhost:1', 'synthetic-private-key', 'glm-5.3-flash', max_retries=1)
    client._client.close()
    requests = []

    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(status, json={'model': 'glm-5.3-flash', 'choices': [
            {'message': {'tool_calls': [{'id': 'done', 'function': {'name': 'submit_result',
                'arguments': json.dumps({'report': 'C', 'findings': []})}}]}, 'finish_reason': 'tool_calls'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 10}})

    client._client = httpx.Client(transport=httpx.MockTransport(reply))
    fn = smoke['probe']
    monkeypatch.setitem(fn.__globals__, 'OpenAICompatLLM', lambda *args, **kwargs: client)
    task = {'verified_fact_ids': [], 'data': {'rows': []}}
    output = tmp_path / 'probe'
    result = fn(settings, task, output)
    assert len(requests) == 1
    assert 'read_project_fact' in {t['function']['name'] for t in requests[0]['tools']}
    assert result['executed_tool_calls'] == 0  # One transport probe, no fact/source execution.
    assert result['pipeline_acceptance'] == 'NOT_RUN'
    assert ('schema_valid' in result) == (status == 200)
    if status != 200:
        assert result['metadata']['http_status'] == 429
    assert 'synthetic-private-key' not in (output / 'receipt.json').read_text()
    with pytest.raises(FileExistsError):
        fn(settings, task, output)


def test_saved_task_recovers_only_matching_truncated_json_from_frozen_data(settings, smoke):
    from ciw2.pipeline.stages import _analysis_tasks, _compact
    from ciw2.render.portal import report_data
    from ciw2.service import Service

    svc = Service(settings)
    pid = svc.create_project('来源固定', ['C'])
    rid = svc.db.create_run(pid)
    tid, _ = svc.db.upsert_entity(pid, 'trial', 'NCT00000001')
    svc.db.add_fact({'project_id': pid, 'entity_id': tid, 'field': 'design.primary_endpoint',
        'value': {'measure': 'Long full endpoint definition ' * 700, 'time_frame': 'Week 16'},
        'tier': 'critical', 'status': 'verified', 'extracted_by': 'code:test'})
    core = _compact(report_data(svc.db, pid, 'C'))
    base = {'indication': '来源固定', 'focus': '', 'cutoff_date': None,
            'overview': {k: len(v) for k, v in core.items() if isinstance(v, list)}}
    task = _analysis_tasks(core, base, {f['id'] for f in svc.db.current_facts(pid)})[0]
    svc.db.log_step(rid, 'analysis_C', 'analysis-c', 0, 'task', task)
    raw = svc.db.one("SELECT content FROM agent_steps WHERE role='task'")['content']
    assert len(raw) == 20000
    before = svc.db.query('SELECT * FROM agent_steps')
    assert smoke['saved_task'](settings.db_path, rid) == task
    assert svc.db.query('SELECT * FROM agent_steps') == before
    svc.db.execute('UPDATE projects SET focus=? WHERE id=?', ('changed input', pid))
    with pytest.raises(ValueError, match='reconstruction differs'):
        smoke['saved_task'](settings.db_path, rid)


@pytest.mark.parametrize('corrupt', [False, True])
def test_saved_task_reads_verified_cas_pointer_without_replanning(settings, smoke, corrupt):
    from ciw2.harness.agent import run_skill
    from ciw2.harness.llm import LLMReply, ScriptedLLM, ToolCall
    from ciw2.service import Service

    svc = Service(settings)
    pid = svc.create_project('完整恢复', ['C'])
    rid = svc.db.create_run(pid)
    ctx = svc.context(pid, rid).tool_ctx()
    task = {'data': {'definition': '完整医学定义' * 5000}, 'verified_fact_ids': []}
    model = ScriptedLLM([LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'report': 'C', 'findings': []})])])
    run_skill(svc.skills['analysis-c'], task, model, svc.context(pid, rid).registry, ctx)
    pointer = json.loads(svc.db.one("SELECT content FROM agent_steps WHERE role='task'")['content'])
    if corrupt:
        svc.cas._path(pointer['digest']).write_bytes(b'simulated corruption')
        with pytest.raises(ValueError, match='hash mismatch'):
            smoke['saved_task'](settings.db_path, rid)
    else:
        assert smoke['saved_task'](settings.db_path, rid) == task
