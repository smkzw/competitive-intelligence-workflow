"""Owner challenges against the actual production adoption function."""
import pytest
from test_nmpa_ingest import certificate, drug, registered

from ciw2.service import Service
from ciw2.sources import nmpa_ingest


@pytest.fixture
def ctx(settings):
    svc=Service(settings)
    pid=svc.create_project('身份核查',['A','B','C'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


def test_english_name_alone_can_bind_bilingual_certificate(ctx):
    eid=drug(ctx,'Drug A Injection')
    sid=registered(ctx,certificate())
    assert nmpa_ingest.activate_source(ctx,sid)['entity_id']==eid
    assert len(ctx.db.current_facts(ctx.project_id))==3


def test_two_language_fields_cannot_select_different_entities_by_preference(ctx):
    cn=drug(ctx,'药物甲注射液')
    en=drug(ctx,'Drug A Injection')
    sid=registered(ctx,certificate())
    out=nmpa_ingest.activate_source(ctx,sid)
    assert out['status']=='unresolved' and set(out['candidate_ids'])=={cn,en}
    assert ctx.db.current_facts(ctx.project_id)==[]


def test_same_source_new_adoption_rule_reassesses_without_rewriting_old_facts(ctx,monkeypatch):
    drug(ctx,'药物甲注射液')
    sid=registered(ctx,certificate())
    first=nmpa_ingest.activate_source(ctx,sid)
    old=ctx.db.query('SELECT * FROM facts ORDER BY id')
    monkeypatch.setattr(nmpa_ingest,'EXTRACTOR_VERSION','new-rule-version',raising=False)
    second=nmpa_ingest.activate_source(ctx,sid)
    assert second['status']=='adopted' and second['facts_added']==3
    assert first['snapshot']!=second['snapshot']
    assert len(ctx.db.current_facts(ctx.project_id))==3
    assert all(row in ctx.db.query('SELECT * FROM facts ORDER BY id') for row in old)
    assert nmpa_ingest.activate_source(ctx,sid)['facts_added']==0


def test_another_tool_scope_does_not_certify_nmpa_identity(ctx):
    drug(ctx,'药物甲注射液')
    sid=registered(ctx,certificate())
    ctx.db.execute("UPDATE sources SET meta=json_set(meta,'$.request_context.tool','other') WHERE id=?",(sid,))
    with pytest.raises(ValueError):
        nmpa_ingest.activate_source(ctx,sid)
    assert ctx.db.current_facts(ctx.project_id)==[]


def test_ledger_failure_keeps_previous_current_and_every_old_row(ctx,monkeypatch):
    drug(ctx,'药物甲注射液')
    first=registered(ctx,certificate())
    nmpa_ingest.activate_source(ctx,first)
    sid=registered(ctx,certificate(observed='2026-10-25T00:00:00Z',holder_en='New Holder'))
    old={t:ctx.db.query(f'SELECT * FROM {t}') for t in ('facts','links','agent_steps')}
    def fail(*a,**k):
        raise RuntimeError('injected ledger failure')
    monkeypatch.setattr(ctx.db,'log_step',fail)
    with pytest.raises(RuntimeError):
        nmpa_ingest.activate_source(ctx,sid)
    assert {t:ctx.db.query(f'SELECT * FROM {t}') for t in old}==old
