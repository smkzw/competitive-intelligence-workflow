import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.stages import _entity_for, _matches, trial_evidence, verify
from ciw2.service import Service
from ciw2.sources.http import register_text


def context(settings, names):
    service = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = service.create_project('适应症', ['C'])
    rid = service.db.create_run(pid)
    for name in names:
        service.db.upsert_entity(pid, 'drug', name)
    return service.context(pid, rid)


@pytest.mark.parametrize('candidate,intervention,expected', [
    ('ABCD', 'ABCD-123', False),
    ('AB-CD', 'ABCD', False),
    ('ABCD', 'ABCD + OtherDrug', False),
    ('中文药名', '中文药名', True),
    ('药名', '药名', True),
    ('KX', 'KX', True),
])
def test_trial_names_preserve_literal_identity(candidate, intervention, expected):
    assert _matches({'name': candidate, 'aliases': []}, [{'name': intervention}]) is expected


def test_known_alias_is_an_exact_trial_match():
    assert _matches({'name': 'AB-CD', 'aliases': ['已核实药名']}, [{'name': 'OTHER', 'other_names': ['已核实药名']}])


def test_writeback_does_not_strip_punctuation(settings):
    rc = context(settings, ['A-B', 'AB'])
    ids = {d['name']: d['id'] for d in rc.db.entities(rc.project_id, 'drug')}
    assert _entity_for(rc, 'AB', 'AB') == ids['AB']


def test_ambiguous_alias_cannot_pick_first_entity(settings):
    rc = context(settings, ['DrugA', 'DrugB'])
    for name in ('DrugA', 'DrugB'):
        rc.db.upsert_entity(rc.project_id, 'drug', name, aliases=['shared'])
    with pytest.raises(ValueError, match='唯一关联'):
        _entity_for(rc, 'shared', 'DrugA')


def test_unknown_entity_not_silently_assigned_to_parent_drug(settings):
    rc = context(settings, ['DrugA'])
    with pytest.raises(ValueError, match='唯一关联'):
        _entity_for(rc, 'unexpected-entity', 'DrugA')
    assert len(rc.db.entities(rc.project_id, 'drug')) == 1


def test_known_chinese_name_and_existing_company_keep_their_own_identity(settings):
    rc = context(settings, ['DrugA'])
    drug, _ = rc.db.upsert_entity(rc.project_id, 'drug', 'DrugA', name_zh='正式药名')
    company, _ = rc.db.upsert_entity(rc.project_id, 'company', 'Source Company')
    assert _entity_for(rc, '正式药名', 'DrugA') == drug
    assert _entity_for(rc, 'Source Company', 'DrugA') == company


def test_trial_linking_retains_ambiguous_relation_without_cross_assignment(settings, monkeypatch):
    from ciw2.sources import ctgov

    rc = context(settings, ['DrugA', 'DrugB'])
    for name in ('DrugA', 'DrugB'):
        rc.db.upsert_entity(rc.project_id, 'drug', name, aliases=['shared'])
    studies = [{'nct': nct, 'interventions': [{'name': name}]} for nct, name in
               [('NCT00000001', 'shared'), ('NCT00000002', 'DrugA')]]
    monkeypatch.setattr(ctgov, 'search', lambda *args, **kwargs: studies)

    def ingest(ctx, nct, route_id):
        row = next(row for row in studies if row['nct'] == nct)
        eid, _ = ctx.db.upsert_entity(ctx.project_id, 'trial', nct, attrs=row)
        return {'entity_id': eid, 'facts_added': 0}

    monkeypatch.setattr(ctgov, 'ingest_trial', ingest)
    result = trial_evidence(rc)
    ids = {d['name']: d['id'] for d in rc.db.entities(rc.project_id, 'drug')}
    links = rc.db.query("SELECT src,dst FROM links WHERE rel='drug-trial'")
    assert len(links) == 1 and links[0]['src'] == ids['DrugA']
    assert result['identity_ambiguities'] == [{'name': 'shared', 'entity_ids': sorted(ids.values())}]
    pending = rc.db.query("SELECT * FROM links WHERE rel='drug-trial-candidate'")
    assert {r['src'] for r in pending} == set(ids.values())
    assert result['pending_identity_links'] == 2


def test_dose_and_composite_hits_remain_recoverable_candidate_links(settings, monkeypatch):
    from ciw2.sources import ctgov

    rc = context(settings, ['DrugA'])
    studies = [{'nct': nct, 'interventions': [{'name': label}]} for nct, label in
               [('NCT00000001', 'DrugA 100 mg'), ('NCT00000002', 'DrugA + DrugB')]]
    monkeypatch.setattr(ctgov, 'search', lambda *args, **kwargs: studies)
    monkeypatch.setattr(ctgov, 'ingest_trial', lambda *args, **kwargs: pytest.fail('Unresolved identity is not accepted'))
    first = trial_evidence(rc)
    second = trial_evidence(rc)
    assert first['linked'] == second['linked'] == 0
    assert first['pending_identity_links'] == second['pending_identity_links'] == 2
    assert len(rc.db.query("SELECT * FROM links WHERE rel='drug-trial-candidate'")) == 2
    assert {t['name'] for t in rc.db.entities(rc.project_id, 'trial')} == {'NCT00000001', 'NCT00000002'}


def test_unresolved_fact_is_retained_as_issue_while_valid_neighbor_is_written(settings):
    rc = context(settings, ['DrugA'])
    url = 'https://example.org/source'
    register_text(rc.tool_ctx(), kind='web', url=url, text='The planned size was 120 participants.')
    base = {'drug': 'DrugA', 'field': 'design.sample_size', 'value': 120,
            'source_url': url, 'quote': 'The planned size was 120 participants.'}
    rc.db.set_stage(rc.run_id, 'extract_design', 'succeeded', output={'facts': [
        {**base, 'entity': 'unresolved-entity'}, {**base, 'entity': 'NCT00000001'}]})
    result = verify(rc)
    facts = rc.db.current_facts(rc.project_id)
    assert len(facts) == 1 and result['stats']['verified'] == 1
    assert result['unresolved_entities'] == 1
    assert result['identity_issues'][0]['entity'] == 'unresolved-entity'
