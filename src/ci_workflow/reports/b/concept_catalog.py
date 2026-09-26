"""安全概念词表单源（会商 round-4 #2 / 层1 根因收敛）。

背景：同一安全概念曾在事实层、A 明细表、A 矩阵 JS、PDF 投影、PPT
投影、B 标签表各自写字面，字面互不相同导致精确匹配失效（TEAE 轴
0/146 命中、PDF A 安全轴 45/45 点静默坏死、门禁词表脱节）。
合同：事实层写概念键（term_key），全部展示层按 key 取标签；
渲染器/构建器禁止再出现中文概念字面常量（catalog 定义处除外）。
"""
from __future__ import annotations

from dataclasses import dataclass

_SOURCE_SUFFIX = "（登记）"


@dataclass(frozen=True)
class SafetyConceptSpec:
    key: str
    label_zh: str  # 受控短标签：明细表/矩阵/筛选（无来源后缀）
    category_zh: str  # 事实层类别（带（登记）来源后缀）
    at_risk_stat: str | None  # AE 模块对应分母统计对象


SAFETY_CONCEPTS: dict[str, SafetyConceptSpec] = {
    "any_teae": SafetyConceptSpec(
        "any_teae", "治疗期间不良事件", "治疗中出现的不良事件（登记）", "other"),
    "any_sae": SafetyConceptSpec(
        "any_sae", "严重不良事件", "严重不良事件（登记）", "serious"),
    "death": SafetyConceptSpec(
        "death", "死亡病例", "死亡病例（登记）", "deaths"),
    "aesi": SafetyConceptSpec(
        "aesi", "特别关注不良事件", "特别关注不良事件（登记）", "other"),
    "discontinuation_ae": SafetyConceptSpec(
        "discontinuation_ae", "因不良事件停药", "因不良事件停药（登记）", "other"),
    "treatment_related_ae": SafetyConceptSpec(
        "treatment_related_ae", "治疗相关不良事件", "治疗相关不良事件（登记）", "other"),
    "grade_3_plus": SafetyConceptSpec(
        "grade_3_plus", "3级及以上不良事件", "3级及以上不良事件（登记）", "other"),
    "grade_specific": SafetyConceptSpec(
        "grade_specific", "特定等级不良事件", "特定等级不良事件（登记）", "other"),
    "non_serious_teae": SafetyConceptSpec(
        "non_serious_teae", "非严重TEAE", "非严重TEAE（登记）", "other"),
    "absence_sae": SafetyConceptSpec(
        "absence_sae", "未发生SAE", "未发生SAE（登记）", "serious"),
    "serious_teae_subset": SafetyConceptSpec(
        "serious_teae_subset", "严重TEAE子集", "严重TEAE子集（登记）", "other"),
    "severity_specific_teae": SafetyConceptSpec(
        "severity_specific_teae", "特定强度TEAE", "特定强度TEAE（登记）", "other"),
    "generic_ae": SafetyConceptSpec(
        "generic_ae", "不良事件", "不良事件（登记）", "other"),
    "specific_ae": SafetyConceptSpec(
        "specific_ae", "特定不良事件指标", "特定不良事件指标（登记）", "other"),
    "composite_ae": SafetyConceptSpec(
        "composite_ae", "复合不良事件指标", "复合不良事件指标（登记）", None),
    "unknown": SafetyConceptSpec(
        "unknown", "未归类安全域指标", "未归类安全域指标（登记）", None),
}


def spec_of(concept: str) -> SafetyConceptSpec:
    return SAFETY_CONCEPTS.get(concept, SAFETY_CONCEPTS["unknown"])


def category_base(category: str | None) -> str:
    """登记类别带"（登记）"来源后缀，判定一律按基础类别名。"""
    return str(category or "").replace(_SOURCE_SUFFIX, "").strip()


# 旧口径类别名 → 概念键（历史载荷/夹具兼容读取；不用于新事实写入）
_LEGACY_BASE_ALIASES = {
    "治疗期间不良事件": "any_teae",
    "任何TEAE": "any_teae",
    "严重不良事件": "any_sae",
    "任何SAE": "any_sae",
    "死亡病例": "death",
    "特别关注不良事件": "aesi",
    "常见不良事件": "generic_ae",
}


def row_concept(row: object) -> str | None:
    """读一行安全事实的概念键；term_key 缺失时按基础类别名回推（旧数据）。"""
    key = getattr(row, "term_key", None)
    if key is None and isinstance(row, dict):
        key = row.get("term_key")
    if key:
        return str(key)
    category = row.get("category") if isinstance(row, dict) else getattr(row, "category", None)
    base = category_base(category)
    if base in _LEGACY_BASE_ALIASES:
        return _LEGACY_BASE_ALIASES[base]
    for concept, spec in SAFETY_CONCEPTS.items():
        if base and base == spec.category_zh.replace(_SOURCE_SUFFIX, ""):
            return concept
    return None


def row_is_any_teae(row: object) -> bool:
    return row_concept(row) == "any_teae"


def row_is_any_sae(row: object) -> bool:
    return row_concept(row) == "any_sae"
