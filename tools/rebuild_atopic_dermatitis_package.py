#!/usr/bin/env python3
"""从锁定的 A 类来源包确定性重建特应性皮炎结果行。

这个工具只读取输入包中已经保存的 ClinicalTrials.gov JSON，不联网，也不修改
输入文件。输出目录包含：

* ``research-content.json``：可交给独立科学复核的规范化内容候选；
* ``rebuild-manifest.json``：输入摘要、内容摘要、抽取计数和精确诊断。

工具不会自行生成或更新 ``scientific_review``。结果内容改变后，必须由独立
复核者重新确认摘要，才能再形成执行器接受的 ``research-package.json``。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from ci_workflow.application.source_research_service import (
    ResearchFact,
    SourceCapture,
    audit_clinicaltrials_result_coverage,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.report_a import ReportAPortalData

ResultKind = Literal["efficacy", "teae", "sae", "aesi", "common_ae"]
IssueKind = Literal["parse_failure", "not_reported", "unmapped_source"]

_NCT_ID = re.compile(r"NCT[0-9]{8}", re.IGNORECASE)
_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
_NOT_REPORTED = frozenset(
    {
        "na",
        "n/a",
        "nr",
        "not available",
        "not reported",
        "not applicable",
        "未报告",
        "未公开",
    }
)


class RebuildError(ValueError):
    """研究包重建输入或输出不符合本工具合同。"""


@dataclass(frozen=True)
class RebuildIssue:
    """一个可审计的未抽取或未映射结果。"""

    kind: IssueKind
    source_id: str
    trial_id: str | None
    source_path: str
    reason_zh: str

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "source_id": self.source_id,
            "trial_id": self.trial_id,
            "source_path": self.source_path,
            "reason_zh": self.reason_zh,
        }


@dataclass(frozen=True)
class RebuildResult:
    """重建结果及其确定性诊断。"""

    input_path: Path
    output_dir: Path
    content_path: Path
    manifest_path: Path
    content_digest: str
    input_digest: str
    counts: Mapping[str, int]
    issues: tuple[RebuildIssue, ...]


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RebuildError(f"无法读取研究包：{path}") from exc
    if not isinstance(value, dict):
        raise RebuildError("研究包顶层必须是对象")
    return cast(dict[str, Any], value)


def _text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} 必须是对象")
    return value


def _list(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} 必须是列表")
    return value


def _nct(value: object) -> str | None:
    match = _NCT_ID.search(_text(value))
    return None if match is None else match.group(0).upper()


def _number(value: object) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError("缺少数值")
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        normalized = _text(value).replace(",", "")
        if _NUMBER.fullmatch(normalized) is None:
            raise ValueError(f"不支持的数值表达：{normalized}")
        result = float(normalized)
    if not math.isfinite(result):
        raise ValueError("数值不是有限数")
    return result


def _integer(value: object) -> int:
    result = _number(value)
    if not result.is_integer():
        raise ValueError("数值不是整数")
    return int(result)


def _value_or_issue(
    value: object,
    *,
    source_id: str,
    trial_id: str,
    source_path: str,
    issues: list[RebuildIssue],
) -> float | None:
    """解析一个结果值；NA 等明确标记为未报告，不伪造零值。"""

    if value is None:
        issues.append(
            RebuildIssue(
                kind="not_reported",
                source_id=source_id,
                trial_id=trial_id,
                source_path=source_path,
                reason_zh="来源明确没有可报告数值，保留为未报告，不以零值代替",
            )
        )
        return None
    if isinstance(value, str) and _text(value).casefold() in _NOT_REPORTED:
        issues.append(
            RebuildIssue(
                kind="not_reported",
                source_id=source_id,
                trial_id=trial_id,
                source_path=source_path,
                reason_zh=f"来源值“{_text(value)}”表示未报告，保留原始状态",
            )
        )
        return None
    try:
        return _number(value)
    except ValueError as exc:
        issues.append(
            RebuildIssue(
                kind="parse_failure",
                source_id=source_id,
                trial_id=trial_id,
                source_path=source_path,
                reason_zh=f"结果值无法安全解析：{exc}",
            )
        )
        return None


def _arm(group_title: object) -> str:
    title = _text(group_title).casefold()
    if "placebo- " in title:
        current = title.rsplit("placebo- ", 1)[-1]
        if not any(token in current for token in ("placebo", "vehicle", "control", "对照")):
            return "治疗组"
    for separator in (" then ", " to ", "/"):
        if separator in title:
            current = title.rsplit(separator, 1)[-1]
            if not any(token in current for token in ("placebo", "vehicle", "control", "对照")):
                return "治疗组"
    if any(token in title for token in ("placebo", "vehicle", "control", "对照")):
        return "对照组"
    return "治疗组"


def _result_category(measure_title: str, class_title: str = "") -> ResultKind | None:
    """按登记标题分类；混合 AE/SAE 依赖 class 标题拆分。"""

    measure = measure_title.casefold()
    class_name = class_title.casefold()
    combined = f"{measure} {class_name}"
    if class_name:
        if "aesi" in class_name or "adverse event of special interest" in class_name:
            return "aesi"
        if "serious" in class_name or class_name.strip() in {"sae", "saes", "serious aes"}:
            return "sae"
        if "teae" in class_name or "treatment emergent adverse event" in class_name:
            return "teae"
        if class_name.strip() in {"ae", "aes", "any ae", "any aes", "adverse events"}:
            return "teae"
    has_teae = any(
        token in combined
        for token in (
            "teae",
            "treatment-emergent adverse event",
            "treatment emergent adverse event",
            "any treatment emergent adverse event",
        )
    )
    has_sae = any(
        token in combined
        for token in (
            "sae",
            "serious adverse event",
            "serious adverse",
            "treatment emergent serious",
            "serious teae",
        )
    )
    if "aesi" in combined or "adverse event of special interest" in combined:
        return "aesi"
    if has_teae and has_sae:
        # class 标题提供了安全维度时可以拆开；否则保持解析失败。
        class_is_sae = "sae" in class_name or "serious" in class_name
        class_is_teae = "teae" in class_name or ("adverse event" in class_name and not class_is_sae)
        if class_is_sae:
            return "sae"
        if class_is_teae:
            return "teae"
        if class_name.strip() in {"aes", "any aes"}:
            return "teae"
        if class_name.strip() in {"saes", "serious aes"}:
            return "sae"
        return None
    if has_sae:
        return "sae"
    if has_teae:
        return "teae"
    return "efficacy"


def _safety_term(category: ResultKind, measure_title: str, class_title: str) -> str:
    if category == "sae":
        return "任何SAE"
    if category == "aesi":
        return "预先界定AESI"
    class_name = class_title.casefold().strip()
    if "any treatment emergent" in class_name or "any teae" in class_name:
        return "任何TEAE"
    if (
        class_name in {"aes", "any aes", "adverse events"}
        and re.search(
            r"(?:number|percentage) of participants with treatment[- ]emergent adverse events",
            measure_title.casefold(),
        )
    ):
        return "任何TEAE"
    if class_name in {"aes", "any aes", "adverse events"}:
        return "任何AE"
    return measure_title


def _unit(measure: Mapping[str, Any], title: str) -> str:
    raw = _text(measure.get("unitOfMeasure"))
    lowered = raw.casefold()
    param_type = _text(measure.get("paramType")).casefold()
    if any(token in lowered for token in ("percentage", "percent", "%", "百分比")):
        return "%"
    if any(
        token in lowered
        for token in ("participant", "participants", "count_of_participants", "number of")
    ) or "count_of_participants" in param_type:
        return "人"
    if not lowered and any(
        token in title.casefold() for token in ("percentage", "percent", "%", "百分比")
    ):
        return "%"
    return raw or "登记原始单位未说明"


def _population(measure: Mapping[str, Any]) -> str:
    return _text(measure.get("populationDescription")) or "登记结果人群未单列"


def _denominators(
    measure: Mapping[str, Any],
    *,
    source_id: str,
    trial_id: str,
    path: str,
    issues: list[RebuildIssue],
) -> dict[str, int]:
    values: dict[str, int] = {}
    raw_denoms = measure.get("denoms", [])
    try:
        denoms = _list(raw_denoms, f"{path}.denoms")
    except ValueError as exc:
        issues.append(
            RebuildIssue("parse_failure", source_id, trial_id, f"{path}.denoms", str(exc))
        )
        return values
    for denom_index, raw_denom in enumerate(denoms):
        denom_path = f"{path}.denoms[{denom_index}]"
        try:
            denom = _mapping(raw_denom, denom_path)
            counts = _list(denom.get("counts", []), f"{denom_path}.counts")
            for count_index, raw_count in enumerate(counts):
                count_path = f"{denom_path}.counts[{count_index}]"
                count = _mapping(raw_count, count_path)
                group_id = _text(count.get("groupId"))
                if not group_id:
                    raise ValueError("分母缺少组别标识")
                values[group_id] = _integer(count.get("value"))
                if values[group_id] <= 0:
                    raise ValueError("分母必须为正整数")
        except (TypeError, ValueError, KeyError) as exc:
            issues.append(RebuildIssue("parse_failure", source_id, trial_id, denom_path, str(exc)))
    return values


def _locator(source: Mapping[str, Any], source_path: str) -> dict[str, Any]:
    base = dict(cast(Mapping[str, Any], source["locator"]))
    base["field_path"] = source_path
    return base


def _raw_value(value: float, unit: str) -> str:
    text = str(int(value)) if value.is_integer() else f"{value:g}"
    return f"{text}%" if unit == "%" else text


def _issue_for_shape(
    issues: list[RebuildIssue], *, source_id: str, trial_id: str, path: str, detail: str
) -> None:
    issues.append(
        RebuildIssue(
            kind="parse_failure",
            source_id=source_id,
            trial_id=trial_id,
            source_path=path,
            reason_zh=f"来源结构暂未支持：{detail}；不得降级为未公开",
        )
    )


def _outcome_rows(
    *,
    source: Mapping[str, Any],
    source_id: str,
    trial_id: str,
    product_id: str,
    trial_name: str,
    issues: list[RebuildIssue],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], CounterLike]:
    rows: list[dict[str, Any]] = []
    fact_meta: list[dict[str, Any]] = []
    counts: CounterLike = defaultdict(int)
    try:
        results_section = _mapping(source["decoded"].get("resultsSection"), "resultsSection")
        module_value = results_section.get("outcomeMeasuresModule")
        if module_value is None:
            return rows, fact_meta, counts
        module = _mapping(module_value, "resultsSection.outcomeMeasuresModule")
        measures = _list(
            module.get("outcomeMeasures", []),
            "resultsSection.outcomeMeasuresModule.outcomeMeasures",
        )
    except (TypeError, ValueError, KeyError) as exc:
        _issue_for_shape(
            issues,
            source_id=source_id,
            trial_id=trial_id,
            path="resultsSection.outcomeMeasuresModule",
            detail=str(exc),
        )
        return rows, fact_meta, counts

    for measure_index, raw_measure in enumerate(measures):
        measure_path = f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{measure_index}]"
        try:
            measure = _mapping(raw_measure, measure_path)
            title = _text(measure.get("title"))
            timeframe = _text(measure.get("timeFrame"))
            if not title or not timeframe:
                raise ValueError("结局缺少标题或时间窗")
            groups_raw = _list(measure.get("groups", []), f"{measure_path}.groups")
            groups: dict[str, str] = {}
            for group_index, raw_group in enumerate(groups_raw):
                group_path = f"{measure_path}.groups[{group_index}]"
                group = _mapping(raw_group, group_path)
                group_id = _text(group.get("id"))
                group_title = _text(group.get("title"))
                if not group_id or not group_title:
                    raise ValueError("结局组别缺少标识或标题")
                groups[group_id] = group_title
            if not groups:
                raise ValueError("结局没有组别")
            classes = _list(measure.get("classes", []), f"{measure_path}.classes")
            denoms = _denominators(
                measure,
                source_id=source_id,
                trial_id=trial_id,
                path=measure_path,
                issues=issues,
            )
            unit = _unit(measure, title)
            population = _population(measure)
        except (TypeError, ValueError, KeyError) as exc:
            _issue_for_shape(
                issues,
                source_id=source_id,
                trial_id=trial_id,
                path=measure_path,
                detail=str(exc),
            )
            continue

        for class_index, raw_class in enumerate(classes):
            class_path = f"{measure_path}.classes[{class_index}]"
            try:
                class_mapping = _mapping(raw_class, class_path)
                class_title = _text(class_mapping.get("title"))
                categories = _list(class_mapping.get("categories", []), f"{class_path}.categories")
                category = _result_category(title, class_title)
                if category is None:
                    raise ValueError("同一结局同时包含 TEAE 与 SAE，且类别标题不足以拆分")
            except (TypeError, ValueError, KeyError) as exc:
                _issue_for_shape(
                    issues,
                    source_id=source_id,
                    trial_id=trial_id,
                    path=class_path,
                    detail=str(exc),
                )
                continue
            for category_index, raw_category in enumerate(categories):
                category_path = f"{class_path}.categories[{category_index}]"
                try:
                    category_mapping = _mapping(raw_category, category_path)
                    measurements = _list(
                        category_mapping.get("measurements", []),
                        f"{category_path}.measurements",
                    )
                except (TypeError, ValueError, KeyError) as exc:
                    _issue_for_shape(
                        issues,
                        source_id=source_id,
                        trial_id=trial_id,
                        path=category_path,
                        detail=str(exc),
                    )
                    continue
                for measurement_index, raw_measurement in enumerate(measurements):
                    measurement_path = f"{category_path}.measurements[{measurement_index}]"
                    try:
                        measurement = _mapping(raw_measurement, measurement_path)
                        group_id = _text(measurement.get("groupId"))
                        if not group_id or group_id not in groups:
                            raise ValueError(f"结果组别未定义：{group_id or '空值'}")
                    except (TypeError, ValueError, KeyError) as exc:
                        _issue_for_shape(
                            issues,
                            source_id=source_id,
                            trial_id=trial_id,
                            path=measurement_path,
                            detail=str(exc),
                        )
                        continue
                    value = _value_or_issue(
                        measurement.get("value"),
                        source_id=source_id,
                        trial_id=trial_id,
                        source_path=measurement_path,
                        issues=issues,
                    )
                    if value is None:
                        continue
                    arm = _arm(groups[group_id])
                    numerator = None
                    denominator = None
                    displayed_value = value
                    displayed_unit = unit
                    if unit == "人" and group_id in denoms:
                        numerator = int(value)
                        denominator = denoms[group_id]
                        if numerator < 0 or numerator > denominator:
                            _issue_for_shape(
                                issues,
                                source_id=source_id,
                                trial_id=trial_id,
                                path=measurement_path,
                                detail="受试者人数超出来源分母",
                            )
                            continue
                        displayed_value = round(numerator * 100 / denominator, 1)
                        displayed_unit = "%"
                    row_id = stable_id("a-rebuild-efficacy-row", source_id, measurement_path)
                    row: dict[str, Any]
                    if category == "efficacy":
                        endpoint = title
                        if class_title and len(classes) > 1:
                            endpoint = f"{title}（{class_title}）"
                        row = {
                            "row_id": row_id,
                            "product_id": product_id,
                            "trial_id": trial_id,
                            "endpoint": endpoint,
                            "timepoint": timeframe,
                            "arm": arm,
                            "arm_detail": groups[group_id],
                            "value": displayed_value,
                            "numerator": numerator,
                            "denominator": denominator,
                            "unit": displayed_unit,
                            "population": population,
                        }
                        rows.append(row)
                        fact_meta.append(
                            _fact_meta(
                                row_ref=f"efficacy:{row_id}",
                                fact_id=stable_id("a-rebuild-fact", source_id, row_id),
                                entity_id=trial_id,
                                entity_type="trial",
                                canonical_name=trial_name or title,
                                field_id="result.efficacy",
                                source=source,
                                source_id=source_id,
                                source_path=measurement_path,
                                raw_value=_raw_value(value, unit),
                                normalized_value=_raw_value(displayed_value, displayed_unit),
                                original_text=(
                                    f"ClinicalTrials.gov {measurement_path}：{title}；"
                                    f"{groups[group_id]}；{_raw_value(value, unit)}"
                                ),
                            )
                        )
                        counts["efficacy"] += 1
                    else:
                        safety_term = _safety_term(category, title, class_title)
                        safety_category = (
                            "治疗期间不良事件" if category == "teae" else "严重不良事件"
                        )
                        numerator = None
                        denominator = None
                        displayed_value = value
                        displayed_unit = unit
                        if unit == "人" and group_id in denoms:
                            numerator = int(value)
                            denominator = denoms[group_id]
                            if numerator < 0 or numerator > denominator:
                                _issue_for_shape(
                                    issues,
                                    source_id=source_id,
                                    trial_id=trial_id,
                                    path=measurement_path,
                                    detail="受试者人数超出来源分母",
                                )
                                continue
                            displayed_value = round(numerator * 100 / denominator, 1)
                            displayed_unit = "%"
                        row_id = stable_id(
                            "a-rebuild-safety-row", source_id, measurement_path, category
                        )
                        row = {
                            "row_id": row_id,
                            "product_id": product_id,
                            "trial_id": trial_id,
                            "arm": arm,
                            "arm_detail": groups[group_id],
                            "category": safety_category,
                            "term": safety_term,
                            "value": displayed_value,
                            "numerator": numerator,
                            "denominator": denominator,
                            "unit": displayed_unit,
                            "time_window": timeframe,
                            "disclosure_state": "已公开",
                        }
                        rows.append(row)
                        fact_meta.append(
                            _fact_meta(
                                row_ref=f"safety:{row_id}",
                                fact_id=stable_id("a-rebuild-fact", source_id, row_id),
                                entity_id=product_id,
                                entity_type="drug",
                                canonical_name=safety_term,
                                field_id="result.safety",
                                source=source,
                                source_id=source_id,
                                source_path=measurement_path,
                                raw_value=_raw_value(value, unit),
                                normalized_value=_raw_value(displayed_value, displayed_unit),
                                original_text=(
                                    f"ClinicalTrials.gov {measurement_path}：{title}；"
                                    f"{groups[group_id]}；{_raw_value(value, unit)}"
                                ),
                            )
                        )
                        counts[category] += 1
    return rows, fact_meta, counts


def _explicit_aesi(event: Mapping[str, Any]) -> bool:
    for key in (
        "isAESI",
        "isAesi",
        "aesi",
        "AESI",
        "specialInterest",
        "eventCategory",
        "classification",
        "eventType",
        "category",
    ):
        marker = event.get(key)
        if marker is True:
            return True
        if isinstance(marker, str) and _text(marker).casefold() in {
            "aesi",
            "aes",
            "adverse events of special interest",
            "特别关注不良事件",
        }:
            return True
    return False


def _fact_meta(
    *,
    row_ref: str,
    fact_id: str,
    entity_id: str,
    entity_type: str,
    canonical_name: str,
    field_id: str,
    source: Mapping[str, Any],
    source_id: str,
    source_path: str,
    raw_value: str,
    normalized_value: str,
    original_text: str,
) -> dict[str, Any]:
    numeric_text = raw_value.removesuffix("%").strip()
    try:
        is_reported_zero = float(numeric_text) == 0.0
    except ValueError:
        is_reported_zero = False
    return {
        "fact_id": fact_id,
        "row_ref": row_ref,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "canonical_name": canonical_name,
        "field_id": field_id,
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "disclosure_state": "reported_zero" if is_reported_zero else "reported_value",
        "source_id": source_id,
        "locator": _locator(source, source_path),
        "original_text": original_text,
    }


CounterLike = dict[str, int]


def _event_rows(
    *,
    source: Mapping[str, Any],
    source_id: str,
    trial_id: str,
    product_id: str,
    product_name: str,
    issues: list[RebuildIssue],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], CounterLike]:
    rows: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    counts: CounterLike = defaultdict(int)
    try:
        results_section = _mapping(source["decoded"].get("resultsSection"), "resultsSection")
        module_value = results_section.get("adverseEventsModule")
        if module_value is None:
            return rows, facts, counts
        module = _mapping(module_value, "resultsSection.adverseEventsModule")
        groups_raw = _list(
            module.get("eventGroups", []),
            "resultsSection.adverseEventsModule.eventGroups",
        )
    except (TypeError, ValueError, KeyError) as exc:
        _issue_for_shape(
            issues,
            source_id=source_id,
            trial_id=trial_id,
            path="resultsSection.adverseEventsModule",
            detail=str(exc),
        )
        return rows, facts, counts

    group_info: dict[str, tuple[str, str]] = {}
    for group_index, raw_group in enumerate(groups_raw):
        path = f"resultsSection.adverseEventsModule.eventGroups[{group_index}]"
        try:
            group = _mapping(raw_group, path)
            group_id = _text(group.get("id"))
            title = _text(group.get("title"))
            if not group_id or not title:
                raise ValueError("事件组缺少标识或标题")
            group_info[group_id] = (title, _arm(title))
            for category, term, affected_key, at_risk_key in (
                ("sae", "任何SAE", "seriousNumAffected", "seriousNumAtRisk"),
                ("common_ae", "其他不良事件汇总", "otherNumAffected", "otherNumAtRisk"),
                ("teae", "任何TEAE", "teaeNumAffected", "teaeNumAtRisk"),
                ("teae", "任何TEAE", "anyTeaeNumAffected", "anyTeaeNumAtRisk"),
                ("teae", "任何TEAE", "anyTEAENumAffected", "anyTEAENumAtRisk"),
            ):
                affected = group.get(affected_key)
                at_risk = group.get(at_risk_key)
                if affected is None and at_risk is None:
                    continue
                value_path = f"{path}.{affected_key}"
                if affected is None or at_risk is None:
                    raise ValueError(f"{affected_key} 与 {at_risk_key} 必须同时存在")
                numerator = _integer(affected)
                denominator = _integer(at_risk)
                if denominator <= 0 or numerator < 0 or numerator > denominator:
                    raise ValueError("事件组分子/分母不符合范围")
                _append_safety_row(
                    rows=rows,
                    facts=facts,
                    counts=counts,
                    source=source,
                    source_id=source_id,
                    trial_id=trial_id,
                    product_id=product_id,
                    canonical_name=product_name,
                    category=cast(ResultKind, category),
                    term=term,
                    arm=group_info[group_id][1],
                    arm_detail=group_info[group_id][0],
                    value=round(numerator * 100 / denominator, 1),
                    numerator=numerator,
                    denominator=denominator,
                    unit="%",
                    time_window="登记结果报告期（来源未单列时间窗）",
                    source_path=value_path,
                    original_label=f"{group_info[group_id][0]}；{term}",
                )
        except (TypeError, ValueError, KeyError) as exc:
            _issue_for_shape(
                issues,
                source_id=source_id,
                trial_id=trial_id,
                path=path,
                detail=str(exc),
            )

    for event_field, category in (("seriousEvents", "sae"), ("otherEvents", "common_ae")):
        field_path = f"resultsSection.adverseEventsModule.{event_field}"
        try:
            events = _list(module.get(event_field, []), field_path)
        except ValueError as exc:
            _issue_for_shape(
                issues, source_id=source_id, trial_id=trial_id, path=field_path, detail=str(exc)
            )
            continue
        for event_index, raw_event in enumerate(events):
            event_path = f"{field_path}[{event_index}]"
            try:
                event = _mapping(raw_event, event_path)
                term = _text(event.get("term"))
                if not term:
                    raise ValueError("AE 缺少术语")
                stats = _list(event.get("stats", []), f"{event_path}.stats")
                if not stats:
                    raise ValueError("AE 缺少逐组统计")
                is_aesi = _explicit_aesi(event)
            except (TypeError, ValueError, KeyError) as exc:
                _issue_for_shape(
                    issues, source_id=source_id, trial_id=trial_id, path=event_path, detail=str(exc)
                )
                continue
            for stat_index, raw_stat in enumerate(stats):
                stat_path = f"{event_path}.stats[{stat_index}]"
                try:
                    stat = _mapping(raw_stat, stat_path)
                    group_id = _text(stat.get("groupId"))
                    if group_id not in group_info:
                        raise ValueError(f"事件组未定义：{group_id or '空值'}")
                    # ClinicalTrials.gov 的 JSON 省略值为 0 的整数标量；缺少
                    # numAffected 因而表示 0，不是“未公开”。分母为 0 的组别
                    # 没有可计算发生率，单独记为未报告，不能制造 0%。
                    numerator = _integer(stat.get("numAffected", 0))
                    denominator = _integer(stat.get("numAtRisk"))
                    if denominator == 0 and numerator == 0:
                        issues.append(
                            RebuildIssue(
                                "not_reported",
                                source_id,
                                trial_id,
                                stat_path,
                                "该事件组风险人数为 0，发生率不可计算，不以零值代替",
                            )
                        )
                        continue
                    if denominator <= 0 or numerator < 0 or numerator > denominator:
                        raise ValueError("AE 分子/分母不符合范围")
                except (TypeError, ValueError, KeyError) as exc:
                    _issue_for_shape(
                        issues,
                        source_id=source_id,
                        trial_id=trial_id,
                        path=stat_path,
                        detail=str(exc),
                    )
                    continue
                value = round(numerator * 100 / denominator, 1)
                _append_safety_row(
                    rows=rows,
                    facts=facts,
                    counts=counts,
                    source=source,
                    source_id=source_id,
                    trial_id=trial_id,
                    product_id=product_id,
                    canonical_name=product_name,
                    category=cast(ResultKind, category),
                    term=term,
                    arm=group_info[group_id][1],
                    arm_detail=group_info[group_id][0],
                    value=value,
                    numerator=numerator,
                    denominator=denominator,
                    unit="%",
                    time_window="登记结果报告期（来源未单列时间窗）",
                    source_path=stat_path,
                    original_label=f"{group_info[group_id][0]}；{term}",
                )
                if is_aesi:
                    _append_safety_row(
                        rows=rows,
                        facts=facts,
                        counts=counts,
                        source=source,
                        source_id=source_id,
                        trial_id=trial_id,
                        product_id=product_id,
                        canonical_name=product_name,
                        category="aesi",
                        term=term,
                        arm=group_info[group_id][1],
                        arm_detail=group_info[group_id][0],
                        value=value,
                        numerator=numerator,
                        denominator=denominator,
                        unit="%",
                        time_window="登记结果报告期（来源未单列时间窗）",
                        source_path=stat_path,
                        original_label=f"{group_info[group_id][0]}；明确 AESI；{term}",
                    )
    return rows, facts, counts


def _append_safety_row(
    *,
    rows: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    counts: CounterLike,
    source: Mapping[str, Any],
    source_id: str,
    trial_id: str,
    product_id: str,
    canonical_name: str,
    category: ResultKind,
    term: str,
    arm: str,
    arm_detail: str,
    value: float,
    numerator: int | None,
    denominator: int | None,
    unit: str,
    time_window: str,
    source_path: str,
    original_label: str,
) -> None:
    row_id = stable_id("a-rebuild-safety-row", source_id, source_path, category, term)
    row = {
        "row_id": row_id,
        "product_id": product_id,
        "trial_id": trial_id,
        "arm": arm,
        "arm_detail": arm_detail,
        "category": {
            "teae": "治疗期间不良事件",
            "sae": "严重不良事件",
            "aesi": "特别关注不良事件",
            "common_ae": "常见不良事件",
        }[category],
        "term": term,
        "value": value,
        "numerator": numerator,
        "denominator": denominator,
        "unit": unit,
        "time_window": time_window,
        "disclosure_state": "已公开",
    }
    rows.append(row)
    raw = _raw_value(value, unit)
    facts.append(
        _fact_meta(
            row_ref=f"safety:{row_id}",
            fact_id=stable_id("a-rebuild-fact", source_id, row_id),
            entity_id=product_id,
            entity_type="drug",
            canonical_name=canonical_name or term,
            field_id="result.safety",
            source=source,
            source_id=source_id,
            source_path=source_path,
            raw_value=raw,
            normalized_value=raw,
            original_text=f"ClinicalTrials.gov {source_path}：{original_label}；{raw}",
        )
    )
    counts[category] += 1


def _source_row_fact_sources(payload: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_fact in cast(Sequence[object], payload.get("facts", [])):
        if not isinstance(raw_fact, Mapping):
            continue
        row_ref = _text(raw_fact.get("row_ref"))
        source_id = _text(raw_fact.get("source_id"))
        if row_ref and source_id:
            result.setdefault(row_ref, source_id)
    return result


def _content_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "scientific_review"}


def _build_claims(
    *,
    original_claims: Sequence[object],
    retained_fact_ids: set[str],
    generated_facts: Sequence[Mapping[str, Any]],
    source_nct: Mapping[str, str],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for raw_claim in original_claims:
        if not isinstance(raw_claim, Mapping):
            continue
        fact_ids = tuple(
            fact_id
            for fact_id in cast(Sequence[object], raw_claim.get("fact_ids", []))
            if isinstance(fact_id, str)
        )
        if fact_ids and set(fact_ids) <= retained_fact_ids:
            claims.append(dict(raw_claim))
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fact in generated_facts:
        row_ref = _text(fact.get("row_ref"))
        fact_id = _text(fact.get("fact_id"))
        source_id = _text(fact.get("source_id"))
        if not row_ref or not fact_id or not source_id:
            continue
        category = "疗效" if row_ref.startswith("efficacy:") else "安全性"
        grouped[(source_id, category)].append(fact_id)
    for (source_id, category), group_fact_ids in sorted(grouped.items()):
        nct = source_nct.get(source_id, source_id)
        claims.append(
            {
                "claim_id": stable_id("a-rebuild-claim", source_id, category),
                "claim_text": (
                    f"ClinicalTrials.gov 登记来源 {nct} 的可解析{category}结果已按来源组别、"
                    "时间窗和原始数值重建。"
                ),
                "claim_kind": "direct_evidence",
                "fact_ids": sorted(group_fact_ids),
            }
        )
    claims.sort(key=lambda item: str(item.get("claim_id", "")))
    return claims


def rebuild_atopic_dermatitis_package(input_path: Path, output_dir: Path) -> RebuildResult:
    """从锁定包重建结果行、事实和声明，写出确定性候选内容。"""

    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    payload = _read_object(input_path)
    if _text(payload.get("indication")) != "特应性皮炎":
        raise RebuildError("重建器只接受适应症为特应性皮炎的研究包")
    report_raw = payload.get("report_data")
    if not isinstance(report_raw, Mapping):
        raise RebuildError("研究包缺少 report_data 对象")
    try:
        base_report = ReportAPortalData.model_validate(report_raw)
    except ValueError as exc:
        raise RebuildError(f"输入报告数据不符合 A 类合同：{exc}") from exc
    source_items = payload.get("sources")
    if not isinstance(source_items, list):
        raise RebuildError("研究包缺少 sources 列表")
    sources: dict[str, dict[str, Any]] = {}
    source_nct: dict[str, str] = {}
    issues: list[RebuildIssue] = []
    for raw_source in source_items:
        if not isinstance(raw_source, Mapping):
            raise RebuildError("来源条目必须是对象")
        source = dict(raw_source)
        source_id = _text(source.get("source_id"))
        if not source_id:
            raise RebuildError("来源条目缺少 source_id")
        if source_id in sources:
            raise RebuildError(f"来源标识重复：{source_id}")
        if source.get("source_type") != "clinical_trial_registry":
            sources[source_id] = source
            continue
        try:
            decoded_value = json.loads(_text(source.get("content_text")))
        except json.JSONDecodeError as exc:
            decoded_value = None
            issues.append(
                RebuildIssue(
                    "parse_failure",
                    source_id,
                    _nct(source.get("query_or_identifier")),
                    "content_text",
                    f"来源 JSON 无法解析：{exc.msg}",
                )
            )
        source["decoded"] = decoded_value if isinstance(decoded_value, Mapping) else {}
        sources[source_id] = source
        query_nct = _nct(source.get("query_or_identifier"))
        if query_nct:
            source_nct[source_id] = query_nct

    product_by_id = {row.id: row for row in base_report.products}
    trial_by_nct: dict[str, Any] = {}
    for trial in base_report.trials:
        for value in (trial.id, trial.display_id):
            nct = _nct(value)
            if nct:
                trial_by_nct[nct.casefold()] = trial

    row_sources = _source_row_fact_sources(payload)
    registry_with_results: set[str] = set()
    generated_rows: list[dict[str, Any]] = []
    generated_facts: list[dict[str, Any]] = []
    generated_counts: CounterLike = defaultdict(int)
    generated_categories: dict[str, set[str]] = defaultdict(set)
    source_result_counts: dict[str, CounterLike] = defaultdict(lambda: defaultdict(int))

    for source_id in sorted(sources):
        source = sources[source_id]
        if source.get("source_type") != "clinical_trial_registry":
            continue
        decoded = source.get("decoded")
        if not isinstance(decoded, Mapping) or "resultsSection" not in decoded:
            continue
        content_nct = None
        if isinstance(decoded.get("protocolSection"), Mapping):
            identification = decoded["protocolSection"].get("identificationModule")
            if isinstance(identification, Mapping):
                content_nct = _nct(identification.get("nctId"))
        nct = content_nct or source_nct.get(source_id)
        if nct is None or nct.casefold() not in trial_by_nct:
            issues.append(
                RebuildIssue(
                    "unmapped_source",
                    source_id,
                    None,
                    "protocolSection.identificationModule.nctId",
                    "来源含结果模块，但无法映射到报告试验，未猜测产品归属",
                )
            )
            continue
        trial = trial_by_nct[nct.casefold()]
        product = product_by_id[trial.product_id]
        registry_with_results.add(source_id)
        source_result_counts[source_id]
        outcome_rows, outcome_facts, outcome_counts = _outcome_rows(
            source=source,
            source_id=source_id,
            trial_id=trial.id,
            product_id=trial.product_id,
            trial_name=trial.name,
            issues=issues,
        )
        event_rows, event_facts, event_counts = _event_rows(
            source=source,
            source_id=source_id,
            trial_id=trial.id,
            product_id=trial.product_id,
            product_name=product.name,
            issues=issues,
        )
        for item in (*outcome_rows, *event_rows):
            generated_rows.append(item)
            category = (
                "efficacy"
                if "endpoint" in item
                else {
                    "治疗期间不良事件": "teae",
                    "严重不良事件": "sae",
                    "特别关注不良事件": "aesi",
                    "常见不良事件": "common_ae",
                }[str(item["category"])]
            )
            generated_categories[source_id].add(str(category))
        generated_facts.extend((*outcome_facts, *event_facts))
        for count_key, count_value in (*outcome_counts.items(), *event_counts.items()):
            generated_counts[count_key] += count_value
            source_result_counts[source_id][count_key] += count_value

    retained_efficacy: list[dict[str, Any]] = []
    for efficacy_row in base_report.efficacy:
        row = efficacy_row.model_dump(mode="json")
        source_for_row: str | None = row_sources.get(f"efficacy:{row['row_id']}")
        if source_for_row in registry_with_results and generated_categories.get(
            source_for_row, set()
        ) & {"efficacy"}:
            continue
        retained_efficacy.append(row)

    retained_safety: list[dict[str, Any]] = []
    for safety_row in base_report.safety:
        row = safety_row.model_dump(mode="json")
        source_for_row = row_sources.get(f"safety:{row['row_id']}")
        safety_category_kind: str | None = {
            "治疗期间不良事件": "teae",
            "严重不良事件": "sae",
            "特别关注不良事件": "aesi",
            "常见不良事件": "common_ae",
        }.get(str(row["category"]))
        if (
            source_for_row in registry_with_results
            and safety_category_kind is not None
            and safety_category_kind in generated_categories.get(source_for_row, set())
        ):
            continue
        retained_safety.append(row)

    generated_rows.sort(key=lambda row: str(row["row_id"]))
    generated_facts.sort(key=lambda fact: str(fact["fact_id"]))
    report_payload = base_report.model_dump(mode="json")
    report_payload["efficacy"] = [
        *retained_efficacy,
        *[row for row in generated_rows if "endpoint" in row],
    ]
    report_payload["safety"] = [
        *retained_safety,
        *[row for row in generated_rows if "category" in row],
    ]
    try:
        rebuilt_report = ReportAPortalData.model_validate(report_payload)
    except ValueError as exc:
        raise RebuildError(f"重建后的报告数据不符合 A 类合同：{exc}") from exc
    report_payload = rebuilt_report.model_dump(mode="json")

    original_facts = payload.get("facts", [])
    if not isinstance(original_facts, list):
        raise RebuildError("研究包缺少 facts 列表")
    kept_refs = {
        *(f"product:{row.id}" for row in base_report.products),
        *(f"trial:{row.id}" for row in base_report.trials),
        *(f"efficacy:{row['row_id']}" for row in report_payload["efficacy"]),
        *(f"safety:{row['row_id']}" for row in report_payload["safety"]),
    }
    generated_row_refs = {str(item["row_ref"]) for item in generated_facts}
    kept_facts = [
        dict(fact)
        for fact in original_facts
        if isinstance(fact, Mapping)
        and _text(fact.get("row_ref")) in kept_refs
        and _text(fact.get("row_ref")) not in generated_row_refs
    ]
    kept_facts.extend(generated_facts)
    kept_facts.sort(key=lambda fact: str(fact["fact_id"]))
    fact_ids = {str(fact["fact_id"]) for fact in kept_facts}
    original_claims = payload.get("claims", [])
    if not isinstance(original_claims, list):
        raise RebuildError("研究包缺少 claims 列表")
    claims = _build_claims(
        original_claims=original_claims,
        retained_fact_ids=fact_ids,
        generated_facts=generated_facts,
        source_nct=source_nct,
    )
    content = _content_payload(payload)
    content["report_data"] = report_payload
    content["facts"] = kept_facts
    content["claims"] = claims
    content.pop("scientific_review", None)
    try:
        coverage_audit = audit_clinicaltrials_result_coverage(
            rebuilt_report,
            tuple(SourceCapture.model_validate(item) for item in content["sources"]),
            facts=tuple(ResearchFact.model_validate(item) for item in kept_facts),
        )
    except ValueError as exc:
        raise RebuildError(f"重建后的结果覆盖审计无法执行：{exc}") from exc
    if not coverage_audit.passed:
        raise RebuildError(coverage_audit.error_message_zh)
    content_digest = _digest(content)
    input_digest = _sha256_file(input_path)
    try:
        input_label = input_path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        input_label = input_path.name
    source_inventory_digest = _digest(
        [
            {
                "source_id": source_id,
                "content_sha256": hashlib.sha256(
                    str(sources[source_id].get("content_text", "")).encode("utf-8")
                ).hexdigest(),
            }
            for source_id in sorted(sources)
        ]
    )
    counts = {
        "products": len(report_payload["products"]),
        "trials": len(report_payload["trials"]),
        "sources": len(content["sources"]),
        "facts": len(kept_facts),
        "claims": len(claims),
        "efficacy_rows": len(report_payload["efficacy"]),
        "safety_rows": len(report_payload["safety"]),
        "added_efficacy_rows": generated_counts.get("efficacy", 0),
        "added_teae_rows": generated_counts.get("teae", 0),
        "added_sae_rows": generated_counts.get("sae", 0),
        "added_aesi_rows": generated_counts.get("aesi", 0),
        "added_common_ae_rows": generated_counts.get("common_ae", 0),
        "not_reported_values": sum(issue.kind == "not_reported" for issue in issues),
        "parse_failures": sum(issue.kind == "parse_failure" for issue in issues),
        "unmapped_sources": sum(issue.kind == "unmapped_source" for issue in issues),
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "tool": "tools/rebuild_atopic_dermatitis_package.py",
        "input": {"path": input_label, "sha256": input_digest},
        "source_inventory_sha256": source_inventory_digest,
        "output": {
            "content_file": "research-content.json",
            "content_sha256": None,
            "content_digest": content_digest,
            "scientific_review": "未生成；需独立复核后再形成 research-package.json",
        },
        "counts": counts,
        "source_result_counts": {
            source_id: dict(source_result_counts[source_id])
            for source_id in sorted(source_result_counts)
        },
        "coverage": {
            "audited_trial_ids": list(coverage_audit.audited_trial_ids),
            "trial_status_counts": {
                status: sum(item.status == status for item in coverage_audit.trial_coverage)
                for status in sorted({item.status for item in coverage_audit.trial_coverage})
            },
            "trials": [
                {
                    "trial_id": item.trial_id,
                    "product_id": item.product_id,
                    "registry_source_ids": list(item.registry_source_ids),
                    "registry_sources_with_results": list(item.registry_sources_with_results),
                    "result_source_ids": list(item.result_source_ids),
                    "projected_efficacy_rows": item.projected_efficacy_rows,
                    "projected_safety_rows": item.projected_safety_rows,
                    "status": item.status,
                }
                for item in coverage_audit.trial_coverage
            ],
            "products": [
                {
                    "product_id": item.product_id,
                    "result_status": item.result_status,
                    "trial_ids": list(item.trial_ids),
                    "numeric_result_trial_ids": list(item.numeric_result_trial_ids),
                    "comparable_result_trial_ids": list(item.comparable_result_trial_ids),
                }
                for item in coverage_audit.product_coverage
            ],
        },
        "issues": [
            issue.as_dict()
            for issue in sorted(
                issues,
                key=lambda item: (item.kind, item.source_id, item.source_path),
            )
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    content_path = output_dir / "research-content.json"
    manifest_path = output_dir / "rebuild-manifest.json"
    _atomic_write(content_path, content)
    manifest["output"]["content_sha256"] = _sha256_file(content_path)
    _atomic_write(manifest_path, manifest)
    return RebuildResult(
        input_path=input_path,
        output_dir=output_dir,
        content_path=content_path,
        manifest_path=manifest_path,
        content_digest=content_digest,
        input_digest=input_digest,
        counts=counts,
        issues=tuple(issues),
    )


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从锁定来源包重建特应性皮炎 A 类结果内容（不联网）"
    )
    parser.add_argument("--input", type=Path, required=True, help="已锁定的 research-package.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="候选内容与重建清单输出目录")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = rebuild_atopic_dermatitis_package(args.input, args.output_dir)
    except RebuildError as exc:
        print(f"重建失败：{exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "content": str(result.content_path),
                "manifest": str(result.manifest_path),
                "content_digest": result.content_digest,
                "counts": dict(result.counts),
                "issue_count": len(result.issues),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
