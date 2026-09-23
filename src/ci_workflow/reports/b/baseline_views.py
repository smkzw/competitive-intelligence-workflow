"""B 类基线人口学、疾病语境和严重程度的同源视图模型。

本模块只投影已经通过 :mod:`baseline` 合同校验的事实。它不计算跨试验
优劣、不补造类别或区间，也不负责 HTML 渲染；图形面板和完整表格始终
从同一筛选后的 ``BaselineObservation`` 集合生成。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
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
from ci_workflow.gates.models import (
    ConflictDisposition,
    DisclosureMaturity,
    SourceRole,
)
from ci_workflow.reports.b.baseline import (
    BaselineCompatibilityKey,
    BaselineDataType,
    BaselineObservation,
    BaselineStatisticForm,
    BaselineVariableDomain,
    validate_baseline_observation,
)


class BaselineViewError(ValueError):
    """基线视图输入、筛选或同源投影不满足合同。"""


class BaselineChartType(StrEnum):
    """由来源统计形式确定的图表面板类型。"""

    POINT = "point"
    INTERVAL = "interval"
    PROPORTION_BAR = "proportion_bar"
    SMALL_MULTIPLE = "small_multiple"
    DISCLOSURE = "disclosure"

    # Adapter spellings all resolve to the same scientific type.
    POINT_PLOT = "point"
    INTERVAL_PLOT = "interval"
    BAR = "proportion_bar"
    SMALL_MULTIPLES = "small_multiple"
    DISCLOSURE_STATUS = "disclosure"


class BaselineChartRowStatus(StrEnum):
    """图表行状态；不可绘制不等于数值零。"""

    DRAWABLE = "drawable"
    DISCLOSURE = "disclosure"
    INCOMPLETE = "incomplete"


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

_DOMAIN_LABELS_ZH: dict[BaselineVariableDomain, str] = {
    BaselineVariableDomain.DEMOGRAPHICS: "人口学",
    BaselineVariableDomain.DISEASE_CONTEXT: "疾病语境",
    BaselineVariableDomain.BASELINE_SEVERITY: "基线疾病严重程度",
}

_STATISTIC_LABELS_ZH: dict[BaselineStatisticForm, str] = {
    BaselineStatisticForm.SAMPLE_SIZE: "组别基线样本量",
    BaselineStatisticForm.MEAN: "均值",
    BaselineStatisticForm.STANDARD_DEVIATION: "标准差",
    BaselineStatisticForm.MEDIAN: "中位数",
    BaselineStatisticForm.QUARTILES: "四分位数",
    BaselineStatisticForm.RANGE: "范围",
    BaselineStatisticForm.COUNT: "计数",
    BaselineStatisticForm.PROPORTION: "比例",
    BaselineStatisticForm.OTHER: "其他统计形式",
}

_CONCEPT_LABELS_ZH: dict[str, str] = {
    "baseline_sample_size": "组别基线样本量",
    "sample_size": "组别基线样本量",
    "baseline_n": "组别基线样本量",
    "n": "组别基线样本量",
    "age": "年龄",
    "baseline_age": "年龄",
    "age_at_baseline": "年龄",
    "sex": "性别",
    "gender": "性别",
    "baseline_sex": "性别",
    "baseline_gender": "性别",
    "ethnicity": "种族/民族",
    "race": "种族/民族",
    "region": "地区",
    "weight": "体重",
    "body_weight": "体重",
    "bmi": "体重指数（BMI）",
    "body_mass_index": "体重指数（BMI）",
    "disease_duration": "病程",
    "prior_treatment": "既往/背景治疗",
    "background_treatment": "既往/背景治疗",
    "phenotype": "表型/亚型",
    "subtype": "表型/亚型",
    "exacerbation_history": "既往加重或事件史",
    "event_history": "既往加重或事件史",
    "comorbidity": "相关合并症",
    "biomarker": "生物标志物",
    "easi_total_score": "EASI 总分",
    "eczema_area_severity_index": "EASI 总分",
    "pruritus_nrs": "瘙痒 NRS",
    "disease_activity_score": "疾病活动度评分",
}

_SAMPLE_SIZE_CONCEPTS = frozenset({"baseline_sample_size", "sample_size", "baseline_n", "n"})
_AGE_CONCEPTS = frozenset({"age", "baseline_age", "age_at_baseline"})
_SEX_CONCEPTS = frozenset({"sex", "gender", "baseline_sex", "baseline_gender"})
# These are stable clinical severity anchors commonly supplied by the B-v1
# adapters. Unknown severity concepts remain visible after disease context;
# they are never inferred from numeric values.
_SEVERITY_ANCHOR_CONCEPTS = frozenset(
    {
        "easi_total_score",
        "eczema_area_severity_index",
        "disease_activity_score",
        "baseline_severity_score",
        "severity_score",
    }
)

_STATISTIC_ORDER = {
    BaselineStatisticForm.SAMPLE_SIZE: 0,
    BaselineStatisticForm.MEAN: 1,
    BaselineStatisticForm.STANDARD_DEVIATION: 2,
    BaselineStatisticForm.MEDIAN: 3,
    BaselineStatisticForm.QUARTILES: 4,
    BaselineStatisticForm.RANGE: 5,
    BaselineStatisticForm.COUNT: 6,
    BaselineStatisticForm.PROPORTION: 7,
    BaselineStatisticForm.OTHER: 8,
}

_DRAWABLE_DISCLOSURES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)


def _text(value: str, *, field_name: str = "基线视图字段") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name}必须是文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _optional_text(value: str | None, *, field_name: str = "基线视图字段") -> str | None:
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


def _value_label(
    *,
    value: int | float | None,
    unit: str | None,
    range_lower: int | float | None,
    range_upper: int | float | None,
) -> str | None:
    if range_lower is not None and range_upper is not None:
        value_text = f"{_number_text(range_lower)}–{_number_text(range_upper)}"
    elif value is not None:
        value_text = _number_text(value)
    else:
        return None
    if unit is None:
        return value_text
    separator = "" if unit in {"%", "％"} else " "
    return f"{value_text}{separator}{unit}"


def _domain_label(domain: BaselineVariableDomain) -> str:
    return _DOMAIN_LABELS_ZH[domain]


def _statistic_label(statistic_form: BaselineStatisticForm) -> str:
    return _STATISTIC_LABELS_ZH[statistic_form]


def _concept_label(concept: str, source_name: str | None = None) -> str:
    normalized = concept.strip().casefold().replace("-", "_").replace(" ", "_")
    known = _CONCEPT_LABELS_ZH.get(normalized)
    if known is not None:
        return known
    candidate = source_name or concept
    if re.fullmatch(r"[a-z0-9_.:/-]+", candidate.strip(), flags=re.IGNORECASE):
        return "其他基线变量"
    return candidate


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


def _validated_observation(value: BaselineObservation | Mapping[str, Any]) -> BaselineObservation:
    try:
        if isinstance(value, BaselineObservation):
            original = value.model_dump(mode="python")
            validated = validate_baseline_observation(value)
            if validated.model_dump(mode="python") != original:
                raise BaselineViewError("原始观察重新校验改变了不可变事实")
            return validated
        return validate_baseline_observation(value)
    except (BaselineViewError, TypeError, ValueError, ValidationError) as error:
        raise BaselineViewError(f"原始观察重新校验失败：{error}") from error


def disclosure_state_label_zh(state: FactDisclosureState) -> str:
    """返回面向临床用户的披露状态中文标签。"""

    try:
        return _DISCLOSURE_LABELS_ZH[state]
    except KeyError as error:
        raise BaselineViewError(f"未知基线披露状态：{state!r}") from error


class BaselineSelectionState(BaseModel):
    """页面级、模块级多选及证据焦点的可逆状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    product_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("product_ids", "products", "product"),
    )
    target_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("target_ids", "targets", "target"),
    )
    trial_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("trial_ids", "trials", "trial"),
    )
    cohort_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("cohort_ids", "cohorts", "cohort"),
    )
    group_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("group_ids", "groups", "group"),
    )
    region_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("region_ids", "regions", "region"),
    )
    analysis_populations: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "analysis_populations",
            "populations",
            "analysis_population",
            "population",
        ),
    )
    variable_domains: tuple[BaselineVariableDomain, ...] = Field(
        default=(),
        validation_alias=AliasChoices("variable_domains", "domains", "variable_domain", "domain"),
    )
    standardized_concepts: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "standardized_concepts",
            "concepts",
            "standardized_concept",
            "concept",
        ),
    )
    statistic_forms: tuple[BaselineStatisticForm, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "statistic_forms",
            "statistics",
            "statistic_form",
            "statistic",
        ),
    )
    scales: tuple[str, ...] = Field(default=(), validation_alias=AliasChoices("scales", "scale"))
    units: tuple[str, ...] = Field(default=(), validation_alias=AliasChoices("units", "unit"))
    disclosure_states: tuple[FactDisclosureState, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "disclosure_states",
            "disclosures",
            "disclosure_state",
            "disclosure",
        ),
    )
    evidence_focus_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("evidence_focus_id", "focus_id", "focus"),
    )

    _ID_FIELDS: ClassVar[tuple[str, ...]] = (
        "product_ids",
        "target_ids",
        "trial_ids",
        "cohort_ids",
        "group_ids",
        "region_ids",
        "analysis_populations",
        "standardized_concepts",
        "scales",
        "units",
    )

    @field_validator(*_ID_FIELDS, mode="before")
    @classmethod
    def _selection_text_lists(cls, value: object, info: Any) -> tuple[str, ...]:
        return _selection_values(value, field_name=str(info.field_name))

    @field_validator("variable_domains", mode="before")
    @classmethod
    def _selection_domains(cls, value: object) -> tuple[BaselineVariableDomain, ...]:
        return cast(
            tuple[BaselineVariableDomain, ...],
            _selection_enum_values(
                value,
                field_name="variable_domains",
                enum_type=BaselineVariableDomain,
            ),
        )

    @field_validator("statistic_forms", mode="before")
    @classmethod
    def _selection_statistics(cls, value: object) -> tuple[BaselineStatisticForm, ...]:
        return cast(
            tuple[BaselineStatisticForm, ...],
            _selection_enum_values(
                value,
                field_name="statistic_forms",
                enum_type=BaselineStatisticForm,
            ),
        )

    @field_validator("disclosure_states", mode="before")
    @classmethod
    def _selection_disclosures(cls, value: object) -> tuple[FactDisclosureState, ...]:
        return cast(
            tuple[FactDisclosureState, ...],
            _selection_enum_values(
                value,
                field_name="disclosure_states",
                enum_type=FactDisclosureState,
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
            ("cohort", self.cohort_ids),
            ("group", self.group_ids),
            ("region", self.region_ids),
            ("population", self.analysis_populations),
            ("domain", tuple(item.value for item in self.variable_domains)),
            ("concept", self.standardized_concepts),
            ("statistic", tuple(item.value for item in self.statistic_forms)),
            ("scale", self.scales),
            ("unit", self.units),
            ("disclosure", tuple(item.value for item in self.disclosure_states)),
        )
        items = [(key, item) for key, selected in values for item in selected]
        if self.evidence_focus_id is not None:
            items.append(("focus", self.evidence_focus_id))
        return tuple(sorted(items, key=lambda item: (item[0], item[1].casefold(), item[1])))

    def to_url_params(self) -> dict[str, str]:
        """返回兼容旧适配器的稳定参数字典；多选值以逗号连接。"""

        params: dict[str, str] = {}
        for key, value in self.to_url_items():
            if key in params:
                params[key] = f"{params[key]},{value}"
            else:
                params[key] = value
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

    def to_url(self, route: str = "/b/baseline") -> str:
        normalized_route = _text(route, field_name="基线 URL 路由")
        query = self.to_url_query()
        return f"{normalized_route}?{query}" if query else normalized_route

    @classmethod
    def from_url(cls, url: str) -> Self:
        if not isinstance(url, str) or not url.strip():
            raise BaselineViewError("基线 URL 不能为空")
        if "?" in url or "://" in url or url.lstrip().startswith("/"):
            raw_url = url
        else:
            raw_url = f"?{url.lstrip('?')}"
        parsed = urlsplit(raw_url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        allowed = {
            "product",
            "target",
            "trial",
            "cohort",
            "group",
            "region",
            "population",
            "domain",
            "concept",
            "statistic",
            "scale",
            "unit",
            "disclosure",
            "focus",
        }
        unknown = set(query) - allowed
        if unknown:
            raise BaselineViewError(f"基线 URL 包含未知字段：{tuple(sorted(unknown))}")
        focus_values = query.get("focus", [])
        if len(focus_values) > 1:
            raise BaselineViewError("证据 focus 不得重复")
        payload: dict[str, object] = {
            "product_ids": tuple(query.get("product", ())),
            "target_ids": tuple(query.get("target", ())),
            "trial_ids": tuple(query.get("trial", ())),
            "cohort_ids": tuple(query.get("cohort", ())),
            "group_ids": tuple(query.get("group", ())),
            "region_ids": tuple(query.get("region", ())),
            "analysis_populations": tuple(query.get("population", ())),
            "variable_domains": tuple(query.get("domain", ())),
            "standardized_concepts": tuple(query.get("concept", ())),
            "statistic_forms": tuple(query.get("statistic", ())),
            "scales": tuple(query.get("scale", ())),
            "units": tuple(query.get("unit", ())),
            "disclosure_states": tuple(query.get("disclosure", ())),
            "evidence_focus_id": focus_values[0] if focus_values else None,
        }
        try:
            return cls.model_validate(payload)
        except (TypeError, ValueError, ValidationError) as error:
            raise BaselineViewError(f"基线 URL 状态无效：{error}") from error

    from_url_query = from_url


BaselineSelection = BaselineSelectionState
BaselineViewSelection = BaselineSelectionState


# All source fields are deliberately copied to the table projection. The
# nested fact additionally gives adapters one immutable, revalidated source
# object instead of forcing them to reconstruct it from display columns.
_TABLE_FACT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "row_id",
    "source_row_id",
    "observation_id",
    "product_id",
    "trial_id",
    "cohort_id",
    "group_id",
    "analysis_population",
    "variable_domain",
    "source_name",
    "source_definition",
    "standardized_concept",
    "scale",
    "scale_version",
    "direction",
    "theoretical_range",
    "data_type",
    "statistic_form",
    "value",
    "raw_value",
    "unit",
    "dispersion",
    "range_lower",
    "range_upper",
    "category_level",
    "bin_label",
    "bin_lower",
    "bin_upper",
    "numerator",
    "denominator",
    "denominator_role",
    "baseline_definition",
    "baseline_timepoint",
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


class BaselineTableRow(BaseModel):
    """基线事实的无损表格投影，并带图表资格状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    fact: BaselineObservation = Field(
        validation_alias=AliasChoices("fact", "observation", "original_observation")
    )
    schema_version: Literal["1.0"]
    row_id: str
    source_row_id: str
    observation_id: str
    product_id: str
    trial_id: str
    cohort_id: str
    group_id: str
    analysis_population: str
    variable_domain: BaselineVariableDomain
    source_name: str
    source_definition: str
    standardized_concept: str
    scale: str | None = None
    scale_version: str | None = None
    direction: str | None = None
    theoretical_range: str | None = None
    data_type: BaselineDataType
    statistic_form: BaselineStatisticForm
    value: int | float | None = None
    raw_value: str | None = None
    unit: str | None = None
    dispersion: int | float | None = None
    range_lower: int | float | None = None
    range_upper: int | float | None = None
    category_level: str | None = None
    bin_label: str | None = None
    bin_lower: int | float | None = None
    bin_upper: int | float | None = None
    numerator: int | None = None
    denominator: int | None = None
    denominator_role: str | None = None
    baseline_definition: str
    baseline_timepoint: str
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
    value_label: str | None = None
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
        "cohort_id",
        "group_id",
        "analysis_population",
        "source_version_id",
        "compatibility_rule",
        "panel_bucket_id",
        "compatibility_bucket_id",
    )
    @classmethod
    def _row_required_text(cls, value: str) -> str:
        return _text(value, field_name="基线表格字段")

    @field_validator("source_name", "source_definition", mode="before")
    @classmethod
    def _row_raw_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("基线表格来源文本不能为空")
        return value

    @field_validator("value_label", "chart_reason_zh")
    @classmethod
    def _row_optional_label(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="基线图表说明")

    @model_validator(mode="after")
    def _row_matches_fact(self) -> Self:
        for field_name in _TABLE_FACT_FIELDS:
            if getattr(self, field_name) != getattr(self.fact, field_name):
                raise ValueError(f"基线表格投影与原始观察不一致：{field_name}")
        if self.compatibility_bucket_id != self.fact.compatibility_bucket_id:
            raise ValueError("基线表格必须保留原始兼容键标识")
        if self.is_chart_drawable and self.chart_reason_zh is not None:
            raise ValueError("可绘制基线行不得携带不可绘制原因")
        if not self.is_chart_drawable and self.chart_reason_zh is None:
            raise ValueError("不可绘制基线行必须携带中文原因")
        return self

    @property
    def original_observation(self) -> BaselineObservation:
        return self.fact

    @property
    def observation(self) -> BaselineObservation:
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
    def compatibility_key(self) -> BaselineCompatibilityKey:
        return self.fact.compatibility_key

    @property
    def statistic(self) -> BaselineStatisticForm:
        return self.statistic_form
    @property
    def domain_label_zh(self) -> str:
        return _domain_label(self.variable_domain)

    @property
    def variable_label_zh(self) -> str:
        return _concept_label(self.standardized_concept, self.source_name)

    @property
    def statistic_label_zh(self) -> str:
        return _statistic_label(self.statistic_form)

    @property
    def status_reason_zh(self) -> str:
        return self.reason_zh

    @property
    def chart_compatibility_bucket_id(self) -> str:
        return self.panel_bucket_id

    @property
    def disclosure_label_zh(self) -> str:
        return disclosure_state_label_zh(self.disclosure_state)

    @property
    def status_label_zh(self) -> str:
        if self.is_chart_drawable:
            return "可绘制"
        return (
            self.disclosure_label_zh
            if self.disclosure_state not in _DRAWABLE_DISCLOSURES
            else "保留原始统计形式"
        )

    @property
    def chart_status(self) -> BaselineChartRowStatus:
        if self.is_chart_drawable:
            return BaselineChartRowStatus.DRAWABLE
        if self.disclosure_state not in _DRAWABLE_DISCLOSURES:
            return BaselineChartRowStatus.DISCLOSURE
        return BaselineChartRowStatus.INCOMPLETE

    @property
    def reason_zh(self) -> str:
        return self.chart_reason_zh or ""

    @property
    def display_value_zh(self) -> str:
        return self.value_label or self.disclosure_label_zh

    @property
    def is_drawable(self) -> bool:
        return self.is_chart_drawable

    @property
    def chart_value(self) -> int | float | None:
        return self.value

    @property
    def source_locator_url(self) -> str | None:
        return self.source_locator.url


BaselineChartRow = BaselineTableRow
BaselineFactTableRow = BaselineTableRow


class BaselineChartPanel(BaseModel):
    """一个科学兼容桶的图形合同及其不可绘制状态行。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    panel_id: str
    variable_domain: BaselineVariableDomain
    standardized_concept: str
    variable_label_zh: str
    statistic_form: BaselineStatisticForm
    data_type: BaselineDataType
    chart_type: BaselineChartType
    compatibility_bucket_id: str
    analysis_population: str | None = None
    denominator_role: str | None = None
    drawable_rows: tuple[BaselineTableRow, ...] = ()
    status_rows: tuple[BaselineTableRow, ...] = ()
    difference_labels_zh: tuple[str, ...] = ()
    is_mixed_compatibility: bool = False
    is_stacked: bool = False
    has_axes: bool = False
    title_zh: str
    description_zh: str

    @field_validator(
        "panel_id",
        "standardized_concept",
        "variable_label_zh",
        "compatibility_bucket_id",
        "title_zh",
        "description_zh",
    )
    @classmethod
    def _panel_text(cls, value: str) -> str:
        return _text(value, field_name="基线图表面板字段")

    @field_validator("difference_labels_zh", mode="before")
    @classmethod
    def _panel_labels(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        values = (value,) if isinstance(value, str) else tuple(cast(Iterable[object], value))
        labels = tuple(_text(str(item), field_name="基线差异标签") for item in values)
        if len(set(labels)) != len(labels):
            raise ValueError("基线差异标签不得重复")
        return labels

    @model_validator(mode="after")
    def _panel_integrity(self) -> Self:
        drawable_ids = tuple(row.row_id for row in self.drawable_rows)
        status_ids = tuple(row.row_id for row in self.status_rows)
        if len(set(drawable_ids + status_ids)) != len(drawable_ids + status_ids):
            raise ValueError("基线图表面板行标识不得重复")
        if set(drawable_ids + status_ids) and any(
            row.panel_bucket_id != self.compatibility_bucket_id
            for row in (*self.drawable_rows, *self.status_rows)
        ):
            raise ValueError("基线图表面板必须引用同一兼容桶")
        if any(not row.is_chart_drawable for row in self.drawable_rows):
            raise ValueError("图表可绘制行不得携带不可绘制状态")
        if any(row.is_chart_drawable for row in self.status_rows):
            raise ValueError("图表状态行不得携带坐标")
        if self.has_axes != bool(self.drawable_rows):
            raise ValueError("基线图表坐标轴状态必须与可绘制行一致")
        if self.is_stacked:
            raise ValueError("基线视图不允许未经穷尽证明的 100% 堆叠图")
        if not self.drawable_rows and self.chart_type is not BaselineChartType.DISCLOSURE:
            raise ValueError("无可绘制数值时只能生成披露状态面板")
        if self.drawable_rows and self.chart_type is BaselineChartType.DISCLOSURE:
            raise ValueError("存在可绘制数值时不得生成空披露面板")
        return self

    @property
    def rows(self) -> tuple[BaselineTableRow, ...]:
        return (*self.drawable_rows, *self.status_rows)

    @property
    def table_rows(self) -> tuple[BaselineTableRow, ...]:
        return self.rows

    @property
    def chart_rows(self) -> tuple[BaselineTableRow, ...]:
        return self.drawable_rows

    @property
    def unplottable_rows(self) -> tuple[BaselineTableRow, ...]:
        return self.status_rows

    @property
    def domain(self) -> BaselineVariableDomain:
        return self.variable_domain

    @property
    def variable(self) -> str:
        return self.standardized_concept

    @property
    def statistic(self) -> BaselineStatisticForm:
        return self.statistic_form
    @property
    def label_zh(self) -> str:
        return self.variable_label_zh

    @property
    def compatibility_id(self) -> str:
        return self.compatibility_bucket_id

    @property
    def domain_label_zh(self) -> str:
        return _domain_label(self.variable_domain)

    @property
    def statistic_label_zh(self) -> str:
        return _statistic_label(self.statistic_form)

    @property
    def compatibility_key(self) -> BaselineCompatibilityKey:
        return (
            self.drawable_rows[0].fact.compatibility_key
            if self.drawable_rows
            else self.status_rows[0].fact.compatibility_key
        )

    @property
    def is_drawable(self) -> bool:
        return bool(self.drawable_rows)


BaselinePanel = BaselineChartPanel
BaselineChartView = BaselineChartPanel


class BaselineFilterApplicability(BaseModel):
    """筛选维度是否在当前 BaselineObservation 合同中适用。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    dimension: str
    enabled: bool
    reason_zh: str | None = None
    available_values: tuple[str, ...] = ()

    @field_validator("dimension")
    @classmethod
    def _dimension_text(cls, value: str) -> str:
        return _text(value, field_name="基线筛选维度")

    @field_validator("reason_zh")
    @classmethod
    def _reason_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="基线筛选说明")

    @field_validator("available_values", mode="before")
    @classmethod
    def _available_values(cls, value: object) -> tuple[str, ...]:
        return _selection_values(value, field_name="基线可用筛选值")

    @property
    def applicable(self) -> bool:
        return self.enabled

    @property
    def values(self) -> tuple[str, ...]:
        return self.available_values


class BaselineFilterOption(BaseModel):
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
        return _text(value, field_name="基线筛选选项")

    @property
    def key(self) -> str:
        return self.value


class BaselineEmptyState(BaseModel):
    """真实空结果状态，不将空集合解释为缺失或零。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_empty: bool
    message_zh: str
    row_count: int = Field(default=0, ge=0)

    @field_validator("message_zh")
    @classmethod
    def _empty_message(cls, value: str) -> str:
        return _text(value, field_name="基线空状态文案")

    @model_validator(mode="after")
    def _empty_integrity(self) -> Self:
        if self.is_empty and self.message_zh != "当前筛选范围暂无基线事实":
            raise ValueError("基线空状态必须使用准确中文文案")
        if self.is_empty != (self.row_count == 0):
            raise ValueError("基线空状态行数不一致")
        return self

    @property
    def text_zh(self) -> str:
        return self.message_zh


class BaselineEvidenceLink(BaseModel):
    """表格/图表行对应的精确证据入口。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    row_id: str = Field(validation_alias=AliasChoices("row_id", "evidence_row_id"))
    fact_row_id: str = Field(validation_alias=AliasChoices("fact_row_id", "evidence_fact_row_id"))
    source_row_id: str
    source_version_id: str
    source_locator: EvidenceLocator
    label_zh: str
    href: str | None = None
    observation: BaselineObservation

    @field_validator("row_id", "fact_row_id", "source_row_id", "source_version_id", "label_zh")
    @classmethod
    def _evidence_text(cls, value: str) -> str:
        return _text(value, field_name="基线证据字段")

    @field_validator("href")
    @classmethod
    def _evidence_href(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="基线证据链接")

    @model_validator(mode="after")
    def _evidence_integrity(self) -> Self:
        if self.row_id != self.fact_row_id:
            raise ValueError("基线证据入口必须绑定同一事实行")
        if self.observation.row_id != self.fact_row_id:
            raise ValueError("基线证据入口必须绑定原始观察")
        if self.source_row_id != self.observation.source_row_id:
            raise ValueError("基线证据来源行必须与原始观察一致")
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
    def original_observation(self) -> BaselineObservation:
        return self.observation


BaselineEvidence = BaselineEvidenceLink
BaselineEvidenceReference = BaselineEvidenceLink


# URL and state fields intentionally use canonical names internally while
# accepting concise aliases at API boundaries.
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
    "cohort": "cohort_ids",
    "cohorts": "cohort_ids",
    "cohort_ids": "cohort_ids",
    "group": "group_ids",
    "groups": "group_ids",
    "group_ids": "group_ids",
    "region": "region_ids",
    "regions": "region_ids",
    "region_ids": "region_ids",
    "population": "analysis_populations",
    "populations": "analysis_populations",
    "analysis_population": "analysis_populations",
    "analysis_populations": "analysis_populations",
    "domain": "variable_domains",
    "domains": "variable_domains",
    "variable_domain": "variable_domains",
    "variable_domains": "variable_domains",
    "concept": "standardized_concepts",
    "concepts": "standardized_concepts",
    "standardized_concept": "standardized_concepts",
    "standardized_concepts": "standardized_concepts",
    "statistic": "statistic_forms",
    "statistics": "statistic_forms",
    "statistic_form": "statistic_forms",
    "statistic_forms": "statistic_forms",
    "scale": "scales",
    "scales": "scales",
    "unit": "units",
    "units": "units",
    "disclosure": "disclosure_states",
    "disclosures": "disclosure_states",
    "disclosure_state": "disclosure_states",
    "disclosure_states": "disclosure_states",
    "focus": "evidence_focus_id",
    "focus_id": "evidence_focus_id",
    "evidence_focus_id": "evidence_focus_id",
}

_PAGE_SELECTION_FIELDS = frozenset({"product_ids", "target_ids", "trial_ids", "region_ids"})
_MODULE_SELECTION_FIELDS = frozenset(
    {
        "cohort_ids",
        "group_ids",
        "analysis_populations",
        "variable_domains",
        "standardized_concepts",
        "statistic_forms",
        "scales",
        "units",
        "disclosure_states",
        "evidence_focus_id",
    }
)


def _validated_selection(
    value: BaselineSelectionState | Mapping[str, Any],
) -> BaselineSelectionState:
    raw: object
    if isinstance(value, BaselineSelectionState):
        raw = value.model_dump(mode="python", warnings="none")
    elif isinstance(value, Mapping):
        raw = dict(value)
    else:
        raise BaselineViewError("基线选择状态必须是 BaselineSelectionState 或映射")
    try:
        return BaselineSelectionState.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise BaselineViewError(f"选择状态重新校验失败：{error}") from error


def _selection_with_mapping(
    current: BaselineSelectionState,
    value: BaselineSelectionState | Mapping[str, Any],
) -> BaselineSelectionState:
    if isinstance(value, BaselineSelectionState):
        return _validated_selection(value)
    if not isinstance(value, Mapping):
        raise BaselineViewError("基线选择状态必须是 BaselineSelectionState 或映射")
    # Validate unknown fields before merging so a typo cannot silently leave
    # the previous filter active.
    try:
        _validated_selection(value)
    except BaselineViewError:
        raise
    merged = current.model_dump(mode="python")
    for key, item in value.items():
        canonical = _SELECTION_ALIASES.get(str(key), str(key))
        merged[canonical] = item
    return _validated_selection(merged)


def _panel_material(fact: BaselineObservation) -> tuple[str, ...]:
    key = fact.compatibility_key
    # Category labels identify rows within one proportion panel, not separate
    # scientific panels. Bounded bins stay in the full key: without an explicit
    # binning scheme it is safer to split than to imply a re-binning operation.
    category_token = _token(key.category_level)
    bin_label_token = _token(key.bin_label)
    if (
        fact.data_type is BaselineDataType.CATEGORICAL
        and fact.statistic_form is BaselineStatisticForm.PROPORTION
        and key.bin_lower is None
        and key.bin_upper is None
    ):
        category_token = "category"
        bin_label_token = "category"
    return (
        key.variable_domain.value,
        key.data_type.value,
        key.standardized_concept,
        _token(key.scale),
        _token(key.scale_version),
        _token(key.direction),
        _token(key.theoretical_range),
        key.statistic_form.value,
        _token(key.unit),
        category_token,
        bin_label_token,
        _token(key.bin_lower),
        _token(key.bin_upper),
        key.baseline_definition,
        key.baseline_timepoint,
        key.compatibility_rule,
        fact.analysis_population,
        _token(fact.denominator_role),
    )


def _panel_bucket_id(fact: BaselineObservation) -> str:
    return stable_id("baseline-chart-bucket", *_panel_material(fact))


def _concept_priority(fact: BaselineObservation) -> tuple[int, str]:
    concept = fact.standardized_concept.casefold()
    if concept in _SAMPLE_SIZE_CONCEPTS:
        return (0, concept)
    if concept in _AGE_CONCEPTS:
        return (1, concept)
    if concept in _SEX_CONCEPTS:
        return (2, concept)
    if concept in _SEVERITY_ANCHOR_CONCEPTS:
        return (3, concept)
    if fact.variable_domain is BaselineVariableDomain.DEMOGRAPHICS:
        return (10, concept)
    if fact.variable_domain is BaselineVariableDomain.DISEASE_CONTEXT:
        return (20, concept)
    return (30, concept)


def _fact_sort_key(fact: BaselineObservation) -> tuple[object, ...]:
    priority, concept = _concept_priority(fact)
    return (
        priority,
        concept,
        fact.variable_domain.value,
        _STATISTIC_ORDER[fact.statistic_form],
        _panel_bucket_id(fact),
        fact.product_id.casefold(),
        fact.product_id,
        fact.trial_id.casefold(),
        fact.trial_id,
        fact.cohort_id.casefold(),
        fact.cohort_id,
        fact.group_id.casefold(),
        fact.group_id,
        fact.analysis_population.casefold(),
        fact.analysis_population,
        (fact.category_level or fact.bin_label or "").casefold(),
        fact.row_id,
    )


def _chart_eligibility(fact: BaselineObservation) -> tuple[bool, str | None]:
    if fact.disclosure_state not in _DRAWABLE_DISCLOSURES:
        return False, disclosure_state_label_zh(fact.disclosure_state)
    if fact.statistic_form in {
        BaselineStatisticForm.QUARTILES,
        BaselineStatisticForm.RANGE,
    } or (
        fact.statistic_form is BaselineStatisticForm.OTHER
        and fact.range_lower is not None
        and fact.range_upper is not None
    ):
        if fact.range_lower is None or fact.range_upper is None:
            return False, "来源未提供完整区间，保留原文统计形式"
        return True, None
    if fact.statistic_form is BaselineStatisticForm.PROPORTION:
        if fact.data_type is not BaselineDataType.CATEGORICAL:
            return False, "比例统计的数据类型不兼容，不生成图形坐标"
        if fact.value is None:
            return False, "来源未提供比例数值，保留原文统计形式"
        if fact.denominator is None:
            return False, "缺少明确分母，不生成比例图"
        if fact.category_level is None and fact.bin_label is None:
            return False, "缺少来源分类水平，不生成比例图"
        return True, None
    if (
        fact.data_type is BaselineDataType.CATEGORICAL
        and fact.category_level is None
        and fact.bin_label is None
    ):
        return False, "缺少来源分类水平，不生成分类图"
    if fact.value is None:
        return False, "来源未提供可绘制中心值，保留原文统计形式"
    return True, None


def _table_row(fact: BaselineObservation, panel_bucket_id: str) -> BaselineTableRow:
    drawable, reason = _chart_eligibility(fact)
    payload = fact.model_dump(mode="python")
    payload.update(
        {
            "fact": fact,
            "value_label": _value_label(
                value=fact.value,
                unit=fact.unit,
                range_lower=fact.range_lower,
                range_upper=fact.range_upper,
            ),
            "chart_reason_zh": reason,
            "is_chart_drawable": drawable,
            "panel_bucket_id": panel_bucket_id,
            "compatibility_bucket_id": fact.compatibility_bucket_id,
        }
    )
    try:
        return BaselineTableRow.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as error:
        raise BaselineViewError(f"基线表格投影失败：{error}") from error


def _auto_difference_labels(
    fact: BaselineObservation,
    same_concept: Sequence[BaselineObservation],
) -> tuple[str, ...]:
    labels: list[str] = []
    key = fact.compatibility_key
    for other in same_concept:
        if other.row_id == fact.row_id:
            continue
        other_key = other.compatibility_key
        if key.scale_version != other_key.scale_version:
            labels.append("量表版本不同，拆分小多图")
        elif key.scale != other_key.scale:
            labels.append("量表或仪器不同，拆分小多图")
        if key.direction != other_key.direction:
            labels.append("方向不同，拆分小多图")
        if key.theoretical_range != other_key.theoretical_range:
            labels.append("理论范围不同，拆分小多图")
        if key.unit != other_key.unit:
            labels.append("单位不同，拆分小多图")
        if key.baseline_definition != other_key.baseline_definition:
            labels.append("基线定义不同，拆分小多图")
        if key.baseline_timepoint != other_key.baseline_timepoint:
            labels.append("基线时间不同，拆分小多图")
        if key.statistic_form != other_key.statistic_form:
            labels.append("统计形式不同，拆分小多图")
        if fact.analysis_population != other.analysis_population:
            labels.append("基线分析人群不同，拆分小多图")
        if fact.denominator_role != other.denominator_role:
            labels.append("分母角色不同，拆分小多图")
        if (
            key.bin_lower != other_key.bin_lower or key.bin_upper != other_key.bin_upper
        ) and fact.data_type is BaselineDataType.CATEGORICAL:
            labels.append("分类分箱边界不同，拆分小多图")
    return tuple(dict.fromkeys(labels))


def _panel_chart_type(
    facts: Sequence[BaselineObservation],
    drawable_rows: Sequence[BaselineTableRow],
) -> BaselineChartType:
    if not drawable_rows:
        return BaselineChartType.DISCLOSURE
    first = facts[0]
    if (
        first.data_type is BaselineDataType.CATEGORICAL
        and first.statistic_form is BaselineStatisticForm.PROPORTION
    ):
        return BaselineChartType.PROPORTION_BAR
    if first.variable_domain is BaselineVariableDomain.BASELINE_SEVERITY:
        return BaselineChartType.SMALL_MULTIPLE
    if (
        first.statistic_form in {
            BaselineStatisticForm.QUARTILES,
            BaselineStatisticForm.RANGE,
        }
        or (
            first.statistic_form is BaselineStatisticForm.OTHER
            and first.range_lower is not None
            and first.range_upper is not None
        )
    ):
        return BaselineChartType.INTERVAL
    return BaselineChartType.POINT


def _build_panels(
    facts: Sequence[BaselineObservation],
    table_by_id: Mapping[str, BaselineTableRow],
) -> tuple[BaselineChartPanel, ...]:
    grouped: dict[str, list[BaselineObservation]] = {}
    for fact in facts:
        grouped.setdefault(_panel_bucket_id(fact), []).append(fact)
    panels: list[BaselineChartPanel] = []
    for bucket_id, bucket_facts in grouped.items():
        ordered_facts = tuple(sorted(bucket_facts, key=_fact_sort_key))
        rows = tuple(table_by_id[fact.row_id] for fact in ordered_facts)
        drawable_rows = tuple(row for row in rows if row.is_chart_drawable)
        status_rows = tuple(row for row in rows if not row.is_chart_drawable)
        first = ordered_facts[0]
        labels: list[str] = []
        for fact in ordered_facts:
            same_concept = tuple(
                other
                for other in facts
                if other.standardized_concept == fact.standardized_concept
            )
            for label in (
                *fact.difference_labels_zh,
                *_auto_difference_labels(fact, same_concept),
            ):
                if label not in labels:
                    labels.append(label)
        chart_type = _panel_chart_type(ordered_facts, drawable_rows)
        variable_label = _concept_label(first.standardized_concept, first.source_name)
        panel = BaselineChartPanel(
            panel_id=bucket_id,
            variable_domain=first.variable_domain,
            standardized_concept=first.standardized_concept,
            variable_label_zh=variable_label,
            statistic_form=first.statistic_form,
            data_type=first.data_type,
            chart_type=chart_type,
            compatibility_bucket_id=bucket_id,
            analysis_population=first.analysis_population,
            denominator_role=first.denominator_role,
            drawable_rows=drawable_rows,
            status_rows=status_rows,
            difference_labels_zh=tuple(labels),
            is_mixed_compatibility=False,
            is_stacked=False,
            has_axes=bool(drawable_rows),
            title_zh=f"{variable_label}（{_statistic_label(first.statistic_form)}）",
            description_zh=(
                "图表仅展示满足原始统计形式且有明确数值的事实；完整来源事实见下表。"
                if drawable_rows
                else "当前事实没有可绘制数值，保留来源披露状态并不生成坐标轴。"
            ),
        )
        panels.append(panel)
    return tuple(panels)


def _filter_match(fact: BaselineObservation, selection: BaselineSelectionState) -> bool:
    # Target and region are not fields on BaselineObservation. An active value
    # must therefore produce no rows rather than silently matching everything.
    if selection.target_ids or selection.region_ids:
        return False
    checks: tuple[tuple[tuple[Any, ...], Any], ...] = (
        (selection.product_ids, fact.product_id),
        (selection.trial_ids, fact.trial_id),
        (selection.cohort_ids, fact.cohort_id),
        (selection.group_ids, fact.group_id),
        (selection.analysis_populations, fact.analysis_population),
        (selection.variable_domains, fact.variable_domain),
        (selection.standardized_concepts, fact.standardized_concept),
        (selection.statistic_forms, fact.statistic_form),
        (selection.scales, fact.scale),
        (selection.units, fact.unit),
        (selection.disclosure_states, fact.disclosure_state),
    )
    return all(not selected or current in selected for selected, current in checks)


def _filter_label(
    dimension: str,
    value: str,
    *,
    display_value: str | None = None,
) -> str:
    labels = {
        "product": "产品",
        "trial": "试验",
        "cohort": "队列",
        "group": "组别",
        "region": "地区",
        "analysis_population": "基线分析人群",
        "variable_domain": "变量域",
        "standardized_concept": "变量",
        "statistic_form": "统计形式",
        "scale": "量表/仪器",
        "unit": "单位",
        "disclosure_state": "披露状态",
    }
    if dimension == "variable_domain":
        try:
            return f"{labels[dimension]}：{_domain_label(BaselineVariableDomain(value))}"
        except ValueError:
            return f"{labels[dimension]}：{value}"
    if dimension == "standardized_concept":
        return f"{labels[dimension]}：{_concept_label(value, display_value)}"
    if dimension == "statistic_form":
        try:
            return f"{labels[dimension]}：{_statistic_label(BaselineStatisticForm(value))}"
        except ValueError:
            return f"{labels[dimension]}：{value}"
    if dimension == "disclosure_state":
        try:
            return f"{labels[dimension]}：{disclosure_state_label_zh(FactDisclosureState(value))}"
        except ValueError:
            return f"{labels[dimension]}：{value}"
    return f"{labels.get(dimension, '筛选')}：{value}"


def _build_filter_surface(
    facts: Sequence[BaselineObservation],
) -> tuple[dict[str, BaselineFilterApplicability], tuple[BaselineFilterOption, ...]]:
    supported: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("product", tuple(sorted({fact.product_id for fact in facts}))),
        ("trial", tuple(sorted({fact.trial_id for fact in facts}))),
        ("cohort", tuple(sorted({fact.cohort_id for fact in facts}))),
        ("group", tuple(sorted({fact.group_id for fact in facts}))),
        (
            "analysis_population",
            tuple(sorted({fact.analysis_population for fact in facts})),
        ),
        (
            "variable_domain",
            tuple(sorted({fact.variable_domain.value for fact in facts})),
        ),
        (
            "standardized_concept",
            tuple(sorted({fact.standardized_concept for fact in facts})),
        ),
        (
            "statistic_form",
            tuple(sorted({fact.statistic_form.value for fact in facts})),
        ),
        ("scale", tuple(sorted({fact.scale for fact in facts if fact.scale is not None}))),
        ("unit", tuple(sorted({fact.unit for fact in facts if fact.unit is not None}))),
        (
            "disclosure_state",
            tuple(sorted({fact.disclosure_state.value for fact in facts})),
        ),
    )
    applicability: dict[str, BaselineFilterApplicability] = {}
    options: list[BaselineFilterOption] = []
    for dimension, values in supported:
        enabled = bool(values)
        applicability[dimension] = BaselineFilterApplicability(
            dimension=dimension,
            enabled=enabled,
            reason_zh=None if enabled else "当前基线事实未提供该筛选维度",
            available_values=values,
        )
        for value in values:
            count = 0
            for fact in facts:
                current: object = {
                    "product": fact.product_id,
                    "trial": fact.trial_id,
                    "cohort": fact.cohort_id,
                    "group": fact.group_id,
                    "analysis_population": fact.analysis_population,
                    "variable_domain": fact.variable_domain.value,
                    "standardized_concept": fact.standardized_concept,
                    "statistic_form": fact.statistic_form.value,
                    "scale": fact.scale,
                    "unit": fact.unit,
                    "disclosure_state": fact.disclosure_state.value,
                }[dimension]
                if current == value:
                    count += 1
            options.append(
                BaselineFilterOption(
                    dimension=dimension,
                    value=value,
                    label_zh=_filter_label(
                        dimension,
                        value,
                        display_value=next(
                            (
                                fact.source_name
                                for fact in facts
                                if dimension == "standardized_concept"
                                and fact.standardized_concept == value
                            ),
                            None,
                        ),
                    ),
                    fact_count=count,
                )
            )
    applicability["target"] = BaselineFilterApplicability(
        dimension="target",
        enabled=False,
        reason_zh="当前基线事实不适用靶点筛选维度",
    )
    applicability["region"] = BaselineFilterApplicability(
        dimension="region",
        enabled=False,
        reason_zh="当前基线事实不适用地区筛选维度",
    )
    # Canonical user-facing order is independent of fact insertion order.
    dimension_order = {
        "product": 0,
        "target": 1,
        "trial": 2,
        "cohort": 3,
        "group": 4,
        "region": 5,
        "analysis_population": 6,
        "variable_domain": 7,
        "standardized_concept": 8,
        "statistic_form": 9,
        "scale": 10,
        "unit": 11,
        "disclosure_state": 12,
    }
    options.sort(
        key=lambda option: (
            dimension_order[option.dimension],
            option.value.casefold(),
            option.value,
        )
    )
    return applicability, tuple(options)

def _evidence_link(row: BaselineTableRow) -> BaselineEvidenceLink:
    return BaselineEvidenceLink(
        row_id=row.row_id,
        fact_row_id=row.row_id,
        source_row_id=row.source_row_id,
        source_version_id=row.source_version_id,
        source_locator=row.source_locator,
        label_zh=(
            f"{_domain_label(row.variable_domain)}："
            f"{_concept_label(row.standardized_concept, row.source_name)}"
        ),
        href=row.source_locator.url,
        observation=row.fact,
    )


def _assemble_view_state(
    facts: Sequence[BaselineObservation],
    *,
    selected_facts: Sequence[BaselineObservation],
    selection: BaselineSelectionState,
    default_selection: BaselineSelectionState,
    route: str,
) -> BaselineViewState:
    ordered_facts = tuple(sorted(facts, key=_fact_sort_key))
    ordered_selected = tuple(sorted(selected_facts, key=_fact_sort_key))
    bucket_by_id = {fact.row_id: _panel_bucket_id(fact) for fact in ordered_selected}
    table_rows = tuple(
        _table_row(fact, bucket_by_id[fact.row_id]) for fact in ordered_selected
    )
    table_by_id = {row.row_id: row for row in table_rows}
    panels = _build_panels(ordered_selected, table_by_id)
    links = tuple(_evidence_link(row) for row in table_rows)
    links_by_id = {link.row_id: link for link in links}
    focus_row = None
    if selection.evidence_focus_id is not None:
        focus_row = table_by_id.get(selection.evidence_focus_id)
        if focus_row is None:
            raise BaselineViewError("证据焦点不在当前筛选结果中")
    applicability, options = _build_filter_surface(ordered_facts)
    normalized_route = _text(route, field_name="基线 URL 路由")
    try:
        return BaselineViewState(
            selection=selection,
            default_selection=default_selection,
            facts=ordered_facts,
            selected_facts=ordered_selected,
            chart_panels=panels,
            complete_table=table_rows,
            table_row_ids=tuple(row.row_id for row in table_rows),
            filter_applicability=applicability,
            filter_options=options,
            evidence_links=links,
            evidence_links_by_row_id=links_by_id,
            evidence_focus_row_id=None if focus_row is None else focus_row.row_id,
            evidence_focus=focus_row,
            empty_state=BaselineEmptyState(
                is_empty=not table_rows,
                message_zh=(
                    "当前筛选范围暂无基线事实"
                    if not table_rows
                    else "当前筛选范围包含基线事实"
                ),
                row_count=len(table_rows),
            ),
            url_state=selection.to_url_params(),
            url=selection.to_url(normalized_route),
            route=normalized_route,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise BaselineViewError(f"基线同步视图组装失败：{error}") from error


class BaselineViewState(BaseModel):
    """由同一事实源确定性重建图、完整表、证据和 URL 状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    selection: BaselineSelectionState
    default_selection: BaselineSelectionState
    facts: tuple[BaselineObservation, ...] = ()
    selected_facts: tuple[BaselineObservation, ...] = ()
    chart_panels: tuple[BaselineChartPanel, ...] = ()
    complete_table: tuple[BaselineTableRow, ...] = ()
    table_row_ids: tuple[str, ...] = ()
    filter_applicability: Mapping[str, BaselineFilterApplicability] = Field(
        default_factory=dict
    )
    filter_options: tuple[BaselineFilterOption, ...] = ()
    evidence_links: tuple[BaselineEvidenceLink, ...] = ()
    evidence_links_by_row_id: Mapping[str, BaselineEvidenceLink] = Field(
        default_factory=dict
    )
    evidence_focus_row_id: str | None = None
    evidence_focus: BaselineTableRow | None = None
    empty_state: BaselineEmptyState
    url_state: Mapping[str, str] = Field(default_factory=dict)
    url: str
    route: str = "/b/baseline"

    @field_validator("url", "route")
    @classmethod
    def _state_url(cls, value: str) -> str:
        return _text(value, field_name="基线 URL")

    @field_validator(
        "filter_applicability",
        "evidence_links_by_row_id",
        "url_state",
        mode="after",
    )
    @classmethod
    def _freeze_mappings(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return MappingProxyType(dict(value))

    @field_serializer(
        "filter_applicability",
        "evidence_links_by_row_id",
        "url_state",
    )
    def _serialize_mappings(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return dict(value)

    @model_validator(mode="after")
    def _state_integrity(self) -> Self:
        fact_ids = tuple(fact.row_id for fact in self.facts)
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("基线视图原始观察不得重复")
        selected_ids = tuple(fact.row_id for fact in self.selected_facts)
        if not set(selected_ids) <= set(fact_ids):
            raise ValueError("基线筛选结果必须来自原始观察集合")
        table_ids = tuple(row.row_id for row in self.complete_table)
        if table_ids != self.table_row_ids:
            raise ValueError("基线完整表行标识不一致")
        if table_ids != selected_ids:
            raise ValueError("完整表必须覆盖全部筛选后事实且不丢行")
        if len(set(table_ids)) != len(table_ids):
            raise ValueError("基线完整表行标识不得重复")
        panel_ids: list[str] = []
        panel_row_ids: list[str] = []
        for panel in self.chart_panels:
            if panel.compatibility_bucket_id in panel_ids:
                raise ValueError("基线图表兼容桶不得重复")
            panel_ids.append(panel.compatibility_bucket_id)
            panel_row_ids.extend(row.row_id for row in panel.rows)
        if set(panel_row_ids) != set(table_ids):
            raise ValueError("图表与完整表必须引用同一筛选后事实集合")
        link_ids = tuple(link.row_id for link in self.evidence_links)
        if link_ids != table_ids:
            raise ValueError("基线证据必须覆盖完整表全部事实")
        if tuple(self.evidence_links_by_row_id) != table_ids:
            raise ValueError("基线证据索引必须保持完整表顺序")
        if any(self.evidence_links_by_row_id[row_id].row_id != row_id for row_id in table_ids):
            raise ValueError("基线证据索引行标识不一致")
        if self.evidence_focus_row_id != (
            None if self.evidence_focus is None else self.evidence_focus.row_id
        ):
            raise ValueError("基线证据焦点行标识不一致")
        if self.evidence_focus is not None and self.evidence_focus.row_id not in table_ids:
            raise ValueError("基线证据焦点必须来自完整表")
        if self.empty_state.is_empty != (not table_ids):
            raise ValueError("基线空状态必须与筛选后事实集合一致")
        if self.url_state != self.selection.to_url_params():
            raise ValueError("基线 URL 状态必须与选择状态一致")
        if self.url != self.selection.to_url(self.route):
            raise ValueError("基线 URL 必须与选择状态和路由一致")
        return self

    @property
    def selection_state(self) -> BaselineSelectionState:
        return self.selection

    @property
    def baseline_selection(self) -> BaselineSelectionState:
        return self.selection

    @property
    def rows(self) -> tuple[BaselineTableRow, ...]:
        return self.complete_table

    @property
    def table(self) -> tuple[BaselineTableRow, ...]:
        return self.complete_table

    @property
    def full_table(self) -> tuple[BaselineTableRow, ...]:
        return self.complete_table

    @property
    def table_rows(self) -> tuple[BaselineTableRow, ...]:
        return self.complete_table

    @property
    def panels(self) -> tuple[BaselineChartPanel, ...]:
        return self.chart_panels

    @property
    def charts(self) -> tuple[BaselineChartPanel, ...]:
        return self.chart_panels

    @property
    def chart(self) -> tuple[BaselineChartPanel, ...]:
        return self.chart_panels

    @property
    def evidence(self) -> tuple[BaselineEvidenceLink, ...]:
        return self.evidence_links

    @property
    def evidence_references(self) -> tuple[BaselineEvidenceLink, ...]:
        return self.evidence_links

    @property
    def focused_row(self) -> BaselineTableRow | None:
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
    def available_facts(self) -> tuple[BaselineObservation, ...]:
        return self.facts

    @property
    def source_facts(self) -> tuple[BaselineObservation, ...]:
        return self.facts

    def assert_synchronized(self) -> Self:
        try:
            validated = type(self).model_validate(
                self.model_dump(mode="python", warnings="none")
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
        except (TypeError, ValueError, ValidationError) as error:
            raise BaselineViewError(f"基线同步视图重新校验失败：{error}") from error
        if rebuilt.model_dump(mode="python", warnings="none") != validated.model_dump(
            mode="python", warnings="none"
        ):
            raise BaselineViewError("基线同步视图与原始事实重新计算结果不一致")
        return self

    def with_selection(
        self,
        selection: BaselineSelectionState | Mapping[str, Any],
    ) -> BaselineViewState:
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

    def with_evidence_focus(self, row_id: str | None) -> BaselineViewState:
        if row_id is not None:
            normalized = _text(row_id, field_name="证据焦点标识")
            if normalized not in self.table_row_ids:
                raise BaselineViewError("证据焦点必须来自当前完整表")
            row_id = normalized
        return self.with_selection(self.selection.model_copy(update={"evidence_focus_id": row_id}))

    focus_evidence = with_evidence_focus
    set_evidence_focus = with_evidence_focus

    def reset(
        self,
        scope: Literal["page", "module", "full"] | str | None = None,
    ) -> BaselineViewState:
        normalized_scope = (
            "full"
            if scope is None
            else _text(scope, field_name="基线重置范围").casefold()
        )
        if normalized_scope in {"full", "all", "view"}:
            parsed = self.default_selection
        elif normalized_scope == "page":
            values = self.selection.model_dump(mode="python")
            for field_name in _PAGE_SELECTION_FIELDS:
                values[field_name] = getattr(self.default_selection, field_name)
            parsed = _validated_selection(values)
        elif normalized_scope == "module":
            values = self.selection.model_dump(mode="python")
            for field_name in _MODULE_SELECTION_FIELDS:
                values[field_name] = getattr(self.default_selection, field_name)
            parsed = _validated_selection(values)
        else:
            raise BaselineViewError("基线重置范围必须是 page、module 或 full")
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


BaselineSynchronizedView = BaselineViewState
BaselinePageState = BaselineViewState
BaselineInteractionState = BaselineViewState


def build_baseline_view_state(
    observations: Sequence[BaselineObservation | Mapping[str, Any]]
    | Iterable[BaselineObservation | Mapping[str, Any]],
    selection: BaselineSelectionState | Mapping[str, Any] | None = None,
    *,
    route: str = "/b/baseline",
) -> BaselineViewState:
    """从 BaselineObservation 单一事实源构建同步基线视图。"""

    try:
        raw_values = tuple(observations)
    except TypeError as error:
        raise BaselineViewError("基线观察必须是可迭代事实集合") from error
    facts = tuple(_validated_observation(value) for value in raw_values)
    fact_ids = tuple(fact.row_id for fact in facts)
    if len(set(fact_ids)) != len(fact_ids):
        raise BaselineViewError("重复 row_id 或重复事实，拒绝构建基线视图")
    ordered_facts = tuple(sorted(facts, key=_fact_sort_key))
    default_selection = BaselineSelectionState()
    parsed = default_selection if selection is None else _validated_selection(selection)
    selected = tuple(fact for fact in ordered_facts if _filter_match(fact, parsed))
    return _assemble_view_state(
        ordered_facts,
        selected_facts=selected,
        selection=parsed,
        default_selection=default_selection,
        route=route,
    )


build_baseline_view = build_baseline_view_state
build_baseline_page_state = build_baseline_view_state
build_baseline_synchronized_view = build_baseline_view_state
build_baseline_interaction_state = build_baseline_view_state
build_baseline_state = build_baseline_view_state


def apply_baseline_selection(
    value: BaselineViewState,
    selection: BaselineSelectionState | Mapping[str, Any],
) -> BaselineViewState:
    if not isinstance(value, BaselineViewState):
        raise BaselineViewError("应用基线选择必须传入 BaselineViewState")
    return value.with_selection(selection)


update_baseline_selection = apply_baseline_selection
select_baseline_view = apply_baseline_selection
update_baseline_view = apply_baseline_selection


def reset_baseline_selection(
    value: BaselineViewState,
    scope: Literal["page", "module", "full"] | str | None = None,
) -> BaselineViewState:
    if not isinstance(value, BaselineViewState):
        raise BaselineViewError("重置基线选择必须传入 BaselineViewState")
    return value.reset(scope)


reset_baseline_view = reset_baseline_selection
reset_baseline_view_state = reset_baseline_selection


def selection_to_url(
    selection: BaselineSelectionState | Mapping[str, Any],
    route: str = "/b/baseline",
) -> str:
    return _validated_selection(selection).to_url(route)


def selection_from_url(url: str) -> BaselineSelectionState:
    return BaselineSelectionState.from_url(url)


parse_baseline_url_state = selection_from_url


__all__ = [
    "BaselineChartPanel",
    "BaselineChartRow",
    "BaselineChartRowStatus",
    "BaselineChartType",
    "BaselineChartView",
    "BaselineEmptyState",
    "BaselineEvidence",
    "BaselineEvidenceLink",
    "BaselineEvidenceReference",
    "BaselineFactTableRow",
    "BaselineFilterApplicability",
    "BaselineFilterOption",
    "BaselineInteractionState",
    "BaselinePageState",
    "BaselinePanel",
    "BaselineSelection",
    "BaselineSelectionState",
    "BaselineSynchronizedView",
    "BaselineTableRow",
    "BaselineViewError",
    "BaselineViewSelection",
    "BaselineViewState",
    "apply_baseline_selection",
    "build_baseline_interaction_state",
    "build_baseline_page_state",
    "build_baseline_state",
    "build_baseline_synchronized_view",
    "build_baseline_view",
    "build_baseline_view_state",
    "disclosure_state_label_zh",
    "parse_baseline_url_state",
    "reset_baseline_selection",
    "reset_baseline_view",
    "reset_baseline_view_state",
    "selection_from_url",
    "selection_to_url",
    "select_baseline_view",
    "update_baseline_selection",
    "update_baseline_view",
]
