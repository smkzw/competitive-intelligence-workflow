"""A CLI observation on stderr must survive; no browser or network is used."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize('stream', ['stdout', 'stderr', 'both'])
def test_browser_observation_is_retained_without_duplicate_success(tmp_path, monkeypatch, stream):
    path = Path(__file__).parents[1]/'scripts/smoke_cde_review_scope.py'
    spec = importlib.util.spec_from_file_location('cde_scope_smoke', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    capture = {'url':'https://www.cde.org.cn/main/xxgk/listpage/example', 'selects':[]}
    line = 'CIW_SCOPE:'+json.dumps(capture)+'\n'
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(
        a, 0, stdout=line if stream in ('stdout', 'both') else '[ego-browser:notice] local notice\n',
        stderr=line if stream in ('stderr', 'both') else ''))
    out = tmp_path/'observation'
    monkeypatch.setattr(sys, 'argv', ['scope', '--space', '80', '--output', str(out)])
    assert module.main() == (1 if stream == 'both' else 0)
    if stream != 'both':
        assert json.loads((out/'capture.json').read_text()) == capture
    else:
        assert not (out/'capture.json').exists()
    receipt = json.loads((out/'receipt.json').read_text())
    assert receipt['adopted_facts'] == 0 and receipt['full_source_closure'] == 'NOT_RUN'
