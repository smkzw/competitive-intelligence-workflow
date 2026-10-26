"""Generic source-literal grammar and the approved molecular/mechanism split."""
import pytest
from test_drug_enrichment import setup

from ciw2.pipeline.stages import verify
from ciw2.render.drug_profile import drug_profiles
from ciw2.render.portal import data_a, render_report
from ciw2.sources.http import register_text


def checked(settings, text, field, value, *, name='ExampleDrug'):
    svc, rc, did = setup(settings)
    svc.db.execute('UPDATE entities SET name=? WHERE id=?', (name, did))
    url = 'https://example.org/source-literal-grammar'
    sid = register_text(rc.tool_ctx(), kind='company', url=url, text=text)
    rc.db.set_stage(rc.run_id, 'enrich_drugs', 'succeeded', output={'facts': [{
        'entity': name, 'drug': name, 'drug_entity_id': did, 'field': field, 'value': value,
        'source_id': sid, 'source_url': url, 'quote': text}]})
    verify(rc)
    fact = next(f for f in svc.db.current_facts(rc.project_id, did) if f['field'] == field)
    return svc, rc, did, fact


@pytest.mark.parametrize('text,field,value', [
    ('A trial of the oral Factor D (FD) inhibitor ExampleDrug.', 'identity.target', 'Factor D (FD)'),
    ('ExampleDrug, a small protein complement C5 inhibitor which binds C5.', 'identity.target', 'complement C5'),
    ('ExampleDrug, a Small Interfering RNA (siRNA) Targeting Complement Factor B.', 'identity.target', 'Complement Factor B'),
    ('ExampleDrug is an investigational siRNA therapy designed to selectively cleave complement factor B (CFB).',
        'identity.target', 'complement factor B (CFB)'),
    ('The recombinant protein ExampleDrug has been studied.', 'identity.modality', 'recombinant protein'),
    ('ExampleDrug, a Small Interfering RNA (siRNA) Targeting Complement Factor B.',
        'identity.modality', 'Small Interfering RNA (siRNA)'),
    ('ExampleDrug, a small protein complement C5 inhibitor.', 'identity.modality', 'small protein'),
    ('ExampleCompany is developing a novel peptidic complement inhibitor ExampleDrug.',
        'identity.developer', 'ExampleCompany'),
    ('ExampleDrug is being developed by ExampleCompany.', 'identity.developer', 'ExampleCompany'),
    ('ExampleCompany is co-developing ExampleDrug.', 'identity.developer', 'ExampleCompany'),
    ('The Factor D inhibitor ExampleDrug is in clinical study.', 'identity.mechanism_class', 'Factor D inhibitor'),
    ('ExampleDrug, a PEGylated C3 inhibitor, has been studied.', 'identity.mechanism_class', 'C3 inhibitor'),
])
def test_explicit_noun_or_development_relations_are_source_supported(settings, text, field, value):
    _, _, _, fact = checked(settings, text, field, value)
    assert fact['status'] == 'verified'


@pytest.mark.parametrize('text,field,value', [
    ('Unlike ExampleDrug, OtherDrug is a Factor D inhibitor.', 'identity.target', 'Factor D'),
    ('OtherDrug, a C5 inhibitor, was co-administered with ExampleDrug.', 'identity.target', 'C5'),
    ('ExampleDrug was compared with a Factor D inhibitor.', 'identity.target', 'Factor D'),
    ('ExampleDrug, a comparator of OtherDrug which targets C5.', 'identity.target', 'C5'),
    ('ExampleDrug is not a Factor D inhibitor.', 'identity.target', 'Factor D'),
    ('ExampleDrug, an unrelated comparator, was combined with an RNA drug.', 'identity.modality', 'RNA'),
    ('ExampleCompany is developing manufacturing capacity for ExampleDrug.', 'identity.developer', 'ExampleCompany'),
    ('ExampleCompany is developing a protein manufacturing process for ExampleDrug.', 'identity.developer', 'ExampleCompany'),
    ("ExampleCompany's partner is developing ExampleDrug.", 'identity.developer', 'ExampleCompany'),
    ("ExampleDrug is being developed by ExampleCompany's partner.", 'identity.developer', 'ExampleCompany'),
    ('ExampleCompany is the lead sponsor of a trial of ExampleDrug.', 'identity.developer', 'ExampleCompany'),
    ('ExampleCompany markets ExampleDrug.', 'identity.developer', 'ExampleCompany'),
    ('ExampleCompany is not developing ExampleDrug.', 'identity.developer', 'ExampleCompany'),
    ('{"organization":"ExampleCompany is developing","drug":"ExampleDrug"}',
        'identity.developer', 'ExampleCompany'),
    ('{"class":"a C5 inhibitor","drug":"ExampleDrug"}', 'identity.target', 'C5'),
    ('ExampleDrug is a C5 inhibitor.', 'identity.modality', 'C5 inhibitor'),
    ('ExampleDrug is a PEGylated C3 inhibitor.', 'identity.modality', 'PEGylated C3 inhibitor'),
    ('ExampleDrug is a protein kinase inhibitor.', 'identity.modality', 'protein'),
    ('ExampleDrug is a small molecule.', 'identity.mechanism_class', 'small molecule'),
    ('ExampleDrug is a monoclonal antibody.', 'identity.mechanism_class', 'monoclonal antibody'),
])
def test_wrong_subject_role_type_or_json_adjacency_is_not_adopted(settings, text, field, value):
    _, _, _, fact = checked(settings, text, field, value)
    assert fact['status'] == 'unverified'


@pytest.mark.parametrize('dash', ['\u2010', '\u2011', '\u2012', '\u2013', '\u00ad'])
def test_source_identifier_dash_matches_quote_normalization_without_merging_entity(settings, dash):
    name = 'APL-2'
    text = f'APL{dash}2 is a monoclonal antibody drug targeting C3.'
    svc, rc, did, fact = checked(settings, text, 'identity.target', 'C3', name=name)
    assert fact['status'] == 'verified'
    assert svc.db.entities(rc.project_id, 'drug')[0]['name'] == name
    assert fact['quote'] == text and fact['entity_id'] == did


@pytest.mark.parametrize('source_name', ['APL-20', 'APL2', 'APL 2', 'APL-2-like'])
def test_dash_normalization_never_strips_or_shortens_an_identifier(settings, source_name):
    text = f'{source_name} is a monoclonal antibody drug targeting C3.'
    _, _, _, fact = checked(settings, text, 'identity.target', 'C3', name='APL-2')
    assert fact['status'] == 'unverified'


def test_one_source_can_support_separate_type_and_mechanism_facts_without_source_changes(settings):
    svc, rc, did = setup(settings)
    text = 'ExampleDrug is a small molecule. ExampleDrug is a C5 inhibitor.'
    url = 'https://example.org/separate-source-claims'
    sid = register_text(rc.tool_ctx(), kind='company', url=url, text=text)
    pairs = [('identity.modality', 'small molecule', 'ExampleDrug is a small molecule.'),
             ('identity.mechanism_class', 'C5 inhibitor', 'ExampleDrug is a C5 inhibitor.')]
    rc.db.set_stage(rc.run_id, 'enrich_drugs', 'succeeded', output={'facts': [{
        'entity': 'ExampleDrug', 'drug': 'ExampleDrug', 'drug_entity_id': did, 'field': field,
        'value': value, 'source_id': sid, 'source_url': url, 'quote': quote}
        for field, value, quote in pairs]})
    source_before = svc.db.one('SELECT * FROM sources WHERE id=?', (sid,))
    verify(rc)
    profile = drug_profiles(svc.db, rc.project_id)[did]
    assert profile['molecular_types'] == ['small molecule']
    assert profile['mechanism_classes'] == ['C5 inhibitor']
    assert {r['source_id'] for r in profile['profile_refs']} == {sid}
    row = data_a(svc.db, rc.project_id)['rows'][0]
    assert row['molecular_types'] == ['small molecule'] and row['mechanism_classes'] == ['C5 inhibitor']
    html = render_report(svc.db, rc.project_id, 'A')
    assert '<th>分子类型</th>' in html and '<th>机制类别</th>' in html
    facts_before = svc.db.query('SELECT * FROM facts')
    assert verify(rc)['replayed'] == 2 and svc.db.query('SELECT * FROM facts') == facts_before
    assert svc.db.one('SELECT * FROM sources WHERE id=?', (sid,)) == source_before


@pytest.mark.parametrize('text,field,value,status',[
    ('Pegcetacoplan (APL‐2), a PEGylated C3 inhibitor, has been studied.','identity.target','C3','verified'),
    ('AMYNDAS is developing a novel peptidic complement inhibitor APL-2.','identity.modality','peptidic','verified'),
    ('OtherDrug (compared with APL-2), a C3 inhibitor, has been studied.','identity.target','C3','unverified'),
    ('OtherDrug (unlike APL-2), a C3 inhibitor, has been studied.','identity.target','C3','unverified'),
])
def test_alias_apposition_or_atomic_type_remains_subject_bound(settings,text,field,value,status):
    _,_,_,fact=checked(settings,text,field,value,name='APL-2')
    assert fact['status']==status


def test_legacy_mixed_class_stays_in_history_without_becoming_a_molecular_type(settings):
    svc,rc,did=setup(settings)
    text='ExampleDrug is a C5 inhibitor.'
    sid=register_text(rc.tool_ctx(),kind='company',url='https://example.org/legacy-class',text=text)
    fid=svc.db.add_fact({'project_id':rc.project_id,'entity_id':did,'field':'identity.modality',
        'value':'C5 inhibitor','source_id':sid,'quote':text,'status':'verified','tier':'standard',
        'extracted_by':'code:legacy-fixture','context':{}})
    before=svc.db.query('SELECT * FROM facts')
    profile=drug_profiles(svc.db,rc.project_id)[did]
    assert profile['molecular_types']==[] and profile['mechanism_classes']==[]
    ref=next(r for r in profile['profile_refs'] if r['fact_id']==fid)
    assert ref['field']=='identity.modality' and ref['value']=='C5 inhibitor'
    assert ref['role']=='历史分类原文'
    assert svc.db.query('SELECT * FROM facts')==before


@pytest.mark.parametrize('text,field,value,status',[
    ('ExampleDrug targets C5.','identity.target','C5','verified'),
    ('ExampleDrug targets C5-mediated hemolysis.','identity.target','C5','unverified'),
    ('ExampleDrug targets Factor D-related pathways.','identity.target','Factor D','unverified'),
    ('ExampleDrug is a protein.','identity.modality','protein','verified'),
    ('ExampleDrug is a protein-binding inhibitor.','identity.modality','protein','unverified'),
    ('ExampleDrug is a protein kinase inhibitor.','identity.modality','protein','unverified'),
    ('ExampleDrug binds C5.','identity.target','C5','verified'),
    ('ExampleDrug binds to C5.','identity.target','C5','verified'),
    ('ExampleDrug inhibits Factor D.','identity.target','Factor D','verified'),
    ('OtherDrug binds to C5, with ExampleDrug as comparator.','identity.target','C5','unverified'),
    ('ExampleDrug does not inhibit Factor D.','identity.target','Factor D','unverified'),
])
def test_independent_review_value_and_relation_counterexamples(settings,text,field,value,status):
    _,_,_,fact=checked(settings,text,field,value)
    assert fact['status']==status


def test_profile_projection_uses_current_receipt_not_only_stored_status(settings,monkeypatch):
    from ciw2.pipeline.requalify import requalify_project
    from ciw2.verify import assessment
    svc,rc,did,fact=checked(settings,'ExampleDrug targets C5.','identity.target','C5')
    assert drug_profiles(svc.db,rc.project_id)[did]['targets']==['C5']
    stored=svc.db.one('SELECT * FROM facts WHERE id=?',(fact['id'],))
    monkeypatch.setattr(assessment,'_RULE','quote-synthetic-next-rule')
    assert drug_profiles(svc.db,rc.project_id)[did]['targets']==[]
    assert next(r for r in data_a(svc.db,rc.project_id)['rows'] if r['id']==did)['targets']==[]
    assert svc.db.one('SELECT * FROM facts WHERE id=?',(fact['id'],))==stored
    assert requalify_project(svc.db,svc.cas,rc.project_id)['counts']['confirmed']==1
    assert drug_profiles(svc.db,rc.project_id)[did]['targets']==['C5']
    assert svc.db.one('SELECT * FROM facts WHERE id=?',(fact['id'],))==stored
