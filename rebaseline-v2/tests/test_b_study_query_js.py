from pathlib import Path

from test_portal_js import run_portal


def test_study_query_preserves_unpublished_studies_and_matches_figure_table_safety():
    run_portal((Path(__file__).parent / 'fixtures/b-study-query.js').read_text())
