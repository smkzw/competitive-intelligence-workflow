import json

import pytest

from ciw2.domain.models import ExtractedFact, ExtractionResult
from ciw2.harness.llm import LLMError, ScriptedLLM
from ciw2.pipeline.stages import _design_extra, _extract, trial_evidence
from ciw2.service import Service
from ciw2.sources.http import register_text, source_by_url


def context(settings, count=1):
    service = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = service.create_project('适应症', ['C'])
    rid = service.db.create_run(pid)
    for i in range(count):
        service.db.upsert_entity(pid, 'drug', f'Drug{i:03}')
    rc = service.context(pid, rid)
    rc.stage = 'extract_design'
    return rc


def test_default_extraction_has_no_thirty_drug_cutoff(settings, monkeypatch):
    rc = context(settings, 35)
    seen = []
    monkeypatch.setattr(rc, 'skill', lambda name, task: (
        seen.append(task['drug']['name']) or ExtractionResult(facts=[], gaps=[])))
    result = _extract('extract-design', _design_extra)(rc)
    assert len(seen) == len(set(seen)) == 35
    assert result['pending_drug_ids'] == []


def test_explicit_budget_preserves_pending_and_resumes_only_remaining_drugs(settings, monkeypatch):
    rc = context(settings, 5)
    rc.cache['max_drugs'] = 2
    seen = []
    monkeypatch.setattr(rc, 'skill', lambda name, task: (
        seen.append(task['drug']['name']) or ExtractionResult(facts=[], gaps=[])))
    work = _extract('extract-design', _design_extra)
    for remaining in (3, 1):
        with pytest.raises(RuntimeError, match='未完成') as error:
            work(rc)
        assert len(error.value.output['pending_drug_ids']) == remaining
    assert work(rc)['pending_drug_ids'] == []
    assert len(seen) == len(set(seen)) == 5


def test_failed_drug_does_not_force_successful_drugs_to_repeat(settings, monkeypatch):
    rc = context(settings, 4)
    seen = []

    def extract(name, task):
        drug = task['drug']['name']
        seen.append(drug)
        if drug == 'Drug001' and seen.count(drug) == 1:
            raise LLMError('one unit unavailable')
        return ExtractionResult(facts=[], gaps=[])

    monkeypatch.setattr(rc, 'skill', extract)
    work = _extract('extract-design', _design_extra)
    with pytest.raises(RuntimeError, match='未完成'):
        work(rc)
    work(rc)
    assert seen.count('Drug001') == 2
    assert all(seen.count(f'Drug{i:03}') == 1 for i in (0, 2, 3))


def test_extraction_cache_invalidates_on_used_source_change(settings, monkeypatch):
    rc = context(settings)
    url = 'https://example.org/paper'
    register_text(rc.tool_ctx(), kind='web', url=url, text='Size 100.')
    calls = []

    def extract(name, task):
        calls.append(name)
        value = 100 if source_by_url(rc.tool_ctx(), url)['digest'] == first_digest else 200
        return ExtractionResult(facts=[ExtractedFact(entity='NCT00000001', field='design.sample_size', value=value,
                                                    quote=f'Size {value}.', source_url=url)])

    first_digest = source_by_url(rc.tool_ctx(), url)['digest']
    monkeypatch.setattr(rc, 'skill', extract)
    work = _extract('extract-design', _design_extra)
    assert work(rc)['facts'][0]['value'] == 100
    assert work(rc)['facts'][0]['value'] == 100
    register_text(rc.tool_ctx(), kind='web', url=url, text='Size 200.')
    assert work(rc)['facts'][0]['value'] == 200
    assert len(calls) == 2


def test_design_inputs_batch_all_references_without_inline_long_definitions(settings, monkeypatch):
    rc = context(settings)
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    expected, seen = set(), []
    for i in range(200):
        tid, _ = rc.db.upsert_entity(rc.project_id, 'trial', f'NCT{i:08}')
        rc.db.link(rc.project_id, drug['id'], 'drug-trial', tid)
        for field in ('design.primary_endpoint', 'design.eligibility.criteria'):
            expected.add(rc.db.add_fact({'project_id': rc.project_id, 'entity_id': tid, 'field': field,
                'value': '完整临床原条款' * 1000, 'tier': 'critical', 'status': 'verified', 'extracted_by': 'code:test'}))

    def extract(name, task):
        assert len(json.dumps(task, ensure_ascii=False)) <= 60000
        for ref in task['existing_design_facts']:
            assert 'value' not in ref and ref['read_tool'] == 'read_project_fact'
            seen.append(ref['id'])
        return ExtractionResult(facts=[], gaps=[])

    monkeypatch.setattr(rc, 'skill', extract)
    _extract('extract-design', _design_extra)(rc)
    assert set(seen) == expected and len(seen) == len(expected)


def seed_trials(rc, monkeypatch, count):
    from ciw2.sources import ctgov

    rc.stage = 'trial_evidence'
    rows = [{'nct': f'NCT{i:08}', 'interventions': [{'name': 'Drug000'}]} for i in range(count)]
    calls, limits = [], []

    def search(*args, **kwargs):
        limits.append(kwargs['max_results'])
        return rows

    def ingest(ctx, nct, route_id):
        calls.append(nct)
        eid, _ = ctx.db.upsert_entity(ctx.project_id, 'trial', nct, attrs=next(r for r in rows if r['nct'] == nct))
        return {'entity_id': eid, 'facts_added': 0}

    monkeypatch.setattr(ctgov, 'search', search)
    monkeypatch.setattr(ctgov, 'ingest_trial', ingest)
    return calls, limits


def test_default_trial_ingestion_is_not_cut_at_fifteen(settings, monkeypatch):
    rc = context(settings)
    calls, limits = seed_trials(rc, monkeypatch, 21)
    result = trial_evidence(rc)
    assert len(calls) == 21 and limits == [None]
    assert result['pending_trials'] == []


def test_trial_budget_preserves_pending_and_does_not_repeat_completed_ingestion(settings, monkeypatch):
    rc = context(settings)
    calls, limits = seed_trials(rc, monkeypatch, 3)
    rc.cache['max_trials_per_drug'] = 1
    for remaining in (2, 1):
        with pytest.raises(RuntimeError, match='未完成') as error:
            trial_evidence(rc)
        assert len(error.value.output['pending_trials']) == remaining
    assert trial_evidence(rc)['pending_trials'] == []
    assert len(calls) == len(set(calls)) == 3
    assert limits == [None, None, None]


def test_runner_persists_partial_output_and_resume_does_not_repeat_finished_units(settings, monkeypatch):
    from ciw2.pipeline import runner
    from ciw2.pipeline.stages import Stage

    rc = context(settings, 3)
    rc.cache['max_drugs'] = 2
    seen = []
    monkeypatch.setattr(rc, 'skill', lambda name, task: (
        seen.append(task['drug']['name']) or ExtractionResult(facts=[], gaps=[])))
    monkeypatch.setattr(runner, 'STAGES', [Stage('extract_design', _extract('extract-design', _design_extra))])
    assert runner.execute(rc) == 'failed'
    row = rc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?', (rc.run_id, 'extract_design'))
    assert row['status'] == 'failed' and len(json.loads(row['output_json'])['pending_drug_ids']) == 1
    rc.cache['max_drugs'] = None
    assert runner.execute(rc) == 'succeeded'
    assert len(seen) == len(set(seen)) == 3


def test_fact_reader_retains_whole_value_with_paging_and_rejects_foreign_fact(settings):
    from ciw2.harness.tools import REGISTRY, PageArgs, ReadFactArgs, _page_result

    rc = context(settings)
    tid, _ = rc.db.upsert_entity(rc.project_id, 'trial', 'NCT00000001')
    text = '完整入排原文AND/OR条件' * 2000
    fid = rc.db.add_fact({'project_id': rc.project_id, 'entity_id': tid, 'field': 'design.eligibility.criteria',
                         'value': text, 'tier': 'standard', 'status': 'verified', 'extracted_by': 'code:test'})
    ctx = rc.tool_ctx()
    tool = REGISTRY.get('read_project_fact')
    page = json.loads(tool.run(ctx, {'fact_id': fid}))
    assert page['status'] == 'paged'
    parts = [page['text']]
    while page['next_offset'] is not None:
        page = _page_result(ctx, PageArgs(result_id=page['result_id'], offset=page['next_offset']))
        parts.append(page['text'])
    assert json.loads(''.join(parts))['fact']['value'] == text
    other = rc.db.create_project('其他', ['C'])
    other_fact = rc.db.add_fact({'project_id': other, 'entity_id': tid, 'field': 'design.sample_size',
        'value': 1, 'tier': 'critical', 'status': 'verified', 'extracted_by': 'code:test'})
    assert tool.fn(ctx, ReadFactArgs(fact_id=other_fact))['status'] == 'tool_failed'


def test_actual_skill_source_dependencies_are_collected_and_invalidate_empty_result(settings, monkeypatch):
    from ciw2.pipeline import context as context_module

    rc = context(settings)
    calls = []
    current = {'text': 'Original methods.'}
    url = 'https://example.org/methods'

    def run(skill, task, llm, registry, ctx, **kwargs):
        calls.append(skill.name)
        register_text(ctx, kind='web', url=url, text=current['text'])
        return ExtractionResult(facts=[], gaps=[])

    monkeypatch.setattr(context_module, 'run_skill', run)
    work = _extract('extract-design', _design_extra)
    work(rc)
    assert len(rc.cache['last_skill_source_ids']) == 1
    work(rc)
    current['text'] = 'Revised methods.'
    register_text(rc.tool_ctx(), kind='web', url=url, text=current['text'])
    work(rc)
    assert len(calls) == 2


@pytest.mark.parametrize('budget', [0, -1, True, '2'])
def test_invalid_work_budget_fails_before_model(settings, monkeypatch, budget):
    rc = context(settings)
    rc.cache['max_drugs'] = budget
    monkeypatch.setattr(rc, 'skill', lambda *args: pytest.fail('Invalid budget started a model'))
    with pytest.raises(ValueError, match='执行预算'):
        _extract('extract-design', _design_extra)(rc)


def test_cached_fetch_is_still_observed_by_current_skill_context(settings):
    import httpx

    from ciw2.sources.http import fetch, source_text

    rc = context(settings)
    ctx = rc.tool_ctx()
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, text='Original source.', headers={'content-type': 'text/plain'})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        first = fetch(ctx, 'https://example.org/source', kind='web', client=client)
        ctx.extra['source_ids_read'] = set()
        second = fetch(ctx, 'https://example.org/source', kind='web', client=client)
    assert len(calls) == 1 and first.source_id == second.source_id
    assert ctx.extra['source_ids_read'] == {first.source_id}
    other = rc.db.create_project('其他', ['C'])
    ctx.project_id = other
    assert source_text(ctx, first.source_id) is None


def test_cli_defaults_to_full_workset_and_does_not_exit_success_for_failed_run(settings, monkeypatch):
    from dataclasses import replace

    from ciw2.cli import main

    service = Service(replace(settings, llm_api_key=''))
    captured = []
    original = service.start_run

    def start(pid, **kwargs):
        captured.append(kwargs)
        return original(pid, **kwargs)

    monkeypatch.setattr(service, 'start_run', start)
    monkeypatch.setattr('ciw2.service.Service', lambda settings: service)
    monkeypatch.setattr('ciw2.config.get_settings', lambda: settings)
    assert main(['run', '--indication', '离线']) == 1
    assert captured[0]['max_drugs'] is None


def test_nonblocking_incomplete_work_can_render_but_cannot_claim_run_success(settings, monkeypatch):
    from ciw2.pipeline import runner
    from ciw2.pipeline.stages import Stage

    rc = context(settings, 2)
    rc.cache['max_drugs'] = 1
    monkeypatch.setattr(rc, 'skill', lambda *args: ExtractionResult(facts=[], gaps=[]))
    monkeypatch.setattr(runner, 'STAGES', [
        Stage('extract_design', _extract('extract-design', _design_extra), blocking=False),
        Stage('render', lambda context: {'partial_render_available': True})])
    assert runner.execute(rc) == 'failed'
    assert rc.db.stage_output(rc.run_id, 'render')['partial_render_available']
    rc.cache['max_drugs'] = None
    assert runner.execute(rc) == 'succeeded'
