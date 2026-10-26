"""Literal official application rows must reach ordinary adoption and the A query."""
from copy import deepcopy

import pytest
from test_cde_classification_provenance import lookup

from ciw2.pipeline import cde_evidence
from ciw2.render.portal import data_a


def adopt(rc, monkeypatch):
    sid = rc.db.entities(rc.project_id, 'drug')[0]['attrs']['cde_acceptance_refs'][0]['source_id']
    monkeypatch.setattr(cde_evidence, '_directory', lambda *a: {'source_id': sid, 'results': []})
    return cde_evidence.collect(rc)


@pytest.mark.parametrize('kind,code,category', [
    ('治疗用生物制品', '1', 'innovative'), ('治疗用生物制品', '3.3', 'biosimilar'),
    ('化药', '1', 'innovative'), ('化药', '2.2', 'modified'), ('疫苗', '3.3', 'unknown'),
])
def test_ordinary_proven_row_reaches_scientific_fact_and_A_category(settings, monkeypatch, kind, code, category):
    rc = lookup(settings, monkeypatch, kind, code)
    original = deepcopy(rc.db.entities(rc.project_id, 'drug')[0])
    adopt(rc, monkeypatch)
    facts = rc.db.current_facts(rc.project_id)
    assert len(facts) == 1
    fact = facts[0]
    assert fact['field'] == 'identity.registration_class' and fact['value'] == code
    source = rc.db.one('SELECT * FROM sources WHERE id=?', (fact['source_id'],))
    text = rc.cas.get_text(source['text_digest'])
    assert text[fact['quote_start']:fact['quote_end']] == fact['quote']
    assert original['name'] in fact['quote'] and 'CXSL2600001' in fact['quote']
    assert fact['context']['json_path'] == '$.pages[0].rows[0][5]'
    assert fact['context']['drug_type'] == kind
    row = data_a(rc.db, rc.project_id)['rows'][0]
    assert row['classification']['category'] == category
    assert row['classification']['refs'][0]['fact_id'] == fact['id']
    assert row['china_mah'] == ''
    assert rc.db.entities(rc.project_id, 'drug')[0] == original
    assert not rc.llm.calls
    first = deepcopy(facts)
    adopt(rc, monkeypatch)
    assert rc.db.current_facts(rc.project_id) == first


def test_discovery_flags_and_changed_class_do_not_make_an_adopted_class(settings, monkeypatch):
    rc = lookup(settings, monkeypatch, '治疗用生物制品', '3.3')
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    refs = drug['attrs']['cde_acceptance_refs']
    refs[0]['registration_class'] = '1'
    rc.db.upsert_entity(rc.project_id, 'drug', drug['name'], attrs={
        'cde_acceptance_refs': refs, 'innovative': True})
    adopt(rc, monkeypatch)
    assert rc.db.current_facts(rc.project_id) == []
    row = data_a(rc.db, rc.project_id)['rows'][0]
    assert row['classification']['category'] == 'unknown'
    assert row['classification']['refs'] == []


@pytest.mark.parametrize('mutation', ['value', 'target', 'source', 'raw'])
def test_direct_adoption_rechecks_literal_binding_before_any_fact_write(settings, monkeypatch, mutation):
    from ciw2.sources.cde_adoption import adopt as literal_adopt
    from ciw2.sources.cde_review_browser import proven_acceptance_refs
    rc = lookup(settings, monkeypatch, '治疗用生物制品', '3.3')
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    rows = proven_acceptance_refs(rc.tool_ctx(), drug)
    target = drug['id']
    if mutation == 'value': rows[0]['registration_class'] = '1'
    if mutation == 'target': target = rc.db.upsert_entity(rc.project_id, 'drug', '其他药物')[0]
    if mutation == 'source': rows[0]['source_id'] = 'missing'
    if mutation == 'raw': rows[0]['raw_cells'][5] = '1'
    with pytest.raises(ValueError): literal_adopt(rc.tool_ctx(), target, rows)
    assert rc.db.current_facts(rc.project_id) == []


def test_presentation_keeps_modified_qualification_unknown_and_escapes_source_text(settings, monkeypatch):
    from ciw2.render.portal import render_report
    rc = lookup(settings, monkeypatch, '化药', '2.2')
    adopt(rc, monkeypatch)
    data = data_a(rc.db, rc.project_id)
    assert data['rows'][0]['classification']['core_membership'] is None
    html = render_report(rc.db, rc.project_id, 'A')
    assert 'id="competition-class"' in html and 'data-competition-class="modified"' in html
    assert '注册类别依据' in html and '改良型' in html
    assert 'CXSL2600001' in html and '原企业;' in html
    assert '已核核心' not in html


def test_conflicting_and_legacy_registration_observations_are_not_first_wins(settings, monkeypatch):
    from ciw2.render.registration import registrations
    rc = lookup(settings, monkeypatch, '治疗用生物制品', '1')
    adopt(rc, monkeypatch)
    fact = rc.db.current_facts(rc.project_id)[0]
    drug_id = fact['entity_id']
    changed = {k: v for k, v in fact.items() if k not in {'id', 'stored_status', 'created_at'}}
    changed['value'] = '3.3'
    changed['context'] = {**changed['context'], 'acceptance_number': 'CXSL2600002'}
    rc.db.add_fact(changed)
    result = registrations(rc.db, rc.project_id)[drug_id]
    assert result['category'] == 'unknown' and len(result['refs']) == 2
    rc.db.execute('DELETE FROM facts WHERE id<>?', (fact['id'],))
    ctx = {**fact['context'], 'handled_date_text': '2019-01-01'}
    import json
    rc.db.execute('UPDATE facts SET context=? WHERE id=?', (json.dumps(ctx), fact['id']))
    assert registrations(rc.db, rc.project_id)[drug_id]['category'] == 'unknown'


def test_category_and_text_filters_keep_A_chart_table_and_sources_in_one_query():
    from pathlib import Path

    from test_portal_js import run_portal
    run_portal((Path(__file__).parent / 'fixtures/registration-facets.js').read_text())
