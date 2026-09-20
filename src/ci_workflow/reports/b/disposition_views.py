"""B 类试验完成情况与受试者处置的同源视图模型。

本模块只把已经通过 :mod:`disposition` 事实合同的观察投影为不可变的
图表、完整表格、披露状态矩阵和证据链接。所有公共交互都从同一份原始
事实重新装配，避免图表、表格、证据和网址状态发生漂移。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType
from typing import Any, ClassVar, Literal, Self, cast
from urllib.parse import parse_qs, urlencode, urlsplit

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.b.disposition import (
    DispositionDenominatorRole,
    DispositionField,
    DispositionFieldFamily,
    DispositionMeasureObject,
    DispositionScopeLevel,
    DispositionStatisticForm,
    TrialDispositionObservation,
    validate_trial_disposition_observation,
)


class DispositionViewError(ValueError):
    """处置视图输入、筛选或同源投影不满足合同。"""


class DispositionChartType(StrEnum):
    """由处置事实兼容桶和统计语境确定的图形类型。"""

    POINT = "point"
    PROPORTION_BAR = "proportion_bar"
    CONSORT_FLOW = "consort_flow"
    REASON_STACKED_100 = "reason_stacked_100"
    REASON_INDEPENDENT_BAR = "reason_independent_bar"
    STATUS_MATRIX = "status_matrix"

    # Common adapter spellings resolve to the same scientific type.
    POINT_PLOT = "point"
    BAR = "proportion_bar"
    FLOW = "consort_flow"
    STACKED_100 = "reason_stacked_100"
    INDEPENDENT_BAR = "reason_independent_bar"
    DISCLOSURE = "status_matrix"
    DISCLOSURE_STATUS = "status_matrix"


class DispositionChartRowStatus(StrEnum):
    """图表行状态；不可绘制不等于明确为零。"""

    DRAWABLE = "drawable"
    DISCLOSURE = "disclosure"
    INCOMPLETE = "incomplete"


_DISLOSURE_LABELS_ZH: dict[FactDisclosureState, str] = {
    FactDisclosureState.REPORTED_VALUE: "已报告数值",
    FactDisclosureState.REPORTED_ZERO: "已报告为零",
    FactDisclosureState.NOT_REPORTED: "原文未报告",
    FactDisclosureState.BELOW_REPORTING_THRESHOLD: "低于来源列示阈值",
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED: "未公开",
    FactDisclosureState.NOT_APPLICABLE: "不适用",
    FactDisclosureState.CONFLICTING: "来源存在冲突",
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE: "技术路径未解决",
}

_FIELD_FAMILY_LABELS_ZH: dict[DispositionFieldFamily, str] = {
    DispositionFieldFamily.PARTICIPANT_FLOW: "受试者流转",
    DispositionFieldFamily.REASON: "处置原因",
    DispositionFieldFamily.ADHERENCE: "依从性",
    DispositionFieldFamily.RESCUE_TREATMENT: "补救治疗",
    DispositionFieldFamily.PROHIBITED_MEDICATION: "禁用药",
    DispositionFieldFamily.PROTOCOL_DEVIATION: "方案偏离",
}

_FIELD_LABELS_ZH: dict[DispositionField, str] = {
    DispositionField.SCREENED: "筛选评估",
    DispositionField.SCREEN_FAILURE: "筛选失败",
    DispositionField.RANDOMIZED: "随机分组",
    DispositionField.RECEIVED_TREATMENT: "接受研究治疗",
    DispositionField.COMPLETED_TREATMENT: "完成研究治疗",
    DispositionField.COMPLETED_STUDY: "完成研究",
    DispositionField.TREATMENT_DISCONTINUED: "停止研究治疗",
    DispositionField.STUDY_WITHDRAWAL: "退出研究",
    DispositionField.LOST_TO_FOLLOW_UP: "失访",
    DispositionField.SCREEN_FAILURE_REASON: "筛选失败原因",
    DispositionField.TREATMENT_DISCONTINUATION_REASON: "停止治疗原因",
    DispositionField.STUDY_WITHDRAWAL_REASON: "退出研究原因",
    DispositionField.ADHERENCE: "依从性",
    DispositionField.RESCUE_TREATMENT: "补救治疗",
    DispositionField.PROHIBITED_MEDICATION: "禁用药使用",
    DispositionField.PROTOCOL_DEVIATION: "方案偏离",
    DispositionField.MAJOR_PROTOCOL_DEVIATION: "重大方案偏离",
    DispositionField.PROTOCOL_DEVIATION_LEADING_TO_EXCLUSION: "导致排除的方案偏离",
    DispositionField.SOURCE_OTHER: "来源其他字段",
}

_MEASURE_LABELS_ZH: dict[DispositionMeasureObject, str] = {
    DispositionMeasureObject.SUBJECT: "受试者",
    DispositionMeasureObject.EVENT: "事件",
}

_STATISTIC_LABELS_ZH: dict[DispositionStatisticForm, str] = {
    DispositionStatisticForm.COUNT: "人数",
    DispositionStatisticForm.EVENT_COUNT: "事件数",
    DispositionStatisticForm.PROPORTION: "比例",
    DispositionStatisticForm.ADHERENCE_SUMMARY: "依从性汇总",
    DispositionStatisticForm.OTHER: "其他统计形式",
}

_DENOMINATOR_LABELS_ZH: dict[DispositionDenominatorRole, str] = {
    DispositionDenominatorRole.SCREENED: "筛选人群",
    DispositionDenominatorRole.RANDOMIZED: "随机人群",
    DispositionDenominatorRole.TREATED: "治疗人群",
    DispositionDenominatorRole.SAFETY: "安全性人群",
    DispositionDenominatorRole.ANALYSIS: "分析人群",
    DispositionDenominatorRole.PERIOD_START: "期间起始人群",
    DispositionDenominatorRole.OTHER: "其他分母",
}

_FIELD_ORDER: dict[DispositionField, int] = {
    DispositionField.SCREENED: 0,
    DispositionField.SCREEN_FAILURE: 1,
    DispositionField.RANDOMIZED: 2,
    DispositionField.RECEIVED_TREATMENT: 3,
    DispositionField.COMPLETED_TREATMENT: 4,
    DispositionField.COMPLETED_STUDY: 5,
    DispositionField.TREATMENT_DISCONTINUED: 6,
    DispositionField.STUDY_WITHDRAWAL: 7,
    DispositionField.LOST_TO_FOLLOW_UP: 8,
    DispositionField.SCREEN_FAILURE_REASON: 20,
    DispositionField.TREATMENT_DISCONTINUATION_REASON: 21,
    DispositionField.STUDY_WITHDRAWAL_REASON: 22,
    DispositionField.ADHERENCE: 30,
    DispositionField.RESCUE_TREATMENT: 31,
    DispositionField.PROHIBITED_MEDICATION: 32,
    DispositionField.PROTOCOL_DEVIATION: 40,
    DispositionField.MAJOR_PROTOCOL_DEVIATION: 41,
    DispositionField.PROTOCOL_DEVIATION_LEADING_TO_EXCLUSION: 42,
    DispositionField.SOURCE_OTHER: 50,
}

_FAMILY_ORDER: dict[DispositionFieldFamily, int] = {
    DispositionFieldFamily.PARTICIPANT_FLOW: 0,
    DispositionFieldFamily.REASON: 1,
    DispositionFieldFamily.ADHERENCE: 2,
    DispositionFieldFamily.RESCUE_TREATMENT: 3,
    DispositionFieldFamily.PROHIBITED_MEDICATION: 4,
    DispositionFieldFamily.PROTOCOL_DEVIATION: 5,
}

_DRAWABLE_DISCLOSURES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)

_CANONICAL_ROUTE = "/b/disposition"
_DISPOSITION_ROUTES = frozenset(
    {
        "/b/disposition",
        "/b/disposition-overview",
        "/b/participant-flow",
        "/b/adherence",
        "/b/loss-exit",
        "/b/screen-failure",
        "/b/rescue-treatment",
        "/b/prohibited-medication",
        "/b/plan-deviation",
    }
)


def _text(value: str, *, field_name: str = "处置视图字段") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name}必须是文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _optional_text(value: str | None, *, field_name: str = "处置视图字段") -> str | None:
    return None if value is None else _text(value, field_name=field_name)


def _token(value: object | None) -> str:
    if value is None:
        return "none"
    if isinstance(value, StrEnum):
        return value.value
    return str(value)


def _number_text(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    return format(value, "g")


def _field_family_label(family: DispositionFieldFamily) -> str:
    return _FIELD_FAMILY_LABELS_ZH[family]


def _field_label(field: DispositionField) -> str:
    return _FIELD_LABELS_ZH[field]


def _measure_label(measure: DispositionMeasureObject) -> str:
    return _MEASURE_LABELS_ZH[measure]


def _statistic_label(statistic: DispositionStatisticForm) -> str:
    return _STATISTIC_LABELS_ZH[statistic]


def _denominator_label(role: DispositionDenominatorRole) -> str:
    return _DENOMINATOR_LABELS_ZH[role]


def _value_label(fact: TrialDispositionObservation) -> str:
    return fact.display_value_zh


def _selection_values(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_values: tuple[object, ...] = tuple(value.split(",")) if "," in value else (value,)
    else:
        try:
            raw_values = tuple(cast(Iterable[object], value))
        except TypeError as error:
            raise ValueError(f"{field_name}必须是文本序列") from error
    normalized: list[str] = []
    for item in raw_values:
        candidate = getattr(item, "value", item)
        if not isinstance(candidate, str):
            raise ValueError(f"{field_name}必须是文本序列")
        normalized.append(_text(candidate, field_name=field_name))
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name}不得重复")
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _selection_enum_values(
    value: object,
    *,
    field_name: str,
    enum_type: type[Any],
) -> tuple[Any, ...]:
    values = _selection_values(value, field_name=field_name)
    try:
        converted = tuple(enum_type(item) for item in values)
    except ValueError as error:
        raise ValueError(f"{field_name}包含未知值") from error
    return tuple(sorted(converted, key=lambda item: (item.value.casefold(), item.value)))


def _validated_observation(
    value: TrialDispositionObservation | Mapping[str, Any],
) -> TrialDispositionObservation:
    try:
        if isinstance(value, TrialDispositionObservation):
            original = value.model_dump(mode="python", warnings=False)
            validated = validate_trial_disposition_observation(value)
            if validated.model_dump(mode="python", warnings=False) != original:
                raise DispositionViewError("原始观察重新校验改变了不可变事实")
            return validated
        return validate_trial_disposition_observation(value)
    except (DispositionViewError, TypeError, ValueError, ValidationError) as error:
        raise DispositionViewError(f"原始观察重新校验失败：{error}") from error


def disclosure_state_label_zh(state: FactDisclosureState | str) -> str:
    """返回面向临床用户的披露状态中文标签。"""

    try:
        resolved = state if isinstance(state, FactDisclosureState) else FactDisclosureState(state)
        return _DISLOSURE_LABELS_ZH[resolved]
    except (KeyError, ValueError) as error:
        raise DispositionViewError(f"未知处置披露状态：{state!r}") from error


class DispositionSelectionState(BaseModel):
    """页面级、模块级多选及证据焦点的可逆状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    product_ids: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("product_ids", "products", "product")
    )
    target_ids: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("target_ids", "targets", "target")
    )
    trial_ids: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("trial_ids", "trials", "trial")
    )
    period_ids: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("period_ids", "periods", "period")
    )
    cohort_ids: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("cohort_ids", "cohorts", "cohort")
    )
    group_ids: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("group_ids", "groups", "group")
    )
    analysis_populations: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "analysis_populations", "populations", "analysis_population", "population"
        ),
    )
    field_families: tuple[DispositionFieldFamily, ...] = Field(
        default=(), validation_alias=AliasChoices("field_families", "families", "family")
    )
    fields: tuple[DispositionField, ...] = Field(
        default=(), validation_alias=AliasChoices("fields", "field")
    )
    canonical_reasons: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("canonical_reasons", "reasons", "reason")
    )
    denominator_roles: tuple[DispositionDenominatorRole, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "denominator_roles", "denominators", "denominator_role", "denominator"
        ),
    )
    time_windows: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "time_windows", "windows", "time_window", "window"
        ),
    )
    measure_objects: tuple[DispositionMeasureObject, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "measure_objects", "measures", "measure_object", "measure"
        ),
    )
    statistic_forms: tuple[DispositionStatisticForm, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "statistic_forms", "statistics", "statistic_form", "statistic"
        ),
    )
    disclosure_states: tuple[FactDisclosureState, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "disclosure_states", "disclosures", "disclosure_state", "disclosure"
        ),
    )
    evidence_focus_id: str | None = Field(
        default=None, validation_alias=AliasChoices("evidence_focus_id", "focus_id", "focus")
    )

    _TEXT_FIELDS: ClassVar[tuple[str, ...]] = (
        "product_ids",
        "target_ids",
        "trial_ids",
        "period_ids",
        "cohort_ids",
        "group_ids",
        "analysis_populations",
        "canonical_reasons",
        "time_windows",
    )

    @field_validator(*_TEXT_FIELDS, mode="before")
    @classmethod
    def _selection_text_lists(cls, value: object, info: Any) -> tuple[str, ...]:
        return _selection_values(value, field_name=str(info.field_name))

    @field_validator("field_families", mode="before")
    @classmethod
    def _selection_families(cls, value: object) -> tuple[DispositionFieldFamily, ...]:
        return cast(
            tuple[DispositionFieldFamily, ...],
            _selection_enum_values(
                value, field_name="field_families", enum_type=DispositionFieldFamily
            ),
        )

    @field_validator("fields", mode="before")
    @classmethod
    def _selection_fields(cls, value: object) -> tuple[DispositionField, ...]:
        return cast(
            tuple[DispositionField, ...],
            _selection_enum_values(value, field_name="fields", enum_type=DispositionField),
        )

    @field_validator("denominator_roles", mode="before")
    @classmethod
    def _selection_denominators(cls, value: object) -> tuple[DispositionDenominatorRole, ...]:
        return cast(
            tuple[DispositionDenominatorRole, ...],
            _selection_enum_values(
                value,
                field_name="denominator_roles",
                enum_type=DispositionDenominatorRole,
            ),
        )

    @field_validator("measure_objects", mode="before")
    @classmethod
    def _selection_measures(cls, value: object) -> tuple[DispositionMeasureObject, ...]:
        return cast(
            tuple[DispositionMeasureObject, ...],
            _selection_enum_values(
                value, field_name="measure_objects", enum_type=DispositionMeasureObject
            ),
        )

    @field_validator("statistic_forms", mode="before")
    @classmethod
    def _selection_statistics(cls, value: object) -> tuple[DispositionStatisticForm, ...]:
        return cast(
            tuple[DispositionStatisticForm, ...],
            _selection_enum_values(
                value, field_name="statistic_forms", enum_type=DispositionStatisticForm
            ),
        )

    @field_validator("disclosure_states", mode="before")
    @classmethod
    def _selection_disclosures(cls, value: object) -> tuple[FactDisclosureState, ...]:
        return cast(
            tuple[FactDisclosureState, ...],
            _selection_enum_values(
                value, field_name="disclosure_states", enum_type=FactDisclosureState
            ),
        )

    @field_validator("evidence_focus_id")
    @classmethod
    def _focus_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="证据焦点标识")

    def to_url_items(self) -> tuple[tuple[str, str], ...]:
        """按重复查询参数表达多选，保持稳定键和值顺序。"""

        values: tuple[tuple[str, tuple[str, ...]], ...] = (
            ("product", self.product_ids),
            ("target", self.target_ids),
            ("trial", self.trial_ids),
            ("period", self.period_ids),
            ("cohort", self.cohort_ids),
            ("group", self.group_ids),
            ("population", self.analysis_populations),
            ("family", tuple(item.value for item in self.field_families)),
            ("field", tuple(item.value for item in self.fields)),
            ("reason", self.canonical_reasons),
            ("denominator", tuple(item.value for item in self.denominator_roles)),
            ("window", self.time_windows),
            ("measure", tuple(item.value for item in self.measure_objects)),
            ("statistic", tuple(item.value for item in self.statistic_forms)),
            ("disclosure", tuple(item.value for item in self.disclosure_states)),
        )
        items = [(key, item) for key, selected in values for item in selected]
        if self.evidence_focus_id is not None:
            items.append(("focus", self.evidence_focus_id))
        return tuple(sorted(items, key=lambda item: (item[0], item[1].casefold(), item[1])))

    def to_url_params(self) -> dict[str, str]:
        """返回兼容旧适配器的参数字典；多选值以逗号连接。"""

        params: dict[str, str] = {}
        for key, value in self.to_url_items():
            params[key] = f"{params[key]},{value}" if key in params else value
        return {key: params[key] for key in sorted(params)}

    @property
    def url_params(self) -> dict[str, str]:
        return self.to_url_params()

    @property
    def url_state(self) -> dict[str, str]:
        return self.to_url_params()

    def to_url_query(self) -> str:
        return urlencode(self.to_url_items(), doseq=True)

    to_query_string = to_url_query

    def to_url(self, route: str = _CANONICAL_ROUTE) -> str:
        normalized_route = _normalize_route(route)
        query = self.to_url_query()
        return f"{normalized_route}?{query}" if query else normalized_route

    @classmethod
    def from_url(cls, url: str) -> Self:
        if not isinstance(url, str) or not url.strip():
            raise DispositionViewError("处置 URL 不能为空")
        if "?" in url or "://" in url or url.lstrip().startswith("/"):
            raw_url = url
        else:
            raw_url = f"?{url.lstrip('?')}"
        parsed = urlsplit(raw_url)
        if parsed.scheme or parsed.netloc:
            raise DispositionViewError("处置 URL 必须使用报告内相对地址")
        if parsed.path and parsed.path not in _DISPOSITION_ROUTES:
            raise DispositionViewError("处置 URL 路由不属于试验完成情况页面")
        query = parse_qs(parsed.query, keep_blank_values=True)
        allowed = {
            "product",
            "target",
            "trial",
            "period",
            "cohort",
            "group",
            "population",
            "family",
            "field",
            "reason",
            "denominator",
            "window",
            "measure",
            "statistic",
            "disclosure",
            "focus",
        }
        unknown = set(query) - allowed
        if unknown:
            raise DispositionViewError(f"处置 URL 包含未知字段：{tuple(sorted(unknown))}")
        focus_values = query.get("focus", [])
        if len(focus_values) > 1:
            raise DispositionViewError("证据 focus 不得重复")
        payload: dict[str, object] = {
            "product_ids": tuple(query.get("product", ())),
            "target_ids": tuple(query.get("target", ())),
            "trial_ids": tuple(query.get("trial", ())),
            "period_ids": tuple(query.get("period", ())),
            "cohort_ids": tuple(query.get("cohort", ())),
            "group_ids": tuple(query.get("group", ())),
            "analysis_populations": tuple(query.get("population", ())),
            "field_families": tuple(query.get("family", ())),
            "fields": tuple(query.get("field", ())),
            "canonical_reasons": tuple(query.get("reason", ())),
            "denominator_roles": tuple(query.get("denominator", ())),
            "time_windows": tuple(query.get("window", ())),
            "measure_objects": tuple(query.get("measure", ())),
            "statistic_forms": tuple(query.get("statistic", ())),
            "disclosure_states": tuple(query.get("disclosure", ())),
            "evidence_focus_id": focus_values[0] if focus_values else None,
        }
        try:
            return cls.model_validate(payload)
        except (TypeError, ValueError, ValidationError) as error:
            raise DispositionViewError(f"处置 URL 状态无效：{error}") from error

    from_url_query = from_url


DispositionSelection = DispositionSelectionState
DispositionViewSelection = DispositionSelectionState


_TABLE_FACT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "row_id",
    "source_row_id",
    "observation_id",
    "product_id",
    "trial_id",
    "period_id",
    "cohort_id",
    "scope_level",
    "group_id",
    "analysis_population",
    "field_family",
    "field",
    "source_field_name",
    "source_field_definition",
    "measure_object",
    "statistic_form",
    "value",
    "raw_value",
    "unit",
    "numerator",
    "denominator",
    "denominator_role",
    "time_window",
    "reason_original_text",
    "canonical_reason",
    "reason_is_mutually_exclusive",
    "reason_is_exhaustive",
    "adherence_definition",
    "adherence_threshold",
    "protocol_deviation_level",
    "source_version_id",
    "source_locator",
    "source_role",
    "disclosure_maturity",
    "review_state",
    "disclosure_state",
    "conflict_disposition",
    "reported_zero_text",
    "route_receipt_id",
    "applicability_predicate_id",
    "compatibility_rule",
    "difference_labels_zh",
)


class DispositionTableRow(BaseModel):
    """处置事实的无损中文表格投影，并带图表资格状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    fact: TrialDispositionObservation = Field(
        validation_alias=AliasChoices("fact", "observation", "original_observation")
    )
    schema_version: Literal["1.0"]
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
    value: int | float | None = None
    raw_value: str | int | float | None = None
    unit: str | None = None
    numerator: int | None = None
    denominator: int | None = None
    denominator_role: DispositionDenominatorRole
    time_window: str
    reason_original_text: str | None = None
    canonical_reason: str | None = None
    reason_is_mutually_exclusive: bool | None = None
    reason_is_exhaustive: bool | None = None
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
    reported_proportion: int | float | None = None
    recomputed_proportion: float | None = None
    display_value_zh: str
    disclosure_label_zh: str
    chart_reason_zh: str | None = None
    is_chart_drawable: bool = False
    panel_bucket_id: str
    compatibility_bucket_id: str

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
        "panel_bucket_id",
        "compatibility_bucket_id",
    )
    @classmethod
    def _row_required_text(cls, value: str) -> str:
        return _text(value, field_name="处置表格字段")

    @field_validator("source_field_name", "source_field_definition", mode="before")
    @classmethod
    def _row_raw_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("处置表格来源文本不能为空")
        return value

    @field_validator("time_window", mode="before")
    @classmethod
    def _row_time_window(cls, value: str) -> str:
        return _text(value, field_name="处置表格时间窗")

    @field_validator("display_value_zh", "disclosure_label_zh")
    @classmethod
    def _row_labels(cls, value: str) -> str:
        return _text(value, field_name="处置表格中文标签")

    @field_validator("chart_reason_zh")
    @classmethod
    def _row_optional_label(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="处置图表说明")

    @model_validator(mode="after")
    def _row_matches_fact(self) -> Self:
        try:
            validated = validate_trial_disposition_observation(self.fact)
        except (TypeError, ValueError, ValidationError) as error:
            raise ValueError(f"处置表格原始观察重新校验失败：{error}") from error
        if validated.model_dump(mode="python", warnings=False) != self.fact.model_dump(
            mode="python", warnings=False
        ):
            raise ValueError("处置表格投影与原始观察不一致：原始观察未通过不可变校验")
        for field_name in _TABLE_FACT_FIELDS:
            if getattr(self, field_name) != getattr(self.fact, field_name):
                raise ValueError(f"处置表格投影与原始观察不一致：{field_name}")
        if self.reported_proportion != self.fact.reported_proportion:
            raise ValueError("处置表格报告比例与原始观察不一致")
        if self.recomputed_proportion != self.fact.recomputed_proportion:
            raise ValueError("处置表格复算比例与原始观察不一致")
        if self.display_value_zh != self.fact.display_value_zh:
            raise ValueError("处置表格显示值与原始观察不一致")
        if self.disclosure_label_zh != disclosure_state_label_zh(self.disclosure_state):
            raise ValueError("处置表格披露状态标签不一致")
        if self.is_chart_drawable and self.chart_reason_zh is not None:
            raise ValueError("可绘制处置行不得携带不可绘制原因")
        if not self.is_chart_drawable and self.chart_reason_zh is None:
            raise ValueError("不可绘制处置行必须携带中文原因")
        return self

    @property
    def original_observation(self) -> TrialDispositionObservation:
        return self.fact

    @property
    def observation(self) -> TrialDispositionObservation:
        return self.fact

    @property
    def fact_row_id(self) -> str:
        return self.row_id

    @property
    def fact_version_id(self) -> str:
        return self.row_id

    @property
    def identity_key(self) -> str:
        return self.row_id

    @property
    def source_locator_url(self) -> str | None:
        return self.source_locator.url

    @property
    def field_family_label_zh(self) -> str:
        return _field_family_label(self.field_family)

    @property
    def field_label_zh(self) -> str:
        return _field_label(self.field)

    @property
    def measure_label_zh(self) -> str:
        return _measure_label(self.measure_object)

    @property
    def statistic_label_zh(self) -> str:
        return _statistic_label(self.statistic_form)

    @property
    def denominator_label_zh(self) -> str:
        return _denominator_label(self.denominator_role)

    @property
    def status_label_zh(self) -> str:
        return "可绘制" if self.is_chart_drawable else self.disclosure_label_zh

    @property
    def chart_status(self) -> DispositionChartRowStatus:
        if self.is_chart_drawable:
            return DispositionChartRowStatus.DRAWABLE
        if self.disclosure_state not in _DRAWABLE_DISCLOSURES:
            return DispositionChartRowStatus.DISCLOSURE
        return DispositionChartRowStatus.INCOMPLETE

    @property
    def reason_zh(self) -> str:
        return self.chart_reason_zh or ""

    @property
    def value_label(self) -> str:
        return self.display_value_zh

    @property
    def chart_value(self) -> int | float | None:
        return self.value

    @property
    def is_drawable(self) -> bool:
        return self.is_chart_drawable

    @property
    def chart_compatibility_bucket_id(self) -> str:
        return self.panel_bucket_id


DispositionChartRow = DispositionTableRow
DispositionFactTableRow = DispositionTableRow


class DispositionChartPanel(BaseModel):
    """一个科学兼容桶的图形合同及其不可绘制状态行。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    panel_id: str
    field_family: DispositionFieldFamily
    field: DispositionField
    field_label_zh: str
    measure_object: DispositionMeasureObject
    statistic_form: DispositionStatisticForm
    denominator_role: DispositionDenominatorRole
    time_window: str
    chart_type: DispositionChartType
    compatibility_bucket_id: str
    drawable_rows: tuple[DispositionTableRow, ...] = ()
    status_rows: tuple[DispositionTableRow, ...] = ()
    difference_labels_zh: tuple[str, ...] = ()
    is_mixed_compatibility: bool = False
    is_stacked: bool = False
    has_axes: bool = False
    title_zh: str
    description_zh: str

    @field_validator(
        "panel_id",
        "field_label_zh",
        "time_window",
        "compatibility_bucket_id",
        "title_zh",
        "description_zh",
    )
    @classmethod
    def _panel_text(cls, value: str) -> str:
        return _text(value, field_name="处置图表面板字段")

    @field_validator("difference_labels_zh", mode="before")
    @classmethod
    def _panel_labels(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        values = (value,) if isinstance(value, str) else tuple(cast(Iterable[object], value))
        labels = tuple(_text(str(item), field_name="处置差异标签") for item in values)
        if len(set(labels)) != len(labels):
            raise ValueError("处置差异标签不得重复")
        return labels

    @model_validator(mode="after")
    def _panel_integrity(self) -> Self:
        rows = (*self.drawable_rows, *self.status_rows)
        row_ids = tuple(row.row_id for row in rows)
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("处置图表面板行标识不得重复")
        if rows and any(row.panel_bucket_id != self.compatibility_bucket_id for row in rows):
            raise ValueError("处置图表面板必须引用同一兼容桶")
        if any(not row.is_chart_drawable for row in self.drawable_rows):
            raise ValueError("图表可绘制行不得携带不可绘制状态")
        if any(row.is_chart_drawable for row in self.status_rows):
            raise ValueError("图表状态行不得携带坐标")
        if self.has_axes != bool(self.drawable_rows):
            raise ValueError("处置图表坐标轴状态必须与可绘制行一致")
        if not self.drawable_rows and self.chart_type is not DispositionChartType.STATUS_MATRIX:
            raise ValueError("无可绘制数值时只能生成披露状态面板")
        if self.drawable_rows and self.chart_type is DispositionChartType.STATUS_MATRIX:
            raise ValueError("存在可绘制数值时不得生成披露状态面板")
        if self.chart_type in {
            DispositionChartType.REASON_STACKED_100,
            DispositionChartType.REASON_INDEPENDENT_BAR,
        } and self.field_family is not DispositionFieldFamily.REASON:
            raise ValueError("原因图只能用于原因字段")
        if self.chart_type is DispositionChartType.CONSORT_FLOW and (
            self.field_family is not DispositionFieldFamily.PARTICIPANT_FLOW
        ):
            raise ValueError("受试者流转图只能用于受试者流转字段")
        if (
            self.chart_type is not DispositionChartType.CONSORT_FLOW
            and self.chart_type is not DispositionChartType.STATUS_MATRIX
            and any(row.field != self.field for row in rows)
        ):
            raise ValueError("非流转处置图表不得混合规范字段")
        if self.chart_type is DispositionChartType.PROPORTION_BAR and any(
            row.statistic_form is not DispositionStatisticForm.PROPORTION for row in rows
        ):
            raise ValueError("比例图表不得混合非比例统计")
        if self.chart_type is DispositionChartType.POINT and any(
            row.statistic_form is DispositionStatisticForm.PROPORTION for row in rows
        ):
            raise ValueError("点图不得混合比例统计")
        if self.is_stacked and self.chart_type is not DispositionChartType.REASON_STACKED_100:
            raise ValueError("只有原因 100% 堆叠图可以声明堆叠")
        if self.chart_type is DispositionChartType.REASON_STACKED_100:
            if self.field_family is not DispositionFieldFamily.REASON:
                raise ValueError("100% 堆叠图只能用于原因字段")
            if self.status_rows:
                raise ValueError("原因集合不完整时不得生成 100% 堆叠图")
            if any(
                row.reason_is_mutually_exclusive is not True
                or row.reason_is_exhaustive is not True
                for row in self.drawable_rows
            ):
                raise ValueError("原因集合未明确互斥且穷尽，不得生成 100% 堆叠图")
            if not self.is_stacked:
                raise ValueError("原因 100% 堆叠图必须声明堆叠")
        elif self.is_stacked:
            raise ValueError("非原因图不得声明堆叠")
        return self

    @property
    def rows(self) -> tuple[DispositionTableRow, ...]:
        return (*self.drawable_rows, *self.status_rows)

    @property
    def table_rows(self) -> tuple[DispositionTableRow, ...]:
        return self.rows

    @property
    def chart_rows(self) -> tuple[DispositionTableRow, ...]:
        return self.drawable_rows

    @property
    def unplottable_rows(self) -> tuple[DispositionTableRow, ...]:
        return self.status_rows

    @property
    def field_family_label_zh(self) -> str:
        return _field_family_label(self.field_family)

    @property
    def statistic_label_zh(self) -> str:
        return _statistic_label(self.statistic_form)

    @property
    def measure_label_zh(self) -> str:
        return _measure_label(self.measure_object)

    @property
    def denominator_label_zh(self) -> str:
        return _denominator_label(self.denominator_role)

    @property
    def compatibility_id(self) -> str:
        return self.compatibility_bucket_id

    @property
    def is_drawable(self) -> bool:
        return bool(self.drawable_rows)


DispositionPanel = DispositionChartPanel
DispositionChartView = DispositionChartPanel


class DispositionStatusMatrix(BaseModel):
    """当前筛选范围无可绘制数值时的试验 × 字段披露状态矩阵。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    matrix_id: str
    chart_type: DispositionChartType = DispositionChartType.STATUS_MATRIX
    rows: tuple[DispositionTableRow, ...] = ()
    trial_ids: tuple[str, ...] = ()
    fields: tuple[DispositionField, ...] = ()
    title_zh: str
    description_zh: str
    has_axes: bool = False

    @field_validator("matrix_id", "title_zh", "description_zh")
    @classmethod
    def _matrix_text(cls, value: str) -> str:
        return _text(value, field_name="处置状态矩阵字段")

    @field_validator("trial_ids", mode="before")
    @classmethod
    def _matrix_trials(cls, value: object) -> tuple[str, ...]:
        return _selection_values(value, field_name="处置状态矩阵试验")

    @field_validator("fields", mode="before")
    @classmethod
    def _matrix_fields(cls, value: object) -> tuple[DispositionField, ...]:
        fields = cast(
            tuple[DispositionField, ...],
            _selection_enum_values(
                value,
                field_name="处置状态矩阵字段",
                enum_type=DispositionField,
            ),
        )
        return tuple(sorted(fields, key=lambda item: (_FIELD_ORDER[item], item.value)))

    @model_validator(mode="after")
    def _matrix_integrity(self) -> Self:
        row_ids = tuple(row.row_id for row in self.rows)
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("处置状态矩阵行标识不得重复")
        if self.chart_type is not DispositionChartType.STATUS_MATRIX:
            raise ValueError("处置状态矩阵必须使用披露状态矩阵类型")
        if self.has_axes:
            raise ValueError("处置状态矩阵不得生成坐标轴")
        if any(row.is_chart_drawable for row in self.rows):
            raise ValueError("处置状态矩阵不得包含可绘制数值")
        trial_ids = tuple(
            sorted(
                {row.trial_id for row in self.rows},
                key=lambda item: (item.casefold(), item),
            )
        )
        if trial_ids != self.trial_ids:
            raise ValueError("处置状态矩阵试验集合不一致")
        fields = tuple(
            sorted(
                {row.field for row in self.rows},
                key=lambda item: (_FIELD_ORDER[item], item.value),
            )
        )
        if fields != self.fields:
            raise ValueError("处置状态矩阵字段集合不一致")
        return self

    @property
    def cells(self) -> tuple[DispositionTableRow, ...]:
        return self.rows

    @property
    def status_rows(self) -> tuple[DispositionTableRow, ...]:
        return self.rows

    @property
    def is_drawable(self) -> bool:
        return False


class DispositionFilterApplicability(BaseModel):
    """筛选维度是否在当前处置事实合同中适用。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    dimension: str
    enabled: bool
    reason_zh: str | None = None
    available_values: tuple[str, ...] = ()

    @field_validator("dimension")
    @classmethod
    def _dimension_text(cls, value: str) -> str:
        return _text(value, field_name="处置筛选维度")

    @field_validator("reason_zh")
    @classmethod
    def _reason_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="处置筛选说明")

    @field_validator("available_values", mode="before")
    @classmethod
    def _available_values(cls, value: object) -> tuple[str, ...]:
        return _selection_values(value, field_name="处置可用筛选值")

    @property
    def applicable(self) -> bool:
        return self.enabled

    @property
    def values(self) -> tuple[str, ...]:
        return self.available_values


class DispositionFilterOption(BaseModel):
    """一个面向用户的可用筛选值。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    dimension: str
    value: str
    label_zh: str
    enabled: bool = True
    fact_count: int = Field(default=0, ge=0)

    @field_validator("dimension", "value", "label_zh")
    @classmethod
    def _option_text(cls, value: str) -> str:
        return _text(value, field_name="处置筛选选项")

    @property
    def key(self) -> str:
        return self.value


class DispositionEmptyState(BaseModel):
    """真实空结果状态，不把空集合解释为缺失或零。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_empty: bool
    message_zh: str
    row_count: int = Field(default=0, ge=0)

    @field_validator("message_zh")
    @classmethod
    def _empty_message(cls, value: str) -> str:
        return _text(value, field_name="处置空状态文案")

    @model_validator(mode="after")
    def _empty_integrity(self) -> Self:
        if self.is_empty and self.message_zh != "当前筛选范围暂无处置事实":
            raise ValueError("处置空状态必须使用准确中文文案")
        if self.is_empty != (self.row_count == 0):
            raise ValueError("处置空状态行数不一致")
        return self

    @property
    def text_zh(self) -> str:
        return self.message_zh


class DispositionEvidenceLink(BaseModel):
    """表格行、图表点/节点和来源证据的一对一入口。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    row_id: str = Field(validation_alias=AliasChoices("row_id", "evidence_row_id"))
    fact_row_id: str = Field(validation_alias=AliasChoices("fact_row_id", "evidence_fact_row_id"))
    source_row_id: str
    source_version_id: str
    source_locator: EvidenceLocator
    label_zh: str
    href: str | None = None
    observation: TrialDispositionObservation

    @field_validator("row_id", "fact_row_id", "source_row_id", "source_version_id", "label_zh")
    @classmethod
    def _evidence_text(cls, value: str) -> str:
        return _text(value, field_name="处置证据字段")

    @field_validator("href")
    @classmethod
    def _evidence_href(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="处置证据链接")

    @model_validator(mode="after")
    def _evidence_integrity(self) -> Self:
        try:
            validated = validate_trial_disposition_observation(self.observation)
        except (TypeError, ValueError, ValidationError) as error:
            raise ValueError(f"处置证据原始观察重新校验失败：{error}") from error
        if validated.model_dump(mode="python", warnings=False) != self.observation.model_dump(
            mode="python", warnings=False
        ):
            raise ValueError("处置证据原始观察未通过不可变校验")
        if self.row_id != self.fact_row_id:
            raise ValueError("处置证据入口必须绑定同一事实行")
        if self.observation.row_id != self.fact_row_id:
            raise ValueError("处置证据入口必须绑定原始观察")
        if self.source_row_id != self.observation.source_row_id:
            raise ValueError("处置证据来源行必须与原始观察一致")
        if self.source_version_id != self.observation.source_version_id:
            raise ValueError("处置证据来源版本必须与原始观察一致")
        return self

    @property
    def fact_version_id(self) -> str:
        return self.fact_row_id

    @property
    def evidence_row_id(self) -> str:
        return self.row_id

    @property
    def table_row_id(self) -> str:
        return self.row_id

    @property
    def url(self) -> str | None:
        return self.href

    @property
    def original_observation(self) -> TrialDispositionObservation:
        return self.observation


DispositionEvidence = DispositionEvidenceLink
DispositionEvidenceReference = DispositionEvidenceLink


_SELECTION_ALIASES: dict[str, str] = {
    "product": "product_ids",
    "products": "product_ids",
    "product_ids": "product_ids",
    "target": "target_ids",
    "targets": "target_ids",
    "target_ids": "target_ids",
    "trial": "trial_ids",
    "trials": "trial_ids",
    "trial_ids": "trial_ids",
    "period": "period_ids",
    "periods": "period_ids",
    "period_id": "period_ids",
    "period_ids": "period_ids",
    "cohort": "cohort_ids",
    "cohorts": "cohort_ids",
    "cohort_ids": "cohort_ids",
    "group": "group_ids",
    "groups": "group_ids",
    "group_ids": "group_ids",
    "population": "analysis_populations",
    "populations": "analysis_populations",
    "analysis_population": "analysis_populations",
    "analysis_populations": "analysis_populations",
    "family": "field_families",
    "families": "field_families",
    "field_family": "field_families",
    "field_families": "field_families",
    "field": "fields",
    "fields": "fields",
    "reason": "canonical_reasons",
    "reasons": "canonical_reasons",
    "canonical_reason": "canonical_reasons",
    "canonical_reasons": "canonical_reasons",
    "denominator": "denominator_roles",
    "denominators": "denominator_roles",
    "denominator_role": "denominator_roles",
    "denominator_roles": "denominator_roles",
    "window": "time_windows",
    "windows": "time_windows",
    "time_window": "time_windows",
    "time_windows": "time_windows",
    "measure": "measure_objects",
    "measures": "measure_objects",
    "measure_object": "measure_objects",
    "measure_objects": "measure_objects",
    "statistic": "statistic_forms",
    "statistics": "statistic_forms",
    "statistic_form": "statistic_forms",
    "statistic_forms": "statistic_forms",
    "disclosure": "disclosure_states",
    "disclosures": "disclosure_states",
    "disclosure_state": "disclosure_states",
    "disclosure_states": "disclosure_states",
    "focus": "evidence_focus_id",
    "focus_id": "evidence_focus_id",
    "evidence_focus_id": "evidence_focus_id",
}

_PAGE_SELECTION_FIELDS = frozenset(
    {"product_ids", "target_ids", "trial_ids", "period_ids"}
)
_MODULE_SELECTION_FIELDS = frozenset(
    {
        "cohort_ids",
        "group_ids",
        "analysis_populations",
        "field_families",
        "fields",
        "canonical_reasons",
        "denominator_roles",
        "time_windows",
        "measure_objects",
        "statistic_forms",
        "disclosure_states",
        "evidence_focus_id",
    }
)


def _normalize_route(route: str) -> str:
    normalized = _text(route, field_name="处置 URL 路由")
    parsed = urlsplit(normalized)
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.path not in _DISPOSITION_ROUTES
    ):
        raise DispositionViewError("处置 URL 路由不属于试验完成情况页面")
    return parsed.path


def _canonical_selection_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    unknown = tuple(sorted({str(key) for key in value} - set(_SELECTION_ALIASES)))
    if unknown:
        raise DispositionViewError(f"处置选择状态包含未知字段：{unknown}")
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        canonical = _SELECTION_ALIASES[str(key)]
        if canonical in normalized:
            raise DispositionViewError(f"处置选择状态字段重复：{canonical}")
        normalized[canonical] = item
    return normalized


def _validated_selection(
    value: DispositionSelectionState | Mapping[str, Any],
) -> DispositionSelectionState:
    raw: object
    if isinstance(value, DispositionSelectionState):
        raw = value.model_dump(mode="python", warnings=False)
    elif isinstance(value, Mapping):
        raw = _canonical_selection_mapping(value)
    else:
        raise DispositionViewError("处置选择状态必须是 DispositionSelectionState 或映射")
    try:
        return DispositionSelectionState.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise DispositionViewError(f"选择状态重新校验失败：{error}") from error


def _selection_with_mapping(
    current: DispositionSelectionState,
    value: DispositionSelectionState | Mapping[str, Any],
) -> DispositionSelectionState:
    if isinstance(value, DispositionSelectionState):
        return _validated_selection(value)
    if not isinstance(value, Mapping):
        raise DispositionViewError("处置选择状态必须是 DispositionSelectionState 或映射")
    merged = current.model_dump(mode="python", warnings=False)
    merged.update(_canonical_selection_mapping(value))
    return _validated_selection(merged)


def _reason_context(fact: TrialDispositionObservation) -> tuple[str, ...]:
    return (
        fact.product_id,
        fact.trial_id,
        fact.period_id,
        _token(fact.cohort_id),
        fact.scope_level.value,
        _token(fact.group_id),
        fact.analysis_population,
    )


def _unit_compatibility_token(fact: TrialDispositionObservation) -> str:
    if fact.statistic_form is DispositionStatisticForm.COUNT:
        return f"subject_count:{(fact.unit or '').strip().casefold()}"
    if fact.statistic_form is DispositionStatisticForm.EVENT_COUNT:
        return f"event_count:{(fact.unit or '').strip().casefold()}"
    token = (fact.unit or "none").strip().casefold()
    if "%" in token or "％" in token or "百分" in token or token in {
        "percent",
        "percentage",
    }:
        return "percent"
    if token in {"ratio", "fraction", "proportion", "rate", "比例", "比率", "率"}:
        return "fraction"
    return token


def _reason_group_key(fact: TrialDispositionObservation) -> tuple[str, ...]:
    return (
        *_reason_context(fact),
        fact.field.value,
        fact.denominator_role.value,
        fact.time_window,
        fact.measure_object.value,
        fact.statistic_form.value,
        _unit_compatibility_token(fact),
        fact.source_field_definition,
        fact.compatibility_rule,
    )


def _reason_qualification_by_row_id(
    all_facts: Sequence[TrialDispositionObservation],
    selected_facts: Sequence[TrialDispositionObservation],
) -> dict[str, bool]:
    full_groups: dict[tuple[str, ...], list[TrialDispositionObservation]] = {}
    selected_groups: dict[tuple[str, ...], list[TrialDispositionObservation]] = {}
    for fact in all_facts:
        if fact.field_family is DispositionFieldFamily.REASON:
            full_groups.setdefault(_reason_group_key(fact), []).append(fact)
    for fact in selected_facts:
        if fact.field_family is DispositionFieldFamily.REASON:
            selected_groups.setdefault(_reason_group_key(fact), []).append(fact)
    qualified: dict[str, bool] = {}
    for key, selected_group in selected_groups.items():
        full_group = full_groups.get(key, ())
        complete_selection = {fact.row_id for fact in selected_group} == {
            fact.row_id for fact in full_group
        }
        denominators = {fact.denominator for fact in full_group}
        eligible = (
            len(full_group) >= 2
            and complete_selection
            and None not in denominators
            and len(denominators) == 1
            and all(
                fact.reason_is_mutually_exclusive is True
                and fact.reason_is_exhaustive is True
                for fact in full_group
            )
        )
        for fact in selected_group:
            qualified[fact.row_id] = eligible
    return qualified


def _panel_material(
    fact: TrialDispositionObservation,
    *,
    single_trial: bool,
    reason_qualified: bool = False,
) -> tuple[str, ...]:
    if (
        single_trial
        and fact.field_family is DispositionFieldFamily.PARTICIPANT_FLOW
        and fact.statistic_form is DispositionStatisticForm.COUNT
    ):
        return (
            "consort_flow",
            *_reason_context(fact),
            fact.time_window,
            fact.measure_object.value,
            _unit_compatibility_token(fact),
        )
    material: list[str] = [
        "disposition",
        fact.field_family.value,
        fact.field.value,
        fact.analysis_population,
        fact.denominator_role.value,
        fact.time_window,
        fact.measure_object.value,
        fact.statistic_form.value,
        _unit_compatibility_token(fact),
        fact.scope_level.value,
        fact.source_field_definition,
        fact.compatibility_rule,
        _token(fact.adherence_definition),
        _token(fact.adherence_threshold),
        _token(fact.protocol_deviation_level),
    ]
    if single_trial:
        material.extend(
            (
                fact.product_id,
                fact.period_id,
                _token(fact.cohort_id),
                fact.scope_level.value,
                _token(fact.group_id),
            )
        )
    if fact.field_family is DispositionFieldFamily.REASON:
        material.extend(
            (*_reason_context(fact), "qualified" if reason_qualified else "independent")
        )
    return tuple(material)


def _panel_bucket_id(
    fact: TrialDispositionObservation,
    *,
    single_trial: bool,
    reason_qualified: bool = False,
) -> str:
    return stable_id(
        "disposition-chart-bucket",
        *_panel_material(fact, single_trial=single_trial, reason_qualified=reason_qualified),
    )


def _fact_sort_key(fact: TrialDispositionObservation) -> tuple[object, ...]:
    return (
        _FAMILY_ORDER[fact.field_family],
        _FIELD_ORDER[fact.field],
        fact.field.value,
        fact.product_id.casefold(),
        fact.product_id,
        fact.trial_id.casefold(),
        fact.trial_id,
        fact.period_id.casefold(),
        fact.period_id,
        (fact.cohort_id or "").casefold(),
        fact.cohort_id or "",
        (fact.group_id or "").casefold(),
        fact.group_id or "",
        fact.analysis_population.casefold(),
        fact.analysis_population,
        fact.denominator_role.value,
        fact.time_window.casefold(),
        fact.time_window,
        fact.measure_object.value,
        fact.statistic_form.value,
        (fact.canonical_reason or "").casefold(),
        fact.canonical_reason or "",
        fact.row_id,
    )


def _chart_eligibility(fact: TrialDispositionObservation) -> tuple[bool, str | None]:
    if fact.disclosure_state not in _DRAWABLE_DISCLOSURES:
        return False, disclosure_state_label_zh(fact.disclosure_state)
    if fact.value is None:
        return False, "来源未提供可绘制数值，保留原始统计形式"
    return True, None


def _table_row(
    fact: TrialDispositionObservation,
    panel_bucket_id: str,
) -> DispositionTableRow:
    drawable, reason = _chart_eligibility(fact)
    payload = fact.model_dump(mode="python", warnings=False)
    payload.update(
        {
            "fact": fact,
            "reported_proportion": fact.reported_proportion,
            "recomputed_proportion": fact.recomputed_proportion,
            "display_value_zh": _value_label(fact),
            "disclosure_label_zh": disclosure_state_label_zh(fact.disclosure_state),
            "chart_reason_zh": reason,
            "is_chart_drawable": drawable,
            "panel_bucket_id": panel_bucket_id,
            "compatibility_bucket_id": panel_bucket_id,
        }
    )
    try:
        return DispositionTableRow.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as error:
        raise DispositionViewError(f"处置表格投影失败：{error}") from error


def _auto_difference_labels(
    fact: TrialDispositionObservation,
    same_field: Sequence[TrialDispositionObservation],
) -> tuple[str, ...]:
    labels: list[str] = []
    for other in same_field:
        if other.row_id == fact.row_id:
            continue
        if fact.denominator_role != other.denominator_role:
            labels.append("分母角色不同，拆分小多图")
        if fact.time_window != other.time_window:
            labels.append("时间窗不同，拆分小多图")
        if fact.measure_object != other.measure_object:
            labels.append("计量对象不同，拆分小多图")
        if fact.statistic_form != other.statistic_form:
            labels.append("统计形式不同，拆分小多图")
        if _unit_compatibility_token(fact) != _unit_compatibility_token(other):
            labels.append("单位或比例尺度不同，拆分小多图")
        if fact.scope_level != other.scope_level:
            labels.append("事实作用域不同，拆分小多图")
        if fact.source_field_definition != other.source_field_definition:
            labels.append("来源定义不同，拆分小多图")
        if fact.compatibility_rule != other.compatibility_rule:
            labels.append("兼容规则不同，拆分小多图")
        if (fact.adherence_definition, fact.adherence_threshold) != (
            other.adherence_definition,
            other.adherence_threshold,
        ):
            labels.append("依从性定义不同，拆分小多图")
        if fact.protocol_deviation_level != other.protocol_deviation_level:
            labels.append("方案偏离层级不同，拆分小多图")
        if fact.analysis_population != other.analysis_population:
            labels.append("分析人群不同，拆分小多图")
        if fact.period_id != other.period_id:
            labels.append("研究期间不同，拆分小多图")
    return tuple(dict.fromkeys(labels))


def _panel_chart_type(
    facts: Sequence[TrialDispositionObservation],
    drawable_rows: Sequence[DispositionTableRow],
    *,
    single_trial: bool,
    reason_qualified: bool,
) -> tuple[DispositionChartType, bool]:
    if not drawable_rows:
        return DispositionChartType.STATUS_MATRIX, False
    first = facts[0]
    if (
        single_trial
        and first.field_family is DispositionFieldFamily.PARTICIPANT_FLOW
        and first.statistic_form is DispositionStatisticForm.COUNT
    ):
        return DispositionChartType.CONSORT_FLOW, False
    if first.field_family is DispositionFieldFamily.REASON:
        qualified = reason_qualified and len(drawable_rows) == len(facts)
        return (
            (
                DispositionChartType.REASON_STACKED_100
                if qualified
                else DispositionChartType.REASON_INDEPENDENT_BAR
            ),
            qualified,
        )
    if first.statistic_form is DispositionStatisticForm.PROPORTION:
        return DispositionChartType.PROPORTION_BAR, False
    return DispositionChartType.POINT, False


def _panel_title_description(
    first: TrialDispositionObservation,
    chart_type: DispositionChartType,
    *,
    is_stacked: bool,
) -> tuple[str, str]:
    field_label = _field_label(first.field)
    measure_label = _measure_label(first.measure_object)
    statistic_label = _statistic_label(first.statistic_form)
    denominator_label = _denominator_label(first.denominator_role)
    if chart_type is DispositionChartType.CONSORT_FLOW:
        return (
            "试验受试者流转",
            "按来源披露的筛选、随机、治疗、完成、停止、退出和失访节点展示；不推导缺失流失人数。",
        )
    if chart_type is DispositionChartType.REASON_STACKED_100:
        return (
            f"{field_label}（100%堆叠）",
            "原因集合已明确互斥且穷尽，按来源原因展示构成；不将原因比例解释为额外退出率。",
        )
    if chart_type is DispositionChartType.REASON_INDEPENDENT_BAR:
        return (
            f"{field_label}（独立{measure_label}）",
            "原因集合未同时证明互斥且穷尽，逐项独立展示，不把原因数值相加为总退出率。",
        )
    if chart_type is DispositionChartType.STATUS_MATRIX:
        return (
            f"{field_label}披露状态",
            "当前事实没有可绘制数值，保留来源披露状态，不生成坐标轴。",
        )
    if first.measure_object is DispositionMeasureObject.EVENT:
        event_noun = (
            "事件数"
            if first.statistic_form is DispositionStatisticForm.EVENT_COUNT
            else "事件比例"
            if first.statistic_form is DispositionStatisticForm.PROPORTION
            else "来源事件统计值"
        )
        return (
            f"{field_label}（{statistic_label}，{denominator_label}）",
            f"按事件计量对象展示{event_noun}，不与受试者人数相加。",
        )
    return (
        f"{field_label}（{statistic_label}，{denominator_label}）",
        "按同一分母角色、统计形式和时间窗展示来源数值；完整来源事实见下表。",
    )


def _build_panels(
    facts: Sequence[TrialDispositionObservation],
    table_by_id: Mapping[str, DispositionTableRow],
    *,
    reason_qualified_by_row_id: Mapping[str, bool],
) -> tuple[DispositionChartPanel, ...]:
    single_trial = len({fact.trial_id for fact in facts}) == 1
    grouped: dict[str, list[TrialDispositionObservation]] = {}
    for fact in facts:
        qualified = reason_qualified_by_row_id.get(fact.row_id, False)
        bucket_id = _panel_bucket_id(
            fact, single_trial=single_trial, reason_qualified=qualified
        )
        grouped.setdefault(bucket_id, []).append(fact)
    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: min(_fact_sort_key(fact) for fact in item[1]),
    )
    panels: list[DispositionChartPanel] = []
    for bucket_id, bucket_facts in ordered_groups:
        ordered_facts = tuple(sorted(bucket_facts, key=_fact_sort_key))
        rows = tuple(table_by_id[fact.row_id] for fact in ordered_facts)
        drawable_rows = tuple(row for row in rows if row.is_chart_drawable)
        status_rows = tuple(row for row in rows if not row.is_chart_drawable)
        first = ordered_facts[0]
        reason_qualified = all(
            reason_qualified_by_row_id.get(fact.row_id, False) for fact in ordered_facts
        )
        chart_type, is_stacked = _panel_chart_type(
            ordered_facts,
            drawable_rows,
            single_trial=single_trial,
            reason_qualified=reason_qualified,
        )
        labels: list[str] = []
        same_field = tuple(fact for fact in facts if fact.field is first.field)
        for fact in ordered_facts:
            for label in (
                *fact.difference_labels_zh,
                *_auto_difference_labels(fact, same_field),
            ):
                if label not in labels:
                    labels.append(label)
        title, description = _panel_title_description(
            first, chart_type, is_stacked=is_stacked
        )
        try:
            panels.append(
                DispositionChartPanel(
                    panel_id=bucket_id,
                    field_family=first.field_family,
                    field=first.field,
                    field_label_zh=_field_label(first.field),
                    measure_object=first.measure_object,
                    statistic_form=first.statistic_form,
                    denominator_role=first.denominator_role,
                    time_window=first.time_window,
                    chart_type=chart_type,
                    compatibility_bucket_id=bucket_id,
                    drawable_rows=drawable_rows,
                    status_rows=status_rows,
                    difference_labels_zh=tuple(labels),
                    is_mixed_compatibility=False,
                    is_stacked=is_stacked,
                    has_axes=bool(drawable_rows),
                    title_zh=title,
                    description_zh=description,
                )
            )
        except (TypeError, ValueError, ValidationError) as error:
            raise DispositionViewError(f"处置图表面板组装失败：{error}") from error
    return tuple(panels)


def _filter_match(fact: TrialDispositionObservation, selection: DispositionSelectionState) -> bool:
    # Target is intentionally absent from TrialDispositionObservation. An active
    # target selection therefore yields no rows instead of silently widening.
    if selection.target_ids:
        return False
    checks: tuple[tuple[tuple[Any, ...], Any], ...] = (
        (selection.product_ids, fact.product_id),
        (selection.trial_ids, fact.trial_id),
        (selection.period_ids, fact.period_id),
        (selection.cohort_ids, fact.cohort_id),
        (selection.group_ids, fact.group_id),
        (selection.analysis_populations, fact.analysis_population),
        (selection.field_families, fact.field_family),
        (selection.fields, fact.field),
        (selection.canonical_reasons, fact.canonical_reason),
        (selection.denominator_roles, fact.denominator_role),
        (selection.time_windows, fact.time_window),
        (selection.measure_objects, fact.measure_object),
        (selection.statistic_forms, fact.statistic_form),
        (selection.disclosure_states, fact.disclosure_state),
    )
    return all(not selected or current in selected for selected, current in checks)


def _filter_label(dimension: str, value: str, *, display_value: str | None = None) -> str:
    labels = {
        "product": "产品",
        "trial": "试验",
        "period": "研究期间",
        "cohort": "队列",
        "group": "组别",
        "analysis_population": "分析人群",
        "field_family": "字段族",
        "field": "字段",
        "canonical_reason": "规范原因",
        "denominator_role": "分母角色",
        "time_window": "时间窗",
        "measure_object": "计量对象",
        "statistic_form": "统计形式",
        "disclosure_state": "披露状态",
    }
    if dimension == "field_family":
        try:
            return f"字段族：{_field_family_label(DispositionFieldFamily(value))}"
        except ValueError:
            return f"字段族：{value}"
    if dimension == "field":
        try:
            return f"字段：{_field_label(DispositionField(value))}"
        except ValueError:
            return f"字段：{display_value or value}"
    if dimension == "denominator_role":
        try:
            return f"分母角色：{_denominator_label(DispositionDenominatorRole(value))}"
        except ValueError:
            return f"分母角色：{value}"
    if dimension == "measure_object":
        try:
            return f"计量对象：{_measure_label(DispositionMeasureObject(value))}"
        except ValueError:
            return f"计量对象：{value}"
    if dimension == "statistic_form":
        try:
            return f"统计形式：{_statistic_label(DispositionStatisticForm(value))}"
        except ValueError:
            return f"统计形式：{value}"
    if dimension == "disclosure_state":
        try:
            return f"披露状态：{disclosure_state_label_zh(FactDisclosureState(value))}"
        except ValueError:
            return f"披露状态：{value}"
    if dimension in {"analysis_population", "canonical_reason", "time_window"} and (
        "_" in value or re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{3,}", value) is not None
    ):
        fallback = {
            "analysis_population": "其他分析人群",
            "canonical_reason": "其他规范原因",
            "time_window": "其他观察时间范围",
        }
        return f"{labels[dimension]}：{fallback[dimension]}"
    return f"{labels.get(dimension, '筛选')}：{value}"


def _build_filter_surface(
    facts: Sequence[TrialDispositionObservation],
) -> tuple[dict[str, DispositionFilterApplicability], tuple[DispositionFilterOption, ...]]:
    supported: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("product", tuple(sorted({fact.product_id for fact in facts}))),
        ("trial", tuple(sorted({fact.trial_id for fact in facts}))),
        ("period", tuple(sorted({fact.period_id for fact in facts}))),
        ("cohort", tuple(sorted({fact.cohort_id for fact in facts if fact.cohort_id is not None}))),
        ("group", tuple(sorted({fact.group_id for fact in facts if fact.group_id is not None}))),
        (
            "analysis_population",
            tuple(sorted({fact.analysis_population for fact in facts})),
        ),
        (
            "field_family",
            tuple(sorted({fact.field_family.value for fact in facts})),
        ),
        ("field", tuple(sorted({fact.field.value for fact in facts}))),
        (
            "canonical_reason",
            tuple(
                sorted(
                    {
                        fact.canonical_reason
                        for fact in facts
                        if fact.canonical_reason is not None
                    }
                )
            ),
        ),
        (
            "denominator_role",
            tuple(sorted({fact.denominator_role.value for fact in facts})),
        ),
        ("time_window", tuple(sorted({fact.time_window for fact in facts}))),
        ("measure_object", tuple(sorted({fact.measure_object.value for fact in facts}))),
        ("statistic_form", tuple(sorted({fact.statistic_form.value for fact in facts}))),
        (
            "disclosure_state",
            tuple(sorted({fact.disclosure_state.value for fact in facts})),
        ),
    )
    applicability: dict[str, DispositionFilterApplicability] = {}
    options: list[DispositionFilterOption] = []
    for dimension, values in supported:
        enabled = bool(values)
        applicability[dimension] = DispositionFilterApplicability(
            dimension=dimension,
            enabled=enabled,
            reason_zh=None if enabled else "当前处置事实未提供该筛选维度",
            available_values=values,
        )
        for value in values:
            current_values: dict[
                str, Callable[[TrialDispositionObservation], object]
            ] = {
                "product": lambda fact: fact.product_id,
                "trial": lambda fact: fact.trial_id,
                "period": lambda fact: fact.period_id,
                "cohort": lambda fact: fact.cohort_id,
                "group": lambda fact: fact.group_id,
                "analysis_population": lambda fact: fact.analysis_population,
                "field_family": lambda fact: fact.field_family.value,
                "field": lambda fact: fact.field.value,
                "canonical_reason": lambda fact: fact.canonical_reason,
                "denominator_role": lambda fact: fact.denominator_role.value,
                "time_window": lambda fact: fact.time_window,
                "measure_object": lambda fact: fact.measure_object.value,
                "statistic_form": lambda fact: fact.statistic_form.value,
                "disclosure_state": lambda fact: fact.disclosure_state.value,
            }
            count = sum(1 for fact in facts if current_values[dimension](fact) == value)
            display_value = next(
                (
                    fact.source_field_name
                    for fact in facts
                    if dimension == "field" and fact.field.value == value
                ),
                None,
            )
            options.append(
                DispositionFilterOption(
                    dimension=dimension,
                    value=value,
                    label_zh=_filter_label(dimension, value, display_value=display_value),
                    fact_count=count,
                )
            )
    applicability["target"] = DispositionFilterApplicability(
        dimension="target",
        enabled=False,
        reason_zh="当前处置事实不适用靶点筛选维度",
    )
    dimension_order = {
        "product": 0,
        "target": 1,
        "trial": 2,
        "period": 3,
        "cohort": 4,
        "group": 5,
        "analysis_population": 6,
        "field_family": 7,
        "field": 8,
        "canonical_reason": 9,
        "denominator_role": 10,
        "time_window": 11,
        "measure_object": 12,
        "statistic_form": 13,
        "disclosure_state": 14,
    }
    options.sort(
        key=lambda option: (
            dimension_order[option.dimension],
            option.value.casefold(),
            option.value,
        )
    )
    return applicability, tuple(options)


def _evidence_link(row: DispositionTableRow) -> DispositionEvidenceLink:
    return DispositionEvidenceLink(
        row_id=row.row_id,
        fact_row_id=row.row_id,
        source_row_id=row.source_row_id,
        source_version_id=row.source_version_id,
        source_locator=row.source_locator,
        label_zh=f"{_field_family_label(row.field_family)}：{_field_label(row.field)}",
        href=row.source_locator.url,
        observation=row.fact,
    )


def _build_status_matrix(
    rows: Sequence[DispositionTableRow],
) -> DispositionStatusMatrix | None:
    if not rows or any(row.is_chart_drawable for row in rows):
        return None
    ordered_rows = tuple(rows)
    try:
        return DispositionStatusMatrix(
            matrix_id=stable_id("disposition-status-matrix", *(row.row_id for row in ordered_rows)),
            rows=ordered_rows,
            trial_ids=tuple(
                sorted(
                    {row.trial_id for row in ordered_rows},
                    key=lambda item: (item.casefold(), item),
                )
            ),
            fields=tuple(
                sorted(
                    {row.field for row in ordered_rows},
                    key=lambda item: (_FIELD_ORDER[item], item.value),
                )
            ),
            title_zh="试验完成情况披露状态",
            description_zh="当前筛选范围没有可绘制数值，以试验和规范字段展示原始披露状态。",
            has_axes=False,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise DispositionViewError(f"处置披露状态矩阵组装失败：{error}") from error


def _assemble_view_state(
    facts: Sequence[TrialDispositionObservation],
    *,
    selected_facts: Sequence[TrialDispositionObservation],
    selection: DispositionSelectionState,
    default_selection: DispositionSelectionState,
    route: str,
) -> DispositionViewState:
    ordered_facts = tuple(sorted(facts, key=_fact_sort_key))
    ordered_selected = tuple(sorted(selected_facts, key=_fact_sort_key))
    single_trial = len({fact.trial_id for fact in ordered_selected}) == 1
    bucket_by_id: dict[str, str] = {}
    reason_qualified_by_row_id = _reason_qualification_by_row_id(
        ordered_facts, ordered_selected
    )
    for fact in ordered_selected:
        qualified = reason_qualified_by_row_id.get(fact.row_id, False)
        bucket_by_id[fact.row_id] = _panel_bucket_id(
            fact, single_trial=single_trial, reason_qualified=qualified
        )
    table_rows = tuple(
        _table_row(fact, bucket_by_id[fact.row_id]) for fact in ordered_selected
    )
    table_by_id = {row.row_id: row for row in table_rows}
    panels = _build_panels(
        ordered_selected,
        table_by_id,
        reason_qualified_by_row_id=reason_qualified_by_row_id,
    )
    links = tuple(_evidence_link(row) for row in table_rows)
    links_by_id = {link.row_id: link for link in links}
    focus_row = None
    normalized_selection = selection
    if selection.evidence_focus_id is not None:
        focus_row = table_by_id.get(selection.evidence_focus_id)
        if focus_row is None:
            normalized_selection = _validated_selection(
                selection.model_copy(update={"evidence_focus_id": None})
            )
    normalized_route = _normalize_route(route)
    applicability, options = _build_filter_surface(ordered_facts)
    status_matrix = _build_status_matrix(table_rows)
    try:
        return DispositionViewState(
            selection=normalized_selection,
            default_selection=default_selection,
            facts=ordered_facts,
            selected_facts=ordered_selected,
            chart_panels=panels,
            status_matrix=status_matrix,
            complete_table=table_rows,
            table_row_ids=tuple(row.row_id for row in table_rows),
            filter_applicability=applicability,
            filter_options=options,
            evidence_links=links,
            evidence_links_by_row_id=links_by_id,
            evidence_focus_row_id=None if focus_row is None else focus_row.row_id,
            evidence_focus=focus_row,
            empty_state=DispositionEmptyState(
                is_empty=not table_rows,
                message_zh=(
                    "当前筛选范围暂无处置事实"
                    if not table_rows
                    else "当前筛选范围包含处置事实"
                ),
                row_count=len(table_rows),
            ),
            url_state=normalized_selection.to_url_params(),
            url=normalized_selection.to_url(normalized_route),
            route=normalized_route,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise DispositionViewError(f"处置同步视图组装失败：{error}") from error


class DispositionViewState(BaseModel):
    """由同一事实源确定性重建图、完整表、状态矩阵、证据和 URL。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    selection: DispositionSelectionState
    default_selection: DispositionSelectionState
    facts: tuple[TrialDispositionObservation, ...] = ()
    selected_facts: tuple[TrialDispositionObservation, ...] = ()
    chart_panels: tuple[DispositionChartPanel, ...] = ()
    status_matrix: DispositionStatusMatrix | None = None
    complete_table: tuple[DispositionTableRow, ...] = ()
    table_row_ids: tuple[str, ...] = ()
    filter_applicability: Mapping[str, DispositionFilterApplicability] = Field(default_factory=dict)
    filter_options: tuple[DispositionFilterOption, ...] = ()
    evidence_links: tuple[DispositionEvidenceLink, ...] = ()
    evidence_links_by_row_id: Mapping[str, DispositionEvidenceLink] = Field(default_factory=dict)
    evidence_focus_row_id: str | None = None
    evidence_focus: DispositionTableRow | None = None
    empty_state: DispositionEmptyState
    url_state: Mapping[str, str] = Field(default_factory=dict)
    url: str
    route: str = _CANONICAL_ROUTE

    @field_validator("url", "route")
    @classmethod
    def _state_url(cls, value: str) -> str:
        return _text(value, field_name="处置 URL")

    @field_validator(
        "filter_applicability",
        "evidence_links_by_row_id",
        "url_state",
        mode="after",
    )
    @classmethod
    def _freeze_mappings(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return MappingProxyType(dict(value))

    @field_serializer("filter_applicability", "evidence_links_by_row_id", "url_state")
    def _serialize_mappings(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return dict(value)

    @model_validator(mode="after")
    def _state_integrity(self) -> Self:
        # Revalidate source observations at every model boundary. Pydantic's
        # frozen model_copy can otherwise carry a forged nested object.
        validated_facts: list[TrialDispositionObservation] = []
        if self.default_selection != DispositionSelectionState():
            raise ValueError("处置默认选择必须保持初始空状态")
        for fact in self.facts:
            validated_facts.append(_validated_observation(fact))
        fact_ids = tuple(fact.row_id for fact in validated_facts)
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("处置视图原始观察不得重复")
        if tuple(fact_ids) != tuple(fact.row_id for fact in self.facts):
            raise ValueError("处置视图原始观察身份未通过不可变校验")
        selected_ids = tuple(fact.row_id for fact in self.selected_facts)
        if not set(selected_ids) <= set(fact_ids):
            raise ValueError("处置筛选结果必须来自原始观察集合")
        expected_selected = tuple(
            fact for fact in validated_facts if _filter_match(fact, self.selection)
        )
        if selected_ids != tuple(fact.row_id for fact in expected_selected):
            raise ValueError("处置筛选结果与选择状态不一致")
        table_ids = tuple(row.row_id for row in self.complete_table)
        if table_ids != self.table_row_ids:
            raise ValueError("处置完整表行标识不一致")
        if table_ids != selected_ids:
            raise ValueError("完整表必须覆盖全部筛选后事实且不丢行")
        if len(set(table_ids)) != len(table_ids):
            raise ValueError("处置完整表行标识不得重复")
        table_by_id = {row.row_id: row for row in self.complete_table}
        for fact in expected_selected:
            row = table_by_id.get(fact.row_id)
            if row is None or row.fact != fact:
                raise ValueError("处置完整表必须保留筛选后原始事实")
        panel_ids: list[str] = []
        panel_row_ids: list[str] = []
        for panel in self.chart_panels:
            if panel.compatibility_bucket_id in panel_ids:
                raise ValueError("处置图表兼容桶不得重复")
            panel_ids.append(panel.compatibility_bucket_id)
            panel_row_ids.extend(row.row_id for row in panel.rows)
        if set(panel_row_ids) != set(table_ids):
            raise ValueError("图表与完整表必须引用同一筛选后事实集合")
        if len(panel_row_ids) != len(set(panel_row_ids)):
            raise ValueError("处置图表行不得重复引用")
        any_drawable = any(row.is_chart_drawable for row in self.complete_table)
        if any_drawable and self.status_matrix is not None:
            raise ValueError("有可绘制数值时不得生成披露状态矩阵")
        if not any_drawable and table_ids and self.status_matrix is None:
            raise ValueError("无可绘制数值时必须生成披露状态矩阵")
        if self.status_matrix is not None and (
            tuple(row.row_id for row in self.status_matrix.rows) != table_ids
        ):
            raise ValueError("披露状态矩阵必须覆盖完整表全部事实")
        link_ids = tuple(link.row_id for link in self.evidence_links)
        if link_ids != table_ids:
            raise ValueError("处置证据必须覆盖完整表全部事实")
        if tuple(self.evidence_links_by_row_id) != table_ids:
            raise ValueError("处置证据索引必须保持完整表顺序")
        if any(self.evidence_links_by_row_id[row_id].row_id != row_id for row_id in table_ids):
            raise ValueError("处置证据索引行标识不一致")
        if self.evidence_focus_row_id != (
            None if self.evidence_focus is None else self.evidence_focus.row_id
        ):
            raise ValueError("处置证据焦点行标识不一致")
        if self.evidence_focus is not None and self.evidence_focus.row_id not in table_ids:
            raise ValueError("处置证据焦点必须来自完整表")
        if self.empty_state.is_empty != (not table_ids):
            raise ValueError("处置空状态必须与筛选后事实集合一致")
        if self.url_state != self.selection.to_url_params():
            raise ValueError("处置 URL 状态必须与选择状态一致")
        if self.url != self.selection.to_url(self.route):
            raise ValueError("处置 URL 必须与选择状态和路由一致")
        return self

    @property
    def selection_state(self) -> DispositionSelectionState:
        return self.selection

    @property
    def disposition_selection(self) -> DispositionSelectionState:
        return self.selection

    @property
    def rows(self) -> tuple[DispositionTableRow, ...]:
        return self.complete_table

    @property
    def table(self) -> tuple[DispositionTableRow, ...]:
        return self.complete_table

    @property
    def full_table(self) -> tuple[DispositionTableRow, ...]:
        return self.complete_table

    @property
    def table_rows(self) -> tuple[DispositionTableRow, ...]:
        return self.complete_table

    @property
    def panels(self) -> tuple[DispositionChartPanel, ...]:
        return self.chart_panels

    @property
    def charts(self) -> tuple[DispositionChartPanel, ...]:
        return self.chart_panels

    @property
    def chart(self) -> tuple[DispositionChartPanel, ...]:
        return self.chart_panels

    @property
    def evidence(self) -> tuple[DispositionEvidenceLink, ...]:
        return self.evidence_links

    @property
    def evidence_references(self) -> tuple[DispositionEvidenceLink, ...]:
        return self.evidence_links

    @property
    def focused_row(self) -> DispositionTableRow | None:
        return self.evidence_focus

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
    def available_facts(self) -> tuple[TrialDispositionObservation, ...]:
        return self.facts

    @property
    def source_facts(self) -> tuple[TrialDispositionObservation, ...]:
        return self.facts

    def assert_synchronized(self) -> Self:
        try:
            validated = type(self).model_validate(
                self.model_dump(mode="python", warnings=False)
            )
            selected = tuple(
                fact for fact in validated.facts if _filter_match(fact, validated.selection)
            )
            rebuilt = _assemble_view_state(
                validated.facts,
                selected_facts=selected,
                selection=validated.selection,
                default_selection=validated.default_selection,
                route=validated.route,
            )
        except (DispositionViewError, TypeError, ValueError, ValidationError) as error:
            raise DispositionViewError(f"处置同步视图重新校验失败：{error}") from error
        if rebuilt.model_dump(mode="python", warnings=False) != validated.model_dump(
            mode="python", warnings=False
        ):
            raise DispositionViewError("处置同步视图与原始事实重新计算结果不一致")
        return self

    def with_selection(
        self,
        selection: DispositionSelectionState | Mapping[str, Any],
    ) -> DispositionViewState:
        self.assert_synchronized()
        parsed = _selection_with_mapping(self.selection, selection)
        selected = tuple(fact for fact in self.facts if _filter_match(fact, parsed))
        return _assemble_view_state(
            self.facts,
            selected_facts=selected,
            selection=parsed,
            default_selection=self.default_selection,
            route=self.route,
        )
    update_selection = with_selection
    apply_selection = with_selection
    select = with_selection
    rebuild = with_selection

    def with_evidence_focus(self, row_id: str | None) -> DispositionViewState:
        self.assert_synchronized()
        if row_id is not None:
            normalized = _text(row_id, field_name="证据焦点标识")
            if normalized not in self.table_row_ids:
                raise DispositionViewError("证据焦点必须来自当前完整表")
            row_id = normalized
        return self.with_selection(self.selection.model_copy(update={"evidence_focus_id": row_id}))

    focus_evidence = with_evidence_focus
    set_evidence_focus = with_evidence_focus

    def reset(
        self,
        scope: Literal["page", "module", "full"] | str | None = None,
    ) -> DispositionViewState:
        self.assert_synchronized()
        normalized_scope = (
            "full"
            if scope is None
            else _text(scope, field_name="处置重置范围").casefold()
        )
        if normalized_scope in {"full", "all", "view"}:
            parsed = self.default_selection
        elif normalized_scope == "page":
            values = self.selection.model_dump(mode="python", warnings=False)
            for field_name in _PAGE_SELECTION_FIELDS:
                values[field_name] = getattr(self.default_selection, field_name)
            parsed = _validated_selection(values)
        elif normalized_scope == "module":
            values = self.selection.model_dump(mode="python", warnings=False)
            for field_name in _MODULE_SELECTION_FIELDS:
                values[field_name] = getattr(self.default_selection, field_name)
            parsed = _validated_selection(values)
        else:
            raise DispositionViewError("处置重置范围必须是 page、module 或 full")
        selected = tuple(fact for fact in self.facts if _filter_match(fact, parsed))
        return _assemble_view_state(
            self.facts,
            selected_facts=selected,
            selection=parsed,
            default_selection=self.default_selection,
            route=self.route,
        )

    reset_selection = reset
    reset_view = reset


DispositionSynchronizedView = DispositionViewState
DispositionPageState = DispositionViewState
DispositionInteractionState = DispositionViewState


def build_disposition_view_state(
    observations: Sequence[TrialDispositionObservation | Mapping[str, Any]]
    | Iterable[TrialDispositionObservation | Mapping[str, Any]],
    selection: DispositionSelectionState | Mapping[str, Any] | None = None,
    *,
    route: str = _CANONICAL_ROUTE,
) -> DispositionViewState:
    """从 TrialDispositionObservation 单一事实源构建同步处置视图。"""

    try:
        raw_values = tuple(observations)
    except TypeError as error:
        raise DispositionViewError("处置观察必须是可迭代事实集合") from error
    facts = tuple(_validated_observation(value) for value in raw_values)
    fact_ids = tuple(fact.row_id for fact in facts)
    if len(set(fact_ids)) != len(fact_ids):
        raise DispositionViewError("重复 row_id 或重复事实，拒绝构建处置视图")
    ordered_facts = tuple(sorted(facts, key=_fact_sort_key))
    default_selection = DispositionSelectionState()
    parsed = default_selection if selection is None else _validated_selection(selection)
    selected = tuple(fact for fact in ordered_facts if _filter_match(fact, parsed))
    return _assemble_view_state(
        ordered_facts,
        selected_facts=selected,
        selection=parsed,
        default_selection=default_selection,
        route=route,
    )


build_disposition_view = build_disposition_view_state
build_disposition_page_state = build_disposition_view_state
build_disposition_synchronized_view = build_disposition_view_state
build_disposition_interaction_state = build_disposition_view_state
build_disposition_state = build_disposition_view_state


def apply_disposition_selection(
    value: DispositionViewState,
    selection: DispositionSelectionState | Mapping[str, Any],
) -> DispositionViewState:
    if not isinstance(value, DispositionViewState):
        raise DispositionViewError("应用处置选择必须传入 DispositionViewState")
    return value.with_selection(selection)


update_disposition_selection = apply_disposition_selection
select_disposition_view = apply_disposition_selection
update_disposition_view = apply_disposition_selection


def reset_disposition_selection(
    value: DispositionViewState,
    scope: Literal["page", "module", "full"] | str | None = None,
) -> DispositionViewState:
    if not isinstance(value, DispositionViewState):
        raise DispositionViewError("重置处置选择必须传入 DispositionViewState")
    return value.reset(scope)


reset_disposition_view = reset_disposition_selection
reset_disposition_view_state = reset_disposition_selection


def selection_to_url(
    selection: DispositionSelectionState | Mapping[str, Any],
    route: str = _CANONICAL_ROUTE,
) -> str:
    return _validated_selection(selection).to_url(route)


def selection_from_url(url: str) -> DispositionSelectionState:
    return DispositionSelectionState.from_url(url)


parse_disposition_url_state = selection_from_url


__all__ = [
    "DispositionChartPanel",
    "DispositionChartRow",
    "DispositionChartRowStatus",
    "DispositionChartType",
    "DispositionChartView",
    "DispositionEmptyState",
    "DispositionEvidence",
    "DispositionEvidenceLink",
    "DispositionEvidenceReference",
    "DispositionFactTableRow",
    "DispositionFilterApplicability",
    "DispositionFilterOption",
    "DispositionInteractionState",
    "DispositionPageState",
    "DispositionPanel",
    "DispositionSelection",
    "DispositionSelectionState",
    "DispositionStatusMatrix",
    "DispositionSynchronizedView",
    "DispositionTableRow",
    "DispositionViewError",
    "DispositionViewSelection",
    "DispositionViewState",
    "apply_disposition_selection",
    "build_disposition_interaction_state",
    "build_disposition_page_state",
    "build_disposition_state",
    "build_disposition_synchronized_view",
    "build_disposition_view",
    "build_disposition_view_state",
    "disclosure_state_label_zh",
    "parse_disposition_url_state",
    "reset_disposition_selection",
    "reset_disposition_view",
    "reset_disposition_view_state",
    "selection_from_url",
    "selection_to_url",
    "select_disposition_view",
    "update_disposition_selection",
    "update_disposition_view",
]
