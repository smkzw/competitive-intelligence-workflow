"""Acquisition completeness is not competitor-universe completeness."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from ci_workflow.sources.connectors.ctgov_fetch import HttpPage, fetch_ctgov_condition
from ci_workflow.storage.content_store import ContentAddressedStore


def _study(number: int) -> dict[str, object]:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": f"NCT{number:08d}", "briefTitle": "Synthetic"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-01-01"}},
        },
        "derivedSection": {"miscInfoModule": {"versionHolder": "2026-09-06"}},
    }


class Pages:
    def __init__(self, payloads: list[dict[str, object] | Exception]) -> None:
        self.payloads = iter(payloads)
        self.urls: list[str] = []

    def __call__(self, url: str, timeout: float, max_bytes: int) -> HttpPage:
        self.urls.append(url)
        value = next(self.payloads)
        if isinstance(value, Exception):
            raise value
        return HttpPage(200, "application/json", json.dumps(value).encode(), url)


@pytest.mark.parametrize("body", [
    b'{"studies":[],"totalCount":9,"totalCount":0}',
    b'{"studies":[],"totalCount":0,"extra":NaN}',
    b'{"studies":[],"totalCount":0,"extra":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}',
], ids=["duplicate-key", "nonfinite", "excessive-nesting"])
def test_ambiguous_or_excessively_nested_json_is_not_zero_results(
    tmp_path: Path, body: bytes,
) -> None:
    def transport(url: str, timeout: float, max_bytes: int) -> HttpPage:
        return HttpPage(200, "application/json", body, url)

    result = fetch_ctgov_condition(tmp_path, "synthetic", transport=transport)
    assert result.status == "invalid_response"
    assert not result.pagination_complete


def test_all_pages_preserve_exact_raw_bytes_and_query(tmp_path: Path) -> None:
    pages = Pages([
        {"studies": [_study(1)], "totalCount": 2, "nextPageToken": "a/b=第二页"},
        {"studies": [_study(2)]},  # Actual API omits totalCount on cursor pages.
    ])
    result = fetch_ctgov_condition(tmp_path, "PNH OR 合成查询", page_size=1, transport=pages)
    assert result.status == "complete"
    assert result.pagination_complete and not result.universe_closed
    assert len(result.studies) == 2
    assert len(result.pages) == 2
    assert parse_qs(urlsplit(pages.urls[1]).query)["pageToken"] == ["a/b=第二页"]
    assert parse_qs(urlsplit(pages.urls[1]).query)["query.cond"] == ["PNH OR 合成查询"]
    raw = ContentAddressedStore(tmp_path).read_bytes(result.pages[0].raw_asset)
    assert json.loads(raw)["studies"][0] == _study(1)


def test_empty_intermediate_page_does_not_end_pagination(tmp_path: Path) -> None:
    pages = Pages([
        {"studies": [], "totalCount": 1, "nextPageToken": "continue"},
        {"studies": [_study(1)], "totalCount": 1},
    ])
    assert fetch_ctgov_condition(tmp_path, "synthetic", transport=pages).status == "complete"


@pytest.mark.parametrize("failure,expected", [
    (TimeoutError(), "network_error"),
    ({"studies": [], "totalCount": 5}, "incomplete"),
    ({"message": "bad response"}, "invalid_response"),
])
def test_failure_is_never_reported_as_no_records(
    tmp_path: Path, failure: dict[str, object] | Exception, expected: str,
) -> None:
    result = fetch_ctgov_condition(tmp_path, "synthetic", transport=Pages([failure]))
    assert result.status == expected
    assert not result.pagination_complete


def test_actual_empty_response_has_a_distinct_state(tmp_path: Path) -> None:
    result = fetch_ctgov_condition(
        tmp_path, "synthetic", transport=Pages([{"studies": [], "totalCount": 0}]),
    )
    assert result.status == "no_records"
    assert result.pagination_complete and not result.universe_closed


@pytest.mark.parametrize("mode", [
    "loop", "limit", "count_drift", "duplicate_drift", "platform_drift",
])
def test_partial_results_never_become_complete(tmp_path: Path, mode: str) -> None:
    second = {"studies": [_study(2)], "totalCount": 2}
    first = {"studies": [_study(1)], "totalCount": 2, "nextPageToken": "next"}
    if mode == "loop":
        second["nextPageToken"] = "next"
    if mode == "count_drift":
        second["totalCount"] = 3
    if mode == "duplicate_drift":
        changed = _study(1)
        changed["extra"] = "changed mid-pagination"
        second["studies"] = [changed]
    if mode == "platform_drift":
        changed = _study(2)
        changed["derivedSection"] = {"miscInfoModule": {"versionHolder": "2026-09-07"}}
        second["studies"] = [changed]
    result = fetch_ctgov_condition(
        tmp_path, "synthetic", transport=Pages([first, second]),
        max_pages=1 if mode == "limit" else 10,
    )
    assert result.status == "incomplete"
    assert not result.pagination_complete
    assert result.studies


@pytest.mark.parametrize("status,kind", [(429, "rate_limited"), (503, "network_error"),
                                         (403, "access_denied"), (302, "invalid_response")])
def test_http_error_does_not_save_response_body(
    tmp_path: Path, status: int, kind: str,
) -> None:
    def transport(url: str, timeout: float, max_bytes: int) -> HttpPage:
        return HttpPage(status, "text/html", b"untrusted error body", url)

    result = fetch_ctgov_condition(tmp_path, "synthetic", transport=transport)
    assert result.status == kind
    assert not result.pages
    assert not (tmp_path / "evidence").exists()


def test_acquisition_derives_each_record_with_raw_page_proof(tmp_path: Path) -> None:
    from ci_workflow.sources.connectors.ctgov_fetch import derive_ctgov_records
    from ci_workflow.storage.source_derivation import verify_source_text_derivation

    result = fetch_ctgov_condition(tmp_path, "synthetic", transport=Pages([
        {"studies": [_study(1), _study(2)], "totalCount": 2},
    ]))
    derived = derive_ctgov_records(tmp_path, result)
    assert [item.nct_id for item in derived] == ["NCT00000001", "NCT00000002"]
    for index, item in enumerate(derived):
        assert item.text_derivation.record_selector.study_index == index
        assert item.text_derivation.raw_asset == result.pages[0].raw_asset
        verify_source_text_derivation(tmp_path, item.text_derivation, item.content_text)
        assert item.registry_posted_date_precision == "calendar_day"


@pytest.mark.parametrize("fault", ["partial", "bytes", "study_identity", "query"])
def test_record_projection_reopens_and_validates_acquisition(tmp_path: Path, fault: str) -> None:
    from ci_workflow.sources.connectors.ctgov_fetch import derive_ctgov_records
    from ci_workflow.storage.source_derivation import SourceDerivationError

    result = fetch_ctgov_condition(tmp_path, "synthetic", transport=Pages([
        {"studies": [_study(1)], "totalCount": 1},
    ]))
    if fault == "partial":
        result = result.model_copy(update={"status": "incomplete", "pagination_complete": False})
    elif fault == "bytes":
        (tmp_path / result.pages[0].raw_asset.relative_path).write_bytes(b"drift")
    elif fault == "query":
        result = result.model_copy(update={"condition": "changed"})
    else:
        result = result.model_copy(update={"studies": (result.studies[0].model_copy(update={
            "source_version_id": "wrong",
        }),)})
    with pytest.raises(SourceDerivationError):
        derive_ctgov_records(tmp_path, result)
