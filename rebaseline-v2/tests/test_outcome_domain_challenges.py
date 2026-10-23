"""Owner source-domain counterexamples from independent frozen review."""
import pytest

from ciw2.domain.outcomes import classify_outcome_domain


@pytest.mark.parametrize('title,description,expected',[
    ('Area Under the Receiver Operating Characteristic Curve (AUC)',None,'unresolved'),
    ('AUC','Area under the receiver operating characteristic curve','unresolved'),
    ('Serum Antibody Levels in Participants With Rheumatoid Arthritis',None,'unresolved'),
    ('Serum Endogenous Erythropoetin Concentrations',None,'unresolved'),
    ('Serum trough levels',None,'unresolved'),
    ('Serum Concentrations in Participants Receiving Nemolizumab',None,'unresolved'),
    ('Nemolizumab Serum Concentrations',None,'unresolved'),
    ('Incidence of Adenosine Deaminase (ADA) Deficiency',None,'unresolved'),
    ('ADA Incidence','Incidence of adenosine deaminase deficiency','unresolved'),
    ('ADA Incidence',None,'unresolved'),
    ('ADA Incidence','Incidence of anti-drug antibodies (ADA)','immunogenicity'),
    ('Bovine Serum Albumin (BSA) Concentration',None,'unresolved'),
    ('Overall Survival: Time From Randomization to Death From Any Cause',None,'clinical'),
    ('Progression-Free Survival',None,'clinical'),
    ('All-cause mortality',None,'unresolved'),
    ('PK/PD Relationship Between Serum Concentration and Clinical Response',None,'unresolved'),
    ('PK/PD Relationship Between Receptor Occupancy and EASI Score',None,'unresolved'),
    ('Change From Baseline','Participants receive nemolizumab; serum concentrations are also monitored.','unresolved'),
])
def test_source_expansion_and_measured_target_precede_generic_cues(title,description,expected):
    assert classify_outcome_domain(title,description)==expected


def test_explicit_source_drug_analyte_binding_not_name_morphology():
    assert classify_outcome_domain('Nemolizumab Serum Concentrations',drug_names=['Nemolizumab'])=='pk'
    assert classify_outcome_domain('Serum Concentrations of CBP-201',drug_names=['CBP-201'])=='pk'
    assert classify_outcome_domain('Serum Concentrations of ABC-1',drug_names=['ABC-10'])=='unresolved'
    assert classify_outcome_domain('Serum Concentrations in Participants Receiving Nemolizumab',
        drug_names=['Nemolizumab'])=='unresolved'
    assert classify_outcome_domain('Serum Concentrations of IgE in Participants Receiving Nemolizumab',
        drug_names=['Nemolizumab'])=='biomarker'
