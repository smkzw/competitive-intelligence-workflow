"""B 类指南依据与竞品终点采用依据合同。

本模块只负责 Task 6.2 的监管指南谱系和首页终点依据。终点观察的
兼容判定始终委托给 Task 6.1 ``reports.b.contracts``；本模块不复制
终点或时间窗规则，也不对试验结果做跨试验合并。
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

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
from ci_workflow.sources.connectors.regulators import (
    GuidelineBasis,
    validate_guideline_lineage,
)

from .contracts import (
    EndpointCompatibilityError,
    EndpointCompatibilityPolicy,
    EndpointCompatibilityResult,
    EndpointObservation,
    TimepointCompatibilityPolicy,
    load_endpoint_compatibility_policy,
    load_timepoint_compatibility_policy,
    match_endpoint_compatibility,
)


class EndpointBasisError(ValueError):
    """指南或竞品终点依据不满足失败关闭合同。"""


class GuidanceTrack(StrEnum):
    """监管依据的平行轨；CDE/FDA 没有隐式优先级。"""

    CDE = "cde"
    FDA = "fda"
    OTHER = "other"

    # 自然语言/调用方兼容别名；序列化值仍只有三种。
    CHINA_CDE = "cde"
    US_FDA = "fda"


class GuidanceLifecycleState(StrEnum):
    """指南在当前快照中的用户可见生命周期语义。"""

    CURRENT = "current"
    DRAFT = "draft"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class EndpointAdoptionStatus(StrEnum):
    """终点族的严格多数/最常采用状态。"""

    NOT_SELECTED = "not_selected"
    STRICT_MAJORITY = "strict_majority"
    MOST_COMMON = "most_common"

    # 兼容常用调用方命名，不增加新的序列化值。
    MAJORITY = "strict_majority"
    NONE = "not_selected"


_GUIDANCE_STATUS_LABELS_ZH: dict[GuidanceLifecycleState, str] = {
    GuidanceLifecycleState.CURRENT: "当前",
    GuidanceLifecycleState.DRAFT: "草案",
    GuidanceLifecycleState.SUPERSEDED: "已替代（历史）",
    GuidanceLifecycleState.WITHDRAWN: "已废止（历史）",
}

_PRIMARY_ENDPOINT_ROLE_TOKENS = frozenset(
    {
        "primary",
        "primary_endpoint",
        "co_primary",
        "co_primary_endpoint",
        "coprimary",
        "coprimary_endpoint",
        "主要",
        "主要终点",
        "共同主要",
        "共同主要终点",
    }
)
_CORE_STUDY_ROLE_TOKENS = frozenset(
    {
        "core",
        "special_core",
        "special-core",
        "核心",
        "特殊核心",
    }
)


def _text(value: str, *, field_name: str = "B 类依据字段") -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _optional_text(value: str | None, *, field_name: str = "B 类依据字段") -> str | None:
    return None if value is None else _text(value, field_name=field_name)


def _as_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    return (value,) if isinstance(value, str) else tuple(value)


def _normalized_token(value: str) -> str:
    return "_".join(value.strip().casefold().replace("-", "_").split())


def _normalize_adoption_status(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return {
        "none": "not_selected",
        "not_selected": "not_selected",
        "no_consensus": "not_selected",
        "majority": "strict_majority",
        "strict_majority": "strict_majority",
        "most_common": "most_common",
        "most_commonly_used": "most_common",
    }.get(_normalized_token(value), value)


def _normalize_guidance_track(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return {
        "cde": "cde",
        "china_cde": "cde",
        "cn_cde": "cde",
        "fda": "fda",
        "us_fda": "fda",
        "other": "other",
    }.get(_normalized_token(value), value)


def _guidance_track(guidance: GuidelineBasis) -> GuidanceTrack:
    jurisdiction = guidance.jurisdiction.strip().casefold()
    agency = " ".join(guidance.agency.strip().casefold().split())
    if jurisdiction in {"cn", "china", "中国"} and agency in {
        "cde",
        "china cde",
        "center for drug evaluation",
        "center for drug evaluation (cde)",
        "药品审评中心",
    }:
        return GuidanceTrack.CDE
    if jurisdiction in {"us", "usa", "美国"} and agency in {
        "fda",
        "u.s. food and drug administration",
        "us food and drug administration",
        "美国食品药品监督管理局",
    }:
        return GuidanceTrack.FDA
    return GuidanceTrack.OTHER


def guidance_lifecycle_state(guidance: GuidelineBasis) -> GuidanceLifecycleState:
    """从已校验的指南字段确定当前/草案/废止语义。"""

    if guidance.lifecycle_status == "withdrawn":
        return GuidanceLifecycleState.WITHDRAWN
    if guidance.lifecycle_status == "superseded":
        return GuidanceLifecycleState.SUPERSEDED
    if guidance.guidance_status == "draft":
        return GuidanceLifecycleState.DRAFT
    # GuidelineBasis 自身保证 active + final 才可驱动当前默认。
    return GuidanceLifecycleState.CURRENT


def guidance_status_label_zh(guidance: GuidelineBasis) -> str:
    """返回不可由界面标签覆盖的指南生命周期标签。"""

    return _GUIDANCE_STATUS_LABELS_ZH[guidance_lifecycle_state(guidance)]


class GuidanceEvidence(GuidelineBasis):
    """带可选终点族范围的完整监管指南证据。

    基础字段全部复用 ``GuidelineBasis``，因此保留司法辖区、机构、标题、
    状态、版本日期、人群、研发语境、精确定位、内容摘要和替代/废止关系。
    ``endpoint_family_ids`` 只表达该指南条目明确覆盖的终点族；为空表示
    适用于传入的全部终点族。监管轨由辖区和机构重新推导，不能由调用方
    伪造为 CDE 或 FDA。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint_family_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices(
            "endpoint_family_ids",
            "endpoint_family_id",
            "endpoint_ids",
            "endpoint_families",
        ),
    )
    track: GuidanceTrack | None = None

    @field_validator("track", mode="before")
    @classmethod
    def _track_alias(cls, value: Any) -> Any:
        return _normalize_guidance_track(value)

    @model_validator(mode="before")
    @classmethod
    def _field_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        aliases = {
            "status": "guidance_status",
            "lifecycle": "lifecycle_status",
            "lifecycle_state": "lifecycle_status",
            "version": "version_date",
            "published_on": "version_date",
            "captured_version": "guideline_version_id",
            "source_version_id": "guideline_version_id",
            "exact_locator": "locator",
            "source_locator": "locator",
        }
        for source, target in aliases.items():
            if target not in payload and source in payload:
                payload[target] = payload[source]
            payload.pop(source, None)
        return payload

    @field_validator("endpoint_family_ids", mode="before")
    @classmethod
    def _endpoint_family_ids(cls, value: Any) -> tuple[str, ...]:
        values = tuple(_text(item, field_name="指南终点族标识") for item in _as_tuple(value))
        lowered = tuple(item.casefold() for item in values)
        if len(set(lowered)) != len(lowered):
            raise ValueError("指南终点族标识不得重复")
        return values

    @model_validator(mode="after")
    def _track_is_derived(self) -> Self:
        derived = _guidance_track(self)
        if self.track is not None and self.track is not derived:
            raise ValueError("指南监管轨必须与司法辖区和发布机构一致")
        return self

    @classmethod
    def create(cls, **kwargs: Any) -> Self:
        """复用 ``GuidelineBasis.create`` 生成完整、稳定的指南身份。"""

        endpoint_family_ids = kwargs.pop("endpoint_family_ids", None)
        if endpoint_family_ids is None and "endpoint_family_id" in kwargs:
            endpoint_family_ids = kwargs.pop("endpoint_family_id")
        track = kwargs.pop("track", None)
        base = GuidelineBasis.create(**kwargs)
        payload = base.model_dump(mode="python", warnings=False)
        payload["endpoint_family_ids"] = _as_tuple(endpoint_family_ids)
        payload["track"] = track
        return cls.model_validate(payload)

    @property
    def regulatory_track(self) -> GuidanceTrack:
        return _guidance_track(self)

    @property
    def lifecycle_state(self) -> GuidanceLifecycleState:
        return guidance_lifecycle_state(self)

    @property
    def lifecycle_label_zh(self) -> str:
        return guidance_status_label_zh(self)

    @property
    def status(self) -> str:
        return self.guidance_status

    @property
    def lifecycle(self) -> str:
        return self.lifecycle_status

    @property
    def version(self) -> date:
        return self.version_date

    @property
    def captured_version(self) -> str:
        return self.guideline_version_id

    @property
    def exact_locator(self) -> EvidenceLocator:
        return self.locator

    @property
    def source_locator(self) -> EvidenceLocator:
        return self.locator

    @property
    def is_current(self) -> bool:
        return self.lifecycle_state is GuidanceLifecycleState.CURRENT

    @property
    def is_draft(self) -> bool:
        return self.lifecycle_state is GuidanceLifecycleState.DRAFT

    @property
    def is_historical(self) -> bool:
        return self.lifecycle_state in {
            GuidanceLifecycleState.SUPERSEDED,
            GuidanceLifecycleState.WITHDRAWN,
        }


# ``GuidelineEvidence`` 是历史任务/调用方常用名称；类型本身保持单一实现。
GuidelineEvidence = GuidanceEvidence


def _validated_guidance(
    value: GuidanceEvidence | GuidelineBasis | Mapping[str, Any],
) -> GuidanceEvidence | GuidelineBasis:
    """重跑指南模型校验，防止 ``model_copy(update=...)`` 绕过边界。"""

    try:
        if isinstance(value, GuidanceEvidence):
            return GuidanceEvidence.model_validate(value.model_dump(mode="python", warnings=False))
        if isinstance(value, GuidelineBasis):
            return GuidelineBasis.model_validate(value.model_dump(mode="python", warnings=False))
        raw = dict(value)
        if "endpoint_family_ids" in raw or "endpoint_family_id" in raw or "track" in raw:
            return GuidanceEvidence.model_validate(raw)
        return GuidelineBasis.model_validate(raw)
    except (ValidationError, TypeError, ValueError) as error:
        raise EndpointBasisError(f"指南依据重新校验失败：{error}") from error


def _validated_guidance_tuple(
    values: Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]],
) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
    validated = tuple(_validated_guidance(value) for value in values)
    try:
        validate_guideline_lineage(validated)
    except ValueError as error:
        raise EndpointBasisError(f"指南谱系校验失败：{error}") from error
    return validated


def select_current_guidance(
    guidelines: Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]],
    *,
    jurisdiction: str | None = None,
    population_context: str | None = None,
    development_context: str | None = None,
    track: GuidanceTrack | str | None = None,
) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
    """仅选择当前最终指南；草案及废止/已替代版本永不驱动默认。"""

    validated = _validated_guidance_tuple(guidelines)
    normalized_jurisdiction = (
        None if jurisdiction is None else _text(jurisdiction, field_name="司法辖区").casefold()
    )
    normalized_population = (
        None if population_context is None else _text(population_context, field_name="适用人群")
    )
    normalized_development = (
        None if development_context is None else _text(development_context, field_name="研发语境")
    )
    expected_track = None if track is None else GuidanceTrack(_normalize_guidance_track(track))
    selected = tuple(
        item
        for item in validated
        if item.can_drive_current_default
        and (
            normalized_jurisdiction is None
            or item.jurisdiction.strip().casefold() == normalized_jurisdiction
        )
        and (normalized_population is None or item.population_context == normalized_population)
        and (normalized_development is None or item.development_context == normalized_development)
        and (expected_track is None or _guidance_track(item) is expected_track)
    )
    # 不按 CDE/FDA 选择优先级；排序只保证稳定可复现。
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                _guidance_track(item).value,
                item.guideline_series_id,
                item.version_date,
                item.guideline_version_id,
            ),
        )
    )


# 语义更直观的别名，保留一个实现。
select_current_guideline_evidence = select_current_guidance


class EndpointBasisObservation(BaseModel):
    """一条进入终点采用依据的原始观察及其当前兼容结果。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    observation: EndpointObservation
    compatibility: EndpointCompatibilityResult | None = None
    product_id: str | None = None
    study_role: str | None = None
    source_version_id: str | None = None
    source_locator: EvidenceLocator | None = None

    @field_validator("product_id", "study_role", "source_version_id")
    @classmethod
    def _optional_record_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="终点依据记录字段")

    @model_validator(mode="after")
    def _compatibility_identity(self) -> Self:
        if self.compatibility is not None and (
            self.compatibility.observation.observation_id != self.observation.observation_id
            or self.compatibility.observation.trial_id != self.observation.trial_id
        ):
            raise ValueError("终点兼容结果必须绑定同一原始观察")
        return self

    @property
    def observation_id(self) -> str:
        return self.observation.observation_id

    @property
    def trial_id(self) -> str:
        return self.observation.trial_id

    @property
    def endpoint_role(self) -> str:
        return self.observation.endpoint_role

    @property
    def endpoint_family_id(self) -> str | None:
        if self.compatibility is None:
            return None
        return self.compatibility.endpoint_rule_id


# Compatibility names for callers that call these rows "evidence" or "records".
EndpointEvidence = EndpointBasisObservation
CompetitorEndpointEvidence = EndpointBasisObservation


class GuidanceBasisGroup(BaseModel):
    """同一终点族内相同人群/研发语境的指南依据组。

    CDE 与 FDA 在同一组内平行保存；语境不兼容时分成不同组，而不是以
    一个优先级或一个标签覆盖另一条依据。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint_family_id: str
    population_context: str
    development_context: str
    guidance_evidence: tuple[GuidanceEvidence | GuidelineBasis, ...] = ()
    merge_reason_zh: str
    split_reason_zh: str | None = None

    @field_validator(
        "endpoint_family_id",
        "population_context",
        "development_context",
        "merge_reason_zh",
    )
    @classmethod
    def _group_text(cls, value: str) -> str:
        return _text(value, field_name="指南依据组字段")

    @field_validator("split_reason_zh")
    @classmethod
    def _group_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="指南依据分列理由")

    @model_validator(mode="after")
    def _group_consistency(self) -> Self:
        if not self.guidance_evidence:
            raise ValueError("指南依据组必须保留至少一条原始指南依据")
        ids = tuple(item.guideline_version_id for item in self.guidance_evidence)
        if len(set(ids)) != len(ids):
            raise ValueError("指南依据组的版本标识不得重复")
        if any(
            item.population_context != self.population_context
            or item.development_context != self.development_context
            for item in self.guidance_evidence
        ):
            raise ValueError("适用人群或研发语境不同的指南必须分列")
        return self

    @property
    def current_guidance_evidence(
        self,
    ) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return tuple(item for item in self.guidance_evidence if item.can_drive_current_default)

    @property
    def draft_guidance_evidence(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return tuple(item for item in self.guidance_evidence if item.guidance_status == "draft")

    @property
    def historical_guidance_evidence(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return tuple(
            item
            for item in self.guidance_evidence
            if item.lifecycle_status in {"superseded", "withdrawn"}
        )

    @property
    def cde_guidance(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return tuple(
            item for item in self.guidance_evidence if _guidance_track(item) is GuidanceTrack.CDE
        )

    @property
    def fda_guidance(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return tuple(
            item for item in self.guidance_evidence if _guidance_track(item) is GuidanceTrack.FDA
        )

    @property
    def guidance_group_id(self) -> str:
        return "::".join(
            (self.endpoint_family_id, self.population_context, self.development_context)
        )


class EndpointBasis(BaseModel):
    """一个兼容终点族的监管/竞品采用依据。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _field_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        aliases = {
            "family_id": "endpoint_family_id",
            "endpoint_family": "endpoint_family_id",
            "endpoint_label_zh": "endpoint_family_label_zh",
            "family_label_zh": "endpoint_family_label_zh",
            "label_zh": "endpoint_family_label_zh",
            "regulatory_guidance": "guidance_evidence",
            "guidelines": "guidance_evidence",
            "guidance": "guidance_evidence",
            "primary_hit_trial_ids": "hit_trial_ids",
            "primary_trial_ids": "hit_trial_ids",
            "denominator": "denominator_trial_ids",
            "basis_records": "endpoint_records",
            "consensus_status": "adoption_status",
            "adoption": "adoption_status",
            "consensus_label_zh": "adoption_label_zh",
        }
        for source, target in aliases.items():
            if target not in payload and source in payload:
                payload[target] = payload[source]
            payload.pop(source, None)
        return payload

    endpoint_family_id: str
    endpoint_family_label_zh: str
    compatibility_rule_ids: tuple[str, ...] = Field(min_length=1)
    compatibility_keys: tuple[tuple[str, str], ...] = ()
    guidance_evidence: tuple[GuidanceEvidence | GuidelineBasis, ...] = ()
    guidance_groups: tuple[GuidanceBasisGroup, ...] = ()
    current_guidance_evidence: tuple[GuidanceEvidence | GuidelineBasis, ...] = ()
    denominator_trial_ids: tuple[str, ...]
    hit_trial_ids: tuple[str, ...]
    endpoint_records: tuple[EndpointBasisObservation, ...] = ()
    original_endpoint_roles: tuple[str, ...] = ()
    merge_reason_zh: str
    split_reasons_zh: tuple[str, ...] = ()
    adoption_status: EndpointAdoptionStatus = EndpointAdoptionStatus.NOT_SELECTED
    adoption_label_zh: str | None = None
    strict_majority_required: int = Field(ge=1)

    @field_validator("adoption_status", mode="before")
    @classmethod
    def _adoption_status_alias(cls, value: Any) -> Any:
        return _normalize_adoption_status(value)

    @field_validator(
        "endpoint_family_id",
        "endpoint_family_label_zh",
        "merge_reason_zh",
    )
    @classmethod
    def _basis_text(cls, value: str) -> str:
        return _text(value, field_name="终点依据字段")

    @field_validator("compatibility_rule_ids", "denominator_trial_ids", "hit_trial_ids")
    @classmethod
    def _basis_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value, field_name="终点依据标识") for value in values)
        if len(set(item.casefold() for item in normalized)) != len(normalized):
            raise ValueError("终点依据标识不得重复")
        return normalized

    @field_validator("original_endpoint_roles", "split_reasons_zh")
    @classmethod
    def _basis_text_tuple(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_text(value, field_name="终点依据文本") for value in values)

    @field_validator("adoption_label_zh")
    @classmethod
    def _optional_label(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="终点采用标签")

    @model_validator(mode="after")
    def _basis_consistency(self) -> Self:
        if self.strict_majority_required != self.denominator_count // 2 + 1:
            raise ValueError("严格多数门槛必须由当前分母确定性计算")
        denominator = {item.casefold() for item in self.denominator_trial_ids}
        hits = {item.casefold() for item in self.hit_trial_ids}
        if not hits <= denominator:
            raise ValueError("终点命中试验必须属于锁定核心试验分母")
        if self.endpoint_records and not self.compatibility_keys:
            raise ValueError("有竞品观察的终点依据必须保存兼容规则键")
        if any(
            len(key) != 2 or key[0] != self.endpoint_family_id for key in self.compatibility_keys
        ):
            raise ValueError("终点依据兼容键必须绑定当前终点族")
        if len(set(self.compatibility_keys)) != len(self.compatibility_keys):
            raise ValueError("终点依据兼容键不得重复")
        if any(rule_id != self.endpoint_family_id for rule_id in self.compatibility_rule_ids):
            raise ValueError("终点依据规则标识必须与终点族一致")
        record_ids = tuple(item.observation_id for item in self.endpoint_records)
        if len(set(record_ids)) != len(record_ids):
            raise ValueError("终点依据原始观察标识不得重复")
        for item in self.endpoint_records:
            compatibility = item.compatibility
            if compatibility is None or not compatibility.compatible:
                raise ValueError("终点依据记录必须保存已命中的兼容结果")
            if compatibility.endpoint_rule_id != self.endpoint_family_id:
                raise ValueError("终点依据记录与终点族不一致")
            if item.trial_id.casefold() not in denominator:
                raise ValueError("终点依据记录必须属于锁定核心试验分母")
        guidance_ids = tuple(item.guideline_version_id for item in self.guidance_evidence)
        if len(set(guidance_ids)) != len(guidance_ids):
            raise ValueError("终点依据指南版本标识不得重复")
        group_ids = tuple(group.guidance_group_id for group in self.guidance_groups)
        if len(set(group_ids)) != len(group_ids):
            raise ValueError("终点依据指南语境组不得重复")
        flattened = tuple(
            item.guideline_version_id
            for group in self.guidance_groups
            for item in group.guidance_evidence
        )
        if set(flattened) != set(guidance_ids):
            raise ValueError("终点依据指南必须完整保留且只属于一个语境组")
        current_ids = {item.guideline_version_id for item in self.current_guidance_evidence}
        if not current_ids <= set(guidance_ids):
            raise ValueError("默认指南必须属于完整指南谱系")
        if any(not item.can_drive_current_default for item in self.current_guidance_evidence):
            raise ValueError("草案和废止/已替代指南不得驱动当前默认")
        expected_label = {
            EndpointAdoptionStatus.NOT_SELECTED: None,
            EndpointAdoptionStatus.STRICT_MAJORITY: "多数竞品采用",
            EndpointAdoptionStatus.MOST_COMMON: "最常采用",
        }[self.adoption_status]
        if self.adoption_label_zh != expected_label:
            raise ValueError("终点采用状态与中文标签不一致")
        if self.adoption_status is EndpointAdoptionStatus.STRICT_MAJORITY and not (
            self.denominator_count >= 2 and self.hit_count >= self.strict_majority_required
        ):
            raise ValueError("严格多数标签需要至少两项核心试验且命中超过半数")
        if self.adoption_status is EndpointAdoptionStatus.MOST_COMMON and self.hit_count < 2:
            raise ValueError("最常采用标签至少需要命中两项核心试验")
        return self

    @property
    def denominator_count(self) -> int:
        return len(self.denominator_trial_ids)

    @property
    def hit_count(self) -> int:
        return len(self.hit_trial_ids)

    @property
    def primary_hit_trial_ids(self) -> tuple[str, ...]:
        return self.hit_trial_ids

    @property
    def primary_hit_count(self) -> int:
        return self.hit_count

    @property
    def denominator(self) -> tuple[str, ...]:
        return self.denominator_trial_ids

    @property
    def compatibility_rule_id(self) -> str:
        return self.endpoint_family_id

    @property
    def matched_rule_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(rule_id for key in self.compatibility_keys for rule_id in key))

    @property
    def endpoint_compatibility_rule_id(self) -> str:
        return self.endpoint_family_id

    @property
    def timepoint_compatibility_rule_ids(self) -> tuple[str, ...]:
        return self.timepoint_rule_ids

    @property
    def timepoint_rule_ids(self) -> tuple[str, ...]:
        return tuple(key[1] for key in self.compatibility_keys)

    @property
    def basis_records(self) -> tuple[EndpointBasisObservation, ...]:
        return self.endpoint_records

    @property
    def regulatory_guidance(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return self.guidance_evidence

    @property
    def regulatory_basis(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return self.guidance_evidence

    @property
    def guideline_version_ids(self) -> tuple[str, ...]:
        return tuple(item.guideline_version_id for item in self.guidance_evidence)

    @property
    def guidance_locators(self) -> tuple[EvidenceLocator, ...]:
        return tuple(item.locator for item in self.guidance_evidence)

    @property
    def adoption_label(self) -> str | None:
        return self.adoption_label_zh

    @property
    def consensus_status(self) -> EndpointAdoptionStatus:
        return self.adoption_status

    @property
    def majority_threshold(self) -> int:
        return self.strict_majority_required

    @property
    def split_reason_zh(self) -> str | None:
        return self.split_reasons_zh[0] if self.split_reasons_zh else None

    @property
    def endpoint_rule_id(self) -> str:
        return self.endpoint_family_id

    @property
    def family_id(self) -> str:
        return self.endpoint_family_id

    @property
    def label_zh(self) -> str:
        return self.endpoint_family_label_zh

    @property
    def current_guidelines(
        self,
    ) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return self.current_guidance_evidence

    @property
    def guidelines(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return self.guidance_evidence

    @property
    def cde_guidance(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return tuple(
            item for item in self.guidance_evidence if _guidance_track(item) is GuidanceTrack.CDE
        )

    @property
    def fda_guidance(self) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
        return tuple(
            item for item in self.guidance_evidence if _guidance_track(item) is GuidanceTrack.FDA
        )

    @property
    def guidance_tracks(self) -> tuple[GuidanceTrack, ...]:
        return tuple(
            track
            for track in GuidanceTrack
            if any(_guidance_track(item) is track for item in self.guidance_evidence)
        )

    @property
    def consensus_label_zh(self) -> str | None:
        return self.adoption_label_zh

    @property
    def is_strict_majority(self) -> bool:
        return self.adoption_status is EndpointAdoptionStatus.STRICT_MAJORITY

    @property
    def is_most_common(self) -> bool:
        return self.adoption_status is EndpointAdoptionStatus.MOST_COMMON


class EndpointBasisSet(BaseModel):
    """完整终点族依据集合；保留分母一致性和确定性顺序。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bases: tuple[EndpointBasis, ...]
    denominator_trial_ids: tuple[str, ...]

    @model_validator(mode="after")
    def _set_consistency(self) -> Self:
        ids = tuple(item.endpoint_family_id for item in self.bases)
        if len(set(ids)) != len(ids):
            raise ValueError("终点依据集合的终点族不得重复")
        if any(item.denominator_trial_ids != self.denominator_trial_ids for item in self.bases):
            raise ValueError("所有终点依据必须使用同一锁定核心试验分母")
        return self

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.bases)

    def __len__(self) -> int:
        return len(self.bases)

    def __getitem__(self, index: int) -> EndpointBasis:
        return self.bases[index]


def validate_endpoint_basis(
    value: EndpointBasis | Mapping[str, Any],
) -> EndpointBasis:
    """在下游消费前重跑终点依据模型校验。"""

    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, EndpointBasis)
            else dict(value)
        )
        return EndpointBasis.model_validate(raw)
    except (ValidationError, TypeError, ValueError) as error:
        raise EndpointBasisError(f"终点依据重新校验失败：{error}") from error


def validate_endpoint_basis_set(
    value: EndpointBasisSet | Mapping[str, Any],
) -> EndpointBasisSet:
    """在下游消费前重跑终点依据集合校验。"""

    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, EndpointBasisSet)
            else dict(value)
        )
        return EndpointBasisSet.model_validate(raw)
    except (ValidationError, TypeError, ValueError) as error:
        raise EndpointBasisError(f"终点依据集合重新校验失败：{error}") from error


# Internal model aliases used by alternate report adapters.
EndpointBasisRecord = EndpointBasis
EndpointConsensus = EndpointBasis


def _validated_endpoint_policy(
    policy: EndpointCompatibilityPolicy | Path | str | None,
) -> EndpointCompatibilityPolicy:
    try:
        if policy is None or isinstance(policy, (Path, str)):
            return load_endpoint_compatibility_policy(policy)
        return EndpointCompatibilityPolicy.model_validate(
            policy.model_dump(mode="python", warnings=False)
        )
    except (ValidationError, TypeError, ValueError, EndpointCompatibilityError) as error:
        raise EndpointBasisError(f"终点兼容策略重新校验失败：{error}") from error


def _validated_timepoint_policy(
    policy: TimepointCompatibilityPolicy | Path | str | None,
) -> TimepointCompatibilityPolicy:
    try:
        if policy is None or isinstance(policy, (Path, str)):
            return load_timepoint_compatibility_policy(policy)
        return TimepointCompatibilityPolicy.model_validate(
            policy.model_dump(mode="python", warnings=False)
        )
    except (ValidationError, TypeError, ValueError, EndpointCompatibilityError) as error:
        raise EndpointBasisError(f"时间窗兼容策略重新校验失败：{error}") from error


def _validated_observation(value: EndpointObservation | Mapping[str, Any]) -> EndpointObservation:
    try:
        if isinstance(value, EndpointObservation):
            raw = value.model_dump(mode="python", warnings=False)
        else:
            raw = dict(value)
        return EndpointObservation.model_validate(raw)
    except (ValidationError, TypeError, ValueError) as error:
        raise EndpointBasisError(f"终点观察重新校验失败：{error}") from error


def _validated_compatibility(
    value: EndpointCompatibilityResult,
) -> EndpointCompatibilityResult:
    try:
        return EndpointCompatibilityResult.model_validate(
            value.model_dump(mode="python", warnings=False)
        )
    except (ValidationError, TypeError, ValueError) as error:
        raise EndpointBasisError(f"终点兼容结果重新校验失败：{error}") from error


def _metadata_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        if key in payload:
            value = payload.pop(key)
            if value is None:
                return None
            if not isinstance(value, str):
                raise EndpointBasisError(f"终点依据字段 {key} 必须是文本")
            return _optional_text(value, field_name="终点依据字段")
    return None


def _coerce_endpoint_basis_observation(
    value: EndpointBasisObservation
    | EndpointObservation
    | EndpointCompatibilityResult
    | Mapping[str, Any],
    *,
    endpoint_policy: EndpointCompatibilityPolicy,
    timepoint_policy: TimepointCompatibilityPolicy,
) -> EndpointBasisObservation:
    supplied_compatibility: EndpointCompatibilityResult | None = None
    if isinstance(value, EndpointBasisObservation):
        try:
            envelope = EndpointBasisObservation.model_validate(
                value.model_dump(mode="python", warnings=False)
            )
        except (ValidationError, TypeError, ValueError) as error:
            raise EndpointBasisError(f"终点依据记录重新校验失败：{error}") from error
        observation = _validated_observation(envelope.observation)
        supplied_compatibility = (
            None
            if envelope.compatibility is None
            else _validated_compatibility(envelope.compatibility)
        )
        metadata = envelope
    elif isinstance(value, EndpointCompatibilityResult):
        supplied_compatibility = _validated_compatibility(value)
        observation = _validated_observation(supplied_compatibility.observation)
        metadata = EndpointBasisObservation(observation=observation)
    elif isinstance(value, EndpointObservation):
        observation = _validated_observation(value)
        metadata = EndpointBasisObservation(observation=observation)
    else:
        payload = dict(value)
        nested = payload.pop("observation", None)
        supplied_raw = payload.pop("compatibility", None)
        if supplied_raw is not None:
            try:
                supplied_compatibility = _validated_compatibility(
                    supplied_raw
                    if isinstance(supplied_raw, EndpointCompatibilityResult)
                    else EndpointCompatibilityResult.model_validate(supplied_raw)
                )
            except (ValidationError, TypeError, ValueError) as error:
                raise EndpointBasisError(f"终点兼容结果重新校验失败：{error}") from error
        if nested is not None:
            observation = _validated_observation(nested)
        else:
            # 只从显式信封字段移除元数据；剩余内容必须完全通过 Task 6.1 模型。
            for key in (
                "product_id",
                "product",
                "study_role",
                "trial_role",
                "source_version_id",
                "source_version",
                "source_locator",
                "locator",
            ):
                payload.pop(key, None)
            observation = _validated_observation(payload)
        raw_product = dict(value)
        product_id = _metadata_text(raw_product, "product_id", "product")
        study_role = _metadata_text(raw_product, "study_role", "trial_role")
        source_version_id = _metadata_text(raw_product, "source_version_id", "source_version")
        raw_locator = raw_product.pop("source_locator", raw_product.pop("locator", None))
        source_locator = None
        if raw_locator is not None:
            try:
                source_locator = (
                    raw_locator
                    if isinstance(raw_locator, EvidenceLocator)
                    else EvidenceLocator.model_validate(raw_locator)
                )
            except (ValidationError, TypeError, ValueError) as error:
                raise EndpointBasisError(f"终点来源定位重新校验失败：{error}") from error
        metadata = EndpointBasisObservation(
            observation=observation,
            product_id=product_id,
            study_role=study_role,
            source_version_id=source_version_id,
            source_locator=source_locator,
        )
    computed = match_endpoint_compatibility(
        observation,
        endpoint_policy=endpoint_policy,
        timepoint_policy=timepoint_policy,
    )
    if supplied_compatibility is not None and supplied_compatibility != computed:
        raise EndpointBasisError("终点兼容结果必须由当前观察和当前规则重新计算")
    try:
        return EndpointBasisObservation(
            observation=observation,
            compatibility=computed,
            product_id=metadata.product_id,
            study_role=metadata.study_role,
            source_version_id=metadata.source_version_id,
            source_locator=metadata.source_locator,
        )
    except (ValidationError, TypeError, ValueError) as error:
        raise EndpointBasisError(f"终点依据记录构建失败：{error}") from error


def _core_trial_ids(
    core_trial_ids: Sequence[str] | None,
    core_trials: Sequence[Any] | None,
) -> tuple[str, ...]:
    values: Sequence[Any]
    if core_trial_ids is not None and core_trials is not None:
        raise EndpointBasisError("锁定核心试验不得同时通过两个参数提供")
    if core_trials is not None:
        values = core_trials
    elif core_trial_ids is not None:
        values = core_trial_ids
    else:
        raise EndpointBasisError("必须提供锁定适格核心试验集合")
    parsed: list[str] = []
    for item in values:
        role_raw: Any = None
        if isinstance(item, str):
            trial_id = item
        elif isinstance(item, Mapping):
            trial_id_raw = item.get("trial_id", item.get("study_id"))
            role_raw = item.get("study_role", item.get("role"))
            if not isinstance(trial_id_raw, str):
                raise EndpointBasisError("锁定核心试验必须提供试验标识")
            trial_id = trial_id_raw
        else:
            trial_id_raw = getattr(item, "trial_id", getattr(item, "study_id", None))
            role_raw = getattr(item, "study_role", getattr(item, "role", None))
            if not isinstance(trial_id_raw, str):
                raise EndpointBasisError("锁定核心试验必须提供试验标识")
            trial_id = trial_id_raw
        if role_raw is not None and not isinstance(role_raw, str):
            role_raw = str(role_raw)
        if not _is_eligible_study_role(role_raw):
            continue
        parsed.append(_text(trial_id, field_name="核心试验标识"))
    if not parsed:
        raise EndpointBasisError("锁定核心试验集合不得为空")
    if len({item.casefold() for item in parsed}) != len(parsed):
        raise EndpointBasisError("锁定核心试验标识不得重复")
    return tuple(parsed)


def _is_primary_endpoint(role: str) -> bool:
    return _normalized_token(role) in _PRIMARY_ENDPOINT_ROLE_TOKENS


def _is_eligible_study_role(role: str | None) -> bool:
    return role is None or _normalized_token(role) in _CORE_STUDY_ROLE_TOKENS


def _guidance_for_family(
    family_id: str,
    *,
    all_guidance: tuple[GuidanceEvidence | GuidelineBasis, ...],
    guidance_by_endpoint: Mapping[
        str, Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]]
    ]
    | None,
) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
    if guidance_by_endpoint is None:
        candidates = all_guidance
    else:
        matching_key = next(
            (key for key in guidance_by_endpoint if key.casefold() == family_id.casefold()),
            None,
        )
        if matching_key is None:
            return ()
        candidates = _validated_guidance_tuple(guidance_by_endpoint[matching_key])
    return tuple(
        item
        for item in candidates
        if not isinstance(item, GuidanceEvidence)
        or not item.endpoint_family_ids
        or any(endpoint.casefold() == family_id.casefold() for endpoint in item.endpoint_family_ids)
    )


def _sorted_guidance(
    values: Sequence[GuidanceEvidence | GuidelineBasis],
) -> tuple[GuidanceEvidence | GuidelineBasis, ...]:
    return tuple(
        sorted(
            values,
            key=lambda item: (
                item.guideline_series_id,
                item.version_date,
                item.guideline_version_id,
            ),
        )
    )


def _guidance_groups(
    family_id: str,
    guidance: tuple[GuidanceEvidence | GuidelineBasis, ...],
) -> tuple[GuidanceBasisGroup, ...]:
    by_context: dict[tuple[str, str], list[GuidanceEvidence | GuidelineBasis]] = {}
    for item in guidance:
        by_context.setdefault((item.population_context, item.development_context), []).append(item)
    contexts = sorted(by_context)
    groups: list[GuidanceBasisGroup] = []
    for index, (population, development) in enumerate(contexts):
        evidence = _sorted_guidance(by_context[(population, development)])
        split_reason = None
        if len(contexts) > 1:
            split_reason = "适用人群或研发语境不同，指南依据分列展示，不强行合并"
        try:
            groups.append(
                GuidanceBasisGroup(
                    endpoint_family_id=family_id,
                    population_context=population,
                    development_context=development,
                    guidance_evidence=evidence,
                    merge_reason_zh=(
                        "终点兼容规则、适用人群和研发语境一致；CDE/FDA 依据平行展示，不设优先级"
                    ),
                    split_reason_zh=split_reason,
                )
            )
        except (ValidationError, TypeError, ValueError) as error:
            raise EndpointBasisError(f"指南依据语境组构建失败（{index}）：{error}") from error
    return tuple(groups)


def _build_basis(
    *,
    family_id: str,
    label_zh: str,
    records: tuple[EndpointBasisObservation, ...],
    denominator_trial_ids: tuple[str, ...],
    guidance: tuple[GuidanceEvidence | GuidelineBasis, ...],
) -> EndpointBasis:
    canonical_trial_id = {item.casefold(): item for item in denominator_trial_ids}
    hit_ids = tuple(
        canonical_trial_id[trial_key]
        for trial_key in sorted(
            {
                item.trial_id.casefold()
                for item in records
                if _is_primary_endpoint(item.endpoint_role)
            }
        )
    )
    compatibility_keys = tuple(
        sorted(
            {
                item.compatibility.compatibility_key
                for item in records
                if item.compatibility is not None
                and item.compatibility.compatibility_key is not None
            }
        )
    )
    roles = tuple(
        sorted(
            {item.endpoint_role for item in records},
            key=lambda value: (value.casefold(), value),
        )
    )
    groups = _guidance_groups(family_id, guidance)
    current = tuple(item for item in guidance if item.can_drive_current_default)
    current = _sorted_guidance(current)
    denominator_count = len(denominator_trial_ids)
    strict_majority_required = denominator_count // 2 + 1
    try:
        return EndpointBasis(
            endpoint_family_id=family_id,
            endpoint_family_label_zh=label_zh,
            compatibility_rule_ids=(family_id,),
            compatibility_keys=compatibility_keys,
            guidance_evidence=_sorted_guidance(guidance),
            guidance_groups=groups,
            current_guidance_evidence=current,
            denominator_trial_ids=denominator_trial_ids,
            hit_trial_ids=hit_ids,
            endpoint_records=records,
            original_endpoint_roles=roles,
            merge_reason_zh=("同一版本化终点兼容规则命中；原始终点、角色和时间窗兼容键全部保留"),
            split_reasons_zh=tuple(
                sorted(
                    {
                        reason
                        for group in groups
                        if group.split_reason_zh is not None
                        for reason in (group.split_reason_zh,)
                    }
                )
            ),
            adoption_status=EndpointAdoptionStatus.NOT_SELECTED,
            adoption_label_zh=None,
            strict_majority_required=strict_majority_required,
        )
    except (ValidationError, TypeError, ValueError) as error:
        raise EndpointBasisError(f"终点依据构建失败：{error}") from error


def build_endpoint_basis(
    observations: Sequence[
        EndpointBasisObservation
        | EndpointObservation
        | EndpointCompatibilityResult
        | Mapping[str, Any]
    ]
    | None = None,
    *,
    endpoint_observations: Sequence[
        EndpointBasisObservation
        | EndpointObservation
        | EndpointCompatibilityResult
        | Mapping[str, Any]
    ]
    | None = None,
    core_trial_ids: Sequence[str] | None = None,
    core_trials: Sequence[Any] | None = None,
    guidelines: Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]] = (),
    guidance_evidence: Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]]
    | None = None,
    guidance_by_endpoint: Mapping[
        str, Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]]
    ]
    | None = None,
    endpoint_policy: EndpointCompatibilityPolicy | Path | str | None = None,
    timepoint_policy: TimepointCompatibilityPolicy | Path | str | None = None,
) -> tuple[EndpointBasis, ...]:
    """从锁定核心试验和原始终点观察构建全部终点族依据。

    - 分母严格等于 ``core_trial_ids``/``core_trials``，不从观察记录推导。
    - 只有原始角色为主要终点的核心试验计入命中；同一试验在同一族内去重。
    - 严格多数优先；若全体族均无严格多数，只将最高命中且至少两项试验
      的族标记为“最常采用”。
    - CDE/FDA 及历史/草案版本均保留；只有当前最终版本进入
      ``current_guidance_evidence``。
    """

    if observations is not None and endpoint_observations is not None:
        raise EndpointBasisError("终点观察不得同时通过两个参数提供")
    source_observations = (
        endpoint_observations if endpoint_observations is not None else observations
    )
    if source_observations is None:
        raise EndpointBasisError("必须提供终点观察")
    denominator = _core_trial_ids(core_trial_ids, core_trials)
    endpoint_rules = _validated_endpoint_policy(endpoint_policy)
    timepoint_rules = _validated_timepoint_policy(timepoint_policy)
    if guidance_evidence is not None and guidelines:
        raise EndpointBasisError("指南依据不得同时通过两个参数提供")
    supplied_guidance = guidelines if guidance_evidence is None else guidance_evidence
    all_guidance = _validated_guidance_tuple(supplied_guidance)
    if guidance_by_endpoint is not None:
        # 先验证所有分支；不允许一个坏分支被未命中终点掩盖。
        for branch in guidance_by_endpoint.values():
            _validated_guidance_tuple(branch)

    canonical_trials = {item.casefold() for item in denominator}
    normalized_records: list[EndpointBasisObservation] = []
    seen_observation_ids: set[str] = set()
    for item in source_observations:
        record = _coerce_endpoint_basis_observation(
            item,
            endpoint_policy=endpoint_rules,
            timepoint_policy=timepoint_rules,
        )
        if record.trial_id.casefold() not in canonical_trials:
            # 支持研究/非锁定试验不得扩大分母或命中计数。
            continue
        if not _is_eligible_study_role(record.study_role):
            continue
        compatibility = record.compatibility
        if compatibility is None or not compatibility.compatible:
            # 无兼容规则的事实仍可由其他视图保留，但不得进入合并终点族。
            continue
        if compatibility.endpoint_rule_id is None:
            continue
        observation_key = record.observation_id.casefold()
        if observation_key in seen_observation_ids:
            raise EndpointBasisError("终点依据原始观察标识不得重复")
        seen_observation_ids.add(observation_key)
        normalized_records.append(record)

    by_family: dict[str, list[EndpointBasisObservation]] = {}
    for record in normalized_records:
        compatibility = record.compatibility
        assert compatibility is not None  # compatibility=True 的模型不允许此处为空
        family_id = compatibility.endpoint_rule_id
        assert family_id is not None  # compatibility=True 的模型不允许此处为空
        by_family.setdefault(family_id, []).append(record)

    explicit_guidance_families = {
        endpoint
        for item in all_guidance
        if isinstance(item, GuidanceEvidence)
        for endpoint in item.endpoint_family_ids
    }
    if guidance_by_endpoint is not None:
        explicit_guidance_families.update(guidance_by_endpoint)
    rule_by_id = {rule.rule_id.casefold(): rule for rule in endpoint_rules.rules}
    family_ids = set(by_family)
    for family_id in explicit_guidance_families:
        rule = rule_by_id.get(family_id.casefold())
        if rule is None:
            raise EndpointBasisError(f"指南依据引用了当前策略不存在的终点族：{family_id}")
        family_ids.add(rule.rule_id)

    bases: list[EndpointBasis] = []
    for family_id in sorted(family_ids):
        records = tuple(
            sorted(
                by_family.get(family_id, ()),
                key=lambda item: (
                    item.observation_id,
                    item.trial_id.casefold(),
                    item.endpoint_role.casefold(),
                ),
            )
        )
        rule = next((item for item in endpoint_rules.rules if item.rule_id == family_id), None)
        if rule is None:
            raise EndpointBasisError("兼容结果引用了当前策略不存在的终点规则")
        guidance = _guidance_for_family(
            family_id,
            all_guidance=all_guidance,
            guidance_by_endpoint=guidance_by_endpoint,
        )
        bases.append(
            _build_basis(
                family_id=family_id,
                label_zh=rule.label_zh,
                records=records,
                denominator_trial_ids=denominator,
                guidance=guidance,
            )
        )

    majority_candidates = [
        item
        for item in bases
        if item.denominator_count >= 2 and item.hit_count >= item.strict_majority_required
    ]
    if majority_candidates:
        majority_ids = {item.endpoint_family_id for item in majority_candidates}
        statuses = {
            item.endpoint_family_id: EndpointAdoptionStatus.STRICT_MAJORITY
            if item.endpoint_family_id in majority_ids
            else EndpointAdoptionStatus.NOT_SELECTED
            for item in bases
        }
    else:
        eligible = [item for item in bases if item.hit_count >= 2]
        max_hits = max((item.hit_count for item in eligible), default=0)
        most_common_ids = {
            item.endpoint_family_id for item in eligible if item.hit_count == max_hits
        }
        statuses = {
            item.endpoint_family_id: EndpointAdoptionStatus.MOST_COMMON
            if item.endpoint_family_id in most_common_ids
            else EndpointAdoptionStatus.NOT_SELECTED
            for item in bases
        }

    final_bases: list[EndpointBasis] = []
    for basis in bases:
        status = statuses[basis.endpoint_family_id]
        if status is basis.adoption_status:
            final_bases.append(basis)
            continue
        payload = basis.model_dump(mode="python", warnings=False)
        payload["adoption_status"] = status
        payload["adoption_label_zh"] = {
            EndpointAdoptionStatus.NOT_SELECTED: None,
            EndpointAdoptionStatus.STRICT_MAJORITY: "多数竞品采用",
            EndpointAdoptionStatus.MOST_COMMON: "最常采用",
        }[status]
        try:
            final_bases.append(EndpointBasis.model_validate(payload))
        except (ValidationError, TypeError, ValueError) as error:
            raise EndpointBasisError(f"终点采用状态构建失败：{error}") from error
    return tuple(final_bases)


# Plural/verb aliases keep one consensus implementation.
build_endpoint_bases = build_endpoint_basis
derive_endpoint_basis = build_endpoint_basis
resolve_endpoint_basis = build_endpoint_basis


def build_endpoint_basis_set(
    observations: Sequence[
        EndpointBasisObservation
        | EndpointObservation
        | EndpointCompatibilityResult
        | Mapping[str, Any]
    ],
    *,
    core_trial_ids: Sequence[str],
    guidelines: Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]] = (),
    guidance_by_endpoint: Mapping[
        str, Sequence[GuidanceEvidence | GuidelineBasis | Mapping[str, Any]]
    ]
    | None = None,
    endpoint_policy: EndpointCompatibilityPolicy | Path | str | None = None,
    timepoint_policy: TimepointCompatibilityPolicy | Path | str | None = None,
) -> EndpointBasisSet:
    """返回带统一分母模型的终点依据集合。"""

    denominator = _core_trial_ids(core_trial_ids, None)
    bases = build_endpoint_basis(
        observations,
        core_trial_ids=denominator,
        guidelines=guidelines,
        guidance_by_endpoint=guidance_by_endpoint,
        endpoint_policy=endpoint_policy,
        timepoint_policy=timepoint_policy,
    )
    return EndpointBasisSet(bases=bases, denominator_trial_ids=denominator)


class EfficacyViewError(ValueError):
    """疗效事实或视图无法满足来源闭合合同。"""


class EfficacyArmRole(StrEnum):
    """疗效比较中的治疗与对照两类组别。"""

    TREATMENT = "treatment"
    CONTROL = "control"

    # 输入别名只归一到两个正式组别，不创建第三种比较角色。
    ACTIVE = "treatment"
    INTERVENTION = "treatment"
    PLACEBO = "control"


ArmRole = EfficacyArmRole


class EfficacyViewKind(StrEnum):
    """B 类疗效页支持的三种图形事实投影。"""

    SINGLE_TIMEPOINT = "single_timepoint"
    LONGITUDINAL = "longitudinal"
    SOURCE_EFFECT_SIZE = "source_effect_size"

    # 森林图是来源效应量视图的图形别名，不产生另一套事实。
    EFFECT_SIZE_FOREST = "source_effect_size"


EfficacyChartKind = EfficacyViewKind


_EFFICACY_NON_CONCRETE_STATES = frozenset(
    {
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.NOT_APPLICABLE,
        FactDisclosureState.CONFLICTING,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    }
)

_ARM_ROLE_ALIASES: dict[str, str] = {
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

_DIRECTION_ALIASES: dict[str, str] = {
    "higher_is_better": "higher_is_better",
    "higher": "higher_is_better",
    "increase_is_better": "higher_is_better",
    "越高越好": "higher_is_better",
    "越高": "higher_is_better",
    "lower_is_better": "lower_is_better",
    "lower": "lower_is_better",
    "decrease_is_better": "lower_is_better",
    "越低越好": "lower_is_better",
    "越低": "lower_is_better",
}


def _efficacy_raw_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}不能为空")
    # 原始终点、单位和来源行不能被规范化文本覆盖；只检查可见内容。
    return value


def _optional_efficacy_text(value: str | None, *, field_name: str) -> str | None:
    return None if value is None else _efficacy_raw_text(value, field_name=field_name)




def _normalize_efficacy_arm_role(value: Any) -> Any:
    if isinstance(value, EfficacyArmRole):
        return value
    if not isinstance(value, str):
        return value
    token = value.strip().casefold().replace("-", "_")
    return _ARM_ROLE_ALIASES.get(token, value)


def _normalize_efficacy_direction(value: Any) -> Any:
    if isinstance(value, EndpointDirection):
        return value
    if not isinstance(value, str):
        return value
    token = value.strip().casefold().replace("-", "_").replace(" ", "_")
    return _DIRECTION_ALIASES.get(token, value)


def _parse_efficacy_compatibility_key(value: Any) -> tuple[str, str]:
    if isinstance(value, str):
        parts = tuple(part.strip() for part in value.split("::"))
    else:
        try:
            parts = tuple(value)
        except TypeError as error:
            raise ValueError("疗效事实必须提供两段兼容桶标识") from error
    if len(parts) != 2 or any(not isinstance(part, str) or not part.strip() for part in parts):
        raise ValueError("疗效事实兼容桶必须由终点规则和时间窗规则两段组成")
    return (
        _efficacy_raw_text(parts[0], field_name="终点兼容规则标识"),
        _efficacy_raw_text(parts[1], field_name="时间窗兼容规则标识"),
    )


def _coerce_efficacy_observation(value: Any) -> EndpointObservation:
    try:
        if isinstance(value, EndpointObservation):
            raw = value.model_dump(mode="python", warnings=False)
        else:
            raw = dict(value)
        return EndpointObservation.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError(f"疗效事实原始观察无效：{error}") from error


def _coerce_efficacy_compatibility(value: Any) -> EndpointCompatibilityResult:
    try:
        if isinstance(value, EndpointCompatibilityResult):
            raw = value.model_dump(mode="python", warnings=False)
        else:
            raw = dict(value)
        return EndpointCompatibilityResult.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError(f"疗效事实兼容结果无效：{error}") from error


def _timepoint_sort_key(value: int | float | str) -> tuple[int, float | str]:
    if isinstance(value, bool):
        return (1, str(value))
    if isinstance(value, (int, float)):
        return (0, float(value))
    return (1, value)


class EfficacyFactRow(BaseModel):
    """一条不可变疗效事实行；所有视图只引用该行，不重写科学事实。

    一行对应一个治疗或对照臂。``compatibility_key`` 是 Task 6.1
    终点规则与时间窗规则的原始兼容桶；``observation`` 和
    ``compatibility``（若上游提供）保留原始观察及规则血统。效应量字段
    只接受来源直接报告的值，构建视图时绝不由两臂数值相减或换算。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    row_id: str = Field(validation_alias=AliasChoices("row_id", "fact_row_id", "id"))
    source_row_id: str = Field(
        validation_alias=AliasChoices("source_row_id", "source_row", "row_ref")
    )
    observation_id: str = Field(
        validation_alias=AliasChoices("observation_id", "endpoint_observation_id")
    )
    product_id: str
    trial_id: str = Field(validation_alias=AliasChoices("trial_id", "study_id"))
    endpoint_family_id: str = Field(
        validation_alias=AliasChoices("endpoint_family_id", "endpoint_family", "family_id")
    )
    endpoint_family_label_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "endpoint_family_label_zh",
            "endpoint_label_zh",
            "family_label_zh",
        ),
    )
    compatibility_key: tuple[str, str]
    original_endpoint: str = Field(
        validation_alias=AliasChoices(
            "original_endpoint",
            "endpoint_id",
            "raw_endpoint",
            "endpoint",
        )
    )
    original_definition: str = Field(
        validation_alias=AliasChoices(
            "original_definition",
            "endpoint_definition",
            "raw_definition",
            "definition",
        )
    )
    endpoint_role: str = Field(
        validation_alias=AliasChoices("endpoint_role", "original_endpoint_role")
    )
    direction: EndpointDirection
    unit: str = Field(validation_alias=AliasChoices("unit", "original_unit", "raw_unit"))
    analysis_form: str
    actual_timepoint: int | float | str = Field(
        validation_alias=AliasChoices(
            "actual_timepoint",
            "timepoint",
            "observed_timepoint",
            "timepoint_value",
        )
    )
    actual_timepoint_unit: str = Field(
        validation_alias=AliasChoices(
            "actual_timepoint_unit",
            "time_unit",
            "observed_time_unit",
            "timepoint_unit",
        )
    )
    analysis_population: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "analysis_population",
            "analysis_population_zh",
            "population",
        ),
    )
    arm_role: EfficacyArmRole = Field(
        validation_alias=AliasChoices("arm_role", "group_role", "arm_type")
    )
    arm_id: str = Field(validation_alias=AliasChoices("arm_id", "group_id", "arm"))
    arm_label: str = Field(
        validation_alias=AliasChoices(
            "arm_label",
            "group_label",
            "group_label_zh",
            "arm_name",
        )
    )
    value: int | float | None = Field(
        default=None,
        validation_alias=AliasChoices("value", "raw_value", "observed_value"),
    )
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, ge=1)
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE
    effect_measure: str | None = Field(
        default=None,
        validation_alias=AliasChoices("effect_measure", "effect_form", "effect_type"),
    )
    effect_value: int | float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "effect_value",
            "effect_size",
            "reported_effect",
            "source_effect_size",
        ),
    )
    effect_lower: int | float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "effect_lower",
            "effect_lower_bound",
            "lower_ci",
            "ci_lower",
        ),
    )
    effect_upper: int | float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "effect_upper",
            "effect_upper_bound",
            "upper_ci",
            "ci_upper",
        ),
    )
    effect_unit: str | None = None
    comparison_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("comparison_id", "comparison_key", "arm_set_id"),
    )
    compatibility_difference_labels_zh: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("compatibility_difference_labels_zh", "difference_labels_zh"),
    )
    source_version_id: str = Field(
        validation_alias=AliasChoices("source_version_id", "source_version")
    )
    source_locator: EvidenceLocator = Field(
        validation_alias=AliasChoices("source_locator", "locator")
    )
    observation: EndpointObservation | None = None
    compatibility: EndpointCompatibilityResult | None = None

    @model_validator(mode="before")
    @classmethod
    def _expand_fact_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        raw_arm = payload.get("arm")
        aliases = {
            "fact_row_id": "row_id",
            "endpoint_family": "endpoint_family_id",
            "family_id": "endpoint_family_id",
            "endpoint_label_zh": "endpoint_family_label_zh",
            "family_label_zh": "endpoint_family_label_zh",
            "endpoint_id": "original_endpoint",
            "raw_endpoint": "original_endpoint",
            "endpoint": "original_endpoint",
            "endpoint_definition": "original_definition",
            "raw_definition": "original_definition",
            "definition": "original_definition",
            "original_endpoint_role": "endpoint_role",
            "original_unit": "unit",
            "raw_unit": "unit",
            "timepoint": "actual_timepoint",
            "observed_timepoint": "actual_timepoint",
            "timepoint_value": "actual_timepoint",
            "time_unit": "actual_timepoint_unit",
            "observed_time_unit": "actual_timepoint_unit",
            "timepoint_unit": "actual_timepoint_unit",
            "population": "analysis_population",
            "analysis_population_zh": "analysis_population",
            "group_role": "arm_role",
            "arm_type": "arm_role",
            "group_id": "arm_id",
            "group_label": "arm_label",
            "group_label_zh": "arm_label",
            "arm_name": "arm_label",
            "raw_value": "value",
            "observed_value": "value",
            "effect_size": "effect_value",
            "reported_effect": "effect_value",
            "source_effect_size": "effect_value",
            "effect_lower_bound": "effect_lower",
            "lower_ci": "effect_lower",
            "ci_lower": "effect_lower",
            "effect_upper_bound": "effect_upper",
            "upper_ci": "effect_upper",
            "ci_upper": "effect_upper",
            "effect_size_lower": "effect_lower",
            "effect_size_upper": "effect_upper",
            "ci_low": "effect_lower",
            "ci_high": "effect_upper",
            "source_line_id": "source_row_id",
            "source_line": "source_row_id",
            "source_row_ref": "source_row_id",
            "compatibility_bucket": "compatibility_bucket_id",
            "bucket_id": "compatibility_bucket_id",
            "endpoint_compatibility_rule_id": "endpoint_rule_id",
            "timepoint_compatibility_rule_id": "timepoint_rule_id",
            "difference_labels_zh": "compatibility_difference_labels_zh",
            "source_row": "source_row_id",
            "row_ref": "source_row_id",
            "source_version": "source_version_id",
            "locator": "source_locator",
            "compatibility_result": "compatibility",
            "raw_observation": "observation",
            "original_observation": "observation",
        }
        for source, target in aliases.items():
            if target not in payload and source in payload:
                payload[target] = payload[source]
            if source != target:
                payload.pop(source, None)
        if "arm_role" not in payload and raw_arm is not None:
            payload["arm_role"] = raw_arm
        if "arm_label" not in payload and raw_arm is not None:
            payload["arm_label"] = raw_arm

        raw_compatibility = payload.get("compatibility")
        compatibility: EndpointCompatibilityResult | None = None
        if raw_compatibility is not None:
            compatibility = _coerce_efficacy_compatibility(raw_compatibility)
            payload["compatibility"] = compatibility
            payload.setdefault("compatibility_key", compatibility.compatibility_key)
            payload.setdefault("endpoint_family_id", compatibility.endpoint_rule_id)
            payload.setdefault(
                "compatibility_difference_labels_zh",
                compatibility.difference_labels_zh,
            )

        raw_observation = payload.get("observation")
        if raw_observation is None and compatibility is not None:
            raw_observation = compatibility.observation
        if raw_observation is None:
            required_observation_fields = (
                "observation_id",
                "trial_id",
                "original_endpoint",
                "original_definition",
                "endpoint_role",
                "direction",
                "unit",
                "analysis_form",
                "actual_timepoint",
                "actual_timepoint_unit",
            )
            if all(field in payload for field in required_observation_fields):
                raw_observation = {
                    "observation_id": payload["observation_id"],
                    "trial_id": payload["trial_id"],
                    "endpoint_id": payload["original_endpoint"],
                    "endpoint_definition": payload["original_definition"],
                    "endpoint_role": payload["endpoint_role"],
                    "direction": _normalize_efficacy_direction(payload["direction"]),
                    "unit": payload["unit"],
                    "analysis_form": payload["analysis_form"],
                    "timepoint": payload["actual_timepoint"],
                    "time_unit": payload["actual_timepoint_unit"],
                }
        if raw_observation is not None:
            observation = _coerce_efficacy_observation(raw_observation)
            payload["observation"] = observation
            observation_fields = {
                "observation_id": observation.observation_id,
                "trial_id": observation.trial_id,
                "original_endpoint": observation.endpoint_id,
                "original_definition": observation.endpoint_definition,
                "endpoint_role": observation.endpoint_role,
                "direction": observation.direction,
                "unit": observation.unit,
                "analysis_form": observation.analysis_form,
                "actual_timepoint": observation.timepoint,
                "actual_timepoint_unit": observation.time_unit,
            }
            for key, observed in observation_fields.items():
                payload.setdefault(key, observed)

            if compatibility is None:
                compatibility = match_endpoint_compatibility(observation)
                if not compatibility.compatible:
                    raise ValueError("疗效事实必须命中当前终点与时间窗兼容规则")
                payload["compatibility"] = compatibility
                payload.setdefault("compatibility_key", compatibility.compatibility_key)
                payload.setdefault("endpoint_family_id", compatibility.endpoint_rule_id)
                payload.setdefault(
                    "compatibility_difference_labels_zh",
                    compatibility.difference_labels_zh,
                )

        if "compatibility_key" not in payload:
            endpoint_rule_id = payload.pop("endpoint_rule_id", None)
            timepoint_rule_id = payload.pop("timepoint_rule_id", None)
            if endpoint_rule_id is not None and timepoint_rule_id is not None:
                payload["compatibility_key"] = (endpoint_rule_id, timepoint_rule_id)
        else:
            payload.pop("endpoint_rule_id", None)
            payload.pop("timepoint_rule_id", None)
        raw_bucket = payload.pop("compatibility_bucket_id", None)
        if "compatibility_key" not in payload and raw_bucket is not None:
            payload["compatibility_key"] = _parse_efficacy_compatibility_key(raw_bucket)
        elif "compatibility_key" in payload:
            payload["compatibility_key"] = _parse_efficacy_compatibility_key(
                payload["compatibility_key"]
            )
        if "endpoint_family_id" not in payload and "compatibility_key" in payload:
            payload["endpoint_family_id"] = payload["compatibility_key"][0]

        if "source_row_id" not in payload and "row_id" in payload:
            # 旧输入把报告行标识同时作为来源行标识时，保留该原始身份。
            payload["source_row_id"] = payload["row_id"]
        if (
            "row_id" not in payload
            and "source_row_id" in payload
            and "source_version_id" in payload
        ):
            parts = (
                str(payload["source_version_id"]),
                str(payload["source_row_id"]),
                str(payload.get("observation_id", payload["source_row_id"])),
                str(_normalize_efficacy_arm_role(payload.get("arm_role", ""))),
            )
            payload["row_id"] = stable_id("efficacy-row", *parts)
        if "observation_id" not in payload and "source_row_id" in payload:
            payload["observation_id"] = payload["source_row_id"]
        if "disclosure_state" not in payload:
            payload["disclosure_state"] = (
                FactDisclosureState.REPORTED_VALUE
                if payload.get("value") is not None
                else FactDisclosureState.NOT_REPORTED
            )
        if "arm_role" in payload:
            payload["arm_role"] = _normalize_efficacy_arm_role(payload["arm_role"])
        if "direction" in payload:
            payload["direction"] = _normalize_efficacy_direction(payload["direction"])
        return payload

    @field_validator(
        "row_id",
        "source_row_id",
        "observation_id",
        "product_id",
        "trial_id",
        "endpoint_family_id",
        "original_endpoint",
        "original_definition",
        "endpoint_role",
        "unit",
        "analysis_form",
        "actual_timepoint_unit",
        "arm_id",
        "arm_label",
        "source_version_id",
    )
    @classmethod
    def _required_fact_text(cls, value: str) -> str:
        return _efficacy_raw_text(value, field_name="疗效事实字段")

    @field_validator(
        "endpoint_family_label_zh",
        "analysis_population",
        "effect_measure",
        "effect_unit",
    )
    def _optional_fact_text(cls, value: str | None) -> str | None:
        return _optional_efficacy_text(value, field_name="疗效事实可选字段")

    @field_validator("arm_role", mode="before")
    @classmethod
    def _arm_role_alias(cls, value: Any) -> Any:
        return _normalize_efficacy_arm_role(value)

    @field_validator("direction", mode="before")
    @classmethod
    def _direction_alias(cls, value: Any) -> Any:
        return _normalize_efficacy_direction(value)

    @field_validator("compatibility_key", mode="before")
    @classmethod
    def _compatibility_key_shape(cls, value: Any) -> tuple[str, str]:
        return _parse_efficacy_compatibility_key(value)

    @field_validator("compatibility_difference_labels_zh", mode="before")
    @classmethod
    def _difference_labels(cls, value: Any) -> tuple[str, ...]:
        return tuple(
            _efficacy_raw_text(str(item), field_name="兼容差异标签")
            for item in _as_tuple(value)
        )

    @field_validator("actual_timepoint")
    @classmethod
    def _timepoint_scalar(cls, value: int | float | str) -> int | float | str:
        if isinstance(value, bool):
            raise ValueError("实际时间点不得为布尔值")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("实际时间点必须是有限数值")
        if isinstance(value, str):
            _efficacy_raw_text(value, field_name="实际时间点")
        return value

    @field_validator("value", "effect_value", "effect_lower", "effect_upper")
    @classmethod
    def _finite_fact_number(cls, value: int | float | None) -> int | float | None:
        if isinstance(value, bool):
            raise ValueError("疗效事实数值不得为布尔值")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("疗效事实数值必须是有限数值")
        return value

    @model_validator(mode="after")
    def _fact_integrity(self) -> Self:
        if self.compatibility_key[0] != self.endpoint_family_id:
            raise ValueError("疗效事实终点族必须与兼容桶第一段一致")
        if self.value is not None and self.disclosure_state in _EFFICACY_NON_CONCRETE_STATES:
            raise ValueError("未报告或不可用疗效状态不得携带确定数值")
        if self.disclosure_state is FactDisclosureState.REPORTED_ZERO and self.value != 0:
            raise ValueError("reported_zero 状态必须保存来源直接报告的零值")
        if self.numerator is not None and self.denominator is None:
            raise ValueError("疗效分子必须绑定来源直接报告的分母")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("疗效分子不得大于分母")
        if (
            self.disclosure_state is FactDisclosureState.REPORTED_VALUE
            and self.value is None
        ):
            raise ValueError("reported_value 状态必须保存来源直接报告的数值")
        if self.effect_value is None and (
            self.effect_lower is not None or self.effect_upper is not None
        ):
            raise ValueError("效应量区间必须绑定来源直接报告的效应量")
        if (
            self.effect_lower is not None
            and self.effect_upper is not None
            and self.effect_lower > self.effect_upper
        ):
            raise ValueError("效应量下限不得大于上限")
        if self.observation is None or self.compatibility is None:
            raise ValueError("疗效事实必须保存原始观察和当前兼容结果")
        observation = _coerce_efficacy_observation(self.observation)
        compatibility = _coerce_efficacy_compatibility(self.compatibility)
        object.__setattr__(self, "observation", observation)
        object.__setattr__(self, "compatibility", compatibility)
        expected = (
            observation.observation_id,
            observation.trial_id,
            observation.endpoint_id,
            observation.endpoint_definition,
            observation.endpoint_role,
            observation.direction,
            observation.unit,
            observation.analysis_form,
            observation.timepoint,
            observation.time_unit,
        )
        actual = (
            self.observation_id,
            self.trial_id,
            self.original_endpoint,
            self.original_definition,
            self.endpoint_role,
            self.direction,
            self.unit,
            self.analysis_form,
            self.actual_timepoint,
            self.actual_timepoint_unit,
        )
        if expected != actual:
            raise ValueError("疗效事实平铺字段不得覆盖原始观察")
        if not compatibility.compatible:
            raise ValueError("不兼容终点观察不得进入疗效视图")
        if compatibility.compatibility_key != self.compatibility_key:
            raise ValueError("疗效事实兼容桶必须与来源兼容结果一致")
        if compatibility.endpoint_rule_id != self.endpoint_family_id:
            raise ValueError("疗效事实终点族必须与来源兼容结果一致")
        if tuple(self.compatibility_difference_labels_zh) != tuple(
            compatibility.difference_labels_zh
        ):
            raise ValueError("疗效事实差异标签必须保留来源兼容结果")
        if observation != compatibility.observation:
            raise ValueError("疗效事实原始观察必须与来源兼容结果一致")
        return self

    @property
    def compatibility_bucket_id(self) -> str:
        return "::".join(self.compatibility_key)

    @property
    def endpoint_rule_id(self) -> str:
        return self.compatibility_key[0]

    @property
    def timepoint_rule_id(self) -> str:
        return self.compatibility_key[1]

    @property
    def raw_endpoint(self) -> str:
        return self.original_endpoint

    @property
    def endpoint(self) -> str:
        return self.original_endpoint

    @property
    def endpoint_definition(self) -> str:
        return self.original_definition

    @property
    def original_endpoint_role(self) -> str:
        return self.endpoint_role

    @property
    def locator(self) -> EvidenceLocator:
        return self.source_locator

    @property
    def original_observation(self) -> EndpointObservation:
        if self.observation is None:
            raise EfficacyViewError("疗效事实缺少原始终点观察")
        return self.observation

    @property
    def raw_definition(self) -> str:
        return self.original_definition

    @property
    def actual_timepoint_value(self) -> int | float | str:
        return self.actual_timepoint

    @property
    def timepoint(self) -> int | float | str:
        return self.actual_timepoint

    @property
    def time_unit(self) -> str:
        return self.actual_timepoint_unit

    @property
    def raw_value(self) -> int | float | None:
        return self.value

    @property
    def observed_value(self) -> int | float | None:
        return self.value

    @property
    def group_role(self) -> EfficacyArmRole:
        return self.arm_role

    @property
    def group_id(self) -> str:
        return self.arm_id

    @property
    def group_label(self) -> str:
        return self.arm_label

    @property
    def effect_size(self) -> int | float | None:
        return self.effect_value

    @property
    def effect_lower_bound(self) -> int | float | None:
        return self.effect_lower

    @property
    def effect_upper_bound(self) -> int | float | None:
        return self.effect_upper

    @property
    def source_row_ref(self) -> str:
        return self.source_row_id


class EfficacyComparison(BaseModel):
    """同一事实上下文中的治疗—对照并列关系。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    comparison_id: str
    product_id: str
    trial_id: str
    endpoint_family_id: str
    compatibility_key: tuple[str, str]
    actual_timepoint: int | float | str
    actual_timepoint_unit: str
    analysis_population: str | None
    analysis_form: str
    unit: str
    treatment: EfficacyFactRow | None = None
    control: EfficacyFactRow | None = None

    @model_validator(mode="after")
    def _comparison_integrity(self) -> Self:
        if self.treatment is None and self.control is None:
            raise ValueError("疗效并列关系至少需要一条治疗或对照事实")
        rows = tuple(row for row in (self.treatment, self.control) if row is not None)
        for row in rows:
            if row.product_id != self.product_id or row.trial_id != self.trial_id:
                raise ValueError("疗效并列关系不得跨产品或试验")
            if (
                row.endpoint_family_id != self.endpoint_family_id
                or row.compatibility_key != self.compatibility_key
                or row.actual_timepoint != self.actual_timepoint
                or row.actual_timepoint_unit != self.actual_timepoint_unit
                or row.analysis_population != self.analysis_population
                or row.analysis_form != self.analysis_form
                or row.unit != self.unit
            ):
                raise ValueError("疗效并列关系上下文必须完全一致")
        if self.treatment is not None and self.treatment.arm_role is not EfficacyArmRole.TREATMENT:
            raise ValueError("治疗列必须绑定治疗臂事实")
        if self.control is not None and self.control.arm_role is not EfficacyArmRole.CONTROL:
            raise ValueError("对照列必须绑定对照臂事实")
        if (
            self.treatment is not None
            and self.control is not None
            and self.treatment.row_id == self.control.row_id
        ):
            raise ValueError("治疗与对照不得复用同一事实行标识")
        return self

    @property
    def rows(self) -> tuple[EfficacyFactRow, ...]:
        return tuple(row for row in (self.treatment, self.control) if row is not None)

    @property
    def has_both_arms(self) -> bool:
        return self.treatment is not None and self.control is not None

    @property
    def is_drawable(self) -> bool:
        return self.has_both_arms and any(row.value is not None for row in self.rows)

    @property
    def source_row_ids(self) -> tuple[str, ...]:
        return tuple(row.source_row_id for row in self.rows)

    @property
    def compatibility_bucket_id(self) -> str:
        return "::".join(self.compatibility_key)


class EfficacyViewBase(BaseModel):
    """三类疗效视图共享的事实行和并列关系。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    view_kind: EfficacyViewKind
    endpoint_family_id: str
    compatibility_key: tuple[str, str] | None = None
    compatibility_keys: tuple[tuple[str, str], ...] = Field(min_length=1)
    rows: tuple[EfficacyFactRow, ...] = Field(min_length=1)
    comparisons: tuple[EfficacyComparison, ...] = ()

    @model_validator(mode="after")
    def _view_integrity(self) -> Self:
        row_ids = tuple(row.row_id for row in self.rows)
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("疗效视图不得包含重复事实行")
        row_keys = tuple(sorted({row.compatibility_key for row in self.rows}))
        if any(row.endpoint_family_id != self.endpoint_family_id for row in self.rows):
            raise ValueError("疗效视图不得合并不同终点族")
        if row_keys != self.compatibility_keys:
            raise ValueError("疗效视图兼容桶必须由事实行确定性派生")
        if (len(row_keys) == 1) != (self.compatibility_key is not None):
            raise ValueError("单兼容桶视图必须保存唯一兼容桶，多时间窗视图不得伪装为单桶")
        if self.compatibility_key is not None and self.compatibility_key != row_keys[0]:
            raise ValueError("疗效视图唯一兼容桶与事实行不一致")
        comparison_row_ids = tuple(
            row.row_id for comparison in self.comparisons for row in comparison.rows
        )
        if set(comparison_row_ids) != set(row_ids):
            raise ValueError("疗效视图并列关系必须完整覆盖全部事实行")
        if len(set(comparison_row_ids)) != len(comparison_row_ids):
            raise ValueError("疗效视图并列关系不得重复引用事实行")
        if any(
            comparison.endpoint_family_id != self.endpoint_family_id
            or comparison.compatibility_key not in self.compatibility_keys
            for comparison in self.comparisons
        ):
            raise ValueError("疗效视图并列关系不得越过兼容桶")
        return self

    @property
    def source_row_ids(self) -> tuple[str, ...]:
        return tuple(row.source_row_id for row in self.rows)

    @property
    def fact_rows(self) -> tuple[EfficacyFactRow, ...]:
        return self.rows

    @property
    def compatibility_bucket_id(self) -> str:
        return " | ".join("::".join(key) for key in self.compatibility_keys)

    @property
    def endpoint_rule_id(self) -> str:
        return self.endpoint_family_id

    @property
    def timepoint_rule_id(self) -> str | None:
        return self.compatibility_key[1] if self.compatibility_key is not None else None

    @property
    def fact_row_ids(self) -> tuple[str, ...]:
        return tuple(row.row_id for row in self.rows)

    @property
    def treatment_rows(self) -> tuple[EfficacyFactRow, ...]:
        return tuple(row for row in self.rows if row.arm_role is EfficacyArmRole.TREATMENT)

    @property
    def control_rows(self) -> tuple[EfficacyFactRow, ...]:
        return tuple(row for row in self.rows if row.arm_role is EfficacyArmRole.CONTROL)

    @property
    def has_renderable_values(self) -> bool:
        return any(row.value is not None for row in self.rows)

    @property
    def has_parallel_arms(self) -> bool:
        return all(comparison.has_both_arms for comparison in self.comparisons)


class SingleTimepointEfficacyView(EfficacyViewBase):
    """单一实际时间点的治疗—对照并列柱状图数据。"""

    view_kind: Literal[EfficacyViewKind.SINGLE_TIMEPOINT] = EfficacyViewKind.SINGLE_TIMEPOINT
    actual_timepoint: int | float | str
    actual_timepoint_unit: str

    @model_validator(mode="after")
    def _single_timepoint_integrity(self) -> Self:
        if len(self.compatibility_keys) != 1:
            raise ValueError("单时间点视图只能使用一个兼容桶")
        if any(
            row.actual_timepoint != self.actual_timepoint
            or row.actual_timepoint_unit != self.actual_timepoint_unit
            for row in self.rows
        ):
            raise ValueError("单时间点视图不得混合实际时间点或单位")
        return self

    @property
    def timepoint(self) -> int | float | str:
        return self.actual_timepoint

    @property
    def timepoint_unit(self) -> str:
        return self.actual_timepoint_unit


class LongitudinalEfficacyView(EfficacyViewBase):
    """同一终点族跨实际时间点的纵向折线图数据。"""

    view_kind: Literal[EfficacyViewKind.LONGITUDINAL] = EfficacyViewKind.LONGITUDINAL
    timepoints: tuple[int | float | str, ...] = Field(min_length=2)
    timepoint_unit: str

    @model_validator(mode="after")
    def _longitudinal_integrity(self) -> Self:
        actual = tuple(
            sorted(
                {row.actual_timepoint for row in self.rows},
                key=_timepoint_sort_key,
            )
        )
        if actual != self.timepoints:
            raise ValueError("纵向视图时间点必须由事实行确定性派生")
        if any(row.actual_timepoint_unit != self.timepoint_unit for row in self.rows):
            raise ValueError("纵向视图不得混合实际时间点单位")
        return self

    @property
    def actual_timepoints(self) -> tuple[int | float | str, ...]:
        return self.timepoints


class SourceEffectSizeEfficacyView(EfficacyViewBase):
    """来源直接报告效应量的非合并森林图数据。"""

    view_kind: Literal[EfficacyViewKind.SOURCE_EFFECT_SIZE] = EfficacyViewKind.SOURCE_EFFECT_SIZE
    effect_measure: str | None = None
    effect_unit: str | None = None
    effect_rows: tuple[EfficacyFactRow, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _effect_integrity(self) -> Self:
        if len(self.compatibility_keys) != 1:
            raise ValueError("来源效应量视图只能使用一个兼容桶")
        row_ids = {row.row_id for row in self.rows}
        effect_ids = {row.row_id for row in self.effect_rows}
        if not effect_ids <= row_ids:
            raise ValueError("来源效应量行必须属于同一疗效事实视图")
        if any(row.effect_value is None for row in self.effect_rows):
            raise ValueError("来源效应量视图不得包含没有直接效应量的行")
        if any(
            row.effect_measure != self.effect_measure or row.effect_unit != self.effect_unit
            for row in self.effect_rows
        ):
            raise ValueError("来源效应量视图不得混合效应量形式或单位")
        return self

    @property
    def forest_rows(self) -> tuple[EfficacyFactRow, ...]:
        return self.effect_rows

    @property
    def source_effect_rows(self) -> tuple[EfficacyFactRow, ...]:
        return self.effect_rows

    @property
    def has_renderable_effects(self) -> bool:
        return bool(self.effect_rows)


# 兼容调用方的简短模型名称；始终指向同一套实现。
SingleTimepointView = SingleTimepointEfficacyView
LongitudinalView = LongitudinalEfficacyView
SourceEffectSizeView = SourceEffectSizeEfficacyView
EffectSizeForestView = SourceEffectSizeEfficacyView

EfficacyForestView = SourceEffectSizeEfficacyView
EfficacySingleTimepointView = SingleTimepointEfficacyView
EfficacyLongitudinalView = LongitudinalEfficacyView
EfficacyEffectSizeView = SourceEffectSizeEfficacyView
EffectSizeView = SourceEffectSizeEfficacyView


class EfficacyViewSet(BaseModel):
    """三类视图的同源集合；空图形以空 tuple 表达，不伪造零值。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_rows: tuple[EfficacyFactRow, ...] = ()
    single_timepoint_views: tuple[SingleTimepointEfficacyView, ...] = ()
    longitudinal_views: tuple[LongitudinalEfficacyView, ...] = ()
    source_effect_size_views: tuple[SourceEffectSizeEfficacyView, ...] = ()

    @model_validator(mode="after")
    def _set_integrity(self) -> Self:
        by_id = {row.row_id: row for row in self.fact_rows}
        for view in (
            *self.single_timepoint_views,
            *self.longitudinal_views,
            *self.source_effect_size_views,
        ):
            for row in view.rows:
                canonical = by_id.get(row.row_id)
                if canonical is None:
                    raise ValueError("疗效视图不得引用集合外事实行")
                if row != canonical:
                    raise ValueError("同一疗效视图集合不得复制或篡改事实行")
        if len(by_id) != len(self.fact_rows):
            raise ValueError("疗效事实集合不得包含重复行标识")
        return self

    @property
    def single_timepoint(self) -> tuple[SingleTimepointEfficacyView, ...]:
        return self.single_timepoint_views

    @property
    def longitudinal(self) -> tuple[LongitudinalEfficacyView, ...]:
        return self.longitudinal_views

    @property
    def source_effect_size(self) -> tuple[SourceEffectSizeEfficacyView, ...]:
        return self.source_effect_size_views

    @property
    def effect_size_views(self) -> tuple[SourceEffectSizeEfficacyView, ...]:
        return self.source_effect_size_views

    @property
    def forest(self) -> tuple[SourceEffectSizeEfficacyView, ...]:
        return self.source_effect_size_views

    @property
    def single_timepoint_view(self) -> SingleTimepointEfficacyView | None:
        return (
            self.single_timepoint_views[0]
            if len(self.single_timepoint_views) == 1
            else None
        )

    @property
    def longitudinal_view(self) -> LongitudinalEfficacyView | None:
        return self.longitudinal_views[0] if len(self.longitudinal_views) == 1 else None

    @property
    def source_effect_size_view(self) -> SourceEffectSizeEfficacyView | None:
        return (
            self.source_effect_size_views[0]
            if len(self.source_effect_size_views) == 1
            else None
        )

    @property
    def all_views(self) -> tuple[EfficacyViewBase, ...]:
        return (
            *self.single_timepoint_views,
            *self.longitudinal_views,
            *self.source_effect_size_views,
        )


EfficacyViews = EfficacyViewSet


class EfficacySortKey(StrEnum):
    """疗效视图排序方式；默认值明确表示不按疗效信号排名。"""

    DEFAULT = "default"
    NONE = "default"
    SIGNAL = "signal"
    EFFICACY_SIGNAL = "signal"


EfficacySortMode = EfficacySortKey


class EfficacySignalState(StrEnum):
    """试验内治疗—对照信号是否可以确定性计算。"""

    KNOWN = "known"
    UNKNOWN = "unknown"


def _normalize_efficacy_sort_key(value: Any) -> Any:
    if value is None:
        return EfficacySortKey.DEFAULT
    if isinstance(value, EfficacySortKey):
        return value
    if not isinstance(value, str):
        return value

    token = value.strip().casefold().replace("-", "_").replace(" ", "_")
    return {
        "default": EfficacySortKey.DEFAULT,
        "none": EfficacySortKey.DEFAULT,
        "unsorted": EfficacySortKey.DEFAULT,
        "no_rank": EfficacySortKey.DEFAULT,
        "no_ranking": EfficacySortKey.DEFAULT,
        "默认": EfficacySortKey.DEFAULT,
        "默认顺序": EfficacySortKey.DEFAULT,
        "signal": EfficacySortKey.SIGNAL,
        "efficacy_signal": EfficacySortKey.SIGNAL,
        "user_signal": EfficacySortKey.SIGNAL,
        "ranking": EfficacySortKey.SIGNAL,
        "疗效信号": EfficacySortKey.SIGNAL,
    }.get(token, value)


class EfficacySortResult(BaseModel):
    """一个兼容桶内的可逆排序结果及显式未知状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    compatibility_key: tuple[str, str]
    sort_key: EfficacySortKey = EfficacySortKey.DEFAULT
    descending: bool = False
    rows: tuple[EfficacyFactRow, ...] = ()
    known_row_ids: tuple[str, ...] = ()
    unknown_row_ids: tuple[str, ...] = ()
    signal_states: tuple[tuple[str, EfficacySignalState], ...] = ()
    signal_by_row_id: tuple[tuple[str, float], ...] = ()
    unknown_reason_by_row_id: tuple[tuple[str, str], ...] = ()

    @field_validator("compatibility_key", mode="before")
    @classmethod
    def _sort_bucket_shape(cls, value: Any) -> tuple[str, str]:
        return _parse_efficacy_compatibility_key(value)

    @field_validator("sort_key", mode="before")
    @classmethod
    def _sort_key_alias(cls, value: Any) -> Any:
        return _normalize_efficacy_sort_key(value)

    @model_validator(mode="after")
    def _sort_integrity(self) -> Self:
        row_ids = tuple(row.row_id for row in self.rows)
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("疗效排序结果不得包含重复事实行")
        if any(row.compatibility_key != self.compatibility_key for row in self.rows):
            raise ValueError("疗效排序结果不得跨越兼容桶")

        known = set(self.known_row_ids)
        unknown = set(self.unknown_row_ids)
        if (
            len(known) != len(self.known_row_ids)
            or len(unknown) != len(self.unknown_row_ids)
            or known & unknown
            or known | unknown != set(row_ids)
        ):
            raise ValueError("疗效排序结果必须完整且唯一标记已知/未知行")

        state_by_id = dict(self.signal_states)
        if (
            len(state_by_id) != len(self.signal_states)
            or set(state_by_id) != set(row_ids)
        ):
            raise ValueError("疗效排序结果必须为每条事实行保存信号状态")
        known_state_ids = {
            row_id
            for row_id, state in state_by_id.items()
            if state is EfficacySignalState.KNOWN
        }
        unknown_state_ids = {
            row_id
            for row_id, state in state_by_id.items()
            if state is EfficacySignalState.UNKNOWN
        }
        if known_state_ids != known:
            raise ValueError("疗效排序结果的信号状态与已知行集合不一致")
        if unknown_state_ids != unknown:
            raise ValueError("疗效排序结果的信号状态与未知行集合不一致")

        signal_by_id = dict(self.signal_by_row_id)
        if (
            len(signal_by_id) != len(self.signal_by_row_id)
            or set(signal_by_id) != known
        ):
            raise ValueError("只有已知信号行可以携带排序信号")
        if any(not math.isfinite(value) for value in signal_by_id.values()):
            raise ValueError("疗效排序信号必须是有限数值")

        reason_by_id = dict(self.unknown_reason_by_row_id)
        if (
            len(reason_by_id) != len(self.unknown_reason_by_row_id)
            or set(reason_by_id) != unknown
            or any(not reason.strip() for reason in reason_by_id.values())
        ):
            raise ValueError("未知疗效行必须保存明确未知原因")
        return self


    @property
    def sort_mode(self) -> EfficacySortKey:
        return self.sort_key

    @property
    def fact_rows(self) -> tuple[EfficacyFactRow, ...]:
        return self.rows

    @property
    def known_rows(self) -> tuple[EfficacyFactRow, ...]:
        known = set(self.known_row_ids)
        return tuple(row for row in self.rows if row.row_id in known)

    @property
    def unknown_rows(self) -> tuple[EfficacyFactRow, ...]:
        unknown = set(self.unknown_row_ids)
        return tuple(row for row in self.rows if row.row_id in unknown)

    @property
    def has_unknown_values(self) -> bool:
        return bool(self.unknown_row_ids)

    @property
    def is_default(self) -> bool:
        return self.sort_key is EfficacySortKey.DEFAULT

    @property
    def is_user_sorted(self) -> bool:
        return self.sort_key is EfficacySortKey.SIGNAL

    def reset(self) -> EfficacySortResult:
        """从当前行集恢复不排名的确定性默认顺序。"""

        return sort_efficacy_rows(
            self.rows,
            self.compatibility_key,
            sort_mode=EfficacySortKey.DEFAULT,
        )

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(
        self,
        index: int | slice,
    ) -> EfficacyFactRow | tuple[EfficacyFactRow, ...]:
        return self.rows[index]


EfficacyViewCollection = EfficacyViewSet


def _validated_efficacy_fact_row(value: EfficacyFactRow | Mapping[str, Any]) -> EfficacyFactRow:
    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, EfficacyFactRow)
            else dict(value)
        )
        return EfficacyFactRow.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"疗效事实行重新校验失败：{error}") from error


def validate_efficacy_fact_row(
    value: EfficacyFactRow | Mapping[str, Any],
) -> EfficacyFactRow:
    """重新校验疗效事实行，拒绝 ``model_copy(update=...)`` 旁路修改。"""

    return _validated_efficacy_fact_row(value)


def validate_efficacy_view_set(
    value: EfficacyViewSet | Mapping[str, Any],
) -> EfficacyViewSet:
    """重新校验同源疗效视图集合及其嵌套事实行。"""

    try:
        raw = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, EfficacyViewSet)
            else dict(value)
        )
        return EfficacyViewSet.model_validate(raw)
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"疗效视图集合重新校验失败：{error}") from error


validate_efficacy_views = validate_efficacy_view_set


def _fact_sort_key(row: EfficacyFactRow) -> tuple[Any, ...]:
    return (
        row.product_id.casefold(),
        row.product_id,
        row.trial_id.casefold(),
        row.trial_id,
        row.endpoint_family_id.casefold(),
        row.compatibility_key,
        _timepoint_sort_key(row.actual_timepoint),
        row.actual_timepoint_unit.casefold(),
        row.analysis_population or "",
        row.analysis_form.casefold(),
        row.unit,
        0 if row.arm_role is EfficacyArmRole.TREATMENT else 1,
        row.arm_id.casefold(),
        row.row_id,
    )


def _pairing_key(row: EfficacyFactRow) -> tuple[Any, ...]:
    return (
        row.product_id,
        row.trial_id,
        row.endpoint_family_id,
        row.compatibility_key,
        row.actual_timepoint,
        row.actual_timepoint_unit,
        row.analysis_population,
        row.analysis_form,
        row.unit,
        row.comparison_id,
    )


def _comparison_id(rows: Sequence[EfficacyFactRow]) -> str:
    supplied: set[str] = {
        row.comparison_id
        for row in rows
        if row.comparison_id is not None
    }
    if len(supplied) > 1:
        raise EfficacyViewError("同一疗效并列关系不得混用多个 comparison_id")
    if supplied:
        return next(iter(supplied))
    row = rows[0]
    return stable_id(
        "efficacy-comparison",
        row.product_id,
        row.trial_id,
        row.endpoint_family_id,
        "::".join(row.compatibility_key),
        str(row.actual_timepoint),
        row.actual_timepoint_unit,
        row.analysis_population or "",
        row.analysis_form,
        row.unit,
    )


def _build_comparisons(rows: Sequence[EfficacyFactRow]) -> tuple[EfficacyComparison, ...]:
    grouped: dict[tuple[Any, ...], list[EfficacyFactRow]] = {}
    for row in rows:
        grouped.setdefault(_pairing_key(row), []).append(row)
    comparisons: list[EfficacyComparison] = []
    for key in sorted(grouped, key=lambda value: tuple(str(item) for item in value)):
        candidates = tuple(sorted(grouped[key], key=_fact_sort_key))
        treatment = next(
            (row for row in candidates if row.arm_role is EfficacyArmRole.TREATMENT),
            None,
        )
        control = next(
            (row for row in candidates if row.arm_role is EfficacyArmRole.CONTROL),
            None,
        )
        if sum(row.arm_role is EfficacyArmRole.TREATMENT for row in candidates) > 1:
            raise EfficacyViewError("同一疗效并列关系包含重复治疗臂事实")
        if sum(row.arm_role is EfficacyArmRole.CONTROL for row in candidates) > 1:
            raise EfficacyViewError("同一疗效并列关系包含重复对照臂事实")
        first = candidates[0]
        try:
            comparisons.append(
                EfficacyComparison(
                    comparison_id=_comparison_id(candidates),
                    product_id=first.product_id,
                    trial_id=first.trial_id,
                    endpoint_family_id=first.endpoint_family_id,
                    compatibility_key=first.compatibility_key,
                    actual_timepoint=first.actual_timepoint,
                    actual_timepoint_unit=first.actual_timepoint_unit,
                    analysis_population=first.analysis_population,
                    analysis_form=first.analysis_form,
                    unit=first.unit,
                    treatment=treatment,
                    control=control,
                )
            )
        except (TypeError, ValueError, ValidationError) as error:
            raise EfficacyViewError(f"疗效治疗—对照并列关系构建失败：{error}") from error
    return tuple(comparisons)


def _view_group_key(row: EfficacyFactRow) -> tuple[Any, ...]:
    return (
        row.endpoint_family_id,
        row.actual_timepoint_unit,
        row.analysis_population,
        row.analysis_form,
        row.unit,
    )


def _make_single_timepoint_view(
    rows: Sequence[EfficacyFactRow],
) -> SingleTimepointEfficacyView:
    ordered = tuple(sorted(rows, key=_fact_sort_key))
    first = ordered[0]
    try:
        return SingleTimepointEfficacyView(
            endpoint_family_id=first.endpoint_family_id,
            compatibility_key=first.compatibility_key,
            compatibility_keys=(first.compatibility_key,),
            rows=ordered,
            comparisons=_build_comparisons(ordered),
            actual_timepoint=first.actual_timepoint,
            actual_timepoint_unit=first.actual_timepoint_unit,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"单时间点疗效视图构建失败：{error}") from error


def _make_longitudinal_view(
    rows: Sequence[EfficacyFactRow],
) -> LongitudinalEfficacyView:
    ordered = tuple(sorted(rows, key=_fact_sort_key))
    first = ordered[0]
    timepoints = tuple(
        sorted({row.actual_timepoint for row in ordered}, key=_timepoint_sort_key)
    )
    try:
        return LongitudinalEfficacyView(
            endpoint_family_id=first.endpoint_family_id,
            compatibility_keys=tuple(sorted({row.compatibility_key for row in ordered})),
            rows=ordered,
            comparisons=_build_comparisons(ordered),
            timepoints=timepoints,
            timepoint_unit=first.actual_timepoint_unit,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"纵向疗效视图构建失败：{error}") from error


def _make_effect_view(
    rows: Sequence[EfficacyFactRow],
    effect_rows: Sequence[EfficacyFactRow],
) -> SourceEffectSizeEfficacyView:
    ordered = tuple(sorted(rows, key=_fact_sort_key))
    direct = tuple(sorted(effect_rows, key=_fact_sort_key))
    first = direct[0]
    try:
        return SourceEffectSizeEfficacyView(
            endpoint_family_id=first.endpoint_family_id,
            compatibility_key=first.compatibility_key,
            compatibility_keys=(first.compatibility_key,),
            rows=ordered,
            comparisons=_build_comparisons(ordered),
            effect_measure=first.effect_measure,
            effect_unit=first.effect_unit,
            effect_rows=direct,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"来源效应量森林图视图构建失败：{error}") from error


def build_efficacy_views(
    facts: Sequence[EfficacyFactRow | Mapping[str, Any]],
    *,
    compatibility_key: tuple[str, str] | str | None = None,
) -> EfficacyViewSet:
    """从同一组事实行构建单时间点、纵向和来源效应量视图。

    视图只在终点规则和时间窗规则都已形成的兼容桶内分组。每个返回的
    图形都携带完整治疗/对照事实行；来源效应量仅筛选 ``effect_value``
    已由来源直接报告的行，不计算差值、比值或任何跨试验效应。
    """

    try:
        validated = tuple(_validated_efficacy_fact_row(item) for item in facts)
    except EfficacyViewError:
        raise
    if len({row.row_id for row in validated}) != len(validated):
        raise EfficacyViewError("疗效事实输入包含重复 row_id")
    selected_key = (
        None
        if compatibility_key is None
        else _parse_efficacy_compatibility_key(compatibility_key)
    )
    selected = tuple(
        row for row in validated if selected_key is None or row.compatibility_key == selected_key
    )

    single_groups: dict[tuple[Any, ...], list[EfficacyFactRow]] = {}
    for row in selected:
        single_groups.setdefault(
            (
                row.endpoint_family_id,
                row.compatibility_key,
                row.actual_timepoint,
                row.actual_timepoint_unit,
                row.analysis_population,
                row.analysis_form,
                row.unit,
            ),
            [],
        ).append(row)
    single_views = tuple(
        _make_single_timepoint_view(single_groups[key])
        for key in sorted(single_groups, key=lambda value: tuple(str(item) for item in value))
        if any(row.value is not None for row in single_groups[key])
    )

    longitudinal_groups: dict[tuple[Any, ...], list[EfficacyFactRow]] = {}
    for row in selected:
        longitudinal_groups.setdefault(_view_group_key(row), []).append(row)
    longitudinal_rows: list[tuple[EfficacyFactRow, ...]] = []
    for key in sorted(
        longitudinal_groups,
        key=lambda value: tuple(str(item) for item in value),
    ):
        rows = longitudinal_groups[key]
        series: dict[tuple[Any, ...], list[EfficacyFactRow]] = {}
        for row in rows:
            series_key = (
                row.product_id,
                row.trial_id,
                row.comparison_id,
                row.arm_id,
            )
            series.setdefault(series_key, []).append(row)
        eligible_series = {
            series_key
            for series_key, series_rows in series.items()
            if len({row.actual_timepoint for row in series_rows}) >= 2
        }
        eligible = tuple(
            row
            for row in rows
            if (
                row.product_id,
                row.trial_id,
                row.comparison_id,
                row.arm_id,
            )
            in eligible_series
        )
        if (
            len({row.actual_timepoint for row in eligible}) >= 2
            and any(row.value is not None for row in eligible)
        ):
            longitudinal_rows.append(eligible)
    longitudinal_views = tuple(
        _make_longitudinal_view(rows)
        for rows in longitudinal_rows
    )

    effect_groups: dict[tuple[Any, ...], list[EfficacyFactRow]] = {}
    effect_rows_by_group: dict[tuple[Any, ...], list[EfficacyFactRow]] = {}
    effect_keys_by_pairing: dict[tuple[Any, ...], set[tuple[Any, ...]]] = {}
    for row in selected:
        if row.effect_value is None:
            continue
        context = (
            row.endpoint_family_id,
            row.compatibility_key,
            row.actual_timepoint_unit,
            row.analysis_population,
            row.analysis_form,
            row.unit,
        )
        key = (
            *context[:2],
            row.effect_measure,
            row.effect_unit,
            *context[2:],
        )
        effect_rows_by_group.setdefault(key, []).append(row)
        effect_keys_by_pairing.setdefault(_pairing_key(row), set()).add(key)
    for row in selected:
        pairing_key = _pairing_key(row)
        for key in sorted(
            effect_keys_by_pairing.get(pairing_key, ()),
            key=lambda value: tuple(str(item) for item in value),
        ):
            effect_groups.setdefault(key, []).append(row)
    effect_views = tuple(
        _make_effect_view(effect_groups[key], effect_rows_by_group[key])
        for key in sorted(effect_groups, key=lambda value: tuple(str(item) for item in value))
    )
    try:
        return EfficacyViewSet(
            fact_rows=selected,
            single_timepoint_views=single_views,
            longitudinal_views=longitudinal_views,
            source_effect_size_views=effect_views,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"疗效视图集合构建失败：{error}") from error


build_efficacy_view = build_efficacy_views


def _sort_group_signal(
    rows: Sequence[EfficacyFactRow],
) -> tuple[float | None, str | None]:
    """返回一组治疗—对照事实的方向校正信号和未知原因。"""

    treatment = tuple(row for row in rows if row.arm_role is EfficacyArmRole.TREATMENT)
    control = tuple(row for row in rows if row.arm_role is EfficacyArmRole.CONTROL)
    if len(treatment) > 1 or len(control) > 1:
        raise EfficacyViewError("同一疗效排序关系包含重复治疗或对照事实")
    if not treatment:
        return None, "缺少治疗组，无法确定试验内信号"
    if not control:
        return None, "缺少对照组，无法确定试验内信号"

    treatment_row = treatment[0]
    control_row = control[0]
    if treatment_row.value is None or control_row.value is None:
        return None, "治疗组或对照组值未报告，信号未知"
    if treatment_row.direction is not control_row.direction:
        return None, "治疗组与对照组方向不一致，信号未知"

    raw_difference = float(treatment_row.value) - float(control_row.value)
    signal = (
        raw_difference
        if treatment_row.direction is EndpointDirection.HIGHER_IS_BETTER
        else -raw_difference
    )
    if not math.isfinite(signal):
        raise EfficacyViewError("疗效排序信号必须是有限数值")
    return signal, None


def sort_efficacy_rows(
    facts: Sequence[EfficacyFactRow | Mapping[str, Any]],
    compatibility_key: tuple[str, str] | str,
    *,
    sort_mode: EfficacySortKey | str | None = EfficacySortKey.DEFAULT,
    sort_key: EfficacySortKey | str | None = None,
    descending: bool = True,
) -> EfficacySortResult:
    """在单一兼容桶内按默认顺序或用户疗效信号排序。

    ``DEFAULT`` 不使用任何疗效数值作为排序键，只按稳定事实身份排序。``SIGNAL``
    以同一试验内治疗—对照的方向校正差值为主键；没有完整可比两臂值
    的事实保持明确未知状态，并排在已知信号之后，而不是按零值处理。
    """

    try:
        requested_bucket = _parse_efficacy_compatibility_key(compatibility_key)
        requested_mode = _normalize_efficacy_sort_key(sort_mode)
        if sort_key is not None:
            supplied_key = _normalize_efficacy_sort_key(sort_key)
            if (
                requested_mode is not EfficacySortKey.DEFAULT
                and requested_mode != supplied_key
            ):
                raise EfficacyViewError("排序方式参数不得互相冲突")
            requested_mode = supplied_key
        mode = EfficacySortKey(requested_mode)
    except EfficacyViewError:
        raise
    except (TypeError, ValueError) as error:
        raise EfficacyViewError(f"疗效排序参数无效：{error}") from error
    if not isinstance(descending, bool):
        raise EfficacyViewError("疗效排序方向必须是布尔值")

    try:
        validated = tuple(_validated_efficacy_fact_row(item) for item in facts)
    except EfficacyViewError:
        raise
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"疗效排序输入无效：{error}") from error
    if len({row.row_id for row in validated}) != len(validated):
        raise EfficacyViewError("疗效排序输入包含重复 row_id")
    if any(row.compatibility_key != requested_bucket for row in validated):
        raise EfficacyViewError("疗效排序只接受一个指定兼容桶，不能跨桶排序")

    grouped: dict[tuple[Any, ...], list[EfficacyFactRow]] = {}
    for row in validated:
        grouped.setdefault(_pairing_key(row), []).append(row)

    groups: list[
        tuple[tuple[EfficacyFactRow, ...], float | None, str | None]
    ] = []
    for key in sorted(grouped, key=lambda value: tuple(str(item) for item in value)):
        candidates = tuple(sorted(grouped[key], key=_fact_sort_key))
        signal, unknown_reason = _sort_group_signal(candidates)
        groups.append((candidates, signal, unknown_reason))

    if mode is EfficacySortKey.DEFAULT:
        ordered = tuple(sorted(validated, key=_fact_sort_key))
    else:
        ordered_groups = sorted(
            groups,
            key=lambda item: (
                0 if item[1] is not None else 1,
                (
                    (-item[1] if descending else item[1])
                    if item[1] is not None
                    else 0.0
                ),
                tuple(
                    str(value)
                    for value in _pairing_key(item[0][0])
                ),
            ),
        )
        ordered = tuple(row for group, _, _ in ordered_groups for row in group)

    unknown_row_ids: list[str] = []
    signal_by_row_id: dict[str, float] = {}
    unknown_reason_by_row_id: dict[str, str] = {}
    state_by_row_id: dict[str, EfficacySignalState] = {}
    for group, signal, unknown_reason in groups:
        if signal is None:
            assert unknown_reason is not None
            for row in group:
                unknown_row_ids.append(row.row_id)
                state_by_row_id[row.row_id] = EfficacySignalState.UNKNOWN
                unknown_reason_by_row_id[row.row_id] = unknown_reason
        else:
            for row in group:
                state_by_row_id[row.row_id] = EfficacySignalState.KNOWN
                signal_by_row_id[row.row_id] = signal

    ordered_state = tuple((row.row_id, state_by_row_id[row.row_id]) for row in ordered)
    ordered_known = tuple(row.row_id for row in ordered if row.row_id in signal_by_row_id)
    ordered_unknown = tuple(
        row.row_id for row in ordered if row.row_id in unknown_reason_by_row_id
    )
    try:
        return EfficacySortResult(
            compatibility_key=requested_bucket,
            sort_key=mode,
            descending=descending if mode is EfficacySortKey.SIGNAL else False,
            rows=ordered,
            known_row_ids=ordered_known,
            unknown_row_ids=ordered_unknown,
            signal_states=ordered_state,
            signal_by_row_id=tuple(
                (row_id, signal_by_row_id[row_id])
                for row_id in ordered_known
            ),
            unknown_reason_by_row_id=tuple(
                (row_id, unknown_reason_by_row_id[row_id])
                for row_id in ordered_unknown
            ),
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise EfficacyViewError(f"疗效排序结果构建失败：{error}") from error


def reset_efficacy_sort(
    value: EfficacySortResult
    | Sequence[EfficacyFactRow | Mapping[str, Any]],
    compatibility_key: tuple[str, str] | str | None = None,
) -> EfficacySortResult:
    """恢复同一兼容桶的默认不排名顺序。"""

    if isinstance(value, EfficacySortResult):
        if compatibility_key is not None:
            requested = _parse_efficacy_compatibility_key(compatibility_key)
            if requested != value.compatibility_key:
                raise EfficacyViewError("重置排序不得切换兼容桶")
        return value.reset()
    if compatibility_key is None:
        raise EfficacyViewError("重置事实行排序必须指定兼容桶")
    return sort_efficacy_rows(
        value,
        compatibility_key,
        sort_mode=EfficacySortKey.DEFAULT,
    )


reset_efficacy_rows = reset_efficacy_sort



__all__ = [
    "CompetitorEndpointEvidence",
    "EndpointAdoptionStatus",
    "EndpointBasis",
    "EndpointBasisError",
    "EndpointBasisObservation",
    "EndpointBasisRecord",
    "EndpointBasisSet",
    "EndpointConsensus",
    "EndpointEvidence",
    "GuidanceBasisGroup",
    "GuidanceEvidence",
    "GuidanceLifecycleState",
    "GuidanceTrack",
    "validate_endpoint_basis",
    "validate_endpoint_basis_set",
    "GuidelineEvidence",
    "build_endpoint_basis",
    "build_endpoint_basis_set",
    "build_endpoint_bases",
    "derive_endpoint_basis",
    "guidance_lifecycle_state",
    "guidance_status_label_zh",
    "resolve_endpoint_basis",
    "select_current_guidance",
    "select_current_guideline_evidence",
    "ArmRole",
    "EfficacyArmRole",
    "EfficacyChartKind",
    "EfficacyComparison",
    "EfficacyFactRow",
    "EfficacySignalState",
    "EfficacySortKey",
    "EfficacySortMode",
    "EfficacySortResult",

    "reset_efficacy_rows",
    "reset_efficacy_sort",
    "sort_efficacy_rows",
    "EfficacyForestView",
    "EfficacyViewBase",
    "EfficacyViewCollection",
    "EfficacyViewError",
    "EfficacyViewKind",
    "EfficacyViewSet",
    "EfficacyViews",
    "EffectSizeForestView",
    "LongitudinalEfficacyView",
    "LongitudinalView",
    "SingleTimepointEfficacyView",
    "SingleTimepointView",
    "SourceEffectSizeEfficacyView",
    "SourceEffectSizeView",
    "build_efficacy_view",
    "build_efficacy_views",
    "validate_efficacy_fact_row",
    "validate_efficacy_view_set",
    "validate_efficacy_views",
    "EfficacyEffectSizeView",
    "EfficacyLongitudinalView",
    "EfficacySingleTimepointView",
    "EffectSizeView",
]
