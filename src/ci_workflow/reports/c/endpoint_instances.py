"""终点实例身份与逐实例时间配对（独立审阅 R05 / 验收 SCI06）。

角色（primary/secondary）不是实例键：同一试验的多条主要终点各自持有
outcome_id 与自己的评估时间。按"角色集合"检查会漏掉"两条主终点只有
一条时间点"的覆盖缺口；实例级检查要求每条终点定义都有配对的时间点，
且同名 outcome_id 不得携带互相矛盾的测量定义。
"""
from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from ci_workflow.reports.c.contracts import DesignObservation
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    extract_locator_quote,
    source_json_decoder,
)


class EndpointInstanceError(ValueError):
    """终点实例身份或终点—时间点配对不满足合同。"""


@dataclass(frozen=True)
class EndpointInstance:
    outcome_id: str
    role: str
    trial_id: str
    measure: str
    timepoint: str | None
    group_id: str
    cohort_id: str
    period: str | None
    window: str
    source_version_id: str
    product_id: str | None


def _family_of(observation: DesignObservation) -> str:
    return str(getattr(observation, "field_family", "") or "")


def _product_identity_axis(observation: DesignObservation) -> str | None:
    """Preserve explicit None; distinguish missing/empty from unknown product."""

    if not hasattr(observation, "product_id"):
        raise EndpointInstanceError("终点实例缺少 product_id；必须明确已知或 null")
    value = observation.product_id
    if value is None:
        return None
    if not isinstance(value, str):
        raise EndpointInstanceError("终点实例 product_id 必须为文本或明确 null")
    normalized = value.strip()
    if not normalized:
        raise EndpointInstanceError("终点实例 product_id 不能为空文本")
    return normalized


_PROTOCOL_OUTCOME = re.compile(
    r"(?P<parent>\$\.protocolSection\.outcomesModule\."
    r"(?P<collection>primaryOutcomes|secondaryOutcomes)\[(?P<index>0|[1-9][0-9]*)\])"
    r"\.(?P<field>measure|description|timeFrame)\Z"
)


def _is_description(observation: DesignObservation) -> bool:
    return getattr(observation, "field", None) in {
        "primary_endpoint_description", "secondary_endpoint_description",
    }


def _protocol_parent(observation: DesignObservation) -> str:
    locator = getattr(observation, "source_locator", None)
    match = _PROTOCOL_OUTCOME.fullmatch(str(getattr(locator, "field_path", "") or ""))
    return match["parent"] if match else ""


def _has_source_backed_protocol_context(
    observation: DesignObservation, protocol_sources: Mapping[str, str],
) -> bool:
    """A protocol outcome has a window but need not have a results-period field.

    This exception requires re-extractable source bytes, not a caller's boolean
    or a fabricated period. It is only protocol design identity, never permission
    to merge results across populations, periods, sources or numeric frames.
    """
    locator = getattr(observation, "source_locator", None)
    match = _PROTOCOL_OUTCOME.fullmatch(str(getattr(locator, "field_path", "") or ""))
    if (locator is None or match is None
            or str(getattr(observation, "source_role", "")) != "clinical_trial_registry"):
        return False
    if observation.period is not None:
        raise EndpointInstanceError(
            f"观察 {observation.row_id} 的登记方案未公开期别，不得填造 period"
        )
    content = protocol_sources.get(observation.source_version_id)
    if content is None:
        raise EndpointInstanceError(f"观察 {observation.row_id} 缺少同版本登记来源字节")
    expected_field = (
        "description" if _is_description(observation)
        else "measure" if _family_of(observation) == "endpoint" else "timeFrame"
    )
    role = "primary" if match["collection"] == "primaryOutcomes" else "secondary"
    if (match["field"] != expected_field
            or observation.endpoint_key not in {role, f"{role}_endpoint"}):
        raise EndpointInstanceError(f"观察 {observation.row_id} 的登记定位与终点角色不一致")
    try:
        record = source_json_decoder().decode(content)
        nct = record["protocolSection"]["identificationModule"]["nctId"]
        if str(observation.trial_id).casefold() != str(nct).casefold():
            raise ValueError("登记来源研究与实例 trial_id 不一致")
        url = urlsplit(str(locator.url or ""))
        if (url.scheme != "https" or url.netloc != "clinicaltrials.gov"
                or url.path != f"/study/{nct}" or url.query or url.fragment):
            raise ValueError("登记定位链接与来源研究不一致")
        short = "pri" if role == "primary" else "sec"
        if observation.outcome_id != f"outcome-{observation.trial_id}-{short}-{match['index']}":
            raise ValueError("登记 outcome_id 与原始终点父级索引不一致")
        if (observation.group_id != f"group-{observation.trial_id}-all"
                or observation.cohort_id != f"cohort-{observation.trial_id}-all"):
            raise ValueError("登记方案终点是研究级定义，不能补造组别或队列归属")
        quote = extract_locator_quote(content, media_type="application/json", locator=locator)
        window = extract_locator_quote(
            content, media_type="application/json",
            locator=locator.model_copy(update={"field_path": match["parent"] + ".timeFrame"}),
        )
        if observation.source_text.strip() != quote.strip() or not window.strip():
            raise ValueError("终点或时间窗原文与精确定位不一致")
        if str(observation.assessment_timepoint or "").strip() != window.strip():
            raise ValueError("终点身份时间窗与来源不一致")
    except (SourceDerivationError, KeyError, TypeError, ValueError) as error:
        raise EndpointInstanceError(
            f"观察 {observation.row_id} 的登记实例证据不闭合：{error}"
        ) from error
    return True


def _identity(observation: DesignObservation) -> tuple[str | None, ...]:
    return (
        str(getattr(observation, "trial_id", "") or ""),
        str(getattr(observation, "outcome_id", "") or ""),
        str(getattr(observation, "endpoint_key", "") or ""),
        str(getattr(observation, "group_id", "") or ""),
        str(getattr(observation, "cohort_id", "") or ""),
        str(getattr(observation, "period", "") or ""),
        str(getattr(observation, "assessment_timepoint", "") or ""),
        str(getattr(observation, "source_version_id", "") or ""),
        _protocol_parent(observation),
        _product_identity_axis(observation),
    )


def _axis_is_missing(label: str, value: object) -> bool:
    if label == "product_id":
        if value is None:
            return False
        return not str(value).strip()
    if not isinstance(value, str):
        return True
    return not value.strip()


def build_endpoint_instances(
    observations: Sequence[DesignObservation],
) -> tuple[EndpointInstance, ...]:
    """把携带 outcome_id 的终点/时间点观察折叠成实例列表。"""
    measures: dict[tuple[str | None, ...], list[DesignObservation]] = {}
    times: dict[tuple[str | None, ...], list[DesignObservation]] = {}
    for observation in observations:
        oid = getattr(observation, "outcome_id", None)
        if not oid or _is_description(observation):
            continue
        key = _identity(observation)
        family = _family_of(observation)
        if family == "endpoint":
            measures.setdefault(key, []).append(observation)
        elif family == "timepoint":
            times.setdefault(key, []).append(observation)
    instances: list[EndpointInstance] = []
    for key, rows in measures.items():
        (trial_id, oid, role, group_id, cohort_id, period, window,
         source_version, _parent, product) = key
        tp_rows = times.pop(key, [])
        if len(rows) != 1 or len(tp_rows) > 1:
            raise EndpointInstanceError(
                f"试验 {trial_id} 的终点实例 {oid} 重复，不能拼接原文掩盖冲突"
            )
        measure = "；".join(
            " ".join(str(row.source_text).split()) for row in rows
        )
        timepoint = "；".join(
            " ".join(str(row.source_text).split())
            for row in tp_rows
            if str(row.source_text or "").strip()
        ) or None
        if product == "":
            raise EndpointInstanceError(
                f"试验 {trial_id} 的终点实例 {oid} 缺少明确产品标识"
            )
        product_id = None if product is None else str(product)
        instances.append(EndpointInstance(
            outcome_id=str(oid), role=str(role), trial_id=str(trial_id),
            measure=measure, timepoint=timepoint,
            group_id=str(group_id), cohort_id=str(cohort_id),
            period=str(period) if period else None,
            window=str(window), source_version_id=str(source_version),
            product_id=product_id,
        ))
    return tuple(instances)


def validate_endpoint_timepoint_pairs(
    observations: Sequence[DesignObservation],
    *,
    universe_trial_ids: Collection[str] | None = None,
    protocol_sources: Mapping[str, str] | None = None,
) -> tuple[EndpointInstance, ...]:
    """逐实例检查终点—时间点配对；返回实例列表，违规抛 EndpointInstanceError。

    只处理携带 outcome_id 的观察；全无 outcome_id 的旧数据由调用方走
    兼容的角色集合检查（独立审阅 R04：未知与旧口径显式区分）。"""
    endpoint_ids: dict[str, dict[tuple[str | None, ...], str]] = {}
    timepoint_ids: dict[str, set[tuple[str | None, ...]]] = {}
    description_ids: dict[str, set[tuple[str | None, ...]]] = {}
    for observation in observations:
        family = _family_of(observation)
        if family not in {"endpoint", "timepoint"}:
            continue
        if universe_trial_ids is not None and observation.trial_id not in universe_trial_ids:
            raise EndpointInstanceError(f"观察 {observation.row_id} 的研究不在声明 universe 内")
        oid = getattr(observation, "outcome_id", None)
        if not oid:
            raise EndpointInstanceError(
                f"观察 {observation.row_id} 缺少 outcome_id 实例标识；"
                "实例级配对要求终点与时间点逐条携带 outcome_id"
            )
        identity = _identity(observation)
        protocol_proven = (
            _has_source_backed_protocol_context(observation, protocol_sources)
            if protocol_sources is not None else False
        )
        required_labels = (
            "trial_id", "outcome_id", "endpoint_role", "group_id", "cohort_id",
            "period", "window", "source_version_id", "protocol_parent", "product_id",
        )
        missing_axes = [
            label for label, value in zip(required_labels, identity, strict=True)
            if label != "protocol_parent"
            and not (label == "period" and protocol_proven)
            and _axis_is_missing(label, value)
        ]
        if missing_axes:
            raise EndpointInstanceError(
                f"观察 {observation.row_id} 的终点实例身份不完整：{','.join(missing_axes)}"
            )
        trial_id = str(observation.trial_id)
        identity = identity[1:]
        if _is_description(observation):
            if not protocol_proven:
                raise EndpointInstanceError(
                    f"观察 {observation.row_id} 的完整定义缺少精确登记来源证明"
                )
            seen_descriptions = description_ids.setdefault(trial_id, set())
            if identity in seen_descriptions:
                raise EndpointInstanceError(f"终点完整定义重复：{observation.outcome_id}")
            seen_descriptions.add(identity)
            continue
        if family == "endpoint":
            text = " ".join(str(observation.source_text or "").split())
            seen = endpoint_ids.setdefault(trial_id, {})
            prior = seen.get(identity)
            if prior is not None and prior != text:
                raise EndpointInstanceError(
                    f"试验 {trial_id} 的终点实例 {oid} 携带互相矛盾的测量定义："
                    f"{prior!r} vs {text!r}"
                )
            seen[identity] = text
        elif family == "timepoint":
            # 会商 F07/E05：配对判据是内容非空的配对，空白时间点不得冒充已配对
            if not str(observation.source_text or "").strip():
                raise EndpointInstanceError(
                    f"试验 {trial_id} 的终点实例 {oid} 的时间点观察为空白，"
                    "不得作为已配对时间点"
                )
            timepoint_ids.setdefault(trial_id, set()).add(identity)

    instances = build_endpoint_instances(observations)
    problems: list[str] = []
    for trial_id, descriptions in description_ids.items():
        if descriptions - set(endpoint_ids.get(trial_id, {})):
            problems.append(f"试验 {trial_id} 的完整定义没有同父级终点标题")
    for trial_id, ids in endpoint_ids.items():
        tps = timepoint_ids.get(trial_id, set())
        missing = sorted(set(ids) - tps, key=_identity_sort_key)
        orphan = sorted(tps - set(ids), key=_identity_sort_key)
        if missing:
            problems.append(
                f"试验 {trial_id} 缺评估时间点的终点实例："
                + '、'.join(str(item[0]) for item in missing)
            )
        if orphan:
            problems.append(
                f"试验 {trial_id} 无对应终点的时间点实例："
                + '、'.join(str(item[0]) for item in orphan)
            )
    # 会商 F07/E06：孤儿检验补反向迭代域——只有时间点、没有终点的试验
    # 同样必须报错（此前只在"该试验同时有终点"时可达）
    for trial_id, tps in timepoint_ids.items():
        if not endpoint_ids.get(trial_id):
            problems.append(
                f"试验 {trial_id} 只有时间点实例而无终点实例："
                f"{'、'.join(str(item[0]) for item in sorted(tps, key=_identity_sort_key))}"
            )
    if universe_trial_ids is not None:
        for trial_id in sorted(str(item) for item in universe_trial_ids):
            if not endpoint_ids.get(trial_id):
                problems.append(f"试验 {trial_id} 缺少终点实例覆盖")
    if problems:
        raise EndpointInstanceError("；".join(problems))
    return instances


def _identity_sort_key(identity: tuple[str | None, ...]) -> tuple[tuple[bool, str], ...]:
    """Diagnostic ordering only; no placeholder is stored in scientific identity."""
    return tuple((value is not None, value or "") for value in identity)
