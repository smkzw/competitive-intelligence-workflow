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
