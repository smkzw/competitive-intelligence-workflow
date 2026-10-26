"""Actual callbacks must be observable as running, not merely queued/pending."""
import pytest
from fastapi.testclient import TestClient

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import runner
from ciw2.pipeline.stages import Stage
from ciw2.web.app import create_app


@pytest.mark.parametrize('outcome', ['succeeded', 'failed', 'cancelled'])
def test_live_callback_and_workbench_show_running_before_terminal_state(settings, monkeypatch, outcome):
    app = create_app(settings, llm_factory=lambda _: (ScriptedLLM([]), None), background=False)
    svc = app.state.svc
    pid = svc.create_project('阶段状态测试', ['C'])
    seen = []

    def work(rc):
        row = rc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?',
                        (rc.run_id, 'enrich_drugs'))
        seen.append(row)
        assert row['status'] == 'running'
        assert row['started_at'] and row['finished_at'] is None
        with TestClient(app) as client:
            page = client.get(f'/projects/{pid}').text
        assert '当前 药物资料补充' in page
        if outcome == 'failed':
            raise RuntimeError('controlled callback failure')
        if outcome == 'cancelled':
            svc.cancel_run(pid, rc.run_id)
            rc.check_cancelled()
        return {'complete': True}

    monkeypatch.setattr(runner, 'STAGES', [Stage('enrich_drugs', work)])
    rid = svc.start_run(pid, background=False)
    assert len(seen) == 1
    assert seen[0]['status'] == 'running' and seen[0]['started_at']
    assert svc.db.run(rid)['status'] == outcome
    row = svc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?', (rid, 'enrich_drugs'))
    assert row['status'] == outcome
    assert row['started_at'] == seen[0]['started_at'] and row['finished_at']
