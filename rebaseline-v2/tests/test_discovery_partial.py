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
