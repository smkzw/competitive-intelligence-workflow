"""CDE 受理品种目录公开列表捕获的确定性校验。仅合成小夹具，全离线。"""
from __future__ import annotations

from typing import Any

import pytest

from ciw2.sources.cde_capture import CaptureError, parse_capture, parse_page

URL = "https://www.cde.org.cn/main/xxgk/listpage/0123456789abcdef0123456789abcdef"
HEADERS = ["序号", "受理号", "药品名称", "药品类型", "申请类型", "注册分类", "企业名称", "承办日期"]
FILTERS = {"year": "", "drug_name": "示例单抗", "applicant": "", "acceptance_number": "",
           "drug_type": "", "application_type": ""}


def _row(number: int, *, acceptance: str | None = None, drug: str = "示例单抗注射液",
         drug_type: str = "治疗用生物制品", application: str = "补充申请", registration: str = "",
         applicant: str = "甲企业;乙企业;", date: str = "2026-01-01") -> list[str]:
    return [str(number), f"JYSB{number:07d}" if acceptance is None else acceptance, drug, drug_type,
            application, registration, applicant, date]


def _page(rows: list[Any], *, current: int = 1, page_size: int = 2, total: int = 5,
          url: str = URL, filters: Any = None, headers: Any = None, text: str | None = None) -> dict[str, Any]:
    return {"url": url, "section": "acceptance",
            "filters": dict(FILTERS) if filters is None else filters,
            "headers": list(HEADERS) if headers is None else headers, "rows": rows,
            "pagination": {"current": current, "page_size": page_size, "total_records": total,
                           "text": f"共 {total} 条上一页\n下一页" if text is None else text}}


def _pages(total: int = 5, page_size: int = 2) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    seen = 0
    total_pages = (total + page_size - 1) // page_size
    for current in range(1, total_pages + 1):
        count = min(page_size, total - seen)
        pages.append(_page([_row(seen + offset + 1) for offset in range(count)], current=current,
                           page_size=page_size, total=total))
        seen += count
    return pages


def test_capture_error_is_value_error():
    assert issubclass(CaptureError, ValueError)


def test_returned_schema_has_only_the_frozen_keys():
    pages = _pages()
    page = parse_page(pages[0], filters=FILTERS)
    assert set(page) == {"section", "filters", "page", "page_size", "total_records", "total_pages", "results"}
    assert set(page["results"][0]) == {
        "acceptance_number", "drug_name", "drug_type", "application_type", "registration_class",
        "company_text", "handled_date_text", "row_number", "page", "source_url", "raw_cells"}
    capture = parse_capture(pages, filters=FILTERS)
    assert set(capture) == {"section", "filters", "page_size", "total_pages", "total_records",
                            "pages_read", "pending_pages", "complete", "results"}


def test_full_capture_canonicalizes_order_and_preserves_public_rows():
    pages = _pages()
    out = parse_capture([pages[2], pages[0], pages[1]], filters=FILTERS)
    assert out["complete"] is True
    assert out["section"] == "acceptance"
    assert out["filters"] == FILTERS
    assert out["page_size"] == 2
    assert out["total_pages"] == 3
    assert out["total_records"] == 5
    assert out["pages_read"] == [1, 2, 3]
    assert out["pending_pages"] == []
    assert [row["row_number"] for row in out["results"]] == [1, 2, 3, 4, 5]
    assert [row["page"] for row in out["results"]] == [1, 1, 2, 2, 3]
    assert out["results"][0]["raw_cells"] == pages[0]["rows"][0]
    assert out["results"][0]["source_url"] == URL
    assert out["results"][0]["acceptance_number"] == "JYSB0000001"


def test_page_size_may_exceed_record_count_when_totals_agree():
    page = _page([_row(i) for i in range(1, 4)], page_size=50, total=3, text="共 3 条")
    out = parse_page(page, filters=FILTERS)
    assert out["total_pages"] == 1
    assert [row["row_number"] for row in out["results"]] == [1, 2, 3]


def test_partial_may_be_any_subset_and_reports_pending_pages():
    pages = _pages()
    out = parse_capture([pages[2], pages[0]], filters=FILTERS, allow_partial=True)
    assert out["complete"] is False
    assert out["pages_read"] == [1, 3]
    assert out["pending_pages"] == [2]
    assert len(out["results"]) == 3
    assert [row["page"] for row in out["results"]] == [1, 1, 3]
    with pytest.raises(CaptureError, match="不完整"):
        parse_capture([pages[2], pages[0]], filters=FILTERS)


def test_allow_partial_does_not_hide_a_complete_capture():
    pages = _pages()
    out = parse_capture(pages, filters=FILTERS, allow_partial=True)
    assert out["complete"] is True
    assert out["pending_pages"] == []


@pytest.mark.parametrize("current", [0, 1])
def test_explicit_zero_is_complete_without_missing_pages(current):
    page = _page([], current=current, page_size=50, total=0, text="共 0 条暂无数据")
    out = parse_page(page, filters=FILTERS)
    assert out["page"] == current
    assert out["total_pages"] == 0
    assert out["results"] == []
    capture = parse_capture([page], filters=FILTERS)
    assert capture["complete"] is True
    assert capture["pages_read"] == [current]
    assert capture["pending_pages"] == []
    assert capture["results"] == []


@pytest.mark.parametrize("text", ["", "暂无数据", "系统繁忙，请稍后重试", "10 条/页", "共 80 条"])
def test_missing_or_contradictory_footer_is_not_zero(text):
    page = _page([], current=1, page_size=50, total=0, text=text)
    with pytest.raises(CaptureError):
        parse_page(page, filters=FILTERS)


def test_zero_page_must_not_contain_rows():
    page = _page([_row(1)], current=1, page_size=50, total=0, text="共 0 条")
    with pytest.raises(CaptureError, match="零"):
        parse_page(page, filters=FILTERS)


@pytest.mark.parametrize("current", [2, -1, True])
def test_zero_current_outside_zero_or_one_is_rejected(current):
    page = _page([], current=current, page_size=50, total=0, text="共 0 条")
    with pytest.raises(CaptureError):
        parse_page(page, filters=FILTERS)


def test_positive_total_without_rows_is_not_zero():
    page = _page([], current=1, page_size=50, total=80)
    with pytest.raises(CaptureError, match="行数"):
        parse_page(page, filters=FILTERS)


@pytest.mark.parametrize("bad", [
    URL.replace("https://", "http://"),
    "https://evil.example/main/xxgk/listpage/" + "a" * 32,
    "https://www.cde.org.cn.evil.example/main/xxgk/listpage/" + "a" * 32,
    URL.replace("https://", "https://user:secret@"),
    URL + "#frag",
    URL + "?token=secret",
    URL + "?api_key=secret",
    URL + "?authorization=secret",
    URL + "?sessionid=secret",
    URL + "?jsessionid=secret",
    URL.replace(".org.cn", ".org.cn:444"),
    "https://www.cde.org.cn/main/xxgk/listpage/" + "a" * 31,
    "https://www.cde.org.cn/main/xxgk/listpage/" + "g" * 32,
    "https://www.cde.org.cn/main/xxgk/other/" + "a" * 32,
    "not-a-url",
])
def test_source_url_must_be_public_official_list_url(bad):
    page = _page([_row(1)], total=1, page_size=1, url=bad)
    with pytest.raises(CaptureError):
        parse_page(page, filters=FILTERS)


def test_url_error_does_not_echo_userinfo_or_token():
    for url in (URL.replace("https://", "https://user:secret@"), URL + "?token=secret"):
        with pytest.raises(CaptureError) as exc:
            parse_page(_page([_row(1)], total=1, page_size=1, url=url), filters=FILTERS)
        assert "secret" not in str(exc.value)


@pytest.mark.parametrize("good", [
    "https://cde.org.cn/main/xxgk/listpage/" + "a" * 32,
    "https://www.cde.org.cn:443/main/xxgk/listpage/" + "a" * 32,
])
def test_official_host_variants_are_accepted(good):
    page = _page([_row(1)], total=1, page_size=1, url=good)
    assert parse_page(page, filters=FILTERS)["results"][0]["source_url"] == good


def test_page_shape_rejects_missing_or_hidden_fields():
    page = _page([_row(1)], total=1, page_size=1)
    del page["pagination"]
    with pytest.raises(CaptureError, match="结构"):
        parse_page(page, filters=FILTERS)
    page = _page([_row(1)], total=1, page_size=1)
    page["cookies"] = "session=secret"
    with pytest.raises(CaptureError, match="结构"):
        parse_page(page, filters=FILTERS)


@pytest.mark.parametrize("section", ["Acceptance", "acceptance ", "approval", None])
def test_section_must_be_acceptance(section):
    page = _page([_row(1)], total=1, page_size=1)
    page["section"] = section
    with pytest.raises(CaptureError, match="栏目|acceptance"):
        parse_page(page, filters=FILTERS)


def test_filters_accept_whitespace_normalization_only():
    captured = dict(FILTERS)
    captured["drug_name"] = " 示例单抗 "
    captured["applicant"] = "\t"
    expected = dict(FILTERS)
    expected["drug_name"] = "示例单抗\u3000"
    page = _page([_row(1)], total=1, page_size=1, filters=captured)
    assert parse_page(page, filters=expected)["filters"] == FILTERS


@pytest.mark.parametrize("mutate", [
    lambda f: f.pop("year"),
    lambda f: f.__setitem__("token", "secret"),
    lambda f: f.__setitem__("year", 2025),
    lambda f: f.__setitem__("drug_name", ""),
    lambda f: f.__setitem__("year", "all"),
    lambda f: f.__setitem__("year", "25"),
])
def test_expected_filters_are_exact_six_string_fields_with_an_anchor(mutate):
    filters = dict(FILTERS)
    mutate(filters)
    with pytest.raises(CaptureError):
        parse_page(_page([_row(1)], total=1, page_size=1), filters=filters)


def test_missing_captured_filter_is_not_treated_as_empty():
    captured = dict(FILTERS)
    del captured["year"]
    page = _page([_row(1)], total=1, page_size=1, filters=captured)
    with pytest.raises(CaptureError, match="缺少"):
        parse_page(page, filters=FILTERS)


@pytest.mark.parametrize("field,value", [
    ("drug_name", "示例单抗注射液"),
    ("year", "2025"),
    ("applicant", "某企业"),
    ("acceptance_number", "JYSB2600265"),
    ("drug_type", "生物制品"),
    ("application_type", "补充申请"),
])
def test_captured_filters_must_match_expected(field, value):
    captured = dict(FILTERS)
    captured[field] = value
    page = _page([_row(1)], total=1, page_size=1, filters=captured)
    with pytest.raises(CaptureError, match="筛选"):
        parse_page(page, filters=FILTERS)


def test_nonempty_year_is_matched_and_retained():
    filters = dict(FILTERS)
    filters["year"] = "2025"
    page = _page([_row(1)], total=1, page_size=1, filters=filters)
    out = parse_page(page, filters=filters)
    assert out["filters"]["year"] == "2025"
    with pytest.raises(CaptureError, match="筛选"):
        parse_page(page, filters=FILTERS)


def test_observed_earlier_year_bucket_is_preserved_not_rewritten_as_a_year():
    filters={**FILTERS,'year':'2015及以前'}
    page=_page([_row(1)],total=1,page_size=1,filters=filters)
    assert parse_page(page,filters=filters)['filters']['year']=='2015及以前'


@pytest.mark.parametrize("headers", [
    ["受理号", "序号", "药品名称", "药品类型", "申请类型", "注册分类", "企业名称", "承办日期"],
    HEADERS[:7],
    HEADERS + ["审评状态"],
    ["序号", "受理号", "药品名称", "药品类型", "申请类型", "注册分类", "企业名称", 6],
])
def test_headers_must_be_the_eight_semantic_columns(headers):
    page = _page([_row(1)], total=1, page_size=1, headers=headers)
    with pytest.raises(CaptureError, match="表头|列"):
        parse_page(page, filters=FILTERS)


def test_header_whitespace_is_normalized():
    headers = [" 序号", "受理号\t", "药品名称 ", "药品类型", " 申请类型", "注册分类", "企业名称", "承办日期\u3000"]
    page = _page([_row(1)], total=1, page_size=1, headers=headers)
    assert parse_page(page, filters=FILTERS)["results"][0]["drug_name"] == "示例单抗注射液"


@pytest.mark.parametrize("mutate", [
    lambda r: r.pop(),
    lambda r: r.append("多列"),
    lambda r: r.__setitem__(2, 123),
])
def test_row_must_be_eight_string_cells(mutate):
    row = _row(1)
    mutate(row)
    with pytest.raises(CaptureError, match="列|字符串"):
        parse_page(_page([row], total=1, page_size=1), filters=FILTERS)


def test_row_must_be_a_list_not_a_tuple():
    row = tuple(_row(1))
    with pytest.raises(CaptureError, match="列|列表"):
        parse_page(_page([row], total=1, page_size=1), filters=FILTERS)


@pytest.mark.parametrize("ordinal", ["0", "-1", "1.0", "", "abc", "01"])
def test_ordinal_must_be_a_positive_integer(ordinal):
    row = _row(1)
    row[0] = ordinal
    with pytest.raises(CaptureError, match="序号"):
        parse_page(_page([row], total=1, page_size=1), filters=FILTERS)


@pytest.mark.parametrize("acceptance", [
    "CXSL2600180", "JTS2600100", "JXSL2500201", "JXSS2500063", "JYSB2600265", "JYSZ2500025", "ABC123",
])
def test_acceptance_number_is_uppercase_prefix_plus_digits(acceptance):
    row = _row(1, acceptance=acceptance)
    out = parse_page(_page([row], total=1, page_size=1), filters=FILTERS)
    assert out["results"][0]["acceptance_number"] == acceptance


@pytest.mark.parametrize("acceptance", ["jysb2600265", "2600265", "JYSB", "", "JYSB26002A5",
                                         "JYSB2600265X", "CXSL-2600180", "JYS B2600265"])
def test_malformed_acceptance_number_is_rejected(acceptance):
    row = _row(1, acceptance=acceptance)
    with pytest.raises(CaptureError, match="受理号"):
        parse_page(_page([row], total=1, page_size=1), filters=FILTERS)


@pytest.mark.parametrize("drug", ["", "   ", "\u3000"])
def test_drug_name_must_be_nonempty(drug):
    row = _row(1, drug=drug)
    with pytest.raises(CaptureError, match="药品名称"):
        parse_page(_page([row], total=1, page_size=1), filters=FILTERS)


def test_empty_optional_cells_stay_empty_and_raw_cells_are_exact():
    row = _row(7, drug_type="", application="", registration="", applicant="", date="")
    page = _page([row], total=1, page_size=1)
    result = parse_page(page, filters=FILTERS)["results"][0]
    assert result["drug_type"] == ""
    assert result["application_type"] == ""
    assert result["registration_class"] == ""
    assert result["company_text"] == ""
    assert result["handled_date_text"] == ""
    assert result["raw_cells"] == row


def test_long_compound_names_and_semicolon_company_text_are_preserved():
    drug = "示例单抗注射液（预充式注射器）;示例单抗注射液（西林瓶）" * 3
    applicant = ("示例药业国际集团有限公司（Example Pharma International Holdings Limited）;"
                 "示例生物医药（中国）有限公司;示例医药科技有限公司;")
    row = _row(1, drug=drug, applicant=applicant)
    result = parse_page(_page([row], total=1, page_size=1), filters=FILTERS)["results"][0]
    assert result["drug_name"] == drug
    assert result["company_text"] == applicant
    assert result["raw_cells"] == row


@pytest.mark.parametrize("mutate", [
    lambda p: p["pagination"].__setitem__("current", True),
    lambda p: p["pagination"].__setitem__("page_size", True),
    lambda p: p["pagination"].__setitem__("page_size", 0),
    lambda p: p["pagination"].__setitem__("total_records", True),
    lambda p: p["pagination"].__setitem__("total_records", -1),
    lambda p: p["pagination"].__setitem__("text", None),
    lambda p: p["pagination"].__setitem__("extra", 1),
    lambda p: p["pagination"].pop("page_size"),
])
def test_pagination_shape_and_types_are_strict(mutate):
    page = _page([_row(1)], total=1, page_size=1)
    mutate(page)
    with pytest.raises(CaptureError):
        parse_page(page, filters=FILTERS)


def test_current_page_must_be_within_derived_total_pages():
    page = _page([_row(1)], current=4, page_size=2, total=5)
    with pytest.raises(CaptureError, match="当前页"):
        parse_page(page, filters=FILTERS)


@pytest.mark.parametrize("mutate", [
    lambda p: p["rows"].pop(),
    lambda p: p["rows"].append(_row(9)),
])
def test_full_page_must_have_declared_page_size_rows(mutate):
    page = _pages()[0]
    mutate(page)
    with pytest.raises(CaptureError, match="行数"):
        parse_page(page, filters=FILTERS)


@pytest.mark.parametrize("count", [0, 2])
def test_last_page_must_have_the_remainder(count):
    rows = [_row(i) for i in range(1, count + 1)]
    page = _page(rows, current=3, page_size=2, total=5)
    with pytest.raises(CaptureError, match="行数"):
        parse_page(page, filters=FILTERS)


def test_more_rows_than_declared_total_is_rejected():
    page = _page([_row(i) for i in range(1, 4)], total=2, page_size=3)
    with pytest.raises(CaptureError, match="行数"):
        parse_page(page, filters=FILTERS)


@pytest.mark.parametrize("text", ["共 0 条", "共 1 条 共 2 条", "1 条", "系统繁忙"])
def test_footer_must_be_explicit_and_agree_with_declared_total(text):
    page = _page([_row(1)], total=1, page_size=1, text=text)
    with pytest.raises(CaptureError):
        parse_page(page, filters=FILTERS)


def test_pages_must_share_url_page_size_and_totals():
    pages = _pages()
    pages[1]["url"] = "https://www.cde.org.cn/main/xxgk/listpage/" + "b" * 32
    with pytest.raises(CaptureError, match="URL"):
        parse_capture(pages, filters=FILTERS)
    pages = _pages()
    pages[1]["pagination"]["page_size"] = 3
    with pytest.raises(CaptureError, match="不一致"):
        parse_capture(pages, filters=FILTERS)
    pages = _pages()
    pages[1]["pagination"]["total_records"] = 6
    pages[1]["pagination"]["text"] = "共 6 条"
    with pytest.raises(CaptureError, match="不一致"):
        parse_capture(pages, filters=FILTERS)


def test_duplicate_page_number_fails_even_when_identical():
    pages = _pages()
    with pytest.raises(CaptureError, match="重复"):
        parse_capture([pages[0], pages[0], pages[1], pages[2]], filters=FILTERS, allow_partial=True)


def test_duplicate_acceptance_number_fails_even_for_identical_rows():
    row = _row(1)
    page = _page([row, list(row)], total=2, page_size=2)
    with pytest.raises(CaptureError, match="重复"):
        parse_capture([page], filters=FILTERS, allow_partial=True)
    pages = _pages()
    pages[1]["rows"][0][1] = pages[0]["rows"][0][1]
    with pytest.raises(CaptureError, match="重复"):
        parse_capture(pages, filters=FILTERS)


@pytest.mark.parametrize("bad", [1, 0, "yes", None, [True]])
def test_allow_partial_must_be_a_real_bool(bad):
    pages = _pages()[:2]
    with pytest.raises(CaptureError, match="allow_partial"):
        parse_capture(pages, filters=FILTERS, allow_partial=bad)


def test_capture_requires_a_nonempty_page_list():
    with pytest.raises(CaptureError, match="页"):
        parse_capture([], filters=FILTERS)
    with pytest.raises(CaptureError, match="pages|列表"):
        parse_capture("nope", filters=FILTERS)  # type: ignore[arg-type]
    with pytest.raises(CaptureError):
        parse_capture([None], filters=FILTERS)  # type: ignore[list-item]
