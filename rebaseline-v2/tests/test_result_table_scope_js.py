from pathlib import Path

from test_portal_js import run_portal


def test_current_metric_table_and_all_matches_share_one_lossless_query():
    run_portal((Path(__file__).parent / 'fixtures/result-table-scope.js').read_text())
