"""Real extraction unit keys follow loaded allowed behavior, not sibling file bytes."""
from dataclasses import replace
from pathlib import Path

import pytest

from ciw2.harness import agent
from ciw2.harness.llm import ScriptedLLM
from ciw2.harness.tools import Tool
from ciw2.pipeline import extraction
from ciw2.pipeline.context import RunContext
from ciw2.service import Service


def context(settings):
    svc = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = svc.create_project('抽取缓存', ['C'])
    return svc.context(pid, svc.db.create_run(pid))


def replacement(fn):
    # Keep an actual existing filename: old key hashes disk, not this loaded code.
    namespace = {'__name__': fn.__module__}
    code = f"def {fn.__name__}(ctx, args):\n return {{'changed': True}}\n"
    exec(compile(code, fn.__code__.co_filename, 'exec'), namespace)  # noqa: S102 - loaded-code regression
    return namespace[fn.__name__]


def test_used_tool_loaded_implementation_invalidates_unit(settings, monkeypatch):
    rc = context(settings)
    before = extraction._key(rc, 'extract-design', {'drug': 'A'})
    tool = rc.registry.get('ctgov_get')
    monkeypatch.setattr(tool, 'fn', replacement(tool.fn))
    assert extraction._key(rc, 'extract-design', {'drug': 'A'}) != before


def test_unrelated_tool_sibling_disk_bytes_do_not_invalidate_unit(settings, monkeypatch):
    rc = context(settings)
    before = extraction._key(rc, 'extract-design', {'drug': 'A'})
    target = Path(rc.registry.get('ctgov_get').fn.__code__.co_filename)
    original = Path.read_bytes

    def changed(path):
        raw = original(path)
        return raw + b'\n# unrelated registered sibling changed\n' if path == target else raw

    monkeypatch.setattr(Path, 'read_bytes', changed)
    assert extraction._key(rc, 'extract-design', {'drug': 'A'}) == before


def test_unused_registered_tool_change_does_not_invalidate_unit(settings, monkeypatch):
    rc = context(settings)
    assert 'ctgov_search' not in rc.skills['extract-design'].tools
    before = extraction._key(rc, 'extract-design', {'drug': 'A'})
    tool = rc.registry.get('ctgov_search')
    monkeypatch.setattr(tool, 'fn', replacement(tool.fn))
    assert extraction._key(rc, 'extract-design', {'drug': 'A'}) == before


@pytest.mark.parametrize('surface', ['dispatch', 'skill_execution', 'agent_budget', 'skill_budget', 'skill_body'])
def test_actual_execution_contract_changes_invalidate_unit(settings, monkeypatch, surface):
    rc = context(settings)
    before = extraction._key(rc, 'extract-design', {'drug': 'A'})
    if surface == 'dispatch':
        monkeypatch.setattr(agent, '_dispatch', replacement(agent._dispatch))
    elif surface == 'skill_execution':
        monkeypatch.setattr(RunContext, 'skill', replacement(RunContext.skill))
    elif surface == 'agent_budget':
        rc.settings = replace(rc.settings, max_agent_steps=rc.settings.max_agent_steps + 1)
    else:
        spec = rc.skills['extract-design']
        changes = {'max_steps': spec.max_steps + 1} if surface == 'skill_budget' else {'body': spec.body + '\nNew rule'}
        rc.skills = {**rc.skills, 'extract-design': replace(spec, **changes)}
    assert extraction._key(rc, 'extract-design', {'drug': 'A'}) != before


def test_tool_schema_and_task_changes_are_still_dependencies(settings, monkeypatch):
    rc = context(settings)
    before = extraction._key(rc, 'extract-design', {'drug': 'A'})
    assert extraction._key(rc, 'extract-design', {'drug': 'B'}) != before
    tool = rc.registry.get('ctgov_get')
    monkeypatch.setitem(rc.registry._tools, 'ctgov_get', Tool(tool.name, tool.description + ' exact source', tool.args_model, tool.fn))
    assert extraction._key(rc, 'extract-design', {'drug': 'A'}) != before


def test_legacy_unit_is_not_resigned_and_new_completed_unit_reuses_without_research(settings, monkeypatch):
    from ciw2.domain.models import ExtractionResult

    rc = context(settings)
    rc.db.upsert_entity(rc.project_id, 'drug', 'Drug A')
    legacy_key = 'extraction:extract-results:' + '0' * 64
    rc.db.set_stage(rc.run_id, legacy_key, 'succeeded', output={
        'sources': [], 'result': {'facts': [], 'gaps': ['legacy-only'], 'extraction_model': 'old'}})
    before = rc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?', (rc.run_id, legacy_key))
    calls = []

    def skill(name, task):
        calls.append((name, task))
        return ExtractionResult(facts=[], gaps=['current exact task'])

    monkeypatch.setattr(rc, 'skill', skill)
    extra = lambda context, drug: {'mode': 'identity_enrichment', 'evidence_urls': []}
    first = extraction.extract_drugs(rc, 'extract-results', extra)
    second = extraction.extract_drugs(rc, 'extract-results', extra)
    assert len(calls) == 1 and first == second
    assert first['gaps'] == ['Drug A: current exact task']
    assert rc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?', (rc.run_id, legacy_key)) == before
    assert rc.llm.calls == []
