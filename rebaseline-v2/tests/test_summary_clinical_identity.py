"""Reduction must retain source-backed clinical identity, not just opaque references."""
import pytest
import test_trial_reading_identity


@pytest.fixture
def identity_project(settings, study):
    return test_trial_reading_identity.identity_project.__wrapped__(settings, study)

from ciw2.pipeline.summary_lineage import summary_basis


def test_reduction_transports_the_existing_source_backed_trial_identity(identity_project):
    svc, pid, trial, _, _ = identity_project
    rc = svc.context(pid, svc.db.create_run(pid))
    fact = next(f for f in svc.db.current_facts(pid)
                if f['entity_id'] == trial and f['field'] == 'design.primary_endpoint')
    before = svc.db.raw_current_facts(pid)
    original = [{'title': 'NCT03985943', 'bullets': ['第16周终点'], 'fact_refs': [fact['id']]}]
    projected, refs, _ = summary_basis(rc, original, {fact['id']})
    study = projected[0]['studies'][0]
    assert study['registry_id'] == 'NCT03985943'
    assert study['drug_label'] == '奈莫利珠单抗'
    assert study['indication'] == '特应性皮炎'
    assert study['phase_label'] == 'III 期'
    assert study['companies'] == [{'role': '申办方', 'name': 'Source Sponsor Ltd.'}]
    assert 'Unverified Holder' not in str(study) and 'Guessed Group' not in str(study)
    assert refs == {'summary_ref_0': [fact['id']]}
    assert original[0]['title'] == 'NCT03985943'
    assert svc.db.raw_current_facts(pid) == before


def test_identity_changes_invalidate_reduction_basis_without_changing_scientific_fact(identity_project):
    svc, pid, trial, drug, sid = identity_project
    rc = svc.context(pid, svc.db.create_run(pid))
    fact = next(f for f in svc.db.current_facts(pid)
                if f['entity_id'] == trial and f['field'] == 'design.primary_endpoint')
    original = [{'title': '研究先例', 'bullets': ['第16周终点'], 'fact_refs': [fact['id']]}]
    _, _, before = summary_basis(rc, original, {fact['id']})
    svc.db.add_fact({'project_id': pid, 'entity_id': drug, 'field': 'status.china_mah',
                    'value': 'Verified Legal Holder', 'status': 'verified', 'tier': 'critical',
                    'source_id': sid, 'quote': 'Verified Legal Holder',
                    'context': {'jurisdiction': 'CN'}, 'extracted_by': 'code:test'})
    projected, _, after = summary_basis(rc, original, {fact['id']})
    assert after != before
    assert {'role': '中国MAH', 'name': 'Verified Legal Holder'} in projected[0]['studies'][0]['companies']
    assert next(f for f in svc.db.current_facts(pid) if f['id'] == fact['id']) == fact
