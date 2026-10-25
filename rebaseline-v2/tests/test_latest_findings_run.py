"""动态报告摘要只能来自项目当前运行：最新运行没有有效分析阶段时不得回退到旧运行。"""
from __future__ import annotations

from typing import Any

import pytest

from ciw2.config import Settings
from ciw2.service import Service


def _project(svc: Service, reports: list[str] | None = None) -> str:
    return svc.db.create_project('特应性皮炎', reports or ['A', 'B', 'C'])


def _run(svc: Service, pid: str, *, status: str = 'succeeded', created_at: str | None = None) -> str:
    run_id = svc.db.create_run(pid)
    svc.db.set_run(run_id, status)
    if created_at is not None:
        svc.db.execute('UPDATE runs SET created_at=? WHERE id=?', (created_at, run_id))
    return run_id


def _analysis(svc: Service, run_id: str, report: str, findings: list[dict[str, Any]],
              *, status: str = 'succeeded') -> None:
    svc.db.set_stage(run_id, f'analysis_{report}', status,
                     {'report': report, 'run': run_id, 'findings': findings})


def test_latest_failed_run_does_not_reuse_older_success(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    _run(svc, pid, status='failed', created_at='2026-10-25T10:00:00+00:00')
    assert svc.latest_findings(pid, 'A') is None


@pytest.mark.parametrize('status', ['queued', 'running', 'cancelled'])
def test_latest_unfinished_or_cancelled_run_does_not_reuse_older_success(settings: Settings, status: str) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    _run(svc, pid, status=status, created_at='2026-10-25T10:00:00+00:00')
    assert svc.latest_findings(pid, 'A') is None


def test_latest_run_without_the_requested_stage_returns_none(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    new = _run(svc, pid, status='failed', created_at='2026-10-25T10:00:00+00:00')
    _analysis(svc, new, 'B', [{'title': '仅有 B 分析'}])
    assert svc.latest_findings(pid, 'A') is None


def test_latest_run_failed_analysis_returns_none(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    new = _run(svc, pid, status='failed', created_at='2026-10-25T10:00:00+00:00')
    _analysis(svc, new, 'A', [{'title': '失败分析'}], status='failed')
    assert svc.latest_findings(pid, 'A') is None


@pytest.mark.parametrize('empty', [None, ''])
def test_latest_run_succeeded_stage_without_output_returns_none(settings: Settings, empty: str | None) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    new = _run(svc, pid, created_at='2026-10-25T10:00:00+00:00')
    svc.db.set_stage(new, 'analysis_A', 'succeeded', None)
    svc.db.execute('UPDATE stages SET output_json=? WHERE run_id=? AND name=?', (empty, new, 'analysis_A'))
    assert svc.latest_findings(pid, 'A') is None


def test_latest_succeeded_run_returns_its_own_findings(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    new = _run(svc, pid, created_at='2026-10-25T10:00:00+00:00')
    _analysis(svc, new, 'A', [{'title': '当前运行要点'}])
    result = svc.latest_findings(pid, 'A')
    assert result is not None
    assert result['run'] == new
    assert result['findings'] == [{'title': '当前运行要点'}]


def test_created_at_outranks_rowid_when_picking_latest_run(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    earlier_rowid = _run(svc, pid, created_at='2026-10-25T10:00:00+00:00')
    _analysis(svc, earlier_rowid, 'A', [{'title': '较新写入时间'}])
    _run(svc, pid, status='failed', created_at='2026-10-24T10:00:00+00:00')
    assert svc.latest_run(pid)['id'] == earlier_rowid
    result = svc.latest_findings(pid, 'A')
    assert result is not None
    assert result['run'] == earlier_rowid


def test_tied_created_at_prefers_the_later_rowid(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    tie = '2026-10-25T10:00:00+00:00'
    first = _run(svc, pid, created_at=tie)
    _analysis(svc, first, 'A', [{'title': '先插入'}])
    second = _run(svc, pid, created_at=tie)
    _analysis(svc, second, 'A', [{'title': '后插入'}])
    assert svc.latest_run(pid)['id'] == second
    result = svc.latest_findings(pid, 'A')
    assert result is not None
    assert result['run'] == second
    assert result['findings'] == [{'title': '后插入'}]


def test_other_project_run_never_supplies_findings(settings: Settings) -> None:
    svc = Service(settings)
    failed_pid = _project(svc)
    other_pid = _project(svc)
    old = _run(svc, failed_pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '本项目旧运行要点'}])
    _run(svc, failed_pid, status='failed', created_at='2026-10-25T10:00:00+00:00')
    other = _run(svc, other_pid, created_at='2026-10-25T11:00:00+00:00')
    _analysis(svc, other, 'A', [{'title': '其他项目要点'}])
    assert svc.latest_findings(failed_pid, 'A') is None
    assert svc.latest_findings(other_pid, 'A')['run'] == other


def test_latest_run_other_report_analysis_never_supplies_findings(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    new = _run(svc, pid, created_at='2026-10-25T10:00:00+00:00')
    _analysis(svc, new, 'B', [{'title': '当前运行 B 要点'}])
    assert svc.latest_findings(pid, 'A') is None
    assert svc.latest_findings(pid, 'B')['run'] == new


def test_empty_findings_in_latest_successful_analysis_are_valid(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    old = _run(svc, pid, created_at='2026-10-24T10:00:00+00:00')
    _analysis(svc, old, 'A', [{'title': '旧运行要点'}])
    new = _run(svc, pid, created_at='2026-10-25T10:00:00+00:00')
    _analysis(svc, new, 'A', [])
    result = svc.latest_findings(pid, 'A')
    assert result is not None
    assert result['run'] == new
    assert result['findings'] == []


def test_latest_analysis_succeeds_even_when_run_fails_another_stage(settings: Settings) -> None:
    svc = Service(settings)
    pid = _project(svc)
    new = _run(svc, pid, status='failed', created_at='2026-10-25T10:00:00+00:00')
    _analysis(svc, new, 'A', [{'title': '当前运行要点'}])
    svc.db.set_stage(new, 'extract-results', 'failed', error='抽取中断')
    result = svc.latest_findings(pid, 'A')
    assert result is not None
    assert result['run'] == new
    assert result['findings'] == [{'title': '当前运行要点'}]


def test_nonexistent_project_returns_none(settings: Settings) -> None:
    svc = Service(settings)
    assert svc.latest_findings('prj_missing', 'A') is None
