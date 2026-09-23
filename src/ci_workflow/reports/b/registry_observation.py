"""登记来源终点族分类器（政策驱动，适应症无关）。

分类规则从版本化 YAML 政策加载（policies/endpoint-families/），
新增适应症只需添加 YAML 规则块，零 Python 代码改动。
安全域拒判（AE/TEAE/SAE 不入疗效域）由合同固化为独立守卫。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Final, cast

_POLICY_DIR: Final = Path(__file__).resolve().parents[4] / "policies" / "endpoint-families"
_POLICY_FILE: Final = _POLICY_DIR / "registry-v7.yaml"

_cache: dict[str, Any] = {}


def _load_policy() -> dict[str, Any]:
    """加载并缓存终点族政策。"""
    if "policy" not in _cache:
        import yaml

        raw = yaml.safe_load(_POLICY_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("登记终点分类政策必须是映射")
        _cache["policy"] = raw
    return cast(dict[str, Any], _cache["policy"])


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
    return cast(tuple[tuple[str, re.Pattern[str]], ...], _cache["compiled_rules"])


def family_meta_for(rule_id: str) -> dict[str, Any]:
    """返回指定族的 family_meta，供构建器消费。"""
    for rule in _load_policy()["rules"]:
        if rule["rule_id"] == rule_id:
            meta = rule.get("family_meta") or {}
            if not isinstance(meta, dict):
                raise ValueError("登记终点分类元数据必须是映射")
            return cast(dict[str, Any], meta)
    return {}


def is_safety_domain_endpoint(endpoint_text: str) -> bool:
    """安全性口径端点判定：数量计数类 AE/TEAE/SAE 不入疗效域。"""
    text = " ".join((endpoint_text or "").strip().split())
    return bool(safety_domain_pattern().search(text))


def indication_scope_of(rule: dict[str, Any]) -> tuple[str, ...]:
    """规则门闩：无 scope 为跨适应症共享；有 scope 仅在匹配适应症生效。"""
    scope = rule.get("indication_scope") or ()
    if isinstance(scope, str):
        return (scope,)
    return tuple(scope)


def resolve_indication_id(name: str | None) -> str | None:
    """把适应症中文名/英文名/缩写/规范 ID 解析为政策 scope 标识。

    独立审阅 R04（SCI05）：规范 ID（pnh/ipf/...）直接识别，不再要求
    别名表收录自身；无法解析返回 None。"""
    if not name:
        return None
    # 会商 F08：连字符是规范 id 的组成部分（atopic-dermatitis），不得当
    # 噪声删除——否则 "p-n-h" 之类伪 id 会与 pnh 全等
    needle = str(name).strip().casefold().replace(" ", "")
    aliases = _load_policy().get("indication_aliases") or {}
    for scope_id, names in aliases.items():
        canonical = str(scope_id).strip().casefold().replace(" ", "")
        if needle == canonical:
            return str(scope_id)
        for alias in names or ():
            if needle == str(alias).strip().casefold().replace(" ", ""):
                return str(scope_id)
    return None


def scoped_family_rules() -> tuple[tuple[str, re.Pattern[str], tuple[str, ...]], ...]:
    """（rule_id, 编译模式, 门闩 scope）三元组；scope 为空 = 跨适应症共享。"""
    if "compiled_scoped_rules" not in _cache:
        _cache["compiled_scoped_rules"] = tuple(
            (
                rule["rule_id"],
                re.compile(rule["match_pattern"], re.IGNORECASE),
                indication_scope_of(rule),
            )
            for rule in _load_policy()["rules"]
        )
    return cast(
        tuple[tuple[str, re.Pattern[str], tuple[str, ...]], ...],
        _cache["compiled_scoped_rules"],
    )


def classify_registry_endpoint(
    endpoint_text: str, indication_id: str | None = None
) -> str | None:
    """把登记终点文本映射到版本化终点族 rule_id；无法确定时返回 None。

    indication_id（或适应症名，经 resolve_indication_id 解析）提供时，
    仅适用"共享规则 ∪ 该适应症规则"——per-indication 规则不再跨适应症
    误命中（会商 P0 #1）。未提供时保持历史全局首条命中行为。
    """
    text = " ".join((endpoint_text or "").strip().split())
    if not text:
        return None
    if is_safety_domain_endpoint(text):
        return None
    resolved = resolve_indication_id(indication_id) if indication_id else None
    if indication_id and resolved is None:
        # 独立审阅 R04（SCI05）：提供了适应症但无法解析（未知适应症）时
        # 只允许跨适应症共享规则，不得放行任何疾病专属规则——
        # 与"未提供适应症"的历史全局行为显式区分
        for rule_id, pattern, scope in scoped_family_rules():
            if scope:
                continue
            if pattern.search(text):
                return rule_id
        return None
    for rule_id, pattern, scope in scoped_family_rules():
        if scope and resolved is not None and resolved not in scope:
            continue
        if pattern.search(text):
            return rule_id
    return None
