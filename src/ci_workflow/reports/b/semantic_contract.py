"""Deterministic clinical-construct compatibility and B bubble presets."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from functools import lru_cache
from typing import Any, Literal, Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.reports.b.contracts import (
    TimepointCompatibilityPolicy,
    TimepointCompatibilityRule,
    load_timepoint_compatibility_policy,
)


class ClinicalSemanticError(ValueError):
    """Clinical observations cannot be safely grouped or rendered."""


class SemanticDirection(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    NEUTRAL = "neutral"
    HIGHER_IS_MORE_SEVERE = "higher_is_more_severe"
    LOWER_IS_MORE_SEVERE = "lower_is_more_severe"


class TimeUnit(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class ClinicalConstructObservation(BaseModel):
    """All axes required before two B observations may share a frame."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["1.3"] = "1.3"
    observation_id: str
    clinical_construct: str = Field(
        validation_alias=AliasChoices("clinical_construct", "construct_id")
    )
    definition: str = Field(
        validation_alias=AliasChoices("definition", "construct_definition", "original_definition")
    )
    direction: str
    unit: str
    estimand: str
    denominator: str = Field(validation_alias=AliasChoices("denominator", "denominator_role"))
    analysis_set: str = Field(
        validation_alias=AliasChoices("analysis_set", "analysis_population", "population_context")
    )
    analysis_form: str = Field(
        validation_alias=AliasChoices("analysis_form", "statistical_form_family", "statistic_form")
    )
    instrument_or_scale: str = Field(
        default="not_reported",
        validation_alias=AliasChoices(
            "instrument_or_scale", "instrument", "scale", "scale_version"
        ),
    )
    actual_timepoint: float
    actual_timepoint_unit: TimeUnit = Field(
        validation_alias=AliasChoices("actual_timepoint_unit", "time_unit")
    )

    @field_validator(
        "observation_id",
        "clinical_construct",
        "definition",
        "direction",
        "unit",
        "estimand",
        "denominator",
        "analysis_set",
        "analysis_form",
        "instrument_or_scale",
    )
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError(f"{info.field_name}不能为空")
        return normalized

    @field_validator("actual_timepoint")
    @classmethod
    def _timepoint(cls, value: float) -> float:
        if isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("实际时间点必须是非负有限数值")
        return value

    @property
    def construct_id(self) -> str:
        return self.clinical_construct

    @property
    def timepoint_weeks(self) -> float:
        return {
            TimeUnit.DAY: self.actual_timepoint / 7.0,
            TimeUnit.WEEK: self.actual_timepoint,
            TimeUnit.MONTH: self.actual_timepoint * 4.34524,
            TimeUnit.YEAR: self.actual_timepoint * 52.1429,
        }[self.actual_timepoint_unit]


class SemanticAdjudicationReceipt(BaseModel):
    """Model-assisted wording decision; deterministic clinical guards still veto."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.3"] = "1.3"
    adjudication_id: str
    observation_ids: tuple[str, str]
    decision: Literal["compatible", "incompatible"]
    model_id: str
    independent_review_id: str
    independent_context: str
    rationale_zh: str

    @field_validator(
        "adjudication_id",
        "model_id",
        "independent_review_id",
        "independent_context",
        "rationale_zh",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError(f"{info.field_name}不能为空")
        return normalized

    @field_validator("observation_ids")
    @classmethod
    def _pair_is_unique(cls, values: tuple[str, str]) -> tuple[str, str]:
        normalized = tuple(" ".join(value.split()) for value in values)
        if any(not value for value in normalized) or len(set(normalized)) != 2:
            raise ValueError("语义裁决必须绑定两个不同观察")
        return normalized  # type: ignore[return-value]

    @model_validator(mode="after")
    def _review_is_independent(self) -> Self:
        if self.model_id == self.independent_review_id:
            raise ValueError("模型语义裁决与独立复核不得使用同一身份")
        if not any("\u4e00" <= char <= "\u9fff" for char in self.rationale_zh):
            raise ValueError("语义裁决理由必须是用户可读中文")
        return self


class SemanticCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    compatible: bool
    reasons: tuple[str, ...] = ()
    time_window_note_zh: str | None = None

    @model_validator(mode="after")
    def _result_has_reasons(self) -> Self:
        if self.compatible and self.reasons:
            raise ValueError("兼容观察不能带冲突原因")
        if not self.compatible and not self.reasons:
            raise ValueError("不兼容观察必须记录冲突原因")
        return self


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def semantic_value_is_unknown(value: object) -> bool:
    """Missing markers are absence of knowledge, never an equivalence class."""
    if not isinstance(value, str) or not value.strip():
        return True
    normalized = "-".join(value.casefold().replace("_", "-").split())
    return normalized in {
        "unknown", "not-reported", "not-publicly-disclosed", "not-specified",
        "unspecified", "missing", "null", "none", "n/a", "na", "-", "—",
        "未报告", "未披露", "未公开", "未注明", "未提供", "未知", "不详",
    } or normalized.endswith(("-not-reported", ":unknown"))


def time_policy_identity(
    policy: TimepointCompatibilityPolicy | None = None,
) -> str:
    """时间政策的审计身份（policy_id@version），供摘要与任务绑定。"""
    current = _default_timepoint_policy() if policy is None else policy
    return f"{current.policy_id}@{current.version}"


@lru_cache(maxsize=1)
def _default_timepoint_policy() -> TimepointCompatibilityPolicy:
    """加载发货默认时间窗政策；运行期不可变，进程内缓存。"""
    return load_timepoint_compatibility_policy()


def _resolve_timepoint_rule(
    observation: ClinicalConstructObservation,
    policy: TimepointCompatibilityPolicy,
) -> TimepointCompatibilityRule | None:
    """按版本化规则解析观察所属时间窗；同单位、闭区间、命中必须唯一。"""
    # 两模块各自定义 TimeUnit 枚举；按值比较避免跨类身份判断失败。
    unit_value = str(observation.actual_timepoint_unit.value)
    matches = tuple(
        rule
        for rule in policy.rules
        if str(rule.time_unit.value) == unit_value
        and rule.minimum <= observation.actual_timepoint <= rule.maximum
    )
    if len(matches) > 1:
        # 配置层已拒绝重叠政策；此路径只挡未重验对象的注入，保守视为不可比。
        return None
    return matches[0] if matches else None


def compare_clinical_constructs(
    left: ClinicalConstructObservation | Mapping[str, Any],
    right: ClinicalConstructObservation | Mapping[str, Any],
    *,
    adjudication: SemanticAdjudicationReceipt | Mapping[str, Any] | None = None,
    timepoint_policy: TimepointCompatibilityPolicy | None = None,
) -> SemanticCompatibility:
    """Apply model-assisted wording equivalence behind deterministic vetoes."""

    first = (
        left
        if isinstance(left, ClinicalConstructObservation)
        else ClinicalConstructObservation.model_validate(left)
    )
    second = (
        right
        if isinstance(right, ClinicalConstructObservation)
        else ClinicalConstructObservation.model_validate(right)
    )
    receipt = (
        None
        if adjudication is None
        else adjudication
        if isinstance(adjudication, SemanticAdjudicationReceipt)
        else SemanticAdjudicationReceipt.model_validate(adjudication)
    )
    if receipt is not None and set(receipt.observation_ids) != {
        first.observation_id,
        second.observation_id,
    }:
        raise ClinicalSemanticError("模型语义裁决未绑定当前观察对")
    hard_axes = (
        ("方向不一致", first.direction, second.direction),
        ("单位不一致", first.unit, second.unit),
        ("估计目标不一致", first.estimand, second.estimand),
        ("分母口径不一致", first.denominator, second.denominator),
        ("分析集不一致", first.analysis_set, second.analysis_set),
        ("分析形式不一致", first.analysis_form, second.analysis_form),
        ("量表或工具不一致", first.instrument_or_scale, second.instrument_or_scale),
    )
    reasons = tuple(
        label
        for label, left_value, right_value in hard_axes
        if _normalized(left_value) != _normalized(right_value)
    )
    required_axes = (
        ("临床构念", first.clinical_construct, second.clinical_construct),
        ("临床定义", first.definition, second.definition),
        *((label.removesuffix("不一致"), left_value, right_value)
          for label, left_value, right_value in hard_axes),
    )
    reasons += tuple(
        f"{label}未明确，不能据此认定临床可比"
        for label, left_value, right_value in required_axes
        if semantic_value_is_unknown(left_value) or semantic_value_is_unknown(right_value)
    )
    wording_differs = (
        _normalized(first.clinical_construct) != _normalized(second.clinical_construct)
        or _normalized(first.definition) != _normalized(second.definition)
    )
    if wording_differs and receipt is None:
        reasons += ("临床构念或定义不一致且缺少模型语义裁决",)
    elif receipt is not None and receipt.decision == "incompatible":
        reasons += ("模型语义裁决为不兼容",)
    note: str | None = None
    policy = (
        _default_timepoint_policy() if timepoint_policy is None else timepoint_policy
    )
    left_rule = _resolve_timepoint_rule(first, policy)
    right_rule = _resolve_timepoint_rule(second, policy)
    identity = f"{policy.policy_id} v{policy.version}"
    if left_rule is None or right_rule is None:
        reasons += (f"实际观察时间未命中版本化时间窗（{identity}）",)
    elif left_rule.rule_id != right_rule.rule_id:
        reasons += (
            f"观察窗分属不同版本化时间窗"
            f"（{left_rule.rule_id} 与 {right_rule.rule_id}，{identity}）",
        )
    else:
        delta = abs(first.timepoint_weeks - second.timepoint_weeks)
        tolerance = left_rule.comparison_tolerance_weeks
        if delta > tolerance:
            reasons += (
                f"观察窗差异超过{left_rule.rule_id}（{left_rule.label_zh}）的版本化容差"
                f"（{delta:g}周 > {tolerance:g}周，{identity}）",
            )
        elif delta > 0:
            note = (
                f"实际观察窗为{first.timepoint_weeks:g}周与{second.timepoint_weeks:g}周；"
                "同框仅表示临床构念兼容，不代表时间点相同"
            )
    return SemanticCompatibility(
        compatible=not reasons,
        reasons=reasons,
        time_window_note_zh=note,
    )


def assert_clinical_construct_compatible(
    observations: Sequence[ClinicalConstructObservation | Mapping[str, Any]],
) -> tuple[ClinicalConstructObservation, ...]:
    """Validate a proposed frame and raise on any incompatible pair."""

    validated = tuple(
        observation
        if isinstance(observation, ClinicalConstructObservation)
        else ClinicalConstructObservation.model_validate(observation)
        for observation in observations
    )
    for index, first in enumerate(validated):
        for second in validated[index + 1 :]:
            result = compare_clinical_constructs(first, second)
            if not result.compatible:
                raise ClinicalSemanticError(
                    f"临床构念不得共框：{first.observation_id}/{second.observation_id}；"
                    + "、".join(result.reasons)
                )
    return validated


BubbleMetric = Literal[
    "efficacy_signal",
    "overall_safety",
    "serious_risk",
    "benefit_durability",
    "discontinuation_risk",
    "treatment_sample_size",
    "effective_analysis_set",
    "long_term_exposure",
]


class BubblePreset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    preset_id: Literal[
        "efficacy_overall_safety",
        "efficacy_serious_risk",
        "durability_discontinuation_risk",
    ]
    label_zh: str
    x_metric: BubbleMetric
    y_metric: BubbleMetric
    size_metric: BubbleMetric
    size_semantics_zh: str
    neutral: Literal[True] = True
    ranking: Literal[False] = False
    composite_score: Literal[False] = False
    recommendation: Literal[False] = False

    @field_validator("label_zh", "size_semantics_zh")
    @classmethod
    def _labels(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("气泡预设标签不能为空")
        return normalized

    @model_validator(mode="after")
    def _preset_axes_are_distinct(self) -> Self:
        if self.x_metric == self.y_metric or self.size_metric in {self.x_metric, self.y_metric}:
            raise ValueError("气泡预设的横轴、纵轴和大小语义必须不同")
        return self


BUBBLE_PRESETS: tuple[BubblePreset, ...] = (
    BubblePreset(
        preset_id="efficacy_overall_safety",
        label_zh="疗效信号 × 总体安全性",
        x_metric="efficacy_signal",
        y_metric="overall_safety",
        size_metric="treatment_sample_size",
        size_semantics_zh="气泡面积表示治疗组样本量，不是疗效或风险排名",
    ),
    BubblePreset(
        preset_id="efficacy_serious_risk",
        label_zh="疗效信号 × 严重风险",
        x_metric="efficacy_signal",
        y_metric="serious_risk",
        size_metric="effective_analysis_set",
        size_semantics_zh="气泡面积表示有效分析集规模，不是综合评分",
    ),
    BubblePreset(
        preset_id="durability_discontinuation_risk",
        label_zh="获益持续性 × 停药风险",
        x_metric="benefit_durability",
        y_metric="discontinuation_risk",
        size_metric="long_term_exposure",
        size_semantics_zh="气泡面积表示长期暴露量，不是研发建议",
    ),
)


def get_bubble_preset(preset_id: str) -> BubblePreset:
    for preset in BUBBLE_PRESETS:
        if preset.preset_id == preset_id:
            return preset
    raise ClinicalSemanticError(f"未知 B 类气泡预设：{preset_id}")


def build_bubble_point(
    preset: BubblePreset | str,
    *,
    x_value: float | None,
    y_value: float | None,
    size_value: float | None,
    x_state: str = "reported_value",
    y_state: str = "reported_value",
    size_state: str = "reported_value",
) -> dict[str, Any] | None:
    """Build only a concrete, non-ranked point; missing states stay unplottable."""

    selected = get_bubble_preset(preset) if isinstance(preset, str) else preset
    if any(
        state not in {"reported_value", "reported_zero"} for state in (x_state, y_state, size_state)
    ):
        return None
    if x_value is None or y_value is None or size_value is None:
        return None
    values = (x_value, y_value, size_value)
    if any(isinstance(value, bool) or not math.isfinite(value) for value in values):
        return None
    if any(value < 0 for value in values):
        raise ClinicalSemanticError("气泡点数值不得为负")
    return {
        "preset_id": selected.preset_id,
        "x": x_value,
        "y": y_value,
        "size": size_value,
        "size_semantics_zh": selected.size_semantics_zh,
        "disclosure_states": {"x": x_state, "y": y_state, "size": size_state},
        "rank": None,
        "composite_score": None,
    }


__all__ = [
    "BUBBLE_PRESETS",
    "BubbleMetric",
    "BubblePreset",
    "ClinicalConstructObservation",
    "ClinicalSemanticError",
    "SemanticCompatibility",
    "SemanticDirection",
    "TimeUnit",
    "assert_clinical_construct_compatible",
    "build_bubble_point",
    "compare_clinical_constructs",
    "get_bubble_preset",
    "semantic_value_is_unknown",
]
