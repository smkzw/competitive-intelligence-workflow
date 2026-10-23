"""注册中心枚举与年龄单位的中文显示适配。

纯查表映射，输入是数据而不是指令：
- 只做精确匹配，不折叠大小写、不去空白/标点、不做模糊匹配；
- 未知编码与未知年龄格式原样返回，缺失值显示破折号；
- 返回普通 str，不做 HTML 转义或标记插值，也不改动调用方数据。
"""

from __future__ import annotations

import re

EM_DASH = "—"
PHASE_ZH = {"preclinical": "临床前", "phase1": "I 期", "phase1_2": "I/II 期", "phase2": "II 期",
            "phase2_3": "II/III 期", "phase3": "III 期", "nda_bla": "上市申请", "approved": "已上市",
            "phase4": "IV 期", "unknown": "未知"}

_REGISTRY_LABELS: dict[str, dict[str, str]] = {
    "trial_status": {
        "NOT_YET_RECRUITING": "尚未招募",
        "RECRUITING": "正在招募",
        "ENROLLING_BY_INVITATION": "邀请入组",
        "ACTIVE_NOT_RECRUITING": "进行中，已停止招募",
        "COMPLETED": "已完成",
        "SUSPENDED": "暂停",
        "TERMINATED": "提前终止",
        "WITHDRAWN": "未启动即撤回",
        "UNKNOWN": "状态未知",
    },
    "allocation": {
        "RANDOMIZED": "随机分组",
        "NON_RANDOMIZED": "非随机分组",
        "NA": "不适用",
    },
    "masking": {
        "NONE": "开放标签",
        "SINGLE": "单盲",
        "DOUBLE": "双盲",
        "TRIPLE": "三盲",
        "QUADRUPLE": "四盲",
    },
    "arm_type": {
        "EXPERIMENTAL": "试验组",
        "ACTIVE_COMPARATOR": "阳性对照组",
        "PLACEBO_COMPARATOR": "安慰剂对照组",
        "SHAM_COMPARATOR": "模拟干预对照组",
        "NO_INTERVENTION": "无干预组",
        "OTHER": "其他组",
    },
}

_AGE_UNITS = {
    "Years": "岁",
    "Months": "个月",
    "Weeks": "周",
    "Days": "天",
    "Hours": "小时",
    "Minutes": "分钟",
}

_AGE_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?) (Years|Months|Weeks|Days|Hours|Minutes)")


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def registry_label(value: object, category: str) -> str:
    """把规范注册中心编码显示为中文；未知编码或分类原样返回。"""
    text = _text(value)
    if text is None:
        return EM_DASH
    labels = _REGISTRY_LABELS.get(category) if isinstance(category, str) else None
    if labels is None:
        return text
    return labels.get(text, text)


def age_label(value: object) -> str:
    """把规范年龄文本显示为中文单位；不换算单位，也不推断不等式或缺失含义。"""
    text = _text(value)
    if text is None:
        return EM_DASH
    match = _AGE_PATTERN.fullmatch(text)
    if match is None:
        return text
    number, unit = match.groups()
    return number + _AGE_UNITS[unit]
