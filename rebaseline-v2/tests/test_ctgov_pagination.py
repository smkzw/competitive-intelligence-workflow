"""CT.gov search 分页：全量模式、显式上限、游标故障守卫与检索参数保真。全离线。"""
from __future__ import annotations

import json
from typing import Any

import pytest

from ciw2.sources import ctgov
from ciw2.sources.http import Fetched


def _study(nct: str) -> dict[str, Any]:
    return {"protocolSection": {"identificationModule": {"nctId": nct, "briefTitle": f"Study {nct}"}}}


def _page(*ncts: str, token: str | None = None) -> dict[str, Any]:
    return {"studies": [_study(n) for n in ncts], "nextPageToken": token}


class FakePages:
    """按顺序返回预置页；请求超出预置页数即报错，防止实现缺陷时真死循环。"""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self.pages = pages
        self.calls: list[dict[str, Any]] = []

    def __call__(self, ctx: Any, url: str, *, kind: str, params: dict[str, Any] | None = None,
                 title: str = "", **kwargs: Any) -> Fetched:
        self.calls.append(dict(params or {}))
        if len(self.calls) > len(self.pages):
            raise AssertionError("TEST-CALL-BUDGET: 请求次数超出预置页数，分页未停止")
        payload = self.pages[len(self.calls) - 1]
        return Fetched(source_id=None, url=url, status=200, content=json.dumps(payload).encode(),
                       text="", content_type="application/json")


def _install(monkeypatch: pytest.MonkeyPatch, pages: list[dict[str, Any]]) -> FakePages:
    fake = FakePages(pages)
    monkeypatch.setattr(ctgov, "fetch", fake)
    return fake


def test_full_mode_walks_every_page_in_source_order(monkeypatch):
    fake = _install(monkeypatch, [_page("NCT00000001", "NCT00000002", token="t1"),
                                  _page("NCT00000003", token="t2"),
                                  _page("NCT00000004")])
    rows = ctgov.search(None, condition="Atopic Dermatitis", term="IL-31", intervention="nemolizumab",
                        location="China")
    assert [r["nct"] for r in rows] == ["NCT00000001", "NCT00000002", "NCT00000003", "NCT00000004"]
    assert [c.get("pageToken") for c in fake.calls] == [None, "t1", "t2"]
    for call in fake.calls:
        assert call["query.cond"] == "Atopic Dermatitis"
        assert call["query.term"] == "IL-31"
        assert call["query.intr"] == "nemolizumab"
        assert call["query.locn"] == "China"
        assert call["pageSize"] == 100


def test_full_mode_has_no_implicit_100_cap(monkeypatch):
    first = [f"NCT{i:08d}" for i in range(1, 101)]
    second = [f"NCT{i:08d}" for i in range(101, 106)]
    fake = _install(monkeypatch, [_page(*first, token="t1"), _page(*second)])
    rows = ctgov.search(None)
    assert len(rows) == 105
    assert rows[0]["nct"] == "NCT00000001" and rows[-1]["nct"] == "NCT00000105"
    assert len(fake.calls) == 2


def test_explicit_limit_is_bounded_across_pages(monkeypatch):
    fake = _install(monkeypatch, [_page("NCT00000001", token="t1"),
                                  _page("NCT00000002", "NCT00000003")])
    rows = ctgov.search(None, max_results=3)
    assert [r["nct"] for r in rows] == ["NCT00000001", "NCT00000002", "NCT00000003"]
    assert len(fake.calls) == 2
    assert fake.calls[0]["pageSize"] == 3


def test_explicit_limit_stops_without_fetching_next_page(monkeypatch):
    fake = _install(monkeypatch, [_page("NCT00000001", "NCT00000002", token="t1")])
    rows = ctgov.search(None, max_results=2)
    assert [r["nct"] for r in rows] == ["NCT00000001", "NCT00000002"]
    assert len(fake.calls) == 1
    assert "pageToken" not in fake.calls[0]


def test_duplicate_nct_across_pages_is_kept_once_in_first_seen_order(monkeypatch):
    fake = _install(monkeypatch, [_page("NCT00000001", "NCT00000002", token="t1"),
                                  _page("NCT00000002", "NCT00000003", token="t2"),
                                  _page("NCT00000001", "NCT00000004")])
    rows = ctgov.search(None)
    assert [r["nct"] for r in rows] == ["NCT00000001", "NCT00000002", "NCT00000003", "NCT00000004"]
    assert len(fake.calls) == 3


@pytest.mark.parametrize("bad", [0, -1])
def test_non_positive_limit_rejected_before_requests(monkeypatch, bad):
    fake = _install(monkeypatch, [_page("NCT00000001")])
    with pytest.raises(ValueError, match="max_results"):
        ctgov.search(None, max_results=bad)
    assert fake.calls == []


@pytest.mark.parametrize("bad", [True, False, 1.5, 2.0, "10"])
def test_invalid_limit_type_rejected_before_requests(monkeypatch, bad):
    fake = _install(monkeypatch, [_page("NCT00000001")])
    with pytest.raises(TypeError, match="max_results"):
        ctgov.search(None, max_results=bad)
    assert fake.calls == []


def test_repeated_cursor_fails_instead_of_looping(monkeypatch):
    fake = _install(monkeypatch, [_page("NCT00000001", token="t1"),
                                  _page("NCT00000002", token="t1")])
    with pytest.raises(RuntimeError, match="游标重复"):
        ctgov.search(None)
    assert len(fake.calls) == 2


def test_empty_page_with_cursor_fails_instead_of_partial_complete(monkeypatch):
    fake = _install(monkeypatch, [_page("NCT00000001", token="t1"), _page(token="t2")])
    with pytest.raises(RuntimeError, match="空页"):
        ctgov.search(None)
    assert len(fake.calls) == 2


def test_legitimate_empty_result_returns_empty(monkeypatch):
    fake = _install(monkeypatch, [{"studies": [], "nextPageToken": None}])
    assert ctgov.search(None, condition="no-such-study") == []
    assert len(fake.calls) == 1


@pytest.mark.parametrize('bad', [None, '', 'not-a-study'])
def test_invalid_study_identity_is_not_counted_as_a_valid_result(monkeypatch, bad):
    _install(monkeypatch, [{'studies': [_study(bad)]}])
    with pytest.raises(RuntimeError, match='登记号'):
        ctgov.search(None)


def test_duplicate_only_page_is_not_unbounded_progress(monkeypatch):
    _install(monkeypatch, [_page('NCT00000001', token='t1'), _page('NCT00000001', token='t2')])
    with pytest.raises(RuntimeError, match='新增'):
        ctgov.search(None)


def test_model_tool_default_walks_complete_source_not_hidden_hundred(monkeypatch):
    from ciw2.harness.tools import ToolContext

    fake = _install(monkeypatch, [_page('NCT00000001', token='t1'), _page('NCT00000002')])
    args = ctgov.SearchArgs(route_id='global:full-test')
    assert args.max_results is None
    result = ctgov._ctgov_search(ToolContext(), args)
    assert result['count'] == 2 and result['collection_scope'] == 'full'
    assert len(fake.calls) == 2
