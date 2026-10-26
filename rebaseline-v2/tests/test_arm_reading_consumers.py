"""The production B chart and both table consumers share source-preserving arm reading."""
from html.parser import HTMLParser

import pytest
from test_result_presentation import project

from ciw2.render.portal import data_b, render_report


class ArmCells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.table = self.fact = None
        self.column = self.depth = 0
        self.capture = self.summary = False
        self.cells = {}
        self.images = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'table': self.table = a.get('id')
        if tag == 'tr': self.fact, self.column = a.get('data-fact-id'), 0
        if tag == 'td':
            self.capture = bool(self.fact and (self.table == 'tbl-b' and a.get('class') == 'result-arm'
                                or self.table == 'tbl-b-safety' and self.column == 2))
            self.column += 1
            if self.capture:
                self.depth = 0
                self.cells[self.table, self.fact] = {'visible': [], 'full': [], 'folds': 0}
        if self.capture:
            if tag == 'details':
                self.depth += 1
                self.cells[self.table, self.fact]['folds'] += 1
            if tag == 'summary': self.summary = True
            if tag == 'img': self.images.append(a)

    def handle_endtag(self, tag):
        if self.capture and tag == 'details': self.depth -= 1
        if tag == 'summary': self.summary = False
        if tag == 'td': self.capture = False
        if tag == 'tr': self.fact = None
        if tag == 'table': self.table = None

    def handle_data(self, text):
        if self.capture:
            cell = self.cells[self.table, self.fact]
            cell['full'].append(text)
            if self.depth == 0 or self.summary: cell['visible'].append(text)


def source_pair(settings, arm):
    db, pid, ids = project(settings, [{'context': {'arm': arm}, 'value': 0}])
    tid = db.entities(pid, 'trial')[0]['id']
    sid = db.query('SELECT id FROM sources WHERE project_id=?', (pid,))[0]['id']
    ids.append(db.add_fact({'project_id': pid, 'entity_id': tid, 'source_id': sid,
        'field': 'safety.sae.any', 'value': 0, 'tier': 'critical', 'status': 'verified',
        'quote': '0', 'context': {'arm': arm, 'group_id': 'G1', 'denominator': 10,
            'timepoint': 'Week 16', 'stat_type': 'count_participants'}, 'extracted_by': 'code:test'}))
    return db, pid, ids


@pytest.mark.parametrize('arm,expected', [
    ('Initial Treatment Period (Baseline - Week 16 Predose): Study drug 30 mg', '初始治疗期 · Study drug 30 mg'),
    ('Maintenance Period (Week 16-Week 48): Study drug 30 mg Q4W to Q8W', '维持治疗期（第16–48周） · Study drug 30 mg Q4W to Q8W'),
    ('Cohort 1: Participants Aged 7-11 Years', '队列1（7–11岁）'),
])
def test_known_arm_reading_is_identical_in_graph_and_both_closed_table_cells(settings, arm, expected):
    db, pid, ids = source_pair(settings, arm)
    before = db.query('SELECT * FROM facts')
    data = data_b(db, pid)
    points = {p['fact_id']: p for g in data['charts']['groups'] for p in g['points']}
    cells = ArmCells()
    cells.feed(render_report(db, pid, 'B'))
    for table, fid in [('tbl-b', ids[0]), ('tbl-b', ids[1]), ('tbl-b-safety', ids[1])]:
        cell = cells.cells[table, fid]
        assert ''.join(cell['visible']).strip() == points[fid]['arm_label'] == expected
        assert arm in ''.join(cell['full']) and cell['folds'] == 1
    assert all(points[fid]['value'] == 0 for fid in ids)
    assert db.query('SELECT * FROM facts') == before


@pytest.mark.parametrize('arm', ['Unknown original arm with unchanged qualifiers',
    'Maintenance Period: Week 16 or 48 by investigator choice',
    'Initial Treatment Period (Baseline - Week 16 Predose): <img src=x onerror=alert(1)> & drug'])
def test_unparsed_arm_is_not_rewritten_and_source_text_is_never_html(settings, arm):
    db, pid, ids = source_pair(settings, arm)
    cells = ArmCells()
    cells.feed(render_report(db, pid, 'B'))
    for table in ['tbl-b', 'tbl-b-safety']:
        cell = cells.cells[table, ids[1]]
        assert arm in ''.join(cell['full'])
        if not arm.startswith('Initial Treatment Period ('):
            assert ''.join(cell['visible']).strip() == arm
    assert cells.images == []
