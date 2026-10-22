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
