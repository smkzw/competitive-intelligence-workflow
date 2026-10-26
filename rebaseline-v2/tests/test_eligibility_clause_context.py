"""A threshold locator must not replace the actual eligibility clause."""
import pytest

from ciw2.render.eligibility import eligibility_reading
from ciw2.render.portal import render_report
from ciw2.service import Service


@pytest.mark.parametrize('text', [
    'Failure to achieve or maintain remission (equivalent to IGA ≤ 2) despite treatment.',
    ('Requirement of long-term treatment to achieve remission (IGA ≤ 2); '
     'documentation on failure to maintain remission (IGA ≤ 2) is also required.'),
])
def test_rendered_clause_keeps_full_context_primary_and_metrics_folded(settings, text):
    svc = Service(settings)
    pid = svc.create_project('特应性皮炎', ['C'])
    tid, _ = svc.db.upsert_entity(pid, 'trial', 'NCT00000001')
    criteria = 'Inclusion Criteria:\n' + text
    svc.db.add_fact({'project_id': pid, 'entity_id': tid, 'field': 'design.eligibility_criteria',
                     'value': criteria, 'quote': criteria, 'status': 'verified', 'tier': 'critical',
                     'extracted_by': 'code:test'})
    before = svc.db.current_facts(pid)
    page = render_report(svc.db, pid, 'C')
    clauses = page.split('<div class="criteria-clause">')[1:]
    assert len(clauses) == 2  # Table disclosure and full source reader.
    for clause in clauses:
        primary, metrics = clause.split('<details class="criteria-metrics">', 1)
        assert 'criteria-clause-original' in primary
        assert 'remission' in primary and 'treatment' in primary
        assert 'IGA 评分 ≤ 2' not in primary
        assert metrics.split('</details>', 1)[0].count('IGA 评分 ≤ 2') == 1
        assert '<summary>提取指标</summary>' in metrics
    assert svc.db.current_facts(pid) == before
    reading = eligibility_reading(criteria)
    assert ''.join(s['text'] for s in reading['segments']) == criteria
    assert any(s['emphasis'] == 'negation' and 'failure' in s['text'].lower()
               for s in reading['segments'])
