"""ClinicalTrials.gov study pages must resolve to the current authoritative JSON document.

The public study page is a client-rendered shell: fetching it as a webpage registers
navigation/glossary text as if it were study evidence. These offline cases bind the
production ``fetch_url`` tool to a mocked HTTP boundary, without real network access.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import httpx
import pytest
from test_source_representations import context

from ciw2.sources import http, websearch

NCT = "NCT03181633"
PAGE = f"https://clinicaltrials.gov/study/{NCT}"
API = f"https://clinicaltrials.gov/api/v2/studies/{NCT}"
SHELL = "<html><body><nav>ClinicalTrials.gov navigation</nav><p>Glossary</p></body></html>"
JSON_TYPE = {"content-type": "application/json"}


def study_document(nct: str = NCT) -> dict:
    return {"protocolSection": {
                "identificationModule": {"nctId": nct, "briefTitle": "Synthetic current registry document"},
                "statusModule": {"overallStatus": "COMPLETED"},
                "descriptionModule": {"detailedDescription": "Synthetic registry narrative. " * 500}},
            "hasResults": False}


def raw(document: dict) -> bytes:
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()


@contextmanager
def offline(monkeypatch: pytest.MonkeyPatch, respond: Callable[[httpx.Request], httpx.Response]
            ) -> Iterator[list[str]]:
    """Bind the production tool to a mocked transport and record every requested URL."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return respond(request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(websearch, "fetch", lambda c, u, **kw: http.fetch(c, u, client=client, **kw))
        yield calls


def test_official_study_page_registers_the_complete_current_json_document(settings, monkeypatch):
    ctx = context(settings)
    document = study_document()
    body = raw(document)
    text = body.decode()
    assert len(text) > 12000

    with offline(monkeypatch, lambda request: httpx.Response(200, content=body, headers=JSON_TYPE)) as calls:
        first = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=PAGE))
        assert calls == [API]  # The shell page is never requested as a webpage.
        assert first["source_url"] == API and first["requested_url"] == PAGE
        assert first["text"] == text[:12000] and first["next_offset"] == 12000
        rest = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=PAGE, offset=first["next_offset"]))

    assert calls == [API]  # One network check per run; the offset page reuses the same source.
    assert rest["offset"] == 12000 and rest["source_id"] == first["source_id"]
    assert rest["source_url"] == API and rest["requested_url"] == PAGE
    assert first["text"] + rest["text"] == text
    assert json.loads(first["text"] + rest["text"])["protocolSection"]["identificationModule"]["nctId"] == NCT
    source = ctx.db.one("SELECT * FROM sources WHERE id=?", (first["source_id"],))
    assert source["kind"] == "ctgov" and source["url"] == API
    assert ctx.cas.get(source["digest"]) == body and ctx.cas.get_text(source["text_digest"]) == text
    assert json.loads(source["meta"]) == {"content_type": "application/json"}
    assert http.source_by_url(ctx, API)["id"] == first["source_id"]
    assert http.source_by_url(ctx, PAGE) is None  # No source laundering under the requested page URL.
    assert first["source_id"] in ctx.extra["source_ids_read"]
    assert ctx.db.current_facts(ctx.project_id) == [] and ctx.db.entities(ctx.project_id, "trial") == []
    assert ctx.db.query("SELECT * FROM agent_steps WHERE role IN ('source_activation','source_rejection')") == []


@pytest.mark.parametrize("page", [
    f"http://clinicaltrials.gov/study/{NCT}",
    f"https://www.clinicaltrials.gov/study/{NCT}/",
    f"https://clinicaltrials.gov:443/study/{NCT}#results",
    f"https://CLINICALTRIALS.GOV/study/{NCT}",
    API,
    f"http://clinicaltrials.gov/api/v2/studies/{NCT}",
])
def test_equivalent_official_page_forms_resolve_to_the_same_document(settings, monkeypatch, page):
    ctx = context(settings)
    body = raw(study_document())
    text = body.decode()
    with offline(monkeypatch, lambda request: httpx.Response(200, content=body, headers=JSON_TYPE)) as calls:
        result = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=page))
    assert calls == [API]
    assert result["source_url"] == API and result["requested_url"] == http.public_url(page)
    assert result["total_chars"] == len(text) and text.startswith(result["text"])


@pytest.mark.parametrize("url", [
    f"https://clinicaltrials.gov/study/{NCT}?tab=history",
    f"https://clinicaltrials.gov/study/{NCT}/history",
    f"https://clinicaltrials.gov/ct2/show/{NCT}",
    f"https://clinicaltrials.gov/api/v2/studies/{NCT}?format=json",
    f"https://example.org/study/{NCT}",
    f"https://clinicaltrials.gov.evil.example/study/{NCT}",
    f"https://clinicaltrials.gov@evil.example/study/{NCT}",
    f"https://@clinicaltrials.gov/study/{NCT}",
    f"https://clinicaltrials.gov:8443/study/{NCT}",
    "https://clinicaltrials.gov/study/NCT0318163",
    "https://clinicaltrials.gov/study/nct03181633",
])
def test_non_current_or_unofficial_pages_keep_generic_web_behavior(settings, monkeypatch, url):
    ctx = context(settings)
    shell = SHELL.encode()
    with offline(monkeypatch, lambda request: httpx.Response(200, content=shell,
                 headers={"content-type": "text/html; charset=utf-8"})) as calls:
        result = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=url))
    assert calls == [str(httpx.Request("GET", url).url)]  # Never rewritten or query-stripped.
    assert "requested_url" not in result
    assert result["source_url"] == http.public_url(url)
    assert "Glossary" in result["text"] and "nctId" not in result["text"]
    assert ctx.db.one("SELECT kind FROM sources WHERE id=?", (result["source_id"],))["kind"] == "web"


@pytest.mark.parametrize(("body", "ctype", "match"), [
    (SHELL.encode(), "text/html; charset=utf-8", "JSON"),
    (raw(study_document("NCT00000001")), "application/json", "登记号"),
    (b'{"protocolSection":{}}', "application/json", "登记号"),
    (b"[]", "application/json", "登记号"),
], ids=["html_shell", "wrong_study", "empty_protocol", "not_an_object"])
def test_shell_or_mismatched_document_is_an_explicit_failure_and_still_audited(
        settings, monkeypatch, body, ctype, match):
    ctx = context(settings)
    with offline(monkeypatch, lambda request: httpx.Response(200, content=body,
                 headers={"content-type": ctype})) as calls, pytest.raises(ValueError, match=match):
        websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=PAGE))
    assert calls == [API]
    sources = ctx.db.query("SELECT * FROM sources")
    assert len(sources) == 1 and sources[0]["kind"] == "ctgov" and sources[0]["url"] == API
    assert ctx.cas.get(sources[0]["digest"]) == body and sources[0]["text_digest"]
    assert not (ctx.extra or {}).get("source_ids_read")  # Retained for audit, not readable evidence.
    assert ctx.db.current_facts(ctx.project_id) == []


def test_existing_shell_source_and_its_history_are_not_rewritten(settings, monkeypatch):
    ctx = context(settings)
    shell = SHELL.encode()
    with httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=shell, headers={"content-type": "text/html"}))) as client:
        legacy = http.fetch(ctx, PAGE, kind="web", client=client)
    before = ctx.db.one("SELECT * FROM sources WHERE id=?", (legacy.source_id,))
    assert "Glossary" in legacy.text

    body = raw(study_document())
    with offline(monkeypatch, lambda request: httpx.Response(200, content=body, headers=JSON_TYPE)) as calls:
        result = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=PAGE))

    assert calls == [API] and result["requested_url"] == PAGE
    assert ctx.db.one("SELECT * FROM sources WHERE id=?", (legacy.source_id,)) == before
    assert ctx.cas.get(before["digest"]) == shell
    assert http.source_by_url(ctx, PAGE)["id"] == legacy.source_id
    assert len(ctx.db.query("SELECT * FROM sources")) == 2


def test_repeated_read_reuses_the_registered_document_without_losing_identity(settings, monkeypatch):
    ctx = context(settings)
    ctx.extra = {"fetch_cache": {}}
    body = raw(study_document())
    with offline(monkeypatch, lambda request: httpx.Response(200, content=body, headers=JSON_TYPE)) as calls:
        first = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=PAGE))
        second = websearch._fetch_url(ctx, websearch.FetchUrlArgs(url=PAGE))
    assert calls == [API]
    assert first["source_id"] == second["source_id"]
    assert first["source_url"] == second["source_url"] == API and second["requested_url"] == PAGE
    assert first["text"] == second["text"] and first["total_chars"] == second["total_chars"]
    modes = [json.loads(row["content"])["mode"] for row in ctx.db.query(
        "SELECT content FROM agent_steps WHERE role='source_observation' ORDER BY id")]
    assert modes == ["network_checked", "cache_reused"]
