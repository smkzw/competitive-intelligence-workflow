"""DeepSeek主抽取 → 异构GLM读取原文核对、纠错、补漏 → 确定性来源校验。

核对者可见抽取候选，不宣称盲审。历史dual_agreed/arbitrated仅兼容读取。
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, ValidationError

from ciw.verify.llm import Backend, check_heterogeneous, parse_json
from ciw.verify.quote import check_quote

PROMPT_VERSION = "source-review-v3.1"
_FORMAT_ERRORS = {"JSONDecodeError", "ValueError", "KeyError"}

SYSTEM_EXTRACT = (
    "你是临床试验与药物研发信息的抽取器。只依据用户给出的原文，按要求的 JSON 结构输出。"
    "每一条结果必须附 quote 字段：从原文逐字复制、能直接支持该条所有数值和关键字段的连续片段。"
    '原文没有的信息不要输出，不要推测，不要补全。输出必须是 JSON 对象：{"items": [...]}。'
    "items中的每条必须直接包含实际数据字段（包括quote），不要复述JSON Schema，"
    "不要使用properties、type、required、description包装数据。找不到符合任务的信息时返回items空数组。"
)
SYSTEM_VERIFY = (
    "你是临床来源核对者。原文是唯一依据；候选可能错误或遗漏，不能当成证据。"
    "阅读全文，逐字段核对候选，纠正错误并主动补齐遗漏。"
    "返回核对后的完整items数组，每项直接符合给定Schema，不返回choice或Schema本身。"
    "每项quote须逐字引用支持其字段的连续原文。原文没有的信息留空，不推测。"
    '输出JSON对象：{"items": [...]}；确实无可用信息才返回空数组。'
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
    item_check: Callable[[dict[str, Any]], tuple[bool, str]] | None = None
    distinct_quotes_conflict: bool = False


class CrosscheckFailed(RuntimeError):
    """A required model call failed; keep its receipt rather than treating it as no information."""

    def __init__(self, message, *, calls=()):
        super().__init__(message)
        self.calls = list(calls)


@dataclass
class CheckedItem:
    item: dict[str, Any]
    status: str  # verified / needs_review
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


def _extract(
    backend: Backend, task: ExtractionTask, candidates=None, errors=None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    call: dict[str, Any] = {
        "role": "extract" if candidates is None else "verify", "family": backend.family, "model": backend.model
    }
    try:
        system, user = SYSTEM_EXTRACT, _user_prompt(task)
        if candidates is not None:
            system = SYSTEM_VERIFY
            user += "\n待核候选（仅供查错，不是来源）：\n" + json.dumps(candidates, ensure_ascii=False)
            if errors:
                user += ("\n确定性校验错误：" + json.dumps(errors, ensure_ascii=False)
                         + "\n本次仅修复所列候选，逐字复制真实连续原文；无法支持的日期留空。不要新增其他身份。")
        if candidates is None and errors:
            user += ("\n上次主抽取答复为空或JSON结构无效：" + json.dumps(errors, ensure_ascii=False)
                     + "\n仅依据上述原文重新输出合法items对象，正确转义引号；不返回分析过程或Schema。")
        payload = parse_json(backend.chat(system, user))
        call.update(getattr(backend, "receipt", {}))
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("模型输出缺少items数组")
        raw_items = payload["items"]
        items = []
        for raw in raw_items:
            try:
                items.append(task.item_model.model_validate(raw).model_dump())
            except ValidationError:
                call.setdefault("invalid_items", 0)
                call["invalid_items"] += 1
        call["n_items"] = len(items)
        if raw_items and not items:
            raise ValueError("所有抽取条目均未通过schema")
        return items, call
    except (ValueError, KeyError, OSError) as exc:  # 网络、JSON 或结构错误：这一路没有结果，不当“无信息”
        call.update(getattr(backend, "receipt", {}))
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
        if not 1 <= month <= 12:
            return False
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
        if m.group(3):
            day, year = int(m.group(3)), int(m.group(1))
            try:
                date(year, month, day)
            except ValueError:
                return False
            numeric = rf"(?<!\d){year}\s*[-/.年]\s*0?{month}\s*[-/.月]\s*0?{day}(?!\d)"
            month_name = rf"(?:{en}|{en[:3]}\.?)"
            english = rf"\b(?:{month_name}\s+0?{day}(?!\d),?\s+{year}|0?{day}\s+{month_name}\s+{year})\b"
            if not (re.search(numeric, q) or re.search(english, q, re.I)):
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
    if task.item_check is not None:
        return task.item_check(item)
    return True, ""


def _key(task: ExtractionTask, item: dict[str, Any]) -> tuple[str, ...]:
    if task.key_fn is not None:
        return task.key_fn(item)
    return tuple(_norm_text(item.get(f, "")) for f in task.key_fields)


def _same(task: ExtractionTask, a: dict[str, Any], b: dict[str, Any]) -> bool:
    return all(_norm_value(a.get(f)) == _norm_value(b.get(f)) for f in task.value_fields)


def _checked_items(task, items):
    out = {}
    for raw in items:
        it = dict(raw)
        ok, reason = _quote_ok(task, it)
        it["_quote_ok"], it["_quote_reason"] = ok, reason
        key = _key(task, it)
        previous = out.get(key)
        if previous is not None and (not _same(task, previous, it) or (
                task.distinct_quotes_conflict and previous["_quote_ok"] and ok
                and _norm_text(previous[task.quote_field]) != _norm_text(it[task.quote_field]))):
            previous["_duplicate_conflict"] = True
        elif previous is None or (not previous["_quote_ok"] and ok):
            out[key] = it
    return out


def _repair_review(task, backend, b_by):
    invalid = {key: it for key, it in b_by.items() if not it["_quote_ok"] or it.get("_duplicate_conflict")}
    if not invalid:
        return []
    errors = [{"key": key, "error": it["_quote_reason"] or "相同身份存在冲突值"} for key, it in invalid.items()]
    repaired, call = _extract(backend, task, [_clean(it) for it in invalid.values()], errors)
    call["role"] = "verify_repair"
    call["requested_keys"] = [list(key) for key in sorted(invalid)]
    if not call.get("error"):
        fixed = _checked_items(task, repaired)
        call["unrequested_items"] = len(set(fixed) - set(invalid))
        for key in invalid:
            if key in fixed:
                b_by[key] = fixed[key]
    return [call]


def extract_candidates(task: ExtractionTask, roles: dict[str, Backend]):
    check_heterogeneous(roles)
    items, call = _extract(roles["extractor_a"], task)
    if call.get("error") in _FORMAT_ERRORS:
        items, correction = _extract(roles["extractor_a"], task, errors=[{"error": call["error"]}])
        correction["format_repair"] = True
        if correction.get("error"):
            raise CrosscheckFailed("主抽取格式纠正失败：" + correction["error"], calls=[call, correction])
        correction["previous_format_call"] = call
        call = correction
    elif call.get("error"):
        raise CrosscheckFailed("主抽取失败：" + call["error"], calls=[call])
    return items, call


def crosscheck(task: ExtractionTask, roles: dict[str, Backend]) -> list[CheckedItem]:
    a_items, a_call = extract_candidates(task, roles)
    return review_candidates(task, roles["verifier"], a_items, a_call)


def review_candidates(task, verifier, a_items, a_call):
    """Review retained candidates with the same source guards and bounded repairs."""
    if verifier.family == a_call["family"]:
        raise ValueError("主抽取和来源核对必须来自两个不同模型家族")
    extract_calls = [a_call["previous_format_call"]] if a_call.get("previous_format_call") else []
    extract_calls.append({k: v for k, v in a_call.items() if k != "previous_format_call"})
    b_items, b_call = _extract(verifier, task, a_items)
    format_calls = []
    if b_call.get("error") in _FORMAT_ERRORS:
        b_items, correction = _extract(verifier, task, a_items,
                                      [{"error": "上次核对输出JSON格式或items结构无效，请返回合法JSON，正确转义引号"}])
        correction["role"] = "verify_format_repair"
        format_calls.append(correction)
        if correction.get("error"):
            raise CrosscheckFailed("来源核对格式纠正失败：" + correction["error"],
                                   calls=[*extract_calls, b_call, correction])
    elif b_call.get("error"):
        raise CrosscheckFailed("来源核对失败：" + b_call["error"], calls=[*extract_calls, b_call])
    a_by, b_by = _checked_items(task, a_items), _checked_items(task, b_items)
    repairs = [] if format_calls else _repair_review(task, verifier, b_by)
    calls = [*extract_calls, b_call, *format_calls, *repairs]
    results = []
    for key in sorted(set(a_by) | set(b_by)):
        a, b = a_by.get(key), b_by.get(key)
        chosen = b or a
        status, note = "verified", "原文核对通过"
        if b is None:
            status, note = "needs_review", "主抽取条目未被核对者确认"
        elif b.get("_duplicate_conflict"):
            status, note = "needs_review", "核对者对同一身份返回冲突值"
        elif not b["_quote_ok"]:
            status, note = "needs_review", "核对结果未通过来源校验：" + b["_quote_reason"]
        elif a is None:
            note = "核对者从原文补充遗漏"
        elif not _same(task, a, b) or a.get("_duplicate_conflict"):
            note = "核对者依据原文修正候选"
        results.append(CheckedItem(_clean(chosen), status, key, calls, note))
    return results


def _clean(item: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in (item or {}).items() if not k.startswith("_")}


def retained_verified(ws, task: ExtractionTask) -> tuple[list[CheckedItem], bool]:
    """Read existing source/task-bound decisions with their actual verifier response; make no calls."""
    by_key, incomplete = {}, False
    for record in ws.verifications().values():
        if record.get("task") != task.task_id or record.get("source_id") != task.source_id:
            continue
        if record.get("status") != "verified":
            incomplete = True
            continue
        try:
            item = task.item_model.model_validate(record.get("item")).model_dump()
        except (ValueError, TypeError):
            incomplete = True
            continue
        if not _quote_ok(task, item)[0] or not _retained_verifier(ws, task, record, item):
            incomplete = True
            continue
        key = _key(task, item)
        bucket = by_key.setdefault(key, [])
        if not any(checked.item == item for checked in bucket):
            bucket.append(CheckedItem(item, "verified", key, record.get("calls", []), record.get("note", "")))
    out = []
    for bucket in by_key.values():
        if len(bucket) != 1:
            incomplete = True
        else:
            out.extend(bucket)
    return out, incomplete


def _retained_verifier(ws, task, record, item):
    calls = record.get("calls", [])
    extracts = [c for c in calls if c.get("role") == "extract" and not c.get("error")]
    reviews = [c for c in calls if c.get("role") in {"verify", "verify_repair", "verify_format_repair"}]
    if not extracts or len({c.get("family") for c in calls if c.get("family")}) != 2:
        return False
    for call in reversed(reviews):
        if (call.get("role") == "verify_repair" and "requested_keys" in call
                and list(_key(task, item)) not in call["requested_keys"]):
            continue  # An unsolicited repair item was never an accepted replacement.
        if (call.get("error") or not call.get("n_items") or not call.get("response_id")
                or call.get("family") == extracts[0].get("family")):
            continue
        with ws.db() as con:
            responses = con.execute("SELECT response, metadata FROM llm_cache WHERE family=? AND model=?",
                                    (call.get("family"), call.get("model"))).fetchall()
        matches = []
        for text, metadata in responses:
            try:
                if json.loads(metadata or "{}").get("response_id") != call["response_id"]:
                    continue
                candidates = [task.item_model.model_validate(raw).model_dump() for raw in parse_json(text)["items"]]
                chosen = _checked_items(task, candidates).get(_key(task, item))
                if chosen is not None:
                    matches.append(not chosen.get("_duplicate_conflict") and _clean(chosen) == item)
            except (ValueError, TypeError, KeyError, AttributeError):
                return False
        if matches:
            return matches == [True]  # A later relevant B revision cannot fall back to an earlier item.
    return False


def retained_candidate(ws, task, record, item):
    """Provenance for a pending candidate, never approval or scientific equivalence."""
    if record.get("task") != task.task_id or record.get("source_id") != task.source_id:
        return False
    for call in reversed(record.get("calls", [])):
        if call.get("error") or not call.get("response_id") or not call.get("n_items"):
            continue
        with ws.db() as con:
            responses = con.execute("SELECT response, metadata FROM llm_cache WHERE family=? AND model=?",
                                    (call.get("family"), call.get("model"))).fetchall()
        for text, metadata in responses:
            try:
                if json.loads(metadata or "{}").get("response_id") != call["response_id"]:
                    continue
                if any(task.item_model.model_validate(raw).model_dump() == item for raw in parse_json(text)["items"]):
                    return True
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
    return False
