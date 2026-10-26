from html.parser import HTMLParser

from test_native_safety_readout import safety_project

from ciw2.render.portal import data_b, render_report


def test_both_safety_consumers_use_one_escaped_source_complete_search_document(settings):
    db, pid, ids = safety_project(settings)
    data = data_b(db, pid)
    row = next(r for r in data['results'] if r['id'] == ids[3])
    assert 'Nervous system disorders' in row['search_text']
    assert 'Headache' in row['search_text'] and 'Safety population' in row['search_text']
    assert ids[3] not in row['search_text']

    class Rows(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'tr':
                self.rows.append(dict(attrs))
    parser = Rows()
    parser.rows = []
    parser.feed(render_report(db, pid, 'B'))
    matches = [r for r in parser.rows if r.get('data-fact-id') == ids[3]]
    assert len(matches) == 2
    assert all(r['data-search-text'] == row['search_text'] for r in matches)
