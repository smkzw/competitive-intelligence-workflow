"""Ordinary pipeline recovery must not silently adopt component-only old work."""
import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import runner
from ciw2.pipeline.stages import Stage
from ciw2.service import Service


@pytest.mark.parametrize('legacy_name,legacy_status', [
    ('analysis_C', 'failed'),
    ('analysis_unit:record:previous', 'succeeded'),
    ('trial_ingestion:fixture:unit', 'succeeded'),
    ('intake', 'pending'),
])
def test_unbound_existing_run_refuses_before_callback_and_stage_mutation(
        settings, monkeypatch, legacy_name, legacy_status):
    svc = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = svc.create_project('合成归并旧记录', ['C'])
    rid = svc.db.create_run(pid)
    svc.db.set_stage(rid, legacy_name, legacy_status, output={'retained': True})
    before = svc.db.query('SELECT * FROM stages ORDER BY name')
    calls = []
    monkeypatch.setattr(runner, 'STAGES', [Stage('intake', lambda rc: calls.append('intake') or {})])
    result = runner.execute(svc.context(pid, rid))
    assert result == 'failed'
    assert calls == []
    assert svc.db.query('SELECT * FROM stages ORDER BY name') == before
    assert '恢复候选' in svc.db.run(rid)['error']


def test_scope_marker_from_other_run_is_not_adopted(settings, monkeypatch):
    from ciw2.pipeline import stage_versions
    svc = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = svc.create_project('错误流程身份', ['C'])
    rid = svc.db.create_run(pid)
    svc.db.set_stage(rid, stage_versions.WORKFLOW_SCOPE_NAME, 'succeeded', output={
        'schema': 'ciw2-pipeline-scope-v1', 'scope': 'ordinary_pipeline',
        'project_id': pid, 'run_id': 'different_run'})
    before = svc.db.query('SELECT * FROM stages ORDER BY name')
    calls = []
    monkeypatch.setattr(runner, 'STAGES', [Stage('intake', lambda rc: calls.append('intake') or {})])
    assert runner.execute(svc.context(pid, rid)) == 'failed'
    assert calls == []
    assert svc.db.query('SELECT * FROM stages ORDER BY name') == before


def test_new_failed_run_scope_allows_same_run_retry_and_hides_internal_row(settings, monkeypatch):
    svc = Service(settings, llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = svc.create_project('正常首次失败后继续', ['C'])
    calls = []

    def intake(rc):
        calls.append('intake')
        if len(calls) == 1:
            raise RuntimeError('temporary failure')
        return {'retained': True}

    monkeypatch.setattr(runner, 'STAGES', [Stage('intake', intake)])
    rid = svc.start_run(pid, background=False)
    assert svc.db.run(rid)['status'] == 'failed'
    assert svc.start_run(pid, resume_run=rid, background=False) == rid
    assert svc.db.run(rid)['status'] == 'succeeded'
    assert calls == ['intake', 'intake']
    assert [s['name'] for s in runner.stage_table(svc.db, rid, ['C'])] == ['intake']
