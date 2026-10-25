"""Tool-scope runtime bindings: whitelisted implementations, not whole modules.

A Skill receipt must change when a tool it can call changes, and must stay equal
when a tool it cannot call changes in the same module. Shared execution
(agent dispatch, schema validation, Tool.run, registry lookup, pagination) must
invalidate every stage that runs a Skill. These cases use the loaded registry
and loaded code, not a mocked digest constant.
"""
from __future__ import annotations

import pytest
from runtime_resume_helpers import plan, render_output, service

from ciw2.harness import tools
from ciw2.pipeline import stage_versions
from ciw2.pipeline.runner import stages_for
from ciw2.pipeline.stages import Stage
from ciw2.sources import ctgov, websearch


def _bindings(rc, names: set[str]) -> dict[str, dict]:
    stages = stages_for(['A', 'B', 'C'])
    return {
        stage.name: stage_versions.stage_binding(
            rc, stage, [item.name for item in stages[:index]])
        for index, stage in enumerate(stages) if stage.name in names
    }


def _loaded(source: str, module_name: str, name: str):
    namespace = {'__name__': module_name}
    exec(compile(source, f'<{module_name}>', 'exec'), namespace)  # noqa: S102 - local fixture
    return namespace[name]


def _swap(monkeypatch, registry, name: str, fn) -> None:
    current = registry.get(name)
    monkeypatch.setitem(
        registry._tools, name,
        tools.Tool(current.name, current.description, current.args_model, fn))


def _analysis_names() -> set[str]:
    return {'intake', 'universe_china', 'candidate_triage',
            'analysis_A', 'analysis_B', 'analysis_C'}


def test_read_project_fact_change_leaves_tool_free_and_unrelated_stages_equal(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('读取工具实现范围', ['A', 'B', 'C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    before = _bindings(rc, _analysis_names())

    replacement = _loaded(
        "def read_project_fact(ctx, args):\n"
        "    return {'status': 'ok', 'requested_ref': args.fact_id, 'fact': None}\n",
        'ciw2.harness.tools', 'read_project_fact')
    monkeypatch.setattr(tools, 'read_project_fact', replacement)
    _swap(monkeypatch, rc.registry, 'read_project_fact', replacement)
    after = _bindings(rc, _analysis_names())

    assert after['intake'] == before['intake']
    assert after['universe_china'] == before['universe_china']
    assert after['candidate_triage'] == before['candidate_triage']
    for name in ('analysis_A', 'analysis_B', 'analysis_C'):
        assert after[name] != before[name]
        assert after[name]['code'] == before[name]['code']


def test_used_source_tool_change_leaves_other_tool_in_same_module_equal(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('来源工具范围', ['A', 'B', 'C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    before = _bindings(rc, {'universe_china', 'extract_design', 'analysis_A'})

    replacement = _loaded(
        "def _ctgov_get(ctx, args):\n"
        "    return {'status': 'ok', 'nct': args.nct, 'changed': True}\n",
        'ciw2.sources.ctgov', '_ctgov_get')
    monkeypatch.setattr(ctgov, '_ctgov_get', replacement)
    _swap(monkeypatch, rc.registry, 'ctgov_get', replacement)
    after = _bindings(rc, {'universe_china', 'extract_design', 'analysis_A'})

    assert after['extract_design'] != before['extract_design']
    assert after['universe_china'] == before['universe_china']
    assert after['analysis_A'] == before['analysis_A']


def test_registry_function_replacement_changes_consuming_stage_only(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('注册表替换', ['A', 'B', 'C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    names = {'universe_china', 'extract_design', 'analysis_A'}
    before = _bindings(rc, names)

    replacement = _loaded(
        "def _ctgov_get(ctx, args):\n"
        "    return {'status': 'ok', 'nct': args.nct, 'source': 'replaced'}\n",
        'ciw2.sources.ctgov', '_ctgov_get')
    _swap(monkeypatch, rc.registry, 'ctgov_get', replacement)
    after = _bindings(rc, names)

    assert after['extract_design'] != before['extract_design']
    assert after['universe_china'] == before['universe_china']
    assert after['analysis_A'] == before['analysis_A']


def test_read_project_fact_change_resumes_at_analysis_without_replaying_intake(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    def render(rc):
        calls.append('render')
        return render_output(rc)

    svc = plan(settings, monkeypatch, [
        Stage('intake', stub('intake')),
        Stage('analysis_C', stub('analysis_C')),
        Stage('render', render),
    ])
    pid = svc.create_project('读取工具恢复', ['C'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['intake', 'analysis_C', 'render']

    replacement = _loaded(
        "def read_project_fact(ctx, args):\n"
        "    return {'status': 'ok', 'requested_ref': args.fact_id, 'fact': None}\n",
        'ciw2.harness.tools', 'read_project_fact')
    monkeypatch.setattr(tools, 'read_project_fact', replacement)
    _swap(monkeypatch, svc.context(pid, run_id).registry, 'read_project_fact', replacement)
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)

    assert calls == ['analysis_C', 'render']


def test_same_module_helper_change_invalidates_the_tool_using_it(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('同模块辅助函数', ['A', 'B', 'C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    names = {'universe_china', 'analysis_A'}
    before = _bindings(rc, names)

    replacement = _loaded(
        "def web_search(settings, query, n=10):\n    return []\n",
        'ciw2.sources.websearch', 'web_search')
    monkeypatch.setattr(websearch, 'web_search', replacement)
    after = _bindings(rc, names)

    assert after['universe_china'] != before['universe_china']
    assert after['analysis_A'] == before['analysis_A']


def _patch_run(monkeypatch) -> None:
    monkeypatch.setattr(tools.Tool, 'run', _loaded(
        "def run(self, ctx, raw_args):\n    return 'changed'\n",
        'ciw2.harness.tools', 'run'))


def _patch_schema(monkeypatch) -> None:
    monkeypatch.setattr(tools.Tool, 'schema', _loaded(
        "def schema(self):\n    return {'type': 'function', 'function': {'name': self.name}}\n",
        'ciw2.harness.tools', 'schema'))


def _patch_registry(monkeypatch) -> None:
    monkeypatch.setattr(tools.ToolRegistry, 'subset', _loaded(
        "def subset(self, names):\n    return list(self._tools.values())\n",
        'ciw2.harness.tools', 'subset'))


def _patch_page_helper(monkeypatch) -> None:
    monkeypatch.setattr(tools, '_page_result', _loaded(
        "def _page_result(ctx, args):\n    return {'status': 'paged', 'changed': True}\n",
        'ciw2.harness.tools', '_page_result'))


def _patch_page_tool(monkeypatch) -> None:
    monkeypatch.setattr(tools, 'RESULT_PAGE_TOOL', tools.Tool(
        'read_tool_result', '变更后的分页说明', tools.PageArgs, tools._page_result))


def _patch_page_args(monkeypatch) -> None:
    class ChangedPageArgs(tools.PageArgs):
        window: int = 1

    monkeypatch.setattr(tools, 'PageArgs', ChangedPageArgs)


@pytest.mark.parametrize('patch', [
    _patch_run, _patch_schema, _patch_registry,
    _patch_page_helper, _patch_page_tool, _patch_page_args,
])
def test_shared_tool_execution_change_invalidates_every_skill_stage(settings, monkeypatch, patch):
    svc = service(settings)
    pid = svc.create_project('共享执行范围', ['A', 'B', 'C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    names = {'intake', 'universe_china', 'analysis_A', 'candidate_triage', 'verify'}
    before = _bindings(rc, names)

    patch(monkeypatch)
    after = _bindings(rc, names)

    for name in ('intake', 'universe_china', 'analysis_A', 'candidate_triage'):
        assert after[name] != before[name]
    assert after['verify'] == before['verify']


def test_unrelated_registered_function_name_cannot_hide_a_used_source_helper(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('工具与辅助函数同名', ['A', 'B', 'C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    unrelated = _loaded(
        "def web_search(ctx, args):\n    return {'status': 'ok', 'fact': None}\n",
        'ciw2.harness.tools', 'web_search')
    _swap(monkeypatch, rc.registry, 'read_project_fact', unrelated)
    before = _bindings(rc, {'universe_china'})
    replacement = _loaded(
        "def web_search(settings, query, n=10):\n    return ['changed helper']\n",
        'ciw2.sources.websearch', 'web_search')
    monkeypatch.setattr(websearch, 'web_search', replacement)
    assert _bindings(rc, {'universe_china'}) != before
