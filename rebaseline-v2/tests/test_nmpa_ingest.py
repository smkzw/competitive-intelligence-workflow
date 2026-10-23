"""Atomic adoption of an already-captured NMPA certificate; literal, versioned, no fetch."""
import base64
import json

import pytest
from test_nmpa_detail import DOMESTIC, FOREIGN, NUMBER, domestic

from ciw2.service import Service
from ciw2.sources import china_browser, nmpa_detail, nmpa_ingest
from ciw2.sources.http import register_text
from ciw2.verify.quote import check_quote


def nmpa_url(seed):
    token=base64.b64encode(f'id={seed*32}&itemId={seed*32}'.encode()).decode()
    return 'https://datasearch.nmpa.gov.cn/datasearch/search-info.html?nmpa='+token


def certificate(seed='a',number=NUMBER,observed='2026-10-24T00:00:00Z',
                name='药物甲注射液',name_en='Drug A Injection',
                holder_zh='————',holder_en='Holder Legal Entity'):
    return {'url':nmpa_url(seed),'category':FOREIGN,'registration_number':number,
        'heading':FOREIGN+' ——“'+number+'”基本信息','observed_at':observed,
        'rows':[['注册证号',number],['上市许可持有人中文名称',holder_zh],
            ['上市许可持有人英文名称',holder_en],['产品名称（中文）',name],
            ['产品名称（英文）',name_en],['生产厂商（英文）','Factory Company'],
            ['规格（中文）','300mg（2.0mL）/支'],['发证日期','2025-02-18'],
            ['有效期截止日','2030-01-23'],['境内责任人名称','境内责任人甲公司'],['注','详情']]}


def registered(ctx,raw,run_id=None):
    parsed=nmpa_detail.parse_capture(raw,url=raw['url'],
        registration_number=raw['registration_number'],category=raw['category'])
    scope={'tool':'nmpa_product_detail','project_id':ctx.project_id,
        'run_id':run_id or ctx.run_id,'space':71,'url':raw['url'],
        'category':raw['category'],'registration_number':raw['registration_number']}
    return register_text(ctx,kind='nmpa',url=raw['url'],text=parsed['source_text'],
        raw=json.dumps(raw,ensure_ascii=False).encode(),title=raw['heading'],
        meta={'method':'ego_public_ui','request_context':scope,
              'extractor_version':nmpa_detail.code_hash(),'observation':'browser_checked'})


def drug(ctx,name,name_zh=None,aliases=None,scope=None):
    eid,_=ctx.db.upsert_entity(ctx.project_id,'drug',name,name_zh=name_zh,aliases=aliases or [])
    if scope is not None:
        ctx.db.set_scope(eid,scope,'fixture')
    return eid


def rows(ctx,sql,params=()):
    return ctx.db.query(sql,params)


def facts(ctx):
    return ctx.db.query("SELECT * FROM facts WHERE extracted_by='code:nmpa' ORDER BY field")


def links(ctx):
    return ctx.db.query("SELECT * FROM links WHERE rel='nmpa-current' ORDER BY dst")


def steps(ctx):
    return ctx.db.query("SELECT * FROM agent_steps WHERE role='source_activation' ORDER BY id")


@pytest.fixture
def ctx(settings):
    svc=Service(settings)
    pid=svc.create_project('研究适应症',['A'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def test_exact_bilingual_certificate_adopts_literal_identity_and_holder_only(ctx,monkeypatch):
    eid=drug(ctx,'Drug A Injection',name_zh='药物甲注射液')
    raw=certificate(); sid=registered(ctx,raw)
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**k:pytest.fail('activation must not fetch'))
    entities=ctx.db.entities(ctx.project_id,'drug')
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(sid,))
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='adopted' and out['entity_id']==eid and out['source_id']==sid
    assert out['facts_added']==3
    by={f['field']:f for f in facts(ctx)}
    assert set(by)=={'identity.name_zh','identity.name_en','status.china_mah'}
    assert by['status.china_mah']['tier']=='critical'
    assert by['identity.name_zh']['tier']=='standard' and by['identity.name_en']['tier']=='standard'
    assert all(f['supersedes'] is None for f in facts(ctx))
    assert json.loads(by['identity.name_zh']['value'])=='药物甲注射液'
    assert json.loads(by['identity.name_en']['value'])=='Drug A Injection'
    assert json.loads(by['status.china_mah']['value'])=='Holder Legal Entity'
    assert by['identity.name_zh']['quote']=='产品名称（中文）\t药物甲注射液'
    assert by['identity.name_en']['quote']=='产品名称（英文）\tDrug A Injection'
    assert by['status.china_mah']['quote']=='上市许可持有人英文名称\tHolder Legal Entity'
    context=json.loads(by['status.china_mah']['context'])
    assert context['role']=='marketing_authorization_holder' and context['jurisdiction']=='CN'
    assert context['registration_number']==NUMBER and context['category']==FOREIGN
    assert context['observed_at']==raw['observed_at'] and context['strength']=='300mg（2.0mL）/支'
    assert context['issue_date']=='2025-02-18' and context['valid_until']=='2030-01-23'
    assert context['approval_date'] is None
    parsed=nmpa_detail.parse_capture(raw,url=raw['url'],registration_number=NUMBER,category=FOREIGN)
    for fact in facts(ctx):
        value=json.loads(fact['value']); quote=fact['quote']
        checked=check_quote(parsed['source_text'],quote,value)
        assert checked.ok and (fact['quote_start'],fact['quote_end'])==(checked.start,checked.end)
        assert fact['status']=='verified' and fact['source_id']==sid and fact['entity_id']==eid
        assert json.loads(fact['context'])['source_snapshot']==out['snapshot']
    pointer=links(ctx)
    assert len(pointer)==1 and pointer[0]['src']==eid and pointer[0]['dst']==sid
    attrs=json.loads(pointer[0]['attrs'])
    assert attrs['snapshot']==out['snapshot'] and attrs['observed_at']==raw['observed_at']
    assert attrs['registration_number']==NUMBER and attrs['category']==FOREIGN
    assert attrs['extractor_version']==nmpa_ingest.EXTRACTOR_VERSION
    assert ctx.db.entities(ctx.project_id,'drug')==entities
    assert ctx.db.one('SELECT * FROM sources WHERE id=?',(sid,))==source
    assert json.loads(steps(ctx)[0]['content'])['facts_added']==3


def test_holder_is_not_factory_or_domestic_responsible_person(ctx):
    drug(ctx,'药物甲注射液')
    sid=registered(ctx,certificate())
    assert nmpa_ingest.activate_source(ctx,sid)['status']=='adopted'
    values={f['field']:json.loads(f['value']) for f in facts(ctx)}
    assert values['status.china_mah']=='Holder Legal Entity'
    assert 'Factory Company' not in values.values() and '境内责任人甲公司' not in values.values()
    assert {f['field'] for f in facts(ctx)}=={
        'identity.name_zh','identity.name_en','status.china_mah'}


def test_missing_holder_emits_no_fact_and_never_borrows_factory_or_agent(ctx):
    drug(ctx,'药物甲注射液')
    sid=registered(ctx,certificate(holder_zh='————',holder_en='————'))
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='adopted' and out['facts_added']==2
    assert {f['field'] for f in facts(ctx)}=={'identity.name_zh','identity.name_en'}
    assert 'Factory Company' not in {json.loads(f['value']) for f in facts(ctx)}
    assert '境内责任人甲公司' not in {json.loads(f['value']) for f in facts(ctx)}


def test_multiple_certificates_keep_separate_current_pointers(ctx):
    eid=drug(ctx,'药物甲注射液')
    first=certificate('a',NUMBER,'2026-10-24T00:00:00Z')
    second=certificate('b','国药准字SJ20240002','2026-10-24T01:00:00Z',holder_en='Second Holder')
    s1,s2=registered(ctx,first),registered(ctx,second)
    assert nmpa_ingest.activate_source(ctx,s1)['status']=='adopted'
    assert nmpa_ingest.activate_source(ctx,s2)['status']=='adopted'
    pointers={json.loads(p['attrs'])['registration_number']:p for p in links(ctx)}
    assert set(pointers)=={NUMBER,'国药准字SJ20240002'}
    assert pointers[NUMBER]['dst']==s1 and pointers['国药准字SJ20240002']['dst']==s2
    assert all(p['src']==eid for p in links(ctx))
    holders={json.loads(f['context'])['registration_number']:json.loads(f['value'])
             for f in facts(ctx) if f['field']=='status.china_mah'}
    assert holders=={NUMBER:'Holder Legal Entity','国药准字SJ20240002':'Second Holder'}


def test_newer_certificate_clears_absent_holder_by_pointer_replacement_only(ctx):
    drug(ctx,'药物甲注射液')
    old=certificate('a',NUMBER,'2026-10-24T00:00:00Z')
    s1=registered(ctx,old)
    assert nmpa_ingest.activate_source(ctx,s1)['status']=='adopted'
    old_holder=next(f for f in facts(ctx) if f['field']=='status.china_mah')
    new=certificate('a',NUMBER,'2026-10-25T00:00:00Z',holder_zh='————',holder_en='————')
    s2=registered(ctx,new)
    out=nmpa_ingest.activate_source(ctx,s2)
    assert out['status']=='adopted' and out['facts_added']==2
    assert links(ctx)[0]['dst']==s2
    current=[f for f in facts(ctx) if f['field']=='status.china_mah'
             and json.loads(f['context'])['source_snapshot']==out['snapshot']]
    assert current==[]
    assert 'Factory Company' not in {json.loads(f['value']) for f in facts(ctx)}
    assert ctx.db.one('SELECT * FROM facts WHERE id=?',(old_holder['id'],))==old_holder


def test_older_observation_never_rolls_current_back_and_replay_is_idempotent(ctx):
    drug(ctx,'药物甲注射液')
    older=certificate('a',NUMBER,'2026-10-24T00:00:00Z')
    newer=certificate('a',NUMBER,'2026-10-25T00:00:00Z',holder_en='New Holder')
    s1,s2=registered(ctx,older),registered(ctx,newer)
    nmpa_ingest.activate_source(ctx,s2)
    pointers=links(ctx); snapshot=rows(ctx,'SELECT * FROM facts ORDER BY id'); log=len(steps(ctx))
    stale=nmpa_ingest.activate_source(ctx,s1)
    assert stale['status']=='stale' and stale['facts_added']==0
    assert stale['reason']=='older_observation'
    assert links(ctx)==pointers and rows(ctx,'SELECT * FROM facts ORDER BY id')==snapshot
    assert len(steps(ctx))==log
    assert stale['current']['source_id']==s2
    replay=nmpa_ingest.activate_source(ctx,s2)
    assert replay['status']=='already_current' and replay['facts_added']==0
    assert replay['reason']=='already_current_certificate'
    assert links(ctx)==pointers and rows(ctx,'SELECT * FROM facts ORDER BY id')==snapshot
    assert len(steps(ctx))==log


def test_source_from_an_earlier_run_of_the_same_project_can_be_activated(ctx):
    eid=drug(ctx,'药物甲注射液')
    first_run=ctx.run_id
    sid=registered(ctx,certificate(),run_id=first_run)
    ctx.run_id=ctx.db.create_run(ctx.project_id)
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='adopted' and out['entity_id']==eid


def test_literal_alias_of_one_drug_is_a_valid_unique_target(ctx):
    eid=drug(ctx,'Drug A Injection',aliases=['药物甲注射液'])
    sid=registered(ctx,certificate())
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='adopted' and out['entity_id']==eid


@pytest.mark.parametrize('case',['no_match','bare_inn','ambiguous','excluded','ambiguous_with_excluded'])
def test_unresolved_target_writes_nothing(ctx,case):
    if case=='bare_inn':
        drug(ctx,'司普奇拜单抗')
        sid=registered(ctx,domestic())
    elif case=='ambiguous':
        drug(ctx,'药物甲注射液')
        drug(ctx,'Drug A Injection')
        sid=registered(ctx,certificate())
    elif case=='excluded':
        drug(ctx,'药物甲注射液',scope=False)
        sid=registered(ctx,certificate())
    elif case=='ambiguous_with_excluded':
        drug(ctx,'药物甲注射液',scope=False)
        drug(ctx,'Drug A Injection',scope=True)
        sid=registered(ctx,certificate())
    else:
        sid=registered(ctx,certificate())
    entities=ctx.db.entities(ctx.project_id)
    drug_ids=sorted(e['id'] for e in entities if e['type']=='drug')
    expected={'no_match':('no_literal_match',[]),'bare_inn':('no_literal_match',[]),
        'ambiguous':('ambiguous_literal_name',drug_ids),
        'excluded':('excluded_target',drug_ids),
        'ambiguous_with_excluded':('ambiguous_literal_name',drug_ids)}[case]
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='unresolved' and out['facts_added']==0
    assert (out['reason'],out['candidate_ids'])==expected
    assert facts(ctx)==[] and links(ctx)==[] and steps(ctx)==[]
    assert ctx.db.entities(ctx.project_id)==entities


@pytest.mark.parametrize('damage',['raw_tamper','raw_structure','raw_missing','text_mismatch','text_missing',
    'meta_json','no_scope','scope_project','scope_run_missing','scope_run_foreign','version',
    'scope_url','scope_number','scope_category','source_url','source_kind','source_project'])
def test_malformed_mismatched_or_unreadable_capture_fails_before_writes(ctx,damage):
    drug(ctx,'药物甲注射液')
    sid=registered(ctx,certificate())
    if damage=='raw_tamper':
        digest=ctx.db.one('SELECT digest FROM sources WHERE id=?',(sid,))['digest']
        (ctx.cas.root/digest[:2]/digest).write_bytes(b'{"tampered":true}')
    elif damage=='raw_structure':
        ctx.db.execute('UPDATE sources SET digest=? WHERE id=?',
            (ctx.cas.put(b'{"note":"not a certificate"}'),sid))
    elif damage=='raw_missing':
        ctx.db.execute('UPDATE sources SET digest=? WHERE id=?',('f'*64,sid))
    elif damage=='text_mismatch':
        ctx.db.execute('UPDATE sources SET text_digest=? WHERE id=?',
            (ctx.cas.put('非该证书原文'.encode()),sid))
    elif damage=='text_missing':
        ctx.db.execute('UPDATE sources SET text_digest=? WHERE id=?',('e'*64,sid))
    elif damage=='meta_json':
        ctx.db.execute('UPDATE sources SET meta=? WHERE id=?',('{',sid))
    elif damage=='no_scope':
        ctx.db.execute('UPDATE sources SET meta=? WHERE id=?',(json.dumps({}),sid))
    elif damage=='scope_project':
        other=ctx.db.create_project('其他项目',['A'])
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.project_id',?) WHERE id=?",
            (other,sid))
    elif damage=='scope_run_missing':
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.run_id','run_missing') WHERE id=?",
            (sid,))
    elif damage=='scope_run_foreign':
        other=ctx.db.create_project('其他项目',['A'])
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.run_id',?) WHERE id=?",
            (ctx.db.create_run(other),sid))
    elif damage=='version':
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.extractor_version','old') WHERE id=?",
            (sid,))
    elif damage=='scope_url':
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.url',?) WHERE id=?",
            (nmpa_url('z'),sid))
    elif damage=='scope_number':
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.registration_number',?) WHERE id=?",
            ('国药准字SJ20249999',sid))
    elif damage=='scope_category':
        ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.category',?) WHERE id=?",
            (DOMESTIC,sid))
    elif damage=='source_url':
        ctx.db.execute('UPDATE sources SET url=? WHERE id=?',(nmpa_url('z'),sid))
    elif damage=='source_kind':
        ctx.db.execute("UPDATE sources SET kind='ctgov' WHERE id=?",(sid,))
    else:
        ctx.db.execute("UPDATE sources SET project_id='other' WHERE id=?",(sid,))
    before=(rows(ctx,'SELECT * FROM sources'),rows(ctx,'SELECT * FROM facts'),
            rows(ctx,'SELECT * FROM links'),rows(ctx,'SELECT * FROM agent_steps'))
    with pytest.raises(ValueError):
        nmpa_ingest.activate_source(ctx,sid)
    assert (rows(ctx,'SELECT * FROM sources'),rows(ctx,'SELECT * FROM facts'),
            rows(ctx,'SELECT * FROM links'),rows(ctx,'SELECT * FROM agent_steps'))==before


def test_current_run_must_belong_to_project(ctx):
    drug(ctx,'药物甲注射液')
    sid=registered(ctx,certificate())
    other=ctx.db.create_project('其他项目',['A'])
    ctx.run_id=ctx.db.create_run(other)
    before=(rows(ctx,'SELECT * FROM facts'),rows(ctx,'SELECT * FROM links'))
    with pytest.raises(ValueError):
        nmpa_ingest.activate_source(ctx,sid)
    assert (rows(ctx,'SELECT * FROM facts'),rows(ctx,'SELECT * FROM links'))==before


def test_transactional_fact_failure_rolls_back_partial_facts_and_pointer(ctx,monkeypatch):
    eid=drug(ctx,'药物甲注射液')
    sid=registered(ctx,certificate())
    original=ctx.db.add_fact; calls=[]
    def fail(fact):
        calls.append(fact)
        if len(calls)==2:
            raise RuntimeError('injected fact write failure')
        return original(fact)
    monkeypatch.setattr(ctx.db,'add_fact',fail)
    with pytest.raises(RuntimeError):
        nmpa_ingest.activate_source(ctx,sid)
    assert calls and facts(ctx)==[] and links(ctx)==[] and steps(ctx)==[]
    assert ctx.db.one('SELECT id FROM sources WHERE id=?',(sid,))
    monkeypatch.setattr(ctx.db,'add_fact',original)
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='adopted' and out['entity_id']==eid and out['facts_added']==3


def test_domestic_certificate_adopts_holder_and_approval_context(ctx):
    eid=drug(ctx,'司普奇拜单抗注射液')
    raw=domestic(); sid=registered(ctx,raw)
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='adopted' and out['entity_id']==eid
    by={f['field']:f for f in facts(ctx)}
    assert json.loads(by['status.china_mah']['value'])=='持有人甲法律实体'
    assert by['status.china_mah']['quote']=='上市许可持有人\t持有人甲法律实体'
    context=json.loads(by['status.china_mah']['context'])
    assert context['approval_date']=='2024-09-10' and context['issue_date'] is None
    assert context['valid_until'] is None and context['category']==DOMESTIC
    assert json.loads(by['identity.name_en']['value'])=='Stapokibart Injection'
