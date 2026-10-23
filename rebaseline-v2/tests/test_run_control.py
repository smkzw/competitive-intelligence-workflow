"""M6 有界运行控制：单进程串行准入、防重复提交和所有权边界。"""
from __future__ import annotations

import threading

import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import runner
from ciw2.pipeline.stages import Stage
from ciw2.service import RunRequestError, Service


def service(settings) -> Service:
    return Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))


def run_row(svc: Service, run_id: str) -> dict:
    return svc.db.one('SELECT * FROM runs WHERE id=?', (run_id,))


def test_simultaneous_starts_for_one_project_share_a_single_run(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('同一项目', ['A'])
    entered, release = threading.Event(), threading.Event()
    calls = []

    def stage(rc):
        calls.append(rc.run_id)
        entered.set()
        assert release.wait(5)
        return {'ok': True}

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', stage)])
    barrier = threading.Barrier(2)
    results, errors = [], []

    def submit():
        barrier.wait(5)
        try:
            results.append(svc.start_run(pid))
        except Exception as exc:  # noqa: BLE001 - failure is asserted below
            errors.append(exc)

    threads = [threading.Thread(target=submit) for _ in range(2)]
    for thread in threads:
        thread.start()
    assert entered.wait(5)
    for thread in threads:
        thread.join(5)
    try:
        assert not errors
        assert len(results) == 2 and len(set(results)) == 1
        assert len(svc.db.query('SELECT * FROM runs')) == 1
        assert calls == [results[0]]
    finally:
        release.set()
    assert svc.wait_idle(5)
    assert run_row(svc, results[0])['status'] == 'succeeded'


def test_distinct_projects_execute_one_at_a_time(settings, monkeypatch):
    svc = service(settings)
    first_project = svc.create_project('甲', ['A'])
    second_project = svc.create_project('乙', ['A'])
    gates = {first_project: threading.Event(), second_project: threading.Event()}
    first_started, second_started = threading.Event(), threading.Event()
    started = []

    def stage(rc):
        started.append(rc.project_id)
        if rc.project_id == first_project:
            first_started.set()
        else:
            second_started.set()
        assert gates[rc.project_id].wait(5)
        return {}

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', stage)])
    first_run = svc.start_run(first_project)
    assert first_started.wait(5)
    second_run = svc.start_run(second_project)
    try:
        assert run_row(svc, second_run)['status'] == 'queued'
        assert started == [first_project]
    finally:
        gates[first_project].set()
    assert second_started.wait(5)
    gates[second_project].set()
    assert svc.wait_idle(5)
    assert started == [first_project, second_project]
    assert run_row(svc, first_run)['status'] == run_row(svc, second_run)['status'] == 'succeeded'


def test_resume_of_active_run_is_deduplicated(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('重复恢复', ['A'])
    entered, release = threading.Event(), threading.Event()
    calls = []

    def stage(rc):
        calls.append(rc.run_id)
        entered.set()
        assert release.wait(5)
        return {}

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', stage)])
    run_id = svc.start_run(pid)
    assert entered.wait(5)
    try:
        assert svc.start_run(pid, resume_run=run_id) == run_id
        assert svc.start_run(pid) == run_id
        assert calls == [run_id]
    finally:
        release.set()
    assert svc.wait_idle(5)


def test_active_run_owned_by_another_process_is_not_taken_over(settings):
    svc = service(settings)
    pid = svc.create_project('外部运行', ['A'])
    run_id = svc.db.create_run(pid)
    svc.db.set_run(run_id, 'running')
    with pytest.raises(RunRequestError, match='其他进程'):
        svc.start_run(pid)
    with pytest.raises(RunRequestError, match='其他进程'):
        svc.cancel_run(pid, run_id)
    # Existing queued/running rows are not declared stale by Service construction or admission.
    assert run_row(svc, run_id)['status'] == 'running'
    assert Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None)).db.run(run_id)['status'] == 'running'


def test_terminal_run_does_not_block_a_new_distinct_run(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('已完成', ['A'])
    monkeypatch.setattr(runner, 'STAGES', [Stage('only', lambda rc: {})])
    first = svc.start_run(pid)
    assert svc.wait_idle(5)
    assert run_row(svc, first)['status'] == 'succeeded'
    second = svc.start_run(pid)
    assert second != first
    assert svc.wait_idle(5)
    assert run_row(svc, second)['status'] == 'succeeded'


def test_synchronous_mode_runs_inline_without_queueing(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('同步', ['A'])
    monkeypatch.setattr(runner, 'STAGES', [Stage('only', lambda rc: {'ok': 1})])
    run_id = svc.start_run(pid, background=False)
    assert run_row(svc, run_id)['status'] == 'succeeded'
    assert svc.wait_idle(0)
    assert svc.db.stage_output(run_id, 'only') == {'ok': 1}


def test_explicit_foreground_resume_claims_an_existing_queued_run(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('命令行恢复', ['A'])
    run_id = svc.db.create_run(pid)
    monkeypatch.setattr(runner, 'STAGES', [Stage('only', lambda rc: {})])
    assert svc.start_run(pid, resume_run=run_id, background=False) == run_id
    assert run_row(svc, run_id)['status'] == 'succeeded'
