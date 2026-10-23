"""Atomic native registry documents reuse the existing source/fact/pointer contract."""
import json
from copy import deepcopy

import pytest
from test_china_design import design_capture

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import china_ingest
from ciw2.sources.china_detail import parse_capture
from ciw2.sources.http import register_text


@pytest.fixture
def ctx(settings):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('登记适应症',['C'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def registered(ctx,raw):
    text=parse_capture(raw,ctr=raw['registry_id'],detail_id=raw['detail_id'])['source_text']
    return register_text(ctx,kind='chinadrugtrials',url=raw['url'],text=text,
        raw=json.dumps(raw,ensure_ascii=False).encode(),meta={'request_context':{
            'registry':'chinadrugtrials','section':'trial_detail','registry_id':raw['registry_id'],'detail_id':raw['detail_id']}})


def adopt(ctx,raw,sid):return china_ingest._activate_design(ctx,raw['registry_id'],raw,sid,'china:detail')


def planned(ctx):
    return [f['value'] for f in ctx.db.current_facts(ctx.project_id) if f['field']=='design.sample_size'
            and f['context']['enrollment_type']=='ESTIMATED' and f['context']['population']=='国内']


def test_snapshot_update_replay_and_reactivation_keep_immutable_history_and_external_facts(ctx):
    a=design_capture()
    b=deepcopy(a)
    b['tables'][3]['rows'][0][1]='国内:88；国际:120；'
    sa,sb=registered(ctx,a),registered(ctx,b)
    first=adopt(ctx,a,sa)
    assert planned(ctx)==[72] and first['facts_added']>0
    original=ctx.db.query('SELECT * FROM facts ORDER BY id')
    assert adopt(ctx,a,sa)['facts_added']==0
    independent=ctx.db.add_fact({'project_id':ctx.project_id,'entity_id':first['entity_id'],'field':'design.control',
        'value':'论文独立补充','tier':'standard','status':'verified','source_id':sa,'quote':'论文独立补充',
        'extracted_by':'llm:fixture'})
    adopt(ctx,b,sb)
    assert planned(ctx)==[88]
    assert ctx.db.one('SELECT id FROM facts WHERE id=?',(independent,))
    assert any(f['id']==independent for f in ctx.db.current_facts(ctx.project_id))
    assert all(ctx.db.one('SELECT * FROM facts WHERE id=?',(f['id'],))==f for f in original)
    count=ctx.db.one('SELECT count(*) n FROM facts')['n']
    assert adopt(ctx,a,sa)['facts_added']==0 and planned(ctx)==[72]
    assert ctx.db.one('SELECT count(*) n FROM facts')['n']==count


def test_mid_bundle_failure_preserves_old_current_and_trial_attrs(ctx,monkeypatch):
    raw=design_capture()
    adopt(ctx,raw,registered(ctx,raw))
    before=ctx.db.current_facts(ctx.project_id)
    entities=ctx.db.entities(ctx.project_id)
    pointers=ctx.db.query("SELECT * FROM links WHERE rel='chinadrugtrials-current'")
    changed=deepcopy(raw)
    changed['tables'][0]['rows'][2][1]='新版本适应症原文'
    sid=registered(ctx,changed)
    original=ctx.db.add_fact
    calls=[]
    def fail(fact):
        calls.append(fact)
        if len(calls)==3:raise RuntimeError('injected bundle write failure')
        return original(fact)
    monkeypatch.setattr(ctx.db,'add_fact',fail)
    with pytest.raises(RuntimeError):adopt(ctx,changed,sid)
    assert ctx.db.current_facts(ctx.project_id)==before and ctx.db.entities(ctx.project_id)==entities
    assert ctx.db.query("SELECT * FROM links WHERE rel='chinadrugtrials-current'")==pointers
    assert ctx.db.one('SELECT id FROM sources WHERE id=?',(sid,))  # Raw observation survives failure.


@pytest.mark.parametrize('damage',['wrong_ctr','changed_payload','cross_project','wrong_text','wrong_run'])
def test_source_identity_version_and_plaintext_must_match_before_adoption(ctx,damage):
    raw=design_capture()
    sid=registered(ctx,raw)
    if damage=='wrong_ctr':
        with pytest.raises(ValueError):china_ingest._activate_design(ctx,'CTR99999999',raw,sid,'china:detail')
        assert not ctx.db.current_facts(ctx.project_id)
        return
    if damage=='changed_payload':raw['basic'][1][1]='已完成'
    elif damage=='cross_project':ctx.db.execute('UPDATE sources SET project_id=? WHERE id=?',('another',sid))
    elif damage=='wrong_run':ctx.run_id='another_project_run'
    else:ctx.db.execute('UPDATE sources SET text_digest=? WHERE id=?',(ctx.cas.put(b'wrong text'),sid))
    with pytest.raises(ValueError):adopt(ctx,raw,sid)
    assert not ctx.db.current_facts(ctx.project_id) and not ctx.db.entities(ctx.project_id)
