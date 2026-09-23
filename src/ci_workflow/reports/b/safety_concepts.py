"""安全域测量的受控概念分类（独立审阅 R02 / 会商 round-4 #1）。

分类原则（会商裁决后的实现顺序）：
1. 否定先行：non-/not-/no-/without- + 严重/TEAE 等否定短语只剥离否定
   短语本身（不得吞掉并列句后半句），剥离后走正常规则；
2. **特定族优先**：因 AE 停药、治疗相关、3 级及以上、AESI、严重 TEAE
   子集等特定指标先判定——它们不得被总体键（any_teae/any_sae）吞掉
   （会商 F02：any 键优先使"无法确认"只可能更粗，伪造总体发生率）；
3. 总体族其次：any TEAE / any SAE / death 只收总体指标；
4. generic AE 兜底；无法确认保留 specific_ae/unknown 一等状态，
   拒判不丢数据。

分母统计对象（CONCEPT_ATRISK_STAT）：generic_ae 同样对应 AE 模块
other 统计口径（会商 #6：generic_ae 不查 crosswalk 导致 55 行分母
写成"未公开"）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ci_workflow.reports.b.concept_catalog import spec_of

# 否定短语：只剥离否定词与其紧邻的限定词，不动并列句其余部分
_NEGATION_PATTERNS = (
    re.compile(r"\bnon[\s-]*serious\b", re.I),
    re.compile(r"\b(?:not|no|without)[\s-]+serious\b", re.I),
    re.compile(r"\bnon[\s-]*treatment[\s-]*emergent\b", re.I),
    re.compile(r"\bnon[\s-]*teaes?\b", re.I),
    re.compile(r"\b(?:not|no|without)\s+teaes?\b", re.I),
)

# 特定族优先（会商 #1：任何 specific 标记先于总体键判定）
_SPECIFIC_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("discontinuation_ae", re.compile(
        r"discontinu\w*(?:\s+\w+){0,4}\s(?:due\s+to|because\s+of|leading)|"
        r"(?:due\s+to|because\s+of)\s+adverse|leading\s+to\s+(?:treatment\s+)?discontinu", re.I)),
    ("treatment_related_ae", re.compile(
        r"treatment[\s-]*related|related\s+adverse\s+events?", re.I)),
    ("grade_3_plus", re.compile(
        r"grade\s*(?:≥|>=)?\s*[34]\b"
        r"|grade\s+[12]\s+(?:or|and)\s+[34]\b"
        r"|grade\s+[34]\s+(?:or|and)\s+[1-4]\b", re.I)),
    ("aesi", re.compile(
        r"(?:adverse\s+events?|\(?teaes?\)?)\s+of\s+special\s+interest|(?<![a-z])aesis?(?![a-z])", re.I)),
    # 严重 TEAE 子集：特定子集，不得归 any_teae/any_sae
    ("serious_teae_subset", re.compile(
        r"serious\s+(?:treatment[\s-]*emergent|teaes?)", re.I)),
)

# 总体族（特定族未命中才判定）
_GENERAL_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("any_teae", re.compile(r"(?<![a-z\-])teaes?(?![a-z])", re.I)),
    ("any_teae", re.compile(
        r"\b(?:any|overall|all)\b[^.;]{0,40}treatment[\s-]*emergent", re.I)),
    ("any_sae", re.compile(r"\bserious\s+adverse\s+events?\b", re.I)),
    ("any_sae", re.compile(r"(?<![a-z\-])saes?(?![a-z])", re.I)),
    ("death", re.compile(r"\bdeaths?\b|\bmortality\b", re.I)),
)

_GENERIC_RULE = re.compile(r"\badverse\s+events?\b|(?<![a-z\-])aes(?![a-z])", re.I)

_CONCEPT_CATEGORY_ZH = {
    key: spec_of(key).category_zh for key in (
        "any_teae", "any_sae", "death", "aesi", "discontinuation_ae",
        "treatment_related_ae", "grade_3_plus", "serious_teae_subset",
        "generic_ae", "specific_ae", "composite_ae", "grade_specific",
        "non_serious_teae", "absence_sae", "unknown",
    )
}

# 概念 → AE 模块分母统计对象（单源：concept_catalog；会商 #6 generic_ae 查 other）
CONCEPT_ATRISK_STAT = {
    key: spec_of(key).at_risk_stat
    for key in (
        "any_teae", "any_sae", "death", "aesi", "discontinuation_ae",
        "treatment_related_ae", "grade_3_plus", "serious_teae_subset",
        "generic_ae", "specific_ae", "composite_ae", "grade_specific",
        "non_serious_teae", "absence_sae", "unknown",
    )
    if spec_of(key).at_risk_stat
}


@dataclass(frozen=True)
class SafetyConcept:
    key: str
    polarity: str = "affirmed"
    grade_set: tuple[int, ...] = ()
    seriousness: str = "unspecified"
    teae: bool | None = None
    relatedness: str = "unspecified"
    parent: str | None = None
    children: tuple[str, ...] = ()
    count_basis: str = "participants"
    at_risk_stat: str | None = None


def _fragments(text: str) -> list[str]:
    # Parenthetical commas describe one event and are not list separators.
    scrubbed = re.sub(r"\([^)]*\)", lambda m: m.group(0).replace(",", "，"), text)
    return [item.strip(" ,;:") for item in re.split(r",|;|\band\b", scrubbed, flags=re.I)
            if item.strip(" ,;:")]


def describe_safety_concept(title: str) -> SafetyConcept:
    text = " ".join(str(title or "").split())
    if not text:
        return SafetyConcept(key="unknown")
    lowered = text.casefold()
    grades = tuple(sorted({int(value) for value in re.findall(r"\b([1-5])\b", lowered)})) \
        if "grade" in lowered else ()
    if re.search(r"\bnon[\s-]*serious\b", lowered) and re.search(r"\bteaes?\b|treatment[\s-]*emergent", lowered):
        return SafetyConcept("non_serious_teae", "negative_seriousness", grades,
                             "non_serious", True, at_risk_stat=spec_of("non_serious_teae").at_risk_stat)
    if re.search(r"\b(?:without|no|not)\s+(?:any\s+)?saes?\b", lowered):
        return SafetyConcept("absence_sae", "negative_presence", grades, "serious", False,
                             at_risk_stat=spec_of("absence_sae").at_risk_stat)
    if grades:
        if re.search(r"grade\s*3\s*(?:or|and|/)\s*(?:4|5)|grade\s*(?:≥|>=)\s*3|grade\s*3\s+or\s+higher", lowered):
            key = "grade_3_plus"
        else:
            key = "grade_specific"
        return SafetyConcept(key, grade_set=grades, seriousness="graded",
                             parent="generic_ae", at_risk_stat=spec_of(key).at_risk_stat)
    children: list[str] = []
    for fragment in _fragments(text):
        stripped = fragment
        for pattern in _NEGATION_PATTERNS:
            stripped = pattern.sub(" ", stripped)
        key = _classify_single(stripped)
        if key and key not in children:
            children.append(key)
    if len(children) > 1:
        return SafetyConcept("composite_ae", children=tuple(children), count_basis="mixed")
    key = children[0] if children else "unknown"
    return SafetyConcept(
        key=key,
        seriousness="serious" if key in {"any_sae", "serious_teae_subset"} else "unspecified",
        teae=True if key in {"any_teae", "serious_teae_subset"} else None,
        relatedness="related" if key == "treatment_related_ae" else "unspecified",
        at_risk_stat=spec_of(key).at_risk_stat,
    )


def _classify_single(text: str) -> str | None:
    for concept, pattern in _SPECIFIC_RULES:
        if pattern.search(text):
            return concept
    for concept, pattern in _GENERAL_RULES:
        if pattern.search(text):
            return concept
    if _GENERIC_RULE.search(text):
        return "generic_ae"
    if re.search(r"adverse|safety|\bae\b", text, re.I):
        return "specific_ae"
    return None


def classify_safety_concept(title: str) -> str:
    """把安全域测量标题映射到受控概念键；永不返回 None（拒判不丢数据）。

    会商 round-5（A r44）：逗号/"and" 并列多处面的复合测量（如
    "TEAEs, SAEs, Grade 3/4 AEs, And Events Leading To Discontinuation"）
    不得按首个特定键收类——逐片段独立分类，≥2 个不同概念即判
    composite_ae（复合不良事件指标），描述性呈现不冒充单一族。"""
    described = describe_safety_concept(title)
    if described.key in {"non_serious_teae", "absence_sae", "grade_specific", "grade_3_plus", "composite_ae"}:
        return described.key
    text = " ".join(str(title or "").split())
    if not text:
        return "unknown"
    stripped = text
    for pattern in _NEGATION_PATTERNS:
        stripped = pattern.sub(" ", stripped)
    fragments = [
        fragment.strip(" ,;:")
        for fragment in re.split(r",|;|\band\b", stripped, flags=re.I)
        if fragment.strip(" ,;:")
    ]
    fragment_concepts = [
        concept
        for fragment in fragments
        if (concept := _classify_single(fragment)) is not None
    ]
    distinct = set(fragment_concepts)
    if len(distinct) == 1:
        return fragment_concepts[0]
    if len(distinct) > 1:
        return "composite_ae"
    whole = _classify_single(stripped)
    if whole is not None:
        return whole
    return "unknown"


def safety_category_zh(concept: str) -> str:
    """概念键 → 展示类别（构建器统一消费，避免各处自造中文）。"""
    return _CONCEPT_CATEGORY_ZH.get(concept, _CONCEPT_CATEGORY_ZH["unknown"])
