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
