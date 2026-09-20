"""C 类设计事实模式、差异、异常点与多路径综合。

消费 Task 7.1 ``DesignObservation``，先析出有来源的模式/差异/异常点，再输出
至少两条由不同设计签名支撑的候选路径。路径身份对输入重排保持不变；不产生
排名、唯一推荐、产品特异建议或无原始值的归一化视图。
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import ConflictDisposition
from ci_workflow.reports.c.contracts import (
    DesignFieldFamily,
    DesignObservation,
    DesignObservationError,
    validate_design_observation,
)

_ACCEPTED_DISCLOSURE_STATES = frozenset(
    {
        FactDisclosureState.REPORTED_VALUE,
        FactDisclosureState.REPORTED_ZERO,
        FactDisclosureState.NOT_APPLICABLE,
    }
)

# 与 Task 7.1 门槛对齐的关键设计字段；未公开或未解决时失败关闭。
_CRITICAL_FIELDS: frozenset[tuple[DesignFieldFamily, str]] = frozenset(
    {
        (DesignFieldFamily.POPULATION, "target_population"),
        (DesignFieldFamily.GROUPING, "arm_randomization_blinding"),
        (DesignFieldFamily.ENDPOINT, "primary_endpoint_definition"),
        (DesignFieldFamily.TIMEPOINT, "primary_endpoint_timepoint"),
    }
)

# 进入设计签名的已公开事实字段（不含产品名）。
_SIGNATURE_FIELDS: tuple[tuple[DesignFieldFamily, str], ...] = (
    (DesignFieldFamily.POPULATION, "target_population"),
    (DesignFieldFamily.GROUPING, "arm_randomization_blinding"),
    (DesignFieldFamily.INTERVENTION, "experimental_arm"),
    (DesignFieldFamily.INTERVENTION, "control_arm"),
    (DesignFieldFamily.DOSE_SCHEDULE, "dosing_regimen"),
    (DesignFieldFamily.ENDPOINT, "primary_endpoint_definition"),
    (DesignFieldFamily.TIMEPOINT, "primary_endpoint_timepoint"),
    (DesignFieldFamily.OPERATIONAL, "visit_schedule"),
)

_FIELD_LABEL_ZH: dict[tuple[DesignFieldFamily, str], str] = {
    (DesignFieldFamily.POPULATION, "target_population"): "目标人群",
    (DesignFieldFamily.GROUPING, "arm_randomization_blinding"): "分组与盲法",
    (DesignFieldFamily.INTERVENTION, "experimental_arm"): "试验组干预",
    (DesignFieldFamily.INTERVENTION, "control_arm"): "对照组干预",
    (DesignFieldFamily.DOSE_SCHEDULE, "dosing_regimen"): "给药方案",
    (DesignFieldFamily.ENDPOINT, "primary_endpoint_definition"): "主要终点",
    (DesignFieldFamily.TIMEPOINT, "primary_endpoint_timepoint"): "主要终点时间点",
    (DesignFieldFamily.OPERATIONAL, "visit_schedule"): "访视安排",
}


class DesignSynthesisError(ValueError):
    """设计路径综合失败关闭：证据不足、关键事实阻断或不足两条签名。"""


class SourcedDesignFactItem(BaseModel):
    """有来源绑定的事实层条目（模式 / 差异 / 异常点）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    statement_zh: str
    observation_ids: tuple[str, ...]
    trial_ids: tuple[str, ...]

    @field_validator("item_id", "statement_zh")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("事实条目文本不能为空")
        return value

    @field_validator("observation_ids", "trial_ids")
    @classmethod
    def _non_empty_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        ids = tuple(part for part in value if isinstance(part, str) and part.strip())
        if not ids:
            raise ValueError("事实条目必须绑定身份")
        if len(ids) != len(set(ids)):
            raise ValueError("事实条目身份不得重复")
        return ids


class CandidateDesignPath(BaseModel):
    """一条有证据支撑的候选设计路径；不含排名语义。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path_id: str
    design_signature: str
    summary_zh: str
    assumptions_zh: str
    tradeoffs_zh: str
    observation_ids: tuple[str, ...]
    trial_ids: tuple[str, ...]

    @field_validator(
        "path_id",
        "design_signature",
        "summary_zh",
        "assumptions_zh",
        "tradeoffs_zh",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("候选路径文本不能为空")
        return value

    @field_validator("observation_ids", "trial_ids")
    @classmethod
    def _non_empty_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        ids = tuple(part for part in value if isinstance(part, str) and part.strip())
        if not ids:
            raise ValueError("候选路径必须绑定身份")
        if len(ids) != len(set(ids)):
            raise ValueError("候选路径身份不得重复")
        return ids


class DesignPathSynthesisResult(BaseModel):
    """事实层与路径综合层分离的综合结果。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    indication_id: str
    patterns: tuple[SourcedDesignFactItem, ...]
    differences: tuple[SourcedDesignFactItem, ...]
    outliers: tuple[SourcedDesignFactItem, ...]
    candidate_paths: tuple[CandidateDesignPath, ...]

    @field_validator("indication_id")
    @classmethod
    def _indication(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("适应症标识不能为空")
        return value.strip()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    punctuation_folded = "".join(
        " " if unicodedata.category(character).startswith("P") else character
        for character in normalized
    )
    return " ".join(punctuation_folded.casefold().split())


def _is_usable_fact(observation: DesignObservation) -> bool:
    return (
        observation.review_state is FactReviewState.ACCEPTED
        and observation.disclosure_state in _ACCEPTED_DISCLOSURE_STATES
        and observation.conflict_disposition
        is ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
    )


def _is_critical(observation: DesignObservation) -> bool:
    return (observation.field_family, observation.field) in _CRITICAL_FIELDS


def _is_undisclosed(observation: DesignObservation) -> bool:
    return observation.disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED


def _sorted_unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({item for item in values if item}))


def _signature_component_text(observation: DesignObservation) -> str:
    parts: list[str] = []
    if observation.field_family is DesignFieldFamily.GROUPING:
        if observation.randomization:
            parts.append(observation.randomization)
        if observation.blinding:
            parts.append(observation.blinding)
    if (
        observation.field_family is DesignFieldFamily.TIMEPOINT
        and observation.assessment_timepoint
    ):
        parts.append(observation.assessment_timepoint)
    if observation.field_family is DesignFieldFamily.ENDPOINT:
        parts.append(observation.source_field_name)
        parts.append(observation.source_field_definition)
    parts.append(observation.source_text)
    return _normalize_text(" | ".join(parts))


def _trial_signature_materials(
    observations: Sequence[DesignObservation],
) -> dict[tuple[str, str], str]:
    """按字段抽取试验设计签名材料；同字段多条时取观察身份字典序首条。"""

    by_field: dict[tuple[str, str], list[DesignObservation]] = defaultdict(list)
    for item in observations:
        if (item.field_family, item.field) not in _SIGNATURE_FIELDS:
            continue
        key = (item.field_family.value, item.field)
        by_field[key].append(item)

    materials: dict[tuple[str, str], str] = {}
    for key, rows in by_field.items():
        chosen = sorted(rows, key=lambda row: row.observation_id)[0]
        materials[key] = _signature_component_text(chosen)
    return materials


def _signature_key(
    materials: Mapping[tuple[str, str], str],
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (family, field, value)
            for (family, field), value in materials.items()
            if value
        )
    )


def _signature_identity(signature_key: tuple[tuple[str, str, str], ...]) -> str:
    if not signature_key:
        raise DesignSynthesisError("设计签名材料为空，无法形成候选路径。")
    parts = [f"{family}:{field}:{value}" for family, field, value in signature_key]
    return stable_id("c-design-signature", *parts)


def _path_identity(*, indication_id: str, signature_id: str) -> str:
    return stable_id("c-design-path", indication_id, signature_id)


def _label_for(family: str, field: str) -> str:
    try:
        enum_family = DesignFieldFamily(family)
    except ValueError:
        return field
    return _FIELD_LABEL_ZH.get((enum_family, field), field)


def _compact_clause(text: str, *, limit: int = 48) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _raise_insufficient(*, message: str) -> None:
    raise DesignSynthesisError(message)


def _validate_inputs(
    indication_id: str,
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> tuple[str, tuple[DesignObservation, ...]]:
    if not isinstance(indication_id, str) or not indication_id.strip():
        _raise_insufficient(message="缺少有效的适应症标识，无法综合候选设计路径。")
    indication = indication_id.strip()

    if not observations:
        _raise_insufficient(
            message=(
                "当前仅有适应症标识或缺少设计观察，证据不足，"
                "无法综合出至少两条候选设计路径。"
            )
        )

    validated: list[DesignObservation] = []
    try:
        for item in observations:
            validated.append(validate_design_observation(item))
    except (DesignObservationError, TypeError, ValueError) as error:
        raise DesignSynthesisError(
            f"设计观察输入不满足合同，无法继续路径综合：{error}"
        ) from error

    return indication, tuple(validated)


def _assert_no_blocked_criticals(observations: Sequence[DesignObservation]) -> None:
    undisclosed = [
        item for item in observations if _is_critical(item) and _is_undisclosed(item)
    ]
    if undisclosed:
        _raise_insufficient(
            message="关键设计事实尚未公开披露，证据不足，无法继续多路径综合。"
        )

    unresolved = [
        item
        for item in observations
        if _is_critical(item) and not _is_usable_fact(item) and not _is_undisclosed(item)
    ]
    if unresolved:
        _raise_insufficient(
            message=(
                "关键设计事实仍待审查确认尚未解决，证据不足，无法继续多路径综合。"
            )
        )


def _build_trial_bundles(
    usable: Sequence[DesignObservation],
) -> dict[str, tuple[DesignObservation, ...]]:
    by_trial: dict[str, list[DesignObservation]] = defaultdict(list)
    for item in usable:
        by_trial[item.trial_id].append(item)
    return {
        trial_id: tuple(sorted(rows, key=lambda row: row.observation_id))
        for trial_id, rows in by_trial.items()
    }


def _group_by_signature(
    trial_bundles: Mapping[str, Sequence[DesignObservation]],
) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for trial_id in sorted(trial_bundles):
        materials = _trial_signature_materials(trial_bundles[trial_id])
        required = {
            ("population", "target_population"),
            ("intervention", "experimental_arm"),
            ("endpoint", "primary_endpoint_definition"),
            ("timepoint", "primary_endpoint_timepoint"),
        }
        if not required.issubset(materials):
            continue
        key = _signature_key(materials)
        signature_id = _signature_identity(key)
        bucket = groups.setdefault(
            signature_id,
            {
                "signature_id": signature_id,
                "signature_key": key,
                "materials": dict(materials),
                "trial_ids": [],
                "observation_ids": [],
            },
        )
        bucket["trial_ids"].append(trial_id)
        bucket["observation_ids"].extend(
            item.observation_id for item in trial_bundles[trial_id]
        )

    for bucket in groups.values():
        bucket["trial_ids"] = list(_sorted_unique(bucket["trial_ids"]))
        bucket["observation_ids"] = list(_sorted_unique(bucket["observation_ids"]))
    return groups


def _describe_signature(materials: Mapping[tuple[str, str], str]) -> str:
    intervention = materials.get(("intervention", "experimental_arm"), "未命名干预")
    control = materials.get(("intervention", "control_arm"), "未说明对照")
    endpoint = materials.get(("endpoint", "primary_endpoint_definition"), "未说明终点")
    timepoint = materials.get(("timepoint", "primary_endpoint_timepoint"), "未说明时间点")
    grouping = materials.get(("grouping", "arm_randomization_blinding"), "未说明分组")
    return (
        f"以{_compact_clause(intervention, limit=36)}为试验干预，"
        f"对照为{_compact_clause(control, limit=28)}，"
        f"主要终点关注{_compact_clause(endpoint, limit=36)}，"
        f"评估时间点为{_compact_clause(timepoint, limit=20)}；"
        f"分组安排为{_compact_clause(grouping, limit=28)}。"
    )


def _build_paths(
    *,
    indication_id: str,
    multi_trial_groups: Sequence[Mapping[str, Any]],
    all_multi_materials: Sequence[Mapping[tuple[str, str], str]],
) -> tuple[CandidateDesignPath, ...]:
    paths: list[CandidateDesignPath] = []
    for group in multi_trial_groups:
        materials: dict[tuple[str, str], str] = dict(group["materials"])
        signature_id = str(group["signature_id"])
        peer_materials = [other for other in all_multi_materials if other != materials]
        difference_notes: list[str] = []
        for peer in peer_materials:
            for field_key, value in sorted(materials.items()):
                peer_value = peer.get(field_key)
                if peer_value and peer_value != value:
                    label = _label_for(field_key[0], field_key[1])
                    difference_notes.append(
                        f"{label}采用{_compact_clause(value, limit=28)}，"
                        f"而另一路径为{_compact_clause(peer_value, limit=28)}"
                    )
        unique_notes = list(dict.fromkeys(difference_notes))
        if unique_notes:
            assumptions = (
                "该路径适用前提来自支撑试验已公开的共同设计安排："
                + "；".join(unique_notes[:4])
                + "。"
            )
            tradeoffs = (
                "与其他候选路径相比，主要权衡体现在已公开差异："
                + "；".join(unique_notes[:4])
                + "。以上仅为设计事实对照，不表示优劣。"
            )
        else:
            assumptions = (
                "该路径适用前提为支撑试验已公开的共同人群、干预对照、"
                "终点与时间点安排。"
            )
            tradeoffs = (
                "当前可见的其他候选路径与本路径在公开设计事实上高度接近；"
                "仍保留为独立证据路径，不表示先后次序。"
            )

        paths.append(
            CandidateDesignPath(
                path_id=_path_identity(
                    indication_id=indication_id,
                    signature_id=signature_id,
                ),
                design_signature=signature_id,
                summary_zh=_describe_signature(materials),
                assumptions_zh=assumptions,
                tradeoffs_zh=tradeoffs,
                observation_ids=tuple(group["observation_ids"]),
                trial_ids=tuple(group["trial_ids"]),
            )
        )

    return tuple(sorted(paths, key=lambda path: path.path_id))


def _build_patterns(
    multi_trial_groups: Sequence[Mapping[str, Any]],
) -> tuple[SourcedDesignFactItem, ...]:
    patterns: list[SourcedDesignFactItem] = []
    for group in multi_trial_groups:
        materials: dict[tuple[str, str], str] = dict(group["materials"])
        trial_ids = tuple(group["trial_ids"])
        observation_ids = tuple(group["observation_ids"])
        statement = (
            f"共有 {len(trial_ids)} 项试验呈现相同设计安排："
            f"{_describe_signature(materials)}"
        )
        item_id = stable_id(
            "c-design-pattern",
            str(group["signature_id"]),
            *trial_ids,
        )
        patterns.append(
            SourcedDesignFactItem(
                item_id=item_id,
                statement_zh=statement,
                observation_ids=observation_ids,
                trial_ids=trial_ids,
            )
        )
    return tuple(sorted(patterns, key=lambda item: item.item_id))


def _build_differences(
    multi_trial_groups: Sequence[Mapping[str, Any]],
) -> tuple[SourcedDesignFactItem, ...]:
    differences: list[SourcedDesignFactItem] = []
    groups = list(multi_trial_groups)
    for index, left in enumerate(groups):
        for right in groups[index + 1 :]:
            left_materials: dict[tuple[str, str], str] = dict(left["materials"])
            right_materials: dict[tuple[str, str], str] = dict(right["materials"])
            field_keys = sorted(set(left_materials) | set(right_materials))
            for field_key in field_keys:
                left_value = left_materials.get(field_key)
                right_value = right_materials.get(field_key)
                if not left_value or not right_value or left_value == right_value:
                    continue
                label = _label_for(field_key[0], field_key[1])
                trial_ids = _sorted_unique([*left["trial_ids"], *right["trial_ids"]])
                observation_ids = _sorted_unique(
                    [*left["observation_ids"], *right["observation_ids"]]
                )
                statement = (
                    f"在{label}上存在重要差异："
                    f"一组试验为{_compact_clause(left_value, limit=40)}；"
                    f"另一组试验为{_compact_clause(right_value, limit=40)}。"
                )
                item_id = stable_id(
                    "c-design-difference",
                    field_key[0],
                    field_key[1],
                    left_value,
                    right_value,
                    *trial_ids,
                )
                differences.append(
                    SourcedDesignFactItem(
                        item_id=item_id,
                        statement_zh=statement,
                        observation_ids=observation_ids,
                        trial_ids=trial_ids,
                    )
                )
    return tuple(sorted(differences, key=lambda item: item.item_id))


def _build_outliers(
    *,
    single_trial_groups: Sequence[Mapping[str, Any]],
    multi_trial_groups: Sequence[Mapping[str, Any]],
) -> tuple[SourcedDesignFactItem, ...]:
    if not multi_trial_groups:
        return ()

    outliers: list[SourcedDesignFactItem] = []
    common_field_values: dict[tuple[str, str], set[str]] = defaultdict(set)
    for group in multi_trial_groups:
        materials: dict[tuple[str, str], str] = dict(group["materials"])
        for field_key, value in materials.items():
            common_field_values[field_key].add(value)

    for group in single_trial_groups:
        materials = dict(group["materials"])
        divergences: list[str] = []
        for field_key, value in sorted(materials.items()):
            common_values = common_field_values.get(field_key, set())
            if common_values and value not in common_values:
                label = _label_for(field_key[0], field_key[1])
                divergences.append(
                    f"{label}为{_compact_clause(value, limit=36)}，"
                    f"与多试验共同安排不同"
                )
        if not divergences:
            divergences.append("整体设计签名仅见于单项试验，未形成共同模式")

        trial_ids = tuple(group["trial_ids"])
        observation_ids = tuple(group["observation_ids"])
        statement = (
            "异常点：试验设计偏离共同模式——"
            + "；".join(divergences[:4])
            + "。此为事实差异标记，不表示优劣判断。"
        )
        item_id = stable_id(
            "c-design-outlier",
            str(group["signature_id"]),
            *trial_ids,
        )
        outliers.append(
            SourcedDesignFactItem(
                item_id=item_id,
                statement_zh=statement,
                observation_ids=observation_ids,
                trial_ids=trial_ids,
            )
        )
    return tuple(sorted(outliers, key=lambda item: item.item_id))


def synthesize_design_paths(
    indication_id: str,
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> DesignPathSynthesisResult:
    """综合适应症下的设计观察，输出事实层与至少两条候选路径。

    输入重排不改变路径身份、绑定与用户可见文本。证据不足以支撑两条不同
    设计签名、或关键事实未公开/未解决时失败关闭。
    """

    indication, validated = _validate_inputs(indication_id, observations)
    _assert_no_blocked_criticals(validated)

    usable = tuple(item for item in validated if _is_usable_fact(item))
    if not usable:
        _raise_insufficient(
            message="缺少已接受且已公开的设计观察，证据不足，无法综合候选设计路径。"
        )

    trial_bundles = _build_trial_bundles(usable)
    groups = _group_by_signature(trial_bundles)
    if not groups:
        _raise_insufficient(
            message="已公开设计观察不足以形成设计签名，无法综合候选设计路径。"
        )

    multi_trial_groups = [
        group for group in groups.values() if len(group["trial_ids"]) >= 2
    ]
    single_trial_groups = [
        group for group in groups.values() if len(group["trial_ids"]) == 1
    ]
    multi_trial_groups = sorted(
        multi_trial_groups, key=lambda group: str(group["signature_id"])
    )
    single_trial_groups = sorted(
        single_trial_groups, key=lambda group: str(group["signature_id"])
    )

    if len(multi_trial_groups) < 2:
        if len(multi_trial_groups) == 1:
            _raise_insufficient(
                message=(
                    "现有已公开设计观察仅支撑一条独立设计签名，证据不足，"
                    "无法形成至少两条候选路径，停止综合。"
                )
            )
        _raise_insufficient(
            message=(
                "现有已公开设计观察未能形成至少两条由多项试验支撑的设计签名，"
                "证据不足，无法综合候选设计路径。"
            )
        )

    all_multi_materials = [dict(group["materials"]) for group in multi_trial_groups]
    patterns = _build_patterns(multi_trial_groups)
    differences = _build_differences(multi_trial_groups)
    outliers = _build_outliers(
        single_trial_groups=single_trial_groups,
        multi_trial_groups=multi_trial_groups,
    )
    paths = _build_paths(
        indication_id=indication,
        multi_trial_groups=multi_trial_groups,
        all_multi_materials=all_multi_materials,
    )

    if len(paths) < 2:
        _raise_insufficient(
            message="综合结果不足两条有证据候选路径，证据不足，停止综合。"
        )

    return DesignPathSynthesisResult(
        indication_id=indication,
        patterns=patterns,
        differences=differences,
        outliers=outliers,
        candidate_paths=paths,
    )


__all__ = [
    "CandidateDesignPath",
    "DesignPathSynthesisResult",
    "DesignSynthesisError",
    "SourcedDesignFactItem",
    "synthesize_design_paths",
]
