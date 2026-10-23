import json
import runpy
from pathlib import Path

import pytest


def test_source_smoke_is_explicitly_budgeted_isolated_and_does_not_call_model(settings, tmp_path, offline_ctgov):
    script = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/smoke_expansion.py'))
    output = tmp_path / 'source-smoke'
    result = script['smoke'](settings, output, 'Atopic Dermatitis', 'nemolizumab')
    assert result['status'] == 'SOURCE_QUERY_COMPLETED_FRONTIER_PENDING'
    assert result['pipeline_acceptance'] == 'NOT_RUN' and result['model_calls'] == 0
    assert result['result']['source_attempts'] == 1 and result['result']['pending_queries']
    assert result['trials'] == 1
    assert (output / 'data/ciw2.sqlite3').is_file()
    before = (output / 'receipt.json').read_bytes()
    assert json.loads(before)['sources'] == result['sources']
    with pytest.raises(FileExistsError):
        script['smoke'](settings, output, 'Atopic Dermatitis', 'nemolizumab')
    assert (output / 'receipt.json').read_bytes() == before
