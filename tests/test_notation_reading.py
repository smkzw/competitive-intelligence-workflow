"""A scientific expression need not contain a Chinese character; English prose still needs translation."""
import pytest

from ciw.verify.design_labels import _atoms, _check


def valid(source,label):
    c=dict(rows=[dict(design_excerpts=[dict(snippets=[dict(text=source,source_id='synthetic',field='eligibility')])])])
    atoms=_atoms(c)
    key=next(iter(atoms))
    item=dict(clause_id=key,quote=source,text_zh=label,condition_zh='',cohort_zh='',timeframe_zh='')
    return _check(item,atoms)[0]


@pytest.mark.parametrize('source,label',[
    ('eGFR≥45ml/min/1.73m2','eGFR≥45ml/min/1.73m2。'),
    ('eGFR greater than or equal to 30 mL/min/1.73 m2','eGFR ≥30 mL/min/1.73 m2'),
    ('UPCR greater than 3.0 g/g','UPCR >3.0 g/g'),
])
def test_equivalent_metric_threshold_unit_expression_does_not_need_filler_chinese(source,label):
    assert valid(source,label)


@pytest.mark.parametrize('source,label',[
    ('At screening, eGFR ≥45 mL/min/1.73 m2.','eGFR ≥45 mL/min/1.73 m2'),
    ('Participants must have a biopsy confirming diagnosis.','Participants must have a biopsy confirming diagnosis.'),
    ('eGFR greater than or equal to 30 mL/min/1.73 m2','ALT ≥30 mL/min/1.73 m2'),
    ('eGFR greater than or equal to 30 mL/min/1.73 m2','EGFR ≥30 mL/min/1.73 m2'),
    ('eGFR greater than or equal to 30 mL/min/1.73 m2','eGFR >30 mL/min/1.73 m2'),
    ('eGFR ≥30 mL/min/1.73 m2 at screening','eGFR ≥30 mL/min/1.73 m2'),
    ('Patients have eGFR greater than or equal to 30 mL/min/1.73 m2',
     'Patients have eGFR greater than or equal to 30 mL/min/1.73 m2'),
])
def test_notation_exception_cannot_drop_prose_change_identity_case_or_threshold(source,label):
    assert not valid(source,label)
