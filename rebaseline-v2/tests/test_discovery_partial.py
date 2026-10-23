from conftest import fake_llm_responder

from ciw2.harness.llm import LLMError, LLMReply, ScriptedLLM, ToolCall
from ciw2.render.portal import data_c
from ciw2.service import Service


def test_read_registry_candidates_survive_model_discovery_failure(settings, offline_ctgov):
    def responder(messages):
        text = messages[0]['content']
        if '# Skill：universe-' in text:
            if not any(m['role'] == 'assistant' for m in messages):
                return LLMReply(tool_calls=[ToolCall('registry', 'ctgov_search', {
                    'condition': 'Atopic Dermatitis', 'route_id': 'global:registry-test'})])
            raise LLMError('model failed after source was already read')
        return fake_llm_responder(messages)

    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM(responder), None))
    pid = svc.create_project('特应性皮炎', ['C'])
    rid = svc.start_run(pid, background=False)
    assert len(data_c(svc.db, pid)['rows']) == 1
    assert svc.db.one('SELECT error FROM runs WHERE id=?', (rid,))['error']
    drug = svc.db.entities(pid, 'drug')[0]
    assert drug['attrs']['discovery_method'] == 'registry_intervention'
    assert drug['attrs'].get('innovative') is None
    assert not drug['attrs'].get('china_mah')
def test_registry_discovery_preserves_all_original_aliases(settings, study, monkeypatch):
    from ciw2.service import Service
    from ciw2.sources import ctgov

    study['protocolSection']['armsInterventionsModule']['interventions'] = [
        {'type': 'DRUG', 'name': 'AB-1', 'otherNames': ['AB1', '中文正式名', 'Shared alias']},
        {'type': 'DRUG', 'name': 'AB-2', 'otherNames': ['Shared alias']}]
    service = Service(settings)
    pid = service.create_project('适应症', ['C'])
    rid = service.db.create_run(pid)
    ctx = service.context(pid, rid).tool_ctx()
    ctx.stage = 'universe_china'
    monkeypatch.setattr(ctgov, 'search', lambda *a, **k: [ctgov.parse_study(study)])
    ctgov._ctgov_search(ctx, ctgov.SearchArgs(condition='condition', route_id='china:test'))
    drugs = {d['name']: d for d in service.db.entities(pid, 'drug')}
    assert set(drugs['AB-1']['aliases']) >= {'AB1', '中文正式名', 'Shared alias'}
    assert 'Shared alias' in drugs['AB-2']['aliases']
    assert set(drugs) == {'AB-1', 'AB-2'}  # A shared alias never merges two source identities.


def test_registry_alias_shape_error_is_not_split_into_character_aliases(study):
    import pytest

    from ciw2.sources.ctgov import parse_study

    study['protocolSection']['armsInterventionsModule']['interventions'][0]['otherNames'] = 'AB-1'
    with pytest.raises(ValueError, match='别名'):
        parse_study(study)


def test_source_other_names_control_label_is_preserved_but_not_an_active_drug_identity(settings, study, monkeypatch):
    from ciw2.pipeline.stages import _matches
    from ciw2.service import Service
    from ciw2.sources import ctgov

    # Real expansion-source-smoke-01 exposed otherNames=['Placebo'] on an active intervention.
    aliases = ['Placebo', ' 安慰剂 ', 'AB-1']
    study['protocolSection']['armsInterventionsModule']['interventions'] = [
        {'type': 'DRUG', 'name': 'Active intervention', 'otherNames': aliases}]
    service = Service(settings)
    pid = service.create_project('适应症', ['C'])
    rc = service.context(pid, service.db.create_run(pid))
    rc.stage = 'universe_expand'
    monkeypatch.setattr(ctgov, 'search', lambda *a, **k: [ctgov.parse_study(study)])
    ctgov._ctgov_search(rc.tool_ctx(), ctgov.SearchArgs(condition='condition', route_id='test:control-alias'))
    drug = service.db.entities(pid, 'drug')[0]
    assert drug['aliases'] == ['AB-1']
    assert not _matches(drug, [{'name': 'Placebo'}])
    assert _matches(drug, [{'name': 'AB-1'}])
    assert service.db.entities(pid, 'trial')[0]['attrs']['interventions'][0]['other_names'] == aliases
