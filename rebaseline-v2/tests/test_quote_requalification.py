"""Current-rule verdict projection: append-only receipts, immutable facts.

The literal quote checker is only half the guarantee. These tests pin the
other half: a stored LLM ``verified`` without a valid receipt for the current
checker bytes is not current evidence, and requalification can only append
verdict receipts -- never rewrite a fact, source, quote or revision link.
"""
from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy

import pytest

from ciw2.domain.models import ExtractedFact
from ciw2.export import encode_export, fact_export
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.stages import verify
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service
from ciw2.sources.http import register_text
from ciw2.verify.quote import check_quote

ALT_SOURCE = '入选标准：ALT < 3；EASI > 16。\n主要终点：IGA ≥2 分改善。\nALT observed value 3.'
GENUINE_QUOTE = 'ALT observed value 3.'
FABRICATED_QUOTE = 'ALT 16'
RESULT_CONTEXT = {'endpoint': 'ALT change', 'timepoint': 'Week 16', 'unit': 'U/L',
                  'stat_type': 'mean', 'population': 'ITT', 'arm': 'Treatment A'}


def _assessment():
    from ciw2.verify import assessment
    return assessment


def _requalify(*args, **kwargs):
    from ciw2.pipeline.requalify import requalify_project
    return requalify_project(*args, **kwargs)


@pytest.fixture
def env(settings):
    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = svc.create_project('特应性皮炎', ['B', 'C'])
    rid = svc.db.create_run(pid)
    rc = svc.context(pid, rid)
    trial, _ = svc.db.upsert_entity(pid, 'trial', 'NCT00000002')
    return svc, rc, pid, trial


def _source(rc, text=ALT_SOURCE, url='https://example.org/criteria'):
    sid = register_text(rc.tool_ctx(), kind='web', url=url, text=text)
    assert sid
    return sid


def _legacy(rc, trial, source_id, *, value=16, quote=FABRICATED_QUOTE, status='verified',
            field='result.primary.value', context=None, supersedes=None,
            extracted_by='llm:legacy-model'):
    return rc.db.add_fact({
        'project_id': rc.project_id, 'entity_id': trial, 'field': field, 'value': value,
        'tier': 'critical', 'status': status, 'source_id': source_id, 'quote': quote,
        'context': dict(context if context is not None else RESULT_CONTEXT),
        'extracted_by': extracted_by, 'supersedes': supersedes})


def _proposal(rc, url, *, value=3, quote=GENUINE_QUOTE, field='result.primary.value',
              supersedes=None, context=None):
    payload = {**ExtractedFact(entity='NCT00000002', field=field, value=value, endpoint='ALT change',
                               unit='U/L', stat_type='mean', timepoint='Week 16', population='ITT',
                               arm='Treatment A', source_url=url, quote=quote,
                               supersedes=supersedes).model_dump(), 'drug': 'Study drug'}
    payload.update(context or {})
    return payload


def _adopt(rc, facts, stage='extract_results'):
    rc.db.set_stage(rc.run_id, stage, 'succeeded', output={'facts': facts})
    rc.stage = 'verify'
    return verify(rc)


def _receipts(db):
    return [json.loads(row['content']) for row in db.query(
        "SELECT content FROM agent_steps WHERE role='fact_verdict' AND json_valid(content) ORDER BY id")]


def _snapshot(db):
    return {table: db.query(f'SELECT * FROM {table} ORDER BY rowid')
            for table in ('facts', 'sources', 'links', 'entities')}


def _effective(db, pid, fact_id):
    return next(row for row in db.current_facts(pid) if row['id'] == fact_id)


# --------------------------------------------------------------------------- A
def test_verify_rejects_fabricated_inequality_quote_end_to_end(env):
    svc, rc, pid, _ = env
    url = 'https://example.org/criteria'
    _source(rc, url=url)
    assert not check_quote(ALT_SOURCE, FABRICATED_QUOTE, 16).ok  # the literal rule's counterexample
    _adopt(rc, [_proposal(rc, url, value=16, quote=FABRICATED_QUOTE)])
    fact = next(f for f in svc.db.current_facts(pid) if f['field'] == 'result.primary.value')
    assert fact['status'] == 'unverified'
    data = report_data(svc.db, pid, 'B')
    assert data['plot_exclusions'][fact['id']] == 'unverified'
    assert all(fact['id'] != point['fact_id'] for group in data['charts']['groups'] for point in group['points'])


def test_verify_accepts_genuine_inequality_quotes_end_to_end(env):
    svc, rc, pid, _ = env
    url = 'https://example.org/criteria'
    _source(rc, url=url)
    _adopt(rc, [_proposal(rc, url, value='< 3', quote='ALT < 3'),
                _proposal(rc, url, value='> 16', quote='EASI > 16')])
    facts = [f for f in svc.db.current_facts(pid) if f['extracted_by'].startswith('llm:')]
    assert {f['value'] for f in facts} == {'< 3', '> 16'}
    assert all(f['status'] == 'verified' for f in facts)
    receipts = _receipts(svc.db)
    assert {r['verdict'] for r in receipts} == {'confirmed'} and len(receipts) == 2
    rule = _assessment().rule_identity()
    assert all(r['rule'] == rule and r['source_digest'] and r['text_digest'] for r in receipts)
    assert all(r['coordinate'] == 'normalized' and r['quote_start'] is not None for r in receipts)
    data = report_data(svc.db,pid,'B')
    assert set(data['plot_exclusions'].values()) == {'non_numeric'}
    assert data['charts']['groups'] == []


# --------------------------------------------------------------------------- B
def test_legacy_fabricated_verified_is_effective_unverified_without_mutation(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    fact_id = _legacy(rc, trial, sid)
    before = _snapshot(svc.db)
    ledger = len(svc.db.query('SELECT * FROM agent_steps'))
    effective = _effective(svc.db, pid, fact_id)
    assert len(svc.db.query('SELECT * FROM agent_steps')) == ledger  # read-time projection writes nothing
    assert effective['status'] == 'unverified' and effective['stored_status'] == 'verified'
    assert effective['verdict_note'] and effective['quote'] == FABRICATED_QUOTE
    assert svc.db.one('SELECT * FROM facts WHERE id=?', (fact_id,))['status'] == 'verified'
    assert svc.db.query('SELECT * FROM facts ORDER BY rowid') == before['facts']
    data = report_data(svc.db, pid, 'B')
    assert data['plot_exclusions'][fact_id] == 'unverified'
    assert all(fact_id != point['fact_id'] for group in data['charts']['groups'] for point in group['points'])


def test_old_verified_cannot_overshadow_a_newer_negative(env):
    svc, rc, pid, trial = env
    old_source = _source(rc)
    old = _legacy(rc, trial, old_source)
    url = 'https://example.org/newer'
    _source(rc, url=url)
    newer_run = svc.context(pid, svc.db.create_run(pid))
    _adopt(newer_run, [_proposal(newer_run, url, value=16, quote=FABRICATED_QUOTE)])
    rows = [f for f in svc.db.current_facts(pid) if f['field'] == 'result.primary.value']
    assert len(rows) == 2 and old in {f['id'] for f in rows}
    assert all(f['status'] == 'unverified' for f in rows)
    assert next(f for f in rows if f['id'] == old)['stored_status'] == 'verified'
    data = report_data(svc.db, pid, 'B')
    assert set(data['plot_exclusions']) == {f['id'] for f in rows}
    assert data['charts']['groups'] == []


def test_requalification_demotes_fabricated_legacy_quote_and_confirms_genuine(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    bad = _legacy(rc, trial, sid)
    good = _legacy(rc, trial, sid, value=3, quote=GENUINE_QUOTE,
                   context={**RESULT_CONTEXT, 'arm': 'Treatment B'})
    before = _snapshot(svc.db)
    summary = _requalify(svc.db, svc.cas, pid)
    assert summary['counts']['scanned'] == 2
    assert summary['counts']['confirmed'] == 1 and summary['counts']['invalidated'] == 1
    assert _snapshot(svc.db) == before  # no fact/source/link/entity bytes changed
    assert _effective(svc.db, pid, bad)['status'] == 'unverified'
    assert _effective(svc.db, pid, good)['status'] == 'verified'
    assert svc.db.one('SELECT status FROM facts WHERE id=?', (bad,))['status'] == 'verified'
    receipts = _receipts(svc.db)
    assert {(r['fact_id'], r['verdict']) for r in receipts} == {
        (bad, 'invalidated'), (good, 'confirmed')}
    assert next(r for r in receipts if r['fact_id'] == bad)['reason'] == '原文中找不到该片段'


def test_requalification_never_promotes_stored_unverified_conflict_or_unknown(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    ids = [_legacy(rc, trial, sid, status=status, value=3, quote=GENUINE_QUOTE,
                   context={**RESULT_CONTEXT, 'arm': status})
           for status in ('unverified', 'conflict', 'unknown')]
    summary = _requalify(svc.db, svc.cas, pid)
    assert summary['counts']['scanned'] == 0
    assert _receipts(svc.db) == []
    assert [_effective(svc.db, pid, fid)['status'] for fid in ids] == ['unverified', 'conflict', 'unknown']
    assert all(_effective(svc.db, pid, fid)['stored_status'] == status
               for fid, status in zip(ids, ('unverified', 'conflict', 'unknown'), strict=True))


def test_code_registry_facts_are_never_requalified(env):
    svc, rc, pid, trial = env
    code_source = _source(rc, text='Planned size 941.', url='https://example.org/registry')
    code = _legacy(rc, trial, code_source, value=941, quote='941', status='verified',
                   extracted_by='code:ctgov',
                   context={'enrollment_type': 'ESTIMATED', 'source_snapshot': 'snap-1'})
    svc.db.link(pid, trial, 'ctgov-current', code_source, {'snapshot': 'snap-1'})
    design_code = _legacy(rc, trial, None, value=941, quote='Planned size 941.', status='verified',
                          field='design.sample_size', extracted_by='code:chinadrugtrials',
                          context={'enrollment_type': 'ESTIMATED'})
    before = _snapshot(svc.db)
    summary = _requalify(svc.db, svc.cas, pid)
    assert summary['counts']['scanned'] == 0
    assert _receipts(svc.db) == []
    assert _snapshot(svc.db) == before
    assert {f['id'] for f in svc.db.current_facts(pid)} == {code, design_code}
    assert all(f['status'] == 'verified' for f in svc.db.current_facts(pid))
    assert svc.db.one("SELECT 1 FROM links WHERE rel='ctgov-current' AND dst=?", (code_source,)) is not None


def test_finding_and_chart_use_effective_not_stored_status(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    bad = _legacy(rc, trial, sid)
    good = _legacy(rc, trial, sid, value=3, quote=GENUINE_QUOTE,
                   context={**RESULT_CONTEXT, 'arm': 'Treatment B'})
    findings = {'findings': [
        {'title': '无依据结论', 'bullets': ['x'], 'fact_refs': [bad]},
        {'title': '有依据结论', 'bullets': ['y'], 'fact_refs': [good]}]}
    pending = render_report(svc.db, pid, 'B', findings=findings)
    assert '无依据结论' not in pending and '有依据结论' not in pending
    _requalify(svc.db, svc.cas, pid)
    rendered = render_report(svc.db, pid, 'B', findings=findings)
    assert '无依据结论' not in rendered and '有依据结论' in rendered


# --------------------------------------------------------------------------- C
def test_requalification_uses_pinned_older_source_not_later_url_version(env):
    svc, rc, pid, trial = env
    url = 'https://example.org/registry'
    older = _source(rc, text='入选标准：ALT < 3。'+GENUINE_QUOTE, url=url)
    config = svc.context(pid, svc.db.create_run(pid))
    newer = register_text(config.tool_ctx(), kind='web', url=url, text='入选标准：ALT < 3；修订后 ALT < 2。')
    assert newer and newer != older
    fact_id = _legacy(rc, trial, older, value=3, quote=GENUINE_QUOTE)
    summary = _requalify(svc.db, svc.cas, pid)
    assert summary['counts']['confirmed'] == 1
    receipt = _receipts(svc.db)[0]
    assert receipt['fact_id'] == fact_id and receipt['source_id'] == older
    assert svc.db.one('SELECT source_id FROM facts WHERE id=?', (fact_id,))['source_id'] == older
    assert _effective(svc.db, pid, fact_id)['status'] == 'verified'


def test_requalification_pinned_older_source_rejects_newer_only_text(env):
    svc, rc, pid, trial = env
    url = 'https://example.org/registry'
    older = _source(rc, text='入选标准：ALT < 3。', url=url)
    future_text = '入选标准：修订后 ALT < 2。EASI > 16。'
    other = svc.context(pid, svc.db.create_run(pid))
    register_text(other.tool_ctx(), kind='web', url=url, text=future_text)
    fact_id = _legacy(rc, trial, older, value=2, quote='ALT < 2')
    _requalify(svc.db, svc.cas, pid)
    assert _effective(svc.db, pid, fact_id)['status'] == 'unverified'
    assert _receipts(svc.db)[0]['verdict'] == 'invalidated'


@pytest.mark.parametrize(('case', 'verdict'), [
    ('unpinned', 'source_unpinned'),
    ('foreign', 'source_unavailable'),
    ('missing', 'source_unreadable'),
    ('tampered', 'source_digest_mismatch'),
])
def test_requalification_distinguishes_source_failures(env, case, verdict):
    svc, rc, pid, trial = env
    if case == 'unpinned':
        sid = None
    elif case == 'foreign':
        other = svc.create_project('其他项目', ['B'])
        other_rc = svc.context(other, svc.db.create_run(other))
        sid = register_text(other_rc.tool_ctx(), kind='web', url='https://example.org/other', text=ALT_SOURCE)
    elif case == 'missing':
        text = ALT_SOURCE.encode()
        sid = svc.db.add_source(pid, 'web', 'https://example.org/missing',
                                hashlib.sha256(b'never-stored').hexdigest(),
                                text_digest=hashlib.sha256(text).hexdigest())
    else:
        sid = _source(rc, text='入选标准：ALT < 3。', url='https://example.org/tampered')
        digest = svc.db.one('SELECT digest FROM sources WHERE id=?', (sid,))['digest']
        svc.cas._path(digest).write_bytes('入选标准：ALT 16。'.encode())
    fact_id = _legacy(rc, trial, sid, value=3, quote=GENUINE_QUOTE)
    before = _snapshot(svc.db)
    summary = _requalify(svc.db, svc.cas, pid)
    assert summary['counts'][verdict] == 1
    assert svc.db.query('SELECT * FROM facts ORDER BY rowid') == before['facts']
    assert svc.db.one('SELECT status FROM facts WHERE id=?', (fact_id,))['status'] == 'verified'
    receipt = _receipts(svc.db)[0]
    assert receipt['fact_id'] == fact_id and receipt['verdict'] == verdict
    assert receipt['source_id'] == sid
    effective = _effective(svc.db, pid, fact_id)
    assert effective['status'] == 'unverified'
    assert effective['verdict'] == verdict and effective['verdict_note']


def test_unreadable_source_is_retried_after_cas_recovery(env):
    svc, rc, pid, trial = env
    text = '入选标准：ALT < 3。'+GENUINE_QUOTE
    raw, encoded = text.encode(), text.encode()
    sid = svc.db.add_source(pid, 'web', 'https://example.org/recovered',
                            hashlib.sha256(raw).hexdigest(),
                            text_digest=hashlib.sha256(encoded).hexdigest())
    fact_id = _legacy(rc, trial, sid, value=3, quote=GENUINE_QUOTE)
    first = _requalify(svc.db, svc.cas, pid)
    assert first['counts']['source_unreadable'] == 1
    assert _effective(svc.db, pid, fact_id)['status'] == 'unverified'
    svc.cas.put(raw)
    svc.cas.put(encoded)
    second = _requalify(svc.db, svc.cas, pid)
    assert second['counts']['confirmed'] == 1
    assert _effective(svc.db, pid, fact_id)['status'] == 'verified'
    assert [r['verdict'] for r in _receipts(svc.db)] == ['source_unreadable', 'confirmed']
    assert _requalify(svc.db, svc.cas, pid)['counts']['skipped'] == 1


# --------------------------------------------------------------------------- D
def test_same_rule_replay_does_not_append_duplicate_receipt(env):
    svc, rc, _, _ = env
    url = 'https://example.org/criteria'
    _source(rc, url=url)
    _adopt(rc, [_proposal(rc, url)])
    facts = svc.db.query('SELECT * FROM facts ORDER BY rowid')
    assert len(_receipts(svc.db)) == 1
    _adopt(rc, [_proposal(rc, url)])
    assert svc.db.query('SELECT * FROM facts ORDER BY rowid') == facts
    assert len(_receipts(svc.db)) == 1


def test_rule_bump_same_run_reassesses_without_duplicate_fact(env, monkeypatch):
    svc, rc, pid, _ = env
    url = 'https://example.org/criteria'
    _source(rc, url=url)
    _adopt(rc, [_proposal(rc, url)])
    facts = svc.db.query('SELECT * FROM facts ORDER BY rowid')
    first = _receipts(svc.db)[0]
    assert first['rule'] == _assessment().rule_identity()
    monkeypatch.setattr(_assessment(), 'rule_identity', lambda: 'quote-test-next-rule')
    _adopt(rc, [_proposal(rc, url)])
    assert svc.db.query('SELECT * FROM facts ORDER BY rowid') == facts
    receipts = _receipts(svc.db)
    assert {r['rule'] for r in receipts} == {first['rule'], 'quote-test-next-rule'}
    fact = svc.db.current_facts(pid)[0]
    assert fact['status'] == 'verified' and fact['verdict_rule'] == 'quote-test-next-rule'


def test_malformed_or_mismatched_receipt_cannot_certify(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    fact_id = _legacy(rc, trial, sid, value=3, quote=GENUINE_QUOTE)
    rule = _assessment().rule_identity()
    svc.db.log_step(rc.run_id, 'requalification', 'verify', 0, 'fact_verdict', {
        'project_id': pid, 'fact_id': fact_id, 'fact_digest': '0' * 64, 'rule': rule,
        'stored_status': 'verified', 'status': 'verified', 'verdict': 'confirmed', 'reason': ''})
    svc.db.log_step(rc.run_id, 'requalification', 'verify', 0, 'fact_verdict', '{broken')
    assert _effective(svc.db, pid, fact_id)['status'] == 'unverified'
    _requalify(svc.db, svc.cas, pid)
    assert _effective(svc.db, pid, fact_id)['status'] == 'verified'
    latest = _receipts(svc.db)[-1]
    assert latest['fact_id'] == fact_id and latest['verdict'] == 'confirmed' and latest['fact_digest'] != '0' * 64


@pytest.mark.parametrize('changes',[
    {'source_id':'src_wrong'}, {'source_digest':'0'*64}, {'text_digest':'0'*64},
    {'quote_len':999}, {'quote_start':None},
    {'source_id':[]}, {'verdict':{}},
])
def test_otherwise_complete_receipt_cannot_certify_a_different_source_or_quote(changes,env):
    svc,rc,pid,trial=env
    sid=_source(rc)
    fid=_legacy(rc,trial,sid,value=3,quote=GENUINE_QUOTE)
    _requalify(svc.db,svc.cas,pid)
    receipt={**_receipts(svc.db)[-1],**changes}
    svc.db.log_step(rc.run_id,'requalification','verify',0,'fact_verdict',receipt)
    assert _effective(svc.db,pid,fid)['status']=='unverified'


def test_fact_assessment_identity_preserves_json_string_and_numeric_types(env):
    svc,rc,pid,trial=env
    fid=_legacy(rc,trial,_source(rc),value=3,quote=GENUINE_QUOTE)
    number=svc.db.raw_current_facts(pid)[0]
    string=deepcopy(number)
    string['value']='3'
    assert number['id']==fid and _assessment().fact_digest(number)!=_assessment().fact_digest(string)


def test_invalid_source_digest_never_reaches_a_file_read(env,monkeypatch):
    svc,rc,pid,trial=env
    sid=_source(rc)
    _legacy(rc,trial,sid,value=3,quote=GENUINE_QUOTE)
    svc.db.execute('UPDATE sources SET text_digest=? WHERE id=?',('../../unrelated-file',sid))
    reads=[]
    monkeypatch.setattr(svc.cas,'get',lambda digest:reads.append(digest) or b'')
    assert _requalify(svc.db,svc.cas,pid)['counts']['source_unavailable']==1
    assert reads==[]


def test_simultaneous_passes_recheck_receipt_idempotency_under_the_write_lock(env,monkeypatch):
    svc,rc,pid,trial=env
    _legacy(rc,trial,_source(rc),value=3,quote=GENUINE_QUOTE)
    barrier=threading.Barrier(2)
    original=_assessment().inspect
    results,errors=[],[]

    def inspect(*args,**kwargs):
        result=original(*args,**kwargs)
        barrier.wait(5)
        return result

    def run():
        try:results.append(_requalify(svc.db,svc.cas,pid))
        except Exception as exc:errors.append(exc)  # noqa: BLE001 - Thread failures are explicitly asserted.

    monkeypatch.setattr(_assessment(),'inspect',inspect)
    threads=[threading.Thread(target=run) for _ in range(2)]
    for thread in threads:thread.start()
    for thread in threads:thread.join(8)
    assert not errors and all(not t.is_alive() for t in threads)
    assert len(results)==2 and len(_receipts(svc.db))==1
    assert sorted(r['counts']['skipped'] for r in results)==[0,1]


def test_receipt_write_failure_rolls_back_adoption(env, monkeypatch):
    svc, rc, pid, _ = env
    url = 'https://example.org/criteria'
    _source(rc, url=url)
    facts = svc.db.query('SELECT * FROM facts ORDER BY rowid')
    entities = svc.db.entities(pid)
    original = rc.db.log_step

    def failing(run_id, stage, skill, step, role, content):
        if role == 'fact_verdict':
            raise RuntimeError('receipt-write-failed')
        return original(run_id, stage, skill, step, role, content)

    monkeypatch.setattr(rc.db, 'log_step', failing)
    with pytest.raises(RuntimeError, match='receipt-write-failed'):
        _adopt(rc, [_proposal(rc, url)])
    assert svc.db.query('SELECT * FROM facts ORDER BY rowid') == facts
    assert svc.db.entities(pid) == entities
    assert _receipts(svc.db) == []


# --------------------------------------------------------------------------- E
def test_dry_run_writes_nothing_and_real_pass_appends_only_receipts(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    bad = _legacy(rc, trial, sid)
    good = _legacy(rc, trial, sid, value=3, quote=GENUINE_QUOTE,
                   context={**RESULT_CONTEXT, 'arm': 'Treatment B'})
    before = _snapshot(svc.db)
    ledger = len(svc.db.query('SELECT * FROM agent_steps'))
    dry = _requalify(svc.db, svc.cas, pid, dry_run=True)
    assert dry['dry_run'] is True
    assert dry['counts']['scanned'] == 2 and dry['counts']['confirmed'] == 1
    assert dry['counts']['invalidated'] == 1 and dry['counts']['skipped'] == 0
    assert len(svc.db.query('SELECT * FROM agent_steps')) == ledger
    assert _snapshot(svc.db) == before
    assert _effective(svc.db, pid, good)['status'] == 'unverified'  # no implicit write
    real = _requalify(svc.db, svc.cas, pid)
    assert real['dry_run'] is False and real['counts'] == dry['counts']
    assert svc.db.query('SELECT * FROM facts ORDER BY rowid') == before['facts']
    assert len(svc.db.query('SELECT * FROM agent_steps')) == ledger + 2
    assert _effective(svc.db, pid, good)['status'] == 'verified'
    assert _effective(svc.db, pid, bad)['status'] == 'unverified'
    again = _requalify(svc.db, svc.cas, pid)
    assert again['counts']['skipped'] == 2
    assert len(svc.db.query('SELECT * FROM agent_steps')) == ledger + 2


def test_requalification_scope_excludes_superseded_history(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    old = _legacy(rc, trial, sid)
    new = _legacy(rc, trial, sid, value=3, quote=GENUINE_QUOTE, supersedes=old)
    assert [f['id'] for f in svc.db.current_facts(pid) if f['field'] == 'result.primary.value'] == [new]
    summary = _requalify(svc.db, svc.cas, pid)
    assert summary['counts']['scanned'] == 1 and summary['counts']['confirmed'] == 1
    assert [r['fact_id'] for r in _receipts(svc.db)] == [new]
    assert svc.db.one('SELECT status FROM facts WHERE id=?', (old,))['status'] == 'verified'


def test_demoted_fact_still_accepts_a_valid_revision_target(env):
    svc, rc, pid, trial = env
    url = 'https://example.org/amendment'
    old_source = _source(rc, text='The planned sample size was 900 participants.',
                         url='https://example.org/old')
    old = _legacy(rc, trial, old_source, value=16, quote='The planned sample size was 16 participants.',
                  field='design.sample_size', context={'enrollment_type': 'ESTIMATED'})
    assert _effective(svc.db, pid, old)['status'] == 'unverified'
    _source(rc, text='The planned sample size was 900 participants.', url=url)
    _adopt(rc, [{**_proposal(rc, url, value=900, quote='The planned sample size was 900 participants.',
                             field='design.sample_size', supersedes=old),
                 'endpoint': None, 'unit': None, 'stat_type': None, 'timepoint': None,
                 'population': None, 'arm': None, 'enrollment_type': 'ESTIMATED'}],
           stage='extract_design')
    facts = svc.db.query('SELECT * FROM facts ORDER BY rowid')
    adopted = next(f for f in facts if f['id'] != old)
    assert adopted['supersedes'] == old and adopted['status'] == 'verified'
    assert svc.db.one('SELECT * FROM facts WHERE id=?', (old,))['status'] == 'verified'
    assert [f['id'] for f in svc.db.current_facts(pid)] == [adopted['id']]
    history = report_data(svc.db, pid, 'C')['rows'][0]['sources']['sample_size'][0]['history']
    assert history[0]['fact_id'] == old
    assert history[0]['quote'] == 'The planned sample size was 16 participants.'


def test_valid_and_failed_revision_lineage_survives_requalification(env):
    svc, rc, pid, trial = env
    url = 'https://example.org/amendment'
    size_text = 'The planned sample size was 900 participants.'
    _source(rc, text=size_text, url=url)
    second, _ = svc.db.upsert_entity(pid, 'trial', 'NCT00000003')
    code_old = _legacy(rc, trial, None, value=941, quote='Planned size 941.', status='verified',
                       field='design.sample_size', extracted_by='code:ctgov',
                       context={'enrollment_type': 'ESTIMATED'})
    _adopt(rc, [{**_proposal(rc, url, value=900, quote=size_text,
                             field='design.sample_size', supersedes=code_old),
                 'entity': 'NCT00000002', 'endpoint': None, 'unit': None, 'stat_type': None,
                 'timepoint': None, 'population': None, 'arm': None, 'enrollment_type': 'ESTIMATED'}],
           stage='extract_design')
    _legacy(rc, second, None, value=941, quote='Planned size 941.', status='verified',
            field='design.sample_size', extracted_by='code:ctgov',
            context={'enrollment_type': 'ESTIMATED'})
    rejected = _legacy(rc, second, None, value=999, quote='Not in any source', status='unverified',
                       field='design.sample_size',
                       context={'enrollment_type': 'ESTIMATED'})
    _requalify(svc.db, svc.cas, pid)
    current = {(f['entity_id'], f['value']) for f in svc.db.current_facts(pid)
               if f['field'] == 'design.sample_size'}
    assert (trial, 900) in current and (trial, 941) not in current
    assert (second, 941) in current and (second, 999) in current
    assert svc.db.one('SELECT supersedes FROM facts WHERE id=?', (rejected,))['supersedes'] is None
    assert svc.db.one('SELECT status FROM facts WHERE id=?', (code_old,))['status'] == 'verified'
    rows = {row['trial']: row for row in report_data(svc.db, pid, 'C')['rows']}
    assert rows['NCT00000002']['sample_size'] == 900
    assert rows['NCT00000003']['sample_size'] == 941


def test_cross_context_observations_survive_requalification(env):
    svc, rc, pid, trial = env
    url = 'https://example.org/amendment'
    size_text = 'The planned sample size was 900 participants.'
    _source(rc, text=size_text, url=url)
    code_old = _legacy(rc, trial, None, value=941, quote='Planned size 941.', status='verified',
                       field='design.sample_size', extracted_by='code:ctgov',
                       context={'enrollment_type': 'ESTIMATED'})
    _adopt(rc, [{**_proposal(rc, url, value=900, quote=size_text,
                             field='design.sample_size', supersedes=code_old),
                 'entity': 'NCT00000002', 'endpoint': None, 'unit': None, 'stat_type': None,
                 'timepoint': None, 'population': None, 'arm': None, 'enrollment_type': 'ACTUAL'}],
           stage='extract_design')
    _requalify(svc.db, svc.cas, pid)
    current = [f for f in svc.db.current_facts(pid) if f['field'] == 'design.sample_size']
    assert {f['value'] for f in current} == {941, 900}
    assert all(f['status'] == 'verified' for f in current)
    assert all(f['supersedes'] is None for f in current)
    row = report_data(svc.db, pid, 'C')['rows'][0]
    assert row.get('sample_size') is None and len(row['observations']['sample_size']) == 2


def test_cli_requalify_is_explicit_offline_and_reports_counts(env, settings, monkeypatch, capsys):
    svc, rc, pid, trial = env
    sid = _source(rc)
    fact_id = _legacy(rc, trial, sid)
    monkeypatch.setenv('CIW_DATA_DIR', str(settings.data_dir))
    from ciw2.cli import main
    assert main(['requalify', '--project', pid, '--dry-run']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['dry_run'] is True and payload['counts']['scanned'] == 1
    assert _receipts(svc.db) == []
    assert main(['requalify', '--project', pid]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['dry_run'] is False and payload['counts']['invalidated'] == 1
    assert _effective(svc.db, pid, fact_id)['status'] == 'unverified'
    assert main(['requalify', '--project', 'prj_missing']) != 0
    assert 'Traceback' not in capsys.readouterr().err


def test_export_exposes_effective_and_stored_status(env):
    svc, rc, pid, trial = env
    sid = _source(rc)
    fact_id = _legacy(rc, trial, sid)
    _requalify(svc.db, svc.cas, pid)
    payload = fact_export(svc.db, pid)
    row = next(f for f in payload['facts'] if f['id'] == fact_id)
    assert row['status'] == 'unverified' and row['stored_status'] == 'verified'
    assert row['verdict_note'] == '原文中找不到该片段'
    csv_text = encode_export(payload, 'csv').decode('utf-8-sig')
    header, line = csv_text.splitlines()[0], csv_text.splitlines()[1]
    assert 'stored_status' in header and 'verdict_note' in header
    assert 'verified' in line and 'unverified' in line
