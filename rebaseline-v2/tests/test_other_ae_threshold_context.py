"""Source-module thresholds stay attached to each reported nonserious AE term."""
import pytest

from ciw2.render.results import result_groups
from ciw2.render.safety import safety_label
from ciw2.sources.ctgov import ae_facts


@pytest.mark.parametrize('threshold', ['5', '0', 0, None])
def test_nonserious_terms_preserve_source_report_threshold_not_per_arm_cutoff(threshold):
    module = {'frequencyThreshold': threshold, 'timeFrame': '16 weeks', 'description': 'Safety set',
        'eventGroups': [{'id': 'EG000', 'title': 'Original placebo'}],
        'otherEvents': [{'term': 'COVID-19', 'organSystem': 'Infections and infestations',
            'stats': [{'groupId': 'EG000', 'numAffected': 6, 'numAtRisk': 321}]}],
        'seriousEvents': [{'term': 'COVID-19', 'organSystem': 'Infections and infestations',
            'stats': [{'groupId': 'EG000', 'numAffected': 1, 'numAtRisk': 321, 'numEvents': 2}]}]}
    facts = ae_facts({'resultsSection': {'adverseEventsModule': module}})
    term = next(f for f in facts if f['field'] == 'safety.ae.term')
    assert term['value'] == 6 and term['context']['proportion'] == 1.9
    assert term['context'].get('threshold_pct') == threshold
    assert term['context']['denominator'] == 321 and 'num_events' not in term['context']
    label = safety_label({'field': term['field'], **term['context']})
    if threshold is not None:
        assert f'报告阈值 {threshold}%' in label
    else:
        assert '报告阈值' not in label
    assert all('threshold_pct' not in f['context'] for f in facts
               if f['field'] in {'safety.sae.term', 'safety.sae.any', 'safety.death.all_cause'})


def test_thresholds_separate_numeric_frames_without_changing_source_counts():
    rows = [{'id': f'f{i}', 'field': 'safety.ae.term', 'entity_id': 'trial', 'source_id': 'source',
        'endpoint': 'COVID-19', 'term': 'COVID-19', 'organ_system': 'Infections and infestations',
        'timepoint': '16 weeks', 'population': 'Safety set', 'unit': 'participants',
        'stat_type': 'count_participants', 'value': 6, 'denominator': 321, 'status': 'verified',
        'domain': 'safety', 'arm': 'Original placebo', 'threshold_pct': threshold}
        for i, threshold in enumerate(('5', '0'))]
    groups, excluded = result_groups(rows)
    assert len(groups) == 2 and not excluded
    assert {p['value'] for g in groups for p in g['points']} == {6}
    assert {g['label'] for g in groups} == {'其他AE（报告阈值 5%） · COVID-19', '其他AE（报告阈值 0%） · COVID-19'}
