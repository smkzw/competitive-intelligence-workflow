"""Normal regulatory prose: literal scientific type does not imply a company role."""
import pytest
from test_drug_enrichment import setup
from test_profile_review_regressions import stage

from ciw2.pipeline.stages import verify
from ciw2.verify.quote import check_quote


def current(settings,text,field,value):
    svc,rc,did=setup(settings)
    stage(rc,did,text,field,value)
    verify(rc)
    return next(f for f in svc.db.current_facts(rc.project_id,did) if f['field']==field)


def test_embedded_target_identifier_is_not_a_negative_clinical_count():
    text='ExampleDrug is a monoclonal antibody drug targeting IL-4Rα.'
    assert check_quote(text,text,'monoclonal antibody drug targeting IL-4Rα').ok
    assert not check_quote(text,text,-4).ok


@pytest.mark.parametrize('source,value',(
    ('The volume is 50mm3.','volume is 500mm3'),
    ('The scientific label is 2F9.','scientific label is 2F8'),
    ('The dose was 100mg.','dose was 10mg'),
))
def test_identifier_prose_fix_cannot_hide_invented_quantities_or_labels(source,value):
    assert not check_quote(source,source,value).ok


@pytest.mark.parametrize('count,expected',((10,True),(999,False)))
def test_literal_nested_type_does_not_bypass_a_separate_numeric_field(count,expected):
    kind='monoclonal antibody drug targeting IL-4Rα'
    text='ExampleDrug is a '+kind+'; 10 participants were enrolled.'
    assert check_quote(text,text,{'description':kind,'count':count}).ok is expected


def test_explicit_antibody_target_predicate_is_supported(settings):
    assert current(settings,'ExampleDrug is a monoclonal antibody drug targeting IL-4Rα.',
                   'identity.target','IL-4Rα')['status']=='verified'


@pytest.mark.parametrize('text',('ExampleDrug of ExampleCompany is approved by the regulator.',
    'ExampleDrug is manufactured by ExampleCompany.',
    'ExampleDrug is marketed by ExampleCompany.'))
def test_ownership_like_wording_is_not_a_developer_claim(settings,text):
    assert current(settings,text,'identity.developer','ExampleCompany')['status']=='unverified'


@pytest.mark.parametrize('text',('ExampleCompany developed ExampleDrug.',
    'ExampleDrug was developed by ExampleCompany.',
    'ExampleCompany宣布，公司自主研发的1类新药ExampleDrug正式上市。'))
def test_explicit_development_relationship_is_supported(settings,text):
    assert current(settings,text,'identity.developer','ExampleCompany')['status']=='verified'


@pytest.mark.parametrize('text',("ExampleCompany developed ExampleDrug's manufacturing process.",
    'ExampleCompany自主研发的ExampleDrug的生产工艺。'))
def test_process_development_is_not_product_development(settings,text):
    assert current(settings,text,'identity.developer','ExampleCompany')['status']=='unverified'


@pytest.mark.parametrize('label',('4-1BB','4‐1BB','4_1BB'))
def test_digit_segment_identifier_does_not_supply_a_clinical_count(label):
    text=f'{label} is a target.'
    assert not check_quote(text,text,4).ok
    assert check_quote(text,text,label).ok


@pytest.mark.parametrize('text',('The range is 10-20mg.','The range is 10-20mg/kg.'))
def test_numeric_range_endpoint_remains_numeric_evidence(text):
    assert check_quote(text,text,10).ok and check_quote(text,text,20).ok
