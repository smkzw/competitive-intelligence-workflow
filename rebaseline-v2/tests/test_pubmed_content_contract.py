"""Offline content-level contract for production `_pubmed_fetch`.

Synthetic records only. Payloads stay under 50KB and never touch the network.
"""
from __future__ import annotations

import pytest

from ciw2.harness.tools import ToolContext
from ciw2.sources import pubmed
from ciw2.sources.http import Fetched, FetchError

PMID_A = "35088348"
PMCID_A = "PMC8941010"
PMID_B = "41081535"
PMCID_B = "PMC13109752"
_LONG = "endpoint " * 1600


def _ids(value: str, *, id_type: str = "pmcid", pmid: str | None = PMID_A, extra: str = "") -> str:
    pmid_xml = "" if pmid is None else f'<article-id pub-id-type="pmid">{pmid}</article-id>'
    return f'<article-id pub-id-type="{id_type}">{value}</article-id>{extra}{pmid_xml}'


def _article(id_xml: str, body_inner: str | None) -> str:
    body = "" if body_inner is None else f"<body>{body_inner}</body>"
    return f"<article><front><article-meta>{id_xml}</article-meta></front>{body}</article>"


def _wrap(fragment: str, *, articleset: bool = False) -> bytes:
    if articleset:
        fragment = f"<pmc-articleset>{fragment}</pmc-articleset>"
    return fragment.encode()


def _citation(pmid: str, prefix: str = "Example citation.\n") -> str:
    return f"{prefix}PMID: {pmid} [Indexed for MEDLINE]\n"


_HELLO = "<p>Hello body</p>"
_BOTH = '<article-id pub-id-type="pmc">8941010</article-id>'
PMC = {
    "valid_a": _wrap(_article(_ids(PMCID_A, extra=_BOTH), _HELLO)),
    "valid_b": _wrap(_article(_ids("13109752", id_type="pmc", pmid=PMID_B), _HELLO), articleset=True),
    "no_pmid": _wrap(_article(_ids(PMCID_A, pmid=None), _HELLO)),
    "long": _wrap(_article(_ids(PMCID_A), f"<p>{_LONG}</p>")),
    "multi": _wrap(_article(_ids(PMCID_A), _HELLO) + _article(_ids(PMCID_A), _HELLO), articleset=True),
    "wrong_pmc": _wrap(_article(_ids("PMC0000001"), _HELLO)),
    "wrong_pmid": _wrap(_article(_ids(PMCID_A, pmid="11112222"), _HELLO)),
    "body_id": _wrap(_article("", f'<article-id pub-id-type="pmcid">{PMCID_A}</article-id>{_HELLO}')),
    "empty_body": _wrap(_article(_ids(PMCID_A), "<p> </p>")),
    "no_body": _wrap(_article(_ids(PMCID_A), None)),
    "malformed": b"<article><front><article-meta></article-meta></front><body><p>Hello</p></article>",
    "error": b"<ERROR>no article</ERROR>",
    "error_set": b"<pmc-articleset><error>no article</error></pmc-articleset>",
}
TEXTS = {
    "cite_a": _citation(PMID_A),
    "long_a": _citation(PMID_A, prefix=_LONG + "\n"),
    "bare_a": f"Example citation.\nPMID: {PMID_A}\n",
    "publisher_a": f"Example citation.\nPMID: {PMID_A} [PubMed - as supplied by publisher]\n",
    "crlf_a": f"Example citation.\r\nPMID: {PMID_A}\r\n",
    "blank": "",
    "space": " \n\t",
    "wrong_id": _citation("11112222"),
    "inline": f"See PMID: {PMID_A} [Indexed for MEDLINE] here\n",
    "dup": _citation(PMID_A) + f"PMID: {PMID_A} [Indexed for MEDLINE]\n",
}
assert sum(len(blob) for blob in PMC.values()) + sum(len(text.encode()) for text in TEXTS.values()) <= 50 * 1024


def _ok_pmc(case_id: str, *, pmid: str, pmcid: str, pmc: str, excerpt: str, offset: int = 0, window: bool = False) -> dict:
    return {
        "id": case_id, "pmid": pmid, "pmcid": pmcid, "full_text": True, "offset": offset, "window": window,
        "summary": [{"pmid": pmid, "pmcid": pmcid}], "fetch": "pmc", "pmc": pmc, "text": "cite_a",
        "content_level": "pmc_full_text", "full_text_status": "available", "excerpt": excerpt,
    }


def _ok_pub(case_id: str, *, full_text: bool, status: str, summary: list, text: str, offset: int = 0,
            window: bool = False, marker_outside_page: bool = False, excerpt: str = "Example citation.") -> dict:
    return {
        "id": case_id, "pmid": PMID_A, "full_text": full_text, "offset": offset, "window": window,
        "marker_outside_page": marker_outside_page, "summary": summary, "fetch": "pubmed", "text": text,
        "content_level": "pubmed_record", "full_text_status": status, "excerpt": excerpt,
    }


def _bad(case_id: str, *, full_text: bool, summary: object, fetch: str | None, text: str = "cite_a",
         pmcid: str | None = None, pmc: str | None = None, pmc_error: FetchError | None = None) -> dict:
    row: dict = {
        "id": case_id, "pmid": PMID_A, "full_text": full_text, "summary": summary, "fetch": fetch,
        "text": text, "error": True,
    }
    if pmcid is not None:
        row["pmcid"] = pmcid
    if pmc is not None:
        row["pmc"] = pmc
    if pmc_error is not None:
        row["pmc_error"] = pmc_error
    return row


_SUMMARY_A = [{"pmid": PMID_A, "pmcid": PMCID_A}]
CASES = [
    _ok_pmc("available_pmcid_and_numeric", pmid=PMID_A, pmcid=PMCID_A, pmc="valid_a", excerpt="Hello body"),
    _ok_pmc("available_articleset_numeric_pmc", pmid=PMID_B, pmcid=PMCID_B, pmc="valid_b", excerpt="Hello body"),
    _ok_pmc("available_without_pmid", pmid=PMID_A, pmcid=PMCID_A, pmc="no_pmid", excerpt="Hello body"),
    _ok_pmc("available_long_page", pmid=PMID_A, pmcid=PMCID_A, pmc="long", excerpt="endpoint", offset=100, window=True),
    _ok_pub("metadata_unresolved", full_text=True, status="metadata_unresolved", summary=[], text="long_a",
            window=True, marker_outside_page=True, excerpt="endpoint"),
    _ok_pub("not_in_pmc", full_text=True, status="not_in_pmc", summary=[{"pmid": PMID_A, "pmcid": None}], text="cite_a"),
    _ok_pub("not_requested", full_text=False, status="not_requested", summary=[], text="cite_a", offset=8),
    _ok_pub("bare_pmid_official_shape", full_text=False, status="not_requested", summary=[], text="bare_a"),
    _ok_pub("publisher_status_not_medline", full_text=False, status="not_requested", summary=[], text="publisher_a"),
    _ok_pub("crlf_without_index_status", full_text=False, status="not_requested", summary=[], text="crlf_a"),
    _bad("summary_pmid_mismatch", full_text=True, summary=[{"pmid": "11112222", "pmcid": PMCID_A}], fetch=None,
         pmcid=PMCID_A, pmc="valid_a"),
    _bad("summary_duplicate", full_text=True, summary=[_SUMMARY_A[0], dict(_SUMMARY_A[0])], fetch=None,
         pmcid=PMCID_A, pmc="valid_a"),
    _bad("summary_missing_pmid", full_text=True, summary=[{"pmcid": PMCID_A}], fetch=None, pmcid=PMCID_A, pmc="valid_a"),
    _bad("esummary_transport", full_text=True, summary=FetchError("HTTP 503"), fetch=None),
    _bad("pmc_transport", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A,
         pmc_error=FetchError("HTTP 503")),
    _bad("malformed_xml", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="malformed"),
    _bad("error_xml", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="error"),
    _bad("error_articleset", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="error_set"),
    _bad("multiple_articles", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="multi"),
    _bad("wrong_pmcid", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="wrong_pmc"),
    _bad("wrong_pmid", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="wrong_pmid"),
    _bad("pmcid_only_in_body", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="body_id"),
    _bad("empty_body", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="empty_body"),
    _bad("missing_body", full_text=True, summary=_SUMMARY_A, fetch="pmc", pmcid=PMCID_A, pmc="no_body"),
    _bad("blank_pubmed", full_text=False, summary=[], fetch="pubmed", text="blank"),
    _bad("whitespace_pubmed", full_text=False, summary=[], fetch="pubmed", text="space"),
    _bad("wrong_pubmed_pmid", full_text=False, summary=[], fetch="pubmed", text="wrong_id"),
    _bad("marker_not_anchored", full_text=False, summary=[], fetch="pubmed", text="inline"),
    _bad("duplicate_marker", full_text=False, summary=[], fetch="pubmed", text="dup"),
    _bad("blank_when_summary_empty", full_text=True, summary=[], fetch="pubmed", text="blank"),
    _bad("blank_when_no_pmcid", full_text=True, summary=[{"pmid": PMID_A, "pmcid": None}], fetch="pubmed", text="space"),
]


def _fetched(kind: str, content: bytes, text: str, case: dict) -> Fetched:
    if kind == "pmc":
        url = f"{pubmed.EUTILS}/efetch.fcgi?db=pmc&id={case['pmcid']}"
        ctype = "application/xml"
    else:
        url = f"{pubmed.EUTILS}/efetch.fcgi?db=pubmed&id={case['pmid']}"
        ctype = "text/plain"
    return Fetched(None, url, 200, content, text, ctype)


def _install(monkeypatch: pytest.MonkeyPatch, case: dict) -> dict:
    script: dict = {"calls": [], "summaries": [], "registered": [], "payload": {}}
    pubmed_text = TEXTS[case.get("text", "cite_a")]
    script["payload"]["pubmed"] = _fetched("pubmed", pubmed_text.encode(), pubmed_text, case)
    if "pmc" in case:
        raw = PMC[case["pmc"]]
        script["payload"]["pmc"] = _fetched("pmc", raw, raw.decode(), case)
    if "pmc_error" in case:
        script["payload"]["pmc"] = case["pmc_error"]

    def fake_fetch(ctx, url, **kwargs):
        script["calls"].append({"url": url, **kwargs})
        payload = script["payload"][kwargs["kind"]]
        if isinstance(payload, Exception):
            raise payload
        return payload

    def fake_esummary(ctx, pmids):
        script["summaries"].append(list(pmids))
        summary = case["summary"]
        if isinstance(summary, Exception):
            raise summary
        return summary

    def fake_register(ctx, **kwargs):
        script["registered"].append(kwargs)
        return "src-contract"

    monkeypatch.setattr(pubmed, "fetch", fake_fetch)
    monkeypatch.setattr(pubmed, "esummary", fake_esummary)
    monkeypatch.setattr(pubmed, "register_text", fake_register)
    return script


def _assert_route(script: dict, case: dict) -> None:
    if case["full_text"]:
        assert script["summaries"] == [[case["pmid"]]]
    else:
        assert script["summaries"] == []
    kind = case["fetch"]
    if kind is None:
        assert script["calls"] == []
        return
    assert len(script["calls"]) == 1
    call = script["calls"][0]
    assert call["url"] == f"{pubmed.EUTILS}/efetch.fcgi"
    assert call.get("register") is False
    assert call["kind"] == kind
    assert call["title"] == (case["pmcid"] if kind == "pmc" else case["pmid"])
    if kind == "pmc":
        assert call["params"] == {"db": "pmc", "id": case["pmcid"], "rettype": "xml"}
    else:
        assert call["params"] == {"db": "pubmed", "id": case["pmid"], "rettype": "abstract", "retmode": "text"}


def _assert_success(result: dict, script: dict, case: dict) -> None:
    _assert_route(script, case)
    assert len(script["registered"]) == 1
    reg = script["registered"][0]
    kind = case["fetch"]
    payload = script["payload"][kind]
    offset = case.get("offset", 0)
    assert reg["raw"] is payload.content
    assert reg["meta"] == {"fetched_url": payload.url}
    assert reg["kind"] == kind
    assert result.get("pmid") == case["pmid"]
    assert result.get("content_level") == case["content_level"]
    assert result.get("full_text_status") == case["full_text_status"]
    assert result.get("full_text_requested") is case["full_text"]
    assert set(result) == {
        "source_url", "source_id", "text", "total_chars", "pmid", "content_level",
        "full_text_requested", "full_text_status",
    }
    assert result["source_id"] == "src-contract"
    assert result["source_url"] == reg["url"]
    assert result["text"] == reg["text"][offset:offset + 12000]
    assert result["total_chars"] == len(reg["text"])
    if case.get("window"):
        assert result["total_chars"] > offset + 12000
        assert len(result["text"]) == 12000
    if kind == "pubmed":
        assert reg["url"] == f"https://pubmed.ncbi.nlm.nih.gov/{case['pmid']}/"
        assert reg["title"] == case["pmid"]
        assert reg["text"] is payload.text
    else:
        assert reg["url"] == f"https://pmc.ncbi.nlm.nih.gov/articles/{case['pmcid']}/"
        assert reg["title"] == case["pmcid"]
        assert reg["raw"].startswith(b"<")
        assert "<article" not in reg["text"]
    if "excerpt" in case:
        assert case["excerpt"] in reg["text"]
    if case.get("marker_outside_page"):
        marker = f"PMID: {case['pmid']} [Indexed for MEDLINE]"
        assert marker in reg["text"]
        assert marker not in result["text"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_pubmed_fetch_content_contract(monkeypatch: pytest.MonkeyPatch, case: dict) -> None:
    script = _install(monkeypatch, case)
    args = pubmed.PubFetchArgs(pmid=case["pmid"], full_text=case["full_text"], offset=case.get("offset", 0))
    try:
        result = pubmed._pubmed_fetch(ToolContext(), args)
    except FetchError:
        result = None
    if case.get("error"):
        assert script["registered"] == []
        assert result is None
        _assert_route(script, case)
        return
    assert result is not None
    _assert_success(result, script, case)
