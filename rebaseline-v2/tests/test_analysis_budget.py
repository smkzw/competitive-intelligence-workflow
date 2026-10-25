import json

import pytest

from ciw2.harness.llm import LLMReply, ScriptedLLM, ToolCall
from ciw2.pipeline.stages import _analysis
from ciw2.service import Service


def setup_analysis(settings, monkeypatch, count=120, measure='EASI-75', focus='设计横比'):
    calls = []

    def respond(messages):
        task = json.loads(messages[1]['content'])
        calls.append(task)
        assert len(json.dumps(task, ensure_ascii=False)) <= 60000
        refs = task['verified_fact_ids']
        return LLMReply(tool_calls=[ToolCall('finish', 'submit_result', {'report': 'C', 'findings': [
            {'title': '设计先例', 'bullets': ['16周设计'], 'fact_refs': refs[:1]}]})])

    service = Service(settings, llm_factory=lambda s: (ScriptedLLM(respond), None))
    pid = service.create_project('设计先例', ['C'], focus=focus)
    rid = service.db.create_run(pid)
    tid, _ = service.db.upsert_entity(pid, 'trial', 'study')
    fid = service.db.add_fact({'project_id': pid, 'entity_id': tid, 'field': 'design.primary_endpoint',
        'value': {'measure': 'EASI-75', 'time_frame': 'Week 16'}, 'tier': 'critical', 'status': 'verified',
        'extracted_by': 'code:test'})
    rows = [{'trial': f'STUDY{i}', 'sample_size': i, 'sample_size_type': 'ACTUAL',
             'primary_endpoints': [{'measure': measure + ' protocol definition' * 25,
                                    'time_frame': 'Week 16', 'fact_id': fid, 'status': 'verified',
                                    'quote': 'raw source' * 2000}],
             'eligibility_criteria': 'Inclusion original unchanged' * 2000,
             'sources': {'sample_size': [{'fact_id': fid, 'status': 'verified',
                                          'value': 'raw source' * 2000, 'quote': 'raw source' * 2000}]}}
            for i in range(count)]
    data = {'rows': rows, 'endpoint_groups': [{'entries': rows}], 'charts': {}}
    monkeypatch.setattr('ciw2.render.portal.report_data', lambda *args: data)
    return service.context(pid, rid), calls, data


def test_analysis_batches_complete_records_without_truncating_report(settings, monkeypatch):
    rc, calls, data = setup_analysis(settings, monkeypatch)
    before = json.dumps(data, ensure_ascii=False)
    result = _analysis('C')(rc)
    assert result['findings']
    batch_calls = [c for c in calls if c.get('mode') == 'batch']
    assert len(batch_calls) > 1
    records = [row for c in batch_calls for row in c['data']['rows']]
    assert [r['trial'] for r in records] == [r['trial'] for r in data['rows']]
    assert all(c['overview']['rows'] == 120 for c in batch_calls)
    assert all(r['primary_endpoints'][0]['measure'] == data['rows'][0]['primary_endpoints'][0]['measure']
               for r in records)
    assert calls[-1]['mode'] == 'synthesis'
    assert json.dumps(data, ensure_ascii=False) == before


def test_single_essential_record_over_budget_fails_before_model(settings, monkeypatch):
    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1, measure='完整临床定义' * 20000)
    with pytest.raises(ValueError, match='摘要输入'):
        _analysis('C')(rc)
    assert calls == []


def test_task_metadata_also_counts_toward_model_budget(settings, monkeypatch):
    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1, focus='临床关注点' * 20000)
    with pytest.raises(ValueError, match='摘要输入'):
        _analysis('C')(rc)
    assert calls == []


def test_unchanged_completed_batch_is_reused_after_later_failure(settings, monkeypatch):
    from ciw2.harness.llm import LLMError

    rc, calls, _ = setup_analysis(settings, monkeypatch)
    original = rc.llm.script
    attempts = {'n': 0}

    def flaky(messages):
        attempts['n'] += 1
        if attempts['n'] == 2:
            raise LLMError('temporary later-batch failure')
        return original(messages)

    rc.llm.script = flaky
    with pytest.raises(LLMError):
        _analysis('C')(rc)
    saved = rc.db.query("SELECT finished_at FROM stages WHERE run_id=? AND status='succeeded'", (rc.run_id,))
    assert saved and all(row['finished_at'] for row in saved)
    first = calls[0]['data']
    rc.llm.script = original
    _analysis('C')(rc)
    assert sum(c['data'] == first for c in calls) == 1


def test_wrong_report_result_is_not_cached_or_adopted(settings, monkeypatch):
    rc, _calls, _ = setup_analysis(settings, monkeypatch, count=1)
    rc.llm.script = lambda messages: LLMReply(tool_calls=[ToolCall('finish', 'submit_result', {
        'report': 'B', 'findings': []})])
    with pytest.raises(ValueError, match='报告类型'):
        _analysis('C')(rc)
    assert rc.db.query('SELECT * FROM stages WHERE run_id=?', (rc.run_id,)) == []


def test_skill_change_invalidates_previous_batch_result(settings, monkeypatch):
    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1)
    _analysis('C')(rc)
    rc.skills['analysis-c'].body += '\nNew summary rule.'
    _analysis('C')(rc)
    assert len(calls) == 2


def test_large_synthesis_is_reduced_without_oversized_model_call(settings, monkeypatch):
    from ciw2.pipeline.stages import _analysis_merge

    rc, calls, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']
    findings = [{'title': f'先例{i}', 'bullets': ['完整设计观察' * 250], 'fact_refs': [fid]} for i in range(100)]
    result = _analysis_merge(rc, 'C', findings, {'overview': {'rows': 100}}, {fid})
    assert result['report'] == 'C' and result['findings']
    assert len(calls) > 1 and all(c['mode'] == 'synthesis' for c in calls)


def test_synthesis_uses_smaller_complete_packets_not_the_raw_research_budget(settings, monkeypatch):
    from ciw2.pipeline.stages import _analysis_merge

    rc,calls,_=setup_analysis(settings,monkeypatch,count=1)
    fid=rc.db.current_facts(rc.project_id)[0]['id']
    findings=[{'title':f'原始先例{i}', 'bullets':['原始设计观察及完整时间人群条件 '*40],
               'fact_refs':[fid]} for i in range(20)]
    before=json.dumps(findings,ensure_ascii=False)
    result=_analysis_merge(rc,'C',findings,{'overview':{'rows':284}}, {fid})
    assert result['findings'] and len(calls)>1
    assert all(len(json.dumps(t,ensure_ascii=False))<=8000 for t in calls)
    originals=[f for t in calls for f in t['data']['candidate_findings'] if f['title'].startswith('原始先例')]
    basis=json.loads(rc.db.query("SELECT content FROM agent_steps WHERE role='synthesis_basis' ORDER BY id")[0]['content'])
    if 'basis_stage' in basis:basis=rc.db.stage_output(rc.run_id,basis['basis_stage'])
    resolved=[{**f,'fact_refs':list(dict.fromkeys(r for key in f['fact_refs'] for r in basis['reference_map'][key]))}
              for f in originals]
    assert resolved==findings  # Complete clinical text and source refs, only transport IDs are shortened.
    assert all(t['overview']['rows']==284 for t in calls)
    assert json.dumps(findings,ensure_ascii=False)==before


def test_synthesis_partial_failure_reuses_completed_packets_without_research(settings, monkeypatch):
    from ciw2.harness.llm import LLMError
    from ciw2.pipeline.stages import _analysis_merge

    rc,calls,_=setup_analysis(settings,monkeypatch,count=1)
    fid=rc.db.current_facts(rc.project_id)[0]['id']
    findings=[{'title':f'原始先例{i}', 'bullets':['完整设计观察 '*200], 'fact_refs':[fid]} for i in range(30)]
    original=rc.llm.script
    attempts=[]
    def fail_second(messages):
        attempts.append(json.loads(messages[1]['content']))
        if len(attempts)==2:
            raise LLMError('one failed synthesis unit')
        return original(messages)
    rc.llm.script=fail_second
    with pytest.raises(LLMError):
        _analysis_merge(rc,'C',findings,{}, {fid})
    first=attempts[0]
    rc.llm.script=original
    result=_analysis_merge(rc,'C',findings,{}, {fid})
    assert result['findings'] and sum(t==first for t in calls)==1
    assert all(t['mode']=='synthesis' for t in calls)
    assert all(len(json.dumps(t,ensure_ascii=False))<=8000 for t in calls)


def test_one_indivisible_synthesis_finding_is_not_truncated_to_fit(settings, monkeypatch):
    from ciw2.pipeline.stages import _analysis_merge

    rc,calls,_=setup_analysis(settings,monkeypatch,count=1)
    fid=rc.db.current_facts(rc.project_id)[0]['id']
    finding={'title':'完整先例', 'bullets':['完整医学定义及上下文 '*1200], 'fact_refs':[fid]}
    with pytest.raises(ValueError,match='摘要输入'):
        _analysis_merge(rc,'C',[finding],{}, {fid})
    assert not calls


def test_intermediate_summary_limit_is_checked_before_caching(settings,monkeypatch):
    from ciw2.pipeline.stages import _analysis_call

    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid=rc.db.current_facts(rc.project_id)[0]['id']
    rc.llm.script=lambda messages: LLMReply(tool_calls=[ToolCall('finish','submit_result',{
        'report':'C','findings':[{'title':f'要点{i}','bullets':['有依据'],'fact_refs':[fid]} for i in range(3)]})])
    task={'mode':'synthesis','finding_limit':2,'data':{'candidate_findings':[]},'verified_fact_ids':[fid]}
    with pytest.raises(ValueError,match='摘要条数'):
        _analysis_call(rc,'C',task)
    assert not rc.db.query('SELECT * FROM stages WHERE run_id=?',(rc.run_id,))


def test_result_and_safety_contexts_survive_summary_projection():
    from ciw2.pipeline.stages import _analysis_tasks, _compact

    result = {'id': 'fct_result', 'value': -1.5, 'endpoint': 'Scale change', 'timepoint': 'Baseline to Week 24',
              'population': 'Safety population', 'arm': 'Arm A', 'unit': 'points', 'stat_type': 'mean_change',
              'denominator': 60, 'status': 'verified'}
    safety = {'id': 'fct_safety', 'value': None, 'denominator': 0, 'proportion': None,
              'timepoint': 'Week 24', 'endpoint': 'Non-serious treatment-emergent adverse events', 'status': 'unknown'}
    core = _compact({'results': [result], 'safety': [safety], 'analyses': [], 'charts': {}})
    packets = _analysis_tasks(core, {'overview': {'results': 1, 'safety': 1}}, {'fct_result'})
    assert packets[0]['data']['results'] == [result]
    assert packets[0]['data']['safety'] == [safety]
    assert packets[0]['verified_fact_ids'] == ['fct_result']


def test_criterion_logic_and_value_are_not_stripped_with_duplicate_evidence():
    from ciw2.pipeline.stages import _compact

    criterion = {'fact_id': 'fct_criterion', 'section': 'exclusion', 'measure': 'BSA',
                 'operator': '>', 'value': 80, 'unit': '%', 'rule_text': 'BSA > 80% OR active infection'}
    assert _compact({'eligibility_thresholds': [criterion]})['eligibility_thresholds'] == [criterion]


def test_summary_keeps_complete_endpoint_but_not_duplicate_source_transport_metadata():
    from ciw2.pipeline.stages import _compact

    endpoint = {'fact_id': 'fct_endpoint', 'measure': 'Complete endpoint', 'description': 'Full definition',
                'time_frame': 'Week 24', 'population': 'ITT', 'status': 'verified',
                'source_id': 'src_original', 'url': 'https://example.org/long-source', 'locator': 'path[0]'}
    projected = _compact(endpoint)
    assert projected == {k: v for k, v in endpoint.items() if k not in {'source_id', 'url', 'locator'}}


def test_summary_uses_smaller_complete_record_batches_after_actual_large_input_timeout(settings, monkeypatch):
    from ciw2.pipeline.stages import ANALYSIS_TASK_CHARS

    assert ANALYSIS_TASK_CHARS == 24000
    rc, calls, data = setup_analysis(settings, monkeypatch, count=80)
    _analysis('C')(rc)
    assert all(len(json.dumps(task, ensure_ascii=False)) <= 24000 for task in calls)
    assert [r['trial'] for task in calls if task['mode'] == 'batch' for r in task['data']['rows']] == [
        r['trial'] for r in data['rows']]


def test_large_design_study_partitions_whole_endpoints_with_shared_context():
    from ciw2.pipeline.stages import _analysis_tasks

    endpoints = [{'fact_id': f'fct_{i}', 'measure': 'Scale', 'description': f'Definition {i} ' * 80,
                  'time_frame': 'Week 16', 'population': 'ITT', 'status': 'verified'} for i in range(90)]
    row = {'trial': 'NCT00000001', 'drugs': ['Test drug'], 'sample_size': 0,
           'sample_size_type': 'ACTUAL', 'arms': [{'label': 'A', 'description': 'Full schedule'}],
           'primary_endpoints': endpoints[:3], 'secondary_endpoints': endpoints[3:],
           'eligibility_thresholds': [{'rule_text': 'EASI >=16 OR IGA >=3', 'section': 'inclusion'}],
           'sources': {'secondary_endpoint': [{'fact_id': e['fact_id'], 'status': 'verified'} for e in endpoints[3:]],
                       'sample_size': [{'fact_id': 'fct_n', 'status': 'verified'}]}}
    before = json.dumps(row, sort_keys=True)
    tasks = _analysis_tasks({'rows': [row]}, {'overview': {'rows': 1}}, {e['fact_id'] for e in endpoints} | {'fct_n'})
    parts = [r for task in tasks for r in task['data']['rows']]
    assert len(parts) > 1
    assert all(len(json.dumps(task, ensure_ascii=False)) <= 24000 for task in tasks)
    assert [e for part in parts for e in part['primary_endpoints']] == endpoints[:3]
    assert [e for part in parts for e in part['secondary_endpoints']] == endpoints[3:]
    for i, part in enumerate(parts, 1):
        assert part['study_part'] == {'index': i, 'count': len(parts), 'primary_total': 3, 'secondary_total': 87}
        assert all(part[key] == row[key] for key in ('trial', 'drugs', 'sample_size', 'sample_size_type',
                                                    'arms', 'eligibility_thresholds'))
    assert set.union(*(set(task['verified_fact_ids']) for task in tasks)) == {e['fact_id'] for e in endpoints} | {'fct_n'}
    assert all(task['overview']['rows'] == 1 for task in tasks)
    assert json.dumps(row, sort_keys=True) == before


def test_design_partition_never_splits_one_definition_or_drops_unmatched_refs():
    from ciw2.pipeline.stages import _analysis_tasks

    row = {'trial': 'NCT00000001', 'primary_endpoints': [], 'secondary_endpoints': [
        {'fact_id': f'fct_{i}', 'description': 'Complete definition' * 600} for i in range(4)],
        'sources': {'secondary_endpoint': [{'fact_id': 'extra_ref', 'status': 'unknown'}]}}
    tasks = _analysis_tasks({'rows': [row]}, {}, {'fct_0', 'fct_1', 'fct_2', 'fct_3'})
    assert all(r['sources']['secondary_endpoint'] == row['sources']['secondary_endpoint']
               for task in tasks for r in task['data']['rows'])
    row['secondary_endpoints'][0]['description'] *= 4
    with pytest.raises(ValueError, match='摘要输入'):
        _analysis_tasks({'rows': [row]}, {}, {'fct_0'})
