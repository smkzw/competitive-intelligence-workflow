"""终点实例身份与逐实例时间配对（独立审阅 R05 / 验收 SCI06）。

角色（primary/secondary）不是实例键：同一试验的多条主要终点各自持有
outcome_id 与自己的评估时间。按"角色集合"检查会漏掉"两条主终点只有
一条时间点"的覆盖缺口；实例级检查要求每条终点定义都有配对的时间点，
且同名 outcome_id 不得携带互相矛盾的测量定义。
"""
from __future__ import annotations

from dataclasses import dataclass


class EndpointInstanceError(ValueError):
    """终点实例身份或终点—时间点配对不满足合同。"""


@dataclass(frozen=True)
class EndpointInstance:
    outcome_id: str
    role: str
    trial_id: str
    measure: str
    timepoint: str | None


def _family_of(observation) -> str:
    return str(getattr(observation, "field_family", "") or "")


def build_endpoint_instances(observations) -> tuple[EndpointInstance, ...]:
    """把携带 outcome_id 的终点/时间点观察折叠成实例列表。"""
    measures: dict[tuple[str, str], list] = {}
    times: dict[tuple[str, str], list] = {}
    for observation in observations:
        oid = getattr(observation, "outcome_id", None)
        if not oid:
            continue
        key = (str(observation.trial_id), str(oid))
        family = _family_of(observation)
        if family == "endpoint":
            measures.setdefault(key, []).append(observation)
        elif family == "timepoint":
            times.setdefault(key, []).append(observation)
    instances: list[EndpointInstance] = []
    for (trial_id, oid), rows in measures.items():
        role = str(rows[0].endpoint_key or "")
        measure = "；".join(
            " ".join(str(row.source_text).split()) for row in rows
        )
        tp_rows = times.pop((trial_id, oid), [])
        timepoint = "；".join(
            " ".join(str(row.source_text).split())
            for row in tp_rows
            if str(row.source_text or "").strip()
        ) or None
        instances.append(EndpointInstance(
            outcome_id=oid, role=role, trial_id=trial_id,
            measure=measure, timepoint=timepoint,
        ))
    return tuple(instances)


def validate_endpoint_timepoint_pairs(
    observations,
    *,
    universe_trial_ids=None,
) -> tuple[EndpointInstance, ...]:
    """逐实例检查终点—时间点配对；返回实例列表，违规抛 EndpointInstanceError。

    只处理携带 outcome_id 的观察；全无 outcome_id 的旧数据由调用方走
    兼容的角色集合检查（独立审阅 R04：未知与旧口径显式区分）。"""
    endpoint_ids: dict[str, dict[str, str]] = {}
    timepoint_ids: dict[str, set[str]] = {}
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
        trial_id = str(observation.trial_id)
        if family == "endpoint":
            text = " ".join(str(observation.source_text or "").split())
            seen = endpoint_ids.setdefault(trial_id, {})
            prior = seen.get(str(oid))
            if prior is not None and prior != text:
                raise EndpointInstanceError(
                    f"试验 {trial_id} 的终点实例 {oid} 携带互相矛盾的测量定义："
                    f"{prior!r} vs {text!r}"
                )
            seen[str(oid)] = text
        else:
            timepoint_ids.setdefault(trial_id, set()).add(str(oid))

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
                f"试验 {trial_id} 缺评估时间点的终点实例：{'、'.join(missing)}"
            )
        if orphan:
            problems.append(
                f"试验 {trial_id} 无对应终点的时间点实例：{'、'.join(orphan)}"
            )
    if problems:
        raise EndpointInstanceError("；".join(problems))
    return instances
