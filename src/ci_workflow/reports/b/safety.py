"""B 类安全性事实与披露语义合同。

本模块只定义安全性事实的来源闭合边界。安全性视图可以把同一事实投影
为热图单元或完整 AE 表，但不能改写事实中的原始术语、数值、披露状态或
来源谱系。尤其是 ``not_reported``、``below_reporting_threshold`` 与技术
路径未解决不是数值零的不同写法。
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from typing import Any, Self

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
from ci_workflow.reports.a.contracts import SafetyMeasurementUnit

SafetyDisclosureState = FactDisclosureState
SafetyValueState = FactDisclosureState
DisclosureState = FactDisclosureState


class SafetyViewError(ValueError):
    """安全性事实或其来源闭合合同无法满足。"""


class SafetyFamily(StrEnum):
    """B 类安全性视图支持的事件族。

    前四类是默认总览维度；其余类别只在来源有对应事实时加入，不暗示
    来源必然披露这些类别。
    """

    TEAE = "teae"
    SAE = "sae"
    AESI = "aesi"
    COMMON_AE = "common_ae"
    DEATH = "death"
    GRADE_3_OR_HIGHER = "grade_3_or_higher"
    DISCONTINUATION_DUE_TO_AE = "discontinuation_due_to_ae"
    TREATMENT_RELATED_TEAE = "treatment_related_teae"

    # 常见输入别名只归一到同一序列化值。
    COMMON_TEAE = "common_ae"
    GRADE_3_PLUS = "grade_3_or_higher"
    GRADE_3_AND_ABOVE = "grade_3_or_higher"
    AE_DISCONTINUATION = "discontinuation_due_to_ae"
    TREATMENT_RELATED = "treatment_related_teae"


SafetyEventFamily = SafetyFamily


# 固定总览维度按临床阅读顺序保留；其余维度只在来源存在事实时加入。
SafetyDefaultDimension = SafetyFamily
SafetyOverviewDimension = SafetyFamily
DEFAULT_SAFETY_DIMENSIONS: tuple[SafetyFamily, ...] = (
    SafetyFamily.TEAE,
    SafetyFamily.SAE,
    SafetyFamily.AESI,
    SafetyFamily.COMMON_AE,
)
DEFAULT_SAFETY_FAMILIES = DEFAULT_SAFETY_DIMENSIONS
OPTIONAL_SAFETY_DIMENSIONS: tuple[SafetyFamily, ...] = (
    SafetyFamily.DEATH,
    SafetyFamily.GRADE_3_OR_HIGHER,
    SafetyFamily.DISCONTINUATION_DUE_TO_AE,
    SafetyFamily.TREATMENT_RELATED_TEAE,
)
OPTIONAL_SAFETY_FAMILIES = OPTIONAL_SAFETY_DIMENSIONS

_DEFAULT_COMMON_AE_LIMIT = 12
_COMMON_AE_RATE_THRESHOLD_PERCENT = 5.0
_COMMON_AE_DIFFERENCE_THRESHOLD_PERCENT = 5.0
SafetyEventKind = SafetyFamily


class SafetyArmRole(StrEnum):
    """安全性事实所属的治疗或对照组别。"""

    TREATMENT = "treatment"
    CONTROL = "control"

    ACTIVE = "treatment"
    INTERVENTION = "treatment"
    TEST = "treatment"
    PLACEBO = "control"
    COMPARATOR = "control"
    REFERENCE = "control"


ArmRole = SafetyArmRole


class SafetyTermMappingConfidence(StrEnum):
    """术语映射置信度；低置信度映射不得覆盖来源术语。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"
    NOT_AVAILABLE = "not_available"

    HIGH_CONFIDENCE = "high"
    MEDIUM_CONFIDENCE = "medium"
    LOW_CONFIDENCE = "low"
    MAPPING_UNCERTAIN = "uncertain"
    UNAVAILABLE = "not_available"


TermMappingConfidence = SafetyTermMappingConfidence


class SafetyTechnicalStatus(StrEnum):
    """技术路径诊断；不是事实披露状态。"""

    ACCESS_BLOCKED = "access_blocked"
    TRANSIENT_NETWORK_FAILURE = "transient_network_failure"
    RATE_LIMITED = "rate_limited"
    ANTI_BOT_OR_CAPTCHA = "anti_bot_or_captcha"
    SOURCE_UNAVAILABLE = "source_unavailable"

    PARSER_OR_SCHEMA_FAILURE = "parser_or_schema_failure"
    TOOL_CAPABILITY_GAP = "tool_capability_gap"
    CONTENT_TRUNCATED = "content_truncated"
    UNKNOWN = "unknown"

    TECHNICALLY_UNAVAILABLE = "unknown"
    TECHNICAL_UNAVAILABLE = "unknown"
    ROUTE_UNRESOLVED = "unknown"


_SAFETY_FAMILY_LABELS_ZH: dict[SafetyFamily, str] = {
    SafetyFamily.TEAE: "治疗期间不良事件",
    SafetyFamily.SAE: "严重不良事件",
    SafetyFamily.AESI: "特别关注不良事件",
    SafetyFamily.COMMON_AE: "常见不良事件",
    SafetyFamily.DEATH: "死亡",
    SafetyFamily.GRADE_3_OR_HIGHER: "3级及以上不良事件",
    SafetyFamily.DISCONTINUATION_DUE_TO_AE: "导致停药不良事件",
    SafetyFamily.TREATMENT_RELATED_TEAE: "治疗相关治疗期间不良事件",
}


TechnicalStatus = SafetyTechnicalStatus


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

_NON_CONCRETE_STATES = frozenset(
    {
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.NOT_APPLICABLE,
        FactDisclosureState.CONFLICTING,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    }
)

_NUMERIC_DISCLOSURE = re.compile(
    r"^\s*[<>≤≥~≈]?\s*[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
    r"\s*(?:[%％]|[A-Za-z\u3400-\u9fff][^\n]*)?\s*$"
)
_ZERO_EVIDENCE = re.compile(r"(?<![0-9.])0(?:\.0+)?(?=\s*(?:[%％/]|[A-Za-z\u3400-\u9fff]+|\)|$))")
_THRESHOLD_EVIDENCE = re.compile(
    r"(?:^\s*[<≤]|低于|少于|小于|未达到|低于或等于)",
    re.IGNORECASE,
)


def _text(value: str, *, field_name: str = "安全性事实字段") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name}必须是文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _raw_text(value: str, *, field_name: str = "安全性原始字段") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}不能为空")
    # 原始来源字段保留原样，只拒绝完全空白。
    return value


def _optional_text(value: str | None, *, field_name: str = "安全性可选字段") -> str | None:
    return None if value is None else _raw_text(value, field_name=field_name)


def _as_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (value,)
    try:
        return tuple(value)
    except TypeError as error:
        raise ValueError("安全性来源标识必须是序列") from error


def _normalize_arm_role(value: Any) -> Any:
    if isinstance(value, SafetyArmRole):
        return value
    if not isinstance(value, str):
        return value
    token = value.strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "treatment": "treatment",
        "active": "treatment",
        "intervention": "treatment",
        "test": "treatment",
        "experimental": "treatment",
        "治疗": "treatment",
        "治疗组": "treatment",
        "试验组": "treatment",
        "干预组": "treatment",
        "control": "control",
        "placebo": "control",
        "comparator": "control",
        "reference": "control",
        "对照": "control",
        "对照组": "control",
        "安慰剂": "control",
        "安慰剂组": "control",
    }
    return aliases.get(token, value)


def _normalize_family(value: Any) -> Any:
    if isinstance(value, SafetyFamily):
        return value
    if not isinstance(value, str):
        return value
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
        "特别关注的不良事件": "aesi",
        "common_ae": "common_ae",
        "common_teae": "common_ae",
        "common_adverse_event": "common_ae",
        "常见不良事件": "common_ae",
        "death": "death",
        "deaths": "death",
        "死亡": "death",
        "grade_3_or_higher": "grade_3_or_higher",
        "grade_3_plus": "grade_3_or_higher",
        "grade_3_and_above": "grade_3_or_higher",
        "grade_≥3": "grade_3_or_higher",
        "3级及以上": "grade_3_or_higher",
        "discontinuation_due_to_ae": "discontinuation_due_to_ae",
        "ae_discontinuation": "discontinuation_due_to_ae",
        "导致停药不良事件": "discontinuation_due_to_ae",
        "treatment_related_teae": "treatment_related_teae",
        "treatment_related": "treatment_related_teae",
        "治疗相关teae": "treatment_related_teae",
    }
    return aliases.get(token, value)


def disclosure_state_label_zh(state: FactDisclosureState | str) -> str:
    """返回披露状态的保守中文标签，不把状态转成数值。"""

    resolved = state if isinstance(state, FactDisclosureState) else FactDisclosureState(state)
    try:
        return _DISCLOSURE_LABELS_ZH[resolved]
    except (KeyError, ValueError) as error:
        raise ValueError(f"未知安全性披露状态：{state!r}") from error


_TECHNICAL_LABELS_ZH: dict[SafetyTechnicalStatus, str] = {
    SafetyTechnicalStatus.ACCESS_BLOCKED: "访问或权限受限",
    SafetyTechnicalStatus.TRANSIENT_NETWORK_FAILURE: "网络暂时不可用",
    SafetyTechnicalStatus.RATE_LIMITED: "访问频率受限",
    SafetyTechnicalStatus.ANTI_BOT_OR_CAPTCHA: "反爬或验证码阻断",
    SafetyTechnicalStatus.SOURCE_UNAVAILABLE: "来源暂不可用",
    SafetyTechnicalStatus.PARSER_OR_SCHEMA_FAILURE: "解析或结构失败",
    SafetyTechnicalStatus.TOOL_CAPABILITY_GAP: "工具能力不足",
    SafetyTechnicalStatus.CONTENT_TRUNCATED: "来源内容不完整",
    SafetyTechnicalStatus.UNKNOWN: "技术原因待核实",
}


def technical_status_label_zh(status: SafetyTechnicalStatus | str) -> str:
    """返回技术异常标签；技术异常不转成科学披露结论。"""

    resolved = (
        status if isinstance(status, SafetyTechnicalStatus) else SafetyTechnicalStatus(status)
    )
    try:
        return _TECHNICAL_LABELS_ZH[resolved]
    except (KeyError, ValueError) as error:
        raise ValueError(f"未知安全性技术状态：{status!r}") from error


safety_value_state_label_zh = disclosure_state_label_zh
safety_technical_status_label_zh = technical_status_label_zh
safety_disclosure_state_label_zh = disclosure_state_label_zh


class SafetyTermMapping(BaseModel):
    """一个可审计的来源术语到规范术语映射。

    ``preferred_term`` 为空时表示没有可靠规范映射；``source_term`` 永远
    不被规范术语覆盖。低、中或不确定置信度的映射可作为人工提示保留，
    但 ``is_reliable`` 为假，比较和分组必须继续使用来源术语。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    source_term: str | None = Field(
        default=None,
        validation_alias=AliasChoices("source_term", "original_term", "raw_term"),
    )
    source_language: str | None = Field(
        default=None,
        validation_alias=AliasChoices("source_language", "language", "term_language"),
    )
    preferred_term: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "preferred_term",
            "meddra_preferred_term",
            "meddra_pt",
            "standard_term",
            "normalized_term",
            "mapped_term",
        ),
    )
    meddra_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices("meddra_version", "version", "dictionary_version"),
    )
    mapping_method: str | None = Field(
        default=None,
        validation_alias=AliasChoices("mapping_method", "method", "mapping_rule"),
    )
    confidence: SafetyTermMappingConfidence | str | None = Field(
        default=None,
        validation_alias=AliasChoices("confidence", "mapping_confidence"),
    )
    mapping_note: str | None = Field(
        default=None,
        validation_alias=AliasChoices("mapping_note", "note"),
    )

    @field_validator(
        "source_term",
        "source_language",
        "preferred_term",
        "meddra_version",
        "mapping_method",
        "mapping_note",
    )
    @classmethod
    def _mapping_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="术语映射字段")

    @field_validator("confidence", mode="before")
    @classmethod
    def _mapping_confidence(cls, value: Any) -> Any:
        if value is None or isinstance(value, SafetyTermMappingConfidence):
            return value
        if not isinstance(value, str):
            return value
        token = value.strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "high_confidence": "high",
            "high": "high",
            "medium_confidence": "medium",
            "moderate": "medium",
            "medium": "medium",
            "low_confidence": "low",
            "low": "low",
            "uncertain": "uncertain",
            "不确定": "uncertain",
            "not_available": "not_available",
            "unavailable": "not_available",
            "不可用": "not_available",
        }
        return aliases.get(token, value)

    @model_validator(mode="after")
    def _mapping_contract(self) -> Self:
        if self.preferred_term is None:
            if self.confidence in {SafetyTermMappingConfidence.HIGH, "high"}:
                raise ValueError("没有规范术语时不得声明高置信度映射")
            return self
        if self.meddra_version is None:
            raise ValueError("规范术语必须保存 MedDRA 或字典版本")
        if self.mapping_method is None:
            raise ValueError("规范术语必须保存映射方法")
        if self.confidence is None:
            raise ValueError("规范术语必须保存映射置信度")
        return self

    @property
    def original_term(self) -> str | None:
        return self.source_term

    @property
    def meddra_preferred_term(self) -> str | None:
        return self.preferred_term

    @property
    def standard_term(self) -> str | None:
        return self.preferred_term

    @property
    def mapped_term(self) -> str | None:
        return self.preferred_term

    @property
    def is_available(self) -> bool:
        return self.preferred_term is not None

    @property
    def is_reliable(self) -> bool:
        """只有明确高置信度映射可作为比较身份。"""

        return self.preferred_term is not None and self.confidence in {
            SafetyTermMappingConfidence.HIGH,
            "high",
        }

    @property
    def can_group_with_standard_term(self) -> bool:
        return self.is_reliable

    @property
    def version(self) -> str | None:
        return self.meddra_version

    @property
    def method(self) -> str | None:
        return self.mapping_method

    @property
    def mapping_confidence(self) -> SafetyTermMappingConfidence | str | None:
        return self.confidence

    @property
    def source_language_code(self) -> str | None:
        return self.source_language


SafetyTermMap = SafetyTermMapping

SafetyTerminologyMapping = SafetyTermMapping
TermMapping = SafetyTermMapping


class SafetySourceLineage(BaseModel):
    """安全性事实的来源版本、来源行和精确证据位置。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    source_version_id: str = Field(
        validation_alias=AliasChoices("source_version_id", "source_version", "captured_version")
    )
    source_row_id: str = Field(
        validation_alias=AliasChoices("source_row_id", "source_row", "source_line_id", "row_ref")
    )

    source_locator: EvidenceLocator = Field(
        validation_alias=AliasChoices("source_locator", "locator", "source_location")
    )
    source_role: str | None = None
    source_scope: str | None = None

    @field_validator("source_version_id", "source_row_id")
    @classmethod
    def _lineage_required_text(cls, value: str) -> str:
        return _text(value, field_name="安全性来源谱系标识")

    @field_validator("source_role", "source_scope")
    @classmethod
    def _lineage_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="安全性来源谱系字段")

    @property
    def source_version(self) -> str:
        return self.source_version_id

    @property
    def source_row(self) -> str:
        return self.source_row_id

    @property
    def locator(self) -> EvidenceLocator:
        return self.source_locator

    @property
    def source_location(self) -> EvidenceLocator:
        return self.source_locator


SafetyProvenance = SafetySourceLineage
SourceLineage = SafetySourceLineage


class SafetyFactRow(BaseModel):
    """一条不可变、来源闭合的安全性事实。

    ``value`` 只承载已报告的确定数值；``raw_value`` 保存来源原始表达。
    非具体披露状态可以保留来源文字，但不能携带确定数值。技术路径问题
    使用 ``UNRESOLVED_DUE_TO_ROUTE`` 加独立诊断和回执表示，绝不降级为
    ``NOT_REPORTED``。术语映射只作为附加谱系，永远不能删除来源术语。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    row_id: str = Field(
        validation_alias=AliasChoices(
            "row_id",
            "fact_row_id",
            "fact_version_id",
            "fact_id",
            "id",
        )
    )
    source_row_id: str = Field(
        validation_alias=AliasChoices("source_row_id", "source_row", "source_line_id", "row_ref")
    )
    observation_id: str = Field(
        default="",
        validation_alias=AliasChoices("observation_id", "event_observation_id", "observation_ref"),
    )
    product_id: str = Field(validation_alias=AliasChoices("product_id", "project_id"))
    trial_id: str = Field(validation_alias=AliasChoices("trial_id", "study_id"))
    family: SafetyFamily = Field(
        validation_alias=AliasChoices(
            "family",
            "event_family",
            "event_family_id",
            "family_id",
            "safety_family",
            "event_kind",
        )
    )
    term_id: str = Field(
        default="",
        validation_alias=AliasChoices("term_id", "event_id", "source_term_id", "ae_term_id"),
    )
    source_term: str = Field(
        validation_alias=AliasChoices(
            "source_term",
            "original_term",
            "raw_term",
            "event_term",
            "term",
            "ae_term",
        )
    )
    term_key: str = "unknown"
    polarity: str = "affirmed"
    grade_set: tuple[int, ...] = ()
    seriousness: str = "unspecified"
    teae: bool | None = None
    relatedness: str = "unspecified"
    parent: str | None = None
    children: tuple[str, ...] = ()
    count_basis: str = "participants"
    at_risk_stat: str | None = None
    standard_term: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "standard_term",
            "normalized_term",
            "meddra_preferred_term",
            "meddra_pt",
            "mapped_term",
        ),
    )
    term_mapping: SafetyTermMapping | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "term_mapping",
            "terminology_mapping",
            "meddra_mapping",
            "mapping",
        ),
    )
    event_definition_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "event_definition_zh",
            "event_definition",
            "original_definition",
            "definition_zh",
            "ae_definition",
        ),
    )
    time_window_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "time_window_zh",
            "time_window",
            "original_time_window",
            "assessment_window",
        ),
    )
    analysis_population_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "analysis_population_zh",
            "analysis_population",
            "population",
            "population_zh",
        ),
    )
    arm_role: SafetyArmRole = Field(
        validation_alias=AliasChoices("arm_role", "group_role", "arm_type")
    )
    arm_id: str = Field(validation_alias=AliasChoices("arm_id", "group_id", "arm"))
    arm_label: str = Field(
        validation_alias=AliasChoices("arm_label", "group_label", "group_label_zh", "arm_name")
    )
    value: int | float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "value",
            "numeric_value",
            "observed_value",
            "raw_numeric_value",
        ),
    )
    raw_value: str | int | float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "raw_value",
            "source_value",
            "reported_value_text",
            "original_value",
            "value_text",
        ),
    )
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, ge=1)
    denominator_semantics_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "denominator_semantics_zh",
            "denominator_semantics",
            "denominator_definition",
            "denominator_basis",
        ),
    )
    unit: str | None = Field(
        default=None,
        validation_alias=AliasChoices("unit", "measurement_unit", "measure_unit"),
    )
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE
    source_version_id: str = Field(
        validation_alias=AliasChoices("source_version_id", "source_version", "captured_version")
    )
    source_locator: EvidenceLocator = Field(
        validation_alias=AliasChoices("source_locator", "locator", "source_location")
    )
    source_role: str | None = None
    source_scope: str | None = None
    source_lineage: SafetySourceLineage | None = Field(
        default=None,
        validation_alias=AliasChoices("source_lineage", "provenance", "lineage"),
    )
    technical_status: SafetyTechnicalStatus | str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "technical_status",
            "technical_issue",
            "technical_anomaly",
            "route_diagnostic",
        ),
    )
    technical_diagnostic: str | None = Field(
        default=None,
        validation_alias=AliasChoices("technical_diagnostic", "technical_reason", "technical_note"),
    )
    unresolved_route_receipt_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "unresolved_route_receipt_id",
            "route_receipt_id",
            "technical_route_receipt_id",
        ),
    )
    applicability_predicate_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("applicability_predicate_id", "applicability_rule_id"),
    )
    conflict_note: str | None = Field(
        default=None,
        validation_alias=AliasChoices("conflict_note", "conflict_reason"),
    )
    conflicting_source_row_ids: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "conflicting_source_row_ids",
            "conflict_source_row_ids",
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _expand_fact_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)

        # Accept a nested lineage as the source for the flattened fields while
        # retaining the flattened representation used by B views.
        raw_lineage = payload.get(
            "source_lineage",
            payload.get("provenance", payload.get("lineage")),
        )
        if raw_lineage is not None:
            try:
                lineage = (
                    raw_lineage
                    if isinstance(raw_lineage, SafetySourceLineage)
                    else SafetySourceLineage.model_validate(raw_lineage)
                )
            except (TypeError, ValueError, ValidationError) as error:
                raise ValueError(f"安全性来源谱系无效：{error}") from error
            payload["source_lineage"] = lineage
            payload.setdefault("source_version_id", lineage.source_version_id)
            payload.setdefault("source_row_id", lineage.source_row_id)
            payload.setdefault("source_locator", lineage.source_locator)
            payload.setdefault("source_role", lineage.source_role)
            payload.setdefault("source_scope", lineage.source_scope)

        # Normalize common legacy names before extra-field rejection. The
        # declared AliasChoices handle input validation; this map handles
        # values that need to participate in derivation below.
        aliases = {
            "id": "row_id",
            "fact_row_id": "row_id",
            "fact_version_id": "row_id",
            "fact_id": "row_id",
            "source_row": "source_row_id",
            "source_line_id": "source_row_id",
            "row_ref": "source_row_id",
            "project_id": "product_id",
            "study_id": "trial_id",
            "event_family": "family",
            "event_family_id": "family",
            "family_id": "family",
            "safety_family": "family",
            "event_kind": "family",
            "event_id": "term_id",
            "source_term_id": "term_id",
            "ae_term_id": "term_id",
            "original_term": "source_term",
            "raw_term": "source_term",
            "event_term": "source_term",
            "term": "source_term",
            "ae_term": "source_term",
            "normalized_term": "standard_term",
            "meddra_preferred_term": "standard_term",
            "meddra_pt": "standard_term",
            "mapped_term": "standard_term",
            "event_definition": "event_definition_zh",
            "original_definition": "event_definition_zh",
            "definition_zh": "event_definition_zh",
            "ae_definition": "event_definition_zh",
            "time_window": "time_window_zh",
            "original_time_window": "time_window_zh",
            "assessment_window": "time_window_zh",
            "analysis_population": "analysis_population_zh",
            "population": "analysis_population_zh",
            "population_zh": "analysis_population_zh",
            "group_role": "arm_role",
            "arm_type": "arm_role",
            "group_id": "arm_id",
            "arm": "arm_id",
            "group_label": "arm_label",
            "group_label_zh": "arm_label",
            "arm_name": "arm_label",
            "numeric_value": "value",
            "observed_value": "value",
            "raw_numeric_value": "value",
            "source_value": "raw_value",
            "reported_value_text": "raw_value",
            "original_value": "raw_value",
            "value_text": "raw_value",
            "measurement_unit": "unit",
            "denominator_semantics": "denominator_semantics_zh",
            "denominator_definition": "denominator_semantics_zh",
            "denominator_basis": "denominator_semantics_zh",
            "measure_unit": "unit",
            "source_version": "source_version_id",
            "captured_version": "source_version_id",
            "locator": "source_locator",
            "source_location": "source_locator",
            "technical_issue": "technical_status",
            "technical_anomaly": "technical_status",
            "route_diagnostic": "technical_status",
            "technical_reason": "technical_diagnostic",
            "technical_note": "technical_diagnostic",
            "route_receipt_id": "unresolved_route_receipt_id",
            "technical_route_receipt_id": "unresolved_route_receipt_id",
            "applicability_rule_id": "applicability_predicate_id",
            "conflict_reason": "conflict_note",
            "conflict_source_row_ids": "conflicting_source_row_ids",
            "terminology_mapping": "term_mapping",
            "meddra_mapping": "term_mapping",
            "mapping": "term_mapping",
            "provenance": "source_lineage",
            "lineage": "source_lineage",
        }
        for source, target in aliases.items():
            if target not in payload and source in payload:
                payload[target] = payload[source]
            if source != target:
                payload.pop(source, None)

        if "family" in payload:
            payload["family"] = _normalize_family(payload["family"])
        if "arm_role" in payload:
            payload["arm_role"] = _normalize_arm_role(payload["arm_role"])

        if "source_row_id" not in payload and "row_id" in payload:
            payload["source_row_id"] = payload["row_id"]
        if "row_id" not in payload and "source_row_id" in payload:
            payload["row_id"] = payload["source_row_id"]
        if "term_id" not in payload and "source_term" in payload:
            # Source term is the conservative identity when no controlled
            # vocabulary identifier exists; it is never replaced by a free
            # translation or an uncertain standardized term.
            payload["term_id"] = payload["source_term"]
        if "observation_id" not in payload and "source_row_id" in payload:
            payload["observation_id"] = payload["source_row_id"]
        if "disclosure_state" not in payload:
            payload["disclosure_state"] = (
                FactDisclosureState.REPORTED_VALUE
                if payload.get("value") is not None
                else FactDisclosureState.NOT_REPORTED
            )

        raw_mapping = payload.get("term_mapping")
        if raw_mapping is not None:
            try:
                mapping = (
                    raw_mapping
                    if isinstance(raw_mapping, SafetyTermMapping)
                    else SafetyTermMapping.model_validate(raw_mapping)
                )
            except (TypeError, ValueError, ValidationError) as error:
                raise ValueError(f"安全性术语映射无效：{error}") from error
            if mapping.source_term is None and "source_term" in payload:
                mapping = SafetyTermMapping(
                    **{
                        **mapping.model_dump(mode="python"),
                        "source_term": payload["source_term"],
                    }
                )
            payload["term_mapping"] = mapping
            if payload.get("standard_term") is None and mapping.preferred_term is not None:
                payload["standard_term"] = mapping.preferred_term

        return payload

    @field_validator(
        "row_id",
        "source_row_id",
        "observation_id",
        "product_id",
        "trial_id",
        "term_id",
        "source_term",
        "arm_id",
        "arm_label",
        "source_version_id",
    )
    @classmethod
    def _required_fact_text(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "standard_term",
        "event_definition_zh",
        "time_window_zh",
        "analysis_population_zh",
        "unit",
        "denominator_semantics_zh",
        "source_role",
        "source_scope",
        "technical_diagnostic",
        "unresolved_route_receipt_id",
        "applicability_predicate_id",
        "conflict_note",
    )
    @classmethod
    def _optional_fact_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="安全性事实可选字段")

    @field_validator("family", mode="before")
    @classmethod
    def _family_alias(cls, value: Any) -> Any:
        return _normalize_family(value)

    @field_validator("arm_role", mode="before")
    @classmethod
    def _arm_alias(cls, value: Any) -> Any:
        return _normalize_arm_role(value)

    @field_validator("technical_status", mode="before")
    @classmethod
    def _technical_status_text(cls, value: Any) -> Any:
        if value is None or isinstance(value, SafetyTechnicalStatus):
            return value
        if not isinstance(value, str):
            return value
        token = value.strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "technical_unavailable": SafetyTechnicalStatus.UNKNOWN,
            "technically_unavailable": SafetyTechnicalStatus.UNKNOWN,
            "技术不可用": SafetyTechnicalStatus.UNKNOWN,
            "access_or_permission_blocked": SafetyTechnicalStatus.ACCESS_BLOCKED,
            "access_blocked": SafetyTechnicalStatus.ACCESS_BLOCKED,
            "访问受限": SafetyTechnicalStatus.ACCESS_BLOCKED,
            "parser_failure": SafetyTechnicalStatus.PARSER_OR_SCHEMA_FAILURE,
            "parser_or_schema_failure": SafetyTechnicalStatus.PARSER_OR_SCHEMA_FAILURE,
            "解析失败": SafetyTechnicalStatus.PARSER_OR_SCHEMA_FAILURE,
            "network_failure": SafetyTechnicalStatus.TRANSIENT_NETWORK_FAILURE,
            "transient_network_failure": SafetyTechnicalStatus.TRANSIENT_NETWORK_FAILURE,
            "rate_limited": SafetyTechnicalStatus.RATE_LIMITED,
            "anti_bot_or_captcha": SafetyTechnicalStatus.ANTI_BOT_OR_CAPTCHA,
            "source_unavailable": SafetyTechnicalStatus.SOURCE_UNAVAILABLE,
            "tool_capability_gap": SafetyTechnicalStatus.TOOL_CAPABILITY_GAP,
            "content_truncated": SafetyTechnicalStatus.CONTENT_TRUNCATED,
        }
        return aliases.get(token, value)

    @field_validator("conflicting_source_row_ids")
    @classmethod
    def _conflict_rows(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value, field_name="冲突来源行标识") for value in values)
        if len(normalized) != len(set(normalized)):
            raise ValueError("冲突来源行标识不得重复")
        return normalized

    @field_validator("value")
    @classmethod
    def _finite_value(cls, value: int | float | None) -> int | float | None:
        if isinstance(value, bool):
            raise ValueError("安全性事实数值不得为布尔值")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("安全性事实数值必须是有限数值")
        return value

    @field_validator("raw_value")
    @classmethod
    def _raw_value_shape(cls, value: str | int | float | None) -> str | int | float | None:
        if isinstance(value, bool):
            raise ValueError("安全性原始数值不得为布尔值")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("安全性原始数值必须是有限数值")
        if isinstance(value, str):
            return _raw_text(value, field_name="安全性原始表达")
        return value

    @field_validator("numerator")
    @classmethod
    def _numerator_is_integer(cls, value: int | None) -> int | None:
        if isinstance(value, bool):
            raise ValueError("安全性事实分子不得为布尔值")
        return value

    @model_validator(mode="after")
    def _fact_integrity(self) -> Self:
        if self.count_basis == "mixed" and (
            self.numerator is not None or self.denominator is not None
        ):
            raise ValueError("复合安全项不得拆值或借用其他项分母")

        if self.disclosure_state in _NON_CONCRETE_STATES and self.value is not None:
            raise ValueError("非数值披露状态不得携带确定数值")
        if self.disclosure_state is FactDisclosureState.REPORTED_VALUE and self.value is None:
            raise ValueError("reported_value 状态必须保存来源直接报告的数值")
        if self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            if self.value != 0:
                raise ValueError("reported_zero 状态必须保存来源直接报告的零值")
            has_zero_evidence = (
                isinstance(self.raw_value, (int, float))
                and not isinstance(self.raw_value, bool)
                and self.raw_value == 0
            ) or (
                isinstance(self.raw_value, str)
                and _ZERO_EVIDENCE.search(self.raw_value) is not None
            )
            if not has_zero_evidence:
                raise ValueError("已报告零值必须保存明确零值原文证据")
        if self.disclosure_state is FactDisclosureState.REPORTED_VALUE and self.value == 0:
            raise ValueError("确定零值必须使用 reported_zero 状态")

        if self.has_numeric_value:
            requires_denominator = (
                self.count_basis == "participants"
                and self.unit not in {"事件数", "event_count", "次"}
            )
            if requires_denominator and self.denominator is None:
                raise ValueError("已报告安全性数值必须保留正分母")
            assert self.value is not None
            if self.value < 0:
                raise ValueError("安全性发生率或事件数不得为负数")
            if self.unit is not None and self.unit.endswith("%") and not 0 <= self.value <= 100:
                raise ValueError("百分比安全性结果必须位于0至100之间")
            if self.unit in {"例", "人", "participant_count"}:
                if not isinstance(self.value, int) or isinstance(self.value, bool):
                    raise ValueError("受试者人数必须是整数")
                if self.denominator is not None and self.value > self.denominator:
                    raise ValueError("受试者人数不得大于分母")
            if self.unit in {"事件数", "event_count"} and (
                not isinstance(self.value, int) or isinstance(self.value, bool)
            ):
                raise ValueError("事件数必须是整数")

        if self.disclosure_state in {
            FactDisclosureState.NOT_REPORTED,
            FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        } and (
            (isinstance(self.raw_value, (int, float)) and not isinstance(self.raw_value, bool))
            or (
                isinstance(self.raw_value, str)
                and _NUMERIC_DISCLOSURE.fullmatch(self.raw_value) is not None
            )
        ):
            raise ValueError("未报告或未公开状态不得携带数值型原始表达")

        if self.disclosure_state is FactDisclosureState.BELOW_REPORTING_THRESHOLD and (
            self.raw_value is None
            or not isinstance(self.raw_value, str)
            or _THRESHOLD_EVIDENCE.search(self.raw_value) is None
        ):
            raise ValueError("低于报告阈值状态必须保存来源阈值原文")

        if (
            self.disclosure_state is FactDisclosureState.NOT_APPLICABLE
            and self.applicability_predicate_id is None
        ):
            raise ValueError("不适用安全性事实必须链接适用性谓词")

        if self.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE:
            if self.unresolved_route_receipt_id is None:
                raise ValueError("路线未解决安全性事实必须链接路由回执")
            if self.technical_status is None and self.technical_diagnostic is None:
                raise ValueError("路线未解决安全性事实必须保存独立技术诊断")
        elif (
            self.technical_status is not None
            or self.technical_diagnostic is not None
            or self.unresolved_route_receipt_id is not None
        ):
            raise ValueError("技术异常必须使用 unresolved_due_to_route 状态，不得伪装为科学缺失")

        if self.term_mapping is not None:
            mapping = self.term_mapping
            if mapping.source_term is not None and mapping.source_term != self.source_term:
                raise ValueError("术语映射来源术语不得覆盖或偏离原始来源术语")
            if mapping.preferred_term is not None:
                if self.standard_term != mapping.preferred_term:
                    raise ValueError("规范术语必须与映射谱系一致")
            elif self.standard_term is not None:
                raise ValueError("没有规范映射时不得携带规范术语")
        elif self.standard_term is not None:
            raise ValueError("规范术语必须链接明确的术语映射谱系")

        if self.source_lineage is not None:
            lineage = self.source_lineage
            if (
                lineage.source_version_id != self.source_version_id
                or lineage.source_row_id != self.source_row_id
                or lineage.source_locator != self.source_locator
                or lineage.source_role != self.source_role
                or lineage.source_scope != self.source_scope
            ):
                raise ValueError("安全性事实平铺来源字段不得覆盖来源谱系")
        else:
            lineage = SafetySourceLineage(
                source_version_id=self.source_version_id,
                source_row_id=self.source_row_id,
                source_locator=self.source_locator,
                source_role=self.source_role,
                source_scope=self.source_scope,
            )
            object.__setattr__(self, "source_lineage", lineage)

        return self

    @property
    def original_term(self) -> str:
        return self.source_term

    @property
    def raw_term(self) -> str:
        return self.source_term

    @property
    def event_term(self) -> str:
        return self.source_term

    @property
    def meddra_preferred_term(self) -> str | None:
        return self.standard_term

    @property
    def normalized_term(self) -> str | None:
        return self.standard_term

    @property
    def mapped_term(self) -> str | None:
        return self.standard_term

    @property
    def source_locator_ref(self) -> EvidenceLocator:
        return self.source_locator

    @property
    def locator(self) -> EvidenceLocator:
        return self.source_locator

    @property
    def provenance(self) -> SafetySourceLineage:
        if self.source_lineage is None:  # pragma: no cover - closed in validator
            raise SafetyViewError("安全性事实缺少来源谱系")
        return self.source_lineage

    @property
    def source_row_ref(self) -> str:
        return self.source_row_id

    @property
    def fact_version_id(self) -> str:
        """兼容下游按事实版本引用安全性事实。"""

        return self.row_id

    @property
    def numeric_value(self) -> int | float | None:
        return self.value if self.has_numeric_value else None

    @property
    def observed_value(self) -> int | float | None:
        return self.value

    @property
    def has_numeric_value(self) -> bool:
        return (
            self.disclosure_state
            in {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
            and self.value is not None
        )

    @property
    def is_colorable(self) -> bool:
        """颜色投影只允许确定数值或明确报告零值。"""

        return self.has_numeric_value

    @property
    def is_non_numeric_state(self) -> bool:
        return not self.has_numeric_value

    @property
    def is_technical_anomaly(self) -> bool:
        return self.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE

    @property
    def technical_issue(self) -> SafetyTechnicalStatus | str | None:
        return self.technical_status

    @property
    def display_value_zh(self) -> str:
        """用户可见值；非数值状态保留状态文字，不伪造零值。"""

        if self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            return f"0{self.unit or ''}"
        if self.disclosure_state is FactDisclosureState.REPORTED_VALUE:
            if self.value is None:  # pragma: no cover - validator closes this path
                raise SafetyViewError("已报告数值缺少数值")
            return (
                f"{self.value:g}{self.unit or ''}"
                if isinstance(self.value, float)
                else f"{self.value}{self.unit or ''}"
            )
        if self.disclosure_state is FactDisclosureState.BELOW_REPORTING_THRESHOLD and isinstance(
            self.raw_value, str
        ):
            return self.raw_value
        return disclosure_state_label_zh(self.disclosure_state)

    @property
    def disclosure_label_zh(self) -> str:
        return disclosure_state_label_zh(self.disclosure_state)

    @property
    def mapping_is_reliable(self) -> bool:
        return self.term_mapping is not None and self.term_mapping.is_reliable

    @property
    def comparison_term(self) -> str:
        """安全分组身份；不可靠规范映射继续使用来源术语。"""

        if self.term_mapping is not None and self.term_mapping.is_reliable:
            return self.term_mapping.preferred_term or self.source_term
        return self.source_term

    @property
    def display_term(self) -> str:
        """保守显示：来源术语始终可见，可靠规范术语作为附加说明。"""

        if self.standard_term is None:
            return self.source_term
        if self.mapping_is_reliable:
            return f"{self.source_term}（MedDRA PT：{self.standard_term}）"
        return f"{self.source_term}（规范映射待核实：{self.standard_term}）"

    @property
    def event_family(self) -> SafetyFamily:
        return self.family

    @property
    def family_id(self) -> str:
        return self.family.value

    @property
    def event_definition(self) -> str | None:
        return self.event_definition_zh

    @property
    def original_definition(self) -> str | None:
        return self.event_definition_zh

    @property
    def time_window(self) -> str | None:
        return self.time_window_zh

    @property
    def analysis_population(self) -> str | None:
        return self.analysis_population_zh

    @property
    def group_role(self) -> SafetyArmRole:
        return self.arm_role

    @property
    def group_id(self) -> str:
        return self.arm_id

    @property
    def group_label(self) -> str:
        return self.arm_label

    @property
    def reported_value(self) -> int | float | None:
        return self.value

    @property
    def measurement_unit(self) -> str | None:
        return self.unit

    @property
    def source_version(self) -> str:
        return self.source_version_id

    @property
    def source_location(self) -> EvidenceLocator:
        return self.source_locator

    @property
    def state(self) -> FactDisclosureState:
        return self.disclosure_state

    @property
    def value_state(self) -> FactDisclosureState:
        return self.disclosure_state

    @property
    def colorable(self) -> bool:
        return self.is_colorable


SafetyFact = SafetyFactRow
SafetyFactRecord = SafetyFactRow


_NON_CONCRETE_DISCLOSURE_STATES = _NON_CONCRETE_STATES


def validate_safety_fact_row(value: SafetyFactRow | Mapping[str, Any]) -> SafetyFactRow:
    """重新校验安全性事实，防止 ``model_copy(update=...)`` 绕过边界。"""

    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, SafetyFactRow)
            else dict(value)
        )
        return SafetyFactRow.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性事实重新校验失败：{error}") from error


validate_safety_fact = validate_safety_fact_row

__all__ = [
    "ArmRole",
    "DisclosureState",
    "SafetyArmRole",
    "SafetyDisclosureState",
    "SafetyEventFamily",
    "SafetyEventKind",
    "SafetyFamily",
    "SafetyFact",
    "SafetyFactRecord",
    "SafetyFactRow",
    "SafetyMeasurementUnit",
    "SafetyProvenance",
    "SafetySourceLineage",
    "SafetyTechnicalStatus",
    "SafetyTermMap",
    "SafetyTermMapping",
    "SafetyTerminologyMapping",
    "SafetyTermMappingConfidence",
    "SafetyValueState",
    "SafetyViewError",
    "TechnicalStatus",
    "TermMapping",
    "TermMappingConfidence",
    "SourceLineage",
    "disclosure_state_label_zh",
    "safety_disclosure_state_label_zh",
    "safety_technical_status_label_zh",
    "safety_value_state_label_zh",
    "technical_status_label_zh",
    "validate_safety_fact",
    "validate_safety_fact_row",
]

# ── Task 6.3：安全性可比语境与多维热图 ─────────────────────────────────────


def _safety_context_token(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split()).casefold()


def _safety_denominator_semantics(fact: SafetyFactRow) -> str:
    explicit = fact.denominator_semantics_zh
    if explicit is not None:
        return explicit
    unit = _safety_context_token(fact.unit)
    if unit in {"%", "percent", "percentage", "例", "participant_count"}:
        return "受试者分母"
    if unit in {"事件数", "event_count"}:
        return "事件数分母"
    if unit in {"每100患者年", "exposure_adjusted_rate"}:
        return "患者年暴露分母"
    return "来源分母语义未说明"


def _safety_color_value(fact: SafetyFactRow) -> float | None:
    """Return the comparable scalar without turning a state into a value."""

    if not fact.is_colorable or fact.value is None:
        return None
    unit = _safety_context_token(fact.unit)
    if unit in {"例", "participant_count"}:
        if fact.denominator is None:
            return None
        value = float(fact.value) / fact.denominator * 100
    else:
        value = float(fact.value)
    if not math.isfinite(value):
        raise SafetyViewError("安全性热图颜色值必须是有限数值")
    if unit in {"%", "percent", "percentage", "例", "participant_count"} and not 0 <= value <= 100:
        raise SafetyViewError("安全性热图发生率必须位于0至100之间")
    return value


def _safety_context_from_fact(fact: SafetyFactRow) -> SafetyComparableContext:
    required = {
        "时间窗": fact.time_window_zh,
        "分析人群": fact.analysis_population_zh,
        "计量单位": fact.unit,
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        raise SafetyViewError(f"安全性可比语境缺少{'、'.join(missing)}")
    assert fact.time_window_zh is not None
    assert fact.analysis_population_zh is not None
    assert fact.unit is not None
    return SafetyComparableContext(
        event_identity=fact.comparison_term,
        event_family=fact.family,
        term_id=fact.term_id,
        source_term=fact.source_term,
        event_definition_zh=fact.event_definition_zh,
        time_window_zh=fact.time_window_zh,
        analysis_population_zh=fact.analysis_population_zh,
        unit=fact.unit,
        denominator_semantics_zh=_safety_denominator_semantics(fact),
    )


class SafetyComparableContext(BaseModel):
    """同一事件和可比测量语境的闭合键。

    产品、试验和组别故意不属于该键；它们是热图的列维度。这样同一
    事件可以在多个试验列中并列，但不同时间窗、人群、单位或分母语义
    永远不会进入同一色阶。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    event_identity: str = Field(
        validation_alias=AliasChoices(
            "event_identity",
            "event_id",
            "comparison_term",
            "comparison_event",
            "term",
        )
    )
    event_family: SafetyFamily | None = Field(
        default=None,
        validation_alias=AliasChoices("event_family", "family", "safety_family"),
    )
    term_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("term_id", "source_term_id", "event_term_id"),
    )
    source_term: str | None = Field(
        default=None,
        validation_alias=AliasChoices("source_term", "original_term", "raw_term"),
    )
    event_definition_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices("event_definition_zh", "event_definition", "definition_zh"),
    )
    time_window_zh: str = Field(
        validation_alias=AliasChoices(
            "time_window_zh",
            "time_window",
            "original_time_window",
            "assessment_window",
        )
    )
    analysis_population_zh: str = Field(
        validation_alias=AliasChoices(
            "analysis_population_zh",
            "analysis_population",
            "population",
            "population_zh",
        )
    )
    unit: str = Field(validation_alias=AliasChoices("unit", "measurement_unit", "measure_unit"))
    denominator_semantics_zh: str = Field(
        default="来源分母语义未说明",
        validation_alias=AliasChoices(
            "denominator_semantics_zh",
            "denominator_semantics",
            "denominator_definition",
            "denominator_basis",
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _context_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        aliases = {
            "event_id": "event_identity",
            "comparison_term": "event_identity",
            "comparison_event": "event_identity",
            "term": "event_identity",
            "family": "event_family",
            "safety_family": "event_family",
            "source_term_id": "term_id",
            "event_term_id": "term_id",
            "original_term": "source_term",
            "raw_term": "source_term",
            "event_definition": "event_definition_zh",
            "definition_zh": "event_definition_zh",
            "time_window": "time_window_zh",
            "original_time_window": "time_window_zh",
            "assessment_window": "time_window_zh",
            "analysis_population": "analysis_population_zh",
            "population": "analysis_population_zh",
            "population_zh": "analysis_population_zh",
            "measurement_unit": "unit",
            "measure_unit": "unit",
            "denominator_semantics": "denominator_semantics_zh",
            "denominator_definition": "denominator_semantics_zh",
            "denominator_basis": "denominator_semantics_zh",
        }
        for source, target in aliases.items():
            if target not in payload and source in payload:
                payload[target] = payload[source]
            if source != target:
                payload.pop(source, None)
        if "event_identity" not in payload and "term_id" in payload:
            payload["event_identity"] = payload["term_id"]
        return payload

    @field_validator(
        "event_identity",
        "time_window_zh",
        "analysis_population_zh",
        "unit",
        "denominator_semantics_zh",
    )
    @classmethod
    def _context_required_text(cls, value: str) -> str:
        return _text(value, field_name="安全性可比语境字段")

    @field_validator("event_family", mode="before")
    @classmethod
    def _context_family_alias(cls, value: Any) -> Any:
        return _normalize_family(value)

    @field_validator("term_id", "source_term", "event_definition_zh")
    @classmethod
    def _context_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="安全性可比语境可选字段")

    @property
    def family(self) -> SafetyFamily | None:
        return self.event_family

    @property
    def event_id(self) -> str:
        return self.event_identity

    @property
    def time_window(self) -> str:
        return self.time_window_zh

    @property
    def analysis_population(self) -> str:
        return self.analysis_population_zh

    @property
    def measurement_unit(self) -> str:
        return self.unit

    @property
    def denominator_semantics(self) -> str:
        return self.denominator_semantics_zh

    @property
    def identity_key(self) -> tuple[str, ...]:
        """The only key permitted to determine a safety colour scale."""

        family = self.event_family.value if self.event_family is not None else ""
        event = (
            f"{family}:{_safety_context_token(self.event_identity)}"
            if family
            else (_safety_context_token(self.event_identity))
        )
        return (
            event,
            _safety_context_token(self.event_definition_zh),
            _safety_context_token(self.time_window_zh),
            _safety_context_token(self.analysis_population_zh),
            _safety_context_token(self.unit),
            _safety_context_token(self.denominator_semantics_zh),
        )

    @property
    def comparison_key(self) -> tuple[str, ...]:
        return self.identity_key

    @property
    def key(self) -> tuple[str, ...]:
        return self.identity_key

    @property
    def context_id(self) -> str:
        return stable_id("safety-context", *self.identity_key)

    @property
    def comparison_bucket_id(self) -> str:
        return "::".join(self.identity_key)


def _safety_contexts_compatible(
    left: SafetyComparableContext,
    right: SafetyComparableContext,
) -> bool:
    """Allow omitted family/definition metadata only as a filter wildcard."""

    left_key = left.identity_key
    right_key = right.identity_key
    if left_key[2:] != right_key[2:]:
        return False
    if (
        left.event_definition_zh is not None
        and right.event_definition_zh is not None
        and left_key[1] != right_key[1]
    ):
        return False
    if left.event_family is not None and right.event_family is not None:
        return left_key[0] == right_key[0]
    return _safety_context_token(left.event_identity) == _safety_context_token(
        right.event_identity
    )


class SafetyHeatmapCell(BaseModel):
    """一个安全性事实的热图单元；非数值状态永远没有颜色值。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    fact_row: SafetyFactRow = Field(
        validation_alias=AliasChoices("fact_row", "fact", "safety_fact", "record", "row")
    )
    context: SafetyComparableContext | None = None
    numeric_value: int | float | None = Field(
        default=None,
        validation_alias=AliasChoices("numeric_value", "reported_numeric_value"),
    )
    display_value_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices("display_value_zh", "display_value", "value_label_zh"),
    )
    color_value: float | None = Field(
        default=None,
        validation_alias=AliasChoices("color_value", "comparable_value", "heat_value"),
    )
    comparison_rate_percent: float | None = Field(default=None, ge=0, le=100)
    relative_intensity: float | None = Field(
        default=None,
        ge=0,
        le=1,
        validation_alias=AliasChoices("relative_intensity", "color_intensity", "intensity"),
    )

    @model_validator(mode="before")
    @classmethod
    def _cell_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        aliases = {
            "fact": "fact_row",
            "safety_fact": "fact_row",
            "record": "fact_row",
            "row": "fact_row",
            "comparable_value": "color_value",
            "heat_value": "color_value",
            "color_intensity": "relative_intensity",
            "intensity": "relative_intensity",
        }
        for source, target in aliases.items():
            if target not in payload and source in payload:
                payload[target] = payload[source]
            if source != target:
                payload.pop(source, None)
        raw_fact = payload.get("fact_row")
        if raw_fact is not None:
            fact = (
                raw_fact
                if isinstance(raw_fact, SafetyFactRow)
                else validate_safety_fact_row(raw_fact)
            )
            payload["fact_row"] = fact
            if "context" not in payload:
                payload["context"] = _safety_context_from_fact(fact)
        return payload

    @model_validator(mode="after")
    def _cell_integrity(self) -> Self:
        fact = validate_safety_fact_row(self.fact_row)
        object.__setattr__(self, "fact_row", fact)
        expected_context = _safety_context_from_fact(fact)
        if self.context is None:
            object.__setattr__(self, "context", expected_context)
        elif not _safety_contexts_compatible(self.context, expected_context):
            raise ValueError("热图单元不得跨越安全性可比语境")
        expected_numeric = fact.numeric_value
        if self.numeric_value is None:
            object.__setattr__(self, "numeric_value", expected_numeric)
        elif self.numeric_value != expected_numeric:
            raise ValueError("热图单元数值必须由安全性事实确定性派生")
        expected_display = fact.display_value_zh
        if self.display_value_zh is None:
            object.__setattr__(self, "display_value_zh", expected_display)
        elif self.display_value_zh != expected_display:
            raise ValueError("热图单元显示值必须保留安全性事实原文语义")

        expected_color = _safety_color_value(fact)
        unit = _safety_context_token(fact.unit)
        expected_rate = (
            expected_color
            if unit in {"%", "percent", "percentage", "例", "participant_count"}
            else None
        )
        if expected_color is None:
            if self.color_value is not None or self.comparison_rate_percent is not None:
                raise ValueError("非数值披露状态不得携带热图颜色数值")
            if self.relative_intensity is not None:
                raise ValueError("非数值披露状态不得进入热图色阶")
        else:
            if self.color_value is None:
                object.__setattr__(self, "color_value", expected_color)
            elif not math.isclose(self.color_value, expected_color, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError("热图颜色值必须由安全性事实确定性派生")
            if expected_rate is None:
                if self.comparison_rate_percent is not None:
                    raise ValueError("非发生率单位不得携带发生率颜色值")
            elif self.comparison_rate_percent is None:
                object.__setattr__(self, "comparison_rate_percent", expected_rate)
            elif not math.isclose(
                self.comparison_rate_percent,
                expected_rate,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                raise ValueError("热图发生率颜色值必须由安全性事实确定性派生")
        return self

    @property
    def fact(self) -> SafetyFactRow:
        return self.fact_row

    @property
    def row(self) -> SafetyFactRow:
        return self.fact_row

    @property
    def value(self) -> int | float | None:
        return self.fact_row.value

    @property
    def raw_value(self) -> str | int | float | None:
        return self.fact_row.raw_value

    @property
    def display_value(self) -> str:
        if self.display_value_zh is None:  # pragma: no cover - closed in validator
            raise SafetyViewError("安全性热图单元缺少显示值")
        return self.display_value_zh

    @property
    def reported_value(self) -> int | float | None:
        return self.value

    @property
    def disclosure_state(self) -> FactDisclosureState:
        return self.fact_row.disclosure_state

    @property
    def state(self) -> FactDisclosureState:
        return self.disclosure_state

    @property
    def value_state(self) -> FactDisclosureState:
        return self.disclosure_state

    @property
    def disclosure_label_zh(self) -> str:
        return self.fact_row.disclosure_label_zh

    @property
    def is_colorable(self) -> bool:
        return self.fact_row.is_colorable and self.color_value is not None

    @property
    def colorable(self) -> bool:
        return self.is_colorable

    @property
    def is_non_numeric_state(self) -> bool:
        return not self.is_colorable

    @property
    def intensity(self) -> float | None:
        return self.relative_intensity

    @property
    def color_intensity(self) -> float | None:
        return self.relative_intensity

    @property
    def context_key(self) -> tuple[str, ...]:
        if self.context is None:  # pragma: no cover - closed in validator
            raise SafetyViewError("安全性热图单元缺少可比语境")
        return self.context.identity_key

    @property
    def context_id(self) -> str:
        if self.context is None:  # pragma: no cover - closed in validator
            raise SafetyViewError("安全性热图单元缺少可比语境")
        return self.context.context_id

    @property
    def event_identity(self) -> str:
        if self.context is None:  # pragma: no cover - closed in validator
            raise SafetyViewError("安全性热图单元缺少可比语境")
        return self.context.event_identity

    @property
    def product_id(self) -> str:
        return self.fact_row.product_id

    @property
    def trial_id(self) -> str:
        return self.fact_row.trial_id

    @property
    def family(self) -> SafetyFamily:
        return self.fact_row.family

    @property
    def term_id(self) -> str:
        return self.fact_row.term_id

    @property
    def arm_role(self) -> SafetyArmRole:
        return self.fact_row.arm_role

    @property
    def arm_id(self) -> str:
        return self.fact_row.arm_id

    @property
    def arm_label(self) -> str:
        return self.fact_row.arm_label

    @property
    def unit(self) -> str | None:
        return self.fact_row.unit

    @property
    def denominator(self) -> int | None:
        return self.fact_row.denominator

    @property
    def fact_version_id(self) -> str:
        return self.fact_row.row_id

    @property
    def source_row_id(self) -> str:
        return self.fact_row.source_row_id

    @property
    def source_locator(self) -> EvidenceLocator:
        return self.fact_row.source_locator


def _safety_cell_sort_key(cell: SafetyHeatmapCell) -> tuple[str, ...]:
    role_order = "0" if cell.arm_role is SafetyArmRole.TREATMENT else "1"
    return (
        _safety_context_token(cell.product_id),
        cell.product_id,
        _safety_context_token(cell.trial_id),
        cell.trial_id,
        role_order,
        _safety_context_token(cell.arm_id),
        cell.arm_id,
        cell.fact_version_id,
    )


class SafetyArmComparison(BaseModel):
    """同一产品—试验列中的治疗与对照并列事实。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    comparison_id: str
    product_id: str
    trial_id: str
    context: SafetyComparableContext | None = None
    treatment_cells: tuple[SafetyHeatmapCell, ...] = Field(
        default=(),
        validation_alias=AliasChoices("treatment_cells", "treatment", "treatment_arm"),
    )
    control_cells: tuple[SafetyHeatmapCell, ...] = Field(
        default=(),
        validation_alias=AliasChoices("control_cells", "control", "control_arm", "placebo"),
    )

    @model_validator(mode="before")
    @classmethod
    def _comparison_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)

        def _raw_cells(*keys: str) -> tuple[Any, ...]:
            for key in keys:
                if key not in payload or payload[key] is None:
                    continue
                raw = payload[key]
                if isinstance(raw, (str, bytes)):
                    return (raw,)
                try:
                    return tuple(raw) if not isinstance(raw, SafetyHeatmapCell) else (raw,)
                except TypeError:
                    return (raw,)
            return ()

        treatment = _raw_cells("treatment_cells", "treatment", "treatment_arm")
        control = _raw_cells("control_cells", "control", "control_arm", "placebo")
        if treatment:
            payload["treatment_cells"] = treatment
        if control:
            payload["control_cells"] = control
        for source in ("treatment", "treatment_arm", "control", "control_arm", "placebo"):
            payload.pop(source, None)
        cells = (*treatment, *control)
        if cells:
            first = cells[0]
            first_cell = (
                first
                if isinstance(first, SafetyHeatmapCell)
                else SafetyHeatmapCell.model_validate(first)
            )
            payload.setdefault("product_id", first_cell.product_id)
            payload.setdefault("trial_id", first_cell.trial_id)
            payload.setdefault("context", first_cell.context)
            if "comparison_id" not in payload:
                context = first_cell.context
                if context is None:  # pragma: no cover - cell validator closes this
                    raise ValueError("安全性并列关系缺少可比语境")
                payload["comparison_id"] = stable_id(
                    "safety-comparison",
                    first_cell.product_id,
                    first_cell.trial_id,
                    context.context_id,
                )
        return payload

    @field_validator("treatment_cells", "control_cells", mode="before")
    @classmethod
    def _comparison_cells_tuple(cls, value: Any) -> tuple[Any, ...]:
        if value is None:
            return ()
        if isinstance(value, SafetyHeatmapCell):
            return (value,)
        if isinstance(value, (str, bytes)):
            return (value,)
        try:
            return tuple(value)
        except TypeError:
            return (value,)

    @field_validator("comparison_id", "product_id", "trial_id")
    @classmethod
    def _comparison_required_text(cls, value: str) -> str:
        return _text(value, field_name="安全性并列关系字段")

    @model_validator(mode="after")
    def _comparison_integrity(self) -> Self:
        cells = (*self.treatment_cells, *self.control_cells)
        if not cells:
            raise ValueError("安全性治疗—对照并列关系至少需要一条事实")
        first = cells[0]
        expected_context = first.context
        if expected_context is None:  # pragma: no cover - closed by cell validator
            raise ValueError("安全性并列关系缺少可比语境")
        if self.context is None:
            object.__setattr__(self, "context", expected_context)
        elif not _safety_contexts_compatible(self.context, expected_context):
            raise ValueError("安全性并列关系不得跨越可比语境")
        row_ids = tuple(cell.fact_version_id for cell in cells)
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("安全性并列关系不得重复引用事实行")
        for cell in cells:
            if (
                cell.product_id != self.product_id
                or cell.trial_id != self.trial_id
                or cell.context_key != expected_context.identity_key
            ):
                raise ValueError("安全性并列关系不得跨越产品、试验或可比语境")
        if any(cell.arm_role is not SafetyArmRole.TREATMENT for cell in self.treatment_cells):
            raise ValueError("治疗列必须绑定治疗臂事实")
        if any(cell.arm_role is not SafetyArmRole.CONTROL for cell in self.control_cells):
            raise ValueError("对照列必须绑定对照臂事实")
        return self

    @property
    def treatment(self) -> SafetyHeatmapCell | None:
        return self.treatment_cells[0] if self.treatment_cells else None

    @property
    def control(self) -> SafetyHeatmapCell | None:
        return self.control_cells[0] if self.control_cells else None

    @property
    def rows(self) -> tuple[SafetyHeatmapCell, ...]:
        return (*self.treatment_cells, *self.control_cells)

    @property
    def cells(self) -> tuple[SafetyHeatmapCell, ...]:
        return self.rows

    @property
    def treatment_rows(self) -> tuple[SafetyHeatmapCell, ...]:
        return self.treatment_cells

    @property
    def control_rows(self) -> tuple[SafetyHeatmapCell, ...]:
        return self.control_cells

    @property
    def has_both_arms(self) -> bool:
        return bool(self.treatment_cells) and bool(self.control_cells)

    @property
    def is_drawable(self) -> bool:
        return self.has_both_arms and any(cell.is_colorable for cell in self.rows)

    @property
    def has_renderable_values(self) -> bool:
        return any(cell.numeric_value is not None for cell in self.rows)

    @property
    def source_row_ids(self) -> tuple[str, ...]:
        return tuple(cell.source_row_id for cell in self.rows)


SafetyComparison = SafetyArmComparison
SafetyHeatmapComparison = SafetyArmComparison


class SafetyHeatmapView(BaseModel):
    """一个可比语境的多维热图：产品—试验—组别是并列列维度。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    context: SafetyComparableContext
    cells: tuple[SafetyHeatmapCell, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("cells", "rows", "heatmap_cells"),
    )
    comparisons: tuple[SafetyArmComparison, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _view_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        if "cells" not in payload:
            for key in ("rows", "heatmap_cells"):
                if key in payload:
                    payload["cells"] = payload[key]
                    break
        payload.pop("rows", None)
        payload.pop("heatmap_cells", None)
        if "cells" not in payload and payload.get("comparisons"):
            raw_comparisons = payload["comparisons"]
            comparisons = (
                raw_comparisons
                if isinstance(raw_comparisons, (list, tuple))
                else (raw_comparisons,)
            )
            cells: list[Any] = []
            for comparison in comparisons:
                parsed = (
                    comparison
                    if isinstance(comparison, SafetyArmComparison)
                    else SafetyArmComparison.model_validate(comparison)
                )
                cells.extend(parsed.rows)
            payload["cells"] = tuple(cells)
        if "context" not in payload and payload.get("cells"):
            first = payload["cells"][0]
            cell = (
                first
                if isinstance(first, SafetyHeatmapCell)
                else SafetyHeatmapCell.model_validate(first)
            )
            payload["context"] = cell.context
        return payload

    @field_validator("cells", "comparisons", mode="before")
    @classmethod
    def _view_tuple(cls, value: Any) -> tuple[Any, ...]:
        if value is None:
            return ()
        if isinstance(value, (str, bytes)):
            return (value,)
        try:
            return tuple(value)
        except TypeError:
            return (value,)

    @model_validator(mode="after")
    def _view_integrity(self) -> Self:
        cells = tuple(
            SafetyHeatmapCell.model_validate(
                cell.model_dump(mode="python", warnings=False)
                if isinstance(cell, SafetyHeatmapCell)
                else cell
            )
            for cell in self.cells
        )
        object.__setattr__(self, "cells", cells)
        if any(
            cell.context is None or not _safety_contexts_compatible(cell.context, self.context)
            for cell in cells
        ):
            raise ValueError("热图视图不得合并不同安全性可比语境")
        row_ids = tuple(cell.fact_version_id for cell in cells)
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("热图视图不得包含重复事实行")

        comparisons = self.comparisons
        if not comparisons:
            comparisons = _build_safety_comparisons(cells)
            object.__setattr__(self, "comparisons", comparisons)
        canonical_cells = {cell.fact_version_id: cell for cell in cells}
        for comparison in comparisons:
            for comparison_cell in comparison.rows:
                canonical = canonical_cells.get(comparison_cell.fact_version_id)
                if canonical is None or canonical != comparison_cell:
                    raise ValueError("热图并列关系不得复制或篡改事实单元")
        comparison_rows = tuple(
            cell.fact_version_id for comparison in comparisons for cell in comparison.rows
        )
        if len(set(comparison_rows)) != len(comparison_rows) or set(comparison_rows) != set(
            row_ids
        ):
            raise ValueError("热图并列关系必须完整且唯一覆盖全部事实行")
        comparison_keys: set[tuple[str, str]] = set()
        for comparison in comparisons:
            if comparison.context is None or not _safety_contexts_compatible(
                comparison.context, self.context
            ):
                raise ValueError("热图并列关系不得越过可比语境")
            key = (comparison.product_id, comparison.trial_id)
            if key in comparison_keys:
                raise ValueError("同一产品和试验不得拆成多个热图列")
            comparison_keys.add(key)
        return self

    @property
    def rows(self) -> tuple[SafetyHeatmapCell, ...]:
        return self.cells

    @property
    def heatmap_cells(self) -> tuple[SafetyHeatmapCell, ...]:
        return self.cells

    @property
    def fact_rows(self) -> tuple[SafetyFactRow, ...]:
        return tuple(cell.fact_row for cell in self.cells)

    @property
    def trial_columns(self) -> tuple[SafetyArmComparison, ...]:
        return self.comparisons

    @property
    def columns(self) -> tuple[SafetyArmComparison, ...]:
        return self.comparisons

    @property
    def product_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(comparison.product_id for comparison in self.comparisons))

    @property
    def trial_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(comparison.trial_id for comparison in self.comparisons))

    @property
    def has_color_scale(self) -> bool:
        return any(cell.relative_intensity is not None for cell in self.cells)

    @property
    def has_renderable_values(self) -> bool:
        return any(cell.is_colorable for cell in self.cells)

    @property
    def has_parallel_arms(self) -> bool:
        return all(comparison.has_both_arms for comparison in self.comparisons)

    @property
    def source_row_ids(self) -> tuple[str, ...]:
        return tuple(cell.source_row_id for cell in self.cells)

    @property
    def context_key(self) -> tuple[str, ...]:
        return self.context.identity_key

    @property
    def is_ranked(self) -> bool:
        return False


SafetyHeatmap = SafetyHeatmapView


def _build_safety_comparisons(
    cells: Sequence[SafetyHeatmapCell],
) -> tuple[SafetyArmComparison, ...]:
    grouped: dict[tuple[str, str], list[SafetyHeatmapCell]] = {}
    for cell in cells:
        grouped.setdefault((cell.product_id, cell.trial_id), []).append(cell)
    comparisons: list[SafetyArmComparison] = []
    for product_id, trial_id in sorted(
        grouped,
        key=lambda value: (
            _safety_context_token(value[0]),
            value[0],
            _safety_context_token(value[1]),
            value[1],
        ),
    ):
        candidates = tuple(sorted(grouped[(product_id, trial_id)], key=_safety_cell_sort_key))
        treatment = tuple(cell for cell in candidates if cell.arm_role is SafetyArmRole.TREATMENT)
        control = tuple(cell for cell in candidates if cell.arm_role is SafetyArmRole.CONTROL)
        if not treatment and not control:
            raise SafetyViewError("安全性并列列缺少治疗或对照事实")
        context = candidates[0].context
        if context is None:  # pragma: no cover - closed by cell validator
            raise SafetyViewError("安全性并列列缺少可比语境")
        try:
            comparisons.append(
                SafetyArmComparison(
                    comparison_id=stable_id(
                        "safety-comparison",
                        product_id,
                        trial_id,
                        context.context_id,
                    ),
                    product_id=product_id,
                    trial_id=trial_id,
                    context=context,
                    treatment_cells=treatment,
                    control_cells=control,
                )
            )
        except (TypeError, ValueError, ValidationError) as error:
            raise SafetyViewError(f"安全性治疗—对照并列关系构建失败：{error}") from error
    return tuple(comparisons)


def _safety_event_key(fact: SafetyFactRow) -> str:
    """Return a stable event identity without using an observed value."""

    identity = fact.comparison_term if fact.mapping_is_reliable else fact.term_id
    if not identity:
        identity = fact.source_term
    return f"{fact.family.value}:{_safety_context_token(identity)}"


def _safety_event_reference_tokens(fact: SafetyFactRow) -> frozenset[str]:
    values = {
        _safety_context_token(_safety_event_key(fact)),
        _safety_context_token(fact.term_id),
        _safety_context_token(fact.source_term),
        _safety_context_token(fact.comparison_term),
    }
    return frozenset(value for value in values if value)


def _safety_selection_tokens(
    value: Iterable[str] | Mapping[str, bool] | str | None,
) -> frozenset[str]:
    if value is None:
        return frozenset()
    values: Iterable[Any]
    if isinstance(value, Mapping):
        values = (key for key, enabled in value.items() if enabled)
    elif isinstance(value, str):
        values = (value,)
    else:
        values = value
    return frozenset(
        _safety_context_token(item) for item in values if isinstance(item, str) and item.strip()
    )


def _safety_reference_is_selected(
    fact: SafetyFactRow,
    selected_tokens: frozenset[str],
) -> bool:
    return bool(_safety_event_reference_tokens(fact) & selected_tokens)


def _safety_mapping_value(
    mapping: Mapping[str, int | float] | None,
    facts: Sequence[SafetyFactRow],
    event_key: str,
) -> int | float | None:
    if mapping is None:
        return None
    normalized = {
        _safety_context_token(key): value for key, value in mapping.items() if isinstance(key, str)
    }
    references = {_safety_context_token(event_key)}
    references.update(
        _safety_context_token(reference)
        for fact in facts
        if _safety_event_key(fact) == event_key
        for reference in (fact.term_id, fact.source_term, fact.comparison_term)
    )
    for reference in references:
        if reference in normalized:
            value = normalized[reference]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SafetyViewError("安全性事件频率标记必须是有限数值")
            if not math.isfinite(float(value)):
                raise SafetyViewError("安全性事件频率标记必须是有限数值")
            return value
    return None


class SafetyEventSelection(BaseModel):
    """安全性默认事件子集与完整事件集的可逆视图状态。

    ``selected_rows`` 只控制默认视图；``complete_rows`` 永远保存当前筛选
    下的完整事实集。两者都按稳定事实身份排列，不使用发生率作为排序键。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    default_dimensions: tuple[SafetyFamily, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "default_dimensions",
            "dimensions",
            "safety_dimensions",
        ),
    )
    selected_event_keys: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "selected_event_keys",
            "event_keys",
            "selected_events",
            "common_ae_event_keys",
        ),
    )
    selected_rows: tuple[SafetyFactRow, ...] = Field(
        default=(),
        validation_alias=AliasChoices("selected_rows", "default_rows", "rows"),
    )
    complete_rows: tuple[SafetyFactRow, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "complete_rows",
            "complete_event_rows",
            "all_rows",
            "fact_rows",
        ),
    )
    selection_limit: int = Field(default=_DEFAULT_COMMON_AE_LIMIT, ge=1, le=1000)
    eligibility_reasons_by_event: tuple[tuple[str, tuple[str, ...]], ...] = ()
    search_query: str | None = None
    expanded: bool = False
    ranked: bool = False

    @field_validator(
        "default_dimensions",
        "selected_event_keys",
        "selected_rows",
        "complete_rows",
        "eligibility_reasons_by_event",
        mode="before",
    )
    @classmethod
    def _selection_tuples(cls, value: Any) -> tuple[Any, ...]:
        return _as_tuple(value)

    @field_validator("default_dimensions", mode="before")
    @classmethod
    def _selection_dimensions(cls, value: Any) -> Any:
        return tuple(_normalize_family(item) for item in _as_tuple(value))

    @field_validator("selected_event_keys", mode="before")
    @classmethod
    def _selection_event_keys(cls, value: Any) -> tuple[str, ...]:
        return tuple(_text(item, field_name="默认安全性事件标识") for item in _as_tuple(value))

    @field_validator("search_query")
    @classmethod
    def _selection_search_query(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, field_name="安全性事件搜索词")

    @model_validator(mode="after")
    def _selection_integrity(self) -> Self:
        dimensions = tuple(self.default_dimensions)
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("默认安全性维度不得重复")
        selected_keys = tuple(self.selected_event_keys)
        if len(set(selected_keys)) != len(selected_keys):
            raise ValueError("默认安全性事件不得重复")
        complete_ids = tuple(row.row_id for row in self.complete_rows)
        selected_ids = tuple(row.row_id for row in self.selected_rows)
        if len(set(complete_ids)) != len(complete_ids):
            raise ValueError("完整安全性事件集不得包含重复事实行")
        if len(set(selected_ids)) != len(selected_ids):
            raise ValueError("默认安全性事件集不得包含重复事实行")
        if not set(selected_ids) <= set(complete_ids):
            raise ValueError("默认安全性事件集必须来自完整事实集")
        common_selected_keys = {
            _safety_event_key(row)
            for row in self.selected_rows
            if row.family is SafetyFamily.COMMON_AE
        }
        if common_selected_keys != set(selected_keys):
            raise ValueError("默认常见不良事件标识必须完整覆盖默认行")
        reason_keys = tuple(key for key, _ in self.eligibility_reasons_by_event)
        if len(set(reason_keys)) != len(reason_keys) or not set(reason_keys) <= set(selected_keys):
            raise ValueError("默认安全性事件选择原因必须对应已选事件")
        if self.ranked:
            raise ValueError("安全性默认事件视图不得启用排名")
        return self

    @property
    def dimensions(self) -> tuple[SafetyFamily, ...]:
        return self.default_dimensions

    @property
    def selected(self) -> tuple[SafetyFactRow, ...]:
        return self.selected_rows

    @property
    def rows(self) -> tuple[SafetyFactRow, ...]:
        return self.selected_rows

    @property
    def fact_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.selected_rows

    @property
    def complete_event_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.complete_rows

    @property
    def all_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.complete_rows

    @property
    def event_keys(self) -> tuple[str, ...]:
        return self.selected_event_keys

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                row.term_id for row in self.selected_rows if row.family is SafetyFamily.COMMON_AE
            )
        )

    @property
    def common_ae_event_keys(self) -> tuple[str, ...]:
        return self.selected_event_keys

    @property
    def common_ae_term_ids(self) -> tuple[str, ...]:
        return self.event_ids

    @property
    def is_expanded(self) -> bool:
        return self.expanded or self.search_query is not None

    @property
    def is_ranked(self) -> bool:
        return False

    @property
    def has_safety_ranking(self) -> bool:
        return False

    def expand(self, query: str | None = None, **filters: Any) -> tuple[SafetyFactRow, ...]:
        return expand_safety_events(self.complete_rows, query=query, **filters)

    def search(self, query: str, **filters: Any) -> tuple[SafetyFactRow, ...]:
        return search_safety_events(self.complete_rows, query, **filters)

    def __len__(self) -> int:
        return len(self.selected_rows)


SafetyDefaultEventSelection = SafetyEventSelection
SafetyDefaultSelection = SafetyEventSelection
SafetyCompleteAEView = SafetyEventSelection


class SafetyViewSet(BaseModel):
    """同源安全性事实与热图集合；不以视图选择删除事实。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    fact_rows: tuple[SafetyFactRow, ...] = Field(
        default=(),
        validation_alias=AliasChoices("fact_rows", "facts", "rows"),
    )
    heatmap_views: tuple[SafetyHeatmapView, ...] = Field(
        default=(),
        validation_alias=AliasChoices("heatmap_views", "heatmaps", "views"),
    )
    default_selection: SafetyEventSelection | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "default_selection",
            "event_selection",
            "safety_selection",
        ),
    )

    @field_validator("fact_rows", "heatmap_views", mode="before")
    @classmethod
    def _set_tuple(cls, value: Any) -> tuple[Any, ...]:
        if value is None:
            return ()
        if isinstance(value, (str, bytes)):
            return (value,)
        try:
            return tuple(value)
        except TypeError:
            return (value,)

    @model_validator(mode="after")
    def _set_integrity(self) -> Self:
        facts = tuple(validate_safety_fact_row(fact) for fact in self.fact_rows)
        views = tuple(
            validate_safety_heatmap_view(
                view.model_dump(mode="python", warnings=False)
                if isinstance(view, SafetyHeatmapView)
                else view
            )
            for view in self.heatmap_views
        )
        object.__setattr__(self, "fact_rows", facts)
        object.__setattr__(self, "heatmap_views", views)
        fact_by_id = {fact.row_id: fact for fact in facts}
        if len(fact_by_id) != len(facts):
            raise ValueError("安全性事实集合不得包含重复行标识")
        view_row_ids: list[str] = []
        for view in self.heatmap_views:
            for cell in view.cells:
                fact = fact_by_id.get(cell.fact_version_id)
                if fact is None:
                    raise ValueError("安全性热图不得引用集合外事实行")
                if fact != cell.fact_row:
                    raise ValueError("安全性热图不得复制或篡改事实行")
                view_row_ids.append(cell.fact_version_id)
        if len(view_row_ids) != len(set(view_row_ids)):
            raise ValueError("安全性热图不得跨视图重复引用事实行")
        if set(view_row_ids) != set(fact_by_id):
            raise ValueError("安全性热图必须完整覆盖事实集合")

        selection = self.default_selection
        if selection is None:
            selection = select_default_safety_events(facts)
        selection_ids = {row.row_id for row in selection.complete_rows}
        if selection_ids != set(fact_by_id):
            raise ValueError("安全性默认视图必须保留完整事件事实集")
        selected_by_id = {row.row_id: row for row in selection.selected_rows}
        if any(fact_by_id[row_id] != row for row_id, row in selected_by_id.items()):
            raise ValueError("安全性默认视图不得复制或篡改事实行")
        object.__setattr__(self, "default_selection", selection)
        return self

    @property
    def facts(self) -> tuple[SafetyFactRow, ...]:
        return self.fact_rows

    @property
    def heatmaps(self) -> tuple[SafetyHeatmapView, ...]:
        return self.heatmap_views

    @property
    def views(self) -> tuple[SafetyHeatmapView, ...]:
        return self.heatmap_views

    @property
    def all_cells(self) -> tuple[SafetyHeatmapCell, ...]:
        return tuple(cell for view in self.heatmap_views for cell in view.cells)

    @property
    def selection(self) -> SafetyEventSelection:
        if self.default_selection is None:  # pragma: no cover - closed in validator
            raise SafetyViewError("安全性视图集合缺少默认事件选择")
        return self.default_selection

    @property
    def default_dimensions(self) -> tuple[SafetyFamily, ...]:
        return self.selection.default_dimensions

    @property
    def default_event_keys(self) -> tuple[str, ...]:
        return self.selection.selected_event_keys

    @property
    def default_event_ids(self) -> tuple[str, ...]:
        return self.selection.event_ids

    @property
    def default_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.selection.selected_rows

    @property
    def default_fact_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.selection.selected_rows

    @property
    def default_common_ae_rows(self) -> tuple[SafetyFactRow, ...]:
        return tuple(
            row for row in self.selection.selected_rows if row.family is SafetyFamily.COMMON_AE
        )

    @property
    def complete_event_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.fact_rows

    @property
    def full_event_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.fact_rows

    @property
    def all_event_rows(self) -> tuple[SafetyFactRow, ...]:
        return self.fact_rows

    @property
    def is_ranked(self) -> bool:
        return False

    @property
    def has_safety_ranking(self) -> bool:
        return False

    def expand_events(
        self,
        query: str | None = None,
        **filters: Any,
    ) -> tuple[SafetyFactRow, ...]:
        return expand_safety_events(self.fact_rows, query=query, **filters)

    def search_events(
        self,
        query: str,
        **filters: Any,
    ) -> tuple[SafetyFactRow, ...]:
        return search_safety_events(self.fact_rows, query, **filters)

    def __len__(self) -> int:
        return len(self.fact_rows)


SafetyViews = SafetyViewSet
SafetyHeatmapSet = SafetyViewSet
SafetyViewCollection = SafetyViewSet


def _validated_safety_context(
    value: SafetyComparableContext | Mapping[str, Any] | Sequence[str],
) -> SafetyComparableContext:
    if isinstance(value, SafetyComparableContext):
        raw = value.model_dump(mode="python", warnings=False)
    elif isinstance(value, Mapping):
        raw = dict(value)
    else:
        parts = tuple(value)
        if len(parts) == 5:
            raw = {
                "event_identity": parts[0],
                "time_window_zh": parts[1],
                "analysis_population_zh": parts[2],
                "unit": parts[3],
                "denominator_semantics_zh": parts[4],
            }
        elif len(parts) == 6:
            raw = {
                "event_family": parts[0],
                "event_identity": parts[1],
                "time_window_zh": parts[2],
                "analysis_population_zh": parts[3],
                "unit": parts[4],
                "denominator_semantics_zh": parts[5],
            }
        else:
            raise SafetyViewError("安全性可比语境键必须包含5或6个字段")
    try:
        return SafetyComparableContext.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性可比语境无效：{error}") from error


def _safety_fact_sort_key(fact: SafetyFactRow) -> tuple[str, ...]:
    role_order = "0" if fact.arm_role is SafetyArmRole.TREATMENT else "1"
    return (
        _safety_context_token(fact.product_id),
        fact.product_id,
        _safety_context_token(fact.trial_id),
        fact.trial_id,
        _safety_context_token(fact.comparison_term),
        _safety_context_token(fact.time_window_zh),
        _safety_context_token(fact.analysis_population_zh),
        _safety_context_token(fact.unit),
        role_order,
        _safety_context_token(fact.arm_id),
        fact.arm_id,
        fact.row_id,
    )


def _validated_safety_rows(
    value: Sequence[SafetyFactRow | Mapping[str, Any]],
) -> tuple[SafetyFactRow, ...]:
    try:
        rows = tuple(validate_safety_fact_row(item) for item in value)
    except SafetyViewError:
        raise
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性事件输入无效：{error}") from error
    if len({row.row_id for row in rows}) != len(rows):
        raise SafetyViewError("安全性事件输入包含重复 row_id")
    return rows


def default_safety_dimensions(
    facts: Sequence[SafetyFactRow | Mapping[str, Any]] | None = None,
) -> tuple[SafetyFamily, ...]:
    """Return the fixed dimensions plus optional dimensions with source data."""

    if facts is None:
        present: set[SafetyFamily] = set()
    else:
        present = {row.family for row in _validated_safety_rows(facts)}
    return (
        *DEFAULT_SAFETY_DIMENSIONS,
        *(family for family in OPTIONAL_SAFETY_DIMENSIONS if family in present),
    )


get_default_safety_dimensions = default_safety_dimensions
default_safety_families = default_safety_dimensions
select_default_safety_dimensions = default_safety_dimensions


def _safety_is_rate_measurement(fact: SafetyFactRow) -> bool:
    return _safety_context_token(fact.unit) in {
        "%",
        "percent",
        "percentage",
        "例",
        "participant_count",
    }


def _safety_common_ae_difference(
    rows: Sequence[SafetyFactRow],
    event_key: str,
) -> float | None:
    by_context: dict[tuple[str, str, tuple[str, ...]], list[SafetyFactRow]] = {}
    for row in rows:
        if _safety_event_key(row) != event_key or not _safety_is_rate_measurement(row):
            continue
        context = _safety_context_from_fact(row)
        key = (row.product_id, row.trial_id, context.identity_key)
        by_context.setdefault(key, []).append(row)
    differences: list[float] = []
    for candidates in by_context.values():
        treatment = tuple(
            value
            for row in candidates
            if row.arm_role is SafetyArmRole.TREATMENT
            for value in (_safety_color_value(row),)
            if value is not None
        )
        control = tuple(
            value
            for row in candidates
            if row.arm_role is SafetyArmRole.CONTROL
            for value in (_safety_color_value(row),)
            if value is not None
        )
        differences.extend(abs(left - right) for left in treatment for right in control)
    return max(differences, default=None)


def select_default_safety_events(
    facts: Sequence[SafetyFactRow | Mapping[str, Any]],
    *,
    clinically_important_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    important_event_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    adapter_marked_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    high_frequency_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    source_frequency_by_event: Mapping[str, int | float] | None = None,
    frequency_by_event: Mapping[str, int | float] | None = None,
    source_frequency_threshold: int | float = 2,
    minimum_treatment_rate_percent: int | float = _COMMON_AE_RATE_THRESHOLD_PERCENT,
    minimum_treatment_control_difference_percent: int | float = (
        _COMMON_AE_DIFFERENCE_THRESHOLD_PERCENT
    ),
    common_ae_limit: int = _DEFAULT_COMMON_AE_LIMIT,
    max_common_ae_events: int | None = None,
) -> SafetyEventSelection:
    """Select a stable common-AE subset while retaining every source row.

    Eligibility is the union of source frequency, a treatment rate of at
    least 5 percent, a treatment-control absolute difference of at least five
    percentage points, and explicit project-adapter importance. Values are
    used only for eligibility; selected events are ordered by stable identity,
    never by risk magnitude.
    """

    rows = _validated_safety_rows(facts)
    if max_common_ae_events is not None:
        if common_ae_limit != _DEFAULT_COMMON_AE_LIMIT and common_ae_limit != max_common_ae_events:
            raise SafetyViewError("常见不良事件选择上限参数互相冲突")
        common_ae_limit = max_common_ae_events
    if isinstance(common_ae_limit, bool) or not isinstance(common_ae_limit, int):
        raise SafetyViewError("常见不良事件选择上限必须是整数")
    if common_ae_limit < 1:
        raise SafetyViewError("常见不良事件选择上限必须为正数")

    numeric_thresholds = (
        ("来源频率", source_frequency_threshold),
        ("治疗组发生率阈值", minimum_treatment_rate_percent),
        ("治疗—对照差值阈值", minimum_treatment_control_difference_percent),
    )
    for label, value in numeric_thresholds:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SafetyViewError(f"{label}必须是有限数值")
        if not math.isfinite(float(value)) or value < 0:
            raise SafetyViewError(f"{label}必须是有限非负数值")

    important_tokens = (
        _safety_selection_tokens(clinically_important_terms)
        | _safety_selection_tokens(important_event_terms)
        | _safety_selection_tokens(adapter_marked_terms)
    )
    frequent_tokens = _safety_selection_tokens(high_frequency_terms)
    frequency_mapping = source_frequency_by_event
    if (
        frequency_mapping is not None
        and frequency_by_event is not None
        and dict(frequency_mapping) != dict(frequency_by_event)
    ):
        raise SafetyViewError("安全性事件频率参数互相冲突")
    if frequency_mapping is None:
        frequency_mapping = frequency_by_event

    common_rows = tuple(row for row in rows if row.family is SafetyFamily.COMMON_AE)
    by_event: dict[str, list[SafetyFactRow]] = {}
    for row in common_rows:
        by_event.setdefault(_safety_event_key(row), []).append(row)

    selected_candidates: list[tuple[str, bool]] = []
    reason_by_event: dict[str, tuple[str, ...]] = {}
    for event_key in sorted(by_event):
        event_rows = tuple(by_event[event_key])
        source_frequency_value = _safety_mapping_value(
            frequency_mapping,
            event_rows,
            event_key,
        )
        source_frequency = (
            float(source_frequency_value) if source_frequency_value is not None else None
        )
        if source_frequency is not None and not math.isfinite(source_frequency):
            raise SafetyViewError("安全性事件来源频率必须是有限数值")
        high_frequency = (
            event_key in frequent_tokens
            or any(
                token in frequent_tokens
                for row in event_rows
                for token in _safety_event_reference_tokens(row)
            )
            or (
                source_frequency is not None
                and source_frequency >= float(source_frequency_threshold)
            )
        )
        treatment_rates = tuple(
            value
            for row in event_rows
            if row.arm_role is SafetyArmRole.TREATMENT and _safety_is_rate_measurement(row)
            for value in (_safety_color_value(row),)
            if value is not None
        )
        treatment_rate = max(treatment_rates, default=None)
        rate_criterion = treatment_rate is not None and treatment_rate >= float(
            minimum_treatment_rate_percent
        )
        difference = _safety_common_ae_difference(rows, event_key)
        difference_criterion = difference is not None and difference >= float(
            minimum_treatment_control_difference_percent
        )
        important = bool(
            important_tokens
            and any(_safety_reference_is_selected(row, important_tokens) for row in event_rows)
        )
        reasons = tuple(
            reason
            for enabled, reason in (
                (high_frequency, "来源高频"),
                (rate_criterion, "治疗组发生率≥5%"),
                (difference_criterion, "治疗—对照绝对差≥5个百分点"),
                (important, "项目适配器标记临床重要"),
            )
            if enabled
        )
        if reasons:
            selected_candidates.append((event_key, important))
            reason_by_event[event_key] = reasons

    # Explicit clinical-importance marks are retained first so a source
    # adapter signal is not silently discarded by the display-size cap. Within
    # each eligibility class, event identity is the only ordering key.
    ordered_candidates = tuple(
        event_key
        for event_key, _ in sorted(
            selected_candidates,
            key=lambda item: (0 if item[1] else 1, item[0]),
        )
    )
    selected_event_keys = ordered_candidates[:common_ae_limit]
    dimensions = default_safety_dimensions(rows)
    selected_key_set = set(selected_event_keys)
    selected_rows = tuple(
        sorted(
            (
                row
                for row in rows
                if row.family in dimensions
                and (
                    row.family is not SafetyFamily.COMMON_AE
                    or _safety_event_key(row) in selected_key_set
                )
            ),
            key=_safety_fact_sort_key,
        )
    )
    complete_rows = tuple(sorted(rows, key=_safety_fact_sort_key))
    try:
        return SafetyEventSelection(
            default_dimensions=dimensions,
            selected_event_keys=selected_event_keys,
            selected_rows=selected_rows,
            complete_rows=complete_rows,
            selection_limit=common_ae_limit,
            eligibility_reasons_by_event=tuple(
                (event_key, reason_by_event[event_key]) for event_key in selected_event_keys
            ),
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"默认安全性事件选择构建失败：{error}") from error


select_default_safety_event_rows = select_default_safety_events
build_default_safety_selection = select_default_safety_events


def search_safety_events(
    value: SafetyViewSet | SafetyEventSelection | Sequence[SafetyFactRow | Mapping[str, Any]],
    query: str,
    *,
    family: SafetyFamily | str | None = None,
    product_id: str | None = None,
    trial_id: str | None = None,
) -> tuple[SafetyFactRow, ...]:
    """Search the complete event set and return every row for matching events."""

    if isinstance(value, SafetyViewSet):
        source_rows: Sequence[SafetyFactRow | Mapping[str, Any]] = value.fact_rows
    elif isinstance(value, SafetyEventSelection):
        source_rows = value.complete_rows
    else:
        source_rows = value
    rows = _validated_safety_rows(source_rows)
    if not isinstance(query, str):
        raise SafetyViewError("安全性事件搜索词必须是文本")
    normalized_query = " ".join(query.split()).casefold()
    requested_family: SafetyFamily | None = None
    if family is not None:
        try:
            requested_family = SafetyFamily(_normalize_family(family))
        except (TypeError, ValueError) as error:
            raise SafetyViewError(f"安全性事件族筛选无效：{family!r}") from error
    for label, identifier in (("产品", product_id), ("试验", trial_id)):
        if identifier is not None and not isinstance(identifier, str):
            raise SafetyViewError(f"安全性事件{label}筛选必须是文本")
    filtered = tuple(
        row
        for row in rows
        if (requested_family is None or row.family is requested_family)
        and (product_id is None or row.product_id == product_id)
        and (trial_id is None or row.trial_id == trial_id)
    )
    if normalized_query:
        matched_keys = {
            _safety_event_key(row)
            for row in filtered
            if normalized_query
            in " ".join(
                _safety_context_token(value)
                for value in (
                    row.term_id,
                    row.source_term,
                    row.standard_term,
                    row.comparison_term,
                    row.event_definition_zh,
                    row.family.value,
                    _SAFETY_FAMILY_LABELS_ZH[row.family],
                )
                if value is not None
            )
        }
        filtered = tuple(row for row in filtered if _safety_event_key(row) in matched_keys)
    return tuple(sorted(filtered, key=_safety_fact_sort_key))


def expand_safety_events(
    value: SafetyViewSet | SafetyEventSelection | Sequence[SafetyFactRow | Mapping[str, Any]],
    query: str | None = None,
    *,
    family: SafetyFamily | str | None = None,
    product_id: str | None = None,
    trial_id: str | None = None,
) -> tuple[SafetyFactRow, ...]:
    """Expand the complete event table, optionally narrowed by a search term."""

    return search_safety_events(
        value,
        "" if query is None else query,
        family=family,
        product_id=product_id,
        trial_id=trial_id,
    )


search_safety_event_rows = search_safety_events
expand_safety_event_rows = expand_safety_events
expand_complete_safety_events = expand_safety_events


def build_safety_views(
    facts: Sequence[SafetyFactRow | Mapping[str, Any]],
    *,
    context: SafetyComparableContext | Mapping[str, Any] | Sequence[str] | None = None,
    comparable_context: SafetyComparableContext | Mapping[str, Any] | Sequence[str] | None = None,
    context_key: SafetyComparableContext | Mapping[str, Any] | Sequence[str] | None = None,
    product_id: str | None = None,
    trial_id: str | None = None,
    clinically_important_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    important_event_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    adapter_marked_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    high_frequency_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    source_frequency_by_event: Mapping[str, int | float] | None = None,
    frequency_by_event: Mapping[str, int | float] | None = None,
    common_ae_limit: int = _DEFAULT_COMMON_AE_LIMIT,
    max_common_ae_events: int | None = None,
) -> SafetyViewSet:
    """Build heatmaps and a default subset without pooling or ranking.

    The complete fact set remains available for search/expand operations.
    """

    requested_values = tuple(
        value for value in (context, comparable_context, context_key) if value is not None
    )
    requested_context: SafetyComparableContext | None = None
    if requested_values:
        requested_context = _validated_safety_context(requested_values[0])
        if any(
            not _safety_contexts_compatible(
                _validated_safety_context(value),
                requested_context,
            )
            for value in requested_values[1:]
        ):
            raise SafetyViewError("安全性可比语境筛选参数互相冲突")

    try:
        validated = tuple(validate_safety_fact_row(item) for item in facts)
    except SafetyViewError:
        raise
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性热图输入无效：{error}") from error
    if len({fact.row_id for fact in validated}) != len(validated):
        raise SafetyViewError("安全性热图输入包含重复 row_id")
    if product_id is not None and not isinstance(product_id, str):
        raise SafetyViewError("安全性热图产品筛选必须是文本")
    if trial_id is not None and not isinstance(trial_id, str):
        raise SafetyViewError("安全性热图试验筛选必须是文本")

    selected = tuple(
        fact
        for fact in validated
        if (product_id is None or fact.product_id == product_id)
        and (trial_id is None or fact.trial_id == trial_id)
        and (
            requested_context is None
            or _safety_contexts_compatible(
                _safety_context_from_fact(fact),
                requested_context,
            )
        )
    )

    default_selection = select_default_safety_events(
        selected,
        clinically_important_terms=clinically_important_terms,
        important_event_terms=important_event_terms,
        adapter_marked_terms=adapter_marked_terms,
        high_frequency_terms=high_frequency_terms,
        source_frequency_by_event=source_frequency_by_event,
        frequency_by_event=frequency_by_event,
        common_ae_limit=common_ae_limit,
        max_common_ae_events=max_common_ae_events,
    )
    if not selected:
        return SafetyViewSet(
            fact_rows=(),
            heatmap_views=(),
            default_selection=default_selection,
        )

    grouped: dict[tuple[str, ...], list[SafetyFactRow]] = {}
    contexts: dict[tuple[str, ...], SafetyComparableContext] = {}
    for fact in selected:
        fact_context = _safety_context_from_fact(fact)
        key = fact_context.identity_key
        grouped.setdefault(key, []).append(fact)
        contexts.setdefault(key, fact_context)

    views: list[SafetyHeatmapView] = []
    for key in sorted(grouped, key=lambda value: tuple(str(item) for item in value)):
        context_value = contexts[key]
        ordered_facts = tuple(sorted(grouped[key], key=_safety_fact_sort_key))
        cells_without_intensity = tuple(
            SafetyHeatmapCell(fact_row=fact, context=context_value) for fact in ordered_facts
        )
        color_values = tuple(
            cell.color_value for cell in cells_without_intensity if cell.color_value is not None
        )
        maximum = max(color_values, default=0.0)
        cells = tuple(
            cell.model_copy(
                update={
                    "relative_intensity": (
                        None
                        if cell.color_value is None
                        else (0.0 if maximum == 0 else cell.color_value / maximum)
                    )
                }
            )
            for cell in cells_without_intensity
        )
        try:
            views.append(
                SafetyHeatmapView(
                    context=context_value,
                    cells=cells,
                    comparisons=_build_safety_comparisons(cells),
                )
            )
        except (TypeError, ValueError, ValidationError) as error:
            raise SafetyViewError(f"安全性热图视图构建失败：{error}") from error
    try:
        return SafetyViewSet(
            fact_rows=selected,
            heatmap_views=tuple(views),
            default_selection=default_selection,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性视图集合构建失败：{error}") from error


build_safety_heatmap_views = build_safety_views
build_safety_heatmaps = build_safety_views
build_safety_heatmap = build_safety_views
build_safety_view_set = build_safety_views


def build_safety_heatmap_view(
    facts: Sequence[SafetyFactRow | Mapping[str, Any]],
    *,
    context: SafetyComparableContext | Mapping[str, Any] | Sequence[str] | None = None,
    comparable_context: SafetyComparableContext | Mapping[str, Any] | Sequence[str] | None = None,
    context_key: SafetyComparableContext | Mapping[str, Any] | Sequence[str] | None = None,
    product_id: str | None = None,
    trial_id: str | None = None,
    clinically_important_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    important_event_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    adapter_marked_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    high_frequency_terms: Iterable[str] | Mapping[str, bool] | str | None = None,
    source_frequency_by_event: Mapping[str, int | float] | None = None,
    frequency_by_event: Mapping[str, int | float] | None = None,
    common_ae_limit: int = _DEFAULT_COMMON_AE_LIMIT,
    max_common_ae_events: int | None = None,
) -> SafetyHeatmapView:
    """Build one context-specific heatmap, rejecting ambiguous input."""

    views = build_safety_views(
        facts,
        context=context,
        comparable_context=comparable_context,
        context_key=context_key,
        product_id=product_id,
        trial_id=trial_id,
        clinically_important_terms=clinically_important_terms,
        important_event_terms=important_event_terms,
        adapter_marked_terms=adapter_marked_terms,
        high_frequency_terms=high_frequency_terms,
        source_frequency_by_event=source_frequency_by_event,
        frequency_by_event=frequency_by_event,
        common_ae_limit=common_ae_limit,
        max_common_ae_events=max_common_ae_events,
    ).heatmap_views
    if len(views) != 1:
        raise SafetyViewError("单一安全性热图必须明确且仅包含一个可比语境")
    return views[0]


def validate_safety_heatmap_cell(
    value: SafetyHeatmapCell | Mapping[str, Any],
) -> SafetyHeatmapCell:
    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, SafetyHeatmapCell)
            else dict(value)
        )
        return SafetyHeatmapCell.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性热图单元重新校验失败：{error}") from error


def validate_safety_heatmap_view(
    value: SafetyHeatmapView | Mapping[str, Any],
) -> SafetyHeatmapView:
    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, SafetyHeatmapView)
            else dict(value)
        )
        return SafetyHeatmapView.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性热图视图重新校验失败：{error}") from error


def validate_safety_view_set(
    value: SafetyViewSet | Mapping[str, Any],
) -> SafetyViewSet:
    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, SafetyViewSet)
            else dict(value)
        )
        return SafetyViewSet.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise SafetyViewError(f"安全性视图集合重新校验失败：{error}") from error


validate_safety_views = validate_safety_view_set
validate_safety_heatmap = validate_safety_heatmap_cell


__all__ += [
    "DEFAULT_SAFETY_DIMENSIONS",
    "DEFAULT_SAFETY_FAMILIES",
    "OPTIONAL_SAFETY_DIMENSIONS",
    "OPTIONAL_SAFETY_FAMILIES",
    "SafetyArmComparison",
    "SafetyCell",
    "SafetyComparableContext",
    "SafetyCompleteAEView",
    "SafetyComparison",
    "SafetyDefaultDimension",
    "SafetyDefaultEventSelection",
    "SafetyDefaultSelection",
    "SafetyEventSelection",
    "SafetyHeatmap",
    "SafetyHeatmapCell",
    "SafetyHeatmapComparison",
    "SafetyHeatmapSet",
    "SafetyHeatmapView",
    "SafetyOverviewDimension",
    "SafetyViewCollection",
    "SafetyViewSet",
    "SafetyViews",
    "build_default_safety_selection",
    "build_safety_heatmap",
    "build_safety_heatmap_view",
    "build_safety_heatmap_views",
    "build_safety_heatmaps",
    "build_safety_view_set",
    "build_safety_views",
    "default_safety_dimensions",
    "default_safety_families",
    "expand_complete_safety_events",
    "expand_safety_event_rows",
    "expand_safety_events",
    "get_default_safety_dimensions",
    "search_safety_event_rows",
    "search_safety_events",
    "select_default_safety_dimensions",
    "select_default_safety_event_rows",
    "select_default_safety_events",
    "validate_safety_heatmap",
    "validate_safety_heatmap_cell",
    "validate_safety_heatmap_view",
    "validate_safety_view_set",
    "validate_safety_views",
]

SafetyCell = SafetyHeatmapCell
