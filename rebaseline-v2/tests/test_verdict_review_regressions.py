"""Production counterexamples from the independent frozen implementation review."""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_quote_requalification import _adopt, _effective, _legacy, _proposal, _receipts, _requalify, _source
from test_quote_requalification import env as env  # noqa: PLC0414 - pytest fixture registration

from ciw2.export import fact_export
from ciw2.render.portal import render_report, report_data
from ciw2.store.db import DB
from ciw2.verify import assessment
from ciw2.verify.quote import check_quote


@pytest.mark.parametrize('value,wrong,right',[
    (1e-10,'The p value was 0.1.','The p value was 1e-10.'),
    (1e-20,'The p value was 0.01.','The p value was 1e-20.'),
    (-1e-10,'The difference was -0.1.','The difference was -1e-10.'),
    (9007199254740993,'The count was 9007199254740992.','The count was 9007199254740993.'),
    ('1e-10','The p value was 0.1.','The p value was 1e-10.'),
    ('.05','The value was 5.','The value was .05.'),
    ('1,000','The count was 1 and 0.','The count was 1,000.'),
    ('IGA2','The score was 9.','The IGA2 threshold was 2.'),
])
def test_numeric_check_preserves_exponent_integer_and_literal_numeric_types(value,wrong,right):
    assert not check_quote(wrong,wrong,value).ok
    assert check_quote(right,right,value).ok


def test_unsupported_exponent_cannot_gain_a_confirmed_receipt_chart_or_download(env):
    svc,rc,pid,_=env
    quote='The p value was 0.1.'
    url='https://example.org/unsupported-exponent'
    _source(rc,text=quote,url=url)
    _adopt(rc,[_proposal(rc,url,value=1e-10,quote=quote)])
    fact=svc.db.current_facts(pid)[0]
    assert fact['value']==1e-10 and fact['status']=='unverified'
    assert not _receipts(svc.db)
    assert not report_data(svc.db,pid,'B')['charts']['groups']
    assert fact_export(svc.db,pid)['facts'][0]['status']=='unverified'


def test_long_missing_numeric_list_keeps_valid_idempotent_specific_verdict(env):
    svc,rc,pid,trial=env
    sid=_source(rc,text='The value was 3.')
    fid=_legacy(rc,trial,sid,value=list(range(5000)),quote='The value was 3.')
    _requalify(svc.db,svc.cas,pid)
    first=_receipts(svc.db)
    assert len(first)==1 and len(first[0]['reason'])<1000
    assert first[0]['verdict']=='invalidated' and '数值未出现在片段中' in first[0]['reason']
    again=_requalify(svc.db,svc.cas,pid)
    assert again['counts']['skipped']==1 and _receipts(svc.db)==first
    assert _effective(svc.db,pid,fid)['verdict']=='invalidated'


def test_verdict_json_is_never_sliced_by_the_conversational_log_limit(env):
    svc,_,pid,_=env
    payload={'project_id':pid,'reason':'检验'*15000,'verdict':'invalidated'}
    svc.db.log_step(None,'verify','verify',0,assessment.ROLE,payload)
    stored=svc.db.query("SELECT content FROM agent_steps WHERE role='fact_verdict'")[0]['content']
    assert json.loads(stored)==payload


def test_separate_db_handles_serialize_assessment_and_do_not_duplicate_receipts(env,monkeypatch):
    svc,rc,pid,trial=env
    sid=_source(rc)
    _legacy(rc,trial,sid,value=3,quote='ALT < 3')
    other=DB(svc.db.path)
    first_read,second_read=threading.Event(),threading.Event()
    first_latest,second_latest=svc.db.latest_verdicts,other.latest_verdicts

    def first(*args,**kwargs):
        result=first_latest(*args,**kwargs)
        if svc.db._conn.in_transaction:
            first_read.set()
            second_read.wait(.25)  # Controlled interleaving, not progress polling.
        return result

    def second(*args,**kwargs):
        result=second_latest(*args,**kwargs)
        if other._conn.in_transaction:second_read.set()
        return result

    monkeypatch.setattr(svc.db,'latest_verdicts',first)
    monkeypatch.setattr(other,'latest_verdicts',second)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(_requalify,svc.db,svc.cas,pid)
            assert first_read.wait(3)
            b=pool.submit(_requalify,other,svc.cas,pid)
            results=[a.result(timeout=5),b.result(timeout=5)]
        assert len(_receipts(svc.db))==1
        assert sum(r['counts']['skipped'] for r in results)==1
    finally:other._conn.close()


def test_ordinary_same_run_replay_retries_recovered_pinned_source_without_new_fact(env):
    svc,rc,pid,_=env
    url='https://example.org/recovered'
    sid=_source(rc,url=url)
    proposal=_proposal(rc,url)
    _adopt(rc,[proposal])
    source=svc.db.one('SELECT * FROM sources WHERE id=?',(sid,))
    path=svc.cas._path(source['text_digest'])
    original=path.read_bytes()
    path.unlink()  # Synthetic temporary fixture only; no real source deletion.
    _requalify(svc.db,svc.cas,pid)
    facts=svc.db.query('SELECT * FROM facts ORDER BY id')
    path.write_bytes(original)
    output=_adopt(rc,[proposal])
    assert output['reassessed']==1
    assert svc.db.current_facts(pid)[0]['status']=='verified'
    assert svc.db.query('SELECT * FROM facts ORDER BY id')==facts


@pytest.mark.parametrize('field,value',[
    ('allocation','RANDOMIZED'),('masking','DOUBLE'),
    ('arms',[{'label':'Treatment','type':'EXPERIMENTAL','description':'Drug 3 mg'}]),
    ('eligibility_age',{'min':18,'max':65}),('eligibility_sex','ALL'),
    ('eligibility_healthy_volunteers','No'),('trial_scope','国内'),('china_site',True),
])
def test_c_prominent_design_value_carries_current_unverified_status(env,field,value):
    svc,rc,pid,trial=env
    sid=_source(rc)
    fid=_legacy(rc,trial,sid,field='design.'+field,value=value,
                context={'geographic_scope':'mainland_china'} if field=='china_site' else None)
    html=render_report(svc.db,pid,'C')
    body=html.split('<tbody>',1)[1].split('</tbody>',1)[0]
    cell=body.split('<td>')[4 if field in {'allocation','masking','arms'} else 6]
    cell=re.sub(r'<details class="evidence">.*?</details>','',cell,flags=re.DOTALL)
    assert f'data-fact-id="{fid}"' in cell
    assert re.search(r'class="badge unverified"[^>]*>未核实</span>',cell)


def test_eligibility_highlights_do_not_drop_current_status(env):
    svc,rc,pid,trial=env
    sid=_source(rc)
    _legacy(rc,trial,sid,field='design.eligibility_criteria',value='Inclusion: EASI >= 16.')
    html=render_report(svc.db,pid,'C')
    quick=html.split('<details class="eligibility-key">',1)[1].split('</details>',1)[0]
    assert 'badge unverified' in quick and 'EASI' in quick


def test_unknown_site_is_not_displayed_as_false(env):
    svc,rc,pid,trial=env
    sid=_source(rc)
    _legacy(rc,trial,sid,field='design.china_site',value=None,status='unknown',extracted_by='code:fixture',
            context={'geographic_scope':'mainland_china'})
    html=render_report(svc.db,pid,'C')
    body=html.split('<tbody>',1)[1].split('</tbody>',1)[0]
    assert '中国大陆站点 否' not in body and '中国大陆站点 —' in body
