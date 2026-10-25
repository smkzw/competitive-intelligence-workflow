"""Root counterexamples: slightly shorter text is not a bounded reduction strategy."""
import copy
import json

import pytest
from test_analysis_budget import setup_analysis

from ciw2.harness.llm import LLMReply, ToolCall
from ciw2.pipeline.stages import _analysis_merge


def reducer(rc, *, items=8, length=3500, cut=1):
    fid=rc.db.current_facts(rc.project_id)[0]['id']
    inputs=[{'title':f'完整先例{i}','bullets':['x'*length],'fact_refs':[fid]} for i in range(items)]
    calls=[]
    def respond(messages):
        task=json.loads(messages[1]['content']);calls.append(task)
        assert len(calls)<=12, 'Repeated near-identical layers consumed unbounded calls'
        rows=copy.deepcopy(task['data']['candidate_findings'][:task.get('finding_limit',6)])
        for row in rows:row['bullets']=[row['bullets'][0][:-cut]]
        return LLMReply(tool_calls=[ToolCall('finish','submit_result',{'report':'C','findings':rows})])
    rc.llm.script=respond
    return fid,inputs,calls


def test_two_inputs_per_packet_really_reduce_count_and_keep_complete_first_level(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid,inputs,calls=reducer(rc)
    before=copy.deepcopy(inputs)
    result=_analysis_merge(rc,'C',inputs,{}, {fid})
    assert result['findings'] and len(calls)<=8
    assert all(t.get('finding_limit')==1 for t in calls[:-1])
    first=[]
    for task in calls:
        if all(r['bullets']==['x'*3500] for r in task['data']['candidate_findings']):
            first.extend(task['data']['candidate_findings'])
    basis=json.loads(rc.db.query("SELECT content FROM agent_steps WHERE role='synthesis_basis' ORDER BY id")[0]['content'])
    if 'basis_stage' in basis:basis=rc.db.stage_output(rc.run_id,basis['basis_stage'])
    restored=[{**f,'fact_refs':[r for key in f['fact_refs'] for r in basis['reference_map'][key]]} for f in first]
    assert restored==inputs and inputs==before
    assert all(len(json.dumps(t,ensure_ascii=False))<=8000 for t in calls)


def test_same_count_tiny_text_reduction_stops_after_one_complete_layer(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid,inputs,calls=reducer(rc,items=4,length=5000)
    with pytest.raises(ValueError,match='归并未收敛'):
        _analysis_merge(rc,'C',inputs,{}, {fid})
    assert len(calls)==4
    assert len(rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:synthesis:%'",(rc.run_id,)))==4
    checkpoint=rc.db.query("SELECT output_json FROM stages WHERE name LIKE 'analysis_C:merge_layer:%'")
    assert len(checkpoint)==1 and json.loads(checkpoint[0]['output_json'])['scope']=='INTERMEDIATE_NOT_FINAL_REPORT'


def test_singleton_packets_can_compact_substantially_then_merge(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid,inputs,calls=reducer(rc,items=4,length=5000,cut=4000)
    result=_analysis_merge(rc,'C',inputs,{}, {fid})
    assert result['findings'] and len(calls)==5
    assert len(calls[0]['data']['candidate_findings'])==1


@pytest.mark.parametrize('length',[5,3500])
def test_unqualified_input_refs_fail_identically_before_any_packet(settings,monkeypatch,length):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    _,inputs,calls=reducer(rc,length=length)
    with pytest.raises(ValueError,match='引用'):
        _analysis_merge(rc,'C',inputs,{},set())
    assert not calls


def test_nonempty_summary_layer_cannot_silently_become_empty(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid,inputs,_=reducer(rc)
    rc.llm.script=lambda messages:LLMReply(tool_calls=[ToolCall('finish','submit_result',{'report':'C','findings':[]})])
    with pytest.raises(ValueError,match='空'):
        _analysis_merge(rc,'C',inputs,{}, {fid})


def test_full_real_length_reference_ids_do_not_prevent_a_small_narrative_from_merging(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    inputs=[{'title':f'观察{i}','bullets':[f'原始条件{i}'],
             'fact_refs':['fct_'+format(n,'064x') for n in range(i*20,(i+1)*20)]} for i in range(8)]
    verified={r for f in inputs for r in f['fact_refs']};before=copy.deepcopy(inputs);calls=[]
    def combine(messages):
        task=json.loads(messages[1]['content']);calls.append(task)
        children=task['data']['candidate_findings']
        return LLMReply(tool_calls=[ToolCall('finish','submit_result',{'report':'C','findings':[
            {'title':'归并观察','bullets':[b for f in children for b in f['bullets']],
             'fact_refs':list(dict.fromkeys(r for f in children for r in f['fact_refs']))}]})])
    rc.llm.script=combine
    result=_analysis_merge(rc,'C',inputs,{},verified)
    assert len(calls)==1 and len(json.dumps(calls[0],ensure_ascii=False))<=8000
    assert set(result['findings'][0]['fact_refs'])==verified
    assert result['findings'][0]['bullets']==[f'原始条件{i}' for i in range(8)] and inputs==before


def test_same_text_with_changed_fact_identity_cannot_reuse_a_different_reference_map(settings,monkeypatch):
    rc,calls,_=setup_analysis(settings,monkeypatch,count=1)
    first=[{'title':'同一句话','bullets':['同一临床条件'],'fact_refs':['fct_'+'a'*64]}]
    second=[{**first[0],'fact_refs':['fct_'+'b'*64]}]
    verified=set(first[0]['fact_refs']+second[0]['fact_refs'])
    a=_analysis_merge(rc,'C',first,{},verified);b=_analysis_merge(rc,'C',second,{},verified)
    assert len(calls)==2 and a['findings'][0]['fact_refs']==first[0]['fact_refs']
    assert b['findings'][0]['fact_refs']==second[0]['fact_refs']


def test_failed_summary_keeps_useful_render_but_not_a_successful_run(settings,monkeypatch):
    from ciw2.pipeline import runner
    from ciw2.pipeline.stages import Stage
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    rendered=[]
    def fail(_):raise ValueError('摘要未收敛')
    monkeypatch.setattr(runner,'STAGES',[Stage('analysis_C',fail,blocking=False),
        Stage('render',lambda _:(rendered.append(True) or {'files':['C.html']}))])
    assert runner.execute(rc)=='failed' and rendered==[True]
    assert rc.db.one('SELECT status FROM runs WHERE id=?',(rc.run_id,))['status']=='failed'


def test_falling_count_but_negligible_text_reduction_stops_at_first_layer(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid,inputs,_=reducer(rc,items=20,length=5000)
    calls=[]
    def slow(messages):
        task=json.loads(messages[1]['content']);calls.append(task)
        assert len(calls)<=20, 'Linear-drain reduction did not stop at layer boundary'
        rows=copy.deepcopy(task['data']['candidate_findings']) if len(calls)>1 else []
        for row in rows:row['bullets']=[row['bullets'][0][:-1]]
        return LLMReply(tool_calls=[ToolCall('finish','submit_result',{'report':'C','findings':rows})])
    rc.llm.script=slow
    with pytest.raises(ValueError,match='归并未收敛'):_analysis_merge(rc,'C',inputs,{}, {fid})
    assert len(calls)==20


def test_resume_later_layer_uses_all_completed_first_layer_calls_once(settings,monkeypatch):
    from ciw2.harness.llm import LLMError
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid,inputs,calls=reducer(rc)
    original=rc.llm.script;attempts=0
    def flaky(messages):
        nonlocal attempts
        attempts+=1
        if attempts==5:raise LLMError('second layer interrupted')
        return original(messages)
    rc.llm.script=flaky
    with pytest.raises(LLMError):_analysis_merge(rc,'C',inputs,{}, {fid})
    assert len(calls)==4
    first=copy.deepcopy(calls)
    rc.llm.script=original
    result=_analysis_merge(rc,'C',inputs,{}, {fid})
    assert result['findings'] and len(calls)==7
    assert all(sum(task==other for other in calls)==1 for task in first)


def test_unknown_short_reference_is_rejected_without_caching_or_silent_deletion(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    fid,inputs,_=reducer(rc,items=1,length=10)
    rc.llm.script=lambda messages:LLMReply(tool_calls=[ToolCall('finish','submit_result',{
        'report':'C','findings':[{'title':'错误引用','bullets':['原观察'],'fact_refs':['not-in-this-input']} ]})])
    with pytest.raises(ValueError,match='引用'):_analysis_merge(rc,'C',inputs,{}, {fid})
    assert not rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:synthesis:%'",(rc.run_id,))


def test_large_reference_lineage_is_valid_and_survives_existing_backup_restore(settings,monkeypatch,tmp_path):
    from ciw2.pipeline.stages import _summary_basis
    from ciw2.store.backup import create_backup, restore_backup
    from ciw2.store.db import DB
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    inputs=[{'title':f'观察{i}','bullets':['完整条件'],
        'fact_refs':['fct_'+format(n,'064x') for n in range(i*40,(i+1)*40)]} for i in range(100)]
    verified={r for f in inputs for r in f['fact_refs']}
    _,mapping,digest=_summary_basis(rc,inputs,verified)
    event=json.loads(rc.db.query("SELECT content FROM agent_steps WHERE role='synthesis_basis' ORDER BY id")[0]['content'])
    assert len(json.dumps(event))<20000
    basis=rc.db.stage_output(rc.run_id,event['basis_stage'])
    assert basis['reference_map']==mapping and basis['digest']==digest
    create_backup(rc.settings.data_dir,tmp_path/'backup')
    restore_backup(tmp_path/'backup',tmp_path/'restored')
    restored=DB(tmp_path/'restored/ciw2.sqlite3')
    assert restored.stage_output(rc.run_id,event['basis_stage'])==basis
