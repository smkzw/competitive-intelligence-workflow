"""登记详情页捕获的确定性校验。移植自 archive/ciw2:rebaseline-v2/src/ciw2/sources/china_detail.py（只取解析部分）。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from ciw.sources.cde.listing import valid_detail_id

BASIC = {"登记号", "试验状态", "首次公示信息日期", "申请人名称"}


def _rows(value: Any) -> list[list[str]]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(r, list) or not r or any(not isinstance(c, str) for c in r) for r in value)
    ):
        raise ValueError("登记详情缺少有效原始单元格")
    return value


def _fields(rows: list[list[str]], labels: set[str]) -> dict[str, str]:
    found = {}
    for row in rows:
        if len(row) % 2:
            raise ValueError("登记详情标签与值不是配对单元格")
        for label, value in zip(row[::2], row[1::2], strict=True):
            key = label.strip()
            if key in labels:
                if key in found:
                    raise ValueError("登记详情身份字段重复，不能任取一项")
                found[key] = value
    return found


def _tables(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("登记详情无临床信息表")
    for table in value:
        if not isinstance(table, dict) or set(table) != {"rows", "nested"} or not isinstance(table["nested"], list):
            raise ValueError("登记详情表结构不符")
        rows = _rows(table["rows"])
        seen = set()
        for nested in table["nested"]:
            if not isinstance(nested, dict) or set(nested) != {"row", "column", "rows"}:
                raise ValueError("登记详情内表结构不符")
            r, c = nested["row"], nested["column"]
            if (
                type(r) is not int
                or type(c) is not int
                or not 0 <= r < len(rows)
                or not 0 <= c < len(rows[r])
                or (r, c) in seen
            ):
                raise ValueError("登记详情内表定位不符")
            seen.add((r, c))
            content = "\n".join("\t".join(row) for row in _rows(nested["rows"]))
            if " ".join(content.split()) != " ".join(rows[r][c].split()):
                raise ValueError("登记详情内表与原始单元格不一致")
    return value


def parse_capture(raw: dict, *, ctr: str, detail_id: str) -> dict[str, Any]:
    expected = {"url", "title", "section", "registry_id", "detail_id", "basic", "tables", "observed_at"}
    if not isinstance(raw, dict) or set(raw) != expected:
        raise ValueError("登记详情捕获结构不符")
    if not re.fullmatch(r"CTR[0-9]{8}", ctr) or not valid_detail_id(detail_id):
        raise ValueError("登记详情请求标识不合法")
    u = urlsplit(raw["url"])
    if (
        u.scheme != "https"
        or u.hostname not in {"www.chinadrugtrials.org.cn", "chinadrugtrials.org.cn"}
        or u.port not in {None, 443}
        or u.username
        or u.password
        or u.query
        or u.fragment
        or u.path != "/clinicaltrials.searchlistdetail.dhtml"
    ):
        raise ValueError("登记详情不是无会话参数的官方页面")
    if (
        raw["section"] != "trial_detail"
        or raw["registry_id"] != ctr
        or raw["detail_id"] != detail_id
        or raw["title"] != ctr + "详细信息"
    ):
        raise ValueError("登记详情与所请求试验不符")
    if not isinstance(raw["observed_at"], str) or datetime.fromisoformat(raw["observed_at"]).tzinfo is None:
        raise ValueError("登记详情无有效实际获取时间")
    basic = _fields(_rows(raw["basic"]), BASIC)
    tables = _tables(raw["tables"])
    fields = _fields(
        [r for t in tables for r in t["rows"]], {"登记号", "药物名称", "适应症", "试验专业题目", "试验分期"}
    )
    labels = {r[0].strip() for t in tables for r in t["rows"]}
    if (
        set(basic) != BASIC
        or basic["登记号"] != ctr
        or fields.get("登记号") != ctr
        or not fields.get("药物名称")
        or not fields.get("适应症")
        or "试验分期" not in fields
        or not {"入选标准", "排除标准"} <= labels
    ):
        raise ValueError("登记详情缺少完整身份/设计/入排原文块")
    text = "\n".join("\t".join(row) for row in [*raw["basic"], *(r for t in tables for r in t["rows"])])
    return {
        "registry_id": ctr,
        "detail_id": detail_id,
        "applicant": basic["申请人名称"],
        "registered_drug_name": fields["药物名称"],
        "indication": fields["适应症"],
        "title": fields.get("试验专业题目"),
        "basic": raw["basic"],
        "tables": tables,
        "source_text": text,
    }
