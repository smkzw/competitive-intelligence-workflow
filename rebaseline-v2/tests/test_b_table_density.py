"""B identity remains clinical; only repeated registry/source metadata is folded."""
from html.parser import HTMLParser
from pathlib import Path

import pytest
from test_portal_js import run_portal
from test_result_arm_identity import arm, drug, result
from test_result_arm_identity import workspace as workspace  # noqa: PLC0414
from test_trial_reading_identity import identity_project as identity_project  # noqa: PLC0414

from ciw2.render.portal import data_b, render_report


class CompactIdentities(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.current = None
        self.record = False
        self.items = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'div' and 'trial-identity-compact' in a.get('class', '').split():
            self.current = {'reading': [], 'record': []}
            self.depth = 0
            self.record = False
        if self.current is not None:
            if tag == 'div': self.depth += 1
            if tag == 'details' and a.get('class') == 'trial-record': self.record = True

    def handle_endtag(self, tag):
        if self.current is not None and tag == 'div':
            self.depth -= 1
            if self.depth == 0:
                self.items.append(self.current)
                self.current = None

    def handle_data(self, text):
        if self.current is not None:
            self.current['record' if self.record else 'reading'].append(text)


def test_both_b_consumers_keep_clinical_identity_and_role_visible_while_folding_record(identity_project):
    svc, pid, tid, _, sid = identity_project
    for field in ['result.primary.value', 'safety.sae.any']:
        svc.db.add_fact({'project_id': pid, 'entity_id': tid, 'source_id': sid, 'field': field,
            'value': 0, 'tier': 'critical', 'status': 'verified', 'extracted_by': 'code:ctgov',
            'quote': '0', 'context': {'arm': 'Source arm', 'endpoint': 'Score',
                'timepoint': 'Week 16', 'population': 'ITT', 'stat_type': 'count_participants',
                'denominator': 10, 'unit': 'participants'}})
    before = svc.db.query('SELECT * FROM facts')
    cells = CompactIdentities()
    cells.feed(render_report(svc.db, pid, 'B'))
    data = data_b(svc.db, pid)
    assert len(cells.items) == len(data['results']) + len(data['safety']) >= 3
    for item in cells.items:
        reading, record = ''.join(item['reading']), ''.join(item['record'])
        assert '奈莫利珠单抗' in reading and '特应性皮炎' in reading and 'III 期' in reading
        assert '申办方' in reading and 'Source Sponsor Ltd.' in reading
        assert 'NCT03985943' not in reading and 'NCT03985943' in record
        assert 'Atopic Dermatitis' in record and 'https://' not in reading
        assert 'Unverified Holder' not in reading and 'Guessed Group' not in reading
    assert 'trial-identity-compact' not in render_report(svc.db, pid, 'C')
    assert svc.db.query('SELECT * FROM facts') == before


@pytest.mark.parametrize('resolved', [False, True])
def test_b_arm_drug_column_uses_actual_binding_not_the_trial_drug(workspace, resolved):
    drug(workspace, 'Alpha')
    if resolved: arm(workspace, 'Arm A', ['Drug: Alpha'])
    result(workspace, 'Arm A')
    html = render_report(workspace[0], workspace[1], 'B')
    assert 'data-arm-drug-column' in html
    assert f'data-arm-drug="{"known" if resolved else "unknown"}"' in html


def test_empty_arm_drug_column_follows_each_consumers_visible_query_and_restores():
    run_portal((Path(__file__).parent / 'fixtures/b-empty-drug-column.js').read_text())
