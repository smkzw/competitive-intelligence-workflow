"""从锁定的 ClinicalTrials.gov 记录恢复完整入选与排除标准。

C 类报告必须保留所选登记版本公开的全部标准。这个模块只做来源字段的
确定性分段与报告数据回填，不翻译、不概括，也不改变其他设计观察。
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class EligibilitySourceError(ValueError):
    """登记原文或报告观察无法形成一一对应的完整入排标准。"""


_EXCLUSION_HEADING = re.compile(
    r"(?:<p[^>]*>\s*)?(?:key\s+)?exclusion\s+criteria\s*:?(?:\s*</p>)?",
    re.IGNORECASE,
)
_INCLUSION_HEADING = re.compile(
    r"(?:<p[^>]*>\s*)?(?:key\s+)?inclusion\s+criteria\s*:?(?:\s*</p>)?",
    re.IGNORECASE,
)


def _required_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EligibilitySourceError(f"{label}必须是对象")
    return value


def extract_eligibility_sections(record: Mapping[str, Any]) -> tuple[str, str]:
    """返回登记字段中完整的入选段和排除段，保持条目正文原样。"""

    protocol = _required_mapping(record.get("protocolSection"), "protocolSection")
    module = _required_mapping(protocol.get("eligibilityModule"), "eligibilityModule")
    raw = module.get("eligibilityCriteria")
    if not isinstance(raw, str) or not raw.strip():
        raise EligibilitySourceError("登记记录缺少 eligibilityCriteria 原文")

    exclusion = _EXCLUSION_HEADING.search(raw)
    if exclusion is None:
        raise EligibilitySourceError("登记原文无法定位排除标准标题")
    inclusion = _INCLUSION_HEADING.search(raw, 0, exclusion.start())
    inclusion_start = 0 if inclusion is None else inclusion.end()
    inclusion_text = raw[inclusion_start : exclusion.start()].strip()
    exclusion_text = raw[exclusion.end() :].strip()
    if not inclusion_text or not exclusion_text:
        raise EligibilitySourceError("登记原文的入选或排除标准为空")
    return inclusion_text, exclusion_text


def hydrate_report_eligibility(
    payload: Mapping[str, Any], source_dir: Path
) -> dict[str, Any]:
    """用逐试验锁定登记原文替换报告中被摘录的入排观察。

    每个试验必须恰有一条入选观察和一条排除观察；完整条目仍保存在同一
    ``source_text`` 内，由门户按条拆分展示。缺来源、重复观察或身份不一致均
    失败关闭，避免把技术缺口误写成“未公开”。
    """

    result = copy.deepcopy(dict(payload))
    trials = result.get("trials")
    observations = result.get("observations")
    if not isinstance(trials, list) or not isinstance(observations, list):
        raise EligibilitySourceError("C 类报告数据缺少试验或设计观察")

    trial_ids = {
        str(item.get("id", "")).strip().casefold()
        for item in trials
        if isinstance(item, Mapping)
    }
    if not trial_ids or "" in trial_ids:
        raise EligibilitySourceError("C 类报告包含无效试验标识")

    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in observations:
        if not isinstance(item, dict):
            raise EligibilitySourceError("设计观察必须是对象")
        field = str(item.get("field", ""))
        if field not in {"inclusion_criterion", "exclusion_criterion"}:
            continue
        key = (str(item.get("trial_id", "")).strip().casefold(), field)
        by_key.setdefault(key, []).append(item)

    for trial_id in sorted(trial_ids):
        source_path = source_dir / f"{trial_id.upper()}.json"
        try:
            record = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EligibilitySourceError(f"无法读取 {trial_id.upper()} 锁定登记记录") from exc
        record_map = _required_mapping(record, f"{trial_id.upper()} 登记记录")
        inclusion_text, exclusion_text = extract_eligibility_sections(record_map)
        replacements = {
            "inclusion_criterion": inclusion_text,
            "exclusion_criterion": exclusion_text,
        }
        for field, source_text in replacements.items():
            rows = by_key.get((trial_id, field), [])
            if len(rows) != 1:
                raise EligibilitySourceError(
                    f"{trial_id.upper()} 的{field}观察应恰有一条，实际 {len(rows)} 条"
                )
            rows[0]["source_text"] = source_text
    return result


__all__ = [
    "EligibilitySourceError",
    "extract_eligibility_sections",
    "hydrate_report_eligibility",
]
