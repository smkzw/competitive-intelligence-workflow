"""The installed CLI can acquire sources without printing full source records."""

import json
from pathlib import Path

import pytest

from ci_workflow.cli import main
from ci_workflow.sources.connectors import ctgov_fetch
from tests.integration.sources.test_ctgov_fetch import Pages, _study
from tests.integration.test_research_package_submission import _project


@pytest.mark.parametrize("network_failure", [False, True])
def test_fetch_cli_retains_source_or_failure_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    network_failure: bool,
) -> None:
    project = _project(tmp_path)
    pages = Pages([TimeoutError()] if network_failure else [
        {"studies": [_study(1)], "totalCount": 1},
    ])
    monkeypatch.setattr(ctgov_fetch, "_download", pages)
    code = main([
        "research", "fetch-ctgov", "--project", str(project), "--condition", "synthetic",
    ])
    assert code == (7 if network_failure else 0)
    output = capsys.readouterr()
    assert "protocolSection" not in output.out
    pointer = json.loads(output.out)
    receipt = json.loads((project / pointer["capture_path"]).read_bytes())
    assert receipt["acquisition"]["universe_closed"] is False
    if network_failure:
        assert receipt["acquisition"]["status"] == "network_error"
        assert receipt["records"] == []
    else:
        assert receipt["acquisition"]["status"] == "complete"
        assert len(receipt["records"]) == 1
        entry = receipt["records"][0]
        capture = json.loads((project / entry["capture_path"]).read_bytes())
        assert capture["media_type"] == "application/json"
        assert json.loads(capture["content_text"]) == _study(1)
        assert capture["text_derivation"]["record_selector"]["nct_id"] == "NCT00000001"
        assert entry["registry_posted_date_precision"] == "calendar_day"


@pytest.mark.parametrize("mode", ["empty", "bad-date", "page-limit"])
def test_fetch_cli_distinguishes_empty_partial_and_unusable_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], mode: str,
) -> None:
    project = _project(tmp_path)
    study = _study(1)
    if mode == "bad-date":
        study["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"] = "unknown"
    payload = {"studies": [] if mode == "empty" else [study],
               "totalCount": 0 if mode == "empty" else 1}
    if mode == "page-limit":
        payload.update(totalCount=2, nextPageToken="more")
    monkeypatch.setattr(ctgov_fetch, "_download", Pages([payload]))
    code = main([
        "research", "fetch-ctgov", "--root", str(project), "--condition", "synthetic",
        "--max-pages", "1",
    ])
    pointer = json.loads(capsys.readouterr().out)
    receipt = json.loads((project / pointer["capture_path"]).read_bytes())
    assert receipt["records"] == []
    if mode == "empty":
        assert code == 0 and pointer["status"] == "no_records"
        assert pointer["projection_status"] == "complete"
    elif mode == "bad-date":
        assert code == 7 and pointer["projection_status"] == "invalid_record"
    else:
        assert code == 7 and pointer["status"] == "incomplete"
        assert len(receipt["acquisition"]["pages"]) == 1
