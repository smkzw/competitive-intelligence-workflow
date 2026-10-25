"""临床语义规则（从 v1 领域层提炼的硬规则，全部确定性实现、可测试）。

1. unknown ≠ 0：来源缺失的数值是 None，永不补零。
2. 统计对象分离：事件次数不能除以人数当受试者比例。
3. 比例派生只在「受试者人数 + 同组明确分母」时成立。
4. 安全类别保留否定、严重性、TEAE、相关性与分级集合；Grade 4 / Grade 1 or 3 / Grade ≥3 互不相同。
5. 时间点：只有天 / 周之间按 7 精确换算；月不固定换算为周。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------- 数值与比例

def parse_number(raw: object) -> float | None:
    """Only finite exact scalars; censoring is not equality to its threshold."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        try:
            value = float(raw)
        except OverflowError:
            return None
        return value if math.isfinite(value) else None
    text = str(raw).strip()
    if text in {"", "NA", "N/A", "NE", "--", "-", "None", "null"}:
        return None
    if not re.fullmatch(r'[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', text):
        return None
    value = float(text.replace(',', ''))
    return value if math.isfinite(value) else None


def parse_observation(raw: object) -> float | str | None:
    """Keep a valid censored source expression verbatim, outside exact axes."""
    if isinstance(raw, str):
        match = re.fullmatch(r'\s*(?:[<>]=?|[≤≥])\s*(.+?)\s*', raw)
        if match and parse_number(match[1]) is not None:
            return raw
    return parse_number(raw)


def derive_proportion(count: object, denominator: object, stat_type: str) -> float | None:
    """受试者比例 (%)。事件次数、未知分母、0 分母一律不派生。"""
    if stat_type != "count_participants":
        return None
    n = parse_number(count)
    d = parse_number(denominator)
    if n is None or d is None or d <= 0 or n < 0 or n > d:
        return None
    return round(n / d * 100, 1)


# ---------------------------------------------------------------- 安全类别

Seriousness = Literal["serious", "non_serious", "any"]


@dataclass(frozen=True)
class SafetyCategory:
    raw: str
    seriousness: Seriousness = "any"
    treatment_emergent: bool = False
    related: bool | None = None            # None = 未限定相关性
    grades: frozenset[int] | None = None   # None = 未限定分级
    excludes_serious: bool = False         # 如 "TEAEs without SAEs"
    leading_to_discontinuation: bool = False
    fatal: bool = False
    composite: bool = False                # 复合父项（如 "SAE or AE leading to discontinuation"）
    notes: tuple[str, ...] = field(default=())

    def key(self) -> tuple[object, ...]:
        return (self.seriousness, self.treatment_emergent, self.related, self.grades,
                self.excludes_serious, self.leading_to_discontinuation, self.fatal, self.composite)


_GRADE_GE = re.compile(r"grade\s*(?:≥|>=|>\s*=|greater than or equal to)\s*(\d)", re.IGNORECASE)
_GRADE_RANGE = re.compile(r"grade\s*(\d)\s*(?:-|–|to)\s*(\d)", re.IGNORECASE)
_GRADE_LIST = re.compile(r"grades?\s*(\d(?:\s*(?:,|or|and)\s*\d)*)", re.IGNORECASE)


def _grades(text: str) -> frozenset[int] | None:
    if m := _GRADE_GE.search(text):
        lo = int(m.group(1))
        return frozenset(range(lo, 6))
    if m := _GRADE_RANGE.search(text):
        lo, hi = sorted((int(m.group(1)), int(m.group(2))))
        return frozenset(range(lo, hi + 1))
    if m := _GRADE_LIST.search(text):
        return frozenset(int(x) for x in re.findall(r"\d", m.group(1)))
    return None


def classify_safety(term: str) -> SafetyCategory:
    t = " " + re.sub(r"\s+", " ", term.lower()) + " "
    notes: list[str] = []
    excludes_serious = bool(re.search(r"(without|excluding|other than)\s+(an?\s+)?(sae|serious)", t))
    if re.search(r"non[- ]?serious", t):
        seriousness: Seriousness = "non_serious"
    elif excludes_serious:
        seriousness = "any"
    elif re.search(r"\bsaes?\b|\bserious\b|\bsteaes?\b|\btesaes?\b", t):
        seriousness = "serious"
    else:
        seriousness = "any"
    teae = bool(re.search(r"\bteaes?\b|treatment[- ]emergent|\btesaes?\b|\bsteaes?\b", t))
    related: bool | None = None
    if re.search(r"not related|unrelated", t):
        related = False
    elif re.search(r"related|drug[- ]related|treatment[- ]related|\btrae", t):
        related = True
    composite = bool(re.search(r"\b(or|and/or)\b", t)) and not _GRADE_LIST.search(t)
    if composite:
        notes.append("复合类别：不得拆分或与单一类别相加")
    return SafetyCategory(
        raw=term,
        seriousness=seriousness,
        treatment_emergent=teae,
        related=related,
        grades=_grades(t),
        excludes_serious=excludes_serious,
        leading_to_discontinuation=bool(re.search(r"discontinu|withdraw", t)),
        fatal=bool(re.search(r"death|fatal|died", t)),
        composite=composite,
        notes=tuple(notes),
    )


def same_safety_category(a: str, b: str) -> bool:
    """两个来源类别是否可放在同一安全比较列中。"""
    return classify_safety(a).key() == classify_safety(b).key()


# ---------------------------------------------------------------- 时间点

@dataclass(frozen=True)
class Timepoint:
    raw: str
    days: int | None          # 能精确换算时的天数
    months: int | None        # 以月表达时保留月，不换算


def parse_timepoint(text: str) -> Timepoint:
    t = text.lower()
    if m := re.search(r"week\s*(\d+)|(\d+)\s*weeks?|第\s*(\d+)\s*周", t):
        n = int(next(g for g in m.groups() if g))
        return Timepoint(text, n * 7, None)
    if m := re.search(r"day\s*(\d+)|(\d+)\s*days?|第\s*(\d+)\s*天", t):
        n = int(next(g for g in m.groups() if g))
        return Timepoint(text, n, None)
    if m := re.search(r"month\s*(\d+)|(\d+)\s*months?|第\s*(\d+)\s*(?:个)?月", t):
        n = int(next(g for g in m.groups() if g))
        return Timepoint(text, None, n)
    return Timepoint(text, None, None)


def same_timepoint(a: str, b: str) -> bool | None:
    """True/False；无法判断返回 None（交给人或分面展示，不强行同轴）。"""
    ta, tb = parse_timepoint(a), parse_timepoint(b)
    if ta.days is not None and tb.days is not None:
        return ta.days == tb.days
    if ta.months is not None and tb.months is not None:
        return ta.months == tb.months
    return None


# ---------------------------------------------------------------- 横比资格

def comparable_on_axis(a: dict[str, object], b: dict[str, object]) -> tuple[bool, str]:
    """两个结果事实能否放在同一数值轴。返回 (是否可比, 不可比原因)。

    规则刻意保守但不阻断展示：不可比时平台使用分面/相邻小图，而不是丢弃数据。
    """
    if a.get("stat_type") != b.get("stat_type"):
        return False, "统计形式不同"
    if (a.get("unit") or "").lower() != (b.get("unit") or "").lower():
        return False, "单位不同"
    same_tp = same_timepoint(str(a.get("timepoint") or ""), str(b.get("timepoint") or ""))
    if same_tp is False:
        return False, "时间点不同"
    if same_tp is None:
        return False, "时间点无法判定"
    if a.get("endpoint_key") and b.get("endpoint_key") and a["endpoint_key"] != b["endpoint_key"]:
        return False, "终点定义不同"
    return True, ""
