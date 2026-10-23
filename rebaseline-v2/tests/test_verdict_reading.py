"""Source details distinguish today's verdict from an immutable historical label."""
from test_quote_requalification import ALT_SOURCE, _legacy, _requalify, _source
from test_quote_requalification import env as env  # noqa: PLC0414 - pytest fixture registration

from ciw2.render.portal import render_report, report_data


def test_current_c_source_exposes_current_reason_without_changing_raw_fact(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    fid = _legacy(rc, trial, sid, field='design.sample_size')
    before = svc.db.one('SELECT * FROM facts WHERE id=?', (fid,))
    _requalify(svc.db, svc.cas, pid)
    data = report_data(svc.db, pid, 'C')
    ref = data['rows'][0]['sources']['sample_size'][0]
    assert ref['stored_status'] == 'verified' and ref['status'] == 'unverified'
    assert ref['verdict_note'] == '原文中找不到该片段'
    assert ref['verdict_note'] in render_report(svc.db, pid, 'C')
    assert svc.db.one('SELECT * FROM facts WHERE id=?', (fid,)) == before
    assert data['charts']['size']['values'] == []


def test_raw_superseded_source_is_explicitly_historical_not_currently_certified(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    old = _legacy(rc, trial, sid, field='design.sample_size', extracted_by='code:fixture')
    _legacy(rc, trial, sid, field='design.sample_size', value=132, supersedes=old,
            extracted_by='code:fixture')
    ref = report_data(svc.db, pid, 'C')['rows'][0]['sources']['sample_size'][0]['history'][0]
    assert ref['historical'] is True and ref['status'] == 'verified'
    html = render_report(svc.db, pid, 'C')
    assert '当时已核实' in html and '修订前记录' in html


def test_b_folded_source_explains_unassessed_old_label(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    fid = _legacy(rc, trial, sid)
    row = next(r for r in report_data(svc.db, pid, 'B')['results'] if r['id'] == fid)
    assert row['stored_status'] == 'verified' and row['status'] == 'unverified'
    assert row['verdict_note'] == '待按当前引文规则复核'
    assert row['verdict_note'] in render_report(svc.db, pid, 'B')


def test_missing_criteria_uses_existing_compact_source_reader_without_empty_column(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    _legacy(rc, trial, sid, field='design.phase', value='phase1', extracted_by='code:fixture')
    html = render_report(svc.db, pid, 'C')
    assert 'data-reading-title="研究依据">研究依据</summary><div class="source-evidence-content">' in html
    assert '<h3>完整入排原文</h3>' not in html


def test_complete_criteria_keeps_full_annotated_original_and_two_content_sections(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    _legacy(rc, trial, sid, field='design.eligibility_criteria', value=ALT_SOURCE,
            extracted_by='code:fixture')
    html = render_report(svc.db, pid, 'C')
    assert 'data-reading-title="入排与依据">完整入排与依据</summary><div class="design-evidence-content">' in html
    assert '<h3>完整入排原文</h3>' in html and 'criteria-threshold' in html
