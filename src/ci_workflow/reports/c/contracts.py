"""C 类设计观察事实合同与登记优先门槛。

本模块只定义设计事实的强类型合同与核心试验门槛判定：关键人群/分组/终点/
时间点缺失阻断；官方登记已覆盖关键设计时 Protocol/SAP 缺失不阻断；统计细节
缺失保持非阻断并保留真实披露状态。门槛通过不等于本层生成草稿。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole

SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "schemas"
    / "reports"
    / "c-design-observation.schema.json"
)

_REGISTRY_DESIGN_ROLES = frozenset({SourceRole.CLINICAL_TRIAL_REGISTRY})
_ACCEPTED_FACT_STATES = frozenset(
    {
        FactDisclosureState.REPORTED_VALUE,
        FactDisclosureState.REPORTED_ZERO,
        FactDisclosureState.NOT_APPLICABLE,
    }
)
_DISCLOSED_STATISTICAL_STATES = frozenset(
    {
        FactDisclosureState.REPORTED_VALUE,
        FactDisclosureState.REPORTED_ZERO,
    }
)


class DesignObservationError(ValueError):
    """设计观察事实不满足强类型或公共边界合同。"""


class DesignFieldFamily(StrEnum):
    """C 类设计事实的封闭字段族。"""

    TRIAL_IDENTITY = "trial_identity"
    POPULATION = "population"
    GROUPING = "grouping"
    INTERVENTION = "intervention"
    DOSE_SCHEDULE = "dose_schedule"
    ENDPOINT = "endpoint"
    TIMEPOINT = "timepoint"
    SAMPLE_SIZE = "sample_size"
    OPERATIONAL = "operational"
    STATISTICAL = "statistical"


class DesignGateDecision(StrEnum):
    """设计门槛决定；本层通过不等于草稿生成。"""

    PASSED = "passed"
    BLOCKED = "blocked"


class DesignEvidenceScope(StrEnum):
    """设计证据范围；Protocol/SAP 有无单独显式，不作为充分性代理。"""

    REGISTRY_ONLY = "registry_only"
    REGISTRY_WITH_PROTOCOL = "registry_with_protocol"
    REGISTRY_WITH_PUBLICATION_CROSSCHECK = "registry_with_publication_crosscheck"
    PROTOCOL_SUPPORTED = "protocol_supported"
    NO_REGISTRY_DESIGN = "no_registry_design"


_CRITICAL_FAMILY_SPECS: tuple[tuple[DesignFieldFamily, str, str], ...] = (
    (
        DesignFieldFamily.POPULATION,
        "target_population",
        "目标人群与关键入排",
    ),
    (
        DesignFieldFamily.GROUPING,
        "arm_randomization_blinding",
        "分组、随机化与盲法",
    ),
    (
        DesignFieldFamily.ENDPOINT,
        "primary_endpoint_definition",
        "主要终点定义",
    ),
    (
        DesignFieldFamily.TIMEPOINT,
        "primary_endpoint_timepoint",
        "主要终点评估时间点",
    ),
)

_CRITICAL_LABEL_TOKENS: dict[DesignFieldFamily, str] = {
    DesignFieldFamily.POPULATION: "人群",
    DesignFieldFamily.GROUPING: "分组",
    DesignFieldFamily.ENDPOINT: "终点",
    DesignFieldFamily.TIMEPOINT: "时间点",
}

_STATISTICAL_FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("analysis_population", "分析人群"),
    ("comparison_logic", "主要比较逻辑"),
    ("statistical_model", "统计模型与检验"),
    ("effect_size", "效应量"),
    ("multiplicity", "多重性控制"),
)


def _text(value: str, *, field_name: str = "设计合同文本") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name}必须是文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name}不能为空")
    return normalized


def _optional_text(value: str | None, *, field_name: str = "设计合同文本") -> str | None:
    return None if value is None else _text(value, field_name=field_name)


def _raw_text(value: str, *, field_name: str = "设计来源原文") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}不能为空")
    return value


class DesignObservation(BaseModel):
    """一条产品—试验—组别闭合的设计事实观察。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: Literal["1.0"] = "1.0"
    row_id: str
    source_row_id: str
    observation_id: str
    product_id: str
    trial_id: str
    cohort_id: str
    group_id: str
    field_family: DesignFieldFamily
    field: str
    endpoint_key: str | None = None
    source_field_name: str
    source_field_definition: str
    source_text: str
    scale: str | None = None
    scale_version: str | None = None
    operator: str | None = None
    threshold_value: str | None = None
    threshold_unit: str | None = None
    assessment_timepoint: str | None = None
    stage: str | None = None
    development_role: str | None = None
    randomization: str | None = None
    blinding: str | None = None
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
        "field",
        "source_version_id",
        "compatibility_rule",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        labels = {
            "product_id": "产品标识",
            "trial_id": "试验标识",
            "cohort_id": "队列标识",
            "group_id": "组别标识",
            "field": "设计字段",
        }
        return _text(value, field_name=labels.get(info.field_name, "设计合同文本"))

    @field_validator("source_field_name", "source_field_definition", "source_text")
    @classmethod
    def _source_raw_text(cls, value: str, info: Any) -> str:
        labels = {
            "source_field_name": "设计来源字段名",
            "source_field_definition": "设计来源字段定义",
            "source_text": "设计来源原文",
        }
        return _raw_text(value, field_name=labels.get(info.field_name, "设计来源原文"))

    @field_validator(
        "scale",
        "scale_version",
        "operator",
        "threshold_value",
        "threshold_unit",
        "assessment_timepoint",
        "stage",
        "development_role",
        "randomization",
        "blinding",
        "reported_zero_text",
        "route_receipt_id",
        "applicability_predicate_id",
        "endpoint_key",
    )
    @classmethod
    def _optional_text_fields(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @field_validator("difference_labels_zh", mode="before")
    @classmethod
    def _difference_labels(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = (value,) if isinstance(value, str) else tuple(value)
        normalized = tuple(_text(item, field_name="设计差异标签") for item in values)
        if len(normalized) != len(set(normalized)):
            raise ValueError("设计差异标签不得重复")
        return normalized

    @model_validator(mode="after")
    def _disclosure_contract(self) -> Self:
        if self.field_family in {
            DesignFieldFamily.ENDPOINT,
            DesignFieldFamily.TIMEPOINT,
        }:
            endpoint_key = self.endpoint_key
            if endpoint_key is None:
                endpoint_key = re.sub(
                    r"_(?:definition|timepoint|assessment_timepoint)$", "", self.field
                )
                object.__setattr__(self, "endpoint_key", endpoint_key)
            if not endpoint_key:
                raise ValueError("终点与时间点观察必须具有可配对的终点键")
        elif self.endpoint_key is not None:
            raise ValueError("非终点设计事实不得携带终点配对键")
        if self.scale is None and self.scale_version is not None:
            raise ValueError("量表版本不能脱离量表名称单独存在")
        if (
            self.disclosure_state is FactDisclosureState.NOT_APPLICABLE
            and self.applicability_predicate_id is None
        ):
            raise ValueError("不适用设计事实必须提供适用性谓词")
        if (
            self.disclosure_state is FactDisclosureState.REPORTED_ZERO
            and self.reported_zero_text is None
        ):
            raise ValueError("已报告为零的设计事实必须保留零值原文")
        if (
            self.conflict_disposition is ConflictDisposition.OPEN_CONFLICT_PRESERVED
            and self.review_state is FactReviewState.ACCEPTED
        ):
            raise ValueError("未解决冲突不得作为已接受设计事实")
        return self


class DesignGateFailure(BaseModel):
    """设计门槛阻断项：稳定失败码 + 试验/组别/字段定位 + 中文补件说明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_code: str
    trial_id: str
    group_id: str | None
    field_id: str
    field_family: DesignFieldFamily | None
    user_note_zh: str

    @field_validator("failure_code", "trial_id", "field_id", "user_note_zh")
    @classmethod
    def _required(cls, value: str) -> str:
        return _text(value)

    @field_validator("group_id")
    @classmethod
    def _optional_group(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="组别标识")


class DesignNonblockingGap(BaseModel):
    """非阻断统计细节缺口；保留真实披露状态，不升级为关键阻断。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    group_id: str | None = None
    field_id: str
    field_family: DesignFieldFamily
    disclosure_state: FactDisclosureState
    blocking: Literal[False] = False
    user_note_zh: str

    @field_validator("trial_id", "field_id", "user_note_zh")
    @classmethod
    def _required(cls, value: str) -> str:
        return _text(value)

    @field_validator("group_id")
    @classmethod
    def _optional_group(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="组别标识")


class DesignGateResult(BaseModel):
    """设计门槛结果；``allows_draft`` 在本层恒为 False。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: DesignGateDecision
    allows_draft: Literal[False] = False
    failures: tuple[DesignGateFailure, ...] = ()
    nonblocking_gaps: tuple[DesignNonblockingGap, ...] = ()
    evidence_scope: DesignEvidenceScope | None = None
    evidence_scope_note_zh: str | None = None
    protocol_sap_available: bool = False

    @field_validator("evidence_scope_note_zh")
    @classmethod
    def _optional_note(cls, value: str | None) -> str | None:
        return _optional_text(value, field_name="证据范围说明")


def validate_design_observation(
    observation: DesignObservation | Mapping[str, Any],
) -> DesignObservation:
    """在公共边界重新校验设计观察，拒绝未知字段与空白身份。"""

    if isinstance(observation, DesignObservation):
        unknown_fields = set(observation.__dict__) - set(type(observation).model_fields)
        if unknown_fields:
            raise DesignObservationError(
                f"设计观察重新校验失败：包含未知字段 {tuple(sorted(unknown_fields))}"
            )
        extras = observation.__pydantic_extra__
        if extras:
            raise DesignObservationError(
                f"设计观察重新校验失败：包含未知字段 {tuple(sorted(extras))}"
            )
        payload: object = observation.model_dump(mode="python", warnings=False)
    elif isinstance(observation, Mapping):
        payload = dict(observation)
    else:
        raise TypeError("设计观察必须是 DesignObservation 或映射")
    try:
        return DesignObservation.model_validate(payload)
    except ValidationError as error:
        raise DesignObservationError(f"设计观察重新校验失败：{error}") from error


def _is_accepted_fact(observation: DesignObservation) -> bool:
    return (
        observation.review_state is FactReviewState.ACCEPTED
        and observation.disclosure_state in _ACCEPTED_FACT_STATES
        and observation.conflict_disposition
        is ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
    )


def _is_registry_design(observation: DesignObservation) -> bool:
    return observation.source_role in _REGISTRY_DESIGN_ROLES


def _family_covered_by_registry(
    observations: Sequence[DesignObservation],
    family: DesignFieldFamily,
) -> bool:
    """四类关键设计只接受官方登记覆盖；Protocol/SAP 不得单独满足。"""

    return any(
        item.field_family is family
        and _is_accepted_fact(item)
        and _is_registry_design(item)
        for item in observations
    )


def _family_present_as_publication(
    observations: Sequence[DesignObservation],
    family: DesignFieldFamily,
) -> bool:
    return any(
        item.field_family is family
        and _is_accepted_fact(item)
        and item.source_role is SourceRole.PRIMARY_TRIAL_REPORT
        for item in observations
    )


def _infer_group_id(observations: Sequence[DesignObservation]) -> str | None:
    for item in observations:
        if item.group_id:
            return item.group_id
    return None


def _missing_failure(
    *,
    trial_id: str,
    group_id: str | None,
    family: DesignFieldFamily,
    field_id: str,
    label: str,
) -> DesignGateFailure:
    token = _CRITICAL_LABEL_TOKENS[family]
    note = (
        f"该项试验（{trial_id}）缺少{token}相关的{label}信息，"
        f"请补充官方登记平台中的对应设计字段。"
    )
    return DesignGateFailure(
        failure_code=f"c_missing_{family.value}",
        trial_id=trial_id,
        group_id=group_id,
        field_id=field_id,
        field_family=family,
        user_note_zh=note,
    )


def _publication_failure(
    *,
    trial_id: str,
    group_id: str | None,
    has_registry_design: bool,
) -> DesignGateFailure:
    if has_registry_design:
        note = (
            f"该项试验（{trial_id}）部分关键设计仅来自论文或文献摘要，"
            f"不能替代官方登记平台中的对应方案设计事实；请补充登记来源。"
        )
    else:
        note = (
            f"该项试验（{trial_id}）仅有论文或文献中的设计摘要，"
            f"不能替代官方登记平台中的方案设计事实；请补充登记来源。"
        )
    return DesignGateFailure(
        failure_code="c_publication_cannot_replace_registry_design",
        trial_id=trial_id,
        group_id=group_id,
        field_id="registry_design_authority",
        field_family=None,
        user_note_zh=note,
    )


def _statistical_gap_note_zh(
    *,
    trial_id: str,
    label: str,
    disclosure_state: FactDisclosureState,
) -> str:
    if disclosure_state is FactDisclosureState.NOT_APPLICABLE:
        return (
            f"该项试验（{trial_id}）的{label}不适用；"
            f"统计细节缺失不阻断本报告通过。"
        )
    if disclosure_state is FactDisclosureState.NOT_REPORTED:
        return (
            f"该项试验（{trial_id}）的{label}原文未报告；"
            f"统计细节缺失不阻断本报告通过。如已公开，请补充来源。"
        )
    if disclosure_state is FactDisclosureState.BELOW_REPORTING_THRESHOLD:
        return (
            f"该项试验（{trial_id}）的{label}低于来源列示阈值；"
            f"统计细节缺失不阻断本报告通过。如已公开，请补充来源。"
        )
    if disclosure_state is FactDisclosureState.CONFLICTING:
        return (
            f"该项试验（{trial_id}）的{label}来源存在冲突；"
            f"统计细节缺失不阻断本报告通过。如已公开，请补充来源。"
        )
    if disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE:
        return (
            f"该项试验（{trial_id}）的{label}因技术路径未解决暂不可用；"
            f"统计细节缺失不阻断本报告通过。如已公开，请补充来源。"
        )
    return (
        f"该项试验（{trial_id}）的{label}尚未公开；"
        f"统计细节缺失不阻断本报告通过。如已公开，请补充来源。"
    )


def _statistical_gap(
    *,
    trial_id: str,
    group_id: str | None,
    field_id: str,
    label: str,
    disclosure_state: FactDisclosureState,
) -> DesignNonblockingGap:
    return DesignNonblockingGap(
        trial_id=trial_id,
        group_id=group_id,
        field_id=field_id,
        field_family=DesignFieldFamily.STATISTICAL,
        disclosure_state=disclosure_state,
        blocking=False,
        user_note_zh=_statistical_gap_note_zh(
            trial_id=trial_id,
            label=label,
            disclosure_state=disclosure_state,
        ),
    )


def _accepted_statistical_by_field(
    observations: Sequence[DesignObservation],
) -> dict[str, DesignObservation]:
    selected: dict[str, DesignObservation] = {}
    for item in observations:
        if item.field_family is not DesignFieldFamily.STATISTICAL:
            continue
        if item.review_state is not FactReviewState.ACCEPTED:
            continue
        current = selected.get(item.field)
        if current is None:
            selected[item.field] = item
            continue
        if (
            item.disclosure_state in _DISCLOSED_STATISTICAL_STATES
            and current.disclosure_state not in _DISCLOSED_STATISTICAL_STATES
        ):
            selected[item.field] = item
    return selected


def _derive_evidence_scope(
    observations: Sequence[DesignObservation],
) -> tuple[DesignEvidenceScope, str, bool]:
    roles = {item.source_role for item in observations}
    protocol_sap_available = SourceRole.PROTOCOL_SAP in roles
    has_registry = SourceRole.CLINICAL_TRIAL_REGISTRY in roles
    has_publication = SourceRole.PRIMARY_TRIAL_REPORT in roles

    if has_registry and has_publication:
        return (
            DesignEvidenceScope.REGISTRY_WITH_PUBLICATION_CROSSCHECK,
            "以官方登记设计事实为准，论文仅作交叉核对",
            protocol_sap_available,
        )
    if has_registry and protocol_sap_available:
        return (
            DesignEvidenceScope.REGISTRY_WITH_PROTOCOL,
            "官方登记与试验方案共同覆盖设计事实",
            True,
        )
    if has_registry:
        return (
            DesignEvidenceScope.REGISTRY_ONLY,
            "仅有注册登记信息",
            False,
        )
    if protocol_sap_available:
        return (
            DesignEvidenceScope.PROTOCOL_SUPPORTED,
            "当前仅有试验方案或统计分析计划中的设计信息，尚无官方登记设计事实",
            True,
        )
    if has_publication:
        return (
            DesignEvidenceScope.NO_REGISTRY_DESIGN,
            "当前仅有论文或文献中的设计摘要，尚无官方登记设计事实",
            False,
        )
    return (
        DesignEvidenceScope.NO_REGISTRY_DESIGN,
        "当前尚无官方登记设计事实",
        False,
    )


def evaluate_design_gate(
    observations: Sequence[DesignObservation | Mapping[str, Any]],
    *,
    core_trial_ids: Sequence[str],
) -> DesignGateResult:
    """按核心试验逐项判定登记优先设计门槛。"""

    if not core_trial_ids:
        raise ValueError("核心试验清单不能为空")
    normalized_core_trial_ids = tuple(
        _text(raw_trial_id, field_name="试验标识") for raw_trial_id in core_trial_ids
    )
    if len(normalized_core_trial_ids) != len(set(normalized_core_trial_ids)):
        raise ValueError("核心试验清单不能重复")

    validated = tuple(validate_design_observation(item) for item in observations)
    failures: list[DesignGateFailure] = []
    gaps: list[DesignNonblockingGap] = []

    for trial_id in normalized_core_trial_ids:
        trial_obs = tuple(item for item in validated if item.trial_id == trial_id)
        group_id = _infer_group_id(trial_obs)
        publication_substitution = False
        has_registry_design = any(
            _is_registry_design(item) and _is_accepted_fact(item) for item in trial_obs
        )

        for family, field_id, label in _CRITICAL_FAMILY_SPECS:
            if _family_covered_by_registry(trial_obs, family):
                continue
            if _family_present_as_publication(trial_obs, family):
                publication_substitution = True
            failures.append(
                _missing_failure(
                    trial_id=trial_id,
                    group_id=group_id,
                    family=family,
                    field_id=field_id,
                    label=label,
                )
            )

        if publication_substitution:
            failures.append(
                _publication_failure(
                    trial_id=trial_id,
                    group_id=group_id,
                    has_registry_design=has_registry_design,
                )
            )

        statistical_by_field = _accepted_statistical_by_field(trial_obs)
        for field_id, label in _STATISTICAL_FIELD_SPECS:
            observed = statistical_by_field.get(field_id)
            if (
                observed is not None
                and observed.disclosure_state in _DISCLOSED_STATISTICAL_STATES
            ):
                continue
            disclosure_state = (
                observed.disclosure_state
                if observed is not None
                else FactDisclosureState.NOT_PUBLICLY_DISCLOSED
            )
            gaps.append(
                _statistical_gap(
                    trial_id=trial_id,
                    group_id=group_id,
                    field_id=field_id,
                    label=label,
                    disclosure_state=disclosure_state,
                )
            )

    scope, note, protocol_sap_available = _derive_evidence_scope(validated)
    if failures:
        return DesignGateResult(
            decision=DesignGateDecision.BLOCKED,
            allows_draft=False,
            failures=tuple(failures),
            nonblocking_gaps=tuple(gaps),
            evidence_scope=scope,
            evidence_scope_note_zh=note,
            protocol_sap_available=protocol_sap_available,
        )

    return DesignGateResult(
        decision=DesignGateDecision.PASSED,
        allows_draft=False,
        failures=(),
        nonblocking_gaps=tuple(gaps),
        evidence_scope=scope,
        evidence_scope_note_zh=note,
        protocol_sap_available=protocol_sap_available,
    )


__all__ = [
    "SCHEMA_PATH",
    "DesignEvidenceScope",
    "DesignFieldFamily",
    "DesignGateDecision",
    "DesignGateFailure",
    "DesignGateResult",
    "DesignNonblockingGap",
    "DesignObservation",
    "DesignObservationError",
    "evaluate_design_gate",
    "validate_design_observation",
]
