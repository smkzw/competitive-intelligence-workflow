"""异构模型交叉核对。

两个不同家族的模型独立抽取同一份原文 → 每条结果先过原文引语校验 → 按身份键配对、逐字段确定性比对：
- 两边一致且引语都在原文中           → dual_agreed
- 不一致、或只有一边抽到             → 第三家族仲裁（看到原文与两份候选，只能选 A/B/都不对）
- 仲裁选中且所选候选引语校验通过     → arbitrated
- 其余                                → needs_review（进入待核队列，不进图表数值轴）
模型自报置信度不参与判定。
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from ciw.verify.llm import Backend, check_heterogeneous, parse_json
from ciw.verify.quote import check_quote

PROMPT_VERSION = "crosscheck-v1"

SYSTEM_EXTRACT = (
    "你是临床试验与药物研发信息的抽取器。只依据用户给出的原文，按要求的 JSON 结构输出。"
    "每一条结果必须附 quote 字段：从原文逐字复制、能直接支持该条所有数值和关键字段的连续片段。"
    '原文没有的信息不要输出，不要推测，不要补全。输出必须是 JSON 对象：{"items": [...]}。'
)
SYSTEM_ARBITER = (
    "你是独立核对员。给你原文和两个抽取器对同一条信息的候选（A 与 B，可能其中一个为空）。"
    '逐字段对照原文，判断哪个候选完全被原文支持。只能回答 JSON：{"choice": "A"|"B"|"neither", '
    '"reason": "一句话"}。两个都对且等价时选 A。'
)


@dataclass
class ExtractionTask:
    task_id: str
    source_id: str
    source_text: str
    instruction: str
    item_model: type[BaseModel]
    key_fields: tuple[str, ...]
    value_fields: tuple[str, ...]
    numeric_fields: tuple[str, ...] = ()
    date_fields: tuple[str, ...] = ()  # 日期必须能在引语里找到（年份和月份）
    quote_field: str = "quote"
    key_fn: Callable[[dict[str, Any]], tuple[str, ...]] | None = None  # 跨模型配对键（例如解析后的产品 ID）


class CrosscheckFailed(RuntimeError):
    """两个抽取器都没有返回可用结果：这不是“没有信息”，调用方必须记为失败。"""


@dataclass
class CheckedItem:
    item: dict[str, Any]
    status: str  # dual_agreed / arbitrated / needs_review
    key: tuple[str, ...]
    calls: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""


def task_id_for(source_sha: str, schema_name: str, instruction: str) -> str:
    raw = f"{PROMPT_VERSION}|{schema_name}|{source_sha}|{instruction}"
    return "xt_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _norm_text(v: Any) -> str:
    s = unicodedata.normalize("NFKC", str(v)).casefold()
    return re.sub(r"\s+", " ", s).strip(" .;,，。；")


def _norm_value(v: Any) -> Any:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    s = _norm_text(v)
    try:
        return round(float(s.replace(",", "")), 6)
    except ValueError:
        return s


def _user_prompt(task: ExtractionTask) -> str:
    schema = json.dumps(task.item_model.model_json_schema(), ensure_ascii=False)
    return f"任务：{task.instruction}\n\n每条 item 的 JSON Schema：{schema}\n\n原文：\n<<<\n{task.source_text}\n>>>"


def _extract(backend: Backend, task: ExtractionTask) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    call: dict[str, Any] = {"role": "extract", "family": backend.family, "model": backend.model}
    try:
        payload = parse_json(backend.chat(SYSTEM_EXTRACT, _user_prompt(task)))
        raw_items = payload.get("items", []) if isinstance(payload, dict) else []
        items = []
        for raw in raw_items:
            try:
                items.append(task.item_model.model_validate(raw).model_dump())
            except ValidationError:
                call.setdefault("invalid_items", 0)
                call["invalid_items"] += 1
        call["n_items"] = len(items)
        return items, call
    except (ValueError, KeyError, OSError) as exc:  # 网络、JSON 或结构错误：这一路没有结果，不当“无信息”
        call["error"] = type(exc).__name__
        return [], call


def _date_in_quote(value: str, quote: str) -> bool:
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", value.strip())
    if not m:
        return False
    q = unicodedata.normalize("NFKC", quote)
    if m.group(1) not in q:
        return False
    if m.group(2):
        month = int(m.group(2))
        en = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ][month - 1]
        if not (re.search(rf"(?<!\d)0?{month}\s*月|[-/.]0?{month}(?!\d)", q) or en[:3] in q.lower()):
            return False
    return True


def _quote_ok(task: ExtractionTask, item: dict[str, Any]) -> tuple[bool, str]:
    quote = item.get(task.quote_field) or ""
    numbers = [item[f] for f in task.numeric_fields if item.get(f) is not None]
    check = check_quote(task.source_text, quote, numbers or None)
    if not check.ok:
        return False, check.reason
    for f in task.date_fields:
        if item.get(f) and not _date_in_quote(str(item[f]), quote):
            return False, f"{f}={item[f]} 在引语中找不到"
    return True, ""


def _key(task: ExtractionTask, item: dict[str, Any]) -> tuple[str, ...]:
    if task.key_fn is not None:
        return task.key_fn(item)
    return tuple(_norm_text(item.get(f, "")) for f in task.key_fields)


def _same(task: ExtractionTask, a: dict[str, Any], b: dict[str, Any]) -> bool:
    return all(_norm_value(a.get(f)) == _norm_value(b.get(f)) for f in task.value_fields)


def _arbitrate(
    arbiter: Backend, task: ExtractionTask, a: dict[str, Any] | None, b: dict[str, Any] | None
) -> tuple[str, dict[str, Any]]:
    call: dict[str, Any] = {"role": "arbitrate", "family": arbiter.family, "model": arbiter.model}
    user = (
        f"任务：{task.instruction}\n\n候选 A：{json.dumps(a, ensure_ascii=False)}\n"
        f"候选 B：{json.dumps(b, ensure_ascii=False)}\n\n原文：\n<<<\n{task.source_text}\n>>>"
    )
    try:
        payload = parse_json(arbiter.chat(SYSTEM_ARBITER, user))
        choice = str(payload.get("choice", "neither")).strip()
        call["choice"] = choice if choice in ("A", "B", "neither") else "neither"
        call["reason"] = str(payload.get("reason", ""))[:200]
    except (ValueError, KeyError, OSError, AttributeError) as exc:
        call["choice"], call["error"] = "neither", type(exc).__name__
    return call["choice"], call


def crosscheck(task: ExtractionTask, roles: dict[str, Backend]) -> list[CheckedItem]:
    check_heterogeneous(roles)
    a_items, a_call = _extract(roles["extractor_a"], task)
    b_items, b_call = _extract(roles["extractor_b"], task)
    base_calls = [a_call, b_call]
    if a_call.get("error") and b_call.get("error"):
        raise CrosscheckFailed(f"两个抽取器均失败：{a_call['error']} / {b_call['error']}")

    def valid(items: list[dict[str, Any]]) -> dict[tuple[str, ...], dict[str, Any]]:
        out: dict[tuple[str, ...], dict[str, Any]] = {}
        for it in items:
            ok, reason = _quote_ok(task, it)
            it["_quote_ok"], it["_quote_reason"] = ok, reason
            out.setdefault(_key(task, it), it)  # 同键重复只取首个；第二个不覆盖
        return out

    a_by, b_by = valid(a_items), valid(b_items)
    results: list[CheckedItem] = []
    for key in sorted(set(a_by) | set(b_by)):
        a, b = a_by.get(key), b_by.get(key)
        calls = list(base_calls)
        if a and b and a["_quote_ok"] and b["_quote_ok"] and _same(task, a, b):
            results.append(CheckedItem(item=_clean(a), status="dual_agreed", key=key, calls=calls))
            continue
        single = "（仅一个抽取器给出，经仲裁）" if not (a and b) else ""
        choice, call = _arbitrate(roles["arbiter"], task, _clean(a) if a else None, _clean(b) if b else None)
        calls.append(call)
        chosen = {"A": a, "B": b}.get(choice)
        if chosen is not None and chosen["_quote_ok"]:
            results.append(
                CheckedItem(
                    item=_clean(chosen), status="arbitrated", key=key, calls=calls, note=f"仲裁选择 {choice}{single}"
                )
            )
        else:
            fallback = a or b
            note = "仲裁未选中可校验的候选" if chosen is None else f"所选候选引语未通过：{chosen['_quote_reason']}"
            results.append(CheckedItem(item=_clean(fallback), status="needs_review", key=key, calls=calls, note=note))
    return results


def _clean(item: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in (item or {}).items() if not k.startswith("_")}
