"""Offline proof replays the captured byte envelope, not a new download budget."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.sources.connectors import ctgov_fetch
from ci_workflow.storage.source_derivation import SourceDerivationError
from tests.integration.sources.test_ctgov_fetch import Pages, _study


@pytest.mark.parametrize("limited_default", ["max_total_bytes", "max_page_bytes"])
def test_replay_uses_exact_retained_byte_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limited_default: str,
) -> None:
    pages = Pages([
        {"studies": [_study(1)], "totalCount": 2, "nextPageToken": "next",
         "padding": "x" * 2048},
        {"studies": [_study(2)], "padding": "y" * 2048},
    ])
    original = ctgov_fetch.fetch_ctgov_condition
    result = original(tmp_path, "synthetic", page_size=1, transport=pages)
    assert result.pagination_complete

    def bounded_replay(*args: Any, **kwargs: Any) -> ctgov_fetch.CtgovFetchResult:
        # Simulate a captured set larger than today's default acquisition limit
        # without allocating 128 MiB of synthetic data or using the network.
        kwargs.setdefault(limited_default, 1024)
        return original(*args, **kwargs)

    monkeypatch.setattr(ctgov_fetch, "fetch_ctgov_condition", bounded_replay)
    derived = ctgov_fetch.derive_ctgov_records(tmp_path, result)
    assert {record.nct_id for record in derived} == {"NCT00000001", "NCT00000002"}
    for record in derived:
        assert json.loads(record.content_text)["protocolSection"]["identificationModule"]


def test_retained_budget_does_not_bypass_raw_size_integrity(tmp_path: Path) -> None:
    result = ctgov_fetch.fetch_ctgov_condition(
        tmp_path, "synthetic", transport=Pages([{"studies": [_study(1)], "totalCount": 1}]),
    )
    page = result.pages[0]
    tampered = result.model_copy(update={"pages": (
        page.model_copy(update={"raw_asset": page.raw_asset.model_copy(update={
            "byte_size": page.raw_asset.byte_size + 1,
        })}),
    )})
    with pytest.raises(SourceDerivationError):
        ctgov_fetch.derive_ctgov_records(tmp_path, tampered)
