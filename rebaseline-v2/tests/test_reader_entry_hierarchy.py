"""Default report hierarchy favors short findings over full source-backed detail."""
from html.parser import HTMLParser

import pytest
import test_m1_design
import test_trial_reading_identity

from ciw2.render.portal import render_report


@pytest.fixture
def identity_project(settings, study):
    return test_trial_reading_identity.identity_project.__wrapped__(settings, study)


@pytest.fixture
def design_project(settings):
    return test_m1_design.design_project.__wrapped__(settings)


@pytest.mark.parametrize('report', ['A', 'B', 'C'])
def test_findings_precede_complete_comparison_for_each_portal(identity_project, report):
    svc, pid, trial, _, _ = identity_project
    fact = next(f for f in svc.db.current_facts(pid)
                if f['entity_id'] == trial and f['field'] == 'design.primary_endpoint')
    summary = {'report': report, 'findings': [{'title': '主要观察', 'bullets': ['第16周评估'],
                                            'fact_refs': [fact['id']]}]}
    html = render_report(svc.db, pid, report, findings=summary)
    assert html.index('id="findings"') < html.index('id="comparison"')
    assert 'id="findings"' not in render_report(svc.db, pid, report)


class RegionReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details_depth = 0
        self.regions = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details':
            self.details_depth += 1
        if tag == 'span' and attrs.get('class') == 'region-name':
            self.regions.append((attrs.get('data-original-value'), self.details_depth))

    def handle_endtag(self, tag):
        if tag == 'details':
            self.details_depth -= 1


@pytest.mark.parametrize('countries', [
    ['China', 'Hong Kong', 'Taiwan', 'United States', 'France'],
    ['United States', 'France', 'Germany', 'Belgium'],
])
def test_long_region_list_is_reachable_but_not_a_default_wall(design_project, countries):
    db, pid, _, _ = design_project
    test_m1_design.add_fact(design_project, 'trial.countries', countries, locations_complete=True)
    before = db.current_facts(pid)
    html = render_report(db, pid, 'C')
    reader = RegionReader()
    reader.feed(html)
    assert {name for name, _ in reader.regions} == set(countries)
    assert all(depth > 0 for _, depth in reader.regions)
    assert db.current_facts(pid) == before
