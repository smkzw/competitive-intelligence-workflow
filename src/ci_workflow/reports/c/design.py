"""C 类入排标准精确结构化投影与稳定下钻链。

基于 Task 7.1 ``DesignObservation`` 投影适用入排观察，不复制证据定位合同、
不生成页面/草稿。未命名量表与缺失运算符/阈值使用显式 ``not_applicable``
与适用性谓词，禁止空串或伪造量表名；原文与 ``EvidenceLocator`` 原样保留。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, field_validator

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation

# 与 RED 封闭目录对齐：仅人口学/人群族下的入排设计要素进入投影。
_ELIGIBILITY_DESIGN_ELEMENTS = frozenset(
    {
        "disease_definition",
        "disease_course",
        "severity_or_activity",
        "prior_therapy",
        "background_therapy",
        "rescue_therapy",
        "washout",
        "age_rule",
        "lab_or_biomarker",
        "comorbidity_rule",
        "inclusion_criterion",
        "exclusion_criterion",
    }
)

_SCALE_NOT_APPLICABLE_PREDICATE_ID = "c-eligibility-scale-unnamed-not-applicable"
_OPERATOR_THRESHOLD_NOT_APPLICABLE_PREDICATE_ID = (
    "c-eligibility-operator-threshold-absent-not-applicable"
)


class EligibilityDesignError(ValueError):
    """入排下钻投影输入或身份材料不满足合同。"""


class FieldApplicability(StrEnum):
    """观察字段适用性：有命名值或显式不适用，禁止空串占位。"""

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"


class EligibilityDrilldownRow(BaseModel):
    """一条完整稳定下钻链：适应症→产品→试验→队列/组别→设计要素→原文与定位。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    indication_id: str
    product_id: str
    trial_id: str
    cohort_id: str
    group_id: str
    design_element: str
    source_field_name: str
    source_text: str
    scale: str | None
    scale_version: str | None
    scale_applicability: FieldApplicability
    scale_applicability_predicate_id: str | None
    assessment_timepoint: str | None
    operator: str | None
    threshold_value: str | None
    threshold_unit: str | None
    operator_threshold_applicability: FieldApplicability
    operator_threshold_applicability_predicate_id: str | None
    source_version_id: str
    source_locator: EvidenceLocator
    observation_id: str
    drilldown_chain_id: str

    @field_validator(
        "indication_id",
        "product_id",
        "trial_id",
        "cohort_id",
        "group_id",
        "design_element",
        "source_field_name",
        "source_text",
        "source_version_id",
        "observation_id",
        "drilldown_chain_id",
    )
    @classmethod
    def _required_raw(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("入排下钻必填文本不能为空")
        return value


class EligibilityEvidenceLink(BaseModel):
    """图/表共用的证据抽屉链接：绑定同一 ``drilldown_chain_id`` 与原文定位。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    drilldown_chain_id: str
    source_text: str
    source_locator: EvidenceLocator

    @field_validator("observation_id", "drilldown_chain_id", "source_text")
    @classmethod
    def _required_raw(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("入排证据链接必填文本不能为空")
        return value


class EligibilityDrilldownView(BaseModel):
    """入排比较图、完整表与证据抽屉的同源投影。"""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    table_rows: tuple[EligibilityDrilldownRow, ...]
    chart_rows: tuple[EligibilityDrilldownRow, ...]
    evidence_by_chain_id: Mapping[str, EligibilityEvidenceLink]

    @field_validator("evidence_by_chain_id", mode="before")
    @classmethod
    def _freeze_evidence(cls, value: Any) -> Mapping[str, EligibilityEvidenceLink]:
        if isinstance(value, MappingProxyType):
            return value
        if not isinstance(value, Mapping):
            raise ValueError("evidence_by_chain_id 必须是映射")
        return MappingProxyType(dict(value))


def _is_applicable_eligibility_observation(observation: DesignObservation) -> bool:
    return (
        observation.field_family is DesignFieldFamily.POPULATION
        and observation.field in _ELIGIBILITY_DESIGN_ELEMENTS
    )


def _require_indication_id(indication_id: str) -> str:
    if not isinstance(indication_id, str) or not indication_id.strip():
        raise EligibilityDesignError("适应症标识不能为空")
    return indication_id


def _scale_projection(
    observation: DesignObservation,
) -> tuple[str | None, str | None, FieldApplicability, str | None]:
    if observation.scale is None:
        return (
            None,
            None,
            FieldApplicability.NOT_APPLICABLE,
            _SCALE_NOT_APPLICABLE_PREDICATE_ID,
        )
    return (
        observation.scale,
        observation.scale_version,
        FieldApplicability.APPLICABLE,
        None,
    )


def _operator_threshold_projection(
    observation: DesignObservation,
) -> tuple[FieldApplicability, str | None]:
    threshold_bits = (
        observation.operator,
        observation.threshold_value,
        observation.threshold_unit,
    )
    if all(item is None for item in threshold_bits):
        return (
            FieldApplicability.NOT_APPLICABLE,
            _OPERATOR_THRESHOLD_NOT_APPLICABLE_PREDICATE_ID,
        )
    return FieldApplicability.APPLICABLE, None


def _drilldown_chain_id(indication_id: str, observation: DesignObservation) -> str:
    """稳定链身份：适应症/产品/试验/队列/组别/设计要素/原始字段/观察 id。"""

    return stable_id(
        "c-eligibility-drilldown",
        indication_id,
        observation.product_id,
        observation.trial_id,
        observation.cohort_id,
        observation.group_id,
        observation.field,
        observation.source_field_name,
        observation.observation_id,
    )


def _project_row(
    observation: DesignObservation,
    *,
    indication_id: str,
) -> EligibilityDrilldownRow:
    scale, scale_version, scale_applicability, scale_predicate = _scale_projection(
        observation
    )
    threshold_applicability, threshold_predicate = _operator_threshold_projection(
        observation
    )
    chain_id = _drilldown_chain_id(indication_id, observation)
    return EligibilityDrilldownRow(
        indication_id=indication_id,
        product_id=observation.product_id,
        trial_id=observation.trial_id,
        cohort_id=observation.cohort_id,
        group_id=observation.group_id,
        design_element=observation.field,
        source_field_name=observation.source_field_name,
        # 原文 byte-for-byte：直接引用观察原文，不做规范化或截短。
        source_text=observation.source_text,
        scale=scale,
        scale_version=scale_version,
        scale_applicability=scale_applicability,
        scale_applicability_predicate_id=scale_predicate,
        assessment_timepoint=observation.assessment_timepoint,
        operator=observation.operator,
        threshold_value=observation.threshold_value,
        threshold_unit=observation.threshold_unit,
        operator_threshold_applicability=threshold_applicability,
        operator_threshold_applicability_predicate_id=threshold_predicate,
        source_version_id=observation.source_version_id,
        source_locator=observation.source_locator,
        observation_id=observation.observation_id,
        drilldown_chain_id=chain_id,
    )


def _evidence_link(row: EligibilityDrilldownRow) -> EligibilityEvidenceLink:
    return EligibilityEvidenceLink(
        observation_id=row.observation_id,
        drilldown_chain_id=row.drilldown_chain_id,
        source_text=row.source_text,
        source_locator=row.source_locator,
    )


def project_eligibility_drilldown(
    observations: object,
    *,
    indication_id: str,
) -> EligibilityDrilldownView:
    """将登记设计观察投影为入排完整表/比较图/证据抽屉同源视图。

    仅纳入 ``POPULATION`` 族且字段属于入排封闭目录的观察；非入排对照被排除。
    图、表与证据抽屉共享同一 ``drilldown_chain_id``。
    """

    indication = _require_indication_id(indication_id)
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        raise EligibilityDesignError("设计观察集合必须是序列")
    typed_observations = cast(Sequence[DesignObservation], observations)

    applicable = tuple(
        item for item in typed_observations if _is_applicable_eligibility_observation(item)
    )
    rows = tuple(_project_row(item, indication_id=indication) for item in applicable)

    seen_chain_ids: set[str] = set()
    for row in rows:
        if row.drilldown_chain_id in seen_chain_ids:
            raise EligibilityDesignError(
                f"入排稳定链身份碰撞：{row.drilldown_chain_id}"
            )
        seen_chain_ids.add(row.drilldown_chain_id)

    evidence = MappingProxyType(
        {row.drilldown_chain_id: _evidence_link(row) for row in rows}
    )
    # 图与表同源：同一投影行集合，禁止另抽子集。
    return EligibilityDrilldownView(
        table_rows=rows,
        chart_rows=rows,
        evidence_by_chain_id=evidence,
    )


__all__ = [
    "EligibilityDesignError",
    "FieldApplicability",
    "EligibilityDrilldownRow",
    "EligibilityEvidenceLink",
    "EligibilityDrilldownView",
    "project_eligibility_drilldown",
]
