"""Independent-review root cases, exercised through actual adoption and renderers."""
import re
from html import unescape

import pytest
from test_nmpa_ingest import certificate, drug, registered

from ciw2.render.portal import render_report
from ciw2.service import Service
from ciw2.sources import nmpa_ingest


@pytest.fixture
def ctx(settings):
    svc=Service(settings)
    pid=svc.create_project('特应性皮炎',['A','B','C'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


@pytest.mark.parametrize('bad_label',['name_zh','alias'])
@pytest.mark.parametrize('prior_proof',[False,True])
def test_discovery_label_cannot_certify_a_different_product(ctx,bad_label,prior_proof):
    drug(ctx,'Stapokibart Injection',name_zh='度普利尤单抗注射液' if bad_label=='name_zh' else None,
         aliases=['度普利尤单抗注射液'] if bad_label=='alias' else [])
    if prior_proof:
        correct=certificate(name='司普奇拜单抗注射液',name_en='Stapokibart Injection')
        assert nmpa_ingest.activate_source(ctx,registered(ctx,correct))['status']=='adopted'
    wrong=certificate('b','国药准字SJ20235004',name='度普利尤单抗注射液',name_en='Dupilumab Injection')
    before=ctx.db.query('SELECT * FROM facts')
    out=nmpa_ingest.activate_source(ctx,registered(ctx,wrong))
    assert out['status']=='unresolved' and out['facts_added']==0
    assert ctx.db.query('SELECT * FROM facts')==before


@pytest.mark.parametrize('newer_first',[True,False])
def test_certificate_current_is_project_wide_not_per_target_entity(ctx,newer_first):
    drug(ctx,'Drug A Injection');drug(ctx,'Drug B Injection')
    old=registered(ctx,certificate(observed='2026-10-23T00:00:00Z'))
    new=registered(ctx,certificate(observed='2026-10-24T00:00:00Z',name='药物乙注射液',name_en='Drug B Injection'))
    nmpa_ingest.activate_source(ctx,new if newer_first else old)
    out=nmpa_ingest.activate_source(ctx,old if newer_first else new)
    assert out['status']==('stale' if newer_first else 'unresolved')
    assert len(ctx.db.query("SELECT * FROM links WHERE rel='nmpa-current'"))==1
    assert len(ctx.db.current_facts(ctx.project_id))==3


def test_new_bad_discovery_alias_does_not_revoke_source_binding(ctx):
    drug(ctx,'Drug A Injection')
    sid=registered(ctx,certificate())
    nmpa_ingest.activate_source(ctx,sid)
    drug(ctx,'Different Product',aliases=['Drug A Injection'])
    before=ctx.db.current_facts(ctx.project_id)
    assert nmpa_ingest.activate_source(ctx,sid)['status']=='already_current'
    assert ctx.db.current_facts(ctx.project_id)==before


@pytest.mark.parametrize('holder_present',[True,False])
def test_legal_holder_dates_are_readable_and_expired_record_is_not_current_effect_claim(ctx,holder_present):
    eid=drug(ctx,'Drug A Injection')
    raw=certificate(observed='2026-10-23T00:00:00Z')
    raw['rows'][8][1]='2026-01-23'
    if not holder_present:raw['rows'][2][1]='————'
    sid=registered(ctx,raw)
    nmpa_ingest.activate_source(ctx,sid)
    trial,_=ctx.db.upsert_entity(ctx.project_id,'trial','NCT00000001')
    ctx.db.link(ctx.project_id,eid,'drug-trial',trial)
    for field,value,context in [('design.phase','phase3',{}),
        ('design.arms',[{'label':'Active','interventions':['Drug: Drug A Injection']}],{}),
        ('result.primary.value',24,{'arm':'Active','endpoint':'Score','unit':'points','stat_type':'mean','timepoint':'Week 12'})]:
        ctx.db.add_fact({'project_id':ctx.project_id,'entity_id':trial,'field':field,'value':value,
            'context':context,'source_id':sid,'tier':'standard','status':'verified','extracted_by':'code:test'})
    for report in 'ABC':
        html=render_report(ctx.db,ctx.project_id,report)
        visible=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>','',html,flags=re.DOTALL)
        text=unescape(re.sub(r'<[^>]+>','',visible))
        assert '有效期至 2026-01-23' in text and '获取 2026-10-23' in text
        assert '发证 2025-02-18' in text
        assert ('许可记录持有人' in text)==holder_present


def test_previous_adoption_rule_cannot_bootstrap_its_own_formal_names(ctx,monkeypatch):
    drug(ctx,'Drug A Injection')
    sid=registered(ctx,certificate())
    nmpa_ingest.activate_source(ctx,sid)
    assert len(ctx.db.current_facts(ctx.project_id))==3
    old=ctx.db.query('SELECT * FROM facts')
    monkeypatch.setattr(nmpa_ingest,'EXTRACTOR_VERSION','next-identity-rule')
    assert ctx.db.current_facts(ctx.project_id)==[]
    assert ctx.db.query('SELECT * FROM facts')==old
    assert nmpa_ingest.activate_source(ctx,sid)['status']=='adopted'
    assert len(ctx.db.current_facts(ctx.project_id))==3


@pytest.mark.parametrize('bad_rule',['missing',None,'legacy-rule'])
def test_incomplete_rule_binding_is_repaired_not_already_current(ctx,bad_rule):
    import json

    drug(ctx,'Drug A Injection')
    sid=registered(ctx,certificate())
    nmpa_ingest.activate_source(ctx,sid)
    row=ctx.db.one("SELECT * FROM links WHERE rel='nmpa-current'")
    attrs=json.loads(row['attrs'])
    if bad_rule=='missing':attrs.pop('extractor_version')
    else:attrs['extractor_version']=bad_rule
    ctx.db.execute("UPDATE links SET attrs=? WHERE rel='nmpa-current'",(json.dumps(attrs),))
    old=ctx.db.query('SELECT * FROM facts')
    assert ctx.db.current_facts(ctx.project_id)==[]
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='adopted' and out['facts_added']==0
    assert len(ctx.db.current_facts(ctx.project_id))==3 and ctx.db.query('SELECT * FROM facts')==old
    assert nmpa_ingest.activate_source(ctx,sid)['status']=='already_current'
