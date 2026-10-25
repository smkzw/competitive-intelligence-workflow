"""The default summary view must identify its source study without opening details."""
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
import test_trial_reading_identity

from ciw2.render.portal import render_report


@pytest.fixture
def identity_project(settings, study):
    return test_trial_reading_identity.identity_project.__wrapped__(settings, study)


class VisibleSummary(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.details = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'section' and dict(attrs).get('id') == 'findings':
            self.active = True
        if self.active and tag == 'details':
            self.details += 1

    def handle_endtag(self, tag):
        if self.active and tag == 'details':
            self.details -= 1
        if tag == 'section':
            self.active = False

    def handle_data(self, data):
        if self.active and not self.details:
            self.text.append(data)


def test_default_summary_has_source_identity_even_when_model_title_is_only_a_clinical_topic(identity_project):
    svc, pid, trial, _, _ = identity_project
    fact = next(f for f in svc.db.current_facts(pid)
                if f['entity_id'] == trial and f['field'] == 'design.primary_endpoint')
    summary = {'report': 'C', 'findings': [{'title': '主要终点与时间窗',
               'bullets': ['第16周主要终点'], 'fact_refs': [fact['id']]}]}
    parser = VisibleSummary()
    parser.feed(render_report(svc.db, pid, 'C', findings=summary))
    visible = ' '.join(parser.text)
    for term in ('奈莫利珠单抗', 'III 期', '特应性皮炎', '申办方', 'Source Sponsor Ltd.'):
        assert term in visible
    assert 'Unverified Holder' not in visible and 'Guessed Group' not in visible


def test_design_visible_window_ignores_offscreen_labels_and_reflows_after_zoom():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['node', str(root / 'tests/fixtures/design-visible-window.js'),
                    str(root / 'src/ciw2/render/static/portal.js')],
                   check=True, capture_output=True, text=True)
