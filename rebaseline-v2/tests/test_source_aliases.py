import json

from ciw2.harness.tools import ToolContext
from ciw2.sources import pubmed
from ciw2.sources.http import Fetched, source_by_url, source_text
from ciw2.store.cas import CAS
from ciw2.store.db import DB


def test_fetched_publication_url_resolves_to_exact_cas_text(settings, monkeypatch):
    settings.ensure_dirs()
    db, cas = DB(settings.db_path), CAS(settings.cas_dir)
    pid = db.create_project('研究', ['C'])
    ctx = ToolContext(db=db, cas=cas, settings=settings, project_id=pid)
    text = 'The primary endpoint was EASI-75 at week 16.'

    def fake_fetch(ctx, url, **kwargs):
        digest = cas.put(text.encode())
        sid = db.add_source(pid, 'pubmed', url + '?db=pubmed&id=12345678', digest, text_digest=digest)
        return Fetched(sid, url + '?db=pubmed&id=12345678', 200, text.encode(), text, 'text/plain')

    monkeypatch.setattr(pubmed, 'fetch', fake_fetch)
    result = pubmed._pubmed_fetch(ctx, pubmed.PubFetchArgs(pmid='12345678'))
    source = source_by_url(ctx, result['source_url'])
    assert source is not None
    assert source_text(ctx, source['id']) == text
    assert source['id'] == result['source_id']
    assert json.loads(source['meta'])['fetched_url'].endswith('?db=pubmed&id=12345678')
