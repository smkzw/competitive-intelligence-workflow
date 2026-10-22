import pytest
from pydantic import BaseModel

from ciw2.domain.models import ScopeResult
from ciw2.harness.agent import AgentBudgetExceeded, run_skill
from ciw2.harness.llm import LLMReply, ScriptedLLM, ToolCall
from ciw2.harness.skills import SkillError, load_skills, parse_skill
from ciw2.harness.tools import ToolContext, ToolRegistry


class EchoArgs(BaseModel):
    text: str


def _registry():
    reg = ToolRegistry()

    @reg.register("echo", "回显", EchoArgs)
    def _echo(ctx, a):
        return {"echo": a.text}

    @reg.register("boom", "总是失败", EchoArgs)
    def _boom(ctx, a):
        raise RuntimeError("网络断了")

    return reg


SKILL = parse_skill("---\nname: t\ndescription: d\ntools: [echo, boom]\noutput: ScopeResult\nmax_steps: 5\n---\n正文")


def call(name, **args):
    return LLMReply(tool_calls=[ToolCall(id=name, name=name, arguments=args)])


def test_tool_then_invalid_then_valid_submit():
    llm = ScriptedLLM([
        call("echo", text="hi"),
        call("submit_result", decisions=[{"drug": "x"}]),                       # 缺字段
        call("submit_result", decisions=[{"drug": "x", "in_scope": True, "reason": "ok"}]),
    ])
    out = run_skill(SKILL, {"q": 1}, llm, _registry(), ToolContext())
    assert isinstance(out, ScopeResult) and out.decisions[0].in_scope is True
    tool_msgs = [m for m in llm.calls[-1] if m["role"] == "tool"]
    assert '"echo": "hi"' in tool_msgs[0]["content"]
    assert "不符合 schema" in tool_msgs[1]["content"]


def test_tool_failure_is_reported_not_hidden():
    llm = ScriptedLLM([call("boom", text="x"),
                       call("submit_result", decisions=[])])
    run_skill(SKILL, {}, llm, _registry(), ToolContext())
    assert "tool_failed" in next(m for m in llm.calls[-1] if m["role"] == "tool")["content"]


def test_non_whitelisted_tool_rejected():
    llm = ScriptedLLM([call("rm_rf", text="/"), call("submit_result", decisions=[])])
    run_skill(SKILL, {}, llm, _registry(), ToolContext())
    assert "不在本 Skill 白名单" in next(m for m in llm.calls[-1] if m["role"] == "tool")["content"]


def test_budget_exceeded():
    llm = ScriptedLLM(lambda msgs: call("echo", text="loop"))
    with pytest.raises(AgentBudgetExceeded):
        run_skill(SKILL, {}, llm, _registry(), ToolContext())


def test_skill_parsing_errors():
    with pytest.raises(SkillError):
        parse_skill("no frontmatter")
    with pytest.raises(SkillError):
        parse_skill("---\nname: x\ndescription: y\noutput: Nope\n---\n")


def test_repo_skills_load_and_tools_exist(settings):
    import ciw2.sources  # noqa: F401
    from ciw2.harness.tools import REGISTRY
    skills = load_skills(settings.skills_dir)
    assert {"intake", "universe-china", "universe-global", "coverage-review", "extract-results",
            "extract-design", "analysis-a", "analysis-b", "analysis-c"} <= set(skills)
    for s in skills.values():
        REGISTRY.subset(s.tools)
def test_harness_warns_before_budget_end_so_model_can_submit():
    def responder(messages):
        remaining = any(m['role'] == 'user' and '剩余 1 次' in m.get('content', '') for m in messages)
        if remaining:
            return call('submit_result', decisions=[])
        return call('echo', text='read')

    llm = ScriptedLLM(responder)
    result = run_skill(SKILL, {}, llm, _registry(), ToolContext(), max_steps=2)
    assert result.decisions == [] and len(llm.calls) == 2


def test_last_interaction_exposes_only_submission_not_more_research():
    class SubmitOnOnlyTool:
        model = 'test'

        def chat(self, messages, tools=None):
            names = [t['function']['name'] for t in tools]
            if names == ['submit_result']:
                return call('submit_result', decisions=[])
            return call('echo', text='more research')

    assert run_skill(SKILL, {}, SubmitOnOnlyTool(), _registry(), ToolContext(), max_steps=2).decisions == []


def test_failed_provider_response_is_recorded_without_being_a_valid_model_call(settings):
    from ciw2.harness.llm import LLMProtocolError
    from ciw2.store.db import DB

    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project('协议失败', ['C'])
    rid = db.create_run(pid)

    def unavailable(messages):
        raise LLMProtocolError('no usable response', {'actual_model': 'test', 'usage': {'completion_tokens': 10}})

    with pytest.raises(LLMProtocolError):
        run_skill(SKILL, {}, ScriptedLLM(unavailable), _registry(), ToolContext(db=db, run_id=rid))
    assert db.one("SELECT count(*) n FROM agent_steps WHERE run_id=? AND role='model'", (rid,))['n'] == 0
    row = db.one("SELECT content FROM agent_steps WHERE run_id=? AND role='model_error'", (rid,))
    assert row and 'completion_tokens' in row['content']


def test_no_research_tools_means_submit_is_required_from_first_interaction():
    no_tools = parse_skill('---\nname: summary\ndescription: d\ntools: []\noutput: ScopeResult\nmax_steps: 4\n---\n正文')
    calls = []

    class InspectTools:
        model = 'test'

        def chat(self, messages, tools=None):
            calls.append([tool['function']['name'] for tool in tools])
            return call('submit_result', decisions=[])

    assert run_skill(no_tools, {}, InspectTools(), _registry(), ToolContext()).decisions == []
    assert calls == [['submit_result']]


def test_reasoning_returned_to_provider_tool_loop_but_not_persisted_as_assistant_log(settings):
    import json

    from ciw2.store.db import DB

    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project('协议测试', ['C'])
    rid = db.create_run(pid)
    reasoning = 'synthetic-private-provider-reasoning'
    reply = call('echo', text='source')
    reply.raw = {'model': 'test', 'choices': [{'message': {'reasoning_content': reasoning}}]}
    llm = ScriptedLLM([reply, call('submit_result', decisions=[])])
    run_skill(SKILL, {}, llm, _registry(), ToolContext(db=db, run_id=rid))
    assistant = next(m for m in llm.calls[-1] if m['role'] == 'assistant')
    assert assistant['reasoning_content'] == reasoning
    logs = db.query('SELECT content FROM agent_steps')
    assert reasoning not in json.dumps(logs)


def test_harness_distinguishes_new_fact_extraction_from_existing_fact_summary():
    from ciw2.harness.agent import HARNESS_RULES

    assert '新抽取的事实' in HARNESS_RULES and '已有已核实事实' in HARNESS_RULES
    assert 'fact_refs' in HARNESS_RULES


def test_long_task_is_retained_in_cas_not_invalid_truncated_json(settings):
    import json

    from ciw2.store.cas import CAS
    from ciw2.store.db import DB

    settings.ensure_dirs()
    db, cas = DB(settings.db_path), CAS(settings.cas_dir)
    pid = db.create_project('完整输入', ['C'])
    rid = db.create_run(pid)
    skill = parse_skill('---\nname: summary\ndescription: d\ntools: []\noutput: ScopeResult\n---\n正文')
    task = {'definition': '完整定义及AND/OR关系' * 2000}
    run_skill(skill, task, ScriptedLLM([call('submit_result', decisions=[])]), _registry(),
              ToolContext(db=db, cas=cas, run_id=rid))
    record = json.loads(db.one("SELECT content FROM agent_steps WHERE role='task'")['content'])
    assert record['kind'] == 'agent_step_payload'
    assert json.loads(cas.get_text(record['digest'])) == task
