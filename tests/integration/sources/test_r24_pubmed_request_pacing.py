"""Production transport pacing; synthetic clock/network, no external requests."""
from __future__ import annotations

from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from ci_workflow.sources.connectors import pubmed_fetch


class Clock:
    def __init__(self, start: float) -> None:
        self.now = start
        self.delays: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, delay: float) -> None:
        assert 0 < delay < 1
        self.delays.append(delay)
        self.now += delay


def install_transport(
    monkeypatch: pytest.MonkeyPatch, clock: Clock,
) -> list[float]:
    starts: list[float] = []

    class Opener:
        def open(self, request: object, timeout: float) -> object:
            starts.append(clock.now)
            # A failed request consumes its admission slot too; no hidden retry.
            raise HTTPError("https://eutils.ncbi.nlm.nih.gov/", 429, "rate", {}, None)

    monkeypatch.setattr(pubmed_fetch, "build_opener", lambda handler: Opener())
    monkeypatch.setattr(pubmed_fetch, "time", SimpleNamespace(
        monotonic=clock.monotonic, sleep=clock.sleep,
    ), raising=False)
    monkeypatch.setattr(pubmed_fetch, "_LAST_REQUEST_STARTED", None, raising=False)
    return starts


@pytest.mark.parametrize("initial_time", [0.0, 100.0])
def test_fast_mixed_eutils_requests_share_a_no_key_budget(
    monkeypatch: pytest.MonkeyPatch, initial_time: float,
) -> None:
    clock = Clock(initial_time)
    starts = install_transport(monkeypatch, clock)
    urls = [
        pubmed_fetch.build_pubmed_term_search_url("trial", retstart=0, retmax=1),
        pubmed_fetch.build_pubmed_records_url(("111",)),
        pubmed_fetch.build_pubmed_summary_url(("222",)),
    ]
    for url in urls + urls:
        response = pubmed_fetch._download(url, 5, 1024)
        assert response.status == 429 and response.body == b""
    assert len(starts) == 6  # Failures do not cause automatic retries.
    assert starts[0] == initial_time  # No gratuitous initial wait.
    assert all(right - left >= 1 / 3 for left, right in zip(starts, starts[1:], strict=False))
    assert len(clock.delays) == 5


def test_slow_transport_does_not_pay_a_second_fixed_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = Clock(100)
    starts = install_transport(monkeypatch, clock)
    url = pubmed_fetch.build_pubmed_records_url(("111",))
    pubmed_fetch._download(url, 5, 1024)
    clock.now += 2
    pubmed_fetch._download(url, 5, 1024)
    assert starts == [100, 102]
    assert clock.delays == []
