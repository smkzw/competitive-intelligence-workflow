"""Production summary failures, precise lineage and useful partial publication."""
import copy
import json

import pytest
from test_analysis_budget import setup_analysis

from ciw2.harness.llm import LLMReply, ToolCall
from ciw2.pipeline import runner, stages


def reply(findings):
    return LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'report': 'C', 'findings': findings})])


def test_all_empty_qualified_batches_fail_on_production_entry(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=120)
    rc.llm.script = lambda _: reply([])
    with pytest.raises(ValueError, match='空|要点'):
        stages._analysis('C')(rc)
    assert not rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:batch:%'", (rc.run_id,))


def test_no_qualified_facts_can_legitimately_have_no_summary(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    monkeypatch.setattr(rc.db, 'current_facts', lambda _: [])
    rc.llm.script = lambda _: reply([])
    assert stages._analysis('C')(rc) == {'report': 'C', 'findings': []}


def test_invalid_batch_reference_is_not_silently_filtered(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    rc.llm.script = lambda _: reply([{'title': '观察', 'bullets': ['16周'], 'fact_refs': ['foreign']}])
    with pytest.raises(ValueError, match='引用'):
        stages._analysis('C')(rc)
    assert not rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:batch:%'", (rc.run_id,))


def test_rejected_layer_is_explicit_and_never_reusable_as_success(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']
    inputs = [{'title': f'先例{i}', 'bullets': ['x' * 5000], 'fact_refs': [fid]} for i in range(4)]
    def respond(messages):
        task = json.loads(messages[1]['content'])
        return reply(copy.deepcopy(task['data']['candidate_findings']))
    rc.llm.script = respond
    with pytest.raises(ValueError, match='收敛'):
        stages._analysis_merge(rc, 'C', inputs, {}, {fid})
    row = rc.db.one("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:merge_layer:%'", (rc.run_id,))
    value = json.loads(row['output_json'])
    assert row['status'] == 'failed' and value['accepted'] is False
    assert value['schema_version'] and value['code_sha256'] and value['skill_sha256']
    assert rc.db.stage_output(rc.run_id, row['name']) is None


def test_final_six_are_not_an_unbounded_narrative(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']
    inputs = [{'title': '先例', 'bullets': ['16周'], 'fact_refs': [fid]}]
    def expand(messages):
        task = json.loads(messages[1]['content'])
        return reply([{'title': '过长', 'bullets': ['长' * 9000], 'fact_refs': task['verified_fact_ids']}])
    rc.llm.script = expand
    with pytest.raises(ValueError, match='正文|预算'):
        stages._analysis_merge(rc, 'C', inputs, {}, {fid})
    assert not rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:synthesis:%'", (rc.run_id,))


def test_single_batch_cannot_bypass_final_narrative_budget(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    def expand(messages):
        task = json.loads(messages[1]['content'])
        return reply([{'title': '过长', 'bullets': ['长' * 9000], 'fact_refs': task['verified_fact_ids']}])
    rc.llm.script = expand
    with pytest.raises(ValueError, match='正文|预算'):
        stages._analysis('C')(rc)


def test_empty_final_summary_is_not_replayed_as_cached_success(settings, monkeypatch):
    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']
    original = rc.llm.script
    rc.llm.script = lambda _: reply([])
    inputs = [{'title': '先例', 'bullets': ['16周'], 'fact_refs': [fid]}]
    with pytest.raises(ValueError, match='空'):
        stages._analysis_merge(rc, 'C', inputs, {}, {fid})
    rc.llm.script = original
    assert stages._analysis_merge(rc, 'C', inputs, {}, {fid})['findings']
    assert len(calls) == 1


def test_distinct_sources_survive_multiple_layers_with_their_own_maps(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    inputs = [{'title': f'先例{i}', 'bullets': [f'研究{i} ' + 'x' * 3450],
               'fact_refs': [f'fct_{i:064x}', f'fct_{i+100:064x}']} for i in range(8)]
    refs = {r for f in inputs for r in f['fact_refs']}
    calls = []
    def combine(messages):
        task = json.loads(messages[1]['content']); calls.append(task)
        rows = task['data']['candidate_findings']
        return reply([{'title': '共同先例', 'bullets': [' / '.join(f['title'] for f in rows)],
                       'fact_refs': sorted({r for f in rows for r in f['fact_refs']})}])
    rc.llm.script = combine
    value = stages._analysis_merge(rc, 'C', inputs, {}, refs)
    assert len(calls) > 1 and set(value['findings'][0]['fact_refs']) == refs
    bases = rc.db.query("SELECT output_json FROM stages WHERE run_id=? AND name LIKE 'analysis_basis:%'", (rc.run_id,))
    assert len(bases) >= 2
    assert all(not r.startswith('summary_ref_') for f in value['findings'] for r in f['fact_refs'])


def test_summary_selection_records_omission_without_retracting_facts(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    inputs = [{'title': f'先例{i}', 'bullets': ['完整条件'], 'fact_refs': [f'fct_{i:064x}']} for i in range(2)]
    refs = {r for f in inputs for r in f['fact_refs']}
    before = copy.deepcopy(rc.db.current_facts(rc.project_id))
    def select(messages):
        task = json.loads(messages[1]['content'])
        return reply([task['data']['candidate_findings'][0]])
    rc.llm.script = select
    result = stages._analysis_merge(rc, 'C', inputs, {}, refs)
    rows = rc.db.query("SELECT output_json FROM stages WHERE run_id=? AND name LIKE 'analysis_selection:%'", (rc.run_id,))
    assert rows
    selection = json.loads(rows[-1]['output_json'])
    assert set(selection['selected_fact_ids']) == set(result['findings'][0]['fact_refs'])
    assert set(selection['omitted_fact_ids']) == refs - set(result['findings'][0]['fact_refs'])
    assert selection['scope'] == 'NARRATIVE_SELECTION_NOT_FACT_RETRACTION'
    assert rc.db.current_facts(rc.project_id) == before


def test_one_short_reference_resolves_one_fact_not_a_whole_parent(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    inputs = [{'title': '两个独立观察', 'bullets': ['年龄18岁', '16周访视'],
               'fact_refs': ['fct_age', 'fct_visit']}]
    def choose_one(messages):
        task = json.loads(messages[1]['content'])
        return reply([{'title': '年龄', 'bullets': ['年龄18岁'],
                       'fact_refs': task['data']['candidate_findings'][0]['fact_refs'][:1]}])
    rc.llm.script = choose_one
    result = stages._analysis_merge(rc, 'C', inputs, {}, {'fct_age', 'fct_visit'})
    assert result['findings'][0]['fact_refs'] == ['fct_age']


def test_same_task_in_a_new_run_does_not_relabel_old_model_cache(settings, monkeypatch):
    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']
    inputs = [{'title': '先例', 'bullets': ['16周'], 'fact_refs': [fid]}]
    stages._analysis_merge(rc, 'C', inputs, {}, {fid})
    stages._analysis_merge(rc, 'C', inputs, {}, {fid})
    assert len(calls) == 1
    rc.run_id = rc.db.create_run(rc.project_id)
    stages._analysis_merge(rc, 'C', inputs, {}, {fid})
    assert len(calls) == 2


def test_failed_summary_produces_actual_usable_html_without_false_success(settings, monkeypatch):
    from ciw2.render.portal import report_data
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    monkeypatch.setattr('ciw2.render.portal.report_data', report_data)
    rc.llm.script = lambda _: reply([])
    monkeypatch.setattr(runner, 'STAGES', [stages.Stage('analysis_C', stages._analysis('C'), blocking=False),
                                        stages.Stage('render', stages.render)])
    assert runner.execute(rc) == 'failed'
    html = (rc.settings.portals_dir / rc.project_id / 'C.html').read_text()
    assert 'EASI-75' in html and '<table' in html and 'echarts' in html
    assert rc.db.one('SELECT status FROM runs WHERE id=?', (rc.run_id,))['status'] == 'failed'
    assert rc.db.stage_output(rc.run_id, 'render') == {'files': ['C.html']}
