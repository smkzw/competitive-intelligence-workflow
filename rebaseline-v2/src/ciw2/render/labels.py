"""注册中心枚举、统计/测量单位与年龄单位的显示适配。

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


def phase_label(value: object) -> str:
    text=_text(value)
    if text is None:
        return PHASE_ZH['unknown']
    # Registry Chinese phase strings are already labels, not unknown enum codes.
    match=re.fullmatch(r'(I{1,3}|IV)(/(?:I{1,3}|IV))?期',text)
    return text[:-1]+' 期' if match else PHASE_ZH.get(text,text)

_REGISTRY_LABELS: dict[str, dict[str, str]] = {
    'measure_unit': {
        'score on a scale': '分', 'Participants': '人', 'participants': '人',
        'percent change': '%变化', 'percentage of participants': '%',
        'nanograms per milliliters (ng/mL)': 'ng/mL',
        'micrograms per milliliter (ug/mL)': 'ug/mL',
        'liter per micrograms (L/ug)': 'L/ug', 'liter per day (L/day)': 'L/day',
        'liter': 'L', 'per day': '1/天', 'day': '天',
    },
    'statistic': {
        'mean': '均值', 'median': '中位数', 'ls_mean': '最小二乘均值',
        'ls_mean_change': '最小二乘均值变化', 'mean_change': '均值变化',
        'percent_change': '百分比变化', 'proportion': '受试者比例',
        'count_participants': '受试者人数', 'count_events': '事件次数',
        'hazard_ratio': '风险比', 'odds_ratio': '优势比', 'risk_difference': '风险差',
        'number': '数值',
    },
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
        "COMPARATOR": "对照组",
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
