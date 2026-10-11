"""Source-preserving display-component projection for exact reported n (%) cells.

One bounded helper for the existing B view: it splits a publication cell only
when the source itself declares it as an n (%) composite
(``raw_value_type=composite_count_and_percent`` with
``value_role=reported_measure`` and an explicit ``n (%)`` source unit). The
percentage is the independently reported cell token — never recomputed from a
column header N, so a rounded n/N difference stays as printed — and raw token
spans let audit prove both source components. Any other atom, and any
conflicting or malformed cell, stays original/raw/unresolved; no denominator,
arm relation, source acceptance or fact version is produced here.
"""

from __future__ import annotations

import re
from typing import Any

from ci_workflow.application.source_research_service import ResearchFact

_PROJECTED = "projected"
_UNRESOLVED = "unresolved"

# Only an explicit trailing "n (%)" segment declares the composite form; a
# percent word or a bare "(%)" never authorizes the split.
_N_PERCENT_UNIT = re.compile(r"(?:^|,)n\(%\)$")
_COUNT_HEAD = re.compile(r"\s*(?P<count>[0-9]+)\s*\(")
_PERCENT_TOKEN = re.compile(r"\s*(?P<percent>[0-9]+(?:\.[0-9]+)?)\s*")


def publication_value_components(fact: ResearchFact) -> dict[str, Any]:
    """Project one immutable fact into display candidates plus its exact payload.

    Returns the fact's full original payload (identities, locator, clause and
    result contexts, ``raw_value``/``normalized_value`` verbatim) under its own
    keys, plus a ``projection`` result with ``state``, ``reason`` when
    unresolved, and components each carrying ``kind``, ``raw_token``,
    ``token_span`` into ``original_text``, numeric ``value`` and ``unit``.
    """
    return {**fact.model_dump(mode="json"), "projection": _project_cell(fact)}


def _unresolved(reason: str) -> dict[str, Any]:
    return {
        "state": _UNRESOLVED, "reason": reason,
        "span_basis": "original_text", "components": (),
    }


def _project_cell(fact: ResearchFact) -> dict[str, Any]:
    context = fact.result_context
    if context is None:
        return _unresolved("结果上下文缺失，不能拆分复合单元格")
    if context.value_role != "reported_measure":
        return _unresolved(f"数值角色为 {context.value_role}，不是报告测度；不拆分")
    if context.raw_value_type != "composite_count_and_percent":
        return _unresolved(
            f"原始值形式为 {context.raw_value_type or '未注明'}，"
            "不是明确的复合 n (%) 单元格；保留原载荷"
        )
    if fact.disclosure_state not in ("reported_value", "reported_zero"):
        return _unresolved(f"披露状态为 {fact.disclosure_state}，不是明确报告值")
    if _N_PERCENT_UNIT.search("".join(context.source_unit.split()).casefold()) is None:
        return _unresolved(f"来源单位未明确声明 n (%) 复合形式：{context.source_unit}")
    if fact.raw_value is not None and fact.raw_value.strip() != fact.original_text.strip():
        return _unresolved("raw_value 与绑定原文冲突；保留原载荷不拆分")
    return _split_composite_cell(fact.original_text)


def _split_composite_cell(text: str) -> dict[str, Any]:
    head = _COUNT_HEAD.match(text)
    if head is None:
        return _unresolved("单元格开头不是纯数字计数；不拆分")
    close = text.find(")", head.end())
    if close < 0:
        return _unresolved("复合单元格缺少右括号；不拆分")
    percent = _PERCENT_TOKEN.fullmatch(text[head.end():close])
    if percent is None:
        return _unresolved("括号内百分数不是纯数字（阈值、区间或标记）；不拆分")
    if text[close + 1:].strip():
        return _unresolved("括号后存在尾注或标记；不拆分")
    percent_value = float(percent.group("percent"))
    if not 0.0 <= percent_value <= 100.0:
        return _unresolved(f"括号内百分数超出 0–100 范围：{percent.group('percent')}")
    return {
        "state": _PROJECTED,
        "reason": None,
        "span_basis": "original_text",
        "components": (
            {
                "kind": "count", "raw_token": head.group("count"),
                "token_span": list(head.span("count")),
                "value": int(head.group("count")), "unit": "n",
            },
            {
                "kind": "percent", "raw_token": percent.group("percent"),
                "token_span": [head.end() + percent.start("percent"),
                               head.end() + percent.end("percent")],
                "value": percent_value, "unit": "%",
            },
        ),
    }
