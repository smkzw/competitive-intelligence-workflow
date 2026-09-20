"""B 类试验角色输出合同。

研究角色和论文角色来自两条独立的确定性链路：前者由共用研究事实与
版本化策略重新计算，后者只接受 PubMed 连接器已经完成的论文分类。B
输出保留两列，论文类型的变化不能覆盖母试验的研究角色。
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from enum import StrEnum
from itertools import combinations
from pathlib import Path
from typing import Any, Literal, Self, cast

import yaml
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.common.study_roles import (
    StudyCandidate,
    StudyRole,
    StudyRolePolicy,
    evaluate_study_role,
)
from ci_workflow.sources.connectors.pubmed import (
    ClassifiedPublication,
    classify_pubmed_records,
)

PublicationRoleValue = Literal[
    "unclassified",
    "primary_report",
    "ad_hoc_analysis",
    "review",
    "supporting_publication",
    "unrelated",
]

_NCT_ID = re.compile(r"NCT[0-9]{8}", re.IGNORECASE)


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("B 类试验角色合同文本不能为空")
    return normalized


class TrialRoleOutput(BaseModel):
    """一个 B 类试验的研究角色与独立论文角色输出。

    `study_role` 始终描述母试验；`publication_role` 只描述所绑定论文，
    没有论文或论文尚未分类时保持 ``unclassified``。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    study_id: str = Field(validation_alias=AliasChoices("study_id", "trial_id"))
    study_role: StudyRole
    inclusion_rationale_zh: str
    matched_rule_ids: tuple[str, ...]
    policy_id: str
    policy_version: str
    evidence_version: str
    publication_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("publication_id", "pmid"),
    )
    publication_role: PublicationRoleValue = "unclassified"
    publication_rationale_zh: str | None = None
    publication_matched_study_ids: tuple[str, ...] = ()
    publication_signals: tuple[str, ...] = ()

    @field_validator(
        "study_id",
        "inclusion_rationale_zh",
        "policy_id",
        "policy_version",
        "evidence_version",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _text(value)

    @field_validator("publication_id", "publication_rationale_zh")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("matched_rule_ids", "publication_matched_study_ids", "publication_signals")
    @classmethod
    def _unique_text_tuple(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("B 类试验角色合同标识不得重复")
        return normalized

    @property
    def trial_id(self) -> str:
        return self.study_id

    @property
    def role(self) -> StudyRole:
        return self.study_role

    @property
    def study_role_policy_id(self) -> str:
        return self.policy_id

    @property
    def study_role_policy_version(self) -> str:
        return self.policy_version

    @property
    def matched_study_rule_ids(self) -> tuple[str, ...]:
        return self.matched_rule_ids

    @property
    def publication_pmid(self) -> str | None:
        return self.publication_id


BTrialRoleOutput = TrialRoleOutput
TrialRoleRecord = TrialRoleOutput


def _validated_candidate(candidate: StudyCandidate | Mapping[str, Any]) -> StudyCandidate:
    try:
        raw = (
            candidate.model_dump(mode="python", warnings=False)
            if isinstance(candidate, StudyCandidate)
            else dict(candidate)
        )
        return StudyCandidate.model_validate(raw)
    except ValidationError as error:
        raise ValueError(f"B 类研究事实重新校验失败：{error}") from error


def _validated_publication(
    publication: ClassifiedPublication | Mapping[str, Any],
    *,
    study_id: str,
) -> ClassifiedPublication:
    try:
        if isinstance(publication, ClassifiedPublication):
            raw = dict(vars(publication))
            raw["record"] = dict(vars(publication.record))
        else:
            raw = dict(publication)
        validated = ClassifiedPublication.model_validate(raw)
    except ValidationError as error:
        raise ValueError(f"论文角色分类结果重新校验失败：{error}") from error

    normalized_study_id = study_id.strip().upper()
    if _NCT_ID.fullmatch(normalized_study_id) is None:
        raise ValueError("非 NCT 试验的论文关联尚不能从当前记录重新计算")
    expected = classify_pubmed_records((validated.record,), target_nct_ids=(normalized_study_id,))[
        0
    ]
    if validated != expected:
        raise ValueError("论文角色必须由当前论文记录和目标试验重新分类")
    return validated


def build_trial_role_output(
    candidate: StudyCandidate | Mapping[str, Any],
    *,
    publication: ClassifiedPublication | Mapping[str, Any] | None = None,
    policy: StudyRolePolicy | None = None,
) -> TrialRoleOutput:
    """从当前研究事实和论文分类构建 B 角色输出。

    不接受调用方注入 ``study_role`` 或裸 ``publication_role``；研究角色由
    共用策略重新判定，论文角色只能来自 ``ClassifiedPublication``。
    """

    current_candidate = _validated_candidate(candidate)
    decision = evaluate_study_role(current_candidate, policy=policy)
    publication_record = (
        None
        if publication is None
        else _validated_publication(publication, study_id=current_candidate.study_id)
    )
    return TrialRoleOutput(
        study_id=decision.study_id,
        study_role=decision.study_role,
        inclusion_rationale_zh=decision.inclusion_rationale_zh,
        matched_rule_ids=decision.matched_rule_ids,
        policy_id=decision.policy_id,
        policy_version=decision.policy_version,
        evidence_version=decision.evidence_version,
        publication_id=None if publication_record is None else publication_record.record.pmid,
        publication_role=(
            "unclassified" if publication_record is None else publication_record.role
        ),
        publication_rationale_zh=(
            None if publication_record is None else publication_record.rationale_zh
        ),
        publication_matched_study_ids=(
            () if publication_record is None else publication_record.matched_nct_ids
        ),
        publication_signals=(
            () if publication_record is None else publication_record.classification_signals
        ),
    )


def build_b_trial_role(
    candidate: StudyCandidate | Mapping[str, Any],
    *,
    publication: ClassifiedPublication | Mapping[str, Any] | None = None,
    policy: StudyRolePolicy | None = None,
) -> TrialRoleOutput:
    """``build_trial_role_output`` 的 B 类语义别名。"""

    return build_trial_role_output(candidate, publication=publication, policy=policy)


# ── Task 6.1：B 类终点—时间窗兼容合同 ──────────────────────────────────────


class EndpointCompatibilityError(ValueError):
    """终点或时间窗规则/观察不满足失败关闭合同。"""


class EndpointAnalysisForm(StrEnum):
    """可进入版本化兼容规则的分析形式。"""

    RESPONSE_RATE = "response_rate"
    CHANGE_FROM_BASELINE = "change_from_baseline"
    ABSOLUTE_VALUE = "absolute_value"
    EVENT_RATE = "event_rate"
    TIME_TO_EVENT = "time_to_event"
    HAZARD_RATIO = "hazard_ratio"
    MEAN_DIFFERENCE = "mean_difference"
    MEDIAN_DIFFERENCE = "median_difference"


class TimeUnit(StrEnum):
    """时间窗规则的封闭单位集合；初版不做单位换算。"""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


_CJK = re.compile(r"[\u3400-\u9fff]")
_TIMEPOINT_TEXT = re.compile(
    r"^第?\s*([0-9]+(?:\.[0-9]+)?)\s*(日|天|d|day|days|周|w|wk|week|weeks|月|mo|month|months|年|y|yr|year|years)?$",
    re.IGNORECASE,
)
_TIME_UNIT_ALIASES = {
    "d": "day",
    "day": "day",
    "days": "day",
    "日": "day",
    "天": "day",
    "w": "week",
    "wk": "week",
    "week": "week",
    "weeks": "week",
    "周": "week",
    "mo": "month",
    "month": "month",
    "months": "month",
    "月": "month",
    "y": "year",
    "yr": "year",
    "year": "year",
    "years": "year",
    "年": "year",
}
_ANALYSIS_FORM_ALIASES = {
    "response": "response_rate",
    "response_rate": "response_rate",
    "responder_rate": "response_rate",
    "change": "change_from_baseline",
    "change_from_baseline": "change_from_baseline",
    "absolute": "absolute_value",
    "absolute_value": "absolute_value",
    "event_rate": "event_rate",
    "time_to_event": "time_to_event",
    "hazard_ratio": "hazard_ratio",
    "mean_difference": "mean_difference",
    "median_difference": "median_difference",
}


def _compat_text(value: str, *, field_name: str = "兼容合同字段") -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _raw_compat_text(value: str, *, field_name: str = "兼容合同字段") -> str:
    if not value.strip():
        raise ValueError(f"{field_name}不能为空")
    return value


def _normalize_time_unit(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    token = value.strip().casefold()
    return _TIME_UNIT_ALIASES.get(token, value)


def _normalize_analysis_form(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    token = value.strip().casefold().replace("-", "_").replace(" ", "_")
    return _ANALYSIS_FORM_ALIASES.get(token, value)


def _as_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    return (value,) if isinstance(value, str) else tuple(value)


class EndpointObservation(BaseModel):
    """B 类疗效观察；原始终点、定义、单位、时间点和角色不被规范化覆盖。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    observation_id: str = Field(validation_alias=AliasChoices("observation_id", "id"))
    trial_id: str = Field(validation_alias=AliasChoices("trial_id", "study_id"))
    endpoint_id: str = Field(
        validation_alias=AliasChoices(
            "endpoint_id", "original_endpoint", "raw_endpoint", "endpoint"
        )
    )
    endpoint_definition: str = Field(
        validation_alias=AliasChoices(
            "endpoint_definition", "original_definition", "raw_definition", "definition"
        )
    )
    endpoint_role: str = Field(
        validation_alias=AliasChoices("endpoint_role", "original_endpoint_role", "role")
    )
    unit: str = Field(validation_alias=AliasChoices("unit", "original_unit", "raw_unit"))
    direction: EndpointDirection
    analysis_form: str
    timepoint: int | float | str = Field(
        validation_alias=AliasChoices(
            "timepoint", "actual_timepoint", "observed_timepoint", "timepoint_value"
        )
    )
    time_unit: str = Field(
        validation_alias=AliasChoices(
            "time_unit", "actual_timepoint_unit", "observed_time_unit", "timepoint_unit"
        )
    )
    clinical_construct: str | None = Field(
        default=None,
        validation_alias=AliasChoices("clinical_construct", "construct_id", "endpoint_construct"),
    )

    @field_validator(
        "observation_id",
        "trial_id",
        "endpoint_id",
        "endpoint_definition",
        "endpoint_role",
        "unit",
        "analysis_form",
        "time_unit",
    )
    @classmethod
    def _observation_text(cls, value: str) -> str:
        return _raw_compat_text(value, field_name="终点观察字段")

    @field_validator("clinical_construct")
    @classmethod
    def _construct_text(cls, value: str | None) -> str | None:
        return None if value is None else _raw_compat_text(value, field_name="临床构念")

    @field_validator("timepoint")
    @classmethod
    def _timepoint_is_scalar(cls, value: int | float | str) -> int | float | str:
        if isinstance(value, bool):
            raise ValueError("实际时间点不得为布尔值")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("实际时间点必须是有限数值")
        if isinstance(value, str):
            _raw_compat_text(value, field_name="实际时间点")
        return value

    @property
    def original_endpoint(self) -> str:
        return self.endpoint_id

    @property
    def original_definition(self) -> str:
        return self.endpoint_definition

    @property
    def original_unit(self) -> str:
        return self.unit

    @property
    def actual_timepoint(self) -> int | float | str:
        return self.timepoint

    @property
    def actual_timepoint_unit(self) -> str:
        return self.time_unit

    @property
    def original_endpoint_role(self) -> str:
        return self.endpoint_role


class EndpointCompatibilityRule(BaseModel):
    """一个临床构念、方向、单位和分析形式固定的终点兼容规则。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    rule_id: str = Field(validation_alias=AliasChoices("rule_id", "id"))
    construct_id: str = Field(
        validation_alias=AliasChoices("construct_id", "clinical_construct", "endpoint_construct")
    )
    label_zh: str = Field(validation_alias=AliasChoices("label_zh", "construct_label_zh"))
    endpoint_ids: tuple[str, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("endpoint_ids", "compatible_endpoint_ids"),
    )
    direction: EndpointDirection
    allowed_units: tuple[str, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("allowed_units", "compatible_units"),
    )
    analysis_forms: tuple[EndpointAnalysisForm, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("analysis_forms", "analysis_form", "allowed_analysis_forms"),
    )
    difference_label_zh: str = Field(
        validation_alias=AliasChoices("difference_label_zh", "difference_labels_zh")
    )

    @field_validator("rule_id", "construct_id", "label_zh", "difference_label_zh")
    @classmethod
    def _rule_text(cls, value: str) -> str:
        return _compat_text(value, field_name="终点兼容规则字段")

    @field_validator("endpoint_ids", "allowed_units", mode="before")
    @classmethod
    def _rule_text_lists(cls, value: Any) -> tuple[str, ...]:
        values = tuple(
            _compat_text(item, field_name="终点兼容规则列表字段") for item in _as_tuple(value)
        )
        if len({item.casefold() for item in values}) != len(values):
            raise ValueError("终点兼容规则列表不得重复")
        return values

    @field_validator("analysis_forms", mode="before")
    @classmethod
    def _analysis_forms(cls, value: Any) -> tuple[Any, ...]:
        values = tuple(_normalize_analysis_form(item) for item in _as_tuple(value))
        if len(set(values)) != len(values):
            raise ValueError("终点兼容规则的分析形式不得重复")
        return values

    @model_validator(mode="after")
    def _difference_label_is_chinese(self) -> Self:
        if not _CJK.search(self.difference_label_zh):
            raise ValueError("终点兼容规则必须提供中文差异说明")
        return self

    @property
    def compatible_units(self) -> tuple[str, ...]:
        return self.allowed_units

    @property
    def compatible_analysis_forms(self) -> tuple[EndpointAnalysisForm, ...]:
        return self.analysis_forms

    @property
    def difference_labels_zh(self) -> tuple[str, ...]:
        return (self.difference_label_zh,)


class EndpointCompatibilityPolicy(BaseModel):
    """版本化终点兼容规则集合。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["1.0"]
    policy_id: str
    version: str = Field(validation_alias=AliasChoices("version", "policy_version"))
    rules: tuple[EndpointCompatibilityRule, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("rules", "endpoint_rules", "compatibility_rules"),
    )

    @field_validator("policy_id", "version")
    @classmethod
    def _policy_id_text(cls, value: str) -> str:
        return _compat_text(value, field_name="终点兼容策略标识")

    @model_validator(mode="after")
    def _rules_are_unique(self) -> Self:
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("终点兼容规则标识不得重复")
        bodies = tuple(
            json.dumps(
                rule.model_dump(mode="json", exclude={"rule_id"}),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for rule in self.rules
        )
        if len(set(bodies)) != len(bodies):
            raise ValueError("终点兼容规则条目不得重复")
        for left, right in combinations(self.rules, 2):
            same_construct = _normalized(left.construct_id) == _normalized(right.construct_id)
            shared_endpoint = bool(
                {_normalized(item) for item in left.endpoint_ids}
                & {_normalized(item) for item in right.endpoint_ids}
            )
            shared_unit = bool(
                {_normalized(item) for item in left.allowed_units}
                & {_normalized(item) for item in right.allowed_units}
            )
            shared_form = bool(set(left.analysis_forms) & set(right.analysis_forms))
            if (
                (same_construct or shared_endpoint)
                and left.direction is right.direction
                and shared_unit
                and shared_form
            ):
                raise ValueError(f"终点兼容规则存在重叠歧义：{left.rule_id}、{right.rule_id}")
        return self

    @classmethod
    def from_yaml(cls, path: Path | str) -> Self:
        try:
            payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise EndpointCompatibilityError("终点兼容策略顶层必须是对象")
            return cls.model_validate(cast(dict[str, Any], payload))
        except EndpointCompatibilityError:
            raise
        except (OSError, yaml.YAMLError, ValidationError, TypeError) as error:
            raise EndpointCompatibilityError(f"终点兼容策略加载失败：{error}") from error


class TimepointCompatibilityRule(BaseModel):
    """一个规范时间单位和闭区间上下界组成的时间窗规则。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    rule_id: str = Field(validation_alias=AliasChoices("rule_id", "id"))
    time_unit: TimeUnit = Field(validation_alias=AliasChoices("time_unit", "unit"))
    minimum: float = Field(validation_alias=AliasChoices("minimum", "min_value", "minimum_value"))
    maximum: float = Field(validation_alias=AliasChoices("maximum", "max_value", "maximum_value"))
    canonical_value: float | None = Field(
        default=None,
        validation_alias=AliasChoices("canonical_value", "target_value", "nominal_value"),
    )
    comparison_tolerance_weeks: float = Field(
        default=2.0,
        validation_alias=AliasChoices(
            "comparison_tolerance_weeks", "tolerance_weeks", "near_window_weeks",
        ),
    )
    label_zh: str = Field(validation_alias=AliasChoices("label_zh", "window_label_zh"))
    difference_label_zh: str = Field(
        validation_alias=AliasChoices("difference_label_zh", "difference_labels_zh")
    )

    @field_validator("rule_id", "label_zh", "difference_label_zh")
    @classmethod
    def _time_rule_text(cls, value: str) -> str:
        return _compat_text(value, field_name="时间窗兼容规则字段")

    @field_validator("time_unit", mode="before")
    @classmethod
    def _time_unit_alias(cls, value: Any) -> Any:
        return _normalize_time_unit(value)

    @model_validator(mode="after")
    def _window_is_valid(self) -> Self:
        if (
            not math.isfinite(self.comparison_tolerance_weeks)
            or self.comparison_tolerance_weeks <= 0
        ):
            raise ValueError("版本化时间容差必须是有限正数（单位：周）")
        if not math.isfinite(self.minimum) or not math.isfinite(self.maximum):
            raise ValueError("时间窗上下界必须是有限数值")
        if self.minimum > self.maximum:
            raise ValueError("时间窗最小值不得大于最大值")
        if self.canonical_value is not None and not (
            self.minimum <= self.canonical_value <= self.maximum
        ):
            raise ValueError("时间窗规范值必须落在最小值和最大值之间")
        if not _CJK.search(self.difference_label_zh):
            raise ValueError("时间窗兼容规则必须提供中文差异说明")
        return self

    @property
    def min_value(self) -> float:
        return self.minimum

    @property
    def max_value(self) -> float:
        return self.maximum

    @property
    def difference_labels_zh(self) -> tuple[str, ...]:
        return (self.difference_label_zh,)


class TimepointCompatibilityPolicy(BaseModel):
    """版本化时间窗兼容规则集合。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["1.0"]
    policy_id: str
    version: str = Field(validation_alias=AliasChoices("version", "policy_version"))
    rules: tuple[TimepointCompatibilityRule, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("rules", "timepoint_rules", "compatibility_rules"),
    )

    @field_validator("policy_id", "version")
    @classmethod
    def _time_policy_id_text(cls, value: str) -> str:
        return _compat_text(value, field_name="时间窗兼容策略标识")

    @model_validator(mode="after")
    def _time_rules_are_unique(self) -> Self:
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("时间窗兼容规则标识不得重复")
        bodies = tuple(
            json.dumps(
                rule.model_dump(mode="json", exclude={"rule_id"}),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for rule in self.rules
        )
        if len(set(bodies)) != len(bodies):
            raise ValueError("时间窗兼容规则条目不得重复")
        for left, right in combinations(self.rules, 2):
            if left.time_unit is right.time_unit and max(left.minimum, right.minimum) <= min(
                left.maximum, right.maximum
            ):
                raise ValueError(f"时间窗兼容规则存在重叠歧义：{left.rule_id}、{right.rule_id}")
        return self

    @classmethod
    def from_yaml(cls, path: Path | str) -> Self:
        try:
            payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise EndpointCompatibilityError("时间窗兼容策略顶层必须是对象")
            return cls.model_validate(cast(dict[str, Any], payload))
        except EndpointCompatibilityError:
            raise
        except (OSError, yaml.YAMLError, ValidationError, TypeError) as error:
            raise EndpointCompatibilityError(f"时间窗兼容策略加载失败：{error}") from error


class EndpointCompatibilityResult(BaseModel):
    """终点与时间窗确定性匹配结果；不兼容记录保留原始观察和差异标签。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation: EndpointObservation
    compatible: bool
    compatibility_key: tuple[str, str] | None
    endpoint_rule_id: str | None
    timepoint_rule_id: str | None
    difference_labels_zh: tuple[str, ...]
    endpoint_policy_id: str
    endpoint_policy_version: str
    timepoint_policy_id: str
    timepoint_policy_version: str

    @model_validator(mode="after")
    def _result_consistency(self) -> Self:
        expected_key = (
            None
            if self.endpoint_rule_id is None or self.timepoint_rule_id is None
            else (self.endpoint_rule_id, self.timepoint_rule_id)
        )
        if self.compatibility_key != expected_key:
            raise ValueError("终点兼容键必须由当前命中的两条规则确定性生成")
        if self.compatible != (expected_key is not None):
            raise ValueError("终点兼容状态与规则命中结果不一致")
        if not self.compatible and not self.difference_labels_zh:
            raise ValueError("不兼容记录必须保留中文差异标签")
        return self

    @property
    def record(self) -> EndpointObservation:
        return self.observation

    @property
    def original_observation(self) -> EndpointObservation:
        return self.observation

    @property
    def original_endpoint(self) -> str:
        return self.observation.original_endpoint

    @property
    def raw_endpoint(self) -> str:
        return self.original_endpoint

    @property
    def original_definition(self) -> str:
        return self.observation.original_definition

    @property
    def raw_definition(self) -> str:
        return self.original_definition

    @property
    def original_unit(self) -> str:
        return self.observation.original_unit

    @property
    def raw_unit(self) -> str:
        return self.original_unit

    @property
    def actual_timepoint(self) -> int | float | str:
        return self.observation.actual_timepoint

    @property
    def observed_timepoint(self) -> int | float | str:
        return self.actual_timepoint

    @property
    def actual_timepoint_unit(self) -> str:
        return self.observation.actual_timepoint_unit

    @property
    def observed_time_unit(self) -> str:
        return self.actual_timepoint_unit

    @property
    def original_endpoint_role(self) -> str:
        return self.observation.original_endpoint_role

    @property
    def endpoint_compatibility_rule_id(self) -> str | None:
        return self.endpoint_rule_id

    @property
    def timepoint_compatibility_rule_id(self) -> str | None:
        return self.timepoint_rule_id

    @property
    def analysis_form(self) -> str:
        return self.observation.analysis_form

    @property
    def matched_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            rule_id
            for rule_id in (self.endpoint_rule_id, self.timepoint_rule_id)
            if rule_id is not None
        )

    @property
    def difference_labels(self) -> tuple[str, ...]:
        return self.difference_labels_zh

    @property
    def compatibility_bucket_id(self) -> str | None:
        return None if self.compatibility_key is None else "::".join(self.compatibility_key)


def _default_compatibility_path(kind: Literal["endpoints", "timepoints"]) -> Path:
    return Path(__file__).resolve().parents[4] / "policies" / kind / "compatibility-v1.yaml"


def load_endpoint_compatibility_policy(
    path: Path | str | None = None,
) -> EndpointCompatibilityPolicy:
    """严格加载终点兼容 YAML；未知字段、枚举和重复规则失败关闭。"""

    return EndpointCompatibilityPolicy.from_yaml(
        _default_compatibility_path("endpoints") if path is None else path
    )


def load_timepoint_compatibility_policy(
    path: Path | str | None = None,
) -> TimepointCompatibilityPolicy:
    """严格加载时间窗兼容 YAML；未知字段、枚举和重复规则失败关闭。"""

    return TimepointCompatibilityPolicy.from_yaml(
        _default_compatibility_path("timepoints") if path is None else path
    )


def _validated_observation(
    observation: EndpointObservation | Mapping[str, Any],
) -> EndpointObservation:
    try:
        raw = (
            dict(vars(observation))
            if isinstance(observation, EndpointObservation)
            else dict(observation)
        )
        return EndpointObservation.model_validate(raw)
    except (ValidationError, TypeError) as error:
        raise EndpointCompatibilityError(f"终点观察重新校验失败：{error}") from error


def _validated_endpoint_policy(
    policy: EndpointCompatibilityPolicy | Path | str | None,
) -> EndpointCompatibilityPolicy:
    if policy is None or isinstance(policy, (Path, str)):
        return load_endpoint_compatibility_policy(policy)
    try:
        raw = dict(vars(policy))
        raw["rules"] = tuple(dict(vars(rule)) for rule in policy.rules)
        return EndpointCompatibilityPolicy.model_validate(raw)
    except ValidationError as error:
        raise EndpointCompatibilityError(f"终点兼容策略重新校验失败：{error}") from error


def _validated_timepoint_policy(
    policy: TimepointCompatibilityPolicy | Path | str | None,
) -> TimepointCompatibilityPolicy:
    if policy is None or isinstance(policy, (Path, str)):
        return load_timepoint_compatibility_policy(policy)
    try:
        raw = dict(vars(policy))
        raw["rules"] = tuple(dict(vars(rule)) for rule in policy.rules)
        return TimepointCompatibilityPolicy.model_validate(raw)
    except ValidationError as error:
        raise EndpointCompatibilityError(f"时间窗兼容策略重新校验失败：{error}") from error


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def _endpoint_match(
    observation: EndpointObservation,
    policy: EndpointCompatibilityPolicy,
) -> tuple[EndpointCompatibilityRule | None, tuple[str, ...]]:
    endpoint_id = _normalized(observation.endpoint_id)
    explicit_construct = (
        None
        if observation.clinical_construct is None
        else _normalized(observation.clinical_construct)
    )
    by_endpoint_id = tuple(
        rule
        for rule in policy.rules
        if endpoint_id in {_normalized(item) for item in rule.endpoint_ids}
    )
    candidates = by_endpoint_id
    if not candidates:
        return None, ("未命中终点兼容规则",)
    if explicit_construct is not None:
        candidates = tuple(
            rule for rule in candidates if _normalized(rule.construct_id) == explicit_construct
        )
        if not candidates:
            return None, ("临床构念不兼容",)

    labels: list[str] = []
    if not any(rule.direction is observation.direction for rule in candidates):
        labels.append("方向不兼容")
    if not any(
        _normalized(observation.unit) in {_normalized(item) for item in rule.allowed_units}
        for rule in candidates
    ):
        labels.append("单位不可直接换算")
    form = _normalize_analysis_form(observation.analysis_form)
    if not any(form in rule.analysis_forms for rule in candidates):
        labels.append("分析形式不兼容")
    if labels:
        return None, tuple(labels)
    matches = tuple(
        rule
        for rule in candidates
        if rule.direction is observation.direction
        and _normalized(observation.unit) in {_normalized(item) for item in rule.allowed_units}
        and form in rule.analysis_forms
    )
    if len(matches) > 1:
        raise EndpointCompatibilityError("终点兼容规则匹配不唯一，拒绝依赖规则顺序")
    return (matches[0], ()) if matches else (None, ("未命中终点兼容规则",))


def _parsed_timepoint(observation: EndpointObservation) -> tuple[float, TimeUnit]:
    raw_unit = _normalize_time_unit(observation.time_unit)
    try:
        unit = TimeUnit(raw_unit)
    except ValueError as error:
        raise EndpointCompatibilityError(f"实际时间点单位未知：{observation.time_unit}") from error

    raw_timepoint = observation.timepoint
    inferred_unit: TimeUnit | None = None
    if isinstance(raw_timepoint, str):
        text = _compat_text(raw_timepoint, field_name="实际时间点")
        match = _TIMEPOINT_TEXT.fullmatch(text)
        if match is None:
            try:
                value = float(text)
            except ValueError as error:
                raise EndpointCompatibilityError("实际时间点无法确定") from error
        else:
            value = float(match.group(1))
            if match.group(2) is not None:
                inferred_unit = TimeUnit(_TIME_UNIT_ALIASES[match.group(2).casefold()])
    else:
        value = float(raw_timepoint)
    if not math.isfinite(value):
        raise EndpointCompatibilityError("实际时间点必须是有限数值")
    if inferred_unit is not None and inferred_unit is not unit:
        raise EndpointCompatibilityError("实际时间点的单位与时间单位字段不一致")
    return value, unit


def _timepoint_match(
    observation: EndpointObservation,
    policy: TimepointCompatibilityPolicy,
) -> tuple[TimepointCompatibilityRule | None, tuple[str, ...]]:
    try:
        value, unit = _parsed_timepoint(observation)
    except EndpointCompatibilityError as error:
        label = "时间单位不兼容" if "单位" in str(error) else "实际时间点无法确定"
        return None, (label,)
    same_unit = tuple(rule for rule in policy.rules if rule.time_unit is unit)
    if not same_unit:
        return None, ("时间单位不兼容",)
    matches = tuple(rule for rule in same_unit if rule.minimum <= value <= rule.maximum)
    if len(matches) > 1:
        raise EndpointCompatibilityError("时间窗兼容规则匹配不唯一，拒绝依赖规则顺序")
    if not matches:
        return None, ("实际时间点未命中同单位兼容窗",)
    matched = matches[0]
    if matched.canonical_value is None or value == matched.canonical_value:
        return matched, ()
    unit_zh = {
        TimeUnit.DAY: "天",
        TimeUnit.WEEK: "周",
        TimeUnit.MONTH: "个月",
        TimeUnit.YEAR: "年",
    }[unit]
    return matched, (f"实际时间点为第 {value:g} {unit_zh}，归入{matched.label_zh}",)


def match_endpoint_compatibility(
    observation: EndpointObservation | Mapping[str, Any],
    endpoint_policy: EndpointCompatibilityPolicy | Path | str | None = None,
    timepoint_policy: TimepointCompatibilityPolicy | Path | str | None = None,
) -> EndpointCompatibilityResult:
    """按当前两份策略确定性匹配；只有两条规则都命中才形成兼容键。"""

    current_observation = _validated_observation(observation)
    current_endpoint_policy = _validated_endpoint_policy(endpoint_policy)
    current_timepoint_policy = _validated_timepoint_policy(timepoint_policy)
    endpoint_rule, endpoint_labels = _endpoint_match(current_observation, current_endpoint_policy)
    timepoint_rule, timepoint_labels = _timepoint_match(
        current_observation, current_timepoint_policy
    )
    labels = tuple(dict.fromkeys((*endpoint_labels, *timepoint_labels)))
    endpoint_rule_id = None if endpoint_rule is None else endpoint_rule.rule_id
    timepoint_rule_id = None if timepoint_rule is None else timepoint_rule.rule_id
    key = (
        None
        if endpoint_rule_id is None or timepoint_rule_id is None
        else (endpoint_rule_id, timepoint_rule_id)
    )
    return EndpointCompatibilityResult(
        observation=current_observation,
        compatible=key is not None,
        compatibility_key=key,
        endpoint_rule_id=endpoint_rule_id,
        timepoint_rule_id=timepoint_rule_id,
        difference_labels_zh=labels,
        endpoint_policy_id=current_endpoint_policy.policy_id,
        endpoint_policy_version=current_endpoint_policy.version,
        timepoint_policy_id=current_timepoint_policy.policy_id,
        timepoint_policy_version=current_timepoint_policy.version,
    )


load_endpoint_compatibility = load_endpoint_compatibility_policy
load_timepoint_compatibility = load_timepoint_compatibility_policy
match_endpoint_timepoint = match_endpoint_compatibility
resolve_endpoint_compatibility = match_endpoint_compatibility


__all__ = [
    "BTrialRoleOutput",
    "EndpointAnalysisForm",
    "EndpointCompatibilityError",
    "EndpointCompatibilityPolicy",
    "EndpointCompatibilityResult",
    "EndpointCompatibilityRule",
    "EndpointDirection",
    "EndpointObservation",
    "PublicationRoleValue",
    "TimeUnit",
    "TimepointCompatibilityPolicy",
    "TimepointCompatibilityRule",
    "TrialRoleOutput",
    "TrialRoleRecord",
    "build_b_trial_role",
    "build_trial_role_output",
    "load_endpoint_compatibility",
    "load_endpoint_compatibility_policy",
    "load_timepoint_compatibility",
    "load_timepoint_compatibility_policy",
    "match_endpoint_compatibility",
    "match_endpoint_timepoint",
    "resolve_endpoint_compatibility",
]
