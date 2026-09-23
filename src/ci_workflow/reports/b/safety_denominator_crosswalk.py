"""跨模块安全分母 crosswalk（独立审阅 R03 / 验收 SCI03、SCI04）。

合同：
- 每条目绑定模块、原始组 ID、归一化标题（含期别标记）、期别、分母统计
  对象（serious/other/deaths/person_time）与数值；
- 标题匹配只生成候选；期别不一致或候选值冲突时返回"未知"，不得借用、
  不得 first-wins、不得以单组回退吞掉冲突；
- 人时（person_time）与人数是不同量纲，互相不可借。
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

_VALID_STATS = frozenset({"serious", "other", "deaths", "person_time"})


def normalize_period(value: str | None) -> str | None:
    """期别入口归一（会商 F06）：tp1/TP1/tp 1 统一为 TP1，lte→LTE。"""
    text = str(value or "").strip().upper().replace(" ", "").replace("-", "")
    if not text:
        return None
    import re as _re
    m = _re.fullmatch(r"TP(\d+)", text)
    if m:
        return f"TP{m.group(1)}"
    m = _re.fullmatch(r"PERIOD(\d+)", text)
    if m:
        return f"TP{m.group(1)}"
    if text in {"LTE", "LTEP"}:
        return "LTE"
    if text == "OLTP":
        return "OLTP"
    if text == "OLEP":
        return "OLEP"
    return text


def period_of(title: str) -> str | None:
    """从组标题提取期别标记（TP1/TP2/OLTP/OLEP/LTE）；无标记返回 None。"""
    text = str(title or "")
    m = re.search(r"\btp\s*[- ]?(\d+)\b", text, re.I)
    if m:
        return f"TP{m.group(1)}"
    # 会商 round-5（grok F12）："Period 1: X" 是期别标记，不得剥前缀后丢期别
    m = re.search(r"\bperiod\s*(\d+)\b", text, re.I)
    if m:
        return f"TP{m.group(1)}"
    if re.search(r"\boltp\b", text, re.I):
        return "OLTP"
    if re.search(r"\bolep\b", text, re.I):
        return "OLEP"
    if re.search(r"\b(?:ltep|lte)\b", text, re.I):
        return "LTE"
    return None


def _base_title(title: str) -> str:
    """标题候选键：剥离期别标记与括注，保留药物/队列身份。"""
    text = " ".join(str(title or "").split()).casefold()
    text = re.sub(r"\((?:tp\s*\d+|lte|olep|oltp|randomized[^)]*)\)", " ", text)
    text = re.sub(r"^(?:treatment\s+)?period\s*\d+\s*[:：]\s*", " ", text)
    text = re.sub(r"\b(?:oltp|olep|ltep|lte|tp\s*\d+)\b:?", " ", text)
    text = re.sub(r"\btp\s*(\d+)\b", " ", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class _Entry:
    study_id: str
    module: str
    stat: str
    period: str | None
    base_title: str
    group_id: str
    title: str
    num_at_risk: int | float
    measure_object: str
    analysis_population: str
    window: str
    source_version_id: str
    relationships: tuple[tuple[str, str, str, str], ...]


@dataclass
class _Crosswalk:
    entries: tuple[_Entry, ...]
    conflicts: list[dict[str, object]] = field(default_factory=list)

    def lookup(
        self,
        *,
        stat: str,
        period: str | None,
        title: str,
        study_id: str | None = None,
        module: str | None = None,
        group_id: str | None = None,
        measure_object: str | None = None,
        analysis_population: str | None = None,
        window: str | None = None,
        source_version_id: str | None = None,
    ) -> int | float | None:
        if stat not in _VALID_STATS:
            return None
        base = _base_title(title)
        identity = (
            study_id, module, group_id, measure_object, analysis_population, window,
            source_version_id,
        )
        if all(value is not None and str(value).strip() for value in identity):
            requested = normalize_period(period)
            def compatible(e: _Entry) -> bool:
                if study_id is not None and e.study_id != str(study_id):
                    return False
                if measure_object is not None and e.measure_object != str(measure_object):
                    return False
                if (
                    analysis_population is not None
                    and e.analysis_population != str(analysis_population)
                ):
                    return False
                if window is not None and normalize_period(e.window) != normalize_period(window):
                    return False
                if source_version_id is not None and e.source_version_id != str(source_version_id):
                    return False
                if requested is not None and e.period != requested:
                    return False
                if group_id is None:
                    return False
                direct = (
                    module is not None and e.module == str(module) and e.group_id == str(group_id)
                )
                explicit = any(
                    target_module == str(module)
                    and target_group == str(group_id)
                    and kind in {"source_declared", "audited_mapping"}
                    and bool(mapping_id)
                    for target_module, target_group, kind, mapping_id in e.relationships
                )
                return direct or explicit
            identified = [e for e in self.entries if e.stat == stat and compatible(e)]
            # A title can veto a wrong explicit edge but can never create one.
            identified = [e for e in identified if not base or e.base_title == base]
            values = {e.num_at_risk for e in identified}
            if len(values) == 1:
                return identified[0].num_at_risk
            if identified:
                self.conflicts.append({
                    "stat": stat, "period": requested, "base_title": base,
                    "values": sorted(values), "reason": "explicit_identity_conflict",
                })
            return None
        # Production lookup is identity-complete and fail closed.  Historical
        # title-only migration is available only through the explicit adapter
        # below and is therefore unreachable from current consumers.
        return None

    def _legacy_readonly_lookup(
        self, *, stat: str, period: str | None, title: str,
    ) -> int | float | None:
        base = _base_title(title)
        candidates = [
            e for e in self.entries
            if e.stat == stat and e.base_title == base
        ]
        if not candidates:
            # 会商 #6 + round-5（grok F10/F11）：名称变体回退仅限——
            # ①该统计对象下恰好一条（人时等其他量纲不参与，也不得挡位）；
            # ②词元级包含（非子串）；③请求期别与该条期别一致（或缺省）
            same_stat = [e for e in self.entries if e.stat == stat]
            # 会商 round-5（grok F11）：其他量纲（人时）不参与也不得挡位；
            # 期别一致与词元包含已足够约束归属
            if len(same_stat) == 1:
                e0 = same_stat[0]
                base_tokens = base.split()
                entry_tokens = set(e0.base_title.split())
                # 会商 round-6（grok F18）：锚定词元一致 + 查询词元全含——
                # "rVA576 Placebo"（多出的角色词）与 "576"（剂量碎片）都不得借
                token_included = (
                    bool(base_tokens)
                    and base_tokens[0] == e0.base_title.split()[0]
                    and set(base_tokens) <= entry_tokens
                )
                requested = normalize_period(period)
                period_ok = requested is None or e0.period == requested
                if token_included and period_ok and base and e0.base_title:
                    return e0.num_at_risk
            return None
        values = {e.num_at_risk for e in candidates}
        requested = normalize_period(period)
        if requested is not None:
            scoped = [e for e in candidates if e.period == requested]
            scoped_values = {e.num_at_risk for e in scoped}
            if len(scoped_values) == 1:
                return scoped.pop().num_at_risk
            if len(scoped_values) > 1:
                # 会商 round-5（grok F13）：期别内冲突只记一条理由
                self.conflicts.append({
                    "stat": stat, "period": requested, "base_title": base,
                    "values": sorted(scoped_values), "reason": "period_scoped_conflict",
                })
                return None
            # 会商 F01：请求期别无候选时一律未知——
            # 不得从其他期别借出（"唯一候选"不是放行理由）
            self.conflicts.append({
                "stat": stat, "period": requested, "base_title": base,
                "values": sorted({e.num_at_risk for e in candidates}),
                "reason": "requested_period_absent",
            })
            return None
        if len(values) == 1 and len({e.period for e in candidates}) == 1:
            # 未请求期别且全部候选同值同期才可确定
            return candidates[0].num_at_risk
        # 同值跨多期：期别未知时借用无依据，拒绝（保守）
        self.conflicts.append({
            "stat": stat, "period": period, "base_title": base,
            "values": sorted(values), "reason": "ambiguous_candidates",
        })
        return None


def build_atrisk_crosswalk(rows: Sequence[Mapping[str, Any]]) -> _Crosswalk:
    """rows: 含 module/group_id/title/period/stat/num_at_risk 的映射序列。"""
    entries: list[_Entry] = []
    for row in rows:
        stat = str(row.get("stat") or "").strip()
        risk = row.get("num_at_risk")
        if stat not in _VALID_STATS or risk is None:
            continue
        try:
            if isinstance(risk, bool):
                continue
            value: int | float = risk if isinstance(risk, (int, float)) else float(risk)
        except (TypeError, ValueError):
            continue
        if value < 0 or not math_isfinite(value):
            continue
        title = str(row.get("title") or "")
        entries.append(_Entry(
            study_id=str(row.get("study_id") or ""),
            module=str(row.get("module") or ""),
            stat=stat,
            period=normalize_period(row.get("period") or period_of(title)),
            base_title=_base_title(title),
            group_id=str(row.get("group_id") or ""),
            title=title,
            num_at_risk=value,
            measure_object=str(row.get("measure_object") or ""),
            analysis_population=str(row.get("analysis_population") or ""),
            window=str(row.get("window") or row.get("period") or ""),
            source_version_id=str(row.get("source_version_id") or ""),
            relationships=tuple(
                (
                    str(item.get("target_module") or ""),
                    str(item.get("target_group_id") or ""),
                    str(item.get("relationship_kind") or ""),
                    str(item.get("mapping_id") or ""),
                )
                for item in row.get("relationships", ())
                if isinstance(item, dict)
            ),
        ))
    return _Crosswalk(entries=tuple(entries))


@dataclass(frozen=True)
class LegacyReadOnlyAtRiskCrosswalkAdapter:
    """Explicit historical snapshot adapter; never use for production builds."""

    crosswalk: _Crosswalk

    def lookup(self, *, stat: str, period: str | None, title: str) -> int | float | None:
        return self.crosswalk._legacy_readonly_lookup(stat=stat, period=period, title=title)


def math_isfinite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
