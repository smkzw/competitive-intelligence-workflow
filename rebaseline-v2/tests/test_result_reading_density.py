from ciw2.render.endpoint_label import endpoint_label
from ciw2.render.results import arm_label, result_groups


def test_explicit_response_title_is_compact_with_threshold_visit_and_population():
    raw = ('Percentage of Participants With >=75% Improvement in Eczema Area and Severity Index '
           '(EASI-75) at Week 16: ITT Population')
    label = endpoint_label(raw)
    assert label == 'EASI-75 · 改善≥75% · 受试者比例 · 第16周 · ITT人群'
    assert endpoint_label(raw.replace('ITT Population', 'Safety subset')) == raw.replace('ITT Population', 'Safety subset')
    assert endpoint_label(raw.replace('>=75%', '<50%')).startswith('EASI-75 · 改善<50%')


def test_explicit_period_prefix_is_shortened_but_source_arm_and_identity_are_unchanged():
    arm = 'Initial Treatment Period (Baseline - Week 16 Predose): Nemolizumab 30 mg'
    assert arm_label(arm) == '初始治疗期 · Nemolizumab 30 mg'
    assert arm_label('Unresolved: Arm A') == 'Unresolved: Arm A'
    rows = [{'id': f'f{i}', 'entity_id': f't{i}', 'entity': f'REG-{i}', 'source_id': f's{i}',
        'field': 'result.primary', 'endpoint': 'EASI', 'population': 'ITT', 'stat_type': 'mean',
        'unit': 'points', 'value': i, 'status': 'verified', 'arm': arm,
        'identity': {'axis_label': '药物甲 · III期'}, 'timepoint': 'Week 16'} for i in (1, 2)]
    groups, _ = result_groups(rows)
    points = groups[0]['points']
    assert len(points) == 2 and all('REG-' in p['axis_label'] for p in points)
    assert len({p['axis_label'] for p in points}) == 2
    assert all(p['arm'] == arm for p in points) and all(r['arm'] == arm for r in rows)
