"""跨模块安全分母 crosswalk（独立审阅 R03 / 验收 SCI03、SCI04）。

合同：
- 每条目绑定模块、原始组 ID、归一化标题（含期别标记）、期别、分母统计
  对象（serious/other/deaths/person_time）与数值；
- 标题匹配只生成候选；期别不一致或候选值冲突时返回"未知"，不得借用、
  不得 first-wins、不得以单组回退吞掉冲突；
- 人时（person_time）与人数是不同量纲，互相不可借。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_VALID_STATS = frozenset({"serious", "other", "deaths", "person_time"})


def normalize_period(value: str | None) -> str | None:
    """期别入口归一（会商 F06）：tp1/TP1/tp 1 统一为 TP1，lte→LTE。"""
    text = str(value or "").strip().upper().replace(" ", "").replace("-", "")
    if not text:
        return None
    import re as _re
    m = _re.fullmatch(r"TP(\d+)", text)
    if m:
        return f"TP{m.group(1)}"
    if text in {"LTE", "LTEP"}:
        return "LTE"
    if text == "OLTP":
        return "OLTP"
    if text == "OLEP":
        return "OLEP"
    return text


def period_of(title: str) -> str | None:
    """从组标题提取期别标记（TP1/TP2/OLTP/OLEP/LTE）；无标记返回 None。"""
    text = str(title or "")
    m = re.search(r"\btp\s*[- ]?(\d+)\b", text, re.I)
    if m:
        return f"TP{m.group(1)}"
    # 会商 round-5（grok F12）："Period 1: X" 是期别标记，不得剥前缀后丢期别
    m = re.search(r"\bperiod\s*(\d+)\b", text, re.I)
    if m:
        return f"TP{m.group(1)}"
    if re.search(r"\boltp\b", text, re.I):
        return "OLTP"
    if re.search(r"\bolep\b", text, re.I):
        return "OLEP"
    if re.search(r"\b(?:ltep|lte)\b", text, re.I):
        return "LTE"
    return None


def _base_title(title: str) -> str:
    """标题候选键：剥离期别标记与括注，保留药物/队列身份。"""
    text = " ".join(str(title or "").split()).casefold()
    text = re.sub(r"\((?:tp\s*\d+|lte|olep|oltp|randomized[^)]*)\)", " ", text)
    text = re.sub(r"^(?:treatment\s+)?period\s*\d+\s*[:：]\s*", " ", text)
    text = re.sub(r"\b(?:oltp|olep|ltep|lte|tp\s*\d+)\b:?", " ", text)
    text = re.sub(r"\btp\s*(\d+)\b", " ", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class _Entry:
    stat: str
    period: str | None
    base_title: str
    group_id: str
    title: str
    num_at_risk: float


@dataclass
class _Crosswalk:
    entries: tuple[_Entry, ...]
    conflicts: list[dict] = field(default_factory=list)

    def lookup(
        self,
        *,
        stat: str,
        period: str | None,
        title: str,
    ) -> float | None:
        if stat not in _VALID_STATS:
            return None
        base = _base_title(title)
        candidates = [
            e for e in self.entries
            if e.stat == stat and e.base_title == base
        ]
        if not candidates:
            # 会商 #6 + round-5（grok F10/F11）：名称变体回退仅限——
            # ①该统计对象下恰好一条（人时等其他量纲不参与，也不得挡位）；
            # ②词元级包含（非子串）；③请求期别与该条期别一致（或缺省）
            same_stat = [e for e in self.entries if e.stat == stat]
            # 会商 round-5（grok F11）：其他量纲（人时）不参与也不得挡位；
            # 期别一致与词元包含已足够约束归属
            if len(same_stat) == 1:
                e0 = same_stat[0]
                base_tokens = set(base.split())
                entry_tokens = set(e0.base_title.split())
                token_included = base_tokens <= entry_tokens or entry_tokens <= base_tokens
                requested = normalize_period(period)
                period_ok = requested is None or e0.period == requested
                if token_included and period_ok and base and e0.base_title:
                    return e0.num_at_risk
            return None
        values = {e.num_at_risk for e in candidates}
        requested = normalize_period(period)
        if requested is not None:
            scoped = [e for e in candidates if e.period == requested]
            scoped_values = {e.num_at_risk for e in scoped}
            if len(scoped_values) == 1:
                return scoped.pop().num_at_risk
            if len(scoped_values) > 1:
                # 会商 round-5（grok F13）：期别内冲突只记一条理由
                self.conflicts.append({
                    "stat": stat, "period": requested, "base_title": base,
                    "values": sorted(scoped_values), "reason": "period_scoped_conflict",
                })
                return None
            # 会商 F01：请求期别无候选时一律未知——
            # 不得从其他期别借出（"唯一候选"不是放行理由）
            self.conflicts.append({
                "stat": stat, "period": requested, "base_title": base,
                "values": sorted({e.num_at_risk for e in candidates}),
                "reason": "requested_period_absent",
            })
            return None
        if len(values) == 1 and len({e.period for e in candidates}) == 1:
            # 未请求期别且全部候选同值同期才可确定
            return candidates[0].num_at_risk
        # 同值跨多期：期别未知时借用无依据，拒绝（保守）
        self.conflicts.append({
            "stat": stat, "period": period, "base_title": base,
            "values": sorted(values), "reason": "ambiguous_candidates",
        })
        return None


def build_atrisk_crosswalk(rows) -> "_Crosswalk":
    """rows: 含 module/group_id/title/period/stat/num_at_risk 的映射序列。"""
    entries: list[_Entry] = []
    for row in rows:
        stat = str(row.get("stat") or "").strip()
        risk = row.get("num_at_risk")
        if stat not in _VALID_STATS or risk is None:
            continue
        try:
            value = float(risk)
        except (TypeError, ValueError):
            continue
        if value < 0 or not math_isfinite(value):
            continue
        title = str(row.get("title") or "")
        entries.append(_Entry(
            stat=stat,
            period=normalize_period(row.get("period") or period_of(title)),
            base_title=_base_title(title),
            group_id=str(row.get("group_id") or ""),
            title=title,
            num_at_risk=value,
        ))
    return _Crosswalk(entries=tuple(entries))


def math_isfinite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
