"""Landscape charts never turn missing knowledge into colored observations."""
import json

from ciw2.harness.llm import ScriptedLLM
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service


def test_landscape_chart_query_retains_ids_and_does_not_invent_unknown_observations(settings):
    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = svc.create_project('研究范围', ['A'])
    known, _ = svc.db.upsert_entity(pid, 'drug', 'Known', attrs={
        'targets': ['Target X'], 'highest_phase_global': 'phase2'})
    unknown, _ = svc.db.upsert_entity(pid, 'drug', 'Unknown')
    data = report_data(svc.db, pid, 'A')
    assert {r['id'] for r in data['rows']} == {known, unknown}
    projected = data['charts']['landscape']['rows']
    assert {r['id'] for r in projected} == {known, unknown}
    assert next(r for r in projected if r['id'] == unknown)['targets'] == []
    assert data['charts']['landscape']['phase_labels']['phase2'] == 'II 期'
    assert 'unknown' not in data['charts']['landscape']['phase_labels']
    html = render_report(svc.db, pid, 'A')
    assert f'data-entity-id="{known}"' in html and f'data-entity-id="{unknown}"' in html
    assert 'id="landscape-count"' in html
    assert '未知靶点' not in json.dumps(data['charts'], ensure_ascii=False)


def test_empty_landscape_does_not_require_placeholder_chart_points(settings):
    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = svc.create_project('研究范围', ['A'])
    assert report_data(svc.db, pid, 'A')['charts']['landscape']['rows'] == []
