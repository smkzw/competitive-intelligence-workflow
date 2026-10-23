import json

import pytest

from ciw2.domain.models import UniverseResult
from ciw2.harness.llm import LLMError, ScriptedLLM
from ciw2.harness.tools import ToolRegistry
from ciw2.pipeline.context import IncompleteWork
from ciw2.service import Service
from ciw2.sources.china import ChinaArgs
from ciw2.sources.ctgov import SearchArgs
from ciw2.sources.websearch import WebSearchArgs


def setup_expansion(settings):
    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = svc.create_project('适应症', ['C'])
    rid = svc.db.create_run(pid)
    eid, _ = svc.db.upsert_entity(pid, 'drug', 'Alpha', aliases=['AB-1', 'AB1'],
                                 attrs={'targets': ['IL-4'], 'companies': ['Company']})
    rc = svc.context(pid, rid)
    rc.stage = 'universe_expand'
    rc.registry = ToolRegistry()
    calls = []

    def source(ctx, args):
        calls.append(args.model_dump())
        svc.db.log_coverage(rid, args.route_id, 'china', 'offline source', 'ok')
        return {'count': 0, 'results': [], 'interventions': [], 'studies': []}

    for name, model in [('ctgov_search', SearchArgs), ('china_registry_search', ChinaArgs), ('web_search', WebSearchArgs)]:
        rc.registry.register(name, name, model)(source)
    return svc, rc, eid, calls


def test_query_plan_preserves_literal_terms_and_deduplicates_shared_seeds(settings):
    from ciw2.pipeline.expansion import query_plan

    svc, rc, eid, _ = setup_expansion(settings)
    svc.db.upsert_entity(rc.project_id, 'drug', 'Other', aliases=['AB-1'], attrs={'targets': ['IL-4']})
    plan = query_plan(rc)
    assert {'Alpha', 'AB-1', 'AB1', 'Other', 'IL-4', 'Company'} <= {q['term'] for q in plan}
    assert len({q['id'] for q in plan}) == len(plan)
    assert {q['registry'] for q in plan if q['tool'] == 'china_registry_search'} == {
        'chinadrugtrials', 'cde', 'nmpa'}
    assert all(q['kind'] in {'alias', 'target', 'company'} for q in plan)
    assert eid in next(q for q in plan if q['term'] == 'Alpha')['owners']


def test_real_registered_tool_calls_are_cached_without_repeating_completed_sources(settings):
    from ciw2.pipeline.expansion import expand_universe

    _, rc, _, calls = setup_expansion(settings)
    first = expand_universe(rc, lambda result: 0)
    assert calls and first['queries'] == len(calls) and first['expansion_complete']
    count = len(calls)
    second = expand_universe(rc, lambda result: 0)
    assert len(calls) == count and second['reused_queries'] == count
    assert first['clinical_universe_accepted'] is False


def test_query_budget_preserves_pending_ids_instead_of_claiming_completion(settings):
    from ciw2.pipeline.expansion import expand_universe, query_plan

    _, rc, _, calls = setup_expansion(settings)
    rc.cache['max_expansion_queries'] = 1
    expected = {q['id'] for q in query_plan(rc)}
    with pytest.raises(IncompleteWork) as caught:
        expand_universe(rc, lambda result: 0)
    output = caught.value.output
    assert len(calls) == 1 and len(output['completed_queries']) == 1
    assert set(output['completed_queries']) | {q['id'] for q in output['pending_queries']} == expected
    assert not output['expansion_complete']


def test_new_discovered_aliases_are_expanded_in_following_round(settings):
    from ciw2.pipeline.expansion import expand_universe

    svc, rc, _, calls = setup_expansion(settings)
    tool = rc.registry.get('ctgov_search')
    original = tool.fn

    def discover(ctx, args):
        if args.intervention == 'Alpha':
            svc.db.upsert_entity(rc.project_id, 'drug', 'Beta', aliases=['B-2'])
        return original(ctx, args)

    tool.fn = discover
    result = expand_universe(rc, lambda res: 0)
    assert result['rounds'] == 2
    assert any(call.get('intervention') == 'Beta' for call in calls)
    assert any(call.get('intervention') == 'B-2' for call in calls)


def test_blocked_and_failed_sources_do_not_become_empty_success_or_cached(settings):
    from ciw2.pipeline.expansion import expand_universe

    _, rc, _, calls = setup_expansion(settings)
    original = rc.registry.get('web_search').fn

    def blocked(ctx, args):
        original(ctx, args)
        return {'status': 'blocked', 'error': 'not configured'}

    rc.registry.get('web_search').fn = blocked
    first = expand_universe(rc, lambda res: 0)
    assert first['source_issues'] and not first['expansion_complete']
    assert all(item['status'] == 'blocked' for item in first['source_issues'])
    before = len(calls)
    expand_universe(rc, lambda res: 0)
    assert len(calls) > before  # Failed/blocked external access is not a reusable accepted result.


def test_completed_source_survives_model_failure_without_duplicate_fetch(settings):
    from ciw2.pipeline.expansion import expand_universe

    _, rc, _, calls = setup_expansion(settings)
    original = rc.registry.get('web_search').fn

    def leads(ctx, args):
        original(ctx, args)
        return {'count': 1, 'results': [{'url': 'https://example.org/lead', 'title': 'Candidate pipeline'}]}

    rc.registry.get('web_search').fn = leads
    attempts = {'count': 0}

    def interpret(name, task):
        attempts['count'] += 1
        if attempts['count'] == 2:
            raise LLMError('temporary model failure')
        return UniverseResult(region=task['region'], candidates=[], routes_run=[])

    rc.skill = interpret
    with pytest.raises(IncompleteWork):
        expand_universe(rc, lambda res: 0)
    queries = json.dumps(calls, sort_keys=True)
    expand_universe(rc, lambda res: 0)
    for call in json.loads(queries):
        assert calls.count(call) == 1  # Source caches precede model interpretation.


def test_round_budget_retains_new_query_frontier(settings):
    from ciw2.pipeline.expansion import expand_universe

    svc, rc, _, _ = setup_expansion(settings)
    rc.cache['max_expansion_rounds'] = 1
    original = rc.registry.get('ctgov_search').fn

    def discover(ctx, args):
        svc.db.upsert_entity(rc.project_id, 'drug', 'New frontier')
        return original(ctx, args)

    rc.registry.get('ctgov_search').fn = discover
    with pytest.raises(IncompleteWork) as caught:
        expand_universe(rc, lambda res: 0)
    assert any(q['term'] == 'New frontier' for q in caught.value.output['pending_queries'])


def test_expansion_is_in_the_production_graph_before_final_scope_review():
    from ciw2.pipeline.runner import stages_for

    names = [s.name for s in stages_for(['C'])]
    assert names.index('universe_global') < names.index('universe_expand') < names.index('coverage_review')
    assert names.index('universe_global') < names.index('candidate_triage') < names.index('universe_expand')


def test_previously_excluded_background_drugs_do_not_expand_but_unknowns_remain(settings):
    from ciw2.pipeline.expansion import query_plan

    svc, rc, eid, _ = setup_expansion(settings)
    svc.db.set_scope(eid, False, 'background treatment')
    svc.db.upsert_entity(rc.project_id, 'drug', 'Unresolved candidate')
    assert {q['term'] for q in query_plan(rc)} == {'Unresolved candidate'}


def test_control_alias_from_legacy_or_model_metadata_does_not_become_search_or_identity(settings):
    from ciw2.domain.identity import literal_names
    from ciw2.pipeline.expansion import query_plan

    svc, rc, eid, _ = setup_expansion(settings)
    svc.db.upsert_entity(rc.project_id, 'drug', 'Alpha', aliases=['Placebo', ' 安慰剂 '])
    drug = next(d for d in svc.db.entities(rc.project_id, 'drug') if d['id'] == eid)
    assert 'placebo' not in literal_names(drug) and '安慰剂' not in literal_names(drug)
    assert not any(q['term'].strip().casefold() in {'placebo', '安慰剂'} for q in query_plan(rc))


def test_model_candidate_adoption_uses_same_control_alias_policy(settings):
    from ciw2.pipeline.stages import _persist_universe

    svc, rc, _, _ = setup_expansion(settings)
    result = UniverseResult(region='global', candidates=[{
        'name': 'New active', 'aliases': ['Placebo', ' 安慰剂 ', 'AB-2'], 'route_id': 'global:test'}], routes_run=[])
    _persist_universe(rc, result)
    drug = next(d for d in svc.db.entities(rc.project_id, 'drug') if d['name'] == 'New active')
    assert drug['aliases'] == ['AB-2']


@pytest.mark.parametrize('payload', [{}, {'count': 0}, {'count': 1, 'results': 'not a result list'}])
def test_malformed_source_payload_cannot_prove_empty_completion(settings, payload):
    from ciw2.pipeline.expansion import expand_universe

    _, rc, _, _ = setup_expansion(settings)
    rc.registry.get('web_search').fn = lambda *args: payload
    result = expand_universe(rc, lambda res: 0)
    assert result['source_issues'] and not result['expansion_complete']
    assert all(item['error_type'] == 'InvalidSourceShape' for item in result['source_issues'])


def test_expansion_empty_input_does_not_claim_universe_acceptance(settings):
    from ciw2.pipeline.expansion import expand_universe

    svc = Service(settings)
    pid = svc.create_project('尚无候选', ['C'])
    rc = svc.context(pid, svc.db.create_run(pid))
    result = expand_universe(rc, lambda res: 0)
    assert result['queries'] == 0 and not result['expansion_complete']


def test_model_interpretation_and_receipt_persist_atomically(settings):
    from ciw2.pipeline.expansion import expand_universe

    svc, rc, _, calls = setup_expansion(settings)
    original = rc.registry.get('web_search').fn

    def leads(ctx, args):
        original(ctx, args)
        return {'count': 1, 'results': [{'url': 'https://example.org/lead'}]}

    rc.registry.get('web_search').fn = leads
    rc.skill = lambda name, task: UniverseResult(region=task['region'], candidates=[], routes_run=[])

    def broken_persist(result):
        svc.db.upsert_entity(rc.project_id, 'drug', 'Do not leak partial model adoption')
        raise RuntimeError('synthetic storage failure')

    with pytest.raises(IncompleteWork):
        expand_universe(rc, broken_persist)
    assert not any(d['name'] == 'Do not leak partial model adoption' for d in svc.db.entities(rc.project_id, 'drug'))
    assert svc.db.query("SELECT name FROM stages WHERE name LIKE 'expansion_interpret:%'") == []
    before = list(calls)
    expand_universe(rc, lambda res: 0)
    assert all(calls.count(call) == 1 for call in before)
