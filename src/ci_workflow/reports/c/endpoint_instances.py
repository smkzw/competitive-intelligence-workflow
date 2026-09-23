"""终点实例身份与逐实例时间配对（独立审阅 R05 / 验收 SCI06）。

角色（primary/secondary）不是实例键：同一试验的多条主要终点各自持有
outcome_id 与自己的评估时间。按"角色集合"检查会漏掉"两条主终点只有
一条时间点"的覆盖缺口；实例级检查要求每条终点定义都有配对的时间点，
且同名 outcome_id 不得携带互相矛盾的测量定义。
"""
from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from ci_workflow.reports.c.contracts import DesignObservation


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
    period: str
    window: str
    source_version_id: str


def _family_of(observation: DesignObservation) -> str:
    return str(getattr(observation, "field_family", "") or "")


def _identity(observation: DesignObservation) -> tuple[str, ...]:
    return (
        str(getattr(observation, "trial_id", "") or ""),
        str(getattr(observation, "outcome_id", "") or ""),
        str(getattr(observation, "endpoint_key", "") or ""),
        str(getattr(observation, "group_id", "") or ""),
        str(getattr(observation, "cohort_id", "") or ""),
        str(getattr(observation, "period", "") or ""),
        str(getattr(observation, "assessment_timepoint", "") or ""),
    )


def build_endpoint_instances(
    observations: Sequence[DesignObservation],
) -> tuple[EndpointInstance, ...]:
    """把携带 outcome_id 的终点/时间点观察折叠成实例列表。"""
    measures: dict[tuple[str, ...], list[DesignObservation]] = {}
    times: dict[tuple[str, ...], list[DesignObservation]] = {}
    for observation in observations:
        oid = getattr(observation, "outcome_id", None)
        if not oid:
            continue
        key = _identity(observation)
        family = _family_of(observation)
        if family == "endpoint":
            measures.setdefault(key, []).append(observation)
        elif family == "timepoint":
            times.setdefault(key, []).append(observation)
    instances: list[EndpointInstance] = []
    for key, rows in measures.items():
        trial_id, oid, role, group_id, cohort_id, period, window = key
        measure = "；".join(
            " ".join(str(row.source_text).split()) for row in rows
        )
        tp_rows = times.pop(key, [])
        timepoint = "；".join(
            " ".join(str(row.source_text).split())
            for row in tp_rows
            if str(row.source_text or "").strip()
        ) or None
        instances.append(EndpointInstance(
            outcome_id=oid, role=role, trial_id=trial_id,
            measure=measure, timepoint=timepoint,
            group_id=group_id, cohort_id=cohort_id, period=period,
            window=window, source_version_id=str(rows[0].source_version_id),
        ))
    return tuple(instances)


def validate_endpoint_timepoint_pairs(
    observations: Sequence[DesignObservation],
    *,
    universe_trial_ids: Collection[str] | None = None,
) -> tuple[EndpointInstance, ...]:
    """逐实例检查终点—时间点配对；返回实例列表，违规抛 EndpointInstanceError。

    只处理携带 outcome_id 的观察；全无 outcome_id 的旧数据由调用方走
    兼容的角色集合检查（独立审阅 R04：未知与旧口径显式区分）。"""
    endpoint_ids: dict[str, dict[tuple[str, ...], str]] = {}
    timepoint_ids: dict[str, set[tuple[str, ...]]] = {}
    for observation in observations:
        family = _family_of(observation)
        if family not in {"endpoint", "timepoint"}:
            continue
        oid = getattr(observation, "outcome_id", None)
        if not oid:
            raise EndpointInstanceError(
                f"观察 {observation.row_id} 缺少 outcome_id 实例标识；"
                "实例级配对要求终点与时间点逐条携带 outcome_id"
            )
        identity = _identity(observation)
        required_labels = (
            "trial_id", "outcome_id", "endpoint_role", "group_id", "cohort_id",
            "period", "window",
        )
        missing_axes = [
            label for label, value in zip(required_labels, identity, strict=True) if not value
        ]
        if missing_axes:
            raise EndpointInstanceError(
                f"观察 {observation.row_id} 的终点实例身份不完整：{','.join(missing_axes)}"
            )
        trial_id = str(observation.trial_id)
        identity = identity[1:]
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
    for trial_id, ids in endpoint_ids.items():
        if universe_trial_ids is not None and trial_id not in universe_trial_ids:
            continue
        tps = timepoint_ids.get(trial_id, set())
        missing = sorted(set(ids) - tps)
        orphan = sorted(tps - set(ids))
        if missing:
            problems.append(
                f"试验 {trial_id} 缺评估时间点的终点实例：{'、'.join(item[0] for item in missing)}"
            )
        if orphan:
            problems.append(
                f"试验 {trial_id} 无对应终点的时间点实例：{'、'.join(item[0] for item in orphan)}"
            )
    # 会商 F07/E06：孤儿检验补反向迭代域——只有时间点、没有终点的试验
    # 同样必须报错（此前只在"该试验同时有终点"时可达）
    for trial_id, tps in timepoint_ids.items():
        if universe_trial_ids is not None and trial_id not in universe_trial_ids:
            continue
        if not endpoint_ids.get(trial_id):
            problems.append(
                f"试验 {trial_id} 只有时间点实例而无终点实例："
                f"{'、'.join(item[0] for item in sorted(tps))}"
            )
    if universe_trial_ids is not None:
        for trial_id in sorted(str(item) for item in universe_trial_ids):
            if not endpoint_ids.get(trial_id):
                problems.append(f"试验 {trial_id} 缺少终点实例覆盖")
    if problems:
        raise EndpointInstanceError("；".join(problems))
    return instances
