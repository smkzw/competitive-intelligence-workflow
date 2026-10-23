"""CDE 受理品种目录公开列表捕获的确定性校验。

输入是浏览器已捕获的公开列表页（来源 URL、栏目、筛选、八列表头、行、分页），
输出可追溯的公开行。本模块不访问网络/浏览器、不生成详情页 URL、不判断适应症、
MAH、审评结论、批准状态或注册分类含义，也不把缺失写成 0。
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

SECTION = "acceptance"
FILTER_KEYS: tuple[str, ...] = ("year", "drug_name", "applicant", "acceptance_number",
                                "drug_type", "application_type")
COLUMNS: tuple[str, ...] = ("序号", "受理号", "药品名称", "药品类型", "申请类型", "注册分类",
                            "企业名称", "承办日期")
_PUBLIC_HOSTS = frozenset({"www.cde.org.cn", "cde.org.cn"})
_ALLOWED_PORTS = frozenset({None, 443})
_LIST_PATH = re.compile(r"/main/xxgk/listpage/[0-9a-fA-F]{32}\Z")
_PAGE_KEYS = frozenset({"url", "section", "filters", "headers", "rows", "pagination"})
_PAGINATION_KEYS = frozenset({"current", "page_size", "total_records", "text"})
_ACCEPTANCE = re.compile(r"[A-Z]+[0-9]+\Z")
_ORDINAL = re.compile(r"[1-9][0-9]*\Z")
_YEAR = re.compile(r"[0-9]{4}\Z")
_FOOTER = re.compile(r"共\s*([0-9]+)\s*条")


class CaptureError(ValueError):
    """捕获结构、来源身份或分页元数据不可信；调用方不得据此推断空结果。"""


def _norm(text: str) -> str:
    return " ".join(text.split())


def _require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaptureError(f"捕获字段 {field} 必须是对象")
    return value


def _require_exact_keys(obj: dict[str, Any], expected: frozenset[str], field: str) -> None:
    extra = sorted(set(obj) - expected, key=str)
    missing = sorted(expected - set(obj))
    if extra or missing:
        raise CaptureError(f"捕获字段 {field} 结构不符：缺少 {missing}，多出 {extra}")


def _require_int(value: Any, field: str, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise CaptureError(f"分页字段 {field} 必须是大于等于 {minimum} 的整数")
    return value


def _check_url(value: Any) -> str:
    if not isinstance(value, str):
        raise CaptureError("来源 URL 必须是字符串")
    url = value.strip()
    if not url or any(ch.isspace() for ch in url):
        raise CaptureError("来源 URL 为空或含空白")
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise CaptureError("来源 URL 无法解析") from exc
    if parsed.scheme != "https":
        raise CaptureError("来源 URL 必须是 https")
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        raise CaptureError("来源 URL 不得包含用户信息")
    if (parsed.hostname or "").lower() not in _PUBLIC_HOSTS:
        raise CaptureError("来源 URL 主机不是 CDE 官方站点")
    try:
        port = parsed.port
    except ValueError as exc:
        raise CaptureError("来源 URL 端口非法") from exc
    if port not in _ALLOWED_PORTS:
        raise CaptureError("来源 URL 端口必须是 443")
    if not _LIST_PATH.fullmatch(parsed.path):
        raise CaptureError("来源 URL 路径不是 CDE 受理品种目录列表页")
    if parsed.fragment:
        raise CaptureError("来源 URL 不得包含片段")
    if parsed.query:
        raise CaptureError("CDE表单筛选保留在捕获上下文，来源URL不接受查询/会话参数")
    return url


def _check_filters(actual: Any, expected: Any) -> dict[str, str]:
    wanted = _require_dict(expected, "filters")
    _require_exact_keys(wanted, frozenset(FILTER_KEYS), "filters")
    for key in FILTER_KEYS:
        if not isinstance(wanted[key], str):
            raise CaptureError(f"筛选条件 {key} 必须是字符串")
    normalized = {key: _norm(wanted[key]) for key in FILTER_KEYS}
    if not any(normalized[key] for key in ("drug_name", "applicant", "acceptance_number")):
        raise CaptureError("筛选条件至少需要药品名称、企业名称或受理号之一")
    if normalized["year"] and normalized['year'] != '2015及以前' and not _YEAR.fullmatch(normalized["year"]):
        raise CaptureError("筛选年份必须是公开选项：全部、四位年份或2015及以前")
    captured = _require_dict(actual, "page.filters")
    _require_exact_keys(captured, frozenset(FILTER_KEYS), "page.filters")
    for key in FILTER_KEYS:
        if not isinstance(captured[key], str):
            raise CaptureError(f"捕获筛选条件 {key} 必须是字符串")
        if _norm(captured[key]) != normalized[key]:
            raise CaptureError(f"捕获筛选条件 {key} 与期望不一致")
    return normalized


def _check_headers(value: Any) -> None:
    if not isinstance(value, list) or len(value) != len(COLUMNS):
        raise CaptureError(f"表头必须是 {len(COLUMNS)} 列")
    if any(not isinstance(item, str) for item in value):
        raise CaptureError("表头每列必须是字符串")
    if tuple(_norm(item) for item in value) != COLUMNS:
        raise CaptureError("表头不是当前八列语义顺序")


def _parse_pagination(value: Any) -> tuple[int, int | None, int, int]:
    pagination = _require_dict(value, "pagination")
    _require_exact_keys(pagination, _PAGINATION_KEYS, "pagination")
    current = _require_int(pagination["current"], "current", 0)
    total_records = _require_int(pagination["total_records"], "total_records", 0)
    text = pagination["text"]
    if not isinstance(text, str):
        raise CaptureError("分页文本必须是字符串")
    if text.strip() == '暂无内容' and current == 0 and total_records == 0 and pagination['page_size'] is None:
        return 0,None,0,0  # Actual CDE empty tbody has no paginator; do not invent a footer or page size.
    page_size = _require_int(pagination["page_size"], "page_size", 1)
    totals = {int(match.group(1)) for match in _FOOTER.finditer(text)}
    if not totals:
        raise CaptureError("分页页脚缺少「共 N 条」：不能当作零结果")
    if len(totals) > 1:
        raise CaptureError("分页页脚出现互相矛盾的记录总数")
    if totals.pop() != total_records:
        raise CaptureError("分页页脚记录总数与 total_records 不一致")
    total_pages = (total_records + page_size - 1) // page_size
    if total_records == 0:
        if current not in (0, 1):
            raise CaptureError("零记录页 current 只能为 0 或 1")
        return current, page_size, total_records, total_pages
    if not 1 <= current <= total_pages:
        raise CaptureError("当前页超出声明总页数")
    return current, page_size, total_records, total_pages


def _expected_rows(current: int, page_size: int, total_pages: int, total_records: int) -> int:
    if current < total_pages:
        return page_size
    expected = total_records - (total_pages - 1) * page_size
    if not 0 < expected <= page_size:
        raise CaptureError("分页元数据与页长矛盾")
    return expected


def _parse_row(value: Any, *, page: int, source_url: str) -> dict[str, Any]:
    if not isinstance(value, list) or len(value) != len(COLUMNS):
        raise CaptureError(f"每行必须是 {len(COLUMNS)} 列的字符串列表")
    if any(not isinstance(cell, str) for cell in value):
        raise CaptureError("每行单元格必须是字符串")
    ordinal = value[0].strip()
    if not _ORDINAL.fullmatch(ordinal):
        raise CaptureError(f"序号不是正整数：{value[0]!r}")
    acceptance_number = value[1].strip()
    if not _ACCEPTANCE.fullmatch(acceptance_number):
        raise CaptureError(f"受理号不是大写字母加数字：{value[1]!r}")
    drug_name = value[2].strip()
    if not drug_name:
        raise CaptureError("药品名称为空")
    return {
        "acceptance_number": acceptance_number,
        "drug_name": drug_name,
        "drug_type": value[3].strip(),
        "application_type": value[4].strip(),
        "registration_class": value[5].strip(),
        "company_text": value[6].strip(),  # Source column 企业名称 does not certify a legal party role.
        "handled_date_text": value[7].strip(),  # 承办日期, not a guessed receipt/approval/publication date.
        "row_number": int(ordinal),
        "page": page,
        "source_url": source_url,
        "raw_cells": list(value),
    }


def parse_page(page: dict[str, Any], *, filters: dict[str, Any]) -> dict[str, Any]:
    """校验一页捕获并返回规范化公开行；不判断任何医学或监管结论。"""
    page_obj = _require_dict(page, "page")
    _require_exact_keys(page_obj, _PAGE_KEYS, "page")
    url = _check_url(page_obj["url"])
    if page_obj["section"] != SECTION:
        raise CaptureError("捕获栏目必须是 acceptance")
    normalized_filters = _check_filters(page_obj["filters"], filters)
    _check_headers(page_obj["headers"])
    current, page_size, total_records, total_pages = _parse_pagination(page_obj["pagination"])
    rows = page_obj["rows"]
    if not isinstance(rows, list):
        raise CaptureError("rows 必须是列表")
    if total_records == 0:
        if rows:
            raise CaptureError("显式零结果不得包含行")
    else:
        assert page_size is not None
        expected = _expected_rows(current, page_size, total_pages, total_records)
        if len(rows) != expected:
            raise CaptureError(f"第 {current} 页行数 {len(rows)} 与应有行数 {expected} 不一致")
    results = [_parse_row(row, page=current, source_url=url) for row in rows]
    return {"section": SECTION, "filters": normalized_filters, "page": current, "page_size": page_size,
            "total_records": total_records, "total_pages": total_pages, "results": results}


def _check_unique(rows: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for row in rows:
        number = row["acceptance_number"]
        if number in seen:
            raise CaptureError(f"受理号重复：{number}")
        seen.add(number)


def parse_capture(pages: list[dict[str, Any]], *, filters: dict[str, Any],
                  allow_partial: bool = False) -> dict[str, Any]:
    """校验整份捕获：URL/筛选/页长/总数一致、页号与受理号唯一、完整或显式不完整。"""
    if type(allow_partial) is not bool:
        raise CaptureError("allow_partial 必须是布尔值")
    if not isinstance(pages, list):
        raise CaptureError("pages 必须是列表")
    if not pages:
        raise CaptureError("捕获至少需要一页")
    parsed = [parse_page(page, filters=filters) for page in pages]
    urls = {_check_url(page["url"]) for page in pages}
    first = parsed[0]
    page_size = first["page_size"]
    total_pages = first["total_pages"]
    total_records = first["total_records"]
    for item in parsed:
        if (item["page_size"], item["total_pages"], item["total_records"]) != (page_size, total_pages, total_records):
            raise CaptureError("各页分页元数据不一致")
        if item["filters"] != first["filters"]:
            raise CaptureError("各页筛选条件不一致")
    if len(urls) != 1:
        raise CaptureError("各页来源 URL 不一致")
    seen_pages: set[int] = set()
    for item in parsed:
        if item["page"] in seen_pages:
            raise CaptureError(f"第 {item['page']} 页重复出现")
        seen_pages.add(item["page"])
    ordered = sorted(parsed, key=lambda item: item["page"])
    pages_read = [item["page"] for item in ordered]
    if total_records == 0:
        if len(ordered) != 1:
            raise CaptureError("零结果捕获只能包含一页")
        return {"section": SECTION, "filters": first["filters"], "page_size": page_size,
                "total_pages": total_pages, "total_records": total_records, "pages_read": pages_read,
                "pending_pages": [], "complete": True, "results": []}
    complete = len(ordered) == total_pages
    if complete and pages_read != list(range(1, total_pages + 1)):
        raise CaptureError("完整捕获的页号不是 1..N")
    results = [row for item in ordered for row in item["results"]]
    _check_unique(results)
    if len(results) > total_records:
        raise CaptureError(f"记录数 {len(results)} 超出声明总数 {total_records}")
    if complete and len(results) != total_records:
        raise CaptureError(f"全部页行数 {len(results)} 与声明总数 {total_records} 不符")
    if not complete and not allow_partial:
        raise CaptureError(f"捕获不完整：已读 {len(ordered)}/{total_pages} 页")
    pending = sorted(set(range(1, total_pages + 1)) - set(pages_read))
    return {"section": SECTION, "filters": first["filters"], "page_size": page_size,
            "total_pages": total_pages, "total_records": total_records, "pages_read": pages_read,
            "pending_pages": pending, "complete": complete, "results": results}
