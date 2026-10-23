"""Source bytes and extracted text have distinct immutable identities (offline)."""
import json

import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources.http import register_text, source_by_url


def context(settings):
    svc=Service(settings,llm_factory=lambda _:(ScriptedLLM([]),None))
    pid=svc.create_project('来源表示版本',['A'])
    return svc.context(pid,svc.db.create_run(pid)).tool_ctx()


@pytest.mark.parametrize('changed',('text','parser','kind','from_unreadable'))
def test_representation_change_is_new_source_without_history_rewrite(settings,changed):
    ctx=context(settings)
    raw=b'%PDF-1.7 synthetic source; not an actual clinical document'
    digest=ctx.cas.put(raw)
    text=ctx.cas.put(b'first layout\f')
    first=ctx.db.add_source(ctx.project_id,'company','https://example.org/annual.pdf',digest,
        text_digest=None if changed=='from_unreadable' else text,
        meta={'text_parser_id':'parser-1','text_state':'failed' if changed=='from_unreadable' else 'parsed'})
    row=ctx.db.one('SELECT * FROM sources WHERE id=?',(first,))
    second=ctx.db.add_source(ctx.project_id,'regulator' if changed=='kind' else 'company',row['url'],digest,
        text_digest=ctx.cas.put(b'second layout\f') if changed=='text' else text,
        meta={'text_parser_id':'parser-2' if changed=='parser' else 'parser-1','text_state':'parsed'})
    assert second!=first
    assert ctx.db.one('SELECT * FROM sources WHERE id=?',(first,))==row
    assert ctx.cas.get(digest)==raw


def test_same_parsed_content_is_reused_without_rewriting_first_seen(settings):
    ctx=context(settings)
    first=register_text(ctx,kind='company',url='https://example.org/source',raw=b'raw',text='original',
                        meta={'text_parser_id':'p1','pages':[{'page':1,'start':0,'end':8}]})
    original=ctx.db.one('SELECT * FROM sources WHERE id=?',(first,))
    again=register_text(ctx,kind='company',url=original['url'],raw=b'raw',text='original',
                        meta={'text_parser_id':'p1','retrieved_note':'not source identity'})
    assert again==first and ctx.db.one('SELECT * FROM sources WHERE id=?',(first,))==original


def test_source_current_reads_latest_observed_representation_not_old_raw_match(settings):
    ctx=context(settings)
    first=register_text(ctx,kind='company',url='https://example.org/source',raw=b'raw',text='old text')
    original=ctx.db.one('SELECT * FROM sources WHERE id=?',(first,))
    second=register_text(ctx,kind='company',url=original['url'],raw=b'raw',text='new text',
                         meta={'text_parser_id':'p2'})
    assert source_by_url(ctx,original['url'])['id']==second
    assert ctx.db.one('SELECT * FROM sources WHERE id=?',(first,))==original
    rows=ctx.db.query("SELECT content FROM agent_steps WHERE role='source_observation' ORDER BY id")
    assert [json.loads(r['content'])['source_id'] for r in rows]==[first,second]


def test_source_representation_still_scoped_to_project(settings):
    ctx=context(settings)
    first=register_text(ctx,kind='web',url='https://example.org',text='same')
    other=ctx.db.create_project('其他项目',['C'])
    second=ctx.db.add_source(other,'web','https://example.org',ctx.cas.put(b'same'),text_digest=ctx.cas.put(b'same'))
    assert first!=second
