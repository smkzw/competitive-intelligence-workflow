"""时间点、统计形式、结局域与临床概念的确定性判定。"""

from __future__ import annotations

import re

from ciw.config import IndicationConfig
from ciw.models import TimePoint

# ---------- 时间点 ----------
_WEEK_LIST = re.compile(
    r"weeks?\s*(\d+(?:\s*(?:,\s*(?:and\s+)?|and\s+)(?:weeks?\s*)?\d+)+)", re.I
)
_WEEK = re.compile(r"weeks?\s*(\d+(?:\.\d+)?)(?:\s*(?:to|-|–|through)\s*(?:weeks?\s*)?(\d+(?:\.\d+)?))?", re.I)
_DAY = re.compile(r"days?\s*(\d+)(?:\s*(?:to|-|–|through)\s*(?:days?\s*)?(\d+))?", re.I)
_MONTH = re.compile(r"months?\s*(\d+)", re.I)
_BARE_WEEKS = re.compile(r"(\d+)\s*weeks?\b", re.I)


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def parse_timepoint(*texts: str) -> TimePoint | None:
    """按优先级在若干文本中找时间点；同一文本里取最后出现（“Baseline, Week 24” → 第24周）。"""
    for text in texts:
        if not text:
            continue
        listed = list(_WEEK_LIST.finditer(text))
        if listed:
            last = float(re.findall(r"\d+", listed[-1].group(1))[-1])
            return TimePoint(raw=text, label=f"至第{_fmt(last)}周（多时间点）", key=f"W{_fmt(last)}*", weeks=last)
        weeks = list(_WEEK.finditer(text))
        if weeks:
            m = weeks[-1]
            a, b = float(m.group(1)), (float(m.group(2)) if m.group(2) else None)
            if b is not None and a == 0:  # “Week 0 to Week 68” 是基线到第 68 周，不是区间
                a, b = b, None
            if b is not None and b != a:
                return TimePoint(raw=text, label=f"第{_fmt(a)}–{_fmt(b)}周", key=f"W{_fmt(a)}-{_fmt(b)}", weeks=b)
            return TimePoint(raw=text, label=f"第{_fmt(a)}周", key=f"W{_fmt(a)}", weeks=a)
        days = list(_DAY.finditer(text))
        if days:
            m = days[-1]
            a = int(m.group(1))
            b = int(m.group(2)) if m.group(2) else None
            if b is not None and a == 0:  # “Day 0 to Day 28” 是基线到第 28 天
                a, b = b, None
            end = b if b is not None else a
            wk = end / 7 if end % 7 == 0 else None
            if b is not None and b != a:
                return TimePoint(raw=text, label=f"第{a}–{b}天", key=f"D{a}-{b}", weeks=wk)
            return TimePoint(raw=text, label=f"第{a}天", key=f"D{a}", weeks=wk)
        months = list(_MONTH.finditer(text))
        if months:
            a = int(months[-1].group(1))
            return TimePoint(raw=text, label=f"第{a}个月", key=f"M{a}", weeks=None)
        bare = list(_BARE_WEEKS.finditer(text))
        if bare:
            a = float(bare[-1].group(1))
            return TimePoint(raw=text, label=f"第{_fmt(a)}周", key=f"W{_fmt(a)}", weeks=a)
    return None


# ---------- 统计形式 ----------
_PCT_OF_PARTICIPANTS = re.compile(
    r"(percent(age)?|%|proportion)\s*(of)?\s*(participants|patients|subjects)|participants\s*\(%\)", re.I
)
_PARTICIPANTS = re.compile(r"\b(participants|patients|subjects)\b", re.I)

MEASURE_LABEL_ZH = {
    "ls_mean": "最小二乘均值",
    "mean": "均值",
    "median": "中位数",
    "geometric_mean": "几何均值",
    "geometric_ls_mean": "几何最小二乘均值",
    "proportion": "比例（%）",
    "count": "人数",
    "count_units": "计数",
    "number": "数值",
    "other": "其他统计量",
}


def measure_kind(param_type: str, unit: str) -> str:
    pt = (param_type or "").upper()
    if pt == "LEAST_SQUARES_MEAN":
        return "ls_mean"
    if pt == "MEAN":
        return "mean"
    if pt == "MEDIAN":
        return "median"
    if pt == "GEOMETRIC_MEAN":
        return "geometric_mean"
    if pt == "GEOMETRIC_LEAST_SQUARES_MEAN":
        return "geometric_ls_mean"
    if pt == "COUNT_OF_PARTICIPANTS":
        return "count"
    if pt == "COUNT_OF_UNITS":
        return "count_units"
    if pt == "NUMBER":
        if _PCT_OF_PARTICIPANTS.search(unit or ""):
            return "proportion"
        if _PARTICIPANTS.search(unit or ""):
            return "count"
        return "number"
    return "other"


# ---------- 域与概念 ----------
_IMMUNO = re.compile(r"anti[- ]drug antibod|\bADAs?\b(?![-\s]?cog)|immunogenicity|neutralizing antibod", re.I)
_PK_STRONG = re.compile(
    r"^\W*(?:serum|plasma|trough|steady[- ]state)?\s*(?:drug\s+)?"
    r"(?:concentrations?|pharmacokinetic|C(?:max|trough|min)\b|AUC)",
    re.I,
)
_PK = re.compile(
    r"pharmacokinetic|concentration|\bC(max|min|trough|avg)\b|\bAUC|\bT(max|1/2)\b|half[- ]li(fe|ves)|"
    r"apparent clearance|clearance \(CL|\bCL/F\b|volume of distribution|\bPK\b",
    re.I,
)
_SAFETY = re.compile(
    r"adverse (event|reaction)|\bT?E?AEs?\b|\bSAEs?\b|treatment[- ]emergent|serious adverse|"
    r"laboratory (abnormal|value|parameter)|vital sign|electrocardiogram|\bECG\b|"
    r"injection[- ]site reaction|hypersensitivity",
    re.I,
)
_PD = re.compile(r"eosinophil|\bIgE\b|\bTARC\b|periostin|FeNO|biomarker|pharmacodynamic|cytokine|\bIL-\d", re.I)


def classify(title: str, cfg: IndicationConfig, definition: str = "") -> tuple[str, str | None]:
    """返回 (domain, concept_id)。疗效只来自概念字典；字典外、非 PK/PD/免疫原性/安全的一律 other。"""
    if _IMMUNO.search(title):
        return "immunogenicity", None
    ordered = sorted(cfg.concepts, key=lambda c: c.source_definition is None)
    clinical = any(c.domain == "efficacy" and c.matches(title, definition) for c in ordered)
    if _PD.search(title) and re.search(r"concentration|level|count", title, re.I) and not clinical:
        return "pd", None  # 生物标志物浓度（如总 IgE）不是药代
    if _PK_STRONG.search(title):
        return "pk", None  # “某药血清浓度…（需全身激素者）”仍是药代
    if _PK.search(title) and not any(c.matches(title, definition) for c in cfg.concepts):
        return "pk", None
    if _SAFETY.search(title):
        return "safety", None
    for concept in ordered:
        if concept.matches(title, definition):
            return concept.domain, concept.id
    if _PD.search(title):
        return "pd", None
    return "other", None


def is_biomarker_title(title: str) -> bool:
    return bool(_PD.search(title))


def concept_of(title: str, cfg: IndicationConfig, definition: str = "") -> str | None:
    ordered = sorted(cfg.concepts, key=lambda c: c.source_definition is None)
    return next((c.id for c in ordered if c.matches(title, definition)), None)


# ---------- 亚组 ----------
_SUBGROUP = re.compile(
    r"(?:[:：,]\s*)?(sub-?group[^;]*|\b(?:in|among)\s+(?:participants|patients|subjects)\s+(?:with|who|without|aged|having|in)\b.*)$",
    re.I,
)


def subgroup_of(title: str) -> str:
    """结局标题里的亚组限定原文；没有返回空串。"""
    m = _SUBGROUP.search(title or "")
    return m.group(1).strip() if m else ""
