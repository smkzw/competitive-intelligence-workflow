import copy
import json

from ciw2.harness.tools import ToolContext
from ciw2.sources import ctgov


def test_discovery_deduplicates_names_without_losing_trials_or_seventh_intervention(study, monkeypatch):
    parsed = ctgov.parse_study(study)
    parsed['interventions'] = [{'name': f'Drug {i}', 'type': 'DRUG', 'other_names': []} for i in range(7)]
    rows = [{**parsed, 'nct': f'NCT{i:08d}'} for i in range(150)]
    monkeypatch.setattr(ctgov, 'search', lambda *a, **kw: rows)
    result = ctgov._ctgov_search(ToolContext(), ctgov.SearchArgs(condition='test', route_id='test'))
    assert result['count'] == 150
    assert len(result['interventions']) == 7
    assert all(len(i['trials']) == 150 for i in result['interventions'])
    assert len({s['nct'] for s in result['studies']}) == 150
    assert len(json.dumps(result, ensure_ascii=False)) < 60000


def test_get_design_does_not_silently_cut_eligibility(study, monkeypatch):
    data = copy.deepcopy(study)
    original = 'Inclusion Criteria:\n' + 'criterion; ' * 500 + '\nExclusion Criteria: important final criterion'
    data['protocolSection']['eligibilityModule']['eligibilityCriteria'] = original
    monkeypatch.setattr(ctgov, 'get_study', lambda *a, **kw: (data, None))
    result = ctgov._ctgov_get(ToolContext(), ctgov.GetArgs(nct='NCT03985943'))
    assert result['eligibility']['criteria'] == original
