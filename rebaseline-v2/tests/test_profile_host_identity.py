"""Profile proposals retain the exact host entity even when legacy case variants coexist."""
import pytest
from test_drug_enrichment import setup

from ciw2.domain.models import ExtractedFact, ExtractionResult
from ciw2.pipeline import extraction, profile
from ciw2.pipeline.stages import verify
from ciw2.sources.http import register_text


def proposal(rc, name='ExampleDrug'):
    url = 'https://example.org/host-profile'
    text = f'{name} targets IL-31RA.'
    sid = register_text(rc.tool_ctx(), kind='company', url=url, text=text)
    return {**ExtractedFact(entity=name, field='identity.target', value='IL-31RA',
                           source_url=url, source_id=sid, quote=text).model_dump(), 'drug': name}


def test_real_enrichment_binds_host_id_through_cached_reuse_and_case_duplicate(settings, monkeypatch):
    svc, rc, legacy = setup(settings)
    current, _ = rc.db.upsert_entity(rc.project_id, 'drug', 'exampledrug')
    rc.db.set_scope(legacy, False, 'Retained legacy case variant, not a separate competitor')
    old = rc.db.one('SELECT * FROM entities WHERE id=?', (legacy,))
    raw = proposal(rc, 'exampledrug')
    calls = []

    def skill(name, task):
        calls.append(task)
        assert task['drug']['entity_id'] == current
        rc.cache['last_skill_source_ids'] = [raw['source_id']]
        return ExtractionResult(facts=[ExtractedFact.model_validate({k: v for k, v in raw.items() if k != 'drug'})])

    monkeypatch.setattr(rc, 'skill', skill)
    first = profile.enrich(rc)
    assert first['facts'][0]['drug_entity_id'] == current
    assert profile.enrich(rc) == first and len(calls) == 1
    rc.db.set_stage(rc.run_id, 'enrich_drugs', 'succeeded', output=first)
    result = verify(rc)
    facts = svc.db.current_facts(rc.project_id)
    assert result['unresolved_entities'] == 0
    assert [(f['entity_id'], f['status']) for f in facts] == [(current, 'verified')]
    assert rc.db.one('SELECT * FROM entities WHERE id=?', (legacy,)) == old
    assert rc.llm.calls == []


@pytest.mark.parametrize('bad', ['foreign', 'trial', 'wrong_name', 'wrong_returned_entity', 'empty'])
def test_explicit_bad_host_never_falls_back_to_matching_name(settings, bad):
    svc, rc, did = setup(settings)
    raw = proposal(rc)
    if bad == 'foreign':
        other = svc.create_project('other', ['A'])
        host, _ = rc.db.upsert_entity(other, 'drug', 'ExampleDrug')
    elif bad == 'trial':
        host, _ = rc.db.upsert_entity(rc.project_id, 'trial', 'ExampleDrug')
    elif bad == 'wrong_name':
        host, _ = rc.db.upsert_entity(rc.project_id, 'drug', 'OtherDrug')
    else:
        host = '' if bad == 'empty' else did
    if bad == 'wrong_returned_entity':
        raw['entity'] = 'OtherDrug'
    rc.db.set_stage(rc.run_id, 'enrich_drugs', 'succeeded', output={
        'facts': [{**raw, 'drug_entity_id': host}]})
    result = verify(rc)
    assert result['unresolved_entities'] == 1
    assert svc.db.current_facts(rc.project_id) == []


def test_adding_trusted_host_metadata_reuses_existing_legacy_fact_without_duplicate(settings):
    _, rc, did = setup(settings)
    raw = proposal(rc)
    rc.db.set_stage(rc.run_id, 'enrich_drugs', 'succeeded', output={'facts': [raw]})
    verify(rc)
    before = rc.db.query('SELECT * FROM facts WHERE project_id=?', (rc.project_id,))
    rc.db.set_stage(rc.run_id, 'enrich_drugs', 'succeeded', output={
        'facts': [{**raw, 'drug_entity_id': did}]})
    assert verify(rc)['replayed'] == 1
    assert rc.db.query('SELECT * FROM facts WHERE project_id=?', (rc.project_id,)) == before


def test_identity_task_carries_only_its_actual_host_id(settings):
    _, rc, did = setup(settings)
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    task = extraction._tasks(rc, 'extract-results', drug, {'mode': 'identity_enrichment'})[0]
    assert task['drug']['entity_id'] == did
