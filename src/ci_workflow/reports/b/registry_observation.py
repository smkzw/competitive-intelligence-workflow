"""登记来源终点族分类器（政策驱动，适应症无关）。

分类规则从版本化 YAML 政策加载（policies/endpoint-families/），
新增适应症只需添加 YAML 规则块，零 Python 代码改动。
安全域拒判（AE/TEAE/SAE 不入疗效域）由合同固化为独立守卫。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Final

_POLICY_DIR: Final = Path(__file__).resolve().parents[4] / "policies" / "endpoint-families"
_POLICY_FILE: Final = _POLICY_DIR / "registry-v7.yaml"

_cache: dict[str, Any] = {}


def _load_policy() -> dict[str, Any]:
    """加载并缓存终点族政策。"""
    if "policy" not in _cache:
        import yaml

        raw = yaml.safe_load(_POLICY_FILE.read_text(encoding="utf-8"))
        _cache["policy"] = raw
    return _cache["policy"]  # type: ignore[return-value]


def classifier_version() -> str:
    return "registry-endpoint-family-" + str(_load_policy().get("version", "?"))


CLASSIFIER_VERSION: Final = classifier_version()


def safety_domain_pattern() -> re.Pattern[str]:
    return re.compile(_load_policy()["safety_domain_pattern"], re.IGNORECASE)


def family_rules() -> tuple[tuple[str, re.Pattern[str]], ...]:
    if "compiled_rules" not in _cache:
        _cache["compiled_rules"] = tuple(
            (rule["rule_id"], re.compile(rule["match_pattern"], re.IGNORECASE))
            for rule in _load_policy()["rules"]
        )
    return _cache["compiled_rules"]  # type: ignore[return-value]


def family_meta_for(rule_id: str) -> dict[str, Any]:
    """返回指定族的 family_meta，供构建器消费。"""
    for rule in _load_policy()["rules"]:
        if rule["rule_id"] == rule_id:
            return rule.get("family_meta") or {}
    return {}


def is_safety_domain_endpoint(endpoint_text: str) -> bool:
    """安全性口径端点判定：数量计数类 AE/TEAE/SAE 不入疗效域。"""
    text = " ".join((endpoint_text or "").strip().split())
    return bool(safety_domain_pattern().search(text))


def classify_registry_endpoint(endpoint_text: str) -> str | None:
    """把登记终点文本映射到版本化终点族 rule_id；无法确定时返回 None。"""
    text = " ".join((endpoint_text or "").strip().split())
    if not text:
        return None
    if is_safety_domain_endpoint(text):
        return None
    for rule_id, pattern in family_rules():
        if pattern.search(text):
            return rule_id
    return None
