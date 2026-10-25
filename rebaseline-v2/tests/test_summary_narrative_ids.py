"""Internal references belong in citations, never in the clinical narrative."""
import json

import pytest
from pydantic import ValidationError
from test_analysis_budget import setup_analysis

from ciw2.domain.models import AnalysisResult
from ciw2.harness.llm import LLMReply, ToolCall
from ciw2.pipeline.stages import _analysis_merge


@pytest.mark.parametrize('token', ['fct_1fae087f089d', 'summary_ref_14'])
@pytest.mark.parametrize('place', ['title', 'bullet'])
def test_internal_fact_reference_rejected_in_narrative(token, place):
    f = {'title': '试验设计', 'bullets': ['第16周'], 'fact_refs': ['fct_1fae087f089d']}
    if place == 'title':
        f['title'] += token
    else:
        f['bullets'].append('对应观察（' + token + '）')
    with pytest.raises(ValidationError, match='内部'):
        AnalysisResult.model_validate({'report': 'C', 'findings': [f]})


def test_registry_codes_and_reference_fields_remain_valid():
    obj = AnalysisResult.model_validate({'report': 'C', 'findings': [{
        'title': '611的研究设计', 'bullets': ['NCT07767253；CTR20253975；EASI-75'],
        'fact_refs': ['fct_1fae087f089d', 'summary_ref_14']}]})
    assert obj.findings[0].fact_refs == ['fct_1fae087f089d', 'summary_ref_14']


def test_narrative_identifier_can_be_corrected_inside_existing_submission_budget(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']

    def reply(messages):
        task = json.loads(messages[1]['content'])
        errors = [m for m in messages if m['role'] == 'tool' and '内部' in m['content']]
        return LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'report': 'C', 'findings': [{
            'title': '设计先例', 'bullets': ['16周' if errors else '对应fct_1fae087f089d'],
            'fact_refs': task['verified_fact_ids']} ]})])

    rc.llm.script = reply
    result = _analysis_merge(rc, 'C', [{'title': '来源要点', 'bullets': ['16周'], 'fact_refs': [fid]}], {}, {fid})
    assert result['findings'][0]['bullets'] == ['16周']
    assert len(rc.llm.calls) == 2


def test_cached_internal_identifier_is_rejected_without_another_model_call(settings, monkeypatch):
    from ciw2.pipeline.stages import _analysis

    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1)
    _analysis('C')(rc)
    row = rc.db.one("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:batch:%'", (rc.run_id,))
    bad = json.loads(row['output_json'])
    bad['findings'][0]['bullets'] = ['对应summary_ref_9']
    rc.db.set_stage(rc.run_id, row['name'], 'succeeded', output=bad)
    with pytest.raises(ValidationError, match='内部'):
        _analysis('C')(rc)
    assert len(calls) == 1
