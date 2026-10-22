import json
import runpy
from pathlib import Path

import pytest

from ciw2.sources import ctgov
from ciw2.sources.http import register_text


@pytest.mark.parametrize('missing', [False, True])
def test_complete_source_smoke_binds_pages_counts_and_preserves_failed_receipt(tmp_path, monkeypatch, missing):
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/smoke_live.py'))

    def search(ctx, **kwargs):
        assert kwargs['max_results'] is None
        for i in (1, 2):
            page = {'totalCount': 2, 'studies': [
                {'protocolSection': {'identificationModule': {'nctId': f'NCT{i:08}'}}}]}
            register_text(ctx, kind='ctgov', url=f'{ctgov.API}?pageToken=public-cursor-{i}', text=json.dumps(page))
        return [{'nct': 'NCT00000001'}] if missing else [{'nct': f'NCT{i:08}'} for i in (1, 2)]

    monkeypatch.setattr(ctgov, 'search', search)
    output = tmp_path / 'probe'
    result = namespace['complete_ctgov']('适应症', output)
    saved = json.loads((output / 'receipt.json').read_text())
    assert saved == result and result['model_calls'] == 0 and len(result['source_versions']) == 2
    assert result['status'] == ('FAILED_SOURCE_PAGINATION' if missing else 'PASSED_SOURCE_PAGINATION_ONLY')
    before = (output / 'receipt.json').read_bytes()
    with pytest.raises(FileExistsError):
        namespace['complete_ctgov']('适应症', output)
    assert (output / 'receipt.json').read_bytes() == before
