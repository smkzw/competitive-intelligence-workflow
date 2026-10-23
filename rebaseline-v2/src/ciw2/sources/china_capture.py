"""中国药物临床试验登记平台检索列表浏览器捕获的确定性校验。

输入是已捕获的公开列表页（来源 URL、查询、六列表头、行、分页页脚），输出候选观察行。
本模块不访问网络/浏览器、不生成详情页 URL、不判断创新、MAH、期别或科学资格；
行号、页号和 detail_id 只作来源定位，不推断任何临床事实。
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from ciw2.sources.http import public_url

COLUMNS: tuple[str, ...] = ("序号", "登记号", "试验状态", "药物名称", "适应症", "试验通俗题目")
_PUBLIC_HOSTS = frozenset({"chinadrugtrials.org.cn", "www.chinadrugtrials.org.cn"})
_LIST_PATH = "/clinicaltrials.searchlist.dhtml"
_ALLOWED_PORTS = frozenset({None, 443})
_PAGE_KEYS = frozenset({"url", "query", "headers", "rows", "pagination_text"})
_ROW_KEYS = frozenset({"cells", "detail_id"})
_CTR = re.compile(r"CTR[0-9]{8}\Z")
_DETAIL_ID = re.compile(r"(?:[0-9a-fA-F]{32}(?:_p)?|[1-9][0-9]*_p)\Z")
_ROW_NUMBER = re.compile(r"[1-9][0-9]*\Z")
_FOOTER = re.compile(
    r"当前第\s*([0-9]+)\s*页\s*[,，]\s*共\s*([0-9]+)\s*页\s*[,，]\s*共\s*([0-9]+)\s*条记录"
)


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


def _check_url(value: Any) -> str:
    if not isinstance(value, str):
        raise CaptureError("来源 URL 必须是字符串")
    url = value.strip()
    if not url or any(ch.isspace() for ch in url):
        raise CaptureError("来源 URL 为空或含空白")
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise CaptureError("来源 URL 必须是 https")
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        raise CaptureError("来源 URL 不得包含用户信息")
    host = (parsed.hostname or "").lower()
    if host not in _PUBLIC_HOSTS:
        raise CaptureError(f"来源 URL 主机不是公开登记平台：{host or '空'}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise CaptureError("来源 URL 端口非法") from exc
    if port not in _ALLOWED_PORTS:
        raise CaptureError("来源 URL 端口必须是 443")
    if parsed.path != _LIST_PATH:
        raise CaptureError("来源 URL 路径必须是检索列表页")
    if parsed.fragment:
        raise CaptureError("来源 URL 不得包含片段")
    if parse_qsl(parsed.query,keep_blank_values=True) != parse_qsl(urlsplit(public_url(url)).query,keep_blank_values=True):
        raise CaptureError('来源 URL 不得包含凭据参数')
    return url


def _parse_pagination(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise CaptureError("分页文本必须是字符串")
    found = {tuple(int(part) for part in match.groups()) for match in _FOOTER.finditer(value)}
    if not found:
        raise CaptureError("分页页脚缺失：不能当作零结果")
    if len(found) > 1:
        raise CaptureError(f"分页元数据互相矛盾：{sorted(found)}")
    current, total_pages, total_records = found.pop()
    if total_records == 0:
        if total_pages > 1:
            raise CaptureError("分页元数据矛盾：零记录却有多个页面")
        if current > 1:
            raise CaptureError("分页元数据矛盾：零记录却当前页大于 1")
        return current, total_pages, total_records
    if total_pages == 0:
        raise CaptureError("分页元数据矛盾：有记录却零页面")
    if total_records < total_pages:
        raise CaptureError("分页元数据矛盾：记录数少于页数")
    if not 1 <= current <= total_pages:
        raise CaptureError("分页元数据矛盾：当前页超出总页数")
    return current, total_pages, total_records


def _check_headers(value: Any) -> None:
    if not isinstance(value, list) or len(value) != len(COLUMNS):
        raise CaptureError(f"表头必须是 {len(COLUMNS)} 列")
    if any(not isinstance(item, str) for item in value):
        raise CaptureError("表头每列必须是字符串")
    if tuple(_norm(item) for item in value) != COLUMNS:
        raise CaptureError("表头不是当前六列语义顺序")


def _check_query(actual: Any, expected: Any) -> str:
    if not isinstance(expected, str):
        raise CaptureError("期望查询词必须是字符串")
    expected_norm = _norm(expected)
    if not expected_norm:
        raise CaptureError("期望查询词为空")
    if not isinstance(actual, str):
        raise CaptureError("捕获查询词必须是字符串")
    if _norm(actual) != expected_norm:
        raise CaptureError(f"查询词不一致：捕获为 {actual!r}，期望为 {expected!r}")
    return expected_norm


def _parse_row(value: Any, *, source_url: str) -> dict[str, Any]:
    row = _require_dict(value, "rows[]")
    _require_exact_keys(row, _ROW_KEYS, "rows[]")
    cells = row["cells"]
    if not isinstance(cells, list) or len(cells) != len(COLUMNS):
        raise CaptureError(f"单元格必须是 {len(COLUMNS)} 列")
    if any(not isinstance(cell, str) for cell in cells):
        raise CaptureError("单元格必须是字符串")
    number_text = cells[0].strip()
    if not _ROW_NUMBER.match(number_text):
        raise CaptureError(f"序号不是正整数：{cells[0]!r}")
    ctr = cells[1].strip()
    if not _CTR.match(ctr):
        raise CaptureError(f"登记号不是 CTR+8 位数字：{cells[1]!r}")
    drug_name = cells[3].strip()
    if not drug_name:
        raise CaptureError("药物名称为空")
    detail_id = row["detail_id"]
    if not isinstance(detail_id, str) or not _DETAIL_ID.match(detail_id):
        raise CaptureError(f"detail_id 不是已观察的公开记录标识：{detail_id!r}")
    return {
        "ctr": ctr,
        "drug_name": drug_name,
        "status_text": cells[2].strip(),
        "indication": cells[4].strip(),
        "title": cells[5].strip(),
        "detail_id": detail_id,
        "source_url": source_url,
        "row_number": int(number_text),
        "raw_cells": list(cells),
    }


def parse_page(page: dict[str, Any], *, query: str) -> dict[str, Any]:
    """校验一页捕获并返回规范化行；不判断任何医学或资格结论。"""
    page_obj = _require_dict(page, "page")
    _require_exact_keys(page_obj, _PAGE_KEYS, "page")
    url = _check_url(page_obj["url"])
    query_norm = _check_query(page_obj["query"], query)
    _check_headers(page_obj["headers"])
    current, total_pages, total_records = _parse_pagination(page_obj["pagination_text"])
    rows = page_obj["rows"]
    if not isinstance(rows, list):
        raise CaptureError("rows 必须是列表")
    if total_records == 0 and rows:
        raise CaptureError("零记录页不得包含行")
    if total_records > 0 and not rows:
        raise CaptureError("正数记录页不得为空")
    if len(rows) > total_records:
        raise CaptureError(f"行数 {len(rows)} 超出总记录数 {total_records}")
    results = [_parse_row(item, source_url=url) for item in rows]
    return {"page": current, "total_pages": total_pages, "total_records": total_records,
            "query": query_norm, "results": results}


def _check_unique(rows: list[dict[str, Any]]) -> None:
    seen_ctr: set[str] = set()
    seen_detail: set[str] = set()
    for row in rows:
        if row["ctr"] in seen_ctr:
            raise CaptureError(f"登记号重复：{row['ctr']}")
        seen_ctr.add(row["ctr"])
        detail_key = row["detail_id"].lower()
        if detail_key in seen_detail:
            raise CaptureError(f"detail_id 重复：{row['detail_id']}")
        seen_detail.add(detail_key)


def _check_page_rows(item: dict[str, Any], page_size: int, total_pages: int, total_records: int) -> None:
    count = len(item["results"])
    number = item["page"]
    if count == 0:
        raise CaptureError(f"正数记录捕获不得包含空页：第 {number} 页")
    if number < total_pages:
        if count != page_size:
            raise CaptureError(f"第 {number} 页行数 {count} 与首页页长 {page_size} 不一致")
        return
    expected_last = total_records - (total_pages - 1) * page_size
    if not 0 < expected_last <= page_size:
        raise CaptureError(f"末页应有行数 {expected_last} 与页长 {page_size} 矛盾")
    if count != expected_last:
        raise CaptureError(f"末页行数 {count} 与声明总数要求 {expected_last} 不符")


def _result(ordered: list[dict[str, Any]], query_norm: str, total_pages: int, total_records: int,
            complete: bool, pending: list[int]) -> dict[str, Any]:
    results = [{**row, "page": item["page"]} for item in ordered for row in item["results"]]
    return {"query": query_norm, "total_pages": total_pages, "total_records": total_records,
            "pages_read": [item["page"] for item in ordered], "complete": complete,
            "pending_pages": pending, "results": results}


def parse_capture(pages: list[dict[str, Any]], *, query: str, allow_partial: bool = False) -> dict[str, Any]:
    """校验整份捕获：页/查询/总数一致、无重复、完整或显式不完整。"""
    if not isinstance(allow_partial, bool):
        raise CaptureError("allow_partial 必须是布尔值")
    if not isinstance(pages, list):
        raise CaptureError("pages 必须是列表")
    if not pages:
        raise CaptureError("捕获至少需要一页")
    parsed = [parse_page(page, query=query) for page in pages]
    query_norm = parsed[0]["query"]
    total_pages = parsed[0]["total_pages"]
    total_records = parsed[0]["total_records"]
    seen_pages: set[int] = set()
    for item in parsed:
        if item["total_pages"] != total_pages or item["total_records"] != total_records:
            raise CaptureError("各页分页总数不一致")
        if item["page"] in seen_pages:
            raise CaptureError(f"第 {item['page']} 页重复出现")
        seen_pages.add(item["page"])
    ordered = sorted(parsed, key=lambda item: item["page"])
    if total_records == 0:
        if len(ordered) != 1:
            raise CaptureError("零记录捕获只能包含一页")
        return _result(ordered, query_norm, total_pages, total_records, True, [])
    numbers = [item["page"] for item in ordered]
    if numbers != list(range(1, len(numbers) + 1)):
        raise CaptureError(f"页号必须是 1..k 的连续前缀：{numbers}")
    page_size = len(ordered[0]["results"])
    for item in ordered:
        _check_page_rows(item, page_size, total_pages, total_records)
    rows = [row for item in ordered for row in item["results"]]
    if len(rows) > total_records:
        raise CaptureError(f"记录数 {len(rows)} 超出声明总数 {total_records}")
    _check_unique(rows)
    full = len(ordered) == total_pages
    if full and len(rows) != total_records:
        raise CaptureError(f"全部页行数 {len(rows)} 与声明总数 {total_records} 不符")
    if not full and not allow_partial:
        raise CaptureError(f"捕获不完整：已读 {len(ordered)}/{total_pages} 页")
    pending = [] if full else list(range(len(ordered) + 1, total_pages + 1))
    return _result(ordered, query_norm, total_pages, total_records, full, pending)
