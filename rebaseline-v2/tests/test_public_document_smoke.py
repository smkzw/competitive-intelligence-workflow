"""The opt-in source probe uses normal ingestion; all test HTTP is synthetic."""
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import httpx

from ciw2.sources import http


def test_regulatory_html_probe_preserves_source_not_approval_date(tmp_path,monkeypatch):
    path=Path(__file__).resolve().parents[1]/'scripts/smoke_company_documents.py'
    spec=importlib.util.spec_from_file_location('_public_documents_probe',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    out=tmp_path/'probe'
    monkeypatch.setattr(sys,'argv',[str(path),'--url','https://example.org/regulatory',
        '--term','IL-X','--kind','regulator','--allow-html','--output',str(out)])
    body=b'<html><h1>Updated: 2025-02-19</h1><p>Drug A targets IL-X.</p></html>'
    fetch=http.fetch
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=body,
                     headers={'content-type':'text/html'}))) as client:
        monkeypatch.setattr('ciw2.sources.websearch.fetch',lambda c,u,**kw:fetch(c,u,client=client,**kw))
        assert module.main()==0
    receipt=json.loads((out/'receipt.json').read_text())
    assert receipt['state']=='RETURNED' and receipt['adopted_facts']==receipt['model_calls']==0
    record=receipt['records'][0]
    assert record['format']=='html_or_text' and record['pages']==0
    assert record['first_tail_text_read'] and not record['first_last_pages_read']
    assert record['matches'][0]['page'] is None and 'IL-X' in record['matches'][0]['text']
    with sqlite3.connect(out/'data/ciw2.sqlite3') as db:
        assert db.execute('SELECT kind,published_date FROM sources').fetchall()==[('regulator',None)]
    assert [event['mode'] for event in receipt['source_events']]==['network_checked','cache_reused']
