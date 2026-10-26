"""Execute the real portal with the shipped token object, not a CSS/string check."""
from pathlib import Path

import pytest
from test_portal_js import run_portal


@pytest.mark.parametrize('count', [3, 7])
def test_clinical_series_use_tokens_stable_frames_and_preserve_every_fact(count):
    script = (Path(__file__).parent / 'fixtures/chart-theme.js').read_text()
    run_portal(script.replace('SERIES_COUNT', str(count)))


def test_landscape_frames_keep_scope_and_source_bindings_when_split_or_filtered():
    run_portal((Path(__file__).parent / 'fixtures/landscape-theme.js').read_text())
