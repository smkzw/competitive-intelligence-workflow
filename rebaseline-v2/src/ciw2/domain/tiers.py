"""字段分级：只有「错了会出事」的字段走严格核验。

critical：必须有来源原文片段，且确定性核验通过（原文存在 + 数值出现在原文中）；
          未通过时在平台中显示为「未核实」，不进入横比图的数值轴。
standard：有原文片段时同样核验；无片段允许展示，但标注抽取方式。
"""

from __future__ import annotations

from typing import Literal

Tier = Literal["critical", "standard"]

# 前缀匹配：字段名以这些前缀开头即为 critical。
CRITICAL_FIELD_PREFIXES: tuple[str, ...] = (
    "result.primary",          # 主要终点结果值
    "result.key_secondary",    # 关键次要终点
    "result.denominator",      # 分母 / 分析人数
    "safety.sae",              # 严重不良事件
    "safety.discontinuation",  # 因 AE 停药
    "safety.death",
    "design.sample_size",      # 样本量
    "design.primary_endpoint", # 主要终点定义 + 时间点
    "status.china",            # 中国注册/上市状态
    "status.china_mah",        # 中国 MAH
    "status.global_approval",  # 全球获批
)


def tier_of(field: str) -> Tier:
    return "critical" if field.startswith(CRITICAL_FIELD_PREFIXES) else "standard"
