from pathlib import Path

from test_portal_js import run_portal


def test_glyph_navigation_hides_hover_before_opening_source_row():
    run_portal((Path(__file__).parent / 'fixtures/result-source-tip.js').read_text())
