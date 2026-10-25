"""Short narrative packets can still expand to an unbounded set of full fact reads."""
import copy
import json

import pytest
from test_analysis_budget import setup_analysis

from ciw2.harness.llm import LLMError, LLMReply, ToolCall
from ciw2.pipeline import stages


def evidence_setup(settings,monkeypatch,*,count=18,quote_chars=4500):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    entity=rc.db.current_facts(rc.project_id)[0]['entity_id'];inputs=[];calls=[]
    for i in range(count):
        fid=rc.db.add_fact({'project_id':rc.project_id,'entity_id':entity,'field':'design.sample_size',
                           'value':100+i,'quote':'source-text '+('q'*quote_chars),'tier':'critical',
                           'status':'verified','extracted_by':'code:test'})
        inputs.append({'title':f'原观察{i}','bullets':[f'第{i}个完整设计观察'],'fact_refs':[fid]})
    verified={f['fact_refs'][0] for f in inputs}
    def respond(messages):
        task=json.loads(messages[1]['content']);calls.append(task)
        row=task['data']['candidate_findings'][0]
        return LLMReply(tool_calls=[ToolCall('done','submit_result',{'report':'C','findings':[
            {'title':'设计要点','bullets':['有完整事实支持的观察'],'fact_refs':row['fact_refs']} ]})])
    rc.llm.script=respond
    return rc,inputs,verified,calls,respond


def test_short_narrative_with_many_long_sources_is_split_before_production_model_call(settings,monkeypatch):
    rc,inputs,verified,calls,_=evidence_setup(settings,monkeypatch)
    before=copy.deepcopy(inputs);facts=rc.db.current_facts(rc.project_id)
    result=stages._analysis_merge(rc,'C',inputs,{},verified)
    assert result['findings'] and len(calls)>1
    first=[r for t in calls for r in t['data']['candidate_findings'] if r['title'].startswith('原观察')]
    assert [r['title'] for r in first]==[r['title'] for r in inputs]
    assert all(len(json.dumps(t,ensure_ascii=False))<=stages.SYNTHESIS_TASK_CHARS for t in calls)
    assert inputs==before and rc.db.current_facts(rc.project_id)==facts


def test_unfinished_evidence_packets_resume_without_repeating_completed_children(settings,monkeypatch):
    rc,inputs,verified,calls,respond=evidence_setup(settings,monkeypatch)
    attempts=0
    def interrupted(messages):
        nonlocal attempts
        attempts+=1
        if attempts==2:raise LLMError('later evidence packet unavailable')
        return respond(messages)
    rc.llm.script=interrupted
    with pytest.raises(LLMError):stages._analysis_merge(rc,'C',inputs,{},verified)
    completed=copy.deepcopy(calls)
    rc.llm.script=respond
    assert stages._analysis_merge(rc,'C',inputs,{},verified)['findings']
    assert completed and all(sum(t==other for other in calls)==1 for t in completed)


def test_indivisible_source_over_hard_limit_fails_without_truncation_or_model(settings,monkeypatch):
    rc,inputs,verified,calls,_=evidence_setup(settings,monkeypatch,count=1,quote_chars=100000)
    before=rc.db.current_facts(rc.project_id)
    with pytest.raises(ValueError,match='证据|上下文'):stages._analysis_merge(rc,'C',inputs,{},verified)
    assert not calls and rc.db.current_facts(rc.project_id)==before
    assert not rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:synthesis:%'",(rc.run_id,))


def test_complete_single_record_above_target_but_under_hard_limit_is_not_trimmed(settings,monkeypatch):
    rc,inputs,verified,calls,_=evidence_setup(settings,monkeypatch,count=1,quote_chars=30000)
    before=rc.db.current_facts(rc.project_id)
    assert stages._analysis_merge(rc,'C',inputs,{},verified)['findings']
    assert len(calls)==1 and calls[0]['data']['candidate_findings'][0]['bullets']==inputs[0]['bullets']
    assert rc.db.current_facts(rc.project_id)==before


def test_qualified_cached_parent_keeps_original_task_instead_of_repartitioning(settings,monkeypatch):
    from ciw2.pipeline import summary_budget
    rc,inputs,verified,_,_=evidence_setup(settings,monkeypatch)
    projected,refs,basis=stages._summary_basis(rc,inputs,verified)
    task={'data':{'candidate_findings':projected},'verified_fact_ids':sorted(refs),
          'finding_basis_sha256':basis,'mode':'synthesis','finding_limit':6}
    costs=summary_budget.read_costs(rc,refs);before=copy.deepcopy(task)
    assert summary_budget.context_chars(task,costs)>summary_budget.MAX_CONTEXT_CHARS
    cached=summary_budget.packets([task],costs,lambda candidate:True)
    pending=summary_budget.packets([task],costs,lambda candidate:False)
    assert len(cached)==1 and cached[0]['data']==task['data']
    assert len(pending)>1 and [r for t in pending for r in t['data']['candidate_findings']]==projected
    assert all(summary_budget.context_chars(t,costs)<=summary_budget.MAX_CONTEXT_CHARS for t in pending)
    assert task==before
