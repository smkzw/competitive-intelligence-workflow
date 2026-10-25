"""Contentless structured success and explicit non-convergence recovery policy."""
import copy
import json

import pytest
from test_analysis_budget import setup_analysis

from ciw2.harness.llm import LLMReply, ToolCall
from ciw2.pipeline.stages import _analysis, _analysis_merge


@pytest.mark.parametrize(('title', 'bullets'), [('', []), ('   ', ['有效观察']), ('先例', []), ('先例', ['  '])])
def test_contentless_finding_is_rejected_before_caching(settings, monkeypatch, title, bullets):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    def reply(messages):
        task = json.loads(messages[1]['content'])
        return LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'report': 'C', 'findings': [
            {'title': title, 'bullets': bullets, 'fact_refs': task['verified_fact_ids']} ]})])
    rc.llm.script = reply
    with pytest.raises(ValueError, match='正文|内容'):
        _analysis('C')(rc)
    assert not rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:batch:%'", (rc.run_id,))


def test_cached_content_is_revalidated_at_acceptance_boundary(settings, monkeypatch):
    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1)
    _analysis('C')(rc)
    row = rc.db.one("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:batch:%'", (rc.run_id,))
    bad = json.loads(row['output_json']); bad['findings'][0]['bullets'] = []
    rc.db.set_stage(rc.run_id, row['name'], 'succeeded', output=bad)
    with pytest.raises(ValueError, match='正文|内容'):
        _analysis('C')(rc)
    assert len(calls) == 1


def test_rejected_layer_does_not_promise_identical_resume_will_repair_it(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']; calls = []
    inputs = [{'title': f'先例{i}', 'bullets': ['x' * 5000], 'fact_refs': [fid]} for i in range(4)]
    def reply(messages):
        task = json.loads(messages[1]['content']); calls.append(task)
        values = copy.deepcopy(task['data']['candidate_findings'])
        return LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'report': 'C', 'findings': values})])
    rc.llm.script = reply
    for _ in range(2):
        with pytest.raises(ValueError, match='未收敛.*新归并运行'):
            _analysis_merge(rc, 'C', inputs, {}, {fid})
    assert len(calls) == 4  # No repeated model spend under an unchanged rejected strategy.
    rows = rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:merge_layer:%'", (rc.run_id,))
    assert len(rows) == 1 and rows[0]['status'] == 'failed'
