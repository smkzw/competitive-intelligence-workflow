"""CTR 检索列表浏览器捕获的确定性校验。仅合成小夹具，全离线。"""
from __future__ import annotations

from typing import Any

import pytest

from ciw2.sources.china_capture import CaptureError, parse_capture, parse_page

URL = "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml"
QUERY = "特应性皮炎"
HEADERS = ["序号", "登记号", "试验状态", "药物名称", "适应症", "试验通俗题目"]


def _footer(current: int, total_pages: int, total_records: int, comma: str = "，") -> str:
    return (f"跳转到  页    当前第 {current} 页{comma}共 {total_pages} 页{comma}共 {total_records} 条记录\n"
            "1\n(current)\n \n2\n \n")


def _row(number: int, *, ctr: str | None = None, drug: str = "甲药片", status: str = "进行中 尚未招募",
         indication: str = "特应性皮炎", title: str = "甲药片人体生物等效性研究",
         detail: str | None = None) -> dict[str, Any]:
    return {"cells": [f" {number}", f"CTR{10000000 + number}" if ctr is None else ctr, status, drug,
                      indication, title],
            "detail_id": f"{number:032x}" if detail is None else detail}


def _page(rows: list[dict[str, Any]], *, current: int, total_pages: int, total_records: int,
          url: str = URL, query: str = QUERY, headers: list[Any] | None = None,
          footer: str | None = None) -> dict[str, Any]:
    return {"url": url, "query": query, "headers": list(HEADERS) if headers is None else headers,
            "rows": rows,
            "pagination_text": _footer(current, total_pages, total_records) if footer is None else footer}


def _multi(total_pages: int = 3, total_records: int = 45, page_size: int = 20) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    seen = 0
    for current in range(1, total_pages + 1):
        count = min(page_size, total_records - seen)
        pages.append(_page([_row(seen + offset + 1) for offset in range(count)],
                           current=current, total_pages=total_pages, total_records=total_records))
        seen += count
    return pages


def _single(row: dict[str, Any], *, total_records: int = 1) -> dict[str, Any]:
    return _page([row], current=1, total_pages=1, total_records=total_records)


def test_capture_error_is_value_error():
    assert issubclass(CaptureError, ValueError)


@pytest.mark.parametrize('detail',['1731_p','1320_p','1318_p','1317_p','d2627e80da8f4e69bda2be4a861e7ee5_p'])
def test_observed_legacy_public_record_ids_are_preserved_without_guessing_urls(detail):
    out=parse_capture([_single(_row(1,detail=detail))],query=QUERY)
    assert out['complete'] and out['results'][0]['detail_id']==detail


@pytest.mark.parametrize('detail',['0_p','-1_p','12_p/../x','12_p?token=x','javascript:12_p'])
def test_legacy_id_is_not_an_arbitrary_path_or_credential_field(detail):
    with pytest.raises(CaptureError):
        parse_page(_single(_row(1,detail=detail)),query=QUERY)


def test_actual_positive_page_shape_is_accepted():
    page = _page([_row(i) for i in range(1, 21)], current=1, total_pages=24, total_records=464)
    out = parse_page(page, query=QUERY)
    assert out["page"] == 1
    assert out["total_pages"] == 24
    assert out["total_records"] == 464
    assert out["query"] == QUERY
    assert [r["row_number"] for r in out["results"]] == list(range(1, 21))
    assert out["results"][0]["raw_cells"] == page["rows"][0]["cells"]
    assert out["results"][0]["source_url"] == URL


def test_full_multi_page_capture_is_complete_with_provenance():
    pages = _multi()
    out = parse_capture([pages[2], pages[0], pages[1]], query=QUERY)
    assert out["complete"] is True
    assert out["query"] == QUERY
    assert out["total_pages"] == 3
    assert out["total_records"] == 45
    assert out["pages_read"] == [1, 2, 3]
    assert out["pending_pages"] == []
    assert len(out["results"]) == 45
    assert out["results"][0]["ctr"] == "CTR10000001"
    assert out["results"][0]["page"] == 1
    assert out["results"][-1]["ctr"] == "CTR10000045"
    assert out["results"][-1]["page"] == 3
    assert "info.dhtml" not in out["results"][0]["source_url"]
    assert out["results"][0]["detail_id"] == pages[0]["rows"][0]["detail_id"]


def test_query_and_headers_accept_whitespace_normalization():
    headers = [" 序号 ", "登记号\t", "试验状态", "药物名称 ", " 适应症", "试验通俗题目\u3000"]
    page = _page([_row(1)], current=1, total_pages=1, total_records=1, query="  特应性皮炎  ",
                 headers=headers)
    out = parse_page(page, query="\u3000特应性皮炎\t")
    assert out["query"] == QUERY
    assert out["results"][0]["drug_name"] == "甲药片"


def test_empty_indication_and_title_are_retained():
    page = _single(_row(1, indication="", title=""))
    out = parse_page(page, query=QUERY)
    assert out["results"][0]["indication"] == ""
    assert out["results"][0]["title"] == ""
    assert out["results"][0]["raw_cells"] == page["rows"][0]["cells"]


def test_long_compound_names_and_titles_are_not_split_or_truncated():
    drug = "重组抗IL-4Rα人源化单克隆抗体注射液（611）两种规格/复方缓释片；对照药"
    title = "一项在健康成年试验参与者中的随机、双盲、安慰剂对照研究" * 20
    page = _single(_row(1, drug=drug, title=title))
    out = parse_page(page, query=QUERY)
    result = out["results"][0]
    assert result["drug_name"] == drug
    assert result["title"] == title
    assert result["raw_cells"][3] == drug
    assert result["raw_cells"][5] == title


def test_pagination_accepts_ascii_commas_and_extra_digits_elsewhere():
    pages = _multi()
    for page in pages:
        page["pagination_text"] = page["pagination_text"].replace("，", ",")
    pages[0]["pagination_text"] = "跳转到 24 页 第 2 页 共 464 条记录\n" + pages[0]["pagination_text"]
    out = parse_capture(pages, query=QUERY)
    assert out["complete"] is True
    assert out["pages_read"] == [1, 2, 3]


@pytest.mark.parametrize("current, total_pages", [(0, 0), (1, 1), (1, 0), (0, 1)])
def test_explicit_zero_count_page_is_empty_and_complete(current, total_pages):
    page = _page([], current=current, total_pages=total_pages, total_records=0)
    out = parse_page(page, query=QUERY)
    assert out["results"] == []
    assert out["total_records"] == 0
    capture = parse_capture([page], query=QUERY)
    assert capture["complete"] is True
    assert capture["results"] == []
    assert capture["pending_pages"] == []
    assert capture["pages_read"] == [current]
    assert capture["total_pages"] == total_pages


def test_zero_count_page_with_rows_is_rejected():
    page = _page([_row(1)], current=1, total_pages=1, total_records=0)
    with pytest.raises(CaptureError, match="零记录"):
        parse_page(page, query=QUERY)
    with pytest.raises(CaptureError):
        parse_capture([page], query=QUERY, allow_partial=True)


@pytest.mark.parametrize("footer", [
    "",
    "系统繁忙，请稍后重试",
    "请输入验证码后继续访问",
    "HTTP 403 Forbidden",
    "当前第 1 页",
    "当前第 1 页，共 3 页",
    "1 2 3 4 24 »",
    "2024",
])
def test_missing_footer_or_challenge_is_not_an_empty_result(footer):
    page = _page([], current=1, total_pages=0, total_records=0, footer=footer)
    with pytest.raises(CaptureError, match="分页"):
        parse_page(page, query=QUERY)
    with pytest.raises(CaptureError, match="分页"):
        parse_capture([page], query=QUERY)


@pytest.mark.parametrize("footer", [
    "当前第 2 页，共 1 页，共 5 条记录",
    "当前第 1 页，共 0 页，共 5 条记录",
    "当前第 1 页，共 2 页，共 0 条记录",
    "当前第 0 页，共 1 页，共 5 条记录",
    "当前第 1 页，共 4 页，共 3 条记录",
])
def test_contradictory_pagination_metadata_is_rejected(footer):
    page = _page([_row(1)], current=1, total_pages=1, total_records=1, footer=footer)
    with pytest.raises(CaptureError, match="分页|页|记录"):
        parse_page(page, query=QUERY)


def test_two_different_footers_in_one_capture_are_rejected():
    text = _footer(1, 3, 45) + _footer(1, 4, 45)
    page = _page([_row(1)], current=1, total_pages=3, total_records=45, footer=text)
    with pytest.raises(CaptureError, match="分页"):
        parse_page(page, query=QUERY)


@pytest.mark.parametrize("bad_url", [
    "http://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml",
    "https://evil.example/clinicaltrials.searchlist.dhtml",
    "https://www.chinadrugtrials.org.cn.evil.example/clinicaltrials.searchlist.dhtml",
    "https://user:secret@www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml",
    "https://www.chinadrugtrials.org.cn/clinicaltrials.info.dhtml",
    "https://www.chinadrugtrials.org.cn/ClinicalTrials.searchlist.dhtml",
    "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml/",
    "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml#frag",
    "https://www.chinadrugtrials.org.cn:444/clinicaltrials.searchlist.dhtml",
    "https://www.chinadrugtrials.org.cn/ clinicaltrials.searchlist.dhtml",
    "not-a-url",
])
def test_source_url_must_be_public_https_list_url(bad_url):
    page = _single(_row(1))
    page["url"] = bad_url
    with pytest.raises(CaptureError, match="URL|来源|地址"):
        parse_page(page, query=QUERY)


@pytest.mark.parametrize("good_url", [
    "https://chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml",
    "https://www.chinadrugtrials.org.cn:443/clinicaltrials.searchlist.dhtml",
])
def test_public_host_variants_are_accepted(good_url):
    page = _single(_row(1))
    page["url"] = good_url
    assert parse_page(page, query=QUERY)["results"][0]["source_url"] == good_url


@pytest.mark.parametrize("headers", [
    ["登记号", "序号", "试验状态", "药物名称", "适应症", "试验通俗题目"],
    ["序号", "登记号", "试验状态", "药物名称", "适应症"],
    list(HEADERS) + ["申办方"],
    ["序号", "登记号", "试验状态", "药物名称", "适应症", 6],
])
def test_wrong_headers_are_rejected(headers):
    page = _page([_row(1)], current=1, total_pages=1, total_records=1, headers=headers)
    with pytest.raises(CaptureError, match="表头|列"):
        parse_page(page, query=QUERY)


@pytest.mark.parametrize("bad_query, expected", [
    ("银屑病", QUERY),
    ("  ", QUERY),
    (QUERY, "  "),
    (QUERY, None),
    (None, QUERY),
])
def test_wrong_or_blank_query_is_rejected(bad_query, expected):
    page = _page([_row(1)], current=1, total_pages=1, total_records=1, query=bad_query)
    with pytest.raises(CaptureError, match="查询"):
        parse_page(page, query=expected)


def test_page_shape_rejects_missing_or_hidden_keys():
    page = _single(_row(1))
    del page["pagination_text"]
    with pytest.raises(CaptureError, match="结构"):
        parse_page(page, query=QUERY)
    page = _single(_row(1))
    page["cookies"] = "session=secret"
    with pytest.raises(CaptureError, match="结构"):
        parse_page(page, query=QUERY)


@pytest.mark.parametrize("mutate", [
    lambda p: p.__setitem__("rows", "not-a-list"),
    lambda p: p.__setitem__("url", 7),
    lambda p: p.__setitem__("headers", tuple(HEADERS)),
    lambda p: p.__setitem__("pagination_text", None),
])
def test_page_field_types_are_rejected(mutate):
    page = _single(_row(1))
    mutate(page)
    with pytest.raises(CaptureError):
        parse_page(page, query=QUERY)


@pytest.mark.parametrize("mutate", [
    lambda r: r.__setitem__("extra", "x"),
    lambda r: r.pop("detail_id"),
    lambda r: r.__setitem__("cells", r["cells"][:5]),
    lambda r: r.__setitem__("cells", r["cells"] + ["多列"]),
    lambda r: r["cells"].__setitem__(3, 123),
])
def test_row_shape_and_cell_types_are_rejected(mutate):
    row = _row(1)
    mutate(row)
    with pytest.raises(CaptureError, match="捕获|列|结构|单元格|detail_id|缺少"):
        parse_page(_single(row), query=QUERY)


@pytest.mark.parametrize("ctr", ["CTR1234567", "CTR123456789", "ctr12345678", "CTR1234567a", ""])
def test_malformed_ctr_is_rejected(ctr):
    with pytest.raises(CaptureError, match="登记号"):
        parse_page(_single(_row(1, ctr=ctr)), query=QUERY)


@pytest.mark.parametrize("detail", ["abc", "a" * 31, "a" * 33, "g" * 32, 123, None])
def test_malformed_detail_id_is_rejected(detail):
    row = _row(1)
    row["detail_id"] = detail
    with pytest.raises(CaptureError, match="detail_id"):
        parse_page(_single(row), query=QUERY)


@pytest.mark.parametrize("number", ["0", "-1", "1.0", "", "abc"])
def test_malformed_row_number_is_rejected(number):
    row = _row(1)
    row["cells"][0] = number
    with pytest.raises(CaptureError, match="序号"):
        parse_page(_single(row), query=QUERY)


@pytest.mark.parametrize("drug", ["", "   "])
def test_empty_drug_name_is_rejected(drug):
    with pytest.raises(CaptureError, match="药物名称"):
        parse_page(_single(_row(1, drug=drug)), query=QUERY)


def test_duplicate_page_number_is_source_drift_even_if_identical():
    pages = _multi()
    duplicated = {**pages[0], "rows": [dict(row) for row in pages[0]["rows"]]}
    with pytest.raises(CaptureError, match="重复"):
        parse_capture([pages[0], duplicated, pages[1]], query=QUERY, allow_partial=True)


def test_duplicate_ctr_across_pages_is_rejected_with_partial_allowed():
    pages = _multi(2, 40)
    pages[1]["rows"][0]["cells"][1] = pages[0]["rows"][0]["cells"][1]
    with pytest.raises(CaptureError, match="重复"):
        parse_capture(pages, query=QUERY, allow_partial=True)


def test_duplicate_detail_id_across_pages_is_rejected():
    pages = _multi(2, 40)
    pages[1]["rows"][0]["detail_id"] = pages[0]["rows"][0]["detail_id"]
    with pytest.raises(CaptureError, match="重复"):
        parse_capture(pages, query=QUERY, allow_partial=True)


def test_identical_duplicate_row_within_page_is_rejected():
    page = _page([_row(1), _row(1)], current=1, total_pages=1, total_records=2)
    with pytest.raises(CaptureError, match="重复"):
        parse_capture([page], query=QUERY)


def test_metadata_drift_between_pages_is_rejected():
    pages = _multi()
    pages[1]["pagination_text"] = _footer(2, 4, 45)
    with pytest.raises(CaptureError, match="一致|总数"):
        parse_capture(pages, query=QUERY)
    pages = _multi()
    pages[1]["pagination_text"] = _footer(2, 3, 44)
    with pytest.raises(CaptureError, match="一致|总数"):
        parse_capture(pages, query=QUERY)


def test_non_contiguous_pages_are_not_a_partial_prefix():
    pages = _multi()
    with pytest.raises(CaptureError, match="前缀|页号"):
        parse_capture([pages[0], pages[2]], query=QUERY, allow_partial=True)
    with pytest.raises(CaptureError, match="前缀|页号"):
        parse_capture([pages[1]], query=QUERY, allow_partial=True)


def test_genuine_partial_prefix_returns_pending_pages():
    pages = _multi()[:2]
    out = parse_capture(pages, query=QUERY, allow_partial=True)
    assert out["complete"] is False
    assert out["pending_pages"] == [3]
    assert out["pages_read"] == [1, 2]
    assert out["total_pages"] == 3 and out["total_records"] == 45
    assert len(out["results"]) == 40
    with pytest.raises(CaptureError, match="不完整"):
        parse_capture(pages, query=QUERY)


@pytest.mark.parametrize("bad", [1, 0, "yes", None, [True]])
def test_partial_flag_must_be_a_real_bool(bad):
    pages = _multi()[:2]
    with pytest.raises(CaptureError, match="allow_partial"):
        parse_capture(pages, query=QUERY, allow_partial=bad)


def test_rows_equal_to_total_do_not_make_a_missing_page_complete():
    pages = _multi(total_pages=3, total_records=40)[:2]
    out = parse_capture(pages, query=QUERY, allow_partial=True)
    assert len(out["results"]) == 40
    assert out["complete"] is False
    assert out["pending_pages"] == [3]
    with pytest.raises(CaptureError, match="不完整"):
        parse_capture(pages, query=QUERY)


def test_record_overflow_is_rejected():
    pages = _multi(2, 30)
    pages[1]["rows"].append(_row(31))
    with pytest.raises(CaptureError, match="末页|超出|总数"):
        parse_capture(pages, query=QUERY)
    page = _page([_row(i) for i in range(1, 32)], current=1, total_pages=2, total_records=30)
    with pytest.raises(CaptureError, match="超出"):
        parse_page(page, query=QUERY)


@pytest.mark.parametrize("mutate", [
    lambda pages: pages[1]["rows"].pop(),
    lambda pages: pages[2]["rows"].append(_row(46)),
    lambda pages: pages[2]["rows"].pop(),
])
def test_full_page_count_mismatch_is_rejected(mutate):
    pages = _multi()
    mutate(pages)
    with pytest.raises(CaptureError, match="末页|页长|总数|不符"):
        parse_capture(pages, query=QUERY)


def test_empty_page_before_positive_total_is_rejected():
    pages = _multi()
    pages[1]["rows"] = []
    with pytest.raises(CaptureError, match="正数|空"):
        parse_page(pages[1], query=QUERY)
    with pytest.raises(CaptureError):
        parse_capture(pages, query=QUERY, allow_partial=True)


def test_page_number_beyond_declared_pages_is_rejected():
    page = _page([_row(21)], current=3, total_pages=2, total_records=45)
    with pytest.raises(CaptureError, match="分页|页"):
        parse_page(page, query=QUERY)


def test_capture_requires_non_empty_page_list():
    with pytest.raises(CaptureError, match="页"):
        parse_capture([], query=QUERY)
    with pytest.raises(CaptureError, match="pages|列表"):
        parse_capture("nope", query=QUERY)  # type: ignore[arg-type]
    with pytest.raises(CaptureError):
        parse_capture([None], query=QUERY)  # type: ignore[list-item]
