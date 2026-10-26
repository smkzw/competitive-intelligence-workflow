"""One exhausted 429 route chain stops later model calls, not pending work or cached facts."""
from __future__ import annotations

import pytest

from ciw2.domain.models import ExtractionResult
from ciw2.harness.cancellation import RunCancelled, RunControl
from ciw2.harness.fallback import FallbackLLM
from ciw2.harness.llm import LLMError, LLMReply, ScriptedLLM, ToolCall
from ciw2.pipeline import extraction
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.recovery import put_unit
from ciw2.service import Service
from ciw2.sources.http import register_text

SKILL = 'extract-design'


def _plain_extra(context, drug):
    return {}


def _route(model, outcome):
    def answer(messages):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    llm = ScriptedLLM(answer)
    llm.model = model
    return llm


def _limited(message='LLM 调用失败：HTTP 429'):
    return LLMError(message, {'http_status': 429, 'transport_error': 'HTTPStatusError', 'attempts': 3})


def _completed(gap='unit completed'):
    return LLMReply(tool_calls=[ToolCall(id='submit', name='submit_result', arguments={'facts': [], 'gaps': [gap]})])


def _pipeline(settings, drugs, routes, *, control=None):
    svc = Service(settings, llm_factory=lambda _: (FallbackLLM(routes), None))
    pid = svc.create_project('传输背压', ['A'])
    ids = [svc.db.upsert_entity(pid, 'drug', name)[0] for name in drugs]
    return svc, svc.context(pid, svc.db.create_run(pid), control=control), ids


def test_many_uncached_units_share_one_exhausted_route_chain_and_stay_pending(settings):
    routes = [_route('primary', _limited()), _route('backup', _limited())]
    _, rc, ids = _pipeline(settings, [f'Drug {letter}' for letter in 'ABCDEF'], routes)
    with pytest.raises(IncompleteWork) as failed:
        extraction.extract_drugs(rc, SKILL, _plain_extra)
    output = failed.value.output
    assert sum(len(route.calls) for route in routes) == len(routes)   # one actual chain, no storm
    assert len(output['errors']) == 1 and '429' in output['errors'][0]
    assert [unit['reason'] for unit in output['pending_units']] == ['transport_rate_limited'] * 6
    assert output['pending_drug_ids'] == sorted(ids)
    assert output['facts'] == [] and output['gaps'] == []


def test_cached_unit_after_limit_is_consumed_and_uncached_work_stays_pending(settings):
    routes = [_route('primary', _limited())]
    _, rc, ids = _pipeline(settings, ['Drug A', 'Drug B', 'Drug C'], routes)
    url, text = 'https://example.org/cached-design', 'Cached design endpoint was met.'
    sid = register_text(rc.tool_ctx(), kind='web', url=url, text=text)
    digest = rc.db.one('SELECT digest FROM sources WHERE id=?', (sid,))['digest']
    assert rc.cas.get(digest).decode() == text          # real CAS bytes, not only a DB row
    drug_b = next(drug for drug in rc.db.entities(rc.project_id, 'drug') if drug['id'] == ids[1])
    task = extraction._tasks(rc, SKILL, drug_b, {})[0]
    cached_fact = {'entity': 'NCT00000001', 'field': 'design.primary_endpoint', 'value': 'cached endpoint',
                   'source_url': url, 'source_id': sid, 'quote': text}
    put_unit(rc, extraction._key(rc, SKILL, task),
             {'facts': [cached_fact], 'gaps': ['cached unit'], 'extraction_model': 'cached-model'},
             source_ids=[sid], urls=[url])

    with pytest.raises(IncompleteWork) as failed:
        extraction.extract_drugs(rc, SKILL, _plain_extra)
    output = failed.value.output
    assert len(routes[0].calls) == 1
    assert output['gaps'] == ['Drug B: cached unit']
    assert [(fact['drug'], fact['value'], fact['extraction_model'], fact['source_id'])
            for fact in output['facts']] == [('Drug B', 'cached endpoint', 'cached-model', sid)]
    assert [unit['drug_id'] for unit in output['pending_units']] == [ids[0], ids[2]]
    assert [unit['reason'] for unit in output['pending_units']] == ['transport_rate_limited'] * 2


@pytest.mark.parametrize('damage', ['missing', 'tampered'])
def test_rejected_cache_after_limit_is_not_consumed_and_costs_no_model_call(settings, damage):
    routes = [_route('primary', _limited())]
    _, rc, ids = _pipeline(settings, ['Drug A', 'Drug B', 'Drug C'], routes)
    url, text = 'https://example.org/stale-design', 'Stale design endpoint was met.'
    sid = register_text(rc.tool_ctx(), kind='web', url=url, text=text)
    digest = rc.db.one('SELECT digest FROM sources WHERE id=?', (sid,))['digest']
    drug_b = next(drug for drug in rc.db.entities(rc.project_id, 'drug') if drug['id'] == ids[1])
    task = extraction._tasks(rc, SKILL, drug_b, {})[0]
    cached_fact = {'entity': 'NCT00000001', 'field': 'design.primary_endpoint', 'value': 'stale endpoint',
                   'source_url': url, 'source_id': sid, 'quote': text}
    put_unit(rc, extraction._key(rc, SKILL, task),
             {'facts': [cached_fact], 'gaps': ['stale unit'], 'extraction_model': 'stale-model'},
             source_ids=[sid], urls=[url])
    stored = rc.cas.root / digest[:2] / digest
    stored.unlink() if damage == 'missing' else stored.write_bytes(b'changed bytes')

    with pytest.raises(IncompleteWork) as failed:
        extraction.extract_drugs(rc, SKILL, _plain_extra)
    output = failed.value.output
    assert len(routes[0].calls) == 1                     # no model retry for the rejected cache
    assert output['facts'] == [] and output['gaps'] == []
    assert [unit['drug_id'] for unit in output['pending_units']] == ids
    assert {unit['reason'] for unit in output['pending_units']} == {'transport_rate_limited'}
    assert rc.db.one('SELECT id FROM sources WHERE id=?', (sid,))['id'] == sid   # evidence row kept


def test_fallback_recovery_on_the_same_call_does_not_start_backpressure(settings):
    primary, backup = _route('primary', _limited()), _route('backup', _completed())
    _, rc, _ = _pipeline(settings, ['Drug A', 'Drug B'], [primary, backup])
    output = extraction.extract_drugs(rc, SKILL, _plain_extra)
    assert output['pending_units'] == [] and output['errors'] == []
    assert output['gaps'] == ['Drug A: unit completed', 'Drug B: unit completed']
    assert len(primary.calls) == 1 and len(backup.calls) == 2


def test_unrelated_unit_errors_do_not_trip_backpressure(settings, monkeypatch):
    _, rc, _ = _pipeline(settings, ['Drug A', 'Drug B', 'Drug C'], [_route('idle', _completed())])

    def skill(name, task):
        drug = task['drug']['name']
        if drug == 'Drug A':
            raise ValueError('unit validation defect')
        if drug == 'Drug B':
            raise LLMError('LLM 调用失败：HTTP 503', {'http_status': 503})
        return ExtractionResult(facts=[], gaps=[f'{drug} ok'])

    monkeypatch.setattr(rc, 'skill', skill)
    with pytest.raises(IncompleteWork) as failed:
        extraction.extract_drugs(rc, SKILL, _plain_extra)
    output = failed.value.output
    assert [unit['reason'] for unit in output['pending_units']] == ['unit_failed'] * 2
    assert len(output['errors']) == 2
    assert output['gaps'] == ['Drug C: Drug C ok']


def test_later_invocation_retries_pending_units_after_the_limit(settings):
    _, rc, _ = _pipeline(settings, ['Drug A', 'Drug B'], [_route('primary', _limited())])
    with pytest.raises(IncompleteWork):
        extraction.extract_drugs(rc, SKILL, _plain_extra)

    backup = _route('backup', _completed())
    rc.llm = FallbackLLM([backup])
    output = extraction.extract_drugs(rc, SKILL, _plain_extra)
    assert output['pending_units'] == []
    assert output['gaps'] == ['Drug A: unit completed', 'Drug B: unit completed']
    assert len(backup.calls) == 2


def test_cancellation_still_propagates_through_the_limited_path(settings):
    control = RunControl()

    def stop(messages):
        control.request_stop()
        raise _limited()

    stopped = ScriptedLLM(stop)
    stopped.model = 'primary'
    _, rc, _ = _pipeline(settings, ['Drug A', 'Drug B'], [stopped], control=control)
    with pytest.raises(RunCancelled):
        extraction.extract_drugs(rc, SKILL, _plain_extra)
    assert len(stopped.calls) == 1


def test_throttled_output_keeps_shape_and_does_not_fabricate_facts(settings):
    svc, rc, ids = _pipeline(settings, ['Drug A', 'Drug B'], [_route('primary', _limited())])
    with pytest.raises(IncompleteWork) as failed:
        extraction.extract_drugs(rc, SKILL, _plain_extra)
    output = failed.value.output
    assert set(output) == {'facts', 'gaps', 'errors', 'pending_drug_ids', 'pending_units'}
    assert output['facts'] == [] and output['gaps'] == []
    assert output['pending_drug_ids'] == sorted(ids)
    assert svc.db.query('SELECT name FROM stages WHERE run_id=?', (rc.run_id,)) == []
