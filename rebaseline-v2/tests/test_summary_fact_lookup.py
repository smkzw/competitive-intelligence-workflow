"""Opaque synthesis aliases must remain resolvable through the existing fact tool."""
import json

from test_analysis_budget import setup_analysis

from ciw2.harness.llm import LLMReply, ToolCall
from ciw2.harness.tools import REGISTRY
from ciw2.pipeline.stages import _analysis_merge


def test_reducer_can_identify_fact_meaning_instead_of_guessing_alias_position(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    trial = rc.db.current_facts(rc.project_id)[0]['entity_id']
    fields = [('design.eligibility_age', {'min': '18 Years', 'max': '65 Years'}),
              ('design.primary_endpoint', {'measure': 'EASI-75', 'time_frame': 'Week 16'})]
    ids = [rc.db.add_fact({'project_id': rc.project_id, 'entity_id': trial, 'field': field,
                          'value': value, 'tier': 'critical', 'status': 'verified',
                          'extracted_by': 'code:test'}) for field, value in fields]
    seen = []
    def respond(messages):
        task = json.loads(messages[1]['content'])
        outputs = [json.loads(m['content']) for m in messages if m['role'] == 'tool']
        if not outputs:
            return LLMReply(tool_calls=[ToolCall(str(i), 'read_project_fact', {'fact_id': alias})
                                        for i, alias in enumerate(task['verified_fact_ids'])])
        seen.extend(outputs)
        age = next(o for o in outputs if o['fact']['field'] == 'design.eligibility_age')
        return LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'report': 'C', 'findings': [
            {'title': '成人设计先例', 'bullets': ['18至65岁'], 'fact_refs': [age['requested_ref']]}]})])
    rc.llm.script = respond
    findings = [{'title': '人群与终点', 'bullets': ['18至65岁；16周EASI-75'], 'fact_refs': ids[::-1]}]
    result = _analysis_merge(rc, 'C', findings, {}, set(ids))
    assert result['findings'][0]['fact_refs'] == [ids[0]]
    assert {o['fact']['id'] for o in seen} == set(ids)
    assert all(o['status'] == 'ok' and o['fact']['value'] for o in seen)
    assert not rc.db.query('SELECT * FROM sources WHERE project_id=?', (rc.project_id,))


def test_alias_outside_this_task_and_stale_alias_from_another_call_are_rejected(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']
    outputs = []
    def respond(messages):
        task = json.loads(messages[1]['content'])
        if not any(m['role'] == 'tool' for m in messages):
            return LLMReply(tool_calls=[ToolCall('outside', 'read_project_fact', {'fact_id': 'summary_ref_9999'})])
        outputs.extend(json.loads(m['content']) for m in messages if m['role'] == 'tool')
        return LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'report': 'C', 'findings': [
            {'title': '设计先例', 'bullets': ['16周'], 'fact_refs': task['verified_fact_ids']} ]})])
    rc.llm.script = respond
    _analysis_merge(rc, 'C', [{'title': '先例', 'bullets': ['16周'], 'fact_refs': [fid]}], {}, {fid})
    assert outputs[0]['status'] == 'tool_failed'
    tool = REGISTRY.get('read_project_fact')
    stale = json.loads(tool.run(rc.tool_ctx(), {'fact_id': 'summary_ref_0'}))
    assert stale['status'] == 'tool_failed'
    ordinary = json.loads(tool.run(rc.tool_ctx(), {'fact_id': fid}))
    assert ordinary['fact']['id'] == fid  # Existing direct-ID callers remain supported.
