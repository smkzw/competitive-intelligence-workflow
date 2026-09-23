"""B 类疗效—安全性矩阵的类型化页面投影。

本模块只把已验证的疗效/安全性事实并列到同一产品—试验—组别语境中。
它不池化试验、不计算综合分数，也不产生排名。气泡图的两个坐标分别是
方向校正后的试验内疗效信号和原始安全性发生率；倒序是图形轴属性，而不是
第二个安全性数值。
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Self, cast
from urllib.parse import parse_qs, urlencode, urlsplit

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import (
    EfficacyArmRole,
    EfficacyFactRow,
    EfficacyViewError,
    validate_efficacy_fact_row,
)
from ci_workflow.reports.b.safety import (
    SafetyArmRole,
    SafetyFactRow,
    SafetyFamily,
    SafetyViewError,
    validate_safety_fact_row,
)

_BUBBLE_Y_AXIS_NOTE_ZH = "向上 = 发生率更低 = 观察到的安全性位置更有利"
_BUBBLE_X_AXIS_NOTE_ZH = "越右表示所选疗效指标的观察信号越强"
_BUBBLE_X_AXIS_LABEL_ZH = "方向校正的试验内治疗—对照疗效信号"
_BUBBLE_Y_AXIS_LABEL_ZH = "治疗组原始治疗期间不良事件发生率（倒序）"
BUBBLE_Y_AXIS_NOTE_ZH = _BUBBLE_Y_AXIS_NOTE_ZH
BUBBLE_X_AXIS_NOTE_ZH = _BUBBLE_X_AXIS_NOTE_ZH
BUBBLE_X_AXIS_LABEL_ZH = _BUBBLE_X_AXIS_LABEL_ZH
BUBBLE_Y_AXIS_LABEL_ZH = _BUBBLE_Y_AXIS_LABEL_ZH

_CONCRETE_DISCLOSURE_STATES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)
_PERCENT_UNITS = frozenset({"%", "％", "percent", "percentage"})
_PARTICIPANT_COUNT_UNITS = frozenset({"例", "participant_count"})


class MatrixViewError(ValueError):
    """疗效—安全性矩阵输入或派生视图不满足来源闭合合同。"""


BubbleViewError = MatrixViewError
ComparisonViewError = MatrixViewError
EfficacySafetyMatrixError = MatrixViewError


# Compatibility names used by different report adapters.  They all point to one
# enum, so a state cannot acquire competing semantics through a second type.
class MatrixComparisonStatus(StrEnum):
    """比较行的保守状态；不可绘制不是数值零。"""

    COMPARABLE = "comparable"
    INCOMPATIBLE = "incompatible"
    NOT_REPORTED = "not_reported"
    NOT_APPLICABLE = "not_applicable"
    PENDING_VERIFICATION = "pending_verification"

    WAITING_VERIFICATION = "pending_verification"
    UNKNOWN = "pending_verification"


MatrixCellStatus = MatrixComparisonStatus
MatrixStatus = MatrixComparisonStatus
ComparisonStatus = MatrixComparisonStatus


class SampleSizeState(StrEnum):
    """治疗组气泡样本量是否有可核验的正整数。"""

    KNOWN = "known"
    UNKNOWN = "unknown"


UnknownSampleSizeState = SampleSizeState


_DISCLOSURE_LABELS_ZH: dict[FactDisclosureState, str] = {
    FactDisclosureState.REPORTED_VALUE: "已报告数值",
    FactDisclosureState.REPORTED_ZERO: "已报告为零",
    FactDisclosureState.NOT_REPORTED: "原文未报告",
    FactDisclosureState.BELOW_REPORTING_THRESHOLD: "低于来源列示阈值",
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED: "未公开",
    FactDisclosureState.NOT_APPLICABLE: "不适用",
    FactDisclosureState.CONFLICTING: "来源存在冲突",
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE: "技术路径未解决",
    FactDisclosureState.USER_CLEARED: "用户清除，待重新核实",
}

_STATUS_LABELS_ZH: dict[MatrixComparisonStatus, str] = {
    MatrixComparisonStatus.COMPARABLE: "可比",
    MatrixComparisonStatus.INCOMPATIBLE: "不兼容",
    MatrixComparisonStatus.NOT_REPORTED: "未报告",
    MatrixComparisonStatus.NOT_APPLICABLE: "不适用",
    MatrixComparisonStatus.PENDING_VERIFICATION: "待核实",
}


def _text(value: str, *, field_name: str = "矩阵字段") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name}必须是文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _optional_text(value: str | None, *, field_name: str = "矩阵字段") -> str | None:
    return None if value is None else _text(value, field_name=field_name)


def _state_label(state: FactDisclosureState) -> str:
    return _DISCLOSURE_LABELS_ZH[state]


def _normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    return "_".join(value.strip().casefold().replace("-", "_").split())


def _coerce_safety_family(value: SafetyFamily | str) -> SafetyFamily:
    if isinstance(value, SafetyFamily):
        return value
    if not isinstance(value, str):
        raise MatrixViewError(f"安全性维度无效：{value!r}")
    token = value.strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "teae": "teae",
        "treatment_emergent_adverse_event": "teae",
        "treatment_emergent_adverse_events": "teae",
        "治疗期间不良事件": "teae",
        "sae": "sae",
        "serious_adverse_event": "sae",
        "serious_adverse_events": "sae",
        "严重不良事件": "sae",
        "aesi": "aesi",
        "adverse_event_of_special_interest": "aesi",
        "特别关注不良事件": "aesi",
        "common_ae": "common_ae",
        "common_teae": "common_ae",
        "常见不良事件": "common_ae",
    }
    try:
        return SafetyFamily(aliases.get(token, token))
    except ValueError as error:
        raise MatrixViewError(f"安全性维度无效：{value!r}") from error


def _validated_efficacy(
    value: EfficacyFactRow | Mapping[str, Any],
) -> EfficacyFactRow:
    try:
        return validate_efficacy_fact_row(value)
    except (TypeError, ValueError, ValidationError, EfficacyViewError) as error:
        raise MatrixViewError(f"疗效事实重新校验失败：{error}") from error


def _validated_safety(value: SafetyFactRow | Mapping[str, Any]) -> SafetyFactRow:
    try:
        return validate_safety_fact_row(value)
    except (TypeError, ValueError, ValidationError, SafetyViewError) as error:
        raise MatrixViewError(f"安全性事实重新校验失败：{error}") from error


def _finite_number(value: int | float | None, *, field_name: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name}不得为布尔值")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name}必须是有限数值")
    return value


def _scalar_key(value: object) -> str:
    """Stable textual key for heterogeneous timepoint scalars."""

    if isinstance(value, float):
        return format(value, ".15g")
    return str(value)


def _efficacy_group_key(row: EfficacyFactRow) -> tuple[object, ...]:
    return (
        row.product_id,
        row.trial_id,
        row.endpoint_family_id,
        row.compatibility_key,
        _scalar_key(row.actual_timepoint),
        row.actual_timepoint_unit,
        row.analysis_population,
        row.effect_measure,
        row.analysis_form,
        row.unit,
    )


def _safety_context_key(row: SafetyFactRow) -> tuple[str | None, ...]:
    family = row.family.value
    event = _normalize_token(row.comparison_term)
    return (
        f"{family}:{event}",
        _normalize_token(row.event_definition_zh) or None,
        _normalize_token(row.time_window_zh) or None,
        _normalize_token(row.analysis_population_zh) or None,
        _normalize_token(row.unit) or None,
        _normalize_token(row.denominator_semantics_zh) or None,
    )


def _safety_context_sort_key(value: tuple[str | None, ...]) -> tuple[str, ...]:
    return tuple("" if item is None else item.casefold() for item in value)


def _is_overall_teae(row: SafetyFactRow) -> bool:
    """Recognize explicit overall-TEAE identities without translating arbitrary terms."""

    tokens = {
        _normalize_token(row.term_id),
        _normalize_token(row.source_term),
        _normalize_token(row.event_definition_zh),
    }
    overall_tokens = {
        "teae_any",
        "any_teae",
        "overall_teae",
        "all_teae",
        "total_teae",
        "teae",
        "any_treatment_emergent_adverse_events",
        "all_treatment_emergent_adverse_events",
        "任何治疗期间不良事件",
        "全部治疗期间不良事件",
        "总体治疗期间不良事件",
    }
    if tokens & overall_tokens:
        return True
    return any(
        ("teae" in token or "治疗期间不良事件" in token)
        and any(
            mark in token for mark in ("any", "overall", "all", "total", "任何", "全部", "总体")
        )
        for token in tokens
    )


def _safety_rate(row: SafetyFactRow | None) -> float | None:
    """Return a rate for the y axis while retaining the original fact unchanged."""

    if row is None or row.disclosure_state not in _CONCRETE_DISCLOSURE_STATES:
        return None
    if row.value is None or row.unit is None:
        return None
    unit = _normalize_token(row.unit)
    if unit in _PERCENT_UNITS:
        rate = float(row.value)
    elif unit in _PARTICIPANT_COUNT_UNITS:
        if row.denominator is None:
            return None
        rate = float(row.value) / row.denominator * 100.0
    else:
        return None
    if not math.isfinite(rate) or not 0 <= rate <= 100:
        raise MatrixViewError("安全性发生率必须是0至100之间的有限数值")
    return rate


def _direction_corrected_signal(
    treatment: EfficacyFactRow | None,
    control: EfficacyFactRow | None,
) -> float | None:
    if treatment is None or control is None:
        return None
    # A direction-corrected difference is only meaningful inside one
    # versioned endpoint/timepoint/population/analysis bucket.  Keep both
    # facts available to the matrix, but never derive a coordinate across
    # incompatible efficacy contexts.
    if _efficacy_group_key(treatment) != _efficacy_group_key(control):
        return None
    if treatment.value is None or control.value is None:
        return None
    if treatment.direction is not control.direction:
        return None
    difference = float(treatment.value) - float(control.value)
    signal = (
        difference if treatment.direction is EndpointDirection.HIGHER_IS_BETTER else -difference
    )
    if not math.isfinite(signal):
        raise MatrixViewError("方向校正后的疗效信号必须是有限数值")
    return signal


def _sample_size_value(value: object, *, field_name: str = "治疗组样本量") -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise MatrixViewError(f"{field_name}不得为布尔值")
    if isinstance(value, str):
        token = _normalize_token(value)
        if token in {
            "unknown",
            "not_reported",
            "not_publicly_disclosed",
            "not_available",
            "not_applicable",
            "na",
            "n/a",
            "nr",
            "pending_verification",
            "未报告",
            "未知",
            "未公开",
            "不适用",
            "待核实",
        }:
            return None
        raise MatrixViewError(f"{field_name}必须是正整数或明确未知状态")
    if not isinstance(value, int):
        raise MatrixViewError(f"{field_name}必须是正整数或明确未知状态")
    if value <= 0:
        raise MatrixViewError(f"{field_name}必须是正整数；零不是未知状态")
    return value


def bubble_radius(sample_size: int | None, radius_scale: float = 1.0) -> float | None:
    """Calculate ``r = k × sqrt(N / pi)``; unknown N remains unknown."""

    if isinstance(radius_scale, bool) or not isinstance(radius_scale, (int, float)):
        raise MatrixViewError("气泡半径系数必须是大于零的有限数值")
    if not math.isfinite(float(radius_scale)) or radius_scale <= 0:
        raise MatrixViewError("气泡半径系数必须是大于零的有限数值")
    if sample_size is None:
        return None
    n = _sample_size_value(sample_size)
    if n is None:
        return None
    radius = float(radius_scale) * math.sqrt(n / math.pi)
    if not math.isfinite(radius) or radius <= 0:
        raise MatrixViewError("气泡半径必须是大于零的有限数值")
    return radius


def bubble_area(sample_size: int | None, radius_scale: float = 1.0) -> float | None:
    """Calculate the rendered area ``pi × r² = k² × N``."""

    radius = bubble_radius(sample_size, radius_scale)
    if radius is None:
        return None
    area = math.pi * radius * radius
    if not math.isfinite(area) or area <= 0:
        raise MatrixViewError("气泡面积必须是大于零的有限数值")
    return area


# Verb aliases keep one formula implementation.
calculate_bubble_radius = bubble_radius
calculate_bubble_area = bubble_area
radius_for_sample_size = bubble_radius
area_for_sample_size = bubble_area


class MatrixComparisonRow(BaseModel):
    """同一产品—试验—终点语境中的原始疗效/安全性并列事实。

    每个嵌套事实行都来自 Task 6.2/6.3 的强类型模型。该行可以因缺少
    对照、不可比定义、未报告值或未知样本量而不可绘制，但不会因此删除
    或改写仍然存在的原始事实。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    comparison_row_id: str = Field(
        validation_alias=AliasChoices("comparison_row_id", "row_id", "comparison_id", "id")
    )
    product_id: str
    trial_id: str = Field(validation_alias=AliasChoices("trial_id", "study_id"))
    target_id: str | None = Field(
        default=None, validation_alias=AliasChoices("target_id", "target")
    )
    efficacy_treatment: EfficacyFactRow | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "efficacy_treatment",
            "efficacy_treatment_row",
            "treatment_efficacy",
            "treatment_efficacy_fact",
        ),
    )
    efficacy_control: EfficacyFactRow | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "efficacy_control",
            "efficacy_control_row",
            "control_efficacy",
            "control_efficacy_fact",
        ),
    )
    safety_treatment: SafetyFactRow | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "safety_treatment",
            "safety_treatment_row",
            "treatment_safety",
            "treatment_safety_fact",
        ),
    )
    safety_control: SafetyFactRow | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "safety_control",
            "safety_control_row",
            "control_safety",
            "control_safety_fact",
        ),
    )
    treatment_sample_size: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices(
            "treatment_sample_size",
            "sample_size",
            "treatment_group_sample_size",
        ),
    )
    sample_size_state: SampleSizeState = SampleSizeState.UNKNOWN
    status: MatrixComparisonStatus | None = Field(
        default=None,
        validation_alias=AliasChoices("status", "comparison_status", "matrix_status", "state"),
    )
    comparison_status: MatrixComparisonStatus | None = None
    status_reason_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices("status_reason_zh", "reason_zh", "comparison_reason_zh"),
    )
    selection_required_reason_zh: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        status_values = tuple(
            payload[key]
            for key in ("status", "comparison_status", "matrix_status", "state")
            if key in payload and payload[key] is not None
        )
        if len(status_values) > 1:
            normalized_statuses: list[object] = []
            for status_value in status_values:
                try:
                    normalized_statuses.append(MatrixComparisonStatus(status_value).value)
                except (TypeError, ValueError):
                    normalized_statuses.append(status_value)
            if any(item != normalized_statuses[0] for item in normalized_statuses[1:]):
                raise ValueError("比较行状态字段不得互相冲突")
        aliases = {
            "study_id": "trial_id",
            "target": "target_id",
            "efficacy_treatment_row": "efficacy_treatment",
            "treatment_efficacy": "efficacy_treatment",
            "treatment_efficacy_fact": "efficacy_treatment",
            "efficacy_control_row": "efficacy_control",
            "control_efficacy": "efficacy_control",
            "control_efficacy_fact": "efficacy_control",
            "safety_treatment_row": "safety_treatment",
            "treatment_safety": "safety_treatment",
            "treatment_safety_fact": "safety_treatment",
            "safety_control_row": "safety_control",
            "control_safety": "safety_control",
            "control_safety_fact": "safety_control",
            "sample_size": "treatment_sample_size",
            "treatment_group_sample_size": "treatment_sample_size",
            "comparison_status": "status",
            "matrix_status": "status",
            "state": "status",
            "reason_zh": "status_reason_zh",
            "comparison_reason_zh": "status_reason_zh",
        }
        for source, target in aliases.items():
            if target not in payload and source in payload:
                payload[target] = payload[source]
            if source != target:
                payload.pop(source, None)
        if "comparison_status" not in payload and "status" in payload:
            payload["comparison_status"] = payload["status"]
        return payload

    @field_validator("comparison_row_id", "product_id", "trial_id")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _text(value, field_name="比较行身份")

    @field_validator("target_id", "status_reason_zh", "selection_required_reason_zh")
    @classmethod
    def _optional_row_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="比较行可选字段")

    @field_validator("treatment_sample_size")
    @classmethod
    def _sample_size_integer(cls, value: int | None) -> int | None:
        return _sample_size_value(value)

    @model_validator(mode="after")
    def _row_integrity(self) -> Self:
        efficacy_treatment = (
            None
            if self.efficacy_treatment is None
            else _validated_efficacy(self.efficacy_treatment)
        )
        efficacy_control = (
            None if self.efficacy_control is None else _validated_efficacy(self.efficacy_control)
        )
        safety_treatment = (
            None if self.safety_treatment is None else _validated_safety(self.safety_treatment)
        )
        safety_control = (
            None if self.safety_control is None else _validated_safety(self.safety_control)
        )
        object.__setattr__(self, "efficacy_treatment", efficacy_treatment)
        object.__setattr__(self, "efficacy_control", efficacy_control)
        object.__setattr__(self, "safety_treatment", safety_treatment)
        object.__setattr__(self, "safety_control", safety_control)

        facts = tuple(
            fact
            for fact in (
                efficacy_treatment,
                efficacy_control,
                safety_treatment,
                safety_control,
            )
            if fact is not None
        )
        if not facts:
            raise ValueError("比较行至少需要一条疗效或安全性事实")
        if any(
            fact.product_id != self.product_id or fact.trial_id != self.trial_id for fact in facts
        ):
            raise ValueError("比较行不得跨越产品或试验")

        if (
            efficacy_treatment is not None
            and efficacy_treatment.arm_role is not EfficacyArmRole.TREATMENT
        ):
            raise ValueError("疗效治疗列必须绑定治疗臂事实")
        if (
            efficacy_control is not None
            and efficacy_control.arm_role is not EfficacyArmRole.CONTROL
        ):
            raise ValueError("疗效对照列必须绑定对照臂事实")
        if (
            safety_treatment is not None
            and safety_treatment.arm_role is not SafetyArmRole.TREATMENT
        ):
            raise ValueError("安全性治疗列必须绑定治疗臂事实")
        if safety_control is not None and safety_control.arm_role is not SafetyArmRole.CONTROL:
            raise ValueError("安全性对照列必须绑定对照臂事实")

        derived_status = None
        if efficacy_treatment is not None and efficacy_control is not None:
            left = _efficacy_group_key(efficacy_treatment)
            right = _efficacy_group_key(efficacy_control)
            if left != right or efficacy_treatment.direction is not efficacy_control.direction:
                # Keep the source facts in one row so the matrix can explain
                # why it is not drawable.  Never reject the row or subtract
                # values from incompatible contexts.
                derived_status = MatrixComparisonStatus.INCOMPATIBLE

        if (
            safety_treatment is not None
            and safety_control is not None
            and _safety_context_key(safety_treatment) != _safety_context_key(safety_control)
        ):
            # Safety context mismatch is also a meaningful matrix state, not
            # a reason to drop one arm or silently choose a context.
            derived_status = MatrixComparisonStatus.INCOMPATIBLE

        if derived_status is None:
            derived_status = _derive_row_status(self)

        sample_state = (
            SampleSizeState.KNOWN
            if self.treatment_sample_size is not None
            else SampleSizeState.UNKNOWN
        )
        if (
            self.sample_size_state is SampleSizeState.KNOWN
            and sample_state is SampleSizeState.UNKNOWN
        ):
            raise ValueError("已知样本量状态必须携带正整数")
        if (
            self.sample_size_state is SampleSizeState.UNKNOWN
            and sample_state is SampleSizeState.KNOWN
        ):
            object.__setattr__(self, "sample_size_state", SampleSizeState.KNOWN)

        status = self.status
        if (
            status is not None
            and self.comparison_status is not None
            and status is not self.comparison_status
        ):
            raise ValueError("比较行状态字段不得互相冲突")
        if status is None:
            status = self.comparison_status
        if status is not None and status is not derived_status:
            raise ValueError("比较行状态必须与事实确定性派生状态一致")
        if status is None:
            status = derived_status
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "comparison_status", status)
        if status is not MatrixComparisonStatus.COMPARABLE and not self.status_reason_zh:
            reason = _status_reason(self)
            if reason:
                object.__setattr__(self, "status_reason_zh", reason)
        return self

    @property
    def efficacy_rows(self) -> tuple[EfficacyFactRow, ...]:
        return tuple(
            row for row in (self.efficacy_treatment, self.efficacy_control) if row is not None
        )

    @property
    def safety_rows(self) -> tuple[SafetyFactRow, ...]:
        return tuple(row for row in (self.safety_treatment, self.safety_control) if row is not None)

    @property
    def treatment_efficacy(self) -> EfficacyFactRow | None:
        return self.efficacy_treatment

    @property
    def control_efficacy(self) -> EfficacyFactRow | None:
        return self.efficacy_control

    @property
    def treatment_safety(self) -> SafetyFactRow | None:
        return self.safety_treatment

    @property
    def control_safety(self) -> SafetyFactRow | None:
        return self.safety_control

    @property
    def endpoint_family_id(self) -> str | None:
        row = self.efficacy_treatment or self.efficacy_control
        return None if row is None else row.endpoint_family_id

    @property
    def compatibility_key(self) -> tuple[str, str] | None:
        row = self.efficacy_treatment or self.efficacy_control
        return None if row is None else row.compatibility_key

    @property
    def efficacy_direction(self) -> EndpointDirection | None:
        row = self.efficacy_treatment or self.efficacy_control
        return None if row is None else row.direction

    @property
    def efficacy_signal(self) -> float | None:
        return _direction_corrected_signal(self.efficacy_treatment, self.efficacy_control)

    @property
    def direction_corrected_signal(self) -> float | None:
        return self.efficacy_signal

    @property
    def raw_treatment_efficacy_value(self) -> int | float | None:
        return None if self.efficacy_treatment is None else self.efficacy_treatment.value

    @property
    def raw_control_efficacy_value(self) -> int | float | None:
        return None if self.efficacy_control is None else self.efficacy_control.value

    @property
    def safety_rate(self) -> float | None:
        return _safety_rate(self.safety_treatment)

    @property
    def raw_safety_rate(self) -> float | None:
        return self.safety_rate

    @property
    def y_value(self) -> float | None:
        return self.safety_rate

    @property
    def x_value(self) -> float | None:
        return self.efficacy_signal

    @property
    def is_drawable(self) -> bool:
        # Coordinates are reserved for a fully comparable row.  Incomplete
        # rows intentionally retain raw values and state labels, but never
        # become a synthetic point at (0, 0).
        return (
            self.status is MatrixComparisonStatus.COMPARABLE
            and self.efficacy_signal is not None
            and self.safety_rate is not None
            and self.treatment_sample_size is not None
        )

    @property
    def source_row_ids(self) -> tuple[str, ...]:
        facts: tuple[EfficacyFactRow | SafetyFactRow, ...] = (
            *self.efficacy_rows,
            *self.safety_rows,
        )
        return tuple(fact.source_row_id for fact in facts)

    @property
    def fact_row_ids(self) -> tuple[str, ...]:
        facts: tuple[EfficacyFactRow | SafetyFactRow, ...] = (
            *self.efficacy_rows,
            *self.safety_rows,
        )
        return tuple(fact.row_id for fact in facts)

    @property
    def comparison_id(self) -> str:
        return self.comparison_row_id

    @property
    def row_id(self) -> str:
        return self.comparison_row_id

    @property
    def source_fact_row_ids(self) -> tuple[str, ...]:
        return self.fact_row_ids

    @property
    def status_label_zh(self) -> str:
        if self.status is None:  # pragma: no cover - closed in validator
            raise MatrixViewError("比较行缺少状态")
        return _STATUS_LABELS_ZH[self.status]

    @property
    def has_known_sample_size(self) -> bool:
        return self.sample_size_state is SampleSizeState.KNOWN

    @property
    def arm_id(self) -> str | None:
        return None if self.efficacy_treatment is None else self.efficacy_treatment.arm_id

    @property
    def group_id(self) -> str | None:
        return self.arm_id

    @property
    def group_label_zh(self) -> str | None:
        return None if self.efficacy_treatment is None else self.efficacy_treatment.arm_label

    @property
    def efficacy_fact_rows(self) -> tuple[EfficacyFactRow, ...]:
        return self.efficacy_rows

    @property
    def safety_fact_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.safety_rows

    @property
    def treatment_efficacy_row(self) -> EfficacyFactRow | None:
        return self.efficacy_treatment

    @property
    def control_efficacy_row(self) -> EfficacyFactRow | None:
        return self.efficacy_control

    @property
    def treatment_safety_row(self) -> SafetyFactRow | None:
        return self.safety_treatment

    @property
    def control_safety_row(self) -> SafetyFactRow | None:
        return self.safety_control

    @property
    def efficacy_treatment_fact_row_id(self) -> str | None:
        return None if self.efficacy_treatment is None else self.efficacy_treatment.row_id

    @property
    def efficacy_control_fact_row_id(self) -> str | None:
        return None if self.efficacy_control is None else self.efficacy_control.row_id

    @property
    def safety_treatment_fact_row_id(self) -> str | None:
        return None if self.safety_treatment is None else self.safety_treatment.row_id

    @property
    def safety_control_fact_row_id(self) -> str | None:
        return None if self.safety_control is None else self.safety_control.row_id


# Explicit aliases avoid adapters creating parallel row implementations.
ComparisonRow = MatrixComparisonRow
MatrixRow = MatrixComparisonRow


class UnplottableBubbleRow(BaseModel):
    """有事实但当前选择无法绘制的比较行；原因始终显式呈现。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    comparison_row_id: str = Field(validation_alias=AliasChoices("comparison_row_id", "row_id"))
    product_id: str
    trial_id: str
    reason_zh: str
    sample_size_state: SampleSizeState = SampleSizeState.UNKNOWN

    @field_validator("comparison_row_id", "product_id", "trial_id", "reason_zh")
    @classmethod
    def _unplottable_text(cls, value: str) -> str:
        return _text(value, field_name="不可绘制行字段")


UnplottableBubbleProduct = UnplottableBubbleRow


class BubblePoint(BaseModel):
    """一个治疗组事实的气泡点；不含综合分数或排名字段。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    comparison_row_id: str = Field(validation_alias=AliasChoices("comparison_row_id", "row_id"))
    product_id: str
    trial_id: str
    target_id: str | None = None
    treatment_arm_id: str = Field(
        validation_alias=AliasChoices("treatment_arm_id", "arm_id", "group_id")
    )
    treatment_arm_label: str = Field(
        validation_alias=AliasChoices("treatment_arm_label", "arm_label", "group_label_zh")
    )
    arm_role: EfficacyArmRole = EfficacyArmRole.TREATMENT
    endpoint_family_id: str = Field(
        validation_alias=AliasChoices("endpoint_family_id", "efficacy_endpoint_family_id")
    )
    efficacy_direction: EndpointDirection = Field(
        validation_alias=AliasChoices("efficacy_direction", "direction")
    )
    x_value: float = Field(
        validation_alias=AliasChoices(
            "x_value",
            "x",
            "efficacy_position",
            "efficacy_axis_value",
            "direction_corrected_signal",
            "efficacy_signal",
        )
    )
    y_value: float = Field(
        validation_alias=AliasChoices(
            "y_value",
            "y",
            "safety_rate",
            "safety_axis_value",
            "raw_safety_rate",
            "safety_position",
        )
    )
    safety_axis_reversed: bool = True
    safety_family: SafetyFamily = SafetyFamily.TEAE
    safety_term_id: str = Field(validation_alias=AliasChoices("safety_term_id", "safety_event_id"))
    safety_event_definition_zh: str | None = None
    safety_time_window_zh: str
    safety_analysis_population_zh: str
    safety_unit: str
    raw_treatment_efficacy_value: int | float | None = None
    raw_control_efficacy_value: int | float | None = None
    raw_safety_value: int | float | None = None
    treatment_sample_size: int = Field(
        validation_alias=AliasChoices(
            "treatment_sample_size",
            "sample_size",
            "treatment_group_sample_size",
            "size",
        ),
        gt=0,
    )
    radius_scale: float = Field(
        default=1.0, gt=0, validation_alias=AliasChoices("radius_scale", "bubble_scale", "k")
    )
    radius: float | None = Field(default=None, gt=0)
    area: float | None = Field(
        default=None, gt=0, validation_alias=AliasChoices("area", "bubble_area")
    )
    efficacy_fact_row_id: str = Field(
        validation_alias=AliasChoices(
            "efficacy_fact_row_id", "efficacy_fact_version_id", "efficacy_row_id"
        )
    )
    safety_fact_row_id: str = Field(
        validation_alias=AliasChoices(
            "safety_fact_row_id", "safety_fact_version_id", "safety_row_id"
        )
    )
    fact_row_ids: tuple[str, ...] = ()
    source_row_ids: tuple[str, ...] = ()

    @field_validator(
        "comparison_row_id",
        "product_id",
        "trial_id",
        "treatment_arm_id",
        "treatment_arm_label",
        "endpoint_family_id",
        "safety_term_id",
        "safety_time_window_zh",
        "safety_analysis_population_zh",
        "safety_unit",
        "efficacy_fact_row_id",
        "safety_fact_row_id",
    )
    @classmethod
    def _point_text(cls, value: str) -> str:
        return _text(value, field_name="气泡点字段")

    @field_validator("safety_family", mode="before")
    @classmethod
    def _point_safety_family(cls, value: SafetyFamily | str) -> SafetyFamily:
        return _coerce_safety_family(value)

    @field_validator(
        "x_value",
        "y_value",
        "raw_treatment_efficacy_value",
        "raw_control_efficacy_value",
        "raw_safety_value",
    )
    @classmethod
    def _point_numbers(cls, value: int | float | None) -> int | float | None:
        return _finite_number(value, field_name="气泡点数值")

    @field_validator("treatment_sample_size")
    @classmethod
    def _point_sample_size(cls, value: int) -> int:
        parsed = _sample_size_value(value)
        if parsed is None:  # pragma: no cover - field is required
            raise ValueError("气泡点必须有已知治疗组样本量")
        return parsed

    @model_validator(mode="after")
    def _point_integrity(self) -> Self:
        if self.arm_role is not EfficacyArmRole.TREATMENT:
            raise ValueError("气泡点只允许绑定治疗组")
        if not self.safety_axis_reversed:
            raise ValueError("安全性轴必须使用倒序映射")
        if not 0 <= self.y_value <= 100:
            raise ValueError("气泡点安全性发生率必须位于0至100之间")
        if not self.safety_time_window_zh or not self.safety_analysis_population_zh:
            raise ValueError("气泡点必须保存安全性时间窗和分析人群")
        if self.radius_scale <= 0 or not math.isfinite(self.radius_scale):
            raise ValueError("气泡半径系数必须是大于零的有限数值")
        expected_radius = bubble_radius(self.treatment_sample_size, self.radius_scale)
        expected_area = bubble_area(self.treatment_sample_size, self.radius_scale)
        assert expected_radius is not None and expected_area is not None
        if self.radius is None:
            object.__setattr__(self, "radius", expected_radius)
        elif not math.isclose(self.radius, expected_radius, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("气泡半径必须遵循 r = k × sqrt(N/pi)")
        if self.area is None:
            object.__setattr__(self, "area", expected_area)
        elif not math.isclose(self.area, expected_area, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("气泡面积必须等于 pi × r²")
        if self.efficacy_fact_row_id == self.safety_fact_row_id:
            raise ValueError("气泡点不得复用同一事实行")
        if len(set(self.fact_row_ids)) != len(self.fact_row_ids):
            raise ValueError("气泡点事实行标识不得重复")
        if len(set(self.source_row_ids)) != len(self.source_row_ids):
            raise ValueError("气泡点来源行标识不得重复")
        if self.efficacy_fact_row_id not in self.fact_row_ids:
            object.__setattr__(
                self, "fact_row_ids", (*self.fact_row_ids, self.efficacy_fact_row_id)
            )
        if self.safety_fact_row_id not in self.fact_row_ids:
            object.__setattr__(self, "fact_row_ids", (*self.fact_row_ids, self.safety_fact_row_id))
        return self

    @property
    def efficacy_position(self) -> float:
        return self.x_value

    @property
    def direction_corrected_value(self) -> float:
        return self.x_value

    @property
    def raw_efficacy_value(self) -> int | float | None:
        return self.raw_treatment_efficacy_value

    @property
    def raw_safety_rate(self) -> float:
        return self.y_value

    @property
    def safety_rate(self) -> float:
        return self.y_value

    @property
    def safety_position(self) -> float:
        """Raw y value; visual reversal is represented only by the boolean flag."""

        return self.y_value

    @property
    def sample_size(self) -> int:
        return self.treatment_sample_size

    @property
    def group_id(self) -> str:
        return self.treatment_arm_id

    @property
    def group_label_zh(self) -> str:
        return self.treatment_arm_label

    @property
    def efficacy_fact_version_id(self) -> str:
        return self.efficacy_fact_row_id

    @property
    def safety_fact_version_id(self) -> str:
        return self.safety_fact_row_id

    @property
    def comparison_id(self) -> str:
        return self.comparison_row_id

    @property
    def row_id(self) -> str:
        return self.comparison_row_id

    @property
    def source_fact_row_ids(self) -> tuple[str, ...]:
        return self.fact_row_ids

    @property
    def efficacy_treatment_value(self) -> int | float | None:
        return self.raw_treatment_efficacy_value

    @property
    def efficacy_control_value(self) -> int | float | None:
        return self.raw_control_efficacy_value

    @property
    def safety_original_value(self) -> int | float | None:
        return self.raw_safety_value

    @property
    def x_axis_value(self) -> float:
        return self.x_value

    @property
    def y_axis_value(self) -> float:
        return self.y_value

    @property
    def safety_axis_value(self) -> float:
        return self.y_value

    @property
    def y_axis_reversed(self) -> bool:
        return self.safety_axis_reversed

    @property
    def bubble_radius(self) -> float:
        if self.radius is None:  # pragma: no cover - closed in validator
            raise MatrixViewError("气泡点缺少半径")
        return self.radius

    @property
    def bubble_area(self) -> float:
        if self.area is None:  # pragma: no cover - closed in validator
            raise MatrixViewError("气泡点缺少面积")
        return self.area

    @property
    def treatment_group_sample_size(self) -> int:
        return self.treatment_sample_size


class BubbleMatrixView(BaseModel):
    """B 类气泡矩阵：二维观察点与不可绘制原因的同源集合。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    endpoint_family_id: str | None = None
    safety_family: SafetyFamily = SafetyFamily.TEAE
    safety_term_id: str | None = None
    radius_scale: float = Field(gt=0)
    x_axis_label_zh: str = _BUBBLE_X_AXIS_LABEL_ZH
    x_axis_note_zh: str = _BUBBLE_X_AXIS_NOTE_ZH
    y_axis_label_zh: str = _BUBBLE_Y_AXIS_LABEL_ZH
    y_axis_note_zh: str = _BUBBLE_Y_AXIS_NOTE_ZH
    safety_axis_reversed: bool = True
    comparison_rows: tuple[MatrixComparisonRow, ...] = Field(
        default=(), validation_alias=AliasChoices("comparison_rows", "rows", "matrix_rows")
    )
    points: tuple[BubblePoint, ...] = Field(
        default=(), validation_alias=AliasChoices("points", "bubble_points")
    )
    unplottable_rows: tuple[UnplottableBubbleRow, ...] = Field(
        default=(),
        validation_alias=AliasChoices("unplottable_rows", "unplottable", "unplottable_products"),
    )

    @field_validator(
        "endpoint_family_id",
        "safety_term_id",
        "x_axis_label_zh",
        "x_axis_note_zh",
        "y_axis_label_zh",
        "y_axis_note_zh",
    )
    @classmethod
    def _view_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="气泡矩阵标签")

    @field_validator("safety_family", mode="before")
    @classmethod
    def _view_safety_family(cls, value: SafetyFamily | str) -> SafetyFamily:
        return _coerce_safety_family(value)

    @model_validator(mode="after")
    def _view_integrity(self) -> Self:
        if not self.safety_axis_reversed:
            raise ValueError("气泡矩阵安全性轴必须倒序映射")
        row_by_id = {row.comparison_row_id: row for row in self.comparison_rows}
        if len(row_by_id) != len(self.comparison_rows):
            raise ValueError("气泡矩阵比较行标识不得重复")
        point_ids = tuple(point.comparison_row_id for point in self.points)
        if len(set(point_ids)) != len(point_ids):
            raise ValueError("同一比较行不得生成多个气泡点")
        if any(row_id not in row_by_id for row_id in point_ids):
            raise ValueError("气泡点必须引用当前比较行")
        unplottable_ids = tuple(item.comparison_row_id for item in self.unplottable_rows)
        if len(set(unplottable_ids)) != len(unplottable_ids):
            raise ValueError("不可绘制比较行标识不得重复")
        if set(point_ids) & set(unplottable_ids):
            raise ValueError("比较行不得同时属于可绘制点和不可绘制集合")
        return self

    @property
    def bubble_points(self) -> tuple[BubblePoint, ...]:
        return self.points

    @property
    def rows(self) -> tuple[MatrixComparisonRow, ...]:
        return self.comparison_rows

    @property
    def fact_rows(self) -> tuple[object, ...]:
        return tuple(
            fact for row in self.comparison_rows for fact in (*row.efficacy_rows, *row.safety_rows)
        )

    @property
    def is_ranked(self) -> bool:
        return False

    @property
    def has_ranking(self) -> bool:
        return False

    @property
    def x_axis(self) -> str:
        return self.x_axis_label_zh

    @property
    def x_axis_direction_zh(self) -> str:
        return self.x_axis_note_zh

    @property
    def y_axis(self) -> str:
        return self.y_axis_label_zh

    @property
    def y_axis_annotation_zh(self) -> str:
        return self.y_axis_note_zh

    @property
    def y_axis_reversed(self) -> bool:
        return self.safety_axis_reversed


BubbleView = BubbleMatrixView
EfficacySafetyBubbleMatrix = BubbleMatrixView
MatrixView = BubbleMatrixView
BubbleMatrix = BubbleMatrixView


def _incompatibility_reason(row: MatrixComparisonRow) -> str | None:
    if row.efficacy_treatment is not None and row.efficacy_control is not None:
        if _efficacy_group_key(row.efficacy_treatment) != _efficacy_group_key(
            row.efficacy_control
        ):
            return "治疗组与对照组疗效事实不属于同一兼容终点/时间窗语境"
        if row.efficacy_treatment.direction is not row.efficacy_control.direction:
            return "治疗组与对照组疗效方向不一致，无法确定方向校正信号"
    if (
        row.safety_treatment is not None
        and row.safety_control is not None
        and _safety_context_key(row.safety_treatment) != _safety_context_key(row.safety_control)
    ):
        return "治疗组与对照组安全性事实不属于同一事件/测量语境"
    return None


def _is_pending_verification_state(state: FactDisclosureState) -> bool:
    return state in {
        FactDisclosureState.CONFLICTING,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    }


def _derive_row_status(row: MatrixComparisonRow) -> MatrixComparisonStatus:
    if _incompatibility_reason(row) is not None:
        return MatrixComparisonStatus.INCOMPATIBLE

    efficacy_rows = row.efficacy_rows
    if any(fact.disclosure_state is FactDisclosureState.NOT_APPLICABLE for fact in efficacy_rows):
        return MatrixComparisonStatus.NOT_APPLICABLE
    if any(_is_pending_verification_state(fact.disclosure_state) for fact in efficacy_rows):
        return MatrixComparisonStatus.PENDING_VERIFICATION
    if row.efficacy_treatment is None or row.efficacy_control is None:
        return MatrixComparisonStatus.NOT_REPORTED
    if any(fact.disclosure_state not in _CONCRETE_DISCLOSURE_STATES for fact in efficacy_rows):
        return MatrixComparisonStatus.NOT_REPORTED

    if row.selection_required_reason_zh is not None:
        return MatrixComparisonStatus.PENDING_VERIFICATION

    safety = row.safety_treatment
    if safety is None:
        return MatrixComparisonStatus.NOT_REPORTED
    if safety.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
        return MatrixComparisonStatus.NOT_APPLICABLE
    if _is_pending_verification_state(safety.disclosure_state):
        return MatrixComparisonStatus.PENDING_VERIFICATION
    if safety.disclosure_state not in _CONCRETE_DISCLOSURE_STATES or _safety_rate(safety) is None:
        return MatrixComparisonStatus.NOT_REPORTED
    if any(
        _is_pending_verification_state(fact.disclosure_state)
        for fact in row.safety_rows
    ):
        return MatrixComparisonStatus.PENDING_VERIFICATION
    if row.treatment_sample_size is None:
        return MatrixComparisonStatus.PENDING_VERIFICATION
    return MatrixComparisonStatus.COMPARABLE


def _status_reason(row: MatrixComparisonRow) -> str:
    incompatibility = _incompatibility_reason(row)
    if incompatibility is not None:
        return incompatibility
    if any(
        fact.disclosure_state is FactDisclosureState.NOT_APPLICABLE
        for fact in row.efficacy_rows
    ):
        return "当前疗效终点对该比较行不适用"
    if any(_is_pending_verification_state(fact.disclosure_state) for fact in row.efficacy_rows):
        return "疗效事实存在冲突或技术路径未解决，待核实"
    if row.efficacy_treatment is None or row.efficacy_control is None:
        return "缺少治疗组或对照组事实，无法确定试验内疗效信号"
    if row.efficacy_treatment.value is None or row.efficacy_control.value is None:
        return "治疗组或对照组疗效值未报告，疗效信号未知"
    if row.selection_required_reason_zh is not None:
        return row.selection_required_reason_zh
    if row.safety_treatment is None:
        return "治疗组所选安全性指标发生率未报告"
    if row.safety_treatment.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
        return "治疗组安全性维度不适用"
    if _is_pending_verification_state(row.safety_treatment.disclosure_state):
        return "治疗组安全性事实存在冲突或技术路径未解决，待核实"
    if row.safety_treatment.disclosure_state not in _CONCRETE_DISCLOSURE_STATES:
        return f"治疗组安全性状态为{_state_label(row.safety_treatment.disclosure_state)}"
    if _safety_rate(row.safety_treatment) is None:
        return "治疗组安全性发生率缺少可比单位或分母"
    if any(_is_pending_verification_state(fact.disclosure_state) for fact in row.safety_rows):
        return "对照组安全性事实存在冲突或技术路径未解决，待核实"
    if row.treatment_sample_size is None:
        return "治疗组样本量未知，不以零绘制气泡"
    return ""


def _row_from_group(
    efficacy_rows: Sequence[EfficacyFactRow],
    safety_facts: Sequence[SafetyFactRow],
    *,
    target_id: str | None,
    treatment_sample_size: int | None,
    selection_required_reason_zh: str | None = None,
) -> MatrixComparisonRow:
    treatment = [row for row in efficacy_rows if row.arm_role is EfficacyArmRole.TREATMENT]
    control = [row for row in efficacy_rows if row.arm_role is EfficacyArmRole.CONTROL]
    if len(treatment) > 1 or len(control) > 1:
        raise MatrixViewError("同一比较语境不得重复绑定治疗或对照疗效事实")
    efficacy_treatment = treatment[0] if treatment else None
    efficacy_control = control[0] if control else None

    def _arm_match(
        candidates: Sequence[SafetyFactRow], efficacy: EfficacyFactRow | None
    ) -> SafetyFactRow | None:
        if not candidates:
            return None
        if efficacy is not None:
            exact = [row for row in candidates if row.arm_id == efficacy.arm_id]
            if len(exact) == 1:
                return exact[0]
            if len(exact) > 1:
                raise MatrixViewError("同一治疗组存在多个安全性事实，无法确定比较行")
            # An arm identity mismatch is not a safe fallback.  A single
            # remaining arm can still belong to a different regimen.
            return None
        if len(candidates) == 1:
            return candidates[0]
        return None

    safety_treatment = _arm_match(
        tuple(row for row in safety_facts if row.arm_role is SafetyArmRole.TREATMENT),
        efficacy_treatment,
    )
    safety_control = _arm_match(
        tuple(row for row in safety_facts if row.arm_role is SafetyArmRole.CONTROL),
        efficacy_control,
    )

    anchor = efficacy_treatment or efficacy_control
    if anchor is None:  # pragma: no cover - callers pass at least one efficacy row
        raise MatrixViewError("比较行至少需要一条疗效事实")
    row_material = [
        anchor.product_id,
        anchor.trial_id,
        anchor.endpoint_family_id,
        "::".join(anchor.compatibility_key),
        _scalar_key(anchor.actual_timepoint),
        anchor.actual_timepoint_unit,
        anchor.analysis_population or "",
        anchor.analysis_form,
        anchor.effect_measure or "not-specified",
    ]
    comparison_row_id = stable_id("matrix-comparison", *(str(item) for item in row_material))
    status = (
        MatrixComparisonStatus.INCOMPATIBLE
        if (
            efficacy_treatment is not None
            and efficacy_control is not None
            and efficacy_treatment.direction is not efficacy_control.direction
        )
        else None
    )
    row = MatrixComparisonRow(
        comparison_row_id=comparison_row_id,
        product_id=anchor.product_id,
        trial_id=anchor.trial_id,
        target_id=target_id,
        efficacy_treatment=efficacy_treatment,
        efficacy_control=efficacy_control,
        safety_treatment=safety_treatment,
        safety_control=safety_control,
        treatment_sample_size=treatment_sample_size,
        selection_required_reason_zh=selection_required_reason_zh,
        status=status,
    )
    reason = _status_reason(row)
    return row.model_copy(update={"status_reason_zh": reason or None})


def _default_endpoint_family_id(rows: Sequence[EfficacyFactRow]) -> str:
    if not rows:
        raise MatrixViewError("疗效事实为空，无法确定默认疗效终点")
    grouped: dict[str, list[EfficacyFactRow]] = {}
    for row in rows:
        grouped.setdefault(row.endpoint_family_id, []).append(row)
    primary = {
        key: values
        for key, values in grouped.items()
        if any(
            _normalize_token(row.endpoint_role) in {"primary", "主要", "主要终点"} for row in values
        )
    }
    source = primary or grouped
    scores: list[tuple[int, str]] = []
    for key, values in source.items():
        buckets: dict[tuple[object, ...], set[EfficacyArmRole]] = {}
        for row in values:
            bucket = _efficacy_group_key(row)
            buckets.setdefault(bucket, set()).add(row.arm_role)
        complete = sum(
            roles == {EfficacyArmRole.TREATMENT, EfficacyArmRole.CONTROL}
            for roles in buckets.values()
        )
        scores.append((complete, key))
    return max(scores, key=lambda item: (item[0], tuple(-ord(char) for char in item[1])))[1]


def _lookup_sample_size(
    mapping: Mapping[object, object] | None,
    *,
    product_id: str,
    trial_id: str,
    arm_id: str | None,
    efficacy_treatment: EfficacyFactRow | None,
    safety_treatment: SafetyFactRow | None,
) -> int | None:
    marker = object()
    if mapping is not None:
        fact_row_id = None if efficacy_treatment is None else efficacy_treatment.row_id
        direct_keys: tuple[object, ...] = (
            (product_id, trial_id, arm_id),
            fact_row_id,
        )
        for key in direct_keys:
            if key is None or key not in mapping:
                continue
            value: object = mapping[key]
            if isinstance(value, Mapping):
                nested_keys = (
                    arm_id,
                    fact_row_id,
                    "treatment",
                    "treatment_group",
                    "治疗组",
                    trial_id,
                    product_id,
                    "n",
                    "sample_size",
                )
                nested = marker
                for nested_key in nested_keys:
                    if nested_key is not None and nested_key in value:
                        nested = value[nested_key]
                        break
                value = None if nested is marker else nested
            return _sample_size_value(value)
        scoped = mapping.get((product_id, trial_id), marker)
        if isinstance(scoped, Mapping):
            for key in (arm_id, fact_row_id):
                if key is not None and key in scoped:
                    return _sample_size_value(scoped[key])
        # An explicitly supplied mapping is authoritative.  A broad product,
        # trial or arm key must not lend one sample size to another trial arm.
        return None
    # An event denominator can be smaller than the randomized or treated arm
    # because of the safety analysis set or event-specific evaluability.  It is
    # therefore not silently promoted to the bubble's treatment-group N.
    return None


def _select_safety_context(
    facts: Sequence[SafetyFactRow],
    *,
    product_id: str,
    trial_id: str,
    efficacy_treatment: EfficacyFactRow | None,
    efficacy_control: EfficacyFactRow | None,
    safety_family: SafetyFamily,
    safety_term_id: str | None,
    safety_event_definition_zh: str | None,
    safety_time_window_zh: str | None,
    safety_analysis_population_zh: str | None,
    safety_unit: str | None,
) -> tuple[SafetyFactRow | None, SafetyFactRow | None, str | None]:
    base_candidates = [
        fact
        for fact in facts
        if fact.product_id == product_id
        and fact.trial_id == trial_id
        and fact.family is safety_family
    ]
    candidates = [
        fact
        for fact in base_candidates
        if (safety_term_id is None or fact.term_id == safety_term_id)
        and (
            safety_event_definition_zh is None
            or fact.event_definition_zh == safety_event_definition_zh
        )
        and (safety_time_window_zh is None or fact.time_window_zh == safety_time_window_zh)
        and (
            safety_analysis_population_zh is None
            or fact.analysis_population_zh == safety_analysis_population_zh
        )
        and (safety_unit is None or fact.unit == safety_unit)
    ]
    if not candidates:
        reason = (
            "已有该安全性维度数据，但当前事件、时间窗、分析人群或分母口径未匹配，请调整筛选条件"
            if base_candidates
            else None
        )
        return None, None, reason
    contexts = {
        _safety_context_key(fact): tuple(
            item for item in candidates if _safety_context_key(item) == _safety_context_key(fact)
        )
        for fact in candidates
    }
    ordered_contexts = sorted(contexts, key=_safety_context_sort_key)
    if safety_term_id is None and safety_family is SafetyFamily.TEAE:
        overall = [
            key for key in ordered_contexts if any(_is_overall_teae(fact) for fact in contexts[key])
        ]
        if len(overall) == 1:
            ordered_contexts = overall
    if len(ordered_contexts) > 1:
        # A selected event may still have multiple windows/populations.  Do not
        # silently choose a scientific context; leave it pending until selected.
        exact_treatment_contexts = [
            key
            for key in ordered_contexts
            if any(
                fact.arm_role is SafetyArmRole.TREATMENT
                and (efficacy_treatment is None or fact.arm_id == efficacy_treatment.arm_id)
                for fact in contexts[key]
            )
        ]
        if len(exact_treatment_contexts) == 1:
            ordered_contexts = exact_treatment_contexts
        else:
            return None, None, "存在多个安全性统计口径，请先选择事件、时间窗、分析人群和分母口径"
    selected = contexts[ordered_contexts[0]]
    treatment = [fact for fact in selected if fact.arm_role is SafetyArmRole.TREATMENT]
    control = [fact for fact in selected if fact.arm_role is SafetyArmRole.CONTROL]

    def pick(
        candidates_for_arm: Sequence[SafetyFactRow], efficacy: EfficacyFactRow | None
    ) -> SafetyFactRow | None:
        if efficacy is not None:
            exact = [fact for fact in candidates_for_arm if fact.arm_id == efficacy.arm_id]
            if len(exact) == 1:
                return exact[0]
            if len(exact) > 1:
                raise MatrixViewError("同一安全性语境存在重复治疗或对照事实")
            return None
        if len(candidates_for_arm) == 1:
            return candidates_for_arm[0]
        return None

    return pick(treatment, efficacy_treatment), pick(control, efficacy_control), None


def build_matrix_comparison_rows(
    efficacy_facts: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    safety_facts: Sequence[SafetyFactRow | Mapping[str, Any]] | None = None,
    *,
    efficacy_rows: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    safety_rows: Sequence[SafetyFactRow | Mapping[str, Any]] | None = None,
    endpoint_family_id: str | None = None,
    default_endpoint_family_id: str | None = None,
    safety_family: SafetyFamily | str = SafetyFamily.TEAE,
    safety_term_id: str | None = None,
    safety_event_id: str | None = None,
    safety_event_definition_zh: str | None = None,
    safety_time_window_zh: str | None = None,
    safety_time_window: str | None = None,
    safety_analysis_population_zh: str | None = None,
    safety_analysis_population: str | None = None,
    safety_unit: str | None = None,
    treatment_sample_sizes: Mapping[object, object] | None = None,
    sample_size_by_arm: Mapping[object, object] | None = None,
    sample_sizes: Mapping[object, object] | None = None,
    treatment_group_sample_sizes: Mapping[object, object] | None = None,
    target_id_by_product: Mapping[str, str] | None = None,
    target_ids: Mapping[str, str] | None = None,
    target_by_product: Mapping[str, str] | None = None,
) -> tuple[MatrixComparisonRow, ...]:
    """Build one comparison row per product/trial/endpoint/timepoint bucket."""
    safety_family = _coerce_safety_family(safety_family)
    if (
        safety_term_id is not None
        and safety_event_id is not None
        and safety_term_id != safety_event_id
    ):
        raise MatrixViewError("安全性事件参数不得互相冲突")
    safety_term_id = safety_term_id or safety_event_id
    if (
        safety_time_window_zh is not None
        and safety_time_window is not None
        and safety_time_window_zh != safety_time_window
    ):
        raise MatrixViewError("安全性时间窗参数不得互相冲突")
    safety_time_window_zh = safety_time_window_zh or safety_time_window
    if (
        safety_analysis_population_zh is not None
        and safety_analysis_population is not None
        and safety_analysis_population_zh != safety_analysis_population
    ):
        raise MatrixViewError("安全性分析人群参数不得互相冲突")
    safety_analysis_population_zh = safety_analysis_population_zh or safety_analysis_population
    supplied_sample_maps = tuple(
        mapping
        for mapping in (
            treatment_sample_sizes,
            sample_size_by_arm,
            sample_sizes,
            treatment_group_sample_sizes,
        )
        if mapping is not None
    )
    if len(supplied_sample_maps) > 1:
        raise MatrixViewError("治疗组样本量参数不得重复提供")
    samples = supplied_sample_maps[0] if supplied_sample_maps else None
    supplied_target_maps = tuple(
        mapping
        for mapping in (target_id_by_product, target_ids, target_by_product)
        if mapping is not None
    )
    if len(supplied_target_maps) > 1:
        raise MatrixViewError("靶点映射参数不得重复提供")
    targets = supplied_target_maps[0] if supplied_target_maps else {}

    raw_efficacy = efficacy_facts if efficacy_facts is not None else efficacy_rows
    raw_safety = safety_facts if safety_facts is not None else safety_rows
    if raw_efficacy is None:
        raise MatrixViewError("必须提供疗效事实行")
    if efficacy_facts is not None and efficacy_rows is not None:
        raise MatrixViewError("疗效事实参数不得重复提供")
    if safety_facts is not None and safety_rows is not None:
        raise MatrixViewError("安全性事实参数不得重复提供")
    try:
        efficacy = tuple(_validated_efficacy(row) for row in raw_efficacy)
        safety = tuple(_validated_safety(row) for row in (raw_safety or ()))
    except MatrixViewError:
        raise
    if len({row.row_id for row in efficacy}) != len(efficacy):
        raise MatrixViewError("疗效事实输入包含重复 row_id")
    if len({row.row_id for row in safety}) != len(safety):
        raise MatrixViewError("安全性事实输入包含重复 row_id")
    if not efficacy:
        return ()
    selected_endpoint = (
        endpoint_family_id or default_endpoint_family_id or _default_endpoint_family_id(efficacy)
    )
    if selected_endpoint not in {row.endpoint_family_id for row in efficacy}:
        raise MatrixViewError("所选疗效终点不属于当前事实集合")
    selected_efficacy = tuple(
        row for row in efficacy if row.endpoint_family_id == selected_endpoint
    )

    grouped: dict[tuple[object, ...], list[EfficacyFactRow]] = {}
    for row in selected_efficacy:
        grouped.setdefault(_efficacy_group_key(row), []).append(row)

    built: list[MatrixComparisonRow] = []
    for key in sorted(grouped, key=lambda value: tuple(str(part) for part in value)):
        rows = tuple(
            sorted(grouped[key], key=lambda row: (row.arm_role.value, row.arm_id, row.row_id))
        )
        first = rows[0]
        product_id, trial_id = first.product_id, first.trial_id
        efficacy_treatment = next(
            (row for row in rows if row.arm_role is EfficacyArmRole.TREATMENT), None
        )
        efficacy_control = next(
            (row for row in rows if row.arm_role is EfficacyArmRole.CONTROL), None
        )
        safety_treatment, safety_control, selection_required_reason_zh = _select_safety_context(
            safety,
            product_id=product_id,
            trial_id=trial_id,
            efficacy_treatment=efficacy_treatment,
            efficacy_control=efficacy_control,
            safety_family=safety_family,
            safety_term_id=safety_term_id,
            safety_event_definition_zh=safety_event_definition_zh,
            safety_time_window_zh=safety_time_window_zh,
            safety_analysis_population_zh=safety_analysis_population_zh,
            safety_unit=safety_unit,
        )
        sample_size = _lookup_sample_size(
            samples,
            product_id=product_id,
            trial_id=trial_id,
            arm_id=None if efficacy_treatment is None else efficacy_treatment.arm_id,
            efficacy_treatment=efficacy_treatment,
            safety_treatment=safety_treatment,
        )
        safety_for_row = tuple(
            fact for fact in (safety_treatment, safety_control) if fact is not None
        )
        built.append(
            _row_from_group(
                rows,
                safety_for_row,
                target_id=targets.get(product_id),
                treatment_sample_size=sample_size,
                selection_required_reason_zh=selection_required_reason_zh,
            )
        )
    return tuple(built)


# Common adapter spellings.
build_comparison_rows = build_matrix_comparison_rows
build_matrix_rows = build_matrix_comparison_rows
build_comparison_matrix_rows = build_matrix_comparison_rows


def _coerce_rows_or_build(
    comparison_rows_or_efficacy: Sequence[MatrixComparisonRow | EfficacyFactRow | Mapping[str, Any]]
    | None,
    safety_facts: Sequence[SafetyFactRow | Mapping[str, Any]] | None,
    *,
    comparison_rows: Sequence[MatrixComparisonRow | Mapping[str, Any]] | None = None,
    efficacy_facts: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    efficacy_rows: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    **kwargs: Any,
) -> tuple[MatrixComparisonRow, ...]:
    supplied = tuple(
        value
        for value in (
            comparison_rows_or_efficacy,
            comparison_rows,
            efficacy_facts,
            efficacy_rows,
        )
        if value is not None
    )
    if len(supplied) > 1:
        raise MatrixViewError("比较行或疗效事实参数不得重复提供")
    values = tuple(supplied[0]) if supplied else ()
    if not supplied:
        raise MatrixViewError("必须提供比较行或疗效事实行")
    if values and all(isinstance(value, MatrixComparisonRow) for value in values):
        if safety_facts:
            raise MatrixViewError("已提供比较行时不得再次提供安全性事实")
        return tuple(
            MatrixComparisonRow.model_validate(value.model_dump(mode="python", warnings=False))
            for value in cast(tuple[MatrixComparisonRow, ...], values)
        )
    if values and all(
        isinstance(value, Mapping)
        and (
            "comparison_row_id" in value
            or "efficacy_treatment" in value
            or "efficacy_treatment_row" in value
            or "safety_treatment" in value
            or "safety_treatment_row" in value
        )
        for value in values
    ):
        if safety_facts:
            raise MatrixViewError("已提供比较行时不得再次提供安全性事实")
        return tuple(MatrixComparisonRow.model_validate(value) for value in values)
    return build_matrix_comparison_rows(values, safety_facts, **kwargs)  # type: ignore[arg-type]


def _point_from_row(
    row: MatrixComparisonRow, *, radius_scale: float, safety_family: SafetyFamily
) -> BubblePoint | None:
    if not row.is_drawable:
        return None
    assert row.efficacy_treatment is not None
    assert row.efficacy_control is not None
    assert row.safety_treatment is not None
    assert row.efficacy_signal is not None
    assert row.safety_rate is not None
    assert row.treatment_sample_size is not None
    if row.safety_treatment.time_window_zh is None:
        return None
    if row.safety_treatment.analysis_population_zh is None:
        return None
    if row.safety_treatment.unit is None:
        return None
    point = BubblePoint(
        comparison_row_id=row.comparison_row_id,
        product_id=row.product_id,
        trial_id=row.trial_id,
        target_id=row.target_id,
        treatment_arm_id=row.efficacy_treatment.arm_id,
        treatment_arm_label=row.efficacy_treatment.arm_label,
        arm_role=EfficacyArmRole.TREATMENT,
        endpoint_family_id=row.efficacy_treatment.endpoint_family_id,
        efficacy_direction=row.efficacy_treatment.direction,
        x_value=row.efficacy_signal,
        y_value=row.safety_rate,
        safety_axis_reversed=True,
        safety_family=safety_family,
        safety_term_id=row.safety_treatment.term_id,
        safety_event_definition_zh=row.safety_treatment.event_definition_zh,
        safety_time_window_zh=row.safety_treatment.time_window_zh,
        safety_analysis_population_zh=row.safety_treatment.analysis_population_zh,
        safety_unit=row.safety_treatment.unit,
        raw_treatment_efficacy_value=row.efficacy_treatment.value,
        raw_control_efficacy_value=row.efficacy_control.value,
        raw_safety_value=row.safety_treatment.value,
        treatment_sample_size=row.treatment_sample_size,
        radius_scale=radius_scale,
        efficacy_fact_row_id=row.efficacy_treatment.row_id,
        safety_fact_row_id=row.safety_treatment.row_id,
        fact_row_ids=row.fact_row_ids,
        source_row_ids=row.source_row_ids,
    )
    return point


def build_bubble_points(
    comparison_rows_or_efficacy: Sequence[MatrixComparisonRow | EfficacyFactRow | Mapping[str, Any]]
    | None = None,
    safety_facts: Sequence[SafetyFactRow | Mapping[str, Any]] | None = None,
    *,
    comparison_rows: Sequence[MatrixComparisonRow | Mapping[str, Any]] | None = None,
    efficacy_facts: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    efficacy_rows: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    radius_scale: float = 1.0,
    safety_family: SafetyFamily | str = SafetyFamily.TEAE,
    **kwargs: Any,
) -> tuple[BubblePoint, ...]:
    """Build only complete points; incomplete rows remain available to the matrix view."""
    safety_family = _coerce_safety_family(safety_family)

    if not math.isfinite(radius_scale) or radius_scale <= 0:
        raise MatrixViewError("气泡半径系数必须是大于零的有限数值")
    rows = _coerce_rows_or_build(
        comparison_rows_or_efficacy,
        safety_facts,
        comparison_rows=comparison_rows,
        efficacy_facts=efficacy_facts,
        efficacy_rows=efficacy_rows,
        safety_family=safety_family,
        **kwargs,
    )
    points = tuple(
        point
        for row in rows
        if (point := _point_from_row(row, radius_scale=radius_scale, safety_family=safety_family))
        is not None
    )
    return points


build_bubble_view_points = build_bubble_points


def build_bubble_matrix(
    comparison_rows_or_efficacy: Sequence[MatrixComparisonRow | EfficacyFactRow | Mapping[str, Any]]
    | None = None,
    safety_facts: Sequence[SafetyFactRow | Mapping[str, Any]] | None = None,
    *,
    comparison_rows: Sequence[MatrixComparisonRow | Mapping[str, Any]] | None = None,
    efficacy_facts: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    efficacy_rows: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    radius_scale: float = 1.0,
    safety_family: SafetyFamily | str = SafetyFamily.TEAE,
    **kwargs: Any,
) -> BubbleMatrixView:
    """Build the B bubble matrix without scores, ranks, or cross-trial pooling."""
    safety_family = _coerce_safety_family(safety_family)

    if not math.isfinite(radius_scale) or radius_scale <= 0:
        raise MatrixViewError("气泡半径系数必须是大于零的有限数值")
    rows = _coerce_rows_or_build(
        comparison_rows_or_efficacy,
        safety_facts,
        comparison_rows=comparison_rows,
        efficacy_facts=efficacy_facts,
        efficacy_rows=efficacy_rows,
        safety_family=safety_family,
        **kwargs,
    )
    points: list[BubblePoint] = []
    unplottable: list[UnplottableBubbleRow] = []
    for row in rows:
        point = _point_from_row(row, radius_scale=radius_scale, safety_family=safety_family)
        if point is not None:
            points.append(point)
        else:
            unplottable.append(
                UnplottableBubbleRow(
                    comparison_row_id=row.comparison_row_id,
                    product_id=row.product_id,
                    trial_id=row.trial_id,
                    reason_zh=_status_reason(row),
                    sample_size_state=row.sample_size_state,
                )
            )
    endpoint_ids = {row.endpoint_family_id for row in rows if row.endpoint_family_id is not None}
    endpoint_id = (
        next(iter(endpoint_ids)) if len(endpoint_ids) == 1 else kwargs.get("endpoint_family_id")
    )
    term_ids = {point.safety_term_id for point in points}
    term_id = next(iter(term_ids)) if len(term_ids) == 1 else kwargs.get("safety_term_id")
    return BubbleMatrixView(
        endpoint_family_id=endpoint_id,
        safety_family=safety_family,
        safety_term_id=term_id,
        radius_scale=radius_scale,
        comparison_rows=tuple(rows),
        points=tuple(points),
        unplottable_rows=tuple(unplottable),
    )


build_efficacy_safety_bubble_matrix = build_bubble_matrix
build_matrix_bubble_view = build_bubble_matrix
build_matrix_view = build_bubble_matrix
build_matrix = build_bubble_matrix
build_bubble_view = build_bubble_matrix


def validate_matrix_comparison_row(
    value: MatrixComparisonRow | Mapping[str, Any],
) -> MatrixComparisonRow:
    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, MatrixComparisonRow)
            else dict(value)
        )
        return MatrixComparisonRow.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise MatrixViewError(f"比较行重新校验失败：{error}") from error


def validate_bubble_point(value: BubblePoint | Mapping[str, Any]) -> BubblePoint:
    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, BubblePoint)
            else dict(value)
        )
        return BubblePoint.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise MatrixViewError(f"气泡点重新校验失败：{error}") from error


validate_comparison_row = validate_matrix_comparison_row
validate_bubble = validate_bubble_point


__all__ = [
    "BUBBLE_X_AXIS_LABEL_ZH",
    "BUBBLE_X_AXIS_NOTE_ZH",
    "BUBBLE_Y_AXIS_LABEL_ZH",
    "BUBBLE_Y_AXIS_NOTE_ZH",
    "BubbleMatrixView",
    "BubbleMatrix",
    "BubblePoint",
    "BubbleView",
    "BubbleViewError",
    "ComparisonRow",
    "ComparisonStatus",
    "ComparisonViewError",
    "EfficacySafetyBubbleMatrix",
    "EfficacySafetyMatrixError",
    "MatrixCellStatus",
    "MatrixComparisonRow",
    "MatrixComparisonStatus",
    "MatrixView",
    "MatrixRow",
    "MatrixStatus",
    "MatrixViewError",
    "SampleSizeState",
    "UnplottableBubbleProduct",
    "UnplottableBubbleRow",
    "UnknownSampleSizeState",
    "area_for_sample_size",
    "build_bubble_matrix",
    "build_bubble_points",
    "build_bubble_view_points",
    "build_comparison_matrix_rows",
    "build_comparison_rows",
    "build_efficacy_safety_bubble_matrix",
    "build_bubble_view",
    "build_matrix",
    "build_matrix_view",
    "build_matrix_bubble_view",
    "build_matrix_comparison_rows",
    "build_matrix_rows",
    "bubble_area",
    "bubble_radius",
    "calculate_bubble_area",
    "calculate_bubble_radius",
    "radius_for_sample_size",
    "validate_bubble",
    "validate_bubble_point",
    "validate_comparison_row",
    "validate_matrix_comparison_row",
]
 
 
# ── Task 6.4：可配置选择状态与同源派生表面 ──────────────────────────────────────


def _selection_scalar(value: object, *, field_name: str) -> int | float | str:
    if isinstance(value, bool):
        raise ValueError(f"{field_name}不得为布尔值")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{field_name}必须是有限数值")
        return value
    if isinstance(value, str):
        return _text(value, field_name=field_name)
    raise ValueError(f"{field_name}必须是文本或数值")


def _selection_ids(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values: tuple[object, ...] = tuple(value.split(",")) if "," in value else (value,)
    else:
        try:
            values = tuple(value)  # type: ignore[arg-type]
        except TypeError as error:
            raise ValueError(f"{field_name}必须是文本序列") from error
    normalized = tuple(_text(str(item), field_name=field_name) for item in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name}不得重复")
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _selection_value_token(value: object) -> str:
    return _normalize_token(str(value)) if value is not None else ""


class MatrixSelectionState(BaseModel):
    """B 类矩阵的全部可切换维度及可复现 URL 状态。

    选择状态只保存筛选条件，不改写任何疗效或安全性事实。空的产品、
    试验和靶点集合表示当前锁定快照中的全部值，而不是一个伪造的空集合。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    efficacy_endpoint_family_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "efficacy_endpoint_family_id",
            "endpoint_family_id",
            "efficacy_endpoint",
            "efficacy_endpoint_id",
            "endpoint",
        ),
    )
    efficacy_effect_form: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "efficacy_effect_form",
            "efficacy_effect",
            "effect_form",
            "efficacy_effect_measure",
            "effect_measure",
        ),
    )
    efficacy_analysis_form: str | None = Field(
        default=None,
        validation_alias=AliasChoices("efficacy_analysis_form", "analysis_form"),
    )
    efficacy_timepoint: int | float | str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "efficacy_timepoint",
            "efficacy_timepoint_value",
            "timepoint",
            "time_point",
            "actual_timepoint",
        ),
    )
    efficacy_timepoint_unit: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "efficacy_timepoint_unit",
            "timepoint_unit",
            "actual_timepoint_unit",
        ),
    )
    efficacy_analysis_population: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "efficacy_analysis_population",
            "efficacy_population",
            "analysis_population",
            "population",
        ),
    )
    safety_family: SafetyFamily = Field(
        default=SafetyFamily.TEAE,
        validation_alias=AliasChoices("safety_family", "safety_dimension", "dimension"),
    )
    safety_term_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "safety_term_id",
            "safety_event_id",
            "event_id",
            "safety_event",
            "event",
        ),
    )
    safety_event_definition_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "safety_event_definition_zh",
            "safety_event_definition",
            "event_definition_zh",
        ),
    )
    safety_time_window_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "safety_time_window_zh",
            "safety_time_window",
            "safety_window",
            "time_window",
            "window",
        ),
    )
    safety_analysis_population_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "safety_analysis_population_zh",
            "safety_analysis_population",
            "safety_population",
        ),
    )
    safety_denominator_semantics_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "safety_denominator_semantics_zh",
            "safety_denominator",
            "denominator_semantics_zh",
            "denominator",
        ),
    )
    bubble_size: str = Field(
        default="treatment_sample_size",
        validation_alias=AliasChoices(
            "bubble_size",
            "bubble_size_dimension",
            "bubble_size_field",
            "size",
        ),
    )
    product_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "product_ids",
            "selected_product_ids",
            "products",
            "selected_products",
            "product",
        ),
    )
    trial_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "trial_ids",
            "selected_trial_ids",
            "trials",
            "selected_trials",
            "trial",
        ),
    )
    target_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "target_ids",
            "selected_target_ids",
            "targets",
            "selected_targets",
            "target",
        ),
    )
    snapshot_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("snapshot_id", "locked_snapshot_id", "report_snapshot_id"),
    )

    @field_validator(
        "efficacy_endpoint_family_id",
        "efficacy_effect_form",
        "efficacy_analysis_form",
        "efficacy_timepoint_unit",
        "efficacy_analysis_population",
        "safety_term_id",
        "safety_event_definition_zh",
        "safety_time_window_zh",
        "safety_analysis_population_zh",
        "safety_denominator_semantics_zh",
        "snapshot_id",
    )
    @classmethod
    def _selection_optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, field_name="矩阵选择字段")

    @field_validator("efficacy_timepoint")
    @classmethod
    def _selection_timepoint(
        cls, value: int | float | str | None
    ) -> int | float | str | None:
        return None if value is None else _selection_scalar(value, field_name="疗效时间点")

    @field_validator("safety_family", mode="before")
    @classmethod
    def _selection_safety_family(cls, value: SafetyFamily | str) -> SafetyFamily:
        return _coerce_safety_family(value)

    @field_validator("bubble_size", mode="before")
    @classmethod
    def _selection_bubble_size(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("气泡大小维度必须是文本")
        token = _selection_value_token(value)
        aliases = {
            "treatment_sample_size": "treatment_sample_size",
            "treatment_group_sample_size": "treatment_sample_size",
            "sample_size": "treatment_sample_size",
            "treatment_n": "treatment_sample_size",
            "n": "treatment_sample_size",
            "治疗组样本量": "treatment_sample_size",
            "样本量": "treatment_sample_size",
        }
        normalized = aliases.get(token, aliases.get(value.strip()))
        if normalized is None:
            raise ValueError("当前矩阵仅支持按治疗组样本量缩放气泡")
        return normalized

    @field_validator("product_ids", "trial_ids", "target_ids", mode="before")
    @classmethod
    def _selection_id_tuple(cls, value: object, info: Any) -> tuple[str, ...]:
        return _selection_ids(value, field_name=str(info.field_name))

    @model_validator(mode="after")
    def _selection_integrity(self) -> Self:
        if self.efficacy_timepoint is None and self.efficacy_timepoint_unit is not None:
            raise ValueError("疗效时间点单位必须绑定时间点")
        return self

    @classmethod
    def from_facts(
        cls,
        efficacy_facts: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
        safety_facts: Sequence[SafetyFactRow | Mapping[str, Any]] | None = None,
        *,
        comparison_rows: Sequence[MatrixComparisonRow | Mapping[str, Any]] | None = None,
        snapshot_id: str | None = None,
        locked_snapshot_id: str | None = None,
        target_id_by_product: Mapping[str, str] | None = None,
        target_ids: Mapping[str, str] | None = None,
    ) -> Self:
        """从当前锁定快照事实确定默认选择，不从模板猜测临床语义。"""

        if (
            snapshot_id is not None
            and locked_snapshot_id is not None
            and snapshot_id != locked_snapshot_id
        ):
            raise MatrixViewError("锁定快照参数不得互相冲突")
        effective_snapshot_id = snapshot_id or locked_snapshot_id
        efficacy: tuple[EfficacyFactRow, ...]
        safety: tuple[SafetyFactRow, ...]
        if comparison_rows is not None:
            rows = tuple(validate_matrix_comparison_row(row) for row in comparison_rows)
            efficacy = tuple(fact for row in rows for fact in row.efficacy_rows)
            safety = tuple(fact for row in rows for fact in row.safety_rows)
        else:
            if efficacy_facts is None:
                raise MatrixViewError("默认矩阵选择必须绑定当前锁定快照事实")
            efficacy = tuple(_validated_efficacy(row) for row in efficacy_facts)
            safety = tuple(_validated_safety(row) for row in (safety_facts or ()))
        if not efficacy:
            raise MatrixViewError("当前锁定快照没有疗效事实，无法确定矩阵默认选择")

        endpoint_family_id = _default_endpoint_family_id(efficacy)
        endpoint_rows = tuple(
            row for row in efficacy if row.endpoint_family_id == endpoint_family_id
        )
        anchor = min(
            endpoint_rows,
            key=lambda row: (
                _efficacy_group_key(row),
                row.arm_role.value,
                row.arm_id,
                row.row_id,
            ),
        )
        effect_form = anchor.effect_measure or anchor.analysis_form

        ordered_safety = tuple(
            sorted(
                safety,
                key=lambda row: (
                    row.family.value,
                    row.term_id,
                    row.event_definition_zh or "",
                    row.time_window_zh or "",
                    row.analysis_population_zh or "",
                    row.denominator_semantics_zh or "",
                    row.arm_role.value,
                    row.arm_id,
                    row.row_id,
                ),
            )
        )
        overall_teae = tuple(
            row
            for row in ordered_safety
            if row.family is SafetyFamily.TEAE and _is_overall_teae(row)
        )
        overall_contexts = {_safety_context_key(row) for row in overall_teae}
        safety_anchor = overall_teae[0] if len(overall_contexts) == 1 else None
        mapped_targets = target_id_by_product or target_ids or {}
        return cls(
            efficacy_endpoint_family_id=endpoint_family_id,
            efficacy_effect_form=effect_form,
            efficacy_analysis_form=anchor.analysis_form,
            efficacy_timepoint=anchor.actual_timepoint,
            efficacy_timepoint_unit=anchor.actual_timepoint_unit,
            efficacy_analysis_population=anchor.analysis_population,
            safety_family=SafetyFamily.TEAE,
            safety_term_id=None if safety_anchor is None else safety_anchor.term_id,
            safety_event_definition_zh=(
                None if safety_anchor is None else safety_anchor.event_definition_zh
            ),
            safety_time_window_zh=None if safety_anchor is None else safety_anchor.time_window_zh,
            safety_analysis_population_zh=(
                None if safety_anchor is None else safety_anchor.analysis_population_zh
            ),
            safety_denominator_semantics_zh=(
                None if safety_anchor is None else safety_anchor.denominator_semantics_zh
            ),
            product_ids=tuple(sorted({row.product_id for row in efficacy})),
            trial_ids=tuple(sorted({row.trial_id for row in efficacy})),
            target_ids=tuple(sorted(set(mapped_targets.values()))),
            snapshot_id=effective_snapshot_id,
        )

    from_snapshot = from_facts
    default_for_facts = from_facts

    @property
    def endpoint_family_id(self) -> str | None:
        return self.efficacy_endpoint_family_id
    @property
    def efficacy_endpoint(self) -> str | None:
        return self.efficacy_endpoint_family_id

    @property
    def efficacy_endpoint_id(self) -> str | None:
        return self.efficacy_endpoint_family_id

    @property
    def effect_form(self) -> str | None:
        return self.efficacy_effect_form
    @property
    def efficacy_effect(self) -> str | None:
        return self.efficacy_effect_form

    @property
    def effect_measure(self) -> str | None:
        return self.efficacy_effect_form

    @property
    def timepoint(self) -> int | float | str | None:
        return self.efficacy_timepoint

    @property
    def timepoint_unit(self) -> str | None:
        return self.efficacy_timepoint_unit

    @property
    def analysis_population(self) -> str | None:
        return self.efficacy_analysis_population
    @property
    def efficacy_population(self) -> str | None:
        return self.efficacy_analysis_population

    @property
    def safety_event_id(self) -> str | None:
        return self.safety_term_id
    @property
    def safety_event(self) -> str | None:
        return self.safety_term_id

    @property
    def safety_time_window(self) -> str | None:
        return self.safety_time_window_zh
    @property
    def safety_window(self) -> str | None:
        return self.safety_time_window_zh

    @property
    def safety_analysis_population(self) -> str | None:
        return self.safety_analysis_population_zh
    @property
    def safety_dimension(self) -> SafetyFamily:
        return self.safety_family

    @property
    def safety_denominator(self) -> str | None:
        return self.safety_denominator_semantics_zh
    @property
    def safety_denominator_semantics(self) -> str | None:
        return self.safety_denominator_semantics_zh

    @property
    def bubble_size_dimension(self) -> str:
        return self.bubble_size

    @property
    def products(self) -> tuple[str, ...]:
        return self.product_ids

    @property
    def trials(self) -> tuple[str, ...]:
        return self.trial_ids

    @property
    def targets(self) -> tuple[str, ...]:
        return self.target_ids

    def to_url_params(self) -> dict[str, str]:
        """Return stable, sorted-by-key-friendly URL parameter values."""

        params: dict[str, str] = {}
        scalar_values = (
            ("endpoint", self.efficacy_endpoint_family_id),
            ("effect_form", self.efficacy_effect_form),
            ("analysis_form", self.efficacy_analysis_form),
            (
                "timepoint",
                None if self.efficacy_timepoint is None else _scalar_key(self.efficacy_timepoint),
            ),
            ("timepoint_unit", self.efficacy_timepoint_unit),
            ("population", self.efficacy_analysis_population),
            ("safety_family", self.safety_family.value),
            ("event", self.safety_term_id),
            ("event_definition", self.safety_event_definition_zh),
            ("window", self.safety_time_window_zh),
            ("safety_population", self.safety_analysis_population_zh),
            ("denominator", self.safety_denominator_semantics_zh),
            ("bubble_size", self.bubble_size),
            ("snapshot", self.snapshot_id),
        )
        for key, value in scalar_values:
            if value is not None:
                params[key] = str(value)
        list_values = (
            ("products", self.product_ids),
            ("trials", self.trial_ids),
            ("targets", self.target_ids),
        )
        for key, values in list_values:
            if values:
                params[key] = ",".join(values)
        return {key: params[key] for key in sorted(params)}

    @property
    def url_params(self) -> dict[str, str]:
        return self.to_url_params()
    @property
    def url_state(self) -> dict[str, str]:
        return self.to_url_params()

    def to_url_query(self) -> str:
        return urlencode(self.to_url_params(), doseq=False)

    to_query_string = to_url_query

    def to_url(self, route: str = "/b/efficacy-safety-matrix") -> str:
        if not isinstance(route, str) or not route.strip():
            raise MatrixViewError("矩阵 URL 路由不能为空")
        normalized_route = route.strip()
        query = self.to_url_query()
        return f"{normalized_route}?{query}" if query else normalized_route

    @classmethod
    def from_url(cls, url: str) -> Self:
        if not isinstance(url, str) or not url.strip():
            raise MatrixViewError("矩阵 URL 不能为空")
        parsed = urlsplit(url if "://" in url or "?" in url else f"?{url.lstrip('?')}")
        query = parse_qs(parsed.query, keep_blank_values=True)
        allowed_keys = frozenset(
            {
                "endpoint",
                "efficacy_endpoint_family_id",
                "efficacy_endpoint",
                "efficacy_endpoint_id",
                "effect_form",
                "efficacy_effect_form",
                "efficacy_effect",
                "effect_measure",
                "analysis_form",
                "efficacy_analysis_form",
                "timepoint",
                "efficacy_timepoint",
                "efficacy_timepoint_value",
                "time_point",
                "timepoint_unit",
                "efficacy_timepoint_unit",
                "population",
                "efficacy_analysis_population",
                "efficacy_population",
                "safety_family",
                "safety_dimension",
                "dimension",
                "event",
                "safety_term_id",
                "safety_event_id",
                "safety_event",
                "event_definition",
                "safety_event_definition_zh",
                "safety_event_definition",
                "window",
                "safety_time_window_zh",
                "safety_time_window",
                "safety_window",
                "safety_population",
                "safety_analysis_population_zh",
                "safety_analysis_population",
                "denominator",
                "safety_denominator_semantics_zh",
                "safety_denominator",
                "denominator_semantics_zh",
                "bubble_size",
                "bubble_size_dimension",
                "bubble_size_field",
                "products",
                "product_ids",
                "selected_product_ids",
                "selected_products",
                "trials",
                "trial_ids",
                "selected_trial_ids",
                "selected_trials",
                "targets",
                "target_ids",
                "selected_target_ids",
                "selected_targets",
                "snapshot",
                "snapshot_id",
                "locked_snapshot_id",
                "report_snapshot_id",
            }
        )
        unknown_keys = set(query) - allowed_keys
        if unknown_keys:
            raise MatrixViewError(f"矩阵 URL 包含未知字段：{sorted(unknown_keys)}")

        def first(*keys: str) -> str | None:
            present = [(key, value) for key in keys for value in query.get(key, ())]
            if len(present) > 1:
                raise MatrixViewError(f"矩阵 URL 字段重复：{','.join(key for key, _ in present)}")
            return None if not present or not present[0][1] else present[0][1]


        def scalar_timepoint(value: str | None) -> int | float | str | None:
            if value is None:
                return None
            try:
                if value.strip().lstrip("-").isdigit():
                    return int(value)
                parsed_float = float(value)
                if math.isfinite(parsed_float):
                    return parsed_float
            except ValueError:
                pass
            return value

        products = first("products", "product_ids", "selected_product_ids")
        trials = first("trials", "trial_ids", "selected_trial_ids")
        targets = first("targets", "target_ids", "selected_target_ids")
        return cls(
            efficacy_endpoint_family_id=first(
                "endpoint",
                "efficacy_endpoint_family_id",
                "efficacy_endpoint",
                "efficacy_endpoint_id",
            ),
            efficacy_effect_form=first(
                "effect_form",
                "efficacy_effect_form",
                "efficacy_effect",
                "effect_measure",
            ),
            efficacy_analysis_form=first("analysis_form", "efficacy_analysis_form"),
            efficacy_timepoint=scalar_timepoint(
                first(
                    "timepoint",
                    "efficacy_timepoint",
                    "efficacy_timepoint_value",
                    "time_point",
                )
            ),
            efficacy_timepoint_unit=first("timepoint_unit", "efficacy_timepoint_unit"),
            efficacy_analysis_population=first(
                "population",
                "efficacy_analysis_population",
                "efficacy_population",
            ),
            safety_family=_coerce_safety_family(
                first("safety_family", "safety_dimension", "dimension") or SafetyFamily.TEAE
            ),
            safety_term_id=first(
                "event",
                "safety_term_id",
                "safety_event_id",
                "safety_event",
            ),
            safety_event_definition_zh=first(
                "event_definition",
                "safety_event_definition_zh",
                "safety_event_definition",
            ),
            safety_time_window_zh=first(
                "window",
                "safety_time_window_zh",
                "safety_window",
                "safety_time_window",
            ),
            safety_analysis_population_zh=first(
                "safety_population",
                "safety_analysis_population_zh",
                "safety_analysis_population",
            ),
            safety_denominator_semantics_zh=first(
                "denominator",
                "safety_denominator_semantics_zh",
                "safety_denominator",
                "denominator_semantics_zh",
            ),
            bubble_size=first("bubble_size", "bubble_size_dimension", "bubble_size_field")
            or "treatment_sample_size",
            product_ids=() if products is None else tuple(products.split(",")),
            trial_ids=() if trials is None else tuple(trials.split(",")),
            target_ids=() if targets is None else tuple(targets.split(",")),
            snapshot_id=first(
                "snapshot",
                "snapshot_id",
                "locked_snapshot_id",
                "report_snapshot_id",
            ),
        )

    from_url_query = from_url


MatrixSelection = MatrixSelectionState
BubbleMatrixSelectionState = MatrixSelectionState


def _selection_matches_efficacy(
    row: EfficacyFactRow, selection: MatrixSelectionState
) -> bool:
    if (
        selection.efficacy_endpoint_family_id is not None
        and row.endpoint_family_id != selection.efficacy_endpoint_family_id
    ):
        return False
    if selection.efficacy_effect_form is not None:
        forms = {row.effect_measure, row.analysis_form}
        if selection.efficacy_effect_form not in forms:
            return False
    if (
        selection.efficacy_analysis_form is not None
        and row.analysis_form != selection.efficacy_analysis_form
    ):
        return False
    if selection.efficacy_timepoint is not None:
        if _scalar_key(row.actual_timepoint) != _scalar_key(selection.efficacy_timepoint):
            return False
        if (
            selection.efficacy_timepoint_unit is not None
            and row.actual_timepoint_unit != selection.efficacy_timepoint_unit
        ):
            return False
    return not (
        selection.efficacy_analysis_population is not None
        and row.analysis_population != selection.efficacy_analysis_population
    )


def _selection_matches_safety(
    row: SafetyFactRow, selection: MatrixSelectionState
) -> bool:
    if row.family is not selection.safety_family:
        return False
    if (
        selection.safety_term_id is not None
        and selection.safety_term_id
        not in {row.term_id, row.source_term, row.comparison_term}
    ):
        return False
    if (
        selection.safety_event_definition_zh is not None
        and row.event_definition_zh != selection.safety_event_definition_zh
    ):
        return False
    if (
        selection.safety_time_window_zh is not None
        and row.time_window_zh != selection.safety_time_window_zh
    ):
        return False
    if (
        selection.safety_analysis_population_zh is not None
        and row.analysis_population_zh != selection.safety_analysis_population_zh
    ):
        return False
    return not (
        selection.safety_denominator_semantics_zh is not None
        and row.denominator_semantics_zh != selection.safety_denominator_semantics_zh
    )


class MatrixCell(BaseModel):
    """完整表中的一行同源单元；不可绘制时保留状态而不伪造坐标。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    comparison_row_id: str = Field(validation_alias=AliasChoices("comparison_row_id", "row_id"))
    product_id: str
    trial_id: str
    target_id: str | None = None
    status: MatrixComparisonStatus
    reason_zh: str
    comparison_row: MatrixComparisonRow | None = None
    point: BubblePoint | None = None
    fact_row_ids: tuple[str, ...] = ()
    source_row_ids: tuple[str, ...] = ()

    @field_validator("comparison_row_id", "product_id", "trial_id", "reason_zh")
    @classmethod
    def _cell_text(cls, value: str) -> str:
        return _text(value, field_name="矩阵单元字段")

    @model_validator(mode="after")
    def _cell_integrity(self) -> Self:
        if len(set(self.fact_row_ids)) != len(self.fact_row_ids):
            raise ValueError("矩阵单元事实行标识不得重复")
        if len(set(self.source_row_ids)) != len(self.source_row_ids):
            raise ValueError("矩阵单元来源行标识不得重复")
        if self.comparison_row is not None:
            if self.comparison_row.comparison_row_id != self.comparison_row_id:
                raise ValueError("矩阵单元必须绑定同一比较行")
            if not self.fact_row_ids:
                object.__setattr__(self, "fact_row_ids", self.comparison_row.fact_row_ids)
            elif set(self.comparison_row.fact_row_ids) != set(self.fact_row_ids):
                raise ValueError("矩阵单元事实行必须与比较行一致")
            if not self.source_row_ids:
                object.__setattr__(self, "source_row_ids", self.comparison_row.source_row_ids)
            elif set(self.comparison_row.source_row_ids) != set(self.source_row_ids):
                raise ValueError("矩阵单元来源行必须与比较行一致")
        if self.point is not None and self.point.comparison_row_id != self.comparison_row_id:
            raise ValueError("矩阵单元气泡点必须引用同一比较行")
        if self.status is not MatrixComparisonStatus.COMPARABLE and self.point is not None:
            raise ValueError("不可比矩阵单元不得携带气泡点")
        return self

    @property
    def row_id(self) -> str:
        return self.comparison_row_id
    @property
    def original_row(self) -> MatrixComparisonRow | None:
        return self.comparison_row

    @property
    def efficacy_treatment(self) -> EfficacyFactRow | None:
        return None if self.comparison_row is None else self.comparison_row.efficacy_treatment

    @property
    def efficacy_control(self) -> EfficacyFactRow | None:
        return None if self.comparison_row is None else self.comparison_row.efficacy_control

    @property
    def safety_treatment(self) -> SafetyFactRow | None:
        return None if self.comparison_row is None else self.comparison_row.safety_treatment

    @property
    def safety_control(self) -> SafetyFactRow | None:
        return None if self.comparison_row is None else self.comparison_row.safety_control

    @property
    def raw_treatment_efficacy_value(self) -> int | float | None:
        return (
            None
            if self.comparison_row is None
            else self.comparison_row.raw_treatment_efficacy_value
        )

    @property
    def raw_control_efficacy_value(self) -> int | float | None:
        return (
            None
            if self.comparison_row is None
            else self.comparison_row.raw_control_efficacy_value
        )

    @property
    def raw_safety_rate(self) -> float | None:
        return None if self.comparison_row is None else self.comparison_row.raw_safety_rate

    @property
    def comparison_status(self) -> MatrixComparisonStatus:
        return self.status

    @property
    def status_reason_zh(self) -> str:
        return self.reason_zh

    @property
    def status_label_zh(self) -> str:
        return _STATUS_LABELS_ZH[self.status]

    @property
    def x_value(self) -> float | None:
        return None if self.point is None else self.point.x_value

    @property
    def y_value(self) -> float | None:
        return None if self.point is None else self.point.y_value

    @property
    def radius(self) -> float | None:
        return None if self.point is None else self.point.radius

    @property
    def area(self) -> float | None:
        return None if self.point is None else self.point.area

    @property
    def is_drawable(self) -> bool:
        return self.point is not None

    @property
    def is_ranked(self) -> bool:
        return False


MatrixTableRow = MatrixCell
MatrixComparisonCell = MatrixCell


class MatrixPrompt(BaseModel):
    """与一个比较行绑定的中文提示；不把缺失事实转成数值。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    comparison_row_id: str = Field(validation_alias=AliasChoices("comparison_row_id", "row_id"))
    status: MatrixComparisonStatus
    message_zh: str
    fact_row_ids: tuple[str, ...] = ()
    source_row_ids: tuple[str, ...] = ()

    @field_validator("comparison_row_id", "message_zh")
    @classmethod
    def _prompt_text(cls, value: str) -> str:
        return _text(value, field_name="矩阵提示字段")

    @property
    def row_id(self) -> str:
        return self.comparison_row_id

    @property
    def status_label_zh(self) -> str:
        return _STATUS_LABELS_ZH[self.status]
    @property
    def text_zh(self) -> str:
        return self.message_zh

    @property
    def prompt_zh(self) -> str:
        return self.message_zh

    @property
    def reason_zh(self) -> str:
        return self.message_zh

    @property
    def is_ranked(self) -> bool:
        return False


MatrixNotice = MatrixPrompt
MatrixTooltip = MatrixPrompt


class MatrixEvidenceLink(BaseModel):
    """一条证据入口；同时携带比较行 ID 与事实行 ID。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    comparison_row_id: str = Field(validation_alias=AliasChoices("comparison_row_id", "row_id"))
    fact_row_id: str = Field(validation_alias=AliasChoices("fact_row_id", "evidence_fact_row_id"))
    source_row_id: str
    source_version_id: str
    source_locator: EvidenceLocator
    label_zh: str
    href: str | None = None

    @field_validator(
        "comparison_row_id",
        "fact_row_id",
        "source_row_id",
        "source_version_id",
        "label_zh",
    )
    @classmethod
    def _evidence_text(cls, value: str) -> str:
        return _text(value, field_name="矩阵证据字段")

    @field_validator("href")
    @classmethod
    def _evidence_href(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, field_name="矩阵证据链接")

    @property
    def row_id(self) -> str:
        return self.comparison_row_id

    @property
    def fact_version_id(self) -> str:
        return self.fact_row_id

    @property
    def url(self) -> str | None:
        return self.href
    @property
    def evidence_row_id(self) -> str:
        return self.fact_row_id


MatrixEvidence = MatrixEvidenceLink
MatrixEvidenceReference = MatrixEvidenceLink


def _prompt_for_row(row: MatrixComparisonRow) -> str:
    if row.status is MatrixComparisonStatus.COMPARABLE:
        return "当前组合可绘制；气泡图仅用于同一试验内观察，不构成跨试验头对头结论"
    reason = row.status_reason_zh or _status_reason(row)
    return f"{row.status_label_zh}：{reason}；当前组合不生成气泡坐标"


def _fact_evidence_link(
    comparison_row_id: str,
    fact: EfficacyFactRow | SafetyFactRow,
) -> MatrixEvidenceLink:
    domain = "疗效" if isinstance(fact, EfficacyFactRow) else "安全性"
    return MatrixEvidenceLink(
        comparison_row_id=comparison_row_id,
        fact_row_id=fact.row_id,
        source_row_id=fact.source_row_id,
        source_version_id=fact.source_version_id,
        source_locator=fact.source_locator,
        label_zh=f"{domain}事实 {fact.row_id}",
        href=fact.source_locator.url,
    )


def _target_mapping_tuple(mapping: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    if mapping is None:
        return ()
    return tuple(
        sorted(
            ((_text(str(key), field_name="产品标识"), _text(str(value), field_name="靶点标识"))
             for key, value in mapping.items()),
            key=lambda item: (item[0].casefold(), item[0], item[1]),
        )
    )


def _select_target_mapping(
    target_id_by_product: Mapping[str, str] | None,
    target_ids: Mapping[str, str] | None,
    target_by_product: Mapping[str, str] | None,
) -> Mapping[str, str]:
    supplied = tuple(
        item for item in (target_id_by_product, target_ids, target_by_product) if item is not None
    )
    if len(supplied) > 1:
        raise MatrixViewError("靶点映射参数不得重复提供")
    return supplied[0] if supplied else {}


def _select_sample_mapping(
    treatment_sample_sizes: Mapping[object, object] | None,
    sample_size_by_arm: Mapping[object, object] | None,
    sample_sizes: Mapping[object, object] | None,
    treatment_group_sample_sizes: Mapping[object, object] | None,
) -> Mapping[object, object] | None:
    supplied = tuple(
        item
        for item in (
            treatment_sample_sizes,
            sample_size_by_arm,
            sample_sizes,
            treatment_group_sample_sizes,
        )
        if item is not None
    )
    if len(supplied) > 1:
        raise MatrixViewError("治疗组样本量参数不得重复提供")
    return supplied[0] if supplied else None

def _validated_selection_state(
    value: MatrixSelectionState | Mapping[str, Any],
) -> MatrixSelectionState:
    raw = (
        value.model_dump(mode="python", warnings=False)
        if isinstance(value, MatrixSelectionState)
        else value
    )
    try:
        return MatrixSelectionState.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise MatrixViewError(f"矩阵选择状态重新校验失败：{error}") from error


def _selection_for_build(
    selection: MatrixSelectionState | Mapping[str, Any] | None,
    *,
    default: MatrixSelectionState,
) -> MatrixSelectionState:
    if selection is None:
        return default
    parsed = _validated_selection_state(selection)
    updates: dict[str, Any] = {}
    for field_name in (
        "efficacy_endpoint_family_id",
        "efficacy_effect_form",
        "efficacy_analysis_form",
        "efficacy_timepoint",
        "efficacy_timepoint_unit",
        "efficacy_analysis_population",
    ):
        if getattr(parsed, field_name) is None and getattr(default, field_name) is not None:
            updates[field_name] = getattr(default, field_name)
    safety_family_changed = parsed.safety_family is not default.safety_family
    for field_name in (
        "safety_term_id",
        "safety_event_definition_zh",
        "safety_time_window_zh",
        "safety_analysis_population_zh",
        "safety_denominator_semantics_zh",
    ):
        if (
            not safety_family_changed
            and getattr(parsed, field_name) is None
            and getattr(default, field_name) is not None
        ):
            updates[field_name] = getattr(default, field_name)
    if isinstance(selection, Mapping) and not any(
        key in selection for key in ("safety_family", "safety_dimension", "dimension")
    ):
        updates["safety_family"] = default.safety_family
    for field_name in ("product_ids", "trial_ids", "target_ids"):
        if not getattr(parsed, field_name) and getattr(default, field_name):
            updates[field_name] = getattr(default, field_name)
    if parsed.snapshot_id is None and default.snapshot_id is not None:
        updates["snapshot_id"] = default.snapshot_id
    if updates:
        parsed = MatrixSelectionState.model_validate(
            {**parsed.model_dump(mode="python", warnings=False), **updates}
        )
    return parsed


def _comparison_row_matches_selection(
    row: MatrixComparisonRow,
    selection: MatrixSelectionState,
) -> bool:
    if selection.product_ids and row.product_id not in selection.product_ids:
        return False
    if selection.trial_ids and row.trial_id not in selection.trial_ids:
        return False
    if selection.target_ids and row.target_id not in selection.target_ids:
        return False
    if row.efficacy_rows and not all(
        _selection_matches_efficacy(fact, selection) for fact in row.efficacy_rows
    ):
        return False
    if not row.efficacy_rows:
        return False
    if row.safety_rows and not all(
        _selection_matches_safety(fact, selection) for fact in row.safety_rows
    ):
        return False
    return not (
        not row.safety_rows
        and any(
            value is not None
            for value in (
                selection.safety_term_id,
                selection.safety_event_definition_zh,
                selection.safety_time_window_zh,
                selection.safety_analysis_population_zh,
                selection.safety_denominator_semantics_zh,
            )
        )
    )


def _fallback_rows_for_selection(
    fallback_rows: Sequence[MatrixComparisonRow],
    selection: MatrixSelectionState,
) -> tuple[MatrixComparisonRow, ...]:
    return tuple(row for row in fallback_rows if _comparison_row_matches_selection(row, selection))


def _rows_for_selection(
    efficacy_facts: Sequence[EfficacyFactRow],
    safety_facts: Sequence[SafetyFactRow],
    selection: MatrixSelectionState,
    *,
    sample_sizes: Mapping[object, object] | None,
    target_mapping: Mapping[str, str],
    fallback_rows: Sequence[MatrixComparisonRow] = (),
) -> tuple[MatrixComparisonRow, ...]:
    fallback_selected = _fallback_rows_for_selection(fallback_rows, selection)
    if fallback_selected:
        return fallback_selected
    selected_efficacy = tuple(
        row for row in efficacy_facts if _selection_matches_efficacy(row, selection)
    )
    # Keep the complete safety fact set until context resolution.  Filtering
    # it here would make "data exists but the selected context did not match"
    # indistinguishable from a genuinely unreported safety dimension.
    selected_safety = tuple(safety_facts)
    if selected_efficacy:
        rows = build_matrix_comparison_rows(
            selected_efficacy,
            selected_safety,
            endpoint_family_id=selection.efficacy_endpoint_family_id,
            safety_family=selection.safety_family,
            safety_term_id=selection.safety_term_id,
            safety_event_definition_zh=selection.safety_event_definition_zh,
            safety_time_window_zh=selection.safety_time_window_zh,
            safety_analysis_population_zh=selection.safety_analysis_population_zh,
            treatment_sample_sizes=sample_sizes,
            target_id_by_product=target_mapping,
        )
    else:
        rows = ()
    return tuple(
        row
        for row in rows
        if (not selection.product_ids or row.product_id in selection.product_ids)
        and (not selection.trial_ids or row.trial_id in selection.trial_ids)
        and (not selection.target_ids or row.target_id in selection.target_ids)
    )


class MatrixViewState(BaseModel):
    """由一个选择状态确定性重建图、完整表、提示、证据和 URL。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    selection: MatrixSelectionState
    default_selection: MatrixSelectionState
    chart: BubbleMatrixView
    complete_table: tuple[MatrixCell, ...] = ()
    prompts: tuple[MatrixPrompt, ...] = ()
    evidence_links: tuple[MatrixEvidenceLink, ...] = ()
    url_state: dict[str, str] = {}
    url: str
    route: str = "/b/efficacy-safety-matrix"
    comparison_rows: tuple[MatrixComparisonRow, ...] = ()
    available_comparison_rows: tuple[MatrixComparisonRow, ...] = ()
    radius_scale: float = Field(gt=0)
    efficacy_facts: tuple[EfficacyFactRow, ...] = ()
    safety_facts: tuple[SafetyFactRow, ...] = ()
    target_id_by_product: tuple[tuple[str, str], ...] = ()
    sample_size_by_fact_row: tuple[tuple[str, int | None], ...] = ()

    @field_validator("url", "route")
    @classmethod
    def _state_url(cls, value: str) -> str:
        return _text(value, field_name="矩阵 URL")

    @model_validator(mode="after")
    def _state_integrity(self) -> Self:
        row_by_id = {row.comparison_row_id: row for row in self.comparison_rows}
        row_ids = tuple(row_by_id)
        if len(row_by_id) != len(self.comparison_rows):
            raise ValueError("矩阵视图比较行标识不得重复")
        chart_row_ids = tuple(row.comparison_row_id for row in self.chart.comparison_rows)
        if chart_row_ids != row_ids:
            raise ValueError("图表与完整表必须引用同一比较行集合")
        table_row_ids = tuple(cell.comparison_row_id for cell in self.complete_table)
        if table_row_ids != row_ids:
            raise ValueError("完整表必须覆盖全部图表比较行")
        prompt_row_ids = tuple(prompt.comparison_row_id for prompt in self.prompts)
        if prompt_row_ids != row_ids:
            raise ValueError("提示必须覆盖全部比较行")
        evidence_row_ids = tuple(
            dict.fromkeys(link.comparison_row_id for link in self.evidence_links)
        )
        if evidence_row_ids != row_ids:
            raise ValueError("证据链接必须覆盖全部比较行")
        for cell in self.complete_table:
            row = row_by_id[cell.comparison_row_id]
            if set(cell.fact_row_ids) != set(row.fact_row_ids):
                raise ValueError("完整表单元必须引用同一比较行事实")
        for prompt in self.prompts:
            row = row_by_id[prompt.comparison_row_id]
            if set(prompt.fact_row_ids) != set(row.fact_row_ids):
                raise ValueError("矩阵提示必须引用同一比较行事实")
        fact_ids = {fact_id for row in self.comparison_rows for fact_id in row.fact_row_ids}
        fact_id_sequence = tuple(
            fact_id for row in self.comparison_rows for fact_id in row.fact_row_ids
        )
        if len(set(fact_id_sequence)) != len(fact_id_sequence):
            raise ValueError("矩阵视图事实行不得跨比较行重复引用")
        evidence_by_row: dict[str, set[str]] = {}
        for link in self.evidence_links:
            evidence_by_row.setdefault(link.comparison_row_id, set()).add(link.fact_row_id)
        for row_id, row in row_by_id.items():
            if evidence_by_row.get(row_id, set()) != set(row.fact_row_ids):
                raise ValueError("矩阵证据必须引用同一比较行事实")
        if self.url_state != self.selection.to_url_params():
            raise ValueError("矩阵 URL 状态必须与选择状态一致")
        if self.url != self.selection.to_url(self.route):
            raise ValueError("矩阵 URL 必须与选择状态和路由一致")
        if self.selection.bubble_size != "treatment_sample_size":
            raise ValueError("当前矩阵仅支持按治疗组样本量缩放气泡")
        if not fact_ids and self.comparison_rows:
            raise ValueError("矩阵比较行必须引用事实行")
        return self

    @property
    def selection_state(self) -> MatrixSelectionState:
        return self.selection

    @property
    def matrix_selection(self) -> MatrixSelectionState:
        return self.selection

    @property
    def bubble_view(self) -> BubbleMatrixView:
        return self.chart

    @property
    def chart_view(self) -> BubbleMatrixView:
        return self.chart
    @property
    def chart_points(self) -> tuple[BubblePoint, ...]:
        return self.chart.points

    @property
    def rows(self) -> tuple[MatrixComparisonRow, ...]:
        return self.comparison_rows

    @property
    def selected_rows(self) -> tuple[MatrixComparisonRow, ...]:
        return self.comparison_rows

    @property
    def table(self) -> tuple[MatrixCell, ...]:
        return self.complete_table
    @property
    def full_table(self) -> tuple[MatrixCell, ...]:
        return self.complete_table

    @property
    def complete_table_rows(self) -> tuple[MatrixCell, ...]:
        return self.complete_table

    @property
    def matrix_cells(self) -> tuple[MatrixCell, ...]:
        return self.complete_table

    @property
    def notices(self) -> tuple[MatrixPrompt, ...]:
        return self.prompts
    @property
    def hints(self) -> tuple[MatrixPrompt, ...]:
        return self.prompts

    @property
    def tooltips(self) -> tuple[MatrixPrompt, ...]:
        return self.prompts

    @property
    def evidence(self) -> tuple[MatrixEvidenceLink, ...]:
        return self.evidence_links

    @property
    def evidence_references(self) -> tuple[MatrixEvidenceLink, ...]:
        return self.evidence_links
    @property
    def evidence_rows(self) -> tuple[MatrixEvidenceLink, ...]:
        return self.evidence_links

    @property
    def comparison_row_ids(self) -> tuple[str, ...]:
        return tuple(row.comparison_row_id for row in self.comparison_rows)

    @property
    def row_ids(self) -> tuple[str, ...]:
        return self.comparison_row_ids

    @property
    def fact_row_ids(self) -> tuple[str, ...]:
        return tuple(
            fact_id
            for row in self.comparison_rows
            for fact_id in row.fact_row_ids
        )

    @property
    def source_row_ids(self) -> tuple[str, ...]:
        return tuple(
            source_id
            for row in self.comparison_rows
            for source_id in row.source_row_ids
        )

    @property
    def url_params(self) -> dict[str, str]:
        return dict(self.url_state)
    @property
    def url_query(self) -> str:
        return self.selection.to_url_query()
    @property
    def selection_url(self) -> str:
        return self.url

    @property
    def url_state_params(self) -> dict[str, str]:
        return dict(self.url_state)

    @property
    def is_ranked(self) -> bool:
        return False

    @property
    def has_ranking(self) -> bool:
        return False

    def assert_synchronized(self) -> Self:
        return self

    def with_selection(
        self,
        selection: MatrixSelectionState | Mapping[str, Any],
    ) -> MatrixViewState:
        parsed = _selection_for_build(selection, default=self.default_selection)
        target_mapping = dict(self.target_id_by_product)
        if self.efficacy_facts:
            sample_mapping: dict[object, object] = {
                row_id: value for row_id, value in self.sample_size_by_fact_row
            }
            rows = _rows_for_selection(
                self.efficacy_facts,
                self.safety_facts,
                parsed,
                sample_sizes=sample_mapping or None,
                target_mapping=target_mapping,
                fallback_rows=self.available_comparison_rows,
            )
            return _assemble_matrix_view_state(
                rows,
                selection=parsed,
                default_selection=self.default_selection,
                radius_scale=self.radius_scale,
                efficacy_facts=self.efficacy_facts,
                safety_facts=self.safety_facts,
                target_mapping=target_mapping,
                sample_size_by_fact_row=self.sample_size_by_fact_row,
                available_comparison_rows=self.available_comparison_rows,
                route=self.route,
            )
        rows = _rows_for_selection(
            tuple(fact for row in self.comparison_rows for fact in row.efficacy_rows),
            tuple(fact for row in self.comparison_rows for fact in row.safety_rows),
            parsed,
            sample_sizes=None,
            target_mapping=target_mapping,
            fallback_rows=self.available_comparison_rows,
        )
        return _assemble_matrix_view_state(
            rows,
            selection=parsed,
            default_selection=self.default_selection,
            radius_scale=self.radius_scale,
            efficacy_facts=self.efficacy_facts,
            safety_facts=self.safety_facts,
            target_mapping=target_mapping,
            sample_size_by_fact_row=self.sample_size_by_fact_row,
            available_comparison_rows=self.available_comparison_rows,
            route=self.route,
        )

    update_selection = with_selection
    apply_selection = with_selection
    select = with_selection
    rebuild = with_selection

    def reset(self) -> MatrixViewState:
        return self.with_selection(self.default_selection)

    reset_selection = reset
    reset_view = reset


MatrixSynchronizedView = MatrixViewState
MatrixPageState = MatrixViewState
MatrixInteractionState = MatrixViewState


def _sample_size_by_fact_rows(
    efficacy_facts: Sequence[EfficacyFactRow],
    safety_facts: Sequence[SafetyFactRow],
    sample_mapping: Mapping[object, object] | None,
) -> tuple[tuple[str, int | None], ...]:
    if sample_mapping is None:
        return ()
    values: list[tuple[str, int | None]] = []
    for row in efficacy_facts:
        safety_treatment = next(
            (
                fact
                for fact in safety_facts
                if fact.product_id == row.product_id
                and fact.trial_id == row.trial_id
                and fact.arm_role is SafetyArmRole.TREATMENT
                and fact.arm_id == row.arm_id
            ),
            None,
        )
        value = _lookup_sample_size(
            sample_mapping,
            product_id=row.product_id,
            trial_id=row.trial_id,
            arm_id=row.arm_id,
            efficacy_treatment=row,
            safety_treatment=safety_treatment,
        )
        values.append((row.row_id, value))
    return tuple(values)


def _assemble_matrix_view_state(
    rows: Sequence[MatrixComparisonRow],
    *,
    selection: MatrixSelectionState,
    default_selection: MatrixSelectionState,
    radius_scale: float,
    efficacy_facts: Sequence[EfficacyFactRow] = (),
    safety_facts: Sequence[SafetyFactRow] = (),
    available_comparison_rows: Sequence[MatrixComparisonRow] = (),
    target_mapping: Mapping[str, str] | None = None,
    sample_size_by_fact_row: Sequence[tuple[str, int | None]] = (),
    route: str = "/b/efficacy-safety-matrix",
) -> MatrixViewState:
    ordered_rows = tuple(
        sorted(
            (validate_matrix_comparison_row(row) for row in rows),
            key=lambda row: (row.product_id, row.trial_id, row.comparison_row_id),
        )
    )
    chart = build_bubble_matrix(
        ordered_rows,
        radius_scale=radius_scale,
        safety_family=selection.safety_family,
    )
    point_by_row_id = {point.comparison_row_id: point for point in chart.points}
    cells = tuple(
        MatrixCell(
            comparison_row_id=row.comparison_row_id,
            comparison_row=row,
            product_id=row.product_id,
            trial_id=row.trial_id,
            target_id=row.target_id,
            status=row.status or MatrixComparisonStatus.PENDING_VERIFICATION,
            reason_zh=row.status_reason_zh or _status_reason(row) or "当前组合可绘制",
            point=point_by_row_id.get(row.comparison_row_id),
            fact_row_ids=row.fact_row_ids,
            source_row_ids=row.source_row_ids,
        )
        for row in ordered_rows
    )
    prompts = tuple(
        MatrixPrompt(
            comparison_row_id=row.comparison_row_id,
            status=row.status or MatrixComparisonStatus.PENDING_VERIFICATION,
            message_zh=_prompt_for_row(row),
            fact_row_ids=row.fact_row_ids,
            source_row_ids=row.source_row_ids,
        )
        for row in ordered_rows
    )
    links = tuple(
        _fact_evidence_link(row.comparison_row_id, fact)
        for row in ordered_rows
        for fact in row.efficacy_rows
    ) + tuple(
        _fact_evidence_link(row.comparison_row_id, fact)
        for row in ordered_rows
        for fact in row.safety_rows
    )
    state = MatrixViewState(
        selection=selection,
        default_selection=default_selection,
        chart=chart,
        complete_table=cells,
        prompts=prompts,
        evidence_links=links,
        url_state=selection.to_url_params(),
        url=selection.to_url(route),
        comparison_rows=ordered_rows,
        available_comparison_rows=tuple(available_comparison_rows),
        route=route,
        radius_scale=radius_scale,
        efficacy_facts=tuple(efficacy_facts),
        safety_facts=tuple(safety_facts),
        target_id_by_product=_target_mapping_tuple(target_mapping),
        sample_size_by_fact_row=tuple(sample_size_by_fact_row),
    )
    return state


def build_matrix_view_state(
    efficacy_facts: Sequence[EfficacyFactRow | Mapping[str, Any]] | None = None,
    safety_facts: Sequence[SafetyFactRow | Mapping[str, Any]] | None = None,
    *,
    comparison_rows: Sequence[MatrixComparisonRow | Mapping[str, Any]] | None = None,
    selection: MatrixSelectionState | Mapping[str, Any] | None = None,
    matrix_selection: MatrixSelectionState | Mapping[str, Any] | None = None,
    locked_snapshot_id: str | None = None,
    snapshot_id: str | None = None,
    treatment_sample_sizes: Mapping[object, object] | None = None,
    sample_size_by_arm: Mapping[object, object] | None = None,
    sample_sizes: Mapping[object, object] | None = None,
    treatment_group_sample_sizes: Mapping[object, object] | None = None,
    target_id_by_product: Mapping[str, str] | None = None,
    target_ids: Mapping[str, str] | None = None,
    target_by_product: Mapping[str, str] | None = None,
    radius_scale: float = 1.0,
    route: str = "/b/efficacy-safety-matrix",
) -> MatrixViewState:
    """构建图、完整表、提示、证据和 URL 的同源矩阵状态。"""
    positional_input: Any = efficacy_facts
    if comparison_rows is None and isinstance(positional_input, BubbleMatrixView):
        comparison_rows = positional_input.comparison_rows
        efficacy_facts = None
    elif comparison_rows is None and efficacy_facts is not None:
        positional_values = tuple(efficacy_facts)
        if positional_values and all(
            isinstance(cast(Any, item), MatrixComparisonRow)
            or (
                isinstance(cast(Any, item), Mapping)
                and any(
                    key in cast(Mapping[str, Any], item)
                    for key in (
                        "comparison_row_id",
                        "efficacy_treatment",
                        "efficacy_treatment_row",
                        "safety_treatment",
                        "safety_treatment_row",
                    )
                )
            )
            for item in positional_values
        ):
            comparison_rows = cast(
                Sequence[MatrixComparisonRow | Mapping[str, Any]],
                positional_values,
            )
            efficacy_facts = None


    if selection is not None and matrix_selection is not None:
        raise MatrixViewError("矩阵选择参数不得重复提供")
    supplied_selection = selection if selection is not None else matrix_selection
    if (
        snapshot_id is not None
        and locked_snapshot_id is not None
        and snapshot_id != locked_snapshot_id
    ):
        raise MatrixViewError("锁定快照参数不得互相冲突")
    effective_snapshot_id = snapshot_id or locked_snapshot_id
    sample_mapping = _select_sample_mapping(
        treatment_sample_sizes,
        sample_size_by_arm,
        sample_sizes,
        treatment_group_sample_sizes,
    )
    target_mapping = _select_target_mapping(target_id_by_product, target_ids, target_by_product)

    if comparison_rows is not None:
        if efficacy_facts is not None or safety_facts is not None:
            raise MatrixViewError("比较行与原始事实参数不得重复提供")
        original_rows = tuple(validate_matrix_comparison_row(row) for row in comparison_rows)
        if not original_rows:
            raise MatrixViewError("矩阵比较行不能为空")
        efficacy = tuple(fact for row in original_rows for fact in row.efficacy_rows)
        safety = tuple(fact for row in original_rows for fact in row.safety_rows)
        if sample_mapping is None:
            sample_mapping = {
                row.efficacy_treatment.row_id: row.treatment_sample_size
                for row in original_rows
                if row.efficacy_treatment is not None
            }
        if not target_mapping:
            target_mapping = {
                row.product_id: row.target_id
                for row in original_rows
                if row.target_id is not None
            }
        default_selection = MatrixSelectionState.from_facts(
            comparison_rows=original_rows,
            snapshot_id=effective_snapshot_id,
            target_id_by_product=target_mapping,
        )
    else:
        if efficacy_facts is None:
            raise MatrixViewError("必须提供疗效事实或比较行")
        efficacy = tuple(_validated_efficacy(row) for row in efficacy_facts)
        safety = tuple(_validated_safety(row) for row in (safety_facts or ()))
        default_selection = MatrixSelectionState.from_facts(
            efficacy,
            safety,
            snapshot_id=effective_snapshot_id,
            target_id_by_product=target_mapping,
        )
        original_rows = ()

    current_selection = _selection_for_build(supplied_selection, default=default_selection)
    if current_selection.bubble_size != "treatment_sample_size":
        raise MatrixViewError("当前矩阵仅支持按治疗组样本量缩放气泡")
    known_sample_sizes = _sample_size_by_fact_rows(efficacy, safety, sample_mapping)
    rebuilt_sample_mapping = {row_id: value for row_id, value in known_sample_sizes}
    rows = _rows_for_selection(
        efficacy,
        safety,
        current_selection,
        sample_sizes=cast(
            Mapping[object, object] | None,
            rebuilt_sample_mapping or sample_mapping,
        ),
        target_mapping=target_mapping,
        fallback_rows=original_rows,
    )
    return _assemble_matrix_view_state(
        rows,
        selection=current_selection,
        default_selection=default_selection,
        radius_scale=radius_scale,
        efficacy_facts=efficacy,
        safety_facts=safety,
        target_mapping=target_mapping,
        sample_size_by_fact_row=known_sample_sizes,
        available_comparison_rows=original_rows,
        route=route,
    )


build_matrix_state = build_matrix_view_state
build_synchronized_matrix_view = build_matrix_view_state
build_matrix_page_state = build_matrix_view_state
build_matrix_interaction_state = build_matrix_view_state


def apply_matrix_selection(
    value: MatrixViewState,
    selection: MatrixSelectionState | Mapping[str, Any],
) -> MatrixViewState:
    if not isinstance(value, MatrixViewState):
        raise MatrixViewError("应用矩阵选择必须传入 MatrixViewState")
    return value.with_selection(selection)


update_matrix_selection = apply_matrix_selection
select_matrix_view = apply_matrix_selection
update_matrix_view = apply_matrix_selection


def reset_matrix_selection(value: MatrixViewState) -> MatrixViewState:
    if not isinstance(value, MatrixViewState):
        raise MatrixViewError("重置矩阵选择必须传入 MatrixViewState")
    return value.reset()


reset_matrix_view = reset_matrix_selection
reset_matrix_state = reset_matrix_selection
reset_matrix_view_state = reset_matrix_selection


def selection_to_url(
    value: MatrixSelectionState | Mapping[str, Any],
    route: str = "/b/efficacy-safety-matrix",
) -> str:
    state = (
        value
        if isinstance(value, MatrixSelectionState)
        else MatrixSelectionState.model_validate(value)
    )
    return state.to_url(route)


def selection_from_url(url: str) -> MatrixSelectionState:
    return MatrixSelectionState.from_url(url)


parse_matrix_url_state = selection_from_url


__all__ += [
    "BubbleMatrixSelectionState",
    "MatrixCell",
    "MatrixComparisonCell",
    "MatrixEvidence",
    "MatrixEvidenceLink",
    "MatrixEvidenceReference",
    "MatrixInteractionState",
    "MatrixNotice",
    "MatrixPageState",
    "MatrixPrompt",
    "MatrixSelection",
    "MatrixSelectionState",
    "MatrixSynchronizedView",
    "MatrixTableRow",
    "MatrixTooltip",
    "MatrixViewState",
    "apply_matrix_selection",
    "build_matrix_interaction_state",
    "build_matrix_page_state",
    "build_matrix_state",
    "build_matrix_view",
    "build_matrix_view_state",
    "build_synchronized_matrix_view",
    "parse_matrix_url_state",
    "reset_matrix_selection",
    "reset_matrix_state",
    "reset_matrix_view",
    "reset_matrix_view_state",
    "select_matrix_view",
    "selection_from_url",
    "selection_to_url",
    "update_matrix_selection",
    "update_matrix_view",
]
