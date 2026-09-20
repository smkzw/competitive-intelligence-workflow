"""PubMed acquisition evidence: pagination, failure kinds and raw-byte custody.

Every transport here is synthetic; no test reaches the network.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from ci_workflow.cli import main
from ci_workflow.sources.connectors import pubmed_fetch
from ci_workflow.sources.connectors.pubmed_fetch import (
    HttpPage,
    PubMedAccessDeniedError,
    PubMedHttpError,
    PubMedNetworkError,
    PubMedRateLimitedError,
    PubMedServerError,
    PubMedTimeoutError,
    fetch_pubmed_results,
)
from ci_workflow.storage.content_store import ContentAddressedStore
from tests.integration.test_research_package_submission import _project

NOW = datetime(2026, 9, 11, 3, 0, tzinfo=UTC)
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def _clock() -> datetime:
    return NOW


class Pages:
    """Synthetic E-utilities transport: queued bytes, HttpPage, or raised exception."""

    def __init__(self, items: list[bytes | HttpPage | Exception]) -> None:
        self.items = iter(items)
        self.urls: list[str] = []

    def __call__(self, url: str, timeout: float, max_bytes: int) -> HttpPage:
        self.urls.append(url)
        value = next(self.items)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, HttpPage):
            return value
        media_type = (
            "application/json"
            if "esearch.fcgi" in url or "esummary.fcgi" in url
            else "text/xml"
        )
        return HttpPage(200, media_type, value, url)


class _Opener:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def open(self, request: object, timeout: float) -> object:
        raise self.error


def _search_page(count: int, retstart: int, retmax: int, ids: list[str]) -> bytes:
    return json.dumps({
        "header": {"type": "esearch"},
        "esearchresult": {
            "count": str(count), "retstart": str(retstart), "retmax": str(retmax), "idlist": ids,
        },
    }).encode("utf-8")


def _article(pmid: str) -> str:
    return (
        "<PubmedArticle><MedlineCitation>"
        f"<PMID>{pmid}</PMID><Article><ArticleTitle>合成题名{pmid}</ArticleTitle>"
        "<Abstract><AbstractText>合成摘要内容</AbstractText></Abstract>"
        "<PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType>"
        "</PublicationTypeList></Article></MedlineCitation></PubmedArticle>"
    )


def _records_xml(*pmids: str) -> bytes:
    body = "".join(_article(pmid) for pmid in pmids)
    return f'<?xml version="1.0"?><PubmedArticleSet>{body}</PubmedArticleSet>'.encode()


def _assert_cas_bytes(
    root: Path, page: pubmed_fetch.CapturedPage, expected: bytes,
) -> None:
    raw = ContentAddressedStore(root).read_bytes(page.raw_asset)
    assert raw == expected
    assert hashlib.sha256(raw).hexdigest() == page.raw_asset.sha256
    assert page.raw_asset.relative_path == (
        f"evidence/raw/sha256/{page.raw_asset.sha256[:2]}/{page.raw_asset.sha256}.bin"
    )
    assert page.acquired_at == NOW and page.acquired_at.utcoffset() == timedelta(0)


def test_two_page_search_keeps_cursor_and_exact_raw_bytes(tmp_path: Path) -> None:
    pages = Pages([
        _search_page(2, 0, 1, ["111"]),
        _search_page(2, 1, 1, ["222"]),
        _records_xml("111", "222"),
    ])
    result = fetch_pubmed_results(
        tmp_path, "pembrolizumab AND NSCLC", page_size=1, transport=pages, clock=_clock,
    )
    assert result.status == "complete" and result.pagination_complete
    assert result.total_count == 2
    assert [record.pmid for record in result.records] == ["111", "222"]
    assert result.acquired_at == NOW and result.acquired_at.utcoffset() == timedelta(0)
    assert result.universe_closed is False and result.temporal_scope == "current_records"
    assert len(result.search_pages) == 2 and len(result.record_pages) == 1

    first = parse_qs(urlsplit(pages.urls[0]).query)
    second = parse_qs(urlsplit(pages.urls[1]).query)
    assert first["term"] == ["pembrolizumab AND NSCLC"]
    assert first["db"] == ["pubmed"] and first["retmode"] == ["json"]
    assert (first["retstart"], first["retmax"]) == (["0"], ["1"])
    assert (second["retstart"], second["retmax"]) == (["1"], ["1"])
    assert parse_qs(urlsplit(pages.urls[2]).query)["id"] == ["111,222"]

    _assert_cas_bytes(tmp_path, result.search_pages[0], _search_page(2, 0, 1, ["111"]))
    _assert_cas_bytes(tmp_path, result.search_pages[1], _search_page(2, 1, 1, ["222"]))
    _assert_cas_bytes(tmp_path, result.record_pages[0], _records_xml("111", "222"))


def test_records_are_fetched_in_bounded_chunks(tmp_path: Path) -> None:
    pages = Pages([
        _search_page(2, 0, 2, ["111", "222"]),
        _records_xml("111"),
        _records_xml("222"),
    ])
    result = fetch_pubmed_results(
        tmp_path, "term", efetch_batch_size=1, transport=pages, clock=_clock,
    )
    assert result.status == "complete"
    assert [record.pmid for record in result.records] == ["111", "222"]
    assert len(result.record_pages) == 2
    assert parse_qs(urlsplit(pages.urls[1]).query)["id"] == ["111"]
    assert parse_qs(urlsplit(pages.urls[2]).query)["id"] == ["222"]


@pytest.mark.parametrize(("failure", "expected"), [
    (TimeoutError("timed out"), "network_error"),
    (URLError("connection refused"), "network_error"),
    (HttpPage(429, "", b"", ""), "rate_limited"),
    (HttpPage(403, "", b"", ""), "access_denied"),
    (HttpPage(503, "", b"", ""), "network_error"),
    (HttpPage(302, "", b"", ""), "invalid_response"),
    (b"<html>not json</html>", "invalid_response"),
    (
        b'{"esearchresult":{"count":"3","retstart":"0","retmax":"3","idlist":[],'
        b'"ERROR":"Invalid term"}}',
        "invalid_response",
    ),
])
def test_every_failure_kind_stays_distinct_from_no_records(
    tmp_path: Path, failure: bytes | HttpPage | Exception, expected: str,
) -> None:
    result = fetch_pubmed_results(tmp_path, "term", transport=Pages([failure]), clock=_clock)
    assert result.status == expected
    assert not result.pagination_complete
    assert result.records == () and result.total_count is None
    assert result.universe_closed is False
    assert not (tmp_path / "evidence").exists()


def test_redirected_response_is_not_accepted(tmp_path: Path) -> None:
    page = HttpPage(200, "application/json", _search_page(1, 0, 1, ["111"]), "https://elsewhere")
    result = fetch_pubmed_results(tmp_path, "term", transport=Pages([page]), clock=_clock)
    assert result.status == "invalid_response" and not result.pagination_complete


def test_repeated_search_page_never_ends_as_completion(tmp_path: Path) -> None:
    pages = Pages([_search_page(4, 0, 1, ["111"]), _search_page(4, 1, 1, ["111"])])
    result = fetch_pubmed_results(
        tmp_path, "term", page_size=1, transport=pages, clock=_clock,
    )
    assert result.status == "incomplete" and not result.pagination_complete
    assert result.records == ()
    assert len(result.search_pages) == 2
    assert len(pages.urls) == 2


def test_search_cursor_must_echo_the_request(tmp_path: Path) -> None:
    pages = Pages([_search_page(2, 0, 1, ["111"]), _search_page(2, 0, 1, ["222"])])
    result = fetch_pubmed_results(
        tmp_path, "term", page_size=1, transport=pages, clock=_clock,
    )
    assert result.status == "invalid_response" and not result.pagination_complete


def test_authoritative_empty_search_is_not_a_failure(tmp_path: Path) -> None:
    pages = Pages([_search_page(0, 0, 200, [])])
    result = fetch_pubmed_results(tmp_path, "term", transport=pages, clock=_clock)
    assert result.status == "no_records" and result.pagination_complete
    assert result.total_count == 0 and result.records == ()
    assert result.universe_closed is False
    assert len(result.search_pages) == 1 and result.record_pages == ()
    assert len(pages.urls) == 1
    _assert_cas_bytes(tmp_path, result.search_pages[0], _search_page(0, 0, 200, []))


@pytest.mark.parametrize(("body", "expected"), [
    (b"<PubmedArticleSet><broken", "invalid_response"),
    (b"<eFetchResult><ERROR>Invalid uid</ERROR></eFetchResult>", "invalid_response"),
    (b'<?xml version="1.0"?><PubmedArticleSet></PubmedArticleSet>', "incomplete"),
])
def test_record_document_faults_are_never_no_records(
    tmp_path: Path, body: bytes, expected: str,
) -> None:
    # 缺失标识经 esummary 显示仍可获取 → 真截断，不是无记录。
    summary = json.dumps({"result": {"111": {"uid": "111", "pubstatus": "pubmed"}}}).encode()
    pages = Pages([_search_page(1, 0, 1, ["111"]), body, summary])
    result = fetch_pubmed_results(
        tmp_path, "term", page_size=1, transport=pages, clock=_clock,
    )
    assert result.status == expected
    assert not result.pagination_complete
    assert result.records == ()


def test_partial_record_page_is_incomplete_not_complete(tmp_path: Path) -> None:
    summary = json.dumps({"result": {"222": {"uid": "222", "pubstatus": "pubmed"}}}).encode()
    pages = Pages([_search_page(2, 0, 2, ["111", "222"]), _records_xml("111"), summary])
    result = fetch_pubmed_results(tmp_path, "term", transport=pages, clock=_clock)
    assert result.status == "incomplete" and not result.pagination_complete
    assert [record.pmid for record in result.records] == ["111"]
    assert len(result.record_pages) == 1


def test_page_and_byte_budgets_never_report_completion(tmp_path: Path) -> None:
    pages = Pages([_search_page(4, 0, 1, ["111"]), _search_page(4, 1, 1, ["222"])])
    limited = fetch_pubmed_results(
        tmp_path, "term", page_size=1, max_pages=2, transport=pages, clock=_clock,
    )
    assert limited.status == "incomplete" and len(limited.search_pages) == 2

    single = _search_page(4, 0, 1, ["111"])
    budget = Pages([single, _search_page(4, 1, 1, ["222"])])
    exhausted = fetch_pubmed_results(
        tmp_path / "budget", "term", page_size=1, max_total_bytes=len(single),
        transport=budget, clock=_clock,
    )
    assert exhausted.status == "incomplete" and len(exhausted.search_pages) == 1
    assert len(budget.urls) == 1


@pytest.mark.parametrize(("error", "expected"), [
    (URLError(TimeoutError("timed out")), PubMedTimeoutError),
    (TimeoutError("timed out"), PubMedTimeoutError),
    (URLError("connection refused"), PubMedNetworkError),
    (OSError("broken pipe"), PubMedNetworkError),
])
def test_download_converts_transport_faults_to_distinct_typed_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception, expected: type[Exception],
) -> None:
    monkeypatch.setattr(pubmed_fetch, "build_opener", lambda handler: _Opener(error))
    with pytest.raises(expected):
        pubmed_fetch._download(ESEARCH, 5.0, 1024)


def test_download_never_returns_a_server_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    error = HTTPError(ESEARCH, 429, "Too Many Requests", {}, None)
    monkeypatch.setattr(pubmed_fetch, "build_opener", lambda handler: _Opener(error))
    page = pubmed_fetch._download(ESEARCH, 5.0, 1024)
    assert page.status == 429 and page.body == b"" and page.final_url == ESEARCH


@pytest.mark.parametrize(("status", "expected"), [
    (429, PubMedRateLimitedError),
    (401, PubMedAccessDeniedError),
    (403, PubMedAccessDeniedError),
    (503, PubMedServerError),
    (302, PubMedHttpError),
])
def test_http_statuses_map_to_distinct_exception_types(
    status: int, expected: type[Exception],
) -> None:
    with pytest.raises(expected):
        pubmed_fetch._classify_status(status, context="PubMed 检索")


@pytest.mark.parametrize("query", ["", "   ", "x" * 4001, "bad\x00term"])
def test_invalid_query_is_rejected_before_any_request(tmp_path: Path, query: str) -> None:
    pages = Pages([_search_page(1, 0, 1, ["111"])])
    with pytest.raises(ValueError):
        fetch_pubmed_results(tmp_path, query, transport=pages, clock=_clock)
    assert pages.urls == []


@pytest.mark.parametrize("overrides", [
    {"page_size": 0}, {"page_size": 10001}, {"max_pages": 0}, {"timeout": 0},
    {"efetch_batch_size": 0}, {"max_page_bytes": 0}, {"max_total_bytes": 0},
])
def test_invalid_limits_are_rejected(tmp_path: Path, overrides: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        fetch_pubmed_results(
            tmp_path, "term", transport=Pages([]), clock=_clock, **overrides,
        )


def test_search_url_is_derived_from_the_canonical_pubmed_route() -> None:
    from ci_workflow.sources.connectors.pubmed import build_pubmed_nct_search_url

    canonical = urlsplit(build_pubmed_nct_search_url("NCT00000001"))
    derived = urlsplit(pubmed_fetch.build_pubmed_term_search_url("term", retstart=0, retmax=1))
    assert (derived.scheme, derived.netloc) == (canonical.scheme, canonical.netloc)
    assert derived.path == canonical.path
    assert parse_qs(derived.query)["db"] == ["pubmed"]


def test_fetch_cli_prints_only_a_pointer_and_binds_the_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    monkeypatch.setattr(
        pubmed_fetch, "_download",
        Pages([_search_page(1, 0, 1, ["111"]), _records_xml("111")]),
    )
    code = main([
        "research", "fetch-pubmed", "--project", str(project), "--term", "合成检索式",
    ])
    assert code == 0
    output = capsys.readouterr().out
    assert "合成摘要内容" not in output
    pointer = json.loads(output)
    assert pointer["status"] == "complete" and pointer["records"] == 1
    assert pointer["total_count"] == 1 and pointer["universe_closed"] is False
    receipt = json.loads((project / pointer["capture_path"]).read_bytes())
    assert receipt["acquisition"]["temporal_scope"] == "current_records"
    assert receipt["acquisition"]["universe_closed"] is False
    assert receipt["record_count"] == 1
    assert receipt["records"] == [{
        "pmid": "111", "title": "合成题名111",
        "publication_types": ["Randomized Controlled Trial"],
    }]


def test_fetch_cli_fails_closed_on_network_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    monkeypatch.setattr(pubmed_fetch, "_download", Pages([TimeoutError("timed out")]))
    code = main([
        "research", "fetch-pubmed", "--root", str(project), "--term", "合成检索式",
    ])
    assert code == 7
    pointer = json.loads(capsys.readouterr().out)
    assert pointer["status"] == "network_error" and pointer["records"] == 0
    receipt = json.loads((project / pointer["capture_path"]).read_bytes())
    assert receipt["acquisition"]["status"] == "network_error"
    assert receipt["acquisition"]["universe_closed"] is False
    assert receipt["records"] == []


def test_fetch_cli_rejects_missing_or_invalid_arguments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    with pytest.raises(SystemExit) as missing:
        main(["research", "fetch-pubmed", "--root", str(project)])
    assert missing.value.code == 2
    assert "缺少必填参数" in capsys.readouterr().err

    assert main(["research", "fetch-pubmed", "--root", str(project), "--term", "   "]) == 2
    assert "CONTRACT_ERROR" in capsys.readouterr().err

    assert main([
        "research", "fetch-pubmed", "--root", str(project), "--term", "term",
        "--page-size", "0",
    ]) == 2
    assert "CONTRACT_ERROR" in capsys.readouterr().err


def test_fetch_cli_requires_a_verified_project_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([
        "research", "fetch-pubmed", "--root", str(tmp_path / "not-a-project"),
        "--term", "term",
    ]) == 2
    assert "CONTRACT_ERROR" in capsys.readouterr().err


def test_efetch_attrition_classified_via_esummary(tmp_path: Path) -> None:
    """G8-1：efatch 缺失经 esummary 分类后按属性完成，不冒充完整记录集。"""
    root = tmp_path / "proj"
    (root / "state").mkdir(parents=True)
    search = _search_page(3, 0, 10, ["1", "2", "3"])
    records = _records_xml("1")
    summary = json.dumps({
        "result": {
            "1": {"uid": "1"},
            "2": {"uid": "2", "pubstatus": "in process"},
            "3": {"uid": "3", "pubstatus": "not_in_pubmed"},
        },
    }).encode()
    transport = Pages([search, records, summary])
    result = fetch_pubmed_results(
        root, "q", page_size=10, max_pages=1, transport=transport,
    )
    assert result.status == "complete_with_attrition"
    assert result.pagination_complete is True
    assert [record.pmid for record in result.records] == ["1"]
    assert {item.pmid: item.state for item in result.attrition} == {
        "2": "in process", "3": "not_in_pubmed",
    }
    assert result.summary_pages, "esummary 回落页必须进 CAS"


def test_unclassified_attrition_stays_incomplete(tmp_path: Path) -> None:
    """esummary 显示可获取却未被 efetch 返回：真截断，不得认定完成。"""
    root = tmp_path / "proj"
    (root / "state").mkdir(parents=True)
    search = _search_page(2, 0, 10, ["1", "2"])
    records = _records_xml("1")
    summary = json.dumps({"result": {"2": {"uid": "2", "pubstatus": "pubmed"}}}).encode()
    transport = Pages([search, records, summary])
    result = fetch_pubmed_results(
        root, "q", page_size=10, max_pages=1, transport=transport, clock=_clock,
    )
    assert result.status == "incomplete"
    assert result.pagination_complete is False
