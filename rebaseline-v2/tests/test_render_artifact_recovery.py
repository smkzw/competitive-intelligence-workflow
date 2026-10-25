"""Production render receipts must cover actual files, not only output filenames."""
from pathlib import Path

import pytest
from runtime_resume_helpers import plan, status

from ciw2.pipeline import stages
from ciw2.pipeline.stages import Stage


@pytest.mark.parametrize('damage', ['missing', 'tampered'])
def test_render_recreates_missing_or_changed_report_without_research(settings, monkeypatch, damage):
    svc = plan(settings, monkeypatch, [Stage('render', stages.render)])
    pid = svc.create_project('恢复真实渲染文件', ['C'])
    rid = svc.start_run(pid, background=False)
    assert status(svc, rid) == 'succeeded'
    page = settings.portals_dir / pid / 'C.html'
    expected = page.read_bytes()
    if damage == 'missing':
        page.unlink()
    else:
        page.write_bytes(b'damaged report bytes')
    svc.start_run(pid, resume_run=rid, background=False)
    assert status(svc, rid) == 'succeeded'
    assert page.is_file() and page.read_bytes() == expected
    assert svc.db.query('SELECT * FROM agent_steps') == []


def test_unchanged_report_is_not_rewritten(settings, monkeypatch):
    svc = plan(settings, monkeypatch, [Stage('render', stages.render)])
    pid = svc.create_project('保留正确页面', ['C'])
    rid = svc.start_run(pid, background=False)
    page = settings.portals_dir / pid / 'C.html'
    before = page.stat().st_mtime_ns
    assert svc.start_run(pid, resume_run=rid, background=False) == rid
    assert Path(page).stat().st_mtime_ns == before


def test_changed_render_bytes_append_receipt_instead_of_overwriting_history(settings, monkeypatch):
    from runtime_resume_helpers import receipts

    from ciw2.pipeline import runner

    svc = plan(settings, monkeypatch, [Stage('prepare', lambda rc: {'revision': 1}),
                                      Stage('render', stages.render)])
    pid = svc.create_project('旧标题', ['C'])
    rid = svc.start_run(pid, background=False)
    old = receipts(svc, rid, 'render')[0]['row']
    svc.db.execute('UPDATE projects SET indication=? WHERE id=?', ('新的标题', pid))
    monkeypatch.setattr(runner, 'STAGES', [Stage('prepare', lambda rc: {'revision': 2}),
                                         Stage('render', stages.render)])
    svc.start_run(pid, resume_run=rid, background=False)
    assert status(svc, rid) == 'succeeded'
    assert '新的标题' in (settings.portals_dir / pid / 'C.html').read_text()
    current = receipts(svc, rid, 'render')
    assert len(current) == 2
    assert current[0]['row'] == old
    assert current[0]['receipt']['artifacts'] != current[1]['receipt']['artifacts']
