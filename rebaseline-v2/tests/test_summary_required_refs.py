"""Omitted citations must be corrected inside the existing bounded submit loop."""
import json
from dataclasses import replace

import pytest
from pydantic import ValidationError
from test_analysis_budget import setup_analysis

from ciw2.domain.models import AnalysisResult
from ciw2.harness.agent import AgentBudgetExceeded
from ciw2.harness.llm import LLMReply, ToolCall
from ciw2.pipeline.stages import _analysis_merge


@pytest.mark.parametrize('refs',[None,[]])
def test_summary_contract_requires_nonempty_references(refs):
    finding={'title':'观察','bullets':['16周']}
    if refs is not None:
        finding['fact_refs']=refs
    with pytest.raises(ValidationError,match='fact_refs'):
        AnalysisResult.model_validate({'report':'C','findings':[finding]})
    schema=AnalysisResult.model_json_schema()['$defs']['Finding']
    assert 'fact_refs' in schema['required'] and schema['properties']['fact_refs']['minItems']==1


def test_third_turn_omission_can_be_corrected_on_existing_fourth_turn(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    rc.settings=replace(rc.settings,max_agent_steps=4)
    fid=rc.db.current_facts(rc.project_id)[0]['id'];before=rc.db.raw_current_facts(rc.project_id)
    def respond(messages):
        turns=sum(m['role']=='assistant' for m in messages)
        task=json.loads(messages[1]['content'])
        if turns==0:
            return LLMReply(content='整理本次观察')
        if turns==1:
            return LLMReply(tool_calls=[ToolCall('read','read_project_fact',{'fact_id':task['verified_fact_ids'][0]})])
        finding={'title':'先例','bullets':['16周设计']}
        if turns==3:
            error=next(m['content'] for m in reversed(messages) if m['role']=='tool')
            assert 'fact_refs' in error and 'schema' in error
            finding['fact_refs']=task['verified_fact_ids'][:1]
        return LLMReply(tool_calls=[ToolCall('done','submit_result',{'report':'C','findings':[finding]})])
    rc.llm.script=respond
    result=_analysis_merge(rc,'C',[{'title':'原要点','bullets':['16周'],'fact_refs':[fid]}],{},{fid})
    assert result['findings'][0]['fact_refs']==[fid] and len(rc.llm.calls)==4
    assert rc.db.raw_current_facts(rc.project_id)==before
    assert len(rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:synthesis:%'",(rc.run_id,)))==1


def test_repeated_missing_references_exhaust_budget_without_false_success(settings,monkeypatch):
    rc,_,_=setup_analysis(settings,monkeypatch,count=1)
    rc.settings=replace(rc.settings,max_agent_steps=4);fid=rc.db.current_facts(rc.project_id)[0]['id']
    rc.llm.script=lambda _:LLMReply(tool_calls=[ToolCall('done','submit_result',{
        'report':'C','findings':[{'title':'无引用','bullets':['16周']} ]})])
    with pytest.raises(AgentBudgetExceeded):
        _analysis_merge(rc,'C',[{'title':'原要点','bullets':['16周'],'fact_refs':[fid]}],{},{fid})
    assert len(rc.llm.calls)==4
    assert not rc.db.query("SELECT * FROM stages WHERE run_id=? AND name LIKE 'analysis_C:synthesis:%'",(rc.run_id,))
