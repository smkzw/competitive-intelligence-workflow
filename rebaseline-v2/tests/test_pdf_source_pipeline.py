"""Native PDF source contracts, with process/network boundaries mocked, not clinical acceptance."""
import json
import sys
from types import SimpleNamespace

import httpx
import pytest
from test_source_representations import context

from ciw2.sources import http, websearch

RAW=b'%PDF-1.7 synthetic; no real clinical document'
TEXT='Synthetic threshold 10 units.\fSecond page.\f'


class ParseError(RuntimeError):
    reason='no_text'


def parser(monkeypatch):
    state={'id':'native-parser-1','calls':0,'error':None}
    def parse(raw,timeout_s=90):
        state['calls']+=1
        if state['error']:raise state['error']
        assert raw==RAW
        return SimpleNamespace(text=TEXT,parser_id=state['id'],parser_version='synthetic-version',pages=[
            {'page':1,'start':0,'end':28},{'page':2,'start':29,'end':41}])
    monkeypatch.setitem(sys.modules,'ciw2.sources.pdf_text',SimpleNamespace(
        parse_pdf=parse,parser_identity=lambda:state['id'],PDFTextError=ParseError))
    return state


def test_normal_fetch_url_reads_native_pdf_and_returns_exact_source_pages(settings,monkeypatch):
    ctx=context(settings);state=parser(monkeypatch)
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=RAW,
                 headers={'content-type':'application/pdf'}))) as client:
        monkeypatch.setattr(websearch,'fetch',lambda c,u,**kw:http.fetch(c,u,client=client,**kw))
        result=websearch._fetch_url(ctx,websearch.FetchUrlArgs(url='https://example.org/study.pdf',offset=8))
    assert result.get('status')!='unsupported' and result['source_id']
    assert result['text']==TEXT[8:] and result['total_chars']==len(TEXT)
    assert result['pages'][1]['page']==2 and result['text_parser_id']==state['id']
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(result['source_id'],))
    assert ctx.cas.get(source['digest'])==RAW and ctx.cas.get_text(source['text_digest'])==TEXT
    assert source['published_date'] is None


@pytest.mark.parametrize('ctype',('application/pdf','application/octet-stream','text/html'))
def test_pdf_magic_never_becomes_utf8_binary_text(settings,monkeypatch,ctype):
    ctx=context(settings);state=parser(monkeypatch)
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=RAW,
                 headers={'content-type':ctype}))) as client:
        result=http.fetch(ctx,'https://example.org/document',kind='web',client=client)
    assert state['calls']==1 and result.text==TEXT
    assert json.loads(ctx.db.one('SELECT meta FROM sources WHERE id=?',(result.source_id,))['meta'])['text_parser_id']==state['id']


def test_new_network_check_reuses_parsing_but_not_freshness_receipt(settings,monkeypatch):
    ctx=context(settings);state=parser(monkeypatch);calls=[];ctx.extra={'fetch_cache':{}}
    def respond(r):
        calls.append(str(r.url));return httpx.Response(200,content=RAW,headers={'content-type':'application/pdf'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        a=http.fetch(ctx,'https://example.org/a.pdf',kind='company',client=client)
        cached=http.fetch(ctx,a.url,kind='company',client=client)
        ctx.extra={'fetch_cache':{}}
        fresh=http.fetch(ctx,a.url,kind='company',client=client)
    assert len(calls)==2 and state['calls']==1 and a.source_id==cached.source_id==fresh.source_id
    modes=[json.loads(r['content'])['mode'] for r in ctx.db.query("SELECT content FROM agent_steps WHERE role='source_observation' ORDER BY id")]
    assert modes==['network_checked','cache_reused','network_checked']
    assert cached.network_checked_at is None and fresh.network_checked_at


def test_parser_change_invalidates_same_run_cache_without_rewriting_old_source(settings,monkeypatch):
    ctx=context(settings);state=parser(monkeypatch);ctx.extra={'fetch_cache':{}}
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=RAW,
                 headers={'content-type':'application/pdf'}))) as client:
        a=http.fetch(ctx,'https://example.org/a.pdf',kind='company',client=client)
        old=ctx.db.one('SELECT * FROM sources WHERE id=?',(a.source_id,))
        state['id']='native-parser-2'
        b=http.fetch(ctx,a.url,kind='company',client=client)
    assert a.source_id!=b.source_id and state['calls']==2
    assert ctx.db.one('SELECT * FROM sources WHERE id=?',(a.source_id,))==old
    assert a.text==b.text==TEXT


def test_failed_parse_retains_raw_evidence_but_is_not_text_or_cached_success(settings,monkeypatch):
    ctx=context(settings);state=parser(monkeypatch);state['error']=ParseError('private stderr should not leak')
    ctx.extra={'fetch_cache':{}}
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=RAW,
                 headers={'content-type':'application/pdf'}))) as client:
        with pytest.raises(http.FetchError) as exc:http.fetch(ctx,'https://example.org/a.pdf?token=secret',kind='web',client=client)
        assert 'secret' not in str(exc.value) and 'private stderr' not in str(exc.value)
        old=ctx.db.one('SELECT * FROM sources')
        assert old and old['text_digest'] is None and ctx.cas.get(old['digest'])==RAW
        assert not ctx.extra['fetch_cache'] and not ctx.extra.get('source_ids_read')
        state['error']=None
        result=http.fetch(ctx,'https://example.org/a.pdf?token=secret',kind='web',client=client)
    assert result.source_id!=old['id'] and result.text==TEXT
    assert ctx.db.one('SELECT * FROM sources WHERE id=?',(old['id'],))==old
    events=''.join(r['content'] for r in ctx.db.query('SELECT content FROM agent_steps'))
    assert 'private stderr' not in events and 'secret' not in events
