import json
import runpy
from dataclasses import replace
from pathlib import Path


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
