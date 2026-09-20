"""C 类设计图谱、终点三元身份与逐试验档案投影。

基于 Task 7.1 ``DesignObservation`` 与 Task 7.2 入排投影提供只读页面数据；
不生成 HTML/草稿，不发明缺失统计，不按显示名或输入顺序配对终点。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import (
    ConflictDisposition,
    DisclosureMaturity,
    SourceRole,
)
from ci_workflow.reports.c.contracts import (
    DesignFieldFamily,
    DesignObservation,
    DesignObservationError,
    validate_design_observation,
)
from ci_workflow.reports.c.design import (
    EligibilityDrilldownView,
    project_eligibility_drilldown,
)

_DEFINITION_SUFFIX = "_definition"
_TIMEPOINT_SUFFIX = "_timepoint"

_INCLUSION_FIELDS = frozenset({"inclusion_criterion"})
_EXCLUSION_FIELDS = frozenset({"exclusion_criterion"})

_DESIGN_MAP_FAMILIES = frozenset(
    {
        DesignFieldFamily.TRIAL_IDENTITY,
        DesignFieldFamily.POPULATION,
        DesignFieldFamily.GROUPING,
        DesignFieldFamily.INTERVENTION,
        DesignFieldFamily.DOSE_SCHEDULE,
        DesignFieldFamily.ENDPOINT,
        DesignFieldFamily.TIMEPOINT,
        DesignFieldFamily.SAMPLE_SIZE,
        DesignFieldFamily.OPERATIONAL,
        DesignFieldFamily.STATISTICAL,
    }
)

_POPULATION_VIEW_FAMILIES = frozenset({DesignFieldFamily.POPULATION})
_INTERVENTION_VIEW_FAMILIES = frozenset(
    {
        DesignFieldFamily.GROUPING,
        DesignFieldFamily.INTERVENTION,
        DesignFieldFamily.DOSE_SCHEDULE,
    }
)
_VISIT_VIEW_FAMILIES = frozenset(
    {
        DesignFieldFamily.DOSE_SCHEDULE,
        DesignFieldFamily.OPERATIONAL,
        DesignFieldFamily.TIMEPOINT,
    }
)
_STATISTICS_VIEW_FAMILIES = frozenset(
    {
        DesignFieldFamily.SAMPLE_SIZE,
        DesignFieldFamily.STATISTICAL,
    }
)


class DesignPagesError(ValueError):
    """C 类设计视图投影输入或配对材料不满足合同。"""


class DesignTopic(StrEnum):
    """专题投影主题；用于图谱与专题页责任划分。"""

    DESIGN_MAP = "design_map"
    POPULATION = "population"
    INTERVENTION = "intervention"
    VISIT_SCHEDULE = "visit_schedule"
    STATISTICS = "statistics"
    ENDPOINT_TIMEPOINT = "endpoint_timepoint"
    TRIAL_DOSSIER = "trial_dossier"


class EndpointDefinitionTimepointRow(BaseModel):
    """一条可比较终点行：名称—完整定义—评估时间点三元身份。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint_identity: str
    pairing_key: str
    product_id: str
    trial_id: str
    cohort_id: str
    group_id: str
    endpoint_display_name: str
    endpoint_definition: str
    assessment_timepoint: str
    endpoint_observation_id: str
    timepoint_observation_id: str
    endpoint_source_text: str
    timepoint_source_text: str
    endpoint_source_version_id: str
    timepoint_source_version_id: str
    endpoint_source_locator: EvidenceLocator
    timepoint_source_locator: EvidenceLocator
    endpoint_disclosure_state: FactDisclosureState
    timepoint_disclosure_state: FactDisclosureState
    endpoint_review_state: FactReviewState
    timepoint_review_state: FactReviewState
    endpoint_conflict_disposition: ConflictDisposition
    timepoint_conflict_disposition: ConflictDisposition
    endpoint_field: str
    timepoint_field: str
    scale: str | None = None
    scale_version: str | None = None

    @field_validator(
        "endpoint_identity",
        "pairing_key",
        "product_id",
        "trial_id",
        "cohort_id",
        "group_id",
        "endpoint_display_name",
        "endpoint_definition",
        "assessment_timepoint",
        "endpoint_observation_id",
        "timepoint_observation_id",
        "endpoint_source_text",
        "timepoint_source_text",
        "endpoint_source_version_id",
        "timepoint_source_version_id",
        "endpoint_field",
        "timepoint_field",
    )
    @classmethod
    def _required_raw(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("终点三元投影必填文本不能为空")
        return value


class EndpointDefinitionTimepointView(BaseModel):
    """终点矩阵图/表同源投影。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    table_rows: tuple[EndpointDefinitionTimepointRow, ...]
    chart_rows: tuple[EndpointDefinitionTimepointRow, ...]
    topic: DesignTopic = DesignTopic.ENDPOINT_TIMEPOINT


class DesignFactRow(BaseModel):
    """设计图谱/专题/档案共用的单条观察投影。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    row_identity: str
    row_id: str
    source_row_id: str
    observation_id: str
    product_id: str
    trial_id: str
    cohort_id: str
    group_id: str
    field_family: DesignFieldFamily
    field: str
    source_field_name: str
    source_field_definition: str
    source_text: str
    source_version_id: str
    source_locator: EvidenceLocator
    source_role: SourceRole
    disclosure_maturity: DisclosureMaturity
    disclosure_state: FactDisclosureState
    review_state: FactReviewState
    conflict_disposition: ConflictDisposition
    assessment_timepoint: str | None = None
    stage: str | None = None
    development_role: str | None = None
    randomization: str | None = None
    blinding: str | None = None
    scale: str | None = None
    scale_version: str | None = None
    operator: str | None = None
    threshold_value: str | None = None
    threshold_unit: str | None = None
    reported_zero_text: str | None = None
    route_receipt_id: str | None = None
    applicability_predicate_id: str | None = None
    compatibility_rule: str
    difference_labels_zh: tuple[str, ...] = ()

    @field_validator(
        "schema_version",
        "row_identity",
        "row_id",
        "source_row_id",
        "observation_id",
        "product_id",
        "trial_id",
        "cohort_id",
        "group_id",
        "field",
        "source_field_name",
        "source_field_definition",
        "source_text",
        "source_version_id",
        "compatibility_rule",
    )
    @classmethod
    def _required_raw(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("设计事实投影必填文本不能为空")
        return value


class DesignTopicView(BaseModel):
    """设计图谱或专题页同源投影。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic: DesignTopic
    table_rows: tuple[DesignFactRow, ...]
    chart_rows: tuple[DesignFactRow, ...]
    observation_ids: tuple[str, ...]


class TrialDossierView(BaseModel):
    """逐试验完整设计档案：观察集合与该试验输入快照相等。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    table_rows: tuple[DesignFactRow, ...]
    chart_rows: tuple[DesignFactRow, ...]
    observation_ids: tuple[str, ...]
    topic: DesignTopic = DesignTopic.TRIAL_DOSSIER

    @field_validator("trial_id")
    @classmethod
    def _trial_id_raw(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("试验标识不能为空")
        return value


def _require_observation_sequence(
    observations: Sequence[DesignObservation | Mapping[str, Any]] | object,
) -> Sequence[DesignObservation | Mapping[str, Any]]:
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        raise DesignPagesError("设计观察集合必须是序列")
    return observations


def _revalidate_observations(
    observations: Sequence[DesignObservation | Mapping[str, Any]] | object,
) -> tuple[DesignObservation, ...]:
    sequence = _require_observation_sequence(observations)
    validated: list[DesignObservation] = []
    for item in sequence:
        try:
            validated.append(validate_design_observation(item))
        except DesignObservationError:
            raise
        except TypeError:
            raise
        except Exception as error:  # noqa: BLE001 - 统一投影层失败码
            raise DesignPagesError(f"设计观察重新校验失败：{error}") from error
    return tuple(validated)


def _pairing_key_from_definition_field(field: str) -> str | None:
    if field.endswith(_DEFINITION_SUFFIX) and len(field) > len(_DEFINITION_SUFFIX):
        return field[: -len(_DEFINITION_SUFFIX)]
    return None


def _pairing_key_from_timepoint_field(field: str) -> str | None:
    if field.endswith(_TIMEPOINT_SUFFIX) and len(field) > len(_TIMEPOINT_SUFFIX):
        return field[: -len(_TIMEPOINT_SUFFIX)]
    return None


def _scope_key(observation: DesignObservation, pairing_key: str) -> tuple[str, ...]:
    return (
        observation.product_id,
        observation.trial_id,
        observation.cohort_id,
        observation.group_id,
        pairing_key,
    )


def _endpoint_identity(
    *,
    endpoint: DesignObservation,
    pairing_key: str,
    display_name: str,
    definition: str,
    assessment_timepoint: str,
) -> str:
    return stable_id(
        "c-endpoint-ternary",
        endpoint.product_id,
        endpoint.trial_id,
        endpoint.cohort_id,
        endpoint.group_id,
        pairing_key,
        display_name,
        definition,
        assessment_timepoint,
        endpoint.observation_id,
    )


def _fact_row_identity(observation: DesignObservation) -> str:
    return stable_id(
        "c-design-fact",
        observation.product_id,
        observation.trial_id,
        observation.cohort_id,
        observation.group_id,
        observation.field_family.value,
        observation.field,
        observation.observation_id,
    )


def _fact_sort_key(row: DesignFactRow) -> tuple[str, ...]:
    return (
        row.product_id,
        row.trial_id,
        row.cohort_id,
        row.group_id,
        row.field_family.value,
        row.field,
        row.observation_id,
        row.row_identity,
    )


def _endpoint_sort_key(row: EndpointDefinitionTimepointRow) -> tuple[str, ...]:
    return (
        row.product_id,
        row.trial_id,
        row.cohort_id,
        row.group_id,
        row.pairing_key,
        row.endpoint_display_name,
        row.endpoint_definition,
        row.assessment_timepoint,
        row.endpoint_observation_id,
        row.endpoint_identity,
    )


def _to_fact_row(observation: DesignObservation) -> DesignFactRow:
    return DesignFactRow(
        schema_version=observation.schema_version,
        row_identity=_fact_row_identity(observation),
        row_id=observation.row_id,
        source_row_id=observation.source_row_id,
        observation_id=observation.observation_id,
        product_id=observation.product_id,
        trial_id=observation.trial_id,
        cohort_id=observation.cohort_id,
        group_id=observation.group_id,
        field_family=observation.field_family,
        field=observation.field,
        source_field_name=observation.source_field_name,
        source_field_definition=observation.source_field_definition,
        source_text=observation.source_text,
        source_version_id=observation.source_version_id,
        source_locator=observation.source_locator,
        source_role=observation.source_role,
        disclosure_maturity=observation.disclosure_maturity,
        disclosure_state=observation.disclosure_state,
        review_state=observation.review_state,
        conflict_disposition=observation.conflict_disposition,
        assessment_timepoint=observation.assessment_timepoint,
        stage=observation.stage,
        development_role=observation.development_role,
        randomization=observation.randomization,
        blinding=observation.blinding,
        scale=observation.scale,
        scale_version=observation.scale_version,
        operator=observation.operator,
        threshold_value=observation.threshold_value,
        threshold_unit=observation.threshold_unit,
        reported_zero_text=observation.reported_zero_text,
        route_receipt_id=observation.route_receipt_id,
        applicability_predicate_id=observation.applicability_predicate_id,
        compatibility_rule=observation.compatibility_rule,
        difference_labels_zh=observation.difference_labels_zh,
    )


def _project_topic_rows(
    observations: Sequence[DesignObservation],
    *,
    families: frozenset[DesignFieldFamily],
    topic: DesignTopic,
) -> DesignTopicView:
    rows = tuple(
        sorted(
            (
                _to_fact_row(item)
                for item in observations
                if item.field_family in families
            ),
            key=_fact_sort_key,
        )
    )
    observation_ids = tuple(row.observation_id for row in rows)
    return DesignTopicView(
        topic=topic,
        table_rows=rows,
        chart_rows=rows,
        observation_ids=observation_ids,
    )


def _build_endpoint_row(
    *,
    endpoint: DesignObservation,
    timepoint: DesignObservation,
    pairing_key: str,
) -> EndpointDefinitionTimepointRow:
    if endpoint.field_family is not DesignFieldFamily.ENDPOINT:
        raise DesignPagesError("终点观察字段族必须是 endpoint")
    if timepoint.field_family is not DesignFieldFamily.TIMEPOINT:
        raise DesignPagesError("时间点观察字段族必须是 timepoint")
    if timepoint.assessment_timepoint is None or not timepoint.assessment_timepoint.strip():
        raise DesignPagesError("配对时间点观察缺少评估时间点")

    display_name = endpoint.source_field_name
    definition = endpoint.source_field_definition
    assessment_timepoint = timepoint.assessment_timepoint
    identity = _endpoint_identity(
        endpoint=endpoint,
        pairing_key=pairing_key,
        display_name=display_name,
        definition=definition,
        assessment_timepoint=assessment_timepoint,
    )
    return EndpointDefinitionTimepointRow(
        endpoint_identity=identity,
        pairing_key=pairing_key,
        product_id=endpoint.product_id,
        trial_id=endpoint.trial_id,
        cohort_id=endpoint.cohort_id,
        group_id=endpoint.group_id,
        endpoint_display_name=display_name,
        endpoint_definition=definition,
        assessment_timepoint=assessment_timepoint,
        endpoint_observation_id=endpoint.observation_id,
        timepoint_observation_id=timepoint.observation_id,
        endpoint_source_text=endpoint.source_text,
        timepoint_source_text=timepoint.source_text,
        endpoint_source_version_id=endpoint.source_version_id,
        timepoint_source_version_id=timepoint.source_version_id,
        endpoint_source_locator=endpoint.source_locator,
        timepoint_source_locator=timepoint.source_locator,
        endpoint_disclosure_state=endpoint.disclosure_state,
        timepoint_disclosure_state=timepoint.disclosure_state,
        endpoint_review_state=endpoint.review_state,
        timepoint_review_state=timepoint.review_state,
        endpoint_conflict_disposition=endpoint.conflict_disposition,
        timepoint_conflict_disposition=timepoint.conflict_disposition,
        endpoint_field=endpoint.field,
        timepoint_field=timepoint.field,
        scale=endpoint.scale,
        scale_version=endpoint.scale_version,
    )


def project_endpoint_definition_timepoint(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> EndpointDefinitionTimepointView:
    """将显式配对的终点与时间点投影为可比较三元身份行。

    仅通过 ``field`` 上的 ``{pairing_key}_definition`` ↔ ``{pairing_key}_timepoint``
    且同一 product/trial/cohort/group 结合；禁止顺序、近似名或跨试验/组别回退。
    """

    validated = _revalidate_observations(observations)
    endpoints_by_scope: dict[tuple[str, ...], list[DesignObservation]] = defaultdict(list)
    timepoints_by_scope: dict[tuple[str, ...], list[DesignObservation]] = defaultdict(
        list
    )

    for item in validated:
        if item.field_family is DesignFieldFamily.ENDPOINT:
            pairing_key = _pairing_key_from_definition_field(item.field)
            if pairing_key is None:
                continue
            endpoints_by_scope[_scope_key(item, pairing_key)].append(item)
        elif item.field_family is DesignFieldFamily.TIMEPOINT:
            pairing_key = _pairing_key_from_timepoint_field(item.field)
            if pairing_key is None:
                continue
            timepoints_by_scope[_scope_key(item, pairing_key)].append(item)

    rows: list[EndpointDefinitionTimepointRow] = []
    for scope, endpoint_items in endpoints_by_scope.items():
        timepoint_items = timepoints_by_scope.get(scope, ())
        if not timepoint_items:
            continue
        if len(endpoint_items) != 1 or len(timepoint_items) != 1:
            raise DesignPagesError(
                "同一产品/试验/队列/组别/配对键下终点或时间点观察不唯一，拒绝静默合并"
            )
        pairing_key = scope[-1]
        rows.append(
            _build_endpoint_row(
                endpoint=endpoint_items[0],
                timepoint=timepoint_items[0],
                pairing_key=pairing_key,
            )
        )

    ordered = tuple(sorted(rows, key=_endpoint_sort_key))
    identities = {row.endpoint_identity for row in ordered}
    if len(identities) != len(ordered):
        raise DesignPagesError("终点三元稳定身份发生碰撞")
    return EndpointDefinitionTimepointView(table_rows=ordered, chart_rows=ordered)


def project_design_map(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> DesignTopicView:
    """设计图谱：确定性投影全部设计字段族，输入重排不改变身份集合。"""

    validated = _revalidate_observations(observations)
    return _project_topic_rows(
        validated,
        families=_DESIGN_MAP_FAMILIES,
        topic=DesignTopic.DESIGN_MAP,
    )


def project_population_view(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> DesignTopicView:
    """人群与疾病定义专题投影。"""

    validated = _revalidate_observations(observations)
    return _project_topic_rows(
        validated,
        families=_POPULATION_VIEW_FAMILIES,
        topic=DesignTopic.POPULATION,
    )


def project_intervention_view(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> DesignTopicView:
    """分组、干预与对照专题投影。"""

    validated = _revalidate_observations(observations)
    return _project_topic_rows(
        validated,
        families=_INTERVENTION_VIEW_FAMILIES,
        topic=DesignTopic.INTERVENTION,
    )


def project_visit_schedule_view(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> DesignTopicView:
    """访视、疗程与随访专题投影；未登记字段保持缺失，不解释为未实施。"""

    validated = _revalidate_observations(observations)
    return _project_topic_rows(
        validated,
        families=_VISIT_VIEW_FAMILIES,
        topic=DesignTopic.VISIT_SCHEDULE,
    )


def project_statistics_view(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
) -> DesignTopicView:
    """样本量与已公开统计字段投影；保留真实披露状态，禁止推断未公开细节。"""

    validated = _revalidate_observations(observations)
    return _project_topic_rows(
        validated,
        families=_STATISTICS_VIEW_FAMILIES,
        topic=DesignTopic.STATISTICS,
    )


def project_inclusion_view(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
    *,
    indication_id: str,
) -> EligibilityDrilldownView:
    """入选标准视图：复用 Task 7.2 入排投影，仅保留入选字段。"""

    validated = _revalidate_observations(observations)
    inclusion_only = tuple(
        item
        for item in validated
        if item.field_family is DesignFieldFamily.POPULATION
        and item.field in _INCLUSION_FIELDS
    )
    return project_eligibility_drilldown(inclusion_only, indication_id=indication_id)


def project_exclusion_view(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
    *,
    indication_id: str,
) -> EligibilityDrilldownView:
    """排除标准视图：复用 Task 7.2 入排投影，仅保留排除字段。"""

    validated = _revalidate_observations(observations)
    exclusion_only = tuple(
        item
        for item in validated
        if item.field_family is DesignFieldFamily.POPULATION
        and item.field in _EXCLUSION_FIELDS
    )
    return project_eligibility_drilldown(exclusion_only, indication_id=indication_id)


def project_trial_dossier(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
    *,
    trial_id: str,
) -> TrialDossierView:
    """逐试验完整设计档案：观察身份集合等于该试验全部输入观察，禁止截断。"""

    if not isinstance(trial_id, str) or not trial_id.strip():
        raise DesignPagesError("试验标识不能为空")
    target_trial = " ".join(trial_id.split())
    validated = _revalidate_observations(observations)
    trial_observations = tuple(
        item for item in validated if item.trial_id == target_trial
    )
    rows = tuple(
        sorted(
            (_to_fact_row(item) for item in trial_observations),
            key=_fact_sort_key,
        )
    )
    observation_ids = tuple(row.observation_id for row in rows)
    input_ids = {item.observation_id for item in trial_observations}
    if len(input_ids) != len(trial_observations):
        raise DesignPagesError("同一试验的设计观察身份不得重复")
    if set(observation_ids) != input_ids:
        raise DesignPagesError("试验档案观察身份集合与输入快照不一致")
    if len(set(observation_ids)) != len(observation_ids):
        raise DesignPagesError("试验档案观察身份发生重复")
    return TrialDossierView(
        trial_id=target_trial,
        table_rows=rows,
        chart_rows=rows,
        observation_ids=observation_ids,
    )


__all__ = [
    "DesignPagesError",
    "DesignTopic",
    "EndpointDefinitionTimepointRow",
    "EndpointDefinitionTimepointView",
    "DesignFactRow",
    "DesignTopicView",
    "TrialDossierView",
    "project_endpoint_definition_timepoint",
    "project_design_map",
    "project_population_view",
    "project_intervention_view",
    "project_visit_schedule_view",
    "project_statistics_view",
    "project_inclusion_view",
    "project_exclusion_view",
    "project_trial_dossier",
]
