import json

from pydantic import BaseModel

from ciw2.harness.agent import run_skill
from ciw2.harness.llm import LLMReply, ScriptedLLM, ToolCall
from ciw2.harness.skills import Skill
from ciw2.harness.tools import ToolContext, ToolRegistry
from ciw2.store.cas import CAS


class EmptyArgs(BaseModel):
    pass


def test_large_result_pages_recover_exact_content_without_refetch(tmp_path):
    registry = ToolRegistry()
    original = '源文"\\\n' * 6000
    reads = []

    @registry.register('large', 'test source', EmptyArgs)
    def large(ctx, args):
        reads.append(True)
        return original

    ctx = ToolContext(cas=CAS(tmp_path / 'cas'))
    returned = []

    def respond(messages):
        tools = [m for m in messages if m['role'] == 'tool']
        if not tools:
            return LLMReply(tool_calls=[ToolCall('first', 'large', {})])
        chunk = json.loads(tools[-1]['content'])
        assert len(tools[-1]['content']) <= 12000
        returned.append(chunk['text'])
        if chunk['next_offset'] is not None:
            return LLMReply(tool_calls=[ToolCall('next', 'read_tool_result', {
                'result_id': chunk['result_id'], 'offset': chunk['next_offset']})])
        return LLMReply(tool_calls=[ToolCall('done', 'submit_result', {'done': True})])

    skill = Skill('pagination', 'bounded returns', '', tools=['large'], max_steps=32)
    assert run_skill(skill, {}, ScriptedLLM(respond), registry, ctx) == {'done': True}
    assert ''.join(returned) == original
    assert len(reads) == 1


def test_large_result_without_cas_is_explicit_failure():
    registry = ToolRegistry()

    @registry.register('large', 'large', EmptyArgs)
    def large(ctx, args):
        return 'x' * 13000

    result = json.loads(registry.get('large').run(ToolContext(), {}))
    assert result['status'] == 'tool_failed'
