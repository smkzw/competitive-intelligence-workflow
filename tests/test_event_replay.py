"""Production-path root cases for source claims, pending replay and scoped repairs (synthetic)."""
import hashlib
import json

import pytest
from test_retained_source_facts import cached_roles

from ciw.sources.captures import extract_events, norm_region
from ciw.verify.events import validate_event_item
from ciw.verify.llm import CachedBackend, FakeBackend
from ciw.verify.quote import check_quote


def capture(ws, text):
    folder = ws.root / 'captures/docs'
    folder.mkdir(exist_ok=True)
    path = folder / 'synthetic.txt'
    path.write_text(text)
    path.with_name(path.name+'.meta.json').write_text(json.dumps(dict(kind='company', url='https://example.org/news')))
    return path


def fact(quote, **changes):
    return dict(product_mention='MG-K10', event_type='approval', region='中国', date='',
                indication='慢性鼻窦炎伴鼻息肉', detail='', quote=quote) | changes


@pytest.mark.parametrize('claim,ok', [
    ('Drug-X10用于CRSwNP；StudyX001研究的应答率为50%。', True),
    ('Drug-X10用于CRSwNP；StudyX001研究的应答率为90%。', False),
    ('Drug-X20用于CRSwNP；StudyX001研究的应答率为50%。', False),
])
def test_prose_identifiers_proven_in_anchor_are_not_clinical_measurements(claim, ok):
    anchor = 'Drug-X10在StudyX001研究中，CRSwNP应答率50%。'
    source = anchor + '另一个研究应答率90%。'
    assert check_quote(source, anchor, claim).ok == ok


@pytest.mark.parametrize('region', ['UK', 'United Kingdom', '英国'])
def test_same_explicit_uk_jurisdiction_has_one_canonical_identity(region):
    assert norm_region(region) == '英国'
    assert norm_region('Ukraine') != '英国'


def test_current_pending_source_items_survive_offline_without_promotion(cfg, resolver, ws):
    text = 'MG-K10已在中国获批用于慢性鼻窦炎伴鼻息肉。'
    capture(ws, text)
    current, _, _ = extract_events(ws,cfg,resolver,cached_roles(ws,[fact(text,detail='未经来源支持的补充摘要')]))
    assert len(current) == 1 and current[0].status == 'needs_review'
    ledger = ws.verifications()
    replayed, issues, coverage = extract_events(ws,cfg,resolver,None)
    assert replayed == current and ws.verifications() == ledger
    assert any(issue['kind'] == 'event_needs_review' for issue in issues)
    assert coverage[0]['status'] == 'partial'
    with ws.db() as con:
        con.execute('DELETE FROM llm_cache')
    missing, _, _ = extract_events(ws,cfg,resolver,None)
    assert not missing  # A pending label alone is not proof of an actual source response.


def test_future_filing_cannot_win_over_actual_acceptance_of_same_product(cfg,resolver,ws):
    planned = 'MG-K10计划明年递交慢性鼻窦炎伴鼻息肉的上市许可申请。'
    actual = 'MG-K10治疗慢性鼻窦炎伴鼻息肉的上市许可申请已获受理。'
    capture(ws,planned+actual)
    items=[fact(planned,event_type='filing'), fact(actual,event_type='filing')]
    assert not validate_event_item(items[0])[0]
    assert validate_event_item(items[1])[0]
    current, _, _ = extract_events(ws,cfg,resolver,cached_roles(ws,items))
    assert len(current) == 1 and current[0].status == 'verified' and current[0].quote == actual
    replayed, _, _ = extract_events(ws,cfg,resolver,None)
    assert replayed == current


def test_unrequested_repair_item_cannot_revoke_an_accepted_other_identity(cfg,resolver,ws):
    text='MG-K10在中国和美国获批用于慢性鼻窦炎伴鼻息肉。'
    capture(ws,text)
    good=fact(text)
    wrong=fact(text,region='美国',date='2024')
    seen=[]
    def review(system,user):
        seen.append(user)
        b.receipt={'response_id':'review-'+hashlib.sha256(user.encode()).hexdigest()}
        items=[good,wrong] if len(seen)==1 else [fact(text,region='美国'), fact(text,detail='无来源的新摘要')]
        return json.dumps({'items':items},ensure_ascii=False)
    a=cached_roles(ws,[good,wrong])['extractor_a']
    b=FakeBackend('glm','glm',review)
    current, _, _=extract_events(ws,cfg,resolver,{'extractor_a':a,'verifier':CachedBackend(b,ws)})
    assert len(current)==2 and {e.status for e in current}=={'verified'}
    repair=current[0]  # Calls are shared for the source, not an array-order identity binding.
    saved=ws.verifications()[repair.event_id]
    call=[c for c in saved['calls'] if c['role']=='verify_repair'][0]
    assert call['requested_keys'] and all('中国' not in key for key in call['requested_keys'])
    replayed,issues,_=extract_events(ws,cfg,resolver,None)
    assert {e.event_id for e in replayed}=={e.event_id for e in current} and not issues


@pytest.mark.parametrize('claim', ['5mg', '剂量为5mg，受试者来自StudyX001。'])
def test_decimal_quantity_cannot_supply_a_matching_identifier_suffix(claim):
    anchor = 'StudyX001采用1.5mg剂量。'
    assert not check_quote(anchor,anchor,claim).ok


@pytest.mark.parametrize('quote,ok', [
    ('MG-K10慢性鼻窦炎伴鼻息肉上市申请尚未受理。', False),
    ('The MG-K10 CRSwNP application has not yet been accepted.', False),
    ('The MG-K10 CRSwNP application has been accepted.', True),
    ('MG-K10慢性鼻窦炎伴鼻息肉上市申请已获受理。', True),
])
def test_filing_means_actual_action_not_an_uncompleted_application(quote,ok):
    indication='CRSwNP' if 'CRSwNP' in quote else '慢性鼻窦炎伴鼻息肉'
    assert validate_event_item(fact(quote,event_type='filing',indication=indication))[0] == ok


@pytest.mark.parametrize('claim,anchor,ok', [
    ('CM310入组310例', '研究CM310入组', False),
    ('剂量310', '编号CM310NP001', False),
    ('给予310mg', '给予CM310', False),
    ('CM310使NPS降低2分', 'CM310针对慢性鼻窦炎', False),
    ('给予CM310-300mg', '给予CM310', False),
    ('CM310治疗后NPS降低2分', 'CM310使NPS降低2分', True),
    ('CM310治疗后NPS降低3分', 'CM310使NPS降低2分', False),
    ('数值为1.2e-4', '指标值1.2e-4', True),
])
def test_prose_keeps_real_numbers_after_removing_only_proven_identifier_digits(claim,anchor,ok):
    assert check_quote(anchor,anchor,claim).ok == ok


@pytest.mark.parametrize('quote,ok', [
    ('Drug-X remains under regulatory review for CRSwNP in Jurisdiction-A.',True),
    ('The company will submit an application for MG-K10 in CRSwNP.',False),
    ('MG-K10尚未递交慢性鼻窦炎伴鼻息肉上市申请。',False),
])
def test_filing_guard_vetoes_explicit_plans_not_unknown_verb_forms(quote,ok):
    mention='Drug-X' if 'Drug-X' in quote else 'MG-K10'
    indication='CRSwNP' if 'CRSwNP' in quote else '慢性鼻窦炎伴鼻息肉'
    assert validate_event_item(fact(quote,product_mention=mention,indication=indication,event_type='filing'))[0] == ok


def test_non_milestone_candidate_is_traceable_in_queue_not_a_first_enrolment_claim(cfg,resolver,ws):
    text='MG-K10针对慢性鼻窦炎伴鼻息肉的III期临床已启动。'
    capture(ws,text)
    current,issues,_=extract_events(ws,cfg,resolver,cached_roles(ws,[fact(text,event_type='phase_start')]))
    assert not current and any(i['kind']=='event_needs_review' for i in issues)
    ledger=ws.verifications()
    replayed,later_issues,_=extract_events(ws,cfg,resolver,None)
    assert not replayed and any(i['kind']=='event_needs_review' for i in later_issues)
    assert ledger == ws.verifications() and {r['status'] for r in ledger.values()} == {'needs_review'}


@pytest.mark.parametrize('different', [True,False])
def test_distinct_quote_valid_claims_conflict_instead_of_first_wins(cfg,resolver,ws,different):
    first='MG-K10已在中国获批用于慢性鼻窦炎伴鼻息肉。'
    second='MG-K10在中国的慢性鼻窦炎伴鼻息肉适应症已获正式批准。' if different else first
    capture(ws,first+second)
    current,_,_=extract_events(ws,cfg,resolver,cached_roles(ws,[fact(first),fact(second)]))
    assert len(current)==1 and (current[0].status=='needs_review') == different


def test_patient_relative_scope_stays_in_source_anchor_and_chinese_detail_is_allowed():
    base='Drug-X is approved for adult patients with CRSwNP'
    scope='for whom systemic corticosteroids and/or surgery do not provide adequate control'
    quote=base+' '+scope+'.'
    common=fact(quote,product_mention='Drug-X',indication='CRSwNP')
    assert not validate_event_item(common | dict(detail='成人CRSwNP附加治疗获批',detail_quote=base))[0]
    assert validate_event_item(common | dict(detail='用于全身激素和/或手术控制不佳的成人CRSwNP',detail_quote=quote))[0]
    assert validate_event_item(fact('Drug-X is approved for severe asthma and CRSwNP.',
        product_mention='Drug-X',indication='CRSwNP',detail='获批治疗CRSwNP',
        detail_quote='Drug-X is approved for severe asthma and CRSwNP.'))[0]


@pytest.mark.parametrize('relative', ['whose disease is not controlled', 'in whom prior therapy was inadequate'])
def test_relative_patient_scope_keeps_original_anchor_and_allows_chinese_summary(relative):
    base='Drug-X is approved for adult patients with CRSwNP'
    quote=base+' '+relative+'.'
    full=fact(quote,product_mention='Drug-X',indication='CRSwNP',detail='用于既往治疗控制不佳的成人CRSwNP')
    assert validate_event_item(full | dict(detail_quote=quote))[0]
    assert not validate_event_item(full | dict(detail_quote=base))[0]
