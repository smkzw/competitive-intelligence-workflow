"""Fact-tool IDs and transport aliases must identify exactly the same supplied fact."""
import copy

import pytest
from test_analysis_budget import setup_analysis

from ciw2.domain.models import AnalysisResult
from ciw2.harness.llm import LLMReply, ToolCall
from ciw2.pipeline import stages


def prepared(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    fid = rc.db.current_facts(rc.project_id)[0]['id']
    rows, refs, basis = stages._summary_basis(
        rc, [{'title': '设计', 'bullets': ['原始观察'], 'fact_refs': [fid]}], {fid})
    task = {'mode': 'synthesis', 'finding_limit': 1, 'finding_basis_sha256': basis,
            'data': {'candidate_findings': rows}, 'verified_fact_ids': sorted(refs)}
    return rc, fid, task, refs


def response(ids):
    return AnalysisResult.model_validate({'report': 'C', 'findings': [
        {'title': '设计', 'bullets': ['原始观察'], 'fact_refs': ids}]})


@pytest.mark.parametrize('mixed', [False, True])
def test_actual_fact_id_from_read_tool_roundtrips_without_another_model_call(settings, monkeypatch, mixed):
    rc, fid, task, refs = prepared(settings, monkeypatch)
    alias = task['verified_fact_ids'][0]
    original = response([alias, fid] if mixed else [fid])
    before = original.model_dump()
    calls = []
    monkeypatch.setattr(rc, 'skill', lambda *args: calls.append(args) or original)
    result = stages._summary_resolve(rc, 'C', task, refs)
    assert result['findings'][0]['fact_refs'] == [fid]
    assert len(calls) == 1 and original.model_dump() == before
    cached = rc.db.stage_output(rc.run_id, stages._analysis_cache_key(rc, 'C', task))
    assert cached['findings'][0]['fact_refs'] == [alias]


def test_cached_actual_id_is_validated_without_rewriting_historical_output(settings, monkeypatch):
    rc, fid, task, refs = prepared(settings, monkeypatch)
    key = stages._analysis_cache_key(rc, 'C', task)
    rc.db.set_stage(rc.run_id, key, 'succeeded', output=response([fid]).model_dump())
    old = copy.deepcopy(rc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?', (rc.run_id, key)))
    monkeypatch.setattr(rc, 'skill', lambda *args: pytest.fail('qualified cache must not call model'))
    assert stages._summary_resolve(rc, 'C', task, refs)['findings'][0]['fact_refs'] == [fid]
    assert rc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?', (rc.run_id, key)) == old


@pytest.mark.parametrize('reference', ['fct_not_supplied', 'summary_ref_9999'])
def test_real_or_short_id_outside_this_packet_is_not_silently_deleted(settings, monkeypatch, reference):
    rc, fid, task, _ = prepared(settings, monkeypatch)
    monkeypatch.setattr(rc, 'skill', lambda *args: response([fid, reference]))
    with pytest.raises(ValueError, match='引用'):
        stages._analysis_call(rc, 'C', task)
    assert rc.db.stage_output(rc.run_id, stages._analysis_cache_key(rc, 'C', task)) is None


def test_real_fact_in_same_basis_but_different_packet_remains_out_of_scope(settings, monkeypatch):
    rc, fid, task, refs = prepared(settings, monkeypatch)
    rows, all_refs, basis = stages._summary_basis(rc, [
        {'title': '本包', 'bullets': ['保留'], 'fact_refs': [fid]},
        {'title': '别包', 'bullets': ['保留'], 'fact_refs': ['fct_other_packet']}], {fid, 'fct_other_packet'})
    task = {**task, 'finding_basis_sha256': basis, 'data': {'candidate_findings': rows[:1]},
            'verified_fact_ids': [next(k for k, ids in all_refs.items() if ids == [fid])]}
    monkeypatch.setattr(rc, 'skill', lambda *args: response(['fct_other_packet']))
    with pytest.raises(ValueError, match='引用'):
        stages._summary_resolve(rc, 'C', task, refs)


def test_actual_fact_id_in_non_alias_batch_does_not_change(settings, monkeypatch):
    rc, fid, _, _ = prepared(settings, monkeypatch)
    task = {'mode': 'batch', 'verified_fact_ids': [fid], 'data': {}}
    monkeypatch.setattr(rc, 'skill', lambda *args: response([fid]))
    assert stages._analysis_call(rc, 'C', task).findings[0].fact_refs == [fid]


def test_real_fact_tool_then_submit_then_cache_preserves_original_fact(settings, monkeypatch):
    rc, fid, task, refs = prepared(settings, monkeypatch)
    import json
    calls = []
    before = copy.deepcopy(rc.db.current_facts(rc.project_id))

    def respond(messages):
        calls.append(1)
        outputs = [json.loads(m['content']) for m in messages if m['role'] == 'tool']
        if not outputs:
            return LLMReply(tool_calls=[ToolCall('read', 'read_project_fact', {
                'fact_id': task['verified_fact_ids'][0]})])
        assert outputs[-1]['requested_ref'] == task['verified_fact_ids'][0]
        return LLMReply(tool_calls=[ToolCall('done', 'submit_result',
                                           response([outputs[-1]['fact']['id']]).model_dump())])

    rc.llm.script = respond
    assert stages._summary_resolve(rc, 'C', task, refs)['findings'][0]['fact_refs'] == [fid]
    assert stages._summary_resolve(rc, 'C', task, refs)['findings'][0]['fact_refs'] == [fid]
    assert len(calls) == 2 and rc.db.current_facts(rc.project_id) == before


def test_ambiguous_mapping_is_not_used_even_for_an_already_cached_submission(settings, monkeypatch):
    rc, fid, task, _ = prepared(settings, monkeypatch)
    digest = task['finding_basis_sha256']
    basis = rc.db.stage_output(rc.run_id, 'analysis_basis:' + digest)
    basis['reference_map']['summary_ref_extra'] = [fid]
    rc.db.set_stage(rc.run_id, 'analysis_basis:' + digest, 'succeeded', output=basis)
    task['verified_fact_ids'].append('summary_ref_extra')
    key = stages._analysis_cache_key(rc, 'C', task)
    rc.db.set_stage(rc.run_id, key, 'succeeded', output=response([fid]).model_dump())
    with pytest.raises(ValueError, match='一对一'):
        stages._analysis_call(rc, 'C', task)
