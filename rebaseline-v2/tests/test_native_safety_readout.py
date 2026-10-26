"""Every adopted native AE observation has a correct, lossless B consumer."""
from test_result_presentation import project

from ciw2.render.portal import data_b, render_report


def safety_project(settings):
    db, pid, _ = project(settings, [])
    tid = db.entities(pid, 'trial')[0]['id']
    sid = db.query('SELECT id FROM sources WHERE project_id=?', (pid,))[0]['id']
    ids = []
    values = [('safety.sae.any', 0, 10, 0, None, None),
              ('safety.death.all_cause', 0, 0, None, None, None),
              ('safety.other_ae.above_threshold', 3, 10, 30, None, None),
              ('safety.sae.term', 2, 10, 20, 'Headache', 5),
              ('safety.ae.term', 1, 10, 10, 'Headache', 2),
              ('safety.ae.term', None, 10, None, 'Unknown term', None)]
    for field, value, n, rate, term, events in values:
        ids.append(db.add_fact({'project_id': pid, 'entity_id': tid, 'source_id': sid,
            'field': field, 'value': value, 'tier': 'critical',
            'status': 'unknown' if value is None else 'verified', 'quote': str(value) if value is not None else None,
            'context': {'timepoint': 'Day 1 to Day 113', 'population': 'Safety population',
                'arm': 'Original arm', 'group_id': 'G1', 'stat_type': 'count_participants',
                'denominator': n, 'proportion': rate, 'term': term, 'num_events': events,
                'organ_system': 'Nervous system disorders' if term else None, 'threshold_pct': 0},
            'extracted_by': 'code:test'}))
    return db, pid, ids


def test_all_native_safety_facts_reach_shared_chart_query_and_complete_tables(settings):
    db, pid, ids = safety_project(settings)
    before = db.query('SELECT * FROM facts')
    data = data_b(db, pid)
    assert {r['id'] for r in data['results']} == set(ids)
    assert {r['id'] for r in data['safety']} == set(ids)
    plotted = {p['fact_id'] for g in data['charts']['groups'] for p in g['points']}
    assert plotted == set(ids[:-1]) and ids[-1] in data['plot_exclusions']
    assert data['study_catalog']['rows'][0]['result_count'] == len(ids)
    assert db.query('SELECT * FROM facts') == before


def test_native_severity_threshold_and_event_counts_do_not_merge_or_become_deaths(settings):
    db, pid, ids = safety_project(settings)
    data = data_b(db, pid)
    by_id = {r['id']: r for r in data['safety']}
    serious, other = by_id[ids[3]], by_id[ids[4]]
    assert serious['num_events'] == 5 and serious['value'] == 2 and serious['denominator'] == 10
    assert other['num_events'] == 2 and other['value'] == 1 and other['organ_system'] == 'Nervous system disorders'
    assert serious['safety_label'] != other['safety_label']
    figures = data['charts']['groups']
    assert len([g for g in figures if any(p['fact_id'] in ids[3:5] for p in g['points'])]) == 2
    summary = by_id[ids[2]]
    assert '0%' in summary['safety_label'] and '报告阈值' in summary['safety_label']
    html = render_report(db, pid, 'B')
    table = html.split('id="tbl-b-safety"', 1)[1].split('</table>', 1)[0]
    assert 'Headache' in table and '事件次数' in table and 'Nervous system disorders' in table
    assert serious['safety_label'] in table and other['safety_label'] in table
    assert table.count('全因死亡') == 1


def test_plot_metadata_preserves_zero_risk_denominator_and_exact_source_ids(settings):
    db, pid, ids = safety_project(settings)
    points = {p['fact_id']: p for g in data_b(db, pid)['charts']['groups'] for p in g['points']}
    zero = points[ids[0]]
    assert zero['value'] == 0 and zero['denominator'] == 10 and zero['proportion'] == 0
    assert points[ids[1]]['denominator'] == 0 and points[ids[1]]['proportion'] is None
    assert points[ids[3]]['value'] == 2 and points[ids[3]]['num_events'] == 5
    assert all(p['source_id'] for p in points.values())
