from pathlib import Path

from test_portal_js import run_portal


def test_source_soc_and_study_domain_constraints_drive_one_fact_query():
    run_portal((Path(__file__).parent / 'fixtures/b-soc-query.js').read_text())
