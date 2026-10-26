"""A shared source window is not a per-point axis paragraph."""
from ciw2.render.results import result_groups


def test_long_shared_window_remains_original_but_is_not_a_compact_visit():
    window = 'Initial treatment: baseline to Week 16; maintenance: Week 16 to Week 48.'
    row = {'id': 'f1', 'entity_id': 'trial', 'source_id': 'source', 'field': 'safety.ae.term',
        'endpoint': 'Source event', 'arm': 'Original arm', 'timepoint': window,
        'population': 'Safety set', 'stat_type': 'count_participants', 'unit': 'participants',
        'value': 6, 'status': 'verified', 'domain': 'safety'}
    group = result_groups([row])[0][0]
    point = group['points'][0]
    assert point['visit'] == window and point['visit_short'] == ''
    assert group['subtitle'] == window and group['kind'] == 'bar'
    row['timepoint'] = 'Week 16'
    assert result_groups([row])[0][0]['points'][0]['visit_short'] == '第16周'
