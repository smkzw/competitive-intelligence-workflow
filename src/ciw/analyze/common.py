"""分析层公用：产品显示名、角色标签、比例派生。"""

from __future__ import annotations

from ciw.models import Product, Trial
from ciw.normalize.arms import ROLE_LABEL_ZH


def product_label(p: Product | None) -> str:
    if p is None:
        return ""
    if p.name_zh:
        return f"{p.name_zh}（{p.name_en}）" if p.name_en.casefold() != p.name_zh.casefold() else p.name_zh
    return p.name_en


def role_label(role: str, trial: Trial | None = None, arm_id: str | None = None) -> str:
    if role == "unknown" and trial and arm_id and any(a.arm_id == arm_id and a.role_conflict for a in trial.arms):
        return "登记角色信息不一致"
    return ROLE_LABEL_ZH.get(role, role)


def pct(n: int | None, N: int | None) -> float | None:
    """只由人数派生比例；n 或 N 缺失、N=0、n>N 都不出比例。"""
    if n is None or N is None or N <= 0 or n < 0 or n > N:
        return None
    return round(100.0 * n / N, 1)
