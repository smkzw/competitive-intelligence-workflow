"""B 类基线观察事实合同与 GateEvidenceBinding 转换。

本模块只保存基线事实、科学兼容键和到现有 GateSpec 输入的严格映射；
门槛适用性、逐组完整性和阻断决定仍由 ``ci_workflow.gates`` 负责。
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import (
    ConflictDisposition,
    DisclosureMaturity,
    FactDomain,
    GateEvidenceBinding,
    ObservationKind,
    SourceRole,
)

NumericValue = StrictInt | StrictFloat


class BaselineObservationError(ValueError):
    """基线观察不满足强类型或 Gate 绑定合同。"""


class BaselineVariableDomain(StrEnum):
    """B 类基线变量的封闭科学域。"""

    DEMOGRAPHICS = "demographics"
    DISEASE_CONTEXT = "disease_context"
    BASELINE_SEVERITY = "baseline_severity"


class BaselineDataType(StrEnum):
    """基线观察的计量数据类型。"""

    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    COUNT = "count"


class BaselineStatisticForm(StrEnum):
    """基线事实的来源统计形式；各形式不互相推导。"""

    SAMPLE_SIZE = "sample_size"
    MEAN = "mean"
    STANDARD_DEVIATION = "standard_deviation"
    MEDIAN = "median"
    QUARTILES = "quartiles"
    RANGE = "range"
    COUNT = "count"
    PROPORTION = "proportion"
    OTHER = "other"


_MISSING_DISCLOSURE_STATES = frozenset(
    {
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    }
)
_REPORTED_DISCLOSURE_STATES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)

_BASELINE_GATE_UNIT_IDS = frozenset(
    {
        "b_baseline_sample_size",
        "b_baseline_age",
        "b_baseline_sex",
        "b_baseline_severity_anchor",
    }
)

# B-v1 的四项关键事实各有自己的科学识别，不把一个任意基线变量冒充为
# 另一项关键条件。允许少量稳定规范概念别名，但不按来源显示名猜测。
_SAMPLE_SIZE_CONCEPTS = frozenset(
    {"baseline_sample_size", "sample_size", "baseline_n", "n"}
)
_AGE_CONCEPTS = frozenset({"age", "baseline_age", "age_at_baseline"})
_SEX_CONCEPTS = frozenset({"sex", "gender", "baseline_sex", "baseline_gender"})


def _text(value: str, *, field_name: str = "基线合同文本") -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _raw_text(value: str, *, field_name: str = "基线原文") -> str:
    if not value.strip():
        raise ValueError(f"{field_name}不能为空")
    return value


def _optional_text(value: str | None, *, field_name: str = "基线合同文本") -> str | None:
    return None if value is None else _text(value, field_name=field_name)


def _as_token(value: object | None) -> str:
    """将科学身份维度编码为稳定、非空的身份材料。"""

    if value is None:
        return "<none>"
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("基线身份数值必须是有限数值")
        return repr(value)
    return str(value)


def _finite_numeric(value: NumericValue | None, *, field_name: str) -> NumericValue | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}必须是数值")
    if not math.isfinite(value):
        raise ValueError(f"{field_name}必须是有限数值")
    return value


def _numeric_fields(observation: BaselineObservation) -> tuple[object | None, ...]:
    return (
        observation.value,
        observation.dispersion,
        observation.range_lower,
        observation.range_upper,
        observation.bin_lower,
        observation.bin_upper,
        observation.numerator,
        observation.denominator,
    )


class BaselineCompatibilityKey(BaseModel):
    """只由科学可比字段组成的基线比较键。

    来源名称、原始定义、来源版本、定位、审阅状态、事实值、分母和展示
    差异标签均不在键内；这些信息必须保留在 ``BaselineObservation`` 中。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    variable_domain: BaselineVariableDomain
    data_type: BaselineDataType
    standardized_concept: str
    scale: str | None = None
    scale_version: str | None = None
    direction: str | None = None
    theoretical_range: str | None = None
    statistic_form: BaselineStatisticForm
    unit: str | None = None
    category_level: str | None = None
    bin_label: str | None = None
    bin_lower: NumericValue | None = None
    bin_upper: NumericValue | None = None
    baseline_definition: str
    baseline_timepoint: str
    compatibility_rule: str

    @field_validator(
        "standardized_concept",
        "baseline_definition",
        "baseline_timepoint",
        "compatibility_rule",
    )
    @classmethod
    def _key_required_text(cls, value: str) -> str:
        return _text(value, field_name="基线兼容键字段")

    @field_validator(
        "scale",
        "scale_version",
        "direction",
        "theoretical_range",
        "unit",
        "category_level",
        "bin_label",
    )
    @classmethod
    def _key_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="基线兼容键字段")

    @field_validator("bin_lower", "bin_upper")
    @classmethod
    def _key_numeric(cls, value: NumericValue | None) -> NumericValue | None:
        return _finite_numeric(value, field_name="基线兼容键分箱边界")

    @model_validator(mode="after")
    def _key_bin_bounds_are_closed(self) -> Self:
        if (self.bin_lower is None) != (self.bin_upper is None):
            raise ValueError("基线兼容键分箱边界必须同时提供")
        if (
            self.bin_lower is not None
            and self.bin_upper is not None
            and self.bin_lower > self.bin_upper
        ):
            raise ValueError("基线兼容键分箱下界不得高于上界")
        if self.scale_version is not None and self.scale is None:
            raise ValueError("基线兼容键量表版本必须绑定量表或仪器")
        return self

    @property
    def identity_key(self) -> str:
        """科学兼容桶的稳定标识，不含来源或审阅元数据。"""

        return stable_id(
            "baseline-compatibility",
            self.variable_domain.value,
            self.data_type.value,
            self.standardized_concept,
            _as_token(self.scale),
            _as_token(self.scale_version),
            _as_token(self.direction),
            _as_token(self.theoretical_range),
            self.statistic_form.value,
            _as_token(self.unit),
            _as_token(self.category_level),
            _as_token(self.bin_label),
            _as_token(self.bin_lower),
            _as_token(self.bin_upper),
            self.baseline_definition,
            self.baseline_timepoint,
            self.compatibility_rule,
        )

    @property
    def compatibility_bucket_id(self) -> str:
        return self.identity_key


class BaselineObservation(BaseModel):
    """一条产品—试验—队列—组别闭合的基线事实观察。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["1.0"] = "1.0"
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
    value: NumericValue | None = None
    raw_value: str | None = None
    unit: str | None = None
    dispersion: NumericValue | None = None
    range_lower: NumericValue | None = None
    range_upper: NumericValue | None = None
    category_level: str | None = None
    bin_label: str | None = None
    bin_lower: NumericValue | None = None
    bin_upper: NumericValue | None = None
    numerator: StrictInt | None = Field(default=None, ge=0)
    denominator: StrictInt | None = Field(default=None, gt=0)
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

    @field_validator(
        "row_id",
        "source_row_id",
        "observation_id",
        "product_id",
        "trial_id",
        "cohort_id",
        "group_id",
        "analysis_population",
        "standardized_concept",
        "baseline_definition",
        "baseline_timepoint",
        "source_version_id",
        "compatibility_rule",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _text(value)

    @field_validator("source_name", "source_definition")
    @classmethod
    def _raw_identity_text(cls, value: str) -> str:
        return _raw_text(value, field_name="基线来源原名/定义")

    @field_validator(
        "scale",
        "scale_version",
        "direction",
        "theoretical_range",
        "unit",
        "category_level",
        "bin_label",
        "denominator_role",
        "route_receipt_id",
        "applicability_predicate_id",
    )
    @classmethod
    def _optional_text_fields(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @field_validator("raw_value")
    @classmethod
    def _raw_value_text(cls, value: str | None) -> str | None:
        return None if value is None else _raw_text(value, field_name="基线来源值原文")

    @field_validator("reported_zero_text")
    @classmethod
    def _reported_zero_text(cls, value: str | None) -> str | None:
        return None if value is None else _raw_text(value, field_name="基线零值原文")

    @field_validator("difference_labels_zh", mode="before")
    @classmethod
    def _difference_labels(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = (value,) if isinstance(value, str) else tuple(value)
        normalized = tuple(_text(item, field_name="基线差异标签") for item in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("基线差异标签不得重复")
        return normalized

    @field_validator(
        "value",
        "dispersion",
        "range_lower",
        "range_upper",
        "bin_lower",
        "bin_upper",
    )
    @classmethod
    def _numeric_fields_are_finite(
        cls, value: NumericValue | None, info: Any
    ) -> NumericValue | None:
        return _finite_numeric(value, field_name=f"基线字段 {info.field_name}")

    @field_validator("schema_version")
    @classmethod
    def _schema_version_is_supported(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("基线观察只支持 schema_version=1.0")
        return value

    @model_validator(mode="after")
    def _observation_contract_is_closed(self) -> Self:
        self._validate_disclosure_contract()
        self._validate_scope_dimensions()
        self._validate_statistic_contract()
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

    def _validate_scope_dimensions(self) -> None:
        if self.scale_version is not None and self.scale is None:
            raise ValueError("量表或仪器版本必须绑定量表或仪器名称")
        if (self.bin_lower is None) != (self.bin_upper is None):
            raise ValueError("分箱边界必须同时提供")
        if (
            self.bin_lower is not None
            and self.bin_upper is not None
            and self.bin_lower > self.bin_upper
        ):
            raise ValueError("分箱下界不得高于上界")
        if (
            self.range_lower is not None
            and self.range_upper is not None
            and self.range_lower > self.range_upper
        ):
            raise ValueError("区间下界不得高于上界")
        if self.dispersion is not None and self.dispersion < 0:
            raise ValueError("离散度不得为负数")
        if (
            self.denominator is not None
            and self.numerator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("分类分子不得大于分母")
        if (
            self.statistic_form is BaselineStatisticForm.PROPORTION
            and self.category_level is None
            and self.bin_label is None
            and self.disclosure_state in _REPORTED_DISCLOSURE_STATES
        ):
            raise ValueError("分类比例必须保留分类水平或分箱标签")

    def _validate_disclosure_contract(self) -> None:
        numeric_values = _numeric_fields(self)
        if self.disclosure_state in _MISSING_DISCLOSURE_STATES:
            if any(value is not None for value in numeric_values):
                raise ValueError("未报告、未公开或路线未解决状态不得携带数值或分母")
        elif self.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
            if self.applicability_predicate_id is None:
                raise ValueError("不适用基线事实必须链接版本化适用性依据")
            if any(value is not None for value in numeric_values):
                raise ValueError("不适用基线事实不得携带数值或分母")
        elif self.disclosure_state is FactDisclosureState.REPORTED_VALUE:
            if (
                self.value is None
                and self.statistic_form
                not in {BaselineStatisticForm.QUARTILES, BaselineStatisticForm.RANGE}
            ):
                raise ValueError("已报告基线事实必须保留明确数值")
            if self.raw_value is None:
                raise ValueError("已报告基线事实必须保留来源原文值")
            if (
                self.unit is None
                and (
                    self.data_type is BaselineDataType.CONTINUOUS
                    or self.statistic_form is BaselineStatisticForm.SAMPLE_SIZE
                )
            ):
                raise ValueError("已报告连续或样本量事实必须保留单位")
        elif self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            if self.value != 0:
                raise ValueError("已报告零值的规范数值必须为零")
            if self.raw_value is None:
                raise ValueError("已报告零值必须保留来源原文值")
            if self.reported_zero_text is None:
                raise ValueError("已报告零值必须有明确零值原文证据")
            if (
                self.unit is None
                and (
                    self.data_type is BaselineDataType.CONTINUOUS
                    or self.statistic_form is BaselineStatisticForm.SAMPLE_SIZE
                )
            ):
                raise ValueError("已报告连续或样本量事实必须保留单位")

        if self.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
            if self.reported_zero_text is not None:
                raise ValueError("不适用基线事实不得携带零值原文")
        elif self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            pass
        elif self.reported_zero_text is not None:
            raise ValueError("非零值或缺失基线事实不得携带零值原文")

        if (
            self.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE
            and self.route_receipt_id is None
        ):
            raise ValueError("路线未解决基线事实必须链接路由回执")
        if self.disclosure_state is FactDisclosureState.CONFLICTING:
            if self.conflict_disposition is not ConflictDisposition.OPEN_CONFLICT_PRESERVED:
                raise ValueError("冲突基线事实必须保留开放冲突处置")
        elif self.conflict_disposition is not ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT:
            raise ValueError("非冲突基线事实必须选择已接受事实")

    def _validate_statistic_contract(self) -> None:
        reported = self.disclosure_state in _REPORTED_DISCLOSURE_STATES
        is_continuous_form = self.statistic_form in {
            BaselineStatisticForm.MEAN,
            BaselineStatisticForm.STANDARD_DEVIATION,
            BaselineStatisticForm.MEDIAN,
            BaselineStatisticForm.QUARTILES,
            BaselineStatisticForm.RANGE,
        }
        if is_continuous_form and self.data_type is not BaselineDataType.CONTINUOUS:
            raise ValueError("连续统计形式必须使用 continuous 数据类型")

        is_range_form = self.statistic_form in {
            BaselineStatisticForm.QUARTILES,
            BaselineStatisticForm.RANGE,
        }
        if is_range_form:
            if reported and (self.range_lower is None or self.range_upper is None):
                raise ValueError("四分位数或范围统计必须保存完整区间")
            if self.dispersion is not None:
                raise ValueError("区间统计不得把区间改存为离散度")
            if reported and self.value is not None:
                raise ValueError("区间统计不得另造中心值")
        elif self.range_lower is not None or self.range_upper is not None:
            if self.statistic_form is not BaselineStatisticForm.OTHER:
                raise ValueError("均值、中位数或其他固定统计形式不得携带范围字段")
            if (self.range_lower is None) != (self.range_upper is None):
                raise ValueError("其他区间统计的上下界必须同时提供")
        if self.statistic_form is BaselineStatisticForm.SAMPLE_SIZE:
            if self.data_type is not BaselineDataType.COUNT:
                raise ValueError("样本量统计必须使用 count 数据类型")
            if reported and (self.value is None or not isinstance(self.value, int)):
                raise ValueError("样本量必须是明确的整数")
            if reported and self.value is not None and self.value < 0:
                raise ValueError("样本量不得为负数")
        if (
            self.statistic_form is BaselineStatisticForm.COUNT
            and reported
            and (self.value is None or not isinstance(self.value, int))
        ):
            raise ValueError("人数或计数统计必须是明确的整数")
        if (
            self.statistic_form is BaselineStatisticForm.COUNT
            and reported
            and self.value is not None
            and self.value < 0
        ):
            raise ValueError("人数或计数不得为负数")
        if self.statistic_form is BaselineStatisticForm.PROPORTION:
            if self.data_type is not BaselineDataType.CATEGORICAL:
                raise ValueError("比例统计必须使用 categorical 数据类型")
            if reported:
                if self.denominator is None:
                    raise ValueError("分类比例必须保留明确正分母")
                if self.category_level is None and self.bin_label is None:
                    raise ValueError("分类比例必须保留分类水平或分箱标签")
                if self.value is not None:
                    upper = 100 if "%" in (self.unit or "") else 1
                    if self.value < 0 or self.value > upper:
                        raise ValueError("比例必须在来源单位允许的范围内")

        if (
            self.data_type is BaselineDataType.CATEGORICAL
            and reported
            and self.category_level is None
            and self.bin_label is None
        ):
            raise ValueError("分类观察必须保留分类水平或分箱标签")
        if self.statistic_form in {
            BaselineStatisticForm.STANDARD_DEVIATION,
            BaselineStatisticForm.SAMPLE_SIZE,
            BaselineStatisticForm.COUNT,
            BaselineStatisticForm.PROPORTION,
        } and self.dispersion is not None:
            raise ValueError("该统计形式不得携带额外离散度")

    def _derived_difference_labels(self) -> tuple[str, ...]:
        """保留来源比例并显式标记可确定复算出的差异。"""

        if (
            self.statistic_form is not BaselineStatisticForm.PROPORTION
            or self.value is None
            or self.numerator is None
            or self.denominator is None
            or self.denominator == 0
            or self.disclosure_state not in _REPORTED_DISCLOSURE_STATES
        ):
            return self.difference_labels_zh
        unit_token = (self.unit or "").casefold()
        expected = self.numerator / self.denominator
        if "%" in unit_token or "百分" in unit_token:
            expected *= 100
        if math.isclose(float(self.value), expected, rel_tol=0.0, abs_tol=1e-9):
            return self.difference_labels_zh
        label = "来源比例与分子/分母复算值不一致，保留来源值"
        if label in self.difference_labels_zh:
            return self.difference_labels_zh
        return (*self.difference_labels_zh, label)

    def _identity_parts(self) -> tuple[str, ...]:
        key = self.compatibility_key
        return (
            self.product_id,
            self.trial_id,
            self.cohort_id,
            self.group_id,
            key.variable_domain.value,
            key.data_type.value,
            key.standardized_concept,
            _as_token(key.scale),
            _as_token(key.scale_version),
            _as_token(key.direction),
            _as_token(key.theoretical_range),
            key.statistic_form.value,
            _as_token(key.unit),
            _as_token(key.category_level),
            _as_token(key.bin_label),
            _as_token(key.bin_lower),
            _as_token(key.bin_upper),
            key.baseline_definition,
            key.baseline_timepoint,
            key.compatibility_rule,
        )

    def _derived_row_id(self) -> str:
        return stable_id("baseline-row", *self._identity_parts())

    @property
    def identity_key(self) -> str:
        """稳定行身份；不含事实值、来源版本或审阅状态。"""

        return self._derived_row_id()

    @property
    def fact_version_id(self) -> str:
        """用于既有 GateEvidenceBinding 的不可变事实版本标识。"""

        return self.row_id

    @property
    def compatibility_key(self) -> BaselineCompatibilityKey:
        return BaselineCompatibilityKey(
            variable_domain=self.variable_domain,
            data_type=self.data_type,
            standardized_concept=self.standardized_concept,
            scale=self.scale,
            scale_version=self.scale_version,
            direction=self.direction,
            theoretical_range=self.theoretical_range,
            statistic_form=self.statistic_form,
            unit=self.unit,
            category_level=self.category_level,
            bin_label=self.bin_label,
            bin_lower=self.bin_lower,
            bin_upper=self.bin_upper,
            baseline_definition=self.baseline_definition,
            baseline_timepoint=self.baseline_timepoint,
            compatibility_rule=self.compatibility_rule,
        )

    @property
    def compatibility_bucket_id(self) -> str:
        return self.compatibility_key.identity_key

    @property
    def difference_labels(self) -> tuple[str, ...]:
        return self.difference_labels_zh


def validate_baseline_observation(
    observation: BaselineObservation | Mapping[str, Any],
) -> BaselineObservation:
    """在公共边界重新校验基线事实，拒绝 ``model_copy`` 绕过的状态。"""

    payload: object
    if isinstance(observation, BaselineObservation):
        unknown_fields = set(observation.__dict__) - set(type(observation).model_fields)
        if unknown_fields:
            raise BaselineObservationError(
                f"基线观察重新校验失败：包含未知字段 {tuple(sorted(unknown_fields))}"
            )
        extras = observation.__pydantic_extra__
        if extras:
            raise BaselineObservationError(
                f"基线观察重新校验失败：包含未知字段 {tuple(sorted(extras))}"
            )
        payload = observation.model_dump(mode="python")
    elif isinstance(observation, Mapping):
        payload = dict(observation)
    else:
        raise TypeError("基线观察必须是 BaselineObservation 或映射")
    try:
        return BaselineObservation.model_validate(payload)
    except ValidationError as error:
        raise BaselineObservationError(f"基线观察重新校验失败：{error}") from error


def _source_location(locator: EvidenceLocator) -> str:
    """将结构化定位压缩为旧 GateBinding 的非空定位字段。"""

    # field_path 是既有 GateBinding 和现有结果视图使用的首选稳定定位。
    if locator.field_path is not None:
        return locator.field_path
    parts: list[str] = [locator.document_role]
    if locator.heading is not None:
        parts.append(locator.heading)
    if locator.table is not None:
        parts.append(locator.table)
    if locator.row is not None:
        parts.append(locator.row)
    if locator.column is not None:
        parts.append(locator.column)
    if locator.page is not None:
        parts.append(f"page={locator.page}")
    if locator.paragraph is not None:
        parts.append(locator.paragraph)
    if locator.url is not None:
        parts.append(locator.url)
    return " / ".join(parts)


def _assert_gate_semantics(
    observation: BaselineObservation,
    unit_id: str,
    severity_anchor_concepts: frozenset[str],
) -> None:
    """验证四个 B-v1 基线单元的科学对象，不复制 GateSpec 判定逻辑。"""

    if observation.disclosure_state not in _REPORTED_DISCLOSURE_STATES:
        # 未报告、未公开、冲突和路线问题必须进入既有 evaluator 的阻断路径，
        # 不能在转换层伪造数值；其作用域与状态仍由 GateBinding 保存。
        return
    concept = observation.standardized_concept.casefold().replace("-", "_").replace(" ", "_")
    if unit_id == "b_baseline_sample_size":
        if concept not in _SAMPLE_SIZE_CONCEPTS:
            raise BaselineObservationError("样本量 Gate 只能绑定 baseline_sample_size 规范概念")
        if observation.variable_domain is not BaselineVariableDomain.DEMOGRAPHICS:
            raise BaselineObservationError("样本量 Gate 必须绑定人口学变量域")
        if observation.data_type is not BaselineDataType.COUNT:
            raise BaselineObservationError("样本量 Gate 必须绑定 count 数据类型")
        if observation.statistic_form is not BaselineStatisticForm.SAMPLE_SIZE:
            raise BaselineObservationError("样本量 Gate 必须绑定 sample_size 统计形式")
    elif unit_id == "b_baseline_age":
        if concept not in _AGE_CONCEPTS:
            raise BaselineObservationError("年龄 Gate 只能绑定 age 规范概念")
        if observation.variable_domain is not BaselineVariableDomain.DEMOGRAPHICS:
            raise BaselineObservationError("年龄 Gate 必须绑定人口学变量域")
        if observation.statistic_form in {
            BaselineStatisticForm.SAMPLE_SIZE,
            BaselineStatisticForm.COUNT,
            BaselineStatisticForm.PROPORTION,
        }:
            raise BaselineObservationError("年龄 Gate 必须绑定连续年龄统计形式")
    elif unit_id == "b_baseline_sex":
        if concept not in _SEX_CONCEPTS:
            raise BaselineObservationError("性别 Gate 只能绑定 sex/gender 规范概念")
        if observation.variable_domain is not BaselineVariableDomain.DEMOGRAPHICS:
            raise BaselineObservationError("性别 Gate 必须绑定人口学变量域")
        if observation.data_type is not BaselineDataType.CATEGORICAL:
            raise BaselineObservationError("性别 Gate 必须绑定 categorical 数据类型")
        if observation.statistic_form not in {
            BaselineStatisticForm.PROPORTION,
            BaselineStatisticForm.COUNT,
        }:
            raise BaselineObservationError("性别 Gate 必须绑定分类比例或人数统计")
        if observation.denominator is None:
            raise BaselineObservationError("性别 Gate 必须绑定明确正分母")
        if observation.category_level is None and observation.bin_label is None:
            raise BaselineObservationError("性别 Gate 必须绑定至少一个分类水平")
    elif unit_id == "b_baseline_severity_anchor":
        if observation.variable_domain is not BaselineVariableDomain.BASELINE_SEVERITY:
            raise BaselineObservationError("严重程度 Gate 必须绑定 baseline_severity 变量域")
        if (
            observation.scale is None
            or observation.scale_version is None
            or observation.direction is None
            or observation.theoretical_range is None
        ):
            raise BaselineObservationError(
                "严重程度 Gate 必须绑定量表/版本、方向和理论范围"
            )
        if concept not in severity_anchor_concepts:
            raise BaselineObservationError("严重程度 Gate 只能绑定当前适应症认可的指标")
    else:  # pragma: no cover - caller checks the closed set before dispatch.
        raise BaselineObservationError(f"未知基线 Gate 单元：{unit_id}")

    if observation.value is None:
        raise BaselineObservationError("已报告基线 Gate 事实必须有明确数值")
    if observation.unit is None and unit_id != "b_baseline_sex":
        raise BaselineObservationError("该基线 Gate 事实必须有单位")
    if observation.analysis_population.strip() == "":
        raise BaselineObservationError("基线 Gate 事实必须有分析人群")
    if observation.baseline_definition.strip() == "":
        raise BaselineObservationError("基线 Gate 事实必须有基线定义")
    if unit_id == "b_baseline_severity_anchor" and observation.baseline_timepoint.strip() == "":
        raise BaselineObservationError("严重程度 Gate 事实必须有基线时间")


def to_gate_evidence_binding(
    observation: BaselineObservation | Mapping[str, Any],
    *,
    unit_id: str,
    severity_anchor_concepts: frozenset[str] = frozenset(),
) -> GateEvidenceBinding:
    """将一条基线事实严格转换为现有 GateEvidenceBinding。

    转换只使用观察自身的产品/试验/组别、事实版本、状态和来源定位；不
    聚合观察、不从其他组借值，也不创建新的门槛或状态机。
    """

    if unit_id not in _BASELINE_GATE_UNIT_IDS:
        raise BaselineObservationError(f"未知基线 Gate 单元：{unit_id}")
    validated = validate_baseline_observation(observation)
    _assert_gate_semantics(validated, unit_id, severity_anchor_concepts)
    try:
        return GateEvidenceBinding.model_validate(
            {
                "schema_version": "1.0",
                "binding_id": stable_id("baseline-gate-binding", unit_id, validated.row_id),
                "unit_id": unit_id,
                "object_id": validated.group_id,
                "fact_version_id": validated.row_id,
                "trial_id": validated.trial_id,
                "group_id": validated.group_id,
                "fact_domain": FactDomain.TRIAL_DESIGN,
                "observation_kind": ObservationKind.OBSERVED_RESULT,
                "numeric_value": validated.value,
                "unit": validated.unit,
                "denominator": validated.denominator,
                "definition": validated.source_definition,
                "direction": validated.direction,
                "timepoint": validated.baseline_timepoint,
                "analysis_population": validated.analysis_population,
                "source_location": _source_location(validated.source_locator),
                "route_receipt_id": validated.route_receipt_id,
                "review_state": validated.review_state,
                "disclosure_state": validated.disclosure_state,
                "disclosure_maturity": validated.disclosure_maturity,
                "source_role": validated.source_role,
                "conflict_disposition": validated.conflict_disposition,
                "applicability_predicate_id": validated.applicability_predicate_id,
                "reported_zero_text": validated.reported_zero_text,
            }
        )
    except ValidationError as error:
        raise BaselineObservationError(f"基线事实转 GateEvidenceBinding 失败：{error}") from error


def build_baseline_gate_bindings(
    observations: Sequence[BaselineObservation | Mapping[str, Any]],
    unit_ids: Sequence[str],
    *,
    severity_anchor_concepts: frozenset[str],
) -> tuple[GateEvidenceBinding, ...]:
    """批量转换并拒绝同一不可变事实被多个组重复使用。"""

    if len(observations) != len(unit_ids):
        raise BaselineObservationError("基线事实与 Gate 单元数量不一致")
    bindings = tuple(
        to_gate_evidence_binding(
            observation,
            unit_id=unit_id,
            severity_anchor_concepts=severity_anchor_concepts,
        )
        for observation, unit_id in zip(observations, unit_ids, strict=True)
    )
    lineage = {(item.fact_version_id, item.group_id) for item in bindings}
    if len({item.fact_version_id for item in bindings}) != len(lineage):
        raise BaselineObservationError("同一基线事实版本不得用于多个组别")
    return bindings


__all__ = [
    "BaselineCompatibilityKey",
    "BaselineDataType",
    "BaselineObservation",
    "BaselineObservationError",
    "BaselineStatisticForm",
    "BaselineVariableDomain",
    "build_baseline_gate_bindings",
    "to_gate_evidence_binding",
    "validate_baseline_observation",
]
