"""组别角色。只用显式信息：armGroups.type、结果组与臂的规范化精确匹配、配置别名。匹配不上就是 unknown。"""

from __future__ import annotations

import re

from ciw.config import normalize_name
from ciw.models import Arm, ArmRole, Period
from ciw.normalize.products import ProductResolver

ROLE_BY_TYPE: dict[str, ArmRole] = {
    "EXPERIMENTAL": "experimental",
    "ACTIVE_COMPARATOR": "active_comparator",
    "PLACEBO_COMPARATOR": "placebo",
    "SHAM_COMPARATOR": "placebo",
    "NO_INTERVENTION": "no_intervention",
    "OTHER": "other",
}

ROLE_LABEL_ZH: dict[str, str] = {
    "experimental": "试验组",
    "active_comparator": "活性对照",
    "placebo": "安慰剂",
    "no_intervention": "空白对照",
    "other": "其他",
    "unknown": "组别未匹配",
}

_PLACEBO = re.compile(r"\b(placebo|vehicle|sham)\b", re.I)
_PLACEBO_ONLY = re.compile(r"(?:(?:matching|matched)\s+)?(?:placebos?|vehicle|sham)(?:\s+(?:to|for)\s+.+)?", re.I)
_PERIOD_RULES: list[tuple[re.Pattern[str], Period]] = [
    (re.compile(r"run[- ]?in", re.I), "run_in"),
    (re.compile(r"follow[- ]?up|post[- ]?treatment|off[- ]?treatment", re.I), "follow_up"),
    (re.compile(r"open[- ]label extension|\bOLE\b|extension (period|phase|study)", re.I), "extension"),
]
_QUALIFIER = re.compile(r"\s*[\(\[（][^)\]）]*[\)\]）]\s*")


def arm_role(arm_type: str, interventions: list[str]) -> tuple[ArmRole, bool]:
    role = ROLE_BY_TYPE.get(arm_type, "unknown")
    conflict = role in {"experimental", "active_comparator", "no_intervention"} and bool(interventions) and all(
        _PLACEBO_ONLY.fullmatch(name.strip()) for name in interventions
    )
    return ("unknown" if conflict else role), conflict


def period_of(title: str) -> Period:
    for rx, period in _PERIOD_RULES:
        if rx.search(title):
            return period
    return "treatment"


def match_group(title: str, arms: list[Arm], resolver: ProductResolver) -> tuple[str | None, ArmRole, str | None]:
    """结果组/AE 组标题 → (arm_id, role, product_id)。"""
    period = period_of(title)
    if period == "run_in":
        return None, "other", None
    by_label = {normalize_name(a.label): a for a in arms}
    for cand in (title, _QUALIFIER.sub(" ", title).strip()):
        arm = by_label.get(normalize_name(cand))
        if arm:
            return arm.arm_id, arm.role, (arm.product_ids[0] if len(arm.product_ids) == 1 else None)

    products = resolver.find_all_in_text(title)
    has_placebo_word = bool(_PLACEBO.search(title))
    if len(products) == 1 and not has_placebo_word:
        pid = next(iter(products))
        # 只看“仅含该产品”的臂：联合方案臂（如 A+B）不能替单药组定角色
        solo = [a for a in arms if a.product_ids == [pid]]
        roles = {a.role for a in solo}
        if len(roles) == 1:
            role = roles.pop()
            return (solo[0].arm_id if len(solo) == 1 else None), role, pid
        return None, "unknown", pid  # 产品不在任何单药臂，或单药臂角色不一致
    if not products and has_placebo_word and any(a.role == "placebo" for a in arms):
        placebo_arms = [a for a in arms if a.role == "placebo"]
        return (placebo_arms[0].arm_id if len(placebo_arms) == 1 else None), "placebo", None
    return None, "unknown", None
