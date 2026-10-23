"""Real parser module through normal HTTP/tool boundaries, with only native/HTTP I/O faked."""
import json
import subprocess

import httpx
import pytest
from test_source_representations import context

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.recovery import get_unit, put_unit
from ciw2.service import Service
from ciw2.sources import http, pdf_text

RAW=b'%PDF-1.7 synthetic source'


def native(monkeypatch):
    calls=[]
    monkeypatch.setattr(pdf_text,'_binary',lambda:'synthetic-pdftotext')
    def invoke(argv,body,timeout):
        if argv[1:]==['-v']:return subprocess.CompletedProcess(argv,0,b'',b'pdftotext version 26.08.0\n')
        calls.append(body)
        return subprocess.CompletedProcess(argv,0,b'Actual module source text\f',b'')
    monkeypatch.setattr(pdf_text,'_invoke',invoke)
    return calls


def test_actual_parser_identity_matches_the_returned_representation(monkeypatch):
    native(monkeypatch)
    assert pdf_text.parse_pdf(RAW).parser_id==pdf_text.parser_identity()


def test_actual_module_reuses_same_pdf_parse_across_cache_and_fresh_check(settings,monkeypatch):
    calls=native(monkeypatch);ctx=context(settings);ctx.extra={'fetch_cache':{}};http_calls=[]
    def respond(req):
        http_calls.append(req.url);return httpx.Response(200,content=RAW,headers={'content-type':'application/pdf'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        a=http.fetch(ctx,'https://example.org/a.pdf',kind='company',client=client)
        b=http.fetch(ctx,a.url,kind='company',client=client)
        ctx.extra={'fetch_cache':{}}
        c=http.fetch(ctx,a.url,kind='company',client=client)
    assert len(http_calls)==2 and calls==[RAW]
    assert a.source_id==b.source_id==c.source_id
    assert [a.mode,b.mode,c.mode]==['network_checked','cache_reused','network_checked']


def test_actual_native_failure_code_is_not_flattened_to_generic_source_failure(settings,monkeypatch):
    native(monkeypatch);ctx=context(settings)
    def no_text(*args,**kwargs):raise pdf_text.PDFTextError('empty_text','OCR not attempted')
    monkeypatch.setattr(pdf_text,'parse_pdf',no_text)
    with (httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=RAW,
                 headers={'content-type':'application/pdf'}))) as client,
          pytest.raises(http.FetchError,match='empty_text')):
        http.fetch(ctx,'https://example.org/a.pdf',kind='web',client=client)
    source=ctx.db.one('SELECT * FROM sources')
    assert source['text_digest'] is None and json.loads(source['meta'])['text_error']=='empty_text'


def test_missing_module_bytes_is_a_safe_structured_failure(monkeypatch):
    native(monkeypatch)
    def gone():raise OSError('secret local path')
    monkeypatch.setattr(pdf_text,'_module_bytes',gone)
    with pytest.raises(pdf_text.PDFTextError) as caught:pdf_text.parser_identity()
    assert 'secret local path' not in str(caught.value)


@pytest.mark.parametrize('change',('module','missing'))
def test_cached_model_unit_requires_current_pdf_parser_before_reuse(settings,monkeypatch,change):
    native(monkeypatch)
    svc=Service(settings,llm_factory=lambda _:(ScriptedLLM([]),None))
    pid=svc.create_project('PDF恢复',['A']);rc=svc.context(pid,svc.db.create_run(pid))
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=RAW,
                 headers={'content-type':'application/pdf'}))) as client:
        source=http.fetch(rc.tool_ctx(),'https://example.org/a.pdf',kind='company',client=client)
    put_unit(rc,'synthetic-pdf-unit',{'facts':[]},source_ids=[source.source_id])
    assert get_unit(rc,'synthetic-pdf-unit')=={'facts':[]}
    if change=='module':monkeypatch.setattr(pdf_text,'_module_bytes',lambda:b'changed module rule')
    else:
        def unavailable():raise pdf_text.PDFTextError('parser_missing')
        monkeypatch.setattr(pdf_text,'_binary',unavailable)
    assert get_unit(rc,'synthetic-pdf-unit') is None
