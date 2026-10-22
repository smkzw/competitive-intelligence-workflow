import pytest
from fastapi.testclient import TestClient

from ciw2.render.portal import render_report, report_data
from ciw2.service import Service
from ciw2.web.app import create_app


def no_model(settings):
    pytest.fail('Rejected run must not initialize a model client')


def test_historical_request_fails_before_model_or_source_access(settings):
    service = Service(settings, llm_factory=no_model)
    pid = service.create_project('适应症', ['C'], cutoff_date='2025-01-01')
    rid = service.start_run(pid, background=False)
    run = service.db.one('SELECT * FROM runs WHERE id=?', (rid,))
    assert run['status'] == 'failed' and '历史截止日' in run['error']
    assert service.db.query('SELECT * FROM agent_steps') == []
    assert service.db.query('SELECT * FROM sources') == []


@pytest.mark.parametrize('report', ['A', 'B', 'C'])
def test_current_facts_cannot_be_rendered_as_historical_report(settings, report):
    service = Service(settings, llm_factory=no_model)
    pid = service.create_project('适应症', [report], cutoff_date='2025-01-01')
    with pytest.raises(ValueError, match='历史截止日'):
        report_data(service.db, pid, report)
    with pytest.raises(ValueError, match='历史截止日'):
        render_report(service.db, pid, report)


def test_history_web_request_has_failed_run_and_unavailable_portal(settings):
    app = create_app(settings, llm_factory=no_model, background=False)
    client = TestClient(app)
    result = client.post('/api/projects', json={'indication': '适应症', 'reports': ['C'],
                                              'cutoff_date': '2025-01-01'}).json()
    run = client.get(f"/api/runs/{result['run_id']}").json()
    assert run['status'] == 'failed'
    response = client.get(f"/projects/{result['project_id']}/portal/C")
    assert response.status_code == 409 and '历史截止日' in response.text


def test_foreign_resume_is_rejected_without_mutating_original_run(settings):
    service = Service(settings, llm_factory=no_model)
    first = service.create_project('甲', ['C'])
    second = service.create_project('乙', ['C'])
    rid = service.db.create_run(first)
    original = service.db.one('SELECT * FROM runs WHERE id=?', (rid,))
    with pytest.raises(ValueError, match='不属于'):
        service.start_run(second, resume_run=rid, background=False)
    assert service.db.one('SELECT * FROM runs WHERE id=?', (rid,)) == original
    assert service.db.query('SELECT * FROM agent_steps') == []


def test_nonexistent_resume_and_project_do_not_create_orphan_runs(settings):
    service = Service(settings, llm_factory=no_model)
    pid = service.create_project('甲', ['C'])
    for project, run_id in ((pid, 'not-a-run'), ('not-a-project', None)):
        with pytest.raises(ValueError, match='不存在'):
            service.start_run(project, resume_run=run_id, background=False)
    assert service.db.query('SELECT * FROM runs') == []


def test_resume_api_rejects_foreign_binding_with_clear_error(settings):
    app = create_app(settings, llm_factory=no_model, background=False)
    client = TestClient(app)
    first = client.post('/api/projects', json={'indication': '甲', 'start': False}).json()['project_id']
    second = client.post('/api/projects', json={'indication': '乙', 'start': False}).json()['project_id']
    rid = app.state.svc.db.create_run(first)
    response = client.post(f'/api/projects/{second}/runs', params={'resume_run': rid})
    assert response.status_code == 409 and '不属于' in response.text
