"""M6 合作式取消：排队取消、执行中停止边界、恢复与 Web 入口。"""
from __future__ import annotations

import json
import threading

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ciw2.harness.agent import run_skill
from ciw2.harness.cancellation import RunCancelled, RunControl
from ciw2.harness.fallback import FallbackLLM
from ciw2.harness.llm import LLMError, LLMReply, ScriptedLLM, ToolCall
from ciw2.harness.skills import Skill
from ciw2.harness.tools import ToolContext, ToolRegistry
from ciw2.pipeline import runner
from ciw2.pipeline.stages import Stage
from ciw2.service import RunRequestError, Service
from ciw2.web.app import create_app


def service(settings) -> Service:
    return Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))


def run_row(svc: Service, run_id: str) -> dict:
    return svc.db.one('SELECT * FROM runs WHERE id=?', (run_id,))


def test_cancelled_sync_run_waiting_for_the_execution_lock_never_starts(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('同步排队取消', ['A'])
    calls = []

    class GateLock:
        def __init__(self) -> None:
            self.entered, self.release = threading.Event(), threading.Event()

        def __enter__(self):
            self.entered.set()
            assert self.release.wait(5)

        def __exit__(self, *exc_info):
            return False

    gate = GateLock()
    svc._run_lock = gate
    monkeypatch.setattr(runner, 'STAGES', [Stage('only', lambda rc: calls.append('ran') or {})])
    thread = threading.Thread(target=lambda: svc.start_run(pid, background=False))
    thread.start()
    assert gate.entered.wait(5)
    active = svc.db.active_run(pid)
    assert active is not None and active['status'] == 'queued'
    reply = svc.cancel_run(pid, active['id'])
    assert reply['status'] == 'cancelled'
    gate.release.set()
    thread.join(5)
    assert not thread.is_alive()
    assert run_row(svc, active['id'])['status'] == 'cancelled'
    assert calls == []


def test_cancellation_is_not_swallowed_by_per_unit_error_isolation(settings, monkeypatch):
    assert issubclass(RunCancelled, BaseException) and not issubclass(RunCancelled, Exception)
    svc = service(settings)
    pid = svc.create_project('不吞取消', ['A'])

    def stage(rc):
        try:
            raise RunCancelled('synthetic stop')
        except Exception:  # noqa: BLE001 - 既有逐单元隔离模式不得吞掉取消
            return {'swallowed': True}
        return {}

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', stage)])
    run_id = svc.start_run(pid)
    assert svc.wait_idle(5)
    assert run_row(svc, run_id)['status'] == 'cancelled'
    assert run_row(svc, run_id)['error']


def test_queued_run_is_cancelled_before_any_stage_or_model(settings, monkeypatch):
    svc = service(settings)
    first_project = svc.create_project('先跑', ['A'])
    queued_project = svc.create_project('排队', ['A'])
    entered, release = threading.Event(), threading.Event()
    calls = []

    def stage(rc):
        calls.append(rc.run_id)
        entered.set()
        assert release.wait(5)
        return {}

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', stage)])
    first_run = svc.start_run(first_project)
    assert entered.wait(5)
    queued_run = svc.start_run(queued_project)
    assert run_row(svc, queued_run)['status'] == 'queued'
    try:
        reply = svc.cancel_run(queued_project, queued_run)
        assert reply == {'run_id': queued_run, 'status': 'cancelled', 'cancel_requested': True}
        assert svc.cancel_run(queued_project, queued_run) == {
            'run_id': queued_run, 'status': 'cancelled', 'cancel_requested': False}
        assert run_row(svc, queued_run)['status'] == 'cancelled'
        assert run_row(svc, queued_run)['finished_at']
    finally:
        release.set()
    assert svc.wait_idle(5)
    assert calls == [first_run]
    assert svc.db.query('SELECT * FROM agent_steps') == []
    assert svc.db.query('SELECT * FROM sources') == []


def test_active_cancel_stops_before_the_next_stage_and_keeps_finished_work(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('执行中', ['A'])
    entered, release = threading.Event(), threading.Event()
    calls = []

    def first_stage(rc):
        calls.append('one')
        entered.set()
        assert release.wait(5)
        return {'facts': 3}

    def second_stage(rc):
        calls.append('two')
        return {}

    monkeypatch.setattr(runner, 'STAGES', [Stage('one', first_stage), Stage('two', second_stage)])
    run_id = svc.start_run(pid)
    assert entered.wait(5)
    reply = svc.cancel_run(pid, run_id)
    assert reply['cancel_requested'] is True and reply['status'] == 'running'
    assert svc.stopping(run_id) is True
    release.set()
    assert svc.wait_idle(5)
    row = run_row(svc, run_id)
    assert row['status'] == 'cancelled' and '用户请求停止' in row['error']
    stages = {s['name']: s for s in svc.db.query('SELECT * FROM stages WHERE run_id=?', (run_id,))}
    assert stages['one']['status'] == 'succeeded'
    assert json.loads(stages['one']['output_json']) == {'facts': 3}
    assert stages.get('two', {'status': 'pending'})['status'] == 'pending'
    assert calls == ['one']


def test_cancel_does_not_replace_a_completed_run(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('完成竞态', ['A'])
    entered, release = threading.Event(), threading.Event()

    def stage(rc):
        entered.set()
        assert release.wait(5)
        return {'done': True}

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', stage)])
    run_id = svc.start_run(pid)
    assert entered.wait(5)
    reply = svc.cancel_run(pid, run_id)
    assert reply['cancel_requested'] is True
    release.set()
    assert svc.wait_idle(5)
    assert run_row(svc, run_id)['status'] == 'succeeded'
    again = svc.cancel_run(pid, run_id)
    assert again == {'run_id': run_id, 'status': 'succeeded', 'cancel_requested': False}
    assert run_row(svc, run_id)['status'] == 'succeeded'


def test_resume_after_cancel_reuses_completed_stage_and_runs_pending(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('取消恢复', ['A'])
    calls = []

    def first_stage(rc):
        calls.append('one')
        svc.cancel_run(rc.project_id, rc.run_id)
        return {'kept': True}

    def second_stage(rc):
        calls.append('two')
        return {'finished': True}

    monkeypatch.setattr(runner, 'STAGES', [Stage('one', first_stage), Stage('two', second_stage)])
    run_id = svc.start_run(pid)
    assert svc.wait_idle(5)
    assert run_row(svc, run_id)['status'] == 'cancelled'
    assert calls == ['one']
    assert svc.start_run(pid, resume_run=run_id) == run_id
    assert svc.wait_idle(5)
    assert run_row(svc, run_id)['status'] == 'succeeded'
    assert calls == ['one', 'two']
    assert svc.db.stage_output(run_id, 'one') == {'kept': True}
    assert svc.db.stage_output(run_id, 'two') == {'finished': True}


def test_resume_after_cancelled_stage_does_not_reuse_stale_downstream_success(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('下游重置', ['A'])
    run_id = svc.db.create_run(pid)
    calls = []

    stages = [
        Stage('one', lambda rc: calls.append('one') or {}),
        Stage('two', lambda rc: calls.append('two') or {'fresh': 2}),
        Stage('three', lambda rc: calls.append('three') or {'fresh': 3}),
    ]
    monkeypatch.setattr(runner, 'STAGES', stages)
    rc = svc.context(pid, run_id)
    # Fixture-only: seed the bound prefix with a legitimate current runtime receipt.
    assert runner.stage_versions.ensure_pipeline_scope(rc)
    runner.complete_stage(rc, stages[0], {'kept': True})
    svc.db.set_stage(run_id, 'two', 'cancelled', error='用户请求停止')
    svc.db.set_stage(run_id, 'three', 'succeeded', output={'stale': True})
    assert runner.execute(rc) == 'succeeded'
    assert calls == ['two', 'three']
    assert svc.db.stage_output(run_id, 'one') == {'kept': True}
    assert svc.db.stage_output(run_id, 'three') == {'fresh': 3}


def test_cancel_rejects_a_run_from_another_project(settings):
    svc = service(settings)
    first = svc.create_project('甲', ['A'])
    second = svc.create_project('乙', ['A'])
    run_id = svc.db.create_run(first)
    with pytest.raises(RunRequestError, match='不属于'):
        svc.cancel_run(second, run_id)
    assert run_row(svc, run_id)['status'] == 'queued'


def test_stop_request_never_enters_a_backup_route():
    class Route:
        def __init__(self, model: str, error: Exception | None = None) -> None:
            self.model = model
            self.error = error
            self.calls = 0

        def chat(self, messages, tools=None):
            self.calls += 1
            if self.error is not None:
                raise self.error
            return LLMReply(content='ok')

    primary, backup = Route('primary', LLMError('unavailable')), Route('backup')
    llm = FallbackLLM([primary, backup])
    checks = {'n': 0}

    def check():
        checks['n'] += 1
        if checks['n'] == 2:
            raise RunCancelled('stop before backup route')

    llm.set_cancel_check(check)
    with pytest.raises(RunCancelled):
        llm.chat([])
    assert primary.calls == 1 and backup.calls == 0


def test_stop_request_is_checked_before_starting_a_tool():
    control = RunControl()

    class RequestingLLM:
        model = 'synthetic'

        def __init__(self) -> None:
            self.calls = 0

        def chat(self, messages, tools=None):
            self.calls += 1
            control.request_stop()
            return LLMReply(tool_calls=[ToolCall(id='t1', name='read_tool_result',
                                                 arguments={'result_id': 'a' * 64})])

    llm = RequestingLLM()
    skill = Skill(name='synthetic', description='d', body='', tools=[])
    with pytest.raises(RunCancelled):
        run_skill(skill, {}, llm, ToolRegistry(), ToolContext(), check_cancelled=control.check_cancelled)
    assert llm.calls == 1


def test_completed_submission_is_kept_when_stop_arrives_during_the_model_call():
    control = RunControl()

    class SubmittingLLM:
        model = 'synthetic'

        def chat(self, messages, tools=None):
            control.request_stop()
            return LLMReply(tool_calls=[ToolCall(id='s1', name='submit_result', arguments={'result': 'kept'})])

    skill = Skill(name='synthetic', description='d', body='', tools=[], output=None)
    result = run_skill(skill, {}, SubmittingLLM(), ToolRegistry(), ToolContext(),
                       check_cancelled=control.check_cancelled)
    assert result == {'result': 'kept'}


def test_stop_request_inside_a_tool_is_not_reported_as_tool_failure():
    registry = ToolRegistry()

    class Args(BaseModel):
        pass

    @registry.register('stop_now', 'synthetic', Args)
    def stop_now(ctx, args):
        raise RunCancelled('stop inside tool')

    with pytest.raises(RunCancelled):
        registry.get('stop_now').run(ToolContext(), {})


def test_authenticated_web_cancel_and_workbench_labels(settings, monkeypatch):
    token = 'unit-access-token'
    monkeypatch.setenv('CIW_ACCESS_TOKEN', token)
    app = create_app(settings, llm_factory=lambda s: (ScriptedLLM([]), None), background=False)
    client = TestClient(app)
    assert client.post('/api/projects/x/runs/y/cancel').status_code == 401
    params = {'token': token}
    first = client.post('/api/projects', params=params,
                        json={'indication': '甲', 'start': False}).json()['project_id']
    second = client.post('/api/projects', params=params,
                         json={'indication': '乙', 'start': False}).json()['project_id']
    svc = app.state.svc
    run_id = svc.db.create_run(first)
    page = client.get(f'/projects/{first}', params=params)
    assert page.status_code == 200 and '排队中' in page.text and '停止' in page.text
    wrong = client.post(f'/api/projects/{second}/runs/{run_id}/cancel', params=params)
    assert wrong.status_code == 409 and '不属于' in wrong.text
    cancelled = client.post(f'/api/projects/{first}/runs/{run_id}/cancel', params=params)
    assert cancelled.status_code == 200
    assert cancelled.json() == {'run_id': run_id, 'status': 'cancelled', 'cancel_requested': True}
    page = client.get(f'/projects/{first}', params=params)
    assert '已取消' in page.text and '从取消处继续' in page.text
    form_run = svc.db.create_run(first)
    form = client.post(f'/projects/{first}/runs/{form_run}/cancel', params=params, follow_redirects=False)
    assert form.status_code == 303
    assert run_row(svc, form_run)['status'] == 'cancelled'
