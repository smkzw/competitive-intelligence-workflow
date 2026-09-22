"""安全域测量的受控概念分类（独立审阅 R02 / 验收 SCI02）。

分类原则：
- 否定先行：non-serious 等否定短语先剥离，再跑正向规则，否定不得被
  positive 词命中；
- 总体与特定分开：any TEAE / any SAE 只给总体指标；generic AE、因 AE
  停药、治疗相关、3 级及以上等特定指标不得自动归入 any 键
  （term_key 驱动安全轴与气泡选择，错配会伪造总体发生率）；
- 拒判不丢数据：无法确认时返回 specific_ae/unknown 概念，行仍可描述性
  呈现，不强行 any。
"""
from __future__ import annotations

import re

# 概念 → 受控键。顺序即优先级；否定剥离先于全部规则。
_CONCEPT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    # 总体 TEAE：TEAE 缩写独立成词，或 any/overall 与 treatment-emergent 同现
    ("any_teae", re.compile(r"(?<![a-z])teaes?(?![a-z])", re.I)),
    ("any_teae", re.compile(
        r"\b(?:any|overall|all)\b[^.;]{0,40}treatment[\s-]*emergent", re.I)),
    # 总体 SAE：serious adverse events / SAE 缩写（否定已先行剥离）
    ("any_sae", re.compile(r"\bserious\s+adverse\s+events?\b", re.I)),
    ("any_sae", re.compile(r"(?<![a-z])saes?(?![a-z])", re.I)),
    ("death", re.compile(r"\bdeaths?\b|\bmortality\b", re.I)),
    ("aesi", re.compile(r"adverse\s+events?\s+of\s+special\s+interest|(?<![a-z])aesis?(?![a-z])", re.I)),
    ("discontinuation_ae", re.compile(
        r"discontinu\w*(?:\s+\w+){0,4}\s(?:due\s+to|because\s+of|leading)|"
        r"(?:due\s+to|because\s+of)\s+adverse", re.I)),
    ("treatment_related_ae", re.compile(
        r"treatment[\s-]*related|related\s+adverse\s+events?", re.I)),
    ("grade_3_plus", re.compile(r"grade\s*(?:≥|>=)?\s*3\b|grade\s+3\s+or", re.I)),
    # generic AE 兜底：adverse events/AEs 无总体限定词
    ("generic_ae", re.compile(r"\badverse\s+events?\b|(?<![a-z])aes(?![a-z])", re.I)),
)

# 否定短语：命中即从候选文本剥离，防止正向词误命中
_NEGATION_PATTERNS = (
    re.compile(r"\bnon[\s-]*serious\b[^;,.)]*", re.I),
    re.compile(r"\bnot[\s-]*serious\b[^;,.)]*", re.I),
    re.compile(r"\bnon[\s-]*treatment[\s-]*emergent\b[^;,.)]*", re.I),
)

_CONCEPT_CATEGORY_ZH = {
    "any_teae": "治疗中出现的不良事件（登记）",
    "any_sae": "严重不良事件（登记）",
    "death": "死亡病例（登记）",
    "aesi": "特别关注不良事件（登记）",
    "discontinuation_ae": "因不良事件停药（登记）",
    "treatment_related_ae": "治疗相关不良事件（登记）",
    "grade_3_plus": "3级及以上不良事件（登记）",
    "generic_ae": "不良事件（登记）",
    "specific_ae": "特定不良事件指标（登记）",
    "unknown": "未归类安全域指标（登记）",
}


def classify_safety_concept(title: str) -> str:
    """把安全域测量标题映射到受控概念键；永不返回 None（拒判不丢数据）。"""
    text = " ".join(str(title or "").split())
    if not text:
        return "unknown"
    stripped = text
    for pattern in _NEGATION_PATTERNS:
        stripped = pattern.sub(" ", stripped)
    for concept, pattern in _CONCEPT_RULES:
        if pattern.search(stripped):
            return concept
    if re.search(r"adverse|safety|\bae\b", stripped, re.I):
        return "specific_ae"
    return "unknown"


def safety_category_zh(concept: str) -> str:
    """概念键 → 展示类别（构建器统一消费，避免各处自造中文）。"""
    return _CONCEPT_CATEGORY_ZH.get(concept, _CONCEPT_CATEGORY_ZH["unknown"])


# 分母统计对象：概念 → AE 模块对应统计列（R03：人数/事件数/人时不可互换）
CONCEPT_ATRISK_STAT = {
    "any_sae": "serious",
    "any_teae": "other",
    "death": "deaths",
}
