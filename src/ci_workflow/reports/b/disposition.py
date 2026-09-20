"""B 类试验完成情况与受试者处置事实合同。

本模块只保存来源闭合的 ``trial_disposition_observation`` 事实。它不参与
GateSpec、证据门槛或渲染决策；缺失处置数值继续沿用共享
``FactDisclosureState``，并在公共边界上保持非阻断、非数值语义。
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictBool,
    StrictFloat,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole

NumericValue = StrictInt | StrictFloat
RawValue = str | StrictInt | StrictFloat


class TrialDispositionObservationError(ValueError):
    """试验完成情况事实不满足强类型或公共边界合同。"""


class DispositionFieldFamily(StrEnum):
    """试验完成情况事实的封闭字段族。"""

    PARTICIPANT_FLOW = "participant_flow"
    REASON = "reason"
    ADHERENCE = "adherence"
    RESCUE_TREATMENT = "rescue_treatment"
    PROHIBITED_MEDICATION = "prohibited_medication"
    PROTOCOL_DEVIATION = "protocol_deviation"


class DispositionField(StrEnum):
    """试验完成情况事实的规范字段；``source_other`` 保留来源新增字段。"""

    SCREENED = "screened"
    SCREEN_FAILURE = "screen_failure"
    RANDOMIZED = "randomized"
    RECEIVED_TREATMENT = "received_treatment"
    COMPLETED_TREATMENT = "completed_treatment"
    COMPLETED_STUDY = "completed_study"
    TREATMENT_DISCONTINUED = "treatment_discontinued"
    STUDY_WITHDRAWAL = "study_withdrawal"
    LOST_TO_FOLLOW_UP = "lost_to_follow_up"
    SCREEN_FAILURE_REASON = "screen_failure_reason"
    TREATMENT_DISCONTINUATION_REASON = "treatment_discontinuation_reason"
    STUDY_WITHDRAWAL_REASON = "study_withdrawal_reason"
    ADHERENCE = "adherence"
    RESCUE_TREATMENT = "rescue_treatment"
    PROHIBITED_MEDICATION = "prohibited_medication"
    PROTOCOL_DEVIATION = "protocol_deviation"
    MAJOR_PROTOCOL_DEVIATION = "major_protocol_deviation"
    PROTOCOL_DEVIATION_LEADING_TO_EXCLUSION = "protocol_deviation_leading_to_exclusion"
    SOURCE_OTHER = "source_other"


class DispositionScopeLevel(StrEnum):
    """事实作用域：总体、队列或治疗组别。"""

    OVERALL = "overall"
    COHORT = "cohort"
    GROUP = "group"


class DispositionMeasureObject(StrEnum):
    """数值代表受试者还是事件。"""

    SUBJECT = "subject"
    EVENT = "event"


class DispositionStatisticForm(StrEnum):
    """来源统计形式；不同形式不互相推导。"""

    COUNT = "count"
    EVENT_COUNT = "event_count"
    PROPORTION = "proportion"
    ADHERENCE_SUMMARY = "adherence_summary"
    OTHER = "other"


class DispositionDenominatorRole(StrEnum):
    """分母所代表的科学人群或期间。"""

    SCREENED = "screened"
    RANDOMIZED = "randomized"
    TREATED = "treated"
    SAFETY = "safety"
    ANALYSIS = "analysis"
    PERIOD_START = "period_start"
    OTHER = "other"


_MISSING_DISCLOSURE_STATES = frozenset(
    {
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.NOT_APPLICABLE,
        FactDisclosureState.CONFLICTING,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    }
)
_REPORTED_DISCLOSURE_STATES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)
_REASON_FIELDS = frozenset(
    {
        DispositionField.SCREEN_FAILURE_REASON,
        DispositionField.TREATMENT_DISCONTINUATION_REASON,
        DispositionField.STUDY_WITHDRAWAL_REASON,
    }
)
_SCREENING_FIELDS = frozenset(
    {
        DispositionField.SCREENED,
        DispositionField.SCREEN_FAILURE,
        DispositionField.SCREEN_FAILURE_REASON,
    }
)
_PROTOCOL_DEVIATION_FIELDS = frozenset(
    {
        DispositionField.PROTOCOL_DEVIATION,
        DispositionField.MAJOR_PROTOCOL_DEVIATION,
        DispositionField.PROTOCOL_DEVIATION_LEADING_TO_EXCLUSION,
    }
)
_FIELD_FAMILY_FIELDS: dict[DispositionFieldFamily, frozenset[DispositionField]] = {
    DispositionFieldFamily.PARTICIPANT_FLOW: frozenset(
        {
            DispositionField.SCREENED,
            DispositionField.SCREEN_FAILURE,
            DispositionField.RANDOMIZED,
            DispositionField.RECEIVED_TREATMENT,
            DispositionField.COMPLETED_TREATMENT,
            DispositionField.COMPLETED_STUDY,
            DispositionField.TREATMENT_DISCONTINUED,
            DispositionField.STUDY_WITHDRAWAL,
            DispositionField.LOST_TO_FOLLOW_UP,
        }
    ),
    DispositionFieldFamily.REASON: _REASON_FIELDS,
    DispositionFieldFamily.ADHERENCE: frozenset({DispositionField.ADHERENCE}),
    DispositionFieldFamily.RESCUE_TREATMENT: frozenset({DispositionField.RESCUE_TREATMENT}),
    DispositionFieldFamily.PROHIBITED_MEDICATION: frozenset(
        {DispositionField.PROHIBITED_MEDICATION}
    ),
    DispositionFieldFamily.PROTOCOL_DEVIATION: _PROTOCOL_DEVIATION_FIELDS,
}
_DISCLOSURE_LABELS_ZH: dict[FactDisclosureState, str] = {
    FactDisclosureState.REPORTED_VALUE: "已报告数值",
    FactDisclosureState.REPORTED_ZERO: "已报告为零",
    FactDisclosureState.NOT_REPORTED: "原文未报告",
    FactDisclosureState.BELOW_REPORTING_THRESHOLD: "低于来源列示阈值",
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED: "未公开",
    FactDisclosureState.NOT_APPLICABLE: "不适用",
    FactDisclosureState.CONFLICTING: "来源存在冲突",
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE: "技术路径未解决",
}
_THRESHOLD_EVIDENCE = re.compile(
    r"(?:^\s*[<≤]|低于|少于|小于|未达到|低于或等于)", re.IGNORECASE
)
_NUMERIC_DISCLOSURE = re.compile(
    r"^\s*[<>≤≥~≈]?\s*[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
    r"\s*(?:[%％]|[A-Za-z\u3400-\u9fff][^\n]*)?\s*$"
)
_ZERO_EVIDENCE = re.compile(
    r"(?<![0-9.])0(?:\.0+)?(?=\s*(?:[%％/]|[A-Za-z\u3400-\u9fff]+|\)|$))"
)
_PERCENT_UNITS = frozenset({"%", "％", "percent", "percentage", "百分比", "百分率"})
_FRACTION_UNITS = frozenset({"ratio", "fraction", "proportion", "rate", "比例", "比率", "率"})


def _text(value: str, *, field_name: str = "处置合同文本") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name}必须是文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _raw_text(value: str, *, field_name: str = "处置来源原文") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}不能为空")
    return value


def _optional_text(value: str | None, *, field_name: str = "处置合同文本") -> str | None:
    return None if value is None else _text(value, field_name=field_name)


def _as_token(value: object | None) -> str:
    if value is None:
        return "<none>"
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("处置事实身份数值必须是有限数值")
        return repr(value)
    return str(value)


def _finite_numeric(value: NumericValue | None, *, field_name: str) -> NumericValue | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}必须是数值")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name}必须是有限数值")
    return value


def _unit_scale(unit: str | None) -> int:
    """Return the explicit proportion scale: 100 for percent, 1 for fraction."""

    if unit is None:
        raise ValueError("比例必须明确使用百分比或0至1比例单位")
    token = unit.strip().casefold()
    if "%" in token or "％" in token or "百分" in token or token in _PERCENT_UNITS:
        return 100
    if token in _FRACTION_UNITS:
        return 1
    raise ValueError("比例单位必须明确为百分比或0至1比例")


def _recognized_unit_scale(unit: str | None) -> int | None:
    """Return a proportion scale only when the unit explicitly denotes one."""

    if unit is None:
        return None
    token = unit.strip().casefold()
    if "%" in token or "％" in token or "百分" in token or token in _PERCENT_UNITS:
        return 100
    if token in _FRACTION_UNITS:
        return 1
    return None


def _numeric_fields(observation: TrialDispositionObservation) -> tuple[object | None, ...]:
    return observation.value, observation.numerator, observation.denominator


def disclosure_state_label_zh(state: FactDisclosureState | str) -> str:
    """Return a conservative Chinese disclosure label without numeric coercion."""

    try:
        resolved = state if isinstance(state, FactDisclosureState) else FactDisclosureState(state)
    except ValueError as error:
        raise ValueError(f"未知处置披露状态：{state!r}") from error
    return _DISCLOSURE_LABELS_ZH[resolved]


class TrialDispositionObservation(BaseModel):
    """一条产品—试验—期间—队列/组别闭合的处置事实观察。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["1.0"] = "1.0"
    row_id: str
    source_row_id: str
    observation_id: str
    product_id: str
    trial_id: str
    period_id: str
    cohort_id: str | None
    scope_level: DispositionScopeLevel
    group_id: str | None
    analysis_population: str
    field_family: DispositionFieldFamily
    field: DispositionField
    source_field_name: str
    source_field_definition: str
    measure_object: DispositionMeasureObject
    statistic_form: DispositionStatisticForm
    value: NumericValue | None = None
    raw_value: RawValue | None = None
    unit: str | None = None
    numerator: StrictInt | None = None
    denominator: StrictInt | None = None
    denominator_role: DispositionDenominatorRole
    time_window: str
    reason_original_text: str | None = None
    canonical_reason: str | None = None
    reason_is_mutually_exclusive: StrictBool | None = None
    reason_is_exhaustive: StrictBool | None = None
    adherence_definition: str | None = None
    adherence_threshold: str | None = None
    protocol_deviation_level: str | None = None
    source_version_id: str
    source_locator: EvidenceLocator
    source_role: SourceRole
    disclosure_maturity: DisclosureMaturity
    review_state: FactReviewState
    disclosure_state: FactDisclosureState
    conflict_disposition: ConflictDisposition
    reported_zero_text: str | None = None
    route_receipt_id: str | None = None
    applicability_predicate_id: str | None = None
    compatibility_rule: str
    difference_labels_zh: tuple[str, ...] = ()

    @field_validator(
        "row_id",
        "source_row_id",
        "observation_id",
        "product_id",
        "trial_id",
        "period_id",
        "analysis_population",
        "source_version_id",
        "compatibility_rule",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "cohort_id",
        "group_id",
        "unit",
        "route_receipt_id",
        "applicability_predicate_id",
    )
    @classmethod
    def _optional_text_fields(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @field_validator("time_window")
    @classmethod
    def _time_window_text(cls, value: str) -> str:
        return _text(value, field_name="处置时间窗")

    @field_validator("source_field_name", "source_field_definition")
    @classmethod
    def _source_fields_preserve_raw_text(cls, value: str) -> str:
        return _raw_text(value, field_name="处置来源字段名/定义")

    @field_validator("reason_original_text")
    @classmethod
    def _reason_original_text(cls, value: str | None) -> str | None:
        return None if value is None else _raw_text(value, field_name="原因来源原文")

    @field_validator("canonical_reason")
    @classmethod
    def _canonical_reason_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="规范原因")

    @field_validator("adherence_definition", "adherence_threshold", "protocol_deviation_level")
    @classmethod
    def _implementation_text(cls, value: str | None) -> str | None:
        return None if value is None else _raw_text(value, field_name="试验实施定义")

    @field_validator("raw_value")
    @classmethod
    def _raw_value_shape(cls, value: RawValue | None) -> RawValue | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("处置来源原始值不得为布尔值")
        if isinstance(value, str):
            return _raw_text(value, field_name="处置来源原始表达")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("处置来源原始值必须是有限数值")
        return value

    @field_validator("reported_zero_text")
    @classmethod
    def _reported_zero_text(cls, value: str | None) -> str | None:
        return None if value is None else _raw_text(value, field_name="处置零值原文")

    @field_validator("difference_labels_zh", mode="before")
    @classmethod
    def _difference_labels(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = (value,) if isinstance(value, str) else tuple(value)
        normalized = tuple(_text(item, field_name="处置差异标签") for item in values)
        if len(normalized) != len(set(normalized)):
            raise ValueError("处置差异标签不得重复")
        return normalized

    @field_validator("value", "numerator", "denominator", mode="before")
    @classmethod
    def _reject_boolean_numbers(cls, value: Any, info: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError(f"处置字段 {info.field_name} 不得为布尔值")
        return value

    @field_validator("numerator", "denominator")
    @classmethod
    def _count_bounds(cls, value: StrictInt | None, info: Any) -> StrictInt | None:
        if value is None:
            return None
        if info.field_name == "numerator" and value < 0:
            raise ValueError("处置分子不得为负数")
        if info.field_name == "denominator" and value <= 0:
            raise ValueError("处置分母必须为正数")
        return value

    @field_validator("value")
    @classmethod
    def _value_is_finite(cls, value: NumericValue | None) -> NumericValue | None:
        return _finite_numeric(value, field_name="处置事实数值")

    @model_validator(mode="after")
    def _observation_contract_is_closed(self) -> Self:
        self._validate_scope_contract()
        self._validate_field_contract()
        self._validate_disclosure_contract()
        self._validate_measurement_contract()
        expected_row_id = self._derived_row_id()
        labels = self._derived_difference_labels()
        updates: dict[str, object] = {}
        if self.row_id != expected_row_id:
            updates["row_id"] = expected_row_id
        if labels != self.difference_labels_zh:
            updates["difference_labels_zh"] = labels
        if updates:
            return self.model_copy(update=updates)
        return self

    def _validate_scope_contract(self) -> None:
        if self.scope_level is DispositionScopeLevel.GROUP:
            if self.group_id is None:
                raise ValueError("组别层级必须提供 group_id")
            if self.cohort_id is None:
                raise ValueError("组别层级必须提供 cohort_id")
        elif self.scope_level is DispositionScopeLevel.COHORT:
            if self.cohort_id is None:
                raise ValueError("队列层级必须提供 cohort_id")
            if self.group_id is not None:
                raise ValueError("队列层级不得携带 group_id")
        elif self.scope_level is DispositionScopeLevel.OVERALL:
            if self.cohort_id is not None or self.group_id is not None:
                raise ValueError("总体层级不得携带 cohort_id 或 group_id")

        if self.field in _SCREENING_FIELDS:
            if self.scope_level is DispositionScopeLevel.GROUP or self.group_id is not None:
                raise ValueError("筛选/筛败字段只能使用总体或队列语境，不能归入组别")
            if self.denominator_role is not DispositionDenominatorRole.SCREENED:
                raise ValueError("筛败/筛选字段必须使用筛选总体分母")

        if self.field_family in {
            DispositionFieldFamily.PARTICIPANT_FLOW,
            DispositionFieldFamily.REASON,
        }:
            if self.measure_object is not DispositionMeasureObject.SUBJECT:
                raise ValueError("受试者流转及退出原因必须使用受试者计量对象")
            if self.statistic_form is DispositionStatisticForm.EVENT_COUNT:
                raise ValueError("受试者流转及退出原因不得使用事件数统计")

    def _validate_field_contract(self) -> None:
        if self.field is not DispositionField.SOURCE_OTHER:
            expected_family = next(
                family
                for family, fields in _FIELD_FAMILY_FIELDS.items()
                if self.field in fields
            )
            if self.field_family is not expected_family:
                raise ValueError("规范处置字段与字段族不匹配")

        is_reason = self.field in _REASON_FIELDS
        reason_values = (self.reason_original_text, self.canonical_reason)
        if is_reason:
            has_reason_metadata = any(value is not None for value in reason_values)
            if self.disclosure_state in _REPORTED_DISCLOSURE_STATES and any(
                value is None for value in reason_values
            ):
                raise ValueError("原因字段必须保留原因原文和规范原因")
            if has_reason_metadata and any(value is None for value in reason_values):
                raise ValueError("原因原文和规范原因必须同时提供")
        elif any(value is not None for value in reason_values) or any(
            value is not None
            for value in (self.reason_is_mutually_exclusive, self.reason_is_exhaustive)
        ):
            raise ValueError("非原因字段不得携带原因语义字段")

        if self.field_family is DispositionFieldFamily.ADHERENCE:
            adherence_values = (self.adherence_definition, self.adherence_threshold)
            if self.disclosure_state in _REPORTED_DISCLOSURE_STATES and any(
                value is None for value in adherence_values
            ):
                raise ValueError("依从性必须保留定义和来源阈值")
            if any(value is not None for value in adherence_values) and any(
                value is None for value in adherence_values
            ):
                raise ValueError("依从性定义和来源阈值必须同时提供")
        elif self.adherence_definition is not None or self.adherence_threshold is not None:
            raise ValueError("非依从性字段不得携带依从性定义或阈值")

        is_pd = self.field in _PROTOCOL_DEVIATION_FIELDS
        if (
            is_pd
            and self.disclosure_state in _REPORTED_DISCLOSURE_STATES
            and self.protocol_deviation_level is None
        ):
            raise ValueError("方案偏离字段必须声明 PD 层级")
        if not is_pd and self.protocol_deviation_level is not None:
            raise ValueError("非方案偏离字段不得携带 PD 层级")
        if (
            self.field is DispositionField.MAJOR_PROTOCOL_DEVIATION
            and self.protocol_deviation_level is not None
            and self.protocol_deviation_level.strip().casefold().replace("-", "_") != "major"
        ):
            raise ValueError("重大方案偏离字段必须使用 major 层级")
        if (
            self.field is DispositionField.PROTOCOL_DEVIATION_LEADING_TO_EXCLUSION
            and self.protocol_deviation_level is not None
        ):
            normalized = self.protocol_deviation_level.strip().casefold().replace("-", "_")
            if normalized not in {"leading_to_exclusion", "exclusion"}:
                raise ValueError("导致排除的方案偏离字段必须使用 leading_to_exclusion 层级")

    def _validate_disclosure_contract(self) -> None:
        numeric_values = _numeric_fields(self)
        state = self.disclosure_state
        if state in _MISSING_DISCLOSURE_STATES and any(
            value is not None for value in numeric_values
        ):
            raise ValueError(
                "未报告、未公开、不适用、冲突或路线未解决状态不得携带数值或分母"
            )
        if state is FactDisclosureState.NOT_APPLICABLE:
            if self.applicability_predicate_id is None:
                raise ValueError("不适用处置事实必须链接适用性依据")
        elif self.applicability_predicate_id is not None:
            raise ValueError("非不适用处置事实不得携带适用性依据")

        if state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE:
            if self.route_receipt_id is None:
                raise ValueError("路线未解决处置事实必须链接路由回执")
        elif self.route_receipt_id is not None:
            raise ValueError("非路线未解决处置事实不得携带路由回执")

        if state is FactDisclosureState.CONFLICTING:
            if self.conflict_disposition is not ConflictDisposition.OPEN_CONFLICT_PRESERVED:
                raise ValueError("冲突处置事实必须保留开放冲突处置")
        elif self.conflict_disposition is not ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT:
            raise ValueError("非冲突处置事实必须选择已接受事实")

        if state in {FactDisclosureState.NOT_REPORTED, FactDisclosureState.NOT_PUBLICLY_DISCLOSED}:
            if isinstance(self.raw_value, (int, float)) and not isinstance(self.raw_value, bool):
                raise ValueError("未报告或未公开状态不得携带数值型原始表达")
            if isinstance(self.raw_value, str) and (
                _NUMERIC_DISCLOSURE.fullmatch(self.raw_value)
                or re.search(r"\d", self.raw_value) is not None
            ):
                raise ValueError("未报告或未公开状态不得携带数值型原始表达")
        elif state is FactDisclosureState.BELOW_REPORTING_THRESHOLD:
            if (
                self.raw_value is None
                or not isinstance(self.raw_value, str)
                or _THRESHOLD_EVIDENCE.search(self.raw_value) is None
            ):
                raise ValueError("低于报告阈值状态必须保存来源阈值原文")

        if state is FactDisclosureState.REPORTED_VALUE:
            if self.value is None:
                raise ValueError("已报告处置事实必须保留明确数值")
            if self.value == 0:
                raise ValueError("确定零值必须使用 reported_zero 状态")
            if self.raw_value is None:
                raise ValueError("已报告处置事实必须保留来源原文值")
        elif state is FactDisclosureState.REPORTED_ZERO:
            if self.value != 0:
                raise ValueError("已报告零值的规范数值必须为零")
            if self.raw_value is None:
                raise ValueError("已报告零值必须保留来源原文值")
            has_zero_evidence = (
                isinstance(self.raw_value, (int, float))
                and not isinstance(self.raw_value, bool)
                and self.raw_value == 0
            ) or (
                isinstance(self.raw_value, str)
                and _ZERO_EVIDENCE.search(self.raw_value) is not None
            )
            if not has_zero_evidence:
                raise ValueError("已报告零值必须保留明确零值原文证据")
            if self.reported_zero_text is None:
                raise ValueError("已报告零值必须有明确零值原文证据")
            if _ZERO_EVIDENCE.search(self.reported_zero_text) is None:
                raise ValueError("已报告零值原文必须包含明确零值证据")
        elif self.reported_zero_text is not None:
            raise ValueError("非零值或缺失处置事实不得携带零值原文")

        if self.numerator is not None and self.denominator is None:
            raise ValueError("处置分子存在时必须同时保留分母")
        if (
            self.denominator is not None
            and self.numerator is not None
            and self.numerator > self.denominator
            and (
                self.measure_object is DispositionMeasureObject.SUBJECT
                or self.statistic_form is DispositionStatisticForm.PROPORTION
            )
        ):
            message = (
                "比例分子不得大于分母"
                if self.statistic_form is DispositionStatisticForm.PROPORTION
                else "处置分子不得大于分母"
            )
            raise ValueError(message)
        if state in _MISSING_DISCLOSURE_STATES and self.reported_zero_text is not None:
            raise ValueError("非具体披露状态不得携带零值原文")

    def _validate_measurement_contract(self) -> None:
        reported = self.disclosure_state in _REPORTED_DISCLOSURE_STATES
        if self.statistic_form is DispositionStatisticForm.COUNT:
            if self.measure_object is not DispositionMeasureObject.SUBJECT:
                raise ValueError("人数统计必须使用受试者计量对象")
            if reported and (self.value is None or not isinstance(self.value, int)):
                raise ValueError("人数必须是非负整数")
            if (
                reported
                and self.value is not None
                and self.denominator is not None
                and self.value > self.denominator
            ):
                raise ValueError("受试者人数不得大于分母")
        elif self.statistic_form is DispositionStatisticForm.EVENT_COUNT:
            if self.measure_object is not DispositionMeasureObject.EVENT:
                raise ValueError("事件数统计必须使用事件计量对象")
            if reported and (self.value is None or not isinstance(self.value, int)):
                raise ValueError("事件数必须是非负整数")
        elif self.statistic_form is DispositionStatisticForm.PROPORTION:
            if reported:
                if self.value is None:
                    raise ValueError("比例统计必须保留来源报告比例")
                scale = _unit_scale(self.unit)
                if self.value < 0 or self.value > scale:
                    raise ValueError("比例必须在明确单位允许的范围内")
                if (self.numerator is None) != (self.denominator is None):
                    raise ValueError("比例复算必须同时提供分子和分母")
        elif self.statistic_form is DispositionStatisticForm.ADHERENCE_SUMMARY:
            if self.measure_object is not DispositionMeasureObject.SUBJECT:
                raise ValueError("依从性汇总必须使用受试者计量对象")
            if reported and self.value is not None and self.value < 0:
                raise ValueError("依从性汇总不得为负数")
            adherence_scale = _recognized_unit_scale(self.unit)
            if (
                reported
                and adherence_scale is not None
                and self.value is not None
                and self.value > adherence_scale
            ):
                raise ValueError("依从性比例必须位于明确单位允许的范围内")
        elif self.statistic_form is DispositionStatisticForm.OTHER:
            if reported and self.value is not None and self.value < 0:
                raise ValueError("其他处置数值不得为负数")

        if reported and self.value is not None and self.value < 0:
            raise ValueError("处置数值不得为负数")
        if (
            self.measure_object is DispositionMeasureObject.EVENT
            and self.statistic_form is DispositionStatisticForm.COUNT
        ):
            raise ValueError("事件计量对象不得映射为受试者人数")

        if (
            self.field in _PROTOCOL_DEVIATION_FIELDS
            and self.measure_object is DispositionMeasureObject.EVENT
            and self.statistic_form
            not in {
                DispositionStatisticForm.EVENT_COUNT,
                DispositionStatisticForm.PROPORTION,
                DispositionStatisticForm.OTHER,
            }
        ):
            raise ValueError("事件型方案偏离必须使用事件数或事件比例统计")

    def _derived_difference_labels(self) -> tuple[str, ...]:
        if (
            self.statistic_form is not DispositionStatisticForm.PROPORTION
            or self.value is None
            or self.numerator is None
            or self.denominator is None
            or self.disclosure_state not in _REPORTED_DISCLOSURE_STATES
        ):
            return self.difference_labels_zh
        expected = self.numerator / self.denominator
        if _unit_scale(self.unit) == 100:
            expected *= 100
        if math.isclose(float(self.value), expected, rel_tol=0.0, abs_tol=1e-9):
            return self.difference_labels_zh
        label = "来源比例与分子/分母复算值不一致，保留来源值"
        if label in self.difference_labels_zh:
            return self.difference_labels_zh
        return (*self.difference_labels_zh, label)

    def _identity_parts(self) -> tuple[str, ...]:
        return (
            self.product_id,
            self.trial_id,
            self.period_id,
            _as_token(self.cohort_id),
            self.scope_level.value,
            _as_token(self.group_id),
            self.analysis_population,
            self.field_family.value,
            self.field.value,
            self.measure_object.value,
            self.statistic_form.value,
            _as_token(self.unit),
            self.denominator_role.value,
            self.time_window,
            _as_token(self.canonical_reason),
            _as_token(self.reason_is_mutually_exclusive),
            _as_token(self.reason_is_exhaustive),
            _as_token(self.adherence_definition),
            _as_token(self.adherence_threshold),
            _as_token(self.protocol_deviation_level),
            self.compatibility_rule,
        )

    def _derived_row_id(self) -> str:
        return stable_id("trial-disposition-row", *self._identity_parts())

    @property
    def identity_key(self) -> str:
        """稳定科学行身份；不含事实值、来源版本或审阅元数据。"""

        return self._derived_row_id()

    @property
    def fact_version_id(self) -> str:
        """供下游证据引用的不可变事实版本标识。"""

        return self.row_id

    @property
    def recomputed_proportion(self) -> float | None:
        """只读复算比例；没有明确分子和正分母时返回 ``None``。"""

        if (
            self.statistic_form is not DispositionStatisticForm.PROPORTION
            or self.disclosure_state not in _REPORTED_DISCLOSURE_STATES
            or self.numerator is None
            or self.denominator is None
        ):
            return None
        result = self.numerator / self.denominator
        if _unit_scale(self.unit) == 100:
            result *= 100
        return result

    @property
    def reported_proportion(self) -> NumericValue | None:
        return (
            self.value
            if self.statistic_form is DispositionStatisticForm.PROPORTION
            and self.disclosure_state in _REPORTED_DISCLOSURE_STATES
            else None
        )

    @property
    def has_numeric_value(self) -> bool:
        return self.disclosure_state in _REPORTED_DISCLOSURE_STATES and self.value is not None

    @property
    def is_non_numeric_state(self) -> bool:
        return not self.has_numeric_value

    @property
    def display_value_zh(self) -> str:
        if self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            return f"0{self.unit or ''}"
        if self.disclosure_state is FactDisclosureState.REPORTED_VALUE:
            if self.value is None:  # pragma: no cover - closed by validator
                raise TrialDispositionObservationError("已报告处置事实缺少数值")
            formatted = f"{self.value:g}" if isinstance(self.value, float) else str(self.value)
            return f"{formatted}{self.unit or ''}"
        if self.disclosure_state is FactDisclosureState.BELOW_REPORTING_THRESHOLD and isinstance(
            self.raw_value, str
        ):
            return self.raw_value
        return disclosure_state_label_zh(self.disclosure_state)

    @property
    def difference_labels(self) -> tuple[str, ...]:
        return self.difference_labels_zh


def validate_trial_disposition_observation(
    observation: TrialDispositionObservation | Mapping[str, Any],
) -> TrialDispositionObservation:
    """在公共边界重新校验事实，拒绝 ``model_copy(update=...)`` 绕过状态。"""

    payload: object
    if isinstance(observation, TrialDispositionObservation):
        unknown_fields = set(observation.__dict__) - set(type(observation).model_fields)
        if unknown_fields:
            raise TrialDispositionObservationError(
                f"处置观察重新校验失败：包含未知字段 {tuple(sorted(unknown_fields))}"
            )
        extras = observation.__pydantic_extra__
        if extras:
            raise TrialDispositionObservationError(
                f"处置观察重新校验失败：包含未知字段 {tuple(sorted(extras))}"
            )
        payload = observation.model_dump(mode="python", warnings=False)
    elif isinstance(observation, Mapping):
        payload = dict(observation)
    else:
        raise TypeError("处置观察必须是 TrialDispositionObservation 或映射")
    try:
        return TrialDispositionObservation.model_validate(payload)
    except ValidationError as error:
        raise TrialDispositionObservationError(f"处置观察重新校验失败：{error}") from error


__all__ = [
    "DispositionDenominatorRole",
    "DispositionField",
    "DispositionFieldFamily",
    "DispositionMeasureObject",
    "DispositionScopeLevel",
    "DispositionStatisticForm",
    "RawValue",
    "TrialDispositionObservation",
    "TrialDispositionObservationError",
    "disclosure_state_label_zh",
    "validate_trial_disposition_observation",
]
