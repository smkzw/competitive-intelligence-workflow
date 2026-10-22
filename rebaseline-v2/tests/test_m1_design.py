import json

import pytest

from ciw2.render.portal import data_c, render_report
from ciw2.sources.ctgov import design_facts, parse_study
from ciw2.store.db import DB


@pytest.fixture
def design_project(settings):
    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project('设计比较', ['C'])
    trial, _ = db.upsert_entity(pid, 'trial', 'trial-one', attrs={'url': 'https://example.org/trial'})
    source = db.add_source(pid, 'ctgov', 'https://example.org/source', 'digest')
    return db, pid, trial, source


def add_fact(project, field, value, status='verified', **context):
    db, pid, trial, source = project
    return db.add_fact({'project_id': pid, 'entity_id': trial, 'field': field, 'value': value,
                        'source_id': source, 'tier': 'critical', 'status': status,
                        'quote': 'Original design evidence', 'context': context, 'extracted_by': 'code:test'})


def test_unverified_size_is_visible_but_never_charted(design_project):
    add_fact(design_project, 'design.sample_size', 100, 'unverified')
    data = data_c(*design_project[:2])
    assert data['rows'][0]['sample_size'] == 100
    assert data['charts']['size']['values'] == []


def test_design_sources_and_enrollment_kind_are_reachable(design_project):
    fid = add_fact(design_project, 'design.sample_size', 0, enrollment_type='ESTIMATED')
    row = data_c(*design_project[:2])['rows'][0]
    assert row['sample_size'] == 0
    assert row['sample_size_type'] == 'ESTIMATED'
    assert row['sources']['sample_size'][0]['fact_id'] == fid
    assert row['sources']['sample_size'][0]['url'] == 'https://example.org/source'
    assert row['sources']['sample_size'][0]['quote'] == 'Original design evidence'


def test_visit_groups_use_exact_equivalence_and_retain_unknowns(design_project):
    for endpoint, visit in [('EASI-75', 'Week 16'), ('EASI-75', 'Day 112'),
                             ('EASI-75', 'Week 24'), ('EASI-75', 'during treatment')]:
        add_fact(design_project, 'design.primary_endpoint', {'measure': endpoint, 'time_frame': visit})
    groups = data_c(*design_project[:2])['endpoint_groups']
    assert sorted(len(g['entries']) for g in groups) == [1, 1, 2]
    assert sum(len(g['entries']) for g in groups) == 4
    assert all(e['fact_id'] for g in groups for e in g['entries'])


def test_registry_eligibility_is_retained_and_thresholds_are_explicit(design_project, study):
    criteria = 'Inclusion Criteria:\n- EASI >= 16\n- IGA >= 3\nExclusion Criteria:\n- active infection'
    study['protocolSection']['eligibilityModule']['eligibilityCriteria'] = criteria
    parsed = design_facts(parse_study(study))
    fact = next(f for f in parsed if f['field'] == 'design.eligibility.criteria')
    assert fact['value'] == criteria and fact['context']['json_path']
    add_fact(design_project, fact['field'], fact['value'])
    row = data_c(*design_project[:2])['rows'][0]
    assert row['eligibility_criteria'] == criteria
    assert {(v['measure'], v['operator'], v['value']) for v in row['eligibility_thresholds']} == {
        ('EASI', '>=', 16.0), ('IGA', '>=', 3.0)}


def test_structured_chart_data_cannot_break_out_of_script(design_project):
    attack = '</script><script>globalThis.INJECTED=true</script>'
    add_fact(design_project, 'design.sample_size', 100)
    add_fact(design_project, 'design.primary_endpoint', {'measure': attack, 'time_frame': 'Week 16'})
    design_project[0].execute('UPDATE entities SET name=? WHERE id=?', (attack, design_project[2]))
    html = render_report(*design_project[:2], 'C')
    assert attack not in html
    payload = html.split('<script id="charts" type="application/json">', 1)[1].split('</script>', 1)[0]
    json.loads(payload)


def test_c_has_comparison_and_inline_original_evidence(design_project):
    add_fact(design_project, 'design.sample_size', 100)
    add_fact(design_project, 'design.primary_endpoint', {'measure': 'EASI-75', 'time_frame': 'Week 16'})
    html = render_report(*design_project[:2], 'C')
    assert '终点与时间点' in html and 'Original design evidence' in html
    assert 'https://example.org/source' in html and 'data-fact-id=' in html


def test_single_visit_and_interval_are_not_merged(design_project):
    for visit in ('Week 16', 'Baseline to Week 16', 'Week 16 and Week 24'):
        add_fact(design_project, 'design.primary_endpoint', {'measure': 'EASI-75', 'time_frame': visit})
    groups = data_c(*design_project[:2])['endpoint_groups']
    assert len(groups) == 3


def test_phase_counts_do_not_use_unverified_phase(design_project):
    add_fact(design_project, 'design.phase', 'phase3', 'unverified')
    data = data_c(*design_project[:2])
    assert data['rows'][0]['phase'] == 'phase3'
    assert data['charts']['phase'] == []
