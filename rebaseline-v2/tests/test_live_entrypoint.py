import json
import runpy
from dataclasses import replace
from pathlib import Path

import pytest


def test_real_entrypoint_records_failed_configuration_without_network(settings, monkeypatch):
    script = Path(__file__).resolve().parents[1] / 'scripts/run_live.py'
    namespace = runpy.run_path(str(script))
    monkeypatch.setattr('sys.argv', [str(script), '--indication', '离线', '--reports', 'C'])
    namespace['main'].__globals__['get_settings'] = lambda: replace(settings, llm_api_key='')
    namespace['main']()
    receipt = json.loads(next((settings.data_dir / 'receipts').glob('*.json')).read_text())
    assert receipt['run_status'] == 'failed' and receipt['stages'] == []
    assert 'src/ciw2/cli.py' in receipt['source_hashes']
    assert all(not Path(p).is_absolute() for p in receipt['source_hashes'])


def test_recovery_receipt_does_not_mix_previous_attempt_model_calls(settings, monkeypatch):
    from ciw2.service import Service

    service = Service(settings)
    pid = service.create_project('恢复回执', ['C'])
    rid = service.db.create_run(pid)
    service.db.log_step(rid, 'intake', 'intake', 1, 'model', {'actual_model': 'prior-attempt'})

    def complete(*args, **kwargs):
        service.db.log_step(rid, 'intake', 'intake', 2, 'model', {'actual_model': 'current-attempt'})
        service.db.set_run(rid, 'failed', 'synthetic receipt test')

    monkeypatch.setattr(service, 'start_run', complete)
    script = Path(__file__).resolve().parents[1] / 'scripts/run_live.py'
    namespace = runpy.run_path(str(script))
    namespace['main'].__globals__.update({'Service': lambda s: service, 'get_settings': lambda: settings})
    monkeypatch.setattr('sys.argv', [str(script), '--indication', '恢复回执', '--project', pid, '--resume-run', rid])
    namespace['main']()
    receipt = json.loads(next((settings.data_dir / 'receipts').glob('*.json')).read_text())
    assert [r['actual_model'] for r in receipt['model_calls']] == ['current-attempt']
    assert receipt['runtime_settings']['max_agent_steps'] == settings.max_agent_steps


def test_isolated_stage_uses_real_stage_path_without_claiming_full_pipeline(settings, monkeypatch):
    from conftest import fake_llm_responder

    from ciw2.harness.llm import ScriptedLLM
    from ciw2.service import Service

    service = Service(settings, llm_factory=lambda s: (ScriptedLLM(fake_llm_responder), None))
    pid = service.create_project('冻结来源', ['C'])
    tid, _ = service.db.upsert_entity(pid, 'trial', 'NCT00000001')
    service.db.add_fact({'project_id': pid, 'entity_id': tid, 'field': 'design.sample_size', 'value': 100,
                         'tier': 'critical', 'status': 'verified', 'extracted_by': 'code:test'})
    script = Path(__file__).resolve().parents[1] / 'scripts/run_live.py'
    namespace = runpy.run_path(str(script))
    namespace['main'].__globals__.update({'Service': lambda s: service, 'get_settings': lambda: settings})
    monkeypatch.setattr('sys.argv', [str(script), '--indication', '冻结来源', '--project', pid,
                                  '--only-stage', 'analysis_C'])
    namespace['main']()
    receipt = json.loads(next((settings.data_dir / 'receipts').glob('*.json')).read_text())
    assert receipt['scope'] == 'stage' and receipt['only_stage'] == 'analysis_C'
    assert receipt['pipeline_acceptance'] == 'NOT_RUN'
    assert receipt['state'] == 'REAL_STAGE_RETURNED_NOT_PIPELINE_ACCEPTANCE'
    assert receipt['run_status'] == 'succeeded' and receipt['rows'] == {'C': 1}
    tasks = service.db.query("SELECT skill FROM agent_steps WHERE role='task'")
    assert [row['skill'] for row in tasks] == ['analysis-c']
    assert receipt['files'] and 'runner_script_sha256' in receipt


def test_stage_only_requires_existing_project_before_constructing_services(monkeypatch):
    script = Path(__file__).resolve().parents[1] / 'scripts/run_live.py'
    namespace = runpy.run_path(str(script))
    namespace['main'].__globals__['Service'] = lambda *args: pytest.fail('Do not create an implicit stage project')
    monkeypatch.setattr('sys.argv', [str(script), '--indication', '冻结来源', '--only-stage', 'analysis_C'])
    with pytest.raises(SystemExit) as error:
        namespace['main']()
    assert error.value.code == 2
